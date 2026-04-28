---
status: resolved
trigger: "gro-top-order-mismatch: Guest molecule order doesn't match between .gro and .top files. .top has SOL first but .gro has guest first."
created: 2026-04-28T00:00:00Z
updated: 2026-04-28T00:30:00Z
---

## Current Focus
hypothesis: FIXED - write_ion_top_file() now writes [molecules] section in same order as write_ion_gro_file()
test: Code review complete
expecting: .gro and .top files now have matching molecule order
next_action: Archive debug session

## Symptoms
expected: Molecule order in .gro should match .top - same sequence of residues
actual: .top has SOL (water) first, but .gro has guest molecules first
errors: None specifically, but GROMACS may misbehave
reproduction:
  1. Generate hydrate with guest
  2. Generate interface
  3. Insert ion
  4. Export GROMACS
  5. Compare molecule order in .gro vs .top - they don't match
started: Unknown

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-28T00:00:00Z
  checked: Debug file created with pre-filled symptoms
  found: Issue is that .top has SOL first but .gro has guest first - order mismatch
  implication: The write_ion_gro_file() and write_ion_top_file() functions are writing molecules in different orders

- timestamp: 2026-04-28T00:15:00Z
  checked: gromacs_writer.py write_ion_gro_file() (lines 1125-1266) and write_ion_top_file() (lines 1269-1339)
  found: |
    write_ion_gro_file() iterates over molecule_index in order and writes atoms.
    write_ion_top_file() hardcodes [molecules] section:
    - Line 1334: SOL (water_count) - always FIRST
    - Line 1336-1337: guest_res_name (guest_count) - if guests present
    - Line 1338: NA (na_count)
    - Line 1339: CL (cl_count)
  implication: The .top file [molecules] order is SOL->guest->NA->CL, but .gro file follows molecule_index order

- timestamp: 2026-04-28T00:20:00Z
  checked: ion_inserter.py _build_molecule_index_from_structure() (lines 60-132)
  found: |
    molecule_index is built in this order:
    1. Ice molecules (if any) - lines 97-104
    2. Guest molecules (if any) - lines 108-119
    3. Water molecules - lines 123-130
    Then in insert_ions(), NA and CL are appended to molecule_index (lines 322-339)
  implication: |
    Final molecule_index order is: ice, guest, water, na, cl
    But .top [molecules] section order is: SOL (water), guest, NA, CL
    MISMATCH: water comes before guest in .top but after guest in .gro!

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: write_ion_top_file() hardcoded the [molecules] section order as SOL (water) first, then guest, NA, CL. But write_ion_gro_file() writes molecules in molecule_index order. The molecule_index is built by _build_molecule_index_from_structure() in order: ice, guest, water, (then na, cl are appended by insert_ions()). This caused .top to say SOL is first, but .gro had guest molecules first.

fix: Modified write_ion_top_file() to iterate over molecule_index and group consecutive molecules of the same type. This ensures the [molecules] section order matches the actual order in the .gro file. The function now properly handles cases where ice and water both map to SOL but may be in different groups.

verification: Code review confirms the fix properly groups consecutive molecules and writes them in molecule_index order.

files_changed:
  - quickice/output/gromacs_writer.py: Modified write_ion_top_file() to write [molecules] section in molecule_index order
