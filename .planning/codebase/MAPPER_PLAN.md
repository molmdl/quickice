# Subagent Strategy: Codebase Mapping + Scancode Tasks

**Created:** 2026-06-15
**Staleness:** Codebase docs last updated 2026-06-12; Phases 34.5–37 shipped since then (CLI pipeline, unified entry point, workflow scripts, 7+ new test files)
**Total Python:** ~30,000 lines across ~80 source files + ~60 test files
**Parallel limit:** 4 subagents max

---

## What Changed Since Last Update (2026-06-12)

The 7 codebase docs are stale after Phases 34.5–37 shipped. Key deltas:

| Area | What Changed | Affected Docs |
|------|-------------|---------------|
| **Entry points** | `quickice/__main__.py` + `quickice/entry.py` (unified router); `quickice.py` now delegates to `entry.main()` | STRUCTURE, ARCHITECTURE, STACK |
| **CLI pipeline** | `quickice/cli/pipeline.py` (744 lines), `quickice/cli/parser.py` (533 lines), `quickice/cli/itp_helpers.py` (406 lines) — all NEW | STRUCTURE, ARCHITECTURE, INTEGRATIONS, CONVENTIONS, TESTING |
| **Build config** | PyInstaller spec entry changed from `quickice/gui/__main__.py` to `quickice/__main__.py`; `console=True` + `hide_console='hide-late'` | STACK, INTEGRATIONS |
| **Scripts** | `scripts/cli-examples.sh`, `scripts/hydrate-interface-custom-ion.sh`, `scripts/assemble-dist.sh` — all NEW | STRUCTURE, STACK |
| **Docs** | `docs/cli-reference.md` unified entry sections; `docs/gro-itp-guide.md` workflow refs | INTEGRATIONS |
| **Tests** | ~7 new files: `test_cli_integration.py`, `test_cli_pipeline.py`, plus test migrations to `run_quickice()` | TESTING |
| **Data ITPs** | `ch4_liquid.itp`, `thf_liquid.itp` — now documented in STRUCTURE | (already partially covered) |
| **Cross-tab flow** | Custom→Solute→Ion workflow chains added to MainWindow | ARCHITECTURE |
| **Bug fixes** | BUG-05, MW-01, DEFLT-01, RNG-01, ATOM-01, TREE-01, GUEST-01, PERF-02, BUG-04 | CONCERNS |

---

## Batch Overview

| Batch | Agents | Duration | Purpose |
|-------|--------|----------|---------|
| **1** | 4 agents parallel | ~15-20 min | Update 7 codebase docs + start Scancode A (flow trace) |
| **2** | 3 agents parallel | ~15-20 min | Scancode B (vulnerability scan) + Scancode C (doc cross-check, 2 agents: CLI + GUI) |
| **3** | 1 agent | ~10-15 min | Scancode D (portable distribution analysis) |

**Total agents:** 8
**Total batches:** 3
**Wall-clock estimate:** ~45-55 minutes

---

## Batch 1: Codebase Doc Updates + Flow Trace (4 parallel agents)

All 4 agents can run simultaneously — no file conflicts, no dependencies between them.

### Agent 1.1: STACK.md + INTEGRATIONS.md Update

- **Subagent type:** `gsd-codebase-mapper`
- **Focus:** Technology stack and external integration audit
- **Prompt summary:** Refresh STACK.md and INTEGRATIONS.md for post-Phase-37 state. Key changes to capture:
  - **STACK.md:** Add `quickice/entry.py` as unified entry module; update PyInstaller entry point from `quickice/gui/__main__.py` to `quickice/__main__.py`; add `console=True` + `hide_console='hide-late'` build notes; note `quickice/cli/` as new module (pipeline.py 744 lines, parser.py 533 lines, itp_helpers.py 406 lines); update click dependency note (still declared but argparse is primary; clarify if click is used anywhere); add `scripts/cli-examples.sh` and `scripts/hydrate-interface-custom-ion.sh` to build/dev section. Verify all version numbers against `environment.yml` imports.
  - **INTEGRATIONS.md:** Add CLI pipeline section describing `quickice/cli/pipeline.py` as new integration surface (full generation workflow via CLI args → Model layer synchronous calls); update CI/CD section noting `quickice-gui.spec` now uses `quickice/__main__.py`; add `scripts/assemble-dist.sh` to deployment section; update GROMACS File Export to note `quickice/cli/itp_helpers.py` as new ITP path resolver; note `comment_out_atomtypes_in_itp()` is used by both GUI exporters and CLI pipeline.
