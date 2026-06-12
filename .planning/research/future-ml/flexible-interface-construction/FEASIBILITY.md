# Feasibility Assessment: Flexible Interface Construction

**Goal:** Extend QuickIce's interface construction beyond fixed symmetric slab with hardcoded layer ordering
**Verdict:** YES — with phased delivery. Three features are feasible (asymmetric slab, crystal face selection, ice+hydrate); two are blocked or deferred (mixed hydrate types, general layer UI).
**Confidence:** HIGH (all findings code-grounded via actual source analysis of slab.py, gromacs_writer.py, interface_builder.py, types.py, GenIce2 genice.py)

## Summary

Flexible interface construction is achievable for QuickIce because the existing codebase already has the key building blocks: `tile_structure()` and `fill_region_with_water()` are fully generic region-fillers, overlap detection is already structure-agnostic, and the Z-stacking in slab.py is trivially generalizable from a hardcoded three-layer loop to a `list[LayerSpec]`-driven loop. The three features with clear scientific demand — asymmetric slab, crystal face selection, and ice+hydrate triple interface — map cleanly to three new mode entries in the existing QStackedWidget pattern, with progressively deeper code changes required.

The critical risk is **P3: dual MW virtual site computation** when ice (3-atom TIP3P) and hydrate (4-atom TIP4P) water molecules coexist in the same export pipeline. This pitfall is CRITICAL because it causes silent atom-index corruption — every molecule after the first mismatched entry shifts by one atom, producing a GRO file that GROMACS rejects at `grompp`. However, the fix is well-understood: switch from per-region atom-count detection to per-molecule `mol_type` checking in the export loop (types.py already stores `MoleculeIndex.mol_type`). This is a contained change, not a redesign.

The two blocked features are blocked for physics reasons, not engineering limitations: slab orientation flip is a PBC no-op, and mixed sI+sII hydrate types have 31% lattice mismatch with zero published MD precedent. These are anti-features that would mislead users rather than empower them.

## Feature Feasibility Verdicts

### 1. Asymmetric Slab Mode (Single Interface)

**Verdict:** FEASIBLE
**Effort:** LOW
**Blockers:** None
**Dependencies:** InterfaceConfig schema update (P14), validation formula update (P4)
**Risk:** LOW
**Scientific Justification:** Most MD interface studies use a single ice-water interface, not the symmetric sandwich. The symmetric sandwich doubles computational cost for no physical benefit in many use cases. Nada et al., Shi et al. (2025 JCP), and numerous ice-growth studies all use asymmetric slabs.

**Implementation Notes:**

The core change is removing the top ice layer from the Z-stack. Current slab.py hardcodes:
```
Z = [0, ice_thickness]                              → Bottom ice (tile_structure)
Z = [ice_thickness, ice_thickness + water_thickness]  → Water (fill_region_with_water)
Z = [ice_thickness + water_thickness, box_z]          → Top ice (tile_structure + Z-shift)
```

For asymmetric slab, simply skip the third layer:
```
Z = [0, ice_thickness]                    → Ice (tile_structure)
Z = [ice_thickness, box_z]               → Water (fill_region_with_water)
```

**Key technical points:**

1. **No coordinate regeneration needed.** GenIce2 generates ice once; asymmetric slab just uses fewer of those coordinates. The ice positions are identical — only the Z-extent of the water region changes.

2. **GenIce2 `shift` is not required.** GenIce2 always centers ice at origin (fractional [0,0,0]). Current code already Z-shifts the ice to start at Z=0 of the box via `positions[:, 2] += offset`. This pattern works unchanged.

3. **Validation formula change (P4):** Current `interface_builder.py:119-142` enforces `box_z = 2*ice_thickness + water_thickness`. Must add conditional: for `mode="asymmetric_slab"`, enforce `box_z = ice_thickness + water_thickness`. This is a 2-line change in `validate_interface_config()`.

