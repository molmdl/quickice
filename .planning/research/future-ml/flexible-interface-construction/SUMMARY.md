# Research Summary: Flexible Interface Construction

**Domain:** Ice-water interface construction for MD simulation
**Researched:** 2026-06-12
**Overall confidence:** HIGH

## Executive Summary

QuickIce's current architecture is extensible — no redesign is needed. The existing QStackedWidget mode-routing pattern, the generic `tile_structure()` / `fill_region_with_water()` pipeline, and the single-SOL GROMACS export convention all generalize cleanly to support new interface configurations. The hardcoded Z-stacking in `slab.py` (bottom-ice → water → top-ice) is the only true structural limitation, and it resolves trivially into a `LayerSpec`-driven loop where each layer carries its type, thickness, source candidate, and Z-range.

The most important finding is that **"slab orientation flip" is physically meaningless under PBC**. Under periodic boundary conditions, the slab repeats infinitely — there is no "top" or "bottom," only the relative ordering of layers. An ice-water-ice sandwich shifted by half a box is the same structure. This is not an implementation limitation; it is a fundamental property of PBC. Implementing a flip control would mislead users into thinking it matters. The real flexibility scientists need is **crystal face selection** (basal vs prismatic face at the interface), which is a GenIce2 lattice name change, not a coordinate flip.

Three features survive the physics+demand filter: **asymmetric slab** (single ice-water interface, table stakes), **crystal face selection** (basal vs prismatic, table stakes), and **ice + hydrate triple interface** (key differentiator, enables dissociation studies). Everything else is either physically meaningless (slab flip), structurally impractical (mixed sI+sII hydrate, 31% lattice mismatch), or premature over-engineering (arbitrary drag-and-drop layer composition UI). The most silently dangerous technical pitfall is P3 — dual MW virtual site computation — where mixing 3-atom ice molecules with 4-atom hydrate molecules in the same GRO file corrupts all subsequent atom indices if the export loop assumes uniform atom count.

## Key Findings

**Stack:** GenIce2 `raw` format + `shift`/`reshape` parameters provide all needed coordinate manipulation; no GenIce2 modifications required. All water models normalize to TIP4P-ICE at export.

**Architecture:** Layer-based assembly engine (`LayerSpec` list → `assemble_layers()` loop) replaces hardcoded Z-stacking. Named mode presets (not general composition) keep UI tractable. Existing QStackedWidget pattern extends naturally.

**Critical pitfall:** P3 — dual MW virtual site computation. When ice (3-atom TIP3P) and hydrate (4-atom TIP4P) SOL molecules coexist in the same GRO file, the export code must detect per-molecule atom count rather than per-region. A single wrong assumption silently corrupts every subsequent atom index. Prevention: use `MoleculeIndex.mol_type` for per-molecule detection in the export loop.

## Implications for Roadmap

Based on research, suggested phase structure for v5.x:

### 1. Phase 1: Asymmetric Slab Mode — table stakes, LOW effort, HIGH demand

- **Addresses:** Single ice-water interface (most common MD study configuration). Reduces computational cost ~40% vs symmetric sandwich for single-interface studies.
- **Avoids:** Pitfall P4 (validation formula break) — update `box_z = ice_thickness + water_thickness` together with InterfaceConfig.
- **Key change:** Skip top ice layer in slab assembly; update validation formula; add `"Asymmetric Slab"` to `mode_combo` QComboBox with new QStackedWidget page.
- **Effort:** ~2-3 days (2 lines of code change for assembly logic + new UI panel + validation update + tests).
- **Risk:** LOW. The change is mechanically simple. The only subtlety is PBC interpretation: under 3D PBC, `ice|water` repeats as `...ice|water|ice|water...` — this IS a symmetric slab. Document that the benefit is reduced atom count (one interface instead of two), not a fundamentally different structure. Vacuum gaps or 2D PBC are user responsibility.

### 2. Phase 2: Crystal Face Selection — real flexibility, LOW-MEDIUM effort

- **Addresses:** Basal (0001) vs prismatic (10-10) face at the ice-water interface. Different faces have different melting rates, growth kinetics, and surface energies — this is a major research variable.
- **Avoids:** Pitfall P7 (triclinic box vectors) — restrict v5.x to orthogonal face options (`1h` and `one[hh]` both produce orthogonal supercells with diagonal reshape).
- **Key change:** Add crystal face QComboBox to all slab-derived panels. GenIce2 `one[hh]` flag already exists and works — just expose in UI. Map: `"Basal (0001)"` → GenIce2 lattice `one[hh]`, `"Primary Prism (10-10)"` → `1h` (current default). Disable dropdown for non-hexagonal ice phases.
- **Effort:** ~2-4 days (UI addition + generator lattice name override + verification of current default face).
- **Risk:** LOW-MEDIUM. Must verify what face the current default `1h` actually exposes (GenIce2 README says axes are "exchanged"). Must also verify that `one[hh]` with QuickIce's diagonal `reshape` produces a valid orthogonal supercell.

