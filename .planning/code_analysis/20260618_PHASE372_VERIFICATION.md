# Phase 37.2 Verification Report

**Date:** 2026-06-18
**Scope:** Verify Phase 37.2 fixes against 30 CONFIRMED + 9 PARTIAL issues from the 2026-06-18 scancode scan
**Method:** Direct code and documentation file reads

---

## CRITICAL Issues (2)

### #1: DOI-D1 — Madrid2019 DOI wrong in README.md
- **Status:** RESOLVED
- **Evidence:** `README.md:371` now has `DOI: https://doi.org/10.1063/1.5121392`. `README.md:375` also has `DOI: 10.1063/1.5121392`. Both are the correct DOI.
- **Notes:** The old wrong DOI `10.1063/1.5121394` has been replaced with the correct `10.1063/1.5121392` at both locations.

### #2: C-CLI N-01 — Madrid2019 DOI 404 in cli-reference.md
- **Status:** RESOLVED
- **Evidence:** `docs/cli-reference.md:934` now has `[Madrid2019 reference](https://doi.org/10.1063/1.5121392)`. The old 404 DOI `10.1021/acs.jctc.9b00902` has been replaced.
- **Notes:** Correct DOI used throughout. The `[ion-concentration]` section (line 928) also now documents the 0.0–5.0 range and references the correct DOI.

---

## HIGH Issues (4)

### #3: B NEW-01/11 — write_solute_gro_file solute/custom positions NOT PBC-wrapped
- **Status:** PARTIALLY RESOLVED
- **Evidence:**
  - **write_ion_gro_file** (`gromacs_writer.py:1446-1455`): Both solute and custom positions ARE now PBC-wrapped with `% np.diag(cell)`. ✅
  - **write_interface_gro_file** (`gromacs_writer.py:689-695`): Both solute and custom positions ARE now PBC-wrapped with `% np.diag(cell)`. ✅
  - **write_solute_gro_file** (`gromacs_writer.py:2395-2399`): Custom molecule positions ARE PBC-wrapped. ✅ BUT solute positions at line 2572 still use raw `solute_structure.positions[start:start + count]` WITHOUT `% np.diag(cell)` wrapping. ❌
  - **write_custom_molecule_gro_file** (`gromacs_writer.py:1967-1971`): Main positions wrapped via `wrap_molecules_into_box`. Custom molecules are in molecule_index and covered by that function. ✅
- **Notes:** 3 of 4 GRO writers now wrap correctly. The write_solute_gro_file is missing solute position wrapping (line 2572). This is the same pattern as write_ion_gro_file line 1447 but was missed.

### #4: B PERF-01 — Triple-nested Python loop in wrap_molecules_into_box
- **Status:** STILL PRESENT
- **Evidence:** `gromacs_writer.py:67-140` — The `wrap_molecules_into_box` function still has `for mol in molecule_index:` (line 93), `for i in range(1, len(mol_positions)):` (line 105), and `for dim in range(3):` (line 109). Triple-nested Python loop is unchanged.
- **Notes:** No vectorization has been applied. The function works correctly but is O(N_molecules × N_atoms_per_molecule × 3) in pure Python.

### #5: C-CLI N-02 — Concentration range not documented
- **Status:** RESOLVED
- **Evidence:**
  - `docs/cli-reference.md:785`: `--custom-concentration` → `**Type:** Float (0.0–5.0 mol/L)` ✅
  - `docs/cli-reference.md:869`: `--solute-concentration` → `**Type:** Float (0.0–5.0 mol/L)` ✅
  - `docs/cli-reference.md:928`: `--ion-concentration` → `**Type:** Float (0.0–5.0 mol/L)` ✅
- **Notes:** All three concentration flags now document the 0.0–5.0 mol/L valid range.

### #6: C-CLI N-03 — Validation Rules section missing 5 of 8 constraints
- **Status:** RESOLVED
- **Evidence:** `docs/cli-reference.md:996-1007` — The Validation Rules section now lists 8 constraints:
  1. Temperature: 0–500 K ✅
  2. Pressure: 0–10000 MPa ✅
  3. Nmolecules: 4–100000 ✅
  4. Box dimension: ≥1.0 nm ✅
  5. Concentration: 0.0–5.0 mol/L ✅
  6. Cage occupancy: 0.0–100.0% ✅
  7. File extension: .gro/.itp ✅
  8. Positive float ✅
