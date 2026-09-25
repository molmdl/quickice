"""GROMACS writers for IonStructure export.

Split from quickice/output/gromacs_writer.py in Phase 48.1 (FRAG-03).
These writers handle the ion export path: ice + water + optional guests +
optional custom molecules + optional solutes + NA ions + CL ions.

CRITICAL (research §7 MoleculeIndex watchpoint + Group 8 fix):
    write_ion_gro_file uses MoleculeIndex synthetic entries at 2 sites
    (custom molecule entry at line ~172, solute entry at line ~183) for the
    wrap step. The ``from quickice.structure_generation.types import MoleculeIndex``
    import is REQUIRED here — do NOT replace with ad-hoc type() objects
    (Group 8 cleanup replaced all 7 ad-hoc sites with the MoleculeIndex dataclass).
    Regression test: tests/test_scancode_bugs_tech_debt.py.

CRITICAL divergences preserved byte-verbatim from gromacs_writer.py:
    1. ``custom_active = (custom_guest_info is not None and len(...) > 0 and ...)``
       gate (the 4-writer pattern — NOT the interface's ``if custom_guest_info:``
       gate NOR the multi_molecule's ``custom_by_moltype`` dict pattern). The
       ion writers use ``custom_active`` + build ``custom_by_moltype`` from it.
    2. ``try/except (OSError, ValueError)`` cleanup block in write_ion_gro_file
       (research §3 row "try/except cleanup" — the ion writer HAS it, unlike
       write_multi_molecule_gro_file and write_solute_gro_file which lack it).
    3. ``DeprecationWarning`` for legacy single-dict ``custom_guest_info`` in
       BOTH writers (transition safety from plan 42-03).
    4. ``_write_top_defaults(f, include_amber_header=False, compact_nbfunc_comment=False)``
       Format C invocation (comb-rule=2 in helper, not inline — same variant as
       write_custom_molecule_top_file + write_solute_top_file).
    5. The ONLY writer using ``_format_na_ion`` + ``_format_cl_ion`` (unique
       to the ion path — the other 5 GRO writers have no ion atoms).
"""

import logging
import warnings
from pathlib import Path

import numpy as np

from quickice.structure_generation.types import IonStructure, MoleculeIndex
from quickice.structure_generation.itp_parser import parse_itp_file

from quickice.output._shared import (
    validate_gro_residue_name,
    wrap_molecules_into_box,
    compute_mw_position,
    reorder_guest_atoms,
    detect_guest_type_from_atoms,
    detect_guest_type_runs,
    get_hydrate_guest_residue_name,
    _write_top_defaults,
    _write_atomtypes_block,
    _merge_custom_atomtypes,
    ION_ATOMTYPES,
    WATER_ATOMTYPES,
    CH4_ATOMTYPE_NAMES,
    THF_ATOMTYPE_NAMES,
    _format_atomtype_line,
    _format_custom_atomtype_line,
    _check_custom_atomtype_conflict,
    parse_itp_atomtypes,
)
from quickice.output._gro_format import (
    _write_gro_header,
    _format_sol_ice_molecule,
    _format_sol_water_molecule,
    _format_guest_molecule,
    _format_custom_molecule,
    _format_solute_molecule,
    _format_na_ion,
    _format_cl_ion,
    _write_gro_box_vectors,
    _wrap_aux_positions,
)

