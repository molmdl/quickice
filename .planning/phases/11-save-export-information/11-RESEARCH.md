# Phase 11: Save/Export + Information - Research

**Researched:** 2026-04-02  
**Domain:** PySide6 file dialogs, matplotlib export, VTK screenshot capture, Qt tooltips  
**Confidence:** HIGH

## Summary

This phase focuses on implementing file export functionality and information display for the QuickIce GUI. The main technical challenges are:
1. **File Save Dialogs** - PySide6 QFileDialog with native dialogs for PDB and image exports
2. **Phase Diagram Export** - Leverage existing matplotlib savefig infrastructure  
3. **VTK Viewport Screenshots** - Use vtkWindowToImageFilter for 3D scene capture
4. **Tooltips** - QToolTip with question mark icons for help text
5. **Phase Info Display** - Repurpose existing log panel for scientific information

The codebase already has most infrastructure in place. Phase diagram export exists, PDB writer exists, log panel exists. This phase is primarily about wiring UI elements and adding screenshot capability.

**Primary recommendation:** Use native QFileDialog for all file saves, leverage existing matplotlib savefig patterns, implement VTK screenshot with vtkWindowToImageFilter, and repurpose InfoPanel for phase information display.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PySide6.QtWidgets.QFileDialog | 6.9.3+ | File save dialogs | Native OS integration, consistent UX |
| matplotlib.figure.Figure.savefig | 3.10+ | Diagram export | Already in codebase, supports PNG/SVG |
| vtkWindowToImageFilter | 9.5.2+ | VTK screenshots | Standard VTK pattern for viewport capture |
| vtkPNGWriter/vtkJPEGWriter | 9.5.2+ | Image output | VTK-native writers |
| QToolTip | 6.9.3+ | Context help | Built-in Qt tooltip system |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib.Path | stdlib | Path handling | Already used throughout codebase |
| QMessageBox | 6.9.3+ | Overwrite confirmation | Required per CONTEXT.md |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native QFileDialog | Qt custom dialog | Native provides better OS integration and user familiarity |
| VTK screenshot | Grab widget pixels | vtkWindowToImageFilter captures full render including offscreen |

**Installation:**
All dependencies already installed. No new packages needed.

## Architecture Patterns

### Recommended Project Structure
```
quickice/gui/
├── export/              # NEW: Export functionality module
│   ├── __init__.py
│   ├── pdb_exporter.py  # PDB file save dialog handler
│   ├── image_exporter.py # Phase diagram and viewport image exporters
│   └── dialogs.py       # File save dialog utilities
├── info/                # NEW: Information display
│   ├── __init__.py
│   ├── phase_info.py    # Phase information display logic
│   └── tooltips.py      # Tooltip content and setup
└── (existing files...)
```

### Pattern 1: Native File Save Dialog
**What:** Use QFileDialog.getSaveFileName() for file exports
**When to use:** All file save operations (PDB, images)
**Example:**
```python
# Source: PySide6 official docs, verified via webfetch
from PySide6.QtWidgets import QFileDialog, QMessageBox
from pathlib import Path

def save_pdb_file(parent_widget, default_name: str) -> str | None:
    """Show file save dialog for PDB export.
    
    Args:
        parent_widget: Parent widget for dialog centering
        default_name: Suggested filename (e.g., "ice_Ih_250K_1000bar_c1.pdb")
    
    Returns:
        Selected filepath or None if cancelled
    """
    filepath, selected_filter = QFileDialog.getSaveFileName(
        parent_widget,
        "Save PDB File",
        default_name,
        "PDB Files (*.pdb);;All Files (*)",
        "PDB Files (*.pdb)"
    )
    
    if not filepath:
        return None
    
    # Ensure .pdb extension
    path = Path(filepath)
    if path.suffix.lower() != '.pdb':
        filepath = str(path.with_suffix('.pdb'))
    
    # Check for overwrite
    if Path(filepath).exists():
        reply = QMessageBox.question(
            parent_widget,
            "Overwrite File?",
            f"File '{Path(filepath).name}' already exists. Overwrite?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.No:
            return None
    
    return filepath
```

