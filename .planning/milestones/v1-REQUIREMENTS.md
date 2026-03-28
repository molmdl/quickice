# Requirements Archive: v1.0 MVP

**Archived:** 2026-03-29
**Status:** ✅ SHIPPED

This is the archived requirements specification for v1.0.
For current requirements, see `.planning/REQUIREMENTS.md` (created for next milestone).

---

# Requirements: QuickIce

**Defined:** 2026-03-26
**Core Value:** Generate plausible ice structure candidates quickly for given thermodynamic conditions

## v1 Requirements

### Input Parameters

- [x] **INPUT-01**: CLI accepts temperature (K) via --temperature flag
- [x] **INPUT-02**: CLI accepts pressure (MPa) via --pressure flag
- [x] **INPUT-03**: CLI accepts molecule count via --nmolecules flag
- [x] **INPUT-04**: Input validation (T: 0-500K, P: 0-10000 MPa, N: 4-100000)

### Phase Mapping

- [x] **PHASE-01**: Rule-based T,P → ice polymorph lookup table
- [x] **PHASE-02**: Support common ice phases (Ice Ih, Ic, II, III, V, VI, VII, VIII)
- [x] **PHASE-03**: Phase diagram data structure (YAML or JSON)

### Structure Generation

- [x] **GEN-01**: GenIce integration for coordinate generation
- [x] **GEN-02**: Generate multiple candidates per query (10 total)
- [x] **GEN-03**: Handle molecule count → supercell sizing
- [x] **GEN-04**: Generate valid hydrogen bond network (via GenIce)

### Ranking

- [x] **RANK-01**: Energy-based ranking of candidates
- [x] **RANK-02**: Density-based scoring (match expected density at T,P)
- [x] **RANK-03**: Diversity scoring (different polymorphs preferred)
- [x] **RANK-04**: Combined ranking score output

### Output

- [x] **OUT-01**: PDB format output with CRYST1 record
- [x] **OUT-02**: 10 PDB files per query (one per candidate)
- [x] **OUT-03**: Rank suffix in filename (e.g., ice_candidate_01.pdb)
- [x] **OUT-04**: Basic validation (no atomic overlap check)
- [x] **OUT-05**: Valid space group verification via spglib

### Documentation

- [x] **DOC-01**: README noting "pure vibe coding project"
- [x] **DOC-02**: Usage documentation with examples
- [x] **DOC-03**: Principles explanation
- [x] **DOC-04**: Explanation of outcomes and ranking

### Audit & Correctness

- [x] **AUDIT-01**: Citation verification and fix
- [x] **AUDIT-02**: Documentation consistency audit
- [x] **AUDIT-03**: Scientific correctness verification
- [x] **AUDIT-04**: Code quality and safety audit
- [x] **AUDIT-05**: Comprehensive audit report

## v3 Requirements

### ML Enhancement

- **ML-01**: ML-based phase prediction (trained on known phase diagram)
- **ML-02**: Confidence scoring for each candidate

### Performance

- **PERF-01**: Parallel candidate generation
- **PERF-02**: Vectorized ranking computation

### Extended Features

- **EXT-01**: CIF output format
- **EXT-02**: Phase identification (match to known ice polymorph)
- **EXT-03**: GRO output format

## Out of Scope

| Feature | Reason |
|---------|--------|
| Physics-based ranking | Using ML/vibe approach per initial prompt |
| Structure analysis | Generation only, no analysis |
| Visualization | CLI-first, no GUI |
| Python API | CLI only |
| Non-water systems | Water ice only |
| New ML model training | Use existing ML models if needed |
| GUI interface | CLI only per requirements |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INPUT-01 | Phase 1 | Complete |
| INPUT-02 | Phase 1 | Complete |
| INPUT-03 | Phase 1 | Complete |
| INPUT-04 | Phase 1 | Complete |
| PHASE-01 | Phase 2 | Complete |
| PHASE-02 | Phase 2 | Complete |
| PHASE-03 | Phase 2 | Complete |
| GEN-01 | Phase 3 | Complete |
| GEN-02 | Phase 3 | Complete |
| GEN-03 | Phase 3 | Complete |
| GEN-04 | Phase 3 | Complete |
| RANK-01 | Phase 4 | Complete |
| RANK-02 | Phase 4 | Complete |
| RANK-03 | Phase 4 | Complete |
| RANK-04 | Phase 4 | Complete |
| OUT-01 | Phase 5 | Complete |
| OUT-02 | Phase 5 | Complete |
| OUT-03 | Phase 5 | Complete |
| OUT-04 | Phase 5 | Complete |
| OUT-05 | Phase 5 | Complete |
| DOC-01 | Phase 6 | Complete |
| DOC-02 | Phase 6 | Complete |
| DOC-03 | Phase 6 | Complete |
| DOC-04 | Phase 6 | Complete |
| AUDIT-01 | Phase 7 | Complete |
| AUDIT-02 | Phase 7 | Complete |
| AUDIT-03 | Phase 7 | Complete |
| AUDIT-04 | Phase 7 | Complete |
| AUDIT-05 | Phase 7 | Complete |

**Coverage:**
- v1 requirements: 29 total
- Mapped to phases: 29 ✓
- Unmapped: 0 ✓

---

## Milestone Summary

**Shipped:** 29 of 29 v1 requirements
**Adjusted:** 0
**Dropped:** 0

**Additional achievements:**
- Extended phase support from 8 to 12 ice phases (Ice IX, XI, X, XV)
- Added spglib space group validation
- Added phase diagram visualization

---

*Archived: 2026-03-29 as part of v1.0 milestone completion*
