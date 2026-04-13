# Feature Landscape: QuickIce v4.0 Molecule Insertion

**Domain:** Molecular dynamics ice structure generation with molecule/ion insertion
**Researched:** 2026-04-14
**Overall confidence:** HIGH (direct codebase analysis + GenIce2 API documentation + domain knowledge)

---

## Executive Summary

QuickIce v4.0 adds molecule insertion capabilities to two new tabs:

- **Tab 2 (Molecules to Ice):** Generates clathrate hydrate structures using GenIce2's built-in hydrate lattice modules, with guest molecule placement in hydrate cages. This is fundamentally different from Tab 1 (pure ice generation) — it uses different lattice types (CS1/sI, CS2/sII, HS3/sH) with cage structures, and places guest molecules inside those cages.

- **Tab 4 (Insert to Liquid):** Adds NaCl ions or custom molecules to the liquid water phase of an existing interface system. Ion insertion replaces water molecules with ions while preserving ice structure integrity. Custom molecule insertion places user-provided .gro/.itp molecules at random or user-specified positions in the liquid phase.

Both features integrate with the existing GROMACS export pipeline (must produce valid .gro/.top/.itp), the 3D VTK viewer (must render distinct molecule types with different visual styles), and the CLI.

Research draws from: GenIce2 source code (genice2 repository), QuickIce v3.5 codebase (interface_builder.py, gromacs_writer.py, vtk_utils.py, types.py), and domain knowledge of clathrate hydrates and MD simulation workflows.

---

## Tab 2: Molecules to Ice — Feature Analysis

### What This Tab Does

Tab 2 generates **clathrate hydrate structures** — ice frameworks with guest molecules trapped inside cage-like cavities. This is NOT the same as Tab 1 (pure ice generation). The hydrate lattices have fundamentally different unit cells and contain pre-defined cage positions where guest molecules are placed.

GenIce2 provides this capability via its `--guest` and `--Guest` CLI flags, and via the Python API through the `GenIce` constructor (`cations`, `anions`, `spot_guests`, `spot_groups` parameters) and `generate_ice()` method (`guests` parameter).

### GenIce2 Hydrate Lattice Types (HIGH confidence — from source code)

| GenIce2 Name | Type | Description | Cages |
|---|---|---|---|
| CS1 / sI / A15 | Structure I | Most common hydrate; methane hydrate | 2×12-pentagonal dodecahedron + 6×tetradecahedron |
| CS2 / sII / XVI | Structure II | Large molecule hydrates (THF) | 16×12-pentagonal dodecahedron + 8×16-hexakaidecahedron |
| HS3 / sH / DOH | Structure H | Requires large help gas | 3×12-pentagonal dodecahedron + 2×12-pentagonal dodecahedron + 1×15-pentakaidecahedron |
| HS1 / sIV | Structure IV | Rare hydrate type | 12-pentagonal dodecahedra + 14-pentakaidecahedra |
| c0te | Filled ice C0 | Teeratchanan (2015) | Guest positions supplied |
| c1te | Filled ice C1 | Teeratchanan (2015) | Guest positions supplied |
| c2te | Filled ice C2 | Teeratchanan (2015) | Guest positions supplied |
| ice1hte | Filled ice Ih | Teeratchanan (2015) | Guest positions supplied |
| sTprime | Filled ice sT' | Smirnov (2013) | Guest positions supplied |

### GenIce2 Built-in Guest Molecules (HIGH confidence — from source code)

| Molecule Name | Type | Description |
|---|---|---|
| me | United-atom | Methane (single Lennard-Jones site) |
| ch4 | All-atom | Methane (5 atoms: C + 4H) |
| et | United-atom | Ethane |
| thf | All-atom | Tetrahydrofuran (13 atoms) |
| uathf | United-atom | THF (5 sites + dummy) |
| uathf6 | United-atom | THF variant |
| H2 | Molecular | Hydrogen molecule |
| co2 | Molecular | Carbon dioxide |
| mol[filename] | Custom | Loader for MOL files from MolView.org |

