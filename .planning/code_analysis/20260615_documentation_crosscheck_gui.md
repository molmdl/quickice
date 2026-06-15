# GUI Documentation Cross-Check Report (Scancode Task C)

**Analysis Date:** 2026-06-15
**Scope:** GUI-facing documentation: `docs/gui-guide.md`, `quickice/gui/help_dialog.py`, `README.md` (GUI sections), tooltips in `*_panel.py`, `docs/principles.md`, `docs/ranking.md`, citations
**Method:** Line-by-line comparison of documentation claims against source code, with delta analysis from `.planning/code_analysis/20260612_documentation_crosscheck.md`
**Focus:** CHANGED content since Phase 34.5/34.6 validation features, Phase 35 tooltips/help, Phase 36/37 unified entry

---

## Executive Summary

18 findings identified across 5 severity levels. Key new findings include: Interface Panel tooltips reference WRONG tab numbers (pre-Phase 34.3 numbering), solute tooltip incorrectly describes THF as a 4-membered ring, custom molecule tooltip says "no overlap checking" but code implements it, README feature bullet list contradicts its own phase detection table, and multiple screenshot paths in `docs/gui-guide.md` don't match actual filenames.

Several previously flagged items from the 2026-06-12 scan have been FIXED (see Section 9).

| Severity | Count |
|----------|-------|
| Misleading | 4 |
| Outdated | 4 |
| Minor | 5 |
| Suggestion | 5 |

---

## 1. Tab Numbering: Interface Panel Tooltips Use Pre-Reorder Numbers (Misleading)

The Interface Construction panel tooltips reference OLD tab numbers from before the Phase 34.3 tab reorder (which added Custom Molecule at Tab 3 and Solute at Tab 4, moving Ion to Tab 5). The current tab layout is:

| Tab Index | Tab Name | `quickice/gui/constants.py` |
|-----------|----------|-----------------------------|
| 0 | Ice Generation | `TabIndex.ICE` |
| 1 | Hydrate Generation | `TabIndex.HYDRATE` |
| 2 | Interface Construction | `TabIndex.INTERFACE` |
| 3 | Custom Molecule | `TabIndex.CUSTOM` |
| 4 | Solute Insertion | `TabIndex.SOLUTE` |
| 5 | Ion Insertion | `TabIndex.ION` |

### 1.1 Ice Candidate tooltip references "Tab 1" instead of Tab 0

- **Document:** `quickice/gui/interface_panel.py:261`
- **What tooltip says:** `"Ice Candidate — Use ice structure from Tab 1"`
- **What code does:** `TabIndex.ICE = 0` — Ice Generation is Tab 0
- **Severity:** Misleading
- **Impact:** Users directed to wrong tab

### 1.2 Hydrate Structure tooltip references "Tab 3" instead of Tab 1

- **Document:** `quickice/gui/interface_panel.py:262`
- **What tooltip says:** `"Hydrate Structure — Generate hydrate directly in Tab 3"`
- **What code does:** `TabIndex.HYDRATE = 1` — Hydrate Generation is Tab 1
- **Severity:** Misleading
- **Impact:** Users directed to wrong tab

### 1.3 HelpIcon references "Tab 2" instead of Tab 1

- **Document:** `quickice/gui/interface_panel.py:267`
- **What HelpIcon says:** `"without going to Tab 2"`
- **What code does:** Hydrate tab is Tab 1, not Tab 2
- **Severity:** Misleading

### 1.4 Candidate dropdown tooltip references "Tab 1" instead of Tab 0

- **Document:** `quickice/gui/interface_panel.py:424`
- **What tooltip says:** `"Select an ice candidate from Tab 1 for interface generation"`
- **What code does:** Ice candidates come from Tab 0
- **Severity:** Misleading

### 1.5 Refresh button tooltip references "Tab 1" instead of Tab 0

- **Document:** `quickice/gui/interface_panel.py:436`
- **What tooltip says:** `"Click after generating new candidates in Tab 1"`
- **What code does:** Candidates generated in Tab 0
- **Severity:** Misleading

