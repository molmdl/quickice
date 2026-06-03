---
phase: e2e-api-workflow
plan: 04
type: execute
wave: 2
depends_on: ["e2e-api-workflow-01"]
files_modified:
  - tests/test_e2e_solute_insertion.py
autonomous: true

must_haves:
  truths:
    - "Solute insertion from Interface source places solutes in liquid region"
    - "Solute insertion from Custom Molecule source preserves custom attributes"
    - "CH4_H hydrate guests and CH4_L liquid solutes coexist with distinct names (MoleculetypeRegistry)"
    - "THF solute (13 atoms) inserts correctly"
    - "Zero concentration produces zero solutes without crash"
  artifacts:
    - path: "tests/test_e2e_solute_insertion.py"
      provides: "~15 solute insertion e2e tests"
      exports: ["test_solute_from_interface_source", "test_ch4_h_ch4_l_coexistence", "test_thf_solute_insertion"]
  key_links:
    - from: "tests/test_e2e_solute_insertion.py"
      to: "quickice/structure_generation/solute_inserter.py"
      via: "SoluteInserter(config).insert_solutes(interface)"
      pattern: "SoluteInserter"
    - from: "tests/test_e2e_solute_insertion.py"
      to: "quickice/structure_generation/moleculetype_registry.py"
      via: "registry.register_liquid_solute('CH4') → 'CH4_L'"
      pattern: "register_liquid_solute"
---

<objective>
Create solute insertion e2e tests covering all source combinations

Purpose: Test the solute insertion pipeline (Workflow 6) end-to-end: insertion from Interface source, insertion from Custom Molecule source, CH4 and THF solutes, CH4_H/CH4_L coexistence (P0 critical test S3), zero concentration handling, and attribute propagation through the workflow chain.

Output: tests/test_e2e_solute_insertion.py with ~15 tests
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
@quickice/structure_generation/solute_inserter.py
@quickice/structure_generation/custom_molecule_inserter.py
@quickice/structure_generation/moleculetype_registry.py
@quickice/structure_generation/types.py
@tests/conftest.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create basic solute insertion and cross-source tests</name>
  <files>tests/test_e2e_solute_insertion.py</files>
  <action>
Create `tests/test_e2e_solute_insertion.py` covering Workflow 6 (Solute Insertion). ~15 tests.

Use `interface_slab`, `interface_hydrate_slab` fixtures from conftest.py. Build CustomMoleculeStructure inline for custom-source tests.

**Basic insertion tests (Workflow 6b — from Interface source):**

1. `test_solute_ch4_from_interface_source` — `SoluteInserter(config=SoluteConfig(concentration_molar=0.5, solute_type='CH4'), seed=42).insert_solutes(interface_slab)`. Verify: `solute.n_molecules > 0`, `solute.solute_type == "CH4"`, `solute.positions.shape[0] == n_molecules * 5`.

2. `test_solute_thf_from_interface_source` — Same with `solute_type='THF'`. Verify: `solute.positions.shape[0] == n_molecules * 13`. THF has 13 atoms per molecule (P1 test S2).

3. `test_solutes_in_liquid_region_only` — For each solute molecule (using `solute.molecule_indices`), compute center of mass and verify within liquid region bounds. Use `solute.interface_structure` to get liquid region.

4. `test_no_solute_solute_overlap` — Build cKDTree from all solute positions. Verify minimum pairwise distance > `SoluteConfig.min_separation` (0.3 nm). Check distance between each pair of molecules, not just atoms within same molecule.

5. `test_zero_concentration_no_solutes` — `SoluteConfig(concentration_molar=0.0, solute_type='CH4')`. Verify: `solute.n_molecules == 0`, `solute.positions.shape == (0, 3)` or empty, no crash.

**P0 Critical: CH4_H/CH4_L coexistence (S3):**

6. `test_ch4_h_ch4_l_coexistence_in_registry` — Generate `interface_hydrate_slab` (has CH4 guests). Create `SoluteInserter(config=SoluteConfig(concentration_molar=0.3, solute_type='CH4'))`. Insert solutes. Verify: `solute.registry` has BOTH hydrate guest AND liquid solute registered with DISTINCT names. Check that registry distinguishes CH4_H (hydrate) from CH4_L (liquid). This is the P0 S3 test.

7. `test_hydrate_guests_preserved_after_solute_insertion` — After inserting CH4 solutes into hydrate interface, verify `solute.interface_structure.guest_nmolecules > 0` and guest atoms are still present.

**From Custom Molecule source (Workflow 6c):**

8. `test_solute_from_custom_molecule_source` — First place custom molecules on interface (create CustomMoleculeStructure inline), then insert solutes from that custom structure. Verify: `solute.custom_molecule_count > 0`, custom attributes propagated.

9. `test_solute_custom_attrs_preserved` — After solute insertion from custom source, check `solute.custom_molecule_atom_count > 0`, `solute.custom_molecule_positions is not None`.

**Molecule count calculation:**

10. `test_solute_molecule_count_from_concentration` — `SoluteInserter(config).calculate_molecule_count(1.0, volume)`. Verify returns integer > 0 for reasonable concentration and volume.

11. `test_solute_molecule_count_approximately_correct` — For 0.5M concentration, compute expected count: `0.5 * volume_L * NA`. Verify `solute.n_molecules` is within ±1 of expected.

**S4/S5 combinations (P2):**

12. `test_hydrate_thf_thf_liquid_coexistence` — Hydrate sI+THF interface → insert THF liquid solutes. Verify THF_H (hydrate) and THF_L (liquid) are distinct in registry. This is S4 test.

13. `test_hydrate_ch4_thf_liquid_mixed` — Hydrate sI+CH4 interface → insert THF liquid solutes (S5). Verify both molecule types present.

**Attribute propagation:**

14. `test_water_removal_after_solute_insertion` — `solute.interface_structure.water_atom_count < interface_slab.water_atom_count` (water molecules removed to make room for solutes).

15. `test_solute_molecule_indices_valid` — Each `(start, end)` in `solute.molecule_indices` maps to correct atom range in `solute.positions`. Verify `end - start == atoms_per_solute_type`.

Import paths:
```python
from quickice.structure_generation.solute_inserter import SoluteInserter
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter
from quickice.structure_generation.types import SoluteConfig, SoluteStructure, CustomMoleculeConfig
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
```
  </action>
  <verify>`pytest tests/test_e2e_solute_insertion.py -v` passes with 15+ tests</verify>
  <done>15 solute insertion tests pass covering Interface/Custom sources, CH4_H/CH4_L coexistence, THF solutes, zero concentration, and attribute propagation</done>
</task>

</tasks>

<verification>
```bash
# All solute tests pass
pytest tests/test_e2e_solute_insertion.py -v

# P0 critical test specifically
pytest tests/test_e2e_solute_insertion.py -v -k "ch4_h_ch4_l_coexistence"
```
</verification>

<success_criteria>
1. test_e2e_solute_insertion.py has 15+ tests, all pass
2. P0 test: CH4_H/CH4_L coexistence verified (S3)
3. Both Interface and Custom Molecule sources tested
4. THF solute (13 atoms) tested (S2)
5. Zero concentration produces zero solutes without crash
6. Attribute propagation from CustomMoleculeStructure to SoluteStructure verified
7. Water removal after solute insertion verified
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-api-workflow/e2e-api-workflow-04-SUMMARY.md`
</output>
