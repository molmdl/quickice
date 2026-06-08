# GROMACS Export Flow Trace

**Analysis Date:** 2026-06-08
**Scope:** Read-only trace of every function call from user action to GROMACS file output
**Tab Structure:** Ice(0) → Hydrate(1) → Interface(2) → Custom(3) → Solute(4) → Ion(5)

---

## Tab Layout & TabIndex Constants

Defined in `quickice/gui/constants.py:9-28`:

| Index | Tab Name | TabIndex Enum |
|-------|----------|---------------|
| 0 | Ice Generation | `TabIndex.ICE` |
| 1 | Hydrate Generation | `TabIndex.HYDRATE` |
| 2 | Interface Construction | `TabIndex.INTERFACE` |
| 3 | Custom Molecule | `TabIndex.CUSTOM` |
| 4 | Solute Insertion | `TabIndex.SOLUTE` |
| 5 | Ion Insertion | `TabIndex.ION` |

---

## 1. Ice Tab GROMACS Export

### 1.1 Generation Flow

```
User clicks "Generate"
  → MainWindow._on_generate_clicked()                    [gui/main_window.py:417]
    → InputPanel.validate_all()
    → InputPanel.get_temperature(), get_pressure(), get_nmolecules()
    → MainViewModel.start_generation(T, P, nmolecules)     [gui/viewmodel.py:61]
      → GenerationWorker(T, P, nmolecules)                 [gui/workers.py:55]
      → worker.moveToThread(thread)
      → thread.started → worker.run()                      [gui/workers.py:69]

worker.run():
  1. lookup_phase(T, P)                                    [phase_mapping/lookup.py]
     → Returns: phase_info dict {phase_id, phase_name, density, ...}
  2. generate_candidates(phase_info, nmolecules, n_candidates=10)  [structure_generation/generator.py:209]
     → IceStructureGenerator(phase_info, nmolecules)        [structure_generation/generator.py:43]
       → get_genice_lattice_name(phase_id)                 [structure_generation/mapper.py]
       → calculate_supercell(nmolecules, molecules_per_unit_cell)
       → generator.generate_all(n_candidates=10)
         → For each candidate:
           → _generate_single(seed)                        [structure_generation/generator.py:79]
             → safe_import('lattice', lattice_name).Lattice()
             → GenIce(lattice, density=density, reshape=supercell_matrix)
             → safe_import('molecule', 'tip3p').Molecule()  ← KEY: 3-atom TIP3P format
             → safe_import('format', 'gromacs').Format()
             → ice.generate_ice(formatter, water, depol='strict')
             → parse_gro_string(gro_string)                [structure_generation/gro_parser.py]
             → Returns: Candidate(positions, atom_names, cell, nmolecules, phase_id, seed, metadata)
  3. rank_candidates(candidates)                           [ranking/scorer.py]
     → Returns: RankingResult(ranked_candidates)

  → Worker emits finished(GenerationResult)
  → ViewModel._on_finished()                              [gui/viewmodel.py:135]
    → Emits ranked_candidates_ready(RankingResult)
  → MainWindow._on_candidates_ready(result)               [gui/main_window.py:462]
    → Stores: self._current_result = result
    → Stores: self._current_T, self._current_P
    → Updates viewer, interface panel dropdown
```

**Data structure produced:** `RankingResult.ranked_candidates[i].candidate` = `Candidate`
- `positions`: (N×3, 3) array — 3 atoms per molecule (O, H, H)
- `atom_names`: ["O", "H", "H", "O", "H", "H", ...]
- `cell`: (3, 3) row-vector cell in nm
- `nmolecules`: actual count (may differ from user request due to supercell)

### 1.2 Export Flow

```
Menu: Export → Export Ice... (Ctrl+G)
  → MainWindow._on_export_gromacs()                         [gui/main_window.py:1593]
    → Gets selected RankedCandidate from viewer
    → Gets T, P from input panel
    → GROMACSExporter.export_gromacs(ranked, T, P)          [gui/export.py:704]
      → QFileDialog.getSaveFileName(...) → filepath
      → write_gro_file(candidate, str(path))                [output/gromacs_writer.py:427]
        → KEY TRANSFORMATION: 3→4 atom expansion
        → For each molecule (3 atoms: O, H, H):
           - compute_mw_position(o_pos, h1_pos, h2_pos)     [output/gromacs_writer.py:587]
             MW = O + α*(H1-O) + α*(H2-O)  where α = 0.13458335
           - Writes 4 lines: OW, HW1, HW2, MW
        → Total atoms = nmolecules × 4 (not nmolecules × 3)
      → write_top_file(candidate, str(top_path))            [output/gromacs_writer.py:513]
        → Writes [defaults], [atomtypes], [moleculetype] SOL, [atoms], [settles],
          [virtual_sites3], [exclusions], [system], [molecules] SOL={nmolecules}
      → shutil.copy(tip4p_itp_path, itp_path)
        → Copies tip4p-ice.itp from quickice/data/

  File outputs: {phase}_{T}K_{P}MPa_c{rank}.gro, .top, tip4p-ice.itp
```

**Critical data transformation:** 3→4 atom expansion at export time
- GenIce generates TIP3P (O, H, H) = 3 atoms/mol
- GROMACS output uses TIP4P-ICE (OW, HW1, HW2, MW) = 4 atoms/mol
- MW virtual site computed on-the-fly: `MW = O + 0.13458335 * (H1-O) + 0.13458335 * (H2-O)`
- Residue name: `SOL` for all water molecules

---

## 2. Hydrate Tab GROMACS Export

### 2.1 Generation Flow

