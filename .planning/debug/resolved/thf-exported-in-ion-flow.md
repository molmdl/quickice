---
status: resolved
trigger: "thf-exported-in-ion-flow: after the mixed-component interface fix, exporting the slab-interface + ion structure to tmp/SII_mixed_ion/ shows THF being exported (misclassified/misrouted)."
created: 2026-07-22T00:00:00Z
updated: 2026-07-22T00:45:00Z
---

## Current Focus

hypothesis: CONFIRMED - Mixed hydrate (CH4=5 atoms + THF=13 atoms per molecule) hits a
SINGLE-uniform-guest-atom-count assumption in 4 places. The ion inserter computes
`guest_atom_count // guest_mols` = 6624//864 = 7 and assigns count=7 to ALL 864 guest
molecule_index entries, corrupting every guest slice. The export writers + ITP staging
also assume ONE guest type (detect only the first guest), so THF is mislabeled/mangled
and thf_hydrate.itp is never staged.

test: Inspect tmp/SII_mixed_ion/ export output + read ion_inserter.py / ion_writer.py /
guest_info.py / _guest.py. Then write a regression test that generates mixed SII ->
slab interface -> ion -> export and asserts correct CH4_H (576x5) + THF_H (288x13)
residues + both .itp staged + [molecules] run-length encoded.

expecting: After fix, .gro has only SOL/CH4_H/THF_H/NA/CL resnames (no GUE/H2_H),
total guest atoms = 6624 (none dropped), .top #includes both ch4_hydrate.itp +
thf_hydrate.itp and [molecules] lists CH4_H + THF_H runs matching .gro order.

next_action: Implement fix in 6 files + regression test, then verify.

## Symptoms

expected: Exporting slab-interface (mixed SII: small cage CH4 100% + large cage THF 100%)
after the ion step to tmp/SII_mixed_ion/ should produce output with water + ions + the
hydrate cage guests represented correctly: CH4 as CH4_H (5 atoms each) and THF as THF_H
(13 atoms each), each with its own _hydrate.itp included and listed in [molecules].

actual: Exported output contains THF but MANGLED. .gro has residues of 7 atoms each with
rotating resnames CH4_H / GUE / H2_H / THF_H (a THF molecule's O/CA atoms even appear
under a CH4_H residue). .top lists only `CH4_H 864` and #includes only ch4_hydrate.itp
(NO thf_hydrate.itp). 576 guest atoms are silently dropped (864x7=6048 written vs 6624
actual).

errors: No crash - correctness bug. Output is produced but is structurally invalid
(grompp would fail: THF_H atoms in .gro undefined in .top; resname GUE/H2_H undefined;
576 atoms missing).

reproduction: GUI: Tab0 SII mixed (CH4 small 100% + THF large 100%) -> Tab2 slab
interface -> Tab5 ion -> Ctrl-S to tmp/SII_mixed_ion/. Inspect .gro/.top. THF present
but mangled; thf_hydrate.itp missing.

started: Discovered immediately after the prior interface-mixed-component-indexerror fix.
Interface GENERATION now works; this bug is in the DOWNSTREAM ion -> export flow.

## Evidence

