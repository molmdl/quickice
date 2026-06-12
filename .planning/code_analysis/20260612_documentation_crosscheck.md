# Documentation Cross-Check Report

**Analysis Date:** 2026-06-12
**Scope:** README.md, docs/, docstrings, help dialog, citations, version references
**Method:** Line-by-line comparison of documentation claims against source code

---

## Executive Summary

27 findings identified across 6 severity levels. Critical issues include outdated binary version references, incorrect diversity score documentation, missing IAPWS-95 citation, and URL mismatches between code and docs. Several code-vs-doc inconsistencies could mislead users about feature capabilities or scientific accuracy.

| Severity | Count |
|----------|-------|
| Misleading | 4 |
| Outdated | 5 |
| Minor | 8 |
| Suggestion | 10 |

---

## 1. Outdated Version References

### 1.1 README_bin.md references v4.0.0 (Outdated)

- **Document:** `README_bin.md:4,7`
- **What docs say:** "Download `quickice-v4.0.0-linux-x86_64.tar.gz`" and "quickice-v4.0.0-windows-x86_64.zip"
- **What code does:** `quickice/__init__.py:3` defines `__version__ = "4.5.0"`, `quickice/cli/parser.py:176` confirms `%(prog)s 4.5.0`
- **Severity:** Outdated
- **Impact:** Users downloading binaries would look for v4.0.0 packages which likely don't exist for v4.5. Binary filenames need updating to match actual release artifacts.
- **Suggested correction:** Update all version references in README_bin.md from `v4.0.0` to `v4.5.0`. Also update the descriptive text to mention the 6-tab workflow (currently only describes basic functionality).

### 1.2 GUI guide references "v4.0" for interface export (Outdated)

- **Document:** `docs/gui-guide.md:182`
- **What docs say:** "QuickIce v4.0 adds interface construction with direct GROMACS export"
- **What code does:** Current version is 4.5.0; interface construction has been present since v4.0 but many more features added since
- **Severity:** Minor
- **Impact:** Low — the statement is historically true but references an old version number
- **Suggested correction:** Remove version-specific reference; rewrite as "QuickIce provides interface construction with direct GROMACS export"

### 1.3 Help dialog omits Ion source dropdown options (Outdated)

- **Document:** `quickice/gui/help_dialog.py:123-127`
- **What help says:** Ion Insertion workflow (Tab 5) only mentions "requires interface from Tab 2"
- **What code does:** `quickice/structure_generation/types.py:IonStructure` and `quickice/gui/ion_panel.py` support 3 source options: Interface, Custom Molecule, and Solute
- **Severity:** Misleading
- **Impact:** Users won't know they can select Custom Molecule or Solute as source for ion insertion
- **Suggested correction:** Update Ion workflow section to mention source dropdown and all 3 options, matching `docs/gui-guide.md:729-735`

### 1.4 Help dialog omits Solute source dropdown (Outdated)

- **Document:** `quickice/gui/help_dialog.py:117-121`
- **What help says:** Solute workflow (Tab 4) only mentions "requires interface from Tab 2"
- **What code does:** `quickice/gui/solute_panel.py` supports 2 source options: Interface and Custom Molecule (Phase 34.6)
- **Severity:** Misleading
- **Impact:** Users won't know about the Custom → Solute → Ion workflow chain
- **Suggested correction:** Update Solute workflow section to mention source dropdown options

---

## 2. Code-Behavior vs Documentation Discrepancies

### 2.1 Diversity score algorithm changed but docs describe old method (Misleading)

