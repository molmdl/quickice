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
    
    if gro_residue_name and itp_residue_name:
        if gro_residue_name in GENERIC_RESIDUE_NAMES:
            # Generic residue name - skip mismatch warning (expected behavior)
            logger.info(
                f"GRO uses generic residue name '{gro_residue_name}', "
                f"ITP uses '{itp_residue_name}' - this is expected"
            )
        elif gro_residue_name != itp_residue_name:
            # Real mismatch - show warning
            residue_name_mismatch = True
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
        gro_residue_name=gro_residue_name,
        itp_residue_name=itp_residue_name,
        gro_atom_count=gro_atom_count
    )
