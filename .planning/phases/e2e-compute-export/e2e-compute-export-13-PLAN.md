---
phase: e2e-compute-export
plan: 13
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/test_e2e_gmx_param_validation.py
autonomous: true

must_haves:
  truths:
    - "Each of 27 untested chain combinations passes gmx grompp (exit code 0)"
    - "Each combination's .top [molecules] section contains expected molecule types"
    - "Each combination's .gro file contains expected residue names"
    - "All 18 existing grompp tests still pass (no regressions)"
  artifacts:
    - path: "tests/test_e2e_gmx_param_validation.py"
      provides: "Parameterized grompp validation tests for 27 chain combinations"
      contains: "CHAIN_COMBINATIONS"
      min_lines: 80
  key_links:
    - from: "tests/test_e2e_gmx_param_validation.py"
      to: "tests/e2e_export_helpers.py"
      via: "import chain builders, staging, grompp helpers"
      pattern: "from e2e_export_helpers import"
    - from: "tests/test_e2e_gmx_param_validation.py"
      to: "quickice/output/gromacs_writer.py"
      via: "import GRO/TOP writer functions"
      pattern: "write_.*_gro_file|write_.*_top_file"
---

<objective>
Add parameterized grompp validation tests covering 27 untested chain combinations.

Purpose: The existing 18 class-based grompp tests (in test_e2e_gmx_validation.py) exercise the deepest chains (F1-F7 variants) which test all writer code paths, but 27 combinations of hydrate type × solute type × chain depth remain untested. A single parameterized test class can cover all 27 systematically in ~150 lines vs ~800 lines for 27 individual classes.

Output: New test file tests/test_e2e_gmx_param_validation.py with 27 parameterized test cases, each building a real GenIce2 chain, exporting GRO/TOP/ITP files, running gmx grompp, and asserting molecule-type presence.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/e2e-compute-export/e2e-compute-export-12-SUMMARY.md
@tests/test_e2e_gmx_validation.py
@tests/e2e_export_helpers.py
@tests/conftest.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create parameterized grompp validation test file</name>
  <files>tests/test_e2e_gmx_param_validation.py</files>
  <action>
Create `tests/test_e2e_gmx_param_validation.py` with the following structure:

1. **Module docstring**: Explain this file complements test_e2e_gmx_validation.py (18 class-based tests) with 27 parameterized test cases for all untested hydrate→interface chain combinations.

2. **Imports**: Same pattern as test_e2e_gmx_validation.py:
   - `sys.path.insert(0, str(Path(__file__).parent))` for e2e_export_helpers import
   - `from tests.conftest import gmx_skipif`
   - Import ALL writer functions needed: `write_interface_gro_file`, `write_interface_top_file`, `write_ion_gro_file`, `write_ion_top_file`, `write_custom_molecule_gro_file`, `write_custom_molecule_top_file`, `write_solute_gro_file`, `write_solute_top_file`
   - Import `write_ion_itp` from quickice.structure_generation.gromacs_ion_export
   - Import from e2e_export_helpers: `parse_top_molecules`, `parse_gro_residue_names`, `_insert_custom_molecules`, `_insert_solutes`, `_insert_ions`, `_insert_ions_from_solute`, `_make_slab_interface`, `_hydrate_sI_ch4_candidate`, `_hydrate_sI_thf_candidate`, `_hydrate_sII_ch4_candidate`, `_hydrate_sII_thf_candidate`, `_stage_itp_files`, `assert_itp_completeness`, `run_gmx_grompp`, `MDP_PATH`

3. **ChainParams NamedTuple** with fields: `id: str`, `hydrate_type: str`, `has_custom: bool`, `solute_type: str | None`, `has_ion: bool`

4. **_HYDRATE_BUILDERS dict** mapping hydrate_type strings to the 4 builder functions: `"sI-CH4" → _hydrate_sI_ch4_candidate`, etc.

5. **_HYDRATE_GUEST dict** mapping hydrate_type to (top_name, gro_name) tuples: `{"sI-CH4": ("CH4_H*", "CH4_H"), "sI-THF": ("THF_H*", "THF_H"), "sII-CH4": ("CH4_H*", "CH4_H"), "sII-THF": ("THF_H*", "THF_H")}`

