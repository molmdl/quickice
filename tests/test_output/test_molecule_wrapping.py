"""Test molecule-aware PBC wrapping."""

import numpy as np
import pytest
from quickice.output.gromacs_writer import wrap_molecules_into_box, wrap_positions_into_box
from quickice.structure_generation.types import MoleculeIndex


class TestWrapMoleculesIntoBox:
    """Test that molecules are wrapped as whole units."""
    
    def test_single_molecule_spanning_boundary(self):
        """Test a single water molecule spanning PBC boundary."""
        # Box: 7.45 x 7.45 x 10.93 nm
        cell = np.array([
            [7.45, 0.0, 0.0],
            [0.0, 7.45, 0.0],
            [0.0, 0.0, 10.93]
        ])
        
        # Water molecule with atoms near boundary
        # Some atoms will wrap, some won't in atom-by-atom wrapping
        positions = np.array([
            [7.40, 0.5, 0.5],   # O near boundary
            [7.45, 0.55, 0.5],  # H1 beyond boundary
            [7.35, 0.45, 0.5],  # H2 inside box
            [7.42, 0.5, 0.5],   # MW near boundary
        ])
        
        molecule_index = [
            MoleculeIndex(start_idx=0, count=4, mol_type="water")
        ]
        
        # Wrap molecules
        wrapped = wrap_molecules_into_box(positions, molecule_index, cell)
        
        # Check that all atoms are on same side of box (not split)
        x_coords = wrapped[:, 0]
        span = max(x_coords) - min(x_coords)
        
        # Should be less than half the box size (molecule kept together)
        assert span < cell[0, 0] / 2, f"Molecule split across PBC: span={span}"
        
        # Check relative distances are preserved
        for i in range(1, 4):
            orig_dist = np.linalg.norm(positions[i] - positions[0])
            wrap_dist = np.linalg.norm(wrapped[i] - wrapped[0])
            assert abs(orig_dist - wrap_dist) < 1e-10, \
                f"Relative distance changed for atom {i}"
    
    def test_multiple_molecules(self):
        """Test multiple molecules, some spanning boundaries."""
        cell = np.array([
            [10.0, 0.0, 0.0],
            [0.0, 10.0, 0.0],
            [0.0, 0.0, 10.0]
        ])
        
        # Three water molecules
        # 1st: well inside box (no wrapping needed)
        # 2nd: spanning X boundary (some atoms beyond 10.0)
        # 3rd: spanning Y boundary (some atoms below 0.0)
        positions = np.array([
            # Molecule 1: inside box
            [5.0, 5.0, 5.0],   # O
            [5.1, 5.0, 5.0],   # H1
            [5.0, 5.1, 5.0],   # H2
            [5.05, 5.05, 5.0], # MW
            
            # Molecule 2: spanning X boundary (atoms beyond 10.0)
            [9.9, 2.0, 2.0],   # O
            [10.1, 2.0, 2.0],  # H1 (beyond box)
            [9.8, 2.1, 2.0],   # H2
            [9.85, 2.05, 2.0], # MW
            
            # Molecule 3: spanning Y boundary (atoms below 0.0)
            [3.0, 0.2, 3.0],   # O
            [3.0, -0.1, 3.0],  # H1 (below 0)
            [3.1, 0.3, 3.0],   # H2
            [3.05, 0.15, 3.0], # MW
        ])
        
        molecule_index = [
            MoleculeIndex(start_idx=0, count=4, mol_type="water"),
            MoleculeIndex(start_idx=4, count=4, mol_type="water"),
            MoleculeIndex(start_idx=8, count=4, mol_type="water"),
        ]
        
        wrapped = wrap_molecules_into_box(positions, molecule_index, cell)
        
        # Check each molecule is kept together
        for mol_idx, mol in enumerate(molecule_index):
            start = mol.start_idx
            count = mol.count
            
            # Get coordinates for this molecule
            mol_coords = wrapped[start:start + count]
            
            # Check X and Y spans
            x_span = max(mol_coords[:, 0]) - min(mol_coords[:, 0])
            y_span = max(mol_coords[:, 1]) - min(mol_coords[:, 1])
            
            # Should be less than half box size
            assert x_span < cell[0, 0] / 2, \
                f"Molecule {mol_idx+1} split in X: span={x_span}"
            assert y_span < cell[1, 1] / 2, \
                f"Molecule {mol_idx+1} split in Y: span={y_span}"
    
    def test_molecule_already_inside_box(self):
        """Test molecule already inside box (no wrapping needed)."""
        cell = np.array([
            [10.0, 0.0, 0.0],
            [0.0, 10.0, 0.0],
            [0.0, 0.0, 10.0]
        ])
        
        positions = np.array([
            [5.0, 5.0, 5.0],
            [5.1, 5.0, 5.0],
            [5.0, 5.1, 5.0],
            [5.05, 5.05, 5.0],
        ])
        
        molecule_index = [
            MoleculeIndex(start_idx=0, count=4, mol_type="water")
        ]
        
        wrapped = wrap_molecules_into_box(positions, molecule_index, cell)
        
        # Should be unchanged
        np.testing.assert_array_almost_equal(wrapped, positions)
    
    def test_ion_molecules(self):
        """Test ion molecules (single atoms)."""
        cell = np.array([
            [10.0, 0.0, 0.0],
            [0.0, 10.0, 0.0],
            [0.0, 0.0, 10.0]
        ])
        
        # Single atom ions at various positions
        positions = np.array([
            [11.5, 5.0, 5.0],  # Na+ beyond X boundary
            [5.0, 5.0, 5.0],   # Cl- inside box
            [5.0, -0.5, 5.0],  # Na+ beyond Y boundary (negative)
        ])
        
        molecule_index = [
            MoleculeIndex(start_idx=0, count=1, mol_type="na"),
            MoleculeIndex(start_idx=1, count=1, mol_type="cl"),
            MoleculeIndex(start_idx=2, count=1, mol_type="na"),
        ]
        
        wrapped = wrap_molecules_into_box(positions, molecule_index, cell)
        
        # All should be wrapped into box
        for i, pos in enumerate(wrapped):
            assert 0.0 <= pos[0] < cell[0, 0], f"Ion {i} X out of bounds"
            assert 0.0 <= pos[1] < cell[1, 1], f"Ion {i} Y out of bounds"
            assert 0.0 <= pos[2] < cell[2, 2], f"Ion {i} Z out of bounds"
    
    def test_comparison_with_atom_by_atom_wrapping(self):
        """Compare molecule-aware vs atom-by-atom wrapping."""
        cell = np.array([
            [7.45, 0.0, 0.0],
            [0.0, 7.45, 0.0],
            [0.0, 0.0, 10.93]
        ])
        
        # Molecule spanning X boundary
        positions = np.array([
            [7.40, 0.5, 0.5],   # O
            [7.45, 0.55, 0.5],  # H1 beyond boundary
            [7.35, 0.45, 0.5],  # H2
            [7.42, 0.5, 0.5],   # MW
        ])
        
        molecule_index = [
            MoleculeIndex(start_idx=0, count=4, mol_type="water")
        ]
        
        # Atom-by-atom wrapping
        wrapped_atoms = wrap_positions_into_box(positions, cell)
        
        # Molecule-aware wrapping
        wrapped_mols = wrap_molecules_into_box(positions, molecule_index, cell)
        
        # Atom-by-atom should split molecule
        x_coords_atoms = wrapped_atoms[:, 0]
        span_atoms = max(x_coords_atoms) - min(x_coords_atoms)
        
        # Molecule-aware should keep together
        x_coords_mols = wrapped_mols[:, 0]
        span_mols = max(x_coords_mols) - min(x_coords_mols)
        
        # Atom-by-atom has larger span (split molecule)
        assert span_atoms > span_mols, \
            "Molecule-aware should keep atoms closer together"
        
        # Molecule-aware span should be small
        assert span_mols < 0.15, \
            f"Molecule atoms should be close: span={span_mols}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
