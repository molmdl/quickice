# All Issues Summary — Grouped by File

**Generated:** 2026-05-22
**Sources:** CONCERNS.md, CONCERNS_VERIFICATION.md, 20260522_gromacs_flow_trace.md, 20260522_documentation_crosscheck.md
**Scope:** Only CONFIRMED, ESCALATED, and PARTIALLY FIXED issues. Excludes: fixed (5), false alarms (1), duplicates (1).

---

## Legend

🔴 CRITICAL — Will cause GROMACS failure or wrong results
🟠 HIGH — Significant impact on users or correctness
🟡 MEDIUM — Moderate impact, should fix
🟢 LOW — Minor, cleanup or future improvement
📋 TEST — Test gap, not a code bug

---

## `quickice/gui/export.py` (4 issues)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| EXC-02 | 🟠 HIGH | `FileNotFoundError: pass` at lines 332-335 and 876-879 — silent failure produces broken .top referencing missing .itp | Replace `pass` with `QMessageBox.warning()` |
| FLOW-01 | 🔴 CRITICAL | `SoluteGROMACSExporter` (line 36) uses `write_gro_file()` and `write_top_file()` — simple writers that don't compute MW for ice or create solute entries in .top | Rewrite to use `write_interface_gro_file()` and proper multi-molecule writer |
| FLOW-02 | 🔴 CRITICAL | `CustomMoleculeGROMACSExporter` (line 163) does NOT copy `tip4p-ice.itp` to output directory, but .top includes it | Add `shutil.copy2(tip4p_path, output_dir / "tip4p-ice.itp")` |
| FLOW-03 | 🟡 MEDIUM | `write_custom_molecule_gro_file()` hardcodes guest residue as "GUE" instead of detecting actual guest type; .top includes `#include "guest.itp"` which doesn't exist | Use `detect_guest_type_from_atoms()` and appropriate `_{type}_hydrate.itp` |

---

## `quickice/output/gromacs_writer.py` (5 issues)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| BUG-03 | 🟡 MEDIUM | Line 1102: `molecule_index.index(mol)` inside loop → O(n²) for residue number lookup | Use `enumerate(molecule_index)` |
| TD-07/FRAG-03 | 🟡 MEDIUM | `comment_out_atomtypes_in_itp()` (lines 310-354) silently modifies user ITP content | Add upload-time validation in custom_molecule_panel.py; warn user |
| BUG-02 | 🟢 LOW | Line 841: Comment says "C5H8O (14 atoms)" — wrong formula for THF (C4H8O = 13 atoms) | Fix comment to "C4H8O (13 atoms)" |
| NEW-02 | 🟢 LOW | Line 14: Dead import of `MOLECULE_TYPE_INFO` — never accessed by key | Remove import |
| FRAG-03 | 🟡 MEDIUM | Single 2054-line file with 15+ write functions; `detect_guest_type_from_atoms()` (line 831) uses heuristic pattern matching | Consider splitting into per-structure-type writers (refactor) |

---

## `quickice/structure_generation/modes/pocket.py` (2 issues)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| BUG-01 | 🟠 HIGH | `_detect_guest_atoms()` (lines 44-69) missing OW-safeguard — water molecules can be misclassified as guests | Add OW check from slab.py lines 80-93 |
| TD-01 | 🟡 MEDIUM | Duplicate functions: `detect_atoms_per_molecule`, `_detect_guest_atoms`, `_count_guest_molecules` — same as slab.py/piece.py | Consolidate to `quickice/utils/molecule_utils.py` |

---

## `quickice/structure_generation/modes/piece.py` (2 issues)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| BUG-01 | 🟠 HIGH | `_detect_guest_atoms()` (lines 51-89) missing OW-safeguard — same as pocket.py | Add OW check from slab.py lines 80-93 |
| TD-01 | 🟡 MEDIUM | Duplicate functions (same as pocket.py) | Consolidate to `quickice/utils/molecule_utils.py` |

---

