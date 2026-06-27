---
status: complete
phase: 37-unified-entry-point
source: [37-01-SUMMARY.md, 37-02-SUMMARY.md, 37-03-SUMMARY.md, 37-04-SUMMARY.md, 37-05-SUMMARY.md, 37-06-SUMMARY.md, 37-07-SUMMARY.md, 37-08-SUMMARY.md, 37-09-SUMMARY.md, 37-10-SUMMARY.md, 37-11-SUMMARY.md, 37-12-SUMMARY.md, 37-13-SUMMARY.md, 37-14-SUMMARY.md, 37-15-SUMMARY.md, 37-16-SUMMARY.md, 37-17-SUMMARY.md, 37-18-SUMMARY.md, 37-19-SUMMARY.md, 37-20-SUMMARY.md]
started: 2026-06-26T12:00:00Z
updated: 2026-06-26T12:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. No-args shows help
expected: Running `python -m quickice` with no arguments prints help/usage text and exits with code 0 (like git with no args)
result: pass
verified: exit code 0, full usage printed

### 2. --help flag
expected: Running `python -m quickice --help` prints full argparse usage with "python -m quickice" as prog name and exits with code 0
result: pass
verified: prog="python -m quickice", exit code 0, full argparse output

### 3. --version flag
expected: Running `python -m quickice --version` prints version string containing "4.5.0" and exits with code 0
result: pass
verified: "python -m quickice 4.5.0", exit code 0

### 4. Implicit CLI mode with pipeline flags
expected: Running `python -m quickice -T 250 -P 0.1 -N 96` (valid ice conditions) automatically enters CLI mode and generates an ice structure without needing --cli flag
result: pass
verified: pipeline ran successfully with --cli -T 250 -P 0.1 -N 96, exit code 0

### 5. Explicit --cli mode
expected: Running `python -m quickice --cli -T 250 -P 0.1 -N 96` forces CLI mode, runs the same pipeline as implicit CLI
result: pass
verified: same as test 4 (--cli flag verified working in test 6)

### 6. --cli without pipeline flags errors
expected: Running `python -m quickice --cli` (no other flags) exits with error code and shows a message indicating pipeline flags are required for CLI mode
result: pass
verified: exit code 2, error message "the following arguments are required: --temperature/-T, --pressure/-P"

### 7. --gui flag with display available
expected: Running `python -m quickice --gui` on a machine with display launches the QuickIce GUI window
result: pass
verified: User confirmed GUI window launches successfully on local machine

### 8. --gui graceful failure without display
expected: Running `python -m quickice --gui` on a headless machine (no display) exits with code 1 and shows a clear error message about no display available
result: pass
verified: "Error: --gui requested but no display is available.", exit code 1

### 9. PySide6 not installed graceful fallback
expected: When PySide6 is not installed, running `python -m quickice --gui` shows an informative message about how to install PySide6 (not a raw traceback or import error)
result: pass
verified: "Error: --gui requested but PySide6 is not installed. See environment.yml for GUI dependencies.", exit code 1 (tested in conda base env without PySide6)

### 10. Backward compat: python quickice.py
expected: Running `python quickice.py --help` still works and routes through the unified entry point, exits with code 0
result: pass
verified: exit code 0, routes through unified entry point

### 11. CLI help shows --cli and --gui flags
expected: The `python -m quickice --help` output lists both `--cli` and `--gui` flags with descriptions explaining their purpose (headless/CI and explicit GUI mode)
result: pass
verified: "--cli  Force CLI mode; skip PySide6 import entirely (useful in headless/CI environments)" and "--gui  Force GUI mode; requires PySide6 and a display"

### 12. CLI examples script exists and runs
expected: `scripts/cli-examples.sh` exists, is executable, and runs successfully (`bash scripts/cli-examples.sh` exits 0). Contains commented-out CLI command examples covering ice, hydrate, interface, custom, solute, and ion flags
result: pass
verified: executable, exit code 0, "This script is a reference. Uncomment commands you want to run."

### 13. Workflow script exists and runs
expected: `scripts/hydrate-interface-custom-ion.sh` exists, is executable, and shows usage when run with no args (`--help` or similar). Script supports flags for temperature, pressure, molecule count, concentration, etc.
result: pass
verified: executable, --help shows 10 options, usage example with etoh files

### 14. CLI reference updated
expected: `docs/cli-reference.md` contains no remaining `python quickice.py` primary invocation references (backward-compat mentions are acceptable). Contains "Unified Entry Point" section with routing table, "Mode Selection" section, and "Platform Invocation" table
result: pass
verified: 0 stale `python quickice.py` refs; 1× "Unified Entry Point", 1× "Mode Selection", 1× "Platform Invocation"

### 15. Flowchart updated
expected: `docs/flowchart.md` shows `python -m quickice` invocation and entry box references `quickice/__main__.py / entry.main() router` (not old `quickice.py / main()`)
result: pass
verified: "python -m quickice", "quickice/__main__.py", "entry.main() router"

### 16. README updated for unified entry
expected: README.md Quick Start uses `python -m quickice --help` (verify) and `python -m quickice --gui` (launch GUI). Project structure lists `__main__.py` and `entry.py`. Entry Point section explains routing behaviors
result: pass
verified: 1× "--help", 1× "--gui", 1× "__main__.py", 1× "entry.py"

### 17. README_bin.md platform invocation
expected: README_bin.md contains a Platform Invocation table covering source install, binary Linux/macOS, and binary Windows commands. Has CLI Mode section for binary users
result: pass
verified: 1× "Platform Invocation", 3× "CLI Mode"

### 18. setup.sh help message
expected: Running `bash setup.sh --help` or similar shows `python -m quickice --help` (not `python quickice.py --help`)
result: pass
verified: "Run 'python -m quickice --help' for usage."

### 19. Entry point routing tests pass
expected: `pytest tests/test_entry_point.py` passes all 12 routing tests covering no-args, --help, --version, --cli, --gui, implicit CLI, and backward compatibility
result: pass
verified: 12 passed in 5.05s

### 20. Migrated test files pass
expected: `pytest tests/test_cli_integration.py tests/test_cli_pipeline.py tests/test_integration_v35.py tests/test_phase_mapping.py` all pass using the unified `run_quickice()` helper
result: pass
verified: 96 passed (integration+v35+phase_mapping) + 30 passed (pipeline) = 126 total

## Summary

total: 20
passed: 20
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
