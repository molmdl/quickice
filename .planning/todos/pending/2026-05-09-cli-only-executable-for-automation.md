---
created: 2026-05-09T17:30
title: Provide CLI-only executable for automation
area: tooling
files:
  - quickice/cli.py
  - pyinstaller.spec
---

## Problem

Users running automated workflows (scripts, HPC jobs, CI/CD pipelines) need a lightweight CLI executable without GUI dependencies. Currently the bundled executable includes VTK and PySide6 which are unnecessary for CLI mode.

## Solution

Create a separate PyInstaller spec for CLI-only bundle:
- Exclude PySide6, VTK, and visualization modules
- Smaller bundle size for headless environments
- May be combined with unified entry point (see related todo)
- Target: v4.6 or v5.0 milestone