```
User configures hydrate (lattice, guest, occupancy, supercell)
  → HydratePanel.generate_requested signal
  → MainWindow._on_hydrate_generate_clicked()               [gui/main_window.py:736]
    → HydratePanel.get_configuration() → HydrateConfig
    → Stores: self._current_hydrate_config
    → Creates HydrateWorker(config)                          [gui/hydrate_worker.py:15]
    → worker.start() (QThread subclass)

HydrateWorker.run():                                         [gui/hydrate_worker.py:50]
  → HydrateStructureGenerator().generate(config)             [structure_generation/hydrate_generator.py:78]
    → _ensure_genice_import() — lazy loads GenIce2
    → _run_via_api(lattice_name, config)                     [hydrate_generator.py:128]
      → safe_import('lattice', lattice_name).Lattice()
      → GenIce(lattice, reshape=supercell_matrix)
      → safe_import('molecule', 'tip4p').Molecule()          ← KEY: 4-atom TIP4P
      → safe_import('format', 'gromacs').Format()
      → Builds guests dict from config (cage_occupancy_small/large)
      → ice.generate_ice(formatter, water, guests, depol='strict')
      → _parse_gro_result(gro_string)                        [hydrate_generator.py:220]
        → Returns: positions, cell, atom_names, residue_names, residue_seq_nums
    → _build_molecule_index(atom_names, positions, residue_names, residue_seq_nums)  [hydrate_generator.py:483]
      → Groups atoms: water(4), ch4(5), thf(13), na(1), cl(1)
      → Returns: list[MoleculeIndex]
    → Returns: HydrateStructure(positions, atom_names, cell, molecule_index, config, ...)

  → Worker emits generation_complete(HydrateStructure)
  → MainWindow._on_hydrate_generation_complete(result)        [gui/main_window.py:768]
    → Stores: self._current_hydrate_result = result
```

**Data structure produced:** `HydrateStructure`
- `positions`: (N_atoms, 3) — mixed water(4 atoms) + guests
- `molecule_index`: list[MoleculeIndex] with mol_type = "water", "ch4", "thf"
- `water_count`, `guest_count`

### 2.2 Export Flow

```
Menu: Export → Export Hydrate... (Ctrl+H)
  → MainWindow._on_export_hydrate_gromacs()                  [gui/main_window.py:1660]
    → Checks self._current_hydrate_result, self._current_hydrate_config
    → HydrateGROMACSExporter.export_hydrate(structure, config) [gui/hydrate_export.py:90]
      → QFileDialog.getSaveFileName(...)
      → write_multi_molecule_gro_file(positions, molecule_index, cell, path, ...)  [output/gromacs_writer.py:1047]
        → Uses MoleculeIndex to determine atoms per molecule type
        → For each MoleculeIndex entry:
           - Writes atoms with correct residue name from MOLECULE_TO_GROMACS
           - Reorders guest atoms (CH4: C first, not H first)
      → MoleculetypeRegistry.register_hydrate_guest(guest_type.upper())
        → CH4 → "CH4_H", THF → "THF_H"
      → write_multi_molecule_top_file(molecule_index, path, ...)  [output/gromacs_writer.py:1144]
        → Groups by mol_type, counts unique types
        → Writes [defaults], [atomtypes] for TIP4P-ICE + GAFF2
        → #include "tip4p-ice.itp", #include "{guest}_hydrate.itp"
        → [molecules] with moleculetype names from registry
      → shutil.copy(tip4p_itp_path, water_itp_dest)
      → shutil.copy(guest_itp_path, guest_itp_dest)  — e.g., ch4_hydrate.itp

  File outputs: hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro, .top, tip4p-ice.itp, {guest}_hydrate.itp
```

**Key difference from Ice export:** Hydrate already uses TIP4P (4 atoms/mol), no 3→4 expansion needed. Uses `write_multi_molecule_gro_file` instead of `write_gro_file`. Guest molecules handled via `molecule_index` and `MoleculetypeRegistry`.

---

## 3. Interface Tab GROMACS Export

### 3.1 Generation Flow (from Ice candidate)

```
User selects ice candidate in Interface panel
  → InterfacePanel.generate_requested signal (with candidate_index)
  → MainWindow._on_interface_generate(candidate_index)       [gui/main_window.py:553]
    → Gets RankingResult from ViewModel
    → Gets selected RankedCandidate → candidate (Candidate)
    → InterfacePanel.get_configuration() → dict
    → InterfaceConfig.from_dict(config_dict)                 [structure_generation/types.py:192]
    → MainViewModel.start_interface_generation(candidate, config)  [gui/viewmodel.py:175]
      → InterfaceGenerationWorker(candidate, config)          [gui/workers.py:146]
      → worker.run():
        → generate_interface(candidate, config)               [structure_generation/interface_builder.py:310]
          → validate_interface_config(config, candidate)       [interface_builder.py:26]
          → Mode routing:
            - "slab"  → assemble_slab(candidate, config)      [structure_generation/modes/slab.py]
            - "pocket" → assemble_pocket(candidate, config)    [structure_generation/modes/pocket.py]
            - "piece" → assemble_piece(candidate, config)      [structure_generation/modes/piece.py]
          → Returns: InterfaceStructure

  → Worker emits finished(InterfaceGenerationResult)
  → ViewModel emits interface_generation_complete(InterfaceStructure)
  → MainWindow._on_interface_generation_complete(result)       [gui/main_window.py:604]
    → Stores: self._current_interface_result = result
    → Updates IonPanel: set_liquid_volume(), set_interface_available(True)
    → Updates SolutePanel: set_liquid_volume(), set_interface_available(True)
    → Updates CustomMoleculePanel: set_interface_structure(result)
```

### 3.2 Generation Flow (from Hydrate candidate)

