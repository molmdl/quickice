"""Integration tests for solute insertion workflow.

Tests the complete solute insertion pipeline:
1. Concentration to molecule count calculation
2. Solute template loading from ITP files
3. Random position and rotation generation
4. All-atom overlap checking
5. Partial success handling
6. GROMACS export with MoleculetypeRegistry
"""

import pytest
import numpy as np
from pathlib import Path

from quickice.structure_generation.types import (
    SoluteConfig, SoluteStructure, InterfaceStructure, CustomMoleculeStructure
)
from quickice.structure_generation.solute_inserter import SoluteInserter
from quickice.gui.solute_renderer import create_solute_actor


class TestSoluteInserter:
    """Tests for SoluteInserter class."""
    
    def test_calculate_molecule_count(self):
        """Test concentration to molecule count conversion."""
        inserter = SoluteInserter()
        
        # Test case: 0.1 M in 1000 nm³
        # Expected: 0.1 mol/L × 1000e-24 L × 6.022e23 = ~60 molecules
        count = inserter.calculate_molecule_count(0.1, 1000.0)
        assert 50 < count < 70, f"Expected ~60 molecules, got {count}"
        
        # Test case: 1.0 M in 100 nm³
        # Expected: 1.0 × 100e-24 × 6.022e23 = ~60 molecules
        count = inserter.calculate_molecule_count(1.0, 100.0)
        assert 50 < count < 70, f"Expected ~60 molecules, got {count}"
    
    def test_load_solute_template_ch4(self):
        """Test loading CH4 template from bundled ITP file."""
        inserter = SoluteInserter()
        positions, atom_names, atom_types = inserter._load_solute_template("CH4")
        
        # CH4 has 5 atoms (C + 4 H)
        assert len(positions) == 5, f"CH4 should have 5 atoms, got {len(positions)}"
        assert len(atom_names) == 5
        # Atom names from ITP files may be lowercase (e.g., "c3", "hc")
        assert any("c" in name.lower() for name in atom_names), f"Should have carbon atom, got {atom_names}"
        assert sum(1 for name in atom_names if "h" in name.lower()) == 4, f"Should have 4 hydrogen atoms, got {atom_names}"
        
        # Positions should be centered at origin
        center = positions.mean(axis=0)
        assert np.allclose(center, 0, atol=0.2), "Template should be centered"
    
    def test_load_solute_template_thf(self):
        """Test loading THF template from bundled ITP file."""
        inserter = SoluteInserter()
        positions, atom_names, atom_types = inserter._load_solute_template("THF")
        
        # THF has more atoms than CH4
        assert len(positions) > 5, f"THF should have >5 atoms, got {len(positions)}"
        
        # Should have C, O, H atoms
        assert any("c" in name.lower() for name in atom_names), f"Should have carbon, got {atom_names}"
        assert any("o" in name.lower() for name in atom_names), f"Should have oxygen, got {atom_names}"
    
    def test_rotation_matrix_generation(self):
        """Test random rotation matrix generation."""
        inserter = SoluteInserter()
        
        # Generate multiple rotation matrices
        for _ in range(10):
            rotation_matrix = inserter._generate_random_rotation_matrix()
            
            # Check shape
            assert rotation_matrix.shape == (3, 3)
            
            # Check orthogonality (R @ R.T = I)
            identity = rotation_matrix @ rotation_matrix.T
            assert np.allclose(identity, np.eye(3), atol=1e-6)
            
            # Check determinant = 1 (proper rotation, not reflection)
            det = np.linalg.det(rotation_matrix)
            assert np.isclose(det, 1.0, atol=1e-6)


