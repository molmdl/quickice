# Codebase Structure

**Analysis Date:** 2026-10-15

## Directory Layout

```
quickice/                          # Project root (also the git repo root); package version 4.7.0
├── quickice.py                    # Backward-compat launcher → entry.main()
├── conftest.py                    # Root pytest config (registers "slow" marker)
├── environment.yml                # Conda env (pinned deps)
├── environment-build.yml          # Build-time env (PyInstaller)
├── lib-to-add.yml                 # Dependency candidate list (not installed)
├── quickice-gui.spec              # PyInstaller spec for GUI binary
├── setup.sh                       # Sets PYTHONPATH to project root
├── QuickIce.sh / QuickIce.bat     # OS launchers
├── requirements-dev.txt
├── README.md / README_bin.md      # Main + binary-distribution docs
├── state_reference.md
├── opencode.json                  # OpenCode agent config (+ several *.oc_free/*.syn* variants — session config, NOT source)
├── quickice/                      # Python package (import root)
│   ├── __init__.py                # __version__ = "4.7.0" (nothing else)
│   ├── __main__.py                # python -m quickice → entry.main()
│   ├── entry.py                   # Unified CLI/GUI/help router (all routing logic HERE)
│   ├── main.py                    # CLI dispatcher (ice-only + pipeline delegation)
│   ├── cli/                       # CLI layer (NO Qt/VTK imports)
│   ├── gui/                       # GUI layer (MVVM, PySide6 + VTK; PEP 562 lazy __init__)
│   ├── structure_generation/      # Core physics engine (shared; PEP 562 lazy __init__)
│   │   └── modes/                 # Interface assembly modes (slab/pocket/piece)
│   ├── output/                    # GROMACS/PDB/diagram writers (shared)
│   ├── phase_mapping/             # IAPWS ice-phase lookup
│   │   └── data/                  # ice_phases.json + ice_boundaries.py
│   ├── ranking/                   # Candidate scoring
│   ├── validation/                # Input validators (argparse type=)
│   ├── utils/                     # Shared helpers (molecule_utils)
│   ├── data/                      # Bundled ITP/GRO + examples
│   │   ├── custom/                # Custom-molecule sample (etoh.*) + test_invalid/
│   │   └── examples/              # custom_positions.csv
│   └── .planning/debug/           # STRAY: committed debug notes + untracked PDBs (not package code)
├── tests/                         # pytest suite (1849 collected tests)
│   ├── __init__.py
│   ├── conftest.py                # Session headless guard + markers + GenIce2 fixtures
│   ├── e2e_chain_fixtures.py      # Extracted module-scoped e2e chain fixtures (NOT a conftest)
│   ├── e2e_export_helpers.py      # Non-collected e2e helper (no test_ prefix)
│   ├── gui_e2e_helpers.py         # Non-collected headless-GUI e2e safety helpers
│   ├── repro_*.py                 # Non-collected repro scripts (2 files)
│   ├── _capture_gro_top_baseline.py  # Non-collected baseline capture script
│   ├── em.mdp                     # GROMACS mdp used by grompp e2e validation
│   ├── _baselines/                # Byte-equivalence baselines + SHA manifest
│   ├── e2e/                       # TRUE E2E tree, feature-organized: tests/e2e/<feature>/test_*.py
│   │   ├── chains/                # Full pipeline-chain tests (F1–F7 workflows)
│   │   ├── custom_guest/          # Custom-guest e2e (CLI + GUI + lattices + mixed cage)
│   │   ├── export_validation/     # gmx grompp validation + ITP baseline/staging tests
│   │   ├── hydrate/               # Hydrate e2e (generation, sH, triclinic, grompp)
│   │   ├── interface/             # Interface e2e (slab/pocket/piece, lattice interfaces)
│   │   ├── lattice/               # Lattice cross-tab + mixed-lattice e2e
│   │   ├── solute_ion/            # Solute/ion insertion + mixed/zero-ion export e2e
│   │   └── test_e2e_gui_fullchain.py  # GUI full-chain e2e (at e2e root, not in a feature dir)
│   ├── scancode/                  # Regression tests (test_scancode_bugs_*)
│   ├── test_cli/                  # CLI integration tests
│   └── test_output/               # Writer-level tests (synthetic structures; own conftest.py)
├── .github/                       # CI (workflows/build-windows.yml) + dependabot.yml
├── scripts/                       # Helper shell scripts (build, run, demos)
├── docs/                          # Documentation + images/
├── licenses/                      # Third-party license texts
├── sample_output/                 # Reference output snapshots (cli_ice, cli_interface, gui_interface, gui_v4)
├── .planning/                     # GSD workflow state: phases/, debug/, codebase/ (this map), STATE.md, ROADMAP.md
├── tmp/                           # Scratch space for e2e GROMACS runs (gitignored)
├── output/                        # Ad-hoc CLI output dumps (gitignored)
└── build/ / dist/                 # PyInstaller build artifacts (gitignored)
```

