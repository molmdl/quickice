# Documentation Issues Verification Report

**Analysis Date:** 2026-05-16
**Focus:** Investigate three documentation discrepancies identified in prior analysis

---

## Issue 1: Ice Phase Documentation (12 vs 8)

### Claim
Documentation shows confusion between "12 detectable phases" and "8 generatable phases"

### Investigation Findings

**Phase Detection (12 phases):**
- Location: `quickice/phase_mapping/lookup.py:27-46`
- `PHASE_METADATA` dictionary contains 12 phases:
  - ice_ih, ice_ic, ice_ii, ice_iii, ice_v, ice_vi, ice_vii, ice_viii (8 standard polymorphs)
  - ice_xi (proton-ordered Ih)
  - ice_ix (proton-ordered III)
  - ice_xv (proton-ordered VI)
  - ice_x (symmetric hydrogen bonds)
- These are phases that can be **identified/detected** from temperature and pressure conditions

**Phase Generation (8 phases):**
- Location: `quickice/structure_generation/mapper.py:10-19`
- `PHASE_TO_GENICE` dictionary contains 8 phases:
  - ice_ih → "ice1h"
  - ice_ic → "ice1c"
  - ice_ii → "ice2"
  - ice_iii → "ice3"
  - ice_v → "ice5"
  - ice_vi → "ice6"
  - ice_vii → "ice7"
  - ice_viii → "ice8"
- These are phases that can be **generated** via GenIce2

**GenIce2 Coverage (18 phases available):**
- Location: `.planning/research/GENICE2_COVERAGE_REPORT.md:64-95`
- GenIce2 supports 18 standard ice phases (1h, 1c, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18)
- QuickIce only exposes 8 of these

**README Documentation:**
- Location: `README.md:226-247`
- States "12 ice polymorphs" and lists all 12
- Does NOT clarify the detect vs generate distinction
- Line 247 correctly notes: "Interface construction: All phases except Ice II work with Tab 2 interface generation"

### Gap Analysis

| Phase | Can Detect | Can Generate | Notes |
|-------|------------|--------------|-------|
| Ice Ih | ✓ | ✓ | Standard hexagonal ice |
| Ice Ic | ✓ | ✓ | Cubic ice |
| Ice II | ✓ | ✓ | Rhombohedral (interface issues) |
| Ice III | ✓ | ✓ | Tetragonal |
| Ice IV | ✗ | ✗ | Available in GenIce2, not exposed |
| Ice V | ✓ | ✓ | Monoclinic |
| Ice VI | ✓ | ✓ | Tetragonal double network |
| Ice VII | ✓ | ✓ | Cubic |
| Ice VIII | ✓ | ✓ | Ordered VII |
| Ice IX | ✓ | ✗ | Ordered III (GenIce2 has ice9) |
| Ice XI | ✓ | ✗ | Ordered Ih (GenIce2 has ice11) |
| Ice XV | ✓ | ✗ | Ordered VI (GenIce2 has ice15) |
| Ice X | ✓ | ✗ | Symmetric H-bonds (extreme pressure) |

**The Confusion:**
1. README claims "12 ice polymorphs" without distinguishing detection from generation
2. Users selecting Ice XI, Ice IX, Ice XV, or Ice X from phase diagram will see phase info but CANNOT generate structures
3. GenIce2 actually supports 18 phases, but QuickIce only exposes 8

### Recommended Fix

**Update README.md line 226-247:**

```markdown
## Supported Ice Phases

QuickIce supports 12 ice polymorphs for phase detection and 8 for structure generation:

### Phase Detection (12 phases)

The interactive phase diagram can identify 12 ice polymorphs based on T/P conditions:

| Phase | Crystal System | Pressure Range | Temperature Range |
|-------|----------------|----------------|-------------------|
| Ice Ih | Hexagonal | 0-200 MPa | 0-273K |
| Ice Ic | Cubic | Low pressure | < 150K |
| Ice II | Rhombohedral | 200-600 MPa | < 250K |
| Ice III | Tetragonal | 200-400 MPa | 250-260K |
| Ice V | Monoclinic | 400-600 MPa | 250-270K |
| Ice VI | Tetragonal | 600-2000 MPa | 250-350K |
| Ice VII | Cubic | > 2000 MPa | 273-355K |
| Ice VIII | Ordered VII | > 2000 MPa | < 273K |
| Ice IX | Ordered III | 200-400 MPa | < 175K |
| Ice XI | Ordered Ih | Low pressure | < 72K |
| Ice XV | Ordered VI | 600-2000 MPa | < 130K |
| Ice X | Symmetric | > 40 GPa | > 273K |

### Structure Generation (8 phases)

GenIce2 can generate atomic structures for 8 phases:

| Phase | Generate | Notes |
|-------|----------|-------|
| Ice Ih | ✓ | |
| Ice Ic | ✓ | |
| Ice II | ✓ | Interface construction limited (rhombohedral) |
| Ice III | ✓ | |
| Ice V | ✓ | |
| Ice VI | ✓ | |
| Ice VII | ✓ | |
| Ice VIII | ✓ | |

**Note:** Ice IX, XI, XV, and X are detected in the phase diagram but cannot be generated. Users selecting these phases will see phase information but no candidates will be generated.
```

