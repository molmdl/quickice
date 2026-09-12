# Coding Conventions

**Analysis Date:** 2026-09-12

## Languages & Runtime

- **Python 3.14** (`python=3.14.3` in `environment.yml`). Conda env `quickice` is the sole environment.
- No `pyproject.toml`, no `setup.cfg`, no `pytest.ini`, no linter, no formatter (no black/ruff/flake8/mypy). Conventions below are derived by reading actual source files in `quickice/` and `tests/`. Match what the codebase already does — there is no tool to enforce it.

## Naming Patterns

**Files:**
- Use `snake_case.py` for all source modules: `quickice/structure_generation/ion_inserter.py`, `quickice/output/gromacs_writer.py`, `quickice/gui/main_window.py`.
- Private sub-modules in a refactored package take a leading underscore: `quickice/output/_constants.py`, `quickice/output/_shared.py`, `quickice/output/_gro_format.py`, `quickice/output/_atomtypes.py`, `quickice/output/_pbc.py`, `quickice/output/_itp.py`, `quickice/output/_guest.py`, `quickice/output/_tip4p.py`. Public re-exports live in the non-underscore facade (`gromacs_writer.py`).
- Tests: `test_*.py` (unit), `tests/e2e/<feature>/test_e2e_*.py` (true e2e), `tests/scancode/test_scancode_bugs_*.py` (scancode regression). Root-level regression tests are named by their issue/origin: `tests/test_uat_f_custom_guest_fixes.py`, `tests/test_thf_bonds_viewer_issue2.py`, `tests/test_gro_top_byte_equivalence.py`. Non-collected helpers MUST NOT start with `test_`: `tests/e2e_export_helpers.py`, `tests/e2e_chain_fixtures.py`, `tests/gui_e2e_helpers.py`, `tests/_capture_gro_top_baseline.py`, `tests/repro_*.py`.

**Functions:**
- Use `snake_case`: `generate_interface`, `write_top_file`, `lookup_phase`, `validate_temperature`, `report_progress`, `parse_gro_residue_names`, `run_quickice`.
- Private/helpers take a leading underscore: `_parse_cage_guest_args`, `_validate_hydrate_atom_counts`, `_build_custom_guest_info`, `_liquid_volume_nm3`, `_insert_custom_molecules`, `_stage_itp_files`, `_get_data_dir`, `_resolve_custom_molecule_itp_name` (`quickice/gui/export.py`).

**Classes:**
- Use `PascalCase`: `CLIPipeline`, `IceStructureGenerator`, `HydrateStructureGenerator`, `IonInserter`, `SoluteInserter`, `CustomMoleculeInserter`, `MoleculetypeRegistry`, `InterfaceStructure`, `HydrateConfig`, `Candidate`, `RankedCandidate`, `HydrateWorker`, `GROMACSExporter`, `HydratePanel`, `MainWindow`.
- Acronyms in class names stay ALL-CAPS only when the whole name is an acronym prefix: `CLIPipeline`, `GROMACSExporter`. Otherwise PascalCase (`HydrateWorker`, not `HydrateWORKER`).

**Variables:**
- Use `snake_case` for locals/attributes: `ice_atom_count`, `water_nmolecules`, `cage_guest_assignments`, `guest_residue_name`, `molecule_index`.
- Private instance attributes take a leading underscore: `self._interface_result`, `self._hydrate_result`, `self._config`, `self._output_dir`, `self._registered`. MainWindow cross-tab results follow the `_current_<tab>_result` pattern (`self._current_hydrate_result`, `self._current_interface_result`, ...).

**Types / Dataclasses:**
- Use `PascalCase`: `Candidate`, `InterfaceConfig`, `HydrateConfig`, `IonStructure`, `SoluteStructure`, `CustomMoleculeStructure`, `MoleculeIndex`, `PlacementValidationResult`, `HydrateLatticeInfo`, `CageGuestAssignment`, `GuestDescriptor`, `StagingResult` (namedtuple in `tests/e2e_export_helpers.py:39`), `ModalMocks` (dataclass in `tests/gui_e2e_helpers.py:57`).

