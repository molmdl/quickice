# Codebase Concerns

**Analysis Date:** 2026-06-08

## Tech Debt

### FRAG-03: GROMACS Writer Monolith (2693 lines, 28 functions)
- Issue: `gromacs_writer.py` is a 2693-line file containing 28 write/parse functions covering all export paths (candidate, interface, ion, custom molecule, solute, multi-molecule). This is the largest file in the codebase and the hardest to modify safely. The file has grown 134 lines since the previous analysis.
- Files: `quickice/output/gromacs_writer.py`
- Impact: Any export change requires understanding the entire file; merge conflicts are likely in team development; the `detect_guest_type_from_atoms()` function at line 886 uses heuristic atom pattern matching that could fail for unusual molecule types
- Fix approach: Split into per-structure-type modules: `gromacs_writer_ice.py`, `gromacs_writer_interface.py`, `gromacs_writer_ion.py`, `gromacs_writer_custom.py`, `gromacs_writer_solute.py`. Shared utilities (`wrap_positions_into_box`, `wrap_molecules_into_box`, `compute_mw_position`, `parse_itp_atomtypes`, `comment_out_atomtypes_in_itp`) go into `gromacs_writer_utils.py`.

### TD-01: Duplicate Mode Functions Across slab.py, pocket.py, piece.py
- Issue: Three functions (`detect_atoms_per_molecule`, `_detect_guest_atoms`, `_count_guest_molecules`) are copy-pasted across all three mode files with near-identical implementations (~150 lines of duplication). Additionally, `ICE_ATOM_NAMES_TEMPLATE = ["O", "H", "H"]` is defined in both `slab.py` and `pocket.py` but never used (dead code — atom names are built dynamically).
- Files: `quickice/structure_generation/modes/slab.py:24-122`, `quickice/structure_generation/modes/pocket.py:24-101`, `quickice/structure_generation/modes/piece.py:31-134`
- Impact: Maintenance burden (changes must be made 3×); `pocket.py`'s `_detect_guest_atoms` is slightly simplified compared to `slab.py`/`piece.py`, but all three now include the OW-safeguard check; dead `ICE_ATOM_NAMES_TEMPLATE` constant in slab.py and pocket.py
- Fix approach: Move `detect_atoms_per_molecule`, `_detect_guest_atoms`, and `_count_guest_molecules` to `quickice/utils/molecule_utils.py` (alongside the already-consolidated `count_guest_atoms`). Remove unused `ICE_ATOM_NAMES_TEMPLATE` from slab.py and pocket.py.

### TD-08: Synthetic Anonymous Objects in GROMACS Writer (7 instances)
- Issue: `write_ion_gro_file()` and `write_solute_gro_file()` create pseudo-MoleculeIndex objects using `type('obj', (object,), {'start_idx': start, 'count': count, 'mol_type': 'custom'})()` instead of actual `MoleculeIndex` dataclass instances. This bypasses type checking, lacks IDE support, and produces confusing stack traces.
- Files: `quickice/output/gromacs_writer.py:1339-1343`, `quickice/output/gromacs_writer.py:1350-1354`, `quickice/output/gromacs_writer.py:2215-2219`, `quickice/output/gromacs_writer.py:2222-2226`, `quickice/output/gromacs_writer.py:2240-2243`, `quickice/output/gromacs_writer.py:2256-2260`, `quickice/output/gromacs_writer.py:2266-2270`
- Impact: No compile-time safety; attribute access can silently fail; 7 ad-hoc objects scattered across 2 functions; confusing for developers unfamiliar with the pattern
- Fix approach: Import `MoleculeIndex` from `quickice.structure_generation.types` and use `MoleculeIndex(start_idx=start, count=count, mol_type=mol_type)` instead. The dataclass is already imported in the types module.

> **DEFLT-01 (fudgeLJ inconsistency) was fixed in Phase 34.7-01.** The TD-09 entry has been removed from this section. All 6 TOP writers now use `fudgeLJ=0.5, fudgeQQ=0.8333`. See "Previously Fixed Issues" table below.

### TD-10: Module-Level Global `_registry` in gromacs_writer.py
- Issue: Line 38 creates a module-level `MoleculetypeRegistry()` as `_registry`, used as the default registry in `write_multi_molecule_top_file()`. This global instance can accumulate state across multiple exports in the same Python session, potentially causing moleculetype name collisions.
- Files: `quickice/output/gromacs_writer.py:37-38`
- Impact: In GUI usage, if a user exports multiple structures in the same session without restarting, the registry accumulates registrations. The `MoleculetypeRegistry.clear()` method exists but is only called in tests.
- Fix approach: Remove the module-level `_registry`. Require callers to pass a `MoleculetypeRegistry` instance, or create a fresh registry at the start of each export function. Add `registry.clear()` call at the start of each export workflow in `quickice/gui/export.py`.