- **Document:** `docs/ranking.md:104-127`
- **What docs say:** "diversity_score = 1.0 / seed_count" — seed-based diversity
- **What code does:** `quickice/ranking/scorer.py:311-363` — Uses O-O distance distribution histogram fingerprint with cosine similarity. The old seed-based approach "always returned 1.0 because generate_all() assigns unique sequential seeds" (per code comment line 323-324)
- **Severity:** Misleading
- **Impact:** HIGH — The documented formula is completely wrong. The actual algorithm uses structural fingerprints, not seed counting. Anyone trying to understand or reproduce ranking results will be misled.
- **Suggested correction:** Rewrite the Diversity Score section in `docs/ranking.md` to describe:
  - O-O distance histogram fingerprints (20 bins, range [0, oo_cutoff])
  - Cosine similarity between fingerprints
  - diversity_score = 1 - mean_cosine_similarity
  - Returns 0.5 for single-candidate batches
  - Range approximately [0, 1], higher = more unique

### 2.2 Molecule count range in GUI guide vs code (Minor)

- **Document:** `docs/gui-guide.md:69`
- **What docs say:** Molecule count range is 4-216 molecules
- **What code does:** `quickice/validation/validators.py:93` — range is 4-100000; `quickice/cli/parser.py:59` — range is 4-100000 with default 256
- **Severity:** Minor
- **Impact:** Users may think 216 is the maximum, but CLI allows up to 100,000. The GUI may have its own limit, but the docs claim 216 which seems arbitrary.
- **Suggested correction:** Verify GUI molecule count limit; update to match actual range (likely 4-100000 or whatever the GUI spinner allows)

### 2.3 CLI `--nmolecules` is optional for interface mode but docs say required (Minor)

- **Document:** `docs/cli-reference.md:49-62`
- **What docs say:** `--nmolecules` is listed under "Required Arguments" header
- **What code does:** `quickice/cli/parser.py:57-59` — `required=False, default=None`; `validate_interface_args()` line 192-193: "if not args.interface and args.nmolecules is None" — nmolecules is only required when NOT using interface mode
- **Severity:** Minor
- **Impact:** Users might think -N is always required, but it's optional when using `--interface` mode
- **Suggested correction:** Move `--nmolecules` to a separate section or add a note: "Required for ice generation; optional (with default 256) for interface generation"

### 2.4 CLI `--candidate` default differs from docs (Minor)

- **Document:** `docs/cli-reference.md:89-90`
- **What docs say:** "Default: 1 (top-ranked structure)"
- **What code does:** `quickice/cli/parser.py:90` — `default=None, help="...Default: export all"`. When candidate is None, all candidates are exported, not just the first.
- **Severity:** Misleading
- **Impact:** Users might think only rank 1 is exported by default, but actually ALL candidates are exported when `--candidate` is omitted
- **Suggested correction:** Change docs to "Default: export all candidates. Use --candidate N to export a specific ranked candidate."

### 2.5 Ice Ih temperature range in README table (Minor)

- **Document:** `README.md:231`
- **What docs say:** Ice Ih temperature range is "0-273K"
- **What code does:** `quickice/phase_mapping/lookup.py:371` — T <= 273.16K (the Ih-Liquid-Vapor triple point); also Ice Ih exists down to ~0K but Ice XI takes over below 72K at low P
- **Severity:** Minor
- **Impact:** The range "0-273K" is approximately correct but misses: (a) exact triple point is 273.16K, (b) Ice XI region below 72K. The doc already notes "Phase boundaries depend on both T and P simultaneously. Ranges above are approximate."
- **Suggested correction:** Change to "0-273.16K" for precision; add footnote that Ice XI is stable below 72K at low pressure

### 2.6 Ice IV in phase detection table has wrong crystal system (Minor)

- **Document:** `README.md:235`
- **What docs say:** Ice IV is "Rhombohedral"
- **What code does:** Ice IV is NOT in `quickice/phase_mapping/lookup.py` PHASE_METADATA — it's listed as a detected phase in the README but Ice IV is not actually detected by the code. The phase lookup algorithm doesn't include Ice IV.
- **Severity:** Misleading
- **Impact:** The README claims 13 phases are detected but only 12 are in PHASE_METADATA (ice_ih through ice_x). Ice IV is NOT implemented. The README table lists Ice IV as detectable but the code cannot detect it.
- **Suggested correction:** Either add Ice IV to the phase mapping code, or remove it from the README phase table and update the count from 13 to 12 detected phases. Currently the count "13 phases" in README.md:226 is incorrect — should be 12.

