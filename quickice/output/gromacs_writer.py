"""GROMACS file writers for ice structure export.

Provides functions to write GROMACS coordinate (.gro) and topology (.top) files
from generated ice structure candidates using the TIP4P-ICE water model.
"""

import logging
import re
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import numpy as np

from quickice.utils.molecule_utils import count_guest_atoms
from quickice.structure_generation.types import Candidate, InterfaceStructure, IonStructure, MoleculeIndex
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
from quickice.structure_generation.itp_parser import parse_itp_file
from quickice.structure_generation.cell_utils import is_cell_orthogonal

if TYPE_CHECKING:
    from quickice.structure_generation.types import CustomMoleculeStructure, SoluteStructure

logger = logging.getLogger(__name__)


def validate_gro_residue_name(res_name: str, context: str = "") -> None:
    """Validate that a GRO residue name fits in the 5-char fixed-width format.
    
    GRO format uses `%<5s` for residue names, which silently overflows if the
    name exceeds 5 characters, corrupting the fixed-width column alignment.
    This validation catches the problem at write time with a clear error.
    
    Args:
        res_name: Residue name to validate
        context: Optional context string for error message (e.g., "custom molecule 'ETHanol'")
        
    Raises:
        ValueError: If res_name exceeds 5 characters
    """
    if len(res_name) > 5:
        msg = (
            f"GRO residue name '{res_name}' ({len(res_name)} chars) exceeds "
            f"the 5-character GRO format limit. "
            f"Use a shorter residue name (≤3 chars recommended for hydrate guests "
            f"to allow for _H suffix: e.g., 'CH4' → 'CH4_H')."
        )
        if context:
            msg = f"{context}: {msg}"
        raise ValueError(msg)


TIP4P_ICE_ALPHA = 0.13458335

# TIP4P-ICE LJ parameters (Abascal et al. 2005, DOI: 10.1063/1.1931662)
# sigma_O = 3.1668 Å = 0.31668 nm; epsilon_O/k_B = 106.1 K → 106.1 × 0.00831446 = 0.88211 kJ/mol
TIP4P_ICE_OW_SIGMA = 3.16680e-1    # nm
TIP4P_ICE_OW_EPSILON = 8.82110e-1   # kJ/mol


# ---------------------------------------------------------------------------
# GAFF2 atomtype definitions for standard guest/solute molecules
# ---------------------------------------------------------------------------
# Each entry: (bond_type, atomic_number, mass, charge, ptype, sigma_nm, epsilon_kjmol)
# Format matches the 8-column GROMACS [ atomtypes ] section.
# Centralizing these eliminates scattered hardcoded atomtype lines and makes
# deduplication between molecule types (e.g., CH4 and THF sharing "hc") trivial.
# ---------------------------------------------------------------------------
GAFF2_ATOMTYPES: dict[str, tuple[str, int, float, float, str, float, float]] = {
    # CH4 atom types
    "c3":  ("c3",  6, 12.0107, 0.0, "A", 3.39771e-1, 4.51035e-1),
    "hc":  ("hc",  1,  1.0079, 0.0, "A", 2.60018e-1, 8.70272e-2),
    # THF atom types
    "os":  ("os",  8, 15.9994, 0.0, "A", 3.15610e-1, 3.03758e-1),
    "c5":  ("c5",  6, 12.0107, 0.0, "A", 3.39771e-1, 4.51035e-1),
    "h1":  ("h1",  1,  1.0079, 0.0, "A", 2.42200e-1, 8.70272e-2),
    # CO2 atom types
    "c_2": ("c_2", 6, 12.0107, 0.0, "A", 3.39955e-1, 4.39089e-1),
    "o_2": ("o_2", 8, 15.9994, 0.0, "A", 3.02714e-1, 8.80314e-1),
    # H2 atom types
    "hn":  ("hn",  1,  1.0080, 0.0, "A", 0.0,         0.0),
}

# Atomtype names required per molecule type (order matches ITP file convention)
CH4_ATOMTYPE_NAMES  = ["c3", "hc"]
THF_ATOMTYPE_NAMES  = ["os", "c5", "hc", "h1"]
CO2_ATOMTYPE_NAMES  = ["c_2", "o_2"]
H2_ATOMTYPE_NAMES   = ["hn"]

# Madrid2019 ion atomtype parameters (name → tuple)
ION_ATOMTYPES: dict[str, tuple[str, int, float, float, str, float, float]] = {
    "NA": ("NA", 11, 22.9898, 0.0, "A", 2.21737e-1, 1.47236e0),
    "CL": ("CL", 17, 35.453,  0.0, "A", 4.69906e-1, 7.69231e-2),
}

# TIP4P-ICE water atomtype parameters (name → tuple)
WATER_ATOMTYPES: dict[str, tuple[str, int, float, float, str, float, float]] = {
    "OW_ice": ("OW_ice", 8, 15.9994, 0.0, "A", TIP4P_ICE_OW_SIGMA, TIP4P_ICE_OW_EPSILON),
    "HW_ice": ("HW_ice", 1,  1.0080, 0.0, "A", 0.0, 0.0),
    "MW":     ("MW",     0,  0.0000, 0.0, "V", 0.0, 0.0),
}


def _format_atomtype_line(name: str, params: tuple[str, ...]) -> str:
    """Format a GAFF2/ion atomtype tuple as a GROMACS [ atomtypes ] line.

    Args:
        name: Atomtype name (also used as bond_type for GAFF2 convention)
        params: (bond_type, atomic_number, mass, charge, ptype, sigma, epsilon)

    Returns:
        Formatted line string with newline.
    """
    bond_type, anum, mass, charge, ptype, sigma, epsilon = params
    return (f"{name:<8s} {bond_type:<8s} {anum:>6d} "
            f"{mass:>12.4f} {charge:>6.1f} {ptype:<4s} "
            f"{sigma:>12.5e} {epsilon:>12.5e}\n")


def _format_custom_atomtype_line(fields: tuple[str, ...]) -> str:
    """Format a custom-molecule atomtype tuple as a GROMACS [ atomtypes ] line.

    Custom atomtypes come from parse_itp_atomtypes() as string tuples.
    Uses string formatting to preserve the original ITP file's numeric format.

    Args:
        fields: 8-element string tuple (name, bond_type, at.num, mass, charge,
                ptype, sigma, epsilon)

    Returns:
        Formatted line string with newline.
    """
    return (f"{fields[0]:<8s} {fields[1]:<8s} {fields[2]:>6s} "
            f"{fields[3]:>12s} {fields[4]:>6s} {fields[5]:<4s} "
            f"{fields[6]:>12s} {fields[7]:>12s}\n")


def _write_atomtypes_block(
    f, names: list[str], source_label: str,
    written: dict[str, tuple[str, int, float, float, str, float, float]],
) -> None:
    """Write a GAFF2 atomtypes block with deduplication.

    For each atomtype name in *names*, checks if it has already been written
    (present in *written*).  If not, writes the atomtype line and records it.
    If the name was already written, skips it silently (built-in GAFF2 types
    from the same GAFF2_ATOMTYPES dict are guaranteed to have identical
    parameters).

    Args:
        f: Open file handle for the .top file.
        names: Atomtype names to write (e.g., CH4_ATOMTYPE_NAMES).
        source_label: Comment label for the block (e.g., "CH4 atom types (GAFF2)").
        written: Mutable dict of already-written atomtypes
                 (name → params tuple).  Updated in place.
    """
    f.write(f"; {source_label}\n")
    for name in names:
        if name in written:
            continue  # Already written — identical params guaranteed for GAFF2
        params = GAFF2_ATOMTYPES[name]
        f.write(_format_atomtype_line(name, params))
        written[name] = params


def _check_custom_atomtype_conflict(
    name: str,
    custom_fields: tuple[str, ...],
    written: dict[str, tuple[str, int, float, float, str, float, float]],
) -> None:
    """Check whether a custom-molecule atomtype conflicts with an existing one.

    If *name* is already in *written*, compares the key LJ parameters
    (sigma, epsilon).  If they differ, raises ValueError — the user must
    rename the atomtype in their custom molecule to avoid the clash.
    If they match, the duplicate is silently skipped (already defined above).

    Args:
        name: Atomtype name from the custom ITP file.
        custom_fields: 8-element string tuple from parse_itp_atomtypes().
        written: Dict of already-written atomtypes (name → params tuple).

    Raises:
        ValueError: If atomtype name already exists with different parameters.
    """
    if name not in written:
        return  # No conflict — name is new

    # Compare LJ parameters numerically (strings may use different formatting)
    try:
        custom_sigma = float(custom_fields[6])
        custom_epsilon = float(custom_fields[7])
    except (ValueError, IndexError):
        # If we can't parse, be conservative and raise
        raise ValueError(
            f"Custom molecule atomtype '{name}' could not be parsed for "
            f"parameter comparison.  Existing atomtypes with this name have "
            f"already been written.  Please rename the atomtype in your "
            f"custom molecule ITP file to avoid the collision."
        )

    existing_params = written[name]
    existing_sigma = existing_params[5]  # index 5 in (bond_type, anum, mass, charge, ptype, sigma, epsilon)
    existing_epsilon = existing_params[6]

    # Use relative tolerance for floating-point comparison
    if not _lj_params_match(existing_sigma, existing_epsilon,
                            custom_sigma, custom_epsilon):
        raise ValueError(
            f"Atomtype '{name}' is already defined with different LJ "
            f"parameters.  Existing: sigma={existing_sigma:.5e} nm, "
            f"epsilon={existing_epsilon:.5e} kJ/mol.  Custom molecule "
            f"defines: sigma={custom_sigma:.5e} nm, "
            f"epsilon={custom_epsilon:.5e} kJ/mol.  "
            f"Please rename the atomtype in your custom molecule ITP file "
            f"to avoid the conflict."
        )
    # Parameters match — duplicate is harmless, already written above


def _lj_params_match(
    sigma1: float, eps1: float, sigma2: float, eps2: float,
    rtol: float = 1e-4,
) -> bool:
    """Compare two LJ parameter sets with relative tolerance.

    Returns True if both sigma and epsilon values are close enough to be
    considered identical (accounting for rounding in different formats).
    """
    import math
    if sigma1 == 0.0 and sigma2 == 0.0 and eps1 == 0.0 and eps2 == 0.0:
        return True
    if sigma1 == 0.0 or sigma2 == 0.0:
        return sigma1 == sigma2  # Both should be zero
    if eps1 == 0.0 or eps2 == 0.0:
        return eps1 == eps2
    return (math.isclose(sigma1, sigma2, rel_tol=rtol) and
            math.isclose(eps1, eps2, rel_tol=rtol))


def _merge_custom_atomtypes(f, itp_path, written, label):
    """Parse [ atomtypes ] from a custom molecule ITP and merge into the main .top.

    For each parsed atomtype: conflict-check against *written* (raises ValueError
    on LJ-param mismatch), then write the line only if the name is new (dedup) and
    record its params in *written* for future conflict checks. No-op when the ITP
    has no [ atomtypes ] section.

    Args:
        f: Open file handle for the .top [ atomtypes ] block.
        itp_path: Path to the custom molecule .itp file.
        written: Mutable dict name -> params tuple, pre-seeded with water/ion/GAFF2
                 atomtypes. Updated in place.
        label: Comment label for the block (e.g. "custom guest etoh_e2e atom types").
    """
    custom_atomtypes = parse_itp_atomtypes(itp_path)
    if not custom_atomtypes:
        return
    f.write(f"; {label}\n")
    for atomtype in custom_atomtypes:
        if len(atomtype) >= 8:
            at_name = atomtype[0]
            _check_custom_atomtype_conflict(at_name, atomtype, written)
            if at_name not in written:
                f.write(_format_custom_atomtype_line(atomtype))
                try:
                    written[at_name] = (
                        atomtype[1], int(atomtype[2]),
                        float(atomtype[3]), float(atomtype[4]),
                        atomtype[5], float(atomtype[6]),
                        float(atomtype[7]),
                    )
                except (ValueError, IndexError):
                    pass  # Best-effort recording


MOLECULE_TO_GROMACS: dict[str, dict[str, str]] = {
    "ice":   {"res_name": "SOL", "itp_file": "tip4p-ice.itp", "mol_name": "SOL"},
    "water": {"res_name": "SOL", "itp_file": "tip4p-ice.itp", "mol_name": "SOL"},
    "na":    {"res_name": "NA",  "itp_file": "na.itp",     "mol_name": "NA"},
    "cl":    {"res_name": "CL",  "itp_file": "cl.itp",     "mol_name": "CL"},
    "ch4":   {"res_name": "CH4", "itp_file": "ch4_hydrate.itp", "mol_name": "CH4"},
    "thf":   {"res_name": "THF", "itp_file": "thf_hydrate.itp", "mol_name": "THF"},
    "co2":   {"res_name": "CO2", "itp_file": "co2.itp",    "mol_name": "CO2"},
    "h2":    {"res_name": "H2",  "itp_file": "h2.itp",     "mol_name": "H2"},
}

# Module-level registry for unique moleculetype naming
_registry = MoleculetypeRegistry()


def wrap_positions_into_box(positions: np.ndarray, cell: np.ndarray) -> np.ndarray:
    """Wrap positions into the simulation box [0, cell[i,i]).
    
    For molecules spanning PBC boundaries, some atoms may be outside [0, boxsize).
    This function wraps each coordinate individually into the box for GRO file output.
    
    For orthogonal (diagonal) cells, each axis is wrapped independently via
    ``np.mod(pos[:, dim], cell[dim, dim])`` — this is the fast path used by slab
    interface exports (slab.py forces orthogonal cells).
    
    For triclinic cells (non-zero off-diagonal elements, e.g. sH/c0te/c1te hydrate
    cells parsed at hydrate_generator.py:414-430), the diagonal-only modulo would
    ignore the off-diagonal shear and leave atoms outside the parallelepiped. The
    triclinic branch wraps via fractional coordinates (``frac = pos @ inv(cell.T)``,
    ``frac = np.mod(frac, 1.0)``, ``wrapped = frac @ cell.T``), reusing the proven
    pattern from ``water_filler.wrap_positions_triclinic`` (CRIT-01 fix).
    
    Args:
        positions: (N, 3) atom positions in nm
        cell: (3, 3) cell vectors as ROW vectors
    
    Returns:
        (N, 3) positions wrapped into the cell (orthogonal: [0, cell[i,i));
        triclinic: fractional coords in [0, 1))
    """
    wrapped = positions.copy()
    if len(wrapped) == 0:
        return wrapped
    # Triclinic cells: wrap via fractional coordinates (handles off-diagonal shear).
    if not is_cell_orthogonal(cell):
        inv_cell_T = np.linalg.inv(cell.T)
        frac = wrapped @ inv_cell_T
        frac = np.mod(frac, 1.0)
        return frac @ cell.T
    # Orthogonal cells: per-axis diagonal modulo (fast path — correct for slabs).
    for dim in range(3):
        # Wrap using modulo: coord % box_size
        # np.mod handles negative numbers correctly
        wrapped[:, dim] = np.mod(wrapped[:, dim], cell[dim, dim])
    return wrapped


def wrap_molecules_into_box(
    positions: np.ndarray,
    molecule_index: list,
    cell: np.ndarray
) -> np.ndarray:
    """Wrap positions into simulation box keeping molecules intact.
    
    Unlike wrap_positions_into_box which wraps each atom independently,
    this function wraps molecules as whole units to prevent splitting
    molecules across periodic boundary conditions.
    
    For each molecule:
    1. Detect if atoms are split across PBC (distance > box_size/2)
    2. Unwrap atoms to be together in same periodic image
    3. Wrap the whole molecule into [0, box_size)
    
    For orthogonal (diagonal) cells, the unwrap + center-wrap use the diagonal
    box sizes ``cell[d, d]`` (fast path used by slab interface exports, which
    force orthogonal cells at slab.py:619).
    
    For triclinic cells (non-zero off-diagonal elements, e.g. sH/c0te/c1te
    hydrate cells parsed at hydrate_generator.py:414-430), the diagonal-only
    unwrap/center-wrap would ignore the off-diagonal shear and leave atoms
    outside the parallelepiped. The triclinic branch wraps each molecule by its
    fractional center-of-mass: ``frac = mol @ inv(cell.T)``; shift all atoms by
    ``-floor(com_frac)``; ``wrapped = frac @ cell.T``. This handles unwrap AND
    wrap in one step and naturally accounts for the triclinic shear, reusing the
    proven pattern from ``water_filler.wrap_positions_triclinic`` (CRIT-01 fix).
    
    Args:
        positions: (N, 3) atom positions in nm
        molecule_index: List of MoleculeIndex objects defining molecule boundaries
        cell: (3, 3) cell vectors as ROW vectors
    
    Returns:
        (N, 3) positions with molecules wrapped as whole units
    """
    wrapped = positions.copy()
    if len(wrapped) == 0 or not molecule_index:
        return wrapped

    # Triclinic cells: wrap each molecule by fractional center-of-mass, reusing
    # the proven water_filler.wrap_positions_triclinic pattern (adapted for
    # variable-size molecule_index: ice/water=4, ch4=5, thf=13, na/cl=1).
    # Handles unwrap + wrap in one step; accounts for off-diagonal shear.
    if not is_cell_orthogonal(cell):
        inv_cell_T = np.linalg.inv(cell.T)
        for mol in molecule_index:
            start = mol.start_idx
            count = mol.count
            mol_frac = wrapped[start:start + count] @ inv_cell_T
            # Shift the whole molecule by the integer fractional offset that
            # brings its center of mass into [0, 1). -np.floor(com) is the
            # standard PBC image selector (identical to water_filler.py:121).
            com_frac = mol_frac.mean(axis=0)
            shift_frac = -np.floor(com_frac)
            mol_frac = mol_frac + shift_frac
            wrapped[start:start + count] = mol_frac @ cell.T
        return wrapped

    # Orthogonal cells: diagonal-only unwrap + center-wrap (fast path — correct
    # for slab interfaces forced orthogonal at slab.py:619).
    for mol in molecule_index:
        start = mol.start_idx
        count = mol.count
        
        # Get positions for this molecule
        mol_positions = wrapped[start:start + count].copy()
        
        # Step 1: Unwrap atoms that are split across PBC (vectorized)
        ref_pos = mol_positions[0]
        
        # Compute delta from reference for all atoms at once
        delta = mol_positions[1:] - ref_pos
        
        # Get box sizes for all 3 dimensions
        box_sizes = np.array([cell[d, d] for d in range(3)])
        
        # Compute unwrapping shifts: vectorized across all atoms and dimensions
        shifts = np.zeros_like(delta)
        half_box = box_sizes / 2
        
        # Atoms "ahead" (delta > box/2) → shift back
        mask_ahead = delta > half_box
        shifts[mask_ahead] -= box_sizes[np.where(mask_ahead)[1] % 3]
        
        # Atoms "behind" (delta < -box/2) → shift forward
        mask_behind = delta < -half_box
        shifts[mask_behind] += box_sizes[np.where(mask_behind)[1] % 3]
        
        # Apply shifts to unwrap all atoms at once
        mol_positions[1:] += shifts
        
        # Step 2: Wrap the whole molecule into [0, box_size) using center
        center = np.mean(mol_positions, axis=0)
        
        # Vectorized center wrapping
        center_wrapped = np.mod(center, box_sizes)
        shift = center_wrapped - center
        
        # Apply shift to all atoms in molecule
        mol_positions += shift
        
        # Store wrapped positions
        wrapped[start:start + count] = mol_positions
    
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
    if (reorder 
        and len(reorder) == len(atom_names) 
        and all(i < len(atom_names) for i in reorder)
        and len(set(reorder)) == len(reorder)):
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
    except (IOError, OSError) as e:
        logger.warning(f"Could not read ITP file: {e}")
    
    return None


