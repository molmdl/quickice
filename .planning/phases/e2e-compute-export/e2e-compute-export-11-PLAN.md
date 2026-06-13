---
phase: e2e-compute-export
plan: 11
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/test_e2e_gmx_validation.py
autonomous: true
gap_closure: true

must_haves:
  truths:
    - "Each grompp test asserts expected molecule type keys appear in .top [molecules]"
    - "Each grompp test asserts expected residue name keys appear in .gro atom records"
    - "Silent failure (molecule missing from both .gro AND .top) would now be caught"
  artifacts:
    - path: "tests/test_e2e_gmx_validation.py"
      provides: "Molecule-type presence assertions in all 14 grompp test methods"
      contains: "parse_top_molecules"
  key_links:
    - from: "tests/test_e2e_gmx_validation.py"
      to: "tests/e2e_export_helpers.py"
      via: "import parse_top_molecules, parse_gro_residue_names"
      pattern: "from e2e_export_helpers import.*parse_top_molecules"
---

<objective>
Add molecule-type presence assertions to all 14 grompp validation tests.

Purpose: The grompp tests currently only check exit_code == 0, creating a silent-failure
scenario where a writer bug dropping a molecule from BOTH .gro and .top would still pass
grompp (internally consistent but missing data). Adding per-type presence checks closes
this gap by verifying the exported files contain the expected molecule types.

Output: Updated test_e2e_gmx_validation.py with molecule-type assertions in all 14 tests.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@tests/test_e2e_gmx_validation.py
@tests/e2e_export_helpers.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add molecule-type presence assertions to all 14 grompp tests</name>
  <files>tests/test_e2e_gmx_validation.py</files>
  <action>
1. Add `parse_top_molecules` and `parse_gro_residue_names` to the existing import from e2e_export_helpers (line 38-52). Currently only `parse_top_includes` is imported from the parsing group. Add these two on the same import block.

2. For each of the 14 test classes, AFTER the existing `assert exit_code == 0` line, add two assertion blocks:

   a) Parse .top [molecules] and assert expected keys are present:
   ```python
   molecules = parse_top_molecules(top_path)
   expected_top_keys = { ... }  # per table below
   for key in expected_top_keys:
       if key.endswith("*"):  # flexible match variant
           base = key.rstrip("*")
           assert any(k in (base, key) for k in molecules), (
               f"Expected molecule type '{base}' or '{key}' in [molecules] for {CHAIN_LABEL}, "
               f"got: {list(molecules.keys())}"
           )
       else:
           assert key in molecules, (
               f"Expected molecule type '{key}' in [molecules] for {CHAIN_LABEL}, "
               f"got: {list(molecules.keys())}"
           )
   ```

   b) Parse .gro residue names and assert expected keys are present:
   ```python
   residue_names = parse_gro_residue_names(gro_path)
   unique_residues = set(residue_names)
   expected_gro_keys = { ... }  # per table below
   for key in expected_gro_keys:
       if key.endswith("*"):  # flexible match variant
           base = key.rstrip("*")
           assert any(k in (base, key) for k in unique_residues), (
               f"Expected residue '{base}' or '{key}' in .gro for {CHAIN_LABEL}, "
               f"got: {sorted(unique_residues)}"
           )
       else:
           assert key in unique_residues, (
               f"Expected residue '{key}' in .gro for {CHAIN_LABEL}, "
               f"got: {sorted(unique_residues)}"
           )
   ```

