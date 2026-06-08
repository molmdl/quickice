---
phase: e2e-compute-export
plan: "09"
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/e2e_export_helpers.py
  - tests/test_e2e_gmx_validation.py
autonomous: true

must_haves:
  truths:
    - "sII CH4 hydrate chain passes gmx grompp"
    - "sII THF hydrate chain passes gmx grompp"
    - "sII hydrate helper functions exist in e2e_export_helpers.py"
  artifacts:
    - path: "tests/e2e_export_helpers.py"
      provides: "_hydrate_sII_ch4_candidate() and _hydrate_sII_thf_candidate() helper functions"
      contains: "_hydrate_sII_"
    - path: "tests/test_e2e_gmx_validation.py"
      provides: "2 sII grompp validation test classes"
      contains: "TestChainF3SII"
  key_links:
    - from: "tests/test_e2e_gmx_validation.py"
      to: "e2e_export_helpers.py"
      via: "_hydrate_sII_ch4_candidate, _hydrate_sII_thf_candidate"
      pattern: "_hydrate_sII_"
    - from: "tests/e2e_export_helpers.py"
      to: "quickice/structure_generation/hydrate_generator.py"
      via: "HydrateStructureGenerator with sII config"
      pattern: "lattice_type.*sII"
---

<objective>
Add sII hydrate grompp validation tests to cover the missing hydrate lattice type.

Purpose: Currently only sI hydrate grompp tests exist. The sII hydrate candidate
fixtures exist in conftest.py (hydrate_sII_ch4_candidate, hydrate_sII_thf_structure)
but no grompp test uses them. sII hydrates have different guest occupancy and
cage structures (large 5^12 6^4 + small 5^12), producing different atom counts
and ITP files. Testing sII validates that the export pipeline handles the
second hydrate lattice type correctly.

Output: 2 sII helper functions in e2e_export_helpers.py + 2 new grompp test classes
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
@tests/e2e_export_helpers.py
@tests/test_e2e_gmx_validation.py
@tests/conftest.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add sII hydrate helpers and grompp validation tests</name>
  <files>tests/e2e_export_helpers.py, tests/test_e2e_gmx_validation.py</files>
  <action>
**Part A: Add sII hydrate helpers to tests/e2e_export_helpers.py**

Add two helper functions after the existing `_hydrate_sI_thf_candidate()` (line ~324). Follow the EXACT same pattern as the sI helpers:

```python
def _hydrate_sII_ch4_candidate():
    """Generate hydrate sII+CH4 candidate inline (for chains needing different config)."""
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sII",
        guest_type="ch4",
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    structure = gen.generate(config)
    return structure.to_candidate()


def _hydrate_sII_thf_candidate():
    """Generate hydrate sII+THF candidate inline."""
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sII",
        guest_type="thf",
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    structure = gen.generate(config)
    return structure.to_candidate()
```

These mirror the existing `_hydrate_sI_ch4_candidate()` and `_hydrate_sI_thf_candidate()` but use `lattice_type="sII"`.

**Part B: Add sII grompp validation tests to tests/test_e2e_gmx_validation.py**

Add 2 new test classes at the END of the file. Follow the exact same 6-step pattern.

**1. Update imports** — Add `_hydrate_sII_ch4_candidate` and `_hydrate_sII_thf_candidate` to the import from `e2e_export_helpers`.

**2. TestChainF3SIIGmxValidation (Hydrate sII-CH4→Interface→Solute(CH4)→Ion)**

4 ITPs: tip4p-ice.itp, ch4_hydrate.itp, ch4_liquid.itp, ion.itp

```python
class TestChainF3SIIGmxValidation:
    """Validate F3-sII chain (Hydrate sII-CH4→Interface→Solute→Ion) passes gmx grompp.

    4 ITPs: tip4p-ice.itp, ch4_hydrate.itp, ch4_liquid.itp, ion.itp
    Tests sII hydrate guest export + grompp validation.
    sII has different cage structure (5^12 6^4 large + 5^12 small) from sI.
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self):
        hydrate = _hydrate_sII_ch4_candidate()
        interface = _make_slab_interface(hydrate)
        solute = _insert_solutes(interface, solute_type='CH4', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f3_sII.gro")
        top_path = str(gmx_workspace / "f3_sII.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f3_sII.gro", top_file="f3_sII.top")
        assert exit_code == 0, f"gmx grompp failed for F3-sII:\n{stderr[-500:]}"
```

