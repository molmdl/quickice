---
status: resolved
trigger: "some updates after tag v4.0fix broke the ion insertion code, 0 ions insert, likely issues in overlap detection. both local main and origin/main have issue, tag v4.0fix did not have this issue"
created: 2026-05-02T00:00:00Z
updated: 2026-05-02T00:15:00Z
---

## Current Focus

hypothesis: Root cause confirmed - overlap checking incorrectly includes ALL water molecules instead of only ice/guest, causing all ion placements to be rejected
test: Implement fix to revert overlap check to only ice and guest molecules (not water)
expecting: Ions will be placed successfully after fix
next_action: Modify ion_inserter.py lines 272-300 to check only ice and guest molecules

## Symptoms

expected: Ion insertion tab calculates number of pairs by concentration and inserts up to that many NaCl into liquid phase
actual: 0 ions are inserted (none at all)
errors: No errors - code runs silently but produces no ions
reproduction: Both hydrate/ice -> interface -> ions workflow in GUI
started: Worked in tag v4.0fix, broken in current main (both local and origin/main)
timeline: Commits between v4.0fix and HEAD available for bisect

## Eliminated

- hypothesis: MW virtual site atoms causing false overlaps
  evidence: Commit 33e0219 already filters MW atoms, but issue persists
  timestamp: 2026-05-02T00:05:00Z

## Evidence

- timestamp: 2026-05-02T00:00:00Z
  checked: Git commits between v4.0fix and HEAD
  found: 19 commits between v4.0fix and HEAD, including several overlap/fix related commits
  implication: Bug introduced in one of these commits, most likely overlap-related ones

- timestamp: 2026-05-02T00:01:00Z
  checked: Commit history of ion_inserter.py
  found: Commit 6689d18 "fix: prevent ion overlap with hydrate water framework" changed logic from checking only ice/guest to checking ALL non-replaced molecules
  implication: This change includes liquid water molecules in overlap check

- timestamp: 2026-05-02T00:02:00Z
  checked: Git diff of commit 6689d18
  found: Changed from `if mol.mol_type in ("ice", "guest")` to `if mol.start_idx not in replaced_starts`
  implication: Now checks distance to all water molecules that won't be replaced

- timestamp: 2026-05-02T00:03:00Z
  checked: Water structure physics
  found: Liquid water O-O distances are ~0.28-0.3 nm, MIN_SEPARATION constant is 0.3 nm
  implication: Overlap check will reject ALL ion placements because water molecules are too close to each other

- timestamp: 2026-05-02T00:04:00Z
  checked: Commit 33e0219 attempted fix
  found: Added MW atom filtering but still checks all water O, H1, H2 atoms
  implication: Fix incomplete - still broken for same reason

- timestamp: 2026-05-02T00:06:00Z
  checked: Hydrate->interface conversion flow in piece.py
  found: Hydrate water framework is labeled as "ice" in InterfaceStructure (ice_nmolecules), not "water". Water molecules are only the liquid water box.
  implication: The fix from commit 6689d18 was conceptually wrong - hydrate framework is already ice-labeled, so checking water molecules is incorrect

- timestamp: 2026-05-02T00:07:00Z
  checked: molecule_index building in ion_inserter.py
  found: _build_molecule_index_from_structure() correctly labels ice molecules as mol_type="ice", water as "water", guests as "guest"
  implication: The overlap check should only check mol_type in ("ice", "guest"), not all non-replaced molecules

- timestamp: 2026-05-02T00:08:00Z
  checked: Realistic liquid water O-O distances
  found: Mean distance 0.176 nm, 98% of waters have neighbor within MIN_SEPARATION (0.3 nm)
  implication: When checking ALL water molecules, 100% of ion placements will be rejected

## Resolution

root_cause: Commit 6689d18 changed ion overlap checking from `if mol.mol_type in ("ice", "guest")` to `if mol.start_idx not in replaced_starts`, which incorrectly included ALL water molecules (not just ice/guest) in the overlap check. Since liquid water molecules have O-O distances ~0.28-0.3 nm and MIN_SEPARATION is 0.3 nm, all ion placements were rejected as "overlapping".

fix: Reverted overlap checking logic to only check ice and guest molecules, not water molecules. Added detailed comments explaining why water molecules must NOT be checked (they're being replaced, and checking them would reject all placements). Kept MW atom filtering improvement from commit 33e0219.

verification: 
  - test_ion_hydrate_fix.py: PASSED
  - Manual verification: PASSED (14 ion pairs inserted in realistic water density structure)
  - All structure generation tests: PASSED (60/60)
  - Fix matches v4.0fix behavior while retaining MW atom filtering improvement
files_changed: [quickice/structure_generation/ion_inserter.py]