## Directory Purposes

**`quickice/` (package root):**
- Purpose: The importable Python package. Only 4 top-level modules.
- Key files: `quickice/entry.py` (the ONLY routing logic location), `quickice/main.py`, `quickice/__main__.py`, `quickice/__init__.py` (just `__version__`).

**`quickice/cli/`:**
- Purpose: CLI-only orchestration. Must work without PySide6/VTK (verified: no such imports in source files).
- Contains (complete): `quickice/cli/parser.py` (argparse + pipeline flags + `validate_pipeline_args`), `quickice/cli/pipeline.py` (`CLIPipeline` ordered steps, 1011 lines), `quickice/cli/itp_helpers.py` (ITP path resolution + `copy_itp_files_for_structure`), `quickice/cli/__init__.py`.

**`quickice/gui/`:**
- Purpose: Qt-based GUI (MVVM). View-layer files import PySide6 at module top; VTK probed via `vtk_utils.is_vtk_available()`.
- Startup note: `quickice/gui/__init__.py` uses PEP 562 `__getattr__`/`__dir__` lazy re-exports (slow-gui-startup fix) — importing `quickice.gui` does NOT load the ion renderer or any vtkmodules; submodules load on first attribute access.
- Contains: View (`main_window.py` 2319 lines, `view.py`, 5 feature panels: `custom_molecule_panel.py`/`hydrate_panel.py`/`interface_panel.py`/`ion_panel.py`/`solute_panel.py`, viewers: `custom_molecule_viewer.py`/`hydrate_viewer.py`/`interface_viewer.py`/`ion_viewer.py`/`solute_viewer.py`/`dual_viewer.py`/`molecular_viewer.py`, renderers: `custom_molecule_renderer.py`/`hydrate_renderer.py`/`ion_renderer.py`/`solute_renderer.py`, `phase_diagram_widget.py` (lightweight panel, 239 lines), `phase_diagram_canvas.py` (heavy matplotlib+shapely canvas, 635 lines — lazy-imported by the widget, split out in the slow-gui-startup fix), `help_dialog.py`), ViewModel (`viewmodel.py` 276 lines), Workers (`workers.py` (QObject+moveToThread), `hydrate_worker.py` (direct QThread — accepted), `custom_molecule_worker.py` (QObject)), Export (`export.py` 1259 lines — matplotlib/VTK deferred into methods, `hydrate_export.py`), Helpers (`constants.py` (`TabIndex`), `validators.py`, `vtk_utils.py` — ALL heavy imports lazy, cached `is_vtk_available()`), `gui/__main__.py` (GUI entry).

**`quickice/structure_generation/`:**
- Purpose: Shared core physics engine. Generates ice/hydrate candidates, assembles interfaces, inserts solutes/custom-molecules/ions. No Qt/VTK.
- Startup note: `quickice/structure_generation/__init__.py` uses PEP 562 lazy re-exports (slow-gui-startup fix) — a bare `import quickice.structure_generation.types` no longer drags in genice2/networkx/scipy (~0.5 s saved on CLI+GUI startup). Names resolve on first attribute access via the `_EXPORT_TO_MODULE` map; `IonConfig`/`IonStructure` are now genuinely importable from the package.
- Contains: `types.py` (1346 lines — the data model + constants), generators (`generator.py`, `hydrate_generator.py`), `interface_builder.py`, inserters (`ion_inserter.py` — module-level `cKDTree = None` lazy handle, patchable for the TREE regression tests; `solute_inserter.py`; `custom_molecule_inserter.py`), `moleculetype_registry.py`, `molecule_validator.py`, `water_filler.py`, `overlap_resolver.py` (scipy imported inside functions), parsers (`gro_parser.py`, `itp_parser.py`), `mapper.py`, `cell_utils.py`, `errors.py`, `gromacs_ion_export.py`, `custom_guest_bridge.py`, and `modes/` (`slab.py`, `pocket.py`, `piece.py`).

