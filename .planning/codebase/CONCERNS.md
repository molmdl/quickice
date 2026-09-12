# Codebase Concerns

**Analysis Date:** 2026-09-12

> Regenerated after phases 48.1–48.3 (test-suite revision, ~62 commits) and v4.7 UAT workflow
> revisions. Every concern carried from the 2026-07-23 audit was re-verified against current
> code; resolved items were dropped (see "Resolved since last audit" at the bottom for the record).

## Tech Debt

**Large GUI "god-object" files:**
- Issue: Four modules exceed 1100 lines, concentrating UI construction, state wiring, and export orchestration in single classes. `main_window.py` (2318 lines) holds all cross-tab `_current_*_result` state, duck-typed attribute propagation, and signal wiring in one `MainWindow` class. `gui/export.py` GREW from 1138 → 1249 lines during 48.3-25 (mixed-ion export mirror work added to `IonGROMACSExporter.export_ion_gromacs`).
- Files: `quickice/gui/main_window.py` (2318), `quickice/gui/custom_molecule_panel.py` (1395), `quickice/gui/export.py` (1249), `quickice/output/phase_diagram.py` (1132)
- Impact: High cognitive load to modify; cross-cutting changes require touching many unrelated sections of one file; hard to test in isolation; merge-conflict-prone.
- Fix approach: Extract state-management (`_current_*_result` + duck-typing propagation) into a dedicated `PipelineState` / controller class; split `export.py` per exporter class into separate modules (it already has 7 exporter classes: `SoluteGROMACSExporter`, `CustomMoleculeGROMACSExporter`, `IonGROMACSExporter`, `PDBExporter`, `DiagramExporter`, `ViewportExporter`, `GROMACSExporter`). Document as a refactor target, not an emergency.

**O(n²) COM-COM overlap warning in custom-molecule placement:**
- Problem: `place_custom` computes pairwise center-of-mass distances with a nested Python loop (SUSP-06 block): `for i in range(n_molecules): for j in range(i + 1, n_molecules): np.linalg.norm(...)`.
- Files: `quickice/structure_generation/custom_molecule_inserter.py:1066-1093` (loop at 1076-1077; moved from line 938 since last audit)
- Cause: Pure-Python double loop with a per-pair `np.linalg.norm` call; no vectorization, no cKDTree. For a custom-positions CSV at the CLI cap (`MAX_CSV_ROWS = 10000`, `quickice/cli/pipeline.py:21`), this is ~50M iterations of Python-level work plus per-iteration numpy dispatch overhead.
- Improvement path: Replace with `scipy.spatial.distance.pdist(com_arr)` (one C-level call) or a `cKDTree.query_ball_tree` self-query; compare against `min_separation`. This is a warning-only path (placement proceeds regardless), so the cost buys only a log line.

