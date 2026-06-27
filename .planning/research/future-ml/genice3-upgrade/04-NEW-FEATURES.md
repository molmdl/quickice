# GenIce3 New Feature Inventory & QuickIce Relevance

**Domain:** Ice/hydrate structure generation library upgrade
**Researched:** 2026-06-27
**Comparison:** GenIce2 v2.2.13.1 → GenIce3 v3.0b4 (latest on main branch; 3.0b3 on PyPI)

---

## Table Stakes Features

Features GenIce3 has that users would expect in any modern ice structure generator. Missing from GenIce2 = product feels outdated.

| Feature | GenIce2 | GenIce3 | Gap Severity |
|---------|---------|---------|-------------|
| Config file (YAML) support | No | `-Y file.yaml` | Medium — standard for CLI tools |
| Clean water model selection | `safe_import('molecule','tip4p').Molecule()` | `-e "gromacs :water_model tip4p"` or `water_model="ice"` | High — GenIce2 requires manual molecule plugin import |
| Spot-level ion doping | No (only unit-cell `-a`/`-c`) | `-A WATER_INDEX=Cl` / `-C WATER_INDEX=Na` | High — standard for ion-doped structures |
| Cage survey as structured output | `--assess_cages` (text print to stdout) | `cage_survey` exporter → JSON | High — structured data is expected |
| TIP4P/2005 water model | Not available | `water_model="tip4p2005"` | Low — niche model |
| LAMMPS export | No | `-e lammps` | Low — GROMACS-focused tools don't need this |
| Non-diagonal replication matrix | No (only `--rep n n n`) | `--replication_matrix 9 integers` | Medium — advanced crystallography |

## Differentiators

Features that set GenIce3 apart from GenIce2 and other ice generation tools.

| Feature | Description | Novelty | QuickIce Relevance |
|---------|-------------|---------|--------------------|
| **Protonic defects (H₃O⁺/OH⁻)** | API-only embedding of ionic defects into HB network | Unique — no other tool does this | Medium — could enable "doped ice" workflow |
| **Bjerrum defects (L/D type)** | Topological defects on specific HB edges | Unique — topological defect generation | Low — niche scientific use |
| **Reactive pipeline (DependencyEngine)** | Auto-computes only required data from dependency graph | Significant — replaces 7-stage fixed pipeline | Low (internal) — but simplifies API usage |
| **CIF input as unit cell** | `UnitCell("CIF", file="path.cif")` — arbitrary crystals | Novel — unlimited extensibility | High — users could import any ice structure |
| **Zeolite framework as unit cell** | `UnitCell("zeolite", code="LTA")` — IZA database | Novel — 200+ zeolite frameworks | Medium — exotic ice/zeolite structures |
| **Cation group attachment** | `spot_cation_groups={51: {12: "methyl", ...}}` | Novel — molecular ion solvation shells | Medium — could simplify ion+group workflows |
| **Stacking disorder** | `UnitCell("one", layers="ccchchc")` / `UnitCell("eleven", ...)` | Novel — stacking-faulted ice I | Medium — physically important ice I variant |
| **Polarization control** | `--target_polarization Px Py Pz` / `--pol_loop_2` | Improved — GenIce2 had `target_polarization` but limited | Low — QuickIce always depolarizes |
| **Supercell-as-unit-cell exporter** | `Exporter("python")` → .py unitcell plugin | Novel — reusable custom lattices | Low — QuickIce doesn't generate plugins |

---

## Feature Relevance Matrix

Each new GenIce3 feature rated by QuickIce relevance.

| Feature | QuickIce Relevance | Confidence | Rationale |
|---------|-------------------|------------|-----------|
| **TIP4P/Ice water model (`"ice"`)** | **Critical** | HIGH | Eliminates our 3→4 atom normalization step; generates correct TIP4P-ICE geometry directly |
| **CIF input as unit cell** | **High** | HIGH | Opens arbitrary crystal structure input; could replace hardcoded phase list |
| **Spot ions (`-A`/`-C`)** | **High** | HIGH | More flexible ion insertion than current unit-cell-only approach; aligns with our ion workflow |
| **Cage survey JSON exporter** | **High** | HIGH | Could populate hydrate UI with cage types/positions; structured data vs text |
| **Water model as exporter suboption** | **High** | HIGH | Cleaner API; currently we import `safe_import('molecule','tip4p').Molecule()` |
| **Stacking disorder (`one`, `eleven`)** | **Medium** | HIGH | Physically important ice I variant; would expand phase coverage |
| **Cation group attachment** | **Medium** | MEDIUM | Could simplify ion+organic group workflows; not yet a QuickIce use case |
| **Protonic defects (H₃O⁺/OH⁻)** | **Medium** | HIGH | Future "doped ice" capability; API-only, no CLI |
| **Ice XXI (21)** | **Medium** | HIGH | Newly discovered (2025) experimentally verified phase; extends phase diagram |
| **Zeolite framework input** | **Medium** | MEDIUM | Exotic ice structures; niche but academically interesting |
| **YAML config file** | **Low** | HIGH | QuickIce has its own CLI/GUI; GenIce3's YAML is not directly useful |
| **LAMMPS export** | **Low** | HIGH | QuickIce is GROMACS-focused; no LAMMPS use case |
| **Plotly 3D visualization** | **Low** | HIGH | QuickIce uses VTK; Plotly HTML output doesn't integrate |
| **Bjerrum defects** | **Low** | HIGH | Niche topological defect; very few users need this |
| **Reactive pipeline** | **Low (internal)** | MEDIUM | Internal change; no direct user-facing benefit but simpler API |
| **Non-diagonal replication** | **Low** | HIGH | QuickIce always uses diagonal supercells |
| **Supercell-as-unit-cell exporter** | **None** | HIGH | QuickIce doesn't generate GenIce plugins |
| **WebAPI (FastAPI/uvicorn)** | **None** | HIGH | QuickIce is a desktop app, not a web service |

