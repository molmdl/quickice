"""
IAPWS R14-08(2011) melting curve equations for ice phases.

Each function returns melting pressure in MPa for given temperature.
Ice is solid when P < P_melt(T) at given T.
Liquid when P > P_melt(T).
"""

import math
from typing import Optional

def ice_ih_melting_pressure(T: float) -> float:
    """
    Ice Ih melting curve (251.165 K ≤ T ≤ 273.16 K).
    Returns pressure in MPa.
    """
    if not (251.165 <= T <= 273.16):
        raise ValueError(f"T={T}K outside Ice Ih melting curve range [251.165, 273.16]K")
    Tt = 273.16
    Pt = 0.000611657
    Tita = T / Tt
    a = [0.119539337e7, 0.808183159e5, 0.33382686e4]
    expo = [3.0, 0.2575e2, 0.10375e3]
    suma = 1 + sum(ai * (1 - Tita**expi) for ai, expi in zip(a, expo))
    return suma * Pt

def ice_iii_melting_pressure(T: float) -> float:
    """Ice III melting curve (251.165 K < T ≤ 256.164 K)."""
    if not (251.165 < T <= 256.164):
        raise ValueError(f"T={T}K outside Ice III melting curve range (251.165, 256.164]K")
    Tref, Pref = 251.165, 208.566
    Tita = T / Tref
    return Pref * (1 - 0.299948 * (1 - Tita**60))

def ice_v_melting_pressure(T: float) -> float:
    """Ice V melting curve (256.164 K < T ≤ 273.31 K)."""
    if not (256.164 < T <= 273.31):
        raise ValueError(f"T={T}K outside Ice V melting curve range (256.164, 273.31]K")
    Tref, Pref = 256.164, 350.100
    Tita = T / Tref
    return Pref * (1 - 1.18721 * (1 - Tita**8))

def ice_vi_melting_pressure(T: float) -> float:
    """Ice VI melting curve (273.31 K < T ≤ 355 K)."""
    if not (273.31 < T <= 355):
        raise ValueError(f"T={T}K outside Ice VI melting curve range (273.31, 355]K")
    Tref, Pref = 273.31, 632.400
    Tita = T / Tref
    return Pref * (1 - 1.07476 * (1 - Tita**4.6))

def ice_vii_melting_pressure(T: float) -> float:
    """Ice VII melting curve (355 K < T ≤ 715 K)."""
    if not (355 < T <= 715):
        raise ValueError(f"T={T}K outside Ice VII melting curve range (355, 715]K")
    Tref, Pref = 355, 2216.000
    Tita = T / Tref
    return Pref * math.exp(
        1.73683 * (1 - 1/Tita)
        - 0.544606e-1 * (1 - Tita**5)
        + 0.806106e-7 * (1 - Tita**22)
    )

def melting_pressure(T: float, ice_type: str = "Ih") -> float:
    """
    Unified melting pressure function.
    
    Args:
        T: Temperature in K
        ice_type: "Ih", "III", "V", "VI", or "VII"
    
    Returns:
        Melting pressure in MPa
    """
    functions = {
        "Ih": ice_ih_melting_pressure,
        "III": ice_iii_melting_pressure,
        "V": ice_v_melting_pressure,
        "VI": ice_vi_melting_pressure,
        "VII": ice_vii_melting_pressure,
    }
    if ice_type not in functions:
        raise ValueError(f"Unknown ice type: {ice_type}. Available: {list(functions.keys())}")
    return functions[ice_type](T)
