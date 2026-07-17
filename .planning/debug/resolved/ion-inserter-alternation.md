---
status: resolved
trigger: "Investigate and fix TWO related issues in ion_inserter.py: CRIT-02 (ion alternation parity) and SUSP-01 (3-atom GenIce fallback miscount). Two atomic commits."
created: 2026-07-17T00:00:00Z
updated: 2026-07-17T01:30:00Z
---

## Current Focus

hypothesis: BOTH root causes CONFIRMED by reading code. CRIT-02 fix is
  unambiguous (no conflict). SUSP-01 "raise" fix has an UNANTICIPATED
  CONFLICT with an existing passing test (test_nmolecules_fields.py) that
  feeds 3-atom GenIce into the same fallback and expects it to RETURN
  non-None (compute) rather than raise.
test: (CRIT-02) apply placed_count counter, run ion suite. (SUSP-01) decide
  resolution with user via CHECKPOINT before applying.
expecting: CRIT-02 commit lands cleanly. SUSP-01 needs user decision on
  whether to (A) raise + update the existing test, or (B) compute //3 for
  3-atom (deviates from deliverable's "assert raises" test spec).
next_action: Apply CRIT-02 fix + test, verify, commit. Then CHECKPOINT on
  SUSP-01 design.

## Symptoms

CRIT-02:
  expected: Na/Cl strictly alternate by PLACEMENT order; a rejected
    (overlap) candidate does not change which ion the next placed ion gets.
  actual: `if i % 2 == 0:` (line 458) keys off enumerate index `i`; the two
    `continue` overlap-skips (lines 444, 451) still advance `i`, flipping
    parity for all later placed ions -> spatial clustering (adjacent
    same-charge ions).
  errors: none (silent spatial artifact; charge-neutral trim keeps net
    charge zero, so only the spatial ARRANGEMENT is wrong).
  reproduction: ion insertion where >=1 selected water candidate is
    rejected for overlap; inspect placed Na/Cl sequence -- not alternating
    relative to placement order.
  started: present since the alternation logic was written.

SUSP-01:
  expected: fallback at line 103 either raises a clear error or computes
    correctly for 3-atom GenIce -- never silently returns 75 mols for 300
    atoms.
  actual: `ice_mols = ice_atom_count // WATER_ATOMS_PER_MOLECULE` (4) ->
    300 // 4 = 75 (wrong for 3-atom GenIce where 300 atoms = 100 mols).
    Only reached when ice_nmolecules == 0 AND interface_structure is None.
  errors: none (silent miscount feeding downstream concentration/volume).
  reproduction: call ion insertion with 3-atom GenIce (300 atoms),
    ice_nmolecules==0, interface_structure=None; ice_mols becomes 75.
  started: present since the fallback was written.

## Eliminated

(none yet)

## Evidence

- 2026-07-17 CONFIRMED CRIT-02 by reading ion_inserter.py:
  - line 431: `for i, water_idx in enumerate(selected):`
  - line 444: `continue` (existing_atoms_tree min_dist < MIN_SEPARATION)
  - line 451: `continue` (ion_tree min_ion_dist < MIN_SEPARATION)
  - line 458: `if i % 2 == 0:` -- uses enumerate index, NOT placement counter
  - lines 488-510: charge-neutrality trim (correct, must stay; only spatial
    alternation was wrong). Verified the trim removes excess Na/Cl from the
    end of new_molecule_index.

- 2026-07-17 CONFIRMED SUSP-01 by reading ion_inserter.py:
  - lines 95-103: `if ice_mols == 0 and ice_atom_count > 0:` -> try
    interface_structure fallback (lines 97-99) -> if still 0:
    `ice_mols = ice_atom_count // WATER_ATOMS_PER_MOLECULE` (line 103, =4).
  - For 3-atom GenIce (atom_names[0]=="O"), this silently computes 75 for
    300 atoms. WATER_ATOMS_PER_MOLECULE (4) is only correct for TIP4P-family
    (atom_names[0]=="OW", 4 atoms/mol incl. MW).
  - types.py has detect_atoms_per_molecule(atom_names) -> 4 if
    atom_names[0]=="OW" else 3 (NOT imported in ion_inserter.py currently).
  - Water fallback at lines 104-110 has the same pattern but is always
    correct (water is always 4-atom TIP4P per codebase). Out of SUSP-01 scope.

- 2026-07-17 CRITICAL CONFLICT found for SUSP-01 "raise" fix:
  - tests/test_nmolecules_fields.py::TestIonInserterBuildMoleculeIndexRobustness
    ::test_build_molecule_index_uses_atom_count_fallback (lines 226-285)
    feeds a SimpleNamespace("buggy_structure") with:
      atom_names=interface_slab.atom_names (3-atom GenIce, "O","H","H"),
      ice_atom_count=9216, ice_nmolecules=0, interface_structure=None,
      molecule_index=[] (triggers the fallback)
    and asserts `mol_index is not None` + ice/water entries exist.
  - Verified interface_slab is 3-atom: atom_names[0]=='O', 3 atoms/mol, no MW
    (ice_atom_count=9216, ice_nmolecules=3072 -> 9216/3072=3).
  - BASELINE: this existing test PASSES today (the //4 fallback returns
    2304 ice entries -- WRONG count but >0, so the test's "entries exist"
    assertions pass; the test does NOT check count correctness, only that
    the fallback returns non-None).
  - Under the SUSP-01 "raise" fix (raise when atom_names[0] != "OW"), this
    test would RAISE -> the unwrapped call `mol_index = inserter._build_...`
    would raise ValueError -> test FAILS.
  - Verified a 4-atom fixture exists: interface_hydrate_slab has
    atom_names[0]=='OW', 4 atoms/mol, WITH MW (ice_atom_count=6624,
    ice_nmolecules=1656 -> 4). So the existing test COULD be switched to a
    4-atom interface to preserve its "compute fallback works" intent for
    the 4-atom path (which the fix preserves), leaving the 3-atom raise to
    the new test file.
  - The other `ice_nmolecules=0` matches (test_scancode_bugs_triclinic_pbc.py:438,
    test_e2e_gmx_validation.py:1139, test_output/*, test_e2e_custom_guest*) all
    set ice_atom_count=0 too (hydrate with no crystalline ice) -> line 95
    `ice_atom_count > 0` is FALSE -> fallback NOT triggered -> NOT affected.

- 2026-07-17 Environment: conda env `quickice`, Python 3.14.3. gmx IS on PATH
  (/data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx). pytest
  default discovery. No linter/formatter.

## Resolution

root_cause:
  CRIT-02: alternation parity keys off enumerate index `i` (line 458), not a
    placement counter; overlap `continue` skips (444, 451) advance `i` and
    flip Na/Cl parity for all later placed ions.
  SUSP-01: line 103 fallback assumes 4 atoms/ice (WATER_ATOMS_PER_MOLECULE)
    for ALL ice, silently miscounting 3-atom GenIce (75 mols for 300 atoms).
fix:
  CRIT-02: DONE + COMMITTED (dbb802d). Added `placed_count = 0` before the
    enumerate loop; increment ONLY on successful placement (after both
    continue guards); replaced `if i % 2 == 0:` with `if placed_count % 2
    == 0:`. Charge-neutrality trim unchanged.
  SUSP-01: DONE + COMMITTED (985eee1). Guarded the ice fallback at ~line
    103: use `WATER_ATOMS_PER_MOLECULE` (//4) ONLY when the ice is confirmed
    4-atom TIP4P-family (first atom "OW" per detect_atoms_per_molecule);
    otherwise raise ValueError explaining the 3-atom GenIce miscount and
    telling the caller to supply ice_nmolecules. Water fallback (always
    4-atom TIP4P) and the normal path (ice_nmolecules available) unchanged.
    Existing test test_nmolecules_fields.py::...::test_build_molecule_index_
    uses_atom_count_fallback switched from 3-atom interface_slab to 4-atom
    interface_hydrate_slab (per user Option A) so it exercises the PRESERVED
    4-atom compute fallback; the 3-atom raise is covered by the new tests.
verification:
  CRIT-02: VERIFIED.
    - New test TestCRIT02 (2 tests) PASS with fix.
    - Catches the bug: with fix stashed, test_rejected_candidate_does_not_flip_parity
      FAILS `assert 1 == 2` (buggy: 3 Na + 1 Cl -> trim -> 1 Na + 1 Cl at
      [5,0,0] & [8,0,0]; fix: 2 Na + 2 Cl at [5,6,7,8], alternating).
  SUSP-01: VERIFIED.
    - New test TestSUSP01 (4 tests) PASS with fix.
    - Catches the bug: with SUSP-01 fix stashed, the 2 raise tests FAIL
      "DID NOT RAISE" (buggy //4 silently returns 75); the 4-atom and
      ice_nmolecules-present tests PASS without the fix (surgical).
  Full-suite regression: non-GUI suite 1459 passed, 2 failed -- BOTH are the
    pre-existing version-string tests (test_*::test_version_shows_version:
    assert '4.5.0' in 'python -m quickice 4.7.0'). Confirmed PRE-EXISTING by
    stashing my changes and re-running: they still fail (version is project-
    wide, unrelated to ion_inserter.py). The 4 GUI dialog/panel/renderer test
    files were excluded due to the known headless Qt/VTK hang (pre-existing
    per deliverable); the ion-adjacent GUI tests (test_ion_source_dropdown,
    test_scancode_bugs_ion_charge_warning, test_solute_insertion) PASS under
    QT_QPA_PLATFORM=offscreen. `-k ion` subset: 547 passed, 2 failed (same
    pre-existing version tests; "version" matches -k ion because it contains
    "ion"). gmx IS on PATH; gmx grompp ion-export validation tests ran (not
    skipped) and passed -> ion topology valid after the change.
files_changed:
  - quickice/structure_generation/ion_inserter.py (CRIT-02 dbb802d; SUSP-01 985eee1)
  - tests/test_scancode_bugs_ion_inserter.py (CRIT-02 tests dbb802d; SUSP-01 tests 985eee1)
  - tests/test_nmolecules_fields.py (existing test switched to 4-atom interface, 985eee1)
