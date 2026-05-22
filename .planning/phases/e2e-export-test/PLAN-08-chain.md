---
phase: e2e-export-test
plan: 08
type: execute
wave: 5
depends_on: ["e2e-export-test-02", "e2e-export-test-03", "e2e-export-test-04", "e2e-export-test-05", "e2e-export-test-06", "e2e-export-test-07"]
files_modified:
  - tests/test_output/test_gromacs_export_chain.py
autonomous: true

must_haves:
  truths:
    - "Incremental chain: interface export produces files, custom adds ITP, solute adds solute ITP, ion adds ion.itp"
    - "Each export level produces ALL files from previous level PLUS its own additions"
    - "IonStructure carrying forward all data (guest, solute, custom) exports correctly"
    - "Full pipeline produces complete set of ITP files"
  artifacts:
    - path: "tests/test_output/test_gromacs_export_chain.py"
      provides: "Full chain E2E test proving the incremental pipeline works"
      min_lines: 200
  key_links:
    - from: "tests/test_output/test_gromacs_export_chain.py"
      to: "quickice/gui/export.py"
      via: "imports all 5 non-hydrate exporters"
      pattern: "InterfaceGROMACSExporter|CustomMoleculeGROMACSExporter|SoluteGROMACSExporter|IonGROMACSExporter"
    - from: "tests/test_output/test_gromacs_export_chain.py"
      to: "quickice/structure_generation/types.py"
      via: "builds structures incrementally following chain dependency"
      pattern: "InterfaceStructure|CustomMoleculeStructure|SoluteStructure|IonStructure"
---

<objective>
Test the FULL chain: Interface → Custom Molecule → Solute → Ion. This is the "real" E2E test that proves the incremental pipeline works end-to-end. Each level of the chain carries forward data from the previous level, and the export must produce the correct cumulative set of files.

Purpose: Individual exporter tests (Plans 02-07) prove each exporter works in isolation. This test proves they work TOGETHER — that IonStructure correctly carries forward guest, solute, and custom molecule data, and that the ion exporter produces ALL ITP files from all previous levels.

Output: `tests/test_output/test_gromacs_export_chain.py` with `TestFullExportChain` class containing 4 test methods.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/e2e-export-test/e2e-export-test-RESEARCH.md
@quickice/gui/export.py
@quickice/structure_generation/types.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create test_gromacs_export_chain.py with 4 chain tests</name>
  <files>tests/test_output/test_gromacs_export_chain.py</files>
  <action>
Create `tests/test_output/test_gromacs_export_chain.py` with class `TestFullExportChain` containing these 4 tests:

