"""Test for custom molecule mode switching behavior.

Verifies that:
1. Mode switching with previous insertion shows dialog
2. User can choose to start fresh (clears results)
3. User can choose to add to existing (keeps results)
4. User can cancel mode switch
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QApplication
from quickice.gui.custom_molecule_panel import CustomMoleculePanel
from quickice.structure_generation.types import CustomMoleculeStructure, InterfaceStructure


@pytest.fixture
def app():
    """Create QApplication for testing."""
    if not QApplication.instance():
        return QApplication([])
    return QApplication.instance()


@pytest.fixture
def panel(app):
    """Create CustomMoleculePanel for testing."""
    return CustomMoleculePanel()


class TestModeSwitching:
    """Test mode switching behavior with previous insertion."""
    
    def test_no_dialog_without_previous_insertion(self, panel):
        """Test that no dialog is shown when no previous insertion exists."""
        # Set mode to Custom (no previous insertion)
        panel._has_previous_insertion = False
        
        # Switch mode should not show dialog
        with patch.object(QMessageBox, 'question') as mock_question:
            panel._on_placement_mode_changed("Custom")
            mock_question.assert_not_called()
        
        # Mode should change
        assert panel.placement_mode == "Custom"
    
    def test_dialog_shown_with_previous_insertion(self, panel):
        """Test that dialog is shown when previous insertion exists."""
        # Set previous insertion
        panel._has_previous_insertion = True
        
        # Mock QMessageBox to return Cancel
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Cancel) as mock_question:
            panel._on_placement_mode_changed("Custom")
            
            # Dialog should be shown
            mock_question.assert_called_once()
            assert "Previous Custom Molecules Found" in mock_question.call_args[0][1]
    
    def test_start_fresh_clears_results(self, panel):
        """Test that choosing 'Yes' clears previous results."""
        # Set previous insertion
        panel._has_previous_insertion = True
        panel.positions_added = [((1.0, 2.0, 3.0), (0.0, 0.0, 0.0))]
        
        # Mock signal emission
        clear_signal_mock = Mock()
        panel.clear_previous_results.connect(clear_signal_mock)
        
        # Mock QMessageBox to return Yes (start fresh)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            panel._on_placement_mode_changed("Custom")
            
            # Signal should be emitted
            clear_signal_mock.assert_called_once()
            
            # State should be cleared
            assert panel._has_previous_insertion == False
            assert len(panel.positions_added) == 0
            assert panel.placement_mode == "Custom"
    
    def test_add_to_existing_keeps_results(self, panel):
        """Test that choosing 'No' keeps previous results."""
        # Set previous insertion
        panel._has_previous_insertion = True
        panel.positions_added = [((1.0, 2.0, 3.0), (0.0, 0.0, 0.0))]
        
        # Mock signal emission
        clear_signal_mock = Mock()
        panel.clear_previous_results.connect(clear_signal_mock)
        
        # Mock QMessageBox to return No (add to existing)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.No):
            panel._on_placement_mode_changed("Custom")
            
            # Signal should NOT be emitted
            clear_signal_mock.assert_not_called()
            
            # State should NOT be cleared
            assert panel._has_previous_insertion == True
            assert len(panel.positions_added) == 1
            assert panel.placement_mode == "Custom"
    
    def test_cancel_reverts_mode(self, panel):
        """Test that canceling the dialog reverts to previous mode."""
        # Start in Random mode
        panel.placement_mode = "Random"
        panel.placement_mode_combo.setCurrentText("Random")
        panel._has_previous_insertion = True
        
        # Mock QMessageBox to return Cancel
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Cancel):
            panel._on_placement_mode_changed("Custom")
            
            # Mode should remain Random
            assert panel.placement_mode_combo.currentText() == "Random"
    
    def test_mark_insertion_complete(self, panel):
        """Test that mark_insertion_complete sets flag."""
        assert panel._has_previous_insertion == False
        
        panel.mark_insertion_complete()
        
        assert panel._has_previous_insertion == True
    
    def test_reset_clears_insertion_flag(self, panel):
        """Test that reset clears the insertion flag."""
        panel._has_previous_insertion = True
        
        panel.reset()
        
        assert panel._has_previous_insertion == False


class TestMainWindowIntegration:
    """Test MainWindow handling of clear signal."""
    
    def test_clear_results_handler(self, app):
        """Test that MainWindow handler clears results properly."""
        from quickice.gui.main_window import MainWindow
        
        # Create main window
        window = MainWindow()
        
        # Set up mock data
        window._current_custom_molecule_result = Mock()
        window.export_custom_action.setEnabled(True)
        
        # Call handler
        window._on_clear_custom_molecule_results()
        
        # Verify results cleared
        assert window._current_custom_molecule_result is None
        assert window.export_custom_action.isEnabled() == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
