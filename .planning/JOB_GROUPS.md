# Job Groups for QuickIce Fixes

**Created:** 2026-05-02
**Purpose:** Group findings from codebase analysis and recommend GSD workflow for each

---

## Overview

| Group | Type | Issues | Workflow | Priority |
|-------|------|--------|----------|----------|
| A | Critical Bugs | 4 | `/gsd-debug` | HIGH |
| B | Quick Fixes | 8 | Quick Task | MEDIUM |
| C | Code Quality | 12 | Insert Phase | MEDIUM |
| D | Documentation | 10 | Quick Task | MEDIUM |
| E | Packaging | 1 | Insert Phase | LOW |
| F | Refactoring | 3 | Insert Phase | LOW |

---

## Group A: Critical Bugs → `/gsd-debug`

**Why debugger:** These are correctness issues that need investigation, root cause analysis, and precise fixes. The debugger workflow provides structured investigation with checkpoints.

### A1. PDB Writer Atom Count Mismatch (HIGH)
**Issue:** `write_interface_pdb_file` assumes 3 atoms per ice molecule, but hydrates have 4 atoms (TIP4P)
**File:** `quickice/output/pdb_writer.py:138-142`
**Impact:** Incorrect PDB output for hydrate structures
**Investigation needed:**
1. Trace how GRO writer handles atoms_per_molecule detection
2. Apply same pattern to PDB writer
3. Test with hydrate structures

### A2. Box Dimension Validation Mismatch (CRITICAL)
**Issue:** Docs say 0.5 nm minimum, code enforces 1.0 nm
**Files:** 
- `docs/cli-reference.md:283` - claims 0.5-100 nm
- `quickice/validation/validators.py:142-145` - enforces >= 1.0 nm
**Investigation needed:**
1. Check which is scientifically correct
2. Either fix code or fix docs
3. Add test for boundary values

### A3. Version Number Mismatch (CRITICAL)
**Issue:** Documentation references v4.0, code reports v3.0.0
**Files:**
- `quickice/__init__.py:3` - `__version__ = "3.0.0"`
- `quickice/cli/parser.py:175` - `version="%(prog)s 3.0.0"`
- `README.md` - references v4.0 throughout
**Fix:** Decide version, update all locations

### A4. README_bin.md Tarball Name Mismatch
**Issue:** Download link says v4.0.0, extraction command says v3.0.0
**File:** `README_bin.md:4-8`
**Fix:** Align version numbers

---

## Group B: Quick Fixes → Quick Task Session

**Why quick task:** Single-line or few-line fixes that don't require investigation or planning. Can be done in one session.

### B1. Installation Typo
**File:** `README.md:87`
**Fix:** `envronment.yml` → `environment.yml`

### B2. Remove Unused Self-Import
**File:** `quickice/output/gromacs_writer.py:11`
**Fix:** Remove `import quickice`

### B3. Remove Duplicate Comment Lines (12 lines)
**Files:**
- `quickice/phase_mapping/data/ice_boundaries.py:23-25` (2 lines)
- `quickice/structure_generation/modes/pocket.py:16-18` (2 lines)
- `quickice/structure_generation/modes/slab.py:16-18` (2 lines)
- `quickice/structure_generation/water_filler.py:137-139` (2 lines)
- `quickice/gui/molecular_viewer.py:29-31` (2 lines)
- `quickice/gui/hydrate_renderer.py:25-27` (2 lines)

### B4. Add Madrid2019 Citation
**File:** `README.md` (add section)
**Content:**
```markdown
### Ion Force Field: Madrid2019

Na⁺ and Cl⁻ ions use the Madrid2019 force field:

Zeron, I. M., Pérez-Villasenor, F., & Vega, C. (2019).
A molecular dynamics study of the ion-ion and ion-water interaction 
parameters for NaCl in water using the Madrid-2019 force field.
Journal of Chemical Physics, 151, 134504.
DOI: https://doi.org/10.1063/1.5121394
```

### B5. Add CO₂ and H₂ to Guest Molecule Docs
**Files:** `README.md`, `docs/gui-guide.md`
**Add:**
```markdown
**Guest Molecules:**
- CH₄ (methane)
- THF (tetrahydrofuran)
- CO₂ (carbon dioxide)
- H₂ (hydrogen)
```

### B6. Document Ion ITP Generation
**Files:** `README.md:33-36`, `docs/gui-guide.md:454`
**Add note:** "Ion parameters are generated at export time using Madrid2019 force field values."

