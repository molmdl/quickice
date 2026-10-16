---
phase: 031-lazify-genice2-imports-in-generator
plan: 01
subsystem: core
tags: [imports, genice2, lazy-imports, performance, tests]
requires: []
provides:
  - "GenIce2-light module import for quickice.structure_generation.generator"
  - "TestLazyGenIceImports permanent import-lightness guard"
affects: []
tech-stack:
  added: []
  patterns: ["In-method lazy imports placed once at method top before the try block (hydrate_generator.py:254-255 pattern)"]
key-files:
  created: []
  modified:
    - quickice/structure_generation/generator.py
    - tests/test_structure_generation.py
    - .planning/codebase/CONCERNS.md
decisions: []
duration: "~5 min"
completed: 2026-10-16
---

# Phase 031 Plan 01: Lazify GenIce2 Imports in Generator Summary

**One-liner:** Deferred `genice2.plugin.safe_import` / `genice2.genice.GenIce` imports from module top level into `IceStructureGenerator._generate_single`, pinned by a subprocess import-lightness guard — AGENTS.md Lazy Imports invariant now true code-wide.

## What Was Done

**Task 1: Lazify generator.py genice2 imports + add import-lightness guard test**
- Removed the two module-top-level genice2 imports at `generator.py:11-12` (plus one surrounding blank line), leaving `import time` / `import numpy as np` / quickice imports untouched.
- Inserted both imports once at the top of `IceStructureGenerator._generate_single` (directly after the method docstring, before the random-state `try` block), with a `custom_guest_bridge.py`-style lazy-import comment referencing quick-031.
- Pre-checked `tests/` for an existing import-lightness guard: none found (all `sys.modules` hits are custom-guest injection/cleanup tests) — proceeded with new test in `tests/test_structure_generation.py` as planned.
- Appended `TestLazyGenIceImports::test_module_import_does_not_load_genice2` at end of `tests/test_structure_generation.py` — subprocess probe asserts `genice2`/`genice2.*` absent from `sys.modules` after importing the module in a fresh interpreter.

**Task 2: Verification gate, atomic commits, CONCERNS.md resolution notes**
- Verification gate run before committing (results below).
- Commit 1 (code + guard test): `060e8d7f perf(core): defer genice2 imports in generator.py to first use`.
- Appended one-line RESOLVED notes with the code hash to both CONCERNS.md targets: the GenIce2 dependency entry's Resolution bullet (line 140) and the AGENTS.md-drift entry's Fix approach line item (c) (line 38). Historical Risk/Issue lines untouched; drift items (a) and (b) remain open.
- Commit 2 (docs): `76a1b9f3 docs(planning): mark genice2 lazy-import drift resolved in CONCERNS.md (quick-031)`.

## Verification Results (actual numbers)

| Check | Expected | Actual |
|-------|----------|--------|
| Focused set (`test_structure_generation.py` + `test_pbc_wrapping.py`) | 64 passed | **64 passed, 0 failed** (4.12s) |
| Guard test alone | 1 passed | **1 passed** (0.27s) |
| Full-suite `--collect-only` | 1850 tests | **1850 tests collected** (4.32s, 0 errors) |
| Smoke (`python -c` import probe) | prints `light` | **prints `light`** |
| `grep -nE "^(from|import) genice2" generator.py` | no matches | none (rc=1) |
| `grep -c "from genice2" generator.py` | 2 | 2 (both in-method) |
| `grep -n "quick-031" CONCERNS.md` | 2 hits with hash | 2 hits, both contain `060e8d7f` |
| `git status --short` | clean | clean |

Baseline before edit: 63 passed focused, 1849 collected — deltas exactly +1 as planned.

## Deviations from Plan

None — plan executed exactly as written. No bugs, missing functionality, or blockers encountered; no items triggered Rule 4.

## Commits

- `060e8d7f` — perf(core): defer genice2 imports in generator.py to first use
- `76a1b9f3` — docs(planning): mark genice2 lazy-import drift resolved in CONCERNS.md (quick-031)

## Out of Scope (untouched, per plan)

- `hydrate_generator.py` (already lazy), PEP 562 `_EXPORT_TO_MODULE` maps in `__init__.py`
- AGENTS.md itself (the invariant statement now simply holds)
- CONCERNS.md drift items (a) test-count and (b) TEST-06 pointer — remain open
- ROADMAP.md / STATE.md (orchestrator concern)
