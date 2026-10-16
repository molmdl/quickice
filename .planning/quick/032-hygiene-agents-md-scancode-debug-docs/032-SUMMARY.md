# Quick Task 032: Hygiene — AGENTS.md drift, scancode moves, debug docs Summary

**Phase:** quick-032
**Plan:** 032
**Subsystem:** repo hygiene (docs + test layout + production cleanup)
**Completed:** 2026-10-16

## One-liner

Closed the 5-item 2026-10-15 audit bundle: pinned AGENTS.md test count (1850), replaced the dead TEST-06 pointer with the operative headless-VTK approach, moved the last 2 root scancode tests into `tests/scancode/` (19/0), removed the `[Water Count Debug]` remnants from `main_window.py`, filed 8 stale debug docs to `.planning/debug/resolved/`, marked DEFERRED-UAT superseded, and resolved the 3 affected CONCERNS.md entries.

## Commits

| Commit | Message |
|--------|---------|
| `3447ce31` | test(scancode): move last 2 root-level scancode regression tests into tests/scancode/ (19 total, 0 at root) |
| `4f378201` | chore(gui): remove leftover "[Water Count Debug]" investigation logging from _on_custom_finished |
| `3c36b6fc` | docs(quick-032): fix AGENTS.md drift (test count, headless-VTK pointer), file 8 stale debug docs, mark DEFERRED-UAT superseded, resolve 3 CONCERNS entries |

## What changed

**Task 1 — test layout (`3447ce31`):**
- `git mv` of `tests/test_scancode_bugs_custom_guest_bridge_assert.py` and `tests/test_scancode_bugs_piece_logger.py` → `tests/scancode/` (final 19/0 layout; previously 17 in dir + 2 at root).
- AGENTS.md Testing tree line updated to `tests/scancode/test_scancode_bugs_*.py` (scancode regression).

**Task 2 — production cleanup (`4f378201`):**
- Removed the 12 `[Water Count Debug]`-tagged log lines from `MainWindow._on_custom_finished` (10 `logger.debug` + 2 `logger.warning`).
- Also removed 2 structural remnants that existed only to host debug logs: the `if hasattr(...)` probe block and the `else:` branch after `if water_replaced > 0:` — both would have been syntax errors with empty bodies after the tagged-line deletions, and both are absent from the plan's expected post-edit shape. Total 15 deletions.
- Water-replacement display logic preserved byte-for-byte: `water_replaced` computation, both `custom_molecule_panel.log_message` calls, the `if water_replaced > 0:` branch, and all comments.

**Task 3 — docs/repo hygiene (`3c36b6fc`):**
- AGENTS.md:12 — `All tests (~1846)` → `All tests (1850)` (tilde dropped, exact count pinned).
- AGENTS.md:42 — dead `ROADMAP.md TEST-06 (deferred)` pointer replaced by direct statement of the accepted offscreen + localhost-DISPLAY + mock/skip approach. Lazy Imports section untouched (resolved by quick-031).
- 8 debug docs `git mv`'d to `.planning/debug/resolved/`; the 7 open-ish ones now carry `status: resolved` + a 2026-10-15 verified-in-code `resolution:` note; `custom-mol-conc-random-mode-crash.md` relocated content-unchanged.
- `.planning/DEFERRED-UAT.md` header → `SUPERSEDED (2026-10-16)` pointing to the six UAT workflow scripts (`.planning/uat-workflows/`, A/B/C/D/E/G — no F, quick-030 dry-ran green).
- `.planning/codebase/CONCERNS.md` — resolution lines with commit hashes appended to: Scancode test placement split, AGENTS.md drift (a)+(b) (stale "(a) and (b) remain open" parenthetical deleted), Stale-open debug documents + investigation remnants.

## Verification numbers (actual)

- **Collection count:** 1850 pre-move → 1850 post-move → 1850 final closure (matches AGENTS.md:12 pin exactly; expected N=1850 confirmed).
- **Moved scancode tests from new location:** 5 passed / 0 failed (1.69s).
- **Layout:** `tests/scancode/test_scancode_bugs_*.py` = 19 files; zero `test_scancode_bugs_*.py` at `tests/` root.
- **Focused GUI sanity run** (`tests/scancode/test_scancode_bugs_gui_ion.py`, `tests/test_hydrate_panel.py`, `tests/test_output/test_hydrate_export_dialog_label.py`, offscreen + `DISPLAY=localhost:11.0`): 47 passed / 0 failed (1.10s).
- **`[Water Count Debug]` matches in `quickice/` (source):** 0.
- **`py_compile quickice/gui/main_window.py`:** clean.
- **`git status` post-run:** clean except untracked `.planning/quick/032-*/` (PLAN left uncommitted per constraints).

## Deviations

- **[Rule 3 - Blocking]** Task 2: beyond the 12 tagged lines, an empty `if hasattr(self, '_current_interface_result'):` probe block and an `else:` branch whose only body was a tagged debug line would have left syntax errors after deletion. Both removed (consistent with the plan's stated expected post-edit shape; 15 deletions total instead of 12, all within the debug region).

## Files modified

- `AGENTS.md`
- `quickice/gui/main_window.py`
- `tests/scancode/test_scancode_bugs_custom_guest_bridge_assert.py` (moved)
- `tests/scancode/test_scancode_bugs_piece_logger.py` (moved)
- 8 docs under `.planning/debug/resolved/` (moved; 7 content-edited)
- `.planning/DEFERRED-UAT.md`
- `.planning/codebase/CONCERNS.md`
