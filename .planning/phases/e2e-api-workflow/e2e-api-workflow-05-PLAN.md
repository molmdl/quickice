---
phase: e2e-api-workflow
plan: 05
type: execute
wave: 2
depends_on: ["e2e-api-workflow-01"]
files_modified:
  - tests/test_e2e_ion_insertion.py
  - tests/test_e2e_workflow_chains.py
autonomous: true

must_haves:
  truths:
    - "Ion insertion from Interface source produces charge-neutral Na+/Cl- pairs"
    - "Ion insertion from Custom Molecule source preserves custom attributes"
    - "SoluteStructure → IonInserter raises AttributeError (BUG I5 exposure)"
    - "Charge neutrality: na_count == cl_count in all IonStructure results"
    - "Guest/custom/solute attributes propagate through ion insertion"
    - "Full chain Ice→Interface→Custom→Solute→Ion produces valid structure with all molecule types present at each step"
  artifacts:
    - path: "tests/test_e2e_ion_insertion.py"
      provides: "~12 ion insertion e2e tests"
      exports: ["test_ion_from_interface_source", "test_solute_structure_attribute_error_bug", "test_ion_charge_neutrality"]
    - path: "tests/test_e2e_workflow_chains.py"
      provides: "~12 workflow chain e2e tests"
      exports: ["test_full_chain_ice_slab_custom_solute_ion", "test_hydrate_chain_solute_ion"]
  key_links:
    - from: "tests/test_e2e_ion_insertion.py"
      to: "quickice/structure_generation/ion_inserter.py"
      via: "IonInserter(config).replace_water_with_ions(structure, ion_pairs)"
      pattern: "replace_water_with_ions"
    - from: "tests/test_e2e_ion_insertion.py"
      to: "quickice/structure_generation/types.py"
      via: "SoluteStructure has molecule_indices not molecule_index"
      pattern: "SoluteStructure|molecule_index"
    - from: "tests/test_e2e_workflow_chains.py"
      to: "tests/conftest.py"
      via: "pytest fixtures (ice_ih_candidate, interface_slab, interface_hydrate_slab)"
      pattern: "ice_ih_candidate|interface_slab|interface_hydrate_slab"
    - from: "tests/test_e2e_workflow_chains.py"
      to: "quickice/structure_generation/custom_molecule_inserter.py"
      via: "CustomMoleculeInserter(config).place_random(interface, N)"
      pattern: "CustomMoleculeInserter"
    - from: "tests/test_e2e_workflow_chains.py"
      to: "quickice/structure_generation/solute_inserter.py"
      via: "SoluteInserter(config).insert_solutes(source_structure, config)"
      pattern: "SoluteInserter"
    - from: "tests/test_e2e_workflow_chains.py"
      to: "quickice/structure_generation/ion_inserter.py"
      via: "IonInserter(config).replace_water_with_ions(source_structure, ion_pairs)"
      pattern: "replace_water_with_ions"
---

<objective>
Create ion insertion e2e tests with bug exposure and workflow chain tests

Purpose: Test the ion insertion pipeline (Workflow 7 + Workflow 8) end-to-end: ion insertion from Interface/Custom/Solute sources, the CRITICAL SoluteStructure→IonInserter AttributeError bug (P0 I5), charge neutrality verification, full workflow chains (F1-F7), and structural invariants across the complete pipeline.

Output: tests/test_e2e_ion_insertion.py with ~12 tests + tests/test_e2e_workflow_chains.py with ~12 tests
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
@quickice/structure_generation/ion_inserter.py
@quickice/structure_generation/solute_inserter.py
@quickice/structure_generation/custom_molecule_inserter.py
@quickice/structure_generation/types.py
@tests/conftest.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create ion insertion e2e tests including bug exposure</name>
  <files>tests/test_e2e_ion_insertion.py</files>
  <action>
Create `tests/test_e2e_ion_insertion.py` covering Workflow 7 (Ion Insertion). ~12 tests.

Use `interface_slab` fixture from conftest.py. Build CustomMoleculeStructure and SoluteStructure inline for source-variant tests.

**Basic insertion tests (I1-I4):**

1. `test_ion_from_interface_source` — `IonInserter(config=IonConfig(concentration_molar=0.15), seed=42)`. Calculate volume: `interface_slab.water_nmolecules * 0.0299`. Calculate ion pairs: `inserter.calculate_ion_pairs(0.15, volume)`. Call `inserter.replace_water_with_ions(interface_slab, ion_pairs)`. Verify: `ion.na_count > 0`, `ion.cl_count > 0`, `ion.na_count == ion.cl_count` (charge neutrality).