### Table Stakes — Tab 2

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes | Dependency |
|---|---|---|---|---|
| Hydrate structure selection | Core capability — user must pick sI, sII, sH, etc. | MEDIUM | Dropdown of GenIce2 lattice names | None |
| Built-in guest molecule selection | Primary use case is methane hydrate, THF hydrate | MEDIUM | Dropdown from GenIce2 molecule list | Hydrate structure |
| Cage occupancy control | Scientific users need to specify which cage types get which guests | MEDIUM | GenIce2 `--guest` syntax: `16=uathf -g 12=me*0.6+co2*0.4` | Hydrate structure + guest |
| Unit cell repetition (supercell) | Need realistic system sizes for MD | LOW | Same `--rep` mechanism as Tab 1 | Hydrate structure |
| GROMACS export (.gro/.top/.itp) | Must produce MD-ready files | HIGH | Need new .itp entries for guest molecules | All generation |
| 3D visualization of hydrate | See guest molecules inside cages | MEDIUM | Distinct rendering for guests vs ice | Hydrate structure |
| Water model selection | TIP4P-ICE vs TIP3P etc. | LOW | Already exists in Tab 1 | None |
| Hydrate unit cell info display | Users need to know cage counts and types | LOW | GenIce2 provides this info in logs | Hydrate structure |

### Differentiators — Tab 2

Features that set QuickIce apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---|---|---|---|
| Custom MOL file import | Users can import arbitrary guest molecules from MolView.org | MEDIUM | GenIce2 `mol[filename.mol]` syntax; user provides .mol file |
| Mixed cage occupancy | Multiple guest types in one hydrate | MEDIUM | GenIce2 supports `12=co2*0.6+me*0.4` syntax |
| Specific cage targeting | Place guests in individual cages by ID | HIGH | GenIce2 `--Guest 0=me` syntax; requires showing cage IDs |
| Ion doping in hydrates | Replace water with Na/Cl inside hydrate | MEDIUM | GenIce2 `--anion` and `--cation` flags |
| Semiclathrate support | TBAB-type structures with group placement | HIGH | GenIce2 `--Group` syntax; complex workflow |
| Cage type visualization | Highlight different cage types in 3D viewer | MEDIUM | GenIce2 provides cage positions; can draw polyhedra |
| Hydrate density/occupancy report | Scientific metadata about structure | LOW | Parse GenIce2 output logs |

### Anti-Features — Tab 2

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|---|---|---|
| Custom hydrate lattice creation | Crystallographically wrong structures are useless | Use GenIce2's built-in lattices only |
| Manual cage position specification | Users don't know where cages are | Let GenIce2 determine cage positions from lattice |
| MD simulation launch | Outside QuickIce's scope (generation only) | Export to GROMACS and let users run their own MD |
| Force field parameter generation | Requires expertise beyond scope | User provides .itp files for custom molecules |
| Multiple hydrate phases simultaneously | Physically unrealistic — one phase per system | Generate one hydrate type at a time |
| Real-time 3D preview during generation | GenIce generation takes seconds | Generate button with progress feedback |

---

## Tab 4: Insert to Liquid — Feature Analysis

### What This Tab Does

Tab 4 adds ions or molecules to the **liquid water phase** of an already-generated interface structure (from Tab 3). This is a post-processing operation on an existing `InterfaceStructure`, not a new generation step.

Two distinct sub-features:
1. **NaCl salt**: Insert Na+ and Cl- ions by concentration, replacing water molecules
2. **Custom molecules**: Insert user-provided molecules at random or specified positions in the liquid phase

### Table Stakes — Tab 4

