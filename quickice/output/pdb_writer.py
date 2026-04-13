"""PDB file writer with CRYST1 records for ice structures.

Converts Candidate structures to standard PDB format with proper crystal cell information.
"""

from pathlib import Path
from typing import List

import numpy as np

from quickice.structure_generation.types import Candidate, InterfaceStructure
from quickice.ranking.types import RankingResult


def _calculate_cell_parameters(cell: np.ndarray) -> tuple[float, float, float, float, float, float]:
    """Calculate cell parameters (a, b, c, alpha, beta, gamma) from cell vectors.
    
    Args:
        cell: (3, 3) array of cell vectors in Angstrom
        
    Returns:
        Tuple of (a, b, c, alpha, beta, gamma) where lengths are in Angstrom
        and angles are in degrees.
    """
    # Cell vector lengths
    a = np.linalg.norm(cell[0])
    b = np.linalg.norm(cell[1])
    c = np.linalg.norm(cell[2])
    
    # Angles between vectors (in degrees)
    # alpha = angle between b and c
    # beta = angle between a and c
    # gamma = angle between a and b
    cos_alpha = np.dot(cell[1], cell[2]) / (b * c) if b > 0 and c > 0 else 0.0
    cos_beta = np.dot(cell[0], cell[2]) / (a * c) if a > 0 and c > 0 else 0.0
    cos_gamma = np.dot(cell[0], cell[1]) / (a * b) if a > 0 and b > 0 else 0.0
    
    # Clamp to valid range for arccos
    cos_alpha = np.clip(cos_alpha, -1.0, 1.0)
    cos_beta = np.clip(cos_beta, -1.0, 1.0)
    cos_gamma = np.clip(cos_gamma, -1.0, 1.0)
    
    alpha = np.degrees(np.arccos(cos_alpha))
    beta = np.degrees(np.arccos(cos_beta))
    gamma = np.degrees(np.arccos(cos_gamma))
    
    return a, b, c, alpha, beta, gamma


