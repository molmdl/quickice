# GUI Documentation Cross-Check Report (Scancode C — Verification + New Issues)

**Analysis Date:** 2026-06-18
**Scope:** GUI-facing documentation: `docs/gui-guide.md`, `quickice/gui/help_dialog.py`, `README.md`, tooltips in `*_panel.py`, `docs/principles.md`, `docs/ranking.md`, citations
**Prior Scan:** `.planning/code_analysis/20260615_documentation_crosscheck_gui.md` (18 findings)
**Focus:** Verify Phase 37.1 fixes (37.1-04, 37.1-13) and identify remaining/new issues

---

## Executive Summary

Of the 18 findings from the 2026-06-15 scan, **12 are now FIXED** and **6 remain unresolved**. Additionally, **4 new issues** were identified, including one introduced by the Phase 37.1-13 fix itself (button label mismatch). The most significant remaining issue is screenshot path mismatches in `docs/gui-guide.md` (5 wrong filenames + 2 missing).

| Category | Count |
|----------|-------|
| Previously fixed (verified) | 12 |
| Previously unfixed (still present) | 6 |
| New findings | 4 |
| **Total active issues** | **10** |

---

## 1. Fix Verification: Phase 37.1-04 (DOC-G1/G2/G3/G4)

### 1.1 DOC-G1: Interface Panel Tab Numbers — ✅ FIXED

**Previously:** 9 tooltip references in `quickice/gui/interface_panel.py` used pre-Phase-34.3 tab numbering (e.g., "Tab 1" for Ice instead of Tab 0).

**Current state:** All tab number references now correctly match `TabIndex` enum values:

| Location | Current Text | Correct? |
|----------|-------------|----------|
| `interface_panel.py:261` | "Tab 0" | ✅ |
| `interface_panel.py:262` | "Tab 1" | ✅ |
| `interface_panel.py:267` | "Tab 1" | ✅ |
| `interface_panel.py:424` | "Tab 0" | ✅ |
| `interface_panel.py:436` | "Tab 0" | ✅ |
| `interface_panel.py:444` | "Tab 0" | ✅ |
| `interface_panel.py:561` | "Tab 0" | ✅ |
| `interface_panel.py:638` | "Tab 0" | ✅ |

Also verified: `ion_panel.py:97-99` correctly references "Tab 2", "Tab 3", "Tab 4". `solute_panel.py:91-92` correctly references "Tab 2", "Tab 3".

### 1.2 DOC-G2: THF Ring Description — ✅ FIXED

**Previously:** `solute_panel.py:210` said "4-membered ring" — incorrect.

**Current state:** `solute_panel.py:209` now says `"5-membered ring (4C + 1O)"` — correct. THF (tetrahydrofuran, C₄H₈O) has 5 ring atoms.

Also verified: `docs/gui-guide.md:631` correctly says "5-membered ring".

### 1.3 DOC-G3: Overlap Checking Tooltip — ✅ FIXED

**Previously:** `custom_molecule_panel.py:256` said "No overlap checking (user responsibility)" — contradicted code.

**Current state:** `custom_molecule_panel.py:256` now says `"Overlap checking with warning dialog (user can override)"` — matches `_check_overlap_with_existing_positions()` at lines 859-887.

Also verified: `docs/gui-guide.md:529-534` correctly describes center-to-center overlap detection with 0.25 nm threshold.

### 1.4 DOC-G4: Diversity Score Description — ✅ FIXED

**Previously:** `docs/principles.md:73` said "Rewards unique seeds" — outdated.

**Current state:** `docs/principles.md:73` now says "Measures structural diversity via O-O distance histogram fingerprints (cosine similarity between candidates)" — matches `scorer.py:318-370`.

Also verified: `docs/principles.md:129` says "O-O distance histogram fingerprints for structural diversity" — correct. `docs/ranking.md:11` says "Rewards structural uniqueness via O-O distance fingerprint" — correct. `scorer.py` module docstring (line 7) says "diversity_score: Rewards structural uniqueness (O-O distance distribution fingerprint)" — correct.

---

## 2. Fix Verification: Phase 37.1-13 (Documentation Accuracy)

### 2.1 README Ice X Range — ✅ FIXED

**Previously:** `README.md:257` said `> 40 GPa | > 273K`.

**Current state:** `README.md:257` now says `> 30 GPa | —` — matches `solid_boundaries.py` (Ice X boundary 30-62 GPa depending on T).

### 2.2 README Ice IV → Ice XV — ✅ FIXED

