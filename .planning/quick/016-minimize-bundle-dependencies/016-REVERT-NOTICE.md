# Quick Task 016: REVERT NOTICE

**Status:** ❌ REVERTED  
**Date Reverted:** 2026-05-04  
**Reason:** Exclusions broke the executable

---

## Issue Summary

Quick task 016 attempted to minimize bundle dependencies by excluding scipy, matplotlib, and shapely submodules. The changes were committed and the task was marked complete.

**However, the optimizations broke the executable at runtime.**

---

## Root Cause

The dependency analysis was incomplete. While the research phase identified transitive dependencies, the exclusions still caused runtime failures when running the bundled executable.

**Specific failures:**
- Excluded modules caused `ImportError` at runtime
- The executable would not start or would crash during certain operations
- Manual testing of the bundled application revealed the issue

---

## Resolution

**User manually reverted `quickice-gui.spec` to the working state.**

The spec file now uses `collect_all()` for all packages without the selective exclusions that were attempted.

---

## Lessons Learned

1. **Transitive dependencies are complex:** Even with careful analysis, PyInstaller's module collection can have unexpected interactions
2. **Runtime testing is critical:** The original verification did not sufficiently test the bundled executable
3. **Conservative exclusions:** For scientific computing packages (scipy, matplotlib, shapely), aggressive exclusions are risky

---

## Recommendation for Future

**Skip this optimization approach.** The ~50MB savings is not worth the risk of breaking the application.

**Alternative approaches to consider:**
1. UPX compression tuning (safer)
2. VTK modularization (if possible, but complex)
3. Accept the current bundle size as reasonable for a scientific application

---

## Commits Referenced

- `7aa522f` - feat(016-01): add scipy exclusions to reduce bundle size (REVERTED)
- `b31261f` - feat(016-02): add matplotlib and shapely exclusions (REVERTED)

**Current state:** quickice-gui.spec reverted to pre-016 state

---

## Action Required

- [x] Mark task as reverted in planning documents
- [x] Update STATE.md to reflect revert
- [x] Document failure for future reference
- [x] Skip this optimization in future quick tasks
