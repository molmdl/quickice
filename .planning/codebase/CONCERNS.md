# Codebase Concerns

**Analysis Date:** 2026-04-11

## Tech Debt

**Giant phase_diagram.py module (1132 lines):**
- Issue: Monolithic file with 13 polygon builder functions, diagram rendering, melting curve sampling, shared cache, IAPWS curve plotting, triple point labeling, and CLI main block. Violates single-responsibility principle.
- Files: `quickice/output/phase_diagram.py`
- Impact: Hard to maintain, test, or extend phase polygons. Any change to one polygon risks breaking another. Adding a new ice phase requires editing this single large file in multiple places.
- Fix approach: Extract polygon builders into `quickice/output/polygons.py`, diagram rendering into `quickice/output/diagram_renderer.py`, keep `phase_diagram.py` as orchestrator. Each polygon builder function (`_build_ice_ih_polygon`, etc.) should live in its own module or at least a dedicated file.

**Duplicated diagram rendering logic:**
- Issue: Phase diagram is rendered independently in two places — `quickice/output/phase_diagram.py` (CLI, lines 836-1111) and `quickice/gui/phase_diagram_widget.py` (GUI, lines 323-551). Both build polygons from `_build_phase_polygon_from_curves`, add labels at shapely centroids, plot melting curves, mark triple points, and add Liquid/Vapor labels. The rendering code is copy-pasted with minor differences (font sizes, DPI, figure size, zorder values).
- Files: `quickice/output/phase_diagram.py`, `quickice/gui/phase_diagram_widget.py`
- Impact: Changes to phase colors, labels, or boundary data must be applied in two places. Inconsistencies can creep in — e.g., GUI uses `markersize=4` for triple points (line 519) while CLI uses `markersize=5` (line 1008).
- Fix approach: Extract a shared `_render_phase_diagram(axes, user_t, user_p, font_scale=1.0)` function that both CLI and GUI call. GUI can wrap with canvas-specific setup (Figure, FigureCanvasQTAgg).

**Duplicated Liquid/Vapor label positions:**
- Issue: "Liquid" label at (340, 50) and "Vapor" label at (460, 0.5) are hardcoded in both `quickice/output/phase_diagram.py` lines 944-965 and `quickice/gui/phase_diagram_widget.py` lines 367-392.
- Files: `quickice/output/phase_diagram.py`, `quickice/gui/phase_diagram_widget.py`
- Impact: If labels need repositioning (e.g., new phase region overlaps), both must be updated independently.
- Fix approach: Extract label positions into a shared constant dict in `quickice/output/phase_diagram.py` (e.g., `PHASE_DIAGRAM_LABELS`).

**Duplicated GROMACS .top file generation logic:**
- Issue: `write_top_file()` and `write_interface_top_file()` in `quickice/output/gromacs_writer.py` contain nearly identical GROMACS topology content (atomtypes, moleculetype, atoms, settles, virtual_sites3, exclusions). The only differences are the system name and molecule count.
- Files: `quickice/output/gromacs_writer.py`
- Impact: Any change to topology parameters (charges, LJ params, settles distances) must be applied in two places. Currently ~75 lines duplicated.
- Fix approach: Extract a `_write_top_content(f, system_name, nmol)` helper that both functions call.

**Duplicated `_is_cell_orthogonal()` function:**
- Issue: The `_is_cell_orthogonal()` function is defined identically in three files: `quickice/structure_generation/interface_builder.py` (line 25), `quickice/structure_generation/modes/slab.py` (line 25), and `quickice/structure_generation/modes/pocket.py` (line 26). Each is a 4-line function with the same logic.
- Files: `quickice/structure_generation/interface_builder.py`, `quickice/structure_generation/modes/slab.py`, `quickice/structure_generation/modes/pocket.py`
- Impact: Bug fix in one copy must be replicated to others. Code smell indicating poor module organization.
- Fix approach: Move to a shared utility module (e.g., `quickice/structure_generation/utils.py`) and import from all three locations.

