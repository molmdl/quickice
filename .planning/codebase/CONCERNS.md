# Codebase Concerns

**Analysis Date:** 2026-07-14

## Resolved Since 2026-06-15

The following concerns were fixed by Phase 34.9, Phase 37.1, and later patches and are **no longer open**:

| ID | Concern | Resolution |
|----|---------|------------|
| AN-01 | `MOLECULE_TYPE_INFO["ice"]["atoms"]` = 3 (should be 4) | Fixed: `quickice/structure_generation/types.py` now has `atoms: 4` |
| AN-02 | MW recomputed incorrectly on 4-atom ice | Fixed: MW uses wrapped positions, computed from O+H1+H2 when count=3, read directly when count=4 |
| AN-03 | Solute/custom positions not PBC-wrapped | Fixed: PBC wrapping added to GRO writers (see SOLUTE-PBC below) |
| UM-01 | AVOGADRO hardcoded in multiple places | Fixed: Single definition in `quickice/structure_generation/ion_inserter.py` line 29 |
| V-02 | cKDTree O(N²) rebuild on every attempt | Fixed: Conditional rebuild only after successful placement (`quickice/structure_generation/solute_inserter.py`) |
| V-05 | Unknown atoms silently skipped | Fixed: `molecule_index` entry created + warning logged |
| V-07 | `detect_atoms_per_molecule` duplicated | Fixed: Moved to `quickice/structure_generation/types.py` |
| V-17 | `solute_inserter._remove_overlapping_water` mutates input | Fixed: Creates a NEW `InterfaceStructure` instead of mutating (`quickice/structure_generation/solute_inserter.py` line 521) |
| UM-02 | `WATER_VOLUME_NM3` missing | Fixed: Constant added at `quickice/structure_generation/types.py` line 39 |
| UM-03 | `water_fraction` heuristic unreliable | Fixed: Replaced with `water_nmolecules * WATER_VOLUME_NM3` volume calculation |
| CP-03 | No range validation for concentration/occupancy | Fixed: `validate_concentration_range` and `validate_occupancy_range` in `quickice/validation/validators.py` lines 150-206 |
| SEC-02 | No file extension validation on .gro/.itp | Fixed: Extension validation added |
| EH-01 | No GRO file I/O protection | Fixed: `try/except (OSError, ValueError)` with cleanup in `quickice/output/gromacs_writer.py` |
| EH-02 | No hydrate wrapper assertion | Fixed: Atom count assertion in `quickice/cli/pipeline.py` |
| EH-05 | Bare `except Exception` in pipeline | Fixed: `quickice/cli/pipeline.py` uses `except (ValueError, OSError)` — no bare `except Exception` (verified 2026-07-14) |
| DOC-* | Documentation issues | Fixed: All resolved |
| TIP4P-ICE LJ | Wrong sigma/epsilon in TOP atomtypes | Fixed: `TIP4P_ICE_OW_SIGMA`/`TIP4P_ICE_OW_EPSILON` constants used in all TOP-writing functions |
| comb-rule | comb-rule=1 (geometric) incompatible with AMBER | Fixed: comb-rule=2 (Lorentz-Berthelot) enforced via `quickice/structure_generation/itp_parser.py` `parse_itp_defaults_comb_rule()` (verified 2026-07-14) |
| GROMACS skipif | Tests fail when `gmx` not installed | Fixed: `gmx_skipif` marker in `tests/conftest.py`, applied to all gmx test classes |
| Hydrate/Solute/Custom grompp | Missing grompp test classes | Fixed: `TestHydrateGmxValidation`, `TestSoluteGmxValidation`, `TestCustomMoleculeGmxValidation` in `tests/test_e2e_gmx_validation.py` |
| CLI grompp (partial) | No CLI subprocess grompp tests | Fixed: `TestPipelineGromppValidation` at `tests/test_cli_pipeline.py` line 694 |
| SOLUTE-PBC | Custom molecule positions not PBC-wrapped in `write_solute_gro_file` | Fixed: `quickice/output/gromacs_writer.py` line 3512 now wraps via `solute_structure.custom_molecule_positions % np.diag(solute_structure.cell)`. All three writers now wrap custom positions: `write_interface_gro_file` (line 1147), `write_ion_gro_file` (line 2200), `write_solute_gro_file` (line 3512) |

