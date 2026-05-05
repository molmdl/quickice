"""GUI constants for QuickIce application.

This module provides type-safe constants for GUI components.
"""

from enum import IntEnum


class TabIndex(IntEnum):
    """Tab position constants for QuickIce v4.5.
    
    Current tab order (v4.5 Phase 33):
        - Tab 0: Ice Configuration
        - Tab 1: Hydrate Configuration
        - Tab 2: Interface Construction
        - Tab 3: Solute Insertion (NEW)
        - Tab 4: Ion Insertion (will move to 5 in Phase 35)
    
    Future tab order (v4.5 Phase 35):
        - Tab 0: Ice Configuration
        - Tab 1: Hydrate Configuration
        - Tab 2: Interface Construction
        - Tab 3: Solute Insertion
        - Tab 4: Custom Molecule (Phase 34)
        - Tab 5: Ion Insertion (moved from Tab 4)
    """
    ICE = 0          # Ice Generation tab
    HYDRATE = 1      # Hydrate Config tab
    INTERFACE = 2    # Interface Construction tab
    SOLUTE = 3       # Solute Insertion tab (NEW in Phase 33)
    ION = 4          # Ion Insertion tab (moved from 3, will move to 5 in Phase 35)
