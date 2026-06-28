# Research Summary: Data Flow Migration — Tabs to Integrated VTK GUI

**Domain:** GUI architecture migration (PySide6 + VTK)
**Researched:** 2026-06-28
**Overall confidence:** HIGH (source code analysis, not external references)

## Executive Summary

QuickIce's current GUI architecture stores pipeline state as 9 `_current_*` attributes directly on a 2126-line MainWindow class. Cross-tab data flows through MainWindow as a god-object mediator: every panel signals to MainWindow, which stores results, then pushes them to downstream panels. This pattern has ossified into a rigid coupling between UI layout (6 QTabWidget tabs) and data flow (linear Ice→Interface→Custom→Solute→Ion→Export pipeline).

The integrated VTK-centric redesign requires replacing both the layout (tabs → docks) AND the state model (scattered attributes → PipelineSession). These are **two independent migrations** that must be sequenced carefully: the PipelineSession can be introduced before the dock migration, but the dock migration is nearly impossible without PipelineSession.

The key architectural decision is that QuickIce's physical pipeline maps cleanly to OVITO's linear modifier stack: Generate Ice (Source) → Build Interface (Modifier 1) → Insert Custom Molecules (Modifier 2) → Insert Solutes (Modifier 3) → Insert Ions (Modifier 4). Steps cannot be reordered (physical constraints), but they can be toggled off. This is NOT a DAG — it's a strictly linear chain.

The CP-01 duck-typing "decision" is actually a non-issue for migration: all runtime-attribute-setting on InterfaceStructure is setting **existing dataclass fields** with defaults, not inventing new attributes. The PipelineSession simply formalizes this as typed step results.

## Key Findings

**Stack:** PipelineSession dataclass replaces 9 `_current_*` attributes; 4 concern-managers replace 2126-line MainWindow; no new libraries needed.
**Architecture:** OVITO-style linear modifier stack (Source + ordered Modifiers) — NOT a ParaView DAG. PipelineSession owns all step outputs and provides per-step export.
**Critical pitfall:** Decomposing MainWindow before extracting PipelineSession creates a distributed coupling problem — every extracted manager needs access to all 9 state attributes, reproducing the god-object across files.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **PipelineSession extraction (Phase 0)** — Introduce PipelineSession dataclass alongside existing `_current_*` attributes, with an adapter that reads from either. No GUI change.
   - Addresses: State model formalization, typed access to pipeline results
   - Avoids: Distributed coupling during MainWindow decomposition

2. **MainWindow decomposition (Phase 1)** — Extract 4 concern-managers (PipelineManager, ViewerManager, ExportManager, DockManager) that interact through PipelineSession, not through MainWindow.
   - Addresses: 2126-line class → 4 focused classes of ~300 lines each
   - Avoids: Circular dependencies between managers

3. **UnifiedViewerWidget (Phase 2)** — Replace 6 separate VTK viewers with 1 central widget using vtkAssembly groups. Still in tab containers.
   - Addresses: Multiple render windows, duplicated rendering code
   - Avoids: Breaking existing panel-to-viewer wiring

4. **QDockWidget migration (Phase 3)** — Replace QTabWidget with dock panels. PipelineSession already exists, so panels read from it instead of MainWindow.
   - Addresses: Tab-based workflow → integrated VTK-centric layout
   - Avoids: Rewiring signal/slot connections

5. **Tool mode system (Phase 4)** — Add toolbar + VTK interactor switching. Dock panels respond to active tool via PipelineManager.
   - Addresses: Context-dependent interaction modes
   - Avoids: Monolithic interactor style class

**Phase ordering rationale:**
- Phase 0 (PipelineSession) MUST come first: every subsequent phase depends on centralized state
- Phase 1 (decomposition) depends on Phase 0: managers need PipelineSession as their shared state
- Phase 2 (unified viewer) depends on Phase 1: ViewerManager must exist before rewiring viewers
- Phase 3 (docks) can partially parallel Phase 2: DockManager setup is independent of ViewerManager
- Phase 4 (tool modes) depends on Phase 3: toolbar/dock panels must exist before tool mode wiring

**Research flags for phases:**
- Phase 0: Low risk — adapter pattern enables incremental migration
- Phase 1: MEDIUM risk — decomposition must maintain test parity; no GUI tests exist yet
- Phase 2: MEDIUM risk — VTK rendering consolidation needs performance validation
- Phase 3: HIGH risk — dock layout migration touches every signal/slot connection; needs integration tests
- Phase 4: LOW risk — tool modes are additive, don't break existing flows

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new libraries; all from existing environment.yml |
| PipelineSession design | HIGH | Directly derived from 9 existing `_current_*` attributes and 6 structure types |
| Architecture (modifier stack) | HIGH | Maps 1:1 from existing linear pipeline; verified against CLI pipeline |
| CP-01 resolution | HIGH | Verified all duck-typed attributes are dataclass fields with defaults |
| Migration phases | MEDIUM | Ordering is sound but parallelization estimates may be optimistic |
| Coexistence (tabs+docks) | MEDIUM | Technically feasible but cost/benefit unclear |

## Gaps to Address

- No GUI test coverage exists — migration safety requires adding GUI integration tests before Phase 1
- Worker lifecycle in integrated model needs prototype validation (QThread + PipelineManager interaction)
- Export-per-step workflow needs UX design review (Option A vs B vs C from questions)
