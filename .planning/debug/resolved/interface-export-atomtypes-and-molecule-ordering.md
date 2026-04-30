---
status: resolved
trigger: "Interface export has two remaining issues: (1) topology uses CH4 atomtypes instead of THF atomtypes, (2) SOL molecules are split into two groups instead of being contiguous."
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
---

## Current Focus

hypothesis: (1) write_interface_top_file() hardcodes CH4 atomtypes instead of detecting guest type, (2) slab.py combines positions as ice→guest→water which causes SOL molecules to be split
test: Fix write_interface_top_file() to detect guest type like write_ion_top_file() does. Fix slab.py to combine positions as ice→water→guest so all SOL are together
expecting: After fixes: atomtypes will show THF types for THF guests, molecules will be ordered as SOL then THF
next_action: Apply fixes to gromacs_writer.py and slab.py

## Symptoms

expected: 
1. Interface topology should have THF atomtypes (os, c5, hc, h1) not CH4 atomtypes (c3, hc)
2. Interface GRO and TOP should have molecules ordered as: SOL (all water), THF (all guest) - NOT SOL -> THF -> SOL

actual:
1. Interface topology shows CH4 atomtypes (c3, hc) in [ atomtypes ] section despite THF being the guest
2. Interface GRO and TOP have molecules split: "SOL 4780, THF 712, SOL 2432" instead of grouped together

errors: No explicit errors, but wrong atomtypes will cause GROMACS simulation failures

reproduction:
- Generate THF sII hydrate
- Export to interface tab
- GROMACS export to tmp/slab/
- Check interface_slab.top [ atomtypes ] section - shows c3, hc (CH4) instead of os, c5, hc, h1 (THF)
- Check interface_slab.top [ molecules ] section - shows SOL split into two groups
- Check interface_slab.gro - molecules also split

started: Current issue, remaining from previous debug session

## Eliminated

## Evidence

- timestamp: Initial
  checked: Provided evidence
  found: interface_slab.top has CH4 atomtypes (c3, hc) instead of THF atomtypes (os, c5, hc, h1)
  implication: Atomtypes generation is using wrong guest type or hardcoded CH4

- timestamp: Initial
  checked: Provided evidence
  found: Molecules ordered as SOL 4780, THF 712, SOL 2432 instead of contiguous groups
  implication: Molecule ordering logic is splitting SOL into two groups

- timestamp: Investigation
  checked: gromacs_writer.py lines 820-826
  found: write_interface_top_file() HARDCODES CH4 atomtypes unconditionally when guest_atom_count > 0. No guest type detection.
  implication: ROOT CAUSE #1: Atomtypes are hardcoded to CH4, never detecting actual guest type

- timestamp: Investigation
  checked: gromacs_writer.py lines 1377-1388 (write_ion_top_file)
  found: write_ion_top_file() correctly detects guest_type and writes appropriate atomtypes (ch4 or thf)
  implication: Correct pattern exists in codebase, just needs to be applied to write_interface_top_file

- timestamp: Investigation
  checked: slab.py lines 577-599
  found: Positions combined as: ice → guest → water. Comment says "guests (in water region)" but they're actually in ICE regions (bottom+top)
  implication: ROOT CAUSE #2: Position concatenation order causes GRO file to have ice SOL → guest → water SOL, splitting SOL into two groups

- timestamp: Investigation
  checked: gromacs_writer.py lines 850-886 (write_interface_top_file molecules section)
  found: Writes ice SOL count, then guest count, then water SOL count - matching position order from slab.py
  implication: Both GRO and TOP have wrong order. Need to reorder positions in slab.py to ice→water→guest so all SOL are contiguous

## Resolution

root_cause: Two separate bugs:
1. write_interface_top_file() hardcodes CH4 atomtypes (lines 820-826) instead of detecting guest type like write_ion_top_file() does
2. slab.py concatenates positions as ice→guest→water (lines 577-599), causing SOL molecules to be split into ice SOL and water SOL in GRO/TOP output

fix: 
1. Added guest type detection to write_interface_top_file() using detect_guest_type_from_atoms() and write appropriate atomtypes based on guest type (ch4, thf, co2, h2)
2. Reordered position concatenation in slab.py to ice→water→guest so all SOL molecules are contiguous in GRO file
3. Updated write_interface_gro_file() to write atoms in new order (ice→water→guest) and updated write_interface_top_file() to match

verification: 
1. Generated THF sII hydrate and exported to interface slab
2. Checked TOP file atomtypes section - shows THF atomtypes (os, c5, hc, h1) ✓
3. Checked GRO file molecule ordering - shows all 3555 SOL contiguous, then 300 THF ✓
4. Checked TOP file molecules section - shows "SOL 3555, THF 300" (correct grouped order) ✓

files_changed:
- quickice/output/gromacs_writer.py: Fixed atomtypes detection, #include directive, molecule ordering
- quickice/structure_generation/modes/slab.py: Fixed position concatenation order
