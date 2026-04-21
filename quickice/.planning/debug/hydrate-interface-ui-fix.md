---
status: resolved
trigger: "Fix hydrate-to-interface panel - simplify UI and fix piece mode error"
created: 2026-04-21T00:00:00
updated: 2026-04-21T00:00:00
---

## Resolution

### Root Cause Found

**Problem 1 (UI duplication):** interface_panel.py had a duplicate `_hydrate_group` with lattice/guest/supercell controls that should NOT exist there - those controls are already in hydrate_panel.py (Tab 2).

**Problem 2 (piece mode error):** piece.py hardcoded `atoms_per_molecule=3` for ice tiling, but hydrate uses TIP4P with 4 atoms per molecule (OW, HW1, HW2, MW).

### Fixes Applied

**1. interface_panel.py:**
- Removed duplicate `_hydrate_group` (lines 277-322)
- Removed unused imports (`HYDRATE_LATTICES`, `GUEST_MOLECULES`)
- Updated `_on_source_changed()` to remove reference to deleted group
- Removed unused `get_hydrate_configuration()` method

**2. modes/piece.py:**
- Added `detect_atoms_per_molecule()` function to detect 3 (ice) or 4 (hydrate/TIP4P) from atom names
- Updated `assemble_piece()` to use dynamic detection instead of hardcoded 3
- Updated overlap detection to use dynamic stride instead of hardcoded `::3`

### Verification

```bash
$ python -c "from quickice.structure_generation.modes.piece import detect_atoms_per_molecule
$ detect_atoms_per_molecule(['O', 'H', 'H'])  # ice
3
$ detect_atoms_per_molecule(['OW', 'HW1', 'HW2', 'MW'])  # hydrate
4"

$ pytest tests/ -v -k "piece" --tb=short
13 passed, 294 deselected in 9.12s
```

### Files Changed

- quickice/gui/interface_panel.py
- quickice/structure_generation/modes/piece.py