- **Notes:** All 8 constraints are now documented. Previously only 3 were listed.

---

## MEDIUM Issues (14)

### #7: B NEW-03/EH-07 — write_custom_molecule_gro_file error handling (PARTIAL)
- **Status:** PARTIALLY RESOLVED
- **Evidence:** `gromacs_writer.py:2128-2135` — The file write is now wrapped in `try/except (OSError, ValueError)` with cleanup. However, the line-building phase (lines 1975-2122) is NOT wrapped in try/except. If formatting fails (e.g., bad position data), the error would be unhandled. The `write_ion_gro_file` uses the same pattern (lines within `try/with` block at 1460-1695).
- **Notes:** The write_custom_molecule_gro_file now uses a build-then-write pattern (build `lines` list, then `writelines()` in try/except), which is more consistent with other writers. But line-building is still unprotected. The original complaint about the line-building phase not being in try/except is partially addressed — the pattern is now consistent across writers, but none of them wrap line-building in try/except.

### #8: B NEW-06/PERF-03 — O(N) Python loop in _build_existing_atoms_tree
- **Status:** STILL PRESENT
- **Evidence:**
  - `solute_inserter.py:318-360`: Still uses per-atom Python `for` loop to filter MW atoms and build `existing_positions` list. No vectorization.
  - `custom_molecule_inserter.py:296-335`: Same pattern — per-atom Python loop.
  - `ion_inserter.py:341-358`: Same pattern — per-atom Python loop.
- **Notes:** All three inserters still use O(N) Python loops to build the existing atoms tree. No NumPy vectorization has been applied.

### #9: B NEW-07/PERF-04 — Per-molecule cKDTree query in _remove_overlapping_water
- **Status:** STILL PRESENT
- **Evidence:**
  - `solute_inserter.py:447-466`: Still iterates `for mol_idx in range(n_water_molecules)` with per-atom `for atom_pos in water_mol_positions:` loop calling `solute_tree.query(atom_pos, k=1)`.
  - `custom_molecule_inserter.py:412-431`: Same per-molecule, per-atom query pattern.
- **Notes:** No batching has been applied. Could be replaced with `cKDTree.query_ball_point()` or bulk query.

### #10: B NEW-16 — Custom molecule atoms excluded from overlap tree
- **Status:** RESOLVED
- **Evidence:**
  - `solute_inserter.py:350-360`: Now includes `custom_molecule_positions` in the overlap tree with MW filtering. ✅
  - `custom_molecule_inserter.py:322-331`: Now includes `custom_molecule_positions` in the overlap tree with MW filtering. ✅
- **Notes:** Both inserters now check for `custom_molecule_positions` attribute and include those atoms in the overlap detection tree.

### #11: B PERF-02 — Hydrate generator double-nested wrapping loop
- **Status:** PARTIALLY RESOLVED
- **Evidence:** `hydrate_generator.py:361-454` — The orthorhombic path (lines 369-405) now uses `np.floor(mol_positions / L).astype(int)` (vectorized cell index computation) instead of per-atom loops. The `for mol in molecule_index` loop remains, but the inner atom-level computation is vectorized for the single-cell case. Multi-cell case (lines 403-405) still has per-atom loop for shift calculation. Triclinic path (lines 407-452) uses fractional coordinates with `mol_positions @ cell_inv` (vectorized) but still has per-atom loops in multi-cell case (lines 428-432, 447-452).
- **Notes:** The common case (all atoms in same cell) is now vectorized. The multi-cell case (rare) still has per-atom Python loops. Substantial improvement over the original pure-Python double-nested loop.

### #12: B PERF-05 — O(N²) memory from vstack-and-rebuild
- **Status:** STILL PRESENT
- **Evidence:** `custom_molecule_inserter.py:653-654`: Still does `all_data = np.vstack([base_existing_data, np.vstack(placed_positions)])` on every successful placement — full rebuild of ALL placed positions.
- **Notes:** The solute_inserter has been improved with incremental `combined_tree_data` pattern (line 830-885), but the custom_molecule_inserter was NOT updated to match. This is an O(N²) memory pattern for N placed molecules.

