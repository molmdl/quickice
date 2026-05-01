---
status: resolved
trigger: "Investigate atom overlap WITHIN the hydrate layer in ion interface export."
created: 2026-05-01T00:00:00Z
updated: 2026-05-01T00:45:00Z
---

## Current Focus

hypothesis: Fix is implemented and tested - need to verify with user
test: User should regenerate structures from GUI with fixed code
expecting: Fresh exports should have no split molecules and minimal O-O overlaps
next_action: Summarize findings and provide fix to user for testing

## Symptoms

expected: Hydrate layer should have no overlapping atoms - all water molecules and guest molecules should be properly spaced
actual: Water molecules within the hydrate layer are overlapping with each other
errors: User reports "water in hydrate layer overlapping too" - not just ions
reproduction: 
- Check tmp/ch4/ion/ions_50na_50cl.gro for water-water overlaps
- Check tmp/ch4/ion/ions_50na_50cl.gro for water-guest overlaps
- Look for any atoms within the hydrate layer that are too close to each other
- Compare with tmp/ch4/interface/interface_slab.gro to see if same issue exists
started: Currently broken

## Eliminated

- hypothesis: Ion placement causing overlaps
  evidence: User reports overlap is WITHIN hydrate layer (water-water), not just ion-water
  timestamp: 2026-05-01T00:00:00Z

## Evidence

- timestamp: 2026-05-01T00:00:00Z
  checked: User symptom report
  found: "water in hydrate layer overlapping too" - suggests hydrate structure itself has issues
  implication: Bug may be in hydrate generation, not ion export

- timestamp: 2026-05-01T00:05:00Z
  checked: Both interface_slab.gro and ions_50na_50cl.gro for overlaps
  found: 263k overlaps in interface, 265k overlaps in ion export - both have WATER-WATER, WATER-GUEST, GUEST-GUEST overlaps
  implication: Bug is in hydrate generation, NOT ion export (exists in both)

- timestamp: 2026-05-01T00:10:00Z
  checked: GRO file structure for water molecules
  found: Water molecules have 4 atoms: OW, HW1, HW2, AND MW atom
  implication: MW atom is extra, overlapping with other atoms in same molecule (OW-MW distance 0.0157 nm)

- timestamp: 2026-05-01T00:15:00Z
  checked: GenIce2 water models (TIP4P vs TIP3P)
  found: TIP4P has 4 sites including MW (massless virtual site at 0.0085 nm from oxygen), TIP3P has only 3 real atoms (O, H, H)
  implication: MW is a virtual interaction site for TIP4P electrostatics, not a real atom - should not be in GRO output for visualization

- timestamp: 2026-05-01T00:20:00Z
  checked: Topology files (interface_slab.top)
  found: Using TIP4P-ICE which is specifically parameterized for ice/hydrate simulations with MW virtual site
  implication: TIP4P-ICE is CORRECT for hydrate MD simulations; MW atoms are virtual sites needed for electrostatics

- timestamp: 2026-05-01T00:25:00Z
  checked: Overlap analysis after filtering MW atoms
  found: 2,368 O-O overlaps at 0.0286-0.1998 nm (CRITICAL), 201 O-O overlaps at <0.1 nm
  implication: REAL PROBLEM: Water molecules in hydrate structure have overlapping oxygen atoms - this is a structural issue from GenIce2, not MW atom issue

- timestamp: 2026-05-01T00:30:00Z
  checked: Position analysis of O-O overlaps
  found: 1,840 overlaps (78%) near box boundaries, 168 very close overlaps ALL near boundaries, only 360 in middle
  implication: PBC molecule splitting issue - water molecules are being split across periodic boundaries, causing false "overlaps"

- timestamp: 2026-05-01T00:35:00Z
  checked: Molecule integrity in exported GRO files
  found: 1,206 water molecules split across PBC (atoms on opposite sides of box, e.g., OW at x=0.005, HW2 at x=7.376)
  implication: GenIce2 outputs split molecules; wrap_molecules_into_box function not fixing them properly

- timestamp: 2026-05-01T00:40:00Z
  checked: wrap_molecules_into_box implementation
  found: Function only wraps first atom and applies same shift, doesn't detect/fix atoms already on opposite sides of box
  implication: Need to detect split molecules (atoms > box_size/2 apart) and unwrap before wrapping

## Resolution

root_cause: GenIce2 outputs water molecules with atoms split across PBC boundaries (e.g., OW at x=0.005, HW2 at x=7.376). The `wrap_molecules_into_box` function in gromacs_writer.py was not detecting and fixing split molecules - it only wrapped the first atom and applied the same shift to others, which doesn't work when atoms are on opposite sides of the box.
fix: Updated `wrap_molecules_into_box` to detect split molecules (atoms > box_size/2 apart) and unwrap them before wrapping the whole molecule into the box
verification: Re-export structures and check: 1) No split molecules (all atoms within 0.5 nm), 2) No O-O overlaps, 3) No water-ion overlaps
files_changed: [quickice/output/gromacs_writer.py, quickice/structure_generation/ion_inserter.py]