```
User selects Source=hydrate in Interface panel
  → InterfacePanel.generate_hydrate_requested signal
  → MainWindow._on_interface_hydrate_generate()              [gui/main_window.py:666]
    → Gets self._current_hydrate_result (HydrateStructure)
    → hydrate.to_candidate()                                 [structure_generation/types.py:654]
      → Iterates molecule_index — includes ALL molecules (water + guests)
      → Concatenates positions for all molecules
      → Returns: Candidate(positions=all, phase_id="hydrate_sI", nmolecules=water_count+guest_count)
    → Same flow as ice: start_interface_generation(candidate, config)
      → generate_interface() → assemble_piece() (typically)
      → Guest molecules preserved via candidate.positions + candidate.atom_names
      → InterfaceStructure.guest_atom_count and guest_nmolecules populated
```

**Data structure produced:** `InterfaceStructure`
- `positions`: (N_atoms, 3) — ice atoms first, then water, then guests (post-commit 90afe86 order)
- `atom_names`: ice names + water names + guest names
- `ice_atom_count`, `water_atom_count`, `guest_atom_count` — boundary markers
- `ice_nmolecules`, `water_nmolecules`, `guest_nmolecules`
- `molecule_index`: list[MoleculeIndex] — populated by interface modes
- `mode`: "slab" / "pocket" / "piece"

### 3.3 Export Flow

```
Menu: Export → Export Interface... (Ctrl+I)
  → MainWindow._on_export_interface_gromacs()                [gui/main_window.py:1634]
    → InterfaceGROMACSExporter.export_interface_gromacs(iface) [gui/export.py:844]
      → QFileDialog.getSaveFileName(...)
      → write_interface_gro_file(iface, str(path))            [output/gromacs_writer.py:607]
        → KEY: Detects ice atom format (3-atom vs 4-atom)
          → has_ow_in_ice = "OW" in ice_region_atom_names   [line 684]
          → atoms_per_ice_mol = 4 if has_ow_in_ice else 3   [line 686]
        → Ice molecules: if 3-atom, expand to 4-atom (MW computed)
        → Water molecules: 4-atom pass-through (MW recomputed)
        → Guest molecules: detect_guest_type_from_atoms()    [line 766]
          → reorder_guest_atoms() if ch4/thf
          → Uses get_hydrate_guest_residue_name() for residue naming
      → write_interface_top_file(iface, str(top_path))       [output/gromacs_writer.py:939]
        → [atomtypes]: TIP4P-ICE + GAFF2 for guests
        → #include "tip4p-ice.itp"
        → #include "{guest_type}_hydrate.itp" (if guests)
        → [molecules]: SOL (ice+water combined), {guest_res_name}
      → Copies tip4p-ice.itp, {guest_type}_hydrate.itp

  File outputs: interface_{mode}.gro, .top, tip4p-ice.itp, {guest}_hydrate.itp (if guests)
```

**Key branching variables:**
- `iface.guest_nmolecules > 0` — controls whether guest section is written
- `has_ow_in_ice` — controls 3→4 expansion vs pass-through for ice molecules
- `guest_type` (from `detect_guest_type_from_atoms()`) — controls which .itp is bundled

---

## 4. Custom Molecule Tab GROMACS Export

### 4.1 Generation Flow

```
User clicks Generate in Custom Molecule panel
  → CustomMoleculePanel.generate_requested signal
  → MainWindow._on_custom_generate_clicked()                 [gui/main_window.py:1091]
    → Checks for previous insertion (asks user)
    → Checks self._current_interface_result exists
    → Gets CustomMoleculeConfig from panel
    → Creates CustomMoleculeWorker(config, interface_result, gro_path, itp_path)  [gui/custom_molecule_worker.py:46]
    → Moves to QThread, starts

CustomMoleculeWorker.run():                                   [gui/custom_molecule_worker.py:67]
  → Parses GRO file: parse_gro_file(gro_path)
  → Creates CustomMoleculeInserter(config)                   [structure_generation/custom_molecule_inserter.py:46]
    → Loads template from GRO file
  → Mode routing:
    - "random" → inserter.place_random(structure, n_molecules)  [custom_molecule_inserter.py:536]
      → Builds cKDTree from ice+guest atoms (excludes water)
      → Samples random positions in liquid region
      → Random rotations via Rotation.random()
      → All-atom overlap checking with min_separation
      → _remove_overlapping_water(structure, custom_positions, min_separation)  [line 343]
        → Removes entire water molecules that overlap with custom molecules
        → Rebuilds molecule_index for new structure
      → Builds complete molecule_index: ice → water → guest → custom
      → MoleculetypeRegistry.register_custom_molecule()
      → Returns CustomMoleculeStructure
    - "custom" → inserter.place_custom(structure, positions, rotations)  [custom_molecule_inserter.py:769]
      → Same as random but with user-specified positions/rotations
      → No overlap checking (user responsibility)
      → Same _remove_overlapping_water(), same molecule_index rebuild

  → Worker emits finished(CustomMoleculeStructure)
  → MainWindow._on_custom_finished(result)                  [gui/main_window.py:1171]
    → Stores: self._current_custom_molecule_result = result
    → Passes result to SolutePanel: solute_panel.set_custom_molecule_structure(result)
    → Passes result to IonPanel: ion_panel.set_custom_molecule_structure(result)
    → Updates liquid volume in both panels
```

**Data structure produced:** `CustomMoleculeStructure`
- `positions`: (N_total, 3) — ice + water + custom (ALL atoms combined)
- `atom_names`: combined list
- `molecule_index`: list[MoleculeIndex] — ice, water, guest, custom
- `ice_atom_count`, `water_atom_count`, `custom_molecule_atom_count`
- `custom_molecule_count`: number of placed custom molecules
- `moleculetype_name`: from MoleculetypeRegistry (e.g., "CUSTOM_MOL_1")
- `gro_path`, `itp_path`: original user files
- `interface_structure`: modified InterfaceStructure after water removal

### 4.2 Export Flow

