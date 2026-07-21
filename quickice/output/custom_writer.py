"""GROMACS writers for CustomMoleculeStructure export.

Split from quickice/output/gromacs_writer.py in Phase 48.1 (FRAG-03).
These writers handle the custom molecule export path: ice + water +
optional guests + custom molecules (user-provided .gro/.itp).

CRITICAL divergence (research §3 "Atom count write" + §10 pitfall):
    write_custom_molecule_gro_file uses f"{total_atoms}\n" (NO :5d) for
    the atom-count header line — DIVERGENT from the other 5 GRO writers
    which use f"{n_atoms:5d}\n". DO NOT use _write_gro_header (which uses
    :5d). Keep the inline header write byte-identically.

CRITICAL divergence (48.1-03 finding + 48.1-06 ORCHESTRATOR CORRECTION):
    write_custom_molecule_gro_file uses a DIVERGENT 3-value diagonal box
    format (NOT the 9-value triclinic format used by the other 5 writers).
    DO NOT call _write_gro_box_vectors — keep the inline box write
    byte-identically. The format is:
        f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}\n"
    (3 values, NOT 9). This is the SOLE divergent writer — see
    _gro_format._write_gro_box_vectors docstring.

Other divergences preserved byte-verbatim from gromacs_writer.py:
    1. ``custom_active = (custom_guest_info is not None and len(...) > 0 and ...)``
       gate (the 4-writer pattern — NOT the interface's
       ``if custom_guest_info:`` gate NOR the multi_molecule's
       ``custom_by_moltype`` dict pattern). Both custom writers use
       ``custom_active`` + build ``custom_by_moltype`` from it.
    2. ``try/except (OSError, ValueError)`` cleanup block in
       write_custom_molecule_gro_file (research §3 row "try/except cleanup"
       — the custom writer HAS it, unlike write_multi_molecule_gro_file
       and write_solute_gro_file which lack it).
    3. ``DeprecationWarning`` for legacy single-dict ``custom_guest_info``
       in BOTH writers (transition safety from plan 42-03).
    4. ``_write_top_defaults(f, include_amber_header=False,
       compact_nbfunc_comment=False)`` Format C invocation (comb-rule=2 in
       helper, not inline — same variant as write_ion_top_file +
       write_solute_top_file).
"""

import logging
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

from quickice.structure_generation.itp_parser import parse_itp_file

from quickice.output._shared import (
    validate_gro_residue_name,
    wrap_molecules_into_box,
    compute_mw_position,
    reorder_guest_atoms,
    detect_guest_type_from_atoms,
    get_hydrate_guest_residue_name,
    _write_top_defaults,
    _write_atomtypes_block,
    _merge_custom_atomtypes,
    _check_custom_atomtype_conflict,
    _format_atomtype_line,
    _format_custom_atomtype_line,
    parse_itp_atomtypes,
    WATER_ATOMTYPES,
    CH4_ATOMTYPE_NAMES,
    THF_ATOMTYPE_NAMES,
)
from quickice.output._gro_format import (
    _format_sol_ice_molecule,
    _format_sol_water_molecule,
    _format_guest_molecule,
    _format_custom_molecule,
)

if TYPE_CHECKING:
    from quickice.structure_generation.types import CustomMoleculeStructure

logger = logging.getLogger(__name__)


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
