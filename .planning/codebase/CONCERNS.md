# Codebase Concerns

**Analysis Date:** 2026-06-12

## Tech Debt

**gromacs_writer.py — God file at 2701 lines:**
- Issue: Single file contains 12 `write_*` functions plus 11+ utility functions. Every new structure type (ice, interface, hydrate, ion, solute, custom molecule) adds two more functions (gro + top writer). Each writer duplicates atomtype emission, molecule ordering, and GRO formatting logic.
- Files: `quickice/output/gromacs_writer.py`
- Impact: Adding any new molecule type requires touching this file in multiple places. The `write_solute_gro_file` function alone is ~250 lines. Bug fixes (atomtype deduplication, guest reordering) must be applied to every writer independently.
- Fix approach: Extract shared GRO line formatting into a base writer class or composable pipeline. Each structure type should provide a "molecule iterator" and the writer should iterate generically. The `type('obj', (object,), {...})()` hack at lines 1347, 2223, 2248, 2264, 2274 is a symptom — synthetic MoleculeIndex-like objects should be real MoleculeIndex instances.

**MainWindow — 2024-line "everything" class:**
- Issue: `MainWindow.__init__` stores 15+ instance attributes for cross-tab state (`_current_result`, `_current_interface_result`, `_current_hydrate_result`, `_current_ion_result`, `_current_solute_result`, `_current_custom_molecule_result`, etc.). Signal connections, export handlers, tab management, generation orchestration, and menu creation are all in one file.
- Files: `quickice/gui/main_window.py`
- Impact: Every new tab or workflow path adds state variables and slot handlers. The `_on_custom_finished` method alone is ~100 lines with nested hasattr checks. Cross-tab data flow is implicit (accessing `_current_interface_result` from ion/solute/custom slots).
- Fix approach: Introduce a shared `ApplicationState` object that all tabs reference, or a mediator/event-bus pattern. Extract each tab's generation logic into its own controller class. The MainWindow should only handle wiring, not orchestration.

**Duplicated GRO/TOP emission logic across exporters:**
- Issue: `quickice/gui/export.py` (929 lines) contains 8 exporter classes that each independently implement: file dialog → call writer → copy ITP files → copy guest ITP → comment out atomtypes. This is the same 5-step pattern repeated with minor variations for each structure type.
- Files: `quickice/gui/export.py`, `quickice/gui/hydrate_export.py`
- Impact: Bug fixes to ITP copying or atomtype commenting must be applied to every exporter. The `SoluteGROMACSExporter`, `CustomMoleculeGROMACSExporter`, `IonGROMACSExporter` in export.py are nearly identical.
- Fix approach: Create a `GROMACSExportBase` class with the common save-dialog → write → copy-itps → comment-atomtypes pipeline. Subclasses only override the specific writer function and filename.

**Duplicated renderer patterns:**
- Issue: `custom_molecule_renderer.py`, `solute_renderer.py`, `hydrate_renderer.py`, `ion_renderer.py` all follow "same pattern as" each other (noted in their own docstrings). Each implements atom-to-VTK-sphere mapping, bond line creation, and unit cell rendering independently.
- Files: `quickice/gui/custom_molecule_renderer.py`, `quickice/gui/solute_renderer.py`, `quickice/gui/hydrate_renderer.py`, `quickice/gui/ion_renderer.py`
- Impact: Rendering bugs (e.g., virtual site skipping at line 108/139/96 of renderers) must be fixed in each file. Adding a new display mode requires editing all renderers.
- Fix approach: Extract common molecule-to-VTK-actor logic into `quickice/gui/vtk_utils.py` (which already exists at 802 lines but is itself large). Create a parameterized renderer function that takes molecule metadata.

