"""GUI constants for QuickIce application.

This module provides type-safe constants for GUI components.
"""

from enum import IntEnum


class TabIndex(IntEnum):
    """Tab position constants for QuickIce v4.5.
    
    Current tab order (v4.5 Phase 34.3):
        - Tab 0: Ice Configuration
        - Tab 1: Hydrate Generation
        - Tab 2: Interface Construction
        - Tab 3: Custom Molecule (Phase 34)
        - Tab 4: Solute Insertion (Phase 33)
        - Tab 5: Ion Insertion
    
    Note: Tab order swapped in Phase 34.3 to enable Custom → Solute workflow.
    Custom Molecule now appears before Solute Insertion.
    """
    ICE = 0          # Ice Generation tab
    HYDRATE = 1      # Hydrate Generation tab
    INTERFACE = 2    # Interface Construction tab
    CUSTOM = 3       # Custom Molecule tab (Phase 34)
    SOLUTE = 4       # Solute Insertion tab (Phase 33)
    ION = 5          # Ion Insertion tab
