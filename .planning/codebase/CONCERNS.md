# Codebase Concerns

**Analysis Date:** 2026-05-22

## Tech Debt

### TD-01: Duplicate Mode Functions Across slab.py, pocket.py, piece.py
- Issue: Three functions (`detect_atoms_per_molecule`, `_detect_guest_atoms`, `_count_guest_molecules`) are duplicated across all three mode files with nearly identical implementations. The `pocket.py` version of `_detect_guest_atoms` is simplified (missing the OW-safeguard that `slab.py` and `piece.py` have), creating an inconsistency bug.
- Files: `quickice/structure_generation/modes/slab.py:24-122`, `quickice/structure_generation/modes/pocket.py:24-85`, `quickice/structure_generation/modes/piece.py:31-117`
- Impact: Bug in pocket.py (no safeguard against misclassifying water as guest), maintenance burden (changes must be made 3×), ~150 lines of duplicate code
- Fix approach: Consolidate to `quickice/utils/molecule_utils.py`. The `count_guest_atoms` function was already consolidated there. Bring the remaining three functions there. Add the OW-safeguard to pocket.py's `_detect_guest_atoms` immediately (copy from slab.py lines 82-93).

### TD-02: Unused `build_molecule_index()` in molecule_utils.py
- Issue: Public function `build_molecule_index()` (70 lines) was created as a "future consolidation target" but never wired up. Private implementations in `hydrate_generator.py:_build_molecule_index()` and `ion_inserter.py:_build_molecule_index_from_structure()` have diverged and remain in use.
- Files: `quickice/utils/molecule_utils.py:111-180`
- Impact: Dead code confusing maintainers; 70 lines of unreachable code
- Fix approach: Delete the function. Verified zero imports across the entire codebase.

### TD-03: Debug Scripts Never Cleaned Up (6,126 lines)
- Issue: 42 Python scripts in `.planning/debug/` (1.7 MB, 6,126 lines) are never referenced by the application or test suite. Includes resolved, deferred, and active subdirectories.
- Files: `.planning/debug/resolved/` (13 files), `.planning/debug/deferred/` (19 files), `.planning/debug/` (8 files, plus `.md` files)
- Impact: Repository bloat, confusing for contributors who may think these are required
- Fix approach: Delete `.planning/debug/resolved/` and `.planning/debug/deferred/` immediately (zero risk). Review active scripts individually — convert useful ones to proper tests in `tests/`, delete the rest.

### TD-04: Duplicate Comment Lines Across Multiple Files
- Issue: Several files have identical comment lines repeated 3× (likely from copy-paste errors during development).
- Files: `quickice/structure_generation/modes/slab.py:19-21`, `quickice/structure_generation/modes/pocket.py:19-21`, `quickice/structure_generation/water_filler.py:137-139`, `quickice/gui/molecular_viewer.py:29-31`, `quickice/gui/hydrate_renderer.py:25-27`
- Impact: Minor code cleanliness, confusing for readers
- Fix approach: Remove duplicate lines, keeping only one copy of each comment.

### TD-05: Global Random State Pollution in GenIce
- Issue: `IceStructureGenerator._generate_single()` saves/restores `np.random` global state around GenIce calls. If GenIce raises an exception between `np.random.seed(seed)` and `np.random.set_state(original_state)`, the global state could be left in a modified state. The code now uses `try/finally` (fixed from original report), but the fundamental approach of manipulating global state is fragile and NOT thread-safe.
- Files: `quickice/structure_generation/generator.py:100-157`
- Impact: Reproducibility issues in concurrent usage; documented as NOT thread-safe
- Fix approach: Use numpy's Generator API (`rng = np.random.Generator(np.random.PCG64(seed))`) when GenIce supports it. Current `try/finally` pattern is adequate for single-threaded use. No immediate fix needed.

### TD-06: Module-Level Global Caches Without Thread Safety
- Issue: `_water_template_cache` in `water_filler.py` and `_genice_lib`/`_gromacs_format`/`_lattice_modules_loaded` in `hydrate_generator.py` are module-level globals with no thread locks.
- Files: `quickice/structure_generation/water_filler.py:144`, `quickice/structure_generation/hydrate_generator.py:28-30`
- Impact: Race condition in multi-threaded usage could cause double-loading. Current design is sequential so this is low risk.
- Fix approach: Add `threading.Lock` around cache access, or use `functools.lru_cache`. Low priority since QuickIce is single-threaded.

