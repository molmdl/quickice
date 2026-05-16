# Quick Task 020: Hydrate Guest Naming Consistency

**Created:** 2026-05-11
**Status:** Draft
**Priority:** High (GROMACS compatibility)

---

## Problem

Hydrate exports produce invalid GROMACS topology due to naming mismatch:

| Component | Current | Expected |
|-----------|---------|----------|
| MoleculetypeRegistry | `CH4_HYD` / `THF_HYD` | `CH4_H` / `THF_H` (shorter) |
| `.top` [ molecules ] | `CH4_HYD` / `THF_HYD` | Must match ITP |
| Hydrate ITP moleculetype | `ch4` / `thf` | `CH4_H` / `THF_H` |

**GROMACS Error:** When `.top` references `CH4_HYD` but `.itp` defines `ch4`, GROMACS fails with "moleculetype not found".

---

## Proposed Fix

Follow the `_L` (liquid) pattern with `_H` (hydrate) suffix:

1. **Create hydrate-specific ITP files:**
   - `quickice/data/ch4_hydrate.itp` with moleculetype `CH4_H`
   - `quickice/data/thf_hydrate.itp` with moleculetype `THF_H`

2. **Update MoleculetypeRegistry:**
   - Change `_HYD` suffix to `_H` in `register_hydrate_guest()`

3. **Update hydrate_export.py:**
   - Copy `ch4_hydrate.itp` / `thf_hydrate.itp` instead of `ch4.itp` / `thf.itp`

---

## Naming Convention Summary

| Type | Suffix | ITP File | Example |
|------|--------|----------|---------|
| Hydrate guest | `_H` | `ch4_hydrate.itp` | `CH4_H` |
| Liquid solute | `_L` | `ch4_liquid.itp` | `CH4_L` |
| Hydrate guest (THF) | `_H` | `thf_hydrate.itp` | `THF_H` |
| Liquid solute (THF) | `_L` | `thf_liquid.itp` | `THF_L` |

Both suffixes are single character (5-char max for GRO format: `CH4_H`, `THF_H`).

---

## Scope

| Task | Files | Complexity |
|------|-------|------------|
| Create ch4_hydrate.itp | 1 new file | Low (copy + modify) |
| Create thf_hydrate.itp | 1 new file | Low (copy + modify) |
| Update MoleculetypeRegistry | 1 file, ~3 lines | Low |
| Update hydrate_export.py | 1 file, ~5 lines | Low |
| Update tests | 1-2 files | Low |
| Test hydrate export | Manual | Low |

**Total:** ~6 files, ~15 lines of code changes

---

## Recommendation: Quick Task

**Reasons:**
1. **Clear scope:** 6 files, ~15 lines of code
2. **Isolated fix:** Only affects hydrate export path
3. **Pattern exists:** Follows the `_L` pattern already implemented
4. **Low risk:** Changes are localized, easy to verify

**Not urgent phase because:**
- No new architecture required
- No cross-phase dependencies
- Single developer can complete in 30-60 minutes

---

## Verification

1. Generate hydrate with CH4 guest → Export GROMACS
2. Verify `.top` includes `#include "ch4_hydrate.itp"`
3. Verify `.top` [ molecules ] shows `CH4_H`
4. Verify `ch4_hydrate.itp` has moleculetype `CH4_H`
5. Run GROMACS grompp to validate topology

---

## Related

- Phase 34.2: Created liquid ITP files (`ch4_liquid.itp`, `thf_liquid.itp`)
- Quick Task 017-019: Custom molecule improvements
- Current issue found during Workflow 9 (GROMACS Export) testing
