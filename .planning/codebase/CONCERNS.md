# Codebase Concerns

**Analysis Date:** 2026-06-13 (updated after scan fix round)

**Type legend:**
- `[bug-fix]` — Can be fixed with a targeted patch; no architectural change
- `[tech-debt-refactor]` — Requires deep refactoring of existing architecture; high risk, high effort
- `[feature-request]` — New capability not currently present; requires design + implementation

---

## Resolved (2026-06-13 scan fix round)

| Issue | Type | Resolution |
|-------|------|------------|
| V-11: identical custom molecule rotations | `[bug-fix]` | Fixed: `self.seed` → `self.rng.randint()` |
| V-16: CO2 misidentified as THF | `[bug-fix]` | Fixed: reordered detect_guest_type_from_atoms |
| SEC: path traversal via str.startswith | `[bug-fix]` | Fixed: → `Path.is_relative_to()` |
| V-19: ion volume uses total cell | `[bug-fix]` | Fixed: water-fraction based liquid volume |
| V-13: GRO parse silently drops lines | `[bug-fix]` | Fixed: added logger.warning calls |
| V-03/V-03b: O(N²) cKDTree rebuild | `[tech-debt-refactor]` | Fixed: base_existing_data batch rebuild |
| V-15: dead /√3*√3 arithmetic | `[bug-fix]` | Fixed: removed no-op arithmetic |
| V-26: reorder_guest_atoms invalid mapping | `[bug-fix]` | Fixed: permutation validation added |
| V-27: broad except Exception | `[bug-fix]` | Fixed: narrowed to (ValueError, OSError) |
| V-24: assert in production | `[bug-fix]` | Fixed: replaced with raise ValueError |
| V-08/V-09: O(N) Python loops in water_filler | `[tech-debt-refactor]` | Fixed: vectorized with numpy reshape |
| V-01: MOLECULE_TYPE_INFO ice atoms=3 | `[bug-fix]` | Low severity — dict is dead in production |
| V-04: charge neutrality index corruption | — | FALSE ALARM — deletion-from-end preserves correctness |
| V-02: per-ion cKDTree rebuild | — | Low severity — ion count typically <50 |
| DOC-*: 15 documentation issues | `[bug-fix]` | All fixed: phases, citations, formulas, CLI defaults |

---

## Open Issues — `[bug-fix]` (targeted patches, no architectural change)

**No input sanitization on custom molecule GRO/ITP files:** `[bug-fix]`
- Risk: Users upload arbitrary `.gro` and `.itp` files. `gro_parser.py` validates only coordinate range. `itp_parser.py` reads arbitrary text with regex. A malformed file could cause unexpected behavior.
- Files: `quickice/structure_generation/gro_parser.py`, `quickice/structure_generation/itp_parser.py`
- Current mitigation: 50nm range check, regex patterns
- Fix: Add file size limits, validate atom count matches header, sanitize moleculetype names (alphanumeric + underscore only)

**File overwrite without confirmation in export:** `[bug-fix]`
- Risk: GROMACS export silently overwrites existing `.top` and `.itp` files.
- Files: `quickice/gui/export.py`
- Current mitigation: `QFileDialog.getSaveFileName` for `.gro` only
- Fix: Check for existing companion files and warn before overwrite

**Module-level mutable MoleculetypeRegistry:** `[bug-fix]`
- Risk: `_registry = MoleculetypeRegistry()` at module level in `gromacs_writer.py:38` leaks state between export scenarios.
- Files: `quickice/output/gromacs_writer.py`
- Current mitigation: `MoleculetypeRegistry.clear()` exists but must be called manually
- Fix: Create per-export instances or auto-reset before each export

**V-07: detect_atoms_per_molecule fragile for guest-first arrays:** `[bug-fix]`
- Risk: Function only checks `atom_names[0]=="OW"`. If guest atoms precede water (non-standard GenIce2 output), returns 3 instead of 4.
- Files: `quickice/structure_generation/modes/slab.py:37-41`, `pocket.py:37-41`, `piece.py:44-48`
- Current status: Works for all supported inputs (GenIce2 always outputs water first). Low priority.
- Fix: Scan first 10 atoms for "OW" or check metadata for hydrate flag.

**V-01: MOLECULE_TYPE_INFO["ice"]["atoms"]=3 inaccurate:** `[bug-fix]`
- Risk: Dict says TIP3P (3 atoms) but codebase uses TIP4P-ICE (4 atoms). No production code reads it, but it's misleading.
- Files: `quickice/structure_generation/types.py:12`
- Fix: Either fix value to 4 and update description, or remove dead dict entirely (see dead code item DC-3.1).

---

## Open Issues — `[tech-debt-refactor]` (deep refactoring, high effort)

