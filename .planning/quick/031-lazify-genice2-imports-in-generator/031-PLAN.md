---
phase: 031-lazify-genice2-imports-in-generator
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/structure_generation/generator.py
  - tests/test_structure_generation.py
  - .planning/codebase/CONCERNS.md
autonomous: true

must_haves:
  truths:
    - "A fresh interpreter importing quickice.structure_generation.generator does NOT load genice2 into sys.modules"
    - "Real generation via _generate_single still works unchanged (63 pre-existing focused tests pass)"
    - "Every direct importer of IceStructureGenerator (tests/conftest.py:50, tests/e2e_export_helpers.py:16, 10+ test files) still imports the module successfully"
    - "The AGENTS.md Lazy Imports invariant (GenIce2 never at module top level) is true code-wide"
    - "CONCERNS.md GenIce2 dependency entry + AGENTS.md-drift entry (c) carry a dated resolution note with the commit hash"
  artifacts:
    - path: "quickice/structure_generation/generator.py"
      provides: "Lazy genice2 imports inside _generate_single (no module-top-level genice2)"
      contains: "def _generate_single"
    - path: "tests/test_structure_generation.py"
      provides: "TestLazyGenIceImports import-lightness guard test"
      contains: "TestLazyGenIceImports"
    - path: ".planning/codebase/CONCERNS.md"
      provides: "Resolution notes (GenIce2 entry + drift entry (c)) with commit hash"
      contains: "quick-031"
  key_links:
    - from: "quickice/structure_generation/generator.py::_generate_single"
      to: "genice2.plugin.safe_import + genice2.genice.GenIce"
      via: "in-method imports at method top (before the random-state try block)"
      pattern: "from genice2\\.(plugin|genice) import"
      note: "If missing, first generation call hits NameError on safe_import/GenIce — the 63 focused tests + new guard catch this. This is THE link that would break."
    - from: "tests/test_structure_generation.py::TestLazyGenIceImports"
      to: "submodule import in a fresh subprocess interpreter"
      via: "subprocess probe asserting 'genice2' not in sys.modules"
      pattern: "quickice\\.structure_generation\\.generator"
---

<objective>
Lazify the genice2 imports in `quickice/structure_generation/generator.py` — the LAST module-top-level genice2 import in the package — so the AGENTS.md Lazy Imports invariant ("PySide6, VTK, GenIce2 are imported inside function bodies — never at module top level") becomes true code-wide, and pin it with an import-lightness regression test.

Purpose: Today a direct `import quickice.structure_generation.generator` (done legitimately by `tests/conftest.py:50`, `tests/e2e_export_helpers.py:16`, and 10+ test files) loads the full genice2+networkx chain at import time. After this change, module import is light; import cost moves to first `_generate_single` call. DECIDED by user 2026-10-15 (recorded in `.planning/codebase/CONCERNS.md` GenIce2 entry).
Output: (1) lazified `generator.py`, (2) new `TestLazyGenIceImports` guard test, (3) two atomic commits, (4) CONCERNS.md resolution notes with commit hash.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@AGENTS.md
@quickice/structure_generation/generator.py
@tests/test_structure_generation.py
@.planning/codebase/CONCERNS.md

# Verified facts (independently verified 2026-10-15/16 — act on these, no re-research)

- `generator.py` is 265 lines. Module-top-level genice2 imports at `:11-12`:
  `from genice2.plugin import safe_import` / `from genice2.genice import GenIce`.
- ALL code uses are inside ONE method, `IceStructureGenerator._generate_single`:
  `safe_import('lattice', self.lattice_name)` at `:108`, `GenIce(...)` at `:111`,
  `safe_import('molecule', 'tip3p')` at `:119`, `safe_import('format', 'gromacs')` at `:122`.
  Every other `GenIce`/`safe_import` mention in the file is a docstring or comment (grep-verified).
  Confirmed: these are the ONLY module-top-level genice2 imports in `quickice/` — after this edit the invariant holds code-wide.
