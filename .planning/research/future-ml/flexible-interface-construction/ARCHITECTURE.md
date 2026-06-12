# Architecture Patterns: Flexible Interface Construction

**Domain:** Ice-water interface construction for MD simulation
**Researched:** 2026-06-12

## Recommended Architecture

**Layer-based composition model with named mode presets** — not a general-purpose layer compositor, but a curated set of named configurations backed by a generalized layer assembly engine.

The key architectural insight is that **QuickIce's existing QStackedWidget + mode routing pattern naturally extends to support new modes**, and the slab.py hardcoded Z-stacking generalizes cleanly into a `LayerSpec`-driven loop. The UI adds new mode entries to the existing `mode_combo` QComboBox and new pages to the `stacked_widget`, while the backend adds a `layer_assembly.py` module that iterates over `list[LayerSpec]` instead of hardcoding bottom-ice / water / top-ice.

**Three new features, three new mode entries:**

1. **"Asymmetric Slab"** — New mode in `mode_combo` with single ice + water parameters
2. **"Ice + Hydrate"** — New mode in `mode_combo` with ice/hydrate source pair + water parameters
3. **Crystal face selection** — NOT a new mode, but a dropdown control added to ALL slab-derived modes

**Explicitly NOT implemented (anti-features):**
- Slab orientation flip (physically meaningless under PBC)
- Arbitrary drag-and-drop layer ordering (over-engineering)
- Mixed hydrate types sI+sII (lattice mismatch, no demand)
- General "any structure for any layer" composition (impossible overlap resolution)

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `InterfacePanel` (UI) | Collects user configuration; shows mode-specific controls | `MainWindow` via signals |
| `InterfaceConfig` (data) | Validates and stores configuration parameters | `InterfacePanel` (created from), `interface_builder.py` (consumed by) |
| `interface_builder.py` (routing) | Validates config, routes to correct mode implementation | `InterfaceConfig`, mode modules |
| `layer_assembly.py` (NEW, backend) | Generic layer-by-layer assembly from `list[LayerSpec]` | Called by `assemble_slab()`, `assemble_asymmetric_slab()`, `assemble_ice_hydrate()` |
| `slab.py` (existing, refactored) | Symmetric slab: ice-water-ice | Calls `layer_assembly.py` internally |
| `asymmetric_slab.py` (NEW) | Single ice + water interface | Calls `layer_assembly.py` |
| `ice_hydrate_slab.py` (NEW) | Ice-hydrate-water triple interface | Calls `layer_assembly.py` with two different crystal sources |
| `MainWindow` (orchestration) | Wires UI signals to ViewModel, handles multi-source generation | `InterfacePanel`, `viewmodel.py`, `hydrate_panel.py` |
| `LayerPreviewWidget` (NEW, UI) | Renders a schematic diagram of the layer stack before generation | Reads from `InterfacePanel` configuration |

### Data Flow

```
User selects mode in InterfacePanel
  → QComboBox.currentIndexChanged → stacked_widget.setCurrentIndex
  → Mode-specific panel shows relevant controls

User configures parameters + clicks "Generate Interface"
  → InterfacePanel.get_configuration() → dict
  → InterfaceConfig.from_dict(dict)
  → MainWindow reads source (ice candidate OR hydrate structure OR multi-source)
  → interface_builder.py validates config
  → Routes to mode module (slab / asymmetric_slab / ice_hydrate_slab)
  → Mode module constructs list[LayerSpec] and calls assemble_layers()
  → assemble_layers() iterates: tile_structure() or fill_region_with_water()
  → Overlap detection + removal between adjacent layers
  → Returns InterfaceStructure

For multi-source (ice+hydrate):
  → MainWindow calls GenIce2 twice (once for ice, once for hydrate)
  → Extracts absolute coordinates from each
  → Constructs list[LayerSpec] with per-layer source
  → Calls assemble_layers()
```

## Current UI Analysis

### InterfacePanel Structure

The `InterfacePanel` class (935 lines) uses a **two-column layout** with a QStackedWidget for mode-dependent controls:

**Left column** (stretch=2):
1. Title label ("Interface Construction")
2. Source selector: `source_combo` QComboBox — ["Ice Candidate", "Hydrate Structure"]
3. Mode selector: `mode_combo` QComboBox — ["Slab", "Pocket", "Piece"]
4. Box dimensions: `box_x_input`, `box_y_input`, `box_z_input` (QDoubleSpinBox, suffix " nm")
5. Random seed: `seed_input` (QSpinBox, range 1–999999)
6. Candidate selection: `candidate_dropdown` QComboBox (populated from Tab 1)
7. Refresh button
8. Generate Interface button
9. Progress panel
10. Info panel (collapsible log)

**Right column** (stretch=3):
1. `stacked_widget` QStackedWidget (mode-specific parameter panels)
   - Page 0: `_create_slab_panel()` — ice_thickness, water_thickness (QDoubleSpinBox)
   - Page 1: `_create_pocket_panel()` — pocket_diameter, pocket_shape (QComboBox)
   - Page 2: `_create_piece_panel()` — informational label only
2. `_viewer_stack` QStackedWidget
   - Page 0: Placeholder label ("Generate a structure to visualize")
   - Page 1: InterfaceViewerWidget (VTK 3D viewer) or fallback label

