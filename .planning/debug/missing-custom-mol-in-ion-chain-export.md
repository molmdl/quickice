---
status: resolved
trigger: "When exporting through the ice→interface→custom→ion chain, the custom molecule is missing from the exported .gro file in the ion export step."
created: 2026-06-19T00:00:00Z
updated: 2026-06-19T00:05:00Z
---

## Current Focus

hypothesis: CONFIRMED - custom_molecule_atom_count is not set when propagating custom molecule attrs from CustomMoleculeStructure to InterfaceStructure in the custom→ion chain
test: Trace GUI main_window.py and CLI pipeline.py custom→ion paths; verify fix with E2E tests
expecting: Custom molecule atoms now appear in .gro file
next_action: Archive debug session

## Symptoms

expected: In the ice-interface-custom-ion chain, the IonStructure export should produce a .gro file that includes custom molecule atoms (e.g., ETOH ethanol) between guest molecules and ions, matching the [molecules] section order: SOL, guest, custom, NA, CL.
actual: The custom molecule atoms are missing from the .gro file, or the positions are wrong/zeroed out. The .top file correctly references the custom molecule ITP and lists it in [molecules], but the .gro file doesn't have corresponding atoms.
errors: GROMACS topology mismatch — .top says there are N custom molecules but .gro doesn't have those atoms, causing atom count mismatch.
reproduction: Build a full chain: Interface with THF guests → CustomMoleculeStructure (add ETOH) → IonStructure (add ions). Export the IonStructure. Check the .gro file for ETOH atoms.
started: Has been present since the ion chain export was implemented.

## Eliminated

- hypothesis: custom_molecule_atom_names is None/empty in IonStructure
  evidence: Both GUI and CLI set custom_molecule_atom_names correctly from the CustomMoleculeStructure's atom_names offset. Not the issue.
  timestamp: 2026-06-19T00:01

- hypothesis: custom_molecule_positions are incorrectly indexed in GRO writer
  evidence: The GRO writer correctly indexes into wrapped_custom_positions using mol.start_idx, which is relative to custom_molecule_positions. The indexing logic is correct IF the data reaches the writer.
  timestamp: 2026-06-19T00:01

- hypothesis: Only the GUI/CLI propagation paths are missing custom_molecule_atom_count
  evidence: The ion_inserter early return paths also miss custom molecule attribute propagation (3 early return paths at lines 227, 254, 289)
  timestamp: 2026-06-19T00:04

## Evidence

- timestamp: 2026-06-19T00:00
  checked: IonStructure type definition (types.py lines 410-461)
  found: IonStructure has custom_molecule_atom_count field (default 0)
  implication: If custom_molecule_atom_count=0, GRO writer computes atoms_per_custom=0, writes zero atoms

- timestamp: 2026-06-19T00:00
  checked: GRO writer (gromacs_writer.py lines 1398-1400)
  found: atoms_per_custom = 0 when custom_molecule_atom_count=0. Each pseudo-mol gets count=0. No custom atoms written.
  implication: Root cause of missing atoms in .gro file

- timestamp: 2026-06-19T00:01
  checked: GUI main_window.py lines 898-904
  found: Sets 6 custom molecule attributes but DOES NOT set custom_molecule_atom_count
  implication: Primary bug in GUI path

- timestamp: 2026-06-19T00:01
  checked: CLI pipeline.py lines 606-618
  found: Same bug — does NOT set custom_molecule_atom_count
  implication: Same bug in CLI path. solute→ion path (line 651) correctly sets it.

- timestamp: 2026-06-19T00:01
  checked: Test helper e2e_export_helpers.py lines 282-283
  found: Correctly sets custom_molecule_atom_count in solute→ion chain
  implication: Test helper is correct, but test doesn't cover custom→ion direct path

- timestamp: 2026-06-19T00:01
  checked: Test test_gromacs_export_chain.py lines 428-431
  found: Test manually constructs IonStructure with custom_molecule_atom_count=9, so test passes. Doesn't verify .gro file content.
  implication: Test doesn't catch this bug because it bypasses the real data flow

- timestamp: 2026-06-19T00:03
  checked: ion_inserter.py early return paths (lines 227, 254, 289)
  found: All 3 early return paths in replace_water_with_ions() omit custom molecule attributes when constructing IonStructure
  implication: Secondary bug — even if propagation is fixed, edge cases (zero ions, no water) still lose custom molecule data

- timestamp: 2026-06-19T00:05
  checked: E2E verification with realistic system (500 water, 3 THF guests, 1 ETOH, 0.5M ions)
  found: After fix, GRO file contains all ETOH atoms, correct residue order (SOL→GUE→ETOH→NA→CL), header count matches actual atoms
  implication: Fix verified with full chain simulation

- timestamp: 2026-06-19T00:05
  checked: Full test suite (224 tests)
  found: All tests pass after fix
  implication: No regressions introduced

## Resolution

root_cause: Two related bugs causing custom molecule atoms to be missing from .gro file in the custom→ion export chain:

1. PRIMARY BUG: In both GUI (main_window.py) and CLI (pipeline.py), when propagating custom molecule attributes from CustomMoleculeStructure to InterfaceStructure for the custom→ion chain, `custom_molecule_atom_count` was NOT set. It stayed at the default value of 0. This caused the GRO writer to compute atoms_per_custom=0, resulting in zero custom molecule atoms being written to the .gro file. The .top file was unaffected because it uses custom_molecule_count (which WAS set), creating a topology/GRO mismatch.

2. SECONDARY BUG: All three early return paths in ion_inserter.py's replace_water_with_ions() method (no water found, zero ion pairs, not enough water) omitted custom molecule attributes when constructing IonStructure, causing custom molecule data to be lost in edge cases.

fix: 
1. Added `interface.custom_molecule_atom_count = custom_structure.custom_molecule_atom_count` in main_window.py (line 902)
2. Added `interface.custom_molecule_atom_count = source.custom_molecule_atom_count` in pipeline.py (line 616)
3. Added custom molecule attribute extraction and propagation to all 3 early return paths in ion_inserter.py (lines 227, 254, 289)

verification: E2E test with 500 water molecules, 3 THF guests, 1 ETOH custom molecule, and 0.5M ions. GRO file contains all 9 ETOH atoms, correct residue order (SOL→GUE→ETOH→NA→CL), header count matches actual atoms. Full test suite of 224 tests passes with zero regressions.

files_changed:
- quickice/gui/main_window.py: Added custom_molecule_atom_count assignment (line 902)
- quickice/cli/pipeline.py: Added custom_molecule_atom_count assignment (line 616)
- quickice/structure_generation/ion_inserter.py: Added custom molecule attribute propagation to 3 early return paths (lines 227, 254, 289)