- **Output files:** `.planning/codebase/STACK.md`, `.planning/codebase/INTEGRATIONS.md`
- **Analysis date:** Update from `2026-06-12` to `2026-06-15`

### Agent 1.2: ARCHITECTURE.md + STRUCTURE.md Update

- **Subagent type:** `gsd-codebase-mapper`
- **Focus:** Architecture patterns and codebase structure
- **Prompt summary:** Refresh ARCHITECTURE.md and STRUCTURE.md for post-Phase-37 state. Key changes:
  - **ARCHITECTURE.md:** Add "Unified Entry Point" section for `quickice/entry.py` (router pattern: `--cli`/`--gui`/default detection, `importlib.util.find_spec` for PySide6, `_has_display` for GUI auto-launch); add "CLI Pipeline Layer" between CLI Layer and Model Layer sections — `quickice/cli/pipeline.py` is `CLIPipeline` class with ordered step execution (source→interface→custom→solute→ion→export), fail-fast semantics, no Qt imports; update "Entry Points" section — `quickice/__main__.py` is now the primary entry point (delegates to `entry.main()`), `quickice/gui/__main__.py` still exists but is superseded, `quickice.py` delegates to `entry.main()` for backward compat; update "Data Flow" to add CLI pipeline data flow (args → CLIPipeline → Model layer → export); update "Cross-Tab Data Flow" to note `MainWindow._current_custom_molecule_result` is now also a source for Solute and Ion tabs; update "Worker Pattern" to note HydrateWorker still subclasses QThread (not migrated to QObject→QThread pattern).
  - **STRUCTURE.md:** Add `quickice/entry.py` to directory layout (unified entry point); add `quickice/cli/` directory with `__init__.py`, `pipeline.py`, `parser.py`, `itp_helpers.py`; add `quickice/__main__.py` to layout; update `scripts/` listing to include `cli-examples.sh`, `hydrate-interface-custom-ion.sh`, `assemble-dist.sh`; update "Key File Locations → Entry Points" — `quickice/__main__.py` is now primary, `quickice/entry.py` is the router; update "Where to Add New Code" — add "New CLI Step" section (add method to CLIPipeline, add flag to parser.py, add helper to itp_helpers.py if needed); update test file list (add `test_cli_integration.py`, `test_cli_pipeline.py`).
- **Output files:** `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`
- **Analysis date:** Update from `2026-06-12` to `2026-06-15`

### Agent 1.3: CONVENTIONS.md + TESTING.md Update

- **Subagent type:** `gsd-codebase-mapper`
- **Focus:** Coding conventions and testing patterns
- **Prompt summary:** Refresh CONVENTIONS.md and TESTING.md for post-Phase-37 state. Key changes:
  - **CONVENTIONS.md:** Add CLI naming conventions — `quickice/cli/pipeline.py` uses `step_` prefix for pipeline step methods (`step_source`, `step_interface`, `step_custom`, `step_solute`, `step_ion`, `step_export`); `_parse_*` prefix for private parsing helpers (`_parse_positions_csv`); `_get_source_structure` for structure resolution; `report_progress()` for stderr logging pattern (`[PROGRESS]` prefix); CLIPipeline class follows the existing `{Feature}Pipeline` pattern but is the only one; `quickice/entry.py` uses `_ROUTER_FLAGS` frozenset for O(1) membership, `_is_pyside6_available()` / `_has_display()` / `_has_pipeline_flags()` private helpers with `_` prefix; update entry point naming — `quickice/__main__.py` → `entry.main()` delegation pattern; add `scripts/cli-examples.sh` bash convention (commented-out commands, safe to execute); `scripts/hydrate-interface-custom-ion.sh` bash convention (`while/shift` for flag parsing, missing-value guards).
  - **TESTING.md:** Add CLI pipeline testing patterns — `run_quickice(*args, timeout=60)` subprocess helper in `tests/conftest.py` (shared, replaces per-file helpers); subprocess-based CLI e2e testing pattern (full pipeline via `subprocess.run`, 120s timeout, tempfile cleanup); add `test_cli_integration.py` (entry point routing tests: subprocess for real integration, direct `entry.main()` call for mock-based tests); add `test_cli_pipeline.py` (CLI pipeline e2e tests: subprocess-based, `--no-overwrite` flag testing); note `from tests.conftest import run_quickice` pattern (root conftest shadows tests/conftest); update test file count from "55+" to "60+" (7 new files); add `@pytest.mark.slow` marker registration in conftest.py; note `sys.path.insert` pattern for e2e_export_helpers import; update "E2E Tests" section to include CLI pipeline e2e category.
