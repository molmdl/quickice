"""Interface assembly modes for ice-water interface generation.

This subpackage provides three geometry modes for interface generation:
- slab: Ice-water-ice sandwich along Z-axis
- pocket: Water cavity in ice matrix
- piece: Ice crystal embedded in water box
"""

from quickice.structure_generation.modes.slab import assemble_slab
from quickice.structure_generation.modes.pocket import assemble_pocket
from quickice.structure_generation.modes.piece import assemble_piece

__all__ = ["assemble_slab", "assemble_pocket", "assemble_piece"]
