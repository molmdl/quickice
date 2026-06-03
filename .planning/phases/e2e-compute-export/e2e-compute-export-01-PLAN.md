---
phase: e2e-compute-export
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/e2e_export_helpers.py
  - tests/test_e2e_ice_interface_export.py
autonomous: true

must_haves:
  truths:
    - "Ice candidate exported via write_gro_file produces valid .gro with only SOL residues"
    - "Interface structure exported produces .gro with SOL before guests"
    - "Interface+hydrate structure exported produces .gro with SOL before CH4/THF guest residues"
    - "GRO atom count header matches actual atom lines for ice, interface, and hydrate-interface exports"
    - "TOP [molecules] section lists correct molecule type counts for every export level"
  artifacts:
    - path: "tests/e2e_export_helpers.py"
      provides: "GRO/TOP/ITP parsing functions + chain-building helpers"
      exports: ["parse_gro_residue_names", "parse_gro_atom_count", "parse_top_molecules", "parse_top_includes", "check_itp_moleculetype", "_insert_custom_molecules", "_insert_solutes", "_solute_to_ion_source", "_insert_ions", "_insert_ions_from_solute"]
    - path: "tests/test_e2e_ice_interface_export.py"
      provides: "Single-structure export tests for Ice + Interface (3 scenarios)"
      contains: "class TestIceCandidateExport"
  key_links:
    - from: "tests/e2e_export_helpers.py"
      to: "tests/test_e2e_ice_interface_export.py"
      via: "import of parse_gro_residue_names and parse_top_molecules"
      pattern: "from e2e_export_helpers import"
    - from: "tests/test_e2e_ice_interface_export.py"
      to: "quickice/output/gromacs_writer.py"
      via: "direct writer function calls"
      pattern: "write_(gro|top|interface_gro|interface_top)_file"
---

<objective>
Create the shared test helpers module and first single-structure export validation tests for Ice and Interface structure types.

Purpose: Establish the foundation (parsing helpers + chain builders) that all subsequent plans depend on, and validate that the simplest export paths (Ice Candidate + Interface with/without guests) produce valid GROMACS output from real GenIce2-generated structures.

Output: tests/e2e_export_helpers.py (shared helpers) + tests/test_e2e_ice_interface_export.py (3 test classes, ~9 test methods)
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
@tests/conftest.py
@tests/test_e2e_workflow_chains.py
@tests/test_gromacs_molecule_ordering.py
@quickice/output/gromacs_writer.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create shared test helpers module</name>
  <files>tests/e2e_export_helpers.py</files>
  <action>
Create tests/e2e_export_helpers.py (NOT test_-prefixed — avoids pytest auto-collection). This module contains ALL parsing and chain-building helpers used by bridge test files.

**GRO/TOP/ITP parsing functions** (based on test_gromacs_molecule_ordering.py lines 20-62 + new additions):

1. `parse_gro_residue_names(gro_path: str) -> list[str]` — Copy from test_gromacs_molecule_ordering.py lines 20-62. Parse residue names from columns [5:10] of each atom line. Skip lines < 20 chars and box vector lines.

2. `parse_gro_atom_count(gro_path: str) -> int` — Read line 2 (atom count) from .gro file. Return int.

3. `parse_top_molecules(top_path: str) -> dict[str, int]` — Parse [ molecules ] section. Track whether we're inside [ molecules ] by detecting `[` brackets. Skip comment lines (starting with `;`) and blank lines. Return dict of molecule_name -> count.

4. `parse_top_includes(top_path: str) -> list[str]` — Parse all #include directives. Extract filename between double quotes. Return list of ITP filenames.

5. `check_itp_has_moleculetype(itp_path: str) -> bool` — Open ITP file, check if `[ moleculetype ]` appears anywhere. Return True/False.

6. `assert_gro_residue_ordering(residue_names: list[str], expected_order: list[str])` — Assert that residue names appear in the specified order with no interleaving. For each pair of consecutive expected types, find the last index of the first type and first index of the second type, assert last < first. Skip types not present in residue_names.

**Chain-building helpers** (COPY from test_e2e_workflow_chains.py lines 37-169, do NOT import from that file):

7. `DATA_DIR`, `ETOH_GRO`, `ETOH_ITP` — Paths to quickice/data/custom/etoh.gro and etoh.itp

8. `_liquid_volume_nm3(structure) -> float` — Copy from lines 46-52

9. `_insert_custom_molecules(interface, n_molecules=3)` — Copy from lines 55-64

10. `_insert_solutes(source_structure, solute_type='CH4', concentration=0.3, seed=42)` — Copy from lines 67-71

11. `_solute_to_ion_source(solute)` — Copy from lines 74-96 (BUG I5 workaround, MANDATORY for solute→ion chains)

12. `_insert_ions(source_structure, concentration=0.15, seed=42)` — Copy from lines 99-105

13. `_insert_ions_from_solute(solute, concentration=0.15, seed=42)` — Copy from lines 108-111

14. `_hydrate_sI_ch4_candidate()` — Copy from lines 114-126

15. `_hydrate_sI_thf_candidate()` — Copy from lines 128-140

16. `_make_slab_interface(candidate, ...)` — Copy from lines 142-154

17. `_make_pocket_interface(candidate, ...)` — Copy from lines 157-169

