# Testing Patterns

**Analysis Date:** 2026-06-08

## Test Framework

**Runner:**
- pytest 9.0.2
- No config file detected (no `pytest.ini`, `pyproject.toml`, or `setup.cfg` with pytest section)
- Python 3.14

**Assertion Library:**
- `assert` statements (Python built-in) — primary pattern
- `np.testing.assert_array_equal` for NumPy array comparisons
- `np.testing.assert_array_almost_equal` for floating-point array comparisons
- `pytest.raises` for exception testing (~65 uses across all test files)

**Run Commands:**
```bash
pytest                              # Run all tests
pytest tests/test_validators.py     # Run single file
pytest -m slow                      # Run slow tests (high-pressure ice phases)
pytest tests/test_e2e_gmx_validation.py  # GROMACS grompp validation (requires gmx)
```

## Test File Organization

**Location:**
- Primary test directory: `tests/` at project root
- Secondary test directory: `tests/test_output/` for export-specific tests
- NOT co-located — all tests in separate `tests/` directory

**Naming:**
- Unit tests: `test_<module_name>.py` (e.g., `test_validators.py`, `test_ranking.py`, `test_phase_mapping.py`)
- E2E generation tests: `test_e2e_<feature>.py` (e.g., `test_e2e_ice_generation.py`, `test_e2e_hydrate_generation.py`)
- E2E export tests: `test_e2e_<feature>_export.py` (e.g., `test_e2e_ion_export.py`, `test_e2e_solute_export.py`)
- E2E GROMACS validation: `test_e2e_gmx_validation.py`
- E2E workflow chains: `test_e2e_workflow_chains.py`
- Test helpers: NOT `test_`-prefixed (e.g., `e2e_export_helpers.py` — line 7: "NOT test_-prefixed to avoid pytest auto-collection")
- GUI export tests: `tests/test_output/test_gromacs_export_<feature>.py`

**Structure:**
```
tests/
├── conftest.py                      # Module-scoped e2e fixtures
├── e2e_export_helpers.py             # Shared GRO/TOP parsing, chain builders
├── em.mdp                           # Energy minimization MDP for grompp
├── test_validators.py               # CLI validator unit tests
├── test_ranking.py                  # Ranking unit tests
├── test_phase_mapping.py            # Phase lookup unit tests (62 test methods)
├── test_structure_generation.py      # Structure generation unit tests (59 test methods)
├── test_e2e_ice_generation.py       # E2E ice generation
├── test_e2e_hydrate_generation.py   # E2E hydrate generation
├── test_e2e_interface_generation.py # E2E interface generation
├── test_e2e_ion_insertion.py        # E2E ion insertion
├── test_e2e_solute_insertion.py     # E2E solute insertion
├── test_e2e_custom_molecule.py      # E2E custom molecule
├── test_e2e_workflow_chains.py      # E2E full pipeline chains (F1-F7)
├── test_e2e_gmx_validation.py       # GROMACS grompp validation (10+ chains)
├── test_e2e_chain_export_1.py       # Chain export validation (part 1)
├── test_e2e_chain_export_2.py       # Chain export validation (part 2)
├── test_e2e_cross_chain_invariants.py  # Cross-chain invariant checks
├── test_e2e_ice_interface_export.py # Ice interface export validation
├── test_e2e_ion_export.py           # Ion export validation
├── test_e2e_solute_export.py        # Solute export validation
├── test_e2e_itp_baseline.py        # ITP baseline validation
├── test_output/
│   ├── conftest.py                  # Export test fixtures + mock dialogs
│   ├── test_gromacs_export_ice.py
│   ├── test_gromacs_export_interface.py
│   ├── test_gromacs_export_hydrate.py
│   ├── test_gromacs_export_ion.py
│   ├── test_gromacs_export_solute.py
│   ├── test_gromacs_export_custom.py
│   ├── test_gromacs_export_chain.py
│   ├── test_pdb_writer.py
│   ├── test_molecule_wrapping.py
│   └── test_validator.py
```

## Test Structure

**Suite Organization:**
```python
class TestValidateTemperature:
    """Tests for temperature validation."""

    def test_accepts_valid_minimum_boundary(self):
        """Temperature 0K should be accepted."""
        result = validate_temperature("0")
        assert result == 0.0
        assert isinstance(result, float)

    def test_rejects_negative_temperature(self):
        """Temperature -1K should be rejected."""
        with pytest.raises(ArgumentTypeError) as exc_info:
            validate_temperature("-1")
        assert "temperature" in str(exc_info.value).lower()
```

