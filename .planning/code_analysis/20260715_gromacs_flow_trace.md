# GROMACS Export Flow Trace — QuickIce v4.7

**Analysis Date:** 2026-07-15
**Scope:** Read-only trace of every function/data-flow step leading to a successful GROMACS (`.gro` + `.top` + `.itp`) export, for BOTH the CLI and GUI paths.
**Method:** Static code reading only — no execution, no modification.

---

## 0. Conventions & Key File-Path Corrections

- All `file:line` references use repo-relative paths (e.g. `quickice/output/gromacs_writer.py:869`).
- **Correction to the task prompt:** the ion-ITP generator lives at `quickice/structure_generation/gromacs_ion_export.py` (NOT `quickice/output/gromacs_ion_export.py`). The `output/` directory contains no `gromacs_ion_export.py`; see `quickice/structure_generation/` listing. `write_ion_itp` is imported from the `structure_generation` package by both GUI (`quickice/gui/export.py:532`) and CLI (`quickice/cli/itp_helpers.py:475`).
- **Important finding — no production `gmx grompp`:** a `grep` of the entire `quickice/` package for `import subprocess`, `subprocess.run`, and `grompp` returns ZERO hits in production source. The only `subprocess.run(["gmx","grompp",...])` invocation lives in the TEST helper `tests/e2e_export_helpers.py:591` (`run_gmx_grompp`). The export path itself writes files and returns; **`gmx grompp` validation is a test-time check, not a production post-export step.** See §6.
- The CLI module is `quickice/main.py` (NOT `quickice/cli/main.py` — the latter does not exist). The router is `quickice/entry.py::main()`.

---

## 1. CLI Path — Full Call Sequence to GROMACS Export

Entry router → CLI main → CLIPipeline → ordered steps → writer dispatch → ITP copy.

### 1.1 Routing & argument parsing

1. `quickice/entry.py:105` `main(argv)` — unified entry router. Pre-parses `--cli`/`--gui` (`entry.py:134-137`), detects pipeline flags via `_has_pipeline_flags` (`entry.py:72-88`), and delegates:
   - `--gui` → `quickice.gui.main_window.run_app` (`entry.py:176-178`) — GUI path (see §2).
   - `--cli` or implicit pipeline flags → `quickice.main.main` (`entry.py:186-187` or `:194-195`).
2. `quickice/main.py:23` `main()` — CLI entry. Calls `quickice/cli/parser.py:514` `get_arguments()` → `create_parser()` (`parser.py:23`) + `validate_pipeline_args` (`parser.py:450`) + `validate_interface_args` (`parser.py:408`).
3. `main.py:37-46` detects pipeline flags (`args.interface` / `args.hydrate` / `args.custom_gro` / `args.solute_type` / `args.ion_concentration`); if any → constructs `CLIPipeline(args)` and calls `pipeline.execute()`. (The ice-only legacy branch at `main.py:48-178` only runs when NO pipeline flags are set and `--gromacs` is used; it calls `write_gro_file`/`write_top_file` directly at `main.py:123/135`.)

### 1.2 CLIPipeline.execute — ordered steps

`quickice/cli/pipeline.py:128` `CLIPipeline.execute()` runs in fail-fast order:

4. **Step 0** — output dir: `pipeline.py:136-142` creates `self._output_dir = Path(args.output).resolve()`; `--no-overwrite` short-circuit at `pipeline.py:145-156`.
5. **Step 1 (source):** `pipeline.py:158-161` → `_run_source_step()` (`pipeline.py:292`).
   - Hydrate branch (`pipeline.py:307-363`): builds `HydrateConfig` (with `_parse_cage_guest_args` at `pipeline.py:33-104` for `--cage-guest`), calls `HydrateStructureGenerator().generate(config)` → `self._hydrate_result` (`pipeline.py:343-344`). If `--interface` also set, converts via `hydrate.to_candidate()` (`pipeline.py:355`, defined at `types.py:1191`).
   - Ice branch (`pipeline.py:365-397`): `lookup_phase` → `generate_candidates(phase_info, nmolecules, n_candidates=1, base_seed)` → `self._ice_candidate = gen_result.candidates[0]`.
6. **Step 2 (interface):** `pipeline.py:164-167` → `_run_interface_step()` (`pipeline.py:399`). Builds `InterfaceConfig` (`pipeline.py:422-432`) and calls `generate_interface(self._ice_candidate, config)` (`pipeline.py:433`) → `self._interface_result`.
7. **Step 3 (custom):** `pipeline.py:170-173` → `_run_custom_step()` (`pipeline.py:449`). Validates `.gro`/`.itp` paths (`pipeline.py:471-509`, SEC-02/SEC-04 checks), branch on `args.custom_placement`:
   - `random` (`pipeline.py:520-553`): count from `--custom-count` or computed from `--custom-concentration` via `water_nmolecules * WATER_VOLUME_NM3 * AVOGADRO` (`pipeline.py:530-534`); `CustomMoleculeInserter(config, seed).place_random(source, count)` → `self._custom_result`.
   - `custom` (`pipeline.py:556-574`): parses CSV via `_parse_positions_csv` (`pipeline.py:217-286`, MAX_CSV_ROWS=10000 SEC-05 cap); `inserter.place_custom(source, positions, rotations)`.
8. **Step 4 (solute):** `pipeline.py:176-179` → `_run_solute_step()` (`pipeline.py:591`). **Auto-chain:** if `solute_source=='interface'` and `self._custom_result is not None`, upgrades to `'custom'` (`pipeline.py:621-626`). `SoluteInserter(config, seed=args.seed).insert_solutes(source, config)` (`pipeline.py:642-643`) → `self._solute_result`.
9. **Step 5 (ion):** `pipeline.py:182-185` → `_run_ion_step()` (`pipeline.py:662`). **Auto-chain:** if `ion_source=='interface'`, upgrades to `'solute'` (if `_solute_result`) or `'custom'` (if `_custom_result`) at `pipeline.py:703-715`. Source-attribute propagation onto `InterfaceStructure` via duck-typing (`pipeline.py:734-794`): sets `.custom_molecule_*`, `.solute_*`, `.solute_registry` (CP-01 design decision). Computes `liquid_volume = water_nmolecules * WATER_VOLUME_NM3` (`pipeline.py:800`), then `insert_ions(source, concentration_molar, liquid_volume_nm3, seed)` (`pipeline.py:803-808`) → `self._ion_result`.
10. **Step 6 (export):** `pipeline.py:188` → `_run_export_step()` (`pipeline.py:821`).

### 1.3 Export step — writer dispatch

