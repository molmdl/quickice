---
phase: 45-e2e-hydrate-tab-workflow
plan: 02
subsystem: testing
tags: [e2e, grompp, cli-export, lattice-types, hydrate, pytest, gromacs]

# Dependency graph
requires:
  - phase: 39-new-hydrate-lattices
    provides: 7 new hydrate lattice types (c0te, c1te, c2te, ice1hte, sTprime, 16, 17) + HydrateConfig/InterfaceConfig
  - phase: 44.1-urgent-cross-tab-wiring
    provides: CLIPipeline._run_export_step reads hydrate_config=getattr(_hydrate_result,"config",None) -> _build_custom_guest_info(None)=None -> built-in path; copy_itp_files_for_structure stages ch4_hydrate.itp for built-in ch4 (byte-identical to pre-44.1)
  - phase: 45-01
    provides: Module-scoped lattice_chains fixture pattern + _assert_lattice_interface_grompp guest-vs-water-only branching (the GUI counterpart; this plan is the CLI half)
provides:
  - Parametrized e2e CLI interface export + grompp test proving 6 non-blocked new lattices (sII/c2te/ice1hte/sTprime/16/17) produce grompp-valid output via CLIPipeline._run_export_step interface branch (Pattern 4)
  - _make_cli_pipeline + _assert_lattice_cli_export shared helpers (reusable template for downstream CLI full-chain Phase 45 plans)
  - Module-scoped lattice_chains fixture (CLI mirror of 45-01's GUI fixture)
affects:
  - 45-e2e-hydrate-tab-workflow (Wave 2+ CLI plans: full tab chain solute/ion/custom for these 6 lattices via _run_export_step)
  - 47-05 (filled-ice grompp — c2te/ice1hte now also proven at CLI interface step)

# Tech tracking
tech-stack:
  added: []  # no new deps — test-only plan
  patterns:
    - "Pattern 4: _make_cli_pipeline(output_dir, hydrate, downstream_attr, downstream_struct) + _run_export_step() direct (no full execute())"
    - "Module-scoped parametrized cross-tab fixture (one GenIce2 chain per lattice, amortized across cases)"
    - "Guest vs water-only lattice classification branching in shared CLI assertion helper"

key-files:
  created:
    - tests/test_e2e_lattice_interface_cli.py
  modified: []

key-decisions:
  - "Assert guest count > 0 (NOT exact) for guest lattices — Pitfall 5: counts vary by lattice/version (mirrors 45-01)"
  - "Water-only lattices (sTprime, 17) assert SOL-only + NO guest residue (CH4_H/GUE absent) — generator's water-only skip drops cages (mirrors 45-01)"
  - "Box 3.0x3.0x8.0 nm (shortest 3.0 nm > 2x rcoulomb=2.0 nm — grompp PBC rule); 1x1x1 supercell sufficient for non-triclinic lattices"
  - "@gmx_skipif decorator + if shutil.which('gmx') guard — file-consistency + guest-residue asserts run whenever test runs"
  - "No QFileDialog/QMessageBox patching needed — CLI pipeline writes directly to _output_dir (unlike the GUI 45-01 path)"

patterns-established:
  - "Pattern: _make_cli_pipeline helper (CLIPipeline(args=SimpleNamespace()) + _output_dir + _hydrate_result + setattr(downstream_attr)) — copied from test_e2e_builtin_cross_tab_regression.py:373-385"
  - "Pattern: _assert_lattice_cli_export(ws, step_name, lattice_type, chain) — step_name-parameterized so it can be reused for solute/custom/ion branches in later CLI plans"
  - "Pattern: CLI interface branch test = _make_cli_pipeline + _run_export_step() assert rc==0 + _assert_lattice_cli_export (no QFileDialog mock)"

# Metrics
duration: 8 min
completed: 2026-07-11
---

# Phase 45 Plan 02: CLI Interface Export grompp for 6 New Lattices Summary

**Parametrized CLI interface export + gmx grompp rc=0 for 6 non-blocked new lattice types (sII/c2te/ice1hte/sTprime/16/17) via CLIPipeline._run_export_step (Pattern 4: _make_cli_pipeline + direct _run_export_step call)**

## Performance

- **Duration:** 8 min
- **Started:** 2026-07-11T02:25:15Z
- **Completed:** 2026-07-11T02:33:21Z
- **Tasks:** 2
- **Files modified:** 1 (created)

## Accomplishments
- Proved all 6 non-blocked new lattice types from Phase 39 produce grompp-valid output (rc=0) at the CLI Interface tab export step via `CLIPipeline._run_export_step` (the interface branch) — closing the CLI new-lattice coverage gap (all prior CLI cross-tab e2e tests used sI only)
- Guest lattices (sII, c2te, ice1hte, 16) stage the built-in `ch4_hydrate.itp` via `copy_itp_files_for_structure` and emit `CH4_H` residue in both `.top [molecules]` and `.gro` residues (count > 0, not exact — Pitfall 5) — `_build_custom_guest_info(config)` returns `None` for built-in ch4 → built-in path byte-identical to pre-44.1
- Water-only lattices (sTprime, 17) correctly emit SOL-only output with NO guest residue (no `CH4_H`, no `GUE`) via the CLI path — the generator's water-only skip drops cages, and the config-driven ITP staging stages nothing
- Established the `_make_cli_pipeline` + `_assert_lattice_cli_export` helper pair as the reusable CLI template for downstream Phase 45 CLI plans (solute/ion/custom branches), mirroring the 45-01 GUI helper pair

## Task Commits

Each task was committed atomically:

1. **Task 1: Write parametrized CLI interface export + grompp test for 6 new lattices** — `46568db` (test) — file written + 6/6 verified in Task 1's `<verify>`, committed as the plan's Task 2 atomic commit
2. **Task 2: Run full test + commit** — `46568db` (test) — all 6 parametrized cases pass, commit made

**Plan metadata:** pending (docs commit follows this summary)

## Files Created/Modified
- `tests/test_e2e_lattice_interface_cli.py` (349 lines) — Module-scoped `lattice_chains` fixture (builds hydrate→assemble_slab for 6 lattices; CLI mirror of 45-01's fixture), `_make_cli_pipeline` helper (Pattern 4: CLIPipeline + _output_dir + _hydrate_result + setattr), shared `_assert_lattice_cli_export` helper (guest vs water-only branching + file-consistency + grompp; step_name-parameterized for reuse), parametrized `@gmx_skipif` test exercising `CLIPipeline._run_export_step` interface branch (no QFileDialog mock needed — CLI writes directly to _output_dir)

## Decisions Made
- Asserted guest count `> 0` (NOT exact) for guest lattices — Pitfall 5 (45-RESEARCH.md): counts vary by lattice/version; exact assertions are false-future-proofing (mirrors 45-01)
- Water-only lattices assert SOL-only with no guest residue — matches the generator's water-only cage-skip behavior (mirrors 45-01)
- Box 3.0×3.0×8.0 nm (shortest vector 3.0 nm > 2×rcoulomb=2.0 nm) — satisfies the grompp PBC rule; 1×1×1 supercell sufficient for these 6 non-triclinic lattices (Pitfall 1 only affects the triclinic filled ices c0te/c1te, which are blocked and covered by separate plans)
- Used `@gmx_skipif` decorator (per plan) PLUS `if shutil.which("gmx"):` guard inside the helper — file-consistency + guest-residue asserts run whenever the test runs
- Made `_assert_lattice_cli_export` take `step_name` (e.g. "interface") so it can be reused for the solute/custom/ion CLI branches in later Phase 45 plans (the CLI writes `{step_name}.gro`/`{step_name}.top`, unlike the GUI which writes `output.gro`/`output.top` via QFileDialog)
- Mirrored the CLI section of `tests/test_e2e_builtin_cross_tab_regression.py` (lines 370-448: `_make_cli_pipeline` + `_run_export_step` per branch), swapping sI → parametrized 6 lattices per the plan
- No `QFileDialog`/`QMessageBox` patching (CLI writes directly to `_output_dir` — unlike the GUI 45-01 path which requires the inline patch under `QT_QPA_PLATFORM=offscreen`)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None. All 6 parametrized cases passed on the first run (including gmx grompp rc=0). Total runtime 1.08s for 6 GenIce2 + 6 grompp calls — the module-scoped fixture amortizes the GenIce2 + assemble_slab across all 6 cases, and grompp on the resulting slab structures is sub-second. `gmx` is on PATH at `/data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx`.

## User Setup Required
None — no external service configuration required. `gmx` is already on PATH.

## Next Phase Readiness
- **Ready for Wave 2 CLI plans:** The `_make_cli_pipeline` + `_assert_lattice_cli_export` helper pair provide the template for downstream full-tab-chain Phase 45 CLI plans (solute/ion/custom branches for these 6 lattices). The `_assert_lattice_cli_export` helper is `step_name`-parameterized so the same helper can assert the solute/custom/ion branches by passing `step_name="solute"` etc. — only the `_make_cli_pipeline` downstream_attr + structure need to change.
- **No blockers.** All 6 new lattices proven at the CLI Interface tab foundation step. Together with 45-01 (GUI half), the Wave 1 foundation is complete — both export paths (GUI `InterfaceGROMACSExporter` + CLI `_run_export_step` interface branch) are now covered for the 6 non-blocked new lattices. The 2 triclinic filled ices (c0te/c1te) remain covered by separate triclinic plans (blocked at interface by design; hydrate-only export at 4×4×4 supercell).
- **Existing regression unaffected:** `tests/test_e2e_builtin_cross_tab_regression.py` (4 CLI tests) and `tests/test_e2e_lattice_interface_gui.py` (6 GUI tests) still pass alongside the new 6 CLI tests — no source code changed (test-only plan).

---
*Phase: 45-e2e-hydrate-tab-workflow*
*Completed: 2026-07-11*
