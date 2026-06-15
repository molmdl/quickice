# Codebase Concerns

**Analysis Date:** 2026-06-15

## Tech Debt

**Duck-typing attribute propagation on IonStructure:**
- Issue: Solute and custom molecule attributes are set on `InterfaceStructure` at runtime via `interface.attr = value` (duck-typing) rather than being part of the dataclass definition. This pattern is used in both GUI (`quickice/gui/main_window.py` lines 866-903) and CLI (`quickice/cli/pipeline.py` lines 553-605). While `IonStructure` has formal fields for these attributes, the intermediate `InterfaceStructure` does not, meaning any code that receives an `InterfaceStructure` after duck-typing must use `getattr()` with defaults to access solute/custom molecule data.
- Files: `quickice/gui/main_window.py`, `quickice/cli/pipeline.py`, `quickice/structure_generation/ion_inserter.py`, `quickice/structure_generation/solute_inserter.py`
- Impact: Fragile — if the attribute names diverge between the duck-typing sites and the `getattr()` consumers, data is silently lost. No compile-time or test-time check catches missing attributes.
- Fix approach: Add optional `solute_type`, `solute_positions`, `solute_atom_names`, `solute_n_molecules`, `solute_molecule_indices`, `solute_registry`, `custom_molecule_count`, `custom_molecule_atom_count`, `custom_molecule_positions`, `custom_molecule_atom_names`, `custom_molecule_moleculetype`, `custom_gro_path`, `custom_itp_path` fields to `InterfaceStructure` dataclass (with defaults of `None`/`0`/`""`). This eliminates all duck-typing on InterfaceStructure. Phase 34.7 already added these fields to `IonStructure` and `SoluteStructure`; the gap is `InterfaceStructure` itself.

**Excessive `getattr()` usage for attribute access:**
- Issue: 100+ `getattr()` calls across `ion_inserter.py`, `solute_inserter.py`, `custom_molecule_inserter.py`, `cli/itp_helpers.py`, and `cli/pipeline.py` used to access attributes that may or may not exist on a given structure type. This is a consequence of the duck-typing pattern above.
- Files: `quickice/structure_generation/ion_inserter.py`, `quickice/structure_generation/solute_inserter.py`, `quickice/structure_generation/custom_molecule_inserter.py`, `quickice/cli/itp_helpers.py`, `quickice/cli/pipeline.py`
- Impact: Readability and maintainability. Each `getattr()` is a silent fallback — if a field name is misspelled or removed, the code silently uses the default instead of raising an `AttributeError`.
- Fix approach: Once `InterfaceStructure` has formal fields for solute/custom attributes, replace `getattr()` calls with direct attribute access. Add `__post_init__` defaults. Optionally add a protocol/ABC for "structure with solutes" and "structure with custom molecules" for type checking.

**Duplicate `_get_hydrate_guest_itp_path()` and `_get_guest_itp_path()` functions:**
- Issue: `_get_hydrate_guest_itp_path()` is defined identically in three places: `quickice/gui/export.py` (line 799), `quickice/gui/hydrate_export.py` (line 44), and `quickice/cli/itp_helpers.py` (line 20). Similarly, `_get_guest_itp_path()` appears in both `quickice/gui/export.py` (line 772) and `quickice/gui/hydrate_export.py` (line 17). The CLI version (`itp_helpers.py`) is the canonical one with case normalization; the GUI versions lack it.
- Files: `quickice/gui/export.py`, `quickice/gui/hydrate_export.py`, `quickice/cli/itp_helpers.py`
- Impact: Bug divergence — if one copy is fixed (e.g., adding case normalization), the others may be missed. GUI copies don't normalize guest_type to lowercase.
- Fix approach: Consolidate into `quickice/cli/itp_helpers.py` (already the most robust) and import from there in GUI modules. Remove duplicate definitions.

**CLIPipeline step chain uses `getattr()` for args that are already defined in parser:**
- Issue: `CLIPipeline._run_source_step()` uses `getattr(self.args, 'hydrate', False)` and `getattr(self.args, 'lattice_type', 'sI')` etc., even though `parser.py` defines these as explicit argparse arguments. The `getattr` pattern is unnecessary for attributes that are guaranteed to exist on the Namespace.
- Files: `quickice/cli/pipeline.py`
- Impact: Code smell — misleading readers into thinking these attributes might not exist. Small performance overhead from `getattr` dispatch.
- Fix approach: Replace `getattr(self.args, 'hydrate', False)` with `self.args.hydrate`, `getattr(self.args, 'lattice_type', 'sI')` with `self.args.lattice_type`, etc. for all attributes defined in `create_parser()`.