**Previously:** `README.md:116` listed "12 ice polymorphs — Ih, Ic, II, III, IV, V, VI, VII, VIII, IX, XI, X" — included Ice IV (not detected) instead of Ice XV.

**Current state:** `README.md:116` now says "Ih, Ic, II, III, V, VI, VII, VIII, IX, XV, X" — matches phase table at lines 244-257 and phase_mapping code.

### 2.3 README Madrid2019 DOI — ✅ FIXED

**Previously:** `README.md:371` had DOI `10.1063/1.5121392` (incorrect).

**Current state:** `README.md:371` now has `10.1063/1.5121394` — correct.

### 2.4 gui-guide v4.0 → v4.5 Reference — ✅ FIXED

**Previously:** `docs/gui-guide.md:182` said "QuickIce v4.0 adds interface construction".

**Current state:** `docs/gui-guide.md:182` now says "QuickIce v4.0 added interface construction; v4.5 adds solute and custom molecule insertion" — correct.

### 2.5 gui-guide Box X Range — ✅ FIXED

**Previously:** `docs/gui-guide.md:369` said "0.5–100 nm".

**Current state:** `docs/gui-guide.md:369` now says "1.0–100 nm" — matches `interface_panel.py:310` `setRange(1.0, 100.0)`.

### 2.6 Help Dialog Tab 3 Prerequisite — ✅ FIXED

**Previously:** `help_dialog.py:119` didn't mention Custom Molecule source requires Tab 3.

**Current state:** `help_dialog.py:120` now says "If using Custom Molecule as source, complete Tab 3 (Custom Molecule) first." — matches code.

### 2.7 README Test Path — ✅ FIXED

**Previously:** `README.md:387` had `pytest tests/gui/test_solute_inserter.py` — non-existent path.

**Current state:** `README.md:388` now has `pytest tests/ -k solute -q` — correct.

---

## 3. Previously Identified Issues Still Present

### 3.1 DOC-G5: Screenshot Filename Mismatches — STILL PRESENT

- **Severity:** MEDIUM
- **Category:** OUTDATED
- **Document:** `docs/gui-guide.md` (7 image references)
- **Issue:** 5 screenshot paths don't match actual filenames in `docs/images/`, and 2 screenshots don't exist at all.

| gui-guide.md Line | Referenced Path | Actual File | Status |
|-------------------|----------------|-------------|--------|
| 241 | `images/hydrate-panel.png` | `images/tab2-hydrate-panel.png` | ❌ MISMATCH |
| 344 | `images/slab-interface.png` | `images/tab2-slab-interface.png` | ❌ MISMATCH |
| 352 | `images/pocket-interface.png` | `images/tab2-pocket-interface.png` | ❌ MISMATCH |
| 359 | `images/piece-interface.png` | `images/tab2-piece-interface.png` | ❌ MISMATCH |
| 426 | `images/custom-molecule-panel.png` | — | ❌ MISSING |
| 621 | `images/solute-panel.png` | — | ❌ MISSING |
| 741 | `images/ion-panel.png` | `images/tab4-ion-panel.png` | ❌ MISMATCH |
| 38 | `images/quickice-v4-gui.png` | `images/quickice-v4-gui.png` | ✅ OK |
| 77 | `images/phase-diagram.png` | `images/phase-diagram.png` | ✅ OK |
| 116 | `images/3d-viewer.png` | `images/3d-viewer.png` | ✅ OK |
| 120 | `images/dual-viewport.png` | `images/dual-viewport.png` | ✅ OK |
| 154 | `images/export-menu.png` | `images/export-menu.png` | ✅ OK |

- **Suggested fix:** Update 5 mismatched paths to use actual filenames. Create missing `images/custom-molecule-panel.png` and `images/solute-panel.png` screenshots (both marked "Screenshot update pending for v4.5" at lines 430 and 625).

### 3.2 DOC-G8: Ice V/VII Citations in `_get_citation()` — STILL PRESENT

- **Severity:** LOW
- **Category:** CITATION
- **Document:** `quickice/gui/main_window.py:1954,1956`
- **Issue:** `_get_citation()` returns "No specific citation in GenIce2" for Ice V and Ice VII, but valid citations exist in `docs/principles.md:208` (Lobban et al., 1998, for Ice V).
- **Suggested fix:**
  - Ice V: `"Lobban, C., Finney, J.L. & Kuhs, W.F. (1998). Nature, 391, 26-29. DOI: 10.1038/34622"`
  - Ice VII: `"Hemley, R.J. et al. (1987). Nature, 330, 737-740. DOI: 10.1038/330737a0"`

### 3.3 DOC-G12: Ion Panel Tooltip Missing Madrid2019 Reference — STILL PRESENT