## `quickice/structure_generation/modes/slab.py` (3 issues)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| FRAG-02 | 🟡 MEDIUM | Lines 527-549: Second overlap removal (guest-water) has no invariant check that `water_atom_count == water_nmolecules * 4` | Add assertion after overlap removal |
| TD-01 | 🟡 MEDIUM | Duplicate functions (consolidation target) | Consolidate to `quickice/utils/molecule_utils.py` |
| TEST-05 | 📋 TEST | No test for atom count consistency after two rounds of overlap removal | Add invariant assertion test |

---

## `quickice/structure_generation/types.py` (2 issues)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| BUG-02 | 🟢 LOW | Line 17 and 87: `MOLECULE_TYPE_INFO["thf"]["atoms"] = 12` — wrong (should be 13) | Change to 13 |
| NEW-02 | 🟢 LOW | `MOLECULE_TYPE_INFO` dict is a dead import in consuming files — never accessed by key | Consider removing dict if unused |

---

## `quickice/utils/molecule_utils.py` (1 issue)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| BUG-02 | 🟢 LOW | Line 77: Comment says "C5H8O = 14 atoms" — wrong formula (THF = C4H8O = 13 atoms) | Fix to "C4H8O = 13 atoms" |

---

## `quickice/gui/main_window.py` (3 issues)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| FRAG-01 | 🟡 MEDIUM | Lines 1193-1234: Cross-tab data flow uses `getattr(structure, 'attr', default)` — fragile, no assertions | Add assertions for required attributes in `set_*()` methods |
| NEW-01 | 🟢 LOW | Lines 1199-1234: Verbose debug logging (`[Liquid Volume Debug]`, `[Water Count Debug]`) at `logger.info()` level | Change to `logger.debug()` |
| TEST-01 | 📋 TEST | No end-to-end test for full interface→custom→solute→ion export chain | Add integration test |

---

## `quickice/gui/solute_panel.py` (1 issue)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| FRAG-01 | 🟡 MEDIUM | Depends on `set_custom_molecule_structure()` and `set_liquid_volume()` from upstream tabs — no assertions | Add assertions for required attributes |

---

## `quickice/gui/ion_panel.py` (1 issue)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| FRAG-01 | 🟡 MEDIUM | Depends on upstream structure attributes via `getattr()` — no assertions | Add assertions for required attributes |

---

## `quickice/gui/custom_molecule_panel.py` (1 issue)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| TD-07 | 🟡 MEDIUM | No upload-time validation for `[ atomtypes ]` in user ITP — only caught at export when silently commented out | Add upload-time warning about atomtypes |

---

## `quickice/structure_generation/gromacs_ion_export.py` (2 issues)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| SCI-04 | 🟢 LOW | Generated `ion.itp` lacks header comment identifying Madrid2019_085 specifically | Add `; Madrid2019_085 ion model (Zeron et al. 2019)` to generated ITP header |
| SCI-04 | 🟢 LOW | Line 22: Code comment says Madrid2019_085 but this isn't propagated to the output file | Copy version string into generated ITP |

---

## `quickice/ranking/scorer.py` (3 issues)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| BUG-04 | 🟢 LOW | `diversity_score()` (lines 196-234) always returns 1.0 since all seeds are unique — zero discriminatory value | Implement structural fingerprint diversity (RDF, bond angles) or remove from ranking |
| PERF-02 | 🟢 LOW | Lines 53-61: 3×3×3 supercell (27× memory) for KDTree PBC | Use `cKDTree(boxsize=)` for orthorhombic cells |
| SCI-1/DOC | 🟢 LOW | Line 168: `AVOGADRO = 6.022e23` vs `6.02214076e23` in solute_inserter.py | Standardize to CODATA 2017 value |

---

## `quickice/ranking/types.py` (1 issue)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| SCI-03 | 🟢 LOW | Lines 21-22: `ideal_oo_distance=0.276` and `oo_cutoff=0.35` lack literature citations | Add comments citing Petrenko & Whitworth (1999) for 0.276 nm |

---

## `quickice/phase_mapping/water_density.py` (2 issues)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| UNIT-02 | 🟢 LOW | Lines 85-92: Fallback to `0.9998 g/cm³` logged at `logger.warning()` but no GUI indicator | Add visual indicator in GUI when fallback used |
| UNIT-03 | 🟢 LOW | Lines 73-74: `warnings.filterwarnings("ignore", message="extrapolated")` — suppressed IAPWS extrapolation warnings | Add `logger.debug()` for extrapolation events |

