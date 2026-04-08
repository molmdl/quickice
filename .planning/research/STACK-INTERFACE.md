# Stack Research: Ice-Water Interface Generation for QuickIce

**Project:** QuickIce — Adding Ice-Water Interface Generation  
**Researched:** 2026-04-08  
**Domain:** Molecular simulation structure generation (ice-liquid water interfaces)  
**Confidence:** MEDIUM-HIGH

---

## Executive Summary

Ice-water interface generation requires **building custom functionality** on top of existing GenIce2 capabilities. There is no established Python library specifically for ice-water interface generation—the approach is to:

1. Use **GenIce2** for ice structure generation (already in stack)
2. Generate **liquid water boxes** using classical molecular modeling techniques
3. **Combine** ice + liquid water into a single periodic system using spatial manipulation
4. Export via existing **GROMACS infrastructure** (already implemented)

**No new external libraries are required.** The implementation can use existing NumPy/SciPy for spatial operations and the existing GROMACS export already handles TIP4P-ICE.

---

## Gap Analysis: What GenIce2 Does NOT Provide

| GenIce2 Capability | Interface Generation Need |
|-------------------|---------------------------|
| Generates pure ice structures | Need ice + liquid water combination |
| Supports tip4p, tip3p, tip5p water | Need liquid water (same or different model) |
| Outputs .gro coordinates | Need combined system coordinates |
| Outputs .top topology | Already handled by existing GROMACS writer |

**Key Finding:** GenIce2 has **no built-in interface generation**. This is a custom capability that must be implemented in QuickIce.

---

## Recommended Stack Additions

### Core Approach: Pure Python Implementation

| Component | Version | Purpose | Why |
|-----------|---------|---------|-----|
| **NumPy** | (existing) | Array operations for coordinate manipulation | Already in stack |
| **SciPy** | (existing) | Spatial operations (concave hull for ice-in-water) | Already in stack |
| **MDAnalysis** | >=2.0.0 | Optional: Enhanced molecular structure handling | Only if complexity warrants |

**No new dependencies required.** The interface generation can be implemented using:
- NumPy for coordinate manipulation
- SciPy.spatial for geometric operations
- Existing GenIce2 for ice generation
- Existing GROMACS export for file output

---

## Alternative: MDAnalysis Approach

If the implementation proves complex, MDAnalysis provides molecular structure handling:

| Library | Use Case | Install? |
|---------|----------|----------|
| **MDAnalysis** | Read/write various molecular formats; system manipulation | Optional (only if needed) |
| **GROMACS Python API (gmxapi)** | Direct GROMACS integration | **NOT recommended** — Overkill for structure generation |

**Recommendation:** Start without MDAnalysis. Only add if NumPy/SciPy approach proves insufficient.

---

## Implementation Architecture

### Three Interface Geometry Modes

The milestone specifies three modes that must be implemented:

| Mode | Description | Technical Approach |
|------|-------------|-------------------|
| **Slab** | Flat ice layer with liquid water on both sides | Stack ice slab + water layers in Z direction |
| **Ice-in-Water** | Ice particles embedded in liquid | Generate ice + place in water box using spatial masking |
| **Water-in-Ice** | Liquid water pockets in ice | Inverse of ice-in-water (porous ice structure) |

### Data Flow

```
User Parameters:
  - box_size: (x, y, z) in nm
  - mode: slab | ice-in-water | water-in-ice
  - seed: random seed for ice orientation
  - thickness: ice layer thickness (slab) or ice fraction (dispersed)

         │
         ▼
┌─────────────────────────────────────┐
│  1. Generate Ice Structure          │
│     (GenIce2, existing)             │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  2. Generate Liquid Water Box       │
│     (Custom: regular grid + thermal │
│      disorder)                      │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  3. Combine Systems                 │
│     (NumPy spatial operations)      │
│     - Slab: concatenate in Z        │
│     - Dispersed: random placement   │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  4. Export Combined Structure       │
│     (Existing GROMACS writer)       │
└─────────────────────────────────────┘
```

---

## Technical Details

### Liquid Water Box Generation

**Algorithm (slab mode example):**
```python
def generate_water_box(box_size: tuple, n_molecules: int) -> np.ndarray:
    """Generate liquid water molecules in a box.
    
    Uses simple cubic lattice with thermal displacement.
    For production use, would typically use GROMACS gmx solvate,
    but we need pure Python for GUI integration.
    """
    volume = box_size[0] * box_size[1] * box_size[2]  # nm³
    water_density = 0.997 g/cm³ = 55.5 mol/L
    n_waters = int(water_density * volume * NA)  # molecules needed
    
    # Place on grid with random displacement
    positions = []
    for i in range(n_waters):
        x = random() * box_size[0]
        y = random() * box_size[1]
        z = random() * box_size[2]
        positions.append([x, y, z])
    
    return np.array(positions)
```