**Backward-compatible `IcePhaseLookup` class:**
- Issue: `IcePhaseLookup` in `quickice/phase_mapping/lookup.py` (lines 395-422) is a wrapper class that only delegates to `lookup_phase()`. It exists purely for backward compatibility with an old polygon-based API. The `__init__` takes a `data_path` arg that is explicitly ignored.
- Files: `quickice/phase_mapping/lookup.py`
- Impact: Dead code that adds confusion. New developers may think `IcePhaseLookup` does something different from `lookup_phase`.
- Fix approach: Mark as deprecated with `warnings.warn` in `__init__`. Remove in next major version.

**Deprecated `atoms_per_molecule` inference in `tile_structure`:**
- Issue: When `atoms_per_molecule=None`, `tile_structure()` in `quickice/structure_generation/water_filler.py` (lines 129-161) uses a fragile heuristic to infer atoms per molecule from total atom count. This emits `DeprecationWarning` but is still callable. The ambiguous case (count divisible by both 3 and 4) raises `ValueError` at runtime.
- Files: `quickice/structure_generation/water_filler.py`
- Impact: All callers in the codebase pass `atoms_per_molecule` explicitly, so the deprecated path is untested dead code. The fallback logic adds ~30 lines of unnecessary complexity.
- Fix approach: Make `atoms_per_molecule` a required parameter (remove None default). All callers already pass it.

**Hardcoded `n_candidates=10` in multiple locations:**
- Issue: The number of candidates to generate (10) is hardcoded in `quickice/gui/workers.py` line 101 (`n_candidates=10`) and `quickice/main.py`. Not configurable by user.
- Files: `quickice/gui/workers.py`, `quickice/main.py`
- Impact: Users cannot control candidate count. Changing it requires code edits. More candidates = better diversity but slower generation.
- Fix approach: Add `--ncandidates` CLI arg and GUI spinbox. Pass through the pipeline.

**Module-level mutable cache for water template:**
- Issue: `_water_template_cache` in `quickice/structure_generation/water_filler.py` (line 21) is a module-level mutable global variable. While it works for single-threaded use, the `global` statement in `load_water_template()` (line 37) and the pattern of checking-then-setting is not thread-safe.
- Files: `quickice/structure_generation/water_filler.py`
- Impact: If two threads call `load_water_template()` simultaneously, both could read the template file and overwrite each other's cache (benign race — same data, but wasteful). Low severity since QuickIce uses sequential generation.
- Fix approach: Use `functools.lru_cache` or a threading lock for thread safety.

**Broad `except Exception` handlers throughout codebase:**
- Issue: At least 15 locations use `except Exception as e:` or `except Exception:` to catch all exceptions. Key locations include `quickice/structure_generation/generator.py` line 143, `quickice/gui/workers.py` lines 126 and 219, all five export methods in `quickice/gui/export.py`, and `quickice/output/orchestrator.py` lines 77/105/123. These catch `KeyboardInterrupt`, `SystemExit`, and programming errors (typos, attribute errors) that should propagate.
- Files: `quickice/structure_generation/generator.py`, `quickice/gui/workers.py`, `quickice/gui/export.py`, `quickice/output/orchestrator.py`
- Impact: Bugs and unexpected errors are silently caught and presented as user-facing error messages, making debugging harder. For example, a typo in `generator.py`'s `_generate_single` would be wrapped as a `StructureGenerationError` with the original traceback lost.
- Fix approach: Catch specific exceptions (`ValueError`, `RuntimeError`, `InterfaceGenerationError`). Let programming errors (`AttributeError`, `TypeError`, `KeyError`) propagate. Use `except StructureGenerationError` in interface_builder.py instead of blanket catch.

**Unused `QMessageBox.StandardButton.Ok` and non-idiomatic PySide6 usage:**
- Issue: `quickice/gui/main_window.py` uses `QMessageBox.StandardButton.Ok` (line 393) and `QMessageBox.Yes | QMessageBox.No` (lines 80-84 in export.py) which work but are verbose. More critically, `QMessageBox.critical()` returns a StandardButton but the return value is ignored everywhere, so the user cannot dismiss the error dialog in a meaningful way.
- Files: `quickice/gui/main_window.py`, `quickice/gui/export.py`
- Impact: Minor — dialog UX works but code is more verbose than needed.
- Fix approach: Use simpler `QMessageBox.critical(self, "Title", "Message")` form. Consider returning dialog results when user choice matters.

