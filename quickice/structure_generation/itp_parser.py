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
        has_atomtypes_section: Whether [ atomtypes ] section exists in file
    """
    molecule_name: str
    atom_count: int
    atom_types: List[str]
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
    for line in atom_lines:
        fields = line.split()
        if len(fields) >= 2:
            # Atom type is second column in [ atoms ] section
            # Format: Index type residue resname atom cgnr charge mass
            atom_types.append(fields[1])
    
    atom_count = len(atom_types)
    
    # Check for [ atomtypes ] section
    has_atomtypes = bool(re.search(
        r'\[\s*atomtypes\s*\]',
        content,
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
        has_atomtypes_section=has_atomtypes
    )
