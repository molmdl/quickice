---
status: resolved
trigger: "AttributeError when trying to set atom color mode in VTK molecule mapper"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:00:02Z
---

## Current Focus

hypothesis: CONFIRMED - VTK 9.5.2 changed API for atom color mode
test: Applied fix using mapper.SetAtomColorMode(mapper.SingleColor)
expecting: Code should work with VTK 9.5.2
next_action: Archive session

## Symptoms

expected: VTK should render molecules with single color for each phase
actual: AttributeError: 'vtkOpenGLMoleculeMapper' object has no attribute 'SetAtomColorModeToSingleColor'
errors: AttributeError at interface_viewer.py:178 - Did you mean: 'SetBondColorModeToSingleColor'?
reproduction: Run GUI via SSH, generate interface structure, view in tab 1
started: Regression in VTK API or compatibility issue

## Eliminated

## Evidence

- timestamp: 2026-04-09T00:00:00Z
  checked: Initial error message
  found: Error suggests SetBondColorModeToSingleColor exists but SetAtomColorModeToSingleColor does not
  implication: Either API changed or atom color mode works differently

- timestamp: 2026-04-09T00:00:01Z
  checked: VTK version and available methods on vtkMoleculeMapper
  found: VTK 9.5.2 - SetAtomColorMode() requires integer constant, not convenience method. mapper.SingleColor = 0, mapper.DiscreteByAtom = 1
  implication: VTK API inconsistency - bonds have SetBondColorModeToSingleColor() convenience method, but atoms only have SetAtomColorMode(int)

- timestamp: 2026-04-09T00:00:01Z
  checked: Tested correct API: mapper.SetAtomColorMode(mapper.SingleColor)
  found: Works correctly! This is the proper VTK 9.5.2 API
  implication: Fix is straightforward - replace method call with correct syntax

## Resolution

root_cause: VTK 9.5.2 API changed - SetAtomColorModeToSingleColor() convenience method does not exist for atoms. Must use SetAtomColorMode(mapper.SingleColor) instead. This is an API inconsistency where bonds have a convenience method but atoms do not.
fix: Changed line 178 in interface_viewer.py from mapper.SetAtomColorModeToSingleColor() to mapper.SetAtomColorMode(mapper.SingleColor) with explanatory comment about VTK 9.5+ API.
verification: Tested the fix by importing the module and verifying the API call works correctly. Module imports successfully. All interface-related tests pass.
files_changed: [quickice/gui/interface_viewer.py]
