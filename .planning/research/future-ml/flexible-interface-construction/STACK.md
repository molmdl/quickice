# Technology Stack: Flexible Interface Construction

**Project:** QuickIce — Flexible Interface Extension
**Researched:** 2026-06-12

## Recommended Stack

### Interface Building Technology
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| GenIce2 `raw` format | 2.2.13.1 | Extract fractional coordinates + cell + cage positions for reassembly | Only way to get `reppositions` (fractional), `repcell`, `repcagepos`, `repcagetype` without GRO round-trip loss |
| GenIce2 `shift` parameter | (in GenIce2) | Shift ice slab origin in fractional coordinates | Enables Z-position control of ice slab within cell; already supported in GenIce2 `__init__` |
| GenIce2 `reshape` matrix | (3x3 integer) | Create non-cubic supercells with arbitrary lattice reorientation | Allows asymmetric replication (e.g., 2×3×5) and basal-plane rotation via non-diagonal matrices |
| numpy | 2.4.3 | Coordinate manipulation, matrix operations | Already in stack; needed for fractional-to-absolute coordinate transforms |
| scipy | 1.17.1 | Spatial distance calculations for overlap detection | Already in stack; KDTree for efficient overlap detection in multi-layer assembly |

### Alternative Format: Raw vs Gromacs
| Approach | Advantages | Disadvantages |
|----------|-----------|---------------|
| **Raw format (recommended)** | Direct access to fractional coordinates, cell matrix, cage positions, rotation matrices; no GRO parsing loss; stage-selective output | Requires custom code to convert fractional→absolute; no atom names (just positions); GenIce2 internal data structures are the source of truth |
| Gromacs format (current) | Already implemented; includes atom names, residue names; GRO parsing works | Position precision loss (3 decimal places in GRO = 0.001 nm); requires wrapping/unwrapping; loses cage metadata; round-trip through string serialization |

## GenIce2 API Capability Matrix

| Capability | GenIce2 Support | QuickIce Uses | Gap for Flexible Interface |
|-----------|-----------------|---------------|---------------------------|
| `shift=(x,y,z)` | YES — fractional shift added to waters1 (line 560 genice.py) | NOT used | CRITICAL: Can shift ice slab origin; values are fractional [0,1); wraps with `-= np.floor` |
| `reshape` (3×3 integer) | YES — any integer matrix (line 410-525 genice.py) | Diagonal only (n×n×n) via `calculate_supercell()` | Can create non-cubic supercells; can rotate crystal axes via non-diagonal reshape |
| `rep=(nx,ny,nz)` | DEPRECATED — warned to use reshape instead (line 461) | NOT used directly | Use `reshape=np.diag([nx,ny,nz])` instead |
| `density` parameter | YES — scales cell to match target density (line 617-627) | YES — passed via `self.density` | Already works; density scaling applies uniformly to entire cell |
| `noise` parameter | YES — `generate_ice(noise=X)` adds Gaussian perturbation (line 814-821) | NOT used | Could add interface roughness; noise is in percent of water radius (0.5×radius × 0.01 × noise) |
| `asis` parameter | YES — preserves HB orientations from lattice | NOT used | N/A for interface construction |
| `guests` parameter | YES — cage-specific guest placement (line 1052-1079) | YES — via `parse_guest()` in hydrate_generator | Already works per-cage-type |
| `spot_guests` | YES — cage-specific manual guest placement (line 1045-1049) | NOT used | Could place guests at specific cage indices |
| `cations`/`anions` | YES — replace water molecules with ions | NOT used (ions added post-generation) | N/A |
| `target_polarization` | YES — depolarization target vector (line 953) | NOT used | Could control net dipole of ice slab |
| Raw format output | YES — stage-selective data extraction (raw.py) | NOT used (uses Gromacs format) | CRITICAL: Provides `reppositions`, `repcell`, `repcagepos`, `rotmatrices`, `mols` at each stage |
| Python format output | YES — generates a Python lattice plugin (python.py) | NOT used | Useful for creating custom lattices from existing structures |

### Coordinate Manipulation

#### `shift=(x, y, z)` — Fractional Origin Shift
**GenIce2 source (genice.py lines 559-562):**
```python
# shift of the origin
self.waters1 += np.array(shift)
# fractional coordinate between [0, 1)
self.waters1 -= np.floor(self.waters1)
```

