---
phase: 36-cli-feature-parity
plan: 09
subsystem: cli
tags: [cli, pipeline, ion, insertion, source-modes, attribute-propagation]

# Dependency graph
requires:
  - phase: 36-03
    provides: _run_ion_step stub with report_progress
  - phase: 36-05
    provides: _run_source_step and _run_interface_step for prerequisite structures
  - phase: 36-08
    provides: _run_custom_step and _run_solute_step for custom/solute source modes
provides:
  - _run_ion_step() with 3 source modes (interface, custom, solute)
  - FIX #4: Custom source offset includes guest_atom_count
  - Attribute propagation for solute source (solute_type, solute_positions, etc.)
  - Attribute propagation for custom source (custom_molecule_positions with correct offset)
  - Custom molecule forward-propagation from solute source
  - Liquid volume calculation from water_nmolecules * 0.0299
affects: [36-10, 36-11, cli-pipeline-integration]

# Tech tracking
tech-stack:
  added: []
patterns:
  - "Duck-typing attribute propagation on InterfaceStructure at runtime (mirrors GUI MainWindow)"
  - "3-source-mode pattern for ion insertion (interface, custom, solute)"
  - "Conditional custom molecule propagation from solute source (Custom → Solute → Ion chain)"

key-files:
  created: []
  modified:
    - quickice/cli/pipeline.py

key-decisions:
  - "FIX #4: offset = ice_atom_count + water_atom_count + guest_atom_count (NOT just ice+water)"
  - "Duck-typing attribute propagation mirrors GUI exactly — no different abstraction"
  - "Solute source also propagates custom molecules if present (hasattr guard)"
  - "getattr(self.args, 'ion_source', 'interface') for backward-compatible default"
  - "water_nmolecules * 0.0299 for liquid volume (matches GUI pattern)"

patterns-established:
  - "3-source ion insertion pattern matching GUI _on_insert_ions"

# Metrics
duration: 1min
completed: 2026-06-14
---

# Phase 36 Plan 09: Ion Step Implementation Summary

**_run_ion_step() with 3 source modes and attribute propagation, FIX #4 (guest offset)**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-06-14T14:44:39Z
- **Completed:** 2026-06-14T14:45:14Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Implemented _run_ion_step() with 3 source modes: interface, custom, solute
- FIX #4: Custom source offset includes guest_atom_count (ice+water+guest, not just ice+water)
- Solute source propagates solute_type, solute_positions, solute_atom_names, solute_n_molecules, solute_molecule_indices, solute_registry to interface structure
- Solute source also propagates custom molecule attributes if present (Custom → Solute → Ion chain)
- Custom source propagates custom_molecule_positions with correct offset, custom_molecule_atom_names, custom_molecule_count, custom_molecule_moleculetype, custom_gro_path, custom_itp_path
- Duck-typing attribute propagation mirrors GUI MainWindow._on_insert_ions exactly
- Liquid volume calculated from water_nmolecules * 0.0299
- insert_ions called with seed=self.args.seed for reproducibility
- Error handling: ValueError for missing structures and invalid sources

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement _run_ion_step with 3 source modes and attribute propagation** - `4a21d5f` (feat)

## Files Created/Modified
- `quickice/cli/pipeline.py` - _run_ion_step() replacing stub with full implementation

## Decisions Made
- FIX #4: offset = ice_atom_count + water_atom_count + guest_atom_count — previous code used only ice+water, missing guest atoms in the offset calculation
- Duck-typing attribute propagation (setting attributes on InterfaceStructure at runtime) — mirrors GUI MainWindow._on_insert_ions exactly, no different abstraction
- Solute source also propagates custom molecules if hasattr(source, 'custom_molecule_count') and count > 0 — handles Custom → Solute → Ion workflow chain
- getattr(self.args, 'ion_source', 'interface') — backward-compatible default for args namespaces without ion_source
- water_nmolecules * 0.0299 for liquid volume — matches existing GUI pattern and custom step pattern
- seed=self.args.seed in insert_ions() — ensures reproducible ion placement

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Ion step fully implemented with all 3 source modes
- Ready for Plan 36-10 (integration/end-to-end testing) and Plan 36-11
- Pipeline now has all 6 steps functional: source, interface, custom, solute, ion, export

---
*Phase: 36-cli-feature-parity*
*Completed: 2026-06-14*