### TD-07: ITP Atomtypes Section Handling Requires Manual Commenting
- Issue: User-provided ITP files may contain `[ atomtypes ]` sections that conflict with the main `.top` file's `[ atomtypes ]`. QuickIce works around this by running `comment_out_atomtypes_in_itp()` at export time, which modifies the ITP content before writing. This is a hack — the proper approach is to tell users not to include atomtypes in their ITP files, or to validate at upload time.
- Files: `quickice/output/gromacs_writer.py:310-354`, `quickice/gui/export.py:211-216`, `quickice/gui/export.py:347-351`, `quickice/gui/export.py:361-365`
- Impact: User confusion about why their ITP file is different after export; silent modification of user files
- Fix approach: At upload time (in `custom_molecule_panel.py`), detect `[ atomtypes ]` and warn the user that it will be commented out at export. Or split atomtypes into a separate file during upload.

---

## Known Bugs

### BUG-01: Pocket Mode `_detect_guest_atoms` Missing OW Safeguard
- Symptoms: Water molecules can be misclassified as guest molecules in pocket mode when atom counting errors occur. This doesn't happen in slab.py or piece.py because they have the OW-safeguard check (lines 82-93 in slab.py).
- Files: `quickice/structure_generation/modes/pocket.py:44-69`
- Trigger: Hydrate candidates where TIP4P water molecules appear at unexpected positions in the atom_names list
- Workaround: None — this is a latent bug that may surface with certain GenIce2 hydrate outputs

### BUG-02: THF Atom Count Inconsistency (12 vs 13 vs 14)
- Symptoms: THF atom count is documented as both 12 and 13 and 14 atoms in different places. `MOLECULE_TYPE_INFO` in `types.py` says 12, `GUEST_MOLECULES` says 12, but `_get_molecule_atoms()` in `gromacs_writer.py:843` says "GenIce2 THF: O, CA, CA, CB, CB, H, H, H, H, H, H, H, H (13 atoms)", and the chemical formula C4H8O = 14 atoms.
- Files: `quickice/structure_generation/types.py:17` (12 atoms), `quickice/structure_generation/types.py:86` (12 atoms), `quickice/output/gromacs_writer.py:843` (13 atoms comment)
- Trigger: GRO/ITP validation may report false atom count mismatches for THF. Export may write wrong number of atoms.
- Workaround: The `count_guest_atoms()` function detects from atom names, not hardcoded counts, which mitigates the issue in practice.

### BUG-03: Residue Number Lookup Uses `molecule_index.index(mol)` — O(n²) in GRO Writer
- Symptoms: `write_multi_molecule_gro_file()` uses `molecule_index.index(mol)` on line 1102 to compute residue numbers. `list.index()` is O(n) per call, and it's inside a loop over all molecules, making the total O(n²).
- Files: `quickice/output/gromacs_writer.py:1102`
- Trigger: Large systems with thousands of molecules will experience quadratic slowdown during export
- Workaround: Use `enumerate(molecule_index)` instead to get the index directly.

### BUG-04: Degenerate Diversity Score
- Symptoms: `diversity_score()` in `scorer.py` computes `1.0 / same_seed_count` where `same_seed_count` is always 1 (since `generate_all()` uses sequential unique seeds). This means diversity_score = 1.0 for all candidates, providing zero discriminatory value.
- Files: `quickice/ranking/scorer.py:196-234`
- Trigger: Always occurs — the diversity score is functionally useless
- Workaround: The score still contributes to ranking via normalization, but provides no actual diversity discrimination. Implement structural fingerprint diversity (RDF, bond angle distributions) for meaningful results.

---

## Security Considerations

### SEC-01: Path Traversal Risk in CLI Output Path
- Risk: `quickice/main.py` uses `Path(args.output)` directly without sanitization. If `phase_info['phase_id']` contains path traversal characters (e.g., `../../etc`), generated filenames could write outside the intended directory.
- Files: `quickice/main.py:127-158`
- Current mitigation: The CLI orchestrator in `output/orchestrator.py` has path traversal protection, but the main.py path does not.
- Recommendations: Add `Path.resolve()` and validate output is within expected directory. Sanitize `phase_id` before using in filenames.

