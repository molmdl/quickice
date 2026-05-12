# GROMACS Export Flow Trace Analysis

**Generated:** 2026-05-12  
**Purpose:** Read-only trace of function and data flow for GROMACS export functionality  
**Reference:** UAT Checklist v4.5 (`.planning/uat/v4.5-batch-testing-checklist.md`)

---

## Executive Summary

This document traces all code paths that lead to GROMACS export (.gro, .top, .itp files) in the QuickIce application. The export system supports 6 different export contexts, each with dedicated exporter classes and writer functions.

**Key Findings:**
- 6 distinct export paths: Ice, Hydrate, Interface, Solute, Custom Molecule, Ion
- Central `gromacs_writer.py` module (2019 lines) handles all file generation
- Moleculetype naming is managed by `MoleculetypeRegistry` for context-specific naming
- All exports use TIP4P-ICE water model with virtual site (MW) computation

---

## 1. Complete Function Call Graph

### 1.1 UI Entry Points (main_window.py)

```
User Action (Menu/Shortcut)
        │
        ▼
MainWindow._on_export_current_tab()     [Ctrl+S - unified export]
        │
        ├── TabIndex.ICE ──────────────► _on_export_gromacs()
        ├── TabIndex.HYDRATE ──────────► _on_export_hydrate_gromacs()
        ├── TabIndex.INTERFACE ────────► _on_export_interface_gromacs()
        ├── TabIndex.SOLUTE ───────────► _on_export_solute_gromacs()
        ├── TabIndex.CUSTOM ───────────► _on_export_custom_molecule_gromacs()
        └── TabIndex.ION ──────────────► _on_export_ion_gromacs()
```

### 1.2 Export Path 1: Ice Structure Export

```
_on_export_gromacs()
    │
    ├── Validate: Check _current_result.ranked_candidates
    ├── Get selected candidate index from viewer
    ├── Extract RankedCandidate object
    ├── Get T (temperature) and P (pressure) from input panel
    │
    ▼
GROMACSExporter.export_gromacs(ranked_candidate, T, P)
    │
    ├── Generate default filename: {phase}_{T}K_{P}MPa_c{rank}.gro
    ├── Show QFileDialog for save path
    │
    ├── [File Generation]
    │   │
    │   ├── write_gro_file(candidate, filepath)
    │   │       │
    │   │       ├── Wrap positions into box: wrap_positions_into_box()
    │   │       ├── Compute MW virtual site: compute_mw_position() for each molecule
    │   │       ├── Write title line
    │   │       ├── Write atom count
    │   │       ├── For each molecule (O, H, H → OW, HW1, HW2, MW):
    │   │       │       Write residue number, residue name (SOL), atom name, coordinates
    │   │       └── Write box vectors (triclinic format)
    │   │
    │   ├── write_top_file(candidate, filepath)
    │   │       │
    │   │       ├── Write [ defaults ] section
    │   │       ├── Write [ atomtypes ] section (OW_ice, HW_ice, MW)
    │   │       ├── Write [ moleculetype ] section (SOL)
    │   │       ├── Write [ atoms ] section (OW, HW1, HW2, MW charges)
    │   │       ├── Write [ settles ], [ virtual_sites3 ], [ exclusions ]
    │   │       ├── Write [ system ] section
    │   │       └── Write [ molecules ] section with count
    │   │
    │   └── Copy tip4p-ice.itp from bundled data
    │           │
    │           └── get_tip4p_itp_path() → quickice/data/tip4p-ice.itp
    │
    └── Show success QMessageBox
```

### 1.3 Export Path 2: Hydrate Structure Export

```
_on_export_hydrate_gromacs()
    │
    ├── Validate: Check _current_hydrate_result, _current_hydrate_config
    │
    ▼
HydrateGROMACSExporter.export_hydrate(structure, config)
    │
    ├── Generate filename: hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro
    ├── Show QFileDialog
    │
    ├── Create MoleculetypeRegistry
    ├── Register guest as hydrate guest: registry.register_hydrate_guest(guest_type)
    │       → Returns "CH4_HYD" or "THF_HYD"
    │
    ├── [File Generation]
    │   │
    │   ├── write_multi_molecule_gro_file(positions, molecule_index, cell, path, title, atom_names)
    │   │       │
    │   │       ├── Wrap molecules into box: wrap_molecules_into_box()
    │   │       ├── For each molecule in molecule_index:
    │   │       │       Get residue name from mol_type
    │   │       │       Reorder guest atoms if needed: reorder_guest_atoms()
    │   │       │       Write all atoms for this molecule
    │   │       └── Write box vectors
    │   │
    │   ├── write_multi_molecule_top_file(molecule_index, path, system_name, itp_files, registry)
    │   │       │
    │   │       ├── Write [ defaults ] section
    │   │       ├── Write [ atomtypes ] section (water + guest types)
    │   │       ├── Write #include directives for ITP files
    │   │       ├── Write [ system ] section
    │   │       └── Write [ molecules ] section with registered names
    │   │
    │   ├── Copy tip4p-ice.itp to output directory
    │   └── Copy guest.itp (ch4.itp or thf.itp) to output directory
    │
    └── Show success QMessageBox
```

