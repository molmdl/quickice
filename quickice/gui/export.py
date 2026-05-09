"""Export handlers for PDB files, phase diagram images, and 3D viewport screenshots.

This module provides exporter classes for saving user work to standard file formats:
- PDBExporter: Save ranked ice structure candidates to PDB format
- DiagramExporter: Export phase diagram to PNG or SVG images
- ViewportExporter: Capture 3D molecular viewport to image files
"""

import logging
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
from quickice.structure_generation.types import Candidate, InterfaceStructure, IonStructure, SoluteStructure, CustomMoleculeStructure

logger = logging.getLogger(__name__)


class SoluteGROMACSExporter:
    """Handle GROMACS file export for solute structures.
    
    Exports: ice + water + solutes (CH4 or THF).
    """
    
    def __init__(self, parent_widget):
        """Initialize solute GROMACS exporter."""
        self.parent = parent_widget
    
    def export_solute_gromacs(self, solute_structure: SoluteStructure) -> bool:
        """Export solute structure to GROMACS format.

        Args:
            solute_structure: SoluteStructure with solute positions and interface

        Returns:
            True if export succeeded
        """
        # Generate default filename with solute type and count
        solute_type = solute_structure.solute_type.lower()
        n_molecules = solute_structure.n_molecules
        default_name = f"solute_{solute_type}_{n_molecules}molecules.gro"

        # Show save dialog for .gro file
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self.parent,
            "Export Solutes for GROMACS",
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
            # Combine interface structure with solutes for export
            interface = solute_structure.interface_structure
            
            # Build combined structure: ice + water + solutes
            all_positions = np.vstack([
                interface.positions,
                solute_structure.positions
            ])
            all_atom_names = interface.atom_names + solute_structure.atom_names
            
            # Write .gro file
            from quickice.output.gromacs_writer import write_gro_file
            write_gro_file(all_positions, all_atom_names, solute_structure.cell, str(path))
            
            # Write .top file with moleculetype names from registry
            from quickice.output.gromacs_writer import write_top_file
            # Build molecule index for combined structure
            molecule_index = []
            
            # Add ice molecules
            ice_nmolecules = interface.ice_nmolecules
            ice_atoms_per_molecule = interface.ice_atom_count // ice_nmolecules if ice_nmolecules > 0 else 0
            idx = 0
            for i in range(ice_nmolecules):
                molecule_index.append({
                    'mol_type': 'ICE_IH',
                    'start_idx': idx,
                    'count': ice_atoms_per_molecule
                })
                idx += ice_atoms_per_molecule
            
            # Add water molecules
            water_nmolecules = interface.water_nmolecules
            water_atoms_per_molecule = interface.water_atom_count // water_nmolecules if water_nmolecules > 0 else 0
            for i in range(water_nmolecules):
                molecule_index.append({
                    'mol_type': 'WATER_LIQ',
                    'start_idx': idx,
                    'count': water_atoms_per_molecule
                })
                idx += water_atoms_per_molecule
            
            # Add solute molecules
            solute_type = solute_structure.solute_type
            moleculetype_name = solute_structure.registry.get_gromacs_name(f"liquid_{solute_type}")
            for start, end in solute_structure.molecule_indices:
                molecule_index.append({
                    'mol_type': moleculetype_name,
                    'start_idx': interface.ice_atom_count + interface.water_atom_count + start,
                    'count': end - start
                })
            
            write_top_file(all_positions, all_atom_names, solute_structure.cell, str(top_path), 
                          molecule_index, registry=solute_structure.registry)
            
            # Copy water topology file (tip4p-ice.itp) for water molecules
            import shutil
            from quickice.output.gromacs_writer import get_tip4p_itp_path
            itp_source = get_tip4p_itp_path()
            water_itp_path = path.with_name("tip4p-ice.itp")
            shutil.copy(itp_source, water_itp_path)
            
            # Copy solute .itp file (liquid solutes use _liquid.itp files)
            # Solute tab only handles liquid solutes, always use _liquid.itp
            solute_type_lower = solute_type.lower()
            solute_itp_name = f"{solute_type_lower}_liquid.itp"

            from pathlib import Path as FilePath
            solute_itp_source = FilePath(__file__).parent.parent / "data" / solute_itp_name
            if solute_itp_source.exists():
                solute_itp_dest = path.with_name(solute_itp_name)
                shutil.copy(solute_itp_source, solute_itp_dest)
            
            return True
        except Exception as e:
            QMessageBox.critical(self.parent, "Export Error", f"Failed: {e}")
            import traceback
            traceback.print_exc()
            return False


