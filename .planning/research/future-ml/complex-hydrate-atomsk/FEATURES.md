# Feature Landscape: Complex Hydrate Generation

**Domain:** Clathrate hydrate molecular dynamics simulation
**Researched:** 2026-06-12
**Overall confidence:** MEDIUM

## Table Stakes

Features users expect for complex hydrate MD. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | GenIce2 Support | Notes |
|---------|-------------|------------|-----------------|-------|
| Filled ice C0 | Planetary science, high-pressure studies | Low | YES (`c0te`) | Already in GenIce2, NOT in QuickIce |
| Filled ice C1 | Hydrogen hydrate, energy storage | Low | YES (`c1te`) | Already in GenIce2, NOT in QuickIce |
| Filled ice C2 | Cubic filled ice, high-pressure | Low | YES (`c2te`) | Already in GenIce2, NOT in QuickIce |
| Filled ice Ih (He/Ne) | Noble gas hydrate studies | Low | YES (`ice1hte`) | Already in GenIce2, NOT in QuickIce |
| Filled ice sT' | Hydrogen storage, ultrahigh-pressure | Low | YES (`sTprime`) | Already in GenIce2, NOT in QuickIce |
| CO2 guest molecule | CO2 sequestration, climate science | Low | YES (`co2`) | Already in GenIce2, NOT in QuickIce |
| H2 guest molecule | Hydrogen storage, energy applications | Low | YES (`H2`) | Already in GenIce2, NOT in QuickIce |
| Ethane guest | Binary/mixed hydrate studies | Low | YES (`et`) | Already in GenIce2, NOT in QuickIce |
| Mixed cage occupancy | Binary clathrates (CH4+CO2, etc.) | Medium | YES (`-g 12=co2*0.6+me*0.4`) | GenIce2 supports mixed occupancy per cage type |
| Specific cage occupancy | Per-cage control (cage 0 = CH4, cage 3 = CO2) | Medium | YES (`-G 0=me`) | GenIce2 supports per-cage guest assignment |
| Semiclathrate TBAB | Coolant, desalination, gas separation | High | PARTIAL (`-H` flag, `-c`/`-a` flags) | Requires manual cage+ion assembly; no one-click TBAB lattice |
| Ice XVII (C0 empty) | Hydrogen storage, porous ice studies | Low | YES (`17`/`ice17`) | Already in GenIce2, NOT in QuickIce |

## Differentiators

Features that set QuickIce apart for complex hydrate work.

| Feature | Value Proposition | Complexity | GenIce2 Support | Notes |
|---------|-------------------|------------|-----------------|-------|
| GUI-driven filled ice generation | No CLI knowledge needed; click to generate C0/C1/C2/ice1hte/sT' | Medium | Backend YES, UI NO | QuickIce's value-add is exposing GenIce2 power via GUI |
| GUI-driven mixed occupancy | Set CH4 60% + CO2 40% via sliders instead of `-g 12=co2*0.6+me*0.4` | Medium | Backend YES, UI NO | Huge UX win for non-CLI users |
| Preset binary clathrate configurations | One-click "CH4+CO2 sI hydrate" instead of assembling CLI flags | Low | Backend YES | Common workflows as presets |
| Semiclathrate TBAB preset | One-click TBAB semiclathrate with correct cage+ion placement | High | PARTIAL | Needs dedicated lattice module in GenIce2 or extensive configuration |
| CIF import via GUI | Load arbitrary hydrate CIF files for custom structures | Medium | YES (`cif[filename.cif]` plugin) | genice2-cif package available; needs pip install |
| Zeolite-derived ice structures | Access IZA zeolite database structures as ice analogs | Medium | YES (`zeolite[ITT]` plugin) | Via genice2-cif; interesting for hypothetical ice studies |
| Comprehensive guest molecule library | Beyond CH4/THF: CO2, H2, ethane, ethylene oxide, custom MOL files | Medium | YES (multiple guest plugins) | GenIce2 supports `mol[THF.mol]` for custom MOL file loading |
| Custom guest MOL file loading | User provides .mol file for any guest molecule | High | YES (`mol[filename.mol]`) | GenIce2 can load MOL files from MolView.org |
| Ion doping in hydrates | NaCl, KCl in hydrate cages for semiclathrate studies | Medium | YES (`-c`/`-a` flags) | QuickIce already supports ions in interface mode |
| Hydrate phase diagram integration | Show stability region for selected hydrate type | High | NO | Would need separate thermodynamic modeling |
| Multiple water models | TIP3P, TIP5P, 6-site, 7-site, SPC/E | Low | YES (`--water tip4p` etc.) | GenIce2 supports 7 water models; QuickIce only exposes TIP4P |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|-------------|-----------|-------------------|
| Custom lattice editor (drawing cages from scratch) | Enormous scope; GenIce2 already has 249+ lattices; no user would build a novel cage by hand | Expose GenIce2's existing lattice library + CIF import |
| Amorphous hydrate generation | Requires completely different algorithm (quench MD); out of scope for crystal generation tool | Point users to separate melt-quench workflows in LAMMPS/GROMACS |
| Hydrate formation simulation (nucleation/growth) | Entirely different problem from structure generation; would be a separate product | Generate initial structures for formation MD studies |
| Force field parameterization for exotic guests | Requires QM calculations; not a structure generator's job | Provide known .itp files for common guests; let users handle custom parameterization |
| sIII/sIV/sV hypothetical clathrate presets | GenIce2 has some (`TS1`, `HS1`, `HS2`) but these are rarely used and poorly documented | Defer; expose via CIF import if needed |
| Superionic ice (Ice XVIII/XX) | Not a hydrate; requires >4 GPa; quantum regime; no conventional MD model | Out of scope entirely |

