---
phase: 45-e2e-hydrate-tab-workflow
plan: 06
subsystem: testing
tags: [e2e, grompp, gui-export, cli-export, cross-tab, sH, hydrate, pytest, gromacs]

# Dependency graph
requires:
  - phase: 39-new-hydrate-lattices
    provides: sH lattice type (triclinic-but-allowed, ~4480 guests through 3x3x8 slab) + HydrateConfig/InterfaceConfig/CustomMoleculeConfig
  - phase: 44.1-urgent-cross-tab-wiring
    provides: All 4 GUI exporters (Interface/Solute/CustomMolecule/Ion GROMACSExporter) accept hydrate_config=None param -> _stage_hydrate_guest_itps built-in path stages ch4_hydrate.itp + threads custom_guest_info=None to the GRO/TOP writers; CLI _run_export_step threads hydrate_config=getattr(self._hydrate_result,"config",None) -> _build_custom_guest_info returns None for built-in -> built-in path
  - phase: 45-03
    provides: Empirical verification that sH passes interface grompp rc=0 (the foundation this plan extends to the FULL GUI + CLI cross-tab chain)
  - phase: 44.1-22
    provides: test_e2e_builtin_cross_tab_regression.py -- the 4-exporter GUI cross-tab template (lines 86-367) this plan MIRRORS for the sH GUI half
  - phase: 44.1-20
    provides: test_e2e_custom_guest_cross_tab_cli.py -- the _make_cli_pipeline + _assert_step_output CLI cross-tab template (lines 155-298) this plan MIRRORS for the sH CLI half
provides:
  - sH full cross-tab GUI (4 exporters: Interface/Solute/CustomMolecule/Ion) + gmx grompp rc=0 e2e test with built-in guest_type="ch4" and hydrate_config=None
  - sH full cross-tab CLI (3 branches: interface/solute/ion) + gmx grompp rc=0 e2e test with built-in guest_type="ch4", ion built from solute (real workflow order)
  - Module-scoped sH_chain fixture amortizing the SLOW GenIce2 sH + 4x fresh assemble_slab (Pattern 2) + 4 inserters across BOTH the GUI and CLI tests
  - _assert_sH_export shared helper (CH4_H residue + ch4_hydrate.itp + no GUE/MOL_H leak + file-consistency + grompp) reused across all 4 GUI exporters + 3 CLI branches
  - Proof sH's large guest count (~4480) survives solute/ion insertion + export through BOTH GUI and CLI chains
affects:
  - 45-e2e-hydrate-tab-workflow (Wave 2 complete for ALL guest lattices: 45-04 GUI + 45-05 CLI for the 4 fast lattices + 45-06 sH GUI+CLI; water-only 45-07 remains for sTprime/17)
  - 47-05 (filled-ice grompp -- sH now proven through the FULL GUI + CLI tab chain, not just the interface step)

# Tech tracking
tech-stack:
  added: []  # no new deps -- test-only plan
  patterns:
    - "Combined GUI+CLI cross-tab test file for a SINGLE slow lattice (sH): module-scoped sH_chain fixture builds the FULL chain (hydrate -> 4x fresh assemble_slab -> solute/custom/ion-from-interface/ion-from-solute) ONCE, shared by BOTH the GUI (4 exporters) and CLI (3 branches) tests -- amortizes the SLOW GenIce2 sH + 4x slab + 4 inserters across both tests"
    - "Pattern 2 (fresh assemble_slab per inserter) at module-fixture scale: 4 fresh slabs (iface/iface_solute/iface_custom/iface_ion) so the ion inserter's mutation of iface.molecule_index (ion_inserter.py:259) does NOT cross-contaminate the solute/custom exporters' interface references"
    - "Dual ion construction in one fixture: ion_from_iface (GUI ion, built from a FRESH interface like the 44.1-22/45-04 built-in template) + ion_from_solute (CLI ion, built from the SOLUTE via _insert_ions_from_solute -- real CLI workflow order, the 44.1-20/45-05 integration aspect)"
    - "RENAMED cmet.gro/cmet.itp (moleculetype etoh -> MOL) -- the LIQUID custom molecule for the Custom Molecule GUI tab, NOT the cage guest; avoids pre-existing .gro/.top moleculetype name mismatch (copied from 44.1-22 template lines 109-124)"

key-files:
  created:
    - tests/test_e2e_sH_cross_tab.py
  modified: []