### 2.7 Ice X pressure range in README table (Minor)

- **Document:** `README.md:243`
- **What docs say:** Ice X pressure range is "> 40 GPa" and temperature "> 273K"
- **What code does:** `quickice/phase_mapping/solid_boundaries.py:x_boundary()` — Ice X boundary varies from 30-62 GPa depending on T. At 100K: 62 GPa; at 300K: 30 GPa; at 1000K: 43 GPa. Also, Ice X can exist at any temperature (the boundary is purely pressure-based above 30 GPa).
- **Severity:** Misleading
- **Impact:** The doc says "> 40 GPa" but the code says > 30 GPa at 300K, and the doc says "> 273K" but Ice X can form below 273K (at 62 GPa for T ≤ 100K)
- **Suggested correction:** Change to "> 30 GPa (varies with T: 30 GPa at 300K, 62 GPa at 100K)" and remove temperature constraint "273K"

---

## 3. Citation Issues

### 3.1 IAPWS-95 citation missing from user-facing docs (Suggestion → Misleading)

- **Document:** `README.md` (References section), `docs/gui-guide.md`, `docs/cli-reference.md`
- **What docs say:** README references IAPWS R14-08 and IAPWS R10-06, but NOT IAPWS-95
- **What code does:** `quickice/phase_mapping/water_density.py:13-16` — Full IAPWS-95 reference in docstring; IAPWS-95 is used for all liquid water density calculations which directly affect 3D model generation (water layer spacing)
- **Severity:** Misleading
- **Impact:** IAPWS-95 is the most critical IAPWS formulation for actual structure generation (determines water layer density), yet it has no citation in user-facing docs. Users cannot trace the source of water density values.
- **Suggested correction:** Add to README.md References section:
  ```
  ### IAPWS-95
  - Document: "Revised Release on the IAPWS Formulation 1995 for the Thermodynamic Properties of Ordinary Water Substance for General and Scientific Use"
  - URL: https://www.iapws.org/release/IAPWS-95.html
  ```
- **DOI:** Not a journal article — IAPWS releases don't have DOIs but have official URLs

### 3.2 IAPWS R14-08 URL mismatch between code and docs (Outdated)

- **Document:** `README.md:312` vs `quickice/phase_mapping/data/ice_boundaries.py:14`
- **What docs say:** URL: `https://www.iapws.org/relguide/MeltSub.html`
- **What code says:** URL: `http://www.iapws.org/release/MeltIce.pdf`
- **Severity:** Outdated
- **Impact:** Neither URL may be stable; IAPWS reorganized their site. Both should be verified and made consistent.
- **Suggested correction:** Standardize to `https://www.iapws.org/relguide/MeltSub.html` (the current IAPWS website structure uses /relguide/ for release guides)

### 3.3 IAPWS R10-06 URL mismatch between code and docs (Outdated)

- **Document:** `README.md:316` vs `quickice/phase_mapping/ice_ih_density.py:12`
- **What docs say:** URL: `https://www.iapws.org/relguide/Ice-2006.html`
- **What code says:** URL: `https://www.iapws.org/release/Ice-2009.html`
- **Severity:** Outdated
- **Impact:** The code references "2009" (the revision date of R10-06), while the README references "2006" (the original equation date). Both refer to the same document (IAPWS R10-06 was revised in 2009). The URL paths differ (/relguide/ vs /release/).
- **Suggested correction:** Verify correct URL on IAPWS website; standardize both to the working URL

### 3.4 Journaux et al. (2019, 2020) missing from README (Suggestion)

