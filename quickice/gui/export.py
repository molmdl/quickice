"""Export handlers for PDB files, phase diagram images, and 3D viewport screenshots.

This module provides exporter classes for saving user work to standard file formats:
- PDBExporter: Save ranked ice structure candidates to PDB format
- DiagramExporter: Export phase diagram to PNG or SVG images
- ViewportExporter: Capture 3D molecular viewport to image files
"""

from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QMessageBox
from matplotlib.figure import Figure
from vtkmodules.all import (
    vtkWindowToImageFilter,
    vtkPNGWriter,
    vtkJPEGWriter,
)

from quickice.output.pdb_writer import write_pdb_with_cryst1
from quickice.ranking.types import RankedCandidate
from quickice.structure_generation.types import Candidate, InterfaceStructure, IonStructure


class IonGROMACSExporter:
    """Handle GROMACS file export for ion structures.
    
    Per Issue 1: Exports ion structure from Ion tab to GROMACS format.
    Exports: ice + water + ions (Na+, Cl-).
    """
    
    def __init__(self, parent_widget):
        """Initialize ion GROMACS exporter."""
        self.parent = parent_widget
    
    def export_ion_gromacs(self, ion_structure: IonStructure) -> bool:
        """Export ion structure to GROMACS format.

        Args:
            ion_structure: IonStructure with water + ion positions

        Returns:
            True if export succeeded
        """
        # Generate default filename with ion counts
        na_count = ion_structure.na_count
        cl_count = ion_structure.cl_count
        default_name = f"ions_{na_count}na_{cl_count}cl.gro"

        # Show save dialog for .gro file
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self.parent,
            "Export Ions for GROMACS",
            default_name,
            "GRO Files (*.gro);;All Files (*)",
            "GRO Files (*.gro)"
        )
        
        if not filepath:
            return False
        
        # Ensure .gro extension
        path = Path(filepath)
        if path.suffix.lower() != '.gro':
            path = path.with_suffix('.gro')
        
        # Generate companion filename using stem
        top_path = path.with_name(path.stem + '.top')
        
        try:
            # Write .gro file
            from quickice.output.gromacs_writer import write_ion_gro_file
            write_ion_gro_file(ion_structure, str(path))
            
            # Write .top file
            from quickice.output.gromacs_writer import write_ion_top_file
            write_ion_top_file(ion_structure, str(top_path))
            
            # Create ion.itp with ion parameters (named ion.itp to match .top references)
            from quickice.structure_generation.gromacs_ion_export import write_ion_itp
            ion_itp_path = path.with_name('ion.itp')
            write_ion_itp(ion_itp_path, na_count, cl_count)
            
            # Copy water topology file (tip4p-ice.itp) for SOL molecules
            import shutil
            from quickice.output.gromacs_writer import get_tip4p_itp_path
            itp_source = get_tip4p_itp_path()
            water_itp_path = path.with_name("tip4p-ice.itp")
            shutil.copy(itp_source, water_itp_path)
            
            # Copy guest .itp file if guests are present in the original interface
            if ion_structure.guest_nmolecules > 0 and ion_structure.guest_atom_count > 0:
                # Determine guest type from ion structure atom names
                # Check first few atoms to determine guest type (CH4 vs THF)
                # Guest atoms were at the beginning of original interface structure
                # After ion insertion, we need to check existing atom names
                # This is tricky since IonStructure only has ions now
                
                # Approach: If we have guest_nmolecules > 0, check if guest data 
                # in molecule_index has guest type info, or default to CH4 (most common)
                
                # Check molecule_index for guest molecule type
                guest_type = None
                for mol in ion_structure.molecule_index:
                    if mol.mol_type == "guest":
                        # Try to determine guest type from atom names in positions
                        # Not available in IonStructure, so use heuristic
                        # Default to CH4 (most common hydrate guest)
                        guest_type = "ch4"
                        break
                
                if guest_type is None:
                    # No guest type found in molecule_index, check if guests existed
                    # Default based on count (heuristic: CH4 has 5 atoms, THF has 13+)
                    if ion_structure.guest_atom_count > 0:
                        if ion_structure.guest_atom_count >= 13:
                            guest_type = "thf"
                        else:
                            guest_type = "ch4"
                
                if guest_type:
                    try:
                        guest_itp_source = _get_guest_itp_path(guest_type)
                        guest_itp_dest = path.with_name(f"{guest_type}.itp")
                        shutil.copy(guest_itp_source, guest_itp_dest)
                    except FileNotFoundError:
                        # Guest .itp file not found - will cause GROMACS to fail
                        # but don't block export, user can add manually
                        pass
            
            return True
        except Exception as e:
            QMessageBox.critical(self.parent, "Export Error", f"Failed: {e}")
            return False


