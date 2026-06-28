# Domain Pitfalls — Polycrystalline Builder with Existing Stack

**Domain:** Molecular simulation GUI — polycrystalline ice/hydrate builder
**Researched:** 2026-06-28
**Stack:** PySide6 6.10.2, VTK 9.5.2, numpy 2.4.3, scipy 1.17.1, shapely 2.1.2

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: VTK Offscreen Rendering Crash
**What goes wrong:** VTK segfaults when calling `Render()` in headless environments (QT_QPA_PLATFORM=offscreen on machines without a display)
**Why it happens:** VTK's OpenGL2 backend requires GPU resources; offscreen mode on headless servers lacks them
**Consequences:** 3D preview panel crashes the entire application; tests fail in CI
**Prevention:**
- Wrap VTK render calls in try/except; fall back to "Preview unavailable in headless mode" text
- Check `QT_QPA_PLATFORM` or `os.environ.get('DISPLAY')` before initializing VTK render window
- Use `vtkRenderWindow.SetOffScreenRendering(1)` with `vtkOSOpenGLRenderWindow` as a software fallback
- In tests: mock or skip VTK-dependent tests (as per AGENTS.md: "mock or skip VTK-dependent tests if needed")
**Detection:** Application crashes when opening the polycrystalline tab in headless mode

### Pitfall 2: Y-Axis Flip Between Qt and VTK/Shapely
**What goes wrong:** Regions appear upside-down or mirrored between 2D editor and 3D preview
**Why it happens:** Qt uses Y-down (screen coordinates), shapely/VTK use Y-up (mathematical convention)
**Consequences:** Region placements are wrong; atoms are generated in wrong positions; user confusion
**Prevention:**
- Establish a clear convention: ALL internal geometry uses Y-up (shapely convention)
- Apply Y-flip ONLY at the QGraphicsView boundary: `qt_y = -shapely_y`
- Use `shapely.affinity.scale(yfact=-1, origin=(0,0))` when converting (verified working)
- Document the convention in every conversion function
**Detection:** Region appears in wrong position in 3D preview; visual mismatch between 2D and 3D views

### Pitfall 3: cKDTree query_ball_tree O(n²) Scaling at Large Scale
**What goes wrong:** Overlap detection becomes unusably slow for large polycrystalline boxes
**Why it happens:** `query_ball_tree(self, self, r=0.25)` scales as O(n²) in dense systems
**Consequences:** 10+ second freeze for 500k+ atoms; application appears hung
**Prevention:**
- NEVER run `query_ball_tree` on a single tree with >200k atoms for overlap detection
- Use STAGED approach: build per-grain trees, pairwise detection (O(k²) pairs × O(n log n) per pair)
- For 500k+ atoms: consider spatial hashing or grid-based pre-filtering before cKDTree
- Show progress dialog during generation (background thread)
**Detection:** Generation takes >5s; UI freezes; user reports "application crashed" (it didn't, it's just slow)

**Benchmark data:**
| N atoms | query_ball_tree time |
|---------|---------------------|
| 50k | 0.06s |
| 100k | 0.14s |
| 200k | 0.35s |
| 500k | 1.33s |
| 1M | 10.8s ← CRITICAL |

### Pitfall 4: shapely 2.5D Model Cannot Represent Arbitrary 3D Shapes
**What goes wrong:** User wants spherical inclusions or tapered pores but the 2.5D model only supports prism-shaped grains
**Why it happens:** shapely is strictly 2D; the 2.5D model (Polygon + Z-range) can only represent extruded 2D shapes, not true 3D geometry
**Consequences:** Scientific use cases like spherical gas bubbles in ice, conical inclusions, or non-vertical grain boundaries are impossible
**Prevention:**
- Design the `PhaseRegion` dataclass with a `shape_type` field from the start: "prism" (V1) and "mesh" (future, requires trimesh)
- Document the 2.5D limitation clearly in the UI
- For V1: accept the limitation; spherical inclusions can be approximated by polygon + Z-range
- For future: trimesh integration adds full 3D CSG
**Detection:** User requests "sphere" or "cylinder" shape; UI can only offer "polygon + Z-range"

## Moderate Pitfalls

Mistakes that cause delays or technical debt.

### Pitfall 5: GenIce2 Sequential Generation Blocks UI
**What goes wrong:** Generating 10+ grains takes 5–25s, freezing the GUI
**Why it happens:** GenIce2 is CPU-bound; QuickIce uses QThread but GenIce2's random state is not thread-safe
**Prevention:**
- Use QThread worker (following existing HydrateWorker pattern in QuickIce)
- Show progress dialog with per-grain status ("Generating grain 3/15...")
- Save/restore numpy random state around each generation call (existing pattern in generator.py)
**Detection:** UI freezes during generation; no progress feedback

### Pitfall 6: shapely vectorized.contains is Deprecated
**What goes wrong:** Code uses `shapely.vectorized.contains()` which is deprecated in shapely 2.1.2
**Why it happens:** shapely 2.0+ moved vectorized operations to top-level `contains_xy`
**Consequences:** DeprecationWarning spam; code breaks in future shapely version
**Prevention:**
- Use `shapely.contains_xy(polygon, x_array, y_array)` instead of `shapely.vectorized.contains()`
- Both are equally fast (0.005s/100k points, verified)
**Detection:** DeprecationWarning in console output

### Pitfall 7: QPolygonF.append() Requires QPointF, Not Float
**What goes wrong:** Trying `qpf.append(x, y)` causes TypeError in PySide6 6.10.2
**Why it happens:** PySide6's QPolygonF.append() requires a QPointF object, not individual floats
**Consequences:** Shape rendering fails; application crashes with TypeError
**Prevention:**
```python
# WRONG:
qpf = QPolygonF()
qpf.append(x, y)  # TypeError

# CORRECT:
from PySide6.QtCore import QPointF
qpf = QPolygonF()
qpf.append(QPointF(x, y))  # Works
```
**Detection:** TypeError on first region rendering attempt