**`quickice/output/`:**
- Purpose: Serialize structures to GROMACS/PDB/diagrams. Shared by CLI + GUI.
- Contains: `gromacs_writer.py` (re-export facade; `__init__.py` of the package is an eager facade — keep heavy additions out of it), `_shared.py` (aggregator), private foundation modules `_constants.py`, `_atomtypes.py`, `_pbc.py`, `_itp.py`, `_guest.py`, `_tip4p.py`, `_gro_format.py`, per-structure writers (`ice_writer.py`, `interface_writer.py`, `multi_molecule_writer.py`, `ion_writer.py`, `custom_writer.py`, `solute_writer.py`), `guest_info.py`, `orchestrator.py`, `pdb_writer.py`, `validator.py`, `phase_diagram.py`, `types.py`.

**`quickice/phase_mapping/`:**
- Purpose: IAPWS R14-08 melting-curve-based ice phase identification.
- Contains: `lookup.py` (`lookup_phase`, `IcePhaseLookup`, `PHASE_METADATA`), `melting_curves.py`, `solid_boundaries.py`, `triple_points.py`, `water_density.py`, `ice_ih_density.py`, `errors.py`, and `data/` (`ice_phases.json`, `ice_boundaries.py`).

**`quickice/ranking/`:**
- Purpose: Multi-criteria candidate ranking (energy, density, diversity).
- Contains: `scorer.py` (`rank_candidates` + individual scorers), `types.py` (`RankedCandidate`, `RankingResult`, `ScoringConfig`).

**`quickice/validation/`:**
- Purpose: Input validators reused as argparse `type=` callbacks (CLI) and inline field checks (GUI).
- Contains: `validators.py` (single module).

**`quickice/utils/`:**
- Purpose: Cross-layer shared helpers.
- Contains: `molecule_utils.py` (`identify_guest_type`, `count_guest_atoms`, `iter_guest_molecules`, `separate_guests_by_type`).

**`quickice/data/`:**
- Purpose: Bundled static data shipped with the package. Read at runtime via `Path(quickice.__file__).parent / "data" / ...`.
- Contains: `tip4p.gro`, `tip4p-ice.itp` (hyphen, NOT underscore — the `.top` `#include` line MUST match; a `tip4p-ice.itp.bak` also sits here), guest ITPs (`ch4.itp`, `ch4_hydrate.itp`, `ch4_liquid.itp`, `thf.itp`, `thf_hydrate.itp`, `thf_liquid.itp`), `custom/` (sample `etoh.gro`/`etoh.itp`/`etoh.chg`/`etoh.top` + `test_invalid/`), `examples/custom_positions.csv`.

**`tests/`:**
- Purpose: pytest suite — **1849 tests collected** (verified via `pytest --collect-only`). Default discovery (no `pytest.ini`/`pyproject.toml`).
- Contains `tests/__init__.py` (package marker for the test tree).
- See the full `tests/` tree section below for details.

## The tests/ Tree (current state)

All e2e tests live in a feature-organized tree. **Root-level e2e file count: 0** (the pre-48.3 root-level `test_e2e_*.py` files were regrouped into `tests/e2e/<feature>/`; pre-regroup locations remain git-history traceable).

**conftest files (complete list — exactly 3, live OUTSIDE the e2e tree):**
- `conftest.py` (project root): registers the `slow` marker.
- `tests/conftest.py`: enforces `QT_QPA_PLATFORM=offscreen` at session start (BEFORE any Qt import), registers markers `slow`/`e2e`/`gui`/`cli`, provides the `gmx_skipif` availability marker, module-scoped GenIce2 fixtures (`ice_ih_candidate`, `hydrate_sI_ch4_candidate`, `hydrate_sI_ch4_structure`, `hydrate_sII_*`, `interface_slab`, `interface_pocket`, `interface_hydrate_slab`) and the `run_quickice` subprocess helper.
- `tests/test_output/conftest.py`: synthetic hand-built structure fixtures + mock dialog fixtures for writer-level exporter tests (NOT real-chain e2e).
- **There is NO conftest.py anywhere under `tests/e2e/`** — an INFRA collision rule forbids new conftest files in the e2e tree.

