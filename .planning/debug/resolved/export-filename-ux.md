---
status: resolved
trigger: "Hydrate export uses a bare filename as QFileDialog default, causing the user to accidentally overwrite an existing ion-export file with hydrate content. Fix: make default_name an absolute path so the dialog always pre-selects the correct filename."
created: 2026-07-06T00:00:00Z
updated: 2026-07-06T00:01:00Z
---

## Current Focus

hypothesis: (confirmed) QFileDialog.getSaveFileName is given a BARE filename (no directory) as its default. Qt opens in an unpredictable dir, exposing unrelated files for accidental overwrite.
test: Convert all 9 bare defaults to absolute paths via a shared last-export-dir helper; run full export test suite.
expecting: All tests pass; default paths are now absolute.
next_action: DONE — fix applied and verified. Archive session.

## Symptoms

expected: Ctrl+S in Hydrate tab opens QFileDialog with the default filename clearly pre-selected as `hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro` in a predictable directory, so the user cannot accidentally overwrite an existing file with a different name (e.g. an ion export `ions_34na_34cl_with_7ch4.gro`).

actual: hydrate_export.py:115 passes a BARE filename `default_name = f"hydrate_..."` to QFileDialog.getSaveFileName. With a bare filename Qt uses CWD/last-used dir. User navigated to tmp/mixed/ (containing a prior ion export), clicked the existing ion file, and hydrate content was written to the ion filename — misleading filename, correct content.

errors: No runtime error. Export "succeeds" but the filename is wrong. Content verified 100% correct (.gro header, .top [system], [molecules], ITPs all correct).

reproduction:
1. Export an ion structure to a dir (e.g. tmp/mixed/) → creates `ions_34na_34cl_with_7ch4.gro`
2. Hydrate tab → generate mixed sII hydrate (CH4+THF)
3. Ctrl+S → QFileDialog opens with bare default `hydrate_sII_ch4_1x1x1.gro`
4. Navigate to tmp/mixed/ → see existing `ions_...gro` in file list
5. Click it to overwrite → hydrate content written to `ions_...gro`
6. Filename says "ions" but content is a hydrate — misleading

started: Pre-existing UX issue (bare-filename pattern always present). Phase 42 mixed occupancy made it more visible.

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-07-06T00:00:00Z
  checked: quickice/gui/hydrate_export.py:115-124
  found: `default_name = f"hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro"` (bare, no dir) passed as 3rd arg to QFileDialog.getSaveFileName at line 118-124.
  implication: Confirms root cause — bare filename lets Qt pick an unpredictable starting directory.

- timestamp: 2026-07-06T00:00:00Z
  checked: quickice/gui/export.py — all QFileDialog.getSaveFileName default args
  found: 9 sites total, ALL bare filenames:
    - export.py:100  SoluteGROMACSExporter → `solute_{type}_{n}molecules.gro`
    - export.py:214  CustomMoleculeGROMACSExporter → `custom_system_{name}_{n}molecules.gro`
    - export.py:317/319 IonGROMACSExporter → `ions_{na}na_{cl}cl[_with_...].gro`
    - export.py:452  PDBExporter → `{phase}_{T}K_{P}MPa_c{rank}.pdb`
    - export.py:527  DiagramExporter → `"phase_diagram.png"`
    - export.py:617/619 ViewportExporter → `ice_structure[_{viewport}].png`
    - export.py:723  GROMACSExporter (ice) → `{phase}_{T}K_{P}MPa_c{rank}.gro`
    - export.py:860  InterfaceGROMACSExporter → `interface_{mode}.gro`
    - hydrate_export.py:115 HydrateGROMACSExporter → `hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro`
  implication: Same UX bug exists in every export path. Fix should be consistent across all.

- timestamp: 2026-07-06T00:00:00Z
  checked: tests/test_output/conftest.py mock_save_dialog / mock_hydrate_save_dialog / mock_cancel_dialog fixtures
  found: All mock QFileDialog.getSaveFileName with `return_value=(save_path, filter)` — return_value ignores the default_name arg. grep for assert_called/call_args/call_count near getSaveFileName → none.
  implication: Changing the default_name argument is test-safe — mocks return fixed paths regardless of the default arg.

