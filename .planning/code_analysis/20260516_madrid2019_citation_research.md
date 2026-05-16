# Madrid2019 Ion Model Citation Research

**Date:** 2026-05-16
**DOI Verified:** 10.1063/1.5121392
**Confidence:** HIGH (verified via arXiv and DOI resolver)

---

## 1. Correct Citation for DOI 10.1063/1.5121392

### Full Citation

**Title:** A force field of Li+, Na+, K+, Mg2+, Ca2+, Cl−, and SO42− in aqueous solution based on the TIP4P/2005 water model and scaled charges for the ions

**Authors:** I. M. Zeron, J. L. F. Abascal, C. Vega

**Journal:** Journal of Chemical Physics, 151, 134504 (2019)

**DOI:** https://doi.org/10.1063/1.5121392

**arXiv:** https://arxiv.org/abs/2401.13164

---

## 2. Title Comparison

| | Title |
|---|---|
| **WRONG (currently claimed)** | A force field of Li+, Na+, K+, Mg2+, Ca2+, Cl−, and SO4 2− in aqueous solution based on ion–water polarizability, dielectric constant, and viscosity |
| **CORRECT** | A force field of Li+, Na+, K+, Mg2+, Ca2+, Cl−, and SO42− in aqueous solution based on the TIP4P/2005 water model and scaled charges for the ions |

**Key differences:**
- Wrong title claims basis in "ion–water polarizability, dielectric constant, and viscosity"
- Correct title specifies "TIP4P/2005 water model and scaled charges for the ions"
- The correct title accurately describes the methodology used in the paper

---

## 3. Parameter Verification

### Paper Parameters

From the paper abstract:
> "Monovalent and divalent ions are modeled using charges of **0.85** and **1.7**, respectively (in electron units)."

> "For water, we use the **TIP4P/2005** model."

### QuickIce Implementation (from `madrid2019_085.top`)

| Ion | Charge in Paper | Charge in .top file | Match |
|-----|-----------------|---------------------|-------|
| Na+ | +0.85 e | 0.8500 | ✓ |
| Cl- | -0.85 e | -0.8500 | ✓ |
| K+ | +0.85 e | 0.8500 | ✓ |
| Li+ | +0.85 e | 0.8500 | ✓ |
| Mg2+ | +1.7 e | 1.7 | ✓ |
| Ca2+ | +1.7 e | 1.7 | ✓ |
| Water | TIP4P/2005 | OWT4 (TIP4P/2005 oxygen) | ✓ |

**Conclusion:** The parameters in QuickIce match the Madrid-2019 paper exactly.

---

## 4. "Madrid2019" Naming Verification

The paper explicitly states:
> "The force field proposed **(denoted as Madrid-2019)** is nonpolarizable..."

This confirms the naming convention used in QuickIce (`madrid2019_085.top`) is correct.

The Madrid group (Vega, Abascal et al.) is from Universidad Complutense de Madrid, hence the naming.

---

## 5. Extended Madrid-2019 Force Field

For ions not in the original paper (F−, Br−, I−, Rb+, Cs+), there is an extension paper:

**Title:** The Madrid-2019 force field for electrolytes in water using TIP4P/2005 and scaled charges: extension to the ions F−, Br−, I−, Rb+, Cs+

**Authors:** Samuel Blazquez, Maria M. Conde, Jose L. F. Abascal, Carlos Vega

**Journal:** Journal of Chemical Physics, 156, 044505 (2022)

**DOI:** https://doi.org/10.1063/5.0077716

The `.top` file includes these extended ions with ±0.85 charges, consistent with the extended Madrid-2019 model.

---

## 6. Recommended Citation for Documentation

### For the Madrid-2019 Ion Force Field

```bibtex
@article{Zeron2019,
  author  = {Zeron, I. M. and Abascal, J. L. F. and Vega, C.},
  title   = {A force field of Li+, Na+, K+, Mg2+, Ca2+, Cl−, and SO42− in aqueous solution based on the TIP4P/2005 water model and scaled charges for the ions},
  journal = {Journal of Chemical Physics},
  volume  = {151},
  pages   = {134504},
  year    = {2019},
  doi     = {10.1063/1.5121392}
}
```

### For Extended Ions (F−, Br−, I−, Rb+, Cs+)

```bibtex
@article{Blazquez2022,
  author  = {Blazquez, Samuel and Conde, Maria M. and Abascal, Jose L. F. and Vega, Carlos},
  title   = {The Madrid-2019 force field for electrolytes in water using TIP4P/2005 and scaled charges: extension to the ions F−, Br−, I−, Rb+, Cs+},
  journal = {Journal of Chemical Physics},
  volume  = {156},
  pages   = {044505},
  year    = {2022},
  doi     = {10.1063/5.0077716}
}
```

---

## 7. Summary

| Question | Answer |
|----------|--------|
| Is DOI 10.1063/1.5121392 correct? | ✓ Yes |
| Was the title wrong? | ✓ Yes - wrong suffix describing methodology |
| Does this match Na+/Cl- parameters? | ✓ Yes - ±0.85 e charges match |
| Is "Madrid2019" the correct name? | ✓ Yes - explicitly stated in paper |
| What to add to docs? | The correct citation above |

---

## Sources

1. **DOI Resolver** (https://doi.org/10.1063/1.5121392) - HIGH confidence
2. **arXiv** (https://arxiv.org/abs/2401.13164) - HIGH confidence, matches DOI
3. **.top file analysis** (`madrid2019_085.top`) - Parameters verified
4. **arXiv search** - Confirmed Madrid-2019 naming convention in abstract
