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
| GRO-01 | Phase 14 | Pending |
| GRO-02 | Phase 14 | Pending |
| GRO-03 | Phase 14 | Pending |
| GRO-04 | Phase 14 | Pending |
| GRO-05 | Phase 14 | Pending |
| GRO-06 | Phase 14 | Pending |
| GRO-07 | Phase 14 | Pending |
| GRO-08 | Phase 14 | Pending |

**Coverage:**
- v2.1 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-05*
*Last updated: 2026-04-05 after initial definition*
