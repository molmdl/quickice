---
status: resolved
trigger: "hydrate-missing-guest (REAL DATA TRACE)"
created: 2026-04-24T00:00:00
updated: 2026-04-24T00:00:00
---

## Current Focus

**COMPLETED**

## Symptoms

### Expected Behavior
When using real GenIce2-generated hydrate structures (from hydrate_generator.py -> HydrateStructure.to_candidate()), guest molecule atoms should appear in the piece interface output alongside water framework and water box atoms.

### Actual Behavior
The user reported that the hydrate interface shows issues when using "actual application" with "real GenIce2 data" - but test with manually created hydrate structures worked correctly.

### Investigation Notes
This was a CLARIFICATION investigation to verify what happens with REAL GenIce2 data vs mock/manually created test data.

## Investigation Steps Taken

### Step 1: Verified GenIce2 availability
- `genice2 --version` → 2.2.13.1 available

### Step 2: Generated test hydrate with GenIce2 CLI
```bash
genice2 CS1 --water tip4p --guest 12=ch4 --guest 14=ch4
```
Output showed correct atom naming:
- Water: OW, HW1, HW2, MW (4 atoms per TIP4P water)
- Guests: C, H, H, H, H (5 atoms per CH4 - 1 carbon + 4 hydrogens)

### Step 3: Traced hydrate generation in Python
HydrateStructureGenerator.generate() correctly produces:
- 46 water molecules × 4 atoms = 184 water framework atoms
- 8 guest molecules × 5 atoms = 40 guest atoms
- Total: 224 atoms

### Step 4: Verified molecule_index building
The `_build_molecule_index()` correctly identifies:
- 46 water molecules (mol_type = "water")  
- 8 guest molecules (mol_type = "ch4")

### Step 5: Verified candidate conversion
- `hydrate.to_candidate()` correctly produces candidate with all 224 atoms
- Metadata correctly includes `original_hydrate: True`

### Step 6: Verified guest detection in piece.py
`_detect_guest_atoms()` correctly identifies:
- water_indices: 184 (OW-based atoms)
- guest_indices: 40 (C, H atoms)

### Step 7: Verified full piece assembly
`assemble_piece()` produces correct output:
- ice_atom_count: 128 (water framework atoms after tiling)
- guest_atom_count: 40 (guest atoms) - **Key metric**
- guest_nmolecules: 8
- water_atom_count: 776 (water box atoms)
- Total: 944 atoms

### Step 8: Verified VTK conversion
`interface_to_vtk_molecules()` correctly renders:
- ice_vtk: 96 atoms (OW-based, MW skipped)
- water_vtk: 582 atoms  
- guest_vtk: 40 atoms (8 CH4 molecules with 5 atoms each)

## Root Cause

**No bug found.** The code correctly handles REAL GenIce2 data.

The reported "issues with real GenIce2 data" may have been:
1. Previous (already fixed) bugs from earlier in the session
2. UI issues (rendering, not generation)
3. Export issues

## Evidence Summary

1. GenIce2 produces correct atom naming: OW/HW1/HW2/MW for water, C/H/H/H/H for CH4
2. HydrateStructure correctly parses and stores all atoms
3. molecule_index correctly tracks water vs guest molecules
4. piece.py assemble_piece() correctly:
   - Extracts guest atoms using `_detect_guest_atoms()`
   - Combines ice + guest + water in correct order
   - Sets guest_atom_count correctly
5. VTK conversion correctly renders guests alongside ice/water

## Resolution

**VERIFIED WORKING**

The entire hydrate → interface pipeline works correctly with real GenIce2 data:
- Hydrate generation (GenIce2 → HydrateStructure)
- Candidate conversion (HydrateStructure → Candidate with metadata)
- Guest detection in piece assembly
- Guest atom counting and tracking  
- VTK molecule rendering

## Files Verified

- `quickice/structure_generation/hydrate_generator.py` - Generation ✓
- `quickice/structure_generation/modes/piece.py` - Guest handling ✓
- `quickice/gui/vtk_utils.py` - VTK conversion ✓

## Test Output

```
=== User flow: hydrate -> interface ===
Hydrate: 46 water, 8 guest molecules
Candidate original_hydrate: True

=== Interface Structure ===
ice_atom_count: 128
guest_atom_count: 40  
guest_nmolecules: 8
water_atom_count: 776
total atoms: 944

=== VTK Molecules ===
ice_vtk atoms: 96
water_vtk atoms: 582
guest_vtk atoms: 40

=== COMPLETE VERIFICATION ===
```