## Accepted Design Decisions (document as fragility, NOT as bugs)

**CP-01: Duck-typing on `InterfaceStructure`:**
- Decision: `getattr()`/`hasattr()` pattern is the accepted design for polymorphic structure handling. Runtime attributes (`.solute_type`, `.custom_molecule_positions`, etc.) are duck-typed onto structure objects.
- Files: `quickice/structure_generation/solute_inserter.py` lines 78-95, `quickice/gui/custom_molecule_panel.py` lines 1038-1040, `quickice/cli/itp_helpers.py` lines 101, 341-347
- Rationale: `InterfaceStructure`, `CustomMoleculeStructure`, `SoluteStructure`, and `IonStructure` share common attributes (`ice_atom_count`, `water_atom_count`, `guest_atom_count`, `molecule_index`) but are distinct dataclasses. Formal protocols/base classes were judged to increase coupling without sufficient benefit.
- Impact: Callers must handle `AttributeError` if new structure types are added without expected attributes. Tests cover all current structure types.

**GUI `HydrateWorker` subclasses `QThread` directly:**
- Decision: `HydrateWorker` subclasses `QThread` directly (NOT migrated to `QObject` + `moveToThread`). This is an accepted design decision per AGENTS.md — do NOT "fix" this.
- Files: `quickice/gui/workers.py`
- Impact: Standard Qt threading caveat applies (worker must not touch GUI widgets directly). Not a bug.

**Module physical constants:**
- `WATER_VOLUME_NM3`, `WATER_ATOMS_PER_MOLECULE`, `TIP4P_ICE_OW_SIGMA`, `TIP4P_ICE_OW_EPSILON` are defined once as module constants — accepted pattern. Flagged below ONLY where the placement of a constant is awkward (TD-CONST), not where it is duplicated or hardcoded.

## Tech Debt

**FRAG-03: `gromacs_writer.py` is a 4067-line monolith (growing):**
- Issue: Single file contains all GRO/TOP writers, 6 TOP-writing functions with duplicated atomtype blocks, guest-detection heuristics, and 6 distinct GRO-writing functions. Grew from ~2802 to **4067 lines** after Phase 37.1 additions.
- Files: `quickice/output/gromacs_writer.py`
- Impact: Each new structure type adds ~150 lines of near-identical GRO/TOP writing code. Code review, debugging, and refactoring are difficult; merge conflicts are likely. The largest single file in the codebase by a wide margin (next largest is `quickice/gui/main_window.py` at 2174 lines).
- Fix approach: Split into per-structure-type modules (e.g., `ice_writer.py`, `interface_writer.py`, `ion_writer.py`, `solute_writer.py`, `custom_writer.py`) with shared base functions for atomtype emission, `#include` directives, and `[molecules]` section. Extract `detect_guest_type_from_atoms()` and `reorder_guest_atoms()` to a shared utility module.

**TD-01: Duplicate GRO-writing code across 6 writer functions:**
- Issue: `write_gro_file`, `write_interface_gro_file`, `write_multi_molecule_gro_file`, `write_ion_gro_file`, `write_custom_molecule_gro_file`, and `write_solute_gro_file` all contain near-identical ice→4-atom expansion logic, SOL formatting, and atom numbering.
- Files: `quickice/output/gromacs_writer.py` — `write_gro_file` (line 833), `write_interface_gro_file` (line 1044), `write_multi_molecule_gro_file` (line 1688), `write_ion_gro_file` (line 2044), `write_custom_molecule_gro_file` (line 2803), `write_solute_gro_file` (line 3336)
- Impact: Any fix to SOL formatting or atom numbering must be applied in 6+ places. Bug introductions are likely (the SOLUTE-PBC bug above was exactly this class of issue — wrapping existed in 2 writers but was missing from the 3rd).
- Fix approach: Extract a shared `write_sol_molecule()` helper and a shared `write_ice_molecule()` helper. Each writer delegates atom formatting to shared functions, keeping only structure-specific ordering logic.

