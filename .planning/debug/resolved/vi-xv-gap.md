---
status: resolved
trigger: "VI polygon gap fix broke VI-XV interface"
created: 2026-04-10T03:00:00Z
updated: 2026-04-10T03:30:00Z
---

## Current Focus

hypothesis: RESOLVED
test: N/A
expecting: N/A
next_action: Archive and commit

## Symptoms

expected: VI should extend from II-V-VI TP (201.9K, 670.8 MPa) down to T=100K where it meets XV
actual: Huge gap between VI and XV - points at T=100-201.9K with high pressure return Ice II instead of Ice VI
errors: Wrong phase identification
reproduction: Click in phase diagram at T=150K, P=1000 MPa - returns Ice II instead of Ice VI

## Evidence

- timestamp: 2026-04-10T03:00:00Z
  checked: My previous commit 1976afc
  found: Removed VI from T < 201.9K entirely, but VI should exist there at high pressures
  implication: Need to restore VI at T in [100, 201.9K] with proper boundary checking

- timestamp: 2026-04-10T03:10:00Z
  checked: V-VI boundary extrapolation
  found: v_vi_boundary(T) extrapolates correctly for T < 201.9K
  implication: VI gap fill can use extrapolated V-VI boundary

- timestamp: 2026-04-10T03:15:00Z
  checked: VI gap fill condition
  found: Condition was `100.0 < T < 218.95`, excluding T=100K
  implication: At T=100K, narrow VI band [726, 950] was missing

## Resolution

root_cause: My previous fix incorrectly removed VI from T < 201.9K. VI should extend from T=100K (meeting XV) up to II-V-VI TP and beyond, bounded by extrapolated V-VI boundary.

fix:
  1. Changed VI gap fill from `T_ii_v_vi <= T < 218.95` to `100.0 <= T < 218.95` to include T=100K
  2. Fixed VI polygon to extend from II-V-VI TP down to T=100K (meeting XV)
  3. Fixed Ice II polygon to trace just below extrapolated V-VI boundary for T in [100, 201.9K]

verification: All 62 phase mapping tests pass. Polygon/lookup consistency verified for VI-XV interface and Ice II region.

files_changed:
  - quickice/phase_mapping/lookup.py: Fixed VI gap fill to include T >= 100K
  - quickice/output/phase_diagram.py: Fixed VI and II polygons for T in [100, 201.9K]
