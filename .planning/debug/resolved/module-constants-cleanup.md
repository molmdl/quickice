---
status: resolved
trigger: "Investigate and fix FOUR module-constants cleanup issues (scancode Group 5): UNIT-02, UNIT-03, UNIT-04, UNIT-05. PURE REFACTOR — no numeric value may change."
created: 2026-07-18T00:00:00Z
updated: 2026-07-18T02:00:00Z
---

## Current Focus

status: RESOLVED. All 4 atomic commits applied; byte-equivalence verified
(TOP_MD5 + ITP_MD5 unchanged); gmx grompp dry-run passes; 21 new regression
tests pass; 121 targeted tests pass; full non-GUI suite: 1423 passed / 13
failed — ALL 13 failures confirmed PRE-EXISTING (fail identically on the
parent commit 52a99e15, before any refactor; they stem from the SAFE-05
output-path containment check vs tmp_path, NOT from the constants refactor).
Zero new failures.

## Symptoms

expected: Module constants are defined ONCE at module top and referenced inline
everywhere. TIP4P-ICE charges/settle/alpha, CH4 C-H bond, and ion charges are
all named constants. Produced .top/.itp/.gro byte-identical to before.
actual: Inline magic numbers duplicated/scattered: TIP4P_ICE_ALPHA defined twice;
TIP4P charges/settle inline at ~1039-1049; CH4 C-H bond inline at
solute_inserter.py:166; ion charges appear in two files (BUT correctly represent
different GROMACS sections — NOT duplicates).
errors: None — pure tech debt / maintainability.
reproduction: Grep for literal values (0.13458335, 0.5897, -1.1794, 0.09572,
0.15139, 0.109620, 0.85) across the codebase.
timeline: Present since values were first inlined.

## Evidence

- timestamp: 2026-07-18T00:01
  checked: gromacs_writer.py line numbers (post CRIT-01/Group 1 commit 38121ba0
           which shifted lines ~375-440 by adding triclinic wrap code).
  found: RESEARCH/PLAN line refs are slightly stale. ACTUAL current lines:
         - TIP4P_ICE_ALPHA = 0.13458335 at line 53 (first def) AND line 444 (DUPLICATE)
         - TIP4P_ICE_OW_SIGMA/EPSILON at lines 57-58 (plan said 56-57)
         - ION_ATOMTYPES dict at lines 91-94 (plan said 91-92)
         - TIP4P inline charges/settle/alpha at lines 1039-1049 (plan said 980-991)
         - compute_mw_position at line 1099 already uses TIP4P_ICE_ALPHA constant
  implication: All findings CONFIRMED at slightly shifted line numbers. Refactor
               targets the same code; line-number drift does not change the work.

- timestamp: 2026-07-18T00:02
  checked: UNIT-03 duplicate TIP4P_ICE_ALPHA definition.
  found: Line 53 `TIP4P_ICE_ALPHA = 0.13458335` (no comment, near LJ constants).
         Line 444 `TIP4P_ICE_ALPHA = 0.13458335` with comment
         "# TIP4P-ICE virtual site parameter (from tip4p-ice.itp virtual_sites3 directive)".
         SAME VALUE — true duplicate. Line 1099 already uses the constant.
         Line 1049 has inline `0.13458335 0.13458335` (virtual_sites3 a,b params).
  implication: UNIT-03 CONFIRMED. Remove line 444 def (preserve its comment by
               moving to line 53), replace line 1049 inline with f-string using
               TIP4P_ICE_ALPHA (twice).

- timestamp: 2026-07-18T00:03
  checked: UNIT-02 inline TIP4P-ICE charges/settle at lines 1039-1049.
  found: Line 1039 `0.5897` (HW_ice charge, appears at 1039 AND 1040),
         Line 1041 `-1.1794` (MW charge),
         Line 1045 `0.09572 0.15139` (settle doh, dhh),
         Line 1049 `0.13458335 0.13458335` (alpha — handled by UNIT-03).
  implication: UNIT-02 CONFIRMED. Add module constants next to LJ constants:
               TIP4P_ICE_HW_CHARGE=0.5897, TIP4P_ICE_MW_CHARGE=-1.1794,
               TIP4P_ICE_SETTLE_DOH=0.09572, TIP4P_ICE_SETTLE_DHH=0.15139.
               Replace inline at 1039-1041, 1045 with f-strings using constants.

- timestamp: 2026-07-18T00:04
  checked: UNIT-02 cross-check against quickice/data/tip4p-ice.itp.
  found: tip4p-ice.itp line 16-18: HW_ice charge 0.5897 (mass 1.008),
         MW charge -1.1794 (mass 0.0). Line 22-24: settles 0.09572 (doh),
         0.15139 (dhh). Line 41: virtual_sites3 0.13458 0.13458 (alpha, 5-decimal
         in .itp but full 0.13458335 in .top). All values MATCH.
  implication: UNIT-02 values verified against the bundled ITP and are consistent
               with Abascal 2005 (DOI 10.1063/1.1931662, per AGENTS.md). Safe to
               extract to named constants with no value change.