**TD-07: No upload-time atomtypes validation for custom molecule ITP:**
- Issue: `comment_out_atomtypes_in_itp()` silently modifies user ITP content at export time. If a custom ITP has atomtypes that conflict with TIP4P-ICE/GAFF2 types (e.g., redefining `OW_ice`), the conflict is only detected at `gmx grompp` time, not at upload.
- Files: `quickice/output/gromacs_writer.py` (ITP staging), `quickice/gui/custom_molecule_panel.py` lines 633-680
- Impact: User may upload a bad ITP, generate a full structure, and only discover the atomtype conflict at export time (wasted computation).
- Fix approach: Add an atomtype overlap check in `validate_custom_molecule()` at upload time, warning the user about potential conflicts with built-in types.

**TD-ADHOC: `type('obj', (object,), {...})()` ad-hoc molecule objects:**
- Issue: The ion and solute GRO writers create anonymous ad-hoc objects with `type('obj', (object,), {'start_idx': ..., 'count': ..., 'mol_type': ...})()` to represent ordered molecule entries. These untyped objects bypass dataclass validation and have no IDE support.
- Files: `quickice/output/gromacs_writer.py` lines 2133, 2144 (in `write_ion_gro_file`), lines 3415, 3422, 3448, 3464, 3474 (in `write_solute_gro_file`)
- Impact: Fragile — any attribute-name typo silently produces wrong behavior. No type checking. Inconsistent with the `MoleculeIndex` dataclass used elsewhere.
- Fix approach: Replace with `MoleculeIndex(start_idx=..., count=..., mol_type=...)` from `quickice/structure_generation/types.py`, or define a lightweight `MoleculeEntry` dataclass.

**TD-CONST: `AVOGADRO` defined in `ion_inserter.py`, not in a shared constants module:**
- Issue: `AVOGADRO = 6.02214076e23` is defined once at `quickice/structure_generation/ion_inserter.py` line 29 (single definition, NOT duplicated — this is the accepted pattern, so this is a placement concern only). Four other modules import it from `ion_inserter`, creating an awkward dependency on a domain-specific inserter for code that does not perform ion insertion.
- Files: defined at `quickice/structure_generation/ion_inserter.py` line 29; imported by `quickice/structure_generation/custom_molecule_inserter.py` line 28, `quickice/structure_generation/solute_inserter.py` line 28, `quickice/ranking/scorer.py` line 18, `quickice/cli/pipeline.py` line 15
- Impact: Import dependency on `ion_inserter` for code unrelated to ion insertion. Circular-dependency risk if `ion_inserter` ever needs to import from a consumer. Importing a side-effect-heavy module just for a constant is brittle.
- Fix approach: Move `AVOGADRO` to `quickice/structure_generation/types.py` (alongside `WATER_VOLUME_NM3`, `WATER_ATOMS_PER_MOLECULE`) or create `quickice/constants.py`, then re-point the 4 importers.

## Known Bugs

**TRICLINIC-WRAP: `wrap_positions_into_box` and `wrap_molecules_into_box` ignore off-diagonal cell elements:**
- Symptoms: For triclinic cells (Ice II, Ice III, Ice V, Ice VI, Ice VIII), PBC wrapping uses only `cell[dim, dim]` (the diagonal), ignoring off-diagonal tilt. Wrapped positions are wrong for non-orthorhombic cells.
- Files: `quickice/output/gromacs_writer.py` — `wrap_positions_into_box` at line 291, `wrap_molecules_into_box` at line 312
- Trigger: Generate any triclinic ice phase and export as GRO.
- Impact: Atoms in triclinic systems may be wrapped to the wrong periodic image. GROMACS may reject the structure or produce simulation artifacts.
- Workaround: Currently only Ice Ih (orthorhombic) is commonly exported. Other ice phases use the cell transformation in `quickice/structure_generation/modes/slab.py` but the wrapping functions do not account for it.
- Fix approach: Use fractional coordinates for wrapping: `frac = positions @ np.linalg.inv(cell)`, wrap `frac` into [0,1), then `wrapped = frac @ cell`. This correctly handles arbitrary triclinic cells. Note `quickice/structure_generation/hydrate_generator.py` (lines 470, 569) already uses the `np.allclose(cell - np.diag(np.diag(cell)), 0)` orthorhombic check — the wrapping functions should branch on the same test.

