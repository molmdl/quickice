---
phase: 45-e2e-hydrate-tab-workflow
plan: 07
subsystem: testing
tags: [e2e, grompp, gui-export, cli-export, cross-tab, water-only, sTprime, ice17, hydrate, pytest, gromacs]

# Dependency graph
requires:
  - phase: 39-new-hydrate-lattices
    provides: sTprime (Ice XVI) + 17 (Ice XVII) water-only lattice types (is_water_only=True -> generator skips cage-guest placement) + HydrateConfig/InterfaceConfig
  - phase: 44.1-urgent-cross-tab-wiring
    provides: All 4 GUI exporters (Interface/Solute/CustomMolecule/Ion GROMACSExporter) accept hydrate_config=None param -> _stage_hydrate_guest_itps no-guest gate (guest_info.py:250) returns (None,{}) for guest_atom_count=0; CLI _run_export_step threads hydrate_config=getattr(self._hydrate_result,"config",None) -> copy_itp_files_for_structure skips cage-guest ITP when guest_atom_count=0
  - phase: 45-01
    provides: Empirical verification that sTprime + 17 interface export passes grompp rc=0 (SOL only, no guest ITP) -- the foundation this plan extends to the FULL GUI + CLI cross-tab chain with solute/ion inserters
  - phase: 44.1-22
    provides: test_e2e_builtin_cross_tab_regression.py -- the 4-exporter GUI cross-tab template (lines 86-367) this plan MIRRORS for the water-only GUI half (3 exporters, no custom)
  - phase: 44.1-20
    provides: test_e2e_custom_guest_cross_tab_cli.py -- the _make_cli_pipeline + _assert_step_output CLI cross-tab template (lines 155-298) this plan MIRRORS for the water-only CLI half (3 branches)
provides:
  - sTprime + 17 (water-only, guest_nmolecules=0) full cross-tab GUI (3 exporters: Interface/Solute/Ion) + gmx grompp rc=0 e2e test -- PROVES solute/ion inserters do NOT crash on guest_nmolecules=0 (Pitfall 3 verified safe)
  - sTprime + 17 full cross-tab CLI (3 branches: interface/solute/ion) + gmx grompp rc=0 e2e test with built-in guest_type="ch4" (IGNORED by the generator water-only skip)
  - Module-scoped water_only_chains fixture amortizing the GenIce2 sTprime + 17 + 3x fresh assemble_slab (Pattern 2) + 2 inserters across BOTH the GUI and CLI tests
  - _assert_water_only_export shared helper (SOL + extras, NO CH4_H/GUE/MOL_H, NO ch4_hydrate.itp, tip4p-ice.itp staged, file-consistency + grompp) reused across all 3 GUI exporters + 3 CLI branches
  - Proof the no-guest gate (guest_info.py:250 for GUI / itp_helpers.py "if guest_atom_count > 0" for CLI) correctly fires for guest_atom_count=0 -> no cage-guest ITP staged
affects:
  - 45-e2e-hydrate-tab-workflow (Wave 2 COMPLETE for ALL 7 new lattices: 45-04/05 GUI+CLI for sII/c2te/ice1hte/16 + 45-06 sH GUI+CLI + 45-07 water-only sTprime/17 GUI+CLI)
  - 47-05 (filled-ice grompp -- water-only lattices now proven through the FULL GUI + CLI tab chain with solute/ion, not just the interface step)

# Tech tracking
tech-stack:
  added: []  # no new deps -- test-only plan
  patterns:
    - "Water-only cross-tab test: module-scoped water_only_chains fixture builds the FULL chain (hydrate -> 3x fresh assemble_slab -> solute/ion) ONCE for BOTH sTprime + 17, with KEY Pitfall 3 assertions at fixture-build time (hydrate.guest_count==0, iface.guest_nmolecules==0, iface.guest_atom_count==0, solute.n_molecules>0, ion.na_count>0 or ion.cl_count>0) -- the inserters NOT crashing is the whole point"
    - "Water-only _assert_water_only_export(ws, gro_name, top_name, extra_mols, extra_itp): asserts SOL (+ extras), NO CH4_H/GUE/MOL_H (no cage-guest residue), NO ch4_hydrate.itp (no-guest gate fires), tip4p-ice.itp staged (water ITP is structural), file-consistency + grompp -- the inverse of the built-in ch4 _assert_lattice_export (which asserts CH4_H present + ch4_hydrate.itp staged)"
    - "3-exporter (interface/solute/ion) GUI test for water-only (NO custom -- no cage-guest context); mirrors 45-04's 4-exporter pattern minus the Custom Molecule tab"

