---
status: resolved
trigger: "Two issues with custom molecule tab: 1) No 3D viewer shown, 2) Upload fails with AttributeError: 'ValidationResult' object has no attribute 'gro_atom_count'"
created: 2026-05-08T00:00:00Z
updated: 2026-05-08T00:35:00Z
---

## Current Focus

hypothesis: Both issues identified and fixes applied
test: Test upload of etoh.gro and etoh.itp files
expecting: Files should upload successfully and show atom count, 3D viewer should be visible
next_action: Test the fixes with actual file upload

## Symptoms

expected: 
- A 3D viewer should be displayed below/above the status box in the custom molecule tab
- Valid GRO and ITP files should upload successfully without errors

actual:
- No 3D viewer is shown in the custom molecule tab
- Upload fails with AttributeError: 'ValidationResult' object has no attribute 'gro_atom_count'

errors: 
- 'ValidationResult' object has no attribute 'gro_atom_count'

reproduction:
- Navigate to custom molecule tab
- Upload valid GRO file: quickice/data/custom/etoh.gro (contains 9 atoms of ethanol molecule)
- Upload valid ITP file: quickice/data/custom/etoh.itp (contains topology for ethanol with atomtypes, moleculetype, atoms, bonds, angles, dihedrals, pairs)
- Error appears after upload attempt

started: Current issue (just discovered)

## Eliminated

## Evidence

- timestamp: 2026-05-08T00:05:00Z
  checked: ValidationResult dataclass definition in molecule_validator.py (lines 18-35)
  found: ValidationResult has these attributes: is_valid, errors, warnings, residue_name_mismatch, gro_residue_name, itp_residue_name. NO gro_atom_count attribute.
  implication: This confirms the AttributeError - the dataclass doesn't have gro_atom_count

- timestamp: 2026-05-08T00:06:00Z
  checked: custom_molecule_panel.py line 489
  found: Code tries to access self.validation_result.gro_atom_count
  implication: This is where the AttributeError originates - trying to access non-existent attribute

- timestamp: 2026-05-08T00:07:00Z
  checked: validate_custom_molecule function in molecule_validator.py (lines 97-180)
  found: gro_atom_count is computed as local variable (line 129: gro_atom_count = len(positions)), but NOT passed to ValidationResult constructor (lines 173-180)
  implication: The attribute exists as local variable but is never stored in the returned object

- timestamp: 2026-05-08T00:15:00Z
  checked: CustomMoleculePanel __init__ and _setup_ui methods (lines 55-133)
  found: Comment at line 78 says "Right column (stretch=3): Log panel + 3D viewer (added by MainWindow)" but the viewer is NEVER created. No custom_viewer attribute exists.
  implication: The 3D viewer is missing from the CustomMoleculePanel entirely

- timestamp: 2026-05-08T00:16:00Z
  checked: SolutePanel for comparison (solute_panel.py lines 145-146)
  found: SolutePanel creates self.solute_viewer = SoluteViewerWidget() and adds it to right_layout.addWidget(self.solute_viewer, stretch=1)
  implication: CustomMoleculePanel should follow the same pattern - create its own viewer widget, not rely on MainWindow to add it

- timestamp: 2026-05-08T00:17:00Z
  checked: main_window.py lines 1092 and 1176-1179
  found: Line 1092 accesses self.custom_molecule_panel.custom_viewer, but lines 1176-1179 check for self.custom_molecule_viewer (different attribute!)
  implication: Inconsistent references - some code expects custom_viewer on the panel, some expects custom_molecule_viewer on MainWindow

## Resolution

root_cause: Two separate issues found:
1. ValidationResult dataclass missing gro_atom_count attribute
2. CustomMoleculePanel missing 3D viewer widget creation

fix: 
1. Added gro_atom_count: int | None = None to ValidationResult dataclass attributes
2. Updated validate_custom_molecule to pass gro_atom_count to ValidationResult constructor
3. Added CustomMoleculeViewerWidget import to custom_molecule_panel.py
4. Created self.custom_viewer in CustomMoleculePanel._setup_ui() and added to right_layout
5. Added hide_placeholder() method to CustomMoleculePanel
6. Fixed inconsistent references in main_window.py (changed self.custom_molecule_viewer to self.custom_molecule_panel.custom_viewer)

verification: 
1. Structural tests passed: ValidationResult has gro_atom_count attribute, CustomMoleculeViewerWidget imported correctly
2. File validation test passed: etoh.gro and etoh.itp files validated successfully, gro_atom_count=9 accessible
3. All existing tests pass: 7 tests in test_custom_molecule.py all pass
4. No AttributeError when accessing result.gro_atom_count
5. 3D viewer widget now created in CustomMoleculePanel

files_changed: 
- quickice/structure_generation/molecule_validator.py
- quickice/gui/custom_molecule_panel.py
- quickice/gui/main_window.py