## Resolved Concerns

**BUG-05 (HW1 Z-coordinate copy-paste):** ✅ RESOLVED (Phase 34.7-01)
- Was: HW1 atom Z-coordinates incorrectly copied from HW2 in `write_interface_gro_file()`
- Fix: Corrected HW1 Z computation using TIP4P alpha in `quickice/output/gromacs_writer.py`

**MW-01 (Molecule-aware wrapping):** ✅ RESOLVED (Phase 34.7-01)
- Was: Ice GRO writer wrapped atoms individually, splitting molecules across PBC
- Fix: Added `wrap_molecules_into_box()` using `molecule_index` for whole-molecule wrapping in `quickice/output/gromacs_writer.py`

**DEFLT-01 (fudgeLJ/fudgeQQ defaults):** ✅ RESOLVED (Phase 34.7-01)
- Was: Some TOP writers used wrong defaults (fudgeLJ=1.0, fudgeQQ=1.0)
- Fix: All TOP writers now use fudgeLJ=0.5, fudgeQQ=0.8333 in `quickice/output/gromacs_writer.py`

**ATOM-01 (WATER_ATOMS_PER_MOLECULE constant):** ✅ RESOLVED (Phase 34.7-02)
- Was: Hardcoded `// 4` throughout codebase
- Fix: Replaced with `WATER_ATOMS_PER_MOLECULE` constant from `quickice/structure_generation/types.py`

**RNG-01 (Unseeded RNG in custom molecule):** ✅ RESOLVED (Phase 34.7-02)
- Was: `CustomMoleculeInserter` used unseeded `random.Random()` and `Rotation.random()` without seed
- Fix: Added `seed` parameter and `self.rng = random.Random(seed)` plus `Rotation.random(random_state=self.rng.randint(0, 2**31-1))`

**TREE-01 (Conditional KDTree rebuild):** ✅ RESOLVED (Phase 34.7-03)
- Was: Ion inserter rebuilt cKDTree on every iteration (O(N²) copy chain)
- Fix: Added conditional rebuild using `existing_atoms_tree is not None` check

**GUEST-01 (Dead CO2 code + guest_type param):** ✅ RESOLVED (Phase 34.7-08)
- Was: Dead CO2 guest code paths; `count_guest_atoms()` lacked explicit `guest_type` parameter
- Fix: Removed dead CO2 code; added `guest_type` parameter to `count_guest_atoms()` in `quickice/utils/molecule_utils.py`

**PERF-02 (cKDTree boxsize for scorer):** ✅ RESOLVED (Phase 34.8-01)
- Was: Scorer used brute-force O-O distance without PBC awareness
- Fix: Added `cKDTree(boxsize=)` for orthorhombic PBC-correct distance in `quickice/ranking/scorer.py`

**BUG-04 (diversity_score always 1.0):** ✅ RESOLVED (Phase 34.8-03)
- Was: O-O distance histogram was always identical across candidates, producing diversity_score=1.0
- Fix: Replaced with O-O distance fingerprint histogram in `quickice/ranking/scorer.py`

**TEST-09 (moleculetype name matching):** ✅ RESOLVED (Phase 34.8-02)
- Was: TOP `[molecules]` names could mismatch ITP `[moleculetype]` names
- Fix: Added regression tests and `parse_itp_file()` returns correct `molecule_name` in `quickice/structure_generation/itp_parser.py`

## Security Considerations

**np.random global state manipulation:**
- Risk: `IceStructureGenerator._generate_single()` in `quickice/structure_generation/generator.py` (lines 103-157) saves, seeds, and restores `np.random` global state around GenIce2 calls. This is a global side effect — if any other thread or coroutine uses `np.random` concurrently, state corruption could occur.
- Files: `quickice/structure_generation/generator.py`
- Current mitigation: Code comments note "NOT thread-safe" and "QuickIce is designed for sequential execution." The `finally` block ensures state restoration even on exception.
- Recommendations: (1) Document thread-safety constraint in module docstring. (2) Consider migrating to `np.random.Generator` API when GenIce2 supports it. (3) The `hydrate_generator.py` does NOT save/restore global state (relies on GenIce2 internal state) — this could be a subtle divergence if hydrate generation is ever called from a threaded context.

**File path injection in CLI custom molecule paths:**
- Risk: `--custom-gro` and `--custom-itp` accept arbitrary file paths. `CustomMoleculeInserter` reads and parses these files.
- Files: `quickice/cli/parser.py`, `quickice/structure_generation/custom_molecule_inserter.py`
- Current mitigation: `FileNotFoundError` is raised if file doesn't exist. No path traversal check.
- Recommendations: Acceptable for CLI tool — user already has shell access. No action needed.

