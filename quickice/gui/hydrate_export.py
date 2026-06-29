"""GROMACS export for hydrate structures.

Provides HydrateGROMACSExporter class to export hydrate structures
to GROMACS format (.gro + .top + guest .itp files) with TIP4P-ice water
and bundled GAFF guest parameters.
"""

import shutil
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from quickice.structure_generation.types import HydrateStructure, HydrateConfig
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry


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


def _get_hydrate_guest_itp_path(guest_type: str) -> Path:
    """Get the path to a hydrate-specific guest .itp file.
    
    Args:
        guest_type: Guest molecule type ("ch4", "thf")
    
    Returns:
        Path to the hydrate guest .itp file (e.g., ch4_hydrate.itp)
    
    Raises:
        FileNotFoundError: If no hydrate .itp file exists for the guest type
    """
    import quickice
    package_dir = Path(quickice.__file__).parent
    itp_path = package_dir / "data" / f"{guest_type}_hydrate.itp"
    
    if itp_path.exists():
        return itp_path
    
    # Fallback to project root (for development)
    fallback = Path(__file__).parent.parent / "data" / f"{guest_type}_hydrate.itp"
    if fallback.exists():
        return fallback
    
    raise FileNotFoundError(f"No hydrate .itp file found for guest type: {guest_type}")


class HydrateGROMACSExporter:
    """Handle GROMACS file export for hydrate structures (.gro, .top, guest .itp).
    
    Per plan 31-05:
    - Exports hydrate structure to GROMACS format
    - Generates default filename: hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro
    - Writes .gro file using write_multi_molecule_gro_file()
    - Writes .top file using write_multi_molecule_top_file() with guest .itp files
    - Copies bundled guest .itp files to export directory
    """
    
    def __init__(self, parent_widget):
        """Initialize hydrate GROMACS exporter.
        
        Args:
            parent_widget: Parent widget for dialog centering
        """
        self.parent = parent_widget
    
    def export_hydrate(self, structure: HydrateStructure, config: HydrateConfig) -> bool:
        """Export hydrate structure to GROMACS format.
        
        Args:
            structure: HydrateStructure with positions, cell, and molecule_index
            config: HydrateConfig with lattice and guest type settings
        
        Returns:
            True if export succeeded, False on cancelled or error
        
        Generates:
            - .gro file: Coordinates with TIP4P-ice water + guests
            - .top file: Topology with #include for guest .itp files
            - Guest .itp files: Copied to export directory
        """
        # Generate default filename: hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro
        lattice = config.lattice_type
        guest = config.guest_type
        nx, ny, nz = config.supercell_x, config.supercell_y, config.supercell_z
        default_name = f"hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro"
        
        # Show save dialog for .gro file
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self.parent,
            "Export Hydrate for GROMACS",
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
        
        # Generate companion filenames using stem
        top_path = path.with_name(path.stem + '.top')
        
        try:
            # Import GROMACS writer functions
            from quickice.output.gromacs_writer import (
                write_multi_molecule_gro_file,
                write_multi_molecule_top_file,
                get_tip4p_itp_path,
                transform_guest_itp,
            )
            
            # Get TIP4P-ICE itp path for water
            tip4p_itp_path = get_tip4p_itp_path()
            
            # Get guest itp path (hydrate-specific)
            guest_itp_path = _get_hydrate_guest_itp_path(config.guest_type)
            
            # Create registry for unique moleculetype naming
            registry = MoleculetypeRegistry()
            
            # Register guest molecule as hydrate guest
            # This ensures CH4 gets registered as "CH4_H", THF as "THF_H"
            guest_upper = config.guest_type.upper()
            registry.register_hydrate_guest(guest_upper)
            
            # Write .gro file
            write_multi_molecule_gro_file(
                structure.positions,
                structure.molecule_index,
                structure.cell,
                str(path),
                f"Hydrate structure ({lattice} + {guest}) exported by QuickIce",
                atom_names=structure.atom_names,
                registry=registry,
             )

            # Build itp_files mapping for .top file
            # Maps internal guest type to itp filename (not full path - use relative path in #include)
            itp_files = {config.guest_type: guest_itp_path.name}
            
            # Write .top file with #include for guest .itp
            write_multi_molecule_top_file(
                structure.molecule_index,
                str(top_path),
                f"Hydrate ({lattice} + {guest})",
                itp_files=itp_files,
                registry=registry,
            )
            
            # Copy TIP4P-ICE .itp file to export directory
            water_itp_path = path.with_name("tip4p-ice.itp")
            shutil.copy(tip4p_itp_path, water_itp_path)
            
            # Copy guest .itp file to export directory with ITP transformation
            # (_H suffix, atomtypes comment-out; no-op for pre-transformed built-in ITPs)
            guest_itp_content = guest_itp_path.read_text()
            transformed_content = transform_guest_itp(guest_itp_content, guest_upper, suffix="_H")
            guest_dest_path = path.with_name(guest_itp_path.name)
            guest_dest_path.write_text(transformed_content)
            
            return True
            
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Export Error",
                f"Failed to export hydrate structure:\n\n{str(e)}"
            )
            return False