**Constants:**
- Use `UPPER_SNAKE_CASE` at module top, with a comment citing the source/reference: `WATER_ATOMS_PER_MOLECULE` (`quickice/structure_generation/types.py:22`, annotated `: int = 4`), `WATER_VOLUME_NM3` (`types.py:39`, `: float = 0.0299`), `TIP4P_ICE_OW_SIGMA`, `TIP4P_ICE_OW_EPSILON`, `TIP4P_ICE_ALPHA`, `TIP4P_ICE_HW_CHARGE`, `TIP4P_ICE_MW_CHARGE`, `TIP4P_ICE_SETTLE_DOH`, `TIP4P_ICE_SETTLE_DHH`, `HYDRATE_LATTICES`, `GUEST_MOLECULES`, `MOLECULE_TYPE_INFO`, `AVOGADRO`, `NA_VDW_RADIUS`, `CL_VDW_RADIUS`, `NA_CHARGE`, `CL_CHARGE`, `MIN_SEPARATION`, `MAX_CSV_ROWS`, `CH4_CH_BOND_LENGTH_NM`, `ION_ATOMTYPES`, `GAFF2_ATOMTYPES`, `WATER_ATOMTYPES`, `RESERVED_NAMES`, `_ROUTER_FLAGS` (frozen set in `quickice/entry.py`). Test-side canonical sets: `CUSTOM_GUEST_LATTICES`, `INTERFACE_LATTICES`, `FILLED_ICE_SUPERCELLS` in `tests/e2e_chain_fixtures.py:71-91`, `PHASE_CONDITIONS` in `tests/conftest.py:58-65`.
- **NEVER hardcode** TIP4P-ICE parameters, `WATER_VOLUME_NM3` (the `0.0299` literal), `WATER_ATOMS_PER_MOLECULE` (the `4` literal), or `comb-rule=1`. Import the named constants from `quickice/structure_generation/types.py` or `quickice/output/_constants.py`. This is enforced by regression tests in `tests/test_tip4p_ice_lj_values.py` and `tests/scancode/test_scancode_bugs_constants.py`.

**Module logger:**
- Add `logger = logging.getLogger(__name__)` at module top (after imports) in every module that logs (38 modules do). Example: `quickice/cli/pipeline.py:19`, `quickice/output/gromacs_writer.py:24`, `quickice/structure_generation/solute_inserter.py:31`, `quickice/gui/main_window.py:26`. (A missing logger was a real bug: `tests/test_scancode_bugs_piece_logger.py` pins the `quickice/structure_generation/modes/piece.py` NameError fix.)

## Code Style

**Formatting:**
- No automated formatter. 4-space indentation. No enforced line length (lines commonly run 100–120 chars; e2e test docstrings regularly exceed).
- Prefer double quotes `"` for string literals and f-strings (types.py has ~341 `"` vs ~39 `'`). Single quotes `'` are acceptable in older code (e.g., `'slab'`, `'ch4'` in `tests/conftest.py`). Be consistent within a file.
- Use f-strings for interpolation and error messages; use `!r` for repr in error text: `raise ValueError(f"Unknown lattice type: {self.lattice_type!r}")` (`quickice/structure_generation/types.py`).

