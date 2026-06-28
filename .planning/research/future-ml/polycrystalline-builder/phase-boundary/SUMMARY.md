# Research Summary: Phase Boundary Physics for Polycrystalline Builder

**Domain:** Polycrystalline ice/hydrate/water — phase boundary characterization and handling
**Researched:** 2026-06-28
**Overall confidence:** MEDIUM (grain boundary physics: HIGH; phase boundary between incompatible lattices: MEDIUM; hydrate-ice interfaces: MEDIUM-HIGH; PBC geometry: HIGH; minimum grain sizes: MEDIUM; MD workflow: MEDIUM)

## Executive Summary

Phase boundaries in polycrystalline ice systems fall into three tiers of difficulty. **Same-phase grain boundaries** (Ice Ih ↔ Ice Ih with different orientations) are the best-studied case: MD simulations show disordered boundary widths of ~1 nm (Yagasaki et al. 2020, J. Chem. Phys. 152, 094703; Moreira et al. 2018, Phys. Chem. Chem. Phys. 20, 1995; Ribeiro & Koning 2021, J. Phys. Chem. C 125, 18297), and Voronoi-based polycrystalline construction with energy minimization is well-established (Davies et al. 2025, Phys. Rev. B; Chen et al. 2023, World Scientific; Li et al. 2024, ACS Appl. Mater. Interfaces). **Ice-water and hydrate-water interfaces** are well-studied for growth/dissociation (Kumar et al. 2025, PCCP; Pirzadeh & Kusalik 2013, JACS; Zhang & Guo 2017, PCCP), and QuickIce's existing `overlap_resolver.py` already handles the overlap-removal pattern. **Cross-phase boundaries between incompatible lattices** (Ice Ih ↔ Ice II, hydrate ↔ Ice Ih) are the hardest case: Nguyen et al. 2015 (J. Phys. Chem. C 119, 2856) showed definitively that "there is no lattice matching between any plane of ice and clathrate hydrates," and the interface always contains a ~1 nm disordered interfacial layer rich in 5-membered rings. Density mismatches (Ice Ih 0.92 g/cm³ vs Ice II 1.18 g/cm³ vs sI hydrate framework 0.79 g/cm³) create void/overlap zones at boundaries that must be resolved.

The recommended approach is a **three-tier boundary strategy**: (1) same-phase grain boundaries get Voronoi-based crystal orientation assignment with ~1 nm disordered buffer accepted by MD; (2) same-water-model phase boundaries (Ice Ih ↔ liquid, hydrate ↔ liquid) use overlap-removal as in current QuickIce interface modes; (3) incompatible-lattice phase boundaries (Ice Ih ↔ Ice II, hydrate ↔ Ice Ih) **require a disordered water buffer zone** of at least 1–2 nm between the phases. Trying to stitch incompatible lattices directly will produce artifacts that crash GROMACS energy minimization.

For PBC-aware shape editing, shapely operates in Euclidean 2D and cannot handle shapes that wrap across periodic boundaries. The recommended approach is to **constrain user-drawn shapes to not cross box boundaries** in the initial implementation, with a "split and wrap" mode deferred to a later phase. This is simpler, avoids geometric ambiguity, and matches how Atomsk and OVITO handle periodic polycrystals.

Minimum grain sizes are phase-dependent: Ice Ih needs ≥2×2×2 unit cells (~300 molecules), sI hydrate needs ≥1 unit cell (~46 water + ~8 guest molecules), and Ice II needs ≥1 unit cell (~12 molecules per hexagonal ring, ~312 total). Grains below these sizes may still produce valid GROMACS starting structures but will have extremely long equilibration times and may not retain crystal identity during MD.

## Key Findings

**Grain boundaries:** Ice Ih grain boundaries are ~1 nm thick disordered regions with enhanced molecular diffusion (MEDIUM-HIGH confidence, supported by multiple MD studies). Tilt boundaries around ⟨0001⟩ axis are the best-characterized (Li et al. 2024). Grain boundary sliding is a key deformation mechanism (Ribeiro & Koning 2021). The quasi-liquid layer at grain boundaries differs from the ice-vapor interface (Yagasaki et al. 2020).

**Phase boundary mismatches:** No lattice matching exists between ice Ih and any clathrate hydrate structure (HIGH confidence — Nguyen et al. 2015). Ice Ih ↔ Ice II boundaries are fundamentally incompatible due to density (0.92 vs 1.18 g/cm³) and symmetry (hexagonal vs rhombohedral) differences. A disordered buffer zone is the standard approach.

