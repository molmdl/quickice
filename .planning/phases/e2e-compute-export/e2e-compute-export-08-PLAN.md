---
phase: e2e-compute-export
plan: "08"
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/test_e2e_gmx_validation.py
autonomous: true

must_haves:
  truths:
    - "F2 chain (Interface→Custom→Ion) passes gmx grompp with 3 ITPs"
    - "F1 w/ THF solute (Interface→Custom→Solute(THF)→Ion) passes gmx grompp with 4 ITPs"
    - "F3 w/ THF solute (Hydrate sI-CH4→Interface→Solute(THF)→Ion) passes gmx grompp with 4 ITPs"
    - "F4 w/ CH4 solute (Hydrate sI-THF→Custom→Solute(CH4)→Ion) passes gmx grompp with 5 ITPs"
  artifacts:
    - path: "tests/test_e2e_gmx_validation.py"
      provides: "4 new grompp validation test classes"
      contains: "TestChainF2GmxValidation"
  key_links:
    - from: "tests/test_e2e_gmx_validation.py"
      to: "e2e_export_helpers.py"
      via: "_insert_custom_molecules, _insert_solutes, _insert_ions, _insert_ions_from_solute"
      pattern: "from e2e_export_helpers import"
    - from: "tests/test_e2e_gmx_validation.py"
      to: "quickice/output/gromacs_writer.py"
      via: "write_custom_molecule_gro_file, write_custom_molecule_top_file"
      pattern: "write_custom_molecule_(gro|top)_file"
---

<objective>
Add 4 missing grompp validation tests covering cross-combinations of guest/solute/custom molecules.

Purpose: The current 8 grompp tests only cover one guest/solute/custom combination per chain.
Missing combinations expose different atomtype interactions in the TOP [atomtypes] section:
- F2 tests custom molecule WITHOUT solute (different writer path: write_custom_molecule_* instead of write_ion_*)
- F1 w/ THF tests THF+etoh atomtype dedup (hc/h1 shared)
- F3 w/ THF tests CH4_H guest + THF_L solute coexistence
- F4 w/ CH4 tests THF_H guest + CH4_L solute + etoh custom (all 3 atomtype sources)

Output: 4 new test classes in test_e2e_gmx_validation.py (4 new tests, total becomes 12)
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/e2e-compute-export/e2e-compute-export-07-SUMMARY.md
@.planning/phases/e2e-compute-export/e2e-compute-export-06-SUMMARY.md
@tests/test_e2e_gmx_validation.py
@tests/e2e_export_helpers.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add F2 and cross-combination grompp validation tests</name>
  <files>tests/test_e2e_gmx_validation.py</files>
  <action>
Add 4 new test classes to the END of tests/test_e2e_gmx_validation.py. Each follows the EXACT same 6-step pattern used by existing test classes. Also add the missing import for write_custom_molecule_gro_file and write_custom_molecule_top_file.

**Step 0: Add imports**

Add `write_custom_molecule_gro_file` and `write_custom_molecule_top_file` to the existing import block from `quickice.output.gromacs_writer`. The current import block (lines 23-30) imports 6 writer functions; add these 2 more.

**Step 1: TestChainF2GmxValidation (Interface→Custom→Ion)**

```python
class TestChainF2GmxValidation:
    """Validate F2 chain (Interface→Custom→Ion) export passes gmx grompp.

    3 ITPs: tip4p-ice.itp, etoh.itp, ion.itp
    Tests Bug 2 fix: [molecules] must use ITP moleculetype name "etoh" (not "MOL")
    WITHOUT solute atomtypes present (tests custom-only dedup).
    Uses write_custom_molecule_gro_file/write_custom_molecule_top_file
    (different writer path from F1 which ends at IonStructure).
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        self.custom = custom

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f2.gro")
        top_path = str(gmx_workspace / "f2.top")
        write_custom_molecule_gro_file(self.custom, gro_path)
        write_custom_molecule_top_file(self.custom, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", 0, 0)  # F2 has no ions, but write_custom_molecule_top_file may not include ion.itp
        # Actually F2 DOES insert ions, so use _insert_ions not _insert_custom_molecules alone
        # CORRECTION: F2 chain is Interface→Custom→Ion, so we need ion output
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f2.gro", top_file="f2.top")
        assert exit_code == 0, f"gmx grompp failed for F2:\n{stderr[-500:]}"
```

IMPORTANT CORRECTION for F2: The F2 chain is Interface→Custom→Ion. This means we need:
1. `_insert_custom_molecules(interface_slab, n_molecules=3)` → CustomMoleculeStructure
2. `_insert_ions(custom, concentration=0.15)` → IonStructure

Then use `write_ion_gro_file(self.ion, ...)` and `write_ion_top_file(self.ion, ...)` (the FINAL output is from the IonStructure, same as F5-F7). The write_custom_molecule_* functions are NOT used for F2 since the chain ends at ions.

HOWEVER — the unique thing about F2 is that no solute is inserted, so the TOP file will have custom molecule atomtypes (oh, ho, hc from etoh.itp) but NO GAFF2 solute atomtypes. This tests Bug 2 fix (moleculetype name "etoh" in [molecules]) and Bug 3 fix (custom-only atomtype dedup) without any GAFF2 atomtype interference.

F2 build chain:
```python
@pytest.fixture(autouse=True)
def _build_chain(self, interface_slab):
    custom = _insert_custom_molecules(interface_slab, n_molecules=3)
    self.ion = _insert_ions(custom, concentration=0.15)
```

F2 export uses ion writers (same as F5):
```python
write_ion_gro_file(self.ion, gro_path)
write_ion_top_file(self.ion, top_path)
write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
```

**Step 2: TestChainF1ThfGmxValidation (Interface→Custom→Solute(THF)→Ion)**

