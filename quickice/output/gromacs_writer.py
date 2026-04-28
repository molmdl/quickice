"""GROMACS file writers for ice structure export.

Provides functions to write GROMACS coordinate (.gro) and topology (.top) files
from generated ice structure candidates using the TIP4P-ICE water model.
"""

from pathlib import Path
from typing import Optional

import numpy as np

from quickice.structure_generation.types import Candidate, InterfaceStructure, IonStructure, MoleculeIndex, MOLECULE_TYPE_INFO


# TIP4P-ICE virtual site parameter (from tip4p-ice.itp virtual_sites3 directive)
TIP4P_ICE_ALPHA = 0.13458335


# Canonical atom order for guest molecules (matching .itp definitions)
# GenIce2 outputs atoms in different order than .itp expects
GUEST_ATOM_ORDER = {
    # CH4: .itp expects [C, H, H, H, H], GenIce2 outputs [H, H, H, H, C]
    "ch4": ["C", "H", "H", "H", "H"],
    # THF: .itp expects [O, CA, CA, CB, CB, H...], GenIce2 outputs [H... O first]
    # THF canonical order from thf.itp
    "thf": ["O", "CA", "CA", "CB", "CB"],
}


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
    # So: reordered_names[i] = atom_names[reorder[i]]
    # And: reordered_positions[i] = positions[reorder[i]]
    
    # Find indices in current order for each canonical atom
    reorder = []
    for target_atom in canonical:
        # Find this atom in current names
        for idx, name in enumerate(atom_names):
            if name == target_atom and idx not in reorder:
                reorder.append(idx)
                break
        else:
            # Not found - keep original position
            if len(reorder) < len(atom_names):
                reorder.append(len(reorder))
    
    # Apply reorder to names
    if reorder and all(i < len(atom_names) for i in reorder):
        reordered_names = [atom_names[i] for i in reorder]
        return reordered_names, reorder
    
    return atom_names, None


def parse_itp_residue_name(itp_path: str | Path) -> Optional[str]:
    """Parse residue name from a GROMACS .itp file's [ atoms ] section.
    
    The residue name is found in column 4 of the [ atoms ] section lines.
    
    Args:
        itp_path: Path to the .itp file
        
    Returns:
        Residue name string (e.g., "CH4", "THF"), or None if not found
    """
    try:
        with open(itp_path, 'r') as f:
            in_atoms_section = False
            for line in f:
                line = line.strip()
                
                # Check for [ atoms ] section header
                if line.startswith('['):
                    if 'atoms' in line.lower():
                        in_atoms_section = True
                    else:
                        in_atoms_section = False
                    continue
                
                # Skip comments and empty lines
                if not line or line.startswith(';'):
                    continue
                
                # Parse [ atoms ] section line
                # Format: nr  type  resi  res  atom  cgnr  charge  mass
                if in_atoms_section:
                    parts = line.split()
                    if len(parts) >= 4:
                        # Column 4 (0-indexed: 3) is residue name
                        res_name = parts[3]
                        return res_name
    except (IOError, OSError):
        pass
    
    return None


def get_guest_residue_name(guest_type: str) -> str:
    """Get the residue name for a guest molecule type from its itp file.
    
    Reads the residue name from the bundled itp file in quickice/data/.
    Falls back to hardcoded values if the itp file cannot be read.
    
    Args:
        guest_type: Guest molecule type ("ch4", "thf", etc.)
    
    Returns:
        Residue name from the itp file (e.g., "CH4", "THF")
    """
    # Try to read from bundled itp file
    try:
        import quickice
        package_dir = Path(quickice.__file__).parent
        itp_path = package_dir / "data" / f"{guest_type}.itp"
        
        if not itp_path.exists():
            # Fallback to project root (for development)
            itp_path = Path(__file__).parent.parent / "data" / f"{guest_type}.itp"
        
        if itp_path.exists():
            res_name = parse_itp_residue_name(itp_path)
            if res_name:
                return res_name
    except Exception:
        pass
    
    # Fallback to hardcoded values (preserves backward compatibility)
    FALLBACK_RESIDUE_NAMES = {
        "ch4": "CH4",
        "thf": "THF",
        "co2": "CO2",
        "h2": "H2",
    }
    return FALLBACK_RESIDUE_NAMES.get(guest_type, "UNK")


# Mapping from internal molecule type to GROMACS names
MOLECULE_TO_GROMACS: dict[str, dict[str, str]] = {
    "ice":   {"res_name": "SOL", "itp_file": "tip4p-ice.itp", "mol_name": "SOL"},
    "water": {"res_name": "SOL", "itp_file": "tip4p-ice.itp", "mol_name": "SOL"},
    "na":    {"res_name": "NA",  "itp_file": "na.itp",     "mol_name": "NA"},
    "cl":    {"res_name": "CL",  "itp_file": "cl.itp",     "mol_name": "CL"},
    "ch4":   {"res_name": "CH4", "itp_file": "ch4.itp",    "mol_name": "CH4"},
    "thf":   {"res_name": "THF", "itp_file": "thf.itp",    "mol_name": "THF"},
    "co2":   {"res_name": "CO2", "itp_file": "co2.itp",    "mol_name": "CO2"},
    "h2":    {"res_name": "H2",  "itp_file": "h2.itp",     "mol_name": "H2"},
}


