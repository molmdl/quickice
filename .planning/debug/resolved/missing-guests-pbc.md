---
status: resolved
trigger: "Fix issue: missing-guests-pbc"
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T00:00:00Z
---

## Current Focus

hypothesis: Guests from GenIce2 are complete molecules already positioned in cage locations. tile_structure() filtering removes guests that span PBC boundaries. We need to skip filtering for guests.
test: Run tests to verify the fix works correctly
expecting: All tests pass, no guests missing at PBC boundaries
next_action: Run tests and verify with hydrate interface generation

## Symptoms

expected: |
  All guest molecules present at PBC boundaries (none missing)
  Continuous periodic images

actual: |
  Guests missing at PBC boundary in hydrate
  Filtering logic removes molecules with atoms outside box

reproduction: |
  Hydrate interface files in tmp/ch4, tmp/thf have missing guests at boundaries
  
  The filtering code in water_filler.py (lines 534-546):
  ```python
  # Check if ALL atoms of this molecule are inside target region [0, target_region)
  all_inside_x = np.all((mol_atoms[:, 0] >= 0) & (mol_atoms[:, 0] < lx - tol))
  all_inside_y = np.all((mol_atoms[:, 1] >= 0) & (mol_atoms[:, 1] < ly - tol))
  all_inside_z = np.all((mol_atoms[:, 2] >= 0) & (mol_atoms[:, 2] < lz - tol))
  
  if all_inside_x and all_inside_y and all_inside_z:
      keep_molecules.append(mol_idx)
  ```
  
  This removes molecules that span PBC boundaries, causing missing guests.

timeline: |
  - Working ice version (892908e) also had filtering
  - But ice had no guest molecules to lose
  - Hydrate has guests that span PBC boundaries and get filtered out

## Eliminated

## Evidence

- timestamp: 2026-05-04T00:00:00Z
  checked: water_filler.py lines 534-546
  found: Filtering logic checks if ALL atoms of a molecule are inside [0, target_region). Molecules with any atom outside are removed.
  implication: This filtering removes guest molecules that span PBC boundaries

- timestamp: 2026-05-04T00:00:00Z
  checked: hydrate_generator.py lines 92-96
  found: GenIce2 outputs complete molecules, and wrapping is explicitly disabled to avoid splitting molecules. Comment says "Do NOT wrap positions. GenIce2 outputs complete molecules"
  implication: Guests from GenIce2 are already complete molecules positioned in cages

- timestamp: 2026-05-04T00:00:00Z
  checked: slab.py lines 422-437
  found: Guest positions are tiled using tile_structure() with filtering enabled (default)
  implication: Guests are being filtered incorrectly at PBC boundaries

- timestamp: 2026-05-04T00:00:00Z
  checked: water_filler.py, slab.py, pocket.py
  found: Added filter_molecules parameter to tile_structure() (default=True). Updated all guest tiling calls to use filter_molecules=False
  implication: Guest molecules will no longer be filtered at PBC boundaries

## Resolution

root_cause: tile_structure() filtered out molecules with atoms outside [0, target_region), which removed guest molecules at PBC boundaries. Guests from GenIce2 are complete molecules already positioned in cage locations and should not be filtered.
fix: Added filter_molecules parameter to tile_structure() (default=True). Updated all guest tiling calls in slab.py and pocket.py to use filter_molecules=False. This preserves all guest molecules while maintaining the filtering behavior for water molecules.
verification: All hydrate interface tests pass (test_hydrate_guest_tiling.py, test_interface_modes_audit.py). Guests are present at both boundaries in generated structures.
files_changed: [quickice/structure_generation/water_filler.py, quickice/structure_generation/modes/slab.py, quickice/structure_generation/modes/pocket.py]
