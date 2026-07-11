---
phase: 45-e2e-hydrate-tab-workflow
plan: 04
subsystem: testing
tags: [e2e, grompp, gui-export, cross-tab, sII, c2te, ice1hte, 16, hydrate, pytest, gromacs]

# Dependency graph
requires:
  - phase: 39-new-hydrate-lattices
    provides: 4 new guest-bearing lattice types (sII, c2te, ice1hte, 16) + HydrateConfig/InterfaceConfig/CustomMoleculeConfig
  - phase: 44.1-urgent-cross-tab-wiring
    provides: All 4 GUI exporters (Interface/Solute/CustomMolecule/Ion GROMACSExporter) accept hydrate_config=None param -> _stage_hydrate_guest_itps built-in path stages ch4_hydrate.itp + threads custom_guest_info=None to the GRO/TOP writers
  - phase: 45-01
    provides: Module-scoped lattice_chains fixture + _assert_lattice_interface_grompp GUI export pattern (QFileDialog/QMessageBox mock + @gmx_skipif) -- the GUI half template this plan extends to the full cross-tab chain
  - phase: 44.1-22
    provides: test_e2e_builtin_cross_tab_regression.py -- the 4-exporter GUI cross-tab template (lines 86-367) this plan MIRRORS, swapping the 2-guest parametrization -> 4-lattice parametrization
provides:
  - Parametrized full GUI cross-tab (4 exporters: Interface/Solute/CustomMolecule/Ion) + grompp e2e test for the 4 new guest-bearing lattices (sII/c2te/ice1hte/16) with built-in guest_type="ch4" and hydrate_config=None
  - Module-scoped lattice_chains fixture amortizing GenIce2 + 4x fresh assemble_slab (Pattern 2) + 3 inserters across all parametrized export cases
  - _assert_lattice_export shared helper (CH4_H residue + ch4_hydrate.itp + no GUE/MOL_H leak + file-consistency + grompp) reused across all 4 GUI exporters
affects:
  - 45-e2e-hydrate-tab-workflow (Wave 2 CLI counterpart 45-05: parametrized 4-lattice CLI cross-tab; water-only 45-07: sTprime/17 through full chain)
  - 47-05 (filled-ice grompp -- c2te/ice1hte now proven through the FULL GUI tab chain, not just the interface step)

# Tech tracking
tech-stack:
  added: []  # no new deps -- test-only plan
  patterns:
    - "Pattern 2 (fresh assemble_slab per inserter) at module-fixture scale: 4 fresh slabs per lattice (iface/iface_solute/iface_custom/iface_ion) so the ion inserter's mutation of iface.molecule_index does NOT cross-contaminate the solute/custom exporters' interface references"
    - "Module-scoped lattice_chains fixture building the FULL chain (hydrate -> 4x fresh slab -> 3 inserters) ONCE per 4 lattices, amortizing GenIce2 (~1-5s each) across all 4 parametrized 4-exporter test cases"
    - "RENAMED cmet.gro/cmet.itp (moleculetype etoh -> MOL) shared across all 4 lattices -- the LIQUID custom molecule for the Custom Molecule tab, NOT the cage guest; avoids pre-existing .gro/.top moleculetype name mismatch (copied from 44.1-22 template lines 109-124)"

key-files:
  created:
    - tests/test_e2e_lattice_cross_tab_gui.py
  modified: []

key-decisions:
  - "Fresh assemble_slab per inserter (Pattern 2) -- 4 slabs per lattice (iface/iface_solute/iface_custom/iface_ion) because the ion inserter mutates iface.molecule_index (ion_inserter.py:259); deterministic with seed=42 so all 4 are byte-identical until an inserter mutates its own copy"
  - "hydrate_config=None -> built-in path (stages ch4_hydrate.itp, references CH4_H); all 4 lattices use built-in guest_type=ch4"
  - "Do NOT assert exact guest/solute/ion counts -- assert > 0 only (Pitfall 5: counts vary by lattice/version)"
  - "Do NOT assert atom-number exactness in .gro header (Pitfall 4: GRO wraps at 100,000; assert_gro_top_consistent counts LINES not header, so it is robust)"
  - "Assert GUE/MOL_H NOT in mols/residues to guard against the custom-guest/fallback path leaking into the built-in path"
  - "RENAMED cmet shared across all 4 lattices (module-level temp dir) -- it is the LIQUID custom molecule for the Custom Molecule tab, not the cage guest; ch4_hydrate.itp (cage) and cmet.itp (liquid) do not collide"
  - "Water-only lattices (sTprime, 17) excluded here (no guests for solute/ion context) -- covered by 45-07"

