---
phase: 03-structure-generation
plan: 01
type: tdd
completed: 2026-03-26
autonomous: true
subsystem: structure_generation
affects: []
provides:
  - Phase ID to GenIce lattice mapping
  - Supercell calculation for molecule count requirements
  - Candidate and GenerationResult dataclasses
  - UnsupportedPhaseError exception
---

# 03-01: Phase ID to GenIce Lattice Mapping with Supercell Calculation

**Status:** ✓ Complete

## Deliverables

### Files Created

| File | Purpose | Lines |
|------|---------|-------|
| quickice/structure_generation/types.py | Candidate and GenerationResult dataclasses | 52 |
| quickice/structure_generation/mapper.py | Phase ID mapping and supercell calculation | 84 |
| quickice/structure_generation/errors.py | Custom exceptions for structure generation | 15 |
| quickice/structure_generation/__init__.py | Module exports | ~30 |
| tests/test_structure_generation.py | TDD test suite | ~300 |

### Test Results

```
34 tests passed ✓
- 8 phase ID to lattice name mappings
- 8 unit cell molecule count tests
- 7 supercell calculation edge cases
- 4 dataclass tests
- 2 error handling tests
- 5 dictionary validation tests
```

## What Was Built

### Phase Mapping

**PHASE_TO_GENICE dictionary** maps all 8 supported ice phases to GenIce lattice names:
- ice_ih → ice1h (hexagonal ice)
- ice_ic → ice1c (cubic ice)
- ice_ii → ice2
- ice_iii → ice3
- ice_v → ice5
- ice_vi → ice6 (double network)
- ice_vii → ice7 (double network)
- ice_viii → ice8 (double network)

**UNIT_CELL_MOLECULES dictionary** stores molecules per unit cell for each GenIce lattice (4 to 28 molecules).

### Supercell Calculation

**calculate_supercell(target_molecules, molecules_per_unit_cell)**:
- Finds smallest n where unit_cell × n³ ≥ target
- Returns (supercell_matrix, actual_molecules)
- Ensures minimum of 1×1×1 supercell
- Correctly handles rounding up for any target count

### Data Structures

**Candidate dataclass**:
- positions: np.ndarray (N_atoms, 3) in nm
- atom_names: list[str] (O, H, H pattern)
- cell: np.ndarray (3, 3) cell vectors
- nmolecules: int
- phase_id: str
- seed: int
- metadata: dict (density, T, P from Phase 2)

**GenerationResult dataclass**:
- candidates: list[Candidate]
- requested_nmolecules: int
- actual_nmolecules: int
- phase_id: str
- phase_name: str
- density: float
- was_rounded: bool

### Error Handling

**UnsupportedPhaseError**:
- Inherits from StructureGenerationError
- Stores phase_id attribute for debugging
- Clear error messages for unsupported phases

## Key Implementation Details

1. **Supercell calculation uses math.ceil** to ensure always ≥ target molecules
2. **Phase mapping validates input** and raises specific error for unsupported phases
3. **Dataclasses use field(default_factory=dict)** for mutable metadata field
4. **All 8 phases mapped** with correct GenIce naming conventions
5. **Unit cell molecule counts** documented for double-network ices (VI, VII, VIII)

## Deviations

None. Implementation matches plan exactly.

## Verification

- [x] All 8 phase ID to lattice name mappings work
- [x] Supercell calculation rounds up correctly
- [x] Actual molecule count returned when rounding occurs
- [x] Unsupported phase raises UnsupportedPhaseError
- [x] All 34 tests pass

## Commits

1. `test(03-01): add failing tests for phase mapping` - RED phase
2. `feat(03-01): implement phase mapping logic` - GREEN phase
3. `refactor(03-01): move math import to module level` - REFACTOR phase

## Next Steps

Plan 03-02 will use:
- `get_genice_lattice_name()` to get GenIce lattice names
- `calculate_supercell()` to determine supercell size
- `Candidate` and `GenerationResult` dataclasses for results
- `UnsupportedPhaseError` for error handling

---

*Completed: 2026-03-26*
