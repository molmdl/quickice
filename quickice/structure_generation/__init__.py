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
from quickice.structure_generation.overlap_resolver import (
    detect_overlaps,
    remove_overlapping_molecules,
    angstrom_to_nm,
    nm_to_angstrom,
)

__all__ = [
    # Types
    "Candidate",
    "GenerationResult",
    "InterfaceConfig",
    "InterfaceStructure",
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
    # Constants
    "PHASE_TO_GENICE",
    "UNIT_CELL_MOLECULES",
]
