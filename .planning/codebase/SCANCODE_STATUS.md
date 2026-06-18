# Scancode Analysis Status

**Updated:** 2026-06-18 (post-Phase 34.9/37.1 refresh)

## Codebase Mapping (Refreshed 2026-06-18)

7 documents in `.planning/codebase/` (2176 total lines):
- STACK.md (193), ARCHITECTURE.md (246), STRUCTURE.md (377)
- CONVENTIONS.md (397), TESTING.md (517), INTEGRATIONS.md (247)
- CONCERNS.md (199)

## Fix Batches Applied

| Batch | Fixes | Commit(s) |
|-------|-------|-----------|
| 1 CRITICAL | FLOW-01/02/03, BUG-01, EXC-02, MOL-1/2/3/4 | d75dde1, 5e18c0e, b90c2e3 |
| 2 HIGH | KS-1/2/3, MOL-5, FF-1 | a9ed3de |
| 3 MEDIUM | BUG-03, FRAG-01/02, UNIT-01, EXP-1/2, VER-1, CIT-GAFF2 | 80753c5 |
| 4 LOW | BUG-02a/b/c, NEW-01/02, SCI-01/03/04, UNIT-03, TD-06, FRAG-04 | f217c6d, 95a6b8c, 9fa898f |
| 5 Security | SEC-01, BUNDLE-01 | 22bd382 |
| 6A Test Gaps | TEST-04, TEST-05 | 687fdad |
| 6B TEST-01 | E2E GROMACS export tests (37 tests) | separate session |
| 7 TEST-02 | Pocket edge cases (51 tests) + cubic bug fix | 925489e, c30c870, 6a43594 |
| 8 Phase 34.7 | BUG-05, MW-01, DEFLT-01, RNG-01, ATOM-01, TREE-01, GUEST-01 | 6965961, ee0f4d5, 8726698, f44c22c, 6d04262 |
| 9 Phase 34.8 | PERF-02, BUG-04, TEST-09 | per-plan commits |
| 10 Phase 36-37 | CLI pipeline, unified entry point, workflow scripts | per-plan commits |
| 11 Phase 34.9 | TIP4P-ICE LJ bugfix, comb-rule revert to 2 | per-plan commits |
| 12 Phase 37.1 | 15 plans: AN-01/02/03, V-02/05/07/17, UM-01/02/03, CP-03, SEC-02, EH-01/02/05, DOC fixes | per-plan commits |

## Issue Status Summary

| Status | Count |
|--------|-------|
| Fixed | 75+ |
| Deferred (design needed) | 6 |
| Ignored (SEC-02) | 1 |
| **Total** | **82+** |

## Remaining Deferred Items

| ID | Issue | Decision Needed |
|----|-------|-----------------|
| FRAG-03 | Split gromacs_writer.py into per-structure modules | Architecture refactor |
| TD-05 | np.random global state (not thread-safe) | GenIce2 dependency |
| BUNDLE-02 | collect_all('genice2') includes unused plugins | Runtime investigation |
| TD-01 | Duplicate functions across slab/pocket/piece | Consolidation refactor |
| TD-07 | No upload-time atomtypes warning | UX decision |
| UNIT-02 | Fallback density no GUI indicator | GUI architecture |

**Previously deferred, now resolved:**
| ID | Resolution |
|----|------------|
| BUG-04 | Resolved (Phase 34.8-03): O-O histogram fingerprint replaces seed-based diversity_score |
| PERF-02 | Resolved (Phase 34.8-01): cKDTree(boxsize=) for orthorhombic PBC |
| EXC-01 | Resolved (Phase 36): CLI pipeline has stderr progress reporting |
| CP-01 | Accepted as design decision (Phase 37.1): Duck-typing documented, not fixed |
| AN-01 | Resolved (Phase 37.1-01): MOLECULE_TYPE_INFO["ice"]["atoms"] = 4 |
| AN-02 | Resolved (Phase 37.1-02): MW from wrapped positions |
| AN-03 | Partially resolved (Phase 37.1-02/14): write_interface_gro_file wraps; write_solute_gro_file may still miss |
| UM-01 | Resolved (Phase 37.1-10): AVOGADRO consolidated |
| V-02 | Resolved (Phase 37.1-08): cKDTree conditional rebuild |
| V-05 | Resolved (Phase 37.1-08): Unknown atom molecule_index entry + warning |
| V-07 | Resolved (Phase 37.1-09): detect_atoms_per_molecule deduplicated to types.py |
| V-17 | Resolved (Phase 37.1-09): Mutation-free solute inserter |
| UM-02 | Resolved (Phase 37.1-10): WATER_VOLUME_NM3 constant |
| UM-03 | Resolved (Phase 37.1-10): molecule-count volume replaces water_fraction heuristic |
| CP-03 | Resolved (Phase 37.1-11): concentration/occupancy range validation |
| SEC-02 | Resolved (Phase 37.1-11): .gro/.itp file extension validation |
| EH-01 | Resolved (Phase 37.1-12): GRO file I/O try/except protection |
| EH-02 | Resolved (Phase 37.1-12): Hydrate wrapper atom count assertion |
| EH-05 | Resolved (Phase 37.1-12): (ValueError, OSError) not bare Exception |

