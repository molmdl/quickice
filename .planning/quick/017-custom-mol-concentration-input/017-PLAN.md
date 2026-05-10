---
phase: 017-custom-mol-concentration-input
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/structure_generation/custom_molecule_inserter.py
  - quickice/gui/custom_molecule_panel.py
  - tests/test_custom_molecule_concentration.py
autonomous: true
must_haves:
  truths:
    - "User can select input mode (By Count / By Concentration)"
    - "User can input molecule count and see calculated concentration"
    - "User can input concentration and see calculated molecule count"
    - "Generated structure has correct number of molecules in both modes"
  artifacts:
    - path: quickice/structure_generation/custom_molecule_inserter.py
      provides: "Calculation methods for count ↔ concentration conversion"
      exports: ["calculate_molecule_count", "calculate_concentration"]
    - path: quickice/gui/custom_molecule_panel.py
      provides: "UI for concentration input with mode switching"
      contains: "input_mode_combo"
    - path: tests/test_custom_molecule_concentration.py
      provides: "Validation of calculation logic"
  key_links:
    - from: quickice/gui/custom_molecule_panel.py
      to: quickice/structure_generation/custom_molecule_inserter.py
      via: "import calculate_molecule_count, calculate_concentration"
      pattern: "from.*custom_molecule_inserter import"
    - from: valueChanged signals
      to: preview labels
      via: "_update_concentration_from_count, _update_count_from_concentration"
      pattern: "valueChanged.connect"
---

<objective>
Add concentration input functionality to Custom Molecule random mode, enabling users to input either molecule count (with calculated concentration) or concentration (with calculated molecule count), matching the SolutePanel pattern.

Purpose: Bring parity between solute insertion and custom molecule insertion workflows, allowing scientists to specify custom molecule amounts by concentration (common in solution chemistry) rather than only by molecule count.

Output: Working concentration/count input toggle in Custom Molecule Panel with real-time preview updates.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/quick/017-custom-mol-concentration-input/task.md

# Reference implementations
@quickice/gui/solute_panel.py
@quickice/structure_generation/solute_inserter.py
@quickice/gui/custom_molecule_panel.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add concentration calculation methods</name>
  <files>quickice/structure_generation/custom_molecule_inserter.py</files>
  <action>
Add two calculation methods to CustomMoleculeInserter class (after __init__ method, around line 89):

1. **calculate_molecule_count(concentration_molar: float, liquid_volume_nm3: float) -> int**
   - Copy logic from SoluteInserter.calculate_molecule_count() (solute_inserter.py:62-89)
   - Formula: N = C_M × V_L × N_A where V_L = volume_nm³ × 1e-24
   - Uses AVOGADRO constant (6.02214076e23)
   - Returns int(round(n_molecules))

2. **calculate_concentration(molecule_count: int, liquid_volume_nm3: float) -> float**
   - REVERSE calculation: C_M = N / (V_L × N_A)
   - Handle edge cases: if volume ≤ 0 or count ≤ 0, return 0.0
   - Returns concentration in mol/L

Both methods should be static methods (no self parameter needed) for easy reuse.

Import AVOGADRO from quickice.structure_generation.solute_inserter (line 32) or define locally if not accessible.
  </action>
  <verify>python -c "from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter; print(CustomMoleculeInserter.calculate_molecule_count(0.1, 100)); print(CustomMoleculeInserter.calculate_concentration(60, 100))"</verify>
  <done>Both calculation methods exist and return correct values. Test with: 0.1 M in 100 nm³ → ~6 molecules. Reverse: 60 molecules in 100 nm³ → ~0.1 M</done>
</task>

<task type="auto">
  <name>Task 2: Add concentration input UI components</name>
  <files>quickice/gui/custom_molecule_panel.py</files>
  <action>
Modify _create_random_controls() method (starting line 320) to add concentration input mode:

1. **Input mode selector** (add after "Molecule Count:" label row):
   - Create QHBoxLayout: mode_row
   - Add QLabel: "Input Mode:"
   - Create QComboBox: self.input_mode_combo
   - Add items: ["By Count", "By Concentration"]
   - Default to "By Count" (index 0) for backward compatibility
   - Add HelpIcon with tooltip explaining both modes
   - Add stretch to push left

2. **Reorganize count input** (modify existing count_row):
   - Keep self.molecule_count_spin
   - Add calculated concentration label below:
     - Create QLabel: self.calculated_concentration_label
     - Initial text: "-- mol/L"
     - Style: "color: gray; font-style: italic;"
   - Wrap in widget: self.count_mode_widget for visibility toggling

3. **Add concentration input section** (new, hidden initially):
   - Create QWidget: self.concentration_mode_widget
   - Set visible(False) initially
   - Concentration spin box:
     - Create QDoubleSpinBox: self.concentration_spin
     - Range: 0.0-2.0 M (match SolutePanel range)
     - Decimals: 3, SingleStep: 0.01
     - Default: 0.1 M
     - Add unit label: "mol/L"
   - Calculated count label:
     - Create QLabel: self.calculated_count_label
     - Initial text: "-- molecules"
     - Style: "color: gray; font-style: italic;"

