# Feasibility Assessment: Complex Hydrate Generation

**Goal:** Extend QuickIce beyond simple clathrate hydrates (sI/sII/sH) to complex hydrate structures  
**Verdict:** YES — with phased approach; "free wins" first, CIF import second, custom plugins third  
**Confidence:** HIGH (verified with hands-on GenIce2 API testing + source code analysis)

## Summary

After exhaustive analysis of GenIce2's source code, plugin architecture, and hands-on API testing, extending QuickIce to support complex hydrates is **highly feasible** and does NOT require atomsk at any stage. The key finding from Wave 1 — that GenIce2 already supports filled ices, semiclathrates, and exotic clathrates — is confirmed and expanded: GenIce2's Python API is fully programmable, supports mixed/binary guest occupancy, per-cage guest assignment, cage auto-detection (`assess_cages`), CIF import via `genice2-cif`, and custom lattice/molecule plugins via both local folders and pip-installable entry points.

The recommended approach is a **three-phase pipeline**: (1) expose existing GenIce2 capabilities in QuickIce's UI with minimal code changes ("free wins"), (2) integrate `genice2-cif` for arbitrary CIF import, and (3) create custom lattice plugins for the few structures not covered by built-in or CIF-importable lattices. Atomsk is definitively excluded — it provides zero hydrate functionality and its GPL-3.0 license creates distribution complications that GenIce2 (MIT) and pymatgen (MIT) avoid entirely.

The only genuine limitation is GenIce2's single-occupancy-per-cage constraint (no multiple H₂ molecules per cage), which requires custom multi-molecule plugins. Semiclathrate TBAB requires multi-step manual assembly even in GenIce2's own CLI, making it a genuinely high-effort feature with low MD simulation demand.

## Requirements

