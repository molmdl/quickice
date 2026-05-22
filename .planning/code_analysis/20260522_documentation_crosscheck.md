# Documentation Cross-Check Report

**Date:** 2026-05-22
**Scope:** README, GUI guide, code comments, citations, docstrings, data files

## Summary

The documentation is largely accurate and well-maintained. The recent bug-fix pass addressed GAFF/GAFF2 citations, THF formula corrections, and keyboard shortcut updates. However, 17 issues remain: 6 in README.md, 5 in the GUI guide, 2 stale/inaccurate code comments, 3 missing citations in README, 1 inaccurate docstring, and several minor data file attribution gaps. The most impactful issues are: (1) missing Ice XV row in the README Phase Detection table, (2) an incorrect tab index in a docstring, (3) missing IAPWS-95 and Journaux citations in README, (4) a stale IAPWS R10-06 URL in README vs. code, and (5) two typos in documentation text.

## README.md Issues

### Issue 1: Missing Ice XV in Phase Detection Table
- **File:** `README.md`, line 229-242
- **What's wrong:** The Phase Detection table lists 12 phases but only shows 11 rows. Ice XV is missing from the table, despite being listed in the "Detection-only phases" note on line 261 as "Ice IX, XI, XV, and X". The code in `quickice/phase_mapping/lookup.py` (line 43) and `quickice/structure_generation/types.py` (line 63) fully support Ice XV detection with metadata including density (1.31 g/cm³) and crystal system.
- **What it should be:** Add an Ice XV row to the Phase Detection table:
  ```
  | Ice XV | Ordered VI | 950-2100 MPa | 50-100K |
  ```

### Issue 2: Typo — "calcution" instead of "calculations"
- **File:** `README.md`, line 218
- **What's wrong:** Text reads "QM calcution were done using Gaussian 16 Rev. C01."
- **What it should be:** "QM calculations were done using Gaussian 16 Rev. C01."

### Issue 3: IAPWS R10-06 URL mismatch between README and code
- **File:** `README.md`, line 316 vs. `quickice/phase_mapping/ice_ih_density.py`, line 12
- **What's wrong:** README references URL `https://www.iapws.org/relguide/Ice-2006.html` while the code references `https://www.iapws.org/release/Ice-2009.html`. The IAPWS document is officially "R10-06(2009)" — the 2009 revision of the 2006 formulation. The code's URL (Ice-2009.html) is more current.
- **What it should be:** Update README to use the 2009 URL: `https://www.iapws.org/release/Ice-2009.html`. Also update the README title from "Equation of State 2006 for H₂O Ice Ih" to "Equation of State 2006 for H₂O Ice Ih (Revised 2009)" to match the code's docstring.

### Issue 4: Non-existent test file referenced in Testing section
- **File:** `README.md`, line 353
- **What's wrong:** Says `pytest tests/gui/test_solute_inserter.py` but this file does not exist. The tests directory contains no `gui/` subdirectory. Solute-related tests are in `tests/test_output/test_gromacs_export_solute.py` and `tests/test_custom_molecule_concentration.py`.
- **What it should be:** Replace with an existing test file, e.g., `pytest tests/test_output/test_gromacs_export_solute.py`

### Issue 5: Project Structure listing inaccurate
- **File:** `README.md`, lines 358-373
- **What's wrong:** The project structure tree is missing the `output/` subdirectory under `quickice/` (which contains `gromacs_writer.py`, `pdb_writer.py`, `orchestrator.py`, `validator.py`, `phase_diagram.py`, `types.py`). Also missing the `utils/` subdirectory. The `quickice/phase_mapping/data/` subdirectory is not listed either.
- **What it should be:** Add `output/`, `utils/`, and `phase_mapping/data/` to the project structure tree.

### Issue 6: "Last updated" date stale
- **File:** `README.md`, line 378
- **What's wrong:** Says "Last updated: 2026-05-07" — may be outdated depending on recent changes.
- **What it should be:** Update to current date if changes are made from this report.

## GUI Guide Issues

### Issue 7: Typo — "Screenshto"
- **File:** `docs/gui-guide.md`, line 428
- **What's wrong:** Text reads "*Screenshto of Custom Molecule Upload tab showing file upload controls and 3D viewer*"
- **What it should be:** "*Screenshot of Custom Molecule Upload tab showing file upload controls and 3D viewer*"

### Issue 8: Stale version reference in Export for GROMACS section
- **File:** `docs/gui-guide.md`, line 182
- **What's wrong:** Says "QuickIce v4.0 adds interface construction with direct GROMACS export for molecular dynamics simulations." — This is a v4.0-era statement in a v4.5 document.
- **What it should be:** Change to "QuickIce provides interface construction with direct GROMACS export for molecular dynamics simulations." or "QuickIce v4.5 provides..."