### 1.4 Export Path 3: Interface Structure Export

```
_on_export_interface_gromacs()
    │
    ├── Validate: Check _current_interface_result
    │
    ▼
InterfaceGROMACSExporter.export_interface_gromacs(interface_structure)
    │
    ├── Generate filename: interface_{mode}.gro
    ├── Show QFileDialog
    │
    ├── [File Generation]
    │   │
    │   ├── write_interface_gro_file(iface, filepath)
    │   │       │
    │   │       ├── Detect ice type: has_ow_in_ice? (classic vs hydrate ice)
    │   │       │
    │   │       ├── [ICE MOLECULES] (3 or 4 atoms per molecule)
    │   │       │       For each ice molecule:
    │   │       │               Get O, H1, H2 positions
    │   │       │               Compute MW position: compute_mw_position()
    │   │       │               Write OW, HW1, HW2, MW atoms
    │   │       │
    │   │       ├── [WATER MOLECULES] (4 atoms per molecule)
    │   │       │       For each water molecule:
    │   │       │               Write OW, HW1, HW2, MW atoms (pass through)
    │   │       │
    │   │       ├── [GUEST MOLECULES] (if present)
    │   │       │       Detect guest type: detect_guest_type_from_atoms()
    │   │       │       Get residue name: get_guest_residue_name()
    │   │       │       Reorder atoms: reorder_guest_atoms()
    │   │       │       Write all guest atoms
    │   │       │
    │   │       └── Write box vectors
    │   │
    │   ├── write_interface_top_file(iface, filepath)
    │   │       │
    │   │       ├── Write [ defaults ] section
    │   │       ├── Write [ atomtypes ] section
    │   │       │       - Water atom types (OW_ice, HW_ice, MW)
    │   │       │       - Guest atom types if present (GAFF2: c3, hc, os, c5, h1)
    │   │       ├── Write #include directives
    │   │       │       - #include "tip4p-ice.itp"
    │   │       │       - #include "{guest_type}.itp" (if guests)
    │   │       ├── Write [ system ] section
    │   │       └── Write [ molecules ] section
    │   │               - SOL: ice_nmolecules + water_nmolecules (combined)
    │   │               - Guest: guest_nmolecules (if present)
    │   │
    │   ├── Copy tip4p-ice.itp
    │   └── Copy guest.itp (if guests present)
    │
    └── Show success QMessageBox
```

### 1.5 Export Path 4: Solute Structure Export

```
_on_export_solute_gromacs()
    │
    ├── Validate: Check _current_solute_result
    │
    ▼
SoluteGROMACSExporter.export_solute_gromacs(solute_structure)
    │
    ├── Generate filename: solute_{type}_{count}molecules.gro
    ├── Show QFileDialog
    │
    ├── [Data Assembly]
    │   │
    │   ├── Get interface_structure from solute_structure
    │   ├── Combine positions: interface.positions + solute.positions
    │   └── Combine atom_names: interface.atom_names + solute.atom_names
    │
    ├── [File Generation]
    │   │
    │   ├── write_gro_file(all_positions, all_atom_names, cell, path)
    │   │
    │   ├── write_top_file(all_positions, all_atom_names, cell, path, molecule_index, registry)
    │   │       │
    │   │       ├── Build molecule_index:
    │   │       │       - Ice molecules → mol_type: "ICE_IH"
    │   │       │       - Water molecules → mol_type: "WATER_LIQ"
    │   │       │       - Solute molecules → mol_type from registry (CH4_L or THF_L)
    │   │       │
    │   │       └── Write topology with molecule counts
    │   │
    │   ├── Copy tip4p-ice.itp
    │   └── Copy {solute}_liquid.itp (ch4_liquid.itp or thf_liquid.itp)
    │
    └── Show success QMessageBox
```

### 1.6 Export Path 5: Custom Molecule Export

