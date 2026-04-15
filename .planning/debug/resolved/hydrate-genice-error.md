---
status: resolved
trigger: "AttributeError: module 'genice2' has no attribute 'GenIce'"
created: 2026-04-16T00:00:00
updated: 2026-04-16T00:00:00
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: FIXED - Import statement assigns GenIce CLASS to `_genice_module`, but code tries to access `_genice_module.GenIce` (expecting a MODULE)
test: Verified module import and GenIce access works correctly
expecting: Hydrate generation should now work
next_action: Done

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: GenIce2 should generate hydrate structures via hydrate_generator.py
actual: AttributeError: module 'genice2' has no attribute 'GenIce'
errors:
  - "AttributeError: module 'genice2' has no attribute 'GenIce'"
reproduction: User tries to generate hydrate structure via Tab 2 - Hydrate Config
started: Recent code change attempted fix but incomplete

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-16
  checked: hydrate_generator.py lines 33-37 and 149
  found: |
    Line 36-37: 
      from genice2.genice import GenIce as GenIce2
      self._genice_module = GenIce2  # Assigns CLASS to _genice_module
    
    Line 149:
      genice = self._genice_module.GenIce  # Tries to access GenIce ATTRIBUTE on CLASS
  implication: |
    self._genice_module is now the GenIce CLASS, not a module.
    Accessing .GenIce on the class fails because it's not an attribute.

- timestamp: 2026-04-16
  checked: generator.py lines 11-12 and 111 for comparison
  found: |
    Line 11-12: from genice2.plugin import safe_import
                from genice2.genice import GenIce
    
    Line 111: ice = GenIce(...)  # Uses class directly
  implication: |
    generator.py imports and uses GenIce as a class directly.
    hydrate_generator.py tried to store the class in a variable meant for a module.

- timestamp: 2026-04-16
  checked: Post-fix verification
  found: |
    - _genice_module type: <class 'module'>
    - _genice_module has GenIce: True
    - GenIce type: <class 'type'>
  implication: Fix verified working

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: |
  Import statement in hydrate_generator.py._ensure_genice_import() was importing 
  the GenIce CLASS, not the genice MODULE. The variable self._genice_module 
  was assigned the class itself, but line 149 expected it to be a module with 
  a GenIce attribute.

fix: |
  Changed from:
    from genice2.genice import GenIce as GenIce2
    self._genice_module = GenIce2
  
  To:
    import genice2.genice as genice_lib
    self._genice_module = genice_lib

verification: |
  - Module imports successfully
  - _genice_module is type <class 'module'>
  - GenIce class accessible via _genice_module.GenIce
  - All 57 structure_generation tests pass
files_changed:
  - quickice/structure_generation/hydrate_generator.py (2 lines changed in _ensure_genice_import)
