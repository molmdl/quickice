---
phase: pocket-edge-tests
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/structure_generation/modes/pocket.py
  - tests/test_pocket_invariants.py
autonomous: true

must_haves:
  truths:
    - "Pocket mode asserts water atom count is divisible by 4 after each overlap removal phase"
    - "Pocket mode asserts atom_names length equals positions length after each overlap removal phase"
    - "All assertions hold for sphere, cubic, thin, and near-boundary pocket configurations"
  artifacts:
    - path: "quickice/structure_generation/modes/pocket.py"
      provides: "Three assert statements after overlap removal phases (water-outside-cavity, guest-water, ice-water)"
      contains: "assert len"
    - path: "tests/test_pocket_invariants.py"
      provides: "Integration tests verifying assertions fire correctly through assemble_pocket()"
      min_lines: 80
  key_links:
    - from: "quickice/structure_generation/modes/pocket.py"
      to: "quickice/structure_generation/overlap_resolver.py"
      via: "remove_overlapping_molecules + filter_atom_names"
      pattern: "assert len\\(.*\\) % 4 == 0"
---

<objective>
Add FRAG-02-equivalent structural assertions to pocket.py and integration tests verifying them.

Purpose: Pocket.py has 3 overlap removal phases (water-outside-cavity, guest-water, ice-water) but NO assertions checking water atom count divisibility or atom_names/positions length consistency. Slab.py got these in FRAG-02 (lines 377-380, 561-564) but pocket.py was missed. Without these assertions, a bug that corrupts the water array (e.g., partial molecule removal) would silently produce invalid output that crashes GROMACS.

Output: 3 assert statements added to pocket.py + integration test file verifying assertions hold across shape variants and size extremes.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/pocket-edge-tests/pocket-edge-tests-RESEARCH.md
@.planning/PROJECT.md
@.planning/STATE.md

@quickice/structure_generation/modes/pocket.py
@quickice/structure_generation/modes/slab.py
@quickice/structure_generation/overlap_resolver.py
@quickice/structure_generation/types.py
@quickice/structure_generation/errors.py

@tests/test_interface_modes_audit.py
@tests/test_overlap_removal_invariants.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add water-count-divisible-by-4 and length-match assertions to pocket.py</name>
  <files>quickice/structure_generation/modes/pocket.py</files>
  <action>
Add assertion statements to pocket.py after each of the 3 overlap removal phases, matching the FRAG-02 pattern in slab.py (lines 377-380, 561-564).

**Phase 1 — After water-outside-cavity removal (after line 330):**
Insert immediately after the `filter_atom_names` call inside the `if water_outside:` block (line 326-330):
```python
        # Invariant: water atom count must be divisible by 4 (TIP4P has 4 atoms/molecule)
        assert len(water_positions) % 4 == 0, (
            f"Water atom count {len(water_positions)} not divisible by 4 "
            f"after water-outside-cavity removal"
        )
        assert len(water_atom_names) == len(water_positions), (
            f"Atom names length {len(water_atom_names)} != positions length {len(water_positions)} "
            f"after water-outside-cavity removal"
        )
```

**Phase 2 — After guest-water overlap removal (after line 461):**
Insert immediately after the `filter_atom_names` call inside the `if guest_overlap_indices:` block (lines 456-461):
```python
            # Invariant: water atom count must be divisible by 4 (TIP4P has 4 atoms/molecule)
            assert len(water_positions) % 4 == 0, (
                f"Water atom count {len(water_positions)} not divisible by 4 "
                f"after guest-water overlap removal"
            )
            assert len(water_atom_names) == len(water_positions), (
                f"Atom names length {len(water_atom_names)} != positions length {len(water_positions)} "
                f"after guest-water overlap removal"
            )
```

**Phase 3 — After ice-water overlap removal (after line 490):**
Insert immediately after the `filter_atom_names` call inside the `if overlapping_mol_indices:` block (lines 486-490):
```python
        # Invariant: water atom count must be divisible by 4 (TIP4P has 4 atoms/molecule)
        assert len(water_positions) % 4 == 0, (
            f"Water atom count {len(water_positions)} not divisible by 4 "
            f"after ice-water overlap removal"
        )
        assert len(water_atom_names) == len(water_positions), (
            f"Atom names length {len(water_atom_names)} != positions length {len(water_positions)} "
            f"after ice-water overlap removal"
        )
```

**CRITICAL:** Place assertions INSIDE the `if` blocks (where removal actually happened), NOT outside them. If no molecules were removed, the invariant is already guaranteed because the input was valid. This matches slab.py's pattern exactly — slab.py asserts inside `if overlapping_mol_indices:` (line 377) and inside `if guest_overlap_indices:` (line 561).

