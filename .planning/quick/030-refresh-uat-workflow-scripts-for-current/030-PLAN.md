---
phase: 030-refresh-uat-workflow-scripts-for-current
plan: 030
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/uat-workflows/E-test-refactor.sh
  - .planning/uat-workflows/README.md
  - .planning/quick/030-refresh-uat-workflow-scripts-for-current/030-SUMMARY.md
autonomous: true

must_haves:
  truths:
    - "E-test-refactor.sh with default RUN_FULL=0 exits 0 against current HEAD (no spurious count-pin failure)"
    - "All six scripted workflows (A, B, C, D, E, G) dry-run against current HEAD; every PASS/FAIL recorded with the exact command in 030-SUMMARY.md"
    - "No LIVE stale test-count reference (1846) remains in any .planning/uat-workflows/*.sh or README.md"
    - "README 'What it checks' / checklist claims match reality (byte-eq contract test, not baseline_shas.json; tests/test_cli/ = 10 files)"
    - "Zero changes to quickice/ or tests/ (UAT script hygiene only)"
  artifacts:
    - path: ".planning/uat-workflows/E-test-refactor.sh"
      provides: "Collection-count pin re-set to current count (1849) + refreshed count comments"
      contains: "-eq 1849"
    - path: ".planning/uat-workflows/README.md"
      provides: "Workflow E narrative matching what the script actually checks"
      contains: "1849"
    - path: ".planning/quick/030-refresh-uat-workflow-scripts-for-current/030-SUMMARY.md"
      provides: "Dry-run results table: workflow | exact command | exit code | PASS/FAIL | drift fixed / escalation"
  key_links:
    - from: ".planning/uat-workflows/E-test-refactor.sh:34 exact-count pin"
      to: "live `python -m pytest --collect-only -q` output"
      via: "COLLECT_COUNT parsed from pytest summary line, compared with -eq"
      pattern: 'COLLECT_COUNT.. -eq 1849'
    - from: ".planning/uat-workflows/README.md 'What it checks' item 9 + checklist 48.1-3"
      to: "tests/test_gro_top_byte_equivalence.py (the post-48.3 byte-eq artifact)"
      via: "README claim updated to the committed contract test (baseline_shas.json was removed in 48.3)"
      pattern: "test_gro_top_byte_equivalence"
---

<objective>
Refresh the UAT workflow scripts for the current test counts so the user's manual UAT redo does not hit spurious failures, then dry-run all six scripted workflows against current HEAD and fix any other drift they reveal.

**Trigger:** Quick task 029 added 3 tests (2 in tests/e2e/solute_ion/, 1 in tests/e2e/hydrate/), moving collection 1846 → 1849. `.planning/uat-workflows/E-test-refactor.sh:34` pins `[ "$COLLECT_COUNT" -eq 1846 ]` → will spuriously FAIL during UAT.

Purpose: the user is about to redo the manual full-workflow UAT (48.3 exit-gate promise). A UAT script failing on a stale count undermines trust in the whole UAT pass/fail signal.
Output: re-pinned E script + refreshed README narrative + verified dry-run of A/B/C/D/E/G with results recorded in 030-SUMMARY.md.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@AGENTS.md
@.planning/uat-workflows/E-test-refactor.sh
@.planning/uat-workflows/README.md
@.planning/uat-workflows/ISSUES-FOUND.md

Environment facts (verified 2026-09-25): conda env `quickice` already active — invoke `python` / `python -m pytest` / `gmx` DIRECTLY (no conda run / activation wrappers; never install anything). `gmx` availability is optional — C and G self-skip grompp checks when absent (record which mode ran).

Current measurements (orchestrator, 2026-09-25):
- `python -m pytest --collect-only -q` → **1849 tests collected** (re-measure in Task 1 before pinning)
- `python -m pytest tests/e2e --collect-only -q` → 331
- Last full suite (quick-029): 1847 passed / 2 skipped / 0 failed / 200.05s (validated — do NOT re-run full suite)

Verified drift targets (exact lines, do not guess further):
- **E-test-refactor.sh**: line 31 (comment "1846 ... post-48.3 count"), line 34 (`-eq 1846` pin), line 35 (`(1846)` PASS label), line 37 (`expected 1846` FAIL label), line 159 (comment "1846 collected, 2 pre-existing skips"). The "2 pre-existing skips" claim is still true (029 run: 2 skipped) — keep it.
- **README.md**: line 178 ("collects 1846 tests"), line 180 ("tests/test_cli/ has 8 files" — actual is **10**; scancode=18 and output=21 verified correct), line 186 ("baseline_shas.json exists" — file was REMOVED post-48.3; the byte-eq contract now lives in tests/test_gro_top_byte_equivalence.py, which EXISTS), line 196 (checklist "1846 tests collected"), line 200 (checklist `.planning/phases/48.1-*/baseline_shas.json exists` — stale same way).

