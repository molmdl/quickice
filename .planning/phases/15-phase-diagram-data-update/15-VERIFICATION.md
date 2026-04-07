---
phase: 15-phase-diagram-data-update
verified: 2026-04-08T00:00:00Z
uat_tested: 2026-04-08T00:00:00Z
status: gaps_found
score: 10/12 must-haves verified
gaps:
  - truth: "Ice Ic appears in the generated phase diagram (CLI)"
    status: failed
    reason: "GUI renders Ice Ic correctly, but CLI export does not include Ice Ic in output"
    artifacts:
      - path: "quickice/output/phase_diagram.py"
        issue: "CLI export path does not include ice_ic in rendering"
    missing:
      - "Add 'ice_ic' to CLI export rendering path"
  - truth: "Ice Ic polygon boundaries are correct (no overlap with Ice XI)"
    status: failed
    reason: "Ice Ic polygon overlaps with Ice XI region in GUI visualization"
    artifacts:
      - path: "quickice/output/phase_diagram.py"
        issue: "Ice Ic defined as 50-150K, but Ice XI exists below 72K"
    missing:
      - "Adjust Ice Ic lower boundary to 72K to avoid Ice XI overlap"
      - "OR add phase priority logic: check Ice XI before Ice Ic"
  - truth: "Ice Ic upper pressure boundary is thermodynamically correct"
    status: failed
    reason: "100 MPa upper limit may not match actual metastable range for Ice Ic"
    artifacts:
      - path: "quickice/output/phase_diagram.py"
        issue: "Hardcoded 100 MPa boundary without scientific validation"
    missing:
      - "Verify correct metastable pressure range from literature"
      - "Adjust upper pressure boundary based on thermodynamic data"
  - truth: "Polygon boundaries align with corrected thermodynamic data (phase_diagram.py)"
    status: failed
    reason: "phase_diagram.py has hardcoded old triple point values in polygon builders"
    artifacts:
      - path: "quickice/output/phase_diagram.py"
        issue: "Lines 261-262, 301, 306, 311-334, 458, 460 use hardcoded old values"
    missing:
      - "Replace hardcoded values with get_triple_point() calls"
uat_reference: ".planning/phases/15-phase-diagram-data-update/15-UAT.md"
---

# Phase 15: Phase Diagram Data Update Verification Report

**Phase Goal:** Users receive accurate ice phase predictions based on IAPWS R14-08(2011) compliant thermodynamic data

**Verified:** 2026-04-08T00:00:00Z

**Status:** gaps_found

**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                 | Status     | Evidence       |
|-----|------------------------------------------------------------------------|------------|----------------|
| 1   | Triple point data is consistent across both files                    | ✓ VERIFIED | cross-file check: all 8 match |
| 2   | All 8 triple points have IAPWS R14-08(2011) compliant values          | ✓ VERIFIED | Values match IAPWS/Journaux |
| 3   | Values match between triple_points.py and ice_boundaries.py           | ✓ VERIFIED | All 8 values verified |
| 4   | Ice Ic appears in the generated phase diagram (GUI)                   | ✓ VERIFIED | GUI renders polygon and label |
| 5   | Ice Ic polygon is rendered with correct metastable region boundaries  | ✗ FAILED   | Overlaps Ice XI, boundary incorrect |
| 6   | Phase diagram shows Ice Ic label in the correct location (GUI)        | ✓ VERIFIED | Label visible in GUI |
| 4b  | Ice Ic appears in CLI export                                          | ✗ FAILED   | CLI export missing Ice Ic |
| 7   | PHASE_POLYGONS vertices reflect corrected triple point values         | ✓ VERIFIED | No old values found, 8 corrected found |
| 8   | MELTING_CURVE_COEFFICIENTS Pref values are IAPWS compliant           | ✓ VERIFIED | All 5 Pref values verified |
| 9   | Polygon boundaries align with corrected thermodynamic data            | ✗ FAILED   | phase_diagram.py has hardcoded old values |
| 10  | Test comments reference correct triple point values                   | ✓ VERIFIED | grep shows correct values (249.4K, 209.9MPa, etc.) |
| 11  | Documentation comments reflect IAPWS R14-08(2011) data sources        | ✓ VERIFIED | lookup.py docstring cites IAPWS and Journaux |
| 12  | Tests pass with corrected values                                       | ✓ VERIFIED | 62/62 tests pass |

