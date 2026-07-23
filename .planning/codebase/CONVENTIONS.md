# Coding Conventions

**Analysis Date:** 2026-07-23

## Languages & Runtime

- **Python 3.14** (`python=3.14.3` in `environment.yml`). Conda env `quickice` is the sole environment.
- No `pyproject.toml`, no `setup.cfg`, no `pytest.ini`, no linter, no formatter (no black/ruff/flake8/mypy). Conventions below are derived by reading actual source files in `quickice/`. Match what the codebase already does — there is no tool to enforce it.

## Naming Patterns

**Files:**
- Use `snake_case.py` for all source modules: `quickice/structure_generation/ion_inserter.py`, `quickice/output/gromacs_writer.py`, `quickice/gui/main_window.py`.
- Private sub-modules in a refactored package take a leading underscore: `quickice/output/_constants.py`, `quickice/output/_shared.py`, `quickice/output/_gro_format.py`, `quickice/output/_atomtypes.py`, `quickice/output/_pbc.py`, `quickice/output/_itp.py`, `quickice/output/_guest.py`, `quickice/output/_tip4p.py`. Public re-exports live in the non-underscore facade (`gromacs_writer.py`).
- Tests: `test_*.py` (unit), `test_e2e_*.py` (end-to-end), `test_scancode_bugs_*.py` (regression, under `tests/scancode/`). Non-collected helpers MUST NOT start with `test_`: `tests/e2e_export_helpers.py`, `tests/_capture_gro_top_baseline.py`.

**Functions:**
- Use `snake_case`: `generate_interface`, `write_top_file`, `lookup_phase`, `validate_temperature`, `report_progress`, `parse_gro_residue_names`, `run_quickice`.
- Private/helpers take a leading underscore: `_parse_cage_guest_args`, `_validate_hydrate_atom_counts`, `_build_custom_guest_info`, `_liquid_volume_nm3`, `_insert_custom_molecules`, `_stage_itp_files`, `_get_data_dir`.

**Classes:**
- Use `PascalCase`: `CLIPipeline`, `IceStructureGenerator`, `HydrateStructureGenerator`, `IonInserter`, `SoluteInserter`, `CustomMoleculeInserter`, `MoleculetypeRegistry`, `InterfaceStructure`, `HydrateConfig`, `Candidate`, `RankedCandidate`, `HydrateWorker`, `GROMACSExporter`, `HydratePanel`, `MainWindow`.
- Acronyms in class names stay ALL-CAPS only when the whole name is an acronym prefix: `CLIPipeline`, `GROMACSExporter`, `GROMACSExporter` subclasses. Otherwise PascalCase (`HydrateWorker`, not `HydrateWORKER`).

**Variables:**
- Use `snake_case` for locals/attributes: `ice_atom_count`, `water_nmolecules`, `cage_guest_assignments`, `guest_residue_name`, `molecule_index`.
- Private instance attributes take a leading underscore: `self._interface_result`, `self._hydrate_result`, `self._config`, `self._output_dir`, `self._registered`.

**Types / Dataclasses:**
- Use `PascalCase`: `Candidate`, `InterfaceConfig`, `HydrateConfig`, `IonStructure`, `SoluteStructure`, `CustomMoleculeStructure`, `MoleculeIndex`, `PlacementValidationResult`, `HydrateLatticeInfo`, `CageGuestAssignment`, `GuestDescriptor`, `StagingResult` (namedtuple in `tests/e2e_export_helpers.py`).

**Constants:**
- Use `UPPER_SNAKE_CASE` at module top, with a comment citing the source/reference: `WATER_ATOMS_PER_MOLECULE`, `WATER_VOLUME_NM3`, `TIP4P_ICE_OW_SIGMA`, `TIP4P_ICE_OW_EPSILON`, `TIP4P_ICE_ALPHA`, `TIP4P_ICE_HW_CHARGE`, `TIP4P_ICE_MW_CHARGE`, `TIP4P_ICE_SETTLE_DOH`, `TIP4P_ICE_SETTLE_DHH`, `HYDRATE_LATTICES`, `GUEST_MOLECULES`, `MOLECULE_TYPE_INFO`, `AVOGADRO`, `NA_VDW_RADIUS`, `CL_VDW_RADIUS`, `NA_CHARGE`, `CL_CHARGE`, `MIN_SEPARATION`, `MAX_CSV_ROWS`, `CH4_CH_BOND_LENGTH_NM`, `ION_ATOMTYPES`, `GAFF2_ATOMTYPES`, `WATER_ATOMTYPES`, `RESERVED_NAMES`, `_ROUTER_FLAGS` (frozen set in `quickice/entry.py`).
- **NEVER hardcode** TIP4P-ICE parameters, `WATER_VOLUME_NM3` (the `0.0299` literal), `WATER_ATOMS_PER_MOLECULE` (the `4` literal), or `comb-rule=1`. Import the named constants from `quickice/structure_generation/types.py` or `quickice/output/_constants.py`. This is enforced by regression tests in `tests/test_tip4p_ice_lj_values.py` and `tests/scancode/test_scancode_bugs_constants.py`.