- **Severity:** LOW
- **Category:** CITATION
- **Document:** `quickice/gui/ion_panel.py:129-131`
- **Issue:** Insert button tooltip says "Insert Na+ and Cl- ions into the liquid water region.\nCalculated from concentration and liquid volume." but doesn't mention the Madrid2019 force field or charge model.
- **Suggested fix:** Add `"\nUses Madrid2019 parameters (±0.85e charges) with TIP4P-ICE water"` to tooltip.

### 3.4 DOC-G14: Ctrl+S vs Ctrl+M Clarity for Custom Molecule Export — STILL PRESENT

- **Severity:** LOW
- **Category:** INCONSISTENCY
- **Document:** `docs/gui-guide.md:578`
- **Issue:** gui-guide workflow step 11 says "Export for GROMACS (Ctrl+S)" for Custom Molecule tab, while keyboard shortcut table (line 214) also lists Ctrl+M. Both work — Ctrl+S routes via unified export, Ctrl+M via Export As menu. Not an error, but potentially confusing. The help_dialog step 22 says "Ctrl+M" while gui-guide workflow says "Ctrl+S".
- **Suggested fix:** Add a note in gui-guide that both Ctrl+S and Ctrl+M work for Tab 3 export, or standardize one.

---

## 4. New Findings

### 4.1 NEW-1: Button Label Mismatch — "Insert Molecule" vs "Generate Custom Molecules"

- **Severity:** MEDIUM
- **Category:** INCONSISTENCY
- **Documents:** `quickice/gui/help_dialog.py:115` and `docs/gui-guide.md:576`
- **What docs say:** Help dialog step 21: "Click Insert Molecule to insert custom molecules"; gui-guide step 9: `Click "Insert Molecule"`
- **What code says:** `quickice/gui/custom_molecule_panel.py:112`: `QPushButton("Generate Custom Molecules")` — the button text is "Generate Custom Molecules", NOT "Insert Molecule"
- **Root cause:** Phase 37.1-13 fixed Finding 13 by changing help_dialog from "Click Generate" to "Click Insert Molecule" (stated rationale: "matches actual GUI button text"). However, the actual button text is "Generate Custom Molecules", not "Insert Molecule". The fix was incorrect — the old text "Click Generate" was closer to the actual button text, or it should have been changed to "Click Generate Custom Molecules".
- **Impact:** Users may look for a button labeled "Insert Molecule" that doesn't exist
- **Suggested fix:** Change both help_dialog step 21 and gui-guide step 9 to `Click "Generate Custom Molecules"` to match the actual button text in `custom_molecule_panel.py:112`

### 4.2 NEW-2: Help Dialog Ion Workflow Step Wording Inconsistency

- **Severity:** LOW
- **Category:** INCONSISTENCY
- **Document:** `quickice/gui/help_dialog.py:129`
- **What help says:** Step 30: "Set ion concentration and insert ions into interface"
- **What code says:** The ion panel button text is "Insert Ions" (`ion_panel.py:126`). The help text implies clicking a button called "insert ions into interface" which is not the actual button label. Also, the phrase "into interface" is misleading — ions go into the liquid water region, not into the interface structure itself.
- **Impact:** Minor wording inconsistency; doesn't match button text exactly
- **Suggested fix:** Change to "Set ion concentration and click Insert Ions"

### 4.3 NEW-3: README "12 ice polymorphs" Count Mismatch — Actually 11 in Feature Bullet

- **Severity:** LOW
- **Category:** WRONG
- **Document:** `README.md:116`
- **What docs say:** `**12 ice polymorphs** — Ih, Ic, II, III, V, VI, VII, VIII, IX, XV, X`
- **What code does:** The list has only 11 names (Ih, Ic, II, III, V, VI, VII, VIII, IX, XV, X = 11 entries), but the count says "12"
- **Impact:** Count contradicts the list that follows it
- **Suggested fix:** Either add Ice XI to the feature list (it IS in the phase table at line 255) making it 12, or change the count to 11. The phase detection table at lines 244-257 shows 12 phases (Ih, Ic, II, III, V, VI, VII, VIII, IX, XI, XV, X). The feature bullet should include Ice XI to reach 12.

### 4.4 NEW-4: ranking.md Diversity Score Description Uses "Rewards" — Ambiguous Wording

