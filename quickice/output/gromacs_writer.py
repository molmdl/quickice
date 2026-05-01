"""GROMACS file writers for ice structure export.

Provides functions to write GROMACS coordinate (.gro) and topology (.top) files
from generated ice structure candidates using the TIP4P-ICE water model.
"""

from pathlib import Path
from typing import Optional

import numpy as np

from quickice.structure_generation.types import Candidate, InterfaceStructure, IonStructure, MoleculeIndex, MOLECULE_TYPE_INFO


def wrap_positions_into_box(positions: np.ndarray, cell: np.ndarray) -> np.ndarray:
    """Wrap positions into the simulation box [0, cell[i,i]).
    
    For molecules spanning PBC boundaries, some atoms may be outside [0, boxsize).
    This function wraps each coordinate individually into the box for GRO file output.
    
    Args:
        positions: (N, 3) atom positions in nm
        cell: (3, 3) cell vectors as ROW vectors
    
    Returns:
        (N, 3) positions wrapped into [0, cell[i,i])
    """
    wrapped = positions.copy()
    for dim in range(3):
        # Wrap using modulo: coord % box_size
        # np.mod handles negative numbers correctly
        wrapped[:, dim] = np.mod(wrapped[:, dim], cell[dim, dim])
    return wrapped


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
    if reorder and all(i < len(atom_names) for i in reorder):
        return list(canonical), reorder

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
    
    # Wrap positions into box for GRO file output
    # Molecules spanning PBC boundaries can have atoms outside [0, boxsize)
    # We wrap them here for valid GRO format
    wrapped_positions = wrap_positions_into_box(candidate.positions, candidate.cell)
    
    # Bounds check: ensure positions array is large enough
    # Ice candidates have 3 atoms per molecule (O, H, H), not 4
    expected_atoms = nmol * 3
    if len(wrapped_positions) < expected_atoms:
        raise ValueError(
            f"positions has {len(wrapped_positions)} atoms but "
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
            
            # Read O, H1, H2 positions from wrapped positions
            o_pos = wrapped_positions[base_idx]
            h1_pos = wrapped_positions[base_idx + 1]
            h2_pos = wrapped_positions[base_idx + 2]
            
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

    # THF: C5H8O (5 C, 8 H, 1 O = 14 atoms typically)
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
    
    Atom arrangement in InterfaceStructure (after slab.py fix):
    - Ice: indices 0 to ice_atom_count-1 (3 atoms/mol for classic ice, 4 atoms/mol for hydrate)
    - Water: indices ice_atom_count to ice_atom_count + water_atom_count-1
    - Guests: indices ice_atom_count + water_atom_count onward (if guest_atom_count > 0)
    
    Args:
        iface: InterfaceStructure object with combined ice + water + guests positions
        filepath: Output file path for .gro file
    
    Note:
        GROMACS .gro format limits atom and residue numbers to 5 digits.
        For systems with >99999 atoms, atom numbers wrap at 100000 (standard GROMACS convention).
        For systems with >99999 residues, residue numbers wrap at 100000.
    """
    # Calculate total atoms:
    # - Ice: ice_nmolecules * 3 input atoms -> ice_nmolecules * 4 output atoms (MW added)
    # - Water: water_nmolecules * 4 (pass through as-is)
    # - Guests: guest_atom_count (no MW, pass through as-is)
    ice_output_atoms = iface.ice_nmolecules * 4  # MW virtual site added
    water_output_atoms = iface.water_nmolecules * 4
    guest_output_atoms = iface.guest_atom_count if iface.guest_atom_count > 0 else 0
    n_atoms = ice_output_atoms + water_output_atoms + guest_output_atoms
    
    # Wrap positions into box for GRO file output
    # Molecules spanning PBC boundaries can have atoms outside [0, boxsize)
    # We wrap them here for valid GRO format
    wrapped_positions = wrap_positions_into_box(iface.positions, iface.cell)
    
    atom_num = 0

    with open(filepath, 'w') as f:
        # Title line
        f.write(f"Ice/water interface ({iface.mode}) exported by QuickIce\n")

        # Number of atoms
        f.write(f"{n_atoms:5d}\n")

        # Build all atom lines in memory for better I/O performance
        lines = []
        
        # Define boundaries (NEW ORDER: ice → water → guests)
        ice_end = iface.ice_atom_count
        water_start = ice_end
        water_end = ice_end + iface.water_atom_count
        guest_start = water_end
        
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
            o_pos = wrapped_positions[base_idx]
            
            # Get H positions based on atoms per molecule
            if atoms_per_ice_mol == 3:
                # Classic ice: O, H, H
                h1_pos = wrapped_positions[base_idx + 1]
                h2_pos = wrapped_positions[base_idx + 2]
            else:
                # Hydrate: OW, HW1, HW2, MW
                h1_pos = wrapped_positions[base_idx + 1]
                h2_pos = wrapped_positions[base_idx + 2]
            
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

        # WATER MOLECULES: 4 atoms per molecule (OW, HW1, HW2, MW) → pass through
        # Write WATER BEFORE guests (new order: ice → water → guests)
        for mol_idx in range(iface.water_nmolecules):
            base_idx = water_start + mol_idx * 4
            # Wrap residue number at 100000 (GROMACS convention for large systems)
            res_num = (iface.ice_nmolecules + mol_idx + 1) % 100000

            atom_names = ["OW", "HW1", "HW2", "MW"]
            for i, atom_name in enumerate(atom_names):
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                pos = wrapped_positions[base_idx + i]
                lines.append(f"{res_num:5d}SOL  "
                            f"{atom_name:>5s}{atom_num_wrapped:5d}"
                            f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")

        # GUEST MOLECULES: pass through with native atom types
        # Write guests AFTER water (new order: ice → water → guests)
        
        if iface.guest_atom_count > 0 and iface.guest_nmolecules > 0:
            guest_atom_names = iface.atom_names[guest_start:]
            
            # Determine guest type by analyzing all atom names
            # GenIce2 outputs atoms in different order than .itp:
            #   CH4: H, H, H, H, C (hydrogen first)
            #   THF: O, C, C, C, C, H, H, H, H, H, H, C, H (oxygen first in some versions)
            # Need to detect based on atom composition, not just first atom
            
            if guest_atom_names:
                # Detect guest type using the centralized function
                guest_type = detect_guest_type_from_atoms(guest_atom_names)
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
                mol_positions = wrapped_positions[guest_start + mol_start:guest_start + mol_end]
                
                # Reorder to match .itp canonical order (C first for ch4, O first for thf)
                reorder_mapping = None
                if guest_type == "ch4" or guest_type == "thf":
                    mol_atom_names, reorder_mapping = reorder_guest_atoms(mol_atom_names, guest_type)
                    # Also reorder positions to match the reordered names
                    if reorder_mapping is not None:
                        mol_positions = [mol_positions[i] for i in reorder_mapping]
                
                # Wrap residue number (guests come after all SOL molecules)
                res_num = (iface.ice_nmolecules + iface.water_nmolecules + mol_idx + 1) % 100000
                
                for i, (atom_name, pos) in enumerate(zip(mol_atom_names, mol_positions)):
                    atom_num += 1
                    atom_num_wrapped = atom_num % 100000
                    lines.append(f"{res_num:5d}{guest_res_name:<5s}"
                                f"{atom_name:>5s}{atom_num_wrapped:5d}"
                                f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")
                
                mol_start = mol_end

        f.writelines(lines)
        
        # Box vectors (triclinic format)
        cell = iface.cell
        f.write(f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}"
                f"{cell[0,1]:10.5f}{cell[0,2]:10.5f}{cell[1,0]:10.5f}"
                f"{cell[1,2]:10.5f}{cell[2,0]:10.5f}{cell[2,1]:10.5f}\n")


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
    
    # THF: Has O and carbon atoms (CA, CB, or C) (check BEFORE CH4)
    # THF atoms are: O, CA, CA, CB, CB, H, H, H, H, H, H, H, H (13 atoms)
    if has_oxygen and has_carbon:
        return "thf"
    
    # CH4: Only C and H, no O, typically 5 atoms
    elif has_carbon and has_hydrogen and not has_oxygen:
        return "ch4"
    
    # H2: Only H atoms (2 atoms)
    elif mol_unique == {'H'}:
        return "h2"
    
    # CO2: C and O atoms (3 atoms, no H)
    elif has_carbon and has_oxygen and not has_hydrogen:
        return "co2"
    
    # United-atom methane
    elif mol_unique == {'Me'}:
        return "ch4"
    
    return None


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
    # Atoms: O, CA, CA, CB, CB, H, H, H, H, H, H, H, H (13 atoms)
    # Note: Carbon atoms can be named C, CA, or CB
    if first_atom == "O":
        # THF starts with O and has 13 atoms
        return 13
    
    if first_atom in ["C", "CA", "CB"]:
        # Check if this looks like THF (has O in next few atoms)
        if start + 1 < len(atom_names):
            next_atoms = atom_names[start:start + 15]
            if 'O' in next_atoms:
                # THF has O, return 13
                return 13
        # Just carbon - might be CH4 or CO2, handled elsewhere

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
        # Detect guest type from atom names (similar to write_ion_top_file)
        guest_type = None
        if iface.guest_atom_count > 0 and iface.guest_nmolecules > 0:
            # Get atom names for the guest region
            # NEW ORDER: ice → water → guests
            # Guest atoms start at ice_atom_count + water_atom_count
            guest_start = iface.ice_atom_count + iface.water_atom_count
            guest_end = guest_start + iface.guest_atom_count
            guest_atom_names = iface.atom_names[guest_start:guest_end]
            guest_type = detect_guest_type_from_atoms(guest_atom_names)
        
        if iface.guest_atom_count > 0 and guest_type:
            if guest_type == "ch4":
                # CH4 atom types (GAFF2)
                f.write("; CH4 atom types (GAFF2)\n")
                f.write("c3        c3        6             12.0107  0.0     A      3.39771e-1    4.51035e-1\n")
                f.write("hc        hc        1              1.0079  0.0     A      2.60018e-1    8.70272e-2\n")
            elif guest_type == "thf":
                # THF atom types (GAFF2)
                f.write("; THF atom types (GAFF2)\n")
                f.write("os        os        8             15.9994  0.0     A      3.15610e-1    3.03758e-1\n")
                f.write("c5        c5        6             12.0107  0.0     A      3.39771e-1    4.51035e-1\n")
                f.write("hc        hc        1              1.0079  0.0     A      2.60018e-1    8.70272e-2\n")
                f.write("h1        h1        1              1.0079  0.0     A      2.42200e-1    8.70272e-2\n")
            elif guest_type == "co2":
                # CO2 atom types (GAFF2)
                f.write("; CO2 atom types (GAFF2)\n")
                f.write("c_2       c_2       6             12.0107  0.0     A      3.39955e-1    4.39089e-1\n")
                f.write("o_2       o_2       8             15.9994  0.0     A      3.02714e-1    8.80314e-1\n")
            elif guest_type == "h2":
                # H2 atom types (GAFF2)
                f.write("; H2 atom types (GAFF2)\n")
                f.write("hn        hn        1              1.0080  0.0     A      0.0           0.0\n")
        elif iface.guest_atom_count > 0:
            # Fallback: unknown guest type, write CH4 atomtypes as default
            f.write("; CH4 atom types (GAFF2) - default for unknown guest\n")
            f.write("c3        c3        6             12.0107  0.0     A      3.39771e-1    4.51035e-1\n")
            f.write("hc        hc        1              1.0079  0.0     A      2.60018e-1    8.70272e-2\n")
        
        f.write("\n")
        
        # Include molecule definitions (after atomtypes, as GROMACS requires)
        f.write("; Molecule definitions\n")
        f.write('#include "tip4p-ice.itp"\n')
        
        if iface.guest_nmolecules > 0 and guest_type:
            # Include the correct .itp file based on detected guest type
            f.write(f'#include "{guest_type}.itp"\n')
        
        f.write("\n")
        
        # [ system ] - system-level section
        f.write("[ system ]\n")
        f.write("; Name\n")
        f.write(f"Ice/water interface ({iface.mode}) exported by QuickIce\n\n")
        
        # [ molecules ] - molecule counts
        # MUST match .gro file order: ice SOL -> water SOL -> guests
        # (all SOL molecules are contiguous after slab.py fix)
        f.write("[ molecules ]\n")
        f.write("; Compound    #mols\n")
        
        # All SOL molecules (ice + water combined)
        total_sol = iface.ice_nmolecules + iface.water_nmolecules
        if total_sol > 0:
            f.write(f"SOL          {total_sol}\n")
        
        # Guest molecules (after all SOL in .gro file)
        if iface.guest_nmolecules > 0:
            # Use already-detected guest_type from above
            if guest_type:
                guest_res_name = get_guest_residue_name(guest_type)
                f.write(f"{guest_res_name:<10s} {iface.guest_nmolecules}\n")


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

    Exports molecules in ORDER: SOL (ice+water), guest, NA, CL.
    This matches the expected topology order and GROMACS requirements.

    Args:
        ion_structure: IonStructure object with molecule_index
        filepath: Output file path for .gro file

    Note:
        GROMACS .gro format limits atom and residue numbers to 5 digits.
        For systems with >99999 atoms, atom numbers wrap at 100000 (standard GROMACS convention).
    """
    # Build an ordered list of molecules: SOL (ice+water) first, then guest, then NA, then CL
    ordered_mols = []
    # Pass 1: SOL molecules (ice + water)
    for mol in ion_structure.molecule_index:
        if mol.mol_type in ("ice", "water"):
            ordered_mols.append(("sol", mol))
    # Pass 2: guest molecules
    for mol in ion_structure.molecule_index:
        if mol.mol_type == "guest":
            ordered_mols.append(("guest", mol))
    # Pass 3: NA ions
    for mol in ion_structure.molecule_index:
        if mol.mol_type == "na":
            ordered_mols.append(("na", mol))
    # Pass 4: CL ions
    for mol in ion_structure.molecule_index:
        if mol.mol_type == "cl":
            ordered_mols.append(("cl", mol))

    # Count total atoms for header
    total_atoms = 0
    for mol_type, mol in ordered_mols:
        if mol_type == "sol":
            if mol.mol_type == "ice":
                # Ice: 3 input atoms -> 4 output atoms (OW, HW1, HW2, MW)
                total_atoms += 4
            else:
                # Water: 4 atoms
                total_atoms += mol.count
        elif mol_type == "guest":
            total_atoms += mol.count
        else:  # na or cl
            total_atoms += 1  # 1 atom per ion

    atom_num = 0
    res_num = 0

    with open(filepath, 'w') as f:
        # Title line
        na_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "na")
        cl_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "cl")
        f.write(f"Ice/water + ions ({na_count} Na+, {cl_count} Cl-) exported by QuickIce\n")

        # Number of atoms
        f.write(f"{total_atoms:5d}\n")

        # Build all atom lines in memory for better I/O performance
        lines = []

        for mol_type, mol in ordered_mols:
            if mol_type == "sol":
                # SOL molecule (ice or water)
                res_num += 1
                res_num_wrapped = res_num % 100000

                start = mol.start_idx

                if mol.mol_type == "ice":
                    # Ice: 3 input atoms (O, H, H) -> 4 output atoms (OW, HW1, HW2, MW)
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

                else:  # water
                    # Water: 4 atoms (OW, HW1, HW2, MW)
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

            elif mol_type == "guest":
                # Guest molecule (CH4, THF, etc.) - write all atoms
                res_num += 1
                res_num_wrapped = res_num % 100000

                start = mol.start_idx
                # Get atom names and positions for this molecule
                mol_atom_names = ion_structure.atom_names[start:start + mol.count]
                mol_positions = ion_structure.positions[start:start + mol.count]

                # Detect guest type from atom names
                guest_type = detect_guest_type_from_atoms(mol_atom_names)

                # Get residue name from itp file (not hardcoded)
                if guest_type:
                    guest_res_name = get_guest_residue_name(guest_type)
                else:
                    guest_res_name = "GUE"  # Fallback

                # Reorder guest atoms to match .itp canonical order
                # (e.g., CH4: C first instead of H first from GenIce2)
                reorder_mapping = None
                if guest_type in ["ch4", "thf"]:
                    mol_atom_names, reorder_mapping = reorder_guest_atoms(mol_atom_names, guest_type)
                    # Also reorder positions to match the reordered names
                    if reorder_mapping is not None:
                        mol_positions = [mol_positions[i] for i in reorder_mapping]

                for i in range(mol.count):
                    atom_num += 1
                    atom_num_wrapped = atom_num % 100000
                    atom_name = mol_atom_names[i]
                    pos = mol_positions[i]
                    lines.append(f"{res_num_wrapped:5d}{guest_res_name:<5s}"
                                f"{atom_name:>5s}{atom_num_wrapped:5d}"
                                f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")

            elif mol_type == "na":
                # NA ion
                res_num += 1
                res_num_wrapped = res_num % 100000
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                pos = ion_structure.positions[mol.start_idx]
                lines.append(f"{res_num_wrapped:5d}NA   "
                            f"   NA{atom_num_wrapped:5d}"
                            f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")

            elif mol_type == "cl":
                # CL ion
                res_num += 1
                res_num_wrapped = res_num % 100000
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                pos = ion_structure.positions[mol.start_idx]
                lines.append(f"{res_num_wrapped:5d}CL   "
                            f"   CL{atom_num_wrapped:5d}"
                            f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")

        f.writelines(lines)

        # Box vectors (triclinic format)
        cell = ion_structure.cell
        f.write(f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}"
                f"{cell[0,1]:10.5f}{cell[0,2]:10.5f}{cell[1,0]:10.5f}"
                f"{cell[1,2]:10.5f}{cell[2,0]:10.5f}{cell[2,1]:10.5f}\n")


def write_ion_top_file(ion_structure: IonStructure, filepath: str) -> None:
    """Write GROMACS topology file for ion structure.

    Uses SOL molecule type for water and ice, NA for sodium, CL for chloride.
    Includes guest molecules if present, with dynamic residue name from itp.
    Writes [molecules] section in order: SOL (ice+water), guest, NA, CL.

    Args:
        ion_structure: IonStructure object with molecule_index
        filepath: Output file path for .top file
    """
    # Count molecules by type across ENTIRE molecule_index
    # This ensures proper grouping (all SOL together, not stuttering)
    sol_count = sum(1 for m in ion_structure.molecule_index if m.mol_type in ("water", "ice"))
    guest_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "guest")
    na_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "na")
    cl_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "cl")

    # Detect guest type from atom names (for including correct .itp and residue name)
    guest_type = None
    guest_res_name = "GUE"  # Fallback
    if guest_count > 0 and ion_structure.guest_atom_count > 0:
        # Get atom names for the first guest molecule to detect type
        # Find the first guest molecule in molecule_index
        for mol in ion_structure.molecule_index:
            if mol.mol_type == "guest":
                start = mol.start_idx
                mol_atom_names = ion_structure.atom_names[start:start + mol.count]
                guest_type = detect_guest_type_from_atoms(mol_atom_names)
                if guest_type:
                    guest_res_name = get_guest_residue_name(guest_type)
                break

    with open(filepath, 'w') as f:
        # Header
        f.write("; Generated by QuickIce\n")
        f.write("; TIP4P-ICE water model with NaCl ions")
        if guest_count > 0:
            f.write(" and guest molecules")
        f.write("\n")
        f.write(f"; Structure: {sol_count} SOL (ice+water) + {guest_count} guests + {na_count} Na+ + {cl_count} Cl-\n\n")
        
        # [ defaults ] - force field defaults
        f.write("[ defaults ]\n")
        f.write("; nbfunc        comb-rule       gen-pairs       fudgeLJ fudgeQQ\n")
        f.write("1               2               yes             0.0     0.0\n\n")
        
        # [ atomtypes ] - MUST be before #include directives
        # TIP4P-ICE water atom types
        f.write("[ atomtypes ]\n")
        f.write("; name   bond_type  atomic_number  mass     charge  ptype  sigma (nm)    epsilon (kJ/mol)\n")
        f.write("OW_ice   OW_ice    8             15.9994  0.0     A      0.31668e-3    0.88216e-6\n")
        f.write("HW_ice   HW_ice    1              1.0080  0.0     A      0.0           0.0\n")
        f.write("MW       MW        0              0.0000  0.0     V      0.0           0.0\n")
        
        # Madrid2019 ion atom types (if ions present)
        if na_count > 0 or cl_count > 0:
            f.write("; Ion atom types (Madrid2019)\n")
            if na_count > 0:
                f.write("NA        NA        11            22.9898  0.0     A      2.21737e-1    1.47236e0\n")
            if cl_count > 0:
                f.write("CL        CL        17            35.453   0.0     A      4.69906e-1    7.69231e-2\n")
        
        # GAFF2 atom types for guests (if present)
        if guest_count > 0:
            if guest_type == "ch4":
                f.write("; CH4 atom types (GAFF2)\n")
                f.write("c3        c3        6             12.0107  0.0     A      3.39771e-1    4.51035e-1\n")
                f.write("hc        hc        1              1.0079  0.0     A      2.60018e-1    8.70272e-2\n")
            elif guest_type == "thf":
                f.write("; THF atom types (GAFF2)\n")
                f.write("os        os        8             15.9994  0.0     A      3.15610e-1    3.03758e-1\n")
                f.write("c5        c5        6             12.0107  0.0     A      3.39771e-1    4.51035e-1\n")
                f.write("hc        hc        1              1.0079  0.0     A      2.60018e-1    8.70272e-2\n")
                f.write("h1        h1        1              1.0079  0.0     A      2.42200e-1    8.70272e-2\n")
        
        f.write("\n")
        
        # Include molecule definitions (AFTER atomtypes)
        f.write("; Molecule definitions\n")
        # Include water itp
        f.write('#include "tip4p-ice.itp"\n')

        # Include guest itp if guests present
        if guest_count > 0:
            if guest_type:
                # Include the specific .itp file based on guest type
                f.write(f'#include "{guest_type}.itp"\n')
            else:
                # Fallback to generic guest.itp
                f.write('#include "guest.itp"\n')

        # Include ion itp (from ion export - combined NA+CL in single file)
        f.write('#include "ion.itp"\n\n')

        # [ system ] section
        f.write("[ system ]\n")
        system_name = f"Ice/water + {guest_count} guests + {na_count} Na+ + {cl_count} Cl- ions"
        f.write(f"{system_name}\n\n")

        # [ molecules ] section - written in ORDER: SOL, guest, NA, CL
        # This matches write_ion_gro_file() output order
        # GROMACS uses [molecules] to know how to group consecutive atoms into molecules
        f.write("[ molecules ]\n")
        f.write("; Compound        #mols\n")

        # Write grouped counts (not stuttering)
        # Order: SOL (ice+water combined), guest, NA, CL
        if sol_count > 0:
            f.write(f"SOL              {sol_count}\n")

        if guest_count > 0:
            f.write(f"{guest_res_name:<17s}{guest_count}\n")

        if na_count > 0:
            f.write(f"NA               {na_count}\n")

        if cl_count > 0:
            f.write(f"CL               {cl_count}\n")
