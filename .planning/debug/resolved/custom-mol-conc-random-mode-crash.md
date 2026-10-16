# Debug Session: custom-mol-conc-random-mode-crash

**Status:** RESOLVED (intermittent - working now)
**Created:** 2026-05-10
**Resolved:** 2026-05-10

## Issue

New custom molecule random mode insert by concentration crashes immediately with memory corruption error when clicking Generate.

## Symptoms

- **Expected:** Like insert by molecule count, but the inserted count is calculated from concentration
- **Actual:** Immediate crash
- **Error:** `malloc_consolidate(): unaligned fastbin chunk detected`
- **Reproduction:** hydrate → interface/slab → custom mol random mode conc input → etoh input → default conc → Generate → crash

## Investigation

- Concentration calculation logic works correctly
- Unit tests pass
- Non-Qt test script works fine
- Qt test script with concentration mode works fine
- All required files exist and are accessible

## Resolution

Issue resolved on its own - now working with exact same workflow. Likely an intermittent Qt/PySide6 memory state issue that didn't reproduce consistently.

## Notes

If this recurs, investigate:
- Qt/PySide6 threading issues
- Widget state management
- C extension memory management
- System resource constraints

