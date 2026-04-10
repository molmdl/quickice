---
status: resolved
trigger: "Fix: Phase diagram polygon boundaries correctly - previous fix d2346f5 was WRONG"
created: 2026-04-10T00:00:00Z
updated: 2026-04-10T00:02:00Z
---

## Current Focus

hypothesis: XV polygon boundaries are correct (T=50-100K), but lookup_phase() has wrong range (T=80-108K)
test: Compare polygon definitions with lookup conditions after revert
expecting: XV polygon at T=50-100K, lookup at T=80-108K (needs fixing)
next_action: Fix complete - resolved

## Symptoms

expected: XV polygon should be T=50-100K, and lookup_phase() should also match T=50-100K
actual: Previous fix d2346f5 changed polygon to T=80-108K to match the wrong lookup range
errors: Wrong approach - changed the correct polygon instead of fixing the incorrect lookup
reproduction: Visual inspection of polygon boundaries and lookup conditions
started: After commit d2346f5 was applied

## Eliminated

- hypothesis: XV polygon needed to change from T=50-100K to T=80-108K
  evidence: XV polygon should extend to lower temperature, not be narrower. The polygon was correct, the lookup was wrong.
  timestamp: 2026-04-10T00:00:00Z

## Evidence

- timestamp: 2026-04-10T00:00:00Z
  checked: Git status
  found: Revert of d2346f5 is staged but not committed. Files modified: phase_diagram.py, lookup.py
  implication: Need to verify what the revert restored and apply correct fix

- timestamp: 2026-04-10T00:00:01Z
  checked: phase_diagram.py _build_ice_xv_polygon() (lines 785-817)
  found: XV polygon is T=50-100K, P=950-2100 MPa (reverted to original)
  implication: Polygon is correct, matches desired state

- timestamp: 2026-04-10T00:00:02Z
  checked: lookup.py lookup_phase() XV condition (lines 228-232)
  found: XV lookup condition: if 80.0 <= T <= 108.0 and 950 <= P <= 2100
  implication: Lookup has wrong T range (80-108K instead of 50-100K) - THIS IS THE BUG

- timestamp: 2026-04-10T00:00:03Z
  checked: phase_diagram.py _build_ice_vi_polygon() (lines 540-577)
  found: VI polygon cold boundary at T=100K (reverted to original)
  implication: VI polygon is correct

- timestamp: 2026-04-10T00:00:04Z
  checked: phase_diagram.py _build_ice_ii_polygon() (lines 400-479)
  found: II polygon stays at P=950 for T < 100K (reverted to original)
  implication: II polygon is correct for the XV range T=50-100K

- timestamp: 2026-04-10T00:00:05Z
  checked: XV phase lookup at T=50-100K
  found: Correctly identifies ice_xv at all temperatures in range
  implication: Fix is working correctly

- timestamp: 2026-04-10T00:00:06Z
  checked: All phase-related tests
  found: 119 tests pass
  implication: Fix doesn't break existing functionality

## Resolution

root_cause: lookup_phase() had wrong temperature range for XV phase (T=80-108K instead of T=50-100K). The polygon definitions were correct, but the lookup logic didn't match.
fix: Changed XV lookup condition from T=80-108K to T=50-100K in lookup.py
verification: All 119 phase-related tests pass. Polygon and lookup now correctly identify XV at T=50-100K, P=950-2100 MPa.
files_changed: [quickice/phase_mapping/lookup.py]
