# Synthesis: Complex Hydrate Generation

**Date:** 2026-06-12
**Confidence:** HIGH

## Executive Verdict

Build complex hydrate support as a phased extension of QuickIce's existing GenIce2 integration — do NOT introduce atomsk as a dependency. GenIce2 already provides 80%+ of the needed functionality (filled ices, semiclathrates, mixed occupancy, CIF import, custom plugins), and the gap between what GenIce2 can do and what QuickIce exposes is almost entirely trivial config changes (~300-400 LOC). The highest-impact move is to expose GenIce2's existing capabilities in the QuickIce UI ("free wins"), then layer on CIF import and a Python-native polycrystal builder. Atomsk's `--polycrystal` mode is the only genuinely valuable atomsk feature for hydrate research, but a Python implementation using `scipy.spatial` delivers strictly superior results (multi-phase grains, native GRO output, molecular-integrity-preserving overlap removal) at ~250-370 LOC with no GPL complications.

## Phase Structure

### Phase 1: "Free Wins" — Expose Existing GenIce2 Features
**Effort:** LOW (~300-400 LOC) | **Risk:** LOW | **Value:** HIGH
**What:**
- Add filled ice lattice types to `HYDRATE_LATTICES`: `c0te`, `c1te`, `c2te`, `ice1hte`, `sTprime`
- Add Ice XVII/XVI lattice types: `ice17`, `ice16`
- Add guest molecules to `GUEST_MOLECULES`: `co2`, `H2`, `et` (ethane)
- Add water model dropdown: TIP3P, TIP5P, SPC/E (GenIce2 supports 7 models)
- Add mixed cage occupancy UI: two guests per cage type with occupancy sliders
- Add per-cage guest assignment (`-G` flag support)
- Add `depol` mode selector (`strict` vs `optimal`)
- Refactor export for multi-guest `.itp` files (binary clathrates)
**Why first:** GenIce2's Python API already supports all of these — verified by hands-on testing (FEASIBILITY.md, 14/14 tests passed). This unlocks 80% of scientific value for 20% of the effort. Per FEATURES.md, filled ices + CO₂ guest + mixed occupancy are the #1, #2, and #3 priorities by impact×effort.
**Pitfalls to avoid:** P5 (water model hardcoding — currently TIP4P-ICE only), P13 (multi-guest ITP handling — refactor `HydrateGROMACSExporter`), P4 (non-orthogonal PBC for filled ices — test c0te with γ=120°)

### Phase 2: CIF Import Pipeline
**Effort:** MEDIUM (~200-300 LOC) | **Risk:** MEDIUM | **Value:** HIGH
**What:**
- Add `genice2-cif` as optional dependency (`pip install quickice[cif]`)
- Add "Import CIF" button + file picker to hydrate panel
- Run `assess_cages=True` after CIF import to auto-detect cages
- Display detected cage types for guest assignment
- Add IZA Zeolite Database browser (`zeolite[ITT]` syntax)
- Add CIF validation layer (pymatgen `Structure.from_file()` pre-check)
**Why second:** Maximizes flexibility — any hydrate with a CIF file becomes importable. genice2-cif is now installed and tested (FEASIBILITY.md). CIF quality varies, so validation is essential (PITFALLS.md P8).
**Pitfalls to avoid:** P8 (CIF quality — add pymatgen validation), P3 (unknown cage occupancy — always run `assess_cages`), P12 (genice2-cif not installed — pre-flight check + optional dep)

