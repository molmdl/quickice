---
status: verifying
trigger: "GenIce uses global np.random state, affecting concurrent operations"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:10:00Z
---

## Current Focus
hypothesis: ROOT CAUSE FOUND - GenIce requires global np.random, save/restore pattern is correct for sequential use
test: Verified save/restore works correctly. No concurrent usage in codebase.
expecting: Fix: document limitation, remove misleading unused rng variable
next_action: Implement fix

## Eliminated
- hypothesis: Save/restore pattern is broken
  evidence: Tested pattern - it correctly restores state after GenIce modifies it
  timestamp: 2026-04-09T00:05:00Z

## Evidence
- timestamp: 2026-04-09T00:00:00Z
  checked: quickice/structure_generation/generator.py lines 84-116
  found: Code saves np.random state (line 86), sets seed (line 87), then restores (line 116). Also creates unused local rng on line 91.
  implication: The save/restore pattern works for sequential use but is not thread-safe

- timestamp: 2026-04-09T00:01:00Z
  checked: genice2/genice.py (installed package source)
  found: GenIce uses global np.random in multiple places: line 58 (np.random.rand), line 816 (np.random.normal), line 1072 (np.random.randint)
  implication: CONFIRMED - GenIce relies on global np.random state, so seed must be set globally

- timestamp: 2026-04-09T00:02:00Z
  checked: quickice/gui/workers.py - GenerationWorker class
  found: GUI uses QThread with worker-object pattern. Single generation call per worker. No concurrent generation.
  implication: Thread-safety issue is theoretical for current QuickIce usage - each generation is sequential

- timestamp: 2026-04-09T00:03:00Z
  checked: Codebase-wide search for threading/multiprocessing/asyncio
  found: No imports or usage of concurrent execution patterns
  implication: QuickIce is designed for sequential execution, thread-safety not required

- timestamp: 2026-04-09T00:04:00Z
  checked: Python test of save/restore pattern
  found: Pattern correctly saves state, GenIce modifies state, state is restored to pre-GenIce state
  implication: The save/restore pattern is correct and works as intended

## Resolution
root_cause: GenIce internally uses global np.random (confirmed in genice2/genice.py lines 58, 816, 1072). QuickIce correctly saves/restores state around generation calls, but this pattern is not thread-safe. However, QuickIce does not use concurrent generation, making this a documentation issue rather than a bug.
fix: Removed misleading unused rng variable (line 91), added documentation about thread-safety limitation in _generate_single docstring
verification: All 20 structure generation tests pass. Reproducibility test passes. Random state preservation test passes.
files_changed: [quickice/structure_generation/generator.py]

## Resolution
root_cause: 
fix: 
verification: 
files_changed: []
