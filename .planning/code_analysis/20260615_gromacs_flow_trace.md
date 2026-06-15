# GROMACS Export Flow Trace

**Generated:** 2026-06-15
**Scope:** Complete function/data flow from user action to successful GROMACS export
**Covers:** All 6 GUI tabs + CLI single-step + CLI full pipeline + unified entry point routing

---

## 1. Unified Entry Point Routing Decision Tree

**File:** `quickice/entry.py` → `main(argv)`

All invocations of QuickIce go through this router:

```
python -m quickice [args]
         │
         ▼
    quickice/__main__.py
         │  sys.exit(main())
         ▼
    quickice/entry.py: main(argv)
         │
         ├─ No args? ──→ print help, return 0
         ├─ --help/-h? ──→ argparse --help (exits 0)
         ├─ --version/-V? ──→ argparse --version (exits 0)
         ├─ --gui explicit? ──→ check PySide6 + display
         │                     ├─ fail → stderr error, return 1
         │                     └─ ok → quickice.gui.main_window.run_app(), return 0
         ├─ --cli explicit? ──→ strip --cli/--gui, delegate to quickice.main.main()
         ├─ Pipeline flags detected? ──→ strip --cli/--gui, delegate to quickice.main.main()
         └─ No pipeline flags? ──→ print help, return 0
```

**Pipeline flags** detected by `_has_pipeline_flags()`: any arg starting with `-` that is NOT in `_ROUTER_FLAGS` (`--cli`, `--gui`, `--help`, `--version`, `-h`, `-V`). Examples: `-T`, `--interface`, `--hydrate`, `-P`, `-N`, `--solute-type`, `--ion-concentration`, `--custom-gro`.

When routed to CLI:
```
quickice/main.py: main()
    │
    ├─ args = get_arguments()  [quickice/cli/parser.py]
    │     └─ parser.parse_args() + validate_pipeline_args()
    │
    ├─ has_pipeline_flags? ──→ CLIPipeline(args).execute()  [quickice/cli/pipeline.py]
    │
    └─ Ice-only workflow (backward compat):
        ├─ lookup_phase(T, P)
        ├─ generate_candidates(phase_info, nmolecules, n_candidates=10)
        ├─ rank_candidates(candidates)
        ├─ if args.gromacs: write_gro_file, write_top_file, copy ITP
        └─ output_ranked_candidates (PDB + diagram)
```

---

## 2. CLI Full Pipeline Step Chain

**File:** `quickice/cli/pipeline.py` → `CLIPipeline.execute()`

The pipeline runs ordered steps with fail-fast semantics:

```
CLIPipeline.execute()
    │
    ├─ Step 0: Create output directory (Path(args.output))
    ├─ Step 0b: Check --no-overwrite
    │
    ├─ Step 1: Source step (_run_source_step)
    │     ├─ --hydrate? → HydrateStructureGenerator().generate(config) → _hydrate_result
    │     │                └─ also --interface? → _hydrate_result.to_candidate() → _ice_candidate
    │     └─ --interface only? → generate_candidates(phase_info, nmolecules) → _ice_candidate
    │
    ├─ Step 2: Interface step (_run_interface_step) [if --interface]
    │     └─ generate_interface(_ice_candidate, InterfaceConfig) → _interface_result
    │
    ├─ Step 3: Custom molecule step (_run_custom_step) [if --custom-gro]
    │     ├─ random mode → CustomMoleculeInserter(config).place_random(source, count) → _custom_result
    │     └─ custom mode → _parse_positions_csv() → CustomMoleculeInserter(config).place_custom(source, positions, rotations) → _custom_result
    │
    ├─ Step 4: Solute step (_run_solute_step) [if --solute-type]
    │     └─ SoluteInserter(config, seed=args.seed).insert_solutes(source, config) → _solute_result
    │
    ├─ Step 5: Ion step (_run_ion_step) [if --ion-concentration]
    │     ├─ ion_source="interface" → insert_ions(_interface_result, ...)
    │     ├─ ion_source="custom" → propagate custom attrs to _interface_result → insert_ions(interface, ...)
    │     └─ ion_source="solute" → propagate solute attrs to _interface_result → insert_ions(interface, ...)
    │     → _ion_result
    │
    └─ Step 6: Export step (_run_export_step)
          ├─ Select most downstream structure (ion > solute > custom > interface > hydrate > ice)
          ├─ Dispatch to step-specific GROMACS writer pair
          └─ Copy ITP files via copy_itp_files_for_structure()
```