## Known Bugs

**Pressure validation range inconsistency:**
- Symptoms: CLI validates pressure as 0-10000 MPa (`quickice/validation/validators.py`), but the phase diagram extends to 100000 MPa (100 GPa) for Ice X. Users entering P > 10000 MPa for Ice X conditions get rejected by CLI validation.
- Files: `quickice/validation/validators.py`, `quickice/gui/validators.py`
- Trigger: `python quickice.py --temperature 200 --pressure 40000` (Ice X conditions)
- Workaround: None for CLI. Must increase upper bound or add `--allow-extreme` flag.

**Liquid region phase lookup returns UnknownPhaseError instead of Liquid:**
- Symptoms: `lookup_phase()` raises `UnknownPhaseError` for conditions in the liquid region (e.g., T=350K, P=50 MPa). The error message says "No ice phase found" which is technically correct but confusing — liquid water IS a valid phase.
- Files: `quickice/phase_mapping/lookup.py` (lines 384-392)
- Trigger: Any T,P in the liquid region above the melting curve
- Workaround: GUI's `PhaseDetector` returns "Liquid" via polygon fallback (line 155 of `phase_diagram_widget.py`), but CLI crashes with error.

**Input panel validation range too narrow for pressure:**
- Symptoms: `_on_input_changed()` in `quickice/gui/main_window.py` (line 567) only updates diagram marker if `0.1 <= pressure <= 10000`. This excludes Ice X conditions (P > 30000 MPa). Users with extreme pressure inputs see no diagram marker update.
- Files: `quickice/gui/main_window.py` line 567
- Trigger: Type pressure > 10000 MPa in GUI input field
- Workaround: Manually click on diagram instead of typing

**VTK availability detection is fragile:**
- Symptoms: `_VTK_AVAILABLE` in both `quickice/gui/view.py` (lines 21-34) and `quickice/gui/interface_panel.py` (lines 28-42) uses a heuristic: if `DISPLAY` env var contains 'localhost', assume SSH X11 forwarding and disable VTK unless `QUICKICE_FORCE_VTK=true`. This misclassifies legitimate local displays (e.g., Wayland with XWayland, WSLg, Docker with local X socket) that set `DISPLAY=:0` or `DISPLAY=:1`.
- Files: `quickice/gui/view.py`, `quickice/gui/interface_panel.py`
- Trigger: Run on Wayland-based system or WSL2 with GUI support
- Workaround: Set `QUICKICE_FORCE_VTK=true` environment variable
- Fix approach: Try importing and creating a VTK render window, catch the specific `vtkXOpenGLRenderWindow` error, rather than relying on DISPLAY heuristic.

**Duplicate `from shapely.geometry import Polygon as ShapelyPolygon` in same function:**
- Symptoms: In `quickice/output/phase_diagram.py`, `generate_phase_diagram()` imports `ShapelyPolygon` on line 864 and again on line 894, within the same function. While not a runtime bug, it indicates the function is too long and was likely written in stages.
- Files: `quickice/output/phase_diagram.py` lines 864, 894
- Impact: Minor — redundant import, no functional impact.

**Tab 2 candidate dropdown index mismatch:**
- Symptoms: `InterfacePanel.update_candidates()` blocks signals while clearing and repopulating the dropdown (`quickice/gui/interface_panel.py` lines 534-557). However, `MainWindow._on_interface_generate()` uses `candidate_index` to index into `ranking_result.ranked_candidates` (line 432). If the candidate list changes between UI display and generation, the wrong candidate could be used.
- Files: `quickice/gui/interface_panel.py`, `quickice/gui/main_window.py`
- Trigger: Rapid candidate refresh + generate click
- Impact: Low — unlikely in practice due to UI disable during generation.

## Security Considerations

