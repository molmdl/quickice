# Phase 28: Pre-requisite Fixes - Research

**Researched:** 2026-04-14
**Domain:** Internal bug fixes in existing QuickIce codebase
**Confidence:** HIGH (direct codebase analysis, confirmed line numbers)

## Summary

This phase requires fixing 4 pre-existing bugs that block v4.0 development:
1. **Pitfall #7:** GenIce2 numpy random state not restored on exception
2. **Pitfall #15:** Temperature/Pressure metadata missing from Candidate
3. **Pitfall #16:** GRO parser duplication between generator.py and water_filler.py
4. **Pitfall #21:** Dual is_cell_orthogonal() implementations with incompatible tolerances

**Primary recommendation:** Fix all 4 in parallel where possible. None have cross-dependencies. The fixes are localized and low-risk because:
- No API contract changes
- No output format modifications
- Existing functions must continue working exactly as before (per CONTEXT.md)

## Standard Stack

| Component | Current | Fix Required |
|------------|---------|---------------|
| numpy | Any | Already installed (np.random.get_state/set_state) |
| Existing modules | generator.py, water_filler.py, interface_builder.py | No new dependencies |

**No new packages needed.** All fixes use existing numpy and the existing module structure.

## Individual Fix Specifications

### Fix 1: Pitfall #7 - GenIce2 Random State Restoration

**Exact file:** `quickice/structure_generation/generator.py`
**Line numbers:** Lines 93-147 (entire `_generate_single` method)

**Current code structure (lines 93-147):**
```python
def _generate_single(self, seed: int) -> Candidate:
    try:
        # Line 96: Save global random state
        original_state = np.random.get_state()
        np.random.seed(seed)
        
        # ... generation code ...
        
        # Line 122: Restore state (OUTSIDE try/except, called only on success)
        np.random.set_state(original_state)
        
        # ... parse and create candidate ...
        
        return candidate
        
    except Exception as e:
        # Line 143-147: Exception handler
        raise StructureGenerationError(...) from e
```

**Problem:** Line 122 executes BEFORE parsing and BEFORE `return`, but if ANY exception occurs during generation (lines 100-119), code jumps to the except block (line 143) and line 122 is SKIPPED — the random state is never restored.

**Fix required:**
```python
def _generate_single(self, seed: int) -> Candidate:
    original_state = np.random.get_state()  # Move OUTSIDE try block
    try:
        np.random.seed(seed)
        # ... rest of generation ...
        candidate = Candidate(...)
        return candidate
    except Exception as e:
        raise StructureGenerationError(...) from e
    finally:
        # ALWAYS restore, regardless of exception or success
        np.random.set_state(original_state)
```

**File location change:** Delete line 96 from inside `try`, delete line 122, add `original_state` at method start, add `finally` block with restoration.

**Test strategy:**
1. Unit test: Mock GenIce to raise exception, verify `set_state` is still called
2. Integration test: Generate with invalid params (should fail), then generate valid structure, compare against fresh-session generation (should match)

**Risk:** LOW — no API changes, only internal flow restructuring.

---

### Fix 2: Pitfall #15 - Temperature/Pressure in Metadata

**Exact file:** `quickice/structure_generation/generator.py`
**Line numbers:** Lines 135-139 (Candidate construction)

**Current code:**
```python
metadata={
    "density": self.density,
    "phase_name": self.phase_name,
},
```

**Missing:** `"temperature"` and `"pressure"` keys

**Context:** Check what parameters are available at this point:
- `self.density` is in the generator (from phase_info)
- `self.phase_id` is known
- Temperature and pressure should come from `phase_info` passed to `__init__`

**Investigation needed:** Does `phase_info` dict from lookup contain temperature/pressure? Check how `IceStructureGenerator` is instantiated.

**Fix required:** Assuming phase_info contains temperature/pressure:
```python
metadata={
    "density": self.density,
    "phase_name": self.phase_name,
    "temperature": self.temperature,      # ADD
    "pressure": self.pressure,              # ADD
},
```

