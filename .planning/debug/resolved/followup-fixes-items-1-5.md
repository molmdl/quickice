---
status: investigating
trigger: "Investigate and fix FIVE follow-up scancode issues (Items 1-5) that surfaced after Group 9 landed"
created: 2026-07-19T00:00:00Z
updated: 2026-07-19T00:00:00Z
---

## Current Focus

hypothesis: All 5 items committed. Running full verification suite.
test: pytest tests/test_scancode_bugs_*.py, pytest -k inserter, QT_QPA_PLATFORM=offscreen pytest -k vtk, full non-GUI suite.
expecting: All new tests pass, zero new failures in full suite (pre-existing failures only).
next_action: Run verification suites and report results.

## Resolution

root_cause: 
  - Item 1: README.md:208-213 said tip4p_ice.itp (underscore) but code exports tip4p-ice.itp (hyphen). FIXED.
  - Item 2: types.py:33 had wrong title for DOI 10.1063/1.1931662. FIXED.
  - Item 3: types.py:38 had 404 DOI 10.1063/1.2121600. FIXED to 10.1063/1.2121687.
  - Item 4: Three inserters rebuilt cKDTree per placement (O(k^2 log k)). FIXED with pre-allocate + batch + buffer.
  - Item 5: _VTK_AVAILABLE detection copy-pasted in 6 viewers. FIXED with shared is_vtk_available() helper.
fix:
  - Item 1: README.md — 6 rows underscore→hyphen. Committed 23c8e1e8.
  - Item 2: types.py:33 title + new regression test. Committed 07e240a0.
  - Item 3: types.py:38 DOI + updated existing test + new regression test. Committed 363bb2ef.
  - Item 4: PERF-01 ion_inserter batch rebuild. Committed 87b07779.
  - Item 4: PERF-02 solute_inserter pre-allocate + batch. Committed a438e1cb.
  - Item 4: PERF-03 custom_molecule_inserter pre-allocate + batch. Committed 03c515b2.
  - Item 5: vtk_utils.is_vtk_available() + 6 viewers updated + regression test. Committed a250d186.
verification:
  - Item 1: grep README.md shows 0 underscore, 6 hyphen. ✓
  - Item 2: test_tip4p_ice_paper_title_matches_readme PASS. ✓
  - Item 3: test_tip4p_2005_doi_resolves PASS, test_tip4p_ice_label_on_correct_doi PASS. ✓
  - Item 4: PERF-01/02/03 golden snapshot tests PASS (byte-equivalent SHA256). TREE-01/TREE-03 tests updated and PASS. 91 inserter tests PASS. ✓
  - Item 5: 44 VTK-DUP tests PASS (14 env-var combinations, caching, 6 viewer source checks, preservation). ✓
  - Full scancode suite: 306 passed. ✓
  - Inserter suite (-k inserter): 104 passed. ✓
  - VTK suite (QT_QPA_PLATFORM=offscreen -k vtk): 44 passed. ✓
  - Full non-GUI suite (excluding ~19 slow GUI/Qt/VTK files): 1633 passed, 3 failed, 2 skipped (185.62s).
    Pre-existing failures (NOT caused by my changes — my commits only touch README, types.py, 3 inserters, 6 viewers, vtk_utils.py, 5 test files):
    1. test_cli_integration.py::test_boundary_nmolecules_max — GenIce2 10s timeout on --nmolecules 1000 (environmental)
    2. test_cli_integration.py::test_version_shows_version — 4.5.0 vs 4.7.0 (version mismatch)
    3. test_entry_point.py::test_version_shows_version — 4.5.0 vs 4.7.0 (version mismatch)
    Zero new failures from my changes. ✓
  - gmx availability: AVAILABLE at /data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx
files_changed:
  - README.md (Item 1)
  - quickice/structure_generation/types.py (Items 2, 3)
  - tests/test_scancode_bugs_documentation.py (Items 2, 3)
  - quickice/structure_generation/ion_inserter.py (Item 4 PERF-01)
  - quickice/structure_generation/solute_inserter.py (Item 4 PERF-02)
  - quickice/structure_generation/custom_molecule_inserter.py (Item 4 PERF-03)
  - tests/test_scancode_bugs_ion.py (Item 4 PERF-01 — TREE-01 test updates)
  - tests/test_scancode_bugs_solute.py (Item 4 PERF-02 — TREE-03 test updates)
  - tests/test_scancode_bugs_inserter_perf_rebuild.py (Item 4 — new test file)
  - quickice/gui/vtk_utils.py (Item 5 — appended is_vtk_available)
  - quickice/gui/view.py (Item 5)
  - quickice/gui/solute_viewer.py (Item 5)
  - quickice/gui/custom_molecule_viewer.py (Item 5)
  - quickice/gui/interface_panel.py (Item 5)
  - quickice/gui/hydrate_viewer.py (Item 5)
  - quickice/gui/ion_viewer.py (Item 5)
  - tests/test_scancode_bugs_vtk_dup.py (Item 5 — new test file)

## Resolution

root_cause: 
  - Item 1: README.md:208-213 said tip4p_ice.itp (underscore) but code exports tip4p-ice.itp (hyphen). FIXED.
  - Item 2: types.py:33 had wrong title for DOI 10.1063/1.1931662. FIXED.
  - Item 3: types.py:38 had 404 DOI 10.1063/1.2121600. FIXED to 10.1063/1.2121687.
  - Item 4: Three inserters rebuilt cKDTree per placement (O(k^2 log k)). FIXED with pre-allocate + batch + buffer.
  - Item 5: (investigating)
