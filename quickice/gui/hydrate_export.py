"""GROMACS export for hydrate structures.

Provides HydrateGROMACSExporter class to export hydrate structures
to GROMACS format (.gro + .top + guest .itp files) with TIP4P-ice water
and bundled GAFF guest parameters.
"""

import shutil
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from quickice.structure_generation.types import (
    CageGuestAssignment,
    GuestDescriptor,
    GUEST_MOLECULES,
    HydrateConfig,
    HydrateStructure,
)
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
from quickice.gui.export import _build_default_path, _remember_export_dir


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
        # Use an ABSOLUTE path so QFileDialog opens in a predictable directory
        # (the last-used export dir, defaulting to home) with the correct
        # filename pre-selected. A bare filename made the starting directory
        # unpredictable and let the user accidentally overwrite an unrelated
        # file (e.g. an ion export) — see .planning/debug/export-filename-ux.md.
        lattice = config.lattice_type
        guest = config.guest_type
        nx, ny, nz = config.supercell_x, config.supercell_y, config.supercell_z
        default_name = _build_default_path(
            self.parent,
            f"hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro",
        )
        
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
        _remember_export_dir(self.parent, filepath)
        
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
            # Phase 42-08 fix: drive ITP staging from the STRUCTURE (what's
            # actually being exported — structure.molecule_index + the
            # .gro/.top writers iterate it) rather than config.cage_guest_assignments
            # (what the panel says). When the user changes the lattice without
            # regenerating, config.cage_guest_assignments becomes empty (sTprime
            # has no cage rows) but structure.molecule_index still carries the
            # old mixed guests — driving from structure ensures the staged ITPs
            # always match the exported .gro/.top content regardless of
            # config/structure desync. register_hydrate_guest is idempotent for
            # the same guest (returns existing name on duplicate), so a legacy
            # single-guest config synthesizing small+large with the same ch4
            # registers CH4_H once (second call is a no-op).
            registry = MoleculetypeRegistry()
            custom_guest_info: list[dict] = []
            itp_files: dict[str, str] = {}
            # (source_itp_path, residue_name_for_transform) per guest ITP.
            custom_guest_itps: list[tuple[Path, str]] = []

            # Unique guest mol_types in the structure (excluding water), in
            # first-occurrence insertion order so ITP staging matches the
            # .gro/.top writer output (the writers iterate molecule_index).
            unique_mol_types: list[str] = []
            _seen_mol: set[str] = set()
            for _m in structure.molecule_index:
                if _m.mol_type != "water" and _m.mol_type not in _seen_mol:
                    unique_mol_types.append(_m.mol_type)
                    _seen_mol.add(_m.mol_type)

            # Config lookup for custom ITP paths — config is the source of
            # WHERE the ITP file is; the structure is the source of WHAT to
            # stage. Keyed by guest_type (= mol_type) for O(1) lookup.
            _config_by_moltype: dict[str, CageGuestAssignment] = {
                a.guest_type: a for a in config.cage_guest_assignments.values()
            }
            # Descriptor lookup for custom guest residue names. Keyed by
            # mol_type. Empty for pre-Phase-42 structures (no
            # guest_descriptors) — handled by the fallback below.
            _descriptor_by_moltype: dict[str, GuestDescriptor] = {
                gd.mol_type: gd for gd in structure.guest_descriptors
            }

            if unique_mol_types and not structure.guest_descriptors:
                # Backward-compat fallback for pre-Phase-42 structures: drive
                # ITP staging from config.cage_guest_assignments (the old
                # logic). Such structures lack guest_descriptors, so the
                # structure cannot resolve custom-guest residue names. The
                # desync bug only manifests with mixed-guest structures (which
                # require guest_descriptors), so the old config-driven path is
                # safe here — pre-Phase-42 structures + config are always
                # consistent.
                for _cage_key, assignment in config.cage_guest_assignments.items():
                    if assignment.is_custom_guest:
                        # Custom guest: validate, collect for custom_guest_info +
                        # transform. Residue name "{guest_residue_name}_H" must
                        # be <=5 chars (e.g. "MOL_H") so validate_gro_residue_name
                        # passes and the ITP transform does not ValueError on a
                        # long guest_type like "etoh_mix" -> "ETOH_MIX_H".
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
                        # _hydrate.itp. register_hydrate_guest is idempotent.
                        guest_itp_path = _get_hydrate_guest_itp_path(
                            assignment.guest_type
                        )
                        registry.register_hydrate_guest(
                            assignment.guest_type.upper()
                        )
                        itp_files[assignment.guest_type] = guest_itp_path.name
                        # Built-in ITPs are pre-transformed (moleculetype
                        # "CH4_H", [atoms] resname "CH4_H"); transform_guest_itp
                        # is idempotent on them. Use guest_type.upper() as the
                        # transform name so new_name = "CH4_H" matches the
                        # pre-transformed ITP.
                        custom_guest_itps.append(
                            (guest_itp_path, assignment.guest_type.upper())
                        )
            else:
                # Structure-driven path (Phase 42-08 fix): iterate the unique
                # guest mol_types actually present in structure.molecule_index.
                # This is what the .gro/.top writers iterate, so the staged
                # ITPs always match the exported content — even when config is
                # out of sync (empty after a lattice change without regen).
                # When the structure has no guests (water-only), unique_mol_types
                # is empty and this loop is a no-op (no guest ITPs needed).
                for mol_type in unique_mol_types:
                    if mol_type in GUEST_MOLECULES:
                        # Built-in guest (ch4/thf): register + use the bundled
                        # _hydrate.itp. register_hydrate_guest is idempotent.
                        guest_itp_path = _get_hydrate_guest_itp_path(mol_type)
                        registry.register_hydrate_guest(mol_type.upper())
                        itp_files[mol_type] = guest_itp_path.name
                        # Built-in ITPs are pre-transformed (moleculetype
                        # "CH4_H", [atoms] resname "CH4_H"); transform_guest_itp
                        # is idempotent on them (Step 2 line.replace is a no-op
                        # when old==new=="CH4_H"; Step 3 rewrites resname to
                        # the same value). Use mol_type.upper() as the transform
                        # name so new_name = "CH4_H" matches the pre-transformed
                        # ITP.
                        custom_guest_itps.append(
                            (guest_itp_path, mol_type.upper())
                        )
                    else:
                        # Custom guest: the descriptor gives residue_name
                        # (WHAT to name it) and config gives the ITP path
                        # (WHERE the source ITP file is). The structure is the
                        # source of WHAT to stage; config is the source of
                        # WHERE the ITP file is. Both must resolve — a custom
                        # guest in the structure but absent from config means
                        # the export cannot locate its ITP.
                        descriptor = _descriptor_by_moltype.get(mol_type)
                        if descriptor is None:
                            raise ValueError(
                                f"Custom guest mol_type '{mol_type}' present "
                                f"in structure.molecule_index has no matching "
                                f"entry in structure.guest_descriptors — cannot "
                                f"resolve residue_name for ITP staging."
                            )
                        assignment = _config_by_moltype.get(mol_type)
                        if assignment is None or not assignment.guest_itp_path:
                            raise FileNotFoundError(
                                f"Custom guest mol_type '{mol_type}' present "
                                f"in structure.molecule_index has no ITP path "
                                f"in config.cage_guest_assignments — cannot "
                                f"stage ITP."
                            )
                        guest_itp_path = Path(assignment.guest_itp_path)
                        if not guest_itp_path.exists():
                            raise FileNotFoundError(
                                f"Custom guest ITP not found: {guest_itp_path}"
                            )
                        residue_name_h = f"{descriptor.guest_residue_name}_H"
                        custom_guest_info.append({
                            "mol_type": mol_type,
                            "residue_name": residue_name_h,
                            "itp_path": guest_itp_path,
                        })
                        itp_files[mol_type] = guest_itp_path.name
                        custom_guest_itps.append(
                            (guest_itp_path, descriptor.guest_residue_name)
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