11. `pipeline.py:851-862` **priority selection** (most-downstream wins): `ion > solute > custom > interface > hydrate > ice`. Selected structure + `step_name` pair.
12. `pipeline.py:879-880` builds `cgi = _build_custom_guest_info(self._hydrate_result.config)` via `quickice/output/guest_info.py:10` `_build_custom_guest_info(config)` — returns `list[dict]` (one per distinct custom guest, deduped by `mol_type`) or `None` for built-in/no-guest.
13. `pipeline.py:883-941` **writer dispatch by `step_name`**:

| step_name | GRO writer call | TOP writer call |
|-----------|----------------|-----------------|
| `ice` | `write_gro_file(structure, gro_path)` (`pipeline.py:884`) | `write_top_file(structure, top_path)` (`pipeline.py:885`) |
| `hydrate` | `write_interface_gro_file(wrapper, gro_path, custom_guest_info=...)` (`pipeline.py:928`) | `write_interface_top_file(wrapper, top_path, custom_guest_info=...)` (`pipeline.py:929`) |
| `interface` | `write_interface_gro_file(structure, gro_path, custom_guest_info=cgi)` (`pipeline.py:931`) | `write_interface_top_file(structure, top_path, custom_guest_info=cgi)` (`pipeline.py:932`) |
| `custom` | `write_custom_molecule_gro_file(structure, gro_path, custom_guest_info=cgi)` (`pipeline.py:934`) | `write_custom_molecule_top_file(structure, top_path, custom_guest_info=cgi)` (`pipeline.py:935`) |
| `solute` | `write_solute_gro_file(structure, gro_path, custom_guest_info=cgi)` (`pipeline.py:937`) | `write_solute_top_file(structure, top_path, custom_guest_info=cgi)` (`pipeline.py:938`) |
| `ion` | `write_ion_gro_file(structure, gro_path, custom_guest_info=cgi)` (`pipeline.py:940`) | `write_ion_top_file(structure, top_path, custom_guest_info=cgi)` (`pipeline.py:941`) |

   - **Hydrate branch special wrap** (`pipeline.py:886-929`): `HydrateStructure` is wrapped into an `InterfaceStructure` (mode `"hydrate"`, `ice_atom_count=0`, `water_atom_count = water_count * WATER_ATOMS_PER_MOLECULE`, `guest_atom_count = len(positions) - water_atom_count`) with an `assert` at `pipeline.py:901-904` verifying atom-count consistency. Its own `custom_guest_info` is built locally from `hydrate.config` (`pipeline.py:927`).
14. `pipeline.py:944-946` `copy_itp_files_for_structure(self._output_dir, structure, step_name, hydrate_config=hydrate_config)` — see §1.4.
15. `pipeline.py:952-955` error handler: `except (OSError, ValueError)` — fails fast, returns 1 (no bare `except Exception` per AGENTS.md constraint).

### 1.4 ITP file staging — `quickice/cli/itp_helpers.py:282` `copy_itp_files_for_structure`

Always copies `tip4p-ice.itp` (`itp_helpers.py:311-318`). Per-step branches:

- **ice** (`itp_helpers.py:320-322`): only tip4p-ice.itp.
- **hydrate** (`itp_helpers.py:324-340`): if `config.is_custom_guest` → `copy_custom_guest_itp` (`itp_helpers.py:201`) transforms the user ITP with `_H` suffix; else `_copy_hydrate_guest_itp` (`itp_helpers.py:167`) → `transform_guest_itp(content, guest_name, "_H")` (`itp_helpers.py:189`, defined `gromacs_writer.py:677`).
- **interface / custom / solute / ion** (`itp_helpers.py:342-518`): first, **custom-guest ITP staging mirror** of the hydrate branch when `hydrate_config` carries a custom assignment (`itp_helpers.py:347-358`, `:371-381`, `:404-414`, `:461-472`) — calls `_build_custom_guest_info` + `copy_custom_guest_itp`. Then step-specific staging:
  - **custom** (`itp_helpers.py:384-400`): `_copy_itp_with_atomtypes_commented` for the custom molecule ITP (`itp_helpers.py:144`), plus guest ITP if `guest_atom_count > 0`.
  - **solute** (`itp_helpers.py:402-458`): `get_solute_liquid_itp_path(solute_type)` (`itp_helpers.py:43`) → `{solute_type}_liquid.itp` copied with atomtypes commented; custom-molecule ITP if `custom_molecule_count > 0`; hydrate-guest ITP if `guest_atom_count > 0`.
  - **ion** (`itp_helpers.py:460-518`): **generates `ion.itp`** via `write_ion_itp(str(output_dir / "ion.itp"), na_count, cl_count)` (`itp_helpers.py:480`, see §3.4); plus solute-liquid ITP, custom-molecule ITP, hydrate-guest ITP as applicable.

---

## 2. GUI Path — Full Call Sequence to GROMACS Export

Entry → `run_app` → `MainWindow` (MVVM View) → `HydrateWorker` (QThread) → tab-specific export button → exporter class → writer dispatch → ITP staging.

### 2.1 Launch & structure generation

1. `quickice/entry.py:176-178` `from quickice.gui.main_window import run_app; run_app()` (only when `--gui` AND `_is_pyside6_available()` AND `_has_display()` pass, `entry.py:168-178`).
2. `quickice/gui/main_window.py:2142` `run_app()` → `_configure_opengl_for_remote` (`:2115`) → `QApplication` → `MainWindow()` (`:2168`).
3. `MainWindow.__init__` (`main_window.py:61-115`) constructs exporters:
   - `_gromacs_exporter = GROMACSExporter(self)` (`:73`) — ice candidates.
   - `_interface_gromacs_exporter = InterfaceGROMACSExporter(self)` (`:74`).
   - `_ion_gromacs_exporter = IonGROMACSExporter(self)` (`:75`).
   - `_hydrate_gromacs_exporter = HydrateGROMACSExporter(self)` (`:90`).
   - `_solute_gromacs_exporter = SoluteGROMACSExporter(self)` (`:93`).
   - `_custom_molecule_gromacs_exporter = CustomMoleculeGROMACSExporter(self)` (`:96`).
   - State attributes: `_current_result`, `_current_interface_result`, `_current_hydrate_result`, `_current_hydrate_config`, `_current_ion_result`, `_current_solute_result`, `_current_custom_molecule_result` (`:78-108`).
