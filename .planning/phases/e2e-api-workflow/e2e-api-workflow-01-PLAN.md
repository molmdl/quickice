---
phase: e2e-api-workflow
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/conftest.py
  - tests/test_e2e_ice_generation.py
  - tests/test_e2e_hydrate_generation.py
autonomous: true

must_haves:
  truths:
    - "Ice generation produces valid Candidate objects with correct phase_id"
    - "All orthogonal ice phases generate successfully (Ih, Ic, III, VI, VII, VIII)"
    - "Hydrate generation produces valid HydrateStructure with guest molecules"
    - "Hydrate sI and sII work with both CH4 and THF guests"
    - "Shared conftest.py provides reusable module-scoped fixtures for downstream tests"
  artifacts:
    - path: "tests/conftest.py"
      provides: "Module-scoped fixtures: ice_candidate, hydrate_sI_ch4_candidate, interface_structure, etc."
      contains: "@pytest.fixture(scope='module')"
    - path: "tests/test_e2e_ice_generation.py"
      provides: "5 ice generation e2e tests"
      exports: ["test_ice_ih_generation", "test_all_orthogonal_phases"]
    - path: "tests/test_e2e_hydrate_generation.py"
      provides: "8 hydrate generation e2e tests"
      exports: ["test_hydrate_sI_ch4_generation", "test_hydrate_sII_thf_generation"]
  key_links:
    - from: "tests/conftest.py"
      to: "quickice/structure_generation/generator.py"
      via: "IceStructureGenerator(phase_info, 96).generate_all(1)"
      pattern: "IceStructureGenerator"
    - from: "tests/conftest.py"
      to: "quickice/structure_generation/hydrate_generator.py"
      via: "HydrateStructureGenerator().generate(config)"
      pattern: "HydrateStructureGenerator"
---

<objective>
Create shared e2e test fixtures and ice/hydrate generation tests

Purpose: Establish the reusable fixture foundation (conftest.py with module-scoped real generation fixtures) and test the two upstream pipeline stages: ice generation (Workflow 2) and hydrate generation (Workflow 3). These fixtures amortize expensive GenIce2 calls (~3-5s each) across all downstream test files.

Output: tests/conftest.py with 8+ module-scoped fixtures, tests/test_e2e_ice_generation.py with ~5 tests, tests/test_e2e_hydrate_generation.py with ~8 tests
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
@quickice/structure_generation/types.py
@quickice/structure_generation/generator.py
@quickice/structure_generation/hydrate_generator.py
@quickice/structure_generation/interface_builder.py
@quickice/structure_generation/errors.py
@quickice/phase_mapping/lookup.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create shared e2e conftest.py with module-scoped fixtures</name>
  <files>tests/conftest.py</files>
  <action>
Create `tests/conftest.py` with module-scoped pytest fixtures for REAL structure generation (not synthetic). These fixtures amortize expensive GenIce2 calls across test modules.

Required fixtures (all `scope="module"`):

1. `ice_ih_candidate` — Ice Ih candidate: `lookup_phase(250, 0.1)` → `IceStructureGenerator(phase_info, 96).generate_all(1)[0]`
2. `ice_ic_candidate` — Ice Ic candidate: `lookup_phase(250, 0.1)` with `phase_id='ice_ic'` (if different T/P needed, use appropriate lookup)
3. `hydrate_sI_ch4_candidate` — Hydrate sI + CH4: `HydrateStructureGenerator().generate(HydrateConfig(lattice_type='sI', guest_type='ch4', supercell_x=1, supercell_y=1, supercell_z=1))` → `.to_candidate()`
4. `hydrate_sI_thf_candidate` — Hydrate sI + THF: same with `guest_type='thf'`
5. `hydrate_sII_ch4_candidate` — Hydrate sII + CH4: `lattice_type='sII'`
6. `interface_slab` — Interface from ice_ih_candidate: `generate_interface(ice_ih_candidate, InterfaceConfig(mode='slab', box_x=3.0, box_y=3.0, box_z=8.0, seed=42, ice_thickness=2.0, water_thickness=4.0))`
7. `interface_pocket` — Pocket interface: `InterfaceConfig(mode='pocket', box_x=3.0, box_y=3.0, box_z=8.0, seed=42, pocket_diameter=1.5, pocket_shape='sphere')`
8. `interface_hydrate_slab` — Interface from hydrate sI+CH4: `generate_interface(hydrate_sI_ch4_candidate, InterfaceConfig(mode='slab', box_x=3.0, box_y=3.0, box_z=8.0, seed=42, ice_thickness=2.0, water_thickness=4.0))`

Imports needed:
```python
import pytest
import numpy as np
from quickice.phase_mapping.lookup import lookup_phase
from quickice.structure_generation.generator import IceStructureGenerator
from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.types import InterfaceConfig, HydrateConfig
```

IMPORTANT: Do NOT add a `qtbot` or `QApplication` fixture — these tests are API-only, no GUI.
IMPORTANT: Do NOT nest test files in subdirectories — project convention is flat `tests/` directory.
IMPORTANT: Use `@pytest.fixture(scope="module")` for all expensive fixtures. Function-scoped only for cheap derived fixtures.
  </action>
  <verify>`python -c "from tests.conftest import *"` or `pytest tests/conftest.py --collect-only` shows fixtures; no import errors</verify>
  <done>tests/conftest.py exists with 8+ module-scoped fixtures providing real ice/hydrate/interface structures</done>