patterns-established:
  - "Pattern: Module-scoped lattice_chains fixture with Pattern 2 (fresh slab per inserter) for the FULL cross-tab chain (4 GUI exporters) -- extends the 45-01 single-exporter interface pattern to solute/custom/ion"
  - "Pattern: _assert_lattice_export(ws, gro_name, top_name, lattice_type) -- gro_name/top_name-parameterized shared helper asserting built-in ch4 path (CH4_H + ch4_hydrate.itp + no GUE/MOL_H leak + file-consistency + grompp) for all 4 GUI exporters"

# Metrics
duration: 1 min
completed: 2026-07-11
---

# Phase 45 Plan 04: GUI Full Cross-Tab grompp for 4 New Lattices Summary

**Parametrized full GUI cross-tab (Interface->Solute->Custom->Ion) + gmx grompp rc=0 for 4 new guest lattices (sII/c2te/ice1hte/16) with built-in ch4, fresh slab per inserter (Pattern 2)**

## Performance

- **Duration:** 1 min (52 sec)
- **Started:** 2026-07-11T02:37:50Z
- **Completed:** 2026-07-11T02:38:42Z
- **Tasks:** 2
- **Files modified:** 1 (created)

## Accomplishments
- Proved the 4 new guest-bearing lattice types from Phase 39 (sII, c2te, ice1hte, 16) pass `gmx grompp` (rc=0) through the FULL GUI cross-tab chain: Interface -> Solute -> Custom Molecule -> Ion -> Export (all 4 GUI exporters) with `hydrate_config=None` (the built-in ch4 path)
- Extended Wave 1's interface-only foundation (45-01 GUI / 45-02 CLI / 45-03 sH) to the FULL downstream chain -- proving the new lattice structures survive solute insertion, custom molecule insertion, AND ion insertion, producing grompp-valid output at each export step (4 exporters x 4 lattices = 16 export+grompp assertions)
- Applied Pattern 2 (fresh `assemble_slab` per inserter) at module-fixture scale: 4 fresh slabs per lattice (iface/iface_solute/iface_custom/iface_ion) so the ion inserter's mutation of `iface.molecule_index` (`ion_inserter.py:259`) does NOT cross-contaminate the solute/custom exporters' interface references
- Confirmed the built-in path (hydrate_config=None) correctly stages `ch4_hydrate.itp` and references `CH4_H` (NOT `GUE` or `MOL_H`) at every export step for all 4 lattices -- no custom-guest/fallback path leak

## Task Commits

Each task was committed atomically:

1. **Task 1: Write parametrized GUI full cross-tab (4 exporters) + grompp for 4 lattices** -- `bdf4af9` (test) -- file written + 4/4 verified in Task 1's `<verify>` (4.78s)
2. **Task 2: Run full test + commit** -- `bdf4af9` (test) -- both tasks share the single atomic test commit (plan specifies one commit message for the test file)

**Plan metadata:** pending (docs commit follows this summary)

## Files Created/Modified
- `tests/test_e2e_lattice_cross_tab_gui.py` (494 lines) -- Module-scoped `lattice_chains` fixture (builds hydrate -> 4x fresh `assemble_slab` per lattice + 3 inserters ONCE for all 4 lattices; asserts `guest_nmolecules > 0` on each slab; RENAMED cmet.gro/cmet.itp shared across lattices for the Custom Molecule tab), shared `_assert_lattice_export` helper (CH4_H residue + ch4_hydrate.itp ITP + no GUE/MOL_H leak + assert_itp_completeness + assert_gro_top_consistent + grompp rc=0), parametrized `@gmx_skipif` test exercising all 4 GUI exporters (Interface/Solute/CustomMolecule/Ion GROMACSExporter with hydrate_config=None + QFileDialog/QMessageBox mock) for sII/c2te/ice1hte/16 with per-exporter ITP checks (ch4_liquid.itp / cmet.itp / ion.itp)

