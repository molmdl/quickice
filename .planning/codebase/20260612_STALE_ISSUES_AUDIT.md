# Stale Issues Audit — 2026-06-12

**Auditor:** OpenCode (gsd-map-codebase)
**Method:** Read every issue in `.planning/codebase/`, verified each against actual source code and git history. Read all 7 pending todos. Cross-referenced with Phase 34.7 commits (6965961, ee0f4d5, 8726698, f44c22c, 6d04262) and earlier fix batches (d75dde1, 5e18c0e, b90c2e3, a9ed3de, 80753c5, 22bd382, 9e002b4, 925489e).

---

## Issues Now Fixed (should be marked as resolved)

These issues are still documented as open/unresolved in `.planning/codebase/` files, but the **actual codebase** shows they have been fixed. Future agents will waste time re-discovering them if not updated.

### From `20260608_ISSUES_VERIFICATION.md` (ALL 7 active issues now fixed)

| Issue ID | Original Finding | How Fixed | Evidence (current code) |
|----------|------------------|-----------|-------------------------|
| BUG-05 | `h2_pos[2]` instead of `h1_pos[2]` at gromacs_writer.py:1971 | Phase 34.7-01, commit 6965961 | Line 1979: `h1_pos[2]` ✅ (all HW1 lines now use `h1_pos[2]`) |
| MW-01 | Ice GRO writer used atom-level wrapping (split molecules at PBC) | Phase 34.7-01, commit 6965961 | Line 463: `wrap_molecules_into_box()` now used for ice writer ✅ |
| RNG-01 | Unseeded `random.Random()` and `Rotation.random()` in CustomMoleculeInserter | Phase 34.7-02, commit ee0f4d5 | Line 81: `self.rng = random.Random(seed)`, Line 611: `Rotation.random(random_state=self.seed)` ✅ |
| ATOM-01 | Hardcoded `// 4` and `count=4` for water atoms | Phase 34.7-02, commit 8726698 | All instances now use `WATER_ATOMS_PER_MOLECULE` constant from types.py ✅ |
| TREE-01 | KDTree rebuilt every iteration even on overlap rejection | Phase 34.7-03, commit f44c22c | Line 362: `ion_tree = None` init, Line 388: rebuild only after `ion_positions.append()` ✅ |
| GUEST-01 | CO2 misidentified as THF; dead CO2 code unreachable | Phase 34.7-08, commit 6d04262 | `count_guest_atoms()` now accepts `guest_type` parameter; dead CO2 handler removed ✅ |
| DEFLT-01 | fudgeLJ=0.0 in ion/custom/solute writers vs 0.5 in others | Phase 34.7-01, commit 6965961 | All 6 writers now use `fudgeLJ=0.5, fudgeQQ=0.8333` ✅ |

**Note:** IDX-01 was already REFUTED in the original report — no action needed.

### From `ISSUES_VERIFICATION.md` (issues verified 2026-05-22, now fixed)

