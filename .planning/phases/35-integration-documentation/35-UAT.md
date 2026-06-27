---
status: complete
phase: 35-integration-documentation
source: [35-01-SUMMARY.md, 35-02-SUMMARY.md, 35-03-SUMMARY.md, 35-04-SUMMARY.md, 35-05-SUMMARY.md, 35-06-SUMMARY.md, 35-07-SUMMARY.md]
started: 2026-06-26T15:37:54Z
updated: 2026-06-26T15:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Ctrl+S Unified Export Shortcut
expected: In the running GUI, pressing Ctrl+S while any tab is active triggers GROMACS export for that tab's content. A file save dialog appears appropriate to the active tab (e.g., ice candidate, hydrate, interface, custom molecule, solute, or ion export).
result: pass
method: "GUI verified — user confirmed Ctrl+S triggers export for active tab"

### 2. Ctrl+H Hydrate Export Shortcut
expected: Pressing Ctrl+H in the GUI triggers hydrate GROMACS export (same as clicking the hydrate export button). This replaces the old Ctrl+E shortcut.
result: pass
method: "GUI verified — user confirmed Ctrl+H triggers hydrate export"

### 3. Export As... Submenu
expected: The File menu has an "Export As..." submenu listing all tab-specific exports (Ice, Hydrate, Interface, Custom Molecule, Solute, Ion). Clicking an entry triggers the corresponding export.
result: pass
method: "CLI grep — export_as_menu found at L378 with per-tab export actions"

### 4. Custom Molecule Panel Tooltips
expected: In the Custom Molecule tab (Tab 3), hovering over the GRO upload button, ITP upload button, and placement mode dropdown shows helpful tooltips with format guidance, required sections, and mode descriptions.
result: pass
method: "CLI grep — 8 setToolTip calls in custom_molecule_panel.py (GRO L156, ITP L182, placement L245)"

### 5. Solute Panel Tooltips
expected: In the Solute Insertion tab (Tab 4), hovering over the concentration input shows the molecule count formula (N = C_M x V_L x N_A) with an example. Hovering over the solute type dropdown shows THF/CH4 descriptions.
result: pass
method: "CLI grep — 11 setToolTip calls in solute_panel.py (source L89, concentration L165, type L206)"

### 6. Help Dialog Tab Numbering
expected: Opening the help dialog (Help > Quick Reference) shows all 6 tabs numbered Tab 0 through Tab 5: Tab 0 — Ice Generation, Tab 1 — Hydrate Config, Tab 2 — Interface Construction, Tab 3 — Custom Molecule, Tab 4 — Solute Insertion, Tab 5 — Ion Insertion.
result: pass
method: "CLI grep — help_dialog.py Tab 0-5 all correct (L88,95,101,109,118,126)"

### 7. Help Dialog Keyboard Shortcuts
expected: The help dialog lists Ctrl+S as "Export current tab for GROMACS", Ctrl+H as "Export hydrate for GROMACS", Ctrl+L for solutes, and Ctrl+M for custom molecules.
result: pass
method: "CLI grep — Ctrl+S L68, Ctrl+H L73, Ctrl+L L75, Ctrl+M L76 all present"

### 8. README v4.5 Content
expected: README.md mentions Solute Insertion and Custom Molecule Upload as v4.5 features with correct tab numbers (Tab 3, Tab 4). The README documents the unified Ctrl+S export shortcut. Ion Insertion is listed as Tab 5 (not Tab 4).
result: pass
method: "CLI grep — Tab 3=Custom Molecule, Tab 4=Solute, Tab 5=Ion, Ctrl+S present"

### 9. GUI Guide Tab 3/4 Workflows
expected: docs/gui-guide.md includes a Custom Molecule Upload (Tab 3) section with an 8-step workflow and a Solute Insertion (Tab 4) section with a 7-step workflow. Tab numbering is consistent (Tab 0-5 throughout).
result: pass
method: "CLI grep — Tab 3=Custom Molecule, Tab 4=Solute, Tab 5=Ion all correct"

### 10. GRO/ITP Creation Guide
expected: docs/gro-itp-guide.md exists and includes GRO/ITP format specifications, at least three creation methods (GROMACS, ACPYPE, CHARMM-GUI), and practical molecule examples (ethanol, aspirin, polymer).
result: pass
method: "CLI check — file exists (26KB), 31 keyword hits for GROMACS/ACPYPE/CHARMM-GUI/ethanol/aspirin"

### 11. Screenshots in Documentation
expected: docs/gui-guide.md references screenshots that exist in docs/images/ — specifically custom-molecule-panel.png and solute-panel.png are present. No image references point to missing files. No "screenshot pending" or "TODO" notes remain in the guide.
result: pass
method: "CLI check — both PNGs exist, no tabX- prefixes, no pending/TODO notes in gui-guide.md"

### 12. Concentration/Count Input Documentation
expected: The GUI guide documents both the molecule count and concentration input modes for Random Placement in the Custom Molecule tab, including the formula N = C_M x V_L x N_A.
result: pass
method: "CLI grep — 'By Concentration' mode at L503, formula N = C_M × V_L × N_A at L507, real-time preview at L511"

## Summary

total: 12
passed: 12
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
