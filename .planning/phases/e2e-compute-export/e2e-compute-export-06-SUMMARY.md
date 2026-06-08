---
phase: e2e-compute-export
plan: "06"
subsystem: gromacs-writer
tags: [gromacs, grompp, atomtypes, moleculetype, dedup, GAFF2, fix]
---

# Phase e2e-compute-export Plan 06: Fix TOP Writers + Add Grompp Helpers Summary

**One-liner:** Fixed three GROMACS-simulation-blocking bugs (missing solute atomtypes, moleculetype name mismatch, duplicate atomtypes) and added grompp validation helpers

## Dependency Graph

- **requires:** e2e-compute-export-01 (e2e_export_helpers.py), e2e-compute-export-03 (ion export + BUG I5 workaround), e2e-compute-export-05 (chain export tests)
- **provides:** Fixed TOP writers that pass gmx grompp, grompp validation helpers (_stage_itp_files, run_gmx_grompp, MDP_PATH)
- **affects:** e2e-compute-export-07 (uses grompp helpers for validation tests)

## Tech Stack

### Added
None (uses existing GROMACS 2023.5 for grompp validation)

### Patterns
- Hardcoded GAFF2 atomtypes replacing ITP-parsing approach (solute ITPs have [atomtypes] pre-commented)
- parse_itp_file() for ITP moleculetype name extraction in [molecules] section
- Atomtype deduplication via tracking set before writing custom molecule atomtypes
- GROMACS grompp validation helpers (stage ITPs, run grompp, MDP path constant)

## Key Files

### Created
None

### Modified
- `quickice/output/gromacs_writer.py` — Fixed write_ion_top_file, write_solute_top_file, write_custom_molecule_top_file with three bug fixes; added parse_itp_file import
- `tests/e2e_export_helpers.py` — Added MDP_PATH, _stage_itp_files(), run_gmx_grompp()
- `tests/test_e2e_chain_export_1.py` — Updated TOP [molecules] assertions from "MOL" to "etoh"
- `tests/test_e2e_chain_export_2.py` — Updated comment about moleculetype naming
- `tests/test_e2e_cross_chain_invariants.py` — Updated comment about moleculetype naming
- `tests/test_e2e_custom_export.py` — Updated TOP [molecules] assertions; added top_mol_name
- `tests/test_e2e_ion_export.py` — Updated TOP [molecules] assertions from "MOL" to "etoh"
- `tests/test_e2e_solute_export.py` — Updated TOP [molecules] assertions; added top_mol_name

## Bug Fixes

### Bug 1: Solute atomtypes not written (CRITICAL — blocks gmx grompp)

**Problem:** ch4_liquid.itp and thf_liquid.itp have [atomtypes] pre-commented, so parse_itp_atomtypes() returns empty. Writer writes comment "; CH4 atom types defined in ch4_liquid.itp" instead of actual atomtype definitions. GROMACS error: "Atomtype c3 not found".

**Fix:** Replace ITP-parsing approach with hardcoded GAFF2 atomtypes. Use combined `needs_ch4_atomtypes` and `needs_thf_atomtypes` flags that cover both guest and solute molecules. Applied to write_ion_top_file, write_solute_top_file.

### Bug 2: Moleculetype name mismatch (CRITICAL — blocks gmx grompp)

**Problem:** [molecules] section writes "MOL" (registry default) but etoh.itp defines moleculetype "etoh". GROMACS requires [molecules] name to match ITP [moleculetype] name. GROMACS error: "No such moleculetype MOL".

