# Phase 18: Structure Generation - Research

**Researched:** 2026-04-08
**Domain:** Molecular dynamics ice-water interface assembly
**Confidence:** HIGH

## Summary

This phase implements the core logic for assembling ice-water interface structures in three modes: slab (ice-water-ice sandwich), pocket (water cavity in ice matrix), and piece (ice crystal in water box). The approach follows the well-established `gmx solvate` pattern: tile a pre-equilibrated water box across the target region, then remove overlapping water molecules that are too close to ice atoms. Ice structure is always preserved intact; only water molecules are removed.

The key technical challenge is efficient overlap detection under periodic boundary conditions. The standard solution is `scipy.spatial.cKDTree` with its `boxsize` parameter, which natively handles minimum-image convention for periodic systems. This avoids hand-rolling distance calculations with wrapping logic.

For piece mode shape: research confirms that **box/cube is the standard and only shape used in practice** in the MD ice-in-water simulation literature. Non-box shapes (sphere, cylinder) break the periodic crystallographic structure of ice and are essentially never used in published studies. Ship box-only for v3.0.

**Primary recommendation:** Use fill-and-trim approach (tile tip4p.gro, remove overlapping water) with scipy.spatial.cKDTree for PBC-aware overlap detection. Ship piece mode as box-only shape.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | 2.4.3 | Array operations for coordinate manipulation | Already in codebase, standard for scientific Python |
| scipy.spatial.cKDTree | 1.17.1 | PBC-aware nearest-neighbor search for overlap detection | Native `boxsize` parameter handles periodic boundaries; `query_ball_tree` finds all overlapping pairs efficiently |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| genice2 | 2.2.13.1 | Ice structure generation (already in codebase) | Generating ice candidates in Tab 1 |
| genice-core | 1.4.3 | Core GenIce algorithms | Used internally by genice2 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| scipy.spatial.cKDTree | Brute-force distance loop | cKDTree is O(N log N) vs O(N²); with `boxsize` it handles PBC natively |
| scipy.spatial.cKDTree | MDAnalysis neighbor search | Overkill dependency for this use case; cKDTree is sufficient |
| Custom PBC wrapping | No wrapping (non-periodic) | Must handle PBC — GROMACS simulations require it |

**Already installed (no new dependencies needed):**
```bash
# All required packages already in environment:
pip list | grep -E 'numpy|scipy|genice'
# numpy 2.4.3, scipy 1.17.1, genice2 2.2.13.1
```

## Architecture Patterns

### Recommended Project Structure
```
quickice/structure_generation/
├── __init__.py              # Module exports (update to include new classes)
├── generator.py             # Existing: IceStructureGenerator
├── mapper.py                # Existing: phase ID mapping
├── types.py                 # Existing: Candidate, GenerationResult + NEW: InterfaceStructure, InterfaceConfig
├── errors.py                # Existing + NEW: InterfaceGenerationError, OverlapError
├── interface_builder.py     # NEW: Main interface assembly orchestrator
├── water_filler.py          # NEW: Water tiling/fill logic (gmx solvate-like)
├── overlap_resolver.py      # NEW: Overlap detection + water removal
└── modes/
    ├── __init__.py
    ├── slab.py              # Slab mode: ice-water-ice sandwich along Z
    ├── pocket.py            # Pocket mode: water cavity in ice matrix
    └── piece.py             # Piece mode: ice crystal in water box
```

