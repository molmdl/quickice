# Synthesis: Flexible Interface Construction

**Date:** 2026-06-12
**Confidence:** HIGH (all findings code-grounded via actual source analysis of GenIce2 genice.py, QuickIce slab.py/gromacs_writer.py/types.py/interface_builder.py)

## Executive Verdict

Build three features in sequence: **asymmetric slab** (table stakes, ~180 LOC), **crystal face selection** (real flexibility, ~55 LOC), and **ice+hydrate triple interface** (key differentiator, ~420 LOC). Everything else is either physically meaningless under PBC (slab flip), structurally impractical (mixed sI+sII, 31% lattice mismatch, zero published MD precedent), or premature over-engineering (drag-and-drop layer UI). The critical prerequisite for ice+hydrate is fixing P3 — per-molecule MW virtual site detection in the GROMACS export loop — because mixing 3-atom ice and 4-atom hydrate SOL molecules in the same GRO file silently corrupts all subsequent atom indices. The existing codebase generalizes cleanly: `tile_structure()` and `fill_region_with_water()` are already generic region-fillers, the QStackedWidget pattern extends naturally to new modes, and the hardcoded Z-stacking in slab.py resolves trivially into a `LayerSpec`-driven loop. No GenIce2 modifications required; all needed APIs (`shift`, `reshape`, `raw` format, `one[hh]` lattice) already exist.

## Phase Structure

### Phase 1: Asymmetric Slab + Crystal Face Selection
**Effort:** LOW (~235 LOC total) | **Risk:** LOW | **Value:** HIGH
**Timeline:** 1-2 development cycles

**What:**
- Allow `box_z = ice_thickness + water_thickness` (skip top ice layer in assembly)
- Add crystal face QComboBox to all slab-derived panels: `"Basal (0001)"` → GenIce2 lattice `one[hh]`, `"Primary Prism (10-10)"` → `1h` (current default)
- Extract `layer_assembly.py` from slab.py — the shared foundation for all future layer-based modes
- Add `"Asymmetric Slab"` to `mode_combo` QComboBox (index 3) with new QStackedWidget page
- Add `InterfaceConfig` fields with backward-compatible defaults: `symmetric=True`, `crystal_face="primary_prism"`, `layer_order=["ice","water","ice"]`
- Update `validate_interface_config()`: conditional formula based on mode (`2*ice+water` for symmetric, `ice+water` for asymmetric)
- Add `LayerPreviewWidget` — simple 2D schematic diagram of layer stack with real-time updates

**File changes:**
| File | Action | Lines |
|------|--------|-------|
| `structure_generation/layer_assembly.py` | CREATE | ~80 |
| `structure_generation/modes/asymmetric_slab.py` | CREATE | ~30 |
| `gui/layer_preview.py` | CREATE | ~60 |
| `structure_generation/types.py` | MODIFY | +3 fields to InterfaceConfig |
| `structure_generation/interface_builder.py` | MODIFY | +8 lines validation |
| `structure_generation/modes/slab.py` | MODIFY | Refactor to use layer_assembly internally |
| `structure_generation/generator.py` | MODIFY | +3 lines lattice name override |
| `gui/interface_panel.py` | MODIFY | +85 lines (asymmetric panel + face combo + preview) |

**Why first:** Smallest change, highest demand-to-effort ratio. Most MD interface studies use single ice-water interface, not the symmetric sandwich. Asymmetric slab reduces computational cost ~40%. Crystal face is the real flexibility scientists need (not slab flip — which is a PBC no-op). Both features share the same UI pattern (new QStackedWidget pages) and the `layer_assembly.py` foundation needed by Phase 3.

**Must avoid:**
- **P4** (validation formula break) — update formula and InterfaceConfig in the same commit
- **P7** (triclinic box vectors) — restrict face options to orthogonal-producing lattices (`1h` and `one[hh]` both produce orthogonal cells with diagonal reshape); defer "Secondary Prism (11-20)"
- **P14** (backward compat) — all new InterfaceConfig fields must have defaults; `from_dict()` must use `.get()`

---

### Phase 2: Export Pipeline Hardening (P3 Fix)
**Effort:** MEDIUM (~30-50 LOC + tests) | **Risk:** MEDIUM | **Value:** HIGH (prerequisite for Phase 3)
**Timeline:** 0.5-1 development cycle

