# Phase quick-028 Plan 01: Hydrate Guest Naming Fix Summary

**One-liner:** Fix hydrate guest naming from _HYD to _H suffix with hydrate-specific ITP files for GROMACS topology consistency

---

## Frontmatter

```yaml
phase: quick-028
plan: 01
subsystem: gromacs-export
tags: [gromacs, topology, hydrate, naming, itp]
requires: [v4.0-hydrate-export]
provides: [hydrate-h-suffix, hydrate-specific-itp]
affects: [hydrate-export, interface-export, ion-export]
tech-stack:
  added: []
  patterns: [hydrate-guest-itp-suffix]
key-files:
  created:
    - quickice/data/ch4_hydrate.itp
    - quickice/data/thf_hydrate.itp
    - tests/test_moleculetype_registry.py
  modified:
    - quickice/structure_generation/moleculetype_registry.py
    - quickice/gui/hydrate_export.py
    - quickice/output/gromacs_writer.py
    - quickice/gui/export.py
decisions:
  - id: d1
    choice: Use _H suffix instead of _HYD for hydrate guests
    rationale: Matches _L (liquid) pattern; 5-char GRO format limit; CH4_H and THF_H are concise
  - id: d2
    choice: Create separate hydrate-specific ITP files (ch4_hydrate.itp, thf_hydrate.itp)
    rationale: ITP moleculetype name must match .top [molecules] entry exactly; base ch4.itp defines moleculetype 'ch4' which doesn't match CH4_H
  - id: d3
    choice: All three exporters (hydrate, interface, ion) use _hydrate.itp and get_hydrate_guest_residue_name()
    rationale: Interface and ion guests originate from hydrate cages, so they need hydrate ITP files too
metrics:
  duration: 4m
  completed: 2026-05-16
```

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create hydrate-specific ITP files and update registry suffix | 2c6e4c4 | ch4_hydrate.itp, thf_hydrate.itp, moleculetype_registry.py, test_moleculetype_registry.py |
| 2 | Update hydrate export to use hydrate-specific ITP files and update gromacs_writer | 52c73e5 | hydrate_export.py, gromacs_writer.py, export.py |

---

## What Was Done

### Task 1: Hydrate ITP files and registry update

- Created `ch4_hydrate.itp` with moleculetype `CH4_H` and resname `CH4_H` (following ch4_liquid.itp pattern)
- Created `thf_hydrate.itp` with moleculetype `THF_H` and resname `THF_H` (following thf_liquid.itp pattern)
- Updated `MoleculetypeRegistry` to change `_HYD` → `_H` suffix in all docstrings, examples, RESERVED_NAMES, and `register_hydrate_guest()` method
- Added `test_moleculetype_registry.py` with 7 tests covering _H suffix, reserved names, and exclusion of old _HYD

### Task 2: Export pipeline updates

- Added `_get_hydrate_guest_itp_path()` to both `hydrate_export.py` and `export.py`
- Added `get_hydrate_guest_residue_name()` to `gromacs_writer.py` (reads CH4_H/THF_H from hydrate ITP files)
- Updated `MOLECULE_TO_GROMACS` dict: ch4 → ch4_hydrate.itp, thf → thf_hydrate.itp
- Updated `write_interface_top_file()`: includes `{guest_type}_hydrate.itp`, uses `get_hydrate_guest_residue_name()`
- Updated `write_ion_top_file()`: includes `{guest_type}_hydrate.itp`, uses `get_hydrate_guest_residue_name()`
- Updated `write_interface_gro_file()` and `write_ion_gro_file()`: guest residue names use hydrate variant
- Updated `InterfaceGROMACSExporter` and `IonGROMACSExporter` in export.py: copy `_hydrate.itp` files

---

## Verification Results

| # | Check | Result |
|---|-------|--------|
| 1 | `MoleculetypeRegistry.register_hydrate_guest('CH4') == 'CH4_H'` | ✓ Pass |
| 2 | `get_hydrate_guest_residue_name('ch4') == 'CH4_H'` | ✓ Pass |
| 3 | `ch4_hydrate.itp` contains `CH4_H` (7 occurrences) | ✓ Pass |
| 4 | `thf_hydrate.itp` contains `THF_H` (15 occurrences) | ✓ Pass |
| 5 | No `_HYD` references in source (only `FALLBACK_HYDRATE_NAMES` variable name) | ✓ Pass |
| 6 | All moleculetype tests pass (8/8) | ✓ Pass |

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Next Phase Readiness

- Hydrate exports now produce self-consistent GROMACS topology
- `_H` suffix pattern mirrors `_L` (liquid) pattern consistently
- Future guest types (CO2, H2) can follow same pattern: create `{guest}_hydrate.itp` with `{GUEST}_H` moleculetype
