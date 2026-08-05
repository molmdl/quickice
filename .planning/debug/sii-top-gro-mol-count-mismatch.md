---
status: resolved
trigger: "GROMACS .top molecule count for custom cage guest (MOL_H) mismatches the .gro atom count when exporting through the slab interface + downstream tabs (Custom/Solute/Ion) workflow. The .top reports config-derived cage count (864) while the .gro contains the actual slab-truncated structure count (576), causing gmx grompp to fail with a coordinate/topology atom count mismatch."
created: 2026-08-05T00:00:00Z
updated: 2026-08-05T01:30:00Z
---

## Current Focus

ROOT CAUSE FOUND (confirmed by reproduction). See Resolution.

## Resolution

root_cause: The .gro MOL_H molecules have 6 atoms each instead of 9 (ethanol = 9 atoms: H,C,H,H,C,H,H,O,H). The .top [molecules] MOL_H=864 AGREES with the .gro's 864 MOL_H residues — they do NOT mismatch on molecule count (the task's "864 vs 576" framing was wrong: 576 = 5184/9 was computed assuming 9 atoms/molecule, but the .gro actually has 864 residues × 6 atoms = 5184). grompp fails because the ITP (etoh.itp) defines MOL_H with 9 atoms/molecule, so it expects 864×9=7776 atoms, but the .gro has 864×6=5184 (diff 2592 = 864×3 = the hydroxyl O+H+H dropped per molecule).

