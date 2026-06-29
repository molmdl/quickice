# QuickIce State

**Project:** QuickIce - Condition-based Ice Structure Generation
**Core Value:** Generate ready-to-use initial models and topologies for GROMACS for the simulation of ice, hydrates, solutes, and custom molecules in water
**Current Focus:** Phase 38 — Internal Pipeline Refactor

---

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-27)

**Core value:** Generate ready-to-use initial models and topologies for GROMACS for the simulation of ice, hydrates, solutes, and custom molecules in water

**Current focus:** v4.7 Extended Hydrate Generation — Phase 38 Internal Pipeline Refactor

**Tech stack:**
- Python 3.14, PySide6 6.10.2, VTK 9.5.2
- GenIce2 2.2.13.1, spglib, numpy, scipy, iapws
- MVVM architecture with QThread workers
- Unified CLI+GUI entry point (`python -m quickice`)

---

## Current Position

| Field | Value |
|-------|-------|
| Milestone | v4.7 Extended Hydrate Generation |
| Phase | 38 of 48 (Internal Pipeline Refactor) |
| Plan | 04 of 04 complete |
| Status | Phase complete |
| Last activity | 2026-06-29 — Completed 38-04-PLAN.md |

**Progress:** [████░░░░░░] ~40%

---

## Milestone History

### v4.5 Solute & Custom Molecule Insertion (SHIPPED 2026-06-27)
**Phases:** 32-37.2 + e2e-export/api/compute (20 phases, 131 plans)
**Archive:** .planning/milestones/v4.5-ROADMAP.md

### v4.0 Molecule Insertion (SHIPPED 2026-05-01)
**Phases:** 28-31.2 (7 phases, 29 plans)
**Archive:** .planning/milestones/v4.0-ROADMAP.md

### v3.5 Interface Enhancements (SHIPPED 2026-04-13)
**Phases:** 22, 24-27 shipped; Phase 23 deferred

### v3.0 Interface Generation (SHIPPED 2026-04-11)
**Phases:** 16-21 (6 phases, 15 plans)

---

## Accumulated Context

### Decisions

Recent decisions affecting v4.7 work:
- sys.modules injection for custom guests: main-thread registration before HydrateWorker (v4.7)
- _H suffix for hydrate guests via MoleculetypeRegistry (v4.7)
- Reject A/B → sigma/epsilon auto-conversion (v4.7)
- GRO 5-char residue name limit: base names ≤3 chars (v4.7)
- sT' = water-only generation in v4.7 (no cagepos in GenIce2)
- Built-in CO₂/H₂/ethane guests deferred to v4.8+ (force field verification needed)
- Water model selector deferred to v4.8+ (downstream impact)
- **[38-01]** Built-in guest types auto-populate metadata in __post_init__; custom types (Phase 40) must provide explicitly
- **[38-01]** guest_itp_path is NOT auto-populated (only relevant for custom guests)
- **[38-01]** atom_labels uses list copy from GUEST_MOLECULES to avoid shared mutable state
- **[38-03]** GRO residue name validation rejects >5 chars with ValueError (no silent truncation)
- **[38-03]** Validation checks only length, not content; callers must fix names upstream
- **[38-03]** Empty MoleculetypeRegistry fallback (source.upper()) can produce >5 char names — must be caught by validation
- **[38-04]** transform_guest_itp() is unified ITP transformation entry point (atomtypes comment-out + _H suffix + GRO name validation)
- **[38-04]** No [ atoms ] residue name rewriting in transform_guest_itp — deferred to Phase 40 custom guests
- **[38-04]** Hydrate export (GUI+CLI) uses read-transform-write instead of shutil.copy for guest ITPs

### Pending Todos

- [2026-06-20] Decide disposition of 26 rogue pip packages in quickice env (tooling)
- [2026-05-24] Pre-built small molecules for custom mol with GROMACS format (feature)
- [2026-05-16] Install UPX for bundle compression (tooling)
- [2026-05-07] Capture screenshots per Phase 35 suggestions (docs)

### Blockers/Concerns

- ~~GRO `:<5s` overflow (NOT truncation) — must validate at every write entry point~~ **[RESOLVED in 38-03]** validate_gro_residue_name() now called at all 10 GRO write entry points
- `_build_molecule_index` is single-point bottleneck — must refactor before any new guest/water model (addressed in Plan 02)
- Thread safety gap: `sys.modules` injection must happen outside existing `_genice_lock` scope

---

## Session Continuity

Last session: 2026-06-29T14:54:40Z
Stopped at: Completed 38-04-PLAN.md (Phase 38 complete)
Resume file: None
