# QuickIce Roadmap: v2.1.1 Phase Diagram Data Update

**Milestone:** v2.1.1 Phase Diagram Data Update  
**Created:** 2026-04-08  
**Core Value:** Generate plausible ice structure candidates quickly with intuitive visual interface

---

## Overview

This bugfix milestone corrects phase diagram triple point data per IAPWS R14-08(2011) and Journaux et al. (2019, 2020). It also adds the metastable Ice Ic phase region to the phase lookup system. The update ensures users receive scientifically accurate ice phase predictions.

---

## Phases

### Phase 15: Phase Diagram Data Update

**Goal:** Users receive accurate ice phase predictions based on IAPWS R14-08(2011) compliant thermodynamic data

**Dependencies:** None (standalone data fix)

**Plans:** 7 plans (4 initial + 3 gap closure)

Plans:
- [x] 15-01-PLAN.md — Update triple points in both files (DATA-01 to DATA-08)
- [x] 15-02-PLAN.md — Add Ice Ic polygon builder and registration (NEW-01, NEW-02)
- [x] 15-03-PLAN.md — Update PHASE_POLYGONS and MELTING_CURVE_COEFFICIENTS (CODE-01, CODE-02)
- [x] 15-04-PLAN.md — Update documentation comments (CODE-03, CODE-04)
- [x] 15-05-PLAN.md — Fix Ice Ic polygon boundaries (Gap closure: Ice XI overlap)
- [x] 15-06-PLAN.md — Add Ice Ic to CLI export (Gap closure: CLI rendering)
- [x] 15-07-PLAN.md — Fix hardcoded old triple point values (Gap closure: polygon consistency)

**Requirements:**
- DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07, DATA-08
- NEW-01, NEW-02
- CODE-01, CODE-02, CODE-03, CODE-04

**Success Criteria:**

1. Phase lookup returns correct ice phase for any (T,P) input using updated triple point data
2. Ice Ic phase is available for metastable conditions (50-150K, 0-100 MPa)
3. All existing tests pass with corrected triple point values
4. New test validates Ice Ic region boundaries work correctly
5. Phase diagram boundaries reflect updated data accurately

---

## Progress

| Phase | Goal | Status | Requirements |
|-------|------|--------|--------------|
| 15 | Phase Diagram Data Update | Complete | 14 mapped |

---

## Coverage

- **v2.1.1 requirements:** 14 total
- **Mapped to phases:** 14
- **Unmapped:** 0 ✓

---

*Roadmap created: 2026-04-08*