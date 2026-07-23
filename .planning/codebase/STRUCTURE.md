# Codebase Structure

**Analysis Date:** 2026-07-23

## Directory Layout

```
quickice/                          # Project root
├── quickice.py                    # Backward-compat launcher → entry.main()
├── conftest.py                    # Root pytest config
├── environment.yml                # Conda env (pinned deps)
├── environment-build.yml          # Build-time env (PyInstaller)
├── quickice-gui.spec              # PyInstaller spec for GUI binary
├── setup.sh                        # Sets PYTHONPATH to project root
├── QuickIce.sh / QuickIce.bat     # OS launchers
├── requirements-dev.txt
├── quickice/                      # Python package (import root)
│   ├── __init__.py / __main__.py  # python -m quickice → entry.main()
│   ├── entry.py                   # Unified CLI/GUI/help router
│   ├── main.py                    # CLI dispatcher (ice-only + pipeline)
│   ├── cli/                       # CLI layer (NO Qt/VTK imports)
│   ├── gui/                       # GUI layer (MVVM, PySide6 + VTK)
│   ├── structure_generation/      # Core physics engine (shared)
│   │   └── modes/                 # Interface assembly modes (slab/pocket/piece)
│   ├── output/                    # GROMACS/PDB/diagram writers (shared)
│   ├── phase_mapping/             # IAPWS ice-phase lookup
│   ├── ranking/                   # Candidate scoring
│   ├── validation/                # Input validators (argparse type=)
│   ├── utils/                     # Shared helpers (molecule_utils)
│   └── data/                      # Bundled ITP/GRO + examples
│       ├── custom/                # Custom-molecule sample (etoh.*)
│       └── examples/              # custom_positions.csv
├── tests/                         # pytest suite (~1007 tests)
│   ├── test_cli/                  # CLI-specific tests
│   ├── scancode/                  # Regression tests (test_scancode_bugs_*)
│   └── test_output/               # Output-fixtures tests
├── .github/workflows/             # CI (build-windows.yml)
├── sample_output/                 # Reference output (CLI + GUI samples)
├── docs/                          # Documentation + images
├── scripts/                       # Helper scripts
├── licenses/                      # Third-party license texts
└── .planning/                     # GSD planning docs (not committed source)
```

## Directory Purposes

**`quickice/cli/`:**
- Purpose: CLI-only orchestration. Must work without PySide6/VTK (verified: no such imports in source files).
- Contains: `parser.py` (argparse + pipeline flags), `pipeline.py` (`CLIPipeline` ordered steps), `itp_helpers.py` (ITP path resolution + `copy_itp_files_for_structure`).
- Key files: `quickice/cli/pipeline.py`, `quickice/cli/parser.py`, `quickice/cli/itp_helpers.py`.

**`quickice/gui/`:**
- Purpose: Qt-based GUI (MVVM). Imports PySide6 at module top in view-layer files; VTK probed via `vtk_utils.is_vtk_available()`.
- Contains: View (`view.py`, `main_window.py`, `*_panel.py`, `*_viewer.py`, `*_renderer.py`, `phase_diagram_widget.py`, `help_dialog.py`), ViewModel (`viewmodel.py`), Model/Workers (`workers.py`, `hydrate_worker.py`, inline `IonInsertionWorker` in `main_window.py`), Export (`export.py`, `hydrate_export.py`), Helpers (`constants.py`, `validators.py`, `vtk_utils.py`).
- Key files: `quickice/gui/main_window.py` (2318 lines — the View orchestrator), `quickice/gui/viewmodel.py`, `quickice/gui/constants.py` (`TabIndex` enum), `quickice/gui/export.py` (1138 lines — all GUI exporters).