| Issue ID | Original Finding | How Fixed | Evidence |
|----------|------------------|-----------|---------|
| FLOW-01 | SoluteGROMACSExporter used wrong writers (crash bugs) | Fix batch 1, commit 5e18c0e+d75dde1 | `export.py` lines 82-87: now uses `write_solute_gro_file`/`write_solute_top_file` ✅ |
| FLOW-02 | CustomMoleculeGROMACSExporter missing tip4p-ice.itp copy | Fix batch 1, commit 5e18c0e | `export.py` lines 230-234: `shutil.copy(water_itp_source, water_itp_dest)` ✅ |
| FLOW-03 | Custom molecule GRO writer hardcoded "GUE" residue | Fix batch 1, commit 5e18c0e | `gromacs_writer.py` line 774: `detect_guest_type_from_atoms()` used ✅ |
| BUG-01 | OW-safeguard missing in pocket.py and piece.py | Fix batch 1, commit 5e18c0e | `pocket.py:75`, `piece.py:90`: `has_ow` check present ✅ |
| EXC-02 | Silent `FileNotFoundError: pass` in export.py | Fix batch 1, commit 5e18c0e | `export.py` lines 119-120, 249-250, 369-370: `QMessageBox.warning()` ✅ |
| MOL-1 | README.md uses CH4_HYD/THF_LIQ | Fix batch 1, commit 5e18c0e | `README.md:194-195`: `CH4_H` and `THF_L` ✅ |
| MOL-2/3 | gui-guide.md uses CH4_LIQ/THF_LIQ and CH4_HYD/THF_HYD | Fix batch 1, commit 5e18c0e | `gui-guide.md:711,713`: `CH4_L`/`THF_L` and `CH4_H`/`THF_H` ✅ |
| MOL-4 | gui-guide.md says ch4.itp/thf.itp | Fix batch 1, commit 5e18c0e | `gui-guide.md:300`: `ch4_hydrate.itp`/`thf_hydrate.itp` ✅ |
| MOL-5 | README.md says ch4.itp/thf.itp | Fix batch 1, commit 5e18c0e | (Part of MOL-4 fix) ✅ |
| FF-1 | gui-guide.md says "GAFF" instead of "GAFF2" | Fix batch 2, commit a9ed3de | `gui-guide.md:257-258,300,631-634`: all say "GAFF2" ✅ |
| KS-1 | Missing Ctrl+Alt+P, Ctrl+L, Ctrl+M in shortcuts table | Fix batch 2, commit a9ed3de | `gui-guide.md:207,214-215`: all three present ✅ |
| KS-2 | Ctrl+S description outdated ("Save PDB from left viewer") | Fix batch 2, commit a9ed3de | `gui-guide.md:163,206`: "Save/Export from active tab (unified)" ✅ |
| KS-3 | gui-guide.md says Ctrl+E for hydrate export | Fix batch 2, commit a9ed3de | `gui-guide.md`: No remaining `Ctrl+E` references ✅ |
| VER-1 | cli-reference.md says version 4.0.0 | Fix batch 3, commit 80753c5 | `cli-reference.md:145`: `4.5.0` ✅ |
| BUG-02 | types.py says THF has 12 atoms (should be 13) | Fix batch 4, commit f217c6d | `types.py:17`: `"atoms": 13` ✅ |
| BUG-02b | gromacs_writer.py comment says "C5H8O (14 atoms)" | Fix batch 4, commit f217c6d | `gromacs_writer.py:850`: `"C4H8O (4 C, 8 H, 1 O = 13 atoms)"` ✅ |
| BUG-02c | molecule_utils.py comment says "C5H8O = 14 atoms" | Fix batch 4, commit f217c6d | `molecule_utils.py:112`: `"C4H8O = 13 atoms"` ✅ |
| BUG-03 | `molecule_index.index(mol)` O(n²) in loop | Fix batch 3, commit 80753c5 | `gromacs_writer.py:1102`: `for res_idx, mol in enumerate(molecule_index)` ✅ |
| NEW-01 | Verbose debug logging at logger.info() level | Fix batch 4, commit 95a6b8c | `main_window.py:1221-1243`: now `logger.debug()` ✅ |
| NEW-02 | Dead import of MOLECULE_TYPE_INFO | Fix batch 4, commit f217c6d | `gromacs_writer.py`: no MOLECULE_TYPE_INFO import; `hydrate_generator.py`: no MOLECULE_TYPE_INFO import ✅ |
| SCI-04 | Generated ion.itp lacks Madrid2019_085 header | Fix batch 4 + e2e-compute-export | `gromacs_ion_export.py:40`: `; Madrid2019_085 ion model (Zeron et al., J. Chem. Phys. 2019)` ✅ |
| SCI-1/DOC | AVOGADRO inconsistency (6.022e23 vs 6.02214076e23) | Fix batch 4, commit f217c6d | `scorer.py:168`: `6.02214076e23` matches `solute_inserter.py:33` ✅ |
| SCI-03 | 0.276 nm and 0.35 nm lack literature citations | Fix batch 4, commit f217c6d | `types.py:21`: `Petrenko & Whitworth, 1999, Physics of Ice`; `ranking.md:31`: same citation ✅ |
| UNIT-01 | gro_parser.py no coordinate range validation | Fix batch 3, commit 80753c5 | `gro_parser.py:59-64`: `if max_coord > 50.0: raise ValueError(...)` ✅ |
| UNIT-03 | Suppressed IAPWS extrapolation warnings, no logging | Fix batch 4, commit 95a6b8c | `water_density.py:76`: `logger.debug(f"Using extrapolated IAPWS-95 value at T={T_K}K, P={P_MPa}MPa")` ✅ |
| CIT-GAFF2 | README.md missing formal GAFF2 citation | Fix batch 3, commit 80753c5 | `README.md:334-335`: Wang et al. (2004) and He et al. (2020) ✅ |
| SEC-01 | Path(args.output) without sanitization | Fix batch 5, commit 22bd382 | `main.py:127,194`: `Path(args.output).resolve()` ✅ |
| SEC-02 | shell=True in v1.0-run_uat_tests.py | Fix: commit 9e002b4 | `.planning/milestones/v1.0-run_uat_tests.py:32-38`: `subprocess.run(command, ...)` without `shell=True` ✅ |
| BUNDLE-01 | PyInstaller excludes=[] missing | Fix batch 5, commit 22bd382 | `quickice-gui.spec:27`: `excludes=['*/tests/*', '*/test/*', '*/docs/*', ...]` ✅ |
| TD-06 | Module-level mutable globals without thread safety | Fix batch 4, commit 95a6b8c | `water_filler.py:12,216`: `@lru_cache(maxsize=1)`; `hydrate_generator.py:28`: `threading.Lock()` ✅ |
| FRAG-01 | Cross-tab getattr without assertions | Partially fixed: batch 3 | Debug logging moved to `logger.debug()`, but `hasattr`/`getattr` patterns still present in `main_window.py` ⚠️ |
| FRAG-02 | Missing invariant check after overlap removal | Fix batch 3 + pocket-edge-tests | `slab.py:386,570`, `pocket.py:345,497,535`: assertions added ✅ |
| EXC-03 | Three export handlers missing traceback.print_exc() | Quick Task 027, commit 719de7f | `export.py`: all 5 export handlers now have `traceback.print_exc()` ✅ |
| EXP-1 | Wrong hydrate filename pattern in gui-guide.md | Fix batch 3, commit 80753c5 | `gui-guide.md:298`: `hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro` ✅ |
| EXP-2 | Wrong solute filename pattern in gui-guide.md | Fix batch 3, commit 80753c5 | `gui-guide.md:707`: `solute_{type}_{count}molecules.gro` ✅ |
| FRAG-04 (validator) | Hardcoded GENERIC_RESIDUE_NAMES too small | Fix batch 4, commit 95a6b8c | `molecule_validator.py:18`: expanded to `{"MOL", "UNK", "LIG", "XXX", "RES", "DRG", "API", "HET", "UNL", "LIG1", "MOL1"}` ✅ |
| TEST-01 | No end-to-end GROMACS export test | e2e-export-test + e2e-compute-export phases | 17 e2e export test files + 130 bridge/grompp tests ✅ |
| TEST-02 | No pocket mode edge case tests | pocket-edge-tests phase | `tests/test_pocket_edge_cases.py` (51 tests) ✅ |
| TEST-04 | No ITP parsing edge case tests | Fix batch 6A, commit 687fdad | `tests/test_itp_parser_edge_cases.py` ✅ |
| TEST-05 | No atom count invariant test | Fix batch 6A, commit 687fdad | `tests/test_overlap_removal_invariants.py` ✅ |
| TEST-07 | No test for BUG-05 (HW1 Z-coordinate) | Phase 34.7-01, commit 57442a9 | `tests/test_bug05_mw01_deflt01.py` (9 regression tests) ✅ |
| TEST-08 | No defaults consistency test | Phase 34.7-01 | Covered by 34.7-01 regression tests (DEFLT-01 fix verified) ✅ |

