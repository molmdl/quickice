# Phase 14: GROMACS Export - Research

**Researched:** 2026-04-05
**Domain:** GROMACS file format generation (molecular dynamics simulation)
**Confidence:** HIGH

## Summary

This phase implements GROMACS export functionality enabling users to export ice structures as valid simulation-ready input files. The implementation requires generating three files: .gro (coordinates), .top (topology), and .itp (force field include). The tip4p-ice.itp force field file already exists at the project root and needs to be bundled as an application resource.

**Primary recommendation:** Create GROMACSExporter class following the existing PDBExporter pattern in export.py, using QFileDialog for file selection and generating all three files from a single user interaction.

## Standard Stack

The established libraries and tools for GROMACS file generation:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.10+ | File I/O, string formatting | Required for .gro/.top generation |
| PySide6 | 6.x | QFileDialog, resource system | Already in project |

### Existing Dependencies
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| genice2 | 2.2.13+ | Generates .gro files natively | Already project dependency |
| tip4p-ice.itp | (local) | TIP4P-ICE force field | Bundled with project |

### Resource Bundling
| Tool | Purpose | Why Standard |
|------|---------|---------------|
| pyside6-rcc | Compile .qrc resource files | Qt's standard resource system |

**Installation:**
```bash
# No new pip packages required
# pyside6-rcc comes with PySide6
```

## Architecture Patterns

### Recommended Project Structure
```
quickice/
├── gui/
│   ├── export.py              # Add GROMACSExporter class here
│   ├── main_window.py         # Add menu item
│   └── resources/
│       └── gromacs.qrc       # Resource collection file
├── output/
│   └── gromacs_writer.py      # NEW: .gro/.top generation logic
├── data/
│   └── tip4p-ice.itp          # Bundled force field
└── tip4p-ice.itp              # Source file (copied to data/)
```

### Pattern 1: GROMACSExporter Class
**What:** Export handler following existing PDBExporter pattern
**When to use:** When user selects "Export for GROMACS" from File menu
**Example:**
```python
# Source: Following PDBExporter pattern from export.py
from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QMessageBox

class GROMACSExporter:
    """Handle GROMACS file export (.gro, .top, .itp)."""
    
    def __init__(self, parent_widget):
        self.parent = parent_widget
    
    def export_gromacs(self, candidate) -> bool:
        """Export ice structure to GROMACS format.
        
        Args:
            candidate: Candidate with positions, atom_names, cell, nmolecules
            
        Returns:
            True if export succeeded
        """
        # Show save dialog for .gro file
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self.parent,
            "Export for GROMACS",
            "ice_structure.gro",
            "GRO Files (*.gro);;All Files (*)",
            "GRO Files (*.gro)"
        )
        
        if not filepath:
            return False
        
        # Ensure .gro extension
        path = Path(filepath)
        if path.suffix.lower() != '.gro':
            path = path.with_suffix('.gro')
        
        # Generate companion filenames
        base = path.with_suffix('')
        top_path = base.with_suffix('.top')
        itp_path = base.with_suffix('.itp')
        
        try:
            # Write .gro file
            write_gro_file(candidate, str(path))
            # Write .top file
            write_top_file(candidate, str(top_path))
            # Copy .itp file
            copy_itp_file(str(itp_path))
            return True
        except Exception as e:
            QMessageBox.critical(self.parent, "Export Error", f"Failed: {e}")
            return False
```

