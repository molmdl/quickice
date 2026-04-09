---
status: resolved
trigger: "HIGH-08 density-unit-conversion - Density calculation assumes positions in nm without validation"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:20:00Z
---

## Current Focus
hypothesis: Root cause confirmed - density_score assumes nm units without validation, creating risk if non-nm coordinates are passed
test: Verify no existing code paths read coordinates in Å, confirm fix approach
expecting: Find that main code path is safe, but fix is needed for robustness
next_action: Search for any coordinate file readers, then implement fix

## Symptoms
expected: Density calculation should validate input units or convert explicitly
actual: Assumes positions in nm, but if Angstrom passed, density wrong by factor of 1000
errors: Incorrect density score for ranking candidates
reproduction: Pass positions in Angstrom instead of nm to scorer
started: Always assumed nm without validation

## Eliminated
<!-- Nothing yet -->

## Evidence
- timestamp: 2026-04-09T00:01:00Z
  checked: scorer.py lines 158-171 (density_score function)
  found: Code calculates volume_nm3 = det(candidate.cell) and converts to cm³ with 1e-21 factor, but has NO validation that cell is actually in nm
  implication: If cell is in Å, volume would be 1000x larger than assumed (1 nm³ = 1000 Å³), leading to density being 1000x too small

- timestamp: 2026-04-09T00:02:00Z
  checked: types.py Candidate and InterfaceConfig dataclasses
  found: Documentation explicitly states positions and cell are in nm (lines 14-16, 63-71), but NO runtime validation exists
  implication: The nm convention is documented but not enforced - any code passing Å coordinates would silently produce incorrect results

- timestamp: 2026-04-09T00:03:00Z
  checked: generator.py lines 138-197 (_parse_gro method)
  found: GenIce outputs GRO format with coordinates in nm (GROMACS standard), _parse_gro correctly extracts positions and cell in nm
  implication: The MAIN code path (GenIce) produces correct nm coordinates, but the issue is that density_score lacks validation for alternative input paths

- timestamp: 2026-04-09T00:04:00Z
  checked: pdb_writer.py lines 53-66 (write_pdb_with_cryst1)
  found: PDB writer converts from nm to Å by multiplying by 10.0, confirming internal representation is in nm
  implication: Codebase consistently uses nm internally, converts to Å only for PDB output

- timestamp: 2026-04-09T00:05:00Z
  checked: water_filler.py lines 21-77 (load_water_template)
  found: TIP4P water template (tip4p.gro) is read in nm, same GRO format as GenIce
  implication: ALL coordinate inputs in the codebase use nm (GenIce, tip4p.gro), no existing code path introduces Å coordinates

- timestamp: 2026-04-09T00:10:00Z
  checked: tests/test_ranking.py after implementing fix
  found: All 36 ranking tests pass, including new unit validation tests. 2 pre-existing test failures in test_structure_generation.py (unrelated to density fix).
  implication: Fix works correctly, no regression introduced.

## Resolution
root_cause: density_score() in scorer.py (lines 158-171) hardcodes conversion factor 1e-21 for nm³ to cm³ without validating that input coordinates are actually in nm. The codebase convention is nm units (documented in types.py), GenIce outputs nm, all coordinate inputs use nm, but density_score has no runtime validation. If Å coordinates were passed, density would be wrong by factor of 1000.
fix: Added validation in density_score() (lines 171-179) to check if calculated density is in reasonable range (0.1-10.0 g/cm³). If density is outside this range, raises ValueError with helpful message explaining that coordinates must be in nm, not Å. Added two new tests: test_density_score_rejects_angstrom_units validates the error is raised for Å coordinates, test_density_score_accepts_valid_nm_units confirms normal nm coordinates work.
verification: Manual test confirmed: (1) nm coordinates with density 1.2 g/cm³ pass validation, (2) Å coordinates with density 0.0012 g/cm³ fail with clear error message. All 36 ranking tests pass including new unit validation tests. No regression introduced.
files_changed: [quickice/ranking/scorer.py, tests/test_ranking.py]