## Complex Hydrate Taxonomy

### Filled Ice Phases

Filled ices are NOT clathrates. They are dense ice phases where guest molecules occupy channels or interstitial voids in the ice lattice, NOT cages. They form at high pressures (>0.5 GPa) where the water lattice is dense enough that guests squeeze into the interstices.

| Phase | GenIce2 Name | Structure | Typical Guests | Stability | Water Molecules/UC | Scientific Use | Confidence |
|-------|-------------|-----------|----------------|-----------|-------------------|----------------|------------|
| C0 | `c0te` | Trigonal (P3₂), channels | Ne, Ar, H₂, He | ~0.5-2 GPa | ~6 | Planetary ices, gas storage at high P | HIGH (verified source) |
| C1 | `c1te` | Rhombohedral (R-3), hydrogen-ordered | H₂ (primary) | ~2-5 GPa | ~6 | Hydrogen storage, energy applications | HIGH (verified source) |
| C2 | `c2te` | Tetragonal (I4₁md), cubic-derived | Ne, H₂ | ~1-3 GPa | ~4 | High-pressure hydrate physics | HIGH (verified source) |
| Filled ice Ih | `ice1hte` | Orthorhombic (Cmc2₁), distorted Ih | Ne, He | ~1 GPa | ~4 | Noble gas hydrate studies, planetary science | HIGH (verified source) |
| Filled sT' | `sTprime` | Tetragonal, distorted | H₂ (primary) | High P | ~8 | Hydrogen storage, ultrahigh-pressure phases | HIGH (verified source) |

**Key structural distinction from clathrates:** Filled ices have NO cages. The water framework is a dense ice lattice (like ice Ih, Ic, or II) with guests squeezed into channels. Clathrates (sI, sII, sH) have well-defined polyhedral cages (5¹², 5¹²6², etc.) formed by the water network.

**Why filled ices matter:** They are the dominant hydrate form in planetary interiors (Uranus, Neptune, icy moons) where pressures exceed 1 GPa. They are also relevant for hydrogen storage at high pressures.

### Semi-Clathrates

Semiclathrates differ from clathrates in that the guest molecule (typically an ionic species) PARTIALLY incorporates into the water framework via hydrogen bonds, rather than being purely van der Waals-encaged. The framework is built from water + ionic species, forming cages that can hold additional small guests.

