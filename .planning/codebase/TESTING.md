# Testing Patterns

**Analysis Date:** 2026-05-22

## Test Framework

**Runner:**
- pytest >= 9.0.0
- Config: No `pytest.ini`, `conftest.py`, or `pyproject.toml` pytest section detected
- Implicit configuration via pytest defaults

**Assertion Library:**
- `pytest.raises()` for exception testing
- `np.testing.assert_array_equal()` and `np.testing.assert_allclose()` for numpy arrays
- Standard Python `assert` statements for all other assertions
- No custom assertion helpers or pytest plugins

**Run Commands:**
```bash
pytest                              # Run all tests
pytest tests/test_phase_mapping.py  # Run specific file
pytest tests/ -v                    # Verbose output
pytest tests/ -k "test_lookup"      # Run tests matching pattern
pytest tests/ -x                    # Stop on first failure
python -m pytest tests/test_ranking.py -v  # Alternative invocation
```

**No coverage configuration detected.** No `.coveragerc`, `pytest-cov`, or coverage targets.

## Test File Organization

**Location:**
- Separate `tests/` directory at project root (not co-located with source)
- Subdirectory `tests/test_output/` for output-related tests
- Test packages have `__init__.py` files

**Naming:**
- Files: `test_<feature>.py` (e.g., `test_phase_mapping.py`, `test_structure_generation.py`)
- Classes: `Test<Feature>` (e.g., `TestLookupPhaseIceIh`, `TestValidateTemperature`)
- Methods: `test_<behavior>` (e.g., `test_lookup_atmospheric_near_melting`, `test_rejects_negative_temperature`)

**Structure:**
```
tests/
├── __init__.py
├── test_atom_names_filtering.py       # Atom name processing
├── test_atom_ordering_validation.py    # Atom ordering checks
├── test_cli_integration.py            # CLI subprocess tests
├── test_custom_molecule.py            # Custom molecule workflow
├── test_custom_molecule_concentration.py  # Concentration calculations
├── test_custom_molecule_panel_34_6.py # GUI panel integration
├── test_custom_molecule_renderer.py    # VTK renderer tests
├── test_gromacs_molecule_ordering.py   # GROMACS export ordering
├── test_hydrate_guest_tiling.py        # Hydrate guest tiling
├── test_ice_ih_density.py             # Ice Ih density calculations
├── test_integration_v35.py            # CLI integration (v3.5 features)
├── test_interface_modes_audit.py      # Interface mode validation
├── test_interface_ordering_validation.py  # Interface atom ordering
├── test_ion_hydrate_fix.py            # Ion+hydrate bug fix
├── test_ion_source_dropdown.py       # GUI ion source dropdown
├── test_med03_minimum_box_size.py     # Minimum box size validation
├── test_moleculetype_registry.py      # GROMACS moleculetype naming
├── test_pbc_hbonds.py                # Periodic boundary H-bonds
├── test_phase_mapping.py             # Phase diagram lookup
├── test_piece_mode_validation.py     # Piece mode water layer
├── test_ranking.py                   # Scoring/ranking
├── test_solute_insertion.py          # Solute insertion workflow
├── test_solute_ion_molecule_index.py # Molecule index tracking
├── test_structure_generation.py      # Structure generation (largest)
├── test_triclinic_interface.py       # Triclinic cell support
├── test_validators.py                # Input validators
├── test_water_density.py             # Water density calculations
└── test_output/
    ├── __init__.py
    ├── test_molecule_wrapping.py     # PBC molecule wrapping
    ├── test_pdb_writer.py            # PDB file output
    └── test_validator.py            # Space group/overlap validation
```

## Test Structure

**Suite Organization:**
```python
class TestLookupPhaseIceIh:
    """Tests for Ice Ih (normal atmospheric ice) lookups."""

    def test_lookup_atmospheric_near_melting(self):
        """Temperature 273K, Pressure 0 MPa should return ice_ih."""
        result = lookup_phase(273, 0)
        assert result["phase_id"] == "ice_ih"
        assert result["phase_name"] == "Ice Ih"
```

**Patterns:**
- One test class per feature/phase/component
- Descriptive docstrings on every test method explaining expected behavior
- Test method names describe the scenario: `test_<condition>_<expected_behavior>`
- Boundary value testing (minimum, maximum, just above/below limits)
- Regression tests reference bug context: `"""This is a regression test for the bug where guest molecules were lost..."""`

