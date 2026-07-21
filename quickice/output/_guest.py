"""Guest identification, reordering, and residue-name lookup helpers.

Extracted from ``gromacs_writer.py`` (Phase 48.1, Wave 1). All function bodies
are byte-identical to the pre-refactor source — only the file path changed.

Cross-cutting helpers (research §10 Q5): ``_get_molecule_atoms`` and
``detect_guest_type_from_atoms`` are used by the interface, ion, and solute
writers; ``reorder_guest_atoms`` is used by the interface, multi-molecule,
ion, and solute writers. They live here so all per-structure writers can
share them via the ``_shared`` aggregator.
"""

import logging
from pathlib import Path

from quickice.output._constants import GUEST_ATOM_ORDER
from quickice.output._itp import parse_itp_residue_name
from quickice.utils.molecule_utils import count_guest_atoms

logger = logging.getLogger(__name__)


def reorder_guest_atoms(atom_names: list[str], mol_type: str) -> tuple[list[str], list[int] | None]:
    """Reorder guest atoms to match canonical .itp definition.
    
    GenIce2 outputs atoms in a different order than GROMACS .itp files define.
    This function reorders atoms to match the .itp canonical order.
    
    CH4 example:
      - GenIce2 output order: H, H, H, H, C (hydrogen first)
      - ITP canonical order: C, H, H, H, H (carbon first)
    
    Args:
        atom_names: List of atom names in GenIce2 output order
        mol_type: Molecule type ('ch4', 'thf')
    
    Returns:
        Tuple of (reordered atom names, reorder mapping)
        - reordered atom names: List of atom names reordered to match .itp
        - reorder mapping: List of indices such that reordered[i] = original[reorder[i]]
          Returns None if no reordering needed (mol_type not in GUEST_ATOM_ORDER)
    """
    if mol_type not in GUEST_ATOM_ORDER:
        return atom_names, None
    
    canonical = GUEST_ATOM_ORDER[mol_type]
    if len(atom_names) != len(canonical):
        # Can't reorder - might be different molecule type
        return atom_names, None
    
    # Build reorder mapping from current to canonical indices
    # reorder[i] = index in original atom_names that should be at position i in canonical order
    # So: reordered_positions[i] = positions[reorder[i]]
    # The output atom NAMES should be the CANONICAL names, not the input names.

    # Find indices in current order for each canonical atom
    reorder = []
    for target_atom in canonical:
        # Find this atom in current names
        found = False
        for idx, name in enumerate(atom_names):
            # Match by canonical name (C, H) or common type (c3, hc)
            if idx not in reorder and (
                name == target_atom or  # Exact match (already canonical)
                (target_atom == "C" and name in ["c3", "C", "Me"]) or  # Carbon
                (target_atom == "H" and name in ["hc", "H"]) or  # Hydrogen
                (target_atom == "O" and name in ["os", "O"]) or  # Oxygen
                (target_atom == "CA" and name in ["c5", "CA"]) or  # Aromatic carbon
                (target_atom == "CB" and name in ["c5", "CB"])  # Aliphatic carbon
            ):
                reorder.append(idx)
                found = True
                break
        if not found:
            # Not found - keep original position
            if len(reorder) < len(atom_names):
                reorder.append(len(reorder))

    # Return CANONICAL names (not reordered input names!)
    # The input atom_names might be types (c3, hc) but .gro needs names (C, H)
    if (reorder 
        and len(reorder) == len(atom_names) 
        and all(i < len(atom_names) for i in reorder)
        and len(set(reorder)) == len(reorder)):
        return list(canonical), reorder

    return atom_names, None


def get_guest_residue_name(guest_type: str) -> str:
    """Get the residue name for a guest molecule type from its itp file.
    
    Reads the residue name from the bundled itp file in quickice/data/.
    Falls back to hardcoded values if the itp file cannot be read.
    
    Args:
        guest_type: Guest molecule type ("ch4", "thf", etc.)
    
    Returns:
        Residue name from the itp file (e.g., "CH4", "THF")
    """
    try:
        import quickice
        package_dir = Path(quickice.__file__).parent
        itp_path = package_dir / "data" / f"{guest_type}.itp"
        
        if not itp_path.exists():
            itp_path = Path(__file__).parent.parent / "data" / f"{guest_type}.itp"
        
        if itp_path.exists():
            res_name = parse_itp_residue_name(itp_path)
            if res_name:
                return res_name
    except (OSError, ValueError) as e:
        logger.warning(f"Could not read guest residue name from ITP file: {e}")
    
    FALLBACK_RESIDUE_NAMES = {
        "ch4": "CH4",
        "thf": "THF",
        "co2": "CO2",
        "h2": "H2",
    }
    return FALLBACK_RESIDUE_NAMES.get(guest_type, "UNK")


