# Codebase Concerns Verification Report

**Verified:** 2026-05-22
**Source:** `.planning/codebase/CONCERNS.md` (2026-05-22)
**Cross-referenced with:** `.planning/code_analysis/*` reports, Quick Tasks 020-028, git history

---

## Summary

| Category | Total | Confirmed | Fixed / False Alarm | Partially Fixed | Escalated |
|----------|-------|-----------|---------------------|-----------------|-----------|
| Tech Debt | 7 | 4 | 2 fixed, 1 false alarm | 0 | 0 |
| Known Bugs | 4 | 2 | 0 | 1 | 1 |
| Security | 2 | 2 | 0 | 0 | 0 |
| Performance | 4 | 1 | 1 fixed, 1 duplicate of TD-06 | 1 | 0 |
| Fragile Areas | 4 | 4 | 0 | 0 | 0 |
| Unit Mismatches | 3 | 3 | 0 | 0 | 0 |
| Scientific Accuracy | 4 | 2 | 0 | 2 | 0 |
| Exception Handling | 3 | 1 | 2 fixed | 0 | 0 |
| Bundle Size | 2 | 2 | 0 | 0 | 0 |
| Test Coverage | 5 | 5 | 0 | 0 | 0 |
| **Total** | **38** | **26** | **5 fixed, 1 false alarm, 1 duplicate** | **4** | **1** |

**Key findings:**
- 5 concerns already fixed by Quick Tasks 021, 022, 026, 027
- 1 false alarm (TD-04: duplicate comment lines — misidentified)
- 1 escalation (BUG-01: OW safeguard missing in BOTH pocket.py AND piece.py, not just pocket.py)
- 26 concerns confirmed as still real

---

## Detailed Verification

---

## Tech Debt

