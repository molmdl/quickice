"""Moleculetype registry for GROMACS topology file generation.

This module provides unique moleculetype naming to distinguish molecules
from different sources (hydrate guests vs liquid solutes).
"""

import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)


class MoleculetypeRegistry:
    """Registry for unique GROMACS moleculetype naming.
    
    Ensures CH4 from hydrate cages (CH4_HYD) is distinct from
    CH4 dissolved in liquid (CH4_L) in GROMACS topology files.
    
    Note: Liquid solutes use _L suffix (5 chars max) for GRO format compatibility.
    
    Attributes:
        RESERVED_NAMES: Set of names that cannot be used as custom molecule names
        
    Example:
        >>> registry = MoleculetypeRegistry()
        >>> registry.register_hydrate_guest('CH4')
        'CH4_HYD'
        >>> registry.register_liquid_solute('CH4')
        'CH4_L'
        >>> registry.get_gromacs_name('hydrate_CH4')
        'CH4_HYD'
    """
    
    RESERVED_NAMES: Set[str] = {
        "SOL", "NA", "CL", "CH4", "THF", "CO2", "H2",
        "CH4_HYD", "CH4_L", "THF_HYD", "THF_L"
    }
    
    def __init__(self) -> None:
        """Initialize empty registry."""
        self._registered: Dict[str, str] = {}
        self._counter = 0
        logger.info("MoleculetypeRegistry initialized")
    
    def register_hydrate_guest(self, molecule: str) -> str:
        """Register hydrate guest molecule with _HYD suffix.
        
        Args:
            molecule: Molecule name (e.g., 'CH4', 'THF')
            
        Returns:
            Registered name with _HYD suffix (e.g., 'CH4_HYD')
            
        Example:
            >>> registry.register_hydrate_guest('CH4')
            'CH4_HYD'
        """
        registered_name = f"{molecule}_HYD"
        source_key = f"hydrate_{molecule}"
        
        # Check if already registered
        if source_key in self._registered:
            logger.debug(f"Hydrate guest {molecule} already registered as {registered_name}")
            return self._registered[source_key]
        
        self._registered[source_key] = registered_name
        logger.info(f"Registered hydrate guest: {molecule} → {registered_name}")
        return registered_name
    
    def register_liquid_solute(self, molecule: str) -> str:
        """Register liquid solute molecule with _L suffix (5 chars max for GRO format).
        
        Args:
            molecule: Molecule name (e.g., 'CH4', 'THF')
            
        Returns:
            Registered name with _L suffix (e.g., 'CH4_L', 'THF_L')
            
        Example:
            >>> registry.register_liquid_solute('CH4')
            'CH4_L'
        """
        registered_name = f"{molecule}_L"
        source_key = f"liquid_{molecule}"
        
        # Check if already registered
        if source_key in self._registered:
            logger.debug(f"Liquid solute {molecule} already registered as {registered_name}")
            return self._registered[source_key]
        
        self._registered[source_key] = registered_name
        logger.info(f"Registered liquid solute: {molecule} → {registered_name}")
        return registered_name
    
    def register_custom_molecule(self, user_name: str = "MOL") -> str:
        """Register custom molecule with unique name.
        
        Args:
            user_name: User-provided molecule name (default: 'MOL')
            
        Returns:
            Unique molecule name (e.g., 'MOL', 'MOL_1', 'MOL_2')
            
        Raises:
            ValueError: If user_name conflicts with reserved names
            
        Example:
            >>> registry.register_custom_molecule('MOL')
            'MOL'
            >>> registry.register_custom_molecule('MOL')
            'MOL_1'
        """
        # Check for reserved name collision
        if user_name.upper() in self.RESERVED_NAMES:
            raise ValueError(
                f"Cannot use reserved name '{user_name}'. "
                f"Reserved names: {', '.join(sorted(self.RESERVED_NAMES))}"
            )
        
        # Check if name already in use
        existing_names = set(self._registered.values())
        
        if user_name not in existing_names:
            # First use of this name
            self._counter += 1
            source_key = f"custom_{self._counter}"
            self._registered[source_key] = user_name
            logger.info(f"Registered custom molecule: {user_name}")
            return user_name
        
        # Name collision - increment counter
        counter = 1
        while f"{user_name}_{counter}" in existing_names:
            counter += 1
        
        unique_name = f"{user_name}_{counter}"
        self._counter += 1
        source_key = f"custom_{self._counter}"
        self._registered[source_key] = unique_name
        logger.info(f"Registered custom molecule (collision resolved): {unique_name}")
        return unique_name
    
    def get_gromacs_name(self, source: str) -> str:
        """Get moleculetype name for GROMACS export.
        
        Args:
            source: Source identifier (e.g., 'hydrate_CH4', 'liquid_CH4', 'custom_1')
            
        Returns:
            Registered moleculetype name, or source.upper() if not registered
            
        Example:
            >>> registry.get_gromacs_name('hydrate_CH4')
            'CH4_HYD'
        """
        return self._registered.get(source, source.upper())
    
    def clear(self) -> None:
        """Clear registry (useful for testing).
        
        Removes all registered molecules and resets counter.
        """
        self._registered.clear()
        self._counter = 0
        logger.info("MoleculetypeRegistry cleared")
