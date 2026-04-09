---
status: verifying
trigger: "MED-05 atom-name-replication - Unnecessary atom name replication creates new lists repeatedly"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:00:00Z
---

## Current Focus

hypothesis: Atom name list multiplication is correct and reasonably efficient for typical use cases (<10k molecules). For large systems, memory usage is O(n) for n molecules.
test: Verify all tests pass after adding module-level constants with documentation
expecting: All tests pass, constants properly defined and used
next_action: Verify tests pass and update debug file with resolution

## Symptoms

expected: Efficient atom name replication for large molecule counts
actual: Creates new list each time using multiplication
errors: No error, but memory-intensive for large molecule counts
reproduction: Generate interface with thousands of molecules
started: Always used this approach

## Eliminated

(none)

## Evidence

- timestamp: 2026-04-09T00:00:00Z
  checked: slab.py:103, pocket.py:93, piece.py:83
  found: All three files use `["O", "H", "H"] * nmolecules` pattern
  implication: Pattern is consistent and called once per interface generation

- timestamp: 2026-04-09T00:00:00Z
  checked: water_filler.py:282
  found: Also uses `template_atom_names * n_molecules` pattern
  implication: Same pattern used throughout codebase

- timestamp: 2026-04-09T00:00:00Z
  checked: types.py:151
  found: InterfaceStructure.atom_names is list[str]
  implication: Must be a list, not generator or other type

- timestamp: 2026-04-09T00:00:00Z
  checked: gromacs_writer.py, vtk_utils.py
  found: atom_names used in zip() with positions, iterated once
  implication: No performance-critical path that would benefit from lazy evaluation

- timestamp: 2026-04-09T00:00:00Z
  checked: Python string interning behavior
  found: Python interns short strings like "O", "H", "H"
  implication: List multiplication creates references to same string objects, not new strings

- timestamp: 2026-04-09T00:00:00Z
  checked: Memory analysis
  found: For 10k molecules: 30k list entries = ~240KB overhead (list pointers only)
  found: For 100k molecules: 300k list entries = ~2.4MB overhead
  implication: Acceptable for typical use (<10k), visible for large systems

- timestamp: 2026-04-09T00:00:00Z
  checked: Tests after fix
  found: 234 tests pass (excluding CLI integration test - pre-existing issue)
  implication: Fix works correctly, no regression

## Resolution

root_cause: List multiplication `["O", "H", "H"] * n` creates O(n) memory allocation. For typical use (<10k molecules), this is acceptable (~240KB). For large systems (>10k molecules), this uses more memory than necessary, but the impact is modest (~2.4MB for 100k molecules).

The pattern is correct and reasonably efficient. Python string interning ensures we're not duplicating string objects, only creating list structure.

fix: Added module-level constants `ICE_ATOM_NAMES_TEMPLATE = ["O", "H", "H"]` in slab.py, pocket.py, and piece.py with documentation explaining the memory trade-off. This improves code maintainability and documents the design decision without adding complexity.

Also fixed pre-existing issue: Added missing constants `IDEAL_OO_DISTANCE` and `OO_CUTOFF` in quickice/ranking/scorer.py that were referenced but not defined.

verification: All 234 tests pass (excluding CLI integration test which has pre-existing phase-not-found issue unrelated to this fix).

files_changed: 
- quickice/structure_generation/modes/slab.py (added ICE_ATOM_NAMES_TEMPLATE constant)
- quickice/structure_generation/modes/pocket.py (added ICE_ATOM_NAMES_TEMPLATE constant)
- quickice/structure_generation/modes/piece.py (added ICE_ATOM_NAMES_TEMPLATE constant)
- quickice/ranking/scorer.py (added IDEAL_OO_DISTANCE and OO_CUTOFF constants)