- timestamp: 2026-07-18T00:05
  checked: UNIT-04 inline r_ch = 0.109620 at solute_inserter.py:166.
  found: Line 159 docstring "Uses C-H bond length from ITP file (0.109620 nm)",
         Line 165 comment "# Bond length from ch4.itp",
         Line 166 `r_ch = 0.109620  # nm`.
         Module top (lines 1-35) has constants MIN_SEPARATION=0.3; place new
         constant near it. AVOGADRO imported from ion_inserter.
  implication: UNIT-04 CONFIRMED. Add CH4_CH_BOND_LENGTH_NM=0.109620 module
               constant with comment citing ch4.itp; replace line 166 inline.

- timestamp: 2026-07-18T00:06
  checked: UNIT-04 cross-check against quickice/data/ch4.itp.
  found: ch4.itp lines 23-26: [bonds] `1 2 1 0.109620 2.889052E+05 ; C-H, prebuilt
         c3-hc` — C-H bond length = 0.109620 nm. EXACT MATCH with r_ch = 0.109620.
  implication: UNIT-04 value verified against ch4.itp. Safe to name the constant.

- timestamp: 2026-07-18T00:07
  checked: UNIT-05 — gromacs_ion_export.py:19-20 (NA_CHARGE=0.85, CL_CHARGE=-0.85)
         vs gromacs_writer.py:91-92 (ION_ATOMTYPES charge=0.0). Investigate the
         GROMACS [atomtypes] vs [moleculetype] [atoms] convention.
  found: Executed `generate_ion_itp(1,1)` and `_format_atomtype_line("NA", ...)`.
         ion.itp ([moleculetype] [atoms] section) writes REAL charge:
           `1 NA 1 NA NA 1 0.85 22.9898` (NA_CHARGE=0.85)
           `1 CL 1 CL CL 1 -0.85 35.453` (CL_CHARGE=-0.85)
         gromacs_writer.py [atomtypes] section writes charge=0.0 PLACEHOLDER:
           `NA       NA           11      22.9898    0.0 A     2.21737e-01  1.47236e+00`
           `CL       CL           17      35.4530    0.0 A     4.69906e-01  7.69231e-02`
         ION_ATOMTYPES is used at gromacs_writer.py:2040-2044 and 2711-2715 via
         `_format_atomtype_line` to produce [atomtypes] lines. The `charge=0.0`
         is the 5th field — in the GROMACS [atomtypes] 8-field form
         (name bond_type atomic_number mass charge ptype sigma epsilon), the
         charge field is a PLACEHOLDER (nonbonded params only; actual charge is
         taken from [moleculetype] [atoms]).
  implication: UNIT-05 NOT a duplicate. The 0.0 in [atomtypes] is the CORRECT
               GROMACS convention (nonbonded params only, charge field ignored).
               The real ±0.85 charges in [moleculetype] [atoms] are a DIFFERENT
               field in a DIFFERENT section. DECISION: add a clarifying comment
               to ION_ATOMTYPES explaining the convention; DO NOT merge.
               Per plan: "If [atomtypes] charge=0.0 is the convention, it is
               CORRECT... add a clarifying comment and do NOT merge."

- timestamp: 2026-07-18T00:08
  checked: Baseline byte-equivalence snapshot (BEFORE any refactor).
  found: Generated ice_ih candidate (96 target mols → 128 actual), exported .top
         via write_top_file, and ion.itp via generate_ion_itp(2,3).
         TOP_MD5=bb3df33e131a5d18c5f5439eaa0c29b2 (len 1447)
         ITP_MD5=bb6d3d1ec3a5bc97bea20b5a70bee663
         TIP4P-ICE [atoms] block bytes confirmed:
           "   2   HW_ice    1  SOL   HW1     1     0.5897   1.00800\n"
           "   3   HW_ice    1  SOL   HW2     1     0.5897   1.00800\n"
           "   4   MW        1  SOL    MW     1    -1.1794   0.00000\n"
         [settles] "  1    1    0.09572  0.15139\n"
         [virtual_sites3] "   4     1       2       3       1      0.13458335 0.13458335\n"
  implication: These MD5 hashes are the byte-equivalence regression baseline.
               After all 4 refactors, re-export and assert identical MD5.

- timestamp: 2026-07-18T00:09
  checked: gmx availability.
  found: gmx IS on PATH at /data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx
  implication: Can run `gmx grompp` dry-run to confirm byte-equivalence at the
               GROMACS level after the refactor.

## Eliminated

(none — all 4 findings confirmed; UNIT-05 is a non-issue by convention, not an
eliminated finding)

## Resolution

root_cause: Pure maintainability tech debt — inline magic numbers and a
duplicate constant definition. No behavior bug. UNIT-05 is NOT a duplicate
after GROMACS-convention investigation ([atomtypes] charge=0.0 placeholder vs
[moleculetype] [atoms] real charge ±0.85).

