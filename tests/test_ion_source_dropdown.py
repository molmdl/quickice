"""Integration tests for ion source dropdown functionality.

Tests the complete source dropdown workflow:
1. Source dropdown rendering with three options (Interface, Custom Molecule, Solute)
2. Source switching behavior and state management
3. Charge warning display for non-neutral configurations
4. Empty state handling when source has no data

Follows testing pattern from tests/test_custom_molecule.py.
"""

import pytest
from PySide6.QtWidgets import QApplication
import sys

from quickice.gui.ion_panel import IonPanel


class TestIonSourceDropdown:
    """Tests for ion source dropdown UI and behavior."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment with QApplication and IonPanel instance."""
        # QApplication is required for Qt widgets
        # Create QApplication if it doesn't exist (singleton pattern)
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()
        
        # Create IonPanel instance for testing
        self.panel = IonPanel()
    
    def test_source_dropdown_renders(self):
        """Test that source dropdown exists and has correct initial state."""
        # Assert source_combo attribute exists
        assert hasattr(self.panel, 'source_combo'), \
            "IonPanel should have source_combo attribute"
        
        # Assert source_combo has 3 items
        assert self.panel.source_combo.count() == 3, \
            f"Source combo should have 3 items, got {self.panel.source_combo.count()}"
        
        # Assert item labels are correct
        assert self.panel.source_combo.itemText(0) == "Interface", \
            f"Item 0 should be 'Interface', got '{self.panel.source_combo.itemText(0)}'"
        assert self.panel.source_combo.itemText(1) == "Custom Molecule", \
            f"Item 1 should be 'Custom Molecule', got '{self.panel.source_combo.itemText(1)}'"
        assert self.panel.source_combo.itemText(2) == "Solute", \
            f"Item 2 should be 'Solute', got '{self.panel.source_combo.itemText(2)}'"
    
    def test_charge_warning_label_exists(self):
        """Test that charge warning label exists and is initially hidden."""
        # Assert charge_warning_label attribute exists
        assert hasattr(self.panel, 'charge_warning_label'), \
            "IonPanel should have charge_warning_label attribute"
        
        # Assert label is initially hidden
        assert not self.panel.charge_warning_label.isVisible(), \
            "Charge warning label should be initially hidden"
    
    def test_default_source_is_interface(self):
        """Test that default source selection is Interface (index 0)."""
        # Assert source_combo.currentIndex() == 0
        assert self.panel.source_combo.currentIndex() == 0, \
            f"Default source index should be 0 (Interface), got {self.panel.source_combo.currentIndex()}"
        
        # Assert _current_source == "Interface"
        assert self.panel._current_source == "Interface", \
            f"Default _current_source should be 'Interface', got '{self.panel._current_source}'"
    
    def test_switch_to_custom_molecule(self):
        """Test switching source to Custom Molecule."""
        # Set source_combo.setCurrentIndex(1)
        self.panel.source_combo.setCurrentIndex(1)
        
        # Assert _current_source == "Custom Molecule"
        assert self.panel._current_source == "Custom Molecule", \
            f"Source should be 'Custom Molecule', got '{self.panel._current_source}'"
        
        # Note: configuration_changed signal is emitted but we don't test it directly
        # The signal emission is tested implicitly by checking state changes
    
    def test_switch_to_solute(self):
        """Test switching source to Solute."""
        # Set source_combo.setCurrentIndex(2)
        self.panel.source_combo.setCurrentIndex(2)
        
        # Assert _current_source == "Solute"
        assert self.panel._current_source == "Solute", \
            f"Source should be 'Solute', got '{self.panel._current_source}'"
    
    def test_switch_back_to_interface(self):
        """Test switching back to Interface after changing sources."""
        # Switch to Custom Molecule first
        self.panel.source_combo.setCurrentIndex(1)
        assert self.panel._current_source == "Custom Molecule"
        
        # Switch back to Interface
        self.panel.source_combo.setCurrentIndex(0)
        
        # Assert _current_source == "Interface"
        assert self.panel._current_source == "Interface", \
            f"Source should be 'Interface', got '{self.panel._current_source}'"
    
    def test_source_switch_preserves_concentration(self):
        """Test that concentration is preserved when switching sources."""
        # Set concentration to 1.5 M
        self.panel.concentration_input.setValue(1.5)
        initial_conc = self.panel.concentration_input.value()
        
        # Switch source to Custom Molecule
        self.panel.source_combo.setCurrentIndex(1)
        
        # Assert concentration remains 1.5 M
        assert self.panel.concentration_input.value() == initial_conc, \
            f"Concentration should be preserved at {initial_conc}, got {self.panel.concentration_input.value()}"
        
        # Switch to Solute
        self.panel.source_combo.setCurrentIndex(2)
        
        # Assert concentration still preserved
        assert self.panel.concentration_input.value() == initial_conc, \
            f"Concentration should still be preserved at {initial_conc}, got {self.panel.concentration_input.value()}"
    
    def test_charge_warning_hidden_for_interface_source(self):
        """Test that charge warning is hidden for Interface source."""
        # Set source to Interface (index 0)
        self.panel.source_combo.setCurrentIndex(0)
        
        # Set liquid volume to 10.0 (needed for ion calculation)
        self.panel.set_liquid_volume(10.0)
        
        # Assert charge_warning_label.isVisible() == False
        assert not self.panel.charge_warning_label.isVisible(), \
            "Charge warning should be hidden for Interface source"
    
    def test_charge_warning_hidden_for_neutral_config(self):
        """Test that charge warning is hidden for neutral ion configuration.
        
        Ion configuration (Na+/Cl- pairs) is always neutral with Madrid2019 charges,
        so warning should never show for ion config alone (without custom molecule).
        """
        # Set source to Custom Molecule
        self.panel.source_combo.setCurrentIndex(1)
        
        # Set liquid volume and concentration
        self.panel.set_liquid_volume(10.0)
        self.panel.concentration_input.setValue(0.5)
        
        # Get total charge - should be 0 for neutral Na+/Cl- configuration
        total_charge = self.panel.get_total_charge()
        
        # Ion configuration is always neutral (equal Na+ and Cl- with charges ±0.85)
        assert total_charge == 0.0, \
            f"Total charge for neutral ion config should be 0.0, got {total_charge}"
        
        # Warning should be hidden for neutral charge
        assert not self.panel.charge_warning_label.isVisible(), \
            "Charge warning should be hidden for neutral ion configuration"
    
    def test_insert_button_disabled_when_interface_unavailable(self):
        """Test that Insert button is disabled when Interface source has no structure."""
        # Set source to Interface (default)
        self.panel.source_combo.setCurrentIndex(0)
        
        # Call set_interface_available(False)
        self.panel.set_interface_available(False)
        
        # Assert insert_button.isEnabled() == False
        assert not self.panel.insert_button.isEnabled(), \
            "Insert button should be disabled when Interface has no structure"
        
        # Assert tooltip explains why
        tooltip = self.panel.insert_button.toolTip()
        assert "Generate Interface structure first" in tooltip, \
            f"Tooltip should explain why disabled, got: {tooltip}"
    
    def test_insert_button_enabled_when_interface_available(self):
        """Test that Insert button is enabled when Interface source has structure."""
        # Set source to Interface (default)
        self.panel.source_combo.setCurrentIndex(0)
        
        # Call set_interface_available(True)
        self.panel.set_interface_available(True)
        
        # Assert insert_button.isEnabled() == True
        assert self.panel.insert_button.isEnabled(), \
            "Insert button should be enabled when Interface has structure"
        
        # Assert tooltip shows normal message
        tooltip = self.panel.insert_button.toolTip()
        assert "Insert Na+ and Cl- ions" in tooltip, \
            f"Tooltip should show normal message, got: {tooltip}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