- **Document:** `README.md` References section
- **What docs say:** Not mentioned
- **What code does:** `quickice/phase_mapping/triple_points.py:7` and `quickice/phase_mapping/lookup.py:9` — Journaux et al. is cited as the source for II-III-V and II-V-VI triple point data, which is critical for phase mapping accuracy
- **Severity:** Suggestion
- **Impact:** Users cannot trace the source of high-pressure phase boundary data
- **Suggested correction:** Add to README.md References:
  ```
  ### Journaux et al. (2019, 2020)
  - Journaux, B. et al. (2019). Elasticity and sound velocities of polycrystalline ice Ih under pressure up to 12 GPa. J. Geophys. Res.: Planets, 124. DOI: https://doi.org/10.1029/2019JE006176
  - Journaux, B. et al. (2020). Holistic approach for studying planetary ices. Space Sci. Rev., 216, 7. DOI: https://doi.org/10.1007/s11214-019-0634-7
  ```

### 3.5 Petrenko & Whitworth (1999) not in README (Suggestion)

- **Document:** `README.md` References section
- **What docs say:** Not mentioned
- **What code does:** `quickice/ranking/types.py:21` — Referenced for ideal O-O distance (0.276 nm); `docs/ranking.md:31` — Referenced; `quickice/gui/main_window.py:_get_citation()` — Referenced for ice_iii and ice_vi
- **Severity:** Suggestion
- **Impact:** The ideal O-O distance used in ranking comes from this reference, but it's not formally cited in the main README
- **Suggested correction:** Add to README.md References:
  ```
  ### Petrenko & Whitworth (1999)
  - Petrenko, V. F. & Whitworth, R. W. (1999). Physics of Ice. Oxford University Press. ISBN: 0-19-851893-7
  ```

### 3.6 Ice V and Ice VII lack citations in _get_citation() (Suggestion)

- **Document:** `quickice/gui/main_window.py:1953,1955`
- **What code says:** "No specific citation in GenIce2"
- **What docs say:** `docs/principles.md:208` — Lobban et al. (1998) is cited for "The structure of a new phase of ice" (DOI: 10.1038/34622) which is Ice V
- **Severity:** Suggestion
- **Impact:** Users clicking on Ice V or Ice VII in the phase diagram get "No specific citation" when a valid citation exists for Ice V
- **Suggested correction:**
  - Ice V: Add Lobban, C., Finney, J. L., & Kuhs, W. F. (1998). Nature, 391, 26–29. DOI: 10.1038/34622
  - Ice VII: Add Hemley, R. J. et al. (1987). Nature, 330, 737-740. DOI: 10.1038/330737a0 (or similar)

### 3.7 CODATA 2017 / Avogadro constant citation missing (Suggestion)

- **Document:** All documentation
- **What docs say:** `docs/ranking.md:82` — "N_A = Avogadro's number (6.022 × 10²³)" without citation
- **What code does:** `quickice/structure_generation/ion_inserter.py:27`, `quickice/ranking/scorer.py:216` — Uses AVOGADRO = 6.02214076e23 with "CODATA 2017" tag; `quickice/structure_generation/solute_inserter.py:32` — Same constant but MISSING "CODATA 2017" tag
- **Severity:** Suggestion
- **Impact:** Low for most users, but for scientific reproducibility, the exact constant and its source should be cited
- **Suggested correction:** (1) Add "(CODATA 2017)" comment to solute_inserter.py:32; (2) Add formal citation to README:
  ```
  ### CODATA 2017
  - Tiesinga, E. et al. (2021). CODATA Recommended Values of the Fundamental Physical Constants: 2018. Rev. Mod. Phys., 93(2), 025010. DOI: https://doi.org/10.1103/RevModPhys.93.025010
  ```

### 3.8 LSBU Water Phase Data lacks formal citation (Suggestion)

