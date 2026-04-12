# Phase 24: Triclinic Transformation Service - Research

**Researched:** 2026-04-12
**Domain:** Crystallographic cell transformation, numpy implementation
**Confidence:** HIGH (verified with GenIce output, crystallographic conventions)

## Summary

Phase 24 enables interface generation for triclinic ice phases (Ice II, V) that are currently rejected by the orthogonal-only validation in piece.py and interface_builder.py. The transformation converts triclinic unit cells to orthogonal supercells while preserving crystal structure integrity (density, coordination, bond lengths).

**Key findings:**
1. Two ice phases require transformation: Ice II (rhombohedral, α=β=γ≈113°) and Ice V (monoclinic, β≈109°)
2. Six ice phases are already orthogonal: Ih, Ic, III, VI, VII, VIII
3. The transformation uses integer supercell matrices that preserve density
4. Existing code has validation at two locations that must be updated

**Primary recommendation:** Implement a `TriclinicTransformer` service that detects triclinic cells, finds appropriate orthogonal supercell transformations, and validates the result.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | 2.x | Matrix operations for cell transformation | Already in use, sufficient for transformation |
| spglib | 2.7.0 | Crystallographic symmetry analysis | Available, provides cell standardization |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| GenIce2 | current | Ice structure generation | Already generates triclinic cells correctly |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom transformation | ASE Cell.niggli_reduce() | ASE not currently in project; adds dependency |
| Custom transformation | spglib.standardize_cell() | Returns conventional cell, may still be triclinic |

**No new dependencies needed.** Numpy is sufficient for the transformation math.

## Architecture Patterns

### Recommended Service Structure
```
quickice/
├── structure_generation/
│   ├── transformer.py          # NEW: TriclinicTransformer class
│   ├── transformer_types.py    # NEW: TransformationResult dataclass
│   └── ...
```

### Pattern 1: Detection + Transformation + Validation
**What:** Three-step pipeline for handling triclinic cells
**When to use:** Always when a candidate is generated
**Example:**
```python
# Source: Established crystallographic practice
class TriclinicTransformer:
    ANGLE_TOL_DEG = 0.1  # From CONTEXT.md decision
    
    def transform_if_needed(self, candidate: Candidate) -> Candidate:
        if not self.is_triclinic(candidate.cell):
            return candidate  # Already orthogonal, no-op
        
        transformation = self.find_orthogonal_supercell(candidate.cell)
        new_positions, new_cell = self.apply_transformation(
            candidate.positions, candidate.cell, transformation.H
        )
        self.validate_transformation(candidate, new_positions, new_cell)
        return Candidate(..., positions=new_positions, cell=new_cell, ...)
```

### Pattern 2: Transformation Matrix Application
**What:** Apply integer matrix transformation to cell and positions
**Example:**
```python
# Source: Crystallographic supercell transformation
def apply_transformation(positions: np.ndarray, cell: np.ndarray, H: np.ndarray) -> tuple:
    """
    Transform triclinic cell to orthogonal supercell.
    
    H is a 3x3 integer matrix with det(H) > 0.
    new_cell = H @ cell
    
    Positions are transformed via fractional coordinates:
    frac_pos = positions @ inv(cell.T)
    new_pos = frac_pos @ new_cell.T  (or replicate for supercell)
    """
    new_cell = H @ cell
    
    # Convert to fractional coordinates
    cell_inv_T = np.linalg.inv(cell.T)
    frac_positions = positions @ cell_inv_T
    
    # For supercell, positions need to be replicated
    # This is handled by the caller based on transformation type
    
    return new_positions, new_cell
```

### Anti-Patterns to Avoid

- **Bounding box approach without replication**: Simply wrapping positions to bounding box changes density (volume increases, atom count stays same). This is INVALID for crystallography.
- **Assuming diagonal cell matrix**: Code like `cell[0,0], cell[1,1], cell[2,2]` fails for triclinic cells where off-diagonal elements are non-zero.
- **Ignoring transformation matrix**: Any coordinate operation must account for the cell shape.

## Don't Hand-Roll

