# Testing Patterns

**Analysis Date:** 2026-05-22

## Test Framework

**Runner:**
- pytest 9.0+ (from `requirements-dev.txt`)
- Config: No `pytest.ini` or `pyproject.toml` `[tool.pytest]` section — uses defaults
- Total tests: 537 collected (as of 2026-05-22)

**Assertion Library:**
- Plain `assert` statements (no `assertEqual`, `assertRaises`, etc.)
- Custom assertion messages with f-strings for clarity

**Run Commands:**
```bash
python -m pytest                    # Run all tests
python -m pytest tests/test_pocket_invariants.py  # Specific file
python -m pytest -k "pocket"        # By keyword
python -m pytest --co -q            # List collected tests
```

**Coverage:**
- `.coverage` file present at project root (coverage.py)
- No minimum coverage threshold enforced
- No coverage reporting command in CI

## Test File Organization

**Location:**
- Co-located in `tests/` directory at project root
- E2E export tests in subdirectory: `tests/test_output/`
- No `__init__.py` in `tests/` (uses pytest autodiscovery)
- `tests/test_output/__init__.py` present for subdirectory discovery

**Naming:**
- Unit tests: `test_{feature_or_module}.py`
  - Examples: `test_overlap_removal_invariants.py`, `test_itp_parser_edge_cases.py`
- E2E tests: `test_gromacs_export_{type}.py` in `tests/test_output/`
  - Examples: `test_gromacs_export_interface.py`, `test_gromacs_export_ice.py`

**Structure:**
```
tests/
├── __init__.py
├── test_atom_names_filtering.py
├── test_atom_ordering_validation.py
├── test_cli_integration.py
├── test_custom_molecule.py
├── test_custom_molecule_concentration.py
├── test_custom_molecule_panel_34_6.py
├── test_custom_molecule_renderer.py
├── test_gromacs_molecule_ordering.py
├── test_hydrate_guest_tiling.py
├── test_ice_ih_density.py
├── test_integration_v35.py
├── test_interface_modes_audit.py
├── test_interface_ordering_validation.py
├── test_ion_hydrate_fix.py
├── test_ion_source_dropdown.py
├── test_itp_parser_edge_cases.py
├── test_med03_minimum_box_size.py
├── test_moleculetype_registry.py
├── test_output/
│   ├── __init__.py
│   ├── conftest.py              # Shared E2E fixtures
│   ├── test_gromacs_export_chain.py
│   ├── test_gromacs_export_custom.py
│   ├── test_gromacs_export_hydrate.py
│   ├── test_gromacs_export_ice.py
│   ├── test_gromacs_export_interface.py
│   ├── test_gromacs_export_ion.py
│   ├── test_gromacs_export_solute.py
│   ├── test_molecule_wrapping.py
│   ├── test_pdb_writer.py
│   └── test_validator.py
├── test_overlap_removal_invariants.py
├── test_pbc_hbonds.py
├── test_phase_mapping.py
├── test_piece_mode_validation.py
├── test_pocket_cubic_guests.py
├── test_pocket_edge_cases.py
├── test_pocket_invariants.py
├── test_ranking.py
├── test_solute_insertion.py
├── test_solute_ion_molecule_index.py
├── test_structure_generation.py
├── test_triclinic_interface.py
├── test_validators.py
└── test_water_density.py
```

## Test Structure

**Suite Organization:**
```python
class TestWaterAtomCountDivisibleByFour:
    """Invariant: water atom count % 4 == 0 after overlap removal.

    TIP4P water has 4 atoms per molecule (OW, HW1, HW2, MW).
    remove_overlapping_molecules always removes whole molecules, so
    if input atom count is divisible by 4, output must be too.
    """

    def _make_water_positions(self, n_molecules: int) -> np.ndarray:
        """Create n_molecules water molecule positions (4 atoms each)."""
        positions = []
        for i in range(n_molecules):
            x = float(i)
            positions.append([x, 0.0, 0.0])       # OW
            positions.append([x + 0.08, 0.06, 0.0])  # HW1
            positions.append([x - 0.08, 0.06, 0.0])  # HW2
            positions.append([x, 0.015, 0.0])      # MW
        return np.array(positions)

    def test_no_overlap_count_divisible_by_4(self):
        positions = self._make_water_positions(10)
        overlapping = set()
        result, n_remaining = remove_overlapping_molecules(
            positions, overlapping, atoms_per_molecule=4
        )
        assert len(result) % 4 == 0
        assert n_remaining == 10
```
File: `tests/test_overlap_removal_invariants.py`

