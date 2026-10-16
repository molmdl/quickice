---
phase: quick-032
plan: 032
type: execute
wave: 1
depends_on: []
files_modified:
  - AGENTS.md
  - tests/test_scancode_bugs_custom_guest_bridge_assert.py   # git mv -> tests/scancode/
  - tests/test_scancode_bugs_piece_logger.py                # git mv -> tests/scancode/
  - quickice/gui/main_window.py
  - .planning/debug/resolved/ (8 docs git mv'd in)
  - .planning/DEFERRED-UAT.md
  - .planning/codebase/CONCERNS.md
autonomous: true

must_haves:
  truths:
    - "AGENTS.md states the exact current collected test count (stale '~1846' gone, no tilde)"
    - "AGENTS.md headless-VTK bullet carries no ROADMAP.md TEST-06 pointer; it states the accepted offscreen + localhost-DISPLAY + mock/skip approach"
    - "All 19 test_scancode_bugs_*.py files live in tests/scancode/; zero remain at tests/ root; both moved files pass from their new location; collection count unchanged"
    - "quickice/ contains zero '[Water Count Debug]' matches"
    - "main_window.py _on_custom_finished still computes water_replaced and issues both custom_molecule_panel.log_message display calls (user-facing behavior preserved)"
    - "All 8 named debug docs live in .planning/debug/resolved/; the 7 former open-ish docs carry status resolved + verified-in-code 2026-10-15 notes; custom-mol-conc-random-mode-crash.md relocated content-unchanged"
    - ".planning/DEFERRED-UAT.md header declares SUPERSEDED, pointing to the six UAT workflow scripts (.planning/uat-workflows/, A/B/C/D/E/G — no F), quick-030 dry-run green"
    - "The three CONCERNS.md entries (Scancode split, AGENTS.md drift (a)+(b), Stale-open debug-docs) carry 'resolved by quick task 032 (commit(s) <hash>, 2026-10-16)' notes"
  artifacts:
    - path: "AGENTS.md"
      contains: ["All tests (", "tests/scancode/test_scancode_bugs_*.py"]
      absent: ["~1846", "TEST-06"]
    - path: "quickice/gui/main_window.py"
      contains: ["water_replaced = original_water_count - modified_water_count", "Replaced {water_replaced} overlapping liquid water molecules"]
      absent: ["[Water Count Debug]"]
    - path: "tests/scancode/test_scancode_bugs_custom_guest_bridge_assert.py"
      provides: "scancode regression test, relocated via git mv"
    - path: "tests/scancode/test_scancode_bugs_piece_logger.py"
      provides: "scancode regression test, relocated via git mv"
    - path: ".planning/debug/resolved/custom-mol-concentration-input.md"
      contains: ["status: resolved", "2026-10-15"]
    - path: ".planning/DEFERRED-UAT.md"
      contains: ["SUPERSEDED", "uat-workflows"]
    - path: ".planning/codebase/CONCERNS.md"
      contains: ["quick-032"]
  key_links:
    - from: "AGENTS.md:12 pinned count"
      to: "Task 1 collection checks (pytest --collect-only, tail -3)"
      via: "exact N measured at execution time (planning-time 2026-10-16: 1850 tests collected)"
      pattern: "All tests \\(\\d+\\)"
    - from: "CONCERNS.md resolution notes"
      to: "Task 1 + Task 2 commit hashes"
      via: "git log --oneline short hashes cited in the appended notes"
      pattern: "quick-032.*commit"
    - from: "main_window.py post-edit region"
      to: "custom_molecule_panel.log_message display path"
      via: "if water_replaced > 0: branch retained around the second log_message call"
      pattern: "if water_replaced > 0:"
---

<objective>
Close the 5-item codebase-hygiene bundle from the 2026-10-15 independent audit (recorded in `.planning/codebase/CONCERNS.md`): pin AGENTS.md's drifted test count, replace the stale ROADMAP TEST-06 pointer with the operative headless-VTK guidance, consolidate the last 2 root-level scancode tests into `tests/scancode/`, file 8 stale-open debug docs to `.planning/debug/resolved/` with resolution notes, mark `.planning/DEFERRED-UAT.md` superseded, remove the `[Water Count Debug]` investigation remnant from `quickice/gui/main_window.py`, and append resolution notes to the 3 affected CONCERNS.md entries.

Purpose: every "open-ish" status in the repo now reflects reality — future agents stop re-investigating verified-fixed issues and stop trusting stale doc claims.
Output: 3 atomic commits (test layout / production cleanup / docs-repo-hygiene); exact commit order and grouping below. Drift item (c) (Lazy Imports) is ALREADY RESOLVED by quick-031 — do NOT touch the AGENTS.md Lazy Imports section.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@AGENTS.md
@.planning/codebase/CONCERNS.md
@quickice/gui/main_window.py

Repo rules that bind every task (from AGENTS.md): conda env `quickice`; every pytest invocation needs `QT_QPA_PLATFORM=offscreen` AND an external `timeout` guard (never pytest-timeout alone); tracked moves use `git mv`; atomic commits with explicit paths only — NEVER `git add .` / `git add -A`.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Consolidate last 2 root-level scancode tests into tests/scancode/ (test layout commit)</name>
  <files>tests/test_scancode_bugs_custom_guest_bridge_assert.py, tests/test_scancode_bugs_piece_logger.py, AGENTS.md</files>
  <action>
1. **Baseline collection count** (feeds the AGENTS.md:12 pin in Task 3 — record the exact number N):
   ```bash
   QT_QPA_PLATFORM=offscreen timeout 180 python -m pytest --collect-only -q 2>/dev/null | tail -3
   ```
   Planning-time check on 2026-10-16 yielded `1850 tests collected in 1.29s`. Expected N=1850; if the observed number differs, use the observed N for Task 3's AGENTS.md edit and note the discrepancy in the Task 3 CONCERNS resolution line.
2. **Pre-move layout check**: `ls tests/test_scancode_bugs_*.py` → exactly the 2 stragglers; `ls tests/scancode/test_scancode_bugs_*.py | wc -l` → 17.
3. **Move both files** (tracked move, preserves history):
   ```bash
   git mv tests/test_scancode_bugs_custom_guest_bridge_assert.py tests/scancode/
   git mv tests/test_scancode_bugs_piece_logger.py tests/scancode/
   ```
   Move is safe: both files import only stdlib (`os`, `subprocess`, `sys`, `types`, `pathlib`, `logging`), `pytest`, and `quickice.structure_generation.*` — zero tests-root-relative imports and zero `__file__`-relative resources. `tests/scancode/` already has `__init__.py` and 17 collected siblings.
4. **Update the AGENTS.md Testing tree line** (the doc/practice half-match named by the CONCERNS "Scancode test placement split" entry — its Fix approach explicitly requires this):
   - Old (AGENTS.md, Testing section): `Test files: \`test_*.py\` (unit), \`tests/e2e/<feature>/test_e2e_*.py\` (e2e), \`test_scancode_bugs_*.py\` (regression).`
   - New: `Test files: \`test_*.py\` (unit), \`tests/e2e/<feature>/test_e2e_*.py\` (e2e), \`tests/scancode/test_scancode_bugs_*.py\` (scancode regression).`
5. **Run BOTH moved files from their new location**:
   ```bash
   QT_QPA_PLATFORM=offscreen timeout 300 python -m pytest tests/scancode/test_scancode_bugs_custom_guest_bridge_assert.py tests/scancode/test_scancode_bugs_piece_logger.py -q
   ```
6. **Post-move collection check** — same command as step 1; count MUST equal the pre-move N (moves add/drop nothing).
7. **Commit** (renames already staged by `git mv`; stage the doc edit explicitly):
   ```bash
   git add AGENTS.md
   git commit -m "test(scancode): move last 2 root-level scancode regression tests into tests/scancode/ (19 total, 0 at root)"
   ```
  </action>
  <verify>
   - Both moved files pass from `tests/scancode/` (0 failed).
   - `ls tests/test_scancode_bugs_*.py 2>/dev/null` → no matches; `ls tests/scancode/test_scancode_bugs_*.py | wc -l` → 19.
   - Collection count pre-move == post-move (N unchanged).
   - `git status --short` shows the two renames as `R` (rename) entries, nothing else unintended; `git log --oneline -1` shows the test-layout commit.
  </verify>
  <done>
   19 scancode regression files in `tests/scancode/`, 0 at `tests/` root, AGENTS.md testing-tree line matches practice, both moved tests green from their new home, collection count unchanged (N). One atomic test-layout commit exists — record its short hash for Task 3's CONCERNS resolution notes.
  </done>
</task>

<task type="auto">
  <name>Task 2: Remove the 12 [Water Count Debug] lines from MainWindow._on_custom_finished (production cleanup commit)</name>
  <files>quickice/gui/main_window.py</files>
  <action>
First enumerate what will be deleted (sanity guard):
```bash
grep -n "\[Water Count Debug\]" quickice/gui/main_window.py
```
Exactly **12 tagged lines** in `MainWindow._on_custom_finished` (def at `:1326`), within the block `:1376-1412`:
- 10× `logger.debug(f"[Water Count Debug] ...")` at `:1376`, `:1377`, `:1379`, `:1383`, `:1387`, `:1392`, `:1398`, `:1405`, `:1407`, `:1412`
- 2× `logger.warning(...)` at `:1389` and `:1395` — these also carry the `[Water Count Debug]` tag and they also go (CONCERNS fix approach: "delete the `[Water Count Debug]` lines").

**Delete ONLY those 12 tagged log lines.** PRESERVE the water-replacement DISPLAY logic interleaved in the same region — it is user-facing behavior and every non-tagged statement/comment around them must survive byte-for-byte:
- `:1382` `original_water_count = self._current_interface_result.water_nmolecules`
- `:1386` `modified_water_count = result.interface_structure.water_nmolecules`
- `:1390` `modified_water_count = original_water_count  # Fallback to avoid negative count`
- `:1391` `water_replaced = original_water_count - modified_water_count`
- `:1394` `water_replaced = 0`
- `:1399-1402` and `:1408-1410` both `self.custom_molecule_panel.log_message(...)` calls
- `:1406` `if water_replaced > 0:` branch structure, and the comments at `:1375`, `:1384`, `:1397`, `:1404`

Expected post-edit shape of the region (verify your edit matches this):
```python
            # Calculate water molecules replaced
            if hasattr(self, '_current_interface_result') and self._current_interface_result is not None:
                original_water_count = self._current_interface_result.water_nmolecules
                # CustomMoleculeStructure.interface_structure is a typed dataclass field (can be None)
                if result.interface_structure is not None:
                    modified_water_count = result.interface_structure.water_nmolecules
                else:
                    modified_water_count = original_water_count  # Fallback to avoid negative count
                water_replaced = original_water_count - modified_water_count
            else:
                water_replaced = 0

            # Log success with complete system info
            self.custom_molecule_panel.log_message(
                f"Custom molecule insertion complete: {result.custom_molecule_count} molecules, "
                f"{len(result.positions)} total atoms (ice+water+custom)"
            )

            # Log water replacement count if any water was replaced
            if water_replaced > 0:
                self.custom_molecule_panel.log_message(
                    f"Replaced {water_replaced} overlapping liquid water molecules"
                )
```
Tidy any leftover double-blank-line artifacts created by the deletions (the former blanks at `:1380`/`:1396`) — cosmetic only, no other change.

GUI-surface sanity (per planning constraints — grep first, then run what exists):
```bash
grep -rn "water_replaced\|_on_custom_finished\|Replaced.*overlapping" tests/
```
No direct coverage of this handler exists today (verified at planning time — expect zero hits on `water_replaced`/`_on_custom_finished`). Run the nearest GUI-surface suites that import and exercise `quickice.gui.main_window`:
```bash
QT_QPA_PLATFORM=offscreen DISPLAY=localhost:11.0 timeout 300 python -m pytest tests/scancode/test_scancode_bugs_gui_ion.py tests/test_hydrate_panel.py tests/test_output/test_hydrate_export_dialog_label.py -q
```
(`DISPLAY=localhost:11.0` makes the `is_vtk_available()` SSH-X11 heuristic return False → MainWindow takes no-VTK branches, per AGENTS.md — no real display needed.)

Commit:
```bash
git add quickice/gui/main_window.py
git commit -m 'chore(gui): remove leftover "[Water Count Debug]" investigation logging from _on_custom_finished'
```
  </action>
  <verify>
   - `grep -c "\[Water Count Debug\]" quickice/gui/main_window.py` → 0 matches (grep exits 1; zero matches in the whole `quickice/` tree).
   - `python -m py_compile quickice/gui/main_window.py` → compiles clean (conda env `quickice`).
   - The focused GUI-surface run (3 files above) → 0 failed.
   - Read back the post-edit `:1370-1400` region and confirm it matches the expected post-edit shape (compute + both `log_message` calls + `if water_replaced > 0:` branch all intact).
   - `git log --oneline -1` shows the production cleanup commit; the diff touches only the 12 log-line deletions (+ blank-line tidy).
  </verify>
  <done>
   Zero `[Water Count Debug]` matches remain in `quickice/`; the water-replacement display behavior (water_replaced computation, both log_message calls, fallback branches) is unchanged; focused GUI tests green; one atomic production cleanup commit exists — record its short hash for Task 3's CONCERNS resolution notes.
  </done>
</task>

<task type="auto">
  <name>Task 3: AGENTS.md drift fixes + debug-doc filing + DEFERRED-UAT superseded note + CONCERNS resolutions (docs/repo-hygiene commit)</name>
  <files>AGENTS.md, .planning/debug/ (8 docs moved to resolved/), .planning/DEFERRED-UAT.md, .planning/codebase/CONCERNS.md</files>
  <action>
**A. AGENTS.md line 12 (drift (a)) — pin the exact count.** Use N from Task 1's collection checks (expected 1850).
- Old: `pytest                          # All tests (~1846)`
- New: `pytest                          # All tests (1850)` (tilde dropped; substitute the observed N if different)

**B. AGENTS.md line 42 (drift (b)) — replace the stale pointer.** Current ROADMAP.md:261 TEST-06 = mixed-cage-occupancy e2e, marked DONE — the "(deferred)" pointer is dead. Keep the first two sentences; replace the final pointer sentence with the direct statement of the operative approach.
- Old line 42: `- **Headless/remote VTK:** GUI tests require \`QT_QPA_PLATFORM=offscreen\` on machines without a display. VTK rendering may still crash in some headless environments — mock or skip VTK-dependent tests if needed. See ROADMAP.md TEST-06 (deferred).`
- New line 42: `- **Headless/remote VTK:** GUI tests require \`QT_QPA_PLATFORM=offscreen\` on machines without a display. VTK rendering may still crash in some headless environments — mock or skip VTK-dependent tests if needed. The accepted approach: \`QT_QPA_PLATFORM=offscreen\` is enforced at session start by \`tests/conftest.py\`; MainWindow-level tests force a localhost \`DISPLAY\` (e.g. \`DISPLAY=localhost:11.0\`) so the \`is_vtk_available()\` SSH-X11 heuristic (\`quickice/gui/vtk_utils.py\`) returns False, and VTK-render-dependent branches are mocked or skipped headless.`
- Do NOT touch the AGENTS.md Lazy Imports section (drift (c) already resolved by quick-031).

**C. File the 8 debug docs** (tracked moves; `.planning/debug/` top level holds 21 .md files — move ONLY these 8 by name; no name collisions exist in `resolved/`):
```bash
git mv .planning/debug/custom-mol-concentration-input.md       .planning/debug/resolved/
git mv .planning/debug/custom-mol-water-count-missing.md       .planning/debug/resolved/
git mv .planning/debug/water-replacement-not-happening.md      .planning/debug/resolved/
git mv .planning/debug/hydrate-custom-solute-visibility.md     .planning/debug/resolved/
git mv .planning/debug/interface-writer-mixed-guest.md        .planning/debug/resolved/
git mv .planning/debug/molh-atom-drop-origin.md                .planning/debug/resolved/
git mv .planning/debug/gmx-export-issues.md                    .planning/debug/resolved/
git mv .planning/debug/custom-mol-conc-random-mode-crash.md    .planning/debug/resolved/
```

**D. Status-line notes for the 7 open-ish docs.** For each, change the frontmatter `status:` value to `resolved` and insert a `resolution:` line immediately after it:
- `custom-mol-concentration-input.md`: `status: analyzed` →
- `custom-mol-water-count-missing.md`: `status: diagnosed` →
- `water-replacement-not-happening.md`: `status: investigating` →
- `hydrate-custom-solute-visibility.md`, `interface-writer-mixed-guest.md`, `molh-atom-drop-origin.md`, `gmx-export-issues.md`: `status: verifying` →

Each becomes:
```yaml
status: resolved
resolution: "Fix verified in code on 2026-10-15 - see .planning/codebase/CONCERNS.md (Stale-open debug documents + investigation remnants)."
```
Leave the `trigger:`/`created:`/`updated:` frontmatter fields and all body content untouched. **`custom-mol-conc-random-mode-crash.md` gets NO content edit** — it is already RESOLVED-status (non-YAML `**Status:** RESOLVED` header); it is relocated as-is.

**E. DEFERRED-UAT.md superseded header note.** Header currently reads `**Status:** Pending execution` (line 4).
- New: `**Status:** SUPERSEDED (2026-10-16) — supplanted by the six UAT workflow scripts in \`.planning/uat-workflows/\` (A/B/C/D/E/G — no F), dry-ran green by quick task 030; retained for historical reference only`
- Do not touch the rest of the 1100-line file.

**F. CONCERNS.md resolution notes.** Append resolution lines to exactly these 3 entries. First capture the Task 1 and Task 2 short hashes: `git log --oneline -2` (h1 = test-layout commit, h2 = production cleanup commit).

1. **"Scancode test placement split"** — after its `Fix approach:` bullet, append:
   `- Resolution: RESOLVED 2026-10-16 by quick task 032 (commit <h1>): the 2 stragglers moved via \`git mv\` into \`tests/scancode/\` (19 files total, 0 at tests/ root); AGENTS.md testing-tree line updated to \`tests/scancode/test_scancode_bugs_*.py\`; full-suite collection count unchanged (N).`
2. **"AGENTS.md drift (three stale claims)"** — the Fix approach line currently ends with `(Drift items (a) and (b) remain open, untouched.)` which is now false: delete that parenthetical, and append after the Fix approach:
   `- Resolution (a)+(b): RESOLVED 2026-10-16 by quick task 032 (commits <h1>, <h2>, docs commit): AGENTS.md:12 count pinned to the exact collected number (N, tilde dropped); AGENTS.md:42 \\\`ROADMAP.md TEST-06 (deferred)\\\` pointer replaced by a direct statement of the accepted offscreen + localhost-DISPLAY + mock/skip approach (current ROADMAP TEST-06 = mixed-cage-occupancy, DONE). Item (c) remains resolved by quick-031 (commit 060e8d7f) above.`
3. **"Stale-open debug documents + investigation remnants"** — after its `Fix approach:` bullet, append:
   `- Resolution: RESOLVED 2026-10-16 by quick task 032: 8 docs filed to \`.planning/debug/resolved/\` (7 open-ish status lines annotated \`status: resolved\` + verified-in-code 2026-10-15 notes per above; \`custom-mol-conc-random-mode-crash.md\` relocated as-is); \`.planning/DEFERRED-UAT.md\` marked SUPERSEDED pointing to the six UAT workflow scripts (\`.planning/uat-workflows/\`, A/B/C/D/E/G — no F, quick-030 dry-ran green); the 12 \`[Water Count Debug]\` log lines removed from \`quickice/gui/main_window.py::_on_custom_finished\` (production cleanup commit <h2>) — water-replacement display logic preserved (focused GUI test run green + post-edit region read-back).`

**G. Commit** — `git mv` already staged the 8 renames; stage the content edits on the moved docs + the 3 edited files with explicit paths (never `git add .`/`-A`):
```bash
git add AGENTS.md .planning/DEFERRED-UAT.md .planning/codebase/CONCERNS.md \
  .planning/debug/resolved/custom-mol-concentration-input.md \
  .planning/debug/resolved/custom-mol-water-count-missing.md \
  .planning/debug/resolved/water-replacement-not-happening.md \
  .planning/debug/resolved/hydrate-custom-solute-visibility.md \
  .planning/debug/resolved/interface-writer-mixed-guest.md \
  .planning/debug/resolved/molh-atom-drop-origin.md \
  .planning/debug/resolved/gmx-export-issues.md
git commit -m "docs(quick-032): fix AGENTS.md drift (test count, headless-VTK pointer), file 8 stale debug docs, mark DEFERRED-UAT superseded, resolve 3 CONCERNS entries"
```

**H. Final closure check** — the pinned AGENTS.md count must match the end-state suite:
```bash
QT_QPA_PLATFORM=offscreen timeout 180 python -m pytest --collect-only -q 2>/dev/null | tail -3
```
→ must report N tests collected (same as the AGENTS.md:12 pin; this bundle adds/removes no tests).
  </action>
  <verify>
   - `grep -n "1846\|TEST-06" AGENTS.md` → zero matches; `grep -n "All tests (" AGENTS.md` → shows the pinned N.
   - All 8 docs exist in `.planning/debug/resolved/` and none remain at `.planning/debug/` top level (the other 13 top-level debug docs stay untouched).
   - `grep -n "^status:" .planning/debug/resolved/custom-mol-concentration-input.md ...` (all 7) → `status: resolved` + a `2026-10-15` resolution line.
   - `grep -n "SUPERSEDED" .planning/DEFERRED-UAT.md` → present in the header with the `uat-workflows` pointer.
   - `grep -c "quick-032" .planning/codebase/CONCERNS.md` → the 3 new resolution notes (stale "(a) and (b) remain open" parenthetical gone).
   - Final collect-only reports N tests (== the AGENTS.md pin).
   - `git log --oneline -3` → the 3 atomic commits; `git status` clean except the uncommitted 032-PLAN.md.
  </verify>
  <done>
   AGENTS.md drift-free (exact count pinned, operative headless guidance in place, Lazy Imports untouched); 8 debug docs filed to resolved/ with verified-in-code notes (1 relocated as-is); DEFERRED-UAT marked SUPERSEDED; the 3 CONCERNS entries closed with quick-032 + commit-hash notes; final collection count equals the pinned count; one atomic docs/hygiene commit exists.
  </done>
</task>

</tasks>

<verification>
Bundle-level closure checks (run after Task 3):
1. `grep -rn "\[Water Count Debug\]" quickice/` → zero matches (production tree; `.planning/debug/` history docs legitimately mention the tag — they are not in scope).
2. `ls tests/scancode/test_scancode_bugs_*.py | wc -l` → 19; root `tests/test_scancode_bugs_*.py` → none.
3. `QT_QPA_PLATFORM=offscreen timeout 180 python -m pytest --collect-only -q 2>/dev/null | tail -3` → N tests collected, N == the number pinned at AGENTS.md:12.
4. Three commits, one per task, each staging explicit paths only (`git mv`-staged renames + named `git add`s). 032-PLAN.md is NOT committed — leave it for the orchestrator.
5. No full-suite GATE-FULL run required for this bundle (mirrors quick-031's verification depth): the only production change is deletion of 12 log lines with no test coverage touching the region; the focused GUI run + collection checks carry the gate.
</verification>

<success_criteria>
- 2 scancode tests relocated via `git mv`, both green from `tests/scancode/`, 19/0 layout, collection count unchanged (N, expected 1850).
- Exactly the 12 tagged `[Water Count Debug]` lines removed from `quickice/gui/main_window.py::_on_custom_finished`; the water-replacement computation, fallback branches, and both `log_message` display calls preserved; focused GUI test files 0 failed.
- AGENTS.md:12 pins the exact count (no `~`); AGENTS.md:42 states the accepted offscreen/DISPLAY/mock-skip approach with no TEST-06 pointer; AGENTS.md testing-tree line says `tests/scancode/`.
- 8 debug docs in `.planning/debug/resolved/`; the 7 former open-ish ones carry `status: resolved` + the 2026-10-15 verified-in-code note; `custom-mol-conc-random-mode-crash.md` relocated content-unchanged; the other 13 top-level debug docs untouched.
- `.planning/DEFERRED-UAT.md` header declares SUPERSEDED → six UAT workflow scripts (A/B/C/D/E/G), quick-030 green.
- `.planning/codebase/CONCERNS.md`: 3 resolution notes ("resolved by quick task 032", commit hashes, 2026-10-16) appended to the Scancode split, AGENTS.md drift (a)+(b), and Stale-open debug-docs entries — with the main_window.py production change noted.
- 3 atomic commits (test layout / production cleanup / docs-hygiene), explicit-path staging only; 032-PLAN.md left uncommitted.
</success_criteria>

<output>
After completion, create `.planning/quick/032-hygiene-agents-md-scancode-debug-docs/032-SUMMARY.md` from the summary template (frontmatter + what changed + verification numbers: pre/post collection N, focused GUI run results, the 3 commit hashes).

If recording completion in STATE.md ("Last activity" row) or committing the summary, stage those explicit files in a final `docs(quick-032): record task 032 completion` commit — commit_docs=true permits committing `.planning/` documents, but do NOT commit `032-PLAN.md` (leave it uncommitted for the orchestrator).
</output>
