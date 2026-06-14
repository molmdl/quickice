---
phase: 36
plan: 02
subsystem: cli
tags: [itp, path-resolution, case-normalization, cli]
requires: []
provides: [itp_helpers.py, get_hydrate_guest_itp_path, get_solute_liquid_itp_path, get_tip4p_itp_path]
affects: [36-04]
tech-stack:
  added: []
  patterns: [path-resolution-with-case-normalization]
key-files:
  created: [quickice/cli/itp_helpers.py]
  modified: []
decisions:
  - id: D1
    choice: "Re-export get_tip4p_itp_path from gromacs_writer instead of reimplementing"
    rationale: "Existing function is tested and works; avoids duplication"
  - id: D2
    choice: "Inline import for get_tip4p_itp_path re-export"
    rationale: "Avoids circular import risk; only imported when actually called"
---

# Phase 36 Plan 02: ITP Path Resolver Functions Summary

**One-liner:** ITP path resolver functions with `.lower()` case normalization for hydrate guest, solute liquid, and TIP4P-ICE ITP files.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create ITP path resolver functions with case normalization | 67ffcdc | quickice/cli/itp_helpers.py |

## Verification Results

1. ✅ `from quickice.cli.itp_helpers import ...` imports without GUI dependency
2. ✅ `get_hydrate_guest_itp_path('CH4')` and `get_hydrate_guest_itp_path('ch4')` return the same path
3. ✅ `get_solute_liquid_itp_path('THF')` and `get_solute_liquid_itp_path('thf')` return the same path
4. ✅ No `from quickice.gui` imports in the module
5. ✅ `FileNotFoundError` raised for non-existent ITP files

## Implementation Details

### Functions

- **`get_hydrate_guest_itp_path(guest_type: str) -> Path`** — Resolves `{guest_type}_hydrate.itp` with case normalization
- **`get_solute_liquid_itp_path(solute_type: str) -> Path`** — Resolves `{solute_type}_liquid.itp` with case normalization
- **`get_tip4p_itp_path() -> Path`** — Re-exported from `quickice.output.gromacs_writer`

### Key Design Decisions

1. **Case normalization via `.lower()` at function entry** — CLI parser choices and `SoluteStructure.solute_type` may pass uppercase strings (e.g., "CH4", "THF"); `.lower()` ensures consistent file path resolution
2. **Re-export pattern for TIP4P** — Inline import avoids circular dependencies while providing convenient CLI-level access

## Deviations from Plan

None — plan executed exactly as written.

## Authentication Gates

None.

## Next Phase Readiness

- ✅ `itp_helpers.py` ready for import by CLI export commands (Plan 04)
- ✅ All three functions tested and verified
- ✅ No GUI coupling — CLI module works standalone
