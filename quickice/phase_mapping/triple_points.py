"""
Triple point coordinates for ice phase boundaries.

Primary sources:
- IAPWS R14-08(2011): Triple point temperatures/pressures for Ice Ih, III, V, VI, VII
- Journaux et al. (2019, 2020): II-III-V and II-V-VI triple points (high pressure phases)
- LSBU Water Phase Data: Additional reference values and verification

T = Temperature in Kelvin, P = Pressure in MPa

Additional phases (XI, IX, X, XV) from literature:
- Ice XI: Proton-ordered form of Ice Ih at low T
- Ice IX: Proton-ordered form of Ice III at low T
- Ice X: Symmetric hydrogen bonds at extreme pressure
- Ice XV: Proton-ordered form of Ice VI at low T
"""

from typing import Tuple, Dict

TRIPLE_POINTS: Dict[str, Tuple[float, float]] = {
    "Ih_III_Liquid": (251.165, 209.9),
    "Ih_II_III": (238.45, 212.9),
    "II_III_V": (249.4, 355.5),
    "III_V_Liquid": (256.164, 350.1),
    "II_V_VI": (201.9, 670.8),
    "V_VI_Liquid": (273.31, 632.4),
    "VI_VII_Liquid": (355.0, 2216.0),
    "VI_VII_VIII": (278.15, 2100.0),
    # Additional phases (XI, IX, X, XV)
    "Ih_XI_Vapor": (72.0, 0.0001),  # Ice XI triple point at ~72K, essentially atmospheric
    "III_IX_Transition": (140.0, 300.0),  # Ice IX forms from Ice III cooling below 140K
    "VII_X_Transition": (300.0, 30000.0),  # Ice X transition at P>30 GPa
    "VI_XV_Transition": (100.0, 1100.0),  # Ice XV boundary near 1.1 GPa
    # Additional triple points for Ice X
    "VII_VIII_X": (100.0, 62000.0),  # 100K, 62 GPa - Ice VII/VIII/X triple point
    "VII_X_Liquid": (1000.0, 43000.0),  # ~1000K, 43 GPa - Liquid/VII/X (outside diagram bounds)
}

def get_triple_point(name: str) -> Tuple[float, float]:
    """Get (T, P) coordinates for a named triple point."""
    if name not in TRIPLE_POINTS:
        raise KeyError(f"Unknown triple point: {name}. Available: {list(TRIPLE_POINTS.keys())}")
    return TRIPLE_POINTS[name]
