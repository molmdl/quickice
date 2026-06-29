---
phase: 38
plan: 02
subsystem: structure_generation
tags: [tdd, metadata-driven, molecule-identification, hydrate, guest-molecules, refactor]
requires: [38-01]
provides: [metadata-driven _build_molecule_index, guest-before-water priority, residue grouping fallback]
affects: [38-03, 38-04]
tech-stack:
  added: []
  patterns: [metadata-driven molecule identification, guest-first identification priority, dual-path backward compat]
key-files:
  created: [tests/test_build_molecule_index.py]
  modified: [quickice/structure_generation/hydrate_generator.py]
decisions:
  - Guest identification checked BEFORE water in metadata-driven path to prevent THF oxygen misidentification as 3-site water
  - Residue grouping is the preferred path for GenIce2 output; atom-label sequence matching is the fallback
  - config=None preserves full backward-compatible pattern matching (no behavior change for existing callers)
  - Two separate code paths (metadata vs pattern-matching) rather than unified to ensure zero regression risk
  - 3-site water check in metadata path no longer needs residue != "THF" guard because guest is checked first
duration: ""
completed: 2026-06-29
---

# Phase 38 Plan 02: Metadata-driven _build_molecule_index Summary

Refactored `_build_molecule_index` to use metadata-driven guest molecule identification from HydrateConfig (guest_atom_labels, guest_atom_count, guest_type) instead of hardcoded pattern matching on atom/residue names.

## One-liner

_build_molecule_index identifies guests from HydrateConfig.guest_atom_labels with guest-before-water priority and residue grouping fallback; config=None preserves backward-compat pattern matching

## What was done

### Task 1: TDD RED — Write failing tests

Created `tests/test_build_molecule_index.py` with 13 tests across 6 test classes:

- `TestCH4MetadataIdentification` (2 tests): CH4 identified via config.guest_atom_labels
- `TestTHFMetadataIdentification` (1 test): THF identified via atom-label sequence matching
- `TestTHFResidueGrouping` (2 tests): THF grouped by residue_seq_nums when residue name matches guest_type.upper()
- `TestGuestBeforeWater` (2 tests): THF "O" not misidentified as 3-site water (KEY correctness property)
- `TestConfigNoneBackwardCompat` (5 tests): config=None preserves pattern matching for TIP4P, CH4, THF, ions, Me
- `TestUnknownAtomWarning` (1 test): Unknown atom produces "unknown" entry with warning

All 13 tests fail with `TypeError: unexpected keyword argument 'config'` — confirming the API doesn't exist yet.

### Task 2: TDD GREEN+REFACTOR — Implement metadata-driven _build_molecule_index

Refactored `_build_molecule_index` signature to accept `config: HydrateConfig | None = None`:

**Metadata-driven path (config provided):**
1. Extract guest_atom_labels, guest_atom_count, guest_type from config
2. Derive guest_res_name = guest_type.upper() (e.g., "THF" for thf)
3. Derive guest_signature = guest_atom_labels[0] (e.g., "O" for THF, "C" for CH4)
4. Main loop checks in order:
   - Guest residue grouping (if residue == guest_res_name) — preferred for GenIce2 output
   - Guest atom-label matching (if atom_names[i:i+count] == guest_atom_labels) — fallback
   - TIP4P water (OW, HW1, HW2, MW) — unchanged
   - 3-site water (O, H, H) — no longer needs THF residue guard
   - Ions (NA/Na, CL/Cl) — unchanged
   - Unknown — unchanged

**Pattern-matching path (config=None):**
- Preserved full backward-compatible code unchanged (THF residue check, Me, C+4H, etc.)

Also updated `generate()` to pass `config=config` to `_build_molecule_index`.

All 13 new tests pass + 146 related tests pass with no regressions.

## Key Design Decisions

1. **Guest before water**: Guest identification checked BEFORE water patterns. This is critical because THF's first atom "O" would match the 3-site water pattern (O, H, H) if water were checked first.

2. **Residue grouping preferred**: When GenIce2 provides residue names that match guest_type.upper(), residue-based grouping is used (same as old hardcoded THF check). This handles variable-length guests correctly without needing exact atom counts.

3. **Atom-label matching as fallback**: When residue names aren't available (e.g., after interface conversion strips residue info), the atom-label sequence matching path identifies guests by checking if the next N atoms match guest_atom_labels.

4. **Two separate code paths**: Rather than trying to unify metadata-driven and pattern-matching paths, they're kept separate. This ensures zero regression risk for config=None callers and makes both paths clear and auditable.

5. **3-site water guard removed in metadata path**: The `residue != "THF"` guard on the 3-site water check is no longer needed in the metadata-driven path because guest is checked first. THF's "O" is caught by the guest check and never reaches the water check.

## Deviations from Plan

None — plan executed exactly as written.

## Verification

1. `python -m pytest tests/test_build_molecule_index.py -v` — 13/13 pass
2. `python -m pytest tests/test_build_molecule_index.py tests/test_hydrate_config_metadata.py tests/test_hydrate_guest_tiling.py ...` — 146/146 pass
3. `_build_molecule_index` signature accepts `config: HydrateConfig | None = None`
4. When config provided, guest identified from guest_atom_labels (not hardcoded patterns)
5. When config=None, backward-compatible pattern matching still works
6. THF "O" atom not misidentified as water (test_guest_before_water tests confirm)