- timestamp: initial
  checked: ls tmp/SII_mixed_ion/ + read .gro/.top/.itp
  found: Files: ch4_hydrate.itp, ion.itp, ions_27na_27cl.gro, ions_27na_27cl.top,
  tip4p-ice.itp. NO thf_hydrate.itp. .top [molecules] = SOL 7825, CH4_H 864, NA 27,
  CL 27 (only CH4_H, only ch4_hydrate.itp #included). .gro has 37402 atoms.
  implication: The export treats ALL 864 guests as a single type (CH4); THF is not
  declared in the topology at all.

- timestamp: initial
  checked: Per-residue parse of ions_27na_27cl.gro (resid, resname, natoms)
  found: Guest region = 864 residues, EACH 7 atoms. resnames: CH4_H(412 residues),
  GUE(141), H2_H(208), THF_H(103). Total guest atoms written = 6048. A residue labeled
  CH4_H (resid 8031) contains atoms C,H,H,H,H,O,CA - i.e. a CH4(5) + start of a THF(13)
  chunked together. "GUE" = fallback resname (ion_writer.py:372), "H2_H" = h2 hydrate name
  (_guest.py:154) - both from misidentification on wrong-sized slices.
  implication: Every guest molecule_index entry has count=7 (= 6624 // 864, integer floor
  of the average). 864x7 = 6048 < 6624, so 576 atoms dropped. The 7-atom chunks of a
  [CH4(5)][THF(13)] stream produce misidentified types -> garbage resnames.

- timestamp: initial
  checked: ion_inserter.py:174-185 `_build_molecule_index_from_structure` guest section
  found: `guest_atoms_per_mol = guest_atom_count // guest_mols` (ONE value) then
  `for i in range(guest_mols): MoleculeIndex(count=guest_atoms_per_mol, mol_type="guest")`.
  For mixed: 6624//864 = 7 -> every guest entry count=7. This is the PRIMARY corruption.
  implication: The molecule_index is built with a single uniform atom count. For mixed
  hydrates (CH4=5, THF=13) this is wrong. Single-guest path works because the uniform
  count IS correct when all guests are the same type.

- timestamp: initial
  checked: ion_writer.py write_ion_top_file:585-596 + 741-745 + 787-788
  found: Built-in path detects guest_type from ONLY the first guest molecule
  (line 589-596 `for mol ...: if mol.mol_type=="guest": ... detect ...; break`), then uses
  that ONE type for: `#include "{guest_type}_hydrate.itp"` (745) and a single
  `{guest_res_name} {guest_count}` line (788). needs_ch4/thf_atomtypes (614-617) check
  the single guest_type.
  implication: For mixed, only ch4 is detected (first guest) -> only ch4_hydrate.itp
  #included, only `CH4_H 864` listed. THF_H never listed. grompp would fail.

- timestamp: initial
  checked: ion_writer.py write_ion_gro_file:329-392 (built-in path)
  found: Per-molecule detect (line 366 `detect_guest_type_from_atoms(mol_atom_names)`)
  on the slice `atom_names[start:start+mol.count]`. Logic is CORRECT per-molecule, BUT
  mol.count is 7 (corrupted by ion_inserter) -> slices are wrong -> detect misidentifies
  -> mangled resnames GUE/H2_H/THF_H + mis-ordered atoms.
  implication: NO change needed here once ion_inserter produces correct per-molecule
  counts (detect on a correct 5-atom CH4 slice -> "ch4"; on a correct 13-atom THF slice
  -> "thf"). Verified: detect_guest_type_from_atoms on [C,H,H,H,H]->"ch4", on
  [O,CA,CA,CB,CB,Hx8]->"thf" (reliable on correct single-molecule slices).

- timestamp: initial
  checked: guest_info.py _stage_hydrate_guest_itps:287-316 + _detect_builtin_guest_type
  found: Built-in path calls `_detect_builtin_guest_type` (returns ONE type - first
  guest) then `shutil.copy({guest_type}_hydrate.itp)` ONCE. Fallback to config picks
  the FIRST non-custom cage assignment. For mixed -> only ch4_hydrate.itp staged;
  thf_hydrate.itp NOT staged.
  implication: Even if .top is fixed to #include thf_hydrate.itp, the file would be
  missing. Must stage ALL distinct built-in guest types.

- timestamp: initial
  checked: Guest layout in interface (slab.py:524-607 mixed branch)
  found: separate_guests_by_type -> for each type tile bottom+top. Final guest region
  order = [bottom_CH4][bottom_THF][top_CH4][top_THF] (4 type-runs, NOT grouped by type).
  guest_atom_count=6624, guest_mols=864 (576 CH4 + 288 THF, ratio 2:1 = 16:8 sII).
  implication: .gro writes guests in molecule_index order = [CH4][THF][CH4][THF]. GROMACS
  [molecules] requires consecutive same-type runs -> .top must run-length encode:
  CH4_H (n1), THF_H (n2), CH4_H (n3), THF_H (n4). NOT a single grouped total.

- timestamp: initial
  checked: Prior fix architecture (resolved/interface-mixed-component-indexerror.md)
  found: Prior fix added identify_guest_type() + separate_guests_by_type() to
  molecule_utils.py and threaded guest_atom_counts dict + guest_descriptors through
  the modes. But that metadata is NOT propagated onto InterfaceStructure (only aggregate
  guest_nmolecules + guest_atom_count are set, slab.py:834-846). Per-type info is
  DISCARDED at the InterfaceStructure boundary.
  implication: The ion flow only has aggregate counts -> must use the single-uniform
  assumption. Fix must propagate type-level guest_descriptors + guest_atom_counts onto
  InterfaceStructure so the ion_inserter can walk per-molecule (and so the .top/staging
  can derive per-type info). guest_descriptors/guest_atom_counts are TYPE-LEVEL
  (tiling-invariant), so the base candidate's values propagate correctly.

## Eliminated

- hypothesis: "THF is correctly a guest and SHOULD be in the export; the export is fine
  and the user is wrong."
  evidence: The export is structurally INVALID (THF atoms under CH4_H resname, GUE/H2_H
  resnames undefined in .top, 576 atoms dropped, thf_hydrate.itp missing). This is a bug
  regardless of whether THF should be retained. Confirmed bug.

## Resolution

root_cause: Four code locations in the ion->export flow assume a SINGLE uniform guest
type/atom-count (the same class of bug as the prior interface-mixed-component case,
but downstream):
1. ion_inserter.py:178 `guest_atoms_per_mol = guest_atom_count // guest_mols` (=7)
   assigns count=7 to all 864 guest molecule_index entries (CH4=5, THF=13 reality) ->
   corrupts every guest slice + drops 576 atoms.
2. ion_writer.py write_ion_top_file:585-596 detects only the FIRST guest type -> single
   #include + single [molecules] line; THF_H never declared.
3. guest_info.py _stage_hydrate_guest_itps/_detect_builtin_guest_type stages only the
   first detected built-in type -> thf_hydrate.itp missing.
4. (write_ion_gro_file per-molecule detect is correct logic but operates on the
   corrupted slices from #1; no change needed once #1 is fixed.)

fix:
- types.py: add guest_descriptors + guest_atom_counts fields to InterfaceStructure
  (backward-compatible empty defaults).
- molecule_utils.py: add iter_guest_molecules() walker (identify_guest_type +
  count_guest_atoms, yields (start, count, type) per molecule; handles mixed + custom
  via descriptors, heuristic fallback for built-in ch4/thf).
- modes/slab.py, pocket.py, piece.py: populate InterfaceStructure.guest_descriptors +
  guest_atom_counts from candidate.metadata.
- ion_inserter.py: use iter_guest_molecules in _build_molecule_index_from_structure
  (fall back to uniform if walk doesn't exactly consume the guest region -> no
  regression for single-guest).
- ion_writer.py write_ion_top_file: walk guest molecule_index entries, detect each
  molecule's type, run-length encode [molecules] (one line per consecutive same-type
  run), #include each distinct type's _hydrate.itp once, set needs_ch4/thf_atomtypes by
  membership.
- guest_info.py: stage ALL distinct built-in guest types (walk molecule_index / config
  cage_guest_assignments), copy each {type}_hydrate.itp.
- Regression test: mixed SII -> slab -> ion -> export asserts correct CH4_H/THF_H
  residues + counts + both .itp + run-length [molecules]; single SI all-CH4 regression
  guard.

verification:
- Reproduction (/tmp/opencode/repro_thf_ion_export.py, mirrors the GUI flow):
  BEFORE fix: ion molecule_index = 864 entries all count=7 (6624//864), sum=6048
  (576 atoms dropped); .gro resnames CH4_H/GUE/H2_H/THF_H (mangled); .top
  `CH4_H 864` + only ch4_hydrate.itp staged.
  AFTER fix: ion molecule_index = 864 entries with counts {5, 13}, sum=6624 (no
  drops); .gro resnames only SOL/CH4_H/THF_H/NA/CL (no GUE/H2_H); CH4=576
  (2880 atoms), THF=288 (3744 atoms), ratio 2:1; .top [molecules] run-length
  encoded `CH4_H 288, THF_H 144, CH4_H 288, THF_H 144` matching the .gro
  [bot_ch4][bot_thf][top_ch4][top_thf] layout; both ch4_hydrate.itp +
  thf_hydrate.itp staged + #included.
- GROMACS-consistency check (/tmp/opencode/verify_thf_consistency.py): .gro
  molecule runs EXACTLY match .top [molecules] (incl. run order); .top atom
  count == .gro atom count (37976); no garbage resnames; both guests present;
  ratio 2:1; both .itp staged + #included. ALL ASSERTIONS PASSED.
- ULTIMATE check: `gmx grompp` dry-run on the full GUI-equivalent export
  (water.itp + ion.itp + guest itps + .gro + .top) SUCCEEDED -> ions.tpr created
  (920KB). "There are 7823 Water, 864 Other, 50 Ion residues", no fatal errors.
  Before the fix grompp would have failed (THF_H/GUE/H2_H undefined in .top,
  576 atoms missing -> coordinate count mismatch).
- New regression tests: 7/7 passed (tests/test_e2e_mixed_ion_export.py).
- Existing tests: ~700+ relevant tests passed (mixed interface, ion export/
  insertion, guest atom counting, build_molecule_index, mixed cage occupancy,
  gromacs moleculetype, stage custom guest itp, interface generation, modes
  audit, ordering, solute/custom export/insertion, ice/sH/triclinic interface
  export, mixed lattice/filled-ice GUI, scancode bugs [ion/ion_inserter/gui_ion/
  inserters/gromacs/structure_gen/tech_debt/solute/pipeline/constants/...],
  custom guest hydrate + cli/gui grompp + cross-tab + lattices, chain exports,
  cli integration [minus 1 PRE-EXISTING version-string failure], gmx
  validation [52 grompp dry-run tests pass with gmx on PATH]).
- The single pre-existing failure (test_cli_integration::test_version_shows_version,
  asserts "4.5.0" vs actual "4.7.0") confirmed UNRELATED: fails identically on
  original code via git stash. A flaky VTK-headless hang in two GUI renderer
  tests (custom_molecule_panel_34_6 + custom_molecule_renderer run together) is
  a known deferred limitation (AGENTS.md TEST-06), not caused by this fix (each
  passes alone; the combo passes on both original and current when retried).

files_changed:
- quickice/structure_generation/types.py (InterfaceStructure +guest_descriptors/guest_atom_counts)
- quickice/utils/molecule_utils.py (new iter_guest_molecules walker)
- quickice/structure_generation/modes/slab.py (propagate guest metadata)
- quickice/structure_generation/modes/pocket.py (propagate guest metadata)
- quickice/structure_generation/modes/piece.py (propagate guest metadata)
- quickice/structure_generation/ion_inserter.py (per-molecule guest molecule_index walk + fallback)
- quickice/output/_guest.py (new detect_guest_type_runs run-length helper)
- quickice/output/_shared.py (re-export detect_guest_type_runs)
- quickice/output/ion_writer.py (multi-guest .top: run-length [molecules] + per-type #include + atomtypes)
- quickice/output/guest_info.py (new _detect_builtin_guest_types; stage ALL built-in guest .itp)
- tests/test_e2e_mixed_ion_export.py (new, 7 regression tests)