### Confidence Level
**HIGH** — Direct code inspection of `mapper.py` and `lookup.py` confirms the 8/12 split.

---

## Issue 2: Madrid2019 Ion Model Citation

### Claim
Madrid2019 ion model is used in Tab 5 (Ion insertion) but not cited in documentation

### Investigation Findings

**Code Usage:**
- Location: `quickice/structure_generation/gromacs_ion_export.py:9-27`
- Parameters defined:
  - `NA_CHARGE = 0.85`
  - `CL_CHARGE = -0.85`
  - VDW parameters (sigma, epsilon) from `Madrid2019_085.top`
- File header (line 4): "with GROMACS standard atom types (Na+/Cl- from Madrid2019)"

**Source Topology:**
- Location: `.planning/phases/28.1-urgent-bugfixes-ff-corrections/ff/madrid2019_085.top`
- Contains full Madrid2019 force field with all ion parameters
- Na charge: 0.8500, Cl charge: -0.8500 (line 7, 15)

**Current Documentation:**
- `docs/gui-guide.md:790`: "Madrid2019 force field parameters used (Na⁺ charge = +0.85, Cl⁻ charge = -0.85)"
- `README.md:169`: "Equal Na⁺/Cl⁻ with Madrid2019 parameters (±0.85e)"
- `quickice/gui/ion_panel.py:467`: "# Madrid2019 ion charges: Na+ = +0.85, Cl- = -0.85"

**Citation Found:**
The correct citation was located in `.planning/code_analysis/20260512_154906_documentation_crosscheck.md:201-207`:

```
Zeron, I. M., Abascal, J. L. F., & Vega, C. (2019). 
A force field of Li+, Na+, K+, Mg2+, Ca2+, Cl−, and SO4 2− in aqueous solution 
based on ion–water polarizability, dielectric constant, and viscosity.
Journal of Chemical Physics, 151(13), 134504.
DOI: https://doi.org/10.1063/1.5121392
```

### Gap Analysis

| Location | Has Parameter Name | Has Citation | Status |
|----------|-------------------|--------------|--------|
| README.md | ✓ | ✗ | Missing |
| docs/gui-guide.md | ✓ | ✗ | Missing |
| ion_panel.py | ✓ | ✗ | Code comment only |

### Recommended Fix

**Add to README.md References section (after line 308):**

```markdown
### Madrid2019 Ion Parameters
- Zeron, I. M., Abascal, J. L. F., & Vega, C. (2019).
  A force field of Li+, Na+, K+, Mg2+, Ca2+, Cl−, and SO4 2− in aqueous solution based on ion–water polarizability, dielectric constant, and viscosity.
  Journal of Chemical Physics, 151(13), 134504.
  DOI: https://doi.org/10.1063/1.5121392
```

**Update docs/gui-guide.md line 790:**

```markdown
- Madrid2019 force field parameters used (Na⁺ charge = +0.85, Cl⁻ charge = -0.85)
  - Citation: Zeron, I. M., Abascal, J. L. F., & Vega, C. (2019). J. Chem. Phys. 151, 134504.
  - DOI: https://doi.org/10.1063/1.5121392
```

### Confidence Level
**HIGH** — Citation verified from planning documents and matches the force field parameters in code.

---

## Issue 3: Hydrate Guests (CO2/H2 vs CH4/THF)

### Claim
Code mentions CO2/H2 as hydrate guests but documentation only lists CH4/THF

### Investigation Findings

