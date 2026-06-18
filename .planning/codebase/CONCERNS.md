# Codebase Concerns

**Analysis Date:** 2026-06-18

## Resolved Since 2026-06-15

The following concerns were fixed by Phase 34.9 and Phase 37.1 and are **no longer open**:

| ID | Concern | Resolution |
|----|---------|------------|
| AN-01 | `MOLECULE_TYPE_INFO["ice"]["atoms"]` = 3 (should be 4) | Fixed: `quickice/structure_generation/types.py` line 12 now has `atoms: 4` |
| AN-02 | MW recomputed incorrectly on 4-atom ice | Fixed: MW uses wrapped positions, computed from O+H1+H2 when count=3, read directly when count=4 |
| AN-03 | Solute/custom positions not PBC-wrapped | Fixed: `write_interface_gro_file` lines 690-695, `write_ion_gro_file` lines 1446-1455 wrap via modulo |
| UM-01 | AVOGADRO hardcoded in multiple places | Fixed: Single definition in `quickice/structure_generation/ion_inserter.py` line 29 |
| V-02 | cKDTree O(N²) rebuild on every attempt | Fixed: Conditional rebuild only after successful placement (`solute_inserter.py` lines 868-874) |
| V-05 | Unknown atoms silently skipped | Fixed: `molecule_index` entry created + warning logged |
| V-07 | `detect_atoms_per_molecule` duplicated | Fixed: Moved to `quickice/structure_generation/types.py` line 28 |
| V-17 | `solute_inserter._remove_overlapping_water` mutates input | Fixed: Creates new `InterfaceStructure` instead of mutating (lines 462-514) |
| UM-02 | `WATER_VOLUME_NM3` missing | Fixed: Constant added at `quickice/structure_generation/types.py` line 25 |
| UM-03 | `water_fraction` heuristic unreliable | Fixed: Replaced with `water_nmolecules * WATER_VOLUME_NM3` volume calculation |
| CP-03 | No range validation for concentration/occupancy | Fixed: `validate_concentration_range` and `validate_occupancy_range` in `quickice/validation/validators.py` lines 150-206 |
| SEC-02 | No file extension validation on .gro/.itp | Fixed: Extension validation added |
| EH-01 | No GRO file I/O protection | Fixed: `try/except (OSError, ValueError)` with cleanup in gromacs_writer.py |
| EH-02 | No hydrate wrapper assertion | Fixed: Atom count assertion in `quickice/cli/pipeline.py` lines 720-723 |
| EH-05 | Bare `except Exception` in gromacs_writer.py | Fixed: Changed to `except (OSError, ValueError)` throughout |
| DOC-C1/C2/C3/C4/G1/G2/G3/G4 | Documentation issues | Fixed: All resolved |
| TIP4P-ICE LJ | Wrong sigma/epsilon in TOP atomtypes | Fixed: `TIP4P_ICE_OW_SIGMA`/`TIP4P_ICE_OW_EPSILON` constants used in all 6 TOP-writing functions |
| comb-rule | comb-rule=1 (geometric) incompatible with AMBER | Fixed: Reverted to comb-rule=2 (Lorentz-Berthelot) in all 6 TOP-writing functions |
| GROMACS skipif | Tests fail when `gmx` not installed | Fixed: `gmx_skipif` marker in `tests/conftest.py` lines 18-27, applied to all gmx test classes |
| Hydrate-only grompp | No `TestHydrateGmxValidation` | Fixed: Added at `tests/test_e2e_gmx_validation.py` line 1102 |
| Solute-only grompp | No solute-only grompp test | Fixed: `TestSoluteGmxValidation` added at line 1205 |
| Custom-only grompp | No custom-only grompp test | Fixed: `TestCustomMoleculeGmxValidation` added at line 1172 |
| CLI grompp (partial) | No CLI subprocess grompp tests | Fixed: `TestPipelineGromppValidation` at `tests/test_cli_pipeline.py` line 694 |

## Accepted Design Decisions

