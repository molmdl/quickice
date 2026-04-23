"""GROMACS file writers for ice structure export.

Provides functions to write GROMACS coordinate (.gro) and topology (.top) files
from generated ice structure candidates using the TIP4P-ICE water model.
"""

from pathlib import Path

import numpy as np

from quickice.structure_generation.types import Candidate, InterfaceStructure, IonStructure, MoleculeIndex, MOLECULE_TYPE_INFO


# TIP4P-ICE virtual site parameter (from tip4p-ice.itp virtual_sites3 directive)
TIP4P_ICE_ALPHA = 0.13458335


# Mapping from internal molecule type to GROMACS names
MOLECULE_TO_GROMACS: dict[str, dict[str, str]] = {
    "ice":   {"res_name": "SOL", "itp_file": "water.itp", "mol_name": "SOL"},
    "water": {"res_name": "SOL", "itp_file": "water.itp", "mol_name": "SOL"},
    "na":    {"res_name": "NA",  "itp_file": "na.itp",     "mol_name": "NA"},
    "cl":    {"res_name": "CL",  "itp_file": "cl.itp",     "mol_name": "CL"},
    "ch4":   {"res_name": "CH4", "itp_file": "ch4.itp",    "mol_name": "CH4"},
    "thf":   {"res_name": "THF", "itp_file": "thf.itp",    "mol_name": "THF"},
    "co2":   {"res_name": "CO2", "itp_file": "co2.itp",    "mol_name": "CO2"},
    "h2":    {"res_name": "H2",  "itp_file": "h2.itp",     "mol_name": "H2"},
}

# Guest atom types that indicate non-water molecules in hydrate
GUEST_ATOM_TYPES = {"C", "Me", "CA", "CB", "CC", "CD", "CE", "OC", "C"}


def extract_guest_molecules(positions: np.ndarray, atom_names: list[str]) -> tuple[list, list, list]:
    """Extract guest molecule data from positions and atom_names.
    
    Identifies guest molecules (CH4, THF, etc.) from atom_names and returns
    their positions, atom names, and a list of (start_idx, count, atom_type).
    
    Args:
        positions: (N_atoms, 3) atom positions
        atom_names: List of atom names
    
    Returns:
        Tuple of (guest_positions, guest_atom_names, guest_indices)
        - guest_positions: List of position arrays for each guest molecule
        - guest_atom_names: Flat list of guest atom names
        - guest_indices: List of (start_idx, count, atom_type) for each guest
    """
    # Detect guest-like atoms based on atom names
    # CH4 (all-atom): starts with C followed by H atoms
    # CH4 (united-atom): single "Me" atom
    # THF: O, C, H atoms with residue name patterns
    
    guest_molecules = []
    i = 0
    while i < len(atom_names):
        atom = atom_names[i]
        
        # Check for united-atom methane (Me)
        if atom == "Me":
            guest_molecules.append((i, 1, "ch4"))
            i += 1
            continue
        
        # Check for all-atom methane (C followed by 4 H atoms)
        if atom == "C" and i + 4 < len(atom_names):
            next_atoms = atom_names[i+1:i+5]
            if all(a == "H" for a in next_atoms):
                guest_molecules.append((i, 5, "ch4"))
                i += 5
                continue
        
        # Check for THF (check oxygen first, then carbons)
        # THF ring: O, CA, CB, CC, CD (5 atoms)
        if atom == "O" and i + 4 < len(atom_names):
            next_atoms = atom_names[i+1:i+5]
            # THF has carbons CA, CB, CC, CD and may have hydrogens
            if next_atoms[0] == "CA" and next_atoms[1] in ["CB", "CA"]:
                # Count all non-hydrogen atoms for THF
                thf_count = 1  # Start with O
                for j in range(i+1, min(i+8, len(atom_names))):
                    if atom_names[j] in ["CA", "CB", "CC", "CD", "OC"]:
                        thf_count += 1
                    elif atom_names[j] == "H":
                        # Continue counting hydrogens but stop after carbons done
                        pass
                    else:
                        break
                guest_molecules.append((i, thf_count, "thf"))
                i += thf_count
                continue
        
        # Not a guest atom, move to next
        i += 1
    
    if not guest_molecules:
        return [], [], []
    
    # Extract positions and atom names for guests
    guest_positions = []
    guest_atom_names = []
    guest_indices = []
    
    for start_idx, count, mol_type in guest_molecules:
        guest_positions.append(positions[start_idx:start_idx + count])
        guest_atom_names.extend(atom_names[start_idx:start_idx + count])
        guest_indices.append((start_idx, count, mol_type))
    
    return guest_positions, guest_atom_names, guest_indices


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


