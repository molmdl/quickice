# Complete Citation Inventory — QuickIce Codebase

**Generated:** 2026-05-22
**Scope:** All citations, references, DOIs, and attribution found in source code, ITP files, README, and docs/

---

## 1. TIP4P-ICE Water Model

**What it is:** Force field for ice simulations

| Location | Citation Text | Format |
|----------|---------------|--------|
| `README.md:211` | Abascal et al. 2005, DOI: https://doi.org/10.1063/1.1931662 | Full ref + DOI |
| `quickice/gui/main_window.py:1626` | (Abascal et al. 2005, DOI: 10.1063/1.1931662) | Inline in info panel |
| `quickice/gui/main_window.py:1649` | (Abascal et al. 2005, DOI: 10.1063/1.1931662) | Inline in info panel |
| `docs/gui-guide.md:864` | [TIP4P-ice Reference](https://doi.org/10.1063/1.1931662) | Hyperlink |
| `docs/cli-reference.md:403` | [TIP4P-ice Reference](https://doi.org/10.1063/1.1931662) | Hyperlink |
| `docs/gro-itp-guide.md:868` | Full ref: Abascal, J.L.F., Sanz, E., García Fernández, R., & Vega, C. (2005). J. Chem. Phys., 122(23), 234511. DOI: 10.1063/1.1931662 | Full ref + DOI |
| `quickice/data/tip4p-ice.itp:1-3` | Adapted from sklogwiki (cc-by-nc-sa 3.0) + computational chemistry commune | Credit + URL |
| `docs/gui-guide.md:196` | Credit: sklogwiki + computational chemistry commune | Credit + URL |
| `docs/cli-reference.md:115` | Credit: computational chemistry commune | Credit + URL |

**Full reference:** Abascal, J. L. F., Sanz, E., García Fernández, R., & Vega, C. (2005). A potential model for the study of ices and amorphous water: TIP4P/Ice. *Journal of Chemical Physics*, 122(23), 234511. **DOI: 10.1063/1.1931662**

---

## 2. GenIce2

**What it is:** Hydrogen-disordered ice structure generator

| Location | Citation Text | Format |
|----------|---------------|--------|
| `README.md:306-308` | Repository + Paper title + DOI: https://doi.org/10.1002/jcc.25077 | Full ref + DOI |
| `docs/principles.md:184-186` | Repository + Paper title + DOI: https://doi.org/10.1002/jcc.25077 | Full ref + DOI |
| `quickice/phase_mapping/data/ice_boundaries.py:10` | GenIce2 Python Library: https://pypi.org/project/genice2/ | URL only |

**Full reference:** Matsumoto, M. et al. (2017). GenIce: Hydrogen-disordered ice structures by combinatorial generation. *Journal of Computational Chemistry*, 38(17), 1493–1501. **DOI: 10.1002/jcc.25077**

---

## 3. IAPWS R14-08 (Melting/Sublimation Curves)

**What it is:** Release on pressure along melting and sublimation curves

| Location | Citation Text | Format |
|----------|---------------|--------|
| `README.md:311-312` | Document title + URL: https://www.iapws.org/relguide/MeltSub.html | Title + URL |
| `docs/principles.md:192` | URL: https://www.iapws.org/relguide/MeltSub.html | URL only |
| `quickice/phase_mapping/data/ice_boundaries.py:14` | IAPWS R14-08(2011): http://www.iapws.org/release/MeltIce.pdf | **Different URL** |
| `quickice/phase_mapping/data/ice_boundaries.py:5-6` | Referenced in module docstring | Name only |

**ISSUE:** URL mismatch — Code uses `http://www.iapws.org/release/MeltIce.pdf`, docs use `https://www.iapws.org/relguide/MeltSub.html`

---

## 4. IAPWS R10-06 (Ice Ih Equation of State)

**What it is:** Equation of State 2006 for H₂O Ice Ih

| Location | Citation Text | Format |
|----------|---------------|--------|
| `README.md:314-316` | Document title + URL: https://www.iapws.org/relguide/Ice-2006.html | Title + URL |
| `quickice/phase_mapping/ice_ih_density.py:11-12` | IAPWS R10-06(2009) + URL: https://www.iapws.org/release/Ice-2009.html | **Different URL** |

**ISSUE:** URL mismatch — README uses `https://www.iapws.org/relguide/Ice-2006.html`, code uses `https://www.iapws.org/release/Ice-2009.html`

---

## 5. IAPWS-95 (Water Thermodynamic Properties)

**What it is:** 1995 formulation for water thermodynamic properties

| Location | Citation Text | Format |
|----------|---------------|--------|
| `quickice/phase_mapping/water_density.py:13-16` | Full title + URL: https://www.iapws.org/release/IAPWS-95.html | Code docstring only |

**ISSUE:** NOT in README or user-facing docs — only in code docstring. Missing from documentation.

---

## 6. spglib

**What it is:** Crystal symmetry search library

| Location | Citation Text | Format |
|----------|---------------|--------|
| `README.md:319-321` | Repository + Paper title + DOI: https://doi.org/10.1080/27660400.2024.2384822 | Full ref + DOI |
| `docs/principles.md:199-201` | Repository + Paper + DOI | Full ref + DOI |
| `docs/cli-reference.md:393-395` | Repository + DOI | Full ref + DOI |

**Full reference:** Togo, A. et al. (2024). Spglib: a software library for crystal symmetry search. *Science and Technology of Advanced Materials: Methods*, 4, 2384822. **DOI: 10.1080/27660400.2024.2384822**

---

## 7. Madrid2019 Ion Parameters

**What it is:** Force field for ions in aqueous solution with scaled charges

| Location | Citation Text | Format |
|----------|---------------|--------|
| `README.md:339-341` | Full reference + DOI: https://doi.org/10.1063/1.5121392 | Full ref + DOI |
| `docs/gui-guide.md:793` | Zeron, Abascal, & Vega, J. Chem. Phys. 151, 134504 (2019), DOI: https://doi.org/10.1063/1.5121392 | Full ref + DOI |
| `quickice/structure_generation/gromacs_ion_export.py:40` | ; Madrid2019_085 ion model (Zeron et al., J. Chem. Phys. 2019) | Comment only, no DOI |
| `quickice/structure_generation/ion_inserter.py:24` | # Ion parameters from Madrid2019_085 (Zeron et al., J. Chem. Phys. 2019) | Comment only, no DOI |

**Full reference:** Zeron, I. M., Abascal, J. L. F., & Vega, C. (2019). A force field of Li⁺, Na⁺, K⁺, Mg²⁺, Ca²⁺, Cl⁻, and SO₄²⁻ in aqueous solution based on the TIP4P/2005 water model and scaled charges for the ions. *Journal of Chemical Physics*, 151, 134504. **DOI: 10.1063/1.5121392**

---

## 8. GAFF / GAFF2

**What it is:** General AMBER Force Field for guest molecules

| Location | Citation Text | Format |
|----------|---------------|--------|
| `README.md:333` | Wang et al. (2004). J. Comput. Chem., 25(9), 1157–1174. DOI: https://doi.org/10.1002/jcc.20035 | Full ref + DOI |
| `README.md:334` | He et al. (2020). JCIM, 60(5), 247–257. DOI: https://doi.org/10.1021/acs.jcim.9b01131 | Full ref + DOI (RESP2 charges) |
| `docs/gro-itp-guide.md:870` | Wang et al. (2004). J. Comput. Chem., 25(9), 1157-1174. DOI: 10.1002/jcc.20035 | Full ref + DOI |

**Two sub-references:**
1. **GAFF:** Wang, J. et al. (2004). Development and testing of a general amber force field. *J. Comput. Chem.*, 25(9), 1157–1174. **DOI: 10.1002/jcc.20035**
2. **RESP2:** He, X. et al. (2020). A fast and high-quality charge model for molecular mechanical force fields. *JCIM*, 60(5), 247–257. **DOI: 10.1021/acs.jcim.9b01131**

---

## 9. Sobtop

**What it is:** Tool for generating GROMACS topology files

| Location | Citation Text | Format |
|----------|---------------|--------|
| `README.md:330` | Tian Lu, Sobtop, Version 2026.1.16, http://sobereva.com/soft/Sobtop | Software citation |
| `quickice/data/ch4.itp:1` | ; Created by Sobtop (http://sobereva.com/soft/sobtop) Version 2026.1.16 on 2026-04-15 | ITP header |
| `quickice/data/ch4_liquid.itp:1` | Same format | ITP header |
| `quickice/data/thf.itp:1` | Same format | ITP header |
| `quickice/data/thf_liquid.itp:1` | Same format | ITP header |
| `quickice/data/ch4_hydrate.itp:1` | Same format | ITP header |
| `quickice/data/thf_hydrate.itp:1` | Same format | ITP header |
| `quickice/data/custom/etoh.itp:1` | Same format (2026-05-08) | ITP header |
| `quickice/data/custom/etoh.top:1` | Same format (2026-05-08) | TOP header |

---

## 10. Multiwfn

**What it is:** Multifunctional wavefunction analyzer (used for charge calculation)

| Location | Citation Text | Format |
|----------|---------------|--------|
| `README.md:324-327` | Two papers: (1) J. Comput. Chem. 33, 580-592 (2012) DOI: 10.1002/jcc.22885; (2) J. Chem. Phys. 161, 082503 (2024) DOI: 10.1063/5.0216272 | Full ref + DOI |
| `docs/gui-guide.md:260` | "GAFF2 with RESP2(0.5) partial charges, prepared using Multiwfn and Sobtop" | Mention only |

**Two sub-references:**
1. Lu, T. & Chen, F. (2012). Multiwfn: A Multifunctional Wavefunction Analyzer. *J. Comput. Chem.*, 33, 580–592. **DOI: 10.1002/jcc.22885**
2. Lu, T. (2024). A comprehensive electron wavefunction analysis toolbox for chemists, Multiwfn. *J. Chem. Phys.*, 161, 082503. **DOI: 10.1063/5.0216272**

---

## 11. Gaussian 16 Rev. C01

**What it is:** QM calculation software used for charge derivation

| Location | Citation Text | Format |
|----------|---------------|--------|
| `README.md:336-337` | Full Gaussian 16 Rev. C01 author list, Gaussian, Inc., Wallingford CT, 2016 | Full software citation |
| `docs/gui-guide.md:260` | "QM calcution were done using Gaussian 16 Rev. C01" | Mention (typo: "calcution") |

**Full reference:** Gaussian 16, Revision C.01, M. J. Frisch et al., Gaussian, Inc., Wallingford CT, 2016.

---

## 12. Ice Phase Crystal Structure Citations

**Source:** `quickice/gui/main_window.py:1942-1962` (_get_citation function)

| Phase | Citation | DOI |
|-------|----------|-----|
| ice_ih | "No specific citation required" | None |
| ice_ii | Kamb, B. (1964). Acta Cryst., 17, 1437-1449. + Kamb, B. et al. (2003). J. Chem. Phys., 55, 1934-1945. | 10.1107/S0365110X64003553 (first only) |
| ice_iii | Petrenko, V.F. & Whitworth, R.W. (1999). Physics of Ice, Table 11.2. | None |
| ice_v | "No specific citation in GenIce2" | None |
| ice_vi | Petrenko, V.F. & Whitworth, R.W. (1999). Physics of Ice, Table 11.2. | None |
| ice_vii | "No specific citation in GenIce2" | None |
| ice_viii | Kuhs, W.F. et al. (1984). J. Chem. Phys., 81(8), 3612-3623. | 10.1063/1.448109 |
| ice_ix | Londono, J.D. et al. (1993). J. Chem. Phys., 98(6), 4878-4888. | 10.1063/1.464942 |
| ice_xv | Salzmann, C.G. et al. (2009). Phys. Rev. Lett., 103(10), 105701. | 10.1103/PhysRevLett.103.105701 |

**Also in:**
- `docs/principles.md:207-209` — Londono, Lobban, Salzmann (with DOIs)
- `quickice/ranking/types.py:21` — Petrenko & Whitworth (1999), Physics of Ice (ideal O-O distance)
- `docs/ranking.md:31` — Petrenko & Whitworth (1999), Physics of Ice

**Petrenko & Whitworth (1999) full reference:** Petrenko, V. F. & Whitworth, R. W. (1999). *Physics of Ice*. Oxford University Press. ISBN: 0-19-851893-7.

---

## 13. Journaux et al. (2019, 2020)

**What it is:** High-pressure ice phase boundary data

| Location | Citation Text | Format |
|----------|---------------|--------|
| `quickice/phase_mapping/data/ice_boundaries.py:15` | Journaux et al. (2019): J. Geophys. Res.: Planets, DOI: 10.1029/2019JE006176 | Full ref + DOI |
| `quickice/phase_mapping/data/ice_boundaries.py:16` | Journaux et al. (2020): Space Science Review, 7:216 | Short ref, no DOI |
| `quickice/phase_mapping/lookup.py:9` | Journaux et al. (2019, 2020) | Name only |
| `quickice/phase_mapping/triple_points.py:6` | Journaux et al. (2019, 2020) | Name only |

**Full references:**
1. Journaux, B. et al. (2019). Elasticity and sound velocities of polycrystalline ice Ih under pressure up to 12 GPa. *Journal of Geophysical Research: Planets*, 124. **DOI: 10.1029/2019JE006176**
2. Journaux, B. et al. (2020). Holistic approach for studying planetary ices: Methodology. *Space Science Reviews*, 216, 7. **DOI: 10.1007/s11214-019-0634-7**

**ISSUE:** NOT in README or user-facing docs — only in code comments/docstrings.

---

## 14. CODATA 2017 / AVOGADRO Constant

**What it is:** Avogadro constant used for concentration→molecule count conversion

| Location | Citation Text | Format |
|----------|---------------|--------|
| `quickice/structure_generation/ion_inserter.py:27` | AVOGADRO = 6.02214076e23 # mol^-1 (CODATA 2017) | Code constant only |
| `quickice/ranking/scorer.py:168` | AVOGADRO = 6.02214076e23 # molecules/mol (CODATA 2017) | Code constant only |
| `quickice/structure_generation/solute_inserter.py:32` | AVOGADRO = 6.02214076e23 # mol^-1 | Code constant, **no CODATA ref** |
| `docs/ranking.md:82` | N_A = Avogadro's number (6.022 × 10²³) | Numeric only |
| `docs/gui-guide.md:511` | N_A is Avogadro's number | Name only |

**ISSUE:** No formal CODATA citation anywhere. The constant value is correct (CODATA 2017) but no formal reference cited.

**Full reference:** Tiesinga, E., Mohr, P. J., Newell, D. B., & Taylor, B. N. (2021). CODATA Recommended Values of the Fundamental Physical Constants: 2018. *Reviews of Modern Physics*, 93(2), 025010. **DOI: 10.1103/RevModPhys.93.025010** (Note: The 2017 value is from the 2017 CODATA adjustment; the 2018 review paper confirms it.)

---

## 15. LSBU Water Phase Data

**What it is:** Phase boundary reference data

| Location | Citation Text | Format |
|----------|---------------|--------|
| `quickice/phase_mapping/data/ice_boundaries.py:26` | LSBU Water Phase Data (source #4) | Comment only |
| `quickice/phase_mapping/data/ice_boundaries.py:408` | __source__ = "LSBU Water Phase Data, IAPWS R14-08(2011)..." | Code constant |

**ISSUE:** No URL or formal citation — just a name reference. The URL appears to be: https://ergodic.ugr.es/termo/lecciones/water1.html (found in `state_reference.md:8`)

---

## 16. External Topology Tools (docs only)

**What it is:** Tool recommendations for custom molecule parameterization

| Location | Tools Mentioned |
|----------|-----------------|
| `docs/gro-itp-guide.md:426-479` | CHARMM-GUI, ATB, LigParGen, CGenFF, SwissParam |
| `docs/gro-itp-guide.md:834-852` | ACPYPE, CHARMM-GUI, LigParGen, ATB, CGenFF, Avogadro, PyMOL |

These are tool references with URLs, not formal scientific citations.

---

## 17. sklogwiki + Computational Chemistry Commune

**What it is:** Source of adapted TIP4P-ICE ITP file

| Location | Citation | Format |
|----------|----------|--------|
| `quickice/data/tip4p-ice.itp:1-3` | Adapted from sklogwiki (cc-by-nc-sa 3.0) + URL | Credit + license |
| `docs/gui-guide.md:196` | Credit links to sklogwiki + computational chemistry commune | Credit + URL |
| `docs/cli-reference.md:115` | Credit link to computational chemistry commune | Credit + URL |

---

## 18. Lobban et al. (1998)

**What it is:** Ice V crystal structure

| Location | Citation | Format |
|----------|----------|--------|
| `docs/principles.md:208` | Lobban et al., "The structure of a new phase of ice" (Nature 1998) — DOI: https://doi.org/10.1038/34622 | Full ref + DOI |

**ISSUE:** This citation appears in principles.md but NOT in `_get_citation()` in main_window.py. The ice_v citation there says "No specific citation in GenIce2" — Lobban could be used.

**Full reference:** Lobban, C., Finney, J. L., & Kuhs, W. F. (1998). The structure of a new phase of ice. *Nature*, 391, 26–29. **DOI: 10.1038/34622**

---

## Issues Summary

| # | Issue | Severity | Location(s) |
|---|-------|----------|-------------|
| 1 | IAPWS R14-08 URL mismatch (code vs docs) | MEDIUM | `ice_boundaries.py:14` vs `README.md:312` |
| 2 | IAPWS R10-06 URL mismatch (code vs docs) | MEDIUM | `ice_ih_density.py:12` vs `README.md:316` |
| 3 | IAPWS-95 missing from user-facing docs | LOW | `water_density.py:13-16` (code only) |
| 4 | Journaux et al. missing from README | MEDIUM | `ice_boundaries.py:15-16` (code only) |
| 5 | CODATA 2017 no formal citation | LOW | `ion_inserter.py:27`, `scorer.py:168` |
| 6 | LSBU data no URL/formal citation | LOW | `ice_boundaries.py:26` |
| 7 | "calcution" typo in gui-guide | LOW | `docs/gui-guide.md:260` |
| 8 | ice_v, ice_vii: "No specific citation" in _get_citation() | LOW | `main_window.py:1953,1955` |
| 9 | solute_inserter.py AVOGADRO missing CODATA tag | LOW | `solute_inserter.py:32` |
| 10 | Lobban et al. not in _get_citation() for ice_v | LOW | `docs/principles.md:208` vs `main_window.py:1953` |

---

*Inventory generated: 2026-05-22*
