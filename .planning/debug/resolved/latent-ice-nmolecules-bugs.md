---
status: verifying
trigger: "CustomMoleculeStructure lacks ice_nmolecules and water_nmolecules fields. Two latent bugs in ion_inserter and cli/pipeline.py"
created: 2026-06-19T00:00:00Z
updated: 2026-06-19T00:10:00Z
---

## Current Focus

hypothesis: ROOT CAUSE confirmed — CustomMoleculeStructure and SoluteStructure lack ice_nmolecules/water_nmolecules fields, making API fragile
test: Traced all code paths — specific getattr calls in ion_inserter.py and pipeline.py are NOT directly triggered, but the root cause (missing fields) creates latent fragility
expecting: Adding fields to dataclasses will fix all downstream getattr calls
next_action: Implement ROOT FIX: add ice_nmolecules and water_nmolecules fields to CustomMoleculeStructure and SoluteStructure dataclasses, then fix ion_inserter._build_molecule_index_from_structure for robustness

## Symptoms

expected: All downstream consumers of CustomMoleculeStructure (and SoluteStructure when sourced from CustomMoleculeStructure) should correctly resolve ice and water molecule counts.
actual: Two code paths default to 0 when the structure lacks ice_nmolecules/water_nmolecules
errors: No errors thrown — silently produces wrong results (zero counts instead of correct values)
reproduction: Run ion insertion with a CustomMoleculeStructure as source (GUI: ice → slab interface → custom mol → ion tab), or CLI chain that passes CustomMoleculeStructure to ion/custom-concentration calculation
started: Latent since CustomMoleculeStructure was created without these fields

## Eliminated

## Evidence

- timestamp: 2026-06-19T00:00:00Z
  checked: Prior analysis of types.py, solute_inserter.py, custom_molecule_inserter.py, main_window.py
  found: CustomMoleculeStructure and SoluteStructure lack ice_nmolecules/water_nmolecules; SoluteInserter already fixed with _resolve pattern; GUI custom_molecule_viewer.py and main_window.py ion export are safe
  implication: Need to verify ion_inserter.py and cli/pipeline.py code paths are actually reachable with these structures

- timestamp: 2026-06-19T00:01:00Z
  checked: GUI _on_insert_ions() flow for "Custom Molecule" source (main_window.py line 878-904)
  found: When source is "Custom Molecule", code extracts interface = custom_structure.interface_structure (InterfaceStructure) and passes THAT to insert_ions, not CustomMoleculeStructure directly. InterfaceStructure HAS ice_nmolecules/water_nmolecules.
  implication: Bug #1 in ion_inserter._build_molecule_index_from_structure is NOT directly reached via GUI

- timestamp: 2026-06-19T00:02:00Z
  checked: CLI _run_ion_step() for all three source modes (pipeline.py line 553-683)
  found: All three modes (interface, custom, solute) extract the InterfaceStructure from interface_structure field and pass THAT as source_for_ions. source_for_ions is always InterfaceStructure with water_nmolecules.
  implication: Bug #2 at pipeline.py line 664 is NOT directly triggered — getattr(source_for_ions, 'water_nmolecules', 0) always finds the field on InterfaceStructure

- timestamp: 2026-06-19T00:03:00Z
  checked: CLI _run_custom_step() source variable (pipeline.py line 420)
  found: source = self._interface_result, which is always InterfaceStructure. Line 437 getattr(source, 'water_nmolecules', 0) always finds the field.
  implication: Bug #2 at pipeline.py line 437 is NOT directly triggered

- timestamp: 2026-06-19T00:04:00Z
  checked: ion_inserter._build_molecule_index_from_structure call path (line 194-197)
  found: Method is only called when structure.molecule_index is falsy. CustomMoleculeStructure has POPULATED molecule_index, so method is NOT called. SoluteStructure lacks molecule_index entirely (raises AttributeError at line 194, which is BUG I5 already known).
  implication: Bug #1 code path is dead code for CustomMoleculeStructure — the method is never reached because molecule_index exists

- timestamp: 2026-06-19T00:05:00Z
  checked: All getattr calls with ice_nmolecules/water_nmolecules across codebase (14 getattr sites, 21 direct access sites)
  found: Current GUI/CLI flows always pass InterfaceStructure (which has fields) to downstream consumers. The fragility is in the dataclass design, not in current call paths.
  implication: ROOT CAUSE is missing fields on dataclasses. The specific bug locations are latent but the root cause makes the API fragile for future code

## Resolution

root_cause: CustomMoleculeStructure and SoluteStructure dataclasses lacked `ice_nmolecules` and `water_nmolecules` fields. While current GUI/CLI workflows always extract the InterfaceStructure (which has these fields) from the `interface_structure` attribute before passing to downstream consumers, this creates API fragility: any new code that directly passes CustomMoleculeStructure or SoluteStructure to getattr(structure, 'ice_nmolecules', 0) will silently get 0. Additionally, ion_inserter._build_molecule_index_from_structure has a latent bug where getattr defaults to 0 for structures lacking these fields, though it's currently dead code for CustomMoleculeStructure (which has populated molecule_index).
fix: 1) ROOT FIX: Added `ice_nmolecules` and `water_nmolecules` fields to CustomMoleculeStructure and SoluteStructure dataclasses in types.py, populated from the source interface structure during creation in custom_molecule_inserter.py and solute_inserter.py. 2) DEFENSE IN DEPTH: Made ion_inserter._build_molecule_index_from_structure robust by computing molecule counts from atom counts and interface_structure fallback when ice_nmolecules/water_nmolecules are 0 but atom counts are > 0. 3) Updated existing regression test in test_solute_insertion.py that asserted CustomMoleculeStructure lacks ice_nmolecules (now it correctly has it).
verification: All 992 tests pass (including 11 new tests in test_nmolecules_fields.py). New tests verify: (a) CustomMoleculeStructure/SoluteStructure have correctly populated ice_nmolecules/water_nmolecules fields, (b) getattr no longer defaults to 0, (c) liquid volume can be computed directly from these fields, (d) ion_inserter._build_molecule_index_from_structure falls back to atom counts when nmolecules fields are 0, (e) SoluteStructure from CustomMoleculeStructure source has correct nmolecules.
files_changed: [types.py, custom_molecule_inserter.py, solute_inserter.py, ion_inserter.py, tests/test_nmolecules_fields.py, tests/test_solute_insertion.py]