```
Menu: Export → Export Custom Molecule... (Ctrl+M)
  → MainWindow._on_export_custom_molecule_gromacs()           [gui/main_window.py:1761]
    → CustomMoleculeGROMACSExporter.export_custom_molecule_gromacs(custom_structure)  [gui/export.py:171]
      → QFileDialog.getSaveFileName(...)
      → write_custom_molecule_gro_file(custom_structure, path)  [output/gromacs_writer.py:1841]
        → Builds ordered mols: SOL(ice+water) → guest → custom
        → Ice: 3→4 expansion if 3-atom
        → Water: 4-atom pass-through (MW recomputed)
        → Custom: uses moleculetype_name as residue name (truncated 5 chars)
      → write_custom_molecule_top_file(custom_structure, top_path)  [output/gromacs_writer.py:2049]
        → Counts: sol_count, guest_count, custom_count
        → Parses custom_mol_name from ITP file (Bug 2 fix)
        → [atomtypes]: TIP4P-ICE + GAFF2 guests + custom atomtypes from ITP (deduped)
        → #include "tip4p-ice.itp", #include "{guest}_hydrate.itp", #include "{custom_itp_name}"
        → [molecules]: SOL, {guest_res}, {custom_mol_name}
      → comment_out_atomtypes_in_itp(itp_content) → writes modified ITP
      → shutil.copy(tip4p-ice.itp)
      → shutil.copy({guest}_hydrate.itp) if guests present

  File outputs: custom_system_{moltype}_{n}molecules.gro, .top, tip4p-ice.itp, {custom}.itp, {guest}_hydrate.itp (if guests)
```

---

## 5. Solute Tab GROMACS Export

### 5.1 Generation Flow

```
User clicks Insert in Solute panel
  → SolutePanel.insert_requested signal
  → MainWindow._on_insert_solutes()                          [gui/main_window.py:982]
    → Gets current_source from solute_panel:
      - "Interface" → uses self._current_interface_result
      - "Custom Molecule" → uses self._current_custom_molecule_result
    → Gets SoluteConfig from panel (concentration, solute_type)
    → Creates SoluteInserter(config)                         [structure_generation/solute_inserter.py:38]
    → inserter.insert_solutes(interface, config)             [solute_inserter.py:610]
      → Calculates liquid volume from water_nmolecules × 0.0299 nm³
      → calculate_molecule_count(concentration, volume)      [line 62]
        → N = C_M × V_L × N_A
      → _load_solute_template(solute_type)                   [line 168]
        → Parses ITP file for atom names/types
        → Generates CH4 or THF coordinates
      → Places molecules:
        → Build existing atoms tree (exclude water for replacement)
        → Sample positions in liquid region bounds
        → Random rotation, overlap check
        → _remove_overlapping_water(structure, all_positions, min_separation)  [line 342]
          → Same water removal pattern as CustomMoleculeInserter
          → Rebuilds molecule_index
          → Preserves custom molecule attributes if present in input
        → Registers with MoleculetypeRegistry: register_liquid_solute(solute_type)
          → CH4 → "CH4_L", THF → "THF_L"
      → Returns SoluteStructure

  → Stores: self._current_solute_result = result
  → Passes to IonPanel: ion_panel.set_solute_structure(solute_structure)
```

**Data structure produced:** `SoluteStructure`
- `positions`: (N_solute_atoms, 3) — solute molecule positions only
- `atom_names`: solute atom names
- `cell`: from interface
- `solute_type`: "CH4" or "THF"
- `n_molecules`: count placed
- `molecule_indices`: list[(start, end)] tuples in solute positions
- `registry`: MoleculetypeRegistry with liquid_solute registered
- `interface_structure`: modified InterfaceStructure (after water removal)
  - Carries `custom_molecule_*` attributes if source was CustomMoleculeStructure

### 5.2 Export Flow

```
Menu: Export → Export Solute... (Ctrl+L)
  → MainWindow._on_export_solute_gromacs()                   [gui/main_window.py:1728]
    → SoluteGROMACSExporter.export_solute_gromacs(solute_structure)  [gui/export.py:46]
      → QFileDialog.getSaveFileName(...)
      → write_solute_gro_file(solute_structure, path)         [output/gromacs_writer.py:2180]
        → Gets interface = solute_structure.interface_structure
        → Builds ordered mols: SOL(ice+water) → guest → custom → solute
        → FALLBACK when molecule_index empty: builds synthetic entries from counts  [line 2205]
        → Ice: 3→4 expansion
        → Water: 4-atom pass-through (MW recomputed)
        → Custom molecules: from solute_structure.custom_molecule_* attrs
        → Solute molecules: from solute_structure.positions
      → write_solute_top_file(solute_structure, top_path)      [output/gromacs_writer.py:—]
        → [molecules] order: SOL, {guest_res}, {custom_mol}, {solute_res}
      → Copies: tip4p-ice.itp
      → Copies: {guest}_hydrate.itp (if guests > 0)
      → Copies: {solute}_liquid.itp (with atomtypes commented)
      → Copies: custom ITP (if custom_molecule_count > 0)

  File outputs: solute_{type}_{n}molecules.gro, .top, tip4p-ice.itp, {guest}_hydrate.itp, {solute}_liquid.itp, {custom}.itp
```

---

## 6. Ion Tab GROMACS Export

### 6.1 Generation Flow