### Pattern 2: .gro File Format
**What:** GROMACS coordinate file format (fixed-width columns)
**When to use:** Writing atomic coordinates for GROMACS
**Example:**
```python
# Source: GROMACS 2026 manual - gro format specification
def write_gro_file(candidate, filepath):
    """Write candidate to GROMACS .gro format.
    
    Format (per GROMACS manual):
    - Title line (free format, optional t= ps)
    - Number of atoms (free format integer)
    - One line per atom (fixed 8-column format)
    - Box vectors (free format, space-separated reals)
    """
    nmol = candidate.nmolecules
    n_atoms = nmol * 4  # 4-point water: O, H1, H2, MW
    
    with open(filepath, 'w') as f:
        # Title line
        f.write(f"Ice structure {candidate.phase_id} exported by QuickIce\n")
        
        # Number of atoms
        f.write(f"{n_atoms:5d}\n")
        
        # Atom lines: residue num, residue name, atom name, atom num, x, y, z
        # Format: i5, a5, a5, i5, 3f8.3 (positions in nm)
        atom_num = 0
        for mol_idx in range(nmol):
            base_idx = mol_idx * 4  # O, H1, H2, MW order
            
            # Oxygen (OW)
            atom_num += 1
            pos = candidate.positions[base_idx]
            f.write(f"{mol_idx+1:5d}SOL    OW1 {atom_num:5d}"
                    f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")
            
            # Hydrogen 1 (HW)
            atom_num += 1
            pos = candidate.positions[base_idx + 1]
            f.write(f"{mol_idx+1:5d}SOL    HW1 {atom_num:5d}"
                    f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")
            
            # Hydrogen 2 (HW)
            atom_num += 1
            pos = candidate.positions[base_idx + 2]
            f.write(f"{mol_idx+1:5d}SOL    HW2 {atom_num:5d}"
                    f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")
            
            # Massless virtual site (MW)
            atom_num += 1
            pos = candidate.positions[base_idx + 3]
            f.write(f"{mol_idx+1:5d}SOL    MW  {atom_num:5d}"
                    f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")
        
        # Box vectors (triclinic: v1(x) v2(y) v3(z) v1(y) v1(z) v2(x) v2(z) v3(x) v3(y))
        cell = candidate.cell
        f.write(f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}"
                f"{cell[0,1]:10.5f}{cell[0,2]:10.5f}{cell[1,0]:10.5f}"
                f"{cell[1,2]:10.5f}{cell[2,0]:10.5f}{cell[2,1]:10.5f}\n")
```

### Pattern 3: .top File Format
**What:** GROMACS topology file structure
**When to use:** Writing topology for ice structure
**Example:**
```python
# Source: GROMACS 2026 topology file specification
def write_top_file(candidate, filepath):
    """Write GROMACS topology file."""
    nmol = candidate.nmolecules
    
    with open(filepath, 'w') as f:
        f.write("; Generated by QuickIce\n")
        f.write("; TIP4P-ICE water model\n\n")
        
        # [ defaults ] - force field defaults
        f.write("[ defaults ]\n")
        f.write("; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ\n")
        f.write("1         2           yes        1.0      1.0\n\n")
        
        # [ atomtypes ] - define custom atom types for TIP4P-ICE
        f.write("[ atomtypes ]\n")
        f.write("; name  bond_type  atomic_number  mass  charge  ptype  V  W\n")
        f.write("OW_ice      8        15.9994      0.0    0.0     A  0.31668e-3  0.88216e-6\n")
        f.write("HW_ice      1         1.0080      0.0    0.0     A  0.0        0.0\n")
        f.write("MW          0         0.0000      0.0    0.0     V  0.0        0.0\n\n")
        
        # [ moleculetype ] - define SOL (water)
        f.write("[ moleculetype ]\n")
        f.write("; Name        nrexcl\n")
        f.write("SOL          2\n\n")
        
        # [ atoms ] - define atoms in molecule
        f.write("[ atoms ]\n")
        f.write(";   nr  type  resi  res  atom  cgnr     charge    mass\n")
        f.write("   1   OW_ice    1  SOL    OW     1       0.0  16.00000\n")
        f.write("   2   HW_ice    1  SOL   HW1     1     0.5897   1.00800\n")
        f.write("   3   HW_ice    1  SOL   HW2     1     0.5897   1.00800\n")
        f.write("   4   MW        1  SOL    MW     1    -1.1794   0.00000\n\n")
        
        # [ settles ] - TIP4P water geometry (for rigid water)
        f.write("[ settles ]\n")
        f.write("; i  funct  doh     dhh\n")
        f.write("  1    1    0.09572  0.15139\n\n")
        
        # [ virtual_sites3 ] - define MW virtual site
        f.write("[ virtual_sites3 ]\n")
        f.write("; Vsite from                    funct  a          b\n")
        f.write("   4     1       2       3       1      0.13458335 0.13458335\n\n")
        
        # [ exclusions ] - exclude virtual site from non-bonded
        f.write("[ exclusions ]\n")
        f.write("  1  2  3  4\n")
        f.write("  2  1  3  4\n")
        f.write("  3  1  2  4\n")
        f.write("  4  1  2  3\n\n")
        
        # [ system ] - system-level section
        f.write("[ system ]\n")
        f.write("; Name\n")
        f.write(f"{candidate.phase_id} exported by QuickIce\n\n")
        
        # [ molecules ] - molecule counts
        f.write("[ molecules ]\n")
        f.write("; Compound    #mols\n")
        f.write(f"SOL          {nmol}\n")
```

