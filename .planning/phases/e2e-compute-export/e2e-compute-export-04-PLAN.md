---
phase: e2e-compute-export
plan: 04
type: execute
wave: 3
depends_on: ["e2e-compute-export-01", "e2e-compute-export-02", "e2e-compute-export-03"]
files_modified:
  - tests/test_e2e_chain_export_1.py
autonomous: true

must_haves:
  truths:
    - "F1 chain (Interface→Custom→Solute→Ion) export produces .gro with SOL→ETOH→CH4_L→NA→CL ordering"
    - "F2 chain (Interface→Custom→Ion) export produces .gro with SOL→ETOH→NA→CL ordering"
    - "F3 chain (Hydrate→Interface→Solute→Ion) export produces .gro with SOL→CH4_H→CH4_L→NA→CL ordering"
    - "F4 chain (Hydrate→Interface→Custom→Solute→Ion) export produces .gro with guest→custom→solute→NA→CL ordering"
    - "All chain exports produce .top [molecules] sections listing every molecule type with correct counts"
  artifacts:
    - path: "tests/test_e2e_chain_export_1.py"
      provides: "Full chain export bridge tests F1-F4"
      contains: "class TestChainF1"
  key_links:
    - from: "tests/test_e2e_chain_export_1.py"
      to: "quickice/output/gromacs_writer.py"
      via: "direct calls to write_ion_gro_file / write_ion_top_file for final chain structure"
      pattern: "write_ion_(gro|top)_file"
    - from: "tests/test_e2e_chain_export_1.py"
      to: "tests/e2e_export_helpers.py"
      via: "import of chain-building helpers and parsing functions"
      pattern: "from e2e_export_helpers import"
---

<objective>
Create full chain export validation tests (F1-F4) that build REAL computation chains and export the final structure, validating the complete compute→export bridge.

Purpose: Test the most complex pipeline chains where multiple insertion steps accumulate molecule types. Each chain produces a unique combination of molecule types that isn't covered by single-structure tests. F4 specifically tests the THF hydrate chain where guest_nmolecules is lost through CustomMoleculeStructure (known limitation).

Output: tests/test_e2e_chain_export_1.py (4 classes, ~12 methods)
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/e2e-compute-export/e2e-compute-export-RESEARCH.md
@tests/e2e_export_helpers.py
@tests/conftest.py
@quickice/output/gromacs_writer.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create full chain export tests F1-F4</name>
  <files>tests/test_e2e_chain_export_1.py</files>
  <action>
Create tests/test_e2e_chain_export_1.py with 4 test classes.

**F1: Interface→Custom→Solute→Ion** (class `TestChainF1`)
- Uses `interface_slab` fixture from conftest.py
- Build chain: `custom = _insert_custom_molecules(interface_slab, 3)` → `solute = _insert_solutes(custom, 'CH4', 0.3)` → `ion = _insert_ions_from_solute(solute, 0.15)`
- Register: `registry.register_liquid_solute("CH4")` before insert_solutes
- Generate ion.itp: `write_ion_itp(tmp_path / "ion.itp", ion.na_count, ion.cl_count)`
- Export: `write_ion_gro_file(ion, gro_path)`, `write_ion_top_file(ion, top_path)`
- Validates ALL 7 checks:
  1. GRO residue names: SOL→ETOH→CH4_L→NA→CL (5 molecule types, all 5 present)
  2. GRO atom count: header matches actual lines
  3. TOP [molecules]: SOL, ETOH, CH4_L, NA, CL with correct counts
  4. TOP #include: ["tip4p-ice.itp", "etoh.itp", "ch4_liquid.itp", "ion.itp"]
  5. ITP files: all 4 exist with [ moleculetype ]
  6. Custom + solute preserved: `ion.custom_molecule_count > 0`, `ion.solute_n_molecules > 0`
  7. Atom conservation: molecule_index sum == positions.shape[0] == GRO atom count

**F2: Interface→Custom→Ion** (class `TestChainF2`)
- Uses `interface_slab` fixture
- Build chain: `custom = _insert_custom_molecules(interface_slab, 3)` → `ion = _insert_ions(custom, 0.15)`
- Generate ion.itp, export, validate ALL 7 checks:
  1. GRO: SOL→ETOH→NA→CL (no solutes)
  2. TOP [molecules]: SOL, ETOH, NA, CL
  3. TOP #include: ["tip4p-ice.itp", "etoh.itp", "ion.itp"]
  4. No solute attributes: `ion.solute_type == ""`, `ion.solute_n_molecules == 0`

