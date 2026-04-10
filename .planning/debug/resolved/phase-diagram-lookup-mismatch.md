---
status: resolved
trigger: "Phase diagram click lookup mismatch - Ice XV, Ice VI appear triclinic, clicking on VI sometimes gives II, some points on XV give II or not supported"
created: 2026-04-10T00:00:00
updated: 2026-04-10T00:45:00
---

## Current Focus

hypothesis: RESOLVED - Fixed XV/VI/II polygon temperature ranges to match lookup_phase() conditions
test: All 62 tests pass, PhaseDetector and lookup_phase() now agree on phase identification
expecting: Commit changes and archive
next_action: Complete debug session

## Symptoms

expected: Clicking on phase region in diagram should return that specific phase
actual: Clicking on VI sometimes gives II, clicking on XV returns II or "not supported"
errors: Wrong phase returned from diagram click
reproduction: Click on VI or XV region in phase diagram
timeline: Unknown

## Eliminated

- None

## Evidence

- timestamp: 2026-04-10T00:01:00
  checked: _build_ice_xv_polygon() in quickice/output/phase_diagram.py
  found: XV polygon is defined as T=50-100K, P=950-2100 MPa
  implication: Polygon covers T=50-100K range

- timestamp: 2026-04-10T00:02:00
  checked: lookup_phase() in quickice/phase_mapping/lookup.py
  found: XV condition is T=80-108K, P=950-2100 MPa
  implication: Lookup covers T=80-108K range - MISMATCH with polygon!

- timestamp: 2026-04-10T00:04:00
  checked: Specific coordinate cases BEFORE FIX
  found: |
    - T=60K, P=1000 MPa: polygon says XV, lookup_phase() returns II (MISMATCH)
    - T=105K, P=1500 MPa: polygon says VI, lookup_phase() returns XV (MISMATCH)
    - T=150K, P=1000 MPa: polygon says VI, lookup_phase() returns II (MISMATCH)
  implication: Multiple mismatches between polygon and lookup

- timestamp: 2026-04-10T00:10:00
  checked: VI polygon vs lookup_phase() condition
  found: |
    - VI polygon: starts at T=100K, goes to T=355K
    - lookup_phase() VI check: T >= 218.95K only
    - Gap: T=100-218K where polygon says VI but lookup returns II
  implication: lookup_phase() missing VI region for T < 218.95K

- timestamp: 2026-04-10T00:25:00
  checked: AFTER FIX - Verification tests
  found: |
    - T=60K, P=1000 MPa: II polygon contains, lookup returns II ✓
    - T=90K, P=1500 MPa: XV polygon contains, lookup returns XV ✓
    - T=105K, P=1500 MPa: XV polygon contains, lookup returns XV ✓
    - T=110K, P=1500 MPa: VI polygon contains, lookup returns VI ✓
    - T=150K, P=1000 MPa: VI polygon contains, lookup returns VI ✓
  implication: All main mismatches fixed!

- timestamp: 2026-04-10T00:40:00
  checked: pytest tests/test_phase_mapping.py
  found: All 62 tests pass
  implication: Fix doesn't break existing functionality

- timestamp: 2026-04-10T00:42:00
  checked: II polygon fix for T < 80K
  found: II polygon extended to P=2100 MPa for T < 80K to fill gap
  implication: T=60K, P=1000 MPa now correctly identified as II

## Resolution

root_cause: Three issues caused mismatch between PhaseDetector (polygon-based) and lookup_phase() (curve-based):
1. XV polygon defined T=50-100K but lookup_phase() checked T=80-108K
2. VI polygon extended to T=100K but lookup_phase() only checked VI for T >= 218.95K
3. II polygon stopped at P=950 MPa for T < 100K, leaving a gap at T < 80K, P > 950 MPa

fix: 
1. Updated _build_ice_xv_polygon() to use T=80-108K (matching lookup_phase() condition)
2. Updated _build_ice_vi_polygon() to start at T=108K (above XV range)
3. Added VI lookup check for T=108-218K in lookup_phase() (fills gap between XV and main VI region)
4. Updated _build_ice_ii_polygon() to extend to P=2100 MPa for T < 80K (fills gap below XV)

verification: All test cases now match between polygon and lookup; 62 pytest tests pass; boundary cases (T=80K) correctly return "II/XV"
files_changed:
- quickice/output/phase_diagram.py (XV, VI, and II polygon definitions)
- quickice/phase_mapping/lookup.py (added VI check for T=108-218K)
