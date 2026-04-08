# Phase 17: Configuration Controls - Research

**Researched:** 2026-04-08
**Domain:** PySide6 GUI Controls / Dynamic Form Layouts / Input Validation
**Confidence:** HIGH

## Summary

This phase implements configuration controls for ice-water interface generation on Tab 2. The research examined PySide6 widget options for mode selection, dynamic form layouts for mode-dependent inputs, validation patterns, and reasonable default values. The existing codebase patterns (InputPanel, HelpIcon, validators returning `Tuple[bool, str]`) provide clear implementation guidance.

**Primary recommendation:** Use QComboBox for mode selection + QStackedWidget for mode-specific parameter groups. Follow existing InputPanel patterns for validation and error display.

## Standard Stack

### Core Widgets
| Widget | Version | Purpose | Why Standard |
|--------|---------|---------|--------------|
| QComboBox | PySide6 6.10.2 | Mode selector (slab/pocket/piece) | Compact, standard dropdown pattern |
| QStackedWidget | PySide6 6.10.2 | Switch mode-specific controls | Clean visibility management, no show/hide logic |
| QDoubleSpinBox | PySide6 6.10.2 | Box dimensions (nm) | Built-in validation, units display, step buttons |
| QSpinBox | PySide6 6.10.2 | Random seed (integer) | Enforces integer input, built-in range |
| QGroupBox | PySide6 6.10.2 | Group mode-specific parameters | Visual separation, collapsible optional |
| QFormLayout | PySide6 6.10.2 | Label-input row layout | Standard form pattern, alignment handled |

### Supporting Components (Existing)
| Component | Location | Purpose | Reuse |
|-----------|----------|---------|-------|
| HelpIcon | `quickice/gui/view.py` | Tooltip "?" icon for parameter help | Copy pattern exactly |
| Validators | `quickice/gui/validators.py` | Return `Tuple[bool, str]` pattern | Extend with new validators |
| ProgressPanel | `quickice/gui/view.py` | Generation progress feedback | Reuse as-is |
| InfoPanel | `quickice/gui/view.py` | Collapsible log output | Reuse as-is |

## Architecture Patterns

### Recommended Project Structure
```
quickice/gui/
├── view.py              # Contains HelpIcon (existing)
├── interface_panel.py   # Extended in this phase
└── validators.py        # Extended with new validators
```

### Pattern 1: Mode Selector with Stacked Controls
**What:** QComboBox for mode selection, QStackedWidget for mode-specific parameters
**When to use:** When different modes require different input sets
**Example:**
```python
# Source: PySide6 docs + existing InputPanel pattern
from PySide6.QtWidgets import QComboBox, QStackedWidget, QWidget, QVBoxLayout

class InterfacePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Mode selector
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Slab", "Pocket", "Piece"])
        
        # Stacked widget for mode-specific controls
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self._create_slab_controls())
        self.stacked_widget.addWidget(self._create_pocket_controls())
        self.stacked_widget.addWidget(self._create_piece_controls())
        
        # Connect mode change to stack index
        self.mode_combo.currentIndexChanged.connect(
            self.stacked_widget.setCurrentIndex
        )
```

### Pattern 2: Form Layout with HelpIcon
**What:** QFormLayout rows with HelpIcon next to labels
**When to use:** Consistent label-above-input pattern from Tab 1
**Example:**
```python
# Source: view.py InputPanel pattern (lines 68-78)
def _create_dimension_row(self, label_text: str, tooltip: str, default: float) -> tuple:
    """Create a form row with label, HelpIcon, and DoubleSpinBox."""
    from quickice.gui.view import HelpIcon
    
    # Label row with HelpIcon
    label_row = QHBoxLayout()
    label_row.addWidget(QLabel(label_text))
    label_row.addWidget(HelpIcon(tooltip))
    label_row.addStretch()
    
    # Spin box with units suffix
    spin_box = QDoubleSpinBox()
    spin_box.setSuffix(" nm")
    spin_box.setRange(0.1, 100.0)
    spin_box.setValue(default)
    spin_box.setDecimals(2)
    spin_box.setSingleStep(0.5)
    
    # Error label (hidden by default)
    error_label = QLabel()
    error_label.setStyleSheet("color: red;")
    error_label.hide()
    
    return label_row, spin_box, error_label
```

### Pattern 3: Validation on Submit (Not Real-time)
**What:** Validate all inputs when Generate button clicked, show inline errors
**When to use:** Consistent with Tab 1 InputPanel.validate_all() pattern
**Example:**
```python
# Source: view.py lines 122-154
def validate_all(self) -> bool:
    """Validate all inputs, show inline errors, return overall validity."""
    valid = True
    
    # Box dimensions
    for dim_input, error_label in self._dimension_inputs:
        valid_dim, dim_err = validate_box_dimension(dim_input.text())
        error_label.setText(dim_err)
        error_label.setVisible(not valid_dim)
        if not valid_dim:
            valid = False
    
    # Mode-specific validation
    current_mode = self.mode_combo.currentText()
    if current_mode == "Slab":
        valid_slab, slab_err = self._validate_slab_params()
        # ... handle errors
    # ... other modes
    
    return valid
```

