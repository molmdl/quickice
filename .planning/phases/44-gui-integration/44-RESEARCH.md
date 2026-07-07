# Phase 44: GUI Integration - Research

**Researched:** 2026-07-07
**Domain:** PySide6 GUI surface for custom-guest upload in the Hydrate tab (plan 44-02 only)
**Confidence:** HIGH (all claims verified by reading source + executing validation/Pitfall-6 probes against the live `quickice` conda env)

## Summary

Phase 44 has been audited down to ONE remaining plan: **44-02 — Custom guest upload panel in the Hydrate tab**. The other three original stubs (44-01 lattice dropdown, 44-03 per-cage rows, 44-04 depol dropdown) were already delivered as vertical slices inside Phases 39-04, 42-06, and 43-02 respectively, and are verified present in `quickice/gui/hydrate_panel.py`. This research therefore focuses exclusively on what 44-02 needs: a `.gro` + `.itp` QFileDialog upload pair in the Hydrate tab that surfaces the specific validation errors from `validate_custom_guest_files` (GUI-02 + GUI-05), and wires the validated custom guest into the existing 42-06 per-cage row infrastructure so it becomes selectable per-cage (unblocking GUI-06's custom path).

The engine is **fully ready** — Phase 40 (custom guest bridge), 41-06 (export custom branch), 42-01 (CageGuestAssignment data model + __post_init__ validation), 42-02 (generator ExitStack dedup), and 42-05/42-08 (mixed export) all already support custom `CageGuestAssignment` entries in `HydrateConfig.cage_guest_assignments`. **No engine changes are required.** 44-02 is pure GUI surface work: build a small upload QGroupBox, reuse `validate_custom_guest_files` (do NOT reimplement), add a "Custom: {residue}" option to each per-cage QComboBox, and extend `get_configuration` to emit a fully-populated custom `CageGuestAssignment`.

The closest in-repo analog is `quickice/gui/custom_molecule_panel.py` (Tab 3 custom-molecule upload), which establishes the exact QFileDialog + QLabel-status + green/red/orange validation-label pattern to copy. The critical design finding (verified by execution) is that the GUI **must parse the GRO itself** to obtain `guest_atom_labels`/`guest_atom_count` (validation returns counts/residue_name but NOT the atom-name list), and **must avoid assigning the same custom guest to 2 cages** because the explicit `cage_guest_assignments` path triggers Pitfall 6 (legacy single-guest shim does not, but the GUI uses the explicit path).

**Primary recommendation:** Add ONE shared custom-guest upload QGroupBox to `HydratePanel._setup_ui` (between the lattice group and the cage-assignment group). On successful upload + validation, store the custom-guest descriptor on the panel and rebuild the cage rows so every per-cage combo gains a "Custom: {residue}" item. Let the user pick which cage(s) get the custom guest; recommend restricting the custom guest to a single cage to avoid Pitfall 6 (or surface the error). `get_configuration` builds a custom `CageGuestAssignment` with full metadata parsed from the GRO.

## Standard Stack

The established libraries/widgets for this domain (all already in the `quickice` conda env — **no new dependencies**):

### Core
| Widget / Tool | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PySide6.QtWidgets | 6.10.2 | GUI framework | Project-wide GUI stack (`quickice/gui/` already imports it) |
| `QFileDialog` | — | `.gro`/`.itp` file picker | Used in `custom_molecule_panel.py:591,607` and `export.py` — the established picker |
| `QGroupBox` + `QFormLayout` | — | Upload panel container | Matches `_create_lattice_group`/`_create_cage_assignment_group` style (`hydrate_panel.py:171,226`) |
| `QLabel` (status) | — | Validation feedback (green/red/orange/gray/black) | Established pattern `custom_molecule_panel.py:172-234,649-693` |
| `QPushButton` | — | "Upload .gro" / "Upload .itp" buttons | `custom_molecule_panel.py:152,180` |
| `QComboBox` | — | Per-cage guest selector (already built by 42-06) | `hydrate_panel.py:293` — extend, not replace |
| `QDoubleSpinBox` | — | Per-cage occupancy (already built by 42-06) | `hydrate_panel.py:303` |

### Supporting (reuse — do NOT reimplement)
| Function | Location | Purpose | When to Use |
|---------|---------|---------|-------------|
| `validate_custom_guest_files` | `custom_guest_bridge.py:177` | Full GRO+ITP validation checklist → `CustomGuestValidation` | On upload, to produce GUI-05 specific errors |
| `parse_gro_file` | `gro_parser.py:90` | `(positions, atom_names, cell)` from GRO | After valid upload, to get `guest_atom_labels` (validation does NOT return atom names) |
| `extract_residue_name_from_gro` | `gro_parser.py:113` | Residue name from first GRO atom line | Redundant with `validation.residue_name` — prefer the latter |
| `parse_itp_file` | `itp_parser.py:36` | `ITPMoleculeInfo` (has `molecule_name`) | Optional — to derive a `guest_type` slug from the ITP moleculetype name |
| `CageGuestAssignment` / `HydrateConfig` | `types.py:429,501` | Data model the GUI must populate | `get_configuration` builds these |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Reusing `validate_custom_guest_files` | Reimplement validation in the GUI | **NEVER** — engine validation is the canonical source; the GUI must surface its messages verbatim (GUI-05) |
| `QFileDialog.getOpenFileName` | A custom file picker | Established pattern; native dialog is best UX |
| Single shared upload slot | Per-cage upload buttons | Single slot is simpler, matches e2e convention (one ethanol), avoids Pitfall 6 complexity — see Q4 |

**Installation:** none — all dependencies already in `environment.yml` (PySide6 6.10.2). **Do not add deps.**

## Architecture Patterns

### Recommended Project Structure (where 44-02 lands)
```
quickice/gui/
├── hydrate_panel.py          # MODIFY: add _create_custom_guest_group(), extend _rebuild_cage_rows + get_configuration
quickice/structure_generation/
├── custom_guest_bridge.py    # REUSE ONLY: validate_custom_guest_files (do NOT edit)
├── gro_parser.py             # REUSE ONLY: parse_gro_file (do NOT edit)
├── itp_parser.py              # REUSE ONLY: parse_itp_file (optional, for guest_type slug)
└── types.py                  # REUSE ONLY: CageGuestAssignment / HydrateConfig (do NOT edit)
tests/
└── test_hydrate_panel.py     # EXTEND: add TestCustomGuestUpload class (same fixture pattern)
```

### Pattern 1: Insert the upload QGroupBox between lattice and cage-assignment groups
**What:** Add a new `_create_custom_guest_group() -> QGroupBox` method and call it in `_setup_ui` between the lattice group and the cage-assignment group.
**When to use:** The custom-guest slot is panel-level (shared across all cage rows), so it belongs ABOVE the per-cage rows, not inside one row.
**Insertion point (file:line):** `hydrate_panel.py:69-75` — add a call between `lattice_group` (line 69-70) and `cage_group` (line 74-75):

```python
# hydrate_panel.py _setup_ui, after line 70 (lattice_group) and before line 74 (cage_group):
        # Custom guest upload group (Phase 44-02). ONE shared slot; on valid
        # upload the custom guest becomes a "Custom: {residue}" option in
        # every per-cage combo (added by _rebuild_cage_rows).
        custom_guest_group = self._create_custom_guest_group()
        left_layout.addWidget(custom_guest_group)
```

The group should hold: a "Upload .gro File" button + `gro_status` QLabel, a "Upload .itp File" button + `itp_status` QLabel, and a `validation_label` QLabel (word-wrapped) — mirroring `custom_molecule_panel.py:150-205,207-234`.

### Pattern 2: Extend `_rebuild_cage_rows` to add the custom option when loaded
**What:** After the `GUEST_MOLECULES` loop in `_rebuild_cage_rows`, append a "Custom: {residue_name}" item to each per-cage combo IF a validated custom guest is stored on the panel.
**When to use:** Every time the lattice changes (rows are rebuilt) OR a custom guest is uploaded/removed.
**Source:** `hydrate_panel.py:293-298` (the current GUEST_MOLECULES loop):

```python
# hydrate_panel.py _rebuild_cage_rows, after line 298 (the GUEST_MOLECULES loop):
            combo = QComboBox()
            for guest_id, guest_info in GUEST_MOLECULES.items():
                combo.addItem(
                    f"{guest_info['name']} ({guest_info['formula']})",
                    guest_id,
                )
            # Phase 44-02: if a custom guest is loaded, add it as an option.
            if self._custom_guest is not None:
                combo.addItem(
                    f"Custom: {self._custom_guest['residue_name']}",
                    self._custom_guest['guest_type'],  # sentinel data; is_custom_guest detects via not in GUEST_MOLECULES
                )
            combo.currentIndexChanged.connect(self._on_guest_changed)
```

After upload succeeds, call `self._rebuild_cage_rows()` to refresh all combos with the new option (and preserve each row's current selection where possible).

### Pattern 3: `get_configuration` builds a custom `CageGuestAssignment` with FULL metadata
**What:** When a per-cage combo's `currentData()` is the custom `guest_type` (i.e. `not in GUEST_MOLECULES`), build the `CageGuestAssignment` with the stored custom metadata (residue_name, gro_path, itp_path, atom_labels, atom_count). For built-in selections, keep the existing 2-field construction.
**When to use:** Always — `get_configuration` is called on every `configuration_changed` signal (`main_window.py:742`) and on generate (`main_window.py:748`).
**Source:** extend `hydrate_panel.py:493-499`:

```python
# hydrate_panel.py get_configuration, replacing lines 493-499:
        for cage_key, combo in self._cage_guest_combos.items():
            guest_id = combo.currentData() or "ch4"
            occ = self._cage_occupancy_spins[cage_key].value()
            if guest_id not in GUEST_MOLECULES and self._custom_guest is not None:
                # Phase 44-02: custom guest — supply FULL metadata (no auto-populate).
                cg = self._custom_guest
                cage_guest_assignments[cage_key] = CageGuestAssignment(
                    guest_type=cg['guest_type'],
                    occupancy=occ,
                    guest_residue_name=cg['residue_name'],
                    guest_gro_path=cg['gro_path'],
                    guest_itp_path=cg['itp_path'],
                    guest_atom_labels=list(cg['atom_labels']),
                    guest_atom_count=cg['atom_count'],
                )
            else:
                cage_guest_assignments[cage_key] = CageGuestAssignment(
                    guest_type=guest_id, occupancy=occ
                )
```

### Pattern 4: QFileDialog + status-label upload (copy from Tab 3)
**What:** Two buttons, each opening `QFileDialog.getOpenFileName` with the established filter, storing the `Path`, and updating a status QLabel.
**When to use:** The custom-guest upload pair.
**Source:** `custom_molecule_panel.py:589-631`:

```python
# Source: custom_molecule_panel.py:589-603 (GRO), 605-631 (ITP)
filepath, _ = QFileDialog.getOpenFileName(
    self, "Select Custom Guest GRO File", "",
    "GRO Files (*.gro);;All Files (*)"
)
if filepath:
    self._gro_path = Path(filepath)
    self.gro_status.setText(self._gro_path.name)
    self.gro_status.setStyleSheet("color: black;")
    self._try_validate()  # validates only when BOTH files selected
```

### Pattern 5: Validation feedback status label (green/red/orange)
**What:** A word-wrapped `validation_label` that shows specific messages with color coding.
**When to use:** After both files are selected, run validation and display the result.
**Source:** `custom_molecule_panel.py:649-693`:

```python
# Source: custom_molecule_panel.py:666-693
if result.is_valid:
    self.validation_label.setText("✓ Custom guest validated successfully")
    self.validation_label.setStyleSheet("color: green;")
else:
    self.validation_label.setText(
        "✗ Validation failed:\n" + "\n".join(result.errors)
    )
    self.validation_label.setStyleSheet("color: red;")
if result.warnings:  # e.g. missing [ atomtypes ] — non-blocking
    QMessageBox.warning(self, "Custom Guest Warnings", "\n".join(result.warnings))
```

### Anti-Patterns to Avoid
- **Reimplementing validation in the GUI** — `validate_custom_guest_files` is canonical; the GUI only displays its `errors`/`warnings` verbatim. Any bespoke check drifts from the engine.
- **Top-level `import PySide6` in test modules at module scope without offscreen** — headless tests crash; use the per-class `monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")` fixture.
- **Calling `get_configuration` without a try/except when a custom guest is in 2 cages** — Pitfall 6 ValueError will propagate uncaught through `main_window.py:742,748` (neither is wrapped). See Common Pitfalls #1.
- **Auto-populating custom `CageGuestAssignment` metadata** — `__post_init__` does NOT auto-populate custom metadata (only built-ins); the GUI MUST supply `guest_atom_labels`/`guest_atom_count` explicitly. See Don't Hand-Roll.
- **Hardcoding `guest_type`** — derive a slug per upload; the sys.modules key must be unique per session. See Q10.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GRO+ITP validation (parseable, atom-count match, residue ≤3, comb-rule=2, audit_name) | Reimplement checks in the GUI | `validate_custom_guest_files(gro, itp, guest_type)` (`custom_guest_bridge.py:177`) | 7-step checklist with specific messages already tested; GUI-05 requires THESE exact messages |
| Extracting `guest_atom_labels` from the GRO | Manual GRO column parsing | `parse_gro_file(gro)` → `atom_names` (`gro_parser.py:90`) | Fixed-width column parsing + >50nm Å-mixup guard already handled |
| Extracting residue name | Manual column 6-10 slice | `validation.residue_name` (from `validate_custom_guest_files`) | Already extracted; redundant to re-parse |
| Validating the `guest_type` slug | Regex check | `audit_name` (called inside `validate_custom_guest_files` step 7) | GenIce2's own validator; `^[A-Za-z0-9-_]+$` |
| Custom guest `CageGuestAssignment` metadata auto-populate | Look up from a custom dict | (nothing — must supply explicitly) | `__post_init__` only auto-populates built-ins; custom requires explicit `guest_atom_labels`/`guest_atom_count` |
| sys.modules registration / cleanup | Call `register_custom_guest` from the GUI | (do nothing — generator handles it) | `hydrate_generator.py:167-176` ExitStack registers/cleans up on the worker thread; the GUI just builds the config |

**Key insight:** The GUI's only job is to (1) collect paths via QFileDialog, (2) call `validate_custom_guest_files` and display its result, (3) on success call `parse_gro_file` once to get `atom_names`, (4) store the descriptor, (5) rebuild cage rows so the custom option appears, (6) in `get_configuration` emit a fully-populated `CageGuestAssignment`. Everything else (sys.modules, generation, export) is the engine's job.

## Common Pitfalls

### Pitfall 1: Pitfall 6 — same custom guest in 2 cages CRASHES the GUI (VERIFIED)
**What goes wrong:** If the user selects the custom guest for both `small` and `large` cages, `get_configuration()` builds an explicit `cage_guest_assignments` with two custom `CageGuestAssignment`s sharing the same `guest_residue_name`. `HydrateConfig.__post_init__` (`types.py:711-720`) raises `ValueError: Duplicate guest_residue_name 'MOL' across custom cage assignments: cage 'small' and cage 'large' both use this residue name.`
**Why it happens:** The explicit `cage_guest_assignments` path (`types.py:666-720`) enforces distinct `guest_residue_name` across custom assignments. The legacy single-guest shim (`types.py:637-665`) does NOT run this check, so the e2e test path (one custom guest in all cages) works — but the GUI uses the explicit path. **Asymmetry verified by execution:** explicit same-guest-2-cages → ValueError; legacy same-guest-2-cages → OK; mixed 1-custom-1-builtin → OK.
**How to avoid:** Pick ONE:
  1. **(Recommended)** Restrict the custom guest to a single cage at a time: when the user selects "Custom: MOL" in a second cage, auto-clear the first cage back to a built-in (or disable the custom option in other combos once one cage uses it). Simplest, zero error surface.
  2. Wrap `get_configuration()` in try/except in `_on_hydrate_config_changed` (`main_window.py:742`) and `_on_hydrate_generate_clicked` (`main_window.py:748`) and surface the ValueError via `QMessageBox.critical` + log. More permissive but exposes an assignment-conflict error to the user.
**Warning signs:** `main_window.py:742,748` call `get_configuration()` with NO try/except — a ValueError there propagates uncaught and crashes the signal handler (silent traceback to stderr, UI desync). This is a pre-existing latent risk that 44-02 makes reachable.

### Pitfall 2: `__post_init__` does NOT auto-populate custom metadata
**What goes wrong:** Building `CageGuestAssignment(guest_type="etoh_gui", occupancy=100, guest_residue_name="MOL", guest_gro_path=..., guest_itp_path=...)` WITHOUT `guest_atom_labels`/`guest_atom_count` raises `ValueError: Custom guest_type 'etoh_gui' in cage 'small' requires guest_atom_labels...` (`types.py:693-704`).
**Why it happens:** `__post_init__` auto-populates built-in metadata from `GUEST_MOLECULES` (`types.py:674-678`) but REQUIRES custom metadata explicitly (`types.py:686-710`).
**How to avoid:** The GUI must call `parse_gro_file(gro)` after a valid upload to get `atom_names` (→ `guest_atom_labels`), and use `validation.gro_atom_count` (→ `guest_atom_count`). Store both on the panel's custom-guest descriptor and pass them into every custom `CageGuestAssignment`.
**Warning signs:** `ValueError: ... requires guest_atom_labels` at `get_configuration` time.

### Pitfall 3: `validate_custom_guest_files` does NOT return atom names
**What goes wrong:** Assuming `CustomGuestValidation` has an `atom_labels` field — it does not. It returns `gro_atom_count`, `itp_atom_count`, `residue_name`, `comb_rule`, `errors`, `warnings`, `is_valid` only (`custom_guest_bridge.py:62-68`).
**Why it happens:** The validator was designed for pass/fail + counts, not for emitting the atom-name list (the generator gets atom names from `build_custom_guest_module`, which re-parses the GRO).
**How to avoid:** Call `parse_gro_file(gro)` separately after validation succeeds. For a single-molecule custom-guest GRO, `atom_names` IS `guest_atom_labels` (verified: `etoh.gro` → `['H','C','H','H','C','H','H','O','H']`, 9 atoms).
**Warning signs:** `AttributeError: 'CustomGuestValidation' object has no attribute 'atom_labels'`.

### Pitfall 4: Truncated / malformed GRO raises IndexError (not just ValueError)
**What goes wrong:** A plain-text file or truncated GRO raises `IndexError: list index out of range` inside `parse_gro_file`. `validate_custom_guest_files` catches `(ValueError, OSError, IndexError)` (`custom_guest_bridge.py:225`) and surfaces it as `"Failed to parse GRO file {path}: list index out of range"`.
**Why it happens:** `parse_gro_string` indexes `lines[1]` and `lines[2+i]` without bounds-checking (`gro_parser.py:39,49`).
**How to avoid:** Do NOT call `parse_gro_file` directly on user input without the validation guard. Always run `validate_custom_guest_files` FIRST; only call `parse_gro_file` when `result.is_valid` is True. The GUI's broad `except` (allowed per AGENTS.md for GUI code) is a safety net but validation-first is the clean path.
**Warning signs:** `IndexError` in a GUI handler from an unparseable upload.

### Pitfall 5: Missing `[ atomtypes ]` is a WARNING, not an error
**What goes wrong:** Rejecting an upload because the ITP has no `[ atomtypes ]` section — this is wrong; it's non-blocking.
**Why it happens:** `validate_custom_guest_files` step 6 appends to `warnings`, not `errors` (`custom_guest_bridge.py:285-294`); `is_valid` stays True.
**How to avoid:** Show warnings via `QMessageBox.warning` (non-blocking dialog) like `custom_molecule_panel.py:744-758` (`_show_validation_warnings`), and still treat the upload as valid (enable the custom option in combos). Verified: `etoh_no_atomtypes.itp` → `is_valid=True`, `warnings=['No [ atomtypes ] in ITP; ensure types are defined in the main .top']`.

### Pitfall 6: `[ defaults ]` absent is ACCEPTED (comb_rule=None)
**What goes wrong:** Rejecting an upload because the ITP has no `[ defaults ]` section — wrong. `parse_itp_defaults_comb_rule` returns `None`, and `validate_custom_guest_files` only errors when `comb is not None and comb != 2` (`custom_guest_bridge.py:276-281`).
**Why it happens:** QuickIce's main `.top` supplies comb-rule=2, so a custom ITP without `[ defaults ]` is fine.
**How to avoid:** Treat `comb_rule=None` as valid. Verified: `etoh.itp` → `comb_rule=None`, `is_valid=True`.

### Pitfall 7: `guest_type` must be a unique sys.modules key per session
**What goes wrong:** Hardcoding `guest_type="custom"` and uploading two different custom guests in one session → the second `build_custom_guest_module` asserts the `sys.modules` key is absent (`custom_guest_bridge.py:346`) and crashes generation.
**Why it happens:** `custom_guest_module` asserts `key not in sys.modules` (`custom_guest_bridge.py:346`); the generator dedups by `guest_type` (`hydrate_generator.py:146`) so the same slug twice is fine within one config, but two DIFFERENT uploads with the same slug across sessions is the risk.
**How to avoid:** For the single-slot design (Q4 recommendation), derive a stable slug per upload (e.g. from the ITP moleculetype name or GRO residue name, lowercased + sanitized) and overwrite the slot on re-upload. Re-uploading replaces `_custom_guest` entirely; the previous one is gone from the config, so no sys.modules collision (the generator only registers what's in `cage_guest_assignments`).

### Pitfall 8: Headless GUI tests crash without `QT_QPA_PLATFORM=offscreen`
**What goes wrong:** Constructing `HydratePanel()` in CI/SSH without a display raises a Qt platform error.
**How to avoid:** Use the per-class fixture from `test_hydrate_panel.py:50-56` (monkeypatch `QT_QPA_PLATFORM=offscreen` + singleton `QApplication`). Copy it verbatim for the new `TestCustomGuestUpload` class.

## Code Examples

### Example 1: The custom-guest upload + validate flow (the core of 44-02)
```python
# Source pattern: custom_molecule_panel.py:589-693 + custom_guest_bridge.py:177
from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QMessageBox, QLabel, QPushButton, QGroupBox, QFormLayout, QHBoxLayout

def _create_custom_guest_group(self) -> QGroupBox:
    group = QGroupBox("Custom Guest (optional)")
    layout = QFormLayout()
    # .gro row
    gro_row = QHBoxLayout()
    self.cg_gro_button = QPushButton("Upload .gro File")
    self.cg_gro_button.setMaximumWidth(150)
    self.cg_gro_button.clicked.connect(self._upload_custom_gro)
    self.cg_gro_status = QLabel("No file selected")
    self.cg_gro_status.setStyleSheet("color: gray;")
    gro_row.addWidget(self.cg_gro_button)
    gro_row.addWidget(self.cg_gro_status)
    gro_row.addStretch()
    layout.addRow("GRO:", gro_row)
    # .itp row
    itp_row = QHBoxLayout()
    self.cg_itp_button = QPushButton("Upload .itp File")
    self.cg_itp_button.setMaximumWidth(150)
    self.cg_itp_button.clicked.connect(self._upload_custom_itp)
    self.cg_itp_status = QLabel("No file selected")
    self.cg_itp_status.setStyleSheet("color: gray;")
    itp_row.addWidget(self.cg_itp_button)
    itp_row.addWidget(self.cg_itp_status)
    itp_row.addStretch()
    layout.addRow("ITP:", itp_row)
    # Validation feedback
    self.cg_validation_label = QLabel("Upload both files to validate")
    self.cg_validation_label.setWordWrap(True)
    layout.addRow(self.cg_validation_label)
    # Slot state (None until a valid pair is uploaded)
    self._custom_guest = None  # dict: guest_type, residue_name, gro_path, itp_path, atom_labels, atom_count
    self._cg_gro_path = None
    self._cg_itp_path = None
    group.setLayout(layout)
    return group

def _upload_custom_gro(self):
    filepath, _ = QFileDialog.getOpenFileName(
        self, "Select Custom Guest GRO File", "",
        "GRO Files (*.gro);;All Files (*)"
    )
    if filepath:
        self._cg_gro_path = Path(filepath)
        self.cg_gro_status.setText(self._cg_gro_path.name)
        self.cg_gro_status.setStyleSheet("color: black;")
        self._try_validate_custom_guest()

def _upload_custom_itp(self):
    filepath, _ = QFileDialog.getOpenFileName(
        self, "Select Custom Guest ITP File", "",
        "ITP Files (*.itp);;All Files (*)"
    )
    if filepath:
        self._cg_itp_path = Path(filepath)
        self.cg_itp_status.setText(self._cg_itp_path.name)
        self.cg_itp_status.setStyleSheet("color: black;")
        self._try_validate_custom_guest()

def _try_validate_custom_guest(self):
    if not (self._cg_gro_path and self._cg_itp_path):
        return
    # Derive a guest_type slug (see Q10). e.g. from ITP moleculetype name.
    guest_type = self._derive_guest_type_slug(self._cg_itp_path)
    # REUSE the canonical validator — do NOT reimplement (GUI-05).
    from quickice.structure_generation.custom_guest_bridge import (
        validate_custom_guest_files,
    )
    result = validate_custom_guest_files(
        self._cg_gro_path, self._cg_itp_path, guest_type
    )
    if not result.is_valid:
        self.cg_validation_label.setText(
            "✗ Validation failed:\n" + "\n".join(result.errors)
        )
        self.cg_validation_label.setStyleSheet("color: red;")
        self._custom_guest = None
        self._rebuild_cage_rows()  # remove the custom option from combos
        self.configuration_changed.emit()
        return
    if result.warnings:
        QMessageBox.warning(
            self, "Custom Guest Warnings", "\n".join(result.warnings)
        )
    # Valid: parse the GRO once to get atom_labels (validation does NOT return them).
    from quickice.structure_generation.gro_parser import parse_gro_file
    _, atom_names, _ = parse_gro_file(self._cg_gro_path)
    self._custom_guest = {
        "guest_type": guest_type,
        "residue_name": result.residue_name,
        "gro_path": str(self._cg_gro_path),
        "itp_path": str(self._cg_itp_path),
        "atom_labels": list(atom_names),       # → CageGuestAssignment.guest_atom_labels
        "atom_count": result.gro_atom_count,    # → CageGuestAssignment.guest_atom_count
    }
    self.cg_validation_label.setText(
        f"✓ Custom guest validated: {result.residue_name} "
        f"({result.gro_atom_count} atoms)"
    )
    self.cg_validation_label.setStyleSheet("color: green;")
    self._rebuild_cage_rows()  # add "Custom: {residue}" to every combo
    self.configuration_changed.emit()
```

### Example 2: Headless test fixture (copy verbatim from test_hydrate_panel.py:50-56)
```python
# Source: tests/test_hydrate_panel.py:50-56
class TestCustomGuestUpload:
    """Custom guest upload panel wiring (Phase 44-02)."""

    @pytest.fixture
    def panel(self, monkeypatch):
        monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
        if not QApplication.instance():
            QApplication(sys.argv)
        return HydratePanel()

    def test_valid_upload_adds_custom_option_to_combos(self, panel, tmp_path):
        # use the bundled valid fixture: quickice/data/custom/etoh.{gro,itp}
        panel._upload_custom_gro()  # ... or set _cg_gro_path directly + call _try_validate_custom_guest
        assert panel._custom_guest is not None
        _select_lattice(panel, "sI")
        # every cage combo now has a "Custom: MOL" item
        for combo in panel._cage_guest_combos.values():
            assert combo.findData(panel._custom_guest["guest_type"]) >= 0
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single `guest_combo` + `occupancy_small`/`occupancy_large` (legacy HydratePanel) | Per-cage-type rows (`_cage_guest_combos`/`_cage_occupancy_spins` dicts keyed by cage_key) | Phase 42-06 | 44-02 extends the per-cage combos, does NOT restore the old single combo |
| Legacy single-guest `HydrateConfig` (guest_type + occupancy fields) | Explicit `cage_guest_assignments` dict of `CageGuestAssignment` | Phase 42-01 | GUI `get_configuration` uses the explicit path → Pitfall 6 applies (see Pitfall #1) |
| Built-in guests only in per-cage combos | Built-ins + one "Custom: {residue}" option (44-02) | This phase | Unblocks GUI-06 custom-per-cage path |

**Deprecated/outdated:**
- The legacy single-guest `HydrateConfig` fields (`guest_type`, `cage_occupancy_small/large`) still work via the `__post_init__` shim (`types.py:637-665`) but the GUI does NOT use them — it builds `cage_guest_assignments` explicitly. Do not "simplify" 44-02 by reverting to the legacy fields; the explicit path is required for mixed occupancy.

## Recommended Design (answers to Q4 and Q5)

### Q4: Single vs multiple custom guests — RECOMMEND SINGLE shared slot
**Evidence:**
- Phase 40/41 e2e tests use ONE custom ethanol guest (`test_e2e_custom_guest_hydrate.py:31` — `_GUEST_TYPE = "etoh_e2e"`, single molecule).
- 42-06 known-limitation: "Phase 42 GUI surface is built-in guests only (ch4/thf) ... Custom-guest-per-cage via the GUI user-facing surface is Phase 44 (GUI-02) scope." (singular custom-guest surface).
- ROADMAP 44-02: "unblocks GUI-06 (custom-per-cage via existing 42-06 row infra; built-in-only limit was the documented 42-06 known limitation)" — the custom guest is added to the existing row infra as ONE option.
- The 42-01 Pitfall 6 duplicate-residue-name rejection (`types.py:711-720`) makes multiple custom guests with the same residue name impossible; multiple custom guests with distinct residue names would require multiple upload panels + distinct slug management — out of scope for v4.7.

**Recommendation:** ONE shared custom-guest slot at the panel level. Upload once → the validated custom guest becomes a "Custom: {residue_name}" option in EVERY per-cage combo. The user picks which cage(s) get it. To satisfy GUI-06's mixed-occupancy custom path, the user assigns the custom guest to one cage and a built-in to another (verified working: mixed 1-custom-1-builtin → `has_custom_assignment=True`, no error).

### Q5: How to add "Custom..." to per-cage combos — shared slot, added on rebuild
**Recommendation:** Add the custom option inside `_rebuild_cage_rows` (`hydrate_panel.py:293-298`), gated on `self._custom_guest is not None`. The option's `itemData` is the custom `guest_type` (a slug); `is_custom_guest` detects it via `guest_type not in GUEST_MOLECULES` (`types.py:466`). Re-upload replaces the slot (overwrites `_custom_guest` + rebuilds rows). Rebuild on upload success AND on lattice change (rows are already rebuilt on lattice change — the custom option re-appears automatically because `_custom_guest` persists across rebuilds).

### Q10: What `guest_type` slug to use
**Convention from e2e/tests:** arbitrary descriptive slugs (`etoh_e2e`, `etoh_mix`, `etoh_custom`, `etoh_test_*` — `test_e2e_custom_guest_hydrate.py:31`, `test_hydrate_config_custom.py:31`). Detection is `guest_type not in GUEST_MOLECULES` (`types.py:466,770`), and `audit_name` enforces `^[A-Za-z0-9-_]+$` (`custom_guest_bridge.py:133`).
**Recommendation:** Derive the slug from the ITP `[ moleculetype ]` name (via `parse_itp_file(itp).molecule_name`, `itp_parser.py:28`) lowercased + sanitized to `[a-z0-9_-]`, falling back to the GRO residue name lowercased if the ITP name is absent/invalid. Append a `_gui` suffix to avoid colliding with test slugs. Validate the result via `validate_custom_guest_files` step 7 (audit_name) — if it fails, show the error (this is one of GUI-05's "unparseable"-class messages). The planner may instead use a fixed `"custom_gui"` slug for simplicity; either works since the slot is single-occupancy.

## Key Decisions for the Planner

| # | Decision | Recommended Answer | Rationale / file:line |
|---|----------|-------------------|----------------------|
| 1 | Single vs multiple custom-guest upload slots? | **Single shared slot** | e2e convention (one ethanol); 42-06 known-limitation language (singular); ROADMAP 44-02 "unblocks GUI-06 ... via existing 42-06 row infra"; Pitfall 6 makes multiple same-name guests impossible. `test_e2e_custom_guest_hydrate.py:31` |
| 2 | Where to insert the upload panel? | New `_create_custom_guest_group()` called in `_setup_ui` between lattice group and cage-assignment group | `hydrate_panel.py:69-75` — panel-level shared slot belongs above per-cage rows |
| 3 | How to populate custom `CageGuestAssignment` metadata? | Call `parse_gro_file(gro)` for `atom_names` (→ `guest_atom_labels`); use `validation.gro_atom_count` (→ `guest_atom_count`) and `validation.residue_name` (→ `guest_residue_name`) | `__post_init__` does NOT auto-populate custom metadata (`types.py:686-710`); `CustomGuestValidation` has no atom-labels field (`custom_guest_bridge.py:62-68`) |
| 4 | How to handle the custom guest in 2 cages (Pitfall 6)? | **Restrict to one cage** (auto-clear other cages' custom selection) OR wrap `get_configuration` in try/except | Verified: explicit path raises `ValueError` (`types.py:711-720`); `main_window.py:742,748` call `get_configuration` without try/except (crash risk). Restricting is simplest. |
| 5 | Reuse `validate_custom_guest_files` or reimplement? | **Reuse — never reimplement** | GUI-05 requires the exact engine messages; `custom_guest_bridge.py:177` is canonical and tested |
| 6 | Where to put the new tests? | Add `TestCustomGuestUpload` class to `tests/test_hydrate_panel.py` (same fixture pattern) | `test_hydrate_panel.py:50-56,133-139` — per-class offscreen fixture; tests assert on `_cage_guest_combos` + `get_configuration` round-trips |

## Existing Code References

| Claim | file:line |
|------|-----------|
| HydratePanel `_setup_ui` left-column layout | `quickice/gui/hydrate_panel.py:52-102` |
| Lattice group creation (insertion anchor — before) | `quickice/gui/hydrate_panel.py:69-70` (`_create_lattice_group`) |
| Cage-assignment group creation (insertion anchor — after) | `quickice/gui/hydrate_panel.py:74-75` (`_create_cage_assignment_group`) |
| `_create_cage_assignment_group` (cage rows container + ff label) | `quickice/gui/hydrate_panel.py:226-254` |
| `_rebuild_cage_rows` (per-cage QComboBox + QDoubleSpinBox; GUEST_MOLECULES loop) | `quickice/gui/hydrate_panel.py:256-314` (combo items at 293-298) |
| `_cage_guest_combos` / `_cage_occupancy_spins` dicts keyed by cage_key | `quickice/gui/hydrate_panel.py:242-243` |
| `get_configuration` builds `cage_guest_assignments` (extend here) | `quickice/gui/hydrate_panel.py:480-507` (per-row construction at 493-499) |
| `validate_custom_guest_files` signature + return | `quickice/structure_generation/custom_guest_bridge.py:177-313` |
| `CustomGuestValidation` dataclass fields | `quickice/structure_generation/custom_guest_bridge.py:48-68` |
| Specific error message: residue name >3 chars | `custom_guest_bridge.py:256-261` |
| Specific error message: wrong comb-rule | `custom_guest_bridge.py:277-281` |
| Specific error message: unparseable GRO (IndexError) | `custom_guest_bridge.py:225-226` |
| Specific error message: invalid guest_type | `custom_guest_bridge.py:300-303` |
| Warning: missing `[ atomtypes ]` | `custom_guest_bridge.py:285-294` |
| `parse_gro_file` returns `(positions, atom_names, cell)` | `quickice/structure_generation/gro_parser.py:90-110` |
| `extract_residue_name_from_gro` | `quickice/structure_generation/gro_parser.py:113-158` |
| `parse_itp_file` returns `ITPMoleculeInfo` (has `molecule_name`) | `quickice/structure_generation/itp_parser.py:16-50` |
| `CageGuestAssignment` dataclass + `is_custom_guest` | `quickice/structure_generation/types.py:429-466` |
| `HydrateConfig.__post_init__` explicit path (Pitfall 6 check) | `quickice/structure_generation/types.py:666-720` (Pitfall 6 at 711-720) |
| `HydrateConfig.__post_init__` legacy shim (no Pitfall 6 check) | `quickice/structure_generation/types.py:637-665` |
| Generator ExitStack dedup by guest_type (handles per-cage custom) | `quickice/structure_generation/hydrate_generator.py:144-183` |
| Export structure-driven custom ITP staging (handles per-cage custom) | `quickice/gui/hydrate_export.py:194-316` |
| HydrateWorker passes config straight to generator (no custom-guest handling needed in GUI) | `quickice/gui/hydrate_worker.py:50-114` |
| `main_window._on_hydrate_config_changed` calls `get_configuration` (NO try/except) | `quickice/gui/main_window.py:740-742` |
| `main_window._on_hydrate_generate_clicked` calls `get_configuration` (NO try/except) | `quickice/gui/main_window.py:745-749` |
| QFileDialog + status-label upload pattern (Tab 3 analog) | `quickice/gui/custom_molecule_panel.py:589-631` |
| Validation feedback label pattern (green/red/orange) | `quickice/gui/custom_molecule_panel.py:172-234,649-693` |
| Warnings dialog pattern (`_show_validation_warnings`) | `quickice/gui/custom_molecule_panel.py:744-758` |
| Headless test fixture (per-class offscreen + singleton QApplication) | `tests/test_hydrate_panel.py:50-56,133-139` |
| e2e custom-guest convention (ONE ethanol, legacy single-guest API) | `tests/test_e2e_custom_guest_hydrate.py:31-62` |
| Per-cage custom `CageGuestAssignment` test convention | `tests/test_hydrate_config_custom.py:224-250` (Pitfall 6 test) |
| Invalid fixture set (combrule1, no_atomtypes, not_a_gro, mismatch) | `quickice/data/custom/test_invalid/README.md` |
| Valid fixture (etoh.gro 9 atoms, etoh.itp) | `quickice/data/custom/etoh.gro`, `etoh.itp` |
| Phase 44 ROADMAP (44-02 is the only remaining plan) | `.planning/ROADMAP.md:139-154` |
| Requirements GUI-02/05 pending, GUI-06 custom gated on 44-02 | `.planning/REQUIREMENTS.md:70,73,74,178,181,182` |

## Open Questions

1. **Pitfall 6 UX: restrict-to-one-cage vs surface-the-error?**
   - What we know: The explicit `cage_guest_assignments` path raises ValueError when the same custom guest is in 2 cages (`types.py:711-720`); `main_window.py:742,748` don't catch it. Mixed 1-custom-1-builtin works.
   - What's unclear: Whether the v4.7 user need requires the same custom guest in multiple cages (the legacy e2e path supports it via the shim, but the GUI explicit path does not).
   - Recommendation: Restrict to one cage (auto-clear other cages) — simplest, zero crash risk, satisfies GUI-06's mixed-occupancy custom path (custom in one cage + built-in in another). If the planner wants permissiveness, wrap `get_configuration` in try/except and surface the specific Pitfall 6 message. **An engine fix to relax Pitfall 6 for same-guest_type-multi-cage is out of scope for 44-02** (it's a 42-01 design decision with a documented rationale: the `_H` hydrate path does not disambiguate residue names).

2. **`guest_type` slug derivation source: ITP moleculetype name vs GRO residue name vs fixed slug?**
   - What we know: e2e tests use arbitrary slugs; `audit_name` requires `^[A-Za-z0-9-_]+$`; `is_custom_guest` detects via `not in GUEST_MOLECULES`.
   - What's unclear: Whether the ITP moleculetype name is always present/clean (some ITPs may have long names with spaces).
   - Recommendation: Derive from ITP moleculetype name slugified + `_gui` suffix; fall back to GRO residue name lowercased; validate via `audit_name` (already in `validate_custom_guest_files` step 7). The planner may simplify to a fixed `"custom_gui"` slug since the slot is single-occupancy.

## Sources

### Primary (HIGH confidence — source code read + execution-verified)
- `quickice/gui/hydrate_panel.py` — full read (547 lines); current post-42-06 structure
- `quickice/structure_generation/custom_guest_bridge.py` — full read (394 lines); `validate_custom_guest_files` + `CustomGuestValidation`
- `quickice/structure_generation/types.py:429-780` — `CageGuestAssignment`, `HydrateConfig`, `__post_init__` (both shim + explicit paths)
- `quickice/structure_generation/hydrate_generator.py:103-232` — generator ExitStack custom branch
- `quickice/gui/hydrate_export.py:140-316` — export structure-driven custom ITP staging
- `quickice/gui/hydrate_worker.py` — full read (114 lines); config passthrough (no custom-guest handling needed)
- `quickice/gui/main_window.py:735-822` — hydrate generate flow (get_configuration call sites, no try/except)
- `quickice/gui/custom_molecule_panel.py:150-234,560-758` — QFileDialog + validation-label patterns (Tab 3 analog)
- `tests/test_hydrate_panel.py` — full read (175 lines); headless fixture pattern
- `tests/test_e2e_custom_guest_hydrate.py` — full read (274 lines); e2e convention (one ethanol)
- `tests/test_hydrate_config_custom.py` — full read (256 lines); Pitfall 6 test
- `quickice/structure_generation/gro_parser.py:90-158` — `parse_gro_file` + `extract_residue_name_from_gro`
- `quickice/structure_generation/itp_parser.py:16-50` — `ITPMoleculeInfo` + `parse_itp_file`
- `.planning/ROADMAP.md:139-154` — Phase 44 scope (44-02 only remaining)
- `.planning/REQUIREMENTS.md:69-74,177-182` — GUI-02/05 pending, GUI-06 custom gated on 44-02

### Execution-verified (HIGH confidence)
- `validate_custom_guest_files` on valid `etoh.gro/itp` → `is_valid=True`, `gro_atom_count=9`, `residue_name='MOL'`, `comb_rule=None`, no warnings
- `validate_custom_guest_files` on `etoh_combrule1.itp` → error "ITP comb-rule must be 2 ... got comb-rule=1"
- `validate_custom_guest_files` on `etoh_no_atomtypes.itp` → `is_valid=True`, warning "No [ atomtypes ] in ITP..."
- `validate_custom_guest_files` on `not_a_gro.txt` → error "Failed to parse GRO file ...: list index out of range"
- `parse_gro_file('etoh.gro')` → `atom_names=['H','C','H','H','C','H','H','O','H']`, `len=9` (= guest_atom_count for single-molecule GRO)
- Pitfall 6 probe: explicit `cage_guest_assignments` with same custom guest in 2 cages → `ValueError: Duplicate guest_residue_name 'MOL' ...`; mixed 1-custom-1-builtin → OK (`has_custom_assignment=True`); legacy single-custom shim → OK

### Secondary (MEDIUM confidence)
- PySide6 widget API (QFileDialog, QLabel, QGroupBox) — standard, consistent with existing `quickice/gui/` usage; not separately fetched (training knowledge + in-repo usage is sufficient and verified against the live codebase)

### Tertiary (LOW confidence)
- None. All findings are source- or execution-verified.

## Metadata

**Confidence breakdown:**
- Standard stack (PySide6 widgets, QFileDialog pattern): HIGH — verified against `custom_molecule_panel.py` + `export.py` in-repo usage
- Architecture (insertion point, get_configuration extension): HIGH — verified by reading `hydrate_panel.py` + executing `get_configuration` round-trips
- Validation integration (`validate_custom_guest_files` messages): HIGH — execution-verified on valid + 4 invalid fixtures
- Pitfalls (Pitfall 6 asymmetry, no-auto-populate, IndexError): HIGH — execution-verified
- Engine-no-change hypothesis: HIGH — generator + export paths read and confirmed to handle explicit custom `cage_guest_assignments`

**Research date:** 2026-07-07
**Valid until:** 2026-08-06 (30 days; stable — no external libs changing, all findings are internal-source-verified)
