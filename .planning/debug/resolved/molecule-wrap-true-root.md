---
status: resolved
trigger: "Investigate 2 persistent issues: (1) Incomplete molecules in unit cell (THF and CH4), (2) THF box doesn't bound all molecules"
created: 2026-04-17T18:36:00
updated: 2026-04-17T18:36:00
---

## Current Focus
FIXED AND VERIFIED

## Symptoms
expected:
  - Issue 1: All molecules complete with all atoms
  - Issue 2: All THF molecules within unit cell box
actual:
  - Issue 1: Incomplete molecules with missing atoms
  - Issue 2: THF molecules outside unit cell box
reproduction: "Generate THF hydrate, observe at edges"
started: "Persistent issue across multiple fix attempts"

## Eliminated
- hypothesis: "Wrapping logic is broken"
  evidence: "Wrapping works correctly - all atoms within [0,L), molecules intact"
  timestamp: 2026-04-17

## Evidence
- timestamp: 2026-04-17
  checked: "Wrapping logic behavior"
  found: "Wrapping logic works correctly - positions within [0,L) after wrapping, molecules kept intact"
  implication: "Issue is NOT in wrapping logic itself"

- timestamp: 2026-04-17
  checked: "GenIce2 options for supercell"
  found: "NO --rep option is generated! _build_genice_options ignores supercell_x/y/z completely"
  implication: "ROOT CAUSE FOUND: Supercell settings ignored - GenIce2 always generates single unit cell"

- timestamp: 2026-04-17
  checked: "Fix applied - added --rep option"
  found: "--rep option now passed to GenIce2, supercell generation works correctly"
  implication: "2x2x2 supercell now generates 432 molecules (vs 54), box is 2.4nm (vs 1.2nm)"

## Resolution
root_cause: "_build_genice_options() did NOT pass --rep option to GenIce2, so supercell settings were completely ignored. GenIce2 always generated single unit cell regardless of supercell config, resulting in box being too small to contain all molecules."
fix: "Added --rep option to _build_genice_options() to pass supercell_x/y/z to GenIce2 CLI. This ensures supercell generation works correctly."
verification: "306/307 tests pass (1 pre-existing unrelated failure). Verified: 2x2x2 supercell now has 432 molecules (8x54), cell size 2x larger (2.4nm vs 1.2nm), all atoms within [0,L), no molecules span cell boundaries."
files_changed: ["quickice/structure_generation/hydrate_generator.py"]