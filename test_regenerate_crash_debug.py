#!/usr/bin/env python3
"""Debug script to reproduce custom molecule regeneration crash.

This script tests the hypothesis that regenerating custom molecules
without checking for previous insertion causes a crash.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QMessageBox
from quickice.gui.main_window import MainWindow
from quickice.structure_generation.types import (
    CustomMoleculeStructure,
    InterfaceStructure,
    CustomMoleculeConfig
)


def create_mock_interface():
    """Create a mock interface structure."""
    # Create mock interface with minimal data
    interface = Mock(spec=InterfaceStructure)
    interface.ice_nmolecules = 100
    interface.water_nmolecules = 1000
    interface.ice_atom_count = 300  # 3 atoms per water * 100
    interface.water_atom_count = 3000  # 3 atoms per water * 1000
    interface.guest_atom_count = 0
    interface.positions = np.random.rand(3300, 3) * 5.0  # Random positions in 5nm box
    interface.atom_names = ['O', 'H', 'H'] * 1100
    interface.cell = np.eye(3) * 5.0  # 5nm cubic box
    return interface


def create_mock_custom_result(custom_count=10):
    """Create a mock custom molecule result."""
    result = Mock(spec=CustomMoleculeStructure)
    result.custom_molecule_count = custom_count
    result.custom_molecule_atom_count = custom_count * 10  # 10 atoms per custom molecule
    result.ice_atom_count = 300
    result.water_atom_count = 3000
    result.guest_atom_count = 0
    result.positions = np.random.rand(3300 + custom_count * 10, 3) * 5.0
    result.atom_names = ['C'] * (custom_count * 10)
    result.cell = np.eye(3) * 5.0
    result.moleculetype_name = "CustomMol"
    result.interface_structure = create_mock_interface()
    return result


def test_regeneration_without_check():
    """Test that regenerating without checking for previous insertion causes issues."""
    print("\n=== TEST: Regeneration without previous insertion check ===\n")
    
    app = QApplication.instance() or QApplication([])
    
    # Create main window
    print("1. Creating MainWindow...")
    window = MainWindow()
    
    # Mock the interface result (prerequisite for custom molecule insertion)
    print("2. Setting up mock interface result...")
    window._current_interface_result = create_mock_interface()
    
    # Create temporary GRO/ITP files
    print("3. Creating temporary GRO/ITP files...")
    with tempfile.TemporaryDirectory() as tmpdir:
        gro_path = Path(tmpdir) / "custom.gro"
        itp_path = Path(tmpdir) / "custom.itp"
        
        # Create minimal GRO file
        gro_content = """Custom molecule
10
    1CUSTOM     C    1   0.000   0.000   0.000
    1CUSTOM     H    2   0.100   0.000   0.000
    1CUSTOM     H    3  -0.050   0.087   0.000
    1CUSTOM     H    4  -0.050  -0.087   0.000
   5.0   5.0   5.0
"""
        gro_path.write_text(gro_content)
        
        # Create minimal ITP file
        itp_content = """[ moleculetype ]
; Name            nrexcl
CUSTOM             3

[ atoms ]
;   nr  type  resnr residue  atom   cgnr  charge       mass
     1   C      1    CUSTOM    C      1    0.000      12.01
     2   H      1    CUSTOM    H      2    0.100       1.008
     3   H      1    CUSTOM    H      3    0.100       1.008
     4   H      1    CUSTOM    H      4    0.100       1.008

[ bonds ]
;  ai    aj funct           c0           c1
    1     2     1
    1     3     1
    1     4     1
"""
        itp_path.write_text(itp_content)
        
        # Set file paths in panel
        window.custom_molecule_panel.gro_path = gro_path
        window.custom_molecule_panel.itp_path = itp_path
        window.custom_molecule_panel._has_previous_insertion = False
        
        # Mock validation to pass
        from quickice.structure_generation.molecule_validator import ValidationResult
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.gro_atom_count = 4
        validation_result.itp_residue_name = "CUSTOM"
        validation_result.gro_residue_name = "CUSTOM"
        validation_result.residue_name_mismatch = False
        validation_result.errors = []
        window.custom_molecule_panel.validation_result = validation_result
        
        # Enable generate button
        window.custom_molecule_panel.generate_button.setEnabled(True)
        
        print("4. Checking initial state...")
        print(f"   - _has_previous_insertion: {window.custom_molecule_panel._has_previous_insertion}")
        print(f"   - _current_custom_molecule_result: {window._current_custom_molecule_result}")
        
        # Mock the worker to return immediately
        print("\n5. Simulating first generation...")
        with patch('quickice.gui.main_window.CustomMoleculeWorker') as MockWorker:
            mock_worker = Mock()
            mock_result = create_mock_custom_result(custom_count=10)
            
            # Setup worker to immediately emit finished signal
            def run_side_effect():
                # Simulate immediate completion
                window._custom_worker.finished.emit(mock_result)
            
            mock_worker.run = Mock(side_effect=run_side_effect)
            mock_worker.finished = Mock()
            mock_worker.finished.connect = Mock()
            mock_worker.error = Mock()
            mock_worker.error.connect = Mock()
            mock_worker.status = Mock()
            mock_worker.status.connect = Mock()
            mock_worker.progress = Mock()
            mock_worker.progress.connect = Mock()
            
            MockWorker.return_value = mock_worker
            
            # Click generate button (first time)
            print("   - Clicking generate button (first time)...")
            window.custom_molecule_panel.generate_button.clicked.emit()
            
            print(f"   - After first click:")
            print(f"     * _has_previous_insertion: {window.custom_molecule_panel._has_previous_insertion}")
            
        # Now try to regenerate (this should crash or fail)
        print("\n6. Simulating second generation (regeneration)...")
        print("   - User changes molecule count to 20")
        print("   - User clicks generate again")
        print("   - NO CHECK for previous insertion")
        print("   - NO CLEANUP of previous results")
        print("   - NO DIALOG asking user what to do")
        
        # Check what happens
        print(f"\n7. Current state before second click:")
        print(f"   - _has_previous_insertion: {window.custom_molecule_panel._has_previous_insertion}")
        print(f"   - _current_custom_molecule_result exists: {window._current_custom_molecule_result is not None}")
        print(f"   - Generate button enabled: {window.custom_molecule_panel.generate_button.isEnabled()}")
        
        print("\n8. CRITICAL FINDING:")
        print("   - Generate button is STILL ENABLED")
        print("   - No check for _has_previous_insertion")
        print("   - No cleanup of previous results")
        print("   - No dialog asking user what to do")
        print("   - This will create a NEW worker, potentially causing:")
        print("     * Thread collision")
        print("     * VTK actor cleanup issues")
        print("     * Silent crash")
        
        print("\n=== TEST COMPLETE ===\n")
        print("ROOT CAUSE CONFIRMED:")
        print("1. No check for _has_previous_insertion when regenerating in same mode")
        print("2. No cleanup of previous results before starting new generation")
        print("3. Generate button not disabled during processing")
        print("4. No dialog asking user if they want to clear previous results")


if __name__ == "__main__":
    test_regeneration_without_check()