**Root cause:** These tooltips were written during Phase 32 when the tab layout was Ice (Tab 0), Interface (Tab 1), Ion (Tab 2). The Phase 34.3 reorder inserted Hydrate at Tab 1 and shifted Interface to Tab 2, but the interface panel tooltips were not updated.

---

## 2. Scientific Inaccuracy: THF Ring Size in Solute Tooltip (Misleading)

- **Document:** `quickice/gui/solute_panel.py:210`
- **What tooltip says:** `"THF (tetrahydrofuran): 4-membered ring, commonly used in hydrate studies"`
- **What science says:** THF (tetrahydrofuran, C₄H₈O) is a **5-membered ring** consisting of 4 carbon atoms and 1 oxygen atom
- **Severity:** Misleading
- **Impact:** Scientifically incorrect information displayed to users in a research tool
- **Suggested correction:** Change "4-membered ring" to "5-membered ring"

---

## 3. Custom Mode Overlap Checking: Tooltip Contradicts Code (Misleading)

- **Document:** `quickice/gui/custom_molecule_panel.py:256`
- **What tooltip says:** `"Custom: User-specified positions and rotations\n  - No overlap checking (user responsibility)"`
- **What code does:** `quickice/gui/custom_molecule_panel.py` implements center-to-center overlap detection with 0.25 nm threshold when adding positions. A warning dialog appears when overlap is detected.
- **What docs say:** `docs/gui-guide.md:529-533` correctly describes the overlap detection: "When adding a position, the system checks for center-to-center overlap with existing positions (default threshold: 0.25 nm)"
- **Severity:** Misleading
- **Impact:** Users may avoid adding nearby positions thinking overlap won't be detected, or may be confused when they see the overlap warning despite the tooltip saying there's no checking
- **Suggested correction:** Change tooltip to "Custom: User-specified positions and rotations\n  - Position-based overlap checking (0.25 nm threshold)\n  - For precise collision avoidance, use Validate & Preview"

---

## 4. README Feature List vs Phase Detection Table: Ice IV/XV Inconsistency (Minor)

- **Document:** `README.md:116` (feature bullet) vs `README.md:244-257` (phase table)
- **What feature bullet says:** `"12 ice polymorphs — Ih, Ic, II, III, IV, V, VI, VII, VIII, IX, XI, X"`
- **What phase table shows:** 12 phases: Ih, Ic, II, III, V, VI, VII, VIII, IX, XI, XV, X — **excludes Ice IV, includes Ice XV**
- **Severity:** Minor
- **Impact:** The bullet list includes Ice IV (not detected by code) and omits Ice XV (detected by code). The table is correct.
- **Suggested correction:** Change bullet to: `"12 ice polymorphs — Ih, Ic, II, III, V, VI, VII, VIII, IX, XI, XV, X"`

---

## 5. Screenshot References Don't Match Actual Filenames (Minor)

- **Document:** `docs/gui-guide.md` (multiple lines)
- **Actual files in:** `docs/images/`

| gui-guide.md Reference | Line | Actual Filename | Status |
|------------------------|------|----------------|--------|
| `images/slab-interface.png` | 344 | `tab2-slab-interface.png` | Mismatch |
| `images/pocket-interface.png` | 352 | `tab2-pocket-interface.png` | Mismatch |
| `images/piece-interface.png` | 359 | `tab2-piece-interface.png` | Mismatch |
| `images/hydrate-panel.png` | 241 | `tab2-hydrate-panel.png` | Mismatch |
| `images/ion-panel.png` | 741 | `tab4-ion-panel.png` | Mismatch |
| `images/custom-molecule-panel.png` | 427 | — | Missing |
| `images/solute-panel.png` | 621 | — | Missing |
| `images/quickice-v4-gui.png` | 38 | `quickice-v4-gui.png` | OK |
| `images/phase-diagram.png` | 77 | `phase-diagram.png` | OK |
| `images/3d-viewer.png` | 117 | `3d-viewer.png` | OK |
| `images/dual-viewport.png` | 120 | `dual-viewport.png` | OK |
| `images/export-menu.png` | 155 | `export-menu.png` | OK |