**Signal/slot wiring** (`_setup_connections`, lines 515–530):
- `source_combo.currentIndexChanged` → `_on_source_changed` (toggles ice/hydrate controls)
- `mode_combo.currentIndexChanged` → `stacked_widget.setCurrentIndex` (swaps mode panels)
- `candidate_dropdown.currentIndexChanged` → `_on_candidate_changed` → emits `candidate_selected(int)`
- `refresh_btn.clicked` → emits `refresh_requested()`
- `generate_btn.clicked` → `_on_generate_clicked` → routes to ice or hydrate handler

### Source Selection Mechanism

The source selector (`source_combo`) controls what generates the crystal structure:

- **Index 0: "Ice Candidate"** — Uses ice structures from Tab 1. Enables `candidate_dropdown` and `refresh_btn`. Disables seed (seed comes from candidate).
- **Index 1: "Hydrate Structure"** — Generates hydrate directly. Disables `candidate_dropdown` and `refresh_btn`. Enables `generate_btn` directly (no candidate needed).

When source is "Hydrate Structure" and user clicks Generate:
1. `generate_btn.clicked` → `_on_generate_clicked` → checks `source_combo.currentIndex()`
2. If index == 1: emits `generate_hydrate_requested()`
3. `MainWindow._on_interface_hydrate_generate` handles the signal
4. Uses `_current_hydrate_result` from Tab 2's HydratePanel
5. Converts hydrate to Candidate via `hydrate.to_candidate()`
6. Pre-populates interface panel via `set_from_hydrate()`
7. Gets config from `interface_panel.get_configuration()`
8. Starts interface generation via `_viewmodel.start_interface_generation(candidate, config)`

**Key limitation of current source mechanism:** Only ONE source at a time — either ice OR hydrate, not both. For ice+hydrate triple interface, we need a dual-source mechanism.

### Validation Architecture

Current validation is split between two locations:

1. **UI-side** (`InterfacePanel.validate_configuration()`, lines 739–811):
   - Box dimension range validation
   - Seed range validation
   - Mode-specific: slab box_z = 2×ice + water; pocket diameter < box
   - Shows inline `QLabel` error messages (red text, hidden by default)

2. **Backend-side** (`interface_builder.py validate_interface_config()`, lines 26–308):
   - Same checks plus box minimum dimension checks
   - Candidate validity checks (positions, cell shape)
   - Ice II rhombohedral rejection
   - Raises `InterfaceGenerationError` with descriptive messages

**For flexible interface:** The validation must become layer-aware. The constraint `box_z = sum(layer_thicknesses)` replaces `box_z = 2*ice_thickness + water_thickness`. This requires changes in both validation locations.

### Generalization Points

**Where to extend for flexible modes:**

1. **`mode_combo` QComboBox** — Add "Asymmetric Slab" and "Ice + Hydrate" entries. The QStackedWidget pattern already supports adding pages.

2. **`stacked_widget` QStackedWidget** — Add new pages for asymmetric slab params (ice_thickness + water_thickness, no top ice) and ice+hydrate params (ice source, hydrate source, water thickness).

3. **`source_combo` QComboBox** — The binary "Ice Candidate" / "Hydrate Structure" model breaks for ice+hydrate mode. Need either: (a) a third option "Ice + Hydrate" that shows dual source controls, or (b) embed source selection per-layer within the mode-specific panel.

4. **`InterfaceConfig` dataclass** — Add `layer_order: list[str]`, `layer_thicknesses: list[float]`, per-layer source fields. Backward-compatible defaults derive from existing fields.

5. **`interface_builder.py`** — Add routing for new modes. Validation must support variable layer counts.

6. **`slab.py`** — Refactor hardcoded bottom-ice / water / top-ice into `assemble_layers()` loop. The existing `tile_structure()` and `fill_region_with_water()` are already generic.

## Scientific GUI Patterns

### Avogadro

**Pattern:** Stepwise build workflow with tool-switching. Avogadro uses a "Build → Insert" workflow where users select molecule types from dropdown menus and use drawing tools to place them. Multi-step building (e.g., crystal + solvent) is done through separate plugin invocations, not a unified composition panel.

**Applicability to QuickIce:** LOW. Avogadro is a general molecular editor with free-form placement. QuickIce has constrained geometry (slab stacking along Z) where the order matters but the degrees of freedom are limited. Avogadro's open-ended approach is over-engineering for our use case.

**Takeaway:** Avogadro uses separate tools for separate tasks, then composes via file import. This is similar to QuickIce's current "generate ice in Tab 1, use in Tab 3" pattern. For multi-source, a similar "import from multiple tabs" approach fits naturally.

### VMD

**Pattern:** Multiple representation configuration with independent per-molecule settings. VMD's "Graphical Representations" dialog lets users add multiple representation layers, each with its own selection, drawing method, and color. Each representation is independently configurable.

**Applicability to QuickIce:** MEDIUM. VMD's per-representation configuration model maps well to "per-layer source selection." Each layer in the interface stack is like a VMD representation — it has its own type, source, and parameters. However, VMD uses a QListWidget-based representation list with add/remove buttons, which is too flexible for our needs.

**Takeaway:** The concept of independently configurable items in a list is relevant. But we should use a FIXED list (not user-editable add/remove) to prevent physically meaningless configurations.

### Packmol

**Pattern:** Text-based constraint specification with `structure ... end structure` blocks. Each block defines a molecule type, count, and spatial constraint (`inside box`, `above plane`, etc.). The `above`/`below plane` constraints are used to build layered interfaces (e.g., water below a plane, CCl4 above it).

