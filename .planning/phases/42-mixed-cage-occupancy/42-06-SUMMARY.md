---
phase: 42-mixed-cage-occupancy
plan: 06
subsystem: ui
tags: [gui, pyside6, hydrate, mixed-occupancy, cage-guest, qcombobox, qdoublespinbox, qformlayout, hydrate-panel]

# Dependency graph
requires:
  - phase: 42-01
    provides: "CageGuestAssignment dataclass + HydrateConfig.cage_guest_assignments dict[str, CageGuestAssignment] + __post_init__ legacy shim (empty -> synthesize small/large from guest_type) + explicit-API auto-populate built-in metadata per-assignment (guest_atom_labels/guest_atom_count from GUEST_MOLECULES) — single source of truth"
  - phase: 42-04
    provides: "render_hydrate_structure returns variable-length list[water, *guest_actors]; hydrate_viewer._guest_actors = _hydrate_actors[1:] so per-type guest actors render without [1] hard-indexing"
  - phase: 42-05
    provides: "HydrateGROMACSExporter.export_hydrate iterates config.cage_guest_assignments (downstream consumer of the GUI's get_configuration output); mixed CH4+ethanol grompp e2e (MIXED-04 GUI path closed)"
provides:
  - "Per-cage-type guest+occupancy rows in HydratePanel (one QComboBox + QDoubleSpinBox per cage_type_map key), rebuilt on lattice change (sI=2, sH=3, filled ice=1, water-only=0)"
  - "get_configuration builds HydrateConfig.cage_guest_assignments from the per-cage rows (CageGuestAssignment with guest_type+occupancy only; built-in metadata auto-populated by __post_init__ per 42-01 — single source of truth, NOT duplicated in get_configuration)"
  - "6 headless (QT_QPA_PLATFORM=offscreen) GUI tests covering row counts (sI=2, sH=3, c0te=1, sTprime=0), get_configuration round-trip (small=CH4@60, large=THF@100), and lattice-change row rebuild"
affects: [44-gui-integration, 45-cli-integration, custom-per-cage-gui-upload, future-gui-hydrate-controls, hydrate-export-gui-path]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-cage-type QFormLayout rows driven by cage_type_map keys (rebuilt on lattice change via _rebuild_cage_rows); _cage_guest_combos/_cage_occupancy_spins dicts keyed by cage_key"
    - "get_configuration builds CageGuestAssignment(guest_type, occupancy) per row; HydrateConfig.__post_init__ owns built-in metadata auto-populate (single source of truth per 42-01, no duplication in the GUI)"
    - "Water-only lattices (empty cage_type_map) render a 'No cages — water-only structure' label with zero rows; filled ices (single 'small' key) render one 'Guest cages' row"

key-files:
  created: []
  modified:
    - "quickice/gui/hydrate_panel.py"
    - "tests/test_hydrate_panel.py"

key-decisions:
  - "Per-cage rows driven by cage_type_map keys (NOT hardcoded small/large): row count varies by lattice (sI=2, sH=3, filled ice=1, water-only=0); _rebuild_cage_rows clears+rebuilds the rows container on lattice change so no stale widgets remain"
  - "get_configuration constructs CageGuestAssignment(guest_type=guest_id, occupancy=occ) per row and lets HydrateConfig.__post_init__ auto-populate built-in metadata (guest_atom_labels/guest_atom_count from GUEST_MOLECULES) — single source of truth per 42-01, NOT duplicated in get_configuration"
  - "_update_ff_label and _update_info_display read the FIRST cage row's selected guest (full per-cage fit display is a nice-to-have explicitly out of scope per the plan)"
  - "Phase 42 GUI surface is built-in guests only (ch4/thf): per-cage combos offer GUEST_MOLECULES entries. Custom-guest-per-cage via the GUI user-facing surface is Phase 44 (GUI-02) scope; custom CLI is Phase 45 (CLI-02) scope. The data model / API path (HydrateConfig.cage_guest_assignments with custom CageGuestAssignment entries) fully supports mixed custom guests — exercised by the 42-02 e2e test (CH4 + custom ethanol). The GUI panel combos and the CLI --cage-guest flag only offer built-in options."

patterns-established:
  - "Pattern: per-cage-type QFormLayout rows driven by cage_type_map keys; _cage_guest_combos/_cage_occupancy_spins dicts keyed by cage_key; _rebuild_cage_rows clears+rebuilds the rows container on lattice change"
  - "Pattern: get_configuration builds CageGuestAssignment per row with guest_type+occupancy only; __post_init__ owns built-in metadata auto-populate (single source of truth, no duplication in the GUI)"

