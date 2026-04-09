# Phase 20: Export - Research

**Researched:** 2026-04-09
**Domain:** GROMACS file export for ice/water interface structures
**Confidence:** HIGH

## Summary

This phase implements GROMACS export for Tab 2's interface structures (ice + water combined). The core challenge is normalizing ice molecules from 3-atom format (O, H, H) to 4-atom TIP4P-ICE format (OW, HW1, HW2, MW) at export time, while water molecules already come in 4-atom format. The topology must use a single SOL molecule type for both phases with a combined molecule count. The implementation should follow Tab 1's existing GROMACSExporter pattern closely, creating a new `InterfaceGROMACSExporter` class that handles the InterfaceStructure data model.

**Primary recommendation:** Create an `InterfaceGROMACSExporter` class following the existing `GROMACSExporter` pattern, with new `write_interface_gro_file` and `write_interface_top_file` functions in `gromacs_writer.py` that accept `InterfaceStructure` and handle ice 3→4 atom normalization inline. Reuse the same bundled `tip4p-ice.itp` file. Add a separate menu action with `Ctrl+I` shortcut.

## Standard Stack

The established libraries and tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.10+ | File I/O, string formatting | Required for .gro/.top generation (no new deps) |
| PySide6 | 6.x | QFileDialog, QAction, QMenu | Already in project for GUI |

### Existing (Reuse)
| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| gromacs_writer.py | quickice/output/ | .gro/.top file generation | Already handles Tab 1 export |
| tip4p-ice.itp | quickice/data/ | TIP4P-ICE force field | Already bundled, same for both phases |
| GROMACSExporter | quickice/gui/export.py | Tab 1 export handler | Pattern to follow for Tab 2 |

### No New Dependencies

```bash
# No pip install needed — all dependencies already in project
```

## Architecture Patterns

### Recommended Project Structure
```
quickice/
├── output/
│   └── gromacs_writer.py      # ADD: write_interface_gro_file, write_interface_top_file
├── gui/
│   ├── export.py              # ADD: InterfaceGROMACSExporter class
│   ├── main_window.py         # ADD: menu action + shortcut + handler
│   └── help_dialog.py         # UPDATE: add Ctrl+I shortcut to shortcuts list
└── data/
    └── tip4p-ice.itp          # REUSE: same .itp for both tabs
```

### Pattern 1: InterfaceGROMACSExporter Class
**What:** Export handler for interface structures, following GROMACSExporter pattern
**When to use:** When user selects "Export Interface for GROMACS" from File menu
**Example:**
```python
# Source: Following GROMACSExporter pattern from export.py
class InterfaceGROMACSExporter:
    """Handle GROMACS file export for interface structures (.gro, .top, .itp).
    
    Per CONTEXT.md:
    - Same SOL molecule type for both ice and water phases
    - Ice molecules normalized from 3-atom to 4-atom TIP4P-ICE format at export time
    - Continuous residue numbering: ice 1..N_ice, water N_ice+1..N_ice+N_water
    - Single combined SOL count in [molecules] section
    """
    
    def __init__(self, parent_widget):
        self.parent = parent_widget
    
    def export_interface_gromacs(self, interface_structure) -> bool:
        """Export interface structure to GROMACS format.
        
        Args:
            interface_structure: InterfaceStructure with combined ice + water data
            
        Returns:
            True if export succeeded
        """
        # Show save dialog with interface-specific default name
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self.parent,
            "Export Interface for GROMACS",
            "interface_slab.gro",  # Default name includes "interface"
            "GRO Files (*.gro);;All Files (*)",
            "GRO Files (*.gro)"
        )
        
        if not filepath:
            return False
        
        path = Path(filepath)
        if path.suffix.lower() != '.gro':
            path = path.with_suffix('.gro')
        
        top_path = path.with_name(path.stem + '.top')
        itp_path = path.with_name(path.stem + '.itp')
        
        try:
            write_interface_gro_file(interface_structure, str(path))
            write_interface_top_file(interface_structure, str(top_path))
            # Copy same .itp as Tab 1 (identical TIP4P-ICE topology)
            shutil.copy(get_tip4p_itp_path(), itp_path)
            return True
        except Exception as e:
            QMessageBox.critical(self.parent, "Export Error", f"Failed: {e}")
            return False
```