**Per-molecule PBC wrapping loop:**
- Problem: `wrap_molecules` loops molecule-by-molecule in Python, doing fractional-coordinate conversion + matrix multiplies per molecule.
- Files: `quickice/structure_generation/water_filler.py:106-131` (loop at line 112)
- Cause: `for mol_idx in range(n_molecules):` with `mol_frac = mol @ inv_cell_T` and `mol_frac @ cell.T` per iteration. For large boxes (tens of thousands of water molecules) the per-iteration numpy dispatch overhead dominates.
- Improvement path: Vectorize — reshape to `(n_molecules, atoms_per_molecule, 3)`, batch the `@ inv_cell_T`, compute COM per molecule via `.mean(axis=1)`, apply the floor-shift broadcast, and batch-convert back. (The inserters' cKDTree rebuilds are already batched — `ion_inserter.py`, `solute_inserter.py` — so they are NOT bottlenecks.)

**Implicit exception chaining in GRO parse guard (minor):**
- Issue: `hydrate_generator.py:339` raises `RuntimeError("Invalid GRO format from GenIce2")` inside `except (IndexError, ValueError)` without an explicit `from e`. Python's implicit `__context__` chaining preserves the original exception, so information is not lost — but the style is inconsistent with the now-fixed explicit `from e` wrapper at `hydrate_generator.py:324-327`.
- Files: `quickice/structure_generation/hydrate_generator.py:336-339`
- Impact: Cosmetic/consistency only. No action required; fix opportunistically if the file is touched.

## Known Bugs

No actively-crashing bugs were found in the analyzed source. Verified invariants (all currently correct):
- Inserters return NEW structures, never mutating inputs (V-17 fix): `solute_inserter.py`, `ion_inserter.py`.
- cKDTree conditional rebuild (rebuild only after successful placement, never on rejection) correctly implemented in `ion_inserter.py` and `solute_inserter.py`; regression-tested by `tests/scancode/test_scancode_bugs_ion_tree_rebuild.py` and `tests/scancode/test_scancode_bugs_inserter_perf_rebuild.py`.
- comb-rule=2 centralized in `quickice/output/_shared.py:71-83` (single source of truth for the `[defaults]` block).
- TIP4P-ICE parameters centralized as module constants (`TIP4P_ICE_OW_SIGMA`/`TIP4P_ICE_OW_EPSILON` in `quickice/output/_shared.py`, re-exported by `quickice/output/gromacs_writer.py:34`).
- `WATER_ATOMS_PER_MOLECULE` and `WATER_VOLUME_NM3` centralized in `quickice/structure_generation/types.py:22` — the former duplicate in `water_filler.py` was removed (see Resolved).
- Moleculetype `_H`/`_L` suffixing handled by `MoleculetypeRegistry` (`quickice/structure_generation/moleculetype_registry.py`).
- The v4.5→v4.7 stale version assert (`tests/test_entry_point.py::test_version_shows_version`) is fixed — the test now imports `from quickice import __version__` (`tests/test_entry_point.py:21`).

## Security Considerations

**Path containment is enforced inconsistently between CLI and GUI:**
- Risk: CLI validates `--output`, custom `.gro`/`.itp`, and positions CSV stay inside the working directory (`quickice/cli/pipeline.py`, SEC-02/04/05 checks). The GUI path has no equivalent containment check — custom molecule `.gro`/`.itp` and guest ITP paths come straight from `QFileDialog` and are read/written without sandboxing. Verified: no `Path.resolve()`/`is_relative_to` usage in `quickice/gui/custom_molecule_panel.py` or `quickice/gui/export.py`.
- Files: `quickice/cli/pipeline.py` (containment present), `quickice/gui/custom_molecule_panel.py`, `quickice/gui/export.py`
- Current mitigation: CLI is sandboxed; GUI relies on the OS file dialog (user-chosen paths). Low risk for a local scientific tool, but the asymmetry is a latent concern if the GUI is ever exposed to untrusted input.
- Recommendations: If GUI hardening is ever needed, apply the same `Path.resolve().is_relative_to(cwd)` guard used in the CLI before reading user-supplied `.gro`/`.itp`.

**Broad exception swallowing in CLI ITP export:**
- Risk: `quickice/cli/itp_helpers.py` catches `except Exception` (lines 162, 196, 317, 510 — line 482 shifted to 510 after 48.1 refactor) and returns/continues on any ITP copy/transform failure, logging only a warning. A malformed user-supplied custom-guest ITP (GUI path feeds `guest_itp_path` into `copy_custom_guest_itp`) can produce a partial export directory missing the guest ITP, with no raised error.
- Files: `quickice/cli/itp_helpers.py:162, 196, 317, 510`
- Current mitigation: `copy_custom_guest_itp` uses the narrower `except (OSError, ValueError)`; the broad catches are on the bundling/copy helpers. Note `quickice/cli/pipeline.py` itself is clean (only `except OSError` / `except (ValueError, TypeError)` / `except (OSError, ValueError)` — the AGENTS.md no-bare-except constraint holds).
- Recommendations: Narrow the four broad catches to `(OSError, ValueError)` and surface a non-zero exit / user-visible error when a required ITP fails to stage, rather than silently omitting it.

## Fragile Areas

**Duck-typed runtime attributes on InterfaceStructure (CP-01, accepted design):**
- Files: `quickice/gui/main_window.py:950-988`, `quickice/cli/pipeline.py:786-830`
- Why fragile: Both paths mutate a shared `InterfaceStructure` instance in place by setting runtime attributes (`interface.solute_type = ...`, `interface.custom_molecule_positions = ...`, etc.). These are optional/defaulted fields on the dataclass, set by duck-typing on an object that may be reused across steps. A typo in an attribute name silently sets an unused field; a code path reusing the same interface object across ion/solute insertion sees stale mutated attributes; no type-checker enforcement.
- Safe modification: Treat as accepted (per AGENTS.md CP-01 — "NOT a bug"; do NOT "fix"). When adding a new carried-through attribute, add it as a defaulted dataclass field on `InterfaceStructure` (`quickice/structure_generation/types.py`) AND set it in BOTH `main_window.py` and `cli/pipeline.py` propagation blocks, or the two paths will diverge. Never assume an `InterfaceStructure` is immutable across pipeline steps.

**HydrateWorker subclasses QThread directly (accepted, not migrated to QObject+moveToThread):**
- Files: `quickice/gui/hydrate_worker.py`
- Why fragile: Per AGENTS.md this is an accepted design decision — do NOT "fix" it. `run()` does the GenIce2 work on the thread. Functional but the older Qt threading idiom.
- Safe modification: Leave as-is. If a new background worker is needed, follow the existing `HydrateWorker` pattern for consistency rather than mixing idioms.

**Guest-type identification heuristic:**
- Files: `quickice/utils/molecule_utils.py:167-180` (WARNING comment block)
- Why fragile: The fallback heuristic assumes "any C-starting molecule with an O atom in the sample window is THF (13 atoms)." It correctly handles only CH4 and THF (the two supported guests). It would misidentify CO2, methanol, acetone, etc. as THF.
- Safe modification: Safe today. If a new guest type is added, this heuristic MUST be updated or callers must pass `guest_type` explicitly (the explicit-`guest_type` path short-circuits before the heuristic). Add a regression test for any new guest before relying on the heuristic.

**multi_molecule_writer lacks try/except cleanup (intentional divergence):**
- Files: `quickice/output/multi_molecule_writer.py:146-160` (NOTE block preserved verbatim through the 48.1 writer split)
- Why fragile: This writer INTENTIONALLY omits the `try/except (OSError, ValueError)` partial-file cleanup block that the other GRO writers have. On a mid-write failure it leaves a partial `.gro` file on disk. The in-code NOTE forbids "fixing" this for byte/behavior identity.
- Safe modification: Do NOT add try/except here for consistency — it is a deliberate behavior contract. If cleanup parity is ever desired, it must be a coordinated behavior change across all writers with updated byte-equivalence tests.

**Broad `except Exception` in output orchestrator produces partial results silently:**
- Files: `quickice/output/orchestrator.py:77, 105, 123` (all inside `output_ranked_candidates`, `quickice/output/orchestrator.py:17`)
- Why fragile: The ranking/export orchestrator catches `except Exception` per-candidate and per-phase-diagram, logs a warning, and continues. A candidate whose PDB write or space-group validation fails is silently dropped from the output list; the caller receives a partial result set with no indication that entries were skipped.
- Safe modification: Acceptable for a best-effort batch exporter, but callers should check `len(output_files)` against the expected candidate count. Consider accumulating failures into a returned report rather than only logging.

**Bare `assert` in GUI slot (stripped under `python -O`):**
- Files: `quickice/gui/main_window.py:1354` (`assert result.water_atom_count >= 0, ...`)
- Why fragile: Under `python -O` / `PYTHONOPTIMIZE=1` this sanity check is silently stripped. Same class as the custom-guest-bridge assert that WAS converted to a real raise in 48.1 (`quickice/structure_generation/custom_guest_bridge.py:367` now raises `RuntimeError`; regression test at `tests/test_scancode_bugs_custom_guest_bridge_assert.py`), but this one is a GUI-only debug check on a required dataclass field, so the risk is much lower.
- Safe modification: Low priority. If touched, replace with an `if ...: raise ValueError(...)` or a logger.warning for consistency with the CRIT-04/bridge-assert pattern.

## Scaling Limits

**GRO atom-number wraparound at 100,000:**
- Current capacity: The GRO fixed-width format reserves 5 digits for atom numbers; they wrap modulo 100,000.
- Limit: `quickice/output/multi_molecule_writer.py:141-144` warns when `n_atoms > 99999` but does NOT prevent the write. Structures above ~99,999 atoms (e.g. a large sII supercell + ions + solutes) get wrapped/duplicate atom numbers in the index column (coordinates remain correct, but the index is ambiguous for tools that rely on it).
- Scaling path: Use a format that supports larger atom counts, or split very large systems. The warning is the only guard; there is no hard cap.

**Custom-positions CSV cap:**
- Current capacity: `MAX_CSV_ROWS = 10000` (`quickice/cli/pipeline.py:21`); enforced at `:317-322`.
- Limit: Custom-placement CSVs are rejected above 10,000 data rows.
- Scaling path: Split the CSV, or use random placement mode (`--custom-count`) for larger counts.

## Dependencies at Risk

**GenIce2 (lazy-imported, required for all ice/hydrate generation):**
- Risk: The entire source step (`quickice/cli/pipeline.py` source step, `quickice/structure_generation/hydrate_generator.py`, `quickice/structure_generation/generator.py`) depends on GenIce2. It is imported inside function bodies (never at module top level, per AGENTS.md). If GenIce2 is unavailable, the source step fails with a "missing package" message; all e2e hydrate/ice tests fail to generate.
- Impact: All structure generation stops. No vendored fallback.
- Status: Version is now PINNED in `environment.yml` (`genice-core==1.4.3`, `genice2==2.2.13.1`) — the previous "pin its version" recommendation is satisfied. Remaining risk is upstream behavioral drift on upgrade; the `depol_mode` validation note (`quickice/structure_generation/types.py`) shows GenIce2 accepts any string silently, so QuickIce remains the sole gatekeeper for that parameter.

**scipy (cKDTree, Rotation, UnivariateSpline) — core to inserters and phase diagram:**
- Risk: `scipy.spatial.cKDTree` and `scipy.spatial.transform.Rotation` are required by both inserters (`ion_inserter.py`, `solute_inserter.py`). `quickice/output/phase_diagram.py` has an `ImportError` fallback ONLY for `UnivariateSpline` (degrades to direct sampling, `phase_diagram.py:228-235`); cKDTree/Rotation have no fallback.
- Impact: Inserters cannot place ions/solutes without scipy.
- Migration plan: Keep scipy as a hard dependency (pinned `scipy==1.17.1` in `environment.yml`). No alternative needed for a scientific tool.

**PySide6 / VTK (GUI-only, lazy-imported, headless-fragile):**
- Risk: GUI tests require `QT_QPA_PLATFORM=offscreen` (enforced at session start by `tests/conftest.py:19`). MainWindow-level e2e tests force `DISPLAY=localhost:11.0` so the SSH-X11 heuristic `is_vtk_available()` (`quickice/gui/vtk_utils.py:925-945`) returns False and MainWindow takes its no-VTK branches (`tests/gui_e2e_helpers.py:49-53`, `tests/e2e/test_e2e_gui_fullchain.py:55-56`). VTK rendering itself may still crash in some headless environments.
- Impact: GUI tests exercise no-VTK fallback branches headlessly; the VTK rendering branches are only exercised on a real display. GUI path unavailable without PySide6 (CLI still works).
- Migration plan: Current mock/skip/heuristic approach is the accepted state. Note: AGENTS.md's pointer to "ROADMAP.md TEST-06 (deferred)" is STALE — the current `.planning/ROADMAP.md` TEST-06 (mixed cage occupancy e2e) is marked DONE; the operative headless-VTK guidance is the AGENTS.md Testing section itself. Consider updating AGENTS.md when convenient (doc drift, not code risk).

**iapws (IAPWS97) — phase diagram liquid-vapor curve only:**
- Risk: `quickice/output/phase_diagram.py:946` imports `IAPWS97` inside the function; per-temperature `except Exception` (line 953) swallows failures and just logs a warning, producing a partial/empty liquid-vapor curve.
- Impact: Only the phase-diagram plot degrades; structure generation is unaffected.
- Migration plan: Optional dependency (pinned `iapws==1.5.5`). Leave the soft-fail behavior.

## Missing Critical Features

**CLI custom-guest mixed cage occupancy:**
- Problem: The CLI surface for `--cage-guest` is built-in-only (CH4/THF). Custom-guest mixed occupancy via the CLI is deferred.
- Files: `quickice/cli/pipeline.py:100-107` (`_parse_cage_guest_args` rejects non-built-in guests with "Custom-guest CLI support is deferred (use the GUI for custom-guest mixed occupancy).")
- Blocks: CLI users cannot specify a custom guest `.gro`/`.itp` for mixed cage occupancy; they must use the GUI. The GUI already supports it via the explicit `cage_guest_assignments` API (`quickice/structure_generation/types.py`).

## Test Coverage Gaps

**GROMACS (grompp) validation skipped when `gmx` is absent:**
- What's not tested: Topology correctness is validated by `gmx grompp` only when `gmx` is on PATH. The `gmx_skipif` marker (`tests/conftest.py:44`) gates 96 usages across the suite (e2e trees `tests/e2e/<feature>/`, `tests/test_cli/test_pipeline_grompp_matrix.py`, `tests/test_gro_top_byte_equivalence.py`, `tests/e2e/export_validation/`).
- Risk: On a machine WITHOUT gmx, byte-equivalence of `.gro`/`.top` files is checked, but actual GROMACS-parseable topology correctness is NOT validated. A top file that is byte-identical to a baseline but semantically broken would pass file-diff tests yet fail grompp.
- Mitigation status: In THIS environment `gmx 2023.5` IS on PATH (per `.planning/phases/48.3-revise-tests-true-e2e/GATES.md`), so the grompp gates actually run here; the skip only bites on gmx-less machines. The 48.3-25 true-e2e audit also closed a real gap here: `tests/e2e/solute_ion/test_e2e_mixed_ion_export.py` now mirrors the FULL mixed-ion export (the pre-audit version was incomplete and could not have passed grompp) and validates with `gmx grompp` rc==0.
- Priority: Medium-low (environment-dependent).

**pytest-qt not installed — 2 permanently skipped tests:**
- What's not tested: `tests/test_solute_insertion.py:237, 251` carry `@pytest.mark.skip(reason="pytest-qt not installed in test environment")` — Qt-interaction coverage for the solute insertion UI path never runs.
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
- What's not tested: The `place_custom` pairwise COM-COM warning loop (`quickice/structure_generation/custom_molecule_inserter.py:1066-1093`) has no performance test. With a large CSV (up to 10,000 rows) the loop is ~50M iterations.
- Risk: A user supplying a large custom-positions CSV hits an unexpectedly slow (multi-second) warning computation that is not rejection-critical.
- Priority: Low.

## Resolved since last audit (2026-07-23)

Dropped from the concern list after verification — recorded here so future audits don't re-flag them:

1. **Duplicate water-atoms constant** — `water_filler.py` now imports `WATER_ATOMS_PER_MOLECULE` from `quickice/structure_generation/types.py` (`water_filler.py:20`; usages at 661, 670). Single source of truth restored.
2. **Exception-cause chain in hydrate generator** — `hydrate_generator.py:324-327` now raises with `from e`, matching `generator.py:150` and `interface_builder.py:370`.
3. **Bare `assert` in custom-guest bridge** — `custom_guest_bridge.py:366-367` now uses `if key in sys.modules: raise RuntimeError(...)`; regression-tested by `tests/test_scancode_bugs_custom_guest_bridge_assert.py`.
4. **Stale v4.5.0 version assert** — `tests/test_entry_point.py:65-67` now asserts against `quickice.__version__`; the known-failure record in `.planning/phases/48.3-revise-tests-true-e2e/baseline-known-failures.md` is obsolete.
5. **Full-suite deadlock (C-level VTK hang at `tests/test_custom_molecule_panel_34_6.py`)** — fixed in 48.3-03; GATE-FULL (`QT_QPA_PLATFORM=offscreen timeout 900 python -m pytest -q`) is valid and the suite runs ~4-5 min headless. The external `timeout` guard remains MANDATORY (SIGALRM cannot interrupt C-level hangs).
6. **True-e2e audit gaps** — 48.3-25 fixed the incomplete mixed-ion export mirror + added grompp validation (`tests/e2e/solute_ion/test_e2e_mixed_ion_export.py`); the e2e suite now lives in the feature tree `tests/e2e/<feature>/` with shared fixtures in `tests/e2e_chain_fixtures.py` and `tests/e2e_export_helpers.py`.
7. **Byte-eq baselines buried in `.planning/`** — moved to `tests/_baselines/` with `__file__`-relative loading (48.3-18).

Also verified clean: no TODO/FIXME/HACK comment clusters in `quickice/` (the only "XXX" match is the legitimate `GENERIC_RESIDUE_NAMES` set in `quickice/structure_generation/molecule_validator.py:18`); `quickice/cli/pipeline.py` contains no bare `except Exception` (AGENTS.md constraint holds); test collection is 1846 tests / 0 errors.

---

*Concerns audit: 2026-09-12*