- **Severity:** Minor
- **Impact:** Broken image links in rendered documentation; 2 screenshots don't exist at all
- **Suggested correction:** Update all 5 mismatched paths to use actual filenames; create missing custom-molecule-panel.png and solute-panel.png screenshots

---

## 6. docs/principles.md: Diversity Score Description Still Outdated (Outdated)

- **Document:** `docs/principles.md:73`
- **What docs say:** `"Diversity score: Rewards unique seeds"`
- **What code does:** `quickice/ranking/scorer.py:318-370` — Uses O-O distance distribution histogram fingerprints with cosine similarity. The old seed-based approach was replaced because "generate_all() assigns unique sequential seeds" (scorer.py:330-331)
- **Severity:** Outdated
- **Impact:** `docs/ranking.md` was correctly updated to describe the histogram method, but `docs/principles.md` was not
- **Suggested correction:** Change to `"Diversity score: Rewards structural uniqueness via O-O distance fingerprints"`

---

## 7. Unfixed from Prior Scan: Ice X Range in README (Outdated)

- **Document:** `README.md:257`
- **What docs say:** `"Ice X | Symmetric | > 40 GPa | > 273K"`
- **What code does:** `quickice/phase_mapping/solid_boundaries.py` — Ice X boundary varies from 30-62 GPa depending on T (30 GPa at 300K, 62 GPa at 100K). No temperature constraint; Ice X can exist at any temperature.
- **Severity:** Outdated (was Finding 2.7 in 20260612 scan)
- **Impact:** Users given incorrect pressure range and incorrect temperature constraint
- **Suggested correction:** Change to `"> 30 GPa (T-dependent: 30 at 300K, 62 at 100K)"` and remove `> 273K` temperature

---

## 8. Unfixed from Prior Scan: `_get_citation()` Returns "No Specific Citation" for Ice V and Ice VII (Suggestion)

- **Document:** `quickice/gui/main_window.py:1953,1955`
- **What code says:** `"Monoclinic ice V. No specific citation in GenIce2."` and `"High-pressure ice VII. No specific citation in GenIce2."`
- **What docs say:** `docs/principles.md:208` cites Lobban et al. (1998) for Ice V
- **Severity:** Suggestion (was Finding 3.6 in 20260612 scan)
- **Impact:** Users clicking on Ice V or Ice VII in the phase diagram get "No specific citation" when valid citations exist
- **Suggested corrections:**
  - Ice V: `"Lobban, C., Finney, J.L. & Kuhs, W.F. (1998). Nature, 391, 26-29. DOI: 10.1038/34622"`
  - Ice VII: `"Hemley, R.J. et al. (1987). Nature, 330, 737-740. DOI: 10.1038/330737a0"`

---

## 9. Unfixed from Prior Scan: Test Path in README (Minor)

- **Document:** `README.md:387`
- **What docs say:** `pytest tests/gui/test_solute_inserter.py`
- **What exists:** No file at that path; test files are at paths like `tests/test_solute_insertion.py`
- **Severity:** Minor (was Finding 5.2 in 20260612 scan)
- **Suggested correction:** Change to `pytest tests/test_solute_insertion.py` or simply `pytest`

---

## 10. Unfixed from Prior Scan: gui-guide.md Version Reference (Minor)

- **Document:** `docs/gui-guide.md:182`
- **What docs say:** `"QuickIce v4.0 adds interface construction with direct GROMACS export"`
- **What code does:** Current version is 4.5.0; interface construction has been present since v4.0
- **Severity:** Minor (was Finding 1.2 in 20260612 scan)
- **Suggested correction:** Remove version-specific reference; rewrite as "QuickIce provides interface construction with direct GROMACS export"

---

## 11. Help Dialog: Solute Tab Prerequisite Incomplete (Suggestion)

- **Document:** `quickice/gui/help_dialog.py:119`
- **What help says:** `"Tab 4 — Solute Insertion:\n23. Switch to Solute Insertion tab (requires interface from Tab 2)"`
- **What code does:** `quickice/gui/solute_panel.py:88` — Source dropdown has "Interface" and "Custom Molecule" options. When "Custom Molecule" is selected, Tab 3 must also be completed first.
- **What docs say:** `docs/gui-guide.md:664-671` correctly describes both source options
- **Severity:** Suggestion
- **Impact:** Users may not realize that the "Custom Molecule" source path requires completing Tab 3 first
- **Suggested correction:** Add note: `"Note: If using 'Custom Molecule' source, complete Tab 3 first"`