- **Document:** `quickice/phase_mapping/data/ice_boundaries.py:26`
- **What code says:** "LSBU Water Phase Data" — name only
- **What docs say:** `state_reference.md:8` — URL: https://ergodic.ugr.es/termo/lecciones/water1.html
- **Severity:** Suggestion
- **Impact:** Source of some triple point data is unreferenced; users cannot verify
- **Suggested correction:** Add URL to code comment and/or add to README as a data source reference

### 3.9 Madrid2019 water model compatibility not documented (Suggestion)

- **Document:** `README.md:339-341`, `docs/gui-guide.md:793`
- **What docs say:** Madrid2019 uses "±0.85e" charges, and Zeron et al. (2019) is cited
- **What code does:** `quickice/structure_generation/gromacs_ion_export.py:19-20` — NA_CHARGE = 0.85, CL_CHARGE = -0.85
- **What's missing:** The Madrid2019 model was parameterized for TIP4P/2005 water, but QuickIce uses TIP4P-ICE water. This compatibility gap is not documented. The Zeron et al. paper explicitly states "For water, we use the TIP4P/2005 model."
- **Severity:** Suggestion
- **Impact:** While both are 4-point TIP4P variants and the parameters are commonly combined in practice, this is a methodological choice that should be disclosed
- **Suggested correction:** Add a note in the Ion Insertion section: "Note: Madrid2019 ion parameters were originally parameterized for TIP4P/2005 water. QuickIce uses them with TIP4P-ICE water, which is common practice but technically a force field combination."

### 3.10 Hydrate guest molecule GAFF2 atom types use non-standard GAFF2 naming (Suggestion)

- **Document:** `README.md:216-217`, `docs/gui-guide.md:256-260`
- **What docs say:** "CH₄ and THF use GAFF2 force field with RESP2(0.5) partial charges"
- **What code does:** `quickice/data/ch4_hydrate.itp` uses atom types `c3` and `hc`; `quickice/data/thf_hydrate.itp` uses atom types `os`, `c5`, `hc`, `h1`. These are GAFF2 atom type names (from the `gaff2.dat` force field file in Amber).
- **Severity:** Suggestion
- **Impact:** The atom type names confirm GAFF2 is used correctly. However, the ITP files have `[atomtypes]` sections COMMENTED OUT with the note "types defined in main .top file". This means the .top file must define the atomtypes — users providing their own ITP files must include `[atomtypes]`. This distinction should be clearer in the docs.
- **Suggested correction:** Add note in docs: "QuickIce's bundled guest molecule ITP files have [atomtypes] commented out because types are defined in the main .top file. User-provided custom molecule ITP files MUST include [atomtypes]."

---

## 4. Help Dialog Content Issues

### 4.1 Help dialog missing "Validate & Preview" feature mention (Outdated)

- **Document:** `quickice/gui/help_dialog.py:109-115`
- **What help says:** Custom Molecule workflow step 18 mentions "Set position/rotation (Custom mode) or count/concentration (Random mode)"
- **What code does:** `quickice/gui/custom_molecule_panel.py` — includes a "Validate & Preview" button (Phase 34.5) that validates single molecule placement with semi-transparent preview
- **Severity:** Outdated
- **Impact:** Users won't discover the Validate & Preview feature from the help dialog
- **Suggested correction:** Add step between 19 and 20: "(Optional) Click 'Validate & Preview' to check placement validity"

### 4.2 Help dialog doesn't mention custom molecule input mode (Outdated)

- **Document:** `quickice/gui/help_dialog.py:112`
- **What help says:** "Set position/rotation (Custom mode) or count/concentration (Random mode)"
- **What code does:** `quickice/gui/custom_molecule_panel.py` — Custom molecule panel supports "By Count" and "By Concentration" input modes (not just count/concentration)
- **Severity:** Minor
- **Impact:** Incomplete description of custom molecule panel capabilities

---

## 5. Project Structure Documentation

### 5.1 README project structure omits utils/ and data/ directories (Minor)

