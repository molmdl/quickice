---
phase: 016-minimize-bundle-dependencies
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [quickice-gui.spec]
autonomous: true

must_haves:
  truths:
    - "PyInstaller bundle builds successfully"
    - "All quickice features work after optimization"
    - "Bundle size reduced by ~15-20MB"
  artifacts:
    - path: "quickice-gui.spec"
      provides: "PyInstaller build configuration"
      contains: "EXCLUDES with scipy/matplotlib/shapely restrictions"
  key_links:
    - from: "quickice-gui.spec"
      to: "scipy bundle size"
      via: "excludes list"
      pattern: "scipy\\.(cluster|integrate|io|ndimage|signal|stats)"
---

<objective>
Restrict scipy, matplotlib, and shapely to only required modules in PyInstaller bundle.

Purpose: Reduce bundle size by excluding unused submodules while preserving all functionality.
Output: Updated spec file with verified exclusions, ~15-20MB bundle size reduction.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/quick/016-minimize-bundle-dependencies/016-RESEARCH.md
@.planning/quick/016-minimize-bundle-dependencies/FUTURE_OPTIMIZATIONS.md

## Dependency Analysis Results

**CRITICAL FINDING:** Research assumptions were incorrect. Transitive dependencies prevent most scipy exclusions.

### scipy Dependency Tree (Verified)

**Importing scipy.spatial.cKDTree loads:**
- scipy.constants (5 modules)
- scipy.linalg (43 modules)
- scipy.sparse (33 modules)
- scipy.special (25 modules)
- scipy.spatial (26 modules)

**Importing scipy.interpolate.UnivariateSpline loads:**
- scipy.constants (5 modules)
- scipy.fft (14 modules)
- scipy.interpolate (33 modules)
- scipy.linalg (45 modules)
- scipy.optimize (91 modules)
- scipy.sparse (68 modules)
- scipy.spatial (26 modules)
- scipy.special (25 modules)

**CAN safely exclude:**
- scipy.cluster
- scipy.integrate
- scipy.io
- scipy.ndimage
- scipy.signal
- scipy.stats

**CANNOT exclude:** constants, fft, linalg, optimize, sparse, special (transitive dependencies)

### matplotlib Dependency Tree (Verified)

**Importing matplotlib modules used by quickice loads:**
- matplotlib.pyplot (loaded by quickice/output/phase_diagram.py line 13)
- matplotlib.backends.backend_qtagg
- matplotlib.figure
- matplotlib.patches
- Total: 101 modules

**CAN safely exclude:**
- matplotlib.animation
- matplotlib.tests (already in EXCLUDES)

**CANNOT exclude:** pyplot (required by phase_diagram.py module-level import)

### shapely Dependency Tree (Verified)

**Importing shapely.geometry.Point/Polygon loads:**
- shapely.geometry (10 modules)
- Total: 34 modules

**CAN safely exclude:**
- shapely.ops
- shapely.prepared
- shapely.tests (already in EXCLUDES)

### Estimated Savings

| Package | Current | Exclusions | Savings |
|---------|---------|------------|---------|
| scipy | 113MB | cluster, integrate, io, ndimage, signal, stats | ~10-15MB |
| matplotlib | 20MB | animation | ~1-2MB |
| shapely | 10.5MB | ops, prepared | ~2-3MB |
| **Total** | **143.5MB** | | **~13-20MB** |

**NOTE:** Original research estimated 105MB savings, but transitive dependencies prevent most exclusions.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update spec file with scipy exclusions</name>
  <files>quickice-gui.spec</files>
  <action>
Replace `collect_all('scipy')` with selective submodule collection and add safe exclusions.

**Changes to make:**

1. **Remove scipy from RUNTIME_PACKAGES list** (line 50):
   - Delete `'scipy',` from the list

2. **Add selective scipy hiddenimports** (after line 44, before RUNTIME_PACKAGES loop):
   ```python
   # scipy - only spatial and interpolate (with their transitive dependencies)
   hiddenimports += collect_submodules('scipy.spatial')
   hiddenimports += collect_submodules('scipy.interpolate')
   ```

3. **Add scipy exclusions to EXCLUDES** (after line 39):
   ```python
   # scipy unused modules (safe to exclude - no transitive dependencies)
   'scipy.cluster', 'scipy.cluster.tests',
   'scipy.integrate', 'scipy.integrate.tests',
   'scipy.io', 'scipy.io.tests',
   'scipy.ndimage', 'scipy.ndimage.tests',
   'scipy.signal', 'scipy.signal.tests',
   'scipy.stats', 'scipy.stats.tests',
   ```

**DO NOT exclude:**
- scipy.constants, scipy.fft, scipy.linalg, scipy.optimize, scipy.sparse, scipy.special
- These are transitive dependencies of scipy.spatial and scipy.interpolate

**Rationale:** Dependency analysis confirmed scipy.spatial.cKDTree and scipy.interpolate.UnivariateSpline require these submodules. Excluding them would cause runtime ImportError.
  </action>
  <verify>
Run Python to verify imports still work:
```bash
python3 -c "from scipy.spatial import cKDTree; from scipy.interpolate import UnivariateSpline; print('OK')"
```
  </verify>
  <done>
scipy excluded from collect_all(), selective spatial/interpolate imports added, safe exclusions added to EXCLUDES list.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update spec file with matplotlib and shapely exclusions</name>
  <files>quickice-gui.spec</files>
  <action>