**Output path traversal check is fragile:**
- Risk: `output_ranked_candidates()` in `quickice/output/orchestrator.py` (lines 48-56) checks that the resolved output path starts with CWD using string prefix matching: `str(output_path).startswith(str(allowed_base))`. This can match false positives — e.g., `/home/user/quickice2` matches `/home/user/quickice`. Symlinks under CWD pointing outside would pass the check after `resolve()`.
- Files: `quickice/output/orchestrator.py`
- Current mitigation: `Path.resolve()` resolves symlinks, which helps but doesn't prevent the prefix-matching false positive.
- Recommendations: Use `pathlib.Path.is_relative_to()` (Python 3.9+) instead of string prefix matching.

**GROMACS file write without overwrite check in CLI:**
- Risk: `quickice/main.py` writes .gro, .top, and .itp files to `args.output` directory using `mkdir(parents=True, exist_ok=True)` and direct file writes. No check for existing files before overwrite. Could silently overwrite user data.
- Files: `quickice/main.py`
- Current mitigation: GUI export shows overwrite dialog (`quickice/gui/export.py`). CLI does not.
- Recommendations: Add `--force` flag or prompt before overwrite in CLI.

**No input sanitization on T,P in diagram text output:**
- Risk: `quickice/output/phase_diagram.py` (lines 1088-1090) writes user-supplied temperature and pressure directly to text file. Values are floats, so injection risk is minimal, but the pattern is worth noting.
- Files: `quickice/output/phase_diagram.py`
- Current mitigation: Values validated as floats upstream. Low risk.

**No rate limiting on diagram click events:**
- Risk: `PhaseDiagramCanvas._on_click()` in `quickice/gui/phase_diagram_widget.py` (line 567) fires on every click without debouncing. Rapid clicks trigger multiple `coordinates_selected` signals, each calling `lookup_phase()` and updating the input panel. Could cause UI lag on slow systems.
- Files: `quickice/gui/phase_diagram_widget.py`
- Current mitigation: Phase lookup is fast (~1ms). Low risk.
- Recommendations: Add 100ms debounce timer if performance becomes an issue.

## Performance Bottlenecks

**PhaseDetector builds all 13 shapely polygons on every init:**
- Problem: `PhaseDetector.__init__()` in `quickice/gui/phase_diagram_widget.py` (lines 41-89) builds shapely polygons for all 12 ice phases plus the vapor polygon by calling `_build_phase_polygon_from_curves()` and `IAPWS97()` for each. Each polygon construction involves numpy linspace operations, boundary function evaluations, and IAPWS thermodynamic calculations.
- Files: `quickice/gui/phase_diagram_widget.py`
- Cause: PhaseDetector is instantiated in `PhaseDiagramCanvas.__init__()`, which is called once per application start. The cost is paid at startup (~1-2 seconds delay).
- Improvement path: Cache PhaseDetector instance at module level (similar to `_SHARED_BOUNDARY_CACHE` pattern in `phase_diagram.py`). Since phase boundaries never change, rebuild on every canvas creation is wasteful.

**Duplicate phase polygon construction (two separate builds per session):**
- Problem: Phase polygons are built TWICE — once for `PhaseDetector` in `quickice/gui/phase_diagram_widget.py` and once for diagram rendering in `PhaseDiagramCanvas._setup_diagram()`. Both call `_build_phase_polygon_from_curves()` for all 12 phases. Each polygon construction involves boundary function evaluation and numpy operations.
- Files: `quickice/gui/phase_diagram_widget.py`
- Cause: No shared cache between the detector and the renderer. The `_SHARED_BOUNDARY_CACHE` in `phase_diagram.py` caches boundary vertices but not the full polygon objects.
- Improvement path: Build polygons once, store in a module-level dict, share between PhaseDetector and canvas rendering.

**cKDTree supercell approach is O(27n) in scorer and validator:**
- Problem: Both `quickice/ranking/scorer.py` (lines 54-61) and `quickice/output/validator.py` build 3x3x3 supercells for PBC handling by explicitly replicating atom positions 27 times. For large systems (>1000 molecules), this creates significant memory overhead. In contrast, `quickice/structure_generation/overlap_resolver.py` already uses the `boxsize` parameter correctly.
- Files: `quickice/ranking/scorer.py`, `quickice/output/validator.py`
- Cause: Legacy approach before cKDTree supported `boxsize` parameter. The overlap_resolver module was written later and uses the modern approach.
- Improvement path: Replace supercell approach with `cKDTree(positions, boxsize=cell_dims)` which handles PBC internally. This reduces memory from 27x to 1x and is the same pattern already used in `overlap_resolver.py`.