**Score:** 10/12 truths verified (2 partial: GUI works, CLI fails)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quickice/phase_mapping/triple_points.py` | TRIPLE_POINTS dict | ✓ VERIFIED | All 8 triple points with correct IAPWS/Journaux values |
| `quickice/phase_mapping/data/ice_boundaries.py` | TRIPLE_POINTS, PHASE_POLYGONS, MELTING_CURVE_COEFFICIENTS | ✓ VERIFIED | All values updated, P_ref values verified |
| `quickice/output/phase_diagram.py` | Ice Ic polygon builder and rendering | ⚠️ PARTIAL | GUI renders correctly, CLI export missing, boundaries overlap Ice XI |
| `tests/test_phase_mapping.py` | Updated test comments | ✓ VERIFIED | Comments reference correct values |
| `quickice/phase_mapping/lookup.py` | Updated docstring | ✓ VERIFIED | Cites IAPWS and Journaux |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `triple_points.py` | `ice_boundaries.py` | Same dict values | ✓ VERIFIED | All 8 values match exactly |
| `_build_phase_polygon_from_curves()` | `_build_ice_ic_polygon()` | dispatch | ✓ VERIFIED | `elif phase_id == "ice_ic"` exists at line 207-208 |
| GUI rendering | ice_ic polygon | rendering | ✓ VERIFIED | Polygon and label visible in GUI |
| CLI export | ice_ic rendering | export path | ✗ NOT_WIRED | CLI export does not include Ice Ic |
| Ice Ic polygon | Ice XI polygon | boundary | ✗ OVERLAP | Ice Ic (50-150K) overlaps Ice XI (<72K) |
| polygon builders | get_triple_point() | function calls | ⚠️ PARTIAL | Some use get_triple_point(), others hardcode old values |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `phase_diagram.py` | 261-262 | Hardcoded old TP (238.55, 212.9) | Medium | Polygon uses wrong triple point |
| `phase_diagram.py` | 301, 306 | Hardcoded 248.85 (old II-III-V TP) | Medium | Polygon uses wrong boundary |
| `phase_diagram.py` | 311-325 | Hardcoded 218.95, 620.0 (old II-V-VI TP) | Medium | Multiple boundaries use wrong values |
| `phase_diagram.py` | Ice Ic polygon | Lower boundary at 50K | High | Overlaps Ice XI (<72K) |
| `phase_diagram.py` | Ice Ic polygon | Upper boundary 100 MPa | High | May not match metastable range |
| CLI export | rendering path | ice_ic not included | Medium | CLI users cannot see Ice Ic |

### Human Verification Required

None - all issues can be verified programmatically.

### Gaps Summary

**4 gaps found (diagnosed via UAT):**

1. **CLI export missing Ice Ic** - The GUI renders Ice Ic correctly, but the CLI export path does not include Ice Ic in the exported diagram. CLI users cannot visualize the Ice Ic phase region.

2. **Ice Ic overlaps Ice XI** - The Ice Ic polygon is defined as 50-150K, but Ice XI exists below 72K. This creates a visual overlap in the GUI phase diagram, causing confusion about which phase is present.

3. **Ice Ic upper pressure boundary may be incorrect** - The 100 MPa upper limit may not match the actual metastable range for Ice Ic. Need to verify against scientific literature and adjust if necessary.

4. **phase_diagram.py has hardcoded old triple point values** - Multiple polygon building functions in `phase_diagram.py` have hardcoded old values instead of using `get_triple_point()`:
   - `_build_ice_ih_polygon()`: Lines 261-262 use (238.55, 212.9)
   - `_build_ice_ii_polygon()`: Multiple hardcoded values at lines 301, 306, 311-334, 458, 460

**Root cause:** 
- Plan 15-02 added the polygon builder but did not account for Ice XI overlap
- Plan 15-02 did not verify the 100 MPa upper boundary against literature
- CLI export uses a different rendering path than GUI
- Polygon builders were not updated to use get_triple_point() instead of hardcoded values

**What works:**
- TRIPLE_POINTS dictionaries in both files are consistent and correct
- PHASE_POLYGONS and MELTING_CURVE_COEFFICIENTS are updated
- Test comments and lookup.py documentation are updated
- All 62 tests pass
- GUI renders Ice Ic polygon and label correctly (visual output works)

---

## User Acceptance Testing

**UAT Report:** `.planning/phases/15-phase-diagram-data-update/15-UAT.md`

**Tester:** User
**Date:** 2026-04-08

**Findings:**
- GUI: Ice Ic polygon and label visible ✓
- GUI: Ice Ic overlaps Ice XI ✗
- GUI: Upper boundary (100 MPa) needs verification ✗
- CLI: Ice Ic not in exported diagram ✗

---

_Verified: 2026-04-08T00:00:00Z_
_Verifier: OpenCode (gsd-verifier) + User (UAT)_