### TD-11: Atomtype Deduplication Logic Duplicated Across 4+ TOP Writers
- Issue: The atomtype deduplication pattern (`_written_atomtypes` set, check `atomtype[0] not in _written_atomtypes`, add after writing) is copy-pasted across `write_ion_top_file()`, `write_custom_molecule_top_file()`, and `write_solute_top_file()` with identical logic (~10 lines each).
- Files: `quickice/output/gromacs_writer.py:1746-1762`, `quickice/output/gromacs_writer.py:2124-2137`, `quickice/output/gromacs_writer.py:2621-2636`
- Impact: Maintenance burden; inconsistency risk if one copy is updated but not others
- Fix approach: Extract a helper function `write_deduplicated_atomtypes(f, atomtypes, written_set)` that handles the dedup logic. Place in `gromacs_writer_utils.py` after the planned split.

### TD-12: `count_guest_atoms()` Has Ambiguous Branching Logic — **PARTIALLY FIXED**
- Issue: `count_guest_atoms()` in `molecule_utils.py` uses heuristic pattern matching to identify molecule types from atom names. The function has ambiguous branches: "C" could be CH4 (5 atoms), CO2 (3 atoms), or the start of THF (13 atoms). The H2 vs CH4 disambiguation depends on counting C and H atoms in a 15-atom sample window, which can fail if molecules are at boundaries.
- Files: `quickice/utils/molecule_utils.py:16-107`
- Impact: Misidentification of guest molecules causes incorrect atom counts, which cascades to wrong molecule_index entries, wrong GRO file headers, and topology mismatches. The "HYDRATE FIX" comments throughout the mode files (slab.py, pocket.py, piece.py) are workarounds for this fragility.
- Fix approach: Add explicit molecule type parameter to `count_guest_atoms()` instead of relying solely on heuristic detection. The caller (mode functions) already know the guest type from the configuration.
- **Status: PARTIALLY FIXED — `guest_type` parameter added (commit 6d04262), allowing callers to bypass heuristic. Dead CO2 handler also removed. However, heuristic fallback still fragile for unknown molecules.**

### TD-07: ITP Atomtypes Section Handling — No Upload-Time Warning
- Issue: User-provided ITP files may contain `[ atomtypes ]` sections that conflict with the main `.top` file's `[ atomtypes ]`. QuickIce works around this by running `comment_out_atomtypes_in_itp()` at export time, which silently modifies the ITP content before writing. Users are not warned at upload time that their atomtypes will be commented out.
- Files: `quickice/output/gromacs_writer.py:310-354`, `quickice/gui/export.py` (3 locations)
- Impact: User confusion about why their ITP file content differs after export; silent modification of user data without notification
- Fix approach: In `quickice/gui/custom_molecule_panel.py`, detect `[ atomtypes ]` at upload time and show a QMessageBox warning that it will be commented out at export. Alternatively, extract atomtypes into a separate file during upload.

### TD-05: Global Random State Pollution in GenIce (Not Thread-Safe)
- Issue: `IceStructureGenerator._generate_single()` saves/restores `np.random` global state around GenIce calls using `try/finally`. The fundamental approach of manipulating global state via `np.random.seed()` is NOT thread-safe. GenIce2 internally uses the legacy `np.random` global state (not the newer Generator API).
- Files: `quickice/structure_generation/generator.py:101-157`
- Impact: If generation is ever made concurrent, random state corruption would produce irreproducible results. Current `try/finally` pattern is adequate for single-threaded use.
- Fix approach: Blocked on GenIce2 supporting numpy's Generator API. No immediate fix needed — the code correctly documents that it is NOT thread-safe (docstring lines 96-99). If concurrency is needed, use `threading.Lock` around `_generate_single()`.

### VTK-DUP: VTK Availability Detection Duplicated 6×
- Issue: The VTK availability check (`_VTK_AVAILABLE`, `DISPLAY`/`localhost` detection, `QUICKICE_FORCE_VTK` override) is copy-pasted across 6 viewer files with identical logic (~20 lines each, ~120 lines total).
- Files: `quickice/gui/view.py:24-33`, `quickice/gui/hydrate_viewer.py:20-39`, `quickice/gui/ion_viewer.py:20-40`, `quickice/gui/custom_molecule_viewer.py:20-39`, `quickice/gui/solute_viewer.py:19-38`, `quickice/gui/interface_panel.py:33-42`
- Impact: Maintenance burden; if the detection logic needs updating, 6 files must be changed; slight variations could introduce inconsistencies
- Fix approach: Extract to `quickice/gui/vtk_utils.py` as a single `_VTK_AVAILABLE` check and `is_vtk_available()` function. All 6 files would import from one location.

