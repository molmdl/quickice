"""ITP path resolver and copy functions for CLI export.

Provides reliable path resolution for bundled ITP files with
case normalization, plus copy_itp_files_for_structure() that
bundles all required ITP files for a given step type.

No GUI imports — works without PySide6/VTK.
"""

import logging
import shutil
from pathlib import Path
from typing import Any

import quickice

logger = logging.getLogger(__name__)


def get_hydrate_guest_itp_path(guest_type: str) -> Path:
    """Resolve path to the hydrate guest ITP file.

    Args:
        guest_type: Hydrate guest molecule type (e.g. 'CH4', 'ch4', 'THF', 'thf').
                   Case-insensitive — normalized to lowercase internally.

    Returns:
        Path to the bundled hydrate guest ITP file.

    Raises:
        FileNotFoundError: If the ITP file does not exist in the data directory.
    """
    guest_type = guest_type.lower()
    path = Path(quickice.__file__).parent / "data" / f"{guest_type}_hydrate.itp"
    if not path.exists():
        raise FileNotFoundError(
            f"Hydrate guest ITP file not found: {path} "
            f"(guest_type={guest_type!r})"
        )
    return path


def get_solute_liquid_itp_path(solute_type: str) -> Path:
    """Resolve path to the solute liquid ITP file.

    Args:
        solute_type: Solute molecule type (e.g. 'CH4', 'ch4', 'THF', 'thf').
                    Case-insensitive — normalized to lowercase internally.

    Returns:
        Path to the bundled solute liquid ITP file.

    Raises:
        FileNotFoundError: If the ITP file does not exist in the data directory.
    """
    solute_type = solute_type.lower()
    path = Path(quickice.__file__).parent / "data" / f"{solute_type}_liquid.itp"
    if not path.exists():
        raise FileNotFoundError(
            f"Solute liquid ITP file not found: {path} "
            f"(solute_type={solute_type!r})"
        )
    return path


def get_tip4p_itp_path() -> Path:
    """Resolve path to the TIP4P-ICE ITP file.

    Re-exported from quickice.output.gromacs_writer for convenience.

    Returns:
        Path to the bundled TIP4P-ICE ITP file.
    """
    from quickice.output.gromacs_writer import get_tip4p_itp_path as _get_tip4p

    return _get_tip4p()


def _detect_guest_type(structure: Any) -> str | None:
    """Detect guest molecule type from a structure object.

    Works with all structure types (InterfaceStructure, SoluteStructure,
    CustomMoleculeStructure, IonStructure, HydrateStructure) by inspecting
    molecule_index entries or using atom-count heuristics.

    For SoluteStructure and IonStructure, delegates to interface_structure
    fallback when the structure itself lacks guest info.

    Args:
        structure: Any structure dataclass that may contain guest molecule info.

    Returns:
        Guest type string ('ch4' or 'thf') or None if no guest detected.
    """
    # Fallback: if structure lacks guest_atom_count AND molecule_index,
    # delegate to interface_structure (SoluteStructure/IonStructure pattern)
    has_guest_atom_count = hasattr(structure, "guest_atom_count")
    has_molecule_index = hasattr(structure, "molecule_index")

    if not has_guest_atom_count and not has_molecule_index:
        interface = getattr(structure, "interface_structure", None)
        if interface is not None:
            return _detect_guest_type(interface)
        return None

    # Check guest_atom_count — if 0, no guests
    guest_atom_count = getattr(structure, "guest_atom_count", 0)
    if guest_atom_count == 0:
        return None

    # Strategy 1: inspect molecule_index entries for specific mol_type
    molecule_index = getattr(structure, "molecule_index", [])
    if molecule_index:
        for entry in molecule_index:
            # MoleculeIndex is a dataclass — use .mol_type attribute,
            # NOT dict-style .get('mol_type')
            mol_type_upper = entry.mol_type.upper()
            if mol_type_upper == "CH4":
                return "ch4"
            elif mol_type_upper == "THF":
                return "thf"
            # Also check 'GUEST' entries — these are generic and need
            # further inspection via atom-count heuristic below

    # Strategy 2: atom-count heuristic
    # Use getattr with default 1 for guest_nmolecules (not bare access —
    # HydrateStructure uses guest_count, not guest_nmolecules)
    guest_nmolecules = getattr(structure, "guest_nmolecules", None)
    if guest_nmolecules is None:
        # HydrateStructure uses guest_count instead
        guest_nmolecules = getattr(structure, "guest_count", 1)
    if guest_nmolecules is None or guest_nmolecules < 1:
        guest_nmolecules = 1

    atoms_per = guest_atom_count / max(guest_nmolecules, 1)
    if atoms_per <= 5:
        return "ch4"
    elif atoms_per >= 10:
        return "thf"

    return None


