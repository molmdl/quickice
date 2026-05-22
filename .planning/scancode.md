after codebase scanning, spawn additional codebase mapper subagents for the additional tasks of read-only analysis, output each report into timestamped file in .planning/code_analysis. do not fix yet, I will start new debug session or urgent phase insertion or quick task for the fix.

## Status (updated 2026-05-22)

**Codebase mapping:** REFRESHED 2026-05-22 — 7 documents in .planning/codebase/ (1928 total lines)
**Concerns verification:** COMPLETED 2026-05-22 — CONCERNS_VERIFICATION.md (600 lines)

| Item | Description | Previous Reports | Current Status |
|------|-------------|------------------|----------------|
| A | Function/data flow trace for GROMACS export | .planning/code_analysis/20260512_gromacs_flow_trace.md | Needs refresh after v4.5 changes |
| B | Vulnerability/safety/performance scan | .planning/code_analysis/20260512_153657_vulnerability_scan.md, .planning/codebase/CONCERNS.md, .planning/codebase/CONCERNS_VERIFICATION.md | CONCERNS.md refreshed, verified 26 confirmed / 5 fixed / 1 false alarm |
| C | Documentation cross-check & citation suggestions | .planning/code_analysis/20260512_154906_documentation_crosscheck.md, 20260516_documentation_issues_verification.md | Partially addressed (QT-024,025,026,028) |
| D | Dead code identification | .planning/code_analysis/20260512_155106_dead_code.md, 20260512_dead_code_verification.md | Partially addressed (QT-021 removed build_molecule_index) |
| E | Portable distribution & PyInstaller optimization | .planning/code_analysis/2026-05-12_portable_distribution.md, PACKAGING_2026-05-02.md | Partially addressed (QT-008,023; UPX pending) |

## Priority Action Items (from verification)

1. **BUG-01 ESCALATED** — OW-safeguard missing in pocket.py AND piece.py (water misclassified as guests)
2. **EXC-02** — Silent FileNotFoundError for guest ITP files (broken exports, no warning)
3. **BUG-03** — O(n²) molecule_index.index() in gromacs_writer.py:1102
4. **TEST-01, TEST-05** — No end-to-end export test, no overlap-removal invariant

---

## Original Requirements

A. do a read-only trace of the function and data flow in the code, to generate the full flowchart of each funtion call before a success gromacs export. see the workflows for read-only test in @.planning/uat/v4.5-batch-testing-checklist.md **do not edit it, this uat is for human, I ask u to do read-only check before I test myself.**
B. for all the codes in this repo, critically scan the code and trace the logic of different options to identift vunlability, suspecious code, or issues leading to safety concerns or performance lost. do not run anything.
pay specific attention to any nested for-loops, unit mismatch and atom number mismatch, and any bugs you can identify.
C. For the documentation, cross-check for consistency with the code, and suggest possible citation to add.
D. identify dead code in the codebase
E. identify the necessary lib to be packaged into a portable distribution and suggest how to change the pyinstaller script in scripts to reduce bundled size