**Test Class Naming Conventions:**
- Group by feature under test: `TestLookupPhaseIceIh`, `TestLookupPhaseIceVii`, `TestLookupPhaseIceVi`
- Group by validation target: `TestValidateTemperature`, `TestValidatePressure`
- Group by component: `TestSoluteInserter`, `TestSoluteInsertion`, `TestSoluteRenderer`
- Group by bug/fix: `TestPolygonOverlapFixes`, `TestHydrateGuestNaming`
- Group by integration scope: `TestIntegrationWithPhase2`, `TestCLIIntegration`

## Fixtures

**pytest Fixtures:**
```python
@pytest.fixture
def simple_candidate():
    """Create a simple candidate for testing."""
    positions = np.array([...])
    atom_names = ['O', 'H', 'H', ...]
    cell = np.eye(3) * 1.0
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=4,
        phase_id='ice_ih',
        seed=1000,
        metadata={'density': 0.9167}
    )
```

**Fixture patterns:**
- Used primarily in `test_ranking.py` and `test_structure_generation.py`
- Create mock data objects with realistic physical values
- No shared `conftest.py` - fixtures are defined per-test-file
- `@pytest.fixture(autouse=True)` used in GUI tests for QApplication setup

## Mocking

**Framework:** No mocking framework detected (no `unittest.mock`, `pytest-mock`, or `mocker` fixture)

**Patterns:**
- Tests use real GenIce2 generation (not mocked) for structure generation tests
- CLI tests use `subprocess.run()` to test actual script execution
- GUI tests create real Qt widgets with QApplication singleton
- No monkeypatching or mock objects detected in test suite

**What to Mock:**
- Not currently mocked - tests use real implementations
- VTK rendering is tested with real VTK (requires display or offscreen)

**What NOT to Mock:**
- Phase mapping calculations (use real IAPWS data)
- Structure generation (use real GenIce2)
- Scoring functions (use real numpy calculations)

## Fixtures and Factories

**Test Data:**
```python
# Mock interface structure for solute insertion tests
@pytest.fixture
def interface_structure(self):
    """Create mock interface structure for testing."""
    n_ice_molecules = 100
    ice_positions = []
    for i in range(n_ice_molecules):
        ice_positions.append([i * 0.3, 0, 0])      # O
        ice_positions.append([i * 0.3 + 0.1, 0.1, 0])  # H
        ice_positions.append([i * 0.3 + 0.1, -0.1, 0])  # H
    # ... water positions, cell, etc.
    return InterfaceStructure(positions=..., atom_names=..., cell=..., ...)
```

**Location:**
- Fixtures defined inline in test files (no shared fixture directory)
- Real test data files in `quickice/data/custom/` (e.g., `etoh.gro`, `etoh.itp`)
- Bundled ITP/GRO files used for solute template and custom molecule tests

## Coverage

**Requirements:** None enforced

**View Coverage:**
```bash
# Not configured; would require:
pytest --cov=quickice tests/
```

## Test Types

**Unit Tests:**
- Most test files are unit tests for specific functions/classes
- Phase mapping lookup: `test_phase_mapping.py` (19 test classes, 618 lines)
- Validators: `test_validators.py` (boundary value testing, 231 lines)
- Scoring functions: `test_ranking.py` (fixture-based, 691 lines)
- Data types: `test_structure_generation.py` (dataclass creation, 752 lines)

**Integration Tests:**
- CLI integration: `test_cli_integration.py` (subprocess-based, 292 lines)
- CLI interface generation: `test_integration_v35.py` (GRO file validation, 513 lines)
- Cross-module integration: `TestIntegrationWithPhase2` in `test_structure_generation.py`
- Solute insertion pipeline: `test_solute_insertion.py` (complete workflow, 269 lines)
- Custom molecule workflow: `test_custom_molecule.py` (GRO/ITP parsing + insertion, 521+ lines)

**E2E Tests:**
- Not formally separated; CLI tests (`test_cli_integration.py`, `test_integration_v35.py`) serve as E2E
- No browser or GUI E2E framework

## GUI Test Patterns

**QApplication Setup (Manual Singleton Pattern):**
```python
# Used in: tests/test_custom_molecule_panel_34_6.py, tests/test_ion_source_dropdown.py
import sys
from PySide6.QtWidgets import QApplication

class TestIonSourceDropdown:
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment with QApplication and IonPanel instance."""
        # QApplication is required for Qt widgets
        # Create QApplication if it doesn't exist (singleton pattern)
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()
        
        # Create the widget under test
        self.panel = IonPanel()
```

**Key points about GUI testing:**
- No `pytest-qt` plugin - manual QApplication management
- Singleton pattern ensures only one QApplication per test session
- `autouse=True` fixture ensures QApplication exists before each test
- Tests access widget attributes directly: `assert hasattr(self.panel, 'source_combo')`
- Tests programmatically interact with widgets: `self.panel.source_combo.setCurrentIndex(1)`
- No signal spy or wait mechanisms - synchronous assertions only

