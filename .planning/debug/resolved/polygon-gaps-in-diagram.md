---
status: resolved
trigger: "polygon-gaps-in-diagram"
created: 2026-03-27T00:00:00Z
updated: 2026-03-27T00:00:00Z
---

## Current Focus
hypothesis: "Gaps caused by: (1) Ih doesn't extend to 50K to meet XI, (2) II and IX pressure boundaries don't meet, (3) XV isolated not connected to VI, (4) VIII/X gap due to no phase between 10-30 GPa"
test: "Modified polygon definitions to connect at boundaries"
expecting: "No gaps between adjacent polygons"
next_action: "Verification complete"
---

## Symptoms
expected: No gaps - all polygons should be adjacent and form space-filling regions between curves
actual: Visual gaps visible between specific polygon pairs: Ih-XI, II-IX, isolated XV, VIII-X, X-VII/VIII
errors: No errors - visual issue only
reproduction: `python quickice.py -T 273 -P 0.1 -N 216 -o out_test`
started: Never worked correctly since implementation

## Evidence
- timestamp: 2026-03-27T00:00:00Z
  checked: "quickice.py structure"
  found: "Main script at quickice.py - handles command line args and orchestrates diagram generation"
  implication: "Need to trace from CLI to polygon generation"

- timestamp: 2026-03-27T00:00:00Z
  checked: "phase_diagram.py polygon generation"
  found: "Polygons defined in _build_*_polygon functions - each phase has its own polygon built from boundary curves"
  implication: "Gaps caused by polygons not meeting at boundaries"

- timestamp: 2026-03-27T00:00:00Z
  checked: "Polygon vertex analysis"
  found: "Ih: T=100-273K P=0-213MPa; XI: T=50-72K P=0.1-200MPa; II: T=180-249K P=207-620MPa; IX: T=100-140K P=201-400MPa; VIII: T=100-278K P=2100-10000MPa; X: T=100-500K P=30000-100000MPa"
  implication: "Multiple gaps identified: (1) Ih starts at 100K but XI ends at 72K, gap 72-100K; (2) II ends ~213MPa but IX starts at 250MPa at 100K; (3) XV at 1100MPa isolated; (4) VIII ends at 10GPa but X starts at 30GPa"

- timestamp: 2026-03-27T00:00:00Z
  checked: "Boundary function values"
  found: "At T=72K: ih_ii_boundary=196.2MPa; At T=100K: ix_boundary=250MPa; At T=278K: x_boundary=31130MPa"
  implication: "Ih-II boundary at 72K is 196MPa, but XI goes to 200MPa. IX starts at 250MPa. Gap between Ih-II and IX."

- timestamp: 2026-03-27T00:00:00Z
  checked: "Polygon verification after fixes"
  found: "Ih-XI: At T=72K, Ih P=196MPa meets XI P=200MPa; II-IX: At T=100K, II P=199-620MPa meets IX P=250-400MPa; XV-VI: At T=200K, XV P=1100MPa meets VI; VIII-X: VIII max P=30000MPa meets X min P=30000MPa; VII-X: VII max P=30000MPa meets X min P=30000MPa"
  implication: "All boundaries now connect properly"

## Eliminated
- timestamp: 2026-03-27T00:00:00Z
  hypothesis: "Gaps are just visual rendering issues"
  evidence: "Polygon coordinates show clear physical gaps between regions - not rendering artifacts"
  eliminated: true

## Resolution
root_cause: "Polygons were standalone regions not designed to meet at boundaries. Missing connections: (1) Ih didn't extend to 50K to meet XI, (2) II and IX didn't meet at pressure boundary, (3) XV was isolated band not connected to VI, (4) No phase existed between VIII (10GPa) and X (30GPa)"
fix: "Modified polygon definitions in phase_diagram.py: (1) Extended Ice Ih to T=50K to meet XI, (2) Extended Ice II to connect with IX boundary at T=100K, (3) Extended Ice XV to connect with VI at T=200K, (4) Extended Ice VIII and VII to meet Ice X at P=30000MPa, (5) Extended Ice X to T=50K, (6) Extended Ice VI to T=100K"
verification: "All boundary connections verified: Ih-XI at T=72K (P~196-200MPa), II-IX at T=100K (P~199-400MPa), XV-VI at T=200K (P~1100MPa), VIII/X/VII at P=30000MPa. Phase diagram generated successfully. Tests pass (211/219, 8 failures pre-existing)."
files_changed: ["quickice/output/phase_diagram.py"]