6. **CHAIN_COMBINATIONS list** of 27 ChainParams instances. Use these exact IDs and parameters:
   ```
   ("sI-CH4_custom_ion",      "sI-CH4",  True,  None,  True)
   ("sI-CH4_custom_thf",      "sI-CH4",  True,  "THF", False)
   ("sI-CH4_custom_thf_ion",  "sI-CH4",  True,  "THF", True)
   ("sI-CH4_ion",             "sI-CH4",  False, None,  True)
   ("sI-THF_custom_ion",     "sI-THF",  True,  None,  True)
   ("sI-THF_ion",             "sI-THF",  False, None,  True)
   ("sI-THF_ch4",            "sI-THF",  False, "CH4", False)
   ("sI-THF_ch4_ion",         "sI-THF",  False, "CH4", True)
   ("sI-THF_thf",            "sI-THF",  False, "THF", False)
   ("sI-THF_thf_ion",         "sI-THF",  False, "THF", True)
   ("sII-CH4_custom",         "sII-CH4", True,  None,  False)
   ("sII-CH4_custom_ion",     "sII-CH4", True,  None,  True)
   ("sII-CH4_custom_ch4",     "sII-CH4", True,  "CH4", False)
   ("sII-CH4_custom_ch4_ion", "sII-CH4", True,  "CH4", True)
   ("sII-CH4_custom_thf",     "sII-CH4", True,  "THF", False)
   ("sII-CH4_custom_thf_ion", "sII-CH4", True,  "THF", True)
   ("sII-CH4_ion",            "sII-CH4", False, None,  True)
   ("sII-CH4_thf",            "sII-CH4", False, "THF", False)
   ("sII-CH4_thf_ion",        "sII-CH4", False, "THF", True)
   ("sII-THF_custom_ion",     "sII-THF", True,  None,  True)
   ("sII-THF_custom_ch4",     "sII-THF", True,  "CH4", False)
   ("sII-THF_custom_ch4_ion", "sII-THF", True,  "CH4", True)
   ("sII-THF_ion",            "sII-THF", False, None,  True)
   ("sII-THF_ch4",            "sII-THF", False, "CH4", False)
   ("sII-THF_ch4_ion",        "sII-THF", False, "CH4", True)
   ("sII-THF_thf",            "sII-THF", False, "THF", False)
   ("sII-THF_thf_ion",        "sII-THF", False, "THF", True)
   ```

7. **_build_param_chain(params: ChainParams) → (final_structure, writer_type)**:
   - Generate hydrate candidate via `_HYDRATE_BUILDERS[params.hydrate_type]()`
   - Create interface via `_make_slab_interface(hydrate)`
   - If `has_custom`: `custom = _insert_custom_molecules(interface, n_molecules=3)`, else `custom = None`
   - If `solute_type is not None`: `source = custom if custom is not None else interface`, then `solute = _insert_solutes(source, solute_type=params.solute_type, concentration=0.3)`, else `solute = None`
   - If `has_ion`:
     - If `solute is not None`: `ion = _insert_ions_from_solute(solute, concentration=0.15)`
     - Elif `custom is not None`: `ion = _insert_ions(custom, concentration=0.15)`
     - Else: `ion = _insert_ions(interface, concentration=0.15)`
   - Else: `ion = None`
   - Return `(ion, "ion")` or `(solute, "solute")` or `(custom, "custom")` or `(interface, "interface")` based on which is the deepest non-None structure

8. **_expected_top_keys(params: ChainParams) → set[str]**:
   - Always include `"SOL"`
   - Add hydrate guest from `_HYDRATE_GUEST[params.hydrate_type][0]` (e.g., `"CH4_H*"`)
   - If `has_custom`: add `"etoh"` (ITP moleculetype name for custom molecule)
   - If `solute_type == "CH4"`: add `"CH4_L"`
   - If `solute_type == "THF"`: add `"THF_L"`
   - If `has_ion`: add `"NA"` and `"CL"`

9. **_expected_gro_residues(params: ChainParams) → set[str]**:
   - Always include `"SOL"`
   - Add hydrate guest from `_HYDRATE_GUEST[params.hydrate_type][1]` (e.g., `"CH4_H"`)
   - If `has_custom`: add `"MOL"` (GRO residue name for custom molecule)
   - If `solute_type == "CH4"`: add `"CH4_L"`
   - If `solute_type == "THF"`: add `"THF_L"`
   - If `has_ion`: add `"NA"` and `"CL"`

10. **_WRITERS dict** mapping writer_type strings to (gro_writer, top_writer) tuples:
    - `"interface"`: `(write_interface_gro_file, write_interface_top_file)`
    - `"custom"`: `(write_custom_molecule_gro_file, write_custom_molecule_top_file)`
    - `"solute"`: `(write_solute_gro_file, write_solute_top_file)`
    - `"ion"`: `(write_ion_gro_file, write_ion_top_file)`

11. **gmx_workspace fixture**: Same as in test_e2e_gmx_validation.py — persistent workspace under `tmp/e2e-gmx-validation/` with subdirectory named after the test node.