**Module logger:**
- Add `logger = logging.getLogger(__name__)` at module top (after imports) in every module that logs. Example: `quickice/cli/pipeline.py:19`, `quickice/output/gromacs_writer.py:24`, `quickice/structure_generation/solute_inserter.py:31`, `quickice/gui/main_window.py:26`.

## Code Style

**Formatting:**
- No automated formatter. 4-space indentation. No enforced line length (lines commonly run 100–120 chars; docstrings/comments may exceed).
- Prefer double quotes `"` for string literals and f-strings. Single quotes `'` are acceptable and appear in older code (e.g., `'slab'`, `'ch4'` in `tests/conftest.py`). Be consistent within a file.
- Use f-strings for interpolation and error messages; use `!r` for repr in error text: `raise ValueError(f"Unknown lattice type: {self.lattice_type!r}")` (`quickice/structure_generation/types.py:588`).

**Type hints:**
- Use modern Python 3.10+ syntax (the env is 3.14): `list[str]`, `dict[str, Any]`, `tuple[int, str, str]`, `X | None`, `list[tuple[int, int]] | None`. Do NOT use `typing.List`/`typing.Dict`/`typing.Optional` (legacy `typing.Dict`/`typing.Set` survive in `quickice/structure_generation/moleculetype_registry.py` — do not extend that pattern; new code uses builtin generics).
- Annotate function signatures and return types. Annotate dataclass fields.
- For circular-import-prone types, use `if TYPE_CHECKING:` guard (see `quickice/output/gromacs_writer.py:21-22`) and `Any` as the runtime field type with an inline comment (`# MoleculetypeRegistry (avoid circular import)`, `quickice/structure_generation/types.py:430`).
- Do NOT use `from __future__ import annotations` — Python 3.14 evaluates annotations natively.

**Linting:**
- None configured. Match surrounding style manually.

## Import Organization

**Order (match this in every new file):**
1. stdlib: `argparse`, `csv`, `logging`, `sys`, `importlib.util`, `pathlib.Path`, `dataclasses`, `random`, `hashlib`, `re`, `shutil`, `tempfile`.
2. third-party: `numpy`, `scipy.spatial`, `scipy.spatial.transform`, `matplotlib`, `networkx`, `PySide6.QtWidgets`/`QtCore`/`QtGui`, `vtk`, `genice2.*`.
3. local: `from quickice.structure_generation.types import ...`, `from quickice.output.gromacs_writer import ...`.
4. `TYPE_CHECKING` block (last) for circular types.

**Path Aliases:**
- None. Always use fully-qualified `quickice.<subpackage>.<module>` imports. No `sys.path` hacks in source (tests do use `sys.path.insert(0, str(Path(__file__).parent))` for helper imports — see `tests/test_pbc_wrapping.py:21`).

## Lazy Imports (critical convention)

- PySide6, VTK, and GenIce2 are imported INSIDE function bodies, NEVER at module top level. This keeps CLI modules importable without GUI/VTK and lets `entry.py` probe availability without crashing headless environments.
- `quickice/entry.py` uses `importlib.util.find_spec('PySide6')` to check availability without importing (`quickice/entry.py:37`). Do not replace with `import PySide6`.
- `quickice/cli/pipeline.py` imports `quickice.structure_generation.*` and `quickice.output.gromacs_writer` inside each `_run_*_step()` method (`quickice/cli/pipeline.py:347-348, 447-450, 498-502, 644-645, 725-726, 870-882`). The CLI package (`quickice/cli/`) MUST NOT import PySide6/VTK.
- GUI `QThread` workers import the heavy generator inside `run()`: `quickice/gui/hydrate_worker.py:65` (`from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator`), `quickice/gui/main_window.py:97` (`from quickice.structure_generation.ion_inserter import insert_ions`).
- `quickice/structure_generation/generator.py` is the ONE exception: it imports `genice2` at module top because it IS the GenIce wrapper.

## Error Handling

**Core pipeline (`quickice/cli/pipeline.py`):**
- **NO bare `except Exception`** in `quickice/cli/pipeline.py`. Catch specific exceptions: `except (OSError, ValueError)`, `except ValueError`, `except ImportError`, `except FileNotFoundError`, `except InterfaceGenerationError`, `except UnknownPhaseError`. (Verified: grep finds 0 `except Exception` in `pipeline.py`.)
- Each `_run_*_step()` returns an `int` exit code (0 success, non-zero failure) and reports via `report_progress(f"... failed: ... — {e}")` + `logger.error(...)`. Do not re-raise from step methods.
- `ValueError` is used for config validation and is NOT an `OSError` — it must propagate past `except OSError` blocks. See `quickice/cli/pipeline.py:170-175` (SEC-05 `--output` containment check raises `ValueError` deliberately).

