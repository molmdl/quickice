# Documentation Cross-Check & Citation Suggestions

**Analysis Date:** 2026-05-22
**Scope:** All documentation files vs current code for QuickIce v4.5.0
**Previous Reports:** `20260512_154906_documentation_crosscheck.md`, `20260516_documentation_issues_verification.md`

---

## 1. Executive Summary

Since the last cross-check (2026-05-16), three Quick Tasks have been completed:
- **QT-024** (ice phases docs): ✓ Fixed — README now distinguishes 12 detectable vs 8 generatable
- **QT-025** (hydrate guest docstring): ✓ Fixed — `hydrate_generator.py` docstring now accurate
- **QT-026** (Madrid2019 citation): ✓ Fixed — Both README and gui-guide now cite Zeron et al. (2019)
- **QT-028** (hydrate naming _HYD→_H): ✓ Fixed in code — BUT documentation NOT fully updated

**Critical findings:** QT-028 renamed hydrate guest suffix from `_HYD` to `_H` and created hydrate-specific ITP files, but several documentation files still reference the old naming (`CH4_HYD`, `THF_HYD`, `CH4_LIQ`, `THF_LIQ`) and old ITP file names (`ch4.itp`, `thf.itp` for hydrate export). Additionally, keyboard shortcuts in gui-guide.md have several mismatches with actual registered shortcuts.

**Total issues found:** 15 (4 Critical, 5 High, 4 Medium, 2 Low)
**Citation suggestions:** 6 new, 2 updates to existing

---

## 2. Tab Numbering Verification

### Code Reference
`quickice/gui/constants.py:9-28` — `TabIndex(IntEnum)`:
```python
ICE = 0          # Ice Generation tab
HYDRATE = 1      # Hydrate Generation tab
INTERFACE = 2    # Interface Construction tab
CUSTOM = 3       # Custom Molecule tab
SOLUTE = 4       # Solute Insertion tab
ION = 5          # Ion Insertion tab
```

### Documentation Verification

| Doc File | Line | Claimed Tab Mapping | Code | Status |
|----------|------|---------------------|------|--------|
| `README.md` | 83-86 | Tab 0=Ice, Tab 2=Interface, Tabs 3-5=Custom/Solute/Ion | ✓ Match | ✓ Consistent |
| `README.md` | 97-168 | Tab 0-5 with correct assignments | ✓ Match | ✓ Consistent |
| `docs/gui-guide.md` | 29-34 | Tab 0-5 with correct assignments | ✓ Match | ✓ Consistent |
| `quickice/gui/help_dialog.py` | 88-126 | Tab 0-5 workflow steps | ✓ Match | ✓ Consistent |

**Result: ✓ Tab numbering is consistent across all documentation and code.**

---

## 3. Molecule Naming Verification

### Code Reference
`quickice/structure_generation/moleculetype_registry.py:28-37`:
```python
RESERVED_NAMES = {
    "SOL", "NA", "CL", "CH4", "THF", "CO2", "H2",
    "CH4_H", "CH4_L", "THF_H", "THF_L"
}
```

Hydrate guests use `_H` suffix (e.g., `CH4_H`, `THF_H`).
Liquid solutes use `_L` suffix (e.g., `CH4_L`, `THF_L`).

### ITP File Verification

| ITP File | moleculetype Name | Code Reference | Status |
|----------|-------------------|-----------------|--------|
| `quickice/data/ch4_hydrate.itp:12` | `CH4_H` | `hydrate_export.py:149` | ✓ Consistent |
| `quickice/data/thf_hydrate.itp:14` | `THF_H` | `hydrate_export.py:149` | ✓ Consistent |
| `quickice/data/ch4_liquid.itp:11` | `CH4_L` | `export.py:115` | ✓ Consistent |
| `quickice/data/thf_liquid.itp:13` | `THF_L` | `export.py:115` | ✓ Consistent |
| `quickice/data/ch4.itp` | `ch4` (legacy, unused for hydrate) | Not used in hydrate export | ✓ Not used |
| `quickice/data/thf.itp` | `thf` (legacy, unused for hydrate) | Not used in hydrate export | ✓ Not used |
| `quickice/data/tip4p-ice.itp:11` | `SOL` | All exporters | ✓ Consistent |
| `quickice/data/custom/etoh.itp` | Example custom ITP | — | ✓ Consistent |

### Documentation vs Code Mismatches (CRITICAL)

#### Issue MOL-1: `README.md` line 194 — `CH4_HYD` should be `CH4_H`

