# Requirements: QuickIce v2.1 GROMACS Export

**Defined:** 2026-04-05
**Core Value:** Generate plausible ice structure candidates quickly with intuitive visual interface

## v2.1 Requirements

Requirements for GROMACS simulation workflow support.

### GROMACS Export

- [ ] **GRO-01**: User can export current structure as .gro coordinate file
- [ ] **GRO-02**: User can export current structure as .top topology file
- [ ] **GRO-03**: tip4p-ice.itp force field file is bundled as application resource
- [ ] **GRO-04**: Generated .gro file contains 4-point water coordinates (O, H1, H2, MW)
- [ ] **GRO-05**: Generated .top file includes proper moleculetype directive
- [ ] **GRO-06**: Exported files pass GROMACS validation (gmx check)
- [ ] **GRO-07**: Export menu provides "Export for GROMACS" option
- [ ] **GRO-08**: Export generates all three files (.gro, .top, .itp) in one action

**Note on tip4p-ice.itp (GRO-03):**
- `[ atomtypes ]` section is commented out in provided file
- Handling depends on force field context:
  - **Option A**: Uncomment with defaults (self-contained .itp, no additional ff needed)
  - **Option B**: Insert into user-provided ffnonbonded.itp
  - **Option C**: Bundle complete ff folder
- Default for v2.1: Option A (self-contained)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-candidate batch export | Single structure export sufficient for v2.1 |
| Force field variants | TIP4P-ICE only for MVP |
| GROMACS executable integration | File generation only, no MD execution |
| Energy minimization | Structure generation only |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GRO-01 | Phase 14 | Complete |
| GRO-02 | Phase 14 | Complete |
| GRO-03 | Phase 14 | Complete |
| GRO-04 | Phase 14 | Complete |
| GRO-05 | Phase 14 | Complete |
| GRO-06 | Phase 14 | Complete |
| GRO-07 | Phase 14 | Complete |
| GRO-08 | Phase 14 | Complete |

**Coverage:**
- v2.1 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-05*
*Last updated: 2026-04-06 after phase 14 verification*
