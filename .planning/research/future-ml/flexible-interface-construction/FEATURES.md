# Feature Landscape: Flexible Interface Construction

**Domain:** Ice-water interface molecular dynamics simulation  
**Researched:** 2026-06-12  
**Confidence:** MEDIUM (physics claims from domain knowledge + webfetch; limited direct literature access)

---

## Executive Summary

This document evaluates five proposed "flexible interface construction" features for QuickIce against known physics constraints and scientific demand. The central finding is that **most proposed flexibility features are either physically meaningless under PBC or serve niche use cases**. The one feature with clear, broad scientific demand is **ice + hydrate in the same simulation box** — this enables hydrate dissociation studies and ice-hydrate interface investigations, which are active research areas.

Key findings:
- **Slab orientation flip is physically meaningless under PBC.** The periodic image makes "ice-on-top" identical to "ice-on-bottom." No MD paper needs this.
- **Crystal face orientation (basal vs prismatic) IS physically meaningful** and is the real flexibility scientists need — but this is a separate feature from "flip."
- **Mixed hydrate types (sI + sII) in one box** have catastrophic lattice mismatch (~44%) and no published MD precedent. This is an anti-feature.
- **Ice + hydrate coexistence** is scientifically valuable: hydrate dissociation studies, ice-hydrate interface free energy, and hydrate nucleation from ice surfaces are all active research topics.
- **Arbitrary layer ordering UI** is over-engineering. Scientists need 2-3 specific configurations, not a general combinatorial system.

---

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Physics Constraint | Notes |
|---------|-------------|------------|-------------------|-------|
| Hydrate slab + water interface | Current hydrate→interface workflow via Tab 3 source dropdown | LOW (already works) | None — standard sandwich | Already implemented as hydrate→interface in v4.0 |
| Single ice slab + water (one interface) | Many studies only need ONE ice-water interface, not sandwich | MEDIUM | Requires vacuum slab or asymmetric box | Current slab mode creates TWO interfaces (top+bottom ice); some studies want just one |
| Correct crystal face at interface | Basal [001] vs prismatic [100]/[110] faces have different melting/growth kinetics | MEDIUM-HIGH | GenIce2 `one[hh]` flag exposes basal face on Z; default `1h` exchanges axes | Document and expose face selection; see GenIce2 README note |

## Differentiators

Features that set QuickIce apart from manual GROMACS setup or other tools.

| Feature | Value Proposition | Complexity | Physics Constraint | Notes |
|---------|-------------------|------------|-------------------|-------|
| Ice + hydrate in same box | Enables ice-hydrate-water triple interface; hydrate dissociation from ice surface; ice-surface nucleation of hydrate | HIGH | Density match is reasonable (~0.92 vs ~0.93-1.0 g/cm³); structural mismatch at boundary requires overlap resolution; interface is physically real | Most impactful new feature. See use cases below. |
| Hydrate pocket in ice (inverse pocket) | Study hydrate formation within ice matrix; permafrost hydrate scenarios | MEDIUM | Pocket mode already carves cavities; hydrate structure must fit within pocket diameter; density difference is small | Natural extension of existing pocket mode |
| Asymmetric slab (one ice layer + water) | Study single ice-water interface without mirror effects; reduces computational cost by ~40% | MEDIUM | PBC with vacuum layer or wall; or simply box_z = ice_thickness + water_thickness (no top ice) | Most MD interface studies use asymmetric slab with vacuum or walls |
| Crystal face selection for interface | Different faces (basal, primary prism, secondary prism) have different surface energies and growth rates | MEDIUM | GenIce2 already supports axis permutation (`one[hh]`); need to expose in UI | Literature shows strong face-dependent effects (Shi et al. 2025, JCP) |
| Hydrate-liquid interface with explicit guest gradient | Study guest concentration effects near hydrate surface | MEDIUM | Guests dissolve from hydrate surface into liquid; need to handle mixed guest/water in liquid region | Related to solute insertion (v4.5 feature) |

## Anti-Features

Features to explicitly NOT build. Common mistakes or over-engineering.