```
User clicks Insert Ions in Ion panel
  → IonPanel.insert_requested signal
  → MainWindow._on_insert_ions()                             [gui/main_window.py:820]
    → Gets current_source from ion_panel:
      - "Interface" → self._current_interface_result
      - "Solute" → self._current_solute_result.interface_structure
        → Also copies solute attributes to interface:
          interface.solute_type, interface.solute_positions, ...
          interface.solute_n_molecules, interface.solute_molecule_indices, ...
          interface.solute_registry
      - "Custom Molecule" → self._current_custom_molecule_result.interface_structure
        → Also copies custom molecule attributes to interface:
          interface.custom_molecule_positions, interface.custom_molecule_atom_names
          interface.custom_molecule_count, interface.custom_molecule_moleculetype
          interface.custom_gro_path, interface.custom_itp_path
    → Gets concentration from IonConfig
    → insert_ions(interface, concentration, volume)          [structure_generation/ion_inserter.py:548]
      → IonInserter(config)                                   [ion_inserter.py:41]
      → calculate_ion_pairs(concentration, volume)             [line 138]
        → N = C_M × V_L × N_A
      → replace_water_with_ions(structure, ion_pairs)         [line 173]
        → KEY: Builds molecule_index if empty (from _build_molecule_index_from_structure)  [line 62]
        → Selects 2×ion_pairs water molecules randomly
        → Replaces with alternating Na+/Cl- ions
        → Overlap checking against ice+guest molecules (NOT water)
        → MW virtual sites excluded from overlap check
        → Charge neutrality enforced: removes excess NA or CL
        → Preserves guest/solute/custom molecule attributes from input
        → Returns: IonStructure

  → Stores: self._current_ion_result = ion_structure
```

**Data structure produced:** `IonStructure`
- `positions`: (N_atoms, 3) — ALL atoms (ice + water + ions, no guests/solutes/custom)
  - Guests/solutes/custom stored separately in dedicated attributes
- `atom_names`: for all atoms in molecule_index
- `molecule_index`: list[MoleculeIndex] — ice, water, guest, na, cl
- `na_count`, `cl_count`
- `guest_nmolecules`, `guest_atom_count` — from source
- `solute_type`, `solute_positions`, `solute_atom_names`, `solute_n_molecules`, `solute_molecule_indices`, `solute_registry`
- `custom_molecule_count`, `custom_molecule_positions`, `custom_molecule_atom_names`, `custom_molecule_moleculetype`, `custom_gro_path`, `custom_itp_path`

### 6.2 Export Flow

```
Menu: Export → Export Ion... (Ctrl+J)
  → MainWindow._on_export_ion_gromacs()                      [gui/main_window.py:1696]
    → IonGROMACSExporter.export_ion_gromacs(ion_structure)    [gui/export.py:279]
      → QFileDialog.getSaveFileName(...)
      → write_ion_gro_file(ion_structure, path)               [output/gromacs_writer.py:1302]
        → Builds ordered mols: SOL(ice+water) → guest → custom → solute → NA → CL  [lines 1317-1362]
        → For custom molecules: creates pseudo-entries from custom_molecule_count
        → For solutes: creates pseudo-entries from solute_molecule_indices
        → Ice: 3→4 expansion (MW computed)
        → Water: 4-atom pass-through (MW recomputed)
        → Guest: detect type, reorder atoms, use hydrate residue name
        → Custom: uses custom_molecule_positions, custom_molecule_atom_names
        → Solute: uses solute_positions, solute_atom_names
        → Ions: 1 atom each, NA/CL residue names
      → write_ion_top_file(ion_structure, top_path)           [output/gromacs_writer.py:1627]
        → Counts: sol_count, guest_count, custom_count, solute_count, na_count, cl_count
        → Parses custom_mol_name from ITP file (Bug 2 fix)
        → [atomtypes]: TIP4P-ICE + Madrid2019 ions + GAFF2 (CH4/THF)
        → Deduplication of custom atomtypes (Bug 3 fix)
        → #include "tip4p-ice.itp"
        → #include "{guest}_hydrate.itp" (if guests)
        → #include "{custom_itp_name}" (if custom molecules)
        → #include "{solute}_liquid.itp" (if solutes)
        → #include "ion.itp"
        → [molecules] order: SOL, {guest_res}, {custom_mol}, {solute_mol}, NA, CL
      → write_ion_itp(path, na_count, cl_count)              [structure_generation/gromacs_ion_export.py:81]
        → Generates ion.itp with [moleculetype] NA and [moleculetype] CL
        → Madrid2019 charges: NA=+0.85, CL=-0.85
      → Copies: tip4p-ice.itp
      → Copies: {guest}_hydrate.itp (if guests)
      → Copies: {solute}_liquid.itp with atomtypes commented (if solutes)
      → Copies: custom ITP with atomtypes commented (if custom molecules)

  File outputs: ions_{na}na_{cl}cl.gro, .top, ion.itp, tip4p-ice.itp,
                {guest}_hydrate.itp, {solute}_liquid.itp, {custom}.itp
```

---

## 7. Full Chain Exports (Workflow 8a & 8b)

### 7.1 Full Chain F1: Ice → Interface → Ion

```
Tab 0: Generate Ice
  → Candidate(positions_3atom, cell, nmolecules)
  → Stored: self._current_result

Tab 2: Generate Interface (from Ice candidate)
  → InterfaceStructure(ice+water+guests)
  → Stored: self._current_interface_result

Tab 5: Insert Ions (source=Interface)
  → insert_ions(self._current_interface_result, concentration, volume)
  → IonStructure with na_count, cl_count, guest info (if hydrate source)
  → Stored: self._current_ion_result

Export Ion:
  → write_ion_gro_file: SOL(ice+water), guest, NA, CL
  → write_ion_top_file: [molecules] SOL, {guest}, NA, CL
  → Bundles: tip4p-ice.itp, {guest}_hydrate.itp, ion.itp
```

### 7.2 Full Chain F2: Ice → Interface → Custom → Ion (Workflow 8b)