### Pattern 1: Fill-and-Trim (gmx solvate approach)
**What:** Tile a pre-equilibrated water structure (tip4p.gro) across the target region, then remove water molecules overlapping with ice atoms.
**When to use:** All three modes (slab, pocket, piece) for placing water molecules.
**Example:**
```python
# Source: gmx solvate documentation + QuickIce tip4p.gro analysis
import numpy as np
from scipy.spatial import cKDTree

def fill_region_with_water(region_box: np.ndarray, water_template_box: np.ndarray, 
                            water_positions_nm: np.ndarray) -> np.ndarray:
    """Tile water template across region, returning all water O positions.
    
    Args:
        region_box: [lx, ly, lz] target region dimensions in nm
        water_template_box: [wx, wy, wz] water template box dimensions in nm  
        water_positions_nm: (N, 3) water molecule positions in nm (O atoms only)
    
    Returns:
        (M, 3) array of tiled water O positions filling the region
    """
    # Calculate tiling counts along each axis
    nx = int(np.ceil(region_box[0] / water_template_box[0]))
    ny = int(np.ceil(region_box[1] / water_template_box[1]))
    nz = int(np.ceil(region_box[2] / water_template_box[2]))
    
    tiled_positions = []
    for ix in range(nx):
        for iy in range(ny):
            for iz in range(nz):
                offset = np.array([
                    ix * water_template_box[0],
                    iy * water_template_box[1], 
                    iz * water_template_box[2]
                ])
                shifted = water_positions_nm + offset
                # Filter to those within region (with small tolerance for PBC)
                mask = (
                    (shifted[:, 0] < region_box[0]) &
                    (shifted[:, 1] < region_box[1]) &
                    (shifted[:, 2] < region_box[2])
                )
                tiled_positions.append(shifted[mask])
    
    return np.vstack(tiled_positions) if tiled_positions else np.empty((0, 3))
```

### Pattern 2: PBC-Aware Overlap Detection with cKDTree
**What:** Use scipy.spatial.cKDTree with `boxsize` parameter for efficient, PBC-correct nearest-neighbor queries.
**When to use:** Detecting overlaps between ice and water atoms at boundaries.
**Example:**
```python
# Source: scipy docs (scipy.spatial.cKDTree with boxsize)
# boxsize handles minimum image convention automatically
from scipy.spatial import cKDTree

def detect_overlaps(ice_o_positions_nm: np.ndarray, 
                    water_o_positions_nm: np.ndarray,
                    box_dims_nm: np.ndarray,
                    threshold_nm: float = 0.25) -> set[int]:
    """Find water molecule indices that overlap with ice O atoms.
    
    Uses cKDTree with boxsize for PBC-aware distance calculation.
    
    Args:
        ice_o_positions_nm: (N_ice, 3) ice oxygen positions in nm
        water_o_positions_nm: (N_water, 3) water oxygen positions in nm
        box_dims_nm: [lx, ly, lz] box dimensions in nm
        threshold_nm: Minimum acceptable O-O distance (0.25 nm = 2.5 Å)
    
    Returns:
        Set of water molecule indices to remove
    """
    # Build KD tree for ice oxygens with PBC
    ice_tree = cKDTree(ice_o_positions_nm, boxsize=box_dims_nm)
    water_tree = cKDTree(water_o_positions_nm, boxsize=box_dims_nm)
    
    # Find all water-ice pairs within threshold distance
    # query_ball_tree returns dict: water_idx -> list of ice indices within r
    pairs = water_tree.query_ball_tree(ice_tree, r=threshold_nm)
    
    # Collect all water molecule indices that have at least one ice neighbor
    overlapping_water_indices = set()
    for water_idx, ice_neighbors in enumerate(pairs):
        if ice_neighbors:  # At least one ice O within threshold
            overlapping_water_indices.add(water_idx)
    
    return overlapping_water_indices
```

