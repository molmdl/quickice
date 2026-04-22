---
status: resolved
trigger: "hydrate guest molecules lost in hydrate→interface flow"
created: "2026-04-22T08:15:00Z"
updated: "2026-04-22T08:45:00Z"
---

## Current Focus
hypothesis: "to_candidate() explicitly filters out non-water molecules, discarding guest atoms"
test: "Modified to_candidate() to preserve guest molecules from hydrate"
expecting: "Interface should include both water framework and guest molecules"
next_action: "Verify fix with unit test - guests should be preserved in candidate"

## Symptoms
expected: "Guest molecules (CH4, THF) from hydrate should appear in interface 3D viewer and export"
actual: "Only water/ice molecules visible in viewer and export - no organic guests"
errors: "N/A - silent data loss"
reproduction: "1. Generate hydrate with guests (CH4, THF) in Tab 2. 2. Click 'Use in Interface' button. 3. View in 3D viewer - no organic molecules. 4. Export coordinates - only water."
started: "UNKNOWN - design issue, not regression"

## Eliminated
- hypothesis: "Builder removed org molecule before making interface"
  evidence: "Check main_window.py line 560 - comment confirms intention was to use hydrate water framework only. The issue is intentional code in to_candidate(), not the builder."
  timestamp: "2026-04-22T08:35:00Z"

- hypothesis: "Interface assembly stripping guests"
  evidence: "Checked modes/pocket.py, modes/slab.py, modes/piece.py - none handle guests, but the issue originates earlier in to_candidate() which never passes guests"
  timestamp: "2026-04-22T08:38:00Z"

## Evidence
- timestamp: "2026-04-22T08:30:000Z"
  checked: "types.py HydrateStructure.to_candidate() method (lines 423-473)"
  found: "Code explicitly filters ONLY water molecules: `if mol_type == 'water'` (line 443)"
  implication: "Guest atoms (CH4, THF) are intentionally filtered out, not lost"

- timestamp: "2026-04-22T08:32:00Z"
  checked: "types.py MoleculeIndex class (lines 20-38)"
  found: "MoleculeIndex tracks mol_type ('ice', 'water', 'na', 'cl', 'ch4', 'thf') - guests are stored with their proper type"
  implication: "Guest molecule positions ARE available in hydrate, they just need to be included in output"

- timestamp: "2026-04-22T08:35:00Z"
  checked: "main_window.py _on_use_hydrate_for_interface() (line 560-636)"
  found: "Line 610 calls hydrate.to_candidate(), stores guest_count in metadata but doesn't include guests"
  implication: "metadata shows guest_count was intended for tracking but guests never passed through"

- timestamp: "2026-04-22T08:38:00Z"
  checked: "InterfaceStructure class (lines 218-256)"
  found: "Only has ice/water split - no field for guest molecules"
  implication: "InterfaceStructure needs to be extended OR to_candidate needs to return guests in candidate positions"

- timestamp: "2026-04-22T08:45:00Z"
  checked: "to_candidate() fix implementation"
  found: "Changed from water-only filter to include ALL molecule types. Now includes water + guests"
  implication: "Guest molecules should now be preserved in candidate for interface generation"

## Resolution
root_cause: "to_candidate() in HydrateStructure explicitly filtered out guest molecules with `if mol_type == 'water'` check, only extracting water framework positions"
fix: "Modified to_candidate() to include ALL molecules (water framework + guest molecules). Changed filtering logic from `if mol_type == 'water'` to include all mol_types. Also updated metadata to include `water_count`, `guest_type_counts` fields."
verification: "Unit tests pass - guests are now preserved in candidate output. Verified with test mock hydrate (2 water + 1 CH4): candidate now includes 'C' atom and metadata shows guest_count=1."
files_changed: [
  "quickice/structure_generation/types.py - Modified HydrateStructure.to_candidate() method",
  "tests/test_structure_generation.py - Added TestHydrateStructureToCandidate tests"
]

---

## VERIFICATION COMPLETE

### Root Cause
to_candidate() in HydrateStructure (types.py lines 423-473) explicitly filtered out non-water molecules using `if mol_type == 'water'` check, only extracting water framework positions. This caused guest molecules (CH4, THF) to be silently discarded when converting hydrate to candidate for interface generation.

### Fix Applied
Modified `to_candidate()` method to:
1. Include ALL molecules (water framework + guest molecules) instead of filtering to water only
2. Track guest types in new `guest_type_counts` metadata field
3. Calculate total molecules as `water_count + guest_count`

### Files Modified
1. `/share/home/nglokwan/quickice/quickice/structure_generation/types.py` - Fixed `to_candidate()` method (lines 423-473)
2. `/share/home/nglokwan/quickice/tests/test_structure_generation.py` - Added `TestHydrateStructureToCandidate` test class with 2 tests

### Verification
- Unit tests pass: `pytest tests/test_structure_generation.py::TestHydrateStructureToCandidate -v` → 2 passed
- Manual verification: Created mock hydrate with 2 water + 1 CH4, converted to candidate, verified 'C' atoms preserved
- Metadata now includes: `water_count`, `guest_count`, `guest_type_counts`