### Phase 3: Python Polycrystal Builder
**Effort:** MEDIUM (~250-370 LOC) | **Risk:** MEDIUM | **Value:** MEDIUM-HIGH
**What:**
- Build Voronoi polycrystal generator in pure Python using `scipy.spatial.Voronoi` + `cKDTree`
- Periodic boundary conditions via 3×3×3 image replication (standard technique)
- Grain rotation via `scipy.spatial.transform.Rotation`
- Atom assignment via `cKDTree` (nearest-grain-node, PBC-aware)
- Grain boundary cleanup via existing `overlap_resolver.py` (whole-molecule removal)
- Multi-phase support: different grains can be sI, sII, sH, or ice
- Native GRO output via existing `gromacs_writer.py`
**Why third:** Polycrystalline hydrate is a real scientific use case (7+ papers in PRL, J. Phys. Chem. B, Fuel — per ATOMSK-HYDRATE-DEEPDIVE.md). Python implementation is superior to atomsk: multi-phase grains (atomsk is single-seed only), GRO output (atomsk has no GRO support), molecular-integrity-preserving cleanup. ~55% of code reuses existing QuickIce components. Per POLYCRYSTAL-FEASIBILITY.md, this is feasible with managed risks.
**Pitfalls to avoid:** Periodic Voronoi edge cases (test with known crystal systems), multi-seed density mismatch (validate cross-section compatibility), rotation of non-cubic cells (all current hydrate lattices are cubic — low risk now)

### Phase 4: Custom Lattice Plugins
**Effort:** MEDIUM per lattice (~40-80 LOC) | **Risk:** LOW | **Value:** MEDIUM
**What:**
- Build "Custom Lattice" wizard: space group + lattice params + asymmetric unit → GenIce2 Lattice module
- Pre-built TBAB semiclathrate plugin (most-requested semiclathrate)
- Custom molecule plugin wizard for multi-H₂ occupancy (virtual "2H₂"/"4H₂" molecule)
- Bundle validated ITP files for semiclathrate ions (TBA, Br)
**Why fourth:** Addresses the ~5% of use cases not covered by built-in GenIce2 or CIF import. Semiclathrate TBAB requires multi-step manual assembly even in GenIce2's own CLI (FEATURES.md), so a one-click preset has high UX value. Custom molecule plugins are ~10 LOC each (FEASIBILITY.md).
**Pitfalls to avoid:** P2 (ice rules — always use GenIce2 for O-networks), P6 (FF parameters for exotic ions — need validated TBA/Br .itp files), semiclathrate requires `--depol=optimal` (not `strict`)

### Phase 5: Packmol Integration (defer)
**Effort:** MEDIUM | **Risk:** MEDIUM | **Value:** LOW-MEDIUM
**What:**
- Packmol subprocess for complex guest placement inside cages
- Cage center extraction from GenIce2 output
- Packmol input file generation
**Why deferred:** GenIce2's `-g`/`-G`/`-H` flags cover most guest placement needs. Packmol is only needed for large organic guests that GenIce2 can't handle. Semiclathrate butyl groups are the primary use case, but Phase 4 handles those via custom molecule plugins. Per ARCHITECTURE.md Option E, this is a v7+ feature.

## Quick Wins

GenIce2 features already available but NOT exposed in QuickIce (per FEATURES.md gap analysis):

- **5 filled ice lattices:** `c0te`, `c1te`, `c2te`, `ice1hte`, `sTprime` — just add to `HYDRATE_LATTICES` dict
- **3 guest molecules:** CO₂ (`co2`), H₂ (`H2`), ethane (`et`) — just add to `GUEST_MOLECULES` dict
- **6 additional water models:** TIP3P, TIP5P, SPC/E, 4-site, 5-site, 7-site — just add dropdown
- **Mixed cage occupancy:** `-g 12=co2*0.6+me*0.4` syntax — just pass through to GenIce2 API
- **Per-cage guest assignment:** `spot_guests={0: 'me', 2: 'co2'}` — just pass through to GenIce2 API
- **2 exotic ice lattices:** Ice XVII (`17`), Ice XVI (`16`) — just add to `HYDRATE_LATTICES`
- **CIF import:** `genice2 "cif[hydrate.cif:O=O]"` — just install genice2-cif + add file picker

## Anti-Features