---

## 3. GUI Export Flows (6 Tabs)

### 3.1 Tab 0: Ice Candidate Export

**Trigger:** User clicks File → "Export for GROMACS" or Ctrl+G on Ice Generation tab

```
MainWindow._on_export_gromacs()  [quickice/gui/main_window.py:1593]
    │
    ├─ Verify self._current_result (GenerationResult) exists
    ├─ Get selected candidate index from ViewerPanel
    ├─ Get T, P from InputPanel
    │
    └─ GROMACSExporter.export_gromacs(ranked_candidate, T, P)  [quickice/gui/export.py:704]
         │
         ├─ QFileDialog.getSaveFileName("Export for GROMACS", default=ice_ih_195K_1.36MPa_c1.gro)
         ├─ write_gro_file(candidate, path)  [quickice/output/gromacs_writer.py:430]
         │     └─ Format: 3-atom (O, H, H) from GenIce TIP3P
         ├─ write_top_file(candidate, top_path)  [quickice/output/gromacs_writer.py:524]
         └─ shutil.copy(get_tip4p_itp_path(), itp_path)
              └─ Source: quickice/data/tip4p-ice.itp
```

**Files produced:** `{phase}_{T}K_{P}MPa_c{rank}.gro`, `.top`, `.itp`

### 3.2 Tab 1: Hydrate Export

**Trigger:** User clicks File → "Export Hydrate for GROMACS" on Hydrate Generation tab

```
MainWindow._on_export_hydrate_gromacs()  [quickice/gui/main_window.py:1660]
    │
    ├─ Verify self._current_hydrate_result (HydrateStructure) exists
    ├─ Verify self._current_hydrate_config (HydrateConfig) exists
    │
    └─ HydrateGROMACSExporter.export_hydrate(structure, config)  [quickice/gui/hydrate_export.py:90]
         │
         ├─ QFileDialog.getSaveFileName("Export Hydrate for GROMACS", default=hydrate_sI_ch4_1x1x1.gro)
         ├─ MoleculetypeRegistry().register_hydrate_guest(guest_type)
         ├─ write_multi_molecule_gro_file(positions, molecule_index, cell, path, ...)  [gromacs_writer.py:1059]
         ├─ write_multi_molecule_top_file(molecule_index, top_path, ..., itp_files, registry)  [gromacs_writer.py:1156]
         ├─ shutil.copy(tip4p_itp_path, path.with_name("tip4p-ice.itp"))
         └─ shutil.copy(guest_itp_path, path.with_name(f"{guest_type}_hydrate.itp"))
              └─ Source: quickice/data/{guest}_hydrate.itp
```

**Files produced:** `hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro`, `.top`, `tip4p-ice.itp`, `{guest}_hydrate.itp`

### 3.3 Tab 2: Interface Export

**Trigger:** User clicks File → "Export Interface for GROMACS" or Ctrl+S on Interface Construction tab

```
MainWindow._on_export_interface_gromacs()  [quickice/gui/main_window.py:1634]
    │
    ├─ Verify self._current_interface_result (InterfaceStructure) exists
    │
    └─ InterfaceGROMACSExporter.export_interface_gromacs(interface)  [quickice/gui/export.py:844]
         │
         ├─ QFileDialog.getSaveFileName("Export Interface for GROMACS", default=interface_slab.gro)
         ├─ write_interface_gro_file(interface, path)  [gromacs_writer.py:618]
         │     └─ Normalizes ice 3→4 atoms (adds MW virtual site)
         │     └─ Wraps molecules into box using molecule_index
         │     └─ Writes: SOL residues for ice+water, guest residues for guests
         ├─ write_interface_top_file(interface, top_path)  [gromacs_writer.py:951]
         │     └─ [molecules]: SOL count, then guest count if present
         │     └─ #include "tip4p-ice.itp" (+ #include "{guest}_hydrate.itp" if guests)
         ├─ shutil.copy(tip4p_itp_path, path.with_name("tip4p-ice.itp"))
         └─ if guests present: shutil.copy(guest_itp_path, path.with_name(f"{guest_type}_hydrate.itp"))
```

