"""Structure generation module for QuickIce.

This module provides the mapping layer between QuickIce phase IDs
and GenIce lattice names, including supercell calculation logic.
"""

from quickice.structure_generation.errors import (
    StructureGenerationError,
    UnsupportedPhaseError,
    InterfaceGenerationError,
)
from quickice.structure_generation.mapper import (
    PHASE_TO_GENICE,
    UNIT_CELL_MOLECULES,
    calculate_supercell,
    get_genice_lattice_name,
)
from quickice.structure_generation.types import (
    Candidate,
    GenerationResult,
    InterfaceConfig,
    InterfaceStructure,
    HydrateConfig,
    HydrateLatticeInfo,
    HydrateStructure,
    MoleculeIndex,
    HYDRATE_LATTICES,
    GUEST_MOLECULES,
)
from quickice.structure_generation.generator import (
    IceStructureGenerator,
    generate_candidates,
)
from quickice.structure_generation.interface_builder import (
    generate_interface,
    validate_interface_config,
)
from quickice.structure_generation.water_filler import (
    load_water_template,
    tile_structure,
    fill_region_with_water,
)
from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
from quickice.structure_generation.overlap_resolver import (
    detect_overlaps,
    remove_overlapping_molecules,
    angstrom_to_nm,
    nm_to_angstrom,
)
from quickice.structure_generation.gro_parser import (
    parse_gro_string,
    parse_gro_file,
)
from quickice.structure_generation.cell_utils import is_cell_orthogonal

__all__ = [
    # Types
    "Candidate",
    "GenerationResult",
    "InterfaceConfig",
    "InterfaceStructure",
    "HydrateConfig",
    "HydrateLatticeInfo",
    "HydrateStructure",
    "MoleculeIndex",
    # Errors
    "StructureGenerationError",
    "UnsupportedPhaseError",
    "InterfaceGenerationError",
    # Mapper functions
    "get_genice_lattice_name",
    "calculate_supercell",
    # Generator
    "IceStructureGenerator",
    "generate_candidates",
    "HydrateStructureGenerator",
    # Interface generation
    "generate_interface",
    "validate_interface_config",
    # Water filling and overlap resolution
    "load_water_template",
    "tile_structure",
    "fill_region_with_water",
    "detect_overlaps",
    "remove_overlapping_molecules",
    # Unit conversion helpers
    "angstrom_to_nm",
    "nm_to_angstrom",
    # GRO parsing utilities
    "parse_gro_string",
    "parse_gro_file",
    # Constants
    "PHASE_TO_GENICE",
    "UNIT_CELL_MOLECULES",
    "HYDRATE_LATTICES",
    "GUEST_MOLECULES",
    # Cell utilities
    "is_cell_orthogonal",
]
