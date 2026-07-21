"""Aggregator for the shared foundation split from gromacs_writer.py (Phase 48.1, Wave 1).

This module re-exports constants and helpers from 6 domain-specific sub-modules
so that downstream callers can use a single import path:

    from quickice.output._shared import validate_gro_residue_name, TIP4P_ICE_OW_SIGMA, ...

The sub-split keeps every file under SC-1's 800-line target (a single monolithic
``_shared.py`` would have been ~1050 lines, exceeding the limit).

Sub-modules:
  _constants: TIP4P_ICE_* + atomtype dicts + _registry singleton
  _atomtypes: 6 atomtype formatting/conflict/merge helpers
  _pbc:       wrap_positions_into_box + wrap_molecules_into_box (Group 1 CRIT-01)
  _itp:       5 ITP parsing/rewriting helpers + validate_gro_residue_name
  _guest:     5 guest identification/reordering helpers
  _tip4p:     get_tip4p_itp_path + compute_mw_position

Downstream callers (``gromacs_writer.py``, ``_gro_format.py``, future per-structure
writers in Waves 3-8) import ONLY from this aggregator. The 6 sub-modules may
import from each other (e.g. ``_atomtypes`` imports from ``_constants`` and
``_itp``) but MUST NOT import from this aggregator (would create a cycle).
"""

import logging

# Re-export constants + _registry singleton
from quickice.output._constants import (
    TIP4P_ICE_ALPHA, TIP4P_ICE_OW_SIGMA, TIP4P_ICE_OW_EPSILON,
    TIP4P_ICE_HW_CHARGE, TIP4P_ICE_MW_CHARGE,
    TIP4P_ICE_SETTLE_DOH, TIP4P_ICE_SETTLE_DHH,
    GAFF2_ATOMTYPES, ION_ATOMTYPES, WATER_ATOMTYPES,
    MOLECULE_TO_GROMACS, GUEST_ATOM_ORDER,
    CH4_ATOMTYPE_NAMES, THF_ATOMTYPE_NAMES, CO2_ATOMTYPE_NAMES, H2_ATOMTYPE_NAMES,
    _registry,
)
# Re-export atomtype helpers
from quickice.output._atomtypes import (
    _format_atomtype_line, _format_custom_atomtype_line, _write_atomtypes_block,
    _check_custom_atomtype_conflict, _lj_params_match, _merge_custom_atomtypes,
)
# Re-export PBC helpers
from quickice.output._pbc import wrap_positions_into_box, wrap_molecules_into_box
# Re-export ITP helpers + validate_gro_residue_name
# (validate_gro_residue_name lives in _itp, not defined directly here —
# co-locating it with its primary consumer transform_guest_itp avoids a
# circular import: _shared -> _itp -> _shared. Function body is byte-identical
# to the pre-refactor source; only the file path changed.)
from quickice.output._itp import (
    parse_itp_residue_name, parse_itp_atomtypes, comment_out_atomtypes_in_itp,
    _rewrite_atoms_section_resname, transform_guest_itp,
    validate_gro_residue_name,
)
# Re-export guest helpers
from quickice.output._guest import (
    reorder_guest_atoms, get_guest_residue_name, get_hydrate_guest_residue_name,
    _get_molecule_atoms, detect_guest_type_from_atoms,
)
# Re-export TIP4P helpers
from quickice.output._tip4p import get_tip4p_itp_path, compute_mw_position

logger = logging.getLogger(__name__)


