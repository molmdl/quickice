---
status: resolved
trigger: "Delete dead code (scancode CRIT-03 + CRIT-05, user-approved deletion). quickice/output/pdb_writer.py write_interface_pdb_file is DEAD CODE (zero callers, not exported) and contains two latent bugs: i//3 integer division (CRIT-03) and MW→M atom-name label (CRIT-05). The user approved DELETE (not wire-up)."
created: 2026-07-19T00:00:00Z
updated: 2026-07-19T00:05:00Z
---

## Current Focus

hypothesis: CONFIRMED — write_interface_pdb_file was dead code (zero callers, not exported). Deleted along with its now-unused InterfaceStructure import.
test: grep across all .py files + check output/__init__.py exports + import check + full non-GUI pytest suite.
expecting: function gone, suite green except documented pre-existing version-string failures.
next_action: DONE — fix committed (1e846db4), debug file archived.

## Symptoms

expected: write_interface_pdb_file is removed from pdb_writer.py. The two latent bugs (CRIT-03 i//3, CRIT-05 MW→M) no longer exist in the codebase. The reachable write_pdb_with_cryst1 still works.
actual: write_interface_pdb_file exists with two latent bugs but has zero callers and is not exported — pure dead code.
errors: None — dead code with latent bugs.
reproduction: Grep write_interface_pdb_file across the repo; observe zero callers.
started: Present since the function was written (added in phase 24-triclinic-transformation as an unused stub).

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-07-19T00:01:00Z
  checked: `grep -rn "write_interface_pdb_file" --include="*.py" .`
  found: Exactly ONE match in all .py files: `./quickice/output/pdb_writer.py:113:def write_interface_pdb_file(iface: InterfaceStructure, filepath: str) -> None:` (the definition itself). Zero callers in source. Zero callers in tests.
  implication: The function is never called anywhere in the codebase. Confirmed dead code.

- timestamp: 2026-07-19T00:01:30Z
  checked: `quickice/output/__init__.py` exports
  found: `__all__` and the `from quickice.output.pdb_writer import ...` line export ONLY `write_pdb_with_cryst1` and `write_ranked_candidates`. `write_interface_pdb_file` is NOT exported.
  implication: The function cannot be reached via `from quickice.output import *` or `quickice.output.write_interface_pdb_file` either. Fully unreachable.

- timestamp: 2026-07-19T00:02:00Z
  checked: `quickice/output/pdb_writer.py` line 11 import: `from quickice.structure_generation.types import Candidate, InterfaceStructure`
  found: `InterfaceStructure` is referenced ONLY in the dead function (lines 113, 116, 120 — signature + docstring). `Candidate` is used by the surviving `write_pdb_with_cryst1` and `write_ranked_candidates`.
  implication: After deleting the function, `InterfaceStructure` becomes an unused import and should be removed from line 11 to keep the file clean.

- timestamp: 2026-07-19T00:02:30Z
  checked: Environment
  found: `python -c "import numpy; print('ok', numpy.__version__)"` → `ok 2.4.3`. Env works.
  implication: Safe to run pytest.

## Resolution

root_cause: write_interface_pdb_file is dead code (defined but never called, not exported) carrying two latent bugs: CRIT-03 (i//3 hardcoded 3 atoms/ice) and CRIT-05 (atom_name[0] → MW→"M"). User approved deletion.
fix: Deleted the entire write_interface_pdb_file function (lines 113-174, 65 lines including trailing blanks) from quickice/output/pdb_writer.py. Removed the now-unused `InterfaceStructure` import from line 11 (it was used only in the deleted function's type hint); kept `Candidate` (still used by the surviving write_pdb_with_cryst1 and write_ranked_candidates). The reachable write_pdb_with_cryst1 and write_ranked_candidates were left UNTOUCHED.
verification: 
  - New regression test tests/test_scancode_bugs_dead_code_pdb.py (11 tests) — ALL PASS:
    * TestDeadFunctionDeleted (5 tests): function not an attribute of pdb_writer; not importable; not exported from output package; name absent from pdb_writer.py source; InterfaceStructure no longer imported.
    * TestReachableSurvivorStillWorks (6 tests): write_pdb_with_cryst1 still callable; writes valid PDB (CRYST1 + 12 HETATM + END); atom count matches positions; residue numbers correct (1,1,1,2,2,2,3,3,3,4,4,4 for 4×3-atom water); element labels correct (O/H only — no MW trigger); CRYST1 cell params correct (10 Å, 90° for 1 nm cubic).
  - Full non-GUI pytest suite (15 GUI/Qt/VTK files excluded): 1551 passed, 2 failed, 2 skipped, 0 new failures. The 2 failures are the documented pre-existing test_version_shows_version ("4.5.0" expected vs "4.7.0" actual — version-string mismatch in the test, unrelated to PDB writing; these tests do not import pdb_writer.py).
  - Import check: `hasattr(pdb_writer, 'write_interface_pdb_file')` → False; `write_pdb_with_cryst1` and `write_ranked_candidates` → True (survivors intact).
files_changed:
  - quickice/output/pdb_writer.py (1 insertion, 65 deletions)
  - tests/test_scancode_bugs_dead_code_pdb.py (new, 276 lines, 11 tests)
commit: 1e846db4 — "fix(scancode): delete dead write_interface_pdb_file (CRIT-03 + CRIT-05)"
gmx_available: yes — gmx 2023.5-plumed_2.9.3 at /data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx (noted for completeness; not relevant to PDB deletion).
