# Codebase Concerns

**Analysis Date:** 2026-05-22

## Tech Debt

### FRAG-03: GROMACS Writer Monolith (2559 lines, 24 functions)
- Issue: `gromacs_writer.py` is a 2559-line file containing 24 write/parse functions covering all export paths (candidate, interface, ion, custom molecule, solute, multi-molecule). This makes it the largest file in the codebase and the hardest to modify safely.
- Files: `quickice/output/gromacs_writer.py`
- Impact: Any export change requires understanding the entire file; merge conflicts are likely in team development; the `detect_guest_type_from_atoms()` function at line 885 uses heuristic atom pattern matching that could fail for unusual molecule types
- Fix approach: Split into per-structure-type modules: `gromacs_writer_ice.py`, `gromacs_writer_interface.py`, `gromacs_writer_ion.py`, `gromacs_writer_custom.py`, `gromacs_writer_solute.py`. Shared utilities (`wrap_positions_into_box`, `wrap_molecules_into_box`, `compute_mw_position`, `parse_itp_atomtypes`, `comment_out_atomtypes_in_itp`) go into `gromacs_writer_utils.py`.

### TD-01: Duplicate Mode Functions Across slab.py, pocket.py, piece.py
- Issue: Three functions (`detect_atoms_per_molecule`, `_detect_guest_atoms`, `_count_guest_molecules`) are copy-pasted across all three mode files with near-identical implementations (~150 lines of duplication). Additionally, `ICE_ATOM_NAMES_TEMPLATE = ["O", "H", "H"]` is defined in both `slab.py` and `pocket.py` but never used (dead code — atom names are built dynamically at line 330/222 respectively).
- Files: `quickice/structure_generation/modes/slab.py:24-122`, `quickice/structure_generation/modes/pocket.py:24-101`, `quickice/structure_generation/modes/piece.py:31-134`
- Impact: Maintenance burden (changes must be made 3×); `pocket.py`'s `_detect_guest_atoms` is slightly simplified compared to `slab.py`/`piece.py`, but all three now include the OW-safeguard check; dead `ICE_ATOM_NAMES_TEMPLATE` constant in slab.py and pocket.py
- Fix approach: Move `detect_atoms_per_molecule`, `_detect_guest_atoms`, and `_count_guest_molecules` to `quickice/utils/molecule_utils.py` (alongside the already-consolidated `count_guest_atoms`). Remove unused `ICE_ATOM_NAMES_TEMPLATE` from slab.py and pocket.py.

### TD-07: ITP Atomtypes Section Handling — No Upload-Time Warning
- Issue: User-provided ITP files may contain `[ atomtypes ]` sections that conflict with the main `.top` file's `[ atomtypes ]`. QuickIce works around this by running `comment_out_atomtypes_in_itp()` at export time, which silently modifies the ITP content before writing. Users are not warned at upload time that their atomtypes will be commented out.
- Files: `quickice/output/gromacs_writer.py:310-354`, `quickice/gui/export.py` (3 locations)
- Impact: User confusion about why their ITP file content differs after export; silent modification of user data without notification
- Fix approach: In `quickice/gui/custom_molecule_panel.py`, detect `[ atomtypes ]` at upload time and show a QMessageBox warning that it will be commented out at export. Alternatively, extract atomtypes into a separate file during upload.

### TD-05: Global Random State Pollution in GenIce (Not Thread-Safe)
- Issue: `IceStructureGenerator._generate_single()` saves/restores `np.random` global state around GenIce calls using `try/finally`. The fundamental approach of manipulating global state via `np.random.seed()` is NOT thread-safe. GenIce2 internally uses the legacy `np.random` global state (not the newer Generator API).
- Files: `quickice/structure_generation/generator.py:101-157`
- Impact: If generation is ever made concurrent, random state corruption would produce irreproducible results. Current `try/finally` pattern is adequate for single-threaded use.
- Fix approach: Blocked on GenIce2 supporting numpy's Generator API. No immediate fix needed — the code correctly documents that it is NOT thread-safe (docstring line 96-99). If concurrency is needed, use `threading.Lock` around `_generate_single()`.

