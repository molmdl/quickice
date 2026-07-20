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


# Re-export shared symbols from _shared.py (Wave 1 extraction).
# _shared.py is an aggregator over 6 domain sub-modules (_constants, _atomtypes,
# _pbc, _itp, _guest, _tip4p) — see plan 48.1-02 for the sub-split rationale (SC-1).
# All 67 caller sites that `from quickice.output.gromacs_writer import X` continue
# to work because these names are bound in this module's namespace.
from quickice.output._shared import (
    # Constants
    TIP4P_ICE_ALPHA, TIP4P_ICE_OW_SIGMA, TIP4P_ICE_OW_EPSILON,
    TIP4P_ICE_HW_CHARGE, TIP4P_ICE_MW_CHARGE,
    TIP4P_ICE_SETTLE_DOH, TIP4P_ICE_SETTLE_DHH,
    GAFF2_ATOMTYPES, ION_ATOMTYPES, WATER_ATOMTYPES, MOLECULE_TO_GROMACS,
    GUEST_ATOM_ORDER,
    CH4_ATOMTYPE_NAMES, THF_ATOMTYPE_NAMES, CO2_ATOMTYPE_NAMES, H2_ATOMTYPE_NAMES,
    # Singleton
    _registry,
    # Helpers
    validate_gro_residue_name,
    _format_atomtype_line, _format_custom_atomtype_line, _write_atomtypes_block,
    _check_custom_atomtype_conflict, _lj_params_match, _merge_custom_atomtypes,
    wrap_positions_into_box, wrap_molecules_into_box,
    reorder_guest_atoms,
    parse_itp_residue_name, parse_itp_atomtypes,
    comment_out_atomtypes_in_itp, _rewrite_atoms_section_resname, transform_guest_itp,
    get_guest_residue_name, get_hydrate_guest_residue_name,
    get_tip4p_itp_path, compute_mw_position,
    _get_molecule_atoms, detect_guest_type_from_atoms,
)

