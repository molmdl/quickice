---
phase: 38-internal-pipeline-refactor
verified: 2026-06-29T17:15:00Z
status: passed
score: 12/12 must-haves verified
gaps: []
---

# Phase 38: Internal Pipeline Refactor Verification Report

**Phase Goal:** Pipeline identifies molecules by metadata (not atom-name pattern matching) and validates format constraints at write time
**Verified:** 2026-06-29T17:15:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | HydrateConfig carries guest_name, guest_atom_labels, guest_atom_count, and guest_itp_path fields | ✓ VERIFIED | types.py L369-372: fields declared with defaults |
| 2 | GUEST_MOLECULES dict has atom_labels for each built-in guest type | ✓ VERIFIED | types.py L122 (ch4: 5 labels), L130 (thf: 13 labels) |
| 3 | HydrateStructure carries guest metadata from HydrateConfig through to export | ✓ VERIFIED | types.py L766-769: 4 guest fields on HydrateStructure; hydrate_generator.py L129-132: propagated from config |
| 4 | Built-in guest types (ch4, thf) populate metadata from GUEST_MOLECULES automatically | ✓ VERIFIED | types.py L388-394: __post_init__ auto-populates when fields empty |
| 5 | _build_molecule_index identifies guest molecules from HydrateConfig.guest_atom_labels and guest_atom_count, not from pattern matching | ✓ VERIFIED | hydrate_generator.py L529-560: metadata-driven path uses config fields; pattern matching only in config=None path (L602+) |
| 6 | Guest molecules are identified by checking if atom names match guest_atom_labels sequence starting from the first atom | ✓ VERIFIED | hydrate_generator.py L554-558: atom_names[i:i+count] == guest_atom_labels |
| 7 | Unknown atom types produce 'unknown' MoleculeIndex entries with a warning | ✓ VERIFIED | hydrate_generator.py L590-598: logger.warning + MoleculeIndex(i, 1, "unknown") |
| 8 | Water identification uses OW signature atom (unchanged for TIP4P compatibility) | ✓ VERIFIED | hydrate_generator.py L562-567: OW, HW1, HW2, MW check unchanged |
| 9 | GRO writer rejects residue names >5 chars with a clear ValueError instead of silently truncating or overflowing | ✓ VERIFIED | gromacs_writer.py L24-47: validate_gro_residue_name raises ValueError with name, length, limit |
| 10 | All 5 truncation sites (res_name[:5]) replaced with validation that raises ValueError | ✓ VERIFIED | 0 remaining truncation sites; grep for `res_name[:5]` returns no matches |
| 11 | All GRO format string sites (<5s, :5s) preceded by validation to prevent overflow | ✓ VERIFIED | 11 format string sites, all with preceding validate_gro_residue_name call verified |
| 12 | ITP transformation pipeline applies _H suffix, comments out atomtypes section, and rewrites moleculetype name | ✓ VERIFIED | gromacs_writer.py L570-642: transform_guest_itp does all 3; wired in GUI (hydrate_export.py L185) and CLI (itp_helpers.py L189) |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quickice/structure_generation/types.py` | HydrateConfig/HydrateStructure guest metadata fields | ✓ VERIFIED | 835 lines; 4 guest metadata fields on both dataclasses; GUEST_MOLECULES has atom_labels |
| `quickice/structure_generation/hydrate_generator.py` | Metadata-driven _build_molecule_index | ✓ VERIFIED | 691 lines (>500 min); config param; metadata path L529-600; pattern-matching path L602+ |
| `quickice/output/gromacs_writer.py` | validate_gro_residue_name + transform_guest_itp | ✓ VERIFIED | 3196 lines; validate at L24-47; transform at L570-642; 11 validation call sites |
| `quickice/gui/hydrate_export.py` | GUI ITP transformation wiring | ✓ VERIFIED | 196 lines; transform_guest_itp imported (L137) and called (L185) |
| `quickice/cli/itp_helpers.py` | CLI ITP transformation wiring | ✓ VERIFIED | 416 lines; lazy import (L182) and call (L189) |
| `tests/test_hydrate_config_metadata.py` | Config/structure metadata tests | ✓ VERIFIED | 250 lines, 30 tests; all passing |
| `tests/test_build_molecule_index.py` | _build_molecule_index tests | ✓ VERIFIED | 357 lines, 13 tests; all passing |
| `tests/test_gro_resname_validation.py` | GRO validation tests | ✓ VERIFIED | 169 lines, 29 tests; all passing |
| `tests/test_itp_transformation.py` | ITP transformation tests | ✓ VERIFIED | 316 lines, 19 tests; all passing |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| HydrateConfig.__post_init__ | GUEST_MOLECULES | Auto-populate empty fields | ✓ WIRED | types.py L388-394: reads guest_info["atom_labels"], ["atoms"] |
| HydrateConfig | HydrateStructure | generate() return | ✓ WIRED | hydrate_generator.py L129-132: guest_name/labels/count/itp_path from config |
| HydrateConfig | _build_molecule_index | config parameter | ✓ WIRED | hydrate_generator.py L107: config=config passed |
| _build_molecule_index | config.guest_atom_labels | Metadata-driven identification | ✓ WIRED | hydrate_generator.py L530-532: extracts from config |
| validate_gro_residue_name | GRO write sites | Validation calls | ✓ WIRED | 11 call sites across 6 writer functions |
| transform_guest_itp | comment_out_atomtypes_in_itp | Delegation | ✓ WIRED | gromacs_writer.py L590 |
| transform_guest_itp | validate_gro_residue_name | GRO name guard | ✓ WIRED | gromacs_writer.py L605: validates before transformation |
| hydrate_export.py (GUI) | transform_guest_itp | Import + call | ✓ WIRED | L137 import, L185 call with suffix="_H" |
| itp_helpers.py (CLI) | transform_guest_itp | Lazy import + call | ✓ WIRED | L182 lazy import, L189 call with suffix="_H" |

### Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| PIPE-01 | ✓ SATISFIED | _build_molecule_index uses config.guest_atom_labels/guest_atom_count (not pattern matching) when config provided |
| PIPE-02 | ✓ SATISFIED | HydrateConfig carries guest_name, guest_atom_labels, guest_atom_count, guest_itp_path through to HydrateStructure |
| PIPE-03 | ✓ SATISFIED | validate_gro_residue_name raises ValueError for >5 chars; all truncation/overflow sites replaced |
| PIPE-04 | ✓ SATISFIED | transform_guest_itp applies _H suffix, comments out atomtypes, validates GRO name; wired in GUI and CLI |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| gromacs_writer.py | 1411 | "placeholder" in docstring | ℹ️ Info | Comment describing "XX placeholder" for element symbols — not a code stub |

No blocker or warning anti-patterns found.

### Human Verification Required

None — all must-haves are programmatically verifiable. The following items are validated by existing automated tests:

- GRO validation behavior (29 tests in test_gro_resname_validation.py)
- ITP transformation correctness (19 tests in test_itp_transformation.py)
- Metadata-driven molecule identification (13 tests in test_build_molecule_index.py)
- Config/structure metadata propagation (30 tests in test_hydrate_config_metadata.py)

Full test suite: 1121 passed, 2 skipped, 0 failures.

### Notes

1. **ROADMAP criterion #4 nuance:** "rewrites residue names for custom guests" — the moleculetype name (which IS the GROMACS residue name) is rewritten with _H suffix. The `[ atoms ]` section residue column rewriting for custom guests was explicitly scoped out per Plan 04 decision, deferred to Phase 40 where custom guests are introduced. Built-in ITPs (ch4_hydrate.itp, thf_hydrate.itp) already have correct residue names (CH4_H, THF_H) in both moleculetype name and atoms section. No gap for Phase 38 scope.

2. **Guest-before-water priority:** The metadata-driven path checks guest identification BEFORE water patterns (hydrate_generator.py L540-577), preventing THF's "O" atom from being misidentified as 3-site water. TestGuestBeforeWater in test_build_molecule_index.py confirms this.

3. **Backward compatibility:** config=None preserves full pattern-matching behavior (hydrate_generator.py L602+). This ensures zero regression risk for callers that don't provide a HydrateConfig.

---

_Verified: 2026-06-29T17:15:00Z_
_Verifier: OpenCode (gsd-verifier)_
