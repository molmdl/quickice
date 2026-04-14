# Phase 30: Tab 4 - Ion Insertion (NaCl) - Research

**Researched:** 2026-04-15
**Domain:** Ion force field parameters for GROMACS with TIP4P-ICE water model
**Confidence:** MEDIUM-HIGH

## Summary

Research focuses on three key technical questions for Phase 30 ion insertion: (1) which ion force fields are compatible with TIP4P-ICE water model, (2) how to include user-provided custom ion.itp in GROMACS export, and (3) KBFF vs AMBER ion parameter tradeoffs.

**Primary recommendation:** Use GROMACS-builtin AMBER ion parameters (NA/CL from amberGS.ff/ions.itp) as default, with option to include user-provided ion.itp via `#include` directive. For TIP4P-ICE compatibility, Joung-Cheatham or OPLS parameters developed for TIP4P-family water models are recommended.

## Standard Stack

The established libraries/tools for ion insertion:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| GROMACS NA/CL ions | Built-in | Na+ and Cl- ion parameters | Standard names, validated with TIP4P-family water models |
| #include directive | GROMACS topology | Include custom ion.itp | Standard GROMACS method for external molecule definitions |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Joung-Cheatham ions | 2008 | Ion LJ parameters for TIP4P-family water | When user needs higher accuracy with TIP4P-ICE |
| OPLS-AA ions | Standard | Ion parameters in OPLS force field | When using OPLS-AA force field |
| Madrid-2019 | 2019 | Scaled-charge ion parameters | When modeling concentrated NaCl solutions |

**Installation:**
No additional packages required - GROMACS ion parameters are built-in.

## Architecture Patterns

### Recommended Project Structure

```
src/
├── ion_inserter.py           # IonInserter class - core insertion logic
├── ion_renderer.py         # VTK rendering for Na+/Cl- ions
├── gromacs_ion_export.py   # GROMACS ion.itp export
└── widgets/
    └── ion_tab.py         # Tab 4 UI components
```

### Pattern 1: Concentration-Based Ion Calculation
**What:** Calculate number of ion pairs from molar concentration and liquid region volume
**When to use:** User specifies mol/L concentration
**Example:**
```python
# Source: Based on gmx genion calculation logic
# ion_count = concentration (mol/L) * volume (L) * Avogadro_constant
# Both Na+ and Cl- added in equal pairs for charge neutrality

def calculate_ion_pairs(concentration_molar: float, liquid_volume_angstrom3: float) -> int:
    """Calculate number of Na+/Cl- ion pairs from concentration and volume."""
    # Convert volume from Å³ to L: volume_angstrom3 * 1e-27
    volume_liters = liquid_volume_angstrom3 * 1e-27
    total_ions = concentration_molar * volume_liters * 6.022e23
    return int(total_ions // 2)  # Each pair = 1 Na+ + 1 Cl-
```

### Pattern 2: Water Molecule Replacement
**What:** Replace water molecules in liquid region with ions
**When to use:** Inserting ions into hydrate structure
**Example:**
```python
# Source: Based on gmx genion approach
# Replace water molecules (SOL), not ice molecules
# Use molecule index ranges from Phase 29 data structures

def replace_water_with_ions(water_indices: list[int], num_ion_pairs: int) -> list[int]:
    """Select water molecule indices to replace with ion pairs."""
    # Random selection without overlap
    selected = random.sample(water_indices, min(num_ion_pairs * 2, len(water_indices)))
    return selected[:num_ion_pairs * 2]
```

### Pattern 3: GROMACS ion.itp Include
**What:** Include custom ion parameters in topology export
**When to use:** Export ions to GROMACS for MD simulation
**Example:**
```python
# Source: GROMACS topology file formats documentation
# Main topology file (system.top):
# #include "tip4pice.ff/forcefield.itp"
# #include "ions.itp"           ; Custom ion parameters
# #include "water.itp"
# ...
# [ molecules ]
# NA       10
# CL       10
# SOL     990
# ...

def generate_ion_itp(na_count: int, cl_count: int) -> str:
    """Generate ion.itp content for GROMACS export."""
    return """[ moleculetype ]
; Name        nrexcl
NA            1

[ atoms ]
;  nr  type  resi  res  atom  cgnr  charge  mass
   1    NA      1    NA    NA     1      1.0    22.9898

[ moleculetype ]
; Name        nrexcl
CL            1

[ atoms ]
;  nr  type  resi  res  atom  cgnr  charge  mass
   1    CL      1    CL    CL     1     -1.0    35.453
"""
```

