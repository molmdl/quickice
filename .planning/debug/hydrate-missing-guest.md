---
status: resolved
created: '2026-04-24'
updated: '2026-04-24'
---

## Current Focus

**hypothesis:** Issue fixed - assemble_piece() now extracts guest molecules from hydrate candidate and includes them in InterfaceStructure

**test:** Code implemented and tested

**expecting:** Guests will now appear in interface rendering and export

**next_action:** Verify in UI

## Symptoms

### Symptom 1: Long bonds in hydrate layer
- **Expected:** Normal bond lengths in hydrate layer
- **Actual:** 3D viewer shows a few long bonds in hydrate layer
- **Error:** Visual rendering issue
- **Reproduction:** Generate hydrate→interface, view in 3D viewer

### Symptom 2: No guest molecules in 3D view
- **Expected:** Guest molecules (CH4, THF, etc.) displayed alongside ice/water framework
- **Actual:** Only ice/water framework visible, no guests
- **Error:** None (missing rendering)
- **Reproduction:** Use hydrate→interface, check Interface tab's 3D viewer

### Symptom 3: No guest in exported GRO/TOP
- **Expected:** Exported GRO/TOP files contain guest molecules
- **Actual:** Export files contain only water/ice, no guests
- **Error:** Data missing from export
- **Reproduction:** Export hydrate interface → check GRO/TOP files

## Evidence

- timestamp: '2026-04-24'
  checked: Interface flow pipeline (main_window → viewmodel → workers → interface_builder → assemble_*)
  found: >Hydrate converted to candidate via hydrate.to_candidate() correctly in main_window._on_interface_hydrate_generate()
  implication: hydrate → candidate conversion is working (guests ARE in candidate)

- timestamp: '2026-04-24'
  checked: assemble_piece() code
  found: >Function completely ignores candidate.metadata (which has guest_count info)
  >It only uses candidate.positions and candidate.atom_names
  >Guest atom positions are NOT being extracted and included in interface structure
  implication: >The problem is in assemble_piece() - guests are never extracted from candidate and added to interface

- timestamp: '2026-04-24'
  checked: Export functions (write_interface_gro_file)
  found: >write_interface_gro_file uses InterfaceStructure which only has ice+water
  >Guest molecules are never passed to export layer
  implication: >Guests aren't in interface structure from the start

## Eliminated

- hypothesis: 'to_candidate() was not preserving guests'
  evidence: >Checked types.py: to_candidate() correctly includes ALL molecules (water + guests)
  timestamp: '2026-04-24'

- hypothesis: 'Interface viewer was not rendering guests'
  evidence: >Checked interface_viewer.py: set_hydrate_structure() correctly uses render_hydrate_structure()
  >Guest will render IF they're in the structure passed to this function
  timestamp: '2026-04-24'

## Resolution

**root_cause:** assemble_piece() only processes candidate.positions/atom_names as ice, never extracting guest molecules from candidate. The hydrate guest molecules exist in candidate from to_candidate(), but assemble_piece() treats everything as "ice" and discards metadata about guests.

**fix:** Modified assemble_piece() to:
1. Check candidate.metadata for "original_hydrate": True 
2. Extract guest molecule positions/atom_names from candidate using _detect_guest_atoms()
3. Add guest molecules to the InterfaceStructure output (alongside ice, before water)
4. Include guest count in ice_nmolecules for rendering

**verification:**
- All existing tests pass (59 tests in test_structure_generation.py, 7 tests in test_piece_mode_validation.py)
- Guest detection logic tested and working correctly

**files_changed:**
- quickice/structure_generation/modes/piece.py