```
Tab 0: Generate Ice → self._current_result
Tab 2: Generate Interface → self._current_interface_result

Tab 3: Insert Custom Molecules
  → CustomMoleculeInserter.place_random/interface_result, n_molecules)
  → _remove_overlapping_water() → modified InterfaceStructure
  → CustomMoleculeStructure(positions=ice+water+custom, molecule_index, ...)
  → Stored: self._current_custom_molecule_result
  → Passed to: IonPanel (set_custom_molecule_structure)

Tab 5: Insert Ions (source=Custom Molecule)
  → MainWindow._on_insert_ions() [line 877]
  → Gets custom_structure.interface_structure
  → COPIES custom molecule attrs to interface object:
      interface.custom_molecule_positions = custom_structure.positions[ice+water+guest:]
      interface.custom_molecule_count = custom_structure.custom_molecule_count
      interface.custom_molecule_moleculetype = custom_structure.moleculetype_name
      interface.custom_gro_path, interface.custom_itp_path
  → insert_ions(interface, ...) → IonStructure (with custom_* attrs populated)

Export Ion:
  → write_ion_gro_file: SOL, guest, custom, NA, CL
  → write_ion_top_file: [molecules] SOL, {guest}, {custom_mol}, NA, CL
  → Bundles: tip4p-ice.itp, {guest}_hydrate.itp, {custom}.itp (atomtypes commented), ion.itp
```

### 7.3 Full Chain F3: Ice → Interface → Custom → Solute → Ion (Workflow 8a)

```
Tab 0: Generate Ice → self._current_result
Tab 2: Generate Interface → self._current_interface_result

Tab 3: Insert Custom Molecules
  → CustomMoleculeStructure (with interface_structure = modified after water removal)
  → Stored: self._current_custom_molecule_result
  → Passed to: SolutePanel, IonPanel

Tab 4: Insert Solutes (source=Custom Molecule)
  → MainWindow._on_insert_solutes() [line 998]
  → Gets custom_structure (full CustomMoleculeStructure)
  → Passes to SoluteInserter.insert_solutes(interface=custom_structure, config)
  → SoluteInserter._remove_overlapping_water():
    → Detects custom molecules in input (custom_molecule_atom_count > 0)
    → Separates guests + custom molecules in positions array
    → Rebuilds new InterfaceStructure with custom molecule attrs preserved
  → SoluteStructure with:
    - interface_structure (modified, with custom molecule attrs)
    - custom_molecule_count, custom_molecule_positions, custom_molecule_atom_names
    - custom_molecule_moleculetype, custom_gro_path, custom_itp_path
  → Stored: self._current_solute_result
  → Passed to: IonPanel (set_solute_structure)

Tab 5: Insert Ions (source=Solute)
  → MainWindow._on_insert_ions() [line 844]
  → Gets solute_structure.interface_structure
  → COPIES solute attrs to interface:
      interface.solute_type, interface.solute_positions, ...
      interface.solute_n_molecules, interface.solute_molecule_indices
  → Also carries custom molecule attrs through (already on interface from SoluteInserter)
  → insert_ions(interface, ...) → IonStructure (with solute_* AND custom_* attrs)

Export Ion:
  → write_ion_gro_file: SOL, guest, custom, solute, NA, CL
  → write_ion_top_file: [molecules] SOL, {guest}, {custom_mol}, {solute_mol}, NA, CL
  → Bundles: tip4p-ice.itp, {guest}_hydrate.itp, {custom}.itp, {solute}_liquid.itp, ion.itp
```

### 7.4 Full Chain F4: Hydrate → Interface → Ion

```
Tab 1: Generate Hydrate → self._current_hydrate_result (HydrateStructure)
Tab 2: Generate Interface (source=Hydrate)
  → hydrate.to_candidate() [types.py:654]
    → Includes ALL molecules (water framework + guests)
    → Candidate with phase_id="hydrate_sI"
  → generate_interface(candidate, config) → assemble_piece()
  → InterfaceStructure with guest_atom_count > 0, guest_nmolecules > 0
  → Stored: self._current_interface_result

Tab 5: Insert Ions (source=Interface)
  → IonStructure with guest info populated
  → Export: SOL, {guest}_H, NA, CL
```

### 7.5 Full Chain F5: Hydrate → Interface → Custom → Ion

```
Same as F4 + Tab 3 (Custom Molecules) inserted before ions
→ Export: SOL, {guest}_H, {custom}, NA, CL
```

### 7.6 Full Chain F6: Hydrate → Interface → Solute → Ion

```
Same as F4 + Tab 4 (Solutes) inserted before ions
→ Export: SOL, {guest}_H, {solute}_L, NA, CL
```

### 7.7 Full Chain F7: Hydrate → Interface → Custom → Solute → Ion

```
Same as F4 + Tab 3 + Tab 4 before ions
→ Export: SOL, {guest}_H, {custom}, {solute}_L, NA, CL
```

---

## 8. Data Flow Diagram: Cross-Tab Structure Passing

```
Tab 0 (Ice)
  │ Candidate (3-atom: O,H,H)
  │
  ├───────────────────────────► Tab 2 (Interface)
  │                               │ InterfaceStructure
  │                               │ (ice_atoms + water_atoms + guest_atoms)
  │                               │
  │                               ├────────────► Tab 3 (Custom)
  │                               │                │ CustomMoleculeStructure
  │                               │                │ (ice+water+guest+custom)
  │                               │                │ .interface_structure = modified Interface
  │                               │                │
  │                               │                ├─────────► Tab 4 (Solute)
  │                               │                │              │ SoluteStructure
  │                               │                │              │ .interface_structure = modified Interface
  │                               │                │              │ .custom_molecule_* attrs preserved
  │                               │                │              │
  │                               │                │              ├─────► Tab 5 (Ion)
  │                               │                │              │          │ IonStructure
  │                               │                │              │          │ .solute_* attrs
  │                               │                │              │          │ .custom_molecule_* attrs
  │                               │                │              │          │
  │                               │                │              │          └──► GROMACS Export
  │                               │                │              │                (most complete: SOL+guest+custom+solute+NA+CL)
  │                               │                │              │
  │                               │                ├─────────► Tab 5 (Ion) [source=Custom]
  │                               │                │              │ IonStructure
  │                               │                │              │ .custom_molecule_* attrs
  │                               │                │              │
  │                               │                │              └──► GROMACS Export
  │                               │                │                    (SOL+guest+custom+NA+CL)
  │                               │                │
  │                               ├────────────► Tab 4 (Solute) [source=Interface]
  │                               │                │ SoluteStructure
  │                               │                │ .interface_structure
  │                               │                │
  │                               │                ├─────► Tab 5 (Ion) [source=Solute]
  │                               │                │          │ IonStructure
  │                               │                │          │ .solute_* attrs
  │                               │                │          │
  │                               │                │          └──► GROMACS Export
  │                               │                │                (SOL+guest+solute+NA+CL)
  │                               │                │
  │                               ├────────────► Tab 5 (Ion) [source=Interface]
  │                               │                │ IonStructure
  │                               │                │ .guest_* attrs (if hydrate source)
  │                               │                │
  │                               │                └──► GROMACS Export
  │                               │                      (SOL+guest+NA+CL)
  │
Tab 1 (Hydrate)
  │ HydrateStructure (4-atom water + guests)
  │ .to_candidate() → Candidate with guests
  │
  └───────────────────────────► Tab 2 (Interface) [source=hydrate]
                                   → Same Interface flow as above
```