logger = logging.getLogger(__name__)


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
    # Issue 3 (molh-atom-drop-origin): the ion inserter now labels cage guests
    # by their specific mol_type (ch4/thf/etoh_mix/...) instead of the generic
    # "guest" (iter_guest_molecules descriptor matching — RELIABLE for ch4 vs
    # custom ethanol, unlike detect_guest_type_from_atoms which misidentifies
    # ethanol as ch4). Collect ALL cage-guest mol_types here: the generic
    # "guest" (fallback path), the built-in ch4/thf/co2/h2, AND the custom
    # guest mol_types (when the caller opted in via custom_guest_info). The
    # built-in path (custom_guest_info is None -> custom_active is False) only
    # collects literal "guest" + built-in entries, preserving byte-identical
    # behavior for ch4/thf. Mirrors write_solute_gro_file's
    # `m.mol_type in custom_by_moltype` lookup (plan 41-04).
    _BUILTIN_CAGE_GUEST_MOL_TYPES = ("guest", "ch4", "thf", "co2", "h2")
    for mol in ion_structure.molecule_index:
        if mol.mol_type in _BUILTIN_CAGE_GUEST_MOL_TYPES:
            ordered_mols.append(("guest", mol))
        elif custom_active and mol.mol_type in custom_by_moltype:
            # Custom guest mol_type (e.g. "etoh_mix") — collect when the
            # caller opted in via custom_guest_info.
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

    # PBC-wrap solute and custom molecule positions via diagonal modulo (AN-03 fix).
    # Uses _wrap_aux_positions (the shared diagonal-modulo helper from _gro_format,
    # also used by write_interface_gro_file — plan 48.1-04). Solute/custom-molecule
    # positions are single small molecules that don't span PBC boundaries, so the
    # simple modulo is sufficient. The `is not None and len(...) > 0` guards stay
    # at the call site because the helper does NOT abstract attribute presence
    # (older/incomplete IonStructure instances may lack the attribute entirely).
    wrapped_solute_positions = (
        _wrap_aux_positions(ion_structure.solute_positions, ion_structure.cell)
        if ion_structure.solute_positions is not None
        and len(ion_structure.solute_positions) > 0
        else ion_structure.solute_positions
    )
    wrapped_custom_positions = (
        _wrap_aux_positions(ion_structure.custom_molecule_positions, ion_structure.cell)
        if ion_structure.custom_molecule_positions is not None
        and len(ion_structure.custom_molecule_positions) > 0
        else ion_structure.custom_molecule_positions
    )

    # atom_num_counter is a 1-element mutable box threaded across helper
    # boundaries so the running atom_num carries across molecule-type
    # transitions (SOL → guest → custom → solute → NA → CL). res_num stays
    # a plain int (the caller wraps it via `% 100000` BEFORE the helper call —
    # the helper takes the already-wrapped res_num and formats it with :5d).
    atom_num_counter = [0]
    res_num = 0

    try:
        with open(filepath, 'w') as f:
            # Build the dynamic title (per-structure: NA/CL counts + optional
            # custom/solute descriptors). The title construction stays inline
            # because it's per-structure; only the header LINE WRITE is
            # delegated to _write_gro_header (the helper is a pure formatter
            # that appends the title line + atom count line to `lines`).
            na_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "na")
            cl_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "cl")
            title_parts = [f"Ice/water + ions ({na_count} Na+, {cl_count} Cl-)"]
            if has_custom:
                title_parts.append(f"{ion_structure.custom_molecule_count} custom molecules")
            if has_solutes:
                title_parts.append(f"{ion_structure.solute_n_molecules} {ion_structure.solute_type.upper()} solutes")
            title_parts.append("exported by QuickIce")
            title = " + ".join(title_parts)

            # Build all GRO lines (header + per-atom) into a single list and
            # flush with one f.writelines() call (I/O-bound; the writelines
            # call dominates execution time vs the O(N) Python formatting).
            # Header is appended to `lines` via the helper so a single
            # f.writelines flushes header + atoms together (byte-identical
            # to the prior f.write + f.writelines split — just reordered I/O).
            lines = []
            _write_gro_header(lines, title, total_atoms)
            # Note: The lines.append() calls below (inside the helpers) are NOT
            # wrapped in try/except because:
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

                        # _format_sol_ice_molecule appends 4 GRO atom lines
                        # (OW, HW1, HW2, MW) and increments atom_num_counter by 4.
                        # Byte-identical to the inline 4-lines.append block that
                        # was here (verified by _gro_format helper unit tests).
                        _format_sol_ice_molecule(
                            lines, o_pos, h1_pos, h2_pos, mw_pos,
                            res_num_wrapped, atom_num_counter,
                        )

                    else:  # water
                        # Water: 4 atoms (OW, HW1, HW2, MW)
                        # Use existing MW from wrapped_positions (already correctly placed)
                        mol_positions = wrapped_positions[start:start + 4]
                        # _format_sol_water_molecule appends 4 GRO atom lines
                        # (OW, HW1, HW2, MW) via the generic {name:>5s} loop and
                        # increments atom_num_counter by 4. Byte-identical to
                        # the inline 4-lines.append block (the helper's
                        # "OW".rjust(5)=="   OW" etc. matches the explicit
                        # "   OW"/"  HW1"/"  HW2"/"   MW" literals).
                        _format_sol_water_molecule(
                            lines, mol_positions, res_num_wrapped, atom_num_counter,
                        )

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
                        #
                        # Issue 3 (molh-atom-drop-origin): MIXED built-in+custom
                        # cage assignment (CH4 built-in small + ethanol custom
                        # large). The ion inserter now labels cage guests by their
                        # specific mol_type (ch4/etoh_mix). Resolve the residue
                        # name PER-MOLECULE so built-in ch4 -> CH4_H (with
                        # reorder_guest_atoms to the ITP canonical order) and
                        # custom ethanol -> MOL_H (NO reorder — custom atoms are
                        # already in ITP order). The old code fell back to the
                        # first custom_guest_info entry for ANY mol_type not in
                        # custom_by_moltype (including the generic "guest" and
                        # built-in ch4), so ALL cage guests got MOL_H and the
                        # 864 CH4 (5-atom) cage guests were labeled MOL_H while
                        # the .top #included etoh.itp (9 atoms/MOL_H) -> grompp
                        # atom-count mismatch. detect_guest_type_from_atoms
                        # CANNOT distinguish CH4 from ethanol (both have C+H;
                        # _get_molecule_atoms grabs only the first 5 atoms and
                        # misses the O -> returns "ch4" for ethanol), so the
                        # per-molecule mol_type from iter_guest_molecules
                        # (descriptor atom_labels matching — RELIABLE) is the
                        # only correct discriminator.
                        ci = custom_by_moltype.get(mol.mol_type)
                        if mol.mol_type in ("ch4", "thf", "co2", "h2"):
                            # Built-in cage guest in a mixed built-in+custom
                            # hydrate — use the built-in hydrate residue name
                            # (CH4_H/THF_H/...) + reorder to ITP canonical order
                            # (GenIce2 emits ch4 H-first; ITP defines C-first).
                            # This is the SAME logic as the built-in path below
                            # (detect_guest_type_from_atoms + reorder), but keyed
                            # on the per-molecule mol_type (reliable) instead of
                            # atom-name detection (which misidentifies ethanol).
                            guest_type = mol.mol_type
                            guest_res_name = get_hydrate_guest_residue_name(guest_type)
                            validate_gro_residue_name(
                                guest_res_name,
                                context="Ion built-in guest (mixed) GRO residue name",
                            )
                            reorder_mapping = None
                            if guest_type in ["ch4", "thf"]:
                                mol_atom_names, reorder_mapping = reorder_guest_atoms(
                                    mol_atom_names, guest_type
                                )
                                if reorder_mapping is not None:
                                    mol_positions = [mol_positions[i] for i in reorder_mapping]
                        elif ci is not None:
                            # Custom cage guest — use the caller-supplied
                            # residue name (e.g. "MOL_H"). NO reorder — custom
                            # guest atoms are already in ITP canonical order
                            # (the interface/solute/custom-molecule writers'
                            # custom branches also skip reorder_guest_atoms).
                            guest_res_name = ci["residue_name"]
                            validate_gro_residue_name(
                                guest_res_name,
                                context="Ion custom guest GRO residue name",
                            )
                        else:
                            # Fallback: literal "guest" mol_type (ion inserter
                            # fallback path, descriptors absent) or an unknown
                            # mol_type not in custom_by_moltype. Fall back to
                            # the first/only custom_guest_info entry — preserves
                            # the single-custom-guest byte-identical behavior
                            # (the ion inserter fallback labels all cage guests
                            # "guest" when descriptors are absent, and the
                            # single-custom path has only custom guests).
                            ci_fallback = next(iter(custom_by_moltype.values()))
                            guest_res_name = ci_fallback["residue_name"]
                            validate_gro_residue_name(
                                guest_res_name,
                                context="Ion custom guest (fallback) GRO residue name",
                            )
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

                    # _format_guest_molecule iterates mol_atom_names and appends
                    # one GRO atom line per atom (f-string byte-identical to the
                    # inline loop that was here). Increments atom_num_counter by
                    # len(mol_atom_names) (== mol.count for well-formed structures).
                    _format_guest_molecule(
                        lines, mol_atom_names, mol_positions,
                        res_num_wrapped, guest_res_name, atom_num_counter,
                    )

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

                    # _format_custom_molecule is a pure formatter (same f-string
                    # as _format_guest_molecule; kept separate for call-site
                    # readability). Byte-identical to the inline zip-loop that
                    # was here. Increments atom_num_counter by len(mol_atom_names).
                    _format_custom_molecule(
                        lines, mol_atom_names, mol_positions,
                        res_num_wrapped, res_name, atom_num_counter,
                    )

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

                    # _format_solute_molecule is a pure formatter (same f-string
                    # as _format_guest_molecule / _format_custom_molecule; kept
                    # separate for call-site readability). Byte-identical to the
                    # inline range-loop that was here. Increments atom_num_counter
                    # by count.
                    _format_solute_molecule(
                        lines, mol_atom_names, mol_positions,
                        res_num_wrapped, solute_res_name, atom_num_counter,
                    )

                elif mol_type == "na":
                    # NA ion — _format_na_ion appends 1 GRO atom line and
                    # increments atom_num_counter by 1. The helper's f-string
                    # ("NA   " + "   NA" + positions) was adjusted in plan
                    # 48.1-03 to match the source's two-fragment form byte-for-byte.
                    res_num += 1
                    res_num_wrapped = res_num % 100000
                    pos = wrapped_positions[mol.start_idx]
                    _format_na_ion(lines, pos, res_num_wrapped, atom_num_counter)

                elif mol_type == "cl":
                    # CL ion — _format_cl_ion appends 1 GRO atom line and
                    # increments atom_num_counter by 1. Same two-fragment form
                    # as _format_na_ion ("CL   " + "   CL" + positions).
                    res_num += 1
                    res_num_wrapped = res_num % 100000
                    pos = wrapped_positions[mol.start_idx]
                    _format_cl_ion(lines, pos, res_num_wrapped, atom_num_counter)

            f.writelines(lines)

            # 9-value triclinic box vector line (matches the other 5 GRO writers
            # that use the triclinic format; write_custom_molecule_gro_file is the
            # sole divergent writer using a 3-value diagonal box line — see
            # _gro_format._write_gro_box_vectors docstring).
            _write_gro_box_vectors(f, ion_structure.cell)
    except (OSError, ValueError) as e:
        logger.error(f"Failed to write GRO file '{filepath}': {e}")
        if Path(filepath).exists():
            Path(filepath).unlink()
        raise