Problems that look simple but have established solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cell angle calculation | Manual dot products | Established formula with np.clip for numerical stability | Edge cases at 0° and 180° |
| Fractional coordinates | Manual matrix solve | positions @ np.linalg.inv(cell.T) | Handles singular matrices properly |
| Wrapping positions | Manual modulo | frac_pos % 1.0 | Correct handling of negative values |

**Key insight:** The transformation math is straightforward numpy operations. The complexity is in:
1. Finding the correct transformation matrix H for each cell type
2. Properly replicating atoms for the supercell
3. Validating that the transformation preserved structure

## Common Pitfalls

### Pitfall 1: Density Loss from Bounding Box
**What goes wrong:** Converting triclinic to bounding box without replication changes density
**Why it happens:** Bounding box volume > triclinic cell volume, but atom count unchanged
**How to avoid:** Always use supercell transformation (integer matrix H) that preserves volume ratio = det(H)
**Warning signs:** Volume ratio between new_cell and old_cell ≠ det(H)

### Pitfall 2: Incorrect ice_dims Extraction
**What goes wrong:** Using `np.diag(cell)` for ice piece dimensions
**Why it happens:** Triclinic cells have off-diagonal elements; diagonal gives wrong dimensions
**How to avoid:** Calculate bounding box extent or use cell vector norms
```python
# WRONG for triclinic:
ice_dims = np.array([cell[0,0], cell[1,1], cell[2,2]])

# CORRECT:
def get_cell_extent(cell):
    a, b, c = cell[0], cell[1], cell[2]
    corners = np.array([a, b, c, a+b, a+c, b+c, a+b+c, [0,0,0]])
    return corners.max(axis=0) - corners.min(axis=0)
```

### Pitfall 3: Breaking piece.py Validation
**What goes wrong:** Transformation succeeds but piece.py validation still rejects
**Why it happens:** Validation happens at multiple points; all must be updated
**How to avoid:** Update both `interface_builder.py:validate_interface_config()` and `piece.py:assemble_piece()`
**Warning signs:** Tests pass for transformation but fail for piece mode

### Pitfall 4: Coordinate Transformation Without Wrapping
**What goes wrong:** Positions outside [0, 1) after fractional coordinate conversion
**Why it happens:** GenIce may output positions that span multiple unit cells
**How to avoid:** Always wrap fractional coordinates: `frac_pos = frac_pos % 1.0`

## Code Examples

### Triclinic Detection
```python
# Source: Established practice with CONTEXT.md tolerance
def is_triclinic(cell: np.ndarray, angle_tol_deg: float = 0.1) -> bool:
    """Check if cell is triclinic (non-orthogonal).
    
    Uses 0.1° tolerance from CONTEXT.md decisions.
    """
    a, b, c = cell[0], cell[1], cell[2]
    
    def angle(v1: np.ndarray, v2: np.ndarray) -> float:
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 < 1e-10 or n2 < 1e-10:
            return 90.0
        cos_a = np.clip(np.dot(v1, v2) / (n1 * n2), -1, 1)
        return np.degrees(np.arccos(cos_a))
    
    alpha = angle(b, c)
    beta = angle(a, c)
    gamma = angle(a, b)
    
    return (abs(alpha - 90) > angle_tol_deg or 
            abs(beta - 90) > angle_tol_deg or 
            abs(gamma - 90) > angle_tol_deg)
```

### Cell Angle Calculation
```python
# Source: Standard crystallographic convention
def get_cell_angles(cell: np.ndarray) -> tuple[float, float, float]:
    """Get cell angles (alpha, beta, gamma) in degrees.
    
    Convention:
    - alpha: angle between b and c
    - beta: angle between a and c  
    - gamma: angle between a and b
    """
    a, b, c = cell[0], cell[1], cell[2]
    
    def angle(v1: np.ndarray, v2: np.ndarray) -> float:
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 < 1e-10 or n2 < 1e-10:
            return 90.0
        cos_a = np.clip(np.dot(v1, v2) / (n1 * n2), -1, 1)
        return np.degrees(np.arccos(cos_a))
    
    alpha = angle(b, c)
    beta = angle(a, c)
    gamma = angle(a, b)
    
    return alpha, beta, gamma
```