### Anti-Patterns to Avoid
- **Real-time validation on every keystroke:** Conflicts with existing pattern, causes flickering error messages
- **Creating separate validator instances in UI:** Use module-level functions like `validators.py` pattern
- **Show/hide with setVisible for mode switching:** Use QStackedWidget for cleaner management
- **Custom spin box widgets:** QDoubleSpinBox with suffix is sufficient for unit display

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mode switching UI | Custom show/hide logic | QStackedWidget | Built-in index management, clean transitions |
| Unit display | Custom QLabel suffix | QDoubleSpinBox.setSuffix() | Integrated, properly aligned |
| Input validation | Per-field validators | Module validators.py functions | Consistent pattern, testable |
| Tooltips | Custom tooltip widgets | HelpIcon (existing) | Already implemented, matches style |
| Range limits | Manual range checking | QDoubleSpinBox.setRange() | Built-in clamping, user sees limits |

## Common Pitfalls

### Pitfall 1: Inconsistent Validation Pattern
**What goes wrong:** New validation approach differs from Tab 1, confusing users about when errors appear
**Why it happens:** Developer forgets to reference existing InputPanel pattern
**How to avoid:** Copy validate_all() structure from view.py lines 122-154 exactly
**Warning signs:** Errors appear on focus loss instead of Generate button click

### Pitfall 2: Missing Mode-Specific Validation
**What goes wrong:** Slab mode accepts negative thickness, pocket mode accepts invalid diameter
**Why it happens:** Only validating shared parameters, forgetting mode-specific ones
**How to avoid:** Create mode-specific validation methods called from validate_all()
**Warning signs:** Structure generation fails with cryptic errors after "valid" input

### Pitfall 3: Layout Breaking on Mode Switch
**What goes wrong:** Controls jump around when switching modes, window resizes unexpectedly
**Why it happens:** Different sized widgets in same layout positions
**How to avoid:** QStackedWidget keeps each mode's layout independent; set consistent minimum widths
**Warning signs:** Window grows/shrinks when clicking mode dropdown

### Pitfall 4: Seed Not Propagated to Generation
**What goes wrong:** Random seed input ignored, non-reproducible structures
**Why it happens:** Forgetting to pass seed value through signal chain
**How to avoid:** Include seed in generate_requested signal payload
**Warning signs:** Same parameters produce different structures each run

## Default Values and Ranges

### Box Dimensions (All Modes)
| Parameter | Default | Range | Units | Rationale |
|-----------|---------|-------|-------|-----------|
| X dimension | 5.0 | 0.5 - 50.0 | nm | Common rectangular slab |
| Y dimension | 5.0 | 0.5 - 50.0 | nm | Common rectangular slab |
| Z dimension | 10.0 | 0.5 - 100.0 | nm | Long axis for slab interfaces |

### Slab Mode
| Parameter | Default | Range | Units | Rationale |
|-----------|---------|-------|-------|-----------|
| Ice thickness | 3.0 | 0.5 - 20.0 | nm | ~10 molecular layers |
| Water thickness | 3.0 | 0.5 - 20.0 | nm | ~10 molecular layers |

### Pocket Mode
| Parameter | Default | Range | Units | Rationale |
|-----------|---------|-------|-------|-----------|
| Pocket diameter | 2.0 | 0.5 - 10.0 | nm | Reasonable cavity size |
| Pocket shape | "sphere" | sphere/ellipse | - | Default to simpler geometry |

### Piece Mode
| Parameter | Default | Range | Units | Rationale |
|-----------|---------|-------|-------|-----------|
| Piece dimensions | (uses candidate) | - | nm | Derived from selected candidate |

### Random Seed
| Parameter | Default | Range | Units | Rationale |
|-----------|---------|-------|-------|-----------|
| Seed | 42 | 1 - 999999 | integer | Classic default, always positive |

## Code Examples