**`quickice/structure_generation/`:**
- Purpose: Shared core physics engine. Generates ice/hydrate candidates, assembles interfaces, inserts solutes/custom-molecules/ions. No Qt/VTK.
- Contains: `types.py` (all dataclasses + constants), generators (`generator.py`, `hydrate_generator.py`), `interface_builder.py` + `modes/`, inserters (`ion_inserter.py`, `solute_inserter.py`, `custom_molecule_inserter.py`), `moleculetype_registry.py`, `molecule_validator.py`, `water_filler.py`, `overlap_resolver.py`, parsers (`gro_parser.py`, `itp_parser.py`), `mapper.py`, `cell_utils.py`, `errors.py`, `gromacs_ion_export.py`, `custom_guest_bridge.py`.
- Key files: `quickice/structure_generation/types.py` (1279 lines — the data model), `quickice/structure_generation/ion_inserter.py`, `quickice/structure_generation/solute_inserter.py`, `quickice/structure_generation/moleculetype_registry.py`.

**`quickice/structure_generation/modes/`:**
- Purpose: Three interface assembly geometries, each exposing `assemble_<mode>(candidate, config) -> InterfaceStructure`.
- Contains: `slab.py` (ice-water-ice sandwich along Z), `pocket.py` (water cavity in ice matrix), `piece.py` (ice crystal in water box).
- Key files: `quickice/structure_generation/modes/slab.py`, `pocket.py`, `piece.py`.

**`quickice/output/`:**
- Purpose: Serialize structures to GROMACS/PDB/diagrams. Shared by CLI + GUI.
- Contains: `gromacs_writer.py` (re-export facade), `_shared.py` (aggregator), 6 domain sub-modules (`_constants.py`, `_atomtypes.py`, `_pbc.py`, `_itp.py`, `_guest.py`, `_tip4p.py`), `_gro_format.py` (GRO line formatters), 6 per-structure writers (`ice_writer.py`, `interface_writer.py`, `multi_molecule_writer.py`, `ion_writer.py`, `custom_writer.py`, `solute_writer.py`), `guest_info.py` (custom-guest metadata + ITP staging), `orchestrator.py` (`output_ranked_candidates`), `pdb_writer.py`, `validator.py`, `phase_diagram.py`, `types.py` (`OutputResult`).
- Key files: `quickice/output/gromacs_writer.py` (import surface), `quickice/output/_shared.py`, `quickice/output/_constants.py` (TIP4P-ICE constants).

**`quickice/phase_mapping/`:**
- Purpose: IAPWS R14-08 melting-curve-based ice phase identification.
- Contains: `lookup.py` (`lookup_phase`, `IcePhaseLookup`, `PHASE_METADATA`), `melting_curves.py`, `solid_boundaries.py`, `triple_points.py`, `water_density.py`, `ice_ih_density.py`, `errors.py` (`PhaseMappingError`, `UnknownPhaseError`), `data/`.
- Key files: `quickice/phase_mapping/lookup.py`, `quickice/phase_mapping/errors.py`.

**`quickice/ranking/`:**
- Purpose: Multi-criteria candidate ranking (energy, density, diversity).
- Contains: `scorer.py` (`rank_candidates` + individual scorers), `types.py` (`RankedCandidate`, `RankingResult`, `ScoringConfig`).
- Key files: `quickice/ranking/scorer.py`, `quickice/ranking/types.py`.

**`quickice/validation/`:**
- Purpose: Input validators reused as argparse `type=` callbacks (CLI) and inline field checks (GUI).
- Contains: `validators.py` (`validate_temperature`, `validate_pressure`, `validate_nmolecules`, `validate_positive_float`, `validate_box_dimension`, `validate_concentration_range`, `validate_occupancy_range`).
- Key files: `quickice/validation/validators.py`.

**`quickice/utils/`:**
- Purpose: Cross-layer shared helpers.
- Contains: `molecule_utils.py` (`identify_guest_type`, `count_guest_atoms`, `iter_guest_molecules`, `separate_guests_by_type`).
- Key files: `quickice/utils/molecule_utils.py`.

