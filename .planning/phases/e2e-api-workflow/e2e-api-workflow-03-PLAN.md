---
phase: e2e-api-workflow
plan: 03
type: execute
wave: 2
depends_on: ["e2e-api-workflow-01"]
files_modified:
  - tests/test_e2e_custom_molecule.py
autonomous: true

must_haves:
  truths:
    - "Custom molecule GRO/ITP validation catches atom count mismatches"
    - "Random placement produces molecules within liquid region bounds"
    - "Custom placement validates bounds and detects overlaps"
    - "Water removal reduces water_atom_count after molecule insertion"
    - "Generic residue name 'MOL' does not trigger mismatch warning"
  artifacts:
    - path: "tests/test_e2e_custom_molecule.py"
      provides: "~20 custom molecule e2e tests"
      exports: ["test_validate_etoh_molecule", "test_random_placement_in_liquid", "test_custom_placement_bounds_validation"]
  key_links:
    - from: "tests/test_e2e_custom_molecule.py"
      to: "quickice/structure_generation/custom_molecule_inserter.py"
      via: "CustomMoleculeInserter(config).place_random(interface, N)"
      pattern: "CustomMoleculeInserter"
    - from: "tests/test_e2e_custom_molecule.py"
      to: "quickice/structure_generation/molecule_validator.py"
      via: "validate_custom_molecule(gro_path, itp_info)"
      pattern: "validate_custom_molecule"
---

<objective>
Create custom molecule upload, validation, and insertion e2e tests

Purpose: Test the custom molecule pipeline (Workflow 5) end-to-end: GRO/ITP file validation, random placement with overlap checking and water removal, custom placement with bounds/overlap validation, and edge cases (atom count mismatch, generic residue names, missing atomtypes section).

Output: tests/test_e2e_custom_molecule.py with ~20 tests
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/e2e-api-workflow/CONTEXT.md
@quickice/structure_generation/custom_molecule_inserter.py
@quickice/structure_generation/molecule_validator.py
@quickice/structure_generation/itp_parser.py
@quickice/structure_generation/gro_parser.py
@quickice/structure_generation/types.py
@tests/conftest.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create custom molecule validation and random placement tests</name>
  <files>tests/test_e2e_custom_molecule.py</files>
  <action>
Create `tests/test_e2e_custom_molecule.py` covering Workflow 5 (Custom Molecule Upload & Insertion). Start with validation tests and random placement tests. ~13 tests.

Use `interface_slab` fixture from conftest.py for placement tests. Use `quickice/data/custom/etoh.gro` and `quickice/data/custom/etoh.itp` as valid test data.

**Validation tests (Workflow 5a):**

1. `test_validate_etoh_molecule_valid` — Parse etoh.itp with `parse_itp_file()`, validate with `validate_custom_molecule(etoh_gro_path, itp_info)`. Verify: `result.is_valid == True`, `result.errors == []`, `result.gro_atom_count == 9`.

2. `test_validate_atom_count_mismatch` — Create a temporary GRO file with wrong atom count (e.g., 10 atoms instead of 9). Verify: `result.is_valid == False`, `result.errors` contains "atom count mismatch".

