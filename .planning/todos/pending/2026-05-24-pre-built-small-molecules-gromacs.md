---
created: 2026-05-24T03:17
updated: 2026-06-14
title: Pre-built small molecules for custom mol with GROMACS format
area: feature
research_status: partial
files:
  - quickice/gui/custom_molecule_panel.py
  - quickice/gui/custom_molecule_worker.py
---

## Problem

Users currently must supply their own .gro/.itp files for custom molecule insertion. Providing a library of pre-built small molecules (e.g. from AMBER geostd set at https://ambermd.org/downloads/amber_geostd.tar.bz2) converted to GROMACS format would lower the barrier to entry and improve usability. A search/browse function in the GUI would let users pick molecules instead of manually preparing files.

## Research Status: Partial ✅

**Research plan designed and partially executed 2026-06-12.** License and format conversion research complete; architecture and pitfalls documented; relevance filter done.

### Research Files

| File | Content | Key Finding |
|------|---------|-------------|
| `.planning/research/future-ml/pre-built-small-molecules/RESEARCH-PLAN.md` | 483-line 5-agent research plan | 3-wave structure: License + Format → Relevance → Architecture + Pitfalls |
| `.planning/research/future-ml/pre-built-small-molecules/LICENSE.md` | License & redistribution analysis | AmberTools GPL-3.0 since 2023; PDB CCD is public domain; complex legal landscape |
| `.planning/research/future-ml/pre-built-small-molecules/FORMAT-CONVERSION.md` | AMBER→GROMACS conversion | Full algorithm documented; unit conversions defined; pairs generation specified |
| `.planning/research/future-ml/pre-built-small-molecules/RELEVANCE-FILTER.md` | Hydrate-relevant molecule selection | PDB geostd "THF" is NOT simple THF; many simple guests may be missing |
| `.planning/research/future-ml/pre-built-small-molecules/ARCHITECTURE.md` | Component design | Converter → data files → GUI panel → inserter → export pipeline |
| `.planning/research/future-ml/pre-built-small-molecules/PITFALLS.md` | Numbered pitfalls | Atom type collisions, 1-4 scaling incompatibility AMBER vs TIP4P-ICE |
| `.planning/research/future-ml/pre-built-small-molecules/SUMMARY.md` | Final synthesis | Go/no-go depends on license resolution |
| `.planning/research/future-ml/pre-built-small-molecules/SUMMARY-A.md` | License research summary | Redistribution of converted files may be legally safe (output ≠ derivative) |
| `.planning/research/future-ml/pre-built-small-molecules/SUMMARY-B.md` | Format conversion summary | Feasible: mol2+frcmod → .gro+.itp, ~200-400 LOC converter |
| `.planning/research/future-ml/pre-built-small-molecules/SUMMARY-C.md` | Relevance filter summary | ~50-200 molecules sweet spot; simple guests likely missing from geostd |

### Key Conclusions from Research

1. **Format conversion is feasible** — ~200-400 LOC Python converter (mol2+frcmod → .gro+.itp)
2. **QuickIce already uses GAFF2 atom types** — conversion simpler than expected
3. **License is the main blocker** — AmberTools is GPL-3.0 since 2023; output of GPL programs is generally NOT GPL-tainted, but legal clarity needed
4. **PDB geostd "THF" is NOT simple THF** — many simple hydrate guest molecules may be absent from the database
5. **1-4 scaling incompatibility** — AMBER fudgeLJ/fudgeQQ differ from TIP4P-ICE defaults; `[defaults]` is system-wide in GROMACS

### Remaining Research

- [ ] Finalize license go/no-go decision (need user input on risk tolerance)
- [ ] Decide: bundle converted files vs. ship converter-only vs. hybrid approach
- [ ] Identify which simple molecules are missing from geostd and need separate sources

## Status

**Research PARTIALLY COMPLETE.** License decision needed before milestone planning.
