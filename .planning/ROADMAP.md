# QuickIce Roadmap

**Project:** QuickIce - Condition-based Ice Structure Generation

---

## Milestones

- ✅ **v1.0 MVP** — Phases 1-7 (shipped 2026-03-29)
- ✅ **v1.1 Hotfix** — Phase 7.1 (shipped 2026-03-31)

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

**Full details:** [.planning/milestones/v1-ROADMAP.md](./milestones/v1-ROADMAP.md)

</details>

<details>
<summary>✅ v1.1 Hotfix (Phase 7.1) — SHIPPED 2026-03-31</summary>

- [x] Phase 7.1: Fix Performance & Critical Bugs (4/6 plans) — completed 2026-03-31
  - 7.1-04 discarded (KDTree optimization sufficient)
  - 7.1-06 deferred (verify references first)

**Key fixes:**
- Ice XV pressure range corrected (950-2100 MPa)
- Ice Ic detection before Ice Ih fallback
- Path traversal protection
- O(n²)→O(n log n) KDTree optimization
- Exception handling with proper logging

**Full details:** [.planning/milestones/v1.1-ROADMAP.md](./milestones/v1.1-ROADMAP.md)

</details>

---

## Next Milestone

🚧 **v2.0 GUI Application** — Planned

Target features:
- Interactive phase diagram (click to select T,P)
- Textbox input for options
- Info window with citations for ice phases
- 3D structure viewer (stick/ball + hydrogen bonds)
- Save/export options

---

## Progress

| Phase | Milestone | Status | Completed |
|-------|-----------|--------|-----------|
| 1 - Input Validation | v1.0 | ✅ Complete | 2026-03-26 |
| 2 - Phase Mapping | v1.0 | ✅ Complete | 2026-03-27 |
| 3 - Structure Generation | v1.0 | ✅ Complete | 2026-03-26 |
| 4 - Ranking | v1.0 | ✅ Complete | 2026-03-26 |
| 5 - Output | v1.0 | ✅ Complete | 2026-03-27 |
| 5.1 - Missing Ice Phases | v1.0 | ✅ Complete | 2026-03-27 |
| 6 - Documentation | v1.0 | ✅ Complete | 2026-03-28 |
| 7 - Audit & Correctness | v1.0 | ✅ Complete | 2026-03-28 |
| 7.1 - Fix Performance & Bugs | v1.1 | ✅ Complete | 2026-03-31 |

---

*Roadmap last updated: 2026-03-31*
