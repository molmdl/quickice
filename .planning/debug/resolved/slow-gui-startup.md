---
status: resolved
trigger: "GUI startup takes very long; intrinsic to app startup path, not just X-forwarding. Long-standing, present in older versions."
created: 2026-09-12T00:00:00
updated: 2026-09-12T00:00:00
---

## Current Focus

RESOLVED. Root cause confirmed with measurements, fix committed on
debug/slow-gui-startup (7 atomic commits, tip d3409ed6), verified.

## Symptoms

expected: GUI window appears quickly (seconds) after launching
actual: GUI startup takes a very long time ("very long" — unquantified yet)
errors: none — slow, not crashing
reproduction: launch GUI via quickice/entry.py::main() GUI branch
started: long-standing, present in older versions — NOT a recent regression

## Eliminated

- hypothesis: X-forwarding / environment is the main cause
  evidence: offscreen headless harness (no X-forwarding) reproduces 4.15s cold / 1.5s warm startup with 89% spent in module imports; fix reduces to 0.33s same environment
  timestamp: 2026-09-12
- hypothesis: blocking work (subprocess gmx calls, QSettings, file I/O) between start and show
  evidence: importtime profile shows ~100% of cost inside module imports (vtkmodules/scipy/matplotlib/genice2/iapws); no subprocess in MainWindow path
  timestamp: 2026-09-12

## Evidence

- timestamp: 2026-09-12 baseline
  checked: timing harness (QT_QPA_PLATFORM=offscreen DISPLAY=localhost:11.0, process body start → MainWindow.show)
  found: cold run 4.15s total (pyside 0.08s, gui module imports 3.68s, app+window 0.38s); warm runs 1.62s / 1.49s (gui_imports 1.32s / 1.21s). GUI MODULE IMPORTS DOMINATE (~89%).
  implication: startup cost is import-time, not widget construction or Qt init; cold-cache amplifies ~2.6x

- timestamp: 2026-09-12 importtime
  checked: python -X importtime -c "import quickice.gui.main_window" (warm, offscreen)
  found: main_window = 1.42s. Chain: gui.view 837ms → gui.vtk_utils 833ms → vtkmodules.all 320ms + scipy.spatial 251ms + structure_generation pkg init 262ms (genice2.genice 140ms incl. networkx 130ms; interface_builder→modes.slab→water_density→iapws 104ms). Second chain: phase_diagram_widget 354ms (matplotlib backend_qtagg 176ms + figure 131ms). export.py imports matplotlib+vtkmodules at top (cheap then only because already loaded).
  implication: three eager chains: (1) view→vtk_utils, (2) phase_diagram_widget→matplotlib, (3) structure_generation pkg __init__→genice2/iapws

- timestamp: 2026-09-12 static analysis
  checked: top-level imports of all quickice/gui modules + key core modules
  found:
    * ROOT CAUSE CANDIDATE: quickice/gui/vtk_utils.py imports `vtkmodules.all` + `scipy.spatial.cKDTree` + `structure_generation.types` at module top (lines 19-31). The 6 viewer modules + view.py do `from quickice.gui.vtk_utils import is_vtk_available` at top BEFORE their `if is_vtk_available():` guards → the guard is worthless; VTK/scipy/genice2 chain loads eagerly at startup even when VTK is unusable (headless/SSH). Docstring of vtk_utils even admits it.
    * hydrate_viewer/ion_viewer/solute_viewer/custom_molecule_viewer import their renderers (which import vtkmodules.all top-level) UNCONDITIONALLY at module top, outside the guard.
    * structure_generation/__init__.py eagerly imports generator (→genice2+networkx), interface_builder (→modes.slab→water_density→iapws), ion_inserter, overlap_resolver (→scipy). Any `import quickice.structure_generation.types` triggers the whole chain (~262ms).
    * phase_diagram_widget.py imports matplotlib+shapely top-level; PhaseDiagramPanel instantiated in MainWindow.__init__ (line 242) → ~350ms at startup even though its tab is not visible initially.
    * export.py imports matplotlib.figure + vtkmodules(vtkWindowToImageFilter etc.) top-level; used only as type annotation / inside capture_viewport → easy to lazify; but main_window instantiates 8 exporters in __init__.
    * main_window.py line 41: `from quickice.structure_generation.ion_inserter import IonInserter, insert_ions` — DEAD import (insert_ions imported lazily inside worker.run() already, IonInserter only mentioned in docstring) → pulls scipy at startup for nothing.
    * ion_inserter/solute_inserter/custom_molecule_inserter/overlap_resolver import scipy.spatial top-level; imported by panels at top (ion_panel, solute_panel, custom_molecule_panel).
    * ion_panel/solute_panel/custom_molecule_panel import their inserters at top level.
  implication: fix = restore the intended lazy-import design: (A) vtk_utils lazy heavy imports, (B) structure_generation/__init__ → PEP 562 lazy re-export, (C) inserter scipy imports lazy, (D) export.py lazy matplotlib/vtk, (E) phase_diagram matplotlib deferred (panel build lazily), (F) main_window remove dead ion_inserter import + lazify renderer imports if needed

