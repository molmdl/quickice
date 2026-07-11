---
phase: 45-e2e-hydrate-tab-workflow
plan: 05
subsystem: testing
tags: [e2e, grompp, cli-export, cross-tab, sII, c2te, ice1hte, 16, hydrate, pytest, gromacs]

# Dependency graph
requires:
  - phase: 39-new-hydrate-lattices
    provides: 4 new guest-bearing lattice types (sII, c2te, ice1hte, 16) + HydrateConfig/InterfaceConfig
  - phase: 44.1-urgent-cross-tab-wiring
    provides: CLI _run_export_step threads hydrate_config=getattr(self._hydrate_result,"config",None) -> _build_custom_guest_info returns None for built-in -> custom_guest_info=None -> built-in path stages ch4_hydrate.itp + references CH4_H
  - phase: 44.1-20
    provides: test_e2e_custom_guest_cross_tab_cli.py -- the _make_cli_pipeline + _assert_step_output CLI cross-tab template (298 lines) this plan MIRRORS, swapping sI custom ethanol -> parametrized 4 lattices with built-in ch4
  - phase: 45-01
    provides: Empirical verification that sII/c2te/ice1hte/16 pass interface grompp rc=0 (the foundation this plan extends to the full CLI cross-tab chain)
provides:
  - Parametrized full CLI cross-tab (3 branches: Interface/Solute/Ion) + grompp e2e test for the 4 new guest-bearing lattices (sII/c2te/ice1hte/16) with built-in guest_type="ch4"
  - Module-scoped lattice_chains fixture amortizing GenIce2 + assemble_slab + 2 inserters (solute + ion-from-solute) across all parametrized export cases
  - _assert_step_output shared helper (CH4_H residue + ch4_hydrate.itp + no GUE/MOL_H leak + file-consistency + grompp) reused across all 3 CLI export branches
  - Proof the ion built from SOLUTE (real CLI workflow order via _insert_ions_from_solute) preserves the built-in cage-guest metadata end-to-end so the ion export still stages ch4_hydrate.itp + references CH4_H
affects:
  - 45-e2e-hydrate-tab-workflow (Wave 2 complete for guest lattices: 45-04 GUI + 45-05 CLI; water-only 45-07 remains for sTprime/17)
  - 47-05 (filled-ice grompp -- c2te/ice1hte now proven through the FULL CLI tab chain Interface->Solute->Ion, not just the interface step)

# Tech tracking
tech-stack:
  added: []  # no new deps -- test-only plan
  patterns:
    - "Pattern 4 (CLI export-step-direct): _make_cli_pipeline(output_dir, hydrate, downstream_attr, downstream_struct) + _run_export_step() direct -- avoids full CLIPipeline.execute() arg-parse + source step; isolates the export branch (copied verbatim from 44.1-20 template lines 155-166)"
    - "Module-scoped lattice_chains fixture building the FULL chain (hydrate -> iface -> solute -> ion-from-solute) ONCE per 4 lattices, amortizing GenIce2 (~1-5s each) across all 4 parametrized 3-branch test cases"
    - "Ion built from SOLUTE via _insert_ions_from_solute (real CLI workflow order) -- NOT from the interface directly; _solute_to_ion_source propagates solute attributes onto solute.interface_structure (duck-typing) so IonInserter can access them (the integration aspect per-branch CLI tests don't cover)"

key-files:
  created:
    - tests/test_e2e_lattice_cross_tab_cli.py
  modified: []

key-decisions:
  - "Ion built from SOLUTE (real CLI workflow order via _insert_ions_from_solute), NOT from the interface directly -- the integration aspect the per-branch CLI tests don't cover; _solute_to_ion_source propagates solute attrs onto solute.interface_structure"
  - "Single iface per lattice (NOT Pattern 2 fresh-slab-per-inserter) -- matches the 44.1-20 CLI template which uses one iface; _solute_to_ion_source only attaches extra attrs to iface that the interface exporter ignores, and the template proves this works"
  - "3 CLI export branches (interface/solute/ion) -- NOT 4 (no custom-molecule branch; matches the 44.1-20 CLI template which also had 3 branches)"
  - "hydrate_config built-in -> _build_custom_guest_info returns None -> built-in path (stages ch4_hydrate.itp, references CH4_H); all 4 lattices use built-in guest_type=ch4"
  - "Do NOT assert exact guest/solute/ion counts -- assert > 0 only (Pitfall 5: counts vary by lattice/version)"
  - "Do NOT assert atom-number exactness in .gro header (Pitfall 4: GRO wraps at 100,000; assert_gro_top_consistent counts LINES not header, so it is robust)"
  - "Assert GUE/MOL_H NOT in mols/residues to guard against the custom-guest/fallback path leaking into the built-in path"
  - "shutil.which('gmx') guard inside _assert_step_output (belt-and-suspenders with @gmx_skipif on the test) so file-consistency + guest-residue asserts run whenever the test runs"

