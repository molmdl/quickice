---
status: verifying
trigger: "IonPanel charge warning never triggers for non-neutral custom molecules"
created: 2026-06-26T00:00:00Z
updated: 2026-06-26T00:10:00Z
---

## Current Focus

hypothesis: CONFIRMED AND FIXED
test: Run full test suite + specific charge calculation tests
expecting: All tests pass, charge warning works for non-neutral custom molecules
next_action: Final verification with full test suite

## Symptoms

expected: When Custom Molecule source is selected and custom molecule has non-neutral charge, Ion tab should show warning like "Charge: +0.85 (non-neutral)"
actual: Charge warning label is never visible because get_total_charge() always returns 0.0
errors: No errors, silent failure — deferred feature never implemented
reproduction: 1) Generate interface, 2) Upload na_single.gro/na_single.itp in Custom tab, 3) Generate custom molecules, 4) Switch to Ion tab, 5) Select "Custom Molecule" source — no charge warning
started: Phase 34.1 — feature explicitly deferred

## Eliminated

## Evidence

- timestamp: 2026-06-26T00:00:30Z
  checked: ion_panel.py get_total_charge() (line 445-475)
  found: Always returns 0.0 — ion pairs are neutral by design, custom molecule charge explicitly deferred
  implication: get_total_charge() needs to compute custom molecule charge

- timestamp: 2026-06-26T00:00:35Z
  checked: itp_parser.py ITPMoleculeInfo (line 17-31) and parse_itp_file() (line 34-141)
  found: ITPMoleculeInfo does NOT have charges field; parser only extracts atom_types and atom_names; charges at fields[6] never parsed
  implication: Need to add charges field and parse it

- timestamp: 2026-06-26T00:00:40Z
  checked: custom_molecule_inserter.py __init__ (lines 66-96)
  found: Only parses GRO; does NOT parse ITP; config has itp_path but never read for charge data
  implication: Need to parse ITP in inserter to get molecule_charge

- timestamp: 2026-06-26T00:00:45Z
  checked: CustomMoleculeStructure dataclass (types.py line 593-637)
  found: Has itp_path and custom_molecule_count but no molecule_charge field
  implication: Need to add molecule_charge field

- timestamp: 2026-06-26T00:00:50Z
  checked: IonPanel.set_custom_molecule_structure() (line 357-370)
  found: Sets _custom_molecule_structure but does NOT call _update_charge_warning()
  implication: Need to also call _update_charge_warning() when structure is set

- timestamp: 2026-06-26T00:05:00Z
  checked: All ITP test files (na_single.itp, ch4.itp, tip4p-ice.itp)
  found: Charge is consistently at fields[6] in [ atoms ] section; na_single has charge 0.85, ch4 and tip4p-ice are neutral
  implication: Confirmed correct column for charge extraction

- timestamp: 2026-06-26T00:08:00Z
  checked: Full test suite (1010 tests)
  found: All pass after fix applied
  implication: No regressions

- timestamp: 2026-06-26T00:09:00Z
  checked: New regression test (test_scancode_bugs_ion_charge_warning.py, 14 tests)
  found: All pass — ITP charge parsing, molecule_charge propagation, IonPanel charge calculation
  implication: Fix verified for all scenarios (neutral, non-neutral, negative charge, no structure)

## Resolution

root_cause: get_total_charge() in ion_panel.py always returned 0.0 because (1) ion pairs are neutral by design, and (2) custom molecule charge was explicitly deferred. ITP parser didn't extract charges, CustomMoleculeStructure didn't carry charge data, and IonPanel didn't compute custom molecule charge.
fix: 1) Added charges field to ITPMoleculeInfo (parsed from [ atoms ] fields[6]), 2) Added molecule_charge to CustomMoleculeStructure, 3) CustomMoleculeInserter now parses ITP to compute molecule_charge, 4) IonPanel.get_total_charge() now returns molecule_charge * molecule_count for Custom Molecule source, 5) set_custom_molecule_structure() now also calls _update_charge_warning()
verification: 1010 existing tests pass + 14 new regression tests pass. Verified: Na+ molecule (charge=0.85 × 5 molecules = 4.25 total), CH4 (neutral, no warning), Interface/Solute sources (0.0, no warning)
files_changed: [quickice/structure_generation/itp_parser.py, quickice/structure_generation/types.py, quickice/structure_generation/custom_molecule_inserter.py, quickice/gui/ion_panel.py, tests/test_scancode_bugs_ion_charge_warning.py, tests/test_itp_parser_edge_cases.py]