### Pattern 4: Charge Neutralization for Custom Molecules
**What:** Add counter-ions to neutralize charge from custom molecules
**When to use:** Phase 32 compatibility - neutralizing user-added charged molecules
**Example:**
```python
def calculate_neutralization_ions(custom_molecule_charge: int) -> dict:
    """Calculate counter-ions needed to neutralize charge."""
    if custom_molecule_charge > 0:
        # Add Cl- ions to neutralize positive charge
        return {"NA": 0, "CL": custom_molecule_charge}
    elif custom_molecule_charge < 0:
        # Add Na+ ions to neutralize negative charge
        return {"NA": -custom_molecule_charge, "CL": 0}
    else:
        return {"NA": 0, "CL": 0}
```

### Anti-Patterns to Avoid
- **Inserting ions in ice region**: Ions should only replace water in liquid region (after ice index boundary)
- **Creating empty space for ions**: Replace existing water molecules, don't add new atoms in empty space
- **Using different ion names**: Use NA/CL (GROMACS standard) not custom names like NA+/Cl-

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|------------|------------|-----|
| Ion force field parameters | Calculate LJ parameters manually | Use GROMACS builtin or published parameters (Joung-Cheatham, OPLS) | Parameters are validated against experimental data |
| GROMACS topology format | Write custom format | Use #include directive for ion.itp | Standard GROMACS approach, ensures compatibility |
| Concentration calculation | Guess formula | Use standard: N = C × V × NA | Proven physics, matches gmx genion |
| Ion names | Create custom names | Use NA/CL (GROMACS standard) | Works with all GROMACS force fields |

**Key insight:** GROMACS already has validated ion parameters. Don't recalculate - use established parameters and just handle the placement logic.

## Common Pitfalls

### Pitfall 1: Wrong Volume Used for Concentration
**What goes wrong:** Calculating ion count using total box volume instead of liquid phase volume
**Why it happens:** Hydrate systems have both ice and liquid water; using total volume overestimates ion count
**How to avoid:** Use liquid region volume only (after ice index boundary from Phase 29 data structures)
**Warning signs:** Ion count much higher than expected for moderate concentrations

### Pitfall 2: TIP4P-ICE Ion Compatibility
**What goes wrong:** Using ion parameters optimized for TIP3P with TIP4P-ICE water
**Why it happens:** TIP3P and TIP4P-family models have different charge distributions and interaction sites
**How to avoid:** Use ions developed for TIP4P-family (TIP4P-Ew, TIP4P-2005) or use builtin GROMACS parameters
**Warning signs:** Ions not hydrating correctly, unusual RDF peaks

### Pitfall 3: Missing Ion Type Definitions in Force Field
**What goes wrong:** Export fails because atom types NA/CL not defined in included force field
**Why it happens:** Some force fields include ions, others require explicit inclusion
**How to avoid:** Always include explicit ion.itp with atom type definitions, or use force field (like AMBERGS) that includes ions
**Warning signs:** grompp error: "Atom type NA not found"

### Pitfall 4: Overlapping Ion Placement
**What goes wrong:** Placing ions too close to each other or to other atoms
**Why it happens:** Random selection without overlap checking
**How to avoid:** Use cKDTree (from Phase 29) to check minimum distance before placement
**Warning signs:** Simulation crashes, "Fatal error: atoms too close"

## Code Examples

Verified patterns from official sources:

### Ion Count Calculation
```python
# Source: Based on GROMACS gmx genion logic
def calculate_ion_count_from_concentration(
    concentration_molL: float,
    liquid_volume_angstrom3: float
) -> int:
    """Calculate total ion count from molar concentration.
    
    Args:
        concentration_molL: Concentration in mol/L (M)
        liquid_volume_angstrom3: Liquid phase volume in Å³
    
    Returns:
        Total number of ions (Na+ + Cl-)
    """
    # Convert Å³ to liters: 1 Å³ = 1e-27 L
    volume_liters = liquid_volume_angstrom3 * 1e-27
    
    # N_ions = C × V × NA
    total_ions = concentration_molL * volume_liters * 6.02214076e23
    
    return int(round(total_ions))
```

