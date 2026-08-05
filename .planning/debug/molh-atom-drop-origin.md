---
status: verifying
trigger: "Determine definitively whether committed fix (b990d151) resolves the real UAT failure (864 MOL_H × 6 atoms = 5184, 2592 atoms physically dropped), or whether a second atom-dropping bug exists that the prior agent missed."
created: 2026-08-05T00:00:00
updated: 2026-08-05T02:45:00Z
---

## Current Focus

IMPLEMENTING the fix from Resolution.fix. Baseline confirmed: mixed CH4+ethanol grompp rc=1 (FAILS — all 1296 cage guests labeled MOL_H); single-ethanol grompp rc=0 (PASSES); mixed-built-in (CH4+THF) 7 tests PASS.

hypothesis: Implementing the plan's 4-source-file fix (ion_inserter per-molecule mol_type + ion_writer per-molecule resname resolution + guest_info dual ITP staging) PLUS necessary updates to detect_guest_type_runs / _detect_builtin_guest_types / existing test filters to handle the new per-molecule mol_types (ch4/thf instead of generic "guest") will fix the mixed case while preserving byte-identity for single-custom and mixed-built-in paths.
test: repro_molh_mixed.py grompp rc=0 after fix; repro_molh_drop.py still rc=0; test_e2e_mixed_ion_export.py still 7 pass; new test_e2e_custom_guest_mixed_cage.py passes.
expecting: mixed case .gro has both CH4_H (5-atom) and MOL_H (9-atom); .top [molecules] declares both; .top #includes both ch4_hydrate.itp and etoh.itp; grompp rc=0.
next_action: Implement the fix across ion_inserter.py, _guest.py, guest_info.py, ion_writer.py; update test_e2e_mixed_ion_export.py filters; add test_e2e_custom_guest_mixed_cage.py; verify.

## Symptoms

expected: When a user uploads bundled quickice/data/custom/etoh.gro (9 atoms) + etoh.itp as custom cage guest, generates sII 3x3 hydrate, runs full tab chain (Interface slab -> Custom -> Solute -> Ion) and exports from Ion tab, exported .gro should contain 864 MOL_H residues × 9 atoms = 7776 MOL_H atoms, and gmx grompp should succeed.

actual: Exported .gro contains 864 MOL_H residues × 6 atoms = 5184 MOL_H atoms. 2592 atoms physically missing. gmx grompp fails: topology (etoh.itp defines MOL_H with 9 atoms/molecule -> expects 864x9=7776) does not match coordinate file (5184).

errors:
```
Fatal error:
number of coordinates in coordinate file (ions_23na_23cl_with_24ch4.gro, 34813)
             does not match topology (ions_23na_23cl_with_24ch4.top, 37405)
```

reproduction:
1. GUI Hydrate tab — upload etoh.gro (9 atoms) + etoh.itp as custom cage guest. Generate sII 3x3 hydrate.
2. Interface tab — build slab structure.
3. Custom tab — insert custom molecule (ethanol).
4. Solute tab — insert CH4 solute.
5. Ion tab — insert NaCl ions. Export from Ion tab.
6. Parse exported .gro — MOL_H residues have 6 atoms each (should be 9).
7. Run gmx grompp — fails with coordinate/topology mismatch.

started: Discovered during UAT Workflow F step 15 (2026-08-04/05). Committed fix b990d151 applied 2026-08-05.

## Eliminated

<!-- APPEND only -->