**`tests/e2e/` (true e2e, feature-organized):**
- Purpose: e2e tests that build structures via real generators/inserters, export through a real pipeline surface, and assert `gmx grompp` rc==0 when gmx is present (the "true e2e" definition from AGENTS.md).
- Structure: `tests/e2e/__init__.py` + one sub-directory per feature, each with its own `__init__.py`:
  - `tests/e2e/chains/`: 2 test files — `test_chain_structures.py` (full Ice→Interface→Custom→Solute→Ion chains F1–F7), `test_e2e_builtin_cross_tab_regression.py`.
  - `tests/e2e/custom_guest/`: 8 test files — cross-tab CLI/GUI, lattice CLI/GUI, mixed-cage (plain + interface), same-basename collision, plain custom-molecule inserter test.
  - `tests/e2e/export_validation/`: 4 test files — `test_e2e_gmx_validation.py` (grompp matrix, `gmx_workspace` fixture at line 85), `test_e2e_gmx_param_validation.py` (`gmx_workspace` fixture at line 208), `test_itp_baseline_data.py`, `test_stage_custom_guest_itp.py`.
  - `tests/e2e/hydrate/`: 9 test files — generation, custom-guest hydrate, filled-ice CLI grompp, same-custom-two-cages, sH cross-tab, sH cage occupancy, triclinic export, mixed placement, CLI mixed builtin hydrate grompp.
  - `tests/e2e/interface/`: 7 test files — lattice interface CLI/GUI, pocket/piece grompp, triclinic blocking e2e, ice/interface/mixed-interface generation.
  - `tests/e2e/lattice/`: 6 test files — cross-tab CLI/GUI, mixed builtin interface export, mixed filled-ice GUI, mixed lattice GUI, water-only cross-tab.
  - `tests/e2e/solute_ion/`: 4 test files — mixed ion export, zero-ion CLI export, ion insertion, solute insertion.
  - Plus `tests/e2e/test_e2e_gui_fullchain.py` at the e2e root (GUI full-chain; the only e2e file not inside a feature dir).
- Naming note: most files follow `test_e2e_*.py`, but some feature-local files use plain `test_*.py` names (e.g. `test_chain_structures.py`, `test_hydrate_generation.py`, `test_ion_insertion.py`) — they are still collected because pytest default discovery matches any `test_*.py`.

**`tests/e2e_chain_fixtures.py`:**
- Purpose: ONE plain module (NOT a conftest) holding the 3 extracted module-scoped fixture clusters that were near-copy duplicates across e2e files (48.3-20 fixture dedup): `custom_guest_chains` (line 99), `lattice_chains` (line 292), `filled_ice_hydrates` (line 347). Fixtures imported into a test module's namespace resolve normally and keep their declared module scope.
- Consumers (6 test modules + `tests/e2e/__init__.py`): `tests/e2e/custom_guest/test_e2e_custom_guest_lattices_cli.py`, `tests/e2e/custom_guest/test_e2e_custom_guest_lattices_gui.py`, `tests/e2e/interface/test_e2e_lattice_interface_cli.py`, `tests/e2e/interface/test_e2e_lattice_interface_gui.py`, `tests/e2e/hydrate/test_e2e_filled_ice_cli_hydrate_grompp.py`, `tests/e2e/lattice/test_e2e_mixed_filled_ice_gui.py`.

**Non-collected helpers (no `test_` prefix) at `tests/` root:**
- `tests/e2e_export_helpers.py`: shared e2e export helpers.
- `tests/gui_e2e_helpers.py`: headless-GUI e2e safety infrastructure (modal-dialog patching, offscreen guard helpers) backing MainWindow-driven tests.
- `tests/repro_sii_mixed_gui_regression.py`, `tests/repro_thf_bonds_viewer.py`: manual repro scripts.
- `tests/_capture_gro_top_baseline.py`: regenerates `tests/_baselines/` snapshots + SHA manifest.

**`tests/_baselines/`:**
- Purpose: Byte-equivalence baselines for `tests/test_gro_top_byte_equivalence.py` and `tests/e2e/export_validation/test_itp_baseline_data.py`.
- Contains: `baseline_shas.json` (authoritative SHA manifest) + `snapshots/baseline/<feature>/` (features: `custom`, `custom_guest`, `hydrate`, `ice`, `interface`, `ion`, `solute` — each holding `.gro`/`.top`/`.itp` snapshots). Regenerate via `tests/_capture_gro_top_baseline.py`.

**`tests/scancode/`:**
- Purpose: Regression tests for documented bugs (17 test files, all named `test_scancode_bugs_*.py`, covering constants, dead-code-pdb, documentation, gromacs, GUI-ion, inserter perf + rebuild, inserters, ion alternation/charge-warning/tree-rebuild, pipeline, solute, structure-gen, tech-debt, triclinic-pbc, vtk-dup) + `__init__.py`.
- Note: two additional scancode-named files live at `tests/` root instead: `tests/test_scancode_bugs_custom_guest_bridge_assert.py`, `tests/test_scancode_bugs_piece_logger.py`.