class CustomMoleculeGROMACSExporter:
    """Handle GROMACS file export for custom molecule structures.
    
    Exports: ice + water + custom molecules (user-provided .gro/.itp).
    Bundles custom .itp file to output directory.
    """
    
    def __init__(self, parent_widget):
        """Initialize custom molecule GROMACS exporter."""
        self.parent = parent_widget
    
    def export_custom_molecule_gromacs(self, custom_structure) -> bool:
        """Export custom molecule structure to GROMACS format.
        
        Exports COMPLETE system: ice + water + custom molecules.
        Files: .gro, .top, and custom .itp bundled.
        
        Args:
            custom_structure: CustomMoleculeStructure with complete system data
        
        Returns:
            True if export succeeded
        """
        # Generate default filename
        moleculetype_name = custom_structure.moleculetype_name
        n_molecules = custom_structure.custom_molecule_count
        default_name = f"custom_system_{moleculetype_name}_{n_molecules}molecules.gro"
        
        # Show save dialog for .gro file
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self.parent,
            "Export Custom Molecule System for GROMACS",
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
        
        # Generate companion filename
        top_path = path.with_name(path.stem + '.top')
        
        try:
            # Write .gro file with complete system
            from quickice.output.gromacs_writer import (
                write_custom_molecule_gro_file,
                write_custom_molecule_top_file
            )
            
            write_custom_molecule_gro_file(custom_structure, str(path))
            write_custom_molecule_top_file(custom_structure, str(top_path))
            
            # Copy custom .itp file to output directory
            import shutil
            custom_itp_dest = path.with_name(custom_structure.itp_path.name)
            shutil.copy(custom_structure.itp_path, custom_itp_dest)
            
            logger.info(f"Exported custom molecule system: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            QMessageBox.critical(self.parent, "Export Error", f"Failed: {e}")
            import traceback
            traceback.print_exc()
            return False


class IonGROMACSExporter:
    """Handle GROMACS file export for ion structures.
    
    Per Issue 1: Exports ion structure from Ion tab to GROMACS format.
    Exports: ice + water + ions (Na+, Cl-) + solutes (if present).
    """
    
    def __init__(self, parent_widget):
        """Initialize ion GROMACS exporter."""
        self.parent = parent_widget
    
    def export_ion_gromacs(self, ion_structure: IonStructure) -> bool:
        """Export ion structure to GROMACS format.

        Args:
            ion_structure: IonStructure with water + ion positions (+ solutes if present)

        Returns:
            True if export succeeded
        """
        # Generate default filename with ion counts
        na_count = ion_structure.na_count
        cl_count = ion_structure.cl_count
        
        # Include solute info in filename if present
        if ion_structure.solute_n_molecules > 0:
            default_name = f"ions_{na_count}na_{cl_count}cl_with_{ion_structure.solute_n_molecules}{ion_structure.solute_type.lower()}.gro"
        else:
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
                # Use the detect_guest_type_from_atoms function for consistent detection
                from quickice.output.gromacs_writer import detect_guest_type_from_atoms
                
                guest_type = None
                
                # Check molecule_index for guest molecule type
                for mol in ion_structure.molecule_index:
                    if mol.mol_type == "guest":
                        # Get atom names for this guest molecule
                        mol_atom_names = ion_structure.atom_names[mol.start_idx:mol.start_idx + mol.count]
                        guest_type = detect_guest_type_from_atoms(mol_atom_names)
                        if guest_type:
                            break
                
                # Fallback: use heuristic based on atom count
                if guest_type is None and ion_structure.guest_nmolecules > 0:
                    atoms_per_guest = ion_structure.guest_atom_count // ion_structure.guest_nmolecules
                    if atoms_per_guest >= 10:
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
            
            # Copy solute .itp file if solutes are present (liquid solutes use _liquid.itp)
            if ion_structure.solute_n_molecules > 0 and ion_structure.solute_positions is not None:
                solute_type_lower = ion_structure.solute_type.lower()
                solute_itp_name = f"{solute_type_lower}_liquid.itp"

                from pathlib import Path as FilePath
                solute_itp_source = FilePath(__file__).parent.parent / "data" / solute_itp_name
                if solute_itp_source.exists():
                    solute_itp_dest = path.with_name(solute_itp_name)
                    shutil.copy(solute_itp_source, solute_itp_dest)
            
            # Copy custom molecule .itp file if custom molecules are present
            if ion_structure.custom_molecule_count > 0 and ion_structure.custom_molecule_positions is not None:
                if ion_structure.custom_itp_path and Path(ion_structure.custom_itp_path).exists():
                    custom_itp_source = Path(ion_structure.custom_itp_path)
                    custom_itp_dest = path.with_name(custom_itp_source.name)
                    shutil.copy(custom_itp_source, custom_itp_dest)
            
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
                # Determine guest type from atom names
                # Guest atoms start at ice_atom_count + water_atom_count (after commit 90afe86)
                # Use the detect_guest_type_from_atoms function for consistent detection
                from quickice.output.gromacs_writer import detect_guest_type_from_atoms
                
                guest_start = interface_structure.ice_atom_count + interface_structure.water_atom_count
                guest_atom_names = interface_structure.atom_names[guest_start:guest_start + interface_structure.guest_atom_count]
                guest_type = detect_guest_type_from_atoms(guest_atom_names)
                
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
