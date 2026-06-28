# Technology Stack

**Project:** QuickIce — Polycrystalline Builder (poly-gen)
**Researched:** 2026-06-28

## Recommended Stack

### Core Libraries (Already in environment.yml)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| numpy | 2.4.3 | Rotation matrices, array ops on atom positions | Already used throughout QuickIce; `np.linalg.inv()`, `np.dot()` for coordinate transforms |
| scipy | 1.17.1 | `scipy.spatial.Voronoi` for auto grain generation, `scipy.spatial.cKDTree` for overlap detection | Already used in `overlap_resolver.py`; Voronoi supports N-dim via Qhull |
| shapely | 2.1.2 | Polygon operations: intersection, clipping, contains, area | Handles arbitrary region geometry; GEOS-backed for robust topology |
| genice2 | 2.2.13.1 | Crystal structure generation for all ice/hydrate phases | Already wrapped in `generator.py` and `hydrate_generator.py` |
| spglib | 2.7.0 | Crystal symmetry analysis (optional) | Can detect space group after rotation to verify structure integrity |

### Infrastructure (Already in environment.yml)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PySide6 | 6.10.2 | GUI for region drawing/editing | Required for interactive polygon editing in polycrystalline tab |
| VTK | 9.5.2 | 3D rendering of molecular structures + region boundaries | Already used for molecular visualization |

### Supporting Libraries (Already in environment.yml)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| networkx | 3.6.1 | Graph operations for GenIce2 HB network | Already GenIce2 dependency; not directly used in poly-gen |
| matplotlib | 3.10.8 | 2D plots for debugging region layouts | Development/debug only; not for production |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Voronoi 2D | `scipy.spatial.Voronoi` + mirror technique | `scipy.spatial.SphericalVoronoi` | SphericalVoronoi is for sphere surfaces, not flat periodic boxes |
| Voronoi 3D PBC | Mirror technique (27 copies) | Custom PBC Voronoi library | No Python library provides PBC Voronoi natively; mirror technique is proven and simple |
| Polygon ops | `shapely` | `matplotlib.path.Path` | Path.contains_point works but lacks set-theoretic ops (intersection, union, difference) needed for grain boundary computation |
| Crystal rotation | `numpy` rotation matrices | `scipy.spatial.transform.Rotation` | Rotation class adds complexity without benefit; we just need R @ positions, not Euler/quaternion decomposition |
| Region definition | `shapely.Polygon` in XY plane | 3D `shapely` polyhedra | Shapely is 2D-only (z ignored in analysis); 3D regions need a custom approach — use 2D polygon extruded along Z |

## No Additional Dependencies Needed

All required libraries are already in `environment.yml`. No new conda packages required.

## Installation

No additional installation needed. All dependencies already available:

```bash
# Verify
python3 -c "from scipy.spatial import Voronoi; from shapely import Polygon; print('OK')"
```

## Key API Details

### scipy.spatial.Voronoi

- Supports N-dimensional Voronoi diagrams (2D and 3D)
- Uses Qhull library internally
- Returns `regions` (list of vertex indices per point) and `vertices` (coordinates)
- Regions with `-1` index are infinite (extend to edge of diagram)
- **Critical for PBC:** Use mirror technique — reflect points across all boundaries to make all regions finite, then clip to original box

### shapely.Polygon

- Constructor: `Polygon([(x1,y1), (x2,y2), ...])` — exterior ring + optional holes
- Key methods for poly-gen:
  - `polygon.contains(point)` — check if molecule COM is inside region
  - `polygon.intersection(other)` — compute overlap between regions
  - `polygon.difference(other)` — subtract one region from another
  - `polygon.buffer(width)` — expand region by buffer (for grain boundary zones)
  - `polygon.area` — compute region area
- **2D only:** Shapely ignores z-coordinate in analysis; use XY polygon extruded along Z for 3D regions

### numpy rotation (R @ positions)

```python
# Rotation matrix from Euler angles (ZXZ convention)
def rotation_matrix(alpha_deg, beta_deg, gamma_deg):
    a, b, g = np.radians([alpha_deg, beta_deg, gamma_deg])
    Rz1 = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(b), -np.sin(b)], [0, np.sin(b), np.cos(b)]])
    Rz2 = np.array([[np.cos(g), -np.sin(g), 0], [np.sin(g), np.cos(g), 0], [0, 0, 1]])
    return Rz2 @ Rx @ Rz1

# Apply: rotated_positions = (R @ positions.T).T
```

## Sources

- scipy.spatial.Voronoi docs (v1.18.0): https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.Voronoi.html
- Shapely User Manual (v2.1.2): https://shapely.readthedocs.io/en/stable/manual.html
- GenIce2 README: https://github.com/genice-dev/GenIce2
- QuickIce `water_filler.py`, `overlap_resolver.py`, `generator.py` (read from codebase)
- Unit cell dimensions verified via GenIce2 API runtime checks (2026-06-28)