- **Output files:** `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/TESTING.md`
- **Analysis date:** Update from `2026-06-12` to `2026-06-15`

### Agent 1.4: CONCERNS.md Update + Scancode A (Flow Trace)

- **Subagent type:** `gsd-codebase-mapper`
- **Focus:** Codebase concerns + GROMACS export flow trace
- **Prompt summary:** Two-part task:
  1. **Refresh CONCERNS.md:** Update resolved/deferred status. Changes since 2026-06-12:
     - BUG-05 (HW1 Z-coordinate copy-paste) → mark RESOLVED (Phase 34.7-01)
     - MW-01 (molecule-aware wrapping) → mark RESOLVED (Phase 34.7-01)
     - DEFLT-01 (fudgeLJ/fudgeQQ defaults) → mark RESOLVED (Phase 34.7-01)
     - ATOM-01 (WATER_ATOMS_PER_MOLECULE constant) → mark RESOLVED (Phase 34.7-02)
     - RNG-01 (unseeded RNG in custom molecule) → mark RESOLVED (Phase 34.7-02)
     - TREE-01 (conditional KDTree rebuild) → mark RESOLVED (Phase 34.7-03)
     - GUEST-01 (dead CO2 code + guest_type param) → mark RESOLVED (Phase 34.7-08)
     - PERF-02 (cKDTree boxsize for scorer) → mark RESOLVED (Phase 34.8-01)
     - BUG-04 (diversity_score always 1.0) → mark RESOLVED (Phase 34.8-03)
     - TEST-09 (moleculetype name matching) → mark RESOLVED (Phase 34.8-02)
     - Add new concerns discovered in Phases 36-37 if any (e.g., CLIPipeline duck-typing attribute propagation on IonStructure, getattr patterns for backward compat)
     - Update "Resolved" table with all Phase 34.7/34.8 fixes
     - Keep deferred items unchanged unless resolved
  2. **Scancode Task A: GROMACS Export Flow Trace:** Generate a complete function/data flow trace from user action to successful GROMACS export. Trace ALL paths including:
     - **GUI paths (6 tabs):** Ice candidate export, Hydrate export, Interface export, Custom Molecule export, Solute export, Ion export — AND full chain exports (F1-F7)
     - **CLI paths:** `python -m quickice --temperature ... --pressure ... --nmolecules ... --export` single-step, AND full pipeline `--interface --custom-placement random --solute-type ch4 --ion-concentration 0.5 --export`
     - For each path: trace every function call from entry point through generation → structure assembly → GROMACS writer → file I/O
     - Note: Previous traces exist (`20260608_gromacs_flow_trace.md`, `20260612_gromacs_flow_trace.md`) but are pre-Phase-36/37 — CLI pipeline path is entirely new
     - Include the unified entry point routing decision tree
- **Output files:** `.planning/codebase/CONCERNS.md`, `.planning/code_analysis/20260615_gromacs_flow_trace.md`
- **Analysis date:** Update from `2026-06-13` to `2026-06-15` (CONCERNS.md only)

---

## Batch 2: Scancode B + C (3 parallel agents)

