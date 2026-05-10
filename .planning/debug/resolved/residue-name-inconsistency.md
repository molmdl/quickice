---
status: resolved
trigger: "residue-name-inconsistency"
created: 2026-05-10T00:00:00Z
updated: 2026-05-10T00:07:00Z
---

## Current Focus

hypothesis: Static ITP template files use 7-char names (CH4_LIQ, THF_LIQ) but GRO writer truncates to 5 chars (CH4_L, THF_L) for GROMACS format compliance
test: Rename moleculetype in ITP templates to 5-char versions to match GRO output
expecting: After renaming ITP templates, GRO and ITP will have consistent names
next_action: COMPLETE - Fix verified and tested

## Symptoms

expected: GRO and ITP should have the same residue name for consistency
actual: GRO file uses CH4_L (truncated to 5 chars for GRO format), but ITP file uses CH4_LIQ. The user prefers using shorter names consistently.
errors: No runtime errors, but inconsistency could cause analysis problems
reproduction: Check files in tmp/test/ - specifically ions_32na_32cl_with_7ch4.gro and ch4_liquid.itp
started: Started when GRO format was fixed to use unique names for analysis

## Eliminated

<!-- APPEND only - prevents re-investigating -->

## Evidence

- timestamp: 2026-05-10T00:01:00Z
  checked: tmp/test/ions_32na_32cl_with_7ch4.gro
  found: GRO file uses residue name "CH4_L" (5 chars) for CH4 solutes
  implication: GRO writer correctly truncates to GROMACS format limit

- timestamp: 2026-05-10T00:01:30Z
  checked: tmp/test/ch4_liquid.itp
  found: ITP file uses moleculetype name "CH4_LIQ" (7 chars) on line 11
  implication: ITP has full 7-char name, inconsistent with GRO

- timestamp: 2026-05-10T00:02:00Z
  checked: quickice/output/gromacs_writer.py line 1547
  found: Code `solute_res_name = solute_res_name[:5]` truncates solute names to 5 chars for GRO
  implication: GRO truncation is intentional and correct for GROMACS format

- timestamp: 2026-05-10T00:02:30Z
  checked: quickice/data/ch4_liquid.itp and thf_liquid.itp
  found: Template ITP files have moleculetype names "CH4_LIQ" (line 11) and "THF_LIQ" (line 13)
  implication: Static ITP templates are the source of the inconsistency

- timestamp: 2026-05-10T00:03:00Z
  checked: quickice/structure_generation/moleculetype_registry.py
  found: Registry generates names like "CH4_LIQ" via register_liquid_solute() method
  implication: Registry uses 7-char names that must be truncated for GRO format

- timestamp: 2026-05-10T00:05:00Z
  checked: Registry and ITP templates after fix
  found: Registry now generates CH4_L and THF_L (5 chars), ITP templates updated to match
  implication: Names are now consistent across all components

- timestamp: 2026-05-10T00:05:30Z
  checked: tests/test_solute_insertion.py
  found: Tests pass with new 5-char names (CH4_L, THF_L)
  implication: Fix is working correctly

- timestamp: 2026-05-10T00:07:00Z
  checked: All components with comprehensive verification
  found: Registry generates 5-char names, ITP templates have matching 5-char names, all tests pass
  implication: Fix is complete and verified

## Resolution

root_cause: MoleculetypeRegistry generates 7-char names (CH4_LIQ, THF_LIQ) but GRO format requires 5-char max. GRO writer truncates names, creating inconsistency with TOP file and ITP templates.
fix: Changed registry to generate 5-char names (CH4_L, THF_L) and updated ITP templates to match. Updated tests and documentation.
verification: All tests pass. Registry generates 5-char names. ITP templates have matching names. Consistency verified across all components.
files_changed:
  - quickice/structure_generation/moleculetype_registry.py (changed _LIQ suffix to _L)
  - quickice/data/ch4_liquid.itp (changed CH4_LIQ to CH4_L)
  - quickice/data/thf_liquid.itp (changed THF_LIQ to THF_L)
  - tests/test_solute_insertion.py (updated assertions)
  - quickice/structure_generation/types.py (updated docstring)