**Type hints:**
- Use modern Python 3.10+ syntax (the env is 3.14): `list[str]`, `dict[str, Any]`, `tuple[int, str]`, `X | None`, `list[tuple[int, int]] | None`. Do NOT use `typing.List`/`typing.Dict`/`typing.Optional` in new code. (Legacy `from typing import Dict, Set` survives ONLY in `quickice/structure_generation/moleculetype_registry.py:8` — do not extend that pattern.)
- Annotate function signatures, return types, and dataclass fields (constants too: `WATER_ATOMS_PER_MOLECULE: int = 4`).
- For circular-import-prone types, use `if TYPE_CHECKING:` guard (used in `quickice/output/gromacs_writer.py`, `quickice/output/custom_writer.py`, `quickice/output/solute_writer.py`, `quickice/gui/ion_panel.py`, `quickice/gui/solute_panel.py`) and `Any` as the runtime field type with an inline comment (`# MoleculetypeRegistry (avoid circular import)`).
- Do NOT use `from __future__ import annotations` — Python 3.14 evaluates annotations natively (0 occurrences in `quickice/`; the only one is the standalone script `tests/_capture_gro_top_baseline.py`).

**Linting:**
- None configured. Match surrounding style manually. Selective `# noqa: F401` on intentional re-exports (`quickice/cli/pipeline.py:17`, `quickice/output/_gro_format.py:53`) and `# noqa: E402` in test files where imports follow module-level env setup.

## Import Organization

**Order (match this in every new file):**
1. stdlib: `argparse`, `csv`, `logging`, `sys`, `importlib.util`, `pathlib.Path`, `dataclasses`, `random`, `hashlib`, `re`, `shutil`, `tempfile`.
2. third-party: `numpy`, `scipy.spatial`, `scipy.spatial.transform`, `matplotlib`, `networkx`, `PySide6.QtWidgets`/`QtCore`/`QtGui`, `vtk`, `genice2.*`.
3. local: `from quickice.structure_generation.types import ...`, `from quickice.output.gromacs_writer import ...`.
4. `TYPE_CHECKING` block (last) for circular types.

**Test-file import order:** e2e test modules follow env guards → stdlib → pytest/numpy → `from tests.conftest import gmx_skipif  # noqa: E402` → `quickice.*` imports → `tests.e2e_export_helpers` / `tests.e2e_chain_fixtures` / `tests.gui_e2e_helpers` imports (see `tests/e2e/interface/test_e2e_lattice_interface_cli.py:65-85`, `tests/e2e/test_e2e_gui_fullchain.py:50-82`).

**Path Aliases:**
- None. Always use fully-qualified `quickice.<subpackage>.<module>` imports and `from tests.<module> import ...` for test helpers (`tests/` is a package; project root on `PYTHONPATH` via `setup.sh`). No `sys.path` hacks in source. Legacy `sys.path.insert` survives only in standalone scripts `tests/_capture_gro_top_baseline.py` and `tests/repro_sii_mixed_gui_regression.py` — do not extend that pattern.

## Lazy Imports (critical convention)

- PySide6, VTK, and GenIce2 are imported INSIDE function bodies, NEVER at module top level. This keeps CLI modules importable without GUI/VTK and lets `entry.py` probe availability without crashing headless environments.
- `quickice/entry.py` uses `importlib.util.find_spec('PySide6')` to check availability without importing (`quickice/entry.py:37`). Do not replace with `import PySide6`.
- `quickice/cli/pipeline.py` imports `quickice.structure_generation.*` and `quickice.output.gromacs_writer` inside each `_run_*_step()` method. The CLI package (`quickice/cli/`) MUST NOT import PySide6/VTK.
- GUI `QThread` workers import the heavy generator inside `run()`: `quickice/gui/hydrate_worker.py`, `quickice/gui/main_window.py`.
- `quickice/structure_generation/generator.py` is the ONE exception: it imports `genice2` at module top because it IS the GenIce wrapper.
- Same rule applies to test helpers that import Qt: `tests/gui_e2e_helpers.py` imports `PySide6.QtWidgets` only inside function bodies (`patch_gui_modals`, `qapp_session`, `teardown_threads`) so `pytest --collect-only` stays cheap.

## Error Handling