**Fix:** Parse actual moleculetype name from ITP file using parse_itp_file() and use it in [molecules]. GRO residue name "MOL" remains unchanged (GROMACS doesn't require residue names to match). Applied to write_ion_top_file, write_solute_top_file, write_custom_molecule_top_file.

### Bug 3: Duplicate atomtypes (WARNING — causes gmx grompp warnings)

**Problem:** When THF guest GAFF2 section writes hc/h1 AND etoh custom molecule writes hc/h1, GROMACS warns about redefined atomtypes.

**Fix:** Track written atomtype names in a set (_written_atomtypes) after writing TIP4P-ICE, ion, and GAFF2 atomtypes. When writing custom molecule atomtypes, skip any already-written names. Applied to write_ion_top_file, write_solute_top_file, write_custom_molecule_top_file.

## Grompp Validation Helpers

Added to `tests/e2e_export_helpers.py`:

- **MDP_PATH**: Path to tests/em.mdp for energy minimization grompp
- **_stage_itp_files(top_path, workspace)**: Copies all #include-referenced ITPs to workspace with atomtypes commented out (using comment_out_atomtypes_in_itp). Skips ion.itp (already generated).
- **run_gmx_grompp(workspace, ...)**: Runs gmx grompp in workspace and returns (exit_code, stderr). Accepts maxwarn parameter (default 5).

## Grompp Verification Results

| Chain | Description | Exit Code | Status |
|-------|-------------|-----------|--------|
| F6 | Interface→Solute(CH4)→Ion | 0 | PASS |
| F1 | Interface→Custom→Solute→Ion | 0 | PASS |
| F4 | Hydrate→Interface→Custom→Solute→Ion | 0 | PASS |

F4 staged ITPs: tip4p-ice.itp, thf_hydrate.itp, etoh.itp, thf_liquid.itp

No duplicate atomtypes in F4 TOP [atomtypes]: OW_ice, HW_ice, MW, NA, CL, os, c5, hc, h1, c3, oh, ho (hc, h1, c3 correctly deduped between THF GAFF2 and etoh custom)

## Bridge Test Updates

Existing bridge tests that asserted "MOL" in TOP [molecules] section were updated to expect "etoh" (the ITP moleculetype name). GRO residue name assertions remain "MOL" (unchanged — GROMACS doesn't require GRO residue names to match ITP moleculetype names).

All 228 bridge tests pass (was 116 before Plan 06 updates; additional 112 from earlier e2e-api-workflow tests that also pass through unchanged).

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Hardcoded GAFF2 atomtypes over ITP parsing | Solute liquid ITPs (ch4_liquid.itp, thf_liquid.itp) have [atomtypes] pre-commented; parsing returns empty |
| parse_itp_file() for moleculetype name | Reliable extraction of [moleculetype] name from ITP; falls back to registry default on failure |
| Dedup set for atomtypes | Prevents GROMACS warnings about redefined atomtypes when guest and custom share GAFF2 types |
| GRO residue name stays "MOL" | GROMACS doesn't require GRO residue names to match ITP moleculetype names; changing would break GRO/TOP consistency |
| _stage_itp_files comments out [atomtypes] | ITPs bundled in data/ may have active [atomtypes] sections (e.g., etoh.itp); these must be commented since types are in main .top |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing bridge tests for correct [molecules] name**

- **Found during:** Task 2, running pytest after fixes
- **Issue:** Existing tests asserted "MOL" in TOP [molecules] section, but Bug 2 fix correctly changed this to "etoh" (ITP moleculetype name). Tests were testing the BUG behavior, not correct behavior.
- **Fix:** Updated 6 test files to expect "etoh" in TOP [molecules] section while keeping "MOL" for GRO residue name assertions. Added `top_mol_name = "etoh"` variable where needed.
- **Files modified:** tests/test_e2e_chain_export_1.py, test_e2e_ion_export.py, test_e2e_custom_export.py, test_e2e_solute_export.py, test_e2e_chain_export_2.py, test_e2e_cross_chain_invariants.py
- **Commit:** b57ca74

## Authentication Gates

None — all tasks executed autonomously.

## Verification Results

All verification criteria met:
1. ✅ F6 (Interface→Solute(CH4)→Ion) gmx grompp exits with code 0
2. ✅ F1 (Interface→Custom→Solute→Ion) gmx grompp exits with code 0
3. ✅ F4 (Hydrate→Interface→Custom→Solute→Ion) gmx grompp exits with code 0
4. ✅ _stage_itp_files() copies all referenced ITPs with atomtypes commented
5. ✅ run_gmx_grompp() returns exit code 0 on valid input
6. ✅ All 228 existing bridge tests still pass

## Next Phase Readiness

- e2e-compute-export-07 can now use MDP_PATH, _stage_itp_files(), and run_gmx_grompp() to add grompp validation tests
- All three GROMACS-simulation-blocking bugs are fixed
- Plan 07 should test F1-F7 chains all pass gmx grompp