Scancode B and C have no dependencies on Batch 1 (they are read-only analysis). Scancode C is split into 2 agents (CLI docs + GUI docs) per the scancode.md instruction to "spawn multiple agents" for documentation cross-check.

### Agent 2.1: Scancode B — Vulnerability/Performance Scan

- **Subagent type:** `general`
- **Focus:** Critical code vulnerability, safety concern, and performance scan
- **Prompt summary:** Perform a read-only critical scan of the entire QuickIce codebase (all Python files in `quickice/` and `tests/`). Focus areas:
  1. **Nested for-loops:** Find all nested loops (2+ deep) and assess whether they can be vectorized with NumPy. Pay special attention to `quickice/structure_generation/` (inserter modules) and `quickice/output/gromacs_writer.py` (2700+ lines).
  2. **Unit mismatch:** Check all physics calculations for unit consistency — nm vs Å, K vs °C, MPa vs bar, g/cm³ vs kg/m³, mol/L vs molecules/nm³. Cross-reference with IAPWS formulas in `quickice/phase_mapping/`.
  3. **Atom number mismatch:** Verify atom counts match between data structures and GRO/TOP writers. Check that `WATER_ATOMS_PER_MOLECULE` (4 for TIP4P-ICE) is used consistently. Verify guest atom counts (CH4=5, THF=13) are correct in all inserters and exporters.
  4. **New CLI pipeline vulnerabilities:** The `quickice/cli/pipeline.py` uses duck-typing attribute propagation (setting attrs on InterfaceStructure at runtime) — is this safe? Check `getattr` patterns for backward compat — do they mask real errors? Check subprocess timeout handling in tests.
  5. **Race conditions / thread safety:** `np.random` global state (TD-05 deferred). Any new shared mutable state in CLI pipeline?
  6. **Error handling gaps:** Are all user-facing errors handled? Missing `try/except` around file I/O in CLI pipeline? Missing validation before GROMACS export?
  7. **Security:** Path traversal in file operations (SEC-01 was fixed, verify no regressions). `comment_out_atomtypes_in_itp` modifies output copy — verify source is never modified.
  
  Reference previous scan results: `20260612_vulnerability_scan.md`. Focus on NEW code since that scan (Phases 34.5-37: CLI pipeline, entry point, workflow scripts).
  
  **DO NOT fix anything.** Report findings only.
- **Output file:** `.planning/code_analysis/20260615_vulnerability_scan.md`

### Agent 2.2: Scancode C — Documentation Cross-Check (CLI Focus)

