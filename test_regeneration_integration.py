#!/usr/bin/env python3
"""Integration test to verify the fix handles regeneration correctly.

This test simulates the user workflow:
1. First generation completes successfully
2. User clicks generate again (regeneration)
3. Dialog appears asking what to do
4. Proper cleanup and regeneration occurs
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import numpy as np

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QThread

from quickice.gui.main_window import MainWindow
from quickice.structure_generation.types import InterfaceStructure, CustomMoleculeStructure


@pytest.fixture
def app():
    """Create QApplication for testing."""
    if not QApplication.instance():
        return QApplication([])
    return QApplication.instance()


@pytest.fixture
def main_window(app):
    """Create MainWindow for testing."""
    return MainWindow()


@pytest.fixture
def mock_interface():
    """Create mock interface structure."""
    interface = Mock(spec=InterfaceStructure)
    interface.ice_nmolecules = 100
    interface.water_nmolecules = 1000
    interface.ice_atom_count = 300
    interface.water_atom_count = 3000
    interface.guest_atom_count = 0
    interface.positions = np.random.rand(3300, 3) * 5.0
    interface.atom_names = ['O', 'H', 'H'] * 1100
    interface.cell = np.eye(3) * 5.0
    return interface


@pytest.fixture
def mock_custom_result():
    """Create mock custom molecule result."""
    result = Mock(spec=CustomMoleculeStructure)
    result.custom_molecule_count = 10
    result.custom_molecule_atom_count = 100
    result.ice_atom_count = 300
    result.water_atom_count = 3000
    result.guest_atom_count = 0
    result.positions = np.random.rand(3400, 3) * 5.0
    result.atom_names = ['C'] * 100
    result.cell = np.eye(3) * 5.0
    result.moleculetype_name = "CustomMol"
    result.interface_structure = Mock(spec=InterfaceStructure)
    result.interface_structure.water_nmolecules = 950  # Some water replaced
    return result


class TestRegenerationFix:
    """Test regeneration crash fix."""
    
    def test_dialog_shown_on_regeneration(self, main_window, mock_interface, mock_custom_result):
        """Test that dialog is shown when regenerating with previous insertion."""
        # Setup: Simulate first generation completed
        main_window._current_interface_result = mock_interface
        main_window._current_custom_molecule_result = mock_custom_result
        main_window.custom_molecule_panel._has_previous_insertion = True
        
        # Mock the dialog to return Cancel
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.No) as mock_dialog:
            # Trigger regeneration
            main_window._on_custom_generate_clicked()
            
            # Verify dialog was shown
            mock_dialog.assert_called_once()
            assert "Previous Custom Molecules Found" in mock_dialog.call_args[0][1]
    
    def test_clear_on_user_confirmation(self, main_window, mock_interface, mock_custom_result):
        """Test that previous results are cleared when user confirms."""
        # Setup: Simulate first generation completed
        main_window._current_interface_result = mock_interface
        main_window._current_custom_molecule_result = mock_custom_result
        main_window.custom_molecule_panel._has_previous_insertion = True
        main_window.export_custom_action.setEnabled(True)
        
        # Mock the dialog to return Yes (clear and regenerate)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            # Mock worker creation to avoid actual processing
            with patch('quickice.gui.custom_molecule_worker.CustomMoleculeWorker') as MockWorker:
                mock_worker = Mock()
                mock_worker.finished = Mock()
                mock_worker.finished.connect = Mock()
                mock_worker.error = Mock()
                mock_worker.error.connect = Mock()
                mock_worker.status = Mock()
                mock_worker.status.connect = Mock()
                mock_worker.progress = Mock()
                mock_worker.progress.connect = Mock()
                MockWorker.return_value = mock_worker
                
                # Trigger regeneration
                main_window._on_custom_generate_clicked()
                
                # Verify previous results were cleared
                assert main_window._current_custom_molecule_result is None
                assert main_window.custom_molecule_panel._has_previous_insertion == False
                assert main_window.export_custom_action.isEnabled() == False
    
    def test_button_disabled_during_processing(self, main_window, mock_interface):
        """Test that generate button is disabled during processing."""
        # Setup
        main_window._current_interface_result = mock_interface
        main_window.custom_molecule_panel._has_previous_insertion = False
        
        # Mock validation and worker
        with patch.object(main_window.custom_molecule_panel, 'get_configuration') as mock_config:
            mock_config.return_value = Mock()
            
            with patch('quickice.gui.custom_molecule_worker.CustomMoleculeWorker') as MockWorker:
                mock_worker = Mock()
                mock_worker.finished = Mock()
                mock_worker.finished.connect = Mock()
                mock_worker.error = Mock()
                mock_worker.error.connect = Mock()
                mock_worker.status = Mock()
                mock_worker.status.connect = Mock()
                mock_worker.progress = Mock()
                mock_worker.progress.connect = Mock()
                MockWorker.return_value = mock_worker
                
                # Enable button first
                main_window.custom_molecule_panel.generate_button.setEnabled(True)
                
                # Trigger generation
                main_window._on_custom_generate_clicked()
                
                # Verify button was disabled
                assert main_window.custom_molecule_panel.generate_button.isEnabled() == False
    
    def test_button_reenabled_after_completion(self, main_window, mock_interface, mock_custom_result):
        """Test that generate button is re-enabled after completion."""
        # Setup
        main_window._current_interface_result = mock_interface
        main_window.custom_molecule_panel.generate_button.setEnabled(False)  # Simulate disabled state
        
        # Trigger completion handler
        main_window._on_custom_finished(mock_custom_result)
        
        # Verify button was re-enabled
        assert main_window.custom_molecule_panel.generate_button.isEnabled() == True
    
    def test_button_reenabled_on_error(self, main_window, mock_interface):
        """Test that generate button is re-enabled even if error occurs."""
        # Setup
        main_window._current_interface_result = mock_interface
        
        # Mock an error during worker creation
        with patch.object(main_window.custom_molecule_panel, 'get_configuration') as mock_config:
            mock_config.return_value = Mock()
            
            with patch('quickice.gui.custom_molecule_worker.CustomMoleculeWorker', side_effect=Exception("Test error")):
                # Enable button first
                main_window.custom_molecule_panel.generate_button.setEnabled(True)
                
                # Trigger generation (will fail)
                main_window._on_custom_generate_clicked()
                
                # Verify button was re-enabled despite error
                assert main_window.custom_molecule_panel.generate_button.isEnabled() == True
    
    def test_no_dialog_without_previous_insertion(self, main_window, mock_interface):
        """Test that no dialog is shown when no previous insertion exists."""
        # Setup
        main_window._current_interface_result = mock_interface
        main_window.custom_molecule_panel._has_previous_insertion = False
        
        # Mock dialog to fail if called
        with patch.object(QMessageBox, 'question') as mock_dialog:
            mock_dialog.side_effect = AssertionError("Dialog should not be shown")
            
            # Mock validation and worker
            with patch.object(main_window.custom_molecule_panel, 'get_configuration') as mock_config:
                mock_config.return_value = Mock()
                
                with patch('quickice.gui.custom_molecule_worker.CustomMoleculeWorker') as MockWorker:
                    mock_worker = Mock()
                    mock_worker.finished = Mock()
                    mock_worker.finished.connect = Mock()
                    mock_worker.error = Mock()
                    mock_worker.error.connect = Mock()
                    mock_worker.status = Mock()
                    mock_worker.status.connect = Mock()
                    mock_worker.progress = Mock()
                    mock_worker.progress.connect = Mock()
                    MockWorker.return_value = mock_worker
                    
                    # Trigger generation - should not show dialog
                    main_window._on_custom_generate_clicked()
                    
                    # Dialog should not have been called
                    mock_dialog.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
