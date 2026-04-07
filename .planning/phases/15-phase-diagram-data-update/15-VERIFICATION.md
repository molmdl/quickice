---
phase: 15-phase-diagram-data-update
verified: 2026-04-08T12:00:00Z
status: gaps_found
score: 11/12 must-haves verified
re_verification: true
previous_status: passed
previous_score: 12/12
gaps_closed:
  - "Ice Ic appears in the generated phase diagram (CLI) - now included in phases_to_plot"
  - "Ice Ic polygon boundaries correct (no overlap with Ice XI) - lower boundary now 72K"
  - "Polygon boundaries align with corrected thermodynamic data - all get_triple_point() calls used"
gaps_remaining:
  - "Ice Ic upper pressure boundary (100 MPa) is scientifically incorrect - should be ~200 MPa to match Ice Ih"
---

# Phase 15: Phase Diagram Data Update Verification Report

**Phase Goal:** Users receive accurate ice phase predictions based on IAPWS R14-08(2011) compliant thermodynamic data

**Verified:** 2026-04-08T12:00:00Z

**Status:** gaps_found

**Re-verification:** Yes — user identified scientific accuracy issue with Ice Ic upper boundary

## Goal Achievement

### Observable Truths

| #   | Truth                                                                 | Status     | Evidence       |
|-----|------------------------------------------------------------------------|------------|----------------|
| 1   | Triple point data is consistent across both files                    | ✓ VERIFIED | cross-file check: all 8 match |
| 2   | All 8 triple points have IAPWS R14-08(2011) compliant values          | ✓ VERIFIED | Values match IAPWS/Journaux |
| 3   | Values match between triple_points.py and ice_boundaries.py           | ✓ VERIFIED | All 8 values verified |
| 4   | Ice Ic appears in the generated phase diagram (GUI)                   | ✓ VERIFIED | GUI renders polygon and label |
| 5   | Ice Ic polygon is rendered with correct metastable region boundaries  | ⚠ PARTIAL | Lower boundary at 72K ✓, Upper boundary 100 MPa incorrect (should be ~200 MPa) |
| 6   | Phase diagram shows Ice Ic label in the correct location (GUI)        | ✓ VERIFIED | Label visible in GUI |
| 4b  | Ice Ic appears in CLI export                                          | ✓ VERIFIED | generate_phase_diagram() includes ice_ic in phases_to_plot |
| 7   | PHASE_POLYGONS vertices reflect corrected triple point values         | ✓ VERIFIED | No old values found, 8 corrected found |
| 8   | MELTING_CURVE_COEFFICIENTS Pref values are IAPWS compliant           | ✓ VERIFIED | All 5 Pref values verified |
| 9   | Polygon boundaries align with corrected thermodynamic data            | ✓ VERIFIED | All polygon builders use get_triple_point() |
| 10  | Test comments reference correct triple point values                   | ✓ VERIFIED | grep shows correct values (249.4K, 209.9MPa, etc.) |
| 11  | Documentation comments reflect IAPWS R14-08(2011) data sources        | ✓ VERIFIED | lookup.py docstring cites IAPWS and Journaux |
| 12  | Tests pass with corrected values                                       | ✓ VERIFIED | 62/62 tests pass |

