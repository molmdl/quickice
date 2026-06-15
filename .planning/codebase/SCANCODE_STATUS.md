# Scancode Analysis Status

**Updated:** 2026-06-15 (post-Phase 37 refresh)

## Codebase Mapping (Refreshed 2026-06-15)

7 documents in `.planning/codebase/` (2051 total lines):
- STACK.md (135), ARCHITECTURE.md (219), STRUCTURE.md (350)
- CONVENTIONS.md (378), TESTING.md (591), INTEGRATIONS.md (189)
- CONCERNS.md (189)

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
| 7 TEST-02 | Pocket edge cases (51 tests) + cubic bug fix | 925489e, c30c870, 6a43594 |
| 8 Phase 34.7 | BUG-05, MW-01, DEFLT-01, RNG-01, ATOM-01, TREE-01, GUEST-01 | 6965961, ee0f4d5, 8726698, f44c22c, 6d04262 |
| 9 Phase 34.8 | PERF-02, BUG-04, TEST-09 | per-plan commits |
| 10 Phase 36-37 | CLI pipeline, unified entry point, workflow scripts | per-plan commits |

## Issue Status Summary

| Status | Count |
|--------|-------|
| Fixed | 57+ |
| Deferred (design needed) | 6 |
| Ignored (SEC-02) | 1 |
| **Total** | **64+** |

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

## Scancode Item Status (A–D)

| Item | Description | Latest Report | Current Status |
|------|-------------|---------------|----------------|
| A | Function/data flow trace for GROMACS export | `20260615_gromacs_flow_trace.md` (547 lines) | DONE — includes CLI pipeline + unified entry point routing (new) |
| B | Vulnerability/safety/performance scan | `20260615_vulnerability_scan.md` (393 lines) | DONE — 31 findings incl. CLI pipeline duck-typing, PBC wrapping gaps |
| C | Documentation cross-check & citation suggestions | `20260615_documentation_crosscheck_cli.md` (521 lines), `20260615_documentation_crosscheck_gui.md` (358 lines) | DONE — split CLI/GUI; 28 CLI findings + 18 GUI findings |
| D | Portable distribution & PyInstaller optimization | `20260615_portable_distribution.md` (816 lines) | DONE — scipy/genice2 collect_all bloat identified (~230-260 MB savings potential) |

## Key New Findings (2026-06-15 Scan)

### Vulnerability Scan (Item B)
- **AN-03** (HIGH): `write_ion_gro_file` writes solute/custom molecule positions without PBC wrapping
- **CP-01** (HIGH): Duck-typing attribute propagation on `InterfaceStructure` — breaks if `__slots__` added
- **UM-01** (MEDIUM): Avogadro constant hardcoded in CLI pipeline instead of shared constant

### Documentation Cross-Check (Item C - CLI)
- 7 hydrate commands in `scripts/cli-examples.sh` missing required `-T`/`-P` flags
- `docs/cli-reference.md` completely missing 18 v4.5 pipeline flag definitions
- `--gromacs` is no-op in pipeline mode (misleading)

### Documentation Cross-Check (Item C - GUI)
- Interface panel tooltips reference wrong tab numbers (pre-Phase 34.3 numbering)
- Solute tooltip says THF is "4-membered ring" — it's 5-membered
- Custom molecule tooltip says "no overlap checking" but code implements overlap detection
- `docs/principles.md` still says "rewards unique seeds" for diversity score (outdated)

### Portable Distribution (Item D)
- scipy `collect_all` = #1 bloat source (113 MB, only spatial+interpolate needed)
- GenIce2 `collect_all` pulls 254 lattice plugins when only 11 used
- CLI-only binary would save ~106 MB (excludes PySide6+VTK)
- Total potential savings: ~230-260 MB (871→610-640 MB)

---

*Status updated: 2026-06-15 — Phase 37 complete, all scancode items A-D refreshed*
