# Prompt 2: Quick Fixes

**Workflow:** Direct prompt (no command needed)
**Priority:** LOW
**Estimated time:** 5-10 minutes

---

## Instructions

Start a new session, then paste the prompt directly.

---

## Summary

After verification, most reported issues were false positives or already fixed:
- ✅ Installation typo - already fixed
- ✅ Self-import - intentional (used for package path)
- ✅ Duplicate comments - do not exist
- ✅ Madrid2019 citation - already exists

**Only 2 real tasks remain:**

---

## Prompt

Fix these issues in quickice:

### 1. Fix README Project Structure
**File:** `README.md:422-441`

**Current (WRONG):**
```
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
├── data/                # Reference data files              ← WRONG
├── output/              # Default output directory          ← WRONG
├── sample_output/       # Sample CLI output directory
├── environment.yml      # Conda environment file
├── setup.sh             # Environment file to source in a new shell
└── README.md            # This file
```

**Correct:**
- `data/` is inside `quickice/` package (bundled force field files)
- `output/` is inside `quickice/` package (Python module for GROMACS/PDB export)
- Root `output/` is user-created at runtime, NOT a project directory

**Fix:** Replace with:
```markdown
## Project Structure

```
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
│   ├── output/          # PDB/GROMACS export module
│   └── data/            # Bundled force field files
├── sample_output/       # Sample CLI output directory
├── environment.yml      # Conda environment file
├── setup.sh             # Environment file to source in a new shell
└── README.md            # This file
```
```

### 2. Add spglib Citation to CLI Reference
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

- `.planning/code_analysis/DEAD_CODE_2026-05-02.md` - Issues #1, #2, #3 (verified as false positives)
- `.planning/code_analysis/DOC_CROSSCHECK_2026-05-02.md` - Issues #5-11

---

## Success Criteria

- [x] No typos in installation instructions
- [x] No unused imports (intentional imports verified)
- [x] No duplicate comment lines (analysis was incorrect)
- [x] Madrid2019 citation added
- [x] Project structure shows data/ and output/ inside quickice/ package
- [x] spglib citation in CLI reference

---

## Execution Log

**Date:** 2026-05-02

| Task | Status | Commit |
|------|--------|--------|
| Fix project structure | ✅ Complete | `09d0ddb` |
| Add spglib citation | ✅ Complete | `7a3372f` |

**Note:** Earlier commit `bd4fc1b` was made based on incorrect analysis (added fake CO₂/H₂ guest info). The analysis errors were:
- Claimed typo existed - already fixed
- Claimed unused imports - intentional for package path resolution
- Claimed duplicate comments - never existed
- Claimed missing Madrid2019 citation - already present
- Claimed fake CO₂/H₂ should be added - these are future features