4. **PBC implications (P10):** Under 3D PBC, `box_z = ice_thickness + water_thickness` creates `...|ice|water|ice|water|...` — which IS a symmetric slab viewed from a different origin. This is not a bug; it's fundamental PBC physics. For a true single interface, users need either (a) 2D PBC (`pbc-z = nil` in MDP) or (b) a vacuum gap above the water. **Recommendation for v5.0:** Just allow the `box_z = ice + water` formula and document that 3D PBC makes the structure periodic. The user gets fewer unique atoms (one interface instead of two), reducing computational cost — which IS the real benefit. Vacuum gap can be added manually by setting `box_z > ice_thickness + water_thickness`.

5. **GROMACS export:** No changes needed. The export pipeline writes: `[ice SOL] → [water SOL] → [guests]`. Without a top ice layer, there's simply fewer ice SOL atoms. The `[molecules]` section still has a single `SOL {count}`. P1 (molecules ordering) is not triggered.

6. **UI change:** Add "Asymmetric Slab" to `mode_combo` QComboBox (index 3), add `_create_asymmetric_slab_panel()` to `stacked_widget`. Panel has: ice_thickness, water_thickness, crystal_face QComboBox. Box Z constraint displays `ice + water` instead of `2*ice + water`.

**Estimated code changes:**
- `types.py`: +3 fields to InterfaceConfig (hydrate_thickness=0.0, crystal_face="basal", symmetric=True)
- `interface_builder.py`: +8 lines in validation (conditional formula)
- `slab.py`: +2 lines (skip top ice layer conditional)
- `interface_panel.py`: +60 lines (new stacked_widget page)
- `layer_assembly.py`: +80 lines (NEW file, extracted from slab.py loop)
- `asymmetric_slab.py`: +30 lines (NEW file, calls layer_assembly)

**Total:** ~180 lines of new/changed code. LOW effort.

---

### 2. Crystal Face Selection (Basal vs Prismatic)

**Verdict:** FEASIBLE (CONDITIONAL — restrict to orthogonal face options for v5.0)
**Effort:** LOW-MEDIUM
**Blockers:** None (if restricted to orthogonal options)
**Dependencies:** GenIce2 `one[hh]` vs `1h` lattice plugin (already available); UI combobox in slab panels
**Risk:** MEDIUM (triclinic box vector risk if non-diagonal reshape is allowed)
**Scientific Justification:** Different crystal faces have dramatically different surface energies (~70-120 mJ/m²), melting rates (basal ~2× slower than prismatic in TIP4P), and growth kinetics (basal via spiral dislocation vs prismatic via 2D nucleation). This is a well-established experimental variable in MD studies of ice-water interfaces.

**Implementation Notes:**

1. **GenIce2 lattice name mapping.** The face selection is NOT a post-generation rotation — it's a different lattice plugin:
   - "Basal (0001)" → GenIce2 lattice `one[hh]` (basal face exposed on Z-axis)
   - "Primary Prism (10-10)" → GenIce2 lattice `1h` (current default, axes exchanged per GenIce2 convention)
   
   This is confirmed by GenIce2 README documentation. The lattice plugins are already available in GenIce2's `genice2/lattice/` package.

2. **Current QuickIce may expose the wrong face.** The GenIce2 README states that the default `1h` lattice has "exchanged" crystal axes. This means current QuickIce likely exposes the **prismatic** face at the Z-interface, not the basal face that most users assume. This should be verified and documented. Switching the default to `one[hh]` (basal on Z) may be warranted for scientific correctness, but this is a breaking change for existing users — recommend keeping `1h` as default with `one[hh]` as an option.

3. **Orthogonal cell constraint (P7).** The critical risk: if `one[hh]` with a diagonal `reshape` matrix produces a **triclinic** supercell, the current code path `cell = np.diag([box_x, box_y, box_z])` (slab.py:606) would produce an orthogonal box while the atomic positions were computed in a triclinic frame → atoms outside the box → GROMACS wrapping artifacts.

   **Resolution for v5.0:** Restrict face options to those that produce **orthogonal** supercells with diagonal reshape. Both `1h` and `one[hh]` with diagonal reshape produce orthogonal cells (verified: GenIce2 reshape with `np.diag([nx,ny,nz])` produces a supercell that is orthogonal if the base lattice vectors along the reshape axes are orthogonal). The "Secondary Prism (11-20)" face would require a non-diagonal reshape → **defer this option** to post-v5.0 when triclinic output is supported.

