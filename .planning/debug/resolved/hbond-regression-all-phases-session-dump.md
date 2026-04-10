# Session Dump: H-Bond Debug Session
**Dumped:** 2026-04-10
**Status:** IN PROGRESS - Needs continuation

---

## User's Original Issue
After fixing PBC for triclinic cells, now **even ice Ih shows wrong h-bonds**.
User sees: **O-O bonds and H-H bonds** (incorrect - should only be H...O bonds)

User's key insight:
> "hbond should be simple O-H distance and angle determination exclude same mol, right?"

## Investigation So Far

### Evidence Gathered
1. **PBC tests pass** - All 6 tests in test_pbc_hbonds.py pass
2. **Old vs new PBC distance identical for Ih** - Mathematically equivalent for orthorhombic cells
3. **Code analysis**: `detect_hydrogen_bonds()` in `vtk_utils.py` appears correct:
   - Collects O atoms at indices 0, 3, 6, ... (mol_idx * 3)
   - Collects H atoms at indices 1, 2, 4, 5, 7, 8, ... (mol_idx * 3 + 1, +2)
   - Skips parent O (same molecule)
   - Uses PBC distance
   - Returns list of (H_position, O_position) tuples

### Code Files Involved
- `quickice/gui/vtk_utils.py`:
  - Line 127-165: `_pbc_distance()` - Uses fractional coordinates for triclinic
  - Line 168-257: `detect_hydrogen_bonds()` - Main detection logic
  - Line 260-316: `create_hbond_actor()` - Visualization
- `quickice/gui/molecular_viewer.py`:
  - Line 380-403: `set_hydrogen_bonds_visible()` - Calls detection and creates actor

### What User Reported
User specifically says they see:
- **O-O bonds** (WRONG - O cannot h-bond to O directly)
- **H-H bonds** (WRONG - H cannot h-bond to H)
- User suspects: "3-point/4-point consideration or some mismatch"

### Key Hypothesis to Test
The h-bond detection code returns `(H_position, O_position)` tuples, which are then drawn as lines by `create_hbond_actor()`. 

**POSSIBLE BUG**: The lines might be drawn incorrectly, or there's confusion about which atoms the endpoints represent.

User's h-bond definition is correct:
1. Distance: O(donor)...H-acceptor distance check
2. Angle: O-H...O angle check
3. **EXCLUDE same molecule**

### What Needs To Be Done
1. **Verify actual visualization**: What atoms are the line endpoints connected to?
   - Add debug logging to print atom indices for each h-bond line
   - Verify lines go from H atom to O atom of DIFFERENT molecule
   
2. **Check for atom type confusion**: 
   - Are O and H atoms being distinguished correctly in visualization?
   - Is there an indexing mismatch between detection and rendering?

3. **Check molecular viewer code**:
   - How does `_extract_bonds()` work? (Line 220 in molecular_viewer.py)
   - Could there be confusion between covalent bonds and h-bonds?

---

## Remaining Issues After This One

### Issue 2: Missing doc on unsupported phase in interface
- Status: NOT STARTED
- Description: Documentation missing for unsupported phases in interface

### Issue 4: PBC overlap in interface slab mode for non-hexagonal ice phases
- Status: NOT STARTED
- Description: Periodic boundary overlap for non-hexagonal ice phases in slab mode

---

## Completed Issues

### Issue 1: Interface GRO export error ✅
- **Commit:** 721d9b2
- **Root cause:** `write_gro_file()` assumed 4 atoms/mol but ice Candidates have 3 atoms/mol
- **Fix:** Changed indexing to use `mol_idx * 3`, compute MW at export time

### Issue 3 (original): Wrong hbond for non-Ih phases ✅ (but regression now)
- **Commit:** dee7802
- **Root cause:** PBC distance assumed orthorhombic cells
- **Fix:** Updated `_pbc_distance()` to use fractional coordinates
- **REGRESSION:** Now even Ih shows wrong h-bonds

---

## Instructions for Next Session

1. Run `/gsd-debug` to resume
2. Select the `hbond-regression-all-phases` session
3. Focus on: **Why are O-O and H-H bonds showing?**
4. The detection code looks correct, so the bug is likely in:
   - Visualization layer (`create_hbond_actor`)
   - Or atom indexing confusion somewhere
   - Or the user is misinterpreting what they see (verify with screenshots/debug output)
