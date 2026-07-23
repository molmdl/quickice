# Codebase Concerns

**Analysis Date:** 2026-07-23

## Tech Debt

**Duplicate water-atoms-per-molecule constant:**
- Issue: `water_filler.py` defines its own local `ATOMS_PER_WATER_MOLECULE = 4` (line 133) instead of importing the canonical `WATER_ATOMS_PER_MOLECULE` from `quickice/structure_generation/types.py:22`. This creates two sources of truth for the same magic number. AGENTS.md mandates "Never hardcode `4` for water atoms per molecule. Use `WATER_ATOMS_PER_MOLECULE` from `types.py`."
- Files: `quickice/structure_generation/water_filler.py:133` (uses it at lines 663, 672), `quickice/structure_generation/types.py:22` (canonical)
- Impact: If the canonical value ever changes (e.g. a non-TIP4P water model), `water_filler.py` silently diverges, corrupting atom-count math in the fill/wrap path. The two constants are not linked, so no test catches a future drift.
- Fix approach: Delete the local constant in `water_filler.py:133` and `from quickice.structure_generation.types import WATER_ATOMS_PER_MOLECULE` at the top of the module; replace usages at lines 663 and 672. (Note: `WATER_VOLUME_NM3 = 0.0299` and `TIP4P_ICE_OW_SIGMA`/`TIP4P_ICE_OW_EPSILON` are correctly centralized — only this one duplicate exists.)

**Exception-cause chain lost in hydrate generator:**
- Issue: `hydrate_generator.py:323` wraps any failure as `raise RuntimeError(f"GenIce2 failed to generate structure: {e}")` WITHOUT `from e`. The sibling wrappers `generator.py:150` (`raise StructureGenerationError(...) from e`) and `interface_builder.py:370` (`raise InterfaceGenerationError(...) from e from e`) correctly preserve the cause chain.
- Files: `quickice/structure_generation/hydrate_generator.py:323-326`
- Impact: The original GenIce2 exception type and traceback are lost; debugging a hydrate-generation failure shows only the wrapped `RuntimeError` with the stringified message, not the underlying cause/stack. Inconsistent with the other two generators.
- Fix approach: Change line 324 to `raise RuntimeError(f"GenIce2 failed to generate structure: {e}") from e`.

**Large GUI "god-object" files:**
- Issue: Three GUI modules exceed 1100 lines, concentrating UI construction, state wiring, and export orchestration in single classes. `main_window.py` (2318 lines) holds all cross-tab `_current_*_result` state, duck-typed attribute propagation, and signal wiring in one `MainWindow` class.
- Files: `quickice/gui/main_window.py` (2318), `quickice/gui/custom_molecule_panel.py` (1395), `quickice/gui/export.py` (1138), `quickice/output/phase_diagram.py` (1132)
- Impact: High cognitive load to modify; cross-cutting changes require touching many unrelated sections of one file; hard to test in isolation; merge-conflict-prone.
- Fix approach: Extract state-management (`_current_*_result` + duck-typing propagation) into a dedicated `PipelineState` / controller class; split `export.py` per step-type writer dispatch. Document as a refactor target, not an emergency.

## Known Bugs

No actively-crashing bugs were found in the analyzed source. The inserters correctly return NEW structures (`solute_inserter.py:504-555` builds a fresh `InterfaceStructure` for the V-17 fix path; `ion_inserter.py` builds new `IonStructure` objects). The cKDTree conditional-rebuild rule (rebuild only after successful placement, never on rejection) is correctly implemented in both `ion_inserter.py:524-575` (`ion_tree` rebuilt only on placement) and `solute_inserter.py:907-984` (`buffer_tree`/`existing_tree` rebuilt only on placement). comb-rule=2 is correctly centralized in `quickice/output/_shared.py:65-141` (data line `1  2  yes  0.5  0.8333`, single source of truth). Moleculetype `_H`/`_L` suffixing is correctly handled by `MoleculetypeRegistry` (`moleculetype_registry.py:46-94`).