```
_on_export_custom_molecule_gromacs()
    │
    ├── Validate: Check _current_custom_molecule_result
    │
    ▼
CustomMoleculeGROMACSExporter.export_custom_molecule_gromacs(custom_structure)
    │
    ├── Generate filename: custom_system_{moleculetype}_{count}molecules.gro
    ├── Show QFileDialog
    │
    ├── [File Generation]
    │   │
    │   ├── write_custom_molecule_gro_file(custom_structure, filepath)
    │   │       │
    │   │       ├── Build ordered molecule list:
    │   │       │       - Pass 1: SOL molecules (ice + water)
    │   │       │       - Pass 2: Guest molecules (if present)
    │   │       │       - Pass 3: Custom molecules
    │   │       │
    │   │       ├── Wrap positions: wrap_molecules_into_box()
    │   │       │
    │   │       └── For each molecule:
    │   │               Write atoms with proper residue name
    │   │
    │   ├── write_custom_molecule_top_file(custom_structure, filepath)
    │   │       │
    │   │       ├── Write [ defaults ] section
    │   │       ├── Write [ atomtypes ] section
    │   │       │       - Water atom types (OW_ice, HW_ice, MW)
    │   │       │       - Custom atom types (parsed from custom .itp)
    │   │       │
    │   │       ├── Parse custom atomtypes: parse_itp_atomtypes(custom_itp_path)
    │   │       │
    │   │       ├── Write #include directives
    │   │       │       - #include "tip4p-ice.itp"
    │   │       │       - #include "guest.itp" (if guests)
    │   │       │       - #include "{custom_itp_name}"
    │   │       │
    │   │       └── Write [ molecules ] section
    │   │               - SOL count
    │   │               - Guest count (if present)
    │   │               - Custom molecule count
    │   │
    │   └── Copy custom .itp with atomtypes commented out
    │           │
    │           ├── Read custom .itp content
    │           ├── comment_out_atomtypes_in_itp(content)
    │           │       - Add comment header
    │           │       - Prefix [ atomtypes ] lines with ";"
    │           └── Write modified content to output directory
    │
    └── Show success QMessageBox
```

### 1.7 Export Path 6: Ion Structure Export

```
_on_export_ion_gromacs()
    │
    ├── Validate: Check _current_ion_result
    │
    ▼
IonGROMACSExporter.export_ion_gromacs(ion_structure)
    │
    ├── Generate filename: ions_{na}na_{cl}cl.gro (with solute info if present)
    ├── Show QFileDialog
    │
    ├── [File Generation]
    │   │
    │   ├── write_ion_gro_file(ion_structure, filepath)
    │   │       │
    │   │       ├── Build ordered molecule list:
    │   │       │       - Pass 1: SOL molecules (ice + water)
    │   │       │       - Pass 2: Guest molecules
    │   │       │       - Pass 3: Custom molecules (if present)
    │   │       │       - Pass 4: Solute molecules (if present)
    │   │       │       - Pass 5: NA ions
    │   │       │       - Pass 6: CL ions
    │   │       │
    │   │       ├── Wrap positions: wrap_molecules_into_box()
    │   │       │
    │   │       └── For each molecule type:
    │   │               - SOL: Compute MW if ice, pass through if water
    │   │               - Guest: Detect type, reorder atoms, write
    │   │               - Custom: Write with moleculetype name
    │   │               - Solute: Write with registry name
    │   │               - NA/CL: Write single atom
    │   │
    │   ├── write_ion_top_file(ion_structure, filepath)
    │   │       │
    │   │       ├── Count molecules by type
    │   │       ├── Detect guest type from atom names
    │   │       │
    │   │       ├── Write [ defaults ] section
    │   │       │
    │   │       ├── Write [ atomtypes ] section:
    │   │       │       - Water atom types
    │   │       │       - Ion atom types (Madrid2019: NA, CL)
    │   │       │       - Guest atom types (GAFF2)
    │   │       │       - Solute atom types (from liquid .itp)
    │   │       │       - Custom atom types (from custom .itp)
    │   │       │
    │   │       ├── Write #include directives:
    │   │       │       - #include "tip4p-ice.itp"
    │   │       │       - #include "{guest_type}.itp" (if guests)
    │   │       │       - #include "{custom_itp_name}" (if custom)
    │   │       │       - #include "{solute}_liquid.itp" (if solutes)
    │   │       │       - #include "ion.itp"
    │   │       │
    │   │       └── Write [ molecules ] section (ORDER: SOL, guest, custom, solute, NA, CL)
    │   │
    │   ├── Create ion.itp: write_ion_itp(path, na_count, cl_count)
    │   │       │
    │   │       ├── Generate [ moleculetype ] section for NA
    │   │       ├── Generate [ moleculetype ] section for CL
    │   │       └── Use Madrid2019 parameters:
    │   │               - NA: charge=+0.85, sigma=0.2217, epsilon=1.4724
    │   │               - CL: charge=-0.85, sigma=0.4699, epsilon=0.0769
    │   │
    │   ├── Copy tip4p-ice.itp
    │   ├── Copy guest.itp (if guests present)
    │   ├── Copy solute_liquid.itp with atomtypes commented (if solutes)
    │   └── Copy custom.itp with atomtypes commented (if custom molecules)
    │
    └── Show success QMessageBox
```