12. **TestParametricGmxValidation class** with `@gmx_skipif` decorator:
    - Single test method `test_gmx_grompp_succeeds(self, params, gmx_workspace)` decorated with `@pytest.mark.parametrize("params", CHAIN_COMBINATIONS, ids=lambda p: p.id)`
    - Build chain via `final, writer_type = _build_param_chain(params)`
    - Write GRO/TOP: `gro_writer, top_writer = _WRITERS[writer_type]`, then write to `f"{params.id}.gro"` and `f"{params.id}.top"`
    - If `writer_type == "ion"`: generate `ion.itp` via `write_ion_itp(gmx_workspace / "ion.itp", final.na_count, final.cl_count)`
    - Copy MDP: `shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")`
    - Stage ITPs: `_stage_itp_files(top_path, gmx_workspace)` then `assert_itp_completeness(top_path, gmx_workspace)`
    - Run grompp: `run_gmx_grompp(gmx_workspace, gro_file=f"{params.id}.gro", top_file=f"{params.id}.top")`
    - Assert exit_code == 0 with descriptive error message including params.id
    - Assert TOP [molecules] keys: use `_expected_top_keys(params)` with asterisk matching (same pattern as existing grompp tests — `key.endswith("*")` → match base or full key)
    - Assert GRO residues: use `_expected_gro_residues(params)` with same asterisk matching

**IMPORTANT design decisions:**
- This file is SEPARATE from test_e2e_gmx_validation.py — do NOT modify the existing file
- The existing 18 class-based tests serve as known-good regression tests and must not be changed
- Use pytest parameterization (NOT 27 separate classes) for maintainability
- All 27 combinations build chains starting from a hydrate candidate (all 27 are hydrate→interface→... variants)
- The `interface_slab` conftest fixture is NOT used — each test generates its own hydrate→interface inline (matching the F3/F4 pattern)
  </action>
  <verify>python -m pytest tests/test_e2e_gmx_param_validation.py --collect-only -q 2>&1 | tail -5</verify>
  <done>test_e2e_gmx_param_validation.py exists with 27 collected parameterized test cases, file passes syntax check</done>
</task>

<task type="auto">
  <name>Task 2: Run parameterized tests and verify all pass</name>
  <files>tests/test_e2e_gmx_param_validation.py</files>
  <action>
Run the new parameterized grompp validation tests and verify all 27 pass:

1. Run `python -m pytest tests/test_e2e_gmx_param_validation.py -v --timeout=300 2>&1 | tail -40` to execute all 27 parameterized test cases

2. If any tests fail, debug and fix:
   - Common issue: wrong expected molecule type names (check actual .top output in tmp/e2e-gmx-validation/ workspace)
   - Common issue: missing ITP file for non-ion chains (solute/custom writer may not include hydrate ITP — this IS a real bug if found, fix the writer)
   - Common issue: writer not handling hydrate guest attributes for custom/solute chains (check guest_atom_count propagation)
   - For any failing test: inspect the workspace files under `tmp/e2e-gmx-validation/` named after the test ID

3. After all 27 parameterized tests pass, run the existing grompp tests to verify no regressions:
   `python -m pytest tests/test_e2e_gmx_validation.py -v --timeout=300 2>&1 | tail -30`

4. Count total parameterized tests passing: should be exactly 27

5. If any writer bugs are discovered (e.g., write_solute_top_file missing hydrate ITP include for chains with guests), fix the writer function in quickice/output/gromacs_writer.py and add a comment explaining the fix
  </action>
  <verify>python -m pytest tests/test_e2e_gmx_param_validation.py -v --timeout=300 2>&1 | grep -E "(PASSED|FAILED|ERROR)" | wc -l && python -m pytest tests/test_e2e_gmx_param_validation.py -v --timeout=300 2>&1 | grep -c "PASSED"</verify>
  <done>All 27 parameterized grompp tests pass with exit_code==0, and all 18 existing grompp tests still pass</done>
</task>

</tasks>

<verification>
1. `python -m pytest tests/test_e2e_gmx_param_validation.py -v --timeout=300` — all 27 tests PASSED
2. `python -m pytest tests/test_e2e_gmx_validation.py -v --timeout=300` — all 18 tests PASSED (no regressions)
3. `grep -c "PASSED" <<< "$(python -m pytest tests/test_e2e_gmx_param_validation.py -v --timeout=300 2>&1)"` — count is 27
4. test_e2e_gmx_param_validation.py contains "CHAIN_COMBINATIONS" and "TestParametricGmxValidation"
5. No modifications to test_e2e_gmx_validation.py (existing 18 tests untouched)
</verification>

<success_criteria>
- 27 parameterized grompp validation test cases all pass gmx grompp (exit code 0)
- Each test case asserts correct molecule types in .top [molecules] and residue names in .gro
- All 18 existing grompp tests continue to pass (no regressions)
- test_e2e_gmx_param_validation.py is a separate file from test_e2e_gmx_validation.py
- Coverage: 27/27 previously untested chain combinations now validated
- Total grompp coverage: 18 + 27 = 45 test cases across 55 possible combinations (the remaining 8 are the Interface-only type combinations already covered by existing non-hydrate tests)
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-compute-export/e2e-compute-export-13-SUMMARY.md`
</output>