class PDBExporter:
    """Handle PDB file export with proper dialogs and validation.
    
    Per CONTEXT.md:
    - Default filename: {phase}_{T}K_{P}MPa_c{candidate_num}.pdb
    - Prompt before overwriting
    """
    
    def __init__(self, parent_widget):
        """Initialize PDB exporter.
        
        Args:
            parent_widget: Parent widget for dialog centering
        """
        self.parent = parent_widget
    
    def export_candidate(self, ranked_candidate: RankedCandidate, T: float, P: float) -> bool:
        """Export a ranked candidate to PDB file.
        
        Args:
            ranked_candidate: RankedCandidate with candidate structure and metadata
            T: Temperature in Kelvin
            P: Pressure in MPa (will be converted to MPa for filename)
            
        Returns:
            True if export succeeded, False if cancelled or failed
            
        Per CONTEXT.md:
        - Default filename format: {phase}_{T}K_{P}MPa_c{candidate_num}.pdb
        - Overwrite behavior: Prompt before overwriting
        """
        # Generate default filename
        phase_id = ranked_candidate.candidate.phase_id or "ice"
        rank = ranked_candidate.rank
        default_name = f"{phase_id}_{T:.0f}K_{P:.2f}MPa_c{rank}.pdb"
        
        # Show save dialog
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self.parent,
            "Save PDB File",
            default_name,
            "PDB Files (*.pdb);;All Files (*)",
            "PDB Files (*.pdb)"
        )
        
        if not filepath:
            return False
        
        # Ensure .pdb extension
        path = Path(filepath)
        if path.suffix.lower() != '.pdb':
            path = path.with_suffix('.pdb')
        
        # Check for overwrite
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
        
        # Write file using existing PDB writer
        try:
            write_pdb_with_cryst1(ranked_candidate.candidate, str(path))
            return True
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Export Error",
                f"Failed to save PDB file:\n\n{str(e)}"
            )
            return False


class DiagramExporter:
    """Handle phase diagram image export to PNG or SVG format.
    
    Per CONTEXT.md: OpenCode's discretion on formats (PNG and/or SVG).
    """
    
    def __init__(self, parent_widget):
        """Initialize diagram exporter.
        
        Args:
            parent_widget: Parent widget for dialog centering
        """
        self.parent = parent_widget
    
    def export_diagram(self, figure: Figure) -> bool:
        """Export matplotlib figure to PNG or SVG.
        
        Args:
            figure: Matplotlib figure to export
            
        Returns:
            True if export succeeded, False if cancelled or failed
            
        Per RESEARCH.md Pattern 2:
        - PNG: dpi=300, bbox_inches='tight', facecolor='white', pad_inches=0.2
        - SVG: format='svg', bbox_inches='tight', facecolor='white'
        """
        # Show save dialog with PNG and SVG options
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self.parent,
            "Save Phase Diagram Image",
            "phase_diagram.png",
            "PNG Image (*.png);;SVG Image (*.svg);;All Files (*)",
            "PNG Image (*.png)"
        )
        
        if not filepath:
            return False
        
        path = Path(filepath)
        
        # Determine format from selected filter or extension
        if 'SVG' in selected_filter or path.suffix.lower() == '.svg':
            path = path.with_suffix('.svg')
            format_type = 'svg'
        else:
            path = path.with_suffix('.png')
            format_type = 'png'
        
        # Check for overwrite
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
        
        # Export using matplotlib savefig
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
                    facecolor='white',
                    pad_inches=0.2
                )
            return True
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Export Error",
                f"Failed to save diagram image:\n\n{str(e)}"
            )
            return False