**`tests/test_cli/`:**
- Purpose: CLI integration tests (9 test files + `__init__.py`): `test_cli_integration.py`, `test_cli_pipeline.py`, `test_depol_flag.py`, `test_integration_v35.py`, `test_itp_helpers_custom_guest.py`, `test_mixed_cage_cli.py`, `test_pipeline_custom_guest_export.py`, `test_pipeline_grompp_matrix.py`, `test_pipeline_step_chain_e2e.py`.

**`tests/test_output/`:**
- Purpose: Writer-level GROMACS export tests built from SYNTHETIC hand-made structures (has its own `conftest.py` + `__init__.py`; real-chain e2e lives in `tests/e2e/`). 20 test files covering ice/hydrate/interface/ion/solute/custom export chains, gro-format helpers, custom-guest ITP merging, molecule wrapping, PDB writer, top defaults, validator.

**Unit tests at `tests/` root (57 files):**
- Purpose: Focused unit/feature tests, one file per concern (e.g. `tests/test_pbc_wrapping.py`, `tests/test_moleculetype_registry.py`, `tests/test_tip4p_ice_lj_values.py`, `tests/test_custom_molecule_residue_reconciliation.py`, `tests/test_thf_bonds_viewer_issue2.py`, `tests/test_uat_f_custom_guest_fixes.py`, `tests/test_scancode_bugs_custom_guest_bridge_assert.py`, `tests/test_scancode_bugs_piece_logger.py`).

**GROMACS e2e infrastructure:**
- `tests/em.mdp`: energy-minimization mdp copied into every grompp workspace.
- `gmx_workspace` fixture: defined per-module (NOT in a conftest) in `tests/e2e/export_validation/test_e2e_gmx_validation.py:85` and `tests/e2e/export_validation/test_e2e_gmx_param_validation.py:208` — persistent directory for debugging failed grompp runs.

## Key File Locations

**Entry Points:**
- `quickice/entry.py`: Unified router (`main()`, line 105). The ONLY place routing logic should live.
- `quickice/__main__.py`: `python -m quickice` → `entry.main()`.
- `quickice.py`: Backward-compat launcher → `entry.main()`.
- `quickice/main.py`: CLI dispatcher (`main()` line 23 → `CLIPipeline` or ice-only legacy).
- `quickice/gui/__main__.py` → `quickice/gui/main_window.py:run_app()` (line 2287): GUI entry.

**Configuration:**
- `environment.yml` / `environment-build.yml`: Conda env pinning.
- `quickice-gui.spec`: PyInstaller spec.
- `setup.sh`: Sets `PYTHONPATH` to project root.
- `conftest.py` (root), `tests/conftest.py`, `tests/test_output/conftest.py`: the complete pytest config/fixture set.
- `quickice/gui/constants.py`: `TabIndex` enum (ICE=0, HYDRATE=1, INTERFACE=2, CUSTOM=3, SOLUTE=4, ION=5 — single source of truth for tab indices).

**Core Logic:**
- `quickice/cli/pipeline.py`: `CLIPipeline` (line 133) — ordered step execution: `execute()` (line 154) → source (line 330) → interface (line 437) → custom (line 487) → solute (line 629) → ion (line 700) → export (line 859).
- `quickice/structure_generation/types.py`: All structure dataclasses + constants (`WATER_VOLUME_NM3` line 39, `WATER_ATOMS_PER_MOLECULE` line 22, `HYDRATE_LATTICES`, `GUEST_MOLECULES`).
- `quickice/structure_generation/interface_builder.py`: `generate_interface` (routes to modes).
- `quickice/structure_generation/{ion,solute,custom_molecule}_inserter.py`: Inserters (return-NEW, cKDTree conditional rebuild).
- `quickice/structure_generation/moleculetype_registry.py`: `MoleculetypeRegistry` (line 13; `_H`/`_L` suffixes, `RESERVED_NAMES` line 35).
- `quickice/output/gromacs_writer.py`: GROMACS writer import facade.
- `quickice/output/_shared.py`: Shared writer helpers + `_write_top_defaults` (comb-rule=2).
- `quickice/output/_constants.py`: TIP4P-ICE LJ constants.
- `quickice/gui/vtk_utils.py`: `is_vtk_available()` (line 958) + cached result + `reset_vtk_available_cache()` (line 1001); all heavy imports lazy.

**Lazy-import infrastructure (slow-gui-startup fix):**
- `quickice/gui/__init__.py`: PEP 562 `__getattr__`/`__dir__` lazy re-export map (MainWindow, run_app, panels, ion renderer symbols).
- `quickice/structure_generation/__init__.py`: PEP 562 lazy re-export map (types, errors, mapper, generators, interface builder, water/overlap helpers, ion inserter, gro parser, ion export, cell utils).
- `quickice/gui/phase_diagram_canvas.py`: heavy matplotlib+shapely canvas; imported lazily by `quickice/gui/phase_diagram_widget.py` only when the canvas is built.
- `quickice/structure_generation/ion_inserter.py`: `cKDTree = None` module-attribute lazy handle (must stay a module attribute — TREE regression tests patch it).