---

## 9. Critical Branch Points

### 9.1 molecule_index Population

**Controls:** Whether `write_*_gro_file` uses MoleculeIndex-based writing vs synthetic entry building.

| Exporter | Uses molecule_index? | Fallback |
|----------|---------------------|----------|
| `write_gro_file` (Ice) | No — iterates nmolecules × 3 | N/A (always 3-atom) |
| `write_interface_gro_file` | Yes (`wrap_molecules_into_box`) | `wrap_positions_into_box` if empty |
| `write_multi_molecule_gro_file` (Hydrate) | Yes — required | None |
| `write_ion_gro_file` | Yes — required | `_build_molecule_index_from_structure()` |
| `write_custom_molecule_gro_file` | Yes — required | None |
| `write_solute_gro_file` | Yes — fallback to synthetic entries from counts | Builds from ice_nmolecules/water_nmolecules |

**Key insight:** `molecule_index` is critical for the multi-molecule writers. When it's empty (GenIce2-generated InterfaceStructures), writers fall back to building from `ice_nmolecules`/`water_nmolecules`/`guest_nmolecules` counts.

### 9.2 guest_nmolecules > 0

**Controls:** Whether guest molecule section appears in .gro, .top, and bundled .itp files.

- `InterfaceStructure.guest_nmolecules` — populated when source was HydrateStructure.to_candidate()
- `IonStructure.guest_nmolecules` — propagated from source interface
- `SoluteStructure.interface_structure.guest_nmolecules` — propagated from source

**When > 0:**
- .gro file includes guest atom lines (after SOL)
- .top file includes `#include "{guest}_hydrate.itp"`
- `{guest}_hydrate.itp` copied to output directory
- [molecules] section includes `{guest_res_name} {guest_nmolecules}`

### 9.3 custom_molecule_count > 0

**Controls:** Whether custom molecule section appears in ion/solute exports.

- Set in `MainWindow._on_insert_ions()` when source is "Custom Molecule" [line 877]
- Propagated through `SoluteInserter._remove_overlapping_water()` to modified InterfaceStructure
- Carried in `IonStructure.custom_molecule_count`, `SoluteStructure.custom_molecule_count`

**When > 0:**
- .gro file includes custom molecule atom lines
- .top file includes `#include "{custom_itp_name}"`
- Custom ITP copied with `comment_out_atomtypes_in_itp()` modification

### 9.4 Ice 3-atom vs 4-atom Detection

**Controls:** Whether MW virtual site needs to be computed or already exists.

- `write_interface_gro_file`: checks `"OW" in ice_region_atom_names` [line 684]
  - If "OW" found → `atoms_per_ice_mol = 4` (hydrate source, TIP4P already)
  - If not → `atoms_per_ice_mol = 3` (GenIce source, TIP3P → needs 3→4 expansion)
- `write_ion_gro_file`: checks `mol.mol_type == "ice"` in molecule_index
  - If ice → compute MW from O, H, H positions
  - If water → MW already in 4th position (recompute anyway for consistency)

### 9.5 solute_n_molecules > 0

**Controls:** Whether solute section appears in ion export.

- Set in `MainWindow._on_insert_ions()` when source is "Solute" [line 844]
- Copied from `solute_structure` attributes to `interface` object before passing to `insert_ions()`

**When > 0:**
- .gro file includes solute atom lines (from solute_positions)
- .top file includes `#include "{solute}_liquid.itp"`
- `{solute}_liquid.itp` copied with atomtypes commented out
- [molecules] includes `{solute_mol_name} {solute_n_molecules}`

---

## 10. Key Data Transformations

### 10.1 3→4 Atom Expansion (Ice TIP3P → TIP4P-ICE)

**When:** Ice export, Interface export (ice region), Ion export (ice molecules), Solute export (ice region)

**Algorithm:** `compute_mw_position(o_pos, h1_pos, h2_pos)` at `output/gromacs_writer.py:587`
```python
MW = O + α*(H1-O) + α*(H2-O)  where α = 0.13458335
```

**Output atom order:** OW, HW1, HW2, MW (all under residue SOL)

### 10.2 Guest Atom Reordering

**When:** Any export that includes guest molecules (CH4 or THF)

**Algorithm:** `reorder_guest_atoms(atom_names, mol_type)` at `output/gromacs_writer.py:153`
- CH4: GenIce2 outputs [H, H, H, H, C] → reorder to [C, H, H, H, H] (canonical .itp order)
- THF: Reorder to match thf.itp canonical [O, CA, CA, CB, CB, ...]
- Returns: `(reordered_names, reorder_mapping)` or `(original_names, None)` if not needed

### 10.3 Water Removal (Overlap-based)

**When:** Custom molecule insertion, Solute insertion