3. Expected molecule types per test class:

   | Test Class | CHAIN_LABEL | expected_top_keys | expected_gro_keys |
   |------------|-------------|-------------------|-------------------|
   | TestIceCandidateGmxValidation | "ice" | {"SOL"} | {"SOL"} |
   | TestInterfaceGmxValidation | "interface" | {"SOL"} | {"SOL"} |
   | TestChainF5GmxValidation | "F5" | {"SOL", "NA", "CL"} | {"SOL", "NA", "CL"} |
   | TestChainF6GmxValidation | "F6" | {"SOL", "CH4_L", "NA", "CL"} | {"SOL", "CH4_L", "NA", "CL"} |
   | TestChainF7GmxValidation | "F7" | {"SOL", "THF_L", "NA", "CL"} | {"SOL", "THF_L", "NA", "CL"} |
   | TestChainF1GmxValidation | "F1" | {"SOL", "etoh", "CH4_L", "NA", "CL"} | {"SOL", "MOL", "CH4_L", "NA", "CL"} |
   | TestChainF3GmxValidation | "F3" | {"SOL", "CH4_H*", "CH4_L", "NA", "CL"} | {"SOL", "CH4_H", "CH4_L", "NA", "CL"} |
   | TestChainF4GmxValidation | "F4" | {"SOL", "THF_H*", "etoh", "THF_L", "NA", "CL"} | {"SOL", "THF_H", "MOL", "THF_L", "NA", "CL"} |
   | TestChainF2GmxValidation | "F2" | {"SOL", "etoh", "NA", "CL"} | {"SOL", "MOL", "NA", "CL"} |
   | TestChainF1ThfGmxValidation | "F1+THF" | {"SOL", "etoh", "THF_L", "NA", "CL"} | {"SOL", "MOL", "THF_L", "NA", "CL"} |
   | TestChainF3ThfGmxValidation | "F3+THF" | {"SOL", "CH4_H*", "THF_L", "NA", "CL"} | {"SOL", "CH4_H", "THF_L", "NA", "CL"} |
   | TestChainF4Ch4GmxValidation | "F4+CH4" | {"SOL", "THF_H*", "etoh", "CH4_L", "NA", "CL"} | {"SOL", "THF_H", "MOL", "CH4_L", "NA", "CL"} |
   | TestChainF3SIIGmxValidation | "F3-sII" | {"SOL", "CH4_H*", "CH4_L", "NA", "CL"} | {"SOL", "CH4_H", "CH4_L", "NA", "CL"} |
   | TestChainF4SIIGmxValidation | "F4-sII" | {"SOL", "THF_H*", "etoh", "THF_L", "NA", "CL"} | {"SOL", "THF_H", "MOL", "THF_L", "NA", "CL"} |

   Keys ending with "*" use flexible matching: the test passes if EITHER the base name (without *) OR the full key is present in the parsed data. For example "CH4_H*" means the assertion passes if "CH4_H" OR "CH4" is found — this handles the ambiguity where the registry may use "CH4" (fallback) or "CH4_H" (registered hydrate guest) depending on whether hydrate guest registration happened before export.

   IMPORTANT: The flexible matching logic is: if key ends with "*", strip the "*", then check if ANY of {base_name, full_key_with_asterisk_stripped} is in the parsed dict/set. Do NOT check for the literal string "CH4_H*" in the data. The asterisk is a METADATA marker indicating flexible matching, not a literal character.

4. Each test method already has `gro_path` and `top_path` variables available. Use them directly for parsing.

5. The Ice and Interface tests use different variable names for paths. Check each test carefully:
   - Ice: `gro_path = str(gmx_workspace / "ice.gro")`, `top_path = str(gmx_workspace / "ice.top")`
   - Interface: `gro_path = str(gmx_workspace / "iface.gro")`, `top_path = str(gmx_workspace / "iface.top")`
   - All others follow the same pattern with their chain-specific filenames

6. Do NOT modify any existing assertions, fixture code, or export logic. Only ADD the new assertions after each existing `assert exit_code == 0` line.
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -m pytest tests/test_e2e_gmx_validation.py -v --tb=short 2>&1 | tail -30</verify>
  <done>All 14 grompp test methods have molecule-type presence assertions for both .top [molecules] keys and .gro residue names. Flexible matching (CH4_H/CH4, THF_H/THF) is used for hydrate guest .top names. All 14 tests pass.</done>
</task>

</tasks>

<verification>
1. `python -m pytest tests/test_e2e_gmx_validation.py -v` — all 14 tests pass
2. `grep -c "parse_top_molecules" tests/test_e2e_gmx_validation.py` — returns >= 15 (1 import + 14 uses)
3. `grep -c "parse_gro_residue_names" tests/test_e2e_gmx_validation.py` — returns >= 15 (1 import + 14 uses)
4. `grep -c "expected_top_keys" tests/test_e2e_gmx_validation.py` — returns 14 (one per test)
5. `grep -c "expected_gro_keys" tests/test_e2e_gmx_validation.py` — returns 14 (one per test)
6. `python -m pytest tests/ -v --tb=short 2>&1 | tail -5` — full test suite still passes (130+ tests)
</verification>

<success_criteria>
All 14 grompp validation tests assert molecule-type presence in both .top [molecules] and .gro residue names. Silent failure scenario (molecule missing from both .gro and .top) would now be detected by these assertions. Full test suite passes.
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-compute-export/e2e-compute-export-11-SUMMARY.md`
</output>
