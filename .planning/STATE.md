# QuickIce State

**Project:** QuickIce - ML-based Ice Structure Generation  
**Core Value:** Generate plausible ice structure candidates quickly for given thermodynamic conditions  
**Current Focus:** Phase 4 Ranking in progress

---

## Project Reference

| Attribute | Value |
|-----------|-------|
| Core Value | Generate plausible ice structure candidates quickly for given thermodynamic conditions |
| Mode | yolo |
| Depth | Comprehensive (7 phases) |
| Approach | Pure "vibe coding" — no physics simulations |

---

## Current Position

| Field | Value |
|-------|-------|
| Phase | 4 of 7 (Ranking) |
| Plan | 2 of 4 in current phase |
| Status | In progress |
| Last activity | 2026-03-26 - Completed 04-02-PLAN.md |
| Progress Bar | ███████████████████████████████ 77% (10 plans complete) |

---

## Phase Summary

| Phase | Name | Goal | Requirements |
|-------|------|------|--------------|
| 1 | Input Validation | Valid CLI flags | 4 |
| 2 | Phase Mapping | T,P → polymorph | 3 |
| 3 | Structure Generation | Valid GenIce output | 4 |
| 4 | Ranking | Scored candidates | 4 |
| 5 | Output | PDB files + phase diagram | 5 |
| 6 | Documentation | User guides | 4 |
| 7 | Audit & Correctness | Quality assurance | 5 |

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Total v1 Requirements | 29 |
| Mapped to Phases | 29 |
| Coverage | 100% |
| Phases | 7 |

---

## Accumulated Context

### Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| 7-phase structure | Natural delivery boundaries from requirements | Approved |
| Comprehensive depth | 7 phases derived from requirements, fits standard range | Approved |
| No horizontal layers | Each phase delivers complete capability | Enforced |
| Float rejection for nmolecules | No silent truncation, explicit integer requirement | Approved (01-02) |
| Return types: float for T/P, int for nmolecules | Matches physical units and user expectations | Approved (01-02) |
| CLI description without ML-guided | Users requested removal of ML reference | Approved (01-03) |
| Entry point: python quickice.py | Standard Python script execution | Approved (01-03) |
| JSON for phase boundary data | Easy to read, modify, and version control | Approved (02-01) |
| Custom exception hierarchy | Provides specific context for debugging | Approved (02-01) |
| Comprehensive phase data | Density and crystal form needed for downstream use | Approved (02-01) |
| Phase order: high pressure first | Ensures correct matching at overlapping boundaries | Approved (02-02) |
| Return dict with 5 keys | Provides complete phase info including input conditions | Approved (02-02) |
| Class + convenience function | Class for repeated lookups, function for convenience | Approved (02-02) |
| CLI prints phase info after inputs | Maintains consistent output order | Approved (02-03) |
| UnknownPhaseError returns exit code 1 | Standard Unix convention for errors | Approved (02-03) |
| Error to stderr, output to stdout | Allows proper stream separation | Approved (02-03) |
| TIP3P water model | Standard for MD simulations, 3 atoms per molecule | Approved (03-02) |
| Seeds 1000-1009 for diversity | Deterministic diversity, reproducible generation | Approved (03-02) |
| GROMACS format for output | Easily parseable, standard in MD community | Approved (03-02) |
| Strict depolarization | Ensures physically valid structures | Approved (03-02) |
| GenIce unit cell definitions | Different from conventional cells, requires mapping adjustment | Approved (03-02) |
| Combined score: lower=better | Consistent with energy scoring convention | Approved (04-01) |
| Flexible metadata dicts | dict[str, Any] for extensibility | Approved (04-01) |
| Manual PBC implementation | scipy.spatial.distance.cdist doesn't handle PBC | Approved (04-02) |
| Energy score scaled by 100 | Makes typical deviations (0.001-0.01 nm) visible | Approved (04-02) |
| Default density 0.9167 g/cm³ | Ice Ih density when not in metadata | Approved (04-02) |

### Dependencies Identified

| Phase | Depends On |
|-------|------------|
| Phase 2 | Phase 1 |
| Phase 3 | Phase 2 |
| Phase 4 | Phase 3 |
| Phase 5 | Phase 4 |
| Phase 7 | Phase 6 |

### Roadmap Evolution

- Phase 7 added: Audit Codebase, Documentation, Scientific Correctness, Safety & Citations

### Research Context

- GenIce provides valid ice structure generation (essential — pure ML fails ice rules)
- Hybrid approach: ML for ranking, GenIce for coordinates
- Phase diagram mapping via rule-based lookup (accurate for known phases)
- spglib for crystal symmetry validation

---

## Session Continuity

**Last Session:** 2026-03-26T16:57:22Z
**Last Completed:** Phase 4 Plan 2 - Scoring Functions

**Next Session:** Continue Phase 4 - Plan 03 (Ranking integration)

---

## Todo

- [x] Phase 1: Input Validation — COMPLETE (verified 16/16)
- [x] Phase 2: Phase Mapping — COMPLETE (verified 28/28)
  - [x] 02-01: Phase mapping data structure
  - [x] 02-02: Phase lookup implementation
  - [x] 02-03: Phase mapping integration
- [x] Phase 3: Structure Generation — COMPLETE (verified 10/10)
  - [x] 03-01: Phase ID to GenIce lattice mapping + supercell calculation
  - [x] 03-02: GenIce integration + generate_candidates
- [ ] Phase 4: Ranking
  - [x] 04-01: Ranking data structures
  - [x] 04-02: Scoring functions
  - [ ] 04-03: Diversity calculation
  - [ ] 04-04: Ranking integration
- [ ] Phase 5: Output
- [ ] Phase 6: Documentation
- [ ] Phase 7: Audit & Correctness

---

*State updated: 2026-03-26*
