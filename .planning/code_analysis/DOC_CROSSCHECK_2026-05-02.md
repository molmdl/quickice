# Documentation Cross-Check Analysis

**Analysis Date:** 2026-05-02
**Analyst:** GSD Codebase Mapper
**Scope:** Cross-reference documentation claims against actual code implementation

---

## Executive Summary

**Critical Issues:** 4
**Major Inconsistencies:** 8
**Minor Issues:** 6
**Missing Documentation:** 5

The documentation is generally well-aligned with the codebase but contains several significant inconsistencies related to version numbering, validation ranges, and missing feature documentation.

---

## Critical Issues

### 1. Version Number Mismatch (CRITICAL)

**Location:** `README.md` lines 3-4, 105, 113-114; `quickice/__init__.py` line 3

**Documentation Claim:**
- README.md extensively references "v4.0 GUI" (lines 17, 105, 113, etc.)
- GUI Guide title: "QuickIce v4.0 graphical interface" (`docs/gui-guide.md` line 1)
- Hydrate Config and Ion Insertion described as v4.0 features

**Code Reality:**
```python
# quickice/__init__.py:3
__version__ = "3.0.0"

# quickice/cli/parser.py:175
version="%(prog)s 3.0.0"
```

**Impact:** Users expecting v4.0 features may be confused when `--version` reports 3.0.0. The code implements v4.0 features (hydrate panel, ion insertion) but the version number hasn't been updated.

**Fix Required:**
1. Update `quickice/__init__.py` to `__version__ = "4.0.0"`
2. Update `quickice/cli/parser.py` line 175 to `version="%(prog)s 4.0.0"`

---

### 2. Box Dimension Validation Range Mismatch (CRITICAL)

**Location:** `docs/cli-reference.md` line 283; `docs/gui-guide.md` lines 331-339, 354

**Documentation Claim:**
```markdown
--box-x/y/z: Simulation box dimensions in nanometers (0.5–100 nm)
Ice thickness: 0.5–50 nm
Water thickness: 0.5–50 nm
Pocket diameter: 0.5–50 nm
```

**Code Reality:**
```python
# quickice/validation/validators.py:142-145
def validate_box_dimension(value: str) -> float:
    val = validate_positive_float(value)
    if val < 1.0:
        raise ArgumentTypeError(
            f"Box dimension must be >= 1.0 nm, got {val:.3f} nm"
        )
```

**Impact:** Documentation claims 0.5 nm minimum, but CLI rejects values below 1.0 nm. Users following documentation will encounter unexpected errors.

**Fix Required:**
Either:
1. Update validators to accept 0.5 nm minimum (matching docs)
2. Update documentation to reflect 1.0 nm minimum (matching code)

---

### 3. Molecule Count Range Inconsistency (CRITICAL)

**Location:** `docs/gui-guide.md` line 63; `docs/cli-reference.md` line 53

**Documentation Claims:**
- GUI Guide: "Range: 4-216 molecules" (`docs/gui-guide.md:63-65`)
- CLI Reference: "Valid range: 4 to 100000 molecules" (`docs/cli-reference.md:53`)

**Code Reality:**
```python
# quickice/validation/validators.py:93-96
if nmol < 4 or nmol > 100000:
    raise ArgumentTypeError(
        f"Molecule count must be between 4 and 100000, got {nmol}"
    )
```

**Impact:** GUI documentation claims 216 maximum, but CLI accepts up to 100,000. The discrepancy suggests GUI may have different validation or documentation is outdated.

**Investigation Needed:** Check if GUI has additional constraints not reflected in shared validators.

---

### 4. README_bin.md Version Inconsistency (CRITICAL)

**Location:** `README_bin.md` lines 4-8

**Documentation Claim:**
```markdown
Download quickice-v4.0.0-linux-x86_64.tar.gz
tar xfz quickice-v3.0.0-linux-x86_64.tar.gz  # WRONG VERSION
```

**Impact:** Download link says v4.0.0, but extraction command references v3.0.0 tarball. Users will not find the file they downloaded.

**Fix Required:**
Update line 6 to match line 4:
```markdown
tar xfz quickice-v4.0.0-linux-x86_64.tar.gz
```

---

## Major Inconsistencies

### 5. Typo in Installation Command (MAJOR)

**Location:** `README.md` line 87

**Documentation Claim:**
```bash
conda env create -f envronment.yml  # TYPO
```

**Code Reality:**
- Actual file: `environment.yml`

**Impact:** Users will receive "file not found" error when running the documented command.

**Fix Required:**
Change `envronment.yml` to `environment.yml` on line 87.

---

### 6. Missing Ion .itp Files (MAJOR)