---

## `quickice/phase_mapping/ice_ih_density.py` (1 issue)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| SCI-01 | 🟢 LOW | Fallback `0.9167 g/cm³` at 273.15 K/0.1 MPa regardless of actual T/P when outside IAPWS range | Return density at stability boundary, or warn conditions are outside Ice Ih range |

---

## `quickice/structure_generation/generator.py` (1 issue)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| TD-05 | 🟢 LOW | Lines 101-157: Manipulates `np.random` global state (not thread-safe); `try/finally` is adequate for single-threaded | Use numpy Generator API when GenIce2 supports it; no immediate fix |

---

## `quickice/structure_generation/water_filler.py` (2 issues)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| TD-06 | 🟢 LOW | Line 144: `_water_template_cache` module-level mutable global without thread safety | Add `functools.lru_cache` or `threading.Lock` |
| TD-06 | 🟢 LOW | Line 234: `global _water_template_cache` pattern | Use `lru_cache` |

---

## `quickice/structure_generation/hydrate_generator.py` (2 issues)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| TD-06 | 🟢 LOW | Lines 28-30: `_genice_lib`, `_gromacs_format`, `_lattice_modules_loaded` module-level globals without thread safety | Add `threading.Lock` or `lru_cache` |
| NEW-02 | 🟢 LOW | Line 15: Dead import of `MOLECULE_TYPE_INFO` | Remove import |

---

## `quickice/structure_generation/ion_inserter.py` (1 issue)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| SCI-04 | 🟢 LOW | Lines 25-36: Ion parameters hardcoded from "Madrid2019" without version tracking in output | Document Madrid2019_085 version in generated ITP |

---

## `quickice/structure_generation/solute_inserter.py` (1 issue)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| SCI-1/DOC | 🟢 LOW | Line 32: `AVOGADRO = 6.02214076e23` — correct CODATA 2017 value (but differs from scorer.py) | No fix needed — this one is correct; fix scorer.py instead |

---

## `quickice/structure_generation/itp_parser.py` (1 issue)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| FRAG-04 | 🟢 LOW | Lines 65-77: Regex for moleculetype name extraction — fragile for non-standard formatting | Add validation against known GenIce2 formats; make generic names configurable |
| TEST-04 | 📋 TEST | No tests for edge cases (BOM, Windows line endings, extra whitespace) | Add test cases |

---

## `quickice/structure_generation/gro_parser.py` (1 issue)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| UNIT-01 | 🟡 MEDIUM | No validation that coordinates < 50 nm (to catch Å→nm mixup) | Add coordinate range validation at parse time |

---

## `quickice/structure_generation/molecule_validator.py` (1 issue)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| FRAG-04 | 🟢 LOW | Line 18: `GENERIC_RESIDUE_NAMES = {"MOL", "UNK", "LIG", "XXX", "RES"}` — hardcoded whitelist, could miss new generic names | Make configurable or expand list |

---

## `quickice/main.py` (1 issue)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| SEC-01 | 🟢 LOW | Line 127: `Path(args.output)` without sanitization; `phase_id` used in filename without validation | Add `Path.resolve()` and boundary checks |

---

## `quickice/gui/phase_diagram_widget.py` (1 issue)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| EXC-01/PARTIAL | 🟢 LOW | Lines 81-82, 483-484: IAPWS failures now logged at `logger.warning()` but no visual indication in GUI | Add dashed line or label where IAPWS calculation failed |

---

## `quickice-gui.spec` (2 issues)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| BUNDLE-01 | 🟢 LOW | Line 9-16: `collect_all()` for 9 packages with `excludes=[]` — includes test files, docs, dev artifacts (~50-200 MB waste) | Add explicit excludes: `*/tests/*`, `*/docs/*`, `*/test/*` |
| BUNDLE-02 | 🟢 LOW | Line 9: `collect_all('genice2')` includes all lattice/molecule/format plugins — most unused | Use `collect_submodules()` with targeted patterns for specific lattices |

---