def write_gro_file(candidate: Candidate, filepath: str) -> None:
    """Write candidate to GROMACS .gro format.
    
    Args:
        candidate: Candidate object with positions, atom_names, cell, nmolecules
        filepath: Output file path for .gro file
    
    Note:
        candidate.nmolecules may differ from the user's requested count due to
        crystal structure constraints. GenIce2 creates supercells to satisfy
        space group symmetry, so the actual count can be larger. For example:
          - ice Ih with requested nmol=216 may generate 432 molecules (2× supercell)
          - ice Ih with requested nmol=4 may generate 16 molecules (4× supercell)
        This is expected behavior and ensures the structure is physically valid.
        
        Ice structures store 3 atoms per molecule (O, H, H). The MW virtual site
        is computed at export time to produce TIP4P-ICE format (4 atoms per molecule).
        
        GROMACS .gro format limits atom and residue numbers to 5 digits.
        For systems with >99999 atoms, atom numbers wrap at 100000 (standard GROMACS convention).
        For systems with >99999 residues, residue numbers wrap at 100000.
    """
    nmol = candidate.nmolecules
    n_atoms = nmol * 4  # 4-point water: O, H1, H2, MW (MW computed from O, H, H)
    
    # Bounds check: ensure positions array is large enough
    # Ice candidates have 3 atoms per molecule (O, H, H), not 4
    expected_atoms = nmol * 3
    if len(candidate.positions) < expected_atoms:
        raise ValueError(
            f"positions has {len(candidate.positions)} atoms but "
            f"nmolecules={nmol} needs {expected_atoms} (3 atoms per ice molecule)"
        )
    
    with open(filepath, 'w') as f:
        # Title line
        f.write(f"Ice structure {candidate.phase_id} exported by QuickIce\n")

        # Number of atoms
        f.write(f"{n_atoms:5d}\n")

        # Atom lines: residue num, residue name, atom name, atom num, x, y, z
        # GROMACS .gro format (no velocities):
        #   resnr(5), resname(5), atomname(5), atomnr(5), x(8), y(8), z(8)
        # Total: 44 characters per line
        # Build all lines in memory first for better I/O performance
        lines = []
        atom_num = 0
        for mol_idx in range(nmol):
            base_idx = mol_idx * 3  # Ice has 3 atoms per molecule: O, H, H
            
            # Read O, H1, H2 positions from Candidate
            o_pos = candidate.positions[base_idx]
            h1_pos = candidate.positions[base_idx + 1]
            h2_pos = candidate.positions[base_idx + 2]
            
            # Compute MW virtual site position
            mw_pos = compute_mw_position(o_pos, h1_pos, h2_pos)

            # Wrap residue and atom numbers at 100000 (GROMACS convention for large systems)
            res_num = (mol_idx + 1) % 100000

            # Oxygen (OW)
            atom_num += 1
            atom_num_wrapped = atom_num % 100000
            lines.append(f"{res_num:5d}SOL  "
                        f"   OW{atom_num_wrapped:5d}"
                        f"{o_pos[0]:8.3f}{o_pos[1]:8.3f}{o_pos[2]:8.3f}\n")

            # Hydrogen 1 (HW1)
            atom_num += 1
            atom_num_wrapped = atom_num % 100000
            lines.append(f"{res_num:5d}SOL  "
                        f"  HW1{atom_num_wrapped:5d}"
                        f"{h1_pos[0]:8.3f}{h1_pos[1]:8.3f}{h1_pos[2]:8.3f}\n")

            # Hydrogen 2 (HW2)
            atom_num += 1
            atom_num_wrapped = atom_num % 100000
            lines.append(f"{res_num:5d}SOL  "
                        f"  HW2{atom_num_wrapped:5d}"
                        f"{h2_pos[0]:8.3f}{h2_pos[1]:8.3f}{h2_pos[2]:8.3f}\n")

            # Massless virtual site (MW)
            atom_num += 1
            atom_num_wrapped = atom_num % 100000
            lines.append(f"{res_num:5d}SOL  "
                        f"   MW{atom_num_wrapped:5d}"
                        f"{mw_pos[0]:8.3f}{mw_pos[1]:8.3f}{mw_pos[2]:8.3f}\n")

        f.writelines(lines)
        
        # Box vectors (triclinic: v1(x) v2(y) v3(z) v1(y) v1(z) v2(x) v2(z) v3(x) v3(y))
        cell = candidate.cell
        f.write(f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}"
                f"{cell[0,1]:10.5f}{cell[0,2]:10.5f}{cell[1,0]:10.5f}"
                f"{cell[1,2]:10.5f}{cell[2,0]:10.5f}{cell[2,1]:10.5f}\n")


def write_top_file(candidate: Candidate, filepath: str) -> None:
    """Write GROMACS topology file.
    
    Args:
        candidate: Candidate object with nmolecules and phase_id
        filepath: Output file path for .top file
    """
    nmol = candidate.nmolecules
    
    with open(filepath, 'w') as f:
        # Header
        f.write("; Generated by QuickIce\n")
        f.write("; TIP4P-ICE water model\n\n")
        
        # [ defaults ] - force field defaults
        f.write("; Defaults compitable with the Amber forcefield\n")
        f.write("[ defaults ]\n")
        f.write("; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ\n")
        f.write("1               2               yes             0.5     0.8333\n\n")
        
        # [ atomtypes ] - define custom atom types for TIP4P-ICE
        f.write("[ atomtypes ]\n")
        f.write("; name  bond_type  atomic_number  mass  charge  ptype  V              W\n")
        f.write("OW_ice      OW_ice     8           15.9994  0.0     A      0.31668e-3    0.88216e-6\n")
        f.write("HW_ice      HW_ice     1            1.0080  0.0     A      0.0          0.0\n")
        f.write("MW          MW          0            0.0000  0.0     V      0.0          0.0\n\n")
        
        # [ moleculetype ] - define SOL (water)
        f.write("[ moleculetype ]\n")
        f.write("; Name        nrexcl\n")
        f.write("SOL          2\n\n")
        
        # [ atoms ] - define atoms in molecule
        f.write("[ atoms ]\n")
        f.write(";   nr  type  resi  res  atom  cgnr     charge    mass\n")
        f.write("   1   OW_ice    1  SOL    OW     1       0.0  16.00000\n")
        f.write("   2   HW_ice    1  SOL   HW1     1     0.5897   1.00800\n")
        f.write("   3   HW_ice    1  SOL   HW2     1     0.5897   1.00800\n")
        f.write("   4   MW        1  SOL    MW     1    -1.1794   0.00000\n\n")
        
        # [ settles ] - TIP4P water geometry (for rigid water)
        f.write("[ settles ]\n")
        f.write("; i  funct  doh     dhh\n")
        f.write("  1    1    0.09572  0.15139\n\n")
        
        # [ virtual_sites3 ] - define MW virtual site
        f.write("[ virtual_sites3 ]\n")
        f.write("; Vsite from                    funct  a          b\n")
        f.write("   4     1       2       3       1      0.13458335 0.13458335\n\n")
        
        # [ exclusions ] - exclude virtual site from non-bonded
        f.write("[ exclusions ]\n")
        f.write("  1  2  3  4\n")
        f.write("  2  1  3  4\n")
        f.write("  3  1  2  4\n")
        f.write("  4  1  2  3\n\n")
        
        # [ system ] - system-level section
        f.write("[ system ]\n")
        f.write("; Name\n")
        f.write(f"{candidate.phase_id} exported by QuickIce\n\n")
        
        # [ molecules ] - molecule counts
        f.write("[ molecules ]\n")
        f.write("; Compound    #mols\n")
        f.write(f"SOL          {nmol}\n")