### #13: C-CLI N-04 — Extension validation not documented
- **Status:** RESOLVED
- **Evidence:** `docs/cli-reference.md:1006`: Now includes `**File extension:** --custom-gro must end in .gro, --custom-itp must end in .itp` in the Validation Rules section.
- **Notes:** Extension validation is documented in both the Validation Rules section and is consistent with code enforcement.

### #14: C-CLI N-05 — OPLS-AA incompatibility not warned (PARTIAL)
- **Status:** RESOLVED
- **Evidence:**
  - `docs/gro-itp-guide.md:481`: Warning box added: "⚠️ Combining Rule Incompatibility: OPLS-AA uses geometric combining rules (comb-rule 3 in GROMACS), while TIP4P-ICE water uses Lorentz-Berthelot combining rules (comb-rule 2)..."
  - `docs/gro-itp-guide.md:769`: Troubleshooting section now states: "**OPLS-AA** uses geometric combining rules and is NOT compatible with QuickIce's default `comb-rule 2`..."
- **Notes:** Two locations now warn about OPLS-AA incompatibility with comb-rule=2. Previously no warning existed.

### #15: C-CLI N-06 — No pipeline vs ice-only output section
- **Status:** RESOLVED
- **Evidence:** `docs/cli-reference.md:1013-1045` — New section "## Pipeline Mode vs Ice-Only Output" with subsections for File Naming, Topology Structure, GROMACS Export, and Phase Diagrams, each with comparison tables.
- **Notes:** Comprehensive section now clearly documents the differences between pipeline and ice-only output behavior.

### #16: C-CLI R-01 — Box dimension range wrong
- **Status:** RESOLVED
- **Evidence:** `docs/cli-reference.md:351`: Now says `**Type:** Float (≥1.0 nm)` instead of the old "1.0–100 nm". The Validation Rules section (line 1003) also says `**Box dimension:** Must be ≥1.0 nm (no upper bound enforced)`.
- **Notes:** The documented range now matches the code enforcement (only lower bound, no upper bound).

### #17: C-CLI R-06 — "User dialog" GUI-only
- **Status:** STILL PRESENT
- **Evidence:** `docs/gro-itp-guide.md:629`: Still says "QuickIce allows mismatch with user dialog" — no CLI caveat added.
- **Notes:** The CLI has no dialog for this. The text should note that CLI mode silently accepts the mismatch or validates differently.

### #18: C-GUI NEW-1 — Button label mismatch
- **Status:** RESOLVED
- **Evidence:**
  - `help_dialog.py:115`: Now says "Click Generate Custom Molecules to insert custom molecules" ✅
  - `docs/gui-guide.md:577`: Now says 'Click "Generate Custom Molecules"' ✅
- **Notes:** Both the help dialog and the guide now match the actual button label "Generate Custom Molecules".

### #19: C-GUI DOC-G5 — Screenshot paths wrong
- **Status:** PARTIALLY RESOLVED
- **Evidence:**
  - Existing valid images in `docs/images/`: `3d-viewer.png`, `dual-viewport.png`, `export-menu.png`, `phase-diagram.png`, `quickice-v3-gui.png`, `quickice-v4-gui.png`, `tab2-hydrate-panel.png`, `tab2-piece-interface.png`, `tab2-pocket-interface.png`, `tab2-slab-interface.png`, `tab4-ion-panel.png`
  - **Missing images:** `custom-molecule-panel.png` (referenced at line 427) and `solute-panel.png` (referenced at line 623) still do NOT exist.
  - Lines 426 and 622 have `<!-- TODO: Capture ... screenshot -->` comments acknowledging the missing images.
- **Notes:** 2 of 7 originally-problematic screenshots are still missing (with TODO comments). The 5 previously wrong paths appear to be fixed (existing images match references).