### Pattern 2: Ice 3→4 Atom Normalization (MW Virtual Site Computation)
**What:** Convert 3-atom ice molecules (O, H, H) to 4-atom TIP4P-ICE format (OW, HW1, HW2, MW) by computing MW position
**When to use:** At export time, for every ice molecule in the InterfaceStructure
**Example:**
```python
# Source: TIP4P-ICE model - Abascal et al. 2005
# MW = O + α * (H1 + H2) / 2  where α = 0.13458335 * 2 = 0.2691667
# Wait — let's be precise. The virtual_sites3 directive says:
#   4  1  2  3  1  0.13458335  0.13458335
# This means: MW = O + a*(H1-O) + b*(H2-O) where a=b=0.13458335
# So: MW = O + 0.13458335*(H1-O) + 0.13458335*(H2-O)
#       = O*(1 - a - b) + a*H1 + b*H2
#       = O*(1 - 0.2691667) + 0.13458335*H1 + 0.13458335*H2

TIP4P_ICE_ALPHA = 0.13458335

def compute_mw_position(o_pos, h1_pos, h2_pos):
    """Compute TIP4P-ICE MW virtual site position.
    
    MW = O + α*(H1-O) + α*(H2-O)  where α=0.13458335
    
    This matches the [ virtual_sites3 ] directive in tip4p-ice.itp:
      4  1  2  3  1  0.13458335  0.13458335
    
    Args:
        o_pos: Oxygen position array (3,) in nm
        h1_pos: Hydrogen 1 position array (3,) in nm
        h2_pos: Hydrogen 2 position array (3,) in nm
    
    Returns:
        MW position array (3,) in nm
    """
    import numpy as np
    alpha = TIP4P_ICE_ALPHA
    return o_pos + alpha * (h1_pos - o_pos) + alpha * (h2_pos - o_pos)
```

