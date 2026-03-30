# QuickIce Roadmap

**Project:** QuickIce - Condition-based Ice Structure Generation

---

## Milestones

- ✅ **v1.0 MVP** — Phases 1-7 (shipped 2026-03-29)

---

## Phase Structure

<details>
<summary>✅ v1.0 MVP (Phases 1-7) — SHIPPED 2026-03-29</summary>

- [x] Phase 1: Input Validation (3/3 plans) — completed 2026-03-26
- [x] Phase 2: Phase Mapping (4/4 plans) — completed 2026-03-27
- [x] Phase 3: Structure Generation (2/2 plans) — completed 2026-03-26
- [x] Phase 4: Ranking (4/4 plans) — completed 2026-03-26
- [x] Phase 5: Output (7/7 plans) — completed 2026-03-27
- [x] Phase 5.1: Add Missing Ice Phases (3/3 plans) — completed 2026-03-27
- [x] Phase 6: Documentation (2/2 plans) — completed 2026-03-28
- [x] Phase 7: Audit & Correctness (5/5 plans) — completed 2026-03-28
- [ ] Phase 7.1: Fix Performance Issues & Critical Bugs (4 plans)
  - [ ] 7.1-01 — Fix lookup.py correctness bugs (C1, C2, PH1, Q1)
  - [ ] 7.1-02 — Fix security and code quality issues (S2, S3, Q2)
  - [ ] 7.1-03 — Fix O(n²) pairwise distance calculations
  - [ ] 7.1-04 — Fix phase diagram performance (P2, P3)

**Full details:** [.planning/milestones/v1-ROADMAP.md](./milestones/v1-ROADMAP.md)

</details>

---

## Progress

| Phase | Goal | Requirements | Status |
|-------|------|--------------|--------|
| 1 - Input Validation | Valid CLI flags | INPUT-01 to INPUT-04 | ✅ Complete |
| 2 - Phase Mapping | T,P → polymorph | PHASE-01 to PHASE-03 | ✅ Complete |
| 3 - Structure Generation | Valid GenIce output | GEN-01 to GEN-04 | ✅ Complete |
| 4 - Ranking | Scored candidates | RANK-01 to RANK-04 | ✅ Complete |
| 5 - Output | PDB files | OUT-01 to OUT-05 | ✅ Complete |
| 5.1 - Missing Ice Phases | IX, XI, X, XV | Extended | ✅ Complete |
| 6 - Documentation | User guides | DOC-01 to DOC-04 | ✅ Complete |
| 7 - Audit & Correctness | Quality assurance | AUDIT-01 to AUDIT-05 | ✅ Complete |
| 7.1 - Fix Performance & Bugs | Fix critical bugs + O(n²) perf | C1, C2, S2, S3, P2, P3 | 📋 Planned |

---

*Roadmap archived from v1.0 development. See milestones/ for full phase details.*
