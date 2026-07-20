"""GROMACS writers for InterfaceStructure export.

Split from quickice/output/gromacs_writer.py in Phase 48.1 (FRAG-03).
These writers handle the interface export path: ice + water + optional
guest molecules (built-in CH4/THF/CO2/H2 or custom guest via custom_guest_info).

CRITICAL divergence (research §3 'custom_active opt-in gate'):
    write_interface_gro_file uses `if custom_guest_info:` for the custom-guest
    gate, while the other 4 GRO writers (multi_molecule, ion, custom, solute)
    use `custom_active = (custom_guest_info is not None and len(...) > 0 and ...)`.
    This difference is INTENTIONAL (interface path is older). DO NOT unify.
"""

import logging
import warnings
from pathlib import Path

import numpy as np

from quickice.structure_generation.types import InterfaceStructure
from quickice.utils.molecule_utils import count_guest_atoms

from quickice.output._shared import (
    validate_gro_residue_name,
    wrap_molecules_into_box,
    wrap_positions_into_box,
    compute_mw_position,
    reorder_guest_atoms,
    get_hydrate_guest_residue_name,
    detect_guest_type_from_atoms,
    _write_top_defaults,
    _write_atomtypes_block,
    _format_atomtype_line,
    _merge_custom_atomtypes,
    WATER_ATOMTYPES,
    CH4_ATOMTYPE_NAMES, THF_ATOMTYPE_NAMES, CO2_ATOMTYPE_NAMES, H2_ATOMTYPE_NAMES,
)
from quickice.output._gro_format import (
    _write_gro_header,
    _format_sol_ice_molecule,
    _format_sol_water_molecule,
    _format_guest_molecule,
    _write_gro_box_vectors,
    _wrap_aux_positions,
)

logger = logging.getLogger(__name__)


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
        
        # [ defaults ] - force field defaults (Format A — write_interface_top_file
        # uses the default helper invocation, same as write_top_file. See
        # _shared._write_top_defaults docstring for the 3-variant rationale.)
        _write_top_defaults(f)
        
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