def get_tip4p_itp_path() -> Path:
    """Get the path to the bundled tip4p-ice.itp file.
    
    Returns:
        Path to the tip4p-ice.itp file in the data directory
    """
    # Try to find in the package
    import quickice
    package_dir = Path(quickice.__file__).parent
    itp_path = package_dir / "data" / "tip4p-ice.itp"
    
    if itp_path.exists():
        return itp_path
    
    # Fallback to project root (for development)
    return Path(__file__).parent.parent / "data" / "tip4p-ice.itp"


def compute_mw_position(o_pos: np.ndarray, h1_pos: np.ndarray, h2_pos: np.ndarray) -> np.ndarray:
    """Compute MW virtual site position for TIP4P-ICE water model.
    
    The MW (massless virtual site) is positioned along the bisector of the H-O-H angle.
    
    Args:
        o_pos: Oxygen position as (3,) array in nm
        h1_pos: Hydrogen 1 position as (3,) array in nm
        h2_pos: Hydrogen 2 position as (3,) array in nm
    
    Returns:
        MW position as (3,) array in nm
    
    Formula:
        MW = O + α*(H1-O) + α*(H2-O)
        where α = 0.13458335 (TIP4P-ICE specific)
    """
    return o_pos + TIP4P_ICE_ALPHA * (h1_pos - o_pos) + TIP4P_ICE_ALPHA * (h2_pos - o_pos)


