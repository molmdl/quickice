# Algorithm: CHILL and CHILL+

## What It Measures

CHILL (CHill Identification of Local Liquid) and its extension CHILL+ classify each water molecule's local structure as cubic ice (Ic), hexagonal ice (Ih), clathrate hydrate, interfacial (between crystal and liquid), or liquid. The classification is based on the number of "staggered" vs "eclipsed" bonds each molecule forms with its four nearest neighbors, determined via correlation of bond orientational order parameters.

**Key advantage over F3/F4**: CHILL+ simultaneously identifies ice AND clathrate hydrate phases, making it ideal for systems where both coexist (e.g., hydrate self-preservation, ice-to-hydrate conversion). It is also 5× faster than cage-recognition algorithms.

## Mathematical Definition

### Step 1: Local Bond Order Parameter q_lm

**Source**: Steinhardt et al., Phys. Rev. B 28, 784 (1983); ten Wolde et al., J. Phys. Chem. B 100, 11431 (1996)

For each water molecule *i* with *n_b* nearest neighbors (n_b = 4 for tetrahedral water):

```
q_lm(i) = (1/n_b) Σ_{j=1}^{n_b} Y_lm(θ_ij, φ_ij)
```

where:
- `Y_lm` are spherical harmonics of rank *l* and order *m*
- `θ_ij` and `φ_ij` are the polar and azimuthal angles of the bond vector **r_ij** (from *i* to neighbor *j*)
- The sum is over the *n_b* = 4 nearest oxygen neighbors (within 3.5 Å cutoff)
- CHILL/CHILL+ uses **l = 3** (some variants use l = 4)

The local orientational bond order parameter vector **q_l(i)** has 2l+1 = 7 complex components for l=3.

### Step 2: Bond Correlation c(i,j)

For a pair of bonded water molecules *i* and *j* (i.e., within 3.5 Å):

```
c(i,j) = Σ_{m=-l}^{l} q_lm(i) · q_lm*(j)
```

where `q_lm*(j)` is the complex conjugate. This is essentially the normalized dot product of the two order parameter vectors.

For l=3, this gives 7 terms in the sum.

### Step 3: Bond Classification (Staggered vs Eclipsed)

| Bond Type | CHILL+ Range | CHILL Range | Physical Meaning |
|-----------|-------------|-------------|-----------------|
| Staggered (S) | c(i,j) ≤ -0.8 | c(i,j) ≤ -0.8 | Neighbors of *i* block neighbors of *j* (like staggered ethane) |
| Eclipsed (E) | 0.25 ≥ c(i,j) ≥ -0.35 | -0.05 ≥ c(i,j) ≥ -0.2 | Neighbors of *i* and *j* visible to each other (like eclipsed ethane) |
| Unclassified | Otherwise | Otherwise | Neither clearly staggered nor eclipsed |

**Key CHILL+ improvement**: The eclipsed bond range is widened from [-0.2, -0.05] (CHILL) to [-0.35, 0.25] (CHILL+). This wider range:
1. Allows identification of clathrate hydrate (which has 4 eclipsed bonds)
2. Improves detection of hexagonal ice at temperatures up to melting (99% vs 67%)

### Step 4: Molecule Classification

| Structure | E (eclipsed) | S (staggered) | Neighbors | Notes |
|-----------|-------------|---------------|-----------|-------|
| Cubic ice (Ic) | 0 | 4 | 4 | All bonds staggered |
| Hexagonal ice (Ih) | 1 | 3 | 4 | 1 eclipsed (c-axis), 3 staggered (basal) |
| Interfacial ice | any | 2 | 4 | Must have ≥1 neighbor with >2 S bonds |
| Interfacial ice | 0 | 3 | 4 | Must have ≥1 neighbor with >1 S bond |
| Clathrate hydrate | 4 | 0 | 4 | All bonds eclipsed |
| Interfacial clathrate | 3 | any | 4 | Partial cages, clathrate "halo" |
| Liquid | N/A | N/A | ≠4 or other | Not fitting above categories |