**Core pipeline (`quickice/cli/pipeline.py`):**
- **NO bare `except Exception`** in `quickice/cli/pipeline.py` (verified: 0 occurrences). Catch specific exceptions: `except (OSError, ValueError)`, `except ValueError`, `except ImportError`, `except FileNotFoundError`, `except InterfaceGenerationError`, `except UnknownPhaseError`.
- Each `_run_*_step()` returns an `int` exit code (0 success, non-zero failure) and reports via `report_progress(f"... failed: ... — {e}")` + `logger.error(...)`. Do not re-raise from step methods.
- `ValueError` is used for config validation and is NOT an `OSError` — it must propagate past `except OSError` blocks. See the SEC-05 `--output` containment check at `quickice/cli/pipeline.py:164-175` (raises `ValueError` deliberately).

**Custom exceptions:**
- Define a hierarchy in `quickice/structure_generation/errors.py`: `StructureGenerationError(Exception)` (base, `errors.py:4`) → `UnsupportedPhaseError` (`errors.py:10`), `InterfaceGenerationError` (`errors.py:18`). Carry context on the exception (`InterfaceGenerationError(mode=...)`, `UnsupportedPhaseError(phase_id=...)`).
- Wrap unexpected errors with `raise ... from e`: `quickice/structure_generation/interface_builder.py`.

**Validation in dataclasses:**
- Implement `__post_init__` that raises `ValueError(...)` for invalid params. See `HydrateConfig.__post_init__`, `InterfaceConfig.__post_init__`, `SoluteConfig.__post_init__`, `IonConfig.__post_init__`, `CustomMoleculeConfig.__post_init__` (all in `quickice/structure_generation/types.py`). Error messages must state the bad value AND the valid range/convention.
- Use real `if ...: raise ValueError(...)` for assertions that must hold under `python -O`/`PYTHONOPTIMIZE=1` — do NOT use bare `assert` for runtime invariants (CRIT-04 / scancode F5: `tests/test_scancode_bugs_custom_guest_bridge_assert.py` pins the `custom_guest_bridge.py` fix where a bare `assert` guard was stripped under `-O`).

**GUI code (user-facing):**
- GUI modules MAY use broad `except Exception as e:` for safety in user-facing workflows and `QThread.run()` methods. Convert to a user-facing message via `QMessageBox` or a worker `*_error` signal. See `quickice/gui/hydrate_worker.py`, `quickice/gui/main_window.py`, `quickice/gui/export.py`. Always include `type(e).__name__` in the message: `f"Unexpected error ... ({type(e).__name__}): {e}"`.
- `quickice/main.py` uses a top-level `except Exception as e:` for the ice-only workflow, printing to stderr and returning 1. Specific exceptions (`UnknownPhaseError`, `InterfaceGenerationError`, `SystemExit`) are caught first.

**CLI argparse input validation:**
- Use `argparse.ArgumentTypeError` in `quickice/validation/validators.py` (`validators.py:7`, raised at `:25` in `validate_temperature`; same pattern in `validate_pressure`, `validate_nmolecules`). Wire these as `type=` arguments in `quickice/cli/parser.py`.

**Path/file containment (SEC-04/SEC-05):**
- Reject user-supplied paths that resolve outside the working directory. Pattern: `resolved = Path(p).resolve(); cwd = Path.cwd().resolve(); if not resolved.is_relative_to(cwd): raise ValueError(...)`. See `quickice/cli/pipeline.py:164-175` (`--output`), plus the input-path checks and the oversized-CSV guard (`pipeline.py:316`). Test-side, `make_temp_output_dir()` in `tests/e2e_export_helpers.py:640-662` mirrors the same constraint by creating dirs under `<cwd>/tmp/`.

## Logging

**Framework:** stdlib `logging`.