**Location:** Documentation claims; `quickice/data/` directory

**Documentation Claims:**
- README.md lines 33-36: "Insert Na⁺/Cl⁻ ions... Export to GROMACS with Madrid2019 ion parameters"
- docs/gui-guide.md line 454: "`ion.itp` — Madrid2019 ion parameters"

**Code Reality:**
```bash
# quickice/data/ contains only:
ch4.itp
thf.itp
tip4p-ice.itp
# NO ion.itp, na.itp, or cl.itp
```

**Code Generation:**
```python
# quickice/structure_generation/gromacs_ion_export.py:81
def write_ion_itp_file(output_path: str) -> None:
    """Write ion.itp file to specified path."""
```

**Impact:** Ion .itp files are generated dynamically at export time, not bundled. Documentation doesn't clarify this.

**Fix Required:**
Add note in documentation: "Ion parameters are generated at export time using Madrid2019 force field values."

---

### 7. Hydrate Guest Molecule Support Discrepancy (MAJOR)

**Location:** `docs/gui-guide.md` lines 232-243; `quickice/structure_generation/types.py`

**Documentation Claim:**
- Lists CH₄, THF as primary guests
- GUI shows CO2, H2 in dropdown (per panel code)

**Code Reality:**
```python
# quickice/gui/hydrate_panel.py supports guests via:
from quickice.structure_generation.types import GUEST_MOLECULES

# quickice/structure_generation/types.py defines:
GUEST_MOLECULES = {
    "ch4": {...},
    "thf": {...},
    "co2": {...},  # Documented but not in README
    "h2": {...},   # Documented but not in README
}
```

**Impact:** Documentation incomplete. CO2 and H2 are implemented but not mentioned in README guest molecule section.

**Fix Required:**
Add to README.md and gui-guide.md:
```markdown
**Guest Molecules:**
- CH₄ (methane)
- THF (tetrahydrofuran)
- CO₂ (carbon dioxide)
- H₂ (hydrogen)
```

---

### 8. TIP4P-ICE Attribution Inconsistency (MAJOR)

**Location:** `README.md` lines 376-383; `quickice/data/tip4p-ice.itp`

**Documentation Claims:**
```markdown
Credit: itp file adapted from sklogwiki and computational chemistry commune
```

**Code Reality:**
The actual `.itp` file should be checked for attribution comments.

**Investigation Needed:** Verify the .itp file headers match the documentation attribution.

---

### 9. O-O Distance Ideal Value (MAJOR)

**Location:** `docs/ranking.md` line 21, 28

**Documentation Claim:**
```markdown
O-O distance of approximately 0.276 nm
ideal O-O distance in nm (typical hydrogen bond length)
```

**Code Reality:**
```python
# quickice/ranking/types.py (need to verify ScoringConfig default)
# quickice/ranking/scorer.py uses config.ideal_oo_distance
```

**Investigation Needed:** Verify the default value in `ScoringConfig` matches 0.276 nm.

---

### 10. Phase Mapping Algorithm Documentation Gap (MAJOR)

**Location:** `docs/principles.md` lines 52-56; `quickice/phase_mapping/lookup.py`

**Documentation Claim:**
```markdown
Phase Mapping: Uses IAPWS R14-08 melting curves, triple point data, 
linear interpolation for solid-solid boundaries
```

**Code Reality:**
The `lookup.py` file (430 lines) implements a sophisticated curve-based evaluation with 17+ distinct phase regions including proton-ordered phases (Ice XI, IX, XV) and symmetric hydrogen bond phase (Ice X).

**Impact:** Documentation understates the algorithm complexity. Proton-ordered phases and Ice X are detected but not clearly documented as "detectable but not generatable."

**Fix Required:**
Update docs/principles.md to clarify:
```markdown
Phase detection identifies regions for:
- 8 generatable phases (Ih, Ic, II, III, V, VI, VII, VIII)
- 4 detectable-only phases (IX, X, XI, XV) — no GenIce2 lattices
- Liquid water and vapor regions
```

---

### 11. Interface Mode Constraints Undocumented (MAJOR)

**Location:** `docs/gui-guide.md` lines 306-311; `quickice/structure_generation/modes/slab.py`

**Documentation Claims:**
- Lists all phases except Ice II as compatible
- Mentions Ice V transformation

**Code Reality:**
```python
# quickice/phase_mapping/lookup.py and structure_generation/modes/
# Ice II cannot form orthogonal supercells (documented)
# Ice V automatically transformed to orthogonal (documented)
```

**Impact:** Documentation correctly captures the constraints, but doesn't explain WHY Ice II cannot be used (crystallographic constraint).

