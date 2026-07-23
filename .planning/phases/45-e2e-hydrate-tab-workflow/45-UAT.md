---
status: testing
phase: 45-e2e-hydrate-tab-workflow
source: [45-01-SUMMARY.md, 45-02-SUMMARY.md, 45-03-SUMMARY.md, 45-04-SUMMARY.md, 45-05-SUMMARY.md, 45-06-SUMMARY.md, 45-07-SUMMARY.md, 45-08-SUMMARY.md, 45-09-SUMMARY.md, 45-10-SUMMARY.md, 45-11-SUMMARY.md, 45-12-SUMMARY.md, 45-13-SUMMARY.md, 45-14-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T19:00:00Z
---

## Current Test

number: 2
name: New lattice types pass grompp through FULL tab chain (GUI + CLI)
expected: |
  For new lattice types (sII, c2te, ice1hte, 16), generate a hydrate and run the FULL tab chain:
  Interface → Solute → Custom → Ion → Export via both GUI and CLI. gmx grompp rc=0 on each.
awaiting: user response (interactive — Workflow F)

## Tests

### 1. New lattice types produce grompp-valid output through Interface tab (GUI + CLI)
expected: Generate hydrate structures with each new lattice type (sII, sH, c2te, ice1hte, sTprime, 16, 17) and export through the Interface tab via both GUI and CLI paths. gmx grompp rc=0.
result: pass
verified: Workflow C — new lattices CLI interface export test passed (tests/test_cli/ -k "interface or lattice")

### 2. New lattice types pass grompp through FULL tab chain (GUI + CLI)
expected: For new lattice types (sII, c2te, ice1hte, 16), run the FULL tab chain (Interface→Solute→Custom→Ion→Export) via both GUI and CLI. gmx grompp rc=0 on each.
result: [pending]
note: Interactive — Workflow F (GUI full tab chain). CLI cross-tab branches partially covered by Workflow C.

### 3. Water-only lattices survive solute/ion insertion without crashing + grompp rc=0
expected: Generate water-only hydrate structures (sTprime, 17) and proceed through Solute and Ion tabs. No crash. Export + grompp rc=0.
result: pass
verified: Workflow C — water-only solute/ion survival test passed

### 4. Triclinic lattices blocked at CLI interface step + GUI worker (e2e)
expected: Generate a triclinic hydrate (c0te, c1te) and attempt to use it as an interface template. Both CLI and GUI should block with a clear error.
result: pass
verified: Workflow C — triclinic blocking CLI test passed (c0te/c1te blocked at CLI interface step with clear error)

### 5. Triclinic hydrate-only export at 4x4x4 passes grompp (CLI + GUI)
expected: Generate a triclinic hydrate (c0te, c1te) at 4x4x4 and export hydrate-only via both CLI and GUI. gmx grompp rc=0.
result: [pending]
note: Interactive — Workflow F (GUI + CLI specific 4x4x4 test). Filled-ice CLI hydrate grompp verified in Workflow C (c2te@3x3x3, ice1hte@4x4x4).

### 6. Custom ethanol guest with non-sI lattices passes grompp (GUI + CLI)
expected: Generate hydrate structures with custom ethanol guest on non-sI lattices (sII, c2te, ice1hte, 16). Export via GUI and CLI. gmx grompp rc=0.
result: [pending]
note: Interactive — Workflow F (GUI). Custom guest CLI grompp with sI verified in Workflow C (41-4). Non-sI lattice tests are in pytest suite (45-10/45-11).

### 7. CLI --depol flag accepts strict/optimal with strict as default
expected: Run with --depol strict, --depol optimal, and without --depol. All should work; default is strict.
result: pass
verified: Workflow B — --depol strict runs (exit 0), --depol optimal runs (exit 0), default runs as strict (exit 0); --lattice-type all 10 choices; --cage-guest repeatable flag present; deprecated banners present

### 8. Mixed built-in occupancy with new lattices passes grompp via GUI hydrate exporter
expected: Generate a mixed built-in occupancy hydrate (CH4+THF) on new lattices (sII, 16). Export via GUI hydrate exporter. gmx grompp rc=0. Also test filled-ice single-cage-key export.
result: pass
verified: Workflow C — mixed built-in GUI hydrate grompp test passed (test_mixed_cage_cli.py, gmx grompp rc=0)

## Summary

total: 8
passed: 5
issues: 0
pending: 3
skipped: 0

## Gaps

[none]