- In-repo lazy-import precedents to mirror:
  - `hydrate_generator.py:254-255` — imports placed once at method top, BEFORE the `try:`, with no special wrapper.
  - `custom_guest_bridge.py:130-131` — comment `# ... Lazy import per AGENTS.md (no top-level GenIce2).` directly above the import.
- No import-lightness regression test exists (grep-verified in `tests/`): all `sys.modules` guards are custom-guest injection/cleanup tests (`test_custom_guest_bridge.py`, e2e hydrate tests); `test_scancode_bugs_gui_ion.py` tests a worker's *internal* lazy call via mocks, not module-import lightness.
- Baselines measured 2026-10-16 before any edit:
  - `tests/test_structure_generation.py` + `tests/test_pbc_wrapping.py`: **63 passed** in ~4.5s.
  - Full-suite collection: **1849 tests** (`--collect-only`, 0 errors).
- `.planning/` IS git-tracked (docs commit is legitimate). Atomic commits only — NEVER `git add .` or `git add -A`.
- No behavior change intended — import timing only. One accepted semantic shift: if genice2 were missing, the ImportError moves from module-import time to the first `_generate_single` call. This matches the existing `hydrate_generator.py` pattern; genice2 is PINNED in `environment.yml`, so this never fires in practice. Do NOT "fix" this by wrapping the import in try/except.

# State/decision boundaries (do not revisit)
- Do NOT touch `hydrate_generator.py` (already lazy) or the PEP 562 `_EXPORT_TO_MODULE` maps in `__init__.py`.
- Do NOT change AGENTS.md — the invariant statement becomes true code-wide after this lands. Drift entries (a) test count and (b) TEST-06 pointer stay UNTOUCHED (out of scope).
</context>

<tasks>

<task type="auto">
  <name>Task 1: Lazify generator.py genice2 imports + add import-lightness guard test</name>
  <files>quickice/structure_generation/generator.py, tests/test_structure_generation.py</files>
  <action>
**Edits to `quickice/structure_generation/generator.py`:**

1. Delete the two module-top-level genice2 imports at `:11-12` AND one of the surrounding blank lines, so the import header reads exactly:
```python
import time

import numpy as np

from quickice.structure_generation.mapper import (
```
(Leave the `mapper`/`types`/`errors`/`gro_parser` imports untouched — they are lazy-safe.)

2. In `IceStructureGenerator._generate_single`, insert BOTH imports ONCE at method top — directly after the closing `'''` of the method docstring (after `:100`), BEFORE the existing `# Save global random state BEFORE try block...` comment (`:101`). NOT inside the `try`, NOT inside any loop — an ImportError must surface before the random state is touched. Mirror `custom_guest_bridge.py:130-131` comment style:
```python
        # Lazy import per AGENTS.md (no top-level GenIce2) — quick-031.
        # ONCE at method top, before the try block (like hydrate_generator.py:254-255).
        from genice2.plugin import safe_import
        from genice2.genice import GenIce
```
No other changes to the file.

**Pre-check for the guard test (satisfies the "grep for an existing lazy-import guard to mirror" step):**
Grep `tests/` for `sys.modules` AND `genice2` together. Planner already verified (2026-10-16): all hits are custom-guest injection/cleanup tests; NO test asserts module-import lightness. Expected result: nothing to mirror. If (unexpectedly) an import-lightness guard IS found, mirror its style in its file instead of adding to `tests/test_structure_generation.py` and note it in the summary.