**Imports needed:**
```python
import numpy as np
from pathlib import Path
from quickice.structure_generation.generator import IceStructureGenerator
from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.ion_inserter import IonInserter
from quickice.structure_generation.solute_inserter import SoluteInserter
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
from quickice.structure_generation.types import (
    InterfaceConfig, HydrateConfig, IonConfig, IonStructure,
    SoluteConfig, SoluteStructure, CustomMoleculeConfig, CustomMoleculeStructure, MoleculeIndex,
)
```

**IMPORTANT:** Do NOT add these helpers to conftest.py. The `from conftest import X` syntax is unreliable in pytest. Use this separate module and import with `from e2e_export_helpers import ...`.
  </action>
  <verify>python -c "from e2e_export_helpers import parse_gro_residue_names, parse_gro_atom_count, parse_top_molecules, parse_top_includes, check_itp_has_moleculetype, assert_gro_residue_ordering, _insert_custom_molecules, _insert_solutes, _solute_to_ion_source, _insert_ions, _insert_ions_from_solute" — all imports succeed</verify>
  <done>e2e_export_helpers.py exists with all 17 functions/constants, all importable, no pytest collection issues</done>
</task>

<task type="auto">
  <name>Task 2: Create Ice/Interface single-structure export validation tests</name>
  <files>tests/test_e2e_ice_interface_export.py</files>
  <action>
Create tests/test_e2e_ice_interface_export.py with 3 test classes covering 3 single-structure export scenarios.

**Scenario 1: Ice Candidate Export** (class `TestIceCandidateExport`)
- Uses `ice_ih_candidate` fixture from conftest.py
- Calls `write_gro_file(candidate, gro_path)` and `write_top_file(candidate, top_path)`
- Validates:
  - GRO residue names: only "SOL" present (ice is all SOL)
  - GRO atom count: header matches actual atom lines (remember: ice_nmolecules * 4 for TIP4P-ICE expansion)
  - TOP [molecules]: `{"SOL": ice_nmolecules}`
  - TOP #include: `["tip4p-ice.itp"]`
  - ITP tip4p-ice.itp exists in quickice/data/ and has [ moleculetype ]
  - Atom conservation: positions.shape[0] == sum of all molecule counts * atoms_per_molecule (ice * 4)

**Scenario 2: Interface (no guests) Export** (class `TestInterfaceExport`)
- Uses `interface_slab` fixture from conftest.py
- Calls `write_interface_gro_file(iface, gro_path)` and `write_interface_top_file(iface, top_path)`
- Validates:
  - GRO residue names: only "SOL" present (ice + water both SOL)
  - GRO atom count: header matches actual lines (ice_nmolecules * 4 + water_nmolecules * 4)
  - TOP [molecules]: `{"SOL": ice_nmolecules + water_nmolecules}`
  - TOP #include: `["tip4p-ice.itp"]` (no guest ITP since no guests)
  - ITP tip4p-ice.itp exists and has [ moleculetype ]

**Scenario 3: Interface + Hydrate Guests Export** (class `TestInterfaceHydrateExport`)
- Uses `interface_hydrate_slab` fixture from conftest.py
- Calls `write_interface_gro_file(iface, gro_path)` and `write_interface_top_file(iface, top_path)`
- Validates:
  - GRO residue names: "SOL" before guest residue name (CH4 for CH4 hydrate)
  - GRO atom count: header matches actual lines
  - TOP [molecules]: `{"SOL": ice_nmolecules + water_nmolecules, "CH4": guest_nmolecules}` (guest res name from get_hydrate_guest_residue_name)
  - TOP #include: `["tip4p-ice.itp", "ch4_hydrate.itp"]`
  - ITP ch4_hydrate.itp exists in quickice/data/ and has [ moleculetype ]
  - No interleaving of SOL and guest residues

**Implementation notes:**
- Use `tmp_path` fixture for output directories (pytest built-in)
- Import parsing functions from e2e_export_helpers: `from e2e_export_helpers import parse_gro_residue_names, parse_gro_atom_count, parse_top_molecules, parse_top_includes, check_itp_has_moleculetype, assert_gro_residue_ordering`
- Import writer functions from quickice.output.gromacs_writer
- For ITP existence checks, use `Path(quickice.__file__).parent / "data" / itp_name` to locate data files
- TIP4P-ICE expansion: ice_nmolecules * 4 atoms (NOT * 3) — MW virtual site added at export
- GRO residue names at columns [5:10] (0-indexed) — 5-char limit
- Hydrate candidate has 4-atom ice (OW, HW1, HW2, MW already), so no 3→4 expansion needed for interface_hydrate_slab
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -m pytest tests/test_e2e_ice_interface_export.py -v --timeout=120 -x</verify>
  <done>3 test classes with ~9 test methods all pass, validating Ice/Interface export bridge with real GenIce2 data</done>
</task>

</tasks>

<verification>
1. All imports from e2e_export_helpers.py succeed
2. pytest tests/test_e2e_ice_interface_export.py passes (3 classes, ~9 methods)
3. No conftest.py modifications needed (helpers in separate module)
4. All test methods use real GenIce2 fixtures (not synthetic)
5. All test methods call writer functions directly (no QFileDialog mocking)
</verification>

<success_criteria>
- tests/e2e_export_helpers.py exists with 17 functions/constants, all importable
- tests/test_e2e_ice_interface_export.py exists with 3 test classes
- All tests pass with real GenIce2 data
- GRO residue ordering validated for ice (SOL only) and interface (SOL + guests)
- TOP [molecules] section validated for all 3 scenarios
- ITP files validated for existence and [ moleculetype ] section
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-compute-export/e2e-compute-export-01-SUMMARY.md`
</output>
