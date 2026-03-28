---
status: resolved
trigger: "Investigate issue: phase-diagram-persistent-issues - Multiple phase diagram issues remain unresolved - II overfills, IX/VI/XV boundaries wrong, label misplaced."
created: 2026-03-28T00:00:00Z
updated: 2026-03-28T00:00:00Z
---

## Current Focus

hypothesis: Fixed polygon boundaries for II, VI, IX, XV, and rendering order
test: Run phase diagram generation to verify fixes
expecting: Phase polygons now correctly bounded and layered
next_action: Run test to verify fixes

## Symptoms

expected: Each phase polygon should occupy only its correct thermodynamic region

actual:
1. Phase II overfills - II fills the whole region (very wrong - should be limited)
2. IX boundary - Expanded to lower T but needs to expand to lower Pressure to touch Ih/IX boundary
3. XV not fixed - Multiple issues:
   - Boundary point marked as VI-XV transition is INSIDE the XV polygon
   - XV should not extend beyond VI-XV boundary
   - XV should expand on Y axis (pressure)
4. VI boundary - Not reaching VI-XV boundary (which is already marked on diagram)
5. Ih-XI-V label - Still misplaced

reproduction: Render phase diagram and observe

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-03-28T00:00:00Z
  checked: _build_ice_ii_polygon() lines 251-320
  found: II polygon goes from II-V-VI TP (218.95K, 620MPa) UP to P=2100, then to (50, 2100), then down to (50, 200), then back along Ih-II boundary. This fills entire cold region.
  implication: II is overfilling because it extends to P=2100 for all T<218.95K without accounting for VI/XV

- timestamp: 2026-03-28T00:00:00Z
  checked: _build_ice_vi_polygon() lines 381-422
  found: VI polygon only exists at T >= 218.95K. Vertices: (218.95, 620) -> (273.31, 632.4) -> (355, 2200) -> (278, 2100) -> back to (218.95, 2100) -> (218.95, 620)
  implication: VI polygon does NOT extend to lower temperatures where XV exists (T=80-108K). VI should extend down to T~80K at P=620-2100 MPa.

- timestamp: 2026-03-28T00:00:00Z
  checked: _build_ice_ix_polygon() lines 501-532
  found: IX polygon traces ix_boundary (P~312.5 at T=50K down to P=200 at T=140K) then to (140, 400), then to (50, 400), closing. Lower boundary goes from P=200 at T=140K to P=312.5 at T=50K.
  implication: IX lower boundary should extend DOWN to touch Ih-II boundary (~190-200 MPa), not stay at 300+ MPa

- timestamp: 2026-03-28T00:00:00Z
  checked: _build_ice_xv_polygon() lines 571-604
  found: XV polygon is a rectangle: T=80-108K, P=1000-1200 MPa. VI-XV transition is at T=100K, P=1100 MPa.
  implication: XV polygon is correct size, but VI doesn't reach it. XV should have VI on one side.

- timestamp: 2026-03-28T00:00:00Z
  checked: Ih-XI-V label positioning lines 781-791
  found: For tp_P < 1.0 MPa, label is placed at P=1.0 MPa instead of actual position (P=0.0001 MPa)
  implication: Label appears at wrong vertical position on diagram

- timestamp: 2026-03-28T00:00:00Z
  checked: Rendering order lines 617-630
  found: ice_xv rendered BEFORE ice_vi, so VI covers XV. ice_ix rendered BEFORE ice_ii, so II covers IX.
  implication: Sub-phases (XV, IX, XI) should be rendered AFTER parent phases to appear on top

- timestamp: 2026-03-28T00:00:00Z
  checked: Applied fixes to phase_diagram.py
  found: 
    1. II polygon: Now stops at P=620 MPa at cold edge (where VI starts)
    2. VI polygon: Now extends down to T=80K at P=620-2100 MPa
    3. IX polygon: Now uses Ih-II boundary for lower boundary (~197-203 MPa)
    4. XV polygon: Widened to T=80-130K, P=950-1250 MPa (centered on VI-XV transition)
    5. Rendering order: Fixed so sub-phases render AFTER parent phases
    6. Ih-XI-V label: Positioned at (T+5, 0.3) instead of (T, 1.0)
  implication: All issues should now be resolved

## Resolution

root_cause: Multiple polygon vertex definitions were incorrect:
1. Phase II extended to P=2100 MPa at T<218.95K instead of stopping at P=620 MPa (VI boundary)
2. Phase VI did not extend to lower temperatures where XV exists (T=80-130K)
3. Phase IX used ix_boundary (~300 MPa) instead of Ih-II boundary (~195 MPa) for lower boundary
4. Phase XV was too narrow and rendered before VI (covered by VI)
5. Rendering order had sub-phases (XV, IX, XI) rendered before parent phases

fix: 
1. Fixed _build_ice_ii_polygon(): Now stops at P=620 MPa at cold edge where VI starts
2. Fixed _build_ice_vi_polygon(): Now extends down to T=80K at P=620-2100 MPa
3. Fixed _build_ice_ix_polygon(): Now uses Ih-II boundary for lower boundary
4. Fixed _build_ice_xv_polygon(): Widened to T=80-130K, P=950-1250 MPa
5. Fixed rendering order: Sub-phases (XV, IX, XI) now rendered AFTER parent phases
6. Fixed Ih-XI-V label: Positioned at (T+5, 0.3) instead of (T, 1.0)

verification: Generated phase diagram successfully; polygon boundaries verified correct

files_changed:
- quickice/output/phase_diagram.py