**Patterns:**
- **Class-per-test-group**: `Test{FeatureName}` classes grouping related tests
- **Helper methods**: Private `_make_*` and `_create_*` methods for test data construction
- **Parametrized tests**: `@pytest.mark.parametrize` for shape variants:
  ```python
  @pytest.mark.parametrize("shape", ["sphere", "cubic"])
  def test_pocket_boundary_conditions(self, shape):
  ```
  File: `tests/test_pocket_edge_cases.py`
- **Skip marks**: `@pytest.mark.skip(reason="pytest-qt not installed in test environment")`
  File: `tests/test_solute_insertion.py`

**Setup/Teardown:**
- No `setUp`/`tearDown` methods (pytest style)
- `@pytest.fixture` for shared setup
- `autouse=True` fixtures for GUI tests:
  ```python
  @pytest.fixture(autouse=True)
  def setup_app(self, qapp):
      self.app = qapp
  ```
  File: `tests/test_custom_molecule_panel_34_6.py`

## Mocking

**Framework:** `unittest.mock` (stdlib) via `from unittest.mock import patch`

**QFileDialog mocking pattern** (established for E2E export tests):
```python
@pytest.fixture
def mock_save_dialog(tmp_path):
    """Factory fixture for export.py QFileDialog mocking.

    Returns a callable that creates (save_path, dialog_patch, mb_patch).

    Usage in tests::

        def test_example(mock_save_dialog):
            save_path, dialog_patch, mb_patch = mock_save_dialog("output.gro")
            with dialog_patch, mb_patch:
                # code under test that calls QFileDialog.getSaveFileName
                ...
            assert Path(save_path).exists()
    """
    def _create(filename="test.gro"):
        save_path = str(tmp_path / filename)
        dialog_patch = patch(
            'quickice.gui.export.QFileDialog.getSaveFileName',
            return_value=(save_path, "GRO Files (*.gro)")
        )
        mb_patch = patch('quickice.gui.export.QMessageBox')
        return save_path, dialog_patch, mb_patch
    return _create
```
File: `tests/test_output/conftest.py` (lines 426-449)

**QMessageBox mocking pattern:**
```python
mb_patch = patch('quickice.gui.export.QMessageBox')
# Used alongside dialog_patch in `with dialog_patch, mb_patch:` context
```

**Cancelled dialog mocking pattern:**
```python
@pytest.fixture
def mock_cancel_dialog():
    """Factory fixture for cancelled QFileDialog simulation.

    Returns empty string ("", "") from getSaveFileName.
    """
    def _create(module_path='quickice.gui.export'):
        dialog_patch = patch(
            f'{module_path}.QFileDialog.getSaveFileName',
            return_value=("", "")
        )
        mb_patch = patch(f'{module_path}.QMessageBox')
        return dialog_patch, mb_patch
    return _create
```
File: `tests/test_output/conftest.py` (lines 477-499)

**What to Mock:**
- `QFileDialog.getSaveFileName` — always mock in export tests (opens native dialog)
- `QMessageBox` — always mock alongside dialog mocks (may show warning dialogs)
- Module path must be where the name is **looked up**, not where it's defined:
  - `'quickice.gui.export.QFileDialog.getSaveFileName'` (not `'PySide6.QtWidgets...'`)
  - `'quickice.gui.hydrate_export.QFileDialog.getSaveFileName'` for hydrate export

**What NOT to Mock:**
- Structure generation functions (use real `assemble_pocket()`, `assemble_slab()`)
- Overlap detection (`detect_overlaps`, `remove_overlapping_molecules`)
- ITP/GRO parsers (use real `parse_itp_file()`, `parse_gro_file()`)
- GROMACS writers (write to `tmp_path` and verify file contents)

## Fixtures and Factories

**Test Data (Structure Fixtures):**
```python
@pytest.fixture
def simple_interface():
    """InterfaceStructure: 2 ice molecules + 2 water molecules, NO guests.

    14 atoms total:
        - 6 ice atoms:  2 × (O, H, H)
        - 8 water atoms: 2 × (OW, HW1, HW2, MW)
    """
    positions = np.zeros((14, 3))
    positions[0:3] = np.array([[0.1, 0.1, 0.1], [0.15, 0.12, 0.1], [0.08, 0.12, 0.1]])
    positions[3:6] = np.array([[0.2, 0.1, 0.1], [0.25, 0.12, 0.1], [0.18, 0.12, 0.1]])
    positions[6:10] = np.array([[0.5, 0.5, 2.0], [0.55, 0.52, 2.0],
                                [0.48, 0.52, 2.0], [0.50, 0.51, 2.0]])
    positions[10:14] = np.array([[1.0, 0.5, 2.0], [1.05, 0.52, 2.0],
                                  [0.98, 0.52, 2.0], [1.00, 0.51, 2.0]])
    atom_names = ["O", "H", "H", "O", "H", "H",
                  "OW", "HW1", "HW2", "MW", "OW", "HW1", "HW2", "MW"]
    cell = np.eye(3) * 3.0
    molecule_index = [
        MoleculeIndex(0, 3, "ice"), MoleculeIndex(3, 3, "ice"),
        MoleculeIndex(6, 4, "water"), MoleculeIndex(10, 4, "water"),
    ]
    return InterfaceStructure(
        positions=positions, atom_names=atom_names, cell=cell,
        ice_atom_count=6, water_atom_count=8, ice_nmolecules=2,
        water_nmolecules=2, mode="slab", report="test",
        guest_atom_count=0, guest_nmolecules=0, molecule_index=molecule_index,
    )
```
File: `tests/test_output/conftest.py` (lines 142-188)

