---
phase: e2e-export-test
plan: 06
type: execute
wave: 3
depends_on: ["e2e-export-test-01", "e2e-export-test-04"]
files_modified:
  - tests/test_output/test_gromacs_export_solute.py
autonomous: true

must_haves:
  truths:
    - "Solute export creates .gro, .top, tip4p-ice.itp, and solute liquid ITP"
    - "Solute liquid ITP has atomtypes commented out"
    - "Guest ITP is copied when interface_structure has guests"
    - "Custom molecule ITP is copied when custom_molecule_count > 0"
    - "interface_structure is accessed for guest detection and molecule_index"
  artifacts:
    - path: "tests/test_output/test_gromacs_export_solute.py"
      provides: "E2E tests for SoluteGROMACSExporter (Tab 4)"
      min_lines: 150
  key_links:
    - from: "tests/test_output/test_gromacs_export_solute.py"
      to: "quickice/gui/export.py"
      via: "import SoluteGROMACSExporter"
      pattern: "from quickice\\.gui\\.export import SoluteGROMACSExporter"
    - from: "tests/test_output/test_gromacs_export_solute.py"
      to: "tests/test_output/conftest.py"
      via: "solute_structure fixture with interface_structure dependency"
      pattern: "solute_structure"
---

<objective>
Test SoluteGROMACSExporter (Tab 4 — Solute) end-to-end. This is the first exporter that accesses a nested structure (`solute_structure.interface_structure`) for guest detection and molecule_index, and has the most conditional ITP logic of any exporter tested so far (solute ITP + guest ITP + custom ITP).

Purpose: Validates that `interface_structure` is correctly accessed for guest detection. If `interface_structure` is None, the export crashes with AttributeError. This test ensures the chain dependency works.

Output: `tests/test_output/test_gromacs_export_solute.py` with `TestSoluteGROMACSExporter` class containing 5 test methods.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/e2e-export-test/e2e-export-test-RESEARCH.md
@.planning/phases/e2e-export-test/PLAN-01-fixtures.md
@quickice/gui/export.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create test_gromacs_export_solute.py with 5 test methods</name>
  <files>tests/test_output/test_gromacs_export_solute.py</files>
  <action>
Create `tests/test_output/test_gromacs_export_solute.py` with class `TestSoluteGROMACSExporter` containing these 5 tests:

**Test 1: `test_export_creates_base_files`**
- Use `solute_structure` fixture from conftest (interface_structure has CH4 guests)
- Use `mock_save_dialog`, filename "solute_ch4_1.gro"
- Call `exporter.export_solute_gromacs(solute_structure)`
- Assert `result is True`
- Assert files exist: `solute_ch4_1.gro`, `solute_ch4_1.top`, `tip4p-ice.itp`
- Assert `ch4_liquid.itp` exists (solute liquid ITP)
- Assert `ch4_hydrate.itp` exists (guest ITP, because interface has guests)

**Test 2: `test_solute_itp_has_atomtypes_commented_out`**
- Export and read `ch4_liquid.itp` from output directory
- Assert it contains the atomtypes comment: `; Modified for QuickIce: [atomtypes] commented` OR atomtypes lines are prefixed with `;`
- The `comment_out_atomtypes_in_itp()` function is applied to solute ITP files before writing

**Test 3: `test_guest_itp_copied_when_interface_has_guests`**
- The `solute_structure` fixture uses `interface_with_ch4_guests` (which has guest_nmolecules=1, guest_atom_count=5)
- Export and verify `ch4_hydrate.itp` exists in output directory
- Read the .top file and assert it contains `#include "ch4_hydrate.itp"`

**Test 4: `test_no_guest_itp_when_no_guests`**
- Create a solute_structure variant with `interface_structure=simple_interface` (no guests)
- The simplest approach: build the solute_structure inline in the test
- Use `simple_interface` fixture (from conftest), create a SoluteStructure with `interface_structure=simple_interface`
- Export and verify NO `ch4_hydrate.itp` or `thf_hydrate.itp` in output directory
- Implementation:
  ```python
  def test_no_guest_itp_when_no_guests(self, simple_interface, mock_save_dialog):
      from quickice.gui.export import SoluteGROMACSExporter
      from quickice.structure_generation.types import SoluteStructure
      from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
      
      registry = MoleculetypeRegistry()
      registry.register_liquid_solute("CH4")
      
      solute = SoluteStructure(
          positions=np.array([[0.5, 0.5, 0.5], [0.55, 0.5, 0.5], [0.45, 0.5, 0.5], [0.55, 0.45, 0.5], [0.45, 0.45, 0.5]]),
          atom_names=["C", "H", "H", "H", "H"],
          cell=simple_interface.cell,
          solute_type="CH4",
          n_molecules=1,
          molecule_indices=[(0, 5)],
          registry=registry,
          interface_structure=simple_interface,  # NO guests
      )
      
      save_path, dialog_p, mb_p = mock_save_dialog("solute_noguest.gro")
      exporter = SoluteGROMACSExporter(parent_widget=None)
      
      with dialog_p, mb_p:
          result = exporter.export_solute_gromacs(solute)
      
      assert result is True
      tmp_path = Path(save_path).parent
      assert not (tmp_path / "ch4_hydrate.itp").exists()
      assert not (tmp_path / "thf_hydrate.itp").exists()
  ```