**`quickice/data/`:**
- Purpose: Bundled static data shipped with the package. Read at runtime via `Path(quickice.__file__).parent / "data" / ...` (see `cli/itp_helpers.py:34`).
- Contains: TIP4P-ICE water template (`tip4p.gro`), `tip4p-ice.itp` (hyphen, NOT underscore — the `.top` `#include` line MUST match), guest ITPs (`ch4.itp`, `ch4_hydrate.itp`, `ch4_liquid.itp`, `thf.itp`, `thf_hydrate.itp`, `thf_liquid.itp`), `custom/` (sample `etoh.gro`/`etoh.itp`/`etoh.chg`/`etoh.top`, `test_invalid/`), `examples/custom_positions.csv`.
- Key files: `quickice/data/tip4p-ice.itp`, `quickice/data/tip4p.gro`, `quickice/data/ch4_hydrate.itp`.

**`tests/`:**
- Purpose: pytest suite (~1007 tests). Default discovery (no `pytest.ini`/`pyproject.toml`).
- Contains: `test_*.py` (unit), `test_e2e_*.py` (e2e), `test_scancode_bugs_*.py` (regression under `scancode/`), non-collected helpers (`e2e_export_helpers.py`, `_capture_gro_top_baseline.py` — no `test_` prefix), `conftest.py`, fixtures (`em.mdp` for GROMACS), `test_cli/` (CLI integration), `scancode/` (regression), `test_output/` (output fixtures).
- Key files: `tests/conftest.py`, `tests/e2e_export_helpers.py`.

## Key File Locations

**Entry Points:**
- `quickice/entry.py`: Unified router (`main()`). The ONLY place routing logic should live.
- `quickice/__main__.py`: `python -m quickice` → `entry.main()`.
- `quickice.py`: Backward-compat launcher → `entry.main()`.
- `quickice/main.py`: CLI dispatcher (`main()` → `CLIPipeline` or ice-only legacy).
- `quickice/gui/main_window.py:run_app()`: GUI entry (`quickice/gui/__main__.py`).

**Configuration:**
- `environment.yml` / `environment-build.yml`: Conda env pinning.
- `quickice-gui.spec`: PyInstaller spec.
- `setup.sh`: Sets `PYTHONPATH` to project root.
- `conftest.py` (root) + `tests/conftest.py`: pytest config/fixtures.
- `quickice/gui/constants.py`: `TabIndex` enum (single source of truth for tab indices).

**Core Logic:**
- `quickice/cli/pipeline.py`: `CLIPipeline` — ordered step execution.
- `quickice/structure_generation/types.py`: All structure dataclasses + constants (`WATER_VOLUME_NM3`, `WATER_ATOMS_PER_MOLECULE`, `HYDRATE_LATTICES`, `GUEST_MOLECULES`).
- `quickice/structure_generation/interface_builder.py`: `generate_interface` (routes to modes).
- `quickice/structure_generation/{ion,solute,custom_molecule}_inserter.py`: Inserters (return-NEW, cKDTree conditional rebuild).
- `quickice/structure_generation/moleculetype_registry.py`: `MoleculetypeRegistry` (`_H`/`_L` suffixes).
- `quickice/output/gromacs_writer.py`: GROMACS writer import facade.
- `quickice/output/_shared.py`: Shared writer helpers + `_write_top_defaults` (comb-rule=2).
- `quickice/output/_constants.py`: TIP4P-ICE LJ constants.

**Testing:**
- `tests/`: pytest root.
- `tests/test_cli/`: CLI integration tests.
- `tests/scancode/test_scancode_bugs_*.py`: Regression tests for documented bugs.
- `tests/e2e_export_helpers.py`: Non-collected e2e helpers (no `test_` prefix).

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g. `ion_inserter.py`, `moleculetype_registry.py`).
- Output sub-modules split from the original monolith use a leading underscore for "private" foundation modules (`_shared.py`, `_constants.py`, `_atomtypes.py`, `_pbc.py`, `_itp.py`, `_guest.py`, `_tip4p.py`, `_gro_format.py`) and public names for per-structure writers (`ice_writer.py`, `ion_writer.py`, ...).
- GUI files: `<feature>_panel.py` (tab UI), `<feature>_viewer.py` (3D VTK viewer), `<feature>_renderer.py` (actor creation), `<feature>_worker.py` (QThread worker).
- Test files: `test_*.py` (unit), `test_e2e_*.py` (end-to-end), `test_scancode_bugs_*.py` (regression). Non-collected helpers have NO `test_` prefix.