### VTK-DUP: VTK Availability Detection Duplicated 6×
- Issue: The VTK availability check (`_VTK_AVAILABLE`, `DISPLAY`/`localhost` detection, `QUICKICE_FORCE_VTK` override) is copy-pasted across 6 viewer files with identical logic (~20 lines each, ~120 lines total).
- Files: `quickice/gui/view.py:24-33`, `quickice/gui/hydrate_viewer.py:20-39`, `quickice/gui/ion_viewer.py:20-40`, `quickice/gui/custom_molecule_viewer.py:20-39`, `quickice/gui/solute_viewer.py:19-38`, `quickice/gui/interface_panel.py:33-42`
- Impact: Maintenance burden; if the detection logic needs updating, 6 files must be changed; slight variations could introduce inconsistencies
- Fix approach: Extract to `quickice/gui/vtk_utils.py` as a single `_VTK_AVAILABLE` check and `is_vtk_available()` function. All 6 files would import from one location.

---

## Known Bugs

### BUG-04: Degenerate Diversity Score — Always Returns 1.0
- Symptoms: `diversity_score()` in `scorer.py` computes `1.0 / same_seed_count` where `same_seed_count` is always 1 (since `generate_all()` uses sequential unique seeds 0, 1, 2, ...). This means `diversity_score = 1.0` for all candidates, providing zero discriminatory value in ranking.
- Files: `quickice/ranking/scorer.py:196-234`, `quickice/ranking/types.py:41`
- Trigger: Always occurs — the diversity score is functionally useless as implemented
- Workaround: The score still participates in ranking via `normalize_scores()` which returns all-zeros when all values are equal, so it effectively contributes nothing. The ranking degrades to energy+density only.
- Fix approach: Replace seed-based diversity with structural fingerprint diversity (radial distribution functions, bond angle distributions, or RMSD between candidate structures). This is a significant feature addition, not a simple fix.

---

## Security Considerations

### SEC-01: Path Traversal Risk in CLI Output Path
- Risk: `quickice/main.py` uses `Path(args.output)` directly without sanitization. If `phase_info['phase_id']` contains path traversal characters (e.g., `../../etc`), generated filenames could write outside the intended directory.
- Files: `quickice/main.py:127-158`
- Current mitigation: The CLI orchestrator in `output/orchestrator.py` has path traversal protection, but the main.py path does not.
- Recommendations: Add `Path.resolve()` and validate output is within expected directory. Sanitize `phase_id` before using in filenames.

---

## Performance Bottlenecks

### PERF-02: 27× Memory Overhead in Scorer O-O Distance Calculation
- Problem: `_calculate_oo_distances_pbc()` builds a 3×3×3 supercell (27 copies) for PBC-aware O-O distance calculation. For 100,000 oxygen atoms, this allocates ~650 MB. The scorer already uses `cKDTree` but doesn't use its `boxsize=` parameter.
- Files: `quickice/ranking/scorer.py:53-64`
- Cause: Using explicit supercell replication instead of `cKDTree(boxsize=)` parameter. The `boxsize=` parameter only works for orthorhombic cells, but the `overlap_resolver.py` module successfully uses `cKDTree(boxsize=box_list)` for the same purpose (see `overlap_resolver.py:72`).
- Improvement path: Use `cKDTree(o_positions, boxsize=cell_dims.tolist())` for orthorhombic phases (ice Ih, III, VI, VII, VIII, IX). Fall back to supercell approach only for triclinic phases (ice II, V). This would reduce memory from 27× to 1× for most phases. The `overlap_resolver.py` module already demonstrates this pattern works correctly.