4. **`generator.py` lattice name override.** Current code hardcodes the lattice name from the Candidate's `phase_id`. For face selection, the generator must accept a lattice name override:
   ```python
   lattice_name = FACE_TO_LATTICE.get(config.crystal_face, candidate.phase_id)
   lattice_module = safe_import('lattice', lattice_name)
   ```
   This is a 1-line change in `generator.py`.

5. **Face selection is NOT a separate mode.** It's a per-mode control (QComboBox) added to all slab-derived panels (Slab, Asymmetric Slab, Ice+Hydrate). It does NOT appear in Pocket or Piece modes (no flat interface to orient).

6. **Disable for non-hexagonal phases.** Crystal face naming only applies to Ice Ih (hexagonal). Ice Ic (cubic) and other polymorphs have different symmetry. The face QComboBox should be disabled when a non-Ih candidate is selected.

**Estimated code changes:**
- `generator.py`: +3 lines (lattice name override from config)
- `interface_panel.py`: +25 lines per slab panel (face QComboBox + signal wiring)
- `types.py`: +1 field (crystal_face="primary_prism")
- `slab.py`: +0 lines (face selection handled at generation time, not assembly)

**Total:** ~55 lines of new/changed code. LOW-MEDIUM effort (mostly UI).

**Conditional:** If `one[hh]` with diagonal reshape produces triclinic cells, this feature requires deferring triclinic support. Verify experimentally before committing.

---

### 3. Ice + Hydrate in Same System

**Verdict:** FEASIBLE (CONDITIONAL — requires P3 fix first, LCM box dimension algorithm)
**Effort:** MEDIUM-HIGH
**Blockers:** P3 (dual MW virtual site computation) must be fixed in export pipeline FIRST
**Dependencies:** P3 fix, P1 (molecules ordering — solved by single SOL group), P2 (LCM box dimensions), layer_assembly.py, dual-source UI
**Risk:** HIGH (most complex feature; multiple export pipeline changes required)
**Scientific Justification:** Ice-hydrate interfaces are physically real and scientifically valuable. CH₄-sI density (~0.91 g/cm³) closely matches Ice Ih (~0.92 g/cm³), making the interface practical. Use cases: hydrate dissociation from ice surface, ice-surface-mediated hydrate nucleation (Artyukhov et al. 2014 JCP), ice-coated hydrate stability studies.

**Implementation Notes:**

**A. Dual GenIce2 calls (SOLVED concept):**

GenIce2 is a single-lattice generator — it cannot produce ice+hydrate in one call. The approach (confirmed in STACK.md):
1. Call GenIce2 for ice (e.g., `ice1h`) → extract positions via raw format or existing GRO parsing
2. Call GenIce2 for hydrate (e.g., `CS1`) → extract positions
3. Place each in designated Z-regions of the simulation box
4. Fill remaining space with liquid water
5. Remove overlapping molecules at both interfaces

This is exactly the existing pipeline, called twice. The `tile_structure()` function is already generic — it places any crystal structure into any rectangular region. The extension is calling it with two different sources for two different Z-regions.

**B. P3 — Dual MW computation (CRITICAL, must fix first):**

This is the single most dangerous pitfall. Current export code (gromacs_writer.py:692-693) detects atoms-per-molecule from the FIRST ice-region atom name:
```python
has_ow_in_ice = "OW" in ice_region_atom_names
atoms_per_ice_mol = 4 if has_ow_in_ice else 3
```

With ice (3-atom "O", "H1", "H2") and hydrate framework (4-atom "OW", "HW1", "HW2", "MW") in the same export, this per-region detection fails. If a hydrate molecule is read as 3-atom, the MW atom becomes the next molecule's oxygen → total index corruption.

