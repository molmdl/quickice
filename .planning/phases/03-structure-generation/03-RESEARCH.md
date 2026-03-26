# Phase 3: Structure Generation - Research

**Researched:** 2026-03-26
**Domain:** GenIce integration for ice structure coordinate generation
**Confidence:** HIGH

## Summary

This phase integrates GenIce (version 2.2.13.1) to generate valid hydrogen-disordered ice structures from Phase 2's phase identification. GenIce automatically ensures exactly 4 hydrogen bonds per water molecule (ice rule), eliminating the need for custom hydrogen bond network generation. The key implementation decisions involve mapping Phase 2's phase_id to GenIce lattice names, handling supercell sizing to meet molecule count requirements, and generating 10 diverse candidates using different random seeds.

**Primary recommendation:** Use GenIce API directly with `genice2.plugin.safe_import()` to load lattice and format modules. Generate candidates by varying the random seed (--seed option), which produces different hydrogen bond network configurations while maintaining the same phase structure. Map Phase 2's `phase_id` (e.g., "ice_ih") to GenIce lattice names (e.g., "ice1h", "1h", "Ih") via a lookup dictionary.

## Standard Stack

The established libraries for ice structure generation:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| genice2 | 2.2.13.1 | Ice structure generation | Primary tool for hydrogen-disordered ice |
| genice-core | 1.4.3 | Core ice graph algorithm | Required by genice2 |
| numpy | ^2.0 | Array operations | Used internally by GenIce |
| networkx | >=2.0 | Graph operations | Used for HB network |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| spglib | 2.7.0 | Space group validation | Phase 5 (not needed here) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| genice2 CLI | Direct Python API | API allows programmatic control over seeds/formats |
| GRO format | PDB, CIF, XYZ | GRO is standard for MD; PDB better for visualization |

**Installation:**
```bash
# Already in environment.yml per CONTEXT.md
# genice2==2.2.13.1
# genice-core==1.4.3
```

## Architecture Patterns

### Recommended Project Structure
```
quickice/
├── structure_generation/
│   ├── __init__.py
│   ├── generator.py      # Main GenIce wrapper
│   ├── mapper.py         # Phase ID → GenIce lattice name
│   └── types.py          # Candidate dataclasses
```

### Pattern 1: GenIce API Usage
**What:** Programmatic GenIce invocation via Python API instead of CLI

**When to use:** Always - provides fine-grained control over seeds, formats, and supercell sizing

**Example:**
```python
# Source: Based on GenIce genice.py and CLI analysis
import numpy as np
from genice2.plugin import safe_import
from genice2.genice import GenIce

# Load lattice (ice phase)
lattice_type, lattice_options = plugin_option_parser("ice1h")  # "ice1h" maps from phase_id
lat = safe_import("lattice", lattice_type).Lattice(**lattice_options)

# Create GenIce instance with supercell sizing
ice = GenIce(
    lat=lat,
    density=0.92,  # Can use phase density from Phase 2
    reshape=np.diag([3, 3, 3]),  # 3x3x3 supercell
)

# Load water model and format
water = safe_import("molecule", "tip3p").Molecule()
formatter = safe_import("format", "gromacs").Format()

# Generate structure
result = ice.generate_ice(
    formatter=formatter,
    water=water,
    depol="strict",  # Ensures zero net dipole
)

# result contains GRO format string
```

### Pattern 2: Phase ID to GenIce Lattice Mapping
**What:** Convert Phase 2's `phase_id` (e.g., "ice_ih") to GenIce lattice names

**When to use:** Required for every generation call

**Example:**
```python
# Phase ID mapping based on GenIce lattice names
PHASE_TO_GENICE = {
    "ice_ih": "ice1h",    # Also accepts: "1h", "Ih", "HS1"
    "ice_ic": "ice1c",    # Also accepts: "1c", "Ic"
    "ice_ii": "ice2",     # Also accepts: "2", "II"
    "ice_iii": "ice3",    # Also accepts: "3", "III"
    "ice_v": "ice5",      # Also accepts: "5", "V"
    "ice_vi": "ice6",     # Also accepts: "6", "VI"
    "ice_vii": "ice7",    # Also accepts: "7", "VII"
    "ice_viii": "ice8",   # Also accepts: "8", "VIII"
}
```