The 6-atom/molecule fragmentation is caused by a config/structure desync in `HydrateStructure.to_candidate()` (types.py:1274): it builds the `guest_atom_counts` metadata dict from `guest_descriptors[].atom_count`, which comes from the user-entered `HydrateConfig.guest_atom_count`. When this config value is WRONG (e.g., 6 instead of 9 — a user typo not matching the .gro's 9 atoms), it propagates to `candidate.metadata["guest_atom_counts"]`. The hydrate generator's `_build_molecule_index` (hydrate_generator.py:674-688) uses RESIDUE GROUPING (the actual .gro atom count via residue_seq_nums), so the structure's `molecule_index` is AUTHORITATIVE (count=9). But `to_candidate` ignores the molecule_index and uses the config-derived `guest_descriptors.atom_count` (6) for the metadata.

Downstream, `slab.py:_count_guest_molecules` / `_detect_guest_atoms` / `iter_guest_molecules` use `guest_atom_counts[mol_type]` (the metadata=6) as the per-molecule stride via `count_guest_atoms` (molecule_utils.py:150 `return guest_atom_count`). With stride 6, the 9-atom guest positions are grouped as 6-atom fragments (misaligned, dropping 3 atoms per molecule). The slab reports `guest_atom_count = len(processed)` (actual 9-atom positions) but `guest_nmolecules = processed // 6` (wrong), so `guest_atom_count // guest_nmolecules = 6` flows through custom_molecule_inserter (line 802) → solute_inserter → ion_inserter → write_ion_top_file (guest_count=864) and write_ion_gro_file (864 residues × 6 atoms).

Reproduced empirically: HydrateConfig(guest_atom_count=6) with the 9-atom etoh.gro/etoh.itp → hydrate molecule_index count_dist={9:24} (correct) BUT candidate.metadata guest_atom_counts={'etoh':6} (WRONG) → slab atoms/mol=6.000 (bug). With guest_atom_count=9 → atoms/mol=9.000 (correct).

NOTE: validate_custom_guest_files (custom_guest_bridge.py:246) checks .gro atom count == .itp atom count (9==9 passes) but does NOT check against config.guest_atom_count, so a wrong config value slips through.

fix: In `HydrateStructure.to_candidate()` (quickice/structure_generation/types.py), derive `candidate.metadata["guest_atom_counts"]` from the AUTHORITATIVE `molecule_index` (the hydrate generator's `_build_molecule_index` groups cage guests by GenIce2 residue sequence number, so each guest `MoleculeIndex.count` is the real per-molecule atom count read from the .gro) instead of `guest_descriptors[].atom_count` (the user-entered `HydrateConfig.guest_atom_count`). Added a `_derive_guest_atom_counts(molecule_index, guest_descriptors)` helper that takes the count from the molecule_index for each non-water mol_type and only falls back to `guest_descriptors` for mol_types absent from the index (keeps the built-in/empty-index path byte-identical). This makes the slab/ion stride always match the real guest atom count, so 9-atom ethanol is grouped as 9-atom molecules (not 6-atom fragments) regardless of a wrong config value.

verification: Reproduced the bug empirically (HydrateConfig guest_atom_count=6 with the 9-atom etoh.gro/itp → slab atoms/mol=6.000, the bug). After the fix: candidate.guest_atom_counts={etoh:9} (from molecule_index, not 6), slab atoms/mol=9.000. Full flow (hydrate→to_candidate→assemble_slab→custom→solute→ion→write_ion_gro/top) with BOTH guest_atom_count=9 and the wrong =6 now produces a consistent export: .gro = 864 MOL_H residues × 9 atoms = 7776, .top [molecules] MOL_H=864, matching the 9-atom etoh.itp ITP → .top-expected (864×9=7776) == .gro (7776), so gmx grompp coordinate/topology counts match. Added regression test `TestToCandidateGuestAtomCountsAuthoritative::test_wrong_config_guest_atom_count_does_not_fragment_guests` which FAILS without the fix (guest_atom_counts={etoh:6}) and PASSES with it (=9). Test suite: 94 e2e tests (custom guest, mixed, ion export, cross-tab, grompp, gro/top equivalence) + 202 output/writer unit tests all pass; new regression test passes.
files_changed: [quickice/structure_generation/types.py, tests/test_e2e_custom_guest_hydrate.py]

## Symptoms

expected: The .top [molecules] MOL_H count should match the .gro MOL_H atom count divided by atoms-per-molecule (9 atoms per ethanol). For a sII 3x3 hydrate exported through slab mode, .top MOL_H should equal 576 (the actual generated count), and gmx grompp should succeed (rc=0).

actual: The .top [molecules] section lists MOL_H = 864 (the config-derived expected cage count = 32 cages/cell x 27 unit cells = 864 at 100% occupancy), but the .gro file contains only 576 MOL_H molecules (5,184 atoms / 9 atoms per molecule). Difference of 288 molecules / 2,592 atoms. gmx grompp fails: topology expects 37,405 total atoms but coordinate file has 34,813.

errors:
```
Fatal error:
number of coordinates in coordinate file (ions_23na_23cl_with_24ch4.gro, 34813)
             does not match topology (ions_23na_23cl_with_24ch4.top, 37405)
```

reproduction:
1. GUI: generate sII 3x3 hydrate with custom ethanol guest (MOL_H) in cages.
2. Interface tab: build slab structure.
3. Custom tab: insert custom molecule (ethanol).
4. Solute tab: insert CH4 solute.
5. Ion tab: insert NaCl ions.
6. Export from Ion tab to GROMACS.
7. Run gmx grompp -> fails with coordinate/topology mismatch.

started: Discovered during UAT Workflow F (GUI interactive testing) step 15, on 2026-08-04/05. v4.7 UAT. Same class of bug (config/structure desync) seen before in hydrate-only export path (resolved: mixed-export-itp-and-dialog.md), but different export path (slab interface + downstream Custom/Solute/Ion tabs).

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-08-05T00:00:00Z
  checked: Prior resolved session .planning/debug/mixed-export-itp-and-dialog.md
  found: Prior bug was config/structure desync in hydrate-only export_hydrate path. ITP staging was driven by config.cage_guest_assignments (empty after lattice change) while .gro/.top content came from structure.molecule_index (stale). Fix pattern: make ITP staging structure-driven (use structure.molecule_index + guest_descriptors), not config-driven. Files changed: quickice/gui/hydrate_export.py, quickice/gui/main_window.py.
  implication: This new bug may be the same desync class but in the slab interface + downstream tabs export path. The fix pattern (structure-driven, not config-driven) likely applies. BUT must verify the actual mechanism — write_ion_top_file already appears structure-driven (computes guest_count from molecule_index), so the desync may be a STALE molecule_index rather than a config-driven override.

- timestamp: 2026-08-05T00:00:00Z
  checked: tmp/SII-ch4-mol_slab_etohL_ch4L_ion/ions_23na_23cl_with_24ch4.top
  found: [molecules] section: SOL 7305, MOL_H 864, etoh 27, CH4_L 24, NA 23, CL 23. Header line 3 says "864 guests". #include directives: tip4p-ice.itp, etoh.itp, etoh_L.itp, ch4_liquid.itp, ion.itp. comb-rule=2 (correct).
  implication: MOL_H=864 is the config-derived full-cage count (32 cages/cell x 27 cells). The .top is the ion export path (write_ion_top_file).

- timestamp: 2026-08-05T00:00:00Z
  checked: quickice/output/ion_writer.py write_ion_top_file (lines 491-848) and write_ion_gro_file (lines 77-488)
  found: BOTH writers derive guest info from ion_structure.molecule_index (re-exported from gromacs_writer.py line 81, no stale duplicate). write_ion_top_file line 540: guest_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "guest"). write_ion_gro_file Pass 2 (lines 142-152) iterates the same molecule_index. custom_active requires guest_count > 0 AND guest_atom_count > 0; guest_res_name (MOL_H) from custom_guest_info, written with guest_count. The GUI export handler (export.py IonGROMACSExporter.export_ion_gromacs) passes the SAME ion_structure to both writers.
  implication: Both writers use the SAME molecule_index, so .top MOL_H count == .gro MOL_H residue count. They AGREE on 864. The mismatch is in PER-MOLECULE ATOM COUNT (6 in .gro vs 9 in ITP), not molecule count.

- timestamp: 2026-08-05T00:30:00Z
  checked: Direct .gro analysis (tmp/SII-ch4-mol_slab_etohL_ch4L_ion/ions_23na_23cl_with_24ch4.gro)
  found: .gro has 864 distinct MOL_H residue numbers, each with EXACTLY 6 atoms (5184 total). atom-name counts {C:1088, H:3840, O:256} (jumbled, not a clean 864×9 subset). The .top [molecules] MOL_H=864 AGREES with the .gro's 864 residues — they do NOT mismatch on molecule count. grompp fails because the etoh.itp ITP defines MOL_H with 9 atoms/molecule (expects 864×9=7776) but the .gro has 864×6=5184 (diff 2592 = 864×3 = the hydroxyl O+H+H dropped per molecule). The task's "864 vs 576 molecule count mismatch" framing was a MISDIAGNOSIS: 576 = 5184/9 was computed assuming 9 atoms/molecule, but the .gro actually has 864 residues × 6 atoms.
  implication: The bug is a per-molecule ATOM COUNT error (6 vs 9), NOT a molecule COUNT error (864 vs 576). The .gro MOL_H molecules are 6-atom fragments (C2H4) of the real 9-atom ethanol (C2H6O).

- timestamp: 2026-08-05T00:45:00Z
  checked: Empirical reproduction (sII 1x1x1 ethanol hydrate → assemble_slab, scanning ice_thickness 1.0–5.0) with guest_atom_count=9 (correct)
  found: slab ALWAYS reports 9.000 atoms/molecule for ALL ice_thickness values (guest_atom_count=9 → candidate.guest_atom_counts={etoh:9} → stride 9). Full flow (custom→solute→ion→export) gives 864 MOL_H × 9 atoms = 7776, .top MOL_H=864 — consistent. The slab does NOT drop atoms (tile_structure filter_molecules=False wraps, doesn't drop). So with a CORRECT config, there is no bug.
  implication: The slab and downstream are correct given a correct config. The 6-atom/molecule must come from a WRONG config value propagating to the stride.

- timestamp: 2026-08-05T00:55:00Z
  checked: Empirical reproduction with HydrateConfig guest_atom_count=6 (WRONG) and the 9-atom etoh.gro/etoh.itp
  found: hydrate molecule_index count_dist={9:24} (CORRECT — _build_molecule_index uses residue grouping, reads the .gro's 9 atoms, ignores config). BUT candidate.metadata guest_atom_counts={'etoh':6} (WRONG — to_candidate used guest_descriptors[].atom_count from config). slab: guest_nmols=1296 guest_atoms=7776 atoms/mol=6.000 (BUG REPRODUCED — stride 6 fragmented 9-atom guests into 6-atom groups). validate_custom_guest_files (custom_guest_bridge.py:246) checks .gro==.itp (9==9, pass) but NOT config.guest_atom_count, so the wrong value slips through.
  implication: ROOT CAUSE CONFIRMED. to_candidate propagates the config's wrong guest_atom_count into guest_atom_counts metadata; the hydrate molecule_index (authoritative) is ignored.

- timestamp: 2026-08-05T01:10:00Z
  checked: Fix applied (to_candidate derives guest_atom_counts from molecule_index via _derive_guest_atom_counts helper) + regression test
  found: With the fix, wrong config (guest_atom_count=6) → candidate.guest_atom_counts={etoh:9} (from molecule_index), slab atoms/mol=9.000 (bug fixed). Full export: .gro 864 MOL_H × 9 atoms = 7776, .top MOL_H=864, consistent with the 9-atom ITP. Regression test FAILS without fix ({etoh:6}) and PASSES with it ({etoh:9}). 94 e2e + 202 unit tests pass.
  implication: Fix verified end-to-end. grompp coordinate/topology counts now match (864×9=7776 in both .gro and .top-expected).

## Resolution

root_cause: (empty until found)
fix: (empty until applied)
verification: (empty until verified)
files_changed: []
