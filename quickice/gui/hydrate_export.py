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
            
            # Create registry for unique moleculetype naming.
            # Built-in guests register into it (CH4 -> "CH4_H", THF -> "THF_H");
            # custom guests leave it empty (writers use custom_guest_info instead).
            #
            # Phase 42-05: iterate config.cage_guest_assignments (one entry per
            # cage key). Built-in guests (ch4/thf) register in the registry and
            # use the bundled _hydrate.itp; custom guests append to the
            # custom_guest_info list + itp_files dict and are transformed per
            # ITP. register_hydrate_guest is idempotent for the same guest
            # (verified in moleculetype_registry.py lines 62-65), so a legacy
            # single-guest HydrateConfig synthesizing small+large with the
            # same ch4 guest registers CH4_H once (second call is a no-op).
            registry = MoleculetypeRegistry()
            custom_guest_info: list[dict] = []
            itp_files: dict[str, str] = {}
            # (source_itp_path, residue_name_for_transform) per assignment.
            custom_guest_itps: list[tuple[Path, str]] = []

            for _cage_key, assignment in config.cage_guest_assignments.items():
                if assignment.is_custom_guest:
                    # Custom guest: validate, collect for custom_guest_info +
                    # transform. Residue name "{guest_residue_name}_H" must be
                    # <=5 chars (e.g. "MOL_H") so validate_gro_residue_name
                    # passes and the ITP transform does not ValueError on a
                    # long guest_type like "etoh_mix" -> "ETOH_MIX_H" (9 chars).
                    guest_itp_path = Path(assignment.guest_itp_path)
                    if not guest_itp_path.exists():
                        raise FileNotFoundError(
                            f"Custom guest ITP not found: {guest_itp_path}"
                        )
                    residue_name_h = f"{assignment.guest_residue_name}_H"
                    custom_guest_info.append({
                        "mol_type": assignment.guest_type,
                        "residue_name": residue_name_h,
                        "itp_path": guest_itp_path,
                    })
                    itp_files[assignment.guest_type] = guest_itp_path.name
                    custom_guest_itps.append(
                        (guest_itp_path, assignment.guest_residue_name)
                    )
                else:
                    # Built-in guest (ch4/thf): register + use bundled
                    # _hydrate.itp. register_hydrate_guest is idempotent for
                    # the same guest (returns existing name on duplicate), so
                    # a legacy single-guest config synthesizing small+large
                    # with the same ch4 guest registers CH4_H exactly once.
                    guest_itp_path = _get_hydrate_guest_itp_path(
                        assignment.guest_type
                    )
                    registry.register_hydrate_guest(
                        assignment.guest_type.upper()
                    )
                    itp_files[assignment.guest_type] = guest_itp_path.name
                    # Built-in ITPs are pre-transformed (moleculetype "CH4_H",
                    # [atoms] resname "CH4_H"); transform_guest_itp is
                    # idempotent on them (STATE [38-04] "read-transform-write":
                    # Step 2 line.replace(old_name, new_name, 1) is a no-op
                    # when old_name == new_name == "CH4_H"; Step 3 rewrites
                    # resname to the same value). Use guest_type.upper() as
                    # the transform name so new_name = "CH4_H" matches the
                    # pre-transformed ITP.
                    custom_guest_itps.append(
                        (guest_itp_path, assignment.guest_type.upper())
                    )

            # custom_guest_info is [] when all guests are built-in (writers'
            # None-equivalent — list[dict] API treats None and [] identically
            # via the `for ci in (custom_guest_info or [])` loop).
            cgi_for_writers = custom_guest_info if custom_guest_info else None

            # Write .gro file
            write_multi_molecule_gro_file(
                structure.positions,
                structure.molecule_index,
                structure.cell,
                str(path),
                f"Hydrate structure ({lattice} + {guest}) exported by QuickIce",
                atom_names=structure.atom_names,
                registry=registry,
                custom_guest_info=cgi_for_writers,
            )

            # Write .top file with #include for guest .itp
            write_multi_molecule_top_file(
                structure.molecule_index,
                str(top_path),
                f"Hydrate ({lattice} + {guest})",
                itp_files=itp_files,
                registry=registry,
                custom_guest_info=cgi_for_writers,
            )

            # Copy TIP4P-ICE .itp file to export directory
            water_itp_path = path.with_name("tip4p-ice.itp")
            shutil.copy(tip4p_itp_path, water_itp_path)

            # Transform + copy each guest .itp (one per assignment).
            # Built-in guest ITPs are pre-transformed so this is a no-op for
            # them; for custom guests it produces the {residue_name}_H-renamed
            # ITP that matches the .gro/.top residue names.
            for guest_itp_path, guest_name_for_transform in custom_guest_itps:
                guest_itp_content = guest_itp_path.read_text()
                transformed_content = transform_guest_itp(
                    guest_itp_content, guest_name_for_transform, suffix="_H"
                )
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