### TD-01: Duplicate Mode Functions Across slab.py, pocket.py, piece.py
**Status: CONFIRMED**
**Evidence:**
- `detect_atoms_per_molecule()`: duplicated in slab.py:24-41, pocket.py:24-41, piece.py:31-48 — identical implementations
- `_detect_guest_atoms()`: duplicated in slab.py:44-106, pocket.py:44-69, piece.py:51-89 — with DIFFERENT implementations (see BUG-01)
- `_count_guest_molecules()`: duplicated in slab.py:109-122, pocket.py:72-85, piece.py:92-117 — nearly identical
- `ICE_ATOM_NAMES_TEMPLATE = ["O", "H", "H"]`: in slab.py:21 and pocket.py:21 (NOT in piece.py)
- Only `count_guest_atoms()` was consolidated to `molecule_utils.py` (Quick Task 021 removed `build_molecule_index` but didn't touch these three functions)

**Correction to CONCERNS.md:** The concern states "pocket.py version of `_detect_guest_atoms` is simplified (missing the OW-safeguard that slab.py and piece.py have)." This is **WRONG** — piece.py also lacks the OW safeguard. Only slab.py has it. See BUG-01 escalation.

**Severity: Medium** — maintenance burden is real; the bug from inconsistency is tracked separately (BUG-01)

---

### TD-02: Unused `build_molecule_index()` in molecule_utils.py
**Status: FALSE ALARM — FIXED by Quick Task 021**

**Evidence:**
- `quickice/utils/molecule_utils.py` is now 108 lines, contains only `count_guest_atoms()`
- `build_molecule_index()` was removed in commit `187368f` (refactor(quick-021): remove unused build_molecule_index function)
- No imports of `build_molecule_index` exist anywhere in the codebase
- Private `_build_molecule_index()` methods remain in `hydrate_generator.py:479` and `ion_inserter.py:60` — these are different functions with different signatures

---

### TD-03: Debug Scripts Never Cleaned Up (6,126 lines)
**Status: CONFIRMED**

**Evidence:**
- Directory `.planning/debug/` exists with 42 `.py` files, 6,126 total lines, 1.7 MB
- Subdirectories: `resolved/` (13 files), `deferred/` (19 files), and 8 active scripts + markdown files
- None of these scripts are imported by the application or test suite

**Severity: Low** — repository bloat only, no functional impact

---

### TD-04: Duplicate Comment Lines Across Multiple Files
**Status: FALSE ALARM — MISIDENTIFIED**

**Evidence:**
The concern claims "identical comment lines repeated 3×" but what actually exists is:
1. **slab.py:18-20** — Three *different* consecutive comment lines about `ICE_ATOM_NAMES_TEMPLATE`
2. **pocket.py:18-20** — Same 3-line comment block as slab.py (2 files, not 3× within a file)
3. **piece.py** — Does NOT have the `ICE_ATOM_NAMES_TEMPLATE` constant or its comment block at all
4. **water_filler.py:137-140** — A 4-line calculation comment, NOT duplicate lines
5. **molecular_viewer.py:29-31** — Three *different* comment lines about VTK unit conversion
6. **hydrate_renderer.py:25-27** — Same 3-line VTK unit conversion comment as molecular_viewer.py (2 files)

No file contains the same comment line repeated 3×. The "duplication" is the same comment block appearing in 2 files (a consequence of code duplication in TD-01), not a copy-paste error within a single file.

**Reclassification:** This is a subset of TD-01 (code duplication), not a separate concern. Merge into TD-01.

---

### TD-05: Global Random State Pollution in GenIce
**Status: CONFIRMED**

**Evidence:**
- `quickice/structure_generation/generator.py:101-157` uses `np.random.seed()` / `np.random.get_state()` / `np.random.set_state()`
- `try/finally` pattern is correctly implemented (lines 101, 155-157)
- NOT thread-safe (documented at lines 96-99)
- GenIce2 uses `np.random` global state internally

**Severity: Low** — adequate for single-threaded use; no immediate fix needed

---

### TD-06: Module-Level Global Caches Without Thread Safety
**Status: CONFIRMED**

**Evidence:**
- `quickice/structure_generation/water_filler.py:144`: `_water_template_cache: Optional[tuple[...]] = None` — module-level mutable global
- `quickice/structure_generation/hydrate_generator.py:28-30`: `_genice_lib = None`, `_gromacs_format = None`, `_lattice_modules_loaded = {}` — module-level globals
- No `threading.Lock` or `functools.lru_cache` used for any of these
- `water_filler.py:234` uses `global _water_template_cache` pattern

**Severity: Low** — QuickIce is single-threaded; race condition only theoretical

---

### TD-07: ITP Atomtypes Section Handling Requires Manual Commenting
**Status: CONFIRMED**

**Evidence:**
- `quickice/output/gromacs_writer.py:310-354`: `comment_out_atomtypes_in_itp()` function modifies ITP content before writing
- `quickice/gui/export.py:211-216`: CustomMoleculeGROMACSExporter uses it
- `quickice/gui/export.py:347-351`: IonGROMACSExporter uses it for solute ITP
- `quickice/gui/export.py:361-365`: IonGROMACSExporter uses it for custom ITP
- User's ITP file is silently modified — no upload-time validation or warning

**Severity: Medium** — users may be confused why their ITP content differs after export

---

## Known Bugs

### BUG-01: Pocket Mode `_detect_guest_atoms` Missing OW Safeguard
**Status: ESCALATED — worse than described**

**Evidence:**
The concern claims "pocket.py version is missing the OW-safeguard that slab.py and piece.py have." This is **incorrect**:

| File | Line Range | Has OW Safeguard? |
|------|-----------|-------------------|
| slab.py | 44-106 | YES (lines 80-93: checks `has_ow` before classifying as guest) |
| pocket.py | 44-69 | NO — directly adds to `guest_indices` without OW check |
| piece.py | 51-89 | NO — directly adds to `guest_indices` without OW check |

Both `pocket.py` and `piece.py` are vulnerable to misclassifying water molecules as guest molecules when atom counting errors occur. The safeguard exists only in `slab.py`.

**Updated severity: Medium-High** — two of three mode files are affected, not one

---

### BUG-02: THF Atom Count Inconsistency (12 vs 13 vs 14)
**Status: PARTIALLY CONFIRMED — documentation error, not runtime bug**

**Evidence:**
- `quickice/structure_generation/types.py:17`: `"thf": {"atoms": 12, ...}` — **WRONG** (should be 13)
- `quickice/structure_generation/types.py:87`: `"thf": {"atoms": 12, ...}` — **WRONG** (should be 13)
- `quickice/utils/molecule_utils.py:77`: Comment says "C5H8O = 14 atoms" — **WRONG** formula (THF = C4H8O = 13 atoms)
- `quickice/output/gromacs_writer.py:841`: Comment says "C5H8O (5 C, 8 H, 1 O = 14 atoms typically)" — **WRONG** formula
- `quickice/output/gromacs_writer.py:843`: Comment says "13 atoms" — **CORRECT**
- `quickice/structure_generation/hydrate_generator.py:489`: Docstring says "13 atoms" — **CORRECT**
- `quickice/gui/solute_renderer.py:5`: Says "C4H8O" — **CORRECT** formula

**Runtime impact: NONE** — `MOLECULE_TYPE_INFO` dict is imported in `hydrate_generator.py` and `gromacs_writer.py` but never accessed by key (dead import). Runtime uses `count_guest_atoms()` which correctly returns 13 for THF, and `hydrate_generator._build_molecule_index()` uses residue-based detection that correctly identifies 13-atom THF molecules.

**Updated severity: Low** — misleading documentation only; no runtime bug. The formula errors (C5H8O → C4H8O) should be corrected.

---

### BUG-03: Residue Number Lookup Uses `molecule_index.index(mol)` — O(n²) in GRO Writer
**Status: CONFIRMED**

**Evidence:**
- `quickice/output/gromacs_writer.py:1102`: `res_num = (molecule_index.index(mol) + 1) % 100000`
- This is inside a `for mol in molecule_index:` loop (line 1093)
- `list.index()` is O(n) per call, total O(n²) for n molecules
- Fix: use `enumerate(molecule_index)` to get index directly

**Severity: Medium** — causes quadratic slowdown for large systems (>10,000 molecules)

---

### BUG-04: Degenerate Diversity Score
**Status: CONFIRMED**

**Evidence:**
- `quickice/ranking/scorer.py:196-234`: `diversity_score()` computes `1.0 / same_seed_count`
- `same_seed_count` from `Counter(all_seeds)` at line 229
- Since `generate_all()` uses sequential unique seeds, `same_seed_count` is always 1
- Therefore `diversity_score = 1.0` for all candidates
- No discriminatory value in ranking

**Severity: Low** — ranking still works via energy and density scores; diversity just provides zero contribution

---

## Security Considerations

### SEC-01: Path Traversal Risk in CLI Output Path
**Status: CONFIRMED**

**Evidence:**
- `quickice/main.py:127`: `output_path = Path(args.output)` — no sanitization
- `quickice/main.py:131`: `base_name = f"interface_{phase_info['phase_id']}_{config.mode}"` — `phase_id` used in filename without validation
- No `Path.resolve()` or boundary checks
- The output orchestrator (`output/orchestrator.py`) has protections but main.py doesn't use them

**Severity: Low** — CLI-only; GUI paths go through Qt file dialogs which prevent traversal

---

### SEC-02: Shell=True in UAT Test Runner
**Status: CONFIRMED**

**Evidence:**
- `.planning/milestones/v1.0-run_uat_tests.py:24`: `shell=True` in subprocess call
- File exists in repository, not part of installed application
- Command being run uses user-provided input strings

**Severity: Very Low** — not shipped, but should be cleaned up or deleted

---

## Performance Bottlenecks

### PERF-01: O(n²) H-Bond Detection in vtk_utils.py
**Status: FALSE ALARM — FIXED by Quick Task 022**

**Evidence:**
- `quickice/gui/vtk_utils.py:9`: `from scipy.spatial import cKDTree` — KDTree import present
- `quickice/gui/vtk_utils.py:282`: `tree = cKDTree(supercell_h)` — KDTree built from supercell
- `quickice/gui/vtk_utils.py:295`: `indices = tree.query_ball_point(o_pos, max_distance)` — KDTree query
- Tests exist: `tests/test_pbc_hbonds.py` (6 tests, all passing)
- Complexity is now O(n log n), not O(n²)
- Commits: `447885c`, `db9badd`, `d4a333e`

---

### PERF-02: 27× Memory Overhead in Scorer Supercell
**Status: CONFIRMED**

**Evidence:**
- `quickice/ranking/scorer.py:53-61`: Builds 3×3×3 supercell:
  ```python
  for i in (-1, 0, 1):
      for j in (-1, 0, 1):
          for k in (-1, 0, 1):
              offset = np.array([i, j, k]) * cell_dims
              supercell_o.append(o_positions + offset)
  supercell_o = np.vstack(supercell_o)
  ```
- 27 copies of O positions created for KDTree PBC handling
- cKDTree `boxsize=` parameter could help for orthorhombic cells but not triclinic (Ice II, V)

**Severity: Low** — scorer is used for ranking only, not real-time; typical systems have <1000 oxygen atoms

---

### PERF-03: Pocket Mode Fills Entire Box Then Filters
**Status: PARTIALLY FIXED**

**Evidence:**
The code was optimized since the concern was written:
- `quickice/structure_generation/modes/pocket.py:248-255`: Now fills only the cavity bounding box `(2r × 2r × 2r)`, NOT the entire box
- `quickice/structure_generation/modes/pocket.py:263-266`: `fill_region_with_water(fill_dims, ...)` uses bounding box dimensions
- Remaining waste: For spherical cavities, water in bounding-box corners (outside sphere) is still generated then filtered (lines 279-287)

**Updated severity: Very Low** — major optimization already done; remaining waste is minor (corner regions only)

---

### PERF-04: Water Template Module-Level Cache Race Condition
**Status: DUPLICATE of TD-06**

Same issue as TD-06. `quickice/structure_generation/water_filler.py:234` uses `global _water_template_cache` pattern. Not a separate concern.

---

## Fragile Areas

### FRAG-01: Cross-Tab Data Flow (Interface → Custom → Solute → Ion)
**Status: CONFIRMED**

**Evidence:**
- `quickice/gui/main_window.py:1193-1219`: After custom molecule insertion:
  - `self.solute_panel.set_custom_molecule_structure(result)` (line 1194)
  - `self.solute_panel.set_liquid_volume(liquid_vol)` (line 1206)
  - `self.ion_panel.set_custom_molecule_structure(result)` (line 1215)
  - `self.ion_panel.set_liquid_volume(liquid_vol)` (line 1219)
- Uses `hasattr(result, 'water_atom_count')` and `getattr` patterns extensively (lines 1200-1209)
- Debug-level logging left in production code: `[Liquid Volume Debug]` and `[Water Count Debug]` markers at `logger.info()` level (lines 1199-1234)
- If any attribute name changes or any tab is skipped, downstream tabs silently get defaults

**Additional finding:** Verbose debug logs (`[Liquid Volume Debug]`, `[Water Count Debug]`) at `logger.info()` level in main_window.py:1199-1234 should be at `logger.debug()` level.

**Severity: Medium** — works correctly in normal flows; fragile to refactoring

---

### FRAG-02: Atom Count Invariants Across Interface Generation
**Status: CONFIRMED**

**Evidence:**
- CRIT-01 is FIXED: `quickice/output/gromacs_writer.py:642-645` correctly computes `n_atoms = ice_nmolecules * 4 + water_nmolecules * 4 + guest_atom_count`
- CRIT-02 is FIXED: Water iteration uses `water_start + mol_idx * 4` (line 737-738)
- BUT: No explicit assertion that `water_atom_count == water_nmolecules * 4` after overlap removal
- The guest-water overlap fix in `quickice/structure_generation/modes/slab.py:527-549` does a second round of overlap removal, but no invariant check follows

**Severity: Medium** — currently works correctly but no safety net if overlap removal breaks

---

### FRAG-03: GROMACS Export Pipeline (2054 lines in gromacs_writer.py)
**Status: CONFIRMED**

**Evidence:**
- `quickice/output/gromacs_writer.py` is 2054 lines
- Contains 15+ write functions for different structure types
- `detect_guest_type_from_atoms()` at line 831 uses heuristic pattern matching
- `reorder_guest_atoms()` depends on exact GenIce2 atom naming
- `comment_out_atomtypes_in_itp()` modifies user ITP content

**Severity: Medium** — complex single-file module; refactoring would improve maintainability

---

### FRAG-04: ITP File Residue Name Matching
**Status: CONFIRMED**

**Evidence:**
- `quickice/structure_generation/itp_parser.py:65-77`: Uses regex `r'\[\s*moleculetype\s*\]\s*\n\s*;.*?\n\s*(\w+)'` with fallback pattern
- `quickice/structure_generation/molecule_validator.py:18`: `GENERIC_RESIDUE_NAMES = {"MOL", "UNK", "LIG", "XXX", "RES"}`
- Hardcoded whitelist could miss new generic names
- `quickice/structure_generation/gro_parser.py:141-145`: Fixed-width column parsing for GRO residue names

**Severity: Low** — works for current use cases; edge cases possible with unusual user files

---

## Unit Mismatches

### UNIT-01: No Explicit Unit Validation at Data Entry Points
**Status: CONFIRMED**

**Evidence:**
- No systematic unit validation exists
- Reactive checks:
  - `quickice/ranking/scorer.py:183-190`: `density_score()` raises ValueError if density outside 0.1-10.0 g/cm³
  - `quickice/structure_generation/types.py:179-189`: `InterfaceConfig.__post_init__()` validates `overlap_threshold` in [0.1, 1.0] nm
  - `quickice/output/gromacs_writer.py:635-636`: Warning if `max_coord > 100`
- No validation in `gro_parser.py` that coordinates < 50 nm for typical molecular systems

**Severity: Medium** — Å→nm mixup would cause 10× length error; current checks catch most cases

---

### UNIT-02: IAPWS Water Density — Fallback Values Without User Visibility
**Status: CONFIRMED**

**Evidence:**
- `quickice/phase_mapping/water_density.py:70-92`: Falls back to `FALLBACK_DENSITY_GCM3 = 0.9998`
- `quickice/phase_mapping/water_density.py:85-86, 91-92`: Logs at `logger.warning()` level
- No visual indicator in GUI when fallback is used
- Fallback value introduces ~0.3% error at 273.15 K / 0.1 MPa

**Severity: Very Low** — error is negligible; fallback is rarely triggered

---

### UNIT-03: IAPWS Warning Suppression for Supercooled Water Extrapolation
**Status: CONFIRMED**

**Evidence:**
- `quickice/phase_mapping/water_density.py:73-74`: `warnings.filterwarnings("ignore", message="extrapolated")`
- Suppressed within context manager, not globally
- IAPWS-95 is designed for extrapolation; suppressed warnings are physically reasonable
- No logging of extrapolation events (even at debug level)

**Severity: Very Low** — IAPWS-95 extrapolation is robust; adding debug-level logging would be nice

---

## Scientific Accuracy Concerns

### SCI-01: Ice Ih Density Uses IAPWS R10-06(2009) — Correct But Limited Range
**Status: CONFIRMED**

**Evidence:**
- `quickice/phase_mapping/ice_ih_density.py:63-75`: IAPWS calculation with fallback
- Fallback `FALLBACK_DENSITY_GCM3 = 0.9167` at 273.15 K / 0.1 MPa (line 33)
- When P > 208.566 MPa or T > 273.16 K, falls back to 0.9167 regardless of actual T/P
- Ice Ih is not stable above 208.566 MPa, so fallback is mostly for inappropriate conditions

**Severity: Low** — fallback conditions are outside Ice Ih stability range anyway

---

### SCI-02: Water Density Scaling Assumption in Interface Modes
**Status: CONFIRMED**

**Evidence:**
- Uniform scaling `scale = (template_density / target_density)^(1/3)` used in slab.py
- TIP4P water template is cubic, so uniform scaling is appropriate
- IAPWS density varies by <5% in typical conditions (0-50°C, 0-100 MPa)

**Severity: Very Low** — assumption is physically reasonable for typical conditions

---

### SCI-03: O-O Distance Cutoff Values Lack Literature Citations
**Status: CONFIRMED**

**Evidence:**
- `quickice/ranking/types.py:21`: `ideal_oo_distance: float = 0.276` — no citation
- `quickice/ranking/types.py:22`: `oo_cutoff: float = 0.35` — no citation
- 0.276 nm is the typical O-O distance in ice Ih (Bernal-Fowler rules)
- 0.35 nm is a standard cutoff for first hydration shell

**Severity: Very Low** — values are well-known in literature; adding citations would improve scientific rigor

---

### SCI-04: Ion VDW Radii From Madrid2019 Without Version Tracking
**Status: PARTIALLY FIXED**

**Evidence:**
- Quick Task 026 added Madrid2019 citation to `README.md` and `docs/gui-guide.md`
- `quickice/structure_generation/gromacs_ion_export.py:22`: Code comment says `# VDW parameters (from Madrid2019_085.top)` — version IS documented in code
- `quickice/structure_generation/gromacs_ion_export.py:19`: `NA_CHARGE = 0.85` and `CL_CHARGE = -0.85` — consistent with Madrid2019_085 (not Madrid2019_1 which uses ±1.0)
- But the ITP file header generated at export time does NOT include the version string

**Remaining gap:** The generated `ion.itp` file should include a comment identifying it as Madrid2019_085 specifically.

**Updated severity: Very Low** — version IS documented in code comments; generated ITP could be clearer

---

## Exception Handling Issues

### EXC-01: IAPWS Failures Logged at Wrong Level in phase_diagram_widget.py
**Status: FIXED by Quick Task 027**

**Evidence:**
- `quickice/gui/phase_diagram_widget.py:81-82`: `except Exception as e: logger.warning(f"...")` ✓
- `quickice/gui/phase_diagram_widget.py:483-484`: `except Exception as e: logger.warning(f"...")` ✓
- Bare `except:` was replaced with `except Exception as e:`
- Logging level upgraded from debug to warning

**Remaining gap:** No visual indication in the GUI when IAPWS calculation fails (diagram may have missing boundary lines without user awareness). This is now a UI feedback issue, not an exception handling issue.

---

### EXC-02: Silent FileNotFoundError for Guest ITP Files During Export
**Status: CONFIRMED**

**Evidence:**
- `quickice/gui/export.py:332-335`: `except FileNotFoundError: pass` — silent, with comment "will cause GROMACS to fail but don't block export"
- `quickice/gui/export.py:876-879`: `except FileNotFoundError: pass` — same pattern
- User gets a .top file that references a non-existent .itp file, causing GROMACS to fail with no indication why

**Severity: Medium** — the exported files are broken but the user isn't told; a QMessageBox warning would fix this

---

### EXC-03: Three Export Handlers Missing traceback.print_exc()
**Status: FIXED by Quick Task 027**

**Evidence:**
- `quickice/gui/export.py:372`: `traceback.print_exc()` ✓ (IonGROMACSExporter)
- `quickice/gui/export.py:727`: `traceback.print_exc()` ✓ (GROMACSExporter)
- `quickice/gui/export.py:884`: `traceback.print_exc()` ✓ (InterfaceGROMACSExporter)
- Additionally, two more handlers now have traceback: lines 148 and 227

All five top-level export exception handlers now print tracebacks.

---

## PyInstaller Bundle Size Concerns

### BUNDLE-01: `collect_all()` For 9 Packages With No Excludes
**Status: CONFIRMED**

**Evidence:**
- `quickice-gui.spec:9`: `for pkg in ['iapws', 'genice2', 'genice_core', 'matplotlib', 'scipy', 'numpy', 'shapely', 'networkx', 'spglib']:`
- `quickice-gui.spec:11`: `tmp_ret = collect_all(pkg)` — collects ALL files from each package
- `quickice-gui.spec:27`: `excludes=[]` — empty excludes list
- `quickice-gui.spec:42`: `upx=True` — UPX compression enabled

**Severity: Low** — bundle works; waste is 50-200 MB estimated; UPX partially mitigates

---

### BUNDLE-02: GenIce2 Includes All Lattice/Molecule/Format Plugins
**Status: CONFIRMED**

**Evidence:**
- `quickice-gui.spec:9`: `collect_all('genice2')` — includes all plugins
- QuickIce only uses specific lattice modules (defined in `generator.py` and `hydrate_generator.py`)
- Unused lattice types, format modules (PDB, CIF), and molecule types are bundled

**Severity: Low** — waste is modest; GenIce2 plugin system makes selective collection harder

---

## Test Coverage Gaps

### TEST-01: GROMACS Export End-to-End Testing
**Status: CONFIRMED**

No test for the full interface→custom→solute→ion export chain exists.

**Severity: High** — the most complex code path in the application has no end-to-end test

---

### TEST-02: Pocket Mode Edge Cases
**Status: CONFIRMED**

No tests for very thin cavities, large boxes with small pockets, or non-spherical cavities.

**Severity: Medium**

---

### TEST-03: Triclinic Cell Interface Generation
**Status: CONFIRMED**

Triclinic cell handling blocked by `TriclinicCellError` check; test coverage is minimal.

**Severity: Medium** (currently blocked by design)

---

### TEST-04: Custom Molecule ITP Parsing Edge Cases
**Status: CONFIRMED**

No tests for non-standard ITP formatting (BOM, Windows line endings, extra whitespace).

**Severity: Medium**

---

### TEST-05: Atom Count Consistency After Multiple Overlap Removal Steps
**Status: CONFIRMED**

No test for the invariant `water_atom_count == water_nmolecules * 4` after the guest-water overlap fix in slab.py:532-554.

**Severity: High** — invariant breakage would cause incorrect GRO files

---

## Previously Identified Issues — Current Status

| Issue | Previous Status | Current Status | Evidence |
|-------|----------------|----------------|---------|
| CRIT-01 (Atom Count Mismatch) | FIXED | STILL FIXED | gromacs_writer.py:642-645 correctly computes n_atoms |
| CRIT-02 (Index Overflow) | FIXED | STILL FIXED | gromacs_writer.py:737-738 uses water_start + mol_idx * 4 |
| CRIT-03 (Inconsistent Atom Names) | FIXED | STILL FIXED | vtk_utils.py properly checks i < iface.ice_atom_count |
| Exception Safety in Generator | FIXED | STILL FIXED | generator.py:101-157 uses try/finally |
| Bare except in Phase Diagram | FIXED | STILL FIXED | phase_diagram_widget.py:81 uses except Exception as e |
| Silent None Return in gro_parser | FIXED | STILL FIXED | gro_parser.py:147-148 logs warning |
| IAPWS Warning Level | PARTIALLY FIXED | STILL PARTIALLY FIXED | Warning level correct; no GUI indicator |
| Degenerate Diversity Score | NOT FIXED | STILL NOT FIXED | scorer.py:234 still returns 1.0 for all |
| 27× Memory Overhead | NOT FIXED | STILL NOT FIXED | scorer.py:53-61 still builds 3×3×3 supercell |
| Debug Print Statements | NOT VERIFIED | FALSE ALARM | No stray print() statements in production code |

### Issues Fixed by Quick Tasks (New)

| Quick Task | Issue Fixed | Commit |
|------------|-------------|--------|
| QT-021 | TD-02: Removed unused `build_molecule_index()` | `187368f` |
| QT-022 | PERF-01: Replaced O(n²) H-bond with KDTree | `447885c`, `db9badd`, `d4a333e` |
| QT-026 | SCI-04: Added Madrid2019 citation to docs | `3858b0e`, `cfc5286` |
| QT-027 | EXC-01: Upgraded IAPWS failure logging | `bae1c9b` |
| QT-027 | EXC-03: Added traceback to export handlers | `719de7f` |
| QT-027 | gro_parser silent return fix (re-verified) | `bae1c9b` |

---

## Additional Findings (Not in CONCERNS.md)

### NEW-01: Verbose Debug Logging in main_window.py
**Evidence:** `quickice/gui/main_window.py:1199-1234` contains debug-level log messages at `logger.info()` level with markers like `[Liquid Volume Debug]` and `[Water Count Debug]`. These should be at `logger.debug()` level.
**Severity: Very Low**

### NEW-02: Dead Import of MOLECULE_TYPE_INFO
**Evidence:** `MOLECULE_TYPE_INFO` is imported in `hydrate_generator.py:15` and `gromacs_writer.py:14` but never accessed by key (`MOLECULE_TYPE_INFO[...]` yields zero results). This is a dead import. The misleading THF atom count (12 vs 13) in the dict is never used at runtime.
**Severity: Very Low** — dead import only

### NEW-03: THF Formula Error in Comments
**Evidence:** `molecule_utils.py:77` and `gromacs_writer.py:841` say "C5H8O" for THF. The correct formula is C4H8O (tetrahydrofuran). C4H8O = 4C + 8H + 1O = 13 atoms. The code returns 13 correctly, but the formula comment is wrong.
**Severity: Very Low** — comment-only error

---

*Verified: 2026-05-22*
*Verifier: OpenCode (gsd-verifier)*