---

## 2. Data Flow Diagram

### 2.1 Data Transformation Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE LAYER                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  Ice Tab │  │HydrateTab│  │Interface │  │ Solute   │  │Custom/Ion│      │
│  │          │  │          │  │   Tab    │  │   Tab    │  │   Tabs   │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│       │             │             │             │             │             │
│       ▼             ▼             ▼             ▼             ▼             │
│  RankedCandidate  Hydrate   Interface    Solute      IonStructure          │
│                   Structure  Structure    Structure                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXPORTER LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐                                                        │
│  │ GROMACSExporter │ ← Ice only                                             │
│  └────────┬────────┘                                                        │
│           │                                                                 │
│  ┌────────┴────────┐                                                        │
│  │ HydrateGROMACS  │ ← Hydrate (water + guests)                             │
│  │    Exporter     │                                                        │
│  └────────┬────────┘                                                        │
│           │                                                                 │
│  ┌────────┴────────┐                                                        │
│  │ InterfaceGROMACS│ ← Interface (ice + water + guests)                     │
│  │    Exporter     │                                                        │
│  └────────┬────────┘                                                        │
│           │                                                                 │
│  ┌────────┴────────┐                                                        │
│  │ SoluteGROMACS   │ ← Solute (ice + water + solutes)                       │
│  │    Exporter     │                                                        │
│  └────────┬────────┘                                                        │
│           │                                                                 │
│  ┌────────┴────────┐                                                        │
│  │ CustomMolecule  │ ← Custom (ice + water + custom + guests)               │
│  │ GROMACSExporter │                                                        │
│  └────────┬────────┘                                                        │
│           │                                                                 │
│  ┌────────┴────────┐                                                        │
│  │ IonGROMACS      │ ← Ion (ice + water + guests + solutes + custom + ions) │
│  │   Exporter      │                                                        │
│  └────────┬────────┘                                                        │
│           │                                                                 │
└───────────┼─────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           WRITER LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  gromacs_writer.py (2019 lines)                                             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Position Wrapping                                                    │    │
│  │   wrap_positions_into_box() - per-atom wrapping                      │    │
│  │   wrap_molecules_into_box() - molecule-aware wrapping                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Virtual Site Computation                                             │    │
│  │   compute_mw_position(o, h1, h2) → MW = O + α*(H1-O) + α*(H2-O)     │    │
│  │   where α = 0.13458335 (TIP4P-ICE parameter)                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Guest Atom Handling                                                  │    │
│  │   detect_guest_type_from_atoms() - CH4, THF, CO2, H2 detection       │    │
│  │   reorder_guest_atoms() - match .itp canonical order                 │    │
│  │   get_guest_residue_name() - read from bundled .itp                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ ITP Parsing                                                          │    │
│  │   parse_itp_residue_name() - extract residue name from [atoms]       │    │
│  │   parse_itp_atomtypes() - extract atom type definitions              │    │
│  │   comment_out_atomtypes_in_itp() - modify for GROMACS compatibility  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ GRO Writers                                                          │    │
│  │   write_gro_file() - basic ice                                      │    │
│  │   write_interface_gro_file() - ice + water + guests                  │    │
│  │   write_multi_molecule_gro_file() - generic multi-molecule           │    │
│  │   write_ion_gro_file() - complete system with ions                   │    │
│  │   write_custom_molecule_gro_file() - with custom molecules           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ TOP Writers                                                          │    │
│  │   write_top_file() - basic ice                                      │    │
│  │   write_interface_top_file() - ice + water + guests                  │    │
│  │   write_multi_molecule_top_file() - generic multi-molecule           │    │
│  │   write_ion_top_file() - complete system with ions                   │    │
│  │   write_custom_molecule_top_file() - with custom molecules           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OUTPUT FILES                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │    .gro     │  │    .top     │  │    .itp     │                         │
│  │  (coords)   │  │ (topology)  │  │ (molecule   │                         │
│  │             │  │             │  │  defs)      │                         │
│  └─────────────┘  └─────────────┘  └─────────────┘                         │
│                                                                             │
│  Bundled ITP files from quickice/data/:                                     │
│    - tip4p-ice.itp  (water model)                                           │
│    - ch4.itp        (hydrate guest CH4)                                     │
│    - thf.itp        (hydrate guest THF)                                     │
│    - ch4_liquid.itp (liquid solute CH4_L)                                   │
│    - thf_liquid.itp (liquid solute THF_L)                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Structure Flow