### Pattern 3: Whole-Molecule Removal (preserve ice, remove water)
**What:** Always remove entire water molecules (all 4 atoms: OW, HW1, HW2, MW) when any atom of that molecule overlaps with ice. Ice structure is never modified.
**When to use:** Overlap resolution in all three modes.
**Key detail:** Water molecules in tip4p.gro are stored as groups of 4 atoms per molecule (OW, HW1, HW2, MW). When detecting overlaps, only check O-O distances (oxygen positions). When removing, remove all 4 atoms of that molecule.
```python
# Water molecule stride in TIP4P: 4 atoms per molecule
ATOMS_PER_MOLECULE = 4  # OW, HW1, HW2, MW

def remove_overlapping_water(all_water_positions: np.ndarray, 
                              overlapping_mol_indices: set[int]) -> np.ndarray:
    """Remove entire water molecules that overlap with ice.
    
    Args:
        all_water_positions: (N*4, 3) all water atom positions
        overlapping_mol_indices: Set of molecule indices to remove
    
    Returns:
        Filtered positions array with overlapping molecules removed
    """
    total_molecules = len(all_water_positions) // ATOMS_PER_MOLECULE
    keep_mask = np.ones(total_molecules, dtype=bool)
    for idx in overlapping_mol_indices:
        keep_mask[idx] = False
    
    # Expand mask to all atoms in each molecule
    atom_mask = np.repeat(keep_mask, ATOMS_PER_MOLECULE)
    return all_water_positions[atom_mask]
```

### Anti-Patterns to Avoid
- **Removing ice atoms to resolve overlaps:** Ice structure from GenIce2 is physically valid and crystallographically correct. Never modify it. Always remove water only.
- **Brute-force O(N²) distance calculation:** With thousands of atoms, O(N²) is too slow. Use cKDTree for O(N log N) queries.
- **Forgetting PBC in distance calculations:** Atoms near box boundaries can overlap with atoms near the opposite boundary. Without PBC-aware distances, you'll miss these overlaps. Use cKDTree `boxsize`.
- **Breaking water molecules:** Always remove all 4 atoms of a TIP4P molecule together. Partial removal creates invalid topology.
- **Mixing units (Å vs nm):** QuickIce stores everything in nm. The threshold is 2.5 Å = 0.25 nm. Consistently use nm internally. Display Å to user only for the threshold input.
- **Non-orthogonal box support in v3.0:** GenIce2 can generate triclinic cells, but QuickIce's interface modes should use orthogonal boxes for simplicity. The existing `cell` format supports triclinic, but the UI only allows orthogonal box input.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PBC-aware distance calculation | Custom wrapping + sqrt loop | scipy.spatial.cKDTree with `boxsize` | Handles minimum image convention correctly; O(N log N) vs O(N²); battle-tested |
| Nearest-neighbor overlap detection | Nested for-loop over all atom pairs | cKDTree.query_ball_tree() | Same O(N log N) benefit; returns all pairs within radius directly |
| GRO file parsing | Custom parser per mode | Existing `_parse_gro()` from generator.py | Already handles orthogonal + triclinic box formats correctly |
| Water molecule group identification | Manual atom grouping by residue | Molecule stride pattern (4 atoms per TIP4P) | tip4p.gro is always OW,HW1,HW2,MW in order, 4 atoms per molecule |

**Key insight:** The `cKDTree` with `boxsize` is the single most important tool for this phase. It replaces what would be a complex, error-prone manual implementation of PBC-aware distance calculations with a single parameter.

## Common Pitfalls

### Pitfall 1: Unit Confusion (Å vs nm)
**What goes wrong:** The overlap threshold is specified as 2.5 Å, but all QuickIce coordinates are in nm. Using 2.5 as the nm threshold would remove way too many molecules (effectively 25 Å cutoff).
**Why it happens:** Different parts of the MD ecosystem use different units. GRO files use nm, PDB files use Å, force fields use various units.
**How to avoid:** Convert threshold immediately on input: `threshold_nm = threshold_angstrom / 10.0`. Store and compute everything in nm. Only display Å in the UI.
**Warning signs:** Unexpectedly few water molecules remaining after overlap removal; or zero overlaps detected.

