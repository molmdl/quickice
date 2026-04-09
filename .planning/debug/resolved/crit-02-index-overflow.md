---
status: resolved
trigger: "CRIT-02 index-overflow"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - tile_structure produces incomplete molecules when atoms are filtered at boundaries
test: Verified with real pocket mode generation: ice_nmolecules=5, ice_atom_count=16 (should be 15)
expecting: Fix tile_structure to ensure complete molecules
next_action: Implement fix to filter atoms at molecule boundaries only

## Symptoms

expected: Water molecule iteration should correctly access water atoms without index overflow
actual: base_idx = iface.ice_atom_count + mol_idx * 4 can cause overflow if ice_atom_count != ice_nmolecules * 3
errors: Runtime IndexError crash or corrupted GRO output files with wrong atoms
reproduction: Generate interface where ice_atom_count != ice_nmolecules * 3 (e.g., after overlap removal), export to GRO
timeline: Potentially broken when ice atoms are removed during overlap resolution

## Eliminated

(No hypotheses eliminated yet)

## Evidence

- timestamp: initial
  checked: gromacs_writer.py lines 258-268
  found: Water molecule loop uses `base_idx = iface.ice_atom_count + mol_idx * 4`
  implication: This formula is correct IF ice atoms occupy indices 0 to ice_atom_count-1 and water atoms follow contiguously

- timestamp: initial
  checked: types.py InterfaceStructure dataclass
  found: 
    - ice_atom_count: Number of ice atoms (marks split between ice and water)
    - ice_nmolecules: Number of ice molecules
    - Ice uses 3 atoms/molecule, water uses 4 atoms/molecule
  implication: Invariant ice_atom_count == ice_nmolecules * 3 should hold

- timestamp: initial
  checked: overlap_resolver.py remove_overlapping_molecules function
  found: 
    - Returns (filtered_positions, n_molecules_remaining)
    - Both values are computed consistently: n_molecules_remaining = filtered_positions.size / atoms_per_molecule
  implication: Function maintains atom/molecule count consistency

- timestamp: initial
  checked: slab.py lines 132, 74 - ice_atom_count and ice_nmolecules calculation
  found:
    - Line 74: total_ice_nmolecules = bottom_ice_nmolecules + top_ice_nmolecules (NOT updated after water removal)
    - Line 132: ice_atom_count = len(combined_ice_positions)
    - Ice atoms are NOT removed in slab mode (only water molecules removed)
  implication: ice_atom_count = ice_nmolecules * 3 holds because ice is not modified

- timestamp: initial
  checked: pocket.py lines 85-89, 163
  found:
    - Lines 85-89: Ice molecules inside cavity ARE removed, ice_positions and ice_nmolecules BOTH updated
    - Line 163: ice_atom_count = len(ice_positions) 
    - ice_nmolecules is from remove_overlapping_molecules return value
  implication: ice_atom_count = ice_nmolecules * 3 should hold (both updated together)

- timestamp: initial
  checked: piece.py lines 129
  found:
    - Line 129: ice_atom_count = len(centered_ice_positions)
    - Ice molecules are NOT removed in piece mode (only water removed)
  implication: ice_atom_count = ice_nmolecules * 3 holds

- timestamp: confirmed_bug
  checked: Real pocket mode generation with assemble_pocket()
  found:
    - ice_nmolecules = 5
    - ice_atom_count = 16 (should be 15 for 5 molecules × 3 atoms)
    - Invariant violation: ice_atom_count != ice_nmolecules * 3
  implication: The bug IS REAL - invariant is violated

- timestamp: root_cause_found
  checked: water_filler.py tile_structure function lines 136, 163
  found:
    - Line 136: filtered = all_positions[keep_mask] - filters atoms individually
    - Line 163: n_molecules = n_tiled_atoms // atoms_per_molecule - truncates!
    - Test result: 152 atoms, 50 molecules (should be 150 atoms for 50 molecules)
    - 2 extra atoms = incomplete molecules
  implication: ROOT CAUSE - tile_structure filters atoms at boundaries without respecting molecule boundaries

## Resolution

root_cause: tile_structure in water_filler.py filters atoms individually at box boundaries without respecting molecule boundaries. This produces incomplete molecules (partial atoms belonging to a molecule). The molecule count is then truncated (n_molecules = n_tiled_atoms // atoms_per_molecule), leading to ice_atom_count != ice_nmolecules * atoms_per_molecule.

fix: Modified tile_structure to filter at molecule boundaries instead of individual atoms. Now checks if ALL atoms of each molecule are inside target region before keeping the molecule. This ensures n_molecules = len(positions) / atoms_per_molecule always holds.

verification: 
- Tested with pocket mode: ice_nmolecules=4, ice_atom_count=12 (4*3), invariant holds
- Tested with slab mode: ice_nmolecules=40, ice_atom_count=120 (40*3), invariant holds
- Tested with piece mode: ice_nmolecules=10, ice_atom_count=30 (10*3), invariant holds
- GRO export successful with correct atom counts
- All debug tests pass

files_changed:
- quickice/structure_generation/water_filler.py: tile_structure function (lines 105-173)