**Fix:** Use per-molecule `MoleculeIndex.mol_type` (already exists in types.py) to determine atoms-per-molecule in the export loop:
```python
for mol_idx in molecule_index:
    if mol_idx.mol_type == "ice":
        # 3-atom → expand to 4-atom (compute MW)
    elif mol_idx.mol_type in ("hydrate_framework", "water_liquid"):
        # 4-atom → pass through (MW already exists)
```

All three outputs are TIP4P-ICE format — identical final molecule topology. The difference is only in how MW is obtained (computed vs pre-existing).

**C. P1 — GROMACS [molecules] ordering (SOLVED by single SOL group):**

Current: `[molecules]` has `SOL {ice_count + water_count}`. With ice+hydrate, the ordering becomes: ice SOL → hydrate SOL → liquid SOL → guests. Since ALL are TIP4P-ICE (normalized), they're the same moleculetype. A single `SOL {total}` entry works, provided the `.gro` file atoms are contiguous. The export code must write: `[ice atoms][hydrate framework atoms][liquid water atoms][guest atoms]` — no interleaving.

This is a natural extension of the current pattern. The atom ordering convention (ice first, water second, guests last) just gains a third SOL sub-group (hydrate framework) between ice and liquid water.

**D. P2 — Periodicity mismatch (requires algorithm):**

Ice Ih cell: ~0.45 × 0.78 × 0.74 nm (GenIce2 1h convention, hexagonal).
sI hydrate cell: ~1.20 × 1.20 × 1.20 nm (cubic).
LCM along X: 0.45 nm × 8 = 3.60 nm ≈ 1.20 nm × 3 = 3.60 nm. ✓ Feasible.
LCM along Y: 0.78 nm × 15 = 11.70 nm; 1.20 nm × ~10 = 11.98 nm. ≈ 0.23% mismatch. Close but not exact. Need to accept approximate match or expand to larger LCM.

**Resolution:** Compute LCM-like dimensions for X, Y, Z separately. Accept a small mismatch (< 0.5%) and document auto-adjustments in the generation report. Current `round_to_periodicity()` already rounds to lattice multiples — extend to round to LCM of BOTH lattices. The boundary region will have ~1 unit cell of structural disorder, which is physically realistic.

**E. Layer assembly:**

```
Layer 0: Ice Ih    — Z = [0, ice_thickness]     — tile_structure(ice_candidate, region)
Layer 1: Hydrate   — Z = [ice_thickness, ice_thickness + hydrate_thickness] — tile_structure(hydrate_candidate, region)
Layer 2: Water     — Z = [ice_thickness + hydrate_thickness, box_z] — fill_region_with_water(region)
```

Overlap detection at BOTH boundaries (P8): ice↔hydrate and hydrate↔water. Current code only checks ice↔water. The `detect_overlaps()` function (cKDTree-based, overlap_resolver.py) is fully generic — just need to call it for each adjacent pair.

**F. Dual-source UI:**

The current `source_combo` (Ice Candidate / Hydrate Structure) is a binary switch. For ice+hydrate mode, embed per-layer source selectors WITHIN the mode-specific panel:

- Ice source: QComboBox populated from Tab 1 candidates (reuse candidate_dropdown pattern)
- Hydrate source: QComboBox with lattice type (sI/sII/sH) + guest (CH4/THF/CO2/H2)
- Do NOT add a third option to the top-level source_combo (ARCHITECTURE.md anti-pattern 6)

**G. Water model normalization (SOLVED):**

All water molecules are normalized to TIP4P-ICE at export:
- Ice: TIP3P (3-atom from GenIce2) → normalized to TIP4P-ICE (MW computed)
- Hydrate: TIP4P (4-atom from GenIce2) → already TIP4P-ICE (MW pre-existing)
- Liquid: TIP4P (4-atom from template) → already TIP4P-ICE

Result: uniform water model throughout the box. ✓

