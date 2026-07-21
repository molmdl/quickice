---
status: resolved
trigger: "interface-mixed-component-indexerror"
created: 2026-07-21T00:00:00Z
updated: 2026-07-21T00:03:00Z
---

## Current Focus

hypothesis: CONFIRMED - Mixed hydrate (guest_type_counts has >1 entry) takes only ONE guest type via `next(iter(guest_type_counts))`, then count_guest_atoms(guest_type="ch4") returns 5 for ALL guests including THF (13 atoms). The miscount desyncs the walking index i; eventually `range(i, i + guest_atoms)` produces index 728 on an array of size 728 (off-by-one out-of-bounds).
test: Reproduction script /tmp/opencode/repro_mixed_interface.py — mixed SII (ch4 small + thf large) candidate has positions.shape=(728,3), guest_type_counts={'ch4':16,'thf':8}, guest_atom_counts={'ch4':5,'thf':13}. All 3 modes fail at `candidate.positions[guest_indices]` with `index 728 is out of bounds for axis 0 with size 728`. Single SI all-ch4 (224 atoms) succeeds.
expecting: Fix by (1) detecting each guest molecule's type per-molecule when mixed (using guest_descriptors/guest_atom_counts dict + heuristic), and (2) clamping guest_indices.extend to end_idx (not i+guest_atoms) to prevent OOB.
next_action: Add identify_guest_type() to molecule_utils.py; thread guest_atom_counts dict + guest_descriptors through _detect_guest_atoms and _count_guest_molecules in all 3 modes; fix range(i, i+guest_atoms)→range(i, end_idx).

## Symptoms

expected: Interface generation should produce a hybrid structure (hydrate + liquid water) for the SII mixed-component hydrate (small cage methane 100%, large cage THF 100%), same as it works for SI hydrate with all methane 100%.
actual: GUI interface tab fails with `Unexpected error during slab mode generation: index 728 is out of bounds for axis 0 with size 728`. All three interface modes (slab/pocket/piece) fail with the SAME error.
errors: `Unexpected error during slab mode generation: index 728 is out of bounds for axis 0 with size 728` (numpy IndexError, index==size means off-by-one)
reproduction: GUI MainWindow → Interface tab → select slab/pocket/piece → generate. Source: SII hydrate, small cage methane 100%, large cage THF 100%. All three modes fail identically. Working: SI hydrate, all methane 100% (single-component).
started: Discovered during mixed-component hydrate support testing. Single-component path works, mixed-component path fails.

## Eliminated

(none yet)

## Evidence

- timestamp: initial
  checked: Grep for error string
  found: Error wrapped in quickice/structure_generation/interface_builder.py:373 `raise InterfaceGenerationError(f"Unexpected error during {config.mode} mode generation: {str(e)}", ...)` from a generic `except Exception as e` at line 370.
  implication: The real IndexError comes from inside assemble_slab/assemble_pocket/assemble_piece (called at lines 356-360). Since all three modes fail identically, the bug is in shared code they all call OR in the Candidate data they share.

- timestamp: initial
  checked: Previous resolved debug case crit-02-index-overflow.md
  found: Earlier bug was `ice_atom_count != ice_nmolecules * 3` invariant violation in water_filler.tile_structure, fixed by filtering at molecule boundaries. gromacs_writer.py uses `base_idx = iface.ice_atom_count + mol_idx * 4` for water loop.
  implication: There is an established invariant `ice_atom_count == ice_nmolecules * 3` for the ice portion. For HYDRATES with GUEST molecules, guest atoms are NOT 3 per molecule (methane=1 UA, THF=many atoms). If guest atoms are counted in ice_atom_count but ice_nmolecules only counts water, the invariant breaks.

## Resolution

