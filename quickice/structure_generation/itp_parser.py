"""GROMACS ITP topology file parser.

This module provides parsing functionality for GROMACS .itp files
to extract molecule information needed for structure generation.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class ITPMoleculeInfo:
    """Parsed information from ITP file.
    
    Attributes:
        molecule_name: Name of the molecule from [ moleculetype ] section
        atom_count: Number of atoms in the molecule
        atom_types: List of atom types (second column in [ atoms ] section)
        atom_names: List of atom names (fifth column in [ atoms ] section)
        charges: List of atom charges (seventh column in [ atoms ] section)
        has_atomtypes_section: Whether [ atomtypes ] section exists in file
    """
    molecule_name: str
    atom_count: int
    atom_types: List[str]
    atom_names: List[str]
    charges: List[float]
    has_atomtypes_section: bool


def parse_itp_file(filepath: Path) -> ITPMoleculeInfo:
    """Parse GROMACS .itp topology file.
    
    Extracts moleculetype name, atom count, and atom types.
    
    Args:
        filepath: Path to .itp file
        
    Returns:
        ITPMoleculeInfo with parsed data
        
    Raises:
        ValueError: If file format is invalid or missing required sections
        FileNotFoundError: If file does not exist
        
    Example:
        >>> from pathlib import Path
        >>> info = parse_itp_file(Path('quickice/data/ch4.itp'))
        >>> info.molecule_name
        'ch4'
        >>> info.atom_count
        5
    """
    if not filepath.exists():
        raise FileNotFoundError(f"ITP file not found: {filepath}")
    
    content = filepath.read_text()
    # Normalize: strip BOM, normalize line endings
    content = content.lstrip('\ufeff')
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    logger.info(f"Parsing ITP file: {filepath.name}")
    
    # Extract moleculetype name
    # Format: [ moleculetype ] followed by comment line then molecule name
    mol_match = re.search(
        r'\[\s*moleculetype\s*\]\s*\n\s*;.*?\n\s*(\w+)',
        content,
        re.IGNORECASE | re.DOTALL
    )
    
    if not mol_match:
        # Try alternative format without comment line
        mol_match = re.search(
            r'\[\s*moleculetype\s*\]\s*\n\s*(\w+)',
            content,
            re.IGNORECASE
        )
    
    if not mol_match:
        raise ValueError(
            f"Missing [ moleculetype ] section in {filepath.name}\n"
            "Required format:\n"
            "[ moleculetype ]\n"
            "; Name  nrexcl\n"
            "MOLNAME  3"
        )
    
    molecule_name = mol_match.group(1)
    
    # Extract atoms section
    atoms_match = re.search(
        r'\[\s*atoms\s*\](.*?)(?=\[\s*\w+\s*\]|$)',
        content,
        re.DOTALL | re.IGNORECASE
    )
    
    if not atoms_match:
        raise ValueError(f"Missing [ atoms ] section in {filepath.name}")
    
    # Parse atom lines
    atoms_section = atoms_match.group(1)
    atom_lines = [
        line for line in atoms_section.split('\n')
        if line.strip() and not line.strip().startswith(';')
    ]
    
    atom_types = []
    atom_names = []
    charges = []
    for line in atom_lines:
        fields = line.split()
        if len(fields) >= 5:
            # Atom type is second column in [ atoms ] section
            # Atom name is fifth column
            # Format: Index type residue resname atom cgnr charge mass
            atom_types.append(fields[1])
            atom_names.append(fields[4])
            # Charge is seventh column (index 6) if present
            if len(fields) >= 7:
                try:
                    charges.append(float(fields[6]))
                except ValueError:
                    charges.append(0.0)
            else:
                charges.append(0.0)
    
    atom_count = len(atom_types)
    
    # Check for [ atomtypes ] section
    # Strip comment lines (starting with ;) before checking to avoid
    # false positives from comments mentioning [ atomtypes ]
    non_comment_lines = [
        line for line in content.split('\n')
        if line.strip() and not line.strip().startswith(';')
    ]
    non_comment_content = '\n'.join(non_comment_lines)
    has_atomtypes = bool(re.search(
        r'\[\s*atomtypes\s*\]',
        non_comment_content,
        re.IGNORECASE
    ))
    
    logger.info(
        f"Parsed {filepath.name}: {molecule_name}, {atom_count} atoms, "
        f"atomtypes section: {has_atomtypes}"
    )
    
    return ITPMoleculeInfo(
        molecule_name=molecule_name,
        atom_count=atom_count,
        atom_types=atom_types,
        atom_names=atom_names,
        charges=charges,
        has_atomtypes_section=has_atomtypes
    )


def parse_itp_defaults_comb_rule(content: str) -> int | None:
    """Return the comb-rule from a GROMACS ITP/TOP ``[ defaults ]`` section.

    The GROMACS ``[ defaults ]`` section has the form::

        [ defaults ]
        ; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ
             1        2         yes       0.5     0.8333

    The comb-rule is the 2nd field (index 1) on the first non-comment,
    non-blank data line after the ``[ defaults ]`` header.

    Args:
        content: Full text of an ITP or TOP file.

    Returns:
        The comb-rule integer (typically 1 or 2) when a ``[ defaults ]``
        section is present and the comb-rule parses as an int, otherwise
        ``None``.

    Validation rule:
        Reject comb-rule != 2 ONLY when this returns a non-None value;
        accept when None (the main ``.top`` supplies comb-rule=2). This
        means an ITP with no ``[ defaults ]`` section (e.g. ``etoh.itp``)
        is valid by design — the comb-rule comes from QuickIce's generated
        main ``.top`` (always comb-rule=2, Lorentz-Berthelot / AMBER-GAFF2).
    """
    match = re.search(
        r'\[\s*defaults\s*\](.*?)(?=\[\s*\w+\s*\]|$)',
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return None
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(';') or stripped.startswith('#'):
            continue
        fields = stripped.split()
        if len(fields) >= 2:
            try:
                return int(fields[1])
            except (ValueError, IndexError):
                return None
    return None