**H-bond detection is O(n²) in vtk_utils:**
- Problem: `detect_hydrogen_bonds()` in `quickice/gui/vtk_utils.py` (lines 258-292) uses nested loops over all H and O atoms with PBC distance checks. This is O(n_H × n_O) per structure. For a typical 96-molecule structure: ~192 H × 96 O = 18,432 distance calculations, each requiring cell matrix inversion.
- Files: `quickice/gui/vtk_utils.py`
- Cause: Brute-force approach for simplicity. The cell matrix inversion (`np.linalg.inv(cell)`) is computed inside `_pbc_distance()` for every pair — this could be cached.
- Improvement path: (1) Cache `cell_inv` outside the loop. (2) Use cKDTree with `boxsize` for O(n log n) neighbor search, similar to `overlap_resolver.py` pattern.

**Molecule-by-molecule filtering loop in tile_structure:**
- Problem: `tile_structure()` in `quickice/structure_generation/water_filler.py` (lines 209-233) iterates over every molecule in a Python for-loop to check if all atoms are inside the target region. For large systems (10,000+ molecules), this is slow due to Python loop overhead.
- Files: `quickice/structure_generation/water_filler.py`
- Cause: Need to check molecule-level completeness (all atoms inside), which requires per-molecule logic.
- Improvement path: Vectorize using numpy — reshape positions to (n_molecules, atoms_per_molecule, 3) and use `np.all()` on the reshaped array.

**Water molecule wrapping loop in tile_structure:**
- Problem: After filtering, `tile_structure()` (lines 244-284) iterates molecule-by-molecule to apply PBC wrapping with a two-pass correction. This is O(n_molecules) in Python, slow for large counts.
- Files: `quickice/structure_generation/water_filler.py`
- Cause: Molecule-centric wrapping requires checking min/max across atoms of each molecule, which is hard to vectorize correctly.
- Improvement path: Use numpy broadcasting to compute min/max per molecule across all atoms simultaneously, then apply shifts in batch.

## Fragile Areas

**Phase boundary between II, IX, XV at low temperatures:**
- Files: `quickice/phase_mapping/lookup.py` (lines 228-309), `quickice/phase_mapping/solid_boundaries.py`
- Why fragile: The Ice II region at T < 140K has complex interactions with Ice IX (P=200-400 MPa) and Ice XV (P=950-2100 MPa). The lookup order in `lookup_phase()` checks XV first (line 231), then VI gap-fill (line 240), then IX (line 306), then II (line 315). Any reorder or boundary change could cause a phase to "win" incorrectly. The polygon builders for II, IX, XV use hardcoded pressure values (950 MPa, 400 MPa) rather than curve functions, creating potential inconsistency between lookup and diagram.
- Safe modification: When changing phase boundaries, test both `lookup_phase()` AND `_build_phase_polygon_from_curves()` for the same T,P points. Run existing test suite (`tests/test_phase_mapping.py` with 62 tests).
- Test coverage: Good for lookup (62 tests). Missing for polygon-boundary consistency.

**GRO format parsing relies on fixed column widths:**
- Files: `quickice/structure_generation/generator.py` (lines 176-188), `quickice/structure_generation/water_filler.py` (lines 55-63)
- Why fragile: GRO format parsing uses hardcoded column indices (`line[10:15]`, `line[20:28]`, `line[28:36]`, `line[36:44]`). Any deviation in GenIce's output format (extra whitespace, different precision) would silently produce wrong coordinates. The parsing code has no format validation or error checking.
- Safe modification: Add roundtrip tests that generate → parse → verify positions match within tolerance. Add format validation (check line length, numeric format) before parsing.