Need to verify: Does `IceStructureGenerator.__init__` receive temperature/pressure? If not, this fix requires adding them as constructor parameters (no API change to callers, just additional data flow).

**Test strategy:**
1. Generate a candidate with known T/P
2. Check `candidate.metadata` for "temperature" and "pressure" keys
3. Verify values match expected (from lookup table)

**Risk:** LOW — metadata is additive, no existing code depends on missing keys.

---

### Fix 3: Pitfall #16 - GRO Parser Deduplication

**Exact locations:**
1. `quickice/structure_generation/generator.py`, line 149-219 (method `_parse_gro`)
2. `quickice/structure_generation/water_filler.py`, lines 267-295 (inline in `load_water_template`)

**Current state:** Two implementations with identical logic:
- `generator.py:_parse_gro(gro_string)` — parses from string
- `water_filler.py:load_water_template()` — has inline GRO parsing (lines 268-295)

**Fix required:**
1. Create new file: `quickice/structure_generation/gro_parser.py`
2. Extract common parsing logic to function:
   ```python
   def parse_gro_string(gro_string: str) -> tuple[np.ndarray, list[str], np.ndarray]:
       """Parse GRO format string.
       
       Args:
           gro_string: GRO format string
           
       Returns:
           (positions, atom_names, cell) - same as current _parse_gro output
       """
       # Copy logic from generator.py _parse_gro
   ```
3. Create wrapper for file loading:
   ```python
   def parse_gro_file(filepath: Path) -> tuple[np.ndarray, list[str], np.ndarray]:
       """Load and parse GRO file."""
       with open(filepath, 'r') as f:
           return parse_gro_string(f.read())
   ```
4. Update `generator.py:_parse_gro` to delegate:
   ```python
   def _parse_gro(self, gro_string: str) -> tuple[...]:# Just call the shared function
       return parse_gro_string(gro_string)  # ADD this, remove body
   ```
5. Update `water_filler.py:load_water_template()` to delegate

**Important:** The existing `_parse_gro` method signature returns a 3-tuple. The new module should provide the same interface for backward compatibility.

**Test strategy:**
1. Refactor test: Parse same GRO string via both old method and new shared function, verify output matches
2. Test the new `parse_gro_file()` function with bundled tip4p.gro
3. Verify `load_water_template()` still works after refactor

**Risk:** MEDIUM — requires creating new module and modifying two existing call sites. Must maintain exact output format.

---

### Fix 4: Pitfall #21 - Unified is_cell_orthogonal()

**Exact locations:**
1. `quickice/structure_generation/water_filler.py`, lines 51-78 (angle_tol=0.1°)
2. `quickice/structure_generation/interface_builder.py`, lines 25-40 (tol=1e-10)

**Current behavior difference:**
| Module | Tolerance Type | Value | Works for |
|---------|----------------|-------|-----------|
| water_filler.py | Angle tolerance | 0.1° (~1.7e-3 rad) | Near-orthogonal cells |
| interface_builder.py | Off-diagonal element | 1e-10 | Exactly numeric zero check |

**Problem:** A cell that is "just barely" orthogonal might pass one check but fail the other, causing inconsistent behavior between water_filler and interface_builder code paths.

**Fix required:**
1. Choose a unified strategy. Recommendation: Use the interface_builder approach (off-diagonal tolerance) as primary because:
   - It's numerically more stable
   - Cell vectors are the fundamental representation
   - The water_filler angle computation has edge cases with zero-length vectors
   
2. Consolidate into one location:
   - Option A: Create `quickice/structure_generation/cell_utils.py` with unified function
   - Option B: Put in existing `mapper.py` (if cell-related utilities exist there)
   
3. Update call sites to use single function:
   - Find all callers of both functions
   - Replace with single import