**CP-01: Duck-typing on InterfaceStructure:**
- Decision: `getattr()`/`hasattr()` pattern is accepted as the design approach for polymorphic structure handling
- Files: `quickice/structure_generation/solute_inserter.py` lines 78-95, `quickice/gui/custom_molecule_panel.py` lines 1038-1040, `quickice/cli/itp_helpers.py` lines 101, 341-347
- Rationale: The codebase intentionally uses structural typing (duck-typing) rather than `isinstance()` checks for structure objects. `InterfaceStructure`, `CustomMoleculeStructure`, `SoluteStructure`, and `IonStructure` share common attributes (`ice_atom_count`, `water_atom_count`, `guest_atom_count`, `molecule_index`) but are distinct dataclasses. Adding formal protocols or base classes would increase coupling without sufficient benefit. The `getattr(..., default)` pattern is intentional and well-tested.
- Impact: Callers must handle `AttributeError` if new structure types are added without the expected attributes. Tests cover all current structure types.

## Tech Debt

**FRAG-03: gromacs_writer.py is a 2802-line monolith:**
- Issue: Single file contains 16 write functions, 6 TOP-writing functions with duplicated atomtype blocks, guest detection heuristics, and 3 different GRO writing patterns (ice-only, interface, multi-molecule)
- Files: `quickice/output/gromacs_writer.py`
- Impact: Grew from ~2054 to 2802 lines after `write_solute_gro_file`/`write_solute_top_file` additions in Phase 37.1. Makes code review, debugging, and refactoring harder. Each new structure type adds ~150 lines of near-identical GRO/TOP writing code
- Fix approach: Split into per-structure-type modules (e.g., `ice_writer.py`, `interface_writer.py`, `ion_writer.py`, `solute_writer.py`, `custom_writer.py`) with shared base functions for atomtype emission, `#include` directives, and `[molecules]` section. Extract `detect_guest_type_from_atoms()` and `reorder_guest_atoms()` to a shared utility module

**TD-01: Duplicate GRO-writing code across 6 writer functions:**
- Issue: `write_interface_gro_file`, `write_ion_gro_file`, `write_custom_molecule_gro_file`, `write_solute_gro_file`, `write_multi_molecule_gro_file`, and `write_gro_file` all contain near-identical ice→4-atom expansion logic, SOL formatting, and atom numbering. The solute writer alone added ~330 lines of duplicated SOL-writing code
- Files: `quickice/output/gromacs_writer.py` lines 435-533, 631-854, 1092-1186, 1349-1699, 1918-2137, 2273-2600
- Impact: Any fix to SOL formatting or atom numbering must be applied in 6+ places. Bug introductions are likely
- Fix approach: Extract a shared `write_sol_molecule()` helper and a shared `write_ice_molecule()` helper. Each writer delegates atom formatting to shared functions, keeping only structure-specific ordering logic

**TD-07: No upload-time atomtypes validation for custom molecule ITP:**
- Issue: `comment_out_atomtypes_in_itp()` silently modifies user ITP content at export time. If a custom ITP has atomtypes that conflict with TIP4P-ICE/GAFF2 types (e.g., redefining `OW_ice`), the conflict is only detected at `gmx grompp` time, not at upload
- Files: `quickice/output/gromacs_writer.py` lines 319-363, `quickice/gui/custom_molecule_panel.py` lines 633-680
- Impact: User may upload a bad ITP, generate a full structure, and only discover the atomtype conflict at export time (wasted computation)
- Fix approach: Add atomtype overlap check in `validate_custom_molecule()` at upload time, warning user about potential conflicts with built-in types