**Hydrate-ice boundaries:** Zhang & Guo 2017 showed that ice surfaces promote methane hydrate nucleation through lattice mismatch-driven quasi-liquid layers. Pirzadeh & Kusalik 2013 demonstrated that clathrate hydrate can nucleate at ice-solution interfaces. Naeiji et al. 2019 showed that an ice shell can form around clathrate hydrates during anomalous preservation, creating a closed hydrate-ice boundary. The hydrate-ice interface always contains a disordered transition region of ~1 nm.

**PBC implications:** Shapely does NOT understand PBC. Shapes crossing box edges must be handled explicitly. Recommendation: constrain shapes to box boundaries in v7.0, add PBC-wrap in v8.0.

**Minimum grain sizes:** Practical minimums: Ice Ih ≥300 molecules, Ice II ≥312, sI hydrate ≥740 (water+guests), liquid water ≥~200 molecules. Below minimum: MD may survive but with very long equilibration.

**MD workflow:** Standard protocol: steepest descent minimization (5000–50000 steps) → NVT equilibration (100–500 ps) → production. Polycrystalline starting structures converge slowly due to grain boundary energy. Multi-phase systems need longer minimization. GROMACS handles this well if there are no steric clashes (overlap ≤ 0.1 nm O-O).

**Density matching:** Ice Ih (0.917 g/cm³), Ice II (1.18), Ice III (1.16), Ice V (1.24), Ice VI (1.31), sI hydrate framework (~0.795), liquid water (~1.0). Volume mismatches at boundaries must be handled by overlap removal or buffer zone insertion.

## Implications for Roadmap

Based on research, suggested phase structure for polycrystalline builder:

1. **Phase 1: Same-phase polycrystal (Ice Ih only)** — Voronoi-based grain generation with random crystal orientations. Lowest risk, well-studied physics. Grain boundaries naturally form disordered regions that MD can equilibrate. Addresses: grain boundary creation, orientation assignment, PBC-safe Voronoi tessellation.

2. **Phase 2: Ice + liquid water polycrystal** — Extend with liquid water grains/regions. Uses existing overlap_resolver.py pattern. Addresses: ice-water boundary handling, density scaling, water filler integration.

3. **Phase 3: Multi-ice-phase polycrystal** — Add Ice II, Ice V, etc. with incompatible lattice boundaries. Requires buffer zone insertion algorithm. Addresses: phase mismatch handling, density mismatch compensation, buffer zone generation.

4. **Phase 4: Hydrate-containing polycrystal** — Add hydrate (sI/sII/sH) grains adjacent to ice or liquid. Most complex boundary type. Addresses: hydrate-ice interface, guest molecule handling at boundaries, hydrate-liquid water boundary.

**Phase ordering rationale:**
- Phase 1 establishes the Voronoi framework (most code, best understood physics)
- Phase 2 leverages existing QuickIce overlap-resolver infrastructure
- Phase 3 requires new buffer-zone code (architectural addition)
- Phase 4 requires both buffer-zone AND guest-molecule-handling code (most complex)

**Research flags for phases:**
- Phase 3: Buffer zone width and composition needs validation (are 5-membered rings needed? Can pure disordered water suffice?)
- Phase 4: Guest molecule escape from hydrate cages at boundaries needs investigation
- All phases: GROMACS energy minimization convergence criteria for polycrystalline starting structures need empirical validation

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Grain boundary physics (Ice Ih) | HIGH | Multiple MD studies agree: ~1 nm width, disordered, enhanced diffusion |
| Grain boundaries (high-pressure ice) | LOW | Very few MD studies; Ice II/III/V/VI grain boundaries not well characterized |
| Ice-clathrate interface structure | MEDIUM-HIGH | Nguyen et al. 2015 is definitive but 11 years old; no contradicting studies found |
| Hydrate-ice nucleation interface | MEDIUM-HIGH | Zhang & Guo 2017, Pirzadeh & Kusalik 2013 agree; TIP4P-ICE model used |
| Phase boundary mismatch handling | MEDIUM | Disordered buffer zone is standard practice, but width/composition details vary |
| PBC implications for shape editing | HIGH | Geometric reasoning, shapely documentation confirm |
| Minimum grain sizes | MEDIUM | Based on unit cell sizes + MD best practices; no systematic study found |
| MD workflow for polycrystalline ice | MEDIUM | Standard GROMACS protocol; convergence for multi-phase systems not well documented |
| Density mismatch handling | MEDIUM | Physical values are well-known; algorithmic approach (buffer/overlap) is standard |