- **Severity:** LOW
- **Category:** INCONSISTENCY
- **Document:** `docs/ranking.md:11`
- **What docs say:** "Diversity Score - Rewards structural uniqueness via O-O distance fingerprint"
- **What code does:** `scorer.py:318-370` — diversity_score = 1 - mean_similarity. Higher score means more unique, but "rewards" is ambiguous — the score is used INVERTED in the combined score (1 - norm_diversity) so higher diversity actually LOWERS the combined score.
- **Contrast with:** `docs/principles.md:73` says "Measures structural diversity via O-O distance histogram fingerprints" — more precise and neutral wording
- **Suggested fix:** Change ranking.md line 11 from "Rewards structural uniqueness" to "Measures structural uniqueness" to match principles.md and be more precise about the scoring direction

---

## 5. Cross-Check: Tab Numbering Consistency

All primary documentation sources now consistently use Tab 0-5 numbering matching `TabIndex` enum:

| Source | Tab 0 | Tab 1 | Tab 2 | Tab 3 | Tab 4 | Tab 5 | Match |
|--------|-------|-------|-------|-------|-------|-------|-------|
| `quickice/gui/constants.py` | ICE | HYDRATE | INTERFACE | CUSTOM | SOLUTE | ION | — |
| `docs/gui-guide.md:29-34` | Ice Gen | Hydrate | Interface | Custom Mol | Solute | Ion | ✅ |
| `quickice/gui/help_dialog.py:88-131` | Ice Gen | Hydrate | Interface | Custom Mol | Solute | Ion | ✅ |
| `README.md:112-183` | Ice Gen | Hydrate | Interface | Custom Mol | Solute | Ion | ✅ |
| `quickice/gui/interface_panel.py` tooltips | Tab 0 | Tab 1 | — | — | — | — | ✅ Fixed |
| `quickice/gui/ion_panel.py` tooltips | — | — | Tab 2 | Tab 3 | Tab 4 | — | ✅ |
| `quickice/gui/solute_panel.py` tooltips | — | — | Tab 2 | Tab 3 | — | — | ✅ |

---

## 6. Cross-Check: Keyboard Shortcuts

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

## 7. Cross-Check: Signal/Slot Connections

Verified that `quickice/gui/main_window.py:_setup_connections()` signal/slot connections match the workflow described in both `docs/gui-guide.md` and `quickice/gui/help_dialog.py`:

| Data Flow | Signal → Slot | Verified |
|-----------|--------------|----------|
| Tab 0 → Tab 2 (ice candidates) | `interface_panel.refresh_requested` → `_on_refresh_candidates()` | ✅ |
| Tab 0 → Tab 2 (auto-sync) | `_on_candidates_ready()` → `interface_panel.update_candidates()` | ✅ |
| Tab 2 → Tab 4 (interface available) | `_on_interface_generation_complete()` → `solute_panel.set_interface_available()` | ✅ |
| Tab 2 → Tab 3 (interface structure) | `_on_interface_generation_complete()` → `custom_molecule_panel.set_interface_structure()` | ✅ |
| Tab 2 → Tab 5 (liquid volume) | `_on_interface_generation_complete()` → `ion_panel.set_liquid_volume()` | ✅ |
| Tab 3 → Tab 4 (custom molecule source) | `_on_custom_finished()` → `solute_panel.set_custom_molecule_structure()` | ✅ |
| Tab 3 → Tab 5 (custom molecule source) | `_on_custom_finished()` → `ion_panel.set_custom_molecule_structure()` | ✅ |
| Tab 4 → Tab 5 (solute source) | `_on_insert_solutes()` → `ion_panel.set_solute_structure()` | ✅ |

The Custom → Solute → Ion workflow chain is properly connected and documented.

---

## 8. Cross-Check: Ranking Documentation vs Code

`docs/ranking.md` correctly describes the current `scorer.py` implementation:

| Component | ranking.md Description | scorer.py Implementation | Match |
|-----------|----------------------|-------------------------|-------|
| Energy score | O-O distance deviation from ideal (0.276 nm) | `energy_score()` lines 139-191 | ✅ |
| Density score | Deviation from expected phase density | `density_score()` lines 194-248 | ✅ |
| Diversity score | O-O histogram fingerprint + cosine similarity | `diversity_score()` lines 318-370, `_compute_oo_histogram()` lines 251-294, `_histogram_cosine_similarity()` lines 297-315 | ✅ |
| Normalization | Min-max scaling to 0-1 | `normalize_scores()` lines 373-411 | ✅ |
| Combination | `w_energy × norm_energy + w_density × norm_density + w_diversity × (1 - norm_diversity)` | `rank_candidates()` lines 473-477 | ✅ |
| Weights | Default: equal (1:1:1) | `weights = {'energy': 1.0, 'density': 1.0, 'diversity': 1.0}` at line 451 | ✅ |

