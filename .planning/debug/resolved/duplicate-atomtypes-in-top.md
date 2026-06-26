---
status: resolved
trigger: "duplicate-atomtypes-in-top"
created: 2026-06-26T00:00:00Z
updated: 2026-06-26T00:00:03Z
---

## Current Focus

hypothesis: CONFIRMED - CH4 and THF atomtype blocks write independently without dedup, causing `hc` to appear twice. `_written_atomtypes` is initialized AFTER the CH4/THF blocks, so it's useless for dedup between them.
test: Read gromacs_writer.py - confirmed in 4 functions
expecting: Found exact root cause in all affected functions
next_action: Implement centralized GAFF2 atomtype definitions and dedup logic in all affected write functions

## Symptoms

expected: Each atomtype name should appear exactly ONCE in the [ atomtypes ] section of the .top file
actual: atomtype `hc` appears twice in tmp/e2e_6/solute_thf_14molecules.top (line 18 from CH4, line 22 from THF)
errors: GROMACS grompp warns about duplicate atomtype definitions. Currently safe because parameters match, but would break if custom molecule defined `hc` with different parameters.
reproduction: Run e2e workflow 6 (hydrate + custom mol + THF solute). Exported .top at tmp/e2e_6/solute_thf_14molecules.top shows the duplicate.
started: Present since combined solute+custom+molecule topology export was implemented

## Eliminated

## Evidence

- timestamp: 2026-06-26T00:00:00Z
  checked: User-reported evidence from exported .top file
  found: `hc` atomtype appears twice (CH4 block line 18, THF block line 22). `c3`/`c5` have different names so no collision. `_written_atomtypes` set exists but only used for custom molecule dedup.
  implication: Root cause is clear - CH4/THF blocks write unconditionally without checking _written_atomtypes

- timestamp: 2026-06-26T00:00:01Z
  checked: gromacs_writer.py lines 1855-1872, 1342-1365, 2258-2282, 2793-2820
  found: 4 functions have the same pattern: (1) write_ion_top_file (L1855), (2) write_multi_molecule_top_file (L1342), (3) write_custom_molecule_top_file (L2258), (4) write_solute_top_file (L2793). In ALL four, _written_atomtypes is initialized AFTER the CH4/THF blocks, making it useless for dedup between them. write_interface_top_file (L1046) uses elif for guest types so only one guest type written - not affected.
  implication: Fix must: (1) move _written_atomtypes init before GAFF2 blocks, (2) check before writing each atomtype, (3) for custom mol atomtypes compare params and error if mismatch

## Resolution

root_cause: In gromacs_writer.py, the CH4 and THF atomtype blocks write their atomtype lines unconditionally without checking if an atomtype name has already been written. The `_written_atomtypes` dedup set exists but is initialized AFTER the CH4/THF blocks, so it only protects the custom molecule atomtype block from duplicates with the built-in ones, NOT the built-in ones from each other. This causes `hc` (shared between CH4 and THF GAFF2) to appear twice when both molecule types are present.
fix: (1) Centralized GAFF2 atomtype definitions in module-level GAFF2_ATOMTYPES/WATER_ATOMTYPES/ION_ATOMTYPES dicts and CH4/THF/CO2/H2_ATOMTYPE_NAMES lists, (2) Added _format_atomtype_line() and _format_custom_atomtype_line() helpers, (3) Added _write_atomtypes_block() that writes GAFF2 blocks with dedup via a _written_atomtypes dict, (4) Added _check_custom_atomtype_conflict() and _lj_params_match() for custom molecule param comparison, (5) Modified write_ion_top_file, write_multi_molecule_top_file, write_interface_top_file, write_custom_molecule_top_file, and write_solute_top_file to use centralized definitions and dedup logic, (6) Added TestDEDUP01 regression tests (5 tests) in test_scancode_bugs_gromacs.py
verification: All 129 existing tests pass. 5 new DEDUP01 regression tests pass. Manual verification of exported .top file shows hc appears exactly once when both CH4 and THF are present.
files_changed: [quickice/output/gromacs_writer.py, tests/test_scancode_bugs_gromacs.py]
