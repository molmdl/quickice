# Scancode Analysis Status

**Updated:** 2026-05-22 (post-fix refresh)

## Codebase Mapping (Refreshed 2026-05-22)

7 documents in `.planning/codebase/` (1854 total lines):
- STACK.md (131), ARCHITECTURE.md (208), STRUCTURE.md (343)
- CONVENTIONS.md (327), TESTING.md (458), INTEGRATIONS.md (167)
- CONCERNS.md (220)

## Fix Batches Applied

| Batch | Fixes | Commit(s) |
|-------|-------|------------|
| 1 CRITICAL | FLOW-01/02/03, BUG-01, EXC-02, MOL-1/2/3/4 | d75dde1, 5e18c0e, b90c2e3 |
| 2 HIGH | KS-1/2/3, MOL-5, FF-1 | a9ed3de |
| 3 MEDIUM | BUG-03, FRAG-01/02, UNIT-01, EXP-1/2, VER-1, CIT-GAFF2 | 80753c5 |
| 4 LOW | BUG-02a/b/c, NEW-01/02, SCI-01/03/04, UNIT-03, TD-06, FRAG-04 | f217c6d, 95a6b8c, 9fa898f |
| 5 Security | SEC-01, BUNDLE-01 | 22bd382 |
| 6A Test Gaps | TEST-04, TEST-05 | 687fdad |
| 6B TEST-01 | E2E GROMACS export tests (37 tests) | separate session |
| 7 TEST-02 | Pocket edge cases (51 tests) + cubic bug fix | 925489e, c30e870, 6a43594 |

## Issue Status Summary

| Status | Count |
|--------|-------|
| Fixed | 44 |
| Deferred (design needed) | 9 |
| Ignored (SEC-02) | 1 |
| **Total** | **54** |

## Remaining Deferred Items

| ID | Issue | Decision Needed |
|----|-------|-----------------|
| FRAG-03 | Split gromacs_writer.py into per-structure modules | Architecture refactor |
| BUG-04 | diversity_score() always returns 1.0 | New algorithm design |
| TD-05 | np.random global state (not thread-safe) | GenIce2 dependency |
| BUNDLE-02 | collect_all('genice2') includes unused plugins | Runtime investigation |
| TD-01 | Duplicate functions across slab/pocket/piece | Consolidation refactor |
| TD-07 | No upload-time atomtypes warning | UX decision |
| PERF-02 | 27× supercell → cKDTree(boxsize=) | Verification needed |
| UNIT-02 | Fallback density no GUI indicator | GUI architecture |
| EXC-01 | IAPWS failures no visual indicator | Matplotlib changes |

## Scancode Item Status (A–E)

| Item | Description | Reports | Current Status |
|------|-------------|---------|----------------|
| A | Function/data flow trace for GROMACS export | `20260512_gromacs_flow_trace.md`, `20260522_gromacs_flow_trace.md` | DONE — full E2E chain traced, tests written |
| B | Vulnerability/safety/performance scan | `20260512_153657_vulnerability_scan.md`, CONCERNS.md | DONE — 44 fixes applied, 9 deferred |
| C | Documentation cross-check & citation suggestions | `20260522_documentation_crosscheck.md`, `20260522_citation_inventory.md` | DONE — 20 doc issues + 10 citation issues identified |
| D | Dead code identification | `20260512_155106_dead_code.md`, `20260512_dead_code_verification.md` | PARTIAL — build_molecule_index removed, NEW-02 dead imports removed |
| E | Portable distribution & PyInstaller optimization | `2026-05-12_portable_distribution.md`, `PACKAGING_2026-05-02.md` | PARTIAL — BUNDLE-01 excludes added, BUNDLE-02 deferred |