- timestamp: 2026-07-06T00:00:00Z
  checked: baseline tests (test_e2e_mixed_cage_occupancy.py, test_output/test_gromacs_export_hydrate.py, test_hydrate_panel.py)
  found: 24 passed in 1.70s (QT_QPA_PLATFORM=offscreen).
  implication: Green baseline before the fix.

- timestamp: 2026-07-06T00:00:30Z
  checked: First post-fix test run of the baseline set.
  found: REGRESSION — test_export_creates_all_files failed with AttributeError: 'NoneType' object has no attribute '_last_export_dir'. Unit tests construct exporters with parent_widget=None; _remember_export_dir tried to set an attr on None.
  implication: Helper must guard parent is None. Fix: `if filepath and parent is not None`.

- timestamp: 2026-07-06T00:00:45Z
  checked: Helper unit sanity (default->home, remember->same dir, cancel->unchanged) + import cleanliness (no circular import between export.py and hydrate_export.py).
  found: All assertions pass; modules import cleanly.
  implication: Helper logic correct; cross-module import safe.

- timestamp: 2026-07-06T00:01:00Z
  checked: Full export regression sweep — tests/test_output/ (all) + tests/test_e2e_{ion,solute,custom,chain_export_1,chain_export_2,ice_interface}_export.py + tests/test_e2e_mixed_cage_occupancy.py + tests/test_hydrate_panel.py. QT_QPA_PLATFORM=offscreen.
  found: 228 passed, 0 failed, 30 warnings (only spglib DeprecationWarning + iapws UserWarning, pre-existing/unrelated).
  implication: No regression across the entire export test surface. Fix verified.

## Resolution

root_cause: QFileDialog.getSaveFileName is given a bare filename (no directory) as its default in all 9 export paths. Qt interprets a bare filename relative to CWD/last-used-dir, so the dialog opens in an unpredictable directory where unrelated files may be visible and clickable for overwrite.
fix: Added shared last-export-dir helpers in quickice/gui/export.py:
  - _build_default_path(parent, filename) -> str: returns str(last_export_dir / filename), defaulting to Path.home() when no dir remembered yet. Guarantees an ABSOLUTE default so QFileDialog opens in a predictable dir with the correct filename pre-selected.
  - _remember_export_dir(parent, filepath): stores Path(filepath).parent on parent._last_export_dir after each successful selection (no-op on cancel or when parent is None).
  Initialized self._last_export_dir = Path.home() on MainWindow (shared across all exporters since they share self.parent = MainWindow). Applied to ALL 9 export paths for consistency: hydrate (hydrate_export.py), solute, custom, ion, PDB, diagram, viewport, ice GROMACS, interface (export.py). Export CONTENT unchanged — only the dialog default path.
verification:
  - Helper unit sanity check: default -> Path.home()/filename; after remembering /tmp/mixed/...gro, next default -> /tmp/mixed/filename; cancel (empty) -> dir unchanged. PASS.
  - Initial run surfaced a regression: unit tests construct exporters with parent_widget=None, and _remember_export_dir tried to set an attr on None (AttributeError). Fixed by guarding `if filepath and parent is not None`.
  - Baseline (the 3 required files): 24 passed.
  - Full export regression sweep (tests/test_output/ + e2e ion/solute/custom/chain/ice-interface/mixed-cage + hydrate_panel): 228 passed, 0 failed.
  - No test inspects getSaveFileName call args (all use return_value mocks), so changing the default arg is safe.
files_changed:
  - quickice/gui/export.py: added _build_default_path + _remember_export_dir helpers; converted 8 bare defaults to absolute paths; remember dir after each selection.
  - quickice/gui/hydrate_export.py: import helpers; convert hydrate default to absolute path; remember dir after selection.
  - quickice/gui/main_window.py: add `from pathlib import Path`; initialize self._last_export_dir = Path.home() in __init__.