## Security Considerations

**Subprocess execution in tests:**
- Risk: `run_gmx_grompp()` and `run_quickice()` run subprocesses with `shell=False` and explicit arg lists — no shell-injection risk.
- Files: `tests/e2e_export_helpers.py` lines 443-487, `tests/conftest.py` lines 222-247
- Current mitigation: Proper subprocess usage with explicit arg list.
- Recommendations: No changes needed.

**Broad `except Exception` in GUI error handlers:**
- Risk: 40+ `except Exception` blocks in GUI code catch more than intended, potentially masking real bugs.
- Files: `quickice/gui/export.py` (8 occurrences), `quickice/gui/main_window.py` (5), `quickice/gui/custom_molecule_panel.py` (3), `quickice/gui/workers.py` (2)
- Current mitigation: GUI error handlers typically show an error dialog + log the exception, which is reasonable UX. Most catch `QFileDialog` or `subprocess` failures. AGENTS.md explicitly permits broad catches in GUI code (only `quickice/cli/pipeline.py` is barred from bare `except Exception`).
- Recommendations: Narrow where possible (e.g., `except (OSError, RuntimeError)`). Low priority — GUI handlers must be broad to avoid crashing the application.

## Performance Bottlenecks

**Grompp tests are slow but isolated:**
- Problem: Each grompp test requires GenIce2 generation (~3-5s) + file writing + subprocess grompp (~2-5s).
- Files: `tests/test_e2e_gmx_validation.py`
- Cause: Tests use real structure generation (not mocked).
- Improvement path: Module-scoped fixtures in `tests/conftest.py` amortize generation cost across test classes, but each test class still generates its own chain.

**Insertion loops are O(n_molecules × max_attempts):**
- Problem: Molecule inserters (`solute_inserter`, `custom_molecule_inserter`) nest an attempt loop inside a molecule loop, so runtime scales as `n_molecules × max_attempts` with a cKDTree query per attempt.
- Files: `quickice/structure_generation/solute_inserter.py` lines 863-866 (`for mol_idx in range(n_molecules):` → `for attempt in range(config.max_attempts):`), `quickice/structure_generation/custom_molecule_inserter.py` lines 620-623 (same pattern)
- Cause: Inherent to the random-placement-with-rejection algorithm. Each candidate molecule is retried up to `max_attempts` until a non-overlapping site is found.
- Improvement path: This is expected for the algorithm; the conditional cKDTree rebuild (V-02 fix) already removed the worst O(N²) cost. Further gains would require a spatial candidate proposer (e.g., bias sampling toward low-density regions). Low priority.

## Fragile Areas

**CP-01 duck-typing (accepted design — fragile by intent):**
- Files: `quickice/structure_generation/solute_inserter.py` lines 78-95, `quickice/gui/custom_molecule_panel.py` lines 1038-1040, `quickice/cli/itp_helpers.py` lines 101, 341-347
- Why fragile: Runtime attributes like `.solute_type` and `.custom_molecule_positions` are set via duck-typing rather than declared on the dataclass. Adding a new structure type without setting these attributes produces `AttributeError` only at the call site.
- Safe modification: When adding a new structure type, audit every `getattr(..., default)` / `hasattr(...)` site and ensure the attribute is either set or the default is correct. Do NOT replace with `isinstance` checks (accepted design decision).
- Test coverage: Current structure types are covered; new types are not.

**ITP staging dual path:**
- Files: `tests/e2e_export_helpers.py` `_stage_itp_files()` vs `quickice/cli/itp_helpers.py` `copy_itp_files_for_structure()`
- Why fragile: Two separate ITP staging implementations; API tests use one, CLI uses the other. Divergence could introduce CLI-only bugs.
- Safe modification: Ensure both paths produce identical ITP file sets; add an integration test that validates CLI output matches API output.
- Test coverage: API path is grompp-validated by 27+ test classes in `tests/test_e2e_gmx_validation.py`; CLI path is grompp-validated by 2 tests in `tests/test_cli_pipeline.py::TestPipelineGromppValidation`.

