---
status: resolved
trigger: "GenIce2 doesn't support CS3 lattice type"
created: 2026-04-24
updated: 2026-04-24
---

## ROOT CAUSE FOUND

**Root Cause:** The `genice_name` for "sH" hydrate lattice was incorrectly set to `"CS3"` in `types.py`. GenIce2 does not have a lattice module called "CS3" - it uses `"sH"` (also known as "DOH" or "HS3").

**Evidence:**
- `genice2 CS3` → `AssertionError: Nonexistent or failed to load the module: CS3`
- `genice2 sH` → Works correctly
- GenIce2 help shows: `DOH, HS3, sH    Clathrate type H`

**Fix Applied:**
- Changed `"genice_name": "CS3"` → `"genice_name": "sH"` in `quickice/structure_generation/types.py`

**Files Changed:**
- `quickice/structure_generation/types.py` (line 62)

**Verification:**
- All hydrate lattice types (sI, sII, sH) now use correct GenIce2 lattice names
- Full generation test passed for sH hydrate
- No other references to CS3 remain in codebase