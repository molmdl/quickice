# Scancode Analysis Status

**Updated:** 2026-05-22

## Codebase Mapping (Refreshed 2026-05-22)

7 documents in `.planning/codebase/` (2528 total lines including verification):
- STACK.md (158), ARCHITECTURE.md (191), STRUCTURE.md (370)
- CONVENTIONS.md (361), TESTING.md (378), INTEGRATIONS.md (153)
- CONCERNS.md (317), CONCERNS_VERIFICATION.md (600)

## Concerns Verification Summary

| Result | Count | Details |
|--------|-------|---------|
| Confirmed | 26 | Real issues still present |
| Fixed | 5 | Addressed by QT-021, 022, 026, 027 |
| False Alarm | 1 | TD-04 (duplicate comment lines) — misidentified |
| Partially Fixed | 4 | PERF-03, BUG-02, SCI-04, EXC-01 |
| Escalated | 1 | BUG-01 (OW safeguard missing in BOTH pocket.py and piece.py) |
| Duplicate | 1 | PERF-04 = TD-06 |

## Priority Action Items

1. **BUG-01 ESCALATED** — OW-safeguard missing in pocket.py AND piece.py (water misclassified as guests)
2. **EXC-02** — Silent FileNotFoundError for guest ITP files → broken exports with no user warning
3. **BUG-03** — O(n²) molecule_index.index() in gromacs_writer.py:1102
4. **TEST-01, TEST-05** — No end-to-end export test, no overlap-removal invariant

## Scancode Item Status (A–E)

| Item | Description | Previous Reports | Current Status |
|------|-------------|------------------|----------------|
| A | Function/data flow trace for GROMACS export | `.planning/code_analysis/20260512_gromacs_flow_trace.md` | Needs refresh after v4.5 changes |
| B | Vulnerability/safety/performance scan | `.planning/code_analysis/20260512_153657_vulnerability_scan.md`, CONCERNS.md, CONCERNS_VERIFICATION.md | Refreshed & verified (26 confirmed / 5 fixed / 1 false alarm) |
| C | Documentation cross-check & citation suggestions | `.planning/code_analysis/20260512_154906_documentation_crosscheck.md`, `20260516_documentation_issues_verification.md` | Partially addressed (QT-024,025,026,028) |
| D | Dead code identification | `.planning/code_analysis/20260512_155106_dead_code.md`, `20260512_dead_code_verification.md` | Partially addressed (QT-021 removed build_molecule_index) |
| E | Portable distribution & PyInstaller optimization | `.planning/code_analysis/2026-05-12_portable_distribution.md`, `PACKAGING_2026-05-02.md` | Partially addressed (QT-008,023; UPX pending) |