### From `CONCERNS.md` (items in body still described as active, but now fixed)

| Section | Issue ID | Original Finding | How Fixed | Evidence |
|---------|----------|------------------|-----------|---------|
| Known Bugs | BUG-05 | Copy-paste error in HW1 Z-coordinate | Phase 34.7-01 | All `h1_pos[2]` correct ✅ |
| Known Bugs | DEFLT-01 (listed as TD-09) | `[ defaults ]` inconsistency | Phase 34.7-01 | All writers now `fudgeLJ=0.5, fudgeQQ=0.8333` ✅ |
| Performance | PERF-01 | O(n²) H-bond detection | Quick Task 022 | `vtk_utils.py` uses KDTree ✅ |
| Performance | PERF-03 | Pocket fills entire box | Already optimized | Pocket fills bounding box `(2r,2r,2r)`, not entire box ✅ |
| Exception Handling | EXC-02 | Silent FileNotFoundError:pass | Fix batch 1 | `QMessageBox.warning()` ✅ |
| Exception Handling | EXC-03 | Missing traceback.print_exc() | Quick Task 027 | All 5 exporters have traceback ✅ |
| Test Coverage | TEST-01 | No e2e export test | e2e phases | 17+ test files ✅ |
| Test Coverage | TEST-02 | No pocket edge cases | pocket-edge-tests | 51 tests ✅ |
| Test Coverage | TEST-05 | No overlap removal invariant tests | Fix batch 6A | `test_overlap_removal_invariants.py` ✅ |
| Test Coverage | TEST-07 | No HW1 Z-coordinate test | Phase 34.7 | Regression tests added ✅ |
| Test Coverage | TEST-08 | No defaults consistency test | Phase 34.7 | Regression tests added ✅ |
| Bundle Issues | BUNDLE-01 | PyInstaller excludes empty | Fix batch 5 | `excludes` list populated ✅ |
| Security | SEC-01 | Path without sanitization | Fix batch 5 | `Path.resolve()` ✅ |
| Scientific | SCI-01 | Ice Ih density fallback at wrong conditions | Partially fixed | Fallback unchanged but better documented; low priority |
| Scientific | SCI-03 | Missing O-O distance citations | Fix batch 4 | Petrenko & Whitworth added ✅ |
| Scientific | SCI-04 | Ion ITP lacks Madrid2019 header | Fix batch 4 + e2e | Header present ✅ |