**Files produced:** `interface_{mode}.gro`, `.top`, `tip4p-ice.itp`, optional `{guest}_hydrate.itp`

### 3.4 Tab 3: Custom Molecule Export

**Trigger:** User clicks File → "Export Custom Molecules for GROMACS" on Custom Molecule tab

```
MainWindow._on_export_custom_molecule_gromacs()  [quickice/gui/main_window.py:1761]
    │
    ├─ Verify self._current_custom_molecule_result (CustomMoleculeStructure) exists
    │
    └─ CustomMoleculeGROMACSExporter.export_custom_molecule_gromacs(custom_structure)  [export.py:171]
         │
         ├─ QFileDialog.getSaveFileName("Export Custom Molecule System for GROMACS", default=custom_system_CUSTOM_MOL_1_5molecules.gro)
         ├─ write_custom_molecule_gro_file(custom_structure, path)  [gromacs_writer.py:1853]
         │     └─ Normalizes ice 3→4 atoms
         │     └─ Writes: SOL (ice+water), guest, custom molecule atoms
         ├─ write_custom_molecule_top_file(custom_structure, top_path)  [gromacs_writer.py:2061]
         │     └─ [molecules]: SOL count, guest count, CUSTOM_MOL_N count
         │     └─ #include "tip4p-ice.itp", #include "{custom}.itp"
         ├─ comment_out_atomtypes_in_itp(custom_itp_content) → write custom .itp
         ├─ shutil.copy(tip4p_itp_path, path.with_name("tip4p-ice.itp"))
         └─ if guests present: shutil.copy(guest_itp_path, ...)
```

**Files produced:** `custom_system_{moltype}_{count}molecules.gro`, `.top`, `tip4p-ice.itp`, `{custom}.itp`, optional `{guest}_hydrate.itp`

### 3.5 Tab 4: Solute Export

**Trigger:** User clicks File → "Export Solutes for GROMACS" on Solute Insertion tab

```
MainWindow._on_export_solute_gromacs()  [quickice/gui/main_window.py:1728]
    │
    ├─ Verify self._current_solute_result (SoluteStructure) exists
    │
    └─ SoluteGROMACSExporter.export_solute_gromacs(solute_structure)  [export.py:46]
         │
         ├─ QFileDialog.getSaveFileName("Export Solutes for GROMACS", default=solute_ch4_5molecules.gro)
         ├─ write_solute_gro_file(solute_structure, path)  [gromacs_writer.py:2192]
         │     └─ Uses interface_structure for ice+water+guest atoms
         │     └─ Appends solute atoms after ice+water+guest
         ├─ write_solute_top_file(solute_structure, top_path)  [gromacs_writer.py:2508]
         │     └─ [molecules]: SOL, [guest], [custom_mol], CH4_L or THF_L
         │     └─ #include "tip4p-ice.itp", #include "{solute}_liquid.itp", etc.
         ├─ shutil.copy(tip4p_itp_path, ...)
         ├─ if guests: shutil.copy(guest_itp_path, ...)
         ├─ comment_out_atomtypes_in_itp(solute_itp) → write {solute}_liquid.itp
         └─ if custom_molecules: comment_out_atomtypes_in_itp(custom_itp) → write custom .itp
```

**Files produced:** `solute_{type}_{count}molecules.gro`, `.top`, `tip4p-ice.itp`, `{solute}_liquid.itp`, optional `{guest}_hydrate.itp`, optional `{custom}.itp`

### 3.6 Tab 5: Ion Export

**Trigger:** User clicks File → "Export Ions for GROMACS" on Ion Insertion tab

```
MainWindow._on_export_ion_gromacs()  [quickice/gui/main_window.py:1696]
    │
    ├─ Verify self._current_ion_result (IonStructure) exists
    │
    └─ IonGROMACSExporter.export_ion_gromacs(ion_structure)  [export.py:279]
         │
         ├─ QFileDialog.getSaveFileName("Export Ions for GROMACS", default=ions_5na_5cl.gro)
         ├─ write_ion_gro_file(ion_structure, path)  [gromacs_writer.py:1314]
         │     └─ Writes: SOL (ice+water), NA, CL, [guest], [solute], [custom]
         ├─ write_ion_top_file(ion_structure, top_path)  [gromacs_writer.py:1639]
         │     └─ [molecules]: SOL, NA, CL, [guest], [CH4_L/THF_L], [CUSTOM_MOL]
         │     └─ #include "tip4p-ice.itp", #include "ion.itp", etc.
         ├─ write_ion_itp(ion_itp_path, na_count, cl_count)  [gromacs_ion_export.py]
         ├─ shutil.copy(tip4p_itp_path, ...)
         ├─ if guests: shutil.copy(guest_itp_path, ...)
         ├─ if solutes: comment_out_atomtypes_in_itp(solute_itp) → write {solute}_liquid.itp
         └─ if custom_molecules: comment_out_atomtypes_in_itp(custom_itp) → write custom .itp
```

