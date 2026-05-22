---
phase: e2e-export-test
plan: 04
type: execute
wave: 2
depends_on: ["e2e-export-test-01"]
files_modified:
  - tests/test_output/test_gromacs_export_interface.py
autonomous: true

must_haves:
  truths:
    - "Interface export creates .gro, .top, and tip4p-ice.itp files"
    - "Interface with no guests exports only tip4p-ice.itp (no guest ITP)"
    - "Interface with CH4 guests also copies ch4_hydrate.itp"
    - "Interface with THF guests also copies thf_hydrate.itp"
    - "Cancelled dialog returns False"
    - "Guest type detection from atom names works correctly"
  artifacts:
    - path: "tests/test_output/test_gromacs_export_interface.py"
      provides: "E2E tests for InterfaceGROMACSExporter (Tab 2)"
      min_lines: 150
  key_links:
    - from: "tests/test_output/test_gromacs_export_interface.py"
      to: "quickice/gui/export.py"
      via: "import InterfaceGROMACSExporter"
      pattern: "from quickice\\.gui\\.export import InterfaceGROMACSExporter"
    - from: "tests/test_output/test_gromacs_export_interface.py"
      to: "quickice/output/gromacs_writer.py"
      via: "detect_guest_type_from_atoms used by exporter"
      pattern: "detect_guest_type"
---

<objective>
Test InterfaceGROMACSExporter (Tab 2 — Interface) end-to-end. This exporter has conditional guest ITP logic based on `guest_nmolecules > 0 AND guest_atom_count > 0`, making it the first test to validate guest detection and conditional ITP copying.

Purpose: The interface exporter is the GATEWAY for the chain dependency — Tab 3 (Custom), Tab 4 (Solute), and Tab 5 (Ion) all depend on InterfaceStructure. Testing the guest detection logic here validates the pattern used by all downstream exporters.

Output: `tests/test_output/test_gromacs_export_interface.py` with `TestInterfaceGROMACSExporter` class containing 6 test methods.
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
  <name>Task 1: Create test_gromacs_export_interface.py with 6 test methods</name>
  <files>tests/test_output/test_gromacs_export_interface.py</files>
  <action>
Create `tests/test_output/test_gromacs_export_interface.py` with class `TestInterfaceGROMACSExporter` containing these 6 tests:

**Test 1: `test_export_no_guests_creates_files`**
- Use `simple_interface` fixture (no guests)
- Use `mock_save_dialog` fixture, filename "interface_slab.gro"
- Call `exporter.export_interface_gromacs(simple_interface)`
- Assert `result is True`
- Assert files exist: `interface_slab.gro`, `interface_slab.top`, `tip4p-ice.itp`
- Assert `ch4_hydrate.itp` does NOT exist (no guests → no guest ITP)

**Test 2: `test_export_cancelled_returns_false`**
- Use `mock_cancel_dialog` fixture
- Call `exporter.export_interface_gromacs(simple_interface)`
- Assert `result is False`

**Test 3: `test_export_with_ch4_guests_creates_guest_itp`**
- Use `interface_with_ch4_guests` fixture (has CH4 guests)
- Use `mock_save_dialog` fixture, filename "iface_ch4.gro"
- Call `exporter.export_interface_gromacs(interface_with_ch4_guests)`
- Assert `result is True`
- Assert files exist: `iface_ch4.gro`, `iface_ch4.top`, `tip4p-ice.itp`, `ch4_hydrate.itp`
- Read ch4_hydrate.itp, assert it contains `[ moleculetype ]` section

**Test 4: `test_export_with_thf_guests_creates_guest_itp`**
- Use `interface_with_thf_guests` fixture (has THF guests)
- Use `mock_save_dialog` fixture, filename "iface_thf.gro"
- Call `exporter.export_interface_gromacs(interface_with_thf_guests)`
- Assert `result is True`
- Assert `thf_hydrate.itp` exists in output directory

**Test 5: `test_no_guest_itp_when_guest_count_zero`**
- Use `simple_interface` fixture (guest_atom_count=0, guest_nmolecules=0)
- Export and verify output directory contains only: .gro, .top, tip4p-ice.itp
- Explicitly assert NO ch4_hydrate.itp and NO thf_hydrate.itp

**Test 6: `test_gro_file_has_ice_and_water_atoms`**
- Use `simple_interface` fixture (2 ice molecules = 6 atoms + 2 water molecules = 8 atoms = 14 total)
- Export and read .gro file
- Ice molecules are expanded from 3→4 atoms at write time (by write_interface_gro_file)
- Water molecules are already 4 atoms (TIP4P-ICE: OW,HW1,HW2,MW)
- Expected total atoms: 2*4 (ice expanded) + 2*4 (water) = 16
- Parse atom count from line 2 of .gro file
- Assert atom count == 16

**IMPORTANT: Guest type detection logic in the exporter (lines 899-907 of export.py):**
```python
if interface_structure.guest_nmolecules > 0 and interface_structure.guest_atom_count > 0:
    guest_start = interface_structure.ice_atom_count + interface_structure.water_atom_count
    guest_atom_names = interface_structure.atom_names[guest_start:guest_start + interface_structure.guest_atom_count]
    guest_type = detect_guest_type_from_atoms(guest_atom_names)
```
The test fixtures MUST set both `guest_nmolecules > 0` AND `guest_atom_count > 0` for the guest ITP to be copied. Setting only one is insufficient.

**Mock pattern (same as Ice but different exporter class):**
```python
from quickice.gui.export import InterfaceGROMACSExporter

save_path, dialog_p, mb_p = mock_save_dialog("interface_slab.gro")
exporter = InterfaceGROMACSExporter(parent_widget=None)

with dialog_p, mb_p:
    result = exporter.export_interface_gromacs(simple_interface)
```

**Key difference from Ice exporter:**
- Ice: ITP named `{stem}.itp` (stem from .gro filename)
- Interface: Water ITP always named `tip4p-ice.itp` (hardcoded in exporter line 895)
- Guest ITP named `{guest_type}_hydrate.itp` (e.g., `ch4_hydrate.itp`)
  </action>
  <verify>
    cd /share/home/nglokwan/quickice && python -m pytest tests/test_output/test_gromacs_export_interface.py -v --tb=short 2>&1 | tail -30
  </verify>
  <done>
    - 6 test methods in TestInterfaceGROMACSExporter class
    - All 6 pass
    - No guests → no guest ITP file
    - CH4 guests → ch4_hydrate.itp copied
    - THF guests → thf_hydrate.itp copied
    - Cancelled returns False
    - Ice atoms expanded from 3→4 in .gro file
  </done>
</task>

</tasks>

<verification>
```bash
cd /share/home/nglokwan/quickice && python -m pytest tests/test_output/test_gromacs_export_interface.py -v
```
All 6 tests pass.
</verification>

<success_criteria>
- test_gromacs_export_interface.py exists with TestInterfaceGROMACSExporter class
- 6/6 tests pass
- Conditional guest ITP logic validated: no guests = no guest ITP, CH4 = ch4_hydrate.itp, THF = thf_hydrate.itp
- Cancelled dialog returns False
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-export-test/e2e-export-test-04-SUMMARY.md`
</output>
