# Algorithm: F3 and F4 Order Parameters

## What It Measures

F3 and F4 are structural order parameters that quantify the local tetrahedral ordering and dihedral/torsional geometry of water molecules. They distinguish liquid water, ice, and clathrate hydrate phases based on how tetrahedral the local environment is (F3) and the rotational conformation of bonded pairs (F4).

- **F3**: Deviation from perfect tetrahedral angle (109.47°) in the O-O-O triplet angles. Perfect tetrahedral → F3 = 0.
- **F4**: Average dihedral/torsional angle correlation between bonded water molecules. Distinguishes staggered (ice) from eclipsed (hydrate) conformations.

## Mathematical Definition

### F3 Order Parameter

**Source**: Errington & Debenedetti, *Nature* 409, 335 (2001); Chau & Hardwick, *Mol. Phys.* 107, 637 (2009)

For each water molecule *i* with *n* nearest oxygen neighbors:

```
F3(i) = ∏_{j<k; j,k ∈ neighbors(i)} |cos(θ_{jik}) + 1/3|
```

where:
- `θ_{jik}` is the angle at oxygen *i* between neighbor oxygens *j* and *k*
- The product is over all unique pairs (j,k) of neighbors of *i*
- For perfect tetrahedral coordination (109.47°), cos(109.47°) = -1/3, so each factor = 0, giving F3 = 0
- For non-tetrahedral environments, each factor > 0, so F3 > 0

**Key property**: F3 = 0 for perfect tetrahedral; F3 > 0 for distorted tetrahedral.

### F4 Order Parameter (Dihedral/Torsional)

**Source**: Chau & Hardwick, *Mol. Phys.* 107, 637 (2009); Rodger et al.

For two hydrogen-bonded water molecules *i* and *j*, define the dihedral angle φ as:

```
φ = dihedral angle formed by:
    - Vector from j to neighbor k1 of i (in plane ⊥ to i-j axis)
    - Vector from i to neighbor l1 of j (in plane ⊥ to i-j axis)
```

Then:

```
F4 = ⟨cos(3φ)⟩
```

averaged over all bonded pairs in the system.

**Alternative definition** (Rodger et al., used in hydrate studies):
F4φ uses the O-O-O-O dihedral angle along the HB network:

```
F4 = ⟨cos(3φ_{OOOO})⟩
```

where `φ_{OOOO}` is the dihedral angle formed by four connected oxygen atoms.

## Classification Thresholds

| Phase | F3 | F4 | Notes |
|-------|-----|-----|-------|
| Ice Ih | ~0.0 | ~-0.4 | Staggered conformation (φ ≈ 60°, 180°, 300°) |
| Ice Ic | ~0.0 | ~-0.4 | Same staggered as Ih |
| Clathrate hydrate | ~0.0 | ~+0.7 to +0.8 | Eclipsed conformation (φ ≈ 0°, 120°, 240°) |
| Liquid water | ~0.1 | ~-0.15 to -0.2 | Mixed conformations |

**Important**: Thresholds vary slightly by water model (TIP3P, TIP4P, SPC/E, mW). The above values are general approximations. For mW coarse-grained model, values may differ slightly.

### F4-based hydrate identification rule (commonly used):
- F4 > +0.5 → hydrate-like
- F4 < -0.2 → ice-like
- -0.2 < F4 < +0.5 → liquid-like

⚠️ **MEDIUM confidence** on exact threshold values — from training data, not verified against official sources. Thresholds should be validated against test systems.

## Pseudocode / Implementation Sketch