- timestamp: 2026-08-05T00:20:00Z
  hypothesis: The real UAT used config=9 (auto-detected) but a SECOND bug physically dropped atoms to 6 per MOL_H.
  evidence: |
    Reproduced the FULL UAT scenario (sII 3x3x3 custom ethanol guest -> slab -> solute -> ion -> GUI IonGROMACSExporter -> gmx grompp) with config=9 (auto-detected value) at the UAT scale (slab box 5.13629x5.13629x10.57382). Result:
    - Hydrate: 648 guests x 9 atoms = 5832; molecule_index authoritative count=9.
    - Candidate.guest_atom_counts = {etoh_uat: 9} (from molecule_index via the fix).
    - Slab: guest_nmolecules=1296, guest_atom_count=11664, atoms/mol=9.000.
    - Ion: 1296 guest entries x 9 atoms = 11664.
    - .gro MOL_H: 1296 residues x 9 atoms = 11664. grompp exit_code=0 (PASS).
    ALSO confirmed: config=9 PRE-FIX would be identical (guest_descriptors atom_count=9 == molecule_index count=9, so _derive_guest_atom_counts returns {etoh:9} either way). So config=9 NEVER produces 6-atom MOL_H, with or without the fix.
  conclusion: REFUTED. config=9 cannot produce 6-atom MOL_H. The real UAT's 6-atom MOL_H could ONLY come from config=6 (pre-fix). There is NO second atom-dropping bug triggered by config=9.