**Patterns:**
- `logger = logging.getLogger(__name__)` at module top.
- `logger.error("...: %s", e)` for failures, `logger.info("...: %s", val)` for chaining decisions, `logger.debug(...)` for routine tracing. Use `%`-style formatting (not f-strings) in `logger.*` calls so the format is lazy-evaluated. See `quickice/cli/pipeline.py`.
- CLI progress to the user goes to **stderr** via `report_progress()` (`quickice/cli/pipeline.py:24-30`: `print(f"[PROGRESS] {message}", file=sys.stderr)`). stdout is reserved for data/help output so it stays clean.
- GUI workers emit Qt signals (`progress_updated`, `*_error`) rather than calling `print`. See `quickice/gui/hydrate_worker.py`, `quickice/gui/main_window.py`.

## Comments

**When to Comment:**
- Cite the plan/fix/issue that motivated a non-obvious block. The codebase references plan/issue IDs inline: `# 48.3-05 (b278a9ed follow-up): ...` (`quickice/cli/itp_helpers.py:361`), `# SEC-05: Reject --output ...` (`quickice/cli/pipeline.py:164`), `# FIX #7`, `# (plan 41-07 custom branch)`, `# Pitfall 6`, `# V-17`, `# AGENTS.md`. Match this style when adding code that addresses a tracked item. Test files go further: module docstrings cite the plan ID, research doc section, and pitfall list (see `tests/e2e/interface/test_e2e_lattice_interface_cli.py:1-63`).
- Explain WHY a value/decision is what it is, especially when it encodes a physical constant or a non-obvious workaround. See the `WATER_VOLUME_NM3` derivation block in `quickice/structure_generation/types.py:24-39` and the `ION_ATOMTYPES` charge=0.0 convention in `quickice/output/_constants.py`.
- Test comment blocks that document a known-broken behavior being pinned are encouraged (`tests/test_thf_bonds_viewer_issue2.py:37` — "Heuristic limitation (documents WHY the fallback is fragile)").

**Section dividers:**
- Use `# ── Title ───────────────────────────────────────────` for subsections (`tests/conftest.py`, `tests/e2e_export_helpers.py`, `tests/test_thf_bonds_viewer_issue2.py`).
- Use `# ═══...` (heavy box-drawing) for major scenario/fixture boundaries (`tests/e2e_chain_fixtures.py:94,287,342`).
- Use `# ---------------------------------------------------------------------------` (72 dashes) for grouping blocks within a class/file.

**Docstrings (Google style):**
- Use triple-double-quoted `"""` docstrings on every module, class, and public function. Sections: `Args:`, `Returns:`, `Raises:`, `Attributes:`, `Example:` / `Usage:`, `Note:`.
- Module docstrings describe purpose AND key design decisions/lazy-import rationale. See `quickice/cli/pipeline.py:1-7`, `quickice/entry.py:1-15`.
- Test docstrings describe what is verified and why (the bug/invariant). `tests/test_thf_bonds_viewer_issue2.py:1-17` is the model: root cause → mechanism → fix summary.
- `'''` (triple-single) appears in `quickice/structure_generation/generator.py` only; `"""` is the dominant convention — use `"""`.

## Function Design

**Size:** No enforced limit. Step methods in `CLIPipeline` are ~60–160 lines; helper functions tend to be <40 lines. Prefer extracting a named helper over a deep nested block (see `_parse_cage_guest_args`, `_validate_hydrate_atom_counts` in the pipeline; `_make_cli_pipeline` / `_assert_lattice_cli_export` extracted per e2e file).

**Parameters:** Prefer keyword-rich signatures with typed parameters and defaults. Use dataclasses (`HydrateConfig`, `SoluteConfig`, `IonConfig`, `CustomMoleculeConfig`, `InterfaceConfig`) to bundle related parameters rather than long positional arg lists. Seed is always an explicit `seed: int | None = None` parameter (see `IonInserter.__init__`, `SoluteInserter.__init__`, `CustomMoleculeInserter.__init__`).