4. **Hydrate generation** (`main_window.py:745-767` `_on_hydrate_generate_clicked`): `config = self.hydrate_panel.get_configuration()` → stored as `self._current_hydrate_config` (`:748-749`); `self._hydrate_worker = HydrateWorker(config)` (`:759`); signals connected (`:762-764`); `worker.start()`.
5. **`HydrateWorker`** (`quickice/gui/hydrate_worker.py:15`) — subclasses `QThread` directly (AGENTS.md: do NOT "fix" this). `run()` (`hydrate_worker.py:50`) lazily imports `HydrateStructureGenerator` (`:65`), calls `generator.generate(self._config)` (`:79`), emits `generation_complete(HydrateStructure)` (`:87`) on success or `generation_error` (`:89-114`) on `ImportError`/`RuntimeError`/`ValueError`/`Exception`.
6. **Hydrate result storage** (`main_window.py:777-802` `_on_hydrate_generation_complete`): `self._current_hydrate_result = result` (`:784`).
7. **Interface generation** (`main_window.py:612-659` `_on_interface_generation_complete`): `self._current_interface_result = result` (`:619`); propagates `liquid_vol = result.water_nmolecules * WATER_VOLUME_NM3` (`:635`) to ion/solute/custom panels.
8. **Solute insertion** (`main_window.py:829-1050` `_on_insert_ions` and the solute equivalent near `:1050`): propagates solute/custom attrs onto `InterfaceStructure` by duck-typing (`main_window.py:875-880`, `:907-913`) — exactly mirroring the CLI's `pipeline.py:734-794`. `self._current_solute_result` / `self._current_custom_molecule_result` / `self._current_ion_result` stored at `:1050`, `:1189`, `:942`.

### 2.2 Export button dispatch (Ctrl+S unified + per-tab menu)

9. `main_window.py:1566-1600` `_on_export_current_tab` — routes `currentIndex()` to the per-tab handler:
   - `TabIndex.ICE` → `_on_export_gromacs` (`:1583`)
   - `TabIndex.HYDRATE` → `_on_export_hydrate_gromacs` (`:1585`)
   - `TabIndex.INTERFACE` → `_on_export_interface_gromacs` (`:1587`)
   - `TabIndex.SOLUTE` → `_on_export_solute_gromacs` (`:1589`)
   - `TabIndex.CUSTOM` → `_on_export_custom_molecule_gromacs` (`:1591`)
   - `TabIndex.ION` → `_on_export_ion_gromacs` (`:1593`)
   Menu actions wired at `main_window.py:357, 391, 396, 401, 406, 411`.

### 2.3 Per-tab exporter → writer dispatch

Each exporter (`quickice/gui/export.py`, `quickice/gui/hydrate_export.py`) follows the same 4-phase pattern:

#### A. Ice — `main_window.py:1603` `_on_export_gromacs` → `export.py:885` `GROMACSExporter.export_gromacs`
- `export.py:900-905` default filename `{phase_id}_{T}K_{P}MPa_c{rank}.gro`.
- `QFileDialog.getSaveFileName` (`:911-917`); `_remember_export_dir` (`:921`).
- `export.py:935` `write_gro_file(candidate, str(path))` (`gromacs_writer.py:833`).
- `export.py:940` `write_top_file(candidate, str(top_path))` (`gromacs_writer.py:948`).
- `export.py:944-946` `shutil.copy(get_tip4p_itp_path(), itp_path)` → copies `tip4p-ice.itp`.

#### B. Hydrate — `main_window.py:1696` `_on_export_hydrate_gromacs` → `hydrate_export.py:97` `HydrateGROMACSExporter.export_hydrate`
- Default filename `hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro` (`hydrate_export.py:118-124`).
- Builds a fresh `MoleculetypeRegistry` (`hydrate_export.py:175`); iterates **unique guest mol_types in `structure.molecule_index`** (Phase 42-08 structure-driven fix, `hydrate_export.py:184-189`):
  - Built-in (`ch4`/`thf` in `GUEST_MOLECULES`): `registry.register_hydrate_guest(mol_type.upper())` → `CH4_H` / `THF_H` (`hydrate_export.py:266`), uses bundled `{guest_type}_hydrate.itp`.
  - Custom: appends to `custom_guest_info` list with `residue_name = f"{descriptor.guest_residue_name}_H"` (`hydrate_export.py:307`).
- `cgi_for_writers = custom_guest_info if custom_guest_info else None` (`hydrate_export.py:321`).
- `hydrate_export.py:324-333` `write_multi_molecule_gro_file(structure.positions, structure.molecule_index, structure.cell, str(path), title, atom_names=structure.atom_names, registry=registry, custom_guest_info=cgi_for_writers)` (`gromacs_writer.py:1688`).
- `hydrate_export.py:336-343` `write_multi_molecule_top_file(structure.molecule_index, str(top_path), system_name, itp_files=itp_files, registry=registry, custom_guest_info=cgi_for_writers)` (`gromacs_writer.py:1837`).
- `hydrate_export.py:346-347` `shutil.copy(tip4p_itp_path, water_itp_path)`.
- `hydrate_export.py:353-359` for each `(guest_itp_path, guest_name_for_transform)`: `transform_guest_itp(content, guest_name, "_H")` → write to `path.with_name(guest_itp_path.name)`. Built-in ITPs are pre-transformed so this is idempotent.

#### C. Interface — `main_window.py:1644` `_on_export_interface_gromacs` → `export.py:1028` `InterfaceGROMACSExporter.export_interface_gromacs`
- Default filename `interface_{mode}.gro` (`export.py:1059-1060`).
- `export.py:1095-1100` `custom_guest_info, _ = _stage_hydrate_guest_itps(path.parent, hydrate_config, interface_structure, guest_atom_count=..., guest_nmolecules=...)` (`quickice/output/guest_info.py:131`). This is the config-driven ITP staging helper (Phase 44.1-08) that handles BOTH the custom path (transform + write) and the built-in path (`shutil.copy` of bundled `{guest_type}_hydrate.itp`).
- `export.py:1103-1107` `write_interface_gro_file(interface_structure, str(path), custom_guest_info=custom_guest_info)` (`gromacs_writer.py:1044`).
- `export.py:1110-1114` `write_interface_top_file(interface_structure, str(top_path), custom_guest_info=custom_guest_info)` (`gromacs_writer.py:1487`).
- `export.py:1118-1123` `shutil.copy(get_tip4p_itp_path(), path.with_name("tip4p-ice.itp"))`.

#### D. Solute — `main_window.py:1796` `_on_export_solute_gromacs` → `export.py:126` `SoluteGROMACSExporter.export_solute_gromacs`
- `export.py:194-200` `_stage_hydrate_guest_itps(path.parent, hydrate_config, _iface, ...)` (uses `solute_structure.interface_structure` for the presence gate).
- `export.py:204-206` `write_solute_gro_file(solute_structure, str(path), custom_guest_info=...)` (`gromacs_writer.py:3336`).
- `export.py:210-212` `write_solute_top_file(solute_structure, str(top_path), custom_guest_info=...)` (`gromacs_writer.py:3768`).
- `export.py:216-219` `shutil.copy(get_tip4p_itp_path(), ...)`.
- `export.py:230-242` copies `{solute_type}_liquid.itp` with `comment_out_atomtypes_in_itp` applied (`gromacs_writer.py:561`).
- `export.py:244-253` if `custom_molecule_count > 0`: copies custom molecule ITP with atomtypes commented.