**Cutoff**: O-O distance ≤ 3.5 Å for first coordination shell.

## Pseudocode / Implementation Sketch

```python
import numpy as np
from scipy.special import sph_harm

def compute_chill_plus(oxygen_positions, cell_matrix, cutoff=3.5, l=3):
    """
    CHILL+ algorithm for water structure classification.
    
    Args:
        oxygen_positions: (N, 3) array of oxygen positions (Angstroms)
        cell_matrix: (3, 3) simulation cell matrix
        cutoff: O-O neighbor cutoff (default 3.5 Å)
        l: order of spherical harmonics (default 3)
    
    Returns:
        classifications: (N,) array of ints
            0=Other/Liquid, 1=Hexagonal, 2=Cubic, 3=Interfacial ice,
            4=Clathrate, 5=Interfacial clathrate
    """
    N = len(oxygen_positions)
    
    # Step 1: Find 4 nearest neighbors for each molecule (PBC-aware)
    neighbors = find_4_nearest_neighbors(oxygen_positions, cell_matrix, cutoff)
    
    # Step 2: Compute q_lm for each molecule
    q_lm = np.zeros((N, 2*l+1), dtype=complex)
    for i in range(N):
        for m_idx, m in enumerate(range(-l, l+1)):
            q_lm[i, m_idx] = 0.0
            for j in neighbors[i]:
                # Bond vector i→j in PBC
                vec = pbc_vector(oxygen_positions[i], oxygen_positions[j], cell_matrix)
                # Convert to spherical coordinates
                r = np.linalg.norm(vec)
                theta = np.arccos(vec[2] / (r + 1e-10))  # polar angle
                phi = np.arctan2(vec[1], vec[0])           # azimuthal angle
                # Spherical harmonic
                q_lm[i, m_idx] += sph_harm(m, l, phi, theta)
            q_lm[i, m_idx] /= len(neighbors[i])  # normalize by neighbor count
    
    # Step 3: Compute bond correlation c(i,j) for bonded pairs
    bond_types = {}  # (i,j) -> 'S', 'E', or 'X'
    for i in range(N):
        for j in neighbors[i]:
            if (j, i) in bond_types:
                continue  # already computed
            c_ij = np.sum(q_lm[i] * np.conj(q_lm[j])).real
            # Normalize (optional, depends on implementation)
            # c_ij /= (np.linalg.norm(q_lm[i]) * np.linalg.norm(q_lm[j]) + 1e-10)
            
            if c_ij <= -0.8:
                bond_types[(i, j)] = 'S'
                bond_types[(j, i)] = 'S'
            elif -0.35 <= c_ij <= 0.25:
                bond_types[(i, j)] = 'E'
                bond_types[(j, i)] = 'E'
            else:
                bond_types[(i, j)] = 'X'
                bond_types[(j, i)] = 'X'
    
    # Step 4: Count staggered/eclipsed bonds per molecule
    n_staggered = np.zeros(N, dtype=int)
    n_eclipsed = np.zeros(N, dtype=int)
    n_neighbors = np.zeros(N, dtype=int)
    
    for i in range(N):
        for j in neighbors[i]:
            bt = bond_types.get((i, j), 'X')
            n_neighbors[i] += 1
            if bt == 'S':
                n_staggered[i] += 1
            elif bt == 'E':
                n_eclipsed[i] += 1
    
    # Step 5: Classify each molecule
    classifications = np.zeros(N, dtype=int)  # 0 = Other/Liquid
    
    for i in range(N):
        if n_neighbors[i] != 4:
            classifications[i] = 0  # Liquid (non-4-coordinated)
            continue
        
        E = n_eclipsed[i]
        S = n_staggered[i]
        
        if E == 4 and S == 0:
            classifications[i] = 4  # Clathrate hydrate
        elif E == 3:
            classifications[i] = 5  # Interfacial clathrate
        elif E == 1 and S == 3:
            classifications[i] = 1  # Hexagonal ice
        elif E == 0 and S == 4:
            classifications[i] = 2  # Cubic ice
        elif S == 2:
            # Interfacial ice: check neighbors
            has_ice_neighbor = any(n_staggered[j] > 2 for j in neighbors[i])
            classifications[i] = 3 if has_ice_neighbor else 0
        elif S == 3 and E == 0:
            # Could be interfacial: check neighbors
            has_ice_neighbor = any(n_staggered[j] > 1 for j in neighbors[i])
            classifications[i] = 3 if has_ice_neighbor else 0
        else:
            classifications[i] = 0  # Liquid/Other
    
    return classifications
```

