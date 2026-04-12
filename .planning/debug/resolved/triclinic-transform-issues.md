---
status: resolved
trigger: "Three related issues after adding triclinic transform code"
created: 2026-04-13T00:00:00Z
updated: 2026-04-13T00:03:00Z
---

## Current Focus

hypothesis: Both fixes verified, all tests pass
test: Full test suite run
expecting: All tests pass
next_action: Archive debug session

## Symptoms

expected:
1. Tooltips should wrap to new lines for long content
2. Tab 1 viewer should display triclinic phases correctly (like before)
3. Tab 2 transformed structure should show correct ice structure with proper atomic positions

actual:
1. All tooltips are chopped/truncated instead of wrapping
2. Tab 1 viewer throws ValueError for triclinic phases
3. Tab 2 shows corrupted output with broken bonds, wrong positions, distorted cell, empty spaces

errors:
```
Traceback (most recent call last):
  File "~/quickice/quickice/gui/main_window.py", line 366, in _on_candidates_ready
    self.viewer_panel.dual_viewer.set_candidates(result.ranked_candidates)
  File "~/quickice/quickice/gui/dual_viewer.py", line 228, in set_candidates
    self.viewer1.set_ranked_candidate(ranked_candidates[0])
  File "~/quickice/quickice/gui/molecular_viewer.py", line 419, in set_ranked_candidate
    self.set_candidate(ranked.candidate)
  File "~/quickice/quickice/gui/molecular_viewer.py", line 164, in set_candidate
    mol = candidate_to_vtk_molecule(candidate)
  File "~/quickice/quickice/gui/vtk_utils.py", line 87, in candidate_to_vtk_molecule
    raise ValueError(...)
ValueError: Invalid atom ordering for molecule 96: expected ['O', 'H', 'H'] or ['OW', 'HW1', 'HW2'], got []. Bond creation requires atoms to be ordered as oxygen followed by two hydrogens.
```

reproduction:
- Load a triclinic phase (e.g., Phase II) in the interface
- Tab 1 viewer throws error
- Tab 2 shows corrupted transformed structure

started: After adding triclinic transform code

## Eliminated

## Evidence

- timestamp: 2026-04-13T00:00:00Z
  checked: Symptoms pre-filled from user report
  found: Three issues: tooltips, tab 1 error, tab 2 corruption
  implication: All three related to triclinic transform code addition

- timestamp: 2026-04-13T00:00:30Z
  checked: generator.py lines 126-165 (candidate creation with transformation)
  found: positions are updated from result.positions but atom_names is NOT updated
  implication: atom_names has original count while positions has supercell count

- timestamp: 2026-04-13T00:01:00Z
  checked: generator.py line 152
  found: atom_names=atom_names uses ORIGINAL atom_names, not replicated
  implication: For 6x transformation: positions has 1728 atoms but atom_names has only 288 names
  root_cause_confirmed: TRUE

- timestamp: 2026-04-13T00:01:30Z
  checked: main_window.py tooltip stylesheet
  found: max-width: 400px on QToolTip causes truncation instead of wrapping
  implication: Qt QToolTip doesn't support max-width for text wrapping

- timestamp: 2026-04-13T00:02:00Z
  checked: Manual verification after fix
  found: positions shape (1728, 3), atom_names count 1728, Match: True
  implication: Fix works correctly

- timestamp: 2026-04-13T00:02:30Z
  checked: VTK molecule creation
  found: candidate_to_vtk_molecule works with 1728 atoms and 1152 bonds
  implication: Tab 1 viewer should now work for triclinic phases

- timestamp: 2026-04-13T00:03:00Z
  checked: Full test suite
  found: 78 tests passed
  implication: No regressions introduced

## Resolution

root_cause: Two bugs found:
1. In generator.py, the triclinic transformation replicates positions to create a supercell, but atom_names was not replicated. This caused a mismatch where positions had multiplier×more atoms than atom_names. The error "got []" for molecule 96 occurred because slicing atom_names[288:291] on a 288-element list returned an empty list.
2. In main_window.py, the QToolTip max-width: 400px CSS property caused text truncation instead of wrapping in Qt.

fix: 
1. Added atom_names replication in generator.py: atom_names = atom_names * result.multiplier when multiplier > 1
2. Removed max-width from tooltip stylesheet, added padding instead
3. Added regression test: test_atom_names_count_matches_positions_after_transformation

verification: 
- Manual test shows atom_names count (1728) matches positions count (1728) after 6x transformation
- VTK molecule creation succeeds with 1728 atoms and 1152 bonds
- All 78 tests in test_structure_generation.py and test_transformer.py pass

files_changed:
- quickice/structure_generation/generator.py
- quickice/gui/main_window.py
- tests/test_structure_generation.py (added regression test)