#### E. Custom Molecule — `main_window.py:1855` `_on_export_custom_molecule_gromacs` → `export.py:274` `CustomMoleculeGROMACSExporter.export_custom_molecule_gromacs`
- `export.py:361-366` `_stage_hydrate_guest_itps(path.parent, hydrate_config, custom_structure, ...)` (passes the flattened `custom_structure`, NOT `interface_structure`, because `CustomMoleculeStructure` carries its own `guest_atom_count`/`molecule_index`).
- `export.py:374-379` `write_custom_molecule_gro_file` + `write_custom_molecule_top_file` (`gromacs_writer.py:2803` / `:3102`).
- `export.py:383-389` copies custom ITP with atomtypes commented.
- `export.py:392-395` `shutil.copy(get_tip4p_itp_path(), ...)`.

#### F. Ion — `main_window.py:1732` `_on_export_ion_gromacs` → `export.py:428` `IonGROMACSExporter.export_ion_gromacs`
- `export.py:512-517` `_stage_hydrate_guest_itps(path.parent, hydrate_config, ion_structure, ...)` (`IonStructure` has NO `interface_structure` ref — carries its own `guest_atom_count`/`guest_nmolecules`).
- `export.py:521-523` `write_ion_gro_file(ion_structure, str(path), custom_guest_info=...)` (`gromacs_writer.py:2044`).
- `export.py:527-529` `write_ion_top_file(ion_structure, str(top_path), custom_guest_info=...)` (`gromacs_writer.py:2482`).
- `export.py:532-534` **`write_ion_itp(ion_itp_path, na_count, cl_count)`** — generates `ion.itp` via `quickice/structure_generation/gromacs_ion_export.py:81` (see §3.4).
- `export.py:538-541` `shutil.copy(get_tip4p_itp_path(), ...)`.
- `export.py:552-582` copies solute-liquid ITP and custom-molecule ITP (both with atomtypes commented) when present.

> **GUI-only `gromacs_ion_export` path:** the task asked to trace a GUI-only `quickice/output/gromacs_ion_export.py`. That path does NOT exist; the ion-ITP generator is `quickice/structure_generation/gromacs_ion_export.py` and is shared by BOTH paths (GUI: `export.py:532`; CLI: `itp_helpers.py:480`). It is not GUI-only.

---

## 3. GROMACS Writer Internals — `quickice/output/gromacs_writer.py` (4067 lines)

### 3.1 Module constants (TIP4P-ICE & force-field params)

- `gromacs_writer.py:52` `TIP4P_ICE_ALPHA = 0.13458335` (also redefined at `:386`).
- `gromacs_writer.py:56-57` **`TIP4P_ICE_OW_SIGMA = 3.16680e-1`** nm, **`TIP4P_ICE_OW_EPSILON = 8.82110e-1`** kJ/mol. Comment cites Abascal et al. 2005, DOI: 10.1063/1.1931662.
- `gromacs_writer.py:68-81` `GAFF2_ATOMTYPES` dict (c3/hc/os/c5/h1/c_2/o_2/hn) — 8-column tuples.
- `gromacs_writer.py:84-87` `CH4_ATOMTYPE_NAMES`, `THF_ATOMTYPE_NAMES`, `CO2_ATOMTYPE_NAMES`, `H2_ATOMTYPE_NAMES`.
- `gromacs_writer.py:90-93` `ION_ATOMTYPES` (Madrid2019 NA/CL).
- `gromacs_writer.py:96-100` `WATER_ATOMTYPES` — `OW_ice`/`HW_ice`/`MW`; OW_ice uses `TIP4P_ICE_OW_SIGMA`/`TIP4P_ICE_OW_EPSILON`.
- `gromacs_writer.py:276-285` `MOLECULE_TO_GROMACS` — maps mol_type → `{res_name, itp_file, mol_name}`.
- `gromacs_writer.py:288` module-level `_registry = MoleculetypeRegistry()` (see §3.5).

**TIP4P-ICE verification against `quickice/data/tip4p-ice.itp`:**
- `tip4p-ice.itp:4` (commented): `OW_ice 8 15.9994 0.0000 A 0.31668 0.88211` → sigma=0.31668 nm, epsilon=0.88211 kJ/mol. ✅ matches `TIP4P_ICE_OW_SIGMA=0.31668`, `TIP4P_ICE_OW_EPSILON=0.88211`.
- `tip4p-ice.itp:41` virtual_sites3: `4 1 2 3 1 0.13458 0.13458` → a=b=0.13458 (5-decimal rounded). `TIP4P_ICE_ALPHA=0.13458335` in code uses higher precision — consistent (rounded form in ITP, full-precision in MW computation at `gromacs_writer.py:1041`).

### 3.2 The `.gro` writers — common pattern

All GRO writers (entry signatures):
- `write_gro_file(candidate: Candidate, filepath: str)` — `gromacs_writer.py:833` (ice-only Candidate).
- `write_interface_gro_file(iface: InterfaceStructure, filepath: str, custom_guest_info: list[dict] | None = None)` — `gromacs_writer.py:1044`.
- `write_multi_molecule_gro_file(positions, molecule_index, cell, filepath, title=..., atom_names=None, registry=None, custom_guest_info=None)` — `gromacs_writer.py:1688` (hydrate path).
- `write_ion_gro_file(ion_structure: IonStructure, filepath: str, custom_guest_info=None)` — `gromacs_writer.py:2044`.
- `write_custom_molecule_gro_file(custom_structure, filepath: str, custom_guest_info=None)` — `gromacs_writer.py:2803`.
- `write_solute_gro_file(solute_structure, filepath: str, custom_guest_info=None)` — `gromacs_writer.py:3336`.