def parse_itp_atomtypes(itp_path: str | Path) -> list[tuple[str, ...]]:
    """Parse atomtypes from a GROMACS .itp file.
    
    Extracts all atomtype definitions from [ atomtypes ] section.
    Each atomtype is returned as a tuple of the line parts.
    
    Supports two common formats:
    - Format 1 (7 cols): name, at.num, mass, charge, ptype, sigma, epsilon
    - Format 2 (8 cols): name, bond_type, at.num, mass, charge, ptype, sigma, epsilon
    
    Args:
        itp_path: Path to the .itp file
        
    Returns:
        List of atomtype tuples, each containing the parsed fields.
        For 7-col format, adds empty bond_type as second element.
    """
    atomtypes = []
    try:
        with open(itp_path, 'r') as f:
            in_atomtypes_section = False
            for line in f:
                stripped = line.strip()
                
                # Check for section headers
                if stripped.startswith('['):
                    if 'atomtypes' in stripped.lower():
                        in_atomtypes_section = True
                    else:
                        in_atomtypes_section = False
                    continue
                
                # Skip comments and empty lines
                if not stripped or stripped.startswith(';') or stripped.startswith('#'):
                    continue
                
                # Parse atomtype line
                if in_atomtypes_section:
                    parts = stripped.split()
                    if len(parts) >= 7:  # Minimum 7 columns for atomtype
                        # Normalize to 8-column format
                        if len(parts) == 7:
                            # Insert empty bond_type after name
                            parts.insert(1, parts[0])  # Use name as bond_type
                        atomtypes.append(tuple(parts))
    except (IOError, OSError) as e:
        logger.warning(f"Could not read ITP file for atomtypes: {e}")
    
    return atomtypes


def comment_out_atomtypes_in_itp(itp_content: str) -> str:
    """Comment out [ atomtypes ] section in ITP file content.
    
    Adds comment header and semicolons to all lines in atomtypes section.
    This is needed because atomtypes should be defined in the main .top file,
    not in individual molecule .itp files (to avoid duplication errors).
    
    Args:
        itp_content: Original ITP file content as string
        
    Returns:
        Modified ITP content with atomtypes section commented out
    """
    lines = itp_content.split('\n')
    result_lines = []
    in_atomtypes_section = False
    atomtypes_found = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Check for section headers
        if stripped.startswith('['):
            if 'atomtypes' in stripped.lower():
                in_atomtypes_section = True
                atomtypes_found = True
                # Add comment header before the section
                result_lines.append("; Modified for QuickIce: [atomtypes] commented - types defined in main .top file")
                result_lines.append("; " + line)  # Comment out the [ atomtypes ] header
                continue
            else:
                in_atomtypes_section = False
        
        # Comment out lines in atomtypes section
        if in_atomtypes_section:
            if stripped and not stripped.startswith(';') and not stripped.startswith('#'):
                # This is a data line, comment it out
                result_lines.append('; ' + line)
            else:
                # Keep existing comments/blank lines as-is
                result_lines.append(line)
        else:
            result_lines.append(line)
    
    return '\n'.join(result_lines)


def _rewrite_atoms_section_resname(content: str, new_name: str) -> str:
    """Rewrite the resname column in the [ atoms ] section to ``new_name``.

    GROMACS ``[ atoms ]`` section format::

        [ atoms ]
        ;  Index   type   residue  resname   atom         cgnr     charge       mass
             1     hc         1      MOL     H              1    0.05772791    1.007941

    The resname is the 4th column (0-based index 3) on each data line.  Columns
    are whitespace-separated.

    Comment lines (starting with ``;`` or ``#``) and blank lines are preserved
    unchanged.  Only data lines with at least 4 whitespace-separated fields have
    their resname column replaced.  Leading whitespace on each data line is
    preserved; internal spacing is normalized to single spaces (GROMACS is
    whitespace-flexible in ITP files).

    This step is scoped to the ``[ atoms ]`` section only — it does not touch
    ``[ moleculetype ]``, ``[ atomtypes ]``, ``[ bonds ]`` or any other section
    (those are handled by Steps 1-2 or must remain untouched).

    Args:
        content: ITP content (after Steps 1-2 of ``transform_guest_itp``).
        new_name: New residue name to write into the resname column
            (e.g., ``"MOL_H"``).

    Returns:
        Content with the ``[ atoms ]`` resname column rewritten.  If no
        ``[ atoms ]`` section is found, ``content`` is returned unchanged
        (graceful no-op — some ITPs may lack an ``[ atoms ]`` section).
    """
    # Match the [ atoms ] header and capture the body up to the next
    # [ section ] header or end of string.  re.IGNORECASE so "[ ATOMS ]" is
    # also handled; re.DOTALL so '.' spans newlines.
    match = re.search(
        r'\[\s*atoms\s*\](.*?)(?=\[\s*\w+\s*\]|$)',
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if not match:
        # No [ atoms ] section — graceful no-op
        return content

    body_start = match.start(1)
    body_end = match.end(1)
    body = match.group(1)

    new_lines = []
    for line in body.split('\n'):
        stripped = line.strip()
        # Preserve blank lines and comment lines unchanged
        if not stripped or stripped.startswith(';') or stripped.startswith('#'):
            new_lines.append(line)
            continue
        # Data line: replace resname (field index 3) with new_name
        leading_ws = line[:len(line) - len(line.lstrip())]
        fields = stripped.split()
        if len(fields) >= 4:
            fields[3] = new_name
            new_lines.append(leading_ws + ' '.join(fields))
        else:
            # Not enough fields to contain a resname column — preserve as-is
            new_lines.append(line)

    new_body = '\n'.join(new_lines)
    return content[:body_start] + new_body + content[body_end:]


def transform_guest_itp(itp_content: str, guest_name: str, suffix: str = "_H") -> str:
    """Transform a guest molecule ITP file for hydrate export.
    
    Applies three transformations:
    1. Comments out [ atomtypes ] section (types defined in main .top)
    2. Appends suffix to moleculetype name (e.g., "CH4" → "CH4_H")
    3. Rewrites the resname column in the [ atoms ] section to match the new
       moleculetype name (e.g., "MOL" → "MOL_H"), so the ITP is internally
       consistent.  Deferred from Phase 38-04.
    
    Args:
        itp_content: Original ITP file content as string
        guest_name: Original guest molecule name (e.g., "CH4", "THF", or custom name)
        suffix: Suffix to append (default "_H" for hydrate guests)
        
    Returns:
        Transformed ITP content
        
    Raises:
        ValueError: If transformed residue name exceeds 5 chars (GRO format limit)
    """
    # Step 1: Comment out atomtypes (existing behavior)
    content = comment_out_atomtypes_in_itp(itp_content)
    
    # Step 2: Rewrite moleculetype name with suffix
    # Pattern: [ moleculetype ] header line followed by name line
    # ITP format:
    #   [ moleculetype ]
    #   ; Name        nrexcl
    #   CH4           3
    # We need to change "CH4" → "CH4_H" on the name line
    lines = content.split('\n')
    result_lines = []
    in_moleculetype = False
    new_name = f"{guest_name}{suffix}"
    
    # Validate the new name fits GRO format
    validate_gro_residue_name(new_name, context=f"Transformed guest ITP moleculetype name '{new_name}'")
    # (validate_gro_residue_name raises ValueError with clear message if >5 chars)
    # Note: For built-in guests (CH4_H, THF_H), the name is exactly 5 chars — passes.
    # For custom guests with base names >3 chars, this will raise — intentionally.
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if stripped.startswith('[') and 'moleculetype' in stripped.lower():
            in_moleculetype = True
            result_lines.append(line)
            continue
        
        if in_moleculetype:
            # Check if this is the name line (not a comment, not empty)
            if stripped and not stripped.startswith(';') and not stripped.startswith('#'):
                # This is the moleculetype name line
                # Replace the old name with new name
                parts = stripped.split()
                old_name = parts[0]
                # Replace old_name with new_name, preserving the rest of the line
                # (e.g., "CH4           3" → "CH4_H         3")
                new_line = line.replace(old_name, new_name, 1)
                result_lines.append(new_line)
                in_moleculetype = False
                continue
            elif not stripped:
                # Empty line after moleculetype header — still in section
                result_lines.append(line)
                continue
            else:
                # Comment line — still in section
                result_lines.append(line)
                continue
        
        result_lines.append(line)
    
    content = '\n'.join(result_lines)
    
    # Step 3: Rewrite the resname column in the [ atoms ] section to new_name
    # (the same "{guest_name}{suffix}" value used for the moleculetype rename).
    # This makes a custom guest ITP internally consistent:
    #   [ moleculetype ] etoh_custom_H  ...  [ atoms ] ... MOL_H ...
    # Graceful no-op if no [ atoms ] section is present (deferred Phase 38-04
    # item, completed in Phase 40-02).
    content = _rewrite_atoms_section_resname(content, new_name)
    
    return content


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
            f.write(f"Ice structure {candidate.phase_id} exported by QuickIce\n")
            f.write(f"{n_atoms:5d}\n")

            lines = []
            # Note: The lines.append() calls below are NOT wrapped in try/except because:
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
            atom_num = 0
            for mol_idx in range(nmol):
                base_idx = mol_idx * 3
                
                o_pos = wrapped_positions[base_idx]
                h1_pos = wrapped_positions[base_idx + 1]
                h2_pos = wrapped_positions[base_idx + 2]
                
                mw_pos = compute_mw_position(o_pos, h1_pos, h2_pos)

                res_num = (mol_idx + 1) % 100000

                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                lines.append(f"{res_num:5d}SOL  "
                            f"   OW{atom_num_wrapped:5d}"
                            f"{o_pos[0]:8.3f}{o_pos[1]:8.3f}{o_pos[2]:8.3f}\n")

                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                lines.append(f"{res_num:5d}SOL  "
                            f"  HW1{atom_num_wrapped:5d}"
                            f"{h1_pos[0]:8.3f}{h1_pos[1]:8.3f}{h1_pos[2]:8.3f}\n")

                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                lines.append(f"{res_num:5d}SOL  "
                            f"  HW2{atom_num_wrapped:5d}"
                            f"{h2_pos[0]:8.3f}{h2_pos[1]:8.3f}{h2_pos[2]:8.3f}\n")

                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                lines.append(f"{res_num:5d}SOL  "
                            f"   MW{atom_num_wrapped:5d}"
                            f"{mw_pos[0]:8.3f}{mw_pos[1]:8.3f}{mw_pos[2]:8.3f}\n")

            f.writelines(lines)
            
            cell = candidate.cell
            f.write(f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}"
                    f"{cell[0,1]:10.5f}{cell[0,2]:10.5f}{cell[1,0]:10.5f}"
                    f"{cell[1,2]:10.5f}{cell[2,0]:10.5f}{cell[2,1]:10.5f}\n")
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
        
        f.write("; Defaults compatible with the Amber forcefield\n")
        f.write("[ defaults ]\n")
        f.write("; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ\n")
        f.write("; comb-rule=2 (Lorentz-Berthelot): sigma_ij=(sigma_i+sigma_j)/2, epsilon_ij=sqrt(eps_i*eps_j)\n")
        f.write("; Matches AMBER/GAFF2 convention used by GROMACS-bundled AMBER force fields\n")
        f.write("1               2               yes             0.5     0.8333\n\n")
        
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
        f.write("   2   HW_ice    1  SOL   HW1     1     0.5897   1.00800\n")
        f.write("   3   HW_ice    1  SOL   HW2     1     0.5897   1.00800\n")
        f.write("   4   MW        1  SOL    MW     1    -1.1794   0.00000\n\n")
        
        f.write("[ settles ]\n")
        f.write("; i  funct  doh     dhh\n")
        f.write("  1    1    0.09572  0.15139\n\n")
        
        f.write("[ virtual_sites3 ]\n")
        f.write("; Vsite from                    funct  a          b\n")
        f.write("   4     1       2       3       1      0.13458335 0.13458335\n\n")
        
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


def get_tip4p_itp_path() -> Path:
    """Get the path to the bundled tip4p-ice.itp file.
    
    Returns:
        Path to the tip4p-ice.itp file in the data directory
    """
    import quickice
    package_dir = Path(quickice.__file__).parent
    itp_path = package_dir / "data" / "tip4p-ice.itp"
    
    if itp_path.exists():
        return itp_path
    
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