key-files:
  created:
    - tests/test_e2e_water_only_cross_tab.py
  modified: []

key-decisions:
  - "KEY Pitfall 3 verification: solute/ion inserters do NOT crash on guest_nmolecules=0 (sTprime + 17) -- the no-guest gate (guest_info.py:250) returns None/{} so the writers emit SOL (+ solute/ion) only with no cage-guest residue. This is the central finding of the plan: the research-indicated safety is now PROVEN by test."
  - "hydrate_config=None (GUI) / hydrate.config (CLI) -> built-in path BUT the no-guest gate fires for guest_atom_count=0 -> NO ch4_hydrate.itp staged (unlike 45-04/45-05/45-06 built-in ch4 which stages ch4_hydrate.itp). Water-only is the inverse assertion shape: assert NOT present, not present."
  - "3 GUI exporters (interface/solute/ion) NOT 4 -- Custom Molecule tab SKIPPED per plan: no cage-guest context for the custom-molecule inserter to interact with (it inserts in the water region, same as any lattice); focus on solute/ion which are the Pitfall 3 risk"
  - "CLI ion built from the interface directly (via _insert_ions) NOT from the solute (unlike 45-05/45-06 which used _insert_ions_from_solute) -- matches the plan's fixture (ion = _insert_ions(iface_ion, ...)) and the 44.1-22/45-04 built-in template; simpler since there's no cage-guest metadata to propagate through the solute->ion hand-off"
  - "guest_type='ch4' is IGNORED for water-only lattices (generator water-only skip at hydrate_generator.py:291-310 'if not is_water_only') -- still required by HydrateConfig.__post_init__ but never reaches parse_guest; documented in the fixture docstring"
  - "Assert ch4_hydrate.itp NOT staged (NOT 'staged with CH4_H') -- the no-guest gate is the KEY water-only invariant; a cage-guest ITP leaking into a water-only export would indicate the gate is broken"
  - "Assert CH4_H/GUE/MOL_H NOT in mols/residues at every export step (water-only: SOL + solute/ion species only) -- guards against the custom-guest/fallback path leaking into the no-guest path"
  - "Do NOT assert exact solute/ion counts -- assert > 0 only (Pitfall 5: counts vary by lattice/version); the > 0 assertion IS the Pitfall 3 no-crash proof"

patterns-established:
  - "Pattern: Water-only cross-tab test = the INVERSE assertion shape of the built-in ch4 cross-tab test (45-04/45-05/45-06): assert ch4_hydrate.itp NOT staged + CH4_H NOT in mols/residues (no cage guest) instead of assert ch4_hydrate.itp staged + CH4_H present"
  - "Pattern: Pitfall-3 verification = assert at fixture-build time that the inserters ran to completion (solute.n_molecules > 0, ion.na_count > 0 or ion.cl_count > 0) -- the crash would happen during _insert_solutes/_insert_ions, so the fixture assertion catches it before the export tests even run"

# Metrics
duration: 2 min
completed: 2026-07-11
---

# Phase 45 Plan 07: Water-Only (sTprime/17) Cross-Tab grompp Summary

**Water-only lattices sTprime + 17 (guest_nmolecules=0) pass gmx grompp rc=0 through the FULL GUI (3 exporters) + CLI (3 branches) cross-tab chain with solute/ion inserters -- PROVES Pitfall 3 (no crash on empty-guest interface), no ch4_hydrate.itp staged**

## Performance

- **Duration:** 2 min (121 sec)
- **Started:** 2026-07-11T02:49:07Z
- **Completed:** 2026-07-11T02:51:08Z
- **Tasks:** 2
- **Files modified:** 1 (created)