### Pattern 3: Supercell Sizing Calculation
**What:** Calculate reshape matrix to achieve target molecule count

**When to use:** When user specifies nmolecules requirement

**Example:**
```python
# Source: GenIce genice.py reshape logic
import numpy as np

def calculate_reshape_matrix(target_molecules: int, molecules_per_unit_cell: int) -> np.ndarray:
    """
    Calculate reshape matrix to achieve target molecule count.
    
    The supercell molecules = det(reshape) × molecules_per_unit_cell
    """
    # Find smallest integer multiplier
    multiplier = 1
    while molecules_per_unit_cell * multiplier < target_molecules:
        multiplier += 1
    
    # Factor into 3D - use cube root for roughly cubic supercell
    cube_n = int(round(multiplier ** (1/3)))
    if cube_n ** 3 == multiplier:
        return np.diag([cube_n, cube_n, cube_n])
    
    # Otherwise use linear factors
    a = b = c = 1
    while a * b * c < multiplier:
        if a * b * c * (a + 1) <= multiplier:
            a += 1
        elif a * b * c * (b + 1) <= multiplier:
            b += 1
        else:
            c += 1
    
    return np.diag([a, b, c])
```

### Pattern 4: Multiple Candidate Generation
**What:** Generate 10 candidates using different random seeds

**When to use:** Required by ROADMAP - 10 candidates per query

**Example:**
```python
# Source: GenIce CLI --seed option
def generate_candidates(phase_info: dict, nmolecules: int, num_candidates: int = 10) -> list:
    """
    Generate multiple ice structure candidates.
    
    Different seeds produce different hydrogen bond network configurations
    while maintaining the same crystal structure and ice rule compliance.
    """
    candidates = []
    for seed in range(1000, 1000 + num_candidates):
        np.random.seed(seed)  # Set seed before GenIce initialization
        # ... GenIce generation code ...
        candidates.append({
            "structure": gro_string,
            "seed": seed,
            "nmolecules": actual_molecule_count,
        })
    return candidates
```

### Anti-Patterns to Avoid
- **Using CLI via subprocess:** Avoid `subprocess.run(["genice2", ...])` - use Python API for better control
- **Ignoring double_network flag:** Ice VI and VII have `double_network = True` (two interpenetrating networks), affects molecule count
- **Assuming exact molecule count:** GenIce supercell sizing rounds up; inform user when adjustment occurs

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Hydrogen bond network | Custom graph algorithms | GenIce genice-core | GenIce ensures exactly 4 H-bonds/molecule (ice rule) |
| Supercell generation | Manual cell replication | GenIce reshape matrix | Handles periodic boundary conditions correctly |
| Multiple candidates | Random coordinate perturbation | Different GenIce seeds | Seeds produce statistically independent configurations |
| Output formatting | Custom PDB/GRO writers | GenIce formatters | Formatters handle all edge cases (atom IDs, box vectors) |

**Key insight:** GenIce is a mature, well-tested tool specifically designed for ice structure generation. The hydrogen bond orientation algorithm in genice-core ensures proton disorder while maintaining zero net dipole moment. Building custom solutions would require replicating this complex graph theory logic.

## Common Pitfalls

### Pitfall 1: Incorrect Phase ID Mapping
**What goes wrong:** GenIce fails with "module not found" or generates wrong crystal structure

**Why it happens:** Phase 2 returns "ice_ih" but GenIce expects "ice1h" or "1h"

**How to avoid:** Use explicit mapping dictionary; GenIce accepts multiple aliases

**Warning signs:** GenIceImportError, unexpected crystal symmetry

### Pitfall 2: Supercell Molecule Count Mismatch
**What goes wrong:** Generated structure has different molecule count than requested