**TD-ADHOC: `type('obj', (object,), {...})()` ad-hoc molecule objects:**
- Issue: `write_ion_gro_file`, `write_solute_gro_file`, and `write_custom_molecule_gro_file` create anonymous ad-hoc objects with `type('obj', (object,), {'start_idx': ..., 'count': ..., 'mol_type': ...})()` to represent molecule entries. These untyped objects bypass dataclass validation and have no IDE support
- Files: `quickice/output/gromacs_writer.py` lines 1386-1390, 1397-1401, 2308-2319, 2333-2337, 2349-2353, 2359-2363
- Impact: Fragile — any attribute name typo silently produces wrong behavior. No type checking. Inconsistent with `MoleculeIndex` dataclass used elsewhere
- Fix approach: Replace with `MoleculeIndex(start_idx=..., count=..., mol_type=...)` from `quickice/structure_generation/types.py`, or define a lightweight `MoleculeEntry` dataclass

**TD-CONST: AVOGADRO defined in ion_inserter.py, not in shared constants:**
- Issue: `AVOGADRO = 6.02214076e23` is defined in `quickice/structure_generation/ion_inserter.py` line 29 and imported by 4 other modules (`solute_inserter.py`, `custom_molecule_inserter.py`, `cli/pipeline.py`, `ranking/scorer.py`). A physics constant should live in a shared location, not a domain-specific inserter module
- Files: `quickice/structure_generation/ion_inserter.py` line 29
- Impact: Import dependency on ion_inserter for code that doesn't use ion insertion. Circular dependency risk if ion_inserter ever needs to import from a consumer
- Fix approach: Move to `quickice/structure_generation/types.py` (alongside `WATER_VOLUME_NM3`, `WATER_ATOMS_PER_MOLECULE`) or create `quickice/constants.py`

## Known Bugs

**SOLUTE-PBC: Custom molecule positions not PBC-wrapped in `write_solute_gro_file`:**
- Symptoms: Custom molecule atoms written to .gro file may have coordinates outside [0, box_size) when custom molecules were placed near PBC boundaries
- Files: `quickice/output/gromacs_writer.py` lines 2544-2547 — `solute_structure.custom_molecule_positions` used directly without PBC wrapping
- Trigger: Export solute structure with custom molecules after placement near box edge
- Impact: Invalid GRO coordinates (negative or > box size). May cause `gmx grompp` failure or simulation artifacts
- Workaround: None at code level. `write_ion_gro_file` correctly wraps custom positions (lines 1452-1455) and solute positions (lines 1447-1450), but `write_solute_gro_file` does not
- Fix approach: Add `wrapped_custom_positions = solute_structure.custom_molecule_positions % np.diag(solute_structure.interface_structure.cell)` before writing, matching the pattern in `write_ion_gro_file`

**TRICLINIC-WRAP: `wrap_positions_into_box` and `wrap_molecules_into_box` only use diagonal cell elements:**
- Symptoms: For triclinic cells (Ice II, Ice III, Ice V, Ice VI, Ice VIII), PBC wrapping uses only `cell[dim, dim]` (diagonal), ignoring off-diagonal elements. This produces incorrect wrapping for non-orthorhombic cells
- Files: `quickice/output/gromacs_writer.py` lines 46-64 (`wrap_positions_into_box`), lines 67-140 (`wrap_molecules_into_box`)
- Trigger: Generate any triclinic ice phase and export as GRO
- Impact: Atoms in triclinic systems may be wrapped to wrong periodic image. GROMACS may reject the structure or produce simulation artifacts
- Workaround: Currently only Ice Ih (orthorhombic) is commonly exported. Other ice phases use the cell transformation in `quickice/structure_generation/modes/slab.py` but the wrapping functions don't account for it
- Fix approach: Use fractional coordinates for wrapping: `frac = positions @ inv(cell)`, wrap `frac` into [0,1), then `wrapped = frac @ cell`. This correctly handles arbitrary triclinic cells

## Security Considerations

**Subprocess execution in tests:**
- Risk: `run_gmx_grompp()` and `run_quickice()` run subprocesses with `shell=False` and explicit args — no injection risk
- Files: `tests/e2e_export_helpers.py` lines 443-487, `tests/conftest.py` lines 222-247
- Current mitigation: Proper subprocess usage with explicit arg list
- Recommendations: No changes needed