**Mock Candidate Factories:**
```python
def create_mock_ice_candidate(n_molecules: int = 96, cell_dim: float = 0.9) -> Candidate:
    """Create a mock Ice Ih candidate with configurable molecule count."""
    grid = int(np.ceil(n_molecules ** (1/3)))
    positions = []
    atom_names = []
    spacing_x = cell_dim / grid
    for i in range(n_molecules):
        ix = i % grid
        iy = (i // grid) % grid
        iz = i // (grid * grid)
        x = ix * spacing_x
        y = iy * spacing_x
        z = iz * spacing_x
        positions.extend([[x, y, z], [x + 0.1, y, z + 0.05], [x + 0.05, y + 0.1, z + 0.1]])
        atom_names.extend(["O", "H", "H"])
    positions = np.array(positions)
    cell = np.diag([cell_dim, cell_dim, cell_dim])
    return Candidate(
        positions=positions, atom_names=atom_names, cell=cell,
        nmolecules=n_molecules, phase_id="ice_ih", seed=42,
        metadata={"temperature": 273.15, "pressure": 0.101325}
    )
```
File: `tests/test_pocket_invariants.py` (lines 18-55)

```python
def create_mock_hydrate_candidate(n_water: int = 32, n_guest: int = 4,
                                   cell_dim: float = 0.9) -> Candidate:
    """Create a mock hydrate candidate with TIP4P water framework + Me guests."""
```
File: `tests/test_pocket_invariants.py` (lines 58-106)

**Chain dependency fixtures:**
- `custom_structure` depends on `simple_interface`
- `solute_structure` depends on `interface_with_ch4_guests`
- `ion_structure` depends on `simple_interface`
File: `tests/test_output/conftest.py` (lines 296-419)

**Location:**
- Structure fixtures: `tests/test_output/conftest.py`
- Mock candidate factories: defined as module-level functions in individual test files
- `tests/test_ranking/conftest.py` style: inline `@pytest.fixture` in test classes

**Temp file pattern:**
```python
def _write_and_parse(content: str) -> ITPMoleculeInfo:
    """Write ITP content to a temp file, parse it, and return the result."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".itp", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        tmp_path = Path(f.name)
    try:
        return parse_itp_file(tmp_path)
    finally:
        tmp_path.unlink()
```
File: `tests/test_itp_parser_edge_cases.py` (lines 37-47)

## Coverage

**Requirements:** None enforced (no minimum threshold)

**View Coverage:**
```bash
python -m pytest --cov=quickice --cov-report=term-missing
```

**Current coverage file:** `.coverage` (present at project root)

## Test Types

**Unit Tests:**
- Scope: Individual functions and classes
- Approach: Mock external dependencies, test logic directly
- Examples:
  - `test_overlap_removal_invariants.py`: Tests `remove_overlapping_molecules`, `filter_atom_names`, `detect_overlaps` directly
  - `test_itp_parser_edge_cases.py`: Tests `parse_itp_file()` with crafted temp files
  - `test_validators.py`: Tests CLI and GUI validator functions

**Integration Tests:**
- Scope: End-to-end structure generation pipelines
- Approach: Call `assemble_pocket()`, `assemble_slab()` with mock candidates (no GenIce2 dependency)
- Examples:
  - `test_pocket_invariants.py`: Calls `assemble_pocket()` end-to-end with `create_mock_ice_candidate()`
  - `test_structure_generation.py`: Tests the full generation pipeline

**E2E Export Tests:**
- Scope: Full GROMACS file export with dialog mocking
- Approach: Mock `QFileDialog`/`QMessageBox`, call exporter, verify file contents
- Examples:
  - `test_gromacs_export_interface.py`: Tests `InterfaceGROMACSExporter` end-to-end
  - `test_gromacs_export_ice.py`: Tests `GROMACSExporter` end-to-end
  - `test_gromacs_export_hydrate.py`: Tests `HydrateGROMACSExporter` end-to-end

