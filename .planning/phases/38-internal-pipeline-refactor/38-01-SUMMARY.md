---
phase: 38
plan: 01
subsystem: structure_generation
tags: [dataclass, metadata, hydrate, guest-molecules, auto-population]
requires: [37.2]
provides: [HydrateConfig guest metadata, HydrateStructure guest metadata, GUEST_MOLECULES atom_labels]
affects: [38-02, 38-03, 38-04]
tech-stack:
  added: []
  patterns: [metadata-driven molecule identification]
key-files:
  created: [tests/test_hydrate_config_metadata.py]
  modified: [quickice/structure_generation/types.py, quickice/structure_generation/hydrate_generator.py]
decisions:
  - Built-in guest types auto-populate metadata in __post_init__; custom types (Phase 40) must provide explicitly
  - guest_itp_path is NOT auto-populated (only relevant for custom guests)
  - atom_labels uses list copy from GUEST_MOLECULES to avoid shared mutable state
duration: ""
completed: 2026-06-27
---

# Phase 38 Plan 01: Guest Molecule Metadata Data Model Summary

Extended GUEST_MOLECULES dict and HydrateConfig/HydrateStructure dataclasses with guest molecule metadata fields, enabling metadata-driven molecule identification for downstream Plans 02-04.

## One-liner

HydrateConfig and HydrateStructure carry guest_name, guest_atom_labels, guest_atom_count, and guest_itp_path; built-in types auto-populate from GUEST_MOLECULES

## What was done

### Task 1: Add atom_labels to GUEST_MOLECULES + extend HydrateConfig

- Added `atom_labels` field to both ch4 and thf entries in `GUEST_MOLECULES` dict
  - ch4: `["C", "H", "H", "H", "H"]` (5 atoms, all-atom methane from GenIce2)
  - thf: `["O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H"]` (13 atoms)
- Added 4 new fields to `HydrateConfig`: `guest_name`, `guest_atom_labels`, `guest_atom_count`, `guest_itp_path`
- Updated `HydrateConfig.__post_init__` to auto-populate metadata for built-in types when fields are empty/default
- Updated `HydrateConfig.from_dict` for backward compatibility with new fields
- Created comprehensive test file with 22 tests for GUEST_MOLECULES and HydrateConfig

### Task 2: Extend HydrateStructure with guest metadata + propagate from config

- Added 4 new fields to `HydrateStructure`: `guest_name`, `guest_atom_labels`, `guest_atom_count`, `guest_itp_path`
- Updated `hydrate_generator.generate()` to pass guest metadata from config to HydrateStructure in return statement
- Added 8 tests for HydrateStructure metadata propagation including round-trip verification

## Verification

- All 30 new tests pass (22 config + 8 structure)
- All 108 hydrate-related tests pass (no regressions)
- GUEST_MOLECULES has atom_labels for ch4 and thf
- HydrateConfig auto-populates metadata for built-in types
- HydrateStructure carries metadata from config

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **Auto-population with empty-check pattern**: `__post_init__` only fills in fields that are empty/default, allowing explicit values to override. This pattern works cleanly with Python dataclass defaults.
2. **List copy for atom_labels**: Auto-population uses `list()` to create a copy of the atom_labels list from GUEST_MOLECULES, preventing shared mutable state issues.
3. **No auto-populate for guest_itp_path**: This field is only meaningful for custom guests (Phase 40), so it stays empty for built-in types.

## Next Phase Readiness

- Plan 02 (`_build_molecule_index` refactor) can now use `config.guest_atom_labels` for metadata-driven identification
- Plan 03 (GRO writer metadata) can use `HydrateStructure.guest_atom_labels` 
- Plan 04 (ITP transformation) can use `HydrateStructure.guest_itp_path`
- No blockers for Plans 02-04