**Note on indentation:** Phase 1 is at top-level in the function (4-space indent for `if` body). Phases 2 and 3 are nested inside hydrate logic — check the exact indentation level in pocket.py. Phase 2 is inside `if is_hydrate and len(water_positions) > 0 and processed_guest_positions is not None...` → the `if guest_overlap_indices:` body is at 12-space indent. Phase 3 `if overlapping_mol_indices:` body is at 4-space indent.
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -c "from quickice.structure_generation.modes.pocket import assemble_pocket; print('Import OK')" && grep -c "assert len" quickice/structure_generation/modes/pocket.py</verify>
  <done>Three assert blocks added to pocket.py, each with water-count-divisible-by-4 and length-match assertions, matching slab.py FRAG-02 pattern</done>
</task>

<task type="auto">
  <name>Task 2: Create integration tests verifying pocket assertions hold across shape variants</name>
  <files>tests/test_pocket_invariants.py</files>
  <action>
Create `tests/test_pocket_invariants.py` that tests the assertions hold through `assemble_pocket()` for multiple configurations. Use the mock candidate factories from `test_interface_modes_audit.py` as a starting pattern but enhance them.

**Test class structure:**

```python
"""Test structural invariants for pocket mode after overlap removal.

Verifies that the FRAG-02 assertions added to pocket.py hold:
1. Water atom count divisible by 4 after each overlap removal phase
2. Atom names length matches positions length after each overlap removal phase

These tests call assemble_pocket() end-to-end with various configurations
to ensure the assertions are triggered and pass under normal operation.
"""

import numpy as np
import pytest
from quickice.structure_generation.types import Candidate, InterfaceConfig
from quickice.structure_generation.modes.pocket import assemble_pocket


def create_mock_ice_candidate(n_molecules: int = 96, cell_dim: float = 0.9) -> Candidate:
    """Create a mock Ice Ih candidate with configurable molecule count and cell dimensions.
    
    Uses simple cubic lattice with 3 atoms per molecule (O, H, H).
    Positions are all positive within [0, cell_dim) per dimension.
    """
    positions = []
    atom_names = []
    for i in range(n_molecules):
        x = (i % 4) * (cell_dim / 4)
        y = ((i // 4) % 4) * (cell_dim / 4)
        z = (i // 16) * (cell_dim / (n_molecules // 16)) if n_molecules > 16 else 0.0
        positions.extend([
            [x, y, z],
            [x + 0.1, y, z + 0.05],
            [x + 0.05, y + 0.1, z + 0.1]
        ])
        atom_names.extend(["O", "H", "H"])
    
    positions = np.array(positions)
    cell = np.array([[cell_dim, 0.0, 0.0], [0.0, cell_dim, 0.0], [0.0, 0.0, cell_dim]])
    
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=n_molecules,
        phase_id="ice_ih",
        seed=42,
        metadata={"temperature": 273.15, "pressure": 0.101325}
    )


def create_mock_hydrate_candidate(n_water: int = 32, n_guest: int = 4, cell_dim: float = 0.9) -> Candidate:
    """Create a mock hydrate candidate with TIP4P water framework + Me guests.
    
    TIP4P: 4 atoms per molecule (OW, HW1, HW2, MW).
    Guests: 1 atom each (Me = united-atom methane).
    """
    positions = []
    atom_names = []
    
    for i in range(n_water):
        x = 0.1 + (i % 4) * (cell_dim / 4)
        y = 0.1 + ((i // 4) % 4) * (cell_dim / 4)
        z = 0.1 + (i // 16) * (cell_dim / (n_water // 16)) if n_water > 16 else 0.1
        positions.extend([
            [x, y, z],
            [x + 0.07, y, z + 0.05],
            [x + 0.05, y + 0.07, z + 0.03],
            [x, y + 0.15, z + 0.05]
        ])
        atom_names.extend(["OW", "HW1", "HW2", "MW"])
    
    for i in range(n_guest):
        x = 0.3 + (i * 0.2)
        y = 0.3 + (i * 0.2)
        z = 0.3 + (i * 0.2)
        positions.append([x, y, z])
        atom_names.append("Me")
    
    positions = np.array(positions)
    cell = np.array([[cell_dim, 0.0, 0.0], [0.0, cell_dim, 0.0], [0.0, 0.0, cell_dim]])
    
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=n_water,
        phase_id="ice_ih",
        seed=42,
        metadata={
            "temperature": 273.15,
            "pressure": 0.101325,
            "original_hydrate": True
        }
    )


class TestPocketInvariantSphere:
    """Verify assertions hold for sphere pocket shape."""

    def test_sphere_standard_diameter(self):
        """Sphere pocket with standard 1.0nm diameter — assertions must hold."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape="sphere"
        )
        result = assemble_pocket(candidate, config)
        # If we got here, all 3 assertion blocks passed
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0

    def test_sphere_large_diameter(self):
        """Sphere pocket with 2.0nm diameter — more ice removed, assertions still hold."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=2.0, pocket_shape="sphere"
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0

    def test_sphere_hydrate_candidate(self):
        """Sphere pocket with hydrate candidate — guest-water overlap assertions hold."""
        candidate = create_mock_hydrate_candidate(n_water=32, n_guest=4, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape="sphere"
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0


class TestPocketInvariantCubic:
    """Verify assertions hold for cubic pocket shape."""

    def test_cubic_standard_diameter(self):
        """Cubic pocket with 1.0nm diameter — assertions must hold."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape="cubic"
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0

    def test_cubic_large_diameter(self):
        """Cubic pocket with 2.0nm diameter — more overlap boundary, assertions still hold."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=2.0, pocket_shape="cubic"
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0

    def test_cubic_hydrate_candidate(self):
        """Cubic pocket with hydrate candidate — guest-water overlap assertions hold."""
        candidate = create_mock_hydrate_candidate(n_water=32, n_guest=4, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape="cubic"
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0


class TestPocketInvariantSizeExtremes:
    """Verify assertions hold for pocket size extremes."""

    def test_near_boundary_pocket(self):
        """Pocket diameter close to box size (4.0nm in 5.0nm box) — thin ice shell, assertions hold."""
        candidate = create_mock_ice_candidate(n_molecules=128, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=5.0, box_y=5.0, box_z=5.0,
            seed=42, pocket_diameter=4.0, pocket_shape="sphere"
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0

    def test_small_pocket_sphere(self):
        """Small sphere pocket (0.5nm diameter) — few water molecules, assertions hold."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=0.5, pocket_shape="sphere"
        )
        # Note: small pockets may produce 0 water molecules after filling + filtering
        # which is valid (0 % 4 == 0), or may raise InterfaceGenerationError
        # Either outcome means assertions work correctly
        try:
            result = assemble_pocket(candidate, config)
            assert len(result.atom_names) == len(result.positions)
            assert result.water_atom_count % 4 == 0
        except Exception as e:
            # If fill_region_with_water returns 0 molecules, we get an error — that's OK
            assert "zero" in str(e).lower() or "Water filling" in str(e)

    def test_small_pocket_cubic(self):
        """Small cubic pocket (0.5nm diameter) — assertions hold."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=0.5, pocket_shape="cubic"
        )
        try:
            result = assemble_pocket(candidate, config)
            assert len(result.atom_names) == len(result.positions)
            assert result.water_atom_count % 4 == 0
        except Exception as e:
            assert "zero" in str(e).lower() or "Water filling" in str(e)


class TestPocketInvariantRectangularBox:
    """Verify assertions hold for non-cubic boxes."""

    def test_rectangular_box_sphere(self):
        """Rectangular box (5x3x3) with sphere pocket — assertions hold."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=5.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape="sphere"
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0

    def test_rectangular_box_cubic(self):
        """Rectangular box (5x3x3) with cubic pocket — assertions hold."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=5.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape="cubic"
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0
```

