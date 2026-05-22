# GROMACS Export Flow Trace

**Analysis Date:** 2026-05-22
**Codebase Version:** v4.5 (Phase 34.3)
**Scope:** Read-only trace of every function call before a successful GROMACS export

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Data Structures](#2-data-structures)
3. [Ctrl+S Unified Export Dispatch](#3-ctrls-unified-export-dispatch)
4. [Export Path 1: Ice Tab → GROMACS Export](#4-export-path-1-ice-tab--gromacs-export)
5. [Export Path 2: Hydrate Tab → GROMACS Export](#5-export-path-2-hydrate-tab--gromacs-export)
6. [Export Path 3: Interface Tab → GROMACS Export](#6-export-path-3-interface-tab--gromacs-export)
7. [Export Path 4: Custom Molecule Tab → GROMACS Export](#7-export-path-4-custom-molecule-tab--gromacs-export)
8. [Export Path 5: Solute Tab → GROMACS Export](#8-export-path-5-solute-tab--gromacs-export)
9. [Export Path 6: Ion Tab → GROMACS Export](#9-export-path-6-ion-tab--gromacs-export)
10. [Export Path 7: Full Chain (Interface → Custom → Solute → Ion)](#10-export-path-7-full-chain)
11. [MoleculetypeRegistry Tracking](#11-moleculetype-registry-tracking)
12. [ITP File Selection Logic](#12-itp-file-selection-logic)
13. [GROMACS File Assembly Details](#13-gromacs-file-assembly-details)
14. [Molecule Ordering Rules](#14-molecule-ordering-rules)
15. [Decision Points](#15-decision-points)
16. [Failure Points and Error Handling](#16-failure-points-and-error-handling)
17. [Cross-Tab Dependency Map](#17-cross-tab-dependency-map)
18. [Bundled ITP File Inventory](#18-bundled-itp-file-inventory)

---

## 1. Architecture Overview

### Key Files by Role

| Role | File | Purpose |
|------|------|---------|
| Main Window | `quickice/gui/main_window.py` | Tab dispatch, Ctrl+S routing, export slot handlers |
| Tab Constants | `quickice/gui/constants.py` | `TabIndex` enum mapping tab index → tab name |
| Ice Exporter | `quickice/gui/export.py:GROMACSExporter` | Ice-only .gro/.top/.itp generation |
| Hydrate Exporter | `quickice/gui/hydrate_export.py:HydrateGROMACSExporter` | Hydrate .gro/.top + guest .itp |
| Interface Exporter | `quickice/gui/export.py:InterfaceGROMACSExporter` | Interface ice+water+guests .gro/.top |
| Solute Exporter | `quickice/gui/export.py:SoluteGROMACSExporter` | Ice+water+solutes .gro/.top |
| Custom Exporter | `quickice/gui/export.py:CustomMoleculeGROMACSExporter` | Ice+water+custom .gro/.top |
| Ion Exporter | `quickice/gui/export.py:IonGROMACSExporter` | Full system .gro/.top/.itp |
| GROMACS Writer | `quickice/output/gromacs_writer.py` | All .gro/.top file format writers (2054 lines) |
| Ion ITP Writer | `quickice/structure_generation/gromacs_ion_export.py` | Generates ion.itp with NA/CL moleculetypes |
| Registry | `quickice/structure_generation/moleculetype_registry.py` | Unique moleculetype naming (_H/_L/_custom) |
| Types | `quickice/structure_generation/types.py` | All dataclass definitions |
| Interface Builder | `quickice/structure_generation/interface_builder.py` | Orchestrates interface generation |
| Hydrate Generator | `quickice/structure_generation/hydrate_generator.py` | GenIce2 hydrate generation |
| Solute Inserter | `quickice/structure_generation/solute_inserter.py` | CH4/THF liquid-phase placement |
| Custom Inserter | `quickice/structure_generation/custom_molecule_inserter.py` | User .gro/.itp molecule placement |
| Ion Inserter | `quickice/structure_generation/ion_inserter.py` | Na+/Cl- water-replacement insertion |
| ITP Parser | `quickice/structure_generation/itp_parser.py` | Parses .itp files for atom names/types |
| GRO Parser | `quickice/structure_generation/gro_parser.py` | Parses .gro files for custom molecules |
| Data Directory | `quickice/data/` | Bundled ITP/GRO topology files |

---

## 2. Data Structures

### 2.1 Candidate (Ice-only)

```
Candidate                          # quickice/structure_generation/types.py:95
├── positions: np.ndarray (N,3)   # nm, from GenIce2
├── atom_names: list[str]         # ["O","H","H","O","H","H",...]
├── cell: np.ndarray (3,3)        # nm, ROW vectors
├── nmolecules: int                # water molecules count
├── phase_id: str                  # "ice_ih", "ice_ii", etc.
├── seed: int
└── metadata: dict
```

### 2.2 InterfaceStructure (Ice + Water + Guests)

```
InterfaceStructure                 # quickice/structure_generation/types.py:219
├── positions: np.ndarray (N,3)   # ALL atoms: ice → water → guests
├── atom_names: list[str]         # ALL atom names (same order)
├── cell: np.ndarray (3,3)
├── ice_atom_count: int           # marks boundary: positions[0:ice_atom_count] = ice
├── water_atom_count: int         # positions[ice_atom_count:ice_atom_count+water_atom_count] = water
├── ice_nmolecules: int
├── water_nmolecules: int
├── mode: str                     # "slab", "pocket", "piece"
├── report: str
├── guest_atom_count: int = 0     # positions[ice+water:] = guests
├── molecule_index: list[MoleculeIndex]
└── guest_nmolecules: int = 0
```

### 2.3 HydrateStructure (Water Framework + Guests)

```
HydrateStructure                   # quickice/structure_generation/types.py:628
├── positions: np.ndarray (N,3)   # water framework + guests
├── atom_names: list[str]
├── cell: np.ndarray (3,3)
├── molecule_index: list[MoleculeIndex]  # water + guest entries
├── config: HydrateConfig
├── lattice_info: HydrateLatticeInfo
├── report: str
├── guest_count: int
└── water_count: int
```

### 2.4 CustomMoleculeStructure (Ice + Water + Custom)

```
CustomMoleculeStructure            # quickice/structure_generation/types.py:520
├── positions: np.ndarray (N,3)   # COMPLETE system: ice + water + custom
├── atom_names: list[str]         # ALL atom names
├── cell: np.ndarray (3,3)
├── molecule_index: list[MoleculeIndex]  # ice, water, guest, custom
├── ice_atom_count: int
├── water_atom_count: int
├── custom_molecule_atom_count: int
├── guest_atom_count: int = 0
├── config: CustomMoleculeConfig | None
├── moleculetype_name: str        # from MoleculetypeRegistry
├── gro_path: Path | None         # user's .gro file
├── itp_path: Path | None        # user's .itp file
├── residue_name: str
├── custom_molecule_count: int
└── interface_structure: InterfaceStructure  # original before custom insertion
```

### 2.5 SoluteStructure (Solute Positions + Interface Reference)

```
SoluteStructure                    # quickice/structure_generation/types.py:424
├── positions: np.ndarray (N,3)   # SOLUTE ATOMS ONLY (not full system!)
├── atom_names: list[str]         # solute atom names only
├── cell: np.ndarray (3,3)
├── solute_type: str              # "CH4" or "THF"
├── n_molecules: int
├── molecule_indices: list[tuple] # (start, end) in solute positions array
├── registry: MoleculetypeRegistry
├── interface_structure: InterfaceStructure  # ice + water (after water removal)
├── custom_molecule_count: int = 0          # propagated from custom tab
├── custom_molecule_atom_count: int = 0
├── custom_molecule_positions: np.ndarray | None
├── custom_molecule_atom_names: list | None
├── custom_molecule_moleculetype: str
├── custom_gro_path: Path | None
└── custom_itp_path: Path | None
```

### 2.6 IonStructure (Full System After Ion Insertion)

```
IonStructure                       # quickice/structure_generation/types.py:341
├── positions: np.ndarray (N,3)   # ice + water + guests (no solutes/custom)
├── atom_names: list[str]
├── cell: np.ndarray (3,3)
├── molecule_index: list[MoleculeIndex]  # ice, water, guest, na, cl
├── na_count: int
├── cl_count: int
├── report: str
├── guest_nmolecules: int = 0
├── guest_atom_count: int = 0
├── solute_type: str = ""                  # propagated from solute tab
├── solute_positions: np.ndarray | None
├── solute_atom_names: list | None
├── solute_n_molecules: int = 0
├── solute_molecule_indices: list | None
├── solute_registry: MoleculetypeRegistry | None
├── custom_molecule_count: int = 0         # propagated from custom tab
├── custom_molecule_atom_count: int = 0
├── custom_molecule_positions: np.ndarray | None
├── custom_molecule_atom_names: list | None
├── custom_molecule_moleculetype: str
├── custom_gro_path: Path | None
└── custom_itp_path: Path | None
```

### 2.7 MoleculeIndex (Tracks Each Molecule in Positions Array)

```
MoleculeIndex                      # quickice/structure_generation/types.py:22
├── start_idx: int                # 0-based index in positions array
├── count: int                     # number of atoms in this molecule
└── mol_type: str                  # "ice", "water", "guest", "ch4", "thf", "na", "cl", "custom"
```

---

## 3. Ctrl+S Unified Export Dispatch

### Entry Point

**File:** `quickice/gui/main_window.py`
**Method:** `MainWindow._on_export_current_tab()` (line 1557)
**Trigger:** Ctrl+S keyboard shortcut → `export_current_action.triggered`

### Dispatch Logic

```
Step 1: User presses Ctrl+S
    → File menu "Export Current Tab for GROMACS..." action triggered
    → Calls MainWindow._on_export_current_tab()

Step 2: Get current tab index
    → current_idx = self.tab_widget.currentIndex()

Step 3: Route based on TabIndex enum (quickice/gui/constants.py:9)
    IF current_idx == TabIndex.ICE (0):
        → self._on_export_gromacs()
    ELIF current_idx == TabIndex.HYDRATE (1):
        → self._on_export_hydrate_gromacs()
    ELIF current_idx == TabIndex.INTERFACE (2):
        → self._on_export_interface_gromacs()
    ELIF current_idx == TabIndex.CUSTOM (3):
        → self._on_export_custom_molecule_gromacs()
    ELIF current_idx == TabIndex.SOLUTE (4):
        → self._on_export_solute_gromacs()
    ELIF current_idx == TabIndex.ION (5):
        → self._on_export_ion_gromacs()
    ELSE:
        → QMessageBox.warning "Unknown Tab"
```

### Alternative Export Triggers

| Shortcut | Menu Path | Handler |
|----------|-----------|---------|
| Ctrl+G | File → Export As → Export Ice | `_on_export_gromacs()` |
| Ctrl+H | File → Export As → Export Hydrate | `_on_export_hydrate_gromacs()` |
| Ctrl+I | File → Export As → Export Interface | `_on_export_interface_gromacs()` |
| Ctrl+L | File → Export As → Export Solute | `_on_export_solute_gromacs()` |
| Ctrl+M | File → Export As → Export Custom Molecule | `_on_export_custom_molecule_gromacs()` |
| Ctrl+J | File → Export As → Export Ion | `_on_export_ion_gromacs()` |

---

## 4. Export Path 1: Ice Tab → GROMACS Export

### Prerequisite: Ice Structure Must Be Generated

```
Step 1: User clicks "Generate" on Ice tab
    → MainViewModel.start_generation(T, P, nmolecules)
    → GenIce2 generates Candidate objects
    → self._current_result = GenerationResult with ranked_candidates

Step 2: User selects a ranked candidate in the viewer
    → selected_idx = self.viewer_panel.get_selected_candidate_index_left()
```

### Export Flow (Numbered Steps)

```
Step 1:  _on_export_gromacs()                                # main_window.py:1593
         ├── Check: self._current_result exists and has ranked_candidates
         ├── Check: ranked_candidates list is not empty
         ├── Get selected_idx from viewer (fallback to 0)
         ├── Extract: ranked = self._current_result.ranked_candidates[selected_idx]
         ├── Get T from input_panel, P from input_panel
         └── Call: self._gromacs_exporter.export_gromacs(ranked, T, P)

Step 2:  GROMACSExporter.export_gromacs(ranked_candidate, T, P)  # export.py:664
         ├── Generate default filename: "{phase_id}_{T}K_{P}MPa_c{rank}.gro"
         ├── Extract: candidate = ranked_candidate.candidate  (type: Candidate)
         ├── QFileDialog.getSaveFileName() → user picks .gro path
         ├── Ensure .gro extension
         ├── Derive companion filenames:
         │   ├── top_path = path.with_name(path.stem + '.top')
         │   └── itp_path = path.with_name(path.stem + '.itp')
         └── TRY:

Step 3:     write_gro_file(candidate, str(path))             # gromacs_writer.py:426
            ├── Compute: nmol = candidate.nmolecules
            ├── Compute: n_atoms = nmol * 4  (TIP4P-ICE: 4 atoms/mol)
            ├── Validate: len(positions) >= nmol*3
            ├── Wrap: wrapped = wrap_positions_into_box(positions, cell)
            ├── FOR mol_idx in range(nmol):
            │   ├── Get O, H1, H2 positions (3 atoms/mol input)
            │   ├── Compute MW = O + α*(H1-O) + α*(H2-O)    (α=0.13458335)
            │   └── Write 4 lines: OW, HW1, HW2, MW (res=SOL)
            └── Write box vectors (triclinic format)

Step 4:     write_top_file(candidate, str(top_path))         # gromacs_writer.py:512
            ├── [defaults]: nbfunc=1, comb-rule=2, gen-pairs=yes, fudgeLJ=0.5, fudgeQQ=0.8333
            ├── [atomtypes]: OW_ice, HW_ice, MW (inline, NOT from .itp)
            ├── [moleculetype]: SOL nrexcl=2
            ├── [atoms]: OW_ice, HW_ice, HW_ice, MW (inline definition)
            ├── [settles], [virtual_sites3], [exclusions]
            ├── [system]: phase_id
            └── [molecules]: SOL {nmol}

Step 5:     Copy tip4p-ice.itp to output directory           # export.py:721
            ├── get_tip4p_itp_path() → quickice/data/tip4p-ice.itp
            └── shutil.copy(itp_source, itp_path)
```

### Files Produced
- `{phase}_{T}K_{P}MPa_c{rank}.gro` — GROMACS coordinates
- `{phase}_{T}K_{P}MPa_c{rank}.top` — GROMACS topology (includes inline SOL definition)
- `{phase}_{T}K_{P}MPa_c{rank}.itp` — copy of tip4p-ice.itp

### Key Notes
- Ice structures store 3 atoms/molecule (O, H, H); MW is computed at export time
- The .top file has an INLINE [moleculetype] SOL definition AND copies tip4p-ice.itp — this is redundant but harmless
- Ice-only export does NOT use MoleculetypeRegistry

---

## 5. Export Path 2: Hydrate Tab → GROMACS Export

### Prerequisite: Hydrate Structure Must Be Generated

```
Step 1: User configures and generates hydrate on Hydrate tab
    → HydrateStructureGenerator.generate(config)           # hydrate_generator.py:74
    → Uses GenIce2 Python API to generate water framework + guests
    → Builds molecule_index with MoleculeIndex entries
    → self._current_hydrate_result = HydrateStructure
    → self._current_hydrate_config = HydrateConfig
```

### Export Flow

```
Step 1:  _on_export_hydrate_gromacs()                        # main_window.py:1661
         ├── Check: self._current_hydrate_result exists
         ├── Check: self._current_hydrate_config exists
         ├── Extract: structure = self._current_hydrate_result (type: HydrateStructure)
         └── Call: self._hydrate_gromacs_exporter.export_hydrate(structure, config)

Step 2:  HydrateGROMACSExporter.export_hydrate(structure, config)  # hydrate_export.py:90
         ├── Generate default filename: "hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro"
         ├── QFileDialog.getSaveFileName() → user picks .gro path
         ├── Ensure .gro extension
         ├── top_path = path.with_name(path.stem + '.top')
         └── TRY:

Step 3:     Import writer functions
            ├── from gromacs_writer import write_multi_molecule_gro_file
            ├── from gromacs_writer import write_multi_molecule_top_file
            ├── from gromacs_writer import get_tip4p_itp_path
            ├── tip4p_itp_path = get_tip4p_itp_path()   → quickice/data/tip4p-ice.itp
            └── guest_itp_path = _get_hydrate_guest_itp_path(config.guest_type)

Step 4:     Create MoleculetypeRegistry                     # hydrate_export.py:146
            ├── registry = MoleculetypeRegistry()
            └── registry.register_hydrate_guest(guest_type.upper())
                → Returns "CH4_H" or "THF_H"

Step 5:     write_multi_molecule_gro_file(...)              # gromacs_writer.py:1046
            ├── structure.positions, structure.molecule_index, structure.cell
            ├── FOR mol in molecule_index:
            │   ├── Get res_name from get_guest_residue_name() or MOLECULE_TO_GROMACS
            │   ├── IF mol_type in ["ch4","thf"]: reorder_guest_atoms()
            │   └── Write atom lines with proper residue names
            └── Write box vectors

Step 6:     write_multi_molecule_top_file(...)               # gromacs_writer.py:1143
            ├── Build itp_files mapping: {guest_type: guest_itp_path.name}
            ├── [defaults]: same as ice
            ├── [atomtypes]: OW_ice, HW_ice, MW + guest atom types
            │   ├── IF "ch4" in types: write c3, hc atomtypes
            │   └── IF "thf" in types: write os, c5, hc, h1 atomtypes
            ├── #include directives:
            │   ├── #include "tip4p-ice.itp"
            │   └── #include "{guest_type}_hydrate.itp"
            ├── [system]
            └── [molecules]: counts from registry
                ├── water → SOL (count from molecule_index)
                └── ch4/thf → CH4_H or THF_H (from registry)

Step 7:     Copy ITP files to output directory
            ├── shutil.copy(tip4p_itp_path, "tip4p-ice.itp")
            └── shutil.copy(guest_itp_path, "{guest}_hydrate.itp")
```

### ITP Path Resolution

```
_get_hydrate_guest_itp_path(guest_type)                     # hydrate_export.py:44
├── Try: quickice/data/{guest_type}_hydrate.itp             # e.g., ch4_hydrate.itp
├── Fallback: {__file__}/../../data/{guest_type}_hydrate.itp
└── FileNotFoundError if not found
```

### Files Produced
- `hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro`
- `hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.top`
- `tip4p-ice.itp` (copied)
- `ch4_hydrate.itp` or `thf_hydrate.itp` (copied)

### Key Notes
- Hydrate guests use `_H` suffix (CH4_H, THF_H) — molecules inside hydrate cages
- Hydrate water framework is labeled mol_type="water" in molecule_index
- GenIce2 outputs atoms in a different order than .itp expects → `reorder_guest_atoms()` is called

---

## 6. Export Path 3: Interface Tab → GROMACS Export

### Prerequisite: Interface Structure Must Be Generated

```
Step 1: User generates interface on Interface tab
    → generate_interface(candidate, config)               # interface_builder.py:310
    ├── validate_interface_config(config, candidate)       # validates box dims, mode params
    ├── Route to mode:
    │   ├── "slab" → assemble_slab(candidate, config)    # modes/slab.py
    │   ├── "pocket" → assemble_pocket(candidate, config) # modes/pocket.py
    │   └── "piece" → assemble_piece(candidate, config)   # modes/piece.py
    └── Returns InterfaceStructure
    → self._current_interface_result = InterfaceStructure
```

### Export Flow

```
Step 1:  _on_export_interface_gromacs()                      # main_window.py:1635
         ├── Check: self._current_interface_result exists
         ├── Extract: iface = self._current_interface_result
         └── Call: self._interface_gromacs_exporter.export_interface_gromacs(iface)

Step 2:  InterfaceGROMACSExporter.export_interface_gromacs(iface)  # export.py:804
         ├── Generate default filename: "interface_{mode}.gro"
         ├── QFileDialog.getSaveFileName() → user picks .gro path
         ├── top_path = path.with_name(path.stem + '.top')
         └── TRY:

Step 3:     write_interface_gro_file(iface, str(path))      # gromacs_writer.py:606
            ├── Compute total atoms:
            │   ├── ice_output_atoms = ice_nmolecules * 4  (MW added)
            │   ├── water_output_atoms = water_nmolecules * 4
            │   └── guest_output_atoms = guest_atom_count
            ├── Wrap positions: wrap_molecules_into_box(iface.positions, iface.molecule_index, iface.cell)
            │   (molecule_index available → use molecule-aware wrapping)
            ├── Detect ice molecule format:
            │   ├── has_ow_in_ice = "OW" in ice_region_atom_names
            │   └── atoms_per_ice_mol = 4 if has_ow else 3
            ├── ICE MOLECULES loop:
            │   ├── IF 3-atom ice: O,H,H → compute MW → write OW,HW1,HW2,MW (res=SOL)
            │   └── IF 4-atom ice (hydrate): OW,HW1,HW2,MW → use positions directly
            ├── WATER MOLECULES loop (4 atoms each, pass through)
            │   └── OW, HW1, HW2, MW (res=SOL)
            └── GUEST MOLECULES loop (if guest_atom_count > 0):
                ├── Detect: guest_type = detect_guest_type_from_atoms(guest_atom_names)
                │   ├── THF: has O AND carbon atoms → "thf"
                │   ├── CH4: has C AND H, no O → "ch4"
                │   ├── H2: only H → "h2"
                │   └── CO2: has C AND O, no H → "co2"
                ├── Get residue name: get_hydrate_guest_residue_name(guest_type)
                │   → "CH4_H", "THF_H", etc.
                ├── Reorder atoms if needed: reorder_guest_atoms(mol_atom_names, guest_type)
                └── Write atoms with guest residue name

Step 4:     write_interface_top_file(iface, str(top_path))  # gromacs_writer.py:938
            ├── [defaults]: same format
            ├── [atomtypes]: OW_ice, HW_ice, MW
            │   └── IF guests present: add guest atom types
            │       ├── ch4 → c3, hc
            │       ├── thf → os, c5, hc, h1
            │       ├── co2 → c_2, o_2
            │       └── h2 → hn
            ├── #include directives:
            │   ├── #include "tip4p-ice.itp"
            │   └── IF guest_nmolecules > 0: #include "{guest_type}_hydrate.itp"
            ├── [system]: "Ice/water interface ({mode})"
            └── [molecules]:
                ├── SOL  {ice_nmolecules + water_nmolecules}  (COMBINED count!)
                └── IF guests: {guest_res_name}  {guest_nmolecules}

Step 5:     Copy ITP files
            ├── shutil.copy(tip4p_itp_path, "tip4p-ice.itp")
            └── IF guests present:
                ├── guest_itp_source = _get_hydrate_guest_itp_path(guest_type)
                └── shutil.copy(guest_itp_source, "{guest_type}_hydrate.itp")
```

### Files Produced
- `interface_{mode}.gro`
- `interface_{mode}.top`
- `tip4p-ice.itp` (copied)
- `ch4_hydrate.itp` or `thf_hydrate.itp` (copied, if guests present)

### Key Notes
- Both ice and water are labeled "SOL" in the .gro file
- The [molecules] section writes a COMBINED SOL count (ice+water together)
- Guest molecules come from hydrate cages → use `_hydrate.itp` files (not `_liquid.itp`)
- Guest residue names use `_H` suffix: CH4_H, THF_H
- Ice molecules are 3-atom (O,H,H) that get expanded to 4-atom (OW,HW1,HW2,MW) at export time
- Hydrate-sourced ice is already 4-atom and passes through unchanged

---

## 7. Export Path 4: Custom Molecule Tab → GROMACS Export

### Prerequisite: Custom Molecules Must Be Placed

```
Step 1: User loads .gro/.itp file pair on Custom Molecule tab
    → CustomMoleculeInserter(config)                       # custom_molecule_inserter.py:46
    → Parses .gro file for template positions/atom_names
    → User selects placement mode (random or custom positions)
    → place_random() or place_custom() on InterfaceStructure
    → Returns CustomMoleculeStructure
    → self._current_custom_molecule_result = CustomMoleculeStructure
```

### Export Flow

```
Step 1:  _on_export_custom_molecule_gromacs()               # main_window.py (via Ctrl+M or Ctrl+S)
         ├── Check: self._current_custom_molecule_result exists
         ├── Extract: custom_structure = self._current_custom_molecule_result
         └── Call: self._custom_molecule_gromacs_exporter.export_custom_molecule_gromacs(custom_structure)

Step 2:  CustomMoleculeGROMACSExporter.export_custom_molecule_gromacs(custom_structure)  # export.py:163
         ├── Generate default filename: "custom_system_{moleculetype_name}_{n_molecules}molecules.gro"
         ├── QFileDialog.getSaveFileName() → user picks .gro path
         ├── top_path = path.with_name(path.stem + '.top')
         └── TRY:

Step 3:     write_custom_molecule_gro_file(custom_structure, str(path))  # gromacs_writer.py:1841
            ├── Build ordered_mols:
            │   ├── Pass 1: SOL (ice + water) from molecule_index
            │   ├── Pass 2: Guest molecules (if guest_atom_count > 0)
            │   └── Pass 3: Custom molecules from molecule_index
            ├── Count total atoms (ice: 4 atoms, water: 4 atoms, others: mol.count)
            ├── Wrap: wrap_molecules_into_box(positions, molecule_index, cell)
            └── Write atom lines:
                ├── SOL molecules → res_name="SOL"
                ├── Guest molecules → res_name="GUE" (generic, NO guest detection!)
                └── Custom molecules → res_name=moleculetype_name[:5]

Step 4:     write_custom_molecule_top_file(custom_structure, str(top_path))  # gromacs_writer.py:1979
            ├── [defaults]: same
            ├── [atomtypes]: OW_ice, HW_ice, MW
            │   └── Parse custom ITP: parse_itp_atomtypes(custom_structure.itp_path)
            │       → Add atom types from user's .itp file
            ├── #include directives:
            │   ├── #include "tip4p-ice.itp"
            │   ├── IF guest_count > 0: #include "guest.itp" (GENERIC, not hydrate-specific!)
            │   └── #include "{custom_itp_path.name}" (user's .itp file)
            ├── [system]
            └── [molecules]:
                ├── SOL  {sol_count}
                ├── IF guests: GUE  {guest_count}  (generic "GUE" name)
                └── {moleculetype_name}  {custom_count}

Step 5:     Copy custom .itp with atomtypes commented out
            ├── Read itp_content = custom_structure.itp_path.read_text()
            ├── modified_content = comment_out_atomtypes_in_itp(itp_content)
            │   → Comments out [ atomtypes ] section to avoid duplication with .top
            └── custom_itp_dest.write_text(modified_content)
```

### Files Produced
- `custom_system_{name}_{n}molecules.gro`
- `custom_system_{name}_{n}molecules.top`
- `tip4p-ice.itp` (copied, implicit from #include — **BUG: NOT actually copied!**)
- `{custom_molecule}.itp` (copied with atomtypes commented out)

### ⚠️ FAILURE POINT: Missing tip4p-ice.itp
The `CustomMoleculeGROMACSExporter` does NOT copy `tip4p-ice.itp` to the output directory, but the .top file includes `#include "tip4p-ice.itp"`. This means GROMACS will fail with "File not found" unless the user manually provides this file. Compare with all other exporters which DO copy it.

### ⚠️ FAILURE POINT: Generic "GUE" residue name
When guest molecules are present (from a hydrate-sourced interface), the custom molecule writer uses "GUE" as the residue name instead of detecting the actual guest type. The .top also uses `#include "guest.itp"` which doesn't exist as a bundled file.

---

## 8. Export Path 5: Solute Tab → GROMACS Export

### Prerequisite: Solutes Must Be Inserted

```
Step 1: User inserts solutes on Solute tab
    → SoluteInserter.insert_solutes(structure, config)    # solute_inserter.py:610
    ├── Calculate n_molecules from concentration and liquid volume
    ├── Load solute template from bundled ITP
    │   ├── CH4: _generate_ch4_coordinates() → 5-atom template
    │   └── THF: _generate_thf_coordinates() → 13-atom template
    ├── Place molecules with overlap checking (cKDTree)
    ├── Remove overlapping water molecules
    ├── Register with MoleculetypeRegistry: register_liquid_solute(solute_type)
    │   → "CH4_L" or "THF_L"
    └── Returns SoluteStructure
    → self._current_solute_result = SoluteStructure
```

### Export Flow

```
Step 1:  _on_export_solute_gromacs()                         # main_window.py:1729
         ├── Check: self._current_solute_result exists
         ├── Extract: solute_structure = self._current_solute_result
         └── Call: self._solute_gromacs_exporter.export_solute_gromacs(solute_structure)

Step 2:  SoluteGROMACSExporter.export_solute_gromacs(solute_structure)  # export.py:36
         ├── Generate default filename: "solute_{type}_{n}molecules.gro"
         ├── QFileDialog.getSaveFileName() → user picks .gro path
         ├── top_path = path.with_name(path.stem + '.top')
         └── TRY:

Step 3:     Combine interface + solute atoms                # export.py:71-79
            ├── interface = solute_structure.interface_structure
            ├── all_positions = np.vstack([interface.positions, solute_structure.positions])
            └── all_atom_names = interface.atom_names + solute_structure.atom_names

Step 4:     write_gro_file(all_positions, all_atom_names, solute_structure.cell, str(path))
            ⚠️ NOTE: This uses write_gro_file() with (positions, atom_names, cell)
            NOT write_interface_gro_file() with InterfaceStructure.
            This means NO MW computation for ice — it just dumps atom names as-is.
            ⚠️ POTENTIAL BUG: If ice molecules are 3-atom (O,H,H), they won't get MW added.

Step 5:     Build molecule_index manually                   # export.py:88-121
            ├── Add ice molecules: mol_type='ICE_IH'
            ├── Add water molecules: mol_type='WATER_LIQ'
            └── Add solute molecules from solute_structure.molecule_indices

Step 6:     write_top_file(all_positions, all_atom_names, cell, top_path, molecule_index, registry)
            ⚠️ NOTE: This calls write_top_file() (ice-only version, line 512)
            NOT write_interface_top_file(). This version only writes SOL.
            ⚠️ POTENTIAL BUG: Topology won't include guest/solute moleculetypes.

Step 7:     Copy tip4p-ice.itp to output directory
            └── shutil.copy(itp_source, "tip4p-ice.itp")

Step 8:     Copy solute .itp file (liquid solutes use _liquid.itp)
            ├── solute_itp_name = f"{solute_type_lower}_liquid.itp"
            ├── solute_itp_source = Path(__file__).parent.parent / "data" / solute_itp_name
            └── IF exists: shutil.copy(solute_itp_source, solute_itp_dest)
```

### ⚠️ MAJOR CONCERN: Solute Export Uses Wrong Writer Functions
The `SoluteGROMACSExporter` calls `write_gro_file(positions, atom_names, cell, path)` — the simple writer that just dumps atoms. It does NOT call `write_interface_gro_file()` which properly handles:
- MW virtual site computation for 3-atom ice
- Guest molecule detection and residue naming
- Proper molecule ordering

Similarly, `write_top_file(candidate, top_path)` is the ice-only version that only creates a SOL moleculetype. It does NOT create entries for solutes or guests.

This appears to be a significant implementation gap. The solute export was written before the multi-molecule writer infrastructure was complete.

### Files Produced
- `solute_{type}_{n}molecules.gro`
- `solute_{type}_{n}molecules.top`
- `tip4p-ice.itp` (copied)
- `ch4_liquid.itp` or `thf_liquid.itp` (copied, if exists)

---

## 9. Export Path 6: Ion Tab → GROMACS Export

### Prerequisite: Ions Must Be Inserted

```
Step 1: User inserts ions on Ion tab
    → IonInserter.replace_water_with_ions(structure, ion_pairs)  # ion_inserter.py:171
    ├── Build molecule_index from interface structure metadata
    ├── Select water molecules to replace (random selection)
    ├── Replace alternating Na+/Cl- (charge neutrality)
    ├── Overlap checking against ice + guest molecules (cKDTree)
    ├── Ensure na_count == cl_count (remove excess)
    ├── Propagate solute info from input structure (if solute tab was used)
    ├── Propagate custom molecule info (if custom tab was used)
    └── Returns IonStructure
    → self._current_ion_result = IonStructure
```

### Export Flow

```
Step 1:  _on_export_ion_gromacs()                            # main_window.py:1697
         ├── Check: self._current_ion_result exists
         ├── Extract: ion_structure = self._current_ion_result
         └── Call: self._ion_gromacs_exporter.export_ion_gromacs(ion_structure)

Step 2:  IonGROMACSExporter.export_ion_gromacs(ion_structure)  # export.py:242
         ├── Generate default filename (with solute info if present)
         ├── QFileDialog.getSaveFileName() → user picks .gro path
         ├── top_path = path.with_name(path.stem + '.top')
         └── TRY:

Step 3:     write_ion_gro_file(ion_structure, str(path))    # gromacs_writer.py:1299
            ├── Build ordered_mols (6 passes):
            │   ├── Pass 1: SOL (ice + water) from molecule_index
            │   ├── Pass 2: guest molecules from molecule_index
            │   ├── Pass 3: custom molecules (if custom_molecule_count > 0)
            │   │   ├── atoms_per_custom = custom_molecule_atom_count // custom_molecule_count
            │   │   └── Create pseudo-entries for each custom molecule
            │   ├── Pass 4: solute molecules (if solute_n_molecules > 0)
            │   │   └── Create pseudo-entries from solute_molecule_indices
            │   ├── Pass 5: NA ions from molecule_index
            │   └── Pass 6: CL ions from molecule_index
            ├── Count total atoms
            ├── Wrap: wrap_molecules_into_box(ion_structure.positions, ion_structure.molecule_index, ion_structure.cell)
            └── Write atom lines for each molecule type:
                ├── SOL (ice): 3→4 atoms (compute MW)
                ├── SOL (water): 4 atoms (pass through, compute MW)
                ├── Guest: detect type → get hydrate residue name → reorder → write
                ├── Custom: use custom_molecule_positions and custom_molecule_atom_names
                ├── Solute: use solute_positions and solute_atom_names
                ├── NA: 1 atom, res_name="NA"
                └── CL: 1 atom, res_name="CL"

Step 4:     write_ion_top_file(ion_structure, str(top_path))  # gromacs_writer.py:1624
            ├── Count molecules by type:
            │   ├── sol_count = ice + water molecules
            │   ├── guest_count = guest molecules
            │   ├── na_count, cl_count
            │   ├── has_custom, custom_count
            │   └── has_solutes, solute_count
            ├── Detect guest type: detect_guest_type_from_atoms()
            ├── [defaults]: nbfunc=1, comb-rule=2, gen-pairs=yes, fudgeLJ=0.0, fudgeQQ=0.0
            │   ⚠️ NOTE: Different fudgeLJ/fudgeQQ than ice-only (0.5/0.8333 vs 0.0/0.0)
            ├── [atomtypes]: OW_ice, HW_ice, MW
            │   ├── IF ions: NA, CL (Madrid2019 parameters)
            │   ├── IF guests (ch4): c3, hc
            │   ├── IF guests (thf): os, c5, hc, h1
            │   ├── IF solutes: parse_itp_atomtypes() from {solute}_liquid.itp
            │   └── IF custom: parse_itp_atomtypes() from custom_itp_path
            ├── #include directives:
            │   ├── #include "tip4p-ice.itp"
            │   ├── IF guests: #include "{guest_type}_hydrate.itp"
            │   ├── IF custom: #include "{custom_itp_name}"
            │   ├── IF solutes: #include "{solute}_liquid.itp"
            │   └── #include "ion.itp"
            ├── [system]: descriptive name with all components
            └── [molecules] (ORDER: SOL, guest, custom, solute, NA, CL):
                ├── SOL  {sol_count}
                ├── {guest_res_name}  {guest_count}  (e.g., CH4_H)
                ├── {custom_mol_name}  {custom_count}
                ├── {solute_mol_name}  {solute_count}  (from registry, e.g., CH4_L)
                ├── NA  {na_count}
                └── CL  {cl_count}

Step 5:     write_ion_itp(ion_itp_path, na_count, cl_count)  # gromacs_ion_export.py:80
            ├── Generate ion.itp content
            │   ├── [moleculetype] NA nrexcl=1
            │   │   └── [atoms]: NA type=NA, charge=+0.85, mass=22.9898
            │   └── [moleculetype] CL nrexcl=1
            │       └── [atoms]: CL type=CL, charge=-0.85, mass=35.453
            └── Write to ion.itp

Step 6:     Copy tip4p-ice.itp
            └── shutil.copy(itp_source, "tip4p-ice.itp")

Step 7:     Copy guest .itp (if guests present)
            ├── Detect guest type from molecule_index (mol_type="guest")
            │   ├── Try detect_guest_type_from_atoms() for each guest molecule
            │   └── Fallback: atoms_per_guest >= 10 → "thf", else → "ch4"
            ├── guest_itp_source = _get_hydrate_guest_itp_path(guest_type)
            ├── guest_itp_dest = path.with_name("{guest_type}_hydrate.itp")
            └── shutil.copy(guest_itp_source, guest_itp_dest)
            ⚠️ SILENT FAILURE: If FileNotFoundError, pass without warning

Step 8:     Copy solute .itp (if solutes present)
            ├── solute_itp_name = f"{solute_type_lower}_liquid.itp"
            ├── solute_itp_source = Path(__file__).parent.parent / "data" / solute_itp_name
            ├── IF exists:
            │   ├── Read content
            │   ├── comment_out_atomtypes_in_itp(content) → comment [atomtypes] section
            │   └── Write modified content
            └── IF not exists: silently skip

Step 9:     Copy custom .itp (if custom molecules present)
            ├── custom_itp_source = Path(ion_structure.custom_itp_path)
            ├── IF exists:
            │   ├── Read content
            │   ├── comment_out_atomtypes_in_itp(content) → comment [atomtypes] section
            │   └── Write modified content
            └── IF not exists: silently skip
```

### Files Produced
- `ions_{na}na_{cl}cl.gro` (or with solute info)
- `ions_{na}na_{cl}cl.top`
- `ion.itp` (generated)
- `tip4p-ice.itp` (copied)
- `ch4_hydrate.itp` or `thf_hydrate.itp` (copied, if guests present)
- `ch4_liquid.itp` or `thf_liquid.itp` (copied with atomtypes commented, if solutes present)
- `{custom_molecule}.itp` (copied with atomtypes commented, if custom present)

---

## 10. Export Path 7: Full Chain (Interface → Custom → Solute → Ion)

This is the most complex export path where ALL tabs contribute to the final system.

### Generation Chain

```
Step 1: Interface Tab — Generate interface
    → InterfaceStructure (ice + water + guests)
    → self._current_interface_result = InterfaceStructure

Step 2: Custom Molecule Tab — Place custom molecules
    → Input: self._current_interface_result (InterfaceStructure)
    → CustomMoleculeInserter.place_random(structure, n_molecules)
    │   ├── Remove overlapping water molecules
    │   ├── Build complete molecule_index: ice, water, guest, custom
    │   └── Return CustomMoleculeStructure
    → self._current_custom_molecule_result = CustomMoleculeStructure

Step 3: Solute Tab — Insert solutes
    → Input: CustomMoleculeStructure (treated as InterfaceStructure)
    → SoluteInserter.insert_solutes(structure, config)
    │   ├── Place solute molecules in liquid region
    │   ├── Remove overlapping water molecules
    │   ├── Preserve custom molecule attributes (propagated through)
    │   └── Return SoluteStructure
    → self._current_solute_result = SoluteStructure

Step 4: Ion Tab — Insert ions
    → Input: SoluteStructure (treated as InterfaceStructure)
    → IonInserter.replace_water_with_ions(structure, ion_pairs)
    │   ├── Replace water molecules with Na+/Cl-
    │   ├── Preserve guest, solute, custom molecule attributes
    │   └── Return IonStructure
    → self._current_ion_result = IonStructure
```

### Data Propagation Through Chain

```
InterfaceStructure
    │
    ▼ CustomMoleculeInserter
CustomMoleculeStructure
    ├── moleculetype_name: "MOL" (or "MOL_1" on collision)
    ├── gro_path: user's .gro
    ├── itp_path: user's .itp
    ├── interface_structure: original InterfaceStructure
    │
    ▼ SoluteInserter (takes modified_structure from CustomMoleculeStructure)
SoluteStructure
    ├── solute_type: "CH4" or "THF"
    ├── registry: MoleculetypeRegistry (CH4_L or THF_L registered)
    ├── interface_structure: InterfaceStructure (after water removal for custom+solute)
    ├── custom_molecule_count: propagated
    ├── custom_molecule_positions: propagated
    ├── custom_molecule_atom_names: propagated
    ├── custom_molecule_moleculetype: propagated
    ├── custom_gro_path: propagated
    ├── custom_itp_path: propagated
    │
    ▼ IonInserter (takes SoluteStructure or interface_structure from it)
IonStructure
    ├── molecule_index: ice, water, guest, na, cl
    ├── na_count, cl_count
    ├── guest_nmolecules, guest_atom_count: propagated
    ├── solute_type, solute_positions, solute_atom_names: propagated
    ├── solute_n_molecules, solute_molecule_indices: propagated
    ├── solute_registry: propagated
    ├── custom_molecule_count, custom_molecule_positions: propagated
    ├── custom_molecule_atom_names, custom_molecule_moleculetype: propagated
    ├── custom_gro_path, custom_itp_path: propagated
```

### Ion Export for Full Chain

The IonGROMACSExporter handles ALL components in one export:

```
.GRO file ordering (write_ion_gro_file):
    1. SOL (ice + water) — ice expanded from 3→4 atoms
    2. Guest molecules (hydrate guests with _H suffix residues)
    3. Custom molecules (from custom_molecule_positions, not main positions array)
    4. Solute molecules (from solute_positions, not main positions array)
    5. NA ions (1 atom each)
    6. CL ions (1 atom each)

.TOP file ordering (write_ion_top_file [molecules] section):
    1. SOL  {ice+water count}
    2. CH4_H  {guest count}          (hydrate guests)
    3. {custom_moltype}  {custom count}
    4. CH4_L  {solute count}         (liquid solutes)
    5. NA  {na_count}
    6. CL  {cl_count}

.ITP files bundled:
    1. tip4p-ice.itp     (water topology)
    2. ch4_hydrate.itp   (or thf_hydrate.itp — guest topology)
    3. ion.itp            (generated — NA+CL parameters)
    4. ch4_liquid.itp    (or thf_liquid.itp — solute topology, atomtypes commented)
    5. {custom}.itp       (user's custom topology, atomtypes commented)
```

---

## 11. MoleculetypeRegistry Tracking

**File:** `quickice/structure_generation/moleculetype_registry.py`

### Purpose
Ensures unique GROMACS moleculetype names so that molecules of the same chemical species but from different sources get distinct topology entries.

### Registration Methods

| Method | Key Format | Output Name | When Used |
|--------|-----------|-------------|-----------|
| `register_hydrate_guest(mol)` | `hydrate_{MOL}` | `{MOL}_H` | Hydrate cage guests |
| `register_liquid_solute(mol)` | `liquid_{MOL}` | `{MOL}_L` | Liquid-phase solutes |
| `register_custom_molecule(name)` | `custom_{N}` | `{name}` or `{name}_{N}` | User molecules |

### Key Behaviors

- `_H` suffix: Hydrate guests (CH4 in hydrate cages → `CH4_H`)
- `_L` suffix: Liquid solutes (CH4 dissolved in water → `CH4_L`)
- Reserved names: `SOL`, `NA`, `CL`, `CH4`, `THF`, `CO2`, `H2`, `CH4_H`, `CH4_L`, `THF_H`, `THF_L`
- Custom molecule collision: If name already used → increment counter (`MOL`, `MOL_1`, `MOL_2`)

### Where Registry Is Used

| Export Path | Registry Created | What's Registered |
|-------------|-----------------|-------------------|
| Ice | Not used | — |
| Hydrate | `MoleculetypeRegistry()` in `export_hydrate()` | `hydrate_{GUEST}` → `{GUEST}_H` |
| Interface | Not used (uses hardcoded `get_hydrate_guest_residue_name()`) | — |
| Custom | `MoleculetypeRegistry()` in `CustomMoleculeInserter.__init__()` | `custom_{N}` → `{name}` |
| Solute | `MoleculetypeRegistry()` in `SoluteInserter.__init__()` | `liquid_{TYPE}` → `{TYPE}_L` |
| Ion | Uses `solute_registry` from IonStructure (propagated from Solute tab) | — |

---

## 12. ITP File Selection Logic

### Decision Tree: Which ITP File To Use

```
Is this molecule a GUEST from a hydrate structure (cage-encaged)?
├── YES → Use {type}_hydrate.itp
│   ├── ch4_hydrate.itp → moleculetype "CH4_H", residue "CH4_H"
│   └── thf_hydrate.itp → moleculetype "THF_H", residue "THF_H"
│
└── NO → Is this molecule a SOLUTE in the liquid phase?
    ├── YES → Use {type}_liquid.itp
    │   ├── ch4_liquid.itp → moleculetype "CH4_L", residue "CH4_L"
    │   └── thf_liquid.itp → moleculetype "THF_L", residue "THF_L"
    │
    └── NO → Is this a CUSTOM user molecule?
        ├── YES → Use user's .itp file
        │   ├── moleculetype from ITP [moleculetype] section
        │   ├── [atomtypes] commented out via comment_out_atomtypes_in_itp()
        │   └── Residue name from ITP [atoms] section
        │
        └── NO → Is this water/SOL?
            ├── YES → Use tip4p-ice.itp (moleculetype "SOL")
            └── NO → Is this an ion?
                ├── YES → Use ion.itp (generated at export time)
                │   ├── moleculetype "NA" (charge +0.85)
                │   └── moleculetype "CL" (charge -0.85)
                └── NO → Unknown → CRITICAL FAILURE
```

### ITP Naming Convention

| Suffix | Meaning | File | moleculetype | Residue |
|--------|---------|------|-------------|---------|
| (none) | Standalone/bulk | `ch4.itp`, `thf.itp` | `CH4`, `THF` | `CH4`, `THF` |
| `_hydrate` | Inside hydrate cage | `ch4_hydrate.itp`, `thf_hydrate.itp` | `CH4_H`, `THF_H` | `CH4_H`, `THF_H` |
| `_liquid` | Dissolved in liquid water | `ch4_liquid.itp`, `thf_liquid.itp` | `CH4_L`, `THF_L` | `CH4_L`, `THF_L` |

### Why Separate ITP Files?
The same chemical molecule (e.g., CH4) has DIFFERENT partial charges depending on its environment:
- CH4 in hydrate cage: charges from QM optimization in cage → `CH4_H`
- CH4 in liquid water: charges from QM optimization in bulk → `CH4_L`

This distinction is critical for GROMACS to correctly model the different electrostatic environments.

---

## 13. GROMACS File Assembly Details

### 13.1 .gro File Assembly

**Format:** GROMACS coordinate file

```
Line 1: Title string (e.g., "Ice/water interface (slab) exported by QuickIce")
Line 2: Total atom count (5 digits max, wraps at 100000)
Lines 3..N+2: Atom lines
    Format: {resnum:5d}{resname:<5s}{atomname:>5s}{atomnum:5d}{x:8.3f}{y:8.3f}{z:8.3f}
Line N+3: Box vectors (triclinic: 9 values, orthorhombic: 3 values)
```

**Atom Output by Molecule Type:**

| Molecule | Input Atoms | Output Atoms | Expansion |
|----------|------------|-------------|-----------|
| Ice (classic) | 3 (O, H, H) | 4 (OW, HW1, HW2, MW) | MW computed: O + α(H1-O) + α(H2-O) |
| Ice (hydrate) | 4 (OW, HW1, HW2, MW) | 4 (pass through) | None |
| Water | 4 (OW, HW1, HW2, MW) | 4 (pass through) | None |
| CH4 guest | 5 (C, H×4) | 5 (reordered: C first) | reorder_guest_atoms() |
| THF guest | 13 (O, CA×2, CB×2, H×8) | 13 | reorder_guest_atoms() |
| Custom | N | N | No expansion |
| Solute (CH4) | 5 | 5 | No reordering in ion export |
| Solute (THF) | 13 | 13 | No reordering in ion export |
| NA | 1 | 1 | — |
| CL | 1 | 1 | — |

### 13.2 .top File Assembly

**Structure (mandatory order in GROMACS):**

```
[ defaults ]                    # Force field defaults
[ atomtypes ]                   # All atom type definitions (MUST be before #include)
#include "tip4p-ice.itp"        # Water moleculetype definition
#include "{guest}_hydrate.itp"  # Guest moleculetype (if hydrate guests)
#include "{solute}_liquid.itp" # Solute moleculetype (if liquid solutes)
#include "{custom}.itp"        # Custom moleculetype (if custom molecules)
#include "ion.itp"              # Ion moleculetypes (if ions)
[ system ]                      # System name
[ molecules ]                   # Molecule counts in .gro file order
```

**Critical rule:** `[molecules]` section order MUST match the order of molecules in the `.gro` file. GROMACS reads atoms sequentially and groups them according to `[molecules]`.

### 13.3 .itp File Bundling

Each `.itp` file is either:
1. **Copied as-is** from `quickice/data/` (water and guest ITPs)
2. **Copied with modification** — `[atomtypes]` section commented out (solute and custom ITPs)
3. **Generated at export time** — `ion.itp` (contains NA + CL moleculetypes)

---

## 14. Molecule Ordering Rules

### GROMACS Requirement
The `[molecules]` section in `.top` and the atom sequence in `.gro` must agree. GROMACS processes atoms sequentially according to `[molecules]` directives.

### Ordering by Export Path

| Export Path | .gro Order | [molecules] Order |
|-------------|-----------|-------------------|
| Ice | SOL (ice) | SOL |
| Hydrate | water → guests | SOL → CH4_H/THF_H |
| Interface | ice SOL → water SOL → guests | SOL (combined) → CH4_H/THF_H |
| Custom | SOL → guests → custom | SOL → GUE → {custom} |
| Solute | SOL → solutes | SOL (combined) ⚠️ incomplete |
| Ion | SOL → guests → custom → solutes → NA → CL | SOL → guest → custom → solute → NA → CL |

### Universal Ordering Rule

```
SOL (ice + water combined) → hydrate guests → custom molecules → liquid solutes → NA → CL
```

- All SOL molecules are contiguous (ice comes first, then water)
- Guest molecules use `_H` residue suffix (from hydrate cages)
- Custom molecules use user-provided moleculetype name
- Liquid solutes use `_L` residue suffix (dissolved in water)
- Ions come last (NA before CL)

---

## 15. Decision Points

### 15.1: Is Ice 3-atom or 4-atom?

**Location:** `write_interface_gro_file()` line 682-684, `write_ion_gro_file()` line 1422

```
ice_region_atom_names = iface.atom_names[:ice_end]
has_ow_in_ice = "OW" in ice_region_atom_names
atoms_per_ice_mol = 4 if has_ow_in_ice else 3

IF atoms_per_ice_mol == 3:
    → Classic ice: expand O,H,H → OW,HW1,HW2,MW at export time
ELSE:
    → Hydrate ice: OW,HW1,HW2,MW already present, pass through
```

### 15.2: What Guest Type Is Present?

**Location:** `detect_guest_type_from_atoms()` in `gromacs_writer.py:885`

```
Analyze atom composition of first guest molecule:
├── Has O AND carbon atoms (CA, CB, C, c3, c5) → "thf"
├── Has C AND H, no O → "ch4"
├── Only H atoms → "h2"
├── Has C AND O, no H → "co2"
├── Only "Me" atom → "ch4" (united-atom methane)
└── Cannot determine → None (fallback to "UNK" or "GUE")
```

### 15.3: Which ITP File for This Guest/Solute?

```
Source = hydrate cage → use {type}_hydrate.itp  (residue {TYPE}_H)
Source = liquid phase → use {type}_liquid.itp  (residue {TYPE}_L)

Detection in export code:
├── Interface tab guests → always from hydrate cages → _hydrate.itp
├── Ion tab guests → always from hydrate cages → _hydrate.itp
├── Solute tab solutes → always in liquid phase → _liquid.itp
└── Hydrate tab guests → in hydrate cages → _hydrate.itp
```

### 15.4: Should [atomtypes] Be Commented in ITP?

```
IF itp_source is from quickice/data/ (bundled ITPs):
    → NO: ch4_hydrate.itp, thf_hydrate.itp already have [atomtypes] commented
    → NO: tip4p-ice.itp already has [atomtypes] commented

IF itp_source is user-provided custom molecule .itp:
    → YES: comment_out_atomtypes_in_itp() removes [atomtypes] to avoid
           duplication with [atomtypes] in main .top file

IF itp_source is solute _liquid.itp:
    → YES: comment_out_atomtypes_in_itp() removes [atomtypes]
    → Atomtypes are parsed and added to main .top instead
```

### 15.5: Custom Molecule Registry Collision

```
IF user_name NOT in existing_names:
    → First use: register as user_name (e.g., "MOL")
ELIF user_name already in existing_names:
    → Collision: increment counter (e.g., "MOL_1", "MOL_2")
```

---

## 16. Failure Points and Error Handling

### 16.1: Missing ITP File

**Risk:** HIGH — GROMACS will fail with fatal error

**Where it can happen:**
- Guest .itp not found: `_get_hydrate_guest_itp_path()` raises `FileNotFoundError`
  - In `InterfaceGROMACSExporter`: caught, logged as pass (line 879)
  - In `IonGROMACSExporter`: caught, silently passed (line 332-335)
- Solute .itp not found: `solute_itp_source.exists()` check → silently skipped
- Custom .itp not found: `Path(custom_itp_path).exists()` check → silently skipped
- `tip4p-ice.itp` not found: would crash (no fallback check in some paths)

**Impact:** Exported files are incomplete. GROMACS `grompp` will fail with "File not found".

### 16.2: Atom Count Mismatch

**Risk:** HIGH — GROMACS validates atom counts between .gro and .top

**Where it can happen:**
- Ice molecules: 3 input atoms → 4 output atoms (MW added). If writer uses wrong atom count, mismatch occurs.
- Solute export (`SoluteGROMACSExporter`): uses `write_gro_file(positions, names, cell)` which writes atoms as-is. If ice is 3-atom, no MW is computed but `.top` expects 4-atom SOL.
- Custom molecule export: if molecule_index `count` field doesn't match actual atoms in .gro section.

### 16.3: Residue Name Mismatch

**Risk:** HIGH — GROMACS validates residue names between .gro and .itp

**Where it can happen:**
- Hydrate guest in .gro has residue "CH4_H" but .itp moleculetype is "CH4" (wrong ITP file)
- Custom molecule residue name in .gro doesn't match [moleculetype] name in .itp
- Solute in .gro has residue "CH4_L" but .top [molecules] says "CH4"

### 16.4: Guest Atom Reordering Failure

**Risk:** MEDIUM — Atoms in wrong order cause force field parameter mismatch

**Where it can happen:**
- `reorder_guest_atoms()` may fail if atom names don't match canonical list
- CH4: GenIce2 outputs H,H,H,H,C but ITP expects C,H,H,H,H
- THF: GenIce2 outputs varying order but ITP expects O,CA,CA,CB,CB,H×8

### 16.5: Solute Export Writer Bug

**Risk:** CRITICAL — Solute export produces broken GROMACS files

**Location:** `SoluteGROMACSExporter.export_solute_gromacs()` (export.py:36)

**Issues:**
1. Uses `write_gro_file(positions, atom_names, cell, path)` — simple writer that does NOT compute MW for ice
2. Uses `write_top_file(candidate, top_path)` — ice-only writer that only creates SOL moleculetype
3. Does NOT create entries for solute moleculetypes in .top
4. Does NOT copy `tip4p-ice.itp` correctly (uses wrong writer signature)

### 16.6: Custom Molecule Export Missing tip4p-ice.itp

**Risk:** HIGH — GROMACS will fail

**Location:** `CustomMoleculeGROMACSExporter.export_custom_molecule_gromacs()` (export.py:163)

**Issue:** Does NOT copy `tip4p-ice.itp` to output directory, but .top includes `#include "tip4p-ice.itp"`.

### 16.7: Custom Molecule Export Generic Guest Handling

**Risk:** MEDIUM — GROMACS will fail if guest molecules present

**Location:** `write_custom_molecule_gro_file()` and `write_custom_molecule_top_file()`

**Issue:**
- Guest residue name hardcoded as "GUE" instead of detecting actual guest type
- .top includes `#include "guest.itp"` which doesn't exist as a bundled file
- Should use `detect_guest_type_from_atoms()` and appropriate `_{type}_hydrate.itp`

### 16.8: Charge Neutrality in Ion Export

**Risk:** LOW — Handled by `IonInserter`

**Where:** `ion_inserter.py:417-439`

**Handling:** After ion placement, excess NA or CL ions are removed until `na_count == cl_count`. This ensures charge neutrality (with NaCl charge of ±0.85 each).

### 16.9: fudgeLJ/fudgeQQ Inconsistency

**Risk:** LOW — Different [defaults] sections in different export paths

**Where:**
- Ice export: fudgeLJ=0.5, fudgeQQ=0.8333
- Ion export: fudgeLJ=0.0, fudgeQQ=0.0

**Impact:** May affect energy calculation accuracy but won't cause GROMACS failure.

---

## 17. Cross-Tab Dependency Map

### Data Flow Between Tabs

```
┌─────────────┐    Candidate    ┌──────────────┐    InterfaceStructure
│  Ice Tab    │ ──────────────→ │ Interface Tab │ ──────────────────┐
│ (TabIndex 0)│                 │ (TabIndex 2)  │                   │
└─────────────┘                 └──────────────┘                   │
                                                                       │
┌─────────────┐    Candidate    ┌──────────────┐                   │
│ Hydrate Tab │ ──────────────→ │ Interface Tab │                   │
│ (TabIndex 1)│  (via to_     │               │                   │
└─────────────┘   candidate()) └──────────────┘                   │
                                    │                              │
                                    │ InterfaceStructure            │
                                    ▼                              │
                              ┌──────────────┐                    │
                              │Custom Mol Tab│ ◄──────────────────┘
                              │ (TabIndex 3) │   InterfaceStructure as input
                              └──────┬───────┘
                                     │ CustomMoleculeStructure
                                     ▼
                              ┌──────────────┐
                              │ Solute Tab   │ ◄── InterfaceStructure or CustomMoleculeStructure
                              │ (TabIndex 4) │    (treated as InterfaceStructure)
                              └──────┬───────┘
                                     │ SoluteStructure
                                     ▼
                              ┌──────────────┐
                              │  Ion Tab     │ ◄── InterfaceStructure or SoluteStructure
                              │ (TabIndex 5) │    or CustomMoleculeStructure
                              └──────┬───────┘
                                     │ IonStructure
                                     ▼
                              ┌──────────────┐
                              │GROMACS Export│  (Ctrl+S from Ion tab)
                              │ .gro/.top/   │
                              │ .itp files   │
                              └──────────────┘
```

### Attribute Propagation Through Chain

| Attribute | Origin | Propagated Via | Present In |
|-----------|--------|---------------|-----------|
| `positions` (ice+water) | Interface | Direct reference | All subsequent structures |
| `molecule_index` | Interface/Custom | Rebuilt in each step | All |
| `guest_nmolecules` | Interface (from hydrate source) | `getattr()` propagation | SoluteStructure, IonStructure |
| `guest_atom_count` | Interface | `getattr()` propagation | SoluteStructure, IonStructure |
| `custom_molecule_count` | Custom tab | Explicit field propagation | SoluteStructure, IonStructure |
| `custom_molecule_positions` | Custom tab | Explicit field propagation | SoluteStructure, IonStructure |
| `custom_molecule_atom_names` | Custom tab | Explicit field propagation | SoluteStructure, IonStructure |
| `custom_molecule_moleculetype` | Custom tab | Explicit field propagation | SoluteStructure, IonStructure |
| `custom_gro_path` | Custom tab | Explicit field propagation | SoluteStructure, IonStructure |
| `custom_itp_path` | Custom tab | Explicit field propagation | SoluteStructure, IonStructure |
| `solute_type` | Solute tab | Explicit field propagation | IonStructure |
| `solute_positions` | Solute tab | Explicit field propagation | IonStructure |
| `solute_atom_names` | Solute tab | Explicit field propagation | IonStructure |
| `solute_n_molecules` | Solute tab | Explicit field propagation | IonStructure |
| `solute_molecule_indices` | Solute tab | Explicit field propagation | IonStructure |
| `solute_registry` | Solute tab | Explicit field propagation | IonStructure |
| `na_count`, `cl_count` | Ion tab | Direct | IonStructure |

### Export Independence

Each tab can export INDEPENDENTLY (without going through the full chain):
- Ice tab → exports just ice
- Hydrate tab → exports just hydrate (water framework + guests)
- Interface tab → exports ice + water + guests
- Custom tab → exports ice + water + custom (NO solutes/ions)
- Solute tab → exports ice + water + solutes (BUGGY: uses wrong writers)
- Ion tab → exports the FULL system (whatever was accumulated through the chain)

**The Ion tab is the "final assembler"** — it handles all components in one export.

---

## 18. Bundled ITP File Inventory

**Directory:** `quickice/data/`

| File | moleculetype | Residue Name | Atom Count | Purpose |
|------|-------------|-------------|------------|---------|
| `tip4p-ice.itp` | SOL | SOL | 4 (OW,HW1,HW2,MW) | TIP4P-ICE water model |
| `ch4_hydrate.itp` | CH4_H | CH4_H | 5 (C,H×4) | CH4 in hydrate cage |
| `thf_hydrate.itp` | THF_H | THF_H | 13 (O,CA×2,CB×2,H×8) | THF in hydrate cage |
| `ch4_liquid.itp` | CH4_L | CH4_L | 5 (C,H×4) | CH4 dissolved in liquid |
| `thf_liquid.itp` | THF_L | THF_L | 13 (O,CA×2,CB×2,H×8) | THF dissolved in liquid |
| `ch4.itp` | CH4 | CH4 | 5 | Standalone CH4 (legacy) |
| `thf.itp` | THF | THF | 13 | Standalone THF (legacy) |
| `tip4p.gro` | — | — | 4 | Template water molecule coordinates |
| `custom/etoh.gro` | — | — | — | Example custom molecule |
| `custom/etoh.itp` | — | — | — | Example custom molecule topology |

### ITP File Atomtypes Handling

| File | Has [atomtypes]? | Treatment |
|------|-----------------|-----------|
| `tip4p-ice.itp` | Already commented out | Copy as-is |
| `ch4_hydrate.itp` | Already commented out | Copy as-is |
| `thf_hydrate.itp` | Already commented out | Copy as-is |
| `ch4_liquid.itp` | Already commented out | Copy as-is (but code still calls comment_out_atomtypes_in_itp()) |
| `thf_liquid.itp` | Already commented out | Copy as-is (but code still calls comment_out_atomtypes_in_itp()) |
| `ch4.itp` | Not commented | Not used in current export paths |
| `thf.itp` | Not commented | Not used in current export paths |
| User custom .itp | May have [atomtypes] | MUST be commented out via comment_out_atomtypes_in_itp() |

### Generated ITP Files

| File | Generated By | Contents |
|------|-------------|---------|
| `ion.itp` | `write_ion_itp()` in `gromacs_ion_export.py:80` | NA moleculetype (charge +0.85, mass 22.99) + CL moleculetype (charge -0.85, mass 35.45) |

---

*Flow trace analysis: 2026-05-22*