## Accomplishments
- PROVED Pitfall 3 (from 45-RESEARCH.md) is safe: the solute inserter (`_insert_solutes`) and ion inserter (`_insert_ions`) do NOT crash on `guest_nmolecules=0` / `guest_atom_count=0` water-only interfaces (sTprime + 17). The inserters place solute/ions in the WATER region (independent of cage guests), so they complete normally: `solute.n_molecules > 0` and `ion.na_count > 0 or ion.cl_count > 0` for both lattices. This was the central unverified risk area flagged in the research (Open Question 1 / Pitfall 3).
- Proved sTprime + 17 pass `gmx grompp` (rc=0) through the FULL GUI cross-tab chain: Interface -> Solute -> Ion -> Export (3 GUI exporters: Interface/Solute/Ion GROMACSExporter with `hydrate_config=None`), with NO cage-guest ITP staged (the no-guest gate at `guest_info.py:250` fires for `guest_atom_count=0` -> returns `(None, {})` -> no `ch4_hydrate.itp`).
- Proved sTprime + 17 pass `gmx grompp` (rc=0) through the FULL CLI cross-tab chain: Interface -> Solute -> Ion -> Export (3 CLI export branches via `_run_export_step`), with `copy_itp_files_for_structure` skipping the cage-guest ITP (`if guest_atom_count > 0` gate -> 0 -> skip) -> only `tip4p-ice.itp` (+ `ch4_liquid.itp` for solute, `ion.itp` for ion) staged.
- Confirmed the water-only export shape: SOL (+ CH4_L for solute, NA/CL for ion) only; NO CH4_H / GUE / MOL_H in `[molecules]` or .gro residues; NO `ch4_hydrate.itp` staged; `tip4p-ice.itp` always staged (structural water ITP).
- Combined the GUI pattern (from `test_e2e_lattice_cross_tab_gui.py` / 45-04) and the CLI pattern (from `test_e2e_lattice_cross_tab_cli.py` / 45-05) into a SINGLE test file with a shared module-scoped `water_only_chains` fixture, amortizing the GenIce2 sTprime + 17 generation + 3x `assemble_slab` (Pattern 2) + 2 inserters across both tests.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write water-only (sTprime, 17) solute/ion cross-tab + grompp test** -- `c461695` (test) -- file written; first run all 4 parametrized cases PASSED (2.42s) -- no Pitfall 3 crash
2. **Task 2: Run full test + commit** -- `c461695` (test) -- both tasks share the single atomic test commit (plan specifies one commit message for the test file)

**Plan metadata:** pending (docs commit follows this summary)

## Files Created/Modified
- `tests/test_e2e_water_only_cross_tab.py` (659 lines) -- Module-scoped `water_only_chains` fixture (builds sTprime + 17 hydrate -> 3x fresh `assemble_slab` per inserter + solute/ion ONCE; KEY Pitfall 3 assertions at fixture-build time: `hydrate.guest_count==0`, `iface.guest_nmolecules==0`, `iface.guest_atom_count==0`, `solute.n_molecules > 0`, `ion.na_count > 0 or ion.cl_count > 0` -- the inserters NOT crashing is the whole point), `_make_cli_pipeline` helper (copied from 45-05 template), shared `_assert_water_only_export` helper (water-only path: SOL + extras, NO CH4_H/GUE/MOL_H, NO ch4_hydrate.itp, tip4p-ice.itp staged, optional extra_mols/extra_itp, assert_itp_completeness + assert_gro_top_consistent + grompp rc=0), `@gmx_skipif` GUI test exercising 3 GUI exporters (Interface/Solute/Ion GROMACSExporter with hydrate_config=None + QFileDialog/QMessageBox mock) with per-exporter ITP checks (ch4_liquid.itp / ion.itp), `@gmx_skipif` CLI test exercising 3 CLI export branches (`_run_export_step` interface/solute/ion via `_make_cli_pipeline`) with per-branch ITP + ion-species checks