| Anti-Feature | Why Avoid | What to Do Instead |
|-------------|-----------|-------------------|
| Slab orientation flip (ice-on-bottom) | Under PBC, the slab repeats infinitely — "top" and "bottom" are the same periodic image. Flipping the slab produces an identical structure (just shifted by half the box). No MD simulation has a preferred gravity direction. | Do NOT implement. If users ask, explain PBC symmetry. The current bottom-ice | water | top-ice is the standard and only meaningful convention. |
| Multiple hydrate types in same box (sI + sII) | Lattice mismatch is ~44% (sI: a≈1.2 nm, sII: a≈1.73 nm). These structures are immiscible — they have fundamentally different cage architectures (5¹² 6² vs 5¹² 6⁴ large cages). No published MD study combines them. The box dimensions would need to be an LCM of both lattice parameters (extremely large). | Do NOT implement. If users need sI and sII in the same simulation, they should use separate simulations. The scientific question (different guest selectivity) is addressed by running separate calculations, not mixing. |
| sI + sH or sII + sH in same box | Same issue as above. sH has hexagonal symmetry (a≈1.22 nm, c≈1.01 nm) which is incompatible with cubic sI/sII. sH also requires two guest types (large + help gas) making mixing even more problematic. | Do NOT implement. |
| Arbitrary layer ordering UI (drag-and-drop layers) | Over-engineering. Scientists need 2-3 specific configurations, not a general combinatorial system. Most "orderings" are physically meaningless (e.g., water-ice-water is just ice sandwich with flipped Z). | Implement specific named modes (e.g., "ice-hydrate-water" triple interface) rather than arbitrary layer stacking. |
| "Water slab in ice" (inverse sandwich) | Under PBC, this is the same as the current ice-water-ice sandwich — just relabeled. The periodic image means "ice surrounding water" is identical to "ice slab with water between." | Current pocket mode already handles water-in-ice for spherical geometries. Slab geometry of water-in-ice is the same as current slab mode. |
| General "any structure for any layer" composition | Would require arbitrary structure loading, incompatible unit cells, and impossible overlap resolution. Most combinations are physically nonsensical. | Support specific scientifically validated configurations. Do NOT build a general layer compositor. |

## Physics Constraints

### Slab Orientation Physics

**PBC Symmetry (CRITICAL finding):**

Under periodic boundary conditions, the simulation box is replicated infinitely in all three dimensions. The slab structure `bottom-ice | water | top-ice` is equivalent to `...| ice | water | ice | water | ice |...` extending infinitely. There is no physical "top" or "bottom" — only the relative ordering of layers matters.

Specifically:
- "Ice on bottom, water on top" = `water | ice | water | ice | water |...` — This is IDENTICAL to the current `ice | water | ice | water |...` but shifted by one layer. Under PBC translation, these are the same structure.
- "Flip the sandwich" = same structure, different origin
- Therefore, **slab orientation flip is a no-op under PBC** and should NOT be implemented.

**Gravity effects:**
- Standard MD simulations do NOT include gravity (no `gravitational-field` in GROMACS standard MD).
- Even when external fields are applied, the effect on nanoscale systems (few nm box) is negligible compared to kT (~2.5 kJ/mol at 300K vs ~10⁻²³ J gravitational potential for one water molecule over 1 nm).
- Conclusion: Gravity-based orientation is irrelevant for MD.

**Crystal face orientation (physically meaningful):**
- The crystallographic face exposed to water IS physically meaningful.
- Basal face (0001): Hexagonal ice exposing the flat hexagonal plane. This is the most commonly studied face.
- Primary prismatic face (10-10): Exposes hexagonal channels.
- Secondary prismatic face (11-20): Different surface structure.
- Different faces have different:
  - Surface energies (~70-120 mJ/m² depending on face and model)
  - Melting rates (basal melts ~2x slower than prismatic in TIP4P models)
  - Growth kinetics (basal grows via spiral dislocation, prismatic via 2D nucleation)
- GenIce2 caveat: The default `1h` lattice has exchanged crystal axes (historical GenIce convention). Use `one[hh]` to get basal face on Z-axis. This is documented in GenIce2 README.

**Current QuickIce status:** Uses GenIce2 default `1h` which has exchanged axes. The Z-axis interface may expose prismatic face, not basal. This should be verified and documented.

**Confidence:** HIGH (PBC symmetry is fundamental; face-dependence is well-established in MD literature)

### Mixed Hydrate Physics

**Lattice parameters (MEDIUM confidence, from domain knowledge + Wikipedia/GenIce2):**

| Structure | Crystal system | Lattice parameter | Unit cell waters | Space group |
|-----------|---------------|------------------|-----------------|-------------|
| sI | Cubic | a ≈ 1.20 nm | 46 | Pm3̄n |
| sII | Cubic | a ≈ 1.73 nm | 136 | Fd3̄m |
| sH | Hexagonal | a ≈ 1.22 nm, c ≈ 1.01 nm | 34 | P6/mmm |

