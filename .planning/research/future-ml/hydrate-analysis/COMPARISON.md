# Comparison: MD Analysis Libraries for Hydrate Simulation

**Context:** QuickIce needs MD trajectory analysis capabilities (RDF, MSD, H-bonds, F3/F4 order parameters, cage occupancy, density profiles, interface detection) for GROMACS-format simulations (.xtc, .trr, .tpr, .gro).
**Recommendation:** **MDAnalysis** as the primary library, supplemented by custom numpy/scipy implementations for hydrate-specific metrics (F3/F4, cage occupancy).

## Quick Comparison

| Criterion | MDAnalysis 2.10 | MDTraj 1.11 | freud 3.5 | pytim 1.0.7 | Custom (numpy/scipy) |
|-----------|----------------|-------------|-----------|-------------|---------------------|
| GROMACS format support | ★★★★★ | ★★★☆☆ | ★☆☆☆☆ | ★★★★☆ (via MDAnalysis) | ★☆☆☆☆ |
| PBC handling | ★★★★★ | ★★★☆☆ | ★★★★★ | ★★★☆☆ | ★☆☆☆☆ |
| Built-in RDF | ★★★★★ | ★★★★☆ | ★★★★★ | ✗ | Build yourself |
| Built-in MSD | ★★★★★ | ✗ | ★★★★☆ | ✗ | Build yourself |
| Built-in H-bonds | ★★★★★ | ★★★★☆ | ✗ | ✗ | Build yourself |
| F3/F4 order parameters | ★★☆☆☆ (custom) | ✗ | ★★☆☆☆ (partial) | ✗ | Build yourself |
| Cage occupancy | ✗ | ✗ | ✗ | ✗ | Build yourself |
| Interface analysis | ✗ | ✗ | ★★★☆☆ | ★★★★★ | Build yourself |
| Topology reading (.tpr) | ★★★★★ | ★★☆☆☆ | ✗ | ★★★★☆ (via MDAnalysis) | ✗ |
| Topology reading (.top/.itp) | ✗ | ✗ | ✗ | ★★★★☆ (via MDAnalysis) | Custom parser (existing) |
| VTK integration | Possible | Possible | No native | Possible | Direct (already in stack) |
| License | LGPLv3+ | LGPLv2.1+ | BSD-3-Clause | GPL-3.0 | MIT (yours) |
| Install size (wheel) | ~13 MB | ~8 MB | ~2 MB | ~0.5 MB (src only) | 0 |
| Python 3.11+ support | ✓ (3.11–3.14) | ✓ (3.11–3.14) | ✗ (3.12+ only) | ✓ (3.10+) | ✓ |
| Active maintenance | Very active | Active | Active | Low activity | N/A |
| Dependency count | ~15 core | ~8 core | ~3 core | ~10 (incl. MDAnalysis) | 0 |
| Memory (large traj) | Moderate (streaming) | Good (on-demand) | Good | Moderate | Depends on impl |

## Detailed Analysis

### MDAnalysis 2.10.0

**Strengths:**
- **Best GROMACS support in the ecosystem**: Native readers for .gro, .xtc, .trr, .tpr, .tng. TPR reader supports GROMACS 2024/2025 (v2.9.0+). Reads coordinates, velocities, forces, and topology from .tpr files.
- **Comprehensive analysis library**: `analysis.rdf.InterRDF` / `InterRDF_s`, `analysis.msd.EinsteinMSD`, `analysis.hbonds.HydrogenBondAnalysis`, `analysis.density`, `analysis.contacts`, `analysis.distances`, `analysis.linear_density.LinearDensity`.
- **PBC-aware**: Built-in periodic boundary condition handling including `make_whole()`, `wrap()`, `unwrap()`, and on-the-fly trajectory transformations (`NoJump`, `translate`, `rotate`).
- **Atom selection language**: Powerful selection syntax (`"resname SOL and name OW"`) critical for selecting water oxygens, guest molecules, specific residue types in hydrate systems.
- **Universe abstraction**: Clean `Universe(topology, trajectory)` pattern makes it easy to load and iterate through frames.
- **Streaming**: Does not load entire trajectory into memory — reads frame-by-frame, critical for large simulations.
- **License changed from GPLv3+ to LGPLv3+** (v2.8.0, Oct 2024): This is MIT-compatible for linking purposes. LGPL allows use as a library without requiring the calling code to be LGPL. **HOWEVER**: QuickIce is MIT-licensed. LGPL requires that users can relink with modified versions of the LGPL library. For a compiled/distributed application, this means dynamic linking is fine, but static linking may have requirements. For a conda/pip-installed Python package, this is effectively fine — MDAnalysis is used as a separate library, not embedded.

