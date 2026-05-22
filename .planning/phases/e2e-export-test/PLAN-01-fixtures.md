---
phase: e2e-export-test
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/test_output/conftest.py
autonomous: true

must_haves:
  truths:
    - "All structure fixtures produce valid dataclass instances"
    - "QFileDialog mock fixture returns tmp_path file path and suppresses QMessageBox"
    - "Hydrate-specific QFileDialog mock uses correct module path"
    - "Chain dependency fixtures build incrementally: interface -> custom -> solute -> ion"
    - "Custom molecule fixture uses existing etoh.itp from quickice/data/custom/"
  artifacts:
    - path: "tests/test_output/conftest.py"
      provides: "All shared fixtures for E2E export tests"
      min_lines: 200
  key_links:
    - from: "tests/test_output/conftest.py"
      to: "quickice/structure_generation/types.py"
      via: "import Candidate, InterfaceStructure, etc."
      pattern: "from quickice\\.structure_generation\\.types import"
    - from: "tests/test_output/conftest.py"
      to: "quickice/ranking/types.py"
      via: "import RankedCandidate"
      pattern: "from quickice\\.ranking\\.types import"
---

<objective>
Create shared conftest.py with all structure fixtures, QFileDialog/QMessageBox mock fixtures, and chain dependency fixtures needed by all 8 plan files.

Purpose: Single source of truth for test fixtures. Every subsequent plan (02-08) imports from this conftest. Without it, each test file would duplicate 100+ lines of fixture setup.

Output: `tests/test_output/conftest.py` with pytest fixtures covering all 6 structure types, both mock dialog paths (export.py and hydrate_export.py), and incremental chain dependencies.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/e2e-export-test/e2e-export-test-RESEARCH.md
@quickice/structure_generation/types.py
@quickice/ranking/types.py
@quickice/gui/export.py
@quickice/gui/hydrate_export.py
@quickice/structure_generation/moleculetype_registry.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create conftest.py with all structure and mock fixtures</name>
  <files>tests/test_output/conftest.py</files>
  <action>
Create `tests/test_output/conftest.py` with the following fixtures. Follow existing test patterns from `tests/test_output/test_validator.py` (hexagonal cell construction) and `tests/test_custom_molecule_panel_34_6.py` (QApplication singleton, InterfaceStructure mock construction).

**Structure fixtures (basic — standalone):**

1. `simple_candidate` — 1-molecule ice Candidate:
   - `positions`: np.array([[0.1, 0.1, 0.1], [0.15, 0.12, 0.1], [0.08, 0.12, 0.1]]) (3 atoms: O, H, H)
   - `atom_names`: ["O", "H", "H"]
   - `cell`: np.array([[0.9, 0.0, 0.0], [0.0, 0.78, 0.0], [0.0, 0.0, 0.72]])
   - `nmolecules`: 1, `phase_id`: "ice_ih", `seed`: 42, `metadata`: {}

2. `ranked_candidate(simple_candidate)` — wraps simple_candidate:
   - `candidate=simple_candidate`, `energy_score=0.0`, `density_score=0.0`, `diversity_score=0.0`, `rank=1`

3. `simple_hydrate_config` — minimal HydrateConfig:
   - `lattice_type="sI"`, `guest_type="ch4"`, `supercell_x=1`, `supercell_y=1`, `supercell_z=1`

4. `simple_hydrate_structure(simple_hydrate_config)` — minimal HydrateStructure:
   - `positions`: 9 atoms (4 water OW,HW1,HW2,MW + 5 CH4 C,H,H,H,H)
   - `atom_names`: ["OW","HW1","HW2","MW","OW","HW1","HW2","MW","C","H","H","H","H"]
   - `cell`: np.eye(3) * 1.2 (1.2 nm box)
   - `molecule_index`: [MoleculeIndex(0, 4, "water"), MoleculeIndex(4, 4, "water"), MoleculeIndex(8, 5, "ch4")]
   - `config=simple_hydrate_config`, `lattice_info=HydrateLatticeInfo.from_lattice_type("sI")`, `report="test"`, `guest_count=1`, `water_count=2`

