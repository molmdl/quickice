---
status: resolved
trigger: "Investigate two GUI hydrate export bugs: (1) missing guest ITPs after lattice change without regeneration, (2) misleading mixed-guest export success dialog"
created: 2026-07-06T00:00:00Z
updated: 2026-07-06T11:10:00Z
---

## Current Focus

hypothesis: Issue 1 — export_hydrate drives ITP staging from config.cage_guest_assignments (NEW config after lattice change = empty) but .gro/.top content from structure.molecule_index (OLD mixed structure). Config/structure desync after lattice change (config rebuilt on _on_hydrate_config_changed, structure only updated on _on_hydrate_generation_complete) → empty ITP staging loop → only tip4p-ice.itp copied, but .top still #includes ch4_hydrate.itp + thf_hydrate.itp. Issue 2 — main_window.py:1718 hardcodes config.guest_type (single primary) as the label for total structure.guest_count, ignoring structure.guest_descriptors for mixed composition.
test: Read export_hydrate ITP staging loop + main_window export dialog + _on_hydrate_config_changed lifecycle; read gromacs_writer write_multi_molecule_top_file to see whether #include uses itp_files (passed) or MOLECULE_TO_GROMACS (hardcoded); read hydrate_panel.get_configuration to confirm lattice change empties cage_guest_assignments.
expecting: Confirm ITP staging loop iterates cage_guest_assignments (config-driven); confirm .top #include comes from itp_files dict (passed from staging); confirm dialog uses config.guest_type not guest_descriptors; confirm get_configuration rebuilds empty cage_guest_assignments when lattice changes.
next_action: Read write_multi_molecule_top_file + hydrate_panel.get_configuration; run baseline tests; write reproduction test.

## Symptoms

expected: After generating a mixed sI hydrate (CH4 in small + THF in large) and exporting, ALL referenced guest .itp files (ch4_hydrate.itp, thf_hydrate.itp, tip4p-ice.itp) should be copied to the output directory so grompp succeeds. The export success dialog should accurately describe the mixed guest composition (e.g. "1 CH4 + 6 THF" or similar), not mislabel all guests as the primary type.

actual:
- Issue 1 (functional): After generating mixed sI (CH4+THF) then changing lattice to sTprime WITHOUT regenerating, Export produces .top with #include ch4_hydrate.itp + thf_hydrate.itp (from stale structure.molecule_index) BUT those ITPs are NOT copied to output dir (config.cage_guest_assignments now empty for sTprime → ITP staging loop is a no-op). Only tip4p-ice.itp copied. .gro still has stale 46 SOL + 1 CH4 + 6 THF structure but filename says sTprime.
- Issue 2 (cosmetic): Export success dialog shows "Guests: 7 ch4" for a mixed (1 CH4 + 6 THF) hydrate — misleading. Counts total guests (7) but labels all as primary config.guest_type ("ch4").

errors: No runtime exception — export returns True but produces incomplete output (missing ITPs). grompp would fail downstream.

reproduction:
Issue 1:
1. GUI Hydrate tab, lattice "sI", Small=CH4 @60%, Large=THF @100%
2. Click Generate → mixed sI structure
3. Change lattice to "sTprime" WITHOUT clicking Generate (per-cage rows disappear; viewer still shows old sI structure)
4. Click Export → output dir has .top (with #include ch4+thf hydrate ITPs), .gro (stale 267 atoms), tip4p-ice.itp — but NO ch4_hydrate.itp or thf_hydrate.itp
Issue 2:
1. After step 2 above (generate mixed sI), click Export immediately
2. Read success dialog: "Guests: 7 ch4"

started:
- Issue 1: New in Phase 42 (plan 42-05 introduced cage_guest_assignments-driven ITP staging).
- Issue 2: Pre-existing dialog code; Phase 42 mixed occupancy makes it visibly wrong.

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-07-06T00:00:00Z
  checked: hydrate_export.py export_hydrate (lines 90-259)
  found: ITP staging loop at lines 161-206 iterates config.cage_guest_assignments.items(). For built-in guests, calls _get_hydrate_guest_itp_path(assignment.guest_type) and appends to custom_guest_itps (lines 204-206). Copy/transform loop at lines 243-249 writes one file per entry in custom_guest_itps. The .gro/.top writers (lines 214-233) are driven by structure.positions/structure.molecule_index (structure-side), NOT config.
  implication: If config.cage_guest_assignments is empty (after lattice change to water-only sTprime), the ITP staging loop body never executes → custom_guest_itps stays empty → no guest ITPs copied. CONFIRMED mechanism for Issue 1 (pending verification that .top #include uses itp_files not MOLECULE_TO_GROMACS).

- timestamp: 2026-07-06T00:00:00Z
  checked: main_window.py _on_hydrate_config_changed (line 732-734) + _on_hydrate_generation_complete (line 769-776) + _on_export_hydrate_gromacs (line 1686-1719)
  found: _on_hydrate_config_changed sets self._current_hydrate_config = self.hydrate_panel.get_configuration() but does NOT clear/invalidate self._current_hydrate_result. _on_hydrate_generation_complete sets self._current_hydrate_result = result (only on generation). Export reads both _current_hydrate_result (structure) and _current_hydrate_config (config) — they can be out of sync. Dialog line 1718: f"Guests: {structure.guest_count} {config.guest_type}" — uses structure.guest_count (total) but config.guest_type (primary single).
  implication: CONFIRMED config/structure desync lifecycle. CONFIRMED Issue 2 root cause (dialog uses config.guest_type not structure.guest_descriptors).

## Resolution

root_cause: export_hydrate drives ITP staging from config.cage_guest_assignments (empty after lattice change) but .gro/.top content from structure.molecule_index (stale mixed) — config/structure desync. Dialog uses config.guest_type (primary) instead of structure.guest_descriptors (per-type).
fix: ITP staging now driven by structure.molecule_index + guest_descriptors (what's in the structure); dialog uses guest_descriptors for per-type composition when mixed.
verification: pytest tests pass; new regression test proves ITPs staged from structure even when config empty.
files_changed: [quickice/gui/hydrate_export.py, quickice/gui/main_window.py, tests/test_output/test_gromacs_export_hydrate.py, tests/test_output/test_hydrate_export_dialog_label.py]
commits: [32ed9dc, d910fbd]