---

## 12. Ion Panel Tooltip: Missing Madrid2019 Reference (Suggestion)

- **Document:** `quickice/gui/ion_panel.py:129-131`
- **What tooltip says:** `"Insert Na+ and Cl- ions into the liquid water region.\nCalculated from concentration and liquid volume."`
- **What code does:** `quickice/structure_generation/gromacs_ion_export.py:19-20` — Uses Madrid2019 force field parameters (Na⁺ charge = +0.85, Cl⁻ charge = -0.85)
- **What docs say:** `docs/gui-guide.md:793` and `README.md:369-375` both reference Madrid2019 and the TIP4P-ICE compatibility note
- **Severity:** Suggestion
- **Impact:** Users won't know the force field or charge model from the tooltip alone. This is brief by design but could benefit from mentioning "Madrid2019" or "±0.85e charges"
- **Suggested correction:** Add to tooltip: `"\nUses Madrid2019 parameters (±0.85e charges) with TIP4P-ICE water"`

---

## 13. Help Dialog Workflow Step Count Mismatch with gui-guide.md (Minor)

- **Document:** `quickice/gui/help_dialog.py:115-116`
- **What help says:** Step 21 is `"Click Generate to insert custom molecules"` and Step 22 is `"Export custom molecules for GROMACS (Ctrl+M)"`
- **What gui-guide says:** `docs/gui-guide.md:576-578` — Step 9 is `"Click 'Insert Molecule'"` and Step 11 is `"Export for GROMACS (Ctrl+S)"`
- **Discrepancy:** The help dialog uses "Generate" while the gui-guide uses "Insert Molecule". The actual button text in `custom_molecule_panel.py` is `"Insert Molecule"` (set in the generate button). Also, the help dialog says `Ctrl+M` for export, but `gui-guide.md:578` says `Ctrl+S` for unified export.
- **Severity:** Minor
- **Impact:** Terminology mismatch between help dialog and gui-guide; both shortcuts work (Ctrl+S via unified export, Ctrl+M via Export As menu)
- **Suggested correction:** Change help dialog step 21 from "Click Generate" to "Click Insert Molecule"; note that both Ctrl+S and Ctrl+M work for export

---

## 14. Keyboard Shortcut: Ctrl+S for Custom Molecule Export Not Explicitly Documented (Suggestion)

- **Document:** `docs/gui-guide.md:578`
- **What docs say:** `"Export for GROMACS (Ctrl+S)"` for Custom Molecule tab
- **What code does:** `quickice/gui/main_window.py:345-348` — Ctrl+S routes to `_on_export_current_tab()` which dispatches to the active tab's export function. For Tab 3 (Custom), it calls `_on_export_custom_molecule_gromacs()`.
- **Also:** `quickice/gui/main_window.py:401` — Ctrl+M explicitly triggers `_on_export_custom_molecule_gromacs()`
- **Severity:** Suggestion
- **Impact:** Both Ctrl+S and Ctrl+M work for Tab 3 export. The gui-guide's keyboard shortcut table (line 206) documents Ctrl+S as unified, and Ctrl+M is listed separately (line 214). The workflow section uses Ctrl+S which is correct but potentially confusing alongside the explicit Ctrl+M.
- **Note:** This is consistent behavior — not an error, just a documentation clarity opportunity.

---

## 15. Box X Range Discrepancy Between Interface Panel and gui-guide.md (Minor)

- **Document:** `quickice/gui/interface_panel.py:310` vs `docs/gui-guide.md:369`
- **What code says:** `self.box_x_input.setRange(1.0, 100.0)` — minimum 1.0 nm
- **What docs say:** `"Box X/Y/Z | 0.5–100 nm | Simulation box dimensions"`
- **Severity:** Minor
- **Impact:** Documentation says 0.5 nm minimum but GUI enforces 1.0 nm minimum
- **Suggested correction:** Update gui-guide table to `"1.0–100 nm"` or update code minimum to 0.5