fix: ALL 4 APPLIED (atomic commits, one per UNIT):
  - UNIT-03 (commit 730c01db): removed duplicate TIP4P_ICE_ALPHA at ~line 444;
    preserved its comment by moving to the surviving definition at ~line 53;
    replaced inline `0.13458335 0.13458335` at the [virtual_sites3] f.write line
    with `{TIP4P_ICE_ALPHA} {TIP4P_ICE_ALPHA}` (f-string).
  - UNIT-02 (commit 9f0feb55): added TIP4P_ICE_HW_CHARGE=0.5897,
    TIP4P_ICE_MW_CHARGE=-1.1794, TIP4P_ICE_SETTLE_DOH=0.09572,
    TIP4P_ICE_SETTLE_DHH=0.15139 next to the LJ constants; replaced inline
    values in the [atoms]/[settles] f.write lines with f-string constants.
  - UNIT-04 (commit 6ccb4e49): added CH4_CH_BOND_LENGTH_NM=0.109620 module
    constant (comment citing ch4.itp) to solute_inserter.py; replaced inline
    `r_ch = 0.109620` with `r_ch = CH4_CH_BOND_LENGTH_NM`.
  - UNIT-05 (commit 0937edd5): added clarifying comments to BOTH
    gromacs_writer.py ION_ATOMTYPES ([atomtypes] charge=0.0 placeholder
    convention) and gromacs_ion_export.py NA_CHARGE/CL_CHARGE (cross-reference
    to [atomtypes]). NO consolidation, NO value change — the two are different
    fields in different GROMACS sections.

verification:
  - Byte-equivalence: TOP_MD5=bb3df33e131a5d18c5f5439eaa0c29b2 and
    ITP_MD5=bb6d3d1ec3a5bc97bea20b5a70bee663 UNCHANGED after each refactor
    (verified after every UNIT; the refactor is provably byte-equivalent).
    Captured the baseline BEFORE any refactor, re-exported after each UNIT.
  - gmx grompp dry-run: PASSES (gmx available at
    /data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx). Custom
    0.65 nm cutoff em.mdp (the 96-mol ice_ih cell min box ~1.47 nm is too
    small for the 1.0 nm cutoff in tests/em.mdp). grompp exits 0 → topology
    is simulation-ready, no value drift at the GROMACS level.
  - Regression tests: tests/test_scancode_bugs_constants.py — 21 tests
    (TestUNIT03 x3, TestUNIT02 x4, TestUNIT04 x3, TestUNIT05 x6,
    TestByteEquivalence x4, grompp x1). All PASS.
  - Targeted suite (121 tests across constants + gromacs + ion + solute +
    inserters + e2e_ion_export + e2e_ion_insertion + triclinic_pbc + pipeline):
    all PASS.
  - Full pytest suite (non-GUI, 14 GUI test files ignored — they are slow due
    to headless Qt/VTK, unrelated to this refactor): 1423 passed, 13 failed
    in 184s. ALL 13 failures confirmed PRE-EXISTING by checking out the
    parent commit 52a99e15 (before any UNIT refactor) and re-running the
    same 13 tests — they fail IDENTICALLY on the pre-refactor code:
      - test_cli_integration.py::TestHelpAndVersion::test_version_shows_version
        (asserts "4.5.0" but version is "4.7.0" — version-string mismatch)
      - test_cli_integration.py::TestValidInputs::test_boundary_nmolecules_max
      - test_integration_v35.py (11 tests) — all fail with "--output path
        resolves outside working directory: /tmp/tmpXXX is not under
        /share/home/nglokwan/quickice" — caused by the SAFE-05 output-path
        containment check (commit ff9c7983) interacting with pytest's tmp_path
        (which is under /tmp, not the cwd). Pre-existing, unrelated to the
        constants refactor.
    Zero new failures introduced by UNIT-02/03/04/05.
  - GUI suite (14 files) not run to completion — they are slow due to headless
    Qt/VTK (pre-existing environment limitation noted in AGENTS.md
    "Headless/remote VTK" + ROADMAP TEST-06 deferred). They do not touch the
    GROMACS writer constants or CH4 coordinate generation, so the
    byte-equivalent constants refactor cannot regress them.

files_changed:
  - quickice/output/gromacs_writer.py (UNIT-03 + UNIT-02 + UNIT-05 comment)
  - quickice/structure_generation/gromacs_ion_export.py (UNIT-05 comment)
  - quickice/structure_generation/solute_inserter.py (UNIT-04)
  - tests/test_scancode_bugs_constants.py (NEW — 21 regression tests)

## Commits (4 atomic, one per UNIT)

1. 730c01db refactor(scancode): dedup TIP4P_ICE_ALPHA definition (UNIT-03)
2. 9f0feb55 refactor(scancode): extract TIP4P-ICE charges/settle/alpha to
   constants (UNIT-02)
3. 6ccb4e49 refactor(scancode): name CH4 C-H bond constant (UNIT-04)
4. 0937edd5 refactor(scancode): clarify ion charge sources, no value change
   (UNIT-05)