**Key findings:**
- Values are **fractional** (not absolute nm). `shift=(0.0, 0.0, 0.5)` shifts all water molecules to Z=0.5 in fractional space
- After shift, positions are wrapped into [0, 1) via `np.floor` subtraction
- Cage positions (`cagepos1`) are also shifted (line 644): `self.cagepos1 = np.array(self.cagepos1) + np.array(shift)`
- **For flexible interface:** `shift` can place the ice origin at any fractional position within the cell. This is ideal for shifting an ice slab to a specific Z position

**Limitations:**
- Shift applies to ALL molecules uniformly — cannot shift different molecules to different positions
- Shift is in fractional coordinates, not absolute nm. Must convert using `cell.rel2abs()` for absolute positioning
- Shift happens BEFORE replication — so the entire replicated supercell is shifted

#### `reshape` (3×3 integer matrix) — Supercell Shape Control
**GenIce2 source (genice.py lines 473-525):**

The reshape matrix defines how the unit cell is tiled to form the supercell. Each row of the reshape matrix defines a lattice vector of the supercell in terms of unit cell lattice vectors.

**Key findings:**
- **Diagonal reshape** (current QuickIce usage): `np.diag([n, n, n])` creates n×n×n cubic supercell
- **Asymmetric reshape**: `np.array([[2,0,0],[0,3,0],[0,0,5]])` creates 2×3×5 supercell
- **Non-diagonal reshape**: `np.array([[1,1,1],[1,-1,0],[1,1,-2]])` creates a rotated/oriented supercell
  - This can rotate the basal plane to be along Z (important for Ice Ih where GenIce's default has basal plane on X)
- Determinant of reshape matrix = number of unit cells in supercell
- GenIce2 computes which replica vectors are needed to fill the supercell (lines 490-518)
- **For flexible interface:** Asymmetric reshape allows different thicknesses in X, Y, Z without wasting molecules

**Constraints:**
- Must be a 3×3 integer matrix
- Determinant must be positive (|det| = number of unit cells)
- GROMACS format has restrictions on cell shape (lower-triangular convention for triclinic)

#### `rep=(nx, ny, nz)` — Deprecated Repetition
**GenIce2 source (genice.py lines 460-472):**
- `rep` is deprecated in favor of `reshape`
- When used, it creates `reshape = np.diag(rep)` internally
- **Use `reshape` instead** for all new code

#### `density` Parameter — Target Density
**GenIce2 source (genice.py lines 598-627):**
- If `density <= 0`, uses lattice's default density
- Scales cell vectors by `ratio = (density0 / self.density) ** (1/3)` (line 623)
- This scales the entire cell uniformly
- **For flexible interface:** Already used correctly in QuickIce. Cannot independently scale different parts of the structure.

#### `noise` Parameter — Position Perturbation
**GenIce2 source (genice.py lines 814-821):**
```python
if noise > 0.0:
    perturb = np.random.normal(
        loc=0.0, scale=noise * 0.01 * 3.0 * 0.5,  # in percent, radius of water
        size=self.reppositions.shape,
    )
    self.reppositions += self.repcell.abs2rel(perturb)
```
- `noise` is in percent of water molecule radius (≈0.15 nm)
- Perturbation is in **absolute** coordinates, then converted to fractional
- **For flexible interface:** Could add interface roughness, but this perturbs ALL molecules, not just interface ones

### Raw Format Extraction

#### Available Data by Stage

| Stage | Variable | Type | Description | Use for Flexible Interface |
|-------|----------|------|-------------|---------------------------|
| 1 | `reppositions` | (N, 3) float | Fractional coordinates of water molecules in replicated cell | **YES** — extract ice slab positions, place at arbitrary Z |
| 1 | `repcell` | Cell object | Shape matrix of replicated cell | **YES** — need cell for fractional→absolute conversion |
| 1 | `repcagetype` | list[str] | Cage type labels | **YES** — identify which cages to fill with which guests |
| 1 | `repcagepos` | (M, 3) float | Fractional coordinates of cage centers | **YES** — extract cage positions independently for hydrate reassembly |
| 1 | `cagetypes` | dict | Set of cage type IDs | Useful for guest placement |
| 5 | `rotmatrices` | (N, 3, 3) float | Rotation matrices for water molecules | **YES** — needed if reconstructing atomic positions from CoM + rotations |
| 6 | `mols` | list[SimpleNamespace] | Serialized molecule data (resname, atomnames, positions, orig_order) | **YES** — full atomic positions in absolute nm |

**CRITICAL: Coordinate System**
- `reppositions` are **fractional coordinates** (relative to repcell)
- To convert to absolute nm: `abs_pos = fractional_pos @ repcell.mat`
- To convert back: `frac_pos = abs_pos @ repcell.inv`
- This is defined in `Cell.rel2abs()` and `Cell.abs2rel()` (cell.py lines 69-72)

**Extraction strategy for flexible interface:**
1. Use `raw` format with `stages=[1]` to get `reppositions`, `repcell`, `repcagepos`
2. Convert `reppositions` to absolute coordinates
3. Shift, rotate, or split the positions as needed for interface assembly
4. Convert back to fractional if needed for further GenIce2 processing

**Can we extract just the ice slab coordinates and place them at arbitrary Z?**
**YES** — with high confidence (code-verified):
1. Get `reppositions` (fractional) and `repcell` from raw format
2. Convert to absolute: `abs_positions = reppositions @ repcell.mat`
3. Z-select molecules in desired slab range
4. Shift Z of selected molecules to target position
5. Reassemble with water filler in the gap

**Can we extract cage positions for hydrate structures independently?**
**YES** — with high confidence (code-verified):
- `repcagepos` contains fractional coordinates of all cage centers
- `repcagetype` identifies cage types (small "12" vs large "14"/"16")
- These can be used to place guest molecules at specific cage positions
- Current QuickIce already separates guests from framework (slab.py lines 188-203)

### Multi-Structure GenIce2 Calls

#### Can we call GenIce2 twice with different lattices and merge?
**YES, with caveats** (MEDIUM confidence — code-verified, integration not tested):

1. **Separate GenIce2 instances:** Each call creates a new `GenIce(lattice, ...)` instance with its own cell and positions. There is no shared state between instances (confirmed by reading genice.py `__init__`).

2. **`safe_import` can load different lattices:** `safe_import('lattice', 'CS1')` and `safe_import('lattice', 'CS2')` are independent module imports. Python's import system caches them, but calling `.Lattice()` on each returns a fresh instance.

3. **Cell dimension mismatch:** Different hydrate types have different cell dimensions:
   - sI: 12.24 Å cubic
   - sII: 17.31 Å cubic  
   - sH: 12.26 Å (hexagonal)
   
   **Solution:** After generating each structure separately, convert to absolute coordinates, then place each in the target region of the simulation box. The `tile_structure()` function already handles placing structures of different dimensions into a target region.

4. **AnalIce cannot analyze a combined structure:** `AnalIce` extends `GenIce` and requires a single lattice as input. It's designed for analyzing structures that conform to a single crystal lattice. It CANNOT handle merged multi-lattice structures.

5. **Graph/topology incompatibility:** Each GenIce2 instance generates its own hydrogen bond network (directed graph). Merging graphs from different lattices is non-trivial because edge indices refer to different position arrays.

**Recommendation:** Generate each crystal type independently, extract absolute coordinates via raw format, then assemble using QuickIce's existing `tile_structure()` + overlap detection pipeline.

#### Can we combine ice + hydrate in the same system?
**YES, but not via a single GenIce2 call** (HIGH confidence — code-verified):

GenIce2 is fundamentally a single-lattice generator. It generates ONE crystal structure per call. To get ice + hydrate:
1. Call GenIce2 for ice (e.g., `ice1h`) with TIP3P
2. Call GenIce2 for hydrate (e.g., `CS1`) with TIP4P
3. Extract absolute coordinates from each
4. Place each in its designated region of the simulation box
5. Fill remaining space with water
6. Remove overlapping molecules

This is exactly what QuickIce's existing pipeline does for hydrate→interface, but would need extension for multi-source assembly.

## Current Code Analysis

### slab.py Z-Stacking Implementation

**Current structure (HARDCODED):**
```
Z = [0, ice_thickness]                          → Bottom ice
Z = [ice_thickness, ice_thickness + water_thickness] → Water
Z = [ice_thickness + water_thickness, box_z]     → Top ice
```

**How it works (slab.py):**
1. Bottom ice: `tile_structure()` fills `[box_x, box_y, ice_thickness]` starting at Z=0 (line 270-277)
2. Top ice: Same tile call, then Z-shift by `+= ice_thickness + water_thickness` (line 293)
3. Water: `fill_region_with_water()` fills `[box_x, box_y, water_thickness]`, then Z-shift by `+= ice_thickness` (line 345)
4. Validation enforces: `box_z = 2 * ice_thickness + water_thickness` (interface_builder.py line 125)

**What's hardcoded:**
- The order is always: bottom-ice → water → top-ice
- Both ice layers have identical thickness (`ice_thickness`)
- The Z-positioning is done with fixed offsets
- The validation formula `box_z = 2*ice_thickness + water_thickness` is hardcoded

**What's parameterized (and can be reused):**
- `tile_structure()` is fully generic — can tile any structure into any rectangular region
- `fill_region_with_water()` is fully generic — fills any region with TIP4P water
- `detect_overlaps()` + `remove_overlapping_molecules()` are fully generic
- Z-shifting is done with simple addition (`positions[:, 2] += offset`) — trivially generalizable
- The hydrate guest separation logic (`_detect_guest_atoms()`) is reusable

**What would need to change for ice-on-bottom vs ice-on-top:**
- **MINIMAL change:** The only difference is which layer gets Z-shifted. Currently:
  - Bottom ice: no shift (starts at Z=0)
  - Water: shift by `ice_thickness`
  - Top ice: shift by `ice_thickness + water_thickness`
  
  For "water-on-bottom, ice-on-top" (single ice slab with water below):
  - Water: no shift (starts at Z=0)
  - Ice: shift by `water_thickness`
  
  This is a trivial parameterization — define a `LayerSpec` with type and thickness, compute cumulative offsets.

### InterfaceConfig Schema

**Current fields (types.py lines 152-181):**
```python
@dataclass
class InterfaceConfig:
    mode: str                          # "slab", "pocket", "piece"
    box_x: float                      # nm
    box_y: float                      # nm
    box_z: float                      # nm
    seed: int                         # random seed
    ice_thickness: float = 0.0        # nm (slab only)
    water_thickness: float = 0.0       # nm (slab only)
    pocket_diameter: float = 0.0      # nm (pocket only)
    pocket_shape: str = "sphere"      # pocket only
    overlap_threshold: float = 0.25   # nm
```

**Needed additions for flexible interface:**

| New Field | Type | Purpose | Default |
|-----------|------|---------|---------|
| `layer_order` | `list[str]` | Ordered list of layer types, e.g., `["ice", "water", "ice"]` | `["ice", "water", "ice"]` (backward compat) |
| `layer_thicknesses` | `list[float]` | Thickness of each layer in nm | Derived from `ice_thickness`/`water_thickness` for backward compat |
| `candidates` | `list[Candidate]` | Multiple crystal candidates (one per ice/hydrate layer) | `None` (single candidate, backward compat) |
| `layer_candidates` | `dict[int, Candidate]` | Map layer index to candidate (for multi-type) | `None` |
| `z_offset` | `float` | Global Z offset for ice slab placement | `0.0` |
| `noise` | `float` | Position noise for interface roughness (GenIce2 `noise`) | `0.0` |
| `reshape` | `np.ndarray` | Custom reshape matrix (non-cubic supercell) | `None` (use `calculate_supercell()`) |

**Backward compatibility strategy:**
- If `layer_order` is not set, derive from `mode`: slab→`["ice","water","ice"]`, pocket→single ice, piece→single ice
- If `layer_thicknesses` is not set, derive from `ice_thickness`/`water_thickness`
- If `candidates` is a single Candidate, use it for all ice/hydrate layers

### Generalization Points

**Architecture recommendation: Layer-based assembly engine**

The current slab.py has significant code duplication between bottom/top ice tiling. The natural generalization is a **layer assembly pipeline**:

```python
@dataclass
class LayerSpec:
    """One layer in the interface stack."""
    layer_type: str          # "ice", "hydrate", "water", "vacuum"
    thickness: float         # nm
    source: Candidate | None # Crystal source (ice/hydrate only)
    z_start: float           # Computed: Z position in box
    z_end: float             # Computed: Z position in box

def assemble_layers(
    layers: list[LayerSpec],
    box_dims: np.ndarray,
    overlap_threshold: float,
    seed: int,
) -> InterfaceStructure:
    """Generic layer-by-layer assembly."""
    ...
```

This replaces the hardcoded Z-stacking with a configurable layer stack:
- `["ice", "water"]` → ice on bottom, water on top (single interface)
- `["water", "ice", "water"]` → ice in middle (piece-like)
- `["ice1", "water", "ice2"]` → two different ice types
- `["hydrate_sI", "water", "ice"]` → hydrate + ice
- `["ice", "water", "ice"]` → current slab mode (backward compat)

**Key refactoring steps:**
1. Extract layer-independent logic from slab.py into `layer_assembly.py`
2. Replace hardcoded bottom/top ice tiling with a loop over `LayerSpec`
3. Keep overlap detection and removal as-is (already generic)
4. Keep guest molecule handling as-is (already separated from framework)

## Water Model Considerations

### TIP3P vs TIP4P Coexistence

**Current approach:**
- Ice generated with TIP3P (3 atoms: O, H, H) via `safe_import('molecule', 'tip3p')`
- Hydrate generated with TIP4P (4 atoms: OW, HW1, HW2, MW) via `safe_import('molecule', 'tip4p')`
- Liquid water uses TIP4P template (`tip4p.gro`, 4 atoms per molecule)
- At GROMACS export, TIP3P ice atoms are **normalized to TIP4P-ICE** (3→4 atoms by adding MW virtual site)

**Can different water models coexist in the same simulation box?**

**GROMACS perspective (MEDIUM confidence — standard MD practice):**
- GROMACS requires all molecules of the same `[moleculetype]` to be identical
- If ice and water both use the same moleculetype name "SOL" with TIP4P-ICE, they CAN coexist — they're the same model
- If you want TIP3P ice + TIP4P water in the same box, you need TWO different moleculetypes in the `.top` file:
  ```
  [ moleculetype ]
  ; SOL_TIP3P   3
  O    1  ...
  H    2  ...
  H    3  ...
  
  [ moleculetype ]  
  ; SOL_TIP4P   4
  OW   1  ...
  HW1  2  ...
  HW2  3  ...
  MW   4  ...
  ```
- This is technically possible but **NOT recommended** for production MD because:
  1. Different geometries create discontinuities at the interface
  2. Different charge distributions cause artifacts
  3. Most MD practitioners normalize all water to a single model

**Current QuickIce approach is correct:** Normalize TIP3P ice → TIP4P-ICE at export. This ensures uniform water model throughout the box.

**For multi-structure (ice + hydrate):**
- Ice: TIP3P (from GenIce2) → normalized to TIP4P-ICE at export
- Hydrate: Already TIP4P → no conversion needed
- Liquid water: Already TIP4P → no conversion needed
- **Result:** ALL water molecules are TIP4P-ICE in the exported system. ✓

**For mixed hydrate types (sI + sII):**
- Both use TIP4P water framework → same water model
- Guests may differ (CH4 in sI, THF in sII) → different moleculetypes, but that's standard
- **Result:** Water framework is uniform. Guest moleculetypes differ (CH4 vs THF). ✓

### Force Field Implications

| Scenario | Water Model | Guest Model | Compatible? |
|----------|------------|-------------|-------------|
| Pure ice slab | TIP4P-ICE (normalized) | None | ✓ Standard |
| Hydrate sI (CH4) | TIP4P-ICE | CH4 (GAFF/GAFF2) | ✓ Standard |
| Ice + hydrate | TIP4P-ICE (all normalized) | CH4 or THF (GAFF/GAFF2) | ✓ Requires careful cross-terms |
| sI + sII mixed | TIP4P-ICE (uniform) | Multiple guest types | ✓ Standard practice |
| TIP3P ice + TIP4P water (unnormalized) | TWO water models | — | ⚠ NOT recommended — interface artifacts |

## Recommendation

### Primary Approach: Layer-Based Assembly with Raw Format Extraction

**Why this approach:**
1. **Raw format eliminates GRO round-trip loss** — Fractional coordinates have full float precision; GRO has 0.001 nm resolution. For multi-layer assembly, precision matters.

2. **Layer-based assembly naturally generalizes the existing code** — Current slab.py is essentially a hardcoded 3-layer assembly. The layer engine just makes the loop explicit.

3. **`shift` parameter provides origin control** — GenIce2's built-in `shift` parameter can position the ice origin in fractional space, useful for Z-placement without manual coordinate manipulation.

4. **`reshape` enables asymmetric supercells** — Currently QuickIce only uses `n×n×n` diagonal reshape. Asymmetric reshape allows different X/Y/Z replication, matching interface geometry requirements (wide but thin slabs, etc.).

5. **Multi-structure is independent GenIce2 calls** — Don't try to merge within GenIce2. Generate each crystal independently, extract positions, assemble in QuickIce.

### Implementation Roadmap

**Phase 1: Generalize Z-stacking** (smallest change, highest impact)
- Add `layer_order: list[str]` to `InterfaceConfig`
- Refactor `assemble_slab()` to iterate over layers instead of hardcoding bottom/top
- Support `["ice", "water"]` (single interface) and `["water", "ice", "water"]`
- Keep backward compatibility via `layer_order` defaults

**Phase 2: Add raw format extraction**
- Use GenIce2 `raw` format (stage 1) to get fractional coordinates + cell
- Implement fractional→absolute conversion using `repcell.mat`
- Extract cage positions for hydrate reassembly
- This replaces GRO string parsing with direct data extraction

**Phase 3: Multi-source support**
- Accept `list[Candidate]` in `InterfaceConfig` (one per ice/hydrate layer)
- Assign different candidates to different layers in the stack
- Handle different cell dimensions via per-layer tiling
- Support sI + sII mixed hydrate systems

**Phase 4: Asymmetric reshape + noise**
- Expose `reshape` matrix in `InterfaceConfig` (or derive from target box dimensions)
- Add `noise` parameter for interface roughness
- Add `shift` parameter for origin placement control

### Anti-Pattern: Don't Modify GenIce2

GenIce2 is a third-party library. Don't fork or modify it. Instead:
- Use its API as-is (GenIce2 API is stable and well-documented in source)
- Extract data via raw format
- Do all assembly in QuickIce

## Sources

| Source | URL/Path | Confidence | Notes |
|--------|----------|------------|-------|
| GenIce2 genice.py source | `/share/home/nglokwan/miniconda3/envs/quickice/lib/python3.14/site-packages/genice2/genice.py` | HIGH | Read full file (1202 lines); all API parameter analysis based on actual source |
| GenIce2 raw.py format | Same site-packages path | HIGH | Read full file; confirms stage-selective data extraction API |
| GenIce2 cell.py | Same site-packages path | HIGH | Read full file; confirms fractional↔absolute conversion API |
| GenIce2 plugin.py | Same site-packages path | HIGH | Read full file; confirms safe_import mechanism |
| GenIce2 gromacs.py format | Same site-packages path | HIGH | Read full file; confirms GRO output format |
| GenIce2 molecules/__init__.py | Same site-packages path | HIGH | Read full file; confirms arrange/serialize mechanism |
| GenIce2 CS1.py lattice | Same site-packages path | HIGH | Read partial; confirms cage/water positions in absolute coords |
| GenIce2 ice1h.py lattice | Same site-packages path | HIGH | Read full; confirms waters in absolute coords |
| QuickIce slab.py | `quickice/structure_generation/modes/slab.py` | HIGH | Read full (641 lines); Z-stacking analysis based on actual code |
| QuickIce pocket.py | `quickice/structure_generation/modes/pocket.py` | HIGH | Read full (598 lines); cavity creation analysis |
| QuickIce piece.py | `quickice/structure_generation/modes/piece.py` | HIGH | Read full (385 lines); centering analysis |
| QuickIce types.py | `quickice/structure_generation/types.py` | HIGH | Read full (722 lines); all data structures analyzed |
| QuickIce interface_panel.py | `quickice/gui/interface_panel.py` | HIGH | Read full (935 lines); UI configuration analyzed |
| QuickIce interface_builder.py | `quickice/structure_generation/interface_builder.py` | HIGH | Read full (354 lines); validation and routing analyzed |
| QuickIce water_filler.py | `quickice/structure_generation/water_filler.py` | HIGH | Read full (687 lines); tiling and water fill analyzed |
| QuickIce cell_utils.py | `quickice/structure_generation/cell_utils.py` | HIGH | Read full; orthogonal cell check analyzed |
| QuickIce generator.py | `quickice/structure_generation/generator.py` | HIGH | Read full; GenIce2 API call pattern analyzed |
| QuickIce hydrate_generator.py | `quickice/structure_generation/hydrate_generator.py` | HIGH | Read full; hydrate generation and TIP4P usage analyzed |
| QuickIce mapper.py | `quickice/structure_generation/mapper.py` | HIGH | Read full; supercell calculation analyzed |
| GenIce2 GitHub | https://github.com/vitroid/GenIce → redirects to genice-dev/GenIce2 | LOW | Page confirms project moved; no detailed API docs found on web |
| GROMACS water model coexistence | Training knowledge | MEDIUM | Standard MD practice; TIP3P/TIP4P coexistence is possible but not recommended |