This is F1 but with THF solute instead of CH4. 4 ITPs: tip4p-ice.itp, etoh.itp, thf_liquid.itp, ion.itp.

Build chain:
```python
@pytest.fixture(autouse=True)
def _build_chain(self, interface_slab):
    custom = _insert_custom_molecules(interface_slab, n_molecules=3)
    solute = _insert_solutes(custom, solute_type='THF', concentration=0.3)
    self.ion = _insert_ions_from_solute(solute, concentration=0.15)
```

Key validation: THF solute atomtypes (os, c5, hc, h1) + etoh custom atomtypes (oh, ho, hc) — "hc" shared between THF GAFF2 and etoh, tests dedup (Bug 3 fix).

**Step 3: TestChainF3ThfGmxValidation (Hydrate sI-CH4→Interface→Solute(THF)→Ion)**

This is F3 but with THF solute instead of CH4. 4 ITPs: tip4p-ice.itp, ch4_hydrate.itp, thf_liquid.itp, ion.itp.

Build chain:
```python
@pytest.fixture(autouse=True)
def _build_chain(self):
    hydrate = _hydrate_sI_ch4_candidate()
    interface = _make_slab_interface(hydrate)
    solute = _insert_solutes(interface, solute_type='THF', concentration=0.3)
    self.ion = _insert_ions_from_solute(solute, concentration=0.15)
```

Key validation: CH4_H hydrate guest (c3, hc GAFF2 atomtypes) + THF_L solute (os, c5, hc, h1 GAFF2 atomtypes) — "hc" shared, tests dedup.

**Step 4: TestChainF4Ch4GmxValidation (Hydrate sI-THF→Interface→Custom→Solute(CH4)→Ion)**

This is F4 but with CH4 solute instead of THF. 5 ITPs: tip4p-ice.itp, thf_hydrate.itp, etoh.itp, ch4_liquid.itp, ion.itp.

Build chain:
```python
@pytest.fixture(autouse=True)
def _build_chain(self):
    hydrate = _hydrate_sI_thf_candidate()
    interface = _make_slab_interface(hydrate)
    custom = _insert_custom_molecules(interface, n_molecules=3)
    solute = _insert_solutes(custom, solute_type='CH4', concentration=0.3)
    self.ion = _insert_ions_from_solute(solute, concentration=0.15)
```

Key validation: THF_H hydrate guest (os, c5, hc, h1) + CH4_L solute (c3, hc) + etoh custom (oh, ho, hc) — THREE atomtype sources with "hc" shared across all three. Most complex dedup scenario.

**Important notes:**
- Each test class follows the EXACT same 6-step pattern as existing classes
- F2 uses `_insert_ions()` (NOT `_insert_ions_from_solute()`) since no solute is in the chain
- F1-Thf, F3-Thf, F4-Ch4 use `_insert_ions_from_solute()` (BUG I5 workaround) since they have solutes
- All test classes use `gmx_workspace` fixture
- Add the missing writer imports (`write_custom_molecule_gro_file`, `write_custom_molecule_top_file`) even though F2 ultimately uses ion writers — they're imported for completeness and may be needed if F2 is later modified to test custom molecule writers directly
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -m pytest tests/test_e2e_gmx_validation.py -v --tb=short 2>&1 | tail -40</verify>
  <done>4 new test classes added (TestChainF2GmxValidation, TestChainF1ThfGmxValidation, TestChainF3ThfGmxValidation, TestChainF4Ch4GmxValidation), all 12 grompp validation tests pass with exit code 0</done>
</task>

<task type="auto">
  <name>Task 2: Run full test suite and verify no regressions</name>
  <files>tests/test_e2e_gmx_validation.py</files>
  <action>
Run the complete e2e compute-export test suite to verify:
1. All 12 grompp validation tests pass (8 existing + 4 new)
2. All 228 bridge tests pass (no regressions from import changes)
3. Total test count is 240 (228 bridge + 12 grompp)

Run: python -m pytest tests/test_e2e_gmx_validation.py tests/test_e2e_ice_export.py tests/test_e2e_interface_export.py tests/test_e2e_custom_export.py tests/test_e2e_solute_export.py tests/test_e2e_ion_export.py tests/test_e2e_chain_export_1.py tests/test_e2e_chain_export_2.py tests/test_e2e_cross_chain_invariants.py tests/test_e2e_itp_baseline.py -v --tb=short

Then run pytest on just the grompp validation file for a quick focused check:
python -m pytest tests/test_e2e_gmx_validation.py -v --tb=short
  </action>
  <verify>python -m pytest tests/test_e2e_gmx_validation.py -v --tb=short 2>&1 | grep -E "(PASSED|FAILED|ERROR|test_)"</verify>
  <done>All 12 grompp validation tests pass, 228 bridge tests pass, total 240 tests</done>
</task>

</tasks>

<verification>
1. 4 new test classes exist in test_e2e_gmx_validation.py
2. All 12 grompp validation tests pass with exit code 0
3. F2 (Interface→Custom→Ion) passes — tests moleculetype name fix without solute atomtypes
4. F1-Thf (Interface→Custom→Solute(THF)→Ion) passes — tests THF+etoh dedup
5. F3-Thf (Hydrate sI-CH4→Solute(THF)→Ion) passes — tests CH4_H+THF_L coexistence
6. F4-Ch4 (Hydrate sI-THF→Custom→Solute(CH4)→Ion) passes — tests 3-source atomtype dedup
7. All 228 existing bridge tests still pass
</verification>

<success_criteria>
12 grompp validation tests pass (8 original + 4 new), 228 bridge tests pass, total 240 tests
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-compute-export/e2e-compute-export-08-SUMMARY.md`
</output>
