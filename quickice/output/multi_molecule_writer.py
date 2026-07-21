"""GROMACS writers for hydrate (multi-molecule) export.

Split from quickice/output/gromacs_writer.py in Phase 48.1 (FRAG-03).
These writers handle the hydrate export path: a HydrateStructure (or
Candidate-converted-from-HydrateStructure) with multiple molecule types
driven by ``molecule_index`` + MoleculetypeRegistry.

CRITICAL (research §3 'try/except cleanup'):
    write_multi_molecule_gro_file INTENTIONALLY LACKS the try/except
    (OSError, ValueError) cleanup block that 4 of the 6 GRO writers have.
    DO NOT add try/except "for consistency" — that would be a behavior change
    (partial files would be cleaned up where they weren't before), violating
    the byte-identical / behavior-identical contract. Preserved verbatim by
    plans 48.1-05 (this writer) and 48.1-06 (write_solute_gro_file).

CRITICAL (research §3 'SOL ice 3→4 expansion'):
    write_multi_molecule_gro_file uses a GENERIC per-atom loop (iterates
    ``mol_atom_names``) — NOT ``_format_sol_ice_molecule`` (which assumes
    3-atom OHH input). The multi-molecule writer's ice molecules are already
    4-atom (OW, HW1, HW2, MW) because the input HydrateStructure has them
    pre-computed, and the res_name is resolved per-molecule via the
    registry/custom_guest_info/fallback chain (NOT hardcoded "SOL"). Forcing
    the generic loop into 1-atom ``_format_guest_molecule`` calls would hurt
    readability. The inline f-string is byte-identical to
    ``_format_guest_molecule``'s f-string (verified by _gro_format helper
    unit tests); the DRY win is the format string itself, which is already
    captured in the helper for the OTHER 4 writers that have specialized
    blocks. The generic loop stays inline — research §3 row "generic (uses
    atom_names)" documents this as the intentional divergence.

Registry singleton (research §1 line 307, §10 'Module-level side effects'):
    write_multi_molecule_top_file uses ``reg = registry or _registry`` as
    fallback when the ``registry`` arg is None. The ``_registry`` singleton
    was moved to ``_shared.py`` in Wave 1 (plan 48.1-02) and is imported here
    from ``_shared``. The fallback logic is unchanged — only the import
    source changed (was module-level in gromacs_writer.py, now imported from
    ``_shared``). This is the ONLY writer that uses the ``_registry``
    singleton (the other 5 GRO/TOP writers either take ``registry`` explicitly
    or don't use a registry at all).
"""

import logging
import warnings
from pathlib import Path

import numpy as np

from quickice.structure_generation.types import MoleculeIndex
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry

from quickice.output._shared import (
    validate_gro_residue_name,
    reorder_guest_atoms,
    get_guest_residue_name,
    MOLECULE_TO_GROMACS,
    WATER_ATOMTYPES,
    ION_ATOMTYPES,
    CH4_ATOMTYPE_NAMES,
    THF_ATOMTYPE_NAMES,
    CO2_ATOMTYPE_NAMES,
    H2_ATOMTYPE_NAMES,
    _write_top_defaults,
    _format_atomtype_line,
    _write_atomtypes_block,
    _merge_custom_atomtypes,
    _registry,  # CRITICAL: singleton moved to _shared in Wave 1 (plan 48.1-02).
)
from quickice.output._gro_format import (
    _write_gro_header,
    _write_gro_box_vectors,
)

logger = logging.getLogger(__name__)


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
        # Format B — write_multi_molecule_top_file is the only writer using
        # this variant: NO '; Defaults compatible' header line + compact
        # '; nbfunc' comment. See _shared._write_top_defaults docstring.
        _write_top_defaults(f, include_amber_header=False)
        
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
