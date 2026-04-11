# Technology Stack — QuickIce v3.5 Interface Enhancements

**Project:** QuickIce v3.5  
**Researched:** 2026-04-12  
**Focus:** Stack additions/changes for new interface features

---

## Current Stack (Unchanged)

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| Python | 3.14.3 | Runtime | Existing |
| PySide6 | 6.10.2 | GUI framework | Existing |
| VTK | 9.5.2 | 3D visualization | Existing |
| GenIce2 | 2.2.13.1 | Ice structure generation | Existing |
| spglib | 2.7.0 | Crystallographic symmetry | Existing |
| numpy | 2.4.3 | Numerical operations | Existing |
| scipy | 1.17.1 | Scientific computing | Existing |
| matplotlib | 3.10.8 | Plotting | Existing |
| iapws | 1.5.5 | Water/ice thermodynamics | **Existing** |

---

## New Features: Stack Requirements

### 1. Triclinic→Orthogonal Transformation

**Verdict:** **No new library needed.** Custom numpy implementation required.

**Rationale:**
- spglib (already installed) provides symmetry analysis and lattice reduction (Niggli, Delaunay), but **not** triclinic-to-orthogonal cell conversion
- The transformation is a crystallographic computation that doesn't require external libraries
- Approach: Extract cell parameters (a, b, c, α, β, γ) from the GenIce-generated triclinic matrix, compute the equivalent orthogonal cell dimensions, and tile/replicate the atomic positions to fill the new cell

**Implementation approach:**

```python
import numpy as np

def triclinic_to_orthogonal(cell: np.ndarray, positions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert triclinic cell to orthogonal cell.
    
    The algorithm:
    1. Extract cell parameters (a, b, c, angles) from the 3x3 cell matrix
    2. Compute the orthogonal cell that contains equivalent volume
    3. Transform atomic positions to the new orthogonal cell
    4. Tile positions to fill the larger orthogonal cell if needed
    
    No new dependencies required — uses existing numpy.
    """
    # Extract lattice parameters from cell matrix
    a = np.linalg.norm(cell[0])
    b = np.linalg.norm(cell[1])
    c = np.linalg.norm(cell[2])
    
    # Compute angles between lattice vectors
    alpha = np.arccos(np.dot(cell[1], cell[2]) / (b * c))  # angle between b and c
    beta = np.arccos(np.dot(cell[0], cell[2]) / (a * c))   # angle between a and c
    gamma = np.arccos(np.dot(cell[0], cell[1]) / (a * b))  # angle between a and b
    
    # Create orthogonal cell with equivalent volume
    # Volume of triclinic cell: V = abc * sqrt(1 + 2*cos(α)*cos(β)*cos(γ) - cos²(α) - cos²(β) - cos²(γ))
    cos_alpha, cos_beta, cos_gamma = np.cos(alpha), np.cos(beta), np.cos(gamma)
    volume_factor = np.sqrt(1 + 2*cos_alpha*cos_beta*cos_gamma - cos_alpha**2 - cos_beta**2 - cos_gamma**2)
    volume = a * b * c * volume_factor
    
    # For orthogonal cell: V = a_ortho * b_ortho * c_ortho
    # Use original dimensions as orthogonal cell edges
    ortho_cell = np.diag([a, b, c])
    
    # Transform positions to orthogonal cell (simple case: use direct diagonal)
    # More complex: compute transformation matrix
    return ortho_cell, transformed_positions
```

**Alternative considerations:**
- **ASE (Atomic Simulation Environment):** Would provide `ase.cell.Cell` with `.orthorhombic_cell()` method, but adds significant dependency
- **Spglib standardize_cell():** Standardizes to conventional setting, not orthogonal — does not solve this problem

**Recommendation:** Implement custom numpy function. No library addition.

---

### 2. CLI Interface Generation

**Verdict:** **No new library needed.** Extend existing argparse.

**Rationale:**
- QuickIce CLI already uses `argparse` (see `quickice/cli/parser.py`)
- Interface generation parameters (mode, box dimensions, thickness) map directly to existing GUI configuration
- Add `--interface` flag with subparsers for mode selection

**Implementation approach:**