**Testing:**
- `tests/`: pytest root (1849 tests).
- `tests/e2e/<feature>/test_*.py`: true e2e (features: `chains`, `custom_guest`, `export_validation`, `hydrate`, `interface`, `lattice`, `solute_ion`).
- `tests/e2e_chain_fixtures.py`: shared e2e chain fixtures (import, not conftest).
- `tests/scancode/test_scancode_bugs_*.py`: regression tests for documented bugs.
- `tests/test_output/`: writer-level export tests (synthetic structures).

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g. `ion_inserter.py`, `moleculetype_registry.py`).
- Output sub-modules: leading underscore for "private" foundation modules (`_shared.py`, `_constants.py`, `_atomtypes.py`, `_pbc.py`, `_itp.py`, `_guest.py`, `_tip4p.py`, `_gro_format.py`); public names for per-structure writers (`ice_writer.py`, `ion_writer.py`, ...).
- GUI files: `<feature>_panel.py` (tab UI), `<feature>_viewer.py` (3D VTK viewer), `<feature>_renderer.py` (actor creation), `<feature>_worker.py` (QThread worker). Lightweight widget + heavy canvas split uses `_widget.py` (light) / `_canvas.py` (heavy) — see `phase_diagram_widget.py` / `phase_diagram_canvas.py`.
- Test files: `test_*.py` (unit), `tests/e2e/<feature>/test_e2e_*.py` (true e2e), `test_scancode_bugs_*.py` (regression). Non-collected helpers have NO `test_` prefix (e.g. `tests/e2e_export_helpers.py`, `tests/gui_e2e_helpers.py`).

**Directories:**
- Package layers: lowercase singular nouns (`cli`, `gui`, `output`, `validation`, `utils`, `ranking`).
- `structure_generation/modes/`: one module per geometry mode (`slab`, `pocket`, `piece`).
- `tests/e2e/<feature>/`: one directory per e2e feature (`chains`, `custom_guest`, `export_validation`, `hydrate`, `interface`, `lattice`, `solute_ion`), each with `__init__.py`.
- `data/`: flat layout for shipped assets; sub-dirs `custom/`, `examples/`.

**Classes:**
- Dataclasses: PascalCase nouns (`InterfaceStructure`, `HydrateConfig`, `IonStructure`).
- Generators/Inserters: PascalCase noun + role suffix (`IceStructureGenerator`, `HydrateStructureGenerator`, `IonInserter`, `SoluteInserter`, `CustomMoleculeInserter`, `MoleculetypeRegistry`).
- Qt widgets/panels/workers/exporters: PascalCase + role suffix (`MainWindow`, `InputPanel`, `ProgressPanel`, `ViewerPanel`, `HydratePanel`, `PhaseDiagramPanel`, `PhaseDiagramCanvas`, `InterfaceGROMACSExporter`, `HydrateWorker`).

**Functions:**
- Public entry points: `snake_case` verbs (`generate_interface`, `insert_ions`, `insert_solutes`, `lookup_phase`, `rank_candidates`, `output_ranked_candidates`, `assemble_slab`).
- Private helpers: leading underscore (`_build_custom_guest_info`, `_write_top_defaults`, `_format_atomtype_line`, `_parse_positions_csv`, `_build_guest_molecule_boundaries`).
- Module re-export shims keep the original public name (e.g. `quickice/output/gromacs_writer.py` re-exports `write_ion_gro_file` from `ion_writer.py`; `quickice/gui/phase_diagram_widget.py` lazily forwards `PhaseDiagramCanvas`).

## Where to Add New Code

**New CLI pipeline step (e.g. a new insertion stage):**
1. Add the dataclass config + result to `quickice/structure_generation/types.py` (follow `SoluteConfig`/`SoluteStructure`).
2. Implement the inserter as a new module `quickice/structure_generation/<name>_inserter.py` — return a NEW structure, never mutate input; use the `cKDTree` conditional-rebuild pattern (init `None`, rebuild only on successful placement). If tests need to patch the tree, use the `cKDTree = None` module-attribute handle pattern from `ion_inserter.py` (NOT a function-local import).
3. Wire the step into `CLIPipeline.execute()` in `quickice/cli/pipeline.py` as a new `_run_<name>_step()` method, inserted at the correct position in the source → interface → custom → solute → ion → export chain. Import heavy structure-generation modules lazily inside the step method.
4. Add CLI flags to `quickice/cli/parser.py::create_parser()` and validation to `validate_pipeline_args`.
5. Add a writer in `quickice/output/<name>_writer.py` (mirroring `solute_writer.py`), re-export it from `quickice/output/gromacs_writer.py`, and dispatch to it in `CLIPipeline._run_export_step` (priority order: most downstream wins).
6. Add ITP copying to `quickice/cli/itp_helpers.py::copy_itp_files_for_structure`.