### Pattern 3: Interface .gro File Writer
**What:** Write combined ice+water coordinates to .gro with all molecules as 4-atom TIP4P-ICE SOL
**When to use:** Exporting interface structure
**Example:**
```python
# Source: GROMACS 2026.1 manual - gro format specification
# Adapted from existing write_gro_file() in gromacs_writer.py

def write_interface_gro_file(iface: InterfaceStructure, filepath: str) -> None:
    """Write interface structure to GROMACS .gro format.
    
    All molecules output as 4-atom TIP4P-ICE (OW, HW1, HW2, MW).
    Ice molecules (3-atom internally) are normalized at export time
    by computing MW virtual site positions.
    
    Args:
        iface: InterfaceStructure with combined positions
        filepath: Output .gro file path
    """
    total_mol = iface.ice_nmolecules + iface.water_nmolecules
    n_atoms = total_mol * 4  # All molecules are 4-atom TIP4P-ICE
    
    with open(filepath, 'w') as f:
        # Title line
        f.write(f"Ice/water interface ({iface.mode}) exported by QuickIce\n")
        
        # Number of atoms
        f.write(f"{n_atoms:5d}\n")
        
        atom_num = 0
        
        # === Ice molecules: normalize 3-atom → 4-atom ===
        for mol_idx in range(iface.ice_nmolecules):
            base_idx = mol_idx * 3  # 3 atoms per ice molecule (O, H, H)
            o_pos = iface.positions[base_idx]
            h1_pos = iface.positions[base_idx + 1]
            h2_pos = iface.positions[base_idx + 2]
            mw_pos = compute_mw_position(o_pos, h1_pos, h2_pos)
            
            res_num = mol_idx + 1  # Continuous numbering: 1..N_ice
            
            atom_num += 1
            f.write(f"{res_num:5d}SOL  "
                    f"   OW{atom_num:5d}"
                    f"{o_pos[0]:8.3f}{o_pos[1]:8.3f}{o_pos[2]:8.3f}\n")
            
            atom_num += 1
            f.write(f"{res_num:5d}SOL  "
                    f"  HW1{atom_num:5d}"
                    f"{h1_pos[0]:8.3f}{h1_pos[1]:8.3f}{h1_pos[2]:8.3f}\n")
            
            atom_num += 1
            f.write(f"{res_num:5d}SOL  "
                    f"  HW2{atom_num:5d}"
                    f"{h2_pos[0]:8.3f}{h2_pos[1]:8.3f}{h2_pos[2]:8.3f}\n")
            
            atom_num += 1
            f.write(f"{res_num:5d}SOL  "
                    f"   MW{atom_num:5d}"
                    f"{mw_pos[0]:8.3f}{mw_pos[1]:8.3f}{mw_pos[2]:8.3f}\n")
        
        # === Water molecules: already 4-atom (OW, HW1, HW2, MW) ===
        for mol_idx in range(iface.water_nmolecules):
            base_idx = iface.ice_atom_count + mol_idx * 4  # Water starts after ice atoms
            res_num = iface.ice_nmolecules + mol_idx + 1  # Continue numbering
            
            for sub_idx, atom_name in enumerate(["OW", "HW1", "HW2", "MW"]):
                pos = iface.positions[base_idx + sub_idx]
                atom_num += 1
                f.write(f"{res_num:5d}SOL  "
                        f"{atom_name:>4s}{atom_num:5d}"
                        f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")
        
        # Box vectors (same triclinic format as Tab 1)
        cell = iface.cell
        f.write(f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}"
                f"{cell[0,1]:10.5f}{cell[0,2]:10.5f}{cell[1,0]:10.5f}"
                f"{cell[1,2]:10.5f}{cell[2,0]:10.5f}{cell[2,1]:10.5f}\n")
```

### Pattern 4: Interface .top File Writer
**What:** Write topology with single SOL molecule type and combined molecule count
**When to use:** Exporting interface structure
**Example:**
```python
# Source: Following write_top_file() pattern from gromacs_writer.py
# Key difference: single combined SOL count (no phase distinction)

def write_interface_top_file(iface: InterfaceStructure, filepath: str) -> None:
    """Write GROMACS topology file for interface structure.
    
    Same SOL molecule type for both ice and water phases.
    Single combined count in [molecules] section.
    
    Args:
        iface: InterfaceStructure
        filepath: Output .top file path
    """
    total_mol = iface.ice_nmolecules + iface.water_nmolecules
    
    with open(filepath, 'w') as f:
        f.write("; Generated by QuickIce\n")
        f.write("; TIP4P-ICE water model\n")
        f.write("; Ice/water interface structure\n\n")
        
        # [ defaults ] — same as Tab 1
        f.write("; Defaults compatible with the Amber forcefield\n")
        f.write("[ defaults ]\n")
        f.write("; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ\n")
        f.write("1               2               yes             0.5     0.8333\n\n")
        
        # [ atomtypes ] — same as Tab 1
        f.write("[ atomtypes ]\n")
        f.write("; name  bond_type  atomic_number  mass  charge  ptype  V              W\n")
        f.write("OW_ice      OW_ice     8           15.9994  0.0     A      0.31668e-3    0.88216e-6\n")
        f.write("HW_ice      HW_ice     1            1.0080  0.0     A      0.0          0.0\n")
        f.write("MW          MW          0            0.0000  0.0     V      0.0          0.0\n\n")
        
        # [ moleculetype ] — same SOL, same as Tab 1
        f.write("[ moleculetype ]\n")
        f.write("; Name        nrexcl\n")
        f.write("SOL          2\n\n")
        
        # [ atoms ] — same as Tab 1 (TIP4P-ICE)
        f.write("[ atoms ]\n")
        f.write(";   nr  type  resi  res  atom  cgnr     charge    mass\n")
        f.write("   1   OW_ice    1  SOL    OW     1       0.0  16.00000\n")
        f.write("   2   HW_ice    1  SOL   HW1     1     0.5897   1.00800\n")
        f.write("   3   HW_ice    1  SOL   HW2     1     0.5897   1.00800\n")
        f.write("   4   MW        1  SOL    MW     1    -1.1794   0.00000\n\n")
        
        # [ settles ] — same as Tab 1
        f.write("[ settles ]\n")
        f.write("; i  funct  doh     dhh\n")
        f.write("  1    1    0.09572  0.15139\n\n")
        
        # [ virtual_sites3 ] — same as Tab 1
        f.write("[ virtual_sites3 ]\n")
        f.write("; Vsite from                    funct  a          b\n")
        f.write("   4     1       2       3       1      0.13458335 0.13458335\n\n")
        
        # [ exclusions ] — same as Tab 1
        f.write("[ exclusions ]\n")
        f.write("  1  2  3  4\n")
        f.write("  2  1  3  4\n")
        f.write("  3  1  2  4\n")
        f.write("  4  1  2  3\n\n")
        
        # [ system ] — interface-specific title
        f.write("[ system ]\n")
        f.write("; Name\n")
        f.write(f"Ice/water interface ({iface.mode}) exported by QuickIce\n\n")
        
        # [ molecules ] — SINGLE combined SOL count
        f.write("[ molecules ]\n")
        f.write("; Compound    #mols\n")
        f.write(f"SOL          {total_mol}\n")
```

