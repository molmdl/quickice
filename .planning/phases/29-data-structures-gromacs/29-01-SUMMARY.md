---
phase: 29-data-structures-gromacs
plan: 01
subsystem: data-structures
tags: [types, dataclass, multi-molecule, gromacs]
created: 2026-04-14
completed: 2026-04-14

dependency_graph:
  requires: []
  provides:
    - MoleculeIndex dataclass
    - InterfaceStructure.molecule_index field
    - MOLECULE_TYPE_INFO constant
  affects: [29-02, 29-03, 29-04, 29-05, 29-06, Phase 30, Phase 31, Phase 32]

tech_stack:
  added: []
  patterns:
    - Dataclass-based data structures for type safety
    - Module-level constants for molecule type information

key_files:
  created: []
  modified:
    - quickice/structure_generation/types.py
      - Added MOLECULE_TYPE_INFO constant at module level
      - Added MoleculeIndex dataclass with start_idx, count, mol_type
      - Added molecule_index field to InterfaceStructure with default empty list

decisions: []

metrics:
  duration: "~1 minute"
  tasks_completed: 3/3
  tests_passed: 57/57 (structure_generation tests)

---

## Summary

Created foundation for multi-molecule type support in QuickIce by adding extensible data structures:

1. **MoleculeIndex dataclass** - Tracks molecule position in atom array with start_idx, count, mol_type fields. Enables variable atoms-per-molecule handling (ions: 1, ice: 3, water: 4, CH4: 5, THF: 12).

2. **InterfaceStructure.molecule_index field** - Extended InterfaceStructure with molecule_index list field. Backward compatible - existing code using ice_atom_count still works.

3. **MOLECULE_TYPE_INFO constant** - Module-level dictionary mapping molecule type strings to atom counts, residue names, and descriptions. Provides single source of truth for atoms-per-molecule.

All verification criteria passed:
- `MoleculeIndex(0, 4, 'water')` creates correct dataclass
- `'molecule_index' in InterfaceStructure.__dataclass_fields__` is True
- `MOLECULE_TYPE_INFO['ch4']['atoms']` returns 5
- All 57 structure_generation tests pass with no breaking changes

## Deviations from Plan

None - plan executed exactly as written. All tasks completed successfully in single atomic commit.

---

## Notes for Future Plans

- MoleculeIndex provides foundation for Phase 29 plans 02-06 (multi-molecule GROMACS export)
- Will be used by Phase 30 (IonInserter) and Phase 31 (HydrateStructureGenerator)
- InterfaceStructure is backward compatible - existing ice-only generation unchanged