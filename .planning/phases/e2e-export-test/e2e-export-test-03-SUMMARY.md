---
phase: e2e-export-test
plan: 03
subsystem: testing
tags: [pytest, GROMACS, export, hydrate, CH4_H, MoleculetypeRegistry, e2e, mock-dialog]
---

# Phase e2e-export-test Plan 03: Hydrate GROMACS Exporter Tests Summary

**One-liner:** 5 E2E tests for HydrateGROMACSExporter (Tab 1 — Hydrate) validating hydrate-specific mock path (hydrate_export.py, NOT export.py) and MoleculetypeRegistry _H suffix pattern (CH4 → CH4_H).

## Dependency Graph

- **requires:** tests/test_output/conftest.py (simple_hydrate_structure, simple_hydrate_config, mock_hydrate_save_dialog, mock_cancel_dialog fixtures), quickice.gui.hydrate_export (HydrateGROMACSExporter), quickice.output.gromacs_writer (write_multi_molecule_gro_file, write_multi_molecule_top_file, get_tip4p_itp_path)
- **provides:** tests/test_output/test_gromacs_export_hydrate.py — hydrate-specific mock path validation and _H suffix testing
- **affects:** Plans 04-08 of e2e-export-test phase (registry case-sensitivity fix benefits solute and chain tests)

## Tech Stack

- **added:** None
- **patterns:** Hydrate-specific QFileDialog mock path (quickice.gui.hydrate_export vs quickice.gui.export); MoleculetypeRegistry _H suffix for hydrate guests; write_multi_molecule_gro_file/write_multi_molecule_top_file (multi-molecule writers)

## Key Files

- **created:**
  - `tests/test_output/test_gromacs_export_hydrate.py` (143 lines) — TestHydrateGROMACSExporter with 5 test methods
- **modified:**
  - `quickice/output/gromacs_writer.py` — Fixed registry case mismatch in write_multi_molecule_top_file (hydrate_ch4 → hydrate_CH4)

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create test_gromacs_export_hydrate.py with 5 test methods | b311a38 | tests/test_output/test_gromacs_export_hydrate.py, quickice/output/gromacs_writer.py |

## Tests Delivered

| # | Test Method | Validates |
|---|------------|-----------|
| 1 | `test_export_creates_all_files` | .gro, .top, tip4p-ice.itp, ch4_hydrate.itp created; water ITP always named tip4p-ice.itp |
| 2 | `test_export_cancelled_returns_false` | Cancelled QFileDialog returns False; validates mock path is quickice.gui.hydrate_export |
| 3 | `test_guest_itp_copied` | ch4_hydrate.itp copied to output with [ moleculetype ] section |
| 4 | `test_top_file_references_guest_itp` | #include "ch4_hydrate.itp" + CH4_H in [ molecules ] (registry _H suffix) |
| 5 | `test_top_file_references_tip4p_ice` | #include "tip4p-ice.itp" + SOL with water molecule count |

## Decisions Made

- **Hydrate mock path confirmed critical:** HydrateGROMACSExporter imports QFileDialog from quickice.gui.hydrate_export, NOT quickice.gui.export. Test 2 explicitly validates this by passing `module_path='quickice.gui.hydrate_export'` to mock_cancel_dialog.
- **Water ITP naming convention differs from Ice:** Hydrate exporter always uses "tip4p-ice.itp" (not stem-based like Ice's "ice_test.itp"). Guest ITP uses its original filename (ch4_hydrate.itp).
- **Hydrate export method signature differs:** `export_hydrate(structure, config)` takes HydrateConfig as second argument (all other exporters take just structure).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed MoleculetypeRegistry case mismatch in write_multi_molecule_top_file**

- **Found during:** Task 1 — test_top_file_references_guest_itp failed because .top file showed `CH4` instead of `CH4_H`
- **Issue:** `register_hydrate_guest('CH4')` stores registry key `hydrate_CH4` (uppercase), but `write_multi_molecule_top_file` constructed lookup key as `hydrate_{mol_type}` where mol_type from molecule_index is lowercase `"ch4"`, producing `hydrate_ch4` — a key that doesn't exist in the registry
- **Fix:** Changed both hydrate and liquid key construction to use `mol_type.upper()`, so `hydrate_CH4` and `liquid_CH4` are correctly matched
- **Files modified:** quickice/output/gromacs_writer.py (lines 1192, 1198)
- **Commit:** b311a38

## Authentication Gates

None.

## Next Phase Readiness

- Hydrate-specific mock path validated — Plans 04-08 must use correct module paths for their exporters
- Registry case mismatch fix benefits Plans 06 (solute uses _L suffix) and 08 (chain test may combine _H and _L)
- Multi-molecule writer pattern validated for Plans 04 (interface also uses multi-molecule writers for guest variants)

## Metrics

- **duration:** ~3 minutes
- **completed:** 2026-05-22