**Patterns:**
- **Class-per-feature**: Each test class groups related tests (e.g., `TestValidateTemperature`, `TestAllOrthogonalPhases`, `TestChainF1GmxValidation`)
- **Descriptive docstrings**: Every test method has a docstring describing the expected behavior
- **Boundary testing**: Test minimum, maximum, and just-beyond boundary values (see `test_validators.py`)
- **Error message validation**: Check that error messages contain relevant keywords (e.g., `assert "temperature" in str(exc_info.value).lower()`)
- **Parametrized tests**: `@pytest.mark.parametrize` for multi-case scenarios:
  ```python
  @pytest.mark.parametrize(
      "phase_id",
      ["ice_ih", "ice_ic", "ice_iii", "ice_vi", "ice_vii", "ice_viii"],
  )
  def test_all_orthogonal_phases_generate_successfully(self, phase_id):
  ```
  See `tests/test_e2e_ice_generation.py` lines 56-61

- **Slow test markers**: `@pytest.mark.slow` for expensive tests (high-pressure phases)
  See `tests/test_e2e_ice_generation.py` line 88

- **Skip markers**: `@pytest.mark.skip(reason="pytest-qt not installed in test environment")`
  See `tests/test_solute_insertion.py` lines 235, 249

## Fixtures

**Framework:** pytest fixtures with explicit scope

**Top-level conftest (`tests/conftest.py`):**
```python
@pytest.fixture(scope="module")
def ice_ih_candidate():
    """Generate Ice Ih candidate at 250 K, 0.1 MPa with 96 target molecules."""
    phase_info = lookup_phase(250, 0.1)
    gen = IceStructureGenerator(phase_info, 96)
    candidates = gen.generate_all(1)
    return candidates[0]

@pytest.fixture(scope="module")
def interface_slab(ice_ih_candidate):
    """Generate slab interface from Ice Ih candidate."""
    config = InterfaceConfig(mode="slab", box_x=3.0, box_y=3.0, box_z=8.0, ...)
    return generate_interface(ice_ih_candidate, config)
```

**Key fixture patterns:**
- ALL top-level conftest fixtures use `scope="module"` to amortize expensive GenIce2 calls (~3-5s each)
- Fixtures build on each other: `interface_slab` depends on `ice_ih_candidate`
- Hydrate fixtures generate both `Candidate` and `HydrateStructure` variants
- `conftest.py` explicitly states: "No qtbot or QApplication fixture — these tests are API-only, no GUI"

**Export conftest (`tests/test_output/conftest.py`):**
```python
@pytest.fixture
def simple_candidate():
    """1-molecule ice Candidate with 3 atoms (O, H, H)."""
    positions = np.array([[0.1, 0.1, 0.1], [0.15, 0.12, 0.1], [0.08, 0.12, 0.1]])
    return Candidate(positions=positions, atom_names=["O", "H", "H"], ...)

@pytest.fixture
def mock_save_dialog(tmp_path):
    """Factory fixture for export.py QFileDialog mocking."""
    def _create(filename="test.gro"):
        save_path = str(tmp_path / filename)
        dialog_patch = patch('quickice.gui.export.QFileDialog.getSaveFileName',
                            return_value=(save_path, "GRO Files (*.gro)"))
        mb_patch = patch('quickice.gui.export.QMessageBox')
        return save_path, dialog_patch, mb_patch
    return _create
```

**GROMACS workspace fixture:**
```python
@pytest.fixture
def gmx_workspace(request):
    """Persistent workspace under tmp/e2e-gmx-validation/ for GROMACS grompp."""
    base = Path(__file__).parent.parent / "tmp" / "e2e-gmx-validation"
    workspace = base / request.node.name.replace("::", "_")
    workspace.mkdir(parents=True, exist_ok=True)
    yield workspace
```
See `tests/test_e2e_gmx_validation.py` lines 55-66

**Chain-building fixtures (autouse pattern):**
```python
class TestChainF1GmxValidation:
    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        solute = _insert_solutes(custom, solute_type='CH4', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)
```
See `tests/test_e2e_gmx_validation.py` lines 240-247

## Mocking

**Framework:** `unittest.mock` (stdlib) — used minimally

