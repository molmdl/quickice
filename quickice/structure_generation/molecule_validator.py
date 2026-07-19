"""Molecule validation utilities.

Validates consistency between GRO structure files and ITP topology files.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

from quickice.structure_generation.gro_parser import parse_gro_file, extract_residue_name_from_gro
from quickice.structure_generation.itp_parser import ITPMoleculeInfo

logger = logging.getLogger(__name__)

# Generic residue names commonly used in computational chemistry
# These are placeholders that should not trigger mismatch warnings
GENERIC_RESIDUE_NAMES = {"MOL", "UNK", "LIG", "XXX", "RES", "DRG", "API", "HET", "UNL", "LIG1", "MOL1"}

# Built-in atomtype names that QuickIce writes into the main .top file.
# Source of truth: quickice/output/gromacs_writer.py — WATER_ATOMTYPES
# (OW_ice, HW_ice, MW) and ION_ATOMTYPES (NA, CL). A user upload that
# REDEFINES any of these names in its own [ atomtypes ] section would cause
# a duplicate-atomtype error in `gmx grompp` (the main .top already defines
# them). TD-07 rejects such uploads at validation time with a clear message
# instead of letting them fail later at grompp with a confusing error.
#
# This literal is kept in sync with gromacs_writer.py via the regression test
# `test_builtin_atomtype_names_match_gromacs_writer` in
# tests/test_scancode_bugs_tech_debt.py — if the dicts change, that test
# forces a review of this set. Defined here (rather than imported from
# quickice.output.gromacs_writer) to avoid reversing the existing
# dependency direction (output imports from structure_generation; not
# vice versa).
BUILTIN_ATOMTYPE_NAMES: frozenset[str] = frozenset({
    "OW_ice",  # TIP4P-ICE water oxygen
    "HW_ice",  # TIP4P-ICE water hydrogen
    "MW",      # TIP4P-ICE water virtual site
    "NA",      # Madrid2019 sodium ion
    "CL",      # Madrid2019 chloride ion
})


@dataclass
class ValidationResult:
    """Result of GRO/ITP consistency validation.
    
    Attributes:
        is_valid: True if validation passed, False otherwise
        errors: List of error messages (blocking issues)
        warnings: List of warning messages (non-blocking issues)
        residue_name_mismatch: True if GRO and ITP residue names differ (non-blocking)
        gro_residue_name: Residue name from GRO file (if extractable)
        itp_residue_name: Residue name from ITP file (moleculetype name)
        gro_atom_count: Number of atoms in GRO file
    """
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    residue_name_mismatch: bool = False
    is_generic_residue_name: bool = False
    gro_residue_name: str | None = None
    itp_residue_name: str | None = None
    gro_atom_count: int | None = None


def validate_gro_itp_consistency(
    gro_path: Path,
    itp_info: ITPMoleculeInfo
) -> ValidationResult:
    """Validate GRO file consistency with ITP file.
    
    Checks:
    1. Atom count matches between GRO and ITP
    2. Residue name matches ITP moleculetype name (if extractable)
    
    Args:
        gro_path: Path to .gro file
        itp_info: Parsed ITP information from parse_itp_file()
        
    Returns:
        ValidationResult with errors and warnings
        
    Example:
        >>> from quickice.structure_generation.itp_parser import parse_itp_file
        >>> itp_info = parse_itp_file(Path("custom_mol.itp"))
        >>> result = validate_gro_itp_consistency(Path("custom_mol.gro"), itp_info)
        >>> if not result.is_valid:
        ...     print("\\n".join(result.errors))
    """
    errors: List[str] = []
    warnings: List[str] = []
    
    # Parse GRO file
    try:
        positions, atom_names, cell = parse_gro_file(gro_path)
        gro_atom_count = len(positions)
        logger.info(f"Parsed GRO file {gro_path.name}: {gro_atom_count} atoms")
    except (ValueError, OSError) as e:
        errors.append(f"Failed to parse GRO file {gro_path.name}: {e}")
        return ValidationResult(False, errors, warnings)
    
    # Check atom count
    if gro_atom_count != itp_info.atom_count:
        errors.append(
            f"Atom count mismatch:\n"
            f"  GRO file {gro_path.name} has {gro_atom_count} atoms\n"
            f"  ITP file defines {itp_info.atom_count} atoms"
        )
    
    # Check for [ atomtypes ] section
    if not itp_info.has_atomtypes_section:
        warnings.append(
            f"Missing [ atomtypes ] section in {gro_path.stem}.itp\n"
            "User must provide atom type parameters separately in force field file"
        )
    
    is_valid = len(errors) == 0
    logger.info(
        f"Validation {gro_path.stem}: {'PASS' if is_valid else 'FAIL'} "
        f"({len(errors)} errors, {len(warnings)} warnings)"
    )
    
    return ValidationResult(is_valid, errors, warnings)


def validate_custom_molecule(
    gro_path: Path,
    itp_info: ITPMoleculeInfo
) -> ValidationResult:
    """Validate GRO file consistency with ITP file for custom molecules.
    
    Comprehensive validation for custom molecule upload:
    1. Atom count matches between GRO and ITP (BLOCKING)
    2. Residue name consistency (NON-BLOCKING, triggers dialog)
    3. [ atomtypes ] section presence (warning)
    
    Args:
        gro_path: Path to .gro file
        itp_info: Parsed ITP information from parse_itp_file()
        
    Returns:
        ValidationResult with detailed errors/warnings and residue name fields
        
    Example:
        >>> from quickice.structure_generation.itp_parser import parse_itp_file
        >>> itp_info = parse_itp_file(Path("custom_mol.itp"))
        >>> result = validate_custom_molecule(Path("custom_mol.gro"), itp_info)
        >>> if result.residue_name_mismatch:
        ...     print(f"Mismatch: GRO uses '{result.gro_residue_name}', ITP uses '{result.itp_residue_name}'")
        ...     # Show dialog asking user if ITP name should override
    """
    errors: List[str] = []
    warnings: List[str] = []
    
    # Parse GRO file
    try:
        positions, atom_names, cell = parse_gro_file(gro_path)
        gro_atom_count = len(positions)
        logger.info(f"Parsed GRO file {gro_path.name}: {gro_atom_count} atoms")
    except (ValueError, OSError) as e:
        errors.append(f"Failed to parse GRO file {gro_path.name}: {e}")
        return ValidationResult(False, errors, warnings)
    
    # Extract residue name from GRO
    gro_residue_name = extract_residue_name_from_gro(gro_path)
    
    # Check atom count (BLOCKING)
    if gro_atom_count != itp_info.atom_count:
        errors.append(
            f"Atom count mismatch:\n"
            f"  GRO file has {gro_atom_count} atoms\n"
            f"  ITP file defines {itp_info.atom_count} atoms"
        )
    
    # Check residue name consistency (NON-BLOCKING)
    itp_residue_name = itp_info.molecule_name
    residue_name_mismatch = False
    is_generic_residue_name = False
    
    if gro_residue_name and itp_residue_name:
        if gro_residue_name != itp_residue_name:
            residue_name_mismatch = True
            
            if gro_residue_name in GENERIC_RESIDUE_NAMES:
                # Generic residue name mismatch - offer dialog to use ITP name
                is_generic_residue_name = True
                logger.info(
                    f"GRO uses generic residue name '{gro_residue_name}', "
                    f"ITP uses '{itp_residue_name}' - offering dialog choice"
                )
                warnings.append(
                    f"Generic residue name in GRO file:\n"
                    f"  GRO file uses '{gro_residue_name}' (generic placeholder)\n"
                    f"  ITP file uses '{itp_residue_name}'\n"
                    f"Use ITP residue name instead?"
                )
            else:
                # Real mismatch - show warning
                warnings.append(
                    f"Residue name mismatch:\n"
                    f"  GRO file uses '{gro_residue_name}'\n"
                    f"  ITP file uses '{itp_residue_name}'\n"
                    f"User must choose to proceed or re-select files."
                )
    
    # Check for [ atomtypes ] section (warning)
    if not itp_info.has_atomtypes_section:
        warnings.append(
            f"Missing [ atomtypes ] section in ITP file.\n"
            f"User must provide atom type parameters separately."
        )
    
    # TD-07: Check for atomtype CONFLICTS with built-in QuickIce types.
    # A user upload that REDEFINES a built-in atomtype name (OW_ice, HW_ice,
    # MW, NA, CL) in its [ atomtypes ] section would cause a duplicate-
    # atomtype error in `gmx grompp` because the main .top already defines
    # these. Reject at upload time with a clear, user-facing message so the
    # user can rename the conflicting type (e.g. OW_ice -> OW_custom) BEFORE
    # running grompp. This is a BLOCKING error. Non-conflicting uploads
    # (including uploads that merely REFERENCE a built-in name in their
    # [ atoms ] section without redefining it) are NOT rejected.
    if itp_info.has_atomtypes_section:
        conflicting = set(itp_info.atomtype_names) & BUILTIN_ATOMTYPE_NAMES
        if conflicting:
            conflicts_str = ", ".join(sorted(conflicting))
            errors.append(
                f"Atomtype name conflict with built-in QuickIce types:\n"
                f"  Your ITP [ atomtypes ] section redefines: {conflicts_str}\n"
                f"  These names are reserved for QuickIce's built-in TIP4P-ICE "
                f"water (OW_ice, HW_ice, MW) and Madrid2019 ion (NA, CL) parameters "
                f"and cannot be redefined — the main .top file already provides them.\n"
                f"  Rename your atomtype(s) (e.g. 'OW_ice' -> 'OW_custom') to avoid a "
                f"duplicate-atomtype error in `gmx grompp`."
            )
            logger.warning(
                f"Custom molecule ITP redefines built-in atomtype(s): {conflicts_str}"
            )
    
    is_valid = len(errors) == 0
    logger.info(
        f"Custom molecule validation {gro_path.stem}: {'PASS' if is_valid else 'FAIL'} "
        f"({len(errors)} errors, {len(warnings)} warnings)"
    )
    
    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        residue_name_mismatch=residue_name_mismatch,
        is_generic_residue_name=is_generic_residue_name,
        gro_residue_name=gro_residue_name,
        itp_residue_name=itp_residue_name,
        gro_atom_count=gro_atom_count
    )