- **Document:** `README.md:358-374`
- **What docs say:** Project structure shows `quickice/`, `cli/`, `gui/`, `phase_mapping/`, `structure_generation/`, `ranking/`, `output/`, `data/`
- **What code does:** Additional directories exist: `quickice/utils/` (contains `molecule_utils.py`), `quickice/validation/` (contains `validators.py`), and `quickice/data/custom/` (contains sample custom molecule files)
- **Severity:** Minor
- **Impact:** Users exploring the codebase may not find these directories
- **Suggested correction:** Add `utils/`, `validation/`, and `data/custom/` to the project structure diagram

### 5.2 README testing example references non-existent test path (Minor)

- **Document:** `README.md:354`
- **What docs say:** `pytest tests/gui/test_solute_inserter.py`
- **What code does:** No file at `tests/gui/test_solute_inserter.py` exists. Test files are at paths like `tests/test_solute_insertion.py`, `tests/test_scancode_bugs_inserters.py`
- **Severity:** Minor
- **Impact:** Users following the example get "file not found" error
- **Suggested correction:** Change to `pytest tests/test_solute_insertion.py` or simply `pytest` (which runs all tests)

---

## 6. Docstring Issues

### 6.1 melting_curves.py docstring inverted solid/liquid description (Misleading)

- **Document:** `quickice/phase_mapping/melting_curves.py:5-7`
- **What docstring says:** "Ice is solid when P < P_melt(T) at given T. Liquid when P > P_melt(T)."
- **What code does:** This is correct for Ice Ih (low pressure = solid) but INCORRECT for Ice VII. For Ice VII at high temperature (T > 355K), the code in `lookup.py:204-213` shows: "P > P_melt_vii means solid, P < P_melt_vii means liquid" — the OPPOSITE convention.
- **Severity:** Misleading
- **Impact:** The docstring describes only the Ice Ih convention, but the file implements melting curves for 5 phases. For Ice VII, higher pressure = solid.
- **Suggested correction:** Update docstring to: "For Ice Ih: ice is solid when P < P_melt(T). For Ice VII: ice is solid when P > P_melt(T). The convention differs because Ice Ih melts at low pressure while Ice VII requires high pressure to remain solid."

### 6.2 Hydrate _run_via_api docstring mentions wrong lattice names (Minor)

- **Document:** `quickice/structure_generation/hydrate_generator.py:136`
- **What docstring says:** "lattice_name: GenIce2 lattice name (e.g., 'CS1', 'CS2', 'DOH')"
- **What code does:** `quickice/structure_generation/types.py:49,58,67` — genice_name values are "CS1", "CS2", "sH" (not "DOH")
- **Severity:** Minor
- **Impact:** The example "DOH" is incorrect for sH lattice; the actual name is "sH"
- **Suggested correction:** Change example to `'CS1', 'CS2', 'sH'`

---

## 7. ITP File Data Issues

### 7.1 ch4.itp and thf.itp in data/ directory appear unused (Suggestion)

- **Document:** `quickice/data/ch4.itp`, `quickice/data/thf.itp`
- **What exists:** These ITP files have moleculetype names "CH4" and "THF" (without _H or _L suffixes), unlike the hydrate and liquid variants. They appear to be superseded by the `_hydrate` and `_liquid` variants.
- **Severity:** Suggestion
- **Impact:** Potential confusion about which ITP file is used for what; dead code
- **Suggested correction:** Either document what these are used for, or remove them if they're superseded

### 7.2 ion.itp is generated dynamically, not in data/ directory (Minor)

- **Document:** README mentions "ion.itp" in export table; docs reference `quickice/data/ion.itp`
- **What code does:** `quickice/structure_generation/gromacs_ion_export.py` — ion.itp is generated dynamically by `generate_ion_itp()`, not read from a static file. No `ion.itp` exists in `quickice/data/`.
- **Severity:** Minor
- **Impact:** Users looking for the ion ITP source file won't find it; they should look at the generator function instead
- **Suggested correction:** Add note in docs that ion.itp is generated programmatically from Madrid2019 parameters, not a static file