**Algorithm:** `_remove_overlapping_water(structure, new_positions, min_separation)`
- Custom: `custom_molecule_inserter.py:343`
- Solute: `solute_inserter.py:342`
- Both follow same pattern:
  1. Build KDTree from new molecule positions
  2. Check each water molecule's atoms against tree
  3. Remove entire water molecules that overlap
  4. Rebuild positions array: ice + kept_water + guests + custom_molecules
  5. Rebuild molecule_index with correct start_idx values
  6. Return new InterfaceStructure

### 10.4 Molecule Index Building

**When:** Ion insertion (from InterfaceStructure without molecule_index)

**Algorithm:** `_build_molecule_index_from_structure(structure)` at `ion_inserter.py:62`
- Uses `ice_atom_count`, `water_atom_count`, `guest_atom_count`
- Computes `atoms_per_mol = count / nmolecules`
- Builds MoleculeIndex entries: ice → water → guest

### 10.5 ITP Atomtypes Comment-out

**When:** Any export that bundles user-provided or solute ITP files

**Algorithm:** `comment_out_atomtypes_in_itp(itp_content)` at `output/gromacs_writer.py:311`
- Adds `; Modified for QuickIce: [atomtypes] commented` header
- Comments out `[ atomtypes ]` section header
- Comments out all data lines within section
- Reason: atomtypes must be defined in main .top file to avoid duplication errors

---

## 11. Known Bugs/Workarounds Documented Inline

### Bug 1: GAFF2 atomtypes missing in Ion .top file
**Location:** `write_ion_top_file()` at `output/gromacs_writer.py:1686`
**Fix:** Added `needs_ch4_atomtypes` and `needs_thf_atomtypes` flags combining guest and solute needs
**Impact:** Without this fix, solute ITP files with pre-commented atomtypes would leave GROMACS unable to find atom type definitions

### Bug 2: Custom molecule [molecules] name mismatch
**Location:** `write_ion_top_file()` at `output/gromacs_writer.py:1671`
**Fix:** Parse moleculetype name from ITP file (`parse_itp_file(itp_path).molecule_name`) instead of using registry name
**Impact:** GROMACS requires [molecules] name to match [moleculetype] name in ITP. Registry names (e.g., "CUSTOM_MOL_1") may not match

### Bug 3: Duplicate atomtypes in Ion .top file
**Location:** `write_ion_top_file()` at `output/gromacs_writer.py:1746`
**Fix:** Track `_written_atomtypes` set, skip atomtypes already written
**Impact:** GROMACS rejects duplicate atomtype definitions in same .top file

### Workaround: Synthetic molecule entries for empty molecule_index
**Location:** `write_solute_gro_file()` at `output/gromacs_writer.py:2205`
**When:** GenIce2-generated InterfaceStructures have empty molecule_index
**Fix:** Build synthetic MoleculeIndex entries from `ice_nmolecules`, `water_nmolecules`, `guest_nmolecules`

### Workaround: Custom molecule data extraction from molecule_index
**Location:** `IonInserter.replace_water_with_ions()` at `ion_inserter.py:495`
**When:** `custom_molecule_positions` is None but `custom_molecule_count > 0`
**Fix:** Extract positions/atom_names from CustomMoleculeStructure's shared positions array using `mol_type == "custom"` entries

---

## 12. GROMACS [molecules] Section Order Per Export Type

| Export Type | [molecules] Order |
|------------|-------------------|
| Ice | SOL |
| Hydrate | SOL, {GUEST}_H |
| Interface | SOL, {GUEST}_H |
| Custom | SOL, {GUEST}_H, {CUSTOM} |
| Solute | SOL, {GUEST}_H, {CUSTOM}, {SOLUTE}_L |
| Ion (from Interface) | SOL, {GUEST}_H, NA, CL |
| Ion (from Custom) | SOL, {GUEST}_H, {CUSTOM}, NA, CL |
| Ion (from Solute) | SOL, {GUEST}_H, {SOLUTE}_L, NA, CL |
| Ion (full chain) | SOL, {GUEST}_H, {CUSTOM}, {SOLUTE}_L, NA, CL |

**GROMACS requirement:** [molecules] order must match atom order in .gro file. All SOL molecules must be contiguous.

---

## 13. ITP Files Bundled Per Export Type

| Export Type | ITPs Bundled |
|------------|-------------|
| Ice | tip4p-ice.itp (copied) |
| Hydrate | tip4p-ice.itp, {guest}_hydrate.itp |
| Interface | tip4p-ice.itp, {guest}_hydrate.itp (if guests) |
| Custom | tip4p-ice.itp, {guest}_hydrate.itp (if guests), {custom}.itp (atomtypes commented) |
| Solute | tip4p-ice.itp, {guest}_hydrate.itp (if guests), {custom}.itp (if custom, atomtypes commented), {solute}_liquid.itp (atomtypes commented) |
| Ion | tip4p-ice.itp, {guest}_hydrate.itp (if guests), {custom}.itp (if custom, atomtypes commented), {solute}_liquid.itp (if solutes, atomtypes commented), ion.itp (generated) |

---

## 14. Moleculetype Registry Naming

Defined in `quickice/structure_generation/moleculetype_registry.py`:

| Context | Registration Method | GROMACS Name |
|---------|-------------------|---------------|
| Hydrate guest (CH4) | `register_hydrate_guest("CH4")` | `CH4_H` |
| Hydrate guest (THF) | `register_hydrate_guest("THF")` | `THF_H` |
| Liquid solute (CH4) | `register_liquid_solute("CH4")` | `CH4_L` |
| Liquid solute (THF) | `register_liquid_solute("THF")` | `THF_L` |
| Custom molecule | `register_custom_molecule()` | `CUSTOM_MOL_1` (auto-increment) |

**Note:** For Ion/Custom exports, the [molecules] name is parsed from the actual ITP file (Bug 2 fix) rather than using the registry name, since GROMACS requires exact match.

---

*Flow trace analysis: 2026-06-08*
