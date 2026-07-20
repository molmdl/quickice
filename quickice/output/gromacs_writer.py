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
    # TOP [defaults] block helper (Wave 2e — plan 48.1-07). All 6 TOP writers
    # call this instead of inline f.write(...) for the [defaults] block. The
    # helper is parameterized (include_amber_header, compact_nbfunc_comment)
    # to preserve byte-identity across the 3 distinct format variants used by
    # the 6 TOP writers — see _shared._write_top_defaults docstring + the
    # 48.1-07 SUMMARY Deviations section for the research §3 correction.
    _write_top_defaults,
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


# Per-structure writer re-exports (Wave 3-8 splits).
# All 67 caller sites that `from quickice.output.gromacs_writer import write_*`
# continue to work because these names are bound in this module's namespace.
from quickice.output.ice_writer import write_gro_file, write_top_file
from quickice.output.interface_writer import write_interface_gro_file, write_interface_top_file
from quickice.output.multi_molecule_writer import write_multi_molecule_gro_file, write_multi_molecule_top_file
from quickice.output.ion_writer import write_ion_gro_file, write_ion_top_file


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
    
    atom_num_counter = [0]  # 1-element mutable box threaded across molecule boundaries
    res_num = 0
    lines = []
    # Note: The lines.append() calls below (inside the helpers) are NOT
    # wrapped in try/except because:
    # 1. String formatting of float values cannot fail unless the input array is malformed
    #    (which would be a programming bug, not a runtime error)
    # 2. numpy array indexing (positions[i]) would raise IndexError on malformed data,
    #    which is a programming error that should propagate rather than be silently caught
    # 3. Any actual I/O error occurs during f.writelines() inside the with-open block,
    #    which IS protected by try/except

    # DIVERGENT HEADER (research §3 row 'Atom count write' + §10 pitfall +
    # ORCHESTRATOR CORRECTION from 48.1-03 finding): this writer uses
    # f"{total_atoms}\n" (NO :5d padding) for the atom-count line — divergent
    # from the other 5 GRO writers which use f"{n_atoms:5d}\n". DO NOT call
    # _write_gro_header here (it would impose the :5d format and break
    # byte-equivalence). Keep the inline header write byte-identically.
    custom_count = custom_structure.custom_molecule_count
    lines.append(f"Custom molecule system: {custom_count} {custom_structure.moleculetype_name} molecules\n")

    # Atom count line — DIVERGENT (NO :5d)
    lines.append(f"{total_atoms}\n")

    # Write atoms — helpers mutate atom_num_counter in place so the running
    # atom_num carries across molecule-type boundaries (SOL ice → SOL water →
    # guest → custom). res_num stays a plain int (caller wraps via % 100000
    # BEFORE the helper call — helpers take already-wrapped res_num).
    for mol_type, mol in ordered_mols:
        if mol_type == "sol":
            # SOL (ice or water)
            res_num += 1
            res_num_wrapped = res_num % 100000

            if mol.mol_type == "ice":
                # Ice: 3 input atoms (O, H, H) -> 4 output atoms (OW, HW1, HW2, MW)
                # or: 4 input atoms (OW, HW1, HW2, MW) -> 4 output atoms.
                # The caller computes mw_pos (3-atom classic ice via
                # compute_mw_position; 4-atom hydrate pulls the existing MW
                # from the wrapped_positions array) and passes it to
                # _format_sol_ice_molecule — the helper is a pure formatter
                # and does NOT call compute_mw_position internally.
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

                _format_sol_ice_molecule(
                    lines, o_pos, h1_pos, h2_pos, mw_pos,
                    res_num_wrapped, atom_num_counter,
                )

            else:  # water
                # Water: 4 atoms (OW, HW1, HW2, MW) — pass through (no MW recompute).
                # _format_sol_water_molecule takes the 4-position slice and writes
                # the pass-through lines using {name:>5s} — byte-identical to the
                # inline explicit "   OW"/"  HW1"/"  HW2"/"   MW" literals that
                # were here before (verified by _gro_format helper unit tests).
                mol_positions = wrapped_positions[mol.start_idx:mol.start_idx + mol.count]
                _format_sol_water_molecule(
                    lines, mol_positions, res_num_wrapped, atom_num_counter,
                )

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

            _format_guest_molecule(
                lines, mol_atom_names, mol_positions,
                res_num_wrapped, guest_res_name, atom_num_counter,
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

            _format_custom_molecule(
                lines, mol_atom_names, mol_positions,
                res_num_wrapped, res_name, atom_num_counter,
            )

    # DIVERGENT BOX VECTORS (ORCHESTRATOR CORRECTION from 48.1-03 finding +
    # research §3 row 'Box vector write' correction): this writer uses a
    # 3-value DIAGONAL box format (f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}\n"),
    # NOT the 9-value triclinic format used by the other 5 GRO writers.
    # DO NOT call _write_gro_box_vectors here (it would emit 9 values and
    # break byte-equivalence — the custom path's box line is 3 values).
    # This is the SOLE divergent writer; the pre-existing divergence is
    # documented in the _gro_format._write_gro_box_vectors docstring. Kept
    # inline byte-identically to the pre-refactor source (gromacs_writer.py
    # line 2148 in the pre-48.1-06 source).
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
        
        # [ defaults ] - force field defaults (Format C — write_custom_molecule_top_file
        # uses NO '; Defaults compatible' header + multi-space aligned
        # '; nbfunc' comment. Same variant as write_ion_top_file and
        # write_solute_top_file. See _shared._write_top_defaults docstring.)
        _write_top_defaults(f, include_amber_header=False, compact_nbfunc_comment=False)
        
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

    # Wrap custom molecule positions into PBC box (same as AN-03 fix in
    # write_ion_gro_file). Uses _wrap_aux_positions (diagonal modulo — the
    # AN-03 fix pattern shared by interface/ion/solute writers, established
    # in 48.1-04 + 48.1-05). The `is not None and len(...) > 0` guards stay
    # at the call site because the helper does NOT abstract attribute
    # presence (the helper's own None/empty guard is a defensive backstop;
    # the caller guards avoid constructing the diag modulo on a None/empty
    # array in the first place — same pattern as the interface + ion writers).
    if solute_structure.custom_molecule_positions is not None and len(solute_structure.custom_molecule_positions) > 0:
        wrapped_custom_mol_positions = _wrap_aux_positions(
            solute_structure.custom_molecule_positions, solute_structure.cell,
        )
    else:
        wrapped_custom_mol_positions = solute_structure.custom_molecule_positions

    # Wrap solute positions into PBC box (same as AN-03 fix in write_ion_gro_file).
    # Solute positions are a SEPARATE array from interface.positions, so
    # wrap_molecules_into_box does NOT cover them. Simple modulo wrapping
    # is sufficient — solute molecules (CH4, THF) are single small molecules
    # that don't span PBC boundaries.
    if solute_structure.positions is not None and len(solute_structure.positions) > 0:
        wrapped_solute_positions = _wrap_aux_positions(
            solute_structure.positions, solute_structure.cell,
        )
    else:
        wrapped_solute_positions = solute_structure.positions

    atom_num_counter = [0]  # 1-element mutable box threaded across molecule boundaries
    res_num = 0
    lines = []
    # Note: The lines.append() calls below (inside the helpers) are NOT
    # wrapped in try/except because:
    # 1. String formatting of float values cannot fail unless the input array is malformed
    #    (which would be a programming bug, not a runtime error)
    # 2. numpy array indexing (positions[i]) would raise IndexError on malformed data,
    #    which is a programming error that should propagate rather than be silently caught
    # 3. Any actual I/O error occurs during f.writelines() inside the with-open block,
    #    which IS protected by try/except

    try:
        with open(filepath, 'w') as f:
            # Build all GRO lines (header + per-atom) into a single list and
            # flush with one f.writelines() call (I/O-bound; the writelines
            # call dominates execution time vs the O(N) Python formatting).
            # Dynamic title construction (per-structure: ice/water interface
            # + optional custom + optional solutes + 'exported by QuickIce')
            # kept inline — only the header LINE WRITE is delegated to
            # _write_gro_header (the helper is a pure formatter that appends
            # title + atom count lines to `lines`). The solute writer DOES
            # use :5d for the atom count (line 2572 in pre-refactor source),
            # so _write_gro_header is safe here (UNLIKE write_custom_molecule_gro_file
            # which uses the divergent f"{total_atoms}\n" no-:5d format).
            title_parts = ["Ice/water interface"]
            if has_custom:
                title_parts.append(f"{solute_structure.custom_molecule_count} custom molecules")
            if has_solutes:
                title_parts.append(f"{solute_structure.n_molecules} {solute_structure.solute_type.upper()} solutes")
            title_parts.append("exported by QuickIce")
            title = " + ".join(title_parts)
            _write_gro_header(lines, title, total_atoms)

            for mol_type, mol in ordered_mols:
                if mol_type == "sol":
                    # SOL molecule (ice or water)
                    res_num += 1
                    res_num_wrapped = res_num % 100000
                    start = mol.start_idx

                    if mol.mol_type == "ice":
                        # Ice: 3 input atoms (O, H, H) -> 4 output atoms (OW, HW1, HW2, MW)
                        # or: 4 input atoms (OW, HW1, HW2, MW) -> 4 output atoms.
                        # The caller computes mw_pos (3-atom classic ice via
                        # compute_mw_position; 4-atom hydrate pulls the existing MW
                        # from the wrapped_positions array) and passes it to
                        # _format_sol_ice_molecule — the helper is a pure formatter
                        # and does NOT call compute_mw_position internally.
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

                        _format_sol_ice_molecule(
                            lines, o_pos, h1_pos, h2_pos, mw_pos,
                            res_num_wrapped, atom_num_counter,
                        )

                    else:  # water
                        # Water: 4 atoms (OW, HW1, HW2, MW) — pass through (no MW recompute).
                        # _format_sol_water_molecule takes the 4-position slice and writes
                        # the pass-through lines using {name:>5s} — byte-identical to the
                        # inline explicit "   OW"/"  HW1"/"  HW2"/"   MW" literals that
                        # were here before (verified by _gro_format helper unit tests).
                        mol_positions = wrapped_positions[start:start + mol.count]
                        _format_sol_water_molecule(
                            lines, mol_positions, res_num_wrapped, atom_num_counter,
                        )

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

                    _format_guest_molecule(
                        lines, mol_atom_names, mol_positions,
                        res_num_wrapped, guest_res_name, atom_num_counter,
                    )

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

                    _format_custom_molecule(
                        lines, mol_atom_names, mol_positions,
                        res_num_wrapped, res_name, atom_num_counter,
                    )

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

                    _format_solute_molecule(
                        lines, mol_atom_names, mol_positions,
                        res_num_wrapped, solute_res_name, atom_num_counter,
                    )

            f.writelines(lines)

            # 9-value triclinic box vector line (matches the other 5 GRO writers
            # that use the triclinic format; write_custom_molecule_gro_file is the
            # sole divergent writer using a 3-value diagonal box line — see
            # _gro_format._write_gro_box_vectors docstring). The solute writer
            # DOES use the 9-value triclinic format (verified by direct source
            # read of pre-refactor lines 2817-2819), so calling the helper is
            # safe here (UNLIKE write_custom_molecule_gro_file).
            _write_gro_box_vectors(f, interface.cell)
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

        # [ defaults ] - force field defaults (Format C — write_solute_top_file
        # uses NO '; Defaults compatible' header + multi-space aligned
        # '; nbfunc' comment. Same variant as write_ion_top_file and
        # write_custom_molecule_top_file. See _shared._write_top_defaults docstring.)
        _write_top_defaults(f, include_amber_header=False, compact_nbfunc_comment=False)

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