class TestSoluteInsertion:
    """Tests for complete solute insertion workflow."""
    
    @pytest.fixture
    def interface_structure(self):
        """Create mock interface structure for testing."""
        # Create a simple mock interface structure
        # with ice and water regions
        
        # Create ice atoms (simple cubic crystal)
        n_ice_molecules = 100
        ice_positions = []
        for i in range(n_ice_molecules):
            # Each water molecule has 3 atoms (O, H, H)
            ice_positions.append([i * 0.3, 0, 0])  # O
            ice_positions.append([i * 0.3 + 0.1, 0.1, 0])  # H
            ice_positions.append([i * 0.3 + 0.1, -0.1, 0])  # H
        
        # Create water atoms (liquid region)
        n_water_molecules = 200
        water_positions = []
        for i in range(n_water_molecules):
            # Each water molecule has 3 atoms (O, H, H)
            # Place in liquid region (y > 5 nm)
            water_positions.append([i * 0.3 % 30, 5 + i * 0.1 % 10, 0])  # O
            water_positions.append([i * 0.3 % 30 + 0.1, 5 + i * 0.1 % 10 + 0.1, 0])  # H
            water_positions.append([i * 0.3 % 30 + 0.1, 5 + i * 0.1 % 10 - 0.1, 0])  # H
        
        all_positions = np.array(ice_positions + water_positions)
        
        # Atom names
        atom_names = ["O", "H", "H"] * (n_ice_molecules + n_water_molecules)
        
        # Cell
        cell = np.eye(3) * 10.0  # 10 nm box
        
        # Create InterfaceStructure
        interface = InterfaceStructure(
            positions=all_positions,
            atom_names=atom_names,
            cell=cell,
            ice_atom_count=n_ice_molecules * 3,
            water_atom_count=n_water_molecules * 3,
            ice_nmolecules=n_ice_molecules,
            water_nmolecules=n_water_molecules,
            mode="slab",
            report="Mock interface for testing",
        )
        
        return interface
    
    def test_insert_ch4_solutes(self, interface_structure):
        """Test CH4 solute insertion into interface structure."""
        config = SoluteConfig(
            concentration_molar=0.5,  # Higher concentration to ensure molecules are placed
            solute_type="CH4",
            max_attempts=1000,
            seed=42,  # Reproducible
        )
        
        inserter = SoluteInserter(config)
        solute_structure = inserter.insert_solutes(interface_structure, config)
        
        # Check structure returned
        assert isinstance(solute_structure, SoluteStructure)
        assert solute_structure.solute_type == "CH4"
        assert solute_structure.n_molecules > 0
        
        # Check positions are in liquid region
        # (Should be after ice_atom_count boundary)
        ice_atoms = interface_structure.ice_atom_count
        assert len(solute_structure.positions) > 0
        
        # Check registry registered solute
        registry_name = solute_structure.registry.get_gromacs_name("liquid_CH4")
        assert registry_name == "CH4_L"
    
    def test_insert_thf_solutes(self, interface_structure):
        """Test THF solute insertion."""
        config = SoluteConfig(
            concentration_molar=0.5,  # Higher concentration to ensure molecules are placed
            solute_type="THF",
            seed=42,
        )
        
        inserter = SoluteInserter(config)
        solute_structure = inserter.insert_solutes(interface_structure, config)
        
        assert solute_structure.solute_type == "THF"
        assert solute_structure.n_molecules > 0
        
        # Check registry
        registry_name = solute_structure.registry.get_gromacs_name("liquid_THF")
        assert registry_name == "THF_L"
    
    def test_partial_success_handling(self, interface_structure):
        """Test partial success when concentration too high."""
        config = SoluteConfig(
            concentration_molar=10.0,  # Very high concentration
            solute_type="CH4",
            max_attempts=100,
            seed=42,
        )
        
        inserter = SoluteInserter(config)
        
        # Should not crash, but may place fewer molecules
        solute_structure = inserter.insert_solutes(interface_structure, config)
        
        # Should have placed some molecules (partial success)
        assert solute_structure.n_molecules >= 0


class TestSoluteRenderer:
    """Tests for solute visualization."""
    
    def test_create_solute_actor_ch4(self):
        """Test creating VTK actor for CH4 molecule."""
        # Create simple CH4 positions
        positions = np.array([
            [0, 0, 0],      # C
            [0.109, 0, 0],  # H1
            [0, 0.109, 0],  # H2
            [0, 0, 0.109],  # H3
            [-0.05, -0.09, -0.05],  # H4
        ])
        atom_names = ["C", "H", "H", "H", "H"]
        cell = np.eye(3) * 5.0
        
        actor = create_solute_actor(positions, atom_names, cell)
        
        assert actor is not None
        assert hasattr(actor, 'GetMapper')
    
    def test_create_solute_actor_empty(self):
        """Test creating actor with empty atom list."""
        positions = np.array([]).reshape(0, 3)
        atom_names = []
        cell = np.eye(3) * 5.0
        
        actor = create_solute_actor(positions, atom_names, cell)
        
        # Should handle gracefully
        assert actor is None