### PERF-01: O(n²) H-Bond Detection in vtk_utils.py
- Problem: `detect_hydrogen_bonds()` uses a nested loop over H atoms × O atoms. For n molecules, complexity is O(n²). At 10,000 molecules this takes 2-5 seconds.
- Files: `quickice/gui/vtk_utils.py:272-290`
- Cause: Simple pairwise distance check with PBC support, no spatial indexing
- Improvement path: Replace with KDTree approach (pattern proven in `quickice/ranking/scorer.py:21-80` and `quickice/structure_generation/overlap_resolver.py:14-85`). Estimated speedup: 5-100× for large structures.

### PERF-03: Pocket Mode Water Filling — Now Optimized But Could Improve Further
- Problem: Pocket mode now fills only the bounding box of the cavity (`fill_dims = np.array([2 * radius, 2 * radius, 2 * radius])`), then removes water outside the cavity shape. This is much better than the original full-box approach, but for spherical pockets, the bounding box is ~48% larger than the actual sphere volume.
- Files: `quickice/structure_generation/modes/pocket.py:271-282`
- Cause: `fill_region_with_water()` only supports rectangular regions, not spherical ones
- Improvement path: Low priority — the optimization already reduces waste from O(box³) to O(pocket³). For typical pocket sizes (1-5 nm diameter), the overhead is modest.

---

## Fragile Areas

### FRAG-01: Cross-Tab Data Flow (Interface → Custom → Solute → Ion)
- Files: `quickice/gui/main_window.py:1170-1279`, `quickice/gui/solute_panel.py`, `quickice/gui/ion_panel.py`, `quickice/gui/custom_molecule_panel.py`
- Why fragile: Data flows through 4+ tabs with manual attribute passing via `getattr(structure, 'attr', default)`. Each tab passes its result to downstream tabs by calling `set_custom_molecule_structure()`, `set_liquid_volume()`, etc. The ion inserter must preserve ALL upstream attributes (solute_type, solute_positions, custom_molecule_count, custom_gro_path, etc.) through `getattr` chains. If any attribute name changes or any tab is skipped, downstream tabs silently get defaults.
- Safe modification: Always test the full chain (interface → custom → solute → ion) after any changes to structure dataclass fields. Add assertions in each tab's `set_*()` method to verify required attributes exist.
- Test coverage: `tests/test_solute_ion_molecule_index.py`, `tests/test_integration_v35.py` cover parts of this chain, but full end-to-end testing is limited.