**VTK Rendering Tests:**
- `test_custom_molecule_renderer.py` tests VTK actor creation
- Requires VTK to be importable (may fail in CI without display)
- Tests create actors and check `assert actor is not None`, `assert hasattr(actor, 'GetMapper')`
- No offscreen rendering setup in test files

## CLI Integration Test Pattern

**Subprocess-based testing:**
```python
# Used in: tests/test_cli_integration.py, tests/test_integration_v35.py
QUICKICE_SCRIPT = Path(__file__).parent.parent / "quickice.py"

def run_cli(*args: str, timeout: int = 60) -> tuple[int, str, str]:
    """Run quickice.py with given arguments."""
    cmd = [sys.executable, str(QUICKICE_SCRIPT)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout, result.stderr
```

**GRO File Validation Helper:**
```python
# Used in: tests/test_integration_v35.py
def validate_gro_file(filepath: Path) -> dict:
    """Validate a GROMACS .gro file.
    
    Returns dict with keys: valid, atom_count, box_dimensions, errors, coordinates
    """
    # Parses header, atom lines, box dimensions
    # Validates coordinates within box bounds
    # Checks triclinic vs orthogonal format
```

**CLI test assertions:**
```python
def test_cli_slab_interface_ice_ih(self):
    with tempfile.TemporaryDirectory() as tmpdir:
        returncode, stdout, stderr = run_cli(
            "--interface", "--mode", "slab",
            "--temperature", "250", "--pressure", "0.1",
            "--box-x", "3.0", "--box-y", "3.0", "--box-z", "8.0",
            "--ice-thickness", "2.0", "--water-thickness", "4.0",
            "--output", tmpdir
        )
        assert returncode == 0
        assert "Interface generation complete" in stdout
        gro_files = list(Path(tmpdir).glob("*.gro"))
        assert len(gro_files) == 1
        result = validate_gro_file(gro_files[0])
        assert result['valid']
```

## Common Patterns

**Async Testing:**
- Not used - all tests are synchronous
- Worker threads are not directly tested (signal emission tested through real execution)
- No `qwait` or event loop processing in tests

**Error Testing:**
```python
# Exception type and message verification
with pytest.raises(UnsupportedPhaseError) as exc_info:
    get_genice_lattice_name("ice_xxx")
assert exc_info.value.phase_id == "ice_xxx"

# Exception message content verification
with pytest.raises(ArgumentTypeError) as exc_info:
    validate_temperature("abc")
assert "temperature" in str(exc_info.value).lower()

# UnknownPhaseError includes T,P in message
with pytest.raises(UnknownPhaseError) as exc_info:
    lookup_phase(500, 500)
assert "500" in str(exc_info.value)
```

**Numpy Array Testing:**
```python
# Exact array equality
np.testing.assert_array_equal(candidate.positions, positions)

# Array shape checking
assert isinstance(candidate.positions, np.ndarray)
assert candidate.positions.shape[1] == 3

# Physical validity checks
assert np.all(np.isfinite(candidate.positions))
assert np.all(np.abs(candidate.positions) < 10)

# Approximate comparison
assert abs(result["density"] - 0.9167) < 0.001
```

**Dataclass Creation in Tests:**
```python
# Direct construction with numpy arrays
candidate = Candidate(
    positions=np.array([[0.0, 0.0, 0.0]]),
    atom_names=["O"],
    cell=np.eye(3),
    nmolecules=1,
    phase_id="ice_ih",
    seed=0
)

# from_dict() pattern for config dataclasses
config = InterfaceConfig.from_dict(config_dict)

# MoleculeIndex for multi-molecule tracking
molecule_index = [
    MoleculeIndex(0, 4, 'water'),
    MoleculeIndex(8, 4, 'water'),
    MoleculeIndex(4, 5, 'ch4'),
]
```

**Test File Self-Execution:**
Some test files include self-execution pattern:
```python
if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
```

## Test Data Dependencies

**Required External Dependencies:**
- GenIce2 must be installed for structure generation tests
- VTK must be importable for renderer tests (skips gracefully if unavailable)
- Matplotlib required for phase diagram tests
- scipy required for PBC/cKDTree tests

**Bundled Test Data:**
- `quickice/data/custom/etoh.gro` - Ethanol GRO file for custom molecule tests
- `quickice/data/custom/etoh.itp` - Ethanol ITP file for custom molecule tests
- `quickice/data/tip4p_ice.itp` - TIP4P-ICE water model topology

---

*Testing analysis: 2026-05-22*