**New GUI tab:**
1. Add a `TabIndex` member to `quickice/gui/constants.py::TabIndex` (IntEnum) — update the docstring with the new tab order.
2. Create `quickice/gui/<feature>_panel.py` containing a `<Feature>Panel(QWidget)` class (follow `quickice/gui/solute_panel.py`).
3. Optionally add `quickice/gui/<feature>_viewer.py`, `<feature>_renderer.py`, and a worker in `quickice/gui/workers.py` (QObject+moveToThread) OR `quickice/gui/<feature>_worker.py` (direct `QThread` subclass — accepted only where mirroring `HydrateWorker` in `quickice/gui/hydrate_worker.py`).
4. Instantiate the panel and `addTab(...)` in `MainWindow._setup_ui` (`quickice/gui/main_window.py`); wire cross-tab data flow via a new `self._current_<feature>_result` attribute and pass it to downstream panels' source dropdowns.
5. Add a `<Feature>GROMACSExporter` in `quickice/gui/export.py` (or `quickice/gui/hydrate_export.py` for hydrate-family) and instantiate it in `MainWindow.__init__`.
6. If the renderer symbols should be package-accessible, add them to `_EXPORT_TO_MODULE` in `quickice/gui/__init__.py` (lazy) — do NOT switch to eager imports.

**New ice/hydrate lattice:**
1. Add an entry to `HYDRATE_LATTICES` in `quickice/structure_generation/types.py` (with `genice_name`, `cages`, `unit_cell_molecules`, `cage_type_map`, `is_triclinic`, `is_water_only`).
2. If a GenIce2 lattice module exists, register it in `HydrateStructureGenerator._ensure_genice_import` (`quickice/structure_generation/hydrate_generator.py:67`). For numeric lattice names (like `16`, `17`) use `safe_import` at generation time (line ~255), not the import dict.
3. If a new guest molecule, add to `GUEST_MOLECULES` in `types.py` and ship `<guest>.itp` / `<guest>_hydrate.itp` / `<guest>_liquid.itp` files in `quickice/data/`. Register the guest names in `MoleculetypeRegistry.RESERVED_NAMES` if they could collide.

**New GROMACS writer (new structure type):**
1. Create `quickice/output/<name>_writer.py` exposing `write_<name>_gro_file(structure, filepath, custom_guest_info=...)` and `write_<name>_top_file(...)`. Call `_write_top_defaults(f, ...)` from `quickice/output/_shared.py` for the `[defaults]` block (comb-rule=2, always).
2. Re-export the new functions from `quickice/output/gromacs_writer.py` (the facade) so `from quickice.output.gromacs_writer import write_<name>_gro_file` works.
3. Use GRO line formatters from `quickice/output/_gro_format.py` to avoid duplicating format strings.
4. Add byte-equivalence tests in the `tests/test_gro_top_byte_equivalence.py` style; add/refresh baselines via `tests/_capture_gro_top_baseline.py`.

**New input validator:**
- Add to `quickice/validation/validators.py` (CLI-shared) and mirror in `quickice/gui/validators.py` for GUI inline use. Wire as argparse `type=` in `quickice/cli/parser.py`.

**New shared helper (cross-layer):**
- Pure molecule/structure helpers → `quickice/utils/molecule_utils.py`.
- GROMACS-format helpers → `quickice/output/_shared.py` or a new `_*.py` sub-module re-exported through `_shared.py`.
- Do NOT add cross-layer helpers to `cli/` or `gui/` — those layers must not depend on each other.

**New bundled data file:**
- Drop into `quickice/data/`. Resolve at runtime via `Path(quickice.__file__).parent / "data" / "<filename>"` (pattern in `quickice/cli/itp_helpers.py`, `quickice/output/_tip4p.py`). For test-only data use `tests/_baselines/` or `tests/test_output/` fixtures, NOT `quickice/data/`.