```
┌──────────────────┐
│   UI Input       │
│ (user params)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────────┐
│ GenerationResult │     │ InterfaceConfig  │
│ (candidates[])   │     │ (mode, sizes)    │
└────────┬─────────┘     └────────┬─────────┘
         │                        │
         ▼                        ▼
┌──────────────────┐     ┌──────────────────┐
│   Candidate      │     │InterfaceStructure│
│ (positions,      │     │ (ice + water +   │
│  atom_names,     │     │  guests,         │
│  cell, nmolecules)│    │  molecule_index) │
└────────┬─────────┘     └────────┬─────────┘
         │                        │
         │         ┌──────────────┼──────────────┐
         │         │              │              │
         │         ▼              ▼              ▼
         │  ┌────────────┐ ┌────────────┐ ┌────────────┐
         │  │SoluteConfig│ │IonConfig   │ │CustomConfig│
         │  │(type, conc)│ │(concentration)│(gro/itp) │
         │  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
         │        │              │              │
         │        ▼              ▼              ▼
         │  ┌────────────┐ ┌────────────┐ ┌────────────┐
         │  │SoluteStruct│ │IonStructure│ │CustomStruct│
         │  │(solute pos)│ │(ions)      │ │(custom pos)│
         │  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
         │        │              │              │
         └────────┴──────────────┴──────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   GROMACS Export      │
              │ (combine all data)    │
              └───────────┬───────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │   .gro   │   │   .top   │   │   .itp   │
    │(coordinates)│ │(topology)│   │(molecule │
    │           │   │          │   │ defs)    │
    └──────────┘   └──────────┘   └──────────┘
```

---

## 3. Key Functions with Inputs/Outputs

### 3.1 Core Writer Functions

| Function | File | Inputs | Outputs | Description |
|----------|------|--------|---------|-------------|
| `write_gro_file` | gromacs_writer.py:393 | `Candidate`, `filepath` | .gro file | Basic ice structure export |
| `write_top_file` | gromacs_writer.py:479 | `Candidate`, `filepath` | .top file | Basic ice topology |
| `write_interface_gro_file` | gromacs_writer.py:573 | `InterfaceStructure`, `filepath` | .gro file | Ice + water + guests |
| `write_interface_top_file` | gromacs_writer.py:905 | `InterfaceStructure`, `filepath` | .top file | Interface topology |
| `write_multi_molecule_gro_file` | gromacs_writer.py:1012 | `positions`, `molecule_index`, `cell`, `filepath`, `title`, `atom_names` | .gro file | Generic multi-molecule |
| `write_multi_molecule_top_file` | gromacs_writer.py:1109 | `molecule_index`, `filepath`, `system_name`, `itp_files`, `registry` | .top file | Generic multi-molecule topology |
| `write_ion_gro_file` | gromacs_writer.py:1265 | `IonStructure`, `filepath` | .gro file | Complete system with ions |
| `write_ion_top_file` | gromacs_writer.py:1590 | `IonStructure`, `filepath` | .top file | Ion system topology |
| `write_custom_molecule_gro_file` | gromacs_writer.py:1806 | `CustomMoleculeStructure`, `filepath` | .gro file | Custom molecule system |
| `write_custom_molecule_top_file` | gromacs_writer.py:1944 | `CustomMoleculeStructure`, `filepath` | .top file | Custom molecule topology |

### 3.2 Utility Functions