**Duplicated viewer widgets:**
- Issue: `custom_molecule_viewer.py`, `ion_viewer.py`, `solute_viewer.py` all duplicate the stacked-widget-with-placeholder pattern, VTK availability check, lazy interface-utils loading, and the same `_interface_utils_loaded` / `_interface_to_vtk_molecules` global state pattern.
- Files: `quickice/gui/custom_molecule_viewer.py`, `quickice/gui/ion_viewer.py`, `quickice/gui/solute_viewer.py`
- Impact: VTK initialization bug fixes must be applied to all three. Global mutable state (`_ion_actors`, `_interface_utils_loaded`) creates subtle coupling.
- Fix approach: Create a `StructureViewerBase` QStackedWidget subclass with VTK init, placeholder, and common rendering hooks.

**`Any` type annotations avoiding circular imports:**
- Issue: `IonStructure`, `SoluteStructure`, and `CustomMoleculeStructure` use `Any` for fields like `solute_registry`, `custom_gro_path`, `custom_itp_path`, and `interface_structure` with comments "(avoid circular import)". There are 7 such fields in `quickice/structure_generation/types.py`.
- Files: `quickice/structure_generation/types.py` (lines 387, 394, 395, 455, 462, 463, 561)
- Impact: IDE type checking is disabled for these fields. Callers must know the actual type from documentation or convention. Refactoring is riskier since there's no compile-time type safety.
- Fix approach: Use `from __future__ import annotations` (already Python 3.14) and `TYPE_CHECKING` block to import the actual types for static analysis while avoiding runtime circular imports.

**`type('obj', (object,), {...})()` synthetic objects in gromacs_writer.py:**
- Issue: When `molecule_index` is empty (real GenIce2 data), the GRO writers create anonymous objects with `start_idx`, `count`, `mol_type` attributes instead of proper `MoleculeIndex` instances. This occurs at 7 locations.
- Files: `quickice/output/gromacs_writer.py` (lines 1347, 1358, 2223, 2230, 2248, 2264, 2274)
- Impact: These synthetic objects lack the `MoleculeIndex` type, making debugging harder. Any code that type-checks against `MoleculeIndex` will fail for these.
- Fix approach: Always populate `molecule_index` during structure generation, or build proper `MoleculeIndex` instances in the fallback path.

## Known Bugs

**None currently tracked as open:**
- The `.planning/debug/resolved/` directory contains 200+ resolved issue notes from 34+ development phases. All known bugs have been fixed and verified with dedicated test scripts.
- The `.planning/debug/deferred/` directory contains 25 files representing optimization and enhancement ideas (e.g., `debug_efficiency.py`, `debug_tiling_detail.py`) that were deferred, not bugs.

**Potential recurrence risks from resolved bugs:**
- Atom name mismatches between GenIce2 output and .itp canonical order (resolved by `reorder_guest_atoms`, but fragile if new guest types are added)
- GRO/TOP molecule count ordering mismatches (resolved, but each new writer must follow the SOL→guest→custom→solute→ions ordering convention exactly)
- Guest molecules lost during ion/solute insertion (resolved by propagating guest attributes, but each new structure type must include all guest/custom/solute fields)
- PBC bond wrapping artifacts in 3D viewer (resolved, but triclinic cell support adds complexity)

## Security Considerations

**Path traversal in orchestrator:**
- Risk: `quickice/output/orchestrator.py` checks output path containment under CWD, but uses string prefix matching (`str(output_path).startswith(str(allowed_base))`). This could be bypassed with symlink attacks or paths containing the CWD as a substring.
- Files: `quickice/output/orchestrator.py` (lines 48-56)
- Current mitigation: `Path.resolve()` is used to normalize paths before comparison
- Recommendations: Use `output_path.is_relative_to(allowed_base)` (Python 3.9+) instead of string prefix check. This is the canonical way to check path containment.

**No input sanitization on custom molecule GRO/ITP files:**
- Risk: Users upload arbitrary `.gro` and `.itp` files. The `gro_parser.py` reads coordinates but validates only the range (> 50nm check). The `itp_parser.py` reads arbitrary text and uses regex matching. A malformed file could cause unexpected behavior.
- Files: `quickice/structure_generation/gro_parser.py`, `quickice/structure_generation/itp_parser.py`
- Current mitigation: `gro_parser.py` has a 50nm coordinate range check. `itp_parser.py` uses regex with specific patterns.
- Recommendations: Add file size limits for uploaded files. Validate that atom counts in GRO files match the declared count. Sanitize moleculetype names from ITP files against GROMACS naming rules (alphanumeric + underscore only).

