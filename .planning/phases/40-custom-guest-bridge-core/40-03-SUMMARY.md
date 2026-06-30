---
phase: 40-custom-guest-bridge-core
plan: 03
subsystem: hydrate-config
tags: [hydrate-config, custom-guest, HydrateConfig, is_custom_guest, guest_residue_name, guest_gro_path, dataclass-validation]

# Dependency graph
requires:
  - phase: 38-internal-pipeline-refactor
    provides: 38-01 added guest_name, guest_atom_labels, guest_atom_count, guest_itp_path fields to HydrateConfig with built-in auto-populate from GUEST_MOLECULES; decision [38-01] established that custom types must provide metadata explicitly (no auto-populate)
  - phase: 40-custom-guest-bridge-core
    provides: 40-RESEARCH.md recommended separating guest_type (GenIce2 plugin name) from guest_residue_name (GRO residue name, <=3 chars base for _H suffix)
provides:
  - HydrateConfig.guest_residue_name field (GRO residue name for custom guests, base <=3 chars)
  - HydrateConfig.guest_gro_path field (path to custom guest .gro for GenIce2 Molecule module building)
  - HydrateConfig.is_custom_guest property (True when guest_type not in GUEST_MOLECULES)
  - Relaxed __post_init__ that accepts custom guest types with explicit required metadata
  - HydrateConfig.from_dict passthrough of guest_residue_name and guest_gro_path
  - 10 unit tests in tests/test_hydrate_config_custom.py