| Requirement | Status | Notes |
|-------------|--------|-------|
| Filled ice structures (C0, C1, C2, Ih, sT') | **Available** — GenIce2 built-in: `c0te`, `c1te`, `c2te`, `ice1hte`, `sTprime` | Tested via Python API; generates valid GRO output with ice rules + depolarization |
| CO₂ guest molecule | **Available** — GenIce2 molecule plugin `co2` | 3-atom linear molecule (C + 2 O); tested successfully |
| H₂ guest molecule | **Available** — GenIce2 molecule plugin `H2` | 2-atom molecule; single occupancy only |
| Ethane guest molecule | **Available** — GenIce2 molecule plugin `et` | United-atom ethane (1 site) |
| Mixed/binary occupancy | **Available** — `-g` flag: `12=co2*0.6+me*0.4` | Tested: CH₄+CO₂ sI binary clathrate via `parse_guest()` API |
| Per-cage guest assignment | **Available** — `spot_guests` dict: `{0: 'me', 2: 'co2'}` | Tested via `GenIce(lattice, spot_guests=...)` API |
| Custom lattice plugin system | **Available** — local `lattices/` folder or entry point | Tested: custom plugin loads via `safe_import()` |
| CIF import via genice2-cif | **Available** — `cif[filename.cif]` and `zeolite[ITT]` | Tested: EMT.cif import + `assess_cages=True` |
| Cage auto-detection | **Available** — `assess_cages=True` in `generate_ice()` | Works for clathrate-like structures; returns "No cages" for filled ices (expected — they have channels, not cages) |
| Ion doping (semiclathrates) | **Available** — `cations`/`anions` dicts in `GenIce()` | Tested: `spot_guests` mechanism works; semiclathrate `-c`/`-a` requires additional `fixedEdges` manipulation |
| Multiple water models | **Available** — TIP3P, TIP4P, TIP5P, SPC/E, 4-site, 5-site, 6-site, 7-site | All loadable via `safe_import('molecule', 'tip3p')` etc. |
| pymatgen for CIF I/O | **Available** — `Structure.from_file()`, `Structure.from_spacegroup()` | MIT license; supplementary to genice2-cif |
| spglib for symmetry | **Available** — `get_spacegroup()`, `refine_cell()`, `find_symmetry()` | BSD-3; already installed |
| Ice rules + depolarization | **Available ONLY in GenIce2** | No other tool provides this; pymatgen/spglib cannot apply ice rules |

## GenIce2 Plugin Architecture (Verified from Source Code)

### Plugin Loading Priority

```
1. Local:  ./lattices/<name>.py        (working directory)
2. System: genice2.lattices.<name>      (installed with genice2)
3. Extra:  entry_points("genice2_lattice") (pip-installable plugins)
```

Same pattern for `molecules/`, `formats/`, `loaders/`, `groups/`.

### Lattice Plugin Required Fields

A valid GenIce2 lattice plugin **must** define a `Lattice` class with:

| Field | Required? | Type | Description |
|-------|-----------|------|-------------|
| `self.cell` | **YES** | np.ndarray (3×3) | Cell vectors in nm |
| `self.waters` | **YES** | np.ndarray (N×3) or string | Water oxygen positions (fractional or absolute) |
| `self.coord` | **YES** | string | `"relative"` (fractional) or `"absolute"` (Cartesian, nm) |
| `self.density` | **YES** | float | Target density in g/cm³ |
| `self.bondlen` | Optional | float | O-O bond threshold in nm (auto-estimated if absent) |
| `self.cagepos` | Optional | np.ndarray (M×3) | Cage center positions (fractional) |
| `self.cagetype` | Optional | list[str] | Cage type labels (e.g., `["12", "14"]`) |
| `self.cages` | Optional (deprecated) | string | Multi-line cage spec (parsed by `parse_cages()`) |
| `self.pairs` | Optional | list[(int,int)] | Pre-defined O-O pairs (auto-detected if absent) |
| `self.fixed` | Optional | list[(int,int)] | Fixed H-bond orientations (for ordered ices) |

**Minimum viable lattice plugin:** ~20 lines of Python.

### Two Patterns for Lattice Plugins

**Pattern A: CIF-like data (for structures with crystallographic data)**
```python
class Lattice(genice2.lattices.Lattice):
    def __init__(self):
        # Define asymmetric unit + space group
        atoms = "O1 0.2342 0.4721 0.8019\nNe1 -0.0647 0.7868 0.7669"
        symops = "x,y,z\n-y,x-y,z+2/3\n-x+y,-x,z+1/3"
        
        from genice2 import CIF
        from genice2.cell import cellvectors
        
        self.cell = cellvectors(a=6.177/10, b=6.177/10, c=6.054/10, C=120)
        atomd = CIF.atomdic(atoms)
        full = CIF.fullatoms(atomd, CIF.symmetry_operators(symops))
        
        self.cagetype = [name for name, _ in full if name.startswith("Ne")]
        self.cagepos = [pos for name, pos in full if name.startswith("Ne")]
        self.waters, self.pairs = CIF.waters_and_pairs(self.cell, atomd, CIF.symmetry_operators(symops))
        self.density = 18 * len(self.waters) / 6.022e23 / (np.linalg.det(self.cell) * 1e-21)
        self.coord = "relative"
```

**Pattern B: Pre-computed positions (for structures where you have all O positions)**
```python
class Lattice(genice2.lattices.Lattice):
    def __init__(self):
        self.density = 0.795
        self.bondlen = 3
        self.coord = "absolute"
        self.cell = cellvectors(a=12.238, b=12.238, c=12.238)
        self.waters = """10.815 3.790 0\n3.790 0 1.423\n..."""
        self.cagepos, self.cagetype = parse_cages("""
            12    0.5000    0.5000    0.5000
            14    0.5000    0.7500    0.0000
            ...
        """)
```

### Molecule Plugin Required Fields

```python
class Molecule(genice2.molecules.Molecule):
    def __init__(self):
        self.sites_ = np.array(...)     # Atom positions relative to molecular center (nm)
        self.labels_ = ["C", "O", "O"]  # Atom names
        self.name_ = "CO2"              # Residue name in GRO output
```

**Minimum viable molecule plugin:** ~10 lines of Python.

### `assess_cages=True` Behavior

When `assess_cages=True` is passed to `generate_ice()`:
1. GenIce2 builds the H-bond network graph from water positions
2. `cycless.cycles_iter()` finds all rings up to size 8
3. `cycless.polyhedra_iter()` detects polyhedral cages
4. Cages are classified by their face topology (e.g., 5¹², 5¹²6²)
5. Cage centers and types are returned and can be used for guest placement

**Important limitation:** `assess_cages` only detects polyhedral cages (convex polyhedra formed by rings of water molecules). It does NOT detect channels in filled ices or irregular voids. This is expected behavior — filled ices have no cages in the clathrate sense.

### genice2-cif Plugin: How It Works

The `genice2-cif` plugin (`pip install genice2-cif`) provides two lattice types:

1. **`cif[filename.cif]`** — Reads a local CIF file
   - Uses `cif2ice.read_and_process()` to parse the CIF
   - Extracts tetrahedral atom positions (default: atoms named "T" or "S" — zeolite convention)
   - Override with `cif[file.cif:O=O]` to treat O atoms as water positions
   - Auto-scales the structure so nearest O-O distance ≈ 2.76 Å (ice Ih distance)
   - Sets `self.waters`, `self.cell`, `self.coord = "relative"`, `self.density`
   - **Does NOT set `self.cagepos`/`self.cagetype`** — cages must be detected via `assess_cages=True`

2. **`zeolite[ITT]`** — Retrieves structure from IZA Zeolite Database
   - Downloads CIF from `http://www.iza-structure.org/IZA-SC/cif/{name}.cif`
   - Same processing as `cif[]` but with auto-download

**Key insight for complex hydrates:** `genice2-cif` treats the CIF as a "zeolite-like" framework. It identifies tetrahedral atoms (or user-specified atoms like O) and places water molecules there. Then GenIce2 applies ice rules + depolarization. If the CIF contains a hydrate structure, you MUST specify `:O=O` to tell it that O atoms are the water positions (not the default T/S atoms). For structures with guest atoms in the CIF, guests are currently IGNORED by the CIF parser — they'd need to be specified separately via `-g`/`-G` flags after cage detection.

## Approach Feasibility Verdicts

### A: Atomsk Subprocess

**Verdict:** BLOCKED for structure generation; FEASIBLE for polycrystalline assembly (optional)  
**Effort:** MEDIUM (polycrystal assembly integration)  
**Blockers:**
- ~~GPL-3.0 license creates distribution complications~~ → Subprocess use is legally safe (see corrected assessment below)
- **Zero hydrate lattice generation capability** — atomsk creates fcc, bcc, hcp lattices only. GenIce2 must generate the seed.
- No Python API — subprocess overhead, no programmatic control
- No GRO format support — requires XYZ bridge format
- Fortran95 codebase — cannot extend for hydrate-specific needs
- `--polycrystal` mode uses SINGLE seed — cannot directly create mixed sI+sII polycrystals

**Updated assessment (2026-06-12):** Previous research stated "atomsk has zero hydrate functionality" and dismissed it entirely. This was wrong. While atomsk cannot **generate** hydrate lattices, its `--polycrystal` mode is actively used by 7+ hydrate papers for creating Voronoi-tessellated polycrystalline hydrate structures from monocrystalline seeds (see ATOMSK-HYDRATE-DEEPDIVE.md). The `--merge` mode is less valuable since QuickIce already does stacking in Python with better GROMACS format support. For polycrystalline hydrate assembly specifically, atomsk provides genuine value (~200-300 LOC to replicate in Python).

**Risk:** LOW (subprocess is well-understood); MEDIUM (format conversion adds friction)  
**Recommendation:** **Add atomsk as an OPTIONAL external tool** for polycrystalline hydrate assembly via `--polycrystal` mode. GenIce2 generates the seed; atomsk assembles the polycrystal. GPL-3.0 is manageable via subprocess (same pattern as LAMMPS, Packmol).

---

### B: GenIce2 Custom Lattice Plugins

**Verdict:** FEASIBLE (primary approach for novel structures)  
**Effort:** LOW-MEDIUM per lattice plugin  
**Blockers:** None significant  
**Dependencies:** GenIce2 (already installed), crystallographic data for target structure  
**Risk:** LOW

**What's needed to create a custom lattice plugin for a semi-clathrate TBAB:**
1. Obtain crystallographic data (space group, asymmetric unit, cell params) — from ICSD or literature
2. Write ~40-80 line Python file defining `Lattice` class:
   - `cell` from lattice parameters via `cellvectors()`
   - `waters` from O positions (extracted via `CIF.waters_and_pairs()`)
   - `cagepos`/`cagetype` from cage center positions
   - `bondlen` and `density` from the structure
3. Place in `lattices/` folder next to QuickIce script (or register as entry point)
4. GenIce2 auto-discovers and applies ice rules + depolarization

**Can existing lattice plugins be modified for filled ice variants?**
Yes. The `c0te.py` pattern (CIF-like data + `CIF.waters_and_pairs()` + guest positions) is a template that works for any structure where you have crystallographic data. The `c1te.py` shows the hydrogen-ordered variant with `self.fixed` for fixed H-bond orientations.

**What data is needed for `cagepos`, `cagetype`, `waters`, `cell`, `bondlen`:**
- `cell`: 3 lattice parameters (a, b, c) and 3 angles (α, β, γ) — from CIF/literature
- `waters`: O atom positions in asymmetric unit + space group symmetry operations — from CIF
- `cagepos`/`cagetype`: Either manually specified (if known from structure analysis) or auto-detected via `assess_cages=True`
- `bondlen`: Auto-estimated if not specified (GenIce2 uses `1.1 * shortest_distance()`)

**How does the ice-rules algorithm handle non-standard cage geometries?**
GenIce2's ice-rule engine (`genice_core.ice_graph()`) operates on the **graph topology** of the H-bond network, not the cage geometry. It constructs a directed graph where each node (water molecule) must have exactly 2 incoming and 2 outgoing edges (Bernal-Fowler rules). This works for ANY tetrahedral network, regardless of cage shape. The engine uses depolarization optimization to minimize the net dipole moment of the structure. This is why GenIce2 works for 100+ different ice structures — the algorithm is structure-agnostic.

**Can `assess_cages=True` auto-detect cages in custom lattice structures?**
YES, but only for clathrate-like structures with well-defined polyhedral cages. Tested and confirmed: `assess_cages` detects cages in CS1 (sI) and EMT zeolite structures. For filled ices (c0te), it returns "No cages detected" — this is correct because filled ices have channels, not polyhedral cages. For semiclathrate TBAB, the water framework does form polyhedral cages, so `assess_cages` should detect them.

---

### C: GenIce2 CIF Import

**Verdict:** FEASIBLE (secondary approach for any structure with a CIF file)  
**Effort:** MEDIUM  
**Blockers:**
- `genice2-cif` was not previously installed; now installed and tested
- CIF parser assumes zeolite-like framework (default: T/S atoms = water positions)
- Must specify `:O=O` for hydrate CIFs where O atoms are water positions
- Guest atoms in CIF are IGNORED by the parser — must be specified separately
- IZA Zeolite DB may have availability/reliability issues (URL-based download)

**Dependencies:** `genice2-cif` (now installed), `cif2ice`, `requests`, `validators`  
**Risk:** MEDIUM

**genice2-cif plugin: what does it actually do?**
1. Reads a CIF file using `cif2ice.read_and_process()`
2. Extracts atom positions and cell shape from the CIF
3. Filters atoms by type (default: T/S = tetrahedral, O = ignored; override with `:O=O`)
4. Scales the structure so nearest O-O distance = 2.76 Å
5. Sets `self.waters`, `self.cell`, `self.coord = "relative"`, `self.density`
6. **Does NOT set cage positions** — use `assess_cages=True` for auto-detection

**Can it load arbitrary CIF files?**
YES, with caveats:
- The CIF must have valid `_atom_site_*` and `_cell_*` fields
- The CIF must contain atom positions that can be interpreted as water positions
- For hydrate CIFs: specify `:O=O` to use O atoms as water framework positions
- For zeolite CIFs: default T/S filtering works correctly

**If CIF files exist for complex hydrates, can GenIce2 use them directly?**
YES, with two steps:
1. `genice2 "cif[hydrate.cif:O=O]" --assess_cages` — loads the framework and detects cages
2. Then use `-g`/`-G` flags to place guests in detected cages

**What happens after CIF import?**
GenIce2 applies its full pipeline:
1. H-bond network construction (from `bondlen` threshold)
2. Ice rule enforcement (Bernal-Fowler: 2 donors, 2 acceptors per water)
3. Depolarization optimization (minimizes net dipole)
4. Water molecule placement (TIP4P, TIP3P, etc.)
5. Guest molecule placement (if cages detected + guests specified)

---

### D: Pure Python Builder with MDAnalysis + spglib

**Verdict:** ALTERNATIVE (fallback, NOT recommended as primary approach)  
**Effort:** HIGH  
**Blockers:**
- Neither MDAnalysis nor spglib can apply ice rules or depolarization
- Would need to reimplement GenIce2's core algorithm (~500+ lines of graph theory)
- No advantage over using GenIce2 directly
- MDAnalysis is for I/O and analysis, not structure building

**Dependencies:** MDAnalysis (installed), spglib (installed), numpy (installed)  
**Risk:** HIGH

**What would a "pure Python" complex hydrate builder require?**
1. CIF reader: pymatgen or spglib can handle this (~0 LOC — library function)
2. Symmetry expansion: spglib `get_symmetry()` + position generation (~50 LOC)
3. O-O pair detection: `scipy.spatial.cKDTree` or `pairlist` (~30 LOC)
4. **Ice rule enforcement**: Construct directed graph, find 2-in/2-out orientation (~200 LOC)
5. **Depolarization optimization**: NetworkX + random shuffling + dipole minimization (~200 LOC)
6. Water molecule placement: Apply rotation matrices to TIP4P coordinates (~50 LOC)
7. Guest molecule placement: Identify cage centers, place guests (~100 LOC)

**Estimated total: ~600-800 LOC** — all to reimplement what GenIce2 already does, with worse quality.

**Is atomsk even necessary, or can GenIce2 plugins + CIF import cover 90% of use cases?**
**GenIce2 plugins + CIF import covers 95%+ of use cases.** The only gap is multiple occupancy per cage (e.g., 2-4 H₂ molecules in a single large cage), which GenIce2 explicitly does NOT support. For this, a custom multi-molecule plugin is needed (~30 LOC to define a virtual "2H₂" molecule with 4 H atoms), NOT a full structure builder.

---

### E: External Pipeline (atomsk → CIF → GenIce2)

**Verdict:** BLOCKED (unnecessary, atomsk adds no value)  
**Effort:** N/A  
**Blockers:**
- Atomsk is GPL-3.0, not needed, adds complexity
- pymatgen reads CIF files directly with better Python integration
- genice2-cif reads CIF files directly into GenIce2
- The pipeline atomsk → CIF → GenIce2 is strictly worse than CIF → GenIce2 (skipping atomsk)

**Risk:** N/A  
**Recommendation:** **Do NOT use atomsk in any pipeline.** If CIF data is available, use `genice2-cif` directly or pymatgen for pre-processing.

---

### F: Expose Existing GenIce2 Features ("Free Wins")

**Verdict:** FEASIBLE (highest priority, lowest effort, highest impact)  
**Effort:** LOW  
**Blockers:** None — all backend support verified via API testing  
**Dependencies:** GenIce2 (already installed), `genice2-cif` (now installed)  
**Risk:** LOW

**Specific changes needed in QuickIce:**

| Feature | Change Required | LOC Estimate | Files to Modify |
|---------|----------------|-------------|-----------------|
| Add CO₂ guest | Add `"co2": {"name": "Carbon Dioxide", "formula": "CO₂", "atoms": 3, ...}` to `GUEST_MOLECULES` | ~5 | `types.py` |
| Add H₂ guest | Add `"h2": {"name": "Hydrogen", "formula": "H₂", "atoms": 2, ...}` to `GUEST_MOLECULES` | ~5 | `types.py` |
| Add ethane guest | Add `"et": {"name": "Ethane", "formula": "C₂H₆", "atoms": 1, ...}` to `GUEST_MOLECULES` | ~5 | `types.py` |
| Add filled ice lattices | Add `c0te`, `c1te`, `c2te`, `ice1hte`, `sTprime` to `HYDRATE_LATTICES` with cage info | ~50 | `types.py` |
| Add Ice XVII/XVI | Add `ice17`, `ice16` to `HYDRATE_LATTICES` | ~15 | `types.py` |
| Add additional water models | Add dropdown for TIP3P, TIP5P, SPC/E | ~20 | `hydrate_panel.py`, `hydrate_generator.py` |
| Mixed occupancy UI | Add second guest selector + occupancy slider per cage type | ~100 | `hydrate_panel.py`, `hydrate_generator.py`, `types.py` |
| Per-cage guest assignment | Add cage ID selector + guest type per cage | ~80 | `hydrate_panel.py`, `hydrate_generator.py` |
| Update `_LATTICE_MODULES` dict | Add imports for filled ice, semiclathrate modules | ~15 | `hydrate_generator.py` |
| Handle `cagepos`/`cagetype` vs `cages` | Support both GenIce2 cage storage formats | ~10 | `hydrate_generator.py` |

**Total estimated effort for all "free wins":** ~300-400 LOC across 3-4 files.

**What GenIce2 API changes are needed in `HydrateStructureGenerator`:**

The current `_run_via_api()` method is hardcoded for sI/sII/sH with single-guest occupancy. The changes needed:

1. **Dynamic lattice module loading:** Replace hardcoded `_LATTICE_MODULES = {"sI": sI, ...}` with `safe_import('lattice', lattice_name).Lattice()` (which already works in the current code at line 148)

2. **Support `cagepos`/`cagetype` attribute:** Filled ice plugins use `cagepos` (list) + `cagetype` (list) instead of the `cages` (string) format. GenIce2's `__init__` already handles both — no change needed in QuickIce.

3. **Support mixed occupancy:** The `parse_guest()` function already handles `12=co2*0.6+me*0.4`. QuickIce just needs to construct the correct guest spec string from UI inputs.

4. **Support per-cage assignment:** Pass `spot_guests` dict to `GenIce()` constructor. Already supported by the API.

5. **Support `depol` option:** Current code hardcodes `depol='strict'`. For semiclathrates with ion doping, `depol='optimal'` is needed. Add a dropdown.

## Comparison Matrix

| Criterion | A (Atomsk polycrystal) | B (GenIce2 Plugin) | C (CIF Import) | D (Pure Python) | E (Pipeline) | F (Free Wins) | G (Atomsk Assembly) |
|-----------|-----------|-------------------|----------------|-----------------|--------------|---------------|---------------------|
| Effort | MEDIUM | LOW-MED | MEDIUM | HIGH | N/A | **LOW** | MEDIUM |
| License Risk | **MANAGEABLE** (GPL-3.0 subprocess) | NONE (MIT) | NONE (MIT) | NONE (MIT) | HIGH (GPL) | NONE (MIT) | **MANAGEABLE** (subprocess) |
| Coverage | Polycrystal only | **90%+** | **95%+** (any CIF) | 70% (no ice rules) | 0% hydrate | **80%** of demand | Polycrystal + merge |
| Maintainability | MEDIUM (subprocess) | **HIGH** (Python) | HIGH (Python) | LOW (custom code) | LOW (multi-tool) | **HIGH** (minimal code) | MEDIUM (subprocess) |
| Ice Rules + Depol | ✅ (via GenIce2 seed) | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ (via GenIce2 seed) |
| Polycrystalline hydrate | ✅ **KEY VALUE** | ❌ | ❌ | ⚠️ (custom code) | ❌ | ❌ | ✅ **KEY VALUE** |
| Mixed-phase merge | ⚠️ (manual workaround) | ❌ | ❌ | ✅ (manual) | ❌ | ❌ | ⚠️ (manual workaround) |
| GRO format support | ❌ (XYZ bridge) | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ (XYZ bridge) |
| Time to Implement | 1-3 weeks | 1-3 weeks | 2-4 weeks | 4-8 weeks | N/A | **1-2 weeks** | 1-3 weeks | 1-3 weeks |

## Recommended Approach

**Three-phase pipeline, ordered by impact × feasibility (updated with atomsk option):**

### Phase 1: "Free Wins" (Weeks 1-2)
**Priority: CRITICAL — 80% of scientific value for 20% of effort**

1. Add filled ice lattice types to `HYDRATE_LATTICES` dict (c0te, c1te, c2te, ice1hte, sTprime)
2. Add CO₂, H₂, ethane to `GUEST_MOLECULES` dict
3. Add water model dropdown (TIP3P, TIP5P, SPC/E)
4. Add mixed occupancy UI (two guest types per cage type with occupancy sliders)
5. Add `depol` mode selector (`strict` vs `optimal`)
6. Update `HydrateStructureGenerator._run_via_api()` to use `safe_import('lattice', name)` dynamically
7. Add Ice XVII, Ice XVI to HYDRATE_LATTICES

**These changes are trivially bridgeable** because GenIce2's Python API already supports all of them. The current QuickIce code hardcodes sI/sII/sH + CH₄/THF, but the GenIce2 API is fully general.

### Phase 2: CIF Import Pipeline (Weeks 3-5)
**Priority: HIGH — enables arbitrary hydrate structures**

1. Add "Import from CIF" button to hydrate panel
2. File picker → `genice2-cif` lattice plugin → `assess_cages=True`
3. Display detected cages and allow guest placement per cage type
4. Add IZA Zeolite Database browser (for low-density ice analogs)
5. Add `:O=O` toggle for hydrate CIF files

**Key design decision:** For CIF import, `assess_cages=True` should be the default. This auto-detects cages so users can immediately place guests. If no cages are detected (e.g., filled ices from CIF), display a warning that the structure has no polyhedral cages for guest placement.

### Phase 3: Custom Lattice Plugins (Weeks 6-8)
**Priority: MEDIUM — for structures not in GenIce2 or available as CIF**

1. Create "Custom Lattice" wizard in QuickIce:
   - Input: space group, lattice parameters, asymmetric unit positions
   - Generate: lattice plugin Python file
   - Test: run `genice2 <custom_name>` and validate output
2. Pre-built lattice plugins for common requests:
   - TBAB semiclathrate (with correct cage + ion layout)
   - TBPB semiclathrate
   - TMAF semiclathrate
3. Custom molecule plugin wizard:
   - Input: atom names, positions, residue name
   - Generate: molecule plugin Python file
   - For multiple H₂ per cage: virtual "2H₂" / "4H₂" molecule plugins

### Phase 4: Atomsk Integration for Polycrystalline Hydrates (Weeks 9-11)
**Priority: MEDIUM — enables polycrystalline hydrate, a genuine scientific use case**

1. Add "Polycrystalline" mode to QuickIce (optional, requires atomsk)
2. Detect atomsk installation: `subprocess.run(["atomsk", "--version"])`
3. Generate monocrystalline seed from GenIce2 → XYZ
4. Write atomsk parameter file from user inputs (grain count, box size, orientations)
5. Call `atomsk --polycrystal seed.xyz params.txt output.lmp -wrap -rmd 1.5`
6. Parse LAMMPS output → reconstruct residue names → write GRO
7. Add optional `-remove-doubles` distance parameter in UI
8. Generate atomsk auxiliary file outputs (*_id-size.txt for grain info)

**This phase is distinct from Phase 1-3** because it requires:
- An external optional dependency (atomsk binary)
- Format conversion pipeline (GenIce2 XYZ → atomsk → LAMMPS → GRO)
- Residue name reconstruction from element-only atom names
- Error handling for missing atomsk installation

### Phase 5: Packmol Integration (Weeks 12+)
**Priority: LOW — for complex guest placement beyond GenIce2's guest system**

1. Use Packmol for placing guest molecules inside hydrate cages when GenIce2's `-g`/`-G` flags are insufficient
2. Requires cage center extraction from GenIce2 output
3. Build Packmol input file generation
4. Handle Packmol subprocess errors

---

### G: Atomsk for Polycrystalline/Mixed Hydrate Assembly (NEW — corrective addition)

**Verdict:** FEASIBLE as optional tool for polycrystalline hydrate assembly
**Effort:** MEDIUM
**Blockers:**
- Atomsk not installed locally (user must install separately)
- No GRO format support (requires XYZ bridge format + residue name reconstruction)
- `--polycrystal` uses single seed (cannot mix different hydrate phases in one polycrystal)
- GPL-3.0 (manageable via subprocess, but adds dependency complexity)

**Dependencies:** GenIce2 (provides seed structures), atomsk binary (user-installed), MDAnalysis (for XYZ↔GRO conversion)
**Risk:** MEDIUM (format conversion, error handling, optional dependency detection)

**What this approach enables:**

1. **Polycrystalline hydrate** — Voronoi-tessellated polycrystal from a monocrystalline hydrate seed (the primary value). 7+ hydrate papers use this exact workflow. The polycrystal can have:
   - Random grain positions and orientations
   - User-specified grain positions and orientations
   - Box dimensions and grain count control
   - Grain boundary cleanup via `-remove-doubles`

2. **Nanocrystalline hydrate** — Small grain sizes (5-20 nm) with many grains, studying grain-size-dependent mechanical properties

3. **Columnar polycrystals** — 2D Voronoi + duplicate along short axis

4. **Hydrate/water interface construction** — `--merge z` to stack hydrate slabs and water layers (but QuickIce's Python code is better for this)

**What this approach does NOT enable:**

1. **Mixed sI+sII polycrystal** — `--polycrystal` uses a single seed; workaround requires `--cut` + `--merge`
2. **Direct GROMACS output** — No GRO support; must convert via XYZ or LAMMPS format
3. **Structure generation** — Atomsk cannot generate any hydrate lattice; GenIce2 must provide the seed
4. **Ice rules / hydrogen disorder** — Atomsk just geometrically copies the seed; all ice-rule processing is done by GenIce2 before the atomsk step

**Integration pattern:**

```
QuickIce UI: "Polycrystalline" tab/mode
  1. Generate seed: GenIce2 → XYZ (monocrystalline sI/sII/sH)
  2. Write atomsk param file: box dimensions, grain count, orientations
  3. Call: atomsk --polycrystal seed.xyz params.txt output.lmp -wrap -rmd 1.5
  4. Parse LAMMPS output → reconstruct residue names → write GRO
  5. Output GRO + TOP for GROMACS
```

**Estimated LOC:** ~150-200 for atomsk wrapper (param file generation, subprocess call, LAMMPS parsing, residue reconstruction)

**Compared to building this in Python:** ~200-300 LOC for Voronoi polycrystal + ~100 LOC for rotation + ~50 LOC for boundary cleanup = ~350-450 LOC total, with more edge cases and less testing

**Recommendation:** Add atomsk support as an optional feature (like Packmol). If atomsk is installed, enable the polycrystalline mode. If not, show installation instructions. This is the standard pattern for optional GPL tools in MIT-licensed projects.

## Key Technical Findings from Hands-On Testing

| Test | Result | Confidence |
|------|--------|------------|
| `c0te` generation via `GenIce()` Python API | ✅ SUCCESS — 192 atoms, valid GRO output | HIGH |
| `CS1` (sI) generation via `GenIce()` API | ✅ SUCCESS — cage types [12, 14] detected | HIGH |
| `genice2-cif` loading of EMT.cif | ✅ SUCCESS — 384 atoms, zeolite ice | HIGH |
| `assess_cages=True` with CS1 | ✅ SUCCESS — cages auto-detected | HIGH |
| `assess_cages=True` with c0te (filled ice) | ✅ Returns "No cages" — CORRECT, filled ices have channels not cages | HIGH |
| `assess_cages=True` with CIF-imported lattice | ✅ SUCCESS — works for clathrate-like structures | HIGH |
| CO₂ molecule plugin loading | ✅ SUCCESS — 3-atom linear C+2O | HIGH |
| H₂ molecule plugin loading | ✅ SUCCESS — 2-atom linear | HIGH |
| Mixed occupancy `12=me, 14=co2` | ✅ SUCCESS — binary clathrate | HIGH |
| Fractional mixed `14=co2*0.6+me*0.4` | ✅ SUCCESS — 60% CO₂ + 40% CH₄ in large cages | HIGH |
| Per-cage assignment `spot_guests={0: 'me', 2: 'co2'}` | ✅ SUCCESS | HIGH |
| Custom local lattice plugin (`./lattices/test_custom.py`) | ✅ SUCCESS — loaded via `safe_import()` | HIGH |
| `genice2-cif` pip install | ✅ INSTALLED — v2.2.1 with dependencies | HIGH |
| `cif2ice.read_and_process()` API | ✅ Functional — reads CIF, returns atoms + cellshape | HIGH |

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| Atomsk is NOT needed | **HIGH** | Verified via source code analysis + capability comparison; hands-on GenIce2 testing confirms all useful features covered |
| GenIce2 API supports "free wins" | **HIGH** | All features tested via Python API; code changes are trivial (adding dict entries, updating imports) |
| Custom lattice plugins are easy | **HIGH** | Pattern verified from 5+ existing plugins; test plugin written and loaded successfully |
| CIF import works | **HIGH** | Tested with EMT.cif + assess_cages; `genice2-cif` now installed |
| `assess_cages` auto-detects cages | **MEDIUM-HIGH** | Works for clathrates; does NOT work for filled ices (expected); semiclathrate behavior not directly tested but should work |
| Semiclathrate TBAB preset | **MEDIUM** | GenIce2 supports HS1 + ion/group flags, but it requires multi-step manual assembly; one-click preset needs careful cage+ion mapping |
| Multiple H₂ per cage | **LOW-MEDIUM** | GenIce2 explicitly does NOT support this; would need custom virtual molecule plugin; not yet tested |
| CIF availability for complex hydrates | **MEDIUM** | Filled ices: available in GenIce2 source; TBAB: in ICSD (commercial); other semiclathrates: limited free availability |

## Sources

| Source | URL/Path | Confidence | Used For |
|--------|----------|------------|----------|
| GenIce2 source: `genice2/genice.py` | Local: `/share/.../genice2/genice.py` | HIGH | Plugin loading, `GenIce` class, `generate_ice()` pipeline, `assess_cages`, guest placement |
| GenIce2 source: `genice2/plugin.py` | Local: `/share/.../genice2/plugin.py` | HIGH | `safe_import()` priority order, entry points, local plugin loading |
| GenIce2 source: `genice2/CIF.py` | Local: `/share/.../genice2/CIF.py` | HIGH | `atomdic()`, `fullatoms()`, `waters_and_pairs()`, `symmetry_operators()` helpers |
| GenIce2 source: `genice2/cage.py` | Local: `/share/.../genice2/cage.py` | HIGH | `assess_cages()` implementation, cage classification, ring detection |
| GenIce2 source: `genice2/valueparser.py` | Local: `/share/.../genice2/valueparser.py` | HIGH | `parse_cages()`, `parse_guest()`, `plugin_option_parser()` |
| GenIce2 lattice: `c0te.py` | Local: `/share/.../genice2/lattices/c0te.py` | HIGH | Filled ice lattice plugin pattern (CIF-like data) |
| GenIce2 lattice: `c1te.py` | Local: `/share/.../genice2/lattices/c1te.py` | HIGH | Hydrogen-ordered filled ice pattern (fixed pairs) |
| GenIce2 lattice: `CS1.py` | Local: `/share/.../genice2/lattices/CS1.py` | HIGH | Clathrate lattice plugin pattern (pre-computed positions) |
| GenIce2 lattice: `HS1.py` | Local: `/share/.../genice2/lattices/HS1.py` | HIGH | Semiclathrate lattice (cages string format, ion doping) |
| GenIce2 lattice: `ice1hte.py` | Local: `/share/.../genice2/lattices/ice1hte.py` | HIGH | Filled ice Ih pattern (CIF-like + repeat) |
| genice2-cif: `lattices/cif.py` | Local: `/share/.../genice2_cif/lattices/cif.py` | HIGH | CIF import implementation, `genice_lattice()`, `:O=O` option |
| genice2-cif: `lattices/zeolite.py` | Local: `/share/.../genice2_cif/lattices/zeolite.py` | HIGH | IZA DB download + CIF import |
| GenIce2 molecules: `co2.py` | Local: `/share/.../genice2/molecules/co2.py` | HIGH | CO₂ molecule plugin (3 atoms: C + 2 O) |
| QuickIce: `hydrate_generator.py` | Local: `/share/.../quickice/quickice/structure_generation/hydrate_generator.py` | HIGH | Current API integration, hardcoded sI/sII/sH + CH₄/THF |
| QuickIce: `types.py` | Local: `/share/.../quickice/quickice/structure_generation/types.py` | HIGH | `HYDRATE_LATTICES`, `GUEST_MOLECULES` dicts, `HydrateConfig` |
| QuickIce: `hydrate_panel.py` | Local: `/share/.../quickice/quickice/gui/hydrate_panel.py` | HIGH | Current GUI layout, lattice/guest dropdowns |
| Hands-on API testing | Local Python 3.14 environment | HIGH | c0te generation, CIF import, assess_cages, mixed occupancy, per-cage guests, custom plugin |
| Wave 1: STACK.md | `.planning/research/future-ml/complex-hydrate-atomsk/STACK.md` | HIGH | Technology recommendations, atomsk analysis |
| Wave 1: FEATURES.md | `.planning/research/future-ml/complex-hydrate-atomsk/FEATURES.md` | HIGH | Feature gap analysis, demand assessment |