**`.gro` file structure produced** (identical format across all writers):
1. **Title line** — `f.write(...)` (e.g. `gromacs_writer.py:880` `"Ice structure {phase_id} exported by QuickIce"`; interface `:1154`; ion `:2218`).
2. **Atom count line** — `f.write(f"{n_atoms:5d}\n")` (e.g. `:881`, `:1157`, `:2221`).
3. **Per-atom lines** built into an in-memory `lines = []` then `f.writelines(lines)` (e.g. `:935`, `:1348`, `:2468`). Each line:
   ```
   {res_num:5d}{res_name:<5s}{atom_name:>5s}{atom_num_wrapped:5d}{x:8.3f}{y:8.3f}{z:8.3f}\n
   ```
   - **Atom indexing:** `atom_num += 1; atom_num_wrapped = atom_num % 100000` (GROMACS 5-digit wrap, e.g. `:911-912`, `:1206`). Logger warning if `n_atoms > 99999` (`:858-859`, `:1125-1126`, `:2180-2181`).
   - **Residue indexing:** `res_num = (mol_idx + 1) % 100000` (e.g. `:909`, `:1202`).
   - **Coordinate precision:** `{pos:8.3f}` — 3 decimal places, 8-char width (GROMACS GRO standard).
   - **TIP4P-ICE MW virtual site:** computed from O/H1/H2 via `compute_mw_position` (`gromacs_writer.py:1024`): `MW = O + α*(H1-O) + α*(H2-O)`, `α = TIP4P_ICE_ALPHA = 0.13458335`. Ice 3-atom (O,H,H) input is normalized to 4-atom (OW,HW1,HW2,MW) at export (`gromacs_writer.py:900-933`, `:1184-1230`); hydrate 4-atom input uses existing MW (`:1194-1199`).
   - **Guest atom reordering:** `reorder_guest_atoms(atom_names, mol_type)` (`gromacs_writer.py:400`) — GenIce2 outputs CH4 as H,H,H,H,C but the ITP expects C,H,H,H,H (`GUEST_ATOM_ORDER` at `:391-397`). Applied only for built-in `ch4`/`thf`; **skipped for custom guests** (atoms already in ITP order, e.g. `gromacs_writer.py:2349-2351`, `:3036-3037`, `:3664-3666`).
   - **`validate_gro_residue_name`** (`gromacs_writer.py:26`) — raises `ValueError` if residue name > 5 chars (GRO fixed-width limit) before writing.
4. **Box line (triclinic)** — `f.write(f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}{cell[0,1]:10.5f}{cell[0,2]:10.5f}{cell[1,0]:10.5f}{cell[1,2]:10.5f}{cell[2,0]:10.5f}{cell[2,1]:10.5f}\n")` (e.g. `:938-940`, `:1352-1354`, `:2472-2474`). 10-char width, 5 decimals. NOTE: `write_custom_molecule_gro_file` writes only the diagonal box line `f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}\n"` (`gromacs_writer.py:3087-3088`) — an inconsistency vs the other writers (which always emit 9 triclinic values).

**Velocities:** **NOT written.** No writer emits a velocity block. GROMACS GRO format supports optional velocities (3 additional `%8.3f` columns per atom); QuickIce omits them entirely (zero-initialized by `gmx grompp` / `mdrun`).

### 3.3 The `.top` writers — common pattern

- `write_top_file(candidate, filepath)` — `gromacs_writer.py:948` (ice-only, self-contained — no `#include`).
- `write_interface_top_file(iface, filepath, custom_guest_info=None)` — `gromacs_writer.py:1487`.
- `write_multi_molecule_top_file(molecule_index, filepath, system_name=..., itp_files=None, registry=None, custom_guest_info=None)` — `gromacs_writer.py:1837` (hydrate).
- `write_ion_top_file(ion_structure, filepath, custom_guest_info=None)` — `gromacs_writer.py:2482`.
- `write_custom_molecule_top_file(custom_structure, filepath, custom_guest_info=None)` — `gromacs_writer.py:3102`.
- `write_solute_top_file(solute_structure, filepath, custom_guest_info=None)` — `gromacs_writer.py:3768`.

**`.top` file section order** (consistent across all multi-molecule writers):

1. **Header comment** — `; Generated by QuickIce` + model name.
2. **`[ defaults ]`** — **comb-rule=2** (Lorentz-Berthelot, AMBER/GAFF2 convention, AGENTS.md constraint):
   ```
   [ defaults ]
   ; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ
   1               2               yes             0.5     0.8333
   ```
   (e.g. `gromacs_writer.py:962-966`, `:1557-1561`, `:1959-1963`, `:2630-2634`, `:3219-3223`, `:3929-3933`.) Never comb-rule=1.
3. **`[ atomtypes ]`** — written via `_format_atomtype_line` (`gromacs_writer.py:103`) and `_write_atomtypes_block` (`:137`) with **deduplication** via `_written_atomtypes` dict. Water (`WATER_ATOMTYPES`) always first; ions (`ION_ATOMTYPES`) when NA/CL present; GAFF2 blocks (`CH4_ATOMTYPE_NAMES` etc.) when guest/solute present. **Custom guest atomtypes merged via `_merge_custom_atomtypes`** (`:240`) which calls `parse_itp_atomtypes` (`:510`) + `_check_custom_atomtype_conflict` (`:165`) — raises `ValueError` on LJ-param mismatch. Custom-molecule atomtypes parsed from the user ITP and conflict-checked (`:2694-2715` ion, `:3265-3284` custom, `:3980-4001` solute). All atomtypes MUST precede any `#include` (GROMACS ordering invariant, e.g. `:1965-1967`).
4. **`#include` directives** — `#include "tip4p-ice.itp"` always (e.g. `:1627`, `:2722`); `#include "{guest_type}_hydrate.itp"` for built-in guests (e.g. `:1642`, `:2738`) OR `#include "{Path(ci['itp_path']).name}"` for each custom guest (e.g. `:1638`, `:2733`); `#include "{solute_type}_liquid.itp"` for solutes (e.g. `:4031-4032`); `#include "ion.itp"` for ions (`:2757`); `#include "{custom_itp_name}"` for custom molecules (e.g. `:2748`, `:3311`).
5. **`[ system ]`** — system name string.
6. **`[ molecules ]`** — `; Compound    #mols` + one line per moleculetype. **Order MUST match `.gro`** (e.g. ice-SOL→water-SOL combined, then guest, then custom, then solute, then NA, then CL for the ion writer — `:2769-2800`). Moleculetype names resolved via `MoleculetypeRegistry.get_gromacs_name` (`:144`):
   - `SOL` for all water/ice.
   - `CH4_H` / `THF_H` (hydrate cage guests, `_H` suffix via `register_hydrate_guest` — `moleculetype_registry.py:46`).
   - `CH4_L` / `THF_L` (liquid solutes, `_L` suffix via `register_liquid_solute` — `moleculetype_registry.py:71`).
   - `{base}_H` for custom hydrate guests (from `custom_guest_info[i]['residue_name']`).
   - `CUSTOM` / ITP-parsed `molecule_name` for custom molecules (via `parse_itp_file` → `itp_info.molecule_name`, e.g. `:2596-2603`).
   - `NA` / `CL` for ions.

### 3.4 `ion.itp` generation — `quickice/structure_generation/gromacs_ion_export.py`

- `write_ion_itp(output_path, na_count, cl_count)` — `gromacs_ion_export.py:81` calls `generate_ion_itp(na_count, cl_count)` (`:30`) which returns a template string with **two `[ moleculetype ]` sections** (`NA` and `CL`), each with one `[ atoms ]` entry.
- Madrid2019 params: `NA_ATOM_MASS=22.9898`, `CL_ATOM_MASS=35.453` (`:11-12`); `NA_CHARGE=0.85`, `CL_CHARGE=-0.85` (`:18-19`); `NA_SIGMA=0.22173668`, `CL_SIGMA=0.46990563`, `NA_EPSILON=1.47235577`, `CL_EPSILON=0.07692308` (`:24-27`). Citation: Zeron et al., J. Chem. Phys. 2019.
- The CLI path calls this from `itp_helpers.py:475-480` (inside the `ion` branch of `copy_itp_files_for_structure`). The GUI path calls it from `export.py:532-534` (`IonGROMACSExporter`).
- Related helpers (unused by the export path but present): `generate_itp_include_section` (`:60`), `add_ion_molecule_to_topology` (`:96`), `get_ion_molecule_section` (`:148`).