### 3. Phase 3: Ice + Hydrate Triple Interface — key differentiator, HIGH demand

- **Addresses:** Ice | hydrate | water triple interface. Enables hydrate dissociation studies from ice surfaces, ice-coated hydrate stability, and ice-surface-mediated hydrate nucleation — all active research areas.
- **Avoids:** Pitfalls P3 (dual MW computation — CRITICAL) and P2 (periodicity mismatch — requires LCM box dimensions). P3 must be fixed FIRST in the export pipeline before any ice+hydrate work begins.
- **Key change:** Multi-source generation: call GenIce2 twice (once for ice, once for hydrate), extract absolute coordinates via raw format, assemble with `LayerSpec`-driven `assemble_layers()`. Dual source selectors embedded in ice+hydrate mode panel (NOT in top-level `source_combo`). Per-molecule `mol_type` detection in GROMACS export loop. LCM box dimension computation for dual-lattice periodicity.
- **Effort:** ~8-15 days (new `layer_assembly.py` module + `ice_hydrate_slab.py` mode + dual-source UI panel + GROMACS export refactor for per-molecule atom count + LCM dimension algorithm + overlap detection across ice-hydrate boundary + comprehensive testing).
- **Risk:** HIGH. This is the most dangerous feature. P3 (dual MW) is a silent data corruption bug if not handled correctly. P2 (periodicity) requires careful LCM math. P8 (cross-layer overlap) is a new check that doesn't exist. P5/P6 (guest naming and atomtype dedup) must be verified for dual-source guests. The `layer_assembly.py` engine must be built and tested first (shared with Phase 1 asymmetric slab).

### 4. Phase 4 (DEFERRED): General Layer Composition UI — over-engineering

- **Only build if demand emerges.** No scientist has asked for arbitrary N-layer composition. Named modes (asymmetric slab, ice+hydrate) cover all known use cases. A general drag-and-drop layer panel is UI complexity without scientific value. If future demand appears, the `LayerSpec` engine from Phase 1/3 already supports it — only the UI would need building.

**Anti-features to explicitly NOT build:**

| Anti-Feature | Why Not |
|--------------|---------|
| Slab orientation flip (ice-on-bottom vs ice-on-top) | Under PBC, these are the same structure shifted by half a box. No physical difference. Implementing it misleads users. |
| Mixed hydrate types (sI + sII) in same box | 31% lattice mismatch. No common supercell below ~10 nm. No published MD study uses this. sI and sII are thermodynamically distinct immiscible phases. |
| sI + sH or sII + sH mixed hydrate | Same lattice mismatch issue. sH has hexagonal symmetry incompatible with cubic sI/sII. |
| Arbitrary drag-and-drop layer ordering UI | Over-engineering. Scientists need 2-3 named configurations, not a general combinatorial system. Most orderings are physically meaningless under PBC. |
| General "any structure for any layer" composition | Would require arbitrary structure loading, incompatible unit cells, intractable validation. Only allow QuickIce-generated sources (ice candidates from Tab 1, hydrate from Tab 2). |
| Water slab in ice (inverse sandwich) | Under PBC, this IS the current ice-water-ice sandwich — just relabeled. Pocket mode already handles water-in-ice for spherical geometries. |

**Phase ordering rationale:**

- **Phase 1 first** because it's the smallest change with the highest demand-to-effort ratio. It also creates `layer_assembly.py`, which Phase 3 depends on. The validation formula fix (P4) must land before any other mode work.
- **Phase 2 second** because it's independent of Phase 1 (different code paths) but lower priority than asymmetric slab. It can overlap with Phase 1 if resources allow. The face verification step is needed before any face-dependent features ship.
- **Phase 3 last** because it depends on the `layer_assembly.py` engine from Phase 1, requires GROMACS export refactoring for per-molecule atom count (P3 fix), and carries the highest risk. The P3 fix is a prerequisite — it must be implemented and tested before any ice+hydrate code is written.
- **Phase 4 deferred** because there is zero evidence of demand. The `LayerSpec` architecture naturally supports it if demand appears later.

**Research flags for phases:**