**Test 1: `test_interface_to_custom_chain`**
- Build InterfaceStructure (with CH4 guests)
- Export it via InterfaceGROMACSExporter → produces .gro, .top, tip4p-ice.itp, ch4_hydrate.itp
- Build CustomMoleculeStructure using the SAME InterfaceStructure (stored as custom.interface_structure)
- Export it via CustomMoleculeGROMACSExporter → produces .gro, .top, tip4p-ice.itp, etoh.itp, ch4_hydrate.itp
- Verify: custom export has ALL files from interface export PLUS etoh.itp
- Implementation:
  ```python
  def test_interface_to_custom_chain(self, tmp_path):
      from quickice.gui.export import InterfaceGROMACSExporter, CustomMoleculeGROMACSExporter
      from quickice.structure_generation.types import InterfaceStructure, CustomMoleculeStructure, MoleculeIndex
      from unittest.mock import patch
      import numpy as np
      
      # Step 1: Build interface with CH4 guests
      iface = InterfaceStructure(
          positions=np.zeros((19, 3)),  # 6 ice + 8 water + 5 CH4
          atom_names=["O","H","H","O","H","H","OW","HW1","HW2","MW","OW","HW1","HW2","MW","C","H","H","H","H"],
          cell=np.eye(3) * 3.0,
          ice_atom_count=6, water_atom_count=8,
          ice_nmolecules=2, water_nmolecules=2,
          mode="slab", report="test",
          guest_atom_count=5, guest_nmolecules=1,
          molecule_index=[
              MoleculeIndex(0, 3, "ice"), MoleculeIndex(3, 3, "ice"),
              MoleculeIndex(6, 4, "water"), MoleculeIndex(10, 4, "water"),
              MoleculeIndex(14, 5, "guest"),
          ],
      )
      
      # Step 1a: Export interface
      iface_dir = tmp_path / "interface"
      iface_dir.mkdir()
      iface_exporter = InterfaceGROMACSExporter(parent_widget=None)
      with patch('quickice.gui.export.QFileDialog.getSaveFileName',
                 return_value=(str(iface_dir / "iface.gro"), "GRO Files (*.gro)")):
          with patch('quickice.gui.export.QMessageBox'):
              result = iface_exporter.export_interface_gromacs(iface)
      assert result is True
      assert (iface_dir / "iface.gro").exists()
      assert (iface_dir / "iface.top").exists()
      assert (iface_dir / "tip4p-ice.itp").exists()
      assert (iface_dir / "ch4_hydrate.itp").exists()
      
      # Step 2: Build custom structure with same interface
      custom = CustomMoleculeStructure(
          positions=np.zeros((28, 3)),  # 19 interface + 9 etoh
          atom_names=iface.atom_names + ["C","H","H","OH","C","H","H","H","H"],  # approximate
          cell=iface.cell,
          molecule_index=iface.molecule_index + [MoleculeIndex(19, 9, "custom")],
          ice_atom_count=6, water_atom_count=8,
          custom_molecule_atom_count=9,
          guest_atom_count=5,
          moleculetype_name="ETOH",
          custom_molecule_count=1,
          itp_path=Path("quickice/data/custom/etoh.itp"),
          interface_structure=iface,
      )
      
      # Step 2a: Export custom
      custom_dir = tmp_path / "custom"
      custom_dir.mkdir()
      custom_exporter = CustomMoleculeGROMACSExporter(parent_widget=None)
      with patch('quickice.gui.export.QFileDialog.getSaveFileName',
                 return_value=(str(custom_dir / "custom.gro"), "GRO Files (*.gro)")):
          with patch('quickice.gui.export.QMessageBox'):
              result = custom_exporter.export_custom_molecule_gromacs(custom)
      assert result is True
      assert (custom_dir / "custom.gro").exists()
      assert (custom_dir / "custom.top").exists()
      assert (custom_dir / "tip4p-ice.itp").exists()
      assert (custom_dir / "etoh.itp").exists()
      assert (custom_dir / "ch4_hydrate.itp").exists()  # guests carried forward
  ```

**Test 2: `test_interface_to_solute_chain`**
- Build InterfaceStructure (with CH4 guests)
- Build SoluteStructure using the interface (CH4 solute)
- Export solute
- Verify: .gro, .top, tip4p-ice.itp, ch4_liquid.itp, ch4_hydrate.itp all exist
- The solute export has BOTH ch4_liquid.itp (for solutes) AND ch4_hydrate.itp (for guests from interface)

**Test 3: `test_full_chain_interface_custom_solute_ion`**
- This is THE main E2E test. Build the full chain:
  1. InterfaceStructure with CH4 guests → export
  2. CustomMoleculeStructure (interface + custom) → export
  3. SoluteStructure (interface + solute + custom) → export
  4. IonStructure (all data carried forward) → export
- At each level, verify the cumulative file set
- Final IonStructure export should produce ALL ITP files:
  - tip4p-ice.itp
  - ion.itp (generated)
  - ch4_hydrate.itp (from guests)
  - ch4_liquid.itp (from solutes)
  - etoh.itp (from custom molecules)
- Implementation:
  ```python
  def test_full_chain_interface_custom_solute_ion(self, tmp_path):
      # ... build interface, custom, solute, ion structures incrementally ...
      # ... export each and verify cumulative files ...
      
      # IonStructure carrying ALL data
      ion = IonStructure(
          positions=np.zeros((20, 3)),
          atom_names=["OW","HW1","HW2","MW","OW","HW1","HW2","MW","NA","CL", ...],
          cell=np.eye(3) * 3.0,
          molecule_index=[...],
          na_count=1, cl_count=1, report="test",
          # Guest data from interface
          guest_nmolecules=1, guest_atom_count=5,
          # Solute data
          solute_type="CH4", solute_n_molecules=1,
          solute_positions=np.array([[0.5, 0.5, 0.5], ...]),
          solute_atom_names=["C", "H", "H", "H", "H"],
          solute_molecule_indices=[(0, 5)],
          solute_registry=registry,
          # Custom data
          custom_molecule_count=1,
          custom_molecule_positions=np.zeros((9, 3)),
          custom_molecule_atom_names=["C", "H", ...],
          custom_molecule_moleculetype="ETOH",
          custom_itp_path=Path("quickice/data/custom/etoh.itp"),
      )
      
      # Export ion
      ion_dir = tmp_path / "ion"
      ion_dir.mkdir()
      ion_exporter = IonGROMACSExporter(parent_widget=None)
      save_path = str(ion_dir / "full_chain.gro")
      with patch('quickice.gui.export.QFileDialog.getSaveFileName',
                 return_value=(save_path, "GRO Files (*.gro)")):
          with patch('quickice.gui.export.QMessageBox'):
              result = ion_exporter.export_ion_gromacs(ion)
      
      assert result is True
      
      # Verify ALL ITP files
      assert (ion_dir / "full_chain.gro").exists()
      assert (ion_dir / "full_chain.top").exists()
      assert (ion_dir / "tip4p-ice.itp").exists()
      assert (ion_dir / "ion.itp").exists()
      assert (ion_dir / "ch4_hydrate.itp").exists()
      assert (ion_dir / "ch4_liquid.itp").exists()
      assert (ion_dir / "etoh.itp").exists()
      
      # Verify ion.itp is generated (not copied)
      ion_itp = (ion_dir / "ion.itp").read_text()
      assert "Madrid2019" in ion_itp
      assert "NA" in ion_itp
      assert "CL" in ion_itp
      
      # Verify .top references all ITP files
      top_content = (ion_dir / "full_chain.top").read_text()
      assert '#include "tip4p-ice.itp"' in top_content
      assert '#include "ion.itp"' in top_content
  ```