### 3.5 MoleculetypeRegistry — `quickice/structure_generation/moleculetype_registry.py`

- `register_hydrate_guest(molecule)` (`:46`) → `f"{molecule}_H"`, key `hydrate_{molecule}`. Idempotent (`:62-65`).
- `register_liquid_solute(molecule)` (`:71`) → `f"{molecule}_L"`, key `liquid_{molecule}`.
- `register_custom_molecule(user_name="MOL")` (`:96`) — reserved-name check (`:114-118`), counter-based collision resolution (`MOL`, `MOL_1`, `MOL_2`, …).
- `RESERVED_NAMES` (`:35-38`): `SOL, NA, CL, CH4, THF, CO2, H2, CH4_H, CH4_L, THF_H, THF_L` — never used for custom molecules.
- `get_gromacs_name(source)` (`:144`) — returns registered name or `source.upper()`.
- Per AGENTS.md: **never hardcode moleculetype names** — always go through the registry.

### 3.6 PBC wrap functions — `quickice/output/gromacs_writer.py`

- `wrap_positions_into_box(positions, cell)` — `gromacs_writer.py:291`. **Atom-by-atom modulo wrap**: `wrapped[:, dim] = np.mod(wrapped[:, dim], cell[dim, dim])` for each dim. May split molecules across PBC. Used as a **fallback** when `molecule_index` is empty (`gromacs_writer.py:1136` interface, `:3506` solute).
- `wrap_molecules_into_box(positions, molecule_index, cell)` — `gromacs_writer.py:312`. **Molecule-aware wrap**: for each `MoleculeIndex`, unwrap atoms split across PBC (`delta > half_box` → shift back, `delta < -half_box` → shift forward, vectorized at `:355-367`), then wrap the molecule center into `[0, box)` and apply the same shift to all atoms (`:370-377`). Keeps molecules intact.
- **Callers in the export path:**
  - `write_gro_file` — `gromacs_writer.py:869` (molecule-aware, ice only).
  - `write_interface_gro_file` — `:1133` (molecule-aware) / `:1136` (atom-by-atom fallback) / `:1143` solute modulo / `:1147` custom modulo.
  - `write_ion_gro_file` — `:2186` (molecule-aware) / `:2194` solute modulo / `:2200` custom modulo.
  - `write_custom_molecule_gro_file` — `:2895` (molecule-aware).
  - `write_solute_gro_file` — `:3501` (molecule-aware) / `:3506` (atom-by-atom fallback) / `:3512` custom modulo / `:3522` solute modulo.
  - `write_multi_molecule_gro_file` (hydrate) — does NOT call wrap (relies on GenIce2 output already being in-box; positions used directly at `:1800`).
- Solute/custom positions are separate arrays from `interface.positions`, so they get a separate `arr % np.diag(cell)` modulo wrap (AN-03 fix, e.g. `:1142-1147`, `:2193-2202`, `:3510-3524`).

### 3.7 ITP transformation helpers

- `transform_guest_itp(itp_content, guest_name, suffix="_H")` — `gromacs_writer.py:677`. Three steps: (1) `comment_out_atomtypes_in_itp` (`:561`) comments out `[ atomtypes ]` (types belong in main `.top`); (2) rewrites `[ moleculetype ]` name → `f"{guest_name}{suffix}"` (e.g. `CH4` → `CH4_H`, `:711`); (3) `_rewrite_atoms_section_resname` (`:608`) rewrites the resname column in `[ atoms ]` to match (Phase 40-02). Validates new name ≤ 5 chars (`:714`).
- `parse_itp_atomtypes(itp_path)` — `gromacs_writer.py:510`. Returns list of 8-col tuples; normalizes 7-col format by inserting `name` as `bond_type` (`:551-553`).
- `parse_itp_residue_name(itp_path)` — `gromacs_writer.py:467`. Reads resname from column 4 of `[ atoms ]`.
- `get_guest_residue_name(guest_type)` — `:764` (liquid path, e.g. `CH4`); `get_hydrate_guest_residue_name(guest_type)` — `:800` (hydrate path, e.g. `CH4_H`). Both fall back to `FALLBACK_*` dicts on read failure.
- `_build_custom_guest_info(config)` — `quickice/output/guest_info.py:10`. Returns `list[dict]` `{'mol_type', 'residue_name'='{base}_H', 'itp_path'=Path}` for each distinct custom guest (deduped by `mol_type`); excludes built-ins (registry handles them); `None` if no custom assignments.
- `_stage_hydrate_guest_itps(output_dir, hydrate_config, structure, guest_atom_count=None, guest_nmolecules=None)` — `guest_info.py:131`. Config-driven ITP staging for interface/solute/custom/ion exporters. Presence gate (`guest_atom_count > 0 and guest_nmolecules > 0`, `:250`); regression fix recovers `guest_nmolecules` from `molecule_index` when 0 (`:233-244`). Custom path: transforms + writes each custom ITP (`:267-286`). Built-in path: `_detect_builtin_guest_type` (`:83`) + `shutil.copy` of bundled `{guest_type}_hydrate.itp` (`:312-316`).

---

## 4. Data-Flow Table — Structure Produced at Each Step

