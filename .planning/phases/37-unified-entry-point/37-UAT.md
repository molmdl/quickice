---
status: testing
phase: 37-unified-entry-point
source: [37-01-SUMMARY.md, 37-02-SUMMARY.md, 37-03-SUMMARY.md, 37-04-SUMMARY.md, 37-05-SUMMARY.md, 37-06-SUMMARY.md, 37-07-SUMMARY.md, 37-08-SUMMARY.md, 37-09-SUMMARY.md, 37-10-SUMMARY.md, 37-11-SUMMARY.md, 37-12-SUMMARY.md, 37-13-SUMMARY.md, 37-14-SUMMARY.md, 37-15-SUMMARY.md, 37-16-SUMMARY.md, 37-17-SUMMARY.md, 37-18-SUMMARY.md, 37-19-SUMMARY.md, 37-20-SUMMARY.md]
started: 2026-06-26T12:00:00Z
updated: 2026-06-26T12:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: No-args shows help
expected: |
  Running `python -m quickice` with no arguments prints help/usage text and exits with code 0 (like git with no args)
awaiting: user response

## Tests

### 1. No-args shows help
expected: Running `python -m quickice` with no arguments prints help/usage text and exits with code 0 (like git with no args)
result: [pending]

### 2. --help flag
expected: Running `python -m quickice --help` prints full argparse usage with "python -m quickice" as prog name and exits with code 0
result: [pending]

### 3. --version flag
expected: Running `python -m quickice --version` prints version string containing "4.5.0" and exits with code 0
result: [pending]

### 4. Implicit CLI mode with pipeline flags
expected: Running `python -m quickice -T 250 -P 0.1 -N 96` (valid ice conditions) automatically enters CLI mode and generates an ice structure without needing --cli flag
result: [pending]

### 5. Explicit --cli mode
expected: Running `python -m quickice --cli -T 250 -P 0.1 -N 96` forces CLI mode, runs the same pipeline as implicit CLI
result: [pending]

### 6. --cli without pipeline flags errors
expected: Running `python -m quickice --cli` (no other flags) exits with error code and shows a message indicating pipeline flags are required for CLI mode
result: [pending]

### 7. --gui flag with display available
expected: Running `python -m quickice --gui` on a machine with display launches the QuickIce GUI window
result: [pending]

### 8. --gui graceful failure without display
expected: Running `python -m quickice --gui` on a headless machine (no display) exits with code 1 and shows a clear error message about no display available
result: [pending]

### 9. PySide6 not installed graceful fallback
expected: When PySide6 is not installed, running `python -m quickice --gui` shows an informative message about how to install PySide6 (not a raw traceback or import error)
result: [pending]

### 10. Backward compat: python quickice.py
expected: Running `python quickice.py --help` still works and routes through the unified entry point, exits with code 0
result: [pending]

### 11. CLI help shows --cli and --gui flags
expected: The `python -m quickice --help` output lists both `--cli` and `--gui` flags with descriptions explaining their purpose (headless/CI and explicit GUI mode)
result: [pending]

### 12. CLI examples script exists and runs
expected: `scripts/cli-examples.sh` exists, is executable, and runs successfully (`bash scripts/cli-examples.sh` exits 0). Contains commented-out CLI command examples covering ice, hydrate, interface, custom, solute, and ion flags
result: [pending]

### 13. Workflow script exists and runs
expected: `scripts/hydrate-interface-custom-ion.sh` exists, is executable, and shows usage when run with no args (`--help` or similar). Script supports flags for temperature, pressure, molecule count, concentration, etc.
result: [pending]

### 14. CLI reference updated
expected: `docs/cli-reference.md` contains no remaining `python quickice.py` primary invocation references (backward-compat mentions are acceptable). Contains "Unified Entry Point" section with routing table, "Mode Selection" section, and "Platform Invocation" table
result: [pending]

### 15. Flowchart updated
expected: `docs/flowchart.md` shows `python -m quickice` invocation and entry box references `quickice/__main__.py / entry.main() router` (not old `quickice.py / main()`)
result: [pending]

### 16. README updated for unified entry
expected: README.md Quick Start uses `python -m quickice --help` (verify) and `python -m quickice --gui` (launch GUI). Project structure lists `__main__.py` and `entry.py`. Entry Point section explains routing behaviors
result: [pending]

### 17. README_bin.md platform invocation
expected: README_bin.md contains a Platform Invocation table covering source install, binary Linux/macOS, and binary Windows commands. Has CLI Mode section for binary users
result: [pending]

### 18. setup.sh help message
expected: Running `bash setup.sh --help` or similar shows `python -m quickice --help` (not `python quickice.py --help`)
result: [pending]

### 19. Entry point routing tests pass
expected: `pytest tests/test_entry_point.py` passes all 12 routing tests covering no-args, --help, --version, --cli, --gui, implicit CLI, and backward compatibility
result: [pending]

### 20. Migrated test files pass
expected: `pytest tests/test_cli_integration.py tests/test_cli_pipeline.py tests/test_integration_v35.py tests/test_phase_mapping.py` all pass using the unified `run_quickice()` helper
result: [pending]

## Summary

total: 20
passed: 0
issues: 0
pending: 20
skipped: 0

## Gaps

[none yet]