| What to NOT build | Why |
|--------------------|-----|
| **Atomsk integration for structure generation** | Atomsk cannot generate any hydrate lattice. GenIce2 already does everything (FEASIBILITY.md: 95%+ coverage) |
| **Atomsk subprocess for polycrystal assembly** | Python can do this better: multi-phase grains, GRO output, molecular integrity, no GPL complexity (POLYCRYSTAL-FEASIBILITY.md) |
| **Custom lattice cage editor (drawing cages from scratch)** | Enormous scope; GenIce2 has 249+ lattices; no user would build a novel cage by hand (FEATURES.md) |
| **Amorphous hydrate generation** | Requires completely different algorithm (melt-quench MD); out of scope (FEATURES.md) |
| **Hydrate formation/nucleation simulation** | Entirely different problem from structure generation; would be a separate product |
| **Force field parameterization for exotic guests** | Requires QM calculations; not a structure generator's job (FEATURES.md) |
| **Pure Python structure builder bypassing GenIce2** | No ice rules, no depolarization — structures would be physically unrealistic (PITFALLS.md P2, ARCHITECTURE.md Option C verdict) |
| **Superionic ice (XVIII/XX)** | Not a hydrate; requires >4 GPa; quantum regime; out of scope entirely |

## Risk-Adjusted Priority

| Phase | Effort | Risk | Value | Priority | Rationale |
|-------|--------|------|-------|----------|-----------|
| 1: Free Wins | LOW | LOW | HIGH | **CRITICAL** | 80% value / 20% effort; all backend verified |
| 2: CIF Import | MEDIUM | MEDIUM | HIGH | **HIGH** | Enables arbitrary structures; validation layer needed |
| 3: Python Polycrystal | MEDIUM | MEDIUM | MED-HIGH | **HIGH** | Killer feature (multi-phase); no atomsk dependency |
| 4: Custom Lattice Plugins | MEDIUM | LOW | MEDIUM | **MEDIUM** | Niche use; easy per-plugin; ~40-80 LOC each |
| 5: Packmol | MEDIUM | MEDIUM | LOW-MED | **LOW** | GenIce2 guest system covers most needs |

## Cross-Cutting Insights

1. **GenIce2 is the single source of truth for ice structures.** Always use GenIce2 for any structure containing a water O-network. Never bypass it with pymatgen or manual placement — ice rules + depolarization are GenIce2's unique, irreplaceable capability (PITFALLS.md P2, ARCHITECTURE.md anti-pattern 2). pymatgen is a supporting tool (CIF validation, format conversion), never a replacement.

2. **Atomsk is obsolete for QuickIce's needs.** The original research question was "should we use atomsk?" The answer across all 7 files is definitively NO. For structure generation, GenIce2 is superior. For polycrystal assembly, Python is superior. For stacking/merging, QuickIce's existing code is superior. The GPL-3.0 license adds zero value that can't be obtained more cleanly elsewhere (STACK.md, POLYCRYSTAL-FEASIBILITY.md).

3. **The format conversion tax is real.** Atomsk's lack of GRO support means any atomsk pipeline needs GenIce2→XYZ→atomsk→LAMMPS→MDAnalysis→GRO, losing residue names at every step (ATOMSK-HYDRATE-DEEPDIVE.md). Python-native paths avoid this entirely: GenIce2 API → builder → GRO writer, all in Python, all preserving molecular identity.

4. **Multi-phase polycrystals are the differentiator.** Atomsk's `--polycrystal` uses a single seed for all grains. Python's cKDTree assignment means each grain can have a different structure (sI + sII + ice Ih in the same system). This is impossible with atomsk and is a genuine scientific need (POLYCRYSTAL-FEASIBILITY.md "Killer Feature").

5. **GenIce2 version pinning is important.** QuickIce is tightly coupled to GenIce2's internal API (`safe_import`, `parse_guest`, `GenIce.__init__`). Pin `genice2>=2.2.13,<2.3` in pyproject.toml and add integration tests (PITFALLS.md P9).