### B7. Update Project Structure in README
**File:** `README.md:410-425`
**Add missing directories:** `output/`, `data/`

### B8. Add spglib Citation to CLI Reference
**File:** `docs/cli-reference.md`
**Add section:**
```markdown
## Validation

QuickIce validates generated structures using spglib for crystal 
symmetry analysis:

- Repository: https://github.com/atztogo/spglib
- Paper: "Spglib: a software library for crystal symmetry search"
- DOI: https://doi.org/10.1080/27660400.2024.2384822
```

---

## Group C: Code Quality → Insert Phase

**Why phase:** These are systematic improvements that touch multiple files and require testing. Better planned as a dedicated phase.

### C1. Add Logging to Empty Pass Statements
**Scope:** 20+ locations with silent exception handling
**Files:**
- `quickice/phase_mapping/lookup.py:294,418`
- `quickice/structure_generation/hydrate_generator.py:268`
- `quickice/output/phase_diagram.py:231`
- `quickice/output/gromacs_writer.py:229,261`
- `quickice/gui/phase_diagram_widget.py:79,481,495,565`
- `quickice/gui/export.py:122,603`
**Approach:** Add `logger.warning()` or `logger.debug()` calls

### C2. Consolidate Duplicate Molecule Index Building
**Scope:** Duplicate logic in multiple files
**Files:** `quickice/structure_generation/ion_inserter.py:60-134`
**Approach:** Create shared utility in `quickice/structure_generation/utils.py`

### C3. Extract Duplicate Guest Atom Functions
**Scope:** `_count_guest_atoms` and `_count_guest_molecules` duplicated across 3 mode files
**Files:**
- `quickice/structure_generation/modes/piece.py`
- `quickice/structure_generation/modes/pocket.py`
- `quickice/structure_generation/modes/slab.py`
**Savings:** ~60 lines of duplicate code

### C4. Add Unit Validation at Data Entry Points
**Scope:** Prevent unit mismatch (nm vs Å)
**Files:**
- File parsers
- User input handlers
**Approach:** Add explicit unit checks with clear error messages

### C5. Add Bounds Validation for Array Operations
**Scope:** Multiple array indexing without checks
**Files:**
- `quickice/structure_generation/modes/slab.py:577-593`
- `quickice/structure_generation/modes/pocket.py:397-403`
- `quickice/structure_generation/water_filler.py:438-455`

### C6. Fix Nested Loop Performance
**Scope:** PBC handling with 27-cell supercell
**Files:** `quickice/ranking/scorer.py:55-61`
**Approach:** Consider cKDTree `boxsize` parameter

### C7. Add Thread Safety Documentation/Locks
**Scope:** Global state issues
**Files:**
- `quickice/structure_generation/generator.py:96-100`
- `quickice/structure_generation/hydrate_generator.py:27-30`
- `quickice/structure_generation/water_filler.py:228-249`

### C8. Standardize THF Atom Count
**Scope:** Inconsistent documentation (12 vs 13 atoms)
**Files:** `quickice/output/gromacs_writer.py:869-874`

### C9. Fix Parameter Naming Inconsistency
**Scope:** CamelCase in Python
**File:** `quickice/structure_generation/modes/piece.py:50`
**Fix:** `atoms_perMol` → `atoms_per_mol`

### C10. Add Warning for Fallback Density Values
**Scope:** Silent fallback in water density calculation
**File:** `quickice/phase_mapping/water_density.py:67-86`

### C11. Add Comprehensive Type Hints
**Scope:** Missing type hints throughout
**Files:** Multiple, especially `quickice/structure_generation/types.py`

### C12. Clean Up Debug Scripts
**Scope:** Remove or integrate debug files
**Files:**
- `tmp/*.py` (15 scripts, 2276 lines)
- `.planning/debug/resolved/*.py` (13 scripts)

---

## Group D: Documentation Updates → Quick Task Session

**Why quick task:** Documentation changes don't affect code execution, can be done independently.

### D1. Clarify Phase Detection vs Generation
**File:** `docs/principles.md:52-56`
**Add:** Explanation of detectable-only phases (Ice IX, X, XI, XV)

### D2. Add Hydrate Lattice Type Descriptions
**File:** `docs/gui-guide.md:230-236`
**Add:** Table with sI, sII, sH structures and typical guests