**GUEST_MOLECULES Definition:**
- Location: `quickice/structure_generation/types.py:76-91`
- Only contains:
  ```python
  GUEST_MOLECULES = {
      "ch4": {"name": "Methane", "formula": "CH₄", ...},
      "thf": {"name": "Tetrahydrofuran", "formula": "C₄H₈O", ...},
  }
  ```

**Docstring Claim:**
- Location: `quickice/structure_generation/hydrate_generator.py:37`
- States: "Supports sI, sII, sH hydrate lattices with configurable guest molecules (CH4, THF, CO2, H2)"
- **This is INCORRECT** — CO2 and H2 are NOT implemented

**GUI Dropdown:**
- Location: `quickice/gui/hydrate_panel.py:194-199`
- Populates dropdown from `GUEST_MOLECULES.items()`
- Users only see: CH₄ (Methane) and THF (Tetrahydrofuran)

**Documentation:**
- `README.md:119`: "Guest molecules — CH₄ (methane), THF (tetrahydrofuran)"
- `docs/gui-guide.md:231`: "Choose guest molecules (CH₄, THF)"
- `docs/gui-guide.md:252-256`: Table showing only CH₄ and THF

**GenIce2 Capabilities:**
- Location: `.planning/research/GENICE2_COVERAGE_REPORT.md:144-150`
- GenIce2 supports 10+ guest molecules including CO2, H2
- QuickIce documentation crosscheck (line 350) noted: "CO2/H2 implemented but not documented"
- **This is WRONG** — they are NOT implemented, only mentioned in a docstring

### Gap Analysis

| Source | Lists CH4 | Lists THF | Lists CO2 | Lists H2 |
|--------|-----------|-----------|-----------|----------|
| types.py (GUEST_MOLECULES) | ✓ | ✓ | ✗ | ✗ |
| hydrate_generator.py docstring | ✓ | ✓ | ✓ | ✓ |
| hydrate_panel.py GUI | ✓ | ✓ | ✗ | ✗ |
| README.md | ✓ | ✓ | ✗ | ✗ |
| docs/gui-guide.md | ✓ | ✓ | ✗ | ✗ |

**The Problem:**
The `hydrate_generator.py` docstring is outdated/incorrect. It claims support for CO2 and H2, but:
1. These are not in `GUEST_MOLECULES` dictionary
2. They are not available in the GUI dropdown
3. They cannot be generated or exported

### Recommended Fix

**Fix hydrate_generator.py docstring (line 36-38):**

```python
class HydrateStructureGenerator:
    """Generator for hydrate structures using GenIce2.
    
    Supports sI, sII, sH hydrate lattices with configurable guest molecules
    (CH4, THF). Additional guests (CO2, H2) are available in GenIce2 but
    not currently exposed in QuickIce GUI.
    """
```

**OR** — If CO2/H2 support is desired:

1. Add to `GUEST_MOLECULES` in `types.py`:
   ```python
   "co2": {
       "name": "Carbon Dioxide",
       "formula": "CO₂",
       "atoms": 3,
       "description": "CO2 guest molecule",
       "force_field": "GAFF/GAFF2",
   },
   "h2": {
       "name": "Hydrogen",
       "formula": "H₂",
       "atoms": 2,
       "description": "H2 guest molecule",
       "force_field": "GAFF/GAFF2",
   },
   ```

2. Add corresponding `.itp` files to `quickice/data/` directory

3. Update documentation to include CO2 and H2

### Confidence Level
**HIGH** — Direct code inspection confirms only CH4 and THF are implemented. The docstring is misleading.

---

## Summary

| Issue | Claim | Finding | Confidence | Priority |
|-------|-------|---------|------------|----------|
| Ice Phases | 12 vs 8 confusion | 12 detectable, 8 generatable | HIGH | Medium |
| Madrid2019 Citation | Missing citation | Citation found in planning docs | HIGH | High |
| Hydrate Guests | CO2/H2 claimed but not documented | CO2/H2 NOT implemented (docstring error) | HIGH | Medium |

### Immediate Actions Required

1. **Madrid2019 Citation** — Add citation to README.md and gui-guide.md (High priority)
2. **Hydrate Docstring** — Fix incorrect docstring in hydrate_generator.py (Medium priority)
3. **Phase Clarification** — Update README.md to clarify detect vs generate distinction (Medium priority)

---

*Report generated: 2026-05-16*