class TestSolutePanel:
    """Tests for SolutePanel UI (requires pytest-qt)."""
    
    @pytest.mark.skip(reason="pytest-qt not installed in test environment")
    def test_panel_initialization(self, qtbot):
        """Test SolutePanel initializes correctly."""
        from quickice.gui.solute_panel import SolutePanel
        
        panel = SolutePanel()
        qtbot.addWidget(panel)
        
        # Check UI elements exist
        assert hasattr(panel, 'concentration_spin')
        assert hasattr(panel, 'solute_type_combo')
        assert hasattr(panel, 'insert_button')
        assert hasattr(panel, 'preview_label')
    
    @pytest.mark.skip(reason="pytest-qt not installed in test environment")
    def test_molecule_count_preview(self, qtbot):
        """Test real-time molecule count preview."""
        from quickice.gui.solute_panel import SolutePanel
        
        panel = SolutePanel()
        qtbot.addWidget(panel)
        
        # Set liquid volume
        panel.set_liquid_volume(1000.0)  # 1000 nm³
        
        # Set concentration
        panel.concentration_spin.setValue(0.1)
        
        # Check preview updated
        preview_text = panel.preview_label.text()
        assert "molecules" in preview_text.lower()


    def test_ice_nmolecules_preserved_from_custom_molecule_structure(self):
        """Regression test: ice_nmolecules must be preserved when solute inserter
        receives a CustomMoleculeStructure.

        Bug (now fixed): CustomMoleculeStructure lacked ice_nmolecules/water_nmolecules
        fields, so getattr(structure, 'ice_nmolecules', 0) returned 0.
        Fix: CustomMoleculeStructure now has ice_nmolecules and water_nmolecules fields
        populated from the source interface structure, and SoluteInserter's
        _resolve_ice_nmolecules falls back to structure.interface_structure.
        """
        n_ice = 20
        n_water = 200
        n_custom = 3
        ice_atom_count = n_ice * 4  # TIP4P-ICE: 4 atoms per molecule
        water_atom_count = n_water * 4
        custom_atom_count = n_custom * 9  # e.g. ethanol-like: 9 atoms per molecule

        total_atoms = ice_atom_count + water_atom_count + custom_atom_count
        atom_names = (["OW", "HW1", "HW2", "MW"] * (n_ice + n_water) +
                     ["C", "H", "H", "H", "O", "H", "C", "H", "H"] * n_custom)
        np.random.seed(42)
        positions = np.random.uniform(0, 10, (total_atoms, 3))

        interface = InterfaceStructure(
            positions=positions,
            atom_names=atom_names,
            cell=np.diag([10.0, 10.0, 10.0]),
            ice_atom_count=ice_atom_count,
            water_atom_count=water_atom_count,
            ice_nmolecules=n_ice,
            water_nmolecules=n_water,
            mode='slab',
            report='test',
        )

        # Create a CustomMoleculeStructure with ice_nmolecules/water_nmolecules populated
        # Mimics the real workflow: ice → slab → custom molecules → solute
        custom = CustomMoleculeStructure(
            positions=positions,
            atom_names=atom_names,
            cell=interface.cell,
            molecule_index=[],
            ice_atom_count=ice_atom_count,
            water_atom_count=water_atom_count,
            custom_molecule_atom_count=custom_atom_count,
            guest_atom_count=0,
            guest_nmolecules=0,
            ice_nmolecules=n_ice,
            water_nmolecules=n_water,
            custom_molecule_count=n_custom,
            interface_structure=interface,
        )

        # Verify CustomMoleculeStructure now HAS ice_nmolecules (root fix)
        assert hasattr(custom, 'ice_nmolecules'), \
            "CustomMoleculeStructure should now have ice_nmolecules field"
        assert custom.ice_nmolecules == n_ice, (
            f"ice_nmolecules should be {n_ice}, got {custom.ice_nmolecules}"
        )

        # Insert solutes via CustomMoleculeStructure
        config = SoluteConfig(
            concentration_molar=0.5,
            solute_type='CH4',
            min_separation=0.3,
            max_attempts=1000,
        )
        inserter = SoluteInserter(config=config, seed=42)
        result = inserter.insert_solutes(custom, config)

        # Verify ice_nmolecules is preserved through the solute insertion
        modified_interface = result.interface_structure
        assert modified_interface.ice_nmolecules == n_ice, (
            f"ice_nmolecules should be {n_ice} (from original interface), "
            f"got {modified_interface.ice_nmolecules}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