patterns-established:
  - "Pattern: Module-scoped lattice_chains fixture with ion-from-solute chaining for the FULL CLI cross-tab chain (3 branches) -- extends the 44.1-20 sI single-case template to a parametrized 4-lattice matrix"
  - "Pattern: _assert_step_output(ws, step_name, hydrate, structure, attr, extra_mols, extra_itp) -- step_name-parameterized shared helper asserting built-in ch4 path (CH4_H + ch4_hydrate.itp + no GUE/MOL_H leak + file-consistency + grompp) for all 3 CLI export branches"

# Metrics
duration: 1 min
completed: 2026-07-11
---

# Phase 45 Plan 05: CLI Full Cross-Tab grompp for 4 New Lattices Summary

**Parametrized full CLI cross-tab (Interface->Solute->Ion) + gmx grompp rc=0 for 4 new guest lattices (sII/c2te/ice1hte/16) with built-in ch4, ion built from solute (real workflow order)**

## Performance

- **Duration:** 1 min (68 sec)
- **Started:** 2026-07-11T02:42:47Z
- **Completed:** 2026-07-11T02:43:55Z
- **Tasks:** 2
- **Files modified:** 1 (created)

## Accomplishments
- Proved the 4 new guest-bearing lattice types from Phase 39 (sII, c2te, ice1hte, 16) pass `gmx grompp` (rc=0) through the FULL CLI cross-tab chain: Interface -> Solute -> Ion -> Export (3 CLI export branches via `_run_export_step`) with built-in `guest_type="ch4"` (`hydrate_config` = the built-in `HydrateConfig` -> `_build_custom_guest_info` returns `None` -> built-in path)
- Proved the ion built from the SOLUTE (real CLI workflow order via `_insert_ions_from_solute` -> `_solute_to_ion_source`, NOT from the interface directly) preserves the built-in cage-guest metadata end-to-end -- the ion export still stages `ch4_hydrate.itp` and references `CH4_H` in `[molecules]` (the integration aspect the per-branch CLI tests don't cover)
- Confirmed the built-in path correctly stages `ch4_hydrate.itp` and references `CH4_H` (NOT `GUE` or `MOL_H`) at every CLI export step (interface/solute/ion) for all 4 lattices -- no custom-guest/fallback path leak
- Completed the CLI half of Wave 2 (the GUI half was 45-04); together with 45-01/02/03 (interface-only) the new-lattice coverage now extends from the interface step to the full cross-tab chain for both GUI and CLI on all 4 guest-bearing lattices

## Task Commits

Each task was committed atomically:

1. **Task 1: Write parametrized CLI full cross-tab (3 branches) + grompp for 4 lattices** -- `1d7a368` (test) -- file written + 4/4 verified in Task 1's `<verify>` (3.16s)
2. **Task 2: Run full test + commit** -- `1d7a368` (test) -- both tasks share the single atomic test commit (plan specifies one commit message for the test file)

**Plan metadata:** pending (docs commit follows this summary)

## Files Created/Modified
- `tests/test_e2e_lattice_cross_tab_cli.py` (417 lines) -- Module-scoped `lattice_chains` fixture (builds hydrate -> `assemble_slab` -> solute -> ion-from-solute ONCE for all 4 lattices; asserts `guest_nmolecules > 0` + solute `n_molecules > 0` + ion `na_count > 0 or cl_count > 0` + ion `guest_atom_count`/`guest_nmolecules > 0` for the staging block), `_make_cli_pipeline` helper (copied from 44.1-20 template), shared `_assert_step_output` helper (built-in ch4 path: CH4_H residue + ch4_hydrate.itp ITP + no GUE/MOL_H leak + assert_itp_completeness + assert_gro_top_consistent + grompp rc=0), parametrized `@gmx_skipif` test exercising 3 CLI export branches (`_run_export_step` interface/solute/ion via `_make_cli_pipeline`) for sII/c2te/ice1hte/16 with per-branch ITP checks (ch4_liquid.itp for solute, ion.itp for ion) and per-ion-species molecule checks (NA/CL conditionally)

## Decisions Made
- Built the ion from the SOLUTE (real CLI workflow order via `_insert_ions_from_solute`), NOT from the interface directly -- this is the integration aspect the per-branch CLI tests (44.1-17) don't cover. `_solute_to_ion_source` propagates solute (+ custom-molecule) attributes onto `solute.interface_structure` (duck-typing) so `IonInserter` can access them.
- Used a SINGLE iface per lattice (NOT Pattern 2 fresh-slab-per-inserter from 45-04) -- matches the 44.1-20 CLI template which uses one iface. `_solute_to_ion_source` only attaches extra solute attributes to `iface` that the interface exporter ignores, and the template proves this works end-to-end. Pattern 2 is a GUI-test concern (multiple inserters reading the same iface); the CLI template's single-iface + ion-from-solute chain is the established pattern.
- Used 3 CLI export branches (interface/solute/ion) -- NOT 4 (no custom-molecule branch). Matches the 44.1-20 CLI template which also had 3 branches; the CLI custom-molecule branch is a separate concern.
- Used `hydrate_config` = the built-in `HydrateConfig` (carried on `hydrate.config`) for all 4 lattices -> `_build_custom_guest_info(config)` returns `None` for built-in ch4 -> `custom_guest_info=None` -> built-in path stages `ch4_hydrate.itp` + references `CH4_H`. All 4 lattices use built-in `guest_type="ch4"`.
- Did NOT assert exact guest/solute/ion counts -- asserted `> 0` only (Pitfall 5: counts vary by lattice/version; the c2te filled ice produces ~2048 guests at 1x1x1 interface while sII/16 produce fewer).
- Did NOT assert atom-number exactness in the .gro header (Pitfall 4: GRO wraps atom numbers at 100,000; `assert_gro_top_consistent` counts atom LINES not the header, so it is robust).
- Asserted `GUE`/`MOL_H` NOT in mols/residues at every export step to guard against the custom-guest/fallback path leaking into the built-in path (mirrors the 44.1-22 template's regression guard).
- Guarded the grompp call inside `_assert_step_output` with `shutil.which("gmx")` (belt-and-suspenders with `@gmx_skipif` on the test) so file-consistency + guest-residue asserts run whenever the test runs.
- Box 3.0x3.0x8.0 nm (shortest vector 3.0 nm > 2x rcoulomb=2.0 nm -- grompp PBC rule); 1x1x1 supercell sufficient for these 4 non-triclinic guest lattices (Pitfall 1 only affects the triclinic filled ices c0te/c1te, which are blocked).

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered
None. All 4 parametrized cases passed on the first run in 3.16s. `gmx` is on PATH at `/data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx`. The module-scoped fixture amortizes GenIce2 + `assemble_slab` + 2 inserters (solute + ion-from-solute) across all 4 parametrized cases; grompp on each resulting structure is sub-second. No source code was modified (test-only plan per the plan's explicit constraint).

## User Setup Required
None -- no external service configuration required. `gmx` is already on PATH.

## Next Phase Readiness
- **Wave 2 complete for guest lattices:** Together with 45-04 (GUI full cross-tab), all 4 guest-bearing new lattices (sII/c2te/ice1hte/16) are now proven through the FULL tab chain (Interface -> Solute -> Ion/Custom -> Export) for BOTH GUI (4 exporters) and CLI (3 branches), all with built-in ch4. The CLI ion-from-solute integration path is now covered (this plan).
- **Ready for water-only full-chain (45-07):** sTprime/17 are excluded here (no cage guests for solute/ion context). 45-07 must verify the solute/ion inserters don't IndexError on `guest_nmolecules=0` (Pitfall 3 -- risk area, UNVERIFIED).
- **No blockers.** All 4 guest-bearing new lattices are now proven through the FULL CLI tab chain (Interface -> Solute -> Ion).
- **Existing regression unaffected:** `tests/test_e2e_custom_guest_cross_tab_cli.py` (44.1-20 CLI template), `tests/test_e2e_builtin_cross_tab_regression.py` (4 CLI), `tests/test_e2e_lattice_interface_cli.py` (6 CLI), `tests/test_e2e_sH_interface_export.py` (2 sH CLI), and `tests/test_e2e_lattice_cross_tab_gui.py` (45-04, 4 GUI) still pass alongside the new 4 CLI cross-tab tests -- no source code changed (test-only plan).

---
*Phase: 45-e2e-hydrate-tab-workflow*
*Completed: 2026-07-11*