**Directories:**
- Package layers: lowercase singular nouns (`cli`, `gui`, `output`, `validation`, `utils`, `ranking`).
- `structure_generation/modes/`: one module per geometry mode (`slab`, `pocket`, `piece`).
- `data/`: flat layout for shipped assets; sub-dirs `custom/`, `examples/`.

**Classes:**
- Dataclasses: PascalCase nouns (`InterfaceStructure`, `HydrateConfig`, `IonStructure`).
- Generators/Inserters: PascalCase noun + role suffix (`IceStructureGenerator`, `HydrateStructureGenerator`, `IonInserter`, `SoluteInserter`, `CustomMoleculeInserter`, `MoleculetypeRegistry`).
- Qt widgets/panels: PascalCase + role suffix (`MainWindow`, `InputPanel`, `ProgressPanel`, `ViewerPanel`, `HydratePanel`, `InterfaceGROMACSExporter`, `HydrateWorker`).

**Functions:**
- Public entry points: `snake_case` verbs (`generate_interface`, `insert_ions`, `insert_solutes`, `lookup_phase`, `rank_candidates`, `output_ranked_candidates`, `assemble_slab`).
- Private helpers: leading underscore (`_build_custom_guest_info`, `_write_top_defaults`, `_format_atomtype_line`, `_parse_positions_csv`).
- Module re-export shims keep the original public name (e.g. `gromacs_writer.py` re-exports `write_ion_gro_file` from `ion_writer.py`).

## Where to Add New Code

**New CLI pipeline step (e.g. a new insertion stage):**
1. Add the dataclass config + result to `quickice/structure_generation/types.py` (follow `SoluteConfig`/`SoluteStructure`).
2. Implement the inserter as a new module `quickice/structure_generation/<name>_inserter.py` — return a NEW structure, never mutate input; use the `cKDTree` conditional-rebuild pattern (init `None`, rebuild only on successful placement).
3. Wire the step into `CLIPipeline.execute()` in `quickice/cli/pipeline.py` as a new `_run_<name>_step()` method, inserted at the correct position in the source → interface → custom → solute → ion → export chain.
4. Add CLI flags to `quickice/cli/parser.py::create_parser()` and validation to `validate_pipeline_args`.
5. Add a writer in `quickice/output/<name>_writer.py` (mirroring `solute_writer.py`), re-export it from `quickice/output/gromacs_writer.py`, and dispatch to it in `CLIPipeline._run_export_step` (priority order: most downstream wins).
6. Add ITP copying to `quickice/cli/itp_helpers.py::copy_itp_files_for_structure`.

**New GUI tab:**
1. Add a `TabIndex` member to `quickice/gui/constants.py::TabIndex` (IntEnum) — update the docstring with the new tab order.
2. Create `quickice/gui/<feature>_panel.py` containing a `<Feature>Panel(QWidget)` class (follow `solute_panel.py`).
3. Optionally add `quickice/gui/<feature>_viewer.py`, `<feature>_renderer.py`, and a worker in `quickice/gui/workers.py` (QObject+moveToThread) OR `quickice/gui/<feature>_worker.py` (direct `QThread` subclass — accepted only where mirroring `HydrateWorker`).
4. Instantiate the panel and `addTab(...)` in `MainWindow._setup_ui` (`quickice/gui/main_window.py:200-307`); wire cross-tab data flow via a new `self._current_<feature>_result` attribute (declare near lines 153-183) and pass it to downstream panels' source dropdowns.
5. Add a `<Feature>GROMACSExporter` in `quickice/gui/export.py` (or `hydrate_export.py` for hydrate-family) and instantiate it in `MainWindow.__init__` near lines 145-171.