**File overwrite without confirmation in export:**
- Risk: GROMACS export writes `.gro`, `.top`, and copies `.itp` files to the user-selected directory. If a file with the same name exists, it is silently overwritten.
- Files: `quickice/gui/export.py`
- Current mitigation: `QFileDialog.getSaveFileName` prompts the user, but only for the `.gro` file. Companion `.top` and `.itp` files are written without separate confirmation.
- Recommendations: Check for existing files and warn before overwrite. This is standard desktop application behavior.

**Module-level mutable state:**
- Risk: `_registry = MoleculetypeRegistry()` at module level in `gromacs_writer.py` (line 38) is a shared global. Between application runs this is fine, but if the module were imported in a test suite running multiple export scenarios, registry state leaks between tests.
- Files: `quickice/output/gromacs_writer.py` (line 38)
- Current mitigation: `MoleculetypeRegistry.clear()` exists but must be called manually
- Recommendations: Remove module-level registry; create per-export instances. Or use a reset mechanism between exports.

## Performance Bottlenecks

**Per-ion VTK sphere creation (O(n) actors):**
- Problem: `ion_renderer.py` creates one `vtkSphereSource` → `vtkPolyDataMapper` → `vtkActor` per ion (lines 97-104, 152-159). For N ions, this creates 3N VTK objects. VTK render loops over all actors each frame.
- Files: `quickice/gui/ion_renderer.py`
- Cause: Simple per-atom actor pattern is easy to implement but scales poorly
- Improvement path: Use `vtkGlyph3D` to render all ions of the same type as a single actor. This reduces draw calls from N to 2 (one per ion type). A glyph-based approach would handle 10,000+ ions smoothly.

**GenIce2 lazy import with thread lock:**
- Problem: `hydrate_generator.py` uses `threading.Lock()` for GenIce2 lazy import (lines 28, 53). This is a global lock that blocks all threads during import. GenIce2 imports are slow (loads many lattice modules).
- Files: `quickice/structure_generation/hydrate_generator.py`
- Cause: Thread-safe initialization pattern needed because GenIce2 is not thread-safe
- Improvement path: Pre-import GenIce2 at startup (in a loading screen) to avoid the runtime penalty. The lock can remain as a safety check.

**String concatenation for GRO file lines:**
- Problem: All `write_*_gro_file` functions build a `lines` list with formatted strings and write them with `f.writelines(lines)`. For large systems (>10,000 atoms), this builds a multi-MB string list in memory before writing.
- Files: `quickice/output/gromacs_writer.py`
- Cause: Standard approach; minor concern for typical use cases
- Improvement path: Write lines incrementally (`f.write()` per line or per molecule batch) instead of accumulating the full list first. This reduces peak memory for large systems.

**cKDTree rebuild for every overlap check:**
- Problem: `overlap_resolver.py` builds a new `cKDTree` for every call to `detect_overlaps`. The SoluteInserter and CustomMoleculeInserter also build cKDTrees for each molecule placement attempt. For N placement attempts, this is O(N * M log M) where M is the number of existing atoms.
- Files: `quickice/structure_generation/overlap_resolver.py`, `quickice/structure_generation/solute_inserter.py`, `quickice/structure_generation/custom_molecule_inserter.py`
- Cause: cKDTree doesn't support incremental insertion
- Improvement path: For the inserters, build the tree once and rebuild only when the tree becomes stale (after a batch of molecules is placed, not after each single molecule). This is a known optimization deferred from Phase 28.

## Fragile Areas