- timestamp: 2026-08-05T00:25:00Z
  hypothesis: Pre-fix config=6 reproduces the real UAT's 6-atom MOL_H pattern (sliding chunks, C-first, with O atoms).
  evidence: |
    Monkeypatched _derive_guest_atom_counts to PRE-FIX behavior ({gd.mol_type: gd.atom_count} = config-derived) and ran config=6 at sII 3x3x3 + UAT slab box. Result:
    - Candidate.guest_atom_counts = {etoh_uat2: 6} (pre-fix, config-derived). CONFIRMED pre-fix behavior.
    - Slab: guest_nmolecules=1944, guest_atom_count=11664, atoms/mol=6.000. iface.guest_atom_counts={etoh_uat2:6}.
    - iface guest region first 18 atom_names = ['H','C','H','H','C','H','H','C','H','H','C','H','H','C','H','H','C','H'] = REPEATED pattern [H,C,H,H,C,H] x 3 (NO oxygen — the slab's guest_pattern=first 6 of source, repeated, drops the O+H+H of each molecule).
    - Ion: 1944 guest entries x 6 atoms = 11664 (stride 6, all atoms covered as 6-atom groups).
    - .gro MOL_H: 1944 residues x 6 atoms. ALL residues IDENTICAL = ['H','C','H','H','C','H'] (repeated pattern). atom_name_multiset = {H:7776, C:3888} (NO OXYGEN). grompp rc=1 (FAIL, atom count mismatch).
    - REAL UAT .gro MOL_H: 864 residues x 6 atoms, SLIDING chunks (different per residue: [C,H,H,H,H,C],[H,H,H,H,C,H],[H,H,H,C,H,H],...), WITH oxygen (multiset {C:1088,H:3840,O:256}).
  conclusion: PARTIALLY CONFIRMED / PARTIALLY REFUTED. Pre-fix config=6 DOES produce 6-atom MOL_H (the atom-COUNT bug, grompp fails) — so the fix IS necessary. BUT the pre-fix config=6 repro does NOT match the real .gro's PATTERN (repeated all-same no-O vs sliding with-O). The real UAT was generated with a DIFFERENT slab code path (kept the actual atom sequence -> sliding chunks, not the repeated pattern) AND a different atom ORDER (C-first vs H-first). The atom-COUNT bug (6 vs 9) is the same; the fix corrects it in both cases (stride 9 -> 9-atom MOL_H). The pattern/order discrepancy is a SECONDARY cosmetic difference, not a second count bug.

- timestamp: 2026-08-05T00:35:00Z
  hypothesis: The real UAT had a SINGLE ethanol cage guest (per the task description "custom-ethanol-guest hydrate").
  evidence: |
    Parsed the real .gro MOL_H atom sequence in order. Found the MOL_H region is a MIX:
    - Pre-O region (first 1440 atoms): [C,H,H,H,H] repeated = C-first CH4 (5-atom, 288 molecules). NO oxygen.
    - O region (from index 1440): [H,C,H,H,C,H,H,O,H] repeated = H-first ethanol (9-atom, SOURCE order). 256 O atoms.
    - The 9-atom window at index 1440 = [H,C,H,H,C,H,H,O,H] = source etoh.gro order (H-first).
    - multiset {C:1088, H:3840, O:256}: 256 ethanol (9-atom, with O) + 576 CH4 (5-atom, no O) = 2304 + 2880 = 5184 atoms.
    A single-ethanol-guest repro (config=9 or config=6) produces ONLY H-first ethanol atoms (no C-first CH4). The C-first CH4 atoms in the real .gro CANNOT come from a single ethanol guest. They MUST come from CH4 in cages (mixed cage assignment). GenIce2 emits CH4 as C-first ([C,H,H,H,H]) — matches the real .gro's pre-O region. The GUI auto-detection (hydrate_panel.py:410) returns atom_count=9 for the bundled etoh.gro, so config=6 is NOT reachable via auto-detection — confirming the real UAT's 6-atom fragments came from the MIXED-guest mislabeling + stride, NOT a wrong config value.
  conclusion: REFUTED. The real UAT had a MIXED cage assignment (CH4 in small cages + ethanol custom in large cages), not a single ethanol guest. The task description "custom-ethanol-guest hydrate" is a simplification (the ethanol is the custom part; CH4 is the built-in small-cage guest).

## Evidence

<!-- APPEND only -->

- timestamp: 2026-08-05T00:45:00Z
  checked: Reproduced MIXED cage assignment (CH4 small + ethanol custom large) with CURRENT code (fix b990d151 applied), sII 1x1x1 + slab, GUI IonGROMACSExporter.
  found: |
    - Hydrate: 16 CH4 (5-atom, C-first) + 8 ethanol (9-atom, H-first) = 24 cages. molecule_index correctly has ch4 (count=5) and etoh_mix (count=9).
    - Candidate.guest_atom_counts = {ch4: 5, etoh_mix: 9} (CORRECT from molecule_index — the fix works for the metadata).
    - Slab: guest_nmolecules=1296, guest_atom_count=8208. iface.guest_atom_counts={ch4:5, etoh_mix:9}. iter_guest_molecules: ch4=864, etoh_mix=432 (CORRECT per-type stride).
    - Ion: 1296 guest entries, count_dist={5:864, 9:432}, total=8208 (CORRECT per-molecule counts — NO atoms dropped at ion stage).
    - .gro MOL_H: 1296 residues, dist={5:864, 9:432}, total=8208. ALL labeled MOL_H (BOTH the 864 CH4 and the 432 ethanol). multiset {C:1728, H:6048, O:432}.
    - .top [molecules]: {SOL, MOL_H:1296, CH4_L:25, NA:11, CL:11}. Only MOL_H (NO CH4_H). #includes etoh.itp (9 atoms/MOL_H).
    - grompp rc=1 (FAILS): coordinate file 55959 atoms != topology 59415. The .top expects MOL_H=1296 x 9 = 11664 (from etoh.itp), but .gro MOL_H has 8208 (864x5 + 432x9). Diff = 3456 = 864x4 (CH4 has 5 atoms, ITP expects 9, 4 missing per CH4).
  implication: |
    SECOND BUG CONFIRMED. With the committed fix applied, a MIXED cage assignment (built-in CH4 + custom ethanol) STILL fails grompp. The ion export labels ALL cage guests as MOL_H (the custom residue name) — the 864 CH4 cage guests get MOL_H instead of CH4_H. The .top declares only MOL_H + #includes etoh.itp (9 atoms), but 864 of the MOL_H residues are 5-atom CH4 -> grompp atom-count mismatch. The committed fix (b990d151, single-guest stride) does NOT address this. This matches the real UAT's pattern (CH4 + ethanol fragments in MOL_H). The fix's _derive_guest_atom_counts correctly produces {ch4:5, etoh_mix:9}, and the ion inserter correctly builds 864 CH4 (5-atom) + 432 ethanol (9-atom) entries — but the WRITER mislabels the CH4 entries as MOL_H (custom_active fallback to first custom_guest_info), and the .top declares only MOL_H.

- timestamp: 2026-08-05T00:10:00Z
  checked: Direct parse of real exported .gro tmp/SII-ch4-mol_slab_etohL_ch4L_ion/ions_23na_23cl_with_24ch4.gro
  found: |
    - Residue summary: SOL 7305×4=29220, MOL_H 864×6=5184, MOL 27×9=243, CH4_L 24×5=120, NA 23×1, CL 23×1. Total=34813.
    - MOL_H residues are assigned SEQUENTIAL residue numbers every 6 atoms (resseq 7306, 7307, 7308 ... each exactly 6 atoms).
    - First MOL_H residue (resseq=7306) atoms: ['C','H','H','H','H','C']. Second: ['H','H','H','H','C','H']. Third: ['H','H','H','C','H','H']. These are 6-atom SLIDING chunks of a contiguous run, NOT molecule-aligned.
    - MOL_H atom-name multiset across ALL 864 residues: {C:1088, H:3840, O:256} total=5184.
    - Source etoh.gro per-molecule atoms: ['H','C','H','H','C','H','H','O','H'] = {C:2, H:6, O:1}.
    - 864 molecules × {C:2,H:6,O:1} = {C:1728, H:5184, O:864} = 7776 atoms (the full guest region).
  implication: |
    - The dropping is a STRIDE-6 walk over the 7776-atom guest region (NOT molecule-aligned). 5184 kept = first 864 chunks of 6; 2592 dropped.
    - The presence of 256 O atoms in MOL_H PROVES the chunks slide across molecule boundaries (if molecule-aligned "drop last 3 (H,O,H)", O would be 0). LCM(6,9)=18: every 2 molecules = 3 chunks, keep first 12 atoms drop last 6. 7776/18=432 blocks × 12 kept = 5184 kept, ×6 dropped = 2592 dropped. ✓ Matches.
    - This is consistent with a stride-6 grouping (config=6). If the real UAT had config=9 (stride 9), the stride-9 walk would be molecule-aligned and NO atoms would be dropped (each chunk = exactly one 9-atom molecule). So the real UAT almost certainly had stride 6 => config=6.
    - BUT: the atom NAME ORDER (C,H,H,H,H,C) does NOT match source first-6 (H,C,H,H,C,H). This means the 7776 guest atoms are NOT in source etoh.gro order — GenIce2 likely reorders atoms during cage placement. Must verify by generating a hydrate and inspecting guest atom order.

## Resolution

root_cause: |
  SECOND BUG (the committed fix b990d151 is INSUFFICIENT for the real UAT). The real UAT had a MIXED cage assignment: CH4 (built-in) in small cages + ethanol (custom) in large cages. The ion export path mislabels ALL cage guests as MOL_H (the custom residue name), so the 864 CH4 cage guests (5 atoms each) are written as MOL_H but the .top #includes etoh.itp (9 atoms/MOL_H) -> gmx grompp atom-count mismatch (expects 864x9=7776, gets a mix of 5-atom CH4 + 9-atom ethanol fragments).

  The committed fix (b990d151) only corrects the per-molecule STRIDE for a SINGLE guest type (6->9 via _derive_guest_atom_counts from molecule_index). It does NOT address the mixed built-in+custom MISLABELING. With the fix applied, a mixed CH4+ethanol repro STILL fails grompp (rc=1): .gro MOL_H = 864 CH4 (5-atom) + 432 ethanol (9-atom) all labeled MOL_H; .top declares only MOL_H=1296 + #includes etoh.itp (9 atoms) -> expects 1296x9=11664, gets 8208.

  Root cause is SYSTEMIC across the cage-guest export path:
  1. ion_inserter.py:207 `_build_molecule_index_from_structure` labels ALL cage guests `mol_type="guest"`, DISCARDING the per-molecule type (`_mt` from iter_guest_molecules, which correctly yields ch4/etoh_mix via descriptor atom_labels matching — reliable).
  2. ion_writer.py / interface_writer.py / solute_writer.py: when `custom_active` (custom guest present), the writers fall back to `next(iter(custom_by_moltype.values()))` (first custom = MOL_H) for ANY guest mol_type not in custom_by_moltype — including the "guest" and built-in CH4 entries -> ALL cage guests get MOL_H.
  3. write_ion_top_file:540 `guest_count = sum(1 for m if mol_type=="guest")` counts ALL cage guests; custom_active -> single `guest_res_name=MOL_H`; .top declares only "MOL_H {count}", never CH4_H.
  4. guest_info.py _stage_hydrate_guest_itps: stages only the custom ITP (etoh.itp), not the built-in ch4_hydrate.itp, when custom_guest_info is non-empty.
  5. detect_guest_type_from_atoms MISIDENTIFIES ethanol as ch4 (both have C+H: [H,C,H,H,C,H,H,O,H] -> "ch4"), so the writers CANNOT use atom-name detection to distinguish CH4 from ethanol in the mixed case — they MUST use the per-molecule mol_type.

  The prior Phase 45-15 fix handled MIXED BUILT-IN guests (CH4+THF) via detect_guest_type_runs, but ONLY when custom_active is False. When custom_active is True (custom guest present), the system assumes a SINGLE custom cage guest and ignores built-in cage guests. The real UAT (mixed built-in + custom) falls into this gap.

  Confirmed the real UAT had a mixed guest: the real .gro MOL_H region contains C-first CH4 atoms ([C,H,H,H,H] repeated, 5-atom, no O — GenIce2's C-first CH4 variant) interleaved with H-first ethanol atoms ([H,C,H,H,C,H,H,O,H], 9-atom, source order, with O). A single-ethanol-guest repro produces ONLY H-first ethanol (no C-first CH4), so the C-first CH4 in the real .gro CANNOT come from a single ethanol guest — it must come from CH4 in cages. The GUI auto-detection (hydrate_panel.py:410) returns atom_count=9 for the bundled etoh.gro, so the real UAT's 6-atom fragments came from the mixed-guest mislabeling + stride (the slab's atoms_per_guest = total//nmols floors to the AVERAGE for mixed guests), NOT a wrong config value of 6.

fix: |
  [PROPOSED — to be implemented in a fresh /gsd-debug session. NOT yet applied.]
  Approach: preserve the per-molecule cage-guest mol_type through the ion inserter so the writers can distinguish built-in (CH4/THF) from custom (ethanol) cage guests, then declare each with its correct residue name + ITP.

  FILES TO CHANGE (4 source + tests):
  1. quickice/structure_generation/ion_inserter.py:207 — in `_build_molecule_index_from_structure`, change `mol_type="guest"` to `mol_type=_mt` (the per-molecule type yielded by `iter_guest_molecules`, which uses `identify_guest_type` + descriptor `atom_labels` matching — RELIABLE for ch4 vs custom ethanol, unlike `detect_guest_type_from_atoms` which misidentifies ethanol as ch4). Keep the fallback path (line 214-227) labeling as "guest" only when the walk fails the guard (preserves single-guest byte-identical behavior when descriptors are absent). NOTE: this changes cage-guest mol_type from "guest" to the specific type (ch4/etoh_mix) for the descriptor-driven path.

  2. quickice/output/ion_writer.py write_ion_gro_file — Pass 2 (lines 142-152): collect cage guests by `mol.mol_type in ("guest", "ch4", "thf") or mol.mol_type in custom_by_moltype` (add built-in ch4/thf so they aren't dropped when the ion inserter now labels them by type). Guest-writing branch (lines 340-393): when custom_active, resolve the residue name per-molecule — if `mol.mol_type in ("ch4","thf")` (built-in), use `get_hydrate_guest_residue_name(mol.mol_type)` (CH4_H/THF_H) + `reorder_guest_atoms` (built-in canonical order); elif `mol.mol_type in custom_by_moltype`, use the custom `residue_name` (MOL_H) + NO reorder. Fall back to the existing first-custom only for the literal "guest" mol_type (backward compat for the fallback path).

  3. quickice/output/ion_writer.py write_ion_top_file — guest_count (line 540): count ALL cage-guest mol_types (guest/ch4/thf/custom), not just "guest". When custom_active AND there are built-in cage guests, run `detect_guest_type_runs`-style per-molecule typing BUT keyed on `mol.mol_type` (not atom-name detection, which misidentifies ethanol). Run-length encode the [molecules] section: CH4_H run + MOL_H run (consecutive same-type). #include BOTH the built-in `{type}_hydrate.itp` (ch4_hydrate.itp) AND the custom ITP (etoh.itp). When custom_active but NO built-in cage guests (pure single-custom), keep the current single-MOL_H path byte-identical.

  4. quickice/output/guest_info.py _stage_hydrate_guest_itps — when custom_guest_info is non-empty AND the config's cage_guest_assignments also contains built-in assignments (ch4/thf), stage BOTH the built-in `{type}_hydrate.itp` AND the custom transformed ITP(s). Currently it stages only the custom ITP. The .top #include list must include both.

  REGRESSION TEST (tests/test_e2e_custom_guest_mixed_cage.py — NEW): mixed CH4 (small) + ethanol custom (large) sII hydrate -> slab -> solute -> ion -> GUI IonGromACSExporter -> gmx grompp. Assert: grompp rc=0; .gro has BOTH CH4_H (5-atom) and MOL_H (9-atom) residues (not all MOL_H); .top [molecules] declares both CH4_H and MOL_H; .top #includes both ch4_hydrate.itp and etoh.itp; CH4:ethanol ratio matches sII small:large (16:8 = 2:1). Also add a guard: single-custom-ethanol (no built-in) still produces only MOL_H (byte-identical to current). And: mixed built-in CH4+THF (Phase 45-15) still passes.

  INVARIANT TO PRESERVE: the single-custom-guest path (only ethanol, no built-in) and the mixed-built-in path (CH4+THF, no custom) must stay byte-identical. The new code only activates when BOTH a built-in AND a custom cage guest are present (the gap case).

  REPRODUCTION SCRIPTS (already on disk, reuse for verification):
  - tests/repro_molh_drop.py — single ethanol config=9 and config=6 (both pass grompp WITH the fix; confirms the single-guest stride fix works).
  - tests/repro_molh_prefixed6.py — pre-fix single ethanol config=6 (fails grompp; confirms fix is necessary for single-guest).
  - tests/repro_molh_mixed.py — mixed CH4+ethanol (FAILS grompp WITH the current fix; this is the second bug). After the new fix, this should PASS.
  Run: `QT_QPA_PLATFORM=offscreen python tests/repro_molh_mixed.py` (expect grompp rc=0 after the fix).

  VERIFICATION: after the fix, run `QT_QPA_PLATFORM=offscreen pytest tests/test_e2e_custom_guest_mixed_cage.py tests/test_e2e_custom_guest_cross_tab_gui.py tests/test_e2e_mixed_ion_export.py tests/test_e2e_custom_guest_hydrate.py -v` — all must pass. Then run the broader e2e suite to confirm no regressions.
verification: |
  IMPLEMENTED + VERIFIED. The fix was applied across 6 source files (4 from the plan + 2 necessary additions: _guest.py detect_guest_type_runs, solute_writer.py) + 1 existing test update + 1 new regression test.

  REPRO SCRIPTS:
  - tests/repro_molh_mixed.py (mixed CH4+ethanol): grompp rc=0 AFTER fix (was rc=1). .gro now has BOTH CH4_H (864×5=4320 atoms) and MOL_H (432×9=3888 atoms); .top [molecules] run-length encoded: CH4_H 432, MOL_H 216, CH4_H 432, MOL_H 216 (864 CH4 + 432 ethanol = 1296 cage guests); .top #includes both ch4_hydrate.itp and etoh.itp; both ITPs staged. CH4:ethanol = 864:432 = 2:1 (sII 16:8). FIXED.
  - tests/repro_molh_drop.py (single ethanol config=9 and =6): both grompp rc=0 AFTER fix (unchanged). MOL_H=1296, all 9-atom. Single-custom path PRESERVED.

  TARGETED E2E SUITE (QT_QPA_PLATFORM=offscreen pytest):
  - tests/test_e2e_custom_guest_mixed_cage.py (NEW, 7 tests): ALL PASS — grompp rc=0; .gro has both CH4_H (5-atom) + MOL_H (9-atom); .top declares both (run-length encoded); .top #includes both ch4_hydrate.itp + etoh.itp; CH4:ethanol=2:1; .gro runs == .top [molecules]; single-custom guard (only MOL_H, no CH4_H, grompp rc=0).
  - tests/test_e2e_custom_guest_cross_tab_gui.py (4 exporters): ALL PASS.
  - tests/test_e2e_custom_guest_hydrate.py (20 tests): ALL PASS.
  - tests/test_e2e_mixed_ion_export.py (7 tests, updated filters): ALL PASS — mixed built-in CH4+THF path preserved (4 runs CH4_H/THF_H/CH4_H/THF_H, 2:1 ratio, both ITPs staged).

  BROADER REGRESSION SWEEP:
  - tests/test_e2e_*.py (392 tests): ALL PASS (no regressions). Includes the sII lattice cross-tab CLI test that initially regressed (solute writer's mol_type=="guest" filter missed the new ch4/thf mol_types after the ion inserter mutates solute.interface_structure.molecule_index — fixed by updating the solute writer's filters to handle per-molecule mol_types).
  - tests/test_scancode_bugs_*.py (5 tests): ALL PASS.
  - targeted unit tests (build_molecule_index, custom_guest_bridge, gromacs_molecule_ordering, gromacs_moleculetype_names, e2e_stage_custom_guest_itp, e2e_ion_export, e2e_ion_insertion, e2e_solute_insertion — 108 tests): ALL PASS.

  BYTE-IDENTITY NOTE: run-to-run byte comparison is NOT possible because the slab assembler / ion insertion is non-deterministic (same code + same seed produces different guest positions + ion positions — pre-existing, NOT caused by this fix). The .top [molecules] section (residue names, run-length encoding, counts) is byte-identical run-to-run; only the random ion/guest coordinates vary. The invariant (guest HANDLING preserved for single-custom and mixed-built-in paths) is verified by the structural assertions in test_e2e_mixed_ion_export.py + test_e2e_custom_guest_mixed_cage.py, which pass consistently.

  AWAITING USER APPROVAL TO COMMIT (not yet committed per instructions).
files_changed:
  - quickice/structure_generation/ion_inserter.py (per-molecule mol_type + overlap check for all cage-guest types)
  - quickice/output/_guest.py (detect_guest_type_runs handles per-molecule mol_types)
  - quickice/output/guest_info.py (_detect_builtin_guest_types + recovery count + _stage_hydrate_guest_itps dual staging)
  - quickice/output/ion_writer.py (gro Pass 2 + per-molecule resname + top guest_count + run-length [molecules] + dual #include)
  - quickice/output/solute_writer.py (gro Pass 2 + top guest_count + guest_type detection — necessary due to ion inserter mutating shared interface.molecule_index)
  - tests/test_e2e_mixed_ion_export.py (updated mol_type filters for new per-molecule types)
  - tests/test_e2e_custom_guest_mixed_cage.py (NEW regression test, 7 tests)