---

## Issues Still Open (genuinely unresolved)

These issues were documented and remain unfixed in the current codebase. They are legitimate concerns.

| Issue ID | Source File | Finding | Status |
|----------|------------|---------|--------|
| BUG-04 | CONCERNS.md, ISSUES_VERIFICATION.md | `diversity_score()` always returns 1.0 | **OPEN** — Design decision needed (structural fingerprint diversity) |
| FRAG-03 | CONCERNS.md, ISSUES_VERIFICATION.md | gromacs_writer.py monolith (2701 lines, 28 functions) | **OPEN** — Refactor deferred |
| TD-01 | CONCERNS.md, ISSUES_VERIFICATION.md | Duplicate mode functions across slab/pocket/piece | **OPEN** — Consolidation deferred |
| TD-05 | CONCERNS.md, CONCERNS_VERIFICATION.md | np.random global state (not thread-safe) | **OPEN** — Blocked on GenIce2 |
| TD-07 | CONCERNS.md, ISSUES_VERIFICATION.md | No upload-time atomtypes warning | **OPEN** — UX decision needed |
| TD-08 | CONCERNS.md | Synthetic anonymous objects (type('obj',...)) in gromacs_writer.py | **OPEN** — 5 instances still use `type('obj', (object,), {...})` instead of `MoleculeIndex` |
| TD-10 | CONCERNS.md | Module-level `_registry` in gromacs_writer.py | **OPEN** — Accumulates state across exports |
| TD-11 | CONCERNS.md | Atomtype dedup logic duplicated across 3+ writers | **OPEN** — Same `_written_atomtypes` pattern copy-pasted |
| TD-12 | CONCERNS.md | `count_guest_atoms()` ambiguous branching | **PARTIALLY FIXED** — `guest_type` param added, but heuristic fallback still fragile |
| PERF-02 | CONCERNS.md, ISSUES_VERIFICATION.md | 27× supercell in scorer O-O distance | **OPEN** — `cKDTree(boxsize=)` not yet used |
| PERF-04 | CONCERNS.md | Nested loops in guest molecule detection | **OPEN** — Low priority |
| PERF-03 | CONCERNS.md | Pocket bounding box overfill | **OPEN** — Low priority (optimized to bounding box already) |
| UNIT-02 | CONCERNS.md, ISSUES_VERIFICATION.md | Fallback density no GUI indicator | **OPEN** — GUI architecture change needed |
| EXC-01 | CONCERNS.md, CONCERNS_VERIFICATION.md | IAPWS failures not visually indicated in GUI | **PARTIALLY FIXED** — Logging correct, no visual indicator |
| FRAG-05 | CONCERNS.md | main_window.py mixed responsibilities (2024 lines) | **OPEN** — Refactor deferred |
| FRAG-06 | CONCERNS.md | 3→4 atom expansion detection | **OPEN** — Detection relies on runtime check |
| FRAG-07 | CONCERNS.md | Moleculetype name mismatch risk | **PARTIALLY ADDRESSED** — e2e grompp tests cover some cases |
| VTK-DUP | CONCERNS.md | VTK availability detection duplicated 6× | **OPEN** — Still copy-pasted across 6 viewer files |
| BUNDLE-02 | CONCERNS.md, SCANCODE_STATUS.md | collect_all('genice2') includes unused plugins | **OPEN** — Needs runtime investigation |
| BUNDLE-03 | CONCERNS.md | UPX compression broke executable (reverted) | **OPEN** — Manual installation step needed |
| TEST-03 | CONCERNS.md | No triclinic interface generation tests | **OPEN** — Currently blocked by design |
| TEST-06 | CONCERNS.md | No VTK rendering fallback tests | **OPEN** — Low priority |
| TEST-09 | CONCERNS.md | No moleculetype name matching test | **PARTIALLY ADDRESSED** — e2e grompp validation tests cover this |
| SCALE-01 | CONCERNS.md | GRO format 99,999 atom number limit | **OPEN** — Design limit, handled by wrapping |
| SCALE-02 | CONCERNS.md | GenIce2 single-threaded generation | **OPEN** — Blocked on TD-05 |
| DEP-01 | CONCERNS.md | GenIce2 uses legacy numpy.random | **OPEN** — External dependency |
| DEP-02 | CONCERNS.md | iapws single-maintainer package | **OPEN** — Mitigated by fallback values |
| SCI-01 | CONCERNS.md | Ice Ih density fallback at wrong conditions | **OPEN** — Low priority, only hit outside stability range |
| SCI-02 | CONCERNS_VERIFICATION.md | Water density scaling assumption | **OPEN** — Physically reasonable, very low priority |