## Performance Bottlenecks

**SoluteInserter KDTree rebuild per molecule:**
- Problem: `solute_inserter.py` (lines 799-804) rebuilds `cKDTree` from `base_existing_data + all_placed_positions` after each successful molecule placement. This involves `np.vstack()` of growing arrays and full tree rebuild.
- Files: `quickice/structure_generation/solute_inserter.py`
- Cause: O(N²) cumulative vstack cost. For large numbers of solute molecules (>100), this becomes noticeable.
- Improvement path: Use incremental tree update or batch placement. Alternatively, use `scipy.spatial.cKDTree` with `boxsize` for PBC and rebuild only every K molecules. The current `base_existing_data` copy already avoids the prior O(N²) chain pattern (TREE-01 was resolved for ion inserter but solute inserter still uses the rebuild pattern, albeit with a cleaner base-copy strategy).

**main_window.py is 2024 lines:**
- Problem: Single file handles 6 tabs' worth of signal connections, export handlers, and generation orchestration.
- Files: `quickice/gui/main_window.py`
- Cause: Accumulated feature additions across Phases 28-37 without refactoring.
- Improvement path: Extract per-tab controller classes (e.g., `IceTabController`, `HydrateTabController`) that own their signal connections and export logic. `MainWindow` becomes a thin shell that instantiates controllers.

## Fragile Areas

**Hydrate→Interface conversion in CLIPipeline:**
- Files: `quickice/cli/pipeline.py` lines 209-282
- Why fragile: `_run_source_step()` converts `HydrateStructure` to `Candidate` via `to_candidate()`, then the interface step treats it as an ice candidate. The `to_candidate()` method (in `quickice/structure_generation/types.py` lines 658-722) bundles water + guest atoms together into a flat `Candidate`. The interface builder must then separate guests from water framework atoms via atom-name heuristics. If GenIce2 changes its atom naming conventions, the guest detection in `slab.py` (`_detect_guest_atoms()`) would break.
- Safe modification: Changes to `HydrateStructure.to_candidate()` should be tested with both CH4 and THF guests across all interface modes. Changes to `assemble_slab()` guest detection should be validated against `test_hydrate_guest_tiling.py`.
- Test coverage: Good — `test_e2e_ice_interface_export.py` and `test_e2e_cross_chain_invariants.py` cover this path.

**IonStructure attribute propagation from SoluteStructure:**
- Files: `quickice/cli/pipeline.py` lines 568-605, `quickice/gui/main_window.py` lines 864-876
- Why fragile: When `--ion-source solute` is used, the CLI pipeline propagates solute attributes from `SoluteStructure` onto the `InterfaceStructure` by setting attributes directly (`interface.solute_type = source.solute_type`, etc.). The GUI does the same in `_on_insert_ions()`. Both paths must match exactly, and any new attribute added to `SoluteStructure` requires updating both propagation sites.
- Safe modification: Add new attributes to `IonStructure` dataclass first, then update both CLI and GUI propagation code, then add test coverage in `test_e2e_ion_export.py`.
- Test coverage: Good — `test_scancode_bugs_ion.py` and `test_e2e_ion_export.py` cover this.

**Custom molecule 3→4 atom normalization at export:**
- Files: `quickice/output/gromacs_writer.py` lines 1853-2060 (`write_custom_molecule_gro_file`)
- Why fragile: Ice atoms from the candidate may use 3-atom format (O, H, H from GenIce) while water uses 4-atom TIP4P (OW, HW1, HW2, MW). The custom molecule GRO writer must detect and normalize ice atoms from 3→4 by inserting MW virtual sites. If the ice portion uses 4-atom hydrate ice (OW, HW1, HW2, MW), no normalization is needed. The detection logic relies on checking the first ice atom name.
- Safe modification: Any changes to ice atom generation (e.g., switching from TIP3P to TIP4P in `IceStructureGenerator`) must be validated against the custom molecule GRO writer.
- Test coverage: Good — `test_gromacs_export_custom.py` covers this.

## Scaling Limits

**cKDTree memory for large systems:**
- Current capacity: Systems up to ~50,000 atoms work well. `cKDTree` construction is O(N log N) and uses ~24 bytes per atom.
- Limit: For systems >200,000 atoms (large hydrate supercells or thick slabs), multiple `cKDTree` instances in ion/solute inserters may consume significant memory.
- Scaling path: Consider using `scipy.spatial.cKDTree` with `boxsize` parameter (already done in scorer) and batch-based overlap checking for very large systems.