| Feature | Why Expected | Complexity | Notes | Dependency |
|---|---|---|---|---|
| NaCl concentration input (mol/L or g/kg) | Primary use case for seawater/brine simulations | LOW | Convert concentration → number of ion pairs | Interface structure |
| Auto-calculate ion count from concentration | Users specify concentration, not count | MEDIUM | `n_ions = conc × volume × NA`; must use water density | Concentration input |
| Ion placement: replace water, not ice | Physical correctness — ions go in liquid, not crystal | HIGH | Must identify water molecules via `ice_atom_count` boundary | Interface structure |
| Charge neutrality enforcement | MD simulations require neutral systems | LOW | Equal number of cations and anions | Ion count |
| Custom molecule .gro + .itp upload | Standard workflow for adding solutes | MEDIUM | File dialogs, parsing, validation | None |
| Random placement mode | Simplest insertion method | MEDIUM | Random COM positions in liquid region, with overlap check | Custom molecule |
| Overlap detection after insertion | Prevent physically impossible structures | MEDIUM | Reuse cKDTree from overlap_resolver.py | Placement |
| GROMACS export with all molecule types | Must produce valid topology for MD | HIGH | Multi-molecule .top with multiple `[moleculetype]` sections | All insertion |
| 3D visualization with distinct styles | Users must see ions vs water vs ice | MEDIUM | 5 actor types in VTK viewer | VTK viewer |

### Differentiators — Tab 4

| Feature | Value Proposition | Complexity | Notes |
|---|---|---|---|
| Custom COM + rotation placement | Precise control for specific insertion sites | MEDIUM | User specifies (x, y, z) and rotation matrix or Euler angles |
| Multiple custom molecule types | Mix NaCl + organic solutes | HIGH | Each molecule type needs its own .gro/.itp pair |
| TIP4P-ICE ion parameters bundled | Users don't need to find/create .itp files | LOW | Bundled Na+ and Cl- .itp with Jorgensen parameters |
| Concentration unit conversion | Scientific users think in mol/L; practical users in g/kg | LOW | `mol/L ↔ g/kg` for NaCl |
| Water molecule replacement visualization | Show which water molecules get replaced | LOW | Highlight replaced waters before deletion |
| Energy minimization suggestion | Post-insertion structures need minimization | LOW | Warning message suggesting `gmx minimize` |

### Anti-Features — Tab 4

| Anti-Feature | Why Avoid | What to Do Instead |
|---|---|---|
| MD minimization in QuickIce | Outside scope (generation only) | Suggest users run `gmx minimize` |
| Multiple salt types (KCl, MgCl₂) | Requires different .itp parameters per salt | Start with NaCl only; add more in future versions |
| Custom ion force field parameters | Requires deep MD expertise | User provides .itp files for custom ions |
| Solvation free energy calculation | Research-grade simulation, not generation | Not in scope |
| Automatic water box equilibration | Requires running MD | Let users do this in GROMACS |
| pH/ionic strength calculation | Too complex for MVP | Just use NaCl concentration |

---

## 3D Viewer Enhancements — Feature Analysis

### Current State (v3.5)

The VTK viewer currently distinguishes two phases:
- **Ice**: Lines (cyan) — `vtk_utils.interface_to_vtk_molecules()` creates `ice_mol`
- **Water**: Lines (cornflower blue) — creates `water_mol`

### Target State (v4.0)

Five distinct molecule types with individual display controls:

| Type | Default Style | Default Color | VTK Implementation | Complexity |
|---|---|---|---|---|
| Ice (water) | Lines | Cyan (0, 0.8, 0.8) | Existing `ice_mol` actor | LOW (existing) |
| Liquid (water) | Lines | Cornflower blue (0.4, 0.6, 0.9) | Existing `water_mol` actor | LOW (existing) |
| Ions (Na+, Cl-) | VDW spheres | Na+: yellow (1.0, 1.0, 0.0), Cl-: green (0.0, 1.0, 0.0) | New `ion_actor` — `vtkSphereSource` per ion | MEDIUM |
| Small molecules | Ball-and-stick | Orange (1.0, 0.5, 0.0) | New `small_mol_actor` — VTK molecule with VDW + bonds | MEDIUM |
| Large molecules | Stick | Magenta (0.8, 0.0, 0.8) | New `large_mol_actor` — VTK molecule with stick mode | MEDIUM |

