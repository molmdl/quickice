---
status: verifying
trigger: "THF .itp file missing from export, and need to verify residue name compatibility"
created: 2026-05-05T00:00:00Z
updated: 2026-05-05T00:15:00Z
---

## Current Focus
hypothesis: CONFIRMED - Path uses "topologies/" instead of "data/"
test: Verify directory structure and fix is applied
expecting: Fix is correct, ready to commit
next_action: Update debug file with verification and commit

## Symptoms
expected: 
1. THF .itp file should be copied to export directory
2. Residue names in .gro and .itp should match
3. Residue names should be GROMACS-compatible (not too long)

actual: 
1. THF .itp file missing from export directory
2. Need to verify residue name length and format
3. Need to check if .itp resname matches .gro resname

errors: No errors visible
reproduction: 
1. CH4 hydrate -> slab -> THF solute -> ions -> export
2. Check export directory - THF .itp missing
3. Check residue names in .gro and .itp files

started: Just discovered after previous fix

## Eliminated
<!-- Empty initially -->

## Evidence
- timestamp: 2026-05-05T00:00:00Z
  checked: quickice/gui/export.py lines 341-348 (IonGROMACSExporter.export_ion_gromacs)
  found: Code tries to copy from "quickice/topologies/thf.itp" but directory doesn't exist
  implication: THF .itp file won't be copied because path is wrong

- timestamp: 2026-05-05T00:00:00Z
  checked: quickice/data/ directory
  found: THF and CH4 .itp files are in quickice/data/, not quickice/topologies/
  implication: Path should be "data/" not "topologies/"

- timestamp: 2026-05-05T00:00:00Z
  checked: quickice/data/thf.itp residue names
  found: [ moleculetype ] name is "thf" (lowercase), [ atoms ] section uses "THF" (uppercase)
  implication: Residue name in .gro file should be "THF" to match [ atoms ] section

- timestamp: 2026-05-05T00:00:00Z
  checked: quickice/output/gromacs_writer.py get_guest_residue_name() function
  found: Function correctly reads residue name from .itp file or falls back to "THF"
  implication: Residue name generation is correct

- timestamp: 2026-05-05T00:05:00Z
  checked: Git history of export.py
  found: Recent commit 0f05868 (May 5 22:34:53) added solute .itp copy logic with wrong path
  implication: Bug introduced in recent fix for preserving solute information

- timestamp: 2026-05-05T00:05:00Z
  checked: Both IonGROMACSExporter (line 345) and SoluteGROMACSExporter (line 137)
  found: Both use "topologies" instead of "data"
  implication: Both exporters need to be fixed

- timestamp: 2026-05-05T00:10:00Z
  checked: Applied fix to both exporters
  found: Changed "topologies" to "data" in lines 137 and 345
  implication: Fix applied

- timestamp: 2026-05-05T00:15:00Z
  checked: Verified directory structure
  found: quickice/data/ exists with ch4.itp, thf.itp, tip4p-ice.itp; topologies/ does not exist
  implication: Fix is correct

## Resolution
root_cause: Export code uses incorrect path "topologies/" instead of "data/" for solute .itp files. The topologies directory doesn't exist, causing thf.itp and ch4.itp files to not be copied during export.
fix: Changed "topologies" to "data" in IonGROMACSExporter (line 345) and SoluteGROMACSExporter (line 137)
verification: Directory structure verified - data/ exists with all required .itp files, topologies/ does not exist
files_changed: [quickice/gui/export.py]
