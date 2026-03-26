"""
Phase lookup functionality for QuickIce.

This module provides the core phase mapping functionality to determine
which ice polymorph is stable at given temperature and pressure conditions.

The lookup uses curved phase boundaries defined via IAPWS-certified triple points
and melting curves, using shapely for point-in-polygon evaluation.
"""

import json
from pathlib import Path
from typing import Optional

from shapely.geometry import Point, Polygon

from quickice.phase_mapping.errors import UnknownPhaseError
from quickice.phase_mapping.data.ice_boundaries import PHASE_POLYGONS


class IcePhaseLookup:
    """
    Lookup class for determining ice phases from T,P conditions.

    This class loads phase boundary data and provides methods to find
    the appropriate ice polymorph for given thermodynamic conditions.

    Attributes:
        phases: Dictionary of phase data loaded from JSON.
        phase_order: List of phase IDs in lookup order (high pressure first).
    """

    def __init__(self, data_path: Optional[str] = None):
        """
        Initialize the phase lookup with boundary data.

        Args:
            data_path: Optional path to ice_phases.json.
                      If None, uses default package location.
        """
        if data_path is None:
            # Default to package data directory
            data_path = Path(__file__).parent / "data" / "ice_phases.json"
        else:
            data_path = Path(data_path)

        with open(data_path, "r") as f:
            data = json.load(f)

        self.phases = data["phases"]
        self.metadata = data.get("metadata", {})

        # Order phases by specificity: high pressure phases first
        # This ensures we check more restrictive regions before general ones
        # Order: VIII, VII, VI, V, III, II, Ic, Ih
        self.phase_order = [
            "ice_viii",
            "ice_vii",
            "ice_vi",
            "ice_v",
            "ice_iii",
            "ice_ii",
            "ice_ic",
            "ice_ih",
        ]

    def _build_result(
        self, phase_id: str, temperature: float, pressure: float
    ) -> dict:
        """
        Build the result dictionary for a matched phase.

        Args:
            phase_id: Phase identifier (e.g., "ice_ih")
            temperature: Input temperature
            pressure: Input pressure

        Returns:
            Dictionary with phase details
        """
        phase_data = self.phases[phase_id]
        return {
            "phase_id": phase_id,
            "phase_name": phase_data["name"],
            "density": phase_data["density"],
            "temperature": temperature,
            "pressure": pressure,
        }

    def lookup(self, temperature: float, pressure: float) -> dict:
        """
        Find the ice phase stable at given T,P conditions using curved boundaries.

        Uses shapely Point-in-Polygon evaluation for accurate phase identification
        at curved boundaries defined by IAPWS triple points and melting curves.

        Args:
            temperature: Temperature in Kelvin.
            pressure: Pressure in MPa.

        Returns:
            Dictionary containing:
                - phase_id: Phase identifier (e.g., "ice_ih")
                - phase_name: Human-readable name (e.g., "Ice Ih")
                - density: Density in g/cm³
                - temperature: Input temperature
                - pressure: Input pressure

        Raises:
            UnknownPhaseError: If no phase matches the given conditions.
        """
        # Create a point for the T,P coordinates
        point = Point(temperature, pressure)

        # Check phases hierarchically (high pressure first)
        # This ensures we check more restrictive regions before general ones
        phase_order = [
            "ice_viii",
            "ice_vii",
            "ice_vi",
            "ice_v",
            "ice_iii",
            "ice_ii",
            "ice_ic",
            "ice_ih",
        ]

        for phase_id in phase_order:
            # Skip if phase not in data
            if phase_id not in self.phases:
                continue

            # Check if phase has polygon data
            if phase_id not in PHASE_POLYGONS:
                continue

            # Get polygon vertices and create shapely polygon
            polygon_vertices = PHASE_POLYGONS[phase_id]
            polygon = Polygon(polygon_vertices)

            # Check if point is inside the polygon (curved boundary evaluation)
            # Use covers() to include points on the boundary
            if polygon.covers(point):
                return self._build_result(phase_id, temperature, pressure)

        # No matching phase found
        raise UnknownPhaseError(
            "No ice phase found for given conditions",
            temperature=temperature,
            pressure=pressure,
        )


def lookup_phase(temperature: float, pressure: float) -> dict:
    """
    Convenience function to lookup ice phase from T,P conditions.

    This function creates a default IcePhaseLookup instance and
    performs the lookup. For repeated lookups, create an IcePhaseLookup
    instance directly to avoid reloading the data.

    Args:
        temperature: Temperature in Kelvin.
        pressure: Pressure in MPa.

    Returns:
        Dictionary containing:
            - phase_id: Phase identifier (e.g., "ice_ih")
            - phase_name: Human-readable name (e.g., "Ice Ih")
            - density: Density in g/cm³
            - temperature: Input temperature
            - pressure: Input pressure

    Raises:
        UnknownPhaseError: If no phase matches the given conditions.

    Example:
        >>> result = lookup_phase(273, 0)
        >>> result['phase_id']
        'ice_ih'
        >>> result['phase_name']
        'Ice Ih'
    """
    lookup = IcePhaseLookup()
    return lookup.lookup(temperature, pressure)