## Gaps to Address

- **High-pressure ice grain boundaries**: No MD data found for Ice II, III, V, VI grain boundaries. May need to treat all high-pressure ice phase boundaries as "incompatible" requiring buffer zones.
- **Buffer zone composition**: Is a simple disordered water layer sufficient, or are 5-membered rings (as seen at hydrate-ice interfaces) necessary for stability?
- **Minimum grain validation**: What happens to grains that are too small — does GROMACS energy minimization converge, or does the crystal identity collapse? This needs empirical testing.
- **Phase transformation kinetics**: At temperatures near phase boundaries (e.g., 250 K at 300 MPa near Ice Ih/II/III triple point), will the MD spontaneously transform one phase into another? This limits which multi-phase structures are physically meaningful.
- **PBC-wrap for shapes**: The geometric algorithm for splitting a shapely polygon at a periodic boundary and wrapping it is non-trivial. Deferred to later phase.

## Sources

- Yagasaki, Matsumoto, Tanaka (2020) "Molecular dynamics study of grain boundaries and triple junctions in ice" J. Chem. Phys. 152, 094703 — grain boundary width ~1 nm at 250 K
- Moreira, Veiga et al. (2018) "Anomalous diffusion of water molecules at grain boundaries in ice Ih" Phys. Chem. Chem. Phys. 20, 1995 — enhanced diffusion at GBs
- Ribeiro & Koning (2021) "Grain-Boundary Sliding in Ice Ih: Tribology and Rheology at the Nanoscale" J. Phys. Chem. C 125, 18297 — GB sliding mechanism
- Li, Phan, Zhang, Xu et al. (2024) "Computational Characterization of Symmetric Tilt Grain Boundaries in Ice" ACS Appl. Mater. Interfaces — ⟨0001⟩ tilt boundaries
- Chen, Tao, Kröger, Li (2023) "Inverse Hall-Petch effect in nanocrystalline ice" — Voronoi polycrystalline construction with mW model
- Nguyen, Koc, Shepherd et al. (2015) "Structure of the ice-clathrate interface" J. Phys. Chem. C 119, 2856 — **no lattice matching between ice and clathrate**
- Zhang & Guo (2017) "The effects of ice on methane hydrate nucleation" PCCP 19, 20737 — ice promotes hydrate nucleation via quasi-liquid layer
- Pirzadeh & Kusalik (2013) "Molecular insights into clathrate hydrate nucleation at an ice-solution interface" JACS 135, 7278 — hydrate nucleation at ice surface
- Kumar, Huang, Wu, Lin (2025) "Accelerated Methane Hydrate Nucleation near Ice" J. Phys. Chem. C — thick interfacial layer at ice-sI interface
- Naeiji, Woo, Alavi et al. (2019) "Molecular dynamic simulations of clathrate hydrate anomalous preservation" J. Phys. Chem. C 123, 11438 — ice shell around hydrate
- Davies, Rosu-Finsen, Salzmann et al. (2025) "Low-density amorphous ice contains crystalline ice grains" Phys. Rev. B — Voronoi polycrystalline ice + TIP4P/2005
- Lu, McCartney, Sadtchenko (2007) "Fast thermal desorption spectroscopy study of H/D isotopic exchange in polycrystalline ice" J. Chem. Phys. 126, 114702 — grain boundary width few nm at -2°C
- Chen, Maki, Nagashima, Murata et al. (2020) "Quasi-liquid layers in grooves of grain boundaries and on grain surfaces of polycrystalline ice thin films" Cryst. Growth Des. — QLL at GBs
- Wikipedia: Phases of ice — density and lattice parameter reference data
- Wikipedia: Clathrate hydrate — structural data (sI/sII/sH)
- Atomsk (Hirel 2015, Comput. Phys. Comm. 197, 212) — polycrystal generation tool (GPL-3.0, incompatible with QuickIce)
- QuickIce codebase: `PHASE_METADATA` in `lookup.py`, `overlap_resolver.py`, `interface_builder.py`, `water_filler.py`