### SEC-02: Shell=True in UAT Test Runner
- Risk: `.planning/milestones/v1.0-run_uat_tests.py` uses `shell=True` in subprocess call. While this file is not part of the application, it exists in the repository.
- Files: `.planning/milestones/v1.0-run_uat_tests.py:22-25`
- Current mitigation: Not part of the installed application
- Recommendations: Remove `shell=True` and pass command as list, or delete the file if no longer needed.

---

## Performance Bottlenecks

### PERF-01: O(n²) H-Bond Detection in vtk_utils.py
- Problem: `detect_hydrogen_bonds()` uses nested loop over H atoms × O atoms. For n molecules, complexity is O(n²). At 10,000 molecules this takes 2-5 seconds.
- Files: `quickice/gui/vtk_utils.py:272-290`
- Cause: Simple pairwise distance check with PBC support, no spatial indexing
- Improvement path: Replace with supercell KDTree approach (already proven in `quickice/ranking/scorer.py:21-80`). Estimated speedup: 5-100× for large structures. See detailed assessment in `.planning/code_analysis/20260512_on2_loop_fix_assessment.md`.

### PERF-02: 27× Memory Overhead in Scorer Supercell
- Problem: `_calculate_oo_distances_pbc()` builds a 3×3×3 supercell (27 copies) for PBC-aware O-O distance calculation. For 100,000 oxygen atoms, this allocates ~650 MB.
- Files: `quickice/ranking/scorer.py:53-61`
- Cause: Using explicit supercell replication for KDTree compatibility
- Improvement path: Use minimum image convention directly with cKDTree's `boxsize=` parameter. However, `boxsize=` only works for orthorhombic cells — ice II and V are triclinic. For the scorer (used only for ice structure ranking, not interfaces), most ice phases are orthorhombic, so `boxsize=` could be used with a triclinic-cell fallback.

### PERF-03: Pocket Mode Fills Entire Box Then Filters
- Problem: Pocket mode calls `fill_region_with_water()` for the entire box, then removes water molecules outside the cavity. For large boxes with small pockets, this creates many unnecessary water molecules.
- Files: `quickice/structure_generation/modes/pocket.py:94-124`
- Cause: Water filler doesn't support filling arbitrary-shaped regions
- Improvement path: Calculate cavity volume first and only fill that region. Medium priority since typical pocket sizes are reasonable.

### PERF-04: Water Template Module-Level Cache Race Condition
- Problem: `load_water_template()` uses a module-level `_water_template_cache` without thread safety.
- Files: `quickice/structure_generation/water_filler.py:228-253`
- Cause: Global mutable state without synchronization
- Improvement path: Use `functools.lru_cache` or threading lock. Low priority since QuickIce is single-threaded.

---

## Fragile Areas

### FRAG-01: Cross-Tab Data Flow (Interface → Custom → Solute → Ion)
- Files: `quickice/gui/main_window.py:1170-1279`, `quickice/gui/solute_panel.py`, `quickice/gui/ion_panel.py`, `quickice/gui/custom_molecule_panel.py`
- Why fragile: Data flows through 4+ tabs with manual attribute passing via `getattr(structure, 'attr', default)`. Each tab passes its result to downstream tabs by calling `set_custom_molecule_structure()`, `set_liquid_volume()`, etc. The ion inserter must preserve ALL upstream attributes (solute_type, solute_positions, custom_molecule_count, custom_gro_path, etc.) through `getattr` chains. If any attribute name changes or any tab is skipped, downstream tabs silently get defaults.
- Safe modification: Always test the full chain (interface → custom → solute → ion) after any changes to structure dataclass fields. Add assertions in each tab's `set_*()` method to verify required attributes exist.
- Test coverage: `tests/test_solute_ion_molecule_index.py`, `tests/test_integration_v35.py` cover parts of this chain, but full end-to-end testing is limited.

