# Prompt 1: Critical Bugs

**Workflow:** `/gsd-debug`
**Priority:** HIGH
**Estimated time:** 2-4 hours

---

## Instructions

Start a new session, then run:
```
/gsd-debug
```

Paste this prompt when asked:

---

## Prompt

Investigate and fix these critical bugs:

### 1. PDB Writer Atom Count Mismatch (HIGH) — ⚠️ DEFERRED
**Issue:** `write_interface_pdb_writer` assumes 3 atoms per ice molecule, but hydrates have 4 atoms (TIP4P format)
**File:** `quickice/output/pdb_writer.py:138-142`
**Impact:** Incorrect PDB output for hydrate structures
**Status:** DEFERRED - Requires investigation and testing with hydrate structures
**Investigation:**
- Trace how GRO writer handles atoms_per_molecule detection
- Apply same pattern to PDB writer
- Test with hydrate structures

### 2. Box Dimension Validation Mismatch (CRITICAL)
**Issue:** Documentation says 0.5 nm minimum, code enforces 1.0 nm minimum
**Files:**
- `docs/cli-reference.md:283` - claims 0.5-100 nm
- `quickice/validation/validators.py:142-145` - enforces >= 1.0 nm
**Investigation:**
- Check which is scientifically correct
- Either fix code or fix docs
- Add test for boundary values

### 3. Version Number Mismatch (CRITICAL)
**Issue:** Documentation references v4.0, code reports v3.0.0
**Files:**
- `quickice/__init__.py:3` - `__version__ = "3.0.0"`
- `quickice/cli/parser.py:175` - `version="%(prog)s 3.0.0"`
- `README.md` - references v4.0 throughout
**Fix:** Decide on correct version, update all locations consistently

### 4. README_bin.md Tarball Name Mismatch
**Issue:** Download link says v4.0.0, extraction command says v3.0.0
**File:** `README_bin.md:4-8`
**Fix:** Align version numbers between download link and extraction command

---

## References

- `.planning/code_analysis/VULNERABILITY_SCAN_2026-05-02.md` - Issues #2, #3
- `.planning/code_analysis/DOC_CROSSCHECK_2026-05-02.md` - Critical Issues #1-4

---

## Success Criteria

- [ ] PDB writer correctly handles hydrate structures (4 atoms/molecule)
- [ ] Box dimension validation matches documentation
- [ ] All version numbers aligned across codebase and documentation
- [ ] README_bin.md download and extraction commands match
- [ ] All tests pass after fixes
