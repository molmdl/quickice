---
status: verifying
trigger: "Fix interface_writer.py mixed built-in+custom cage guest export (latent gap from commit 29085047)"
created: 2026-08-05T00:00:00Z
updated: 2026-08-05T00:01:00Z
---

## Current Focus

hypothesis: interface_writer.py has the same mixed built-in+custom cage-guest bug
  class as ion_writer.py / solute_writer.py (fixed in 29085047). The GRO custom
  branch walks ALL guests with a single `atoms_per_mol` stride (floor of average
  for mixed) and labels all MOL_H; the TOP declares only MOL_H + #includes only
  the custom ITP, never CH4_H / ch4_hydrate.itp.
test: implement the fix mirroring the ion_writer pattern, adapted to the
  interface path's data model (NO molecule_index — use iter_guest_molecules with
  guest_descriptors + guest_atom_counts), then add a mixed-interface regression
  test + byte-identity guards.
expecting: mixed interface export -> grompp rc=0, .gro has both CH4_H + MOL_H,
  .top declares both + #includes both ITPs; single-custom + pure-built-in
  byte-identical.
next_action: implement GRO + TOP fixes in interface_writer.py

## Symptoms

expected: A mixed built-in+custom interface (CH4 built-in small + ethanol custom
  large) exported via InterfaceGROMACSExporter produces a valid GROMACS export:
  .gro with CH4_H (5-atom) + MOL_H (9-atom); .top declaring both + #including
  both ch4_hydrate.itp and etoh.itp; grompp rc=0.