### FRAG-02: Atom Count Invariants Across Interface Generation
- Files: `quickice/structure_generation/modes/slab.py`, `quickice/structure_generation/modes/pocket.py`, `quickice/structure_generation/modes/piece.py`, `quickice/output/gromacs_writer.py:606-812`
- Why fragile: The critical invariants `ice_atom_count == ice_nmolecules * atoms_per_ice_mol` and `water_atom_count == water_nmolecules * 4` must hold after overlap removal. If overlap removal removes partial molecules (it shouldn't, but the code is complex), these invariants break, causing incorrect GRO file headers and wrong atom indexing in exports.
- Safe modification: Add assertion checks after each overlap removal step. The GRO writer now correctly computes `n_atoms` from `ice_nmolecules * 4 + water_nmolecules * 4 + guest_atom_count` (the CRIT-01 bug from earlier reports is FIXED), but the invariant is not explicitly validated.
- Test coverage: `tests/test_atom_ordering_validation.py`, `tests/test_interface_ordering_validation.py` partially cover this. Need explicit invariant assertions.

### FRAG-03: GROMACS Export Pipeline (2054 lines in gromacs_writer.py)
- Files: `quickice/output/gromacs_writer.py`
- Why fragile: Single 2054-line file containing 15+ write functions for different structure types (candidate, interface, ion, custom, multi-molecule). Guest atom reordering logic (`reorder_guest_atoms()`) depends on exact atom naming from GenIce2, which may differ from .itp canonical order. The `detect_guest_type_from_atoms()` function uses heuristic atom pattern matching that could fail for unusual molecule types.
- Safe modification: Add explicit guest type tracking in InterfaceStructure (instead of re-detecting from atom names at export time). Split the file into per-structure-type writers.
- Test coverage: `tests/test_gromacs_molecule_ordering.py` covers atom ordering, but not all export paths.

### FRAG-04: ITP File Residue Name Matching
- Files: `quickice/structure_generation/itp_parser.py:34-138`, `quickice/structure_generation/gro_parser.py:103-149`, `quickice/structure_generation/molecule_validator.py:43-194`
- Why fragile: ITP parser uses regex to extract moleculetype name, which can fail for non-standard formatting. GRO residue name extraction relies on fixed-width column parsing that assumes well-formed files. The `validate_custom_molecule()` function compares GRO residue name to ITP moleculetype name, but GRO files often use generic names like "MOL" or "UNK". The validator has a whitelist of generic names (`GENERIC_RESIDUE_NAMES = {"MOL", "UNK", "LIG", "XXX", "RES"}`) to skip mismatches, but this is fragile — any new generic name would cause false warnings.
- Safe modification: Make the generic names list configurable. Add validation for ITP regex patterns against known GenIce2 output formats. Improve error messages to distinguish between "generic name expected" and "real mismatch detected".
- Test coverage: `tests/test_moleculetype_registry.py`, but ITP parsing edge cases are undertested.

---

## Unit Mismatches

### UNIT-01: No Explicit Unit Validation at Data Entry Points
- Risk: The codebase uses nanometers (nm) throughout, but has no systematic unit validation. If coordinates in Ångströms are passed where nm is expected, the error will be massive (10× in length, 1000× in volume, 1000× in density). The `density_score()` function has a sanity check (0.1-10.0 g/cm³), and the GRO writer warns if max coordinate > 100, but these are reactive, not preventive.
- Files: `quickice/ranking/scorer.py:183-190`, `quickice/output/gromacs_writer.py:633-636`
- Current mitigation: `density_score()` raises ValueError if density is outside 0.1-10.0 g/cm³ (catches Å→nm mixup). `overlap_resolver.py` validates `threshold_nm` is in [0.1, 1.0] nm. `InterfaceConfig.__post_init__()` validates `overlap_threshold`. GRO writer warns if max_coord > 100.
- Recommendations: Add unit validation at ALL data entry points: `gro_parser.py` (check coordinates < 50 nm for typical molecular systems), user input validation (display unit labels in GUI).

### UNIT-02: IAPWS Water Density — Fallback Values Without User Visibility
- Risk: `water_density_gcm3()` falls back to 0.9998 g/cm³ when IAPWS fails. This affects 3D model generation (water layer density scaling in slab.py, pocket.py, piece.py). The fallback is logged at `logger.warning()` level but not shown in the GUI.
- Files: `quickice/phase_mapping/water_density.py:70-92`, `quickice/structure_generation/modes/slab.py:224-229`
- Current mitigation: Fallback value (0.9998 g/cm³ at 273.15 K) introduces ~0.3% error — negligible for most simulations.
- Recommendations: Add visual indicator in GUI when fallback is used. See detailed analysis in `.planning/code_analysis/20260516_iapws_water_density_research.md`.

### UNIT-03: IAPWS Warning Suppression for Supercooled Water Extrapolation
- Risk: `water_density_gcm3()` suppresses IAPWS extrapolation warnings with `warnings.filterwarnings("ignore", message="extrapolated")`. Users may not know when extrapolated (potentially less accurate) values are used for supercooled water.
- Files: `quickice/phase_mapping/water_density.py:70-72`
- Current mitigation: IAPWS-95 is designed for extrapolation and is robust. The extrapolation is physically reasonable.
- Recommendations: Log extrapolation events at `logger.debug()` level at minimum.

---

## Scientific Accuracy Concerns

### SCI-01: Ice Ih Density Uses IAPWS R10-06(2009) — Correct But Limited Range
- Issue: Ice Ih density calculation uses IAPWS R10-06(2009) formulation, valid for T ≤ 273.16 K and P ≤ 208.566 MPa. Above these limits, the code falls back to hardcoded 0.9167 g/cm³. This is correct (Ice Ih is not stable above 208.566 MPa), but the fallback value is at 273.15 K / 0.1 MPa, not at the actual T/P.
- Files: `quickice/phase_mapping/ice_ih_density.py`
- Impact: Small — Ice Ih isn't stable in those ranges, so the fallback is only hit when users select inappropriate conditions.
- Recommendations: Return the density at the stability boundary rather than 273.15 K / 0.1 MPa, or show a warning that conditions are outside Ice Ih stability range.

### SCI-02: Water Density Scaling Assumption in Interface Modes
- Issue: Slab, pocket, and piece modes scale the TIP4P water template to match target density via `scale = (template_density / target_density)^(1/3)`. This assumes uniform scaling in all three dimensions, which is correct for cubic water templates but may not preserve molecular geometry optimally for highly anisotropic temperature/pressure conditions.
- Files: `quickice/structure_generation/modes/slab.py:224-229`, `quickice/structure_generation/water_filler.py:183-213`
- Impact: Negligible for typical conditions (0-50°C, 0-100 MPa). IAPWS density varies by <5% in this range.
- Recommendations: No change needed for typical use.

### SCI-03: O-O Distance Cutoff Values Lack Literature Citations
- Issue: `IDEAL_OO_DISTANCE = 0.276 nm` and `OO_CUTOFF = 0.35 nm` in scorer.py are magic numbers without literature references. These are physical constants that affect scoring accuracy.
- Files: `quickice/ranking/scorer.py:22-23`
- Impact: Scoring is heuristic (not a real energy calculation), so the impact is limited to ranking quality, not scientific accuracy.
- Recommendations: Add citations. 0.276 nm is the typical O-O distance in ice Ih (Bernal-Fowler rules). 0.35 nm is a standard cutoff for first hydration shell.

### SCI-04: Ion VDW Radii From Madrid2019 Without Version Tracking
- Issue: Ion parameters (NA_VDW_RADIUS=0.190 nm, CL_VDW_RADIUS=0.181 nm) and charges (NA_CHARGE=0.85, CL_CHARGE=-0.85) are hardcoded from "Madrid2019" force field but without specifying which version (e.g., Madrid2019_085 vs Madrid2019_1).
- Files: `quickice/structure_generation/gromacs_ion_export.py:9-27`, `quickice/structure_generation/ion_inserter.py:25-36`
- Impact: Different Madrid2019 versions have different ion charges and VDW parameters. Using wrong parameters could affect MD simulation accuracy.
- Recommendations: Document the specific Madrid2019 version in the ITP file header and in code comments. Consider making the ion model selectable.

---

## Exception Handling Issues

### EXC-01: IAPWS Failures Logged at Wrong Level in phase_diagram_widget.py
- Issue: IAPWS saturation curve failures in the phase diagram widget are logged at `logger.warning()` level (FIXED from earlier `logger.debug()` — see verification in `.planning/code_analysis/20260516_exception_handling_review.md`). However, if IAPWS consistently fails, the diagram may be incomplete with no visual indication to the user.
- Files: `quickice/gui/phase_diagram_widget.py:81-82`, `quickice/gui/phase_diagram_widget.py:483-484`
- Impact: Missing boundary lines in phase diagram, but application continues
- Recommendations: Add visual indication (dashed line or label) where IAPWS calculations failed.

### EXC-02: Silent FileNotFoundError for Guest ITP Files During Export
- Issue: When exporting ion or interface structures with guests, if the guest .itp file is not found, the export continues silently with `pass`. This means the user gets a .top file that references a non-existent .itp file, which will cause GROMACS to fail.
- Files: `quickice/gui/export.py:331-335`, `quickice/gui/export.py:873-879`
- Impact: User gets an incomplete export that fails in GROMACS with no indication why
- Recommendations: Show a QMessageBox warning when a guest .itp file is not found, instead of silently continuing.

### EXC-03: Three Export Handlers Missing traceback.print_exc()
- Issue: `IonGROMACSExporter.export_ion_gromacs()`, `GROMACSExporter.export_gromacs()`, and `InterfaceGROMACSExporter.export_interface_gromacs()` show error dialogs but don't print tracebacks, unlike `SoluteGROMACSExporter` and `CustomMoleculeGROMACSExporter` which do.
- Files: `quickice/gui/export.py:370-374`, `quickice/gui/export.py:725-729`, `quickice/gui/export.py:882-886`
- Impact: Makes debugging export failures harder
- Recommendations: Add `import traceback; traceback.print_exc()` to all three handlers for consistency with other exporters.

---

## PyInstaller Bundle Size Concerns

### BUNDLE-01: `collect_all()` For 9 Packages With No Excludes
- Issue: The PyInstaller spec file uses `collect_all()` for `iapws`, `genice2`, `genice_core`, `matplotlib`, `scipy`, `numpy`, `shapely`, `networkx`, `spglib`. This collects ALL files (data, binaries, hidden imports) from each package with no filtering. The `excludes=[]` list is empty.
- Files: `quickice-gui.spec:9-16`
- Impact: Bundle includes unnecessary test files, documentation, and development artifacts from each package. Estimated wasted space: 50-200 MB.
- Recommendations: Add explicit excludes for test directories (`*/tests/*`, `*/test/*`), documentation (`*/docs/*`), and development artifacts. Consider using `collect_submodules()` + `collect_data_files()` with targeted patterns instead of `collect_all()`.

### BUNDLE-02: GenIce2 Includes All Lattice/Molecule/Format Plugins
- Issue: GenIce2's plugin system means `collect_all('genice2')` includes all lattice types, molecule types, and format plugins — many of which QuickIce never uses.
- Files: `quickice-gui.spec:9`
- Impact: Unnecessary lattice modules (ice phases QuickIce doesn't support) and format modules (PDB, CIF, etc.) are bundled.
- Recommendations: Collect only the specific GenIce2 submodules that QuickIce uses: `genice2.genice`, `genice2.plugin`, and the specific lattice/molecule/format modules listed in `generator.py`.

---

## Test Coverage Gaps

### TEST-01: GROMACS Export End-to-End Testing
- What's not tested: Complete GRO+TOP+ITP export for ion structures with solutes AND custom molecules present (the full interface→custom→solute→ion chain). Tests exist for individual tabs but not the full chain.
- Files: `quickice/output/gromacs_writer.py` (2054 lines), `quickice/gui/export.py` (886 lines)
- Risk: Changes to attribute passing between tabs could silently break export
- Priority: High

### TEST-02: Pocket Mode Edge Cases
- What's not tested: Pocket mode with very thin cavities, large boxes with small pockets, non-spherical cavities
- Files: `quickice/structure_generation/modes/pocket.py`
- Risk: Pocket mode could produce incorrect structures for unusual parameters
- Priority: Medium

### TEST-03: Triclinic Cell Interface Generation
- What's not tested: Interface generation for triclinic ice phases (Ice II, Ice V). The code has a `TriclinicCellError` check that blocks these phases, but the test is minimal.
- Files: `quickice/structure_generation/modes/slab.py`, `quickice/structure_generation/modes/pocket.py`, `quickice/structure_generation/modes/piece.py`
- Risk: Triclinic cell handling may be broken when this feature is enabled
- Priority: Medium (currently blocked by design)

### TEST-04: Custom Molecule ITP Parsing Edge Cases
- What's not tested: ITP files with non-standard formatting (missing comment lines, extra whitespace, BOM markers, Windows line endings, non-ASCII residue names)
- Files: `quickice/structure_generation/itp_parser.py`
- Risk: User-uploaded ITP files may fail to parse with unclear errors
- Priority: Medium

### TEST-05: Atom Count Consistency After Multiple Overlap Removal Steps
- What's not tested: Scenarios where both ice-water overlap AND guest-water overlap removal occur in slab mode (the `# GUEST-WATER OVERLAP FIX` section in slab.py:532-554)
- Files: `quickice/structure_generation/modes/slab.py:532-554`
- Risk: Invariant `water_atom_count == water_nmolecules * 4` could break after two rounds of overlap removal
- Priority: High

---

## Previously Identified Issues — Current Status

### FIXED: CRIT-01 (Atom Count Mismatch in Interface GRO Export)
- Original issue: `n_atoms = (iface.ice_nmolecules + iface.water_nmolecules) * 4` was incorrect because ice molecules have 3 atoms internally
- Current status: **FIXED** in `quickice/output/gromacs_writer.py:642-645`. Now correctly computes: `ice_output_atoms = iface.ice_nmolecules * 4` (after MW addition), `water_output_atoms = iface.water_nmolecules * 4`, `guest_output_atoms = iface.guest_atom_count`. Total is correct.

### FIXED: CRIT-02 (Index Overflow in Water Atom Access)
- Original issue: Water molecule iteration used `iface.ice_atom_count` incorrectly
- Current status: **FIXED** in `quickice/output/gromacs_writer.py:737-738`. Water now uses `water_start + mol_idx * 4` with `water_start = ice_end`.

### FIXED: CRIT-03 (Inconsistent Atom Name Handling Between Ice and Water)
- Original issue: VTK atom name handling was inconsistent
- Current status: **FIXED** in `quickice/gui/vtk_utils.py`. The code now properly checks `i < iface.ice_atom_count` to distinguish ice from water atoms.

### FIXED: Exception Safety in Generator Random State
- Original issue: `np.random.set_state()` was not guaranteed on exception
- Current status: **FIXED** in `quickice/structure_generation/generator.py:101-157`. Now uses `try/finally` pattern ensuring state restoration even on exception.

### FIXED: Bare except in IAPWS Phase Diagram Widget
- Original issue: `except:` bare except blocks were used in phase diagram
- Current status: **FIXED** in `quickice/gui/phase_diagram_widget.py:81-82, 483-484`. Now uses `except Exception as e:` with `logger.warning()`.

### FIXED: Silent None Return in gro_parser.py
- Original issue: `extract_residue_name_from_gro()` returned None silently without logging
- Current status: **FIXED** in `quickice/structure_generation/gro_parser.py:147-148`. Now logs `logger.warning()`.

### PARTIALLY FIXED: IAPWS Warning Level in phase_diagram_widget
- Original issue: Failures logged at debug level, invisible in normal operation
- Current status: **PARTIALLY FIXED** — changed to `logger.warning()` level, but no visual indication in the GUI when IAPWS fails.

### NOT FIXED: Degenerate Diversity Score
- Original issue: diversity_score always returns 1.0 since all seeds are unique
- Current status: **NOT FIXED**. Code unchanged from original report.

### NOT FIXED: 27× Memory Overhead in Scorer Supercell
- Original issue: 3×3×3 supercell creates 27× memory overhead for O-O distance calculation
- Current status: **NOT FIXED**. Still using explicit supercell approach.

### NOT FIXED: Debug Print Statements (LOW-04 from earlier report)
- Original issue: Debug print statements left in production code
- Current status: **NOT VERIFIED** — need to check if removed.

---

*Concerns audit: 2026-05-22*