### Pattern 5: Menu Action and Shortcut Integration
**What:** Add separate File menu action for Tab 2 export with distinct shortcut
**When to use:** In _create_menu_bar() method
**Example:**
```python
# Source: Following existing menu pattern in main_window.py

# In _create_menu_bar(), after existing "Export for GROMACS..." action:
file_menu.addSeparator()

# Export Interface for GROMACS (Tab 2) — separate action, separate shortcut
export_interface_gromacs_action = file_menu.addAction("Export Interface for GROMACS...")
export_interface_gromacs_action.setShortcut("Ctrl+I")  # I for Interface
export_interface_gromacs_action.triggered.connect(self._on_export_interface_gromacs)

# Handler:
def _on_export_interface_gromacs(self):
    """Handle Export Interface for GROMACS menu action."""
    if not self._current_interface_result:
        QMessageBox.warning(self, "No Interface", "Generate an interface structure first.")
        return
    
    success = self._interface_gromacs_exporter.export_interface_gromacs(
        self._current_interface_result
    )
    
    if success:
        iface = self._current_interface_result
        QMessageBox.information(
            self,
            "Export Complete",
            f"GROMACS files exported successfully.\n\n"
            f"Water model: TIP4P-ICE\n"
            f"(Abascal et al. 2005, DOI: 10.1063/1.1931662)\n\n"
            f"Ice molecules: {iface.ice_nmolecules}\n"
            f"Water molecules: {iface.water_nmolecules}\n"
            f"Total: {iface.ice_nmolecules + iface.water_nmolecules}\n\n"
            f"Files generated:\n"
            f"• interface_{iface.mode}.gro\n"
            f"• interface_{iface.mode}.top\n"
            f"• interface_{iface.mode}.itp"
        )
```