**Weaknesses:**
- **No F3/F4 order parameter built-in**: MDAnalysis does not include F3/F4 tetrahedral order parameters out of the box. Must be implemented as custom analysis class extending `AnalysisBase`.
- **No cage occupancy analysis**: No built-in clathrate cage identification.
- **No interface detection**: No ITIM/Willard-Chandler methods.
- **Larger dependency footprint**: ~15 core dependencies including `mda_xdrlib`, `gridDataFormats`, `filelock`, `tqdm`, etc. Adds ~13 MB to install.
- **LGPL license**: Not MIT — requires careful handling for distribution. Acceptable for conda/pip deployment but not ideal.

**GROMACS topology support detail:**
- `.tpr`: Full support (coordinates + topology + forces) — this is the recommended way to load GROMACS topology.
- `.gro`: Full support (coordinates + basic topology from atom names/residue names).
- `.top` / `.itp`: **Not supported.** MDAnalysis cannot parse GROMACS topology files directly. This matches our existing research finding from v4.5. Use `.tpr` instead for topology, or the existing custom .itp parser.

### MDTraj 1.11.1

**Strengths:**
- **Lighter weight**: ~8 MB wheel, ~8 core dependencies. Simpler than MDAnalysis.
- **GROMACS trajectory support**: Reads .xtc and .trr trajectories. Reads .gro as topology/coordinates.
- **Built-in analysis**: `compute_rdf()`, `compute_neighbors()`, `hydrogen_bond()`, `compute_contacts()`, `compute_distances()`, `compute_angles()`, `compute_dihedrals()`, `compute_rmsd()`.
- **LGPLv2.1+ license**: Slightly more permissive than MDAnalysis's LGPLv3+. Still LGPL but compatible.
- **Good for simple workflows**: Single `load_xtc()` + `compute_*()` function pattern is straightforward.
- **Actively maintained**: v1.11.1 released Jan 2026, Python 3.11–3.14 support.

**Weaknesses:**
- **No .tpr topology reader**: Cannot read GROMACS .tpr files. Must provide topology via .gro, .pdb, or other format. This is a **significant limitation** — .tpr is the primary way to get GROMACS topology (atom types, charges, bond info).
- **No MSD analysis**: No built-in mean squared displacement. Would need custom implementation.
- **No PBC make_whole**: No built-in method to unwrap periodic molecules. `make_molecules_whole()` exists but is less flexible than MDAnalysis's approach.
- **No atom selection language**: Must use index-based selection (e.g., `traj.top.select("name O")`) rather than the richer MDAnalysis selection syntax. Less intuitive for complex hydrate systems.
- **No density profile**: No built-in 1D density profile along an axis.
- **No built-in trajectory transformations**: No on-the-fly PBC unwrapping, centering, etc.
- **Less comprehensive analysis**: Significantly fewer analysis modules than MDAnalysis. Missing: MSD, density, contacts, linear density, polymer analysis, membrane analysis, etc.
- **Whole-trajectory loading**: MDTraj loads the full trajectory positions into memory (`traj.xyz`), which is problematic for large simulations (>100K atoms, >10K frames).

**GROMACS format support detail:**
- `.xtc`: Read support ✓
- `.trr`: Read support ✓
- `.gro`: Read support ✓ (topology + single frame)
- `.tpr`: ✗ Not supported
- `.top` / `.itp`: ✗ Not supported

### freud 3.5.0

