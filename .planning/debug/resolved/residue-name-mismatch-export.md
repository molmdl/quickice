---
status: verifying
trigger: "Residue name in exported files doesn't match the itp definition"
created: 2026-04-27T00:00:00Z
updated: 2026-04-27T00:00:00Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: ".itp files have residue name 'MOL' but .gro writer uses 'CH4'/'THF'. The .top file references CH4/THF but .gro uses different residue, causing mismatch."
test: "Compare residue names in generated .gro file and .itp files directly"
expecting: ".gro will have CH4/THF, .itp will have MOL"
next_action: "Apply fix: Update .itp files to use CH4/THF instead of MOL for residue names"

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: Residue name in exported .gro file should match the residue name defined in the corresponding .itp file
actual: Residue name differs between .gro and .itp files
errors: None
reproduction: 
  1. Generate hydrate with guest (e.g., CH4)
  2. Generate interface
  3. Insert ion
  4. Export GROMACS files
  5. Compare residue names in .gro vs .itp - they don't match

## Eliminated
<!-- APPEND only - prevents re-investigation -->

- none yet

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: "2026-04-27T00:05:00Z"
  checked: "ch4.itp moleculetype and residue name"
  found: "moleculetype is 'ch4' but residue name in [atoms] is 'MOL'"
  implication: "Mismatch with .gro file which uses 'CH4' as residue name"
- timestamp: "2026-04-27T00:05:00Z"
  checked: "thf.itp moleculetype and residue name"
  found: "moleculetype is 'thf' but residue name in [atoms] is 'MOL'"
  implication: "Mismatch with .gro file which uses 'THF' as residue name"

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: ".itp files had residue name 'MOL' but .gro writer used 'CH4'/'THF' from MOLECULE_TO_GROMACS mapping"
fix: "Updated ch4.itp and thf.itp to use correct residue names (CH4, THF)"
verification: "Verified ch4.itp and thf.itp now use CH4/THF residue names matching .gro file writer"
files_changed: ["quickice/data/ch4.itp", "quickice/data/thf.itp"]