**3. TestChainF4SIIGmxValidation (Hydrate sII-THF→Interface→Custom→Solute(THF)→Ion)**

5 ITPs: tip4p-ice.itp, thf_hydrate.itp, etoh.itp, thf_liquid.itp, ion.itp

```python
class TestChainF4SIIGmxValidation:
    """Validate F4-sII chain (Hydrate sII-THF→Interface→Custom→Solute→Ion) passes gmx grompp.

    5 ITPs: tip4p-ice.itp, thf_hydrate.itp, etoh.itp, thf_liquid.itp, ion.itp
    Tests sII hydrate with full custom+solute+ion chain.
    Most complex sII chain — tests all 3 bug fixes with sII lattice.
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self):
        hydrate = _hydrate_sII_thf_candidate()
        interface = _make_slab_interface(hydrate)
        custom = _insert_custom_molecules(interface, n_molecules=3)
        solute = _insert_solutes(custom, solute_type='THF', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f4_sII.gro")
        top_path = str(gmx_workspace / "f4_sII.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f4_sII.gro", top_file="f4_sII.top")
        assert exit_code == 0, f"gmx grompp failed for F4-sII:\n{stderr[-500:]}"
```

**Important notes:**
- sII uses the SAME ITP filenames as sI (ch4_hydrate.itp, thf_hydrate.itp) — the hydrate ITP files are the same for both lattice types
- The difference is in the CANDIDATE structure (sII has different water/guest atom counts)
- Use `_insert_ions_from_solute()` for both since both chains have solutes
- File names use `_sII` suffix to avoid workspace collision with sI tests
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -m pytest tests/test_e2e_gmx_validation.py -v --tb=short 2>&1 | tail -40</verify>
  <done>2 sII helpers added to e2e_export_helpers.py, 2 sII grompp test classes added, all 14 grompp tests pass</done>
</task>

<task type="auto">
  <name>Task 2: Run full test suite and verify no regressions</name>
  <files>tests/test_e2e_gmx_validation.py</files>
  <action>
Run the complete grompp validation test suite and bridge test suite:

1. Run grompp validation tests:
   python -m pytest tests/test_e2e_gmx_validation.py -v --tb=short

2. Run all e2e compute-export bridge tests to verify no regressions:
   python -m pytest tests/test_e2e_ice_export.py tests/test_e2e_interface_export.py tests/test_e2e_custom_export.py tests/test_e2e_solute_export.py tests/test_e2e_ion_export.py tests/test_e2e_chain_export_1.py tests/test_e2e_chain_export_2.py tests/test_e2e_cross_chain_invariants.py tests/test_e2e_itp_baseline.py -v --tb=short

Verify:
- All 14 grompp validation tests pass (8 original + 4 from Plan 08 + 2 sII)
- All 228 bridge tests pass
- Total: 242 tests
  </action>
  <verify>python -m pytest tests/test_e2e_gmx_validation.py -v --tb=short 2>&1 | grep -E "(PASSED|FAILED|ERROR)"</verify>
  <done>All 14 grompp validation tests pass, 228 bridge tests pass, total 242 tests</done>
</task>

</tasks>

<verification>
1. _hydrate_sII_ch4_candidate() exists in e2e_export_helpers.py
2. _hydrate_sII_thf_candidate() exists in e2e_export_helpers.py
3. TestChainF3SIIGmxValidation exists and passes gmx grompp
4. TestChainF4SIIGmxValidation exists and passes gmx grompp
5. All 14 grompp validation tests pass
6. All 228 bridge tests pass (no regressions)
</verification>

<success_criteria>
14 grompp validation tests pass (8 original + 4 cross-combinations + 2 sII), 228 bridge tests pass, total 242 tests
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-compute-export/e2e-compute-export-09-SUMMARY.md`
</output>