### Table Stakes — 3D Viewer

| Feature | Why Expected | Complexity | Notes |
|---|---|---|---|
| Distinct rendering per molecule type | Users must visually distinguish components | MEDIUM | 5 actor types in VTK pipeline |
| Toggle visibility per molecule type | Common request for complex systems | LOW | Checkbox per type in viewer panel |
| Style selection dropdown per type | Users want control over representation | MEDIUM | QComboBox per type |
| Color picker per type | Customization | LOW | QColorDialog per type |

### Differentiators — 3D Viewer

| Feature | Value Proposition | Complexity | Notes |
|---|---|---|---|
| Atom-type-based coloring | Standard in MD viewers (OVITO, VMD) | HIGH | Element-based coloring (O=red, H=white, C=gray, Na=purple, Cl=green) |
| Unit cell overlay for hydrates | Essential for understanding cage structure | LOW | Reuse existing `create_unit_cell_actor()` |
| Cage boundary visualization | See hydrate cages in 3D | HIGH | Draw polyhedra from GenIce2 cage positions |

### Anti-Features — 3D Viewer

| Anti-Feature | Why Avoid | What to Do Instead |
|---|---|---|
| Real-time MD animation | Outside scope (generation only) | Generate initial structures, let users animate externally |
| Ray tracing / POV-Ray export | Nice to have but not essential | Standard VTK rendering is sufficient |
| Custom force field visualization | Research tool, not generation tool | Standard atom/bond rendering |
| Surface rendering | Adds complexity without clear value for ice structures | Stick/VDW/ball-and-stick sufficient |

---

## GROMACS Export Enhancements — Feature Analysis

### Current State (v3.5)

- Single `[moleculetype]` section: SOL (TIP4P-ICE)
- All water molecules (ice + liquid) grouped as SOL
- Bundled `tip4p-ice.itp` force field file

### Target State (v4.0)

- Multiple `[moleculetype]` sections in .top file
- Separate molecule groups: SOL (water), ION (ions), GUEST (guest molecules)
- User-provided .itp files bundled or referenced
- Guest molecule atoms included in .gro output
- Molecule type ordering: SOL, ions, solutes (per v4_context.md)

### Table Stakes — GROMACS Export

| Feature | Why Expected | Complexity | Notes |
|---|---|---|---|
| Multi-molecule .top file | Must produce valid GROMACS topology | MEDIUM | `[moleculetype]` per molecule type |
| Bundled ion .itp (Na+, Cl-) | Users shouldn't have to create these | LOW | Standard TIP4P-ICE compatible parameters |
| User .itp file inclusion | Custom molecules need their topology | MEDIUM | Copy to output dir or reference by path |
| Correct `[molecules]` section | GROMACS needs molecule counts | LOW | SOL count, ION count, GUEST count |
| Guest atom positions in .gro | Must include all atoms in coordinate file | MEDIUM | Extend existing .gro writer |

### Differentiators — GROMACS Export

| Feature | Value Proposition | Complexity | Notes |
|---|---|---|---|
| .itp generation for simple guests | Methane, CO₂ — users shouldn't need external files | MEDIUM | Pre-bundled .itp for GenIce2 built-in molecules |
| Automatic charge validation | Ensure system neutrality | LOW | Sum of charges = 0 check |
| Molecule type grouping by residue name | Standard GROMACS convention | LOW | Group by resname in .gro output |

### Anti-Features — GROMACS Export

