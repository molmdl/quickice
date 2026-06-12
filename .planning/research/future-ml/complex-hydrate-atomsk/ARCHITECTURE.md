# Architecture Patterns: Complex Hydrate Generation

**Domain:** Clathrate hydrate structure generation
**Researched:** 2026-06-12
**Confidence:** HIGH (based on direct source code analysis)

## Recommended Architecture

QuickIce uses an **MVVM (Model-View-ViewModel)** pattern with **QThread-based workers** for background computation. The hydrate tab currently follows:

```
HydratePanel (View) → HydrateWorker (QThread) → HydrateStructureGenerator (Model)
       ↕                        ↕                           ↕
  HydrateViewer           signals to MainWindow      GenIce2 Python API
       ↕                                                   ↕
  HydrateRenderer (VTK)                            genice2.lattices.*
                                                   genice2.formats.gromacs
```

**The recommended extension strategy: augment the existing MVVM pipeline**, not replace it. Each new capability should slot into the existing pattern:

1. **Expand `types.py`** config dicts (HYDRATE_LATTICES, GUEST_MOLECULES) — this is the "free wins" path
2. **Extend `HydrateStructureGenerator`** to handle new lattice types and guest molecules via GenIce2's plugin system
3. **Add new Worker classes** only when the computation pattern differs significantly (e.g., CIF import with validation)
4. **Add new Panel widgets** within the existing Hydrate tab, not new tabs

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `types.py` (HYDRATE_LATTICES, GUEST_MOLECULES) | Data definitions: lattice metadata, guest metadata, cage info | HydratePanel, HydrateGenerator, HydrateExport, HydrateRenderer |
| `HydratePanel` (View) | UI controls: lattice dropdown, guest dropdown, occupancy sliders, supercell spinboxes | MainWindow (signals), HydrateViewer |
| `HydrateWorker` (QThread) | Background thread for GenIce2 generation | HydratePanel (progress signals), MainWindow (completion signals) |
| `HydrateStructureGenerator` (Model) | GenIce2 API wrapper: builds GenIce instance, calls generate_ice, parses GRO output | HydrateWorker, types.py |
| `HydrateViewer` | VTK 3D rendering of hydrate structure | HydrateRenderer, HydratePanel |
| `HydrateRenderer` | VTK actor creation for water framework + guest molecules | HydrateViewer |
| `HydrateExport` | GROMACS file export (.gro + .top + .itp) | MainWindow, MoleculetypeRegistry, data/ ITP files |
| `MainWindow` | Orchestrator: connects panel signals to workers, stores results for cross-tab flow | All panels, ViewModel, all workers |

### Data Flow (Current)

```
User clicks "Generate Hydrate"
  → HydratePanel.generate_requested signal
    → MainWindow._on_hydrate_generate_clicked()
      → HydratePanel.get_configuration() → HydrateConfig
      → HydrateWorker(config).start()
        → HydrateWorker.run()
          → HydrateStructureGenerator().generate(config)
            → _ensure_genice_import() (lazy, thread-safe)
            → safe_import('lattice', lattice_name).Lattice()
            → GenIce(lattice, reshape=supercell_matrix)
            → parse_guest(guests, guest_spec)
            → ice.generate_ice(formatter, water, guests, depol='strict')
            → _parse_gro_result(gro_string)
            → _build_molecule_index(atom_names, positions, residue_names, seq_nums)
          → HydrateStructure returned
        → generation_complete signal
      → MainWindow stores _current_hydrate_result
      → HydratePanel.set_hydrate_structure(result)
        → HydrateViewer renders via HydrateRenderer
```

### Data Flow (Cross-Tab: Hydrate → Interface)

```
Hydrate Tab result stored in MainWindow._current_hydrate_result
  → User selects "Hydrate" source in Interface Tab
  → MainWindow._on_interface_hydrate_generate()
    → hydrate.to_candidate() → Candidate
    → MainViewModel.start_interface_generation(candidate, config)
    → InterfaceGenerationWorker → InterfaceBuilder → InterfaceStructure
```

## Architecture Options

### Option A: GenIce2 Custom Lattice Plugin

