# QuickIce State

**Project:** QuickIce - ML-based Ice Structure Generation  
**Core Value:** Generate plausible ice structure candidates quickly for given thermodynamic conditions  
**Current Focus:** Phase 5 Output in progress, OutputResult types established

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
| Phase | 5 of 7 (Output) |
| Plan | 2 of 6 in current phase |
| Status | In progress |
| Last activity | 2026-03-26 - Completed 05-02-PLAN.md (PDB Writer) |
| Progress Bar | ██████████████▌░░░░░░ 74% (14 plans complete) |

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
| Diversity inverted in combined score | 1 - norm_diversity to maintain lower=better convention | Approved (04-03) |
| Default equal weights (1:1:1) | Simple starting point, users can customize | Approved (04-03) |
| Test fixtures with explicit positions | Avoids random inf energy scores, ensures reproducibility | Approved (04-04) |
| Empty list raises ValueError | Documents expected behavior, no silent handling | Approved (04-04) |
| Remove GenIce submodule | Using pip-installed genice2 (v2.2.13.1), submodule was outdated and unused | Approved (quick-001) |
| OutputResult follows RankingResult pattern | Consistency across phases, clean module structure | Approved (05-01) |
| Flexible dict types for validation/summary | Extensible for future validation metrics and statistics | Approved (05-01) |
| HETATM for water molecules | Standard PDB practice for non-standard residues | Approved (05-02) |
| Top 10 candidates written | Reasonable output size, matches user expectations | Approved (05-02) |
| Element symbols right-justified | Follows PDB format specification | Approved (05-02) |

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

**Last Session:** 2026-03-26T18:25:36Z
**Last Completed:** Phase 5 Plan 2 - PDB Writer

**Next Session:** Continue Phase 5 - Output (Plan 3: Validator)

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
- [x] Phase 4: Ranking — COMPLETE (verified 34/34 tests)
  - [x] 04-01: Ranking data structures
  - [x] 04-02: Scoring functions
  - [x] 04-03: Ranking integration
  - [x] 04-04: Ranking tests
- [ ] Phase 5: Output
  - [x] 05-01: Output types (OutputResult dataclass)
  - [x] 05-02: PDB Writer
  - [ ] 05-03: Validator
  - [ ] 05-04: Phase diagram generation
  - [ ] 05-05: Output integration
  - [ ] 05-06: Output tests
- [ ] Phase 6: Documentation
- [ ] Phase 7: Audit & Correctness

---

## Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 001 | Remove redundant GenIce submodule | 2026-03-27 | manual | N/A |

---

*State updated: 2026-03-26*