def write_pdb_with_cryst1(candidate: Candidate, filepath: str) -> None:
    """Write a Candidate structure to PDB format with CRYST1 record.
    
    Converts coordinates and cell from nm to Angstrom (multiply by 10.0).
    
    Args:
        candidate: Candidate structure with positions and cell in nm
        filepath: Output PDB file path
    """
    # Convert cell from nm to Angstrom
    cell_angstrom = candidate.cell * 10.0
    
    # Calculate cell parameters
    a, b, c, alpha, beta, gamma = _calculate_cell_parameters(cell_angstrom)
    
    # Convert positions from nm to Angstrom
    positions_angstrom = candidate.positions * 10.0
    
    with open(filepath, 'w') as f:
        # Write CRYST1 record
        # Format: CRYST1 a(9.3) b(9.3) c(9.3) alpha(7.2) beta(7.2) gamma(7.2) spacegroup
        # Total width: 80 characters
        cryst1_line = f"CRYST1{a:9.3f}{b:9.3f}{c:9.3f}{alpha:7.2f}{beta:7.2f}{gamma:7.2f}  1\n"
        f.write(cryst1_line)
        
        # Detect atoms per water molecule from actual positions
        # TIP3P has 3 atoms (O, H, H), TIP4P has 4 atoms (O, H, H, MW)
        atoms_per_water = len(positions_angstrom) // candidate.nmolecules
        if len(positions_angstrom) % candidate.nmolecules != 0:
            raise ValueError(
                f"positions has {len(positions_angstrom)} atoms which is not divisible by "
                f"nmolecules={candidate.nmolecules}"
            )
        
        # Write ATOM records
        # Format: HETATM serial(5) atom_name(4) resName(3) chain(1) resSeq(4) x(8.3) y(8.3) z(8.3) occ(6.2) temp(6.2) element(2)
        # Each water molecule (O, H, H, [MW]) gets its own residue number
        for i, (pos, atom_name) in enumerate(zip(positions_angstrom, candidate.atom_names)):
            serial = i + 1
            residue_num = (i // atoms_per_water) + 1  # atoms_per_water atoms per water molecule
            x, y, z = pos
            
            # Atom name: left-aligned in columns 13-16 (4 chars total)
            # For single-letter elements, position in column 14
            if len(atom_name) == 1:
                formatted_name = f" {atom_name}  "
            else:
                formatted_name = f"{atom_name:<4s}"
            
            # Element symbol: right-justified in columns 77-78
            # Extract element from atom name (first letter for single-letter elements)
            element = atom_name[0] if atom_name else ""
            
            # Build ATOM line following PDB specification
            # Using HETATM for water molecules (non-standard residues)
            # Format: HETATM serial(5) space(1) atom_name(4) resName(3) chain(1) resSeq(4) ...
            line = f"HETATM{serial:5d} {formatted_name}HOH A{residue_num:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00          {element:>2s}\n"
            f.write(line)
        
        # Write END record
        f.write("END\n")


def write_interface_pdb_file(iface: InterfaceStructure, filepath: str) -> None:
    """Write interface structure to PDB format with CRYST1 record.
    
    Converts InterfaceStructure to PDB format with correct cell parameters
    for triclinic cells. Includes both ice and water atoms.
    
    Args:
        iface: InterfaceStructure with combined ice + water positions
        filepath: Output PDB file path
    """
    # Convert cell from nm to Angstrom
    cell_angstrom = iface.cell * 10.0
    
    # Calculate cell parameters
    a, b, c, alpha, beta, gamma = _calculate_cell_parameters(cell_angstrom)
    
    # Convert positions from nm to Angstrom
    positions_angstrom = iface.positions * 10.0
    
    with open(filepath, 'w') as f:
        # Write CRYST1 record
        cryst1_line = f"CRYST1{a:9.3f}{b:9.3f}{c:9.3f}{alpha:7.2f}{beta:7.2f}{gamma:7.2f}  1\n"
        f.write(cryst1_line)
        
        # Write ice atoms first (3 atoms per molecule: O, H, H)
        for i in range(iface.ice_atom_count):
            pos = positions_angstrom[i]
            atom_name = iface.atom_names[i]
            residue_num = (i // 3) + 1  # 3 atoms per ice molecule
            serial = i + 1
            
            # Format atom name (left-aligned in columns 13-16)
            if len(atom_name) == 1:
                formatted_name = f" {atom_name}  "
            else:
                formatted_name = f"{atom_name:<4s}"
            
            element = atom_name[0] if atom_name else ""
            
            line = f"HETATM{serial:5d} {formatted_name}HOH A{residue_num:4d}    {pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}  1.00  0.00          {element:>2s}\n"
            f.write(line)
        
        # Write water atoms (4 atoms per molecule: OW, HW1, HW2, MW)
        for i in range(iface.water_atom_count):
            idx = iface.ice_atom_count + i
            pos = positions_angstrom[idx]
            atom_name = iface.atom_names[idx]
            residue_num = iface.ice_nmolecules + (i // 4) + 1  # 4 atoms per water molecule
            serial = idx + 1
            
            if len(atom_name) == 1:
                formatted_name = f" {atom_name}  "
            else:
                formatted_name = f"{atom_name:<4s}"
            
            element = atom_name[0] if atom_name else ""
            
            line = f"HETATM{serial:5d} {formatted_name}HOH A{residue_num:4d}    {pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}  1.00  0.00          {element:>2s}\n"
            f.write(line)
        
        # Write END record
        f.write("END\n")


def write_ranked_candidates(
    ranking_result: RankingResult, 
    output_dir: str, 
    base_name: str
) -> List[str]:
    """Write top 10 ranked candidates to PDB files.
    
    Creates output directory if needed. Filenames follow pattern: {base_name}_{rank:02d}.pdb
    
    Args:
        ranking_result: RankingResult with ranked_candidates
        output_dir: Directory to write PDB files
        base_name: Base filename (e.g., "ice_candidate")
        
    Returns:
        List of output file paths
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    output_files = []
    
    # Write top 10 candidates (or fewer if less available)
    for ranked_candidate in ranking_result.ranked_candidates[:10]:
        rank = ranked_candidate.rank
        filename = f"{base_name}_{rank:02d}.pdb"
        filepath = output_path / filename
        
        write_pdb_with_cryst1(ranked_candidate.candidate, str(filepath))
        output_files.append(str(filepath))
    
    return output_files