| Function | File | Inputs | Outputs | Description |
|----------|------|--------|---------|-------------|
| `wrap_positions_into_box` | gromacs_writer.py:40 | `positions`, `cell` | `np.ndarray` | Per-atom wrapping |
| `wrap_molecules_into_box` | gromacs_writer.py:61 | `positions`, `molecule_index`, `cell` | `np.ndarray` | Molecule-aware wrapping |
| `compute_mw_position` | gromacs_writer.py:553 | `o_pos`, `h1_pos`, `h2_pos` | `np.ndarray` | MW virtual site calculation |
| `detect_guest_type_from_atoms` | gromacs_writer.py:852 | `atom_names` | `str` or `None` | Guest molecule type detection |
| `reorder_guest_atoms` | gromacs_writer.py:152 | `atom_names`, `mol_type` | `(list, list)` | Reorder to match .itp |
| `get_guest_residue_name` | gromacs_writer.py:357 | `guest_type` | `str` | Residue name from .itp |
| `get_tip4p_itp_path` | gromacs_writer.py:537 | - | `Path` | Bundled tip4p-ice.itp path |
| `parse_itp_atomtypes` | gromacs_writer.py:259 | `itp_path` | `list[tuple]` | Extract atomtype definitions |
| `comment_out_atomtypes_in_itp` | gromacs_writer.py:310 | `itp_content` | `str` | Modify .itp for compatibility |
| `write_ion_itp` | gromacs_ion_export.py:80 | `output_path`, `na_count`, `cl_count` | ion.itp | Generate ion topology |

### 3.3 Exporter Classes

| Class | File | Key Method | Purpose |
|-------|------|------------|---------|
| `GROMACSExporter` | export.py:648 | `export_gromacs()` | Ice structure export |
| `HydrateGROMACSExporter` | hydrate_export.py:44 | `export_hydrate()` | Hydrate structure export |
| `InterfaceGROMACSExporter` | export.py:755 | `export_interface_gromacs()` | Interface structure export |
| `SoluteGROMACSExporter` | export.py:26 | `export_solute_gromacs()` | Solute structure export |
| `CustomMoleculeGROMACSExporter` | export.py:152 | `export_custom_molecule_gromacs()` | Custom molecule export |
| `IonGROMACSExporter` | export.py:231 | `export_ion_gromacs()` | Ion structure export |

---

## 4. Critical Validation Checkpoints

### 4.1 Pre-Export Validation

| Checkpoint | Location | Validation |
|------------|----------|------------|
| Structure exists | main_window.py:1597 | `_current_result.ranked_candidates` not empty |
| Interface exists | main_window.py:1635 | `_current_interface_result` not None |
| Hydrate exists | main_window.py:1664 | `_current_hydrate_result` not None |
| Solute exists | main_window.py:1733 | `_current_solute_result` not None |
| Custom molecules exist | main_window.py:1766 | `_current_custom_molecule_result` not None |
| Ions exist | main_window.py:1702 | `_current_ion_result` not None |

### 4.2 Data Integrity Validation

| Checkpoint | Location | Validation |
|------------|----------|------------|
| Atom count | gromacs_writer.py:424 | `positions` has expected atom count |
| Coordinate range | gromacs_writer.py:600 | Coordinates in nm range (< 100) |
| GRO limit | gromacs_writer.py:418 | Warning if > 99999 atoms |
| Molecule index | gromacs_writer.py:621 | Use molecule-aware wrapping if available |
| Guest detection | gromacs_writer.py:732 | Detect guest type from atom composition |

### 4.3 File Generation Validation

| Checkpoint | Location | Validation |
|------------|----------|------------|
| .gro file created | gromacs_writer.py:430-476 | Write coordinates and box vectors |
| .top file created | gromacs_writer.py:488-534 | Write topology sections |
| .itp file copied | export.py:718-720 | Copy tip4p-ice.itp from bundled data |
| Guest .itp copied | export.py:841-844 | Copy guest.itp if guests present |
| Custom .itp modified | export.py:212-216 | Comment out [ atomtypes ] section |

---

## 5. Dependencies Between Modules

