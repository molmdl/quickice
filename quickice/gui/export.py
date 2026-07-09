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


def _detect_guest_type_from_structure(structure) -> str | None:
    """Detect guest molecule type from a structure using molecule_index.

    Uses the same detection logic as write_ion_top_file() for consistency:
    1. Check molecule_index for mol_type == "guest" entries
    2. Detect type from atom names of first guest molecule
    3. Fallback: heuristic based on guest_atom_count / guest_nmolecules

    This function is robust even when guest_nmolecules == 0 on the structure
    (e.g., when CustomMoleculeStructure is used as a source and the field
    was not propagated), because it uses molecule_index as the primary source.

    Args:
        structure: Any structure with molecule_index, atom_names,
                   guest_nmolecules, and guest_atom_count attributes.

    Returns:
        Guest type string ('ch4' or 'thf') or None if no guest detected.
    """
    from quickice.output.gromacs_writer import detect_guest_type_from_atoms

    # Primary: check molecule_index for guest entries (consistent with write_ion_top_file)
    guest_count = sum(1 for m in structure.molecule_index if m.mol_type == "guest")
    guest_atom_count = getattr(structure, 'guest_atom_count', 0)

    if guest_count > 0 and guest_atom_count > 0:
        for mol in structure.molecule_index:
            if mol.mol_type == "guest":
                mol_atom_names = structure.atom_names[mol.start_idx:mol.start_idx + mol.count]
                guest_type = detect_guest_type_from_atoms(mol_atom_names)
                if guest_type:
                    return guest_type

    # Fallback: heuristic based on atom count when guest_nmolecules is available
    guest_nmolecules = getattr(structure, 'guest_nmolecules', 0)
    if guest_atom_count > 0 and guest_nmolecules > 0:
        atoms_per_guest = guest_atom_count // guest_nmolecules
        return "thf" if atoms_per_guest >= 10 else "ch4"

    return None


def _build_default_path(parent, filename: str) -> str:
    """Build an absolute default path for ``QFileDialog.getSaveFileName``.

    QFileDialog.getSaveFileName interprets a bare filename (no directory) as
    relative to the process CWD / Qt's last-used directory, which makes the
    dialog's starting location unpredictable. With a bare default the dialog
    may open in a directory containing unrelated files the user could
    accidentally click to overwrite (see ``.planning/debug/export-filename-ux.md``).

    This returns ``str(last_export_dir / filename)`` so the dialog always
    opens in a predictable directory with the correct filename pre-selected.
    The last-export directory lives on ``parent`` (the MainWindow) and is
    updated by :func:`_remember_export_dir` after each successful selection,
    defaulting to the current working directory on first launch — matching the
    original bare-filename behavior (Qt resolved bare names relative to CWD)
    and typical scientific CLI tool conventions (the user ``cd``'d to their
    project directory and expects output there). Subsequent exports reuse the
    last-used directory so the user does not have to re-navigate each time.
    """
    last_dir = getattr(parent, "_last_export_dir", None)
    if last_dir is None:
        last_dir = Path.cwd()
    return str(last_dir / filename)


def _remember_export_dir(parent, filepath: str) -> None:
    """Remember the directory of a chosen export path on ``parent``.

    Call after a (non-cancelled) QFileDialog selection so the next export
    opens in the same directory. No-op on an empty path (cancel) or when
    ``parent`` is ``None`` (e.g. unit tests constructing an exporter without
    a real widget parent — there is nowhere to persist the directory, but the
    export itself is unaffected).
    """
    if filepath and parent is not None:
        parent._last_export_dir = Path(filepath).parent


