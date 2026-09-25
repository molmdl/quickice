---
phase: 030-refresh-uat-workflow-scripts-for-current
plan: 030
subsystem: uat-workflow-hygiene
tags: [uat, test-count, dry-run, drift-fix]
requires: [quick-029]
provides: [E-repin-1849, readme-refresh, A-G-dry-run-verification]
affects: [manual-uat-redo]
tech-stack:
  added: []
  patterns: [exact-count drift-detection pin preserved in E-test-refactor.sh]
key-files:
  created: [.planning/quick/030-refresh-uat-workflow-scripts-for-current/030-SUMMARY.md]
  modified: [.planning/uat-workflows/E-test-refactor.sh, .planning/uat-workflows/README.md]
decisions:
  - "E count pin set to 1849 (re-measured live before pinning; matches orchestrator measurement — no delta)"
  - "Exact-count (-eq) drift-detection style kept — not weakened to a range"
  - "ISSUES-FOUND.md left unchanged (dated historical records)"
  - "E kept on default RUN_FULL=0 (full suite already validated in quick-029)"
metrics:
  duration: "~20 min"
  completed: 2026-09-25
---

# Phase 030 Plan 030: Refresh UAT Workflow Scripts for Current Summary

**One-liner:** Re-pinned E-test-refactor.sh collection-count to 1849 (post-quick-029), refreshed stale README Workflow-E claims (count, test_cli=10 files, baseline_shas.json → byte-eq contract test), then dry-ran all six scripted workflows (A/B/C/D/E/G) against HEAD — all PASS, zero further drift, zero escalations.

## Task 1 Pin Decision

Re-measured before pinning per plan Step 0:

- `python -m pytest --collect-only -q` → **1849 tests collected in 1.08s**, 0 collection errors.
- Orchestrator planning measurement was 1849 → **no delta**. Pin set to 1849.

Edits applied (exactly per plan):
- `E-test-refactor.sh`: line 31 comment, line 34 `-eq 1849` pin, line 35 PASS label, line 37 FAIL label, line 159 comment (kept "Post-48.3:" prefix and "~4 min"; kept "2 pre-existing skips" — still true). Exact-count drift-detection style preserved.
- `README.md`: line 178 (collects 1849), line 180 (test_cli 8 → 10 files; scancode=18 / test_output=21 verified correct and left), line 186 (baseline_shas.json claim → `tests/test_gro_top_byte_equivalence.py` byte-eq contract test, mirroring E:138-148), line 196 (checklist 1849), line 200 (checklist baseline_shas.json → byte-eq contract test).

Commit: `0ad4699e` — "docs(uat-workflows): re-pin E collection count to 1849, refresh stale README claims (post-quick-029)" (2 files, planning docs only).

## ISSUES-FOUND.md Leave-As-Is Decision

ISSUES-FOUND.md lines 105, 203, 204 cite "342 passed" / "1844 passed". These are **dated historical records** ("2026-09-12 re-run" / "2026-09-12 verified") describing what was true at that date. They do NOT misreport current HEAD, and rewriting them would falsify the record. **Left unchanged**, per plan. File not touched in any commit from this task.

## Dry-Run Results (all against current HEAD, gmx available on PATH: GROMACS 2023.5-plumed_2.9.3 → C/G ran WITH real grompp checks, no self-skip mode)

| Workflow | Exact command | Exit code | PASS/FAIL (checks) | gmx mode | Drift fixed | Escalation |
|---|---|---|---|---|---|---|
| A: Unit Validation | `timeout 600 bash .planning/uat-workflows/A-unit-validation.sh` | 0 | PASS (7/0/0) | n/a | none | none |
| B: CLI Surface | `timeout 600 bash .planning/uat-workflows/B-cli-surface.sh` | 0 | PASS (7/0/0) | n/a | none | none |
| C: E2E Generation & Grompp | `timeout 1800 bash .planning/uat-workflows/C-e2e-grompp.sh` | 0 | PASS (13/0/0) | gmx present → full grompp checks ran (no self-skip) | none | none |
| D: Documentation | `timeout 300 bash .planning/uat-workflows/D-documentation.sh` | 0 | PASS (28/0/0) | n/a | none | none |
| E: Test Suite & Refactor | `timeout 900 bash .planning/uat-workflows/E-test-refactor.sh` | 0 | PASS (13/0/0) | n/a | count pin 1849 (Task 1, pre-dry-run) | none |
| G: Export Inspection | `timeout 900 bash .planning/uat-workflows/G-export-inspection.sh` | 0 | PASS (6/0/0) | gmx present → grompp rc=0 check ran ("42-3 mixed hydrate grompp rc=0 PASS") | none | none |

E was run with **default RUN_FULL=0** (GATE-SUBSET) — RUN_FULL=1 was NOT set; full suite remains validated by quick-029 (1847 passed / 2 skipped / 0 failed / 200.05s).

Key verification highlights:
- E `48.2-1 test collection count (1849)` → **PASS** (trigger condition closed — no spurious count-pin failure).
- E GATE-SUBSET (tests/e2e + byte-eq) → PASS.
- C custom guest GUI + CLI grompp checks → PASS with real gmx.
- G mixed-hydrate grompp rc=0 → PASS with real gmx.

## Escalations

**None.** No workflow failed; no REAL product/test bug surfaced. Zero changes to `quickice/` or `tests/`.

## Deviations from Plan

None — plan executed exactly as written. Re-measured count (1849) matched the plan's expected value; no drift-fix commits beyond the planned Task 1 pin/refresh commit were required.

## Next Readiness

The UAT workflow scripts now reflect current HEAD: E exits 0 with RUN_FULL=0, all six scripted workflows PASS with exact commands recorded above, and no live stale 1846 reference remains in `*.sh` or `README.md`. The user's manual full-workflow UAT redo will not hit spurious failures from stale counts.