| Type | Formula | Framework | Cages | Applications | GenIce2 Support | Confidence |
|------|---------|-----------|-------|-------------|-----------------|------------|
| TBAB | (TBA)Br·nH₂O | TBA⁺ + Br⁻ + H₂O | 5¹², 5¹²6², 5¹²6³ | Coolant (AC), desalination, gas separation | PARTIAL (HS1 + -H/-c/-a flags) | MEDIUM |
| TBPB | (TBP)Br·nH₂O | TBP⁺ + Br⁻ + H₂O | Similar to TBAB | Coolant, gas storage | NO dedicated lattice | LOW |
| TMAF | (TMA)F·nH₂O | TMA⁺ + F⁻ + H₂O | 5¹², 5¹²6² | Gas separation, CO2 capture | NO dedicated lattice | LOW |
| TBAF | (TBA)F·nH₂O | TBA⁺ + F⁻ + H₂O | Similar to TBAB | Coolant, desalination | NO dedicated lattice | LOW |

**GenIce2 semiclathrate support detail:**

GenIce2's `HS1` lattice (sIV) provides the water framework for a TBAB-like structure. The semiclathrate is assembled by:
1. Loading the HS1 lattice: `genice2 HS1`
2. Replacing a water molecule with a cation (N for TBA nitrogen): `-c 0=N`
3. Replacing another water with an anion (Br): `-a 2=Br`
4. Placing Bu- groups in cages adjacent to the cation: `-H 9=Bu-:3 -H 11=Bu-:3 -H 13=Bu-:3 -H 7=Bu-:3`
5. Using `--depol=optimal` since ions prevent strict depolarization

This is a multi-step manual process, NOT a one-click preset. It requires knowing which cage IDs are adjacent to which dopant positions, which is only discoverable by running `--assess_cages` first.

### Binary/Mixed Clathrates

Binary clathrates contain two types of guest molecules in the same hydrate structure. This is the most common natural hydrate state.

| Configuration | Structure | Scientific Use | GenIce2 Support | Confidence |
|--------------|-----------|----------------|-----------------|------------|
| CH4 + CO2 (sI) | CH4 in small cages, CO2 in large | CO2-CH4 swap for climate+energy | YES: `-g 12=co2*0.6+me*0.4 -g 14=co2` | HIGH |
| CH4 + THF (sII) | THF in large cages, CH4 in small | sII stabilization, flow assurance | YES: `-g 12=me -g 16=uathf` | HIGH |
| CH4 + C2H6 (sI) | Mixed small/large hydrocarbons | Natural gas hydrate composition | YES: `-g 12=me -g 14=et` | HIGH |
| H2 + THF (sII) | H2 in small cages, THF in large | Hydrogen storage | YES: `-g 12=H2 -g 16=uathf` | HIGH |
| CH4 + neo-pentane (sH) | Large help guest + CH4 | sH natural hydrates | POSSIBLE via custom guest | MEDIUM |

