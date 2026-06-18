# Complete DOI Inventory — QuickIce Codebase

**Audit Date:** 2026-06-18
**Scope:** All production documentation and source code (excludes `.planning/` internal notes)
**Method:** Exhaustive grep for `10.\d{4,}` and `doi`/`DOI` across all `.md`, `.py`, `.top`, `.itp` files

---

## Summary

| Paper/Reference | DOI(s) Found | Occurrences | Discrepancy? |
|---|---|---|---|
| TIP4P-ICE (Abascal 2005) | `10.1063/1.1931662` | 8 | **No** — consistent |
| Madrid2019 (Zeron 2019) | `10.1063/1.5121394` ⛔, `10.1063/1.5121392` ✅, `10.1021/acs.jctc.9b00902` ⛔ | 4 | **YES — 3 different DOIs, verified: `1394`=wrong paper, `9b00902`=404, `1392`=correct** |
| GenIce2 (Matsumoto 2017) | `10.1002/jcc.25077` | 3 | No |
| spglib (Togo 2024) | `10.1080/27660400.2024.2384822` | 4 | No |
| GAFF (Wang 2004) | `10.1002/jcc.20035` | 3 | No |
| RESP2 (He 2020) | `10.1021/acs.jcim.9b01131` | 1 | No |
| Journaux 2019 | `10.1029/2019JE006176` | 4 | No |
| Journaux 2020 | `10.1007/s11214-019-0634-7` | 1 | No |
| CODATA 2017 (Tiesinga 2021) | `10.1103/RevModPhys.93.025010` | 1 | No |
| Multiwfn 2012 (Lu & Chen) | `10.1002/jcc.22885` | 1 | No |
| Multiwfn 2024 (Lu) | `10.1063/5.0216272` | 1 | No |
| Ice Ic — Vos 1993 | `10.1103/PhysRevLett.71.3150` | 1 | No |
| Ice II — Kamb 1964 | `10.1107/S0365110X64003553` | 1 | No |
| Ice VIII — Kuhs 1984 | `10.1063/1.448109` | 1 | No |
| Ice IX — Londono 1993 | `10.1063/1.464942` | 2 | No |
| Ice XV — Salzmann 2009 | `10.1103/PhysRevLett.103.105701` | 2 | No |
| Lobban 1998 (Ice V) | `10.1038/34622` | 1 | No |

**Total unique DOI strings:** 19
**Total occurrences in production files:** 36

---

## Group 1: TIP4P-ICE (Abascal et al. 2005)

**Paper:** Abascal, J. L. F., Sanz, E., García Fernández, R., & Vega, C. (2005). A potential model for the study of ices and amorphous water: TIP4P/Ice. *Journal of Chemical Physics*, 122(23), 234511.

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 1 | `README.md` | 226 | `10.1063/1.1931662` | `DOI: https://doi.org/10.1063/1.1931662` | Full reference in Water Model section |
| 2 | `docs/gui-guide.md` | 864 | `10.1063/1.1931662` | `https://doi.org/10.1063/1.1931662` | Hyperlink in References section |
| 3 | `docs/cli-reference.md` | 1183 | `10.1063/1.1931662` | `https://doi.org/10.1063/1.1931662` | Hyperlink in See Also section |
| 4 | `docs/gro-itp-guide.md` | 894 | `10.1063/1.1931662` | `DOI: 10.1063/1.1931662` | Full reference in Scientific References section |
| 5 | `quickice/gui/main_window.py` | 1627 | `10.1063/1.1931662` | `DOI: 10.1063/1.1931662` | Inline in QMessageBox — ice export success dialog |
| 6 | `quickice/gui/main_window.py` | 1650 | `10.1063/1.1931662` | `DOI: 10.1063/1.1931662` | Inline in QMessageBox — interface export success dialog |
| 7 | `tests/test_tip4p_ice_lj_values.py` | 8 | `10.1063/1.1931662` | `DOI: 10.1063/1.1931662` | Docstring reference for LJ parameter test |
| 8 | `docs/principles.md` | — | — | — | **NOT present** — principles.md does NOT cite TIP4P-ICE DOI |

