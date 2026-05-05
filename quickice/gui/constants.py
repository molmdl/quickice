"""GUI constants for QuickIce application.

This module provides type-safe constants for GUI components.
"""

from enum import IntEnum


class TabIndex(IntEnum):
    """Tab position constants for QuickIce v4.5.
    
    Current tab order (v4.5 Phase 34):
        - Tab 0: Ice Configuration
        - Tab 1: Hydrate Configuration
        - Tab 2: Interface Construction
        - Tab 3: Solute Insertion
        - Tab 4: Custom Molecule (NEW)
        - Tab 5: Ion Insertion (moved from Tab 4)
    
    Note: Tab reordering complete in Phase 34.
    Ion tab moved from position 4 to position 5.
    """
    ICE = 0          # Ice Generation tab
    HYDRATE = 1      # Hydrate Config tab
    INTERFACE = 2    # Interface Construction tab
    SOLUTE = 3       # Solute Insertion tab (Phase 33)
    CUSTOM = 4       # Custom Molecule tab (NEW in Phase 34)
    ION = 5          # Ion Insertion tab (moved from 4)