5. `simple_interface` — 2 ice + 2 water, NO guests:
   - `positions`: np.zeros((14, 3)) — 6 ice atoms (2 × 3) + 8 water atoms (2 × 4)
   - `atom_names`: ["O","H","H","O","H","H","OW","HW1","HW2","MW","OW","HW1","HW2","MW"]
   - `cell`: np.eye(3) * 3.0
   - `ice_atom_count=6`, `water_atom_count=8`, `ice_nmolecules=2`, `water_nmolecules=2`, `mode="slab"`, `report="test"`, `guest_atom_count=0`, `guest_nmolecules=0`
   - `molecule_index`: [MoleculeIndex(0,3,"ice"), MoleculeIndex(3,3,"ice"), MoleculeIndex(6,4,"water"), MoleculeIndex(10,4,"water")]

6. `interface_with_ch4_guests(simple_interface)` — extends simple_interface with CH4 guests:
   - Positions: ice (6) + water (8) + 1 CH4 molecule (5 atoms: C,H,H,H,H)
   - `atom_names`: extends simple_interface list with ["C","H","H","H","H"]
   - `ice_atom_count=6`, `water_atom_count=8`, `guest_atom_count=5`, `guest_nmolecules=1`
   - `molecule_index`: extends simple_interface list with MoleculeIndex(14,5,"guest")

7. `interface_with_thf_guests` — variant with THF (13 atoms per molecule):
   - `atom_names` for THF: ["O","CA","CA","CB","CB","H","H","H","H","H","H","H","H"]
   - `guest_atom_count=13`, `guest_nmolecules=1`

**Chain dependency fixtures (incremental):**

8. `custom_structure(simple_interface)` — CustomMoleculeStructure using etoh.itp:
   - `itp_path`: Path("quickice/data/custom/etoh.itp") — MUST point to existing file
   - `positions`: np.zeros((22, 3)) — 14 interface + 8 custom atoms (2 ethanol × 4 atoms each, use etoh atom count from ITP)
   - Actually read etoh.itp to determine atom count, or use a fixed small number. For simplicity, use 9 atoms (1 ethanol molecule as per etoh.gro)
   - `moleculetype_name="ETOH"`, `custom_molecule_count=1`
   - `ice_atom_count=6`, `water_atom_count=8`, `custom_molecule_atom_count=9`, `guest_atom_count=0`
   - `interface_structure=simple_interface`
   - `molecule_index`: ice + water molecules from simple_interface + MoleculeIndex(14,9,"custom")

9. `solute_structure(interface_with_ch4_guests)` — SoluteStructure:
   - `positions`: 5 atoms (1 CH4: C,H,H,H,H)
   - `atom_names`: ["C","H","H","H","H"]
   - `cell`: same as interface
   - `solute_type="CH4"`, `n_molecules=1`, `molecule_indices=[(0,5)]`
   - `registry`: MoleculetypeRegistry with `registry.register_liquid_solute("CH4")`
   - `interface_structure=interface_with_ch4_guests`

10. `ion_structure(simple_interface)` — minimal IonStructure (no guests, no solutes, no custom):
    - `positions`: np.zeros((10, 3)) — 8 water atoms (2 × 4) + 1 NA + 1 CL
    - `atom_names`: ["OW","HW1","HW2","MW","OW","HW1","HW2","MW","NA","CL"]
    - `cell`: np.eye(3) * 3.0
    - `molecule_index`: [MoleculeIndex(0,4,"water"), MoleculeIndex(4,4,"water"), MoleculeIndex(8,1,"na"), MoleculeIndex(9,1,"cl")]
    - `na_count=1`, `cl_count=1`, `report="test"`

**Mock dialog fixtures:**

11. `mock_save_dialog(tmp_path)` — factory fixture for export.py QFileDialog:
    ```python
    @pytest.fixture
    def mock_save_dialog(tmp_path):
        """Factory: mock QFileDialog.getSaveFileName from quickice.gui.export."""
        def _mock_save(filename="test.gro"):
            save_path = str(tmp_path / filename)
            def decorator(func):
                from unittest.mock import patch
                with patch('quickice.gui.export.QFileDialog.getSaveFileName', return_value=(save_path, "GRO Files (*.gro)")):
                    with patch('quickice.gui.export.QMessageBox'):
                        return func()
                # This pattern won't work as a decorator. Use context manager pattern instead.
            return decorator
        return _mock_save
    ```
    **CORRECTED PATTERN** — use as a context manager, not decorator:
    ```python
    @pytest.fixture
    def mock_save_dialog(tmp_path):
        """Returns (exporter, save_path, patch objects) for export.py mocking."""
        def _create(filename="test.gro"):
            save_path = str(tmp_path / filename)
            dialog_patch = patch('quickice.gui.export.QFileDialog.getSaveFileName', return_value=(save_path, "GRO Files (*.gro)"))
            mb_patch = patch('quickice.gui.export.QMessageBox')
            return save_path, dialog_patch, mb_patch
        return _create
    ```

