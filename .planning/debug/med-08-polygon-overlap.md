---
status: investigating
trigger: "MED-08 phase-diagram-polygon-overlap - Phase diagram polygon overlap potential at boundaries"
created: 2026-04-09T00:00:00
updated: 2026-04-09T00:00:00
---

## Current Focus

hypothesis: **CONFIRMED** - Polygon boundary vertices are sampled independently with different numbers of points, causing geometric overlaps at boundaries where x_boundary and vii_viii_boundary diverge (T > 100K)
test: Use shapely to check for actual geometric overlap between polygon pairs
expecting: Find small polygon overlaps (~1000 area units) where boundary sampling misaligns
next_action: Implement fix by using shared boundary sampling or explicit boundary alignment

## Symptoms

expected: Phase regions should not overlap when rendering phase diagram
actual: Multiple polygons for different phases could overlap at boundaries
errors: Visual artifacts at triple points and phase boundaries
reproduction: Visualize phase diagram, check for overlapping colors at triple points
timeline: Always had hardcoded coordinates without overlap checking

## Eliminated

<!-- Hypotheses that were disproven -->

## Evidence

- timestamp: initial
  checked: phase_diagram.py structure
  found: Phases rendered in layered order (back to front) with alpha=0.6 transparency. 12 phase polygons built from curve functions.
  implication: Overlapping polygons with transparency will create visual color blending artifacts

- timestamp: investigation
  checked: Triple points and boundary functions
  found: Triple points defined with float precision. Boundary functions use linear interpolation. Polygons carefully constructed to share boundaries (e.g., Ice IX upper P=400 matches Ice II lower boundary, Ice XV at T=100K matches Ice VI vertical edge).
  implication: Polygons are designed to NOT overlap geometrically but SHARE boundaries

- timestamp: investigation
  checked: Polygon construction for Ice VI and Ice XV
  found: Ice VI has vertical edge at T=100K, P=1100-2100. Ice XV is T=50-100K, P=950-2100. Both have boundary at T=100K, creating shared edge.
  implication: At T=100K, P=1100-2100, both polygons have boundary points. With alpha=0.6, the shared edge will have double-blended colors.

- timestamp: root_cause_analysis
  checked: Shapely polygon intersection analysis
  found: OVERLAP: ice_x x ice_viii = area 1006.52, OVERLAP: ice_x x ice_vii = area 1850.95. Intersection contains Polygon component at T=95-101K where x_boundary and vii_viii_boundary diverge. Point testing shows regions where BOTH polygons claim the same area.
  implication: Geometric overlap exists, not just shared boundaries

- timestamp: root_cause_confirmed
  checked: Vertex temperature alignment at boundaries
  found: Ice VII vertex at T=100.00, Ice VIII vertices at T=97.37 and T=100.00, Ice X vertex at T=95.92. All on same boundary line but different temperatures. Polygons use independent sampling (Ice X: 50 points, Ice VIII: 20 points, Ice VII: 40 points) with different temperature ranges.
  implication: **ROOT CAUSE: Independent polygon sampling causes vertex misalignment. At T > 100K where x_boundary(T) ≠ vii_viii_boundary(T), the interpolated edges create gaps/overlaps.**

## Resolution

root_cause: Polygons use independent sampling for shared boundary curves (Ice X: 50 points, Ice VIII: 20 points, Ice VII: 40 points) with different temperature ranges. At T > 100K where x_boundary(T) ≠ vii_viii_boundary(T), the misaligned interpolated edges create geometric overlaps of ~1000-2000 area units.
fix: Implemented shared boundary sampling by: (1) Added `_get_shared_boundary_vertices()` function with caching to ensure all polygons sharing a boundary use identical vertex arrays, (2) Explicitly include triple points (VII_VIII_X at T=100K) as vertices in all relevant boundaries, (3) Updated `_build_ice_vii_polygon()`, `_build_ice_viii_polygon()`, and `_build_ice_x_polygon()` to use shared boundary vertices.
verification: Verified with shapely intersection test - 0 geometric overlaps detected (down from 2 overlaps with areas ~1006 and ~1850). Boundary intersection analysis confirms shared edges (MultiLineString) and shared vertices (MultiPoint). All 79 existing tests pass.
files_changed: []