### D3. Document Water Density Calculation Method
**Files:** `README.md`, `docs/principles.md`
**Add:** Reference to IAPWS-95 formulation

### D4. Add Ion Concentration Formula Explanation
**File:** `docs/gui-guide.md:413-418`
**Add:** Step-by-step derivation

### D5. Explain Ice II Constraint
**File:** `docs/gui-guide.md:306-311`
**Add:** Why Ice II cannot be used (rhombohedral symmetry incompatible with orthogonal box)

### D6. Update Test Commands in README
**File:** `README.md:429-439`
**Add:** `pytest --cov=quickice tests/`

### D7. Document Hardcoded Default Box Size
**File:** `quickice/structure_generation/hydrate_generator.py:318`
**Add:** Comment explaining 10nm default

### D8. Add VTK Version Requirement
**File:** `README.md`, `environment.yml`
**Note:** VTK 9.5.2 required for molecule rendering

### D9. Document GLIBC Requirement for GUI
**File:** `docs/gui-guide.md:472-489`
**Clarify:** Qt 6.10.2 requires GLIBC 2.28+

### D10. Add Molecule Count Range Investigation Note
**Issue:** GUI docs say 4-216, CLI accepts 4-100000
**File:** `docs/gui-guide.md:63`
**Action:** Verify if GUI has additional constraints

---

## Group E: Packaging Optimization → Insert Phase

**Why phase:** Requires testing of built executable, multiple changes with dependencies.

### E1. Optimize PyInstaller Bundle Size
**Current size:** ~700MB
**Target:** ~500-550MB (22-43% reduction)

**Changes to `quickice-gui.spec`:**

```python
EXCLUDES = [
    # Testing
    'pytest', 'iniconfig', 'pluggy', 'pygments', '_pytest',
    
    # PyInstaller (build-time only)
    'pyinstaller', 'altgraph', 'pyinstaller_hooks_contrib',
    
    # Unused packages
    'gsw',  # Gibbs Sea Water
    'git_filter_repo',
]

RUNTIME_PACKAGES = [
    'vtk', 'vtkmodules',  # Add VTK explicitly
    'iapws', 'genice2', 'genice_core',
    'matplotlib', 'scipy', 'numpy', 
    'shapely', 'networkx', 'spglib',
    'PySide6', 'shiboken6',
]

# Add genice2 plugin hidden imports
hiddenimports += collect_submodules('genice2.plugin')

# Enable optimization
optimize=2
```

**Testing required:**
1. Build executable
2. Test all ice phase generation
3. Test hydrate generation
4. Test ion insertion
5. Test all export formats
6. Test phase diagram rendering
7. Test 3D viewer

**Estimated effort:** 1-2 days including testing

---

## Group F: Refactoring → Insert Phase (Low Priority)

**Why phase:** Large-scale code reorganization requires careful planning and testing.

### F1. Refactor Large Files
**Files:**
- `quickice/output/gromacs_writer.py` (1559 lines)
- `quickice/gui/main_window.py` (1317 lines)
- `quickice/output/phase_diagram.py` (1132 lines)

**Approach:** Split into smaller modules with single responsibilities

### F2. Remove Deprecated Heuristic
**File:** `quickice/structure_generation/water_filler.py:335-359`
**Approach:** Require explicit `atoms_per_molecule` parameter

### F3. Add Missing CLI Features
**Scope:** Hydrate generation and ion insertion only available in GUI
**Files:** `quickice/cli/parser.py`, `quickice/main.py`
**Approach:** Add CLI arguments and workflow for hydrate/ion features

---

## Recommended Session Order

### Session 1: Critical Bugs (HIGH PRIORITY)
```
/new
/gsd-debug
```
**Prompt:**
```
Investigate and fix these critical bugs:

1. PDB writer atom count mismatch for hydrates
   - quickice/output/pdb_writer.py:138-142
   - Assumes 3 atoms, hydrates have 4

2. Box dimension validation mismatch
   - Docs say 0.5 nm minimum
   - Code enforces 1.0 nm minimum
   - Determine correct value and fix

3. Version number mismatch
   - quickice/__init__.py:3 says 3.0.0
   - README.md says 4.0
   - Align all version references

4. README_bin.md tarball name mismatch
   - Download says v4.0.0, extraction says v3.0.0

Reference: .planning/code_analysis/VULNERABILITY_SCAN_2026-05-02.md
Reference: .planning/code_analysis/DOC_CROSSCHECK_2026-05-02.md
```