key-decisions:
  - "Single combined GUI+CLI test file for sH (NOT split into 2 files like 45-04/45-05) -- sH is SLOW (~10-30s for GenIce2 + tiling + inserters); the module-scoped sH_chain fixture amortizes the expensive setup across BOTH tests so the combined file is faster than 2 separate files each rebuilding the sH chain"
  - "Dual ion construction: ion_from_iface (GUI) built from a FRESH interface + ion_from_solute (CLI) built from the SOLUTE -- matches the GUI built-in template (ion from interface, 44.1-22/45-04) AND the CLI integration template (ion from solute, 44.1-20/45-05) in one fixture"
  - "Fresh assemble_slab per inserter (Pattern 2) -- 4 slabs (iface/iface_solute/iface_custom/iface_ion) because the ion inserter mutates iface.molecule_index (ion_inserter.py:259); deterministic with seed=42 so all 4 are byte-identical until an inserter mutates its own copy"
  - "hydrate_config=None (GUI) / hydrate.config (CLI) -> built-in path (stages ch4_hydrate.itp, references CH4_H); sH uses built-in guest_type=ch4"
  - "Do NOT assert exact guest/solute/ion counts -- assert > 0 only (Pitfall 5: sH has ~4480 guests, version-dependent)"
  - "Do NOT assert atom-number exactness in .gro header (Pitfall 4: GRO wraps at 100,000; assert_gro_top_consistent counts LINES not header, so it is robust -- sH interface ~54k atoms is under 100k but the wrap is irrelevant either way)"
  - "Assert GUE/MOL_H NOT in mols/residues to guard against the custom-guest/fallback path leaking into the built-in path"
  - "ws.mkdir(parents=True, exist_ok=True) before _make_cli_pipeline for each CLI branch -- _run_export_step writes to self._output_dir/{step_name}.gro but does NOT create the dir (only CLIPipeline.execute() does); mirrors 45-05 _assert_step_output"

patterns-established:
  - "Pattern: Combined GUI+CLI cross-tab test file for a SINGLE slow lattice with a shared module-scoped fixture -- extends the 45-04 (GUI) + 45-05 (CLI) split-file pattern to a single-file pattern when the lattice is slow enough that amortizing setup across both paths is worth the combined file"
  - "Pattern: _assert_sH_export(ws, gro_name, top_name, extra_mols, extra_itp) -- gro_name/top_name-parameterized shared helper with optional extra_mols/extra_itp, serving BOTH GUI (no extras, per-exporter ITPs checked in test body) and CLI (extras for per-branch mols/ITPs) assertion shapes"

# Metrics
duration: 3 min
completed: 2026-07-11
---

# Phase 45 Plan 06: sH Full Cross-Tab grompp (GUI + CLI) Summary

**sH (~4480 guests through 3x3x8 slab) passes gmx grompp rc=0 through the FULL GUI (4 exporters) + CLI (3 branches) cross-tab chain with built-in ch4, sharing a module-scoped fixture that amortizes the slow GenIce2 sH + 4x slab + 4 inserters**

## Performance

- **Duration:** 3 min (152 sec)
- **Started:** 2026-07-11T02:45:13Z
- **Completed:** 2026-07-11T02:47:45Z
- **Tasks:** 2
- **Files modified:** 1 (created)

