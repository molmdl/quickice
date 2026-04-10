---
status: investigating
trigger: "hbond-regression-all-phases"
created: 2026-04-10T16:30:00
updated: 2026-04-10T17:00:00
---

## Current Focus

hypothesis: H-bond detection and visualization work correctly for pure ice Ih structures. The issue reported by user may be (1) in a different context (Interface structures with ice+water), (2) a misunderstanding of what's displayed (confusing covalent O-H bonds with H-bonds), or (3) specific to their viewing setup. Need to ask user for clarification about EXACTLY what they're seeing - which tab, which structure, what the displayed bonds look like.
test: Ask user for more specific details with CHECKPOINT
expecting: User provides (1) which tab they're viewing, (2) what structure type (ice Ih only or interface), (3) screenshot or description of what "O-O and H-H bonds" means - are these separate lines from O to O and H to H, or something else?
next_action: Return CHECKPOINT for user clarification

## Symptoms

expected: H-bonds should be detected between O (acceptor) and H (donor) atoms of DIFFERENT molecules, based on O...H distance and O-H...O angle criteria
actual: After PBC fix, even Ih shows wrong h-bonds
errors: No error message - incorrect visualization
reproduction: Load any ice structure (including Ih) in tab 1 and toggle h-bond display
started: Regression from the previous triclinic cell fix (commit dee7802)

## Eliminated

## Evidence

- timestamp: 2026-04-10T17:05:00
  checked: Atom structure in ice Ih candidates (debug_atom_structure.py)
  found: Ice Ih candidates correctly use 3 atoms per molecule (O, H, H). Atom ordering is correct: ["O", "H", "H", "O", "H", "H", ...]. H-bond detection returns correct H-O pairs (32 H-bonds for 16 molecules = 2 per molecule, no same-molecule bonds).
  implication: The issue is NOT with ice Ih candidates. The atom indexing and H-bond detection logic are correct for pure ice structures. Must investigate: (1) Interface structures (ice + water), (2) Visualization layer, (3) User's specific context (which tab/structure type).

- timestamp: 2026-04-10T17:00:00
  checked: User checkpoint response
  found: H-bonds showing as O-O and H-H bonds (wrong!). Ice Candidates have 3 atoms per molecule (O, H, H) in positions array, but TIP4P-ICE has 4 atoms per molecule (O, H1, H2, MW) in output format.
  implication: H-bond detection might be using wrong indices - treating MW as H, or not using atom_names array correctly. This would cause O-O bonds (MW involved) or H-H bonds (wrong indices).

- timestamp: 2026-04-10T16:30:00
  checked: Git commit dee7802
  found: Previous fix changed _pbc_distance() in vtk_utils.py and _extract_bonds() in molecular_viewer.py
  implication: Need to examine how these changes affected h-bond detection logic

- timestamp: 2026-04-10T16:32:00
  checked: detect_hydrogen_bonds() function (lines 168-257)
  found: Function checks H...O distance < max_distance and skips parent O (same molecule). Does NOT check O-H...O angle.
  implication: Current algorithm uses only distance criterion, no angle check. User mentioned "angle determination" as part of h-bond detection

- timestamp: 2026-04-10T16:33:00
  checked: PBC tests (test_pbc_hbonds.py)
  found: All 6 tests pass - PBC distance calculation is working correctly for both orthorhombic and triclinic cells
  implication: The PBC fix itself is correct. The regression must be something else. Need to investigate what "wrong h-bonds" actually means

- timestamp: 2026-04-10T16:38:00
  checked: Simple diagnostic test (debug_hbonds.py)
  found: H-bond detection finds 8 H-bonds in a 4-molecule test. Some are "spurious" PBC cross-overs (H at -0.1 nm -> O at 0.9 nm = 1.0 nm direct but 0.2 nm via PBC). The algorithm correctly applies PBC distance, but this creates false positives when atoms are far apart in real space.
  implication: The PBC distance calculation is working AS DESIGNED. Need to check if real ice structures have this issue or if there's a different problem. User said "even Ih shows wrong h-bonds" - need to test with actual ice Ih data

- timestamp: 2026-04-10T16:42:00
  checked: Real ice Ih structure test (debug_real_ice.py)
  found: H-bond detection works PERFECTLY for ice Ih: 32 H-bonds for 16 molecules (exactly 2 per molecule as expected), no same-molecule bonds, each molecule donates exactly 2 H-bonds. The detection logic is CORRECT.
  implication: The issue is NOT with H-bond detection logic. The PBC fix did NOT break Ih detection. Must investigate visualization or GUI-specific issues. User mentioned "incorrect visualization" - need to check how H-bonds are displayed

- timestamp: 2026-04-10T16:48:00
  checked: PBC distance comparison (debug_pbc_compare.py)
  found: Old and new PBC distance calculations give IDENTICAL results for orthorhombic cells. Tested 5 cases including across boundaries, all match perfectly. Also tested with real ice Ih H...O distances - all match.
  implication: The triclinic fix did NOT change behavior for orthorhombic cells. The PBC distance calculation is mathematically equivalent for Ih. This confirms the fix is correct for both cell types

## Resolution

root_cause:
fix:
verification:
files_changed: []