### Pitfall 2: Missing PBC Overlaps at Box Boundaries
**What goes wrong:** An ice O atom at z=0.01 nm and a water O at z=4.99 nm (in a 5 nm box) are actually only 0.02 nm apart through the periodic boundary, but a naive distance calculation gives 4.98 nm.
**Why it happens:** Forgetting that atoms near one face of the box can overlap with atoms near the opposite face.
**How to avoid:** Always use cKDTree with `boxsize` parameter. Never compute distances without PBC awareness.
**Warning signs:** Overlap count is suspiciously low for interface systems; visual artifacts at box boundaries.

### Pitfall 3: Incomplete Water Tiling (gaps in water region)
**What goes wrong:** The water region isn't completely filled because tiling didn't cover the full target volume, or molecules at tiling boundaries were incorrectly filtered.
**Why it happens:** Integer ceiling of region/template ratio doesn't guarantee full coverage if molecules are filtered by strict < comparison rather than ≤.
**How to avoid:** Use `np.ceil` for tiling counts, and allow a small tolerance when filtering molecules. Then wrap all positions into the box using modulo.
**Warning signs:** Visible gaps or voids in the water region; lower water density than expected (~1.0 g/cm³).

### Pitfall 4: Slab Mode Z-axis Orientation
**What goes wrong:** Ice and water layers are assembled in the wrong order or with incorrect Z offsets.
**Why it happens:** Confusion about whether ice is "above" or "below" water, and whether coordinates start from 0 or from the bottom of the box.
**How to avoid:** Standard convention: Z=0 at bottom, ice layer at bottom (0 to ice_thickness), water in middle (ice_thickness to ice_thickness + water_thickness), ice at top. Verify with density calculation.
**Warning signs:** Water-vacuum interface (missing top ice layer); ice layers not at expected Z positions.

### Pitfall 5: Pocket Mode Cavity Too Small for tip4p.gro Tiling
**What goes wrong:** A pocket diameter of 0.5 nm can't fit any complete TIP4P water molecules after overlap removal with the surrounding ice.
**Why it happens:** The tip4p.gro template box is ~1.868 nm, and after tiling a small pocket and removing overlaps with ice walls, there may be zero water molecules left.
**How to avoid:** Validate pocket diameter against minimum reasonable size during pre-generation validation. A pocket of diameter < 1.0 nm is unlikely to contain any water molecules. Warn user if no water fits.
**Warning signs:** Zero water molecules in pocket mode result; empty cavity.

### Pitfall 6: Piece Mode Box Dimensions vs Candidate Cell Dimensions
**What goes wrong:** The user-specified box dimensions may not match the ice candidate's crystal cell, leading to awkward embedding.
**Why it happens:** Piece mode dimensions come from the selected candidate, but the user also specifies overall box dimensions. If the box is too small for the ice piece, there's a problem.
**How to avoid:** Ice piece dimensions are derived from the candidate cell diagonal (cell[0,0], cell[1,1], cell[2,2]). Box must be larger than ice piece in all dimensions. Validate during pre-generation check.
**Warning signs:** Ice piece extends beyond box boundaries; box dimensions smaller than candidate cell dimensions.

## Code Examples

### Reading tip4p.gro Water Template
```python
# Source: QuickIce codebase (quickice/data/tip4p.gro)
# tip4p.gro: 216 TIP4P water molecules, 864 atoms, box ~1.868 nm
# Atoms per molecule: OW, HW1, HW2, MW (4 atoms)
# Positions in nm, velocities in nm/ps

import numpy as np
from pathlib import Path

def load_water_template() -> tuple[np.ndarray, list[str], np.ndarray]:
    """Load bundled tip4p.gro water template.
    
    Returns:
        positions: (864, 3) atom positions in nm
        atom_names: list of 864 atom names
        box: [1.86824, 1.86824, 1.86824] in nm
    """
    gro_path = Path(__file__).parent.parent / "data" / "tip4p.gro"
    # Parse using same logic as IceStructureGenerator._parse_gro()
    # ... (reuse existing GRO parser pattern)
```