---

## Known Bugs

> **BUG-05 (HW1 Z-coordinate) was fixed in Phase 34.7-01 (commit 6965961).** The entry has been removed from this section. See "Previously Fixed Issues" table below.

### BUG-04: Degenerate Diversity Score — Always Returns 1.0
- Symptoms: `diversity_score()` in `scorer.py` computes `1.0 / same_seed_count` where `same_seed_count` is always 1 (since `generate_all()` uses sequential unique seeds 0, 1, 2, ...). This means `diversity_score = 1.0` for all candidates, providing zero discriminatory value in ranking.
- Files: `quickice/ranking/scorer.py:196-234`, `quickice/ranking/types.py:41`
- Trigger: Always occurs — the diversity score is functionally useless as implemented
- Workaround: The score still participates in ranking via `normalize_scores()` which returns all-zeros when all values are equal, so it effectively contributes nothing. The ranking degrades to energy+density only.
- Fix approach: Replace seed-based diversity with structural fingerprint diversity (radial distribution functions, bond angle distributions, or RMSD between candidate structures). This is a significant feature addition, not a simple fix.

---

## Security Considerations

### SEC-01: Path Traversal Risk in CLI Output Path — **FIXED**
- ~~Risk: `quickice/main.py` uses `Path(args.output)` directly without sanitization. If `phase_info['phase_id']` contains path traversal characters (e.g., `../../etc`), generated filenames could write outside the intended directory.~~
- **Fixed — `Path.resolve()` used (fix batch 5, commit 22bd382).**
- Files: `quickice/main.py:127-158`

---

## Performance Bottlenecks

### PERF-02: 27× Memory Overhead in Scorer O-O Distance Calculation
- Problem: `_calculate_oo_distances_pbc()` builds a 3×3×3 supercell (27 copies) for PBC-aware O-O distance calculation. For 100,000 oxygen atoms, this allocates ~650 MB. The scorer already uses `cKDTree` but doesn't use its `boxsize=` parameter.
- Files: `quickice/ranking/scorer.py:53-64`
- Cause: Using explicit supercell replication instead of `cKDTree(boxsize=)` parameter. The `boxsize=` parameter only works for orthorhombic cells, but the `overlap_resolver.py` module successfully uses `cKDTree(boxsize=box_list)` for the same purpose (see `overlap_resolver.py:72`).
- Improvement path: Use `cKDTree(o_positions, boxsize=cell_dims.tolist())` for orthorhombic phases (ice Ih, III, VI, VII, VIII, IX). Fall back to supercell approach only for triclinic phases (ice II, V). This would reduce memory from 27× to 1× for most phases.

### PERF-01: O(n²) H-Bond Detection in vtk_utils.py — **FIXED**
- ~~Problem: `detect_hydrogen_bonds()` uses a nested loop over H atoms × O atoms. For n molecules, complexity is O(n²). At 10,000 molecules this takes 2-5 seconds.~~
- **Fixed by Quick Task 022 (KDTree H-bond detection).** Complexity is now O(n log n).
- Files: `quickice/gui/vtk_utils.py:272-290`
- Cause: Simple pairwise distance check with PBC support, no spatial indexing
- Improvement path: Replace with KDTree approach (pattern proven in `quickice/ranking/scorer.py:21-80` and `quickice/structure_generation/overlap_resolver.py:14-85`). Estimated speedup: 5-100× for large structures.

### PERF-03: Pocket Mode Water Filling — Bounding Box Overfill
- Problem: Pocket mode fills the bounding box of the cavity (`fill_dims = np.array([2 * radius, 2 * radius, 2 * radius])`), then removes water outside the cavity shape. For spherical pockets, the bounding box is ~48% larger than the actual sphere volume.
- Files: `quickice/structure_generation/modes/pocket.py:271-282`
- Cause: `fill_region_with_water()` only supports rectangular regions, not spherical ones
- Improvement path: Low priority — the optimization already reduces waste from O(box³) to O(pocket³). For typical pocket sizes (1-5 nm diameter), the overhead is modest.