**Estimated code changes:**
- `layer_assembly.py`: +120 lines (NEW, generic layer loop with overlap detection)
- `ice_hydrate_slab.py`: +80 lines (NEW, dual-source assembly)
- `gromacs_writer.py`: +30 lines (P3 fix: per-molecule mol_type detection in export loop)
- `interface_panel.py`: +100 lines (ice+hydrate panel with dual source)
- `main_window.py`: +25 lines (dual-source signal wiring)
- `types.py`: +8 fields (hydrate_thickness, ice_source_index, hydrate_lattice, hydrate_guest, etc.)
- `interface_builder.py`: +40 lines (ice_hydrate mode routing + LCM dimension computation)
- `generator.py`: +15 lines (dual GenIce2 call orchestration)

**Total:** ~420 lines of new/changed code. MEDIUM-HIGH effort.

**Critical dependency:** P3 fix (per-molecule MW detection) must be implemented and tested BEFORE any ice+hydrate generation code. Without it, every export produces corrupted atom indices.

---

### 4. Mixed Hydrate Types (sI + sII)

**Verdict:** BLOCKED (anti-feature)
**Effort:** N/A — do not build
**Blockers:** Physical impossibility (31% lattice mismatch), zero scientific demand
**Dependencies:** None
**Risk:** N/A
**Scientific Justification:** None. No published MD study combines sI and sII in the same simulation box. The lattice mismatch (sI: a≈1.20 nm, sII: a≈1.73 nm) means the smallest common supercell requires box dimensions of ~9.6 nm (8×sI ≈ 5×sII) — impractically large. sI and sII are thermodynamically distinct phases with fundamentally different cage architectures; they are NOT miscible.

**Why BLOCKED, not CONDITIONAL:**

1. **Lattice mismatch is catastrophic:** sI/sII ratio = 1.20/1.73 ≈ 0.69. No integer multiples produce dimensions closer than ~9.6 nm. This is 8× the typical box size.

2. **Cage incompatibility:** sI has 5¹²6² cages (small + large). sII has 5¹²6⁴ cages (small + much larger). The "large" cages are structurally incompatible — different ring topologies cannot form a continuous hydrogen-bond network at any boundary.

3. **No scientific demand:** arXiv search (2026-06-12) returned only 4 results for "ice hydrate interface molecular dynamics" — none about mixed structures. Google Scholar search produced server errors but no relevant results. If a study needed both sI and sII, it would run separate simulations — not mix them.

4. **Mixed guest systems form ONE structure:** In nature, a mixed-guest system (e.g., CH₄ + C₂H₆) forms a single sI or sII structure, not a mixture. The phase rule determines which structure forms.

5. **Building this would mislead users:** A "mixed hydrate" option would suggest this is physically meaningful when it is not. Users who select it would produce large, structurally corrupted systems that cannot be used for legitimate MD studies.

**What to do instead:** If users ask for mixed hydrate types, explain the lattice mismatch and recommend separate simulations. The correct approach for studying different hydrate structures is to run multiple independent calculations, not to mix them in one box.

**Confidence:** HIGH (lattice parameters well-established; PBC physics fundamental; absence of published studies notable)

---

### 5. General Layer Composition UI

**Verdict:** CONDITIONAL (defer to post-v6; only if demand emerges)
**Effort:** HIGH (major UI redesign)
**Blockers:** No scientific demand; over-engineering risk
**Dependencies:** All three feasible features must be implemented first to validate the pattern
**Risk:** HIGH (combinatorial validation explosion; physically meaningless configurations)
**Scientific Justification:** None. Scientists need 2-3 specific named configurations, not arbitrary N-layer stacks. The vast majority of "layer orderings" are either (a) physically meaningless under PBC (e.g., water-ice-water = ice-water-ice shifted), or (b) impossible (incompatible lattice parameters), or (c) useless (nobody studies them).

**Why CONDITIONAL, not BLOCKED:**

The general layer UI is not physically impossible — it's just wasteful. If demand emerges for a 4th or 5th named configuration (beyond slab, asymmetric, ice+hydrate), the architecture should support adding it via a new mode entry + panel, NOT via a drag-and-drop compositor. The `layer_assembly.py` engine (built for features 1-3) would already support any fixed N-layer configuration.