def write_interface_gro_file(
    iface: InterfaceStructure,
    filepath: str,
    custom_guest_info: list[dict] | None = None,
) -> None:
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
        custom_guest_info: Opt-in list of dicts (one per custom guest) for
            metadata-driven custom guest writing (P3 / EXPORT-05). When
            provided, the guest residue name is taken from the matching
            ``custom_guest_info[i]['residue_name']`` (e.g. 'MOL_H') instead
            of being detected via ``detect_guest_type_from_atoms`` (which
            returns ``None`` for unknown guests and falls through to 'UNK').
            Guest atoms are chunked by the matching ``molecule_index``
            entry's ``count`` instead of the ``count_guest_atoms`` heuristic
            (which miscounts non-ch4/thf guests like ethanol as 5 atoms).
            Dict shape: ``{'mol_type': str, 'residue_name': str,
            'itp_path': Path}`` — ``itp_path`` is unused by the GRO writer
            (consumed by the TOP writers) but kept on the dict for a single
            consistent API across plans 41-02..41-05 / 42-03. When ``None``
            or empty (default), the built-in path
            (``detect_guest_type_from_atoms`` + ``count_guest_atoms`` +
            ch4/thf reordering) is used byte-identically to before this
            param was added.
            
            NOTE: ``write_interface_gro_file`` handles ONE guest mol_type
            in the interface (the interface carries a single guest stream),
            so for the CLI/GUI interface path ``custom_guest_info`` will be
            a 1-element list in practice — but the API is ``list[dict]``
            for consistency with the multi-molecule writers. A legacy
            single ``dict`` is wrapped into a 1-element list with a
            ``DeprecationWarning`` (transition safety through 42-05/42-07).
    
    Note:
        GROMACS .gro format limits atom and residue numbers to 5 digits.
        For systems with >99999 atoms, atom numbers wrap at 100000 (standard GROMACS convention).
        For systems with >99999 residues, residue numbers wrap at 100000.
        
    Units:
        All coordinates are in nm (GROMACS standard).
    """
    # Transition safety: wrap a legacy single dict into a 1-element list.
    if isinstance(custom_guest_info, dict):
        warnings.warn(
            "write_interface_gro_file: custom_guest_info expects a list[dict] "
            "as of plan 42-03 (a single dict is deprecated and will be rejected "
            "in a future release). Wrapping the dict into a 1-element list.",
            DeprecationWarning,
            stacklevel=2,
        )
        custom_guest_info = [custom_guest_info]
    # Units: nm (GROMACS standard)
    # Validate coordinates are in reasonable range for nm units
    if iface.positions is not None:
        max_coord = np.max(np.abs(iface.positions))
        if max_coord > 100:
            logger.warning(f"Coordinates may be in Å instead of nm (max={max_coord:.1f}, GROMACS uses nm)")
    
    # Calculate total atoms:
    # - Ice: ice_nmolecules * 3 input atoms -> ice_nmolecules * 4 output atoms (MW added)
    # - Water: water_nmolecules * 4 (pass through as-is)
    # - Guests: guest_atom_count (no MW, pass through as-is)
    ice_output_atoms = iface.ice_nmolecules * 4  # MW virtual site added
    water_output_atoms = iface.water_nmolecules * 4
    guest_output_atoms = iface.guest_atom_count if iface.guest_atom_count > 0 else 0
    n_atoms = ice_output_atoms + water_output_atoms + guest_output_atoms
    
    # Warn if GRO atom limit exceeded (numbers wrap at 100,000)
    if n_atoms > 99999:
        logger.warning(f"GRO format wraps atom numbers at 100,000 (have {n_atoms} atoms)")
    
    # Wrap positions into box for GRO file output
    # Molecules spanning PBC boundaries can have atoms outside [0, boxsize)
    # We wrap them here for valid GRO format, keeping molecules intact
    if iface.molecule_index:
        # Use molecule-aware wrapping if molecule_index is available
        wrapped_positions = wrap_molecules_into_box(iface.positions, iface.molecule_index, iface.cell)
    else:
        # Fallback to atom-by-atom wrapping (may split molecules)
        wrapped_positions = wrap_positions_into_box(iface.positions, iface.cell)

    # PBC-wrap solute and custom molecule positions if present on InterfaceStructure
    # (defensive: interface-level export only writes ice+water+guests, but
    # solute/custom positions may be carried forward from upstream insertion)
    wrapped_solute_positions = None
    if hasattr(iface, 'solute_positions') and iface.solute_positions is not None and len(iface.solute_positions) > 0:
        wrapped_solute_positions = iface.solute_positions % np.diag(iface.cell)

    wrapped_custom_positions = None
    if hasattr(iface, 'custom_molecule_positions') and iface.custom_molecule_positions is not None and len(iface.custom_molecule_positions) > 0:
        wrapped_custom_positions = iface.custom_molecule_positions % np.diag(iface.cell)

    atom_num = 0

    try:
        with open(filepath, 'w') as f:
            # Title line
            f.write(f"Ice/water interface ({iface.mode}) exported by QuickIce\n")

            # Number of atoms
            f.write(f"{n_atoms:5d}\n")

            # Build all atom lines in memory for better I/O performance
            lines = []
            # Note: The lines.append() calls below are NOT wrapped in try/except because:
            # 1. String formatting of float values cannot fail unless the input array is malformed
            #    (which would be a programming bug, not a runtime error)
            # 2. numpy array indexing (positions[i]) would raise IndexError on malformed data,
            #    which is a programming error that should propagate rather than be silently caught
            # 3. Any actual I/O error occurs during f.writelines() inside the with-open block,
            #    which IS protected by try/except
        
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
                    # Classic ice: O, H, H — no existing MW, must compute
                    h1_pos = wrapped_positions[base_idx + 1]
                    h2_pos = wrapped_positions[base_idx + 2]
                    mw_pos = compute_mw_position(o_pos, h1_pos, h2_pos)
                else:
                    # Hydrate: OW, HW1, HW2, MW — use existing MW
                    # (already correctly placed by molecule-aware wrapping)
                    h1_pos = wrapped_positions[base_idx + 1]
                    h2_pos = wrapped_positions[base_idx + 2]
                    mw_pos = wrapped_positions[base_idx + 3]

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
                if custom_guest_info:
                    # ---- P3 / EXPORT-05: metadata-driven custom guest (no
                    # detect_guest_type_from_atoms, no count_guest_atoms heuristic
                    # — those misfire for custom guests like ethanol). The
                    # interface carries a single guest stream so the matching
                    # custom_guest_info entry resolves the residue name and
                    # molecule_index chunk size. custom_by_moltype is built once
                    # (one entry for the interface path); a multi-element list is
                    # tolerated but only the matching mol_type is consumed. ----
                    custom_by_moltype = {ci["mol_type"]: ci for ci in custom_guest_info}
                    # Find the matching molecule_index entry's mol_type so we can
                    # resolve the residue name + chunk size for the (single) guest
                    # stream carried by this interface.
                    guest_index_entry = next(
                        (m for m in iface.molecule_index
                         if m.mol_type in custom_by_moltype),
                        None,
                    )
                    if guest_index_entry is not None:
                        ci = custom_by_moltype[guest_index_entry.mol_type]
                    else:
                        # No molecule_index entry matches a custom mol_type —
                        # fall back to the first/only entry (defensive; the
                        # caller is expected to keep molecule_index consistent
                        # with custom_guest_info).
                        ci = next(iter(custom_by_moltype.values()))
                    guest_res_name = ci["residue_name"]
                    validate_gro_residue_name(guest_res_name, context="Custom guest GRO residue name")
                    atoms_per_mol = (guest_index_entry.count
                                     if guest_index_entry is not None
                                     else iface.guest_atom_count // max(iface.guest_nmolecules, 1))
                    for mol_idx in range(iface.guest_nmolecules):
                        mol_start = mol_idx * atoms_per_mol
                        mol_end = mol_start + atoms_per_mol
                        mol_atom_names = guest_atom_names[mol_start:mol_end]
                        mol_positions = wrapped_positions[guest_start + mol_start:guest_start + mol_end]
                        res_num = (iface.ice_nmolecules + iface.water_nmolecules + mol_idx + 1) % 100000
                        for i, (atom_name, pos) in enumerate(zip(mol_atom_names, mol_positions)):
                            atom_num += 1
                            atom_num_wrapped = atom_num % 100000
                            lines.append(f"{res_num:5d}{guest_res_name:<5s}"
                                         f"{atom_name:>5s}{atom_num_wrapped:5d}"
                                         f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")
                else:
                    # ---- existing path: built-in hydrate / real interface structures (UNCHANGED) ----
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

                    # Get residue name from hydrate itp file (interface guests are hydrate cage guests)
                    if guest_type:
                        guest_res_name = get_hydrate_guest_residue_name(guest_type)
                    else:
                        guest_res_name = "UNK"

                    validate_gro_residue_name(guest_res_name, context="Interface guest residue name")

                    # Group atoms by molecule and write
                    mol_start = 0
                    for mol_idx in range(iface.guest_nmolecules):
                        guest_atoms = count_guest_atoms(guest_atom_names, mol_start)
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
    except (OSError, ValueError) as e:
        logger.error(f"Failed to write GRO file '{filepath}': {e}")
        if Path(filepath).exists():
            Path(filepath).unlink()
        raise


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


def write_interface_top_file(
    iface: InterfaceStructure,
    filepath: str,
    custom_guest_info: list[dict] | None = None,
) -> None:
    """Write GROMACS topology file for interface structure.
    
    Writes topology with SOL (water) for ice + water, and CH4/THF for guests
    if present. Uses #include directives for molecule definitions.
    
    When ``custom_guest_info`` is supplied (CLI/GUI custom-guest hydrate path),
    the guest is identified by ``mol_type`` (NOT ``detect_guest_type_from_atoms``,
    which returns None for unknown guests → no [molecules] entry today). The
    custom atomtypes are merged via ``_merge_custom_atomtypes`` (oh/ho written,
    hc/c3/h1 deduped), the custom ``.itp`` filename is ``#include`` d, and
    the matching ``custom_guest_info[i]["residue_name"]`` (e.g. ``"MOL_H"``)
    is listed in ``[ molecules ]``. The built-in ch4/thf/co2/h2 path
    (custom_guest_info is None or empty) is unchanged —
    ``detect_guest_type_from_atoms`` + the GAFF2 built-in atomtype blocks +
    ``"{guest_type}_hydrate.itp"`` #include +
    ``get_hydrate_guest_residue_name`` are all preserved verbatim.
    
    Args:
        iface: InterfaceStructure object with ice, guest, and water counts
        filepath: Output file path for .top file
        custom_guest_info: Optional list of dicts (one per custom guest)
            ``{"mol_type": str, "residue_name": str, "itp_path": Path}``
            for custom guest molecules. When None or empty, the built-in
            ch4/thf/co2/h2 path is used (no regression). For the interface
            path with a single custom guest, this is a 1-element list; the
            #include and [molecules] resolve via the matching entry. A legacy
            single ``dict`` is wrapped into a 1-element list with a
            ``DeprecationWarning`` (transition safety through 42-05/42-07).
    """
    # Transition safety: wrap a legacy single dict into a 1-element list.
    if isinstance(custom_guest_info, dict):
        warnings.warn(
            "write_interface_top_file: custom_guest_info expects a list[dict] "
            "as of plan 42-03 (a single dict is deprecated and will be rejected "
            "in a future release). Wrapping the dict into a 1-element list.",
            DeprecationWarning,
            stacklevel=2,
        )
        custom_guest_info = [custom_guest_info]

    total_molecules = iface.ice_nmolecules + iface.guest_nmolecules + iface.water_nmolecules

    # Custom-guest branch is opt-in: only active when the caller supplies
    # custom_guest_info AND the interface actually carries guest atoms/molecules.
    custom_active = (
        custom_guest_info is not None
        and len(custom_guest_info) > 0
        and iface.guest_atom_count > 0
        and iface.guest_nmolecules > 0
    )
    # When custom_active, build a mol_type → dict lookup for the custom guests
    # (interface path: typically 1 entry, but the dict supports N for free).
    custom_by_moltype = (
        {ci["mol_type"]: ci for ci in custom_guest_info}
        if custom_active else {}
    )
    
    with open(filepath, 'w') as f:
        # Header
        f.write("; Generated by QuickIce\n")
        f.write("; TIP4P-ICE water model\n")
        f.write("; Ice/water interface structure\n\n")
        
        # [ defaults ] - force field defaults
        f.write("; Defaults compatible with the Amber forcefield\n")
        f.write("[ defaults ]\n")
        f.write("; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ\n")
        f.write("; comb-rule=2 (Lorentz-Berthelot): sigma_ij=(sigma_i+sigma_j)/2, epsilon_ij=sqrt(eps_i*eps_j)\n")
        f.write("; Matches AMBER/GAFF2 convention used by GROMACS-bundled AMBER force fields\n")
        f.write("1               2               yes             0.5     0.8333\n\n")
        
        # [ atomtypes ] - define custom atom types for TIP4P-ICE and guests
        f.write("[ atomtypes ]\n")
        f.write("; name  bond_type  atomic_number  mass  charge  ptype  sigma (nm)     epsilon (kJ/mol)\n")

        # Initialize dedup tracking
        _written_atomtypes: dict[str, tuple] = {}

        # TIP4P-ICE water atom types
        for name, params in WATER_ATOMTYPES.items():
            f.write(_format_atomtype_line(name, params))
            _written_atomtypes[name] = params

        # Guest atom types if guests are present.
        # P3 fix (EXPORT-05): the custom branch is metadata-driven — it does NOT
        # call detect_guest_type_from_atoms (which returns None for unknown
        # guests like ethanol, falling through to the CH4 fallback that misses
        # oh/ho). The built-in path keeps detect_guest_type_from_atoms.
        guest_type = None
        if not custom_active and iface.guest_atom_count > 0 and iface.guest_nmolecules > 0:
            # Get atom names for the guest region
            # NEW ORDER: ice → water → guests
            # Guest atoms start at ice_atom_count + water_atom_count
            guest_start = iface.ice_atom_count + iface.water_atom_count
            guest_end = guest_start + iface.guest_atom_count
            guest_atom_names = iface.atom_names[guest_start:guest_end]
            guest_type = detect_guest_type_from_atoms(guest_atom_names)

        if custom_active:
            # Merge custom guest atomtypes (oh/ho written, hc/c3/h1 deduped
            # against water/GAFF2). Loops over each custom guest's ITP so
            # shared atomtypes (e.g. hc across two custom guests) are written
            # only once via the _written_atomtypes dedup dict. Replaces the
            # CH4 fallback block.
            for ci in custom_guest_info:
                if ci.get("itp_path"):
                    _merge_custom_atomtypes(
                        f,
                        Path(ci["itp_path"]),
                        _written_atomtypes,
                        f"custom guest {ci['mol_type']} atom types",
                    )
        elif iface.guest_atom_count > 0 and guest_type:
            if guest_type == "ch4":
                _write_atomtypes_block(f, CH4_ATOMTYPE_NAMES,
                                       "CH4 atom types (GAFF2)", _written_atomtypes)
            elif guest_type == "thf":
                _write_atomtypes_block(f, THF_ATOMTYPE_NAMES,
                                       "THF atom types (GAFF2)", _written_atomtypes)
            elif guest_type == "co2":
                _write_atomtypes_block(f, CO2_ATOMTYPE_NAMES,
                                       "CO2 atom types (GAFF2)", _written_atomtypes)
            elif guest_type == "h2":
                _write_atomtypes_block(f, H2_ATOMTYPE_NAMES,
                                       "H2 atom types (GAFF2)", _written_atomtypes)
        elif iface.guest_atom_count > 0:
            # Fallback: unknown guest type, write CH4 atomtypes as default
            _write_atomtypes_block(f, CH4_ATOMTYPE_NAMES,
                                   "CH4 atom types (GAFF2) - default for unknown guest",
                                   _written_atomtypes)
        
        f.write("\n")
        
        # Include molecule definitions (after atomtypes, as GROMACS requires)
        f.write("; Molecule definitions\n")
        f.write('#include "tip4p-ice.itp"\n')

        if custom_active:
            # #include each custom guest .itp (basename of the supplied path,
            # e.g. "etoh.itp"). Matches the staging in copy_custom_guest_itp
            # (plan 41-07) which writes the ITP to output_dir/<src.name>. The
            # interface path typically carries a single custom guest stream so
            # this loop emits one #include line; the loop form keeps the writer
            # list-aware for free.
            for ci in custom_guest_info:
                if ci.get("itp_path"):
                    f.write(f'#include "{Path(ci["itp_path"]).name}"\n')
        elif iface.guest_nmolecules > 0 and guest_type:
            # Include the correct .itp file based on detected guest type
            # Interface guests come from hydrate cages, use hydrate-specific ITP
            f.write(f'#include "{guest_type}_hydrate.itp"\n')
        
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
            if custom_active:
                # P3: custom guest residue name from custom_by_moltype (e.g.
                # "MOL_H") — does NOT call get_hydrate_guest_residue_name
                # (which would fall through to UNK for unknown mol_type).
                # The interface carries a single guest stream, so resolve via
                # the matching molecule_index entry's mol_type (fall back to
                # the first/only entry if molecule_index lacks a match —
                # defensive, the caller is expected to keep them consistent).
                guest_index_entry = next(
                    (m for m in iface.molecule_index
                     if m.mol_type in custom_by_moltype),
                    None,
                )
                if guest_index_entry is not None:
                    ci_mol = custom_by_moltype[guest_index_entry.mol_type]
                else:
                    ci_mol = next(iter(custom_by_moltype.values()))
                f.write(f"{ci_mol['residue_name']:<10s} {iface.guest_nmolecules}\n")
            elif guest_type:
                # Use already-detected guest_type from above
                guest_res_name = get_hydrate_guest_residue_name(guest_type)
                f.write(f"{guest_res_name:<10s} {iface.guest_nmolecules}\n")


def write_multi_molecule_gro_file(
    positions: np.ndarray,
    molecule_index: list[MoleculeIndex],
    cell: np.ndarray,
    filepath: str,
    title: str = "Multi-molecule system exported by QuickIce",
    atom_names: list[str] | None = None,
    registry: 'MoleculetypeRegistry | None' = None,
    custom_guest_info: list[dict] | None = None,
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
        registry: Optional MoleculetypeRegistry for context-specific residue naming.
                  When provided, uses registry to determine residue names for guest
                  molecules (e.g. "CH4_H" for hydrate guests vs "CH4" for default).
        custom_guest_info: Optional list of dicts (one per custom guest) mapping
                  a custom guest mol_type to its residue name, so the writer
                  emits the caller-supplied name (e.g. "MOL_H") instead of
                  falling through to "UNK" for an unknown mol_type. Dict shape:
                  ``{"mol_type": str, "residue_name": str, "itp_path": Path}``.
                  ``itp_path`` is unused by this GRO writer (it is consumed by
                  the TOP writers for the atomtypes merge) but is kept on the
                  dict for a single consistent API across plans 41-02..41-05
                  / 42-03. When None, empty, or the mol_type does not match
                  any entry, the built-in registry/fallback path is used
                  (no regression). A legacy single ``dict`` is wrapped into a
                  1-element list with a ``DeprecationWarning`` (transition
                  safety through 42-05/42-07).
    
    Note:
        GROMACS .gro format limits atom and residue numbers to 5 digits.
        For systems with >99999 atoms, numbers wrap at 100000.
        
    Units:
        All coordinates are in nm (GROMACS standard).
    """
    # Transition safety: wrap a legacy single dict into a 1-element list.
    if isinstance(custom_guest_info, dict):
        warnings.warn(
            "write_multi_molecule_gro_file: custom_guest_info expects a "
            "list[dict] as of plan 42-03 (a single dict is deprecated and "
            "will be rejected in a future release). Wrapping the dict into a "
            "1-element list.",
            DeprecationWarning,
            stacklevel=2,
        )
        custom_guest_info = [custom_guest_info]
    # Units: nm (GROMACS standard)
    # Validate coordinates are in reasonable range for nm units
    if positions is not None and len(positions) > 0:
        max_coord = np.max(np.abs(positions))
        if max_coord > 100:
            logger.warning(f"Coordinates may be in Å instead of nm (max={max_coord:.1f}, GROMACS uses nm)")
    
    n_atoms = len(positions)
    
    # Warn if GRO atom limit exceeded (numbers wrap at 100,000)
    if n_atoms > 99999:
        logger.warning(f"GRO format wraps atom numbers at 100,000 (have {n_atoms} atoms)")
    
    with open(filepath, 'w') as f:
        f.write(f"{title}\n")
        f.write(f"{n_atoms:5d}\n")
        
        lines = []
        atom_num = 0
        # Build the custom_guest_info mol_type → dict lookup ONCE before the
        # per-molecule loop so res_name resolution is O(1) per molecule and
        # multiple custom guests each resolve via their own entry.
        custom_by_moltype = {ci["mol_type"]: ci for ci in (custom_guest_info or [])}
        for res_idx, mol in enumerate(molecule_index):
            # Get residue name — check registry first for context-specific naming
            # (e.g. "CH4_H" for hydrate guests, "CH4_L" for liquid solutes),
            # then fall back to standard naming
            res_name = None
            if registry and mol.mol_type in ["ch4", "thf", "co2", "h2"]:
                # Check hydrate guest registration (key format: "hydrate_CH4")
                hydrate_key = f"hydrate_{mol.mol_type.upper()}"
                if hydrate_key in registry._registered:
                    res_name = registry.get_gromacs_name(hydrate_key)
                # Check liquid solute registration (key format: "liquid_CH4")
                else:
                    liquid_key = f"liquid_{mol.mol_type.upper()}"
                    if liquid_key in registry._registered:
                        res_name = registry.get_gromacs_name(liquid_key)
            
            if res_name is None:
                if mol.mol_type in custom_by_moltype:
                    res_name = custom_by_moltype[mol.mol_type]["residue_name"]
                elif mol.mol_type in ["ch4", "thf", "co2", "h2"]:
                    res_name = get_guest_residue_name(mol.mol_type)
                else:
                    gromacs_info = MOLECULE_TO_GROMACS.get(mol.mol_type, {"res_name": "UNK"})
                    res_name = gromacs_info["res_name"]
            
            validate_gro_residue_name(res_name, context=f"Molecule type '{mol.mol_type}' residue name")
            
            # Residue number wraps at 100000
            res_num = (res_idx + 1) % 100000
            
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
    registry: MoleculetypeRegistry | None = None,
    custom_guest_info: list[dict] | None = None,
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
        registry: Optional MoleculetypeRegistry for unique naming (default: use module-level)
        custom_guest_info: Optional list of dicts (one per custom hydrate guest
                   molecule), enabling EXPORT-01 (residue name in [ molecules ])
                   and EXPORT-03 (atomtypes merge into the main .top).  Shape::
                       {"mol_type": str,         # matches a MoleculeIndex.mol_type
                        "residue_name": str,     # e.g. "MOL_H" (used in [ molecules ])
                        "itp_path": Path}        # source .itp for atomtypes merge
                   When None or empty (default), the writer behaves exactly as
                   before (no regression for built-in ch4/thf/co2/h2 guests).
                   A legacy single ``dict`` is wrapped into a 1-element list
                   with a ``DeprecationWarning`` (transition safety through
                   42-05/42-07).
        
    Note:
        The main .top file uses #include to include separate .itp files.
        Bundled .itp files are in quickice/data/ directory.
        User-provided .itp files (ch4.itp, thf.itp) should have [atomtypes] section
        commented out, as types are defined in the main .top file.
    """
    # Transition safety: wrap a legacy single dict into a 1-element list.
    if isinstance(custom_guest_info, dict):
        warnings.warn(
            "write_multi_molecule_top_file: custom_guest_info expects a "
            "list[dict] as of plan 42-03 (a single dict is deprecated and "
            "will be rejected in a future release). Wrapping the dict into a "
            "1-element list.",
            DeprecationWarning,
            stacklevel=2,
        )
        custom_guest_info = [custom_guest_info]

    reg = registry or _registry
    # Count molecules by type
    counts: dict[str, int] = {}
    unique_types: list[str] = []
    
    for mol in molecule_index:
        if mol.mol_type not in counts:
            counts[mol.mol_type] = 0
            unique_types.append(mol.mol_type)
        counts[mol.mol_type] += 1
    
    # Build the custom_guest_info mol_type → dict lookup ONCE before the
    # per-molecule-type loop so res_name resolution is O(1) per type and
    # multiple custom guests each resolve via their own entry.
    custom_by_moltype = {ci["mol_type"]: ci for ci in (custom_guest_info or [])}
    
    # Build [ molecules ] section entries in order of first appearance
    molecules_lines = []
    for mol_type in unique_types:
        # Try to get name from registry first (for context-specific naming)
        # Fall back to standard naming if not in registry
        res_name = None
        
        # Check if registry has this molecule type registered
        # (future: will be populated when source context is available)
        # For now, maintain backward compatibility
        if registry:
            # Check for hydrate guest registration
            # Registry keys use uppercase molecule names (e.g. hydrate_CH4),
            # but mol_type from molecule_index is lowercase (e.g. "ch4")
            hydrate_key = f"hydrate_{mol_type.upper()}"
            if hydrate_key in reg._registered:
                res_name = reg.get_gromacs_name(hydrate_key)
            # Check for liquid solute registration
            else:
                liquid_key = f"liquid_{mol_type.upper()}"
                if liquid_key in reg._registered:
                    res_name = reg.get_gromacs_name(liquid_key)
        
        # Fall back to standard naming
        if res_name is None:
            if mol_type in custom_by_moltype:
                res_name = custom_by_moltype[mol_type]["residue_name"]
            elif mol_type in ["ch4", "thf", "co2", "h2"]:
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
        f.write("; comb-rule=2 (Lorentz-Berthelot): sigma_ij=(sigma_i+sigma_j)/2, epsilon_ij=sqrt(eps_i*eps_j)\n")
        f.write("; Matches AMBER/GAFF2 convention used by GROMACS-bundled AMBER force fields\n")
        f.write("1               2               yes             0.5     0.8333\n\n")
        
        # [ atomtypes ] - MUST be grouped after [ defaults ] and before #include
        # GROMACS requires all atomtypes before any #include directives
        f.write("[ atomtypes ]\n")
        f.write("; name   bond_type  atomic_number  mass     charge  ptype  sigma (nm)    epsilon (kJ/mol)\n")

        # Initialize dedup tracking BEFORE writing any atomtype blocks
        _written_atomtypes: dict[str, tuple] = {}

        # TIP4P-ICE water atom types
        for name, params in WATER_ATOMTYPES.items():
            f.write(_format_atomtype_line(name, params))
            _written_atomtypes[name] = params

        # Madrid2019 ion atom types (if ions present)
        if "na" in unique_types or "cl" in unique_types:
            f.write("; Ion atom types (Madrid2019)\n")
            if "na" in unique_types:
                params = ION_ATOMTYPES["NA"]
                f.write(_format_atomtype_line("NA", params))
                _written_atomtypes["NA"] = params
            if "cl" in unique_types:
                params = ION_ATOMTYPES["CL"]
                f.write(_format_atomtype_line("CL", params))
                _written_atomtypes["CL"] = params

        # GAFF2 atom types for each molecule type — with deduplication
        # Shared atomtypes (e.g., "hc" in both CH4 and THF) are written only once.
        if "ch4" in unique_types:
            _write_atomtypes_block(f, CH4_ATOMTYPE_NAMES,
                                   "CH4 atom types (GAFF2)", _written_atomtypes)

        if "thf" in unique_types:
            _write_atomtypes_block(f, THF_ATOMTYPE_NAMES,
                                   "THF atom types (GAFF2)", _written_atomtypes)

        if "co2" in unique_types:
            _write_atomtypes_block(f, CO2_ATOMTYPE_NAMES,
                                   "CO2 atom types (GAFF2)", _written_atomtypes)

        if "h2" in unique_types:
            _write_atomtypes_block(f, H2_ATOMTYPE_NAMES,
                                   "H2 atom types (GAFF2)", _written_atomtypes)

        # Custom guest atom types (EXPORT-03): merge from EACH custom guest
        # ITP with dedup.  _written_atomtypes accumulates across guests so
        # shared atomtypes (e.g. "hc" in two custom guests) are written only
        # once.  Written BEFORE the #include block so all [ atomtypes ]
        # (water+ion+GAFF2+custom) precede molecule definitions (GROMACS
        # ordering invariant).  The #include for each custom guest is already
        # produced by the itp_files loop below — do NOT add a second one.
        for ci in (custom_guest_info or []):
            if ci.get("itp_path"):
                _merge_custom_atomtypes(
                    f,
                    Path(ci["itp_path"]),
                    _written_atomtypes,
                    f"custom guest {ci['mol_type']} atom types",
                )

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


def write_ion_gro_file(
    ion_structure: IonStructure,
    filepath: str,
    custom_guest_info: list[dict] | None = None,
) -> None:
    """Write ion structure to GROMACS .gro format.

    Exports molecules in ORDER: SOL (ice+water), guest, NA, CL.
    This matches the expected topology order and GROMACS requirements.

    Args:
        ion_structure: IonStructure object with molecule_index
        filepath: Output file path for .gro file
        custom_guest_info: Opt-in list of dicts (one per custom guest) for
            metadata-driven custom guest writing (mirror of
            ``write_interface_gro_file``'s ``custom_guest_info`` kwarg from
            plans 41-04 / 44.1-09, ``write_solute_gro_file`` from 44.1-11, and
            ``write_custom_molecule_gro_file`` from 44.1-13). When provided,
            the guest residue name is taken from the matching
            ``custom_guest_info[i]['residue_name']`` (e.g. 'MOL_H') instead of
            being detected via ``detect_guest_type_from_atoms`` (which returns
            ``None`` for unknown guests and falls through to 'GUE'). When
            ``None`` or empty (default), the built-in path
            (``detect_guest_type_from_atoms`` + ch4/thf reordering) is used
            byte-identically to before this param was added. Dict shape:
            ``{'mol_type': str, 'residue_name': str, 'itp_path': Path}``. A
            legacy single ``dict`` is wrapped into a 1-element list with a
            ``DeprecationWarning`` (transition safety).

    Note:
        GROMACS .gro format limits atom and residue numbers to 5 digits.
        For systems with >99999 atoms, atom numbers wrap at 100000 (standard GROMACS convention).
    """
    # Transition safety: wrap a legacy single dict into a 1-element list.
    if isinstance(custom_guest_info, dict):
        warnings.warn(
            "write_ion_gro_file: custom_guest_info expects a list[dict] as of "
            "plan 44.1-15 (a single dict is deprecated and will be rejected in "
            "a future release). Wrapping the dict into a 1-element list.",
            DeprecationWarning,
            stacklevel=2,
        )
        custom_guest_info = [custom_guest_info]

    # Custom-guest branch is opt-in: only active when the caller supplies
    # custom_guest_info AND the structure actually carries guest atoms.
    # Mirrors write_solute_gro_file:3215-3227 (plan 44.1-11). IonStructure
    # carries guest_atom_count directly (no interface_structure ref).
    custom_active = (
        custom_guest_info is not None
        and len(custom_guest_info) > 0
        and ion_structure.guest_atom_count > 0
    )
    custom_by_moltype = (
        {ci["mol_type"]: ci for ci in custom_guest_info}
        if custom_active else {}
    )

    # Build an ordered list of molecules: SOL (ice+water) first, then guest, then custom molecules, then solutes, then NA, then CL
    ordered_mols = []
    # Pass 1: SOL molecules (ice + water)
    for mol in ion_structure.molecule_index:
        if mol.mol_type in ("ice", "water"):
            ordered_mols.append(("sol", mol))
    # Pass 2: guest molecules
    for mol in ion_structure.molecule_index:
        if mol.mol_type == "guest":
            ordered_mols.append(("guest", mol))
        elif custom_active and mol.mol_type in custom_by_moltype:
            # Custom guest mol_type (e.g. "etoh_e2e") — collect when the
            # caller opted in via custom_guest_info. The built-in path
            # (custom_guest_info is None -> custom_active is False) only
            # collects literal "guest" entries, preserving byte-identical
            # behavior for ch4/thf. Mirrors write_solute_gro_file's
            # `m.mol_type in custom_by_moltype` lookup (plan 41-04).
            ordered_mols.append(("guest", mol))
    # Pass 3: custom molecules (if present)
    # Note: custom molecules are stored separately, not in molecule_index
    has_custom = ion_structure.custom_molecule_count > 0 and ion_structure.custom_molecule_positions is not None
    if has_custom:
        # Custom molecules are already positioned correctly in the structure
        # We need to determine how many atoms per custom molecule
        atoms_per_custom = 0
        if ion_structure.custom_molecule_atom_count > 0 and ion_structure.custom_molecule_count > 0:
            atoms_per_custom = ion_structure.custom_molecule_atom_count // ion_structure.custom_molecule_count
        
        # Create pseudo-entries for each custom molecule
        for i in range(ion_structure.custom_molecule_count):
            start = i * atoms_per_custom
            ordered_mols.append(("custom", type('obj', (object,), {
                'start_idx': start,
                'count': atoms_per_custom,
                'mol_type': 'custom'
            })()))
    # Pass 4: solute molecules (if present)
    # Note: solutes are stored separately, not in molecule_index
    has_solutes = ion_structure.solute_n_molecules > 0 and ion_structure.solute_positions is not None
    if has_solutes:
        for start, end in ion_structure.solute_molecule_indices:
            # Create a temporary MoleculeIndex-like object for solutes
            ordered_mols.append(("solute", type('obj', (object,), {
                'start_idx': start,
                'count': end - start,
                'mol_type': 'solute'
            })()))
    # Pass 5: NA ions
    for mol in ion_structure.molecule_index:
        if mol.mol_type == "na":
            ordered_mols.append(("na", mol))
    # Pass 6: CL ions
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
        elif mol_type == "custom":
            # Custom molecule atoms (use custom_molecule_positions)
            total_atoms += mol.count
        elif mol_type == "solute":
            # Solute atoms (use solute_positions)
            total_atoms += mol.count
        else:  # na or cl
            total_atoms += 1  # 1 atom per ion

    # Warn if GRO atom limit exceeded (numbers wrap at 100,000)
    if total_atoms > 99999:
        logger.warning(f"GRO format wraps atom numbers at 100,000 (have {total_atoms} atoms)")

    # Wrap positions into box for GRO file output
    # Molecules spanning PBC boundaries can have atoms outside [0, boxsize)
    # We wrap them here for valid GRO format, keeping molecules intact
    wrapped_positions = wrap_molecules_into_box(
        ion_structure.positions, ion_structure.molecule_index, ion_structure.cell
    )

    # Wrap solute positions into PBC box (AN-03 fix)
    # Solute molecules are single molecules that don't span PBC boundaries,
    # so simple modulo wrapping is sufficient.
    if ion_structure.solute_positions is not None and len(ion_structure.solute_positions) > 0:
        wrapped_solute_positions = ion_structure.solute_positions % np.diag(ion_structure.cell)
    else:
        wrapped_solute_positions = ion_structure.solute_positions
    
    # Wrap custom molecule positions into PBC box (AN-03 fix)
    if ion_structure.custom_molecule_positions is not None and len(ion_structure.custom_molecule_positions) > 0:
        wrapped_custom_positions = ion_structure.custom_molecule_positions % np.diag(ion_structure.cell)
    else:
        wrapped_custom_positions = ion_structure.custom_molecule_positions

    atom_num = 0
    res_num = 0

    try:
        with open(filepath, 'w') as f:
            # Title line
            na_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "na")
            cl_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "cl")
            title_parts = [f"Ice/water + ions ({na_count} Na+, {cl_count} Cl-)"]
            if has_custom:
                title_parts.append(f"{ion_structure.custom_molecule_count} custom molecules")
            if has_solutes:
                title_parts.append(f"{ion_structure.solute_n_molecules} {ion_structure.solute_type.upper()} solutes")
            title_parts.append("exported by QuickIce")
            f.write(" + ".join(title_parts) + "\n")

            # Number of atoms
            f.write(f"{total_atoms:5d}\n")

            # Build all atom lines in memory for better I/O performance
            lines = []
            # Note: The lines.append() calls below are NOT wrapped in try/except because:
            # 1. String formatting of float values cannot fail unless the input array is malformed
            #    (which would be a programming bug, not a runtime error)
            # 2. numpy array indexing (positions[i]) would raise IndexError on malformed data,
            #    which is a programming error that should propagate rather than be silently caught
            # 3. Any actual I/O error occurs during f.writelines() inside the with-open block,
            #    which IS protected by try/except

            for mol_type, mol in ordered_mols:
                if mol_type == "sol":
                    # SOL molecule (ice or water)
                    res_num += 1
                    res_num_wrapped = res_num % 100000

                    start = mol.start_idx

                    if mol.mol_type == "ice":
                        # Ice: 3 input atoms (O, H, H) -> 4 output atoms (OW, HW1, HW2, MW)
                        # or: 4 input atoms (OW, HW1, HW2, MW) -> 4 output atoms
                        o_pos = wrapped_positions[start]
                        h1_pos = wrapped_positions[start + 1]
                        h2_pos = wrapped_positions[start + 2]
                        if mol.count == 3:
                            # Classic 3-atom ice: no existing MW, must compute
                            mw_pos = compute_mw_position(o_pos, h1_pos, h2_pos)
                        else:
                            # Hydrate 4-atom ice: MW already exists at index 3
                            # (already correctly placed by molecule-aware wrapping)
                            mw_pos = wrapped_positions[start + 3]

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
                        # Use existing MW from wrapped_positions (already correctly placed)
                        o_pos = wrapped_positions[start]
                        h1_pos = wrapped_positions[start + 1]
                        h2_pos = wrapped_positions[start + 2]
                        mw_pos = wrapped_positions[start + 3]

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
                    # Guest molecule (CH4, THF, or custom guest) — write all atoms
                    res_num += 1
                    res_num_wrapped = res_num % 100000

                    start = mol.start_idx
                    # Get atom names and positions for this molecule
                    mol_atom_names = ion_structure.atom_names[start:start + mol.count]
                    mol_positions = wrapped_positions[start:start + mol.count]

                    if custom_active:
                        # P3 / EXPORT-05 custom guest (mirror write_interface_gro_file
                        # custom branch, plans 41-04 / 44.1-09 / 44.1-11 / 44.1-13):
                        # use the caller-supplied residue name (e.g. "MOL_H")
                        # from custom_guest_info instead of detect_guest_type_from_atoms
                        # (which returns None for custom guests like ethanol). The
                        # ion path carries a single guest stream; resolve via the
                        # matching molecule_index mol_type, falling back to the
                        # first/only custom_guest_info entry (defensive — matches
                        # the solute/custom-molecule writers' fallback for
                        # synthetic 'guest' entries when molecule_index lacks the
                        # real mol_type).
                        ci = custom_by_moltype.get(mol.mol_type)
                        if ci is None:
                            ci = next(iter(custom_by_moltype.values()))
                        guest_res_name = ci["residue_name"]
                        validate_gro_residue_name(
                            guest_res_name,
                            context="Ion custom guest GRO residue name",
                        )
                        # No reorder — custom guest atoms are already in ITP
                        # canonical order (the interface / solute / custom-molecule
                        # writers' custom branches also skip reorder_guest_atoms).
                    else:
                        # Built-in path: detect guest type and get residue name
                        # (byte-identical to before custom_guest_info).
                        # Detect guest type from atom names
                        guest_type = detect_guest_type_from_atoms(mol_atom_names)

                        # Get residue name from hydrate itp file (ion guests are hydrate cage guests)
                        if guest_type:
                            guest_res_name = get_hydrate_guest_residue_name(guest_type)
                        else:
                            guest_res_name = "GUE"  # Fallback

                        validate_gro_residue_name(guest_res_name, context="Ion guest residue name")

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
            
                elif mol_type == "custom":
                    # Custom molecule - write all atoms from custom_molecule_positions
                    res_num += 1
                    res_num_wrapped = res_num % 100000
                
                    # Get residue name (use moleculetype name)
                    res_name = ion_structure.custom_molecule_moleculetype if ion_structure.custom_molecule_moleculetype else "CST"
                    validate_gro_residue_name(res_name, context="Custom molecule residue name")
                
                    # Get atom names and positions for this molecule
                    start = mol.start_idx
                    if ion_structure.custom_molecule_atom_names:
                        mol_atom_names = ion_structure.custom_molecule_atom_names[start:start + mol.count]
                    else:
                        mol_atom_names = [f"C{i}" for i in range(mol.count)]  # Fallback
                
                    if wrapped_custom_positions is not None:
                        mol_positions = wrapped_custom_positions[start:start + mol.count]
                    else:
                        mol_positions = np.zeros((mol.count, 3))  # Fallback
                
                    # Write all atoms
                    for i, (atom_name, pos) in enumerate(zip(mol_atom_names, mol_positions)):
                        atom_num += 1
                        atom_num_wrapped = atom_num % 100000
                        lines.append(f"{res_num_wrapped:5d}{res_name:<5s}"
                                    f"{atom_name:>5s}{atom_num_wrapped:5d}"
                                    f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")
            
                elif mol_type == "solute":
                    # Solute molecule (CH4_L or THF_L) - write all atoms
                    # Solute positions are stored separately in ion_structure.solute_positions
                    res_num += 1
                    res_num_wrapped = res_num % 100000
                
                    start = mol.start_idx
                    count = mol.count
                
                    # Get atom names and positions for this solute molecule
                    mol_atom_names = ion_structure.solute_atom_names[start:start + count]
                    mol_positions = wrapped_solute_positions[start:start + count]
                
                    # Get residue name from registry
                    solute_type_upper = ion_structure.solute_type.upper()
                    if ion_structure.solute_registry:
                        solute_res_name = ion_structure.solute_registry.get_gromacs_name(f"liquid_{ion_structure.solute_type}")
                    else:
                        # Fallback
                        solute_res_name = f"{solute_type_upper}_L"
                
                    validate_gro_residue_name(solute_res_name, context="Solute residue name")
                
                    for i in range(count):
                        atom_num += 1
                        atom_num_wrapped = atom_num % 100000
                        atom_name = mol_atom_names[i]
                        pos = mol_positions[i]
                        lines.append(f"{res_num_wrapped:5d}{solute_res_name:<5s}"
                                    f"{atom_name:>5s}{atom_num_wrapped:5d}"
                                    f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")


                elif mol_type == "na":
                    # NA ion
                    res_num += 1
                    res_num_wrapped = res_num % 100000
                    atom_num += 1
                    atom_num_wrapped = atom_num % 100000
                    pos = wrapped_positions[mol.start_idx]
                    lines.append(f"{res_num_wrapped:5d}NA   "
                                f"   NA{atom_num_wrapped:5d}"
                                f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")

                elif mol_type == "cl":
                    # CL ion
                    res_num += 1
                    res_num_wrapped = res_num % 100000
                    atom_num += 1
                    atom_num_wrapped = atom_num % 100000
                    pos = wrapped_positions[mol.start_idx]
                    lines.append(f"{res_num_wrapped:5d}CL   "
                                f"   CL{atom_num_wrapped:5d}"
                                f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")

            f.writelines(lines)

            # Box vectors (triclinic format)
            cell = ion_structure.cell
            f.write(f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}"
                    f"{cell[0,1]:10.5f}{cell[0,2]:10.5f}{cell[1,0]:10.5f}"
                    f"{cell[1,2]:10.5f}{cell[2,0]:10.5f}{cell[2,1]:10.5f}\n")
    except (OSError, ValueError) as e:
        logger.error(f"Failed to write GRO file '{filepath}': {e}")
        if Path(filepath).exists():
            Path(filepath).unlink()
        raise


def write_ion_top_file(
    ion_structure: IonStructure,
    filepath: str,
    custom_guest_info: list[dict] | None = None,
) -> None:
    """Write GROMACS topology file for ion structure.

    Uses SOL molecule type for water and ice, NA for sodium, CL for chloride.
    Includes guest molecules if present, with dynamic residue name from itp.
    Includes solute molecules if present, with registry-based moleculetype name.
    Includes custom molecules if present, with custom moleculetype from user file.
    Writes [molecules] section in order: SOL (ice+water), guest, custom, solute, NA, CL.

    Args:
        ion_structure: IonStructure object with molecule_index
        filepath: Output file path for .top file
        custom_guest_info: Opt-in list of dicts (one per custom guest) for
            metadata-driven custom guest writing (mirror of
            ``write_interface_top_file``'s ``custom_guest_info`` kwarg from
            plans 41-05 / 44.1-09, ``write_solute_top_file`` from 44.1-11, and
            ``write_custom_molecule_top_file`` from 44.1-13). When supplied,
            the guest is identified by ``mol_type`` (NOT
            ``detect_guest_type_from_atoms``, which returns None for unknown
            guests -> ``guest_res_name="GUE"`` + a non-existent
            ``#include "guest.itp"`` -> grompp fatal). The custom atomtypes are
            merged via ``_merge_custom_atomtypes`` (oh/ho written, hc/c3/h1
            deduped), the custom ``.itp`` filename is ``#include``d, and the
            matching ``custom_guest_info[i]['residue_name']`` (e.g.
            ``"MOL_H"``) is listed in ``[ molecules ]``. The built-in
            ch4/thf path (custom_guest_info is None or empty) is unchanged.
            Dict shape: ``{'mol_type': str, 'residue_name': str,
            'itp_path': Path}``. A legacy single ``dict`` is wrapped into a
            1-element list with a ``DeprecationWarning`` (transition safety).
    """
    # Transition safety: wrap a legacy single dict into a 1-element list.
    if isinstance(custom_guest_info, dict):
        warnings.warn(
            "write_ion_top_file: custom_guest_info expects a list[dict] as of "
            "plan 44.1-15 (a single dict is deprecated and will be rejected in "
            "a future release). Wrapping the dict into a 1-element list.",
            DeprecationWarning,
            stacklevel=2,
        )
        custom_guest_info = [custom_guest_info]

    # Count molecules by type across ENTIRE molecule_index
    # This ensures proper grouping (all SOL together, not stuttering)
    sol_count = sum(1 for m in ion_structure.molecule_index if m.mol_type in ("water", "ice"))
    guest_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "guest")
    na_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "na")
    cl_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "cl")
    
    # Check for custom molecules
    has_custom = ion_structure.custom_molecule_count > 0 and ion_structure.custom_molecule_positions is not None
    custom_count = ion_structure.custom_molecule_count if has_custom else 0
    
    # Check for solutes
    has_solutes = ion_structure.solute_n_molecules > 0 and ion_structure.solute_positions is not None
    solute_count = ion_structure.solute_n_molecules if has_solutes else 0

    # Detect guest type from atom names (for including correct .itp and residue name)
    guest_type = None
    guest_res_name = "GUE"  # Fallback
    # Custom-guest branch is opt-in (mirror write_interface_top_file:1536-1603,
    # plans 41-05 / 44.1-09 / 44.1-11 / 44.1-13). When active, the residue name
    # comes from custom_guest_info (e.g. "MOL_H") and the custom ITP is
    # #include'd by basename; detect_guest_type_from_atoms is skipped (returns
    # None for custom guests). The built-in path (custom_guest_info is None or
    # empty) is byte-identical to before this param was added.
    custom_active = (
        custom_guest_info is not None
        and len(custom_guest_info) > 0
        and guest_count > 0
        and ion_structure.guest_atom_count > 0
    )
    custom_by_moltype = (
        {ci["mol_type"]: ci for ci in custom_guest_info}
        if custom_active else {}
    )
    if custom_active:
        # Resolve the custom residue name via the matching molecule_index
        # entry's mol_type (fall back to the first/only custom_guest_info
        # entry — defensive, matches the interface/solute/custom-molecule
        # writers' fallback when molecule_index lacks a match or uses the
        # literal "guest" mol_type).
        guest_index_entry = next(
            (m for m in ion_structure.molecule_index
             if m.mol_type in custom_by_moltype),
            None,
        )
        if guest_index_entry is not None:
            ci_mol = custom_by_moltype[guest_index_entry.mol_type]
        else:
            ci_mol = next(iter(custom_by_moltype.values()))
        guest_res_name = ci_mol["residue_name"]
    elif guest_count > 0 and ion_structure.guest_atom_count > 0:
        # Built-in path: detect guest type from atom names of first guest
        # Get atom names for the first guest molecule to detect type
        # Find the first guest molecule in molecule_index
        for mol in ion_structure.molecule_index:
            if mol.mol_type == "guest":
                start = mol.start_idx
                mol_atom_names = ion_structure.atom_names[start:start + mol.count]
                guest_type = detect_guest_type_from_atoms(mol_atom_names)
                if guest_type:
                    guest_res_name = get_hydrate_guest_residue_name(guest_type)
                break

    # Parse custom molecule moleculetype name from ITP file (Bug 2 fix)
    # GROMACS requires [molecules] name to match ITP [moleculetype] name
    custom_mol_name = "CUSTOM"  # fallback
    if has_custom and ion_structure.custom_itp_path:
        custom_itp_path = Path(ion_structure.custom_itp_path)
        if custom_itp_path.exists():
            try:
                itp_info = parse_itp_file(custom_itp_path)
                custom_mol_name = itp_info.molecule_name
            except (OSError, ValueError):
                if ion_structure.custom_molecule_moleculetype:
                    custom_mol_name = ion_structure.custom_molecule_moleculetype
        elif ion_structure.custom_molecule_moleculetype:
            custom_mol_name = ion_structure.custom_molecule_moleculetype

    # Determine which GAFF2 atomtype sets are needed (Bug 1 fix)
    needs_ch4_atomtypes = (guest_count > 0 and guest_type == "ch4") or \
                          (has_solutes and ion_structure.solute_type.upper() == "CH4")
    needs_thf_atomtypes = (guest_count > 0 and guest_type == "thf") or \
                          (has_solutes and ion_structure.solute_type.upper() == "THF")

    with open(filepath, 'w') as f:
        # Header
        f.write("; Generated by QuickIce\n")
        f.write("; TIP4P-ICE water model with NaCl ions")
        if guest_count > 0:
            f.write(" and guest molecules")
        if has_custom:
            f.write(f" and {custom_count} custom molecules")
        if has_solutes:
            f.write(f" and {solute_count} {ion_structure.solute_type.upper()} solutes")
        f.write("\n")
        f.write(f"; Structure: {sol_count} SOL (ice+water) + {guest_count} guests")
        if has_custom:
            f.write(f" + {custom_count} custom molecules")
        if has_solutes:
            f.write(f" + {solute_count} {ion_structure.solute_type.upper()} solutes")
        f.write(f" + {na_count} Na+ + {cl_count} Cl-\n\n")
        
        # [ defaults ] - force field defaults
        f.write("[ defaults ]\n")
        f.write("; nbfunc        comb-rule       gen-pairs       fudgeLJ fudgeQQ\n")
        f.write("; comb-rule=2 (Lorentz-Berthelot): sigma_ij=(sigma_i+sigma_j)/2, epsilon_ij=sqrt(eps_i*eps_j)\n")
        f.write("; Matches AMBER/GAFF2 convention used by GROMACS-bundled AMBER force fields\n")
        f.write("1               2               yes             0.5     0.8333\n\n")
        
        # [ atomtypes ] - MUST be before #include directives
        f.write("[ atomtypes ]\n")
        f.write("; name   bond_type  atomic_number  mass     charge  ptype  sigma (nm)    epsilon (kJ/mol)\n")

        # Initialize dedup tracking BEFORE writing any atomtype blocks
        # Maps atomtype name → params tuple for conflict detection
        _written_atomtypes: dict[str, tuple] = {}

        # TIP4P-ICE water atom types
        for name, params in WATER_ATOMTYPES.items():
            f.write(_format_atomtype_line(name, params))
            _written_atomtypes[name] = params

        # Madrid2019 ion atom types (if ions present)
        if na_count > 0 or cl_count > 0:
            f.write("; Ion atom types (Madrid2019)\n")
            if na_count > 0:
                params = ION_ATOMTYPES["NA"]
                f.write(_format_atomtype_line("NA", params))
                _written_atomtypes["NA"] = params
            if cl_count > 0:
                params = ION_ATOMTYPES["CL"]
                f.write(_format_atomtype_line("CL", params))
                _written_atomtypes["CL"] = params

        # Combined GAFF2 atom types for guests AND solutes (Bug 1 fix)
        # Solute ITP files have [atomtypes] pre-commented, so parse_itp_atomtypes
        # returns empty. Use centralized GAFF2_ATOMTYPES dict instead.
        # _write_atomtypes_block skips names already in _written_atomtypes,
        # preventing duplicates (e.g., "hc" shared by CH4 and THF).
        if needs_ch4_atomtypes:
            _write_atomtypes_block(f, CH4_ATOMTYPE_NAMES,
                                   "CH4 atom types (GAFF2)", _written_atomtypes)

        if needs_thf_atomtypes:
            _write_atomtypes_block(f, THF_ATOMTYPE_NAMES,
                                   "THF atom types (GAFF2)", _written_atomtypes)

        # Custom GUEST atom types (hydrate cage guests) — merge via the shared
        # _merge_custom_atomtypes (plan 41-01). ci["itp_path"] is the SOURCE ITP
        # (uncommented [atomtypes]); the #include below resolves to the STAGED
        # transformed ITP (same filename, [atomtypes] commented) written to the
        # export dir by _stage_hydrate_guest_itps (plan 44.1-08). Dedup via
        # _written_atomtypes prevents duplicates with water/GAFF2/custom-molecule
        # types. Mirrors write_solute_top_file:3798-3806 (plans 41-05 / 44.1-11).
        if custom_active:
            for ci in custom_guest_info:
                if ci.get("itp_path"):
                    _merge_custom_atomtypes(
                        f,
                        Path(ci["itp_path"]),
                        _written_atomtypes,
                        f"custom guest {ci['mol_type']} atom types",
                    )

        # Custom molecule atom types (if present) — with deduplication (Bug 3 fix)
        # Checks parameter compatibility: raises ValueError if a custom atomtype
        # name matches an existing one with different LJ parameters.
        if has_custom and ion_structure.custom_itp_path:
            custom_itp_path = Path(ion_structure.custom_itp_path)
            if custom_itp_path.exists():
                custom_atomtypes = parse_itp_atomtypes(custom_itp_path)
                if custom_atomtypes:
                    f.write(f"; {custom_mol_name} custom molecule atom types\n")
                    for atomtype in custom_atomtypes:
                        if len(atomtype) >= 8:
                            at_name = atomtype[0]
                            _check_custom_atomtype_conflict(
                                at_name, atomtype, _written_atomtypes)
                            if at_name not in _written_atomtypes:
                                f.write(_format_custom_atomtype_line(atomtype))
                                # Record params for future conflict checks
                                try:
                                    _written_atomtypes[at_name] = (
                                        atomtype[1], int(atomtype[2]),
                                        float(atomtype[3]), float(atomtype[4]),
                                        atomtype[5], float(atomtype[6]),
                                        float(atomtype[7]))
                                except (ValueError, IndexError):
                                    pass  # Best-effort recording
        
        f.write("\n")
        
        # Include molecule definitions (AFTER atomtypes)
        f.write("; Molecule definitions\n")
        # Include water itp
        f.write('#include "tip4p-ice.itp"\n')

        # Include guest itp if guests present
        if custom_active:
            # #include each custom guest .itp (basename of ci["itp_path"], e.g.
            # "etoh.itp"). The staged transformed ITP (moleculetype MOL_H,
            # [atomtypes] commented, [atoms] resname MOL_H) is written to
            # path.parent/<basename> by _stage_hydrate_guest_itps (plan 44.1-08).
            # Mirrors write_solute_top_file:3847-3849 (plans 41-05 / 44.1-11).
            for ci in custom_guest_info:
                if ci.get("itp_path"):
                    f.write(f'#include "{Path(ci["itp_path"]).name}"\n')
        elif guest_count > 0:
            if guest_type:
                # Include the hydrate-specific .itp file based on guest type
                # Ion tab guests come from hydrate cages, use hydrate ITP
                f.write(f'#include "{guest_type}_hydrate.itp"\n')
            else:
                # Fallback to generic guest.itp
                f.write('#include "guest.itp"\n')

        # Include custom molecule itp if custom molecules present
        if has_custom and ion_structure.custom_itp_path:
            # Copy just the filename from the path
            from pathlib import Path as FilePath
            custom_itp_name = FilePath(ion_structure.custom_itp_path).name
            f.write(f'#include "{custom_itp_name}"\n')

        # Include solute itp if solutes present (liquid solutes use _liquid.itp)
        if has_solutes:
            solute_type_lower = ion_structure.solute_type.lower()
            solute_itp_name = f"{solute_type_lower}_liquid.itp"
            f.write(f'#include "{solute_itp_name}"\n')

        # Include ion itp (from ion export - combined NA+CL in single file)
        f.write('#include "ion.itp"\n\n')

        # [ system ] section
        f.write("[ system ]\n")
        system_name = f"Ice/water + {guest_count} guests"
        if has_custom:
            system_name += f" + {custom_count} custom molecules"
        if has_solutes:
            system_name += f" + {solute_count} {ion_structure.solute_type.upper()} solutes"
        system_name += f" + {na_count} Na+ + {cl_count} Cl- ions"
        f.write(f"{system_name}\n\n")

        # [ molecules ] section - written in ORDER: SOL, guest, custom, solute, NA, CL
        # This matches write_ion_gro_file() output order
        # GROMACS uses [molecules] to know how to group consecutive atoms into molecules
        f.write("[ molecules ]\n")
        f.write("; Compound        #mols\n")

        # Write grouped counts (not stuttering)
        # Order: SOL (ice+water combined), guest, custom, solute, NA, CL
        if sol_count > 0:
            f.write(f"SOL              {sol_count}\n")

        if guest_count > 0:
            f.write(f"{guest_res_name:<17s}{guest_count}\n")

        if has_custom:
            # custom_mol_name computed from ITP file above (Bug 2 fix)
            f.write(f"{custom_mol_name:<17s}{custom_count}\n")

        if has_solutes:
            # Get moleculetype name from registry
            if ion_structure.solute_registry:
                solute_mol_name = ion_structure.solute_registry.get_gromacs_name(f"liquid_{ion_structure.solute_type}")
            else:
                # Fallback
                solute_mol_name = f"{ion_structure.solute_type.upper()}_L"
            f.write(f"{solute_mol_name:<17s}{solute_count}\n")

        if na_count > 0:
            f.write(f"NA               {na_count}\n")

        if cl_count > 0:
            f.write(f"CL               {cl_count}\n")


def write_custom_molecule_gro_file(
    custom_structure: "CustomMoleculeStructure",
    filepath: str,
    custom_guest_info: list[dict] | None = None,
) -> None:
    """Write custom molecule structure to GROMACS .gro format.
    
    Exports COMPLETE system: ice + water + custom molecules.
    Follows write_ion_gro_file() pattern for consistency.
    
    Args:
        custom_structure: CustomMoleculeStructure with complete system data
        filepath: Output file path for .gro file
        custom_guest_info: Opt-in list of dicts (one per custom guest) for
            metadata-driven custom guest writing (mirror of
            ``write_interface_gro_file``'s ``custom_guest_info`` kwarg from
            plans 41-04 / 44.1-09 and ``write_solute_gro_file`` from 44.1-11).
            When provided, the guest residue name is taken from the matching
            ``custom_guest_info[i]['residue_name']`` (e.g. 'MOL_H') instead of
            being detected via ``detect_guest_type_from_atoms`` (which returns
            ``None`` for unknown guests and falls through to 'GUE'). When
            ``None`` or empty (default), the built-in path
            (``detect_guest_type_from_atoms`` + ch4/thf reordering) is used
            byte-identically to before this param was added. Dict shape:
            ``{'mol_type': str, 'residue_name': str, 'itp_path': Path}``. A
            legacy single ``dict`` is wrapped into a 1-element list with a
            ``DeprecationWarning`` (transition safety).
    
    Note:
        GROMACS .gro format limits atom and residue numbers to 5 digits.
        For systems with >99999 atoms, atom numbers wrap at 100000.
    """
    # Transition safety: wrap a legacy single dict into a 1-element list.
    if isinstance(custom_guest_info, dict):
        warnings.warn(
            "write_custom_molecule_gro_file: custom_guest_info expects a "
            "list[dict] as of plan 44.1-13 (a single dict is deprecated and "
            "will be rejected in a future release). Wrapping the dict into a "
            "1-element list.",
            DeprecationWarning,
            stacklevel=2,
        )
        custom_guest_info = [custom_guest_info]

    # Custom-guest branch is opt-in: only active when the caller supplies
    # custom_guest_info AND the structure actually carries guest atoms.
    # Mirrors write_solute_gro_file:3054-3066 (plan 44.1-11).
    custom_active = (
        custom_guest_info is not None
        and len(custom_guest_info) > 0
        and custom_structure.guest_atom_count > 0
    )
    custom_by_moltype = (
        {ci["mol_type"]: ci for ci in custom_guest_info}
        if custom_active else {}
    )

    # Build ordered list of molecules: SOL (ice+water), then custom molecules
    ordered_mols = []
    
    # Pass 1: SOL molecules (ice + water)
    for mol in custom_structure.molecule_index:
        if mol.mol_type in ("ice", "water"):
            ordered_mols.append(("sol", mol))
    
    # Pass 2: Guest molecules (if present)
    if custom_structure.guest_atom_count > 0:
        for mol in custom_structure.molecule_index:
            if mol.mol_type == "guest":
                ordered_mols.append(("guest", mol))
    
    # Pass 3: Custom molecules
    for mol in custom_structure.molecule_index:
        if mol.mol_type == "custom":
            ordered_mols.append(("custom", mol))
    
    # Count total atoms for header
    total_atoms = 0
    for mol_type, mol in ordered_mols:
        if mol_type == "sol":
            if mol.mol_type == "ice":
                total_atoms += 4  # Ice: OW, HW1, HW2, MW
            else:
                total_atoms += mol.count  # Water: 4 atoms
        else:
            total_atoms += mol.count
    
    # Warn if GRO atom limit exceeded
    if total_atoms > 99999:
        logger.warning(f"GRO format wraps atom numbers at 100,000 (have {total_atoms} atoms)")
    
    # Wrap positions into box
    wrapped_positions = wrap_molecules_into_box(
        custom_structure.positions,
        custom_structure.molecule_index,
        custom_structure.cell
    )
    
    atom_num = 0
    res_num = 0
    lines = []
    # Note: The lines.append() calls below are NOT wrapped in try/except because:
    # 1. String formatting of float values cannot fail unless the input array is malformed
    #    (which would be a programming bug, not a runtime error)
    # 2. numpy array indexing (positions[i]) would raise IndexError on malformed data,
    #    which is a programming error that should propagate rather than be silently caught
    # 3. Any actual I/O error occurs during f.writelines() inside the with-open block,
    #    which IS protected by try/except
    
    # Title line
    custom_count = custom_structure.custom_molecule_count
    lines.append(f"Custom molecule system: {custom_count} {custom_structure.moleculetype_name} molecules\n")
    
    # Atom count line
    lines.append(f"{total_atoms}\n")
    
    # Write atoms
    for mol_type, mol in ordered_mols:
        if mol_type == "sol":
            # SOL (ice or water)
            res_num += 1
            res_num_wrapped = res_num % 100000
            
            if mol.mol_type == "ice":
                # Ice: 3 input atoms (O, H, H) -> 4 output atoms (OW, HW1, HW2, MW)
                # or: 4 input atoms (OW, HW1, HW2, MW) -> 4 output atoms
                o_pos = wrapped_positions[mol.start_idx]
                h1_pos = wrapped_positions[mol.start_idx + 1]
                h2_pos = wrapped_positions[mol.start_idx + 2]
                if mol.count == 3:
                    # Classic 3-atom ice: no existing MW, must compute
                    mw_pos = compute_mw_position(o_pos, h1_pos, h2_pos)
                else:
                    # Hydrate 4-atom ice: MW already exists at index 3
                    # (already correctly placed by molecule-aware wrapping)
                    mw_pos = wrapped_positions[mol.start_idx + 3]
                
                # OW (oxygen)
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                lines.append(f"{res_num_wrapped:5d}SOL  "
                             f"   OW{atom_num_wrapped:5d}"
                             f"{o_pos[0]:8.3f}{o_pos[1]:8.3f}{o_pos[2]:8.3f}\n")
                
                # HW1
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                lines.append(f"{res_num_wrapped:5d}SOL  "
                             f"  HW1{atom_num_wrapped:5d}"
                             f"{h1_pos[0]:8.3f}{h1_pos[1]:8.3f}{h1_pos[2]:8.3f}\n")
                
                # HW2
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
                # Use existing MW from wrapped_positions (already correctly placed)
                mol_atom_names = custom_structure.atom_names[mol.start_idx:mol.start_idx + mol.count]
                mol_positions = wrapped_positions[mol.start_idx:mol.start_idx + mol.count]
                
                o_pos = mol_positions[0]
                h1_pos = mol_positions[1]
                h2_pos = mol_positions[2]
                mw_pos = mol_positions[3]
                
                # OW
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                lines.append(f"{res_num_wrapped:5d}SOL  "
                             f"   OW{atom_num_wrapped:5d}"
                             f"{o_pos[0]:8.3f}{o_pos[1]:8.3f}{o_pos[2]:8.3f}\n")
                
                # HW1
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                lines.append(f"{res_num_wrapped:5d}SOL  "
                             f"  HW1{atom_num_wrapped:5d}"
                             f"{h1_pos[0]:8.3f}{h1_pos[1]:8.3f}{h1_pos[2]:8.3f}\n")
                
                # HW2
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
            # Guest molecule (from interface)
            res_num += 1
            res_num_wrapped = res_num % 100000
            
            mol_atom_names = custom_structure.atom_names[mol.start_idx:mol.start_idx + mol.count]
            mol_positions = wrapped_positions[mol.start_idx:mol.start_idx + mol.count]
            
            if custom_active:
                # P3 / EXPORT-05 custom guest (mirror write_solute_gro_file
                # custom branch, plans 41-04 / 44.1-09 / 44.1-11): use the
                # caller-supplied residue name (e.g. "MOL_H") from
                # custom_guest_info instead of detect_guest_type_from_atoms
                # (which returns None for custom guests like ethanol). The
                # custom molecule inserter builds molecule_index with literal
                # mol_type == "guest" (NOT the custom guest's mol_type like
                # "etoh_e2e"), so resolve via the matching custom_by_moltype
                # entry with a fallback to the first/only entry (defensive —
                # matches the solute writer's fallback for synthetic 'guest'
                # entries built when molecule_index lacks the real mol_type).
                ci = custom_by_moltype.get(mol.mol_type)
                if ci is None:
                    ci = next(iter(custom_by_moltype.values()))
                guest_res_name = ci["residue_name"]
                validate_gro_residue_name(
                    guest_res_name,
                    context="Custom molecule system custom guest GRO residue name",
                )
                # No reorder — custom guest atoms are already in ITP canonical
                # order (the interface / solute writers' custom branches also
                # skip reorder_guest_atoms).
            else:
                # Built-in path: detect guest type and use correct residue name
                # (same as ion writer) — byte-identical to before custom_guest_info.
                guest_type = detect_guest_type_from_atoms(mol_atom_names)
                if guest_type:
                    guest_res_name = get_hydrate_guest_residue_name(guest_type)
                    validate_gro_residue_name(guest_res_name, context="Custom molecule system guest residue name")
                    # Reorder guest atoms to match .itp canonical order
                    reorder_mapping = None
                    if guest_type in ["ch4", "thf"]:
                        mol_atom_names, reorder_mapping = reorder_guest_atoms(mol_atom_names, guest_type)
                        if reorder_mapping is not None:
                            mol_positions = [mol_positions[i] for i in reorder_mapping]
                else:
                    guest_res_name = "GUE"  # Fallback for unknown guest types
            
            for i in range(mol.count):
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                atom_name = mol_atom_names[i]
                pos = mol_positions[i]
                lines.append(
                    f"{res_num_wrapped:5d}{guest_res_name:<5s}{atom_name:>5s}{atom_num_wrapped:5d}"
                    f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n"
                )
        
        elif mol_type == "custom":
            # Custom molecule
            res_num += 1
            res_num_wrapped = res_num % 100000
            
            mol_atom_names = custom_structure.atom_names[mol.start_idx:mol.start_idx + mol.count]
            mol_positions = wrapped_positions[mol.start_idx:mol.start_idx + mol.count]
            
            # Use moleculetype_name as residue name (validate for GRO 5-char limit)
            res_name = custom_structure.moleculetype_name
            validate_gro_residue_name(res_name, context="Custom molecule residue name")
            
            for i in range(mol.count):
                atom_num += 1
                atom_num_wrapped = atom_num % 100000
                atom_name = mol_atom_names[i]
                pos = mol_positions[i]
                lines.append(
                    f"{res_num_wrapped:5d}{res_name:<5s}{atom_name:>5s}{atom_num_wrapped:5d}"
                    f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n"
                )
    
    # Box vectors
    box_line = f"{custom_structure.cell[0, 0]:10.5f}{custom_structure.cell[1, 1]:10.5f}{custom_structure.cell[2, 2]:10.5f}\n"
    lines.append(box_line)
    
    try:
        with open(filepath, 'w') as f:
            f.writelines(lines)
    except (OSError, ValueError) as e:
        logger.error(f"Failed to write GRO file '{filepath}': {e}")
        if Path(filepath).exists():
            Path(filepath).unlink()
        raise
    
    logger.info(f"Wrote GRO file for custom molecule system: {filepath}")


def write_custom_molecule_top_file(
    custom_structure: "CustomMoleculeStructure",
    filepath: str,
    custom_guest_info: list[dict] | None = None,
) -> None:
    """Write GROMACS topology file for custom molecule structure.
    
    Uses SOL molecule type for water and ice, includes custom molecule.
    Writes [molecules] section in order: SOL (ice+water), guest (if present), custom.
    
    Args:
        custom_structure: CustomMoleculeStructure with complete system data
        filepath: Output file path for .top file
        custom_guest_info: Opt-in list of dicts (one per custom guest) for
            metadata-driven custom guest writing (mirror of
            ``write_interface_top_file``'s ``custom_guest_info`` kwarg from
            plans 41-05 / 44.1-09 and ``write_solute_top_file`` from 44.1-11).
            When supplied, the guest is identified by ``mol_type`` (NOT
            ``detect_guest_type_from_atoms``, which returns None for unknown
            guests -> ``guest_res_name="GUE"`` + a non-existent
            ``#include "guest.itp"`` -> grompp fatal). The custom atomtypes are
            merged via ``_merge_custom_atomtypes`` (oh/ho written, hc/c3/h1
            deduped), the custom ``.itp`` filename is ``#include``d, and the
            matching ``custom_guest_info[i]['residue_name']`` (e.g.
            ``"MOL_H"``) is listed in ``[ molecules ]``. The built-in
            ch4/thf path (custom_guest_info is None or empty) is unchanged.
            Dict shape: ``{'mol_type': str, 'residue_name': str,
            'itp_path': Path}``. A legacy single ``dict`` is wrapped into a
            1-element list with a ``DeprecationWarning`` (transition safety).
    """
    # Transition safety: wrap a legacy single dict into a 1-element list.
    if isinstance(custom_guest_info, dict):
        warnings.warn(
            "write_custom_molecule_top_file: custom_guest_info expects a "
            "list[dict] as of plan 44.1-13 (a single dict is deprecated and "
            "will be rejected in a future release). Wrapping the dict into a "
            "1-element list.",
            DeprecationWarning,
            stacklevel=2,
        )
        custom_guest_info = [custom_guest_info]

    # Count molecules by type
    sol_count = sum(1 for m in custom_structure.molecule_index if m.mol_type in ("water", "ice"))
    guest_count = sum(1 for m in custom_structure.molecule_index if m.mol_type == "guest")
    custom_count = custom_structure.custom_molecule_count
    
    # Detect guest type from atom names (for including correct .itp and residue name)
    # Mirrors the pattern from write_ion_top_file() / write_solute_top_file (44.1-11).
    guest_type = None
    guest_res_name = "GUE"  # Fallback
    # Custom-guest branch is opt-in (mirror write_solute_top_file:3506-3556,
    # plans 41-05 / 44.1-09 / 44.1-11). When active, the residue name comes
    # from custom_guest_info (e.g. "MOL_H") and the custom ITP is #include'd
    # by basename; detect_guest_type_from_atoms is skipped (returns None for
    # custom guests). The built-in path (custom_guest_info is None or empty)
    # is byte-identical to before this param was added.
    custom_active = (
        custom_guest_info is not None
        and len(custom_guest_info) > 0
        and guest_count > 0
        and custom_structure.guest_atom_count > 0
    )
    custom_by_moltype = (
        {ci["mol_type"]: ci for ci in custom_guest_info}
        if custom_active else {}
    )
    if custom_active:
        # Resolve the custom residue name via the matching molecule_index
        # entry's mol_type. The custom molecule inserter builds molecule_index
        # with literal mol_type == "guest" (NOT the custom guest's mol_type
        # like "etoh_e2e"), so fall back to the first/only custom_guest_info
        # entry (defensive — matches the solute writer's fallback for
        # synthetic 'guest' entries when molecule_index lacks the real
        # mol_type).
        guest_index_entry = next(
            (m for m in custom_structure.molecule_index
             if m.mol_type in custom_by_moltype),
            None,
        )
        if guest_index_entry is not None:
            ci_mol = custom_by_moltype[guest_index_entry.mol_type]
        else:
            ci_mol = next(iter(custom_by_moltype.values()))
        guest_res_name = ci_mol["residue_name"]
    elif guest_count > 0 and custom_structure.guest_atom_count > 0:
        # Built-in path: detect guest type from atom names of first guest
        # Get atom names for the first guest molecule to detect type
        for mol in custom_structure.molecule_index:
            if mol.mol_type == "guest":
                start = mol.start_idx
                mol_atom_names = custom_structure.atom_names[start:start + mol.count]
                guest_type = detect_guest_type_from_atoms(mol_atom_names)
                if guest_type:
                    guest_res_name = get_hydrate_guest_residue_name(guest_type)
                break
    
    # Parse custom molecule moleculetype name from ITP file (Bug 2 fix)
    # GROMACS requires [molecules] name to match ITP [moleculetype] name
    custom_mol_name = custom_structure.moleculetype_name  # fallback to registry default
    if custom_structure.itp_path and custom_structure.itp_path.exists():
        try:
            itp_info = parse_itp_file(custom_structure.itp_path)
            custom_mol_name = itp_info.molecule_name
        except (OSError, ValueError):
            pass  # Keep moleculetype_name as fallback

    # Determine which GAFF2 atomtype sets are needed for deduplication
    needs_ch4_atomtypes = (guest_count > 0 and guest_type == "ch4")
    needs_thf_atomtypes = (guest_count > 0 and guest_type == "thf")

    with open(filepath, 'w') as f:
        # Header
        f.write("; Generated by QuickIce\n")
        f.write(f"; Custom molecule system: {sol_count} SOL + {guest_count} guests + {custom_count} {custom_mol_name}\n\n")
        
        # [ defaults ] - force field defaults
        f.write("[ defaults ]\n")
        f.write("; nbfunc        comb-rule       gen-pairs       fudgeLJ fudgeQQ\n")
        f.write("; comb-rule=2 (Lorentz-Berthelot): sigma_ij=(sigma_i+sigma_j)/2, epsilon_ij=sqrt(eps_i*eps_j)\n")
        f.write("; Matches AMBER/GAFF2 convention used by GROMACS-bundled AMBER force fields\n")
        f.write("1               2               yes             0.5     0.8333\n\n")
        
        # [ atomtypes ] - MUST be before #include directives
        f.write("[ atomtypes ]\n")
        f.write("; name   bond_type  atomic_number  mass     charge  ptype  sigma (nm)    epsilon (kJ/mol)\n")

        # Initialize dedup tracking BEFORE writing any atomtype blocks
        _written_atomtypes: dict[str, tuple] = {}

        # TIP4P-ICE water atom types
        for name, params in WATER_ATOMTYPES.items():
            f.write(_format_atomtype_line(name, params))
            _written_atomtypes[name] = params
        
        # GAFF2 atom types for guests (if present) — with deduplication
        if needs_ch4_atomtypes:
            _write_atomtypes_block(f, CH4_ATOMTYPE_NAMES,
                                   "CH4 atom types (GAFF2)", _written_atomtypes)
        if needs_thf_atomtypes:
            _write_atomtypes_block(f, THF_ATOMTYPE_NAMES,
                                   "THF atom types (GAFF2)", _written_atomtypes)

        # Custom GUEST atom types (hydrate cage guests) — merge via the shared
        # _merge_custom_atomtypes (plan 41-01). ci["itp_path"] is the SOURCE ITP
        # (uncommented [atomtypes]); the #include below resolves to the STAGED
        # transformed ITP (same filename, [atomtypes] commented) written to the
        # export dir by _stage_hydrate_guest_itps (plan 44.1-08). Dedup via
        # _written_atomtypes prevents duplicates with water/GAFF2/custom-molecule
        # types. Mirrors write_solute_top_file:3630-3645 (plans 41-05 / 44.1-11).
        if custom_active:
            for ci in custom_guest_info:
                if ci.get("itp_path"):
                    _merge_custom_atomtypes(
                        f,
                        Path(ci["itp_path"]),
                        _written_atomtypes,
                        f"custom guest {ci['mol_type']} atom types",
                    )
        
        # Custom molecule atom types - parse from ITP file, with dedup (Bug 3 fix)
        # Checks parameter compatibility: raises ValueError if a custom atomtype
        # name matches an existing one with different LJ parameters.
        if custom_structure.itp_path and custom_structure.itp_path.exists():
            custom_atomtypes = parse_itp_atomtypes(custom_structure.itp_path)
            if custom_atomtypes:
                f.write(f"; {custom_mol_name} custom molecule atom types\n")
                for atomtype in custom_atomtypes:
                    if len(atomtype) >= 8:
                        at_name = atomtype[0]
                        _check_custom_atomtype_conflict(
                            at_name, atomtype, _written_atomtypes)
                        if at_name not in _written_atomtypes:
                            f.write(_format_custom_atomtype_line(atomtype))
                            # Record params for future conflict checks
                            try:
                                _written_atomtypes[at_name] = (
                                    atomtype[1], int(atomtype[2]),
                                    float(atomtype[3]), float(atomtype[4]),
                                    atomtype[5], float(atomtype[6]),
                                    float(atomtype[7]))
                            except (ValueError, IndexError):
                                pass  # Best-effort recording
        
        f.write("\n")
        
        # Include molecule definitions (AFTER atomtypes)
        f.write("; Molecule definitions\n")
        f.write('#include "tip4p-ice.itp"\n')
        
        # Include guest topology if present
        if custom_active:
            # #include each custom guest .itp (basename of ci["itp_path"], e.g.
            # "etoh.itp"). The staged transformed ITP (moleculetype MOL_H,
            # [atomtypes] commented, [atoms] resname MOL_H) is written to
            # path.parent/<basename> by _stage_hydrate_guest_itps (plan 44.1-08).
            # Mirrors write_solute_top_file:3680-3688 (plans 41-05 / 44.1-11).
            for ci in custom_guest_info:
                if ci.get("itp_path"):
                    f.write(f'#include "{Path(ci["itp_path"]).name}"\n')
        elif guest_count > 0:
            if guest_type:
                # Include the hydrate-specific .itp file based on guest type
                f.write(f'#include "{guest_type}_hydrate.itp"\n')
            else:
                # Fallback to generic guest.itp
                f.write('#include "guest.itp"\n')
        
        # Include custom molecule ITP
        f.write(f'#include "{custom_structure.itp_path.name}"\n\n')
        
        # [ system ] section
        f.write("[ system ]\n")
        system_name = f"Ice/water + {custom_count} {custom_mol_name}"
        if guest_count > 0:
            system_name = f"Ice/water + {guest_count} guests + {custom_count} {custom_mol_name}"
        f.write(f"{system_name}\n\n")
        
        # [ molecules ] section - ORDER: SOL, guest, custom
        f.write("[ molecules ]\n")
        f.write("; Compound        #mols\n")
        
        if sol_count > 0:
            f.write(f"SOL              {sol_count}\n")
        
        if guest_count > 0:
            f.write(f"{guest_res_name:<17s}{guest_count}\n")
        
        # custom_mol_name from ITP file (Bug 2 fix)
        f.write(f"{custom_mol_name:<17s}{custom_count}\n")

    logger.info(f"Wrote topology file: {filepath}")


def write_solute_gro_file(
    solute_structure: "SoluteStructure",
    filepath: str,
    custom_guest_info: list[dict] | None = None,
) -> None:
    """Write solute structure to GROMACS .gro format.

    Exports molecules in ORDER: SOL (ice+water), guest, custom, solute.
    This matches the expected topology order and GROMACS requirements.
    Ice molecules are expanded from 3→4 atoms (MW virtual site added).
    Water molecules have MW recomputed from OW/HW1/HW2 positions.

    Args:
        solute_structure: SoluteStructure object with solute + interface data
        filepath: Output file path for .gro file
        custom_guest_info: Opt-in list of dicts (one per custom guest) for
            metadata-driven custom guest writing (mirror of
            ``write_interface_gro_file``'s ``custom_guest_info`` kwarg from
            plans 41-04 / 44.1-09). When provided, the guest residue name is
            taken from the matching ``custom_guest_info[i]['residue_name']``
            (e.g. 'MOL_H') instead of being detected via
            ``detect_guest_type_from_atoms`` (which returns ``None`` for
            unknown guests and falls through to 'GUE'). When ``None`` or
            empty (default), the built-in path
            (``detect_guest_type_from_atoms`` + ``count_guest_atoms`` +
            ch4/thf reordering) is used byte-identically to before this
            param was added. Dict shape: ``{'mol_type': str,
            'residue_name': str, 'itp_path': Path}``. A legacy single
            ``dict`` is wrapped into a 1-element list with a
            ``DeprecationWarning`` (transition safety).

    Note:
        GROMACS .gro format limits atom and residue numbers to 5 digits.
        For systems with >99999 atoms, atom numbers wrap at 100000.
    """
    interface = solute_structure.interface_structure

    # Transition safety: wrap a legacy single dict into a 1-element list.
    if isinstance(custom_guest_info, dict):
        warnings.warn(
            "write_solute_gro_file: custom_guest_info expects a list[dict] "
            "as of plan 44.1-11 (a single dict is deprecated and will be rejected "
            "in a future release). Wrapping the dict into a 1-element list.",
            DeprecationWarning,
            stacklevel=2,
        )
        custom_guest_info = [custom_guest_info]

    # Custom-guest branch is opt-in: only active when the caller supplies
    # custom_guest_info AND the interface actually carries guest atoms/molecules.
    # Mirrors write_interface_gro_file:1253-1312 (plans 41-04 / 44.1-09).
    custom_active = (
        custom_guest_info is not None
        and len(custom_guest_info) > 0
        and interface.guest_atom_count > 0
        and interface.guest_nmolecules > 0
    )
    custom_by_moltype = (
        {ci["mol_type"]: ci for ci in custom_guest_info}
        if custom_active else {}
    )

    # Build ordered list of molecules: SOL (ice+water), guest, custom, solute
    ordered_mols = []

    # Pass 1: SOL molecules (ice + water) from interface
    # FALLBACK: When molecule_index is empty (real GenIce2 data), build
    # synthetic molecule entries from ice_nmolecules and water_nmolecules
    # counts, mirroring write_interface_gro_file's approach.
    if interface.molecule_index:
        for mol in interface.molecule_index:
            if mol.mol_type in ("ice", "water"):
                ordered_mols.append(("sol", mol))
    else:
        # Build from ice_nmolecules/water_nmolecules when molecule_index is empty
        # (real GenIce2-generated InterfaceStructures have empty molecule_index)
        atoms_per_ice_mol = 3 if "O" in interface.atom_names[:interface.ice_atom_count] else 4
        for mol_idx in range(interface.ice_nmolecules):
            base_idx = mol_idx * atoms_per_ice_mol
            ordered_mols.append(("sol", type('obj', (object,), {
                'start_idx': base_idx,
                'count': atoms_per_ice_mol,
                'mol_type': 'ice'
            })()))
        for mol_idx in range(interface.water_nmolecules):
            base_idx = interface.ice_atom_count + mol_idx * 4
            ordered_mols.append(("sol", type('obj', (object,), {
                'start_idx': base_idx,
                'count': 4,
                'mol_type': 'water'
            })()))

    # Pass 2: guest molecules (if present in interface)
    if interface.guest_atom_count > 0 and interface.guest_nmolecules > 0:
        if interface.molecule_index:
            for mol in interface.molecule_index:
                if mol.mol_type == "guest":
                    ordered_mols.append(("guest", mol))
                elif custom_active and mol.mol_type in custom_by_moltype:
                    # Custom guest mol_type (e.g. "etoh_e2e") — collect when the
                    # caller opted in via custom_guest_info. The built-in path
                    # (custom_guest_info is None -> custom_active is False) only
                    # collects literal "guest" entries, preserving byte-identical
                    # behavior for ch4/thf. Mirrors write_interface_gro_file's
                    # `m.mol_type in custom_by_moltype` lookup (plan 41-04).
                    ordered_mols.append(("guest", mol))
        else:
            # Build guest entries from counts when molecule_index is empty
            guest_start = interface.ice_atom_count + interface.water_atom_count
            atoms_per_guest = interface.guest_atom_count // max(interface.guest_nmolecules, 1)
            for mol_idx in range(interface.guest_nmolecules):
                start = guest_start + mol_idx * atoms_per_guest
                ordered_mols.append(("guest", type('obj', (object,), {
                    'start_idx': start,
                    'count': atoms_per_guest,
                    'mol_type': 'guest'
                })()))

    # Pass 3: custom molecules (if present, propagated from custom tab)
    has_custom = (solute_structure.custom_molecule_count > 0 and
                  solute_structure.custom_molecule_positions is not None)
    if has_custom:
        atoms_per_custom = 0
        if solute_structure.custom_molecule_atom_count > 0 and solute_structure.custom_molecule_count > 0:
            atoms_per_custom = solute_structure.custom_molecule_atom_count // solute_structure.custom_molecule_count

        for i in range(solute_structure.custom_molecule_count):
            start = i * atoms_per_custom
            ordered_mols.append(("custom", type('obj', (object,), {
                'start_idx': start,
                'count': atoms_per_custom,
                'mol_type': 'custom'
            })()))

    # Pass 4: solute molecules (from solute_structure.positions)
    has_solutes = solute_structure.n_molecules > 0 and solute_structure.positions is not None
    if has_solutes:
        for start, end in solute_structure.molecule_indices:
            ordered_mols.append(("solute", type('obj', (object,), {
                'start_idx': start,
                'count': end - start,
                'mol_type': 'solute'
            })()))

    # Count total atoms for header
    total_atoms = 0
    for mol_type, mol in ordered_mols:
        if mol_type == "sol":
            if mol.mol_type == "ice":
                total_atoms += 4  # Ice: 3→4 atoms (OW, HW1, HW2, MW)
            else:
                total_atoms += mol.count  # Water: 4 atoms
        elif mol_type == "guest":
            total_atoms += mol.count
        elif mol_type == "custom":
            total_atoms += mol.count
        elif mol_type == "solute":
            total_atoms += mol.count

    # Warn if GRO atom limit exceeded
    if total_atoms > 99999:
        logger.warning(f"GRO format wraps atom numbers at 100,000 (have {total_atoms} atoms)")

    # Wrap positions into box using molecule-aware wrapping
    if interface.molecule_index:
        wrapped_positions = wrap_molecules_into_box(
            interface.positions, interface.molecule_index, interface.cell
        )
    else:
        # Fallback: atom-by-atom wrapping when molecule_index is empty
        wrapped_positions = wrap_positions_into_box(
            interface.positions, interface.cell
        )

    # Wrap custom molecule positions into PBC box (same as AN-03 fix in write_ion_gro_file)
    if solute_structure.custom_molecule_positions is not None and len(solute_structure.custom_molecule_positions) > 0:
        wrapped_custom_mol_positions = solute_structure.custom_molecule_positions % np.diag(solute_structure.cell)
    else:
        wrapped_custom_mol_positions = solute_structure.custom_molecule_positions

    # Wrap solute positions into PBC box (same as AN-03 fix in write_ion_gro_file)
    # Solute positions are a SEPARATE array from interface.positions, so
    # wrap_molecules_into_box does NOT cover them. Simple modulo wrapping
    # is sufficient — solute molecules (CH4, THF) are single small molecules
    # that don't span PBC boundaries.
    if solute_structure.positions is not None and len(solute_structure.positions) > 0:
        wrapped_solute_positions = solute_structure.positions % np.diag(solute_structure.cell)
    else:
        wrapped_solute_positions = solute_structure.positions

    atom_num = 0
    res_num = 0
    lines = []
    # Note: The lines.append() calls below are NOT wrapped in try/except because:
    # 1. String formatting of float values cannot fail unless the input array is malformed
    #    (which would be a programming bug, not a runtime error)
    # 2. numpy array indexing (positions[i]) would raise IndexError on malformed data,
    #    which is a programming error that should propagate rather than be silently caught
    # 3. Any actual I/O error occurs during f.writelines() inside the with-open block,
    #    which IS protected by try/except

    try:
        with open(filepath, 'w') as f:
            # Title line
            title_parts = ["Ice/water interface"]
            if has_custom:
                title_parts.append(f"{solute_structure.custom_molecule_count} custom molecules")
            if has_solutes:
                title_parts.append(f"{solute_structure.n_molecules} {solute_structure.solute_type.upper()} solutes")
            title_parts.append("exported by QuickIce")
            f.write(" + ".join(title_parts) + "\n")

            # Number of atoms
            f.write(f"{total_atoms:5d}\n")

            for mol_type, mol in ordered_mols:
                if mol_type == "sol":
                    # SOL molecule (ice or water)
                    res_num += 1
                    res_num_wrapped = res_num % 100000
                    start = mol.start_idx

                    if mol.mol_type == "ice":
                        # Ice: 3 input atoms (O, H, H) -> 4 output atoms (OW, HW1, HW2, MW)
                        # or: 4 input atoms (OW, HW1, HW2, MW) -> 4 output atoms
                        o_pos = wrapped_positions[start]
                        h1_pos = wrapped_positions[start + 1]
                        h2_pos = wrapped_positions[start + 2]
                        if mol.count == 3:
                            # Classic 3-atom ice: no existing MW, must compute
                            mw_pos = compute_mw_position(o_pos, h1_pos, h2_pos)
                        else:
                            # Hydrate 4-atom ice: MW already exists at index 3
                            # (already correctly placed by molecule-aware wrapping)
                            mw_pos = wrapped_positions[start + 3]

                        # OW (oxygen)
                        atom_num += 1
                        atom_num_wrapped = atom_num % 100000
                        lines.append(f"{res_num_wrapped:5d}SOL  "
                                    f"   OW{atom_num_wrapped:5d}"
                                    f"{o_pos[0]:8.3f}{o_pos[1]:8.3f}{o_pos[2]:8.3f}\n")

                        # HW1
                        atom_num += 1
                        atom_num_wrapped = atom_num % 100000
                        lines.append(f"{res_num_wrapped:5d}SOL  "
                                    f"  HW1{atom_num_wrapped:5d}"
                                    f"{h1_pos[0]:8.3f}{h1_pos[1]:8.3f}{h1_pos[2]:8.3f}\n")

                        # HW2
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
                        # Use existing MW from wrapped_positions (already correctly placed)
                        o_pos = wrapped_positions[start]
                        h1_pos = wrapped_positions[start + 1]
                        h2_pos = wrapped_positions[start + 2]
                        mw_pos = wrapped_positions[start + 3]

                        # OW
                        atom_num += 1
                        atom_num_wrapped = atom_num % 100000
                        lines.append(f"{res_num_wrapped:5d}SOL  "
                                    f"   OW{atom_num_wrapped:5d}"
                                    f"{o_pos[0]:8.3f}{o_pos[1]:8.3f}{o_pos[2]:8.3f}\n")

                        # HW1
                        atom_num += 1
                        atom_num_wrapped = atom_num % 100000
                        lines.append(f"{res_num_wrapped:5d}SOL  "
                                    f"  HW1{atom_num_wrapped:5d}"
                                    f"{h1_pos[0]:8.3f}{h1_pos[1]:8.3f}{h1_pos[2]:8.3f}\n")

                        # HW2
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
                    # Guest molecule (CH4, THF, or custom guest) — hydrate cage guests
                    res_num += 1
                    res_num_wrapped = res_num % 100000

                    start = mol.start_idx
                    mol_atom_names = interface.atom_names[start:start + mol.count]
                    mol_positions = wrapped_positions[start:start + mol.count]

                    if custom_active:
                        # P3 / EXPORT-05 custom guest (mirror write_interface_gro_file
                        # custom branch, plans 41-04 / 44.1-09): use the caller-
                        # supplied residue name (e.g. "MOL_H") from custom_guest_info
                        # instead of detect_guest_type_from_atoms (which returns
                        # None for custom guests like ethanol). The solute path
                        # carries a single guest stream; resolve via the matching
                        # molecule_index mol_type, falling back to the first/only
                        # custom_guest_info entry (defensive — matches the interface
                        # writer's fallback when molecule_index lacks a match or is
                        # empty and synthetic 'guest' entries were built above).
                        ci = custom_by_moltype.get(mol.mol_type)
                        if ci is None:
                            ci = next(iter(custom_by_moltype.values()))
                        guest_res_name = ci["residue_name"]
                        validate_gro_residue_name(
                            guest_res_name,
                            context="Solute custom guest GRO residue name",
                        )
                        # No reorder — custom guest atoms are already in ITP
                        # canonical order (the interface writer's custom branch
                        # also skips reorder_guest_atoms).
                    else:
                        # Built-in path: detect guest type and get residue name
                        guest_type = detect_guest_type_from_atoms(mol_atom_names)
                        if guest_type:
                            guest_res_name = get_hydrate_guest_residue_name(guest_type)
                        else:
                            guest_res_name = "GUE"  # Fallback

                        validate_gro_residue_name(
                            guest_res_name,
                            context="Solute system guest residue name",
                        )

                        # Reorder guest atoms to match .itp canonical order
                        reorder_mapping = None
                        if guest_type in ["ch4", "thf"]:
                            mol_atom_names, reorder_mapping = reorder_guest_atoms(mol_atom_names, guest_type)
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

                elif mol_type == "custom":
                    # Custom molecule — write from solute_structure custom attributes
                    res_num += 1
                    res_num_wrapped = res_num % 100000

                    res_name = solute_structure.custom_molecule_moleculetype if solute_structure.custom_molecule_moleculetype else "CST"
                    validate_gro_residue_name(res_name, context="Custom molecule residue name")

                    start = mol.start_idx
                    if solute_structure.custom_molecule_atom_names:
                        mol_atom_names = solute_structure.custom_molecule_atom_names[start:start + mol.count]
                    else:
                        mol_atom_names = [f"C{i}" for i in range(mol.count)]

                    if wrapped_custom_mol_positions is not None:
                        mol_positions = wrapped_custom_mol_positions[start:start + mol.count]
                    else:
                        mol_positions = np.zeros((mol.count, 3))

                    for i, (atom_name, pos) in enumerate(zip(mol_atom_names, mol_positions)):
                        atom_num += 1
                        atom_num_wrapped = atom_num % 100000
                        lines.append(f"{res_num_wrapped:5d}{res_name:<5s}"
                                    f"{atom_name:>5s}{atom_num_wrapped:5d}"
                                    f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")

                elif mol_type == "solute":
                    # Solute molecule (CH4_L or THF_L) — write from solute_structure
                    res_num += 1
                    res_num_wrapped = res_num % 100000

                    start = mol.start_idx
                    count = mol.count

                    # Get atom names and positions from solute_structure
                    mol_atom_names = solute_structure.atom_names[start:start + count]
                    mol_positions = wrapped_solute_positions[start:start + count]

                    # Get residue name from registry
                    solute_type_upper = solute_structure.solute_type.upper()
                    if solute_structure.registry:
                        solute_res_name = solute_structure.registry.get_gromacs_name(f"liquid_{solute_structure.solute_type}")
                    else:
                        solute_res_name = f"{solute_type_upper}_L"

                    validate_gro_residue_name(solute_res_name, context="Solute residue name")

                    for i in range(count):
                        atom_num += 1
                        atom_num_wrapped = atom_num % 100000
                        atom_name = mol_atom_names[i]
                        pos = mol_positions[i]
                        lines.append(f"{res_num_wrapped:5d}{solute_res_name:<5s}"
                                    f"{atom_name:>5s}{atom_num_wrapped:5d}"
                                    f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")

            f.writelines(lines)

            # Box vectors (triclinic format)
            cell = interface.cell
            f.write(f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}"
                    f"{cell[0,1]:10.5f}{cell[0,2]:10.5f}{cell[1,0]:10.5f}"
                    f"{cell[1,2]:10.5f}{cell[2,0]:10.5f}{cell[2,1]:10.5f}\n")
    except (OSError, ValueError) as e:
        logger.error(f"Failed to write GRO file '{filepath}': {e}")
        if Path(filepath).exists():
            Path(filepath).unlink()
        raise

    logger.info(f"Wrote GRO file for solute system: {filepath}")


def write_solute_top_file(
    solute_structure: "SoluteStructure",
    filepath: str,
    custom_guest_info: list[dict] | None = None,
) -> None:
    """Write GROMACS topology file for solute structure.

    Uses SOL molecule type for water and ice, includes solute molecules
    with registry-based moleculetype name (e.g., CH4_L or THF_L).
    Also handles guest molecules (from hydrate cages) and custom molecules
    (propagated from custom tab).

    Writes [molecules] section in order: SOL (ice+water), guest, custom, solute.

    Args:
        solute_structure: SoluteStructure object with solute + interface data
        filepath: Output file path for .top file
        custom_guest_info: Opt-in list of dicts (one per custom guest) for
            metadata-driven custom guest writing (mirror of
            ``write_interface_top_file``'s ``custom_guest_info`` kwarg from
            plans 41-05 / 44.1-09). When supplied, the guest is identified by
            ``mol_type`` (NOT ``detect_guest_type_from_atoms``, which returns
            None for unknown guests -> no [molecules] entry). The custom
            atomtypes are merged via ``_merge_custom_atomtypes`` (oh/ho
            written, hc/c3/h1 deduped), the custom ``.itp`` filename is
            ``#include``d, and the matching
            ``custom_guest_info[i]['residue_name']`` (e.g. ``"MOL_H"``) is
            listed in ``[ molecules ]``. The built-in ch4/thf path
            (custom_guest_info is None or empty) is unchanged. Dict shape:
            ``{'mol_type': str, 'residue_name': str, 'itp_path': Path}``.
            A legacy single ``dict`` is wrapped into a 1-element list with a
            ``DeprecationWarning`` (transition safety).
    """
    interface = solute_structure.interface_structure

    # Transition safety: wrap a legacy single dict into a 1-element list.
    if isinstance(custom_guest_info, dict):
        warnings.warn(
            "write_solute_top_file: custom_guest_info expects a list[dict] "
            "as of plan 44.1-11 (a single dict is deprecated and will be rejected "
            "in a future release). Wrapping the dict into a 1-element list.",
            DeprecationWarning,
            stacklevel=2,
        )
        custom_guest_info = [custom_guest_info]

    # Count molecules by type from interface's molecule_index
    # FALLBACK: When molecule_index is empty (real GenIce2 data), use
    # ice_nmolecules + water_nmolecules from the interface structure
    if interface.molecule_index:
        sol_count = sum(1 for m in interface.molecule_index if m.mol_type in ("water", "ice"))
        guest_count = sum(1 for m in interface.molecule_index if m.mol_type == "guest")
    else:
        sol_count = interface.ice_nmolecules + interface.water_nmolecules
        guest_count = interface.guest_nmolecules if interface.guest_nmolecules > 0 else 0

    # Check for custom molecules (propagated from custom tab)
    has_custom = (solute_structure.custom_molecule_count > 0 and
                  solute_structure.custom_molecule_positions is not None)
    custom_count = solute_structure.custom_molecule_count if has_custom else 0

    # Check for solutes
    has_solutes = solute_structure.n_molecules > 0 and solute_structure.positions is not None
    solute_count = solute_structure.n_molecules if has_solutes else 0

    # Detect guest type from atom names (for correct .itp and residue name)
    guest_type = None
    guest_res_name = "GUE"  # Fallback
    # Custom-guest branch is opt-in (mirror write_interface_top_file:1536-1603,
    # plans 41-05 / 44.1-09). When active, the residue name comes from
    # custom_guest_info (e.g. "MOL_H") and the custom ITP is #include'd by
    # basename; detect_guest_type_from_atoms is skipped (returns None for
    # custom guests). The built-in path (custom_guest_info is None or empty)
    # is byte-identical to before this param was added.
    custom_active = (
        custom_guest_info is not None
        and len(custom_guest_info) > 0
        and guest_count > 0
        and interface.guest_atom_count > 0
        and interface.guest_nmolecules > 0
    )
    custom_by_moltype = (
        {ci["mol_type"]: ci for ci in custom_guest_info}
        if custom_active else {}
    )
    if custom_active:
        # Resolve the custom residue name via the matching molecule_index
        # entry's mol_type (fall back to the first/only custom_guest_info
        # entry — defensive, matches the interface writer's fallback when
        # molecule_index lacks a match or is empty for real GenIce2 data).
        guest_index_entry = next(
            (m for m in interface.molecule_index
             if m.mol_type in custom_by_moltype),
            None,
        )
        if guest_index_entry is not None:
            ci_mol = custom_by_moltype[guest_index_entry.mol_type]
        else:
            ci_mol = next(iter(custom_by_moltype.values()))
        guest_res_name = ci_mol["residue_name"]
    elif guest_count > 0 and interface.guest_atom_count > 0:
        if interface.molecule_index:
            for mol in interface.molecule_index:
                if mol.mol_type == "guest":
                    start = mol.start_idx
                    mol_atom_names = interface.atom_names[start:start + mol.count]
                    guest_type = detect_guest_type_from_atoms(mol_atom_names)
                    if guest_type:
                        guest_res_name = get_hydrate_guest_residue_name(guest_type)
                    break
        else:
            # Fallback: detect guest type from atom names in guest region
            guest_start = interface.ice_atom_count + interface.water_atom_count
            guest_end = guest_start + interface.guest_atom_count
            mol_atom_names = interface.atom_names[guest_start:guest_end]
            guest_type = detect_guest_type_from_atoms(mol_atom_names)
            if guest_type:
                guest_res_name = get_hydrate_guest_residue_name(guest_type)

    # Parse custom molecule moleculetype name from ITP file (Bug 2 fix)
    # GROMACS requires [molecules] name to match ITP [moleculetype] name
    custom_mol_name = "CUSTOM"  # fallback
    if has_custom and solute_structure.custom_itp_path:
        custom_itp_path = Path(solute_structure.custom_itp_path)
        if custom_itp_path.exists():
            try:
                itp_info = parse_itp_file(custom_itp_path)
                custom_mol_name = itp_info.molecule_name
            except (OSError, ValueError):
                if solute_structure.custom_molecule_moleculetype:
                    custom_mol_name = solute_structure.custom_molecule_moleculetype
        elif solute_structure.custom_molecule_moleculetype:
            custom_mol_name = solute_structure.custom_molecule_moleculetype

    # Determine which GAFF2 atomtype sets are needed (Bug 1 fix)
    needs_ch4_atomtypes = (guest_count > 0 and guest_type == "ch4") or \
                          (has_solutes and solute_structure.solute_type.upper() == "CH4")
    needs_thf_atomtypes = (guest_count > 0 and guest_type == "thf") or \
                          (has_solutes and solute_structure.solute_type.upper() == "THF")

    with open(filepath, 'w') as f:
        # Header
        f.write("; Generated by QuickIce\n")
        f.write("; TIP4P-ICE water model")
        if guest_count > 0:
            f.write(" with guest molecules")
        if has_custom:
            f.write(f" and {custom_count} custom molecules")
        if has_solutes:
            f.write(f" and {solute_count} {solute_structure.solute_type.upper()} solutes")
        f.write("\n")
        f.write(f"; Structure: {sol_count} SOL (ice+water)")
        if guest_count > 0:
            f.write(f" + {guest_count} guests")
        if has_custom:
            f.write(f" + {custom_count} custom molecules")
        if has_solutes:
            f.write(f" + {solute_count} {solute_structure.solute_type.upper()} solutes")
        f.write("\n\n")

        # [ defaults ] - force field defaults
        f.write("[ defaults ]\n")
        f.write("; nbfunc        comb-rule       gen-pairs       fudgeLJ fudgeQQ\n")
        f.write("; comb-rule=2 (Lorentz-Berthelot): sigma_ij=(sigma_i+sigma_j)/2, epsilon_ij=sqrt(eps_i*eps_j)\n")
        f.write("; Matches AMBER/GAFF2 convention used by GROMACS-bundled AMBER force fields\n")
        f.write("1               2               yes             0.5     0.8333\n\n")

        # [ atomtypes ] - MUST be before #include directives
        f.write("[ atomtypes ]\n")
        f.write("; name   bond_type  atomic_number  mass     charge  ptype  sigma (nm)    epsilon (kJ/mol)\n")

        # Initialize dedup tracking BEFORE writing any atomtype blocks
        _written_atomtypes: dict[str, tuple] = {}

        # TIP4P-ICE water atom types
        for name, params in WATER_ATOMTYPES.items():
            f.write(_format_atomtype_line(name, params))
            _written_atomtypes[name] = params

        # Combined GAFF2 atom types for guests AND solutes (Bug 1 fix)
        # Solute ITP files have [atomtypes] pre-commented, so parse_itp_atomtypes
        # returns empty. Use centralized GAFF2_ATOMTYPES dict instead.
        # _write_atomtypes_block skips names already in _written_atomtypes,
        # preventing duplicates (e.g., "hc" shared by CH4 and THF).
        if needs_ch4_atomtypes:
            _write_atomtypes_block(f, CH4_ATOMTYPE_NAMES,
                                   "CH4 atom types (GAFF2)", _written_atomtypes)

        if needs_thf_atomtypes:
            _write_atomtypes_block(f, THF_ATOMTYPE_NAMES,
                                   "THF atom types (GAFF2)", _written_atomtypes)

        # Custom GUEST atom types (hydrate cage guests) — merge via the shared
        # _merge_custom_atomtypes (plan 41-01). ci["itp_path"] is the SOURCE ITP
        # (uncommented [atomtypes]); the #include below resolves to the STAGED
        # transformed ITP (same filename, [atomtypes] commented) written to the
        # export dir by _stage_hydrate_guest_itps (plan 44.1-08). Dedup via
        # _written_atomtypes prevents duplicates with water/GAFF2/solute types.
        # Mirrors write_interface_top_file:1590-1603 (plans 41-05 / 44.1-09).
        if custom_active:
            for ci in custom_guest_info:
                if ci.get("itp_path"):
                    _merge_custom_atomtypes(
                        f,
                        Path(ci["itp_path"]),
                        _written_atomtypes,
                        f"custom guest {ci['mol_type']} atom types",
                    )

        # Custom molecule atom types (if present) — with deduplication (Bug 3 fix)
        # Checks parameter compatibility: raises ValueError if a custom atomtype
        # name matches an existing one with different LJ parameters.
        if has_custom and solute_structure.custom_itp_path:
            custom_itp_path = Path(solute_structure.custom_itp_path)
            if custom_itp_path.exists():
                custom_atomtypes = parse_itp_atomtypes(custom_itp_path)
                if custom_atomtypes:
                    f.write(f"; {custom_mol_name} custom molecule atom types\n")
                    for atomtype in custom_atomtypes:
                        if len(atomtype) >= 8:
                            at_name = atomtype[0]
                            _check_custom_atomtype_conflict(
                                at_name, atomtype, _written_atomtypes)
                            if at_name not in _written_atomtypes:
                                f.write(_format_custom_atomtype_line(atomtype))
                                # Record params for future conflict checks
                                try:
                                    _written_atomtypes[at_name] = (
                                        atomtype[1], int(atomtype[2]),
                                        float(atomtype[3]), float(atomtype[4]),
                                        atomtype[5], float(atomtype[6]),
                                        float(atomtype[7]))
                                except (ValueError, IndexError):
                                    pass  # Best-effort recording

        f.write("\n")

        # Include molecule definitions (AFTER atomtypes)
        f.write("; Molecule definitions\n")
        f.write('#include "tip4p-ice.itp"\n')

        # Include guest topology if guests present
        if custom_active:
            # #include each custom guest .itp (basename of ci["itp_path"], e.g.
            # "etoh.itp"). The staged transformed ITP (moleculetype MOL_H,
            # [atomtypes] commented, [atoms] resname MOL_H) is written to
            # path.parent/<basename> by _stage_hydrate_guest_itps (plan 44.1-08).
            # Mirrors write_interface_top_file:1636-1638 (plans 41-05 / 44.1-09).
            for ci in custom_guest_info:
                if ci.get("itp_path"):
                    f.write(f'#include "{Path(ci["itp_path"]).name}"\n')
        elif guest_count > 0 and guest_type:
            f.write(f'#include "{guest_type}_hydrate.itp"\n')

        # Include custom molecule ITP if custom molecules present
        if has_custom and solute_structure.custom_itp_path:
            from pathlib import Path as FilePath
            custom_itp_name = FilePath(solute_structure.custom_itp_path).name
            f.write(f'#include "{custom_itp_name}"\n')

        # Include solute ITP (liquid solutes use _liquid.itp)
        if has_solutes:
            solute_type_lower = solute_structure.solute_type.lower()
            solute_itp_name = f"{solute_type_lower}_liquid.itp"
            f.write(f'#include "{solute_itp_name}"\n')

        f.write("\n")

        # [ system ] section
        f.write("[ system ]\n")
        system_name = f"Ice/water + {solute_count} {solute_structure.solute_type.upper()} solutes"
        if guest_count > 0:
            system_name = f"Ice/water + {guest_count} guests + {solute_count} {solute_structure.solute_type.upper()} solutes"
        if has_custom:
            system_name += f" + {custom_count} custom molecules"
        f.write(f"{system_name}\n\n")

        # [ molecules ] section - ORDER: SOL, guest, custom, solute
        # This matches write_solute_gro_file() output order
        f.write("[ molecules ]\n")
        f.write("; Compound        #mols\n")

        if sol_count > 0:
            f.write(f"SOL              {sol_count}\n")

        if guest_count > 0:
            f.write(f"{guest_res_name:<17s}{guest_count}\n")

        if has_custom:
            # custom_mol_name computed from ITP file above (Bug 2 fix)
            f.write(f"{custom_mol_name:<17s}{custom_count}\n")

        if has_solutes:
            if solute_structure.registry:
                solute_mol_name = solute_structure.registry.get_gromacs_name(f"liquid_{solute_structure.solute_type}")
            else:
                solute_mol_name = f"{solute_structure.solute_type.upper()}_L"
            f.write(f"{solute_mol_name:<17s}{solute_count}\n")

    logger.info(f"Wrote topology file for solute system: {filepath}")
