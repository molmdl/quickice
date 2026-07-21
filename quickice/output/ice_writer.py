"""GROMACS writers for ice-only Candidate export.

Split from quickice/output/gromacs_writer.py in Phase 48.1 (FRAG-03).
These writers handle the simplest export path: a Candidate containing
only ice molecules (3-atom OHH → 4-atom TIP4P-ICE OW/HW1/HW2/MW).
"""

import logging
from pathlib import Path

import numpy as np

from quickice.structure_generation.types import Candidate, MoleculeIndex

from quickice.output._shared import (
    compute_mw_position,
    wrap_molecules_into_box,
    _write_top_defaults,
    TIP4P_ICE_OW_SIGMA, TIP4P_ICE_OW_EPSILON,
    TIP4P_ICE_HW_CHARGE, TIP4P_ICE_MW_CHARGE,
    TIP4P_ICE_SETTLE_DOH, TIP4P_ICE_SETTLE_DHH,
    TIP4P_ICE_ALPHA,
    validate_gro_residue_name,
)
from quickice.output._gro_format import (
    _write_gro_header,
    _format_sol_ice_molecule,
    _write_gro_box_vectors,
)

logger = logging.getLogger(__name__)


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
    n_atoms = nmol * 4
    
    if n_atoms > 99999:
        logger.warning(f"GRO format wraps atom numbers at 100,000 (have {n_atoms} atoms)")
    
    # Build molecule_index for molecule-aware wrapping
    # NOTE: count=3 here (OW, HW1, HW2) is the WRAPPING set — MW is computed AFTER
    # wrapping from these 3 atoms, so MW is not included in the molecule_index for wrapping.
    # This is distinct from WATER_ATOMS_PER_MOLECULE=4 (total including MW) used elsewhere.
    ice_molecule_index = [
        MoleculeIndex(start_idx=i * 3, count=3, mol_type="ice")
        for i in range(nmol)
    ]
    wrapped_positions = wrap_molecules_into_box(candidate.positions, ice_molecule_index, candidate.cell)
    
    expected_atoms = nmol * 3
    if len(wrapped_positions) < expected_atoms:
        raise ValueError(
            f"positions has {len(wrapped_positions)} atoms but "
            f"nmolecules={nmol} needs {expected_atoms} (3 atoms per ice molecule)"
        )
    
    try:
        with open(filepath, 'w') as f:
            # Build all GRO lines (header + per-atom) into a single list and
            # flush with one f.writelines() call (I/O-bound; the writelines
            # call dominates execution time vs the O(N) Python formatting).
            lines = []
            _write_gro_header(
                lines,
                f"Ice structure {candidate.phase_id} exported by QuickIce",
                n_atoms,
            )

            # Note: The lines.append() calls below (inside the helper) are NOT
            # wrapped in try/except because:
            # 1. String formatting of float values cannot fail unless the input array is malformed
            #    (which would be a programming bug, not a runtime error)
            # 2. numpy array indexing (positions[i]) would raise IndexError on malformed data,
            #    which is a programming error that should propagate rather than be silently caught
            # 3. Any actual I/O error occurs during f.writelines() inside the with-open block,
            #    which IS protected by try/except

            # PERF-06 NOTE: This per-atom loop formats and appends GRO coordinate strings.
            # While this is O(N) in Python, the loop is I/O-bound (the writelines() call
            # that follows dominates execution time). The heterogeneous formatting
            # (different residue types, atom name column widths, and position formatting)
            # makes vectorization complex with minimal performance gain since the actual
            # bottleneck is disk I/O, not string formatting. Kept as explicit loop for
            # clarity and maintainability.
            atom_num_counter = [0]  # 1-element mutable box threaded across molecule boundaries
            for mol_idx in range(nmol):
                base_idx = mol_idx * 3

                o_pos = wrapped_positions[base_idx]
                h1_pos = wrapped_positions[base_idx + 1]
                h2_pos = wrapped_positions[base_idx + 2]

                mw_pos = compute_mw_position(o_pos, h1_pos, h2_pos)

                res_num = (mol_idx + 1) % 100000

                _format_sol_ice_molecule(
                    lines, o_pos, h1_pos, h2_pos, mw_pos,
                    res_num, atom_num_counter,
                )

            f.writelines(lines)

            # 9-value triclinic box vector line (matches the other 5 GRO writers
            # that use the triclinic format; write_custom_molecule_gro_file is the
            # sole divergent writer using a 3-value diagonal box line — see
            # _gro_format._write_gro_box_vectors docstring).
            _write_gro_box_vectors(f, candidate.cell)
    except (OSError, ValueError) as e:
        logger.error(f"Failed to write GRO file '{filepath}': {e}")
        if Path(filepath).exists():
            Path(filepath).unlink()
        raise