actual: write_interface_gro_file labels ALL cage guests MOL_H and walks them
  with a single `atoms_per_mol = guest_atom_count // guest_nmolecules` (FLOOR of
  the average, e.g. 152//24=6 for sII 2:1) — misaligning 5-atom CH4 guests.
  write_interface_top_file declares only MOL_H + #includes only etoh.itp, never
  CH4_H / ch4_hydrate.itp. grompp would fail with atom-count mismatch.
errors: latent (interface export not in current UAT path; export is from Ion tab).
  Reproducible by exporting a mixed interface via InterfaceGROMACSExporter.
reproduction: HydrateConfig(sII, cage_guest_assignments={small: ch4, large:
  etoh_mix custom}) -> assemble_slab -> InterfaceGROMACSExporter.export_interface_gromacs.
started: latent gap deferred in commit 29085047 (interface writer not manifesting
  in current UAT since export is from Ion tab).

## Evidence

- timestamp: 2026-08-05T00:00:00Z
  checked: git show 29085047 (ion_writer.py, solute_writer.py, _guest.py,
    guest_info.py) — the reference fix pattern.
  found: ion_writer GRO resolves residue name PER-MOLECULE via molecule_index
    (built-in ch4->CH4_H+reorder; custom->MOL_H+no-reorder); TOP run-length
    encodes [molecules] as (resname, count) runs; #includes BOTH built-in and
    custom ITPs when mixed. solute_writer broadened mol_type filters.
  implication: mirror this pattern in interface_writer, but interface path has
    NO molecule_index (slab/piece builders don't populate it).

- timestamp: 2026-08-05T00:00:00Z
  checked: interface_writer.py full read (549 lines) + slab.py / piece.py
    InterfaceStructure construction.
  found: InterfaceStructure.molecule_index defaults to [] (field(default_factory=
    list)); slab/piece builders set guest_atom_count, guest_nmolecules,
    guest_descriptors, guest_atom_counts but NOT molecule_index. So the GRO
    custom branch's `next(m for m in iface.molecule_index ...)` returns None and
    falls back to `atoms_per_mol = guest_atom_count // guest_nmolecules` (floor
    of average) — BROKEN for mixed.
  implication: must use iter_guest_molecules (descriptor-driven, reliable for
    ch4 vs etoh_mix) instead of molecule_index for the interface path.

- timestamp: 2026-08-05T00:00:00Z
  checked: guest_info.py _stage_hydrate_guest_itps (lines 358-390, fixed in
    29085047) + InterfaceGROMACSExporter.export_interface_gromacs (export.py
    1121-1249).
  found: staging helper is CONFIG-DRIVEN (uses hydrate_config.cage_guest_
    assignments to detect built-in types) and ALREADY stages BOTH custom and
    built-in ITPs when mixed. InterfaceGROMACSExporter passes hydrate_config
    to the helper. So the interface path's ITP staging is ALREADY correct.
  implication: NO change needed to guest_info.py — only interface_writer.py
    (.gro + .top) needs the fix.

- timestamp: 2026-08-05T00:00:00Z
  checked: identify_guest_type + iter_guest_molecules (molecule_utils.py) +
    hydrate_generator descriptor building.
  found: guest_descriptors built for ALL cage assignments (built-in ch4 AND
    custom etoh_mix), each carrying atom_labels + atom_count. identify_guest_
    type does exact atom_labels prefix match FIRST (reliable), then heuristic.
    iter_guest_molecules(atom_names, 0, total, guest_descriptors,
    guest_atom_counts) yields (start, count, mol_type) per molecule — the SAME
    walker the ion inserter uses to build its molecule_index (test asserts ch4
    + etoh_mix mol_types).
  implication: iter_guest_molecules reliably distinguishes ch4 from etoh_mix
    for the interface path. Use it for the mixed per-molecule walk.

- timestamp: 2026-08-05T00:00:00Z
  checked: detect_guest_type_from_atoms misidentifies ethanol as ch4 (both
    have C+H; _get_molecule_atoms grabs first 5 atoms C+4H, misses O).
  found: confirmed in the 29085047 commit message + _guest.py comments.
  implication: do NOT use detect_guest_type_from_atoms to distinguish CH4 from
    ethanol in the mixed case — use per-molecule mol_type from iter_guest_
    molecules.

## Resolution

root_cause: interface_writer.py GRO custom branch (lines 259-290) uses a single
  `atoms_per_mol` stride + single MOL_H residue name for ALL guests; TOP custom
  branch (lines 454-467 atomtypes, 493-502 #include, 528-545 [molecules]) emits
  only the custom residue/ITP. When a built-in CH4 + custom ethanol coexist,
  CH4 (5-atom) guests get MOL_H + the 9-atom stride, and the .top never declares
  CH4_H / ch4_hydrate.itp.
fix: (implemented) Mirror the 29085047 ion_writer pattern, adapted to the
  interface path's data model (NO molecule_index — use iter_guest_molecules with
  guest_descriptors + guest_atom_counts). GRO: when mixed (detected via
  guest_atom_counts having a built-in type AND custom_guest_info non-empty),
  walk per-molecule via iter_guest_molecules; built-in -> CH4_H + reorder,
  custom -> MOL_H + no reorder; single-custom path kept verbatim. TOP: when
  mixed, write BOTH atomtypes blocks (custom + built-in per distinct_builtin_
  types), #include BOTH ITPs (custom + built-in {type}_hydrate.itp), run-length
  encode [molecules] as (resname, count) runs via iter_guest_molecules; single-
  custom + pure-built-in paths kept verbatim. guest_info.py NOT changed
  (_stage_hydrate_guest_itps already config-driven + already stages both ITPs
  when mixed, per 29085047).
verification:
  - NEW test tests/test_e2e_custom_guest_mixed_cage_interface.py (8 tests): ALL
    PASS, including gmx grompp rc=0 on the mixed CH4+ethanol interface export
    (gmx available). Asserts: .gro has both CH4_H (5-atom) + MOL_H (9-atom);
    .top [molecules] declares both (runs); .top #includes both ch4_hydrate.itp
    + etoh.itp; CH4:ethanol ratio 2:1; .gro runs == .top runs; single-custom
    guard (only MOL_H); pure-built-in guard (only CH4_H).
  - Existing e2e suites (test_e2e_lattice_cross_tab_cli, test_e2e_custom_guest_
    cross_tab_gui, test_e2e_mixed_ion_export, test_e2e_custom_guest_mixed_cage):
    22 pass, 0 regressions.
  - Broader e2e sweep (tests/test_e2e_*.py -x --timeout=120): 400 pass, 0
    failures (392 prior + 8 new).
  - Byte-equivalence + interface unit tests (test_gro_top_byte_equivalence,
    test_interface_gro_custom_guest, test_interface_top_custom_guest,
    test_gromacs_moleculetype_names, test_gromacs_export_interface): 45 pass.
  - BYTE-IDENTITY (writer-isolated): generated single-custom + pure-built-in
    interface structures ONCE, pickled, wrote with my fix (after) and with
    pre-fix writer (via git stash, same pickled structures) (before); diff -rq
    iso_before iso_after => IDENTICAL. (An earlier non-isolated diff showed
    differences, but a control run confirmed PRE-FIX code run twice ALSO
    differs — structure generation has run-to-run non-determinism in water
    filling / GenIce2, independent of interface_writer. The writer-isolated
    check is the valid test and PASSES.)
files_changed:
  - quickice/output/interface_writer.py (GRO + TOP mixed-case handling)
  - tests/test_e2e_custom_guest_mixed_cage_interface.py (NEW regression test)
  - .planning/debug/interface-writer-mixed-guest.md (this debug session)