**Atom ordering assumptions throughout codebase:**
- Files: `quickice/gui/vtk_utils.py` (lines 80-91), `quickice/output/gromacs_writer.py` (lines 59-87), `quickice/ranking/scorer.py` (lines 42-43)
- Why fragile: Multiple modules assume atoms are ordered as O, H, H (TIP3P) or OW, HW1, HW2, MW (TIP4P) per molecule. If GenIce changes its output ordering, bond creation and MW position computation would produce wrong results. Some modules validate this (`vtk_utils` raises ValueError on mismatch at line 87), but `gromacs_writer` and `scorer` do NOT validate.
- Safe modification: Always validate atom ordering at function entry (follow `vtk_utils` pattern). Add validation to `gromacs_writer.write_gro_file` and `scorer._calculate_oo_distances_pbc`.

**Thread cancellation with 100ms timeout:**
- Files: `quickice/gui/viewmodel.py` (lines 71-76, 107-112, 186-191, 222-227)
- Why fragile: Both `start_generation()` and `cancel_generation()` call `thread.wait(100)` with only 100ms timeout. If the worker thread is in the middle of GenIce generation (which can take seconds), the thread won't actually stop. The old thread object is scheduled for deletion (`deleteLater`) but the Python thread may continue running, potentially causing issues if a new generation starts while the old one is still executing.
- Safe modification: Track whether a worker is truly finished before starting a new one. Add worker state checking with `QThread.isFinished()` instead of `QThread.isRunning()`. Consider `thread.wait(5000)` with longer timeout in cancel.

**PhaseDetector boundary detection uses two different tolerance approaches:**
- Files: `quickice/gui/phase_diagram_widget.py` (lines 93-202)
- Why fragile: `_check_near_boundary()` uses a fixed 5 MPa tolerance (line 188), while `_is_near_boundary()` uses a default 10 MPa tolerance parameter (line 204). The class attribute `BOUNDARY_TOLERANCE_PRESSURE_FRAC` (line 97, 5% relative) is defined but never used. The `detect_phase()` method calls `_is_near_boundary` with the 10 MPa tolerance, ignoring the class attribute. This is confusing and could lead to incorrect boundary detection.
- Safe modification: Consolidate boundary detection into a single method with a single tolerance strategy. Use the relative tolerance approach (BOUNDARY_TOLERANCE_PRESSURE_FRAC) for better scaling across the pressure range.

**Slice indexing in _build_ice_iii_polygon:**
- Files: `quickice/output/phase_diagram.py` (line 508)
- Why fragile: `_build_ice_iii_polygon()` uses `T_vals[1:-1]` (line 508) which skips both endpoints of the II-III boundary. This assumes the triple points are already in the vertices list and should not be duplicated. If the boundary function evaluation at a triple point disagrees with the stored triple point value, there will be a gap or overlap in the polygon.
- Safe modification: Use `T_vals[1:]` and ensure triple point values match boundary function output at those temperatures. Add assertions.

## Scaling Limits

**Large molecule count generation:**
- Current capacity: `validate_nmolecules` in `quickice/validation/validators.py` allows up to 100,000 molecules.
- Limit: GenIce generation for 100,000 molecules would take minutes and use significant memory (each molecule has 3-4 atoms, so 400,000+ positions). The 3x3x3 supercell approach in `scorer.py` and `validator.py` would create 27x memory overhead (~10.8 million atom positions). The H-bond detection loop in `vtk_utils.py` would be O(n²) = 10 billion operations.
- Scaling path: Replace supercell approach with `boxsize`-based cKDTree. Vectorize molecule filtering in `tile_structure`. Use cKDTree for H-bond detection. Consider lazy candidate generation for large counts.

**Phase diagram rendering with many phases:**
- Current capacity: 12 ice phases rendered
- Limit: Adding more phases (Ice XVII, Ice XIX, etc.) would increase polygon computation and shapely operations proportionally. No architectural limit, but performance degrades linearly and the diagram becomes visually crowded.
- Scaling path: Cache phase polygons after first build (already partially done via `_SHARED_BOUNDARY_CACHE`). Consider lazy polygon building — only build polygons for phases visible in current view.