**gromacs_writer.py — God file at 2701 lines:** `[tech-debt-refactor]`
- Issue: 12 `write_*` functions + 11+ utilities. Every new molecule type adds 2 more functions. Each writer duplicates atomtype emission, molecule ordering, and GRO formatting logic.
- Files: `quickice/output/gromacs_writer.py`
- Impact: Bug fixes must be applied to every writer independently. Adding new molecule types requires touching multiple places.
- Fix approach: Extract shared GRO line formatting into a base writer class or composable pipeline. Each structure type provides a "molecule iterator" and the writer iterates generically. The `type('obj', (object,), {...})()` hack at 7 locations is a symptom — synthetic objects should be real `MoleculeIndex` instances.
- Effort: HIGH (touches 12+ functions, every export path, all 130+ export tests)

**MainWindow — 2024-line "everything" class:** `[tech-debt-refactor]`
- Issue: 15+ instance attributes for cross-tab state, signal connections, export handlers, tab management, generation orchestration, and menu creation all in one file.
- Files: `quickice/gui/main_window.py`
- Impact: Every new tab adds state variables and slot handlers. `_on_custom_finished` alone is ~100 lines with nested hasattr checks.
- Fix approach: Introduce `ApplicationState` object or mediator/event-bus pattern. Extract each tab's generation logic into its own controller class.
- Effort: VERY HIGH (touches entire GUI layer, all signal connections, all e2e GUI tests)

**Duplicated GRO/TOP emission logic across exporters:** `[tech-debt-refactor]`
- Issue: 8 exporter classes in `export.py` (929 lines) independently implement the same 5-step pattern.
- Files: `quickice/gui/export.py`, `quickice/gui/hydrate_export.py`
- Fix approach: Create `GROMACSExportBase` class with common pipeline. Subclasses override only writer function and filename.
- Effort: MEDIUM (contained to 2 files, each subclass is ~50 lines)

**Duplicated renderer + viewer patterns:** `[tech-debt-refactor]`
- Issue: 4 renderers + 3 viewers all duplicate the same patterns (atom-to-VTK mapping, bond lines, unit cell rendering, stacked-widget placeholder, VTK init, lazy loading).
- Files: 7 files in `quickice/gui/`
- Fix approach: Extract common logic into `vtk_utils.py` (parameterized renderer) and `StructureViewerBase` (QStackedWidget subclass).
- Effort: MEDIUM-HIGH (7 files, VTK rendering is fragile, visual regression risk)

**`Any` type annotations avoiding circular imports:** `[tech-debt-refactor]`
- Issue: 7 fields in `types.py` use `Any` to avoid circular imports. Disables IDE type checking.
- Files: `quickice/structure_generation/types.py`
- Fix approach: Use `from __future__ import annotations` + `TYPE_CHECKING` block.
- Effort: LOW (mechanical change, but must verify no runtime circular import)

**Cross-tab state flow in MainWindow:** `[tech-debt-refactor]`
- Issue: Data flows between tabs via direct attribute access and hasattr/getattr duck-typing.
- Files: `quickice/gui/main_window.py`
- Risk: Adding a new tab requires updating all downstream tabs' slot handlers, GROMACS writers, and molecule_index logic.
- Fix approach: Centralized `ApplicationState` with typed signals.
- Effort: HIGH (coupled with MainWindow refactor above)

**`molecule_index` empty vs populated dual code paths:** `[tech-debt-refactor]`
- Issue: GenIce2 structures have `molecule_index = []`; QuickIce-assembled structures have populated index. Every GRO/TOP writer has separate code paths.
- Files: `quickice/output/gromacs_writer.py`, `quickice/structure_generation/ion_inserter.py`
- Fix approach: Always populate `molecule_index` during structure generation, eliminating the empty fallback path and synthetic MoleculeIndex-like objects.
- Effort: MEDIUM (must trace all generation paths to ensure index is populated)

**Per-ion VTK sphere creation — O(n) actors:** `[tech-debt-refactor]`
- Issue: One VTK actor per ion → 3N VTK objects for N ions. Slow at >1000 ions.
- Files: `quickice/gui/ion_renderer.py`
- Fix approach: Use `vtkGlyph3D` for batched rendering (2 actors total instead of 3N).
- Effort: MEDIUM (VTK API change, visual regression testing needed)

---

## Open Issues — `[feature-request]` (new capabilities, requires design)

**No undo/redo for structure modifications:** `[feature-request]`
- Problem: Insertions are permanent. Only "undo" is clearing all results and starting over.
- Design: Snapshot-based undo stack or command pattern. Each insertion creates a reversible operation.
- Effort: HIGH (requires state serialization, UI changes, undo stack management)

**No project save/load:** `[feature-request]`
- Problem: All state lost on application close. No session persistence.
- Design: Serialize generation parameters, structures, viewer state to JSON/ZIP. Load on startup.
- Effort: HIGH (dataclass serialization, version migration, UI for save/load)