**GenIce2 generation time:**
- Current capacity: ~1-5 seconds for 256-768 molecules per candidate.
- Limit: For very large systems (>10,000 molecules), GenIce2 generation time grows linearly with supercell size. 10 candidates for 4096 molecules takes ~30 seconds.
- Scaling path: GenIce2 is inherently sequential. Parallel generation of candidates with different seeds could reduce wall-clock time for multi-candidate workflows.

## Dependencies at Risk

**GenIce2 (genice2):**
- Risk: GenIce2 is a research-grade package with infrequent updates. It uses the deprecated `np.random` global state API internally rather than `np.random.Generator`. Its API is not formally versioned (uses date-based versions like `2.2.13.1`).
- Impact: If GenIce2 breaks on a future NumPy version that removes global `np.random`, all ice and hydrate generation fails.
- Migration plan: Pin NumPy version in `environment.yml`. Monitor GenIce2 releases for `np.random.Generator` migration. The save/restore pattern in `quickice/structure_generation/generator.py` provides a partial workaround.

**PySide6:**
- Risk: PySide6 major version upgrades (6.x→7.x) may break Qt API compatibility. PySide6 is already at 6.10.2.
- Impact: GUI would fail to launch. CLI mode is unaffected (lazy import in `entry.py`).
- Migration plan: `quickice/entry.py` already handles PySide6 unavailability gracefully with `_is_pyside6_available()` check, routing to CLI mode when absent.

## Missing Critical Features

**No CLI `--export` flag to trigger GROMACS export automatically:**
- Problem: The CLI parser defines `--gromacs` / `-g` flag but `CLIPipeline._run_export_step()` always exports GROMACS files — the `--gromacs` flag is only used in the ice-only backward-compat path in `quickice/main.py`. For the pipeline path, export always happens.
- Files: `quickice/cli/parser.py`, `quickice/cli/pipeline.py`
- Blocks: Users who want to run the pipeline without writing files (e.g., just to validate parameters or compute structure in memory).

**No progress reporting for long-running CLI steps:**
- Problem: `report_progress()` prints to stderr, but there's no ETA or percentage completion for multi-step pipelines.
- Files: `quickice/cli/pipeline.py`
- Blocks: Users can't estimate remaining time for large systems.

## Test Coverage Gaps

**CLI pipeline e2e tests don't validate GROMACS file content:**
- What's not tested: `test_cli_pipeline.py` and `test_cli_integration.py` verify exit codes and stderr output but don't parse the exported `.gro`/`.top` files to validate atom counts, molecule ordering, or ITP inclusion.
- Files: `quickice/tests/test_cli_pipeline.py`, `quickice/tests/test_cli_integration.py`
- Risk: A writer bug (like BUG-05 HW1 Z-coordinate) could slip through CLI tests because they don't inspect file contents.
- Priority: Medium — API-level tests in `test_output/` directory cover the writer functions directly, but the CLI integration path is untested for file content.

**No test for np.random state corruption:**
- What's not tested: Whether `IceStructureGenerator._generate_single()` correctly restores `np.random` state after exceptions.
- Files: `quickice/structure_generation/generator.py`
- Risk: If a GenIce2 exception path skips the `finally` block (Python doesn't allow this, but a `SystemExit` or `os._exit()` could), global state would be corrupted.
- Priority: Low — Python's `try/finally` guarantees execution, and the code is well-structured.

**Duck-typing propagation not tested for attribute absence:**
- What's not tested: What happens when an `InterfaceStructure` that has NOT been duck-typed (no solute/custom attributes set) is passed to `IonInserter.replace_water_with_ions()`.
- Files: `quickice/structure_generation/ion_inserter.py`, `quickice/gui/main_window.py`
- Risk: The `getattr()` fallbacks return defaults (0, None, ""), which produces an `IonStructure` with zero solutes and zero custom molecules — this is actually the correct behavior for the "interface source" path, but it's not explicitly tested.
- Priority: Low — behavior is correct but implicit.

## Deferred Items (Unchanged)

**Deferred UAT testing (v3.0 phases 17-21):**
- See `.planning/DEFERRED-UAT.md` — all Phase 17-21 GUI tests are pending execution.
- No change from previous analysis.

**Screenshots and release notes (Phase 35-06):**
- Deferred per STATE.md line 106.
- No change from previous analysis.

---

*Concerns audit: 2026-06-15*