**Files produced:** `ions_{na}na_{cl}cl.gro`, `.top`, `tip4p-ice.itp`, `ion.itp`, optional `{guest}_hydrate.itp`, optional `{solute}_liquid.itp`, optional `{custom}.itp`

---

## 4. CLI Single-Step Export Paths

### 4.1 Ice-only (backward compat)

```bash
python -m quickice -T 250 -P 0.1 -N 256 --gromacs -o output
```

```
entry.py: main()
    └─ pipeline flags (-T, -P, -N) → quickice/main.py: main()
         ├─ get_arguments() → args.gromacs=True
         ├─ NO pipeline flags (no --interface etc) → ice-only workflow
         ├─ lookup_phase(250, 0.1) → phase_info
         ├─ generate_candidates(phase_info, 256, n_candidates=10)
         │     └─ IceStructureGenerator(phase_info, 256).generate_all(10, base_seed)
         │          └─ _generate_single(seed): GenIce2 → parse_gro_string → Candidate
         ├─ rank_candidates(candidates)
         └─ if args.gromacs:
              ├─ for each ranked_candidate:
              │     └─ write_gro_file(candidate, "output/{phase}_{T}K_{P}MPa_c{rank}.gro")
              ├─ write_top_file(first_candidate, "output/{phase}.top")
              └─ shutil.copy(get_tip4p_itp_path(), "output/tip4p-ice.itp")
```

### 4.2 Interface-only

```bash
python -m quickice -T 270 -P 0.1 --interface --mode slab --box-x 3 --box-y 3 --box-z 5 --ice-thickness 1.5 --water-thickness 2.0 --export -o output
```

```
entry.py: main()
    └─ pipeline flags → quickice/main.py: main()
         └─ has_pipeline_flags=True → CLIPipeline(args).execute()
              ├─ Step 1: _run_source_step()
              │     └─ generate_candidates(phase_info, nmolecules=256, n_candidates=1) → _ice_candidate
              ├─ Step 2: _run_interface_step()
              │     └─ generate_interface(_ice_candidate, InterfaceConfig(mode=slab, ...))
              │          └─ validate_interface_config → assemble_slab(candidate, config)
              │               └─ tile ice → fill_region_with_water → detect_overlaps → InterfaceStructure
              └─ Step 6: _run_export_step()
                   ├─ step_name="interface"
                   ├─ write_interface_gro_file(interface_result, "output/interface.gro")
                   ├─ write_interface_top_file(interface_result, "output/interface.top")
                   └─ copy_itp_files_for_structure(output_dir, interface_result, "interface")
                        └─ tip4p-ice.itp + optional guest ITP
```

### 4.3 Hydrate-only

```bash
python -m quickice -T 270 -P 10 --hydrate --lattice-type sI --guest CH4 --supercell-x 2 --export -o output
```

```
entry.py: main()
    └─ pipeline flags → quickice/main.py: main()
         └─ CLIPipeline(args).execute()
              ├─ Step 1: _run_source_step()
              │     └─ --hydrate=True → HydrateStructureGenerator().generate(HydrateConfig)
              │          └─ GenIce2 API → _parse_gro_result → _build_molecule_index → HydrateStructure
              │          └─ --interface=False → no to_candidate() conversion
              └─ Step 6: _run_export_step()
                   ├─ step_name="hydrate"
                   ├─ Build InterfaceStructure wrapper from HydrateStructure
                   │     └─ water_atom_count = water_count * WATER_ATOMS_PER_MOLECULE
                   │     └─ guest_atom_count = len(positions) - water_atom_count
                   ├─ write_interface_gro_file(wrapper, "output/hydrate.gro")
                   ├─ write_interface_top_file(wrapper, "output/hydrate.top")
                   └─ copy_itp_files_for_structure(output_dir, wrapper, "hydrate")
                        └─ tip4p-ice.itp + {guest}_hydrate.itp
```