**Minor wording note:** ranking.md line 11 says "Rewards structural uniqueness" while principles.md line 73 says "Measures structural diversity" — slightly different phrasing (see NEW-4).

---

## 9. Cross-Check: Custom Molecule → Solute Workflow Documentation

Both `docs/gui-guide.md:549-567` and `quickice/gui/help_dialog.py:109-127` document the Custom → Solute → Ion workflow chain. Verified against code:

| Workflow Step | gui-guide | help_dialog | Code | Match |
|--------------|-----------|-------------|------|-------|
| Tab 3 requires interface from Tab 2 | ✅ (line 569) | ✅ (line 110) | `custom_molecule_panel.set_interface_structure()` | ✅ |
| Tab 4 source: Interface or Custom Molecule | ✅ (line 664-671) | ✅ (line 121) | `solute_panel.source_combo.addItems(["Interface", "Custom Molecule"])` | ✅ |
| Tab 5 source: Interface, Custom, Solute | ✅ (line 729-735) | ✅ (line 128) | `ion_panel.source_combo.addItems(["Interface", "Custom Molecule", "Solute"])` | ✅ |
| Tab 3 export includes full system (ice+water+custom) | ✅ (line 564) | Implicit | `MainWindow._on_custom_finished()` passes result to downstream | ✅ |

---

## Summary Table

| # | ID | Category | Document | Severity | Brief Description | Status |
|---|----|----------|----------|----------|-------------------|--------|
| 1 | DOC-G1 | Tab Number | interface_panel.py tooltips | — | Tab numbers wrong | ✅ Fixed (37.1-04) |
| 2 | DOC-G2 | Science | solute_panel.py tooltip | — | THF "4-membered" → "5-membered" | ✅ Fixed (37.1-04) |
| 3 | DOC-G3 | Feature | custom_molecule_panel.py tooltip | — | "no overlap" → "overlap checking" | ✅ Fixed (37.1-04) |
| 4 | DOC-G4 | Algorithm | principles.md diversity score | — | "unique seeds" → "O-O histogram" | ✅ Fixed (37.1-04) |
| 5 | DOC-G5 | Images | gui-guide.md screenshot paths | MEDIUM | 5 mismatched + 2 missing | ❌ Still present |
| 6 | DOC-G7 | Data | README.md Ice X range | — | >40 GPa/>273K | ✅ Fixed (37.1-13) |
| 7 | DOC-G8 | Citation | main_window.py:1954,1956 | LOW | Ice V/VII no citation | ❌ Still present |
| 8 | DOC-G9 | Testing | README.md test path | — | Non-existent path | ✅ Fixed (37.1-13) |
| 9 | DOC-G10 | Version | gui-guide.md:182 | — | "v4.0 adds" → "v4.0 added; v4.5 adds" | ✅ Fixed (37.1-13) |
| 10 | DOC-G11 | Help | help_dialog.py Tab 3 prereq | — | Added Custom Molecule source note | ✅ Fixed (37.1-13) |
| 11 | DOC-G12 | Citation | ion_panel.py:129-131 | LOW | Missing Madrid2019 reference | ❌ Still present |
| 12 | DOC-G13 | Terminology | help_dialog.py:115 | — | "Generate" → "Insert Molecule" | ⚠️ Fix introduced new issue (see NEW-1) |
| 13 | DOC-G14 | Shortcut | gui-guide.md:578 | LOW | Ctrl+S vs Ctrl+M clarity | ❌ Still present |
| 14 | DOC-G15 | Range | interface_panel.py vs gui-guide.md | — | Box X 0.5 vs 1.0 nm | ✅ Fixed (37.1-13) |
| 15 | — | Data | README.md:116 | — | Ice IV → Ice XV | ✅ Fixed (37.1-13) |
| 16 | NEW-1 | Inconsistency | help_dialog.py:115, gui-guide.md:576 | MEDIUM | Button "Generate Custom Molecules" not "Insert Molecule" | 🆕 New (introduced by 37.1-13 fix) |
| 17 | NEW-2 | Inconsistency | help_dialog.py:129 | LOW | Ion step doesn't match button text | 🆕 New |
| 18 | NEW-3 | Wrong | README.md:116 | LOW | Says "12" but lists 11 polymorphs | 🆕 New |
| 19 | NEW-4 | Inconsistency | ranking.md:11 | LOW | "Rewards" vs "Measures" (vs principles.md) | 🆕 New |

---

*GUI Documentation Cross-Check: 2026-06-18*
*Delta from: .planning/code_analysis/20260615_documentation_crosscheck_gui.md*
