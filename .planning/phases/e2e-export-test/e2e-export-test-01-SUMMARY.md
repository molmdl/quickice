---
phase: e2e-export-test
plan: 01
subsystem: testing
tags: [pytest, conftest, fixtures, GROMACS, export, e2e]
---

# Phase e2e-export-test Plan 01: Shared Conftest Fixtures Summary

**One-liner:** 13 pytest fixtures for all 6 structure types, mock QFileDialog/QMessageBox dialogs, and incremental chain dependencies across the full E2E export pipeline.

## Dependency Graph

- **requires:** quickice.structure_generation.types (Candidate, InterfaceStructure, HydrateStructure, HydrateConfig, HydrateLatticeInfo, MoleculeIndex, IonStructure, SoluteStructure, CustomMoleculeStructure, CustomMoleculeConfig), quickice.ranking.types (RankedCandidate), quickice.structure_generation.moleculetype_registry (MoleculetypeRegistry)
- **provides:** tests/test_output/conftest.py — all shared fixtures for E2E export tests (plans 02-08)
- **affects:** Plans 02-08 of e2e-export-test phase (all import from this conftest)

## Tech Stack

- **added:** None (pytest, numpy already in project)
- **patterns:** Factory fixtures for mock dialogs, incremental chain fixtures for dependency injection

## Key Files

- **created:**
  - `tests/test_output/conftest.py` (499 lines) — All 13 shared fixtures
- **modified:** None

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create conftest.py with all structure and mock fixtures | 9638be0 | tests/test_output/conftest.py |

## Fixtures Delivered

| # | Fixture Name | Type | Description |
|---|-------------|------|-------------|
| 1 | `simple_candidate` | Candidate | 1-molecule ice (3 atoms: O, H, H) |
| 2 | `ranked_candidate` | RankedCandidate | Wraps simple_candidate, rank=1 |
| 3 | `simple_hydrate_config` | HydrateConfig | sI lattice, ch4 guest, 1x1x1 supercell |
| 4 | `simple_hydrate_structure` | HydrateStructure | 2 water + 1 CH4 (13 atoms) |
| 5 | `simple_interface` | InterfaceStructure | 2 ice + 2 water, no guests (14 atoms) |
| 6 | `interface_with_ch4_guests` | InterfaceStructure | Extends simple_interface + 1 CH4 (19 atoms) |
| 7 | `interface_with_thf_guests` | InterfaceStructure | 2 ice + 2 water + 1 THF (27 atoms) |
| 8 | `custom_structure` | CustomMoleculeStructure | Interface + 1 ethanol from etoh.itp (23 atoms) |
| 9 | `solute_structure` | SoluteStructure | 1 CH4 solute with registry (5 atoms) |
| 10 | `ion_structure` | IonStructure | 2 water + 1 Na + 1 Cl (10 atoms) |
| 11 | `mock_save_dialog` | Factory | export.py QFileDialog/QMessageBox mock |
| 12 | `mock_hydrate_save_dialog` | Factory | hydrate_export.py QFileDialog/QMessageBox mock |
| 13 | `mock_cancel_dialog` | Factory | Cancelled QFileDialog simulation |

## Decisions Made

1. **No QApplication fixture** — Export tests don't need a running Qt event loop. Exporters only use QFileDialog/QMessageBox as static method calls, fully mocked.
2. **Factory pattern for mock dialogs** — Returns `(save_path, dialog_patch, mb_patch)` tuples so tests control filename and module path.
3. **custom_structure uses etoh.itp** — Points to existing `quickice/data/custom/etoh.itp` (9 atoms per ethanol) rather than creating temp files.
4. **solute_structure uses interface_with_ch4_guests** — Ensures `interface.guest_nmolecules > 0` triggers guest ITP code path in solute export.
5. **All positions are numpy arrays** — gromacs_writer accesses positions with numpy indexing; lists would fail.
6. **Incremental chain fixtures** — `custom_structure(simple_interface)`, `solute_structure(interface_with_ch4_guests)`, `ion_structure(simple_interface)` — each builds on parent, matching real app workflow.

## Deviations from Plan

None — plan executed exactly as written.

## Next Phase Readiness

- All 13 fixtures available for plans 02-08
- Chain dependencies correctly set up: interface → custom → solute → ion
- Mock dialog fixtures cover both export.py and hydrate_export.py module paths
- etoh.itp verified to exist at `quickice/data/custom/etoh.itp`
- All dataclass constructors validated with smoke tests

## Metrics

- **duration:** 97 seconds
- **completed:** 2026-05-22