---

## 5. CLI Full Pipeline Export Paths (F1–F7 Chains)

### 5.1 F1: Interface → Custom → Solute → Ion

```bash
python -m quickice -T 270 -P 0.1 --interface --mode slab --box-x 3 --box-y 3 --box-z 5 \
  --ice-thickness 1.5 --water-thickness 2.0 \
  --custom-gro mol.gro --custom-itp mol.itp --custom-placement random --custom-count 5 \
  --solute-type CH4 --solute-concentration 0.5 --ion-concentration 0.15 --ion-source solute \
  --export -o output
```

```
CLIPipeline.execute()
    ├─ Step 1: _run_source_step() → generate_candidates() → _ice_candidate
    ├─ Step 2: _run_interface_step() → generate_interface() → _interface_result
    ├─ Step 3: _run_custom_step()
    │     └─ CustomMoleculeInserter(config).place_random(_interface_result, 5)
    │          └─ Build cKDTree → sample positions → rotate → check overlap → place
    │          └─ _remove_overlapping_water() → CustomMoleculeStructure → _custom_result
    ├─ Step 4: _run_solute_step()
    │     └─ source_name=getattr(args,'solute_source','interface') → _get_source_structure('interface')
    │          → SoluteInserter(config, seed).insert_solutes(_interface_result, config)
    │          └─ Load CH4 template → build tree → place → _remove_overlapping_water()
    │          → SoluteStructure → _solute_result
    ├─ Step 5: _run_ion_step()
    │     └─ ion_source='solute' → _solute_result.interface_structure
    │          └─ Propagate: interface.solute_type, .solute_positions, .solute_atom_names,
    │             .solute_n_molecules, .solute_molecule_indices, .solute_registry
    │          └─ Propagate custom: if source.custom_molecule_count > 0 →
    │             interface.custom_molecule_count, .custom_molecule_atom_count, etc.
    │          └─ insert_ions(interface, 0.15, liquid_volume, seed) → _ion_result
    └─ Step 6: _run_export_step()
         ├─ _ion_result is not None → step_name="ion"
         ├─ write_ion_gro_file(_ion_result, "output/ion.gro")
         ├─ write_ion_top_file(_ion_result, "output/ion.top")
         └─ copy_itp_files_for_structure(output_dir, _ion_result, "ion")
              └─ tip4p-ice.itp, ion.itp, ch4_liquid.itp, {custom}.itp
```

### 5.2 F2: Interface → Custom → Ion (no solute)

```bash
python -m quickice -T 270 -P 0.1 --interface --mode slab --box-x 3 --box-y 3 --box-z 5 \
  --ice-thickness 1.5 --water-thickness 2.0 \
  --custom-gro mol.gro --custom-itp mol.itp --custom-placement random --custom-count 5 \
  --ion-concentration 0.15 --ion-source custom --export -o output
```

```
CLIPipeline.execute()
    ├─ Step 1: _run_source_step() → _ice_candidate
    ├─ Step 2: _run_interface_step() → _interface_result
    ├─ Step 3: _run_custom_step() → _custom_result (CustomMoleculeStructure)
    ├─ Step 5: _run_ion_step()
    │     └─ ion_source='custom' → _custom_result.interface_structure
    │          └─ FIX #4 offset: ice_atom_count + water_atom_count + guest_atom_count
    │          └─ interface.custom_molecule_positions = source.positions[offset:]
    │          └─ interface.custom_molecule_atom_names = source.atom_names[offset:]
    │          └─ interface.custom_molecule_count = source.custom_molecule_count
    │          └─ interface.custom_molecule_moleculetype = source.moleculetype_name
    │          └─ insert_ions(interface, 0.15, liquid_volume, seed) → _ion_result
    └─ Step 6: write_ion_gro_file + write_ion_top_file + copy_itp_files
         └─ tip4p-ice.itp, ion.itp, {custom}.itp
```

### 5.3 F3: Hydrate → Interface → Solute → Ion