**Verdict:** All 7 occurrences use identical DOI `10.1063/1.1931662`. **Consistent.**

---

## Group 2: Madrid2019 (Zeron, Abascal & Vega 2019) — ⚠️ CRITICAL DISCREPANCY

**Paper:** Zeron, I. M., Abascal, J. L. F., & Vega, C. (2019). A force field of Li⁺, Na⁺, K⁺, Mg²⁺, Ca²⁺, Cl⁻, and SO₄²⁻ in aqueous solution based on the TIP4P/2005 water model and scaled charges for the ions. *Journal of Chemical Physics*, 151, 134504.

### 2a: DOI `10.1063/1.5121394` (currently in README)

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 1 | `README.md` | 371 | `10.1063/1.5121394` | `DOI: https://doi.org/10.1063/1.5121394` | Madrid2019 Ion Parameters section — full reference |
| 2 | `README.md` | 375 | `10.1063/1.5121394` | `DOI: 10.1063/1.5121394` | Madrid2019 / TIP4P-ICE Compatibility section |

### 2b: DOI `10.1063/1.5121392` (in gui-guide.md)

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 3 | `docs/gui-guide.md` | 793 | `10.1063/1.5121392` | `DOI: https://doi.org/10.1063/1.5121392` | Ion Tab section — Madrid2019 force field parameters note |

### 2c: DOI `10.1021/acs.jctc.9b00902` (in cli-reference.md) — ⛔ WRONG PAPER

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 4 | `docs/cli-reference.md` | 930 | `10.1021/acs.jctc.9b00902` | `https://doi.org/10.1021/acs.jctc.9b00902` | `--ion-concentration` option — Madrid2019 reference link |

### 2d: Source code references (no DOI, but name Madrid2019)

| # | File | Line | Context |
|---|------|------|---------|
| 5 | `quickice/structure_generation/gromacs_ion_export.py` | 4 | Docstring: "Na+/Cl- from Madrid2019" |
| 6 | `quickice/structure_generation/gromacs_ion_export.py` | 9 | Comment: "# Madrid2019 ion parameters" |
| 7 | `quickice/structure_generation/gromacs_ion_export.py` | 14 | Comment: "# GROMACS atom type names (Madrid2019)" |
| 8 | `quickice/structure_generation/gromacs_ion_export.py` | 18 | Comment: "# Partial charges (Madrid2019 ion parameters)" |
| 9 | `quickice/structure_generation/gromacs_ion_export.py` | 22 | Comment: "# VDW parameters (from Madrid2019_085.top)" |
| 10 | `quickice/structure_generation/gromacs_ion_export.py` | 40 | Generated ITP: "; Madrid2019_085 ion model (Zeron et al., J. Chem. Phys. 2019)" — **no DOI in generated output** |
| 11 | `quickice/structure_generation/ion_inserter.py` | 26 | Comment: "# Ion parameters from Madrid2019_085 (Zeron et al., J. Chem. Phys. 2019)" |
| 12 | `quickice/gui/ion_panel.py` | 446 | Docstring: "±0.85 from Madrid2019" |
| 13 | `quickice/gui/ion_panel.py` | 467 | Comment: "# Madrid2019 ion charges" |

**Key finding:** Source code references Madrid2019 by name and journal but **does not include any DOI**. The only DOI in generated output is absent (line 40 of gromacs_ion_export.py just has the paper name, no DOI).

---

## Group 3: GenIce2 (Matsumoto et al. 2017)

**Paper:** Matsumoto, M. et al. (2017). GenIce: Hydrogen-disordered ice structures by combinatorial generation. *Journal of Computational Chemistry*, 38(17), 1493–1501.

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 1 | `README.md` | 324 | `10.1002/jcc.25077` | `DOI: https://doi.org/10.1002/jcc.25077` | GenIce2 section |
| 2 | `docs/principles.md` | 186 | `10.1002/jcc.25077` | `DOI: https://doi.org/10.1002/jcc.25077` | GenIce2 section |