## Scancode Item Status (A–D)

| Item | Description | Latest Report | Current Status |
|------|-------------|---------------|----------------|
| A | Function/data flow trace for GROMACS export | `20260618_gromacs_flow_trace.md` (1510 lines) | DONE — full trace with dual PBC wrapping, TIP4P-ICE LJ constants, conditional cKDTree, mutation-free inserter |
| B | Vulnerability/safety/performance scan | `20260618_vulnerability_scan.md` (540 lines) | DONE — 10/13 fixes verified, 11 NEW issues found (2 HIGH: solute PBC gap, custom GRO writer) |
| C-CLI | Documentation cross-check (CLI) | `20260618_documentation_crosscheck_cli.md` (394 lines) | DONE — 18/28 prior fixed, 10 remain, 8 new (1 CRITICAL: wrong Madrid2019 DOI) |
| C-GUI | Documentation cross-check (GUI) | `20260618_documentation_crosscheck_gui.md` (331 lines) | DONE — 12/18 prior fixed, 6 remain, 4 new (1 MEDIUM: "Insert Molecule" vs "Generate Custom Molecules") |
| D | Portable distribution & PyInstaller optimization | `20260618_portable_distribution.md` (639 lines) | DONE — no new deps; scipy savings revised 113→26 MB; 27 MB test data leak; revised total ~118 MB GUI savings |

## Key New Findings (2026-06-18 Scan)

### Vulnerability Scan (Item B)
- **NEW-B01** (HIGH): `write_solute_gro_file` may not PBC-wrap solute/custom positions (AN-03 only fixed in write_interface_gro_file)
- **NEW-B02** (HIGH): Custom GRO writer EH-01 may not catch all I/O failures
- **NEW-B03** (MEDIUM): scipy cKDTree loads linalg/sparse/special at runtime — cannot fully exclude scipy submodules
- 8 additional MEDIUM/LOW findings (see report)

### Documentation Cross-Check (Item C - CLI)
- **NEW-C01** (CRITICAL): `docs/cli-reference.md:930` has wrong Madrid2019 DOI (`10.1021/acs.jctc.9b00902` → 404, doesn't exist). **AND** `README.md:371,375` also have wrong DOI (`10.1063/1.5121394` → points to wrong paper about misinformation on networks). Correct DOI verified: `10.1063/1.5121392` (resolves to Zeron et al. 2019, J. Chem. Phys. 151, 134504).
- **NEW-C02** (MEDIUM): `--occupancy` range documentation inconsistent (code says 0-100%, docs say 0-1)
- 6 additional MEDIUM/LOW findings (see report)

### Documentation Cross-Check (Item C - GUI)
- **NEW-CG01** (MEDIUM): help_dialog + gui-guide say "Insert Molecule" but button text is "Generate Custom Molecules" (introduced by 37.1-13 fix)
- 3 additional LOW findings (see report)

### Portable Distribution (Item D)
- **NEW-D01**: 27.2 MB of test data leaking into bundle (excludes pattern fails with collect_all)
- **NEW-D02**: scipy.optimize._highspy (6.9 MB) unnecessary — never called by QuickIce
- **CORRECTION**: scipy savings revised from ~113 MB → ~26 MB (cKDTree runtime deps)
- **BUG FIX**: June 15 report missed genice2.lattices.sI and genice2.lattices.sII in hiddenimports
- **Revised total savings**: ~118 MB GUI / ~224 MB CLI (down from 230-260 MB)

---

*Status updated: 2026-06-18 — Phase 34.9/37.1 complete, all scancode items A-D refreshed*