**Cross-tab state flow in MainWindow:**
- Files: `quickice/gui/main_window.py`
- Why fragile: Data flows between tabs via direct attribute access (`self._current_interface_result`, `self.solute_panel._custom_molecule_structure`, `self.ion_panel._custom_molecule_structure`). The flow is: Ice→Interface→(Hydrate→Interface)→Custom→Solute→Ion. Each tab's slot handler checks `hasattr` and `getattr` to detect what data is available from upstream tabs.
- Safe modification: When adding a new tab, you must: (1) add a `_current_*_result` attribute to MainWindow, (2) update all downstream tabs' slot handlers to check for the new attribute, (3) update all GROMACS writers to handle the new molecule type, (4) add the new molecule type to the `molecule_index` building logic in every writer's fallback path. Missing any step causes silent data loss.
- Test coverage: E2E workflow chain tests cover the main paths, but not all permutations (e.g., Custom→Ion without Solute is tested, but Hydrate→Interface→Custom→Solute→Ion may not be)

**`molecule_index` empty vs populated dual code paths:**
- Files: `quickice/output/gromacs_writer.py` (multiple writers), `quickice/structure_generation/ion_inserter.py`
- Why fragile: GenIce2-generated InterfaceStructures have `molecule_index = []`, while structures assembled by QuickIce have populated `molecule_index`. Every GRO/TOP writer must handle both cases with separate code paths. The empty case requires synthetic MoleculeIndex-like objects. If `molecule_index` is partially populated or inconsistent with `ice_atom_count`/`water_atom_count`, silent misalignment occurs.
- Safe modification: Always verify that atom counts match the sum of molecule counts. When adding a new structure type, ensure `molecule_index` is populated during generation (not left empty).
- Test coverage: Tests cover populated and empty molecule_index paths separately, but not the edge case where they're inconsistent.

**VTK display mode and atom size tuning:**
- Files: `quickice/gui/vtk_utils.py`, `quickice/gui/hydrate_renderer.py`, `quickice/gui/molecular_viewer.py`
- Why fragile: VTK sphere resolution, bond line widths, and color schemes are spread across multiple files as hardcoded constants. The display tuning history (see resolved notes: `display-radius-critical.md`, `display-radius-tuning.md`, `H-atom-color-scale.md`, `sphere-size-tuning.md`) shows this area has been fragile — small changes in sphere resolution or radius cause visual regressions.
- Safe modification: Centralize all display constants in `quickice/gui/constants.py` (which currently only has `TabIndex`). Do not hardcode VTK properties in renderer functions.
- Test coverage: Visual properties are not tested programmatically. Only manual visual inspection catches regressions.

**GenIce2 random state management:**
- Files: `quickice/structure_generation/generator.py` (lines 92-157)
- Why fragile: GenIce2 uses the global `np.random` state (not the modern Generator API). QuickIce saves/restores the global state around each generation call. This is explicitly NOT thread-safe (documented in the docstring). If any concurrent code touches `np.random`, generation results become non-reproducible.
- Safe modification: Do not introduce multi-threading in the generation pipeline. If parallelism is needed, use process-based parallelism (separate Python processes).
- Test coverage: The seed-based reproducibility is tested via e2e generation tests, but not under concurrent access.

**Phase diagram polygon rendering:**
- Files: `quickice/output/phase_diagram.py` (1132 lines), `quickice/gui/phase_diagram_widget.py` (778 lines)
- Why fragile: The phase diagram uses matplotlib polygons with manual coordinate clipping. Historical issues include polygon gaps, overlaps, and rendering regressions (see resolved notes: `polygon-gaps-in-diagram.md`, `phase-diagram-polygon-fix-v2.md`, `phase-diagram-worse-after-fix.md`). The boundary curves are defined in multiple files (`melting_curves.py`, `solid_boundaries.py`, `triple_points.py`) and any inaccuracy propagates to visual gaps.
- Safe modification: When adjusting boundary curves, regenerate the entire phase diagram and check for visual gaps. The curve-based lookup in `lookup.py` is independent of the polygon rendering, so lookup accuracy is not affected by rendering changes.
- Test coverage: `test_phase_mapping.py` (618 lines) covers the lookup logic. Polygon rendering is tested via visual regression in the e2e tests.