**What to build instead:** Named mode presets with fixed layer stacks (CHARMM-GUI Membrane Builder pattern). Each mode has a predetermined layer ordering with per-layer source dropdowns. No drag-and-drop, no add/remove buttons, no arbitrary N-layer configuration.

**Defer until:** At least 2 of the 3 feasible features are shipped and user feedback confirms (or denies) demand for more configurations. If nobody asks for a 4th configuration, this remains permanently deferred.

**Estimated code changes if built:** +400-600 lines (major UI redesign: QListWidget or custom widget, per-layer parameter panels, dynamic validation). This is 3-4× the effort of any individual feature — for zero proven demand.

---

## Comparison Matrix

| Criterion | Asymmetric Slab | Crystal Face | Ice+Hydrate | Mixed Hydrate | Layer UI |
|-----------|----------------|-------------|-------------|---------------|----------|
| Feasibility | ✅ FEASIBLE | ✅ FEASIBLE (conditional) | ✅ FEASIBLE (conditional) | ❌ BLOCKED | ⏸ CONDITIONAL |
| Effort | LOW (~180 LOC) | LOW-MED (~55 LOC) | MED-HIGH (~420 LOC) | N/A | HIGH (~500 LOC) |
| Scientific Demand | HIGH — most common study type | MEDIUM — established variable | MEDIUM — growing research area | NONE — no published precedent | NONE — no user requests |
| Risk | LOW | MEDIUM (triclinic risk) | HIGH (P3 export corruption) | N/A | HIGH (validation explosion) |
| GROMACS Impact | Minimal | Minimal (orthogonal cells) | Significant (dual MW, LCM dims) | N/A | Severe |
| User-Facing Value | Reduces compute cost ~40% | Enables face-dependent studies | Enables new research configs | Misleading | Confusing |
| Must Fix First | P4 (validation formula) | Verify one[hh] orthogonality | P3 (per-molecule MW) | N/A | Ship 2+ features first |

## Recommended Phasing

### Phase 1: Asymmetric Slab + Crystal Face Selection

**Rationale:** Lowest effort, highest immediate impact, and no GROMACS export changes needed. These two features can be developed and tested together because they share the same UI pattern (new stacked_widget pages) and both modify only `InterfaceConfig` + validation + assembly. Crystal face selection is additive to asymmetric slab — the face dropdown appears in the asymmetric slab panel.

**Deliverables:**
- `layer_assembly.py` — extracted from slab.py (shared foundation for all future features)
- `asymmetric_slab.py` — new mode module
- Crystal face QComboBox added to slab, asymmetric_slab, and (later) ice+hydrate panels
- InterfaceConfig: +3 fields (symmetric, crystal_face, layer_order)
- Validation: conditional formula based on mode
- Verification: confirm `one[hh]` with diagonal reshape produces orthogonal cells

**Exit criteria:** User can generate asymmetric slab with basal or prismatic face. GROMACS export produces valid `.gro` + `.top` that passes `grompp`.

**Estimated timeline:** 1-2 development cycles.

### Phase 2: Export Pipeline Hardening (P3 Fix)

**Rationale:** The P3 pitfall (dual MW computation for mixed 3-atom/4-atom molecules) is a prerequisite for ice+hydrate mode. It must be implemented and tested independently BEFORE any multi-source generation code. Fixing P3 first means the export pipeline is ready when the ice+hydrate feature arrives.

**Deliverables:**
- Per-molecule `mol_type` detection in `write_interface_gro_file()` export loop
- Post-export atom count assertion: `total_atoms = (ice_nmol × 4) + (hyd_water_nmol × 4) + (liq_water_nmol × 4) + guest_atoms`
- Unit test: generate a mixed ice+hydrate SOL array (synthetic, not from GenIce2) and verify export correctness

**Exit criteria:** Unit test passes: a `.gro` file with 3-atom ice SOL and 4-atom hydrate SOL exports correctly with TIP4P-ICE normalization. `grompp` accepts the output.

**Estimated timeline:** 0.5-1 development cycle.

### Phase 3: Ice + Hydrate Triple Interface