**Guest type detection heuristic:**
- Files: `quickice/output/gromacs_writer.py` `detect_guest_type_from_atoms` / `_get_molecule_atoms`
- Why fragile: Pattern-matching heuristic that identifies CH4, THF, CO2, H2 from atom-name composition. The heuristic in `quickice/structure_generation/molecule_utils.py` line 66 explicitly warns that "any C-starting molecule with an O atom" would be misidentified as THF.
- Safe modification: Currently works because QuickIce only supports CH4 and THF guests. Adding new guest types (e.g., methanol, CO2, acetone) would break the heuristic.
- Test coverage: `detect_guest_type_from_atoms` is exercised only indirectly via grompp validation. No unit tests for the heuristic itself.

**Solute GRO writer fallback when `molecule_index` is empty:**
- Files: `quickice/output/gromacs_writer.py` `write_solute_gro_file` (around lines 3415-3448)
- Why fragile: When `interface.molecule_index` is empty (real GenIce2 data), synthetic molecule entries are created using `atoms_per_ice_mol = 3 if "O" in interface.atom_names[:interface.ice_atom_count] else 4`. This detection-by-atom-name assumes ice atoms use "O" and hydrate atoms use "OW", but the detection only checks the first `ice_atom_count` names. Combined with TD-ADHOC (ad-hoc objects) at the same site.
- Safe modification: Add an explicit `ice_atoms_per_molecule` attribute to `InterfaceStructure` to avoid heuristic detection at export time.
- Test coverage: Covered by `TestSoluteGmxValidation` (API-level structures with `molecule_index` populated). The fallback path (empty `molecule_index`) is exercised only by CLI pipeline tests.

## Scaling Limits

**GRO atom number limit (99,999):**
- Problem: GROMACS `.gro` format wraps atom numbers at 100,000. Large systems (e.g., 256×4=1024 atoms for ice Ih + water + ions) can exceed this.
- Files: `quickice/output/gromacs_writer.py` — all write functions have `% 100000` wrapping and warning logs.
- Current capacity: Works correctly for systems up to ~25,000 molecules (100,000 atoms). Above that, atom numbers wrap but GROMACS still reads the file correctly.
- Limit: Atom numbers wrap but the simulation still works. The warning is informational only.
- Scaling path: GRO format limitation is inherent. For larger systems, users should export to `.pdb` or `.tng` format (not yet implemented).

## Dependencies at Risk

**TD-05: GenIce2 uses `np.random` global state (not thread-safe):**
- Risk: `np.random.seed()`/`np.random.set_state()` manipulate the global numpy RNG, which is not thread-safe. If QuickIce ever runs structure generation in parallel threads, race conditions would corrupt random state.
- Files: `quickice/structure_generation/generator.py` lines 101-157
- Current mitigation: QuickIce is single-threaded. The `try/finally` block restores numpy state after GenIce2 calls.
- Impact: Would break reproducibility if parallel generation is added.
- Migration plan: Use the `numpy.random.Generator` API when GenIce2 supports it. Blocked on an external dependency.

**BUNDLE-02: `collect_all('genice2')` bundles unused lattice/molecule/format plugins:**
- Risk: PyInstaller bundles ALL GenIce2 plugins, including unused lattice types and format plugins. Increases bundle size.
- Files: `quickice-gui.spec` (PyInstaller spec), `quickice/structure_generation/generator.py`
- Impact: Larger distribution binary (~50-100 MB of unused GenIce2 plugins).
- Migration plan: Use `collect_submodules()` with targeted patterns for specific lattices (only `ice1h`, `ice1c`, `ice2`, `ice3`, `ice5`, `ice6`, `ice7`, `ice8`, `sI`, `sII`, `sH`). Requires careful testing because GenIce2's `safe_import()` dynamically loads plugins.

## Missing Critical Features

