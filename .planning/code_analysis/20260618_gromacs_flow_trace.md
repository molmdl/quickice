# GROMACS Export Flow Trace

**Analysis Date:** 2026-06-18
**Based on:** Post-Phase 34.9 and Post-Phase 37.1 codebase state
**Supersedes:** 20260615_gromacs_flow_trace.md (547 lines)

---

## Table of Contents

1. [Unified Entry Point Routing](#1-unified-entry-point-routing)
2. [CLI Paths](#2-cli-paths)
3. [GUI Paths](#3-gui-paths)
4. [Shared Export Writer Functions](#4-shared-export-writer-functions)
5. [PBC Wrapping: Dual-Wrapping Path](#5-pbc-wrapping-dual-wrapping-path)
6. [TIP4P-ICE LJ Constants Flow](#6-tip4p-ice-lj-constants-flow)
7. [comb-rule=2 Flow](#7-comb-rule2-flow)
8. [Conditional cKDTree Rebuild](#8-conditional-ckdtree-rebuild)
9. [detect_atoms_per_molecule Call Chain](#9-detect_atoms_per_molecule-call-chain)
10. [Mutation-Free Solute Inserter](#10-mutation-free-solute-inserter)
11. [Error Handling and Input Validation](#11-error-handling-and-input-validation)
12. [ITP File Bundling](#12-itp-file-bundling)
13. [MoleculetypeRegistry Naming](#13-moleculetyperegistry-naming)
14. [Full Chain: F1–F7 (CLI)](#14-full-chain-f1f7-cli)
15. [Full Chain: Ice→Ion (GUI)](#15-full-chain-iceion-gui)

---

## 1. Unified Entry Point Routing

**File:** `quickice/entry.py` (lines 105–201)

### Function: `entry.main(argv=None)`

**Parameters:**
- `argv`: `list[str] | None` — defaults to `sys.argv`

**Return:** `int` — exit code (0=success, 1=error, 2=argparse)

### Routing Priority:

| Priority | Condition | Action |
|----------|-----------|--------|
| 1 | No args (`effective_args` empty) | Print help via `create_parser()`, return 0 |
| 2 | `--help/-h` in args | Delegate to argparse help (exits 0) |
| 3 | `--version/-V` in args | Delegate to argparse version (exits 0) |
| 4 | `--gui` explicit | Check `_is_pyside6_available()` + `_has_display()`, then `run_app()` |
| 5 | `--cli` explicit | Strip `--cli`, pass remaining to `quickice.main.main()` |
| 6 | Pipeline flags detected | Strip `--cli/--gui`, pass to `quickice.main.main()` |
| 7 | No pipeline flags, no mode | Print help, return 0 |

**Helper Functions:**

- `_is_pyside6_available()` → `quickice/entry.py:26` — uses `importlib.util.find_spec('PySide6')`, never imports PySide6
- `_has_display()` → `quickice/entry.py:42` — checks `DISPLAY`, `WAYLAND_DISPLAY`, `QT_QPA_PLATFORM` on Linux; always True on macOS/Windows
- `_has_pipeline_flags(argv)` → `quickice/entry.py:72` — returns True if any arg starts with `-` and is NOT in `_ROUTER_FLAGS` (`--cli`, `--gui`, `--help`, `--version`, `-h`, `-V`)

### Branch: GUI Path
```
entry.main() → --gui → _is_pyside6_available() → _has_display()
  → quickice.gui.main_window.run_app()
```

### Branch: CLI Path
```
entry.main() → --cli or pipeline flags → quickice.main.main()
```

---

## 2. CLI Paths

### 2.1 Ice-Only Workflow

**File:** `quickice/main.py` (lines 23–195)

**Function:** `main() → int`

**Flow:**

```
1. get_arguments()                              # quickice/cli/parser.py
2. Detect pipeline flags (interface, hydrate, custom_gro, solute_type, ion_concentration)
   → IF any present: CLIPipeline(args).execute()  # see §2.2
3. Ice-only branch:
   a. lookup_phase(args.temperature, args.pressure)
      → quickice/phase_mapping/lookup.py
      → Returns phase_info dict {phase_name, phase_id, density}
   b. generate_candidates(phase_info, nmolecules, n_candidates=10)
      → quickice/structure_generation/__init__.py
      → Returns GenerationResult {candidates, actual_nmolecules, was_rounded}
   c. rank_candidates(gen_result.candidates)
      → quickice/ranking/__init__.py
      → Returns RankingResult {ranked_candidates}
   d. IF args.gromacs:
      i.   write_gro_file(candidate, gro_filepath)           # §4.1
      ii.  write_top_file(candidate, top_filepath)            # §4.2
      iii. shutil.copy(get_tip4p_itp_path(), itp_filepath)    # §4.3
   e. output_ranked_candidates(ranking_result, output_dir, ...) # PDB export
4. Return 0
```

**Error Handling:**
- `UnknownPhaseError` → print to stderr, return 1
- `InterfaceGenerationError` → print to stderr, return 1
- `SystemExit` → re-raise (argparse)
- `Exception` → catch-all, print to stderr, return 1

### 2.2 Full Pipeline Workflow (CLI)

**File:** `quickice/cli/pipeline.py` (lines 30–769)

**Class:** `CLIPipeline`

**Constructor:** `__init__(self, args)` — stores `args`, initializes all result slots to `None`

**Method:** `execute() → int`

### Pipeline Step Dispatch

```
Step 0:  Create output_dir, check --no-overwrite
Step 1:  _run_source_step()     # IF args.interface or args.hydrate
Step 2:  _run_interface_step()  # IF args.interface
Step 3:  _run_custom_step()     # IF args.custom_gro
Step 4:  _run_solute_step()     # IF args.solute_type
Step 5:  _run_ion_step()        # IF args.ion_concentration
Step 6:  _run_export_step()     # ALWAYS
```

**Fail-fast:** Each step returns non-zero on failure → immediate return.

### Step 1: Source Step

**Method:** `_run_source_step()` (line 198)

**Hydrate Branch:**
```
1. HydrateConfig(lattice_type, guest_type, supercell_*, cage_occupancy_*)
   → quickice/structure_generation/types.py:328
   → __post_init__() validates: lattice_type in HYDRATE_LATTICES,
     guest_type in GUEST_MOLECULES, occupancy 0-100, supercell >= 1
2. HydrateStructureGenerator().generate(config)
   → quickice/structure_generation/hydrate_generator.py
3. self._hydrate_result = generator.generate(config)
4. IF args.interface:
   self._ice_candidate = self._hydrate_result.to_candidate()
   → types.py:711 — converts hydrate to Candidate preserving guests
```

**Ice Candidate Branch:**
```
1. lookup_phase(args.temperature, args.pressure)
2. generate_candidates(phase_info, nmolecules, n_candidates=1)
3. self._ice_candidate = gen_result.candidates[0]
```

**Error Handling:** `ValueError` → return 1, `UnknownPhaseError` → return 1

### Step 2: Interface Step

**Method:** `_run_interface_step()` (line 288)

```
1. InterfaceConfig(mode, box_x/y/z, ice/water_thickness, pocket_diameter, seed)
   → types.py:176
   → __post_init__() validates overlap_threshold in [0.1, 1.0] nm
2. generate_interface(self._ice_candidate, config)
   → quickice/structure_generation/interface_builder.py
3. self._interface_result = generate_interface(ice_candidate, config)
```

**Error Handling:** `InterfaceGenerationError` → return 1

### Step 3: Custom Molecule Step

**Method:** `_run_custom_step()` (line 338)

**Input Validation (SEC-02):**
```
1. gro_path.suffix.lower() != '.gro' → report_progress error, return 1
2. itp_path.suffix.lower() != '.itp' → report_progress error, return 1
3. FileNotFoundError if files don't exist
```

**Random Placement Branch:**
```
1. Determine count from --custom-count or --custom-concentration
   → concentration: water_nmolecules * WATER_VOLUME_NM3 * concentration * 1e-24 * AVOGADRO
2. CustomMoleculeConfig(gro_path, itp_path, placement_mode="random", molecule_count=count)
   → types.py:518
   → __post_init__() validates: mode in ("random","custom"),
     min_separation in [0.1, 1.0], max_attempts >= 1
3. CustomMoleculeInserter(config, seed=args.seed)
   → quickice/structure_generation/custom_molecule_inserter.py:47
4. inserter.place_random(source, count) → CustomMoleculeStructure
```

**Custom Placement Branch:**
```
1. _parse_positions_csv(args.custom_positions_file)
   → pipeline.py:140 — 6 columns (x,y,z,alpha,beta,gamma)
2. CustomMoleculeConfig(placement_mode="custom", positions, rotations)
3. inserter.place_custom(source, positions, rotations) → CustomMoleculeStructure
```

**Error Handling:** `FileNotFoundError`, `ValueError`, `InsertionError` → return 1

### Step 4: Solute Step

**Method:** `_run_solute_step()` (line 463)

```
1. _get_source_structure(source_name) — "interface", "custom", or "solute"
2. SoluteConfig(concentration_molar, solute_type)
   → types.py:449
   → __post_init__() validates: concentration >= 0, solute_type in ("CH4","THF"),
     max_attempts >= 1, min_separation > 0
3. SoluteInserter(config, seed=args.seed)
   → quickice/structure_generation/solute_inserter.py:38
4. inserter.insert_solutes(source, config) → SoluteStructure
```

**FIX #7:** `seed=args.seed` passed to SoluteInserter (not omitted).

**Error Handling:** `ValueError`, `FileNotFoundError` → return 1

### Step 5: Ion Step

**Method:** `_run_ion_step()` (line 517)

**Three Source Modes:**

| Source | What happens |
|--------|-------------|
| `interface` | Use `self._interface_result` directly |
| `custom` | Extract `interface` from `custom_structure.interface_structure`, propagate custom molecule attrs with FIX #4 offset (`ice_atom_count + water_atom_count + guest_atom_count`) |
| `solute` | Extract `interface` from `solute_structure.interface_structure`, propagate solute attrs + custom molecule attrs if present |

**FIX #4 Offset:** Custom molecule positions start AFTER `ice_atom_count + water_atom_count + guest_atom_count` (not just ice+water).

```
5. insert_ions(source_for_ions, concentration_molar, liquid_volume_nm3, seed)
   → quickice/structure_generation/ion_inserter.py:552
6. self._ion_result = insert_ions(...)
```

**Error Handling:** `ValueError` → return 1

### Step 6: Export Step

**Method:** `_run_export_step()` (line 649)

**Priority Order (most downstream wins):**
```
ion > solute > custom > interface > hydrate > ice
```

**Writer Dispatch:**

| step_name | GRO Writer | TOP Writer |
|-----------|-----------|------------|
| `ice` | `write_gro_file()` | `write_top_file()` |
| `hydrate` | `write_interface_gro_file(wrapper)` | `write_interface_top_file(wrapper)` |
| `interface` | `write_interface_gro_file()` | `write_interface_top_file()` |
| `custom` | `write_custom_molecule_gro_file()` | `write_custom_molecule_top_file()` |
| `solute` | `write_solute_gro_file()` | `write_solute_top_file()` |
| `ion` | `write_ion_gro_file()` | `write_ion_top_file()` |

**Hydrate Wrapper (FIX #9):**
```
hydrate = structure  # HydrateStructure
water_atom_count = hydrate.water_count * WATER_ATOMS_PER_MOLECULE
guest_atom_count = len(hydrate.positions) - water_atom_count
# ATOM COUNT ASSERTION:
assert water_atom_count + guest_atom_count == len(hydrate.positions), ...
wrapper = InterfaceStructure(
    positions=hydrate.positions, atom_names=hydrate.atom_names,
    cell=hydrate.cell, molecule_index=hydrate.molecule_index,
    mode="hydrate", ice_atom_count=0, water_atom_count=water_atom_count,
    ice_nmolecules=0, water_nmolecules=hydrate.water_count,
    guest_atom_count=guest_atom_count, guest_nmolecules=hydrate.guest_count
)
write_interface_gro_file(wrapper, gro_path)
write_interface_top_file(wrapper, top_path)
```

**ITP Bundling:**
```
copy_itp_files_for_structure(self._output_dir, structure, step_name)
→ quickice/cli/itp_helpers.py:232
```

**Error Handling:** `except (OSError, ValueError)` → return 1 (NOT `Exception`)

---

## 3. GUI Paths

**File:** `quickice/gui/main_window.py`

### 3.1 Tab-to-Export Routing

**Method:** `_on_export_current_tab()` (line 1557)

Triggered by Ctrl+S. Routes by `tab_widget.currentIndex()`:

| Tab | Index | Export Method | Exporter Class |
|-----|-------|--------------|---------------|
| ICE | 0 | `_on_export_gromacs()` | `GROMACSExporter` |
| HYDRATE | 1 | `_on_export_hydrate_gromacs()` | `HydrateGROMACSExporter` |
| INTERFACE | 2 | `_on_export_interface_gromacs()` | `InterfaceGROMACSExporter` |
| SOLUTE | 3 | `_on_export_solute_gromacs()` | `SoluteGROMACSExporter` |
| CUSTOM | 4 | `_on_export_custom_molecule_gromacs()` | `CustomMoleculeGROMACSExporter` |
| ION | 5 | `_on_export_ion_gromacs()` | `IonGROMACSExporter` |

### 3.2 Ice Tab Export

**Method:** `_on_export_gromacs()` (line 1593)

```
1. Get selected candidate from viewer (selected_idx)
2. Get T, P from input panel
3. GROMACSExporter.export_gromacs(ranked, T, P)
   → quickice/gui/export.py:705
   → QFileDialog.getSaveFileName("Export for GROMACS")
   → write_gro_file(candidate, path)
   → write_top_file(candidate, top_path)
   → shutil.copy(get_tip4p_itp_path(), itp_path)
```

### 3.3 Hydrate Tab Export

**Method:** `_on_export_hydrate_gromacs()` (line 1660)

```
1. Check self._current_hydrate_result and self._current_hydrate_config
2. HydrateGROMACSExporter.export_hydrate(structure, config)
   → quickice/gui/hydrate_export.py:90
   → QFileDialog.getSaveFileName("Export Hydrate for GROMACS")
   → MoleculetypeRegistry().register_hydrate_guest(guest_upper) → "CH4_H"/"THF_H"
   → write_multi_molecule_gro_file(positions, molecule_index, cell, path, title, atom_names)
   → write_multi_molecule_top_file(molecule_index, top_path, system_name, itp_files, registry)
   → shutil.copy(tip4p_itp, dest)
   → shutil.copy(guest_itp, dest)
```

### 3.4 Interface Tab Export

**Method:** `_on_export_interface_gromacs()` (line 1635)

```
1. Check self._current_interface_result
2. InterfaceGROMACSExporter.export_interface_gromacs(iface)
   → quickice/gui/export.py:845
   → QFileDialog.getSaveFileName("Export Interface for GROMACS")
   → write_interface_gro_file(interface_structure, path)
   → write_interface_top_file(interface_structure, top_path)
   → shutil.copy(tip4p_itp, dest)
   → IF guest_type detected: shutil.copy(guest_itp, dest)
```

### 3.5 Custom Molecule Tab Export

**Method:** `_on_export_custom_molecule_gromacs()` (line 1762)

```
1. Check self._current_custom_molecule_result
2. CustomMoleculeGROMACSExporter.export_custom_molecule_gromacs(custom_structure)
   → quickice/gui/export.py:199
   → QFileDialog.getSaveFileName("Export Custom Molecule System for GROMACS")
   → write_custom_molecule_gro_file(custom_structure, path)
   → write_custom_molecule_top_file(custom_structure, top_path)
   → comment_out_atomtypes_in_itp(itp_content) → write modified custom ITP
   → shutil.copy(tip4p_itp, dest)
   → IF guest_type detected: shutil.copy(guest_itp, dest)
```

### 3.6 Solute Tab Export

**Method:** `_on_export_solute_gromacs()` (line 1729)

```
1. Check self._current_solute_result
2. SoluteGROMACSExporter.export_solute_gromacs(solute_structure)
   → quickice/gui/export.py:88
   → QFileDialog.getSaveFileName("Export Solutes for GROMACS")
   → write_solute_gro_file(solute_structure, path)
   → write_solute_top_file(solute_structure, top_path)
   → shutil.copy(tip4p_itp, dest)
   → IF guest_type: shutil.copy(guest_itp, dest)
   → IF solute: comment_out_atomtypes_in_itp(solute_itp) → write modified
   → IF custom_molecule_count > 0: comment_out_atomtypes_in_itp(custom_itp) → write modified
```

### 3.7 Ion Tab Export

**Method:** `_on_export_ion_gromacs()` (line 1697)

```
1. Check self._current_ion_result
2. IonGROMACSExporter.export_ion_gromacs(ion_structure)
   → quickice/gui/export.py:302
   → QFileDialog.getSaveFileName("Export Ions for GROMACS")
   → write_ion_gro_file(ion_structure, path)
   → write_ion_top_file(ion_structure, top_path)
   → write_ion_itp(ion_itp_path, na_count, cl_count)           # generates ion.itp
   → shutil.copy(tip4p_itp, dest)
   → IF guest_type: shutil.copy(guest_itp, dest)
   → IF solute: comment_out_atomtypes_in_itp(solute_itp) → write
   → IF custom: comment_out_atomtypes_in_itp(custom_itp) → write
```

### 3.8 GUI Ion Insertion Flow (Source Selection)

**Method:** `_on_insert_ions()` (line 821)

**Three Source Modes:**

| Source | Flow |
|--------|------|
| Interface | `interface = self._current_interface_result` → direct |
| Solute | `interface = solute_structure.interface_structure` → propagate solute attrs to interface via duck-typing |
| Custom Molecule | `interface = custom_structure.interface_structure` → propagate custom attrs with offset |

**Duck-typing attribute propagation on InterfaceStructure:**
```
interface.solute_type = solute_structure.solute_type
interface.solute_positions = solute_structure.positions
interface.solute_atom_names = solute_structure.atom_names
interface.solute_n_molecules = solute_structure.n_molecules
interface.solute_molecule_indices = solute_structure.molecule_indices
interface.solute_registry = solute_structure.registry
```

### 3.9 GUI Solute Insertion Flow

**Method:** `_on_insert_solutes()` (line 983)

| Source | Interface passed to SoluteInserter |
|--------|-----------------------------------|
| Interface | `self._current_interface_result` |
| Custom Molecule | `custom_structure` (full CustomMoleculeStructure — contains interface_structure attribute) |

---

## 4. Shared Export Writer Functions

**File:** `quickice/output/gromacs_writer.py` (2802 lines)

### 4.1 write_gro_file()

**Location:** line 435
**Signature:** `write_gro_file(candidate: Candidate, filepath: str) → None`

**Flow:**
```
1. nmol = candidate.nmolecules
2. n_atoms = nmol * 4  (TIP4P-ICE: OW, HW1, HW2, MW)
3. Build ice_molecule_index: [MoleculeIndex(start_idx=i*3, count=3, mol_type="ice") for i in range(nmol)]
   NOTE: count=3 (O, H, H) for wrapping — MW computed AFTER wrapping
4. wrapped_positions = wrap_molecules_into_box(candidate.positions, ice_molecule_index, candidate.cell)
5. Validate: len(wrapped_positions) >= nmol * 3
6. For each molecule mol_idx:
   a. base_idx = mol_idx * 3
   b. o_pos, h1_pos, h2_pos from wrapped_positions
   c. mw_pos = compute_mw_position(o_pos, h1_pos, h2_pos)
   d. Write 4 lines: OW, HW1, HW2, MW with res_num = (mol_idx+1) % 100000
7. Write box vectors (triclinic format)
```

**Error Handling:** `except (OSError, ValueError)` → unlink partial file, re-raise

### 4.2 write_top_file()

**Location:** line 535
**Signature:** `write_top_file(candidate: Candidate, filepath: str) → None`

**Flow:**
```
1. [defaults]: nbfunc=1, comb-rule=2, gen-pairs=yes, fudgeLJ=0.5, fudgeQQ=0.8333
2. [atomtypes]: OW_ice (σ=TIP4P_ICE_OW_SIGMA, ε=TIP4P_ICE_OW_EPSILON), HW_ice, MW
3. [moleculetype]: SOL, nrexcl=2
4. [atoms]: OW_ice, HW_ice, MW with charges (0, +0.5897, +0.5897, -1.1794)
5. [settles], [virtual_sites3], [exclusions]
6. [system]: phase_id + " exported by QuickIce"
7. [molecules]: SOL  nmol
```

### 4.3 write_interface_gro_file()

**Location:** line 631
**Signature:** `write_interface_gro_file(iface: InterfaceStructure, filepath: str) → None`

**Dual-Wrapping Path (Phase 34.9 update):**
```
1. IF iface.molecule_index:
     wrapped_positions = wrap_molecules_into_box(iface.positions, iface.molecule_index, iface.cell)
   ELSE:
     wrapped_positions = wrap_positions_into_box(iface.positions, iface.cell)

2. PBC-wrap solute positions (if present):
   IF iface.solute_positions is not None AND len > 0:
     wrapped_solute_positions = iface.solute_positions % np.diag(iface.cell)

3. PBC-wrap custom molecule positions (if present):
   IF iface.custom_molecule_positions is not None AND len > 0:
     wrapped_custom_positions = iface.custom_molecule_positions % np.diag(iface.cell)
```

**Ice Molecule Detection (uses detect_atoms_per_molecule):**
```
ice_region_atom_names = iface.atom_names[:ice_end]
has_ow_in_ice = "OW" in ice_region_atom_names
atoms_per_ice_mol = 4 if has_ow_in_ice else 3
```

**Molecule Write Order:** ice → water → guests

**Ice Output:** 3 input atoms (O,H,H) → 4 output atoms (OW,HW1,HW2,MW), MW computed
**Hydrate Ice Output:** 4 input atoms (OW,HW1,HW2,MW) → 4 output atoms, MW from existing
**Water Output:** 4 atoms pass through unchanged

**Error Handling:** `except (OSError, ValueError)` → unlink partial file, re-raise

### 4.4 write_interface_top_file()

**Location:** line 982
**Signature:** `write_interface_top_file(iface: InterfaceStructure, filepath: str) → None`

**Flow:**
```
1. [defaults]: comb-rule=2
2. [atomtypes]: OW_ice (σ=TIP4P_ICE_OW_SIGMA, ε=TIP4P_ICE_OW_EPSILON), HW_ice, MW
3. IF guests: detect guest type → write GAFF2 atomtypes (ch4/thf/co2/h2)
4. #include "tip4p-ice.itp"
5. IF guests: #include "{guest_type}_hydrate.itp"
6. [system]: "Ice/water interface ({mode}) exported by QuickIce"
7. [molecules]: SOL (ice+water combined count), then guest_res_name (guest count)
```

### 4.5 write_custom_molecule_gro_file()

**Location:** line 1918
**Flow:** Molecule order: SOL (ice+water) → guest → custom
- Wrapping: `wrap_molecules_into_box(custom_structure.positions, molecule_index, cell)`
- Custom molecule atom names from `custom_structure.atom_names[mol.start_idx:mol.start_idx+mol.count]`
- Residue name: `custom_structure.moleculetype_name[:5]`

**Error Handling:** `except (OSError, ValueError)` → unlink, re-raise

### 4.6 write_custom_molecule_top_file()

**Location:** line 2140
**Flow:**
```
1. [defaults]: comb-rule=2
2. [atomtypes]: OW_ice (TIP4P_ICE_OW_SIGMA/EPSILON), HW_ice, MW
3. IF guests: GAFF2 atomtypes (ch4/thf)
4. _written_atomtypes tracking for deduplication
5. IF custom ITP exists: parse_itp_atomtypes(custom_itp_path) → write non-duplicate atomtypes
6. #include "tip4p-ice.itp"
7. IF guests: #include "{guest_type}_hydrate.itp"
8. #include "{custom_structure.itp_path.name}"
9. [molecules]: SOL, guest (if present), custom_mol_name
```

### 4.7 write_solute_gro_file()

**Location:** line 2273
**Signature:** `write_solute_gro_file(solute_structure: SoluteStructure, filepath: str) → None`

**Flow:**
```
1. interface = solute_structure.interface_structure
2. Build ordered_mols: SOL (ice+water) → guest → custom → solute
   FALLBACK when molecule_index empty: build synthetic entries from counts
3. Count total atoms
4. IF interface.molecule_index:
     wrapped_positions = wrap_molecules_into_box(interface.positions, interface.molecule_index, interface.cell)
   ELSE:
     wrapped_positions = wrap_positions_into_box(interface.positions, interface.cell)
5. Write molecules in order:
   - SOL: ice (3→4 or 4→4) and water (4→4)
   - Guest: detect type, get residue name, reorder atoms
   - Custom: from solute_structure.custom_molecule_* attributes
   - Solute: from solute_structure.positions, residue name from registry
6. Box vectors
```

**Error Handling:** `except (OSError, ValueError)` → unlink, re-raise

### 4.8 write_solute_top_file()

**Location:** line 2603
**Flow:**
```
1. [defaults]: comb-rule=2
2. [atomtypes]: OW_ice (TIP4P_ICE_OW_SIGMA/EPSILON), HW_ice, MW
3. GAFF2 atomtypes: needs_ch4_atomtypes / needs_thf_atomtypes
   (combined guest AND solute detection)
4. _written_atomtypes deduplication
5. IF custom ITP: parse + write non-duplicate custom atomtypes
6. #include "tip4p-ice.itp"
7. IF guests: #include "{guest_type}_hydrate.itp"
8. IF custom: #include "{custom_itp_name}"
9. IF solutes: #include "{solute_type_lower}_liquid.itp"
10. [molecules]: SOL, guest, custom, solute
```

### 4.9 write_ion_gro_file()

**Location:** line 1349
**Signature:** `write_ion_gro_file(ion_structure: IonStructure, filepath: str) → None`

**Flow:**
```
1. Build ordered_mols in 6 passes:
   Pass 1: SOL (ice + water)
   Pass 2: guest molecules (mol_type == "guest")
   Pass 3: custom molecules (from ion_structure.custom_molecule_*)
   Pass 4: solute molecules (from ion_structure.solute_*)
   Pass 5: NA ions
   Pass 6: CL ions
2. Count total atoms
3. wrapped_positions = wrap_molecules_into_box(ion_structure.positions, ion_structure.molecule_index, ion_structure.cell)
4. Dual PBC-wrapping (AN-03 fix):
   IF solute_positions is not None AND len > 0:
     wrapped_solute_positions = ion_structure.solute_positions % np.diag(ion_structure.cell)
   IF custom_molecule_positions is not None AND len > 0:
     wrapped_custom_positions = ion_structure.custom_molecule_positions % np.diag(ion_structure.cell)
5. Write all molecules in ordered_mols order
6. Box vectors
```

**Error Handling:** `except (OSError, ValueError)` → unlink, re-raise

### 4.10 write_ion_top_file()

**Location:** line 1702
**Flow:**
```
1. Count: sol_count, guest_count, na_count, cl_count, custom_count, solute_count
2. Detect guest_type from atom_names (for correct .itp)
3. Parse custom_mol_name from ITP (Bug 2 fix)
4. Determine needs_ch4_atomtypes / needs_thf_atomtypes (combined guest+solute)
5. [defaults]: comb-rule=2
6. [atomtypes]:
   - OW_ice (TIP4P_ICE_OW_SIGMA/EPSILON), HW_ice, MW
   - IF ions: Madrid2019 NA/CL atomtypes
   - IF needs_ch4: GAFF2 c3, hc
   - IF needs_thf: GAFF2 os, c5, hc, h1
   - _written_atomtypes tracking for dedup
   - IF custom: parse_itp_atomtypes + dedup write
7. #include "tip4p-ice.itp"
8. IF guests: #include "{guest_type}_hydrate.itp"
9. IF custom: #include "{custom_itp_name}"
10. IF solutes: #include "{solute_type_lower}_liquid.itp"
11. #include "ion.itp"
12. [system]
13. [molecules]: SOL, guest, custom, solute, NA, CL
```

### 4.11 write_multi_molecule_gro_file()

**Location:** line 1092
**Used by:** Hydrate export

**Flow:**
```
1. n_atoms = len(positions)
2. For each MoleculeIndex in molecule_index:
   a. Get residue name (guest → get_guest_residue_name, else MOLECULE_TO_GROMACS)
   b. Reorder guest atoms (ch4/thf) to match .itp canonical order
   c. Write atoms with position
3. Box vectors
```

### 4.12 write_multi_molecule_top_file()

**Location:** line 1189
**Used by:** Hydrate export

**Flow:**
```
1. Count molecules by type → unique_types
2. Build [molecules] entries (registry-aware for hydrate/liquid naming)
3. Build ITP include list
4. [defaults]: comb-rule=2
5. [atomtypes]: OW_ice (TIP4P_ICE_OW_SIGMA/EPSILON), HW_ice, MW
   + Madrid2019 NA/CL if present
   + GAFF2 ch4/thf/co2/h2 if present
6. #include directives for each unique molecule type
7. [system], [molecules]
```

### 4.13 compute_mw_position()

**Location:** line 611
**Signature:** `compute_mw_position(o_pos, h1_pos, h2_pos) → np.ndarray`

**Formula:** `MW = O + α*(H1-O) + α*(H2-O)` where `α = TIP4P_ICE_ALPHA = 0.13458335`

---

## 5. PBC Wrapping: Dual-Wrapping Path

**Phase 34.9 introduced dual-wrapping** in `write_interface_gro_file()` and `write_ion_gro_file()`.

### Primary Wrapping (molecule positions)

**Function:** `wrap_molecules_into_box(positions, molecule_index, cell)` → line 67

**Algorithm:**
```
For each molecule in molecule_index:
  1. Get mol_positions = positions[start:start+count]
  2. Unwrap atoms split across PBC:
     - For each atom after the first, check distance to reference
     - If delta > box_size/2: shift back by box_size
     - If delta < -box_size/2: shift forward by box_size
  3. Wrap whole molecule into [0, box_size):
     - Compute center = mean(mol_positions)
     - Wrap center via np.mod(center, box_size)
     - Apply shift to all atoms
```

**Fallback:** `wrap_positions_into_box(positions, cell)` → line 46
- Atom-by-atom `np.mod(positions[:,dim], cell[dim,dim])`

### Secondary Wrapping (solute/custom positions)

**In `write_interface_gro_file()` (lines 686–695):**
```python
wrapped_solute_positions = iface.solute_positions % np.diag(iface.cell)
wrapped_custom_positions = iface.custom_molecule_positions % np.diag(iface.cell)
```

**In `write_ion_gro_file()` (lines 1443–1455):**
```python
wrapped_solute_positions = ion_structure.solute_positions % np.diag(ion_structure.cell)
wrapped_custom_positions = ion_structure.custom_molecule_positions % np.diag(ion_structure.cell)
```

**Rationale:** Solute/custom molecules are single molecules that don't span PBC boundaries, so simple modulo wrapping is sufficient (AN-03 fix).

### Guard Conditions

Both wrapping paths check `is not None AND len > 0` before wrapping:
```python
if hasattr(iface, 'solute_positions') and iface.solute_positions is not None and len(iface.solute_positions) > 0:
    wrapped_solute_positions = iface.solute_positions % np.diag(iface.cell)
```

---

## 6. TIP4P-ICE LJ Constants Flow

**Defined in:** `quickice/output/gromacs_writer.py` (lines 25–28)

```python
TIP4P_ICE_OW_SIGMA = 3.16680e-1    # nm
TIP4P_ICE_OW_EPSILON = 8.82110e-1   # kJ/mol
```

**Source:** Abascal et al. 2005, DOI: 10.1063/1.1931662
- σ_O = 3.1668 Å = 0.31668 nm
- ε_O/k_B = 106.1 K → 106.1 × 0.00831446 = 0.88211 kJ/mol

### Flow into TOP Files

All 6 TOP-writing functions use these constants identically:

| Function | File:Line | Usage |
|----------|----------|-------|
| `write_top_file()` | gromacs_writer.py:557 | `f"OW_ice ... {TIP4P_ICE_OW_SIGMA:.5e} {TIP4P_ICE_OW_EPSILON:.5e}"` |
| `write_interface_top_file()` | gromacs_writer.py:1011 | Same format |
| `write_multi_molecule_top_file()` | gromacs_writer.py:1292 | Same format |
| `write_custom_molecule_top_file()` | gromacs_writer.py:2201 | Same format |
| `write_solute_top_file()` | gromacs_writer.py:2711 | Same format |
| `write_ion_top_file()` | gromacs_writer.py:1795 | Same format |

**All output the same line:**
```
OW_ice   OW_ice    8             15.9994  0.0     A      3.16680e-1    8.82110e-1
```

**No other LJ parameters** are parameterized via module constants — guest/solute/ion atomtypes are hardcoded within each function.

---

## 7. comb-rule=2 Flow

**All 6 TOP-writing functions now write:** `comb-rule = 2` (Lorentz-Berthelot)

**[defaults] section in every TOP file:**
```
[ defaults ]
; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ
; comb-rule=2 (Lorentz-Berthelot): sigma_ij=(sigma_i+sigma_j)/2, epsilon_ij=sqrt(eps_i*eps_j)
; Matches AMBER/GAFF2 convention used by GROMACS-bundled AMBER force fields
1               2               yes             0.5     0.8333
```

**Values:**
- `nbfunc = 1` (Lennard-Jones)
- `comb-rule = 2` (Lorentz-Berthelot)
- `gen-pairs = yes`
- `fudgeLJ = 0.5`
- `fudgeQQ = 0.8333`

**Files that write this section:**

| Function | File:Line |
|----------|-----------|
| `write_top_file()` | gromacs_writer.py:549 |
| `write_interface_top_file()` | gromacs_writer.py:1001 |
| `write_multi_molecule_top_file()` | gromacs_writer.py:1279 |
| `write_custom_molecule_top_file()` | gromacs_writer.py:2189 |
| `write_solute_top_file()` | gromacs_writer.py:2701 |
| `write_ion_top_file()` | gromacs_writer.py:1784 |

**Comment in each function:**
```
; comb-rule=2 (Lorentz-Berthelot): sigma_ij=(sigma_i+sigma_j)/2, epsilon_ij=sqrt(eps_i*eps_j)
; Matches AMBER/GAFF2 convention used by GROMACS-bundled AMBER force fields
```

---

## 8. Conditional cKDTree Rebuild

**Implemented in both ion_inserter and solute_inserter (TREE-01 / Plan 08 / V-03)**

### 8.1 Ion Inserter — Conditional Rebuild

**File:** `quickice/structure_generation/ion_inserter.py` (lines 363–391)

**Before the loop:**
```python
ion_tree = None  # KDTree for ion-ion overlap checking (rebuilt only on successful placement)
```

**In the loop (line 366):**
```python
for i, water_idx in enumerate(selected):
    water_mol = water_mols[water_idx]
    water_pos = structure.positions[water_mol.start_idx]
    
    # Check against ice/guest framework
    if existing_atoms_tree is not None:
        min_dist = existing_atoms_tree.query(water_pos, k=1)[0]
        if min_dist < MIN_SEPARATION:
            continue  # Skip — NO rebuild
    
    # Check against previously placed ions
    if ion_tree is not None:
        min_ion_dist = ion_tree.query(water_pos, k=1)[0]
        if min_ion_dist < MIN_SEPARATION:
            continue  # Skip — NO rebuild
    
    # VALID placement reached — rebuild ion_tree
    ion_positions.append(water_pos)
    ion_tree = cKDTree(np.array(ion_positions))  # Rebuild ONLY on success
```

**Decision Path:**
```
Overlap with framework? → continue (skip, no rebuild)
Overlap with ions?      → continue (skip, no rebuild)
Valid placement?        → append to ion_positions, rebuild ion_tree
```

### 8.2 Solute Inserter — Conditional Rebuild

**File:** `quickice/structure_generation/solute_inserter.py` (lines 815–876)

**Before the loop:**
```python
combined_tree_data = existing_tree.data.copy() if existing_tree is not None else np.zeros((0, 3))
```

**In the loop (line 830):**
```python
for mol_idx in range(n_molecules):
    for attempt in range(config.max_attempts):
        # Generate position + rotation
        solute_positions = rotated_positions + position
        
        # Check overlap
        if existing_tree is not None:
            if self._check_solute_overlap(solute_positions, existing_tree, config.min_separation):
                continue  # Try again — NO rebuild
        
        # Valid placement
        placed_positions.append(solute_positions)
        placed_count += 1
        placed = True
        
        # Conditional rebuild (V-03 fix)
        combined_tree_data = np.vstack([combined_tree_data, solute_positions])
        existing_tree = cKDTree(combined_tree_data)
        
        break  # Move to next molecule
```

**Decision Path:**
```
Overlap detected? → continue (try again, no rebuild)
Valid placement?  → vstack new positions to combined_tree_data, rebuild cKDTree
```

**Performance:** O(N) rebuilds for N placed solutes (not O(N×A) where A=max_attempts).

### 8.3 Custom Molecule Inserter — Tree Rebuild

**File:** `quickice/structure_generation/custom_molecule_inserter.py` (lines 641–649)

**Different pattern — rebuilds from base data + all placed positions:**
```python
if base_existing_data is not None and len(placed_positions) > 0:
    all_data = np.vstack([base_existing_data, np.vstack(placed_positions)])
    existing_tree = cKDTree(all_data)
```

**Decision Path:**
```
Overlap? → continue (no rebuild)
Valid?   → rebuild from base_existing_data + ALL placed positions (avoids O(N²) copy chain)
```

---

## 9. detect_atoms_per_molecule Call Chain

**Function:** `detect_atoms_per_molecule(atom_names: list[str]) → int`
**File:** `quickice/structure_generation/types.py` (line 28)

**Algorithm:**
```python
if len(atom_names) >= 4 and atom_names[0] == "OW":
    return 4  # TIP4P (hydrate)
return 3  # Default to GenIce ice (3 atoms)
```

### Call Sites

| Caller | File | Context |
|--------|------|---------|
| `write_interface_gro_file()` | gromacs_writer.py:719–721 | Detects ice region atom type: `has_ow_in_ice = "OW" in ice_region_atom_names` → `atoms_per_ice_mol = 4 if has_ow_in_ice else 3` |
| `write_ion_gro_file()` | gromacs_writer.py:1487–1499 | For ice molecules in ordered_mols: `if mol.count == 3: compute_mw_position(...)` else use existing MW |
| `write_custom_molecule_gro_file()` | gromacs_writer.py:1991–2003 | Same pattern as ion writer |
| `write_solute_gro_file()` | gromacs_writer.py:2305–2312 | Fallback when molecule_index empty: `atoms_per_ice_mol = 3 if "O" in ... else 4` |

**Note:** The interface/solute writers check for "OW" in atom names rather than calling `detect_atoms_per_molecule()` directly, but use the same logic: "OW" at position 0 → 4 atoms, else → 3 atoms.

### Where detect_atoms_per_molecule IS called directly

The function is also used by the structure generation modules to determine ice molecule type during candidate creation and interface building.

---

## 10. Mutation-Free Solute Inserter

**Phase 37.1 change:** SoluteInserter._remove_overlapping_water() no longer mutates the input InterfaceStructure.

**File:** `quickice/structure_generation/solute_inserter.py`

### Old (mutating) behavior

Previously, `_remove_overlapping_water()` set attributes directly on the input `structure`:
```python
structure.custom_molecule_count = ...
structure.custom_molecule_positions = ...
# etc. — MUTATES input
```

### New (mutation-free) behavior

**Method:** `_remove_overlapping_water()` (line 378)

**When no water molecules removed:**
```python
if removed_count == 0:
    if not has_custom_molecules:
        return structure  # Safe to return original (no custom mol attrs)
    # BUILD NEW InterfaceStructure with custom molecule attrs
    new_interface = InterfaceStructure(
        positions=structure.positions,
        atom_names=structure.atom_names,
        cell=structure.cell,
        ice_atom_count=structure.ice_atom_count,
        water_atom_count=water_atom_count,
        ...
    )
    new_interface.custom_molecule_count = getattr(structure, 'custom_molecule_count', 0)
    new_interface.custom_molecule_atom_count = structure.custom_molecule_atom_count
    new_interface.custom_molecule_positions = custom_positions
    # ... set attrs on NEW interface, NOT on input
    return new_interface
```

**When water molecules removed:**
```python
# Build new positions, atom_names, molecule_index
new_interface = InterfaceStructure(
    positions=new_positions,
    atom_names=new_atom_names,
    cell=structure.cell,
    ice_atom_count=structure.ice_atom_count,
    water_atom_count=len(kept_water_atom_names),
    ...
)
# Preserve custom molecule attributes if present
if has_custom_molecules:
    new_interface.custom_molecule_count = structure.custom_molecule_count
    # ... etc.
return new_interface
```

**Impact on downstream:** The returned `new_interface` is what gets stored as `SoluteStructure.interface_structure`, preserving custom molecule data without corrupting the original input.

---

## 11. Error Handling and Input Validation

### 11.1 Pipeline Error Handling (ValueError, OSError)

**CLI Pipeline — `quickice/cli/pipeline.py`:**

Each step catches specific exception types:
- `_run_source_step()`: `ValueError`, `UnknownPhaseError`, `ImportError`
- `_run_interface_step()`: `InterfaceGenerationError`, `ImportError`
- `_run_custom_step()`: `FileNotFoundError`, `ValueError`, `InsertionError`, `ImportError`
- `_run_solute_step()`: `ValueError`, `FileNotFoundError`, `ImportError`
- `_run_ion_step()`: `ValueError`, `ImportError`
- `_run_export_step()`: `(OSError, ValueError)`, `ImportError`

**NOT `Exception`** — each catches specific types only.

### 11.2 GRO I/O Protection

**All GRO writers:** `except (OSError, ValueError)` → logger.error → unlink partial file → re-raise

```python
try:
    with open(filepath, 'w') as f:
        ...
except (OSError, ValueError) as e:
    logger.error(f"Failed to write GRO file '{filepath}': {e}")
    if Path(filepath).exists():
        Path(filepath).unlink()
    raise
```

**Applies to:** `write_gro_file()`, `write_interface_gro_file()`, `write_ion_gro_file()`, `write_custom_molecule_gro_file()`, `write_solute_gro_file()`

### 11.3 Hydrate Wrapper Atom Count Assertion

**In `_run_export_step()` (pipeline.py:720):**
```python
assert water_atom_count + guest_atom_count == len(hydrate.positions), \
    f"Atom count mismatch: water_atom_count({water_atom_count}) + " \
    f"guest_atom_count({guest_atom_count}) != " \
    f"total positions({len(hydrate.positions)})"
```

### 11.4 Concentration Range Validation

**File:** `quickice/validation/validators.py`

**`validate_concentration_range(value)`** (line 150):
- Range: `[0.0, 5.0]` mol/L
- Used as argparse type converter

**`validate_occupancy_range(value)`** (line 179):
- Range: `[0.0, 100.0]` percent
- Used for cage occupancy

**SoluteConfig.__post_init__()** (types.py:466):
- `concentration_molar >= 0`
- `solute_type in ("CH4", "THF")`
- `max_attempts >= 1`
- `min_separation > 0`

**IonConfig.__post_init__()** (types.py:390):
- `concentration_molar >= 0`

**CustomMoleculeConfig.__post_init__()** (types.py:540):
- `placement_mode in ("random", "custom")`
- `min_separation in [0.1, 1.0]`
- `max_attempts >= 1`

### 11.5 File Extension Validation

**CLI `_run_custom_step()` (pipeline.py:370–381):**
```python
if gro_path.suffix.lower() != '.gro':
    report_progress("Error: --custom-gro file must have .gro extension...")
    return 1
if itp_path.suffix.lower() != '.itp':
    report_progress("Error: --custom-itp file must have .itp extension...")
    return 1
```

**GUI exporters** ensure `.gro` extension in save dialog:
```python
if path.suffix.lower() != '.gro':
    path = path.with_suffix('.gro')
```

---

## 12. ITP File Bundling

### 12.1 CLI ITP Bundling

**Function:** `copy_itp_files_for_structure(output_dir, structure, step_name, args_ref=None)`
**File:** `quickice/cli/itp_helpers.py` (line 232)

**Per-step ITP requirements:**

| Step | Required ITP Files |
|------|--------------------|
| `ice` | tip4p-ice.itp |
| `hydrate` | tip4p-ice.itp + `{guest_type}_hydrate.itp` |
| `interface` | tip4p-ice.itp + `{guest_type}_hydrate.itp` (if guests) |
| `custom` | tip4p-ice.itp + custom `.itp` (atomtypes commented) + `{guest_type}_hydrate.itp` (if guests) |
| `solute` | tip4p-ice.itp + `{solute}_liquid.itp` (atomtypes commented) + custom `.itp` (if custom_molecule_count > 0) + `{guest_type}_hydrate.itp` (if guests) |
| `ion` | tip4p-ice.itp + ion.itp (generated) + `{solute}_liquid.itp` (if solutes) + custom `.itp` (if custom) + `{guest_type}_hydrate.itp` (if guests) |

**ITP path resolution functions:**

| Function | File:Line | Returns |
|----------|-----------|---------|
| `get_tip4p_itp_path()` | itp_helpers.py:66 | Path to `tip4p-ice.itp` |
| `get_hydrate_guest_itp_path(guest_type)` | itp_helpers.py:20 | Path to `{guest_type}_hydrate.itp` |
| `get_solute_liquid_itp_path(solute_type)` | itp_helpers.py:43 | Path to `{solute_type}_liquid.itp` |

**Atomtypes commenting:**
```python
_copy_itp_with_atomtypes_commented(source, dest)
→ comment_out_atomtypes_in_itp(content)  # from gromacs_writer.py:319
→ Writes modified content to dest
```

### 12.2 GUI ITP Bundling

Each GUI exporter handles ITP copying independently:

| Exporter | ITP Files |
|----------|-----------|
| `GROMACSExporter` | tip4p-ice.itp (shutil.copy) |
| `HydrateGROMACSExporter` | tip4p-ice.itp + `{guest}_hydrate.itp` |
| `InterfaceGROMACSExporter` | tip4p-ice.itp + `{guest}_hydrate.itp` (if guests) |
| `CustomMoleculeGROMACSExporter` | tip4p-ice.itp + custom `.itp` (atomtypes commented) + `{guest}_hydrate.itp` |
| `SoluteGROMACSExporter` | tip4p-ice.itp + `{solute}_liquid.itp` (atomtypes commented) + custom `.itp` (if custom) + `{guest}_hydrate.itp` |
| `IonGROMACSExporter` | tip4p-ice.itp + ion.itp (generated) + `{solute}_liquid.itp` + custom `.itp` + `{guest}_hydrate.itp` |

### 12.3 ion.itp Generation

**Function:** `write_ion_itp(output_path, na_count, cl_count)`
**File:** `quickice/structure_generation/gromacs_ion_export.py` (line 81)

**Content:** Madrid2019 parameters for NA and CL moleculetypes with:
- NA: charge=0.85, mass=22.9898
- CL: charge=-0.85, mass=35.453

---

## 13. MoleculetypeRegistry Naming

**File:** `quickice/structure_generation/moleculetype_registry.py`

### Registration Methods

| Method | Returns | Context |
|--------|---------|---------|
| `register_hydrate_guest("CH4")` | `"CH4_H"` | Hydrate cage guests |
| `register_hydrate_guest("THF")` | `"THF_H"` | Hydrate cage guests |
| `register_liquid_solute("CH4")` | `"CH4_L"` | Dissolved in liquid |
| `register_liquid_solute("THF")` | `"THF_L"` | Dissolved in liquid |
| `register_custom_molecule("MOL")` | `"MOL"` (first), `"MOL_1"` (collision) | User-provided molecules |

### Name Resolution

```python
registry.get_gromacs_name("hydrate_CH4")  # → "CH4_H"
registry.get_gromacs_name("liquid_CH4")   # → "CH4_L"
registry.get_gromacs_name("custom_1")      # → "MOL"
registry.get_gromacs_name("unknown")       # → "UNKNOWN" (fallback)
```

### RESERVED_NAMES

```python
RESERVED_NAMES = {"SOL", "NA", "CL", "CH4", "THF", "CO2", "H2",
                  "CH4_H", "CH4_L", "THF_H", "THF_L"}
```

Custom molecules cannot use these names → `ValueError` raised.

### Where Registry is Used

| Location | How |
|----------|-----|
| HydrateGROMACSExporter.export_hydrate() | `register_hydrate_guest()` → `write_multi_molecule_top_file(registry=registry)` |
| SoluteInserter.insert_solutes() | `self.registry.register_liquid_solute(solute_type)` → stored in SoluteStructure |
| CustomMoleculeInserter.place_random() | `self.registry.register_custom_molecule()` → stored in CustomMoleculeStructure |
| write_solute_top_file() | `solute_structure.registry.get_gromacs_name(f"liquid_{solute_type}")` |
| write_ion_top_file() | `ion_structure.solute_registry.get_gromacs_name(f"liquid_{solute_type}")` |
| write_multi_molecule_top_file() | Checks registry for hydrate/liquid keys before falling back to standard names |

---

## 14. Full Chain: F1–F7 (CLI)

### F1: Ice-Only

```
$ quickice -T 250 -P 0.1 --gromacs -N 256

entry.main() → _has_pipeline_flags(argv)=True
  → quickice.main.main()
    → get_arguments() → args
    → no pipeline flags → ice-only branch
    → lookup_phase(250, 0.1)
    → generate_candidates(phase_info, 256, n_candidates=10)
    → rank_candidates(candidates)
    → write_gro_file(candidate, path)
    → write_top_file(candidate, path)
    → shutil.copy(tip4p_itp, dest)
    → output_ranked_candidates(...)
  → return 0
```

### F2: Interface Only

```
$ quickice --interface -T 250 -P 0.1 --mode slab --box-x 4 --box-y 4 --box-z 8 --ice-thickness 3 --water-thickness 3 --gromacs

entry.main() → pipeline flags
  → quickice.main.main() → CLIPipeline(args).execute()
    → Step 1: _run_source_step() → generate ice candidate
    → Step 2: _run_interface_step() → generate_interface(candidate, InterfaceConfig)
    → Step 6: _run_export_step() → step_name="interface"
      → write_interface_gro_file(interface, gro_path)
      → write_interface_top_file(interface, top_path)
      → copy_itp_files_for_structure(dir, interface, "interface")
```

### F3: Interface → Custom

```
$ quickice --interface ... --custom-gro mol.gro --custom-itp mol.itp --custom-count 5 ...

→ Step 1: source
→ Step 2: interface
→ Step 3: custom
  → CustomMoleculeInserter(config, seed).place_random(interface, count)
  → self._custom_result = result
→ Step 6: export → step_name="custom"
  → write_custom_molecule_gro_file(custom_result, gro_path)
  → write_custom_molecule_top_file(custom_result, top_path)
  → copy_itp_files_for_structure(dir, custom_result, "custom")
    → tip4p-ice.itp + custom .itp (atomtypes commented) + guest .itp (if guests)
```

### F4: Interface → Solute

```
$ quickice --interface ... --solute-type CH4 --solute-concentration 0.5 ...

→ Step 1: source
→ Step 2: interface
→ Step 4: solute
  → SoluteInserter(config, seed).insert_solutes(interface, config)
  → self._solute_result = result
→ Step 6: export → step_name="solute"
  → write_solute_gro_file(solute_result, gro_path)
  → write_solute_top_file(solute_result, top_path)
  → copy_itp_files_for_structure(dir, solute_result, "solute")
    → tip4p-ice.itp + ch4_liquid.itp (atomtypes commented) + guest .itp (if guests)
```

### F5: Interface → Ion

```
$ quickice --interface ... --ion-concentration 0.15 ...

→ Step 1: source
→ Step 2: interface
→ Step 5: ion
  → insert_ions(interface, concentration, liquid_volume, seed)
  → self._ion_result = result
→ Step 6: export → step_name="ion"
  → write_ion_gro_file(ion_result, gro_path)
  → write_ion_top_file(ion_result, top_path)
  → copy_itp_files_for_structure(dir, ion_result, "ion")
    → tip4p-ice.itp + ion.itp + guest .itp (if guests)
```

### F6: Interface → Custom → Solute

```
→ Step 3: custom → CustomMoleculeInserter.place_random(interface, count)
→ Step 4: solute → source=custom
  → SoluteInserter(config, seed).insert_solutes(custom_result, config)
  → SoluteInserter._remove_overlapping_water(structure, all_positions, min_separation)
  → Returns NEW InterfaceStructure (mutation-free) with custom molecule attrs
  → self._solute_result = SoluteStructure(interface_structure=new_interface, custom_molecule_count=..., ...)
→ Step 6: export → step_name="solute"
  → write_solute_gro_file(solute_result, gro_path)
  → write_solute_top_file(solute_result, top_path)
  → copy_itp_files_for_structure(dir, solute_result, "solute")
    → tip4p-ice.itp + ch4_liquid.itp + custom .itp + guest .itp (if guests)
```

### F7: Interface → Custom → Solute → Ion (Full Chain)

```
→ Step 3: custom → custom_result
→ Step 4: solute → source=custom → solute_result
  → Custom molecule attrs preserved in solute_result
→ Step 5: ion → source=solute
  → interface = solute_result.interface_structure
  → interface.solute_type = solute_result.solute_type
  → interface.solute_positions = solute_result.positions
  → interface.solute_atom_names = solute_result.atom_names
  → interface.solute_n_molecules = solute_result.n_molecules
  → interface.solute_molecule_indices = solute_result.molecule_indices
  → interface.solute_registry = solute_result.registry
  → IF custom molecules: interface.custom_molecule_* = solute_result.custom_molecule_*
  → insert_ions(interface, concentration, liquid_volume, seed)
  → self._ion_result = result (preserves solute + custom info)
→ Step 6: export → step_name="ion"
  → write_ion_gro_file(ion_result, gro_path)
    → Dual-wrapping: main positions + solute % diag(cell) + custom % diag(cell)
    → Write order: SOL → guest → custom → solute → NA → CL
  → write_ion_top_file(ion_result, top_path)
    → [atomtypes]: OW_ice (TIP4P_ICE constants), HW_ice, MW, NA, CL, GAFF2 (if needed)
    → Dedup: _written_atomtypes tracking
    → Custom atomtypes from ITP (dedup)
    → [molecules]: SOL, guest, custom, solute, NA, CL
  → copy_itp_files_for_structure(dir, ion_result, "ion")
    → tip4p-ice.itp + ion.itp + ch4_liquid.itp + custom.itp + guest_hydrate.itp
```

---

## 15. Full Chain: Ice→Ion (GUI)

### Step-by-Step Flow

**1. User generates ice candidate (Ice tab):**
```
InputPanel → on_generate_clicked → worker → generate_candidates → rank_candidates
→ self._current_result = RankingResult
→ viewer displays candidates
```

**2. User generates interface (Interface tab):**
```
InterfacePanel → on_generate_clicked → generate_interface(candidate, InterfaceConfig)
→ self._current_interface_result = InterfaceStructure
```

**3. User inserts custom molecules (Custom tab):**
```
CustomMoleculePanel → _on_custom_generate_clicked
→ CustomMoleculeInserter(config, seed).place_random(self._current_interface_result, count)
→ self._current_custom_molecule_result = CustomMoleculeStructure
```

**4. User inserts solutes (Solute tab):**
```
SolutePanel → _on_insert_solutes
→ SoluteInserter(config).insert_solutes(custom_structure, config)
   (source=Custom → passes full CustomMoleculeStructure)
→ self._current_solute_result = SoluteStructure
→ Custom molecule attrs preserved through mutation-free _remove_overlapping_water()
```

**5. User inserts ions (Ion tab, source=Solute):**
```
IonPanel → _on_insert_ions
→ source = solute_structure.interface_structure
→ Propagate solute attrs via duck-typing:
   interface.solute_type = ...
   interface.solute_positions = ...
   etc.
→ Custom molecule attrs already on interface from step 4
→ insert_ions(interface, concentration, volume, seed)
→ self._current_ion_result = IonStructure (with solute + custom attrs)
```

**6. User exports (Ion tab, Ctrl+S or Ctrl+J):**
```
_on_export_ion_gromacs()
→ IonGROMACSExporter.export_ion_gromacs(self._current_ion_result)
→ write_ion_gro_file(ion_structure, path)
→ write_ion_top_file(ion_structure, top_path)
→ write_ion_itp(ion_itp_path, na_count, cl_count)
→ shutil.copy(tip4p_itp, dest)
→ Copy guest/solute/custom ITP files (with atomtypes commented where needed)
```

### Molecule Write Order in Final Export

**GRO file order (write_ion_gro_file):**
```
SOL (ice)    → 3→4 atoms (MW computed) or 4→4 atoms
SOL (water)  → 4 atoms pass-through
guest        → native atoms, reordered for .itp
custom       → from ion_structure.custom_molecule_positions (PBC-wrapped)
solute       → from wrapped_solute_positions (PBC-wrapped via % np.diag)
NA           → 1 atom
CL           → 1 atom
```

**TOP file [molecules] order:**
```
SOL              {sol_count}
{guest_res_name} {guest_count}
{custom_mol_name} {custom_count}
{solute_mol_name} {solute_count}
NA               {na_count}
CL               {cl_count}
```

---

## Appendix A: Data Structure Flow Summary

```
Candidate           → write_gro_file / write_top_file (ice-only)
  ├── positions (N*3, 3) nm
  ├── atom_names ["O","H","H",...]
  ├── cell (3,3) nm
  ├── nmolecules
  └── phase_id

InterfaceStructure → write_interface_gro/top_file (interface/hydrate)
  ├── positions (ice+water+guest)
  ├── atom_names
  ├── cell
  ├── ice_atom_count, water_atom_count, guest_atom_count
  ├── ice_nmolecules, water_nmolecules, guest_nmolecules
  ├── molecule_index
  ├── solute_* attrs (when populated by duck-typing)
  └── custom_molecule_* attrs (when populated by duck-typing)

CustomMoleculeStructure → write_custom_molecule_gro/top_file
  ├── positions (ice+water+guest+custom, COMPLETE system)
  ├── molecule_index (ice, water, guest, custom)
  ├── ice_atom_count, water_atom_count, custom_molecule_atom_count
  ├── moleculetype_name (from registry)
  ├── itp_path (user's .itp file)
  └── interface_structure (original interface, for downstream use)

SoluteStructure → write_solute_gro/top_file
  ├── positions (solute-only atoms)
  ├── atom_names (solute atoms)
  ├── solute_type, n_molecules, molecule_indices
  ├── registry (MoleculetypeRegistry with liquid_ registration)
  ├── interface_structure (MODIFIED by _remove_overlapping_water, mutation-free)
  └── custom_molecule_* attrs (propagated from source)

IonStructure → write_ion_gro/top_file
  ├── positions (water+ice+guest, NOT solute/custom)
  ├── molecule_index (ice, water, guest, na, cl)
  ├── na_count, cl_count
  ├── solute_* attrs (propagated from source)
  └── custom_molecule_* attrs (propagated from source)
```

## Appendix B: PBC Wrapping Decision Tree

```
Is molecule_index available?
├── YES → wrap_molecules_into_box(positions, molecule_index, cell)
│         └── For each molecule: unwrap PBC-split atoms → wrap whole molecule
└── NO  → wrap_positions_into_box(positions, cell)
          └── Atom-by-atom np.mod(positions[:,dim], cell[dim,dim])

Are solute_positions present?
├── YES (len > 0) → wrapped_solute = positions % np.diag(cell)
└── NO → None (not wrapped)

Are custom_molecule_positions present?
├── YES (len > 0) → wrapped_custom = positions % np.diag(cell)
└── NO → None (not wrapped)
```

## Appendix C: Atomtype Deduplication Flow (Bug 3 fix)

**Used in:** write_ion_top_file, write_custom_molecule_top_file, write_solute_top_file

```
1. Initialize _written_atomtypes = {"OW_ice", "HW_ice", "MW"}
2. Add ion names: if na_count > 0 → add "NA"; if cl_count > 0 → add "CL"
3. Add GAFF2 names: if needs_ch4 → add "c3","hc"; if needs_thf → add "os","c5","hc","h1"
4. For custom ITP atomtypes:
   for atomtype in parse_itp_atomtypes(custom_itp_path):
     if atomtype[0] not in _written_atomtypes:
       write atomtype line
       add atomtype[0] to _written_atomtypes
```

This prevents duplicate atomtype entries when GAFF2 types from guests/solutes overlap with custom ITP types.