class ViewportExporter:
    """Handle 3D viewport screenshot export to PNG or JPEG.
    
    Per RESEARCH.md Pitfall 1: MUST call render_window.Render() before capture.
    Per RESEARCH.md Pitfall 5: Use SetScale(2) for higher resolution.
    """
    
    def __init__(self, parent_widget):
        """Initialize viewport exporter.
        
        Args:
            parent_widget: Parent widget for dialog centering
        """
        self.parent = parent_widget
    
    def capture_viewport(self, vtk_widget, viewport_name: str = "") -> bool:
        """Capture and save 3D viewport to image file.
        
        Args:
            vtk_widget: QVTKRenderWindowInteractor to capture
            viewport_name: Optional viewport identifier (e.g., "left", "right") for unique filename
            
        Returns:
            True if export succeeded, False if cancelled or failed
            
        Per RESEARCH.md Pattern 3:
        - Force render before capture to avoid black images
        - Use SetScale(2) for 2x resolution
        - ReadFrontBufferOff() for offscreen buffer
        - JPEG quality: 95
        """
        # Generate default filename with viewport identifier if provided
        if viewport_name:
            default_filename = f"ice_structure_{viewport_name}.png"
        else:
            default_filename = "ice_structure.png"
        
        # Show save dialog with PNG and JPEG options
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self.parent,
            "Save Viewport Image",
            default_filename,
            "PNG Image (*.png);;JPEG Image (*.jpg);;All Files (*)",
            "PNG Image (*.png)"
        )
        
        if not filepath:
            return False
        
        path = Path(filepath)
        
        # Determine format from selected filter or extension
        if 'JPEG' in selected_filter or path.suffix.lower() in ('.jpg', '.jpeg'):
            path = path.with_suffix('.jpg')
            use_jpeg = True
        else:
            path = path.with_suffix('.png')
            use_jpeg = False
        
        # Check for overwrite
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
        
        # Capture viewport using VTK
        try:
            render_window = vtk_widget.GetRenderWindow()
            
            # CRITICAL: Force render before capture to avoid black images
            render_window.Render()
            
            # Create window-to-image filter
            window_to_image = vtkWindowToImageFilter()
            window_to_image.SetInput(render_window)
            window_to_image.SetScale(2)  # 2x resolution for better quality
            window_to_image.ReadFrontBufferOff()  # Use offscreen buffer
            window_to_image.Update()
            
            # Write image using appropriate writer
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


class GROMACSExporter:
    """Handle GROMACS file export (.gro, .top, .itp).
    
    Per plan 14-02: Single export action generates all three files.
    """
    
    def __init__(self, parent_widget):
        """Initialize GROMACS exporter.
        
        Args:
            parent_widget: Parent widget for dialog centering
        """
        self.parent = parent_widget
    
    def export_gromacs(self, ranked_candidate: RankedCandidate, T: float, P: float) -> bool:
        """Export ice structure to GROMACS format.

        Args:
            ranked_candidate: RankedCandidate with candidate structure and metadata
            T: Temperature in Kelvin
            P: Pressure in MPa

        Returns:
            True if export succeeded

        Per CONTEXT.md:
        - Default filename format: {phase}_{T}K_{P}MPa_c{rank}.gro
        - Generates companion .top and .itp files
        """
        # Generate default filename with rank/T/P info
        phase_id = ranked_candidate.candidate.phase_id or "ice"
        rank = ranked_candidate.rank
        default_name = f"{phase_id}_{T:.0f}K_{P:.2f}MPa_c{rank}.gro"

        # Extract candidate from RankedCandidate
        candidate = ranked_candidate.candidate

        # Show save dialog for .gro file
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self.parent,
            "Export for GROMACS",
            default_name,
            "GRO Files (*.gro);;All Files (*)",
            "GRO Files (*.gro)"
        )
        
        if not filepath:
            return False
        
        # Ensure .gro extension
        path = Path(filepath)
        if path.suffix.lower() != '.gro':
            path = path.with_suffix('.gro')
        
        # Generate companion filenames using stem (handles dots in filename correctly)
        # stem = filename without .gro extension (e.g., ice_ih_195K_1.36MPa_c5)
        top_path = path.with_name(path.stem + '.top')
        itp_path = path.with_name(path.stem + '.itp')
        
        try:
            # Write .gro file using gromacs_writer
            from quickice.output.gromacs_writer import write_gro_file
            write_gro_file(candidate, str(path))
            
            # Write .top file
            from quickice.output.gromacs_writer import write_top_file
            write_top_file(candidate, str(top_path))
            
            # Copy .itp file from data directory
            import shutil
            from quickice.output.gromacs_writer import get_tip4p_itp_path
            itp_source = get_tip4p_itp_path()
            shutil.copy(itp_source, itp_path)
            
            return True
        except Exception as e:
            QMessageBox.critical(self.parent, "Export Error", f"Failed: {e}")
            return False