---

## 16. Tab Numbering Consistency Verification (Informational)

All three primary documentation sources now agree on the Tab 0-5 numbering:

| Source | Tab 0 | Tab 1 | Tab 2 | Tab 3 | Tab 4 | Tab 5 | Match |
|--------|-------|-------|-------|-------|-------|-------|-------|
| `quickice/gui/constants.py` | ICE | HYDRATE | INTERFACE | CUSTOM | SOLUTE | ION | — |
| `docs/gui-guide.md:29-34` | Ice Gen | Hydrate | Interface | Custom Mol | Solute | Ion | ✅ |
| `quickice/gui/help_dialog.py:88-127` | Ice Gen | Hydrate | Interface | Custom Mol | Solute | Ion | ✅ |
| `README.md:112-183` | Ice Gen | Hydrate | Interface | Custom Mol | Solute | Ion | ✅ |

**Exception:** `quickice/gui/interface_panel.py` tooltips use old numbering (see Section 1).

---

## 17. Keyboard Shortcuts Cross-Check (Informational)

All documented shortcuts match `quickice/gui/main_window.py` QAction registrations:

| Shortcut | gui-guide.md | help_dialog.py | main_window.py | Match |
|----------|-------------|----------------|----------------|-------|
| Enter | ✅ | ✅ | :316 | ✅ |
| Escape | ✅ | ✅ | :327 | ✅ |
| Ctrl+S | ✅ | ✅ | :346 | ✅ |
| Ctrl+Shift+S | ✅ | ✅ | :357 | ✅ |
| Ctrl+Alt+P | ✅ | ✅ | :352 | ✅ |
| Ctrl+D | ✅ | ✅ | :365 | ✅ |
| Ctrl+Alt+S | ✅ | ✅ | :370 | ✅ |
| Ctrl+G | ✅ | ✅ | :381 | ✅ |
| Ctrl+H | ✅ | ✅ | :385 | ✅ |
| Ctrl+I | ✅ | ✅ | :391 | ✅ |
| Ctrl+L | ✅ | ✅ | :395 | ✅ |
| Ctrl+M | ✅ | ✅ | :401 | ✅ |
| Ctrl+J | ✅ | ✅ | :405 | ✅ |

No undocumented shortcuts found. No missing documented shortcuts.

---

## 18. Signal/Slot Connections: Workflow Descriptions Match Code (Informational)

Verified that `quickice/gui/main_window.py:_setup_connections()` signal/slot connections match the workflow described in both `docs/gui-guide.md` and `quickice/gui/help_dialog.py`:

- Tab 0 → Tab 2: `interface_panel.refresh_requested` → `_on_refresh_candidates()` ✅
- Tab 0 → Tab 2: `_on_candidates_ready()` → `interface_panel.update_candidates()` ✅
- Tab 2 → Tab 4: `_on_interface_generation_complete()` → `solute_panel.set_interface_available()` ✅
- Tab 2 → Tab 3: `_on_interface_generation_complete()` → `custom_molecule_panel.set_interface_structure()` ✅
- Tab 3 → Tab 4: `_on_custom_finished()` → `solute_panel.set_custom_molecule_structure()` ✅
- Tab 3 → Tab 5: `_on_custom_finished()` → `ion_panel.set_custom_molecule_structure()` ✅
- Tab 4 → Tab 5: `_on_insert_solutes()` → `ion_panel.set_solute_structure()` ✅
- Tab 2 → Tab 5: `_on_interface_generation_complete()` → `ion_panel.set_interface_available()` ✅

The Custom → Solute → Ion workflow chain is properly connected in code and documented in both gui-guide and help dialog.

---

## 9. Previously Fixed Findings (Delta from 20260612 Scan)

The following issues from `.planning/code_analysis/20260612_documentation_crosscheck.md` have been **resolved**:

