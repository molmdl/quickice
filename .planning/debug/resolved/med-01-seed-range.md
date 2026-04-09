---
status: resolved
trigger: "Investigate issue: MED-01 hardcoded-seed-range - Hardcoded seed range limits diversity of generated candidates"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:15:00Z
---

## Current Focus

hypothesis: Fix implemented and verified
test: All tests pass
expecting: Complete
next_action: Report completion

## Symptoms

expected: Users should be able to get truly random candidates
actual: Seeds are sequential (1000, 1001, 1002...) limiting diversity
errors: No error, but limits exploration of configuration space
reproduction: Generate multiple candidates, observe they use sequential seeds
started: Always used sequential seeds

## Eliminated

(None)

## Evidence

- timestamp: 2026-04-09T00:00:00Z
  checked: User-reported issue location
  found: File quickice/structure_generation/generator.py lines 214-220 hardcodes base_seed=1000 with sequential generation
  implication: Confirms the reported issue - every batch starts at seed 1000

- timestamp: 2026-04-09T00:02:00Z
  checked: Tests in test_structure_generation.py
  found: Tests expect seeds 1000-1009 (line 420), check diversity within batch (line 431), check reproducibility (line 442)
  implication: Tests don't cover cross-batch diversity issue

- timestamp: 2026-04-09T00:03:00Z
  checked: Usage in main.py and gui/workers.py
  found: Both call generate_candidates() without seed control
  implication: Users have no way to control seed from CLI or GUI

- timestamp: 2026-04-09T00:04:00Z
  checked: types.py InterfaceConfig
  found: InterfaceConfig has seed attribute for interface generation
  implication: Seed control pattern exists in codebase

- timestamp: 2026-04-09T00:08:00Z
  checked: Test run after fix implementation
  found: All 57 tests pass including new seed diversity tests
  implication: Fix is working correctly

## Resolution

root_cause: generate_all() hardcodes base_seed=1000 with no parameter to change it. Every call produces identical candidates (seeds 1000, 1001, 1002...).
fix: Added base_seed parameter to generate_all() and generate_candidates(). Default to None (uses time_ns() for nanosecond precision) for automatic diversity. When specified, use user-provided seed for reproducibility.
verification: All 57 tests pass. New tests verify: (1) explicit base_seed produces sequential seeds, (2) random seeds produce different batches, (3) same base_seed produces identical results.
files_changed: [quickice/structure_generation/generator.py, tests/test_structure_generation.py]

## Commit

hash: d8952b9
message: fix(med-01): add base_seed parameter for candidate diversity