</task>

<task type="auto">
  <name>Task 2: Create ice generation e2e tests</name>
  <files>tests/test_e2e_ice_generation.py</files>
  <action>
Create `tests/test_e2e_ice_generation.py` covering Workflow 2 (Ice Generation). ~5 tests.

Tests to create:

1. `test_ice_ih_generation_produces_valid_candidate` — Generate Ice Ih with `lookup_phase(250, 0.1)` and `IceStructureGenerator(phase_info, 96).generate_all(1)`. Verify: `len(candidates) >= 1`, candidate has `.positions.shape[1] == 3`, `.cell.shape == (3,3)`, `.nmolecules > 0`, `.phase_id == "ice_ih"`, `np.all(np.isfinite(candidate.positions))`.

2. `test_all_orthogonal_phases_generate_successfully` — Parameterized test over `["ice_ih", "ice_ic", "ice_iii", "ice_vi", "ice_vii", "ice_viii"]`. For each, call `lookup_phase` with appropriate T/P (use 250K/0.1MPa for all — lookup_phase handles phase stability), generate, verify positions/cell/nmolecules are valid. Use `pytest.mark.slow` if any take >5s.

3. `test_ice_candidate_has_correct_atom_count` — Verify `len(candidate.positions) == candidate.nmolecules * 3` for TIP3P ice (3 atoms: O, H, H), OR `len(candidate.positions) == candidate.nmolecules * 4` for TIP4P ice. Check `len(candidate.atom_names) == len(candidate.positions)`.

4. `test_ice_cell_has_positive_volume` — Verify `np.linalg.det(candidate.cell) > 0`.

5. `test_ice_positions_within_cell` — Verify all atom positions are within the cell boundaries (using PBC: positions mod cell should be within [0, 1] for fractional coords, or equivalently positions should be near the cell).

Use the `ice_ih_candidate` fixture from conftest.py for test 1/3/4/5. Generate new candidates inline for test 2 (parameterized).
  </action>
  <verify>`pytest tests/test_e2e_ice_generation.py -v --collect-only` shows 5+ tests; `pytest tests/test_e2e_ice_generation.py -v` passes</verify>
  <done>5 ice generation tests pass, covering all orthogonal phases and structural invariants</done>
</task>

<task type="auto">
  <name>Task 3: Create hydrate generation e2e tests</name>
  <files>tests/test_e2e_hydrate_generation.py</files>
  <action>
Create `tests/test_e2e_hydrate_generation.py` covering Workflow 3 (Hydrate Generation). ~8 tests.

Tests to create:

1. `test_hydrate_sI_ch4_generation` — Generate sI+CH4 hydrate. Verify: `structure.guest_count > 0`, `structure.water_count > 0`, `len(structure.positions) > 0`, structure has `molecule_index` with "ch4" type entries.

2. `test_hydrate_sI_thf_generation` — Generate sI+THF. Same structural checks. THF guests have 13 atoms each.

3. `test_hydrate_sII_ch4_generation` — Generate sII+CH4. More cages than sI.

4. `test_hydrate_sII_thf_generation` — Generate sII+THF.

5. `test_hydrate_to_candidate_preserves_guests` — `structure.to_candidate()` should have `metadata['guest_type_counts']` with CH4 or THF entries, `nmolecules == water_count + guest_count`.

6. `test_hydrate_guest_atom_count_correct` — For CH4 hydrate: `guest_atom_count == guest_count * 5`. For THF: `guest_atom_count == guest_count * 13`.

7. `test_hydrate_molecule_index_tracks_all_molecules` — `len(structure.molecule_index) == water_count + guest_count`. Each entry has `mol_type` in ("water", "ch4", "thf").

8. `test_hydrate_invalid_lattice_raises_error` — `HydrateConfig(lattice_type='invalid', guest_type='ch4')` → `pytest.raises(ValueError)`.

Use conftest fixtures where available. Generate new structures inline for parameterized tests.

IMPORTANT: Hydrate sH may fail with some guest types in GenIce2. If sH+THF fails, mark it `pytest.mark.xfail(reason="sH+THF may not be supported by GenIce2")`.
  </action>
  <verify>`pytest tests/test_e2e_hydrate_generation.py -v` passes with 8+ tests</verify>
  <done>8 hydrate generation tests pass, covering sI/sII × ch4/thf, to_candidate conversion, and error cases</done>
</task>

</tasks>

<verification>
```bash
# All ice + hydrate tests pass
pytest tests/test_e2e_ice_generation.py tests/test_e2e_hydrate_generation.py -v

# conftest fixtures can be imported
python -c "import tests.conftest"

# Verify fixture count
grep -c "@pytest.fixture" tests/conftest.py
```
</verification>

<success_criteria>
1. tests/conftest.py has 8+ module-scoped fixtures for real structure generation
2. test_e2e_ice_generation.py has 5+ tests, all pass
3. test_e2e_hydrate_generation.py has 8+ tests, all pass
4. All orthogonal ice phases (Ih, Ic, III, VI, VII, VIII) generate successfully
5. All sI/sII × ch4/thf hydrate combinations generate successfully
6. Total test runtime < 60s (module-scoped fixtures amortize generation cost)
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-api-workflow/e2e-api-workflow-01-SUMMARY.md`
</output>