3. `test_validate_generic_residue_name_no_mismatch` — Create temporary GRO file with residue name "MOL" (generic) and ITP with moleculetype name "etoh". Verify: `result.residue_name_mismatch == False` (generic names don't trigger warning).

4. `test_validate_real_residue_name_mismatch` — Create temporary GRO with residue name "XXX_CUSTOM" (non-generic) and ITP with different moleculetype. Verify: `result.residue_name_mismatch == True`.

5. `test_validate_itp_without_atomtypes_warning` — Create temporary ITP without [ atomtypes ] section. Verify: `result.warnings` contains "atomtypes" but `result.is_valid == True` (warning only, not blocking).

6. `test_parse_non_gro_file_raises_error` — Try `parse_gro_file(Path('nonexistent.txt'))`. Verify raises exception (FileNotFoundError or ValueError).

**Random placement tests (Workflow 5b):**

7. `test_random_placement_produces_custom_structure` — Use `CustomMoleculeConfig(placement_mode='random', gro_path=etoh_gro, itp_path=etoh_itp, molecule_count=3)`. Call `inserter.place_random(interface_slab, 3)`. Verify: `custom.custom_molecule_count == 3`, `custom.positions.shape[0] > 0`, `custom.custom_molecule_atom_count == 3 * 9`.

8. `test_random_placement_molecules_in_liquid_region` — For each placed molecule, compute center of mass and verify it's within liquid region bounds (between ice and water atom positions z-range for slab mode).

9. `test_random_placement_no_ice_overlap` — Verify minimum distance between custom molecule atoms and ice atoms > min_separation (0.3 nm). Build cKDTree from ice atoms and query.

10. `test_random_placement_water_removal` — Verify `custom.water_atom_count < interface_slab.water_atom_count` (some water was removed to make room for custom molecules).

11. `test_random_placement_complete_system` — Verify `custom.ice_atom_count + custom.water_atom_count + custom.custom_molecule_atom_count == len(custom.positions)`.

12. `test_molecule_count_from_concentration` — `CustomMoleculeInserter.calculate_molecule_count(1.0, liquid_volume_nm3)` should return integer > 0. Verify `liquid_volume_nm3 = interface_slab.water_nmolecules * 0.0299`.

13. `test_concentration_roundtrip` — `count = calculate_molecule_count(C, V)`, then `C2 = calculate_concentration(count, V)`. Verify `abs(C2 - C) < 0.01`.

Import paths:
```python
from pathlib import Path
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter, InsertionError
from quickice.structure_generation.molecule_validator import validate_custom_molecule, ValidationResult
from quickice.structure_generation.itp_parser import parse_itp_file
from quickice.structure_generation.gro_parser import parse_gro_file, extract_residue_name_from_gro
from quickice.structure_generation.types import CustomMoleculeConfig, CustomMoleculeStructure
```

For temporary GRO/ITP files, use `tmp_path` fixture from pytest and write minimal GRO/ITP content.
  </action>
  <verify>`pytest tests/test_e2e_custom_molecule.py -v -k "validate or random"` passes with 13+ tests</verify>
  <done>13 validation + random placement tests pass</done>
</task>

<task type="auto">
  <name>Task 2: Add custom placement validation and edge case tests</name>
  <files>tests/test_e2e_custom_molecule.py</files>
  <action>
Add custom placement and edge case tests to the SAME file. ~7 more tests.

**Custom placement tests (Workflow 5c):**

1. `test_custom_placement_at_valid_position` — Use `CustomMoleculeConfig(placement_mode='custom', gro_path=etoh_gro, itp_path=etoh_itp, positions=[(1.5, 1.5, 4.0)], rotations=[(0, 0, 0)])`. Call `inserter.validate_single_placement(interface_slab, (1.5, 1.5, 4.0), (0, 0, 0))`. Verify: `result.is_valid == True` or `result.within_bounds == True` (position in liquid region).

2. `test_custom_placement_out_of_bounds` — Position outside liquid region (e.g., in ice region z < ice boundary). Verify: `result.within_bounds == False`, `result.is_valid == False`.

3. `test_custom_placement_overlap_detected` — Position very close to ice atoms (e.g., (0.1, 0.1, 0.1) which is in ice region). Verify: `result.has_overlap == True` OR `result.within_bounds == False`. The overlap check should detect conflict with ice atoms.

4. `test_custom_placement_no_interface_returns_invalid` — Call `validate_single_placement()` with a structure that has `water_atom_count == 0`. Verify: `result.is_valid == False`, error message mentions "No liquid region".

5. `test_place_custom_with_user_positions` — Call `inserter.place_custom(interface_slab, positions=[(1.5, 1.5, 4.0)], rotations=[(0, 0, 0)])`. Verify: `custom.custom_molecule_count == 1`, has custom molecule atoms, complete system atom counts sum correctly.

**Edge case tests:**

6. `test_custom_molecule_moleculetype_registration` — After `place_random()`, verify `custom.moleculetype_name` is set (e.g., "CUSTOM_MOL_1" or similar). Check `inserter.registry` has the registered type.

7. `test_custom_molecule_from_hydrate_interface` — Place custom molecule on `interface_hydrate_slab` (has guests). Verify: `custom.guest_atom_count > 0`, guests preserved, custom molecules placed correctly.

Use `interface_slab` and `interface_hydrate_slab` fixtures from conftest.py.
  </action>
  <verify>`pytest tests/test_e2e_custom_molecule.py -v` passes with 20+ tests total</verify>
  <done>20 custom molecule tests pass covering validation, random placement, custom placement, and edge cases</done>
</task>

</tasks>

<verification>
```bash
# All custom molecule tests pass
pytest tests/test_e2e_custom_molecule.py -v

# Verify test count
pytest tests/test_e2e_custom_molecule.py --collect-only -q | wc -l
```
</verification>

<success_criteria>
1. test_e2e_custom_molecule.py has 20+ tests, all pass
2. GRO/ITP validation tests cover: valid molecule, atom count mismatch, residue name mismatch (generic vs real), missing atomtypes
3. Random placement tests verify: molecule count, liquid region bounds, no ice overlap, water removal, complete system
4. Custom placement tests verify: bounds validation, overlap detection, no-interface error
5. Edge cases: moleculetype registration, hydrate interface with guests
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-api-workflow/e2e-api-workflow-03-SUMMARY.md`
</output>