**Return Values:**
- CLI step methods return `int` exit codes (0 success, non-zero failure).
- Inserters return NEW structure objects (NEVER mutate inputs — V-17 fix). See `SoluteInserter.insert_solutes`, `IonInserter.replace_water_with_ions`, `CustomMoleculeInserter.place_random`/`place_custom`. (Known, contained exception: the ion inserter sets `structure.molecule_index` on an interface whose `molecule_index` is empty — `ion_inserter.py:259`; e2e fixtures build a fresh interface per inserter to contain it.)
- Generators return dataclasses (`Candidate`, `InterfaceStructure`, `HydrateStructure`, `IonStructure`, `SoluteStructure`, `CustomMoleculeStructure`) or `GenerationResult`.
- Writers (`write_gro_file`, `write_top_file`, etc.) return `None` and take an output path string.
- Functions that can fail at the file system level raise `FileNotFoundError` / `OSError` / `ValueError` rather than returning a sentinel.

## Module Design

**Exports:**
- Each package `__init__.py` re-exports the public API and defines `__all__`. See `quickice/structure_generation/__init__.py`. Import from the package in new code: `from quickice.structure_generation import generate_interface, InterfaceConfig` rather than reaching into submodules, UNLESS the submodule is the only source (e.g., `from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry`).

**Facade / re-export pattern:**
- `quickice/output/gromacs_writer.py` is a facade: it re-exports constants from `quickice/output/_shared.py` (which aggregates `_constants`, `_atomtypes`, `_pbc`, `_itp`, `_guest`, `_tip4p`) and writer functions from `quickice/output/{ice,interface,ion,custom,solute,multi_molecule}_writer.py`. The public import path `from quickice.output.gromacs_writer import X` is stable. When adding a new writer or constant, add it to the relevant sub-module AND re-export it through `gromacs_writer.py`.
- Use `# noqa: F401` on re-exports that are intentionally unused in the facade module (`quickice/cli/pipeline.py:17` re-exports `_build_custom_guest_info` for backward compat).

**Barrel files:**
- `quickice/structure_generation/__init__.py` is a barrel. Keep `__all__` in sync with the re-exports.

**Constants location:**
- Physical constants for the output layer live in `quickice/output/_constants.py`. Structure-generation constants live in `quickice/structure_generation/types.py`. Do not duplicate — import from the canonical location (enforced by `tests/scancode/test_scancode_bugs_constants.py`, which asserts `TIP4P_ICE_ALPHA` is defined exactly once).

**Moleculetype naming:**
- Hydrate guests use the `_H` suffix, liquid solutes use the `_L` suffix (5-char GRO limit). Managed by `MoleculetypeRegistry` in `quickice/structure_generation/moleculetype_registry.py`. NEVER hardcode moleculetype names — register them. The same convention extends to custom-molecule ITP collision renames: a colliding custom ITP is renamed to `{stem}_L.itp` by `_resolve_custom_molecule_itp_name` in `quickice/gui/export.py` (tested in `tests/test_uat_f_custom_guest_fixes.py`).

**Path handling:**
- Use `pathlib.Path` everywhere, not raw `str`. Convert at boundaries with `str(path)` only when calling writer APIs. `.resolve()` for canonical paths, `.is_relative_to()` for containment, `.exists()` / `.suffix.lower()` for validation. Test data paths are `__file__`-anchored absolute paths (`tests/e2e_export_helpers.py:45-47`) or `quickice.__file__`-anchored (`tests/e2e/export_validation/test_e2e_gmx_validation.py:93`) so they are CWD-independent.

**Test helper modules (plain modules, never conftest in `tests/e2e/`):**
- Shared fixtures extracted from near-copy siblings go into a plain module (`tests/e2e_chain_fixtures.py`) imported into test modules' namespaces — pytest resolves imported fixtures normally and preserves their declared scope. The INFRA collision rule forbids new conftest.py files under `tests/e2e/` (an e2e conftest must not shadow `test_output` fixture names). Divergent same-name sibling fixtures are RENAMED apart, never merged.

---

*Convention analysis: 2026-09-12*