## Feasibility Assessment

- **Lines of code**: ~200-300 (including neighbor search and spherical harmonics)
- **Complexity**: MEDIUM
- **Dependencies**: numpy, scipy (for `sph_harm`), MDAnalysis or `pairlist` for PBC neighbor search
- **Blockers**:
  - PBC-aware neighbor search with minimum image convention is critical
  - `scipy.special.sph_harm` computes spherical harmonics — straightforward
  - The correlation c(i,j) requires careful normalization
  - Need to handle the case where molecules have < 4 neighbors
- **Confidence**: HIGH (algorithm fully specified in the Nguyen & Molinero (2015) paper, verified against official source)

## Reference Implementations

| Source | Language | URL | Confidence |
|--------|----------|-----|------------|
| OVITO ChillPlusModifier | C++ | https://www.ovito.org/docs/current/reference/pipelines/modifiers/chill_plus.html | HIGH |
| LAMMPS (via compute orientorder/atom) | C++ | https://docs.lammps.org/compute_orientorder_atom.html | HIGH |
| Nguyen & Molinero (2015) paper | Algorithm spec | doi:10.1021/jp510289t | HIGH |
| Moore & Molinero (2010) CHILL original | Algorithm spec | doi:10.1039/b919724a | HIGH |

**No standalone Python CHILL+ implementation found on GitHub.** OVITO's C++ implementation is the only open-source one known. We would need to implement from scratch.

## Key Pitfalls

1. **Spherical harmonics normalization**: `scipy.special.sph_harm` uses the Condon-Shortley phase convention. Make sure the formula matches what the paper uses. Different conventions can give different signs for c(i,j), flipping the staggered/eclipsed classification.

2. **PBC and neighbor list**: The neighbor search must use the minimum image convention. For non-orthogonal cells, this requires the general formula: `d = r_i - r_j`, `d -= cell @ np.floor(cell_inv @ d + 0.5)`. The `pairlist` library (already a GenIce2 dependency) handles this.

3. **Exactly 4 neighbors**: The algorithm assumes 4-coordinated water. If a molecule has 3 or 5 neighbors within the 3.5 Å cutoff, it's automatically classified as liquid. This cutoff may need adjustment for different water models or densities.

4. **Interfacial classification requires neighbor check**: The interfacial ice category requires checking if any of the molecule's neighbors are already classified as ice. This creates a dependency: you need to classify some molecules first before classifying others. The paper resolves this by first classifying bulk (clear cases) then interfacial.

5. **Performance**: For large systems (100K+ waters), computing spherical harmonics for all 7 components of q_3 for all molecules is O(N × 4 × 7). This is manageable — the bottleneck is the neighbor search.

6. **Clathrate vs liquid false positives**: ~2-3% of liquid water molecules are classified as "clathrate" by CHILL+. The paper recommends filtering by cluster size (use the largest cluster of 3E+4E molecules for clathrate identification).

7. **Cannot distinguish clathrate polymorphs**: CHILL+ identifies "clathrate" as a class but cannot distinguish sI, sII, or sH. For polymorph identification, use cage recognition (see ALGO-CAGE.md).
