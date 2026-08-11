---
status: resolved
trigger: "THF cage guests render WITH bonds in Hydrate tab but WITHOUT bonds in Custom Molecule / Solute / Ion tabs. Prior fix (solute_renderer.py MW index mapping) did not fix it. Recent export fixes (b278a9ed, ae743f37) may or may not have auto-resolved it."
created: 2026-08-11T00:00:00Z
updated: 2026-08-11T01:00:00Z
---

## Current Focus

hypothesis: The Custom/Solute/Ion tabs use vtk_utils.interface_to_vtk_molecules which builds ONE guest_mol for ALL guests and walks iface.molecule_index for bond detection. Need to verify whether the new (post-fix) molecule_index with per-molecule ch4(thf) entries produces correct bonds, OR if there's a separate rendering bug (e.g., guest actor not rendering bonds, or wrong structure passed).
test: Trace interface_to_vtk_molecules bond loop with the new molecule_index shape; compare with working hydrate_renderer guest approach.
expecting: Either bonds are now detected (auto-resolved) or identify the remaining divergence.
next_action: Read hydrate_renderer guest actor code + viewer guest actor code; write repro to inspect bond counts.

## Symptoms

expected: In ALL GUI tabs (Hydrate, Custom Molecule, Solute, Ion), THF cage guest molecules render with correct bonds (C-C, C-O, C-H visible as sticks). Hydrate tab ALREADY works.
actual: In Custom Molecule, Solute, Ion tabs, THF cage guests render as DISCRETE ATOMS ONLY (no bond sticks). Hydrate tab works.
errors: No error messages — bonds simply don't appear.
reproduction: GUI: generate SII mixed (small 100% CH4, large 100% THF) -> slab -> Custom Molecule tab -> observe THF guests in hydrate layer have no bonds. Compare with Hydrate tab.
started: Persisted after prior THF_ION_SOLUTE_FIX_SUMMARY.md fix AND after just-committed export fixes (b278a9ed, ae743f37).

## Eliminated

- hypothesis: solute_renderer.py MW index mapping is the cause of cage-guest bond loss in Custom/Solute/Ion tabs
  evidence: The prior fix (THF_ION_SOLUTE_FIX_SUMMARY.md) targeted solute_renderer.py which renders LIQUID-PHASE solutes, NOT cage guests. The failing tabs render cage guests via vtk_utils.interface_to_vtk_molecules, a different code path. So the prior fix addressed a different problem.
  timestamp: 2026-08-11T00:01:00Z

## Evidence

- timestamp: 2026-08-11T00:00:30Z
  checked: git log for recent commits
  found: Recent commits b278a9ed (Issue 3 slab), ae743f37 (Issues 1&4 full chain — preserve per-molecule cage-guest mol_type). These changed molecule_index to have per-molecule ch4(thf)/thf entries with correct counts (5/13) instead of generic "guest" stride-7.
  implication: The viewer's bond loop (vtk_utils.py:606-633) walks molecule_index; with correct 13-atom thf entries it MAY now detect bonds. Need to verify.

- timestamp: 2026-08-11T00:01:30Z
  checked: vtk_utils.py:447-686 interface_to_vtk_molecules bond detection
  found: Bond loop at 606-633 iterates iface.molecule_index, skips only mol.mol_type=="water", then for entries within guest range [guest_start, guest_end] adds distance-based bonds (< 0.16nm) within [mol_start, mol_end]. Uses guest_indices[i] which maps directly (no skipping for guests).
  implication: If molecule_index has correct thf entries (count=13, start_idx in guest range), bonds SHOULD be detected. Verify the actual molecule_index shape passed to the viewers.

## Resolution

root_cause: SEPARATE viewer rendering bug (NOT auto-resolved by export fixes b278a9ed/ae743f37).
  The slab mode (modes/slab.py:834) builds the InterfaceStructure WITHOUT populating
  molecule_index (defaults to empty list []). The export fixes added guest_descriptors
  and guest_atom_counts but NOT molecule_index. So interface_to_vtk_molecules
  (vtk_utils.py:599 `if guest_indices and iface.molecule_index:`) is FALSE → falls
  to the fragile heuristic fallback (_count_guest_atoms_for_rendering, line 636).
  The heuristic's "O"-first (THF) branch stops ONLY at the next "O"/"OW" (line 732),
  NOT at "C" (CH4). At THF→CH4 tile boundaries (1 per SII mixed slab), the heuristic
  over-counts THF as 15 (13 THF + 2 CH4 atoms), then destroys the following CH4
  (split into fake "H2"=2 + single H=1). Result: 2291 bonds vs correct 2688
  (256 CH4×4 + 128 THF×13). The Hydrate tab works because hydrate_renderer.create_guest_actor
  uses the HydrateStructure's POPULATED molecule_index (hydrate_generator.py:756).
fix: Build per-molecule guest boundaries from guest_descriptors (atom_labels matching)
  in interface_to_vtk_molecules when molecule_index is empty. Mirrors the working
  hydrate_renderer per-molecule approach. Single-point fix in vtk_utils.py fixes all
  3 tabs (custom/solute/ion) since they all call this central function.
verification: VERIFIED.
  - Repro (tests/repro_thf_bonds_viewer.py): guest bonds 2291 (broken) -> 2688 (fixed).
    2688 = 256 CH4*4 + 128 THF*13 (5 ring + 8 C-H), the exact correct count.
  - All 3 failing tabs pass the slab interface (empty molecule_index, populated
    guest_descriptors) to interface_to_vtk_molecules -> now use the descriptor path:
      * Custom Molecule tab (custom_molecule_viewer.py:369,440): slab interface -> 2688 bonds
      * Solute tab (solute_viewer.py:387): solute.interface_structure -> 2688 bonds
        (guest_descriptors carries through solute insertion: 2 entries preserved)
      * Ion tab (ion_viewer.py:265 via set_interface_structure): interface passed
        to ion_viewer is _current_interface_result (or solute.interface_structure),
        NOT the IonStructure -> 2688 bonds. (The IonStructure's separate
        set_ion_structure renders only the ions, not cage guests.)
  - Hydrate tab unaffected (uses hydrate_renderer.create_guest_actor with the
    HydrateStructure's populated molecule_index -- different code path).
  - Backward compat: structures with neither molecule_index nor guest_descriptors
    still use the heuristic fallback (case 3). Unit test pins this.
  - Tests: tests/test_thf_bonds_viewer_issue2.py 6/6 passed (4 unit + 2 integration).
    e2e suite 400 passed. viewer/renderer/vtk 70 passed. Broad keyword suite
    812 passed. No regressions.
files_changed:
  - quickice/gui/vtk_utils.py: added _build_guest_molecule_boundaries helper
    (molecule_index -> guest_descriptors -> heuristic resolution); rewrote the
    guest bond-detection block in interface_to_vtk_molecules to use it (unified
    the two-branch if/elif into one loop).
  - tests/repro_thf_bonds_viewer.py: new repro script (heuristic + real slab).
  - tests/test_thf_bonds_viewer_issue2.py: new regression test (6 tests).
  - .planning/debug/thf-bonds-viewer-issue2.md: this debug session.