### Anti-Patterns to Avoid
- **Separate molecule types for ice/water:** CONTEXT explicitly overrides EXP-02 — no chain A/B, no separate molecule types. Both are SOL.
- **Separate SOL counts in [molecules]:** Must be a single combined number, not "SOL_ice N_ice" + "SOL_water N_water"
- **Adding chain identifiers in .gro:** No chain column in GROMACS .gro format, and CONTEXT says no chain distinction
- **Normalizing atom counts in InterfaceStructure:** The InterfaceStructure stores raw 3-atom ice + 4-atom water; normalization is ONLY at export time
- **Sharing Ctrl+G shortcut:** CONTEXT requires separate shortcut for Tab 2 export

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MW virtual site position | Custom formula from scratch | TIP4P-ICE formula: MW = O + α*(H1-O) + α*(H2-O) | Must match tip4p-ice.itp virtual_sites3 parameters exactly |
| .gro file format | Space-separated values | Fixed-width GROMACS format (5d, 5s, 5s, 5d, 8.3f) | GROMACS parsers expect exact column positions |
| .top file structure | Custom topology sections | Copy from Tab 1's write_top_file + modify [system] and [molecules] | Identical TIP4P-ICE topology for both phases |
| .itp file | Generate programmatically | Copy bundled tip4p-ice.itp | Already validated force field file |
| File save dialog | Custom dialog | QFileDialog.getSaveFileName | Qt standard, handles overwrite checking |

**Key insight:** The .top file structure is identical to Tab 1's except for the [system] name and [molecules] count. The .gro file differs only in how atoms are iterated (3-atom ice segments + 4-atom water segments → all output as 4-atom). The .itp file is identical. This is primarily a "write the loop differently" problem, not a "new format" problem.

## Common Pitfalls

### Pitfall 1: Wrong MW Position Formula
**What goes wrong:** MW virtual site placed incorrectly, simulation energies wrong
**Why it happens:** Confusion between different TIP4P variants (TIP4P, TIP4P-Ew, TIP4P-ICE have different α values)
**How to avoid:** Use α=0.13458335 specifically for TIP4P-ICE, matching the tip4p-ice.itp `virtual_sites3` directive: `4  1  2  3  1  0.13458335  0.13458335`
**Warning signs:** gmx grompp warnings about virtual site positions; O-MW distances ≠ expected ~0.01577 nm

### Pitfall 2: Off-by-One in Atom Indexing (Ice 3-atom vs Water 4-atom)
**What goes wrong:** Atom positions shifted, wrong molecule boundaries
**Why it happens:** Ice molecules use 3 atoms per molecule internally (O, H, H), water uses 4 (OW, HW1, HW2, MW). Mixing up strides causes position misalignment.
**How to avoid:** For ice molecules iterate `base_idx = mol_idx * 3`, for water iterate `base_idx = iface.ice_atom_count + mol_idx * 4`
**Warning signs:** Visual inspection shows displaced atoms; unrealistic bond lengths

### Pitfall 3: Splitting Molecule Counts in [molecules] Section
**What goes wrong:** GROMACS can't find two different molecule types
**Why it happens:** Thinking ice and water need separate entries (EXP-02 before override)
**How to avoid:** Single `SOL` entry with combined count: `SOL  {ice_nmolecules + water_nmolecules}`
**Warning signs:** gmx grompp error about unknown molecule type

### Pitfall 4: Residue Numbering Not Continuous
**What goes wrong:** GROMACS expects continuous residue numbering within a molecule type
**Why it happens:** Resetting residue counter between ice and water phases
**How to avoid:** Ice molecules get residues 1..N_ice, water molecules get N_ice+1..N_ice+N_water
**Warning signs:** gmx check reports discontinuous residues

### Pitfall 5: Forgetting .gro Title Line Distinguishes the File
**What goes wrong:** User can't tell Tab 1 export from Tab 2 export
**Why it happens:** Using same title line format for both
**How to avoid:** Tab 2 title includes "interface" and mode (e.g., "Ice/water interface (slab) exported by QuickIce")
**Warning signs:** User confusion about which file is which

