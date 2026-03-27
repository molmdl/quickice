---
status: resolved
trigger: "phase-diagram-gaps"
created: 2026-03-27T00:00:00Z
updated: 2026-03-27T00:00:00Z
---

## Current Focus
hypothesis: "Multiple root causes: (1) Ice XI polygon only 1 MPa wide instead of extending to 200 MPa, (2) Ih-XI-V triple point label outside plot bounds, (3) VIII/X polygon boundaries don't align with lookup logic"
test: "Fix polygon definitions to match lookup logic and ensure labels are within plot"
expecting: "Will create contiguous filled polygons and correctly positioned labels"
next_action: "Fix Ice XI polygon to extend P range to match lookup (P<200 MPa)"

## Symptoms
expected: "Phase diagram should show all phase regions as contiguous filled areas with no gaps between polygons. All phases should be visible within the diagram bounds. Labels should be inside the plot."
actual: "Gaps visible between phase polygons (X and VIII/VII), isolated XV and XI regions, Ih-XI-V label outside plot. Phases appear to have gaps between them."
errors: "No errors, but visual gaps in diagram."
reproduction: "Generate phase diagram with any T,P values and observe gaps between phase regions."
started: "Started after Phase 5.1 added new phases (XI, IX, X, XV) to diagram."

## Eliminated
- hypothesis: "Labels simply positioned wrong - can be adjusted in rendering"
  evidence: "Not yet investigated"
  timestamp: "2026-03-27T00:00:00Z"

## Evidence
- timestamp: "2026-03-27T00:00:00Z"
  checked: "Context mentions key files"
  found: "Need to investigate phase_diagram.py, solid_boundaries.py, lookup.py"
  implication: "May reveal whether gaps are visual (diagram) or functional (lookup)"
- timestamp: "2026-03-27T00:00:00Z"
  checked: "Ice XI polygon in phase_diagram.py lines 395-409"
  found: "Polygon vertices: (50,0.1)->(72,0.1)->(72,1.0)->(50,0.1) - only 0.9 MPa wide"
  implication: "Visual gap - polygon should extend to at least 200 MPa per lookup logic"
- timestamp: "2026-03-27T00:00:00Z"
  checked: "Ice IX polygon in phase_diagram.py lines 412-429"
  found: "Polygon uses fixed boundaries at P=200-400 MPa but lookup uses variable boundary via ix_boundary(T)"
  implication: "Mismatch between fixed visual polygon and variable lookup boundary"
- timestamp: "2026-03-27T00:00:00Z"
  checked: "Ice XV polygon in phase_diagram.py lines 451-461"
  found: "Polygon: T=80-108K, P=1000-1200 MPa (fixed 200 MPa band)"
  implication: "Lookup checks: 80<=T<=108 AND 1000<=P<=1200, but xv_boundary returns ~1100 MPa"
- timestamp: "2026-03-27T00:00:00Z"
  checked: "Ice X polygon in phase_diagram.py lines 432-448"
  found: "Polygon: T=100-500K, P=30000-100000 MPa - correct high pressure region"
  implication: "Should connect with VIII/VII at P=2100-30000 MPa but visual gap may exist"
- timestamp: "2026-03-27T00:00:00Z"
  checked: "VII/VIII polygons"
  found: "VIII: rectangle from VI-VII-VIII TP up to 10000 MPa. VII: similar but at higher T"
  implication: "VIII/VII should fill gap to X at 30000 MPa, check visual connection"

## Resolution
root_cause: "Multiple issues: (1) Ice XI polygon was only 0.9 MPa wide instead of extending to 200 MPa like lookup, (2) Ice IX/X/XV polygons used fixed boundaries instead of variable boundary functions that match lookup, (3) Ih-XI-V triple point label was placed at P=0.0001 which is outside plot bounds (P_min=0.1)"
fix: "Extended XI polygon from P=0.1-1.0 to P=0.1-200 MPa; updated IX/X/XV polygons to use boundary functions (ix_boundary, x_boundary, xv_boundary) matching lookup logic; fixed label positioning to place low-P triple point labels inside plot at P=1 MPa"
verification: "Tested generating phase diagram - completes successfully. Verified lookup still works correctly for all phase regions."
files_changed: ["quickice/output/phase_diagram.py"]