| Anti-Feature | Why Avoid | What to Do Instead |
|---|---|---|
| MD run file generation (mdp files) | Outside scope (generation only) | Provide .gro/.top/.itp only |
| Force field parameter generation | Requires deep expertise | User provides .itp for custom molecules |
| Topology merging/conflict resolution | Too complex for MVP | Warn users about conflicts |

---

## Feature Dependencies

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Tab 2: Molecules to Ice                              │
│                                                                          │
│  Hydrate Structure Selection ──► Guest Molecule Selection               │
│         │                                │                                │
│         │                                ▼                                │
│         │                        Cage Occupancy Config                   │
│         │                                │                                │
│         ▼                                ▼                                │
│  GenIce2 API Call ──► Parse GRO Output ──► Candidate Object             │
│                                              │                            │
│                                              ▼                            │
│                                    3D Visualization                       │
│                                    GROMACS Export                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                     Tab 4: Insert to Liquid                              │
│                                                                          │
│  Interface Structure (from Tab 3) ──► Identify Liquid Phase              │
│                                              │                            │
│                    ┌─────────────────────────┤                            │
│                    ▼                         ▼                            │
│              NaCl Insertion         Custom Molecule Insertion             │
│                    │                         │                            │
│                    ▼                         ▼                            │
│          Concentration → Count     .gro/.itp Upload                       │
│                    │                         │                            │
│                    ▼                         ▼                            │
│          Replace Water Molecules   Random/Custom Placement                │
│                    │                         │                            │
│                    └─────────┬───────────────┘                            │
│                              ▼                                            │
│                     Overlap Detection                                     │
│                              │                                            │
│                              ▼                                            │
│                    Modified Interface Structure                           │
│                              │                                            │
│                              ▼                                            │
│                    3D Visualization + GROMACS Export                      │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                     Cross-Tab Dependencies                               │
│                                                                          │
│  Tab 2 ──► NOT dependent on Tab 1 (different generation path)            │
│  Tab 2 ──► NOT dependent on Tab 3 (standalone hydrate generation)        │
│  Tab 4 ──► DEPENDENT on Tab 3 (needs existing interface structure)       │
│  Tab 4 ──► Uses overlap_resolver.py from Tab 3                          │
│  Tab 2 ──► Shares GROMACS export with Tabs 1, 3                         │
│  Tab 4 ──► Shares GROMACS export with Tabs 1, 3                         │
│  3D Viewer ──► Enhanced by both Tab 2 and Tab 4 molecule types          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Critical Dependency Notes

1. **Tab 2 is independent of Tab 1**: Hydrate generation uses different GenIce2 lattice types (CS1, CS2, etc.) instead of pure ice types (ice1h, ice1c, etc.). The generation pipeline is separate.

2. **Tab 4 depends on Tab 3**: Ion/molecule insertion requires an existing `InterfaceStructure` with an `ice_atom_count` boundary. Cannot insert into liquid without knowing which atoms are liquid.

3. **GenIce2 API path for hydrates**: The `GenIce` class constructor accepts `cations`, `anions`, `spot_guests`, `spot_groups`. The `generate_ice()` method accepts `guests` dict. This is different from the current QuickIce `IceStructureGenerator` which only uses `lattice`, `density`, `reshape`, `water`, and `depol`.

4. **GRO parsing needs enhancement**: Current `_parse_gro()` in `generator.py` assumes all atoms are water (O, H, H pattern). Hydrate GRO output includes guest molecule atoms with different residue names and atom names. The parser must handle multi-molecule GRO files.

5. **Topology (.top) generation needs multi-molecule support**: Current `write_interface_top_file()` writes a single `[moleculetype]` for SOL. With ions and guests, it needs multiple `[moleculetype]` sections and `[molecules]` entries.

---

## MVP Recommendation

For v4.0 MVP, prioritize in this order:

### Phase 1 (Must Have — Tab 4 Foundation)

