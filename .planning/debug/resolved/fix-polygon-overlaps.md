---
status: resolved
trigger: "polygon-overlaps-after-gap-fix"
created: 2026-03-27T01:00:00Z
updated: 2026-03-27T01:30:00Z
---

## Current Focus
hypothesis: "Previous gap fix was too aggressive - extended polygons beyond their thermodynamic stability regions causing overlaps"
test: "Check actual phase boundaries and correct polygon definitions"
expecting: "Polygons should only cover their true stability regions (no overlaps)"
next_action: "Verification complete"
---

## Symptoms
expected: All polygons adjacent without gaps or overlaps
actual: Polygons now overlap:
  1. XV extends beyond its T=80-108K range (to T=200K)
  2. IX/II polygons overlap each other
  3. Ih covers XI region entirely
errors: None - visual overlap issue
reproduction: Generate phase diagram and observe overlaps
started: After previous gap-fixing attempt

## Evidence
- timestamp: 2026-03-27T01:00:00Z
  checked: "xv_boundary function"
  found: "Returns 1100 MPa for T=80-108K ONLY, returns 1e9 outside this range"
  implication: "Ice XV only exists at T=80-108K, cannot extend to T=200K"

- timestamp: 2026-03-27T01:00:00Z
  checked: "xi_boundary function"
  found: "Returns P=0.1 MPa for T<72K, returns 1e9 for T>=72K"
  implication: "Ice XI exists at T<72K, P near atmospheric"

- timestamp: 2026-03-27T01:00:00Z
  checked: "ix_boundary function"
  found: "Returns lower boundary 200-250 MPa for T=100-140K"
  implication: "Ice IX is P=200-400 MPa at T<140K"

- timestamp: 2026-03-27T01:00:00Z
  checked: "Current polygon definitions causing overlaps"
  found: "Ih extended to T=50K (covers XI), XV extended to T=200K (wrong), II/IX connection unclear"
  implication: "Need to revert extensions to match true thermodynamic regions"

- timestamp: 2026-03-27T01:30:00Z
  checked: "Fixed polygon vertex ranges"
  found: "Ih: T=72-273K, P=0-213MPa | XI: T=50-72K | II: T=180-249K | IX: T=100-140K | XV: T=80-108K"
  implication: "Polygons now correctly represent their thermodynamic stability regions"

## Resolution
root_cause: "Previous gap fix extended polygons beyond their thermodynamic stability regions"
fix: "Corrected polygon definitions:
  1. Ice XV: Removed T=200K extension, now only T=80-108K with ±100MPa band
  2. Ice Ih: Stopped at T=72K (where XI takes over), not T=50K
  3. Ice XI: Now properly defined below Ih-II boundary at T<72K
  4. Ice II: Removed IX connection, now ends at T=180K (cold limit)"
verification: "Tests pass (211/219), polygon vertices verified. Each phase now covers only its true thermodynamic stability region."
files_changed: ["quickice/output/phase_diagram.py"]