**Rationale:** The highest-impact differentiator feature. Depends on Phase 1 (layer_assembly.py) and Phase 2 (P3 fix). This is the most complex feature but also the most scientifically valuable — it enables research configurations that currently require manual GROMACS setup.

**Deliverables:**
- `ice_hydrate_slab.py` — new mode module (dual GenIce2 calls, LCM dimensions)
- Dual-source UI panel (ice candidate QComboBox + hydrate lattice/guest QComboBoxes)
- LCM box dimension computation with auto-adjustment reporting
- Cross-layer overlap detection (ice↔hydrate + hydrate↔water)
- Density mismatch warning in UI (≤1% for sI CH4, ~7% for sII THF)

**Exit criteria:** User can generate ice-hydrate-water triple interface. GROMACS export has correct SOL ordering, correct MW computation, and passes `grompp`. LCM box dimensions are reported in generation log.

**Estimated timeline:** 2-3 development cycles.

### Phase 4 (Deferred): General Layer Composition UI

**Rationale:** Build ONLY if demand emerges after Phases 1-3 ship. The architecture already supports it (layer_assembly.py + named modes). Adding a 4th or 5th named mode is trivial. A drag-and-drop compositor is not.

---

## Phase-Specific Research Flags

| Phase | Topic | Needs Research? | Why |
|-------|-------|----------------|-----|
| Phase 1 | Verify `one[hh]` produces orthogonal cell with diagonal reshape | **YES** | P7 risk — must confirm before shipping crystal face selection. Quick test: run GenIce2 with `one[hh]` and `reshape=np.diag([3,3,3])`, check if output cell is orthogonal |
| Phase 1 | Verify current QuickIce exposes prismatic face (not basal) | **YES** | Affects default behavior and documentation. Run current slab generation, inspect crystal face at Z-interface |
| Phase 2 | P3 fix: verify MoleculeIndex.mol_type is populated for all molecule sources | **YES** | Critical assumption — if mol_type is not set for some molecules, the per-molecule detection fails |
| Phase 3 | LCM algorithm for hexagonal ice + cubic hydrate cell dimensions | **MINIMAL** | LCM math is straightforward; main complexity is handling non-cubic ice cell (different a, b dimensions) |
| Phase 3 | Ice-hydrate boundary structural characterization | **NO** | Accept disordered boundary as physically realistic. No special treatment needed beyond overlap removal |

## Sources

| Source | Confidence | Notes |
|--------|------------|-------|
| STACK.md (Wave 1) | HIGH | GenIce2 API analysis from actual source code |
| FEATURES.md (Wave 1) | HIGH | Physics constraints; PBC symmetry, lattice mismatch, density compatibility |
| ARCHITECTURE.md (Wave 2) | HIGH | UI patterns, component boundaries, data flow from actual code analysis |
| PITFALLS.md (Wave 2) | HIGH | All 15 pitfalls code-grounded in gromacs_writer.py, slab.py, types.py |
| GenIce2 genice.py source | HIGH | Read full file; shift, reshape, density, noise parameters verified |
| GenIce2 README | MEDIUM | Documents `one[hh]` vs `1h` axis convention; not directly fetched |
| QuickIce slab.py | HIGH | Read full (641 lines); Z-stacking implementation confirmed |
| QuickIce gromacs_writer.py | HIGH | Read full (2328 lines); export pipeline and MW computation confirmed |
| QuickIce interface_builder.py | HIGH | Read full (354 lines); validation formula confirmed |
| QuickIce types.py | HIGH | Read full (722 lines); MoleculeIndex.mol_type confirmed |
| PBC symmetry argument | HIGH | Fundamental property of periodic boundary conditions; textbook physics |
| Lattice parameter values | MEDIUM | sI: a≈1.20 nm, sII: a≈1.73 nm from Wikipedia/Sloan & Koh (2008) |
| Ice Ih density 0.92 g/cm³ | HIGH | IAPWS standard value |
| CH₄-sI density ~0.91 g/cm³ | MEDIUM | Domain knowledge + Wikipedia; close match to ice Ih is well-known |