### Pattern 2: Matplotlib Figure Export
**What:** Export phase diagram to PNG/SVG using existing matplotlib infrastructure
**When to use:** Phase diagram image save (EXPORT-02)
**Example:**
```python
# Source: matplotlib.figure.Figure.savefig docs (verified), existing codebase
# File: quickice/output/phase_diagram.py line 929
from matplotlib.figure import Figure

def export_diagram_image(figure: Figure, filepath: str, format: str = 'PNG'):
    """Export matplotlib figure to image file.
    
    Args:
        figure: Matplotlib figure to export
        filepath: Output path (extension determines format)
        format: 'PNG' or 'SVG'
    """
    # Existing pattern from phase_diagram.py
    if format.upper() == 'PNG':
        figure.savefig(
            filepath, 
            dpi=300,  # High resolution for publications
            bbox_inches='tight', 
            facecolor='white'
        )
    elif format.upper() == 'SVG':
        figure.savefig(
            filepath, 
            format='svg',
            bbox_inches='tight', 
            facecolor='white'
        )
```

### Pattern 3: VTK Viewport Screenshot
**What:** Capture 3D viewport content to image file
**When to use:** 3D scene image save (EXPORT-03)
**Example:**
```python
# Source: VTK 9.5 documentation patterns (training knowledge)
from vtkmodules.all import (
    vtkWindowToImageFilter,
    vtkPNGWriter,
    vtkJPEGWriter,
)
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

def capture_viewport(vtk_widget: QVTKRenderWindowInteractor, 
                      filepath: str, 
                      magnification: int = 1):
    """Capture VTK viewport to image file.
    
    Args:
        vtk_widget: The QVTKRenderWindowInteractor to capture
        filepath: Output path (.png or .jpg)
        magnification: Scale factor for higher resolution (default 1)
    """
    render_window = vtk_widget.GetRenderWindow()
    
    # Create window-to-image filter
    window_to_image = vtkWindowToImageFilter()
    window_to_image.SetInput(render_window)
    window_to_image.SetScale(magnification)
    window_to_image.ReadFrontBufferOff()  # Use offscreen buffer
    window_to_image.Update()
    
    # Determine writer based on extension
    path = Path(filepath)
    if path.suffix.lower() == '.png':
        writer = vtkPNGWriter()
    else:
        writer = vtkJPEGWriter()
        writer.SetQuality(95)  # High quality JPEG
    
    writer.SetFileName(filepath)
    writer.SetInputConnection(window_to_image.GetOutputPort())
    writer.Write()
```

### Pattern 4: QToolTip with Question Mark Icon
**What:** Display help text on hover over ? icon
**When to use:** UI element help tooltips (INFO-03)
**Example:**
```python
# Source: PySide6 QToolTip documentation patterns (verified)
from PySide6.QtWidgets import QLabel, QApplication, QWidget, QHBoxLayout
from PySide6.QtCore import Qt

class HelpLabel(QWidget):
    """Question mark icon that shows tooltip on hover.
    
    Per CONTEXT.md: Tooltip triggered by hovering over ? icon.
    """
    
    def __init__(self, help_text: str, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Question mark icon
        self.icon_label = QLabel("?")
        self.icon_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #999;
                border-radius: 8px;
                padding: 2px;
                min-width: 16px;
                max-width: 16px;
                min-height: 16px;
                max-height: 16px;
            }
            QLabel:hover {
                background-color: #e0e0e0;
                color: #333;
            }
        """)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setCursor(Qt.WhatsThisCursor)
        
        # Set tooltip - shown on hover
        self.icon_label.setToolTip(help_text)
        
        layout.addWidget(self.icon_label)
```