**Interface generation with large boxes:**
- Current capacity: Box dimensions up to 100 nm per side (UI spinbox limit in `quickice/gui/interface_panel.py` lines 278-306)
- Limit: A 100×100×100 nm box would contain ~33 million water molecules (at ~1g/cm³). Water template tiling and overlap detection would be extremely slow. The molecule-by-molecule filtering loop in `tile_structure` would iterate millions of times.
- Scaling path: Add maximum box size warning in validation. Optimize `tile_structure` with vectorized filtering. Consider chunked generation for very large boxes.

## Dependencies at Risk

**genice2 (v2.2.13.1):**
- Risk: GenIce2 is a specialized academic package with a small maintainer base. It uses the legacy `np.random.seed()` global state API (noted in `quickice/structure_generation/generator.py` lines 84-97). If GenIce2 stops being maintained or breaks with newer numpy (numpy 2.0+ removed some legacy APIs), QuickIce's core functionality (structure generation) would be broken.
- Impact: All ice structure generation fails. No alternative library provides the same lattice generation + hydrogen bond network randomization.
- Migration plan: Pin numpy <2.0 in requirements if needed. Consider forking GenIce2's critical path (Lattice + GenIce + depol) into QuickIce as a vendored dependency.

**Python 3.14 dependency:**
- Risk: `environment.yml` specifies `python=3.14.3`. Python 3.14 is very new (released 2025-2026). Many scientific packages may not yet fully support it.
- Impact: If any dependency (GenIce2, spglib, iapws) fails on Python 3.14, the entire application breaks.
- Migration plan: Test with Python 3.12 as a fallback. Keep `environment.yml` updated. Consider specifying `python>=3.12` instead of pinning to 3.14.