**Then append this test class at the END of `tests/test_structure_generation.py` (after the last test method, line ~752):**
```python
class TestLazyGenIceImports:
    """Import-lightness guard: importing the generator module must not load GenIce2.

    RED-first evidence (quick-031, verified 2026-10-15): before the fix,
    ``quickice/structure_generation/generator.py:11-12`` imported
    ``genice2.plugin`` and ``genice2.genice`` at module top level, so a direct
    ``import quickice.structure_generation.generator`` (legitimate at
    ``tests/conftest.py:50``) pulled the full genice2+networkx chain into
    sys.modules. The fix defers both imports into
    ``IceStructureGenerator._generate_single``. This test FAILS on the
    pre-fix code and PASSES after (AGENTS.md Lazy Imports invariant).

    The assertion runs in a SUBPROCESS (fresh interpreter): sibling tests in
    this file legitimately load genice2 at generation time in the shared
    pytest process, so an in-process ``sys.modules`` check would be
    order-fragile. A fresh interpreter isolates the module import itself.
    """

    def test_module_import_does_not_load_genice2(self):
        """A fresh interpreter importing the module must NOT have genice2 in sys.modules."""
        import os
        import subprocess
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[1]
        probe = (
            "import sys; "
            "import quickice.structure_generation.generator; "
            "loaded = [m for m in sys.modules "
            "          if m == 'genice2' or m.startswith('genice2.')]; "
            "assert not loaded, f'genice2 loaded at import time: {loaded}'"
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = str(repo_root) + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(repo_root),
            env=env,
        )
        assert result.returncode == 0, (
            f"generator module import is not genice2-light "
            f"(rc={result.returncode}):\\nstdout: {result.stdout}\\nstderr: {result.stderr}"
        )
```
> Escape-code note: the `\\n` above becomes a literal backslash-n inside the quoted f-string — write the f-string exactly as shown (single backslash + n in the file), matching normal Python escape syntax.

Imports (`os`/`subprocess`/`sys`/`pathlib`) are inside the test method — matches the repo convention of function-body imports for test helpers (see `tests/conftest.py::run_quickice`).
  </action>
  <verify>
```bash
QT_QPA_PLATFORM=offscreen timeout 300 python -m pytest -q tests/test_structure_generation.py tests/test_pbc_wrapping.py
```
Expect: **64 passed, 0 failed** (63 pre-existing baseline + 1 new guard test). Also run the guard explicitly:
```bash
QT_QPA_PLATFORM=offscreen timeout 120 python -m pytest -q "tests/test_structure_generation.py::TestLazyGenIceImports::test_module_import_does_not_load_genice2"
```
Expect: 1 passed. Optional 5-second smoke mirroring the test:
```bash
timeout 60 python -c "import sys; import quickice.structure_generation.generator; assert 'genice2' not in sys.modules; print('light')"
```
Expect: prints `light`.
  </verify>
  <done>generator.py has zero module-top-level genice2 imports (grep `^(from|import) genice2` in the file returns nothing) and both imports present once in `_generate_single` (grep `from genice2` returns exactly the 2 in-method lines); new guard test passes; 63 pre-existing focused tests unaffected; `tests/conftest.py:50`-style direct imports still work (proven by the suite running at all).</done>
</task>

<task type="auto">
  <name>Task 2: Verification gate, atomic commits, CONCERNS.md resolution notes</name>
  <files>.planning/codebase/CONCERNS.md</files>
  <action>
**1. Verification gate (run BEFORE committing; report both counts in the summary):**
```bash
QT_QPA_PLATFORM=offscreen timeout 300 python -m pytest -q tests/test_structure_generation.py tests/test_pbc_wrapping.py
QT_QPA_PLATFORM=offscreen timeout 180 python -m pytest -q --collect-only 2>&1 | tail -1
```
Expect focused set: 64 passed / 0 failed. Expect collection line: `1850 tests collected` (1849 baseline + 1 new). Report BOTH numbers in the summary. If collect ≠ 1850, STOP and reconcile (an extra/missing test crept in) before committing.

**2. Atomic commit 1 (code + its guard test — one logical change):**
```bash
git add quickice/structure_generation/generator.py tests/test_structure_generation.py
git commit -m "perf(core): defer genice2 imports in generator.py to first use"
git rev-parse --short HEAD
```
Record the short hash (use it in the notes below).