1. **NaCl ion insertion to liquid phase** — Most requested feature, builds on existing interface infrastructure
2. **Ion visualization in 3D viewer** — VDW spheres for Na+/Cl-, distinct from water
3. **Multi-molecule GROMACS export** — .top with SOL + ION sections, bundled Na+/Cl- .itp

### Phase 2 (Must Have — Tab 2 Foundation)

4. **Hydrate structure generation** — GenIce2 API call for CS1, CS2, HS3 with guest molecules
5. **Built-in guest molecule selection** — me, thf, co2, H2, ch4 from dropdown
6. **Hydrate 3D visualization** — Ice + guest molecules with distinct styles
7. **Hydrate GROMACS export** — .gro/.top with SOL + GUEST sections

### Phase 3 (Should Have — Enhanced)

8. **Custom molecule .gro/.itp upload** — File dialogs for user-provided molecules
9. **Custom molecule placement modes** — Random and user-specified COM
10. **Cage occupancy control** — Partial/mixed occupancy UI for hydrate guests
11. **Display style controls** — Per-type style dropdowns and color pickers

### Post-v4.0 (Consider Later)

- Semiclathrate hydrate support (TBAB-type)
- Cage visualization in 3D viewer (polyhedra)
- Multiple salt types (KCl, MgCl₂)
- Ion doping in hydrate structures (Tab 2)
- Custom MOL file import from MolView.org
- Concentration unit conversion helper (mol/L ↔ g/kg)

---

## Complexity Assessment

| Feature | Complexity | Risk | Dependency |
|---|---|---|---|
| NaCl ion insertion | MEDIUM | MEDIUM | Tab 3 interface, overlap_resolver.py |
| Ion count from concentration | LOW | LOW | Water density (already available) |
| Hydrate structure generation | MEDIUM-HIGH | MEDIUM | GenIce2 API changes, new data types |
| Built-in guest molecules | MEDIUM | LOW | GenIce2 molecule plugins |
| Custom molecule upload | MEDIUM | MEDIUM | .gro/.itp parsing and validation |
| Custom placement (COM/rotation) | MEDIUM | LOW | Coordinate math |
| Multi-molecule .top export | MEDIUM | LOW | Extend existing writer |
| Multi-molecule .gro export | MEDIUM | MEDIUM | Extend existing writer |
| VTK per-type rendering | MEDIUM | LOW | Multiple actors, style mapping |
| Visibility toggles per type | LOW | LOW | QCheckBox per actor |
| Style/color selection per type | MEDIUM | LOW | QComboBox + QColorDialog per type |
| Cage occupancy UI | HIGH | MEDIUM | Complex UI for GenIce2 cage syntax |
| GRO parser for hydrates | MEDIUM-HIGH | HIGH | Multi-molecule GRO, different atom patterns |

---

## Sources

- **GenIce2 Repository** (HIGH confidence): https://github.com/genice-dev/GenIce2 — API, lattice modules, molecule plugins, format modules
- **GenIce2 CLI Help** (HIGH confidence): Full `--help` output with all lattice types, molecule types, cage syntax
- **QuickIce v3.5 Codebase** (HIGH confidence): `generator.py`, `interface_builder.py`, `gromacs_writer.py`, `vtk_utils.py`, `types.py`
- **v4 Context Document** (HIGH confidence): `.planning/v4-context.md` — Tab 2/4 feature definitions
- **GenIce2 GROMACS Format** (HIGH confidence): `genice2/formats/gromacs.py` — GRO output format for multi-molecule systems
- **GenIce2 Molecule Base Class** (HIGH confidence): `genice2/molecules/__init__.py` — Molecule class, arrange(), monatom(), serialize()
- **GenIce2 Lattice Modules** (HIGH confidence): `CS1.py`, `CS2.py` — Hydrate structures with cage positions
- **GenIce2 Core** (HIGH confidence): `genice2/genice.py` — GenIce class, guest placement, ion doping, group handling

---

*Research for: QuickIce v4.0 Molecule Insertion milestone*
*Generated: 2026-04-14*