---
status: resolved
trigger: "SII mixed hydrate GUI export chain regression — prior fixes work in pytest but NOT in GUI export path. 3 regression bugs despite commits b990d151, 29085047, 0421c1e0."
created: 2026-08-06T00:00:00Z
updated: 2026-08-06T12:00:00Z
---

## Current Focus

hypothesis: CONFIRMED and FIXED. All 3 remaining bugs resolved.
test: repro script + grompp + 680+ regression tests.
expecting: All 3 issues pass grompp rc=0; no test regressions.
next_action: Report results to user (do NOT commit — leave for review).

## Symptoms

expected:
1. Full chain SII mixed (CH4 small + THF large) -> slab -> custom mol (etoh) -> solute (ch4) -> ion should export GROMACS files that pass `gmx grompp`.
2. 3D viewer in custom mol / solute / ion tabs should render THF WITH bonds (correct topology).
3. ch4+thf hydrate slab export should pass grompp.
4. custom mol full chain export should pass grompp.

actual:
1. Full chain export FAILS with QuickIce error: `Failed: No hydrate .itp file found for guest type: h2` — but the guest is THF, NOT h2. (Export itself fails, not grompp.)
2. 3D viewer renders THF WITHOUT bonds in custom mol / solute / ion tabs.
3. ch4+thf hydrate slab export succeeds but grompp FAILS: coordinate file 38136 != topology 35832 (diff 2304 = THF atoms mislabeled as CH4_H).
4. custom mol full chain export succeeds but grompp FAILS: coordinate file 34763 != topology 37355 (diff 2592 = 864×3, the old MOL_H 6-atom fragmentation).

errors:
- Issue 1: `Failed: No hydrate .itp file found for guest type: h2` (quickice/output/guest_info.py:80, quickice/gui/export.py:1118, quickice/gui/hydrate_export.py:75)
- Issue 3 grompp: coordinate file 38136 != topology 35832 (diff 2304 = THF mislabeled as CH4_H)
- Issue 4 grompp: coordinate file 34763 != topology 37355 (diff 2592 = 864×3, MOL_H 6-atom fragmentation)

reproduction:
- Issue 1: GUI SII mixed -> slab -> custom mol (etoh) -> solute (ch4) -> ion -> Export from ion tab. FAILS "h2".
- Issue 3: GUI SII mixed (CH4+THF) -> slab -> Export from interface tab. Files tmp/SII-ch4-thf_slab/.
- Issue 4: GUI SII (CH4 + custom mol large) -> slab -> custom mol (etoh) -> solute (ch4) -> ion -> Export. Files tmp/SII-ch4-mol_slab_etohL_ch4L_ion/.

started: 2026-08-06 (after fixes committed 2026-08-05)

## Eliminated

<!-- APPEND only -->

## Evidence

<!-- APPEND only -->

