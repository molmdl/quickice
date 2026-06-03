---
phase: e2e-compute-export
plan: 02
type: execute
wave: 2
depends_on: ["e2e-compute-export-01"]
files_modified:
  - tests/test_e2e_custom_export.py
  - tests/test_e2e_solute_export.py
autonomous: true

must_haves:
  truths:
    - "Custom molecule structure exported produces .gro with SOL before custom residue name"
    - "Solute from Interface exported produces .gro with SOL before solute residue name"
    - "Solute from Custom exported produces .gro with SOL before custom before solute"
    - "GRO atom count header matches actual atom lines for all 3 custom/solute export scenarios"
    - "TOP [molecules] section lists correct molecule type counts for custom and solute exports"
  artifacts:
    - path: "tests/test_e2e_custom_export.py"
      provides: "Custom molecule single-structure export tests"
      contains: "class TestCustomMoleculeExport"
    - path: "tests/test_e2e_solute_export.py"
      provides: "Solute single-structure export tests (2 scenarios)"
      contains: "class TestSoluteFromInterface"
  key_links:
    - from: "tests/test_e2e_custom_export.py"
      to: "quickice/output/gromacs_writer.py"
      via: "direct calls to write_custom_molecule_gro_file / write_custom_molecule_top_file"
      pattern: "write_custom_molecule_(gro|top)_file"
    - from: "tests/test_e2e_solute_export.py"
      to: "quickice/output/gromacs_writer.py"
      via: "direct calls to write_solute_gro_file / write_solute_top_file"
      pattern: "write_solute_(gro|top)_file"
---

<objective>
Create single-structure export validation tests for Custom Molecule and Solute structure types, validating that real computation pipeline output flows correctly through GROMACS exporters.

Purpose: Cover the Custom Molecule export (1 scenario) and Solute export (2 scenarios: from Interface and from Custom source) — these are the middle layers of the pipeline that must correctly pass guest and custom molecule attributes to the writer.

Output: tests/test_e2e_custom_export.py (1 class, ~3 methods) + tests/test_e2e_solute_export.py (2 classes, ~6 methods)
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
  <name>Task 1: Create Custom Molecule single-structure export tests</name>
  <files>tests/test_e2e_custom_export.py</files>
  <action>
Create tests/test_e2e_custom_export.py with 1 test class.

**Scenario 4: Custom Molecule Export** (class `TestCustomMoleculeExport`)
- Uses `interface_slab` fixture from conftest.py
- Builds custom structure: `custom = _insert_custom_molecules(interface_slab, n_molecules=3)` (helper from e2e_export_helpers.py)
- Calls `write_custom_molecule_gro_file(custom, gro_path)` and `write_custom_molecule_top_file(custom, top_path)`
- Validates ALL 7 checks:
  1. GRO residue names: "SOL" first, then custom molecule residue name (ETOH — 4 chars, fits GRO 5-char limit). No interleaving.
  2. GRO atom count: header matches actual lines. Expected = ice_nmolecules*4 + water_nmolecules*4 + custom_molecule_count*9 (ethanol = 9 atoms per molecule)
  3. TOP [molecules]: `{"SOL": ice_nmolecules + water_nmolecules, "ETOH": 3}` (moleculetype_name from custom structure)
  4. TOP #include: `["tip4p-ice.itp", "etoh.itp"]` (custom ITP uses original filename)
  5. ITP etoh.itp exists in quickice/data/custom/ and has [ moleculetype ]
  6. ITP tip4p-ice.itp exists in quickice/data/ and has [ moleculetype ]
  7. Atom conservation: total atoms from molecule_index == positions.shape[0] (no atoms lost)

**Implementation notes:**
- Import chain helpers from e2e_export_helpers: `from e2e_export_helpers import _insert_custom_molecules, parse_gro_residue_names, parse_gro_atom_count, parse_top_molecules, parse_top_includes, check_itp_has_moleculetype, assert_gro_residue_ordering`
- Import writer functions: `from quickice.output.gromacs_writer import write_custom_molecule_gro_file, write_custom_molecule_top_file`
- Use `tmp_path` for output directory
- Custom molecule ITP path: `Path(quickice.__file__).parent / "data" / "custom" / "etoh.itp"`
- CustomMoleculeStructure includes complete system (ice + water + custom) — verified in e2e-api-workflow-05
- moleculetype_name comes from `custom.moleculetype_name` (should be "ETOH" from the ITP file)
- Custom ITP filename in #include uses the ORIGINAL filename "etoh.itp" (not stem-based like ice exporter)
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -m pytest tests/test_e2e_custom_export.py -v --timeout=120 -x</verify>
  <done>Custom molecule export test passes with all 7 validation checks on real GenIce2 data</done>