| Step | Producing site | Data structure | Consumed by |
|------|----------------|----------------|-------------|
| Arg parse | `cli/parser.py:514` `get_arguments()` | `argparse.Namespace` | `CLIPipeline.__init__` (`pipeline.py:118`) |
| Source — ice | `generate_candidates` (via `pipeline.py:378`) | `GenerationResult.candidates[0]` → `Candidate` (`types.py:224`) | `_run_interface_step` |
| Source — hydrate | `HydrateStructureGenerator().generate(config)` (`pipeline.py:344`) | `HydrateStructure` (`types.py:1152`) | `.to_candidate()` (`:1191`) → interface; OR export hydrate branch wraps it |
| Interface | `generate_interface(candidate, config)` (`pipeline.py:433`) | `InterfaceStructure` (`types.py:348`) with `positions/atom_names/cell/ice_atom_count/water_atom_count/guest_atom_count/molecule_index` | Custom/Solute/Ion steps + `write_interface_gro/top_file` |
| Custom | `CustomMoleculeInserter.place_random/place_custom` (`pipeline.py:550/568`) | `CustomMoleculeStructure` (`types.py:1010`) with `molecule_index/moleculetype_name/itp_path/interface_structure` | Solute/Ion step (auto-chain) + `write_custom_molecule_gro/top_file` |
| Solute | `SoluteInserter.insert_solutes(source, config)` (`pipeline.py:643`) | `SoluteStructure` (`types.py:909`) with `positions/molecule_indices/registry/interface_structure/custom_*` | Ion step (auto-chain) + `write_solute_gro/top_file` |
| Ion | `insert_ions(source, concentration, liquid_volume, seed)` (`pipeline.py:803`) | `IonStructure` (`types.py:826`) with `molecule_index/na_count/cl_count/guest_*/solute_*/custom_*` | `write_ion_gro/top_file` + `write_ion_itp` |
| Duck-typed attrs | `pipeline.py:734-794` (CLI) / `main_window.py:875-913` (GUI) | `InterfaceStructure.solute_*/custom_molecule_*` (runtime-set, CP-01) | Ion inserter + writers read these |
| `custom_guest_info` | `_build_custom_guest_info(hydrate_config)` (`guest_info.py:10`) | `list[dict]{'mol_type','residue_name','itp_path'}` or `None` | threaded into every multi-molecule writer kwarg |
| `.gro` bytes | `write_*_gro_file` (`gromacs_writer.py:833/1044/1688/2044/2803/3336`) | GRO text (title + count + atom lines + box line) → written to disk | `gmx grompp -c` (test-only) |
| `.top` bytes | `write_*_top_file` (`gromacs_writer.py:948/1487/1837/2482/3102/3768`) | TOP text (defaults + atomtypes + #includes + system + molecules) → disk | `gmx grompp -p` (test-only) |
| `.itp` files | `copy_itp_files_for_structure` (CLI `itp_helpers.py:282`) / per-exporter staging (GUI `export.py`) | `tip4p-ice.itp` (copied) + `{guest}_hydrate.itp` (copied or transformed) + `{solute}_liquid.itp` (atomtypes commented) + `ion.itp` (generated) + custom `.itp` (atomtypes commented) | `gmx grompp` `#include` resolution |

---

## 5. Branch Points — How Each Branch Reaches the Writer

### 5.1 Step-type selection (CLI)

`pipeline.py:851-862` — the priority `ion > solute > custom > interface > hydrate > ice` selects BOTH the structure AND the `step_name`, which then selects the writer pair at `pipeline.py:883-941`. Each branch is mutually exclusive at export time (only the most-downstream step that actually ran is exported).

### 5.2 Hydrate guest: built-in (ch4/thf) vs custom

- **Built-in (`ch4`/`thf`):** `custom_guest_info` is `None`/empty. Writers use `detect_guest_type_from_atoms` (`gromacs_writer.py:1433`) + `get_hydrate_guest_residue_name` (`:800`) → `CH4_H`/`THF_H` (5 chars, fits GRO). ITP staging copies the bundled pre-transformed `{guest_type}_hydrate.itp`.
- **Custom guest (e.g. `etoh_e2e`):** `custom_guest_info` is a non-empty `list[dict]` from `_build_custom_guest_info`. Writers take the residue name from `ci['residue_name']` (e.g. `MOL_H`, validated ≤5 chars) and **skip** `detect_guest_type_from_atoms` (which returns `None` for unknown guests). ITP staging transforms the user ITP via `transform_guest_itp` (comments atomtypes, renames moleculetype to `{base}_H`, rewrites `[ atoms ]` resname).

### 5.3 Ion vs no-ion

- **With ions:** `step_name == "ion"` → `write_ion_gro_file`/`write_ion_top_file` + `write_ion_itp`. The `.top` `[ molecules ]` section includes `SOL`, `guest`, `custom`, `solute`, `NA`, `CL` lines (in that exact order). `[ atomtypes ]` includes `NA`/`CL` (Madrid2019).
- **Without ions:** a downstream non-ion step is exported (or no ion step ran). The ion-specific ITP/atomtypes/molecules entries are omitted entirely. `write_ion_itp` is NOT called.

### 5.4 Solute vs no-solute

- **With solutes:** `SoluteStructure.registry` is populated (`register_liquid_solute` → `CH4_L`/`THF_L`). The solute writer's `[ molecules ]` includes the `{SOLUTE}_L` line; `[ atomtypes ]` includes the GAFF2 block for that solute type (`needs_ch4_atomtypes`/`needs_thf_atomtypes` at `:3903-3906`); `#include "{solute_type}_liquid.itp"`.
- **Without solutes:** `has_solutes` is False (`solute_structure.n_molecules == 0` or `positions is None`); the solute lines/includes are skipped.

### 5.5 Custom molecule vs hydrate guest

These are **orthogonal**: a system can have BOTH a hydrate guest (from cages) AND a custom molecule (placed in the liquid region).
- **Custom molecule** = user-supplied `.gro`/`.itp` inserted into the liquid region via `CustomMoleculeInserter`. Stored as `CustomMoleculeStructure.moleculetype_name` / `itp_path`. The writers parse the ITP for the `[ moleculetype ]` name (`parse_itp_file` → `itp_info.molecule_name`, e.g. `gromacs_writer.py:2598, 3204`) and use it in `[ molecules ]`. Custom atomtypes are conflict-checked against the dedup dict (`_check_custom_atomtype_conflict`, `:165`).
- **Hydrate guest** = molecule in a hydrate cage (CH4/THF built-in or custom guest via `--cage-guest`). Uses `_H` suffix and the hydrate-guest ITP (`{guest_type}_hydrate.itp` or transformed custom ITP).
- A custom **guest** (Phase 40, e.g. ethanol in cages) is distinct from a custom **molecule** (Phase 34, e.g. ethanol in the liquid). The former goes through `custom_guest_info` + `transform_guest_itp` with `_H`; the latter goes through the custom-molecule ITP with atomtypes commented (no `_H`).

### 5.6 Empty `molecule_index` fallback (real GenIce2 data)

Real GenIce2 `InterfaceStructure`s often have an EMPTY `molecule_index`. Writers handle this:
- `write_interface_gro_file` falls back to `wrap_positions_into_box` (`gromacs_writer.py:1136`) and uses `ice_nmolecules`/`water_nmolecules` counts directly.
- `write_solute_gro_file` builds synthetic `MoleculeIndex`-like objects from counts (`:3412-3426`) when `interface.molecule_index` is empty.
- `write_solute_top_file` uses `interface.ice_nmolecules + interface.water_nmolecules` for `sol_count` (`:3821`).
- `_stage_hydrate_guest_itps` recovers `guest_nmolecules` from `molecule_index` when the attr is 0 (`guest_info.py:233-244`).

---

## 6. GROMACS CLI Subprocess Calls

### 6.1 Production code — **NONE**

A complete `grep` of `quickice/` (the production package) for `import subprocess`, `subprocess.run`, and `grompp` returns ZERO production hits. The only `grompp` mentions in production are **comments** in `quickice/gui/export.py` (lines 225, 401, 547, 1129) explaining that mis-staging would cause `grompp` to fail — there is no actual invocation.

**Conclusion:** the export path writes `.gro` + `.top` + `.itp` files and returns `True`/exit-0. Post-export `gmx grompp` validation is NOT performed by the application. Users must run `gmx grompp` themselves.

### 6.2 Test-only `gmx grompp` — `tests/e2e_export_helpers.py:591` `run_gmx_grompp`

This is the ONLY `subprocess.run(["gmx","grompp",...])` in the entire repository. It is a test helper, gated by the `@gmx_skipif` marker (skips when `gmx` not on `PATH`).

**Argument construction** (`tests/e2e_export_helpers.py:618-625`):
```python
cmd = [
    "gmx", "grompp",
    "-f", mdp_file,     # default "em.mdp"
    "-c", gro_file,     # default "struct.gro"
    "-p", top_file,     # default "struct.top"
    "-o", tpr_file,     # default "em.tpr"
    "-maxwarn", str(maxwarn),   # default 5
]
```

**Invocation** (`tests/e2e_export_helpers.py:627-633`):
```python
result = subprocess.run(
    cmd,
    cwd=str(workspace),
    capture_output=True,
    text=True,
    timeout=60,
)
return result.returncode, result.stderr
```

**Pre-call cleanup** (`:611-616`): removes stale `em.tpr*` backups and the target `.tpr` to avoid GROMACS's "Won't make more than 99 backups" error.

**Error handling in tests:** callers assert `rc == 0` and include `stderr` in the failure message (e.g. `tests/test_e2e_filled_ice_cli_hydrate_grompp.py:235`, `tests/test_e2e_mixed_lattice_gui.py:240-244`). A nonzero `rc` typically means: (a) `.top` references a residue not present in `.gro` (file-consistency failure), (b) a `#include`'d ITP is missing, (c) box shorter than `2*rcoulomb` (PBC cut-off fatal), or (d) atomtype conflict.

**Callers** (all test files, all gated by `@gmx_skipif`):
- `tests/test_e2e_filled_ice_cli_hydrate_grompp.py:233` (CLI hydrate c2te/ice1hte)
- `tests/test_e2e_mixed_filled_ice_gui.py:256` (GUI filled-ice single-cage)
- `tests/test_e2e_mixed_lattice_gui.py:240` (GUI sII/16 mixed built-in)
- `tests/test_e2e_custom_guest_lattices_cli.py:260` (CLI custom ethanol interface)
- `tests/test_e2e_custom_guest_lattices_gui.py:219` (GUI custom ethanol interface)
- `tests/test_cli_pipeline.py:704` (CLI subprocess → gmx grompp path)

Test fixtures (`tests/conftest.py:237-241`) also use `subprocess.run` (e.g. to detect `gmx` availability for the `gmx_skipif` marker / `gmx_workspace` fixture).

---

## 7. Summary of Key Constraints Verified in the Export Path

| Constraint (AGENTS.md) | Where enforced |
|------------------------|----------------|
| comb-rule=2 in ALL `.top` | every `[ defaults ]` line: `gromacs_writer.py:966, 1561, 1963, 2634, 3223, 3933` |
| Never hardcode TIP4P-ICE params | `TIP4P_ICE_OW_SIGMA`/`TIP4P_ICE_OW_EPSILON` (`gromacs_writer.py:56-57`) used in `WATER_ATOMTYPES` (`:97`) and `write_top_file` (`:970`); verified against `quickice/data/tip4p-ice.itp:4` (0.31668 nm, 0.88211 kJ/mol ✅) |
| `WATER_VOLUME_NM3 = 0.0299` | `types.py:39`; used in `pipeline.py:530,800`, `main_window.py:635,1214`, inserters |
| `WATER_ATOMS_PER_MOLECULE = 4` | `types.py:22`; used in `pipeline.py:895`, `ion_inserter.py:103,110,645`, `solute_inserter.py:457,463,634,751`, `custom_molecule_inserter.py:413,492,712,891,894` |
| `AVOGADRO` defined once | `ion_inserter.py:29` `AVOGADRO = 6.02214076e23`; imported everywhere else (`pipeline.py:15`, `solute_inserter.py:28`, `custom_molecule_inserter.py:28`, `ranking/scorer.py:18`) |
| All inserters return NEW structures | enforced in `ion_inserter.py` / `solute_inserter.py` / `custom_molecule_inserter.py` (V-17 fix) |
| Moleculetype `_H`/`_L` via registry | `moleculetype_registry.py:46/71`; never hardcoded |
| No bare `except Exception` in `cli/pipeline.py` | `pipeline.py:952` uses `except (OSError, ValueError)`; broad catches only in GUI (`export.py:256, 409, 585, 951, 1134`) |
| Atomic commits / no `git add .` | (process constraint, not code) |

---

## 8. Cross-Path Reconciliation (CLI vs GUI)

Both paths converge on the **same** `quickice/output/gromacs_writer.py` writers and the **same** `quickice/structure_generation/gromacs_ion_export.py::write_ion_itp`. Differences:

| Aspect | CLI | GUI |
|--------|-----|-----|
| Entry | `entry.py:186` → `main.py:23` → `CLIPipeline.execute` | `entry.py:176` → `main_window.py:2142 run_app` |
| Source generation | synchronous in `_run_source_step` | `HydrateWorker(QThread).run` (`hydrate_worker.py:50`) emits `generation_complete` |
| ITP staging | `cli/itp_helpers.py:282 copy_itp_files_for_structure` (single dispatcher) | per-exporter inline staging + shared `_stage_hydrate_guest_itps` (`guest_info.py:131`) |
| `custom_guest_info` source | `_build_custom_guest_info(self._hydrate_result.config)` (`pipeline.py:880`) | `_stage_hydrate_guest_itps(...)` returns it (`export.py:1096` etc.) |
| File destination | `{output_dir}/{step_name}.gro/.top` (auto-named) | `QFileDialog.getSaveFileName` user-chosen path; `.top`/`.itp` derived from `.gro` stem |
| Post-export | prints `[PROGRESS] Exported GROMACS: ...` (`pipeline.py:948`) | `QMessageBox.information("Export Complete", ...)` (`main_window.py:1631/1689/1722/1789/1849/1901`) |
| `gmx grompp` | NOT run | NOT run |
| Error handling | `except (OSError, ValueError)` → return 1 (`pipeline.py:952`) | `except Exception` → `QMessageBox.critical` + `traceback.print_exc` (e.g. `export.py:256-260`) |

---

*End of read-only flow trace. No source files were modified.*