def _write_top_defaults(
    f,
    *,
    include_amber_header: bool = True,
    compact_nbfunc_comment: bool = True,
) -> None:
    """Write the [defaults] block (comb-rule=2, Lorentz-Berthelot, AMBER/GAFF2 convention).

    Used by: all 6 TOP writers (write_top_file, write_interface_top_file,
             write_multi_molecule_top_file, write_ion_top_file,
             write_custom_molecule_top_file, write_solute_top_file).

    CRITICAL (AGENTS.md): comb-rule=2 (Lorentz-Berthelot) is the AMBER/GAFF2
    convention. Never use comb-rule=1. The data line
    ``1               2               yes             0.5     0.8333`` has
    nbfunc=1, comb-rule=2 — emitted byte-identically in ONE place (this helper)
    regardless of the ``include_amber_header`` / ``compact_nbfunc_comment``
    flags; the flags only affect the 2 comment lines above the data line, NOT
    the data line itself. This is the single source of truth for comb-rule=2.

    Format variants (preserved byte-identically per writer — research §3 had
    an error: it claimed "byte-identical across all 6 TOP writers" but the
    actual source has 3 distinct [defaults] block formats. Discovered and
    verified during plan 48.1-07 execution — see 48.1-07 SUMMARY Deviations.
    The parameterization preserves byte-identity for all 3 variants so the
    14 byte-equivalence tests continue to PASS):

    - **Format A** (write_top_file, write_interface_top_file): 6 lines, includes
      ``; Defaults compatible with the Amber forcefield`` + compact ``; nbfunc``
      comment (single-space separators). Default helper invocation:
      ``_write_top_defaults(f)``.
    - **Format B** (write_multi_molecule_top_file): 5 lines, NO ``; Defaults``
      header line, compact ``; nbfunc`` comment. Call:
      ``_write_top_defaults(f, include_amber_header=False)``.
    - **Format C** (write_ion_top_file, write_custom_molecule_top_file,
      write_solute_top_file): 5 lines, NO ``; Defaults`` header line, aligned
      ``; nbfunc`` comment (multi-space tabular alignment, different from A/B).
      Call: ``_write_top_defaults(f, include_amber_header=False,
      compact_nbfunc_comment=False)``.

    Args:
        f: open file handle to write to.
        include_amber_header: When True (default), emit the
            ``; Defaults compatible with the Amber forcefield\\n`` line before
            ``[ defaults ]\\n`` (Format A — write_top_file +
            write_interface_top_file). When False, skip that line (Formats B/C
            — the other 4 writers).
        compact_nbfunc_comment: When True (default), emit
            ``; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ\\n`` (single-space
            separators — Formats A/B). When False, emit
            ``; nbfunc        comb-rule       gen-pairs       fudgeLJ fudgeQQ\\n``
            (multi-space tabular alignment — Format C, used by write_ion_top_file
            + write_custom_molecule_top_file + write_solute_top_file).

    Output (Format A, default — byte-identical to the original write_top_file
    and write_interface_top_file inline blocks)::

        ; Defaults compatible with the Amber forcefield
        [ defaults ]
        ; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ
        ; comb-rule=2 (Lorentz-Berthelot): sigma_ij=(sigma_i+sigma_j)/2, epsilon_ij=sqrt(eps_i*eps_j)
        ; Matches AMBER/GAFF2 convention used by GROMACS-bundled AMBER force fields
        1               2               yes             0.5     0.8333

    The trailing ``\\n\\n`` on the data line emits a blank line after the
    [defaults] block, byte-identical to all 6 original inline blocks.
    """
    if include_amber_header:
        f.write("; Defaults compatible with the Amber forcefield\n")
    f.write("[ defaults ]\n")
    if compact_nbfunc_comment:
        f.write("; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ\n")
    else:
        f.write("; nbfunc        comb-rule       gen-pairs       fudgeLJ fudgeQQ\n")
    f.write("; comb-rule=2 (Lorentz-Berthelot): sigma_ij=(sigma_i+sigma_j)/2, epsilon_ij=sqrt(eps_i*eps_j)\n")
    f.write("; Matches AMBER/GAFF2 convention used by GROMACS-bundled AMBER force fields\n")
    f.write("1               2               yes             0.5     0.8333\n\n")


__all__ = [
    # Constants
    "TIP4P_ICE_ALPHA", "TIP4P_ICE_OW_SIGMA", "TIP4P_ICE_OW_EPSILON",
    "TIP4P_ICE_HW_CHARGE", "TIP4P_ICE_MW_CHARGE",
    "TIP4P_ICE_SETTLE_DOH", "TIP4P_ICE_SETTLE_DHH",
    "GAFF2_ATOMTYPES", "ION_ATOMTYPES", "WATER_ATOMTYPES",
    "MOLECULE_TO_GROMACS", "GUEST_ATOM_ORDER",
    "CH4_ATOMTYPE_NAMES", "THF_ATOMTYPE_NAMES", "CO2_ATOMTYPE_NAMES", "H2_ATOMTYPE_NAMES",
    "_registry",
    # Atomtype helpers
    "_format_atomtype_line", "_format_custom_atomtype_line", "_write_atomtypes_block",
    "_check_custom_atomtype_conflict", "_lj_params_match", "_merge_custom_atomtypes",
    # PBC helpers
    "wrap_positions_into_box", "wrap_molecules_into_box",
    # ITP helpers + GRO validator
    "parse_itp_residue_name", "parse_itp_atomtypes", "comment_out_atomtypes_in_itp",
    "_rewrite_atoms_section_resname", "transform_guest_itp",
    "validate_gro_residue_name",
    # Guest helpers
    "reorder_guest_atoms", "get_guest_residue_name", "get_hydrate_guest_residue_name",
    "_get_molecule_atoms", "detect_guest_type_from_atoms",
    # TIP4P helpers
    "get_tip4p_itp_path", "compute_mw_position",
    # TOP [defaults] block helper (Wave 2e — plan 48.1-07)
    "_write_top_defaults",
]
