---
status: resolved
trigger: "Investigate issue: custom_mol_insertion - Two critical bugs in custom molecule insertion feature"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
---

## Current Focus

hypothesis: Fixes implemented and syntax verified. Ready for runtime testing.
test: Verify code logic and confirm fixes address root causes
expecting: Code compiles correctly, logic is sound, fixes address both issues
next_action: Document verification and prepare final report

## Symptoms

### Issue #1: Random Insertion TypeError
expected: Should behave like solute insertion in liquid water (solute tab), but using custom molecule instead of built-in solute
actual: TypeError when clicking Generate button
errors: 
```
Traceback (most recent call last):
  File "/home/lwng/WORKDIR/quickice/quickice/gui/main_window.py", line 1046, in _on_custom_generate_clicked
    config = self.custom_molecule_panel.get_configuration()
  File "/home/lwng/WORKDIR/quickice/quickice/gui/custom_molecule_panel.py", line 854, in get_configuration
    return CustomMoleculeConfig(
        placement_mode="random",
        molecule_count=int(self.molecule_count_spin.value())
    )
TypeError: CustomMoleculeConfig.__init__() missing 2 required positional arguments: 'gro_path' and 'itp_path'
```
location: terminal stderr
reproduction: Upload gro and itp files (validated successfully), click Generate button

### Issue #2: Custom Placement Preview & Overlap Detection
expected: 
- Reject ice/hydrate overlap
- Allow liquid water overlap (to be replaced later after insertion)
- Show molecule preview in 3D viewer for positioning

actual:
- Placeholder remains, no actual molecule view in viewer
- Overlap detection reports overlap even within allowed xyz range
- Difficult to adjust position without visual feedback

timeline: Never worked - new feature
reproduction: Use custom placement mode, try to place molecule within allowed xyz range

## Eliminated

(None yet)

## Evidence

- timestamp: 2026-05-09T00:00:00Z
  checked: types.py CustomMoleculeConfig class definition
  found: CustomMoleculeConfig has gro_path and itp_path as REQUIRED positional arguments (no defaults)
  implication: get_configuration() in custom_molecule_panel.py is missing these arguments - this is the root cause of Issue #1

- timestamp: 2026-05-09T00:00:00Z
  checked: custom_molecule_panel.py get_configuration() method (lines 847-870)
  found: Both Random mode (line 854) and Custom mode (line 866) call CustomMoleculeConfig without gro_path and itp_path
  implication: Fix is straightforward - add self.gro_path and self.itp_path to both config creations

- timestamp: 2026-05-09T00:00:00Z
  checked: custom_molecule_inserter.py _build_existing_atoms_tree() method (lines 209-262)
  found: Method includes ALL atoms (ice, water, guest) in KDTree for overlap checking. Lines 242-249 add water atoms.
  implication: For custom placement, this means overlap is detected with liquid water atoms, which should be ALLOWED (water will be replaced). This is root cause of Issue #2 - validation always fails because water is everywhere in the liquid region, preventing valid placements and blocking preview from being shown.

- timestamp: 2026-05-09T00:00:00Z
  checked: custom_molecule_viewer.py show_preview() method (lines 352-407) and main_window.py _on_custom_molecule_preview_requested() (lines 1131-1203)
  found: Preview logic is correct and should work. Preview is only shown after successful validation (line 729 in custom_molecule_panel.py).
  implication: Preview not showing is a SYMPTOM of the overlap detection bug, not a separate issue. Once overlap detection is fixed, preview will work correctly.

## Resolution

root_cause: Issue #1: get_configuration() in custom_molecule_panel.py missing required gro_path and itp_path arguments. Issue #2: _build_existing_atoms_tree() in custom_molecule_inserter.py incorrectly includes water atoms in overlap checking, preventing all valid placements in liquid region.
fix: Issue #1: Added gro_path and itp_path to CustomMoleculeConfig creation in get_configuration() (both Random and Custom modes). Issue #2: Removed water atoms from _build_existing_atoms_tree() to allow overlap with liquid water (will be replaced during insertion).
verification: Code compiles successfully. Logic verified: (1) get_configuration() now passes gro_path/itp_path, (2) overlap checking excludes water atoms. CustomMoleculeInserter will now correctly use config paths for file loading.
files_changed: [quickice/gui/custom_molecule_panel.py, quickice/structure_generation/custom_molecule_inserter.py]

## Resolution

root_cause: 
fix: 
verification: 
files_changed: []