Add safe exclusions for matplotlib and shapely. Keep collect_all for these packages.

**Changes to make:**

1. **Add matplotlib exclusions to EXCLUDES** (after scipy exclusions from Task 1):
   ```python
   # matplotlib unused modules
   'matplotlib.animation', 'matplotlib.animation.tests',
   ```

2. **Add shapely exclusions to EXCLUDES** (after matplotlib exclusions):
   ```python
   # shapely unused modules
   'shapely.ops', 'shapely.ops.tests',
   'shapely.prepared', 'shapely.prepared.tests',
   ```

**DO NOT exclude:**
- matplotlib.pyplot (required by quickice/output/phase_diagram.py module-level import)
- Any other matplotlib submodules (extensive transitive dependencies)

**Rationale:** 
- matplotlib.pyplot is imported at module level in phase_diagram.py (line 13), so it loads with any import from that module.
- shapely.ops and shapely.prepared are not required by Point/Polygon and can be safely excluded.
  </action>
  <verify>
Run Python to verify imports still work:
```bash
python3 -c "from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg; from matplotlib.figure import Figure; from matplotlib.patches import Polygon; from shapely.geometry import Point, Polygon; print('OK')"
```
  </verify>
  <done>
matplotlib.animation and shapely.ops/prepared added to EXCLUDES list.
  </done>
</task>

<task type="auto">
  <name>Task 3: Build bundle and verify all features work</name>
  <files>quickice-gui.spec</files>
  <action>
Build the PyInstaller bundle and run comprehensive feature tests to verify no runtime errors.

**Build command:**
```bash
./scripts/build-linux.sh
```

**Verify bundle size reduction:**
```bash
du -sh dist/quickice-gui/
du -sh dist/quickice-gui/_internal/scipy*
```

**Run comprehensive feature tests:**
1. Start the bundled application: `./dist/quickice-gui/quickice-gui`
2. Test ice generation: Generate Ice Ih structure
3. Test hydrate generation: Generate sI methane hydrate
4. Test ion insertion: Generate ice with NaCl ions
5. Test interface generation: Generate ice-water interface
6. Test phase diagram: Open phase diagram tab, click to select phase
7. Test export: Export structure to GROMACS/PDB

**Expected behavior:**
- Application starts without errors
- All generation modes work (ice, hydrate, ion, interface)
- Phase diagram displays and responds to clicks
- Export functions work
- Bundle size reduced by ~15-20MB (from 863MB to ~843-848MB)

**If errors occur:**
- Check for ImportError messages in console output
- Verify excluded modules are not actually required
- Add missing modules to hiddenimports if needed
  </action>
  <verify>
```bash
# Verify bundle built
test -d dist/quickice-gui && echo "Bundle exists"

# Verify bundle size reduction (expect ~15-20MB smaller)
OLD_SIZE=863
NEW_SIZE=$(du -sm dist/quickice-gui | cut -f1)
SAVINGS=$((OLD_SIZE - NEW_SIZE))
echo "Bundle size: ${NEW_SIZE}MB (saved ${SAVINGS}MB)"

# Verify scipy size reduction
du -sh dist/quickice-gui/_internal/scipy*
```
  </verify>
  <done>
Bundle builds successfully, all features work, bundle size reduced by ~15-20MB.
  </done>
</task>

</tasks>

<verification>
## Build Verification

- [ ] Bundle builds without errors: `./scripts/build-linux.sh` exits 0
- [ ] Bundle size reduced: `du -sh dist/quickice-gui/` shows ~843-848MB (down from 863MB)
- [ ] scipy size reduced: `du -sh dist/quickice-gui/_internal/scipy*` shows reduction

## Feature Verification

Test all quickice features in the bundled application:

1. **Ice Generation:**
   - Generate Ice Ih structure
   - Verify 3D visualization renders correctly
   - Uses scipy.spatial.cKDTree (overlap resolution)

2. **Hydrate Generation:**
   - Generate sI methane hydrate
   - Verify dual-style rendering (water lines + guest ball-and-stick)

3. **Ion Insertion:**
   - Generate ice with NaCl ions
   - Uses scipy.spatial.cKDTree (ion placement)

4. **Interface Generation:**
   - Generate ice-water interface
   - Verify phase-distinct coloring

5. **Phase Diagram:**
   - Open phase diagram tab
   - Click to select temperature/pressure
   - Uses shapely.geometry.Point/Polygon (phase detection)
   - Uses matplotlib.backends.backend_qtagg (canvas)
   - Uses matplotlib.pyplot (via phase_diagram.py import)

6. **Export:**
   - Export structure to GROMACS/PDB
   - Verify files created successfully
</verification>

<success_criteria>
1. **Build succeeds:** PyInstaller completes without errors
2. **Bundle size reduced:** ~15-20MB savings (863MB → ~843-848MB)
3. **All features work:** No ImportError or runtime errors in any feature
4. **Spec file updated:** EXCLUDES includes scipy cluster/integrate/io/ndimage/signal/stats, matplotlib.animation, shapely.ops/prepared
</success_criteria>

<output>
After completion, create `.planning/quick/016-minimize-bundle-dependencies/016-SUMMARY.md` with:
- Final bundle size
- Actual savings achieved
- Verification results for all features
- Any issues encountered and resolutions
</output>
