# Prompt 2: Quick Fixes

**Workflow:** Direct prompt (no command needed)
**Priority:** MEDIUM
**Estimated time:** 1-2 hours

---

## Instructions

Start a new session, then paste the prompt directly.

---

## Prompt

Fix these issues in quickice:

### 1. Installation Typo
**File:** `README.md:87`
**Fix:** Change `envronment.yml` to `environment.yml`

```bash
# Before
conda env create -f envronment.yml

# After
conda env create -f environment.yml
```

### 2. Remove Unused Self-Import
**File:** `quickice/output/gromacs_writer.py:11`
**Fix:** Remove the line `import quickice`

### 3. Remove Duplicate Comment Lines (12 lines total)
**Files to edit:**

- `quickice/phase_mapping/data/ice_boundaries.py:23-25`
  - Remove 2 duplicate `# ==============` lines

- `quickice/structure_generation/modes/pocket.py:16-18`
  - Remove 2 duplicate memory note lines

- `quickice/structure_generation/modes/slab.py:16-18`
  - Remove 2 duplicate memory note lines

- `quickice/structure_generation/water_filler.py:137-139`
  - Remove 2 duplicate density calculation comment lines

- `quickice/gui/molecular_viewer.py:29-31`
  - Remove 2 duplicate unit conversion note lines

- `quickice/gui/hydrate_renderer.py:25-27`
  - Remove 2 duplicate unit conversion note lines

### 4. Add Madrid2019 Citation
**File:** `README.md` (add new section after ion insertion description)

```markdown
### Ion Force Field: Madrid2019

Na⁺ and Cl⁻ ions use the Madrid2019 force field:

Zeron, I. M., Pérez-Villasenor, F., & Vega, C. (2019).
A molecular dynamics study of the ion-ion and ion-water interaction 
parameters for NaCl in water using the Madrid-2019 force field.
Journal of Chemical Physics, 151, 134504.
DOI: https://doi.org/10.1063/1.5121394
```

### 5. Add CO₂ and H₂ to Guest Molecule Documentation
**Files:** `README.md`, `docs/gui-guide.md`

Add to guest molecule sections:
```markdown
**Guest Molecules:**
- CH₄ (methane)
- THF (tetrahydrofuran)
- CO₂ (carbon dioxide)
- H₂ (hydrogen)
```

### 6. Update Project Structure in README
**File:** `README.md:410-425`

Add missing directories to the project structure:
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

### 7. Add spglib Citation to CLI Reference
**File:** `docs/cli-reference.md`

Add new section:
```markdown
## Validation

QuickIce validates generated structures using spglib for crystal 
symmetry analysis:

- Repository: https://github.com/atztogo/spglib
- Paper: "Spglib: a software library for crystal symmetry search"
- DOI: https://doi.org/10.1080/27660400.2024.2384822
```

---

## References

- `.planning/code_analysis/DEAD_CODE_2026-05-02.md` - Issues #1, #2, #3
- `.planning/code_analysis/DOC_CROSSCHECK_2026-05-02.md` - Issues #5-11

---

## Success Criteria

- [ ] No typos in installation instructions
- [ ] No unused imports
- [ ] No duplicate comment lines
- [ ] Madrid2019 citation added
- [ ] CO₂ and H₂ documented as guest molecules
- [ ] Project structure includes output/ and data/
- [ ] spglib citation in CLI reference
