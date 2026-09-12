"""Structure generation module for QuickIce.

This module provides the mapping layer between QuickIce phase IDs
and GenIce lattice names, including supercell calculation logic.

Startup-performance note (slow-gui-startup fix): all re-exports are LAZY via
PEP 562 ``__getattr__``. The eager version of this file imported the full
chain (generator → genice2 + networkx, interface_builder → water_density →
iapws, ion_inserter / overlap_resolver → scipy.spatial) whenever ANY
submodule of this package was imported — including a bare
``import quickice.structure_generation.types``. That put ~0.5 s of heavy
imports on both the CLI and GUI startup paths for no benefit. With the lazy
map below, submodules load on first attribute access instead.

A side effect: names that were listed in ``__all__`` but missing from the
eager imports (``IonConfig``, ``IonStructure`` — they live in ``types.py``)
are now actually importable from this package, as ``__all__`` always
claimed.
"""

import importlib
from typing import Any

# name -> submodule that defines it
_EXPORT_TO_MODULE = {
    # Types
    "Candidate": "types",
    "GenerationResult": "types",
    "InterfaceConfig": "types",
    "InterfaceStructure": "types",
    "HydrateConfig": "types",
    "HydrateLatticeInfo": "types",
    "HydrateStructure": "types",
    "IonConfig": "types",
    "IonStructure": "types",
    "MoleculeIndex": "types",
    "HYDRATE_LATTICES": "types",
    "GUEST_MOLECULES": "types",
    # Errors
    "StructureGenerationError": "errors",
    "UnsupportedPhaseError": "errors",
    "InterfaceGenerationError": "errors",
    # Mapper functions and constants
    "PHASE_TO_GENICE": "mapper",
    "UNIT_CELL_MOLECULES": "mapper",
    "get_genice_lattice_name": "mapper",
    "calculate_supercell": "mapper",
    # Generator
    "IceStructureGenerator": "generator",
    "generate_candidates": "generator",
    "HydrateStructureGenerator": "hydrate_generator",
    # Interface generation
    "generate_interface": "interface_builder",
    "validate_interface_config": "interface_builder",
    # Water filling and overlap resolution
    "load_water_template": "water_filler",
    "tile_structure": "water_filler",
    "fill_region_with_water": "water_filler",
    "detect_overlaps": "overlap_resolver",
    "remove_overlapping_molecules": "overlap_resolver",
    # Unit conversion helpers
    "angstrom_to_nm": "overlap_resolver",
    "nm_to_angstrom": "overlap_resolver",
    # Ion insertion
    "IonInserter": "ion_inserter",
    # GRO parsing utilities
    "parse_gro_string": "gro_parser",
    "parse_gro_file": "gro_parser",
    # Ion export utilities
    "generate_ion_itp": "gromacs_ion_export",
    "write_ion_itp": "gromacs_ion_export",
    "get_ion_molecule_section": "gromacs_ion_export",
    # Cell utilities
    "is_cell_orthogonal": "cell_utils",
}

__all__ = sorted(_EXPORT_TO_MODULE)


def __getattr__(name: str) -> Any:
    """PEP 562 lazy re-export: load the defining submodule on first access."""
    try:
        submodule = _EXPORT_TO_MODULE[name]
    except KeyError:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        ) from None
    module = importlib.import_module(
        f"{__name__}.{submodule}"
    )
    value = getattr(module, name)
    # Cache on the package so subsequent accesses skip __getattr__.
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_EXPORT_TO_MODULE))
