# Triclinic Interface Builder - Planning Context

**Created:** 2026-04-13
**Purpose:** Context for replanning triclinic handling - build interfaces with native triclinic cells instead of transforming to orthogonal

---

## Goal

Remove the triclinic-to-orthogonal transformer and instead build interface generation that natively handles triclinic cells. This is scientifically correct and aligns with how crystallography works.

---

## Why This Approach

1. **Tab 1 works perfectly** with original triclinic structure (confirmed by user)
2. **GenIce produces correct triclinic cells** - forcing orthogonal is artificial
3. **GRO format supports triclinic** - 9 box values (v1.x v1.y v1.z v2.x v2.y v2.z v3.x v3.y v3.z)
4. **VTK handles triclinic cells** - via cell matrix transformation
5. **Transformer is a workaround** that has caused 7+ bugs with persistent gaps

---

## Phases Affected

### Triclinic Phases (need native handling):
| Phase | Crystal Form | Cell Angles | GenIce Lattice |
|-------|-------------|-------------|----------------|
| Ice II | Rhombohedral | ~113°, ~113°, ~113° | ice2 |
| Ice V | Monoclinic | 90°, β≠90°, 90° | ice5 |

### Already Orthogonal (no changes needed):
| Phase | Crystal Form | GenIce Lattice |
|-------|-------------|----------------|
| Ice Ih | Hexagonal* | ice1h |
| Ice Ic | Cubic | ice1c |
| Ice III | Tetragonal | ice3 |
| Ice VI | Tetragonal | ice6 |
| Ice VII | Cubic | ice7 |
| Ice VIII | Tetragonal | ice8 |

*Note: Ice Ih is hexagonal but GenIce produces it in an orthogonal supercell representation.

---

## Current Architecture

### What Gets Removed:
```
quickice/structure_generation/
├── transformer.py          # ~300+ lines - DELETE
├── transformer_types.py    # TransformationResult, TransformationStatus - DELETE
└── generator.py            # Remove transform_if_needed() call

tests/
└── test_transformer.py     # DELETE
```

### What Gets Modified:
```
quickice/structure_generation/
├── types.py                # Remove original_positions, original_cell fields
├── modes/
│   ├── slab.py             # Handle triclinic tiling
│   ├── pocket.py           # Handle triclinic tiling
│   └── piece.py            # Handle triclinic tiling
├── tiler.py                # Core tiling logic for triclinic
└── generator.py            # Remove transformer import/call

quickice/gui/
└── molecular_viewer.py     # Simplify - no original_positions handling

quickice/export/
├── gro.py                  # Verify triclinic box output
└── pdb.py                  # Add CRYST1 with angles
```

---

## Key Technical Challenges

### 1. Triclinic Tiling

**Current (orthogonal):**
```python
# Simple offset along axes
for i in range(nx):
    for j in range(ny):
        for k in range(nz):
            offset = i * cell[0] + j * cell[1] + k * cell[2]
```

**Triclinic (needed):**
```python
# Offset along lattice vectors (cell rows)
for i in range(nx):
    for j in range(ny):
        for k in range(nz):
            offset = i * cell[0] + j * cell[1] + k * cell[2]
            # This still works! The cell vectors ARE the lattice vectors
```

**Key insight:** The cell matrix rows ARE the lattice vectors. Tiling works the same way - we just need to track the full cell matrix, not just diagonal.

### 2. Triclinic PBC Wrapping

**Orthogonal:**
```python
wrapped = pos % cell_diagonal
```

**Triclinic:**
```python
# Fractional coordinates
inv_cell = np.linalg.inv(cell.T)
frac = pos @ inv_cell
frac_wrapped = frac % 1.0
wrapped = frac_wrapped @ cell.T
```

### 3. Cell Extent Calculation

**Orthogonal:**
```python
extent = [cell[0,0], cell[1,1], cell[2,2]]
```

**Triclinic:**
```python
# Bounding box of parallelepiped
corners = np.array([
    [0, 0, 0],
    cell[0],
    cell[1],
    cell[2],
    cell[0] + cell[1],
    cell[0] + cell[2],
    cell[1] + cell[2],
    cell[0] + cell[1] + cell[2]
])
extent = corners.max(axis=0) - corners.min(axis=0)
```

---

## GRO Triclinic Format

GRO files support triclinic cells with 9 values on the last line:

```
   v1.x    v2.y    v3.z    v1.y    v1.z    v2.x    v2.z    v3.x    v3.y
```

Where:
- v1, v2, v3 are the cell vectors (in nm)
- v1.x v1.y v1.z = first lattice vector
- v2.x v2.y v2.z = second lattice vector
- v3.x v3.y v3.z = third lattice vector

**Current code already has this:**
```python
# In gro.py export
if len(box_dimensions) == 9:
    # Triclinic box format
```

---

## PDB CRYST1 Format

PDB requires CRYST1 record with cell parameters:

```
CRYST1   a      b      c    alpha  beta   gamma sgroup  z
```

For triclinic:
- a, b, c = vector lengths
- alpha, beta, gamma = angles between vectors (degrees)

---

## Interface Generation Modes

### Slab Mode:
- Ice at bottom, water in middle, ice at top (sandwich)
- Need to position layers correctly in triclinic cell
- Z-axis stacking should work with cell[2] vector

### Pocket Mode:
- Ice surrounds water pocket
- Need triclinic-aware spatial selection
- Position water molecules inside ice cell

### Piece Mode:
- Ice piece placed in box
- Need triclinic cell placement
- Box sizing for triclinic cells

---

## Verification Approach

### Tests to Add:
1. Triclinic slab generation (Ice II, Ice V)
2. Triclinic pocket generation
3. Triclinic piece generation
4. GRO export with triclinic box
5. PDB export with CRYST1 angles
6. Visualization of triclinic in Tab 2

### Manual Verification:
1. Generate Ice II interface in slab mode
2. Check no gaps in structure
3. Export to GRO, verify 9 box values
4. Load in VMD/PyMOL to verify structure

---

## Files to Review

### Understanding Current Tiling:
- `quickice/structure_generation/modes/slab.py`
- `quickice/structure_generation/modes/pocket.py`
- `quickice/structure_generation/modes/piece.py`
- `quickice/structure_generation/tiler.py`

### Understanding Export:
- `quickice/export/gro.py` - lines for triclinic box
- `quickice/export/pdb.py` - CRYST1 record

### Understanding Candidate:
- `quickice/structure_generation/types.py`

---

## Success Criteria

1. Ice II and Ice V generate correct interfaces without gaps
2. GRO export has 9 box values for triclinic phases
3. PDB export has correct CRYST1 record
4. Tab 2 displays triclinic structure correctly
5. No transformer code remains
6. All tests pass

---

## Estimated Scope

**Major components:**
1. Remove transformer (~1 plan)
2. Update interface builder for triclinic (~2-3 plans)
3. Update export for triclinic (~1 plan)
4. Update viewer handling (~1 plan)
5. Documentation updates (~1 plan)

**Total: ~6-7 plans across multiple phases**