### Pattern 5: Phase Info Display in Log Panel
**What:** Repurpose existing InfoPanel for phase information
**When to use:** Display phase details (INFO-01)
**Example:**
```python
# Source: Existing InfoPanel from quickice/gui/view.py
from quickice.gui.view import InfoPanel
from quickice.phase_mapping.lookup import PHASE_METADATA

class PhaseInfoDisplay:
    """Display phase information in existing log panel.
    
    Per CONTEXT.md: Use existing log panel — no new info window needed.
    """
    
    @staticmethod
    def display_phase_info(info_panel: InfoPanel, phase_id: str, T: float, P: float):
        """Display phase information in log panel.
        
        Args:
            info_panel: The existing InfoPanel widget
            phase_id: Phase identifier (e.g., "ice_ih")
            T: Temperature in Kelvin
            P: Pressure in MPa
        """
        meta = PHASE_METADATA.get(phase_id, {})
        phase_name = meta.get("name", phase_id)
        density = meta.get("density", "Unknown")
        
        info_panel.append_log(f"\n{'='*50}")
        info_panel.append_log(f"Phase Information: {phase_name}")
        info_panel.append_log(f"{'='*50}")
        info_panel.append_log(f"Conditions: T = {T:.1f} K, P = {P:.1f} MPa")
        info_panel.append_log(f"Density: {density} g/cm³")
        info_panel.append_log(f"Structure: {_get_structure_type(phase_id)}")
        info_panel.append_log(f"")
        info_panel.append_log(f"Citation:")
        info_panel.append_log(_get_citation(phase_id))
        
        # Add copy button functionality (per CONTEXT.md)
        info_panel.append_log(f"[Copy citation to clipboard]")


def _get_structure_type(phase_id: str) -> str:
    """Get human-readable structure type."""
    structure_types = {
        "ice_ih": "Hexagonal (P6₃/mmc)",
        "ice_ic": "Cubic diamond (Fd3m)",
        "ice_ii": "Rhombohedral (R-3)",
        "ice_iii": "Tetragonal (P4₁2₁2)",
        "ice_v": "Monoclinic (C2/c)",
        "ice_vi": "Tetragonal (P4₂/nmc)",
        "ice_vii": "Cubic (Pn-3m)",
        "ice_viii": "Tetragonal (I4₁/amd)",
        "ice_xi": "Hexagonal ordered (Cmc2₁)",
        "ice_ix": "Tetragonal ordered (P4₁2₁2)",
        "ice_x": "Symmetric H-bonds (Pn-3m)",
        "ice_xv": "Ordered (P-1)",
    }
    return structure_types.get(phase_id, "Unknown")


def _get_citation(phase_id: str) -> str:
    """Get primary citation for phase."""
    # These are authoritative references for each ice phase
    citations = {
        "ice_ih": "Bjerrum, K. (1952). Science, 115(2989), 385-390.",
        "ice_ii": "Kamb, B. (1964). Science, 150(3696), 544-546.",
        "ice_iii": "Kamb, B. & Datta, S.K. (1971). Science, 174(4009), 557-558.",
        "ice_v": "Kamb, B. (1965). Science, 150(3700), 1123-1125.",
        "ice_vi": "Kamb, B. (1965). J. Chem. Phys., 43(12), 4252-4255.",
        "ice_vii": "Kamb, B. & Davis, B.L. (1964). PNAS, 52(6), 1433-1439.",
        "ice_viii": "Kamb, B. (1967). J. Chem. Phys., 46(5), 2079-2080.",
        "ice_xi": "Tajima, Y. et al. (1982). J. Phys. C: Solid State Phys., 15(8), L755-L758.",
        "ice_ix": "Whalley, E. et al. (1968). J. Chem. Phys., 48(5), 2362-2370.",
        "ice_x": "Holzapfel, W.B. et al. (1984). Phys. Rev. B, 30(6), 3042-3047.",
        "ice_xv": "Salzmann, C.G. et al. (2009). Phys. Rev. Lett., 103(10), 105701.",
    }
    return citations.get(phase_id, "See IAPWS R14-08(2011) for phase data.")
```

### Anti-Patterns to Avoid
- **Don't use QFileDialog::DontUseNativeDialog**: Native dialogs provide better OS integration and user familiarity
- **Don't capture VTK widget with QPixmap::grabWidget**: Won't capture hardware-rendered content correctly; use vtkWindowToImageFilter instead
- **Don't create separate info windows**: Per CONTEXT.md, repurpose existing log panel

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File overwrite confirmation | Custom QMessageBox logic | QFileDialog handles + explicit check | Consistent UX, proper i18n |
| VTK screenshot | QPixmap grab of widget | vtkWindowToImageFilter | Hardware-accelerated rendering needs VTK-native capture |
| Path extension handling | Manual string manipulation | Path.with_suffix() | Edge cases, cross-platform issues |
| PDB file writing | New writer | write_pdb_with_cryst1 (exists) | Already implements PDB spec correctly |

**Key insight:** The codebase already has PDB writing infrastructure in `quickice/output/pdb_writer.py`. Reuse this rather than building new export logic.

## Common Pitfalls

### Pitfall 1: VTK Screenshot Returns Black Image
**What goes wrong:** Capturing VTK viewport before render completes results in black/empty images
**Why it happens:** VTK renders asynchronously; capture may happen before scene is drawn
**How to avoid:** Force render before capture with `render_window.Render()` before window_to_image
**Warning signs:** Intermittent black images, especially after scene changes

