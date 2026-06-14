---
created: 2026-05-09T17:30
updated: 2026-06-14
title: Provide CLI-only executable for automation
area: tooling
files:
  - quickice/cli.py
  - pyinstaller.spec
---

## Problem

Users running automated workflows (scripts, HPC jobs, CI/CD pipelines) need a lightweight CLI executable without GUI dependencies. Currently the bundled executable includes VTK and PySide6 which are unnecessary for CLI mode.

## Existing Context

**Related Quick Tasks (already shipped):**
- Quick Task 013: CLI hydrate support (`.planning/quick/013-add-cli-hydrate-support/`)
- Quick Task 014: CLI ion support (`.planning/quick/014-add-cli-ion-support/`)
- Quick Task 015: CLI progress reporting (`.planning/quick/015-add-cli-progress-reporting/`)

**Related bundle research:**
- Quick Task 008: Optimize PyInstaller bundle (`.planning/quick/008-optimize-pyinstaller-bundle-size/`)
- Quick Task 016: Minimize dependencies (`.planning/quick/016-minimize-bundle-dependencies/`) — **REVERTED** (exclusions broke executable)

**Deferred v4.5 requirements:** CLI-01 to CLI-05 (solute, custom molecule, ion source, interface mode CLI support) — targeted for v4.5.1 milestone

## Solution

Create a separate PyInstaller spec for CLI-only bundle:
- Exclude PySide6, VTK, and visualization modules
- Smaller bundle size for headless environments
- May be combined with unified entry point (see related todo: unify-gui-cli-entry-point)
- **Risk:** Quick Task 016 showed aggressive exclusions break the executable — conservative approach needed
- Target: v4.5.1 or v5.0 milestone

## Dependency

Should be done AFTER v4.5.1 CLI feature parity (CLI-01 to CLI-05) is complete — otherwise the CLI-only bundle would lack features.
