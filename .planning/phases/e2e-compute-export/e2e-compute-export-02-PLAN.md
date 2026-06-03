---
phase: e2e-compute-export
plan: 02
type: execute
wave: 2
depends_on:
  - e2e-compute-export-01
files_modified:
  - tests/test_e2e_compute_export_chain.py
autonomous: true

must_haves:
  truths:
    - "Full chain F1 (Ice→Interface→Custom→Solute→Ion) export produces valid .gro with SOL→guests→custom→solutes→ions ordering"
    - "Full chain F3 (Hydrate→Interface→Solute→Ion) export produces .gro with CH4_H before CH4_L before NA before CL"
    - ".top [molecules] section lists all molecule types with correct counts for full chain exports"
    - "ITP files referenced in .top #include directives exist in quickice/data/ and contain [moleculetype]"
    - "Atom count in .gro matches structure positions (no atoms lost across export)"
  artifacts:
    - path: "tests/test_e2e_compute_export_chain.py"
      provides: "Full chain compute→export bridge e2e tests (~12 tests)"
      contains: "class TestFullChainF1Export"
  key_links:
    - from: "tests/test_e2e_compute_export_chain.py"
      to: "tests/conftest.py"
      via: "import of parse_gro_residue_names and parse_top_molecules helpers + fixture consumption"
      pattern: "from conftest import.*parse_gro"
    - from: "tests/test_e2e_compute_export_chain.py"
      to: "quickice/output/gromacs_writer.py"
      via: "write_ion_gro_file and write_ion_top_file for full chain output"
      pattern: "write_ion_(gro|top)_file"
    - from: "tests/test_e2e_compute_export_chain.py"
      to: "tests/test_e2e_workflow_chains.py"
      via: "reuse of chain-building helper pattern (_insert_custom_molecules, _solute_to_ion_source, etc.)"
      pattern: "_insert_custom_molecules|_solute_to_ion_source"
---

<objective>
Create end-to-end tests that take REAL computation pipeline chain outputs (Ice→Interface→Custom→Solute→Ion) and export them via GROMACS writer functions, validating atom ordering, topology format, ITP bundling, and atom count conservation for multi-molecule systems.

Purpose: This is THE critical bridge test — the gap not covered by e2e-api-workflow (stops before export) or e2e-export-test (uses synthetic fixtures). Validates that real GenIce2 structures flow correctly through the entire export pipeline.

Output: test_e2e_compute_export_chain.py with ~12 passing tests covering F1-F7 chains
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/e2e-compute-export/e2e-compute-export-01-SUMMARY.md
@tests/conftest.py
@tests/test_e2e_workflow_chains.py
@quickice/output/gromacs_writer.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create full chain GRO/TOP export validation tests</name>
  <files>tests/test_e2e_compute_export_chain.py</files>
  <action>
Create `tests/test_e2e_compute_export_chain.py` with end-to-end chain export tests. These tests build real structures through the full pipeline (Ice→Interface→Custom→Solute→Ion) and then export the FINAL IonStructure via `write_ion_gro_file` and `write_ion_top_file`, validating the complete output.

Copy these helper functions from `tests/test_e2e_workflow_chains.py` (lines 46-111) as module-level helpers at the top of the new file:
- `_liquid_volume_nm3(structure)` — estimate liquid volume
- `_insert_custom_molecules(interface, n_molecules=3)` — place ethanol molecules
- `_insert_solutes(source_structure, solute_type='CH4', concentration=0.3, seed=42)` — insert solutes
- `_solute_to_ion_source(solute)` — BUG I5 workaround: attach solute attrs to interface_structure
- `_insert_ions(source_structure, concentration=0.15, seed=42)` — insert ions
- `_insert_ions_from_solute(solute, concentration=0.15, seed=42)` — insert ions via workaround
- `_hydrate_sI_ch4_candidate()` — generate hydrate candidate inline
- `_hydrate_sI_thf_candidate()` — generate THF hydrate candidate inline
- `_make_slab_interface(candidate, ...)` — generate slab interface from candidate