### Session 2: Quick Fixes (MEDIUM PRIORITY)
```
/new
```
Then provide this prompt directly:
```
Fix these issues in quickice:

1. README.md:87 - typo `envronment.yml` → `environment.yml`

2. quickice/output/gromacs_writer.py:11 - remove unused `import quickice`

3. Remove duplicate comment lines (2 lines each):
   - quickice/phase_mapping/data/ice_boundaries.py:23-25
   - quickice/structure_generation/modes/pocket.py:16-18
   - quickice/structure_generation/modes/slab.py:16-18
   - quickice/structure_generation/water_filler.py:137-139
   - quickice/gui/molecular_viewer.py:29-31
   - quickice/gui/hydrate_renderer.py:25-27

4. Add Madrid2019 citation to README.md

5. Add CO₂ and H₂ to guest molecule list in README.md

6. Update project structure in README.md to include output/ and data/

7. Add spglib citation to docs/cli-reference.md

Reference: .planning/code_analysis/DEAD_CODE_2026-05-02.md
Reference: .planning/code_analysis/DOC_CROSSCHECK_2026-05-02.md
```

### Session 3: Code Quality Phase (MEDIUM PRIORITY)
```
/new
/gsd-plan-phase
```
**Prompt:**
```
Phase: Code Quality Improvements

Goals:
1. Add logging to 20+ empty pass statements (silent exception handling)
2. Consolidate duplicate molecule index building logic
3. Extract duplicate _count_guest_atoms and _count_guest_molecules from mode files
4. Add unit validation at data entry points
5. Add bounds validation for array operations
6. Add warning when fallback density values are used

Reference: .planning/code_analysis/VULNERABILITY_SCAN_2026-05-02.md
Reference: .planning/codebase/CONCERNS.md
```

### Session 4: Documentation Updates (MEDIUM PRIORITY)
```
/new
```
Then provide this prompt directly:
```
Update documentation:

1. docs/principles.md - Clarify detectable-only phases (Ice IX, X, XI, XV)

2. docs/gui-guide.md:230-236 - Add hydrate lattice type descriptions table

3. README.md - Add water density calculation method (IAPWS-95)

4. docs/gui-guide.md:413-418 - Add ion concentration formula explanation

5. docs/gui-guide.md:306-311 - Explain Ice II constraint

6. README.md:429-439 - Add coverage test command

Reference: .planning/code_analysis/DOC_CROSSCHECK_2026-05-02.md
```

### Session 5: Packaging Optimization (LOW PRIORITY)
```
/new
/gsd-plan-phase
```
**Prompt:**
```
Phase: Optimize PyInstaller Bundle Size

Goal: Reduce bundle size from ~700MB to ~500-550MB (22-43% reduction)

Tasks:
1. Add EXCLUDES list to quickice-gui.spec
2. Add VTK to collect_all packages
3. Add genice2.plugin hidden imports
4. Enable optimize=2
5. Test all features after build

Reference: .planning/code_analysis/PACKAGING_2026-05-02.md
```

### Session 6: Refactoring (LOW PRIORITY - FUTURE)
```
/new
/gsd-plan-phase
```
**Prompt:**
```
Phase: Code Refactoring

Goals:
1. Split gromacs_writer.py (1559 lines) into smaller modules
2. Split main_window.py (1317 lines) into smaller modules
3. Split phase_diagram.py (1132 lines) into smaller modules
4. Remove deprecated atoms_per_molecule heuristic
5. Add CLI support for hydrate generation
6. Add CLI support for ion insertion

Reference: .planning/codebase/CONCERNS.md
Reference: .planning/codebase/ARCHITECTURE.md
```

---

## Summary Matrix

| Group | Workflow | Sessions | Priority | Risk |
|-------|----------|----------|----------|------|
| A: Critical Bugs | `/gsd-debug` | 1 | HIGH | Medium |
| B: Quick Fixes | Direct prompt | 1 | MEDIUM | Low |
| C: Code Quality | `/gsd-plan-phase` | 1-2 | MEDIUM | Medium |
| D: Documentation | Direct prompt | 1 | MEDIUM | Low |
| E: Packaging | `/gsd-plan-phase` | 1 | LOW | Medium |
| F: Refactoring | `/gsd-plan-phase` | 1-2 | LOW | High |

**Total sessions needed:** 6-8 sessions

**Recommended order:** A → B → D → C → E → F

---

*Document created: 2026-05-02*