### FRAG-02: Atom Count Invariants Across Interface Generation
- Files: `quickice/structure_generation/modes/slab.py`, `quickice/structure_generation/modes/pocket.py`, `quickice/structure_generation/modes/piece.py`, `quickice/output/gromacs_writer.py:606-812`
- Why fragile: The critical invariants `ice_atom_count == ice_nmolecules * atoms_per_ice_mol` and `water_atom_count == water_nmolecules * 4` must hold after overlap removal. If overlap removal removes partial molecules (it shouldn't, but the code is complex), these invariants break, causing incorrect GRO file headers and wrong atom indexing in exports. Current code has `assert` statements after overlap removal steps (e.g., `slab.py:377-380`), but these are only checked in debug mode (Python `-O` disables assertions).
- Safe modification: Convert critical `assert` statements to explicit `if`/`raise` checks that always run. Add invariant validation at the end of each `assemble_*()` function.
- Test coverage: `tests/test_atom_ordering_validation.py`, `tests/test_interface_ordering_validation.py` partially cover this.

### FRAG-04: ITP File Residue Name Matching
- Files: `quickice/structure_generation/itp_parser.py:34-138`, `quickice/structure_generation/gro_parser.py:103-149`, `quickice/structure_generation/molecule_validator.py:43-194`
- Why fragile: ITP parser uses regex to extract moleculetype name, which can fail for non-standard formatting. GRO residue name extraction relies on fixed-width column parsing that assumes well-formed files. The `validate_custom_molecule()` function compares GRO residue name to ITP moleculetype name, but GRO files often use generic names like "MOL" or "UNK". The validator has a whitelist of generic names (`GENERIC_RESIDUE_NAMES = {"MOL", "UNK", "LIG", "XXX", "RES", "DRG", "API", "HET", "UNL", "LIG1", "MOL1"}`) to skip mismatches, but this is fragile — any new generic name would cause false warnings.
- Safe modification: Make the generic names list configurable. Add validation for ITP regex patterns against known GenIce2 output formats.
- Test coverage: `tests/test_moleculetype_registry.py`, but ITP parsing edge cases are undertested.

### FRAG-05: main_window.py — 2024 Lines With Mixed Responsibilities
- Files: `quickice/gui/main_window.py`
- Why fragile: MainWindow handles generation triggers, tab coordination, all 7+ export paths, progress reporting, and VTK rendering coordination. It has 12 `logger.warning`/`logger.error` calls and multiple `try`/`except` blocks with bare `pass` (lines 979, 1285).
- Safe modification: Extract export orchestration into a dedicated `quickice/gui/export_coordinator.py`. Move tab coordination logic into the ViewModel (`quickice/gui/viewmodel.py`).
- Test coverage: Limited — GUI code is difficult to unit test. Integration tests in `tests/test_integration_v35.py` partially cover this.

---

## Exception Handling Issues

### EXC-01: IAPWS Failures Not Visually Indicated in GUI
- Issue: `water_density_gcm3()` falls back to 0.9998 g/cm³ when IAPWS calculation fails, logging at `logger.warning` level. Similarly, `ice_ih_density_gcm3()` falls back to 0.9167 g/cm³. Neither fallback is shown to the user in the GUI — the generation silently proceeds with approximate density values.
- Files: `quickice/phase_mapping/water_density.py:70-93`, `quickice/phase_mapping/ice_ih_density.py:63-75`
- Impact: User may not realize the water layer density in interface structures is approximate (~0.3% error for water fallback, varies for ice Ih). For most conditions this is negligible, but for extreme T/P conditions the error could be larger.
- Fix approach: Emit a Qt signal from the generation worker when fallback density is used. Display a yellow warning badge in the status bar. At minimum, add a note in the generation report.

### EXC-03: Three Export Handlers Missing traceback.print_exc()
- Issue: `IonGROMACSExporter.export_ion_gromacs()`, `GROMACSExporter.export_gromacs()`, and `InterfaceGROMACSExporter.export_interface_gromacs()` show error dialogs but don't print tracebacks, unlike `SoluteGROMACSExporter` and `CustomMoleculeGROMACSExporter` which do include `traceback.print_exc()`.
- Files: `quickice/gui/export.py:370-374`, `quickice/gui/export.py:725-729`, `quickice/gui/export.py:882-886`
- Impact: Makes debugging export failures harder for users and developers
- Fix approach: Add `import traceback; traceback.print_exc()` to all three handlers for consistency with other exporters.

---

## PyInstaller Bundle Size Concerns

### BUNDLE-01: PyInstaller Spec Now Excludes Tests (FIXED)
- Issue: The `excludes` list in `quickice-gui.spec:27` now contains `['*/tests/*', '*/test/*', '*/docs/*', '*/__pycache__/*', '*/.pytest_cache/*', '*/egg-info/*']`, filtering out test files from all collected packages.
- Files: `quickice-gui.spec:27`
- Status: **FIXED** — test directories are now excluded from the bundle.

### BUNDLE-02: GenIce2 Includes All Lattice/Molecule/Format Plugins
- Issue: GenIce2's plugin system means `collect_all('genice2')` includes ALL lattice types, molecule types, and format plugins — many of which QuickIce never uses. QuickIce only uses: `genice2.genice.GenIce`, `genice2.plugin.safe_import`, lattices for supported ice phases (1h, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, sI, sII, sH), the `tip3p` molecule, the `tip4p` molecule, and the `gromacs` format.
- Files: `quickice-gui.spec:9`
- Impact: Unnecessary lattice modules (obscure ice phases, non-ice crystal structures), molecule types (many water models QuickIce doesn't use), and format modules (PDB, CIF, etc.) are bundled. Estimated wasted space: 20-50 MB.
- Fix approach: Replace `collect_all('genice2')` with targeted `collect_submodules()` + `collect_data_files()` specifying only the submodules QuickIce uses. This requires enumerating all supported phase lattice names from `quickice/structure_generation/mapper.py`.

---

## Test Coverage Gaps

### TEST-01: GROMACS Export End-to-End Testing (Full Chain)
- What's not tested: Complete GRO+TOP+ITP export for ion structures with solutes AND custom molecules present (the full interface→custom→solute→ion chain). Tests exist for individual tabs but not the full chain.
- Files: `quickice/output/gromacs_writer.py`, `quickice/gui/export.py`
- Risk: Changes to attribute passing between tabs could silently break export
- Priority: High

### TEST-02: Pocket Mode Edge Cases
- What's not tested: Pocket mode with very thin cavities, large boxes with small pockets, non-spherical cavities
- Files: `quickice/structure_generation/modes/pocket.py`
- Risk: Pocket mode could produce incorrect structures for unusual parameters
- Priority: Medium

### TEST-03: Triclinic Cell Interface Generation
- What's not tested: Interface generation for triclinic ice phases (Ice II, Ice V). The code currently blocks these phases, but if support is added, there are no tests to validate it.
- Files: `quickice/structure_generation/modes/slab.py`, `quickice/structure_generation/modes/pocket.py`, `quickice/structure_generation/modes/piece.py`
- Risk: Triclinic cell handling may be broken when this feature is enabled
- Priority: Medium (currently blocked by design)

### TEST-05: Atom Count Consistency After Multiple Overlap Removal Steps
- What's not tested: Scenarios where both ice-water overlap AND guest-water overlap removal occur in slab mode (the `# GUEST-WATER OVERLAP FIX` section in `slab.py:532-564`).
- Files: `quickice/structure_generation/modes/slab.py:532-564`
- Risk: Invariant `water_atom_count == water_nmolecules * 4` could break after two rounds of overlap removal
- Priority: High

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

## Previously Fixed Issues (Reference Only)

The following issues were identified in prior analyses and have been **FIXED**. They are listed here for traceability only — do not treat as active concerns.

| ID | Description | Key File |
|----|-------------|----------|
| FLOW-01/02/03 | Exporter crashes/wrong output | `quickice/output/gromacs_writer.py` |
| BUG-01 | OW safeguard | `quickice/structure_generation/modes/*.py` |
| BUG-02a/b/c | THF formula | `quickice/structure_generation/types.py` |
| BUG-03 | O(n²) residue lookup | `quickice/output/gromacs_writer.py:1102` |
| MOL-1–5 | Naming mismatches | Various |
| KS-1/2/3 | Keyboard shortcuts | `quickice/gui/main_window.py` |
| FF-1 | GAFF→GAFF2 | `quickice/output/gromacs_writer.py` |
| FRAG-01/02 | Fragile code (assertions added) | `quickice/structure_generation/modes/*.py` |
| EXC-02 | FileNotFoundError:pass | `quickice/gui/export.py` |
| EXP-1/2 | Filename patterns | `quickice/output/` |
| VER-1 | Version | `quickice/__init__.py` |
| CIT-GAFF2 | Citations | `quickice/output/gromacs_writer.py` |
| SCI-01/03/04 | Scientific accuracy | Various |
| TD-05/06 | Threading/cache | `quickice/structure_generation/generator.py` |
| SEC-01 | Path.resolve | `quickice/main.py` |
| BUNDLE-01 | PyInstaller excludes | `quickice-gui.spec` |
| TEST-01/02/04/05 | Test gaps | `tests/` |
| NEW-01/02 | Logger/dead imports | Various |
| FRAG-04a/b | Resilience improvements | Various |
| UNIT-01/03 | Validation/logging | Various |

---

*Concerns audit: 2026-05-22*
