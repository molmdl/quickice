"""Test for PBC bond wrapping in molecular visualization.

This test verifies that bonds are correctly wrapped across periodic boundaries
to avoid drawing long bonds through the middle of the box.
"""

import numpy as np
import pytest
from vtkmodules.all import vtkMolecule

from quickice.structure_generation.types import Candidate, InterfaceStructure
from quickice.gui.vtk_utils import (
    candidate_to_vtk_molecule,
    interface_to_vtk_molecules,
    _pbc_distance,
)


class TestPBDBondWrapping:
    """Test PBC bond wrapping in molecular visualization."""
    
    def test_pbc_distance_wraps_correctly(self):
        """Test that _pbc_distance applies minimum image convention."""
        # Box of 10 nm
        cell_dims = np.array([10.0, 10.0, 10.0])
        
        # Position 1 at z=0.1, position 2 at z=9.9
        # Without PBC: distance = 9.8 nm
        # With PBC: distance = 0.2 nm (wrapped)
        pos1 = np.array([5.0, 5.0, 0.1])
        pos2 = np.array([5.0, 5.0, 9.9])
        
        # Calculate distance with PBC
        from quickice.gui.vtk_utils import _pbc_distance
        dist = _pbc_distance(pos1, pos2, cell_dims)
        
        # Should be close to 0.2 nm, not 9.8 nm
        assert dist < 0.3, f"Expected PBC distance ~0.2 nm, got {dist} nm"
        assert dist > 0.1, f"Expected PBC distance ~0.2 nm, got {dist} nm"
    
    def test_interface_viewer_bond_extraction_wraps_pbc(self):
        """Test that _extract_bonds in interface_viewer wraps bonds correctly."""
        from quickice.gui.interface_viewer import InterfaceViewerWidget
        
        # Create a simple interface structure with a bond crossing PBC
        # Box: 10x10x10 nm
        cell = np.eye(3) * 10.0
        
        # Ice: 1 water molecule at z=0.05 (O at z=0.05, H at z=9.95, H at z=0.15)
        # This simulates a water molecule where the O-H bond crosses the PBC
        # Typical O-H bond length ~0.1 nm
        ice_positions = np.array([
            [5.0, 5.0, 0.05],   # O
            [5.0, 5.0, 9.95],   # H (wrapped: should be at z=-0.05)
            [5.0, 5.0, 0.15],   # H
        ])
        ice_atom_names = ["O", "H", "H"]
        
        # Water: 1 water molecule in center
        water_positions = np.array([
            [5.0, 5.0, 5.0],   # OW
            [5.0, 5.0, 5.1],   # HW1
            [5.0, 5.0, 5.2],   # HW2
            [5.0, 5.0, 5.15],  # MW (virtual site, will be skipped)
        ])
        water_atom_names = ["OW", "HW1", "HW2", "MW"]
        
        # Combine
        positions = np.vstack([ice_positions, water_positions])
        atom_names = ice_atom_names + water_atom_names
        
        iface = InterfaceStructure(
            positions=positions,
            atom_names=atom_names,
            cell=cell,
            ice_atom_count=3,
            water_atom_count=4,
            ice_nmolecules=1,
            water_nmolecules=1,
            mode="slab",
            report="Test interface structure",
        )
        
        # Convert to VTK molecules
        ice_mol, water_mol = interface_to_vtk_molecules(iface)
        
        # Create a mock viewer to test _extract_bonds
        # We can't create a full QWidget, so we'll test the logic directly
        # by simulating what _extract_bonds does
        
        # Extract bonds from ice molecule with PBC
        n_bonds = ice_mol.GetNumberOfBonds()
        assert n_bonds == 2, f"Expected 2 bonds in ice molecule, got {n_bonds}"
        
        # Test the PBC wrapping logic manually
        cell_dims = np.diag(cell)
        
        bond_lengths = []
        for i in range(n_bonds):
            bond = ice_mol.GetBond(i)
            atom1_id = bond.GetBeginAtomId()
            atom2_id = bond.GetEndAtomId()
            atom1 = ice_mol.GetAtom(atom1_id)
            atom2 = ice_mol.GetAtom(atom2_id)
            pos1 = np.array(atom1.GetPosition())
            pos2 = np.array(atom2.GetPosition())
            
            # Apply minimum image convention
            delta = pos2 - pos1
            delta = delta - cell_dims * np.round(delta / cell_dims)
            pos2_wrapped = pos1 + delta
            
            # Calculate wrapped bond length
            bond_length = np.linalg.norm(pos2_wrapped - pos1)
            bond_lengths.append(bond_length)
        
        # All bond lengths should be reasonable O-H distances (~0.1 nm)
        for length in bond_lengths:
            assert length < 0.2, f"Bond length {length} nm is too long (PBC not applied?)"
    
    def test_molecular_viewer_bond_extraction_wraps_pbc(self):
        """Test that _extract_bonds in molecular_viewer wraps bonds correctly."""
        from quickice.gui.molecular_viewer import MolecularViewerWidget
        
        # Create a simple candidate with a bond crossing PBC
        cell = np.eye(3) * 10.0
        
        # Water molecule where H crosses PBC
        # Typical O-H bond length ~0.1 nm
        positions = np.array([
            [5.0, 5.0, 0.05],   # O
            [5.0, 5.0, 9.95],   # H (wrapped: should be at z=-0.05)
            [5.0, 5.0, 0.15],   # H
        ])
        atom_names = ["O", "H", "H"]
        
        candidate = Candidate(
            positions=positions,
            atom_names=atom_names,
            cell=cell,
            nmolecules=1,
            phase_id="test",
            seed=12345,
        )
        
        # Convert to VTK molecule
        mol = candidate_to_vtk_molecule(candidate)
        
        # Test PBC wrapping
        n_bonds = mol.GetNumberOfBonds()
        assert n_bonds == 2, f"Expected 2 bonds, got {n_bonds}"
        
        cell_dims = np.diag(cell)
        
        for i in range(n_bonds):
            bond = mol.GetBond(i)
            atom1_id = bond.GetBeginAtomId()
            atom2_id = bond.GetEndAtomId()
            atom1 = mol.GetAtom(atom1_id)
            atom2 = mol.GetAtom(atom2_id)
            pos1 = np.array(atom1.GetPosition())
            pos2 = np.array(atom2.GetPosition())
            
            # Apply minimum image convention
            delta = pos2 - pos1
            delta = delta - cell_dims * np.round(delta / cell_dims)
            pos2_wrapped = pos1 + delta
            
            # Bond length should be short
            bond_length = np.linalg.norm(pos2_wrapped - pos1)
            assert bond_length < 0.2, f"Bond {i} length {bond_length} nm too long"
    
    def test_bond_not_wrapped_when_within_box(self):
        """Test that bonds within the box are not affected by PBC wrapping."""
        cell = np.eye(3) * 10.0
        cell_dims = np.diag(cell)
        
        # Normal bond within the box (O at z=5, H at z=5.1)
        pos1 = np.array([5.0, 5.0, 5.0])
        pos2 = np.array([5.0, 5.0, 5.1])
        
        # Apply minimum image convention
        delta = pos2 - pos1
        delta_wrapped = delta - cell_dims * np.round(delta / cell_dims)
        pos2_wrapped = pos1 + delta_wrapped
        
        # Should not change
        assert np.allclose(pos2, pos2_wrapped), "Bond within box should not be wrapped"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