def write_ion_top_file(
    ion_structure: IonStructure,
    filepath: str,
    custom_guest_info: list[dict] | None = None,
    custom_molecule_itp_name: str | None = None,
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
    # Issue 3 (molh-atom-drop-origin): the ion inserter now labels cage guests
    # by their specific mol_type (ch4/thf/etoh_mix/...) instead of the generic
    # "guest". Count ALL cage-guest mol_types here: the generic "guest" (ion
    # inserter fallback path), the built-in ch4/thf/co2/h2, AND custom guest
    # mol_types (resolved against custom_by_moltype below once custom_active
    # is known). The old `mol_type == "guest"` filter would miss the ch4/thf
    # entries the ion inserter now produces, undercounting cage guests and
    # skipping the guest section entirely -> grompp atom-count mismatch.
    _BUILTIN_CAGE_GUEST_MOL_TYPES = ("guest", "ch4", "thf", "co2", "h2")
    # Custom guest mol_types are not known until custom_active is resolved
    # below; count them after custom_by_moltype is built.
    builtin_guest_count = sum(
        1 for m in ion_structure.molecule_index
        if m.mol_type in _BUILTIN_CAGE_GUEST_MOL_TYPES
    )
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
    # Phase 45-15 + Issue 3 (molh-atom-drop-origin): ``guest_runs`` is the
    # run-length-encoded list of ``(resname, count)`` in molecule order
    # (GROMACS [molecules] requires consecutive same-type runs — a
    # [CH4][THF][CH4][THF] layout emits 4 lines, not a single grouped total).
    # Resolved to RESNAME strings (not guest_types) so the [molecules]
    # writer emits them directly — unifies the built-in and mixed-custom
    # write paths. ``distinct_guest_types`` is the ordered deduped list of
    # BUILT-IN guest types (e.g. ["ch4"]) for #include directives (each
    # type's ``{type}_hydrate.itp`` included once) and atomtype blocks.
    # Empty for the pure single-custom path (no built-in cage guests).
    guest_runs: list[tuple] = []
    distinct_guest_types: list = []
    # Custom-guest branch is opt-in (mirror write_interface_top_file:1536-1603,
    # plans 41-05 / 44.1-09 / 44.1-11 / 44.1-13). When active, the residue name
    # comes from custom_guest_info (e.g. "MOL_H") and the custom ITP is
    # #include'd by basename; detect_guest_type_from_atoms is skipped (returns
    # None for custom guests). The built-in path (custom_guest_info is None or
    # empty) is byte-identical to before this param was added.
    custom_active = (
        custom_guest_info is not None
        and len(custom_guest_info) > 0
        and ion_structure.guest_atom_count > 0
    )
    custom_by_moltype = (
        {ci["mol_type"]: ci for ci in custom_guest_info}
        if custom_active else {}
    )
    # Issue 3: count ALL cage guests (built-in + custom). The ion inserter
    # now labels cage guests by their specific mol_type (ch4/thf/etoh_mix/...);
    # the old `mol_type == "guest"` filter would miss the ch4/thf/etoh_mix
    # entries. ``builtin_guest_count`` was computed above (before
    # custom_by_moltype was known); add the custom-guest count now.
    custom_guest_count = sum(
        1 for m in ion_structure.molecule_index
        if m.mol_type in custom_by_moltype
    )
    guest_count = builtin_guest_count + custom_guest_count
    # Refine custom_active: only active if there are actually cage guests in
    # the molecule_index (matches the old `guest_count > 0` gate condition).
    custom_active = custom_active and guest_count > 0

    if custom_active:
        # Detect which BUILT-IN cage guest types coexist with the custom
        # guests (the MIXED built-in+custom case — e.g. CH4 built-in small +
        # ethanol custom large). The ion inserter labels built-in guests
        # ch4/thf/...; collect the distinct types in molecule order for
        # #include + atomtype blocks. Empty for the pure single-custom path.
        for m in ion_structure.molecule_index:
            if m.mol_type in ("ch4", "thf", "co2", "h2"):
                if m.mol_type not in distinct_guest_types:
                    distinct_guest_types.append(m.mol_type)

        if distinct_guest_types:
            # MIXED built-in+custom: run-length encode the [molecules] section
            # by per-molecule RESIDUE NAME, keyed on ``mol.mol_type`` (NOT
            # detect_guest_type_from_atoms, which misidentifies ethanol as
            # ch4 because _get_molecule_atoms grabs only the first 5 atoms
            # C+4H and misses the O). Built-in ch4 -> CH4_H; custom ethanol
            # -> MOL_H.
            # The .gro writes guests in molecule_index order (Pass 2), so the
            # runs here match the .gro layout (GROMACS groups CONSECUTIVE
            # atoms by [molecules] entries).
            for m in ion_structure.molecule_index:
                if m.mol_type in ("ch4", "thf", "co2", "h2"):
                    _res = get_hydrate_guest_residue_name(m.mol_type)
                elif m.mol_type in custom_by_moltype:
                    _res = custom_by_moltype[m.mol_type]["residue_name"]
                elif m.mol_type == "guest":
                    # Generic "guest" fallback (ion inserter fallback path,
                    # descriptors absent) — fall back to first custom
                    # (preserves single-custom byte-identity when the
                    # inserter labeled "guest").
                    _res = next(iter(custom_by_moltype.values()))["residue_name"]
                else:
                    continue
                if guest_runs and guest_runs[-1][0] == _res:
                    guest_runs[-1] = (_res, guest_runs[-1][1] + 1)
                else:
                    guest_runs.append((_res, 1))
            # guest_res_name for the header / fallback: first run's resname.
            guest_res_name = (
                guest_runs[0][0] if guest_runs
                else next(iter(custom_by_moltype.values()))["residue_name"]
            )
            guest_type = (
                distinct_guest_types[0] if distinct_guest_types else None
            )
        else:
            # Pure single-custom (NO built-in cage guests): single MOL_H run.
            # Byte-identical to the old custom_active path. Resolve the
            # custom residue name via the matching molecule_index entry's
            # mol_type (fall back to the first/only custom_guest_info entry
            # — defensive, matches the interface/solute/custom-molecule
            # writers' fallback when molecule_index lacks a match or uses
            # the literal "guest" mol_type).
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
            # guest_runs stays [] -> [molecules] writes single MOL_H line.
    elif guest_count > 0 and ion_structure.guest_atom_count > 0:
        # Built-in path. Phase 45-15: detect EACH guest molecule's type and
        # run-length encode by consecutive same-type molecules. Issue 3:
        # ``detect_guest_type_runs`` now handles the per-molecule mol_types
        # the ion inserter produces (ch4/thf directly, "guest" via atom-name
        # detection) — byte-identical to before (the detected type matches
        # the mol_type for built-in guests). Resolve runs to RESNAME strings
        # so the [molecules] writer emits them directly (unified with the
        # mixed-custom path).
        _type_runs, distinct_guest_types = detect_guest_type_runs(
            ion_structure.molecule_index, ion_structure.atom_names
        )
        guest_type = distinct_guest_types[0] if distinct_guest_types else None
        guest_res_name = (
            get_hydrate_guest_residue_name(guest_type) if guest_type else "GUE"
        )
        for _gt, _cnt in _type_runs:
            _res = get_hydrate_guest_residue_name(_gt) if _gt else "GUE"
            guest_runs.append((_res, _cnt))

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
    # Phase 45-15: a mixed built-in hydrate needs BOTH ch4 and thf atomtype
    # sets (one per distinct guest type). Membership in distinct_guest_types
    # replaces the old single-``guest_type`` equality check.
    needs_ch4_atomtypes = ("ch4" in distinct_guest_types) or \
                          (has_solutes and ion_structure.solute_type.upper() == "CH4")
    needs_thf_atomtypes = ("thf" in distinct_guest_types) or \
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
        
        # [ defaults ] - force field defaults (Format C — write_ion_top_file
        # uses NO '; Defaults compatible' header + multi-space aligned
        # '; nbfunc' comment. Same variant as write_custom_molecule_top_file
        # and write_solute_top_file. See _shared._write_top_defaults docstring.)
        _write_top_defaults(f, include_amber_header=False, compact_nbfunc_comment=False)
        
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
            # Issue 3 (molh-atom-drop-origin): MIXED built-in+custom cage
            # assignment (CH4 built-in small + ethanol custom large). The
            # .gro contains BOTH CH4_H (built-in, 5-atom) and MOL_H (custom,
            # 9-atom) residues; the .top must #include BOTH the custom ITP
            # (etoh.itp, for MOL_H) AND the built-in {type}_hydrate.itp
            # (ch4_hydrate.itp, for CH4_H). Staged by
            # _stage_hydrate_guest_itps (which now stages built-in ITPs in
            # the custom path too). Pure single-custom (distinct_guest_types
            # is empty) -> no built-in #include (byte-identical to old).
            for _gt in distinct_guest_types:
                f.write(f'#include "{_gt}_hydrate.itp"\n')
        elif guest_count > 0:
            # Phase 45-15: include EACH distinct built-in guest type's
            # hydrate .itp (mixed CH4+THF needs both ch4_hydrate.itp and
            # thf_hydrate.itp). Single-guest yields one #include (unchanged).
            # The matching {type}_hydrate.itp files are staged into the
            # export dir by _stage_hydrate_guest_itps (which now stages ALL
            # distinct built-in types, not just the first).
            if distinct_guest_types:
                for _gt in distinct_guest_types:
                    f.write(f'#include "{_gt}_hydrate.itp"\n')
            else:
                # Fallback to generic guest.itp
                f.write('#include "guest.itp"\n')

        # Include custom molecule itp if custom molecules present.
        # custom_molecule_itp_name (UAT-F Issue 2 fix): when the custom molecule
        # ITP basename collides with a cage-guest ITP basename (both "etoh.itp"),
        # the exporter renames the staged copy to "{stem}_L.itp" (mirroring the
        # built-in _H/_L convention) and passes the renamed name here. When
        # None (no collision), the basename from custom_itp_path is used.
        if has_custom and ion_structure.custom_itp_path:
            from pathlib import Path as FilePath
            custom_itp_name = custom_molecule_itp_name or FilePath(ion_structure.custom_itp_path).name
            f.write(f'#include "{custom_itp_name}"\n')

        # Include solute itp if solutes present (liquid solutes use _liquid.itp)
        if has_solutes:
            solute_type_lower = ion_structure.solute_type.lower()
            solute_itp_name = f"{solute_type_lower}_liquid.itp"
            f.write(f'#include "{solute_itp_name}"\n')

        # Include ion itp (from ion export - combined NA+CL in single file)
        # Quick-029 bug (a): skip the include when 0 ions were inserted — the
        # NA/CL [atomtypes] block above is gated on the counts, so including
        # ion.itp (whose [atoms] reference NA/CL) is a grompp-fatal orphan
        # include ("Atomtype NA not found"). Byte-identical when ions present.
        if na_count > 0 or cl_count > 0:
            f.write('#include "ion.itp"\n')
        f.write("\n")

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
            # Phase 45-15 + Issue 3: write one [molecules] line per consecutive
            # same-type guest RUN (run-length encoded as ``(resname, count)``),
            # matching the .gro molecule order. GROMACS groups CONSECUTIVE
            # atoms by [molecules] entries, so a mixed [CH4_H][MOL_H] layout
            # in the .gro requires 2 [molecules] lines — NOT a single grouped
            # total. ``guest_runs`` is pre-resolved to resname strings (built-
            # in CH4_H/THF_H or custom MOL_H), so emit directly.
            # The pure single-custom path has ``guest_runs == []`` -> fall
            # back to the single ``guest_res_name`` line (byte-identical to
            # the old custom_active behavior).
            if guest_runs:
                for _res, _cnt in guest_runs:
                    f.write(f"{_res:<17s}{_cnt}\n")
            else:
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