**Key design decisions:**
- Tests call `assemble_pocket()` end-to-end — if any assertion inside pocket.py fails, the test fails with the assertion error message
- Mock candidates use configurable `cell_dim` and `n_molecules` for flexibility
- Small pocket tests use try/except because `fill_region_with_water()` may return 0 molecules for very small fill regions (which raises `InterfaceGenerationError`) — this is expected and valid
- Tests are organized by variant (shape, size, box) for easy failure diagnosis
- Each test checks both `len(atom_names) == len(positions)` and `water_atom_count % 4 == 0` as post-condition verification
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -m pytest tests/test_pocket_invariants.py -v --tb=short 2>&1 | head -60</verify>
  <done>All tests in test_pocket_invariants.py pass. At least 4 test classes covering sphere, cubic, size extremes, and rectangular box. Each test calls assemble_pocket() and verifies assertions hold.</done>
</task>

</tasks>

<verification>
1. Run: `python -m pytest tests/test_pocket_invariants.py -v` — all tests pass
2. Run: `grep -c "assert len" quickice/structure_generation/modes/pocket.py` — count is >= 6 (3 phases × 2 assertions)
3. Run: `python -c "from quickice.structure_generation.modes.pocket import assemble_pocket"` — import succeeds (no syntax errors from added assertions)
4. Run existing tests to confirm no regressions: `python -m pytest tests/test_interface_modes_audit.py tests/test_overlap_removal_invariants.py -v`
</verification>

<success_criteria>
- 3 assert blocks added to pocket.py after each overlap removal phase (water-outside-cavity, guest-water, ice-water)
- Each block contains: `assert len(water_positions) % 4 == 0` and `assert len(water_atom_names) == len(water_positions)`
- test_pocket_invariants.py has >= 10 tests covering sphere, cubic, size extremes, and rectangular box configurations
- All tests pass without assertion failures
- Existing tests (test_interface_modes_audit.py, test_overlap_removal_invariants.py) still pass
</success_criteria>

<output>
After completion, create `.planning/phases/pocket-edge-tests/01-SUMMARY.md`
</output>
