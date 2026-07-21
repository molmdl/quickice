"""TIP4P-ICE + GAFF2/ION/WATER constants and the module-level ``_registry`` singleton.

Extracted from ``gromacs_writer.py`` (Phase 48.1, Wave 1) so that downstream
modules can import from a stable location instead of from the monolith.
All values are byte-identical to the pre-refactor source (no numeric change).

References:
    Abascal et al. 2005, DOI: 10.1063/1.1931662 (TIP4P-ICE)
    Madrid2019 (ION_ATOMTYPES)
"""

from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry


# TIP4P-ICE virtual site parameter (from tip4p-ice.itp virtual_sites3 directive).
# Abascal et al. 2005, DOI: 10.1063/1.1931662.
TIP4P_ICE_ALPHA = 0.13458335

# TIP4P-ICE LJ parameters (Abascal et al. 2005, DOI: 10.1063/1.1931662)
# sigma_O = 3.1668 Å = 0.31668 nm; epsilon_O/k_B = 106.1 K → 106.1 × 0.00831446 = 0.88211 kJ/mol
TIP4P_ICE_OW_SIGMA = 3.16680e-1    # nm
TIP4P_ICE_OW_EPSILON = 8.82110e-1   # kJ/mol

# TIP4P-ICE charges and settle distances (from quickice/data/tip4p-ice.itp
# [atoms]/[settles] sections; Abascal et al. 2005, DOI: 10.1063/1.1931662).
# Water is charge-neutral: OW=0, 2*HW=+1.1794, MW=-1.1794 (net 0).
TIP4P_ICE_HW_CHARGE = 0.5897       # e (HW_ice, x2 per water molecule)
TIP4P_ICE_MW_CHARGE = -1.1794       # e (MW virtual site; = -2 * HW_CHARGE)
TIP4P_ICE_SETTLE_DOH = 0.09572     # nm (O-H distance, [settles] doh)
TIP4P_ICE_SETTLE_DHH = 0.15139     # nm (H-H distance, [settles] dhh)


# ---------------------------------------------------------------------------
# GAFF2 atomtype definitions for standard guest/solute molecules
# ---------------------------------------------------------------------------
# Each entry: (bond_type, atomic_number, mass, charge, ptype, sigma_nm, epsilon_kjmol)
# Format matches the 8-column GROMACS [ atomtypes ] section.
# Centralizing these eliminates scattered hardcoded atomtype lines and makes
# deduplication between molecule types (e.g., CH4 and THF sharing "hc") trivial.
# ---------------------------------------------------------------------------
GAFF2_ATOMTYPES: dict[str, tuple[str, int, float, float, str, float, float]] = {
    # CH4 atom types
    "c3":  ("c3",  6, 12.0107, 0.0, "A", 3.39771e-1, 4.51035e-1),
    "hc":  ("hc",  1,  1.0079, 0.0, "A", 2.60018e-1, 8.70272e-2),
    # THF atom types
    "os":  ("os",  8, 15.9994, 0.0, "A", 3.15610e-1, 3.03758e-1),
    "c5":  ("c5",  6, 12.0107, 0.0, "A", 3.39771e-1, 4.51035e-1),
    "h1":  ("h1",  1,  1.0079, 0.0, "A", 2.42200e-1, 8.70272e-2),
    # CO2 atom types
    "c_2": ("c_2", 6, 12.0107, 0.0, "A", 3.39955e-1, 4.39089e-1),
    "o_2": ("o_2", 8, 15.9994, 0.0, "A", 3.02714e-1, 8.80314e-1),
    # H2 atom types
    "hn":  ("hn",  1,  1.0080, 0.0, "A", 0.0,         0.0),
}

# Atomtype names required per molecule type (order matches ITP file convention)
CH4_ATOMTYPE_NAMES  = ["c3", "hc"]
THF_ATOMTYPE_NAMES  = ["os", "c5", "hc", "h1"]
CO2_ATOMTYPE_NAMES  = ["c_2", "o_2"]
H2_ATOMTYPE_NAMES   = ["hn"]

# Madrid2019 ion atomtype parameters (name → tuple).
# NOTE: The `charge` field here is 0.0 by GROMACS convention — the [atomtypes]
# section carries NONBONDED parameters only (sigma, epsilon); the charge column
# is a placeholder and is IGNORED for nonbonded tabulation. The REAL ion charge
# (Na+ = +0.85, Cl- = -0.85, Madrid2019) lives in the [moleculetype] [atoms]
# section written by quickice/structure_generation/gromacs_ion_export.py
# (NA_CHARGE / CL_CHARGE). The two values are DIFFERENT FIELDS in DIFFERENT
# sections — they are NOT duplicates and MUST NOT be merged. See RESEARCH.md
# UNIT-05 and Abascal/Madrid2019 conventions.
ION_ATOMTYPES: dict[str, tuple[str, int, float, float, str, float, float]] = {
    "NA": ("NA", 11, 22.9898, 0.0, "A", 2.21737e-1, 1.47236e0),
    "CL": ("CL", 17, 35.453,  0.0, "A", 4.69906e-1, 7.69231e-2),
}

# TIP4P-ICE water atomtype parameters (name → tuple)
WATER_ATOMTYPES: dict[str, tuple[str, int, float, float, str, float, float]] = {
    "OW_ice": ("OW_ice", 8, 15.9994, 0.0, "A", TIP4P_ICE_OW_SIGMA, TIP4P_ICE_OW_EPSILON),
    "HW_ice": ("HW_ice", 1,  1.0080, 0.0, "A", 0.0, 0.0),
    "MW":     ("MW",     0,  0.0000, 0.0, "V", 0.0, 0.0),
}

MOLECULE_TO_GROMACS: dict[str, dict[str, str]] = {
    "ice":   {"res_name": "SOL", "itp_file": "tip4p-ice.itp", "mol_name": "SOL"},
    "water": {"res_name": "SOL", "itp_file": "tip4p-ice.itp", "mol_name": "SOL"},
    "na":    {"res_name": "NA",  "itp_file": "na.itp",     "mol_name": "NA"},
    "cl":    {"res_name": "CL",  "itp_file": "cl.itp",     "mol_name": "CL"},
    "ch4":   {"res_name": "CH4", "itp_file": "ch4_hydrate.itp", "mol_name": "CH4"},
    "thf":   {"res_name": "THF", "itp_file": "thf_hydrate.itp", "mol_name": "THF"},
    "co2":   {"res_name": "CO2", "itp_file": "co2.itp",    "mol_name": "CO2"},
    "h2":    {"res_name": "H2",  "itp_file": "h2.itp",     "mol_name": "H2"},
}


# Canonical atom order for guest molecules (matching .itp definitions)
# GenIce2 outputs atoms in different order than .itp expects
GUEST_ATOM_ORDER = {
    # CH4: .itp expects [C, H, H, H, H], GenIce2 outputs [H, H, H, H, C]
    "ch4": ["C", "H", "H", "H", "H"],
    # THF: .itp expects [O, CA, CA, CB, CB, H...], GenIce2 outputs [H... O first]
    # THF canonical order from thf.itp
    "thf": ["O", "CA", "CA", "CB", "CB"],
}


# Module-level registry for unique moleculetype naming
_registry = MoleculetypeRegistry()