root_cause: All three interface modes (slab.py:188, pocket.py:170, piece.py:209) extract only ONE guest type via `_guest_type = next(iter(guest_type_counts), None)`. For a mixed hydrate (guest_type_counts={'ch4':16,'thf':8}) this yields only 'ch4'. They then call `_detect_guest_atoms(..., guest_type='ch4')` which calls `count_guest_atoms(..., guest_type='ch4')`. In count_guest_atoms (molecule_utils.py:73-75), `guest_type=='ch4'` short-circuits and returns CH4_ATOMS_PER_MOLECULE=5 for EVERY guest molecule — including THF which actually has 13 atoms. This 5-vs-13 miscount desyncs the walking index `i` in _detect_guest_atoms. Compounding the bug, the guest branch at slab.py:83 / pocket.py:67 / piece.py:82 uses `guest_indices.extend(range(i, i + guest_atoms))` with the UNCLAMPED `i + guest_atoms` (end_idx = min(i+guest_atoms, len) is computed but only used for the has_ow check, NOT for the extend). When the desynced `i` lands at 724 (last value where i+4 <= 728), a 5-atom guest stride produces `range(724, 729)` which includes index 728 — out of bounds for candidate.positions of size 728. The single-guest path (SI all-ch4) works because count_guest_atoms(guest_type='ch4')=5 is CORRECT for every molecule, so no desync occurs. The asymmetry (mixed fails, single works) is fully explained: the single-guest case has a uniform 5-atom stride that matches reality; the mixed case has THF (13 atoms) miscounted as 5, accumulating a 2-atom-per-THF overshoot that eventually produces the OOB index. 728 = 136 water×4 + 16 ch4×5 + 8 thf×13 = 544+80+104.

fix: 
1. quickice/utils/molecule_utils.py: Added identify_guest_type() (detects guest mol_type from atom names via guest_descriptors exact-prefix match + heuristic) and separate_guests_by_type() (splits mixed guest atoms into per-type groups for separate tiling). Added `import numpy as np`.
2. quickice/structure_generation/modes/slab.py: _detect_guest_atoms + _count_guest_molecules gained guest_atom_counts dict + guest_descriptors params (backward-compatible None defaults). When is_mixed (len(guest_atom_counts)>1), identify_guest_type detects each molecule's type and looks up the count from the dict. Fixed range(i, i+guest_atoms)→range(i, end_idx) OOB clamp. assemble_slab call sites pass guest_atom_counts + guest_descriptors. Guest tiling section: mixed branch tiles each guest type SEPARATELY (ch4 with atoms_per_molecule=5, thf with 13), then concatenates bottom+top results. Single-guest branch unchanged.
3. quickice/structure_generation/modes/pocket.py: Same _detect_guest_atoms + _count_guest_molecules fixes. Guest tiling section: mixed branch tiles each type separately, removes per-type molecules inside the cavity, concatenates. Single-guest branch unchanged.
4. quickice/structure_generation/modes/piece.py: Same _detect_guest_atoms + _count_guest_molecules fixes. No mixed-guest tiling needed (piece translates guests as a block, no tile_structure call on guests).
5. tests/test_e2e_mixed_interface_generation.py: New regression test (7 tests) covering all 3 modes for mixed sII (ch4+thf) + single sI all-ch4 regression guard.

verification:
- Reproduction (/tmp/opencode/repro_mixed_interface.py): mixed SII (ch4+thf) all 3 modes now SUCCEED (slab guest_atoms=6624, pocket guest_atoms=8206, piece guest_atoms=184). Single SI all-CH4 slab still succeeds (guest_atoms=2560). ch4:thf ratio = 2:1 in all modes (matches 16:8 sII cage ratio). positions.shape matches len(atom_names) for all.
- New regression tests: 7/7 passed (test_e2e_mixed_interface_generation.py).
- Existing tests: 562 interface/slab/pocket/piece/hydrate tests passed. 59 guest_atom_counting + overlap_removal_invariants passed. 79 structure_generation + custom_guest_bridge passed. 15 e2e_custom_guest_hydrate + same_custom_two_cages passed. 11 mixed_cage_occupancy + mixed_lattice_gui + builtin_cross_tab_regression passed. 21 e2e_interface_generation passed. 22 e2e_hydrate_generation + sH_interface + same_custom + mixed_filled_ice passed. 128 test_cli/ + test_output/ passed. 17 e2e_lattice_cross_tab + builtin_cross_tab + triclinic + custom_guest_cli passed. 109 pocket/piece/interface/triclinic tests passed. 172 scancode_bugs + solute/ion tests passed (2 skipped). 117 workflow_chains + chain_export + cross_chain + custom + sH_cross_tab + sh_cage + custom_guest_cross_tab passed. 413 cli_pipeline + hydrate_config + gromacs + moleculetype + build_molecule_index + atom tests passed.
- 2 PRE-EXISTING failures (test_entry_point + test_cli_integration version string "4.5.0" vs "4.7.0") — confirmed unrelated to this fix (fail on original code without changes via git stash).

files_changed:
- quickice/utils/molecule_utils.py
- quickice/structure_generation/modes/slab.py
- quickice/structure_generation/modes/pocket.py
- quickice/structure_generation/modes/piece.py
- tests/test_e2e_mixed_interface_generation.py (new)
