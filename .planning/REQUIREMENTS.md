# Requirements: QuickIce v2.1.1 Phase Diagram Data Update

**Defined:** 2026-04-08
**Core Value:** Generate plausible ice structure candidates quickly with intuitive visual interface

## v2.1.1 Requirements

Bugfix phase to correct phase diagram triple point data per IAPWS R14-08(2011) and Journaux et al. (2019, 2020).

### Triple Point Data Updates

- [x] **DATA-01**: Update Ih-III-Liquid triple point (251.165 K, 209.9 MPa) — was 207.5 MPa
- [x] **DATA-02**: Update Ih-II-III triple point (238.45 K, 212.9 MPa) — was 238.55 K
- [x] **DATA-03**: Update II-III-V triple point (249.4 K, 355.5 MPa) — was (248.85 K, 344.3 MPa) [Journaux 2019]
- [x] **DATA-04**: Update III-V-Liquid triple point (256.164 K, 350.1 MPa) — was 346.3 MPa
- [x] **DATA-05**: Update II-V-VI triple point (201.9 K, 670.8 MPa) — was (218.95 K, 620.0 MPa) [Journaux 2019]
- [x] **DATA-06**: Update V-VI-Liquid triple point (273.31 K, 632.4 MPa) — was 625.9 MPa
- [x] **DATA-07**: Update VI-VII-Liquid triple point (355.0 K, 2216.0 MPa) — was (354.75 K, 2200.0 MPa)
- [x] **DATA-08**: Update VI-VII-VIII triple point (278.15 K, 2100.0 MPa) — was 278.0 K

### New Phase Region

- [x] **NEW-01**: Add Ice Ic polygon (metastable cubic ice, 72-150 K, 0-100 MPa)
- [x] **NEW-02**: Register Ice Ic in phase lookup function `_build_phase_polygon_from_curves()`

### Code Updates

- [x] **CODE-01**: Update melting curve Pref values (lines 109, 122, 135, 149, 150 in ice_boundaries.py)
- [x] **CODE-02**: Update PHASE_POLYGONS vertices using corrected triple points
- [x] **CODE-03**: Update documentation comments in lookup.py
- [x] **CODE-04**: Update test comments in test_phase_mapping.py

## Out of Scope

| Feature | Reason |
|---------|--------|
| Other metastable phases (IV, XII, XIII) | User requested Ice Ic only |
| Validation testing with MD | Visualization-focused, no physics validation |
| GUI changes | Data-only update |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 15 | Complete |
| DATA-02 | Phase 15 | Complete |
| DATA-03 | Phase 15 | Complete |
| DATA-04 | Phase 15 | Complete |
| DATA-05 | Phase 15 | Complete |
| DATA-06 | Phase 15 | Complete |
| DATA-07 | Phase 15 | Complete |
| DATA-08 | Phase 15 | Complete |
| NEW-01 | Phase 15 | Complete |
| NEW-02 | Phase 15 | Complete |
| CODE-01 | Phase 15 | Complete |
| CODE-02 | Phase 15 | Complete |
| CODE-03 | Phase 15 | Complete |
| CODE-04 | Phase 15 | Complete |

**Coverage:**
- v2.1.1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-08*
*Last updated: 2026-04-08 — Phase 15 complete*