**New ice/hydrate lattice:**
1. Add an entry to `HYDRATE_LATTICES` in `quickice/structure_generation/types.py` (with `genice_name`, `cages`, `unit_cell_molecules`, `cage_type_map`, `is_triclinic`, `is_water_only`).
2. If GenIce2 lattice module exists, register it in `HydrateStructureGenerator._ensure_genice_import` (`hydrate_generator.py:85`). For numeric lattice names (like `16`, `17`) use `safe_import` at runtime, not the import dict.
3. If a new guest molecule, add to `GUEST_MOLECULES` (`types.py:203`) and ship `_hydrate.itp` / `_liquid.itp` / `.itp` files in `quickice/data/`.

**New GROMACS writer (new structure type):**
1. Create `quickice/output/<name>_writer.py` exposing `write_<name>_gro_file(structure, filepath, custom_guest_info=...)` and `write_<name>_top_file(...)`. Call `_write_top_defaults(f, ...)` from `quickice/output/_shared.py` for the `[defaults]` block (comb-rule=2, always).
2. Re-export the new functions from `quickice/output/gromacs_writer.py` (the facade) so `from quickice.output.gromacs_writer import write_<name>_gro_file` works.
3. Use GRO line formatters from `quickice/output/_gro_format.py` (`_format_sol_ice_molecule`, `_format_guest_molecule`, etc.) to avoid duplicating format strings.
4. Add byte-equivalence tests under `tests/test_gro_top_byte_equivalence.py` style.

**New input validator:**
- Add to `quickice/validation/validators.py` (CLI-shared) and mirror in `quickice/gui/validators.py` for GUI inline use. Wire as argparse `type=` in `quickice/cli/parser.py`.

**New shared helper (cross-layer):**
- Pure molecule/structure helpers → `quickice/utils/molecule_utils.py`.
- GROMACS-format helpers → `quickice/output/_shared.py` or a new `_*.py` sub-module re-exported through `_shared.py`.
- Do NOT add cross-layer helpers to `cli/` or `gui/` — those layers must not depend on each other.

**New bundled data file:**
- Drop into `quickice/data/`. Resolve at runtime via `Path(quickice.__file__).parent / "data" / "<filename>"` (pattern in `cli/itp_helpers.py:34`, `output/_tip4p.py`). For test-only data use `tests/test_output/` or `tests/` fixtures, NOT `quickice/data/`.

**New test:**
- Unit test: `tests/test_<feature>.py`.
- End-to-end: `tests/test_e2e_<feature>.py`.
- Regression for a documented bug: `tests/scancode/test_scancode_bugs_<area>.py`.
- Non-collected helper: NO `test_` prefix (e.g. `e2e_export_helpers.py`).
- GROMACS-dependent tests: use the `@gmx_skipif` marker (skip if `gmx` not on PATH).
- Use `tmp_path` for temp files; `gmx_workspace` fixture for persistent GROMACS debugging; module-scoped fixtures for expensive GenIce2 calls.

## Special Directories

**`quickice/data/`:**
- Purpose: Shipped static assets (ITP, GRO, examples) read at runtime.
- Generated: No.
- Committed: Yes. Required for both CLI and GUI export.

**`sample_output/`:**
- Purpose: Reference output snapshots (CLI + GUI) for manual comparison/regression.
- Generated: Yes (by manual runs).
- Committed: Yes. Not imported by code.

**`tests/test_output/` & `tests/scancode/`:**
- Purpose: Test-only fixtures and regression suites.
- Generated: `test_output/` holds generated baselines.
- Committed: Yes.

**`.planning/`:**
- Purpose: GSD planning docs (phases, milestones, STATE.md, ROADMAP.md, this codebase analysis). NOT part of the shipped package.
- Generated: Yes (by GSD tooling).
- Committed: Yes (project history). Do NOT import from source code.

**`tmp/`:**
- Purpose: Scratch space for e2e GROMACS validation runs.
- Generated: Yes.
- Committed: No (gitignored).

**`build/` / `dist/`:**
- Purpose: PyInstaller build artifacts.
- Generated: Yes.
- Committed: No.

**`__pycache__/` (everywhere):**
- Purpose: Python bytecode cache.
- Generated: Yes.
- Committed: No.

---

*Structure analysis: 2026-07-23*