Verified NOT drifted (leave alone):
- C-e2e-grompp.sh and G-export-inspection.sh only check pass/fail (`[ "$FAIL" -eq 0 ]`); G's `tests/test_output/test_gromacs_export_hydrate.py::TestMultiGuestWriter` reference still exists.
- ISSUES-FOUND.md lines 105, 203, 204 cite "342 passed" / "1844 passed" — these are DATED historical records ("2026-09-12 re-run" / "2026-09-12 verified"). They describe what was true at that date and do NOT misreport current HEAD. **Leave unchanged** — rewriting them would falsify the record. Note this decision in the summary.
- A broader numeric sweep (328, 331, 338, 342, 395, 414, 1844, 1847, 1854, 1857, 1903) found no other live references in *.sh or README.md.
- The ONLY exact-count pin in all six scripts is E:34 (grep-verified; D:52 checks STALE_COUNT>0 which is a live check, E:63/71 are structural >0 / <120 checks).
- E lines 27-28 run pytest twice per group (A:27/28 same quirk) — pre-existing inefficiency, NOT drift; do NOT "fix".

Known non-issues to NOT touch: E's GATE-SUBSET/GATE-FULL timing notes (~70s / ~225s / ~4 min) are approximate and remain accurate enough after 029 (200.05s full run); only count-bearing text changes.

Constraint reminders: NO production code changes — do not touch `quickice/` or `tests/`. Atomic commits only (stage only intended files, never `git add .` / `-A`). Do NOT update ROADMAP.md or STATE.md (orchestrator handles those). Do NOT run E with RUN_FULL=1 (full suite validated in 029).
</context>

<tasks>

<task type="auto">
  <name>Task 1: Re-pin E-test-refactor.sh count to 1849 and refresh stale README claims</name>
  <files>.planning/uat-workflows/E-test-refactor.sh, .planning/uat-workflows/README.md</files>
  <action>
**Step 0 — re-measure before pinning** (guard against drift since planning):
```bash
python -m pytest --collect-only -q 2>&1 | tail -1
```
Expect `1849 tests collected`. If it differs: confirm 0 collection errors in the full collect output, then pin to the MEASURED value in every target below (same class of fix — drift-detection pin) and record the delta + likely reason prominently in the summary. If collection errors appear, STOP and escalate.

**Step 1 — E-test-refactor.sh (5 edits):**
- Line 31: `# 48.2-1: pytest collects 1846 tests, 0 collection errors (post-48.3 count)` → `# 48.2-1: pytest collects 1849 tests, 0 collection errors (post-quick-029 count; 029 added 3 e2e tests)`
- Line 34: `if [ "$COLLECT_COUNT" -eq 1846 ]; then` → `-eq 1849`
- Line 35: `check "48.2-1 test collection count (1846)" PASS` → `(1849)`
- Line 37: `check "48.2-1 test collection count (got $COLLECT_COUNT, expected 1846)" FAIL` → `expected 1849`
- Line 159: `# Post-48.3: full suite runs headless in ~4 min (1846 collected, 2 pre-existing skips).` → `(1849 collected, 2 pre-existing skips).` — keep "Post-48.3:" prefix and "~4 min" (only the count is stale).

KEEP the exact-count check style (drift detection) — do NOT weaken to a range; no reason found to change it.

**Step 2 — README.md (5 edits, all in the Workflow E section):**
- Line 178: `1. Phase 48.2-1: \`pytest --collect-only\` collects 1846 tests, 0 collection errors` → `1849`
- Line 180: `tests/test_cli/ has 8 files` → `tests/test_cli/ has 10 files` (leave `scancode/ has 18` and `test_output/ has 21` — verified correct)
- Line 186: `9. Phase 48.1-3: baseline_shas.json exists (byte-equivalence baselines captured)` → `9. Phase 48.1-3: byte-eq contract test passes (tests/test_gro_top_byte_equivalence.py)` — mirrors what E:138-148 actually checks
- Line 196: `- [ ] **48.2-1.** \`pytest --collect-only -q\` shows "1846 tests collected" with 0 errors` → `"1849 tests collected"`
- Line 200: `- [ ] **48.1-3.** \`.planning/phases/48.1-*/baseline_shas.json\` exists` → `- [ ] **48.1-3.** \`tests/test_gro_top_byte_equivalence.py\` exists (byte-eq contract test)`

