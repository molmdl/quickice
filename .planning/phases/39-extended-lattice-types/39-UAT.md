---
status: testing
phase: 39-extended-lattice-types
source: [39-01-SUMMARY.md, 39-02-SUMMARY.md, 39-03-SUMMARY.md, 39-04-SUMMARY.md, 39-05-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T12:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: Select new lattice types in Hydrate tab
expected: |
  Open the QuickIce GUI, go to the Hydrate tab. The lattice type dropdown should include all
  7 new lattice types: C0 (c0te), C1 (c1te), C2 (c2te), Ih (ice1hte), sT' (sTprime), Ice XVI (16),
  and Ice XVII (17), in addition to the existing sI, sII, sH types. Selecting each new type should
  not crash and should update the cage info display.
awaiting: user response

## Tests

### 1. Select new lattice types in Hydrate tab
expected: Open the QuickIce GUI, go to the Hydrate tab. The lattice type dropdown should include all 7 new lattice types: C0 (c0te), C1 (c1te), C2 (c2te), Ih (ice1hte), sT' (sTprime), Ice XVI (16), and Ice XVII (17), in addition to the existing sI, sII, sH types. Selecting each new type should not crash and should update the cage info display.
result: [pending]

### 2. Triclinic filled ices blocked for interface generation with clear error
expected: In the GUI, generate a hydrate with a triclinic filled ice (C0/c0te or C1/c1te), then move to the Interface tab and attempt to generate an interface structure. A clear error message should be displayed (same pattern as Ice II blocking), preventing the interface generation from proceeding.
result: [pending]

### 3. Filled ice lattices place guests via parse_guest (not spot_guests)
expected: Generate a hydrate structure with a filled ice lattice (C0, C1, C2, or Ih) with a guest (e.g. CH4). The structure should be generated successfully with guests placed in the correct cage positions via the parse_guest code path (not spot_guests, which crashes with IndexError). Verify the generated structure has the expected number of guest molecules.
result: [pending]

### 4. sT' and Ice XVII generate water-only with guest UI disabled
expected: In the GUI Hydrate tab, select sT' (sTprime) or Ice XVII (17) as the lattice type. The guest controls (combo boxes and occupancy spinners) should be disabled since these are water-only lattices. Generate the structure and verify it contains only water molecules (no guest atoms).
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0

## Gaps

[none yet]
