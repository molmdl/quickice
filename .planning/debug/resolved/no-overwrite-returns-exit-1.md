---
status: resolved
trigger: "When --no-overwrite flag is set and output directory already has files, the CLI pipeline exits with code 1 instead of code 0."
created: 2026-06-27T00:00:00
updated: 2026-06-27T00:01:00
---

## Current Focus

hypothesis: confirmed — --no-overwrite guard returns exit code 1 and logs at ERROR level
test: Applied fix, ran full test suite
expecting: All 53 tests pass
next_action: Archive

## Symptoms

expected: --no-overwrite should be a graceful skip, exiting with code 0 (success) since the flag's purpose IS to prevent writing when files exist.
actual: Pipeline exits with code 1 (runtime error) when files exist and --no-overwrite is set.
errors: stderr: "Output directory /tmp/xxx already contains files and --no-overwrite was specified"
reproduction: First run succeeds (rc=0), second run with --no-overwrite exits rc=1
started: Always been this way since --no-overwrite was implemented in Phase 36 Plan 01.

## Eliminated

## Evidence

- timestamp: 2026-06-27T00:00:00
  checked: quickice/cli/pipeline.py lines 69-80
  found: Line 74 uses logger.error, line 80 returns 1. Both indicate error semantics for an intentional skip.
  implication: Root cause confirmed

- timestamp: 2026-06-27T00:00:30
  checked: tests/test_cli_pipeline.py line 684
  found: Test asserted rc != 0, reinforcing the old behavior
  implication: Test must also be updated to assert rc == 0

- timestamp: 2026-06-27T00:01:00
  checked: Full test suite after fix
  found: All 53 tests pass (test_cli_pipeline.py + test_cli_integration.py)
  implication: Fix verified, no regressions

## Resolution

root_cause: pipeline.py line 80 returned 1 (runtime error) and line 74 used logger.error for the --no-overwrite skip path, treating intentional graceful behavior as a failure
fix: Changed return 1 → return 0 on line 80, changed logger.error → logger.info on line 74 (with updated message including "; skipping"), updated test to assert rc == 0 and verify --no-overwrite mentioned in stderr
verification: All 53 tests pass (test_cli_pipeline.py + test_cli_integration.py)
files_changed: [quickice/cli/pipeline.py, tests/test_cli_pipeline.py]