Also copy: `DATA_DIR`, `ETOH_GRO`, `ETOH_ITP` constants.

Import parsing helpers: `from conftest import parse_gro_residue_names, parse_gro_atom_count, parse_top_molecules, parse_top_includes`

Import writer functions: `from quickice.output.gromacs_writer import write_ion_gro_file, write_ion_top_file`

**Class TestFullChainF1Export:**
- `test_f1_gro_molecule_ordering(self, interface_slab, tmp_path)`: Build F1 chain (interface_slab → custom(3) → solute(CH4,0.3) → ion(0.15)). Call `write_ion_gro_file(ion, str(tmp_path / "f1.gro"))`. Parse residue names. Find SOL, custom (first non-SOL non-NA/CL residue), NA, CL indices. Assert max(SOL indices) < min(custom indices). Find CH4_L indices (solute residues). Assert max(custom indices) < min(CH4_L indices). Assert max(CH4_L indices) < min(NA indices). Assert max(NA indices) < min(CL indices).
- `test_f1_top_molecules_section(self, interface_slab, tmp_path)`: Call `write_ion_top_file(ion, str(tmp_path / "f1.top"))`. Parse `parse_top_molecules`. Assert "SOL" in molecules with count == ice+water. Assert "NA" count == ion.na_count. Assert "CL" count == ion.cl_count. Assert custom moleculetype name in molecules with count == 3. Assert "CH4_L" (or solute moleculetype name) in molecules with count matching solute count.
- `test_f1_atom_count_conservation(self, interface_slab, tmp_path)`: After building F1 chain and writing .gro, parse `parse_gro_atom_count(gro_path)`. Count total output atoms: ice_nmolecules*4 + water_nmolecules*4 + custom_molecule_atom_count + solute atom count + na_count + cl_count. Assert .gro atom count == calculated total. This verifies no atoms are lost in the export.

**Class TestShortChainF2Export:**
- `test_f2_gro_molecule_ordering(self, interface_slab, tmp_path)`: Build F2 chain (interface_slab → custom(3) → ion(0.15), NO solute step). Call `write_ion_gro_file(ion, ...)`. Parse residue names. Assert SOL before custom before NA before CL. Assert NO "CH4_L" residues.
- `test_f2_top_no_solute_itp(self, interface_slab, tmp_path)`: Call `write_ion_top_file(ion, ...)`. Parse includes. Assert "ch4_liquid.itp" NOT in includes (no solutes). Assert "etoh.itp" in includes (custom molecules). Assert "ion.itp" in includes.

**Class TestHydrateChainF3Export:**
- `test_f3_gro_has_ch4_h_and_ch4_l(self, tmp_path)`: Build F3 chain: hydrate_sI_ch4_candidate() → slab interface → solute(CH4,0.3) → ion(0.15) via workaround. Call `write_ion_gro_file(ion, ...)`. Parse residue names. Find CH4_H (hydrate guest) and CH4_L (liquid solute) residues. Assert CH4_H indices before CH4_L indices. Assert CH4_L indices before NA indices.
- `test_f3_top_molecules_ch4_h_ch4_l_distinct(self, tmp_path)`: Call `write_ion_top_file(ion, ...)`. Parse molecules. Assert BOTH "CH4_H" and "CH4_L" in molecules dict. Assert counts are > 0 for each. Parse includes. Assert "ch4_hydrate.itp" AND "ch4_liquid.itp" in includes.

**Class TestSimpleSoluteChainF6Export:**
- `test_f6_gro_sol_before_solute_before_ions(self, interface_slab, tmp_path)`: Build F6 chain: interface_slab → solute(CH4,0.3) → ion(0.15) via workaround. Call `write_ion_gro_file(ion, ...)`. Parse residue names. Assert SOL before CH4_L before NA before CL. Assert NO custom molecule residues.
- `test_f6_top_molecules_correct(self, interface_slab, tmp_path)`: Parse `parse_top_molecules`. Assert SOL, CH4_L, NA, CL all present with correct counts. No custom entry.