affects: [40-04-custom-guest-bridge, 40-05-hydrate-generator-integration, 41-gromacs-export-custom-guests, 42-mixed-cage-occupancy, 44-gui-integration, 45-cli-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Custom guest validation branch in __post_init__: when guest_type not in GUEST_MOLECULES, require explicit guest_residue_name + guest_atom_labels + guest_atom_count + guest_gro_path (no auto-populate per [38-01]); built-in path unchanged"
    - "is_custom_guest property: `return self.guest_type not in GUEST_MOLECULES` — clean boolean distinguishing custom (True) from built-in (False) guests"
    - "New fields default to empty string (\"\") for backward compatibility — built-in guests never need guest_residue_name or guest_gro_path"
    - "guest_name defaults to guest_residue_name (not guest_type) for custom guests — residue name is the user-facing identifier in the GRO file"

key-files:
  created:
    - tests/test_hydrate_config_custom.py
  modified:
    - quickice/structure_generation/types.py

key-decisions:
  - "Custom guests require ALL of guest_residue_name, guest_atom_labels, guest_atom_count, guest_gro_path — no auto-populate (per decision [38-01]); this forces the caller (40-04 bridge) to supply complete metadata"
  - "guest_name defaults to guest_residue_name for custom guests (e.g. 'MOL'), not to guest_type (e.g. 'etoh_custom') — the residue name is the user-facing identifier"
  - "Validation order: lattice_type → cage_occupancy → supercell → guest branch (residue_name → atom_labels → atom_count → gro_path); the old single 'Unknown guest type' raise is replaced by the branching logic"
  - "New fields default to empty string for backward compatibility — old callers/dicts without them still work; built-in guests never set guest_residue_name or guest_gro_path"

patterns-established:
  - "Custom guest validation in HydrateConfig: explicit-metadata-required branch keyed off `guest_type not in GUEST_MOLECULES` — reusable pattern for any future config that must distinguish built-in from user-supplied entries"

# Metrics
duration: 7min
completed: 2026-06-30
---

# Phase 40 Plan 03: HydrateConfig Extension for Custom Guests Summary

**HydrateConfig now carries guest_residue_name + guest_gro_path and accepts custom guest types (not in GUEST_MOLECULES) when explicit metadata is provided, with an is_custom_guest property distinguishing custom from built-in; 10 new + 30 existing tests pass with no regression**

## Performance

- **Duration:** 7 min
- **Started:** 2026-06-30T09:28:36Z
- **Completed:** 2026-06-30T09:35:40Z
- **Tasks:** 2
- **Files modified:** 2 (1 modified, 1 created)

## Accomplishments
- Extended `HydrateConfig` with two new backward-compatible fields: `guest_residue_name` (GRO residue name, base <=3 chars for the `_H` suffix) and `guest_gro_path` (path to the custom guest `.gro` for GenIce2 Molecule module building). Both default to empty string so built-in guests are unaffected.
- Added the `is_custom_guest` property: returns `True` when `guest_type` is not in `GUEST_MOLECULES` (i.e. a custom guest), `False` for built-ins. This is the single boolean the 40-04 bridge and 40-05 generator will branch on.
- Relaxed `__post_init__` validation: replaced the single `raise ValueError(f"Unknown guest type: ...")` with a branch — custom guests require explicit `guest_residue_name`, `guest_atom_labels`, `guest_atom_count`, and `guest_gro_path` (no auto-populate, per decision [38-01]); built-in guests auto-populate metadata from `GUEST_MOLECULES` unchanged. `guest_name` defaults to `guest_residue_name` for custom guests.
- Updated `from_dict` to pass `guest_residue_name` and `guest_gro_path` through (with empty-string defaults), so old dicts without the new fields still work and new dicts carrying custom-guest metadata flow through correctly.
- Created 10 unit tests covering: valid custom guest construction, explicit guest_name override, the 4 missing-required-field ValueError paths, built-in ch4/thf backward compat, from_dict passthrough, and from_dict backward compat.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add guest_residue_name, guest_gro_path fields + is_custom_guest property to HydrateConfig** - `2f21336` (feat)
2. **Task 2: Unit tests for custom guest HydrateConfig** - `7dc7fe5` (test)

## Files Created/Modified
- `quickice/structure_generation/types.py` - Added `guest_residue_name: str = ""` and `guest_gro_path: str = ""` fields after `guest_itp_path`; added `is_custom_guest` property (returns `guest_type not in GUEST_MOLECULES`); branched `__post_init__` so custom guests require explicit metadata while built-ins auto-populate unchanged; extended `from_dict` to pass the two new fields through; updated the class docstring to document the new fields, the property, and the custom-guest validation rules.
- `tests/test_hydrate_config_custom.py` - New 10-test unit suite across 4 classes (TestCustomGuestValid, TestCustomGuestValidation, TestBuiltinGuestBackwardCompat, TestFromDictCustomFields). Uses `pytest.raises(ValueError, match=...)` to assert field-specific error messages. Mirrors the import and class-grouping style of `tests/test_hydrate_config_metadata.py`.

## Decisions Made
- Custom guests require ALL of `guest_residue_name`, `guest_atom_labels`, `guest_atom_count`, `guest_gro_path` — no auto-populate from `GUEST_MOLECULES` (enforces decision [38-01]). The 40-04 bridge must supply complete metadata.
- `guest_name` defaults to `guest_residue_name` (e.g. "MOL") for custom guests rather than `guest_type` (e.g. "etoh_custom") — the residue name is the user-facing identifier written into the GRO file.
- Validation order kept the original sequence (lattice → occupancy → supercell → guest branch); the guest branch checks `guest_residue_name` first, then `atom_labels`, `atom_count`, `gro_path` — providing field-specific error messages that the 40-04 bridge can surface to the user.
- New fields default to empty string for backward compatibility — existing callers and old `from_dict` dicts without the new fields continue to work; built-in guests never set them.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `HydrateConfig` now carries `guest_residue_name` and `guest_gro_path`, and `is_custom_guest` is available — ready for **40-04** (custom guest bridge) which will set these fields when a user uploads a `.gro`/`.itp` pair, and **40-05** (hydrate generator integration) which will branch on `config.is_custom_guest` to register the custom guest module before `generate_ice()`.
- `_build_molecule_index` (Phase 38-02) already supports a `guest_residue_name` fallback (`getattr(config, "guest_residue_name", "") or guest_type.upper()`); the field now exists on the dataclass so the `getattr` fallback resolves to the explicit value for custom guests.
- No blockers: pure dataclass extension with no threading, I/O, or GenIce2 concerns.

---
*Phase: 40-custom-guest-bridge-core*
*Completed: 2026-06-30*
