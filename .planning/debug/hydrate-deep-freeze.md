---
status: investigating
trigger: "DEEP DEBUG: Hydrate→interface generation still frozen - trace BOTH builder AND viewer"
created: 2026-04-23T12:00:00
updated: 2026-04-23T12:10:00
---

## Current Focus
**hypothesis:** Unknown - need to trace WHERE exactly it hangs
**test:** Added debug print statements throughout the code path
**expecting:** Will see print output showing where execution stops
**next_action:** Run GUI and observe where output stops

## Symptoms
**expected:** Interface generation completes in seconds, 3D viewer shows structure
**actual:** Hangs indefinitely at "Generating interface..." with no error
**errors:** None - silent hang
**reproduction:** Click Generate button → progress bar → frozen forever
**started:** Unknown - reported as persistent issue

## Eliminated
<!-- APPEND as hypotheses are disproven -->

## Evidence
<!-- APPEND after each finding -->
- timestamp: 2026-04-23T12:10:00
  checked: Code flow analysis and debug print insertion
  found: |
    Added debug prints to:
    - workers.py: InterfaceGenerationWorker.run()
    - interface_builder.py: generate_interface()
    - slab.py: assemble_slab()
    - water_filler.py: tile_structure(), fill_region_with_water()
    - viewmodel.py: _on_interface_finished()
    - main_window.py: _on_interface_generation_complete()
    - interface_viewer.py: set_interface_structure()
  implication: Will see exactly where execution stops

## Debug Print Locations
```
workers.py:          START run(), before/after generate_interface(), finished signal
interface_builder.py: START generate_interface(), validation, mode routing
slab.py:             START/END assemble_slab(), candidate info
water_filler.py:     START/END tile_structure(), fill_region_with_water()
viewmodel.py:         _on_interface_finished signal handling
main_window.py:       _on_interface_generation_complete handler
interface_viewer.py:  set_interface_structure START/END, guest detection
```

## Resolution
**root_cause:** 
**fix:**
**verification:**
**files_changed:**
- quickice/gui/workers.py (added debug prints)
- quickice/structure_generation/interface_builder.py (added debug prints)
- quickice/structure_generation/modes/slab.py (added debug prints)
- quickice/structure_generation/water_filler.py (added debug prints)
- quickice/gui/viewmodel.py (added debug prints)
- quickice/gui/main_window.py (added debug prints)
- quickice/gui/interface_viewer.py (added debug prints)