```python
import numpy as np
from scipy.spatial import cKDTree

def compute_F3(oxygen_positions, cell_matrix, cutoff=3.5):
    """
    Compute F3 order parameter for each water molecule.
    
    Args:
        oxygen_positions: (N, 3) array of oxygen positions in Angstroms
        cell_matrix: (3, 3) cell matrix for PBC
        cutoff: O-O distance cutoff for neighbors (default 3.5 Å)
    
    Returns:
        f3_values: (N,) array of F3 values per molecule
    """
    N = len(oxygen_positions)
    f3_values = np.zeros(N)
    
    # Build neighbor list with PBC
    # Use pairlist or MDAnalysis for PBC-aware neighbor search
    # For each molecule i:
    for i in range(N):
        # Find all neighbors within cutoff (PBC-aware)
        neighbors = find_pbc_neighbors(i, oxygen_positions, cell_matrix, cutoff)
        
        if len(neighbors) < 3:
            f3_values[i] = np.nan  # insufficient neighbors
            continue
        
        # Compute all O-O-O angles at molecule i
        product = 1.0
        for j_idx in range(len(neighbors)):
            for k_idx in range(j_idx + 1, len(neighbors)):
                j, k = neighbors[j_idx], neighbors[k_idx]
                vec_ij = pbc_vector(oxygen_positions[i], oxygen_positions[j], cell_matrix)
                vec_ik = pbc_vector(oxygen_positions[i], oxygen_positions[k], cell_matrix)
                
                # Angle at i between j and k
                cos_theta = np.dot(vec_ij, vec_ik) / (
                    np.linalg.norm(vec_ij) * np.linalg.norm(vec_ik)
                )
                cos_theta = np.clip(cos_theta, -1.0, 1.0)
                
                # F3 factor: |cos(theta) + 1/3|
                factor = np.abs(cos_theta + 1.0/3.0)
                product *= factor
        
        f3_values[i] = product
    
    return f3_values


def compute_F4(oxygen_positions, cell_matrix, bond_cutoff=3.5):
    """
    Compute F4 order parameter (dihedral-based) for the system.
    
    Args:
        oxygen_positions: (N, 3) array of oxygen positions
        cell_matrix: (3, 3) cell matrix for PBC
        bond_cutoff: O-O distance cutoff for bonded pairs
    
    Returns:
        f4_system: scalar, average F4 for the system
        f4_per_bond: per-bond F4 values (for per-molecule classification)
    """
    N = len(oxygen_positions)
    
    # 1. Find bonded O-O pairs (HB network)
    bonded_pairs = find_bonded_pairs(oxygen_positions, cell_matrix, bond_cutoff)
    
    f4_values = []
    
    for i, j in bonded_pairs:
        # 2. Find neighbors of i (excluding j)
        neighbors_i = find_pbc_neighbors(i, oxygen_positions, cell_matrix, bond_cutoff)
        neighbors_i = [n for n in neighbors_i if n != j]
        
        # 3. Find neighbors of j (excluding i)
        neighbors_j = find_pbc_neighbors(j, oxygen_positions, cell_matrix, bond_cutoff)
        neighbors_j = [n for n in neighbors_j if n != i]
        
        if len(neighbors_i) < 2 or len(neighbors_j) < 2:
            continue  # need at least 2 other neighbors each
        
        # 4. Compute dihedral angle O_k - O_i - O_j - O_l
        # Pick two neighbors k of i and two neighbors l of j
        k = neighbors_i[0]  # simplest: first neighbor
        l = neighbors_j[0]
        
        vec_ki = pbc_vector(oxygen_positions[k], oxygen_positions[i], cell_matrix)
        vec_ij = pbc_vector(oxygen_positions[i], oxygen_positions[j], cell_matrix)
        vec_jl = pbc_vector(oxygen_positions[j], oxygen_positions[l], cell_matrix)
        
        # Dihedral angle via cross products
        b1 = np.cross(vec_ki, vec_ij)
        b2 = np.cross(vec_ij, vec_jl)
        
        cos_phi = np.dot(b1, b2) / (
            np.linalg.norm(b1) * np.linalg.norm(b2) + 1e-10
        )
        cos_phi = np.clip(cos_phi, -1.0, 1.0)
        
        f4_values.append(np.cos(3 * np.arccos(cos_phi)))
    
    f4_per_bond = np.array(f4_values)
    f4_system = np.mean(f4_per_bond) if len(f4_per_bond) > 0 else 0.0
    
    return f4_system, f4_per_bond
```

## Feasibility Assessment

- **Lines of code**: ~150-250 (including PBC-aware neighbor search)
- **Complexity**: MEDIUM
- **Dependencies**: numpy, scipy (KDTree for neighbor search), or MDAnalysis for trajectory I/O and PBC
- **Blockers**: 
  - PBC-aware neighbor search is critical and non-trivial — can use `pairlist` library (already in QuickIce's GenIce2 deps) or MDAnalysis
  - F4 dihedral computation requires careful handling of hydrogen bond network identification
  - Thresholds may need tuning per water model
- **Confidence**: MEDIUM (formulas well-established in literature but exact implementation details for F4 dihedral atom selection need validation)

## Reference Implementations

| Source | Language | URL | Confidence |
|--------|----------|-----|------------|
| OVITO (CHILL+ includes q3 correlation) | C++ | https://www.ovito.org/docs/current/reference/pipelines/modifiers/chill_plus.html | HIGH |
| LAMMPS compute orientorder/atom | C++ | https://docs.lammps.org/compute_orientorder_atom.html | HIGH |
| CHILL+ paper (Nguyen & Molinero, JPCB 2015) | Fortran/LAMMPS input | doi:10.1021/jp510289t | HIGH |
| MDAnalysis (density, HBond) | Python | https://www.mdanalysis.org/ | HIGH |

**No complete standalone Python F3/F4 implementation found on GitHub.** This is a known gap — researchers typically implement these locally or use LAMMPS/OVITO.

## Key Pitfalls

1. **PBC handling**: The most common source of bugs. Neighbor search must correctly account for minimum image convention. Use existing libraries (`pairlist`, `MDAnalysis.lib.distances`, `scipy.spatial`) rather than rolling your own.

2. **Neighbor count sensitivity**: F3 is a product over all neighbor pairs. If a 5th or 6th neighbor is included (shouldn't be, in tetrahedral water), the product blows up. **Always use exactly the 4 nearest neighbors for water systems.**

3. **F4 dihedral atom selection ambiguity**: The dihedral requires selecting which neighbor of molecule *i* and which neighbor of molecule *j* to use. Different papers use different conventions. Some average over all possible neighbor choices, others pick the first. This must be consistent with the reference implementation.

4. **Threshold model-dependence**: TIP3P, TIP4P, SPC/E, and mW water models have slightly different F3/F4 distributions. Thresholds calibrated for one model may not work for another. Always calibrate against known phase reference systems.

5. **Temperature effects**: At higher temperatures (near melting), F4 distributions broaden significantly. A fixed threshold becomes less reliable. Consider using adaptive thresholds or probability-based classification.

6. **F4 requires hydrogen bond network**: F4 is defined for bonded O-O pairs. The neighbor cutoff (3.5 Å) and whether to use strict HB criteria (O-H...O) vs. simple O-O distance affects results.

7. **Speed for large systems**: For 10,000+ water molecules, the O(N²) neighbor search is the bottleneck. Use KDTree or cell-list methods from `pairlist` or MDAnalysis.