**What:**
- Refactor `write_interface_gro_file()` export loop (gromacs_writer.py:692-743): switch from per-region `atoms_per_ice_mol` detection to per-molecule `MoleculeIndex.mol_type` detection
- Handle three molecule types in the same export: `ice` (3-atom → expand to 4-atom by computing MW), `hydrate_framework` (4-atom → pass through), `water_liquid` (4-atom → pass through)
- All three produce identical TIP4P-ICE output — only the source atom count differs
- Add post-export atom count assertion: `total_atoms = (ice_nmol × 4) + (hyd_water_nmol × 4) + (liq_water_nmol × 4) + guest_atoms`
- Unit test: synthetic mixed 3-atom/4-atom SOL array → export → verify atom count and ordering → verify `grompp` acceptance

**File changes:**
| File | Action | Lines |
|------|--------|-------|
| `output/gromacs_writer.py` | MODIFY | ~30 lines in export loop (lines 688-743) |
| `tests/` | CREATE | New test for mixed SOL export |

**Why second:** P3 is the single most dangerous pitfall in the entire feature set. It causes **silent data corruption** — if a hydrate 4-atom molecule is read as ice 3-atom, the MW atom becomes the next molecule's oxygen → every subsequent atom shifts by one index → total coordinate corruption → GROMACS crashes at `grompp`. This is a contained change (export loop refactor, not redesign) but must be tested independently before any ice+hydrate code is written.

**Must avoid:**
- **P1** (GROMACS `[molecules]` ordering) — maintain single contiguous SOL group: `[ice SOL][hydrate SOL][liquid SOL][guests]` → single `SOL {total}` in `[molecules]`
- **P14** — verify `MoleculeIndex.mol_type` is populated for ALL molecule sources (ice, hydrate_framework, water_liquid, guests). Audit types.py before implementing.
- **P6** (atomtype dedup) — ensure `comment_out_atomtypes_in_itp()` is called for ALL bundled ITP files

---

### Phase 3: Ice + Hydrate Triple Interface
**Effort:** MEDIUM-HIGH (~420 LOC) | **Risk:** HIGH | **Value:** HIGH
**Timeline:** 2-3 development cycles