def _copy_itp_with_atomtypes_commented(source: Path, dest: Path) -> str | None:
    """Copy ITP file with [ atomtypes ] section commented out.

    Args:
        source: Source ITP file path.
        dest: Destination ITP file path.

    Returns:
        Destination filename if copied successfully, None on failure.
    """
    from quickice.output.gromacs_writer import comment_out_atomtypes_in_itp

    try:
        content = source.read_text()
        modified = comment_out_atomtypes_in_itp(content)
        dest.write_text(modified)
        logger.info(f"ITP copied with atomtypes commented: {dest}")
        return dest.name
    except Exception as e:
        logger.warning(f"Failed to copy ITP with atomtypes commented ({source}): {e}")
        return None


def _copy_hydrate_guest_itp(output_dir: Path, guest_type: str) -> str | None:
    """Copy hydrate guest ITP file to output directory.

    Args:
        output_dir: Destination directory.
        guest_type: Guest molecule type ('ch4' or 'thf').

    Returns:
        ITP filename if copied successfully, None on failure.
    """
    try:
        source = get_hydrate_guest_itp_path(guest_type)
        dest = output_dir / f"{guest_type}_hydrate.itp"
        shutil.copy(source, dest)
        logger.info(f"Hydrate guest ITP copied: {dest}")
        return dest.name
    except FileNotFoundError:
        logger.warning(f"Hydrate guest ITP file not found for guest_type={guest_type!r}")
        return None
    except Exception as e:
        logger.warning(f"Failed to copy hydrate guest ITP (guest_type={guest_type!r}): {e}")
        return None


def _resolve_guest_type_for_hydrate_step(structure: Any, args_ref: Any = None) -> str | None:
    """Resolve guest type for hydrate step with multiple fallback strategies.

    Priority order:
    1. structure.guest_type attribute (if exists, call .lower())
    2. structure.config.guest_type (HydrateStructure pattern)
    3. _detect_guest_type(structure) for molecule_index/atom-count detection
    4. getattr(args_ref, 'guest', 'CH4').lower() as last resort

    Args:
        structure: HydrateStructure or similar with guest info.
        args_ref: Optional args namespace for last-resort fallback.

    Returns:
        Guest type string ('ch4' or 'thf') or None if undetected.
    """
    # Strategy 1: direct guest_type attribute
    guest_type = getattr(structure, "guest_type", None)
    if guest_type is not None:
        return guest_type.lower()

    # Strategy 2: config.guest_type (HydrateStructure.config is HydrateConfig)
    config = getattr(structure, "config", None)
    if config is not None:
        config_guest_type = getattr(config, "guest_type", None)
        if config_guest_type is not None:
            return config_guest_type.lower()

    # Strategy 3: detect from molecule_index or atom counts
    detected = _detect_guest_type(structure)
    if detected is not None:
        return detected

    # Strategy 4: last resort — args reference
    if args_ref is not None:
        fallback = getattr(args_ref, "guest", "CH4")
        return fallback.lower()

    return None


