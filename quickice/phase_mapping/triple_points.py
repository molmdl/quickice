"""
Triple point coordinates for ice phase boundaries.

All values from IAPWS R14-08(2011) and LSBU Water Phase Data.
T = Temperature in Kelvin, P = Pressure in MPa
"""

from typing import Tuple, Dict

TRIPLE_POINTS: Dict[str, Tuple[float, float]] = {
    "Ih_III_Liquid": (251.165, 207.5),
    "Ih_II_III": (238.55, 212.9),
    "II_III_V": (248.85, 344.3),
    "III_V_Liquid": (256.165, 346.3),
    "II_V_VI": (218.95, 620.0),
    "V_VI_Liquid": (273.31, 625.9),
    "VI_VII_Liquid": (354.75, 2200.0),
    "VI_VII_VIII": (278.0, 2100.0),
}

def get_triple_point(name: str) -> Tuple[float, float]:
    """Get (T, P) coordinates for a named triple point."""
    if name not in TRIPLE_POINTS:
        raise KeyError(f"Unknown triple point: {name}. Available: {list(TRIPLE_POINTS.keys())}")
    return TRIPLE_POINTS[name]