**Score:** 11/12 truths verified (1 partial)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quickice/phase_mapping/triple_points.py` | TRIPLE_POINTS dict | ✓ VERIFIED | All 8 triple points with correct IAPWS/Journaux values |
| `quickice/phase_mapping/data/ice_boundaries.py` | TRIPLE_POINTS, PHASE_POLYGONS, MELTING_CURVE_COEFFICIENTS | ✓ VERIFIED | All values updated, P_ref values verified |
| `quickice/output/phase_diagram.py` | Ice Ic polygon builder and rendering | ⚠ PARTIAL | Ice Ic included ✓, lower boundary correct ✓, upper boundary incorrect (100 MPa should be ~200 MPa) |
| `tests/test_phase_mapping.py` | Updated test comments | ✓ VERIFIED | Comments reference correct values |
| `quickice/phase_mapping/lookup.py` | Updated docstring | ✓ VERIFIED | Cites IAPWS and Journaux |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `triple_points.py` | `ice_boundaries.py` | Same dict values | ✓ VERIFIED | All 8 values match exactly |
| `_build_phase_polygon_from_curves()` | `_build_ice_ic_polygon()` | dispatch | ✓ VERIFIED | `elif phase_id == "ice_ic"` exists at line 207-208 |
| GUI rendering | ice_ic polygon | rendering | ✓ VERIFIED | Polygon and label visible in GUI |
| CLI export (generate_phase_diagram) | ice_ic rendering | export path | ✓ VERIFIED | ice_ic in phases_to_plot at line 774 |
| Ice Ic polygon | Ice XI polygon | boundary | ⚠ PARTIAL | Ice Ic (72-150K) does not overlap Ice XI (<72K) ✓, BUT upper P boundary incorrect |
| polygon builders | get_triple_point() | function calls | ✓ VERIFIED | All polygon builders use get_triple_point() (23 calls found) |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Status |
|------|------|---------|----------|--------|
| `phase_diagram.py` | (was 261-262) | Hardcoded old TP (238.55, 212.9) | Medium | ✓ FIXED - Now uses get_triple_point() |
| `phase_diagram.py` | (was 301, 306) | Hardcoded 248.85 (old II-III-V TP) | Medium | ✓ FIXED - Now uses get_triple_point() |
| `phase_diagram.py` | (was 311-325) | Hardcoded 218.95, 620.0 (old II-V-VI TP) | Medium | ✓ FIXED - Now uses get_triple_point() |
| `phase_diagram.py` | Ice Ic polygon | Lower boundary at 50K | High | ✓ FIXED - Now 72K |
| `phase_diagram.py` | Ice Ic polygon | Upper boundary 100 MPa | High | ✗ NEEDS FIX - Should be ~200 MPa to match Ice Ih boundary |
| `generate_phase_diagram` | rendering path | ice_ic not included | Medium | ✓ FIXED - Now included in phases_to_plot |

### Gap Found

**Ice Ic Upper Pressure Boundary Scientifically Incorrect**

**Current implementation:** 100 MPa upper limit
**Issue:** Arbitrary value not scientifically justified
**Correct value:** Should be ~200 MPa (matching Ice Ih boundary in T=72-150K range)

**Evidence:**
```python
# Ice Ih polygon at low temperatures (T=72-150K):
# At T=72K: P≈196 MPa (Ih-II boundary)
# At T=150K: P≈204 MPa (Ih-II boundary)
# Range: 196-210 MPa

# Ice Ic (metastable relative to Ice Ih):
# Should extend to same pressure range where Ice Ih is stable
# Current 100 MPa limit incorrectly truncates the region
```

**Scientific rationale:**
1. Ice Ic is metastable with respect to Ice Ih
2. No defined thermodynamic upper pressure boundary exists
3. Ice Ic can exist metastably wherever Ice Ih is stable
4. Therefore, Ice Ic should extend to the Ih-II boundary (~200 MPa)
5. The 100 MPa limit is arbitrary and not scientifically supported

**Impact:**
- Users see incorrect Ice Ic region in phase diagram
- Scientific accuracy compromised
- Visualization does not reflect actual metastable range

**Recommended fix:**
- Update `_build_ice_ic_polygon()` upper pressure boundary to ~200 MPa
- Optionally: Use Ih-II boundary function for dynamic upper limit

### Gaps Summary

**Previous gaps (all closed):**

1. ✓ **CLI export missing Ice Ic** - Fixed in Plan 15-07. The `generate_phase_diagram()` function (line 774) now includes "ice_ic" in the `phases_to_plot` list. When the diagram is saved via `plt.savefig()`, Ice Ic is now rendered.

2. ✓ **Ice Ic overlaps Ice XI** - Fixed by updating `_build_ice_ic_polygon()`. The lower boundary is now 72K (matching Ice XI's upper boundary at the Ih_XI_Vapor triple point). Verified programmatically: `min_T = 72.0K, max_T = 150.0K`.

3. ✓ **phase_diagram.py has hardcoded old triple point values** - Fixed in Plan 15-07. All polygon builders now use `get_triple_point()` calls instead of hardcoded values. Verified by:
   - grep shows 23 uses of `get_triple_point` in phase_diagram.py
   - No hardcoded old values (248.85, 218.95, 207.5, 238.55) remain
   - Tests confirm correct triple point values in polygon vertices

**NEW GAP FOUND:**

4. ✗ **Ice Ic upper pressure boundary scientifically incorrect** - The 100 MPa upper limit is arbitrary and not scientifically justified. Ice Ic should extend to ~200 MPa (matching Ice Ih's boundary at T=72-150K). This requires a new gap closure plan.

**What works:**
- TRIPLE_POINTS dictionaries in both files are consistent and correct
- PHASE_POLYGONS and MELTING_CURVE_COEFFICIENTS are updated
- Test comments and lookup.py documentation are updated
- All 62 tests pass
- GUI renders Ice Ic polygon and label correctly
- CLI export now includes Ice Ic in generated diagrams
- No overlap between Ice Ic and Ice XI regions (lower boundary correct)

**What needs fixing:**
- Ice Ic upper pressure boundary (100 MPa → ~200 MPa)

---

_Verified: 2026-04-08T12:00:00Z_
_Verifier: OpenCode (gsd-verifier)_