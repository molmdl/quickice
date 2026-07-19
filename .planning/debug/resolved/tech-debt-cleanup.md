---
status: resolved
trigger: "Investigate and fix TWO tech-debt issues (scancode Group 8): TD-ADHOC (replace 7 type('obj', (object,), {...})() in gromacs_writer.py with MoleculeIndex dataclass) and TD-07 (atomtype-conflict validation in molecule_validator.py:185). Two atomic commits."
created: 2026-07-19T00:00:00Z
updated: 2026-07-19T09:50:00Z
---

## Current Focus

hypothesis: BOTH fixes committed and verified. TD-ADHOC = commit 92464737 (18 new tests pass, behavior-preserving). TD-07 = commit 7be40ee3 (17 new tests pass; full non-GUI suite 2 pre-existing version failures only, ZERO new failures; gmx grompp dry-run confirms the error now surfaces at validation time with a clear message + rename guidance instead of later at grompp with a confusing duplicate-atomtype error).
test: Final verification — `python -m pytest tests/test_scancode_bugs_tech_debt.py -v` → 35 passed. Full non-GUI suite (15 GUI/Qt/VTK files excluded, QT_QPA_PLATFORM=offscreen, 180s timeout) → 2 failed, 1534 passed in 197.79s. The 2 failures are the pre-existing version-string tests (assert "4.5.0" vs actual "4.7.0" in quickice/__init__.py); verified pre-existing by checking out parent commit 92464737 and confirming the same 2 tests fail identically there. gmx available (GROMACS 2023.5 + PLUMED 2.9.3); gmx grompp dry-run on a built-in-atomtype-conflicting upload shows the OLD confusing error ("Atomtype OW_ice was defined previously...") that TD-07 now surfaces earlier with a clear rename hint.
expecting: All verification criteria met. Archiving debug file.
next_action: Archive debug file to .planning/debug/resolved/ and commit as a docs commit (matches prior groups' pattern; .planning/config.json has commit_docs=true and .planning is not gitignored).

## Symptoms

### TD-ADHOC
expected: 7 anonymous-class instances use a proper @dataclass (MoleculeIndex), with identical fields and values; behavior preserved (drop-in replacement).
actual: 7 sites use type('obj', (object,), {...})() — ad-hoc, hard to read/type/maintain.
errors: None — tech debt / maintainability.
reproduction: Grep type('obj', (object,), in gromacs_writer.py; observe 7 occurrences.
timeline: Present since the anonymous-class pattern was introduced.

### TD-07
expected: A user upload that redefines a built-in atomtype name (OW_ice, HW_ice, MW, NA, CL) is rejected at upload time with a clear validation error, BEFORE gmx grompp fails confusingly.
actual: validate_custom_molecule only checks atomtypes PRESENCE (if not itp_info.has_atomtypes_section), not CONFLICT. A redefining upload passes validation and fails later at gmx grompp with a confusing duplicate-atomtype error.
errors: No validation error at upload — confusing gmx grompp error later.
reproduction: Upload a custom molecule that redefines OW_ice (or NA/CL); observe it passes validation; run gmx grompp; observe a confusing duplicate-atomtype error.
timeline: Present since the validator was written.

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-07-19T00:00:00Z
  checked: env (conda quickice)
  found: `python -c "import numpy; print('ok', numpy.__version__)"` → `ok 2.4.3`. Env works.
  implication: Can run pytest and python.

- timestamp: 2026-07-19T00:00:00Z
  checked: Grep `type('obj', \(object,\)` in quickice/output/gromacs_writer.py
  found: 7 matches at lines 2205, 2216, 3487, 3494, 3520, 3536, 3546 (shifted from plan's ~2133/~2144/~3415/~3422/~3448/~3464/~3474 because Group 5 already modified the file).
  implication: TD-ADHOC finding CONFIRMED at shifted line numbers. All 7 sites use the SAME 3 fields: start_idx, count, mol_type.

- timestamp: 2026-07-19T00:00:00Z
  checked: quickice/structure_generation/types.py:62-80 (MoleculeIndex dataclass)
  found: `@dataclass class MoleculeIndex: start_idx: int; count: int; mol_type: str` — EXACTLY the 3 fields used by the 7 ad-hoc sites.
  implication: MoleculeIndex ALREADY EXISTS with the exact field shape. No new dataclass needed. Already imported at gromacs_writer.py:16. TD-ADHOC is a pure drop-in replacement.

- timestamp: 2026-07-19T00:00:00Z
  checked: molecule_validator.py:185 (TD-07 site)
  found: `if not itp_info.has_atomtypes_section: warnings.append(...)` — checks PRESENCE only, not CONFLICT. Finding CONFIRMED.
  implication: Need to add a CONFLICT check using user-defined atomtype names (from the [ atomtypes ] section) intersecting with built-in names {OW_ice, HW_ice, MW, NA, CL}.

- timestamp: 2026-07-19T00:00:00Z
  checked: itp_parser.py ITPMoleculeInfo dataclass + parse_itp_file
  found: ITPMoleculeInfo has molecule_name, atom_count, atom_types (from [ atoms ] section), atom_names, charges, has_atomtypes_section. Does NOT parse names DEFINED in the [ atomtypes ] section.
  implication: To check redefinition conflicts, need the names in the user's [ atomtypes ] section. Plan: extend ITPMoleculeInfo with `atomtype_names: List[str] = field(default_factory=list)` (backward-compat default) and parse them in parse_itp_file.

- timestamp: 2026-07-19T00:00:00Z
  checked: All callers of ITPMoleculeInfo(...) constructor
  found: 2 construction sites — itp_parser.py:153 (parser, uses kwargs) and tests/test_scancode_bugs_ion_charge_warning.py:30 (test, uses kwargs without atomtype_names). Adding `atomtype_names` with `field(default_factory=list)` default keeps both working.
  implication: Safe to extend ITPMoleculeInfo with a default-factory list field.

- timestamp: 2026-07-19T00:00:00Z
  checked: All callers of validate_custom_molecule
  found: GUI caller at quickice/gui/custom_molecule_panel.py:641 (user-facing upload path — errors surface via validation_result.errors displayed red in the panel). Test callers in test_e2e_custom_molecule.py, test_custom_molecule.py, test_custom_molecule_panel_34_6.py.
  implication: Adding a blocking error to validation_result.errors will surface to the user in the GUI as a red validation message. This is the desired UX (clear error at upload time).

- timestamp: 2026-07-19T00:00:00Z
  checked: Test fixtures for existing custom-molecule ITPs (etoh.itp, etoh_no_atomtypes.itp, na_single.itp, test_custom_molecule.py inline ITPs, test_e2e_custom_molecule.py write_minimal_itp)
  found: etoh.itp defines {hc, c3, h1, oh, ho} — NONE in conflict set. etoh_no_atomtypes.itp has no [ atomtypes ] section. na_single.itp defines {NA} but is only used by test_scancode_bugs_ion_charge_warning.py which calls parse_itp_file (NOT validate_custom_molecule) — unaffected. test_custom_molecule.py inline ITPs use {CT, OH, HO, HC} with NO [ atomtypes ] section — conflict check gated on has_atomtypes_section=True skips them. test_e2e_custom_molecule.py write_minimal_itp uses {hc} — not in conflict set.
  implication: TD-07 conflict check (gated on has_atomtypes_section=True AND name in {OW_ice,HW_ice,MW,NA,CL}) will NOT break any existing test. Safe.

- timestamp: 2026-07-19T00:00:00Z
  checked: Whether structure_generation already imports from output (precedent for cross-package import direction)
  found: No `from quickice.output` imports in quickice/structure_generation/. output imports from structure_generation (output is higher-level).
  implication: To preserve layering, define BUILTIN_ATOMTYPE_NAMES conflict set in molecule_validator.py (the consumer) as a frozenset literal with a comment citing gromacs_writer.py WATER_ATOMTYPES + ION_ATOMTYPES as source of truth, guarded by a sync test that imports the dicts and asserts equality. Avoids reverse cross-package import.

## Resolution

root_cause:
  - TD-ADHOC: 7 sites in gromacs_writer.py use ad-hoc `type('obj', (object,), {start_idx, count, mol_type})()` instead of the existing MoleculeIndex dataclass (already defined in types.py:62-80, already imported). Pure tech debt — behavior is correct but the pattern is unreadable and untyped.
  - TD-07: molecule_validator.py:185 only checks `[ atomtypes ]` PRESENCE (`if not itp_info.has_atomtypes_section`), not whether the user's `[ atomtypes ]` section REDEFINES a built-in atomtype name (OW_ice/HW_ice/MW/NA/CL). A redefining upload passes validation and fails later at `gmx grompp` with a confusing duplicate-atomtype error (`"Atomtype OW_ice was defined previously..."`).

fix:
  - TD-ADHOC (commit 92464737): Replaced 7 `type('obj', (object,), {...})()` with `MoleculeIndex(start_idx=..., count=..., mol_type=...)` in gromacs_writer.py. Drop-in — MoleculeIndex already has the exact fields. 18 new regression tests added to tests/test_scancode_bugs_tech_debt.py (TestMoleculeIndexAdhoc class).
  - TD-07 (commit 7be40ee3): (1) Extended ITPMoleculeInfo with `atomtype_names: List[str] = field(default_factory=list)` and parse the [ atomtypes ] section names in parse_itp_file (first column of each data line; skips comments/`;`/`#` and stray <2-field fragments). (2) Added `BUILTIN_ATOMTYPE_NAMES` frozenset {OW_ice, HW_ice, MW, NA, CL} to molecule_validator.py (literal with comment citing gromacs_writer.py WATER_ATOMTYPES + ION_ATOMTYPES as source of truth). (3) In validate_custom_molecule, when has_atomtypes_section=True, check `set(itp_info.atomtype_names) & BUILTIN_ATOMTYPE_NAMES`; on intersection, append a BLOCKING error with rename guidance (e.g. `OW_ice -> OW_custom`). 17 new regression tests added (TestTD07BuiltinAtomtypeNamesSet, TestTD07ParseITPExtractsAtomtypeNames, TestTD07ValidateRejectsAtomtypeConflicts) — including a sync test `test_builtin_atomtype_names_match_gromacs_writer` that guards the literal against drift in gromacs_writer.py.

verification:
  - TD-ADHOC + TD-07 test file: 35 passed in 0.37s (18 TD-ADHOC + 17 TD-07).
  - Full non-GUI suite (15 GUI/Qt/VTK files excluded, QT_QPA_PLATFORM=offscreen, 180s per-test timeout): 2 failed, 1534 passed in 197.79s. The 2 failures are the pre-existing version-string tests (test_cli_integration.py::test_version_shows_version, test_entry_point.py::test_version_shows_version — assert "4.5.0" but quickice/__init__.py has __version__ = "4.7.0"). Verified PRE-EXISTING by checking out parent commit 92464737 (before TD-07) and confirming the same 2 tests fail identically there. ZERO new failures from TD-ADHOC or TD-07.
  - gmx available (GROMACS 2023.5 + PLUMED 2.9.3). gmx grompp dry-run on a built-in-atomtype-conflicting upload (OW_ice redefined in user ITP + main .top also defines OW_ice) confirms the OLD confusing error surface: `"Atomtype OW_ice was defined previously (e.g. in the forcefield files), self-contained molecule .itp file that duplicates or replaces the..."`. TD-07 now surfaces this error at VALIDATION time with a clear, user-facing message + rename guidance (OW_ice -> OW_custom) BEFORE grompp runs.

files_changed:
  - TD-ADHOC (commit 92464737): quickice/output/gromacs_writer.py (7 ad-hoc type() sites → MoleculeIndex), tests/test_scancode_bugs_tech_debt.py (TestMoleculeIndexAdhoc, 18 tests).
  - TD-07 (commit 7be40ee3): quickice/structure_generation/itp_parser.py (atomtype_names field + parser), quickice/structure_generation/molecule_validator.py (BUILTIN_ATOMTYPE_NAMES + conflict check in validate_custom_molecule), tests/test_scancode_bugs_tech_debt.py (3 TD-07 test classes, 17 tests).

## Commits

- 92464737: refactor(scancode): replace ad-hoc type() objects with MoleculeIndex dataclass (TD-ADHOC)
- 7be40ee3: fix(scancode): reject built-in atomtype conflicts at upload (TD-07)

## Outcome

Both TD-ADHOC and TD-07 applied as two atomic commits. TD-ADHOC is a pure
behavior-preserving refactor (MoleculeIndex drop-in). TD-07 closes a real
UX gap: uploads redefining built-in atomtype names (OW_ice/HW_ice/MW/NA/CL)
are now rejected at upload time with a clear rename hint, instead of failing
later at `gmx grompp` with a confusing duplicate-atomtype error buried in
grompp's verbose output. Full non-GUI suite: 2 pre-existing version-string
failures only, ZERO new failures.