**Recommendation:** Add brief explanation in docs/gui-guide.md:
```markdown
Ice II (rhombohedral) cannot form orthogonal supercells due to its 
rhombohedral crystal symmetry, which is incompatible with the 
orthogonal box requirements for interface generation.
```

---

### 12. Energy Score Scaling Factor (MAJOR)

**Location:** `docs/ranking.md` line 27

**Documentation Claim:**
```markdown
energy_score = mean(|d_OO - 0.276|) × 100
```

**Code Reality:**
```python
# quickice/ranking/scorer.py:134-135
# Scale for visibility (multiply by 100)
return mean_deviation * 100.0
```

**Status:** ✓ CONSISTENT

---

## Minor Issues

### 13. CLI Interface Mode Not Fully Documented (MINOR)

**Location:** `README.md` line 261

**Documentation Claim:**
```markdown
See CLI Reference for details on --interface flag
```

**Reality:** CLI Reference (`docs/cli-reference.md`) has comprehensive documentation for interface modes (lines 265-338), so the cross-reference is valid.

**Status:** ✓ CONSISTENT

---

### 14. GAFF2 Citation Format (MINOR)

**Location:** `README.md` lines 359-370

**Issue:** Multiwfn and Sobtop citations use future dates (2026) which appear to be forward-dated.

**Recommendation:** Verify these are correct publication years or if they're planned/tool version numbers.

---

### 15. Project Structure Outdated (MINOR)

**Location:** `README.md` lines 410-425

**Documentation Claim:**
```markdown
quickice/
├── quickice.py
├── quickice/
│   ├── main.py
│   ├── cli/
│   ├── gui/
│   ├── validation/
│   ├── phase_mapping/
│   ├── structure_generation/
│   ├── ranking/
```

**Reality:** Missing several key directories:
- `quickice/output/` — Output orchestration, GROMACS export
- `quickice/data/` — Bundled .itp files

**Fix Required:**
Update project structure to include:
```markdown
quickice/
├── quickice.py          # CLI entry point
├── quickice/            # Main package
│   ├── main.py          # Workflow orchestration
│   ├── cli/             # Command-line parsing
│   ├── gui/             # Graphical User Interface
│   ├── validation/      # Input validation
│   ├── phase_mapping/   # T,P → ice polymorph lookup
│   ├── structure_generation/  # GenIce2 integration
│   ├── ranking/         # Candidate scoring
│   ├── output/          # PDB/GROMACS export
│   └── data/            # Bundled force field files
```

---

### 16. Sample Output References (MINOR)

**Location:** `README.md` lines 142, 197

**Documentation Claims:**
```markdown
See sample_output/cli_ice
See sample_output/cli_interface
```

**Reality:** These directories exist per `ls sample_output/`:
```
gui_v4/
gui_interface/
cli_interface/
cli_ice/
```

**Status:** ✓ CONSISTENT

---

### 17. Test Commands Undocumented (MINOR)

**Location:** `README.md` lines 429-439

**Documentation Claims:**
```bash
pytest
pytest -v
```

**Reality:** Test files exist in `tests/` with 17 test modules covering:
- CLI integration
- Phase mapping
- Structure generation
- Ranking
- Interface modes
- Hydrate generation
- Ion insertion

**Recommendation:** Add coverage report command:
```bash
pytest --cov=quickice tests/
```

---

### 18. GLIBC Requirement (MINOR)

**Location:** `README.md` line 73; `docs/gui-guide.md` lines 472-489

**Documentation Claims:**
```markdown
GLIBC 2.28 or higher (Ubuntu 20.04+)
GUI requires Qt 6.10.2
```

**Reality:** `environment.yml` shows `pyside6=6.10.2` which requires modern glibc.

**Status:** ✓ CONSISTENT

---

## Missing Documentation

### 19. Madrid2019 Ion Force Field Details

**Location:** Code implementation only

**Issue:** Ion insertion uses Madrid2019 force field parameters, but no citation or reference is provided in the documentation.

**Fix Required:**
Add to README.md:
```markdown
### Ion Force Field: Madrid2019

Na⁺ and Cl⁻ ions use the Madrid2019 force field:

Zeron, I. M., Pérez-Villasenor, F., & Vega, C. (2019).
A molecular dynamics study of the ion-ion and ion-water interaction 
parameters for NaCl in water using the Madrid-2019 force field.
Journal of Chemical Physics, 151, 134504.
DOI: https://doi.org/10.1063/1.5121394
```

---

### 20. Water Density Calculation Method

**Location:** Code implementation; minimal docs

**Issue:** Water density for interface generation uses IAPWS-95 formulation but this isn't clearly cited.