**Custom exceptions:**
- Define a hierarchy in `quickice/structure_generation/errors.py`: `StructureGenerationError(Exception)` (base) → `UnsupportedPhaseError`, `InterfaceGenerationError`. Carry context on the exception (`InterfaceGenerationError(mode=...)`, `UnsupportedPhaseError(phase_id=...)`).
- Wrap unexpected errors with `raise ... from e`: `quickice/structure_generation/interface_builder.py:370-375`.

**Validation in dataclasses:**
- Implement `__post_init__` that `raise ValueError(...)` for invalid params. See `HydrateConfig.__post_init__` (`quickice/structure_generation/types.py:575`), `InterfaceConfig.__post_init__` (`types.py:308`), `SoluteConfig.__post_init__` (`types.py:908`), `IonConfig.__post_init__` (`types.py:832`), `CustomMoleculeConfig.__post_init__` (`types.py:987`). Error messages must state the bad value AND the valid range/convention.
- Use real `if ...: raise ValueError(...)` for assertions that must hold under `python -O`/`PYTHONOPTIMIZE=1` — do NOT use `assert` for runtime invariants (see `_validate_hydrate_atom_counts` in `quickice/cli/pipeline.py:33-56`, the CRIT-04 fix).

**GUI code (user-facing):**
- GUI modules MAY use broad `except Exception as e:` for safety in user-facing workflows and `QThread.run()` methods. Convert to a user-facing message via `QMessageBox` or a worker `*_error` signal. See `quickice/gui/hydrate_worker.py:110-114`, `quickice/gui/main_window.py:114-119`, `quickice/gui/export.py` (8 sites), `quickice/gui/main_window.py:1240,1318,1413,1516,1566`. Always include `type(e).__name__` in the message: `f"Unexpected error ... ({type(e).__name__}): {e}"`.
- `quickice/main.py` uses a top-level `except Exception as e:` for the ice-only workflow (`quickice/main.py:193`), printing to stderr and returning 1. Specific exceptions (`UnknownPhaseError`, `InterfaceGenerationError`, `SystemExit`) are caught first.

**CLI argparse input validation:**
- Use `argparse.ArgumentTypeError` in `quickice/validation/validators.py` (`validate_temperature`, `validate_pressure`, `validate_nmolecules`). Wire these as `type=` arguments in `quickice/cli/parser.py`.

**Path/file containment (SEC-04/SEC-05):**
- Reject user-supplied paths that resolve outside the working directory. Pattern: `resolved = Path(p).resolve(); cwd = Path.cwd().resolve(); if not resolved.is_relative_to(cwd): raise ValueError(...)`. See `quickice/cli/pipeline.py:170-175, 281-287, 533-547`.

## Logging

**Framework:** stdlib `logging`.

**Patterns:**
- `logger = logging.getLogger(__name__)` at module top.
- `logger.error("...: %s", e)` for failures, `logger.info("...: %s", val)` for chaining decisions, `logger.debug(...)` for routine tracing. Use `%`-style formatting (not f-strings) in `logger.*` calls so the format is lazy-evaluated. See `quickice/cli/pipeline.py:179, 351, 661-664, 744-752`.
- CLI progress to the user goes to **stderr** via `report_progress()` (`quickice/cli/pipeline.py:24-30`: `print(f"[PROGRESS] {message}", file=sys.stderr)`). stdout is reserved for data/help output so it stays clean.
- GUI workers emit Qt signals (`progress_updated`, `*_error`) rather than calling `print`. See `quickice/gui/hydrate_worker.py:62, 95-96`, `quickice/gui/main_window.py:94-119`.

## Comments

**When to Comment:**
- Cite the plan/fix/issue that motivated a non-obvious block. The codebase references plan IDs inline: `# Phase 42 mixed cage occupancy`, `# FIX #7`, `# FIX #9: hydrate between interface and ice`, `# CRIT-04`, `# SEC-04`, `# SEC-05`, `# (plan 41-07 custom branch)`, `# (44.1)`, `# Pitfall 6`, `# AGENTS.md`. Match this style when adding code that addresses a tracked item.
- Explain WHY a value/decision is what it is, especially when it encodes a physical constant or a non-obvious workaround. See the `WATER_VOLUME_NM3` derivation block in `quickice/structure_generation/types.py:24-39` and the `ION_ATOMTYPES` charge=0.0 convention in `quickice/output/_constants.py:62-70`.