**Strengths:**
- **Excellent order parameters**: `freud.order.Steinhardt` (Steinhardt-Nelson bond order parameters q_l), `freud.order.Nematic`, `freud.order.Hexatic`, `freud.order.SolidLiquid`, `freud.order.Cubatic`, `freud.order.ContinuousCoordination`. Best-in-class for structural identification.
- **Fast C++ core**: Parallelized,高性能 implementations. Significantly faster than pure-Python alternatives for RDF, MSD, order parameters.
- **Clean PBC handling**: `freud.box.Box` natively handles periodic boundary conditions. Well-tested for triclinic boxes.
- **Built-in MSD**: `freud.msd.MSD` with FFT-based fast computation.
- **Excellent RDF**: `freud.density.RDF` with proper PBC normalization.
- **Interface detection**: `freud.interface.Interface` identifies particles at an interface (though not as sophisticated as pytim's ITIM).
- **BSD-3-Clause license**: Fully MIT-compatible. No restrictions.
- **Small install**: ~2 MB wheel, minimal dependencies (numpy, rowan for quaternions).
- **Native MDAnalysis integration**: `freud.locality.NeighborQuery.from_system()` accepts MDAnalysis reader frames directly.

**Weaknesses:**
- **No native GROMACS format support**: Cannot read .xtc, .trr, .tpr, or .gro files directly. Must use MDTraj or MDAnalysis as a reader, then convert to freud's `(box, positions)` format.
- **Python 3.12+ requirement (v3.5.0)**: **Incompatible with Python 3.11.** QuickIce's current environment uses Python 3.14 in the yml, but the spec says 3.11. v3.2.0 was the last to support Python 3.11. **CRITICAL: If QuickIce stays on Python 3.11, freud 3.5.0 is not usable.** Would need to pin freud<=3.2.0.
- **No hydrogen bond analysis**: No built-in H-bond detection. Must use MDAnalysis or custom code.
- **No topology reading**: No concept of atom types, residues, bonds. Operates purely on particle positions and box vectors.
- **No atom selection**: No way to select "water oxygens" or "methane molecules" — must pre-filter indices before passing to freud.
- **No trajectory reading**: Does not iterate through frames. You must loop through frames yourself and call `compute()` on each.
- **F3/F4 not directly available**: `freud.order.Steinhardt` provides q_l (spherical harmonics-based), not the tetrahedral F3/F4 order parameters used in water/hydrate analysis. These are different metrics. Steinhardt is useful for crystal structure identification but F3/F4 specifically measure tetrahedral ordering in water.

**GROMACS integration path:**
```python
# Use MDAnalysis as reader, freud as analyzer
import MDAnalysis as mda
import freud

u = mda.Universe('topol.tpr', 'traj.xtc')
oxygen = u.select_atoms('name OW')

rdf = freud.density.RDF(bins=50, r_max=5)
for ts in u.trajectory:
    box = freud.box.Box.from_matrix(ts.triclinic_dimensions)
    rdf.compute(system=(box, oxygen.positions), reset=False)
```

### pytim 1.0.7

**Strengths:**
- **Best interface detection**: Implements ITIM (Intrinsic Thermal Identification of Molecules), GITIM, SASA, Willard-Chandler, and DBSCAN filtering methods. These are the gold standard for identifying molecules at fluid-fluid interfaces.
- **Built on MDAnalysis**: Reads all GROMACS formats through MDAnalysis. Seamlessly works with MDAnalysis Universes.
- **Domain-specific**: Specifically designed for interfacial analysis in molecular simulations, which is directly relevant to hydrate-liquid interface studies.
- **Recently updated**: v1.0.7 released Jun 2026 (literally today). Active maintenance.

**Weaknesses:**
- **GPL-3.0-only license**: **NOT MIT-compatible.** GPL-3.0 is a copyleft license — any code that links to GPL-3.0 must also be GPL-3.0. This makes pytim **incompatible with QuickIce's MIT license** if distributed together. For a conda package, users would install pytim separately, but we could not bundle it or import it as a required dependency.
- **Narrow scope**: Only does interface analysis. No RDF, MSD, H-bonds, order parameters. Must be combined with other libraries.
- **Additional dependency**: Requires MDAnalysis (which we'd already have), adds its own code on top.
- **Small community**: Single primary maintainer (Marcello Sega), smaller user base than MDAnalysis/freud.
- **License is a dealbreaker**: GPL-3.0 is incompatible with QuickIce's MIT license for distribution purposes. We cannot make pytim a required dependency of QuickIce without changing QuickIce's license.

### Custom Implementation (numpy/scipy)

**Strengths:**
- **No new dependencies**: Everything uses existing numpy 2.4.3 + scipy 1.17.1 already in the stack.
- **MIT license**: No licensing concerns.
- **Full control**: Can implement exactly what's needed for hydrate analysis.
- **VTK integration**: VTK is already in the stack — can leverage `vtkProbeFilter`, `vtkCellLocator`, `vtkPointLocator` for spatial queries.
- **Existing .gro/.itp parsers**: QuickIce already has `gro_parser.py` and can build on it.

**Weaknesses:**
- **No trajectory reader**: Would need to implement .xtc/.trr readers. XTC is a compressed binary format requiring XDR library — significant effort (hundreds of lines of C-level code). TRR similarly complex. **This alone makes custom impractical as a primary approach.**
- **PBC handling is hard**: Correct periodic boundary condition handling (wrapping, unwrapping, minimum image convention, make_whole) is notoriously error-prone. Existing libraries have spent years getting this right.
- **RDF from scratch**: ~50-100 lines with scipy, but PBC handling and normalization add complexity.
- **MSD from scratch**: ~30 lines with FFT (scipy.fft), but need correct PBC unwrapping first.
- **H-bond detection**: ~100-200 lines. Must identify donors/acceptors, handle geometric criteria (distance + angle), PBC.
- **F3/F4 from scratch**: ~30-50 lines each. The math is well-documented but neighbor identification with PBC is tricky.
- **Cage occupancy from scratch**: Very hard. Requires identifying clathrate cage types (5^12, 5^12 6^2, 5^12 6^4, etc.), which involves ring-finding algorithms on the hydrogen bond network. Probably 500+ lines of complex graph theory code.
- **Density profile from scratch**: ~30-50 lines with numpy histogram, but PBC handling needed.
- **No .tpr reading**: Would need GROMACS installed or a custom TPR parser (extremely complex binary format).

**Feasibility assessments:**

| Analysis | Lines of Code | Difficulty | Time Estimate | PBC Required? |
|----------|--------------|------------|---------------|---------------|
| RDF (O-O, O-guest) | ~80 | Medium | 2-3 days | Yes |
| MSD | ~50 | Medium | 1-2 days | Yes (unwrap) |
| H-bond analysis | ~150 | Medium-Hard | 3-5 days | Yes (min image) |
| F3 order parameter | ~40 | Medium | 1-2 days | Yes (neighbors) |
| F4 order parameter | ~40 | Medium | 1-2 days | Yes (neighbors) |
| Density profile (1D) | ~30 | Easy | 0.5-1 day | Yes (wrapping) |
| Cage occupancy | ~500+ | Very Hard | 10-20 days | Yes (H-bond network) |
| .xtc reader | ~300+ | Very Hard | 5-10 days | N/A |
| .trr reader | ~200+ | Very Hard | 3-7 days | N/A |

## F3/F4 Order Parameters: Specific Research

F3 and F4 are tetrahedral order parameters specifically used for water structure analysis and hydrate identification. They are **NOT** the same as Steinhardt order parameters (q_l) provided by freud.

**F3**: Measures the deviation of the O-O-O angle from the ideal tetrahedral angle (109.47°).
```python
F3_i = sum_{j,k} [|cos(theta_jik)| * cos(theta_jik) + 0.11]^3 / (3 * n_neighbors * (n_neighbors-1))
```
F3 ≈ 0 for perfect tetrahedral (ice/hydrate), F3 ≈ 0.09 for liquid water.

**F4**: Measures dihedral angle O-O-O-O characteristic of tetrahedral ordering.
```python
F4_i = <cos(3*phi)> where phi is the O-O-O-O dihedral
```
F4 ≈ -0.04 for ice Ih, F4 ≈ 0.02 for liquid water, F4 ≈ -0.01 for hydrate.

**Availability in libraries:**
- MDAnalysis: ✗ Not built-in. Must implement custom `AnalysisBase` subclass. The neighbor finding and PBC infrastructure from MDAnalysis makes this ~50-100 lines.
- MDTraj: ✗ Not available.
- freud: ✗ Not the same as Steinhardt. Could potentially use `freud.environment.LocalDescriptors` to compute spherical harmonics, but F3/F4 are specific geometric formulas, not spherical harmonics.
- Custom: Feasible if you have positions + PBC. MDAnalysis provides the infrastructure to make this much easier.

**Recommendation**: Implement F3/F4 as custom MDAnalysis analysis classes. This leverages MDAnalysis's neighbor finding, PBC handling, and AtomGroup selection, while adding only ~100-150 lines of hydrate-specific code.

## Recommendation

### Primary: MDAnalysis 2.10.0

**Why MDAnalysis over alternatives:**

1. **GROMACS format support is essential and unmatched**: QuickIce generates GROMACS-format files. MDAnalysis reads .tpr (topology + coordinates), .xtc (compressed trajectory), .trr (full-precision trajectory), .gro (coordinates). No other library comes close for GROMACS integration.

2. **The .tpr reader alone is worth it**: MDTraj cannot read .tpr files. freud cannot read any GROMACS format. The .tpr file is the canonical way to get atom types, charges, bond information, and molecule definitions from a GROMACS simulation. Without it, you're limited to .gro files which only contain basic atom names.

3. **PBC handling is critical and hard to get right**: Hydrate simulations have periodic boundary conditions. MDAnalysis provides `make_whole()`, `wrap()`, `unwrap()`, and on-the-fly transformations. Implementing correct PBC from scratch is a significant source of bugs in MD analysis code.

4. **Analysis coverage**: RDF, MSD, H-bonds, density, contacts, linear density — all built-in. Only F3/F4 and cage occupancy need custom implementation.

5. **Atom selection language**: `"resname SOL and name OW"` is invaluable for hydrate systems where you need to select water oxygens, guest molecules, specific cage regions, etc.

6. **LGPL is acceptable**: For a conda/pip-installed Python package, LGPL poses no practical problem. MDAnalysis is a separate library that users install. QuickIce imports it, doesn't embed it.

### Supplementary: freud 3.x (conditional)

**If Python 3.12+ is adopted**, consider freud for:
- `freud.order.Steinhardt` for structural identification (complement to F3/F4)
- `freud.density.RDF` for fast RDF computation
- `freud.msd.MSD` for FFT-based MSD
- `freud.interface.Interface` for basic interface detection

**BUT**: freud 3.5.0 requires Python ≥3.12. If QuickIce stays on Python 3.11, use freud ≤3.2.0 (less ideal) or skip freud entirely.

### NOT recommended: pytim

**Due to GPL-3.0 license incompatibility.** The ITIM and Willard-Chandler interface methods are the best available, but the GPL license makes pytim unsuitable as a required dependency for an MIT-licensed project. If interface analysis becomes critical, consider:
1. Implementing a simpler interface detection method (e.g., z-coordinate binning for flat interfaces, or using freud.interface.Interface)
2. Making pytim an optional dependency with clear license documentation
3. Re-implementing ITIM algorithm from the published literature (the algorithm itself is not copyrighted)

### NOT recommended: Custom trajectory I/O

Writing .xtc/.trr readers from scratch is not practical. The binary formats require XDR library support, and getting the details right (especially for compressed XTC) is substantial work. MDAnalysis or MDTraj must handle trajectory I/O.

### NOT recommended: MDTraj alone

Missing .tpr reading, no MSD, no density profiles, no trajectory transformations, and whole-trajectory memory loading makes MDTraj insufficient as the sole library for hydrate analysis.

## Sources

- MDAnalysis 2.10.0 docs: https://docs.mdanalysis.org/stable/ (HIGH confidence, official documentation)
- MDAnalysis releases: https://github.com/MDAnalysis/mdanalysis/releases (HIGH confidence, verified)
- MDAnalysis PyPI: https://pypi.org/project/MDAnalysis/ (HIGH confidence, verified)
- MDAnalysis coordinate formats: https://docs.mdanalysis.org/stable/documentation_pages/coordinates/init.html (HIGH confidence, verified format table)
- MDTraj 1.11.1 releases: https://github.com/mdtraj/mdtraj/releases (HIGH confidence, verified)
- MDTraj PyPI: https://pypi.org/project/mdtraj/ (HIGH confidence, verified)
- freud 3.5.0 docs: https://freud.readthedocs.io/en/stable/ (HIGH confidence, official documentation)
- freud PyPI: https://pypi.org/project/freud-analysis/ (HIGH confidence, verified)
- freud data inputs (GROMACS integration): https://freud.readthedocs.io/en/stable/topics/datainputs.html (HIGH confidence, verified)
- freud releases: https://github.com/glotzerlab/freud/releases (HIGH confidence, verified)
- pytim 1.0.7 PyPI: https://pypi.org/project/pytim/ (HIGH confidence, verified)
- F3/F4 order parameters: Based on training knowledge of water/hydrate physics literature (MEDIUM confidence — formulas verified against published papers but not against a specific library implementation)
- License compatibility: LGPL compatibility assessment based on FSF licensing guidelines (HIGH confidence for dynamic linking in Python packages)