**3. Append ONE-line resolution notes to `.planning/codebase/CONCERNS.md` (substitute {HASH} with the recorded commit hash):**

- In the GenIce2 dependency entry, append to the end of the `Resolution (DECIDED 2026-10-15, user)` bullet (currently the entry's last line, ~`:140`):
```
RESOLVED 2026-10-16 (quick-031, commit {HASH}): safe_import/GenIce deferred into `IceStructureGenerator._generate_single` (once, at method top, mirroring `hydrate_generator.py:254-255`); direct module import is now light — pinned by `tests/test_structure_generation.py::TestLazyGenIceImports`; AGENTS.md Lazy Imports invariant now true code-wide.
```
- In the AGENTS.md-drift entry, append to the end of the Fix approach line for item (c) (~`:38`):
```
(c) RESOLVED 2026-10-16 (quick-031, commit {HASH}) — generator.py:11-12 lazified; the Lazy Imports claim now holds code-wide. (Drift items (a) and (b) remain open, untouched.)
```
Append only — do NOT rewrite the historical Risk/Issue lines (they document state at discovery time; the dated RESOLVED note supersedes them).

**4. Atomic commit 2 (docs):**
```bash
git add .planning/codebase/CONCERNS.md
git commit -m "docs(planning): mark genice2 lazy-import drift resolved in CONCERNS.md (quick-031)"
```

AGENTS.md itself: UNCHANGED (the invariant statement is now simply true). Never `git add .` / `git add -A` — stage only the named files.
  </action>
  <verify>```bash
git log --oneline -2
git status --short
```
Expect: two commits on top (perf(core) + docs(planning)), and `git status` clean of the three intended files. Confirm the notes landed: `grep -n "quick-031" .planning/codebase/CONCERNS.md` shows 2 hits (GenIce2 entry + drift entry (c)), each containing the real commit hash.</verify>
  <done>Focused set 64/0 green; collect-only reports 1850 (named in summary); `git log` shows exactly two atomic commits; `git status` clean; CONCERNS.md carries both one-line RESOLVED notes with the code-commit hash and date 2026-10-16.</done>
</task>

</tasks>

<verification>
1. `grep -n "^(from|import) genice2" quickice/structure_generation/generator.py` → no matches (module-top-level imports gone).
2. `grep -c "from genice2" quickice/structure_generation/generator.py` → 2 (both in-method, both inside `_generate_single`).
3. `QT_QPA_PLATFORM=offscreen timeout 300 python -m pytest -q tests/test_structure_generation.py tests/test_pbc_wrapping.py` → 64 passed / 0 failed.
4. `QT_QPA_PLATFORM=offscreen timeout 180 python -m pytest -q --collect-only 2>&1 | tail -1` → `1850 tests collected` (report the count).
5. `git log --oneline -2` → perf(core) commit + docs(planning) commit; `git status` clean.
6. CONCERNS.md: 2 new `quick-031` RESOLVED notes containing the code-commit hash.
</verification>

<success_criteria>
- Importing `quickice.structure_generation.generator` in a fresh interpreter does not put `genice2` (or any `genice2.*` submodule) into `sys.modules` — enforced by the new permanent guard test.
- Real generation through `_generate_single` is unchanged: 63 pre-existing focused tests pass + new guard = 64.
- Full-suite collection is 1850 (was 1849), 0 collection errors.
- Zero top-level genice2 imports remain anywhere in `quickice/` — AGENTS.md Lazy Imports invariant true code-wide.
- Two atomic commits landed; CONCERNS.md GenIce2 entry + drift entry (c) marked RESOLVED with commit hash, dated 2026-10-16.
</success_criteria>

<output>
After completion, create `.planning/quick/031-lazify-genice2-imports-in-generator/031-SUMMARY.md` — include: focused-set pass count (expect 64), collect-only count (expect 1850), code commit hash, docs commit hash.
</output>