**Why it happens:** GenIce supercell = unit_cell × reshape_det; rounds up automatically

**How to avoid:** Calculate reshape matrix explicitly; inform user of adjustments

**Warning signs:** nmolecules parameter not exactly matched

### Pitfall 3: Seed-Based Duplicate Configurations
**What goes wrong:** Multiple seeds produce identical or nearly identical configurations

**Why it happens:** GenIce's graph generation may have limited state space for some phases

**How to avoid:** Verify candidate uniqueness; may need additional randomization (e.g., rotate unit cell)

**Warning signs:** 10 candidates with >90% similarity in HB network

### Pitfall 4: Ignoring Density Parameter
**What goes wrong:** Generated structure has wrong density, affecting simulation validity

**Why it happens:** GenIce defaults to lattice-specific density; Phase 2 provides density

**How to pass:** Use Phase 2's `density` value in GenIce `density` parameter

**Warning signs:** Unexpected lattice constants

## Code Examples

### Complete Generation Workflow
```python
# Source: Based on GenIce genice.py and plugin.py analysis
from genice2.plugin import safe_import, plugin_option_parser
from genice2.genice import GenIce
import numpy as np
from dataclasses import dataclass
from typing import Optional

@dataclass
class IceStructureCandidate:
    """Represents a generated ice structure candidate."""
    structure: str  # GRO format string
    seed: int
    nmolecules: int
    phase_id: str
    lattice_name: str

# Phase ID to GenIce lattice name mapping
PHASE_TO_GENICE = {
    "ice_ih": "ice1h",
    "ice_ic": "ice1c", 
    "ice_ii": "ice2",
    "ice_iii": "ice3",
    "ice_v": "ice5",
    "ice_vi": "ice6",
    "ice_vii": "ice7",
    "ice_viii": "ice8",
}

# Molecules per unit cell for each phase
UNIT_CELL_MOLECULES = {
    "ice1h": 4,
    "ice1c": 8,
    "ice2": 12,
    "ice3": 12,
    "ice5": 28,
    "ice6": 10,  # double_network
    "ice7": 16,  # double_network
    "ice8": 16,  # double_network
}

def generate_structures(
    phase_info: dict,
    target_molecules: int,
    num_candidates: int = 10,
) -> list[IceStructureCandidate]:
    """
    Generate ice structure candidates using GenIce.
    
    Args:
        phase_info: Output from Phase 2 lookup_phase()
        target_molecules: Desired number of water molecules
        num_candidates: Number of candidates to generate (default: 10)
    
    Returns:
        List of IceStructureCandidate objects
    """
    phase_id = phase_info["phase_id"]
    density = phase_info["density"]
    
    # Map to GenIce lattice name
    lattice_name = PHASE_TO_GENICE.get(phase_id)
    if lattice_name is None:
        raise ValueError(f"Unsupported phase: {phase_id}")
    
    # Calculate supercell size
    molecules_per_uc = UNIT_CELL_MOLECULES.get(lattice_name, 4)
    multiplier = 1
    while molecules_per_uc * multiplier < target_molecules:
        multiplier += 1
    
    # Use cubic-like factorization
    cube_n = int(round(multiplier ** (1/3))) if multiplier > 1 else 1
    if cube_n ** 3 <= multiplier:
        reshape = np.diag([cube_n, cube_n, cube_n])
    else:
        # Linear expansion
        reshape = np.diag([multiplier, 1, 1])
    
    candidates = []
    base_seed = 1000
    
    for i in range(num_candidates):
        seed = base_seed + i
        np.random.seed(seed)
        
        # Load lattice
        lat = safe_import("lattice", lattice_name).Lattice()
        
        # Create GenIce instance
        ice = GenIce(
            lat=lat,
            density=density,
            reshape=reshape,
        )
        
        # Load water model and format
        water = safe_import("molecule", "tip3p").Molecule()
        formatter = safe_import("format", "gromacs").Format()
        
        # Generate structure
        gro_string = ice.generate_ice(
            formatter=formatter,
            water=water,
            depol="strict",
        )
        
        # Count actual molecules
        actual_molecules = molecules_per_uc * np.linalg.det(reshape)
        
        candidates.append(IceStructureCandidate(
            structure=gro_string,
            seed=seed,
            nmolecules=int(actual_molecules),
            phase_id=phase_id,
            lattice_name=lattice_name,
        ))
    
    return candidates
```