**Test 5: `test_custom_itp_copied_when_custom_molecules_present`**
- Create a solute_structure with `custom_molecule_count > 0` and `custom_molecule_positions is not None`
- Set `custom_itp_path = Path("quickice/data/custom/etoh.itp")` (must exist)
- Set `custom_molecule_moleculetype = "ETOH"`
- Export and verify `etoh.itp` exists in output directory
- Verify the output etoh.itp has atomtypes commented out
- Implementation:
  ```python
  def test_custom_itp_copied_when_custom_molecules_present(self, interface_with_ch4_guests, mock_save_dialog):
      from quickice.gui.export import SoluteGROMACSExporter
      from quickice.structure_generation.types import SoluteStructure
      from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
      
      registry = MoleculetypeRegistry()
      registry.register_liquid_solute("CH4")
      
      solute = SoluteStructure(
          positions=np.array([[0.5, 0.5, 0.5], [0.55, 0.5, 0.5], [0.45, 0.5, 0.5], [0.55, 0.45, 0.5], [0.45, 0.45, 0.5]]),
          atom_names=["C", "H", "H", "H", "H"],
          cell=interface_with_ch4_guests.cell,
          solute_type="CH4",
          n_molecules=1,
          molecule_indices=[(0, 5)],
          registry=registry,
          interface_structure=interface_with_ch4_guests,
          custom_molecule_count=1,
          custom_molecule_positions=np.zeros((9, 3)),
          custom_molecule_moleculetype="ETOH",
          custom_itp_path=Path("quickice/data/custom/etoh.itp"),
      )
      
      save_path, dialog_p, mb_p = mock_save_dialog("solute_custom.gro")
      exporter = SoluteGROMACSExporter(parent_widget=None)
      
      with dialog_p, mb_p:
          result = exporter.export_solute_gromacs(solute)
      
      assert result is True
      tmp_path = Path(save_path).parent
      assert (tmp_path / "etoh.itp").exists()
  ```

**Key details from source code (export.py lines 80-157):**
- The exporter accesses `solute_structure.interface_structure` at line 97
- If `interface.guest_nmolecules > 0 and interface.guest_atom_count > 0`, it detects guest type from molecule_index entries with mol_type=="guest"
- The solute ITP is found via `Path(__file__).parent.parent / "data" / f"{solute_type_lower}_liquid.itp"` (line 132)
- If the solute ITP source file doesn't exist, it silently skips (no error, just no ITP copied)
- Custom ITP requires ALL THREE: `custom_molecule_count > 0 AND custom_molecule_positions is not None AND custom_itp_path exists`

**IMPORTANT: SoluteGROMACSExporter is the FIRST class in export.py (line 26), before CustomMoleculeGROMACSExporter (line 160).**
  </action>
  <verify>
    cd /share/home/nglokwan/quickice && python -m pytest tests/test_output/test_gromacs_export_solute.py -v --tb=short 2>&1 | tail -30
  </verify>
  <done>
    - 5 test methods in TestSoluteGROMACSExporter class
    - All 5 pass
    - interface_structure dependency validated (guest detection works through nested access)
    - Solute liquid ITP has atomtypes commented
    - Guest ITP conditional on interface guests
    - Custom ITP conditional on custom_molecule_count + positions + itp_path
  </done>
</task>

</tasks>

<verification>
```bash
cd /share/home/nglokwan/quickice && python -m pytest tests/test_output/test_gromacs_export_solute.py -v
```
All 5 tests pass.
</verification>

<success_criteria>
- test_gromacs_export_solute.py exists with TestSoluteGROMACSExporter class
- 5/5 tests pass
- interface_structure access pattern validated (no AttributeError)
- ch4_liquid.itp created with atomtypes commented
- Guest and custom ITP conditional logic works correctly
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-export-test/e2e-export-test-06-SUMMARY.md`
</output>