### 5.1 Module Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GUI Layer (gui/)                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   main_window.py                                                    │
│        │                                                            │
│        ├──► export.py (GROMACSExporter classes)                     │
│        │        │                                                   │
│        │        └──► gromacs_writer.py (write_* functions)          │
│        │                    │                                       │
│        │                    ├──► types.py (data structures)         │
│        │                    ├──► molecule_utils.py (count_guest)    │
│        │                    └──► moleculetype_registry.py           │
│        │                                                            │
│        └──► hydrate_export.py (HydrateGROMACSExporter)              │
│                 │                                                   │
│                 └──► gromacs_writer.py                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Structure Generation Layer                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   types.py                                                          │
│        │                                                            │
│        ├── Candidate (ice structures)                               │
│        ├── InterfaceStructure (ice + water + guests)                │
│        ├── HydrateStructure (water + guests)                        │
│        ├── SoluteStructure (interface + solutes)                    │
│        ├── CustomMoleculeStructure (interface + custom)             │
│        └── IonStructure (all components + ions)                     │
│                                                                     │
│   MoleculeIndex (tracks molecules in atom array)                    │
│                                                                     │
│   moleculetype_registry.py                                          │
│        │                                                            │
│        └── MoleculetypeRegistry                                     │
│             - register_hydrate_guest() → CH4_HYD, THF_HYD           │
│             - register_liquid_solute() → CH4_L, THF_L               │
│             - register_custom_molecule() → unique name              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Data Layer (data/)                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   quickice/data/                                                    │
│        │                                                            │
│        ├── tip4p-ice.itp    (TIP4P-ICE water model)                 │
│        ├── ch4.itp          (Hydrate guest CH4)                     │
│        ├── thf.itp          (Hydrate guest THF)                     │
│        ├── ch4_liquid.itp   (Liquid solute CH4_L)                   │
│        └── thf_liquid.itp   (Liquid solute THF_L)                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Import Dependencies

```python
# main_window.py imports
from quickice.gui.export import (
    GROMACSExporter,
    InterfaceGROMACSExporter,
    IonGROMACSExporter,
    SoluteGROMACSExporter,
    CustomMoleculeGROMACSExporter
)
from quickice.gui.hydrate_export import HydrateGROMACSExporter

# export.py imports
from quickice.output.gromacs_writer import (
    write_gro_file,
    write_top_file,
    write_interface_gro_file,
    write_interface_top_file,
    write_ion_gro_file,
    write_ion_top_file,
    write_custom_molecule_gro_file,
    write_custom_molecule_top_file,
    get_tip4p_itp_path,
    detect_guest_type_from_atoms,
    comment_out_atomtypes_in_itp,
)
from quickice.structure_generation.gromacs_ion_export import write_ion_itp
from quickice.structure_generation.types import (
    Candidate,
    InterfaceStructure,
    IonStructure,
    SoluteStructure,
    CustomMoleculeStructure
)

# gromacs_writer.py imports
from quickice.utils.molecule_utils import count_guest_atoms
from quickice.structure_generation.types import (
    Candidate,
    InterfaceStructure,
    IonStructure,
    MoleculeIndex,
    MOLECULE_TYPE_INFO
)
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
```

---

## 6. Error Handling

### 6.1 Export-Level Error Handling

```python
# Pattern used in all exporter classes
try:
    # ... file generation code ...
    return True
except Exception as e:
    QMessageBox.critical(self.parent, "Export Error", f"Failed: {e}")
    import traceback
    traceback.print_exc()
    return False
```

### 6.2 Common Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| "No Data" | No structure generated | User must generate structure first |
| "No Interface" | No interface created | User must create interface first |
| "No Hydrate" | No hydrate generated | User must generate hydrate first |
| "No Solutes" | No solutes inserted | User must insert solutes first |
| "No Custom Molecules" | No custom molecules placed | User must place custom molecules first |
| "No Ions" | No ions inserted | User must insert ions first |
| FileNotFoundError | Guest .itp not found | Use bundled .itp or provide manually |

### 6.3 Graceful Degradation

- Guest .itp not found: Export continues, user warned they may need to add manually
- Atom count mismatch: Warning logged, export continues
- Coordinate range warning: Logs if coordinates may be in Angstrom instead of nm

---

## 7. Moleculetype Naming Convention

### 7.1 Registry-Based Naming

The `MoleculetypeRegistry` provides context-specific moleculetype names:

| Context | Molecule | Registered Name | .itp File |
|---------|----------|-----------------|-----------|
| Hydrate guest | CH4 | CH4_HYD | ch4.itp |
| Hydrate guest | THF | THF_HYD | thf.itp |
| Liquid solute | CH4 | CH4_L | ch4_liquid.itp |
| Liquid solute | THF | THF_L | thf_liquid.itp |
| Custom molecule | (user-defined) | MOL, MOL_1, etc. | (user-provided) |

### 7.2 Reserved Names

```python
RESERVED_NAMES = {
    "SOL", "NA", "CL", "CH4", "THF", "CO2", "H2",
    "CH4_HYD", "CH4_L", "THF_HYD", "THF_L"
}
```

---

## 8. File Output Format Details

### 8.1 .gro File Structure