**Class TestTHFChainF7Export:**
- `test_f7_gro_thf_l_residues(self, interface_slab, tmp_path)`: Build F7 chain: interface_slab → solute(THF,0.15) → ion(0.15) via workaround. Call `write_ion_gro_file(ion, ...)`. Parse residue names. Assert SOL before THF_L before NA before CL. THF_L is 5 chars (truncated from THF_LIQ if needed — the writer uses `solute_res_name[:5]`, so check what the actual output name is; it should be "THF_L").
- `test_f7_top_thf_liquid_itp(self, interface_slab, tmp_path)`: Parse includes. Assert "thf_liquid.itp" in includes. Parse molecules — assert "THF_L" in molecules.

CRITICAL implementation notes:
- The SoluteInserter for F3 needs `inserter.registry.register_hydrate_guest("CH4")` BEFORE `insert_solutes()` — same pattern as test_e2e_solute_insertion.py
- The `_solute_to_ion_source` workaround is MANDATORY for F1, F3, F6, F7 (where source is a SoluteStructure) — it attaches solute attrs to interface_structure so IonInserter can access them
- F2 chain does NOT need the workaround (source is CustomMoleculeStructure, which goes directly to IonInserter)
- For F1: custom molecule residue name in .gro is `custom.moleculetype_name[:5]` which is "ETOH" (from etoh.itp). Check test output to confirm.
- THF_L residue name: `solute_structure.registry.get_gromacs_name(f"liquid_{solute_structure.solute_type}")` → "THF_L". Truncated to 5 chars = "THF_L" (5 chars exactly, fits).
- CH4_L residue name: same logic → "CH4_L" (5 chars exactly).
- `parse_gro_atom_count` returns the integer from line 2 of .gro. The actual number of atom LINES should be `len(residue_names)` since each atom has one residue name.
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -m pytest tests/test_e2e_compute_export_chain.py -v --no-header -q 2>&1 | tail -20</verify>
  <done>All ~8 chain export tests pass: F1 (3), F2 (2), F3 (2), F6 (2), F7 (2). Molecule ordering validated in .gro. [molecules] section validated in .top. ITP includes validated.</done>
</task>

<task type="auto">
  <name>Task 2: Add ITP bundling validation + atom conservation + THF hydrate chain tests</name>
  <files>tests/test_e2e_compute_export_chain.py</files>
  <action>
Add additional tests to `tests/test_e2e_compute_export_chain.py` (append to the file created in Task 1):

**Class TestITPBundling:**
- `test_full_chain_itp_files_exist(self, interface_slab, tmp_path)`: Build F1 chain and export. Parse `parse_top_includes(top_path)`. For each included filename, assert `Path("quickice/data") / filename` exists (use `quickice.__file__` to find package dir, same as `get_tip4p_itp_path()` pattern). Assert ALL included ITP files exist.
- `test_full_chain_itp_have_moleculetype(self, interface_slab, tmp_path)`: For each ITP file from the test above, open and read content. Assert `[ moleculetype ]` (case-insensitive) appears in each ITP file. This verifies ITP files are valid GROMACS topology fragments.
- `test_hydrate_chain_itp_set(self, tmp_path)`: Build F3 chain and export. Parse includes. Assert the includes contain AT LEAST: "tip4p-ice.itp", "ch4_hydrate.itp", "ch4_liquid.itp", "ion.itp". These 4 ITP files represent all molecule types in the F3 chain.

**Class TestAtomConservation:**
- `test_no_atoms_lost_in_export(self, interface_slab, tmp_path)`: Build F1 chain. Calculate EXPECTED output atom count:
  - SOL (ice): sum(1 for m in ion.molecule_index if m.mol_type == 'ice') * 4 (3→4 expansion with MW)
  - SOL (water): sum(1 for m in ion.molecule_index if m.mol_type == 'water') * 4
  - Guests: ion.guest_atom_count (if > 0)
  - Custom: ion.custom_molecule_atom_count (if > 0)
  - Solutes: len(ion.solute_atom_names) if ion.solute_positions is not None
  - Ions: ion.na_count + ion.cl_count (1 atom each)
  
  Write .gro via `write_ion_gro_file`. Parse `parse_gro_atom_count`. Assert parsed count == expected count. Also assert `len(parse_gro_residue_names(gro_path)) == expected_count` (each atom line has one residue name).