def write_interface_gro_file(iface: InterfaceStructure, filepath: str) -> None:
    """Write interface structure to GROMACS .gro format.
    
    Ice molecules (3-atom: O, H, H) are normalized to 4-atom TIP4P-ICE format
    (OW, HW1, HW2, MW) at export time. Water molecules (4-atom: OW, HW1, HW2, MW)
    pass through unchanged.
    
    When guest molecules are present (detected from guest_type_counts), their .itp
    files are also needed. Guest atoms are written at the end of the file.
    
    Args:
        iface: InterfaceStructure object with combined ice + water + guest positions
        filepath: Output file path for .gro file
    
    Note:
        GROMACS .gro format limits atom and residue numbers to 5 digits.
        For systems with >99999 atoms, atom numbers wrap at 100000 (standard GROMACS convention).
        For systems with >99999 residues, residue numbers wrap at 100000.
    """
    # First, extract guest molecule data from interface if present
    # Guest molecules are at the END of the positions array
    # Total positions should include: ice_atoms + water_atoms + guest_atoms
    
    # Calculate guest atom count from positions - known counts
    # InterfaceStructure positions layout:
    # - First: ice_atoms = ice_nmolecules * 3 (for GenIce) or ice_nmolecules * 4 (for hydrate source)
    # - Next: water_atoms = water_nmolecules * 4
    # - Last: guest_atoms (if any)
    
    # Determine atom counts from interface
    ice_atoms_in_file = len(iface.positions) - iface.water_atom_count
    water_atoms_in_file = iface.water_atom_count
    
    # Check for guest atoms by comparing to expected ice + water
    # If there's extra content, those are guest atoms
    guest_atoms_in_file = 0
    
    # Calculate expected atoms if all ice (3-atom) + water (4-atom)
    expected_ice_water = (iface.ice_nmolecules * 3) + (iface.water_nmolecules * 4)
    
    # Check if this is hydrate-derived (4-atom ice framework)
    # If first atoms are OW (not O), it's likely hydrate source
    is_hydrate_source = len(iface.atom_names) > 0 and iface.atom_names[0] == "OW"
    
    if is_hydrate_source:
        # hydrate source: ice part is actually 4-atom water framework
        expected_ice_water = (iface.ice_nmolecules * 4) + (iface.water_nmolecules * 4)
    
    # Guest atoms = total positions - expected ice/water
    guest_atoms_in_file = max(0, len(iface.positions) - expected_ice_water)
    
    # If guest atoms exist, detect and write them
    guest_atoms_count = guest_atoms_in_file
    
    # Total output atoms: ice (normalized to 4) + water (4) + guests (as-is)
    n_atoms = (iface.ice_nmolecules + iface.water_nmolecules) * 4 + guest_atoms_count
    
    atom_num = 0

    with open(filepath, 'w') as f:
        # Title line - include guest info if present
        if guest_atoms_count > 0:
            f.write(f"Ice/water interface ({iface.mode}) + guests exported by QuickIce\n")
        else:
            f.write(f"Ice/water interface ({iface.mode}) exported by QuickIce\n")

        # Number of atoms
        f.write(f"{n_atoms:5d}\n")

        # Build all atom lines in memory for better I/O performance
        lines = []

        # ICE/WATER MOLECULES (first part of positions array)
        # Determine atoms per molecule from atom_names
        if is_hydrate_source:
            # Hydrate source: 4 atoms per molecule (TIP4P format)
            atoms_per_mol = 4
        else:
            # GenIce: 3 atoms per molecule
            atoms_per_mol = 3

        # Process ice part (which is either 3-atom or 4-atom water framework)
        ice_start = 0
        ice_end = ice_atoms_in_file  # This uses len(positions) - water_atom_count
        # FIX: For hydrate source (4-atom), recalculate correctly
        if is_hydrate_source:
            ice_end = iface.ice_nmolecules * 4  # Correct boundary
        
        for mol_idx in range(iface.ice_nmolecules):
            base_idx = mol_idx * atoms_per_mol
            
            if atoms_per_mol == 3:
                # GenIce 3-atom ice → normalize to 4-atom TIP4P-ICE
                o_pos = iface.positions[base_idx]
                h1_pos = iface.positions[base_idx + 1]
                h2_pos = iface.positions[base_idx + 2]
                mw_pos = compute_mw_position(o_pos, h1_pos, h2_pos)
                
                # Wrap residue number at 100000
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
            else:
                # Already TIP4P format (4 atoms: OW, HW1, HW2, MW)
                atom_names = ["OW", "HW1", "HW2", "MW"]
                res_num = (mol_idx + 1) % 100000
                
                for i, atom_name in enumerate(atom_names):
                    atom_num += 1
                    atom_num_wrapped = atom_num % 100000
                    pos = iface.positions[base_idx + i]
                    lines.append(f"{res_num:5d}SOL  "
                                f"{atom_name:>4s}{atom_num_wrapped:5d}"
                                f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")

        # WATER MOLECULES: 4 atoms per molecule (already TIP4P format)
        water_start = ice_end
        for mol_idx in range(iface.water_nmolecules):
            base_idx = water_start + mol_idx * 4
            res_num = (iface.ice_nmolecules + mol_idx + 1) % 100000

            atom_names = ["OW", "HW1", "HW2", "MW"]
            for i, atom_name in enumerate(atom_names):
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                pos = iface.positions[base_idx + i]
                lines.append(f"{res_num:5d}SOL  "
                            f"{atom_name:>4s}{atom_num_wrapped:5d}"
                            f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")

        # GUEST MOLECULES (at the end of positions array, if any)
        if guest_atoms_count > 0:
            # FIX: calculate guest_start correctly
            ice_atoms_num = (iface.ice_nmolecules * 4) if is_hydrate_source else (iface.ice_nmolecules * 3)
            guest_start = ice_atoms_num + (iface.water_nmolecules * 4)
            
            # Detect guest molecule type and count atoms per molecule
            # Try to determine molecule type from atom names
            mol_type = "CH4"  # Default
            atoms_per_guest = 5  # Default for CH4
            
            # Check atom names to determine type
            if guest_start < len(iface.atom_names):
                first_guest_atom = iface.atom_names[guest_start]
                if first_guest_atom == "Me":
                    mol_type = "CH4"
                    atoms_per_guest = 1
                else:
                    # Count atoms in first guest molecule by scanning
                    # Look for pattern: C + H*H*H*H = CH4 (5 atoms)
                    guest_atom_names = iface.atom_names[guest_start:]
                    if len(guest_atom_names) >= 5:
                        if guest_atom_names[0] == "C" and all(a == "H" for a in guest_atom_names[1:5]):
                            mol_type = "CH4"
                            atoms_per_guest = 5
                        elif "CA" in guest_atom_names or "CB" in guest_atom_names:
                            mol_type = "THF"
                            # Count atoms until we find next molecule or end
                            atoms_per_guest = len(guest_atom_names)
            
            # Write guest molecules
            gromacs_info = MOLECULE_TO_GROMACS.get(mol_type.lower(), {"res_name": "UNK"})
            res_name = gromacs_info["res_name"]
            
            guest_mol_idx = 0
            while guest_start + guest_mol_idx * atoms_per_guest < len(iface.positions):
                mol_start = guest_start + guest_mol_idx * atoms_per_guest
                res_num = (iface.ice_nmolecules + iface.water_nmolecules + guest_mol_idx + 1) % 100000
                
                for i in range(atoms_per_guest):
                    if mol_start + i >= len(iface.positions):
                        break
                    atom_num += 1
                    atom_num_wrapped = atom_num % 100000
                    pos = iface.positions[mol_start + i]
                    atom_name = iface.atom_names[mol_start + i]
                    lines.append(f"{res_num:5d}{res_name:<5s}"
                                f"{atom_name:>5s}{atom_num_wrapped:5d}"
                                f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")
                guest_mol_idx += 1

        f.writelines(lines)
        
        # Box vectors (triclinic format)
        cell = iface.cell
        f.write(f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}"
                f"{cell[0,1]:10.5f}{cell[0,2]:10.5f}{cell[1,0]:10.5f}"
                f"{cell[1,2]:10.5f}{cell[2,0]:10.5f}{cell[2,1]:10.5f}\n")


def write_interface_top_file(iface: InterfaceStructure, filepath: str) -> None:
    """Write GROMACS topology file for interface structure.
    
    Uses a single SOL molecule type with combined ice + water molecule count.
    
    Args:
        iface: InterfaceStructure object with ice_nmolecules and water_nmolecules
        filepath: Output file path for .top file
    """
    total_molecules = iface.ice_nmolecules + iface.water_nmolecules
    
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
        f.write(f"Ice/water interface ({iface.mode}) exported by QuickIce\n\n")
        
        # [ molecules ] - molecule counts (SINGLE combined count)
        f.write("[ molecules ]\n")
        f.write("; Compound    #mols\n")
        f.write(f"SOL          {total_molecules}\n")


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
            gromacs_info = MOLECULE_TO_GROMACS.get(mol.mol_type, {"res_name": "UNK"})
            res_name = gromacs_info["res_name"]
            
            # Residue number wraps at 100000
            res_num = (molecule_index.index(mol) + 1) % 100000
            
            # Write atoms for this molecule
            for i in range(mol.count):
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                pos = positions[mol.start_idx + i]
                
                # Use actual atom name if provided, otherwise use generic "XX"
                if atom_names is not None:
                    actual_name = atom_names[mol.start_idx + i]
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
        gromacs_info = MOLECULE_TO_GROMACS.get(mol_type, {"mol_name": "UNK"})
        mol_name = gromacs_info["mol_name"]
        count = counts[mol_type]
        molecules_lines.append(f"{mol_name:<15s} {count:10d}")
    
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
    
    Also exports guest molecules if present (from hydrate-derived interfaces).
    
    Args:
        ion_structure: IonStructure object with water + ion + guest positions
        filepath: Output file path for .gro file
    
    Note:
        GROMACS .gro format limits atom and residue numbers to 5 digits.
        For systems with >99999 atoms, atom numbers wrap at 100000 (standard GROMACS convention).
    """
    # Count total atoms: water (4 atoms/mol) + ions (1 atom/mol) + guests (if any)
    water_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "water")
    
    # Check for guest molecules
    guest_atoms = 0
    if hasattr(ion_structure, 'guest_type_counts') and ion_structure.guest_type_counts:
        # Detect guest atoms from remaining positions not in molecule_index
        # molecule_index covers water and ions only
        # Find positions after all known molecules
        known_atoms = sum(m.count for m in ion_structure.molecule_index)
        guest_atoms = max(0, len(ion_structure.positions) - known_atoms)
    
    total_atoms = water_count * 4 + ion_structure.na_count + ion_structure.cl_count + guest_atoms
    
    atom_num = 0
    res_num = 0
    
    with open(filepath, 'w') as f:
        # Title line
        guest_info = ""
        if guest_atoms > 0:
            guest_info = f" + {ion_structure.guest_type_counts}"
        f.write(f"Ice/water + ions ({ion_structure.na_count} Na+, {ion_structure.cl_count} Cl-){guest_info} exported by QuickIce\n")
        
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
        
        # Guest molecules (at the end of positions array)
        if guest_atoms > 0:
            known_atoms = sum(m.count for m in ion_structure.molecule_index)
            guest_start = known_atoms
            
            # Determine guest molecule type from atom names
            mol_type = "CH4"
            atoms_per_guest = 5
            if guest_start < len(ion_structure.atom_names):
                first_atom = ion_structure.atom_names[guest_start]
                if first_atom == "Me":
                    mol_type = "CH4"
                    atoms_per_guest = 1
            
            gromacs_info = MOLECULE_TO_GROMACS.get(mol_type.lower(), {"res_name": "UNK"})
            res_name = gromacs_info["res_name"]
            
            guest_mol_idx = 0
            while guest_start + guest_mol_idx * atoms_per_guest < len(ion_structure.positions):
                mol_start = guest_start + guest_mol_idx * atoms_per_guest
                res_num += 1
                res_num_wrapped = res_num % 100000
                
                for i in range(atoms_per_guest):
                    if mol_start + i >= len(ion_structure.positions):
                        break
                    atom_num += 1
                    atom_num_wrapped = atom_num % 100000
                    pos = ion_structure.positions[mol_start + i]
                    atom_name = ion_structure.atom_names[mol_start + i]
                    lines.append(f"{res_num_wrapped:5d}{res_name:<5s}"
                                f"{atom_name:>5s}{atom_num_wrapped:5d}"
                                f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")
                guest_mol_idx += 1
        
        f.writelines(lines)
        
        # Box vectors (triclinic format)
        cell = ion_structure.cell
        f.write(f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}"
                f"{cell[0,1]:10.5f}{cell[0,2]:10.5f}{cell[1,0]:10.5f}"
                f"{cell[1,2]:10.5f}{cell[2,0]:10.5f}{cell[2,1]:10.5f}\n")


def write_ion_top_file(ion_structure: IonStructure, filepath: str) -> None:
    """Write GROMACS topology file for ion structure.
    
    Uses SOL molecule type for water, NA for sodium, CL for chloride.
    
    Args:
        ion_structure: IonStructure object with water and ion counts
        filepath: Output file path for .top file
    """
    water_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "water")
    
    with open(filepath, 'w') as f:
        # Header
        f.write("; Generated by QuickIce\n")
        f.write("; TIP4P-ICE water model with NaCl ions\n")
        f.write(f"; Structure: {water_count} water + {ion_structure.na_count} Na+ + {ion_structure.cl_count} Cl-\n\n")
        
        # Default GROMACS directives
        f.write("[ defaults ]\n")
        f.write("; nbfunc        comb-rule       gen-pairs       fudgeLJ fudgeQQ\n")
        f.write("1               2               yes             0.0     0.0\n\n")
        
        # Include water itp
        f.write('#include "tip4p-ice.itp"\n')

        # Include ion itp (from ion export - combined NA+CL in single file)
        f.write('#include "ion.itp"\n\n')
        
        # [ system ] section
        f.write("[ system ]\n")
        f.write(f"Ice/water + {ion_structure.na_count} Na+ + {ion_structure.cl_count} Cl- ions\n\n")
        
        # [ molecules ] section
        f.write("[ molecules ]\n")
        f.write("; Compound        #mols\n")
        f.write(f"SOL              {water_count}\n")
        f.write(f"NA               {ion_structure.na_count}\n")
        f.write(f"CL               {ion_structure.cl_count}\n")