- **Phase 2:** Needs verification of GenIce2 `1h` vs `one[hh]` axis convention — what face does the current QuickIce slab actually expose at Z? The GenIce2 README says axes are "exchanged" but this must be confirmed by generating both and inspecting the output.
- **Phase 3:** Needs deeper research on GROMACS dual-MW export handling. The current `write_interface_gro_file()` assumes uniform `atoms_per_ice_mol` for the entire ice region. Per-molecule detection via `MoleculeIndex.mol_type` is the recommended approach but has not been prototyped. Also needs testing of ice-hydrate boundary overlap detection — this is a new check that doesn't exist in current code.
- **Phase 3:** Needs domain-expert input on whether the ice-hydrate boundary requires special structural treatment (bond matching, orientation alignment) or if simple layer stacking + energy minimization is sufficient. Literature suggests the boundary is naturally disordered, but this has not been verified for GenIce2-generated structures.

## Quick Wins

The two easiest features that deliver the most value:

1. **Asymmetric slab:** Skip the top ice layer. In `slab.py`, the bottom ice tiling and Z-shift code already work; just omit the top ice call and update the validation formula from `2*ice + water` to `ice + water`. This is ~2 lines of assembly change + a new UI panel + validation update. Delivers the most-requested MD configuration (single interface).

2. **Crystal face:** GenIce2's `one[hh]` lattice flag already produces the basal face on Z. Current QuickIce doesn't expose it. Adding a QComboBox that maps `"Basal (0001)"` → lattice name `one[hh]` and `"Primary Prism (10-10)"` → `1h` is a pure UI + generator-routing change. GenIce2 already does the work; QuickIce just needs to pass the right lattice name.

Both quick wins share a common enabler: the `layer_assembly.py` engine for asymmetric slab, and the crystal face combo for both asymmetric and existing slab modes.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | GenIce2 API analysis from full source code read (genice.py, raw.py, cell.py, plugin.py, lattice plugins). All claims code-verified. |
| Features | HIGH | PBC symmetry is fundamental physics. Scientific demand from arXiv/Google Scholar search + domain knowledge. Anti-features well-supported by lattice mismatch data. |
| Architecture | HIGH | UI patterns from full source code read of interface_panel.py (935 lines), slab.py (641 lines). LayerSpec generalization traced through actual code. PySide6 patterns from existing usage. |
| Pitfalls | HIGH | All 15 pitfalls traced to actual source code (gromacs_writer.py 2000+ lines, slab.py 641 lines, types.py 722 lines, interface_builder.py 354 lines). P3 and P1 are code-verified critical issues. |
| Phase estimates | MEDIUM | Effort estimates based on code analysis, not implementation experience. Phase 3 risk is genuine — dual-MW handling has not been prototyped. |

## Gaps to Address

1. **Current QuickIce crystal face verification:** Need to generate a test slab with `1h` and `one[hh]` and inspect which crystal face is actually at the Z-interface. The GenIce2 README says axes are "exchanged" for `1h`, but this must be verified in QuickIce's actual output. This is a blocking unknown for Phase 2.

2. **Per-molecule MW export prototyping:** The recommended approach for P3 (per-molecule `mol_type` detection in the GRO export loop) needs a proof-of-concept. Current code assumes uniform `atoms_per_ice_mol` per region. The change to per-molecule detection is architecturally clean but must be tested with mixed 3-atom/4-atom input.

3. **Ice-hydrate boundary structural compatibility:** How does the hydrogen-bond network transition from ice Ih to sI at the atomic level? Can a simple layer-stacking approach (no special boundary treatment) produce a structure that energy-minimizes cleanly? Domain-expert input recommended.

4. **Asymmetric slab PBC semantics:** Under 3D PBC, `ice|water` is a symmetric slab. Is this acceptable to users, or do they expect a true single interface with vacuum/2D PBC? QuickIce should document the PBC implications clearly. A future "vacuum gap" parameter could address this, but it requires GROMACS `.mdp` awareness that QuickIce currently doesn't have.

5. **LCM box dimension algorithm for dual-lattice periodicity:** The math is straightforward (LCM of ice and hydrate lattice parameters for X/Y/Z), but the user experience needs design: auto-adjust with warning? Manual override? How to report the dimension change?

## Dependencies on Other Milestones

- **v4.5 must be complete** — InterfaceConfig schema must be stable before adding new fields (`layer_order`, `hydrate_thickness`, `crystal_face`, `hydrate_lattice`, `hydrate_guest`). v4.5 adds solute/custom molecule infrastructure that may affect the export pipeline (P5/P6 guest naming patterns).
- **v4.5.1 CLI work may affect InterfaceConfig schema** — If CLI work adds or renames fields, Phase 1's InterfaceConfig additions must align. Coordinate with CLI milestone to avoid merge conflicts.
- **v4.6 multi-guest hydrate may overlap with ice+hydrate work** — If v4.6 adds support for multiple guest types in a single hydrate, the guest handling infrastructure (MoleculetypeRegistry, ITP bundling) will be shared with Phase 3. Ice+hydrate Phase 3 should consume v4.6's guest handling rather than building its own.