**Section dividers:**
- Use `# ── Title ───────────────────────────────────────────` for subsections (see `tests/conftest.py`, `tests/e2e_export_helpers.py`).
- Use `# ═══...` (heavy box-drawing) for major scenario boundaries in test files (see `tests/test_e2e_ice_interface_export.py:50,156,236`).
- Use `# ---------------------------------------------------------------------------` (72 dashes) for grouping blocks within a class/file.

**JSDoc/TSDoc → Python docstrings:**
- Use Google-style triple-double-quoted docstrings on every module, class, and public function. Sections: `Args:`, `Returns:`, `Raises:`, `Attributes:`, `Example:` / `Usage:`, `Note:`. See `quickice/structure_generation/types.py:62-77` (`MoleculeIndex`), `quickice/cli/pipeline.py:154-160` (`execute`), `quickice/gui/hydrate_worker.py:15-33`.
- Module docstrings describe purpose AND key design decisions/lazy-import rationale. See `quickice/cli/pipeline.py:1-7`, `quickice/entry.py:1-15`, `quickice/structure_generation/types.py:1`.
- Test docstrings describe what is being verified and why (the bug/invariant). See `tests/test_tip4p_ice_lj_values.py:1-11`, `tests/scancode/test_scancode_bugs_constants.py:1-24`.
- `'''` (triple-single) appears in `quickice/structure_generation/generator.py` only; `"""` is the dominant convention — use `"""`.

## Function Design

**Size:** No enforced limit. Step methods in `CLIPipeline` are ~60–160 lines; helper functions tend to be <40 lines. Prefer extracting a named helper over a deep nested block (see `_parse_cage_guest_args`, `_validate_hydrate_atom_counts`, `_parse_positions_csv` extracted from the pipeline).

**Parameters:** Prefer keyword-rich signatures with typed parameters and defaults. Use dataclasses (`HydrateConfig`, `SoluteConfig`, `IonConfig`, `CustomMoleculeConfig`, `InterfaceConfig`) to bundle related parameters rather than long positional arg lists. Seed is always an explicit `seed: int | None = None` parameter (see `IonInserter.__init__`, `SoluteInserter.__init__`).

**Return Values:**
- CLI step methods return `int` exit codes (0 success, non-zero failure).
- Inserters return NEW structure objects (NEVER mutate inputs — V-17 fix). See `SoluteInserter.insert_solutes`, `IonInserter.replace_water_with_ions`, `CustomMoleculeInserter.place_random`/`place_custom`.
- Generators return dataclasses (`Candidate`, `InterfaceStructure`, `HydrateStructure`, `IonStructure`, `SoluteStructure`, `CustomMoleculeStructure`) or `GenerationResult`.
- Writers (`write_gro_file`, `write_top_file`, etc.) return `None` and take an output path string.
- Functions that can fail at the file system level raise `FileNotFoundError` / `OSError` / `ValueError` rather than returning a sentinel.

## Module Design

**Exports:**
- Each package `__init__.py` re-exports the public API and defines `__all__`. See `quickice/structure_generation/__init__.py:62-112`. Import from the package in new code: `from quickice.structure_generation import generate_interface, InterfaceConfig` rather than reaching into submodules, UNLESS the submodule is the only source (e.g., `from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry`).

**Facade / re-export pattern:**
- `quickice/output/gromacs_writer.py` is a facade: it re-exports constants from `quickice/output/_shared.py` (which aggregates `_constants`, `_atomtypes`, `_pbc`, `_itp`, `_guest`, `_tip4p`) and writer functions from `quickice/output/{ice,interface,ion,custom,solute,multi_molecule}_writer.py`. The public import path `from quickice.output.gromacs_writer import X` is stable; 67 caller sites depend on it. When adding a new writer or constant, add it to the relevant sub-module AND re-export it through `gromacs_writer.py`.
- Use `# noqa: F401` on re-exports that are intentionally unused in the facade module (`quickice/cli/pipeline.py:17`).

**Barrel files:**
- `quickice/structure_generation/__init__.py` is a barrel. Keep `__all__` in sync with the re-exports.

**Constants location:**
- Physical constants for the output layer live in `quickice/output/_constants.py`. Structure-generation constants live in `quickice/structure_generation/types.py`. Do not duplicate — import from the canonical location (enforced by `test_scancode_bugs_constants.py` which asserts `TIP4P_ICE_ALPHA` is defined exactly once).

**Moleculetype naming:**
- Hydrate guests use the `_H` suffix, liquid solutes use the `_L` suffix (5-char GRO limit). Managed by `MoleculetypeRegistry` in `quickice/structure_generation/moleculetype_registry.py`. NEVER hardcode moleculetype names — register them.

**Path handling:**
- Use `pathlib.Path` everywhere, not raw `str`. Convert at boundaries with `str(path)` only when calling writer APIs. `.resolve()` for canonical paths, `.is_relative_to()` for containment, `.exists()` / `.suffix.lower()` for validation.

---

*Convention analysis: 2026-07-23*