# Metrics
duration: ~15min
completed: 2026-07-06
---

# Phase 42 Plan 06: GUI Per-Cage-Type Controls Summary

**Per-cage-type guest+occupancy rows in HydratePanel driven by cage_type_map (rebuilt on lattice change: sI=2, sH=3, filled ice=1, water-only=0), get_configuration builds cage_guest_assignments, 6 headless GUI tests (MIXED-01/02/03 GUI surface closed)**

## Performance

- **Duration:** ~15 min (implementation + human-verify checkpoint)
- **Started:** 2026-07-06T05:41Z (Task 1 commit)
- **Completed:** 2026-07-06T09:59Z (finalization after checkpoint approval)
- **Tasks:** 2 (plus 1 human-verify checkpoint — APPROVED)
- **Files modified:** 2 (quickice/gui/hydrate_panel.py, tests/test_hydrate_panel.py)

## Accomplishments

- Replaced the single `guest_combo` + `occupancy_small`/`occupancy_large` spinboxes in `HydratePanel` with per-cage-type rows: one `QComboBox` (built-in guest options from `GUEST_MOLECULES`) + one `QDoubleSpinBox` (0-100%, 1 decimal) per key in the selected lattice's `cage_type_map`, laid out in a `QFormLayout`
- Row count varies by lattice and rebuilds on lattice change: sI → 2 rows (small, large), sH → 3 rows (small, medium, large), filled ice c0te → 1 row (small), water-only sTprime → 0 rows with a "No cages — water-only structure" label
- `get_configuration` builds a `HydrateConfig(cage_guest_assignments={...})` from the per-cage rows, constructing `CageGuestAssignment(guest_type=guest_id, occupancy=occ)` per row; built-in metadata (`guest_atom_labels`/`guest_atom_count`) is auto-populated by `HydrateConfig.__post_init__` per 42-01 (single source of truth — NOT duplicated in `get_configuration`)
- `_update_ff_label` and `_update_info_display` read the FIRST cage row's guest (full per-cage fit display is a nice-to-have, explicitly out of scope); `configuration_changed` signal preserved on row change
- 6 headless (`QT_QPA_PLATFORM=offscreen`) GUI tests added: row counts for sI/sH/c0te/sTprime, `get_configuration` round-trip (small=CH4@60, large=THF@100), and lattice-change row rebuild
- Human-verify checkpoint APPROVED: user confirmed per-cage rows render correctly for sI=2, sH=3, c0te=1, sTprime=0; `get_configuration` round-trips; lattice change rebuilds rows; generate + export both function (export produced .gro + .top + tip4p-ice.itp)

## Task Commits

Each task was committed atomically:

1. **Task 1: Per-cage-type guest+occupancy rows driven by cage_type_map** - `815cf09` (feat)
2. **Task 2: Per-cage GUI row + get_configuration round-trip tests** - `1f40f39` (test)

**Plan metadata:** (pending — will be created after this SUMMARY)

_Note: Task 1 included the `get_configuration` rewrite (not just the row UI) — see Deviations._

## Files Created/Modified

- `quickice/gui/hydrate_panel.py` - Replaced `_create_guest_group` + `_create_occupancy_group` with `_create_cage_assignment_group` + `_rebuild_cage_rows`; per-cage `QComboBox` + `QDoubleSpinBox` rows driven by `cage_type_map`; `get_configuration` builds `cage_guest_assignments`; `_update_guest_ui_for_lattice` calls `_rebuild_cage_rows`; `_update_ff_label`/`_update_info_display` read the first cage row's guest
- `tests/test_hydrate_panel.py` - 6 headless GUI tests (row counts sI=2/sH=3/c0te=1/sTprime=0, `get_configuration` round-trip, lattice-change rebuild)

## Decisions Made