## `README.md` (3 issues — all documentation)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| MOL-1 | 🔴 CRITICAL | Line 192-198: Uses `CH4_HYD` and `THF_LIQ` instead of `CH4_H` and `THF_L` | Replace old names |
| MOL-5 | 🟠 HIGH | Line 181: Says `ch4.itp/thf.itp` but code exports `ch4_hydrate.itp/thf_hydrate.itp` | Update ITP file names |
| CIT-GAFF2 | 🟡 MEDIUM | Line 216: Mentions "GAFF2 force field" but no formal citation in References | Add Wang et al. (2004) and He et al. (2020) citations |

---

## `docs/gui-guide.md` (9 issues — all documentation)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| MOL-2 | 🔴 CRITICAL | Line 708: `CH4_LIQ`/`THF_LIQ` → should be `CH4_L`/`THF_L` | Replace names |
| MOL-3 | 🔴 CRITICAL | Line 710: `CH4_HYD`/`THF_HYD` → should be `CH4_H`/`THF_H`, `_LIQ` → `_L` | Replace names and update note |
| MOL-4 | 🟠 HIGH | Line 297: Says `ch4.itp`/`thf.itp` → should be `ch4_hydrate.itp`/`thf_hydrate.itp` | Update ITP file names |
| FF-1 | 🟠 HIGH | Line 297: Says "GAFF" → should be "GAFF2" | Replace force field name |
| KS-1 | 🟠 HIGH | Lines 200-214: Missing Ctrl+Alt+P, Ctrl+L, Ctrl+M in shortcuts table | Add three missing shortcuts |
| KS-2 | 🟠 HIGH | Line 163: Ctrl+S description still says "Save PDB from left viewer" → should be "Export current tab" | Update to unified export |
| KS-3 | 🟠 HIGH | Line 281: Says `Ctrl+E` → should be `Ctrl+H` for hydrate export | Replace shortcut |
| EXP-1 | 🟡 MEDIUM | Line 295: `hydrate_{lattice}.gro` → actual pattern is `hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro` | Update filename pattern |
| EXP-2 | 🟡 MEDIUM | Lines 704-705: `interface_with_solutes.gro` → actual pattern is `solute_{type}_{count}molecules.gro` | Update filename pattern |

---

## `docs/cli-reference.md` (1 issue — documentation)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| VER-1 | 🟡 MEDIUM | Line 145: Says version `4.0.0` → should be `4.5.0` | Update version string |

---

## `docs/ranking.md` (1 issue — documentation)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| SCI-03 | 🟢 LOW | Line 31: "0.276 = Ideal O-O distance" without citation | Add citation to Petrenko & Whitworth (1999) |

---

## `.planning/milestones/v1.0-run_uat_tests.py` (1 issue)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| SEC-02 | 🟢 LOW | Line 24: `shell=True` in subprocess call | Historical UAT record script (289 lines, not shipped, not in app/test suite). Low risk — user can remove `shell=True` or delete the file if desired |

---

## `.planning/debug/` (1 issue)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| TD-03 | 🟢 LOW | 42 Python scripts (6,126 lines, 1.7 MB) never referenced by app or tests | Delete `resolved/` and `deferred/` subdirs; review active scripts |

---

## Test files to add (no existing file — new test gaps)

| ID | Severity | Gap | Suggested file |
|----|----------|-----|----------------|
| TEST-01 | 📋 HIGH | No end-to-end GROMACS export test for full chain (interface→custom→solute→ion) | `tests/test_e2e_export_chain.py` |
| TEST-05 | 📋 HIGH | No atom count invariant assertion after multiple overlap removal steps | `tests/test_overlap_removal_invariants.py` |
| TEST-02 | 📋 MEDIUM | No pocket mode edge cases (thin cavities, non-spherical) | `tests/test_pocket_edge_cases.py` |
| TEST-04 | 📋 MEDIUM | No ITP parsing edge cases (BOM, Windows line endings) | `tests/test_itp_parser_edge_cases.py` |

---

## FILE PRIORITY RANKING

**Fix all issues in these files first (CRITICAL + HIGH):**

