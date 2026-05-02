# Prompt 4: Code Quality Improvements

## Prompt to Paste

```
Phase: Code Quality Improvements

Goals:
1. Add logging to 20+ empty pass statements in exception handlers
2. Consolidate duplicate molecule index building logic into utils.py
3. Extract duplicate _count_guest_atoms functions from mode files (~60 lines)
4. Add unit validation at data entry points (nm vs Å mismatch prevention)
5. Add bounds validation for array operations
6. Add warning when fallback density values are used
7. Fix parameter naming: atoms_perMol → atoms_per_mol in piece.py:50
8. Add warning when GRO format atom limit (>100k) exceeded

Reference: .planning/code_analysis/VULNERABILITY_SCAN_2026-05-02.md
Reference: .planning/codebase/CONCERNS.md
```
