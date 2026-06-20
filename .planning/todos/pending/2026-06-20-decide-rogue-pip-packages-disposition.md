---
created: 2026-06-20T23:30
title: Decide disposition of 26 rogue pip packages in quickice env
area: tooling
files:
  - lib-to-add.yml
  - environment.yml
  - environment-build.yml
---

## Problem

26 packages were pip-installed into the quickice conda env by opencode agents without permission (violating PROJECT.md line 203). They are documented in `lib-to-add.yml` grouped by source command and session ID. The quickice source code imports NONE of them, and a clean `conda env create -f environment.yml` + PyInstaller build produces a working binary without them. However, they remain installed, making the env deviate from the yml spec and `conda env export` not reproducible.

5 groups total:
- G1: MDAnalysis + 9 deps (research debris, Jun 12)
- G2: genice2-cif + 13 deps (research debris, Jun 12)
- G3: gsw (research debris, Apr 12)
- G4: pytest-timeout (executor agent, Jun 14)
- G5: git-filter-repo (unknown agent, Apr 4)

## Solution

TBD — user must decide keep/remove for each group. If keeping any, add to environment.yml with version pins. If removing, `pip uninstall` each group. The binary is unaffected either way (verified).