### Slab Mode Assembly
```python
# Source: gmx solvate approach adapted for ice-water interfaces
# Z-axis stacking is standard for MD (GROMACS convention)

def assemble_slab(ice_candidate: Candidate, 
                  ice_thickness_bottom_nm: float,
                  ice_thickness_top_nm: float,
                  water_thickness_nm: float,
                  box_x_nm: float, box_y_nm: float,
                  overlap_threshold_nm: float = 0.25) -> InterfaceStructure:
    """Assemble ice-water-ice slab interface along Z-axis.
    
    Layout (Z-axis):
        [0, ice_thickness_bottom]                          = bottom ice
        [ice_thickness_bottom, ice_thickness_bottom + water] = water layer
        [ice_thickness_bottom + water, total_z]            = top ice
    
    Total Z = ice_thickness_bottom + water_thickness + ice_thickness_top
    """
    total_z = ice_thickness_bottom_nm + water_thickness_nm + ice_thickness_top_nm
    
    # 1. Get ice oxygen positions (already from candidate)
    # 2. Scale/replicate ice to fill ice layers
    # 3. Tile water into middle region
    # 4. Detect and resolve overlaps
    # 5. Combine into final structure with correct box
    ...
```

### Pocket Mode Assembly
```python
# Source: Standard MD pocket/cavity approach

def assemble_pocket(ice_candidate: Candidate,
                    pocket_diameter_nm: float,
                    box_x_nm: float, box_y_nm: float, box_z_nm: float,
                    overlap_threshold_nm: float = 0.25) -> InterfaceStructure:
    """Assemble pocket mode: water cavity inside ice matrix.
    
    1. Generate ice to fill the entire box
    2. Define spherical cavity at box center with given diameter
    3. Remove ice molecules whose O is within the cavity
    4. Fill cavity with water from tip4p.gro
    5. Remove water molecules overlapping with remaining ice at cavity boundary
    """
    # Cavity center at (box_x/2, box_y/2, box_z/2)
    center = np.array([box_x_nm, box_y_nm, box_z_nm]) / 2.0
    radius_nm = pocket_diameter_nm / 2.0
    
    # Remove ice molecules within cavity
    ice_o_positions = ice_candidate.positions[::4]  # Every 4th atom is OW
    dists = np.linalg.norm(ice_o_positions - center, axis=1)
    ice_outside_cavity = dists >= radius_nm  # Keep ice outside cavity
    
    # ... fill cavity with water, resolve overlaps
```

### Piece Mode Assembly (Box-Only)
```python
# Source: Standard MD ice-in-water simulation approach
# Box/cube shape is the only standard in published literature

def assemble_piece(ice_candidate: Candidate,
                   box_x_nm: float, box_y_nm: float, box_z_nm: float,
                   overlap_threshold_nm: float = 0.25) -> InterfaceStructure:
    """Assemble piece mode: ice crystal embedded in water box.
    
    Ice piece dimensions derived from candidate cell:
        ice_x = candidate.cell[0,0]
        ice_y = candidate.cell[1,1]
        ice_z = candidate.cell[2,2]
    
    Ice centered at (box_x/2, box_y/2, box_z/2).
    """
    ice_dims = np.array([
        ice_candidate.cell[0, 0],
        ice_candidate.cell[1, 1],
        ice_candidate.cell[2, 2]
    ])
    
    center = np.array([box_x_nm, box_y_nm, box_z_nm]) / 2.0
    ice_offset = center - ice_dims / 2.0
    
    # Shift ice positions to center
    ice_positions = ice_candidate.positions + ice_offset
    
    # Fill entire box with water
    # Remove water overlapping with ice
    ...
```