def _get_molecule_atoms(atom_names: list[str]) -> list[str]:
    """Extract atom names for one complete guest molecule from the list.

    Handles various guest molecule types and their atom naming conventions.
    Works regardless of atom order (unlike _count_guest_atoms which assumes
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

    # THF: C5H8O (5 C, 8 H, 1 O = 14 atoms typically)
    # GenIce2 THF: O, C, C, C, C, H, H, H, H, H, C, H, H (13 atoms)
    if counts.get('O', 0) >= 1 and counts.get('C', 0) >= 4:
        # Return first 13 atoms as likely THF
        return sample[:13]

    # H2: just H atoms
    if set(sample[:2]) == {'H'} and len(sample) >= 2:
        return ['H', 'H']

    # CO2: C and O atoms
    if counts.get('C', 0) >= 1 and counts.get('O', 0) >= 2:
        return ['C', 'O', 'O']

    # If first atom is Me (united-atom methane), return 1 atom
    if sample[0] == 'Me':
        return ['Me']

    # Fallback: try using _count_guest_atoms
    count = _count_guest_atoms(atom_names, 0)
    if count > 0:
        return atom_names[:count]

    return []


def write_interface_gro_file(iface: InterfaceStructure, filepath: str) -> None:
    """Write interface structure to GROMACS .gro format.
    
    Ice molecules (3-atom: O, H, H) are normalized to 4-atom TIP4P-ICE format
    (OW, HW1, HW2, MW) at export time. Water molecules (4-atom: OW, HW1, HW2, MW)
    pass through unchanged. Guest molecules (CH4, THF, etc.) are exported with
    their native atom types.
    
    Atom arrangement in InterfaceStructure:
    - Ice: indices 0 to ice_atom_count-1 (3 atoms/mol for classic ice, 4 atoms/mol for hydrate)
    - Guests: indices ice_atom_count to ice_atom_count + guest_atom_count-1 (if guest_atom_count > 0)
    - Water: indices ice_atom_count + guest_atom_count onward (4 atoms/mol)
    
    Args:
        iface: InterfaceStructure object with combined ice + guests + water positions
        filepath: Output file path for .gro file
    
    Note:
        GROMACS .gro format limits atom and residue numbers to 5 digits.
        For systems with >99999 atoms, atom numbers wrap at 100000 (standard GROMACS convention).
        For systems with >99999 residues, residue numbers wrap at 100000.
    """
    # Calculate total atoms:
    # - Ice: ice_nmolecules * 3 input atoms -> ice_nmolecules * 4 output atoms (MW added)
    # - Guests: guest_atom_count (no MW, pass through as-is)
    # - Water: water_nmolecules * 4 (pass through as-is)
    ice_output_atoms = iface.ice_nmolecules * 4  # MW virtual site added
    guest_output_atoms = iface.guest_atom_count if iface.guest_atom_count > 0 else 0
    water_output_atoms = iface.water_nmolecules * 4
    n_atoms = ice_output_atoms + guest_output_atoms + water_output_atoms
    
    atom_num = 0

    with open(filepath, 'w') as f:
        # Title line
        f.write(f"Ice/water interface ({iface.mode}) exported by QuickIce\n")

        # Number of atoms
        f.write(f"{n_atoms:5d}\n")

        # Build all atom lines in memory for better I/O performance
        lines = []
        
        # Define boundaries
        ice_end = iface.ice_atom_count
        guest_start = ice_end
        guest_end = ice_end + iface.guest_atom_count
        water_start = guest_end
        
        # Detect atoms per ice molecule
        # Classic ice: 3 atoms (O, H, H) - uses "O" (not "OW")
        # Hydrate: 4 atoms (OW, HW1, HW2, MW) - uses "OW"
        ice_region_atom_names = iface.atom_names[:ice_end]
        has_ow_in_ice = "OW" in ice_region_atom_names
        atoms_per_ice_mol = 4 if has_ow_in_ice else 3

        # ICE MOLECULES: 3 atoms per molecule (O, H, H) → normalize to 4-atom
        # OR: 4 atoms per molecule (OW, HW1, HW2, MW) → normalize to 4-atom
        for mol_idx in range(iface.ice_nmolecules):
            base_idx = mol_idx * atoms_per_ice_mol
            o_pos = iface.positions[base_idx]
            
            # Get H positions based on atoms per molecule
            if atoms_per_ice_mol == 3:
                # Classic ice: O, H, H
                h1_pos = iface.positions[base_idx + 1]
                h2_pos = iface.positions[base_idx + 2]
            else:
                # Hydrate: OW, HW1, HW2, MW
                h1_pos = iface.positions[base_idx + 1]
                h2_pos = iface.positions[base_idx + 2]
            
            mw_pos = compute_mw_position(o_pos, h1_pos, h2_pos)

            # Wrap residue number at 100000 (GROMACS convention for large systems)
            res_num = (mol_idx + 1) % 100000

            # OW (oxygen)
            atom_num += 1
            atom_num_wrapped = atom_num % 100000
            lines.append(f"{res_num:5d}SOL  "
                        f"   OW{atom_num_wrapped:5d}"
                        f"{o_pos[0]:8.3f}{o_pos[1]:8.3f}{o_pos[2]:8.3f}\n")

            # HW1 (hydrogen 1)
            atom_num += 1
            atom_num_wrapped = atom_num % 100000
            lines.append(f"{res_num:5d}SOL  "
                        f"  HW1{atom_num_wrapped:5d}"
                        f"{h1_pos[0]:8.3f}{h1_pos[1]:8.3f}{h1_pos[2]:8.3f}\n")

            # HW2 (hydrogen 2)
            atom_num += 1
            atom_num_wrapped = atom_num % 100000
            lines.append(f"{res_num:5d}SOL  "
                        f"  HW2{atom_num_wrapped:5d}"
                        f"{h2_pos[0]:8.3f}{h2_pos[1]:8.3f}{h2_pos[2]:8.3f}\n")

            # MW (virtual site)
            atom_num += 1
            atom_num_wrapped = atom_num % 100000
            lines.append(f"{res_num:5d}SOL  "
                        f"   MW{atom_num_wrapped:5d}"
                        f"{mw_pos[0]:8.3f}{mw_pos[1]:8.3f}{mw_pos[2]:8.3f}\n")

        # GUEST MOLECULES: pass through with native atom types
        # Determine guest residue name by reading from itp file
        
        if iface.guest_atom_count > 0 and iface.guest_nmolecules > 0:
            guest_atom_names = iface.atom_names[guest_start:guest_end]
            
            # Determine guest type by analyzing all atom names
            # GenIce2 outputs atoms in different order than .itp:
            #   CH4: H, H, H, H, C (hydrogen first)
            #   THF: O, C, C, C, C, H, H, H, H, H, H, C, H (oxygen first in some versions)
            # Need to detect based on atom composition, not just first atom
            
            if guest_atom_names:
                # Count unique atom types to identify molecule
                unique_atoms = set(guest_atom_names[:10])  # Check first 10 atoms
                
                # CH4: Only has C and H atoms (5 atoms total)
                # THF: Has C, H, and O atoms (13 atoms total)
                # CO2: Has C and O atoms
                # H2: Has only H atoms
                
                # Get atoms for one molecule
                mol_atoms = _get_molecule_atoms(guest_atom_names)
                
                if mol_atoms:
                    mol_unique = set(mol_atoms)
                    
                    # CH4 detection: only C and H, typically 5 atoms
                    if 'C' in mol_unique and 'H' in mol_unique and 'O' not in mol_unique:
                        # Could be CH4 (5 atoms) - verify count
                        if len(mol_atoms) == 5:
                            guest_type = "ch4"
                        else:
                            # Unexpected - log warning but try ch4
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(f"Unexpected CH4-like molecule with {len(mol_atoms)} atoms")
                            guest_type = "ch4"  # Try anyway
                    # THF detection: has C, H, and O, typically 12-13 atoms
                    elif 'O' in mol_unique and 'C' in mol_unique:
                        guest_type = "thf"
                    # H2 detection: only H
                    elif mol_unique == {'H'}:
                        guest_type = "h2"
                    # CO2 detection: C and O
                    elif mol_unique == {'C', 'O'}:
                        guest_type = "co2"
                    else:
                        guest_type = None
                else:
                    guest_type = None
            else:
                guest_type = None
            
            # Get residue name from itp file (not hardcoded)
            if guest_type:
                guest_res_name = get_guest_residue_name(guest_type)
            else:
                guest_res_name = "UNK"
            
            # Group atoms by molecule and write
            mol_start = 0
            for mol_idx in range(iface.guest_nmolecules):
                guest_atoms = _count_guest_atoms(guest_atom_names, mol_start)
                mol_end = mol_start + guest_atoms
                
                # Get this molecule's atom names and positions
                mol_atom_names = guest_atom_names[mol_start:mol_end]
                mol_positions = iface.positions[guest_start + mol_start:guest_start + mol_end]
                
                # Reorder to match .itp canonical order (C first for ch4, O first for thf)
                reorder_mapping = None
                if guest_type == "ch4" or guest_type == "thf":
                    mol_atom_names, reorder_mapping = reorder_guest_atoms(mol_atom_names, guest_type)
                    # Also reorder positions to match the reordered names
                    if reorder_mapping is not None:
                        mol_positions = [mol_positions[i] for i in reorder_mapping]
                
                # Wrap residue number
                res_num = (iface.ice_nmolecules + mol_idx + 1) % 100000
                
                for i, (atom_name, pos) in enumerate(zip(mol_atom_names, mol_positions)):
                    atom_num += 1
                    atom_num_wrapped = atom_num % 100000
                    lines.append(f"{res_num:5d}{guest_res_name:<5s}"
                                f"{atom_name:>5s}{atom_num_wrapped:5d}"
                                f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")
                
                mol_start = mol_end

        # WATER MOLECULES: 4 atoms per molecule (OW, HW1, HW2, MW) → pass through
        for mol_idx in range(iface.water_nmolecules):
            base_idx = water_start + mol_idx * 4
            # Wrap residue number at 100000 (GROMACS convention for large systems)
            res_num = (iface.ice_nmolecules + iface.guest_nmolecules + mol_idx + 1) % 100000

            atom_names = ["OW", "HW1", "HW2", "MW"]
            for i, atom_name in enumerate(atom_names):
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                pos = iface.positions[base_idx + i]
                lines.append(f"{res_num:5d}SOL  "
                            f"{atom_name:>4s}{atom_num_wrapped:5d}"
                            f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")

        f.writelines(lines)
        
        # Box vectors (triclinic format)
        cell = iface.cell
        f.write(f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}"
                f"{cell[0,1]:10.5f}{cell[0,2]:10.5f}{cell[1,0]:10.5f}"
                f"{cell[1,2]:10.5f}{cell[2,0]:10.5f}{cell[2,1]:10.5f}\n")


def _count_guest_atoms(atom_names: list[str], start: int) -> int:
    """Count atoms in a guest molecule starting at index.

    Handles GenIce2 output where atom order may not match .itp canonical order.
    For CH4, GenIce2 outputs H, H, H, H, C (H first), while .itp expects C first.

    Args:
        atom_names: List of atom names in guest region
        start: Starting index within atom_names

    Returns:
        Number of atoms in this guest molecule
    """
    if start >= len(atom_names):
        return 0

    # Strategy: look at the next several atoms to determine molecule type
    # Check up to 15 atoms ahead to identify the pattern
    sample = atom_names[start:min(start + 15, len(atom_names))]

    if not sample:
        return 0

    first_atom = sample[0]

    # United-atom methane (Me) - single carbon
    if first_atom == "Me":
        return 1

    # All-atom methane: C + 4H = 5 atoms
    # GenIce2 may output as: H, H, H, H, C (H first) or C, H, H, H, H (C first)
    if first_atom == "C" or (first_atom == "H" and len(sample) >= 5):
        # Check if this looks like CH4
        # Count C and H atoms in the sample
        c_count = sum(1 for a in sample if a == 'C')
        h_count = sum(1 for a in sample if a == 'H')

        # CH4 has exactly 1 C and 4 H
        if c_count >= 1 and h_count >= 4 and (c_count + h_count) >= 5:
            # Return 5 atoms for CH4
            # Find where the 5-atom group ends
            count = 0
            c_found = 0
            h_found = 0
            for atom in sample:
                if atom == 'C' and c_found == 0:
                    c_found += 1
                    count += 1
                elif atom == 'H' and h_found < 4:
                    h_found += 1
                    count += 1
                if count >= 5:
                    break
            return max(count, 5)  # At least 5 for CH4

    # THF: C5H8O = 14 atoms, but GenIce2 outputs 13 atoms (some versions)
    # Atoms: O, C, C, C, C, H, H, H, H, H, H, C, H, H (14) or similar
    if first_atom in ["O", "C"]:
        # Check if this looks like THF (has O, multiple C, multiple H)
        has_oxygen = any(a == 'O' for a in sample)
        has_carbon = sum(1 for a in sample if a == 'C') >= 4
        if has_oxygen and has_carbon:
            # Count until we see a pattern break (OW, or different atom type)
            count = 0
            i = start
            while i < len(atom_names):
                if atom_names[i] == "OW":
                    break
                count += 1
                i += 1
                if count > 20:  # Safety limit
                    break
            return max(count, 13)  # At least 13 for THF
        elif first_atom == "C":
            # Just carbon atoms - might be part of THF or other molecule
            count = 0
            i = start
            while i < len(atom_names) and count < 15:
                count += 1
                i += 1
            return count

    # H2: two hydrogen atoms
    if first_atom == "H":
        # Check if next atom is also H (H2 molecule)
        if len(sample) >= 2 and sample[1] == 'H':
            return 2
        # Otherwise might be CH4 with H first - but we handled that above
        # Default: assume single H atom
        return 1

    # CO2: C and O atoms
    if first_atom == "C" and any(a == 'O' for a in sample[:3]):
        return 3  # C + O + O

    # Default: treat as 1 atom guest
    return 1


def write_interface_top_file(iface: InterfaceStructure, filepath: str) -> None:
    """Write GROMACS topology file for interface structure.
    
    Writes topology with SOL (water) for ice + water, and CH4/THF for guests
    if present. Uses #include directives for molecule definitions.
    
    Args:
        iface: InterfaceStructure object with ice, guest, and water counts
        filepath: Output file path for .top file
    """
    total_molecules = iface.ice_nmolecules + iface.guest_nmolecules + iface.water_nmolecules
    
    with open(filepath, 'w') as f:
        # Header
        f.write("; Generated by QuickIce\n")
        f.write("; TIP4P-ICE water model\n")
        f.write("; Ice/water interface structure\n\n")
        
        # [ defaults ] - force field defaults
        f.write("; Defaults compitable with the Amber forcefield\n")
        f.write("[ defaults ]\n")
        f.write("; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ\n")
        f.write("1               2               yes             0.5     0.8333\n\n")
        
        # [ atomtypes ] - define custom atom types for TIP4P-ICE and guests
        f.write("[ atomtypes ]\n")
        f.write("; name  bond_type  atomic_number  mass  charge  ptype  V              W\n")
        f.write("OW_ice      OW_ice     8           15.9994  0.0     A      0.31668e-3    0.88216e-6\n")
        f.write("HW_ice      HW_ice     1            1.0080  0.0     A      0.0          0.0\n")
        f.write("MW          MW          0            0.0000  0.0     V      0.0          0.0\n")
        
        # Guest atom types if guests are present
        if iface.guest_atom_count > 0:
            # CH4 atom types (GAFF2) - common for methane
            f.write("; CH4 atom types (GAFF2)\n")
            f.write("c3        c3        6             12.0107  0.0     A      3.39771e-1    4.51035e-1\n")
            f.write("hc        hc        1              1.0079  0.0     A      2.60018e-1    8.70272e-2\n")
        
        f.write("\n")
        
        # Include molecule definitions (after atomtypes, as GROMACS requires)
        f.write("; Molecule definitions\n")
        f.write('#include "tip4p-ice.itp"\n')
        
        if iface.guest_nmolecules > 0:
            # Determine guest type from atom names
            if iface.guest_atom_count > 0:
                ice_end = iface.ice_atom_count
                first_guest_atom = iface.atom_names[ice_end] if ice_end < len(iface.atom_names) else "C"
                if first_guest_atom in ["Me", "C"]:
                    f.write('#include "ch4.itp"\n')
                elif first_guest_atom in ["O", "C"]:  # THF
                    f.write('#include "thf.itp"\n')
        
        f.write("\n")
        
        # [ system ] - system-level section
        f.write("[ system ]\n")
        f.write("; Name\n")
        f.write(f"Ice/water interface ({iface.mode}) exported by QuickIce\n\n")
        
        # [ molecules ] - molecule counts
        f.write("[ molecules ]\n")
        f.write("; Compound    #mols\n")
        f.write(f"SOL          {iface.ice_nmolecules + iface.water_nmolecules}\n")
        
        if iface.guest_nmolecules > 0:
            # Determine guest residue name from itp file
            if iface.guest_atom_count > 0:
                ice_end = iface.ice_atom_count
                first_guest_atom = iface.atom_names[ice_end] if ice_end < len(iface.atom_names) else "C"
                if first_guest_atom in ["Me", "C"]:
                    # Could be CH4 (5 atoms) or THF (13 atoms starting with C)
                    # Count atoms to determine
                    count = _count_guest_atoms(iface.atom_names[ice_end:ice_end + 20], 0)
                    if count <= 5:
                        guest_type = "ch4"
                    else:
                        guest_type = "thf"
                elif first_guest_atom in ["O", "c"]:
                    guest_type = "thf"
                else:
                    guest_type = None
                
                if guest_type:
                    guest_res_name = get_guest_residue_name(guest_type)
                    f.write(f"{guest_res_name:<10s} {iface.guest_nmolecules}\n")
                else:
                    f.write(f"UNK          {iface.guest_nmolecules}\n")


def write_multi_molecule_gro_file(
    positions: np.ndarray,
    molecule_index: list[MoleculeIndex],
    cell: np.ndarray,
    filepath: str,
    title: str = "Multi-molecule system exported by QuickIce",
    atom_names: list[str] | None = None
) -> None:
    """Write multi-molecule system to GROMACS .gro format.
    
    Uses MoleculeIndex list to determine atom counts per molecule type.
    
    Args:
        positions: (N_atoms, 3) coordinates in nm
        molecule_index: List of MoleculeIndex objects tracking each molecule
        cell: (3, 3) cell vectors in nm
        filepath: Output file path
        title: Title line for .gro file
        atom_names: Optional list of atom names. If provided, uses actual names.
                   If None, uses generic "XX" placeholder.
    
    Note:
        GROMACS .gro format limits atom and residue numbers to 5 digits.
        For systems with >99999 atoms, numbers wrap at 100000.
    """
    n_atoms = len(positions)
    
    with open(filepath, 'w') as f:
        f.write(f"{title}\n")
        f.write(f"{n_atoms:5d}\n")
        
        lines = []
        atom_num = 0
        for mol in molecule_index:
            # Get residue name from itp file for guest molecules
            if mol.mol_type in ["ch4", "thf", "co2", "h2"]:
                res_name = get_guest_residue_name(mol.mol_type)
            else:
                gromacs_info = MOLECULE_TO_GROMACS.get(mol.mol_type, {"res_name": "UNK"})
                res_name = gromacs_info["res_name"]
            
            # Residue number wraps at 100000
            res_num = (molecule_index.index(mol) + 1) % 100000
            
            # Get atom names and positions for this molecule
            mol_atom_names = []
            mol_positions = positions[mol.start_idx:mol.start_idx + mol.count]
            if atom_names is not None:
                mol_atom_names = atom_names[mol.start_idx:mol.start_idx + mol.count]
            
            # Reorder guest atoms to match .itp canonical order
            # For water, ice (TIP4P), ion molecules: use as-is
            # For guest molecules (CH4, THF): reorder to match .itp
            if mol.mol_type in ["ch4", "thf"] and mol_atom_names:
                mol_atom_names, reorder_mapping = reorder_guest_atoms(mol_atom_names, mol.mol_type)
                # Also reorder positions to match the reordered names
                if reorder_mapping is not None:
                    mol_positions = [mol_positions[i] for i in reorder_mapping]
            
            # Write atoms for this molecule
            for i in range(mol.count):
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                pos = mol_positions[i]
                
                # Use actual atom name if provided, otherwise use generic "XX"
                if mol_atom_names:
                    actual_name = mol_atom_names[i]
                else:
                    actual_name = "XX"
                
                lines.append(f"{res_num:5d}{res_name:<5s}"
                            f"{actual_name:>5s}{atom_num_wrapped:5d}"
                            f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")
        
        f.writelines(lines)
        
        # Box vectors (triclinic format)
        f.write(f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}"
                f"{cell[0,1]:10.5f}{cell[0,2]:10.5f}{cell[1,0]:10.5f}"
                f"{cell[1,2]:10.5f}{cell[2,0]:10.5f}{cell[2,1]:10.5f}\n")


def write_multi_molecule_top_file(
    molecule_index: list[MoleculeIndex],
    filepath: str,
    system_name: str = "Multi-molecule system",
    itp_files: dict[str, str] | None = None,
) -> None:
    """Write GROMACS topology file with multiple moleculetypes.
    
    Uses #include directives for each molecule type's .itp file.
    CRITICAL: All [atomtypes] must be grouped after [ defaults ] and before #include directives.
    
    Args:
        molecule_index: List of MoleculeIndex objects
        filepath: Output file path for .top
        system_name: Name for [ system ] section
        itp_files: Optional mapping of mol_type -> itp path to use instead of bundled
                   Example: {"ch4": "/path/to/custom_ch4.itp"}
    
    Note:
        The main .top file uses #include to include separate .itp files.
        Bundled .itp files are in quickice/data/ directory.
        User-provided .itp files (ch4.itp, thf.itp) should have [atomtypes] section
        commented out, as types are defined in the main .top file.
    """
    # Count molecules by type
    counts: dict[str, int] = {}
    unique_types: list[str] = []
    
    for mol in molecule_index:
        if mol.mol_type not in counts:
            counts[mol.mol_type] = 0
            unique_types.append(mol.mol_type)
        counts[mol.mol_type] += 1
    
    # Build [ molecules ] section entries in order of first appearance
    molecules_lines = []
    for mol_type in unique_types:
        # Get residue name from itp file if available
        if mol_type in ["ch4", "thf", "co2", "h2"]:
            res_name = get_guest_residue_name(mol_type)
        else:
            gromacs_info = MOLECULE_TO_GROMACS.get(mol_type, {"mol_name": "UNK"})
            res_name = gromacs_info.get("mol_name", "UNK")
        count = counts[mol_type]
        molecules_lines.append(f"{res_name:<15s} {count:10d}")
    
    # Build list of .itp files to include
    itp_includes: list[str] = []
    included_files: set[str] = set()
    for mol_type in unique_types:
        gromacs_info = MOLECULE_TO_GROMACS.get(mol_type, {"itp_file": "unknown.itp"})
        if itp_files and mol_type in itp_files:
            itp_path = itp_files[mol_type]
        else:
            itp_path = gromacs_info["itp_file"]
        if itp_path not in included_files:
            itp_includes.append(itp_path)
            included_files.add(itp_path)
    
    with open(filepath, 'w') as f:
        # Header
        f.write("; Generated by QuickIce\n")
        f.write("; Multi-molecule topology\n")
        f.write("; TIP4P-ICE water, Madrid2019 ions, GAFF2 guest molecules\n\n")
        
        # [ defaults ] - force field defaults (TIP4P-ICE compatible)
        f.write("[ defaults ]\n")
        f.write("; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ\n")
        f.write("1               2               yes             0.5     0.8333\n\n")
        
        # [ atomtypes ] - MUST be grouped after [ defaults ] and before #include
        # GROMACS requires all atomtypes before any #include directives
        f.write("[ atomtypes ]\n")
        f.write("; name   bond_type  atomic_number  mass     charge  ptype  sigma (nm)    epsilon (kJ/mol)\n")
        
        # TIP4P-ICE water atom types
        f.write("OW_ice   OW_ice    8             15.9994  0.0     A      0.31668e-3    0.88216e-6\n")
        f.write("HW_ice   HW_ice    1              1.0080  0.0     A      0.0           0.0\n")
        f.write("MW       MW        0              0.0000  0.0     V      0.0           0.0\n")
        
        # Madrid2019 ion atom types (if ions present)
        if "na" in unique_types or "cl" in unique_types:
            f.write("; Ion atom types (Madrid2019)\n")
            if "na" in unique_types:
                f.write("NA        NA        11            22.9898  0.0     A      2.21737e-1    1.47236e0\n")
            if "cl" in unique_types:
                f.write("CL        CL        17            35.453   0.0     A      4.69906e-1    7.69231e-2\n")
        
        # GAFF2 atom types for CH4 (if present)
        if "ch4" in unique_types:
            f.write("; CH4 atom types (GAFF2)\n")
            f.write("c3        c3        6             12.0107  0.0     A      3.39771e-1    4.51035e-1\n")
            f.write("hc        hc        1              1.0079  0.0     A      2.60018e-1    8.70272e-2\n")
        
        # GAFF2 atom types for THF (if present)
        if "thf" in unique_types:
            f.write("; THF atom types (GAFF2)\n")
            f.write("os        os        8             15.9994  0.0     A      3.15610e-1    3.03758e-1\n")
            f.write("c5        c5        6             12.0107  0.0     A      3.39771e-1    4.51035e-1\n")
            f.write("hc        hc        1              1.0079  0.0     A      2.60018e-1    8.70272e-2\n")
            f.write("h1        h1        1              1.0079  0.0     A      2.42200e-1    8.70272e-2\n")
        
        # GAFF2 atom types for CO2 (if present)
        if "co2" in unique_types:
            f.write("; CO2 atom types (GAFF2)\n")
            f.write("c_2       c_2       6             12.0107  0.0     A      3.39955e-1    4.39089e-1\n")
            f.write("o_2       o_2       8             15.9994  0.0     A      3.02714e-1    8.80314e-1\n")
        
        # GAFF2 atom types for H2 (if present)
        if "h2" in unique_types:
            f.write("; H2 atom types (GAFF2)\n")
            f.write("hn        hn        1              1.0080  0.0     A      0.0           0.0\n")
        
        f.write("\n")
        
        # Include molecule definitions (AFTER atomtypes)
        f.write("; Molecule definitions\n")
        for itp_path in itp_includes:
            f.write(f'#include "{itp_path}"\n')
        
        f.write("\n")
        
        # [ system ] section
        f.write("[ system ]\n")
        f.write(f"{system_name}\n\n")
        
        # [ molecules ] section
        f.write("[ molecules ]\n")
        f.write("; Compound        #mols\n")
        for line in molecules_lines:
            f.write(f"{line}\n")


def write_ion_gro_file(ion_structure: IonStructure, filepath: str) -> None:
    """Write ion structure to GROMACS .gro format.
    
    Exports water molecules (4-atom TIP4P-ICE format) plus Na+ and Cl- ions.
    Uses molecule_index to determine which atoms are water vs ions.
    
    Args:
        ion_structure: IonStructure object with water + ion positions
        filepath: Output file path for .gro file
    
    Note:
        GROMACS .gro format limits atom and residue numbers to 5 digits.
        For systems with >99999 atoms, atom numbers wrap at 100000 (standard GROMACS convention).
    """
    # Count total atoms: water (4 atoms/mol) + ions (1 atom/mol) + guest (variable atoms/mol)
    water_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "water")
    guest_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "guest")
    # Also sum guest atoms (each guest may have different atom count)
    guest_atoms = sum(m.count for m in ion_structure.molecule_index if m.mol_type == "guest")
    total_atoms = water_count * 4 + ion_structure.na_count + ion_structure.cl_count + guest_atoms
    
    atom_num = 0
    res_num = 0
    
    with open(filepath, 'w') as f:
        # Title line
        f.write(f"Ice/water + ions ({ion_structure.na_count} Na+, {ion_structure.cl_count} Cl-) exported by QuickIce\n")
        
        # Number of atoms
        f.write(f"{total_atoms:5d}\n")
        
        # Build all atom lines in memory for better I/O performance
        lines = []
        
        # Process each molecule from molecule_index
        for mol in ion_structure.molecule_index:
            if mol.mol_type == "water":
                # Water molecule: 4 atoms (OW, HW1, HW2, MW)
                res_num += 1
                res_num_wrapped = res_num % 100000
                
                start = mol.start_idx
                # Get positions - water has OW, HW1, HW2 (MW computed)
                o_pos = ion_structure.positions[start]
                h1_pos = ion_structure.positions[start + 1]
                h2_pos = ion_structure.positions[start + 2]
                mw_pos = compute_mw_position(o_pos, h1_pos, h2_pos)
                
                # OW (oxygen)
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                lines.append(f"{res_num_wrapped:5d}SOL  "
                            f"   OW{atom_num_wrapped:5d}"
                            f"{o_pos[0]:8.3f}{o_pos[1]:8.3f}{o_pos[2]:8.3f}\n")
                
                # HW1 (hydrogen 1)
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                lines.append(f"{res_num_wrapped:5d}SOL  "
                            f"  HW1{atom_num_wrapped:5d}"
                            f"{h1_pos[0]:8.3f}{h1_pos[1]:8.3f}{h1_pos[2]:8.3f}\n")
                
                # HW2 (hydrogen 2)
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                lines.append(f"{res_num_wrapped:5d}SOL  "
                            f"  HW2{atom_num_wrapped:5d}"
                            f"{h2_pos[0]:8.3f}{h2_pos[1]:8.3f}{h2_pos[2]:8.3f}\n")
                
                # MW (virtual site)
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                lines.append(f"{res_num_wrapped:5d}SOL  "
                            f"   MW{atom_num_wrapped:5d}"
                            f"{mw_pos[0]:8.3f}{mw_pos[1]:8.3f}{mw_pos[2]:8.3f}\n")
            
            elif mol.mol_type == "na":
                # Na+ ion
                res_num += 1
                res_num_wrapped = res_num % 100000
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                pos = ion_structure.positions[mol.start_idx]
                lines.append(f"{res_num_wrapped:5d}NA   "
                            f"   NA{atom_num_wrapped:5d}"
                            f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")
            
            elif mol.mol_type == "cl":
                # Cl- ion
                res_num += 1
                res_num_wrapped = res_num % 100000
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                pos = ion_structure.positions[mol.start_idx]
                lines.append(f"{res_num_wrapped:5d}CL   "
                            f"   CL{atom_num_wrapped:5d}"
                            f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")
            
            elif mol.mol_type == "guest":
                # Guest molecule (CH4, THF, etc.) - write all atoms
                res_num += 1
                res_num_wrapped = res_num % 100000
                
                start = mol.start_idx
                for atom_offset in range(mol.count):
                    atom_num += 1
                    atom_num_wrapped = atom_num % 100000
                    atom_name = ion_structure.atom_names[start + atom_offset]
                    pos = ion_structure.positions[start + atom_offset]
                    lines.append(f"{res_num_wrapped:5d}GUE  "
                                f"{atom_name[0:4]:4s}{atom_num_wrapped:5d}"
                                f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")
        
        f.writelines(lines)
        
        # Box vectors (triclinic format)
        cell = ion_structure.cell
        f.write(f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}"
                f"{cell[0,1]:10.5f}{cell[0,2]:10.5f}{cell[1,0]:10.5f}"
                f"{cell[1,2]:10.5f}{cell[2,0]:10.5f}{cell[2,1]:10.5f}\n")


def write_ion_top_file(ion_structure: IonStructure, filepath: str) -> None:
    """Write GROMACS topology file for ion structure.
    
    Uses SOL molecule type for water, NA for sodium, CL for chloride.
    Includes guest molecules if present.
    
    Args:
        ion_structure: IonStructure object with water and ion counts
        filepath: Output file path for .top file
    """
    water_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "water")
    guest_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "guest")
    
    with open(filepath, 'w') as f:
        # Header
        f.write("; Generated by QuickIce\n")
        f.write("; TIP4P-ICE water model with NaCl ions")
        if guest_count > 0:
            f.write(" and guest molecules")
        f.write("\n")
        f.write(f"; Structure: {water_count} water + {guest_count} guests + {ion_structure.na_count} Na+ + {ion_structure.cl_count} Cl-\n\n")
        
        # Default GROMACS directives
        f.write("[ defaults ]\n")
        f.write("; nbfunc        comb-rule       gen-pairs       fudgeLJ fudgeQQ\n")
        f.write("1               2               yes             0.0     0.0\n\n")
        
        # Include water itp
        f.write('#include "tip4p-ice.itp"\n')

        # Include guest itp if guests present
        if guest_count > 0:
            # Need to include guest parameters - for now use generic guest.itp
            # In production, would need proper guest .itp files based on guest type
            f.write('#include "guest.itp"\n')
        
        # Include ion itp (from ion export - combined NA+CL in single file)
        f.write('#include "ion.itp"\n\n')
        
        # [ system ] section
        f.write("[ system ]\n")
        system_name = f"Ice/water + {guest_count} guests + {ion_structure.na_count} Na+ + {ion_structure.cl_count} Cl- ions"
        f.write(f"{system_name}\n\n")
        
        # [ molecules ] section
        f.write("[ molecules ]\n")
        f.write("; Compound        #mols\n")
        f.write(f"SOL              {water_count}\n")
        # Write guest molecule counts (group all guests as GUE)
        if guest_count > 0:
            f.write(f"GUE              {guest_count}\n")
        f.write(f"NA               {ion_structure.na_count}\n")
        f.write(f"CL               {ion_structure.cl_count}\n")