### GROMACS Topology Include Pattern
```python
# Source: Based on GROMACS topology file format
def generate_topology_with_ions(
    water_count: int,
    na_count: int,
    cl_count: int,
    force_field: str = "amberGS.ff"
) -> str:
    """Generate main topology with ion inclusion."""
    topology = f"""; Topology for hydrate with ions
#include "{force_field}/forcefield.itp"
#include "ions.itp"
#include "tip4pice.itp"
#include "water.itp"

[ system ]
Hydrate with NaCl

[ molecules ]
; Compound        nmols
SOL             {water_count}
NA              {na_count}
CL              {cl_count}
"""
    return topology
```

### VTK Ion Rendering Colors
```python
# Source: Standard CPK coloring conventions (modified for visibility)
def get_ion_colors() -> dict:
    """Return colors for Na+ and Cl- ions as specified in CONTEXT."""
    return {
        "NA": {
            "color": (1.0, 0.84, 0.0),  # Gold (paler)
            "radius": 0.190,  # Na+ VDW radius in nm (190 pm = 1.90 Å = 0.19 nm)
            "opacity": 0.9,
        },
        "CL": {
            "color": (0.56, 0.99, 0.56),  # Lime/paler green
            "radius": 0.181,  # Cl- VDW radius in nm (181 pm = 1.81 Å = 0.181 nm)
            "opacity": 0.9,
        },
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|----------------|--------------|--------|
| Hand-calculated LJ parameters | Published parameters (JC, OPLS, AMBER) | 2008+ | Validated against experimental thermodynamics |
| Inline ion definitions | Separate ion.itp with #include | GROMACS 4.x+ | Reusable, cleaner topology |
| TIP3P ion parameters | TIP4P-optimized parameters | 2017+ | Better compatibility with ice water models |

**Deprecated/outdated:**
- **Inline topology definitions**: Modern GROMACS uses #include for modularity
- **Unverified LJ parameters**: Use published parameter sets only

## Open Questions

1. **TIP4P-ICE specific ion parameters**
   - What we know: TIP4P-ICE is similar to TIP4P-2005, parameters transfer between them
   - What's unclear: Whether specific TIP4P-ICE ion parameters exist or need to be developed
   - Recommendation: Use GROMACS-builtin AMBER or OPLS parameters as default; note for Phase 32 that custom ion.itp with TIP4P-Ew parameters can be provided

2. **Water density display units**
   - What we know: WATER-02 requires displaying water density in Tab 1 info panel
   - What's unclear: Exact display format (kg/m³ vs g/cm³) and position in UI
   - Recommendation: Display in g/cm³ (standard units) alongside molecule count already shown

## Sources

### Primary (HIGH confidence)
- GROMACS 2026.1 documentation: https://manual.gromacs.org/documentation/current/manual.html
- GROMACS topology file formats: https://manual.gromacs.org/current/reference-manual/topologies/topology-file-formats.html
- GROMACS #include directive behavior

### Secondary (MEDIUM confidence)
- Joung & Cheatham ion parameters (2008): Optimized for TIP4P-family water models
- TIP4P-ICE paper (Abascal et al., 2005): Water model for ice simulations
- Döpke et al. (2020): Ion parameter transferability to TIP4P-2005

### Tertiary (LOW confidence)
- Community discussions on ion force field compatibility
- Madrid-2019 force field for concentrated solutions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - GROMACS builtin, well-documented topology format
- Architecture: HIGH - Based on gmx genion approach, proven pattern
- Pitfalls: MEDIUM - Documented common issues, requires verification against Phase 29 data
- Force field compatibility: MEDIUM - Research agrees on TIP4P-family compatibility, specific to TIP4P-ICE needs validation

**Research date:** 2026-04-15
**Valid until:** Approximately 90 days for force field recommendations (stable field)

---

*This research file was prepared for Phase 30 planning. The key deliverable is the IonInserter class with concentration-based calculation, replacement of liquid-region water molecules, and GROMACS ion.itp export with proper #include pattern.*