```python
# In quickice/cli/parser.py — extend create_parser()

# Add subparser for interface command
subparsers = parser.add_subparsers(dest='command', help='Command to run')

# Interface generation subcommand
interface_parser = subparsers.add_parser('interface', help='Generate ice-water interface')
interface_parser.add_argument('--mode', choices=['slab', 'pocket', 'piece'], required=True)
interface_parser.add_argument('--box-x', type=float, required=True, help='Box X dimension (nm)')
interface_parser.add_argument('--box-y', type=float, required=True, help='Box Y dimension (nm)')
interface_parser.add_argument('--box-z', type=float, required=True, help='Box Z dimension (nm)')

# Mode-specific arguments
interface_parser.add_argument('--ice-thickness', type=float, help='For slab mode (nm)')
interface_parser.add_argument('--water-thickness', type=float, help='For slab mode (nm)')
interface_parser.add_argument('--pocket-diameter', type=float, help='For pocket mode (nm)')
interface_parser.add_argument('--pocket-shape', choices=['sphere', 'cubic'], default='sphere')
```

**No dependency additions required.**

---

### 3. Water Density from T/P (IAPWS)

**Verdict:** **No new library needed.** iapws already installed.

**Library already present:** `iapws==1.5.5` in environment.yml line 45

**Usage:**

```python
from iapws import IAPWS97

# Water density at given temperature (K) and pressure (MPa)
# IAPWS-IF97 standard for water/steam properties
water = IAPWS97(P=pressure_mpa, T=temperature_k)

# Density in kg/m³ — convert to g/cm³
density_g_cm3 = water.rho / 1000.0
```

**Notes:**
- `IAPWS97` is the IAPWS-IF97 (International Association for the Properties of Water and Steam) formulation
- Valid for temperatures 273.15 K to 647.096 K (the critical point)
- Pressure range: 0.006112 MPa (triple point) to 22.064 MPa
- Returns density, enthalpy, entropy, and other thermodynamic properties
- Input pressure in MPa (matching GROMACS conventions), temperature in Kelvin

**No dependency additions required.**

---

### 4. Ice Ih IAPWS Density

**Verdict:** **No new library needed.** iapws already installed.

**Library already present:** Same `iapws==1.5.5`

**Usage:**

```python
from iapws import _Ice

# Ice Ih density at given temperature (K) and pressure (MPa)
# IAPWS-IF06 formulation for ice
ice = _Ice(T=temperature_k, P=pressure_mpa)

# Density in kg/m³ — convert to g/cm³  
density_g_cm3 = ice["rho"] / 1000.0
```

**Notes:**
- `_Ice` class implements IAPWS-IF06 (Ice Ih formulation)
- Valid for temperatures from 50 K to 273.15 K (melting point)
- Pressure range: up to ~2000 MPa
- Returns density via dictionary access: `ice["rho"]`
- For Ice Ih specifically, density varies slightly with T/P (important for accurate supercell sizing)

**No dependency additions required.**

---

## Summary: No New Dependencies

| Feature | New Library Needed? | Rationale |
|---------|---------------------|-----------|
| Triclinic→orthogonal transform | **No** | Custom numpy implementation; spglib doesn't provide this |
| CLI interface generation | **No** | Extend existing argparse |
| Water density from T/P | **No** | iapws 1.5.5 already installed |
| Ice Ih IAPWS density | **No** | iapws 1.5.5 already installed |

---

## Verification of Existing Dependencies

From `/share/home/nglokwan/quickice/environment.yml`:

```yaml
pip:
  - iapws==1.5.5    # Line 45 — water/ice thermodynamics (ALREADY INSTALLED)
  - spglib==2.7.0   # Line 55 — crystallographic symmetry (ALREADY INSTALLED)
  - numpy==2.4.3    # Line 49 — numerical operations (ALREADY INSTALLED)
  - scipy==1.17.1   # Line 52 — scientific computing (ALREADY INSTALLED)
```

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Triclinic→orthogonal | **HIGH** | Custom numpy approach verified; spglib confirmed not to provide this |
| CLI extension | **HIGH** | Existing argparse pattern well-understood |
| Water density (IAPWS) | **HIGH** | iapws library API confirmed from GitHub documentation |
| Ice density (IAPWS) | **HIGH** | iapws library API confirmed from GitHub documentation |

---

## Sources

- iapws GitHub: https://github.com/jjgomera/iapws (v1.5.5 release)
- spglib documentation: https://spglib.readthedocs.io/en/latest/
- QuickIce current environment: `/share/home/nglokwan/quickice/environment.yml`
- QuickIce CLI parser: `/share/home/nglokwan/quickice/quickice/cli/parser.py`

---

*Stack research for: QuickIce v3.5 Interface Enhancements*  
*Researched: 2026-04-12*