```
Title line (user-defined or auto-generated)
{N_atoms:5d}
{res_num:5d}{res_name:<5s}{atom_name:>5s}{atom_num:5d}{x:8.3f}{y:8.3f}{z:8.3f}
... (repeat for each atom)
{box_xx:10.5f}{box_yy:10.5f}{box_zz:10.5f}{box_xy:10.5f}{box_xz:10.5f}{box_yx:10.5f}{box_yz:10.5f}{box_zx:10.5f}{box_zy:10.5f}
```

### 8.2 .top File Structure

```
; Header comments
[ defaults ]
; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ
1         2          yes        0.5      0.8333

[ atomtypes ]
; name  bond_type  atomic_number  mass  charge  ptype  V  W
OW_ice  OW_ice     8              15.9994  0.0   A      0.31668e-3  0.88216e-6
...

; Molecule definitions
#include "tip4p-ice.itp"
#include "ch4.itp"  (if guests)
#include "custom.itp"  (if custom)
#include "ion.itp"  (if ions)

[ system ]
System name

[ molecules ]
; Compound    #mols
SOL           N
CH4_HYD       M  (hydrate guests)
CH4_L         K  (liquid solutes)
CUSTOM        L  (custom molecules)
NA            P  (sodium ions)
CL            Q  (chloride ions)
```

### 8.3 .itp File Handling

Bundled .itp files in `quickice/data/`:

| File | Moleculetype | Purpose |
|------|--------------|---------|
| tip4p-ice.itp | SOL | TIP4P-ICE water model |
| ch4.itp | CH4 | Hydrate guest methane |
| thf.itp | THF | Hydrate guest THF |
| ch4_liquid.itp | CH4_L | Liquid solute methane |
| thf_liquid.itp | THF_L | Liquid solute THF |

Custom .itp files are modified at export:
- `[ atomtypes ]` section is commented out
- Types must be defined in main .top file to avoid GROMACS errors

---

## 9. Workflow Chains (from UAT Checklist)

### 9.1 Full Chain: Interface → Custom → Solute → Ion

```
1. Tab 2 (Interface): Generate interface structure
   └─► _current_interface_result = InterfaceStructure
   
2. Tab 3 (Custom): Upload molecule files, place molecules
   └─► _current_custom_molecule_result = CustomMoleculeStructure
       (contains: ice + water + custom molecules)
   
3. Tab 4 (Solute): Select Custom Molecule source, add solutes
   └─► _current_solute_result = SoluteStructure
       (contains: interface + solutes, passes custom molecule data)
   
4. Tab 5 (Ion): Select Solute source, add ions
   └─► _current_ion_result = IonStructure
       (contains: ALL components + ions)
   
5. Export from Ion tab
   └─► IonGROMACSExporter.export_ion_gromacs()
       Outputs: .gro, .top, ion.itp, tip4p-ice.itp,
                solute_liquid.itp, custom.itp
```

### 9.2 Molecule Ordering in Output

```
[ molecules ] section order:
1. SOL (ice + water combined)
2. Guest molecules (CH4_HYD, THF_HYD) - from hydrate
3. Custom molecules (user-defined name)
4. Solute molecules (CH4_L, THF_L)
5. NA (sodium ions)
6. CL (chloride ions)
```

---

## 10. Summary

The GROMACS export system in QuickIce is a comprehensive pipeline supporting 6 different export contexts. Key architectural decisions:

1. **Separation of Concerns**: UI handlers, exporter classes, and writer functions are cleanly separated
2. **Data Structure Consistency**: All structure types follow a common pattern with positions, atom_names, cell, and molecule_index
3. **Registry-Based Naming**: MoleculetypeRegistry ensures unique, context-appropriate moleculetype names
4. **Bundled Resources**: Standard .itp files are bundled with the package, custom .itp files are modified for compatibility
5. **Comprehensive Molecule Support**: Water (TIP4P-ICE), guests (CH4, THF), ions (NA, CL), and custom molecules are all supported

The export pipeline correctly handles:
- 3-atom ice molecules (O, H, H) → 4-atom TIP4P-ICE (OW, HW1, HW2, MW)
- Virtual site (MW) computation at export time
- Guest atom reordering to match .itp canonical order
- Multi-molecule topology generation with proper [ molecules ] ordering
- ITP file modification (atomtypes commenting) for GROMACS compatibility

---

*Report generated: 2026-05-12*
*Analysis based on code review of quickice/gui/export.py, quickice/gui/hydrate_export.py, quickice/output/gromacs_writer.py, and related modules*
