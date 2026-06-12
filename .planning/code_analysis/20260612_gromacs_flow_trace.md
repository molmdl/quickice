# GROMACS Export Flow Trace

**Analysis Date:** 2026-06-12
**Scope:** Complete function and data flow trace from user action to GROMACS file output
**Reference:** `.planning/uat/v4.5-batch-testing-checklist.md` Workflows 2–9

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Exporter Classes Summary](#2-exporter-classes-summary)
3. [Workflow 2: Ice Generation → GROMACS Export](#3-workflow-2-ice-generation--gromacs-export)
4. [Workflow 3: Hydrate Generation → GROMACS Export](#4-workflow-3-hydrate-generation--gromacs-export)
5. [Workflow 4: Interface Generation → GROMACS Export](#5-workflow-4-interface-generation--gromacs-export)
6. [Workflow 5: Custom Molecule → GROMACS Export](#6-workflow-5-custom-molecule--gromacs-export)
7. [Workflow 6: Solute Insertion → GROMACS Export](#7-workflow-6-solute-insertion--gromacs-export)
8. [Workflow 7: Ion Insertion → GROMACS Export](#8-workflow-7-ion-insertion--gromacs-export)
9. [Workflow 8: Cross-Tab Chain → GROMACS Export](#9-workflow-8-cross-tab-chain--gromacs-export)
10. [Workflow 9: Tab-Specific Export Paths](#10-workflow-9-tab-specific-export-paths)
11. [Core GROMACS Writer Functions](#11-core-gromacs-writer-functions)
12. [Data Structures Reference](#12-data-structures-reference)
13. [Error Handling Paths](#13-error-handling-paths)
14. [File Output Summary](#14-file-output-summary)

---

## 1. Architecture Overview

The GROMACS export flow follows a 3-layer architecture:

```
┌─────────────────────────────────────────────────────────┐
│  VIEW LAYER (PySide6 GUI)                              │
│  MainWindow → Menu/Shortcut → _on_export_*_gromacs()  │
│  File: quickice/gui/main_window.py                     │
└──────────────┬──────────────────────────────────────────┘
               │ calls
┌──────────────▼──────────────────────────────────────────┐
│  EXPORT LAYER (QFileDialog + file coordination)         │
│  GROMACSExporter / InterfaceGROMACSExporter /            │
│  HydrateGROMACSExporter / SoluteGROMACSExporter /       │
│  CustomMoleculeGROMACSExporter / IonGROMACSExporter     │
│  File: quickice/gui/export.py, quickice/gui/hydrate_export.py │
└──────────────┬──────────────────────────────────────────┘
               │ calls
┌──────────────▼──────────────────────────────────────────┐
│  WRITER LAYER (Pure data → file I/O)                    │
│  write_gro_file / write_interface_gro_file /            │
│  write_ion_gro_file / write_solute_gro_file /           │
│  write_custom_molecule_gro_file / write_*_top_file      │
│  File: quickice/output/gromacs_writer.py                │
│  File: quickice/structure_generation/gromacs_ion_export.py │
└─────────────────────────────────────────────────────────┘
```

**Key principle:** The View layer decides WHAT to export, the Export layer coordinates WHERE and bundles ITP files, the Writer layer handles the actual binary/text file format.

---

## 2. Exporter Classes Summary

| Exporter Class | File | Tab | Input Data | Output Files |
|---|---|---|---|---|
| `GROMACSExporter` | `quickice/gui/export.py:690` | Tab 0 (Ice) | `RankedCandidate` | `.gro`, `.top`, `tip4p-ice.itp` |
| `HydrateGROMACSExporter` | `quickice/gui/hydrate_export.py:71` | Tab 1 (Hydrate) | `HydrateStructure` + `HydrateConfig` | `.gro`, `.top`, `tip4p-ice.itp`, `{guest}_hydrate.itp` |
| `InterfaceGROMACSExporter` | `quickice/gui/export.py:826` | Tab 2 (Interface) | `InterfaceStructure` | `.gro`, `.top`, `tip4p-ice.itp`, `{guest}_hydrate.itp` (if guests) |
| `CustomMoleculeGROMACSExporter` | `quickice/gui/export.py:160` | Tab 3 (Custom) | `CustomMoleculeStructure` | `.gro`, `.top`, `tip4p-ice.itp`, custom `.itp`, `{guest}_hydrate.itp` (if guests) |
| `SoluteGROMACSExporter` | `quickice/gui/export.py:26` | Tab 4 (Solute) | `SoluteStructure` | `.gro`, `.top`, `tip4p-ice.itp`, `{solute}_liquid.itp`, `{guest}_hydrate.itp`, custom `.itp` (if present) |
| `IonGROMACSExporter` | `quickice/gui/export.py:268` | Tab 5 (Ion) | `IonStructure` | `.gro`, `.top`, `tip4p-ice.itp`, `ion.itp`, `{guest}_hydrate.itp`, `{solute}_liquid.itp`, custom `.itp` (if present) |

---

## 3. Workflow 2: Ice Generation → GROMACS Export

### 3.1 Generation Phase (Tab 0)

```
User clicks "Generate" button
  → MainWindow._on_generate_clicked()                      [main_window.py:417]
    → InputPanel.validate_all()
    → InputPanel.get_temperature() → float (K)
    → InputPanel.get_pressure() → float (MPa)
    → InputPanel.get_nmolecules() → int
    → MainViewModel.start_generation(T, P, nmolecules)    [viewmodel.py:61]
      → GenerationWorker(T, P, nmolecules)                 [workers.py:26]
      → worker.moveToThread(QThread)
      → thread.start()

  [Background Thread]
  → GenerationWorker.run()                                  [workers.py:69]
    → lookup_phase(T, P)                                    [phase_mapping/lookup.py]
      → Returns phase_info
    → generate_candidates(phase_info, nmolecules, n_candidates=10)
      → Returns GenerationResult with candidates list
    → rank_candidates(candidates)
      → Returns RankingResult with ranked_candidates list

  [Main Thread - Signal]
  → ViewModel._on_finished(result)                          [viewmodel.py:135]
    → ranked_candidates_ready.emit(RankingResult)
  → MainWindow._on_candidates_ready(result)                 [main_window.py:462]
    → Stores self._current_result = result
    → Updates InterfacePanel candidate dropdown
    → Loads dual viewer with ranked candidates
```

### 3.2 Export Phase (Tab 0)

```
User clicks "Export for GROMACS" (Ctrl+G) or "Export Current Tab" (Ctrl+S) on Tab 0
  → MainWindow._on_export_gromacs()                        [main_window.py:1593]
    │ Guard: self._current_result must exist and have ranked_candidates
    │ Guard: ranked_candidates must not be empty
    │
    → Gets selected_idx from ViewerPanel.get_selected_candidate_index_left()
    → ranked = self._current_result.ranked_candidates[selected_idx]
    → T = InputPanel.get_temperature()
    → P = InputPanel.get_pressure()
    │
    → self._gromacs_exporter.export_gromacs(ranked, T, P)  [export.py:704]
      │
      │ ┌─ Default filename: {phase_id}_{T}K_{P}MPa_c{rank}.gro
      │ │  QFileDialog.getSaveFileName(parent, "Export for GROMACS", default_name, "GRO Files (*.gro)")
      │ │  Returns: (filepath, selected_filter)
      │ │  If user cancels: return False
      │ │
      │ │  Ensures .gro extension on path
      │ │  top_path = path.stem + '.top'
      │ │  itp_path = path.stem + '.itp'
      │ │
      │ ├─ WRITER: write_gro_file(candidate, str(path))     [gromacs_writer.py:427]
      │ │  Input: Candidate (positions, atom_names, cell, nmolecules, phase_id)
      │ │  Process:
      │ │    1. Build MoleculeIndex list: ice_molecule_index[i] = MoleculeIndex(start=i*3, count=3, mol_type="ice")
      │ │    2. wrap_molecules_into_box(candidate.positions, ice_molecule_index, candidate.cell)
      │ │       → For each molecule: unwrap atoms split across PBC, then wrap center into [0, box)
      │ │    3. Validate: len(wrapped_positions) >= nmolecules * 3
      │ │    4. For each molecule (mol_idx):
      │ │       - O_pos = wrapped[mol_idx*3], H1 = [mol_idx*3+1], H2 = [mol_idx*3+2]
      │ │       - MW = compute_mw_position(O, H1, H2)     [gromacs_writer.py:595]
      │ │         Formula: MW = O + α*(H1-O) + α*(H2-O), α = 0.13458335
      │ │       - Write: res_num SOL OW/HW1/HW2/MW with coordinates
      │ │    5. Write box vectors (triclinic format: 9 values)
      │ │  Output: .gro file with nmolecules*4 atoms (3→4 atom expansion)
      │ │
      │ ├─ WRITER: write_top_file(candidate, str(top_path))  [gromacs_writer.py:521]
      │ │  Input: Candidate (nmolecules, phase_id)
      │ │  Output: .top file with:
      │ │    - [ defaults ]: nbfunc=1, comb-rule=2, gen-pairs=yes, fudgeLJ=0.5, fudgeQQ=0.8333
      │ │    - [ atomtypes ]: OW_ice, HW_ice, MW (TIP4P-ICE)
      │ │    - [ moleculetype ]: SOL nrexcl=2
      │ │    - [ atoms ]: OW/HW1/HW2/MW with charges
      │ │    - [ settles ], [ virtual_sites3 ], [ exclusions ]
      │ │    - [ system ], [ molecules ]: SOL {nmol}
      │ │
      │ └─ BUNDLING: shutil.copy(get_tip4p_itp_path(), itp_path)
      │     get_tip4p_itp_path()                              [gromacs_writer.py:579]
      │       → Package dir: quickice/data/tip4p-ice.itp
      │       → Fallback: project_root/data/tip4p-ice.itp
      │
      → On success: QMessageBox.information("Export Complete")
      → On exception: QMessageBox.critical("Export Error", f"Failed: {e}")
```

### 3.3 Output Files

| File | Content | Format |
|---|---|---|
| `{phase_id}_{T}K_{P}MPa_c{rank}.gro` | Atom coordinates (TIP4P-ICE: 4 atoms/mol) | GROMACS coordinate |
| `{phase_id}_{T}K_{P}MPa_c{rank}.top` | Full topology (inline SOL definition) | GROMACS topology |
| `{phase_id}_{T}K_{P}MPa_c{rank}.itp` | Copy of `tip4p-ice.itp` | GROMACS include |

---

## 4. Workflow 3: Hydrate Generation → GROMACS Export

### 4.1 Generation Phase (Tab 1)

```
User configures HydratePanel and clicks "Generate"
  → MainWindow._on_hydrate_generate_clicked()              [main_window.py:736]
    → config = HydratePanel.get_configuration()
    → self._current_hydrate_config = config
    → self._hydrate_worker = HydrateWorker(config)          [hydrate_worker.py:15]
    → Connect signals: progress_updated, generation_complete, generation_error
    → worker.start()

  [Background Thread]
  → HydrateWorker.run()                                     [hydrate_worker.py:50]
    → HydrateStructureGenerator().generate(config)          [hydrate_generator.py]
      → Uses GenIce2 to generate hydrate lattice
      → Returns HydrateStructure(positions, atom_names, cell, molecule_index, config, lattice_info, report, guest_count, water_count)

  [Main Thread - Signal]
  → MainWindow._on_hydrate_generation_complete(result)      [main_window.py:768]
    → self._current_hydrate_result = result
    → hydrate_panel.set_hydrate_structure(result)
```

### 4.2 Export Phase (Tab 1)

```
User clicks "Export Hydrate..." (Ctrl+H) or Ctrl+S on Tab 1
  → MainWindow._on_export_hydrate_gromacs()                 [main_window.py:1660]
    │ Guard: self._current_hydrate_result must exist
    │ Guard: self._current_hydrate_config must exist
    │
    → self._hydrate_gromacs_exporter.export_hydrate(structure, config)  [hydrate_export.py:90]
      │
      │ ┌─ Default filename: hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro
      │ │  QFileDialog.getSaveFileName(...)
      │ │  Ensures .gro extension
      │ │  top_path = path.stem + '.top'
      │ │
      │ ├─ REGISTRY: MoleculetypeRegistry()                  [moleculetype_registry.py:13]
      │ │  → registry.register_hydrate_guest(config.guest_type.upper())
      │ │  → Returns "CH4_H" or "THF_H"
      │ │
      │ ├─ ITP PATH: _get_hydrate_guest_itp_path(guest_type) [hydrate_export.py:44]
      │ │  → Package dir: quickice/data/{guest}_hydrate.itp
      │ │  → Fallback: project_root/data/{guest}_hydrate.itp
      │ │
      │ ├─ WRITER: write_multi_molecule_gro_file(           [gromacs_writer.py:1055]
      │ │    structure.positions,
      │ │    structure.molecule_index,
      │ │    structure.cell,
      │ │    str(path),
      │ │    title,
      │ │    atom_names=structure.atom_names)
      │ │  Process:
      │ │    1. Validate coordinates in nm range
      │ │    2. For each MoleculeIndex in molecule_index:
      │ │       - Get residue name: guest mol → get_guest_residue_name(mol_type)
      │ │       - For guest mol (ch4/thf): reorder_guest_atoms() to canonical order
      │ │       - Write atoms with {res_num}{res_name}{atom_name}{atom_num}{coords}
      │ │    3. Write box vectors
      │ │
      │ ├─ WRITER: write_multi_molecule_top_file(           [gromacs_writer.py:1152]
      │ │    structure.molecule_index,
      │ │    str(top_path),
      │ │    system_name,
      │ │    itp_files={guest_type: guest_itp_path.name},
      │ │    registry=registry)
      │ │  Process:
      │ │    1. Count molecules by type (unique_types, counts)
      │ │    2. Build [atomtypes] section: OW_ice, HW_ice, MW + GAFF2 types
      │ │    3. Build #include directives: tip4p-ice.itp, {guest}_hydrate.itp
      │ │    4. Build [system] and [molecules] sections
      │ │       - Uses registry for moleculetype names (CH4_H, THF_H)
      │ │
      │ └─ BUNDLING:
      │    → shutil.copy(tip4p_itp_path, "tip4p-ice.itp")
      │    → shutil.copy(guest_itp_path, "{guest}_hydrate.itp")
      │
      → On success: QMessageBox.information(...)
      → On exception: QMessageBox.critical(...)
```

### 4.3 Output Files

| File | Content |
|---|---|
| `hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro` | Water + guest coordinates |
| `hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.top` | Topology with #include directives |
| `tip4p-ice.itp` | Bundled water topology |
| `{guest}_hydrate.itp` | Bundled guest topology (CH4_H or THF_H moleculetype) |

---

## 5. Workflow 4: Interface Generation → GROMACS Export

### 5.1 Generation Phase (Tab 2)

**From Ice Source:**
```
User selects candidate and clicks "Generate Interface"
  → MainWindow._on_interface_generate(candidate_index)      [main_window.py:553]
    → ranking_result = viewmodel.get_last_ranking_result()
    → candidate = ranking_result.ranked_candidates[candidate_index].candidate
    → config_dict = interface_panel.get_configuration()
    → config = InterfaceConfig.from_dict(config_dict)       [types.py:196]
    → viewmodel.start_interface_generation(candidate, config)

  [Background Thread]
  → InterfaceGenerationWorker.run()                         [workers.py:185]
    → generate_interface(candidate, config)                 [interface_builder.py]
      → validate_interface_config(config, candidate)
      → Route to mode: assemble_slab / assemble_pocket / assemble_piece
      → Returns InterfaceStructure

  [Main Thread - Signal]
  → MainWindow._on_interface_generation_complete(result)     [main_window.py:604]
    → self._current_interface_result = result
    → Updates ion_panel liquid volume
    → Updates solute_panel liquid volume
    → Updates custom_molecule_panel interface structure
```

**From Hydrate Source:**
```
User clicks "Use in Interface →" or generates with Source=hydrate
  → MainWindow._on_interface_hydrate_generate()             [main_window.py:666]
    → hydrate = self._current_hydrate_result
    → candidate = hydrate.to_candidate()                    [types.py:658]
      → Iterates molecule_index, collects all positions (water + guests)
      → Returns Candidate with hydrate water+guest data
    → Same flow as ice source: viewmodel.start_interface_generation(candidate, config)
```

### 5.2 Export Phase (Tab 2)

```
User clicks "Export Interface..." (Ctrl+I) or Ctrl+S on Tab 2
  → MainWindow._on_export_interface_gromacs()                [main_window.py:1634]
    │ Guard: self._current_interface_result must exist
    │
    → self._interface_gromacs_exporter.export_interface_gromacs(iface)  [export.py:844]
      │
      │ ┌─ Default filename: interface_{mode}.gro
      │ │  QFileDialog.getSaveFileName(...)
      │ │  Ensures .gro extension
      │ │  top_path = path.stem + '.top'
      │ │
      │ ├─ WRITER: write_interface_gro_file(iface, str(path))  [gromacs_writer.py:615]
      │ │  Input: InterfaceStructure
      │ │    - positions (ice + water + guests)
      │ │    - atom_names
      │ │    - cell (3x3 nm)
      │ │    - ice_atom_count, water_atom_count, guest_atom_count
      │ │    - ice_nmolecules, water_nmolecules, guest_nmolecules
      │ │    - molecule_index (optional)
      │ │  Process:
      │ │    1. Validate coordinates in nm range (warn if max > 100)
      │ │    2. Calculate total output atoms:
      │ │       - Ice: ice_nmolecules * 4 (3→4 expansion)
      │ │       - Water: water_nmolecules * 4
      │ │       - Guests: guest_atom_count
      │ │    3. Wrap positions: wrap_molecules_into_box() if molecule_index exists,
      │ │       else wrap_positions_into_box()
      │ │    4. Detect ice atom type: "OW" in ice_region → 4 atoms/mol, else 3
      │ │    5. Write ice molecules: 3→4 atom expansion with compute_mw_position()
      │ │    6. Write water molecules: 4 atoms pass-through, MW recomputed
      │ │    7. Write guest molecules (if present):
      │ │       - detect_guest_type_from_atoms(guest_atom_names)
      │ │       - get_hydrate_guest_residue_name(guest_type) → "CH4_H" / "THF_H"
      │ │       - reorder_guest_atoms() for ch4/thf canonical order
      │ │    8. Write box vectors
      │ │
      │ ├─ WRITER: write_interface_top_file(iface, str(top_path))  [gromacs_writer.py:947]
      │ │  Input: InterfaceStructure
      │ │  Process:
      │ │    1. [defaults] section
      │ │    2. [atomtypes]: OW_ice, HW_ice, MW + GAFF2 for guests
      │ │    3. #include "tip4p-ice.itp"
      │ │    4. If guests: #include "{guest_type}_hydrate.itp"
      │ │    5. [system] section
      │ │    6. [molecules]: SOL {ice_nmolecules + water_nmolecules}, then guests
      │ │
      │ └─ BUNDLING:
      │    → shutil.copy(get_tip4p_itp_path(), "tip4p-ice.itp")
      │    → If guests: shutil.copy({guest}_hydrate.itp path, "{guest}_hydrate.itp")
      │       On FileNotFoundError: QMessageBox.warning("Missing Guest ITP")
      │
      → On success: QMessageBox.information(...)
      → On exception: QMessageBox.critical(...)
```

### 5.3 Output Files

| File | Content |
|---|---|
| `interface_{mode}.gro` | Ice + water + guest coordinates (ice 3→4 atoms) |
| `interface_{mode}.top` | Topology with SOL + guest molecules |
| `tip4p-ice.itp` | Bundled water topology |
| `{guest}_hydrate.itp` | Guest topology (if guests present) |

---

## 6. Workflow 5: Custom Molecule → GROMACS Export

### 6.1 Generation Phase (Tab 3)

```
User uploads .gro/.itp files and clicks "Generate"
  → MainWindow._on_custom_generate_clicked()               [main_window.py:1091]
    │ Guard: Check for previous insertion → prompt to clear or cancel
    │ Guard: self._current_interface_result must exist
    │
    → config = custom_molecule_panel.get_configuration()   → CustomMoleculeConfig
    → self._custom_worker = CustomMoleculeWorker(config, interface_result, gro_path, itp_path)
    → self._custom_worker_thread = QThread()
    → worker.moveToThread(thread)
    → Connect signals: started→run, finished→quit, finished→_on_custom_finished
    → thread.start()

  [Background Thread]
  → CustomMoleculeWorker.run()                               [custom_molecule_worker.py:67]
    → parse_gro_file(gro_path)                              [gro_parser.py]
    → CustomMoleculeInserter(config)                         [custom_molecule_inserter.py:47]
      → Loads template: parse_gro_file(config.gro_path) → template_positions, template_atom_names
    │
    │ If placement_mode == "random":
    │   → inserter.place_random(structure, n_molecules)     [custom_molecule_inserter.py:543]
    │     1. Build existing_tree from ice+guest atoms (exclude water, MW)
    │     2. Get liquid region bounds (min/max coords)
    │     3. For each molecule (max_attempts per):
    │        - Random position in liquid bounds
    │        - Random rotation: Rotation.random()
    │        - Rotate centered template, translate to position
    │        - Check overlap against existing_tree
    │        - If valid: add to placed_positions, rebuild tree
    │     4. _remove_overlapping_water(structure, all_custom_positions, min_separation)
    │        - Build KDTree from custom molecule atoms
    │        - Check each water molecule for overlap with custom atoms
    │        - Remove overlapping water molecules
    │        - Return modified InterfaceStructure
    │     5. Build complete_molecule_index: ice → water → guest → custom
    │     6. Combine positions: modified_structure[ice+water+guest] + custom_positions
    │     7. Register: registry.register_custom_molecule() → "MOL" / "MOL_1" / ...
    │     8. Return CustomMoleculeStructure
    │
    │ If placement_mode == "custom":
    │   → inserter.place_custom(structure, positions, rotations) [custom_molecule_inserter.py:775]
    │     1. For each (position, rotation):
    │        - Convert Euler angles to rotation matrix
    │        - Rotate centered template, translate to position
    │        - No overlap check (user responsibility)
    │     2. _remove_overlapping_water() same as random mode
    │     3. Build complete molecule_index, combine positions
    │     4. Register custom molecule
    │     5. Return CustomMoleculeStructure

  [Main Thread - Signal]
  → MainWindow._on_custom_finished(result)                  [main_window.py:1170]
    → self._current_custom_molecule_result = result
    → custom_molecule_panel.custom_viewer.update_structure(result)
    → solute_panel.set_custom_molecule_structure(result)   → enables "Custom Molecule" source
    → ion_panel.set_custom_molecule_structure(result)        → enables "Custom Molecule" source
    → Updates solute/ion liquid volumes
```

### 6.2 Export Phase (Tab 3)

```
User clicks "Export Custom Molecule..." (Ctrl+M) or Ctrl+S on Tab 3
  → MainWindow._on_export_custom_molecule_gromacs()         [main_window.py:1761]
    │ Guard: self._current_custom_molecule_result must exist
    │
    → self._custom_molecule_gromacs_exporter.export_custom_molecule_gromacs(custom_structure)  [export.py:171]
      │
      │ ┌─ Default filename: custom_system_{moleculetype_name}_{n_molecules}molecules.gro
      │ │  QFileDialog.getSaveFileName(...)
      │ │  Ensures .gro extension
      │ │  top_path = path.stem + '.top'
      │ │
      │ ├─ WRITER: write_custom_molecule_gro_file(custom_structure, str(path))  [gromacs_writer.py:1849]
      │ │  Input: CustomMoleculeStructure
      │ │  Process:
      │ │    1. Build ordered_mols: SOL (ice+water), guest, custom
      │ │    2. wrap_molecules_into_box(positions, molecule_index, cell)
      │ │    3. For SOL: ice 3→4 expansion, water pass-through (MW recomputed)
      │ │    4. For guest: detect type, reorder, get_hydrate_guest_residue_name
      │ │    5. For custom: use moleculetype_name[:5] as res_name
      │ │    6. Write box vectors
      │ │
      │ ├─ WRITER: write_custom_molecule_top_file(custom_structure, str(top_path))  [gromacs_writer.py:2057]
      │ │  Input: CustomMoleculeStructure
      │ │  Process:
      │ │    1. Count SOL, guest, custom molecules
      │ │    2. [atomtypes]: OW_ice, HW_ice, MW + GAFF2 for guests + custom from ITP
      │ │       → parse_itp_atomtypes(custom_itp_path) → deduplicate with _written_atomtypes
      │ │    3. #include "tip4p-ice.itp"
      │ │    4. If guests: #include "{guest}_hydrate.itp"
      │ │    5. #include "{custom_itp_path.name}"
      │ │    6. [molecules]: SOL, guest, custom_mol_name (from ITP file parse)
      │ │
      │ └─ BUNDLING:
      │    → comment_out_atomtypes_in_itp(custom_itp_content)  [gromacs_writer.py:311]
      │      → Reads .itp, comments out [ atomtypes ] section lines
      │      → Writes modified content to dest
      │    → shutil.copy(get_tip4p_itp_path(), "tip4p-ice.itp")
      │    → If guests: shutil.copy({guest}_hydrate.itp, dest)
      │       On FileNotFoundError: QMessageBox.warning(...)
      │
      → On success: QMessageBox.information(...)
      → On exception: QMessageBox.critical(...)
```

### 6.3 Output Files

| File | Content |
|---|---|
| `custom_system_{moltype}_{N}molecules.gro` | Ice + water + custom molecule coordinates |
| `custom_system_{moltype}_{N}molecules.top` | Topology with SOL + custom |
| `tip4p-ice.itp` | Bundled water topology |
| `{custom_itp_name}.itp` | Custom molecule topology (atomtypes commented out) |
| `{guest}_hydrate.itp` | Guest topology (if guests present) |

---

## 7. Workflow 6: Solute Insertion → GROMACS Export

### 7.1 Insertion Phase (Tab 4)

```
User selects source and concentration, clicks "Insert"
  → MainWindow._on_insert_solutes()                          [main_window.py:982]
    │
    │ Get source:
    │   "Interface" → self._current_interface_result
    │   "Custom Molecule" → self._current_custom_molecule_result (full CustomMoleculeStructure)
    │
    → config = solute_panel.get_configuration()              → SoluteConfig
    │
    → SoluteInserter(config)                                 [solute_inserter.py:39]
    → inserter.insert_solutes(interface, config)              [solute_inserter.py:611]
      │
      │ Process:
      │  1. Validate concentration >= 0
      │  2. Calculate liquid volume: water_nmolecules * 0.0299 nm³
      │  3. Calculate molecule count: concentration * volume_L * AVOGADRO
      │  4. Load solute template: _load_solute_template(solute_type)
      │     → parse_itp_file("{solute_type}.itp")
      │     → _generate_ch4_coordinates() or _generate_thf_coordinates()
      │  5. Build existing_tree: _build_existing_atoms_tree(structure, exclude_water=True)
      │  6. Get liquid region bounds (min/max coordinates)
      │  7. For each molecule (up to max_attempts):
      │     - Random position in liquid bounds
      │     - Random rotation
      │     - Rotate template, translate
      │     - Check overlap: _check_solute_overlap()
      │     - If valid: add to placed, rebuild tree
      │  8. Register: registry.register_liquid_solute(solute_type) → "CH4_L" / "THF_L"
      │  9. _remove_overlapping_water(structure, all_solute_positions, min_separation)
      │     → Build KDTree from solute atoms
      │     → Remove overlapping water molecules from interface
      │     → Preserve custom molecule attributes on modified interface
      │  10. Return SoluteStructure(
      │       positions, atom_names, cell, solute_type, n_molecules,
      │       molecule_indices, registry, interface_structure=modified_interface,
      │       custom_molecule_count, custom_molecule_positions, ...  ← propagated
      │     )
      │
    → self._current_solute_result = solute_structure
    → solute_panel.solute_viewer.render_solute(solute_structure)
    → ion_panel.set_solute_structure(solute_structure)        → enables "Solute" source
```

### 7.2 Export Phase (Tab 4)

```
User clicks "Export Solute..." (Ctrl+L) or Ctrl+S on Tab 4
  → MainWindow._on_export_solute_gromacs()                   [main_window.py:1728]
    │ Guard: self._current_solute_result must exist
    │
    → self._solute_gromacs_exporter.export_solute_gromacs(solute_structure)  [export.py:46]
      │
      │ ┌─ Default filename: solute_{type}_{N}molecules.gro
      │ │  QFileDialog.getSaveFileName(...)
      │ │  Ensures .gro extension
      │ │  top_path = path.stem + '.top'
      │ │
      │ ├─ WRITER: write_solute_gro_file(solute_structure, str(path))  [gromacs_writer.py:2188]
      │ │  Input: SoluteStructure
      │ │  Process:
      │ │    1. Build ordered_mols from interface: SOL, guest, custom, solute
      │ │    2. Wrap interface positions (molecule-aware or atom-wise fallback)
      │ │    3. Write SOL (ice 3→4 expansion, water pass-through)
      │ │    4. Write guests (detect, reorder, hydrate residue name)
      │ │    5. Write custom molecules (from solute_structure.custom_molecule_*)
      │ │    6. Write solute molecules (from solute_structure.positions/atom_names)
      │ │       - Uses registry for residue name: CH4_L / THF_L
      │ │
      │ ├─ WRITER: write_solute_top_file(solute_structure, str(top_path))  [gromacs_writer.py:2504]
      │ │  Input: SoluteStructure
      │ │  Process:
      │ │    1. Count: SOL (from interface molecule_index or nmolecules)
      │ │    2. [atomtypes]: TIP4P-ICE + GAFF2 for guests/solutes + custom from ITP
      │ │    3. #include "tip4p-ice.itp"
      │ │    4. If guests: #include "{guest}_hydrate.itp"
      │ │    5. If custom: #include "{custom_itp_name}"
      │ │    6. If solutes: #include "{solute}_liquid.itp"
      │ │    7. [molecules]: SOL, guest, custom, solute (CH4_L / THF_L)
      │ │
      │ └─ BUNDLING:
      │    → shutil.copy(get_tip4p_itp_path(), "tip4p-ice.itp")
      │    → If guests: shutil.copy({guest}_hydrate.itp) [with FileNotFoundError handling]
      │    → Solute ITP: read {solute}_liquid.itp from quickice/data/,
      │      comment_out_atomtypes_in_itp(content), write to dest
      │    → If custom: read custom_itp_path, comment_out_atomtypes, write to dest
      │
      → On success: QMessageBox.information(...)
      → On exception: QMessageBox.critical(...)
```

### 7.3 Output Files

| File | Content |
|---|---|
| `solute_{type}_{N}molecules.gro` | Ice + water + guests + custom + solute coordinates |
| `solute_{type}_{N}molecules.top` | Topology with SOL + guest + custom + solute |
| `tip4p-ice.itp` | Bundled water topology |
| `{guest}_hydrate.itp` | Guest topology (if present) |
| `{solute}_liquid.itp` | Solute topology (atomtypes commented out) |
| `{custom_itp_name}.itp` | Custom topology (if present, atomtypes commented out) |

---

## 8. Workflow 7: Ion Insertion → GROMACS Export

### 8.1 Insertion Phase (Tab 5)

```
User selects source and concentration, clicks "Insert Ions"
  → MainWindow._on_insert_ions()                             [main_window.py:820]
    │
    │ Get source and interface:
    │   "Interface" → self._current_interface_result
    │   "Solute" → self._current_solute_result.interface_structure
    │     + Set interface.solute_type/positions/atom_names/n_molecules/molecule_indices/registry
    │     + Custom molecule info preserved automatically by solute_inserter._remove_overlapping_water()
    │   "Custom Molecule" → self._current_custom_molecule_result.interface_structure
    │     + Set interface.custom_molecule_positions/atom_names/count/moleculetype/gro_path/itp_path
    │
    → config = ion_panel.get_configuration()                 → IonConfig
    → liquid_volume = ion_panel.get_liquid_volume()
    → concentration = config.concentration_molar
    │
    → insert_ions(interface, concentration, volume_arg)      [ion_inserter.py:549]
      │
      │ Internal flow:
      │ → IonInserter(config, seed)
      │ → calculate_ion_pairs(concentration, volume_nm3)
      │   Formula: N = C_M × V_L × NA (V_L = nm³ × 1e-24)
      │   Returns: integer number of ion pairs
      │ → replace_water_with_ions(structure, ion_pairs)
      │   Process:
      │     1. Build molecule_index from structure if empty
      │     2. Select random water molecules (ion_pairs * 2)
      │     3. Build KDTree from ice+guest atoms (NOT water!)
      │     4. For each selected water:
      │        - Check min distance to ice/guest tree (< MIN_SEPARATION → skip)
      │        - Check min distance to ion tree (< MIN_SEPARATION → skip)
      │        - Alternating: even → NA, odd → CL
      │     5. Ensure charge neutrality: na_count == cl_count
      │        - Remove excess ions from end
      │     6. Build new positions: non-replaced + ions
      │     7. Preserve all solute/guest/custom attributes from input
      │     8. Return IonStructure
      │
    → self._current_ion_result = ion_structure
    → ion_panel.ion_viewer.set_interface_structure(interface)
    → ion_panel.ion_viewer.set_ion_structure(ion_structure)
    → If source == "Solute": render solute actors
    → If source == "Custom Molecule": render custom molecules
```

### 8.2 Export Phase (Tab 5)

```
User clicks "Export Ion..." (Ctrl+J) or Ctrl+S on Tab 5
  → MainWindow._on_export_ion_gromacs()                      [main_window.py:1696]
    │ Guard: self._current_ion_result must exist
    │
    → self._ion_gromacs_exporter.export_ion_gromacs(ion_structure)  [export.py:279]
      │
      │ ┌─ Default filename: ions_{na}na_{cl}cl.gro (with solute suffix if present)
      │ │  QFileDialog.getSaveFileName(...)
      │ │  Ensures .gro extension
      │ │  top_path = path.stem + '.top'
      │ │
      │ ├─ WRITER: write_ion_gro_file(ion_structure, str(path))  [gromacs_writer.py:1310]
      │ │  Input: IonStructure
      │ │  Process:
      │ │    1. Build ordered_mols in 6 passes:
      │ │       Pass 1: SOL (ice+water from molecule_index)
      │ │       Pass 2: guest (from molecule_index)
      │ │       Pass 3: custom (from custom_molecule_count + custom_molecule_positions)
      │ │       Pass 4: solute (from solute_n_molecules + solute_positions/molecule_indices)
      │ │       Pass 5: NA (from molecule_index)
      │ │       Pass 6: CL (from molecule_index)
      │ │    2. Count total atoms (ice 3→4 expansion)
      │ │    3. wrap_molecules_into_box(ion_structure.positions, molecule_index, cell)
      │ │    4. Write each molecule type with correct residue name:
      │ │       - SOL: res_name="SOL", ice 3→4 expansion, water MW recomputed
      │ │       - guest: detect type, hydrate residue name, reorder atoms
      │ │       - custom: moleculetype_name[:5] as res_name, from custom_molecule_positions
      │ │       - solute: registry-based name (CH4_L/THF_L), from solute_positions
      │ │       - NA: res_name="NA", 1 atom
      │ │       - CL: res_name="CL", 1 atom
      │ │    5. Write box vectors
      │ │
      │ ├─ WRITER: write_ion_top_file(ion_structure, str(top_path))  [gromacs_writer.py:1635]
      │ │  Input: IonStructure
      │ │  Process:
      │ │    1. Count: SOL, guest, custom, solute, NA, CL
      │ │    2. Detect guest type from atom names
      │ │    3. Parse custom moleculetype name from ITP (Bug 2 fix)
      │ │    4. Determine GAFF2 atomtype needs (Bug 1 fix)
      │ │    5. [atomtypes]: TIP4P-ICE + Madrid2019 ions + GAFF2 for guests/solutes
      │ │       + custom from ITP with deduplication (Bug 3 fix)
      │ │    6. #include directives:
      │ │       - "tip4p-ice.itp"
      │ │       - "{guest}_hydrate.itp" (if guests)
      │ │       - "{custom_itp_name}" (if custom)
      │ │       - "{solute}_liquid.itp" (if solutes)
      │ │       - "ion.itp"
      │ │    7. [molecules]: SOL, guest, custom, solute, NA, CL
      │ │
      │ ├─ ION ITP: write_ion_itp(ion_itp_path, na_count, cl_count)  [gromacs_ion_export.py:81]
      │ │  → generate_ion_itp(na_count, cl_count)
      │ │  Content:
      │ │    [ moleculetype ] NA 1
      │ │    [ atoms ] 1 NA 1 NA NA 1 0.85 22.9898
      │ │    [ moleculetype ] CL 1
      │ │    [ atoms ] 1 CL 1 CL CL 1 -0.85 35.453
      │ │
      │ └─ BUNDLING:
      │    → shutil.copy(get_tip4p_itp_path(), "tip4p-ice.itp")
      │    → If guests: shutil.copy({guest}_hydrate.itp) [with FileNotFoundError handling]
      │    → If solutes: read {solute}_liquid.itp, comment atomtypes, write to dest
      │    → If custom: read custom_itp_path, comment atomtypes, write to dest
      │
      → On success: QMessageBox.information(...)
      → On exception: QMessageBox.critical(...)
```

### 8.3 Output Files

| File | Content |
|---|---|
| `ions_{na}na_{cl}cl.gro` | Ice + water + guests + custom + solutes + NA + CL coordinates |
| `ions_{na}na_{cl}cl.top` | Topology with all molecule types |
| `tip4p-ice.itp` | Bundled water topology |
| `ion.itp` | NA + CL molecule definitions (Madrid2019) |
| `{guest}_hydrate.itp` | Guest topology (if present) |
| `{solute}_liquid.itp` | Solute topology (if present, atomtypes commented) |
| `{custom_itp_name}.itp` | Custom topology (if present, atomtypes commented) |

---

## 9. Workflow 8: Cross-Tab Chain → GROMACS Export

### 8a. Full Chain: Interface → Custom → Solute → Ion → GROMACS Export

```
┌─────────────────────────────────────────────────────────────────┐
│ Tab 0 (Ice): User generates ice candidates                     │
│   GenerationWorker.run() → ranked_candidates_ready signal      │
│   MainWindow._on_candidates_ready() stores self._current_result │
└──────────────────┬──────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│ Tab 2 (Interface): User generates interface from candidate      │
│   InterfaceGenerationWorker.run() → generate_interface()        │
│   MainWindow._on_interface_generation_complete(result)          │
│   Stores self._current_interface_result = result                │
│   → Updates: ion_panel liquid_vol, solute_panel liquid_vol     │
│   → Updates: custom_molecule_panel.set_interface_structure()    │
└──────────────────┬──────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│ Tab 3 (Custom): User uploads .gro/.itp, places molecules       │
│   CustomMoleculeWorker.run() → CustomMoleculeInserter           │
│   → place_random() or place_custom()                            │
│   → _remove_overlapping_water() → modified InterfaceStructure   │
│   → Returns CustomMoleculeStructure                             │
│   MainWindow._on_custom_finished(result)                         │
│   Stores self._current_custom_molecule_result = result          │
│   → Passes to: solute_panel.set_custom_molecule_structure()     │
│   → Passes to: ion_panel.set_custom_molecule_structure()        │
└──────────────────┬──────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│ Tab 4 (Solute): User selects source="Custom Molecule", inserts │
│   SoluteInserter(config).insert_solutes(custom_structure, conf) │
│   → Uses CustomMoleculeStructure as input (not just interface)  │
│   → _remove_overlapping_water() preserves custom mol attributes │
│   → Returns SoluteStructure                                     │
│     SoluteStructure carries:                                    │
│       - interface_structure (modified: ice+water, water reduced) │
│       - custom_molecule_count, custom_molecule_positions, etc.  │
│       - solute positions, registry (CH4_L / THF_L)             │
│   Stores self._current_solute_result = solute_structure         │
│   → Passes to: ion_panel.set_solute_structure()                 │
└──────────────────┬──────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│ Tab 5 (Ion): User selects source="Solute", inserts ions        │
│   interface = solute_structure.interface_structure               │
│   + Sets: interface.solute_type/positions/atom_names/etc.       │
│   insert_ions(interface, concentration, volume)                  │
│   → IonInserter.replace_water_with_ions()                       │
│   → Returns IonStructure carrying:                              │
│     - All SOL (ice+water), guest, solute, custom attributes     │
│     - na_count, cl_count                                        │
│   Stores self._current_ion_result = ion_structure               │
└──────────────────┬──────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│ Export: User clicks Ctrl+S on Tab 5                            │
│   → _on_export_current_tab() → _on_export_ion_gromacs()        │
│   → IonGROMACSExporter.export_ion_gromacs(ion_structure)        │
│   → write_ion_gro_file(): 6-pass ordered molecule write        │
│   → write_ion_top_file(): full topology with all includes       │
│   → write_ion_itp(): NA + CL Madrid2019 definitions            │
│   → Bundle: tip4p-ice.itp + ion.itp + guest/solute/custom ITPs │
└─────────────────────────────────────────────────────────────────┘
```

**Data propagation through the chain:**

| Step | Custom Molecule Data | Solute Data | Source |
|---|---|---|---|
| CustomMoleculeStructure | positions, atom_names, count, moleculetype, gro/itp paths | — | Tab 3 output |
| SoluteStructure | `custom_molecule_*` fields propagated from interface | positions, atom_names, n_molecules, registry | Tab 4 output |
| IonStructure | `custom_molecule_*` fields propagated from input interface | `solute_*` fields propagated from input interface | Tab 5 output |

### 8b. Short Chain: Interface → Custom → Ion (skip Solute)

Same as above but skipping Tab 4. When user selects "Custom Molecule" source on Ion tab:

```
MainWindow._on_insert_ions():
  → current_source == "Custom Molecule"
  → custom_structure = self._current_custom_molecule_result
  → interface = custom_structure.interface_structure
  → Sets: interface.custom_molecule_positions, atom_names, count, moleculetype, gro_path, itp_path
  → insert_ions(interface, concentration, volume)
    → IonInserter preserves custom molecule attributes from interface
    → Returns IonStructure (no solute_* fields populated)
```

---

## 10. Workflow 9: GROMACS Export (Tab-Specific Paths)

### Unified Export Router (Ctrl+S)

```
User presses Ctrl+S
  → MainWindow._on_export_current_tab()                      [main_window.py:1556]
    → current_idx = self.tab_widget.currentIndex()
    │
    │ if TabIndex.ICE (0):       → _on_export_gromacs()
    │ if TabIndex.HYDRATE (1):    → _on_export_hydrate_gromacs()
    │ if TabIndex.INTERFACE (2):  → _on_export_interface_gromacs()
    │ if TabIndex.SOLUTE (4):     → _on_export_solute_gromacs()
    │ if TabIndex.CUSTOM (3):     → _on_export_custom_molecule_gromacs()
    │ if TabIndex.ION (5):        → _on_export_ion_gromacs()
    │ else:                        → QMessageBox.warning("Unknown Tab")
```

### Export As... Menu Paths

```
File → Export As → Export Ice... (Ctrl+G)           → _on_export_gromacs()
File → Export As → Export Hydrate... (Ctrl+H)        → _on_export_hydrate_gromacs()
File → Export As → Export Interface... (Ctrl+I)      → _on_export_interface_gromacs()
File → Export As → Export Solute... (Ctrl+L)          → _on_export_solute_gromacs()
File → Export As → Export Custom Molecule... (Ctrl+M) → _on_export_custom_molecule_gromacs()
File → Export As → Export Ion... (Ctrl+J)             → _on_export_ion_gromacs()
```

---

## 11. Core GROMACS Writer Functions

All writer functions are in `quickice/output/gromacs_writer.py` unless noted.

### 11.1 Position Wrapping

| Function | Signature | Purpose |
|---|---|---|
| `wrap_positions_into_box()` | `(positions: ndarray, cell: ndarray) → ndarray` | Wraps each atom independently into [0, box_size) |
| `wrap_molecules_into_box()` | `(positions, molecule_index, cell) → ndarray` | Wraps molecules as whole units (unwrap PBC split, then wrap center) |

### 11.2 Virtual Site Computation

```python
def compute_mw_position(o_pos, h1_pos, h2_pos) → ndarray   [line 595]
    # MW = O + α*(H1-O) + α*(H2-O)
    # α = 0.13458335 (TIP4P-ICE specific)
```

### 11.3 GRO File Writers

| Function | Line | Input | Molecule Order in .gro |
|---|---|---|---|
| `write_gro_file()` | 427 | `Candidate` | SOL (all ice, 3→4 expansion) |
| `write_interface_gro_file()` | 615 | `InterfaceStructure` | SOL (ice→water), guests |
| `write_multi_molecule_gro_file()` | 1055 | `positions, molecule_index, cell` | Follows molecule_index order |
| `write_ion_gro_file()` | 1310 | `IonStructure` | SOL, guest, custom, solute, NA, CL |
| `write_custom_molecule_gro_file()` | 1849 | `CustomMoleculeStructure` | SOL, guest, custom |
| `write_solute_gro_file()` | 2188 | `SoluteStructure` | SOL, guest, custom, solute |

### 11.4 TOP File Writers

| Function | Line | Input | [molecules] Order |
|---|---|---|---|
| `write_top_file()` | 521 | `Candidate` | SOL |
| `write_interface_top_file()` | 947 | `InterfaceStructure` | SOL, guest |
| `write_multi_molecule_top_file()` | 1152 | `molecule_index, itp_files, registry` | First-appearance order |
| `write_ion_top_file()` | 1635 | `IonStructure` | SOL, guest, custom, solute, NA, CL |
| `write_custom_molecule_top_file()` | 2057 | `CustomMoleculeStructure` | SOL, guest, custom |
| `write_solute_top_file()` | 2504 | `SoluteStructure` | SOL, guest, custom, solute |

### 11.5 ITP File Handling

| Function | Signature | Purpose |
|---|---|---|
| `get_tip4p_itp_path()` | `() → Path` | Locate `quickice/data/tip4p-ice.itp` |
| `_get_guest_itp_path()` | `(guest_type: str) → Path` | Locate `quickice/data/{guest}.itp` |
| `_get_hydrate_guest_itp_path()` | `(guest_type: str) → Path` | Locate `quickice/data/{guest}_hydrate.itp` |
| `comment_out_atomtypes_in_itp()` | `(itp_content: str) → str` | Comment out `[ atomtypes ]` section lines |
| `parse_itp_residue_name()` | `(itp_path) → Optional[str]` | Read residue name from `[ atoms ]` section |
| `parse_itp_atomtypes()` | `(itp_path) → list[tuple]` | Parse `[ atomtypes ]` section for custom molecules |
| `detect_guest_type_from_atoms()` | `(atom_names) → str|None` | Detect ch4/thf/co2/h2 from atom composition |
| `reorder_guest_atoms()` | `(atom_names, mol_type) → (names, mapping)` | Reorder GenIce2 atom order to .itp canonical order |
| `get_guest_residue_name()` | `(guest_type) → str` | Residue name from standard .itp (CH4, THF) |
| `get_hydrate_guest_residue_name()` | `(guest_type) → str` | Residue name from hydrate .itp (CH4_H, THF_H) |

### 11.6 Ion ITP Writer

In `quickice/structure_generation/gromacs_ion_export.py`:

| Function | Signature | Purpose |
|---|---|---|
| `generate_ion_itp()` | `(na_count, cl_count) → str` | Generate ion.itp content with NA+CL moleculetypes |
| `write_ion_itp()` | `(output_path, na_count, cl_count) → None` | Write ion.itp to file |
| `generate_itp_include_section()` | `(na_count, cl_count) → str` | Generate [molecules] section for ions |
| `add_ion_molecules_to_topology()` | `(top_path, na_count, cl_count) → None` | Post-hoc add ions to existing .top |

---

## 12. Data Structures Reference

All data structures in `quickice/structure_generation/types.py`.

### 12.1 MoleculeIndex

```python
@dataclass
class MoleculeIndex:
    start_idx: int    # First atom index in positions array (0-based)
    count: int        # Number of atoms in this molecule
    mol_type: str      # 'ice', 'water', 'na', 'cl', 'ch4', 'thf', 'guest', 'custom', 'solute'
```

### 12.2 Candidate (Tab 0 output)

```python
@dataclass
class Candidate:
    positions: np.ndarray     # (N_atoms, 3) nm — ice: 3 atoms/mol (O, H, H)
    atom_names: list[str]     # ["O", "H", "H", ...]
    cell: np.ndarray          # (3, 3) nm, ROW vectors
    nmolecules: int           # Number of water molecules
    phase_id: str             # "ice_ih", "ice_ic", etc.
    seed: int
    metadata: dict
```

### 12.3 InterfaceStructure (Tab 2 output)

```python
@dataclass
class InterfaceStructure:
    positions: np.ndarray     # (N, 3) nm — ORDER: ice → water → guests
    atom_names: list[str]
    cell: np.ndarray          # (3, 3) nm
    ice_atom_count: int       # Marks split: positions[0:ice_atom_count] = ice
    water_atom_count: int     # positions[ice_atom_count:ice+water] = water
    ice_nmolecules: int
    water_nmolecules: int
    mode: str                 # "slab", "pocket", "piece"
    report: str
    guest_atom_count: int     # positions[ice+water:] = guests
    molecule_index: list[MoleculeIndex]
    guest_nmolecules: int
```

### 12.4 CustomMoleculeStructure (Tab 3 output)

```python
@dataclass
class CustomMoleculeStructure:
    positions: np.ndarray     # ALL atoms: ice + water + guests + custom
    atom_names: list[str]
    cell: np.ndarray
    molecule_index: list[MoleculeIndex]  # ice, water, guest, custom entries
    ice_atom_count: int
    water_atom_count: int
    custom_molecule_atom_count: int
    guest_atom_count: int
    config: CustomMoleculeConfig
    moleculetype_name: str     # "MOL", "MOL_1", etc.
    gro_path: Path
    itp_path: Path
    residue_name: str
    custom_molecule_count: int
    interface_structure: InterfaceStructure  # Modified (water removed)
```

### 12.5 SoluteStructure (Tab 4 output)

```python
@dataclass
class SoluteStructure:
    positions: np.ndarray         # SOLUTE-ONLY positions (not the full system!)
    atom_names: list[str]         # Solute atom names only
    cell: np.ndarray
    solute_type: str              # "CH4" or "THF"
    n_molecules: int
    molecule_indices: list[tuple[int, int]]  # (start, end) in solute positions
    registry: MoleculetypeRegistry
    interface_structure: InterfaceStructure    # Modified (water reduced)
    # Custom molecule propagation:
    custom_molecule_count: int
    custom_molecule_atom_count: int
    custom_molecule_positions: np.ndarray | None
    custom_molecule_atom_names: list[str] | None
    custom_molecule_moleculetype: str
    custom_gro_path: Any
    custom_itp_path: Any
```

### 12.6 IonStructure (Tab 5 output)

```python
@dataclass
class IonStructure:
    positions: np.ndarray     # Water + ions (NOT separate from interface)
    atom_names: list[str]
    cell: np.ndarray
    molecule_index: list[MoleculeIndex]  # ice, water, guest, na, cl
    na_count: int
    cl_count: int
    report: str
    # Guest propagation:
    guest_nmolecules: int
    guest_atom_count: int
    # Solute propagation:
    solute_type: str
    solute_positions: np.ndarray | None
    solute_atom_names: list[str] | None
    solute_n_molecules: int
    solute_molecule_indices: list[tuple[int, int]] | None
    solute_registry: MoleculetypeRegistry | None
    # Custom molecule propagation:
    custom_molecule_count: int
    custom_molecule_atom_count: int
    custom_molecule_positions: np.ndarray | None
    custom_molecule_atom_names: list[str] | None
    custom_molecule_moleculetype: str
    custom_gro_path: Any
    custom_itp_path: Any
```

---

## 13. Error Handling Paths

### 13.1 Generation Phase Errors

| Error | Source | Handler |
|---|---|---|
| `InterfaceGenerationError` | `validate_interface_config()` / `assemble_*()` | `InterfaceGenerationWorker.run()` → `error.emit()` → `MainWindow._on_interface_generation_error()` → `QMessageBox.critical()` |
| `InsertionError` | `CustomMoleculeInserter.place_random()` | `CustomMoleculeWorker.run()` → `error.emit()` → `custom_molecule_panel.log_message(f"Error: {msg}")` |
| Generic exception | Any worker | `worker.run()` except block → `error.emit()` → `QMessageBox.critical()` |

### 13.2 Export Phase Errors

| Error | Source | Handler |
|---|---|---|
| No structure generated | `_on_export_*_gromacs()` guard | `QMessageBox.warning("No Data/Interface/Ions/etc.")` |
| User cancels save dialog | `QFileDialog.getSaveFileName()` returns empty | `return False` (silent) |
| Write failure | `write_*_gro_file()` / `write_*_top_file()` exceptions | `try/except` in exporter → `QMessageBox.critical("Export Error", f"Failed: {e}")` |
| Guest ITP not found | `_get_hydrate_guest_itp_path()` raises `FileNotFoundError` | `QMessageBox.warning("Missing Guest ITP")` — .top still references it but file not bundled |
| Invalid concentration | `_on_insert_ions()` concentration <= 0 | `QMessageBox.warning("Invalid Concentration")` |
| No water for ions | `IonInserter.replace_water_with_ions()` | Returns `IonStructure` with 0 ions, report explains why |

### 13.3 Cross-Tab Data Dependency Errors

| Missing Dependency | Tab Affected | Handler |
|---|---|---|
| No ice candidates | Tab 2 (Interface) | `QMessageBox.warning("No candidates available")` |
| No hydrate result | Tab 2 (Interface from hydrate) | `QMessageBox.warning("No Hydrate")` |
| No interface result | Tab 3 (Custom) | `log_message("Error: No interface structure available")` |
| No interface/custom result | Tab 4 (Solute) | `log_message("Error: No interface/custom molecule structure available")` |
| No solute/custom/interface result | Tab 5 (Ion) | `QMessageBox.warning("No Interface/Solute/Custom Molecule Structure")` |

---

## 14. File Output Summary

### 14.1 Bundled ITP Files (from `quickice/data/`)

| File | Moleculetype | Purpose |
|---|---|---|
| `tip4p-ice.itp` | SOL | TIP4P-ICE water model (Abascal et al. 2005) |
| `ch4_hydrate.itp` | CH4_H | Methane guest in hydrate cages |
| `thf_hydrate.itp` | THF_H | THF guest in hydrate cages |
| `ch4_liquid.itp` | CH4_L | Liquid methane solute |
| `thf_liquid.itp` | THF_L | Liquid THF solute |
| `ch4.itp` | CH4 | Standard methane (used by multi-molecule writer) |
| `thf.itp` | THF | Standard THF (used by multi-molecule writer) |

### 14.2 Generated ITP Files

| File | Source | Content |
|---|---|---|
| `ion.itp` | `write_ion_itp()` | NA and CL moleculetype definitions (Madrid2019) |
| `{custom_name}.itp` | User's custom .itp | User-provided molecule definition (atomtypes commented out) |

### 14.3 Standard GRO File Format

```
{title line}
{total_atoms:5d}
{res_num:5d}{res_name:<5s}{atom_name:>5s}{atom_num:5d}{x:8.3f}{y:8.3f}{z:8.3f}
...
{box_xx:10.5f}{box_yy:10.5f}{box_zz:10.5f}{box_xy:10.5f}{box_xz:10.5f}{box_yx:10.5f}{box_yz:10.5f}{box_zx:10.5f}{box_zy:10.5f}
```

**Number wrapping:** Atom and residue numbers wrap at 100000 (GROMACS convention for large systems).

### 14.4 Standard TOP File Format

```
; Generated by QuickIce
[ defaults ]
; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ
1        2          yes        0.5     0.8333

[ atomtypes ]
; name  bond_type  atomic_number  mass  charge  ptype  V(nm)  W(kJ/mol)
OW_ice   OW_ice    8    15.9994  0.0  A  0.31668e-3  0.88216e-6
HW_ice   HW_ice    1     1.0080  0.0  A  0.0         0.0
MW       MW        0     0.0000  0.0  V  0.0         0.0
[+ Madrid2019 ions + GAFF2 guest/solute types + custom types]

; Molecule definitions
#include "tip4p-ice.itp"
#include "{guest}_hydrate.itp"     [if guests]
#include "{custom_itp_name}"       [if custom molecules]
#include "{solute}_liquid.itp"    [if solutes]
#include "ion.itp"                 [if ions]

[ system ]
; Name
{system_name}

[ molecules ]
; Compound        #mols
SOL              {sol_count}
{guest_res_name} {guest_count}   [if guests]
{custom_name}    {custom_count}   [if custom]
{solute_name}    {solute_count}  [if solutes]
NA               {na_count}      [if ions]
CL               {cl_count}      [if ions]
```

### 14.5 Moleculetype Naming Convention

| Context | Name | Source |
|---|---|---|
| Ice water (TIP4P-ICE) | SOL | `tip4p-ice.itp` |
| Hydrate guest (CH4) | CH4_H | `ch4_hydrate.itp` |
| Hydrate guest (THF) | THF_H | `thf_hydrate.itp` |
| Liquid solute (CH4) | CH4_L | `ch4_liquid.itp` |
| Liquid solute (THF) | THF_L | `thf_liquid.itp` |
| Na+ ion | NA | `ion.itp` (Madrid2019) |
| Cl- ion | CL | `ion.itp` (Madrid2019) |
| Custom molecule | From ITP `[moleculetype]` | User-provided .itp |

---

*Flow trace analysis: 2026-06-12*