- timestamp: 2026-08-06T00:30:00Z
  checked: Reproduction script tests/repro_sii_mixed_gui_regression.py mimicking EXACT GUI flow.
  found: |
    ISSUE 3 (mixed built-in CH4+THF slab interface export):
      - slab correctly sets guest_descriptors + guest_atom_counts ({ch4:5, thf:13}).
      - interface_writer built-in branch (line 398) uses detect_guest_type_from_atoms on WHOLE guest region -> single type "ch4" -> ALL 1296 guests labeled CH4_H (864×5 + 432×13). THF mislabeled.
      - .top declares only CH4_H, #includes only ch4_hydrate.itp. grompp rc=1 FAIL.
      - The 0421c1e0 mixed fix is GATED by `if custom_guest_info:` (line 250) — for pure built-in CH4+THF, custom_guest_info is None -> mixed code NEVER activates.
    ISSUE 1 (full chain CH4+THF + custom mol + solute + ion, "h2" error):
      - [slab] guest_descriptors populated, guest_atom_counts={ch4:5, thf:13}.
      - [after custom_molecule_inserter] guest_descriptors=[], guest_atom_counts={} — DROPPED.
      - [after solute_inserter] guest_descriptors=[], guest_atom_counts={} — DROPPED.
      - [ion_struct] cage-guest mol_types: {'guest': 1296} — iter_guest_molecules walk FAILED (no descriptors) -> fallback to uniform "guest".
      - _stage_hydrate_guest_itps built-in path: _detect_builtin_guest_types walks molecule_index -> all "guest" -> detect_guest_type_from_atoms on misaligned slices -> some slice all-H -> "h2" -> FileNotFoundError "No hydrate .itp file found for guest type: h2".
    ISSUE 4 (full chain CH4+custom_ethanol_cage + custom mol + solute + ion):
      - Same: guest_descriptors/guest_atom_counts DROPPED after custom + solute inserters.
      - ion_struct cage-guest mol_types: {'guest': 1296} (fallback).
      - .gro MOL_H: 1296 mols × 6 atoms = 7776 (6-atom fragmentation, stride = floor avg = 6). multiset {C:1632,H:5760,O:384} = mixed CH4+ethanol chunked at stride 6.
      - .top declares MOL_H 1296, #includes etoh.itp (9 atoms). grompp rc=1 FAIL (expects 1296×9=11664, gets 7776).
  implication: |
    ROOT CAUSES CONFIRMED:
    - Issue 3: interface_writer.py built-in branch (line 398-446) uses single detect_guest_type_from_atoms for ALL guests. Fix: detect mixed built-in via guest_atom_counts (2+ built-in types) and walk per-molecule via iter_guest_molecules (descriptor-driven), mirroring the custom mixed branch.
    - Issue 1 & 4 (SAME root cause): custom_molecule_inserter.py:547 and solute_inserter.py:528,694 create NEW InterfaceStructure WITHOUT guest_descriptors/guest_atom_counts (default to empty). The ion inserter's iter_guest_molecules walk then fails -> fallback to uniform "guest" with wrong stride. Fix: preserve guest_descriptors + guest_atom_counts when creating new InterfaceStructure.

## Resolution