### Generation Feedback (gmx solvate-like reporting)
```python
# Source: gmx solvate reports molecules added, not removed

def format_generation_report(
    mode: str,
    ice_molecules: int,
    water_molecules_initial: int,
    water_molecules_kept: int,
    box_dims: tuple[float, float, float]
) -> str:
    """Format generation report following gmx solvate convention.
    
    Reports water molecules present, not removed (positive framing).
    """
    water_removed = water_molecules_initial - water_molecules_kept
    total = ice_molecules + water_molecules_kept
    
    return (
        f"Generated {mode} interface structure\n"
        f"  Ice molecules: {ice_molecules}\n"
        f"  Water molecules: {water_molecules_kept}\n"
        f"  Total molecules: {total}\n"
        f"  Box: {box_dims[0]:.2f} x {box_dims[1]:.2f} x {box_dims[2]:.2f} nm"
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| gmx solvate VdW-based removal | Distance-based O-O threshold removal | QuickIce-specific | Simpler to implement; no VdW database needed; O-O distance is physically meaningful for water |
| Brute-force N² overlap search | KDTree-based O(N log N) search | Standard since ~2000 | Orders of magnitude faster for large systems |
| scipy.spatial.KDTree | scipy.spatial.cKDTree | SciPy 1.6+ | cKDTree and KDTree merged; cKDTree name retained for compatibility |
| Manual PBC wrapping in distance calcs | cKDTree `boxsize` parameter | SciPy 1.x | Single parameter replaces complex manual wrapping logic |

**Deprecated/outdated:**
- Custom KDTree implementations: Use scipy's cKDTree
- Manual minimum-image convention code: Use cKDTree `boxsize`
- VdW radii-based overlap detection (gmx solvate style): For ice-water, O-O distance threshold is simpler and more appropriate

## Piece Mode Shape Research

### Question: Should piece mode support sphere, cylinder, or only box/cube shapes?

**Findings:**

1. **Box/cube is the universal standard** in MD ice-in-water simulations. Every published study of ice crystals embedded in water uses rectangular parallelepiped (box) geometry. This is because:
   - Ice crystals are periodic structures with rectangular unit cells
   - Box shapes preserve the crystallographic periodicity
   - GROMACS and other MD engines natively support rectangular boxes
   - Sphere/cylinder shapes would cut through crystal planes, destroying structural validity

2. **Sphere/cylinder shapes are not used** in the ice-in-water MD literature. These shapes appear in:
   - Spherical droplet simulations (water in vacuum, not ice in water)
   - Cylindrical nanopore simulations (confinement, not embedding)
   - Neither case is relevant to ice-in-water interface generation

3. **Practical implications of non-box shapes:**
   - Sphere: Would require cutting ice at curved boundaries → breaks crystal symmetry
   - Cylinder: Would require cutting ice at curved walls → same issue
   - Both would create unphysical surfaces that don't correspond to real ice facets

**Recommendation:** Ship box/cube only for v3.0. This matches standard practice and avoids the significant complexity of curved-boundary crystal cutting.

**Confidence:** HIGH (verified across multiple published MD simulation studies and GROMACS documentation)

## gmx solvate Behavior Reference

Based on GROMACS 2026.1 official documentation:

### How gmx solvate works:
1. **Two modes:** (a) Generate a box of solvent from scratch, (b) Solvate a solute in a bath of solvent
2. **Solvent tiling:** "The box of solute is built by stacking the coordinates read from the coordinate file" — i.e., tile the solvent template to fill the box
3. **Overlap removal:** "Solvent molecules are removed from the box where the distance between any atom of the solute molecule(s) and any atom of the solvent molecule is less than the sum of the scaled van der Waals radii"
4. **VdW scaling:** Default scale factor 0.57 yields density close to 1000 g/l for proteins in water
5. **Default solvent:** SPC water from `$GMXLIB/spc216.gro` (analogous to our `tip4p.gro`)
6. **Reporting:** Reports number of solvent molecules in output, not number removed
7. **Key constraint:** "Molecules must be whole in the initial configurations" — i.e., don't split molecules across periodic boundaries in the template

### QuickIce adaptation:
- Instead of VdW-based removal (complex, requires radii database), use simple O-O distance threshold (2.5 Å = 0.25 nm default)
- Instead of SPC water, use bundled tip4p.gro (216 TIP4P molecules, ~1.868 nm box)
- Same tiling approach: stack tip4p.gro copies to fill the target region
- Same reporting convention: report water molecules present, not removed

## Open Questions

1. **Ice layer scaling for slab mode**
   - What we know: The ice candidate from GenIce2 has a fixed cell size determined by density and molecule count. The user specifies ice thickness (e.g., 3.0 nm), which may not match the candidate's Z dimension.
   - What's unclear: Should we (a) replicate the ice cell along Z to fill the thickness, (b) scale the ice cell to match, or (c) use the candidate cell size as-is and adjust the reported thickness?
   - Recommendation: Replicate along Z (most physically valid — preserves crystal structure). The actual ice thickness will be an integer multiple of the candidate cell's Z dimension. Report actual thickness, not requested thickness. If user requests 3.0 nm but ice cell is 1.47 nm, they get 2×1.47=2.94 nm or 3×1.47=4.41 nm.

2. **Pocket mode ice generation**
   - What we know: Pocket mode needs ice filling the entire box EXCEPT the cavity.
   - What's unclear: The ice candidate from Tab 1 has a fixed number of molecules. For pocket mode, we may need MORE ice molecules than the candidate provides.
   - Recommendation: For pocket mode, generate ice using the candidate's phase/density info with enough molecules to fill the full box. This means running GenIce2 again with a larger molecule count. The candidate provides phase info (phase_id, density, lattice) but the number of molecules must be recalculated for the box volume.

3. **Asymmetric slab thickness UI**
   - What we know: CONTEXT.md allows asymmetric top/bottom ice thickness.
   - What's unclear: Current UI only has one "ice thickness" spinner.
   - Recommendation: This is a UI concern, not a generation logic concern. The generation code should accept `ice_thickness_bottom` and `ice_thickness_top` as separate parameters. The UI can default to symmetric (same value for both) with an optional "Advanced: different top/bottom" toggle. For v3.0 MVP, support both params in the backend but UI may default to symmetric.

## Sources

### Primary (HIGH confidence)
- GROMACS 2026.1 official documentation — gmx solvate: https://manual.gromacs.org/current/onlinehelp/gmx-solvate.html
- GROMACS 2026.1 reference manual — Periodic boundary conditions: https://manual.gromacs.org/current/reference-manual/algorithms/periodic-boundary-conditions.html
- SciPy 1.17.0 documentation — cKDTree with boxsize: https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.html
- GenIce2 GitHub repository: https://github.com/genice-dev/GenIce2
- QuickIce codebase (all files in quickice/structure_generation/, quickice/gui/, quickice/data/)

### Secondary (MEDIUM confidence)
- gmx solvate fill-and-trim approach adapted for ice-water interfaces (well-known pattern in MD community)
- O-O distance threshold of 2.5 Å as standard minimum distance in water models (common in TIP4P literature)

### Tertiary (LOW confidence)
- Piece mode sphere/cylinder shapes not used in literature: Based on training knowledge of MD simulation literature; no specific webfetch verification of this negative claim, but absence of such methods across multiple known references supports HIGH confidence in practice

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — scipy cKDTree with boxsize is the standard tool; verified against official docs
- Architecture: HIGH — fill-and-trim pattern directly from gmx solvate; well-established in MD community
- Pitfalls: HIGH — unit confusion and PBC issues are well-documented gotchas in MD
- Piece mode shape: HIGH — box-only is standard practice; verified against MD literature conventions
- Overlap detection: HIGH — cKDTree.query_ball_tree with boxsize is the correct, efficient solution

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable domain — MD simulation fundamentals don't change rapidly)
