# AGENTS.md

## Environment

- **Conda only.** Never `sudo`, `apt`, `pip install` system-wide, or modify anything outside user-space. All deps live in the `quickice` conda env.
- To add a dependency: edit `environment.yml`, then ask user to run `conda env update`. Do NOT auto-install.
- Python 3.14.3 (conda-forge). Activate env: `conda activate quickice`.
- `PYTHONPATH` must include project root (handled by `setup.sh`).

## Run Commands

```bash
pytest                          # All tests (~1007)
pytest tests/test_foo.py        # Single file
pytest -k "test_pbc"            # Match by name
pytest -x                       # Stop on first failure
pytest --timeout=120            # With timeout (if pytest-timeout installed)
pytest --cov=quickice --cov-report=term-missing   # Coverage
```

No linter or formatter is configured (no black, ruff, flake8, mypy). No `pyproject.toml`.

## Architecture

Dual-path app sharing a core physics engine:
- **CLI path:** `entry.py` → `main.py` → `CLIPipeline.execute()` — ordered step execution, fail-fast. **No Qt/PySide6/VTK imports in `quickice/cli/`.**
- **GUI path:** `entry.py` → `main_window.py` (MVVM). `HydrateWorker` subclasses `QThread` directly (not migrated to QObject+moveToThread) — do not "fix" this.
- **Shared core:** `quickice/structure_generation/` + `quickice/output/` — used by both paths.

CLI pipeline step order: source → interface → custom → solute → ion → export.
Entry router is `quickice/entry.py::main()` — add routing logic there, not in `__main__.py` or `quickice.py`.

### Cross-Tab Data Flow (GUI)

Tab 0 (Ice) → Tab 2 (Interface) → Tab 3 (Custom) → Tab 4 (Solute) → Tab 5 (Ion) → Export

MainWindow stores results as `_current_*_result` attributes. Duck-typing sets runtime attributes on `InterfaceStructure` (e.g., `.solute_type`, `.custom_molecule_positions`). This is an accepted design decision (CP-01), NOT a bug.

## Constraints

- **Never auto-install dependencies.** Add to `environment.yml`, seek approval, wait for user.
- **Never make up references or data.** Always verify sources. Document limitations explicitly. If you must guess, explicitly label it as a guess. After verifying a reference, show it to the user and seek approval before including it in the codebase.
- **Headless/remote VTK:** GUI tests require `QT_QPA_PLATFORM=offscreen` on machines without a display. VTK rendering may still crash in some headless environments — mock or skip VTK-dependent tests if needed. See ROADMAP.md TEST-06 (deferred).
- **No bare `except Exception`** in core pipeline code (`quickice/cli/pipeline.py`). Use `except (ValueError, OSError)` or more specific. GUI code may use broad catches for user-facing workflows.
- **comb-rule=2** (Lorentz-Berthelot) in ALL GROMACS `.top` files — AMBER/GAFF2 convention. Never use comb-rule=1.
- **Never hardcode TIP4P-ICE parameters.** Use module constants (`TIP4P_ICE_OW_SIGMA` / `TIP4P_ICE_OW_EPSILON` in `quickice/output/gromacs_writer.py`). For verification, check `quickice/data/tip4p-ice.itp` or the original literature (Abascal et al. 2005, DOI: 10.1063/1.1931662).
- **Never hardcode `0.0299`** for water volume. Use `WATER_VOLUME_NM3` from `quickice/structure_generation/types.py`.
- **Never hardcode `4`** for water atoms per molecule. Use `WATER_ATOMS_PER_MOLECULE` from `types.py`.
- **AVOGADRO** is defined once in `ion_inserter.py` — import from there, never duplicate.
- **All inserters return NEW structure objects.** Never mutate input structures (V-17 fix).
- **cKDTree conditional rebuild:** Initialize tree as `None`, rebuild ONLY after successful placement (not on rejection). See `ion_inserter.py` and `solute_inserter.py`.
- **Moleculetype naming:** Hydrate guests use `_H` suffix, liquid solutes use `_L` suffix. `MoleculetypeRegistry` in `quickice/structure_generation/moleculetype_registry.py` manages this. Never hardcode moleculetype names.
- **Atomic commits only.** Never `git add .` or `git add -A`. Stage only intended files with `git add <path>`. Each commit should represent one logical change.

## Testing

- **pytest** with default discovery (no `pytest.ini` or `pyproject.toml`).
- Test files: `test_*.py` (unit), `test_e2e_*.py` (e2e), `test_scancode_bugs_*.py` (regression).
- Non-collected helpers: no `test_` prefix (e.g., `e2e_export_helpers.py`).
- GROMACS-dependent tests use `@gmx_skipif` marker (skip if `gmx` not on PATH).
- Module-scoped fixtures amortize expensive GenIce2 calls (~3-5s each).
- `tmp_path` for temp files (auto-cleaned); `gmx_workspace` for persistent GROMACS debugging.

## Lazy Imports

PySide6, VTK, GenIce2 are imported inside function bodies (never at module top level). `entry.py` uses `importlib.util.find_spec('PySide6')` to check availability without importing.
