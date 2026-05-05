---
status: resolved
trigger: "Hydrogen atoms of solute THF are messed up - positions or arrangement incorrect"
created: 2026-05-05T00:00:00Z
updated: 2026-05-05T00:00:02Z
---

## Current Focus
hypothesis: CONFIRMED - _generate_thf_coordinates() generates completely wrong ring and H geometry
test: Compared generated coordinates with actual hydrate THF and ITP values
expecting: Found ring bonds 0.21 nm (should be 0.14-0.15), H-C-H angles 122° (should be 107-108°)
next_action: Rewrite _generate_thf_coordinates() with proper ring building and tetrahedral H placement

## Eliminated

## Evidence
- timestamp: 2026-05-05T00:00:00Z
  checked: thf.itp bonds section
  found: THF ring connectivity is O(1)-CB(4)-CA(2)-CA(3)-CB(5)-O(1), NOT O-C-C-C-C in simple sequence
  implication: Ring generation in _generate_thf_coordinates() doesn't match actual THF connectivity

- timestamp: 2026-05-05T00:00:00Z
  checked: _generate_thf_coordinates() lines 170-181
  found: H atoms placed with angles ±120° from carbon ring position plus z-offset of ±0.3 nm
  implication: This is arbitrary geometry, not proper tetrahedral arrangement. H positions don't match ITP bond angles.

- timestamp: 2026-05-05T00:00:00Z
  checked: thf.itp angles section
  found: H-C-H angle is 107.22° for CA carbons and 108.13° for CB carbons (not 240° implied by ±120° placement)
  implication: Current code creates completely wrong H-C-H angles

- timestamp: 2026-05-05T00:00:00Z
  checked: Hydrate THF coordinates vs generated coordinates
  found: Current code produces O-C bonds 0.16-0.22 nm (should be 0.143 nm), C-C bonds 0.21 nm (should be 0.155 nm), H-C-H angles 122° (should be 107-108°)
  implication: Ring geometry is fundamentally wrong - not just H positions but entire ring structure

- timestamp: 2026-05-05T00:00:00Z
  checked: Root cause of ring geometry error
  found: Code places O at (r_oc, 0, 0) but then places carbons around ring_radius calculated from r_cc, creating inconsistent geometry
  implication: Ring building logic doesn't match actual THF connectivity O-CB-CA-CA-CB-O

## Resolution
root_cause: _generate_thf_coordinates() used incorrect ring-building logic that placed O and C atoms with wrong distances (O-C: 0.16-0.22 nm instead of 0.143 nm, C-C: 0.21 nm instead of 0.155 nm) and placed H atoms with arbitrary ±120° angles and ±0.3 nm z-offsets instead of proper tetrahedral geometry (resulting in H-C-H angles of 122° instead of 107-108°)
fix: Replaced function with verified THF template coordinates from actual hydrate structure. New coordinates match ITP bond lengths (O-C: 0.143 nm, C-C: 0.155 nm, C-H: 0.109 nm) and angles (H-C-H: 107-108°). The template is centered at origin and matches thf.itp atom ordering.
verification: All tests pass (test_solute_insertion.py: 9 passed). Verified bond lengths and angles match ITP values within acceptable tolerances. THF insertion successful with correct geometry.
files_changed: [quickice/structure_generation/solute_inserter.py]
