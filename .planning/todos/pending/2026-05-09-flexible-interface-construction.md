---
created: 2026-05-09T17:30
updated: 2026-06-14
title: Support flexible interface construction modes
area: feature
research_status: comprehensive
files:
  - quickice/interface/
  - quickice/interface_panel.py
---

## Problem

Current interface construction has limited flexibility:
- Slab placement is fixed (ice on top, water below)
- Cannot mix different hydrate types in same system
- Cannot combine ice + hydrate in same system

## Research Completed ✅

**Extensive research completed 2026-06-12.** Verdict: YES with phased delivery.

### Research Files

| File | Content | Key Finding |
|------|---------|-------------|
| `.planning/research/future-ml/flexible-interface-construction/FEASIBILITY.md` | 353-line feasibility assessment | 3 features feasible, 2 blocked, 1 conditional |
| `.planning/research/future-ml/flexible-interface-construction/SYNTHESIS.md` | Synthesis & phasing | Phase 1: asymmetric+face → Phase 2: P3 fix → Phase 3: ice+hydrate |
| `.planning/research/future-ml/flexible-interface-construction/SUMMARY.md` | Executive summary | All 3 feasible features are code-grounded via source analysis |
| `.planning/research/future-ml/flexible-interface-construction/STACK.md` | Tech stack | GenIce2 `one[hh]` vs `1h` lattice names for face selection |
| `.planning/research/future-ml/flexible-interface-construction/FEATURES.md` | Feature gap analysis | Most MD studies use asymmetric slab, not symmetric |
| `.planning/research/future-ml/flexible-interface-construction/PITFALLS.md` | 15 numbered pitfalls | **P3 is CRITICAL:** dual MW virtual site computation corrupts GRO |
| `.planning/research/future-ml/flexible-interface-construction/ARCHITECTURE.md` | UI & code architecture | Named mode presets, QStackedWidget pattern |
| `.planning/research/future-ml/flexible-interface-construction/PLAN.md` | Implementation plan | Phased delivery sequence |

### Feature Feasibility Verdicts

| Feature | Verdict | Effort | Scientific Demand | Risk |
|---------|---------|-------|-------------------|------|
| Asymmetric slab | ✅ FEASIBLE | LOW (~180 LOC) | HIGH — most common study type | LOW |
| Crystal face selection (basal/prismatic) | ✅ FEASIBLE (conditional) | LOW-MED (~55 LOC) | MEDIUM | MEDIUM (triclinic risk) |
| Ice + hydrate triple interface | ✅ FEASIBLE (conditional) | MED-HIGH (~420 LOC) | MEDIUM | HIGH (P3 export corruption) |
| Mixed sI + sII hydrate | ❌ BLOCKED | N/A | NONE — 31% lattice mismatch | N/A |
| General layer UI | ⏸ CONDITIONAL | HIGH | NONE — defer until demand | HIGH |

### Critical Blocker: P3 (Dual MW Virtual Site)

For ice+hydrate mode, the GROMACS export pipeline MUST be fixed first. Current code detects atoms-per-molecule from the first ice-region atom, which fails when ice (3-atom TIP3P) and hydrate (4-atom TIP4P) coexist. **Fix:** Use per-molecule `MoleculeIndex.mol_type` in export loop (types.py already stores this).

### Recommended Roadmap

| Phase | Scope | Effort | Priority |
|-------|-------|--------|----------|
| 1: Asymmetric Slab + Crystal Face | New mode, face QComboBox, validation formula update | LOW | CRITICAL |
| 2: Export Pipeline Hardening | P3 fix: per-molecule MW detection in gromacs_writer.py | LOW | HIGH (prerequisite for Phase 3) |
| 3: Ice + Hydrate Triple Interface | Dual GenIce2 calls, LCM box dims, dual-source UI | MED-HIGH | MEDIUM |

### Open Research Questions

- [ ] Verify `one[hh]` with diagonal reshape produces orthogonal cells (P7 risk)
- [ ] Verify current QuickIce exposes prismatic face (not basal) — may affect defaults
- [ ] Verify MoleculeIndex.mol_type is populated for all molecule sources (P3 prerequisite)

## Status

**Research COMPLETE.** Ready for milestone planning (`/gsd-new-milestone`).
