---
status: investigating
trigger: "atom order mismatch gro vs top"
created: 2026-04-27T00:00:00Z
updated: 2026-04-27T00:00:00Z
---

## Current Focus

hypothesis: "Interface export (write_interface_gro_file) may reorder molecules differently than the topology expects"
test: "Trace full pipeline: hydrate generation -> interface -> ion insertion -> export"
expecting: "Confirm whether ion insertion or interface building causes molecule reordering"
next_action: "Test exact reproduction path: hydrate->interface->ion insertion->GROMACS export"
---

## Current Focus

hypothesis: "ROOT CAUSE FOUND: Ion insertion rebuilds molecule_index in wrong order"
test: "Check ion_inserter.replace_water_with_ions() molecule_index construction"
expecting: "Ion insertion creates water first, but guests should be preserved in separate section"
next_action: "Verify molecule_index construction in ion_inserter and trace export flow"

## Symptoms

expected: Atom order in .gro should match atom order definitions in .top/.itp files
actual: Atoms appear in different order between .gro and .top
errors: GROMACS may error or produce incorrect results
reproduction: 
  1. Generate hydrate with guest
  2. Generate interface
  3. Insert ion
  4. Export GROMACS
  5. Compare atom order in .gro file vs .top/.itp file - they don't match
started: Unknown

## Eliminated

## Evidence

## Resolution

root_cause: 
fix: 
verification: 
files_changed: []