### Ice-in-Water Geometry

For dispersed ice-in-water:
1. Generate ice structure (GenIce2)
2. Scale to target box
3. Select random position in water box
4. Use SciPy spatial distance to identify water molecules within ice region
5. Replace those water molecules with ice structure

### Water-in-Ice Geometry

For porous ice with water pockets:
1. Generate ice structure
2. Identify cavities using convex hull or distance-based analysis
3. Mark cavity regions as liquid water
4. Adjust topology to reflect mixed phase regions

---

## Integration with Existing Stack

### Existing Components to Reuse

| Component | Integration Point |
|-----------|-------------------|
| `genice2` | Step 1: Ice structure generation |
| `quickice.output.gromacs_writer` | Step 4: Export combined .gro/.top |
| `quickice.structure_generation.types.Candidate` | Represent combined system |
| NumPy/SciPy | Steps 2-3: Coordinate manipulation |
| VTK | Visualization of combined interface |

### UI Parameter Changes

| Current Input | New Input |
|--------------|-----------|
| `nmol` (number of molecules) | `box_size` (x, y, z in nm) |
| — | `mode` (slab/ice-in-water/water-in-ice) |
| — | `seed` (random seed) |
| — | `thickness` (ice layer or ice fraction) |

---

## What NOT to Add

| Library | Why Avoid | Alternative |
|---------|-----------|-------------|
| **gmxapi** | Complex GROMACS Python bindings; overkill | Use existing GROMACS writer |
| **OpenMM** | MD simulation engine; not needed for structure generation | Pure coordinate generation |
| **HOOMD-blue** | GPU-accelerated MD; not needed | N/A |
| **ase** | Atomic simulation environment; overlaps with existing functionality | NumPy directly |
| **MDAnalysis** (unless needed) | Adds dependency weight; NumPy sufficient for now | Start without |

---

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| No new libraries needed | HIGH | Verified via GenIce2 docs and molecular modeling research |
| Implementation feasibility | HIGH | Standard approach in molecular modeling |
| Geometry modes | MEDIUM | Slab is straightforward; dispersed modes need algorithm development |
| GROMACS export | HIGH | Already implemented and tested |

---

## Sources

### Primary Sources

1. **GenIce2 Documentation** — PyPI genice2 2.2.13.3  
   https://pypi.org/project/genice2/  
   **Finding:** No interface generation; pure ice only

2. **GROMACS Documentation**  
   https://manual.gromacs.org/current/  
   **Finding:** Standard tool for water box generation (gmx solvate)

3. **Molecular Modeling Basics**  
   Water box generation follows standard practices in MD simulations

### Secondary Sources

4. **TIP4P-ICE Parameters** — Already verified in STACK_GROMACS.md  
   Used for liquid water in interface

---

## Roadmap Implications

### Phase Structure Recommendation

1. **Phase 1: Core Infrastructure**
   - Implement liquid water box generator
   - Slab mode (simplest geometry)
   - Combine ice + water into single system
   - Export via existing GROMACS writer

2. **Phase 2: Dispersed Geometries**
   - Ice-in-water mode (particle embedding)
   - Water-in-ice mode (porous structure)
   - Seed-based reproducibility

3. **Phase 3: Polish**
   - VTK visualization of interfaces
   - Parameter validation
   - User testing

### Complexity Rating

| Aspect | Rating | Notes |
|--------|--------|-------|
| Slab interface | 2/5 | Straightforward concatenation |
| Ice-in-water | 3/5 | Spatial placement algorithm |
| Water-in-ice | 4/5 | Cavity detection + replacement |
| GROMACS integration | 1/5 | Already working |
| VTK visualization | 2/5 | Reuse existing viewer |

---

## Open Questions

1. **Water model for liquid:** Should liquid water use TIP4P-ICE (same as ice) or TIP4P (standard liquid)?
   - Recommendation: Use TIP4P-ICE for consistency, or make configurable

2. **Validation approach:** Should interfaces be validated structurally before export?
   - Recommendation: Basic sanity check (no atom overlap)

3. **Box size vs. molecule count:** Replace `nmol` with `box_size` — is this acceptable UI change?
   - Recommendation: Yes, per milestone requirements

---

## Research Complete

**Summary:** Ice-water interface generation requires **custom implementation** using existing tools (GenIce2 + NumPy/SciPy). No new external libraries are needed. The three geometry modes (slab, ice-in-water, water-in-ice) are achievable through coordinate manipulation. Integration with existing GROMACS export is straightforward.

**Recommendation:** Proceed with Pure Python implementation using NumPy/SciPy. Only add MDAnalysis if complexity warrants.

---