# Phase Diagram Polygon Issues

> Status: **Open** - Requires thermodynamic boundary verification

## Summary

Phase diagram polygons have gaps between some boundaries and overlaps in others. The polygon definitions need verification against thermodynamic phase boundaries.

---

## Issue 1: Polygon Gaps

### a. Ih-XI Gap
- **Location**: Between Ice Ih and Ice XI
- **Problem**: Triangular gap with correct connection at higher pressure, but Ih shrinked at low pressure
- **Expected**: Polygons should meet at T≈72K

### b. IX-II Gap  
- **Location**: Between Ice IX and Ice II boundaries
- **Problem**: No continuous boundary between these phases
- **Expected**: II likely needs to expand towards IX boundary

### c. IX-VI Gap
- **Location**: Between Ice IX (T=100-140K, P=200-400 MPa) and Ice VI
- **Problem**: Gap exists in the P=400-620 MPa region
- **Expected**: Proper boundary connection or identification of missing phase

### d. IX-Ih Gap
- **Location**: Between Ice IX and Ih
- **Problem**: Irregular IX shape result in the gap
- **Expected**: Proper boundary connection or identification of missing phase.

---

## Issue 2: Polygon Overlaps

### a. XV Overlaps VI
- **Location**: Ice XV extends beyond its thermodynamic region
- **Problem**: XV polygon overlaps with Ice VI region
- **Fix needed**: Restrict XV to stop at the boundary of VI

---

## Issue 3: Size Issues

### XV Too Small
- **Problem**: Ice XV exists in a narrow region
- **Note**: Verify the temperature and pressure range of this phase
- **Action**: Verify against literature; may need to expand in both temperature an pressure

### IX Too Small
- **Problem**: Ice XV does not extend to lower temperature
- **Note**: Verify the temperature and pressure range of this phase
- **Action**: Verify against literature; may need to expand in both temperature an pressure 

---

## Root Cause

Polygon vertices are defined with fixed boundaries that don't properly meet at triple points:
1. Boundary functions from `solid_boundaries.py` have discontinuities
2. Fixed vertex definitions override actual boundary intersections
3. No dynamic checking that polygons are gapless and non-overlapping

---

## Files to Review

| File | Purpose |
|------|---------|
| `quickice/output/phase_diagram.py` | Polygon vertex definitions |
| `quickice/phase_mapping/solid_boundaries.py` | Boundary curve functions |
| `quickice/phase_mapping/__init__.py` | Triple point definitions |

---

## Debug History

| Session | Date | Issue | Resolution |
|---------|------|-------|------------|
| polygon-gaps-in-diagram | 2026-03-27 | Gaps: Ih-XI, II-IX, XV isolated, VIII-X | Extended polygons - created overlaps |
| fix-polygon-overlaps | 2026-03-27 | Overlaps: XV, IX/II, Ih covers XI | Corrected boundaries - created new gaps |

---

## Suggested Approach

1. **Use boundary functions dynamically** - Instead of fixed vertices, compute boundaries at render time using curve functions
2. **Add validation** - Check for gaps/overlaps before rendering
3. **Consult phase diagram literature** - Verify actual boundary connections
4. **Inspect if this is a problem in diagram only of affecting the phase lookup** - verify if this is just the problem in drawing diagram or affects the phase identification

---

*Last updated: 2026-03-28*
