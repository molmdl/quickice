---
status: resolved
trigger: "Investigate issue: LOW-01 magic-numbers-scoring\n\n**Summary:** Magic numbers in scoring without configuration mechanism"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:02:00Z
---

## Current Focus
hypothesis: Magic numbers IDEAL_OO_DISTANCE and OO_CUTOFF are hardcoded at module level with no configuration mechanism
test: Verified constants are module-level variables used in 3 locations with no way to override
expecting: Root cause confirmed - constants hardcoded without config
next_action: Implement ScoringConfig dataclass and update functions

## Symptoms
expected: Scoring parameters should be configurable
actual: Hardcoded constants IDEAL_OO_DISTANCE and OO_CUTOFF
errors: No error, but limits flexibility for different simulation setups
reproduction: Try to adjust scoring criteria
started: Always hardcoded

## Eliminated

## Evidence
- timestamp: 2026-04-09T00:00:00Z
  checked: quickice/ranking/scorer.py lines 22-23
  found: Hardcoded constants IDEAL_OO_DISTANCE = 0.276 and OO_CUTOFF = 0.35
  implication: Values cannot be changed without modifying source code
- timestamp: 2026-04-09T00:00:00Z
  checked: scorer.py lines 30, 124, 349
  found: Constants used in 3 locations: _calculate_oo_distances_pbc (cutoff param), energy_score (ideal distance calc), rank_candidates (metadata)
  implication: Fix needs to propagate to all usage sites
- timestamp: 2026-04-09T00:00:00Z
  checked: quickice/structure_generation/types.py
  found: Project uses dataclasses for configuration (InterfaceConfig example)
  implication: Should follow same pattern for ScoringConfig

## Resolution
root_cause: IDEAL_OO_DISTANCE and OO_CUTOFF were hardcoded module-level constants (lines 22-23 in scorer.py) with no configuration mechanism, preventing users from adjusting scoring parameters for different water models or research scenarios
fix: Added ScoringConfig dataclass to types.py, modified energy_score() and rank_candidates() to accept optional config parameter, removed hardcoded constants, updated scoring_metadata to include config values
verification: Created ScoringConfig with default values (0.276, 0.35), tested custom config values (0.28, 0.40) - all work correctly
files_changed: [quickice/ranking/types.py, quickice/ranking/scorer.py, quickice/ranking/__init__.py]