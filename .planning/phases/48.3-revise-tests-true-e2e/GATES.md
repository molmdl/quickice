# Phase 48.3 — Canonical Gate Commands

Every 48.3 plan's verification section references these gate names **instead of redefining commands**. Run all gates from the project root with conda env `quickice` active. Commands are reproduced verbatim below; do not paraphrase or modify them in downstream plans.

## Baselines (committed in this directory, captured by 48.3-01)

| File | Provides |
| ---- | -------- |
| `baseline-before-count.txt` | Pre-phase collect summary line: `1890 tests collected` (plus `# gmx:` header comment) |
| `baseline-before-ids.txt` | 1890 full sorted test IDs (file path included) |
| `baseline-before-ids-stripped.txt` | 1890 path-stripped sorted test IDs (used by GATE-IDS so path changes don't false-positive) |
| `baseline-e2e-subset.txt` | GATE-SUBSET baseline: 414 passed in ~71s |
| `baseline-known-failures.md` | The single known pre-existing failure and the rule for counting it |

## Gates

### GATE-COUNT

```bash
python -m pytest --collect-only -q 2>/dev/null | tail -1
```

Compare to the expected count for the current plan stage. The pre-phase baseline is **1890** (see `baseline-before-count.txt`). Merge/delete plans state their expected delta in the plan; pure-reorg plans must keep the count unchanged. Collection must always finish with **0 errors** (48.2 constraint).

### GATE-IDS

```bash
python -m pytest --collect-only -q 2>/dev/null | grep "::" | sed 's|^[^:]*::||' | sort > /tmp/opencode/after-ids.txt && diff .planning/phases/48.3-revise-tests-true-e2e/baseline-before-ids-stripped.txt /tmp/opencode/after-ids.txt
```

- For **pure reorganization** plans: the diff must be **empty** (same test IDs, possibly different file locations).
- For **merge/delete** plans: the diff must contain **ONLY the explicitly removed IDs listed in that plan** — nothing else.
- The `sed 's|^[^:]*::||'` strips the file path so move/rename plans don't false-positive; class/test-name changes always show.

### GATE-SUBSET

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_e2e_*.py tests/test_gro_top_byte_equivalence.py -q
```

Baseline: **414 passed in ~71s** (see `baseline-e2e-subset.txt`). Expect exactly 1 known failure here only if a plan's selection adds `tests/test_entry_point.py` — see `baseline-known-failures.md` for the counting rule.

> **Path note:** after 48.3-21 lands, the glob becomes the grouped directory: `pytest tests/e2e/ tests/test_gro_top_byte_equivalence.py`. Plans executed after 48.3-21 must use the updated path.

### GATE-FULL (only valid after 48.3-03)

```bash
QT_QPA_PLATFORM=offscreen timeout 900 python -m pytest -q
```

- **Only valid after 48.3-03 fixes the deadlock** at `tests/test_custom_molecule_panel_34_6.py` (C-level VTK hang). Do NOT run a bare full suite before that fix lands.
- The `timeout 900` is an **external process timeout** — it MUST stay. NEVER rely on pytest-timeout alone: SIGALRM cannot interrupt C-level hangs (48.1-14 / 48.2-01 precedent: a full-suite attempt hung ~1 hour).
- Full-suite baseline is captured in 48.3-03 after its fix.

## GROMACS note

`gmx 2023.5` is on PATH in this env (`/data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx`), but `@gmx_skipif` still gates every grompp test so the suite stays green (skips, not failures) on machines without gmx.

## The rule

**Every 48.3 plan's verification section references these gate names (GATE-COUNT / GATE-IDS / GATE-SUBSET / GATE-FULL) instead of redefining commands.** This file is the single source of truth; if a command here is wrong, fix it here — never redefine a divergent copy downstream.