### Fractional Coordinate Conversion
```python
# Source: Standard crystallographic formula
def cartesian_to_fractional(positions: np.ndarray, cell: np.ndarray) -> np.ndarray:
    """Convert Cartesian positions to fractional coordinates.
    
    Formula: frac_pos = positions @ inv(cell.T)
    
    Note: cell is stored as ROW vectors in QuickIce convention.
    """
    cell_inv_T = np.linalg.inv(cell.T)
    frac_positions = positions @ cell_inv_T
    return frac_positions

def fractional_to_cartesian(frac_positions: np.ndarray, cell: np.ndarray) -> np.ndarray:
    """Convert fractional coordinates to Cartesian positions.
    
    Formula: cart_pos = frac_pos @ cell.T
    """
    return frac_positions @ cell.T
```

### Ice Phase Classification
```python
# Source: Verified from GenIce output
TRICLINIC_PHASES = {"ice_ii", "ice_v"}
ORTHOGONAL_PHASES = {"ice_ih", "ice_ic", "ice_iii", "ice_vi", "ice_vii", "ice_viii"}

# GenIce lattice names
PHASE_TO_GENICE = {
    "ice_ih": "ice1h",   # Orthogonal
    "ice_ic": "ice1c",   # Orthogonal
    "ice_ii": "ice2",    # RHOMBOHEDRAL: α=β=γ≈113°
    "ice_iii": "ice3",   # Orthogonal
    "ice_v": "ice5",     # MONOCLINIC: β≈109°, α=γ=90°
    "ice_vi": "ice6",    # Orthogonal
    "ice_vii": "ice7",   # Orthogonal
    "ice_viii": "ice8",  # Orthogonal
}

# Measured angles from GenIce (unit cell):
# Ice II: α=β=γ=113.10° (rhombohedral)
# Ice V:  α=90°, β=109.20°, γ=90° (monoclinic)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Reject triclinic cells | Transform to orthogonal | Phase 24 | Enables all 8 ice phases |

**Outdated (to be removed):**
- `interface_builder.py` lines 119-130: Triclinic rejection error
- `piece.py` lines 62-71: Triclinic rejection error

## Existing Codebase Integration Points

### Files Requiring Modification

| File | Lines | Current Behavior | Required Change |
|------|-------|-----------------|-----------------|
| `interface_builder.py` | 119-130 | Reject triclinic with error | Call transformer before validation |
| `piece.py` | 62-71 | Check `_is_cell_orthogonal()` and raise | Remove check (handled upstream) |
| `piece.py` | 74-79 | `ice_dims = np.diag(cell)` | Use bounding box extent |
| `generator.py` | 149-206 | `_parse_gro()` handles triclinic | Already correct, no changes |

### New Files to Create

| File | Purpose |
|------|---------|
| `transformer.py` | TriclinicTransformer class |
| `transformer_types.py` | TransformationResult dataclass |

### Integration Flow
```
Tab 1 (Ice Generation):
  generate_candidates() 
    → IceStructureGenerator._generate_single()
    → TriclinicTransformer.transform_if_needed()  # NEW
    → Return Candidate (now always orthogonal)

Tab 2 (Interface Builder):
  generate_interface()
    → validate_interface_config()  # Remove triclinic check
    → assemble_piece()             # Assumes orthogonal (guaranteed)
```

## Validation Approach

From CONTEXT.md decisions:

1. **Density Preservation**
   - Compare before/after densities
   - Tolerance: relative error < 1%

2. **Coordination Numbers**
   - Count nearest neighbors before/after
   - Should be identical (same crystal structure)

3. **Bond Lengths and Angles**
   - Measure O-O, O-H distances and H-O-H angles
   - Should be within tolerance

4. **Internal Consistency Only**
   - No need for published reference comparison
   - Before/after comparison sufficient

### Validation Code
```python
def validate_transformation(
    original: Candidate, 
    transformed: Candidate,
    density_tol: float = 0.01,
    bond_tol: float = 0.01  # 1% relative
) -> bool:
    """Validate that transformation preserved crystal structure."""
    # Density check
    vol_orig = np.abs(np.linalg.det(original.cell))
    vol_new = np.abs(np.linalg.det(transformed.cell))
    
    # Volume should scale by multiplier (det(H))
    multiplier = transformed.nmolecules / original.nmolecules
    expected_vol_ratio = multiplier
    
    actual_vol_ratio = vol_new / vol_orig
    if abs(actual_vol_ratio - expected_vol_ratio) / expected_vol_ratio > density_tol:
        return False
    
    # Bond length check (sample a few molecules)
    # ... coordination number check ...
    
    return True