2. `test_ion_charge_neutrality` — For multiple concentration values (0.05, 0.15, 0.5 M), verify `ion.na_count == ion.cl_count` always. This is invariant #16.

3. `test_ion_from_hydrate_interface_source` — Insert ions into `interface_hydrate_slab`. Verify: `ion.guest_nmolecules > 0` (guests preserved), `ion.na_count == ion.cl_count`.

4. `test_ion_from_custom_molecule_source` — First create CustomMoleculeStructure by placing ethanol on interface (inline). Then insert ions into the CustomMoleculeStructure. Verify: `ion.custom_molecule_count > 0`, `ion.custom_molecule_atom_count > 0`, custom attributes propagated (I3 test).

5. `test_ion_positions_within_cell` — All ion positions should be within cell boundaries.

**P0 CRITICAL: SoluteStructure bug (I5):**

6. `test_solute_structure_attribute_error_bug` — This is the P0 bug exposure test (I5). Create a SoluteStructure by inserting solutes into interface. Then try `IonInserter.replace_water_with_ions(solute_structure, ion_pairs)`. 

The EXPECTED behavior is that this should raise `AttributeError: 'SoluteStructure' object has no attribute 'molecule_index'` because SoluteStructure has `molecule_indices` (list of tuples) but NOT `molecule_index` (list of MoleculeIndex).

Write this test to EXPOSE the bug:
```python
def test_solute_structure_attribute_error_bug(interface_slab):
    """P0: SoluteStructure → IonInserter raises AttributeError (BUG I5).
    
    SoluteStructure has molecule_indices (list of tuples) but NOT molecule_index
    (list of MoleculeIndex). IonInserter.replace_water_with_ions checks
    structure.molecule_index first, causing AttributeError.
    """
    # Insert solutes
    solute_config = SoluteConfig(concentration_molar=0.3, solute_type='CH4')
    solute_inserter = SoluteInserter(config=solute_config, seed=42)
    solute = solute_inserter.insert_solutes(interface_slab, solute_config)
    
    # Try to insert ions into SoluteStructure
    ion_config = IonConfig(concentration_molar=0.15)
    ion_inserter = IonInserter(config=ion_config, seed=42)
    volume = solute.interface_structure.water_nmolecules * 0.0299
    ion_pairs = ion_inserter.calculate_ion_pairs(0.15, volume)
    
    # This should raise AttributeError because SoluteStructure lacks molecule_index
    with pytest.raises(AttributeError, match="molecule_index"):
        ion_inserter.replace_water_with_ions(solute, ion_pairs)
```

**GUI workaround test:**

7. `test_ion_from_solute_workaround` — Show the GUI workaround works: pass `solute.interface_structure` instead of `solute` directly. Set solute attributes on the interface_structure before passing. Verify this produces valid IonStructure.

**Ion count and volume tests:**

8. `test_ion_count_approximately_correct` — For 0.15M concentration, verify `ion.na_count ≈ 0.15 * volume_L * NA` (within rounding tolerance).

9. `test_zero_concentration_no_ions` — `IonConfig(concentration_molar=0.0)`. Verify: `ion.na_count == 0`, `ion.cl_count == 0`.

**Attribute propagation tests (I3, I4, I6, I7):**

10. `test_custom_attrs_propagate_through_ion` — After ion insertion from CustomMoleculeStructure, verify `ion.custom_molecule_count > 0`, `ion.custom_molecule_positions is not None`.

11. `test_guest_attrs_propagate_through_ion` — After ion insertion into hydrate interface, verify `ion.guest_nmolecules > 0`, `ion.guest_atom_count > 0`.

12. `test_solute_attrs_propagate_through_ion_workaround` — After ion insertion via workaround (using interface_structure with solute attrs set), verify `ion.solute_type != ""`, `ion.solute_n_molecules > 0`, `ion.solute_positions is not None`.

Import paths:
```python
from quickice.structure_generation.ion_inserter import IonInserter
from quickice.structure_generation.solute_inserter import SoluteInserter
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter
from quickice.structure_generation.types import IonConfig, IonStructure, SoluteConfig, SoluteStructure, CustomMoleculeConfig
```
  </action>
  <verify>`pytest tests/test_e2e_ion_insertion.py -v` passes with 12+ tests (including the expected-fail bug test)</verify>
  <done>12 ion insertion tests pass including P0 SoluteStructure bug exposure, charge neutrality, and attribute propagation</done>
</task>

<task type="auto">
  <name>Task 2: Create full workflow chain e2e tests</name>
  <files>tests/test_e2e_workflow_chains.py</files>
  <action>
