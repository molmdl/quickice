---
status: resolved
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

hypothesis: "ROOT CAUSE FOUND - write_multi_molecule_top_file() uses wrong molecule counts"
test: "Trace write_multi_molecule_top_file logic for counting molecules"
expecting: "Will find that incorrect counting causes mismatch, and interface export code uses wrong residue mapping"
next_action: "Verify the exact counting logic and implement fix"

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

- timestamp: 2026-04-27
  checked: Fresh hydrate export (hydrate -> export directly)
  found: "GRO SOL=184 lines, CH4=40 lines" vs "TOP SOL=46 molecules, CH4=8 molecules"
  implication: GRO counts ATOMS (lines) × molecules × atoms_per_mol, TOP counts molecules correctly

- timestamp: 2026-04-27
  checked: Full pipeline (hydrate -> interface -> ions -> export)
  found: "GRO SOL=43,858 (should be 13,116)" vs "TOP SOL=4,522 (should be 13,116)"
  implication: BUG - GRO over-counts, TOP under-counts

## Resolution

root_cause: "GRO export writes atoms in GenIce2 output order (H first), but .itp defines atoms in GAFF order (C first for ch4, O first for thf). When writing CH4/GUEST molecules, the atom order in the exported .gro file doesn't match the atom order defined in the corresponding .itp file."
fix: "Add atom reordering in write_multi_molecule_gro_file() to match ITP canonical order:
  - CH4: reorder to C, H, H, H, H (not H, H, H, H, C)
  - THF: reorder to O, CA, CA, CB, CB, H... (not H, H... O first)
  Add helper function to reorder guest atoms to canonical ITP order."
verification: "After fix, GRO atom sequence matches .itp [atoms] section order"
files_changed: ["quickice/output/gromacs_writer.py"]