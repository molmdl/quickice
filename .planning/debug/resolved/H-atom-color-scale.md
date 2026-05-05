---
status: resolved
trigger: "H atoms in THF and CH4 solutes have wrong color/scale - need to match hydrate interface display"
created: 2026-05-05T00:00:00Z
updated: 2026-05-05T00:00:00Z
---

## Current Focus

hypothesis: ROOT CAUSE CONFIRMED - solute_inserter.py uses atom types instead of atom names, causing H atoms to be labeled "hc" or "h1" instead of "H", which doesn't match guest_atomic_numbers dictionary
test: Fix ITP parser to extract atom names (column 5) instead of just types (column 2)
expecting: H atoms will be correctly labeled "H" and get atomic number 1 (white color)
next_action: Implement fix in itp_parser.py and solute_inserter.py

## Evidence

- timestamp: Initial investigation
  checked: solute_viewer.py, vtk_utils.py, solute_inserter.py, hydrate_renderer.py
  found: |
    1. solute_viewer.py line 317: Uses ball-and-stick with radius 0.25 * ANGSTROM_TO_NM
    2. vtk_utils.py line 501: guest_atomic_numbers.get(name, 6) - defaults to carbon if name not found!
    3. solute_inserter.py line 238: Uses atom_types as atom_names
    4. hydrate_renderer.py line 124-152: Extracts element from atom name using string parsing
  implication: If solute H atoms have types like "hc" instead of "H", they'll get atomic number 6 (carbon) instead of 1 (hydrogen), causing wrong CPK color

- timestamp: ITP file analysis
  checked: quickice/data/ch4.itp and quickice/data/thf.itp
  found: |
    CH4 ITP:
    - Carbon: type=c3, name=C (line 15)
    - Hydrogens: type=hc, name=H (lines 16-19)
    
    THF ITP:
    - Oxygen: type=os, name=O (line 17)
    - Carbons: type=c5, names=CA,CB (lines 18-21)
    - Hydrogens: type=hc or h1, name=H (lines 22-29)
    
    ITP parser (itp_parser.py line 111):
    - Only extracts fields[1] (atom type), not fields[4] (atom name)
    - solute_inserter.py line 238 uses itp_info.atom_types as atom_names
  implication: H atoms are labeled "hc" or "h1" instead of "H", causing them to default to atomic number 6 (carbon/gray) instead of 1 (hydrogen/white)

## Symptoms

expected: H atoms should display with correct color (WHITE) and scale matching hydrate interface guest display
actual: H atoms have wrong color/scale in solute viewer after insertion
errors: No errors
reproduction: Insert THF or CH4 solute and compare H atom appearance to hydrate interface guests
started: Discovered after fixing water replacement and ANGSTROM_TO_NM issues

## Eliminated

## Evidence

## Resolution

root_cause: solute_inserter.py uses atom types (e.g., "hc", "h1") instead of atom names (e.g., "H") when creating SoluteStructure. The atom types don't match the guest_atomic_numbers dictionary in vtk_utils.py, causing H atoms to default to atomic number 6 (carbon/gray) instead of 1 (hydrogen/white). The ITP parser only extracts atom types (column 2), not atom names (column 5).
fix: Updated ITP parser to extract both atom types and atom names, then modified solute_inserter.py to use atom names for visualization. This ensures H atoms are correctly identified as "H" and get atomic number 1 (white color).
verification: |
  - Tested CH4 template: H atoms now labeled "H" -> atomic #1 -> WHITE ✓
  - Tested THF template: All 8 H atoms labeled "H" -> atomic #1 -> WHITE ✓
  - All existing tests pass (test_solute_insertion.py, test_custom_molecule.py)
  - Comprehensive verification confirms H atoms get correct color
files_changed:
  - quickice/structure_generation/itp_parser.py: Added atom_names field to ITPMoleculeInfo, updated parser to extract atom names (column 5)
  - quickice/structure_generation/solute_inserter.py: Updated _load_solute_template to use atom_names instead of atom_types for visualization