fix:
  - Item 1: README.md — 6 rows underscore→hyphen. Committed 23c8e1e8.
  - Item 2: types.py:33 title + new regression test. Committed 07e240a0.
  - Item 3: types.py:38 DOI + updated existing test + new regression test. Committed 363bb2ef.
  - Item 4: PERF-01 ion_inserter batch rebuild. Committed 87b07779.
  - Item 4: PERF-02 solute_inserter pre-allocate + batch. Committed a438e1cb.
  - Item 4: PERF-03 custom_molecule_inserter pre-allocate + batch. Committed 03c515b2.
  - Item 5: (investigating)
verification:
  - Item 1: grep README.md shows 0 underscore, 6 hyphen. ✓
  - Item 2: test_tip4p_ice_paper_title_matches_readme PASS. ✓
  - Item 3: test_tip4p_2005_doi_resolves PASS, test_tip4p_ice_label_on_correct_doi PASS. ✓
  - Item 4: PERF-01/02/03 golden snapshot tests PASS (byte-equivalent SHA256). TREE-01/TREE-03 tests updated and PASS. 91 inserter tests PASS. ✓
  - Item 5: (pending)
files_changed:
  - README.md (Item 1)
  - quickice/structure_generation/types.py (Items 2, 3)
  - tests/test_scancode_bugs_documentation.py (Items 2, 3)
  - quickice/structure_generation/ion_inserter.py (Item 4 PERF-01)
  - quickice/structure_generation/solute_inserter.py (Item 4 PERF-02)
  - quickice/structure_generation/custom_molecule_inserter.py (Item 4 PERF-03)
  - tests/test_scancode_bugs_ion.py (Item 4 PERF-01 — TREE-01 test updates)
  - tests/test_scancode_bugs_solute.py (Item 4 PERF-02 — TREE-03 test updates)
  - tests/test_scancode_bugs_inserter_perf_rebuild.py (Item 4 — new test file)

## Resolution

root_cause: 
  - Item 1: README.md:208-213 said tip4p_ice.itp (underscore) but code exports tip4p-ice.itp (hyphen). FIXED.
  - Item 2: types.py:33 had wrong title for DOI 10.1063/1.1931662. FIXED to "A potential model for the study of ices and amorphous water: TIP4P/Ice".
  - Item 3: types.py:38 had 404 DOI 10.1063/1.2121600. FIXED to 10.1063/1.2121687.
  - Item 4: (investigating)
  - Item 5: (pending)
fix:
  - Item 1: README.md — 6 rows underscore→hyphen. Committed 23c8e1e8.
  - Item 2: types.py:33 title + new regression test. Committed 07e240a0.
  - Item 3: types.py:38 DOI + updated existing test + new regression test. Committed 363bb2ef.
  - Item 4: (investigating)
  - Item 5: (pending)
verification:
  - Item 1: grep README.md shows 0 underscore, 6 hyphen. ✓
  - Item 2: test_tip4p_ice_paper_title_matches_readme PASS. ✓
  - Item 3: test_tip4p_2005_doi_resolves PASS, test_tip4p_ice_label_on_correct_doi PASS (updated to new DOI). ✓
  - Item 4: (pending)
  - Item 5: (pending)
files_changed:
  - README.md (Item 1)
  - quickice/structure_generation/types.py (Items 2, 3)
  - tests/test_scancode_bugs_documentation.py (Items 2, 3)


## Symptoms

expected: 5 scancode follow-up issues fixed via 7 atomic commits (or fewer if combined), with regression tests for Items 4 and 5.
actual: (pending — will document each item's pre-fix state)
errors: (none — these are scancode findings, not runtime errors)
reproduction: Read source files at the cited lines.
started: Pre-existing tech debt; Items 1-3 are docs, Items 4-5 are previously-deferred M-complexity refactors now approved.

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-07-19T00:01:00Z
  checked: README.md:208-213
  found: All 6 rows say `tip4p_ice.itp` (underscore). Verified via grep.
  implication: Item 1 finding confirmed; fix to `tip4p-ice.itp` (hyphen).

- timestamp: 2026-07-19T00:01:00Z
  checked: quickice/structure_generation/types.py:25-49
  found: Line 33 says "A potential model for the phase diagram of TIP4P water" (WRONG title for DOI 10.1063/1.1931662). Line 38 says "DOI: 10.1063/1.2121600" (404 DOI for TIP4P/2005).
  implication: Items 2 and 3 findings confirmed.

- timestamp: 2026-07-19T00:02:00Z
  checked: quickice/main.py:143
  found: Already uses `itp_filename = "tip4p-ice.itp"` (hyphen) — CLI #3 was fixed in commit 9fc88ac3.
  implication: Item 1's underlying filename is `tip4p-ice.itp` (hyphen); README is the only outlier.

- timestamp: 2026-07-19T00:02:00Z
  checked: tests/test_scancode_bugs_documentation.py
  found: Existing `test_tip4p_ice_label_on_correct_doi` asserts DOI 10.1063/1.2121600 is in types.py (line 105). Will BREAK when Item 3 changes DOI to 10.1063/1.2121687.
  implication: Item 3 fix MUST also update this existing test to reference the new DOI 10.1063/1.2121687.

- timestamp: 2026-07-19T00:02:00Z
  checked: docs/cli-reference.md:119 (separate file, also says tip4p_ice.itp)
  found: docs/cli-reference.md:119 says `tip4p_ice.itp` (underscore), but user's task scope for Item 1 is ONLY README.md:208-213.
  implication: Do NOT touch docs/cli-reference.md in this task — out of scope per user's explicit Item 1 definition.

## Resolution

root_cause: (pending per item)
fix: (pending per item)
verification: (pending)
files_changed: []