def _get_guest_itp_path(guest_type: str) -> Path:
    """Get the path to a bundled guest .itp file.
    
    Args:
        guest_type: Guest molecule type ("ch4", "thf")
    
    Returns:
        Path to the guest .itp file in the data directory
    
    Raises:
        FileNotFoundError: If no .itp file exists for the guest type
    """
    import quickice
    package_dir = Path(quickice.__file__).parent
    itp_path = package_dir / "data" / f"{guest_type}.itp"
    
    if itp_path.exists():
        return itp_path
    
    # Fallback to project root (for development)
    fallback = Path(__file__).parent.parent / "data" / f"{guest_type}.itp"
    if fallback.exists():
        return fallback
    
    raise FileNotFoundError(f"No .itp file found for guest type: {guest_type}")


class InterfaceGROMACSExporter:
    """Handle GROMACS file export for interface structures (.gro, .top, .itp).
    
    Per CONTEXT.md:
    - Same SOL molecule type for both ice and water phases
    - Ice molecules normalized from 3-atom to 4-atom TIP4P-ICE format at export time
    - Continuous residue numbering: ice 1..N_ice, water N_ice+1..N_ice+N_water
    - Single combined SOL count in [molecules] section
    """
    
    def __init__(self, parent_widget):
        """Initialize interface GROMACS exporter.
        
        Args:
            parent_widget: Parent widget for dialog centering
        """
        self.parent = parent_widget
    
    def export_interface_gromacs(self, interface_structure: InterfaceStructure) -> bool:
        """Export interface structure to GROMACS format.

        Args:
            interface_structure: InterfaceStructure with ice and water phases

        Returns:
            True if export succeeded

        Per CONTEXT.md:
        - Default filename format: interface_{mode}.gro
        - Generates companion .top and .itp files
        """
        # Generate default filename with mode info
        mode = interface_structure.mode
        default_name = f"interface_{mode}.gro"

        # Show save dialog for .gro file
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self.parent,
            "Export Interface for GROMACS",
            default_name,
            "GRO Files (*.gro);;All Files (*)",
            "GRO Files (*.gro)"
        )
        
        if not filepath:
            return False
        
        # Ensure .gro extension
        path = Path(filepath)
        if path.suffix.lower() != '.gro':
            path = path.with_suffix('.gro')
        
        # Generate companion filenames using stem (handles dots in filename correctly)
        top_path = path.with_name(path.stem + '.top')
        itp_path = path.with_name(path.stem + '.itp')
        
        try:
            # Write .gro file using gromacs_writer
            from quickice.output.gromacs_writer import write_interface_gro_file
            write_interface_gro_file(interface_structure, str(path))
            
            # Write .top file
            from quickice.output.gromacs_writer import write_interface_top_file
            write_interface_top_file(interface_structure, str(top_path))
            
            # Copy .itp files from data directory
            import shutil
            from quickice.output.gromacs_writer import get_tip4p_itp_path
            
            # Copy water .itp file (must match the #include "tip4p-ice.itp" in .top file)
            water_itp_source = get_tip4p_itp_path()
            water_itp_dest = path.with_name("tip4p-ice.itp")
            shutil.copy(water_itp_source, water_itp_dest)
            
            # Copy guest .itp file if guests are present
            if interface_structure.guest_nmolecules > 0 and interface_structure.guest_atom_count > 0:
                # Determine guest type from first guest atom name
                ice_end = interface_structure.ice_atom_count
                first_guest_atom = interface_structure.atom_names[ice_end] if ice_end < len(interface_structure.atom_names) else "C"
                
                if first_guest_atom in ["Me", "C"]:
                    guest_type = "ch4"
                elif first_guest_atom in ["O", "c"]:
                    guest_type = "thf"
                else:
                    guest_type = None
                
                if guest_type:
                    try:
                        guest_itp_source = _get_guest_itp_path(guest_type)
                        guest_itp_dest = path.with_name(f"{guest_type}.itp")
                        shutil.copy(guest_itp_source, guest_itp_dest)
                    except FileNotFoundError:
                        # Guest .itp file not found - will cause GROMACS to fail
                        # but don't block export, user can add manually
                        pass
            
            return True
        except Exception as e:
            QMessageBox.critical(self.parent, "Export Error", f"Failed: {e}")
            return False
