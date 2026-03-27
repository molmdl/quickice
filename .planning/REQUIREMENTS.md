# Requirements: QuickIce

**Defined:** 2026-03-26
**Core Value:** Generate plausible ice structure candidates quickly for given thermodynamic conditions

## v1 Requirements

### Input Parameters

- [ ] **INPUT-01**: CLI accepts temperature (K) via --temperature flag
- [ ] **INPUT-02**: CLI accepts pressure (MPa) via --pressure flag
- [ ] **INPUT-03**: CLI accepts molecule count via --nmolecules flag
- [ ] **INPUT-04**: Input validation (T: 0-500K, P: 0-10000 MPa, N: 4-100000)

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

- [ ] **DOC-01**: README noting "pure vibe coding project"
- [ ] **DOC-02**: Usage documentation with examples
- [ ] **DOC-03**: Principles explanation
- [ ] **DOC-04**: Explanation of outcomes and ranking

## v2 Requirements

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

Which phases cover which requirements. Updated during roadmap creation.

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
| DOC-01 | Phase 6 | Pending |
| DOC-02 | Phase 6 | Pending |
| DOC-03 | Phase 6 | Pending |
| DOC-04 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24 ✓
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-26*
*Last updated: 2026-03-27 after Phase 5 completion*