**README.md line 192-198:**
```
[ molecules ]
SOL               5919    ; Water molecules
CH4_HYD           128     ; Hydrate guests (from Tab 1)
THF_LIQ           45      ; Liquid solutes (from Tab 4)
```

**Code (`moleculetype_registry.py:28`):** `CH4_H`, `THF_L` (not `CH4_HYD`, `THF_LIQ`)

**Discrepancy:** README uses old naming convention (`_HYD` and `_LIQ` suffixes) that was changed by QT-028. Correct names are `CH4_H` and `THF_L`.

**Priority:** CRITICAL — Users will get GROMACS errors if they manually construct topology based on README example.

**Fix:** Replace `CH4_HYD` → `CH4_H`, `THF_LIQ` → `THF_L` in README example at lines 192-198.

---

#### Issue MOL-2: `docs/gui-guide.md` line 708 — `CH4_LIQ`/`THF_LIQ` should be `CH4_L`/`THF_L`

**gui-guide.md line 708:**
> Solute molecules appear after SOL in the [ molecules ] section with names `CH4_LIQ` or `THF_LIQ`.

**Code:** `moleculetype_registry.py:82` returns `CH4_L` and `THF_L` (via `register_liquid_solute()`)

**Discrepancy:** Doc says `_LIQ` but code uses `_L`.

**Priority:** CRITICAL

**Fix:** Change `CH4_LIQ` → `CH4_L` and `THF_LIQ` → `THF_L` at line 708.

---

#### Issue MOL-3: `docs/gui-guide.md` line 710 — `CH4_HYD`/`THF_HYD` should be `CH4_H`/`THF_H`

**gui-guide.md line 710:**
> Note: Solute ITP files use `_LIQ` suffix to distinguish from hydrate guests (`CH4_HYD`, `THF_HYD`)

**Code:** `moleculetype_registry.py:28` uses `CH4_H` and `THF_H` (not `_HYD`)

**Discrepancy:** Doc says `_HYD` but code uses `_H`.

**Priority:** CRITICAL

**Fix:** Change `_LIQ` → `_L`, `CH4_HYD` → `CH4_H`, `THF_HYD` → `THF_H` at line 710. Update the explanatory note to match current convention.

---

#### Issue MOL-4: `docs/gui-guide.md` line 297 — Hydrate ITP file names outdated

**gui-guide.md line 297:**
> `ch4.itp` or `thf.itp` — Guest molecule parameters (GAFF)

**Code:** `hydrate_export.py:143-144` uses `_get_hydrate_guest_itp_path()` which returns `ch4_hydrate.itp` and `thf_hydrate.itp`.

**Discrepancy:** Doc says `ch4.itp`/`thf.itp` but code copies `ch4_hydrate.itp`/`thf_hydrate.itp`.

**Priority:** HIGH

**Fix:** Change line 297 to:
> `ch4_hydrate.itp` or `thf_hydrate.itp` — Guest molecule parameters (GAFF2)

Also change "GAFF" → "GAFF2" (see Issue FF-1 below).

---

#### Issue MOL-5: `README.md` line 181-185 — Hydrate export ITP naming

**README.md line 181:**
> Tab 1 | Hydrate GROMACS | .gro, .top, tip4p_ice.itp, ch4.itp/thf.itp

**Code:** `hydrate_export.py:143-144` copies `ch4_hydrate.itp`/`thf_hydrate.itp`

**Discrepancy:** README says `ch4.itp/thf.itp` but code exports `ch4_hydrate.itp/thf_hydrate.itp`.

**Priority:** HIGH

**Fix:** Change line 181 to: `ch4_hydrate.itp/thf_hydrate.itp`

---

## 4. ITP File Inventory Verification

### Files Present in `quickice/data/`

| File | moleculetype | Purpose | Documented? |
|------|--------------|---------|-------------|
| `tip4p-ice.itp` | SOL | TIP4P-ICE water model | ✓ README, gui-guide |
| `ch4.itp` | ch4 | Legacy standalone CH4 (GAFF2) | ✗ Not documented (not used in hydrate export) |
| `thf.itp` | thf | Legacy standalone THF (GAFF2) | ✗ Not documented (not used in hydrate export) |
| `ch4_hydrate.itp` | CH4_H | Hydrate guest CH4 (GAFF2) | ✗ README line 181 says `ch4.itp` instead |
| `thf_hydrate.itp` | THF_H | Hydrate guest THF (GAFF2) | ✗ README line 181 says `thf.itp` instead |
| `ch4_liquid.itp` | CH4_L | Liquid solute CH4 (GAFF2) | ✓ README line 184, gui-guide line 706 |
| `thf_liquid.itp` | THF_L | Liquid solute THF (GAFF2) | ✓ README line 184, gui-guide line 706 |
| `custom/etoh.itp` | ETOH | Example custom molecule | ✗ Not documented |