**Do NOT touch:** ISSUES-FOUND.md (dated historical records — see context), C/G/B/A/D scripts, anything in quickice/ or tests/.

**Step 3 — commit (atomic, planning docs only):**
```bash
git add .planning/uat-workflows/E-test-refactor.sh .planning/uat-workflows/README.md
git commit -m "docs(uat-workflows): re-pin E collection count to 1849, refresh stale README claims (post-quick-029)"
```
  </action>
  <verify>
```bash
bash -n .planning/uat-workflows/E-test-refactor.sh && echo SYNTAX-OK
grep -n "1846" .planning/uat-workflows/*.sh .planning/uat-workflows/README.md || echo "NO-LIVE-1846"
grep -n "1849" .planning/uat-workflows/E-test-refactor.sh .planning/uat-workflows/README.md
git show --stat HEAD | head -8
```
Expected: SYNTAX-OK; no 1846 matches in *.sh + README.md (ISSUES-FOUND.md 1844/342 untouched); 1849 present at E:31/34/35/37/159 and README:178/196; HEAD commit touches exactly 2 files.
  </verify>
  <done>E-test-refactor.sh pins the current collection count (1849 or re-measured) with refreshed comments; README Workflow E narrative matches script reality (count, test_cli=10, byte-eq contract test); only the 2 planning files committed.</done>
</task>