**Bare `except Exception` in GUI error handlers:**
- Risk: 40+ `except Exception` blocks in GUI code catch more than intended, potentially masking real bugs
- Files: `quickice/gui/export.py` (8 occurrences), `quickice/gui/main_window.py` (5), `quickice/gui/custom_molecule_panel.py` (3), `quickice/gui/workers.py` (2)
- Current mitigation: GUI error handlers typically show error dialog + log the exception, which is reasonable UX. Most are catching `QFileDialog` or `subprocess` failures
- Recommendations: Narrow exceptions where possible (e.g., `except (OSError, RuntimeError)` instead of `except Exception`). Low priority since GUI error handlers must be broad to avoid crashing the application

## Performance Bottlenecks

**Grompp tests are slow but isolated:**
- Problem: Each grompp test requires GenIce2 generation (~3-5s) + file writing + subprocess grompp (~2-5s)
- Files: `tests/test_e2e_gmx_validation.py`
- Cause: Tests use real structure generation (not mocked)
- Improvement path: Module-scoped fixtures in `conftest.py` amortize generation cost across test classes, but each test class still generates its own chain

## Fragile Areas

**ITP staging dual path:**
- Files: `tests/e2e_export_helpers.py` `_stage_itp_files()` vs `quickice/cli/itp_helpers.py` `copy_itp_files_for_structure()`
- Why fragile: Two separate ITP staging implementations; API tests use one, CLI uses the other. Divergence could introduce CLI-only bugs
- Safe modification: Ensure both paths produce identical ITP file sets; add integration test that validates CLI output matches API output
- Test coverage: API path is grompp-validated by 27+ test classes in `test_e2e_gmx_validation.py`; CLI path is grompp-validated by 2 tests in `test_cli_pipeline.py` `TestPipelineGromppValidation`

**Guest type detection heuristic:**
- Files: `quickice/output/gromacs_writer.py` lines 857-979 (`_get_molecule_atoms`, `detect_guest_type_from_atoms`)
- Why fragile: Pattern-matching heuristic that identifies CH4, THF, CO2, H2 based on atom name composition. The heuristic in `molecule_utils.py` line 66 explicitly warns that "any C-starting molecule with an O atom" would be misidentified as THF
- Safe modification: Currently works because QuickIce only supports CH4 and THF guests. Adding new guest types (e.g., methanol, CO2, acetone) would break the heuristic
- Test coverage: `detect_guest_type_from_atoms` tested via grompp validation tests (which implicitly verify correct guest ITP is included). No unit tests for the heuristic itself

**Solute GRO writer fallback when `molecule_index` is empty:**
- Files: `quickice/output/gromacs_writer.py` lines 2305-2319
- Why fragile: When `interface.molecule_index` is empty (real GenIce2 data), synthetic molecule entries are created using `atoms_per_ice_mol = 3 if "O" in interface.atom_names[:interface.ice_atom_count] else 4`. This detection by atom name assumes ice atoms use "O" and hydrate atoms use "OW", but the detection only checks the first `ice_atom_count` names
- Safe modification: Add explicit `ice_atoms_per_molecule` attribute to `InterfaceStructure` to avoid heuristic detection at export time
- Test coverage: Covered by `TestSoluteGmxValidation` which uses API-level structures (with `molecule_index` populated). The fallback path (empty `molecule_index`) is exercised by CLI pipeline tests

## Scaling Limits

**GRO atom number limit (99,999):**
- Problem: GROMACS .gro format wraps atom numbers at 100,000. Large systems (e.g., 256×4=1024 atoms for ice Ih + water + ions) can exceed this
- Files: `quickice/output/gromacs_writer.py` — all write functions have `% 100000` wrapping and warning logs
- Current capacity: Works correctly for systems up to ~25,000 molecules (100,000 atoms). Above that, atom numbers wrap but GROMACS still reads the file correctly
- Limit: Atom numbers wrap but simulation still works. The warning is informational only
- Scaling path: GRO format limitation is inherent. For larger systems, users should export to .pdb or .tng format (not yet implemented)

## Dependencies at Risk