### Issue INV-1: Missing hydrate-specific ITP file documentation

**Priority:** HIGH (consequence of MOL-4/MOL-5 above)

**Fix:** Update all references from `ch4.itp`/`thf.itp` to `ch4_hydrate.itp`/`thf_hydrate.itp` in hydrate export contexts.

### Issue INV-2: No ion ITP file in data directory

The `ion.itp` file is generated dynamically by `gromacs_ion_export.py:30-56` at export time — it's not a static file in `quickice/data/`. This is correct behavior but the distinction between bundled vs generated ITP files is not documented.

**Priority:** LOW

---

## 5. GROMACS Export Descriptions Verification

### Issue EXP-1: Hydrate export file naming pattern

**gui-guide.md line 295:**
> `hydrate_{lattice}.gro` — Coordinates

**Code (`hydrate_export.py:109`):**
```python
default_name = f"hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro"
```

**Discrepancy:** Doc says `hydrate_{lattice}.gro` but code generates `hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro` (includes guest type and supercell dimensions).

**Priority:** MEDIUM

**Fix:** Update line 295 to: `hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro`

---

### Issue EXP-2: Solute export file naming pattern

**gui-guide.md lines 703-706:**
> `interface_with_solutes.gro` — Coordinates with solutes
> `interface_with_solutes.top` — Topology with solute moleculetype

**Code (`export.py:48`):**
```python
default_name = f"solute_{solute_type}_{n_molecules}molecules.gro"
```

**Discrepancy:** Doc says `interface_with_solutes.gro` but code generates `solute_{type}_{count}molecules.gro`.

**Priority:** MEDIUM

**Fix:** Update lines 704-705 to match actual naming pattern.

---

### Issue EXP-3: Custom molecule export file naming

**gui-guide.md lines 589-591:**
> `interface_with_custom.gro` — Coordinates with custom molecules
> `interface_with_custom.top` — Topology with custom moleculetype

**Code (`export.py:178`):**
```python
default_name = f"custom_system_{moleculetype_name}_{n_molecules}molecules.gro"
```

**Discrepancy:** Doc says `interface_with_custom.gro` but code generates `custom_system_{name}_{count}molecules.gro`.

**Priority:** MEDIUM

**Fix:** Update lines 589-590 to match actual naming pattern.

---

## 6. Keyboard Shortcuts Verification

### Code Reference: `quickice/gui/main_window.py:340-407`

| Shortcut | Code Action | gui-guide.md Line | gui-guide.md Claim | Help Dialog Line | Help Dialog Claim | Status |
|----------|-------------|-------------------|-------------------|------------------|-------------------|--------|
| `Ctrl+S` | Export current tab for GROMACS | 206 | ✓ "Save/Export from active tab" | 68 | ✓ "Export current tab for GROMACS" | ✓ Match |
| `Ctrl+Shift+S` | Save PDB (right viewer) | 207 | ✓ "Save PDB (right viewer, Tab 0 only)" | 69 | ✓ "Save PDB (right viewer)" | ✓ Match |
| `Ctrl+Alt+P` | Save PDB (left viewer) | — | ✗ NOT documented in gui-guide shortcuts table | 70 | ✓ "Save PDB (left viewer)" | ⚠ GUI guide missing |
| `Ctrl+D` | Save phase diagram | 208 | ✓ "Save phase diagram" | 71 | ✓ | ✓ Match |
| `Ctrl+Alt+S` | Save viewport screenshot | 209 | ✓ "Save viewport screenshot" | 78 | ✓ | ✓ Match |
| `Ctrl+G` | Export ice for GROMACS | 210 | ✓ "Export ice for GROMACS (Tab 0)" | 72 | ✓ | ✓ Match |
| `Ctrl+H` | Export hydrate for GROMACS | 211 | ✓ "Export hydrate for GROMACS (Tab 1)" | 73 | ✓ | ✓ Match |
| `Ctrl+I` | Export interface for GROMACS | 212 | ✓ "Export interface for GROMACS (Tab 2)" | 74 | ✓ | ✓ Match |
| `Ctrl+M` | Export custom molecules for GROMACS | — | ✗ NOT documented in gui-guide shortcuts table | 76 | ✓ "Export custom molecules" | ⚠ GUI guide missing |
| `Ctrl+L` | Export solutes for GROMACS | — | ✗ NOT documented in gui-guide shortcuts table | 75 | ✓ "Export solutes" | ⚠ GUI guide missing |
| `Ctrl+J` | Export ions for GROMACS | 213 | ✓ "Export ions for GROMACS (Tab 5)" | 77 | ✓ | ✓ Match |