**F3: Hydrate→Interface→Solute→Ion** (class `TestChainF3`)
- Generate hydrate candidate inline: `hydrate_candidate = _hydrate_sI_ch4_candidate()`
- Build chain: `interface = _make_slab_interface(hydrate_candidate)` → `solute = _insert_solutes(interface, 'CH4', 0.3)` → `ion = _insert_ions_from_solute(solute, 0.15)`
- Register: `registry.register_hydrate_guest("CH4")` before insert_solutes AND `registry.register_liquid_solute("CH4")`
- Generate ion.itp, export, validate ALL 7 checks:
  1. GRO: SOL→CH4_H→CH4_L→NA→CL (CH4_H + CH4_L coexistence — key P0 test)
  2. TOP [molecules]: SOL, CH4_H (or CH4), CH4_L, NA, CL
  3. TOP #include: ["tip4p-ice.itp", "ch4_hydrate.itp", "ch4_liquid.itp", "ion.itp"]
  4. Guest count: `ion.guest_nmolecules > 0` (preserved because chain bypasses CustomMoleculeStructure)
  5. Registry distinguishes: CH4_H != CH4_L (the core MoleculetypeRegistry test)

**F4: Hydrate→Interface→Custom→Solute→Ion** (class `TestChainF4`)
- Generate hydrate candidate inline: `hydrate_candidate = _hydrate_sI_thf_candidate()`
- Build chain: `interface = _make_slab_interface(hydrate_candidate)` → `custom = _insert_custom_molecules(interface, 2)` → `solute = _insert_solutes(custom, 'THF', 0.2)` → `ion = _insert_ions_from_solute(solute, 0.15)`
- Register: `registry.register_hydrate_guest("THF")` before insert_solutes AND `registry.register_liquid_solute("THF")`
- Generate ion.itp, export, validate ALL 7 checks:
  1. GRO: SOL→THF_H→ETOH→THF_L→NA→CL (6 molecule types — all present)
  2. TOP [molecules]: SOL, THF_H (or THF), ETOH, THF_L, NA, CL
  3. TOP #include: ["tip4p-ice.itp", "thf_hydrate.itp", "etoh.itp", "thf_liquid.itp", "ion.itp"]
  4. KNOWN LIMITATION: `guest_nmolecules` may be 0 after passing through CustomMoleculeStructure (field doesn't exist on that type). Use `guest_atom_count > 0` instead. This is a documented limitation.
  5. Registry distinguishes: THF_H != THF_L

**CRITICAL implementation notes:**
- F3/F4 use inline hydrate candidate generation (not conftest fixture) because the interface needs to be built with a different seed than the shared fixture
- F1/F4 use `_insert_ions_from_solute()` which applies the BUG I5 workaround
- F3 uses `_insert_ions_from_solute()` — also needs workaround since solute is in the chain
- F2 uses `_insert_ions()` directly — no workaround needed (custom→ion doesn't hit BUG I5)
- For F3/F4, register_hydrate_guest() MUST be called before insert_solutes() — SoluteInserter creates its own registry, and the hydrate guest must be in that registry for correct CH4_H/THF_H naming
- THF has 13 atoms per molecule (not 5 like CH4) — affects atom count expectations
- Ethanol has 9 atoms per molecule
- All chains use tmp_path for output directory, write_ion_itp() to generate ion.itp in same directory

**Test helper usage:**
```python
from e2e_export_helpers import (
    parse_gro_residue_names, parse_gro_atom_count, parse_top_molecules,
    parse_top_includes, check_itp_has_moleculetype, assert_gro_residue_ordering,
    _insert_custom_molecules, _insert_solutes, _solute_to_ion_source,
    _insert_ions, _insert_ions_from_solute,
    _hydrate_sI_ch4_candidate, _hydrate_sI_thf_candidate, _make_slab_interface,
)
from quickice.output.gromacs_writer import write_ion_gro_file, write_ion_top_file
from quickice.structure_generation.gromacs_ion_export import write_ion_itp
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
```
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -m pytest tests/test_e2e_chain_export_1.py -v --timeout=180 -x</verify>
  <done>F1-F4 chain export tests pass with all 7 validation checks per chain, BUG I5 workaround applied, CH4_H/CH4_L coexistence validated in F3, guest_nmolecules limitation documented in F4</done>
</task>

</tasks>

<verification>
1. pytest tests/test_e2e_chain_export_1.py passes (4 classes, ~12 methods)
2. F1: SOL→ETOH→CH4_L→NA→CL ordering validated
3. F2: SOL→ETOH→NA→CL ordering validated (no solutes)
4. F3: SOL→CH4_H→CH4_L→NA→CL ordering validated (P0 CH4 coexistence test)
5. F4: SOL→THF_H→ETOH→THF_L→NA→CL ordering validated (6 molecule types)
6. All chains: TOP [molecules] + #include + ITP + atom conservation validated
7. BUG I5 workaround used correctly for F1, F3, F4
8. guest_nmolecules limitation handled in F4 (use guest_atom_count > 0)
</verification>

<success_criteria>
- tests/test_e2e_chain_export_1.py exists with 4 test classes
- F1-F4 chain exports validated with real GenIce2 data
- Molecule ordering matches GROMACS convention in all chains
- ITP bundling correct: each chain has expected ITP file count (F1: 4, F2: 3, F3: 4, F4: 5)
- CH4_H/CH4_L coexistence validated in F3 (registry distinction)
- THF_H/THF_L coexistence validated in F4 (registry distinction)
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-compute-export/e2e-compute-export-04-SUMMARY.md`
</output>