12. `mock_hydrate_save_dialog(tmp_path)` — same but for `quickice.gui.hydrate_export`:
    ```python
    @pytest.fixture
    def mock_hydrate_save_dialog(tmp_path):
        """Factory for hydrate_export.py QFileDialog mocking."""
        def _create(filename="hydrate_test.gro"):
            save_path = str(tmp_path / filename)
            dialog_patch = patch('quickice.gui.hydrate_export.QFileDialog.getSaveFileName', return_value=(save_path, "GRO Files (*.gro)"))
            mb_patch = patch('quickice.gui.hydrate_export.QMessageBox')
            return save_path, dialog_patch, mb_patch
        return _create
    ```

13. `mock_cancel_dialog` — returns empty string to simulate cancelled dialog:
    ```python
    @pytest.fixture
    def mock_cancel_dialog():
        """Factory for cancelled QFileDialog."""
        def _create(module_path='quickice.gui.export'):
            dialog_patch = patch(f'{module_path}.QFileDialog.getSaveFileName', return_value=("", ""))
            mb_patch = patch(f'{module_path}.QMessageBox')
            return dialog_patch, mb_patch
        return _create
    ```

**Import block at top of conftest.py:**
```python
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch

from quickice.structure_generation.types import (
    Candidate, InterfaceStructure, HydrateStructure, HydrateConfig,
    HydrateLatticeInfo, MoleculeIndex, IonStructure, SoluteStructure,
    CustomMoleculeStructure, CustomMoleculeConfig
)
from quickice.ranking.types import RankedCandidate
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
```

**Key constraints:**
- DO NOT create a QApplication fixture — export tests don't need a running Qt event loop. The exporters only use QFileDialog and QMessageBox as static method calls, which are fully mocked.
- All `positions` arrays must be real numpy arrays (not lists) because gromacs_writer accesses them with indexing.
- The `cell` arrays must be (3,3) shaped numpy arrays.
- `simple_interface` and `interface_with_ch4_guests` must have `molecule_index` populated because multiple exporters iterate over it for guest detection.
- `custom_structure.itp_path` MUST point to `Path("quickice/data/custom/etoh.itp")` which exists in the repo. Do NOT create a temp file for this.
- For `solute_structure.interface_structure`, use `interface_with_ch4_guests` (not simple_interface) so that `interface.guest_nmolecules > 0` triggers the guest ITP code path.
  </action>
  <verify>
    cd /share/home/nglokwan/quickice && python -c "import pytest; print('pytest ok')" && python -c "from quickice.structure_generation.types import Candidate, InterfaceStructure, HydrateStructure, HydrateConfig, HydrateLatticeInfo, MoleculeIndex, IonStructure, SoluteStructure, CustomMoleculeStructure; print('types ok')" && python -c "from quickice.ranking.types import RankedCandidate; print('ranked ok')" && python -c "from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry; print('registry ok')"
  </verify>
  <done>
    - tests/test_output/conftest.py exists with all 13+ fixtures
    - All imports resolve without errors
    - Fixtures use correct dataclass constructors matching types.py
    - custom_structure.itp_path points to existing file
    - solute_structure.interface_structure is not None
  </done>
</task>

</tasks>

<verification>
1. `python -m pytest tests/test_output/conftest.py --co -q` lists all fixtures without import errors
2. `python -c "from tests.test_output.conftest import *; print('imports ok')"` succeeds
3. Quick smoke test: `python -m pytest tests/test_output/conftest.py --fixtures -q | grep -c "simple_candidate\|ranked_candidate\|mock_save_dialog"` returns 3+
</verification>

<success_criteria>
- conftest.py exists with 13+ fixtures covering all 6 structure types
- Both mock dialog paths (export.py and hydrate_export.py) available
- Chain dependency fixtures build incrementally
- custom_structure.itp_path points to existing quickice/data/custom/etoh.itp
- All imports from quickice.structure_generation.types, quickice.ranking.types, moleculetype_registry succeed
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-export-test/e2e-export-test-01-SUMMARY.md`
</output>