**No GUI export grompp coverage:**
- Problem: GUI export tests (`tests/test_output/`) mock QFileDialogs but never validate grompp on output.
- Files: `tests/test_output/test_gromacs_export_*.py`
- Blocks: Detecting GUI export bugs that produce GROMACS-invalid files.

**No concentration/occupancy validator test coverage:**
- Problem: `validate_concentration_range` and `validate_occupancy_range` in `quickice/validation/validators.py` lines 150-206 have zero test coverage. `tests/test_validators.py` only tests temperature, pressure, nmolecules, and box_dimension validators.
- Files: `quickice/validation/validators.py` lines 150-206, `tests/test_validators.py`
- Blocks: Catching validation boundary errors in concentration/occupancy inputs (used by CLI `--ion-concentration`, `--solute-concentration`, `--cage-occupancy-small`, `--cage-occupancy-large`).

**No PDB/TNG export for large systems:**
- Problem: Only `.gro` export is implemented, which wraps atom numbers at 99,999.
- Files: `quickice/output/gromacs_writer.py`
- Blocks: Exporting systems larger than ~25,000 molecules without atom-number wraparound.

## Test Coverage Gaps

**CLI grompp validation — incomplete coverage:**
- What's not tested: Hydrate-only CLI grompp, custom-only CLI grompp, solute-only CLI grompp. Only 2 of 6+ CLI workflow combos are tested.
- Files: `tests/test_cli_pipeline.py` lines 694-769 (`TestPipelineGromppValidation` has only `test_slab_interface_grompp` and `test_solute_ion_chain_grompp`)
- Risk: CLI ITP staging (`copy_itp_files_for_structure`) for hydrate, custom, and solute-only workflows is not grompp-validated.
- Priority: High

**Ice phase variety grompp:**
- What's not tested: Ice Ic, Ice III, Ice V, Ice VI, Ice VII, Ice VIII exports validated by grompp.
- Files: `tests/test_e2e_gmx_validation.py` (only Ice Ih tested)
- Risk: Different lattice types may produce GRO formatting issues for other phases.
- Priority: Low (orthorhombic phases work; triclinic phases blocked by TRICLINIC-WRAP)

**`detect_guest_type_from_atoms` heuristic unit tests:**
- What's not tested: The guest-type detection heuristic that differentiates CH4, THF, CO2, H2 from atom-name patterns.
- Files: `quickice/output/gromacs_writer.py` `detect_guest_type_from_atoms` / `_get_molecule_atoms`
- Risk: Heuristic changes or new guest types could silently break guest detection, causing the wrong ITP files to be included.
- Priority: Medium

**`wrap_molecules_into_box` for triclinic cells:**
- What's not tested: PBC molecule wrapping with non-orthorhombic cell vectors.
- Files: `quickice/output/gromacs_writer.py` lines 312+ (`wrap_molecules_into_box`)
- Risk: Triclinic cell wrapping may place atoms in the wrong periodic image.
- Priority: Medium (blocked by TRICLINIC-WRAP)

**Concentration/occupancy validators:**
- What's not tested: `validate_concentration_range` and `validate_occupancy_range` boundary behavior.
- Files: `quickice/validation/validators.py` lines 150-206, `tests/test_validators.py`
- Risk: Off-by-one or sign errors in range validation could accept invalid CLI inputs.
- Priority: Medium

## Positive Signals

- **No open `TODO`/`FIXME`/`HACK` code markers** in `quickice/` source (grep 2026-07-14 found only `"XXX"` as a legitimate residue-name string in `quickice/structure_generation/molecule_validator.py` line 18, not a code annotation).
- **AGENTS.md constraints upheld** (verified 2026-07-14): `quickice/cli/pipeline.py` uses specific exceptions with no bare `except Exception`; comb-rule=2 enforced via `itp_parser.py`; `AVOGADRO` defined once (not duplicated); module constants (`WATER_VOLUME_NM3`, `WATER_ATOMS_PER_MOLECULE`, `TIP4P_ICE_OW_SIGMA/EPSILON`) used in place of hardcoded literals.

---

*Concerns audit: 2026-07-14*
