# QuickIce Roadmap

**Project:** QuickIce - ML-based Ice Structure Generation  
**Generated:** 2026-03-26  
**Depth:** Comprehensive (7 phases derived from natural boundaries)

---

## Overview

QuickIce is a CLI tool that generates plausible ice structure candidates from temperature (T) and pressure (P) conditions. The pipeline: CLI input → phase mapping → GenIce generation → ranking → PDB output. All v1 requirements map to 6 phases delivering a complete, verifiable MVP.

---

## Phase Structure

### Phase 1: Input Validation

**Goal:** Users can provide valid temperature, pressure, and molecule count via CLI flags.

**Requirements:** INPUT-01, INPUT-02, INPUT-03, INPUT-04

**Plans:** 3 plans in 3 waves

**Success Criteria:**

1. User can specify temperature in Kelvin via --temperature flag
2. User can specify pressure in MPa via --pressure flag
3. User can specify molecule count via --nmolecules flag
4. Invalid inputs are rejected with clear error messages (T: 0-500K, P: 0-10000 MPa, N: 4-100000)

**Dependencies:** None

**Plans:**
- [x] 01-01-PLAN.md — Conda env + setup.sh + entry point + package structure
- [x] 01-02-PLAN.md — TDD validators for T/P/nmolecules
- [x] 01-03-PLAN.md — CLI parser + main.py + integration tests

---

### Phase 2: Phase Mapping

**Goal:** Users receive correct ice polymorph identification for their thermodynamic conditions.

**Requirements:** PHASE-01, PHASE-02, PHASE-03

**Plans:** 4 plans in 4 waves (curve-based replan)

**Status:** ✓ Complete

**Success Criteria:**

1. ✓ User can query with T,P and receive polymorph identification
2. ✓ Lookup table correctly maps T,P to phases using curved boundaries (IAPWS R14-08)
3. ✓ Common ice phases (Ih, Ic, II, III, V, VI, VII, VIII) are supported
4. ✓ No polygon overlap errors near phase boundaries

**Dependencies:** None

**Plans:**
- [x] 02-01-PLAN.md — Triple points + IAPWS melting curves (wave 1)
- [x] 02-02-PLAN.md — Solid-solid boundary functions (wave 2)
- [x] 02-03-PLAN.md — TDD curve-based phase lookup (wave 3)
- [x] 02-04-PLAN.md — CLI integration + verification (wave 4)

---

### Phase 3: Structure Generation

**Goal:** Users receive valid ice structure coordinates from GenIce for their selected phase.

**Requirements:** GEN-01, GEN-02, GEN-03, GEN-04

**Plans:** 2 plans in 2 waves

**Success Criteria:**

1. GenIce generates valid hydrogen bond networks (exactly 4 H-bonds per molecule)
2. 10 candidates generated per query
3. Molecule count properly determines supercell sizing
4. Generated coordinates are parseable and valid

**Dependencies:** Phase 2 (phase must be identified before generation)

**Plans:**
- [x] 03-01-PLAN.md — TDD phase mapper (types + phase_id → GenIce lattice mapping + supercell calculation)
- [x] 03-02-PLAN.md — IceStructureGenerator with GenIce integration + generate_candidates function

---

### Phase 4: Ranking

**Goal:** Candidates are ranked by relevance to user's T,P conditions using ML/vibe scoring.

**Requirements:** RANK-01, RANK-02, RANK-03, RANK-04

**Plans:** 4 plans in 4 waves

**Success Criteria:**

1. Candidates ranked by energy (lower energy preferred)
2. Candidates scored by density match to expected density at T,P
3. Diversity scoring rewards different polymorphs
4. Combined ranking score available for each candidate

**Dependencies:** Phase 3 (candidates must exist before ranking)

**Plans:**
- [x] 04-01-PLAN.md — Ranking types (RankedCandidate, RankingResult dataclasses)
- [x] 04-02-PLAN.md — Scoring functions (energy, density, diversity)
- [x] 04-03-PLAN.md — Integration (rank_candidates + normalization + exports)
- [x] 04-04-PLAN.md — Testing (comprehensive test coverage)

---

### Phase 5: Output

**Goal:** Users receive 10 usable PDB files ready for molecular visualization or analysis. Optional phase diagram visualization shows user's T,P point.

**Requirements:** OUT-01, OUT-02, OUT-03, OUT-04, OUT-05

**Success Criteria:**

