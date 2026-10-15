# Codebase Concerns

**Analysis Date:** 2026-10-15

> refreshed in place after the 2026-09-12 audit. Every carried concern was re-verified
> against current code (post-48.3, post slow-gui-startup/windows-window debug sessions, post quick-029).
> Resolved items since both prior audits are recorded at the bottom so future audits don't re-flag them.

## Tech Debt

**Large GUI "god-object" files:**
- Issue: Four modules exceed 1100 lines, concentrating UI construction, state wiring, and export orchestration in single classes. `quickice/gui/main_window.py` (2319 lines) holds all cross-tab `_current_*_result` state, duck-typed attribute propagation, and signal wiring in one `MainWindow` class. `quickice/gui/export.py` (1259 lines) carries ~7 exporter classes (`SoluteGROMACSExporter`, `CustomMoleculeGROMACSExporter`, `IonGROMACSExporter`, `PDBExporter`, `DiagramExporter`, `ViewportExporter`, `GROMACSExporter`). Large core modules follow the same pattern: `quickice/structure_generation/types.py` (1346), `quickice/structure_generation/custom_molecule_inserter.py` (1249), `quickice/structure_generation/solute_inserter.py` (1142), `quickice/output/ion_writer.py` (1014).
- Files: `quickice/gui/main_window.py` (2319), `quickice/gui/custom_molecule_panel.py` (1395), `quickice/gui/export.py` (1259), `quickice/output/phase_diagram.py` (1135)
- Impact: High cognitive load to modify; cross-cutting changes touch many unrelated sections of one file; hard to test in isolation; merge-conflict-prone.
- Fix approach: Extract state management (`_current_*_result` + duck-typing propagation) into a dedicated `PipelineState`/controller class; split `export.py` per exporter class into separate modules. Document as a refactor target, not an emergency. (Per AGENTS.md, the `_current_*_result` pattern itself is accepted — extract, don't redesign.)

**Stale-open debug documents + investigation remnants (planning hygiene):**
- Issue: Seven top-level `.planning/debug/` docs carry open-ish status headers (`analyzed`/`diagnosed`/`verifying`/`investigating`) but their fixes are verifiably in the current code: `custom-mol-concentration-input.md` (concentration mode implemented: `quickice/gui/custom_molecule_panel.py:334-379`), `custom-mol-water-count-missing.md` + `water-replacement-not-happening.md` (display logic exists: `quickice/gui/main_window.py:1391-1412`), `hydrate-custom-solute-visibility.md` (`render_custom_molecules` paths at `quickice/gui/main_window.py:1088-1095, 1224-1225`), `interface-writer-mixed-guest.md` (per-molecule `mol_type` handling landed in `quickice/output/interface_writer.py:258-326`), `molh-atom-drop-origin.md` (`tests/e2e/custom_guest/test_e2e_custom_guest_mixed_cage.py` exists), `gmx-export-issues.md` (fixed long ago; follow-ups live in `resolved/`). One RESOLVED-status doc (`custom-mol-conc-random-mode-crash.md`) also sits at top level instead of `resolved/`. Related remnant: the `[Water Count Debug]` `logger.debug` block (`quickice/gui/main_window.py:1391-1412`) is leftover investigation logging in production GUI code. `.planning/DEFERRED-UAT.md` (v3.0 phases 17–21 "Pending execution", 2026-04) is superseded by the A–G UAT workflow scripts that quick-030 dry-ran green.
- Files: `.planning/debug/` (top level), `quickice/gui/main_window.py:1391-1412`
- Impact: Future agents chasing these statuses re-investigate already-fixed issues; debug noise degrades status-log readability.
- Fix approach: File the seven docs to `.planning/debug/resolved/` with resolution notes (or delete if redundant with code+tests); delete the `[Water Count Debug]` lines; mark `.planning/DEFERRED-UAT.md` superseded with a pointer to the UAT workflow scripts.

**Scancode test placement split:**
- Issue: 16 `test_scancode_bugs_*.py` regression files live in `tests/scancode/` (48.2-01 move), but 2 remain at `tests/` root: `tests/test_scancode_bugs_custom_guest_bridge_assert.py` and `tests/test_scancode_bugs_piece_logger.py`. AGENTS.md ("Testing") documents the root-level `test_scancode_bugs_*.py` pattern, so doc and practice each half-match.
- Files: `tests/scancode/`, `tests/test_scancode_bugs_custom_guest_bridge_assert.py`, `tests/test_scancode_bugs_piece_logger.py`, `AGENTS.md`
- Impact: Harmless for pytest discovery but inconsistent; new scancode tests may land in either spot.
- Fix approach: Move the 2 stragglers into `tests/scancode/` and update the AGENTS.md testing line. Low priority.

**AGENTS.md drift (two stale claims):**
- Issue: (a) `AGENTS.md:12` says "All tests (~1846)" — the suite now collects **1849** tests (verified via `pytest --collect-only`). (b) `AGENTS.md:42` still points to "ROADMAP.md TEST-06 (deferred)" for headless-VTK guidance, but the current `.planning/ROADMAP.md` TEST-06 is the mixed-cage-occupancy e2e requirement — marked **DONE** (line 261). The operative headless-VTK guidance is the AGENTS.md Testing section itself.
- Files: `AGENTS.md:12`, `AGENTS.md:42`
- Impact: Doc-only; misleads future agents about coverage and sends them to an irrelevant ROADMAP entry.
- Fix approach: Update the count and replace the TEST-06 pointer with a direct statement of the accepted mock/skip/heuristic approach.

**Implicit exception chaining in GRO parse guard (minor):**
- Issue: `quickice/structure_generation/hydrate_generator.py:337` raises `RuntimeError("Invalid GRO format from GenIce2")` inside `except (IndexError, ValueError)` without an explicit `from e`. Python's implicit `__context__` chaining preserves the original exception, so no information is lost — but the style is inconsistent with the explicit `from e` wrapper at `hydrate_generator.py:324-327` (and `generator.py:150`, `interface_builder.py:370`).
- Files: `quickice/structure_generation/hydrate_generator.py:334-338`
- Impact: Cosmetic/consistency only. No action required; fix opportunistically if the file is touched.

## Known Bugs

No actively-crashing bugs were found in the analyzed source. Verified invariants (all currently correct):
- Inserters return NEW structures, never mutating inputs (V-17 fix): `quickice/structure_generation/solute_inserter.py`, `quickice/structure_generation/ion_inserter.py` — regression-tested under `tests/scancode/`.
- cKDTree conditional rebuild (rebuild only after successful placement, never on rejection) correctly implemented: `quickice/structure_generation/ion_inserter.py:571,621`; `quickice/structure_generation/solute_inserter.py:971,1046,1051` — regression-tested by `tests/scancode/test_scancode_bugs_ion_tree_rebuild.py` and `tests/scancode/test_scancode_bugs_inserter_perf_rebuild.py`.
- comb-rule=2 centralized in `quickice/output/_shared.py:71-83` (single source of truth for the `[defaults]` block; the AGENTS.md no-comb-rule-1 constraint holds).
- TIP4P-ICE parameters centralized as module constants (`TIP4P_ICE_ALPHA`/`TIP4P_ICE_OW_SIGMA`/`TIP4P_ICE_OW_EPSILON` in `quickice/output/_shared.py:29`, re-exported at `quickice/output/gromacs_writer.py:34`).
- `WATER_ATOMS_PER_MOLECULE` (`quickice/structure_generation/types.py:22`) and `WATER_VOLUME_NM3` (`types.py:39`) are the single sources of truth; `quickice/structure_generation/water_filler.py:20` imports the former (usages at 661, 670). No hardcoded `0.0299`/`4` outside these definitions.
- Moleculetype `_H`/`_L` suffixing handled by `MoleculetypeRegistry` (`quickice/structure_generation/moleculetype_registry.py`).
- The 48.3-25 exit-audit CLI export bugs (0-ion orphan `ion.itp` include; mixed built-in guest mislabeling) are FIXED by quick-029 (see Resolved).
- `quickice/cli/pipeline.py` contains NO bare `except Exception` (verified: zero matches) — the AGENTS.md constraint holds. The one production bare `assert` (`quickice/gui/main_window.py:1354`) is noted under Fragile Areas.

## Security Considerations

**Path containment is enforced inconsistently between CLI and GUI:**
- Risk: CLI validates `--output`, custom `.gro`/`.itp`, and positions CSV stay inside the working directory (`quickice/cli/pipeline.py:163-171, 281-283, 533-542` — SEC-02/04/05 checks). The GUI path has no equivalent containment check — custom molecule `.gro`/`.itp` and guest ITP paths come straight from `QFileDialog` and are read/written without sandboxing (verified: no `Path.resolve()`/`is_relative_to` usage in `quickice/gui/custom_molecule_panel.py` or `quickice/gui/export.py`).
- Files: `quickice/cli/pipeline.py` (containment present), `quickice/gui/custom_molecule_panel.py`, `quickice/gui/export.py`
- Current mitigation: CLI is sandboxed; GUI relies on the OS file dialog (user-chosen paths). Low risk for a local scientific tool, but the asymmetry is a latent concern if the GUI is ever exposed to untrusted input.
- Recommendations: If GUI hardening is ever needed, apply the same `Path.resolve().is_relative_to(cwd)` guard used in the CLI before reading user-supplied `.gro`/`.itp`.

**Broad exception swallowing in CLI ITP export:**
- Risk: `quickice/cli/itp_helpers.py` catches `except Exception` at **lines 162, 196, 317, 528** and returns/continues on any ITP copy/transform failure, logging only a warning. A malformed user-supplied custom-guest ITP (the GUI path feeds `guest_itp_path` into `copy_custom_guest_itp`) can produce a partial export directory missing a guest ITP, with no raised error. Note: the quick-029 ion-branch catch (:528) is now count-gated (`na_count > 0 or cl_count > 0`) but still broadly catches.
- Files: `quickice/cli/itp_helpers.py:162, 196, 317, 528`
- Current mitigation: `copy_custom_guest_itp` (`itp_helpers.py:201-231`) uses the narrower `except (OSError, ValueError)` with an explicit "DO NOT broadly swallow" comment; `quickice/cli/pipeline.py` itself is clean — the AGENTS.md no-bare-except constraint holds.
- Recommendations: Narrow the four broad catches to `(OSError, ValueError)` and surface a non-zero exit / user-visible error when a required ITP fails to stage, rather than silently omitting it.

## Performance Bottlenecks

**O(n²) COM-COM overlap warning in custom-molecule placement:**
- Problem: `place_custom` computes pairwise center-of-mass distances with a nested Python loop (SUSP-06 block): `for i in range(n_molecules): for j in range(i + 1, n_molecules): np.linalg.norm(...)` at `quickice/structure_generation/custom_molecule_inserter.py:1100-1102` (block at 1090-1107).
- Files: `quickice/structure_generation/custom_molecule_inserter.py:1090-1107`
- Cause: Pure-Python double loop with a per-pair `np.linalg.norm` call; no vectorization, no cKDTree. For a custom-positions CSV at the CLI cap (`MAX_CSV_ROWS = 10000`, `quickice/cli/pipeline.py:21`), this is ~50M iterations of Python-level work plus per-iteration numpy dispatch overhead.
- Improvement path: Replace with `scipy.spatial.distance.pdist(com_arr)` (one C-level call) or a `cKDTree.query_ball_tree` self-query; compare against `min_separation`. This is a warning-only path (placement proceeds regardless), so the cost buys only a log line.

**Per-molecule PBC wrapping loop:**
- Problem: `wrap_positions_triclinic` (`quickice/structure_generation/water_filler.py:85`, loop at `:112-137`) loops molecule-by-molecule in Python, doing fractional-coordinate conversion + matrix multiplies per molecule (`mol_frac = mol @ inv_cell_T`, COM via `.mean(axis=0)`, back via `mol_frac @ cell.T`).
- Files: `quickice/structure_generation/water_filler.py:85-144`, plus the same per-molecule pattern in `quickice/output/_pbc.py:62` (`wrap_molecules_into_box`, export path)
- Cause: For large boxes (tens of thousands of water molecules) the per-iteration numpy dispatch overhead dominates.
- Improvement path: Vectorize — reshape to `(n_molecules, atoms_per_molecule, 3)`, batch the `@ inv_cell_T`, compute COM per molecule via `.mean(axis=1)`, apply the floor-shift broadcast, and batch-convert back. (The inserters' cKDTree rebuilds are already conditional/batched — `ion_inserter.py`, `solute_inserter.py` — so they are NOT bottlenecks.)

## Fragile Areas

**Duck-typed runtime attributes on InterfaceStructure (CP-01, accepted design):**
- Files: `quickice/gui/main_window.py:950-995`, `quickice/cli/pipeline.py:786-830`
- Why fragile: Both paths mutate a shared `InterfaceStructure` instance in place by setting runtime attributes (`interface.solute_type = ...`, `interface.custom_molecule_positions = ...`, etc.). These are optional/defaulted fields on the dataclass, set by duck-typing on an object that may be reused across steps. A typo in an attribute name silently sets an unused field; no type-checker enforcement.
- Safe modification: Treat as accepted (per AGENTS.md CP-01 — "NOT a bug"; do NOT "fix"). When adding a new carried-through attribute, add it as a defaulted dataclass field on `InterfaceStructure` (`quickice/structure_generation/types.py`) AND set it in BOTH `main_window.py` and `cli/pipeline.py` propagation blocks, or the two paths will diverge. Never assume an `InterfaceStructure` is immutable across pipeline steps. The same applies to MainWindow `_current_*_result` attributes (accepted cross-tab flow design).

**HydrateWorker subclasses QThread directly (accepted, not migrated to QObject+moveToThread):**
- Files: `quickice/gui/hydrate_worker.py`
- Why fragile: Per AGENTS.md this is an accepted design decision — do NOT "fix" it. `run()` does the GenIce2 work on the thread. Functional but the older Qt threading idiom.
- Safe modification: Leave as-is. If a new background worker is needed, follow the existing `HydrateWorker` pattern for consistency rather than mixing idioms.

**Guest-type identification heuristic:**
- Files: `quickice/utils/molecule_utils.py:161-174` (HEURISTIC FALLBACK + WARNING comment block)
- Why fragile: The fallback heuristic assumes "any C-starting molecule with an O atom in the sample window is THF (13 atoms)". It correctly handles only CH4 and THF (the two supported built-in guests). It would misidentify CO2, methanol, acetone, etc. as THF.
- Safe modification: Safe today. If a new guest type is added, this heuristic MUST be updated or callers must pass `guest_type` explicitly (the explicit-`guest_type` path short-circuits before the heuristic). Add a regression test for any new guest before relying on the heuristic.

**multi_molecule_writer lacks try/except cleanup (intentional divergence):**
- Files: `quickice/output/multi_molecule_writer.py:146-160` (NOTE block preserved verbatim through the 48.1 writer split)
- Why fragile: This writer INTENTIONALLY omits the `try/except (OSError, ValueError)` partial-file cleanup block that the other GRO writers have. On a mid-write failure it leaves a partial `.gro` file on disk. The in-code NOTE forbids "fixing" this for byte/behavior identity.
- Safe modification: Do NOT add try/except here for consistency — it is a deliberate behavior contract. If cleanup parity is ever desired, it must be a coordinated behavior change across all writers with updated byte-equivalence tests.

**Broad `except Exception` in output orchestrator produces partial results silently:**
- Files: `quickice/output/orchestrator.py:77, 105, 123` (all inside `output_ranked_candidates`, `orchestrator.py:17`)
- Why fragile: The ranking/export orchestrator catches `except Exception` per-candidate and per-phase-diagram, logs a warning, and continues. A candidate whose PDB write or space-group validation fails is silently dropped from the output list; the caller receives a partial result set with no indication that entries were skipped.
- Safe modification: Acceptable for a best-effort batch exporter, but callers should check `len(output_files)` against the expected candidate count. Consider accumulating failures into a returned report rather than only logging.

**Bare `assert` in GUI slot (stripped under `python -O`):**
- Files: `quickice/gui/main_window.py:1354` (`assert result.water_atom_count >= 0, ...`)
- Why fragile: Under `python -O` / `PYTHONOPTIMIZE=1` this sanity check is silently stripped. Same class as the custom-guest-bridge assert that WAS converted to a real raise (`quickice/structure_generation/custom_guest_bridge.py:367` now raises `RuntimeError`; regression test at `tests/test_scancode_bugs_custom_guest_bridge_assert.py`), but this one is a GUI-only debug check on a required dataclass field, so the risk is much lower.
- Safe modification: Low priority. If touched, replace with an `if ...: raise ValueError(...)` or a `logger.warning` for consistency with the CRIT-04/bridge-assert pattern.

**Lazy PEP 562 re-export maps must be extended, not bypassed:**
- Files: `quickice/gui/__init__.py`, `quickice/structure_generation/__init__.py`
- Why fragile: All package-level re-exports are lazy via `_EXPORT_TO_MODULE` + `__getattr__` (slow-gui-startup fix). A NEW public name added to a submodule is NOT importable from the package root (`from quickice.structure_generation import X`) until it is added to the map. The implementation itself is correct (result is cached in `globals()`, `__dir__` is defined, and a missing name still fails fast with `AttributeError`).
- Safe modification: When adding a new public API, append the name→submodule entry to `_EXPORT_TO_MODULE` in the relevant `__init__.py` in the same change (and export from the submodule as before). Do not "restore" eager imports to work around the map — that would reintroduce the startup regression the lazy re-exports fixed.

## Scaling Limits

**GRO atom-number wraparound at 100,000:**
- Current capacity: The GRO fixed-width format reserves 5 digits for atom numbers; they wrap modulo 100,000.
- Limit: `quickice/output/multi_molecule_writer.py:141-143` warns when `n_atoms > 99999` but does NOT prevent the write. Structures above ~99,999 atoms (e.g. a large sII supercell + ions + solutes) get wrapped/duplicate atom numbers in the index column (coordinates remain correct, but the index is ambiguous for tools that rely on it).
- Scaling path: Use a format that supports larger atom counts, or split very large systems. The warning is the only guard; there is no hard cap.

**Custom-positions CSV cap:**
- Current capacity: `MAX_CSV_ROWS = 10000` (`quickice/cli/pipeline.py:21`); enforced at `:317-322`.
- Limit: Custom-placement CSVs are rejected above 10,000 data rows.
- Scaling path: Split the CSV, or use random placement mode (`--custom-count`) for larger counts.

## Dependencies at Risk

**GenIce2 (lazy-imported, required for all ice/hydrate generation):**
- Risk: The entire source step (`quickice/cli/pipeline.py` source step, `quickice/structure_generation/hydrate_generator.py`, `quickice/structure_generation/generator.py`) depends on GenIce2, imported inside function bodies (never at module top level, per AGENTS.md). Note: since the lazy-`__init__` refactor, the heavy generator→genice2+networkx import chain loads on first attribute/use rather than at `import quickice.structure_generation.*` — same requirement, later failure point.
- Impact: All structure generation stops if GenIce2 is unavailable. No vendored fallback.
- Status: PINNED in `environment.yml` (`genice-core==1.4.3`, `genice2==2.2.13.1`, lines 42-43) — the earlier "pin its version" recommendation is satisfied. Remaining risk is upstream behavioral drift on upgrade; QuickIce remains the sole gatekeeper for `depol_mode` validation (`quickice/structure_generation/types.py:571-598` — GenIce2 accepts any string silently).

**scipy (cKDTree, Rotation, UnivariateSpline) — core to inserters and phase diagram:**
- Risk: `scipy.spatial.cKDTree` and `scipy.spatial.transform.Rotation` are required by both inserters (`quickice/structure_generation/ion_inserter.py`, `quickice/structure_generation/solute_inserter.py`); heavy scipy imports are deferred to first use (slow-gui-startup fix). `quickice/output/phase_diagram.py` has an `ImportError` fallback ONLY for `UnivariateSpline` (degrades to direct sampling, `phase_diagram.py:221-235`); cKDTree/Rotation have no fallback.
- Impact: Inserters cannot place ions/solutes without scipy.
- Migration plan: Keep scipy as a hard dependency (pinned `scipy==1.17.1` in `environment.yml:52`). No alternative needed for a scientific tool.

**PySide6 / VTK (GUI-only, lazy-imported, headless-fragile):**
- Risk: GUI tests require `QT_QPA_PLATFORM=offscreen` (session-start `setdefault` in `tests/conftest.py:19`). MainWindow-level e2e tests force `DISPLAY=localhost:11.0` so the SSH-X11 heuristic `is_vtk_available()` returns False — now at `quickice/gui/vtk_utils.py:958` (cache + `reset_vtk_available_cache` at `:1001`; the helper does NOT import VTK itself) — and MainWindow takes its no-VTK branches (`tests/e2e/test_e2e_gui_fullchain.py:52-56`, `tests/gui_e2e_helpers.py:49-53`). VTK rendering itself may still crash in some headless environments (the 48.1-14 C-level hang precedent is why the external `timeout` guard is mandatory).
- Impact: GUI tests exercise no-VTK fallback branches headlessly; the VTK rendering branches are only exercised on a real display. GUI path unavailable without PySide6 (CLI still works).
- Migration plan: Current mock/skip/heuristic approach is the accepted state. NOTE: AGENTS.md:42's "ROADMAP.md TEST-06 (deferred)" pointer is STALE (current ROADMAP TEST-06 = mixed cage occupancy e2e, DONE at `.planning/ROADMAP.md:261`); the operative guidance is the AGENTS.md Testing section itself (see Tech Debt — AGENTS.md drift).

**iapws (IAPWS97) — phase diagram liquid-vapor curve only:**
- Risk: `quickice/output/phase_diagram.py:949` imports `IAPWS97` inside the function; per-temperature `except Exception` (`:953-957`) swallows failures and logs a warning, producing a partial/empty liquid-vapor curve. (quick-027 additionally upgraded the IAPWS failure logging in `quickice/gui/phase_diagram_widget.py` from debug to warning.)
- Impact: Only the phase-diagram plot degrades; structure generation is unaffected.
- Migration plan: Optional dependency (pinned `iapws==1.5.5`, `environment.yml:45`). Leave the soft-fail behavior.

## Missing Critical Features

**CLI custom-guest mixed cage occupancy:**
- Problem: The CLI surface for `--cage-guest` is built-in-only (CH4/THF). Custom-guest mixed occupancy via the CLI is deferred BY DESIGN (`.planning/ROADMAP.md:229` documents CLI-02 as GUI-only for v4.7).
- Files: `quickice/cli/pipeline.py:59-107` (`_parse_cage_guest_args` at `:59`; rejects non-built-in guests at `:105` with "Custom-guest CLI support is deferred (use the GUI for mixed occupancy).")
- Blocks: CLI users cannot specify a custom guest `.gro`/`.itp` for mixed cage occupancy; they must use the GUI. The GUI already supports it via the explicit `cage_guest_assignments` API (`quickice/structure_generation/types.py`), and the Python API path is covered by CLI-side e2e tests (`tests/e2e/custom_guest/`, `tests/test_cli/test_mixed_cage_cli.py`).

## Test Coverage Gaps

**GROMACS (grompp) validation skipped when `gmx` is absent:**
- What's not tested: Topology correctness is validated by `gmx grompp` only when `gmx` is on PATH. The `gmx_skipif` marker (`tests/conftest.py:44`) gates **133** usages across the suite (e2e trees `tests/e2e/<feature>/`, `tests/test_cli/test_pipeline_grompp_matrix.py`, `tests/e2e/export_validation/`).
- Risk: On a machine WITHOUT gmx, byte-equivalence of `.gro`/`.top` is still checked, but actual GROMACS-parseable topology correctness is NOT. A top file that is byte-identical to a baseline but semantically broken would pass file-diff tests yet fail grompp.
- Mitigation status: In THIS environment `gmx 2023.5` (plumed-2.9.3 build) IS on PATH, so the grompp gates actually run here; the skip only bites on gmx-less machines. The 48.3-25 true-e2e audit plus quick-029 keep widening grompp-validated real-export coverage (e.g. `tests/e2e/solute_ion/test_e2e_mixed_ion_export.py`, `tests/e2e/solute_ion/test_e2e_cli_zero_ion_export.py`, `tests/e2e/hydrate/test_e2e_cli_mixed_builtin_hydrate_grompp.py`).
- Priority: Medium-low (environment-dependent).

**pytest-qt not installed — 2 permanently skipped tests:**
- What's not tested: `tests/test_solute_insertion.py:237, 251` carry `@pytest.mark.skip(reason="pytest-qt not installed in test environment")` — Qt-interaction coverage for the solute insertion UI path never runs. `pytest-qt` is not in `environment.yml`.
- Files: `tests/test_solute_insertion.py:237, 251`
- Risk: Solute-panel Qt signal/slot regressions go uncaught; the skipped tests also silently rot as the surrounding code evolves.
- Priority: Low-medium. Either add `pytest-qt` to `environment.yml` (requires user approval per AGENTS.md) or delete the dead tests.

**VTK rendering branches only exercised on a real display:**
- What's not tested: The VTK-dependent rendering paths (`quickice/gui/vtk_utils.py`, `quickice/gui/hydrate_renderer.py`, viewer widgets) are bypassed in headless/SSH-X11 runs via the `is_vtk_available()` heuristic; only the no-VTK fallback branches are exercised by `tests/e2e/test_e2e_gui_fullchain.py` and the `tests/gui_e2e_helpers.py`-based suites.
- Risk: A regression in actual VTK rendering (actor construction, camera, per-type guest styles) passes CI headlessly and only surfaces at the user's manual full-workflow test.
- Priority: Low (GUI rendering, not physics correctness). This is the residual behind the (stale) AGENTS.md "TEST-06 deferred" pointer.

**`python -O` / `PYTHONOPTIMIZE=1` code path:**
- What's not tested: No test suite runs the pipeline with `PYTHONOPTIMIZE=1` to confirm no asserts are load-bearing. One bare assert remains in production code (`quickice/gui/main_window.py:1354`); the previous `custom_guest_bridge.py` assert was converted to a real raise (regression test `tests/test_scancode_bugs_custom_guest_bridge_assert.py` exists).
- Risk: Minimal — the remaining assert is a GUI debug check on a required dataclass field.
- Priority: Low.

**O(n²) custom-molecule overlap-warning path:**
- What's not tested: The `place_custom` pairwise COM-COM warning loop (`quickice/structure_generation/custom_molecule_inserter.py:1090-1107`) has no performance test. With a large CSV (up to 10,000 rows) the loop is ~50M iterations.
- Risk: A user supplying a large custom-positions CSV hits an unexpectedly slow (multi-second) warning computation that is not rejection-critical.
- Priority: Low.

## Resolved since previous audits

**Since the 2026-09-12 audit:**

1. **Slow GUI startup (VTK/matplotlib import cost)** — RESOLVED. Lazy PEP 562 re-exports in `quickice/gui/__init__.py` + `quickice/structure_generation/__init__.py` (commits 7786c16a, 17d67cef), deferred heavy imports in `quickice/gui/vtk_utils.py` (44fe5033), exporters (50544098), phase-diagram canvas deferral (822d8041), renderer module unloading at startup (d3409ed6), scipy deferral to first use (d1f99ac9). Debug record: `.planning/debug/resolved/slow-gui-startup.md`. Side-benefit: latent `__all__` bug fixed — `IonConfig`/`IonStructure` were listed in `__all__` but not actually importable from the package root before the lazy map.
2. **Windows extra/lingering console window** — RESOLVED (launch via `start`, hide-early spec; commits d8bcc4f8, 3945af15, merge 1eaea9c4; archived in 62a508b6). Debug record: `.planning/debug/resolved/windows-extra-window.md`.
3. **0-ion orphan `ion.itp` include + CLI mixed built-in guest mislabeling** (48.3-25 exit-audit bugs) — RESOLVED in quick-029: include+staging now count-gated in `quickice/output/ion_writer.py` + `quickice/cli/itp_helpers.py` (1cfa8a70); `guest_descriptors`/`guest_atom_counts` threaded into the CLI hydrate wrapper (d39e8ba4). True-e2e regressions: `tests/e2e/solute_ion/test_e2e_cli_zero_ion_export.py`, `tests/e2e/hydrate/test_e2e_cli_mixed_builtin_hydrate_grompp.py`.
4. **Dead conftest fixtures** (48.2/48.3 deferred follow-up) — `hydrate_sI_thf_candidate`/`hydrate_sII_ch4_candidate` fixtures deleted from `tests/conftest.py`; the names surviving in e2e modules are local `_`-prefixed helper *functions* (e.g. `tests/e2e/chains/test_chain_structures.py:133`), not fixtures.

**Since the 2026-07-23 audit (carried record):**

5. **Duplicate water-atoms constant** — `water_filler.py` imports `WATER_ATOMS_PER_MOLECULE` from `quickice/structure_generation/types.py` (`water_filler.py:20`; usages at 661, 670).
6. **Exception-cause chain in hydrate generator** — `hydrate_generator.py:324-327` raises with `from e`, matching `generator.py:150` and `interface_builder.py:370`.
7. **Bare `assert` in custom-guest bridge** — `custom_guest_bridge.py:366-367` now uses `if key in sys.modules: raise RuntimeError(...)`; regression-tested by `tests/test_scancode_bugs_custom_guest_bridge_assert.py`.
8. **Stale v4.5.0 version assert** — `tests/test_entry_point.py` asserts against `quickice.__version__` (currently `4.7.0`, `quickice/__init__.py:3`).
9. **Full-suite deadlock (C-level VTK hang)** — fixed in 48.3-03; GATE-FULL (`QT_QPA_PLATFORM=offscreen timeout 900 python -m pytest -q`) is valid (~4-5 min headless). The external `timeout` guard remains MANDATORY (SIGALRM cannot interrupt C-level hangs).
10. **True-e2e audit gaps** — 48.3-25 fixed the incomplete mixed-ion export mirror + added grompp validation (`tests/e2e/solute_ion/test_e2e_mixed_ion_export.py`); the e2e suite lives in the feature tree `tests/e2e/<feature>/` (chains, custom_guest, export_validation, hydrate, interface, lattice, solute_ion) with shared fixtures in `tests/e2e_chain_fixtures.py` and `tests/e2e_export_helpers.py`.
11. **Byte-eq baselines buried in `.planning/`** — moved to `tests/_baselines/` with `__file__`-relative loading (48.3-18).

Also verified clean this audit: no TODO/FIXME/HACK comments in `quickice/` or root Python files (the only "XXX" match is the legitimate `GENERIC_RESIDUE_NAMES` set in `quickice/structure_generation/molecule_validator.py:18`); no hardcoded TIP4P-ICE parameters or `0.0299`/`4` water magic numbers outside their single sources of truth; no comb-rule violations; test collection is **1849 tests / 0 errors** (QT_QPA_PLATFORM=offscreen, 1.11s collect).

---

*Concerns audit: 2026-10-15*