**Patterns:**
- **QFileDialog mocking**: Only used in `tests/test_output/` for GUI export tests
  ```python
  dialog_patch = patch('quickice.gui.export.QFileDialog.getSaveFileName',
                       return_value=(save_path, "GRO Files (*.gro)"))
  mb_patch = patch('quickice.gui.export.QMessageBox')
  with dialog_p, mb_p:
      result = exporter.export_gromacs(ranked_candidate, T=195, P=1.36)
  ```

- **No mocking of computation modules**: All e2e tests use REAL GenIce2 generation (not mocks)
- **No mocking of numpy/scipy**: Real numerical computation in tests
- **subprocess.run for CLI integration**: Direct subprocess calls to `quickice.py`
  ```python
  result = subprocess.run(
      [sys.executable, "quickice.py", "--temperature", "273", "--pressure", "0", "--nmolecules", "100"],
      capture_output=True, text=True,
  )
  assert result.returncode == 0
  ```
  See `tests/test_phase_mapping.py` `TestCLIIntegration` class

**What to Mock:**
- QFileDialog (only in export tests)
- QMessageBox (only in export tests)
- GUI dialogs that require user interaction

**What NOT to Mock:**
- GenIce2 generation (use real generation for e2e tests)
- NumPy/SciPy computation
- Phase mapping lookup
- GROMACS file writing

## Fixtures and Factories

**Test Data:**
```python
# Inline test structures (export tests)
positions = np.array([[0.1, 0.1, 0.1], [0.15, 0.12, 0.1], [0.08, 0.12, 0.1]])
atom_names = ["O", "H", "H"]
cell = np.array([[0.9, 0.0, 0.0], [0.0, 0.78, 0.0], [0.0, 0.0, 0.72]])
candidate = Candidate(positions=positions, atom_names=atom_names, cell=cell, nmolecules=1, phase_id="ice_ih", seed=42, metadata={})
```
See `tests/test_output/conftest.py`

**Shared test data paths:**
```python
DATA_DIR = Path(__file__).resolve().parent.parent / "quickice" / "data" / "custom"
ETOH_GRO = DATA_DIR / "etoh.gro"
ETOH_ITP = DATA_DIR / "etoh.itp"
MDP_PATH = Path(__file__).resolve().parent / "em.mdp"
```
See `tests/e2e_export_helpers.py` lines 36-38, `tests/test_e2e_workflow_chains.py` lines 37-38

**Location:**
- Synthetic test data: Inline in `tests/test_output/conftest.py`
- Real molecule data: `quickice/data/custom/` (etoh.gro, etoh.itp)
- MDP file: `tests/em.mdp`
- GROMACS validation workspaces: `tmp/e2e-gmx-validation/`

## Coverage

**Requirements:** No enforced target detected

**Coverage file:** `.coverage` exists at project root (from prior runs)

**View Coverage:**
```bash
pytest --cov=quickice --cov-report=html    # Generate HTML report
pytest --cov=quickice --cov-report=term    # Terminal report
```

## Test Types

**Unit Tests:**
- Pure function testing with known inputs/outputs
- Boundary value testing (min, max, just-beyond)
- Error message content validation
- Dataclass validation (`__post_init__` checks)
- Examples: `test_validators.py` (33 tests), `test_ranking.py` (36 tests), `test_phase_mapping.py` (62 tests)

**Integration Tests:**
- Cross-module integration (e.g., `lookup_phase()` → `IceStructureGenerator` → `Candidate`)
- Full pipeline chain tests (Interface → Custom → Solute → Ion)
- CLI integration via subprocess
- Examples: `test_structure_generation.py` `TestIntegrationWithPhase2`, `test_e2e_workflow_chains.py`

**E2E Tests (Generation):**
- Real GenIce2 structure generation for all ice phases
- Structural invariant validation (positions finite, cell volume positive, atom counts match)
- Hydrate generation with different lattice types and guest molecules
- Examples: `test_e2e_ice_generation.py`, `test_e2e_hydrate_generation.py`, `test_e2e_interface_generation.py`

**E2E Tests (Export):**
- GROMACS file export validation (GRO/TOP/ITP format)
- Residue ordering verification
- GROMACS `gmx grompp` validation (most rigorous — runs actual GROMACS)
- Chain export tests (F1-F7 workflow chains with varying complexity)
- Examples: `test_e2e_gmx_validation.py`, `test_e2e_chain_export_1.py`, `test_e2e_chain_export_2.py`