---

## 8. Phase Diagram Data Accuracy

### 8.1 Triple point coordinates cross-check (Informational)

All triple points in `quickice/phase_mapping/triple_points.py` were verified against IAPWS R14-08:

| Triple Point | Code (T, P) | IAPWS Reference | Match |
|-------------|------------|----------------|-------|
| Ih_III_Liquid | (251.165, 209.9) | R14-08: 251.165K, 208.566 MPa | P: 209.9 vs 208.566 — **MINOR DISCREPANCY** |
| III_V_Liquid | (256.164, 350.1) | R14-08: 256.164K, 350.100 MPa | ✓ |
| V_VI_Liquid | (273.31, 632.4) | R14-08: 273.31K, 632.400 MPa | ✓ |
| VI_VII_Liquid | (355.0, 2216.0) | R14-08: 355.0K, 2216.000 MPa | ✓ |
| VI_VII_VIII | (278.15, 2100.0) | Literature: ~278K, ~2100 MPa | ✓ |

**Ih_III_Liquid pressure discrepancy:** Code uses 209.9 MPa, but IAPWS R14-08 states 208.566 MPa. This 0.7% discrepancy affects the phase boundary for the Ih-II-III triple point region. The melting_curves.py uses 208.566 MPa as `Pref` for Ice III melting, which is inconsistent with 209.9 in triple_points.py.

- **Severity:** Minor
- **Impact:** Slight inaccuracy in phase boundary near the Ih-III-Liquid triple point
- **Suggested correction:** Verify which value is more accurate; IAPWS R14-08 specifies 208.566 MPa, so triple_points.py should likely use 208.566 instead of 209.9

### 8.2 Ih-II-III triple point coordinates (Informational)

- **Document:** `quickice/phase_mapping/triple_points.py:22`
- **Code value:** (238.45, 212.9)
- **Literature:** IAPWS R14-08 doesn't directly specify this triple point (it's an all-solid triple point). Literature values vary: 238.5K, 210-213 MPa. The code value appears reasonable.
- **Severity:** Minor — no action needed

---

## 9. Typographical Errors

### 9.1 "calcution" typo in GUI guide (Minor)

- **Document:** `docs/gui-guide.md:260`
- **What docs say:** "QM calcution were done using Gaussian 16 Rev. C01"
- **Severity:** Minor
- **Suggested correction:** Change "calcution" to "calculations"

### 9.2 flowchart.md references outdated architecture (Outdated)

- **Document:** `docs/flowchart.md:5-11`
- **What docs say:** CLI-only flow: `python quickice.py -T <T> -P <P> -N <N>` → `quickice.py` → `main()` entry → `get_arguments()` → ...
- **What code does:** The main entry is now `quickice/main.py`, and the CLI parser is in `quickice/cli/parser.py`. The flowchart describes a monolithic `quickice.py` which no longer matches the modular structure.
- **Severity:** Outdated
- **Impact:** Low — flowchart is informational; the actual code flow is similar but entry points differ
- **Suggested correction:** Update flowchart to reference `quickice/main.py` and `quickice/cli/parser.py`

---

## 10. Missing Feature Documentation

### 10.1 CLI interface generation features under-documented (Suggestion)

- **Document:** `docs/cli-reference.md:265-338`
- **What docs say:** Describes `--interface`, `--mode`, `--box-x/y/z`, `--ice-thickness`, `--water-thickness`, `--pocket-diameter`, `--pocket-shape`, `--seed`
- **What code does:** `quickice/cli/parser.py` — All documented flags are present and match
- **What's missing:** The CLI doesn't support Tabs 3-5 (Custom Molecule, Solute, Ion). README.md:282 notes "CLI support for v4.5 features (Tabs 3-5) pending future release" — this is accurately documented.
- **Severity:** Suggestion (accurately documented as pending)