### New Validators for Interface Parameters
```python
# Source: Pattern from validators.py
# Add to quickice/gui/validators.py

def validate_box_dimension(value: str) -> Tuple[bool, str]:
    """Validate box dimension input for GUI.
    
    Args:
        value: String input from GUI text field
        
    Returns:
        Tuple of (is_valid, error_message). error_message is empty on success.
    """
    try:
        dim = float(value)
    except ValueError:
        return (False, "Box dimension must be a number")
    
    if dim < 0.5 or dim > 100.0:
        return (False, "Box dimension must be between 0.5 and 100 nm")
    
    return (True, "")


def validate_thickness(value: str) -> Tuple[bool, str]:
    """Validate layer thickness input (slab mode)."""
    try:
        thickness = float(value)
    except ValueError:
        return (False, "Thickness must be a number")
    
    if thickness < 0.5 or thickness > 50.0:
        return (False, "Thickness must be between 0.5 and 50 nm")
    
    return (True, "")


def validate_pocket_diameter(value: str) -> Tuple[bool, str]:
    """Validate pocket diameter input (pocket mode)."""
    try:
        diameter = float(value)
    except ValueError:
        return (False, "Diameter must be a number")
    
    if diameter < 0.5 or diameter > 50.0:
        return (False, "Diameter must be between 0.5 and 50 nm")
    
    return (True, "")


def validate_seed(value: str) -> Tuple[bool, str]:
    """Validate random seed input."""
    try:
        float_val = float(value)
    except ValueError:
        return (False, "Seed must be an integer")
    
    if float_val != int(float_val):
        return (False, "Seed must be an integer")
    
    seed = int(float_val)
    
    if seed < 1 or seed > 999999:
        return (False, "Seed must be between 1 and 999999")
    
    return (True, "")
```

### Mode-Specific Control Panels
```python
# Source: QGroupBox + QFormLayout pattern
def _create_slab_controls(self) -> QWidget:
    """Create slab mode parameter group."""
    from PySide6.QtWidgets import QGroupBox, QFormLayout, QDoubleSpinBox
    from quickice.gui.view import HelpIcon
    
    group = QGroupBox("Slab Parameters")
    layout = QFormLayout(group)
    
    # Ice thickness
    ice_row = QHBoxLayout()
    ice_row.addWidget(QLabel("Ice thickness:"))
    ice_row.addWidget(HelpIcon("Thickness of ice layer in nanometers"))
    ice_row.addStretch()
    
    self.ice_thickness_input = QDoubleSpinBox()
    self.ice_thickness_input.setSuffix(" nm")
    self.ice_thickness_input.setRange(0.5, 50.0)
    self.ice_thickness_input.setValue(3.0)
    self.ice_thickness_input.setDecimals(2)
    
    self.ice_thickness_error = QLabel()
    self.ice_thickness_error.setStyleSheet("color: red;")
    self.ice_thickness_error.hide()
    
    layout.addRow(ice_row)
    layout.addWidget(self.ice_thickness_input)
    layout.addWidget(self.ice_thickness_error)
    
    # Water thickness (similar pattern)
    # ...
    
    return group
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| QLineEdit for all numeric inputs | QDoubleSpinBox/QSpinBox for numeric | Qt standard | Built-in validation, step buttons, range enforcement |
| Real-time validation | Validate on submit | Phase 08 | Consistent with Tab 1, less visual noise |
| QWidget.show/hide for modes | QStackedWidget | This phase | Cleaner transitions, no layout recalculation |

**Deprecated/outdated:**
- Custom numeric input widgets: QDoubleSpinBox with suffix handles unit display
- QRadioButton groups for 3 modes: QComboBox is more compact for this use case

## Open Questions

Things that couldn't be fully resolved:

1. **Box auto-calculation from layer thicknesses**
   - What we know: Slab mode could auto-calculate Z from ice+water thickness
   - What's unclear: Should user override or is it read-only?
   - Recommendation: Start with manual all-3 dimensions; add auto-calc checkbox if requested

2. **Piece mode dimension derivation**
   - What we know: Uses selected candidate size as reference
   - What's unclear: Allow scaling or fixed to candidate size?
   - Recommendation: Show candidate-derived defaults as read-only display; allow simple scale factor input

3. **Mode switching persistence**
   - What we know: QStackedWidget preserves widget state
   - What's unclear: Should previously entered values persist across mode switches?
   - Recommendation: Yes, preserve values — QStackedWidget handles this naturally

## Sources

### Primary (HIGH confidence)
- `quickice/gui/view.py` — InputPanel pattern (lines 37-206), HelpIcon (lines 638-681)
- `quickice/gui/validators.py` — Validator pattern returning `Tuple[bool, str]`
- `quickice/gui/interface_panel.py` — Current InterfacePanel structure (lines 1-261)
- PySide6 documentation — QComboBox, QStackedWidget, QDoubleSpinBox, QFormLayout

### Secondary (MEDIUM confidence)
- `.planning/research/SUMMARY-INTERFACE.md` — Interface generation parameters and defaults
- `.planning/research/PITFALLS-INTERFACE.md` — Validation requirements

### Tertiary (LOW confidence)
- Training knowledge of PySide6 widget behavior

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — PySide6 standard widgets, existing codebase patterns verified
- Architecture: HIGH — Follows existing InputPanel pattern exactly
- Pitfalls: HIGH — Based on direct codebase analysis and Qt documentation
- Default values: MEDIUM — Based on interface research; may need adjustment based on user feedback

**Research date:** 2026-04-08
**Valid until:** 30 days (stable GUI framework, unlikely to change)