---

## Stale Pending Todos

| Todo File | Description | Should Archive? | Reason |
|-----------|-------------|-----------------|--------|
| `2026-05-07-capture-screenshots-per-phase-35-suggestions.md` | Capture screenshots for Phase 35 documentation | **KEEP** — Still pending (screenshots deferred in STATE.md) | Screenshots are genuinely needed for docs but deferred; still a real task |
| `2026-05-09-cli-only-executable-for-automation.md` | CLI-only executable for automation | **KEEP** — Future milestone (v4.6+) | Real feature request, not yet implemented |
| `2026-05-09-complex-hydrate-formation-atomsk.md` | Complex hydrate formation via atomsk | **KEEP** — Far-future research | Post-v6 research, still relevant |
| `2026-05-09-flexible-interface-construction.md` | Flexible interface construction modes | **KEEP** — Future feature | v5.x milestone, still relevant |
| `2026-05-09-unify-gui-cli-entry-point.md` | Unify GUI/CLI entry point | **KEEP** — Future tooling | v4.6+ milestone, still relevant |
| `2026-05-16-install-upx-for-bundle-compression.md` | Install UPX for bundle compression | **KEEP** — Manual tooling step | UPX installation is still needed; BUNDLE-03 remains open |
| `2026-05-24-pre-built-small-molecules-gromacs.md` | Pre-built small molecules with GROMACS format | **KEEP** — Future feature | Research complete (see `.planning/research/future-ml/`), implementation pending |