**Strategy:** Create a new Python module in a `lattices/` directory (GenIce2's plugin discovery path) that defines a custom hydrate lattice not in GenIce2's catalog (e.g., TBAB semiclathrate, TBPB semiclathrate).

**When to use:** When a specific hydrate structure is needed that GenIce2 doesn't have built-in, but crystallographic data (space group, lattice params, atomic positions) IS available.

#### Component Diagram

```
quickice/
├── structure_generation/
│   ├── types.py              ← ADD new entries to HYDRATE_LATTICES
│   ├── hydrate_generator.py  ← EXTEND _run_via_api() to handle new lattice types
│   └── custom_lattice_builder.py  ← NEW: converts crystallographic data → GenIce2 Lattice class
│
├── data/
│   └── lattices/              ← NEW: custom lattice definitions as Python modules
│       ├── tbab.py             ← TBAB semiclathrate lattice
│       └── tbpb.py             ← TBPB semiclathrate lattice
│
├── gui/
│   ├── hydrate_panel.py       ← EXTEND: add "Custom / Semiclathrate" section
│   ├── hydrate_worker.py      ← MINIMAL CHANGES: already handles arbitrary configs
│   └── hydrate_export.py      ← EXTEND: handle guest ITP files for semiclathrate ions
```

#### Data Flow

```
1. Crystallographic data (from literature) → Python Lattice module in data/lattices/
2. Lattice module defines:
   - self.cell (cell vectors)
   - self.waters (O positions)
   - self.cagetype + self.cagepos (cage definitions)
   - self.density, self.bondlen, self.coord
3. HydrateStructureGenerator._run_via_api():
   - safe_import('lattice', lattice_name) → finds module in lattices/ dir
   - OR: import from quickice.data.lattices.{name}
   - GenIce(lattice, reshape=...) → generate_ice(...)
4. Standard pipeline continues (parse GRO, build molecule_index, render, export)
```

#### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `types.py` | MODIFY | Add new entries to HYDRATE_LATTICES dict (e.g., "tbaB": {...}) |
| `hydrate_generator.py` | MODIFY | Extend _LATTICE_MODULES and _run_via_api() to load custom lattices from data/lattices/ |
| `hydrate_panel.py` | MODIFY | Add "Semiclathrate" sub-section or category separator in lattice dropdown |
| `hydrate_export.py` | MODIFY | Add ITP files for semiclathrate ions (TBA, Br) |
| `data/lattices/` | NEW DIR | Custom GenIce2 Lattice modules |
| `data/lattices/tbab.py` | NEW FILE | TBAB lattice definition |
| `data/tba.itp`, `data/br.itp` | NEW FILES | GROMACS topology for semiclathrate ions |

#### Pros

- **Follows GenIce2's established pattern** — custom lattice modules are how GenIce2 was designed to be extended
- **Ice rules + depolarization come for free** — GenIce2's core algorithm handles hydrogen disordering
- **Reuses entire existing pipeline** — same _run_via_api(), same _parse_gro_result(), same HydrateWorker, same renderer
- **Low risk** — GenIce2's Lattice interface is simple (just set `self.cell`, `self.waters`, `self.cagepos`, `self.cagetype`)

#### Cons

- **Requires crystallographic data** — must know exact O positions, space group, cage centers
- **One lattice per module** — each new structure needs its own Python file
- **No runtime CIF loading** — lattice is hardcoded in Python, not read from file
- **GenIce2 plugin discovery** — must ensure GenIce2 can find modules in `data/lattices/` (may need `lattices/` in CWD or sys.path manipulation)

#### Verdict

**Recommended for well-known, frequently-requested structures (TBAB semiclathrate).** The effort is moderate (writing a ~50-line Python module per lattice), but the payoff is full integration with GenIce2's ice rules and hydrogen disordering. Best used when the same structure will be requested many times.

---

### Option B: GenIce2 CIF Import via genice2-cif

**Strategy:** Install the `genice2-cif` package, which allows `genice2 "cif[structure.cif]"` to read any CIF file and generate an H-disordered ice structure from it. QuickIce adds a CIF file upload UI.

**When to use:** When the user has a CIF file from literature or a database, and needs to convert it to a hydrogen-disordered ice/hydrate structure.

#### Component Diagram

```
quickice/
├── structure_generation/
│   ├── types.py                ← ADD "cif_import" as a virtual lattice type
│   ├── hydrate_generator.py    ← EXTEND: handle cif[] lattice name in _run_via_api()
│   └── cif_validator.py        ← NEW: validate CIF file before passing to GenIce2
│
├── gui/
│   ├── hydrate_panel.py        ← EXTEND: add "Import CIF" button + file picker
│   ├── hydrate_worker.py       ← MINIMAL CHANGES
│   └── cif_preview_dialog.py   ← NEW (optional): show CIF contents before import
│
├── data/
│   └── cif_examples/           ← NEW: bundled example CIF files for common hydrates
```

#### Data Flow

```
1. User clicks "Import CIF" → QFileDialog.getOpenFileName("*.cif")
2. Selected CIF path stored in HydrateConfig.cif_path
3. HydrateWorker.run() → HydrateStructureGenerator.generate(config)
4. _run_via_api():
   a. lattice_name = f"cif[{config.cif_path}]"
   b. safe_import('lattice', lattice_name) → loads genice2-cif plugin
   c. GenIce(cif_lattice, reshape=...) → generate_ice(formatter, water, guests, ...)
   d. CIF file is parsed internally by genice2-cif's cif2ice module
5. Standard pipeline continues
```

#### Key Integration Detail

GenIce2's `safe_import` function discovers lattice plugins by:
1. Looking in `genice2.lattices` package (built-in)
2. Looking in a `lattices/` directory in the current working directory (CWD)
3. The `genice2-cif` package installs a `cif` lattice plugin

The `cif[filename.cif]` syntax is handled by the genice2-cif plugin's Lattice class, which reads the CIF file and generates the water network + cage definitions.

**CIF → GenIce2 resolution chain:**
```python
# In hydrate_generator.py _run_via_api():
lattice_name = f"cif[{cif_path}]"
lattice = safe_import('lattice', lattice_name).Lattice()
# This triggers genice2-cif to read the CIF file and build a Lattice object
```

#### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `types.py` | MODIFY | Add `cif_path` field to HydrateConfig, add CIF-related validation |
| `hydrate_generator.py` | MODIFY | Handle `cif[]` lattice names, add genice2-cif import handling |
| `hydrate_panel.py` | MODIFY | Add "Import CIF" button, file picker, CIF path display, optional guest specification |
| `hydrate_worker.py` | MINIMAL | Already handles arbitrary configs |
| `cif_validator.py` | NEW | Validate CIF before import (check for space group, atom positions) |
| `pyproject.toml` | MODIFY | Add `genice2-cif>=2.2.1` as optional dependency |

#### Pros

- **Maximum flexibility** — any structure with a CIF file can be imported
- **Ice rules come for free** — genice2-cif applies Bernal-Fowler rules to any O-network
- **Zeolite DB access** — `genice2 "zeolite[ITT]"` for IZA database structures
- **No hardcoded crystallographic data** — read from file at runtime

#### Cons

- **New dependency** — `genice2-cif` is NOT currently installed (confirmed: `pip list | grep genice2-cif` returns nothing)
- **CIF quality varies** — poor CIF files (missing symmetry ops, wrong atom types) will cause silent failures or incorrect structures
- **No cage filling by default** — genice2-cif produces the water framework, but cage guest assignment requires manual `-g`/`-G` flags or post-processing
- **Semiclathrate ions** — CIF import doesn't know which atoms are cations/anions; manual `-c`/`-a` flags needed
- **File path management** — CIF path must survive CWD changes; absolute paths preferred

#### Verdict

**Recommended as Phase 2 feature** (after "free wins"). Provides maximum flexibility for novel structures, but requires `genice2-cif` installation and CIF validation. The main risk is CIF file quality — a validation layer is essential.

---

### Option C: Pure Python Structure Builder with pymatgen

**Strategy:** Build hydrate structures from scratch using pymatgen for crystallographic I/O and spglib for symmetry, bypassing GenIce2 entirely for structures GenIce2 doesn't support.

**When to use:** When GenIce2 cannot handle the structure (e.g., no ice rules needed, non-ice frameworks, arbitrary crystal structures with no O-network).

#### Component Diagram

```
quickice/
├── structure_generation/
│   ├── types.py                      ← ADD ComplexHydrateConfig, ComplexHydrateStructure
│   ├── hydrate_generator.py          ← UNCHANGED (GenIce2 path)
│   ├── complex_hydrate_builder.py    ← NEW: pymatgen-based builder
│   │   ├── read_cif(path) → pymatgen.Structure
│   │   ├── extract_cage_centers(structure) → cage_positions
│   │   ├── place_guests(cage_centers, guest_molecules) → full_structure
│   │   └── to_gro_string(structure) → GRO format output
│   └── cage_detector.py              ← NEW: identify cage centers from O-network
│
├── gui/
│   ├── hydrate_panel.py              ← EXTEND: add "Advanced Builder" mode
│   ├── complex_hydrate_worker.py     ← NEW: Worker for pymatgen-based generation
│   └── complex_hydrate_panel.py       ← NEW (optional): separate panel for builder UI
```

#### Data Flow

```
1. User provides CIF file or space group + lattice params
2. complex_hydrate_builder:
   a. pymatgen.Structure.from_file("hydrate.cif") → read crystal structure
   b. OR: pymatgen.Structure.from_spacegroup(sg, lattice, species, coords)
   c. cage_detector: analyze O-network → find cage centers via Voronoi decomposition
   d. place_guests: insert guest Molecule objects at cage centers
   e. validate: check steric clashes, cage occupancy
   f. to_gro_string: convert pymatgen Structure → GRO format
3. Parse GRO string → HydrateStructure (reuse existing parser)
4. Standard pipeline continues (render, export)
```

#### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `types.py` | MODIFY | Add ComplexHydrateConfig dataclass |
| `complex_hydrate_builder.py` | NEW | pymatgen-based structure builder |
| `cage_detector.py` | NEW | Voronoi-based cage center detection |
| `complex_hydrate_worker.py` | NEW | QThread worker for builder |
| `hydrate_panel.py` | MODIFY | Add "Advanced Builder" sub-mode |
| `pyproject.toml` | MODIFY | Add `pymatgen>=2026.5` dependency |

#### Pros

- **Full control** — no dependency on GenIce2's limitations
- **pymatgen is MIT** — no license issues
- **Powerful CIF I/O** — best-in-class CIF reader with space group expansion
- **Can handle non-ice frameworks** — zeolites, MOFs, any periodic structure

#### Cons

- **NO ice rules or depolarization** — pymatgen has no concept of Bernal-Fowler rules. The resulting structure will have ordered hydrogens unless you add an explicit disordering step. This is GenIce2's unique value.
- **Cage detection is non-trivial** — Voronoi decomposition gives Voronoi nodes, not necessarily physical cage centers. Requires careful algorithm design.
- **Guest placement is manual** — no built-in concept of "cage type" → "guest type" mapping. Must be implemented from scratch.
- **Duplicate effort** — GenIce2 already does ice rules + cage filling. Reimplementing in pymatgen is significant effort with no ice-rule guarantee.
- **Output format mismatch** — pymatgen outputs CIF/POSCAR, not GRO. Must convert to GRO format for GROMACS compatibility.

#### Verdict

**NOT recommended as the primary approach.** Use pymatgen only when GenIce2 genuinely cannot handle the structure (non-ice frameworks, no hydrogen disordering needed). For any structure with a water O-network, GenIce2 + genice2-cif (Option B) is far superior because it provides ice rules + depolarization for free.

**Use pymatgen as a supporting tool** for CIF validation and format conversion, not as a replacement for GenIce2.

---

### Option D: Expose Existing GenIce2 Features in QuickIce UI ("Free Wins")

**Strategy:** Add existing GenIce2 lattice types and guest molecules to QuickIce's configuration dicts, requiring only UI and config changes — no new backend code.

**When to use:** ALWAYS FIRST. This is the highest-impact, lowest-effort option.

#### Component Diagram

```
Changes are MINIMAL:

types.py:
  HYDRATE_LATTICES += {c0te, c1te, c2te, ice1hte, sTprime, sIV, sV, sVII, ice17, ice16}
  GUEST_MOLECULES += {co2, H2, et (ethane)}
  HydrateConfig.cage_occupancy_small → extend to handle 3+ cage types

hydrate_panel.py:
  Lattice dropdown: add "Filled Ice" and "Exotic" categories
  Guest dropdown: add CO2, H2, Ethane
  Occupancy: add 3rd cage type slider for sH (medium cages)
  Water model dropdown: add TIP3P, TIP5P, SPC/E
  Mode selector: add "Mixed Occupancy" for binary clathrates

hydrate_generator.py:
  _LATTICE_MODULES += {c0te, c1te, c2te, ice1hte, sTprime, ...}
  _run_via_api(): handle mixed guest syntax (e.g., "-g 12=co2*0.6+me*0.4")
  Water model: add option to select non-TIP4P models

hydrate_export.py:
  _get_hydrate_guest_itp_path(): add co2.itp, h2.itp, et.itp

data/:
  Add co2_hydrate.itp, h2_hydrate.itp, et_hydrate.itp
```

#### Data Flow

```
IDENTICAL to current flow, just with expanded options:

User selects "c0te (Filled Ice C0)" from dropdown
  → HydrateConfig(lattice_type="c0te", guest_type="ne", ...)
  → HydrateWorker → HydrateStructureGenerator._run_via_api()
    → safe_import('lattice', 'c0te').Lattice()  ← GenIce2 already has this!
    → GenIce(lattice, reshape=...)
    → ice.generate_ice(formatter, water, guests, depol='strict')
  → HydrateStructure → render → export
```

#### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `types.py` | MODIFY | Add 8+ lattice entries to HYDRATE_LATTICES, add 3 guest entries to GUEST_MOLECULES |
| `hydrate_generator.py` | MODIFY | Extend _LATTICE_MODULES dict, add mixed-occupancy guest building, add water model selection |
| `hydrate_panel.py` | MODIFY | Expand lattice dropdown (add categories), expand guest dropdown, add mixed-occupancy UI, add water model dropdown |
| `hydrate_export.py` | MODIFY | Handle new guest ITP files |
| `hydrate_renderer.py` | MINIMAL | May need new CPK colors for new atom types (e.g., N for Ne) |
| `data/co2_hydrate.itp` | NEW | CO2 GROMACS topology for hydrate |
| `data/h2_hydrate.itp` | NEW | H2 GROMACS topology for hydrate |
| `data/et_hydrate.itp` | NEW | Ethane GROMACS topology for hydrate |

#### Pros

- **80% of the scientific value for 20% of the effort** — GenIce2 already does all the work
- **Zero new backend code** — just configuration changes
- **Zero risk** — GenIce2's existing code is battle-tested
- **Immediate user benefit** — filled ices, CO2 guest, mixed occupancy are the most-requested features
- **Tested by GenIce2 community** — these lattice types are used by other researchers

#### Cons

- **Limited to GenIce2's catalog** — can only expose what GenIce2 already has
- **UI complexity** — more dropdown options, more occupancy sliders, more configuration
- **Mixed occupancy UI is non-trivial** — need sliders + combo boxes for per-cage-type guest assignment
- **Some structures need 3+ cage types** — sH has small/medium/large, requiring 3 occupancy sliders instead of 2

#### Verdict

**HIGHEST PRIORITY. Do this first.** This option provides the largest scientific value increase with the lowest risk and effort. The main design work is in the UI (mixed occupancy controls, lattice categorization), not in the backend.

---

### Option E: Packmol Integration for Complex Guest Placement

**Strategy:** Use Packmol (MIT license, pip-installable) to place guest molecules inside hydrate cages when GenIce2's built-in guest system is insufficient — e.g., large organic guests, multi-atom guests with specific orientations, or mixed cage scenarios.

**When to use:** When the guest molecule is too large or complex for GenIce2's `-g`/`-G` flags (e.g., TBAB butyl groups, MEG, long-chain alcohols).

#### Component Diagram

```
quickice/
├── structure_generation/
│   ├── types.py                    ← ADD PackmolConfig
│   ├── hydrate_generator.py        ← UNCHANGED
│   ├── packmol_placer.py           ← NEW: wrapper for Packmol subprocess
│   │   ├── generate_empty_framework(config) → GRO file of empty hydrate
│   │   ├── extract_cage_centers(structure) → cage center coordinates
│   │   ├── build_packmol_input(cage_centers, guest_mol) → Packmol input file
│   │   └── run_packmol(input_file) → GRO/PDB output
│   └── cage_center_extractor.py    ← NEW: find cage centers from GenIce2 output
│
├── gui/
│   ├── hydrate_panel.py            ← EXTEND: add "Packmol Placement" mode
│   ├── packmol_worker.py           ← NEW: QThread worker for Packmol subprocess
│   └── packmol_config_panel.py     ← NEW (optional): Packmol-specific configuration
│
├── data/
│   └── guest_pdbs/                 ← NEW: PDB files for common guest molecules
│       ├── thf.pdb
│       ├── tba.pdb
│       └── co2.pdb
```

#### Data Flow

```
1. Generate empty hydrate framework with GenIce2:
   genice2 CS2 -g 12=empty -g 16=empty → empty_sII.gro

2. Extract cage centers from GenIce2 output:
   Parse GRO file → find O-network → Voronoi decomposition → cage center positions
   OR: Use GenIce2's --assess_cages flag to output cage info

3. Build Packmol input file:
   structure empty_sII.gro
     number 1
     inside box 0 0 0 Lx Ly Lz
   end
   structure thf.pdb
     number 8
     inside sphere cx cy cz R   # One sphere per large cage
   end
   structure ch4.pdb
     number 16
     inside sphere cx cy cz R   # One sphere per small cage
   end

4. Run Packmol subprocess:
   subprocess.run(["packmol"], input=packmol_input)

5. Parse Packmol output → combine with empty framework → HydrateStructure
```

#### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `types.py` | MODIFY | Add PackmolConfig dataclass |
| `packmol_placer.py` | NEW | Packmol wrapper (subprocess call + I/O) |
| `cage_center_extractor.py` | NEW | Extract cage centers from GenIce2 output |
| `packmol_worker.py` | NEW | QThread worker for Packmol execution |
| `hydrate_panel.py` | MODIFY | Add "Packmol Placement" mode toggle |
| `pyproject.toml` | MODIFY | Add `packmol>=21.2` as optional dependency |
| `data/guest_pdbs/` | NEW DIR | PDB files for guest molecules |

#### Pros

- **Handles arbitrarily complex guests** — large organic molecules, complex orientations
- **Steric clash avoidance** — Packmol guarantees no atom-atom overlaps
- **MIT license** — no licensing concerns
- **pip-installable** — `pip install packmol` works (installs the Fortran binary)

#### Cons

- **Subprocess-based** — not a Python API; format conversion overhead
- **Requires cage center knowledge** — must know where cages are to define spatial constraints
- **No ice rules** — Packmol just packs molecules; if you need H-disordered water, you still need GenIce2 first
- **Error handling is tricky** — Packmol's failure modes are hard to parse from output
- **Significant implementation effort** — cage center extraction, Packmol input generation, output parsing

#### Verdict

**Recommended as Phase 3+ feature** for advanced use cases (large organic guests in semiclathrates). The "free wins" (Option D) and CIF import (Option B) cover most use cases. Packmol is only needed when GenIce2's guest system (`-g`, `-G`, `-H`) is insufficient for the specific guest molecule.

---

## Recommended Implementation Order

| Priority | Option | Rationale | Phase |
|----------|--------|-----------|-------|
| 1 | **Option D: Free Wins** | Highest impact/effort ratio; unlocks 80% of new capabilities | v5.0 |
| 2 | **Option B: CIF Import** | Maximum flexibility for novel structures; builds on Option D | v5.1 |
| 3 | **Option A: Custom Lattice Plugin** | For frequently-requested structures (TBAB) that need one-click presets | v6.0 |
| 4 | **Option E: Packmol** | For complex guest placement beyond GenIce2's guest system | v7.0 |
| 5 | **Option C: pymatgen Builder** | Only for non-ice frameworks; avoid unless GenIce2 genuinely can't handle it | Deferred |

## Patterns to Follow

### Pattern 1: Config Dict Extension (for "Free Wins")

**What:** Extend `HYDRATE_LATTICES` and `GUEST_MOLECULES` dictionaries in `types.py` to add new lattice/guest types, then update the UI to display them.

**When:** Adding any GenIce2 lattice or guest that already exists in GenIce2's catalog.

**Example:**
```python
# types.py - Add filled ice lattice
HYDRATE_LATTICES["c0te"] = {
    "genice_name": "c0te",
    "description": "Filled ice C0 (high-pressure, channels)",
    "category": "filled_ice",  # NEW: categorize for UI grouping
    "cages": {
        "channel": {"name": "Channel", "count_per_unit_cell": 2, "guest_fits": ["ne", "he", "h2"]},
    },
    "unit_cell_molecules": 18,
}
```

### Pattern 2: Worker-First Background Computation

**What:** Any new generation/computation pathway must use the QThread-based Worker pattern. Never run GenIce2, pymatgen, or Packmol on the main thread.

**When:** Any new feature that takes >100ms (GenIce2 generation, CIF parsing, Packmol placement).

**Example:**
```python
# Follow HydrateWorker pattern exactly:
class ComplexHydrateWorker(QThread):
    progress_updated = Signal(str)
    generation_complete = Signal(object)
    generation_error = Signal(str)
    
    def __init__(self, config: ComplexHydrateConfig, parent=None):
        super().__init__(parent)
        self._config = config
    
    def run(self):
        try:
            # Import inside run() for thread safety
            from quickice.structure_generation.complex_hydrate_builder import ComplexHydrateBuilder
            builder = ComplexHydrateBuilder()
            result = builder.build(self._config)
            self.generation_complete.emit(result)
        except Exception as e:
            self.generation_error.emit(str(e))
```

### Pattern 3: Lattice Name Mapping (for GenIce2 Integration)

**What:** Map QuickIce's user-friendly lattice names to GenIce2's internal lattice module names via the `_LATTICE_MODULES` dict and `HYDRATE_LATTICES[].genice_name`.

**When:** Adding any new GenIce2 lattice type.

**Example:**
```python
# hydrate_generator.py
_LATTICE_MODULES = {
    "sI": "sI",
    "sII": "sII",
    "sH": "sH",
    "c0te": "c0te",       # NEW
    "c1te": "c1te",       # NEW
    "c2te": "c2te",       # NEW
    "ice1hte": "ice1hte", # NEW
    "sTprime": "sTprime", # NEW
}
```

### Pattern 4: GROMACS Export with Guest ITP Files

**What:** Each new guest molecule requires a bundled `.itp` file in `data/` and a corresponding `_hydrate.itp` variant with appropriate `[ moleculetype ]` naming.

**When:** Adding any new guest molecule type.

**Example:**
```python
# data/co2_hydrate.itp - CO2 topology for hydrate cages
[ moleculetype ]
; name    nrexcl
CO2_H     1

[ atoms ]
; nr  type  resnr  residue  atom  cgnr  charge  mass
  1   C_o   1      CO2_H    C     1     0.65    12.010
  2   O_o   1      CO2_H    O1    1    -0.33    15.999
  3   O_o   1      CO2_H    O2    1    -0.33    15.999

[ bonds ]
  1  2  4  0.1152  123010.0
  1  3  4  0.1152  123010.0
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Subprocess Call to GenIce2 CLI

**What:** Running `genice2 CS1 -g 12=ch4 > output.gro` via `subprocess.run()` instead of using GenIce2's Python API.

**Why bad:** 
- Format conversion overhead (string parsing of GRO output)
- Error handling is fragile (parse stderr)
- No programmatic control over intermediate steps
- Breaks PyInstaller packaging (CLI may not be in PATH)
- Harder to debug

**Instead:** Use GenIce2's Python API directly (as current `hydrate_generator.py` already does):
```python
from genice2.genice import GenIce
from genice2.plugin import safe_import
lattice = safe_import('lattice', lattice_name).Lattice()
ice = GenIce(lattice, reshape=supercell_matrix)
gro_string = ice.generate_ice(formatter, water, guests, depol='strict')
```

### Anti-Pattern 2: Replacing GenIce2 with pymatgen for Ice Structures

**What:** Using pymatgen's `Structure.from_spacegroup()` to build ice/hydrate structures from scratch, bypassing GenIce2.

**Why bad:** pymatgen has no concept of:
- Bernal-Fowler ice rules (each O has 2 H donors, 2 H acceptors)
- Depolarization (net dipole should be near zero for bulk ice)
- Hydrogen bond network construction
- Cage filling with guest molecules

The resulting structure would have **ordered hydrogens**, which is physically unrealistic for most ice/hydrate phases (except Ice XI, Ice XV, etc.).

**Instead:** Always use GenIce2 for any structure containing a water O-network. Use pymatgen only for non-ice crystallographic tasks (CIF validation, format conversion, symmetry analysis).

### Anti-Pattern 3: Modifying GenIce2 Source Code

**What:** Editing files inside `genice2/` package directory to add new features.

**Why bad:**
- GenIce2 is a separate MIT-licensed package; modifications should be upstreamed
- Local modifications break on `pip install --upgrade genice2`
- Violates separation of concerns

**Instead:** Use GenIce2's plugin system (custom lattice modules, custom molecule modules) or create wrappers in QuickIce's codebase.

### Anti-Pattern 4: Adding a New Tab for Each Feature

**What:** Creating a "Filled Ice" tab, a "Semiclathrate" tab, a "CIF Import" tab, etc.

**Why bad:**
- Tab proliferation makes the UI overwhelming
- Each tab duplicates the same generation → render → export pipeline
- The existing Hydrate tab already handles this pattern

**Instead:** Extend the existing Hydrate Generation tab with sub-modes, dropdown categories, and conditional UI sections. Use QStackedWidget or conditional visibility to show relevant controls per lattice type.

## Scalability Considerations

| Concern | At 3 Lattice Types (Current) | At 10 Lattice Types | At 30+ Lattice Types |
|---------|-------------------------------|---------------------|----------------------|
| Dropdown usability | Flat list is fine | Needs categories ("Standard", "Filled Ice", "Exotic") | Needs searchable combo + categories + icons |
| Occupancy controls | 2 sliders (small/large) | 2-3 sliders per type | Dynamic: generate sliders from HYDRATE_LATTICES cages dict |
| Guest molecule ITP | 2 files (ch4, thf) | 5+ files (add CO2, H2, ethane) | Lazy-load from data/ based on selection |
| GenIce2 import time | ~0.5s (3 lattice modules) | ~1s (10 modules) | ~2s (30+ modules) — consider selective imports |
| Renderer complexity | Water + CH4/THF | Water + 5 guest types | Water + arbitrary guests — renderer must handle any atom type |

## Sources

| Source | URL | Confidence |
|--------|-----|------------|
| QuickIce source code (local) | `/share/home/nglokwan/quickice/quickice/` | HIGH |
| GenIce2 CS1 lattice source | `genice2.lattices.CS1` (inspected via Python) | HIGH |
| GenIce2 c0te lattice source | `genice2.lattices.c0te` (inspected via Python) | HIGH |
| GenIce2 Lattice base class | `genice2.lattices.Lattice` (inspected via Python) | HIGH |
| GenIce2 GenIce.__init__ signature | `genice2.genice.GenIce` (inspected via Python) | HIGH |
| GenIce2 generate_ice method | `genice2.genice.GenIce.generate_ice` (inspected via Python) | HIGH |
| GenIce2 available lattice modules | `pkgutil.iter_modules(genice2.lattices.__path__)` | HIGH |
| Stack research (Wave 1) | `.planning/research/future-ml/complex-hydrate-atomsk/STACK.md` | HIGH |
| Features research (Wave 1) | `.planning/research/future-ml/complex-hydrate-atomsk/FEATURES.md` | HIGH |
| genice2-cif NOT installed | `pip list | grep genice2-cif` returns nothing | HIGH |
