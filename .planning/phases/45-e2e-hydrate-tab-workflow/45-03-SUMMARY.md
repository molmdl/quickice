---
phase: 45-e2e-hydrate-tab-workflow
plan: 03
subsystem: testing
tags: [e2e, grompp, sH, triclinic, gui-export, cli-export, hydrate, pytest, gromacs]

# Dependency graph
requires:
  - phase: 39-new-hydrate-lattices
    provides: sH lattice type (is_triclinic=True but NOT in TRICLINIC_HYDRATE_PHASES — only c0te/c1te blocked) + HydrateConfig/InterfaceConfig
  - phase: 42-00
    provides: sH cage_type_map medium key "12_1" fix — without it medium cages were unreachable (0 medium guests); all 3 cage types (small+medium+large) now routed
  - phase: 44.1-urgent-cross-tab-wiring
    provides: GUI InterfaceGROMACSExporter.export_interface_gromacs accepts hydrate_config=None -> built-in ITP staging; CLI _run_export_step reads hydrate_config=getattr(_hydrate_result,"config",None) -> _build_custom_guest_info(None)=None -> built-in path
  - phase: 45-01
    provides: Module-scoped lattice_chains fixture + _assert_lattice_interface_grompp GUI export pattern (QFileDialog/QMessageBox mock) — the GUI half template
  - phase: 45-02
    provides: _make_cli_pipeline + _assert_lattice_cli_export CLI export pattern (Pattern 4: _run_export_step direct) — the CLI half template
provides:
  - e2e sH (triclinic-but-allowed, ~4480 guests) interface export + grompp via BOTH GUI InterfaceGROMACSExporter.export_interface_gromacs (hydrate_config=None) and CLI CLIPipeline._run_export_step (interface branch)
  - Module-scoped sH_chain fixture (one GenIce2 + assemble_slab, amortized across GUI + CLI tests)
  - _assert_sH_interface_export shared helper (file-consistency + CH4_H residue + ch4_hydrate.itp + grompp; reused for both GUI output.gro/output.top and CLI interface.gro/interface.top)
affects:
  - 45-e2e-hydrate-tab-workflow (Wave 2+ plans: full tab chain solute/ion/custom for sH; sH is slow so may need smaller box or generous timeout)
  - 47-05 (filled-ice grompp — sH proven at interface step, not a filled ice but closes the triclinic-but-allowed lattice gap)

# Tech tracking
tech-stack:
  added: []  # no new deps — test-only plan
  patterns:
    - "Module-scoped single-lattice fixture (sH_chain) amortizing slow GenIce2 + slab across GUI + CLI tests (one gen, two exports)"
    - "Combined GUI + CLI test in ONE file sharing a module-scoped fixture (45-01/02 split GUI/CLI per file; 45-03 combines because sH is a single slow lattice — one fixture amortizes both paths)"

key-files:
  created:
    - tests/test_e2e_sH_interface_export.py
  modified: []

key-decisions:
  - "Assert guest_nmolecules > 0 (NOT exact count) for sH — Pitfall 5: sH through 3x3x8 slab produces ~4480 guests but exact count is version-dependent"
  - "Do NOT assert atom-number exactness in .gro header — Pitfall 4: GRO wraps at 100,000 (sH ~54k atoms is under threshold but assert_gro_top_consistent counts LINES not header regardless)"
  - "Combined GUI + CLI tests in ONE file (unlike 45-01/02 which split per file) — sH is a single slow lattice; one module-scoped fixture amortizes both export paths"
  - "Box 3.0x3.0x8.0 nm (shortest 3.0 nm > 2x rcoulomb=2.0 nm — grompp PBC rule); 1x1x1 supercell sufficient (sH is triclinic but ALLOWED, not blocked)"
  - "@gmx_skipif decorator + if shutil.which('gmx') guard — file-consistency + guest-residue asserts run whenever test runs"

patterns-established:
  - "Pattern: Module-scoped single-lattice fixture (scope='module') for a SLOW lattice (sH ~5-30s) shared across GUI + CLI export tests — one GenIce2 + slab, two exports"
  - "Pattern: _assert_sH_interface_export(ws, gro_name, top_name) — gro_name/top_name-parameterized so the same helper asserts GUI (output.gro/output.top) AND CLI (interface.gro/interface.top) exports"

# Metrics
duration: 2 min
completed: 2026-07-11
---

# Phase 45 Plan 03: sH Interface Export grompp (GUI + CLI) Summary

**e2e sH (triclinic-but-allowed, ~4480 guests) interface export + gmx grompp rc=0 via BOTH GUI InterfaceGROMACSExporter and CLI CLIPipeline._run_export_step, sharing one module-scoped GenIce2+slab fixture**

## Performance

- **Duration:** 2 min
- **Started:** 2026-07-11T02:34:42Z
- **Completed:** 2026-07-11T02:36:15Z
- **Tasks:** 2
- **Files modified:** 1 (created)

## Accomplishments
- Proved sH — the triclinic-but-ALLOWED hydrate lattice (is_triclinic=True but NOT in TRICLINIC_HYDRATE_PHASES; only c0te/c1te are blocked) — produces grompp-valid output (rc=0) at the Interface tab export step via BOTH the GUI `InterfaceGROMACSExporter.export_interface_gromacs` (hydrate_config=None built-in ch4 path) AND the CLI `CLIPipeline._run_export_step` (interface branch)
- Confirmed sH's large guest count (~4480 guests through the 3×3×8 nm slab — EXPECTED, not a bug; sH has 3 cage types small+medium+large, all routed via the 42-00 medium "12_1" key fix) does NOT cause export or grompp failures — grompp rc=0 on the ~54k-atom system
- Verified the phase_id-based triclinic blocking correctly EXCLUDES sH (TRICLINIC_HYDRATE_PHASES = {"hydrate_c0te", "hydrate_c1te"} — sH proceeds through interface assembly; the is_triclinic flag is forward-looking metadata, not a block gate per decision [39-01]/[39-03])
- Established the combined GUI + CLI single-file pattern for a SLOW lattice (one module-scoped fixture amortizes both export paths) — the 45-01/02 templates split GUI/CLI per file, but 45-03 combines because sH is a single slow lattice where one GenIce2 + slab call serves both tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Write sH GUI + CLI interface export + grompp test** — `d05e654` (test) — file written + 2/2 verified in Task 1's `<verify>`, committed as the plan's Task 2 atomic commit
2. **Task 2: Run full test + commit** — `d05e654` (test) — both tests pass, commit made