**Proposed unified implementation:**
```python
def is_cell_orthogonal(cell: np.ndarray, tol: float = 1e-10) -> bool:
    """Check if cell matrix represents an orthogonal (rectangular) box.
    
    Uses off-diagonal element tolerance for stability.
    
    Args:
        cell: (3, 3) cell matrix where each row is a lattice vector
        tol: Tolerance for off-diagonal elements (default 1e-10)
    
    Returns:
        True if orthogonal, False if triclinic
    """
    off_diagonal = cell.copy()
    np.fill_diagonal(off_diagonal, 0)
    return np.allclose(off_diagonal, 0, atol=tol)
```

**Test strategy:**
1. Test with known orthogonal cell: should return True
2. Test with known triclinic cell: should return False
3. Test with near-orthogonal cell (off-diags ~1e-11): depends on tol
4. Regression test: Verify all existing callers still work with results

**Risk:** MEDIUM — changes behavior at tolerance boundary. Must verify existing code that depends on specific behavior still works.

---

## Dependencies Between Fixes

| Fix | Depends On | Can Be Done |
|-----|-----------|-------------|
| #7 Random state | None | In parallel |
| #15 T/P metadata | None | In parallel |
| #16 GRO parser | None | In parallel |
| #21 is_cell_orthogonal | None | In parallel |

**All 4 fixes are independent** — they touch different files, different functions. Can be done in any order or simultaneously.

---

## Risk Assessment Summary

| Fix | Risk Level | Reason |
|-----|------------|-------|
| #7 Random state | LOW | Internal flow change, always restores |
| #15 T/P metadata | LOW | Additive metadata, no dependencies |
| #16 GRO parser | MEDIUM | New module creation, must preserve output |
| #21 is_cell_orthogonal | MEDIUM | Changes tolerance semantics |

---

## Test Strategies Summary

### Fix #1: Random State
- Mock exception during generation, verify set_state called in finally
- Integration: generate(fail) → generate(success), compare to fresh-session

### Fix #2: T/P Metadata  
- Generate candidate, inspect metadata dict for keys
- Verify temperature/pressure values are numeric

### Fix #3: GRO Parser
- Run existing tests (if any) after refactor
- Verify output equivalence between old and new

### Fix #4: is_cell_orthogonal
- Test with orthogonal cell = True
- Test with triclinic cell = False
- Verify all call sites work post-change

---

## Open Questions

1. **Fix #15:** Does `phase_info` dict contain temperature/pressure, or do they need to be added as constructor parameters?
   - Current code: `IceStructureGenerator.__init__(phase_info, nmolecules)`
   - Need to check how `phase_info` is populated from lookup
   
2. **Fix #16:** Should the new `gro_parser.py` module also handle parsing user-provided .gro files (for custom molecules in v4.0)?
   - PITFALLS.md mentions custom molecule parsing as motivation
   - May want to include file-loading function now

---

## Sources

### Primary (HIGH confidence)
- `quickice/structure_generation/generator.py` lines 93-147 (_generate_single method)
- `quickice/structure_generation/generator.py` lines 149-219 (_parse_gro method)
- `quickice/structure_generation/water_filler.py` lines 51-78 (is_cell_orthogonal)
- `quickice/structure_generation/interface_builder.py` lines 25-40 (is_cell_orthogonal)
- `quickice/structure_generation/water_filler.py` lines 267-295 (inline GRO parsing)

### Secondary (MEDIUM confidence)
- `.planning/research/PITFALLS.md` - pitfall descriptions and rationale

---

## Metadata

**Confidence breakdown:**
- File locations: HIGH - verified by grep and reading source
- Line numbers: HIGH - verified by reading source files  
- Fix implementation: HIGH - code changes are straightforward
- Test strategy: MEDIUM - suggested approaches, not yet implemented

**Research date:** 2026-04-14
**Valid until:** 30 days (bug fixes, unlikely to change)