- **Subagent type:** `general`
- **Focus:** Cross-check CLI documentation against actual CLI code
- **Prompt summary:** Cross-check all CLI-facing documentation for consistency with the actual code implementation. Documents to check:
  1. **`docs/cli-reference.md`:** Verify all CLI flags documented match `quickice/cli/parser.py` argparse definitions. Check flag names, defaults, help strings, and value types. Verify the unified entry point routing table is accurate against `quickice/entry.py`. Check platform invocation table. Verify example commands still work (syntax check only, don't execute).
  2. **`scripts/cli-examples.sh`:** Verify all 39 commented-out commands reference valid flags. Check that flag combinations are logically consistent (e.g., `--hydrate` implies `--hydrate-type`, `--interface` requires prior generation flags).
  3. **`scripts/hydrate-interface-custom-ion.sh`:** Verify the full pipeline chain script is consistent with `quickice/cli/pipeline.py` step order. Check flag values against parser constraints.
  4. **`docs/gro-itp-guide.md`:** Verify any CLI references are consistent with current parser.
  5. **`README.md`:** Verify CLI quick-start examples are current.
  6. **Citation suggestions:** Check if any CLI-related code references scientific methods that should have citations in docs (e.g., Madrid2019 for ions, GAFF2 for solutes, IAPWS for phase mapping).
  
  Reference previous results: `20260612_documentation_crosscheck.md`, `20260608_docs_crosscheck_and_dead_code.md`. Focus on NEW/CHANGED content since those scans.
  
  **DO NOT fix anything.** Report findings only.
- **Output file:** `.planning/code_analysis/20260615_documentation_crosscheck_cli.md`

### Agent 2.3: Scancode C — Documentation Cross-Check (GUI Focus)

- **Subagent type:** `general`
- **Focus:** Cross-check GUI documentation and in-app help against actual GUI code
- **Prompt summary:** Cross-check all GUI-facing documentation for consistency with the actual GUI implementation. Documents to check:
  1. **`docs/gui-guide.md`:** Verify tab numbering (Tab 0-5) matches `quickice/gui/constants.py` TabIndex enum. Verify workflow descriptions match actual `MainWindow` signal/slot connections. Check that all keyboard shortcuts documented match actual `QShortcut` registrations in `quickice/gui/main_window.py`.
  2. **`quickice/gui/help_dialog.py`:** Verify help dialog content matches current application state — tab descriptions, shortcuts, workflow descriptions. Check that Tab 0-5 numbering is consistent.
  3. **`README.md`:** Verify GUI feature list matches current tab structure. Check screenshots references still valid.
  4. **Tooltips in GUI code:** Scan all `setToolTip()` calls in `quickice/gui/*_panel.py` files. Verify tooltip text is scientifically accurate and consistent with `docs/gui-guide.md`.
  5. **`docs/principles.md`:** Check if core principles are still reflected in current code patterns.
  6. **`docs/ranking.md`:** Verify ranking documentation matches current `scorer.py` implementation (diversity_score now uses O-O histogram fingerprint, not seed-based).
  7. **Citation suggestions:** Check if GUI help/tooltips reference scientific methods that need citations.
  
  Reference previous results: `20260612_documentation_crosscheck.md`. Focus on CHANGED content since that scan (Phase 34.5/34.6 validation features, Phase 35 tooltips/help, Phase 36/37 unified entry).
  
  **DO NOT fix anything.** Report findings only.
- **Output file:** `.planning/code_analysis/20260615_documentation_crosscheck_gui.md`

---

## Batch 3: Scancode D — Portable Distribution Analysis (1 agent)

This agent can run after Batch 1 completes (needs updated STACK.md for dependency info) but doesn't depend on Batch 2.

### Agent 3.1: Scancode D — Portable Distribution & PyInstaller Optimization

- **Subagent type:** `general`
- **Focus:** Identify necessary libs for portable distribution and PyInstaller optimization
- **Prompt summary:** Analyze the QuickIce project for portable distribution optimization. Tasks:
  1. **Dependency audit:** List ALL runtime dependencies actually used by the application (both GUI and CLI modes). Cross-reference `environment.yml` with actual imports in `quickice/`. Categorize each dependency as:
     - **GUI-critical** (required for `python -m quickice` with GUI): PySide6, VTK, matplotlib (phase diagram widget), shapely
     - **CLI-only** (required for `python -m quickice --cli`): numpy, scipy, iapws, genice2, spglib
     - **Shared** (both modes): numpy, scipy, iapws, genice2
     - **Unnecessary** (declared but not actually imported/used at runtime): check click, openpyscad, deprecated, deprecation, yaplotlib, wirerope, methodtools, pairlist, cycless, graphstat
  2. **PyInstaller spec analysis (`quickice-gui.spec`):** 
     - Current `collect_all()` calls: `iapws`, `genice2`, `genice_core`, `matplotlib`, `scipy`, `numpy`, `shapely`, `networkx`, `spglib`
     - Which of these are truly needed at runtime? Which collect_all brings in excessive subpackages?
     - `genice2 collect_all` brings ALL lattice/molecule/format plugins (BUNDLE-02 deferred) — can we exclude unused lattice plugins (only need `ice1h`, `ice1c`, `ice2`, `ice3`, `ice5`, `ice6`, `ice7`, `ice8`, `sI`, `sII`, `sH`)?
     - Can `matplotlib` collection be narrowed? Only need `matplotlib.backends.backend_qt5agg` and basic pyplot.
     - `networkx` — is this needed at runtime or only by GenIce during generation? Can it be excluded if GenIce bundles it?
  3. **CLI-only binary feasibility:** Could we build a smaller CLI-only binary by excluding PySide6/VTK/matplotlib/shapely? Estimate size savings.
  4. **Bundle size reduction suggestions:** Specific changes to `quickice-gui.spec`:
     - Add to `excludes` list: packages that are never imported
     - Replace `collect_all()` with targeted `collect_submodules()` + `collect_data_files()` where possible
     - UPX compression status (Quick Task 023 investigated, QT 023 pending)
     - Suggest `--onefile` vs `--onedir` trade-offs
  5. **`scripts/assemble-dist.sh` review:** Check if the assembly script properly packages all necessary runtime files.
  
  Reference previous results: `20260612_portable_distribution.md`, `20260608_portable_distribution_analysis.md`, `.planning/codebase/CONCERNS.md` (BUNDLE-01 fixed, BUNDLE-02 deferred). Build on those findings with current code state.
  
  **DO NOT fix anything.** Report findings only.
- **Output file:** `.planning/code_analysis/20260615_portable_distribution.md`

---

## Dependency Graph

```
Batch 1 (4 agents, parallel):
  Agent 1.1 ─┐
  Agent 1.2 ─┤──→ STACK.md, INTEGRATIONS.md, ARCHITECTURE.md, STRUCTURE.md,
  Agent 1.3 ─┤    CONVENTIONS.md, TESTING.md, CONCERNS.md, flow_trace.md
  Agent 1.4 ─┘

Batch 2 (3 agents, parallel, no dependency on Batch 1):
  Agent 2.1 ───→ vulnerability_scan.md
  Agent 2.2 ───→ documentation_crosscheck_cli.md
  Agent 2.3 ───→ documentation_crosscheck_gui.md

Batch 3 (1 agent, depends on Batch 1 for updated STACK.md):
  Agent 3.1 ───→ portable_distribution.md
```

**Note:** Batches 1 and 2 CAN run concurrently if the 4-parallel limit is respected (4 from Batch 1 = max capacity, so Batch 2 must wait). However, if Batch 1 agents complete early, Batch 2 agents can start immediately without waiting for all of Batch 1.

**Optimal scheduling:** Start Batch 1 (4 agents). As each agent finishes, replace it with a Batch 2 agent (respecting 4-parallel limit). Start Batch 3 after Batch 1 is fully complete (needs updated STACK.md).

---

## Output File Registry

| Agent | Output Files |
|-------|-------------|
| 1.1 | `.planning/codebase/STACK.md`, `.planning/codebase/INTEGRATIONS.md` |
| 1.2 | `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md` |
| 1.3 | `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/TESTING.md` |
| 1.4 | `.planning/codebase/CONCERNS.md`, `.planning/code_analysis/20260615_gromacs_flow_trace.md` |
| 2.1 | `.planning/code_analysis/20260615_vulnerability_scan.md` |
| 2.2 | `.planning/code_analysis/20260615_documentation_crosscheck_cli.md` |
| 2.3 | `.planning/code_analysis/20260615_documentation_crosscheck_gui.md` |
| 3.1 | `.planning/code_analysis/20260615_portable_distribution.md` |

---

## SCANCODE_STATUS.md Update

After all agents complete, update `.planning/codebase/SCANCODE_STATUS.md` to reflect:
- Codebase mapping refreshed 2026-06-15 (post-Phase 37)
- Scancode items A–D re-run with new timestamped reports
- Update line counts and doc freshness dates

---

## Summary

| Metric | Value |
|--------|-------|
| **Total agents** | 8 |
| **Total batches** | 3 |
| **Max parallel** | 4 |
| **Codebase docs updated** | 7 (STACK, INTEGRATIONS, ARCHITECTURE, STRUCTURE, CONVENTIONS, TESTING, CONCERNS) |
| **Scancode reports produced** | 4 (flow trace, vulnerability scan, doc cross-check ×2, portable distribution) |
| **Total output files** | 11 (7 doc updates + 4 analysis reports) |
| **Estimated wall-clock** | ~45-55 minutes |
| **Read-only guarantee** | Yes — no code changes, only documentation/analysis updates |