1. **`quickice/gui/export.py`** — 2 CRITICAL bugs (solute writer, missing tip4p-ice.itp) + 1 HIGH (silent FileNotFoundError)
2. **`quickice/structure_generation/modes/pocket.py`** — 1 HIGH (missing OW safeguard)
3. **`quickice/structure_generation/modes/piece.py`** — 1 HIGH (missing OW safeguard)
4. **`README.md`** — 1 CRITICAL (molecule naming), 1 HIGH (ITP file names)
5. **`docs/gui-guide.md`** — 3 CRITICAL (molecule naming), 4 HIGH (shortcuts, GAFF→GAFF2, ITP names)

**Then MEDIUM issues:**

6. **`quickice/output/gromacs_writer.py`** — 3 MEDIUM (O(n²), atomtypes handling, file size/refactor)
7. **`quickice/structure_generation/modes/slab.py`** — 1 MEDIUM (invariant check)
8. **`quickice/gui/main_window.py`** — 1 MEDIUM (fragile getattr) + 1 TEST gap
9. **`quickice/structure_generation/gro_parser.py`** — 1 MEDIUM (unit validation)
10. **`docs/cli-reference.md`** — 1 MEDIUM (version)

**LOW issues can be batched:**

11-17. All remaining files — comments, citations, logging levels, bundle optimization, debug cleanup

---

**Total: 38 confirmed issues across 25 files**
- 🔴 CRITICAL: 5 (2 code + 3 doc)
- 🟠 HIGH: 8 (3 code + 5 doc)
- 🟡 MEDIUM: 8 (4 code + 3 doc + 1 spec)
- 🟢 LOW: 17 (10 code + 3 doc + 2 test runner + 2 debug)
- 📋 TEST: 4 gaps

*Generated: 2026-05-22*

---

## Resolution Status (2026-06-12)

### Files with ZERO remaining issues (all documented issues now fixed)

| File | Fixed Issues | How |
|------|-------------|-----|
| `quickice/gui/export.py` | FLOW-01, FLOW-02, FLOW-03, EXC-02 | Fix batch 1 |
| `quickice/structure_generation/modes/pocket.py` | BUG-01 | Fix batch 1 (OW safeguard) |
| `quickice/structure_generation/modes/piece.py` | BUG-01 | Fix batch 1 (OW safeguard) |
| `README.md` | MOL-1, MOL-5, CIT-GAFF2 | Fix batches 1-3 |
| `docs/gui-guide.md` | FF-1, KS-1, KS-2, KS-3, MOL-2, MOL-3, MOL-4, EXP-1, EXP-2 | Fix batches 1-3 (9 issues all fixed) |
| `docs/cli-reference.md` | VER-1 | Fix batch 3 |
| `quickice/structure_generation/types.py` | BUG-02 | Fix batch 4 |
| `quickice/utils/molecule_utils.py` | BUG-02c, SCI-1/DOC | Fix batch 4 |
| `quickice/gui/main_window.py` | NEW-01 | Fix batch 4 (but FRAG-05 still open) |
| `quickice/ranking/scorer.py` | SCI-1/DOC | Fix batch 4 (but PERF-02 still open) |
| `quickice/main.py` | SEC-01 | Fix batch 5, commit 22bd382 |
| `quickice/phase_mapping/water_density.py` | UNIT-03 | Fix batch 4 |
| `quickice/structure_generation/gro_parser.py` | UNIT-01 | Fix batch 3 |

### Files with significant progress but remaining issues

| File | Fixed Issues | Remaining Open Issues |
|------|-------------|----------------------|
| `quickice/output/gromacs_writer.py` | BUG-02, BUG-03, BUG-05, MW-01, DEFLT-01, NEW-02, FLOW-03 | FRAG-03 (monolith), TD-08, TD-10, TD-11 |
| `quickice/structure_generation/modes/slab.py` | FRAG-02 (assertions added) | TD-01 (duplicate functions) |
| `quickice/structure_generation/modes/pocket.py` | BUG-01, FRAG-02 | TD-01 |
| `quickice/structure_generation/modes/piece.py` | BUG-01, FRAG-02 | TD-01 |
| `quickice/gui/main_window.py` | NEW-01 | FRAG-01, FRAG-05, TEST-01 |
| `quickice-gui.spec` | BUNDLE-01 | BUNDLE-02, BUNDLE-03 |

*Resolution status updated: 2026-06-12*