**E2E Test coverage by tab:**
| Test File | Tab | Structure Fixture |
|-----------|-----|-------------------|
| `test_gromacs_export_ice.py` | Tab 1 (Ice) | `simple_candidate`, `ranked_candidate` |
| `test_gromacs_export_interface.py` | Tab 2 (Interface) | `simple_interface`, `interface_with_ch4_guests`, `interface_with_thf_guests` |
| `test_gromacs_export_custom.py` | Tab 3 (Custom) | `custom_structure` |
| `test_gromacs_export_solute.py` | Tab 4 (Solute) | `solute_structure` |
| `test_gromacs_export_ion.py` | Tab 5 (Ion) | `ion_structure` |
| `test_gromacs_export_hydrate.py` | Tab 6 (Hydrate) | `simple_hydrate_structure` |
| `test_gromacs_export_chain.py` | Chain dependency | Combines above |

**E2E Tests Not Used:** No browser/protocol testing (desktop app)

## Common Patterns

**Invariant testing pattern:**
```python
# Test the invariant directly
def test_no_overlap_count_divisible_by_4(self):
    positions = self._make_water_positions(10)
    overlapping = set()
    result, n_remaining = remove_overlapping_molecules(
        positions, overlapping, atoms_per_molecule=4
    )
    assert len(result) % 4 == 0
    assert n_remaining == 10

# Test end-to-end through the code that has the assertion
def test_sphere_standard_diameter(self):
    candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
    config = InterfaceConfig(
        mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
        seed=42, pocket_diameter=1.0, pocket_shape="sphere"
    )
    result = assemble_pocket(candidate, config)
    # If we got here, all 3 assertion blocks passed
    assert len(result.atom_names) == len(result.positions)
    assert result.water_atom_count % 4 == 0
```

**Async Testing:**
- Not used (no asyncio in codebase)
- Background threads via QThread in GUI workers, but tests don't test async behavior directly

**Error Testing:**
```python
# Testing ValueError with range hints
def test_invalid_threshold_raises_value_error(self):
    with pytest.raises(ValueError, match="outside reasonable range"):
        detect_overlaps(ice_o, water_o, box, threshold_nm=5.0)  # 5.0 nm is out of range

# Testing graceful error handling (try/except in test)
def test_small_pocket_may_raise(self):
    try:
        result = assemble_pocket(candidate, config)
        assert result.water_atom_count % 4 == 0
    except Exception as e:
        assert "zero" in str(e).lower() or "Water filling" in str(e)
```
File: `tests/test_pocket_invariants.py`

**File content verification pattern:**
```python
def test_gro_file_has_ice_and_water_atoms(self, simple_interface, mock_save_dialog):
    save_path, dialog_p, mb_p = mock_save_dialog("interface_slab.gro")
    exporter = InterfaceGROMACSExporter(parent_widget=None)
    with dialog_p, mb_p:
        result = exporter.export_interface_gromacs(simple_interface)
    assert result is True
    gro_path = Path(save_path)
    lines = gro_path.read_text().splitlines()
    atom_count = int(lines[1].strip())  # Line 2 of .gro has count
    assert atom_count == 16
```
File: `tests/test_output/test_gromacs_export_interface.py`

**ITP file content verification pattern:**
```python
ch4_itp = (tmp_path / "ch4_hydrate.itp").read_text()
assert "[ moleculetype ]" in ch4_itp
```
File: `tests/test_output/test_gromacs_export_interface.py`

**Parametrized shape testing:**
```python
@pytest.mark.parametrize("shape", ["sphere", "cubic"])
def test_pocket_edge_case(self, shape):
    """Run test for both pocket shapes."""
```
File: `tests/test_pocket_edge_cases.py`

**Adding new E2E export tests:**
1. Add structure fixture to `tests/test_output/conftest.py`
2. Create `test_gromacs_export_{type}.py` in `tests/test_output/`
3. Use `mock_save_dialog` and `mock_cancel_dialog` from conftest
4. Assert file existence and content after export

**Adding new pocket/slab tests:**
1. Use `create_mock_ice_candidate()` or `create_mock_hydrate_candidate()` for test data
2. Call `assemble_pocket()` or `assemble_slab()` with `InterfaceConfig`
3. Assert structural invariants: `result.water_atom_count % 4 == 0`, `len(result.atom_names) == len(result.positions)`

---

*Testing analysis: 2026-05-22*