### Pitfall 6: Shortcut Conflict with Existing Actions
**What goes wrong:** Two actions fire from same shortcut
**Why it happens:** Reusing Ctrl+G for both Tab 1 and Tab 2 export
**How to avoid:** Use Ctrl+I (I for Interface) — verified no conflict with existing shortcuts (Ctrl+S, Ctrl+Shift+S, Ctrl+D, Ctrl+Alt+S, Ctrl+G are all taken)
**Warning signs:** Both export dialogs open simultaneously

### Pitfall 7: Export When No Interface Generated
**What goes wrong:** AttributeError or NoneType crash
**Why it happens:** `_current_interface_result` is None before any Tab 2 generation
**How to avoid:** Guard check at start of handler, show warning dialog
**Warning signs:** Crash when clicking export before generating interface

## Code Examples

Verified patterns from existing codebase and GROMACS documentation:

### Existing Tab 1 Export Flow (reference implementation)
```python
# Source: quickice/gui/export.py lines 296-373
# Tab 1 GROMACSExporter flow:
# 1. Show QFileDialog with default name
# 2. Write .gro using write_gro_file(candidate, path)
# 3. Write .top using write_top_file(candidate, path)
# 4. Copy .itp using shutil.copy(get_tip4p_itp_path(), itp_path)
# 5. Show success message with TIP4P-ICE info

# Key differences for Tab 2:
# - Accept InterfaceStructure instead of Candidate
# - Ice 3→4 atom normalization in .gro writer
# - Combined SOL count in .top writer
# - Different default filename ("interface_*" instead of "{phase}_{T}K_{P}MPa_c{rank}")
# - Different dialog title
```

### InterfaceStructure Data Model
```python
# Source: quickice/structure_generation/types.py lines 112-145
@dataclass
class InterfaceStructure:
    """Result of interface structure generation.
    
    Attributes:
        positions: (N_atoms, 3) combined ice + water atom positions in nm.
            Ice atoms come FIRST, then water atoms.
        atom_names: Atom names for all atoms (ice names then water names)
            Ice: ["O", "H", "H", "O", "H", "H", ...]  (3 per molecule)
            Water: ["OW", "HW1", "HW2", "MW", ...]     (4 per molecule)
        cell: (3, 3) box cell vectors in nm
        ice_atom_count: Number of ice atoms (ALL atoms in ice section)
        water_atom_count: Number of water atoms (ALL atoms in water section)
        ice_nmolecules: Number of ice molecules
        water_nmolecules: Number of water molecules
        mode: Interface mode used ("slab", "pocket", or "piece")
        report: Generation report string
    """
```

### Accessing Interface Structure from MainWindow
```python
# Source: quickice/gui/main_window.py lines 63, 461
# _current_interface_result is set in _on_interface_generation_complete():
self._current_interface_result = result

# The result has all needed fields:
iface = self._current_interface_result
iface.positions          # np.ndarray (N, 3) — combined ice+water
iface.atom_names        # list[str] — combined names
iface.cell              # np.ndarray (3, 3) — box vectors
iface.ice_atom_count    # int — boundary index in positions array
iface.ice_nmolecules    # int
iface.water_nmolecules  # int
iface.mode              # str — "slab", "pocket", or "piece"
```