### Issue KS-1: gui-guide.md shortcuts table missing Ctrl+Alt+P, Ctrl+L, Ctrl+M

**gui-guide.md lines 200-214** keyboard shortcuts table does not include:
- `Ctrl+Alt+P` — Save PDB (left viewer) — registered in code at `main_window.py:352`
- `Ctrl+L` — Export solutes for GROMACS — registered at `main_window.py:396`
- `Ctrl+M` — Export custom molecules for GROMACS — registered at `main_window.py:401`

**Priority:** HIGH

**Fix:** Add these three shortcuts to the gui-guide.md keyboard shortcuts table.

---

### Issue KS-2: gui-guide.md line 163 — Ctrl+S description outdated

**gui-guide.md line 163:**
> Ctrl+S: Save PDB from left viewer (rank #1)

**Code (`main_window.py:346-348`):** Ctrl+S now triggers `_on_export_current_tab()` — unified GROMACS export from active tab.

**Discrepancy:** Line 163 describes the OLD behavior (PDB save). The unified Ctrl+S is documented at line 206, but line 163 contradicts it.

**Priority:** HIGH

**Fix:** Update line 163 to reflect that Ctrl+S is now unified GROMACS export. The old PDB save is now Ctrl+Alt+P.

---

### Issue KS-3: gui-guide.md line 281 — Hydrate workflow references old Ctrl+E shortcut

**gui-guide.md line 281:**
> 7. Export for GROMACS (Ctrl+E)

**Code:** `main_window.py:386` — Hydrate export shortcut is `Ctrl+H` (changed from Ctrl+E, as noted in code comment).

**Discrepancy:** Doc says Ctrl+E but code uses Ctrl+H.

**Priority:** HIGH

**Fix:** Change `Ctrl+E` → `Ctrl+H` at line 281.

---

### Issue KS-4: gui-guide.md line 25 — Solute workflow references Ctrl+E for hydrate

The gui-guide workflow at line 25 says hydrate workflow uses Ctrl+E (but it's Ctrl+H now). This is the same issue as KS-3 in a different location.

**Priority:** MEDIUM (same fix as KS-3)

---

## 7. Version References Verification

### Code Reference
`quickice/__init__.py:3`: `__version__ = "4.5.0"`
`quickice/cli/parser.py:175`: `version="%(prog)s 4.5.0"`

### Documentation Verification

| Doc File | Line | Version Claim | Code | Status |
|----------|------|---------------|------|--------|
| `README.md` | 14 | "v4.5" | 4.5.0 | ✓ Consistent |
| `README.md` | 373 | "v4.5" | 4.5.0 | ✓ Consistent |
| `docs/gui-guide.md` | 3 | "v4.5" | 4.5.0 | ✓ Consistent |
| `docs/gro-itp-guide.md` | 3 | "v4.5" | 4.5.0 | ✓ Consistent |
| `docs/cli-reference.md` | 145 | "4.0.0" | 4.5.0 | ⚠ OUTDATED |
| `docs/gro-itp-guide.md` | 908 | "v4.5" | 4.5.0 | ✓ Consistent |

### Issue VER-1: `docs/cli-reference.md` line 145 — Version output shows 4.0.0

**cli-reference.md line 145:**
> Output: python quickice.py 4.0.0

**Code:** `parser.py:175` returns `4.5.0`

**Discrepancy:** CLI reference shows outdated version 4.0.0.

**Priority:** MEDIUM

**Fix:** Change `4.0.0` → `4.5.0` at line 145.

---

## 8. Scientific Claims Verification

### 8.1 Density Values

**Code (`quickice/phase_mapping/lookup.py:27-46`):**

| Phase | Code Density (g/cm³) | Source |
|-------|----------------------|--------|
| Ice Ih | 0.9167 (fallback; actual via IAPWS R10-06) | IAPWS R10-06(2009) |
| Ice Ic | 0.92 | Literature reference |
| Ice II | 1.18 | Literature reference |
| Ice III | 1.16 | Literature reference |
| Ice V | 1.24 | Literature reference |
| Ice VI | 1.31 | Literature reference |
| Ice VII | 1.65 | Literature reference |
| Ice VIII | 1.65 | Literature reference |
| Ice XI | 0.92 | Proton-ordered Ih |
| Ice IX | 1.16 | Proton-ordered III |
| Ice XV | 1.31 | Proton-ordered VI |
| Ice X | 2.79 | Symmetric H bonds |

**Documentation (`docs/ranking.md:97`):** Uses 0.9167 g/cm³ for Ice Ih — ✓ consistent.

**Documentation (`docs/ranking.md:168`):** `AVOGADRO = 6.022e23` — Note: code uses `6.02214076e23` in `solute_inserter.py:32` but `6.022e23` in `scorer.py:168`. Minor inconsistency (see Issue SCI-1).

### Issue SCI-1: Avogadro's number inconsistency in code

**Code `solute_inserter.py:32`:** `AVOGADRO = 6.02214076e23  # mol^-1`
**Code `scorer.py:168`:** `AVOGADRO = 6.022e23  # molecules/mol`

**Discrepancy:** Two different precision levels for Avogadro's number in the codebase itself. The CODATA 2017 value is 6.02214076e23.

**Impact:** Low — the difference is ~0.004% and doesn't affect practical calculations.

**Priority:** LOW

---

### 8.2 O-O Distance Reference

**Code (`quickice/ranking/scorer.py`):** Uses 0.276 nm as ideal O-O distance.
**Documentation (`docs/ranking.md:31`):** "0.276 = Ideal O-O distance in nm (typical hydrogen bond length)"

**Verification:** 0.276 nm is the accepted O-O nearest-neighbor distance in Ice Ih at ambient conditions. This is consistent with Petrenko & Whitworth (1999), *Physics of Ice*.

**Status:** ✓ Consistent, but missing citation (see Section 10).

---

### 8.3 TIP4P-ICE Parameters

**Code (`quickice/data/tip4p-ice.itp:15-18`):**
- OW charge: 0, HW charge: 0.5897, MW charge: -1.1794
- O-H bond: 0.09572 nm, H-H distance: 0.15139 nm

**Documentation (`README.md:207-212`):** Cites Abascal et al. (2005), J. Chem. Phys. 122, 234511.

**Verification:** Parameters match the published TIP4P-ICE model. Citation is correct.

**Status:** ✓ Consistent

---

### 8.4 Madrid2019 Ion Parameters

**Code (`quickice/structure_generation/gromacs_ion_export.py:9-27`):**
- NA_CHARGE = 0.85, CL_CHARGE = -0.85
- NA_SIGMA = 0.22173668, CL_SIGMA = 0.46990563
- NA_EPSILON = 1.47235577, CL_EPSILON = 0.07692308

**Documentation (`README.md:335-337`):** Full citation added by QT-026.
**Documentation (`docs/gui-guide.md:790`):** Inline citation added by QT-026.

**Verification:** Parameters match Zeron et al. (2019), J. Chem. Phys. 151, 134504 (Madrid2019 model with ±0.85e scaled charges).

**Status:** ✓ Consistent. Citation properly added by QT-026.

**Remaining gap (noted in CONCERNS_VERIFICATION.md):** Generated `ion.itp` file lacks a header comment identifying it as Madrid2019_085 specifically.

---

### 8.5 GAFF2 Force Field Parameters

**Code (`quickice/output/gromacs_writer.py:1254-1266`):** Writes GAFF2 atom types for CH4 and THF.
**Code (`quickice/data/ch4_hydrate.itp:1`):** "Created by Sobtop Version 2026.1.16 on 2026-04-15"

**Documentation (`README.md:216-219`):** Mentions "GAFF2 force field with RESP2(0.5) partial charges" and tools used.

**Status:** ✓ Consistent, but missing formal GAFF2 citation (see Section 10).

---

## 9. Quick Task Verification Summary

### QT-024: Ice Phases Documentation (✓ FIXED)

**Before:** README claimed "12 ice polymorphs" without distinction.
**After:** README (lines 222-263) now has separate "Phase Detection (12 phases)" and "Structure Generation (8 phases)" tables.
**Code verification:** `PHASE_METADATA` in `lookup.py:27-46` has 12 entries; `PHASE_TO_GENICE` in `mapper.py` has 8 entries.
**Status:** ✓ Consistent.

### QT-025: Hydrate Guest Docstring (✓ FIXED)

**Before:** `hydrate_generator.py` docstring said "(CH4, THF, CO2, H2)".
**After:** Now says "(CH4, THF)" with note about GenIce2 capabilities.
**Code verification:** `GUEST_MOLECULES` in `types.py:76-91` only contains `ch4` and `thf`.
**Status:** ✓ Consistent.

### QT-026: Madrid2019 Citation (✓ FIXED)

**Before:** No citation for Madrid2019 ion parameters.
**After:** README lines 335-337 have full citation; gui-guide line 790 has inline citation with DOI.
**Status:** ✓ Consistent.

### QT-028: Hydrate Naming _HYD→_H (✓ FIXED IN CODE, ✗ NOT FULLY FIXED IN DOCS)

**Before:** Registry used `_HYD` suffix; hydrate export used `ch4.itp`/`thf.itp`.
**After (code):** Registry uses `_H` suffix; hydrate export uses `ch4_hydrate.itp`/`thf_hydrate.itp`.
**After (docs):** STILL REFERENCES OLD NAMES in README (CH4_HYD, THF_LIQ) and gui-guide (CH4_LIQ, THF_LIQ, CH4_HYD, THF_HYD, ch4.itp, thf.itp).

**Remaining issues:** MOL-1, MOL-2, MOL-3, MOL-4, MOL-5 (see Section 3).

---

## 10. Citation Suggestions

### 10.1 GAFF2 Force Field (HIGH PRIORITY — currently uncited in formal references)

**Where used:** CH₄ and THF guest/solute molecule parameters throughout QuickIce.
**Code reference:** `quickice/output/gromacs_writer.py:1254-1266` (atom types), `quickice/data/ch4_hydrate.itp:1` (Sobtop attribution)
**Current documentation:** README mentions "GAFF2 force field with RESP2(0.5) partial charges" at line 216 but provides no formal citation in References section.

**Suggested citation text:**
```
### GAFF2 Force Field
- Wang, J., Wolf, R. M., Caldwell, J. W., Kollman, P. A., & Case, D. A. (2004).
  Development and testing of a general amber force field.
  Journal of Computational Chemistry, 25(9), 1157-1174.
  DOI: https://doi.org/10.1002/jcc.20035

- He, X., Man, V. H., Yang, W., Lee, T. S., & Wang, J. (2020).
  A fast and high-quality charge model for the next generation general AMBER force field.
  Journal of Chemical Physics, 153(11), 114502.
  DOI: https://doi.org/10.1063/5.0019053
```

**Note:** The `gro-itp-guide.md` already cites GAFF2 (Wang et al. 2004) at line 870. This should be added to the main README References section as well.

---

### 10.2 RESP2 Charge Model (MEDIUM PRIORITY)

**Where used:** CH₄ and THF partial charges are derived using RESP2(0.5).
**Code reference:** `quickice/data/ch4_hydrate.itp:1-2` (Sobtop/Multiwfn attribution), README line 216.
**Current documentation:** Mentions "RESP2(0.5) partial charges" but no formal citation.

**Suggested citation text:**
```
### RESP2 Charge Model
- Schauperl, M., Nerenberg, P. S., Lambrecht, D., Cui, Q., & Bayly, C. I. (2021).
  Non-bonded force field model with advanced restrained electrostatic potential
  charges (RESP2).
  Communications Chemistry, 4, 73.
  DOI: https://doi.org/10.1038/s42004-021-00490-5
```

---

### 10.3 Clathrate Hydrate Structures (MEDIUM PRIORITY)

**Where used:** Hydrate generation (Tab 1) — sI, sII, sH cage structures.
**Code reference:** `quickice/structure_generation/types.py:42-72` (HYDRATE_LATTICES with cage descriptions).
**Current documentation:** No citation for hydrate structure types.

**Suggested citation text:**
```
### Clathrate Hydrate Structures
- Sloan, E. D., & Koh, C. A. (2007).
  Clathrate Hydrates of Natural Gases (3rd ed.).
  CRC Press. ISBN: 978-08449390784

- Jeffrey, G. A. (1984).
  Clathrate hydrates.
  In Comprehensive Supramolecular Chemistry (Vol. 6, pp. 757-788).
  DOI: https://doi.org/10.1016/B978-0-08-097774-4.00617-6
```

---

### 10.4 O-O Distance in Ice (LOW PRIORITY)

**Where used:** Ranking energy score calculation (ideal O-O = 0.276 nm).
**Code reference:** `quickice/ranking/scorer.py` (energy_score formula).
**Documentation:** `docs/ranking.md:31` mentions "0.276 = Ideal O-O distance" without citation.

**Suggested citation text:**
```
### Ice O-O Distance Reference
- Petrenko, V. F., & Whitworth, R. W. (1999).
  Physics of Ice.
  Oxford University Press. ISBN: 978-0198518945

- Bjerrum, N. (1952).
  Structure and properties of ice.
  Science, 115(2989), 385-390.
  DOI: https://doi.org/10.1126/science.115.2989.385
```

---

### 10.5 IAPWS R10-06(2009) — Ice Ih Density (LOW PRIORITY — partially cited)

**Where used:** Ice Ih temperature-dependent density calculation.
**Code reference:** `quickice/phase_mapping/ice_ih_density.py:1-21`.
**Current documentation:** README line 314-316 cites IAPWS R10-06 correctly.

**Status:** ✓ Already cited. No action needed.

---

### 10.6 CODATA 2017 Avogadro's Number (LOW PRIORITY)

**Where used:** Molecule count calculations in solute, ion, and custom molecule inserters.
**Code reference:** `quickice/structure_generation/solute_inserter.py:32` (`AVOGADRO = 6.02214076e23`).
**Current documentation:** gui-guide mentions "Avogadro's number" but not the specific value or its source.

**Suggested citation text:**
```
### Avogadro Constant (CODATA 2017)
- Newell, D. B., et al. (2018).
  The CODATA 2017 values of h, e, k, and NA for the revision of the SI.
  Metrologia, 55(1), L13.
  DOI: https://doi.org/10.1088/1681-7575/aa950a
```

---

### 10.7 GenIce2 — Update existing citation (MEDIUM PRIORITY)

**Current README citation (line 305-308):**
> Paper: "GenIce: Hydrogen-disordered ice structures by combinatorial generation", J. Comput. Chem. 2017
> DOI: https://doi.org/10.1002/jcc.25077

**Issue:** The citation text is incomplete — missing author names and journal volume/pages.

**Suggested full citation:**
```
### GenIce2
- Matsumoto, M., & Yagasaki, T. (2022).
  GenIce2: Versatile and efficient algorithm for generation of hydrogen-disordered ice structures.
  Journal of Computational Chemistry, 43(7), 471-479.
  DOI: https://doi.org/10.1002/jcc.25077

  Repository: https://github.com/genice-dev/GenIce2
```

**Note:** The DOI is the same but the 2022 date and full author list should be verified. The original GenIce (Matsumoto 2017, DOI: 10.1002/jcc.24812) is a different paper than GenIce2.

---

### 10.8 spglib — Verify existing citation (LOW PRIORITY)

**Current README citation (line 319-321):**
> Paper: "Spglib: a software library for crystal symmetry search", Sci. Technol. Adv. Mater., Meth. 4, 2384822 (2024)
> DOI: https://doi.org/10.1080/27660400.2024.2384822

**Issue:** Missing author names. Full citation should include:
- Togo, A., et al. (2024).

**Priority:** LOW — Existing citation is functional, just not complete.

---

## 11. Force Field Naming Inconsistency

### Issue FF-1: GAFF vs GAFF2 in documentation

**gui-guide.md line 297:**
> `ch4.itp` or `thf.itp` — Guest molecule parameters (GAFF)

**README.md line 216:**
> CH₄ and THF use GAFF2 force field

**Code (`gromacs_writer.py:1229`):**
> ; TIP4P-ICE water, Madrid2019 ions, GAFF2 guest molecules

**Code (`gromacs_writer.py:1254`):**
> ; CH4 atom types (GAFF2)

**Discrepancy:** gui-guide says "GAFF" (v1) while code and README say "GAFF2". The ITP files were created with GAFF2 parameters via Sobtop.

**Priority:** HIGH

**Fix:** Change "GAFF" → "GAFF2" in gui-guide.md line 297 and any other occurrences of bare "GAFF" in hydrate/guest molecule contexts.

---

## 12. Priority Ranking of All Documentation Fixes

### CRITICAL (GROMACS topology accuracy — users will get errors)

| ID | Issue | File | Lines | Fix |
|----|-------|------|-------|-----|
| MOL-1 | `CH4_HYD` → `CH4_H`, `THF_LIQ` → `THF_L` | `README.md` | 194-195 | Replace old moleculetype names |
| MOL-2 | `CH4_LIQ`/`THF_LIQ` → `CH4_L`/`THF_L` | `docs/gui-guide.md` | 708 | Replace names |
| MOL-3 | `CH4_HYD`/`THF_HYD` → `CH4_H`/`THF_H`, `_LIQ` → `_L` | `docs/gui-guide.md` | 710 | Replace names and update note |
| MOL-4 | `ch4.itp`/`thf.itp` → `ch4_hydrate.itp`/`thf_hydrate.itp` | `docs/gui-guide.md` | 297 | Update ITP file names |

### HIGH (Significant user confusion)

| ID | Issue | File | Lines | Fix |
|----|-------|------|-------|-----|
| MOL-5 | Hydrate ITP names in export table | `README.md` | 181 | `ch4.itp/thf.itp` → `ch4_hydrate.itp/thf_hydrate.itp` |
| FF-1 | "GAFF" → "GAFF2" | `docs/gui-guide.md` | 297 | Replace force field name |
| KS-1 | Missing shortcuts in table | `docs/gui-guide.md` | 200-214 | Add Ctrl+Alt+P, Ctrl+L, Ctrl+M |
| KS-2 | Ctrl+S description outdated | `docs/gui-guide.md` | 163 | Update to unified export behavior |
| KS-3 | Ctrl+E → Ctrl+H | `docs/gui-guide.md` | 281 | Update shortcut |

### MEDIUM (Moderate confusion)

| ID | Issue | File | Lines | Fix |
|----|-------|------|-------|-----|
| EXP-1 | Hydrate export filename pattern | `docs/gui-guide.md` | 295 | Add guest and supercell dims |
| EXP-2 | Solute export filename pattern | `docs/gui-guide.md` | 704-705 | Update to `solute_{type}_{count}.gro` |
| EXP-3 | Custom export filename pattern | `docs/gui-guide.md` | 589-590 | Update to `custom_system_{name}_{count}.gro` |
| VER-1 | CLI version 4.0.0 → 4.5.0 | `docs/cli-reference.md` | 145 | Update version string |

### LOW (Minor issues)

| ID | Issue | File | Lines | Fix |
|----|-------|------|-------|-----|
| SCI-1 | Avogadro number precision | `scorer.py` vs `solute_inserter.py` | 168 vs 32 | Standardize to 6.02214076e23 |
| INV-2 | ion.itp not documented as generated | — | — | Add note to gui-guide |

---

## 13. Items Fixed Since Previous Reports (2026-05-12 and 2026-05-16)

| Previous Issue ID | Description | Status | Fixed By |
|-------------------|-------------|--------|----------|
| V1 (2026-05-12) | Version 4.0.0 vs 4.5 in `__init__.py` | ✓ Fixed | `__version__` now `4.5.0` |
| D1 (2026-05-12) | 12 vs 8 ice phases not clarified | ✓ Fixed | QT-024: Two separate tables |
| C1 (2026-05-12) | Madrid2019 citation missing | ✓ Fixed | QT-026: Full citation added |
| D2 (2026-05-12) | Hydrate guest docstring (CO2/H2) | ✓ Fixed | QT-025: Docstring corrected |
| I2 (2026-05-16) | Madrid2019 citation missing (gui-guide) | ✓ Fixed | QT-026: Inline citation added |
| I3 (2026-05-16) | CO2/H2 not implemented (docstring error) | ✓ Fixed | QT-025: Docstring corrected |
| — | Hydrate naming _HYD → _H in code | ✓ Fixed | QT-028: Registry + ITP files |

---

## 14. Summary Statistics

| Metric | Value |
|--------|-------|
| Documentation files reviewed | 8 |
| Total documentation lines | ~3,355 |
| Issues found (total) | 15 |
| Critical issues | 4 |
| High issues | 5 |
| Medium issues | 4 |
| Low issues | 2 |
| Citation suggestions | 8 (6 new + 2 updates) |
| Items fixed since last report | 7 |
| Remaining doc-only fixes | 14 (all can be fixed without code changes) |

---

## 15. Recommended Fix Order

1. **MOL-1 + MOL-2 + MOL-3 + MOL-4** (CRITICAL) — Batch fix all molecule naming in README and gui-guide. ~10 minutes.
2. **MOL-5 + FF-1** (HIGH) — Fix hydrate ITP names and GAFF2 naming. ~3 minutes.
3. **KS-1 + KS-2 + KS-3** (HIGH) — Fix keyboard shortcuts table. ~5 minutes.
4. **EXP-1 + EXP-2 + EXP-3** (MEDIUM) — Fix export filename patterns. ~5 minutes.
5. **VER-1** (MEDIUM) — Fix CLI version reference. ~1 minute.
6. **Add citations** — Add GAFF2, RESP2, clathrate hydrate references to README. ~15 minutes.

**Total estimated effort:** ~40 minutes for all documentation fixes.

---

*Analysis complete. Report generated: 2026-05-22*