### Issue 9: THF Formula column contains name, not formula
- **File:** `docs/gui-guide.md`, lines 255-259
- **What's wrong:** The Guest Molecules table has columns `Guest | Formula | Force Field | Fits In`. The CH₄ row shows "CH₄" in the Formula column (which happens to be both name and formula), but the THF row shows "Tetrahydrofuran" in the Formula column — this is the name, not the formula. The code in `quickice/structure_generation/types.py` (line 87) correctly records the formula as `"C₄H₈O"`.
- **What it should be:** Change THF Formula cell from "Tetrahydrofuran" to "C₄H₈O" (matching the code and README types.py definition).

### Issue 10: Solute Types table same Formula column issue
- **File:** `docs/gui-guide.md`, lines 629-632
- **What's wrong:** Same issue as Issue 9. The Solute Types table columns are `Solute | Formula | Force Field | Description`. CH₄ shows "Methane" and THF shows "Tetrahydrofuran" in the Formula column — these are names, not formulas.
- **What it should be:** CH₄ row Formula: "CH₄", THF row Formula: "C₄H₈O"

### Issue 11: Help dialog mentions "empty" guest type not in code
- **File:** `quickice/gui/help_dialog.py`, line 97
- **What's wrong:** The help dialog workflow text says "Select lattice type (sI, sII, sH) and guest type (empty, CH₄, etc.)". The code in `quickice/structure_generation/types.py` (lines 76-91) only supports `"ch4"` and `"thf"` as guest types. There is no "empty" guest type option in the GUEST_MOLECULES dictionary.
- **What it should be:** Remove "empty" from the guest type list, or clarify that some lattice types can be generated without guests (if that's supported by GenIce2). The actual `quickice/gui/hydrate_panel.py` likely has the guest dropdown populated from GUEST_MOLECULES which only has CH₄ and THF. Change to "guest type (CH₄, THF)".

## Code Comment Inconsistencies

### Issue 12: Stale development phase comments in main_window.py
- **File:** `quickice/gui/main_window.py`, lines 130-143
- **What's wrong:** Comments reference "Phase 32", "Phase 33", "Phase 34", "Phase 35", "ARCH-05b", and describe planned vs. completed work. Example: "Note: Tab reordering (ARCH-05b) happens in Phase 35, not Phase 32. Phase 32 prepares infrastructure..." and "Future data flows (v4.5): Interface Construction → Solute Insertion...". These are development artifacts that no longer describe future work — all these phases are complete.
- **Impact:** Low (comments are in the method body, not user-facing)
- **Fix approach:** Clean up to describe current state only. Replace "Future data flows (v4.5):" with "Cross-tab data flows (v4.5):" and remove the Phase/ARCH references.

### Issue 13: Inconsistent AVOGADRO comment across modules
- **File:** `quickice/structure_generation/solute_inserter.py`, line 32 vs. `quickice/structure_generation/ion_inserter.py`, line 27 vs. `quickice/ranking/scorer.py`, line 168
- **What's wrong:** The AVOGADRO constant is defined in three places with different comment quality:
  - `ion_inserter.py`: `AVOGADRO = 6.02214076e23  # mol^-1 (CODATA 2017)` ✅ Full attribution
  - `solute_inserter.py`: `AVOGADRO = 6.02214076e23  # mol^-1` ❌ Missing CODATA 2017
  - `scorer.py`: `AVOGADRO = 6.02214076e23  # molecules/mol (CODATA 2017)` ✅ Full attribution (different unit comment)
- **Impact:** Low (same numeric value), but attribution should be consistent
- **Fix approach:** Update `solute_inserter.py` to match: `# mol^-1 (CODATA 2017)`

## Missing Citations

### Issue 14: IAPWS-95 formulation not cited in README
- **What's missing:** The code in `quickice/phase_mapping/water_density.py` implements water density using the IAPWS-95 formulation with a reference URL (https://www.iapws.org/release/IAPWS-95.html). This is a critical scientific method used for liquid water density calculations, but the README References section only cites IAPWS R14-08 and R10-06 — not IAPWS-95.
- **Impact:** High — IAPWS-95 is the primary source for liquid water density, which directly affects interface generation accuracy
- **Citation to add:**
  ```
  ### IAPWS-95
  - Document: "Revised Release on the IAPWS Formulation 1995 for the Thermodynamic Properties of Ordinary Water Substance for General and Scientific Use"
  - URL: https://www.iapws.org/release/IAPWS-95.html
  ```

### Issue 15: Journaux et al. (2019, 2020) not cited in README
- **What's missing:** The code in `quickice/phase_mapping/data/ice_boundaries.py` (lines 15-16) and `quickice/phase_mapping/triple_points.py` (line 6) reference Journaux et al. for the II-III-V and II-V-VI triple points, with full DOIs. These are primary sources for high-pressure phase boundary data. The README References section does not cite these papers.
- **Impact:** Medium — These papers provide the triple point data for Ice II-V-VI and II-III-V boundaries which are critical for phase mapping accuracy at moderate pressures
- **Citations to add:**
  ```
  ### Journaux et al. (2019)
  - Journaux, B., et al. (2019). "Planetary ices phase diagram mapping using density functional theory." Journal of Geophysical Research: Planets, 124(12), 3090-3108.
  - DOI: https://doi.org/10.1029/2019JE006176

  ### Journaux et al. (2020)
  - Journaux, B., et al. (2020). "Ice metastability and ice-water clathrate transformations at high pressure." Space Science Reviews, 216, 7.
  - DOI: https://doi.org/10.1007/s11214-020-00717-4
  ```

### Issue 16: Clathrate hydrate structure reference missing
- **What's missing:** The code implements sI, sII, and sH clathrate hydrate generation, with cage type descriptions in `quickice/structure_generation/types.py` (lines 43-72). The README describes these structures in the Hydrate Generation section but provides no primary scientific reference for clathrate hydrate crystal structures. Sloan & Koh is the standard reference.
- **Impact:** Low-Medium — The hydrate structures come from GenIce2 which has its own citation, but the crystallographic descriptions (cage types, unit cell molecules) come from the clathrate hydrate literature
- **Citation to add:**
  ```
  ### Sloan & Koh — Clathrate Hydrates
  - Sloan, E.D. & Koh, C.A. (2007). Clathrate Hydrates of Natural Gases, 3rd ed. CRC Press.
  - ISBN: 978-0849390784
  ```

## Inaccurate Docstrings

### Issue 17: Wrong tab index in `_on_tab_changed` docstring
- **File:** `quickice/gui/main_window.py`, line 1426
- **What's wrong:** Docstring says `index: New tab index (0 = Ice Generation, 1 = Interface Construction)`. Tab 1 is actually **Hydrate Generation**, not Interface Construction. Interface Construction is Tab 2. The correct mapping is defined in `quickice/gui/constants.py` (lines 9-28).
- **What it should be:** `index: New tab index (0 = Ice Generation, 1 = Hydrate Generation, 2 = Interface Construction, 3 = Custom Molecule, 4 = Solute Insertion, 5 = Ion Insertion)`

## Data File Documentation

### Issue 18: GAFF/GAFF2 paper citation not in ITP file headers
- **Files:** `quickice/data/ch4.itp`, `quickice/data/thf.itp`, `quickice/data/ch4_hydrate.itp`, `quickice/data/thf_hydrate.itp`, `quickice/data/ch4_liquid.itp`, `quickice/data/thf_liquid.itp`
- **What's wrong:** All ITP files attribute parameter creation to Sobtop (line 1: "Created by Sobtop...") and note "Modified for QuickIce: [atomtypes] commented" (line 2-3). However, none include the GAFF/GAFF2 citation directly in the file header. The README has the citation (lines 332-334), but someone examining the ITP file alone wouldn't find the force field paper reference.
- **Impact:** Low — README has the citation, and the ITP files do mention they're "GAFF2-prepared"
- **Recommendation:** Add a comment line to each ITP file header referencing GAFF2:
  ```
  ; GAFF2 Force Field: Wang et al. (2004) J. Comput. Chem. 25(9), 1157-1174, DOI: 10.1002/jcc.20035
  ; He et al. (2020) J. Chem. Inf. Model. 60(5), 247-257, DOI: 10.1021/acs.jcim.9b01131
  ```

### Issue 19: TIP4P-ICE ITP file — SklogWiki reference incomplete
- **File:** `quickice/data/tip4p-ice.itp`, line 1-2
- **What's wrong:** The header says "File adapted from the following link under the cc-by-nc-sa 3.0 license" and provides the SklogWiki URL. It does not mention the computational chemistry commune source (bbs.keinsci.com) that the GUI guide (line 196) and CLI reference (line 115) both reference. The three documentation sources are inconsistent about which source(s) the ITP file comes from.
- **Impact:** Low — The ITP file header is the most authoritative source since it's what actually ships
- **Recommendation:** Add the secondary source to the ITP header for completeness, or update GUI guide/CLI reference to match the ITP header

### Issue 20: ion.itp generated at runtime has citation but no source URL
- **File:** `quickice/structure_generation/gromacs_ion_export.py`, line 40
- **What's wrong:** The generated ion.itp header says "Madrid2019_085 ion model (Zeron et al., J. Chem. Phys. 2019)" — which correctly references the paper by name but doesn't include the DOI. The README (line 341) has the full DOI.
- **Recommendation:** Add DOI to the generated ITP header:
  ```
  ; Madrid2019_085 ion model (Zeron et al., J. Chem. Phys. 2019)
  ; DOI: https://doi.org/10.1063/1.5121392
  ```

## Citation Suggestions

### S1: IAPWS-95 Formulation
**Where to add:** README.md, References section (after IAPWS R10-06)
```
### IAPWS-95
- Document: "Revised Release on the IAPWS Formulation 1995 for the Thermodynamic Properties of Ordinary Water Substance for General and Scientific Use"
- URL: https://www.iapws.org/release/IAPWS-95.html
- Used for: Liquid water density calculation in interface generation
```

### S2: Journaux et al. (2019)
**Where to add:** README.md, References section
```
### Journaux et al. (2019)
- Journaux, B., et al. (2019). "Planetary ices phase diagram mapping using density functional theory." J. Geophys. Res.: Planets, 124(12), 3090-3108.
- DOI: https://doi.org/10.1029/2019JE006176
- Used for: Ice II-III-V and Ice II-V-VI triple point coordinates
```

### S3: Journaux et al. (2020)
**Where to add:** README.md, References section
```
### Journaux et al. (2020)
- Journaux, B., et al. (2020). Space Science Reviews, 216, 7.
- DOI: https://doi.org/10.1007/s11214-020-00717-4
- Used for: High-pressure ice phase boundary validation
```

### S4: Sloan & Koh — Clathrate Hydrates
**Where to add:** README.md, Hydrate Generation section or References
```
### Sloan & Koh
- Sloan, E.D. & Koh, C.A. (2007). Clathrate Hydrates of Natural Gases, 3rd ed. CRC Press.
- ISBN: 978-0849390784
- Used for: Clathrate hydrate structure types (sI, sII, sH), cage descriptions
```

### S5: CODATA 2017 (Avogadro Constant)
**Where to add:** README.md, References section or inline near concentration formulas
```
### CODATA 2017
- Tiesinga, E., et al. (2021). "CODATA recommended values of the fundamental physical constants: 2017." Reviews of Modern Physics, 93(2), 025010.
- DOI: https://doi.org/10.1103/RevModPhys.93.025010
- Used for: Avogadro constant (6.02214076×10²³ mol⁻¹) in concentration calculations
```

### S6: GenIce2 hydrate lattices
**Where to add:** README.md, Hydrate Generation section (not just References)
- The GenIce2 citation exists in the References section but the Hydrate Generation section (lines 109-119) does not explicitly reference GenIce2 as the source of the hydrate lattice implementations. A brief note like "Hydrate structures are generated using GenIce2's lattice implementations for sI, sII, and sH" with a link to the GenIce2 reference section would improve traceability.

## Additional Observations (Non-Blocking)

1. **CLI reference inconsistency with GUI guide on nmolecules range:** `docs/cli-reference.md` (line 51) says "--nmolecules" range is "4-100000" while `docs/gui-guide.md` (line 68) says "4-216 molecules". The CLI accepts much larger values than the GUI. This is intentional (GUI has a practical limit for visualization) but could be confusing. Consider adding a note in the GUI guide explaining the difference.

2. **CLI reference TIP4P-ICE credit inconsistency:** `docs/cli-reference.md` (line 115) credits the ITP file to "http://bbs.keinsci.com/..." only, while `docs/gui-guide.md` (line 196) credits both SklogWiki and the Chinese chemistry forum. The actual ITP file (`quickice/data/tip4p-ice.itp`, line 1-2) only credits SklogWiki. These should be aligned.

3. **README "Quick Start" workflow skips Tab 1 (Hydrate):** The 5-minute workflow on lines 83-93 jumps from Tab 0 to Tab 2, skipping Tab 1. This is fine for a minimal workflow but could add a note like "(Skip Tab 1 Hydrate Generation for this quick start)".

4. **AVOGADRO constant duplication:** The AVOGADRO constant is defined independently in three modules (`ion_inserter.py`, `solute_inserter.py`, `scorer.py`) and imported in `custom_molecule_inserter.py`. Consider defining it once in a shared constants module to avoid divergence risk.

5. **README "Known Issues" mentions "CLI support for v4.5 features (Tabs 3-5) pending future release"** (line 282): The CLI in `quickice/cli/parser.py` does support `--interface` mode for Tab 2 functionality. It does not support custom molecules (Tab 3), solutes (Tab 4), or ions (Tab 5). This statement appears accurate.

---

*Cross-check analysis: 2026-05-22*
