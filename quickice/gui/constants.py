"""GUI constants for QuickIce application.

This module provides type-safe constants for GUI components.
"""

from enum import IntEnum


class TabIndex(IntEnum):
    """Tab position constants for QTabWidget indices.
    
    Current tab positions (v4.0). Use instead of hardcoded integers.
    Note: ION position will change from 3 to 5 when Solute/Custom tabs are added in Phase 35.
    
    Example: tab_widget.setCurrentIndex(TabIndex.ICE)
    """
    ICE = 0          # Ice Generation tab
    HYDRATE = 1      # Hydrate Config tab
    INTERFACE = 2    # Interface Construction tab
    ION = 3          # Ion Insertion tab (current position, moves to 5 in Phase 35)
    # Future tabs (Phase 33-34):
    # SOLUTE = 3     # Solute Insertion tab (Phase 33)
    # CUSTOM = 4     # Custom Molecule tab (Phase 34)
    # ION will move to position 5 when Solute/Custom tabs are added