### Parsing GRO Output
```python
# Source: GenIce formats/gromacs.py
def parse_gro(gro_string: str) -> dict:
    """
    Parse GRO format output from GenIce.
    
    Returns:
        Dictionary with atoms, box_vectors, nmolecules
    """
    lines = gro_string.strip().split("\n")
    
    # Header line + nmolecules line
    nmolecules = int(lines[1])
    
    # Atom lines (lines 2 to nmolecules+1)
    atoms = []
    for line in lines[2:nmolecules+2]:
        resno = int(line[0:5])
        resname = line[5:10].strip()
        atomname = line[10:15].strip()
        atomno = int(line[15:20])
        x = float(line[20:28])
        y = float(line[28:36])
        z = float(line[36:44])
        atoms.append({
            "resno": resno,
            "resname": resname,
            "atomname": atomname,
            "atomno": atomno,
            "x": x, "y": y, "z": z,
        })
    
    # Box vector line
    box_line = lines[-1]
    box_vectors = [float(x) for x in box_line.split()]
    
    return {
        "atoms": atoms,
        "nmolecules": nmolecules,
        "box_vectors": box_vectors,
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom HB network generation | GenIce genice-core algorithm | GenIce 2.0+ | Automatic ice rule compliance |
| Fixed unit cells | Programmatic reshape matrix | GenIce 2.0+ | Flexible supercell sizing |
| CLI subprocess | Python API | GenIce 2.0+ | Fine-grained control |
| Single structure | Seed-based multiple candidates | GenIce 2.0+ | Candidate diversity |

**Deprecated/outdated:**
- GenIce 1.x CLI-only interface: Replaced by Python API in 2.0
- Manual hydrogen bond orientation: Replaced by genice-core algorithm

## Open Questions

Things that couldn't be fully resolved:

1. **Candidate Uniqueness Verification**
   - What we know: Different seeds produce different HB configurations
   - What's unclear: How to quantify "different enough" for ML ranking
   - Recommendation: Include RMSD calculation or HB network graph comparison in Phase 4

2. **Supercell Shape Optimization**
   - What we know: Current implementation uses simple diagonal reshape
   - What's unclear: Whether non-cubic supercells affect simulation quality
   - Recommendation: Default to cubic-like; allow user preference for non-cubic

3. **Lower Bound Handling (nmolecules < minimum viable)**
   - What we know: Some phases have large unit cells (ice5 = 28 molecules)
   - What's unclear: How to handle user requesting < 8 molecules
   - Recommendation: Return error with minimum viable count for phase

4. **Metadata Requirements**
   - What we know: Phase 2 provides density, phase_id, phase_name
   - What's unclear: What additional metadata to store with candidate
   - Recommendation: Store seed, actual nmolecules, reshape matrix, generation timestamp

## Sources

### Primary (HIGH confidence)
- GenIce2 GitHub README - https://github.com/genice-dev/GenIce2
- GenIce genice.py source - Internal code analysis
- GenIce plugin.py source - Lattice/format loading mechanism
- GenIce formats/gromacs.py - Output format handling

### Secondary (MEDIUM confidence)
- GenIce lattices (ice1h.py, ice6.py, ice7.py) - Unit cell molecule counts
- Phase mapping lookup.py - Output format from Phase 2

### Tertiary (LOW confidence)
- None - All sources verified via direct code examination

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - genice2 is the standard tool for ice structure generation
- Architecture: HIGH - Direct API usage patterns verified via code analysis
- Pitfalls: MEDIUM - Some edge cases (unique seeds, lower bounds) require validation

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (genice2 is stable; only minor version updates expected)