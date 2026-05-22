---
phase: e2e-export-test
plan: 02
subsystem: testing
tags: [pytest, GROMACS, export, ice, TIP4P-ICE, e2e, mock-dialog]
---

# Phase e2e-export-test Plan 02: Ice GROMACS Exporter Tests Summary

**One-liner:** 5 E2E tests for GROMACSExporter (Tab 0 — Ice) validating QFileDialog/QMessageBox mock pattern and TIP4P-ICE 3→4 atom expansion (O,H,H → OW,HW1,HW2,MW).

## Dependency Graph

- **requires:** tests/test_output/conftest.py (ranked_candidate, mock_save_dialog, mock_cancel_dialog fixtures), quickice.gui.export (GROMACSExporter), quickice.output.gromacs_writer (write_gro_file, write_top_file, get_tip4p_itp_path)
- **provides:** tests/test_output/test_gromacs_export_ice.py — baseline mock pattern for all 6 exporters
- **affects:** Plans 03-08 of e2e-export-test phase (all reuse the same mock pattern validated here)

## Tech Stack

- **added:** None
- **patterns:** QFileDialog/QMessageBox mock via unittest.mock.patch with context managers; GRO file format parsing (fixed-width columns at positions 10:15 for atom names)

## Key Files

- **created:**
  - `tests/test_output/test_gromacs_export_ice.py` (126 lines) — TestIceGROMACSExporter with 5 test methods
- **modified:** None

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create test_gromacs_export_ice.py with 5 test methods | 6e65e6b | tests/test_output/test_gromacs_export_ice.py |

## Tests Delivered

| # | Test Method | Validates |
|---|------------|-----------|
| 1 | `test_export_creates_gro_top_itp` | .gro, .top, .itp files created; ITP uses .gro stem |
| 2 | `test_export_cancelled_returns_false` | Cancelled QFileDialog returns False, no files created |
| 3 | `test_gro_file_has_correct_atom_count` | nmolecules * 4 atoms (TIP4P-ICE expansion, not 3) |
| 4 | `test_gro_file_has_tip4p_atom_names` | OW, HW1, HW2, MW atom names at GRO positions 10:15 |
| 5 | `test_top_file_has_molecules_section` | [ molecules ] section with SOL count matching nmolecules |

## Decisions Made

- **ITP filename convention confirmed:** The .itp file is named `{stem}.itp` where stem comes from the .gro filename (e.g., "ice_test.itp" for "ice_test.gro"), NOT "tip4p-ice.itp". This is the behavior of `GROMACSExporter.export_gromacs()` which uses `path.with_name(path.stem + '.itp')`.
- **Mock pattern validated for reuse:** The `(save_path, dialog_patch, mb_patch)` tuple pattern from conftest.py works correctly with `with dialog_p, mb_p:` context managers. This pattern is confirmed for Plans 03-08.
- **No QApplication needed:** GROMACSExporter only uses QFileDialog and QMessageBox which are fully mocked, confirming the conftest.py design decision.

## Deviations from Plan

None — plan executed exactly as written.

## Authentication Gates

None.

## Next Phase Readiness

- Mock pattern proven: Plans 03-08 can follow identical mock_save_dialog/mock_cancel_dialog pattern
- GRO file parsing approach (fixed-width columns) established for reuse in Plans 03-07
- TIP4P-ICE 3→4 expansion validated, establishing baseline for interface/hydrate tests

## Metrics

- **duration:** ~2 minutes
- **completed:** 2026-05-22
