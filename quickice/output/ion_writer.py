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
    # Phase 45-15: built-in mixed hydrates (CH4 in small + THF in large cages)
    # carry MULTIPLE guest types. ``guest_runs`` is the run-length-encoded
    # list of ``(guest_type, count)`` in molecule order (GROMACS [molecules]
    # requires consecutive same-type runs — a [CH4][THF][CH4][THF] layout emits
    # 4 lines, not a single grouped total). ``distinct_guest_types`` is the
    # ordered deduped list for #include directives (each type's
    # ``{type}_hydrate.itp`` included once). Empty for the custom-guest path
    # (which uses a single ``guest_res_name`` from custom_guest_info).
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
        # Built-in path. Phase 45-15: detect EACH guest molecule's type from
        # its atom-name slice and run-length encode by consecutive same-type
        # molecules. Each molecule_index entry now carries the CORRECT
        # per-molecule count (post ion-inserter fix), so the slice is exactly
        # one molecule — no neighbor contamination, detection is reliable.
        # The single-guest path (all-CH4) yields one run, byte-identical to
        # before; a mixed [CH4][THF][CH4][THF] layout yields 4 runs.
        guest_runs, distinct_guest_types = detect_guest_type_runs(
            ion_structure.molecule_index, ion_structure.atom_names
        )
        guest_type = distinct_guest_types[0] if distinct_guest_types else None
        guest_res_name = (
            get_hydrate_guest_residue_name(guest_type) if guest_type else "GUE"
        )

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
            # Phase 45-15: write one [molecules] line per consecutive
            # same-type guest RUN (run-length encoded), matching the .gro
            # molecule order. GROMACS groups CONSECUTIVE atoms by [molecules]
            # entries, so a mixed [CH4][THF][CH4][THF] layout in the .gro
            # requires 4 [molecules] lines — NOT a single grouped total.
            # The custom-guest path (custom_active) emits a single line with
            # the caller-supplied guest_res_name (unchanged).
            if custom_active or not guest_runs:
                f.write(f"{guest_res_name:<17s}{guest_count}\n")
            else:
                for _gt, _cnt in guest_runs:
                    _res = (
                        get_hydrate_guest_residue_name(_gt) if _gt else "GUE"
                    )
                    f.write(f"{_res:<17s}{_cnt}\n")

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
