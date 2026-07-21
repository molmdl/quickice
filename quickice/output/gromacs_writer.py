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


from quickice.output.custom_writer import write_custom_molecule_gro_file, write_custom_molecule_top_file

from quickice.output.solute_writer import write_solute_gro_file, write_solute_top_file