</task>

<task type="auto">
  <name>Task 2: Create Solute single-structure export tests</name>
  <files>tests/test_e2e_solute_export.py</files>
  <action>
Create tests/test_e2e_solute_export.py with 2 test classes covering 2 scenarios.

**Scenario 5: Solute from Interface Export** (class `TestSoluteFromInterface`)
- Uses `interface_slab` fixture from conftest.py
- Register solute: create MoleculetypeRegistry, call `registry.register_liquid_solute("CH4")` BEFORE inserting solutes
- Build solute structure: `solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)` (helper from e2e_export_helpers.py)
- Calls `write_solute_gro_file(solute, gro_path)` and `write_solute_top_file(solute, top_path)`
- Validates ALL 7 checks:
  1. GRO residue names: "SOL" first, then solute residue name "CH4_L" (5 chars, fits exactly)
  2. GRO atom count: header matches actual lines. Expected = ice*4 + water*4 + solute.n_molecules*5 (CH4 = 5 atoms)
  3. TOP [molecules]: `{"SOL": ice + water, "CH4_L": solute.n_molecules}`
  4. TOP #include: `["tip4p-ice.itp", "ch4_liquid.itp"]`
  5. ITP ch4_liquid.itp exists in quickice/data/ and has [ moleculetype ]
  6. ITP tip4p-ice.itp exists in quickice/data/ and has [ moleculetype ]
  7. Atom conservation: total atoms from structure matches GRO output

**Scenario 6: Solute from Custom Export** (class `TestSoluteFromCustom`)
- Uses `interface_slab` fixture from conftest.py
- Build chain: `custom = _insert_custom_molecules(interface_slab, n_molecules=3)`, then `solute = _insert_solutes(custom, solute_type='CH4', concentration=0.3)`
- Register: `registry.register_liquid_solute("CH4")` before insert_solutes
- Calls `write_solute_gro_file(solute, gro_path)` and `write_solute_top_file(solute, top_path)`
- Validates ALL 7 checks:
  1. GRO residue names: "SOL" first, then custom molecule residues, then solute residues "CH4_L"
  2. GRO atom count: header matches actual lines
  3. TOP [molecules]: `{"SOL": ice + water, "ETOH": 3, "CH4_L": solute.n_molecules}` — custom molecules appear BEFORE solutes
  4. TOP #include: `["tip4p-ice.itp", "etoh.itp", "ch4_liquid.itp"]` — custom ITP before solute ITP
  5. ITP etoh.itp and ch4_liquid.itp exist and have [ moleculetype ]
  6. Custom molecule count preserved: `solute.custom_molecule_count == 3`
  7. Atom conservation: total atoms match

**CRITICAL pitfall (Pitfall 6 from RESEARCH):** Registry MUST be populated before writer use. The writer calls `registry.get_gromacs_name()` which returns `source.upper()` if key isn't registered, leading to "LIQUID_CH4" instead of "CH4_L". Always create a fresh MoleculetypeRegistry, call register_liquid_solute(), and pass it to SoluteInserter. SoluteInserter creates its own registry internally, so register_hydrate_guest() must be called manually before insert_solutes() when testing hydrate chains.

**IMPORTANT:** SoluteStructure stores solute positions SEPARATELY from interface positions. The writer (write_solute_gro_file) accesses `solute_structure.interface_structure` for ice/water positions and `solute_structure.positions` for solute atoms. solute_molecule_indices are relative to solute_positions, NOT main positions.
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -m pytest tests/test_e2e_solute_export.py -v --timeout=120 -x</verify>
  <done>Solute export tests pass with all 7 validation checks for both Interface and Custom sources</done>
</task>

</tasks>

<verification>
1. pytest tests/test_e2e_custom_export.py passes (1 class, ~3 methods)
2. pytest tests/test_e2e_solute_export.py passes (2 classes, ~6 methods)
3. GRO residue ordering validated: SOL before custom before solute
4. TOP [molecules] section validated with correct CH4_L/ETOH names
5. ITP files validated for existence and [ moleculetype ]
6. Registry populated before writer use (no "LIQUID_CH4" fallback names)
</verification>

<success_criteria>
- tests/test_e2e_custom_export.py exists with 1 test class, all methods pass
- tests/test_e2e_solute_export.py exists with 2 test classes, all methods pass
- Custom export validates SOL→ETOH ordering and ITP bundling
- Solute from Interface validates SOL→CH4_L ordering
- Solute from Custom validates SOL→ETOH→CH4_L ordering (3 molecule types)
- All tests use real GenIce2 data, call writers directly
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-compute-export/e2e-compute-export-02-SUMMARY.md`
</output>