**No stale todos found.** All 7 pending todos reference genuinely unresolved future work. None describe issues that have been fixed.

---

## STATE.md Stale References

**Blockers section:** The "Blockers" section in STATE.md (lines 432-467) lists phase status for completed phases:
- Phase 34.6 status shows all 8 plans complete with "Phase 34.6 COMPLETE!" — This is historical, not a blocker
- Phase 35 status shows screenshots deferred — Still accurate
- Phase 34.5 status shows all complete — Historical, not a blocker

**Recommendation:** The "Blockers" section name is misleading since none are actual blockers. Consider renaming to "Completed Phase Status" or archiving completed phase checkpoints.

**Phase 34.7 decisions in STATE.md (lines 408-417):** Correctly document all 7 bug/design fixes as shipped. These are accurate.

**"Remaining Phase 35 work" (lines 461-467):** Still accurate — screenshots and release notes are genuinely pending.

---

## Documentation Files Needing Updates

### 1. `20260608_ISSUES_VERIFICATION.md` — NEEDS UPDATE

**Current state:** Lists all 7 active issues with verdicts (4 CONFIRMED, 3 PARTIALLY CORRECT) but does NOT indicate they are now fixed.

**Required update:** Add a "Resolution Status" column or section documenting that ALL 7 issues were fixed in Phase 34.7:

| ID | Verdict | Resolution |
|----|---------|------------|
| BUG-05 | CONFIRMED | **FIXED** — Phase 34.7-01, commit 6965961 |
| MW-01 | PARTIALLY CORRECT | **FIXED** — Phase 34.7-01, commit 6965961 (ice writer now uses molecule-aware wrapping) |
| RNG-01 | CONFIRMED | **FIXED** — Phase 34.7-02, commit ee0f4d5 (seeded RNG + Rotation.random) |
| IDX-01 | REFUTED | N/A — Was already refuted |
| ATOM-01 | CONFIRMED | **FIXED** — Phase 34.7-02, commit 8726698 (WATER_ATOMS_PER_MOLECULE constant) |
| TREE-01 | PARTIALLY CORRECT | **FIXED** — Phase 34.7-03, commit f44c22c (conditional KDTree rebuild) |
| GUEST-01 | PARTIALLY CORRECT | **FIXED** — Phase 34.7-08, commit 6d04262 (guest_type param + dead CO2 removal) |
| DEFLT-01 | CONFIRMED | **FIXED** — Phase 34.7-01, commit 6965961 (all writers fudgeLJ=0.5) |

### 2. `ISSUES_VERIFICATION.md` — NEEDS UPDATE

**Current state:** 38 issues verified 2026-05-22. The "Previously Fixed Issues" table in CONCERNS.md covers some, but this file still describes them as active.

**Required update:** Add resolution status to each issue. At minimum, add a "Resolution" header noting which batch/commit fixed each confirmed issue. The summary section should note that 32 of 34 confirmed issues are now fixed, with only BUG-04 and FRAG-03 (design items) still deferred.

### 3. `CONCERNS.md` — NEEDS UPDATE

**Current state:** Has a "Previously Fixed Issues" reference table (lines 307-333) but the main body still describes BUG-05 and DEFLT-01 as active "Known Bugs" and lists many fixed items as current concerns.

**Required updates:**
- **Remove BUG-05 from "Known Bugs" section** — It's fixed (Phase 34.7-01)
- **Remove DEFLT-01/TD-09 from "Tech Debt" section** — All 6 writers now use fudgeLJ=0.5 (Phase 34.7-01)
- **Update PERF-01** — Already fixed by QT-022, remove from "Performance Bottlenecks"
- **Update PERF-03** — Already optimized, mark as very low priority
- **Update EXC-02** — Now shows QMessageBox.warning, remove from "Exception Handling Issues"
- **Update EXC-03** — Now has traceback.print_exc in all 5 handlers, mark as FIXED
- **Update TEST-01/02/05/07/08** — All have test files now, mark as FIXED
- **Update BUNDLE-01** — Excludes list now populated, mark as FIXED
- **Update SEC-01** — Path.resolve() now used, mark as FIXED
- **Update SCI-03/SCI-04** — Citations and headers now present, mark as FIXED
- **Add resolution status to TD-06** — lru_cache and Lock implemented, mark as FIXED
- **Add TD-08/TD-10/TD-11** — These are real unfixed concerns not in the original ISSUES_VERIFICATION.md but added to CONCERNS.md
- **Update FRAG-02** — Assertions now present, mark as FIXED
- **Update VTK-DUP** — Still duplicated across 6 files (confirmed unfixed)
- **Update TD-12** — guest_type parameter added, partial fix noted