6. **Semiclathrates are harder than they look.** TBAB requires multi-step manual assembly even in GenIce2's own CLI (`HS1` + `-c` + `-a` + `-H` + `--depol=optimal`). There is no one-click solution. A TBAB preset requires careful cage+ion mapping that should be validated with domain experts before committing to a GUI design (FEATURES.md, FEASIBILITY.md).

7. **The .itp file bottleneck.** Every new guest molecule and water model needs validated GROMACS topology files. CO₂ needs Zhang-Sprik parameters, H₂ needs Vehkamäki parameters, ethane needs OPLS-AA with TIP4P-ICE cross-parameters. These are NOT trivial — wrong LJ parameters mean guests escape cages during MD (PITFALLS.md P6).

## Open Questions

1. **CIF availability for target structures** — Filled ices are in GenIce2 source; TBAB is in ICSD (commercial, ~€5000/yr); TBPB/TMAF are limited. Need to determine which CIFs to bundle vs. require user-supplied. (FEATURES.md crystallographic data section)

2. **Semiclathrate cage+ion mapping** — The HS1 lattice has specific cage IDs adjacent to specific dopant positions, discoverable only by running `--assess_cages`. A one-click TBAB preset needs this mapping hardcoded, but it hasn't been extracted yet. Needs domain-expert validation. (FEASIBILITY.md, FEATURES.md)

3. **Periodic Voronoi tessellation edge cases** — The 3×3×3 image replication approach is standard but needs testing with known crystal systems (BCC Fe, FCC Al) where Voronoi regions are well-characterized. Specifically: vertex wrapping at box boundaries, open (infinite) Voronoi regions near edges. (POLYCRYSTAL-FEASIBILITY.md)

4. **Multi-phase polycrystal lattice mismatch** — When sI (a=11.8Å) and sII (a=17.3Å) grains share a box, the cross-section mismatch must be managed. Need to determine minimum acceptable mismatch threshold and whether strain compensation is needed. (ATOMSK-HYDRATE-DEEPDIVE.md, POLYCRYSTAL-FEASIBILITY.md)

5. **ITP parameter provenance** — Which parameterization source for CO₂ in hydrates? Zhang-Sprik is common in literature but has multiple variants. Need to pick one and document the choice. (PITFALLS.md P6)

6. **GenIce2 `assess_cages` for semiclathrates** — Tested for clathrates (works) and filled ices (correctly returns "no cages"). Not yet tested for semiclathrate water frameworks where cages may be partially disrupted by ions. (FEASIBILITY.md)

## Sources (Aggregated)

| Source | Files Using It | Confidence |
|--------|---------------|------------|
| GenIce2 source code (local inspection) | STACK, FEASIBILITY, ARCHITECTURE, PITFALLS | HIGH |
| GenIce2 hands-on API testing (14/14 passed) | FEASIBILITY, ARCHITECTURE | HIGH |
| QuickIce source code (local) | ARCHITECTURE, PITFALLS, POLYCRYSTAL-FEASIBILITY | HIGH |
| Atomsk official documentation | STACK, ATOMSK-HYDRATE-DEEPDIVE | HIGH |
| Atomsk citation list (7+ hydrate papers) | ATOMSK-HYDRATE-DEEPDIVE, FEASIBILITY | MEDIUM-HIGH |
| Sveinsson & Cao (2025) — explicit ATOMSK use | ATOMSK-HYDRATE-DEEPDIVE | MEDIUM |
| genice2-cif plugin (now installed + tested) | FEASIBILITY, ARCHITECTURE | HIGH |
| pymatgen documentation | STACK, ARCHITECTURE | HIGH |
| scipy.spatial API documentation | POLYCRYSTAL-FEASIBILITY | HIGH |
| GPL-3.0 license text + FSF FAQ | STACK, ATOMSK-HYDRATE-DEEPDIVE | HIGH |
| GROMACS manual (triclinic boxes) | PITFALLS | MEDIUM |