4. **Add to layout**:
   - Add input_mode_combo row to layout
   - Add count_mode_widget to layout
   - Add concentration_mode_widget to layout
   - Keep existing volume display and estimate rows at bottom

5. **Signal connections** (add to _setup_connections method around line 490):
   - self.input_mode_combo.currentIndexChanged.connect(self._on_input_mode_changed)
   - self.molecule_count_spin.valueChanged.connect(self._update_concentration_from_count)
   - self.concentration_spin.valueChanged.connect(self._update_count_from_concentration)
  </action>
  <verify>python -c "from quickice.gui.custom_molecule_panel import CustomMoleculePanel; from PySide6.QtWidgets import QApplication; import sys; app = QApplication(sys.argv); panel = CustomMoleculePanel(); print('Input mode combo:', panel.input_mode_combo.count()); print('Concentration spin:', panel.concentration_spin.range())"</verify>
  <done>UI components exist with proper layout. Input mode dropdown has 2 options. Concentration spin box has range 0.0-2.0. Both count and concentration sections have calculated value labels.</done>
</task>

<task type="auto">
  <name>Task 3: Wire up preview updates and generate logic</name>
  <files>quickice/gui/custom_molecule_panel.py</files>
  <action>
Add three new methods and update get_configuration():

1. **Add _on_input_mode_changed(self, index: int)** method:
   - Show count_mode_widget when index == 0 (By Count)
   - Show concentration_mode_widget when index == 1 (By Concentration)
   - Call _update_volume_preview() to refresh calculated values

2. **Add _update_concentration_from_count(self)** method:
   - Check if _interface_structure exists (return if None)
   - Get liquid volume (reuse logic from _update_volume_preview: water_count // 4 * 0.0299)
   - Import calculate_concentration from custom_molecule_inserter
   - Calculate concentration: concentration = CustomMoleculeInserter.calculate_concentration(molecule_count, liquid_volume_nm3)
   - Update self.calculated_concentration_label with "{concentration:.4f} mol/L"

3. **Add _update_count_from_concentration(self)** method:
   - Check if _interface_structure exists (return if None)
   - Get liquid volume
   - Import calculate_molecule_count from custom_molecule_inserter
   - Calculate count: count = CustomMoleculeInserter.calculate_molecule_count(concentration, liquid_volume_nm3)
   - Update self.calculated_count_label with "{count} molecules"
   - Also update self.molecule_estimate_label with "{count} molecules" (for consistency with existing UI)

4. **Update _update_volume_preview(self)** method:
   - After calculating volume and estimate, call either:
     - _update_concentration_from_count() if in "By Count" mode
     - _update_count_from_concentration() if in "By Concentration" mode
   - Add helper: self.input_mode_combo.currentText() == "By Count"

5. **Update get_configuration(self)** method (around line 995):
   - Check input mode: mode_text = self.input_mode_combo.currentText()
   - If "By Concentration":
     - Get concentration = self.concentration_spin.value()
     - Calculate molecule_count from concentration and liquid volume
     - Use calculated count in CustomMoleculeConfig
   - If "By Count":
     - Use existing logic (self.molecule_count_spin.value())

6. **Import statement** (add to top of file around line 20):
   - from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter
</action>
  <verify>python -c "
from quickice.gui.custom_molecule_panel import CustomMoleculePanel
from PySide6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
panel = CustomMoleculePanel()

# Check methods exist
assert hasattr(panel, '_on_input_mode_changed')
assert hasattr(panel, '_update_concentration_from_count')
assert hasattr(panel, '_update_count_from_concentration')

# Test mode switching
panel._on_input_mode_changed(0)
assert panel.count_mode_widget.isVisible()
assert not panel.concentration_mode_widget.isVisible()

panel._on_input_mode_changed(1)
assert not panel.count_mode_widget.isVisible()
assert panel.concentration_mode_widget.isVisible()

print('All mode switching logic verified')
"</verify>
  <done>Real-time preview updates work in both modes. Mode switching correctly shows/hides widgets. get_configuration() returns correct molecule count in both modes. All signal connections functional.</done>
</task>

</tasks>

<verification>
1. Unit tests pass: pytest tests/test_custom_molecule_concentration.py
2. Manual testing:
   - Launch GUI: python quickice/gui/main_window.py
   - Generate interface structure
   - Upload custom molecule files (use tests/data/etoh.gro and etoh.itp)
   - Switch to Random mode
   - Test "By Count": input count, verify concentration shows
   - Test "By Concentration": input concentration, verify count shows
   - Generate structure, verify correct molecule count
3. Edge cases:
   - Zero volume shows "--" for calculated values
   - High concentrations (>1 M) work correctly
   - Mode switching preserves appropriate values
</verification>

<success_criteria>
- [ ] User can select input mode (By Count / By Concentration) in Custom Molecule random mode
- [ ] User can input molecule count and see calculated concentration in real-time
- [ ] User can input concentration and see calculated molecule count in real-time
- [ ] Default mode is "By Count" for backward compatibility
- [ ] Generated structure has correct number of molecules in both input modes
- [ ] All calculation methods return mathematically correct values
- [ ] All unit tests pass
- [ ] Manual testing confirms UI works correctly
</success_criteria>

<output>
After completion, create `.planning/quick/017-custom-mol-concentration-input/017-SUMMARY.md`
</output>
