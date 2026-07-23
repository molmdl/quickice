---
status: testing
phase: 45-e2e-hydrate-tab-workflow
source: [45-01-SUMMARY.md, 45-02-SUMMARY.md, 45-03-SUMMARY.md, 45-04-SUMMARY.md, 45-05-SUMMARY.md, 45-06-SUMMARY.md, 45-07-SUMMARY.md, 45-08-SUMMARY.md, 45-09-SUMMARY.md, 45-10-SUMMARY.md, 45-11-SUMMARY.md, 45-12-SUMMARY.md, 45-13-SUMMARY.md, 45-14-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T12:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: New lattice types produce grompp-valid output through Interface tab (GUI + CLI)
expected: |
  Generate hydrate structures with each new lattice type (sII, sH, c2te, ice1hte, sTprime,
  16, 17) and export through the Interface tab via both GUI and CLI paths. Run `gmx grompp`
  on each export. All should exit with return code 0 (valid GROMACS input). sH may be slow
  (~4480 guests) but should still complete successfully.
awaiting: user response

## Tests

### 1. New lattice types produce grompp-valid output through Interface tab (GUI + CLI)
expected: Generate hydrate structures with each new lattice type (sII, sH, c2te, ice1hte, sTprime, 16, 17) and export through the Interface tab via both GUI and CLI paths. Run `gmx grompp` on each export. All should exit with return code 0 (valid GROMACS input). sH may be slow (~4480 guests) but should still complete successfully.
result: [pending]

### 2. New lattice types pass grompp through FULL tab chain (GUI + CLI)
expected: For new lattice types (sII, c2te, ice1hte, 16), generate a hydrate and run the FULL tab chain: Interface → Solute → Custom → Ion → Export via both GUI (4 exporters) and CLI (3 branches). Run `gmx grompp` on each export. All should exit with return code 0, confirming the complete cross-tab pipeline works for these lattice types.
result: [pending]

### 3. Water-only lattices survive solute/ion insertion without crashing + grompp rc=0
expected: Generate water-only hydrate structures (sTprime, lattice 17) and proceed through the Solute and Ion tabs (inserting solutes/ions into the water structure). The structure should not crash during insertion. Export to GROMACS and run `gmx grompp` — return code 0. This verifies Pitfall 3 (water-only structures with no guests survive downstream processing).
result: [pending]

### 4. Triclinic lattices blocked at CLI interface step + GUI worker (e2e)
expected: Generate a triclinic hydrate (c0te or c1te) and attempt to use it as an interface template. Both the CLI _run_interface_step and the GUI worker should block the operation with a clear error message (e2e blocking, not just a validator check). The interface generation should not proceed.
result: [pending]

### 5. Triclinic hydrate-only export at 4x4x4 passes grompp (CLI + GUI)
expected: Generate a triclinic hydrate (c0te or c1te) at 4x4x4 supercell and export hydrate-only (not through the Interface tab) via both CLI and GUI paths. Run `gmx grompp` on the exported files. Should exit with return code 0. This verifies Pitfalls 1 and 6 (triclinic hydrate-only export works, only interface generation is blocked).
result: [pending]

### 6. Custom ethanol guest with non-sI lattices passes grompp (GUI + CLI)
expected: Generate hydrate structures with a custom ethanol guest on non-sI lattices (sII, c2te, ice1hte, 16). Export through the Interface tab via both GUI and CLI paths. Run `gmx grompp` on each export — return code 0. This verifies custom guests work with extended lattice types, not just sI.
result: [pending]

### 7. CLI --depol flag accepts strict/optimal with strict as default
expected: Run `python -m quickice --cli --hydrate-lattice sI --depol strict [other required flags]` — should generate with strict depol mode. Run with `--depol optimal` — should generate with optimal depol mode. Run without --depol — should default to strict. The --depol flag should accept only "strict" or "optimal" as values.
result: [pending]

### 8. Mixed built-in occupancy with new lattices passes grompp via GUI hydrate exporter
expected: Generate a mixed built-in occupancy hydrate (e.g. CH4 in small + THF in large cages) on new lattices (sII, 16). Export via the GUI hydrate exporter (HydrateGROMACSExporter.export_hydrate). Run `gmx grompp` on the exported files — return code 0. Also test filled-ice (c2te, ice1hte) single-cage-key hydrate export via GUI — grompp rc=0.
result: [pending]

## Summary

total: 8
passed: 0
issues: 0
pending: 8
skipped: 0

## Gaps

[none yet]