**TD-05: GenIce2 uses `np.random` global state (not thread-safe):**
- Risk: `np.random.seed()`/`np.random.set_state()` manipulate global numpy RNG, which is not thread-safe. If QuickIce ever runs structure generation in parallel threads, race conditions would corrupt random state
- Files: `quickice/structure_generation/generator.py` lines 101-157
- Current mitigation: QuickIce is single-threaded. The `try/finally` block restores numpy state after GenIce2 calls
- Impact: Would break reproducibility if parallel generation is added
- Migration plan: Use `numpy.random.Generator` API when GenIce2 supports it. Blocked on external dependency

**BUNDLE-02: `collect_all('genice2')` includes unused lattice/molecule/format plugins:**
- Risk: PyInstaller bundles ALL GenIce2 plugins, including unused lattice types and format plugins. Increases bundle size
- Files: `quickice-gui.spec` (PyInstaller spec), `quickice/structure_generation/generator.py`
- Impact: Larger distribution binary (~50-100 MB of unused GenIce2 plugins)
- Migration plan: Use `collect_submodules()` with targeted patterns for specific lattices (only `ice1h`, `ice1c`, `ice2`, `ice3`, `ice5`, `ice6`, `ice7`, `ice8`, `sI`, `sII`, `sH`). Requires careful testing because genice2's `safe_import()` dynamically loads plugins

## Missing Critical Features

**No GUI export grompp coverage:**
- Problem: GUI export tests (`tests/test_output/`) mock QFileDialogs but never validate grompp on output
- Files: `tests/test_output/test_gromacs_export_*.py`
- Blocks: Detecting GUI export bugs that produce GROMACS-invalid files

**No concentration/occupancy validator test coverage:**
- Problem: `validate_concentration_range` and `validate_occupancy_range` in `quickice/validation/validators.py` lines 150-206 have zero test coverage. `tests/test_validators.py` only tests temperature, pressure, nmolecules, and box_dimension validators
- Files: `quickice/validation/validators.py` lines 150-206, `tests/test_validators.py`
- Blocks: Catching validation boundary errors in concentration/occupancy inputs (used by CLI `--ion-concentration`, `--solute-concentration`, `--cage-occupancy-small`, `--cage-occupancy-large`)

## Test Coverage Gaps

**CLI grompp validation — incomplete coverage:**
- What's not tested: Hydrate-only CLI grompp, custom-only CLI grompp, solute-only CLI grompp. Only 2 of 6+ CLI workflow combos are tested
- Files: `tests/test_cli_pipeline.py` lines 694-769 (`TestPipelineGromppValidation` has only `test_slab_interface_grompp` and `test_solute_ion_chain_grompp`)
- Risk: CLI ITP staging (`copy_itp_files_for_structure`) for hydrate, custom, and solute-only workflows is not grompp-validated
- Priority: High

**Ice phase variety grompp:**
- What's not tested: Ice Ic, Ice III, Ice V, Ice VI, Ice VII, Ice VIII exports validated by grompp
- Files: `tests/test_e2e_gmx_validation.py` (only Ice Ih tested)
- Risk: Different lattice types may produce GRO formatting issues for other phases
- Priority: Low (orthorhombic phases work; triclinic phases blocked by TRICLINIC-WRAP concern)

**`detect_guest_type_from_atoms` heuristic unit tests:**
- What's not tested: The guest type detection heuristic that differentiates CH4, THF, CO2, H2 from atom name patterns
- Files: `quickice/output/gromacs_writer.py` lines 857-979
- Risk: Heuristic changes or new guest types could silently break guest detection, causing wrong ITP files to be included
- Priority: Medium

**`wrap_molecules_into_box` for triclinic cells:**
- What's not tested: PBC molecule wrapping with non-orthorhombic cell vectors
- Files: `quickice/output/gromacs_writer.py` lines 67-140
- Risk: Triclinic cell wrapping may place atoms in wrong periodic image
- Priority: Medium (blocked by TRICLINIC-WRAP)

---

*Concerns audit: 2026-06-18*
