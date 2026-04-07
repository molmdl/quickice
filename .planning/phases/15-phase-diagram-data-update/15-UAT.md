---
phase: 15-phase-diagram-data-update
tested: 2026-04-08T00:00:00Z
status: diagnosed
tester: user
issues:
  - component: CLI export
    issue: "Ice Ic does not appear in exported phase diagram"
    severity: medium
    impact: "CLI users cannot visualize Ice Ic phase region"
    status: "FIXED in Plan 15-06"
  - component: GUI phase diagram
    issue: "Ice Ic polygon overlaps with Ice XI"
    severity: high
    impact: "Visual confusion, incorrect phase region boundaries"
    status: "FIXED in Plan 15-05 (lower boundary now 72K)"
  - component: Ice Ic upper boundary
    issue: "Upper pressure boundary (100 MPa) is scientifically incorrect"
    severity: high
    impact: "Ice Ic region incorrectly truncated, should extend to ~200 MPa to match Ice Ih"
    status: "NEEDS FIX"
---

# Phase 15: User Acceptance Testing Report

**Phase:** 15 - Phase Diagram Data Update
**Tested:** 2026-04-08T00:00:00Z
**Tester:** User
**Status:** diagnosed

## Testing Environment

- **Application:** QuickIce GUI + CLI
- **Test Date:** 2026-04-08
- **Test Scope:** Phase diagram rendering and Ice Ic visualization

## Test Results

### CLI Export

**Test:** Generate phase diagram via CLI export
**Result:** FAIL

**Issue:** Ice Ic does not appear in the exported phase diagram

**Details:**
- When using CLI export functionality, the Ice Ic phase region is not rendered
- The polygon builder function exists and dispatch works
- But the rendering pipeline does not include Ice Ic in the output

**Impact:** CLI users cannot visualize the Ice Ic metastable phase region

---

### GUI Phase Diagram

**Test:** View phase diagram in GUI application
**Result:** PARTIAL PASS

**Issue:** Ice Ic polygon and label ARE visible in GUI, but boundaries are incorrect

**Details:**
- ✓ Ice Ic polygon renders in the GUI phase diagram
- ✓ Ice Ic label appears in correct location
- ✗ Ice Ic polygon overlaps with Ice XI phase region
- ✗ Upper pressure boundary (100 MPa) appears incorrect

**Impact:** 
- Users see overlapping phase regions
- Thermodynamic boundaries not accurately represented
- Potential confusion about which phase is present at given conditions

---

## Root Cause Analysis

### Issue 1: CLI Export Missing Ice Ic

**Likely cause:** Different rendering paths for GUI vs CLI
- GUI may use `generate_phase_diagram()` with all phases
- CLI export may use a different code path that doesn't include Ice Ic in rendering list
- Need to check CLI export code and ensure `ice_ic` is included

### Issue 2: Ice Ic Overlaps Ice XI

**Likely cause:** Incorrect boundary definition for Ice Ic
- Current definition: 50-150K, 0-100 MPa (rectangular region)
- Ice XI exists at very low temperatures (below 72K)
- Overlap occurs because Ice Ic includes 50-72K range
- Need to add Ice XI exclusion logic or adjust Ice Ic boundaries

### Issue 3: Upper Pressure Boundary Incorrect

**Likely cause:** 100 MPa upper limit is arbitrary, not scientifically validated
- Ice Ic is metastable with respect to Ice Ih
- At T=72-150K, Ice Ih exists at P≈196-210 MPa (along Ih-II boundary)
- Ice Ic could exist as metastable in the same region where Ice Ih is stable
- The 100 MPa limit incorrectly truncates the Ice Ic region

**Scientific evidence:**
- Ice Ih polygon shows upper boundary at ~196-210 MPa for T=72-150K
- Ice Ic should extend to the same pressure range (up to Ih-II boundary)
- No thermodynamic reason for 100 MPa limit

**Recommended fix:**
- Update Ice Ic polygon upper pressure boundary from 100 MPa to ~200 MPa
- Use Ih-II boundary as the upper limit (same as Ice Ih)
- This reflects that Ice Ic can exist metastably wherever Ice Ih is stable

## Recommended Fixes

### Fix 1: Add Ice Ic to CLI Export Rendering

**File:** `quickice/output/phase_diagram.py` (or CLI export module)
**Action:** Ensure `ice_ic` is in the rendering list for CLI export path

### Fix 2: Adjust Ice Ic Boundaries to Avoid Ice XI Overlap

**File:** `quickice/output/phase_diagram.py`
**Action:** Update `_build_ice_ic_polygon()` to exclude Ice XI region:
- Lower temperature boundary should start above 72K (Ice XI max temp)
- OR: Add logic to check for Ice XI first, then Ice Ic
- Current polygon: 50-150K, 0-100 MPa
- Proposed polygon: 72-150K, 0-100 MPa (after Ice XI check)

### Fix 3: Update Upper Pressure Boundary to Match Ice Ih

**File:** `quickice/output/phase_diagram.py`
**Action:**
1. Update `_build_ice_ic_polygon()` to use ~200 MPa upper pressure boundary
2. Ice Ih exists at P≈196-210 MPa for T=72-150K (along Ih-II boundary)
3. Ice Ic (metastable) should extend to same pressure range
4. Proposed polygon: 72-150K, 0.1-200 MPa (approximate, matching Ih-II boundary)

**Scientific justification:**
- Ice Ic is metastable relative to Ice Ih
- No defined thermodynamic upper pressure boundary
- Should exist wherever Ice Ih is stable (up to Ih-II transition)
- This is the scientifically correct approach

## Priority

1. **High:** Fix Ice Ic upper pressure boundary to ~200 MPa (scientific accuracy)
2. ~~High: Fix Ice Ic/Ice XI overlap~~ ✓ FIXED (Plan 15-05)
3. ~~Medium: Fix CLI export to include Ice Ic~~ ✓ FIXED (Plan 15-06)

---

_Tested: 2026-04-08T00:00:00Z_
_Tester: User_
