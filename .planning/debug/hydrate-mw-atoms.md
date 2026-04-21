---
status: fixing
trigger: "ValueError: Invalid ice atom ordering for molecule 1: expected ['O', 'H', 'H'] or ['OW', 'HW1', 'HW2'], got ['MW', 'OW', 'HW1']"
created: 2026-04-21T00:00:00Z
updated: 2026-04-21T00:00:00Z
---

## Current Focus
hypothesis: Validation code needs to accept new hydrate-water-pattern ['MW', 'OW', 'HW1'] as valid ice atom ordering
test: Update validation in vtk_utils.py line 482-490
expecting: Three valid patterns: ["O", "H", "H"], ["OW", "HW1", "HW2"], ["MW", "OW", "HW1"]
next_action: Apply fix and add test for new pattern

## Symptoms
expected: Validation should accept ['MW', 'OW', 'HW1'] as valid ice atom ordering
actual: Validation rejects this pattern, throwing ValueError
errors:
  - "ValueError: Invalid ice atom ordering for molecule 1: expected ['O', 'H', 'H'] or ['OW', 'HW1', 'HW2'], got ['MW', 'OW', 'HW1']"
reproduction: When converting hydrate→interface with membrane water present
started: Recently - new pattern introduced

## Eliminated

## Evidence

## Resolution
root_cause:
fix:
verification:
files_changed: []