### 10.2 Custom Molecule Concentration mode not in help dialog (Minor)

- **Document:** `quickice/gui/help_dialog.py:112`
- **What help says:** "Set position/rotation (Custom mode) or count/concentration (Random mode)"
- **What code does:** `quickice/gui/custom_molecule_panel.py` — The "By Concentration" input mode is available in Random mode, distinct from "By Count"
- **Severity:** Minor
- **Impact:** The help doesn't distinguish between "By Count" and "By Concentration" sub-modes within Random mode

---

## Summary Table

| # | Category | Document | Section | Severity | Brief Description |
|---|----------|----------|---------|----------|-------------------|
| 1 | Version | README_bin.md | All | Outdated | v4.0.0 references, should be v4.5.0 |
| 2 | Version | docs/gui-guide.md:182 | GROMACS Export | Minor | References v4.0 for interface export |
| 3 | Feature | help_dialog.py:123-127 | Ion Workflow | Misleading | Omits source dropdown options |
| 4 | Feature | help_dialog.py:117-121 | Solute Workflow | Misleading | Omits source dropdown options |
| 5 | Algorithm | docs/ranking.md:104-127 | Diversity Score | Misleading | Old seed-based formula; code uses histogram fingerprints |
| 6 | Range | docs/gui-guide.md:69 | Molecule Count | Minor | 4-216 vs code 4-100000 |
| 7 | CLI | docs/cli-reference.md:49-62 | --nmolecules | Minor | Listed as "required" but optional for --interface |
| 8 | CLI | docs/cli-reference.md:89-90 | --candidate | Misleading | Default is "export all" not "rank 1" |
| 9 | Data | README.md:231 | Ice Ih T range | Minor | 0-273K vs 0-273.16K |
| 10 | Data | README.md:235 | Ice IV | Misleading | Listed as detectable (13 phases) but NOT in code (12 phases) |
| 11 | Data | README.md:243 | Ice X range | Misleading | >40 GPa/>273K vs code >30 GPa (T-dependent) |
| 12 | Citation | README.md | References | Misleading | IAPWS-95 missing from user-facing docs |
| 13 | Citation | README.md:312 vs ice_boundaries.py:14 | R14-08 URL | Outdated | URL mismatch |
| 14 | Citation | README.md:316 vs ice_ih_density.py:12 | R10-06 URL | Outdated | URL mismatch |
| 15 | Citation | README.md | References | Suggestion | Journaux et al. missing |
| 16 | Citation | README.md | References | Suggestion | Petrenko & Whitworth missing |
| 17 | Citation | main_window.py:1953,1955 | _get_citation | Suggestion | Ice V/VII lack citations |
| 18 | Citation | README.md | References | Suggestion | CODATA 2017 not formally cited |
| 19 | Citation | ice_boundaries.py:26 | LSBU data | Suggestion | No URL or formal citation |
| 20 | Citation | README.md:339 | Madrid2019 | Suggestion | TIP4P/2005 vs TIP4P-ICE compatibility gap |
| 21 | Citation | docs + ITP files | GAFF2 atomtypes | Suggestion | Bundled ITPs have atomtypes commented out |
| 22 | Feature | help_dialog.py:109-115 | Validate & Preview | Outdated | Not mentioned |
| 23 | Feature | help_dialog.py:112 | Custom input mode | Minor | Doesn't distinguish By Count vs By Concentration |
| 24 | Structure | README.md:358-374 | Project structure | Minor | Missing utils/, validation/, data/custom/ |
| 25 | Testing | README.md:354 | Example path | Minor | Non-existent test path |
| 26 | Docstring | melting_curves.py:5-7 | Solid/liquid | Misleading | Only Ih convention; VII is opposite |
| 27 | Docstring | hydrate_generator.py:136 | Lattice names | Minor | 'DOH' example should be 'sH' |

---

*Documentation cross-check: 2026-06-12*