**E2E Tests (GROMACS Validation):**
The most rigorous test type — validates exported files pass `gmx grompp`:
```python
exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f1.gro", top_file="f1.top")
assert exit_code == 0, f"gmx grompp failed for F1:\n{stderr[-500:]}"
```
Covered chains (in `test_e2e_gmx_validation.py`):
- Ice candidate (inline moleculetype, no ITPs)
- Interface slab (#include tip4p-ice.itp)
- F5: Interface→Ion (2 ITPs)
- F6: Interface→Solute(CH4)→Ion (3 ITPs)
- F7: Interface→Solute(THF)→Ion (3 ITPs)
- F1: Interface→Custom→Solute→Ion (4 ITPs)
- F3: Hydrate→Interface→Solute→Ion (4 ITPs)
- F4: Hydrate→Interface→Custom→Solute→Ion (5 ITPs)
- F2: Interface→Custom→Ion (3 ITPs)
- Cross-combinations with THF/CH4 variants

## Common Patterns

**Async/Threaded Testing:**
- No async test patterns — workers are tested via their API, not directly
- GUI tests are skipped when pytest-qt is unavailable (`@pytest.mark.skip(reason="pytest-qt not installed")`)

**Error Testing:**
```python
# Pattern 1: Exception type + message content
with pytest.raises(ArgumentTypeError) as exc_info:
    validate_temperature("-1")
assert "temperature" in str(exc_info.value).lower()

# Pattern 2: Custom exception attributes
with pytest.raises(UnsupportedPhaseError) as exc_info:
    get_genice_lattice_name("ice_xxx")
assert exc_info.value.phase_id == "ice_xxx"

# Pattern 3: UnknownPhaseError for out-of-range conditions
with pytest.raises(UnknownPhaseError):
    lookup_phase(260, 300)

# Pattern 4: Error message contains input values
with pytest.raises(UnknownPhaseError) as exc_info:
    lookup_phase(500, 500)
assert "500" in str(exc_info.value)
```

**Array Comparison Testing:**
```python
# Exact array comparison
np.testing.assert_array_equal(candidate.positions, positions)

# Floating-point array comparison
np.testing.assert_array_almost_equal(wrapped, positions)

# Approximate scalar comparison
assert abs(result["density"] - 0.9167) < 0.001

# Finite values check
assert np.all(np.isfinite(candidate.positions))

# Shape assertions
assert candidate.positions.ndim == 2
assert candidate.positions.shape[1] == 3
assert candidate.cell.shape == (3, 3)
```

**Structural Invariant Testing:**
```python
# Atom count = molecules × atoms_per_molecule
atoms_per_molecule = 3  # TIP3P: O, H, H
expected_atoms = candidate.nmolecules * atoms_per_molecule
assert len(candidate.positions) == expected_atoms

# Fractional coordinates within [0, 1] + tolerance
cell_inv = np.linalg.inv(cell)
frac_coords = candidate.positions @ cell_inv
tolerance = 0.01
assert np.all(frac_coords >= -tolerance)
assert np.all(frac_coords <= 1.0 + tolerance)
```

**GROMACS File Parsing in Tests:**
```python
# Parse GRO residue names
def parse_gro_residue_names(gro_path: str) -> list[str]:
    # Fixed-width column parsing per GROMACS spec
    res_name = line[5:10].strip()
    ...

# Parse TOP [ molecules ] section
def parse_top_molecules(top_path: str) -> dict[str, int]:
    ...

# Assert residue ordering
assert_gro_residue_ordering(residue_names, ["SOL", "CH4"])
```
See `tests/e2e_export_helpers.py` for all parsing helpers

## Test Statistics

- **Total test files**: 40+ Python test files
- **Total test classes**: 193
- **Total test functions**: 760
- **Largest test files** (by line count):
  - `test_structure_generation.py` (752 lines, 59 tests)
  - `test_ranking.py` (691 lines, 36 tests)
  - `test_e2e_chain_export_1.py` (662 lines, 26 tests)
  - `test_e2e_custom_molecule.py` (661 lines, 20 tests)
  - `test_custom_molecule_panel_34_6.py` (653 lines)
  - `test_phase_mapping.py` (618 lines, 62 tests)

---

*Testing analysis: 2026-06-08*