# DRY-extracted GRO formatting helpers (Wave 2a — plan 48.1-03). These pure
# formatters eliminate ~590 lines of near-byte-identical inline code across
# the 6 GRO writers. Plans 48.1-04/05/06 swap inline code for helper calls
# 2 writers at a time. This module (gromacs_writer.py) is the Wave 2b caller
# (write_gro_file + write_interface_gro_file). The other 4 writers are updated
# in 48.1-05 (multi_molecule + ion) and 48.1-06 (custom_molecule + solute).
from quickice.output._gro_format import (
    _write_gro_header, _format_sol_ice_molecule, _format_sol_water_molecule,
    _format_guest_molecule, _format_custom_molecule, _format_solute_molecule,
    _format_na_ion, _format_cl_ion, _write_gro_box_vectors, _wrap_aux_positions,
)


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
    # solute/custom positions may be carried forward from upstream insertion).
    # Uses _wrap_aux_positions (diagonal modulo — the AN-03 fix pattern shared
    # by interface/ion/solute). The hasattr guard stays at the call site
    # because the helper does not abstract attribute presence (older/incomplete
    # InterfaceStructure instances may lack the attribute entirely).
    wrapped_solute_positions = None
    if hasattr(iface, 'solute_positions') and iface.solute_positions is not None and len(iface.solute_positions) > 0:
        wrapped_solute_positions = _wrap_aux_positions(iface.solute_positions, iface.cell)

    wrapped_custom_positions = None
    if hasattr(iface, 'custom_molecule_positions') and iface.custom_molecule_positions is not None and len(iface.custom_molecule_positions) > 0:
        wrapped_custom_positions = _wrap_aux_positions(iface.custom_molecule_positions, iface.cell)

    atom_num_counter = [0]  # 1-element mutable box threaded across molecule boundaries

    try:
        with open(filepath, 'w') as f:
            # Build all GRO lines (header + per-atom) into a single list and
            # flush with one f.writelines() call (I/O-bound; the writelines
            # call dominates execution time vs the O(N) Python formatting).
            lines = []
            _write_gro_header(
                lines,
                f"Ice/water interface ({iface.mode}) exported by QuickIce",
                n_atoms,
            )
            # Note: The lines.append() calls below (inside the helpers) are NOT
            # wrapped in try/except because:
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
            # The caller computes mw_pos (3-atom classic ice via compute_mw_position;
            # 4-atom hydrate pulls the existing MW from the wrapped_positions array)
            # and passes it to _format_sol_ice_molecule — the helper is a pure
            # formatter and does NOT call compute_mw_position internally.
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

                _format_sol_ice_molecule(
                    lines, o_pos, h1_pos, h2_pos, mw_pos,
                    res_num, atom_num_counter,
                )

            # WATER MOLECULES: 4 atoms per molecule (OW, HW1, HW2, MW) → pass through
            # Write WATER BEFORE guests (new order: ice → water → guests).
            # _format_sol_water_molecule takes a 4-position slice (OW, HW1, HW2, MW)
            # and writes the pass-through lines using {atom_name:>5s} — byte-identical
            # to the inline generic loop that was here.
            for mol_idx in range(iface.water_nmolecules):
                base_idx = water_start + mol_idx * 4
                # Wrap residue number at 100000 (GROMACS convention for large systems)
                res_num = (iface.ice_nmolecules + mol_idx + 1) % 100000
                mol_positions = wrapped_positions[base_idx:base_idx + 4]
                _format_sol_water_molecule(lines, mol_positions, res_num, atom_num_counter)

            # GUEST MOLECULES: pass through with native atom types
            # Write guests AFTER water (new order: ice → water → guests)

            if iface.guest_atom_count > 0 and iface.guest_nmolecules > 0:
                guest_atom_names = iface.atom_names[guest_start:]
                # CRITICAL (research §7 risk #3): the interface writer uses
                # `if custom_guest_info:` as the opt-in gate — NOT the
                # `custom_active = (custom_guest_info is not None and len(...) > 0
                # and ...)` pattern used by the other 4 GRO writers. The
                # difference is intentional (interface path is older) and
                # unifying would change byte-output for the empty-list case.
                # The helper takes res_name as a caller-resolved parameter so
                # the gate logic stays in the per-structure writer.
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
                        _format_guest_molecule(
                            lines, mol_atom_names, mol_positions,
                            res_num, guest_res_name, atom_num_counter,
                        )
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

                        _format_guest_molecule(
                            lines, mol_atom_names, mol_positions,
                            res_num, guest_res_name, atom_num_counter,
                        )

                        mol_start = mol_end

            f.writelines(lines)

            # 9-value triclinic box vector line (matches the other 5 GRO writers
            # that use the triclinic format; write_custom_molecule_gro_file is the
            # sole divergent writer using a 3-value diagonal box line).
            _write_gro_box_vectors(f, iface.cell)
    except (OSError, ValueError) as e:
        logger.error(f"Failed to write GRO file '{filepath}': {e}")
        if Path(filepath).exists():
            Path(filepath).unlink()
        raise


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
    
    # NOTE: This writer INTENTIONALLY LACKS the `try/except (OSError, ValueError)`
    # cleanup block that write_gro_file / write_interface_gro_file /
    # write_ion_gro_file / write_custom_molecule_gro_file have. The 4-writer
    # pattern deletes the partial output file on OSError/ValueError; this
    # writer leaves partial output on failure (pre-existing divergence —
    # research §3 row "try/except cleanup"). DO NOT add try/except here
    # "for consistency" — that would be a behavior change (partial files
    # would be cleaned up where they weren't before), violating the
    # byte-identical / behavior-identical contract. Preserved verbatim by
    # plans 48.1-05 (this writer) and 48.1-06 (write_solute_gro_file).
    with open(filepath, 'w') as f:
        # Build all GRO lines (header + per-atom) into a single list and
        # flush with one f.writelines() call (I/O-bound; the writelines
        # call dominates execution time vs the O(N) Python formatting).
        # Header is appended to `lines` via the helper so a single
        # f.writelines flushes header + atoms together (byte-identical
        # to the prior f.write + f.writelines split — just reordered I/O).
        lines = []
        _write_gro_header(lines, title, n_atoms)

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
            
            # Write atoms for this molecule — GENERIC per-atom loop.
            #
            # Research §3 row "SOL ice 3→4 expansion" + plan 48.1-05 Task 1:
            # this writer uses a GENERIC per-atom loop (iterates `mol_atom_names`
            # and emits each atom with a {res_name:<5s}{atom_name:>5s} format),
            # NOT the specialized _format_sol_ice_molecule / _format_sol_water_molecule
            # helpers (which assume 3-atom OHH → 4-atom OW/HW1/HW2/MW expansion
            # or a 4-atom pass-through chunk). The multi-molecule writer's ice
            # molecules are already 4-atom (OW, HW1, HW2, MW) because the input
            # HydrateStructure has them pre-computed, and the res_name is
            # resolved per-molecule via the registry/custom_guest_info/fallback
            # chain (NOT hardcoded "SOL"). Forcing the generic loop into 1-atom
            # _format_guest_molecule(lines, [name], [pos], res_num, res_name,
            # atom_num_counter) calls would HURT readability (the helper expects
            # a molecule's atom list — passing 1-atom chunks is awkward). The
            # inline f-string is byte-identical to _format_guest_molecule's
            # f-string (verified by _gro_format helper unit tests); the DRY win
            # is the format string itself, which is already captured in the
            # helper for the OTHER 4 writers that have specialized blocks. The
            # generic loop stays inline — research §3 row "generic (uses
            # atom_names)" documents this as the intentional divergence.
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
        
        # 9-value triclinic box vector line (matches the other 5 GRO writers
        # that use the triclinic format; write_custom_molecule_gro_file is the
        # sole divergent writer using a 3-value diagonal box line — see
        # _gro_format._write_gro_box_vectors docstring).
        _write_gro_box_vectors(f, cell)


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
            ordered_mols.append(("custom", MoleculeIndex(
                start_idx=start,
                count=atoms_per_custom,
                mol_type='custom'
            )))
    # Pass 4: solute molecules (if present)
    # Note: solutes are stored separately, not in molecule_index
    has_solutes = ion_structure.solute_n_molecules > 0 and ion_structure.solute_positions is not None
    if has_solutes:
        for start, end in ion_structure.solute_molecule_indices:
            # Create a temporary MoleculeIndex-like object for solutes
            ordered_mols.append(("solute", MoleculeIndex(
                start_idx=start,
                count=end - start,
                mol_type='solute'
            )))
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
            ordered_mols.append(("sol", MoleculeIndex(
                start_idx=base_idx,
                count=atoms_per_ice_mol,
                mol_type='ice'
            )))
        for mol_idx in range(interface.water_nmolecules):
            base_idx = interface.ice_atom_count + mol_idx * 4
            ordered_mols.append(("sol", MoleculeIndex(
                start_idx=base_idx,
                count=4,
                mol_type='water'
            )))

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
                ordered_mols.append(("guest", MoleculeIndex(
                    start_idx=start,
                    count=atoms_per_guest,
                    mol_type='guest'
                )))

    # Pass 3: custom molecules (if present, propagated from custom tab)
    has_custom = (solute_structure.custom_molecule_count > 0 and
                  solute_structure.custom_molecule_positions is not None)
    if has_custom:
        atoms_per_custom = 0
        if solute_structure.custom_molecule_atom_count > 0 and solute_structure.custom_molecule_count > 0:
            atoms_per_custom = solute_structure.custom_molecule_atom_count // solute_structure.custom_molecule_count

        for i in range(solute_structure.custom_molecule_count):
            start = i * atoms_per_custom
            ordered_mols.append(("custom", MoleculeIndex(
                start_idx=start,
                count=atoms_per_custom,
                mol_type='custom'
            )))

    # Pass 4: solute molecules (from solute_structure.positions)
    has_solutes = solute_structure.n_molecules > 0 and solute_structure.positions is not None
    if has_solutes:
        for start, end in solute_structure.molecule_indices:
            ordered_mols.append(("solute", MoleculeIndex(
                start_idx=start,
                count=end - start,
                mol_type='solute'
            )))

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