## Scaling Limits

**GRO format 5-digit atom/residue number limit:**
- Current capacity: 99,999 atoms per GRO file
- Limit: GRO format uses 5-character fields for atom and residue numbers. At 100,000+ atoms, numbers wrap modulo 100,000 (already implemented at lines like `atom_num_wrapped = atom_num % 100000` in gromacs_writer.py).
- Scaling path: This is a GROMACS format limitation, not a QuickIce bug. GROMACS itself handles wrapped numbers. For very large systems (>25,000 water molecules = 100,000 atoms), the wrapped numbers are functional but may confuse downstream tools.

**Single-threaded generation pipeline:**
- Current capacity: ~1-5 seconds for 96-256 molecule ice generation
- Limit: Generation is sequential: lookup → generate candidates → rank → display. All generation happens on one background thread. For very large systems (>1000 molecules), generation time grows linearly with molecule count.
- Scaling path: Candidate generation could be parallelized across processes (not threads, due to GenIce2's global random state). The ranking step is already fast.

**VTK rendering for >10,000 atoms:**
- Current capacity: Smooth rendering up to ~5,000 atoms
- Limit: Per-atom VTK actor pattern (especially ion_renderer.py) creates O(n) actors. VTK's render loop visits each actor. At >10,000 atoms, frame rates drop noticeably.
- Scaling path: Use vtkGlyph3D for batched rendering. Group all atoms of the same type into a single actor with glyph-based instancing. This is a deferred optimization from Phase 28.

## Dependencies at Risk

**GenIce2 (genice2==2.2.13.1):**
- Risk: GenIce2 is a research-grade package with a small maintainer team. It uses deprecated Python patterns (global `np.random` state, module-level imports). The package hasn't seen major updates since its initial release.
- Impact: If GenIce2 breaks on a future Python version (it already has compatibility quirks with 3.14), QuickIce cannot generate any ice or hydrate structures.
- Migration plan: The GenIce2 API is simple (create Lattice → GenIce → generate_ice). A fallback could directly read pre-generated GRO files from the bundled data directory for common configurations.

**VTK (vtk==9.5.2):**
- Risk: VTK is a massive dependency (~500MB in the dist). The PySide6 VTK integration (`QVTKRenderWindowInteractor`) is fragile across platforms (see `_VTK_AVAILABLE` checks and `_configure_opengl_for_remote` in main_window.py). SSH X11 forwarding causes segfaults without the Mesa GLX workaround.
- Impact: Users on remote displays (SSH X11 forwarding) cannot use the 3D viewer unless `QUICKICE_FORCE_VTK=true` is set. The workaround at `main_window.py:1965-1989` forces Mesa GLX for remote displays.
- Migration plan: Consider py3dmol or NGLview as lighter-weight 3D viewers for remote display scenarios. VTK could remain for local desktop use.

**IAPWS (iapws==1.5.5):**
- Risk: Small scientific package; may not keep up with Python version changes. Critical for density calculations.
- Impact: If iapws breaks, water/ice density calculations fail. The fallback values in `PHASE_METADATA` are coarse (single density values for most phases).
- Migration plan: Hardcode IAPWS R10-06(2009) density formulas for ice Ih (already partially done in `ice_ih_density.py`) and IAPWS95 for water (partially in `water_density.py`). Full independence from the iapws package is feasible.

**scipy (scipy==1.17.1):**
- Risk: Large dependency (~200MB), but actively maintained. The only critical usage is `scipy.spatial.cKDTree` for overlap detection and `scipy.spatial.transform.Rotation` for molecule rotation.
- Impact: If scipy needs to be dropped (e.g., for package size reduction), these two functions would need reimplementing.
- Migration plan: cKDTree could be replaced with a simple distance matrix calculation for small systems. Rotation could use a hand-rolled Euler angle implementation (already partially done in `main_window.py:1337-1341`).

## Missing Critical Features

**No undo/redo for structure modifications:**
- Problem: When a user inserts ions, solutes, or custom molecules, the modification is permanent. The only "undo" is clearing all results and starting over. The "Previous Custom Molecules Found" dialog (main_window.py:1097-1119) asks users to start fresh or cancel.
- Blocks: Users cannot experiment with different configurations without losing their entire workflow state.

**No project save/load:**
- Problem: All generation parameters, structures, and viewer states are lost when the application closes. There is no serialization of the application state.
- Blocks: Users cannot resume work on a structure across sessions.

**No CLI support for interface/hydrate/ion/solute/custom workflows:**
- Problem: The CLI (`quickice/cli/parser.py`) only supports basic ice generation. The interface, hydrate, ion, solute, and custom molecule workflows are GUI-only.
- Blocks: Batch processing and scripting workflows require the GUI.

**No validation of generated GRO files against GROMACS:**
- Problem: While e2e tests run `gmx grompp` on exported files (see `tests/test_e2e_gmx_validation.py`), there is no in-app validation. Users may export files that fail `gmx grompp` without knowing until they try to run the simulation.
- Blocks: Silent export errors (e.g., mismatched molecule counts, atomtype conflicts) are only caught downstream.

## Test Coverage Gaps

**GUI rendering code has no programmatic tests:**
- What's not tested: All VTK rendering functions (renderer.py files, vtk_utils.py, viewer.py files) are tested only via manual visual inspection. Color choices, sphere sizes, bond widths, and atom filtering (virtual site skipping) are not verified programmatically.
- Files: `quickice/gui/custom_molecule_renderer.py`, `quickice/gui/solute_renderer.py`, `quickice/gui/hydrate_renderer.py`, `quickice/gui/ion_renderer.py`, `quickice/gui/vtk_utils.py`
- Risk: Visual regressions from constant tuning go undetected. The `return None  # Virtual site, skip` pattern in multiple renderers could silently drop atoms.
- Priority: Medium

**MainWindow slot handlers are not unit-tested:**
- What's not tested: The 15+ slot handler methods in MainWindow (`_on_custom_finished`, `_on_insert_solutes`, `_on_insert_ions`, `_on_custom_generate_clicked`, etc.) contain complex cross-tab state management logic. Only e2e workflow tests exercise these indirectly.
- Files: `quickice/gui/main_window.py`
- Risk: Cross-tab state management bugs (e.g., stale references after clearing, incorrect water count calculations) are caught only by manual testing or e2e tests.
- Priority: High

**Custom molecule concentration calculation:**
- What's not tested: `CustomMoleculeInserter.calculate_molecule_count` (lines 98-131) calculates molecule count from molar concentration and volume. The CLI path is tested, but the GUI's concentration-to-count conversion (which uses a different volume calculation path) has limited test coverage.
- Files: `quickice/structure_generation/custom_molecule_inserter.py`
- Risk: Incorrect molecule counts could lead to physically invalid structures
- Priority: Medium

**Triclinic cell handling in export:**
- What's not tested: GRO export for triclinic cells (Ice II, Ice V) writes the full 9-value cell vector line. Tests primarily cover orthogonal cells. The triclinic export path in `write_interface_gro_file` and related writers has limited coverage.
- Files: `quickice/output/gromacs_writer.py`
- Risk: Triclinic cell vectors could be written in wrong order (GRO format: v1x v2y v3z v1y v1z v2x v2z v3x v3y), causing `gmx grompp` failures.
- Priority: Medium

**Global random state in multi-context usage:**
- What's not tested: `np.random` save/restore in `generator.py` is designed for sequential use. If QuickIce is used as a library (imported and called from another application), concurrent generation calls could corrupt random state.
- Files: `quickice/structure_generation/generator.py`
- Risk: Non-reproducible results when used as a library
- Priority: Low (current use case is GUI-only, which is sequential)

---

*Concerns audit: 2026-06-12*