### Pitfall 2: Matplotlib Export Cropping Content
**What goes wrong:** Phase diagram export cuts off labels or legend
**Why it happens:** Default bbox_inches='tight' can clip some elements
**How to avoid:** Use explicit `pad_inches=0.2` and ensure figure layout is finalized
**Warning signs:** Labels at figure edges appear cut off in exported files

### Pitfall 3: File Dialog Default Directory
**What goes wrong:** Dialog opens to unexpected directory, confusing users
**Why it happens:** No explicit directory set in QFileDialog call
**How to avoid:** Use project directory or last-used directory as starting point
**Warning signs:** User reports "can't find my files" after saving

### Pitfall 4: Overwrite Confirmation Missing
**What goes wrong:** User accidentally overwrites existing files
**Why it happens:** QFileDialog's overwrite prompt is OS-dependent and may not show
**How to avoid:** Explicitly check with QMessageBox before writing (per CONTEXT.md)
**Warning signs:** User complaints about lost work

### Pitfall 5: VTK Capture Resolution Too Low
**What goes wrong:** Exported 3D scene images appear pixelated
**Why it happens:** Default viewport size used for capture
**How to avoid:** Use SetScale() on vtkWindowToImageFilter for higher resolution export
**Warning signs:** Users request "higher quality" exports

## Code Examples

### Complete PDB Export Handler
```python
# Source: Existing codebase patterns + new functionality
from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QMessageBox
from quickice.output.pdb_writer import write_pdb_with_cryst1
from quickice.structure_generation.types import Candidate
from quickice.ranking.types import RankedCandidate

class PDBExporter:
    """Handle PDB file export with proper dialogs and validation."""
    
    def __init__(self, parent_widget):
        self.parent = parent_widget
    
    def export_candidate(self, ranked: RankedCandidate, T: float, P: float):
        """Export a ranked candidate to PDB file.
        
        Per CONTEXT.md:
        - Default filename: {phase}_{T}K_{P}bar_c{candidate_num}.pdb
        - Prompt before overwriting
        """
        # Generate default filename
        phase_id = ranked.candidate.phase_id or "ice"
        default_name = f"{phase_id}_{T:.0f}K_{P:.0f}bar_c{ranked.rank}.pdb"
        
        # Show save dialog
        filepath, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Save PDB File",
            default_name,
            "PDB Files (*.pdb);;All Files (*)"
        )
        
        if not filepath:
            return False
        
        # Ensure extension
        path = Path(filepath)
        if path.suffix.lower() != '.pdb':
            path = path.with_suffix('.pdb')
        
        # Check overwrite
        if path.exists():
            reply = QMessageBox.question(
                self.parent,
                "Overwrite File?",
                f"File '{path.name}' already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return False
        
        # Write file
        try:
            write_pdb_with_cryst1(ranked.candidate, str(path))
            return True
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Export Error",
                f"Failed to save PDB file:\n\n{str(e)}"
            )
            return False
```

### Phase Diagram Export Handler
```python
# Source: Existing savefig pattern from quickice/output/phase_diagram.py
from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QMessageBox
from matplotlib.figure import Figure

class DiagramExporter:
    """Handle phase diagram image export."""
    
    def __init__(self, parent_widget):
        self.parent = parent_widget
    
    def export_diagram(self, figure: Figure):
        """Export phase diagram to PNG or SVG.
        
        Per CONTEXT.md: OpenCode's discretion on formats (PNG and/or SVG).
        """
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self.parent,
            "Save Phase Diagram Image",
            "phase_diagram.png",
            "PNG Image (*.png);;SVG Image (*.svg);;All Files (*)"
        )
        
        if not filepath:
            return False
        
        path = Path(filepath)
        
        # Determine format from filter or extension
        if 'SVG' in selected_filter or path.suffix.lower() == '.svg':
            path = path.with_suffix('.svg')
            format_type = 'svg'
        else:
            path = path.with_suffix('.png')
            format_type = 'png'
        
        # Check overwrite
        if path.exists():
            reply = QMessageBox.question(
                self.parent,
                "Overwrite File?",
                f"File '{path.name}' already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return False
        
        # Export using existing pattern
        try:
            if format_type == 'svg':
                figure.savefig(
                    str(path),
                    format='svg',
                    bbox_inches='tight',
                    facecolor='white'
                )
            else:
                figure.savefig(
                    str(path),
                    dpi=300,
                    bbox_inches='tight',
                    facecolor='white'
                )
            return True
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Export Error",
                f"Failed to save diagram image:\n\n{str(e)}"
            )
            return False
```