class SoluteGROMACSExporter:
    """Handle GROMACS file export for solute structures.
    
    Exports: ice + water + solutes (CH4 or THF).
    Also handles guest molecules (from hydrate cages) and custom molecules
    (propagated from custom molecule tab) if present in the source interface.
    
    Files produced:
    - .gro file with molecules in order: SOL (ice+water), guest, custom, solute
    - .top file with matching [molecules] section and #include directives
    - tip4p-ice.itp (copied)
    - {solute}_liquid.itp (copied with atomtypes commented)
    - {guest}_hydrate.itp (copied if guests present)
    - {custom}.itp (copied with atomtypes commented if custom molecules present)
    """
    
    def __init__(self, parent_widget):
        """Initialize solute GROMACS exporter."""
        self.parent = parent_widget
    
    def export_solute_gromacs(
        self, solute_structure: SoluteStructure, hydrate_config=None
    ) -> bool:
        """Export solute structure to GROMACS format.

        Args:
            solute_structure: SoluteStructure with solute positions and interface
            hydrate_config: Optional :class:`HydrateConfig` that produced the
                hydrate the solute's interface was assembled from. When the
                interface carries custom guest molecules (e.g. a custom
                ethanol hydrate exported via the Solute tab), this drives the
                config-driven ITP staging via :func:`quickice.output.guest_info._stage_hydrate_guest_itps`
                (plan 44.1-08): it builds ``custom_guest_info`` from the
                config, transforms + writes each custom ITP with the ``_H``
                suffix, and threads ``custom_guest_info`` to both
                :func:`write_solute_gro_file` and :func:`write_solute_top_file`
                (extended in plan 44.1-11 to accept the kwarg). When ``None``
                (built-in ch4 / thf path) or a config with only built-in cage
                assignments, the helper copies the bundled pre-transformed
                ``{guest_type}_hydrate.itp`` — byte-identical to the previous
                built-in path.

        Returns:
            True if export succeeded
        """
        # Generate default filename with solute type and count
        solute_type = solute_structure.solute_type.lower()
        n_molecules = solute_structure.n_molecules
        default_name = _build_default_path(
            self.parent, f"solute_{solute_type}_{n_molecules}molecules.gro"
        )

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
        _remember_export_dir(self.parent, filepath)
        
        # Ensure .gro extension
        path = Path(filepath)
        if path.suffix.lower() != '.gro':
            path = path.with_suffix('.gro')
        
        # Generate companion filename using stem
        top_path = path.with_name(path.stem + '.top')
        
        try:
            # Stage hydrate guest ITPs (config-driven, plan 44.1-08/11).
            # Replaces the broken _detect_guest_type_from_structure (returns
            # None for custom guests like etoh_e2e) + shutil.copy(
            # {guest_type}_hydrate.itp) (FileNotFoundError for custom) pattern.
            # The helper handles both paths: custom guests get a transformed
            # ITP (moleculetype {base}_H, [atomtypes] commented, [atoms] resname
            # {base}_H) written to path.parent; built-in ch4/thf get the
            # bundled pre-transformed {guest_type}_hydrate.itp copied across.
            # The solute structure carries interface_structure (types.py
            # SoluteStructure.interface_structure); reach guest presence via
            # that interface's guest_atom_count / guest_nmolecules so the
            # helper's presence gate short-circuits no-guest exports (e.g.
            # plain ice+water interface + solutes) without touching the
            # filesystem. Matches the InterfaceGROMACSExporter wiring (44.1-09).
            from quickice.output.guest_info import _stage_hydrate_guest_itps
            _iface = getattr(solute_structure, 'interface_structure', solute_structure)
            custom_guest_info, _staged_guest_itps = _stage_hydrate_guest_itps(
                path.parent, hydrate_config, _iface,
                guest_atom_count=getattr(_iface, 'guest_atom_count', 0),
                guest_nmolecules=getattr(_iface, 'guest_nmolecules', 0),
            )

            # Write .gro file using dedicated solute writer
            from quickice.output.gromacs_writer import write_solute_gro_file
            write_solute_gro_file(
                solute_structure, str(path), custom_guest_info=custom_guest_info
            )
            
            # Write .top file using dedicated solute writer
            from quickice.output.gromacs_writer import write_solute_top_file
            write_solute_top_file(
                solute_structure, str(top_path), custom_guest_info=custom_guest_info
            )
            
            # Copy water topology file (tip4p-ice.itp) for water molecules
            import shutil
            from quickice.output.gromacs_writer import get_tip4p_itp_path
            itp_source = get_tip4p_itp_path()
            water_itp_path = path.with_name("tip4p-ice.itp")
            shutil.copy(itp_source, water_itp_path)
            
            # Guest .itp staging is config-driven via _stage_hydrate_guest_itps
            # above. The previous _detect_guest_type_from_structure +
            # shutil.copy({guest_type}_hydrate.itp) + QMessageBox.warning block is
            # removed: it could not handle custom guests (detect returns None, so
            # no ITP was staged and grompp would fail with a missing-ITP error),
            # and the helper now covers both the custom (transform+write) and
            # built-in (shutil.copy of the bundled _hydrate.itp) paths in one
            # place.
            
            # Copy solute .itp file (liquid solutes use _liquid.itp)
            solute_type_lower = solute_type
            solute_itp_name = f"{solute_type_lower}_liquid.itp"

            from pathlib import Path as FilePath
            solute_itp_source = FilePath(__file__).parent.parent / "data" / solute_itp_name
            if solute_itp_source.exists():
                from quickice.output.gromacs_writer import comment_out_atomtypes_in_itp
                itp_content = solute_itp_source.read_text()
                modified_content = comment_out_atomtypes_in_itp(itp_content)
                solute_itp_dest = path.with_name(solute_itp_name)
                solute_itp_dest.write_text(modified_content)
                logger.info(f"Solute ITP copied with atomtypes commented: {solute_itp_dest}")
            
            # Copy custom molecule .itp file if custom molecules are present
            if solute_structure.custom_molecule_count > 0 and solute_structure.custom_molecule_positions is not None:
                if solute_structure.custom_itp_path and Path(solute_structure.custom_itp_path).exists():
                    from quickice.output.gromacs_writer import comment_out_atomtypes_in_itp
                    custom_itp_source = Path(solute_structure.custom_itp_path)
                    custom_itp_dest = path.with_name(custom_itp_source.name)
                    itp_content = custom_itp_source.read_text()
                    modified_content = comment_out_atomtypes_in_itp(itp_content)
                    custom_itp_dest.write_text(modified_content)
                    logger.info(f"Custom ITP copied with atomtypes commented: {custom_itp_dest}")
            
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
    
    def export_custom_molecule_gromacs(
        self, custom_structure, hydrate_config=None
    ) -> bool:
        """Export custom molecule structure to GROMACS format.
        
        Exports COMPLETE system: ice + water + custom molecules.
        Files: .gro, .top, and custom .itp bundled.

        Args:
            custom_structure: CustomMoleculeStructure with complete system data
            hydrate_config: Optional :class:`HydrateConfig` that produced the
                hydrate the custom molecule's interface was assembled from.
                When the interface carries custom guest molecules (e.g. a
                custom ethanol hydrate exported via the Custom Molecule tab),
                this drives the config-driven ITP staging via
                :func:`quickice.output.guest_info._stage_hydrate_guest_itps`
                (plan 44.1-08): it builds ``custom_guest_info`` from the
                config, transforms + writes each custom ITP with the ``_H``
                suffix, and threads ``custom_guest_info`` to both
                :func:`write_custom_molecule_gro_file` and
                :func:`write_custom_molecule_top_file` (extended in plan
                44.1-13 to accept the kwarg). When ``None`` (built-in ch4 /
                thf path) or a config with only built-in cage assignments, the
                helper copies the bundled pre-transformed
                ``{guest_type}_hydrate.itp`` — byte-identical to the previous
                built-in path.
        
        Returns:
            True if export succeeded
        """
        # Generate default filename
        moleculetype_name = custom_structure.moleculetype_name
        n_molecules = custom_structure.custom_molecule_count
        default_name = _build_default_path(
            self.parent,
            f"custom_system_{moleculetype_name}_{n_molecules}molecules.gro",
        )
        
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
        _remember_export_dir(self.parent, filepath)
        
        # Ensure .gro extension
        path = Path(filepath)
        if path.suffix.lower() != '.gro':
            path = path.with_suffix('.gro')
        
        # Generate companion filename
        top_path = path.with_name(path.stem + '.top')
        
        try:
            import shutil
            
            # Stage hydrate guest ITPs (config-driven, plan 44.1-08/13).
            # Replaces the broken _detect_guest_type_from_structure (returns
            # None for custom guests like etoh_e2e) + shutil.copy(
            # {guest_type}_hydrate.itp) (FileNotFoundError for custom) pattern.
            # The helper handles both paths: custom guests get a transformed
            # ITP (moleculetype {base}_H, [atomtypes] commented, [atoms] resname
            # {base}_H) written to path.parent; built-in ch4/thf get the
            # bundled pre-transformed {guest_type}_hydrate.itp copied across.
            #
            # Unlike SoluteStructure (which delegates guest info to
            # interface_structure), CustomMoleculeStructure carries its OWN
            # guest_atom_count / guest_nmolecules (propagated from the
            # interface during insertion, types.py:1044-1045) and its OWN
            # molecule_index with "guest" entries (custom_molecule_inserter
            # builds complete_molecule_index). These are authoritative for the
            # flattened structure being exported, so pass custom_structure
            # (not interface_structure) as the structure for the helper's
            # presence gate + built-in detection + molecule_index regression
            # fix. The interface_structure is the SOURCE interface (which for
            # real GenIce2 data has an EMPTY molecule_index); the
            # custom_structure's molecule_index is the one that carries the
            # guest entries the helper needs. Matches the 44.1-08 helper's
            # regression fix (recover guest_nmolecules from molecule_index)
            # and the 44.1-11 SoluteGROMACSExporter pattern (which uses
            # interface_structure because SoluteStructure delegates to it).
            from quickice.output.guest_info import _stage_hydrate_guest_itps
            custom_guest_info, _staged_guest_itps = _stage_hydrate_guest_itps(
                path.parent, hydrate_config, custom_structure,
                guest_atom_count=getattr(custom_structure, 'guest_atom_count', 0),
                guest_nmolecules=getattr(custom_structure, 'guest_nmolecules', 0),
            )

            # Write .gro file with complete system
            from quickice.output.gromacs_writer import (
                write_custom_molecule_gro_file,
                write_custom_molecule_top_file
            )
            
            write_custom_molecule_gro_file(
                custom_structure, str(path), custom_guest_info=custom_guest_info
            )
            write_custom_molecule_top_file(
                custom_structure, str(top_path), custom_guest_info=custom_guest_info
            )
            
            # Copy custom .itp file to output directory
            # Read, modify, and write ITP file with atomtypes commented out
            from quickice.output.gromacs_writer import comment_out_atomtypes_in_itp
            itp_content = custom_structure.itp_path.read_text()
            modified_content = comment_out_atomtypes_in_itp(itp_content)
            custom_itp_dest = path.with_name(custom_structure.itp_path.name)
            custom_itp_dest.write_text(modified_content)
            
            logger.info(f"Custom ITP copied with atomtypes commented: {custom_itp_dest}")
            
            # Copy water .itp file (must match the #include "tip4p-ice.itp" in .top file)
            from quickice.output.gromacs_writer import get_tip4p_itp_path
            water_itp_source = get_tip4p_itp_path()
            water_itp_dest = path.with_name("tip4p-ice.itp")
            shutil.copy(water_itp_source, water_itp_dest)
            
            # Guest .itp staging is config-driven via _stage_hydrate_guest_itps
            # above. The previous _detect_guest_type_from_structure +
            # shutil.copy({guest_type}_hydrate.itp) + QMessageBox.warning block
            # is removed: it could not handle custom guests (detect returns
            # None, so no ITP was staged and grompp would fail with a
            # missing-ITP error), and the helper now covers both the custom
            # (transform+write) and built-in (shutil.copy of the bundled
            # _hydrate.itp) paths in one place.
            
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
            bare_name = f"ions_{na_count}na_{cl_count}cl_with_{ion_structure.solute_n_molecules}{ion_structure.solute_type.lower()}.gro"
        else:
            bare_name = f"ions_{na_count}na_{cl_count}cl.gro"
        default_name = _build_default_path(self.parent, bare_name)

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
        _remember_export_dir(self.parent, filepath)
        
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
            guest_type = _detect_guest_type_from_structure(ion_structure)
            
            if guest_type:
                try:
                    guest_itp_source = _get_hydrate_guest_itp_path(guest_type)
                    guest_itp_dest = path.with_name(f"{guest_type}_hydrate.itp")
                    shutil.copy(guest_itp_source, guest_itp_dest)
                except FileNotFoundError:
                    QMessageBox.warning(
                        self.parent, "Missing Guest ITP",
                        f"Guest ITP file for '{guest_type}' not found.\n"
                        f"The exported .top file will reference it, but it won't be bundled.\n"
                        f"Add the missing .itp file manually before running GROMACS."
                    )
            
            # Copy solute .itp file if solutes are present (liquid solutes use _liquid.itp)
            if ion_structure.solute_n_molecules > 0 and ion_structure.solute_positions is not None:
                solute_type_lower = ion_structure.solute_type.lower()
                solute_itp_name = f"{solute_type_lower}_liquid.itp"

                from pathlib import Path as FilePath
                solute_itp_source = FilePath(__file__).parent.parent / "data" / solute_itp_name
                if solute_itp_source.exists():
                    solute_itp_dest = path.with_name(solute_itp_name)
                    
                    # Read, modify, and write ITP file with atomtypes commented out
                    from quickice.output.gromacs_writer import comment_out_atomtypes_in_itp
                    itp_content = solute_itp_source.read_text()
                    modified_content = comment_out_atomtypes_in_itp(itp_content)
                    solute_itp_dest.write_text(modified_content)
                    
                    logger.info(f"Solute ITP copied with atomtypes commented: {solute_itp_dest}")
            
            # Copy custom molecule .itp file if custom molecules are present
            if ion_structure.custom_molecule_count > 0 and ion_structure.custom_molecule_positions is not None:
                if ion_structure.custom_itp_path and Path(ion_structure.custom_itp_path).exists():
                    custom_itp_source = Path(ion_structure.custom_itp_path)
                    custom_itp_dest = path.with_name(custom_itp_source.name)
                    
                    # Read, modify, and write ITP file with atomtypes commented out
                    from quickice.output.gromacs_writer import comment_out_atomtypes_in_itp
                    itp_content = custom_itp_source.read_text()
                    modified_content = comment_out_atomtypes_in_itp(itp_content)
                    custom_itp_dest.write_text(modified_content)
                    
                    logger.info(f"Custom ITP copied with atomtypes commented: {custom_itp_dest}")
            
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
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
        default_name = _build_default_path(
            self.parent, f"{phase_id}_{T:.0f}K_{P:.2f}MPa_c{rank}.pdb"
        )
        
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
        _remember_export_dir(self.parent, filepath)
        
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
            _build_default_path(self.parent, "phase_diagram.png"),
            "PNG Image (*.png);;SVG Image (*.svg);;All Files (*)",
            "PNG Image (*.png)"
        )
        
        if not filepath:
            return False
        _remember_export_dir(self.parent, filepath)
        
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
            bare_filename = f"ice_structure_{viewport_name}.png"
        else:
            bare_filename = "ice_structure.png"
        default_filename = _build_default_path(self.parent, bare_filename)
        
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
        _remember_export_dir(self.parent, filepath)
        
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
        default_name = _build_default_path(
            self.parent, f"{phase_id}_{T:.0f}K_{P:.2f}MPa_c{rank}.gro"
        )

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
        _remember_export_dir(self.parent, filepath)
        
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
            import traceback
            traceback.print_exc()
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
    
    def export_interface_gromacs(
        self, interface_structure: InterfaceStructure, hydrate_config=None
    ) -> bool:
        """Export interface structure to GROMACS format.

        Args:
            interface_structure: InterfaceStructure with ice and water phases
            hydrate_config: Optional :class:`HydrateConfig` that produced the
                hydrate the interface was assembled from. When the interface
                carries custom guest molecules (e.g. a custom ethanol hydrate
                exported via the Interface tab), this drives the config-driven
                ITP staging via :func:`quickice.output.guest_info._stage_hydrate_guest_itps`
                (plan 44.1-08): it builds ``custom_guest_info`` from the config,
                transforms + writes each custom ITP with the ``_H`` suffix, and
                threads ``custom_guest_info`` to both
                :func:`write_interface_gro_file` and
                :func:`write_interface_top_file` (which already accept the
                kwarg from plans 41-04 / 41-05). When ``None`` (built-in
                ch4 / thf path) or a config with only built-in cage assignments,
                the helper copies the bundled pre-transformed
                ``{guest_type}_hydrate.itp`` — byte-identical to the previous
                built-in path.

        Returns:
            True if export succeeded

        Per CONTEXT.md:
        - Default filename format: interface_{mode}.gro
        - Generates companion .top and .itp files
        """
        # Generate default filename with mode info
        mode = interface_structure.mode
        default_name = _build_default_path(self.parent, f"interface_{mode}.gro")

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
        _remember_export_dir(self.parent, filepath)
        
        # Ensure .gro extension
        path = Path(filepath)
        if path.suffix.lower() != '.gro':
            path = path.with_suffix('.gro')
        
        # Generate companion filenames using stem (handles dots in filename correctly)
        top_path = path.with_name(path.stem + '.top')
        itp_path = path.with_name(path.stem + '.itp')
        
        try:
            # Stage hydrate guest ITPs (config-driven, plan 44.1-08/09).
            # Replaces the broken _detect_guest_type_from_structure (returns
            # None for custom guests like etoh_e2e) + shutil.copy(
            # {guest_type}_hydrate.itp) (FileNotFoundError for custom) pattern.
            # The helper handles both paths: custom guests get a transformed
            # ITP (moleculetype {base}_H, [atomtypes] commented, [atoms] resname
            # {base}_H) written to path.parent; built-in ch4/thf get the
            # bundled pre-transformed {guest_type}_hydrate.itp copied across.
            # custom_guest_info is None for the no-guest / built-in paths (the
            # writers treat None and [] identically via `for ci in (x or [])`).
            from quickice.output.guest_info import _stage_hydrate_guest_itps
            custom_guest_info, _staged_guest_itps = _stage_hydrate_guest_itps(
                path.parent, hydrate_config, interface_structure,
                guest_atom_count=getattr(interface_structure, 'guest_atom_count', 0),
                guest_nmolecules=getattr(interface_structure, 'guest_nmolecules', 0),
            )

            # Write .gro file using gromacs_writer
            from quickice.output.gromacs_writer import write_interface_gro_file
            write_interface_gro_file(
                interface_structure, str(path),
                custom_guest_info=custom_guest_info,
            )

            # Write .top file
            from quickice.output.gromacs_writer import write_interface_top_file
            write_interface_top_file(
                interface_structure, str(top_path),
                custom_guest_info=custom_guest_info,
            )

            # Copy .itp files from data directory
            import shutil
            from quickice.output.gromacs_writer import get_tip4p_itp_path

            # Copy water .itp file (must match the #include "tip4p-ice.itp" in .top file)
            water_itp_source = get_tip4p_itp_path()
            water_itp_dest = path.with_name("tip4p-ice.itp")
            shutil.copy(water_itp_source, water_itp_dest)

            # Guest .itp staging is config-driven via _stage_hydrate_guest_itps
            # above. The previous _detect_guest_type_from_structure +
            # shutil.copy({guest_type}_hydrate.itp) block is removed: it could
            # not handle custom guests (detect returns None, so no ITP was
            # staged and grompp would fail with a missing-ITP error), and the
            # helper now covers both the custom (transform+write) and built-in
            # (shutil.copy of the bundled _hydrate.itp) paths in one place.

            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self.parent, "Export Error", f"Failed: {e}")
            return False
