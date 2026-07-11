---
phase: 45-e2e-hydrate-tab-workflow
plan: 12
subsystem: cli
tags: [argparse, depol, hydrate, cli-flag, depolarization, hydrate-config]

# Dependency graph
requires:
  - phase: 43-01
    provides: HydrateConfig.depol_mode dataclass field (default "strict"), __post_init__ validation (strict/optimal only), hydrate_generator._run_via_api threading to GenIce2 generate_ice(depol=...)
  - phase: 42-07
    provides: --cage-guest CLI flag pattern in hydrate_group, tests/test_cli/ directory (pytest rootdir mode, no __init__.py)
provides:
  - "--depol CLI flag (strict/optimal, default strict) in parser.py hydrate_group"
  - "depol_mode threading from args.depol to HydrateConfig in pipeline.py _run_source_step"
  - "tests/test_cli/test_depol_flag.py (3 tests: arg parse default, arg parse optimal/strict, config threading)"
affects: [cli-flag-completeness, e2e-hydrate-workflow, cli-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "getattr(self.args, 'flag', default) for backward-compat arg threading (old SimpleNamespaces without the attr default safely)"
    - "argparse choices=['strict','optimal'] as first-line gate; HydrateConfig.__post_init__ as second-line gate (defense in depth)"

key-files:
  created:
    - tests/test_cli/test_depol_flag.py
  modified:
    - quickice/cli/parser.py
    - quickice/cli/pipeline.py

key-decisions:
  - "getattr(self.args, 'depol', 'strict') mirrors the existing getattr pattern for all other args in the HydrateConfig constructor — backward compat with old SimpleNamespaces (e.g. test helpers) that lack the depol attr"
  - "argparse choices=['strict','optimal'] provides double safety: rejects invalid values BEFORE they reach HydrateConfig.__post_init__ (which ALSO validates per 43-01)"
  - "DO NOT assert strict != optimal output in tests (Pitfall 1: GenIce2 2.2.13.1 produces IDENTICAL output for both modes — Stage34E branches only on 'none' vs anything-else; both set dipoleOptimizationCycles=1000). Only assert the config FIELD is threaded correctly."
  - "Default 'strict' preserves byte-identical pre-change behavior: every existing HydrateConfig(...) call site that omits depol_mode inherits 'strict' (43-01 dataclass default); the CLI now matches."

patterns-established:
  - "CLI flag threading uses getattr(self.args, 'flag', default) for backward compat with test SimpleNamespaces missing the attr"

# Metrics
duration: ~1 min (97s)
completed: 2026-07-11
---

# Phase 45 Plan 12: --depol CLI Flag Summary

**Add `--depol` CLI flag (strict/optimal, default strict) threading depol_mode from args to HydrateConfig in `_run_source_step`, closing CLI-03 — the only CLI flag missing**

## Performance

- **Duration:** ~1 min (97s)
- **Started:** 2026-07-11T09:53:55Z
- **Completed:** 2026-07-11T09:55:32Z
- **Tasks:** 3
- **Files modified:** 3 (2 source + 1 test)

## Accomplishments
- Added `--depol` argparse flag to the `hydrate_group` in parser.py (choices=["strict", "optimal"], default="strict") — the ONLY CLI flag that was missing (CLI-03 / 45-02a gap)
- Threaded `depol_mode=getattr(self.args, 'depol', 'strict')` to the `HydrateConfig(...)` constructor in `pipeline.py::_run_source_step` — mirrors the existing `getattr` pattern for all other args (backward compat with test SimpleNamespaces)
- Created `tests/test_cli/test_depol_flag.py` with 3 tests covering arg-parse default, arg-parse optimal/strict choices, and config threading through `_run_source_step` (with GenIce2 generation)
- No regression: 16/16 tests in `tests/test_cli/` pass + 2/2 `TestDepolModePassthrough` (43-01) pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add --depol flag to parser.py + thread to HydrateConfig in pipeline.py** - `8fb4149` (feat)
2. **Task 2: Write test_cli/test_depol_flag.py** - `6de2bb3` (test)
3. **Task 3: Run new tests + regression check + commit** - (verification only; commits done in Task 1 & 2)

**Plan metadata:** `docs(45-12)` (docs: complete plan — to be committed below)

## Files Created/Modified
- `quickice/cli/parser.py` - Added `--depol` argument to `hydrate_group` (after `--cage-guest`, before `custom_group`); choices=["strict","optimal"], default="strict"
- `quickice/cli/pipeline.py` - Added `depol_mode=getattr(self.args, 'depol', 'strict')` as the last kwarg to the `HydrateConfig(...)` constructor in `_run_source_step`
- `tests/test_cli/test_depol_flag.py` - 3 tests: arg-parse default (strict), arg-parse optimal/strict choices, config threading via `_run_source_step` (131 lines)

## Decisions Made
- **Used `getattr(self.args, 'depol', 'strict')` (not `self.args.depol`)** for backward compat: if an old `SimpleNamespace` without `depol` is passed (e.g. from test helpers), it defaults to "strict". This mirrors the existing `getattr` pattern used for ALL other args in this constructor (guest, supercell_x/y/z, cage_occupancy_small/large).
- **Did NOT change `HydrateConfig.__post_init__`** — it already validates `depol_mode in ("strict", "optimal")` (43-01, types.py:586). The argparse `choices` is a first-line gate; `__post_init__` is the second-line gate (defense in depth).
- **Did NOT change `hydrate_generator._run_via_api`** — it already passes `config.depol_mode` to GenIce2 `generate_ice(depol=...)` (43-01, line 317).
- **Did NOT add `--custom-guest`/`--custom-guest-itp` flags** — these are DEFERRED BY DESIGN (pipeline.py:73-81, CLI surface is built-in-only for v4.7). Only `--depol` is in scope.
- **Did NOT assert strict != optimal output** in tests (Pitfall 1 from 45-RESEARCH.md: GenIce2 2.2.13.1 produces identical output for both modes). Tests assert only the config FIELD is threaded correctly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added required --temperature/--pressure to test parse_args calls**
- **Found during:** Task 2 (writing test_depol_flag.py)
- **Issue:** The plan's test snippets for `test_depol_arg_parse_defaults_to_strict` and `test_depol_arg_parse_accepts_optimal` used `p.parse_args(['--hydrate'])` and `p.parse_args(['--hydrate', '--depol', 'optimal'])`, but `create_parser()` declares `--temperature`/`-T` and `--pressure`/`-P` as `required=True`. Calling `parse_args` without them raises `SystemExit` ("the following arguments are required: --temperature/-T, --pressure/-P"), so the tests as written would fail to even reach the `assert a.depol` line.
- **Fix:** Added `["--temperature", "270", "--pressure", "1"]` to the `parse_args` calls in both arg-parse tests. The values are arbitrary valid inputs (270 K, 1 MPa) — they satisfy the `validate_temperature`/`validate_pressure` validators and are unrelated to `--depol` behavior.
- **Files modified:** tests/test_cli/test_depol_flag.py
- **Verification:** All 3 tests pass (`python -m pytest tests/test_cli/test_depol_flag.py -v` → 3 passed in 0.34s)
- **Committed in:** `6de2bb3` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The fix was necessary for the tests to run at all (the plan's snippets would raise SystemExit). No scope creep — the fix only adds the argparse-required positional args the plan omitted; the `--depol` assertions are unchanged.

## Issues Encountered
None — the source change is purely additive (default "strict" = byte-identical pre-change behavior), GenIce2 sI 1×1×1 generation is fast (~0.3s), and all regression tests pass on the first run.

## User Setup Required
None - no external service configuration required. The `--depol` flag uses the existing GenIce2 dependency (already in `environment.yml`); no new packages.

## Next Phase Readiness
- CLI-03 is CLOSED: `--depol` is the only CLI flag that was missing (per 45-RESEARCH.md CLI Flag Gaps table). All hydrate-relevant CLI flags are now present (`--hydrate`, `--lattice-type` (all 10), `--guest`, `--cage-guest`, `--supercell-x/y/z`, `--depol`). `--custom-guest`/`--custom-guest-itp` (cage guest) remain deferred BY DESIGN (pipeline.py:73-81).
- The CLI now matches the GUI's depol combo (hydrate_panel.py:218, strict/optimal) — full GUI/CLI feature parity for depol mode.
- Plans 45-13 and 45-14 remain in this phase (test-only plans, per the phase design).
- No blockers or concerns for downstream plans.

---
*Phase: 45-e2e-hydrate-tab-workflow*
*Completed: 2026-07-11*
