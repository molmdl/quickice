---
status: resolved
trigger: "Debug hydrate interface generation error - PBC overlap detected after commits ea835d0"
created: 2026-05-01T09:30:00Z
updated: 2026-05-01T10:15:00Z
---

## Current Focus

hypothesis: CONFIRMED - The new tile_structure() allows atoms outside [0, target_region). When slab.py shifts top ice positions, atoms that exceed adjusted_ice_thickness end up exceeding adjusted_box_z. The PBC check raises an error instead of wrapping.
test: Apply wrapping logic to top_ice_positions after shifting, similar to what's done for guest molecules (lines 505-521)
expecting: After wrapping, all atoms will be within [0, adjusted_box_z), and the PBC overlap error will be resolved
next_action: Verify the fix works correctly and update debug file

## Symptoms

expected: Hydrate interface generation should work without PBC overlap errors, similar to how ice interface works.
actual: Hydrate interface generation fails with PBC overlap error. The error shows top ice atoms have Z >= box_z.
errors: "[slab] PBC overlap detected: 0 top ice atoms have Z < 0, 100 atoms have Z >= box_z (10.20 nm)"
reproduction: Try to generate hydrate interface using slab mode with box_z=10.20 nm, ice_thickness=3.60 nm, water_thickness=3.00 nm.
timeline: Started after commit ea835d0 which modified water_filler.py. Ice interface still works with old water_filler.py.

## Eliminated

## Evidence

- timestamp: 2026-05-01T09:30:00Z
  checked: Git commit history
  found: Commit ea835d0 modified tile_structure() in water_filler.py to wrap/clamp molecules at PBC boundaries
  implication: This change was meant to preserve hydrate guest molecules, but may have broken hydrate interface generation

- timestamp: 2026-05-01T09:30:00Z
  checked: Git diff for ea835d0
  found: tile_structure() now wraps molecules based on COM, then clamps individual atoms into [0, target_region)
  implication: The wrapping/clamping logic may be incorrect for the hydrate interface case where box dimensions are set up differently

- timestamp: 2026-05-01T09:35:00Z
  checked: Commit 96cb6a7 (after ea835d0)
  found: Removed Step 2 atom clamping from tile_structure(). Now only wraps based on COM and accepts molecules with atoms outside [0, target_region)
  implication: Atoms can now be outside the target region, and downstream code should handle wrapping. But slab.py's PBC check doesn't handle this.

- timestamp: 2026-05-01T09:35:00Z
  checked: Commit d87978d (the ice fix from April 12)
  found: Added round_to_periodicity() to adjust box dimensions and ice thickness to align with ice unit cell dimensions. This worked because old tile_structure() filtered out boundary molecules.
  implication: The ice fix relied on tile_structure() filtering, which ensured all atoms were strictly within [0, target_region). The new tile_structure() doesn't filter, so atoms can be outside.

- timestamp: 2026-05-01T09:45:00Z
  checked: Reproduced error with real hydrate structure
  found: Hydrate structure has atoms with negative coordinates (Z range: [-0.076, 1.153]). After tiling, 100 atoms exceed adjusted_ice_thickness (3.601 nm) by ~5 pm. After shifting, they exceed adjusted_box_z (10.20 nm).
  implication: The PBC check in slab.py raises an error because atoms exceed the boundary. The fix should wrap atoms instead of raising an error.

- timestamp: 2026-05-01T09:50:00Z
  checked: Guest molecule wrapping in slab.py (lines 505-521)
  found: Guest molecules are already wrapped after shifting using COM-based logic. Ice water framework atoms are NOT wrapped.
  implication: We need to add the same wrapping logic for ice water framework atoms after shifting, before the PBC check.

- timestamp: 2026-05-01T10:00:00Z
  checked: Fixed slab.py by adding wrapping logic for top_ice_positions
  found: Replaced error-raising PBC check with molecular wrapping based on COM. After wrapping, molecules whose COM is outside [0, box_z) get shifted back into the box.
  implication: This preserves molecular integrity while ensuring atoms are within reasonable bounds. Individual atoms can still be outside [0, box_z) for molecules spanning PBC, which is correct.

- timestamp: 2026-05-01T10:10:00Z
  checked: Verified fix with tests
  found: All existing tests pass (test_hydrate_guest_tiling.py, test_structure_generation.py). Molecular integrity is preserved. GRO output wrapping works correctly.
  implication: The fix is correct and doesn't break any existing functionality.

## Resolution

root_cause: After commits ea835d0 and 96cb6a7, tile_structure() allows atoms to be outside [0, target_region) to preserve molecules spanning PBC boundaries. However, slab.py's PBC check was raising an error when top ice atoms exceeded box_z after shifting, instead of wrapping them. This broke hydrate interface generation because hydrate structures have molecules with negative coordinates that get tiled and shifted.

fix: Modified slab.py to wrap top ice molecules based on COM after shifting (lines 340-361), similar to how guest molecules are wrapped. This replaces the error-raising PBC check with molecular wrapping that preserves molecular integrity. Individual atoms can still be outside [0, box_z) for molecules spanning PBC boundaries, which is correct behavior - the final wrapping is done in overlap_resolver.py and gromacs_writer.py when needed.

verification: 
1. Reproduced the error with real hydrate structure
2. Applied fix in slab.py
3. Verified hydrate interface generation works without errors
4. Verified all existing tests pass (59 tests in test_structure_generation.py, 2 tests in test_hydrate_guest_tiling.py)
5. Verified molecular integrity is preserved
6. Verified GRO output wrapping works correctly (all atoms within [0, boxsize) after wrapping)

files_changed: 
- quickice/structure_generation/modes/slab.py: Lines 340-361, replaced error-raising PBC check with molecular wrapping logic