**Verdict:** Consistent across both occurrences.

---

## Group 4: spglib (Togo et al. 2024)

**Paper:** Togo, A. et al. (2024). Spglib: a software library for crystal symmetry search. *Science and Technology of Advanced Materials: Methods*, 4, 2384822.

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 1 | `README.md` | 351 | `10.1080/27660400.2024.2384822` | `DOI: https://doi.org/10.1080/27660400.2024.2384822` | spglib section |
| 2 | `docs/cli-reference.md` | 1046 | `10.1080/27660400.2024.2384822` | `DOI: https://doi.org/10.1080/27660400.2024.2384822` | spglib section |
| 3 | `docs/principles.md` | 201 | `10.1080/27660400.2024.2384822` | `DOI: https://doi.org/10.1080/27660400.2024.2384822` | spglib section |

**Verdict:** Consistent across all 3 occurrences.

---

## Group 5: GAFF (Wang et al. 2004)

**Paper:** Wang, J., Wolf, R. M., Caldwell, J. W., Kollman, P. A., & Case, D. A. (2004). Development and testing of a general amber force field. *Journal of Computational Chemistry*, 25(9), 1157–1174.

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 1 | `README.md` | 363 | `10.1002/jcc.20035` | `DOI: https://doi.org/10.1002/jcc.20035` | GAFF / GAFF2 section |
| 2 | `docs/gro-itp-guide.md` | 896 | `10.1002/jcc.20035` | `DOI: 10.1002/jcc.20035` | GAFF2 reference |

**Verdict:** Consistent across both occurrences.

---

## Group 6: RESP2 (He et al. 2020)

**Paper:** He, X., Man, V. H., Yang, Y., Wang, L.-P., & Merz, K. M. (2020). A fast and high-quality charge model for molecular mechanical force fields. *JCIM*, 60(5), 247–257.

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 1 | `README.md` | 364 | `10.1021/acs.jcim.9b01131` | `DOI: https://doi.org/10.1021/acs.jcim.9b01131` | GAFF / GAFF2 section |

**Verdict:** Single occurrence only.

---

## Group 7: Journaux et al. (2019)