| Old # | Description | Status |
|-------|-------------|--------|
| 1.3 | Help dialog omits Ion source dropdown options | ✅ Fixed — `help_dialog.py:127-128` now lists all 3 sources |
| 1.4 | Help dialog omits Solute source dropdown | ✅ Fixed — `help_dialog.py:120` now lists both sources |
| 2.1 | `docs/ranking.md` describes old seed-based diversity | ✅ Fixed — now correctly describes O-O histogram method |
| 2.2 | Molecule count range 4-216 vs 4-100000 | ✅ Fixed — `gui-guide.md:67` now says 4-100,000 |
| 2.6 | Ice IV in phase table (13 vs 12 phases) | ✅ Fixed — table now lists 12 phases without Ice IV |
| 3.1 | IAPWS-95 missing from README | ✅ Fixed — `README.md:334-336` |
| 3.4 | Journaux et al. missing from README | ✅ Fixed — `README.md:338-340` |
| 3.5 | Petrenko & Whitworth missing from README | ✅ Fixed — `README.md:342-343` |
| 3.7 | CODATA 2017 not formally cited | ✅ Fixed — `README.md:345-346` |
| 3.9 | Madrid2019 TIP4P-ICE compatibility not documented | ✅ Fixed — `README.md:373-375` |
| 4.1 | Help dialog missing Validate & Preview | ✅ Fixed — `help_dialog.py:114` |
| 9.1 | "calcution" typo in gui-guide | ✅ Fixed — `gui-guide.md:260` now reads "calculations" |
| 2.5 | Ice Ih T range 0-273K | ✅ Fixed — `README.md:246` now says 0-273.16K |

---

## Summary Table

| # | Category | Document | Section | Severity | Brief Description |
|---|----------|----------|---------|----------|-------------------|
| 1.1 | Tab Number | interface_panel.py:261 | Source tooltip | Misleading | "Tab 1" should be Tab 0 for Ice |
| 1.2 | Tab Number | interface_panel.py:262 | Source tooltip | Misleading | "Tab 3" should be Tab 1 for Hydrate |
| 1.3 | Tab Number | interface_panel.py:267 | HelpIcon | Misleading | "Tab 2" should be Tab 1 |
| 1.4 | Tab Number | interface_panel.py:424 | Candidate tooltip | Misleading | "Tab 1" should be Tab 0 |
| 1.5 | Tab Number | interface_panel.py:436 | Refresh tooltip | Misleading | "Tab 1" should be Tab 0 |
| 2 | Science | solute_panel.py:210 | Solute type tooltip | Misleading | THF is 5-membered ring, not 4 |
| 3 | Feature | custom_molecule_panel.py:256 | Placement mode tooltip | Misleading | Says "no overlap checking" but code implements it |
| 4 | Data | README.md:116 vs :244 | Feature list | Minor | Ice IV in bullet, XV in table |
| 5 | Images | gui-guide.md (7 lines) | Screenshots | Minor | 5 filename mismatches, 2 missing |
| 6 | Algorithm | principles.md:73 | Diversity score | Outdated | Still says "unique seeds" |
| 7 | Data | README.md:257 | Ice X range | Outdated | >40 GPa/>273K vs code >30 GPa (unfixed) |
| 8 | Citation | main_window.py:1953,1955 | _get_citation | Suggestion | Ice V/VII lack citations (unfixed) |
| 9 | Testing | README.md:387 | Example path | Minor | Non-existent test path (unfixed) |
| 10 | Version | gui-guide.md:182 | Interface export | Minor | References "v4.0" (unfixed) |
| 11 | Help | help_dialog.py:119 | Solute prerequisite | Suggestion | Doesn't mention Custom Molecule source requires Tab 3 |
| 12 | Citation | ion_panel.py:129-131 | Insert tooltip | Suggestion | Missing Madrid2019 reference |
| 13 | Terminology | help_dialog.py:115-116 | Button name | Minor | "Generate" vs actual "Insert Molecule" |
| 14 | Shortcut | gui-guide.md:578 | Export shortcut | Suggestion | Ctrl+S vs Ctrl+M clarity |
| 15 | Range | interface_panel.py:310 vs gui-guide.md:369 | Box X min | Minor | Code 1.0 nm vs docs 0.5 nm |

---

*GUI Documentation Cross-Check: 2026-06-15*
*Delta from: .planning/code_analysis/20260612_documentation_crosscheck.md*