### VTK Viewport Export Handler
```python
# Source: VTK 9.5 patterns
from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QMessageBox
from vtkmodules.all import vtkWindowToImageFilter, vtkPNGWriter, vtkJPEGWriter
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

class ViewportExporter:
    """Handle 3D viewport screenshot export."""
    
    def __init__(self, parent_widget):
        self.parent = parent_widget
    
    def capture_viewport(self, vtk_widget: QVTKRenderWindowInteractor):
        """Capture and save 3D viewport to image file."""
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self.parent,
            "Save Viewport Image",
            "ice_structure.png",
            "PNG Image (*.png);;JPEG Image (*.jpg);;All Files (*)"
        )
        
        if not filepath:
            return False
        
        path = Path(filepath)
        
        # Determine format
        if 'JPEG' in selected_filter or path.suffix.lower() in ('.jpg', '.jpeg'):
            path = path.with_suffix('.jpg')
            use_jpeg = True
        else:
            path = path.with_suffix('.png')
            use_jpeg = False
        
        # Check overwrite
        if path.exists():
            reply = QMessageBox.question(
                self.parent,
                "Overwrite File?",
                f"File '{path.name}' already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return False
        
        # Capture viewport
        try:
            render_window = vtk_widget.GetRenderWindow()
            
            # Force render to ensure scene is current
            render_window.Render()
            
            # Create window-to-image filter
            window_to_image = vtkWindowToImageFilter()
            window_to_image.SetInput(render_window)
            window_to_image.SetScale(2)  # 2x resolution for better quality
            window_to_image.ReadFrontBufferOff()
            window_to_image.Update()
            
            # Write image
            if use_jpeg:
                writer = vtkJPEGWriter()
                writer.SetQuality(95)
            else:
                writer = vtkPNGWriter()
            
            writer.SetFileName(str(path))
            writer.SetInputConnection(window_to_image.GetOutputPort())
            writer.Write()
            
            return True
            
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Export Error",
                f"Failed to save viewport image:\n\n{str(e)}"
            )
            return False
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom file dialogs | Native QFileDialog | Qt standard | Better OS integration |
| QPixmap::grabWidget for VTK | vtkWindowToImageFilter | VTK best practice | Captures hardware rendering |
| Separate info windows | Repurposed log panel | Per CONTEXT.md | Less window clutter |
| Implicit overwrite prompt | Explicit QMessageBox check | Per CONTEXT.md | Prevents data loss |

**Deprecated/outdated:**
- QFileDialog::getSaveFileName without default directory: Always provide starting directory for better UX
- QPixmap::grabWindow for VTK widgets: Won't capture OpenGL content correctly

## Open Questions

Things that couldn't be fully resolved:

1. **High-resolution VTK export settings**
   - What we know: SetScale() increases resolution but affects performance
   - What's unclear: Optimal scale factor for publication-quality exports
   - Recommendation: Start with 2x, consider adding user preference for quality vs. speed

2. **Image format for viewport screenshots**
   - What we know: PNG is lossless, JPEG is smaller
   - What's unclear: User preference between formats
   - Recommendation: Support both PNG and JPEG, default to PNG for quality

## Sources

### Primary (HIGH confidence)
- PySide6 QFileDialog documentation (webfetch verified) - File save dialog patterns
- matplotlib.figure.Figure.savefig (webfetch verified) - Image export API
- Existing codebase files (read verified):
  - `quickice/gui/view.py` - InfoPanel structure
  - `quickice/gui/phase_diagram_widget.py` - Diagram widget with figure
  - `quickice/output/pdb_writer.py` - PDB writing functions
  - `quickice/phase_mapping/lookup.py` - Phase metadata (PHASE_METADATA)

### Secondary (MEDIUM confidence)
- VTK 9.5 documentation patterns (training knowledge) - Window capture methods
- PySide6 QToolTip patterns (training knowledge) - Tooltip implementation

### Tertiary (LOW confidence)
- Ice phase citations (training knowledge + Wikipedia general reference) - Marked for validation with IAPWS R14-08(2011)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All dependencies verified in existing codebase and official docs
- Architecture: HIGH - Patterns align with existing codebase structure  
- Pitfalls: MEDIUM - VTK-specific issues based on training knowledge, should be validated during implementation

**Research date:** 2026-04-02  
**Valid until:** 2026-05-02 (30 days - stable Qt/VTK APIs)