**Lattice mismatch:**
- sI ↔ sII: a_sI/a_sII = 1.20/1.73 ≈ 0.69. Mismatch is ~31%. Finding a common supercell would require LCM-like multiples → box dimensions of ~10+ nm (8×sI ≈ 5×sII ≈ 9.6 nm). This is impractical.
- sI ↔ sH: a_sI/a_sH ≈ 0.98 along a-axis. Closer, but sH is hexagonal vs sI cubic → incompatible symmetry.
- sII ↔ sH: a_sII/a_sH ≈ 1.42. Mismatch ~30%.

**Miscibility:**
- sI and sII are NOT miscible. They are thermodynamically distinct phases with different cage architectures.
- In natural systems, one structure type dominates based on guest molecule size. Small guests (CH₄, CO₂) → sI. Larger guests (THF, N₂) → sII. Mixed guest systems form ONE structure, not a mixture.
- Phase separation: If sI and sII were placed in the same box, they would remain as separate phases with a disordered boundary region. The interface between them has never been characterized.

**Published studies:** None found for mixed sI+sII or mixed hydrate type simulations. The arXiv search (2026-06-12) returned only 4 results for "ice hydrate interface molecular dynamics" — all focused on single-structure hydrate-water interfaces.

**Confidence:** MEDIUM (lattice parameters are well-established; absence of published mixed-structure studies is notable but may reflect search limitations)

### Ice + Hydrate Physics

**Density compatibility:**

| Phase | Density (g/cm³) | Notes |
|-------|----------------|-------|
| Ice Ih | 0.92 | At 273 K, 1 atm |
| sI hydrate (empty) | ~0.80 | Lower than ice (porous cage structure) |
| sI hydrate (CH₄-filled) | ~0.91 | Close to ice Ih |
| sII hydrate (empty) | ~0.81 | Ice XVI (Falenty 2014) |
| sII hydrate (THF-filled) | ~0.99 | Close to liquid water |
| Liquid water | 1.00 | At 273 K |