## Decisions Made
- Applied Pattern 2 (fresh `assemble_slab` per inserter) with 4 slabs per lattice (iface/iface_solute/iface_custom/iface_ion) -- the ion inserter mutates `iface.molecule_index` in-place (`ion_inserter.py:259`), so each inserter gets its OWN fresh slab (deterministic with `seed=42`) to prevent cross-contamination. Mirrors `test_e2e_custom_guest_cross_tab_gui.py:120-139`.
- Used `hydrate_config=None` (built-in path) for all 4 lattices -> `_stage_hydrate_guest_itps` copies the bundled `ch4_hydrate.itp` and the writers reference `CH4_H`. All 4 lattices use built-in `guest_type="ch4"`.
- Did NOT assert exact guest/solute/ion counts -- asserted `> 0` only (Pitfall 5: counts vary by lattice/version; the c2te filled ice produces ~2048 guests at 1x1x1 interface while sII/16 produce fewer).
- Did NOT assert atom-number exactness in the .gro header (Pitfall 4: GRO wraps atom numbers at 100,000; `assert_gro_top_consistent` counts atom LINES not the header, so it is robust).
- Asserted `GUE`/`MOL_H` NOT in mols/residues at every export step to guard against the custom-guest/fallback path leaking into the built-in path (mirrors the 44.1-22 template's regression guard).
- Built the RENAMED cmet.gro/cmet.itp (moleculetype `etoh` -> `MOL`) ONCE at module level (shared across all 4 lattices) -- it is the LIQUID custom molecule for the Custom Molecule tab, NOT the cage guest; `ch4_hydrate.itp` (cage) and `cmet.itp` (liquid) do not collide. Copied the rename logic verbatim from `test_e2e_builtin_cross_tab_regression.py:109-124`.
- Excluded water-only lattices (sTprime, 17) from this plan -- they have no cage guests for the solute/ion context; they are covered by 45-07.
- Box 3.0x3.0x8.0 nm (shortest vector 3.0 nm > 2x rcoulomb=2.0 nm -- grompp PBC rule); 1x1x1 supercell sufficient for these 4 non-triclinic guest lattices (Pitfall 1 only affects the triclinic filled ices c0te/c1te, which are blocked).

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered
None. All 4 parametrized cases passed on the first run in 4.78s (4.80s on the final verification run). `gmx` is on PATH at `/data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx`. The module-scoped fixture amortizes GenIce2 + 4x `assemble_slab` + 3 inserters across all 4 parametrized cases; grompp on each resulting structure is sub-second. No source code was modified (test-only plan per the plan's explicit constraint).

## User Setup Required
None -- no external service configuration required. `gmx` is already on PATH; `QT_QPA_PLATFORM=offscreen` is set for the headless GUI exporter tests.

## Next Phase Readiness
- **Ready for Wave 2 CLI counterpart (45-05):** The CLI full cross-tab test (`test_e2e_lattice_cross_tab_cli.py`) mirrors this plan for the CLI export branches (`_run_export_step` interface/solute/custom/ion) using Pattern 4 (`_make_cli_pipeline` + `_run_export_step` direct). The `_assert_lattice_export` helper's gro_name/top_name-parameterized design (learned from 45-03) allows the same assertion shape for CLI `{step_name}.gro`/`{step_name}.top` filenames.
- **Ready for water-only full-chain (45-07):** sTprime/17 are excluded here (no cage guests for solute/ion). 45-07 must verify the solute/ion inserters don't IndexError on `guest_nmolecules=0` (Pitfall 3 -- risk area, UNVERIFIED).
- **No blockers.** All 4 guest-bearing new lattices are now proven through the FULL GUI tab chain (Interface -> Solute -> Custom -> Ion). Together with 45-01 (6 lattices GUI interface) / 45-02 (6 lattices CLI interface) / 45-03 (sH GUI+CLI interface), the new-lattice GUI coverage extends from the interface step to the full cross-tab chain for guest lattices.
- **Existing regression unaffected:** `tests/test_e2e_builtin_cross_tab_regression.py` (4 GUI + 4 CLI), `tests/test_e2e_lattice_interface_gui.py` (6 GUI), `tests/test_e2e_lattice_interface_cli.py` (6 CLI), and `tests/test_e2e_sH_interface_export.py` (2 sH) still pass alongside the new 4 GUI cross-tab tests -- no source code changed (test-only plan).

---
*Phase: 45-e2e-hydrate-tab-workflow*
*Completed: 2026-07-11*