**iapws package for water thermodynamics:**
- Risk: The `iapws` package is used for IAPWS97 calculations (liquid-vapor boundary, melting curves). It's a niche package with limited maintenance. Its exception handling is inconsistent (raises generic `Exception` in some cases), caught by broad `except Exception` blocks in `quickice/output/phase_diagram.py` lines 953 and `quickice/gui/phase_diagram_widget.py` lines 78-79 and 480.
- Impact: Phase diagram rendering and liquid region detection would fail without IAPWS. The broad exception catches hide failures silently.
- Migration plan: Implement critical IAPWS R14-08 equations directly (they're relatively simple polynomial/Simon-Glatzel fits). This would also eliminate the broad `except Exception` blocks.

**shapely for polygon containment checks:**
- Risk: `shapely` is used for polygon containment checks in `PhaseDetector` and centroid calculation for phase labels. It's a well-maintained GEOS wrapper but adds a C dependency (GEOS library). If GEOS is unavailable on a platform, the GUI phase detection and label placement would fail.
- Impact: Phase diagram click detection and label placement would break. Diagram could still render (using matplotlib Polygon patches) but detection would fail.
- Migration plan: Implement simple point-in-polygon test (ray casting) for the detector. Use matplotlib's built-in centroid approximation for labels.

## Missing Critical Features

**No triclinic cell support for interface generation:**
- Problem: Ice II and Ice V produce triclinic (non-orthogonal) cells. The interface builder explicitly rejects these with `InterfaceGenerationError` in three places (`interface_builder.py` line 120, `slab.py` line 64, `pocket.py` line 66). Users who generate Ice II or Ice V cannot create interface structures.
- Blocks: Ice II and Ice V interface construction — two of the most scientifically interesting phases for interface studies.
- Files: `quickice/structure_generation/interface_builder.py`, `quickice/structure_generation/modes/slab.py`, `quickice/structure_generation/modes/pocket.py`

**No undo/redo in GUI:**
- Problem: Users cannot undo accidental input changes or diagram clicks. No way to revert to previous T,P state.
- Blocks: Quick recovery from mistakes requires re-typing values.

**No persistent user preferences:**
- Problem: Window size, splitter positions, last-used T/P values are not saved between sessions. Users must re-enter everything each time.
- Blocks: Efficient repeated use of the application.

**No progress reporting for individual candidate generation:**
- Problem: Worker emits progress at fixed points (10%, 20%, 60%, 90%, 100%) regardless of how many candidates are generated. For 10 candidates, each candidate takes ~6% of total time but there's no per-candidate progress.
- Files: `quickice/gui/workers.py` lines 84-121
- Blocks: User cannot estimate remaining time for large nmolecules.

**No export format for LAMMPS or CIF:**
- Problem: Only PDB and GROMACS formats are supported. No LAMMPS data file or CIF export. Many MD simulation groups use LAMMPS, and crystallographers use CIF.
- Blocks: Users must manually convert PDB to LAMMPS/CIF format.

## Test Coverage Gaps

**GUI layer has zero test coverage:**
- What's not tested: All of `quickice/gui/` (16+ files, ~5000+ lines) — MainWindow, ViewModels, Workers, Exporters, PhaseDiagramPanel, VTK viewers, InterfacePanel.
- Files: `quickice/gui/` (entire directory)
- Risk: Any GUI regression (broken signal connections, dialog errors, thread safety issues) goes undetected until manual testing. The most complex parts (thread management, signal wiring, VTK rendering) are the least tested.
- Priority: High — GUI is the primary user interface.

**No integration test for full CLI pipeline with GROMACS export:**
- What's not tested: End-to-end test running `quickice.py --temperature 250 --pressure 500 --gromacs` and verifying .gro, .top, .itp output files are valid GROMACS format.
- Files: `tests/test_cli_integration.py` (292 lines but doesn't test GROMACS export path)
- Risk: GROMACS export could break silently (wrong atom counts, incorrect box vectors) without detection.
- Priority: High — GROMACS export is a key deliverable.

**No polygon-boundary consistency tests:**
- What's not tested: Whether `_build_phase_polygon_from_curves()` produces polygons that are consistent with `lookup_phase()`. A point inside the polygon should map to the same phase that `lookup_phase` returns.
- Files: `quickice/output/phase_diagram.py`, `quickice/phase_mapping/lookup.py`
- Risk: Polygon and lookup could diverge (different boundary values, different ordering logic), producing inconsistent results between diagram display and actual generation. The II/IX/XV region is most at risk since polygon builders use hardcoded pressures while lookup uses boundary functions.
- Priority: Medium — Would catch the II/IX/XV boundary inconsistency.

**No test for triclinic cell rejection in interface builder:**
- What's not tested: `is_cell_orthogonal()` and the triclinic rejection path in `validate_interface_config()`. No test creates a triclinic candidate and verifies the error is raised.
- Files: `quickice/structure_generation/interface_builder.py` (lines 119-131)
- Risk: If triclinic detection logic has a bug (wrong tolerance, wrong off-diagonal check), invalid cells could pass through and produce corrupt interface structures.
- Priority: Medium — ice_ii and ice_v produce triclinic cells.

**No test for thread cancellation behavior:**
- What's not tested: What happens when generation is cancelled mid-stream? Does the old thread actually stop? Are resources properly cleaned up? Does starting a new generation while an old one is running cause issues?
- Files: `quickice/gui/viewmodel.py`, `quickice/gui/workers.py`
- Risk: Thread leak or zombie generation continuing after user clicks Cancel.
- Priority: Medium — Directly affects user experience.

**No test for overlap detection edge cases:**
- What's not tested: Overlaps at exact box boundaries (atoms at x=0 and x=lx), zero-length distances, or single-molecule structures.
- Files: `quickice/structure_generation/overlap_resolver.py`
- Risk: Edge case overlaps could cause incorrect molecule removal or index errors.
- Priority: Low — Unlikely in practice but correctness matters.

**No test for interface structure generation:**
- What's not tested: End-to-end tests for `assemble_slab()`, `assemble_pocket()`, `assemble_piece()`. The interface modes are tested individually for validation (e.g., `test_piece_mode_validation.py`, `test_med03_minimum_box_size.py`) but there's no test that actually generates a complete interface structure and verifies atom counts, positions, and phase separation.
- Files: `quickice/structure_generation/modes/slab.py`, `quickice/structure_generation/modes/pocket.py`, `quickice/structure_generation/modes/piece.py`
- Risk: Interface generation could produce incorrect structures (wrong water count, overlapping atoms, incorrect cell dimensions) without detection.
- Priority: High — Interface generation is a core feature of v3.0.

---

*Concerns audit: 2026-04-11*