```bash
python -m quickice -T 260 -P 10 --hydrate --lattice-type sI --guest CH4 \
  --interface --mode slab --box-x 3 --box-y 3 --box-z 5 \
  --ice-thickness 1.5 --water-thickness 2.0 \
  --solute-type CH4 --solute-concentration 0.5 --ion-concentration 0.15 --ion-source solute \
  --export -o output
```

```
CLIPipeline.execute()
    ├─ Step 1: _run_source_step()
    │     └─ --hydrate → HydrateStructureGenerator().generate() → _hydrate_result
    │     └─ --interface → _hydrate_result.to_candidate() → _ice_candidate
    │          └─ Bundles water + guest atoms into flat Candidate
    ├─ Step 2: _run_interface_step()
    │     └─ generate_interface(_ice_candidate, config) → _interface_result
    │          └─ assemble_slab detects guests via _detect_guest_atoms()
    │          └─ InterfaceStructure with guest_atom_count > 0, guest_nmolecules > 0
    ├─ Step 4: _run_solute_step()
    │     └─ SoluteInserter.insert_solutes(_interface_result, config) → _solute_result
    │          └─ CH4_L registered in MoleculetypeRegistry (distinct from CH4_H hydrate guest)
    ├─ Step 5: _run_ion_step()
    │     └─ ion_source='solute' → propagate attrs → insert_ions() → _ion_result
    └─ Step 6: write_ion_gro_file + write_ion_top_file + copy_itp_files
         └─ tip4p-ice.itp, ion.itp, ch4_liquid.itp, ch4_hydrate.itp
         └─ KEY: CH4_H (hydrate) and CH4_L (solute) are distinct moleculetypes in .top
```

### 5.4 F4: Hydrate → Interface → Custom → Solute → Ion

Same as F3 with additional `--custom-gro`/`--custom-itp` step:

```
    ├─ Step 3: _run_custom_step() → CustomMoleculeStructure → _custom_result
    ├─ Step 4: _run_solute_step() → source=interface → SoluteStructure
    │     └─ Custom molecule attrs preserved via _remove_overlapping_water()
    ├─ Step 5: _run_ion_step()
    │     └─ ion_source='solute' → propagate solute + custom attrs
    └─ Step 6: write_ion files
         └─ tip4p-ice.itp, ion.itp, ch4_liquid.itp, ch4_hydrate.itp, {custom}.itp
         └─ 6 molecule types in .top [molecules]: SOL, CH4, CUSTOM_MOL, CH4_L, NA, CL
```

### 5.5 F5: Interface → Ion (simplest pipeline)

```bash
python -m quickice -T 270 -P 0.1 --interface --mode slab --box-x 3 --box-y 3 --box-z 5 \
  --ice-thickness 1.5 --water-thickness 2.0 --ion-concentration 0.15 --export -o output
```

```
    ├─ Step 1: generate_candidates() → _ice_candidate
    ├─ Step 2: generate_interface() → _interface_result
    ├─ Step 5: _run_ion_step() → ion_source='interface' → insert_ions(_interface_result) → _ion_result
    └─ Step 6: write_ion files → tip4p-ice.itp, ion.itp
```

### 5.6 F6: Interface → Solute (CH4) → Ion

```bash
python -m quickice -T 270 -P 0.1 --interface --mode slab --box-x 3 --box-y 3 --box-z 5 \
  --ice-thickness 1.5 --water-thickness 2.0 \
  --solute-type CH4 --solute-concentration 0.5 --ion-concentration 0.15 --ion-source solute \
  --export -o output
```

```
    └─ Step 6: tip4p-ice.itp, ion.itp, ch4_liquid.itp
```

### 5.7 F7: Interface → Solute (THF) → Ion

```bash
python -m quickice -T 270 -P 0.1 --interface --mode slab --box-x 3 --box-y 3 --box-z 5 \
  --ice-thickness 1.5 --water-thickness 2.0 \
  --solute-type THF --solute-concentration 0.5 --ion-concentration 0.15 --ion-source solute \
  --export -o output
```

```
    └─ Step 6: tip4p-ice.itp, ion.itp, thf_liquid.itp
         └─ THF_L has 13 atoms (O, CA, CA, CB, CB + 8 H)
```

---

## 6. GROMACS Writer Function Inventory

All writer functions live in `quickice/output/gromacs_writer.py`:

| Function | Line | Structure Type | GRO Content Order |
|----------|------|----------------|-------------------|
| `write_gro_file` | 430 | `Candidate` | SOL (3-atom ice, no normalization) |
| `write_top_file` | 524 | `Candidate` | Single SOL in [molecules] |
| `write_interface_gro_file` | 618 | `InterfaceStructure` | SOL (4-atom normalized ice + water), then guests |
| `write_interface_top_file` | 951 | `InterfaceStructure` | SOL, then guests |
| `write_multi_molecule_gro_file` | 1059 | Generic (molecule_index) | Ordered by molecule_index |
| `write_multi_molecule_top_file` | 1156 | Generic (molecule_index) | Ordered by molecule_index |
| `write_ion_gro_file` | 1314 | `IonStructure` | SOL, NA, CL, [guests], [solute], [custom] |
| `write_ion_top_file` | 1639 | `IonStructure` | SOL, NA, CL, [guests], [solute], [custom] |
| `write_custom_molecule_gro_file` | 1853 | `CustomMoleculeStructure` | SOL (ice+water), [guests], custom |
| `write_custom_molecule_top_file` | 2061 | `CustomMoleculeStructure` | SOL, [guests], CUSTOM_MOL |
| `write_solute_gro_file` | 2192 | `SoluteStructure` | SOL (ice+water from interface), [guests], [custom], solute |
| `write_solute_top_file` | 2508 | `SoluteStructure` | SOL, [guests], [custom], CH4_L/THF_L |

---

## 7. ITP File Resolution

**Canonical resolver:** `quickice/cli/itp_helpers.py`

| ITP File | Resolver Function | Source Location |
|----------|-------------------|-----------------|
| `tip4p-ice.itp` | `get_tip4p_itp_path()` → `gromacs_writer.get_tip4p_itp_path()` | `quickice/data/tip4p-ice.itp` |
| `{guest}_hydrate.itp` | `get_hydrate_guest_itp_path(guest_type)` | `quickice/data/{guest}_hydrate.itp` |
| `{solute}_liquid.itp` | `get_solute_liquid_itp_path(solute_type)` | `quickice/data/{solute}_liquid.itp` |
| `ion.itp` | `write_ion_itp(path, na_count, cl_count)` | Generated dynamically |
| Custom ITP | From `CustomMoleculeStructure.itp_path` | User-provided file |
| `{guest}.itp` | `_get_guest_itp_path(guest_type)` (GUI only) | `quickice/data/{guest}.itp` |

**ITP atomtypes handling:** All non-tip4p ITP files have their `[ atomtypes ]` section commented out via `comment_out_atomtypes_in_itp()` before writing to output directory. This prevents conflicts with the TOP file's inline `[ atomtypes ]` section.

---

## 8. Key Data Transformations

### 8.1 Ice 3→4 Atom Normalization

**Where:** `write_interface_gro_file()`, `write_custom_molecule_gro_file()`, `write_solute_gro_file()`, `write_ion_gro_file()`

**What:** GenIce2 ice candidates use 3-atom TIP3P format (O, H, H). GROMACS export normalizes to 4-atom TIP4P-ICE (OW, HW1, HW2, MW) by:
1. Renaming O→OW, H→HW1, H→HW2
2. Computing MW position: `MW = OW + α * (HW1 - OW) + α * (HW2 - OW)` where α = 0.13458335

**File:** `quickice/output/gromacs_writer.py` — `_normalize_ice_atoms()`

### 8.2 Hydrate → InterfaceStructure Wrapping

**Where:** `CLIPipeline._run_export_step()` (step_name="hydrate")

**What:** HydrateStructure has `water_count` and `guest_count` (not `water_nmolecules`, `ice_atom_count`, etc.). Export wraps it in a temporary `InterfaceStructure` with:
- `ice_atom_count=0` (hydrate water framework is "water", not "ice")
- `water_atom_count = water_count * WATER_ATOMS_PER_MOLECULE`
- `guest_atom_count = len(positions) - water_atom_count`
- `mode="hydrate"`

### 8.3 Molecule-aware Wrapping

**Where:** `gromacs_writer.wrap_molecules_into_box()`

**What:** Before writing GRO file, atoms are wrapped into [0, box_size) keeping molecules intact (not splitting across PBC). Uses `molecule_index` to group atoms by molecule.

---

*Flow trace: 2026-06-15*