Create `tests/test_e2e_workflow_chains.py` covering Workflow 8 (Complete Workflow Chains). ~12 tests.

These tests exercise the FULL pipeline: Ice → Interface → Custom → Solute → Ion, verifying that each step produces valid output and that the next step can consume it.

Use conftest fixtures as starting points and build chains inline.

**Full chain tests (F1-F7 from CONTEXT.md):**

1. `test_full_chain_ice_slab_custom_solute_ion` — F1: Generate ice → slab interface → custom random placement → solute from custom source → ion from solute source (workaround). Verify at each step: positions finite, atom counts sum, all molecule types present in final structure. This is the P0 baseline.

2. `test_short_chain_ice_slab_custom_ion` — F2: Ice → slab interface → custom → ion (skip solute). Verify final structure has ice+water+custom+ions, no solute attrs.

3. `test_hydrate_chain_solute_ion` — F3: Hydrate sI+CH4 → slab interface → solute CH4 from interface source → ion from solute source (workaround). Verify CH4_H guests + CH4_L solutes coexist, ion structure has guests.

4. `test_hydrate_thf_custom_solute_ion_chain` — F4: Hydrate sI+THF → interface → custom → solute THF from custom → ion. All molecule types present: guests+custom+solute+ions.

5. `test_pocket_chain_custom_solute` — F5: Ice Ih → pocket interface → custom random → solute. Different interface mode (pocket vs slab).

6. `test_ice_slab_solute_no_custom` — F6: Ice → slab interface → solute (no custom step). Simpler chain, verify solute insertion works without custom molecules.

7. `test_ice_slab_solute_thf_ion` — F7: Ice → slab → solute THF → ion. THF solute chain.

**Structural invariant tests across chains:**

8. `test_chain_no_atoms_lost` — After full chain (F1), verify `sum of all molecule atom counts == total positions`. No atoms lost or duplicated.

9. `test_chain_molecule_ordering_correct` — After full chain, verify molecule ordering in final IonStructure: SOL (ice+water) → hydrate guests → liquid solutes → custom molecules → ions. Check `ion.molecule_index` entries are in correct order.

10. `test_chain_cell_volume_preserved` — Cell should remain the same through all insertion steps (no cell modification during molecule insertion).

11. `test_chain_all_molecule_types_present` — After F1, verify IonStructure has: ice molecules, water molecules, custom molecules (custom_molecule_count > 0), ions (na_count > 0, cl_count > 0). After F4, also verify guests (guest_nmolecules > 0) and solutes (solute_n_molecules > 0).

12. `test_chain_ch4_h_neq_ch4_l` — After F3 (hydrate+CH4 chain), verify that the MoleculetypeRegistry distinguishes CH4_H from CH4_L. Check that `registry.get_moleculetype_name` for hydrate CH4 ≠ liquid CH4.

IMPORTANT: For chains involving SoluteStructure → IonInserter, use the workaround (pass `solute.interface_structure` with solute attrs attached). This is documented in CONTEXT.md and the SoluteStructure bug test in Plan 05.

For custom molecule step: use `CustomMoleculeInserter(config).place_random(interface, 3)` with etoh.gro/etoh.itp.
For solute step: use `SoluteInserter(config).insert_solutes(source_structure, config)`.
For ion step: use `IonInserter(config).replace_water_with_ions(source_structure, ion_pairs)`.
  </action>
  <verify>`pytest tests/test_e2e_workflow_chains.py -v` passes with 12+ tests</verify>
  <done>12 workflow chain tests pass covering F1-F7 chains and cross-chain structural invariants</done>
</task>

</tasks>

<verification>
```bash
# All ion + chain tests pass
pytest tests/test_e2e_ion_insertion.py tests/test_e2e_workflow_chains.py -v

# P0 bug exposure test
pytest tests/test_e2e_ion_insertion.py -v -k "solute_structure_attribute_error"

# P0 full chain test
pytest tests/test_e2e_workflow_chains.py -v -k "full_chain_ice_slab_custom_solute_ion"
```
</verification>

<success_criteria>
1. test_e2e_ion_insertion.py has 12+ tests, all pass (including expected AttributeError for bug I5)
2. test_e2e_workflow_chains.py has 12+ tests, all pass
3. P0: SoluteStructure → IonInserter AttributeError exposed (test 6)
4. P0: Full chain F1 tested (ice→interface→custom→solute→ion)
5. P0: CH4_H/CH4_L coexistence in hydrate+solute chain (F3)
6. Charge neutrality verified for all ion insertion tests
7. All structural invariants verified across chains (atom count sum, molecule ordering, cell volume)
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-api-workflow/e2e-api-workflow-05-SUMMARY.md`
</output>
