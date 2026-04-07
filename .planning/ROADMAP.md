# Milestone v2.1: GROMACS Export

**Status:** GAP CLOSURE
**Phases:** 14
**Total Requirements:** 8
**Completion Date:** 2026-04-07

## Overview

Enable direct GROMACS simulation workflow from QuickIce by generating valid .gro, .top, and bundled force field files.

## Phases

### Phase 14: GROMACS Export

**Goal:** Users can export ice structures as valid GROMACS input files ready for molecular dynamics simulation

**Requirements:** GRO-01, GRO-02, GRO-03, GRO-04, GRO-05, GRO-06, GRO-07, GRO-08

**Dependencies:** None (uses existing structure generation)

**Success Criteria (Observable User Behaviors):**

1. **User can export current structure as .gro file** — User selects "Export for GROMACS" from menu, receives .gro file with correct 4-point water coordinates (O, H1, H2, MW) in GROMACS format

2. **User can export current structure as .top topology file** — Exported .top file contains proper [ moleculetype ], [ atoms ], [ bonds ] directives that GROMACS can parse

3. **tip4p-ice.itp force field is bundled** — Application bundles tip4p-ice.itp file as resource; export action includes this file in output directory

4. **Single export action generates all files** — One "Export for GROMACS" menu option produces .gro, .top, and .itp files simultaneously

5. **Exported files pass GROMACS validation** — User can run `gmx check` on exported .gro file without errors; .top file loads in GROMACS without topology warnings

---

## Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| GRO-01: .gro coordinate export | Phase 14 | Complete |
| GRO-02: .top topology export | Phase 14 | Complete |
| GRO-03: Bundle tip4p-ice.itp | Phase 14 | Complete |
| GRO-04: 4-point water coords | Phase 14 | Complete |
| GRO-05: Proper moleculetype | Phase 14 | Complete |
| GRO-06: GROMACS validation | Phase 14 | Complete |
| GRO-07: Export menu option | Phase 14 | Complete |
| GRO-08: All three files | Phase 14 | Complete |

**Coverage:** 8/8 requirements mapped ✓

**Plans:** 8 plans (6 complete, 2 gap closure)

**Plan list:**
- [x] 14-01-PLAN.md — GROMACS file writers and resource bundling
- [x] 14-02-PLAN.md — Add GROMACS export to GUI
- [x] 14-03-PLAN.md — Add GROMACS export to CLI
- [x] 14-04-PLAN.md — Fix PDB residue numbering and molecule count documentation
- [x] 14-05-PLAN.md — Add candidate selection for GROMACS export
- [x] 14-06-PLAN.md — Add GROMACS export to in-app help
- [ ] 14-07-PLAN.md — Fix GROMACS export crash and clarify water model (Wave 1)
- [ ] 14-08-PLAN.md — Update documentation and GUI labels (Wave 2)

**Gap Closure Items:**
1. CRITICAL: Fix AttributeError crash in GROMACS export (temperature_spinbox missing)
2. Clarify water model selection (TIP4P-ICE) in GUI
3. Add TIP4P-ICE reference citation to README/docs
4. Update "Number of molecules" label to "Minimum number of molecules"

---

## Technical Notes

- GenIce2 provides `.gro` output via `-f gromacs` flag
- TIP4P-ICE force field parameters from Abascal et al. 2005
- Custom .itp file required (not built into GROMACS)
- Topology generation requires parsing ice structure to extract molecules
- `[ atomtypes ]` handling: uncomment with defaults for self-contained .itp (Option A)

---

_For current project status, see STATE.md_