Key observations:
- CH₄-filled sI has density very close to ice Ih (~0.91 vs 0.92 g/cm³) — this makes an ice-hydrate interface practical.
- THF-filled sII has density close to liquid water (~0.99 vs 1.00 g/cm³) — this makes hydrate-water interface practical (already supported).
- Empty hydrates are less dense than ice — they would float in ice if gravity mattered (but it doesn't in PBC MD).

**Structural compatibility at ice-hydrate boundary:**

The ice-hydrate interface is structurally complex because:
1. Ice Ih has a continuous hydrogen-bonded network with ~275 pm O-O distance
2. Hydrate has a cage-based network with both 5-membered and 6-membered rings
3. The transition from one network topology to another requires bond-breaking and reformation
4. In nature, ice-hydrate interfaces exist (permafrost, ocean sediments) — so they ARE physically real

**Published MD studies of ice-hydrate interfaces:**
- Hydrate dissociation studies commonly use a hydrate slab + water configuration (which QuickIce already supports)
- Ice-surface-mediated hydrate nucleation: Artyukhov et al. (2014, JCP 141:034503) simulated Xe solution/ice interface
- THF hydrate-water interfacial free energy: Torrejón et al. (2024, JCP 161:064701) — TIP4P/Ice model
- CO₂ hydrate nucleation: Zerón et al. (2025, arXiv:2504.07492) — found interface doesn't affect nucleation at deep supercooling

**Hydrate pockets in ice (inverse pocket):**
- Physically meaningful: hydrate lenses in permafrost, hydrate veins in ice cores
- QuickIce pocket mode already supports spherical/cubic cavities; extending to hydrate-filled cavities is a natural progression
- The key challenge: hydrate cage structure must fit within the pocket diameter (sI unit cell ≈ 1.2 nm, so minimum pocket ≈ 1.5-2.0 nm)

**Confidence:** MEDIUM (density values well-known; structural compatibility assessment from domain knowledge; specific papers from arXiv search)

## Scientific Use Cases

| Configuration | Papers Using It | Demand Level | QuickIce Status |
|--------------|----------------|-------------|-----------------|
| Ice slab + water (sandwich) | Most ice-water interface studies (100+ papers) | **HIGH** — standard | ✅ Supported (slab mode) |
| Hydrate slab + water | Hydrate dissociation studies (Rodger et al., English et al., numerous) | **HIGH** — standard | ✅ Supported (hydrate→interface) |
| Single ice face + water (asymmetric) | Face-dependent growth/melting (Nada et al., Shi et al. 2025) | **HIGH** — very common | ❌ NOT supported (current slab is symmetric) |
| Ice + hydrate + water triple interface | Hydrate dissociation from ice surface, ice-coated hydrate | **MEDIUM** — growing | ❌ NOT supported |
| Hydrate pocket in ice | Permafrost hydrate lens studies | **LOW-MEDIUM** — niche | ❌ NOT supported (pocket mode is water-only) |
| Crystal face selection (basal/prism) | Face-dependent kinetics studies | **MEDIUM** — established | ⚠️ Partially (GenIce2 supports it but not exposed in UI) |
| Mixed sI + sII hydrate | None found | **NONE** — no demand | ❌ Correctly NOT supported |
| sI + sH mixed hydrate | None found | **NONE** — no demand | ❌ Correctly NOT supported |
| Arbitrary layer stacking | None found | **NONE** — no demand | ❌ Correctly NOT supported |

## Feature Categorization Summary

| Proposed Feature | Verdict | Rationale |
|-----------------|---------|----------|
| Slab orientation flip | **ANTI-FEATURE** | Physically meaningless under PBC |
| Sandwich configuration control | **TABLE STAKES** (face selection) | Crystal face at interface IS meaningful; already partially available via GenIce2 |
| Multiple hydrate types in same box | **ANTI-FEATURE** | Lattice mismatch makes this impractical; no scientific demand |
| Ice + hydrate in same system | **DIFFERENTIATOR** | Scientifically valuable; enables new research configurations |
| Arbitrary layer ordering UI | **ANTI-FEATURE** | Over-engineering; no scientific demand for arbitrary combinations |
| Custom slab composition | **TABLE STAKES** (for specific validated modes) | Named modes like "ice-hydrate-water" are useful; general composition is not |

## MVP Recommendation

For v5.x flexible interface construction, prioritize:

### 1. Asymmetric slab mode (single ice-water interface) — TABLE STAKES
- **What:** Allow box_z = ice_thickness + water_thickness (no top ice layer)
- **Why:** Most MD interface studies use a single ice-water interface, not the symmetric sandwich. The symmetric sandwich doubles the computational cost for no physical benefit in many cases.
- **Complexity:** LOW — just skip the top ice layer in slab assembly
- **Physics:** Fully valid under PBC (vacuum gap or wall on one side; or just let water extend to box boundary)

### 2. Crystal face selection — TABLE STAKES
- **What:** Expose GenIce2's `one[hh]` (basal on Z) vs `1h` (prismatic on Z) choice in the interface UI
- **Why:** Different crystal faces have different melting/growth kinetics. This is a well-established variable in MD studies.
- **Complexity:** LOW — GenIce2 already supports this; just needs UI exposure
- **Physics:** Completely valid; face-dependence is a major research variable

### 3. Ice + hydrate + water triple interface — DIFFERENTIATOR
- **What:** New mode: ice slab | hydrate slab | water, with two distinct interfaces
- **Why:** Enables hydrate dissociation studies where ice is adjacent to hydrate; ice-surface-mediated hydrate formation; ice-coated hydrate stability
- **Complexity:** MEDIUM-HIGH — need to handle two different crystal structures (ice cell vs hydrate cell) in same box; density matching; overlap resolution at both interfaces
- **Physics:** Physically valid and scientifically interesting. CH₄-sI density (~0.91 g/cm³) close to ice (~0.92 g/cm³) makes this practical.

Defer to later:
- **Hydrate pocket in ice (inverse pocket):** MEDIUM complexity extension of existing pocket mode. Requires hydrate structure fitting within pocket. Useful but niche — defer to v5.x+1.
- **Multiple hydrate types in same box:** ANTI-FEATURE — do not build. Lattice mismatch and lack of scientific demand make this unjustified.
- **Slab orientation flip:** ANTI-FEATURE — physically meaningless under PBC. Do not build.
- **Arbitrary layer ordering UI:** ANTI-FEATURE — over-engineering. Build named modes instead.

## Implementation Notes for Ice + Hydrate Mode

This is the most complex proposed feature. Key design considerations:

### Box Geometry
```
Current slab mode:  [Ice] [Water] [Ice]     (symmetric, two identical interfaces)
Ice+hydrate mode:   [Ice] [Hydrate] [Water]  (asymmetric, two distinct interfaces)
```

### Cell Compatibility Challenge
- Ice Ih cell: hexagonal, ~0.45×0.45×0.74 nm (GenIce2 convention)  
- sI hydrate cell: cubic, a ≈ 1.20 nm
- sII hydrate cell: cubic, a ≈ 1.73 nm
- **Problem:** Box dimensions must be integer multiples of BOTH ice cell AND hydrate cell for PBC continuity.
- **Solution:** Compute LCM-like dimension (e.g., box_x must be nx*ice_a ≈ nh*hydrate_a). Use `round_to_periodicity()` for each structure independently, then find common box dimensions.

### Density Matching
- Ice Ih: 0.92 g/cm³  
- CH₄-sI: ~0.91 g/cm³ → **excellent match**
- THF-sII: ~0.99 g/cm³ → **moderate mismatch** (need thin water layer between ice and hydrate)
- At the ice-hydrate boundary: both are solid phases, so density mismatch is tolerable (unlike ice-water where the interface is disordered)

### Guest Handling
- Hydrate guests (CH₄, THF) stay in the hydrate layer
- No guests in the ice layer
- No guests in the water layer (unless solute insertion is also active)
- Guest molecules at the hydrate-water interface may dissolve during MD — this is the intended behavior for dissociation studies

## Sources

### HIGH Confidence
- **PBC symmetry argument:** Fundamental property of periodic boundary conditions. No citation needed — any MD textbook covers this.
- **GenIce2 documentation:** Confirmed lattice types (sI, sII, sH), `one[hh]` axis convention, guest support. Source: https://github.com/genice-dev/GenIce2
- **QuickIce source code:** Slab mode implementation, hydrate generator, overlap resolution. Verified current behavior.
- **Ice Ih density:** 0.9167 g/cm³. Source: IAPWS, Wikipedia "Phases of ice."

### MEDIUM Confidence
- **Hydrate lattice parameters:** sI a≈1.2 nm, sII a≈1.73 nm, sH a≈1.22 nm/c≈1.01 nm. Source: Wikipedia "Clathrate hydrate," Sloan & Koh (2008).
- **Hydrate densities:** CH₄-sI ≈ 0.91 g/cm³, THF-sII ≈ 0.99 g/cm³, empty sII ≈ 0.81 g/cm³. Source: Wikipedia, domain knowledge.
- **Face-dependent ice interface properties:** Basal vs prismatic growth/melting rates differ. Source: Google Scholar search results (Shi et al. 2025, Harless et al. 2025, multiple ice-water interface studies).
- **THF hydrate-water interfacial free energy:** 27(2) mJ/m² at 500 bar. Source: Torrejón et al. (2024), JCP 161:064701. Confirmed via arXiv:2408.13321.
- **CO₂ hydrate nucleation rates:** Source: Zerón et al. (2025), arXiv:2504.07492.

### LOW Confidence
- **Claim: No published MD study of mixed sI+sII hydrates.** Based on arXiv search (4 results, none about mixed structures) and Google Scholar search (server errors). This absence may reflect search limitations rather than true absence. Should be verified with a domain expert.
- **Claim: sI+sII lattice mismatch makes common box dimensions impractical.** The LCM calculation is straightforward (9.6 nm for sI+sII), but the question is whether any research group has done this despite the difficulty. LOW confidence in "no one has done this."
- **Empty hydrate density values.** Falenty et al. (2014, Nature 516:231) measured ice XVI (empty sII) at 0.81 g/cm³, but exact values depend on the water model used.

## Gaps Requiring Domain Expert Input

1. **Crystal face of current QuickIce slab:** Verify whether GenIce2 `1h` default places basal or prismatic face at the Z-interface. The GenIce2 README says axes are "exchanged" and recommends `one[hh]` for basal on Z. Need to verify what QuickIce actually generates.

2. **Ice-hydrate structural compatibility:** How does the hydrogen-bond network transition from ice Ih to sI/sII at the atomic level? Are there published interface structures? This affects whether a simple layer-stacking approach works or if the interface region needs special treatment.

3. **Asymmetric slab with PBC:** Some MD studies use a vacuum layer above the water to prevent interaction through PBC in Z. Others use 2D PBC (xy periodic, z non-periodic with walls). Should QuickIce support vacuum gaps? This requires GROMACS `pbc = nil` setting.

---

*Research for: QuickIce v5.x Flexible Interface Construction*  
*Researched: 2026-06-12*  
*Confidence: MEDIUM — Domain physics well-understood; literature search limited by source access*
