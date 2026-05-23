---
created: 2026-05-24T03:17
title: Pre-built small molecules for custom mol with GROMACS format
area: feature
files:
  - quickice/gui/custom_molecule_panel.py
  - quickice/gui/custom_molecule_worker.py
---

## Problem

Users currently must supply their own .gro/.itp files for custom molecule insertion. Providing a library of pre-built small molecules (e.g. from AMBER geostd set at https://ambermd.org/downloads/amber_geostd.tar.bz2) converted to GROMACS format would lower the barrier to entry and improve usability. A search/browse function in the GUI would let users pick molecules instead of manually preparing files.

## Solution

TBD — Research needed:

1. **License:** Check AMBER geostd license (likely Amber Force Field terms — verify redistribution rights for bundled .gro/.itp in GROMACS format)
2. **Size:** Inventory the molecule set in amber_geostd.tar.bz2 (count, types, file sizes)
3. **Conversion:** Research AMBER → GROMACS format conversion (parm7/nc → .gro/.itp). Tools: ACPYPE, ParmEd, InterMol. Evaluate quality and automation feasibility.
4. **Implementation:** Convert subset, bundle as data files, add GUI search/browse panel to Custom Molecule tab
5. **Utility:** Consider shipping a standalone conversion function (AMBER → GROMACS) for user-supplied AMBER files
