---
status: resolved
trigger: "Phase diagram still has issues with II, XV, VI boundaries and Ih-XI-V label."
created: 2026-03-28T00:00:00Z
updated: 2026-03-28T00:03:00Z
---

## Current Focus

hypothesis: All fixes verified
test: Phase diagram generated successfully with correct boundaries
expecting: N/A
next_action: Archive session

## Symptoms

expected: Each phase polygon should correctly share boundaries with neighboring phases

actual:
1. **II overlaps IX** - II should wrap around IX boundary and fill gap between VI/XV and IX. At the IX region, II should stop at the IX boundary
2. **XV completely wrong** - XV should start from low temperature (T=50K?) and extend towards VI-XV boundary. Pressure should touch VIII lower boundary and II's upper boundary
3. **VI overlaps XV** - VI should touch the VI-XV boundary point (~100K, ~1100 MPa) instead of overlapping XV
4. **Ih-XI-V label** - Check if this triple point is within current graph bounds (T=50-500K, P=0.1-100000 MPa). If not, remove the label

reproduction: Render phase diagram and observe

started: N/A (design issue)

## Eliminated

(empty)

## Evidence

- timestamp: initial
  checked: phase_diagram.py lines 251-295 (_build_ice_ii_polygon)
  found: II polygon goes from II-V-VI TP (218.95K, 620 MPa) straight down to (50K, 620 MPa) without respecting IX region
  implication: II polygon ignores IX boundary - should stop at P=400 MPa for T < 140K

- timestamp: initial
  checked: phase_diagram.py lines 541-574 (_build_ice_xv_polygon)
  found: XV polygon uses T=80-130K, P=950-1250 MPa, doesn't extend to lower T
  implication: XV polygon is wrong - should extend down to T=50K per symptoms

- timestamp: initial
  checked: phase_diagram.py lines 356-392 (_build_ice_vi_polygon)
  found: VI polygon goes from II-V-VI TP (218.95, 620 MPa) to (80K, 620 MPa) to (80K, 2100 MPa)
  implication: VI polygon doesn't touch VI-XV transition point (100K, 1100 MPa)

- timestamp: initial
  checked: triple_points.py line 26
  found: Ih_XI_Vapor triple point is at (72.0, 0.0001) MPa
  implication: P=0.0001 MPa is outside graph bounds (P >= 0.1 MPa) - label should be removed

- timestamp: after_fix
  checked: phase_diagram.py after fixes
  found: II polygon now correctly stops at P=400 MPa for T < 140K, then extends to P=950 MPa to meet XV
  implication: II no longer overlaps IX

- timestamp: after_fix
  checked: phase_diagram.py after fixes
  found: XV polygon now at T=50-100K, P=950-2100 MPa
  implication: XV correctly extends to T=50K and touches VIII lower boundary

- timestamp: after_fix
  checked: phase_diagram.py after fixes
  found: VI polygon now stops at T=100K, touching (100K, 1100 MPa) VI-XV transition point
  implication: VI no longer overlaps XV at T < 100K

- timestamp: after_fix
  checked: phase_diagram.py after fixes
  found: Ih_XI_Vapor removed from triple_point_names list
  implication: Ih-XI-V label no longer displayed (point is outside graph bounds)

## Resolution

root_cause: Multiple polygon boundary definitions were incorrect:
1. II polygon extended to P=620 MPa at all temperatures, ignoring IX boundary at P=400 MPa for T < 140K
2. XV polygon was too small (T=80-130K) and didn't extend to T=50K or touch VIII boundary
3. VI polygon extended to T=80K instead of stopping at T=100K where XV begins
4. Ih-XI-V triple point label was displayed despite being outside graph bounds (P=0.0001 MPa < P_min=0.1 MPa)

fix: 
1. II polygon: Modified to stop at P=400 MPa (IX upper boundary) for T < 140K, then extend to P=950 MPa to meet XV
2. XV polygon: Extended to T=50-100K, P=950-2100 MPa (touching II upper and VIII lower boundaries)
3. VI polygon: Cold edge now stops at T=100K, touching VI-XV transition at (100K, 1100 MPa)
4. Ih-XI-V label: Removed from triple_point_names list (point outside graph bounds)

verification: 
- Generated phase diagram successfully with new polygon vertices
- II polygon: stops at P=400 MPa for T < 140K (no longer overlaps IX)
- XV polygon: extends from T=50-100K, P=950-2100 MPa (fills gap between II and VIII)
- VI polygon: stops at T=100K, touches (100K, 1100 MPa) (no longer overlaps XV)
- Ih-XI-V label removed from diagram

NOTE: Phase diagram polygons (visualization) now differ slightly from lookup_phase boundaries (thermodynamic). The diagram shows extended XV region per user requirements, while lookup uses tighter boundaries from triple_points.py.

files_changed:
- quickice/output/phase_diagram.py: Fixed _build_ice_ii_polygon, _build_ice_xv_polygon, _build_ice_vi_polygon, removed Ih_XI_Vapor from triple_point_names