## Security Considerations

**Path containment is enforced inconsistently between CLI and GUI:**
- Risk: CLI validates `--output`, custom `.gro`/`.itp`, and positions CSV stay inside the working directory (`cli/pipeline.py:170-176`, `:281-287`, `:533-547`). The GUI path has no equivalent containment check — custom molecule `.gro`/`.itp` and guest ITP paths come straight from `QFileDialog` and are read/written without sandboxing.
- Files: `quickice/cli/pipeline.py` (SEC-02/04/05 checks present), `quickice/gui/custom_molecule_panel.py`, `quickice/gui/export.py`
- Current mitigation: CLI is sandboxed; GUI relies on the OS file dialog (user-chosen paths). Low risk for a local scientific tool, but the asymmetry is a latent concern if the GUI is ever exposed to untrusted input.
- Recommendations: If GUI hardening is ever needed, apply the same `Path.resolve().is_relative_to(cwd)` guard used in the CLI before reading user-supplied `.gro`/`.itp`.

**Broad exception swallowing in CLI ITP export:**
- Risk: `cli/itp_helpers.py` catches `except Exception` (lines 162, 196, 317, 482) and returns `None` on any ITP copy/transform failure, logging only a warning. A malformed user-supplied custom-guest ITP (GUI path feeds `guest_itp_path` into `copy_custom_guest_itp`) produces a partial export directory missing the guest ITP, with no raised error.
- Files: `quickice/cli/itp_helpers.py:162, 196, 317, 482`
- Current mitigation: `copy_custom_guest_itp` (line 234) uses the narrower `except (OSError, ValueError)`; the broad catches are on the bundling/copy helpers.
- Recommendations: Narrow the four broad catches to `(OSError, ValueError)` and surface a non-zero exit / user-visible error when a required ITP fails to stage, rather than silently omitting it.

## Performance Bottlenecks

**O(n²) COM-COM overlap warning in custom-molecule placement:**
- Problem: `place_custom` computes pairwise center-of-mass distances with a nested Python loop: `for i in range(n_molecules): for j in range(i+1, n_molecules): np.linalg.norm(...)`.
- Files: `quickice/structure_generation/custom_molecule_inserter.py:938-941`
- Cause: Pure-Python double loop with a per-pair `np.linalg.norm` call; no vectorization, no cKDTree. For a custom-positions CSV at the CLI cap (`MAX_CSV_ROWS = 10000`, `cli/pipeline.py:21`), this is ~50M iterations of Python-level work plus per-iteration numpy dispatch overhead.
- Improvement path: Replace with `scipy.spatial.distance.pdist(com_arr)` (one C-level call) or a `cKDTree.query_ball_tree` self-query; compare against `min_separation`. This is a warning-only path (placement proceeds regardless), so the cost buys only a log line.