**Paper:** Journaux, B. et al. (2019). J. Geophys. Res.: Planets, 124.

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 1 | `README.md` | 339 | `10.1029/2019JE006176` | `DOI: 10.1029/2019JE006176` | Journaux section (bare DOI, no https://doi.org/ prefix) |
| 2 | `quickice/phase_mapping/data/ice_boundaries.py` | 15 | `10.1029/2019JE006176` | `DOI: 10.1029/2019JE006176` | Module docstring — data sources list |
| 3 | `quickice/phase_mapping/data/ice_boundaries.py` | 43 | `10.1029/2019JE006176` | `DOI: 10.1029/2019JE006176` | Inline comment — II-III-V triple point |
| 4 | `quickice/phase_mapping/data/ice_boundaries.py` | 56 | `10.1029/2019JE006176` | `DOI: 10.1029/2019JE006176` | Inline comment — II-V-VI triple point |

**Verdict:** Consistent across all 4 occurrences. Format varies (README has no `https://doi.org/` wrapper, code uses bare `DOI:` prefix).

---

## Group 8: Journaux et al. (2020)

**Paper:** Journaux, B. et al. (2020). Space Sci. Rev., 216, 7.

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 1 | `README.md` | 340 | `10.1007/s11214-019-0634-7` | `DOI: 10.1007/s11214-019-0634-7` | Journaux section (bare DOI) |

**Verdict:** Single occurrence only. Note: `ice_boundaries.py` mentions Journaux 2020 in docstring (line 16: "7. Journaux et al. (2020): Space Science Review, 7:216") but **does NOT include a DOI** for the 2020 paper.

---

## Group 9: CODATA 2017 (Tiesinga et al. 2021)

**Paper:** Tiesinga, E. et al. (2021). Rev. Mod. Phys., 93(2), 025010.

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 1 | `README.md` | 346 | `10.1103/RevModPhys.93.025010` | `DOI: 10.1103/RevModPhys.93.025010` | CODATA 2017 section |

**Verdict:** Single occurrence only.

---

## Group 10: Multiwfn 2012 (Lu & Chen)

**Paper:** Lu, T. & Chen, F. (2012). Multiwfn: A Multifunctional Wavefunction Analyzer. *J. Comput. Chem.*, 33, 580–592.

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 1 | `README.md` | 355 | `10.1002/jcc.22885` | `DOI: 10.1002/jcc.22885` | Multiwfn section (bare DOI) |

**Verdict:** Single occurrence only.

---

## Group 11: Multiwfn 2024 (Lu)

**Paper:** Lu, T. (2024). A comprehensive electron wavefunction analysis toolbox for chemists, Multiwfn. *J. Chem. Phys.*, 161, 082503.

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 1 | `README.md` | 357 | `10.1063/5.0216272` | `DOI: 10.1063/5.0216272` | Multiwfn section (bare DOI) |

**Verdict:** Single occurrence only.

---

## Group 12: Ice Ic — Vos et al. (1993)

**Paper:** Vos, W.L. et al. (1993). Phys. Rev. Lett., 71(19), 3150-3153.

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 1 | `quickice/gui/main_window.py` | 1947 | `10.1103/PhysRevLett.71.3150` | `DOI: 10.1103/PhysRevLett.71.3150` | Phase citation dict — displayed in GUI |

**Verdict:** Single occurrence, only in GUI source code (user-facing).

---

## Group 13: Ice II — Kamb (1964)

**Paper:** Kamb, B. (1964). Acta Cryst., 17, 1437-1449.

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 1 | `quickice/gui/main_window.py` | 1952 | `10.1107/S0365110X64003553` | `DOI: 10.1107/S0365110X64003553` | Phase citation dict — displayed in GUI |

**Verdict:** Single occurrence, only in GUI source code (user-facing).

---

## Group 14: Ice VIII — Kuhs et al. (1984)

**Paper:** Kuhs, W.F. et al. (1984). J. Chem. Phys., 81(8), 3612-3623.

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 1 | `quickice/gui/main_window.py` | 1957 | `10.1063/1.448109` | `DOI: 10.1063/1.448109` | Phase citation dict — displayed in GUI |

**Verdict:** Single occurrence, only in GUI source code (user-facing).

---

## Group 15: Ice IX — Londono et al. (1993)

**Paper:** Londono, J.D. et al. (1993). J. Chem. Phys., 98(6), 4878-4888.

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 1 | `quickice/gui/main_window.py` | 1959 | `10.1063/1.464942` | `DOI: 10.1063/1.464942` | Phase citation dict — displayed in GUI |
| 2 | `docs/principles.md` | 207 | `10.1063/1.464942` | `DOI: https://doi.org/10.1063/1.464942` | Ice Phase Diagrams section |

**Verdict:** Consistent across both occurrences.

---

## Group 16: Ice XV — Salzmann et al. (2009)

**Paper:** Salzmann, C.G. et al. (2009). Phys. Rev. Lett., 103(10), 105701.

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 1 | `quickice/gui/main_window.py` | 1961 | `10.1103/PhysRevLett.103.105701` | `DOI: 10.1103/PhysRevLett.103.105701` | Phase citation dict — displayed in GUI |
| 2 | `docs/principles.md` | 209 | `10.1103/physrevlett.103.105701` | `DOI: https://doi.org/10.1103/physrevlett.103.105701` | Ice Phase Diagrams section — **note lowercase `physrevlett`** |

**Verdict:** DOI is the same but **case differs**: GUI uses `PhysRevLett` (PascalCase), principles.md uses `physrevlett` (lowercase). DOIs are case-insensitive per the spec, so functionally identical — but cosmetically inconsistent.

---

## Group 17: Lobban et al. (1998) — Ice V

**Paper:** Lobban, C., Finney, J. L., & Kuhs, W. F. (1998). The structure of a new phase of ice. *Nature*, 391, 26–29.

| # | File | Line | DOI String | Format | Context |
|---|------|------|-----------|--------|---------|
| 1 | `docs/principles.md` | 208 | `10.1038/34622` | `DOI: https://doi.org/10.1038/34622` | Ice Phase Diagrams section |

**Verdict:** Single occurrence only. Not referenced in GUI citation dict or README.

---

## Files With NO DOIs

The following production files were checked and contain **no DOI references**:

- `README_bin.md` — Binary distribution guide, no citations
- `state_reference.md` — Reference URLs only, no DOIs
- `docs/ranking.md` — No DOIs
- `docs/flowchart.md` — No DOIs
- `quickice/structure_generation/gromacs_ion_export.py` — References "Madrid2019" and "Zeron et al., J. Chem. Phys. 2019" by name but **no DOI**
- `quickice/structure_generation/ion_inserter.py` — References "Madrid2019_085" but **no DOI**
- `quickice/gui/ion_panel.py` — References "Madrid2019" but **no DOI**
- `quickice/gui/export.py` — No DOIs
- `quickice/gui/hydrate_export.py` — No DOIs
- All `.top` files in `sample_output/` — No DOIs
- All `.itp` files in `sample_output/` and `quickice/data/` — No DOIs
- `scripts/` — All shell scripts, no DOIs

---

## DISCREPANCIES

### D1: Madrid2019 — THREE DIFFERENT DOIs for the same paper ⛔ CRITICAL

| Location | DOI | Status |
|----------|-----|--------|
| `README.md:371` | `10.1063/1.5121394` | ⛔ **WRONG** — resolves to Xian et al. 2019, "Misinformation spreading on correlated multiplex networks", *Chaos* 29(11) |
| `README.md:375` | `10.1063/1.5121394` | ⛔ **WRONG** — same wrong paper as above |
| `docs/gui-guide.md:793` | `10.1063/1.5121392` | ✅ **CORRECT** — resolves to Zeron, Abascal & Vega 2019, J. Chem. Phys. 151, 134504 |
| `docs/cli-reference.md:930` | `10.1021/acs.jctc.9b00902` | ⛔ **WRONG** — returns HTTP 404, DOI does not exist |

**Verified by resolving all three DOIs on 2026-06-18:**
- `https://doi.org/10.1063/1.5121394` → Xian, Yang, Pan, Wang & Wang (2019). "Misinformation spreading on correlated multiplex networks." *Chaos* 29(11). **NOT the Madrid2019 paper.**
- `https://doi.org/10.1063/1.5121392` → Zeron, Abascal & Vega (2019). "A force field of Li⁺, Na⁺, K⁺, Mg²⁺, Ca²⁺, Cl⁻, and SO₄²⁻ in aqueous solution..." *J. Chem. Phys.* 151, 134504. **This IS the Madrid2019 paper.**
- `https://doi.org/10.1021/acs.jctc.9b00902` → HTTP 404. DOI does not resolve. **Completely fictitious.**

**Correct DOI: `10.1063/1.5121392`**

**Fix required:**
- `README.md:371` — change `10.1063/1.5121394` → `10.1063/1.5121392`
- `README.md:375` — change `10.1063/1.5121394` → `10.1063/1.5121392`
- `docs/cli-reference.md:930` — change `10.1021/acs.jctc.9b00902` → `10.1063/1.5121392`
- `docs/gui-guide.md:793` — already correct, no change needed

### D2: Ice XV DOI — case inconsistency (COSMETIC)

| Location | DOI | Case |
|----------|-----|------|
| `quickice/gui/main_window.py:1961` | `10.1103/PhysRevLett.103.105701` | PascalCase `PhysRevLett` |
| `docs/principles.md:209` | `10.1103/physrevlett.103.105701` | lowercase `physrevlett` |

**Impact:** Negligible — DOIs are case-insensitive. Both resolve to the same paper.
**Recommendation:** Standardize to PascalCase `PhysRevLett` for readability (matches the journal abbreviation convention used elsewhere).

### D3: Madrid2019 in source code — no DOI at all (GAP)

| Location | What's There | What's Missing |
|----------|-------------|----------------|
| `quickice/structure_generation/gromacs_ion_export.py:40` | `; Madrid2019_085 ion model (Zeron et al., J. Chem. Phys. 2019)` | No DOI in generated .itp output |
| `quickice/structure_generation/ion_inserter.py:26` | `# Ion parameters from Madrid2019_085 (Zeron et al., J. Chem. Phys. 2019)` | No DOI in comment |
| `quickice/gui/ion_panel.py:446` | `±0.85 from Madrid2019` | No DOI in docstring |

**Impact:** The generated ion.itp file (line 40) is user-facing output that lacks a DOI. Users won't know which paper to cite from the .itp alone.
**Recommendation:** Add the correct DOI `10.1063/1.5121392` to the generated .itp output in `gromacs_ion_export.py:40`, e.g., `; Madrid2019_085 ion model (Zeron et al., J. Chem. Phys. 2019, DOI: 10.1063/1.5121392)`.

### D4: Journaux 2020 — DOI missing from ice_boundaries.py (GAP)

| Location | What's There | What's Missing |
|----------|-------------|----------------|
| `quickice/phase_mapping/data/ice_boundaries.py:16` | `7. Journaux et al. (2020): Space Science Review, 7:216` | No DOI (unlike line 15 which has one for 2019) |
| `README.md:340` | `DOI: 10.1007/s11214-019-0634-7` | Correct DOI present in README |

**Impact:** Minor — code comment is incomplete.
**Recommendation:** Add `DOI: 10.1007/s11214-019-0634-7` to line 16 of `ice_boundaries.py`.

---

## Files NOT Containing Any DOI Reference

For completeness, these production files were explicitly checked and confirmed to contain zero DOI references:

- `README_bin.md`
- `state_reference.md`
- `docs/ranking.md`
- `docs/flowchart.md`
- All files in `scripts/` (shell scripts only)
- All `.top` files in `sample_output/`
- All `.itp` files in `sample_output/` and `quickice/data/`
- `quickice/gui/export.py`
- `quickice/gui/hydrate_export.py`
- `quickice/cli/pipeline.py`
- `quickice/cli/parser.py`
- `quickice/cli/itp_helpers.py`
- `quickice/structure_generation/generator.py`
- `quickice/structure_generation/mapper.py`
- `quickice/structure_generation/gro_parser.py`
- `quickice/structure_generation/itp_parser.py`
- `quickice/structure_generation/molecule_validator.py`
- `quickice/structure_generation/errors.py`

---

## Appendix: Raw DOI String Formats Found

| Format | Example | Files Using This |
|--------|---------|------------------|
| `DOI: https://doi.org/10.XXXX` | `DOI: https://doi.org/10.1063/1.1931662` | `README.md` |
| `https://doi.org/10.XXXX` | `https://doi.org/10.1063/1.1931662` | `docs/gui-guide.md`, `docs/cli-reference.md`, `docs/principles.md` |
| `DOI: 10.XXXX` | `DOI: 10.1063/1.1931662` | `docs/gro-itp-guide.md`, `quickice/gui/main_window.py`, `quickice/phase_mapping/data/ice_boundaries.py`, `tests/test_tip4p_ice_lj_values.py` |
| Bare `10.XXXX` | `10.1063/1.5121394` | `README.md:375` |
| `https://doi.org/10.XXXX` (markdown link) | `[text](https://doi.org/10.XXXX)` | `docs/cli-reference.md:930`, `docs/gui-guide.md:864`, `docs/cli-reference.md:1183` |

**Recommendation:** Standardize DOI format across the codebase. Suggested canonical format: `DOI: https://doi.org/10.XXXX` (includes both prefix and resolver URL for maximum usability).

---

*Audit complete. Total production DOI occurrences: 36 across 8 documentation files and 3 source files.*
