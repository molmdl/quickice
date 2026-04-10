# QuickIce - Open Issues

**Last Updated:** 2026-04-10

---

## Active Issues

### Issue 3: Wrong Hydrogen Bonds in Tab 1 (REGRESSION)

**Status:** In Progress  
**Priority:** High  
**Debug Session:** `.planning/debug/hbond-regression-all-phases.md`

**Description:**
After fixing PBC distance calculation for triclinic cells (commit dee7802), hydrogen bond display now shows incorrect bonds even for ice Ih (which used to work correctly).

**Symptoms:**
- O-O bonds displayed (incorrect - O cannot H-bond to O directly)
- H-H bonds displayed (incorrect - H cannot H-bond to H)
- Affects all ice phases, including orthorhombic ice Ih

**Expected Behavior:**
H-bonds should only be displayed between:
- H atom (donor) of one molecule
- O atom (acceptor) of a **different** molecule
- Based on distance (< 2.5 Å) and O-H...O angle criteria

**User's Key Insight:**
> "hbond should be simple O-H distance and angle determination exclude same mol, right?"

**Investigation Notes:**
- `detect_hydrogen_bonds()` in `vtk_utils.py` appears logically correct
- Returns `(H_position, O_position)` tuples
- PBC distance calculation works (tests pass)
- Bug likely in visualization layer or atom indexing

**Files Involved:**
- `quickice/gui/vtk_utils.py` - Lines 168-257 (detection), 260-316 (visualization)
- `quickice/gui/molecular_viewer.py` - Lines 380-403 (display control)

---

### Issue 2: Missing Documentation on Unsupported Phase in Interface

**Status:** Pending  
**Priority:** Medium  

**Description:**
Documentation is missing for which ice phases are not supported in interface construction mode.

**Expected Behavior:**
Users should see clear documentation or error messages when attempting to create an interface with unsupported ice phases.

**Action Needed:**
- Identify which phases are unsupported for interface mode
- Add documentation in UI (tooltips, help text)
- Add validation with clear error messages

---

### Issue 4: PBC Overlap in Interface Slab Mode (Non-Hexagonal Phases)

**Status:** Pending  
**Priority:** High  

**Description:**
Periodic boundary condition overlap occurs in interface slab mode for some non-hexagonal ice phases (e.g., ice II, III, V, VI, VII).

**Symptoms:**
- Visual artifacts showing atoms overlapping across PBC boundaries
- Affects non-hexagonal (triclinic) ice phases in slab mode
- Hexagonal ice Ih works correctly

**Expected Behavior:**
Atoms should be properly wrapped within the simulation box, no visual overlap across boundaries.

**Likely Cause:**
The slab mode code may assume orthorhombic cells when placing/trimming ice layers, similar to the previous H-bond PBC issue.

**Files to Investigate:**
- `quickice/interface_generation/slab.py`
- Related PBC handling in interface construction

---

## Recently Resolved

### Issue 1: Interface GRO Export Error ✅
- **Commit:** 721d9b2
- **Root Cause:** `write_gro_file()` assumed 4 atoms/mol but ice Candidates have 3 atoms/mol
- **Fix:** Corrected indexing to use `mol_idx * 3`, compute MW at export time

### Issue 3 (Original): Wrong H-bonds for Non-Ih Phases ✅ (partial)
- **Commit:** dee7802
- **Root Cause:** PBC distance assumed orthorhombic cells
- **Fix:** Updated `_pbc_distance()` to use fractional coordinates for triclinic cells
- **Note:** This fix introduced the current regression for Issue 3

---

## Summary

| Issue | Description | Status | Priority |
|-------|-------------|--------|----------|
| 1 | Interface GRO export error | ✅ Fixed | - |
| 2 | Missing doc on unsupported phases | ⏳ Pending | Medium |
| 3 | Wrong H-bonds (regression) | 🔄 In Progress | High |
| 4 | PBC overlap in slab mode | ⏳ Pending | High |
