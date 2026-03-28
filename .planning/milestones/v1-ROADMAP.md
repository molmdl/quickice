# Milestone v1: MVP

**Status:** ✅ SHIPPED 2026-03-29
**Phases:** 01-07 (plus 05.1)
**Total Plans:** 30+

## Overview

QuickIce is a CLI tool that generates plausible ice structure candidates from temperature (T) and pressure (P) conditions. The pipeline: CLI input → phase mapping → GenIce generation → ranking → PDB output. All v1 requirements map to 7 phases delivering a complete, verifiable MVP.

## Phases

### Phase 01: Input Validation

**Goal**: Users can provide valid temperature, pressure, and molecule count via CLI flags.
**Depends on**: None
**Plans**: 3 plans

Plans:

- [x] 01-01-PLAN.md — Conda env + setup.sh + entry point + package structure
- [x] 01-02-PLAN.md — TDD validators for T/P/nmolecules
- [x] 01-03-PLAN.md — CLI parser + main.py + integration tests

**Details:**
- CLI flags: --temperature, --pressure, --nmolecules
- Validation: T: 0-500K, P: 0-10000 MPa, N: 4-100000
- All 45 tests pass

---

### Phase 02: Phase Mapping

**Goal**: Users receive correct ice polymorph identification for their thermodynamic conditions.
**Depends on**: None
**Plans**: 4 plans

Plans:

- [x] 02-01-PLAN.md — Triple points + IAPWS melting curves (wave 1)
- [x] 02-02-PLAN.md — Solid-solid boundary functions (wave 2)
- [x] 02-03-PLAN.md — TDD curve-based phase lookup (wave 3)
- [x] 02-04-PLAN.md — CLI integration + verification (wave 4)

**Details:**
- Curve-based phase lookup using IAPWS R14-08
- Supports Ice Ih, Ic, II, III, V, VI, VII, VIII
- 50 tests pass

---

### Phase 03: Structure Generation

**Goal**: Users receive valid ice structure coordinates from GenIce for their selected phase.
**Depends on**: Phase 2
**Plans**: 2 plans

Plans:

- [x] 03-01-PLAN.md — TDD phase mapper (types + phase_id → GenIce lattice mapping + supercell calculation)
- [x] 03-02-PLAN.md — IceStructureGenerator with GenIce integration + generate_candidates function

**Details:**
- GenIce integration for coordinate generation
- 10 candidates generated per query
- 54 tests pass

---

### Phase 04: Ranking

**Goal**: Candidates are ranked by relevance to user's T,P conditions using knowledge-based scoring.
**Depends on**: Phase 3
**Plans**: 4 plans

Plans:

- [x] 04-01-PLAN.md — Ranking types (RankedCandidate, RankingResult dataclasses)
- [x] 04-02-PLAN.md — Scoring functions (energy, density, diversity)
- [x] 04-03-PLAN.md — Integration (rank_candidates + normalization + exports)
- [x] 04-04-PLAN.md — Testing (comprehensive test coverage)

**Details:**
- Energy scoring: O-O distance deviation from 0.276nm
- Density scoring: match expected density at T,P
- Diversity scoring: unique polymorphs preferred
- 34 tests pass

---

### Phase 05: Output

**Goal**: Users receive 10 usable PDB files ready for molecular visualization or analysis.
**Depends on**: Phase 4
**Plans**: 7 plans

Plans:

- [x] 05-01-PLAN.md — Output types (OutputResult dataclass)
- [x] 05-02-PLAN.md — PDB writer with TDD (CRYST1 records, coordinate conversion)
- [x] 05-03-PLAN.md — Validator with TDD (space group, atomic overlap with PBC)
- [x] 05-04-PLAN.md — Phase diagram verification (PNG, SVG, text outputs)
- [x] 05-05-PLAN.md — Output orchestrator (coordinates PDB writer, validator, diagram)
- [x] 05-06-PLAN.md — CLI integration (--output, --no-diagram flags, end-to-end checkpoint)
- [x] 05-07-PLAN.md — Fix phase diagram axes and curve-based filling