### PERF-04: Nested Loops in Guest Molecule Detection
- Problem: `_detect_guest_atoms()` in slab.py, pocket.py, and piece.py iterates through the atom list with a while loop, calling `count_guest_atoms()` for each guest candidate. Inside `count_guest_atoms()`, there's another loop scanning 15 atoms ahead. For structures with many guest molecules (e.g., hydrate sII with 24 guest molecules per unit cell), this creates nested iteration. Additionally, the OW-safeguard check adds a scan through detected atoms.
- Files: `quickice/structure_generation/modes/slab.py:44-110`, `quickice/structure_generation/modes/pocket.py:44-85`, `quickice/utils/molecule_utils.py:16-107`
- Cause: Sequential atom-by-atom scanning with no batch processing or caching
- Improvement path: Pre-classify atoms by residue name (when available from GenIce2) to avoid the while-loop + heuristic pattern. For hydrate structures, residue names are already available from `_parse_gro_result()` and should be propagated to mode functions.

---

## Fragile Areas

### FRAG-01: Cross-Tab Data Flow (Interface → Custom → Solute → Ion)
- Files: `quickice/gui/main_window.py:1170-1279`, `quickice/gui/solute_panel.py`, `quickice/gui/ion_panel.py`, `quickice/gui/custom_molecule_panel.py`
- Why fragile: Data flows through 4+ tabs with manual attribute passing via `getattr(structure, 'attr', default)`. Each tab passes its result to downstream tabs by calling `set_custom_molecule_structure()`, `set_liquid_volume()`, etc. The ion inserter must preserve ALL upstream attributes (solute_type, solute_positions, custom_molecule_count, custom_gro_path, etc.) through `getattr` chains. If any attribute name changes or any tab is skipped, downstream tabs silently get defaults.
- Safe modification: Always test the full chain (interface → custom → solute → ion) after any changes to structure dataclass fields. Add assertions in each tab's `set_*()` method to verify required attributes exist.
- Test coverage: `tests/test_solute_ion_molecule_index.py`, `tests/test_integration_v35.py` cover parts of this chain, but full end-to-end testing is limited.