**Test 4: `test_chain_minimal_no_guests_no_solute_no_custom`**
- Build IonStructure with NO guests, NO solutes, NO custom molecules (minimal ion)
- Export and verify ONLY base files: .gro, .top, tip4p-ice.itp, ion.itp
- Verify NO conditional ITPs: no ch4_hydrate.itp, no ch4_liquid.itp, no etoh.itp
- This validates the "empty chain" — ions with just water and Na/Cl

**Structure for full chain test:**
For the IonStructure in test 3, the positions/molecule_index must be internally consistent:
- 2 water molecules = 8 atoms (OW,HW1,HW2,MW each)
- 1 NA = 1 atom
- 1 CL = 1 atom
- Guest atoms are NOT in IonStructure.positions — they're stored as guest_nmolecules/guest_atom_count metadata
- Similarly, solute atoms are in solute_positions (separate), custom atoms in custom_molecule_positions (separate)

Wait — actually checking IonStructure definition more carefully: the main `positions` field contains water + ions only. The solute and guest positions are stored in separate fields. The `molecule_index` tracks the main positions array. So:
- `positions`: 8 water + 1 NA + 1 CL = 10 atoms
- `molecule_index`: [MoleculeIndex(0,4,"water"), MoleculeIndex(4,4,"water"), MoleculeIndex(8,1,"na"), MoleculeIndex(9,1,"cl")]
- Guest data: `guest_nmolecules=1`, `guest_atom_count=5` (metadata only, not in positions)
- Solute data: `solute_positions` is a separate array
- Custom data: `custom_molecule_positions` is a separate array

This matches the IonStructure dataclass definition in types.py (line 341-391).

**IMPORTANT:** For guest ITP to be copied, the IonGROMACSExporter checks `ion_structure.molecule_index` for `mol_type == "guest"` entries (lines 346-352). If guest data is only in the metadata fields (guest_nmolecules, guest_atom_count) but NOT in molecule_index, the `detect_guest_type_from_atoms` will find no guest entries and fall through to the heuristic. The test MUST add a guest entry to molecule_index:
```python
molecule_index=[..., MoleculeIndex(10, 5, "guest")]
```
AND the atom_names must include the guest atoms at those positions.
  </action>
  <verify>
    cd /share/home/nglokwan/quickice && python -m pytest tests/test_output/test_gromacs_export_chain.py -v --tb=short 2>&1 | tail -30
  </verify>
  <done>
    - 4 test methods in TestFullExportChain class
    - All 4 pass
    - Interface → Custom chain carries guest ITP forward
    - Interface → Solute chain produces both liquid and hydrate ITPs
    - Full chain (interface → custom → solute → ion) produces ALL ITP files
    - Minimal chain (ions only) produces only base files
  </done>
</task>

</tasks>

<verification>
```bash
cd /share/home/nglokwan/quickice && python -m pytest tests/test_output/test_gromacs_export_chain.py -v
```
All 4 tests pass.
</verification>

<success_criteria>
- test_gromacs_export_chain.py exists with TestFullExportChain class
- 4/4 tests pass
- Full chain produces 7 ITP files (tip4p-ice, ion, ch4_hydrate, ch4_liquid, etoh)
- Minimal chain produces only 2 ITP files (tip4p-ice, ion)
- Chain data carry-forward validated (guest, solute, custom all accessible from IonStructure)
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-export-test/e2e-export-test-08-SUMMARY.md`
</output>
