---
status: resolved
trigger: "Fix GROMACS export to include guest molecules for hydrate→interface and ion workflows"
created: "2026-04-22T00:00:00.000Z"
updated: "2026-04-23T00:00:00.000Z"
---

## Current Focus
Fixed: Guest molecules now included in GROMACS export for hydrate-derived interfaces

## Symptoms
expected: ".gro file should include all atoms (water, ice, ions, AND guest molecules). .top file should include guest molecule types and counts."
actual: "Guest molecules (CH4, THF) are NOT included in .gro or .top files when exporting hydrate after ion insertion or hydrate interface"
errors: []
reproduction: "1. Create hydrate via Interface tab (Tab 3) with guest molecules OR 2. Insert ions into hydrate via Ion tab (Tab 4) starting from hydrate interface. 3. Export to GROMACS. 4. Observe that guest molecules are missing from exported .gro/.top files"
started: "Unknown - appears to be missing feature"

## Root Cause
When hydrate is converted to Candidate via to_candidate(), guest info is stored in metadata but NOT passed through interface_builder modes. InterfaceStructure lacked guest molecule positions/data, and the exporter didn't handle guests.

## Fix Applied
1. **types.py**: Added guest_type_counts field to InterfaceStructure and IonStructure
2. **types.py**: Modified to_candidate() to preserve molecule_index in metadata
3. **piece.py, slab.py, pocket.py**: Pass guest_type_counts from candidate metadata to InterfaceStructure
4. **main_window.py**: Propagate guest metadata from interface to ion structure on ion insertion
5. **gromacs_writer.py**: 
   - Added guest detection for hydrate-derived interfaces (is_hydrate_source detection)
   - Fixed guest_start calculation (used wrong boundary for 4-atom ice framework)
   - Added guest molecule writing in write_interface_gro_file
   - Added guest molecule writing in write_ion_gro_file
   - Added guest_type_counts field handling to IonStructure

## Verification
- Test with hydrate-derived interface shows CH4 guests in exported .gro file
- All existing tests pass (64 tests)
- Guest atoms correctly appear at residue 5 with CH4 residue name

## Files Changed
- quickice/structure_generation/types.py: added guest_type_counts field
- quickice/structure_generation/modes/piece.py: pass guest metadata
- quickice/structure_generation/modes/slab.py: pass guest metadata  
- quickice/structure_generation/modes/pocket.py: pass guest metadata
- quickice/gui/main_window.py: propagate guest metadata to ion structure
- quickice/output/gromacs_writer.py: guest detection and writing