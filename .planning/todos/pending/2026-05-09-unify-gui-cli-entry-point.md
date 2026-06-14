---
created: 2026-05-09T17:30
updated: 2026-06-14
title: Unify GUI/CLI entry point into single executable
area: tooling
files:
  - quickice/__main__.py
  - quickice/cli.py
  - quickice/gui.py
---

## Problem

Currently GUI and CLI are separate entry points. After v4.5.1 CLI feature parity milestone, the project should have a single executable that can launch either GUI or CLI mode based on command-line options. This simplifies distribution and user experience.

## Solution

After v4.5.1 milestone completes CLI feature parity with GUI:
- Detect if running with `--cli` or `--no-gui` flags
- Launch CLI mode if flags present, otherwise launch GUI
- Consider argparse subcommands (e.g., `quickice generate`, `quickice gui`)
- Target: v4.5.1 or v5.0 milestone

## Dependencies

1. **v4.5.1 CLI feature parity must be complete first** — otherwise unified entry point has incomplete CLI
2. **CLI-only executable todo** — may combine into single effort
3. **Related Quick Tasks:** 013 (CLI hydrate), 014 (CLI ion), 015 (CLI progress) — already shipped as partial CLI