def get_hydrate_guest_residue_name(guest_type: str) -> str:
    """Get the residue name for a hydrate guest molecule from its hydrate-specific itp file.
    
    Args:
        guest_type: Guest molecule type ("ch4", "thf", etc.)
    
    Returns:
        Residue name from the hydrate ITP file (e.g., "CH4_H", "THF_H")
    """
    try:
        import quickice
        package_dir = Path(quickice.__file__).parent
        itp_path = package_dir / "data" / f"{guest_type}_hydrate.itp"
        
        if not itp_path.exists():
            itp_path = Path(__file__).parent.parent / "data" / f"{guest_type}_hydrate.itp"
        
        if itp_path.exists():
            res_name = parse_itp_residue_name(itp_path)
            if res_name:
                return res_name
    except (OSError, ValueError) as e:
        logger.warning(f"Could not read hydrate guest residue name from ITP file: {e}")
    
    FALLBACK_HYDRATE_NAMES = {
        "ch4": "CH4_H",
        "thf": "THF_H",
        "co2": "CO2_H",
        "h2": "H2_H",
    }
    return FALLBACK_HYDRATE_NAMES.get(guest_type, "UNK_H")


def _get_molecule_atoms(atom_names: list[str]) -> list[str]:
    """Extract atom names for one complete guest molecule from the list.

    Handles various guest molecule types and their atom naming conventions.
    Works regardless of atom order (unlike count_guest_atoms which assumes
    certain atoms come first).

    Args:
        atom_names: List of atom names in guest region

    Returns:
        List of atom names for the first complete molecule,
        or empty list if cannot determine
    """
    if not atom_names:
        return []

    # Strategy: detect molecule by counting atoms of each type
    # and looking for patterns

    # Check first 20 atoms max to avoid infinite loop
    sample = atom_names[:20]

    # Count atoms by type
    from collections import Counter
    counts = Counter(sample)

    # THF: C4H8O (4 C, 8 H, 1 O = 13 atoms)
    # Check BEFORE CH4 since THF also has C and H
    # GenIce2 THF: O, CA, CA, CB, CB, H, H, H, H, H, H, H, H (13 atoms)
    # Atoms can be named C, CA, or CB for carbons
    carbon_count = sum(counts.get(atom, 0) for atom in ['C', 'CA', 'CB', 'c3', 'c5'])
    if counts.get('O', 0) >= 1 and carbon_count >= 4:
        # Return first 13 atoms as likely THF
        return sample[:13]

    # CH4: 1 C + 4 H = 5 atoms
    if counts.get('C', 0) >= 1 and counts.get('H', 0) >= 4:
        # Find C and 4 H atoms
        mol_atoms = []
        h_count = 0
        for atom in sample:
            if atom == 'C' and 'C' not in mol_atoms:
                mol_atoms.append(atom)
            elif atom == 'H' and h_count < 4:
                mol_atoms.append(atom)
                h_count += 1
            if len(mol_atoms) == 5:
                break
        return mol_atoms[:5]

    # H2: just H atoms
    if set(sample[:2]) == {'H'} and len(sample) >= 2:
        return ['H', 'H']

    # CO2: C and O atoms
    if counts.get('C', 0) >= 1 and counts.get('O', 0) >= 2:
        return ['C', 'O', 'O']

    # If first atom is Me (united-atom methane), return 1 atom
    if sample[0] == 'Me':
        return ['Me']

    # Fallback: try using count_guest_atoms from molecule_utils
    count = count_guest_atoms(atom_names, 0)
    if count > 0:
        return atom_names[:count]

    return []


def detect_guest_type_from_atoms(atom_names: list[str]) -> str | None:
    """Detect guest molecule type from atom names.
    
    Analyzes the atom composition to determine the guest molecule type.
    This is needed because molecule_index may store mol_type as "guest"
    (generic) rather than the specific type like "ch4" or "thf".
    
    Args:
        atom_names: List of atom names for one or more guest molecules
        
    Returns:
        Guest type string ("ch4", "thf", "co2", "h2") or None if undetected
    """
    if not atom_names:
        return None
    
    # Get atoms for one molecule to identify type
    mol_atoms = _get_molecule_atoms(atom_names)
    
    if not mol_atoms:
        return None
    
    mol_unique = set(mol_atoms)
    
    # Check for carbon atoms (can be named C, CA, CB, c3, c5, etc.)
    has_carbon = any(atom in mol_unique for atom in ['C', 'CA', 'CB', 'c3', 'c5'])
    has_oxygen = 'O' in mol_unique
    has_hydrogen = 'H' in mol_unique
    
    # CO2: C and O atoms, no H (3 atoms) — MUST check BEFORE THF
    # CO2 has C and O like THF, but CO2 has no hydrogen
    if has_carbon and has_oxygen and not has_hydrogen:
        return "co2"
    
    # THF: Has O and carbon atoms (CA, CB, or C), may have H
    # THF atoms are: O, CA, CA, CB, CB, H, H, H, H, H, H, H, H (13 atoms)
    elif has_oxygen and has_carbon:
        return "thf"
    
    # CH4: Only C and H, no O, typically 5 atoms
    elif has_carbon and has_hydrogen and not has_oxygen:
        return "ch4"
    
    # H2: Only H atoms (2 atoms)
    elif mol_unique == {'H'}:
        return "h2"
    
    # United-atom methane
    elif mol_unique == {'Me'}:
        return "ch4"
    
    return None