**Per-molecule PBC wrapping loop:**
- Problem: `wrap_molecules` loops molecule-by-molecule in Python, doing fractional-coordinate conversion + matrix multiplies per molecule.
- Files: `quickice/structure_generation/water_filler.py:108-129`
- Cause: `for mol_idx in range(n_molecules):` with `mol_frac = mol @ inv_cell_T` and `mol_frac @ cell.T` per iteration. For large boxes (tens of thousands of water molecules) the per-iteration numpy dispatch overhead dominates.
- Improvement path: Vectorize — reshape to `(n_molecules, atoms_per_molecule, 3)`, batch the `@ inv_cell_T`, compute COM per molecule via `.mean(axis=1)`, apply the floor-shift broadcast, and batch-convert back. (Note: the inserters' cKDTree rebuilds are already batched — `ion_inserter.py:520-575` PERF-01, `solute_inserter.py:895-984` PERF-02 — so they are NOT bottlenecks.)

## Fragile Areas

**Duck-typed runtime attributes on InterfaceStructure (CP-01, accepted design):**
- Files: `quickice/gui/main_window.py:950-988`, `quickice/cli/pipeline.py:786-830`
- Why fragile: Both paths mutate a shared `InterfaceStructure` instance in place by setting runtime attributes (`interface.solute_type = ...`, `interface.solute_positions = ...`, `interface.custom_molecule_positions = ...`, `interface.custom_molecule_moleculetype = ...`). These attributes are NOT declared on the `InterfaceStructure` dataclass (`types.py:347-438`) — they are optional fields with defaults, but the GUI/CLI set them by duck-typing on an object that may be reused across steps. A typo in an attribute name silently sets an unused field; a code path that reuses the same interface object across ion/solute insertion sees stale mutated attributes; there is no type-checker enforcement.
- Safe modification: Treat this as accepted (per AGENTS.md CP-01 — "NOT a bug"). When adding a new carried-through attribute, add it as a defaulted dataclass field on `InterfaceStructure` (`types.py`) AND set it in BOTH `main_window.py` and `cli/pipeline.py` propagation blocks, or the two paths will diverge. Never assume an `InterfaceStructure` is immutable across pipeline steps.

**HydrateWorker subclasses QThread directly (accepted, not migrated to QObject+moveToThread):**
- Files: `quickice/gui/hydrate_worker.py:15` (`class HydrateWorker(QThread):`)
- Why fragile: Per AGENTS.md this is an accepted design decision — do NOT "fix" it. The `run()` method (line 50) does the GenIce2 work on the thread. This pattern is functional but is the older Qt threading idiom; event-loop/signals from a `QThread.run()` override behave differently than the `QObject.moveToThread` pattern.
- Safe modification: Leave as-is. If a new background worker is needed, follow the existing `HydrateWorker` pattern for consistency rather than mixing idioms.

**Guest-type identification heuristic:**
- Files: `quickice/utils/molecule_utils.py:167-170` (with the WARNING comment)
- Why fragile: The fallback heuristic assumes "any C-starting molecule with an O atom in the sample window is THF (13 atoms)." It correctly handles only CH4 and THF (the two supported guests). It would misidentify CO2, methanol, acetone, etc. as THF.
- Safe modification: Safe today. If a new guest type is added, this heuristic MUST be updated or callers must pass `guest_type` explicitly (the explicit-`guest_type` path at `molecule_utils.py:154-158` short-circuits before the heuristic). Add a regression test for any new guest before relying on the heuristic.

**multi_molecule_writer lacks try/except cleanup (intentional divergence):**
- Files: `quickice/output/multi_molecule_writer.py:146-155`
- Why fragile: This writer INTENTIONALLY omits the `try/except (OSError, ValueError)` partial-file cleanup block that the other 4 GRO writers (`write_gro_file`, `write_interface_gro_file`, `write_ion_gro_file`, `write_custom_molecule_gro_file`) have. On a mid-write `OSError`/`ValueError`, it leaves a partial `.gro` file on disk instead of deleting it. The NOTE at line 146 forbids "fixing" this for byte/behavior identity.
- Safe modification: Do NOT add try/except here for consistency — it is a deliberate behavior contract. If cleanup parity is ever desired, it must be a coordinated behavior change across all writers with updated byte-equivalence tests.

**Bare `assert` in custom-guest bridge (stripped under `python -O`):**
- Files: `quickice/structure_generation/custom_guest_bridge.py:346` (`assert key not in sys.modules, ...`)
- Why fragile: Under `python -O` / `PYTHONOPTIMIZE=1`, this `assert` is silently stripped, so a stale `sys.modules` registration goes undetected. This is the same class of bug as the CRIT-04 hydrate atom-count `assert` that was already converted to a real `if ...: raise ValueError` in `cli/pipeline.py:33-56` (`_validate_hydrate_atom_counts`).
- Safe modification: Replace with `if key in sys.modules: raise RuntimeError(f"{key} already registered (stale state?)")` so the guard is always active regardless of optimization level.

**Broad `except Exception` in output orchestrator produces partial results silently:**
- Files: `quickice/output/orchestrator.py:77, 105, 123`
- Why fragile: The ranking/export orchestrator catches `except Exception` per-candidate and per-phase-diagram, logs a warning, and continues. A candidate whose PDB write or space-group validation fails is silently dropped from the output list; the caller receives a partial result set with no indication that entries were skipped.
- Safe modification: Acceptable for a best-effort batch exporter, but callers should check `len(output_files)` against the expected candidate count. Consider accumulating failures into a returned report rather than only logging.

## Scaling Limits

**GRO atom-number wraparound at 100,000:**
- Current capacity: The GRO fixed-width format reserves 5 digits for atom numbers; they wrap modulo 100,000.
- Limit: `quickice/output/multi_molecule_writer.py:143-144` warns when `n_atoms > 99999` but does NOT prevent the write. Structures above ~99,999 atoms (e.g. a large sII supercell + ions + solutes) get wrapped/duplicate atom numbers in the index column (coordinates remain correct, but the index is ambiguous for tools that rely on it).
- Scaling path: Use a format that supports larger atom counts, or split very large systems. The warning is the only guard; there is no hard cap.

**Custom-positions CSV cap:**
- Current capacity: `MAX_CSV_ROWS = 10000` (`quickice/cli/pipeline.py:21`); enforced at `:317-322`.
- Limit: Custom-placement CSVs are rejected above 10,000 data rows.
- Scaling path: Split the CSV, or use random placement mode (`--custom-count`) for larger counts.

## Dependencies at Risk

**GenIce2 (lazy-imported, required for all ice/hydrate generation):**
- Risk: The entire source step (`cli/pipeline.py:348`, `hydrate_generator.py`, `generator.py`) depends on GenIce2. It is imported inside function bodies (never at module top level, per AGENTS.md). If GenIce2 is unavailable, the source step returns exit code 1 with a "missing package" message; all e2e hydrate/ice tests fail to generate.
- Impact: All structure generation stops. No vendored fallback.
- Migration plan: None practical — GenIce2 is the core lattice engine. Pin its version in `environment.yml` and track upstream changes (the `depol_mode` validation note at `types.py:596-601` shows GenIce2 accepts any string silently, so QuickIce is the sole gatekeeper).

**scipy (cKDTree, Rotation, UnivariateSpline) — core to inserters and phase diagram:**
- Risk: `scipy.spatial.cKDTree` and `scipy.spatial.transform.Rotation` are required by both inserters (`ion_inserter.py:14`, `solute_inserter.py:15-16`). `phase_diagram.py:223-231` has an `ImportError` fallback ONLY for `UnivariateSpline` (degrades to direct sampling); cKDTree/Rotation have no fallback.
- Impact: Inserters cannot place ions/solutes without scipy.
- Migration plan: Keep scipy as a hard dependency. No alternative needed for a scientific tool.

**PySide6 / VTK (GUI-only, lazy-imported, headless-fragile):**
- Risk: GUI tests require `QT_QPA_PLATFORM=offscreen` (see test files). VTK rendering may crash in some headless environments; this is ROADMAP.md TEST-06 (deferred). `entry.py` uses `importlib.util.find_spec('PySide6')` to check availability without importing.
- Impact: GUI tests may skip or crash in headless CI; GUI path unavailable without PySide6 (CLI still works).
- Migration plan: Mock or skip VTK-dependent tests in headless environments (already the stated approach).

**iapws (IAPWS97) — phase diagram liquid-vapor curve only:**
- Risk: `phase_diagram.py:946` imports `IAPWS97` inside the function; per-temperature `except Exception` (line 953) swallows failures and just logs a warning, producing a partial/empty liquid-vapor curve.
- Impact: Only the phase-diagram plot degrades; structure generation is unaffected.
- Migration plan: Optional dependency. Leave the soft-fail behavior.

## Missing Critical Features

**CLI custom-guest mixed cage occupancy:**
- Problem: The CLI surface for `--cage-guest` is built-in-only (CH4/THF). Custom-guest mixed occupancy via the CLI is deferred.
- Files: `quickice/cli/pipeline.py:102-107` (`_parse_cage_guest_args` rejects non-built-in guests with "Custom-guest CLI support is deferred (use the GUI for custom-guest mixed occupancy).")
- Blocks: CLI users cannot specify a custom guest `.gro`/`.itp` for mixed cage occupancy; they must use the GUI. The GUI already supports it via the explicit `cage_guest_assignments` API (`types.py:565-570`).

## Test Coverage Gaps

**GROMACS (grompp) validation skipped when `gmx` is absent:**
- What's not tested: Topology correctness is validated by `gmx grompp` only when `gmx` is on PATH. The marker `gmx_skipif` (`tests/conftest.py:24-27`) skips these tests entirely when `gmx` is missing.
- Files: `tests/conftest.py:18-27`, `tests/test_e2e_gmx_validation.py` (14 `@gmx_skipif` cases), `tests/test_gro_top_byte_equivalence.py:855`, plus many `test_e2e_*_grompp.py` / `test_e2e_*_cross_tab_*.py` files.
- Risk: In a CI environment without GROMACS, byte-equivalence of `.gro`/`.top` files is checked, but actual GROMACS-parseable topology correctness is NOT validated. A top file that is byte-identical to a baseline but semantically broken (e.g. a future regression in `[ moleculetype ]` naming) would pass file-diff tests yet fail grompp — and that failure is invisible without `gmx`.
- Priority: Medium. Mitigated by the large number of byte-equivalence + structural invariant tests; residual risk is semantic topology drift.

**VTK / headless GUI rendering:**
- What's not tested: VTK-dependent rendering paths in GUI viewers (`gui/vtk_utils.py`, `gui/hydrate_renderer.py`, `gui/*_viewer.py`) require a display or `QT_QPA_PLATFORM=offscreen`. VTK may still crash in some headless environments (ROADMAP.md TEST-06 deferred).
- Files: `tests/test_hydrate_panel.py:54` (sets `QT_QPA_PLATFORM=offscreen`), `tests/test_e2e_triclinic_blocking_e2e.py:165`, many `test_e2e_*_gui.py` files.
- Risk: GUI viewer rendering regressions can go uncaught in headless CI. Viewer tests that exercise VTK directly may skip/crash rather than fail cleanly.
- Priority: Low (GUI rendering, not physics correctness).

**`python -O` / `PYTHONOPTIMIZE=1` code path:**
- What's not tested: The remaining bare `assert` in `quickice/structure_generation/custom_guest_bridge.py:346` is untested under `-O`. The CRIT-04 fix in `cli/pipeline.py` converted the hydrate atom-count assert to a real raise, but no test suite runs the whole pipeline with `PYTHONOPTIMIZE=1` to confirm no other asserts are load-bearing.
- Files: `quickice/structure_generation/custom_guest_bridge.py:346`
- Risk: A stale `sys.modules` state in the custom-guest bridge is undetected when run optimized.
- Priority: Low (only one remaining assert; custom-guest bridge is a narrow path).

**O(n²) custom-molecule overlap-warning path:**
- What's not tested: The `place_custom` pairwise COM-COM warning loop (`custom_molecule_inserter.py:938-941`) has no performance test. With a large CSV (up to 10,000 rows) the loop is ~50M iterations.
- Files: `quickice/structure_generation/custom_molecule_inserter.py:938-941`
- Risk: A user supplying a large custom-positions CSV hits an unexpectedly slow (multi-second) warning computation that is not rejection-critical.
- Priority: Low.

---

*Concerns audit: 2026-07-23*