**Applicability to QuickIce:** HIGH for the concept of region-based placement with multiple sources. Packmol's `above plane` / `below plane` constraints are exactly what QuickIce needs conceptually: each layer occupies a Z-region defined by planes. However, Packmol is text-file-driven (no official GUI), and its interface is declarative rather than interactive.

**Key Packmol pattern for QuickIce:**
```
structure water.pdb
  number 1000
  below plane 0.0 0.0 1.0 5.0
end structure
structure ice.pdb
  number 500
  above plane 0.0 0.0 1.0 5.0
end structure
```
This maps directly to our `LayerSpec` model: each layer has a source, a count (derived from density), and a Z-region.

**Takeaway:** The `structure ... end structure` block pattern is the conceptual model for `LayerSpec`. Each block has: source, spatial region, molecule count. The order of blocks doesn't matter (constraints define placement), but in QuickIce the order matters for the Z-stacking.

### LAMMPS-GUI

**Pattern:** Tabbed parameter configuration with validation. LAMMPS-GUI (if available) provides structured input forms for simulation parameters with real-time validation and script generation. Parameters are grouped by category (force field, integrator, output) and cross-validated.

**Applicability to QuickIce:** MEDIUM. The pattern of grouped parameters with cross-validation is directly relevant. QuickIce already uses this pattern (box dims + mode-specific params + validation). The extension is adding cross-layer validation (thickness sums, density compatibility).

### Layer Composition UIs

**Common patterns across tools:**

1. **GIMP/Photoshop-style layer panel:** Each layer is an item in a vertical list with thumbnail, visibility toggle, opacity. Drag-and-drop reordering. This is the most common "layer composition" UI but is **too general** for QuickIce — scientists don't need arbitrary reordering.

2. **VMD representation list:** QListWidget with add/remove buttons. Each item has independent config. Again too general.

3. **Packmol constraint blocks:** Declarative text specification with per-block spatial constraints. Good conceptual model but poor GUI pattern.

4. **CHARMM-GUI Membrane Builder:** Step-by-step wizard with dropdowns. User selects "lipid type" → "number of layers" → "solvent" in a fixed sequence. This is the **closest match** to QuickIce's needs: a curated set of named configurations with per-step source selection.

**Recommendation for QuickIce:** Use the **CHARMM-GUI Membrane Builder pattern** — named mode presets with fixed layer stacks. Each mode has a predetermined layer ordering (e.g., "ice-water" for asymmetric slab, "ice-hydrate-water" for triple interface) with per-layer source dropdowns. No drag-and-drop, no add/remove buttons.

## Proposed UI Architecture

### Design Principle: Curated Modes, Not General Composition

**Why not a general layer compositor:**
- Most layer orderings are physically meaningless (e.g., "water-ice-water" = same as current slab under PBC)
- Drag-and-drop adds UI complexity without scientific value
- Per-layer parameter explosion makes validation intractable
- QuickIce's users are MD scientists, not GUI designers — they want named configurations

**Instead:** Three new named modes in the existing mode selector, each with its own parameter panel. This follows the existing pattern (Slab, Pocket, Piece) and keeps the UI simple.

### Asymmetric Slab Mode

**New mode entry:** `"Asymmetric Slab"` in `mode_combo`

**New stacked_widget page:** `_create_asymmetric_slab_panel()`

**Controls:**

| Control | Widget | Range | Default | Purpose |
|---------|--------|-------|---------|---------|
| Ice thickness | QDoubleSpinBox | 0.5–50 nm | 3.0 | Single ice layer on bottom |
| Water thickness | QDoubleSpinBox | 0.5–50 nm | 6.0 | Water layer on top |
| Crystal face | QComboBox | — | "Basal (0001)" | Face exposed at interface |

**Layout:**
```
┌─ Asymmetric Slab Parameters ──────────────┐
│ Ice thickness:     [3.00] nm  [?]         │
│ Water thickness:   [6.00] nm  [?]         │
│ Crystal face:     [Basal (0001) ▼] [?]    │
│                                            │
│ Info: box_z = ice_thickness + water_thickness │
│       = 3.00 + 6.00 = 9.00 nm             │
└────────────────────────────────────────────┘
```

**Box Z constraint:** `box_z = ice_thickness + water_thickness` (replaces `2*ice_thickness + water_thickness`)

**Source selection:** Same as current slab — uses `source_combo` (Ice Candidate or Hydrate Structure)

**Validation changes:**
- Remove the `2*ice_thickness + water_thickness` constraint
- Add `ice_thickness + water_thickness` constraint
- Add crystal face selection validation (ensure GenIce2 lattice supports selected face)

**Backend:**
- New file: `quickice/structure_generation/modes/asymmetric_slab.py`
- Uses `layer_assembly.py` with `LayerSpec` list: `[LayerSpec(type="ice", thickness=ice_thickness, source=candidate), LayerSpec(type="water", thickness=water_thickness)]`
- No top ice layer — water extends to `box_z`
- Under PBC, this creates a single ice-water interface (most common MD study configuration)

**Crystal face dropdown — added to ALL slab-derived modes:**

The crystal face selector should appear in:
- Slab panel (existing mode)
- Asymmetric Slab panel (new mode)
- Ice + Hydrate panel (new mode, for the ice layer face)

