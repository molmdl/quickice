# Codebase Concerns

**Analysis Date:** 2026-04-10

## Tech Debt

**Giant phase_diagram.py module (1116 lines):**
- Issue: Monolithic file with 13 polygon builder functions, diagram rendering, melting curve sampling, and shared cache all in one module. Violates single-responsibility principle.
- Files: `quickice/output/phase_diagram.py`
- Impact: Hard to maintain, test, or extend phase polygons. Any change to one polygon risks breaking another.
- Fix approach: Extract polygon builders into `quickice/output/polygons.py`, diagram rendering into `quickice/output/diagram_renderer.py`, keep phase_diagram.py as orchestrator.

**Duplicated diagram rendering logic:**
- Issue: Phase diagram is rendered independently in two places — `quickice/output/phase_diagram.py` (CLI) and `quickice/gui/phase_diagram_widget.py` (GUI). Both build polygons from `_build_phase_polygon_from_curves`, add labels at shapely centroids, plot melting curves, mark triple points, and add Liquid/Vapor labels. The rendering code is copy-pasted with minor differences (font sizes, DPI, figure size).
- Files: `quickice/output/phase_diagram.py`, `quickice/gui/phase_diagram_widget.py`
- Impact: Changes to phase colors, labels, or boundary data must be applied in two places. Inconsistencies can creep in.
- Fix approach: Extract a shared `_render_phase_diagram(axes, user_t, user_p, figsize)` function that both CLI and GUI call. GUI can wrap with canvas-specific setup.

**Duplicated Liquid/Vapor label positions:**
- Issue: "Liquid" label at (340, 50) and "Vapor" label at (460, 0.5) are hardcoded in both `quickice/output/phase_diagram.py` lines 944-965 and `quickice/gui/phase_diagram_widget.py` lines 367-392.
- Files: `quickice/output/phase_diagram.py`, `quickice/gui/phase_diagram_widget.py`
- Impact: If labels need repositioning (e.g., new phase region overlaps), both must be updated.
- Fix approach: Extract label positions into a shared constant dict.

**Duplicated top file generation logic:**
- Issue: `write_top_file()` and `write_interface_top_file()` in `quickice/output/gromacs_writer.py` contain nearly identical GROMACS topology content (atomtypes, moleculetype, atoms, settles, virtual_sites3, exclusions). The only differences are the system name and molecule count.
- Files: `quickice/output/gromacs_writer.py` (lines 98-164 vs 289-357)
- Impact: Any change to topology parameters (charges, LJ params, settles distances) must be applied in two places.
- Fix approach: Extract a `_write_top_content(f, system_name, nmol)` helper that both functions call.

**Backward-compatible `IcePhaseLookup` class:**
- Issue: `IcePhaseLookup` in `quickice/phase_mapping/lookup.py` (lines 373-400) is a wrapper class that only delegates to `lookup_phase()`. It exists purely for backward compatibility with an old polygon-based API. The `__init__` takes a `data_path` arg that is explicitly ignored.
- Files: `quickice/phase_mapping/lookup.py`
- Impact: Dead code that adds confusion. New developers may think `IcePhaseLookup` does something different from `lookup_phase`.
- Fix approach: Mark as deprecated with `warnings.warn` in `__init__`. Remove in next major version.

**Deprecated `atoms_per_molecule` inference in `tile_structure`:**
- Issue: When `atoms_per_molecule=None`, `tile_structure()` in `quickice/structure_generation/water_filler.py` (lines 129-161) uses a fragile heuristic to infer atoms per molecule from total atom count. This emits `DeprecationWarning` but is still callable.
- Files: `quickice/structure_generation/water_filler.py`
- Impact: Ambiguous case (count divisible by both 3 and 4) raises `ValueError` at runtime instead of being caught at call time. All callers in the codebase pass `atoms_per_molecule` explicitly, so the deprecated path is untested.
- Fix approach: Make `atoms_per_molecule` a required parameter (remove None default). All callers already pass it.

**Hardcoded `n_candidates=10` in multiple locations:**
- Issue: The number of candidates to generate (10) is hardcoded in `quickice/main.py` line 46, `quickice/gui/workers.py` line 101, and possibly elsewhere. Not configurable by user.
- Files: `quickice/main.py`, `quickice/gui/workers.py`
- Impact: Users cannot control candidate count. Changing it requires code edits.
- Fix approach: Add `--ncandidates` CLI arg and GUI spinbox. Pass through the pipeline.

## Known Bugs