**What:**
- New mode: `"Ice + Hydrate"` (index 4 in `mode_combo`) with dual-source panel
- Dual-source UI: ice candidate QComboBox (from Tab 1) + hydrate lattice/guest QComboBoxes (sI/sII/sH + CH4/THF/CO2/H2) — embedded in mode-specific panel, NOT in top-level `source_combo`
- Dual GenIce2 calls: ice (e.g., `ice1h`) + hydrate (e.g., `CS1`), extract absolute coordinates independently
- LCM box dimension computation for dual-lattice periodicity (e.g., ice a≈0.45 nm + sI a≈1.20 nm → LCM X = 3.60 nm = 8×ice_a = 3×hyd_a)
- Cross-layer overlap detection: ice↔hydrate boundary + hydrate↔water boundary (new check that doesn't exist in current code)
- Layer stack: `[Ice Ih | Hydrate | Water]` with `box_z = ice_thickness + hydrate_thickness + water_thickness`
- Density mismatch warning in UI (≤1% for CH₄-sI = excellent match; ~7% for THF-sII = acceptable)
- Crystal face QComboBox for the ice layer (reuse Phase 1 widget)
- MainWindow dual-source signal wiring

**File changes:**
| File | Action | Lines |
|------|--------|-------|
| `structure_generation/modes/ice_hydrate_slab.py` | CREATE | ~80 |
| `structure_generation/layer_assembly.py` | MODIFY | +40 (overlap detection for adjacent layers) |
| `gui/interface_panel.py` | MODIFY | +100 (ice+hydrate dual-source panel) |
| `gui/main_window.py` | MODIFY | +25 (dual-source signal wiring) |
| `structure_generation/types.py` | MODIFY | +8 fields (hydrate_thickness, ice_source_index, hydrate_lattice, hydrate_guest, etc.) |
| `structure_generation/interface_builder.py` | MODIFY | +40 (ice_hydrate routing + LCM dimension computation) |
| `structure_generation/generator.py` | MODIFY | +15 (dual GenIce2 call orchestration) |

**Why third:** Depends on Phase 1 (`layer_assembly.py` engine) and Phase 2 (P3 per-molecule MW fix — MUST be fixed and tested first). This is the most scientifically valuable feature — it enables research configurations that currently require manual GROMACS setup: hydrate dissociation from ice surface, ice-coated hydrate stability, ice-surface-mediated hydrate nucleation. CH₄-sI density (~0.91 g/cm³) closely matches Ice Ih (~0.92 g/cm³), making the interface physically practical.

**Must avoid:**
- **P3** (dual MW — fixed in Phase 2, but verify the fix handles dual-source correctly)
- **P2** (periodicity mismatch — compute LCM dimensions with auto-adjustment reporting in generation log)
- **P8** (cross-layer overlaps — add ice↔hydrate boundary check using existing cKDTree-based `detect_overlaps()`)
- **P5/P6** (guest naming + atomtype dedup — existing `_H`/`_L` suffix pattern handles dual-source, but verify explicitly)
- **P9** (density mismatch — generate both ice and hydrate at same target density; accept ~0.5 nm disordered boundary as physically realistic)

---

### Phase 4 (DEFERRED): General Layer Composition UI
**Effort:** HIGH (~500 LOC) | **Risk:** HIGH | **Value:** NONE (no demand)
**Why deferred:** No scientist has asked for arbitrary N-layer composition. Named modes (asymmetric slab, ice+hydrate) cover all known use cases. The `LayerSpec` engine from Phase 1 already supports adding new modes trivially — a 4th or 5th named mode is ~100 LOC. A general drag-and-drop compositor is ~500 LOC of UI complexity for zero proven demand. Revisit ONLY if Phases 1-3 ship and users request more configurations.

## Quick Wins

| Win | LOC | What to Do | Delivers |
|-----|-----|-----------|----------|
| Asymmetric slab assembly | ~2 lines | In `slab.py`, skip top ice tiling + update validation formula to `ice+water` | Most common MD study config; ~40% compute savings |
| Crystal face dropdown | ~25 lines | QComboBox in slab panels mapping to GenIce2 lattice name | Real scientific flexibility (basal vs prismatic face) |
| Verify current default face | 0 LOC | Generate test slab with `1h`, inspect which face is at Z-interface | Documentation fix; may reveal current QuickIce exposes wrong face |
| InterfaceConfig backward compat | ~3 fields | Add `symmetric=True`, `crystal_face="primary_prism"`, `layer_order` with defaults | Unblocks all future mode work without breaking existing configs |
| P3 audit | 0 LOC | Check `MoleculeIndex.mol_type` is set for all molecule sources | Confirms Phase 2 approach is viable before investing |

## Anti-Features

| What NOT to Build | Why | Source |
|-------------------|-----|--------|
| **Slab orientation flip** (ice-on-bottom vs ice-on-top) | Under PBC, these are the same structure shifted by half a box. Implementing it misleads users into thinking orientation matters. | FEATURES.md: PBC symmetry |
| **Mixed hydrate types** (sI + sII, sI + sH, sII + sH) | 31% lattice mismatch between sI and sII. No common supercell below ~10 nm. No published MD study uses this. sI and sII are thermodynamically distinct immiscible phases. | FEATURES.md: lattice mismatch |
| **Arbitrary drag-and-drop layer ordering** | Over-engineering. Scientists need 2-3 named configurations, not combinatorial freedom. Most orderings are PBC-meaningless. | ARCHITECTURE.md: anti-patterns 1-2 |
| **General "any structure for any layer"** | Requires arbitrary .gro loading, incompatible unit cells, intractable validation. Only allow QuickIce-generated sources. | ARCHITECTURE.md: anti-pattern 5 |
| **Water slab in ice (inverse sandwich)** | Under PBC, this IS the current symmetric sandwich — just relabeled. Pocket mode handles spherical water-in-ice. | FEATURES.md: anti-feature |
| **Third option in top-level source_combo** | Dual-source for ice+hydrate belongs in mode-specific panel, not in the top-level binary switch. | ARCHITECTURE.md: anti-pattern 6 |

## Risk-Adjusted Priority

| Phase | Effort | Risk | Value | Priority | Rationale |
|-------|--------|------|-------|----------|-----------|
| 1: Asymmetric + Face | LOW | LOW | HIGH | **1 — Ship first** | Highest demand-to-effort ratio; creates `layer_assembly.py` foundation |
| 2: P3 Export Fix | MEDIUM | MEDIUM | HIGH (prereq) | **2 — Before Phase 3** | Silent corruption bug; contained fix; enables ice+hydrate |
| 3: Ice + Hydrate | MED-HIGH | HIGH | HIGH | **3 — After Phases 1+2** | Most valuable new feature; highest risk; depends on both |
| 4: Layer UI | HIGH | HIGH | NONE | **∞ — Deferred** | Zero demand; revisit only if Phases 1-3 generate requests |

## Cross-Cutting Insights

1. **PBC symmetry is the central physics constraint.** It invalidates slab flip (identical under translation), makes asymmetric slab periodic by default (document, don't "fix"), and constrains which layer orderings are physically distinct. Every UI decision must account for PBC — a "flip" button would mislead users; a "water-ice-water" ordering is just the current slab shifted.

2. **All water normalizes to TIP4P-ICE at export.** Ice (3-atom TIP3P) → MW computed. Hydrate framework (4-atom TIP4P) → MW pre-existing. Liquid water (4-atom TIP4P) → MW pre-existing. All three produce the same `[moleculetype] SOL`. This means a single `SOL {total}` in `[molecules]` works for ALL configurations — even ice+hydrate. The ONLY catch is the export loop must handle per-molecule atom count variation (P3). This normalization pattern is why mixed-source is feasible at all.

3. **`layer_assembly.py` is the keystone refactoring.** It replaces slab.py's hardcoded bottom-ice / water / top-ice loop with a generic `list[LayerSpec]` → `assemble_layers()` pipeline. Building it in Phase 1 means Phase 3 doesn't duplicate assembly logic. The `LayerSpec` dataclass (`layer_type`, `thickness`, `source`, `z_start`, `z_end`) naturally extends to any future named mode.

4. **Crystal face is a GenIce2 lattice name change, NOT a post-generation rotation.** `"Basal (0001)"` → GenIce2 lattice `one[hh]`. `"Primary Prism (10-10)"` → `1h` (current default). QuickIce passes a different lattice name to `safe_import()` — ~3 lines in `generator.py`. The expensive part is UI + verification, not generation logic.

5. **GenIce2's `raw` format is the escape hatch.** It provides fractional coordinates + cell matrix + cage positions at full float precision, avoiding the 0.001 nm GRO round-trip loss. For Phases 1-2, existing GRO parsing works fine. For Phase 3 (dual-source with different cell dimensions), raw format extraction becomes valuable. Build the raw-format path when needed, not before.

6. **The `one[hh]` vs `1h` axis convention is an unverified assumption.** GenIce2 README says `1h` has "exchanged" axes and recommends `one[hh]` for basal face on Z. Current QuickIce uses `1h` by default — it may expose the **prismatic** face, not the basal face most users assume. This has been true since v1.0 and likely affects all existing QuickIce ice-water interface simulations. Must verify before Phase 2 ships.

7. **Named mode presets beat general composition.** The CHARMM-GUI Membrane Builder pattern (curated named configurations with fixed layer stacks) is the right model for QuickIce. Each mode has a predetermined layer ordering with per-layer source dropdowns. No drag-and-drop, no add/remove buttons. This keeps validation tractable and prevents physically meaningless configurations.

## Open Questions

| Question | Blocks | How to Resolve |
|----------|--------|---------------|
| Does GenIce2 `1h` produce prismatic face at Z-interface in QuickIce? | Phase 2 correctness, documentation | Generate test slab with both `1h` and `one[hh]`, inspect crystal orientation at Z-boundary. ~1 hour of testing. |
| Does `one[hh]` with diagonal reshape produce orthogonal cells? | Phase 2 scope (triclinic risk P7) | Run GenIce2 with `one[hh]` + `reshape=np.diag([3,3,3])`, check output cell matrix. If triclinic, defer "Basal (0001)" option or add triclinic output support. |
| Is `MoleculeIndex.mol_type` populated for ALL molecule sources? | Phase 2 P3 fix viability | Audit types.py + all molecule creation paths. If any source misses `mol_type`, per-molecule detection fails silently. Must fix before Phase 2 code. |
| Does the ice-hydrate boundary need special structural treatment? | Phase 3 quality | Domain-expert input. Literature suggests ~0.5 nm disordered transition region. Simple layer stacking + overlap removal + energy minimization may suffice. If not, interface matching algorithms would significantly increase Phase 3 scope. |
| How should LCM box dimension auto-adjustment be reported? | Phase 3 UX | Design decision: auto-adjust with warning in generation log (follows current `round_to_periodicity()` pattern) vs manual override vs reject-and-reprompt. |
| Is asymmetric slab under 3D PBC acceptable to users? | Phase 1 documentation | Under 3D PBC, `ice|water` repeats as `ice|water|ice|water`. Benefit is fewer unique atoms. Document clearly. Add "vacuum gap" parameter in future if demand emerges. |

## Dependencies on Other Milestones

- **v4.5 must be complete** — InterfaceConfig schema must stabilize before adding new fields. v4.5 adds solute/custom molecule infrastructure that affects the export pipeline (P5/P6 guest naming patterns, MoleculetypeRegistry).
- **v4.5.1 CLI work** — If CLI adds or renames InterfaceConfig fields, Phase 1 additions must align to avoid merge conflicts.
- **v4.6 multi-guest hydrate** — Guest handling infrastructure (MoleculetypeRegistry, ITP bundling) overlaps with Phase 3. Ice+hydrate should consume v4.6's guest handling rather than building its own.