- timestamp: 2026-09-12 after fixes
  checked: same harness, same env, worktree cwd (baseline had been measured from main-repo cwd — same commit, so baseline remains valid; verified worktree imports via sys.path)
  found: gui_imports 1.29s → 0.15s; app_and_window 0.19s → 0.10s; total_to_show 1.57s(warm) → 0.330-0.344s (4 runs, stable). Cold baseline was 4.15s → expect ~0.5s (cold cache multiplies import work).
  found: assert-clean run: importing quickice.gui.main_window leaves vtkmodules/scipy/matplotlib/genice2/networkx/iapws/shapely ALL absent from sys.modules. Forced-VTK path (QUICKICE_FORCE_VTK=true, simulating local desktop with VTK): main_window import = 0.52s, only vtkmodules (0.28s via dual_viewer) remains — legitimate, tab-0 viewer needs VTK.
  implication: root cause fixed; remaining import cost is numpy+PySide6 (irreducible)

## Resolution

root_cause: The AGENTS.md lazy-import design was broken across the GUI import chain.
  (1) quickice/gui/vtk_utils.py — the module hosting is_vtk_available(), imported at
  top-level by all 6 viewers BEFORE their availability guards — itself imported
  vtkmodules.all + scipy.spatial + structure_generation.types eagerly, defeating every guard.
  (2) structure_generation/__init__.py eagerly pulled genice2+networkx, iapws (via
  interface_builder→modes.slab→water_density), and scipy (via inserters) whenever ANY
  submodule was imported. (3) gui/__init__.py eagerly imported ion_renderer (vtkmodules).
  (4) export.py + output/phase_diagram.py + phase_diagram_widget.py imported matplotlib at top;
  PhaseDiagramPanel (tab 0) built the matplotlib canvas in MainWindow.__init__.
  (5) viewers imported their renderer modules (vtkmodules) unconditionally outside the guards.
  (6) ranking/scorer.py + output/validator.py pulled scipy.spatial at top level.
  (7) main_window.py had dead top-level imports (ion_inserter→scipy; render_hydrate_structure, render_ion_structure).
fix: Restored lazy imports: vtk_utils heavy imports moved inside functions; structure_generation/__init__
  and gui/__init__ converted to PEP 562 lazy __getattr__ re-exports; scipy imports in ion/solute/
  custom_molecule inserters, overlap_resolver, scorer, validator lazy via PEP 562 module __getattr__;
  export.py + output/phase_diagram.py matplotlib/vtk moved into methods; matplotlib/shapely classes
  split into new quickice/gui/phase_diagram_canvas.py with PhaseDiagramPanel building the canvas
  after window show (QTimer.singleShot(0)) or on first access; viewers lazily import renderers
  inside render methods; main_window dead imports removed, create_solute_actor import moved into handler.
verification:
  - Timing harness (QT_QPA_PLATFORM=offscreen, DISPLAY=localhost:11.0, process body → MainWindow.show):
    BEFORE 1.57s warm / 4.15s cold-first-run; AFTER 0.328–0.344s (5 runs). ~4.6x warm improvement;
    cold improvement expectedly larger (eliminated matplotlib/pyplot fontconfig + many .so loads).
  - Import-purity assert: after `import quickice.gui.main_window`, sys.modules contains NO
    vtkmodules/scipy/matplotlib/genice2/networkx/iapws/shapely. Remaining import cost: numpy+PySide6 (irreducible).
  - Forced-VTK path (local desktop simulation): main_window import = 0.52s, only vtkmodules remains
    (tab-0 viewer legitimately needs VTK).
  - Functional: deferred phase-diagram canvas builds on show/processEvents; on-demand diagram_canvas
    access works without event loop; set_coordinates works; export path (figure) works.
  - Full pytest suite (worktree): 1834 passed, 2 skipped, 10 failed — the 10 failures are the
    PRE-EXISTING, documented load-boundary subprocess-timeout flakes (7x test_cli_integration +
    3x test_phase_mapping::TestCLIIntegration) that fail IDENTICALLY on the unmodified baseline
    (confirmed by running the same files against the main-repo checkout).
  - False-start lesson recorded: PEP 562 module __getattr__ does NOT fire for LOAD_GLOBAL inside the
    same module (function-local name resolution); and function-local imports bypass mock.patch on
    module attributes — hence the sentinel+prologue pattern in ion_inserter/solute_inserter.
files_changed:
  - quickice/gui/vtk_utils.py
  - quickice/gui/__init__.py
  - quickice/gui/main_window.py
  - quickice/gui/export.py
  - quickice/gui/phase_diagram_widget.py
  - quickice/gui/phase_diagram_canvas.py (NEW — split from phase_diagram_widget)
  - quickice/gui/hydrate_viewer.py
  - quickice/gui/ion_viewer.py
  - quickice/gui/solute_viewer.py
  - quickice/gui/custom_molecule_viewer.py
  - quickice/structure_generation/__init__.py
  - quickice/structure_generation/ion_inserter.py
  - quickice/structure_generation/solute_inserter.py
  - quickice/structure_generation/custom_molecule_inserter.py
  - quickice/structure_generation/overlap_resolver.py
  - quickice/output/phase_diagram.py
  - quickice/output/validator.py
  - quickice/ranking/scorer.py