**Pressure validation range inconsistency:**
- Symptoms: CLI validates pressure as 0-10000 MPa (`quickice/validation/validators.py` line 56), but the GUI `quickice/gui/validators.py` likely uses a different range. The phase diagram extends to 100000 MPa (100 GPa) for Ice X. Users entering P > 10000 MPa for Ice X conditions get rejected by CLI validation.
- Files: `quickice/validation/validators.py`, `quickice/gui/validators.py`
- Trigger: `python quickice.py --temperature 200 --pressure 40000` (Ice X conditions)
- Workaround: None for CLI. Must increase upper bound or add `--allow-extreme` flag.

**Liquid region phase lookup returns UnknownPhaseError instead of Liquid:**
- Symptoms: `lookup_phase()` raises `UnknownPhaseError` for conditions in the liquid region (e.g., T=350K, P=50 MPa). The error message says "No ice phase found" which is technically correct but confusing — liquid water IS a valid phase.
- Files: `quickice/phase_mapping/lookup.py` (lines 366-370)
- Trigger: Any T,P in the liquid region above the melting curve
- Workaround: GUI's PhaseDetector returns "Liquid" via polygon fallback, but CLI crashes with error.

**Input panel validation range too narrow for pressure:**
- Symptoms: `_on_input_changed()` in `quickice/gui/main_window.py` (line 567) only updates diagram marker if 0.1 <= pressure <= 10000. This excludes Ice X conditions (P > 30000 MPa). Users with extreme pressure inputs see no diagram marker update.
- Files: `quickice/gui/main_window.py` line 567
- Trigger: Type pressure > 10000 MPa in GUI input field
- Workaround: Manually click on diagram instead of typing

## Security Considerations

**Output path traversal check is fragile:**
- Risk: `output_ranked_candidates()` in `quickice/output/orchestrator.py` (lines 48-56) checks that the resolved output path starts with CWD. This can be bypassed with symlinks — a symlink under CWD pointing outside would pass the check. Also, `str(output_path).startswith(str(allowed_base))` is string-based and could match false positives (e.g., `/home/user/quickice2` matches `/home/user/quickice`).
- Files: `quickice/output/orchestrator.py`
- Current mitigation: Path.resolve() is used to resolve symlinks, which helps but doesn't prevent the prefix-matching false positive.
- Recommendations: Use `pathlib.Path.is_relative_to()` (Python 3.9+) instead of string prefix matching.

**GROMACS file write without atomic overwrite check in CLI:**
- Risk: `quickice/main.py` (lines 73-126) writes .gro, .top, and .itp files to `args.output` directory using `mkdir(parents=True, exist_ok=True)` and direct file writes. No check for existing files before overwrite. Could silently overwrite user data.
- Files: `quickice/main.py`
- Current mitigation: GUI export shows overwrite dialog (`quickice/gui/export.py`). CLI does not.
- Recommendations: Add `--force` flag or prompt before overwrite in CLI.

**No input sanitization on T,P in diagram text output:**
- Risk: `quickice/output/phase_diagram.py` (lines 1088-1090) writes user-supplied temperature and pressure directly to text file. Values are floats, so injection risk is minimal, but the pattern is worth noting.
- Files: `quickice/output/phase_diagram.py`
- Current mitigation: Values validated as floats upstream. Low risk.

## Performance Bottlenecks

**PhaseDetector builds all 13 shapely polygons on every init:**
- Problem: `PhaseDetector.__init__()` in `quickice/gui/phase_diagram_widget.py` (lines 41-89) builds shapely polygons for all 12 ice phases plus the vapor polygon by calling `_build_phase_polygon_from_curves()` and `IAPWS97()` for each. This is computationally expensive (multiple numpy linspace + boundary function evaluations + IAPWS calculations).
- Files: `quickice/gui/phase_diagram_widget.py`
- Cause: PhaseDetector is instantiated in `PhaseDiagramCanvas.__init__()` which is called once per application start. The cost is paid at startup but noticeable (~1-2 seconds delay).
- Improvement path: Cache PhaseDetector instance at module level (similar to `_SHARED_BOUNDARY_CACHE` pattern in phase_diagram.py). Since phase boundaries never change, rebuild on every canvas creation is wasteful.

**Duplicate phase polygon construction:**
- Problem: Phase polygons are built TWICE — once for PhaseDetector in `quickice/gui/phase_diagram_widget.py` and once for diagram rendering in `PhaseDiagramCanvas._setup_diagram()`. Both call `_build_phase_polygon_from_curves()` for all 12 phases. Each polygon construction involves boundary function evaluation and numpy operations.
- Files: `quickice/gui/phase_diagram_widget.py`
- Cause: No shared cache between the detector and the renderer.
- Improvement path: Build polygons once, share between PhaseDetector and canvas rendering.