```

## Transformation Matrix Discovery

Finding the correct transformation matrix H is the key challenge. Known approaches:

### For Rhombohedral (Ice II)
The rhombohedral cell can be transformed to hexagonal setting:
```python
# Rhombohedral → Hexagonal (γ=120°, still not orthogonal)
H_rhomb_to_hex = np.array([
    [1, -1, 0],
    [0, 1, -1],
    [1, 1, 1]
])
# Multiplier: 3x

# Hexagonal → Orthogonal
H_hex_to_ortho = np.array([
    [2, 1, 0],
    [1, 2, 0],
    [0, 0, 1]
])
# Multiplier: 3x

# Combined: 9x multiplier
```

### For Monoclinic (Ice V)
The monoclinic cell has one tilted axis; transformation depends on tilt direction:
```python
# For β ≠ 90° (a-c plane tilt)
# Need to find integer n such that a' = a + n*c is orthogonal to c
# This may require large multipliers
```

### General Algorithm
```python
def find_orthogonal_supercell(cell: np.ndarray, max_multiplier: int = 100) -> np.ndarray:
    """Find integer matrix H such that H @ cell is approximately orthogonal.
    
    Returns None if no suitable transformation found within max_multiplier.
    """
    # Try common transformation patterns
    patterns = [
        np.diag([2, 2, 2]),
        np.diag([3, 3, 3]),
        np.array([[1, 1, 0], [-1, 1, 0], [0, 0, 1]]),
        # ... more patterns from crystallographic conventions
    ]
    
    for H in patterns:
        if abs(np.linalg.det(H)) > max_multiplier:
            continue
        new_cell = H @ cell
        if is_orthogonal(new_cell):
            return H
    
    # If no pattern works, may need to reject with error
    return None
```

## Open Questions

### Q1: What is the maximum acceptable supercell multiplier?
**What we know:** Large multipliers mean more atoms, slower computation
**What's unclear:** Practical limit for nmol=100 starting point
**Recommendation:** Start with max_multiplier=50, adjust based on testing

### Q2: Should transformation happen in generator or as post-processing?
**What we know:** CONTEXT.md says "Tab 1 (Ice Generation) when triclinic phase selected"
**What's unclear:** Exact integration point in IceStructureGenerator
**Recommendation:** Post-processing step after `_generate_single()`, before returning Candidate

### Q3: How to handle transformation failure?
**What we know:** CONTEXT.md says "retry with different molecule counts"
**What's unclear:** How many retries, what nmol adjustments
**Recommendation:** 
- Try 3-5 different supercell multipliers
- If all fail, reject with clear error message suggesting different nmol

## Sources

### Primary (HIGH confidence)
- GenIce2 source code - verified triclinic cell output format
- GROMACS manual - triclinic cell representation
- Existing `generator.py` lines 193-206 - triclinic cell parsing

### Secondary (MEDIUM confidence)
- spglib documentation - niggli_reduce, standardize_cell functions
- ASE Cell documentation - niggli_reduce implementation

### Tertiary (LOW confidence)
- None - all core findings verified with code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - numpy/spglib already available
- Architecture: HIGH - clear integration points identified
- Pitfalls: HIGH - verified with actual triclinic cells from GenIce
- Transformation algorithms: MEDIUM - patterns known but optimal H may require tuning

**Research date:** 2026-04-12
**Valid until:** 30 days (stable crystallographic algorithms)

---

*Phase: 24-triclinic-transformation*
*Research completed: 2026-04-12*