<task type="auto">
  <name>Task 2: Dry-run all six scripted workflows (A/B/C/D/E/G) against HEAD; fix drift, record results</name>
  <files>.planning/uat-workflows/*.sh (conditional drift fixes), .planning/quick/030-refresh-uat-workflow-scripts-for-current/030-SUMMARY.md</files>
  <action>
**Step 1 — record gmx mode (informational for C/G):**
```bash
command -v gmx && gmx --version 2>/dev/null | head -1 || echo "gmx NOT on PATH (C/G will self-skip grompp checks)"
```

**Step 2 — dry-run each workflow IN THIS ORDER** (E last-ish so its fix from Task 1 is exercised; external `timeout` guards per AGENTS.md — never rely on pytest-timeout for C-level hangs). Run from repo root, capture output + exit code of each:

```bash
timeout 600  bash .planning/uat-workflows/A-unit-validation.sh;   echo "A exit=$?"
timeout 600  bash .planning/uat-workflows/B-cli-surface.sh;       echo "B exit=$?"
timeout 1800 bash .planning/uat-workflows/C-e2e-grompp.sh;        echo "C exit=$?"
timeout 300  bash .planning/uat-workflows/D-documentation.sh;     echo "D exit=$?"
timeout 900  bash .planning/uat-workflows/E-test-refactor.sh;     echo "E exit=$?"
timeout 900  bash .planning/uat-workflows/G-export-inspection.sh; echo "G exit=$?"
```
E runs with default RUN_FULL=0 (GATE-SUBSET ~70s) — do NOT set RUN_FULL=1 (full suite validated in quick-029: 1847 passed / 2 skipped / 0 failed / 200.05s). C is the long pole (~12 e2e pytest invocations + grompp when gmx present) — let its 1800s guard absorb it; do not run C's inner pytest calls individually unless triaging a failure.

**Step 3 — triage any failure, by class:**
- **Script drift** (stale path, expected string, node ID, or count INSIDE a workflow script) → fix that script minimally, re-run ONLY that workflow, iterate until exit 0. Commit each script fix atomically: `git add .planning/uat-workflows/<fixed>.sh && git commit -m "fix(uat-workflows): <script> — <drift fixed> (quick-030 dry-run)"`.
- **Count-class doc drift surfaced by D** (D greps docs and finds a stale count/version of the same class this task exists to fix, e.g. a doc citing "1846") → fix the doc (docs are NOT production code), re-run D. Commit: `docs(uat-workflows): refresh stale count surfaced by D dry-run (quick-030)`.
- **REAL product/test bug** (workflow fails because code or tests are genuinely broken at HEAD — not a script/reference issue) → STOP that workflow's dry-run immediately. Record the exact command, failing check, and error excerpt in the summary under "Escalations". Do NOT patch quickice/ or tests/. Escalation goes back to the user.
- **Environment/environmental failures** (timeout hit, transient) → note and re-run once with the same guard; if it repeats, treat per the classes above.

**Step 4 — write 030-SUMMARY.md** (path above) containing, at minimum:
1. **Dry-run results table** — one row per workflow: exact command run | exit code | PASS/FAIL | gmx mode (for C/G) | drift fixed (or "none") | escalation (or "none").
2. The Task 1 pin decision (1849 or re-measured value + any delta).
3. The ISSUES-FOUND.md leave-as-is decision (dated historical records).
4. Any escalations with exact failure excerpts.

**Do NOT touch:** quickice/, tests/, ROADMAP.md, STATE.md, ISSUES-FOUND.md. Scripts A/B/C/D/G get edited ONLY if the dry-run proves drift in them.

**Final commit:** `git add .planning/quick/030-refresh-uat-workflow-scripts-for-current/030-SUMMARY.md && git commit -m "docs(quick-030): record A-G UAT workflow dry-run results"`
  </action>
  <verify>
```bash
# All six scripts syntax-clean after any fixes:
for s in A-unit-validation B-cli-surface C-e2e-grompp D-documentation E-test-refactor G-export-inspection; do bash -n .planning/uat-workflows/$s.sh || echo "SYNTAX FAIL: $s"; done; echo BASH-N-DONE
# E passes with default RUN_FULL (the trigger condition is closed):
timeout 900 bash .planning/uat-workflows/E-test-refactor.sh > /tmp/opencode/030-e-rerun.log 2>&1; echo "E rerun exit=$?"; tail -5 /tmp/opencode/030-e-rerun.log
# No production/test changes anywhere in the task:
git status --porcelain | grep -E '^\s*M?\s*(quickice/|tests/)' || echo "NO-PRODUCTION-CHANGES"
# Summary records every workflow:
grep -cE '^\|' .planning/quick/030-refresh-uat-workflow-scripts-for-current/030-SUMMARY.md
```
Expected: BASH-N-DONE with no failures; `E rerun exit=0` with `Failed: 0` in the tail and PASS on the 48.2-1 count check; NO-PRODUCTION-CHANGES; summary contains a row per workflow (≥6 table rows).
  </verify>
  <done>All six scripted workflows dry-run against HEAD with results (command, exit code, PASS/FAIL) recorded in 030-SUMMARY.md; E exits 0 with RUN_FULL=0; every revealed script-drift item fixed and committed atomically; any real product/test bug escalated instead of patched; zero modifications to quickice/ or tests/.</done>
</task>

</tasks>

<verification>
Plan-level checks (run after both tasks):
1. `grep -rn "1846" .planning/uat-workflows/*.sh .planning/uat-workflows/README.md` → no matches (live stale count eliminated; ISSUES-FOUND.md dated 1844/342 intentionally retained).
2. `bash -n .planning/uat-workflows/E-test-refactor.sh` → clean.
3. `timeout 900 bash .planning/uat-workflows/E-test-refactor.sh` (default RUN_FULL=0) → exit 0, `Failed: 0`, count check PASS at 1849.
4. `git log --oneline -5` → pin/refresh commit + summary commit (+ any drift-fix commits), each staging only .planning/ paths.
5. `git status --porcelain` → no quickice/ or tests/ entries.
</verification>

<success_criteria>
- E-test-refactor.sh re-pinned to the current collection count with the exact-count (drift-detection) style preserved, comments/narrative refreshed.
- README.md Workflow E section matches script reality: 1849 collected, tests/test_cli/ = 10 files, byte-eq contract = tests/test_gro_top_byte_equivalence.py (no baseline_shas.json claims).
- All six workflows (A, B, C, D, E, G) dry-run against current HEAD with external timeout guards; per-workflow PASS/FAIL recorded with exact commands in 030-SUMMARY.md; E not run with RUN_FULL=1.
- Every revealed script-drift item fixed and committed atomically; real product/test bugs (if any) escalated, not patched.
- Zero changes to quickice/ or tests/; ROADMAP.md and STATE.md untouched.
- Atomic commits only; planning docs committed (commit_docs: true).
</success_criteria>

<output>
After completion, create `.planning/quick/030-refresh-uat-workflow-scripts-for-current/030-SUMMARY.md` (dry-run results table + decisions + escalations, per Task 2 Step 4).
</output>