def write_top_file(candidate: Candidate, filepath: str) -> None:
    """Write GROMACS topology file.
    
    Args:
        candidate: Candidate object with nmolecules and phase_id
        filepath: Output file path for .top file
    """
    nmol = candidate.nmolecules
    
    with open(filepath, 'w') as f:
        f.write("; Generated by QuickIce\n")
        f.write("; TIP4P-ICE water model\n\n")
        
        # [ defaults ] - force field defaults (Format A — write_top_file +
        # write_interface_top_file use the default helper invocation which
        # emits '; Defaults compatible with the Amber forcefield' + the
        # compact '; nbfunc' comment. See _shared._write_top_defaults docstring
        # for the 3-variant parameterization rationale.)
        _write_top_defaults(f)
        
        f.write("[ atomtypes ]\n")
        f.write("; name  bond_type  atomic_number  mass  charge  ptype  sigma (nm)     epsilon (kJ/mol)\n")
        f.write(f"OW_ice      OW_ice     8           15.9994  0.0     A      {TIP4P_ICE_OW_SIGMA:.5e}    {TIP4P_ICE_OW_EPSILON:.5e}\n")
        f.write("HW_ice      HW_ice     1            1.0080  0.0     A      0.0          0.0\n")
        f.write("MW          MW          0            0.0000  0.0     V      0.0          0.0\n\n")
        
        f.write("[ moleculetype ]\n")
        f.write("; Name        nrexcl\n")
        f.write("SOL          2\n\n")
        
        f.write("[ atoms ]\n")
        f.write(";   nr  type  resi  res  atom  cgnr     charge    mass\n")
        f.write("   1   OW_ice    1  SOL    OW     1       0.0  16.00000\n")
        f.write(f"   2   HW_ice    1  SOL   HW1     1     {TIP4P_ICE_HW_CHARGE}   1.00800\n")
        f.write(f"   3   HW_ice    1  SOL   HW2     1     {TIP4P_ICE_HW_CHARGE}   1.00800\n")
        f.write(f"   4   MW        1  SOL    MW     1    {TIP4P_ICE_MW_CHARGE}   0.00000\n\n")
        
        f.write("[ settles ]\n")
        f.write("; i  funct  doh     dhh\n")
        f.write(f"  1    1    {TIP4P_ICE_SETTLE_DOH}  {TIP4P_ICE_SETTLE_DHH}\n\n")
        
        f.write("[ virtual_sites3 ]\n")
        f.write("; Vsite from                    funct  a          b\n")
        f.write(f"   4     1       2       3       1      {TIP4P_ICE_ALPHA} {TIP4P_ICE_ALPHA}\n\n")
        
        f.write("[ exclusions ]\n")
        f.write("  1  2  3  4\n")
        f.write("  2  1  3  4\n")
        f.write("  3  1  2  4\n")
        f.write("  4  1  2  3\n\n")
        
        f.write("[ system ]\n")
        f.write("; Name\n")
        f.write(f"{candidate.phase_id} exported by QuickIce\n\n")
        
        f.write("[ molecules ]\n")
        f.write("; Compound    #mols\n")
        f.write(f"SOL          {nmol}\n")