### Pitfall 8: QUndoStack Import Location
**What goes wrong:** `from PySide6.QtWidgets import QUndoStack` raises ImportError
**Why it happens:** QUndoStack is in QtGui, not QtWidgets (PySide6 6.10.2)
**Consequences:** Import error; builder fails to load
**Prevention:**
```python
# WRONG:
from PySide6.QtWidgets import QUndoStack  # ImportError

# CORRECT:
from PySide6.QtGui import QUndoStack, QUndoCommand
```
**Detection:** ImportError on module load

### Pitfall 9: cKDTree Requires Coordinates Within [0, boxsize)
**What goes wrong:** Atoms with positions exactly on the PBC boundary cause cKDTree errors
**Why it happens:** cKDTree with `boxsize` requires all coordinates in [0, boxsize); `np.mod(-tiny, L)` can return exactly L
**Consequences:** Overlap detection crashes or produces wrong results
**Prevention:**
- Follow existing pattern from overlap_resolver.py: wrap coordinates, then fix boundary edge cases
- `np.mod(coords, boxsize)` then check for `>= boxsize` and subtract
**Detection:** ValueError from cKDTree or unexpected overlap counts

### Pitfall 10: Voronoi Regions Extend Beyond Box
**What goes wrong:** scipy Voronoi produces unbounded regions that extend to infinity
**Why it happens:** Voronoi cells near the box boundary are unbounded by default
**Consequences:** Grains have infinite extent; atom clipping assigns atoms to wrong grain
**Prevention:**
- Use mirror-point technique (Wave 1 recommendation): replicate seed points across box boundaries before Voronoi computation, then clip resulting regions to box via `shapely.intersection(region, box)`
- For 3D: many scipy Voronoi regions are unbounded (922/1001 finite for 1000 seeds); the mirror-point technique is essential
**Detection:** Voronoi regions with -1 in vertex indices; grains with unbounded extent

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 11: VTK Prism Rendering Z-Fighting
**What goes wrong:** Overlapping translucent prism faces produce flickering/z-fighting artifacts
**Why it happens:** VTK's depth buffer doesn't handle overlapping translucent surfaces well
**Prevention:** Enable depth peeling: `renderer.SetUseDepthPeeling(1)`; sort actors back-to-front
**Detection:** Flickering in 3D preview when regions overlap

### Pitfall 12: Region Color Ambiguity
**What goes wrong:** Similar-looking colors for adjacent ice Ih grains make them indistinguishable
**Why it happens:** Default color palette doesn't consider perceptual distinctness
**Prevention:** Use a perceptually uniform colormap (e.g., tab10, Set3 from matplotlib); assign colors with maximum contrast between neighbors
**Detection:** User can't tell which grain is which in 3D preview

### Pitfall 13: Minimum Grain Size Violation
**What goes wrong:** User draws region too small for the selected crystal phase (<300 molecules for Ice Ih, <740 for sI hydrate)
**Why it happens:** Users don't know the minimum viable grain sizes
**Prevention:** Compute `polygon.area * z_height / volume_per_molecule` in real-time; show warning when below minimum
**Detection:** GenIce2 generates too few molecules or fails; structure is physically unreasonable

### Pitfall 14: Density Mismatch at Phase Boundaries
**What goes wrong:** Ice Ih (0.92 g/cm³) next to hydrate sI (0.95 g/cm³) creates ~3% density gap at boundaries
**Why it happens:** Different crystal structures have different densities
**Consequences:** Visible gap or overlap at boundaries in 3D preview; simulation instability
**Prevention:** Use boundary buffer zones (disordered water layer) per phase-boundary research; adjust Z-range of buffer zone to accommodate density difference
**Detection:** Atoms overlap at phase boundary; overlap_resolver removes too many molecules

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Data model design | Pitfall 4: 2.5D limitation for arbitrary 3D | Design PhaseRegion with shape_type field from start |
| 2D editor | Pitfall 2: Y-axis flip | Establish convention, test with visual verification |
| 2D editor | Pitfall 7: QPolygonF.append | Use QPointF explicitly |
| 2D editor | Pitfall 8: QUndoStack import | Import from QtGui |
| 3D preview | Pitfall 1: VTK offscreen crash | Try/except with fallback; skip in tests |
| 3D preview | Pitfall 11: Z-fighting | Enable depth peeling |
| Generate-Clip-Resolve | Pitfall 3: cKDTree scaling | Staged pairwise approach |
| Generate-Clip-Resolve | Pitfall 5: GenIce2 blocks UI | QThread worker + progress |
| Generate-Clip-Resolve | Pitfall 9: cKDTree boundary | Follow overlap_resolver pattern |
| Voronoi auto-generation | Pitfall 10: Unbounded regions | Mirror-point technique |
| Phase boundaries | Pitfall 14: Density mismatch | Buffer zones with adjustable thickness |
| shapely integration | Pitfall 6: deprecated vectorized | Use contains_xy |

## Sources

- All benchmarks: run on actual hardware (see STACK.md for data)
- VTK crash: reproduced in this environment (segfault on offscreen Render())
- shapely deprecation: DeprecationWarning observed in benchmark output
- QPolygonF.append: TypeError observed in testing
- QUndoStack import: ImportError observed in testing
- cKDTree boundary: from existing overlap_resolver.py code comments
- Voronoi unbounded: scipy benchmark data (922/1001 finite for 1000 3D seeds)