**No CLI support for Tabs 3-5 (Custom, Solute, Ion):** `[feature-request]`
- Problem: CLI only supports basic ice generation. Custom molecule, solute, and ion workflows are GUI-only.
- Design: Extend CLI parser with `--custom-gro`, `--custom-itp`, `--solute`, `--ion` flags.
- Effort: MEDIUM (CLI is ~200 lines, each new flag maps to existing API)

**No in-app GROMACS validation:** `[feature-request]`
- Problem: Exported files may fail `gmx grompp` without user knowing until simulation time.
- Design: Optional post-export `gmx grompp` check (if GROMACS installed). Show pass/fail in export dialog.
- Effort: LOW-MEDIUM (subprocess call + result parsing, conditional on gmx availability)

---

## Fragile Areas (ongoing risk, not fixable without architecture change)

**VTK display mode and atom size tuning:**
- Files: `quickice/gui/vtk_utils.py`, `quickice/gui/hydrate_renderer.py`, `quickice/gui/molecular_viewer.py`
- Why fragile: VTK constants hardcoded across files. Small changes cause visual regressions.
- Mitigation: Centralize display constants in `quickice/gui/constants.py`. No programmatic VTK tests exist.

**GenIce2 random state management:**
- Files: `quickice/structure_generation/generator.py:92-157`
- Why fragile: Uses global `np.random` state (not modern Generator API). NOT thread-safe.
- Mitigation: Sequential execution only. Process-based parallelism if needed.

**Phase diagram polygon rendering:**
- Files: `quickice/output/phase_diagram.py` (1132 lines), `quickice/gui/phase_diagram_widget.py` (778 lines)
- Why fragile: Matplotlib polygons with manual coordinate clipping. Boundary curve inaccuracies propagate to visual gaps.
- Mitigation: Regenerate full diagram after any boundary curve change. Lookup logic is independent of rendering.

---

## Scaling Limits (GROMACS format, inherent constraints)

**GRO format 5-digit atom/residue number limit:**
- Capacity: 99,999 atoms. Numbers wrap modulo 100,000 (already implemented).
- Path: GROMACS format limitation. Functional but may confuse downstream tools.

**Single-threaded generation pipeline:**
- Capacity: ~1-5s for 96-256 molecules. Linear growth with molecule count.
- Path: Process-based parallelism for candidate generation (not threads, due to GenIce2 global state).

**VTK rendering for >10,000 atoms:**
- Capacity: Smooth up to ~5,000 atoms. Frame rates drop above 10,000.
- Path: `vtkGlyph3D` batched rendering (deferred from Phase 28).

---

## Dependencies at Risk

**GenIce2 (genice2==2.2.13.1):**
- Risk: Small maintainer team, deprecated Python patterns, no recent updates. Compatibility quirks with Python 3.14.
- Migration plan: Pre-generated GRO files from bundled data as fallback.

**VTK (vtk==9.5.2):**
- Risk: ~500MB dependency. PySide6+VTK integration fragile across platforms. SSH X11 requires Mesa GLX workaround.
- Migration plan: py3dmol or NGLview for remote display; VTK for local desktop.

**IAPWS (iapws==1.5.5):**
- Risk: Small package, may not track Python versions. Critical for density calculations.
- Migration plan: Hardcode IAPWS formulas (partially done in `ice_ih_density.py` and `water_density.py`).

**scipy (scipy==1.17.1):**
- Risk: ~200MB, actively maintained. Critical for `cKDTree` and `Rotation`.
- Migration plan: Simple distance matrix for small systems. Hand-rolled Euler angles (partially in `main_window.py:1337-1341`).

---

## Test Coverage Gaps

**GUI rendering code has no programmatic tests:**
- Files: 4 renderer files + `vtk_utils.py` + 3 viewer files
- Risk: Visual regressions undetected. Virtual site skip could silently drop atoms.
- Priority: Medium

**MainWindow slot handlers are not unit-tested:** `[tech-debt-refactor]` prerequisite
- Files: `quickice/gui/main_window.py`
- Risk: Cross-tab state bugs caught only by e2e or manual testing.
- Priority: High

**Custom molecule concentration calculation:**
- Files: `quickice/structure_generation/custom_molecule_inserter.py`
- Risk: Incorrect molecule counts → physically invalid structures
- Priority: Medium

**Triclinic cell handling in export:**
- Files: `quickice/output/gromacs_writer.py`
- Risk: Wrong cell vector order → `gmx grompp` failures
- Priority: Medium

**Global random state in multi-context usage:**
- Files: `quickice/structure_generation/generator.py`
- Risk: Non-reproducible results when used as library
- Priority: Low

---

*Concerns audit: 2026-06-13 — updated with scan fix resolutions and type labels*
