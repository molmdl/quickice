# Quick Task 017: Custom Molecule Concentration Input

**Created:** 2026-05-10
**Status:** pending
**Priority:** high
**Estimated effort:** 6-9 hours, ~460 lines

---

## Objective

Add concentration input functionality to Custom Molecule random mode, enabling users to either:
1. Input molecule count → see calculated concentration (based on liquid volume)
2. Input concentration → see calculated molecule count (based on liquid volume)

This follows the existing `SolutePanel` pattern and brings parity between solute insertion and custom molecule insertion workflows.

---

## Background

**Current state:** CustomMoleculePanel random mode only provides molecule count input. No concentration option exists.

**Reference implementation:** `SolutePanel._create_concentration_group()` (lines 159-203) provides concentration input UI. `SoluteInserter.calculate_molecule_count()` (lines 62-89) provides calculation logic.

**User request:** "custom mol random mode should allow user to input conc or calculate concentration from liquid volume and mol count"

---

## Implementation Plan

### Phase 1: Add Calculation Logic (1-2 hours)

**File:** `quickice/structure_generation/custom_molecule_inserter.py`

Add two calculation methods:

```python
from quickice.structure_generation.constants import AVOGADRO

def calculate_molecule_count(
    concentration_molar: float,
    liquid_volume_nm3: float
) -> int:
    """Calculate molecule count from concentration.
    
    Formula: N = C_M × V_L × N_A
    
    Where:
    - C_M = concentration (mol/L)
    - V_L = liquid volume (nm³) × 1e-24 = volume (L)
    - N_A = Avogadro's number (6.022×10²³)
    
    Reuse from SoluteInserter (solute_inserter.py:62-89).
    """
    volume_liters = liquid_volume_nm3 * 1e-24
    n_molecules = concentration_molar * volume_liters * AVOGADRO
    return int(round(n_molecules))

def calculate_concentration(
    molecule_count: int,
    liquid_volume_nm3: float
) -> float:
    """Calculate concentration from molecule count (REVERSE).
    
    Formula: C_M = N / (V_L × N_A)
    
    Args:
        molecule_count: Number of molecules
        liquid_volume_nm3: Liquid volume in nm³
        
    Returns:
        Concentration in mol/L (M)
    """
    if liquid_volume_nm3 <= 0 or molecule_count <= 0:
        return 0.0
    
    volume_liters = liquid_volume_nm3 * 1e-24
    concentration = molecule_count / (volume_liters * AVOGADRO)
    return concentration
```

### Phase 2: Add UI Components (3-4 hours)

**File:** `quickice/gui/custom_molecule_panel.py`

Add to `_create_random_controls()`:

1. **Input mode selector:**
   - QComboBox with "By Count" and "By Concentration" options
   - Default to "By Count" for backward compatibility

2. **By Count mode (existing + new):**
   - Keep existing `molecule_count_spin`
   - Add calculated concentration label below

3. **By Concentration mode (new):**
   - Add `concentration_spin` (QDoubleSpinBox, range 0.0-2.0 M)
   - Add calculated molecule count label below

4. **Signal connections:**
   - `input_mode_combo.currentIndexChanged` → `_on_input_mode_changed`
   - `molecule_count_spin.valueChanged` → `_update_concentration_from_count`
   - `concentration_spin.valueChanged` → `_update_count_from_concentration`

5. **Preview updates:**
   - When in "By Count" mode, update concentration label in real-time
   - When in "By Concentration" mode, update count label in real-time

### Phase 3: Add Panel Methods (1-2 hours)

**File:** `quickice/gui/custom_molecule_panel.py`

```python
def _on_input_mode_changed(self, index: int):
    """Switch between 'By Count' and 'By Concentration' modes."""
    self.count_mode_widget.setVisible(index == 0)
    self.concentration_mode_widget.setVisible(index == 1)
    self._update_preview()

def _update_concentration_from_count(self):
    """Calculate concentration from molecule count."""
    if self._interface_structure is None:
        self.calculated_concentration_label.setText("-- mol/L")
        return
    
    # Get liquid volume (reuse existing calculation)
    water_count = getattr(self._interface_structure, 'water_atom_count', 0)
    water_nmolecules = water_count // 4 if water_count > 0 else 0
    liquid_volume_nm3 = water_nmolecules * 0.0299
    
    # Calculate concentration
    molecule_count = int(self.molecule_count_spin.value())
    concentration = calculate_concentration(molecule_count, liquid_volume_nm3)
    
    self.calculated_concentration_label.setText(f"{concentration:.4f} mol/L")

def _update_count_from_concentration(self):
    """Calculate molecule count from concentration."""
    if self._interface_structure is None:
        self.calculated_count_label.setText("-- molecules")
        return
    
    # Get liquid volume
    water_count = getattr(self._interface_structure, 'water_atom_count', 0)
    water_nmolecules = water_count // 4 if water_count > 0 else 0
    liquid_volume_nm3 = water_nmolecules * 0.0299
    
    # Calculate molecule count
    concentration = self.concentration_spin.value()
    molecule_count = calculate_molecule_count(concentration, liquid_volume_nm3)
    
    self.calculated_count_label.setText(f"{molecule_count} molecules")
    self.molecule_estimate_label.setText(f"{molecule_count} molecules")
```

### Phase 4: Update Generate Logic (30 min)

**File:** `quickice/gui/custom_molecule_panel.py`

Update `get_config()` to handle both modes:
- If mode is "By Concentration", calculate molecule count and use that
- If mode is "By Count", use existing logic

---

## Testing Requirements

### Unit Tests

**File:** `tests/test_custom_molecule_concentration.py`

1. Test `calculate_molecule_count()` with known volumes and concentrations
2. Test `calculate_concentration()` reverse calculation
3. Test round-trip: count → concentration → count (should match)
4. Test edge cases: zero volume, zero count, very high concentration

### Integration Tests

1. Test UI switching between "By Count" and "By Concentration" modes
2. Test real-time preview updates
3. Test with various interface structures (different liquid volumes)
4. Test that generated structure has correct molecule count in both modes

### Manual Testing

1. Launch GUI: `python quickice/gui/main_window.py`
2. Create an interface structure
3. Upload custom molecule files
4. Switch to Random mode
5. Test "By Count" → input count, verify concentration shows
6. Test "By Concentration" → input conc, verify count shows
7. Generate and verify correct molecule count

---

## Files to Modify

| File | Changes | Lines |
|------|---------|-------|
| `quickice/structure_generation/custom_molecule_inserter.py` | Add calculation methods | +30 |
| `quickice/gui/custom_molecule_panel.py` | Add concentration UI and mode switching | +150 |
| `tests/test_custom_molecule_concentration.py` | New test file | +80 |

**Total:** ~260 lines (reduced from original estimate due to existing patterns)

---

## Success Criteria

- [ ] User can select input mode (By Count / By Concentration)
- [ ] User can input molecule count and see calculated concentration
- [ ] User can input concentration and see calculated molecule count
- [ ] Switching modes preserves values where appropriate
- [ ] Generated structure has correct number of molecules in both modes
- [ ] All unit tests pass
- [ ] Manual testing confirms UI works correctly

---

## Reference Files

- `quickice/gui/solute_panel.py` - Existing concentration UI pattern
- `quickice/structure_generation/solute_inserter.py` - Existing calculation logic
- `.planning/debug/custom-mol-concentration-input.md` - Full analysis from debugger