**Details:**
- PDB format with CRYST1 record
- 10 ranked candidates output
- Space group validation via spglib
- Optional phase diagram visualization

---

### Phase 05.1: Add Missing Ice Phases (INSERTED)

**Goal**: Extend phase mapping to include Ice IX, XI, X, XV for comprehensive coverage.
**Depends on**: Phase 5
**Plans**: 3 plans

Plans:

- [x] 05.1-01-PLAN.md — Triple points + boundary curves for Ice XI, IX, X, XV (wave 1)
- [x] 05.1-02-PLAN.md — Update phase lookup to detect new phases + tests (wave 2)
- [x] 05.1-03-PLAN.md — Extend phase diagram for new phases (wave 3)

**Details:**
- Ice XI: T<72K at low P (proton-ordered Ih)
- Ice IX: T<140K, P=200-400 MPa (proton-ordered III)
- Ice X: P>30 GPa (symmetrized hydrogen bonds)
- Ice XV: T=80-108K, P≈1.1 GPa (proton-ordered VI)
- All 12 ice phases now supported

---

### Phase 06: Documentation

**Goal**: Users understand how to use the tool, interpret results, and know this is a "pure vibe coding project."
**Depends on**: None
**Plans**: 2 plans

Plans:

- [x] 06-01-PLAN.md — README.md update with disclaimer, overview, installation, quick start
- [x] 06-02-PLAN.md — docs/ folder (CLI reference, ranking methodology, principles)

**Details:**
- README with "pure vibe coding project" disclaimer
- docs/cli-reference.md (315 lines)
- docs/ranking.md (241 lines)
- docs/principles.md (237 lines)

---

### Phase 07: Audit & Correctness

**Goal**: Codebase and documentation are audited for consistency, scientific correctness, efficiency, safety, proper citations, and accuracy.
**Depends on**: Phase 6
**Plans**: 5 plans

Plans:

- [x] 07-01-PLAN.md — Citation audit and fix (wave 1)
- [x] 07-02-PLAN.md — Documentation consistency audit and fix (wave 1)
- [x] 07-03-PLAN.md — Scientific correctness audit (wave 2)
- [x] 07-04-PLAN.md — Code consistency and safety audit (wave 2)
- [x] 07-05-PLAN.md — Create audit report (wave 3)

**Details:**
- Citations verified with DOIs
- Code quality verified
- Scientific correctness verified
- AUDIT-REPORT.md created

---

## Milestone Summary

**Key Decisions:**

- CLI-only interface (Rationale: Keep it simple, fast to use)
- PDB output format (Rationale: Standard, universal compatibility)
- Ranking approach (Rationale: Research phase determined knowledge-based scoring)
- Use only Python libraries in current conda environment

**Issues Resolved:**

- Fixed polygon overlap errors near phase boundaries (switched to curve-based approach)
- Extended phase coverage from 8 to 12 ice phases
- Fixed citation errors (GenIce2 DOI, spglib, Ice XV references)
- Phase diagram axes fixed (T on X, P on Y with log scale)

**Issues Deferred:**

- None - all v1 requirements completed

**Technical Debt Incurred:**

- Public API incomplete: validators not exported from quickice.validation (minor)

---

_For current project status, see .planning/ROADMAP.md_

---

## Usage Guidelines

<guidelines>
**When to create milestone archives:**
- After completing all phases in a milestone (v1.0, v1.1, v2.0, etc.)
- Triggered by complete-milestone workflow
- Before planning next milestone work

**Archive location:**

- Saved to `.planning/milestones/v{VERSION}-ROADMAP.md`

**After archiving:**

- Update ROADMAP.md to collapse completed milestone in `<details>` tag
- Update PROJECT.md to brownfield format with Current State section
- Continue phase numbering in next milestone (never restart at 01)
</guidelines>