## Decisions Made
- KEY Pitfall 3 verification: the solute/ion inserters do NOT crash on `guest_nmolecules=0` (sTprime + 17). The no-guest gate (`guest_info.py:250` `if guest_atom_count <= 0 or guest_nmolecules <= 0: return None, {}`) returns the no-op result so the writers emit SOL (+ solute/ion) only with no cage-guest residue. This is the central finding -- the research-indicated safety is now PROVEN by test (not just empirically observed at the interface step).
- Used `hydrate_config=None` (GUI) / `hydrate.config` (CLI) for the built-in path BUT the no-guest gate fires for `guest_atom_count=0` -> NO `ch4_hydrate.itp` staged (unlike 45-04/45-05/45-06 built-in ch4 which stages `ch4_hydrate.itp`). Water-only is the INVERSE assertion shape: assert NOT present, not present.
- 3 GUI exporters (interface/solute/ion) NOT 4 -- Custom Molecule tab SKIPPED per plan: no cage-guest context for the custom-molecule inserter to interact with (it inserts in the water region, same as any lattice); focus on solute/ion which are the Pitfall 3 risk.
- CLI ion built from the interface directly (via `_insert_ions`) NOT from the solute (unlike 45-05/45-06 which used `_insert_ions_from_solute` for the integration aspect) -- matches the plan's fixture (`ion = _insert_ions(iface_ion, ...)`) and the 44.1-22/45-04 built-in template. Simpler since there's no cage-guest metadata to propagate through the solute->ion hand-off for water-only (no cage guest).
- `guest_type="ch4"` is IGNORED for water-only lattices (generator water-only skip at `hydrate_generator.py:291-310` `if not is_water_only`) -- still required by `HydrateConfig.__post_init__` (guest_type is a required field) but never reaches `parse_guest`; documented in the fixture docstring so future readers don't assume ch4 was placed.
- Asserted `ch4_hydrate.itp` NOT staged (NOT 'staged with CH4_H') -- the no-guest gate is the KEY water-only invariant; a cage-guest ITP leaking into a water-only export would indicate the gate is broken.
- Asserted CH4_H/GUE/MOL_H NOT in mols/residues at every export step (water-only: SOL + solute/ion species only) -- guards against the custom-guest/fallback path leaking into the no-guest path.
- Did NOT assert exact solute/ion counts -- asserted `> 0` only (Pitfall 5: counts vary by lattice/version); the `> 0` assertion IS the Pitfall 3 no-crash proof (a crash would never reach the assertion).
- Did NOT assert atom-number exactness in the .gro header (Pitfall 4: GRO wraps at 100,000; `assert_gro_top_consistent` counts atom LINES, not the header, so it is robust).
- Applied Pattern 2 (fresh `assemble_slab` per inserter) with 3 slabs (iface/iface_solute/iface_ion) -- the ion inserter mutates `iface.molecule_index` in-place (`ion_inserter.py:259`), so each inserter gets its OWN fresh slab (deterministic with `seed=42`) to prevent cross-contamination. Mirrors 45-04 lines 168-215.

## Deviations from Plan

None - plan executed exactly as written. The KEY Pitfall 3 assertion (solute/ion inserters do NOT crash on `guest_nmolecules=0`) held on the first run -- no source bug was found, so this remained a TEST-ONLY plan (no `quickice/` source modifications, per the plan's explicit constraint). The research-indicated safety (no-guest gate at `guest_info.py:250` returns `None/{}`) is now PROVEN by test.

## Issues Encountered
None. All 4 parametrized cases passed on the first run (2.42s); the final verification run also passed (2.35s). `gmx` is on PATH at `/data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx`. `QT_QPA_PLATFORM=offscreen` was set for the GUI exporter tests (the env var was unset in the shell, so it was passed inline to the pytest invocation, matching the established pattern for the 45-04/45-05/45-06 tests). The module-scoped fixture amortizes GenIce2 sTprime + 17 + 3x `assemble_slab` + 2 inserters across both tests; grompp on each resulting structure is sub-second. No source code was modified (test-only plan per the plan's explicit constraint).

## User Setup Required
None -- no external service configuration required. `gmx` is already on PATH; `QT_QPA_PLATFORM=offscreen` is set inline for the headless GUI exporter tests.

## Next Phase Readiness
- **Wave 2 COMPLETE for ALL 7 new lattices:** Together with 45-04 (GUI full cross-tab for sII/c2te/ice1hte/16), 45-05 (CLI full cross-tab for sII/c2te/ice1hte/16), and 45-06 (sH GUI+CLI), ALL 7 new guest-bearing + water-only lattices (sII/c2te/ice1hte/16/sH/sTprime/17) are now proven through the FULL tab chain (Interface -> Solute -> Ion/Custom -> Export) for BOTH GUI and CLI, all with grompp rc=0. The 2 water-only lattices (sTprime/17) are proven to NOT crash the solute/ion inserters on `guest_nmolecules=0` (Pitfall 3 verified safe).
- **Remaining Phase 45 plans:** 45-08 through 45-14 (custom guest with non-sI lattices, triclinic blocking e2e, triclinic hydrate-only export @ 4x4x4, depol CLI flag, mixed occupancy). The water-only Pitfall 3 risk area is now CLOSED.
- **No blockers.** sTprime + 17 are now proven through the FULL GUI + CLI tab chain with solute/ion inserters.
- **Existing regression unaffected:** `tests/test_e2e_builtin_cross_tab_regression.py` (4 GUI + 4 CLI), `tests/test_e2e_lattice_cross_tab_gui.py` (45-04, 4 GUI), `tests/test_e2e_lattice_cross_tab_cli.py` (45-05, 4 CLI), `tests/test_e2e_sH_cross_tab.py` (45-06, sH GUI+CLI), and `tests/test_e2e_lattice_interface_*.py` (45-01/02/03) still pass alongside the new 2 water-only cross-tab tests -- no source code changed (test-only plan).

---
*Phase: 45-e2e-hydrate-tab-workflow*
*Completed: 2026-07-11*