**cKDTree supercell approach is O(27n):**
- Problem: Both `quickice/ranking/scorer.py` (lines 54-61) and `quickice/output/validator.py` (lines 119-126) build 3x3x3 supercells for PBC handling by explicitly replicating atom positions 27 times. For large systems (>1000 molecules), this creates significant memory overhead.
- Files: `quickice/ranking/scorer.py`, `quickice/output/validator.py`
- Cause: Legacy approach before cKDTree supported `boxsize` parameter.
- Improvement path: Replace supercell approach with `cKDTree(positions, boxsize=cell_dims)` which handles PBC internally (already done in `quickice/structure_generation/overlap_resolver.py`). This reduces memory from 27x to 1x.

**H-bond detection is O(n²):**
- Problem: `detect_hydrogen_bonds()` in `quickice/gui/vtk_utils.py` (lines 220-238) uses nested loops over all H and O atoms with PBC distance checks. This is O(n_H × n_O) per structure.
- Files: `quickice/gui/vtk_utils.py`
- Cause: Brute-force approach for simplicity.
- Improvement path: Use cKDTree with `boxsize` for O(n log n) neighbor search, similar to overlap_resolver.py pattern.

## Fragile Areas

**Phase boundary between II, IX, XV at low temperatures:**
- Files: `quickice/phase_mapping/lookup.py` (lines 228-309), `quickice/phase_mapping/solid_boundaries.py`
- Why fragile: The Ice II region at T < 140K has complex interactions with Ice IX (P=200-400 MPa) and Ice XV (P=950-2100 MPa). The lookup order in `lookup_phase()` checks XV first (line 230), then IX (line 284), then II (line 293). Any reorder or boundary change could cause a phase to "win" incorrectly. The polygon builders for II, IX, XV use hardcoded pressure values (950 MPa, 400 MPa) rather than curve functions, creating potential inconsistency between lookup and diagram.
- Safe modification: When changing phase boundaries, test both `lookup_phase()` AND `_build_phase_polygon_from_curves()` for the same T,P points. Run existing test suite (`tests/test_phase_mapping.py` with 62 tests).
- Test coverage: Good for lookup (62 tests). Missing for polygon-boundary consistency.

**GRO format parsing relies on fixed column widths:**
- Files: `quickice/structure_generation/generator.py` (lines 176-188), `quickice/structure_generation/water_filler.py` (lines 55-63)
- Why fragile: GRO format parsing uses hardcoded column indices (`line[10:15]`, `line[20:28]`, `line[28:36]`, `line[36:44]`). Any deviation in GenIce's output format (extra whitespace, different precision) would silently produce wrong coordinates.
- Safe modification: Add roundtrip tests that generate → parse → verify positions match within tolerance.

**Atom ordering assumptions throughout codebase:**
- Files: `quickice/gui/vtk_utils.py` (lines 80-91), `quickice/output/gromacs_writer.py` (lines 59-87), `quickice/ranking/scorer.py` (lines 42-43)
- Why fragile: Multiple modules assume atoms are ordered as O, H, H (TIP3P) or OW, HW1, HW2, MW (TIP4P) per molecule. If GenIce changes its output ordering, bond creation and MW position computation would produce wrong results. Some modules validate this (vtk_utils raises ValueError on mismatch), but gromacs_writer and scorer do NOT validate.
- Safe modification: Always validate atom ordering at function entry (follow vtk_utils pattern). Add validation to gromacs_writer.write_gro_file and scorer._calculate_oo_distances_pbc.

**Thread cancellation with 100ms timeout:**
- Files: `quickice/gui/viewmodel.py` (lines 71-76, 107-112)
- Why fragile: Both `start_generation()` and `cancel_generation()` call `thread.wait(100)` with only 100ms timeout. If the worker thread is in the middle of GenIce generation (which can take seconds), the thread won't actually stop. The old thread object is deleted but the Python thread may continue running, potentially causing issues if a new generation starts while the old one is still executing.
- Safe modification: Track whether a worker is truly finished before starting a new one. Add worker state checking.

## Scaling Limits

**Large molecule count generation:**
- Current capacity: `validate_nmolecules` allows up to 100,000 molecules (line 93 in `quickice/validation/validators.py`)
- Limit: GenIce generation for 100,000 molecules would take minutes and use significant memory (each molecule has 3-4 atoms, so 400,000+ positions in memory). The 3x3x3 supercell approach in scorer and validator would create 27x memory overhead (~10.8 million atom positions).
- Scaling path: Replace supercell approach with `boxsize`-based cKDTree. Consider lazy candidate generation for large counts.

