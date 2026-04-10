---
status: resolved
trigger: "ice-ii-diagram-lookup"
created: 2026-04-10T00:00:00Z
updated: 2026-04-10T02:00:00Z
---

## Current Focus

hypothesis: RESOLVED
test: N/A
expecting: N/A
next_action: Archive and commit

## Symptoms

expected: Ice II structure should be generated when clicking on Ice II region in phase diagram
actual: All clicks in Ice II region show Ice II info in display, but when generating ice structure, upper right area of Ice II region generates Ice VI instead of Ice II
errors: None visible - phase detection appears correct, only structure generation is wrong
reproduction: Click on upper right area of Ice II region in phase diagram, then generate ice structure - will produce Ice VI instead of Ice II
started: Not sure if this existed before the XV/VI fix (commit d2346f5)

## Eliminated

- hypothesis: Ice II polygon just needs to match VI polygon
  evidence: VI polygon was also wrong - extended below II-V-VI TP
  timestamp: 2026-04-10T01:00:00Z

## Evidence

- timestamp: 2026-04-10T00:30:00Z
  checked: Previous fix commit d2346f5 and XV/VI handling
  found: XV/VI fix aligned polygon definitions with lookup_phase() conditions - same pattern needed for Ice II
  implication: Need to compare Ice II polygon with lookup conditions

- timestamp: 2026-04-10T00:45:00Z
  checked: Ice II polygon in phase_diagram.py (lines 400-479) vs VI lookup in lookup.py (lines 245-278)
  found: TWO BUGS:
    1. Ice II polygon traced incorrect "VI left edge" instead of V-VI boundary
    2. VI lookup returned Ice VI for all P > 620 at T >= 218.95K WITHOUT checking V-VI boundary
  implication: Both polygon and lookup needed fixes

- timestamp: 2026-04-10T00:55:00Z
  checked: VI lookup logic for T >= 218.95K (lines 249-278)
  found: For T in [218.95, 278], P > 620, returned Ice VI without checking if point is below V-VI boundary
  implication: Points in Ice V or Ice II region at T >= 218.95K incorrectly returned Ice VI

- timestamp: 2026-04-10T01:10:00Z
  checked: VI gap fill logic at T=100-218.95K
  found: VI gap fill assumed VI exists at T > 100K, but VI only exists at T >= II-V-VI TP (201.9K)
  implication: Fixed VI gap fill to only apply for T >= 201.9K

- timestamp: 2026-04-10T01:30:00Z
  checked: VI polygon construction
  found: VI polygon extended below II-V-VI TP (201.9K) down to T=100K, but VI doesn't exist below 201.9K
  implication: Fixed VI polygon to stop at II-V-VI TP

- timestamp: 2026-04-10T01:45:00Z
  checked: Ice II polygon construction
  found: Ice II polygon traced V-VI boundary for T < 201.9K, but VI doesn't exist there
  implication: Fixed Ice II polygon to extend to P=945 MPa (below XV) for T < 201.9K

## Resolution

root_cause: Three related issues:
  1. Ice II polygon traced incorrect boundary (arbitrary "VI left edge" instead of actual phase boundaries)
  2. VI lookup didn't check V-VI boundary for T in [218.95, 278K]
  3. VI gap fill assumed VI exists at T > 100K, but VI only exists at T >= II-V-VI TP (201.9K)

fix: 
  1. Fixed VI lookup to check V-VI boundary before returning Ice VI for T in [218.95, 278K]
  2. Fixed VI gap fill to only apply for T >= 201.9K (II-V-VI TP)
  3. Fixed VI polygon to stop at II-V-VI TP (not extend below 201.9K)
  4. Fixed Ice II polygon to properly define boundaries for T < 201.9K

verification: All 62 phase mapping tests pass. Polygon/lookup consistency verified for test points in problematic region.

files_changed:
  - quickice/phase_mapping/lookup.py: Fixed VI lookup logic
  - quickice/output/phase_diagram.py: Fixed II and VI polygon definitions