root_cause: |
  3 root causes (all confirmed + fixed):
  
  Issue 3 (mixed built-in CH4+THF slab ITP staging): guest_info.py
  _stage_hydrate_guest_itps built-in path called _detect_builtin_guest_types
  FIRST (structure-based). For the interface slab, molecule_index is EMPTY
  and detect_guest_type_from_atoms returns a SINGLE type (ch4) for the whole
  guest region. The config fallback was gated by `if not guest_types:` — since
  ch4 was detected, thf was never staged from config -> thf_hydrate.itp missing
  -> grompp "include file not found".
  
  Issues 1 & 4 (SAME root cause — wrong molecule_index stride): 
  custom_molecule_inserter built the guest portion of molecule_index using the
  uniform floor-of-average stride `guest_atom_count // guest_nmolecules`
  (9936//1296=7 for CH4+THF, 7776//1296=6 for CH4+ethanol). This created 1296
  generic "guest" entries with count=7 (or 6), misaligning every per-molecule
  slice. The wrong molecule_index propagated through solute_inserter (which
  copied "guest" entries verbatim, filtering mol_type=="guest") to
  ion_inserter (which skipped its correct _build_molecule_index_from_structure
  rebuild because molecule_index was non-empty). At export, misaligned 7-atom
  slices caused detect_guest_type_from_atoms to misidentify some all-H slices
  as "h2" (Issue 1) and 6-atom MOL_H fragmentation (Issue 4).

fix: |
  4 files changed (3 from first agent kept + 4 new/extended by this agent):
  
  1. quickice/output/guest_info.py (Issue 3): _stage_hydrate_guest_itps
     built-in path now stages built-in types from hydrate_config.
     cage_guest_assignments FIRST (authoritative source), with structure
     detection as fallback ONLY when config is None. Mirrors the custom-mixed
     path. Fix: both ch4_hydrate.itp AND thf_hydrate.itp are now staged.
  
  2. quickice/structure_generation/custom_molecule_inserter.py (Issues 1&4):
     Added _build_guest_molecule_entries helper mirroring ion_inserter's
     _build_molecule_index_from_structure guest section. All 3 BUILD sites
     (lines ~536, ~813, ~1023) now use iter_guest_molecules with preserved
     guest_descriptors + guest_atom_counts to build per-molecule entries with
     CORRECT mol_type (ch4/thf/etoh_mix) and count (5/13/9), guarded by
     len==nmols and sum==atom_count (falls back to uniform stride when guard
     fails — byte-identical for single-guest no-descriptor path). All 3 COPY
     filters changed from `mol_type == "guest"` to `mol_type not in
     _NON_GUEST_MOL_TYPES` to pass specific types through. (First agent's
     descriptor-preservation fix kept.)
  
  3. quickice/structure_generation/solute_inserter.py (Issues 1&4): COPY
     filter (line 672) changed from `mol_type == "guest"` to `mol_type not in
     _NON_GUEST_MOL_TYPES` so specific cage-guest types survive solute
     insertion. Last-resort _resolve_guest_nmolecules count (line 126) also
     fixed. (First agent's descriptor-preservation fix kept.)
  
  4. quickice/output/custom_writer.py (NEW — needed because custom_molecule
     inserter now produces specific mol_types): GRO + TOP writers updated to
     recognize ALL cage-guest mol_types (generic "guest" + specific built-in
     ch4/thf/co2/h2 + custom slug etoh_mix/etoh_e2e) via _NON_GUEST_MOL_TYPES
     exclusion. GRO writer's guest residue name resolution now uses
     get_hydrate_guest_residue_name(mol.mol_type) for specific built-in types
     (reliable — avoids detect_guest_type_from_atoms which misidentifies
     custom ethanol as ch4/thf). TOP writer's guest_count and guest type
     detection also fixed. Mirrors ion_writer/solute_writer pattern.
  
  (First agent's interface_writer.py mixed-built-in fix kept unchanged.)

verification: |
  Repro script (tests/repro_sii_mixed_gui_regression.py) + grompp:
    - Issue 3: .gro CH4_H=864(5atom), THF_H=432(13atom); .top includes BOTH
      ch4_hydrate.itp + thf_hydrate.itp; gmx grompp rc=0 ✓
    - Issue 1: cage-guest mol_types {'ch4':864, 'thf':432}; "h2" error GONE;
      gmx grompp rc=0 ✓
    - Issue 4: .gro MOL_H=432(9atom, no 6-atom fragmentation); CH4_H=864;
      .top [molecules] correct; gmx grompp rc=0 ✓
  
  Regression tests (all PASS, zero failures):
    - 33 targeted e2e (mixed_cage, cross_tab_gui, mixed_ion_export, custom_guest_hydrate)
    - 400 broad e2e sweep (all test_e2e_*.py)
    - 138 unit/scancode (scancode_bugs, custom_molecule, solute, ion, structure, gro_resname, itp)
    - 142 additional e2e (custom_molecule, solute_export, ion_export, ion_insertion, solute_insertion, mixed_interface, builtin_cross_tab, gmx_validation)
    Total: 713 tests passed, 0 failed, 4 skipped (GROMACS-dependent)

files_changed:
  - quickice/output/guest_info.py (Issue 3 ITP staging)
  - quickice/structure_generation/custom_molecule_inserter.py (Issues 1&4 iter_guest_molecules + COPY filters + descriptor preservation)
  - quickice/structure_generation/solute_inserter.py (Issues 1&4 COPY filter + descriptor preservation)
  - quickice/output/custom_writer.py (NEW: cage-guest mol_type recognition)
  - quickice/output/interface_writer.py (first agent: mixed built-in GRO+TOP)
