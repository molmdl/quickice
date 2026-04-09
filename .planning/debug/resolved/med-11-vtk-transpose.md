---
status: resolved
trigger: "MED-11 cell-matrix-transposition"
created: "2026-04-09T20:50:00.000Z"
updated: "2026-04-09T20:55:00.000Z"
---

## Current Focus
hypothesis: The transpose in vtk_utils.py is correct but needs more comprehensive documentation to prevent confusion
test: Add detailed documentation explaining conventions
expecting: Clear documentation that prevents future confusion
next_action: Archive resolved session

## Symptoms
expected: Clear documentation of cell matrix orientation assumptions
actual: Transpose is necessary but not documented, requiring careful interpretation
errors: No error, but could confuse future developers
reproduction: Read VTK cell matrix code, try to understand why transpose is needed
started: Always used transpose, not documented

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: "2026-04-09T20:50"
  checked: "vtk_utils.py lines 100-108"
  found: "Transpose exists with minimal comment: 'VTK expects column vectors, we have row vectors'"
  implication: "Comment is accurate but terse. Could benefit from more context."

- timestamp: "2026-04-09T20:50"
  checked: "Resolved debug session unit-cell-mismatch.md"
  found: "This was previously debugged and fixed. Root cause was row vs column vector convention."
  implication: "Transpose is CORRECT. Just needs better documentation."

- timestamp: "2026-04-09T20:50"
  checked: "types.py Candidate dataclass"
  found: "cell is documented as '(3, 3) cell vectors in nm' but does not specify row vs column convention"
  implication: "Cell matrix convention is not documented at type definition level"

- timestamp: "2026-04-09T20:50"
  checked: "generator.py _parse_gro method"
  found: "Cell is stored with each ROW being a lattice vector"
  implication: "QuickIce convention is row vectors. This should be documented."

- timestamp: "2026-04-09T20:55"
  checked: "Added comprehensive documentation to vtk_utils.py"
  found: "Added detailed comment block explaining VTK column vectors vs QuickIce row vectors"
  implication: "Future developers will understand why transpose is needed"

- timestamp: "2026-04-09T20:55"
  checked: "Updated types.py Candidate.cell docstring"
  found: "Added explicit documentation of row-vector convention with matrix layout"
  implication: "Type definition now documents convention, visible in IDEs"

## Resolution
root_cause: The transpose was correct but documentation was insufficient. The cell matrix orientation conventions (QuickIce uses row vectors, VTK uses column vectors) were not documented at the type definition level, and the inline comment in vtk_utils.py was too terse.
fix: Added comprehensive documentation:
  1. vtk_utils.py: Detailed comment block explaining VTK column vectors vs QuickIce row vectors, the transpose relationship, and when it matters (non-orthogonal cells)
  2. types.py Candidate.cell: Added explicit documentation of row-vector convention with matrix layout and note about VTK transpose
  3. types.py InterfaceStructure.cell: Added reference to Candidate.cell for consistency
verification: Python imports verified successfully. Documentation strings confirmed to contain key terms ('ROW vectors', 'transpose').
files_changed: ["quickice/gui/vtk_utils.py", "quickice/structure_generation/types.py"]