**Phase diagram rendering with many phases:**
- Current capacity: 12 ice phases rendered
- Limit: Adding more phases (Ice XVII, Ice XIX, etc.) would increase polygon computation and shapely operations proportionally. No architectural limit, but performance degrades linearly.
- Scaling path: Cache phase polygons after first build (already partially done via `_SHARED_BOUNDARY_CACHE`). Consider lazy polygon building.

## Dependencies at Risk

**genice2 (v2.2.13.1):**
- Risk: GenIce2 is a specialized academic package with a small maintainer base. It uses the legacy `np.random.seed()` global state API. If GenIce2 stops being maintained or breaks with newer numpy, QuickIce's core functionality (structure generation) would be broken.
- Impact: All ice structure generation fails. No alternative library provides the same lattice generation + hydrogen bond network randomization.
- Migration plan: Pin numpy <2.0 in requirements if needed. Consider forking GenIce2's critical path (Lattice + GenIce + depol) into QuickIce as a vendored dependency.

**Python 3.14 dependency:**
- Risk: `environment.yml` specifies `python=3.14.3`. Python 3.14 is very new (released 2025-2026). Many scientific packages may not yet fully support it.
- Impact: If any dependency (GenIce2, spglib, iapws) fails on Python 3.14, the entire application breaks.
- Migration plan: Test with Python 3.12 as a fallback. Keep `environment.yml` updated.

**iapws package for water thermodynamics:**
- Risk: The `iapws` package (v1.5.5) is used for IAPWS97 calculations (liquid-vapor boundary, melting curves). It's a niche package with limited maintenance. Its exception handling is inconsistent (raises generic `Exception` in some cases, caught by broad `except Exception` blocks).
- Impact: Phase diagram rendering and liquid region detection would fail without IAPWS.
- Migration plan: Implement critical IAPWS R14-08 equations directly (they're relatively simple polynomial/Simon-Glatzel fits). This would also eliminate the broad `except Exception` blocks in phase_diagram.py.

## Missing Critical Features

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

## Test Coverage Gaps

**GUI layer has zero test coverage:**
- What's not tested: All of `quickice/gui/` (16 files, ~5000 lines) — MainWindow, ViewModels, Workers, Exporters, PhaseDiagramPanel, VTK viewers.
- Files: `quickice/gui/` (entire directory)
- Risk: Any GUI regression (broken signal connections, dialog errors, thread safety issues) goes undetected until manual testing.
- Priority: High — GUI is the primary user interface.

**No integration test for full CLI pipeline with GROMACS export:**
- What's not tested: End-to-end test running `quickice.py --temperature 250 --pressure 500 --gromacs` and verifying .gro, .top, .itp output files are valid.
- Files: `tests/test_cli_integration.py` (292 lines but doesn't test GROMACS export path)
- Risk: GROMACS export could break silently (wrong atom counts, incorrect box vectors) without detection.
- Priority: High — GROMACS export is a key deliverable.

**No polygon-boundary consistency tests:**
- What's not tested: Whether `_build_phase_polygon_from_curves()` produces polygons that are consistent with `lookup_phase()`. A point inside the polygon should map to the same phase that lookup_phase returns.
- Files: `quickice/output/phase_diagram.py`, `quickice/phase_mapping/lookup.py`
- Risk: Polygon and lookup could diverge (different boundary values, different ordering logic), producing inconsistent results between diagram display and actual generation.
- Priority: Medium — Would catch the II/IX/XV boundary inconsistency.

**No test for triclinic cell rejection in interface builder:**
- What's not tested: `is_cell_orthogonal()` and the triclinic rejection path in `validate_interface_config()`. No test creates a triclinic candidate and verifies the error is raised.
- Files: `quickice/structure_generation/interface_builder.py` (lines 119-131)
- Risk: If triclinic detection logic has a bug, invalid cells could pass through and produce corrupt interface structures.
- Priority: Medium — ice_ii and ice_v produce triclinic cells.

**No test for thread cancellation behavior:**
- What's not tested: What happens when generation is cancelled mid-stream? Does the old thread actually stop? Are resources properly cleaned up?
- Files: `quickice/gui/viewmodel.py`, `quickice/gui/workers.py`
- Risk: Thread leak or zombie generation continuing after user clicks Cancel.
- Priority: Medium — Directly affects user experience.

**No test for overlap detection edge cases:**
- What's not tested: Overlaps at exact box boundaries (atoms at x=0 and x=lx), zero-length distances, or single-molecule structures.
- Files: `quickice/structure_generation/overlap_resolver.py`
- Risk: Edge case overlaps could cause incorrect molecule removal or index errors.
- Priority: Low — Unlikely in practice but correctness matters.

---

*Concerns audit: 2026-04-10*