### 4. `CONCERNS_VERIFICATION.md` — NEEDS UPDATE

**Current state:** Verified 2026-05-22. Many issues marked as "CONFIRMED" are now fixed.

**Required update:** Add a "Post-verification fix status" section or re-verify with current code. Key items now fixed since verification:
- BUG-01 (escalated): FIXED (OW safeguard added to pocket.py and piece.py)
- BUG-02 (partially confirmed): FIXED (types.py now says 13, comments corrected)
- EXC-02: FIXED (QMessageBox.warning added)
- BUNDLE-01: FIXED (excludes list populated)
- TD-06: FIXED (lru_cache + Lock)
- FRAG-02: FIXED (assertions added)
- TEST-01/02/04/05: FIXED (test files created)

### 5. `ISSUES_BY_FILE.md` — NEEDS UPDATE

**Current state:** Generated 2026-05-22, lists 38 confirmed issues across 25 files with priority ranking. Most are now fixed.

**Required update:** Add resolution column. Many files should have zero remaining issues (e.g., `export.py` — all 4 issues fixed; `pocket.py`/`piece.py` — OW safeguard added; `README.md` — naming fixed; `gui-guide.md` — 9 issues all fixed). The file priority ranking is now outdated.

### 6. `SCANCODE_STATUS.md` — PARTIALLY STALE

**Current state:** Updated 2026-05-22, lists 44 fixed + 9 deferred. The 9 deferred items are accurate but the total count doesn't account for Phase 34.7 fixes (7 additional fixes). Also missing reference to e2e-compute-export and e2e-api-workflow test phases.

**Required update:** Add Phase 34.7 to fix batches table (7 more fixes). Update "Fixed" count from 44 to 51. The deferred items list is accurate.

---

## Recommendations

- [ ] **HIGH PRIORITY:** Update `20260608_ISSUES_VERIFICATION.md` — Add resolution status for all 8 issues (7 fixed + 1 refuted). This is the most recent verification report and future agents will read it first.
- [ ] **HIGH PRIORITY:** Update `CONCERNS.md` — Move BUG-05 and DEFLT-01 from "Known Bugs" to "Previously Fixed Issues" table. Update PERF-01, EXC-02, EXC-03, BUNDLE-01, SEC-01, SCI-03/04, TD-06, FRAG-02, TEST-01/02/05/07/08 as fixed.
- [ ] **MEDIUM PRIORITY:** Update `ISSUES_VERIFICATION.md` — Add resolution status to all 38 issues. Note that 32+ are now fixed.
- [ ] **MEDIUM PRIORITY:** Update `ISSUES_BY_FILE.md` — Add resolution column. Many files now have zero remaining issues. Update file priority ranking.
- [ ] **MEDIUM PRIORITY:** Update `CONCERNS_VERIFICATION.md` — Add post-verification fix status for issues fixed after 2026-05-22.
- [ ] **LOW PRIORITY:** Update `SCANCODE_STATUS.md` — Add Phase 34.7 to fix batch table. Update fixed count from 44 to 51.
- [ ] **LOW PRIORITY:** Rename "Blockers" section in `STATE.md` — Completed phases listed under "Blockers" is misleading. Archive completed phase status.
- [ ] **NO ACTION NEEDED:** Pending todos — All 7 are genuinely unresolved future work items.
- [ ] **NO ACTION NEEDED:** STATE.md Phase 34.7 decisions — Already correctly documented as shipped.

---

*Stale issues audit: 2026-06-12*