### FRAG-02: Atom Count Invariants Across Interface Generation — **FIXED**
- ~~Files: `quickice/structure_generation/modes/slab.py`, `quickice/structure_generation/modes/pocket.py`, `quickice/structure_generation/modes/piece.py`, `quickice/output/gromacs_writer.py:606-812`~~
- ~~Why fragile: The critical invariants `ice_atom_count == ice_nmolecules * atoms_per_ice_mol` and `water_atom_count == water_nmolecules * 4` must hold after overlap removal. If overlap removal removes partial molecules (it shouldn't, but the code is complex), these invariants break, causing incorrect GRO file headers and wrong atom indexing in exports. Current code has `assert` statements after overlap removal steps (e.g., `slab.py:561-563`), but these are only checked in debug mode (Python `-O` disables assertions).~~
- **Fixed — Assertions added after overlap removal in pocket-edge-tests phase. Invariant tests in `tests/test_overlap_removal_invariants.py`.**
- ~~Safe modification: Convert critical `assert` statements to explicit `if`/`raise` checks that always run. Add invariant validation at the end of each `assemble_*()` function.~~
- ~~Test coverage: `tests/test_atom_ordering_validation.py`, `tests/test_interface_ordering_validation.py` partially cover this.~~

### FRAG-03: GROMACS Writer Monolith — See Tech Debt Section
- (See FRAG-03 in Tech Debt section above — same issue, listed in both categories)

### FRAG-04: ITP File Residue Name Matching
- Files: `quickice/structure_generation/itp_parser.py:34-138`, `quickice/structure_generation/gro_parser.py`, `quickice/structure_generation/molecule_validator.py:43-194`
- Why fragile: ITP parser uses regex to extract moleculetype name, which can fail for non-standard formatting. GRO residue name extraction relies on fixed-width column parsing that assumes well-formed files. The `validate_custom_molecule()` function compares GRO residue name to ITP moleculetype name, but GRO files often use generic names like "MOL" or "UNK". The validator has a whitelist of generic names to skip mismatches, but this is fragile — any new generic name would cause false warnings.
- Safe modification: Make the generic names list configurable. Add validation for ITP regex patterns against known GenIce2 output formats.
- Test coverage: `tests/test_moleculetype_registry.py`, but ITP parsing edge cases are undertested.

### FRAG-05: main_window.py — 2024 Lines With Mixed Responsibilities
- Files: `quickice/gui/main_window.py`
- Why fragile: MainWindow handles generation triggers, tab coordination, all 7+ export paths, progress reporting, and VTK rendering coordination. It has 12 `logger.warning`/`logger.error` calls and multiple `try`/`except` blocks with bare `pass`.
- Safe modification: Extract export orchestration into a dedicated `quickice/gui/export_coordinator.py`. Move tab coordination logic into the ViewModel (`quickice/gui/viewmodel.py`).
- Test coverage: Limited — GUI code is difficult to unit test. Integration tests in `tests/test_integration_v35.py` partially cover this.

### FRAG-06: 3→4 Atom Expansion Requires Consistent Ice vs Hydrate Detection
- Files: `quickice/output/gromacs_writer.py:606-734`, `quickice/structure_generation/modes/slab.py:24-42`, `quickice/structure_generation/modes/pocket.py:24-42`
- Why fragile: Ice structures generated by GenIce use 3 atoms per molecule (O, H, H). Hydrate structures use 4 atoms per molecule (OW, HW1, HW2, MW). The GRO writer must detect which format the input uses to correctly expand 3→4 (adding MW virtual site) or pass through 4 atoms unchanged. Detection relies on checking `atom_names[0] == "OW"` at the start of the ice region. If atom_names ordering changes or if mixed ice types appear in the same structure, this detection fails.
- Safe modification: Add an explicit `atoms_per_ice_mol` attribute to `InterfaceStructure` and `Candidate` dataclasses instead of relying on runtime detection. Validate detection result matches expected molecule count.
- Test coverage: `tests/test_atom_ordering_validation.py` covers some cases; hydrate→interface conversion is partially tested.

### FRAG-07: Moleculetype Name Mismatches in GROMACS Export
- Files: `quickice/output/gromacs_writer.py:1669-1684`, `quickice/output/gromacs_writer.py:2079-2087`, `quickice/output/gromacs_writer.py:2553-2566`
- Why fragile: The `[ molecules ]` section in TOP files must use a moleculetype name that exactly matches the `[ moleculetype ]` name in the corresponding .itp file. The code parses this from the user's ITP file at export time using `parse_itp_file()`. If parsing fails (regex mismatch, non-standard formatting), it falls back to `custom_molecule_moleculetype` or "CUSTOM". A mismatch between the TOP `[ molecules ]` name and the ITP `[ moleculetype ]` name causes GROMACS to fail with "Mismatch in moleculetype names" error.
- Safe modification: Add a post-export validation step that reads the generated TOP file and verifies all `[ molecules ]` names match their corresponding .itp files. Add to e2e test suite.
- Test coverage: `tests/test_moleculetype_registry.py` tests the registry but not the end-to-end name matching.

---

## Exception Handling Issues

### EXC-01: IAPWS Failures Not Visually Indicated in GUI
- Issue: `water_density_gcm3()` falls back to 0.9998 g/cm³ when IAPWS calculation fails, logging at `logger.warning` level. Similarly, `ice_ih_density_gcm3()` falls back to 0.9167 g/cm³. Neither fallback is shown to the user in the GUI — the generation silently proceeds with approximate density values.
- Files: `quickice/phase_mapping/water_density.py:70-93`, `quickice/phase_mapping/ice_ih_density.py:63-75`
- Impact: User may not realize the water layer density in interface structures is approximate (~0.3% error for water fallback, varies for ice Ih). For most conditions this is negligible, but for extreme T/P conditions the error could be larger.
- Fix approach: Emit a Qt signal from the generation worker when fallback density is used. Display a yellow warning badge in the status bar. At minimum, add a note in the generation report.

### EXC-03: Three Export Handlers Missing traceback.print_exc() — **FIXED**
- ~~Issue: `IonGROMACSExporter.export_ion_gromacs()`, `GROMACSExporter.export_gromacs()`, and `InterfaceGROMACSExporter.export_interface_gromacs()` show error dialogs but don't print tracebacks, unlike `SoluteGROMACSExporter` and `CustomMoleculeGROMACSExporter` which do include `traceback.print_exc()`.~~
- **Fixed — Now shows `QMessageBox.warning` (fix batch 1) and `traceback.print_exc()` in all 5 handlers (Quick Task 027, commit 719de7f).**
- Files: `quickice/gui/export.py:370-374`, `quickice/gui/export.py:725-729`, `quickice/gui/export.py:882-886`

---

## PyInstaller Bundle Issues

### BUNDLE-01: PyInstaller Spec Excludes Tests — **FIXED**
- ~~Issue: The `excludes` list in `quickice-gui.spec:27` now contains `['*/tests/*', '*/test/*', '*/docs/*', '*/__pycache__/*', '*/.pytest_cache/*', '*/egg-info/*']`.~~
- **Fixed — excludes list populated in fix batch 5, commit 22bd382.**
- Files: `quickice-gui.spec:27`

### BUNDLE-02: GenIce2 Includes All Lattice/Molecule/Format Plugins
- Issue: GenIce2's plugin system means `collect_all('genice2')` includes ALL lattice types, molecule types, and format plugins — many of which QuickIce never uses. QuickIce only uses: `genice2.genice.GenIce`, `genice2.plugin.safe_import`, lattices for supported ice phases (1h, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, sI, sII, sH), the `tip3p` molecule, the `tip4p` molecule, and the `gromacs` format.
- Files: `quickice-gui.spec:9`
- Impact: Unnecessary lattice modules (obscure ice phases, non-ice crystal structures), molecule types (many water models QuickIce doesn't use), and format modules (PDB, CIF, etc.) are bundled. Estimated wasted space: 20-50 MB.
- Fix approach: Replace `collect_all('genice2')` with targeted `collect_submodules()` + `collect_data_files()` specifying only the submodules QuickIce uses.

### BUNDLE-03: UPX Compression Broke Executable (REVERTED)
- Issue: An attempt to optimize PyInstaller bundle size by enabling UPX compression (`upx=True` in `quickice-gui.spec:42,56`) broke the executable. The UPX-compressed binary failed to launch on some platforms due to incompatibility with certain Python shared libraries (particularly VTK and numpy's compiled extensions). The change was reverted.
- Files: `quickice-gui.spec:42,56`
- Impact: Bundle size is larger than optimal (~500 MB vs ~300 MB potential). UPX is still set to `True` in the current spec file, which may cause issues on some platforms.
- Workaround: Set `upx=False` in the spec file if bundle fails to launch. Test on all target platforms after building.
- Fix approach: Test with `upx=True` on all target platforms; if it fails, set `upx=False` and add `upx_exclude=[]` for problematic binaries. Consider using `upx_exclude` to list numpy, VTK, and scipy compiled extensions.

---

## Test Coverage Gaps

### TEST-01: GROMACS Export End-to-End Testing (Full Chain) — **FIXED**
- ~~What's not tested: Complete GRO+TOP+ITP export for ion structures with solutes AND custom molecules present (the full interface→custom→solute→ion chain). Tests exist for individual tabs but not the full chain.~~
- **Fixed — e2e-export-test + e2e-compute-export phases, 17+ test files with 258+ tests.**

### TEST-02: Pocket Mode Edge Cases — **FIXED**
- ~~What's not tested: Pocket mode with very thin cavities, large boxes with small pockets, non-spherical (cubic) cavities~~
- **Fixed — pocket-edge-tests phase, 51 tests.**

### TEST-03: Triclinic Cell Interface Generation
- What's not tested: Interface generation for triclinic ice phases (Ice II, Ice V). The code currently blocks these phases, but if support is added, there are no tests to validate it.
- Files: `quickice/structure_generation/modes/slab.py`, `quickice/structure_generation/modes/pocket.py`, `quickice/structure_generation/modes/piece.py`
- Risk: Triclinic cell handling may be broken when this feature is enabled
- Priority: Medium (currently blocked by design)

### TEST-05: Atom Count Consistency After Multiple Overlap Removal Steps — **FIXED**
- ~~What's not tested: Scenarios where both ice-water overlap AND guest-water overlap removal occur in slab mode (the `# GUEST-WATER OVERLAP FIX` section in `slab.py:532-564`).~~
- **Fixed — `tests/test_overlap_removal_invariants.py` (fix batch 6A, commit 687fdad).**

### TEST-07: Custom Molecule GRO Writer HW1 Z-Coordinate — **FIXED**
- ~~What's not tested: The custom molecule GRO writer's water molecule output (specifically the HW1 line). BUG-05 above shows `h2_pos[2]` is used instead of `h1_pos[2]` at line 1971.~~
- **Fixed — Phase 34.7-01 regression tests (commit 6965961).** BUG-05 itself also fixed in same commit.

### TEST-08: `[ defaults ]` Consistency Across Export Paths — **FIXED**
- ~~What's not tested: Verification that all TOP file writers produce consistent `[ defaults ]` sections. Currently, some writers use `fudgeLJ=0.5` and others use `fudgeLJ=0.0`.~~
- **Fixed — Phase 34.7 DEFLT-01 regression tests (commit 6965961).** All writers now use `fudgeLJ=0.5, fudgeQQ=0.8333`.

### TEST-09: Moleculetype Name Matching in TOP vs ITP Files
- What's not tested: Post-export verification that `[ molecules ]` names in TOP files match `[ moleculetype ]` names in corresponding ITP files. A mismatch causes GROMACS fatal errors.
- Files: `quickice/output/gromacs_writer.py`, `quickice/data/*.itp`
- Risk: Custom molecule exports may produce incompatible TOP/ITP pairs
- Priority: Medium

### TEST-06: VTK Rendering Fallback Path
- What's not tested: When VTK is unavailable (SSH X11 forwarding), the fallback widget path in 6 viewer files. No tests verify the fallback label is displayed.
- Files: `quickice/gui/custom_molecule_viewer.py:225-241`, `quickice/gui/solute_viewer.py`, `quickice/gui/hydrate_viewer.py`, `quickice/gui/view.py:402-415`
- Risk: Fallback path could be broken without detection
- Priority: Low (only affects SSH users)

---

## Scientific Accuracy Concerns

### SCI-01: Ice Ih Density Fallback at Wrong Conditions
- Issue: `ice_ih_density_gcm3()` falls back to 0.9167 g/cm³ (density at 273.15 K, 0.1 MPa) when IAPWS calculation fails. This fallback value is at a specific reference condition, not at the user's actual T/P conditions.
- Files: `quickice/phase_mapping/ice_ih_density.py:33,74-75`
- Impact: Small — Ice Ih isn't stable above 208.566 MPa, so the fallback is only hit for inappropriate conditions
- Recommendations: Return the density at the stability boundary rather than 273.15 K / 0.1 MPa, or show a warning that conditions are outside Ice Ih stability range.

### UNIT-02: IAPWS Water Density Fallback Without GUI Indicator
- Risk: `water_density_gcm3()` falls back to 0.9998 g/cm³ when IAPWS fails. This affects interface structure generation (water layer density scaling in slab.py, pocket.py, piece.py). The fallback is logged at `logger.warning()` level but not shown in the GUI.
- Files: `quickice/phase_mapping/water_density.py:70-92`, `quickice/structure_generation/modes/slab.py:224-229`
- Impact: ~0.3% error for water density (negligible for most simulations), but no user awareness
- Recommendations: Add visual indicator in GUI when fallback is used.

---

## Scaling Limits

### SCALE-01: GRO Format Atom Number Limit (99,999)
- Problem: GROMACS .gro format limits atom and residue numbers to 5 digits. For systems with >99,999 atoms, numbers wrap at 100,000 (standard GROMACS convention). QuickIce handles this with `% 100000` wrapping, but some downstream tools may not handle wrapped numbers correctly.
- Files: `quickice/output/gromacs_writer.py:452-453`, `quickice/output/gromacs_writer.py:648-650`
- Current capacity: Up to ~24,999 water molecules (99,996 atoms) before wrapping occurs
- Limit: GRO format wrapping at 100,000 atoms
- Scaling path: Accept wrapping (GROMACS convention) or offer .pdb export as alternative for large systems

### SCALE-02: GenIce2 Structure Generation Time
- Problem: Each GenIce2 structure generation call takes 3-5 seconds. Generating 10 candidates (default) takes 30-50 seconds. No parallelism because of the global `np.random` state issue (TD-05).
- Files: `quickice/structure_generation/generator.py:175-206`
- Current capacity: ~10 candidates in 30-50 seconds
- Limit: Single-threaded; no candidate parallelism
- Scaling path: Add `threading.Lock` around `_generate_single()` to enable thread-pool parallelism (blocked by GenIce2's np.random usage). Or use process-based parallelism with `multiprocessing`.

---

## Dependencies at Risk

### DEP-01: GenIce2 Uses Legacy numpy.random (Not Generator API)
- Risk: GenIce2 internally uses the legacy `np.random` global state instead of the modern `numpy.random.Generator` API. NumPy has deprecated the legacy interface and may remove it in a future major version.
- Impact: GenIce2 would fail; QuickIce ice/hydrate generation would be broken
- Migration plan: Blocked on GenIce2 upstream update. QuickIce's `try/finally` save/restore pattern in `generator.py:101-157` mitigates the symptom but not the dependency risk.

### DEP-02: iapws Package — Single-Maintainer Scientific Package
- Risk: The `iapws` package (used for IAPWS-95 water density and IAPWS R10-06 ice Ih density calculations) is a niche scientific package with a single maintainer. API breaks or abandonment could affect QuickIce's density calculations.
- Impact: Fallback densities (0.9167 g/cm³ for ice, 0.9998 g/cm³ for water) are already in place, so generation would continue with approximate values
- Migration plan: If `iapws` becomes unavailable, the fallback path in `water_density.py:92-93` and `ice_ih_density.py:74-75` would be hit for all conditions. Consider vendoring the IAPWS formulas used.

---

## Previously Fixed Issues (Reference Only)

The following issues were identified in prior analyses and have been **FIXED**. They are listed here for traceability only — do not treat as active concerns.

| ID | Description | Key File | Fixed How/When |
|----|-------------|----------|----------------|
| FLOW-01/02/03 | Exporter crashes/wrong output | `quickice/output/gromacs_writer.py` | Fix batch 1 |
| BUG-01 | OW safeguard | `quickice/structure_generation/modes/*.py` | Fix batch 1 |
| BUG-02a/b/c | THF formula | `quickice/structure_generation/types.py` | Fix batch 4 |
| BUG-03 | O(n²) residue lookup | `quickice/output/gromacs_writer.py:1102` | Fix batch 3 |
| BUG-05 | HW1 Z-coordinate copy-paste | `quickice/output/gromacs_writer.py:1971` | Phase 34.7-01, commit 6965961 |
| MOL-1–5 | Naming mismatches | Various | Fix batches 1-2 |
| KS-1/2/3 | Keyboard shortcuts | `quickice/gui/main_window.py` | Fix batch 2 |
| FF-1 | GAFF→GAFF2 | `quickice/output/gromacs_writer.py` | Fix batch 2 |
| FRAG-01/02 | Fragile code (assertions added) | `quickice/structure_generation/modes/*.py` | Fix batch 3 / pocket-edge-tests |
| EXC-02 | FileNotFoundError:pass | `quickice/gui/export.py` | Fix batch 1 (QMessageBox.warning) |
| EXC-03 | Missing traceback.print_exc | `quickice/gui/export.py` | Quick Task 027, commit 719de7f |
| EXP-1/2 | Filename patterns | `quickice/output/` | Fix batch 3 |
| VER-1 | Version | `quickice/__init__.py` | Fix batch 3 |
| CIT-GAFF2 | Citations | `quickice/output/gromacs_writer.py` | Fix batch 3 |
| SCI-01 | Ice Ih density fallback | `quickice/phase_mapping/ice_ih_density.py` | Fix batch 4 (warning added) |
| SCI-03 | O-O distance citations | `quickice/ranking/types.py` | Fix batch 4 (Petrenko & Whitworth citation) |
| SCI-04 | Madrid2019 header | `quickice/structure_generation/gromacs_ion_export.py` | Fix batch 4 + e2e-compute-export |
| TD-05/06 | Threading/cache | `quickice/structure_generation/generator.py` | Fix batch 4 (lru_cache + Lock) |
| DEFLT-01 | fudgeLJ inconsistency | `quickice/output/gromacs_writer.py` | Phase 34.7-01, commit 6965961 |
| PERF-01 | O(n²) H-bond detection | `quickice/gui/vtk_utils.py` | Quick Task 022 (KDTree) |
| SEC-01 | Path.resolve | `quickice/main.py` | Fix batch 5, commit 22bd382 |
| BUNDLE-01 | PyInstaller excludes | `quickice-gui.spec` | Fix batch 5, commit 22bd382 |
| TEST-01 | E2E export chain tests | `tests/` | e2e-export-test + e2e-compute-export |
| TEST-02 | Pocket mode edge cases | `tests/` | pocket-edge-tests phase, 51 tests |
| TEST-04 | ITP parsing edge cases | `tests/` | `tests/test_itp_parser_edge_cases.py` (fix batch 6A) |
| TEST-05 | Overlap removal invariants | `tests/` | `tests/test_overlap_removal_invariants.py` (fix batch 6A) |
| TEST-07 | BUG-05 regression tests | `tests/` | Phase 34.7-01 regression tests |
| TEST-08 | DEFLT-01 regression tests | `tests/` | Phase 34.7 regression tests |
| NEW-01/02 | Logger/dead imports | Various | Fix batch 4 |
| FRAG-04a/b | Resilience improvements | Various | Fix batch 4 |
| UNIT-01/03 | Validation/logging | Various | Fix batch 3 / batch 4 |
| MW-01 | MW from wrapped atoms | `quickice/output/gromacs_writer.py` | Phase 34.7-01, commit 6965961 |
| RNG-01 | Unseeded RNG | `quickice/structure_generation/custom_molecule_inserter.py` | Phase 34.7-02, commit ee0f4d5 |
| ATOM-01 | Hardcoded water atom count | Various | Phase 34.7-02, commit 8726698 |
| TREE-01 | KDTree rebuild optimization | `quickice/structure_generation/ion_inserter.py` | Phase 34.7-03, commit f44c22c |
| GUEST-01 | CO2 misidentification / dead code | `quickice/utils/molecule_utils.py` | commit 6d04262 |

---

*Concerns audit: 2026-06-08*
*Resolution status updated: 2026-06-12*