**New test (IMPORTANT — current rules):**
- Unit test: `tests/test_<feature>.py`.
- True e2e test: `tests/e2e/<feature>/test_e2e_<name>.py` — pick the feature dir matching the pipeline surface (`chains`, `custom_guest`, `export_validation`, `hydrate`, `interface`, `lattice`, `solute_ion`). Each feature dir must contain `__init__.py`. Do NOT create root-level `test_e2e_*.py` files and do NOT add new conftest.py files under `tests/e2e/` (INFRA collision rule).
- Shared e2e chain fixtures: add to `tests/e2e_chain_fixtures.py` (plain module, imported by consuming test modules — module scope is preserved) ONLY if the fixture body is identical across consumers; divergent same-name fixtures stay local and get renamed apart.
- GUI e2e safety helpers: extend `tests/gui_e2e_helpers.py` (modal catalog, offscreen guards).
- Regression for a documented bug: `tests/scancode/test_scancode_bugs_<area>.py`.
- Non-collected helper: NO `test_` prefix (e.g. `tests/e2e_export_helpers.py`).
- GROMACS-dependent tests: use the `@gmx_skipif` marker (skip if `gmx` not on PATH) and copy `tests/em.mdp` into the workspace.
- Use `tmp_path` for temp files; a local `gmx_workspace` fixture (pattern in `tests/e2e/export_validation/test_e2e_gmx_validation.py:85`) for persistent GROMACS debugging; module-scoped fixtures for expensive GenIce2 calls.

**New heavy import (CRITICAL — lazy-import rule):**
- NEVER add a heavy top-level import (PySide6 submodules beyond what a module already pulls, vtkmodules, scipy, matplotlib, gensice2/networkx) to any module reachable from CLI or GUI startup — put it inside the function/method that needs it, with a `# Lazy import (AGENTS.md)` comment.
- Exception within GUI: view-layer widgets already import PySide6 at module top (that is their purpose); the rule targets scientific/rendering stacks.
- If a package-level re-export is needed, add the name to `_EXPORT_TO_MODULE` in `quickice/gui/__init__.py` or `quickice/structure_generation/__init__.py` — do not add eager imports to those files.
- For new heavy rendering, follow the widget/canvas split pattern: light UI module (eagerly importable) + heavy canvas module imported lazily at build/show time (`phase_diagram_widget.py` ↔ `phase_diagram_canvas.py`).

## Special Directories

**`quickice/data/`:**
- Purpose: Shipped static assets (ITP, GRO, examples) read at runtime.
- Generated: No.
- Committed: Yes. Required for both CLI and GUI export.

**`tests/_baselines/`:**
- Purpose: Byte-equivalence reference snapshots + SHA manifest for export regression tests.
- Generated: Yes (by `tests/_capture_gro_top_baseline.py`).
- Committed: Yes. Refresh deliberately when writer output legitimately changes.

**`tests/e2e/`:**
- Purpose: True-e2e feature tree (real generators → real pipeline surface → `gmx grompp`).
- Generated: No (hand-written tests).
- Committed: Yes.

**`sample_output/`:**
- Purpose: Reference output snapshots (CLI + GUI) for manual comparison/regression.
- Generated: Yes (by manual runs).
- Committed: Yes. Not imported by code.

**`.planning/`:**
- Purpose: GSD workflow state — phases (`.planning/phases/`), debug notes (`.planning/debug/`), this codebase map (`.planning/codebase/`), plus `PROJECT.md`, `REQUIREMENTS.md`, `STATE.md`, `ROADMAP.md`, milestones and misc analysis docs. NOT part of the shipped package.
- Generated: Yes (by GSD tooling).
- Committed: Yes (project history). Do NOT import from source code.
- Note: a stray `​.planning/34.6-revise-custom-panel-valid-input/` directory sits at `.planning/` root (plan + debug note that belong elsewhere) — safe to ignore; do not add new content there.

**`quickice/.planning/debug/`:**
- Purpose: STRAY directory inside the package — committed debug notes + untracked ice-candidate PDB dumps. Not package code; safe to ignore (candidate for cleanup).

**`tmp/` / `output/`:**
- Purpose: `tmp/` is scratch space for e2e GROMACS validation runs and probes; `output/` holds ad-hoc CLI output dumps.
- Generated: Yes.
- Committed: No (both gitignored).

**`build/` / `dist/`:**
- Purpose: PyInstaller build artifacts.
- Generated: Yes.
- Committed: No.

**`__pycache__/` / `.pytest_cache/` (everywhere):**
- Purpose: Python bytecode / pytest caches.
- Generated: Yes.
- Committed: No.

---

*Structure analysis: 2026-10-15*
