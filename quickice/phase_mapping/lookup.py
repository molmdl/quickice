"""
Phase lookup functionality for QuickIce.

This module provides the core phase mapping functionality to determine
which ice polymorph is stable at given temperature and pressure conditions.

The lookup is based on phase diagram boundaries defined in ice_phases.json.
"""

import json
from pathlib import Path
from typing import Optional

from quickice.phase_mapping.errors import UnknownPhaseError


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
        # Order: VII, VIII, VI, V, III, II, Ic, Ih
        self.phase_order = [
            "ice_vii",
            "ice_viii",
            "ice_vi",
            "ice_v",
            "ice_iii",
            "ice_ii",
            "ice_ic",
            "ice_ih",
        ]

    def lookup(self, temperature: float, pressure: float) -> dict:
        """
        Find the ice phase stable at given T,P conditions.

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
        # Check each phase in order of specificity
        for phase_id in self.phase_order:
            if phase_id not in self.phases:
                continue

            phase_data = self.phases[phase_id]
            boundaries = phase_data["boundaries"]

            t_min = boundaries["temperature"]["min"]
            t_max = boundaries["temperature"]["max"]
            p_min = boundaries["pressure"]["min"]
            p_max = boundaries["pressure"]["max"]

            # Check if T,P falls within this phase's boundaries
            if t_min <= temperature <= t_max and p_min <= pressure <= p_max:
                return {
                    "phase_id": phase_id,
                    "phase_name": phase_data["name"],
                    "density": phase_data["density"],
                    "temperature": temperature,
                    "pressure": pressure,
                }

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