### Pattern 4: Resource Bundling
**What:** Bundle tip4p-ice.itp using Qt resource system
**When to use:** Accessing .itp file at runtime
**Example:**
```python
# Resource collection file: gromacs.qrc
<RCC>
  <qresource prefix="/gromacs">
    <file>tip4p-ice.itp</file>
  </qresource>
</RCC>

# Python code to access resource
from PySide6.QtCore import QResource
QResource.registerResource(":/gromacs/gromacs.rcc")

# Reading bundled resource
def get_tip4p_itp():
    """Read tip4p-ice.itp from resources."""
    resource = QResource(":/gromacs/tip4p-ice.itp")
    if resource.isValid():
        return resource.data().decode('utf-8')
    # Fallback: read from file system
    with open("quickice/data/tip4p-ice.itp", 'r') as f:
        return f.read()
```

### Anti-Patterns to Avoid
- **Hand-rolling coordinate format:** .gro has specific fixed-width formatting - use string formatting with exact column widths
- **Missing virtual site (MW):** TIP4P models require a massless virtual site for electrostatics - don't omit
- **Wrong box format:** GROMACS supports only specific box types - use the triclinic format shown

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| .gro file format | Custom string formatting | Follow GROMACS fixed format spec | Columns are position-specific |
| TIP4P-ICE topology | Type parameters from literature | tip4p-ice.itp from Vega group | Validated force field |
| Resource loading | Relative file path | Qt resource system | Works in PyInstaller bundle |
| Coordinate units | Assume Angstrom | Use nm (Candidate uses nm) | GROMACS expects nm |

**Key insight:** GROMACS file formats have strict specifications. The .gro format uses fixed column positions (not space-separated), and the .top format requires specific directive ordering.

## Common Pitfalls

### Pitfall 1: .gro Column Alignment
**What goes wrong:** Atoms appear scrambled or displaced in visualization
**Why it happens:** .gro format requires exact column widths, not space-separated values
**How to avoid:** Use exact format string `"%5d%-5s%5s%5d%8.3f%8.3f%8.3f"`
**Warning signs:** gmx check reports position errors

### Pitfall 2: Missing Massless Virtual Site
**What goes wrong:** Simulation fails or gives wrong energies
**Why it happens:** TIP4P models need MW (massless virtual site) for correct electrostatics
**How to avoid:** Include MW atom in both .gro and .top; use `virtual_sites3` directive
**Warning signs:** GROMACS grompp warnings about missing charges

### Pitfall 3: Box Vector Format
**What goes wrong:** Simulation doesn't recognize periodic box
**Why it happens:** Using wrong box format (GROMACS limited to specific triclinic)
**How to avoid:** Use format: `v1(x) v2(y) v3(z) v1(y) v1(z) v2(x) v2(z) v3(x) v3(y)`
**Warning signs:** gmx check reports box errors