### Atom Name Mapping for Export
```python
# Source: verified from InterfaceStructure definition and generation code
# Ice atoms (3 per molecule): O, H, H → renamed to OW, HW1, HW2 at export
# Water atoms (4 per molecule): OW, HW1, HW2, MW → kept as-is at export
# MW computed for ice molecules using TIP4P-ICE formula

# The normalization mapping:
ICE_ATOM_MAP = {
    0: "OW",   # O → OW
    1: "HW1",  # H → HW1  
    2: "HW2",  # H → HW2
}
# MW computed from O, H1, H2 positions
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tab 1 only export | Tab 1 + Tab 2 export | Phase 20 | Interface structures can be used in GROMACS |
| Separate ice/water molecule types | Single SOL for both | CONTEXT override | Simpler topology, standard GROMACS practice |
| No atom normalization | 3→4 atom normalization at export | Phase 20 | Ice molecules get MW virtual sites at export |

**Deprecated/outdated:**
- EXP-02 original requirement (chain A/B distinction): OVERRIDDEN by CONTEXT — no chain distinction
- Any approach that normalizes InterfaceStructure's internal representation: normalization is ONLY at export time

## Open Questions

1. **Exact default filename format**
   - What we know: CONTEXT says OpenCode's discretion, should identify as interface output
   - What's unclear: Exact format string
   - Recommendation: Use `interface_{mode}.gro` (e.g., `interface_slab.gro`, `interface_pocket.gro`). Simple, descriptive, distinguishes from Tab 1's `{phase}_{T}K_{P}MPa_c{rank}.gro`.

2. **Dialog title text**
   - What we know: Should distinguish from Tab 1's "Export for GROMACS"
   - What's unclear: Exact wording
   - Recommendation: Use "Export Interface for GROMACS" — adds "Interface" to clearly distinguish.

3. **.gro title line content**
   - What we know: Should include enough info to identify the file
   - What's unclear: Exact format
   - Recommendation: `f"Ice/water interface ({iface.mode}) exported by QuickIce"` — includes mode and clearly identifies as interface.

4. **Reuse vs. new code for normalization**
   - What we know: Tab 1 already handles 4-point TIP4P-ICE format in write_gro_file()
   - What's unclear: Whether to refactor shared code or write new functions
   - Recommendation: Write new `write_interface_gro_file()` and `write_interface_top_file()` functions that accept `InterfaceStructure`. The iteration logic is fundamentally different (3-atom ice stride + 4-atom water stride vs. uniform 4-atom stride), so sharing code would add complexity. The MW computation is a simple 3-line function that can be shared if desired, but it's small enough to define inline.

5. **Ctrl+I shortcut availability**
   - What we know: Verified no conflict with existing shortcuts (Ctrl+S, Ctrl+Shift+S, Ctrl+D, Ctrl+Alt+S, Ctrl+G, Enter, Escape)
   - What's unclear: Whether Qt/OS reserves Ctrl+I
   - Recommendation: Use Ctrl+I. It's not reserved by Qt and not used by any other action in the app. "I" is mnemonic for "Interface" which distinguishes from Ctrl+G (GROMACS).

## Sources

### Primary (HIGH confidence)
- GROMACS 2026.1 official manual - .gro file format: https://manual.gromacs.org/current/reference-manual/file-formats.html
- quickice/output/gromacs_writer.py — existing Tab 1 export implementation (verified line by line)
- quickice/structure_generation/types.py — InterfaceStructure dataclass definition (verified)
- quickice/data/tip4p-ice.itp — bundled TIP4P-ICE force field with virtual_sites3 parameters (verified α=0.13458335)
- quickice/gui/export.py — GROMACSExporter class pattern (verified)

### Secondary (MEDIUM confidence)
- quickice/structure_generation/modes/piece.py, pocket.py, slab.py — ice_atom_count, water_atom_count assignment logic (verified 3-atom ice stride)
- quickice/gui/vtk_utils.py — interface_to_vtk_molecules() demonstrates 3-atom ice / 4-atom water stride handling (verified pattern)
- quickice/gui/main_window.py — existing shortcut assignments verified (Ctrl+S, Ctrl+Shift+S, Ctrl+D, Ctrl+Alt+S, Ctrl+G)

### Tertiary (LOW confidence)
- None required — all findings verified from codebase or official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, follows existing Tab 1 patterns
- Architecture: HIGH — new functions follow exact same pattern as existing gromacs_writer.py
- Pitfalls: HIGH — MW formula verified against tip4p-ice.itp, atom stride verified against types.py and generation code
- Normalization: HIGH — formula MW = O + α*(H1-O) + α*(H2-O) with α=0.13458335 matches virtual_sites3 directive exactly

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (30 days for stable format spec)