1. Each candidate saved as valid PDB file with CRYST1 record
2. 10 PDB files output per query with rank suffix (_01 to _10)
3. No atomic overlap in output structures
4. Valid space group verified via spglib
5. Optional: --diagram flag outputs phase diagram with T,P point marked

**Dependencies:** Phase 4 (ranking needed before output)

**Plans:** 7 plans in 5 waves

**Plans:**
- [x] 05-01-PLAN.md — Output types (OutputResult dataclass)
- [x] 05-02-PLAN.md — PDB writer with TDD (CRYST1 records, coordinate conversion)
- [x] 05-03-PLAN.md — Validator with TDD (space group, atomic overlap with PBC)
- [x] 05-04-PLAN.md — Phase diagram verification (PNG, SVG, text outputs - already implemented)
- [x] 05-05-PLAN.md — Output orchestrator (coordinates PDB writer, validator, diagram)
- [ ] 05-06-PLAN.md — CLI integration (--output, --no-diagram flags, end-to-end checkpoint)
- [ ] 05-07-PLAN.md — Fix phase diagram axes and curve-based filling (T on X, P on Y with log scale)

**Archived:**
- 05-04-PLAN.md.superseded — Original diagram plan (replaced by verification)
- 05-08-PLAN.md.superseded — Unified diagram (diagram already uses PHASE_POLYGONS)

---

### Phase 6: Documentation

**Goal:** Users understand how to use the tool, interpret results, and know this is a "pure vibe coding project."

**Requirements:** DOC-01, DOC-02, DOC-03, DOC-04

**Success Criteria:**

1. README clearly notes "pure vibe coding project" disclaimer
2. Usage documentation with CLI examples provided
3. Principles explanation (why ML/vibe approach, not physics simulation)
4. Explanation of outcomes and ranking methodology

**Dependencies:** None (can run in parallel or post-MVP)

---

### Phase 7: Audit Codebase, Documentation, Scientific Correctness, Safety & Citations

**Goal:** Codebase and documentation are audited for consistency, scientific correctness, efficiency, safety, proper citations, and accuracy. Issues identified are fixed.

**Requirements:** AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-05

**Success Criteria:**

1. Code consistency verified across all modules (naming, patterns, error handling)
2. Scientific correctness validated (physics units, formulas, GenIce usage)
3. Efficiency reviewed (no obvious bottlenecks, proper algorithms)
4. Safety checks in place (input validation, file handling, no silent failures)
5. Citations verified and real scientific sources cited where appropriate

**Dependencies:** Phase 6 (documentation complete before audit)

---

## Progress Table

| Phase | Goal | Requirements | Status |
|-------|------|--------------|--------|
| 1 - Input Validation | Valid CLI flags | INPUT-01 to INPUT-04 | ✓ Complete |
| 2 - Phase Mapping | T,P → polymorph | PHASE-01 to PHASE-03 | ✓ Complete |
| 3 - Structure Generation | Valid GenIce output | GEN-01 to GEN-04 | ✓ Complete |
| 4 - Ranking | Scored candidates | RANK-01 to RANK-04 | ✓ Complete |
| 5 - Output | PDB files | OUT-01 to OUT-05 | Pending |
| 6 - Documentation | User guides | DOC-01 to DOC-04 | Pending |
| 7 - Audit & Correctness | Quality assurance | AUDIT-01 to AUDIT-05 | Pending |

---

## Coverage Validation

| Phase | Requirements Covered |
|-------|---------------------|
| Phase 1 | INPUT-01, INPUT-02, INPUT-03, INPUT-04 |
| Phase 2 | PHASE-01, PHASE-02, PHASE-03 |
| Phase 3 | GEN-01, GEN-02, GEN-03, GEN-04 |
| Phase 4 | RANK-01, RANK-02, RANK-03, RANK-04 |
| Phase 5 | OUT-01, OUT-02, OUT-03, OUT-04, OUT-05 |
| Phase 6 | DOC-01, DOC-02, DOC-03, DOC-04 |
| Phase 7 | AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-05 |

**Coverage:** 29/29 v1 requirements mapped ✓

---

## Notes

- **Philosophy:** Pure "vibe coding" approach — no physics simulations. GenIce provides valid coordinate generation; ML/vibe methods handle ranking.
- **Architecture:** Sequential pipeline (CLI → Validator → Phase Mapper → GenIce → Ranker → PDB Writer)
- **Anti-Patterns Avoided:** No horizontal layers, no project management artifacts, no vague success criteria

---

*Roadmap generated: 2026-03-26*