---

## Detailed Feature Descriptions

### 1. TIP4P/Ice Water Model (`water_model="ice"`)

**What:** GenIce3's `"ice"` water model symbol produces the exact TIP4P/Ice (Abascal 2005) geometry — 4 atoms per molecule: OW, HW1, HW2, MW with correct positions.

**Why Critical for QuickIce:** Currently, `generator.py` generates ice with 3-atom TIP3P format (`safe_import('molecule', 'tip3p').Molecule()`) then normalizes to 4-atom TIP4P-ICE at export time (line 116-118 comment). With GenIce3, we could use:

```python
# GenIce3 API (proposed QuickIce usage)
genice = GenIce3(replication_matrix=supercell_matrix)
genice.set_unitcell("1h", density=density)
Exporter("gromacs").dump(genice, water_model="ice")
```

This eliminates the 3→4 atom normalization step entirely, producing correct TIP4P-ICE geometry directly from generation.

**Confidence:** HIGH — verified from [Water models page](https://genice-dev.github.io/GenIce3/water-models.html) and GenIce2 source (`genice2.molecules.ice.Molecule` produces `['O', 'H', 'H', '.']`).

### 2. CIF Input as Unit Cell

**What:** GenIce3 can load any CIF crystallographic file as a unit cell:

```python
# API
genice.set_unitcell("CIF", file="path/to/structure.cif", osite="O", hsite=None)

# CLI
genice3 CIF --file path/to/structure.cif --osite O
```

**How it works:** The `CIF` unit cell plugin reads a CIF file, identifies oxygen sites (via `--osite` regex), and optionally identifies hydrogen sites (via `--hsite` regex). If `hsite` is omitted, GenIce3 places hydrogen atoms automatically using the ice rule algorithm. This means:
- Structures with known H positions: `hsite="H"` → preserves experimental H ordering
- Structures without H positions: `hsite=None` → GenIce3 generates H-disordered network

**QuickIce relevance:** Users could import ANY crystal structure from CIF files (e.g., from ICSD, COD, or custom experiments) and generate hydrogen-disordered ice from it. This would make QuickIce extensible beyond the hardcoded phase list.

**Confidence:** HIGH — verified from [Unit cells page](https://genice-dev.github.io/GenIce3/unitcells.html) and API examples.

### 3. Spot Ions (`-A`/`-C`)

**What:** GenIce3 distinguishes between unit-cell ions and spot ions:

| Type | GenIce3 CLI | GenIce3 API | GenIce2 Equivalent |
|------|------------|-------------|-------------------|
| Unit-cell ions | `-a SITE=Cl` / `-c SITE=Na` | `set_unitcell("A15", anion={15: "Cl"}, cation={21: "Na"})` | `-a 3=Cl` / `-c 3=Na` (same) |
| Spot ions | `-A WATER_INDEX=Cl` / `-C WATER_INDEX=Na` | `GenIce3(spot_anions={1: "Cl"}, spot_cations={51: "Na"})` | **NOT AVAILABLE** |

**Key difference:** Unit-cell ions are replicated with the lattice (same ion at every unit-cell image), while spot ions replace a specific water molecule in the supercell by its global index. This is much more flexible — you can place ions at arbitrary positions, not just lattice-equivalent sites.

**⚠️ Breaking change:** In GenIce2 CLI, `-A` means `--assess_cages`. In GenIce3 CLI, `-A` means `--spot_anion`. This is a flag collision that will confuse anyone migrating.

**QuickIce relevance:** Our `ion_inserter.py` does post-hoc ion insertion after ice generation. With spot ions, we could do GenIce3-native ion doping during generation, which would produce better hydrogen-bond networks around ions (GenIce3 adjusts the HB network to accommodate the ion).

**API usage:**
```python
genice = GenIce3(
    replication_matrix=np.array([[2,0,0],[0,2,0],[0,0,2]]),
    spot_anions={1: "Cl"},
    spot_cations={51: "Na"},
)
genice.set_unitcell("A15")
Exporter("gromacs").dump(genice, water_model="4site")
```

**Confidence:** HIGH — verified from [Doping and defects page](https://genice-dev.github.io/GenIce3/doping-and-defects.html) and API examples.

### 4. Cage Survey Exporter (JSON)

**What:** Replaces GenIce2's `--assess_cages` flag with a proper exporter that outputs structured JSON:

```bash
# GenIce2 (text output, mixed with logging)
genice2 CS2 -A  # prints cage info to stdout mixed with other output

# GenIce3 (structured JSON)
genice3 CS2 -e cage_survey > cages.json
```

**Output format:** JSON containing:
- Cage positions (fractional coordinates)
- Cage type labels (e.g., "A12", "A16")
- Cage face information
- Optional `:max_cage_rings N` suboption (default 16)

**QuickIce relevance:** We could use this to populate our hydrate UI with cage information before generating the full structure. Currently, QuickIce has no cage visualization — cage survey JSON would enable:
- Showing which cages are occupied/vacant
- Interactive cage selection in GUI
- Pre-generation cage type display (show user what cages exist before choosing guests)

**Confidence:** HIGH — verified from [Output formats page](https://genice-dev.github.io/GenIce3/output-formats.html) and [Changes from GenIce2 page](https://genice-dev.github.io/GenIce3/changes-from-genice2.html).

### 5. Protonic Defects (H₃O⁺/OH⁻)

**What:** API-only feature for embedding ionic defects into the hydrogen-bond network:

```python
from genice3.util import find_nearest_sites_pbc

genice = GenIce3(replication_matrix=np.array([[2,0,0],[0,2,0],[0,0,2]]))
genice.set_unitcell("A15")

# Specify defect positions in fractional coordinates
celli = np.linalg.inv(genice.cell)
H3O_positions = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]) @ celli
OH_positions = np.array([[1.0, 0.0, 0.0], [2.0, 1.0, 1.0]]) @ celli
H3O_sites = find_nearest_sites_pbc(H3O_positions, genice.lattice_sites, genice.cell)
OH_sites = find_nearest_sites_pbc(OH_positions, genice.lattice_sites, genice.cell)

genice.add_spot_hydronium(H3O_sites)
genice.add_spot_hydroxide(OH_sites)

Exporter("gromacs").dump(genice, water_model="3site")
```

**Key constraints:**
- API-only (no CLI option yet)
- Charge must balance (equal H₃O⁺ and OH⁻)
- Defects are embedded into the HB network topology, not just atom replacement
- Uses `find_nearest_sites_pbc()` utility to convert coordinates to lattice site indices

**QuickIce relevance:** Medium. This is more scientifically specialized than our Na/Cl ion insertion. H₃O⁺/OH⁻ defects are relevant to:
- Proton conduction studies in ice
- Acid/base chemistry in confined water
- Electrochemical ice systems

Our current ion insertion is substitutional (replace water with Na/Cl). Protonic defects are topological (modify the HB network). These are fundamentally different workflows.

**Confidence:** HIGH — verified from [API examples → topological defects](https://genice-dev.github.io/GenIce3/api-examples/topological_defects.html) with full code samples.

### 6. Bjerrum Defects (L/D type)

**What:** API-only feature for topological defects on specific hydrogen bonds:

```python
from genice3.util import find_nearest_edges_pbc

genice = GenIce3(replication_matrix=np.array([[2,0,0],[0,2,0],[0,0,2]]))
genice.set_unitcell("A15")

# D-defect: both H on same bond oriented same way
D_positions = np.array([[0.0, 0.0, 0.0]]) @ celli
D_edges = find_nearest_edges_pbc(D_positions, genice.graph, genice.lattice_sites, genice.cell)
genice.add_bjerrum_D(D_edges)

# L-defect: no H on a bond (both missing)
L_positions = np.array([[1.0, 0.0, 0.0]]) @ celli
L_edges = find_nearest_edges_pbc(L_positions, genice.graph, genice.lattice_sites, genice.cell)
genice.add_bjerrum_L(L_edges)
```

**QuickIce relevance:** Low. Bjerrum defects are a niche crystallographic concept. Very few users outside specialized ice physics would need this.

**Confidence:** HIGH — verified from API examples.

### 7. Stacking Disorder (`one`, `eleven`)

**What:** Two new unit cells for stacking-disordered ice I:

```python
# Ice I with arbitrary stacking (c=cubic, h=hexagonal)
genice.set_unitcell("one", layers="ccchchc")    # H-disordered
genice.set_unitcell("eleven", layers="ccchchc")  # Ice XI with stacking faults
```

**Scientific context:** Real ice I is never perfectly Ice Ih or Ice Ic — it has stacking faults. The `one` unit cell lets users specify arbitrary stacking sequences (e.g., "cchhcchh"). This is physically much more realistic than pure Ih or Ic.

**QuickIce relevance:** Medium. Stacking-disordered ice I is a hot research topic. Adding this would:
- Replace the binary Ih/Ic choice with a spectrum
- Allow users to model realistic ice I
- Potentially replace both `ice_ih` and `ice_ic` with a single `ice_1` entry + stacking control

**Confidence:** HIGH — verified from [Unit cells page](https://genice-dev.github.io/GenIce3/unitcells.html).

### 8. Ice XXI (21)

**What:** Newly added ice phase:

```python
genice.set_unitcell("21")  # or "ice21"
```

**Scientific context:** Ice XXI is a newly discovered phase (2025). References: Kobayashi 2025, Lee 2025. This is experimentally verified.

**QuickIce relevance:** Medium. Extends QuickIce's phase coverage from 8 to 9 experimentally verified phases. However, it's so new that very few users will request it yet.

**Confidence:** HIGH — verified from [Unit cells page](https://genice-dev.github.io/GenIce3/unitcells.html) with references.

### 9. Cation Group Attachment

**What:** Attach molecular groups to cations within the lattice:

```python
# API
genice = GenIce3(
    spot_cations={51: "N"},
    spot_cation_groups={51: {12: "methyl", 48: "methyl", 49: "methyl", 50: "methyl"}},
)

# CLI
genice3 A15 --spot_cation 51=N :group 12=methyl 48=methyl 49=methyl 50=methyl
```

**What this does:** When a cation (e.g., N from TMA) replaces a water molecule, the cation may have organic groups (methyl groups for TMA). The `:group` suboption tells GenIce3 which cages surrounding the cation should have which group attached. This is critical for molecules like tetramethylammonium (TMA) where the ion + 4 methyl groups form a single molecular entity.

**QuickIce relevance:** Medium. Currently QuickIce doesn't support organic cations with groups. But if we add support for TMA or other organo-cations in hydrates, this feature would be essential.

**Confidence:** HIGH — verified from [API examples → doping](https://genice-dev.github.io/GenIce3/api-examples/doping.html) with full code samples.

### 10. Prism (Ice Nanotubes)

**What:** Twisted hydrogen-ordered ice nanotubes:

```python
genice.set_unitcell("prism", circum="6 1", axial="-1 10", x="f", y="a")
```

Parameters:
- `circum`: Chiral vector on square lattice (defines tube circumference)
- `axial`: Translational vector (defines tube length)
- `x`, `y`: HB orientation — `f`=ferroelectric, `a`=antiferroelectric

**QuickIce relevance:** Low. Ice nanotubes are a niche carbon-nanotube-related structure. Not part of the standard ice phase diagram.

**Confidence:** HIGH — verified from [Unit cells page](https://genice-dev.github.io/GenIce3/unitcells.html).

### 11. Reactive Pipeline (DependencyEngine)

**What:** GenIce3 replaces GenIce2's fixed 7-stage pipeline with a reactive dependency engine:

- **GenIce2:** `Stage1 → Stage2 → Stage34E → Stage5 → Stage6 → Stage7` (always runs all stages)
- **GenIce3:** `DependencyEngine` computes only what's needed based on requested outputs

**How it works:** Properties like `graph`, `lattice_sites`, `digraph`, `orientations` are computed on demand. When you request an output, the engine traces dependencies and runs only the required computation steps.

**QuickIce relevance:** Low (internal change). However, this has indirect benefits:
- Faster when only cage info is needed (cage_survey doesn't need full atom positions)
- Cleaner API — set properties, then read them; no explicit `generate_ice()` call
- Better composability for our post-generation pipeline

**Confidence:** MEDIUM — architecture described in docs but no benchmarks published.

---

## Performance Comparison

### Published Benchmarks

**No quantitative benchmarks comparing GenIce2 vs GenIce3 have been found.** The CHANGES.md mentions benchmark scripts were added (commit cde8c5e, 2026-02-14: "Add benchmark scripts and gnuplot support"), but no benchmark results are published.

### Qualitative Performance Claims

| Aspect | GenIce2 | GenIce3 | Evidence |
|--------|---------|---------|----------|
| **Generation speed** | Fixed 7-stage pipeline | Reactive (skip unused stages) | Docs claim DependencyEngine "runs only required tasks" — but main GROMACS export likely still runs most stages |
| **Memory usage** | Unknown | Unknown | No claims made |
| **genice-core algorithm** | v1.3–1.4 | v1.5.4+ | GenIce3 requires `genice-core>=1.5.4`; the J. Chem. Phys. 2024 paper (DOI:10.1063/5.0198056) describes algorithmic improvements in genice-core |
| **Random seed control** | Global `np.random.seed()` | `seed` parameter in constructor | GenIce3 passes seed to genice-core, avoiding global state mutation — this is a correctness improvement, not speed |

### QuickIce-Specific Performance Implications

1. **Random state isolation:** GenIce2 mutates global `np.random` (we work around this in `generator.py` lines 101-157). GenIce3's `seed` parameter eliminates this hack entirely.
2. **Cage survey without full generation:** GenIce3's reactive pipeline can output cage info (`cage_survey`) without computing full atom positions. This could make hydrate UI pre-generation much faster.
3. **No speed regression expected:** GenIce3 uses the same `genice-core` algorithms; the reactive pipeline is overhead-reduction, not algorithm-change.

**Confidence:** MEDIUM — no published benchmarks; qualitative assessment from source code and documentation.

---

## Water Model Support Comparison

| Water Model | GenIce2 Module | GenIce3 Symbol | Type | Sites | QuickIce Uses |
|-------------|---------------|-----------------|------|-------|--------------|
| TIP3P | `tip3p` / `3site` | `3site` / `tip3p` / `spce` | 3-site | O, H, H | Yes — ice generation (then normalized to TIP4P-ICE) |
| SPC/E | `spce` | `spce` | 3-site | O, H, H | No |
| TIP4P | `tip4p` / `4site` | `4site` / `tip4p` | 4-site | O, H, H, M | Yes — hydrate generation |
| **TIP4P/Ice** | `ice` | `ice` | 4-site | O, H, H, M | **YES — our force field, but GenIce2 requires manual import** |
| **TIP4P/2005** | **NOT AVAILABLE** | `tip4p2005` | 4-site | O, H, H, M | No — but valuable option |
| TIP5P | `tip5p` / `5site` | `5site` / `tip5p` | 5-site | O, H, H, LP1, LP2 | No |
| 6-site (NvdE) | `NvdE` / `6site` | `6site` / `NvdE` | 6-site | O, H, H, M, LP1, LP2 | No |
| 7-site | `7site` | `7site` | 7-site | 7 atoms | No |
| Physical water | `physical_water` | `physical_water` | 1-site | O only | No |

### Key Differences

1. **TIP4P/2005 is NEW in GenIce3** — not available in GenIce2 at all. [Confidence: HIGH — verified by `ImportError` test]
2. **Water model selection mechanism is cleaner** — GenIce2 requires `safe_import('molecule', 'tip4p').Molecule()` while GenIce3 uses `Exporter("gromacs").dump(genice, water_model="ice")`. The water model is now an exporter suboption, not a separate import. [Confidence: HIGH]
3. **TIP4P/Ice was already in GenIce2** as `genice2.molecules.ice.Molecule` — but QuickIce never uses it directly (we use tip3p + normalization). GenIce3 makes it just `water_model="ice"`. [Confidence: HIGH]

### QuickIce Impact

The biggest win is using `water_model="ice"` directly, which would:
- Generate 4-atom TIP4P-ICE molecules from the start
- Eliminate the 3→4 atom normalization step in `generator.py`
- Eliminate the need for `safe_import('molecule', 'tip3p').Molecule()` + post-processing
- Ensure TIP4P-ICE geometry is correct by construction (not by normalization)

---

## Ice Phase Coverage Comparison

### Experimentally Verified Ice Phases

| Phase | GenIce2 Name | GenIce3 Name | QuickIce Currently Supports | Notes |
|-------|-------------|-------------|---------------------------|-------|
| Ice 0 | `0` / `ice0` | `0` / `ice0` | No | Metastable; not in QuickIce phase list |
| Ice Ih | `1h` / `ice1h` | `1h` / `ice1h` | **Yes** | Most common phase |
| Ice Ic | `1c` / `ice1c` | `1c` / `ice1c` | **Yes** | Cubic ice |
| Ice II | `2` / `ice2` | `2` / `ice2` | **Yes** | Hydrogen-ordered |
| Ice III | `3` / `ice3` | `3` / `ice3` | **Yes** | High-pressure |
| Ice V | `5` / `ice5` | `5` / `ice5` | **Yes** | Monoclinic |
| Ice VI | `6` / `ice6` | `6` / `ice6` | **Yes** | Double-network |
| Ice VII | `7` / `ice7` | `7` / `ice7` | **Yes** | Double-network |
| Ice VIII | `8` / `ice8` | `8` / `ice8` | **Yes** | Ordered Ice VII |
| Ice IX | `9` / `ice9` | `9` / `ice9` | No | Ordered Ice III |
| Ice XI | `11` / `XI` | `11` / `XI` | No | Ordered Ice Ih (antiferroelectric) |
| Ice XII | `12` / `XII` | `12` / `XII` | No | High-pressure metastable |
| Ice XIII | `13` / `XIII` | `13` / `XIII` | No | Ordered Ice V |
| Ice XIV | `14` / `ice14` | `14` / `ice14` | No | Ordered Ice XII |
| Ice XVI | `16` / `CS2` | `16` / `CS2` | No | Ultralow-density (sII empty) |
| Ice XVII | `17` / `XVII` | `17` / `XVII` | No | Ultralow-density |
| **Ice XXI** | **NOT AVAILABLE** | `21` / `ice21` | No | **NEW in GenIce3** (Kobayashi 2025, Lee 2025) |

### Hypothetical/Niche Phases Available in Both

| Phase | GenIce2 | GenIce3 | Type |
|-------|---------|---------|------|
| Ice A | `A` / `iceA` | `A` / `iceA` | Hypothetical |
| Ice B | `B` / `iceB` | `B` / `iceB` | Hypothetical |
| Ice M | `M` / `iceM` | `M` / `iceM` | Hypothetical high-density |
| Ice L | `iceL` | `iceL` | Hypothetical (Lei 2025) |
| Ice R | `iceR` | `iceR` | Hypothetical partial plastic |
| Ice T | `iceT` | `iceT` | Hypothetical |
| Ice T2 | `iceT2` | `iceT2` | Hypothetical |
| YKD | `YKD` | `YKD` | d-surface ice |
| CRN1-3 | `CRN1-3` | `CRN1-3` | Sillium CRN |
| Filled ices (C0-C2) | `c0te`-`c2te` | `c0te`-`c2te` | Filled ice |
| Ice nanotubes | `oprism` | `oprism` + **`prism`** | Nanotubes |

### Clathrate Hydrate Phases

| Phase | GenIce2 | GenIce3 | QuickIce Supports |
|-------|---------|---------|-------------------|
| sI | `CS1` / `sI` / `MEP` | `CS1` / `sI` / `MEP` | **Yes** |
| sII | `CS2` / `sII` / `16` / `MTN` | `CS2` / `sII` / `16` / `MTN` | **Yes** |
| sH | `DOH` / `sH` / `HS3` | `DOH` / `sH` / `HS3` | **Yes** |
| sIII | `TS1` / `sIII` | `TS1` / `sIII` | No |
| sIV | `HS1` / `sIV` | `HS1` / `sIV` | No |
| sV | `HS2` / `sV` | `HS2` / `sV` | No |
| sVII | `CS4` / `sVII` | `CS4` / `sVII` | No |
| Type T | `T` | `T` | No |

### NEW Unit Cells in GenIce3 (not in GenIce2)

| Unit Cell | Description | Type | QuickIce Relevance |
|-----------|-------------|------|-------------------|
| **`21` / `ice21`** | Ice XXI (Kobayashi 2025) | Experimentally verified | **Medium** — extends phase diagram |
| **`prism`** | Twisted ice nanotubes (Miao 2026) | Niche | Low |
| **`CIF`** | Load any CIF file | Extensibility | **High** — arbitrary crystal input |
| **`zeolite`** | IZA zeolite framework by code | Niche | Medium |
| **`aeroice`** | Alias of xFAU | Alias | Low |
| **`1c_2_2_2`** | Pre-expanded supercell for Ice Ic | Performance | Low |
| **`1h_2_2_2`** | Pre-expanded supercell for Ice Ih | Performance | Low |
| **`dtc`** | Porous ice with cylindrical channels (Matsumoto 2021) | Niche | Low |

### Unit Cells REMOVED from GenIce3 (present in GenIce2)

| Unit Cell | Notes |
|-----------|-------|
| `4R` | Not listed in GenIce3 docs |
| `bilayer` | Not listed in GenIce3 docs |
| `II` / `III` / `IV` / `IX` / `V` / `VI` / `VII` / `VIII` / `XII` / `XIII` / `XI` / `XVI` / `XVII` / `Ic` / `Ih` | Roman numeral aliases removed in GenIce3; use numeric names instead |

### Naming Changes (GenIce2 → GenIce3)

| GenIce2 | GenIce3 | Notes |
|---------|---------|-------|
| `safe_import('lattice', name)` | `UnitCell(name, ...)` or `genice.set_unitcell(name, ...)` | Unified plugin API |
| `safe_import('format', 'gromacs')` | `Exporter("gromacs")` | Renamed from "format" to "exporter" |
| `safe_import('molecule', 'tip4p')` | `water_model="tip4p"` (exporter suboption) | Water model is now part of exporter |
| `GenIce(lattice, reshape=...)` | `GenIce3(replication_matrix=...)` | Renamed parameter |
| `ice.generate_ice(formatter, water, ...)` | `Exporter("gromacs").dump(genice, water_model=...)` | Inverted call pattern |

---

## Release Timeline Assessment

### Current Release Status

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| 3.0a3 | ~2026-02-15 | Alpha | First tagged alpha |
| 3.0a4 | ~2026-02-16 | Alpha | Added group/cation features |
| 3.0b0 | 2026-02-26 | Beta | Major API stabilization |
| 3.0b1 | 2026-02-26 | Beta | Quick iteration |
| 3.0b2 | 2026-02-26 | Beta | Quick iteration |
| 3.0b3 | 2026-03-02 | Beta | **Latest on PyPI** |
| 3.0b4 | 2026-03-28 | Beta | **Latest on GitHub main** (not yet on PyPI) |
| 3.0.0 | Unknown | **Not released** | No GitHub releases page; no tagged releases |

### Assessment

- **No GitHub releases have been created** — the releases page is empty. Version bumps only happen in `pyproject.toml` and `README.md`.
- **Beta pace has slowed:** 3 beta releases in one day (Feb 26), then 1 week gap, then 1 month gap to b4. This suggests the API is stabilizing.
- **No Python 3.14 support:** GenIce3 requires `Python <3.14, >=3.11` (per PyPI). QuickIce uses Python 3.14.3. **This is a blocker.**
- **Active development:** 1,174 commits on main, latest commit ~2026-04-30 (ice XXI addition). The project is actively maintained.
- **No announced stable release date:** No roadmap, no milestone tracking visible.

### Prediction

Based on the release cadence (beta0→beta4 over ~1 month, then 2 months without a new beta), the API appears to be stabilizing. A 3.0.0 stable release is **plausible within 3-6 months** (by Q3-Q4 2026), but this is speculative. The Python 3.14 compatibility issue needs to be addressed.

**Confidence:** LOW — no official timeline, and the Python version constraint is a concrete blocker.

### Critical Blocker: Python 3.14 Incompatibility

GenIce3's `pyproject.toml` specifies `Python <3.14, >=3.11`. QuickIce runs on Python 3.14.3. This means:

1. **GenIce3 cannot be installed in our current environment** via pip
2. We would need to either:
   - Request Python 3.14 support from the GenIce3 maintainer (likely feasible — the constraint may be conservative)
   - Run GenIce3 in a separate Python 3.13 environment
   - Wait for GenIce3 to drop the `<3.14` upper bound

**Action item:** Contact vitroid@gmail.com (GenIce3 maintainer) to request Python 3.14 support testing.

---

## GenIce2 → GenIce3 API Migration Map

For QuickIce's two main generation files, here's how the API changes:

### `generator.py` (Ice Generation)

```python
# === GenIce2 (current) ===
from genice2.plugin import safe_import
from genice2.genice import GenIce

lattice = safe_import('lattice', 'ice1h').Lattice()
ice = GenIce(lattice, density=self.density, reshape=self.supercell_matrix)
water = safe_import('molecule', 'tip3p').Molecule()
formatter = safe_import('format', 'gromacs').Format()
gro_string = ice.generate_ice(formatter=formatter, water=water, depol='strict')

# === GenIce3 (proposed) ===
from genice3.genice import GenIce3
from genice3.plugin import Exporter

genice = GenIce3(replication_matrix=self.supercell_matrix, seed=seed)
genice.set_unitcell("1h", density=self.density)
gro_string = Exporter("gromacs").dump(genice, water_model="ice")
```

**Key differences:**
1. No `safe_import()` — use `set_unitcell()` / `Exporter()`
2. Water model is an exporter suboption, not a separate import
3. `seed` is a constructor parameter (eliminates `np.random.seed()` hack)
4. No explicit `generate_ice()` call — `Exporter.dump()` triggers computation
5. `water_model="ice"` produces TIP4P-ICE directly (no 3→4 normalization)

### `hydrate_generator.py` (Hydrate Generation)

```python
# === GenIce2 (current) ===
from genice2.genice import GenIce
from genice2.plugin import safe_import
from genice2.valueparser import parse_guest

lattice = safe_import('lattice', lattice_name).Lattice()
ice = GenIce(lattice, reshape=supercell_matrix)
water = safe_import('molecule', 'tip4p').Molecule()
formatter = safe_import('format', 'gromacs').Format()
guests = defaultdict(dict)
parse_guest(guests, "12=ch4*0.5")
gro_string = ice.generate_ice(formatter=formatter, water=water, guests=guests, depol='strict')

# === GenIce3 (proposed) ===
from genice3.genice import GenIce3
from genice3.plugin import Exporter

genice = GenIce3(replication_matrix=supercell_matrix)
genice.set_unitcell("CS1")
# Guests via set_unitcell or constructor
gro_string = Exporter("gromacs").dump(genice, water_model="ice")
```

**Key differences:**
1. Guest specification syntax changes (needs investigation — GenIce3 uses `-g`/`-G` CLI flags, but API equivalent needs checking)
2. `parse_guest` from GenIce2 may not exist in GenIce3
3. Lattice names changed (e.g., `CS1` replaces `sI` module import)

---

## Sources

| Source | URL | Confidence | What Verified |
|--------|-----|------------|---------------|
| GenIce3 Manual (official) | https://genice-dev.github.io/GenIce3/ | HIGH | Overview, features list |
| AI Assistants page | https://genice-dev.github.io/GenIce3/for-ai-assistants.html | HIGH | Structured feature summary |
| Unit cells page | https://genice-dev.github.io/GenIce3/unitcells.html | HIGH | All 80+ unit cells, options, references |
| Output formats page | https://genice-dev.github.io/GenIce3/output-formats.html | HIGH | All exporters, pipeline description |
| Doping and defects page | https://genice-dev.github.io/GenIce3/doping-and-defects.html | HIGH | Spot ions, protonic/Bjerrum defects |
| Water models page | https://genice-dev.github.io/GenIce3/water-models.html | HIGH | All water models including tip4p2005 |
| Guest molecules page | https://genice-dev.github.io/GenIce3/guest-molecules.html | HIGH | Guest molecule catalog |
| CLI reference | https://genice-dev.github.io/GenIce3/cli.html | HIGH | Full CLI options |
| API examples (topological defects) | https://genice-dev.github.io/GenIce3/api-examples/topological_defects.html | HIGH | Full code for H3O+/OH- and Bjerrum defects |
| API examples (doping) | https://genice-dev.github.io/GenIce3/api-examples/doping.html | HIGH | Full code for spot ions, cation groups |
| Changes from GenIce2 | https://genice-dev.github.io/GenIce3/changes-from-genice2.html | HIGH | Cage survey replaces assess_cages |
| Getting started | https://genice-dev.github.io/GenIce3/getting-started.html | HIGH | Requirements, install |
| PyPI genice3 3.0b3 | https://pypi.org/project/genice3/3.0b3/ | HIGH | Python <3.14 constraint, dependencies |
| GitHub CHANGES.md | https://raw.githubusercontent.com/genice-dev/GenIce3/main/CHANGES.md | HIGH | 1174 commits of development log |
| GitHub RELEASE_NOTE.md | https://raw.githubusercontent.com/genice-dev/GenIce3/main/RELEASE_NOTE.md | HIGH | Release note summary |
| GitHub repo | https://github.com/genice-dev/GenIce3 | HIGH | No GitHub releases, 2 stars, 0 forks |
| QuickIce `generator.py` | quickice/structure_generation/generator.py | HIGH | Current GenIce2 usage patterns |
| QuickIce `hydrate_generator.py` | quickice/structure_generation/hydrate_generator.py | HIGH | Current GenIce2 hydrate API usage |
| QuickIce `mapper.py` | quickice/structure_generation/mapper.py | HIGH | Phase ID to lattice name mapping |
| GenIce2 local inspection | `pip show genice2` / Python inspection | HIGH | 140+ lattice modules, molecule modules |

---

## Summary of Key Findings

1. **TIP4P/Ice direct generation (`water_model="ice"`) is the highest-impact feature** — eliminates our 3→4 atom normalization hack and produces correct TIP4P-ICE geometry by construction. [Confidence: HIGH]

2. **CIF input as unit cell is the most extensible feature** — allows users to import arbitrary crystal structures, potentially replacing the hardcoded 8-phase limit. [Confidence: HIGH]

3. **Spot ions (`-A`/`-C`) are the most relevant new ion feature** — GenIce2 only supports unit-cell-level ion doping; GenIce3 adds per-molecule replacement. This could improve our ion insertion workflow significantly. [Confidence: HIGH]

4. **Cage survey JSON replaces `--assess_cages`** — structured cage data could enable interactive hydrate UI features. [Confidence: HIGH]

5. **Ice XXI is the only new experimentally-verified phase** — all other "new" unit cells in GenIce3 are hypothetical or niche structures. [Confidence: HIGH]

6. **Python 3.14 compatibility is a BLOCKER** — GenIce3 requires `<3.14`, QuickIce runs 3.14.3. This must be resolved before any migration. [Confidence: HIGH]

7. **The API surface has changed significantly** — `safe_import()` → `UnitCell()`/`Exporter()`, water model from molecule import to exporter suboption, inverted call pattern (`generate_ice(formatter)` → `Exporter.dump(genice)`). Full API rewrite required. [Confidence: HIGH]

8. **No stable release exists yet** — only beta (3.0b3 on PyPI, 3.0b4 on GitHub). No release date announced. [Confidence: HIGH]

9. **No published performance benchmarks** — cannot confirm GenIce3 is faster or slower. The reactive pipeline should help for partial outputs (cage_survey) but full GROMACS export likely runs similar computation. [Confidence: MEDIUM]