def copy_itp_files_for_structure(
    output_dir: Path, structure: Any, step_name: str, args_ref: Any = None
) -> list[str]:
    """Copy all required ITP files for a given structure and step type.

    Handles all 6 step types (ice, hydrate, interface, custom, solute, ion)
    with correct ITP file selection and optional atomtypes commenting.

    Args:
        output_dir: Directory to copy ITP files into.
        structure: Structure dataclass (Candidate, HydrateStructure,
                   InterfaceStructure, CustomMoleculeStructure,
                   SoluteStructure, IonStructure).
        step_name: Step type name ('ice', 'hydrate', 'interface',
                   'custom', 'solute', 'ion').
        args_ref: Optional args namespace for fallback guest type resolution.

    Returns:
        List of ITP filenames that were successfully copied.
    """
    copied: list[str] = []

    # Step 1: always copy tip4p-ice.itp (required by all step types)
    try:
        tip4p_source = get_tip4p_itp_path()
        tip4p_dest = output_dir / "tip4p-ice.itp"
        shutil.copy(tip4p_source, tip4p_dest)
        copied.append("tip4p-ice.itp")
    except Exception as e:
        logger.warning(f"Failed to copy tip4p-ice.itp: {e}")

    if step_name == "ice":
        # Ice step: only tip4p-ice.itp needed (already copied)
        pass

    elif step_name == "hydrate":
        # Hydrate step: tip4p-ice.itp + hydrate guest ITP
        guest_type = _resolve_guest_type_for_hydrate_step(structure, args_ref)
        if guest_type is not None:
            itp_name = _copy_hydrate_guest_itp(output_dir, guest_type)
            if itp_name:
                copied.append(itp_name)
        else:
            logger.warning("Hydrate step but no guest type detected — skipping guest ITP")

    elif step_name == "interface":
        # Interface step: tip4p-ice.itp + guest ITP if guests present
        guest_atom_count = getattr(structure, "guest_atom_count", 0)
        if guest_atom_count > 0:
            guest_type = _detect_guest_type(structure)
            if guest_type is not None:
                itp_name = _copy_hydrate_guest_itp(output_dir, guest_type)
                if itp_name:
                    copied.append(itp_name)
            else:
                logger.warning("Interface has guests but type could not be detected")

    elif step_name == "custom":
        # Custom step: tip4p-ice.itp + custom ITP (atomtypes commented)
        #              + hydrate guest ITP if guests present
        itp_path = getattr(structure, "itp_path", None)
        if itp_path is not None:
            source = Path(itp_path)
            if source.exists():
                dest = output_dir / source.name
                itp_name = _copy_itp_with_atomtypes_commented(source, dest)
                if itp_name:
                    copied.append(itp_name)

        # Guest ITP if guests present
        guest_atom_count = getattr(structure, "guest_atom_count", 0)
        if guest_atom_count > 0:
            guest_type = _detect_guest_type(structure)
            if guest_type is not None:
                itp_name = _copy_hydrate_guest_itp(output_dir, guest_type)
                if itp_name:
                    copied.append(itp_name)

    elif step_name == "solute":
        # Solute step: tip4p-ice.itp + solute liquid ITP (atomtypes commented)
        #              + custom ITP if custom_molecule_count > 0 (atomtypes commented)
        #              + hydrate guest ITP if guests present
        solute_type = getattr(structure, "solute_type", "")
        if solute_type:
            try:
                solute_source = get_solute_liquid_itp_path(solute_type)
                solute_dest = output_dir / f"{solute_type.lower()}_liquid.itp"
                itp_name = _copy_itp_with_atomtypes_commented(solute_source, solute_dest)
                if itp_name:
                    copied.append(itp_name)
            except FileNotFoundError:
                logger.warning(f"Solute liquid ITP not found for solute_type={solute_type!r}")

        # Custom molecule ITP if present
        custom_molecule_count = getattr(structure, "custom_molecule_count", 0)
        if custom_molecule_count > 0:
            custom_itp_path = getattr(structure, "custom_itp_path", None)
            if custom_itp_path is not None:
                source = Path(custom_itp_path)
                if source.exists():
                    dest = output_dir / source.name
                    itp_name = _copy_itp_with_atomtypes_commented(source, dest)
                    if itp_name:
                        copied.append(itp_name)

        # Hydrate guest ITP if guests present in interface
        guest_atom_count = getattr(structure, "guest_atom_count", 0)
        # SoluteStructure stores guest info on its interface_structure
        if guest_atom_count == 0:
            interface = getattr(structure, "interface_structure", None)
            if interface is not None:
                guest_atom_count = getattr(interface, "guest_atom_count", 0)
        if guest_atom_count > 0:
            # Use structure or its interface for detection
            detect_target = structure
            interface = getattr(structure, "interface_structure", None)
            if interface is not None and not getattr(structure, "guest_atom_count", 0):
                detect_target = interface
            guest_type = _detect_guest_type(detect_target)
            if guest_type is not None:
                itp_name = _copy_hydrate_guest_itp(output_dir, guest_type)
                if itp_name:
                    copied.append(itp_name)

    elif step_name == "ion":
        # Ion step: tip4p-ice.itp + ion.itp (generated) + solute liquid ITP
        #           + custom ITP + hydrate guest ITP
        from quickice.structure_generation.gromacs_ion_export import write_ion_itp

        na_count = getattr(structure, "na_count", 0)
        cl_count = getattr(structure, "cl_count", 0)
        try:
            write_ion_itp(str(output_dir / "ion.itp"), na_count, cl_count)
            copied.append("ion.itp")
        except Exception as e:
            logger.warning(f"Failed to generate ion.itp: {e}")

        # Solute liquid ITP if solutes present
        solute_type = getattr(structure, "solute_type", "")
        solute_n_molecules = getattr(structure, "solute_n_molecules", 0)
        if solute_type and solute_n_molecules > 0:
            try:
                solute_source = get_solute_liquid_itp_path(solute_type)
                solute_dest = output_dir / f"{solute_type.lower()}_liquid.itp"
                itp_name = _copy_itp_with_atomtypes_commented(solute_source, solute_dest)
                if itp_name:
                    copied.append(itp_name)
            except FileNotFoundError:
                logger.warning(f"Solute liquid ITP not found for solute_type={solute_type!r}")

        # Custom molecule ITP if present
        custom_molecule_count = getattr(structure, "custom_molecule_count", 0)
        if custom_molecule_count > 0:
            custom_itp_path = getattr(structure, "custom_itp_path", None)
            if custom_itp_path is not None:
                source = Path(custom_itp_path)
                if source.exists():
                    dest = output_dir / source.name
                    itp_name = _copy_itp_with_atomtypes_commented(source, dest)
                    if itp_name:
                        copied.append(itp_name)

        # Hydrate guest ITP if guests present
        guest_atom_count = getattr(structure, "guest_atom_count", 0)
        if guest_atom_count > 0:
            guest_type = _detect_guest_type(structure)
            if guest_type is not None:
                itp_name = _copy_hydrate_guest_itp(output_dir, guest_type)
                if itp_name:
                    copied.append(itp_name)

    else:
        logger.warning(f"Unknown step_name={step_name!r} — only tip4p-ice.itp copied")

    return copied
