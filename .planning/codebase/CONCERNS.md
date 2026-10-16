# Codebase Concerns

**Analysis Date:** 2026-10-15

> refreshed in place after the 2026-09-12 audit. Every carried concern was re-verified
> against current code (post-48.3, post slow-gui-startup/windows-window debug sessions, post quick-029).
> Resolved items since both prior audits are recorded at the bottom so future audits don't re-flag them.
> Independently verified 2026-10-15 by a second read-only audit (74 claims checked: 62 confirmed,
> 12 corrected in place — 7 substantive, 5 line-cite). Key corrected premises: the GUI export path
> does NOT use `copy_custom_guest_itp` (CLI-only helper); `generator.py:11-12` imports genice2 at
> module top level (contradicting AGENTS.md's lazy-import invariant); `gmx_skipif` gates 99 usages.
> New findings from that verification pass are folded in below.

## Tech Debt

**Large GUI "god-object" files:**
- Issue: Four modules exceed 1100 lines, concentrating UI construction, state wiring, and export orchestration in single classes. `quickice/gui/main_window.py` (2319 lines) holds all cross-tab `_current_*_result` state, duck-typed attribute propagation, and signal wiring in one `MainWindow` class. `quickice/gui/export.py` (1259 lines) carries 8 exporter classes (`SoluteGROMACSExporter` `:151`, `CustomMoleculeGROMACSExporter` `:333`, `IonGROMACSExporter` `:508`, `PDBExporter` `:705`, `DiagramExporter` `:786`, `ViewportExporter` `:875`, `GROMACSExporter` `:992`, `InterfaceGROMACSExporter` `:1131` — the 8th was missed by the initial 2026-10-15 audit and caught by verification). Large core modules follow the same pattern: `quickice/structure_generation/types.py` (1346), `quickice/structure_generation/custom_molecule_inserter.py` (1249), `quickice/structure_generation/solute_inserter.py` (1142), `quickice/output/ion_writer.py` (1014).
- Files: `quickice/gui/main_window.py` (2319), `quickice/gui/custom_molecule_panel.py` (1395), `quickice/gui/export.py` (1259), `quickice/output/phase_diagram.py` (1135)
- Impact: High cognitive load to modify; cross-cutting changes touch many unrelated sections of one file; hard to test in isolation; merge-conflict-prone.
- Fix approach: Extract state management (`_current_*_result` + duck-typing propagation) into a dedicated `PipelineState`/controller class; split `export.py` per exporter class into separate modules. Document as a refactor target, not an emergency. (Per AGENTS.md, the `_current_*_result` pattern itself is accepted — extract, don't redesign.)

**Stale-open debug documents + investigation remnants (planning hygiene):**
- Issue: Seven top-level `.planning/debug/` docs carry open-ish status headers (`analyzed`/`diagnosed`/`verifying`/`investigating`) but their fixes are verifiably in the current code: `custom-mol-concentration-input.md` (concentration mode implemented: `quickice/gui/custom_molecule_panel.py:334-379`), `custom-mol-water-count-missing.md` + `water-replacement-not-happening.md` (display logic exists: `quickice/gui/main_window.py:1391-1412`), `hydrate-custom-solute-visibility.md` (`render_custom_molecules` paths at `quickice/gui/main_window.py:1088-1095, 1224-1225`), `interface-writer-mixed-guest.md` (per-molecule `mol_type` handling landed in `quickice/output/interface_writer.py:259-334`), `molh-atom-drop-origin.md` (`tests/e2e/custom_guest/test_e2e_custom_guest_mixed_cage.py` exists), `gmx-export-issues.md` (fixed long ago; follow-ups live in `resolved/`). One RESOLVED-status doc (`custom-mol-conc-random-mode-crash.md`) also sits at top level instead of `resolved/`. Related remnant: the `[Water Count Debug]` `logger.debug` block (`quickice/gui/main_window.py:1376-1412`) is leftover investigation logging in production GUI code. `.planning/DEFERRED-UAT.md` (v3.0 phases 17–21 "Pending execution", 2026-04) is superseded by the six UAT workflow scripts — A/B/C/D/E/G in `.planning/uat-workflows/`, no F exists — that quick-030 dry-ran green.
- Files: `.planning/debug/` (top level), `quickice/gui/main_window.py:1376-1412`
- Impact: Future agents chasing these statuses re-investigate already-fixed issues; debug noise degrades status-log readability.
- Fix approach: File the seven docs to `.planning/debug/resolved/` with resolution notes (or delete if redundant with code+tests); delete the `[Water Count Debug]` lines; mark `.planning/DEFERRED-UAT.md` superseded with a pointer to the UAT workflow scripts.

**Scancode test placement split:**
- Issue: 17 `test_scancode_bugs_*.py` regression files live in `tests/scancode/` (48.2-01 move; corroborated by `.planning/ROADMAP.md:444`), but 2 remain at `tests/` root (19 total): `tests/test_scancode_bugs_custom_guest_bridge_assert.py` and `tests/test_scancode_bugs_piece_logger.py`. AGENTS.md ("Testing") documents the root-level `test_scancode_bugs_*.py` pattern, so doc and practice each half-match.
- Files: `tests/scancode/`, `tests/test_scancode_bugs_custom_guest_bridge_assert.py`, `tests/test_scancode_bugs_piece_logger.py`, `AGENTS.md`
- Impact: Harmless for pytest discovery but inconsistent; new scancode tests may land in either spot.
- Fix approach: Move the 2 stragglers into `tests/scancode/` and update the AGENTS.md testing line. Low priority.

**AGENTS.md drift (three stale claims):**
- Issue: (a) `AGENTS.md:12` says "All tests (~1846)" — the suite now collects **1849** tests (re-verified via `pytest --collect-only`, 0 errors). (b) `AGENTS.md:42` still points to "ROADMAP.md TEST-06 (deferred)" for headless-VTK guidance, but the current `.planning/ROADMAP.md` TEST-06 is the mixed-cage-occupancy e2e requirement — marked **DONE** (line 261). The operative headless-VTK guidance is the AGENTS.md Testing section itself. (c) The AGENTS.md Lazy Imports section says PySide6/VTK/GenIce2 are "imported inside function bodies (never at module top level)" — **false for `quickice/structure_generation/generator.py:11-12`**, which imports `from genice2.plugin import safe_import` and `from genice2.genice import GenIce` at module top level (new finding, 2026-10-15 verification). Note (c) is a genuine doc-vs-code divergence: only the lazy PEP 562 `__init__` map keeps `import quickice.structure_generation` light; a direct `import quickice.structure_generation.generator` (e.g. `tests/conftest.py:50`, legitimate for tests) loads the full genice2+networkx chain at import time.
- Files: `AGENTS.md:12`, `AGENTS.md:42`, `quickice/structure_generation/generator.py:11-12`
- Impact: (a)/(b) doc-only; (c) misleads agents about the import graph and leaves the startup-perf contract enforced by convention alone rather than by code.
- Fix approach: (a) update the count; (b) replace the TEST-06 pointer with a direct statement of the accepted mock/skip/heuristic approach; (c) DECIDED 2026-10-15: lazify `generator.py`'s genice2 imports into function bodies (matching `hydrate_generator.py:79-82, :254`) — the AGENTS.md invariant itself stays unchanged. (c) RESOLVED 2026-10-16 (quick-031, commit 060e8d7f) — generator.py:11-12 lazified; the Lazy Imports claim now holds code-wide. (Drift items (a) and (b) remain open, untouched.)

**Implicit exception chaining in GRO parse guard (minor):**
- Issue: `quickice/structure_generation/hydrate_generator.py:339` raises `RuntimeError("Invalid GRO format from GenIce2")` inside `except (IndexError, ValueError)` (guard block `:336-339`, except clause at `:338`) without an explicit `from e`. Python's implicit `__context__` chaining preserves the original exception, so no information is lost — but the style is inconsistent with the explicit `from e` wrapper at `hydrate_generator.py:324-327` (and `generator.py:150`, `interface_builder.py:370`).
- Files: `quickice/structure_generation/hydrate_generator.py:336-339`
- Impact: Cosmetic/consistency only. No action required; fix opportunistically if the file is touched.

## Known Bugs

No actively-crashing bugs were found in the analyzed source. Verified invariants (all currently correct):
- Inserters return NEW structures, never mutating inputs (V-17 fix): `quickice/structure_generation/solute_inserter.py`, `quickice/structure_generation/ion_inserter.py` — regression-tested under `tests/scancode/`.
- cKDTree conditional rebuild (rebuild only after successful placement, never on rejection) correctly implemented: `quickice/structure_generation/ion_inserter.py:571,621`; `quickice/structure_generation/solute_inserter.py:971,1046,1051` — regression-tested by `tests/scancode/test_scancode_bugs_ion_tree_rebuild.py` and `tests/scancode/test_scancode_bugs_inserter_perf_rebuild.py`. Rebuilds are amortized per batch (`_ION_BATCH_SIZE = 8` at `ion_inserter.py:567`; buffer-tree merge pattern at `solute_inserter.py:1034-1053`), still strictly success-gated — do not misread a batch rebuild as a rule violation.
- comb-rule=2 centralized in `quickice/output/_shared.py` (`_write_top_defaults`: source-of-truth docstring `:71-83`, `[defaults]` emission `:132-141`; the AGENTS.md no-comb-rule-1 constraint holds repo-wide — comb-rule=1 appears only in deliberate negative-test fixtures under `quickice/data/custom/test_invalid/`).
- TIP4P-ICE parameters centralized as module constants (`TIP4P_ICE_ALPHA`/`TIP4P_ICE_OW_SIGMA`/`TIP4P_ICE_OW_EPSILON` defined in `quickice/output/_constants.py:15-30`, re-exported via `quickice/output/_shared.py:28-36` and `quickice/output/gromacs_writer.py:34`).
- `WATER_ATOMS_PER_MOLECULE` (`quickice/structure_generation/types.py:22`) and `WATER_VOLUME_NM3` (`types.py:39`) are the single sources of truth; `quickice/structure_generation/water_filler.py:20` imports the former (usages at 661, 670). No hardcoded `0.0299`/`4` outside these definitions.
- Moleculetype `_H`/`_L` suffixing handled by `MoleculetypeRegistry` (`quickice/structure_generation/moleculetype_registry.py`).
- The 48.3-25 exit-audit CLI export bugs (0-ion orphan `ion.itp` include; mixed built-in guest mislabeling) are FIXED by quick-029 (see Resolved).
- `quickice/cli/pipeline.py` contains NO bare `except Exception` (verified: zero matches) — the AGENTS.md constraint holds. The one production bare `assert` (`quickice/gui/main_window.py:1355`) is noted under Fragile Areas.

## Security Considerations

**Path containment is enforced inconsistently between CLI and GUI:**
- Risk: CLI validates `--output`, custom `.gro`/`.itp`, and positions CSV stay inside the working directory (`quickice/cli/pipeline.py:163-171, 280-287, 532-547` — SEC-04/05 containment checks; SEC-02 at `:518` is the file-extension check, not containment). A third containment site exists: `quickice/output/orchestrator.py:47-56` (`Path.resolve().is_relative_to`) independently guards the ranked-candidate output path. The GUI path has no equivalent containment check — custom molecule `.gro`/`.itp` and guest ITP paths come straight from `QFileDialog` and are read/written without sandboxing (verified: no `Path.resolve()`/`is_relative_to` usage in `quickice/gui/custom_molecule_panel.py` or `quickice/gui/export.py`).
- Files: `quickice/cli/pipeline.py` + `quickice/output/orchestrator.py:47-56` (containment present), `quickice/gui/custom_molecule_panel.py`, `quickice/gui/export.py`
- Current mitigation: CLI is sandboxed; GUI relies on the OS file dialog (user-chosen paths). Low risk for a local scientific tool, but the asymmetry is a latent concern if the GUI is ever exposed to untrusted input.
- Recommendations: If GUI hardening is ever needed, apply the same `Path.resolve().is_relative_to(cwd)` guard used in the CLI before reading user-supplied `.gro`/`.itp`.

**Broad exception swallowing in CLI ITP export (CLI path only — verification 2026-10-15):**
- Risk: `quickice/cli/itp_helpers.py` catches `except Exception` at **lines 162, 196, 317, 528** and returns/continues on any ITP copy/transform failure, logging only a warning. A malformed user-supplied custom-guest ITP fed through the **CLI** export path can produce a partial export directory missing a guest ITP, with no raised error. The quick-029 ion-branch catch (:528) is now count-gated (gate `if na_count > 0 or cl_count > 0:` at `:524`) but still broadly catches. **Corrected premise:** `copy_custom_guest_itp` is **CLI-only** — defined and called 5×, all within `itp_helpers.py`, sole importer `quickice/cli/pipeline.py:882`. The GUI does NOT use this helper: its hydrate export stages guest ITPs itself in `quickice/gui/hydrate_export.py:349-359` and *raises* `FileNotFoundError`/`ValueError` on missing ITPs (`:221-224, :296-306`), surfaced as `QMessageBox.critical` via the `:363` handler — no silent omission GUI-side through this mechanism.
- Files: `quickice/cli/itp_helpers.py:162, 196, 317, 528`; GUI-side partial-output surfaces (different mechanism, see below): `quickice/gui/export.py:326, 500, 698, 777, 866, 983, 1070, 1255`
- Current mitigation: `copy_custom_guest_itp` (`itp_helpers.py:201-238`) uses the narrower `except (OSError, ValueError)` at `:234` with the explicit "DO NOT broadly swallow" comment at `:236`; `quickice/cli/pipeline.py` itself is clean (all 23 except clauses typed; loosest is `except (OSError, ValueError)` at `:1006`) — the AGENTS.md no-bare-except core-pipeline constraint holds. GUI-side, 8 broad catch-and-dialog sites in `quickice/gui/export.py` are permitted by AGENTS.md for GUI user-facing workflows, but each can yield a partial output directory with only a dialog notice.
- Recommendations: Narrow the four CLI broad catches to `(OSError, ValueError)` and surface a non-zero exit / user-visible error when a required ITP fails to stage, rather than silently omitting it. GUI-side, consider accumulating per-stage failures into one end-of-export report dialog.

## Performance Bottlenecks

**O(n²) COM-COM overlap warning in custom-molecule placement:**
- Problem: `place_custom` computes pairwise center-of-mass distances with a nested Python loop (SUSP-06 block): `for i in range(n_molecules): for j in range(i + 1, n_molecules): np.linalg.norm(...)` at `quickice/structure_generation/custom_molecule_inserter.py:1100-1102` (block at 1090-1107).
- Files: `quickice/structure_generation/custom_molecule_inserter.py:1090-1107`
- Cause: Pure-Python double loop with a per-pair `np.linalg.norm` call; no vectorization, no cKDTree. For a custom-positions CSV at the CLI cap (`MAX_CSV_ROWS = 10000`, `quickice/cli/pipeline.py:21`), this is ~50M iterations of Python-level work plus per-iteration numpy dispatch overhead.
- Improvement path: Replace with `scipy.spatial.distance.pdist(com_arr)` (one C-level call) or a `cKDTree.query_ball_tree` self-query; compare against `min_separation`. This is a warning-only path (placement proceeds regardless), so the cost buys only a log line.

**Per-molecule PBC wrapping loop:**
- Problem: `wrap_positions_triclinic` (`quickice/structure_generation/water_filler.py:85`, per-molecule loop at `:112-128`, return at `:130`) loops molecule-by-molecule in Python, doing fractional-coordinate conversion + matrix multiplies per molecule (`mol_frac = mol @ inv_cell_T`, COM via `.mean(axis=0)`, back via `mol_frac @ cell.T`).
- Files: `quickice/structure_generation/water_filler.py:85-130`, plus the same per-molecule pattern in `quickice/output/_pbc.py:62` (`wrap_molecules_into_box`: triclinic loop `:109-120`, orthogonal loop `:124-166`, export path)
- Cause: For large boxes (tens of thousands of water molecules) the per-iteration numpy dispatch overhead dominates.
- Improvement path: Vectorize — reshape to `(n_molecules, atoms_per_molecule, 3)`, batch the `@ inv_cell_T`, compute COM per molecule via `.mean(axis=1)`, apply the floor-shift broadcast, and batch-convert back. (The inserters' cKDTree rebuilds are already conditional/batched — `ion_inserter.py`, `solute_inserter.py` — so they are NOT bottlenecks.)

## Fragile Areas

**Duck-typed runtime attributes on InterfaceStructure (CP-01, accepted design):**
- Files: `quickice/gui/main_window.py:948-986`, `quickice/cli/pipeline.py:786-830`
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
- Files: `quickice/output/multi_molecule_writer.py:146-156` (NOTE block `:146-155`, un-guarded `with open` write at `:156`; preserved verbatim through the 48.1 writer split)
- Why fragile: This writer INTENTIONALLY omits the `try/except (OSError, ValueError)` partial-file cleanup block that the other GRO writers have. On a mid-write failure it leaves a partial `.gro` file on disk. The in-code NOTE forbids "fixing" this for byte/behavior identity.
- Safe modification: Do NOT add try/except here for consistency — it is a deliberate behavior contract. If cleanup parity is ever desired, it must be a coordinated behavior change across all writers with updated byte-equivalence tests.

**Broad `except Exception` in output orchestrator produces partial results silently:**
- Files: `quickice/output/orchestrator.py:77, 105, 123` (all inside `output_ranked_candidates`, `orchestrator.py:17`)
- Why fragile: The ranking/export orchestrator catches `except Exception` per-candidate and per-phase-diagram, logs a warning, and continues. A candidate whose PDB write or space-group validation fails is silently dropped from the output list; the caller receives a partial result set with no indication that entries were skipped. Verification addendum (2026-10-15): the module defines no module `logger` — it calls root `logging.warning(...)` directly at `orchestrator.py:78, 97, 101, 106, 124` (despite `import logging` at `:7`), so these drop-warnings bypass per-module logging naming and are even easier to miss.
- Safe modification: Acceptable for a best-effort batch exporter, but callers should check `len(output_files)` against the expected candidate count. Consider accumulating failures into a returned report rather than only logging.

**Bare `assert` in GUI slot (stripped under `python -O`):**
- Files: `quickice/gui/main_window.py:1355` (`assert result.water_atom_count >= 0, ...`; `:1354` is a comment)
- Why fragile: Under `python -O` / `PYTHONOPTIMIZE=1` this sanity check is silently stripped. Same class as the custom-guest-bridge assert that WAS converted to a real raise (`quickice/structure_generation/custom_guest_bridge.py:367` now raises `RuntimeError`; regression test at `tests/test_scancode_bugs_custom_guest_bridge_assert.py`), but this one is a GUI-only debug check on a required dataclass field, so the risk is much lower.
- Safe modification: Low priority. If touched, replace with an `if ...: raise ValueError(...)` or a `logger.warning` for consistency with the CRIT-04/bridge-assert pattern.

**Lazy PEP 562 re-export maps must be extended, not bypassed:**
- Files: `quickice/gui/__init__.py`, `quickice/structure_generation/__init__.py`
- Why fragile: All package-level re-exports are lazy via `_EXPORT_TO_MODULE` + `__getattr__` (slow-gui-startup fix). A NEW public name added to a submodule is NOT importable from the package root (`from quickice.structure_generation import X`) until it is added to the map. The implementation itself is correct (result is cached in `globals()`, `__dir__` is defined, and a missing name still fails fast with `AttributeError`).
- Safe modification: When adding a new public API, append the name→submodule entry to `_EXPORT_TO_MODULE` in the relevant `__init__.py` in the same change (and export from the submodule as before). Do not "restore" eager imports to work around the map — that would reintroduce the startup regression the lazy re-exports fixed.

## Scaling Limits

**GRO atom-number wraparound at 100,000:**
- Current capacity: The GRO fixed-width format reserves 5 digits for atom numbers; they wrap modulo 100,000.
- Limit: `quickice/output/multi_molecule_writer.py:142-144` (check at `:143`) warns when `n_atoms > 99999` but does NOT prevent the write. Structures above ~99,999 atoms (e.g. a large sII supercell + ions + solutes) get wrapped/duplicate atom numbers in the index column (coordinates remain correct, but the index is ambiguous for tools that rely on it).
- Scaling path: **DECIDED 2026-10-15 (user): keep warn-only — permanent design choice, not a deferred fix.** Rationale: `gmx grompp` matches atoms by ORDER against the `.top` (it does not rely on the GRO index column), and GROMACS itself supports very large systems — a hard `ValueError` would block legitimate large exports. The `:143` warning stays as the only guard, deliberately.

**Custom-positions CSV cap:**
- Current capacity: `MAX_CSV_ROWS = 10000` (`quickice/cli/pipeline.py:21`); enforced at `:317-322`.
- Limit: Custom-placement CSVs are rejected above 10,000 data rows.
- Scaling path: Split the CSV, or use random placement mode (`--custom-count`) for larger counts.

## Dependencies at Risk

**GenIce2 (required for all ice/hydrate generation; lazy EXCEPT in `generator.py`):**
- Risk: The entire source step (`quickice/cli/pipeline.py` source step, `quickice/structure_generation/hydrate_generator.py`, `quickice/structure_generation/generator.py`) depends on GenIce2. Import placement is MIXED, not uniformly lazy: `hydrate_generator.py` defers genice2 into function bodies (`:79-82`, `:254`) and `pipeline.py` is clean, but **`quickice/structure_generation/generator.py:11-12` imports genice2 at module top level** (`from genice2.plugin import safe_import`, `from genice2.genice import GenIce`) — contradicting AGENTS.md's "never at module top level" invariant (new finding, 2026-10-15 verification). The lazy PEP 562 `__init__` map is currently the ONLY thing keeping `import quickice.structure_generation` light; a direct `import quickice.structure_generation.generator` (e.g. `tests/conftest.py:50`, legitimate there) loads the heavy genice2+networkx chain at import time. Since the lazy-`__init__` refactor, the package-level import defers the chain to first attribute/use — same requirement, later failure point.
- Impact: All structure generation stops if GenIce2 is unavailable. No vendored fallback.
- Status: PINNED in `environment.yml` (`genice-core==1.4.3`, `genice2==2.2.13.1`, lines 42-43) — the earlier "pin its version" recommendation is satisfied. Remaining risk is upstream behavioral drift on upgrade; QuickIce remains the sole gatekeeper for `depol_mode` validation (`quickice/structure_generation/types.py:571-601`, validation gate `:598-601`, "accepts any string silently" comment `:595-597`).
- Resolution (DECIDED 2026-10-15, user): **lazify `generator.py:11-12`** — defer the `safe_import`/`GenIce` imports into function bodies, matching `hydrate_generator.py:79-82, :254`. AGENTS.md's Lazy Imports invariant stays unchanged and becomes true code-wide once this lands. RESOLVED 2026-10-16 (quick-031, commit 060e8d7f): safe_import/GenIce deferred into `IceStructureGenerator._generate_single` (once, at method top, mirroring `hydrate_generator.py:254-255`); direct module import is now light — pinned by `tests/test_structure_generation.py::TestLazyGenIceImports`; AGENTS.md Lazy Imports invariant now true code-wide.

**scipy (cKDTree, Rotation, UnivariateSpline) — core to inserters and phase diagram:**
- Risk: `scipy.spatial.cKDTree` and `scipy.spatial.transform.Rotation` are required by both inserters (`quickice/structure_generation/ion_inserter.py`, `quickice/structure_generation/solute_inserter.py`); heavy scipy imports are deferred to first use (slow-gui-startup fix). `quickice/output/phase_diagram.py` has an `ImportError` fallback ONLY for `UnivariateSpline` (degrades to direct sampling, `phase_diagram.py:221-235`); cKDTree/Rotation have no fallback.
- Impact: Inserters cannot place ions/solutes without scipy.
- Migration plan: Keep scipy as a hard dependency (pinned `scipy==1.17.1` in `environment.yml:52`). No alternative needed for a scientific tool.

**PySide6 / VTK (GUI-only, lazy-imported, headless-fragile):**
- Risk: GUI tests require `QT_QPA_PLATFORM=offscreen` (session-start `setdefault` in `tests/conftest.py:19`). MainWindow-level e2e tests force `DISPLAY=localhost:11.0` so the SSH-X11 heuristic `is_vtk_available()` returns False — now at `quickice/gui/vtk_utils.py:958` (cache + `reset_vtk_available_cache` at `:1001`; the helper does NOT import VTK itself) — and MainWindow takes its no-VTK branches (`tests/e2e/test_e2e_gui_fullchain.py:52-56`, `tests/gui_e2e_helpers.py:49-53`). VTK rendering itself may still crash in some headless environments (the 48.1-14 C-level hang precedent is why the external `timeout` guard is mandatory).
- Impact: GUI tests exercise no-VTK fallback branches headlessly; the VTK rendering branches are only exercised on a real display. GUI path unavailable without PySide6 (CLI still works).
- Migration plan: Current mock/skip/heuristic approach is the accepted state. NOTE: AGENTS.md:42's "ROADMAP.md TEST-06 (deferred)" pointer is STALE (current ROADMAP TEST-06 = mixed cage occupancy e2e, DONE at `.planning/ROADMAP.md:261`); the operative guidance is the AGENTS.md Testing section itself (see Tech Debt — AGENTS.md drift).

**iapws (IAPWS97) — phase diagram liquid-vapor curve only:**
- Risk: `quickice/output/phase_diagram.py:949` imports `IAPWS97` inside the function; per-temperature `except Exception` (`:953-957`) swallows failures and logs a warning, producing a partial/empty liquid-vapor curve. (quick-027 additionally upgraded the IAPWS failure logging from debug to warning — the code now lives in `quickice/gui/phase_diagram_canvas.py:81` and `:483` after the widget/canvas split; quick-027's summary cites the pre-split `phase_diagram_widget.py:82/:484`, which line-aligns exactly with today's canvas.py.)
- Impact: Only the phase-diagram plot degrades; structure generation is unaffected.
- Migration plan: Optional dependency (pinned `iapws==1.5.5`, `environment.yml:45`). Leave the soft-fail behavior.

## Missing Critical Features

**CLI custom-guest mixed cage occupancy:**
- Problem: The CLI surface for `--cage-guest` is built-in-only (CH4/THF). Custom-guest mixed occupancy via the CLI is deferred BY DESIGN (`.planning/ROADMAP.md:229` documents CLI-02 as GUI-only for v4.7).
- Files: `quickice/cli/pipeline.py:59-107` (`_parse_cage_guest_args` at `:59`; built-in-only rejection raise at `:103-107`, message at `:105-106`: "Custom-guest CLI support is deferred (use the GUI for custom-guest mixed occupancy).")
- Blocks: CLI users cannot specify a custom guest `.gro`/`.itp` for mixed cage occupancy; they must use the GUI. The GUI already supports it via the explicit `cage_guest_assignments` API (`quickice/structure_generation/types.py`), and the Python API path is covered by CLI-side e2e tests (`tests/e2e/custom_guest/`, `tests/test_cli/test_mixed_cage_cli.py`).

## Test Coverage Gaps

**GROMACS (grompp) validation skipped when `gmx` is absent:**
- What's not tested: Topology correctness is validated by `gmx grompp` only when `gmx` is on PATH. The `gmx_skipif` marker (`tests/conftest.py:44`) gates **99** usages across the suite — 98 `@gmx_skipif` decorators (23 class-level, covering multi-test classes such as `test_e2e_gmx_validation.py`) plus one module-level `pytestmark` at `tests/test_cli/test_pipeline_grompp_matrix.py:77`. (The previously quoted 133 is the raw count of `gmx_skipif` string occurrences in `tests/`: 98 decorators + 31 imports + 1 definition + 1 pytestmark + 2 comments/docstring mentions.)
- Risk: On a machine WITHOUT gmx, byte-equivalence of `.gro`/`.top` is still checked, but actual GROMACS-parseable topology correctness is NOT. A top file that is byte-identical to a baseline but semantically broken would pass file-diff tests yet fail grompp.
- Mitigation status: In THIS environment `gmx 2023.5` (plumed-2.9.3 build) IS on PATH, so the grompp gates actually run here; the skip only bites on gmx-less machines. The 48.3-25 true-e2e audit plus quick-029 keep widening grompp-validated real-export coverage (e.g. `tests/e2e/solute_ion/test_e2e_mixed_ion_export.py`, `tests/e2e/solute_ion/test_e2e_cli_zero_ion_export.py`, `tests/e2e/hydrate/test_e2e_cli_mixed_builtin_hydrate_grompp.py`).
- Priority: Medium-low (environment-dependent).

**pytest-qt not installed — 2 permanently skipped tests:**
- What's not tested: `tests/test_solute_insertion.py:237, 251` carry `@pytest.mark.skip(reason="pytest-qt not installed in test environment")` — Qt-interaction coverage for the solute insertion UI path never runs. `pytest-qt` is not in `environment.yml`. Related reproducibility gap (new finding, 2026-10-15 verification): pytest itself is not pinned in `environment.yml` either (no pytest / pytest-qt / pytest-timeout entries) — the test framework's exact version is whatever is ad hoc in the conda env.
- Files: `tests/test_solute_insertion.py:237, 251`
- Risk: Solute-panel Qt signal/slot regressions go uncaught; the skipped tests also silently rot as the surrounding code evolves.
- Priority: Low-medium. Either add `pytest-qt` to `environment.yml` (requires user approval per AGENTS.md) or delete the dead tests.

**VTK rendering branches only exercised on a real display:**
- What's not tested: The VTK-dependent rendering paths (`quickice/gui/vtk_utils.py`, `quickice/gui/hydrate_renderer.py`, viewer widgets) are bypassed in headless/SSH-X11 runs via the `is_vtk_available()` heuristic; only the no-VTK fallback branches are exercised by `tests/e2e/test_e2e_gui_fullchain.py` and the `tests/gui_e2e_helpers.py`-based suites.
- Risk: A regression in actual VTK rendering (actor construction, camera, per-type guest styles) passes CI headlessly and only surfaces at the user's manual full-workflow test.
- Priority: Low (GUI rendering, not physics correctness). This is the residual behind the (stale) AGENTS.md "TEST-06 deferred" pointer.

**`python -O` / `PYTHONOPTIMIZE=1` code path:**
- What's not tested: No test runs the FULL CLI pipeline end-to-end under `PYTHONOPTIMIZE=1`. (Correction, 2026-10-15 verification: a targeted stripped-assert check DOES exist — `tests/scancode/test_scancode_bugs_pipeline.py:83` spawns a `python -O` subprocess and verifies `_validate_hydrate_atom_counts` still raises `ValueError` when asserts are stripped, with a source-guard test at `:67-81` preventing reversion.) One bare assert remains in production code (`quickice/gui/main_window.py:1355`); the previous `custom_guest_bridge.py` assert was converted to a real raise (regression test `tests/test_scancode_bugs_custom_guest_bridge_assert.py` exists).
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

Also verified clean this audit: no TODO/FIXME/HACK comments in `quickice/` or root Python files (the only "XXX" match is the legitimate `GENERIC_RESIDUE_NAMES` set in `quickice/structure_generation/molecule_validator.py:18`); no hardcoded TIP4P-ICE parameters or `0.0299`/`4` water magic numbers outside their single sources of truth; no comb-rule violations; test collection is **1849 tests / 0 errors** (QT_QPA_PLATFORM=offscreen; ~1-2s collect, re-run at verification).

---

*Concerns audit: 2026-10-15*