- `test_hydrate_chain_atom_conservation(self, tmp_path)`: Build F3 chain. Calculate expected atoms similarly. Write .gro. Assert atom count matches.

**Class TestTHFHydrateChainF4Export:**
- `test_f4_gro_all_molecule_types(self, tmp_path)`: Build F4 chain: hydrate_sI_thf_candidate() → slab interface → custom(2) → solute(THF,0.2) → ion(0.15) via workaround. Write .gro. Parse residue names. Assert at least 4 distinct residue name types appear: SOL, THF_H (or THF_H truncated — check output), custom mol name, THF_L, NA, CL. NOTE: guest_nmolecules is lost through CustomMoleculeStructure (known limitation from e2e-api-workflow-05), so guest residues may NOT appear in the output. If guest_atom_count > 0 but guest_nmolecules == 0, the writer may skip guest lines. This is a known limitation — the test should document this and check guest_atom_count > 0 as a precondition, then assert accordingly.
- `test_f4_top_thf_h_and_thf_l(self, tmp_path)`: Write .top. Parse molecules. If THF_H present (guest_nmolecules > 0), assert THF_H and THF_L both in molecules dict with distinct counts. If guest_nmolecules == 0 (known limitation), assert at least THF_L present. Parse includes — assert "thf_hydrate.itp" (if guests) and "thf_liquid.itp" present.

IMPORTANT: For F4, the `guest_nmolecules` loss through CustomMoleculeStructure is a KNOWN limitation documented in e2e-api-workflow Plan 05. The test should handle this gracefully:
```python
# Known limitation: guest_nmolecules lost through CustomMoleculeStructure
if ion.guest_nmolecules > 0:
    # Full guest export works
    assert "THF_H" in residue_names or any("THF" in n for n in residue_names)
else:
    # Known limitation: guest_atom_count > 0 but guest_nmolecules == 0
    # Guest atoms exist but writer may not produce guest residue lines
    pytest.skip("guest_nmolecules lost through CustomMoleculeStructure (known limitation)")
```

Package directory resolution for ITP existence checks:
```python
import quickice
package_dir = Path(quickice.__file__).parent
data_dir = package_dir / "data"
```
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -m pytest tests/test_e2e_compute_export_chain.py -v --no-header -q 2>&1 | tail -20</verify>
  <done>All ~12 chain export tests pass. ITP bundling validated (files exist + have [moleculetype]). Atom conservation verified for F1 and F3 chains. THF hydrate chain (F4) tested with known limitation handling.</done>
</task>

</tasks>

<verification>
1. `python -m pytest tests/test_e2e_compute_export_chain.py -v` — all tests pass
2. `python -m pytest tests/ -k "compute_export" --co -q` — lists all new tests from both files
3. `python -m pytest tests/ -k "compute_export" -v` — all compute-export tests pass together
</verification>

<success_criteria>
1. test_e2e_compute_export_chain.py created with ~12 tests covering F1-F7 chains
2. F1 (Ice→Custom→Solute→Ion) export validates SOL→custom→CH4_L→NA→CL ordering
3. F3 (Hydrate→Solute→Ion) export validates CH4_H before CH4_L before NA before CL
4. ITP files referenced in .top exist in quickice/data/ and contain [moleculetype]
5. Atom count in .gro matches calculated expected count (no atoms lost)
6. THF chain (F7) validates THF_L residue names and thf_liquid.itp
7. F4 (THF hydrate chain) gracefully handles guest_nmolecules limitation
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-compute-export/e2e-compute-export-02-SUMMARY.md`
</output>