### #20: D — Test data leaking into bundle (PARTIAL)
- **Status:** PARTIALLY RESOLVED
- **Evidence:** `quickice-gui.spec:2,9-16`: Still uses `collect_all(pkg)` for iapws, genice2, genice_core, matplotlib, scipy, numpy, shapely, networkx, spglib. Line 27 does have `excludes=['*/tests/*', '*/test/*', ...]` to filter test dirs, but `collect_all` still pulls in all data files from those packages, including any test data not under `*/tests/*` paths.
- **Notes:** The excludes list helps with `*/tests/*` paths but `collect_all` remains — it still pulls all data/binaries/hidden imports from each package, which is the original concern. Targeted imports would be more precise.

---

## LOW Issues (16) — spot-check

### #21: B NEW-08 — Simple modulo wrapping may split multi-atom solutes (PARTIAL)
- **Status:** PARTIALLY RESOLVED
- **Evidence:** `gromacs_writer.py:1443-1447`: Comment acknowledges "Solute molecules are single molecules that don't span PBC boundaries, so simple modulo wrapping is sufficient." The modulo wrapping IS now present (was the original fix for #3), but it's still simple `% np.diag(cell)` rather than molecule-aware wrapping.
- **Notes:** For CH4 (5 atoms, ~0.38 nm diameter) and THF (13 atoms, ~0.55 nm diameter) in typical boxes (≥5 nm), simple modulo is unlikely to split molecules. But the general pattern is not robust for arbitrary multi-atom solutes.

### #22: B NEW-09/EH-08 — Broad except Exception
- **Status:** STILL PRESENT
- **Evidence:** 48 occurrences of `except Exception as e:` or `except Exception:` found across the codebase, including:
  - `gromacs_writer.py:390,423`: `except Exception as e:`
  - `gui/export.py`: 9 occurrences
  - `gui/main_window.py`: 5 occurrences
  - `cli/itp_helpers.py`: 4 occurrences
- **Notes:** No narrowing of exception types has been applied. Most are in GUI/export code where broad catching may be acceptable for UX, but the gromacs_writer.py uses should be narrowed to specific exceptions.

### #23: B NEW-15 — 7 test files hardcode 0.0299
- **Status:** STILL PRESENT
- **Evidence:** 14 occurrences of `0.0299` in test files, across 7 test modules:
  - `test_custom_molecule_concentration.py:117`
  - `e2e_export_helpers.py:239,244`
  - `test_e2e_solute_insertion.py:357,374`
  - `test_e2e_custom_molecule.py:382,385,398`
  - `test_e2e_ion_insertion.py:44,49`
  - `test_e2e_workflow_chains.py:47,52`
  - `test_scancode_bugs_ion.py:20,25`
- **Notes:** The constant `WATER_VOLUME_NM3 = 0.0299` exists in `types.py:25` but test files still hardcode the value instead of importing the constant. Source code (`pipeline.py`, `ion_inserter.py`, etc.) does import and use the constant.

### #25: B SEC-04 — No path traversal check (PARTIAL)
- **Status:** STILL PRESENT
- **Evidence:** No path traversal validation (e.g., checking for `..` in paths, `os.path.normpath` comparison) found anywhere in the codebase.
- **Notes:** The GUI uses Qt file dialogs which limit user selection, but CLI paths are not validated against traversal.

### #26: B SEC-05 — CSV no size limit
- **Status:** STILL PRESENT
- **Evidence:** No CSV file size limits or row count limits found. `custom_molecule_panel.py` reads CSV without size checks.
- **Notes:** A maliciously large CSV could exhaust memory.

### #27: B PERF-06 — GRO per-atom string formatting
- **Status:** STILL PRESENT
- **Evidence:** `gromacs_writer.py` still uses per-atom Python `lines.append(f"...")` pattern throughout all GRO writer functions. 54+ `lines.append()` calls building strings atom by atom in Python loops. No NumPy vectorization.
- **Notes:** The build-then-write pattern (collect lines in list, then `writelines()`) is reasonable for I/O, but the per-atom string formatting loop is still pure Python.

### #28: C-CLI R-02 — --cli + --gui conflict not documented
- **Status:** STILL PRESENT
- **Evidence:** `docs/cli-reference.md:1119-1123` shows the routing table and priority `--gui > computation flags > no arguments`, but does NOT explicitly state what happens when `--cli --gui` are both provided. The code (`entry.py:168-178`) checks `--gui` first, so `--cli --gui` results in GUI mode.
- **Notes:** The priority chain implies the behavior but is not explicit about the conflict case.

### #29: C-CLI R-03 — --no-diagram in pipeline commands
- **Status:** RESOLVED
- **Evidence:** `docs/cli-reference.md:99`: "In pipeline mode (when any pipeline flags like `--hydrate`, `--interface`, `--custom-gro`, `--solute-type`, or `--ion-concentration` are present), the `--no-diagram` flag has no effect". Also documented in the Pipeline vs Ice-Only section (line 1044).
- **Notes:** Clear documentation that --no-diagram is a no-op in pipeline mode.

### #30: C-CLI R-04 — --seed 42 redundant
- **Status:** STILL PRESENT
- **Evidence:** `docs/cli-reference.md:467`: Default is still documented as `42`. This means `--seed 42` is always redundant.
- **Notes:** Not necessarily a bug, but the documentation could note that the default seed is 42 for reproducibility, and specifying `--seed 42` is redundant.

### #31: C-CLI R-05 — --no-diagram in hydrate script
- **Status:** RESOLVED
- **Evidence:** Same as #29 — the pipeline mode note at line 99 covers this. `--hydrate` is a pipeline flag, so `--no-diagram` is correctly documented as having no effect.
- **Notes:** Covered by the general pipeline mode note.

### #32: C-CLI R-07 — No citation for WATER_VOLUME_NM3
- **Status:** STILL PRESENT
- **Evidence:** `quickice/structure_generation/types.py:24-25`: Still just says `# Volume per TIP4P-ICE water molecule in nm³ (at ~1 bar, 300K)` followed by `WATER_VOLUME_NM3: float = 0.0299`. No literature citation, DOI, or derivation.
- **Notes:** The value 0.0299 nm³ comes from TIP4P-ICE water density but has no traceable citation.

### #33: C-CLI N-08 — TIP4P-ICE bare DOI (PARTIAL)
- **Status:** STILL PRESENT
- **Evidence:** `docs/gui-guide.md:866`: Still a bare link `[TIP4P-ice Reference](https://doi.org/10.1063/1.1931662)` without author, title, or year.
- **Notes:** A proper citation would be: Abascal, J. L. F., Sanz, E., García Fernández, R., & Vega, C. (2005). A potential model for the phase diagram of TIP4P water. J. Chem. Phys. 122, 234511. DOI: 10.1063/1.1931662.

### #34: C-GUI DOC-G8 — Ice V/VII citation
- **Status:** STILL PRESENT
- **Evidence:** `docs/gui-guide.md` — No citations for Ice V or Ice VII crystal structures. The "Further Reading" section (line 860) only links to GenIce2, IAPWS, and TIP4P-ice.
- **Notes:** Should include Lobban et al. (1998) for Ice V and Hemley et al. (1987) for Ice VII.

### #35: C-GUI DOC-G14 — Ion tooltip missing Madrid2019
- **Status:** STILL PRESENT
- **Evidence:** `quickice/gui/ion_panel.py:180-184`: The concentration HelpIcon tooltip says "Target NaCl concentration in mol/L (M). Typical seawater: ~0.6 M. For drinking water: <0.05 M." — no mention of Madrid2019 ion model or ±0.85e charges.
- **Notes:** The Madrid2019 reference is mentioned in the charge calculation (line 446-468) but NOT in the user-facing tooltip.

### #36: C-GUI DOC-G14 — Ctrl+S vs Ctrl+M (PARTIAL)
- **Status:** PARTIALLY RESOLVED
- **Evidence:** `docs/gui-guide.md:590`: Says "File → Export Custom Molecules for GROMACS (Ctrl+S)". But the keyboard shortcuts table at line 214 says "Ctrl+M | Export custom molecules for GROMACS (Tab 3)". Line 218 explains "Ctrl+S provides unified export from the currently active tab."
- **Notes:** The docs now explain that Ctrl+S is a unified shortcut that works across all tabs (including Tab 3), while Ctrl+M is the Tab-3-specific shortcut. This is less ambiguous than before but still potentially confusing — a reader on line 590 may not realize Ctrl+M also works.

### #37: C-GUI NEW-3 — README "12 polymorphs" lists 11
- **Status:** STILL PRESENT
- **Evidence:** `README.md:116`: "**12 ice polymorphs** — Ih, Ic, II, III, V, VI, VII, VIII, IX, XV, X". Counting: Ih(1), Ic(2), II(3), III(4), V(5), VI(6), VII(7), VIII(8), IX(9), XV(10), X(11) = 11 polymorphs, not 12.
- **Notes:** Either the count "12" should be changed to 11, or a 12th polymorph (likely Ice III→Ice II family or Ice XI) should be added to the list.

### #38: C-GUI NEW-4 — "Rewards" for diversity ambiguous
- **Status:** STILL PRESENT
- **Evidence:** `docs/ranking.md:11`: Still says "**Diversity Score** - Rewards structural uniqueness via O-O distance fingerprint". However, lines 183-188 now clearly explain the inversion: `1 - norm_diversity` means higher diversity → lower combined score.
- **Notes:** The word "Rewards" is still ambiguous/misleading in the overview. The detailed explanation (lines 183-188) is now correct. "Penalizes structural similarity" would be more accurate.

---

## Summary Table

| # | ID | Status | Evidence Summary |
|---|-----|--------|------------------|
| 1 | DOI-D1 | RESOLVED | README.md:371,375 now have correct DOI 10.1063/1.5121392 |
| 2 | C-CLI N-01 | RESOLVED | cli-reference.md:934 now has correct DOI 10.1063/1.5121392 |
| 3 | B NEW-01/11 | PARTIALLY RESOLVED | Ion/interface/custom writers wrap; solute writer still missing at line 2572 |
| 4 | B PERF-01 | STILL PRESENT | Triple-nested loop in gromacs_writer.py:67-140 unchanged |
| 5 | C-CLI N-02 | RESOLVED | All 3 concentration flags now document 0.0–5.0 range |
| 6 | C-CLI N-03 | RESOLVED | Validation Rules now lists all 8 constraints (was 3) |
| 7 | B NEW-03/EH-07 | PARTIALLY RESOLVED | Write phase now in try/except; line-building still unprotected (consistent with other writers) |
| 8 | B NEW-06/PERF-03 | STILL PRESENT | Per-atom Python loops in _build_existing_atoms_tree in all 3 inserters |
| 9 | B NEW-07/PERF-04 | STILL PRESENT | Per-molecule, per-atom cKDTree query in _remove_overlapping_water |
| 10 | B NEW-16 | RESOLVED | custom_molecule_positions now included in overlap tree in both solute and custom inserters |
| 11 | B PERF-02 | PARTIALLY RESOLVED | Common case vectorized; multi-cell case still has per-atom loop |
| 12 | B PERF-05 | STILL PRESENT | custom_molecule_inserter still uses full vstack-and-rebuild on each placement |
| 13 | C-CLI N-04 | RESOLVED | Extension validation (.gro/.itp) now documented in Validation Rules |
| 14 | C-CLI N-05 | RESOLVED | OPLS-AA incompatibility warning added at gro-itp-guide.md:481 and :769 |
| 15 | C-CLI N-06 | RESOLVED | Pipeline vs ice-only output section added at cli-reference.md:1013-1045 |
| 16 | C-CLI R-01 | RESOLVED | Box dimension now documented as "≥1.0 nm" (no upper bound) |
| 17 | C-CLI R-06 | STILL PRESENT | gro-itp-guide.md:629 still says "user dialog" without CLI caveat |
| 18 | C-GUI NEW-1 | RESOLVED | help_dialog.py:115 and gui-guide.md:577 now say "Generate Custom Molecules" |
| 19 | C-GUI DOC-G5 | PARTIALLY RESOLVED | 5 wrong paths fixed; 2 screenshots still missing (custom-molecule-panel.png, solute-panel.png) |
| 20 | D (PARTIAL) | PARTIALLY RESOLVED | spec has excludes list but still uses collect_all for all packages |
| 21 | B NEW-08 | PARTIALLY RESOLVED | Modulo wrapping present (was #3 fix); still simple modulo, not molecule-aware |
| 22 | B NEW-09/EH-08 | STILL PRESENT | 48 broad `except Exception` occurrences remain |
| 23 | B NEW-15 | STILL PRESENT | 7 test files still hardcode 0.0299 instead of importing WATER_VOLUME_NM3 |
| 25 | B SEC-04 | STILL PRESENT | No path traversal checks added |
| 26 | B SEC-05 | STILL PRESENT | No CSV size limits added |
| 27 | B PERF-06 | STILL PRESENT | Per-atom Python string formatting in GRO writers unchanged |
| 28 | C-CLI R-02 | STILL PRESENT | --cli + --gui conflict behavior not explicitly documented |
| 29 | C-CLI R-03 | RESOLVED | --no-diagram no-op in pipeline mode documented at line 99 and 1044 |
| 30 | C-CLI R-04 | STILL PRESENT | --seed default=42 still documented; redundancy not noted |
| 31 | C-CLI R-05 | RESOLVED | Covered by pipeline mode note (same as #29) |
| 32 | C-CLI R-07 | STILL PRESENT | WATER_VOLUME_NM3 still has no literature citation |
| 33 | C-CLI N-08 | STILL PRESENT | TIP4P-ICE bare DOI at gui-guide.md:866 without author/title/year |
| 34 | C-GUI DOC-G8 | STILL PRESENT | No Ice V/VII citations in gui-guide.md |
| 35 | C-GUI DOC-G14 | STILL PRESENT | Ion tooltip at ion_panel.py:180-184 missing Madrid2019 reference |
| 36 | C-GUI DOC-G14 | PARTIALLY RESOLVED | Unified Ctrl+S explained but line 590 and line 214 still show different shortcuts |
| 37 | C-GUI NEW-3 | STILL PRESENT | README.md:116 says "12 polymorphs" but lists only 11 |
| 38 | C-GUI NEW-4 | STILL PRESENT | ranking.md:11 still says "Rewards"; detailed explanation correct |

---

## Final Counts

| Status | Count | Percentage |
|--------|-------|------------|
| RESOLVED | 12 | 33% |
| PARTIALLY RESOLVED | 8 | 22% |
| STILL PRESENT | 16 | 44% |
| DEFERRED | 0 | 0% |
| **Total** | **36** | **100%** |

### By Priority

| Priority | Total | RESOLVED | PARTIAL | STILL PRESENT |
|----------|-------|----------|---------|---------------|
| CRITICAL | 2 | 2 | 0 | 0 |
| HIGH | 4 | 2 | 1 | 1 |
| MEDIUM | 14 | 6 | 3 | 5 |
| LOW | 16 | 2 | 4 | 10 |

---

## Phase 37.2 Completion Assessment

**In-scope issues:** 36 (excluding #39-42 which were deferred to Phase 38)

**Fully resolved:** 12 of 36 = **33%**

**At least partially addressed:** 20 of 36 = **56%**

**Assessment:** Phase 37.2 made good progress on CRITICAL and documentation issues:
- Both CRITICAL DOI bugs are fixed ✅
- 6 of 8 documentation gaps are resolved ✅
- Custom molecule overlap tree now includes custom_molecule_positions ✅
- Concentration ranges, validation rules, pipeline output section all documented ✅
- OPLS-AA warning, box dimension range, extension validation all documented ✅

However, several in-scope items remain:
- **#3 (HIGH):** `write_solute_gro_file` solute positions still not PBC-wrapped (line 2572)
- **#4 (HIGH):** `wrap_molecules_into_box` triple-nested Python loop not vectorized
- **#8, #9 (MEDIUM):** Inserter performance loops not vectorized
- **#12 (MEDIUM):** `custom_molecule_inserter` vstack-and-rebuild not fixed (solute_inserter was)
- **#17 (MEDIUM):** "user dialog" without CLI caveat
- **LOW items:** 10 of 16 still present (mostly documentation and code quality)

**Recommendation:** A Phase 37.3 may be warranted to address the remaining HIGH item (#3 solute wrapping) and the performance issues (#4, #8, #9, #12), plus the outstanding documentation gaps.