- **Per-cage rows driven by `cage_type_map` keys** (not hardcoded small/large): row count varies by lattice and `_rebuild_cage_rows` clears+rebuilds the rows container on lattice change so no stale widgets remain (sI=2, sH=3, filled ice=1, water-only=0).
- **`get_configuration` delegates built-in metadata to `__post_init__`**: constructs `CageGuestAssignment(guest_type=guest_id, occupancy=occ)` per row; `HydrateConfig.__post_init__` auto-populates built-in `guest_atom_labels`/`guest_atom_count` from `GUEST_MOLECULES` (42-01 single source of truth — no duplication in `get_configuration`).
- **First-row guest for ff label + fit display**: `_update_ff_label` and `_update_info_display` read the first cage row's selected guest; full per-cage fit display is a nice-to-have explicitly out of scope per the plan.
- **Phase 42 GUI surface is built-in guests only (ch4/thf)**: per-cage combos offer `GUEST_MOLECULES` entries only. Custom-guest-per-cage via the GUI user-facing surface is Phase 44 (GUI-02) scope; custom CLI is Phase 45 (CLI-02) scope. The data model / API path (`HydrateConfig.cage_guest_assignments` with custom `CageGuestAssignment` entries) fully supports mixed custom guests — exercised by the 42-02 e2e test (CH4 + custom ethanol). The GUI panel combos (this plan) and the CLI `--cage-guest` flag (42-07) only offer built-in options.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug / Rule 3 - Blocking] `get_configuration` implemented in Task 1 (not Task 2) to avoid a broken intermediate commit**
- **Found during:** Task 1 (removing `self.guest_combo` / `self.occupancy_small` / `self.occupancy_large`)
- **Issue:** The plan placed the `get_configuration` rewrite in Task 2 (the test task). But Task 1 removed the legacy single-guest widgets (`self.guest_combo`, `self.occupancy_small`, `self.occupancy_large`) and replaced them with per-cage `_cage_guest_combos`/`_cage_occupancy_spins` dicts. Leaving `get_configuration` referencing the removed widgets after Task 1 would produce a commit that crashes on the next `get_configuration()` call (broken intermediate state — `AttributeError`). An atomic commit must be in a working state; the first commit would not pass its own verify step.
- **Fix:** Moved the `get_configuration` rewrite (build `HydrateConfig(cage_guest_assignments=...)` from `_cage_guest_combos`/`_cage_occupancy_spins`) into Task 1 so the feature commit is internally consistent. Task 2 became test-only (added the 6 headless GUI tests), matching its actual `test(42-06):` commit type.
- **Files modified:** quickice/gui/hydrate_panel.py (Task 1); tests/test_hydrate_panel.py (Task 2)
- **Verification:** `pytest tests/test_hydrate_panel.py` → 6 passed; `pytest tests/test_hydrate_config_custom.py` → 16 passed (no regression); `pytest tests/test_cli/test_mixed_cage_cli.py tests/test_e2e_mixed_cage_occupancy.py` → 9 passed (no regression). Human-verify checkpoint steps 1-7 confirmed rows render + round-trip + rebuild; step 8 confirmed export produces .gro + .top + tip4p-ice.itp.
- **Committed in:** 815cf09 (Task 1 — get_configuration included)

---

**Total deviations:** 1 auto-fixed (1 bug/blocking — get_configuration moved into Task 1 for a working atomic commit; Task 2 became test-only)
**Impact on plan:** No scope creep. The deviation only changes which task carries the `get_configuration` rewrite — the final code and tests are identical to what the plan specified, just partitioned into a working feat commit + a test commit instead of a feat commit that would crash + a combined feat+test commit.

## Issues Encountered

- The user noted (checkpoint step 8) that the export path has a separate ITP-staging gap when config and structure are mismatched — that is 42-05 scope, NOT 42-06; it will be caught by phase verification. No 42-06 action required.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 42-06 complete: GUI `HydratePanel` shows per-cage-type guest+occupancy rows driven by `cage_type_map`, rebuilt on lattice change; `get_configuration` builds `cage_guest_assignments`; 6 headless GUI tests pass.
- Phase 42 is now 8/8 plans complete — Phase 42 COMPLETE. All MIXED-01/02/03/04/05 items closed across GUI + CLI + generator + writers + renderer.
- Known limitation (Phase 42 surface): GUI panel combos (this plan) and the CLI `--cage-guest` flag (42-07) offer built-in guests only (ch4/thf). Custom-guest-per-cage via the GUI/CLI user-facing surfaces is Phase 44 (GUI-02) and Phase 45 (CLI-02) scope. The data model / API path (`HydrateConfig.cage_guest_assignments` with custom `CageGuestAssignment` entries) fully supports mixed custom guests — exercised by the 42-02 e2e test (CH4 + custom ethanol).
- Known limitation (export ITP staging): a separate ITP-staging gap exists when config and structure are mismatched — 42-05 scope, to be caught by phase verification (not a 42-06 regression).

---
*Phase: 42-mixed-cage-occupancy*
*Completed: 2026-07-06*