## Accomplishments
- Proved sH (triclinic-but-allowed, ~4480 cage guests through the 3x3x8 nm slab + ~50k waters = ~54k atoms) passes `gmx grompp` (rc=0) through the FULL GUI cross-tab chain: Interface -> Solute -> Custom Molecule -> Ion -> Export (all 4 GUI exporters) with `hydrate_config=None` (the built-in ch4 path)
- Proved sH passes `gmx grompp` (rc=0) through the FULL CLI cross-tab chain: Interface -> Solute -> Ion -> Export (3 CLI export branches via `_run_export_step`) with built-in `guest_type="ch4"`, where the ion is built from the SOLUTE (real CLI workflow order via `_insert_ions_from_solute`, NOT from the interface directly)
- Confirmed sH's large guest count (~4480) survives solute insertion, custom molecule insertion, AND ion insertion, producing grompp-valid output at each export step for BOTH GUI (4 exporters x grompp) and CLI (3 branches x grompp)
- Combined the GUI pattern (from `test_e2e_builtin_cross_tab_regression.py` / 45-04) and the CLI pattern (from `test_e2e_custom_guest_cross_tab_cli.py` / 45-05) into a SINGLE test file with a shared module-scoped `sH_chain` fixture, amortizing the SLOW GenIce2 sH generation + 4x `assemble_slab` (Pattern 2) + 4 inserters across both tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Write sH full cross-tab GUI (4 exporters) + CLI (3 branches) + grompp test** -- `8f7b47c` (test) -- file written; initial run revealed a test bug (CLI output subdir not mkdir'd before `_run_export_step`), fixed inline; both tests pass (19.01s)
2. **Task 2: Run full test + commit** -- `8f7b47c` (test) -- both tasks share the single atomic test commit (plan specifies one commit message for the test file)

**Plan metadata:** pending (docs commit follows this summary)

## Files Created/Modified
- `tests/test_e2e_sH_cross_tab.py` (671 lines) -- Module-scoped `sH_chain` fixture (builds sH hydrate -> 4x fresh `assemble_slab` per inserter + solute/custom/ion-from-interface/ion-from-solute ONCE; asserts `guest_nmolecules > 0` on each slab + solute `n_molecules > 0` + ion `na_count > 0 or cl_count > 0` + ion `guest_atom_count`/`guest_nmolecules > 0` for the staging block; RENAMED cmet.gro/cmet.itp for the Custom Molecule GUI tab; dual ion construction: `ion` from fresh interface for GUI, `ion_cli` from solute for CLI), `_make_cli_pipeline` helper (copied from 44.1-20/45-05 template), shared `_assert_sH_export` helper (built-in ch4 path: CH4_H residue + ch4_hydrate.itp ITP + no GUE/MOL_H leak + optional extra_mols/extra_itp + assert_itp_completeness + assert_gro_top_consistent + grompp rc=0), `@gmx_skipif` GUI test exercising all 4 GUI exporters (Interface/Solute/CustomMolecule/Ion GROMACSExporter with hydrate_config=None + QFileDialog/QMessageBox mock) with per-exporter ITP checks (ch4_liquid.itp / cmet.itp / ion.itp), `@gmx_skipif` CLI test exercising 3 CLI export branches (`_run_export_step` interface/solute/ion via `_make_cli_pipeline`) with per-branch ITP + ion-species checks

## Decisions Made
- Combined the GUI + CLI cross-tab tests into a SINGLE file for sH (unlike 45-04/45-05 which split GUI/CLI into 2 files). sH is SLOW (~10-30s for GenIce2 + tiling + inserters per the RESEARCH Pitfall 5 / Open Question 5); the module-scoped `sH_chain` fixture amortizes the expensive setup across BOTH the GUI and CLI tests, so the combined file is faster than 2 separate files each rebuilding the sH chain.
- Built a DUAL ion construction in the fixture: `ion_from_iface` (GUI ion, built from a FRESH interface -- matches the 44.1-22/45-04 built-in template where the GUI ion exporter gets an ion built from the interface) + `ion_from_solute` (CLI ion, built from the SOLUTE via `_insert_ions_from_solute` -- matches the 44.1-20/45-05 CLI integration template where the ion is built from the solute, the real CLI workflow order). Both are needed because the GUI and CLI test different ion-construction paths.
- Applied Pattern 2 (fresh `assemble_slab` per inserter) with 4 slabs (iface/iface_solute/iface_custom/iface_ion) -- the ion inserter mutates `iface.molecule_index` in-place (`ion_inserter.py:259`), so each inserter gets its OWN fresh slab (deterministic with `seed=42`) to prevent cross-contamination. Mirrors `test_e2e_lattice_cross_tab_gui.py` (45-04) lines 168-215.
- Used `hydrate_config=None` (GUI) / `hydrate.config` (CLI) for the built-in path -> stages `ch4_hydrate.itp` and references `CH4_H`. sH uses built-in `guest_type="ch4"` (NOT custom).
- Did NOT assert exact guest/solute/ion counts -- asserted `> 0` only (Pitfall 5: sH has ~4480 guests through the 3x3x8 slab, version-dependent).
- Did NOT assert atom-number exactness in the .gro header (Pitfall 4: GRO wraps atom numbers at 100,000; `assert_gro_top_consistent` counts atom LINES not the header, so it is robust).
- Asserted `GUE`/`MOL_H` NOT in mols/residues at every export step to guard against the custom-guest/fallback path leaking into the built-in path (mirrors the 44.1-22 template's regression guard).
- Built the RENAMED cmet.gro/cmet.itp (moleculetype `etoh` -> `MOL`) ONCE at module level -- it is the LIQUID custom molecule for the Custom Molecule GUI tab, NOT the cage guest; `ch4_hydrate.itp` (cage) and `cmet.itp` (liquid) do not collide. Copied the rename logic verbatim from `test_e2e_builtin_cross_tab_regression.py:109-124`.
- Box 3.0x3.0x8.0 nm (shortest vector 3.0 nm > 2x rcoulomb=2.0 nm -- grompp PBC rule); 1x1x1 supercell sufficient for sH: sH is triclinic BUT explicitly allowed (NOT in `TRICLINIC_HYDRATE_PHASES` which only blocks c0te/c1te).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CLI output subdirectory not created before `_run_export_step`**
- **Found during:** Task 1 (CLI test first run)
- **Issue:** The CLI test set `ws = tmp_path / "interface"` (etc.) and called `_make_cli_pipeline(ws, ...)` + `_run_export_step()`, but `_run_export_step` writes to `self._output_dir / f"{step_name}.gro` and does NOT create the output directory (only `CLIPipeline.execute()` does). The first run failed with `[Errno 2] No such file or directory: '.../interface/interface.gro'` (rc=1).
- **Fix:** Added `ws.mkdir(parents=True, exist_ok=True)` before `_make_cli_pipeline` for each of the 3 CLI branches (interface/solute/ion). This mirrors the 45-05 template's `_assert_step_output` helper which does the same `ws.mkdir(parents=True, exist_ok=True)` before constructing the pipeline.
- **Files modified:** tests/test_e2e_sH_cross_tab.py (CLI test section)
- **Verification:** Both tests pass (19.01s) after the fix; the GUI test was unaffected (it already `ws.mkdir()`'d each per-exporter subdir).
- **Committed in:** 8f7b47c (Task 2 / single test commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The bug was a test-setup omission (missing `mkdir`), not a source issue. The fix matches the established 45-05 CLI template pattern. No source code was modified (test-only plan per the plan's explicit constraint).

## Issues Encountered
None beyond the auto-fixed CLI `mkdir` bug above. Both tests pass on the second run in 19.01s. `gmx` is on PATH at `/data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx`. The module-scoped fixture amortizes GenIce2 sH + 4x `assemble_slab` + 4 inserters across both tests; grompp on each resulting ~54k-atom structure is sub-second. The sH chain built in ~10s (fixture setup); each test's 4 (GUI) / 3 (CLI) exports + grompp took ~4-9s. No source code was modified (test-only plan per the plan's explicit constraint).

## User Setup Required
None -- no external service configuration required. `gmx` is already on PATH; `QT_QPA_PLATFORM=offscreen` is set for the headless GUI exporter tests.

## Next Phase Readiness
- **Wave 2 complete for ALL guest lattices:** Together with 45-04 (GUI full cross-tab for sII/c2te/ice1hte/16) and 45-05 (CLI full cross-tab for sII/c2te/ice1hte/16), all 5 guest-bearing new lattices (sII/c2te/ice1hte/16/sH) are now proven through the FULL tab chain (Interface -> Solute -> Ion/Custom -> Export) for BOTH GUI (4 exporters) and CLI (3 branches), all with built-in ch4. sH's large guest count (~4480) is now proven to survive solute/ion insertion + export through both chains.
- **Ready for water-only full-chain (45-07):** sTprime/17 are the remaining new lattices (water-only, no cage guests for solute/ion context). 45-07 must verify the solute/ion inserters don't IndexError on `guest_nmolecules=0` (Pitfall 3 -- risk area, UNVERIFIED).
- **No blockers.** sH is now proven through the FULL GUI + CLI tab chain.
- **Existing regression unaffected:** `tests/test_e2e_builtin_cross_tab_regression.py` (4 GUI + 4 CLI), `tests/test_e2e_lattice_cross_tab_gui.py` (45-04, 4 GUI), `tests/test_e2e_lattice_cross_tab_cli.py` (45-05, 4 CLI), and `tests/test_e2e_sH_interface_export.py` (45-03, 2 sH interface) still pass alongside the new 2 sH cross-tab tests -- no source code changed (test-only plan).

---
*Phase: 45-e2e-hydrate-tab-workflow*
*Completed: 2026-07-11*
