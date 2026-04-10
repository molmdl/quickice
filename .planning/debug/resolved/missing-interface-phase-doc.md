---
status: verifying
trigger: "Debug Issue 2: Missing doc on unsupported phase in interface"
created: 2026-04-10T00:00:00Z
updated: 2026-04-10T00:10:00Z
---

## Current Focus

hypothesis: Documentation added to README.md and gui-guide.md
test: Verify documentation is clear and accurate
expecting: Users will now understand which phases support interface generation
next_action: Verify documentation quality and completeness

## Symptoms

expected: Clear documentation about which ice phases are supported/not supported for interface generation
actual: Documentation missing, users may encounter errors without explanation
errors: Users don't know which phases work with interface mode
reproduction: Try to use unsupported phase for interface generation
started: Unknown - needs investigation

## Eliminated

<!-- APPEND only - prevents re-investigating -->

## Evidence

- timestamp: 2026-04-10T00:02:00Z
  checked: interface_builder.py lines 119-130
  found: Triclinic cell validation with error message mentioning "Affected phases include: ice_ii, ice_v"
  implication: Code correctly detects triclinic cells and provides error message

- timestamp: 2026-04-10T00:03:00Z
  checked: piece.py, pocket.py, slab.py (all modes)
  found: All three interface mode files have identical triclinic validation logic
  implication: Limitation applies to ALL interface modes (slab, pocket, piece)

- timestamp: 2026-04-10T00:03:30Z
  checked: README.md lines 207-224
  found: Lists 8 supported ice phases (Ih, Ic, II, III, V, VI, VII, VIII) for ice generation, no mention of interface limitations
  implication: Users think all 8 phases work for interface generation, but only orthogonal cell phases do

- timestamp: 2026-04-10T00:04:00Z
  checked: docs/gui-guide.md lines 196-252
  found: Interface mode documentation doesn't mention phase compatibility or cell type requirements
  implication: No guidance for users about which candidates they can use in Tab 2

- timestamp: 2026-04-10T00:05:00Z
  checked: User workflow
  found: Users can successfully generate ice_ii and ice_v candidates in Tab 1, then fail in Tab 2
  implication: Wasted user time - they generate candidates they cannot use for interfaces

## Resolution

<!-- OVERWRITE as understanding evolves -->

root_cause: Documentation gap - README.md and gui-guide.md don't explain that interface generation requires orthogonal cells, which excludes ice_ii (rhombohedral) and ice_v (monoclinic) phases. Users can generate these candidates in Tab 1 but cannot use them for interface construction in Tab 2.
fix: Added documentation to README.md (lines 226-230) and gui-guide.md (lines 211-222) clarifying which phases support interface generation. README.md now has "Interface Construction Limitation" note after the Supported Ice Phases table. gui-guide.md now has "Phase Compatibility" section in the Interface Construction chapter explaining compatible vs incompatible phases.
verification: Pending - need to verify documentation is clear and addresses user confusion
files_changed: [README.md, docs/gui-guide.md]