**GenIce2 mixed occupancy syntax:**
- Per cage TYPE: `-g 12=co2*0.6+me*0.4` (60% CO2 + 40% CH4 in type-12 cages)
- Per specific CAGE: `-G 0=me` (CH4 in cage #0, overriding cage type assignment)

### High-Pressure Phases

| Phase | Structure | Pressure Range | Hydrate Type | GenIce2 Support | Scientific Use |
|-------|-----------|---------------|-------------|-----------------|----------------|
| Ice VI | Tetragonal, self-clathrating | 1-2 GPa | Not a hydrate | YES (`6`, `6h`) | High-pressure physics baseline |
| Ice VII | Cubic, two interpenetrating lattices | 2-60 GPa | Not a hydrate | YES (`7`) | Planetary interiors |
| Ice XVII (C0 framework) | Hexagonal, porous channels | Ambient (metastable) | Filled ice emptied | YES (`17`/`ice17`) | H2 storage |
| Ice XVI (sII emptied) | Cubic, empty sII framework | Ambient (metastable) | Empty clathrate | YES (`16`/`CS2`/`sII` w/ empty) | Mechanical properties of empty hydrate |
| sVII | Hypothetical zeolitic ice | N/A (theoretical) | Hypothetical | YES (`sVII`/`CS4`) | Theoretical studies |

### Helium and Hydrogen Hydrates

| Configuration | Structure | Key Feature | GenIce2 Support | Confidence |
|--------------|-----------|-------------|-----------------|------------|
| He sII | sII with He guest | Multiple He per large cage | YES (H2 guest similar) | MEDIUM |
| H2 sII | sII with H2 guest | Up to 4 H2 per large cage | YES (`H2` molecule) | HIGH |
| H2 sH | sH with H2 | Multiple H2 per cage | YES | MEDIUM |
| H2 filled ice | C0/C1/C2 | H2 in channels | YES (`c0te`, `c1te`, `c2te`) | HIGH |

**Note on multiple occupancy:** GenIce2's README explicitly states: "multiple occupancy is not implemented. If it is required, make a module of a virtual molecule that contains multiple molecules." This means for H2 sII with 2-4 H2 molecules per cage, you'd need to create a custom multi-molecule plugin. This is a genuine limitation.

### GenIce2 Coverage Gap Analysis

| Hydrate Type | GenIce2 Support | QuickIce Exposes | Gap | Priority |
|-------------|-----------------|-------------------|-----|----------|
| sI (CS1) | YES | YES | None | — |
| sII (CS2) | YES | YES | None | — |
| sH (DOH/HS3) | YES | YES | None | — |
| Filled ice C0 | YES (`c0te`) | NO | **UI gap** | HIGH |
| Filled ice C1 | YES (`c1te`) | NO | **UI gap** | HIGH |
| Filled ice C2 | YES (`c2te`) | NO | **UI gap** | HIGH |
| Filled ice Ih | YES (`ice1hte`) | NO | **UI gap** | HIGH |
| Filled sT' | YES (`sTprime`) | NO | **UI gap** | MEDIUM |
| Ice XVII | YES (`17`) | NO | **UI gap** | MEDIUM |
| Ice XVI (empty sII) | YES (`16` w/ empty) | NO | **UI gap** | MEDIUM |
| CO2 guest | YES (`co2`) | NO | **Guest gap** | HIGH |
| H2 guest | YES (`H2`) | NO | **Guest gap** | MEDIUM |
| Ethane guest | YES (`et`) | NO | **Guest gap** | MEDIUM |
| Mixed occupancy | YES (`-g` flag) | NO | **Feature gap** | HIGH |
| Per-cage occupancy | YES (`-G` flag) | NO | **Feature gap** | MEDIUM |
| Semiclathrate TBAB | PARTIAL (manual assembly) | NO | **Major gap** | LOW (rare in MD) |
| TBPB semiclathrate | NO | NO | **Full gap** | LOW |
| TMAF semiclathrate | NO | NO | **Full gap** | LOW |
| Multiple H2 per cage | NO (single occupancy only) | NO | **GenIce2 limit** | LOW |
| Custom CIF import | YES (`cif[x.cif]` plugin) | NO | **Feature gap** | MEDIUM |
| Zeolite ice import | YES (`zeolite[ITT]` plugin) | NO | **Feature gap** | LOW |
| Custom MOL guest | YES (`mol[X.mol]`) | NO | **Feature gap** | MEDIUM |
| Ion doping in hydrate | YES (`-c`/`-a`) | NO | **Feature gap** | MEDIUM |
| Multiple water models | YES (7 models) | NO (TIP4P only) | **Feature gap** | MEDIUM |
| Hypothetical clathrates (sIII, sIV, sV) | YES (various names) | NO | **UI gap** | LOW |

## Scientific Demand Assessment

| Field | Hydrate Types Used | Demand Level | Notes | Confidence |
|-------|-------------------|-------------|-------|------------|
| Flow Assurance (Oil & Gas) | sI (CH4, CO2), sII (THF), mixed CH4+CO2 | **VERY HIGH** | Pipeline blockage prevention; largest industrial use case | HIGH |
| Climate Science | sI (CH4), sII, CO2 hydrates, mixed CH4+CO2 | **HIGH** | Methane hydrate stability, CO2 sequestration | HIGH |
| Energy (Gas Production) | sI CH4, sII, mixed | **HIGH** | Methane hydrate extraction (Japan, China programs) | HIGH |
| Hydrogen Storage | sII H2+THF, filled ice C0/C1/C2, H2 sH | **MEDIUM** | Active research area but smaller community | MEDIUM |
| Planetary Science | Filled ices (C0, C1, C2), sI/sII on icy moons | **MEDIUM** | Uranus/Neptune interiors; small but dedicated community | MEDIUM |
| Coolant Technology | Semiclathrates (TBAB, TBPB, TMAF) | **MEDIUM** | District cooling, AC; mostly experimental, less MD | MEDIUM |
| Desalination | Semiclathrates (TBAB, TBAF) | **LOW** | Emerging; very few MD simulation papers | LOW |
| Theoretical/Computational | Hypothetical clathrates, empty hydrates | **LOW** | Academic curiosity; PCOD structures, foam crystals | LOW |

**Relative demand estimate:**
- Simple clathrates (sI/sII/sH) with CH4/THF: **~70%** of hydrate MD simulation papers
- Binary/mixed clathrates: **~15%**
- Filled ice phases: **~5%**
- Semiclathrates: **~5%**
- Other exotic: **~5%**

### Crystallographic Data Availability

| Database | Content | Free? | CIF Quality | Relevance |
|----------|---------|-------|-------------|-----------|
| COD (Crystallography Open Database) | ~500K structures, some hydrates | YES (CC0) | Variable | Can find some hydrate CIFs; search by formula |
| ICSD (Inorganic Crystal Structure Database) | Comprehensive; best for hydrates | NO (commercial, ~€5000/yr) | HIGH | Best source for filled ice and semiclathrate CIFs |
| CSD (Cambridge Structural Database) | Organic crystals, some hydrate-like | PARTIAL (free subset) | HIGH | Limited hydrate coverage |
| IZA Structure Database | Zeolite topologies (share cage networks with clathrates) | YES | GOOD | Directly usable via GenIce2 `zeolite[]` plugin |
| CCDC | Organic/inorganic | PARTIAL | HIGH | Some hydrate structures |

**GenIce2 CIF import capability:** The `genice2-cif` package (`pip install genice2-cif`) enables:
1. Loading any local CIF file: `genice2 cif[my_hydrate.cif]`
2. Loading from IZA zeolite database: `genice2 zeolite[ITT]`
3. Specifying tetrahedral atom type: `genice2 cif[ice.cif:O=O]`

This means ANY hydrate structure with a CIF file can be loaded. The main limitation is CIF quality — the file must have correct space group, atom positions, and symmetry operations that GenIce2's `cif2ice` parser can handle.

**CIF availability for specific complex hydrate types:**
- Filled ice C0/C1/C2: Available in literature (Teeratchanan 2015); CIFs in supplemental materials; also hardcoded in GenIce2
- TBAB semiclathrate: CIFs available in ICSD and various publications (Kamata 2004, Shimada 2005); NOT in COD
- TBPB semiclathrate: CIFs in ICSD; limited free availability
- TMAF semiclathrate: CIFs in ICSD; limited free availability

## MVP Recommendation

For v5/v6, prioritize (ordered by impact × effort):

1. **Expose CO2 guest molecule** — Trivial code change, massive scientific demand. Just add "co2" to GUEST_MOLECULE dict and handle `co2` in molecule index parsing. [Effort: Low, Impact: HIGH]

2. **Expose filled ice lattice types (c0te, c1te, c2te, ice1hte, sTprime)** — Add to HYDRATE_LATTICES dict with appropriate cage info. GenIce2 already does the heavy lifting. [Effort: Low, Impact: MEDIUM]

3. **Expose mixed cage occupancy** — Allow users to set two guest types per cage type with occupancy sliders. This is the primary use case for binary clathrates. [Effort: Medium, Impact: HIGH]

4. **Expose H2 and ethane guests** — Similar to CO2, just add to GUEST_MOLECULES. [Effort: Low, Impact: MEDIUM]

5. **Expose per-cage guest assignment (-G flag)** — For advanced users who want specific cages filled with specific guests. [Effort: Medium, Impact: MEDIUM]

6. **Expose additional water models (TIP3P, TIP5P, SPC/E)** — Add dropdown selector. GenIce2 supports 7 models. [Effort: Low, Impact: MEDIUM]

Defer to later (v7+):
- **Semiclathrate TBAB preset**: Requires either a dedicated GenIce2 lattice module (not yet available) or complex multi-step UI assembly. Low MD demand. [Effort: HIGH, Impact: LOW]
- **Custom CIF import**: Needs genice2-cif pip package dependency; file picker + validation UI; moderate effort. [Effort: MEDIUM, Impact: MEDIUM]
- **Custom MOL file guest loading**: Complex UI; requires understanding MOL file format; niche use. [Effort: HIGH, Impact: LOW]
- **Multiple H2 per cage**: GenIce2 explicitly does NOT support this; would require a custom multi-molecule plugin. [Effort: HIGH, Impact: LOW]
- **TBPB/TMAF semiclathrates**: No GenIce2 lattice; would need CIF import or custom lattice module. [Effort: HIGH, Impact: LOW]

## Sources

| Source | URL | Confidence | Used For |
|--------|-----|------------|----------|
| GenIce2 GitHub README (official) | https://github.com/genice-dev/GenIce2 | HIGH | Lattice list, guest molecules, flags, semiclathrate docs |
| GenIce2 CLI help (`genice2 -h`) | Local installation | HIGH | Exact lattice names, flag syntax, available molecules |
| GenIce2 source: c0te.py, c1te.py, c2te.py, ice1hte.py, sTprime.py | https://github.com/genice-dev/GenIce2 | HIGH | Filled ice structural details, guest positions |
| GenIce2 source: HS1.py (sIV/semiclathrate) | https://github.com/genice-dev/GenIce2 | HIGH | Semiclathrate cage layout, test configuration |
| genice2-cif plugin | https://github.com/vitroid/genice-cif | HIGH | CIF import capability, zeolite DB access |
| Wikipedia: Clathrate hydrate | https://en.wikipedia.org/wiki/Clathrate_hydrate | MEDIUM | Structure types (sI/sII/sH), applications, general context |
| Wikipedia: Phases of ice | https://en.wikipedia.org/wiki/Phases_of_ice | MEDIUM | Ice XVI, XVII, filled ice context |
| QuickIce source code (local) | `/share/home/nglokwan/quickice/quickice/` | HIGH | Current feature set, HYDRATE_LATTICES dict, GUEST_MOLECULES dict |
| COD database | https://www.crystallography.net/cod/ | MEDIUM | CIF availability assessment |
| Teeratchanan 2015 (via GenIce2 refs) | Cited in GenIce2 source | MEDIUM | Filled ice C0/C1/C2 structural data |
| GenIce2 naming convention table | GenIce2 README | HIGH | Cross-reference between hydrate/ice/FK/zeolite/foam nomenclatures |

## Key Insight: The "Free Wins" Gap

The single most important finding is that **GenIce2 already supports far more than QuickIce exposes**, and most of the gap is trivially bridgeable:

**"Free wins" (GenIce2 already does it, QuickIce just needs to expose it):**
1. 5 filled ice lattice types (c0te, c1te, c2te, ice1hte, sTprime) — just add to HYDRATE_LATTICES dict
2. 3 additional guest molecules (CO2, H2, ethane) — just add to GUEST_MOLECULES dict
3. 2 additional water models (TIP3P, TIP5P) — just add dropdown
4. Mixed cage occupancy — pass `-g` flag syntax through to GenIce2 API
5. Ice XVII, Ice XVI — already lattice types in GenIce2

**Genuine new features (GenIce2 doesn't fully support):**
1. Semiclathrate TBAB preset — would need a dedicated lattice module
2. Multiple H2 occupancy per cage — would need custom multi-molecule plugin
3. TBPB/TMAF semiclathrates — would need CIF import or custom lattice
4. Hydrate phase diagram — would need separate thermodynamic modeling

**Recommendation:** Focus v5 on the "free wins" — they provide 80% of the scientific value for 20% of the effort. Complex semiclathrate support can wait for v7+ when there's clear user demand.