It should NOT appear in Pocket or Piece modes (those don't expose a specific face at a flat interface).

### Crystal Face Selection

**NOT a separate mode.** Crystal face is a per-mode control, like ice_thickness.

**Control:** QComboBox added to slab parameter panels

| Option | GenIce2 Lattice | Description |
|--------|----------------|-------------|
| "Basal (0001)" | `one[hh]` | Hexagonal flat plane, most studied face |
| "Primary Prism (10-10)" | `1h` (default) | Hexagonal channels exposed |
| "Secondary Prism (11-20)" | Custom reshape needed | Different surface structure |

**Implementation:**
- When user selects "Basal (0001)", the generator uses GenIce2 lattice `one[hh]` instead of default `1h`
- This is a **GenIce2 lattice name change**, not a post-generation rotation
- The face selector changes which GenIce2 lattice plugin is loaded
- Current QuickIce uses `1h` by default — this may expose prismatic face, not basal. The GenIce2 README notes this axis exchange. **This should be verified and documented.**

**Signal flow:**
```python
self.crystal_face_combo.currentIndexChanged.connect(self._on_face_changed)
# → Updates lattice_name in configuration dict
# → MainWindow passes lattice_name to generator
# → Generator calls safe_import('lattice', lattice_name)
```

**Important nuance:** Crystal face only makes sense for Ice Ih (hexagonal). Other ice phases (Ic, II, III, etc.) have different crystal systems and face naming. The dropdown should be disabled or hidden when a non-hexagonal candidate is selected.

### Ice + Hydrate Triple Interface

**New mode entry:** `"Ice + Hydrate"` in `mode_combo`

**New stacked_widget page:** `_create_ice_hydrate_panel()`

This is the most complex new mode. It requires TWO crystal sources (ice + hydrate) plus a water layer.

**Controls:**

| Control | Widget | Range | Default | Purpose |
|---------|--------|-------|---------|---------|
| Ice thickness | QDoubleSpinBox | 0.5–50 nm | 3.0 | Ice layer thickness |
| Hydrate thickness | QDoubleSpinBox | 0.5–50 nm | 3.0 | Hydrate layer thickness |
| Water thickness | QDoubleSpinBox | 0.5–50 nm | 4.0 | Water layer on top |
| Ice source | QComboBox | — | (from Tab 1) | Ice candidate selection |
| Hydrate source | QComboBox | — | (from Tab 2) | Hydrate lattice type + guest |
| Crystal face | QComboBox | — | "Basal (0001)" | Face of ice exposed to hydrate |

**Layout:**
```
┌─ Ice + Hydrate Parameters ────────────────────┐
│ Ice thickness:      [3.00] nm  [?]             │
│ Hydrate thickness:  [3.00] nm  [?]             │
│ Water thickness:    [4.00] nm  [?]             │
│ Crystal face:      [Basal (0001) ▼] [?]        │
│                                                │
│ ── Sources ──                                  │
│ Ice candidate:     [Rank 1 (ice_Ih) ▼] [Refresh]│
│ Hydrate:          [sI / CH4 ▼] [?]            │
│                                                │
│ Info: box_z = 3.00 + 3.00 + 4.00 = 10.00 nm   │
│ Layer: [Ice | Hydrate | Water]                 │
└────────────────────────────────────────────────┘
```

**Box Z constraint:** `box_z = ice_thickness + hydrate_thickness + water_thickness`

**Dual-source mechanism:**

This is the key new UI challenge. Currently, the source_combo switches between "Ice Candidate" (single source from Tab 1) and "Hydrate Structure" (single source from Tab 2). For ice+hydrate mode, we need BOTH sources.

**Recommended approach:** Don't extend the top-level source_combo. Instead, embed source selectors within the mode-specific panel:

```python
def _create_ice_hydrate_panel(self):
    # Ice source: reuse candidate_dropdown pattern
    self.ice_candidate_combo = QComboBox()
    self.ice_refresh_btn = QPushButton("Refresh ice candidates")
    
    # Hydrate source: reuse hydrate_panel pattern (lattice + guest dropdowns)
    self.hydrate_lattice_combo = QComboBox()  # sI, sII, sH
    self.hydrate_guest_combo = QComboBox()   # CH4, THF, CO2, H2
    
    # Thickness controls
    self.ice_thickness_input = QDoubleSpinBox(...)
    self.hydrate_thickness_input = QDoubleSpinBox(...)
    self.water_thickness_input = QDoubleSpinBox(...)
```

**Why embed source selectors in the mode panel (not top-level):**
- The top-level `source_combo` already works for single-source modes — don't break them
- Ice+hydrate mode is the only mode that needs dual sources
- Per-layer source selection naturally lives in the mode-specific panel
- This avoids adding a third option to `source_combo` that would disable/hide controls in conflicting ways

**Signal flow for ice+hydrate generation:**
```
generate_btn.clicked
  → mode == "ice_hydrate"
  → Emit new signal: ice_hydrate_generate_requested
  
MainWindow._on_ice_hydrate_generate()
  → Get ice candidate from interface_panel.ice_candidate_combo
  → Get hydrate config from interface_panel (lattice + guest)
  → Generate hydrate structure via hydrate_generator
  → Call GenIce2 for ice (if not using existing candidate)
  → Construct list[LayerSpec] with both sources
  → Start generation with dual-source candidate
```

**Backend:**
- New file: `quickice/structure_generation/modes/ice_hydrate_slab.py`
- Uses `layer_assembly.py` with `LayerSpec` list: `[LayerSpec(type="ice", thickness=ice_thickness, source=ice_candidate), LayerSpec(type="hydrate", thickness=hydrate_thickness, source=hydrate_candidate), LayerSpec(type="water", thickness=water_thickness)]`
- Must handle different cell dimensions for ice vs hydrate
- Overlap resolution at both interfaces (ice-hydrate and hydrate-water)

### Preview Panel

**New widget:** `LayerPreviewWidget` — a non-interactive schematic diagram showing the layer stack with dimensions.

This is **not a 3D viewer** — it's a 2D side-view diagram that updates in real-time as the user changes parameters. It shows:

```
┌─────────────────────┐  Z = 10.00 nm
│     Water           │  4.00 nm   (blue)
├─────────────────────┤  Z = 6.00 nm
│   Hydrate (sI)      │  3.00 nm   (orange)
├─────────────────────┤  Z = 3.00 nm
│   Ice (Ih)          │  3.00 nm   (cyan)
└─────────────────────┘  Z = 0.00 nm
  ← 5.00 nm → ← 5.00 nm →
```

**Implementation:**
- Custom QWidget with `paintEvent()` override
- Draws colored rectangles proportional to layer thicknesses
- Labels each layer with type, source, and thickness
- Shows Z-axis with tick marks
- Shows X/Y box dimensions
- Updates when any thickness or source input changes (connected via signals)

**Where to place it:** In the right column of InterfacePanel, above the 3D viewer. Or, replace the placeholder label when no structure has been generated yet. It occupies minimal vertical space (~150px) and provides immediate visual feedback.

**Why not QPainterScene or matplotlib:** Too heavy. A simple `paintEvent()` with `QPainter.drawRect()` and `QPainter.drawText()` is sufficient. No external dependencies.

**Preview data flow:**
```python
# In InterfacePanel._setup_connections():
self.ice_thickness_input.valueChanged.connect(self._update_layer_preview)
self.water_thickness_input.valueChanged.connect(self._update_layer_preview)
# etc.

def _update_layer_preview(self):
    layers = self._get_layer_specs_from_current_config()
    self.layer_preview.set_layers(layers, box_x=self.box_x_input.value(), box_y=self.box_y_input.value())
```

## PySide6 Implementation Patterns

### Mode-Dependent Controls: QStackedWidget (Already Used)

**Current pattern** (confirmed from source code):
```python
# _setup_ui():
self.stacked_widget = QStackedWidget()
self.stacked_widget.addWidget(self._create_slab_panel())    # index 0
self.stacked_widget.addWidget(self._create_pocket_panel())   # index 1
self.stacked_widget.addWidget(self._create_piece_panel())    # index 2

# _setup_connections():
self.mode_combo.currentIndexChanged.connect(self.stacked_widget.setCurrentIndex)
```

**Extension for new modes:**
```python
# Add to _setup_ui():
self.stacked_widget.addWidget(self._create_asymmetric_slab_panel())  # index 3
self.stacked_widget.addWidget(self._create_ice_hydrate_panel())      # index 4

# Update mode_combo items:
self.mode_combo.addItems(["Slab", "Pocket", "Piece", "Asymmetric Slab", "Ice + Hydrate"])
# Mapping: Slab→0, Pocket→1, Piece→2, Asymmetric Slab→3, Ice + Hydrate→4
```

**Important:** The mode→index mapping is currently implicit (order of addItems matches order of addWidget). For 5 modes, this becomes fragile. **Recommendation:** Use an explicit mapping dict:
```python
MODE_INDEX_MAP = {"Slab": 0, "Pocket": 1, "Piece": 2, "Asymmetric Slab": 3, "Ice + Hydrate": 4}
```

### Source Selection: QComboBox (Already Used)

**Current pattern:**
```python
self.source_combo = QComboBox()
self.source_combo.addItems(["Ice Candidate", "Hydrate Structure"])
self.source_combo.currentIndexChanged.connect(self._on_source_changed)
```

**For ice+hydrate dual source:** Do NOT add a third option to `source_combo`. Instead, embed per-layer source selectors in the `_create_ice_hydrate_panel()`. This keeps the top-level source selector simple for existing modes and adds complexity only where it's needed.

### Per-Layer Source Selection: Dual QComboBox

In `_create_ice_hydrate_panel()`:
```python
# Ice source: mirrors the existing candidate_dropdown pattern
self.ice_source_combo = QComboBox()
self.ice_source_combo.addItems(["No candidates - generate ice first"])
self.ice_refresh_btn = QPushButton("Refresh ice")

# Hydrate source: mirrors hydrate_panel pattern
self.hydrate_lattice_combo = QComboBox()
self.hydrate_lattice_combo.addItems(["sI", "sII", "sH"])
self.hydrate_guest_combo = QComboBox()
self.hydrate_guest_combo.addItems(["CH4", "THF", "CO2", "H2"])
```

**Signal wiring for ice candidate refresh in ice+hydrate mode:**
```python
self.ice_refresh_btn.clicked.connect(self.refresh_requested)  # Reuse existing signal
# MainWindow handles refresh the same way (updates all candidate dropdowns)
```

**Hydrate source combo population:**
```python
# Reuse data from types.py
from quickice.structure_generation.types import HYDRATE_LATTICES, GUEST_MOLECULES

for lattice_id, info in HYDRATE_LATTICES.items():
    self.hydrate_lattice_combo.addItem(info.description, userData=lattice_id)
```

### Parameter Input: QFormLayout + QDoubleSpinBox (Already Used)

**Current pattern** (from `_create_slab_panel`):
```python
group = QGroupBox("Slab Parameters")
layout = QFormLayout()
self.ice_thickness_input = QDoubleSpinBox()
self.ice_thickness_input.setSuffix(" nm")
self.ice_thickness_input.setRange(0.5, 50.0)
layout.addRow(ice_row)
```

**For new modes, follow identical pattern:**
- QGroupBox with mode name as title
- QFormLayout for parameter rows
- QDoubleSpinBox with " nm" suffix for all dimension inputs
- HelpIcon (existing) for tooltips
- Inline error QLabel (red, hidden by default) below each input

### Signal/Slot Architecture for Cross-Layer Validation

**Current pattern:** Validation happens at generate-time in `validate_configuration()`. Error labels are shown and the method returns False.

**For layer-aware validation:** Add real-time validation that fires on value changes:

```python
# In _create_asymmetric_slab_panel():
self.ice_thickness_input.valueChanged.connect(self._validate_asymmetric_slab)
self.water_thickness_input.valueChanged.connect(self._validate_asymmetric_slab)
self.box_z_input.valueChanged.connect(self._validate_asymmetric_slab)

def _validate_asymmetric_slab(self):
    ice_t = self.ice_thickness_input.value()
    water_t = self.water_thickness_input.value()
    box_z = self.box_z_input.value()
    expected_z = ice_t + water_t
    if abs(box_z - expected_z) > 0.01:
        self.box_z_error.setText(f"Box Z must equal ice + water = {expected_z:.2f} nm")
        self.box_z_error.setVisible(True)
    else:
        self.box_z_error.setVisible(False)
    
    # Update preview
    self._update_layer_preview()
```

**Cross-layer density warnings** (ice+hydrate mode):
```python
def _validate_ice_hydrate(self):
    ice_density = 0.92  # g/cm³ for ice Ih
    hydrate_lattice = self.hydrate_lattice_combo.currentData()
    hydrate_densities = {"CS1": 0.91, "CS2": 0.99, "CS3": None}
    hydrate_density = hydrate_densities.get(hydrate_lattice)
    
    if hydrate_density and abs(ice_density - hydrate_density) > 0.15:
        self.density_warning.setText(
            f"⚠ Density mismatch: Ice ({ice_density:.2f}) vs Hydrate ({hydrate_density:.2f}) g/cm³\n"
            f"Large density difference may cause interfacial instability."
        )
        self.density_warning.setVisible(True)
    else:
        self.density_warning.setVisible(False)
```

### Extension Strategy: Don't Break Existing Modes

**Key principle:** All changes must be backward-compatible. Existing Slab, Pocket, Piece modes must work identically.

**Approach:**
1. Add new mode entries to `mode_combo` at the END (preserves existing indices 0–2)
2. Add new pages to `stacked_widget` at the END
3. Add new fields to `InterfaceConfig` with defaults that reproduce current behavior
4. Refactor `slab.py` to use `layer_assembly.py` internally — same output, cleaner code
5. Keep existing signals and slots; add new ones for new modes
6. New mode modules are NEW files, not modifications to existing ones

**InterfaceConfig backward compatibility:**
```python
@dataclass
class InterfaceConfig:
    mode: str
    box_x: float
    box_y: float
    box_z: float
    seed: int
    ice_thickness: float = 0.0      # EXISTING
    water_thickness: float = 0.0     # EXISTING
    pocket_diameter: float = 0.0     # EXISTING
    pocket_shape: str = "sphere"     # EXISTING
    overlap_threshold: float = 0.25 # EXISTING
    # NEW FIELDS (with backward-compatible defaults)
    layer_order: list[str] = field(default_factory=lambda: ["ice", "water", "ice"])
    hydrate_thickness: float = 0.0  # For ice+hydrate mode
    crystal_face: str = "basal"     # Face selection
    ice_source_index: int = 0       # Candidate index for ice layer
    hydrate_lattice: str = "CS1"    # Hydrate lattice for hydrate layer
    hydrate_guest: str = "CH4"      # Guest molecule for hydrate layer
```

**When `mode == "slab"` and `layer_order` is not explicitly set:**
- Derive `layer_order` from mode: `["ice", "water", "ice"]`
- Derive thicknesses from `ice_thickness`, `water_thickness`
- Backward compatible — same behavior as before

**When `mode == "asymmetric_slab"`:**
- `layer_order = ["ice", "water"]`
- Thicknesses: `ice_thickness`, `water_thickness`
- `box_z = ice_thickness + water_thickness`

**When `mode == "ice_hydrate"`:**
- `layer_order = ["ice", "hydrate", "water"]`
- Thicknesses: `ice_thickness`, `hydrate_thickness`, `water_thickness`
- `box_z = ice_thickness + hydrate_thickness + water_thickness`

### Crystal Face Selector: QComboBox in Slab Panels

Add to all slab-derived parameter panels:

```python
# In _create_slab_panel() and _create_asymmetric_slab_panel():
face_row = QHBoxLayout()
self.crystal_face_combo = QComboBox()
self.crystal_face_combo.addItems([
    "Basal (0001)",           # GenIce2: one[hh]
    "Primary Prism (10-10)",  # GenIce2: 1h (current default)
])
self.crystal_face_combo.setToolTip(
    "Crystal face exposed at ice-water interface.\n"
    "• Basal (0001): Flat hexagonal plane, most studied\n"
    "• Primary Prism (10-10): Hexagonal channels, faster melting"
)
face_row.addWidget(QLabel("Crystal face:"))
face_row.addWidget(HelpIcon(...))
face_row.addWidget(self.crystal_face_combo)
face_row.addStretch()
layout.addRow(face_row)
```

**GenIce2 lattice mapping:**
```python
FACE_TO_LATTICE = {
    "Basal (0001)": "one[hh]",        # GenIce2 convention for basal on Z
    "Primary Prism (10-10)": "1h",    # GenIce2 default (axes exchanged)
}
```

**Disable for non-hexagonal phases:**
```python
def _on_candidate_changed(self, index):
    candidate = self._candidates[index] if self._candidates else None
    if candidate and candidate.phase_id not in ("ice_1h", "ice_Ih"):
        self.crystal_face_combo.setEnabled(False)
        self.crystal_face_combo.setToolTip("Crystal face selection only available for Ice Ih")
    else:
        self.crystal_face_combo.setEnabled(True)
```

## Configuration Validation

### Real-Time Validation Rules

| Rule | When to Check | Error Level | Message |
|------|---------------|-------------|---------|
| `box_z == sum(layer_thicknesses)` | Any thickness or box_z change | ERROR | "Box Z (X.XX nm) must equal sum of layers = Y.YY nm" |
| `box_x, box_y > 0` | Box dimension change | ERROR | "Box dimension must be positive" |
| All thicknesses > 0 | Thickness change | ERROR | "Layer thickness must be positive" |
| `ice_thickness >= 1.0 nm` | Ice thickness change | WARNING | "Very thin ice slab — minimum 2 nm recommended for stable interface" |
| `water_thickness >= 2.0 nm` | Water thickness change | WARNING | "Thin water layer — may see PBC artifacts. 3+ nm recommended" |
| Density mismatch > 15% | Ice+hydrate source change | WARNING | "⚠ Density mismatch between adjacent layers" |
| Lattice incompatibility | Crystal face + non-Ih candidate | ERROR | "Crystal face selection only available for Ice Ih" |

### Warning vs Error Distinction

**ERROR** (red label, blocks generation):
- Box dimension mismatches
- Zero or negative thicknesses
- Incompatible crystal phase + face selection
- Pocket diameter > box dimensions

**WARNING** (orange/yellow label, allows generation):
- Thin layers (below recommended minimum)
- Density mismatch between adjacent layers
- Very small or very large box dimensions

**Implementation:**
```python
# Add warning label style alongside existing error style
self.density_warning = QLabel()
self.density_warning.setStyleSheet("color: #cc7700;")  # Orange for warning
self.density_warning.setWordWrap(True)
self.density_warning.hide()
```

### Cross-Layer Density Validation (Ice + Hydrate Mode)

When ice density (0.92 g/cm³) and hydrate density differ significantly, warn the user:

| Ice Type | Hydrate Type | Ice ρ | Hydrate ρ | Δρ | Warning? |
|----------|-------------|-------|-----------|-----|----------|
| Ice Ih | sI CH4 | 0.92 | 0.91 | 1% | No — excellent match |
| Ice Ih | sI CO2 | 0.92 | 0.92 | 0% | No — perfect match |
| Ice Ih | sII THF | 0.92 | 0.99 | 7% | No — acceptable |
| Ice Ih | sII empty | 0.92 | 0.81 | 11% | Low — note in log |
| Ice Ih | sH | 0.92 | ~0.88 | 4% | No — acceptable |

**Implementation:**
```python
LAYER_DENSITIES = {
    "ice_1h": 0.92,
    "CS1_CH4": 0.91, "CS1_CO2": 0.92, "CS1_H2": 0.88,
    "CS2_THF": 0.99, "CS2_CH4": 0.89,
    "CS3": 0.88,
}

def _compute_density_mismatch(layer_a: str, layer_b: str) -> float:
    rho_a = LAYER_DENSITIES.get(layer_a, 1.0)
    rho_b = LAYER_DENSITIES.get(layer_b, 1.0)
    return abs(rho_a - rho_b) / max(rho_a, rho_b) * 100  # percent
```

### Preview: Layer Stack Diagram

The `LayerPreviewWidget` provides real-time visual feedback:

**Drawing algorithm:**
1. Compute cumulative Z positions: `z_positions = [0, t1, t1+t2, ..., box_z]`
2. For each layer, draw a colored rectangle proportional to its thickness
3. Add text labels: layer type, source name, thickness
4. Draw Z-axis with tick marks
5. Draw X/Y dimension indicators

**Colors:**
- Ice: Cyan (0.0, 0.8, 0.8) — matching InterfaceViewer ICE_COLOR
- Water: Cornflower blue (0.39, 0.58, 0.93) — matching InterfaceViewer WATER_COLOR
- Hydrate: Orange (1.0, 0.65, 0.0) — new color for hydrate layers
- Guests: Gray (0.8, 0.8, 0.8) — matching InterfaceViewer GUEST_COLOR

**Update triggers:**
- Any `QDoubleSpinBox.valueChanged` signal
- Any `QComboBox.currentIndexChanged` signal
- Mode change (mode_combo)

## Anti-Patterns to Avoid

### Anti-Pattern 1: Drag-and-Drop Layer Ordering

**What:** QListWidget with drag-and-drop for reordering layers (Photoshop-style)

**Why bad:** Most orderings are physically meaningless under PBC (e.g., water-ice-water = ice-water-ice with shifted origin). Users could create nonsensical configurations. Adds UI complexity for no scientific gain.

**Instead:** Use named mode presets with fixed layer ordering. If users need a new ordering, it should be a new named mode, not a custom rearrangement.

### Anti-Pattern 2: Per-Layer "Add/Remove" Buttons

**What:** "+" and "−" buttons to add/remove layers from the stack

**Why bad:** Leads to combinatorial explosion of validation rules. Most resulting configurations are physically invalid. No scientific demand for arbitrary N-layer stacks.

**Instead:** Each named mode has a fixed number of layers with predetermined types.

### Anti-Pattern 3: Slab Orientation Flip Control

**What:** A "Flip" button or dropdown to switch "ice-on-bottom" vs "ice-on-top"

**Why bad:** Under PBC, these are the same structure (just shifted by half the box). The periodic image makes orientation irrelevant. Adding this control would confuse users into thinking it matters.

**Instead:** Document that PBC makes orientation a no-op. Do NOT implement any flip control. If asked, explain PBC symmetry.

### Anti-Pattern 4: Mixed Hydrate Type Selector

**What:** "sI + sII" or "sI + sH" multi-select in the hydrate source

**Why bad:** 31% lattice mismatch between sI and sII. No common supercell below ~10 nm. No published MD study uses mixed hydrate types. The interface between them has never been characterized.

**Instead:** Support only ONE hydrate type per generation. If users need different hydrate types, use separate simulations.

### Anti-Pattern 5: General "Any Structure for Any Layer" Composition

**What:** File dialog to load arbitrary .gro/.pdb as a layer source

**Why bad:** QuickIce's overlap resolution assumes specific water molecule geometry (TIP3P/TIP4P). Arbitrary structures may have different atom names, molecule topologies, and coordinate conventions. Validation becomes intractable.

**Instead:** Only allow sources that QuickIce generates (ice candidates from Tab 1, hydrate structures from Tab 2). This guarantees compatible molecule formats.

### Anti-Pattern 6: Modifying the Top-Level Source Combo for Dual Source

**What:** Adding a third option "Ice + Hydrate" to `source_combo`

**Why bad:** The `source_combo` currently controls whether ice candidate or hydrate controls are visible. Adding a third option creates a 3-way branching logic that's hard to maintain. The dual-source pattern doesn't fit the existing single-source model.

**Instead:** Keep `source_combo` as-is for existing modes. Embed dual-source selectors within the ice+hydrate mode-specific panel. The mode selector (not the source selector) determines how many sources are needed.

## Implementation Phases

### Phase 1: Asymmetric Slab + Crystal Face (Low complexity)

**Files to create:**
- `quickice/structure_generation/layer_assembly.py` — Generic layer assembly engine
- `quickice/structure_generation/modes/asymmetric_slab.py` — Asymmetric slab mode

**Files to modify:**
- `quickice/gui/interface_panel.py` — Add asymmetric slab panel, crystal face combo to slab panels
- `quickice/structure_generation/types.py` — Add new fields to InterfaceConfig
- `quickice/structure_generation/interface_builder.py` — Add routing for asymmetric_slab mode

**Refactor:**
- `quickice/structure_generation/modes/slab.py` — Refactor to use `layer_assembly.py` internally

### Phase 2: Layer Preview Widget (Medium complexity)

**Files to create:**
- `quickice/gui/layer_preview.py` — LayerPreviewWidget

**Files to modify:**
- `quickice/gui/interface_panel.py` — Add preview widget to right column

### Phase 3: Ice + Hydrate Triple Interface (High complexity)

**Files to create:**
- `quickice/structure_generation/modes/ice_hydrate_slab.py` — Ice+hydrate assembly mode

**Files to modify:**
- `quickice/gui/interface_panel.py` — Add ice+hydrate panel with dual source
- `quickice/gui/main_window.py` — Wire dual-source generation signals
- `quickice/structure_generation/types.py` — Add ice+hydrate fields to InterfaceConfig
- `quickice/structure_generation/interface_builder.py` — Add routing for ice_hydrate mode
- `quickice/structure_generation/generator.py` — Support GenIce2 lattice name override for face selection

## Sources

| Source | Confidence | Notes |
|--------|------------|-------|
| QuickIce interface_panel.py | HIGH | Read full file (935 lines); all UI patterns and widget choices from actual source |
| QuickIce slab.py | HIGH | Read full file (641 lines); Z-stacking implementation analyzed from actual code |
| QuickIce interface_builder.py | HIGH | Read full file (354 lines); validation and routing from actual code |
| QuickIce types.py | HIGH | Read InterfaceConfig dataclass; all fields and from_dict method from actual source |
| QuickIce main_window.py | HIGH | Read signal wiring sections; generation flow from actual code |
| QuickIce hydrate_panel.py | HIGH | Read partial; hydrate source pattern from actual code |
| QuickIce viewmodel.py | HIGH | Read partial; MVVM signal pattern from actual code |
| Wave 1 STACK.md | HIGH | GenIce2 API capabilities; all from source code analysis |
| Wave 1 FEATURES.md | HIGH | Physics constraints; PBC symmetry, lattice mismatch, density compatibility |
| Avogadro documentation | LOW | Only saw index page; building workflow pattern from training knowledge |
| VMD documentation | LOW | Only saw logging page; representation list pattern from training knowledge |
| Packmol user guide | MEDIUM | Read full page; constraint-based layer composition verified from official docs |
| LAMMPS website | LOW | Only saw landing page; no GUI documentation found |
| CHARMM-GUI Membrane Builder | LOW | Pattern from training knowledge; not directly verified |
| PBC symmetry argument | HIGH | Fundamental property of periodic boundary conditions; textbook physics |
