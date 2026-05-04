---
status: resolved
trigger: "Missing Ice Molecules at Periodic Boundaries in Hydrate Slab Mode"
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T00:00:05Z
---

## Current Focus

hypothesis: Fix verified successfully
test: All tests pass, CH4 gap eliminated, THF gap identified as pre-existing
expecting: Fix is complete and working
next_action: Archive debug session and commit changes

## Symptoms

expected: Ice OW atoms should extend to Z=0 and Z=box_z for continuous periodic images.
actual: Ice OW atoms have gaps at periodic boundaries - CH4 hydrate: 0.135 nm gap at both boundaries, THF hydrate: 0.050 nm gap at both boundaries
errors: No error messages, but structural gaps detected
reproduction: Generate slab mode interface for CH4 or THF hydrate
started: Always present in hydrate slab mode

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-05-04T00:00:00Z
  checked: tile_structure() function in water_filler.py
  found: When filter_molecules=True (default), molecules with atoms outside [0, target_region) are filtered out (lines 526-557)
  implication: Ice molecules at boundaries with atoms spanning PBC get removed, creating gaps

- timestamp: 2026-05-04T00:00:00Z
  checked: slab.py ice tiling calls (lines 268-274, 278-284)
  found: Both bottom and top ice tiling use default filter_molecules=True
  implication: Ice molecules at boundaries are being filtered out

- timestamp: 2026-05-04T00:00:00Z
  checked: slab.py guest tiling calls (lines 424-431, 434-441)
  found: Guest tiling uses filter_molecules=False (fixed in commit 9e45e19)
  implication: Same approach should work for ice tiling

- timestamp: 2026-05-04T00:00:01Z
  checked: Tiling process comparison for CH4 hydrate
  found: filter_molecules=True creates 0.218 nm gap at Z=0; filter_molecules=False reduces gap to -0.005 nm (atoms extend beyond boundaries)
  implication: Fix works perfectly for CH4 hydrate - eliminates gap created by filtering

- timestamp: 2026-05-04T00:00:02Z
  checked: Tiling process comparison for THF hydrate
  found: THF candidate has inherent 0.050 nm gap at Z=0 in original structure; filter_molecules=True makes it 0.050 nm; filter_molecules=False reduces to 0.047 nm
  implication: THF gap is inherent to the sII crystal structure from GenIce2, not caused by filter_molecules issue. Fix works but cannot eliminate pre-existing structural gap.

- timestamp: 2026-05-04T00:00:03Z
  checked: Verification after fix
  found: CH4 hydrate: gap reduced from 0.135 nm to 0.004 nm ✓; THF hydrate: gap remains ~0.050 nm (inherent to candidate)
  implication: Fix successfully addresses filter_molecules issue. THF gap is a separate pre-existing issue in hydrate candidate structure.

## Resolution

root_cause: tile_structure() with filter_molecules=True removes ice molecules that span PBC boundaries, creating artificial gaps at Z=0 and Z=box_z. This is in addition to any inherent gaps in the hydrate candidate structure.
fix: Added filter_molecules=False parameter to ice tiling calls in slab.py (lines 268-276 and 280-288). This preserves ice molecules spanning PBC boundaries, allowing them to be wrapped correctly by the existing wrapping logic in tile_structure().
verification: 
  - CH4 hydrate: Gap reduced from 0.135 nm to 0.004 nm ✓ (fix successful)
  - THF hydrate: Gap remains ~0.050 nm (inherent to sII crystal structure from GenIce2, not caused by filter_molecules)
  - The fix successfully addresses the filter_molecules issue for molecules spanning PBC boundaries.
  - THF hydrate has a pre-existing structural gap that is inherent to the sII crystal and cannot be fixed by this change.
  - All tests pass: test_hydrate_guest_tiling.py (2 passed), test_interface_modes_audit.py (6 passed)
files_changed: [quickice/structure_generation/modes/slab.py]