### Pitfall 4: Wrong Atom Ordering
**What goes wrong:** Molecule geometry is wrong
**Why it happens:** O, H, H order vs. H, O, H
**How to avoid:** Verify atom_names from Candidate match TIP4P ordering (O first, then H atoms, then MW)
**Warning signs:** O-H distances unrealistic

### Pitfall 5: Resource Path in PyInstaller
**What goes wrong:** FileNotFoundError when running from PyInstaller bundle
**Why it happens:** Hardcoded relative paths break in frozen app
**How to avoid:** Use Qt resource system or `sys._MEIPASS` detection
**Warning signs:** Export works in dev but fails in packaged app

## Code Examples

Verified patterns from GROMACS manual and existing codebase:

### Export Handler Integration
```python
# Source: Following Phase 11 pattern in main_window.py
# In main_window.py _create_menu_bar():
export_menu = file_menu.addMenu("Export")

export_gromacs_action = export_menu.addAction("Export for GROMACS...")
export_gromacs_action.triggered.connect(self._on_export_gromacs)

# Handler initialization
self._gromacs_exporter = GROMACSExporter(self)

# Callback
def _on_export_gromacs(self):
    """Handle GROMACS export."""
    candidate = self._viewmodel.get_current_candidate()
    if candidate is None:
        QMessageBox.warning(self, "No Structure", "Generate a structure first.")
        return
    
    self._gromacs_exporter.export_gromacs(candidate)
```

### Candidate Access
```python
# Source: quickice/structure_generation/types.py
# Candidate structure:
@dataclass
class Candidate:
    positions: np.ndarray      # (N_atoms, 3) in nm
    atom_names: list[str]     # ["O", "H", "H", "O", "H", "H", ...]
    cell: np.ndarray          # (3, 3) cell vectors in nm
    nmolecules: int           # Number of water molecules
    phase_id: str            # e.g., "ice_ih"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No GROMACS export | Generate .gro/.top/.itp | Phase 14 | Users can run MD simulations |
| GenIce2 output only | Custom .top generation | Phase 14 | Proper topology for TIP4P-ICE |
| File system .itp | Resource bundling | Phase 14 | Works in PyInstaller |

**Deprecated/outdated:**
- None - this is new functionality

## Open Questions

1. **Virtual site calculation for generated structures**
   - What we know: tip4p-ice.itp uses fixed virtual site parameters (a=b=0.13458335)
   - What's unclear: Whether positions in Candidate include MW or require calculation
   - Recommendation: Verify Candidate positions format (4-point or 3-point)

2. **GenIce2 output format**
   - What we know: GenIce2 can output GROMACS .gro format via `-f gromacs`
   - What's unclear: Whether QuickIce should use GenIce2 output directly or reformat Candidate
   - Recommendation: Use Candidate directly to ensure consistency with 3D viewer

3. **Validation approach**
   - What we know: GRO-06 requires files pass gmx check
   - What's unclear: Whether to validate internally or require user to run gmx check
   - Recommendation: Silent export (per CONTEXT.md) - user validates externally

## Sources

### Primary (HIGH confidence)
- GROMACS 2026 Manual - File Formats: https://manual.gromacs.org/current/reference-manual/file-formats.html
- GROMACS 2026 Manual - Topology: https://manual.gromacs.org/current/reference-manual/topologies/topology-file-formats.html
- PySide6 QResource: https://doc.qt.io/qtforpython-6.6/PySide6/QtCore/QResource.html

### Secondary (MEDIUM confidence)
- tip4p-ice.itp file (project source): Verified exists at /share/home/nglokwan/quickice/tip4p-ice.itp
- Existing export.py patterns: Verified in codebase

### Tertiary (LOW confidence)
- None required

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH - No new dependencies needed
- Architecture: HIGH - Follows existing Phase 11 patterns
- Pitfalls: MEDIUM - GROMACS format details verified from manual

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (30 days for stable format spec)
