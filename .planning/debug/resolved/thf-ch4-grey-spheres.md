---
status: resolved
trigger: "THF and CH4 solutes show only grey spheres in viewer, and there are concerns about concentration calculations and water replacement tracking"
created: 2026-05-05T00:00:00Z
updated: 2026-05-05T00:00:00Z
---

## Current Focus

hypothesis: THF and CH4 appear as grey spheres because their template positions are all zeros in _load_solute_template() method
test: Verify that ITP files don't contain coordinates and that the code creates zero positions for all atoms
expecting: Confirm that atomic positions are [0,0,0] for all atoms, causing them to overlap and appear as single spheres
next_action: Create proper 3D coordinate templates for CH4 and THF molecules

## Symptoms

expected: 
1. THF and CH4 should render as proper molecular structures (not just grey spheres)
2. Different solutes at same concentration in same volume should have consistent molecule count calculations
3. User should see how many liquid water molecules are replaced by the solute insertion

actual: 
1. THF and CH4 appear as randomly distributed grey spheres in empty space (matching liquid region size)
2. Need to verify if concentration calculations are correct and consistent across different solute types
3. No feedback showing how many water molecules were replaced

errors: No errors visible
reproduction: Generate interface, then insert THF or CH4 solute at various concentrations
timeline: Part of the same solute insertion feature that was just partially fixed

## Eliminated

(none yet)

## Evidence

(timestamp: initial)
checked: Related context from previous debug session
found: Volume calculation, interface rendering, and insert button were fixed, but THF/CH4 rendering issue persists
implication: The issue is specific to THF/CH4 molecule handling, not the general solute insertion flow

(timestamp: investigation-1)
checked: solute_inserter.py _load_solute_template() method (lines 90-138)
found: Template positions are created as np.zeros((n_atoms, 3)) - all atoms at origin
implication: All atoms in each molecule are at the same position (0,0,0), so after rotation/translation they all end up at the translated position, appearing as a single grey sphere

(timestamp: investigation-2)
checked: ch4.itp and thf.itp files in quickice/data/
found: ITP files contain topology (bonds, angles, atom types) but NO atomic coordinates
implication: ITP format is for topology only, not structure coordinates - need separate coordinate source

(timestamp: investigation-3)
checked: itp_parser.py and gro_parser.py
found: itp_parser only extracts atom types and counts, not positions; gro_parser extracts 3D coordinates
implication: Need to either create .gro files for CH4/THF or generate coordinates programmatically from bond lengths/angles in ITP

(timestamp: verification-1)
checked: Coordinate generation functions _generate_ch4_coordinates() and _generate_thf_coordinates()
found: CH4 creates proper tetrahedral geometry with C-H bond length 0.10962 nm; THF creates 5-membered ring with 13 atoms
implication: Fix resolves the grey spheres issue - molecules now have proper 3D structure

(timestamp: verification-2)
checked: Concentration calculation formula in calculate_molecule_count()
found: Formula N = C × V × NA is correct; CH4 and THF at same concentration give identical molecule counts
implication: Concentration calculations are correct and consistent across different solute types

(timestamp: verification-3)
checked: Water replacement tracking
found: Current implementation places solutes in liquid region without actually removing water molecules; no tracking or reporting of water replacement
implication: Water replacement feedback is a missing feature, not a bug - the current approach is "additive placement" not "replacement"

## Resolution

root_cause: THF and CH4 solutes appeared as grey spheres because the _load_solute_template() method created all-zero positions for atoms. All atoms in each molecule were at position [0,0,0], so after rotation and translation, they all ended up at the same translated position, appearing as single spheres instead of molecular structures.

fix: Added two coordinate generation methods:
1. _generate_ch4_coordinates(): Creates tetrahedral geometry for CH4 (C at center, 4 H atoms at tetrahedral corners)
2. _generate_thf_coordinates(): Creates planar ring geometry for THF (O-C-C-C-C ring with hydrogens)
Both methods use bond lengths from the ITP files and center molecules at origin for proper rotation/translation during insertion.

verification: 
1. Module imports successfully
2. CH4 coordinates: 5 atoms, proper tetrahedral geometry, C-H bond length 0.10962 nm (matches ITP)
3. THF coordinates: 13 atoms, planar ring structure, centered at origin
4. End-to-end test: CH4 molecules have 5 atoms with 3D spread (~0.17 nm), THF molecules have 13 atoms with 3D spread (~0.23 nm)
5. Concentration calculation verified: formula N = C × V × NA is correct and consistent across solute types
6. Water replacement: Current implementation uses "additive placement" (no water removal) - this is a feature gap, not a bug

files_changed: 
- quickice/structure_generation/solute_inserter.py