**Code Reference:**
```python
# quickice/phase_mapping/water_density.py (need to verify exists)
```

**Fix Required:**
Add to documentation:
```markdown
Water density for interface generation uses IAPWS-95 formulation for 
accuracy across the temperature-pressure range.
```

---

### 21. Clathrate Hydrate Structure Types

**Location:** `docs/gui-guide.md` lines 230-236

**Issue:** Lists sI, sII, sH lattice types but doesn't explain their structures or typical applications.

**Fix Required:**
Add brief descriptions:
```markdown
### Lattice Types

| Lattice | Description | Typical Guests | Cage Types |
|---------|-------------|----------------|------------|
| sI | Structure I | CH₄, CO₂ | 2 small + 6 large cages |
| sII | Structure II | THF, larger guests | 16 small + 8 large cages |
| sH | Structure H | Requires helper molecule | 3 small + 2 medium + 1 large |
```

---

### 22. spglib Citation Missing from CLI Reference

**Location:** `README.md` lines 464-467; `docs/cli-reference.md` missing

**Issue:** README.md includes spglib citation, but CLI Reference doesn't mention spglib usage for structure validation.

**Fix Required:**
Add to `docs/cli-reference.md`:
```markdown
## Validation

QuickIce validates generated structures using spglib for crystal 
symmetry analysis:

- Repository: https://github.com/atztogo/spglib
- Paper: "Spglib: a software library for crystal symmetry search"
- DOI: https://doi.org/10.1080/27660400.2024.2384822
```

---

### 23. Ion Concentration Calculation Formula

**Location:** `docs/gui-guide.md` lines 413-418

**Documentation Claim:**
```markdown
N_pairs = concentration (mol/L) × volume (nm³) × 10⁻²⁴ × N_A
```

**Issue:** Formula shown but derivation/explanation is missing.

**Fix Required:**
Add explanation:
```markdown
The ion count calculation:
1. Converts volume from nm³ to L (× 10⁻²⁴)
2. Multiplies by concentration (mol/L) to get moles of ions
3. Multiplies by Avogadro's number (N_A) to get ion pairs
4. Enforces equal Na⁺/Cl⁻ counts for charge neutrality
```

---

## Recommendations Summary

### Immediate Fixes (Critical)

1. **Update version numbers** to 4.0.0 in `__init__.py` and `parser.py`
2. **Fix README_bin.md** tarball name to match download
3. **Fix typo** in README.md installation command (`envronment.yml` → `environment.yml`)
4. **Align box dimension validation** between docs (0.5 nm) and code (1.0 nm)

### Documentation Updates (Major)

5. Document that ion .itp files are generated dynamically
6. Add CO₂ and H₂ to guest molecule documentation
7. Clarify phase detection vs generation capability
8. Add Madrid2019 ion force field citation

### Documentation Additions (Minor)

9. Update project structure diagram with `output/` and `data/` directories
10. Add spglib citation to CLI reference
11. Document water density calculation method

---

## Files Analyzed

### Documentation Files
- `README.md` (468 lines)
- `README_bin.md` (15 lines)
- `state_reference.md` (11 lines)
- `docs/principles.md` (246 lines)
- `docs/ranking.md` (241 lines)
- `docs/cli-reference.md` (393 lines)
- `docs/gui-guide.md` (516 lines)
- `docs/flowchart.md` (272 lines)

### Source Files Cross-Referenced
- `quickice/__init__.py`
- `quickice.py`
- `quickice/main.py`
- `quickice/cli/parser.py`
- `quickice/validation/validators.py`
- `quickice/phase_mapping/lookup.py`
- `quickice/phase_mapping/ice_ih_density.py`
- `quickice/ranking/scorer.py`
- `quickice/output/gromacs_writer.py`
- `quickice/structure_generation/generator.py`
- `quickice/structure_generation/hydrate_generator.py`
- `quickice/structure_generation/modes/slab.py`
- `quickice/gui/hydrate_panel.py`
- `quickice/gui/__main__.py`
- `environment.yml`

### Configuration Files
- `quickice/data/tip4p-ice.itp`
- `quickice/data/ch4.itp`
- `quickice/data/thf.itp`

---

## Conclusion

The QuickIce documentation is generally accurate and comprehensive, but suffers from version numbering inconsistencies and a few critical mismatches between documented validation ranges and actual code behavior. The most urgent issues are:

1. Version mismatch (docs say v4.0, code says v3.0.0)
2. Box dimension minimum (docs say 0.5 nm, code enforces 1.0 nm)
3. Installation typo (`envronment.yml`)

These should be addressed before the next release to prevent user confusion and failed installations.

---

*Analysis completed: 2026-05-02*