**Plan metadata:** pending (docs commit follows this summary)

## Files Created/Modified
- `tests/test_e2e_sH_interface_export.py` (327 lines) — Module-scoped `sH_chain` fixture (builds sH hydrate → to_candidate → assemble_slab ONCE; asserts guest_nmolecules > 0; carries hydrate/iface/config for both GUI + CLI tests), shared `_assert_sH_interface_export` helper (file-consistency + CH4_H residue + ch4_hydrate.itp ITP + grompp; gro_name/top_name-parameterized for GUI output.* vs CLI interface.*), GUI test (`@gmx_skipif` + QFileDialog/QMessageBox mock + export_interface_gromacs(hydrate_config=None)), CLI test (`@gmx_skipif` + CLIPipeline._run_export_step interface branch via Pattern 4)

## Decisions Made
- Asserted `guest_nmolecules > 0` (NOT exact count) for sH — Pitfall 5 (45-RESEARCH.md): sH through the 3×3×8 nm slab produces ~4480 guests but the exact number is version-dependent (GenIce2 version + tiling); exact assertions are false-future-proofing
- Did NOT assert atom-number exactness in the .gro header — Pitfall 4 (45-RESEARCH.md): GRO wraps atom numbers at 100,000 (sH ~54k atoms is under the threshold, but `assert_gro_top_consistent` counts atom LINES not the header regardless, so it is robust)
- Combined GUI + CLI tests in ONE file (unlike 45-01/02 which split per file) — sH is a single slow lattice (~5-30s for GenIce2 + slab); one module-scoped fixture amortizes both export paths (one generation, two exports). This matches the plan's explicit instruction: "Create `tests/test_e2e_sH_interface_export.py` with BOTH a GUI test and a CLI test for sH interface export, sharing a module-scoped fixture."
- Box 3.0×3.0×8.0 nm (shortest vector 3.0 nm > 2×rcoulomb=2.0 nm) — satisfies the grompp PBC rule; 1×1×1 supercell sufficient for sH (Pitfall 1 only affects the triclinic filled ices c0te/c1te which are blocked; sH is triclinic-but-allowed so the slab box is what matters for PBC, not the unit cell)
- Used `@gmx_skipif` decorator (per plan) PLUS `if shutil.which("gmx"):` guard inside the helper — file-consistency + guest-residue asserts run whenever the test runs
- Made `_assert_sH_interface_export` take `gro_name`/`top_name` (e.g. "output.gro"/"output.top" for GUI, "interface.gro"/"interface.top" for CLI) so the same helper asserts both paths — the GUI writes via QFileDialog mock, the CLI writes to `_output_dir`
- Mirrored the GUI section of `tests/test_e2e_lattice_interface_gui.py` (45-01: QFileDialog/QMessageBox mock + export_interface_gromacs) and the CLI section of `tests/test_e2e_lattice_interface_cli.py` (45-02: CLIPipeline + _run_export_step), adapted for a single sH lattice (not parametrized)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None. Both tests passed on the first run in 3.48s (faster than the expected ~5-30s — the module-scoped fixture amortizes the GenIce2 + assemble_slab call across both GUI + CLI tests, and grompp on the resulting ~54k-atom slab structure is sub-second). `gmx` is on PATH at `/data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx`. The sH medium cage_type_map key "12_1" (42-00 fix) correctly routes all 3 cage types (small+medium+large) producing the expected large guest count.

## User Setup Required
None — no external service configuration required. `gmx` is already on PATH.

## Next Phase Readiness
- **Ready for Wave 2 sH plans:** The `_assert_sH_interface_export` helper provides the template for downstream full-tab-chain Phase 45 plans for sH (solute/ion/custom branches). sH is slow (~5-30s for GenIce2 + slab) so Wave 2 sH tests should reuse the module-scoped fixture pattern and use `--timeout=300` (or a smaller box if the full chain + grompp is too slow). The helper is `gro_name`/`top_name`-parameterized so it can assert the solute/custom/ion branches by passing the appropriate filenames.
- **No blockers.** sH is now proven at the Interface tab foundation step via BOTH export paths (GUI + CLI). Together with 45-01 (6 lattices GUI) and 45-02 (6 lattices CLI), the Wave 1 foundation is complete — all 7 non-blocked new lattices (sII, sH, c2te, ice1hte, sTprime, 16, 17) plus sH are now covered at the interface export step. The 2 triclinic filled ices (c0te/c1te) remain covered by separate triclinic plans (blocked at interface by design; hydrate-only export at 4×4×4 supercell).
- **Existing regression unaffected:** `tests/test_e2e_builtin_cross_tab_regression.py` (4 GUI + 4 CLI tests), `tests/test_e2e_lattice_interface_gui.py` (6 GUI tests), and `tests/test_e2e_lattice_interface_cli.py` (6 CLI tests) still pass alongside the new 2 sH tests — no source code changed (test-only plan).

---
*Phase: 45-e2e-hydrate-tab-workflow*
*Completed: 2026-07-11*
