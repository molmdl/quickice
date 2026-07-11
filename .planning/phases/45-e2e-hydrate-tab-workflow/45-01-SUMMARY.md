---
phase: 45-e2e-hydrate-tab-workflow
plan: 01
subsystem: testing
tags: [e2e, grompp, gui-export, lattice-types, hydrate, pytest, gromacs]

# Dependency graph
requires:
  - phase: 39-new-hydrate-lattices
    provides: 7 new hydrate lattice types (c0te, c1te, c2te, ice1hte, sTprime, 16, 17) + HydrateConfig/InterfaceConfig
  - phase: 44.1-urgent-cross-tab-wiring
    provides: InterfaceGROMACSExporter.export_interface_gromacs(hydrate_config=None) config-driven ITP staging + _stage_hydrate_guest_itps helper (built-in path byte-identical to pre-44.1)
provides:
  - Parametrized e2e GUI interface export + grompp test proving 6 non-blocked new lattices (sII/c2te/ice1hte/sTprime/16/17) produce grompp-valid output at the Interface tab
  - Module-scoped lattice_chains fixture (reusable template for downstream full-chain Phase 45 plans)
  - _assert_lattice_interface_grompp shared helper (guest vs water-only branching)
affects:
  - 45-e2e-hydrate-tab-workflow (Wave 2+ plans: full tab chain solute/ion/custom for these 6 lattices)
  - 47-05 (filled-ice grompp — c2te/ice1hte now proven at interface step)

# Tech tracking
tech-stack:
  added: []  # no new deps — test-only plan
  patterns:
    - "Module-scoped parametrized cross-tab fixture (one GenIce2 chain per lattice, amortized across cases)"
    - "Guest vs water-only lattice classification branching in shared assertion helper"
    - "QFileDialog + QMessageBox inline patch under QT_QPA_PLATFORM=offscreen (Pattern 3)"

key-files:
  created:
    - tests/test_e2e_lattice_interface_gui.py
  modified: []

key-decisions:
  - "Assert guest count > 0 (NOT exact) for guest lattices — Pitfall 5: counts vary by lattice/version"
  - "Water-only lattices (sTprime, 17) assert SOL-only + NO guest residue (CH4_H/GUE absent) — generator's water-only skip drops cages"
  - "Box 3.0x3.0x8.0 nm (shortest 3.0 nm > 2x rcoulomb=2.0 nm — grompp PBC rule); 1x1x1 supercell sufficient for non-triclinic lattices"
  - "@gmx_skipif decorator + if shutil.which('gmx') guard — file-consistency + guest-residue asserts run whenever test runs"

patterns-established:
  - "Pattern: module-scoped fixture keyed by lattice_type dict, parametrized test indexes by lattice_type"
  - "Pattern: _assert_lattice_interface_grompp helper branches on frozenset lattice classification (WITH_GUESTS / WATER_ONLY)"

# Metrics
duration: 4 min
completed: 2026-07-11
---

# Phase 45 Plan 01: GUI Interface Export grompp for 6 New Lattices Summary

**Parametrized GUI interface export + gmx grompp rc=0 for 6 non-blocked new lattice types (sII/c2te/ice1hte/sTprime/16/17) via InterfaceGROMACSExporter with hydrate_config=None**

## Performance

- **Duration:** 4 min
- **Started:** 2026-07-11T02:19:40Z
- **Completed:** 2026-07-11T02:24:14Z
- **Tasks:** 2
- **Files modified:** 1 (created)

## Accomplishments
- Proved all 6 non-blocked new lattice types from Phase 39 produce grompp-valid output (rc=0) at the GUI Interface tab export step — closing the new-lattice coverage gap (all prior cross-tab e2e tests used sI only)
- Guest lattices (sII, c2te, ice1hte, 16) stage the built-in `ch4_hydrate.itp` and emit `CH4_H` residue in both `.top [molecules]` and `.gro` residues (count > 0, not exact — Pitfall 5)
- Water-only lattices (sTprime, 17) correctly emit SOL-only output with NO guest residue (no `CH4_H`, no `GUE`) — the generator's water-only skip drops cages, and the config-driven ITP staging helper stages nothing
- Module-scoped fixture amortizes GenIce2 + assemble_slab across all 6 parametrized cases (per AGENTS.md testing guidance)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write parametrized GUI interface export + grompp test** — `c29799f` (test) — file written + verified in Task 1's `<verify>`, committed as the plan's Task 2 atomic commit
2. **Task 2: Run full test file + regression check + commit** — `c29799f` (test) — both test files green, commit made

**Plan metadata:** pending (docs commit follows this summary)

## Files Created/Modified
- `tests/test_e2e_lattice_interface_gui.py` (291 lines) — Module-scoped `lattice_chains` fixture (builds hydrate→assemble_slab for 6 lattices), shared `_assert_lattice_interface_grompp` helper (guest vs water-only branching + file-consistency + grompp), parametrized `@gmx_skipif` test exercising `InterfaceGROMACSExporter.export_interface_gromacs(iface, hydrate_config=None)` via QFileDialog + QMessageBox inline patch

## Decisions Made
- Asserted guest count `> 0` (NOT exact) for guest lattices — Pitfall 5 (45-RESEARCH.md): counts vary by lattice/version; exact assertions are false-future-proofing
- Water-only lattices assert SOL-only with no guest residue — matches the generator's water-only cage-skip behavior
- Box 3.0×3.0×8.0 nm (shortest vector 3.0 nm > 2×rcoulomb=2.0 nm) — satisfies the grompp PBC rule; 1×1×1 supercell sufficient for these 6 non-triclinic lattices (Pitfall 1 only affects the triclinic filled ices c0te/c1te, which are blocked and covered by separate plans)
- Used `@gmx_skipif` decorator (per plan) PLUS `if shutil.which("gmx"):` guard inside the helper — file-consistency + guest-residue asserts run whenever the test runs; matches the `test_e2e_custom_guest_cross_tab_gui.py` pattern
- Mirrored the GUI section of `tests/test_e2e_builtin_cross_tab_regression.py` (lines 86-302), swapping sI → parametrized 6 lattices per the plan

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None. All 6 parametrized cases passed on the first run (including gmx grompp rc=0). The 1.68s total runtime for 6 GenIce2 + 6 grompp calls was confirmed legitimate — GenIce2 for these small 1×1×1 supercells is ~0.03s each (the research's "~1-5s" estimate was conservative for larger systems), and grompp on the resulting slab structures is sub-second.

## User Setup Required
None — no external service configuration required. `gmx` is already on PATH at `/data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx`.

## Next Phase Readiness
- **Ready for Wave 2:** The `lattice_chains` module-scoped fixture + `_assert_lattice_interface_grompp` helper provide the template for downstream full-tab-chain Phase 45 plans (solute/ion/custom tabs for these 6 lattices). The fixture can be extended to also build solute/ion/custom structures per lattice.
- **No blockers.** All 6 new lattices proven at the Interface tab foundation step. The 2 triclinic filled ices (c0te/c1te) remain covered by separate triclinic plans (blocked at interface by design; hydrate-only export at 4×4×4 supercell).
- **Existing regression unaffected:** `tests/test_e2e_builtin_cross_tab_regression.py` (4 tests) still passes alongside the new 6 — no source code changed (test-only plan).

---
*Phase: 45-e2e-hydrate-tab-workflow*
*Completed: 2026-07-11*
