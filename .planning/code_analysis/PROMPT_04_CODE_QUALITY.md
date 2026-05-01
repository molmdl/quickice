# Prompt 4: Code Quality Improvements

**Workflow:** `/gsd-plan-phase`
**Priority:** MEDIUM
**Estimated time:** 4-8 hours

---

## Instructions

Start a new session, then run:
```
/gsd-plan-phase
```

Paste this prompt when asked:

---

## Prompt

Phase: Code Quality Improvements

### Goals

Improve code quality by addressing technical debt, reducing code duplication, and enhancing error handling.

---

### Task 1: Add Logging to Empty Pass Statements

**Issue:** 20+ locations have silent exception handling with `pass`
**Impact:** Failures go unnoticed, debugging is difficult

**Files to update:**
- `quickice/phase_mapping/lookup.py:294,418`
- `quickice/structure_generation/hydrate_generator.py:268`
- `quickice/output/phase_diagram.py:231`
- `quickice/output/gromacs_writer.py:229,261`
- `quickice/gui/phase_diagram_widget.py:79,481,495,565`
- `quickice/gui/export.py:122,603`

**Approach:**
```python
import logging
logger = logging.getLogger(__name__)

# Replace:
except Exception:
    pass

# With:
except Exception as e:
    logger.warning(f"Non-critical error in {function_name}: {e}")
```

---

### Task 2: Consolidate Duplicate Molecule Index Building

**Issue:** `_build_molecule_index_from_structure` duplicated in multiple files
**Files:** `quickice/structure_generation/ion_inserter.py:60-134`

**Approach:**
1. Create `quickice/structure_generation/utils.py` if not exists
2. Move molecule index building function there
3. Update imports in ion_inserter.py and other files

---

### Task 3: Extract Duplicate Guest Atom Functions

**Issue:** `_count_guest_atoms` and `_count_guest_molecules` duplicated across 3 mode files
**Files:**
- `quickice/structure_generation/modes/piece.py`
- `quickice/structure_generation/modes/pocket.py`
- `quickice/structure_generation/modes/slab.py`

**Savings:** ~60 lines of duplicate code

**Approach:**
1. Move functions to `quickice/structure_generation/utils.py`
2. Import from utils in each mode file
3. Add unit tests for the extracted functions

---

### Task 4: Add Unit Validation at Data Entry Points

**Issue:** Unit mismatch (nm vs Å) could produce incorrect scientific results
**Current check:** `quickice/ranking/scorer.py:183-190` (density sanity check)

**Approach:**
Add validation at file parsing and user input:
```python
def validate_units_nm(value: np.ndarray, name: str) -> None:
    """Validate that coordinates are in nanometers, not Angstroms."""
    max_val = np.abs(value).max()
    if max_val > 100:  # Likely Angstroms if > 100
        raise ValueError(
            f"{name} has max value {max_val:.1f}. "
            f"QuickIce expects nanometers (nm), not Angstroms (Å). "
            f"Divide by 10 to convert Å → nm."
        )
```

---

### Task 5: Add Bounds Validation for Array Operations

**Issue:** Array indexing without bounds checks could cause IndexError

**Files:**
- `quickice/structure_generation/modes/slab.py:577-593`
- `quickice/structure_generation/modes/pocket.py:397-403`
- `quickice/structure_generation/water_filler.py:438-455`

**Approach:**
```python
# Add before array indexing:
if guest_atoms_per_mol <= 0:
    raise ValueError(f"Invalid guest_atoms_per_mol: {guest_atoms_per_mol}")

if end_idx > len(positions):
    raise IndexError(f"Index {end_idx} exceeds array length {len(positions)}")
```

---

### Task 6: Add Warning When Fallback Density Values Are Used

**Issue:** Silent fallback to default density when IAPWS calculation fails
**File:** `quickice/phase_mapping/water_density.py:67-86`

**Approach:**
```python
import logging
logger = logging.getLogger(__name__)

try:
    # ... IAPWS calculation ...
except (NotImplementedError, ValueError, OverflowError) as e:
    logger.warning(
        f"IAPWS calculation failed at T={T_K}K, P={P_MPa}MPa: {e}. "
        f"Using fallback density {FALLBACK_DENSITY_GCM3} g/cm³"
    )
    return FALLBACK_DENSITY_GCM3 * 1000
```

---

### Task 7: Fix Parameter Naming Inconsistency

**Issue:** CamelCase parameter name in Python
**File:** `quickice/structure_generation/modes/piece.py:50`

**Fix:**
```python
# Before
def _detect_guest_atoms(atom_names: list[str], atoms_perMol: int = 4):

# After
def _detect_guest_atoms(atom_names: list[str], atoms_per_mol: int = 4):
```

---

### Task 8: Add Warning for Large System GRO Format Limits

**Issue:** GRO format wraps atom numbers at 100,000 but no warning
**File:** `quickice/output/gromacs_writer.py:350-380`

**Approach:**
```python
if atom_count > 100000:
    logger.warning(
        f"GRO format limits atom/residue numbers to 5 digits. "
        f"System has {atom_count} atoms - numbers will wrap at 100,000."
    )
```

---

## References

- `.planning/code_analysis/VULNERABILITY_SCAN_2026-05-02.md` - Medium/Low severity issues
- `.planning/code_analysis/DEAD_CODE_2026-05-02.md` - Duplicate code patterns
- `.planning/codebase/CONCERNS.md` - Tech debt section

---

## Success Criteria

- [ ] All empty `pass` statements have logging
- [ ] Molecule index building consolidated in utils.py
- [ ] Guest atom counting functions extracted to utils.py
- [ ] Unit validation added at data entry points
- [ ] Bounds validation added for array operations
- [ ] Fallback density warning logged
- [ ] Parameter naming follows snake_case
- [ ] GRO format limit warning added
- [ ] All existing tests pass
- [ ] New tests added for utility functions
