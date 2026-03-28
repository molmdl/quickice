# Phase Diagram Polygon Issues

> Status: **Resolved (Major)** - 2026-03-28

## Summary

Most phase diagram polygon issues have been resolved. Two minor gaps remain (see below).

---

## Resolved Issues

### Ih-XI Gap ✅
- **Status**: Fixed
- **Solution**: Ih polygon closes with vertical/horizontal path at T=72K

### IX-Ih Overlap ✅
- **Status**: Fixed
- **Solution**: IX uses 1 MPa buffer above Ih-II boundary

### XV-VI Overlap ✅
- **Status**: Fixed
- **Solution**: VI cold edge stops at P=1150, XV rendered after VI

### II-VI Overlap ✅
- **Status**: Fixed
- **Solution**: II traces just below VI boundary, capped at P=950

### X-VIII Gap ✅
- **Status**: Fixed
- **Solution**: X uses P=30000 boundary to touch VIII/VII

### XV Size ✅
- **Status**: Fixed
- **Solution**: Extended to T=50-100K, P=950-2100 MPa

---

## Remaining Minor Issues

### 1. II-IX-Ih Triangle Gap
- **Location**: Between Ice II, Ice IX, and Ice Ih
- **Problem**: Triangular gap exists
- **Fix**: Adjust either II towards IX boundary or IX towards II boundary
- **Note**: This is a legitimate phase region - may not need to fill

### 2. VI-XV-II Triangle Gap
- **Location**: Between Ice VI, Ice XV, and Ice II
- **Problem**: Tiny triangular gap exists
- **Fix**: Adjust VI to touch II upper boundary at P=950 MPa

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
| polygon-phase-diagram-issues | 2026-03-28 | All gaps/overlaps | Fixed Ih-XI, IX-Ih, XV-VI |
| phase-diagram-worse-after-fix | 2026-03-28 | Over-correction | Fixed II, VI, IX, XV |
| phase-diagram-persistent-issues | 2026-03-28 | II overfills, XV wrong | Fixed II, VI, XV, label |
| phase-diagram-II-X-fixes | 2026-03-28 | II overlap VI, X gap | Fixed both |

---

*Last updated: 2026-03-28*
