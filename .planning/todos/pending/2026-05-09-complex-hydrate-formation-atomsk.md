---
created: 2026-05-09T17:30
updated: 2026-06-14
title: Complex hydrate generation (GenIce2 plugins + polycrystal)
area: feature
research_status: comprehensive
files: []
---

## Problem

Current hydrate generation relies on GenIce2 which handles simple clathrate hydrates (sI, sII, sH). Complex hydrate structures (e.g., filled ice, semiclathrates, mixed phases) may require alternative approaches.

## Research Completed ✅

**Extensive research completed 2026-06-12.** Key finding: **atomsk is NOT needed for structure generation** — GenIce2's Python API already supports everything needed. Atomsk has niche value for polycrystalline assembly only, but Python can replace it.

### Research Files

| File | Content | Key Finding |
|------|---------|-------------|
| `.planning/research/future-ml/complex-hydrate-atomsk/FEASIBILITY.md` | 520-line feasibility assessment | GenIce2 covers 95%+ use cases; atomsk adds zero hydrate generation |
| `.planning/research/future-ml/complex-hydrate-atomsk/POLYCRYSTAL-FEASIBILITY.md` | 534-line Python polycrystal feasibility | Build in Python (~300 LOC), don't use atomsk |
| `.planning/research/future-ml/complex-hydrate-atomsk/SYNTHESIS.md` | Synthesis & phased roadmap | 3-phase pipeline: Free Wins → CIF Import → Custom Plugins |
| `.planning/research/future-ml/complex-hydrate-atomsk/SUMMARY.md` | Executive summary | Verdict: YES with phased approach, no atomsk dependency |
| `.planning/research/future-ml/complex-hydrate-atomsk/STACK.md` | Tech stack analysis | GenIce2 plugin architecture fully programmable |
| `.planning/research/future-ml/complex-hydrate-atomsk/FEATURES.md` | Feature gap & demand analysis | Filled ices, CO₂/H₂ guests, mixed occupancy = "free wins" |
| `.planning/research/future-ml/complex-hydrate-atomsk/PITFALLS.md` | 15 numbered pitfalls | Key: single-occupancy-per-cage constraint |
| `.planning/research/future-ml/complex-hydrate-atomsk/ARCHITECTURE.md` | UI & code architecture | 3 new mode entries in QStackedWidget |
| `.planning/research/future-ml/complex-hydrate-atomsk/ATOMSK-HYDRATE-DEEPDIVE.md` | Atomsk hydrate paper analysis | 7+ papers use atomsk for polycrystal, NOT generation |

### Key Conclusions from Research

1. **Atomsk NOT needed for generation** — GenIce2 already supports: filled ices (c0te, c1te, c2te), CO₂/H₂/ethane guests, mixed occupancy, per-cage assignment, CIF import, custom lattice plugins
2. **Atomsk's ONLY value** = `--polycrystal` mode for Voronoi-tessellated polycrystalline hydrate assembly
3. **Python can replace atomsk** for polycrystal assembly (~300 LOC using scipy.spatial.Voronoi + cKDTree)
4. **Python polycrystal is BETTER** than atomsk: multi-phase (sI+sII+ice grains), native GRO output, molecular integrity at boundaries

### Recommended Roadmap

| Phase | Scope | Effort | Priority |
|-------|-------|--------|----------|
| 1: "Free Wins" | Add filled ice lattices, CO₂/H₂/ethane guests, water model dropdown, mixed occupancy UI | ~300-400 LOC | CRITICAL — 80% of value for 20% of effort |
| 2: CIF Import | genice2-cif integration, assess_cages, guest placement from detected cages | MEDIUM | HIGH |
| 3: Custom Plugins | Lattice/molecule plugin wizard, semiclathrate presets | MEDIUM | MEDIUM |
| 4: Polycrystal | Python Voronoi polycrystal builder (NOT atomsk) | ~300 LOC | MEDIUM |

## Status

**Research COMPLETE.** Ready for milestone planning (`/gsd-new-milestone`).

**Title updated:** Was "Explore complex hydrate formation using atomsk" — now reflects that atomsk is excluded from the approach.
