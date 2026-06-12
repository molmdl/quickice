# Algorithm: Cage Occupancy and Detection

## What It Measures

Cage detection identifies the polyhedral cages (5¹², 5¹²6², 5¹²6³, 5¹²6⁴, etc.) formed by water molecules in clathrate hydrate structures. Cage occupancy determines whether each cage contains a guest molecule and tracks which guest is in which cage over time.

This is the **hardest** analysis task for hydrate simulations, but **GenIce2 dramatically simplifies it** by providing cage center positions at structure generation time.

## Approaches to Cage Detection

### Approach 1: Coordinate-Based (RECOMMENDED for QuickIce)

**Critical insight from GenIce2 source code investigation**: GenIce2's lattice modules **already define cage center positions and cage types** for every supported hydrate structure.

**Evidence from GenIce2 source** (HIGH confidence, verified directly):

```python
# From genice2/lattices/CS1.py (sI clathrate):
self.cagepos, self.cagetype = parse_cages("""
    12    0.5000    0.5000    0.5000     # 5^12 small cage
    12    1.0000    1.0000    0.0000     # 5^12 small cage
    14    0.5000    0.7500    0.0000     # 5^12 6^2 large cage
    14    0.5000    0.2500    0.0000     # 5^12 6^2 large cage
    ...
""")
```

**How it works for QuickIce**:

1. **At generation time**: GenIce2 stores `cagepos` (fractional coordinates) and `cagetype` for each cage
2. **When replicating**: GenIce2 creates `repcagepos` and `repcagetype` for the full simulation cell (see `genice.py` Stage1, line 828-851)
3. **When placing guests**: GenIce2 uses `repcagepos[cage_id]` as the center of each cage
4. **In the `raw` format**: GenIce2 can output these positions

**Implementation strategy for post-MD analysis**:
1. Save cage center positions from GenIce2 output when generating the initial structure
2. During MD, track which guest molecule is closest to each cage center
3. A guest is "occupying" a cage if its distance from the cage center < cage radius threshold
4. This avoids the entire cage detection problem during analysis

**Cage radii (approximate, from crystallography)**:

| Cage Type | Notation | Face Topology | Radius (Å) | Structure |
|-----------|----------|---------------|-------------|-----------|
| Small cage | 5¹² | 12 pentagons | ~3.9 | sI, sII, sH |
| Large cage (sI) | 5¹²6² | 12 pent + 2 hex | ~4.3 | sI |
| Large cage (sII) | 5¹²6⁴ | 12 pent + 4 hex | ~4.7 | sII |
| Medium cage (sH) | 4³5⁶6³ | 3 sq + 6 pent + 3 hex | ~4.0 | sH |
| Large cage (sH) | 5¹²6⁸ | 12 pent + 8 hex | ~5.7 | sH |

### Approach 2: Topological Cage Detection (GenIce2's `assess_cages`)

GenIce2 already has a built-in cage detection algorithm in `genice2/cage.py`:

```python
def assess_cages(graph, node_frac):
    """Assess cages from the graph topology.
    Args:
        graph: HB network
        node_frac: Positions of the nodes
    """
    # 1. Find rings up to size 8 using cycless.cycles.cycles_iter
    ringlist = [cycles_iter(nx.Graph(graph), 8, pos=node_frac)]
    
    # 2. Compute ring center positions
    ringpos = [centerOfMass(ringnodes, node_frac) for ringnodes in ringlist]
    
    # 3. Detect polyhedral cages using cycless.polyhed.polyhedra_iter
    cages = [cage for cage in polyhedra_iter(ringlist, MaxCageSize=22)]
    
    # 4. Classify cages by graph topology using graphstat.GraphStat
    cage_graphs = [cage_to_graph(cage, ringlist) for cage in cages]
    # ... classify using isomorphism comparison
    
    # 5. Compute cage centers
    cage_fracs = [center_of_graph(g, node_frac) for g in cage_graphs]
    
    return np.array(cage_fracs), cagetypes
```

**Dependencies**: `cycless`, `graphstat`, `networkx`, `numpy` — all already installed as GenIce2 dependencies.

**Limitation**: This works on static structures (snapshot), not MD trajectories. For MD, the HB network topology may change, making cage detection per-frame expensive.

### Approach 3: Ring Detection for Periodic Systems

The "from scratch" approach — detect cages by finding rings and combining them into polyhedra. This is what the `genice2-cage` plugin and Jacobson & Molinero's cage code do.

**Algorithm** (from Molinero group):

1. Find all shortest-path rings of size 5 and 6 in the HB network
2. For each set of rings that share edges, check if they form a closed polyhedron
3. Classify the polyhedron by its face topology (e.g., 12 pentagons = 5¹² dodecahedron)
4. Compute the center as the centroid of ring centers

**Complexity**: O(N²) for ring finding in the worst case, O(N × nb) with cell lists where nb = avg. neighbors per molecule.

**This approach is EXPENSIVE and COMPLEX.** The ring detection alone requires careful handling of PBC and can be ambiguous for disordered/liquid structures.

### Approach 4: HashMap (Venditti Group)

**Source**: Venditti group at U of T, described in various hydrate MD papers.

The HashMap approach:
1. Create a hash table mapping cage graph topology to cage type
2. For each water molecule, examine its local connectivity graph (up to 2nd shell)
3. Hash the connectivity pattern and look up the cage type
4. This is faster than full ring detection but requires a pre-built hash table

**Status**: No public implementation found. Described only in papers. **LOW confidence** on algorithm details.

## Pseudocode / Implementation Sketch (Coordinate-Based, Recommended)

```python
import numpy as np

class CageTracker:
    """Track cage occupancy using known cage centers from GenIce2."""
    
    def __init__(self, cage_centers_frac, cage_types, cell_matrix):
        """
        Args:
            cage_centers_frac: (N_cages, 3) fractional coordinates of cage centers
            cage_types: list of cage type strings (e.g., "12", "14", "16")
            cell_matrix: (3, 3) cell matrix in nm
        """
        self.cage_centers_frac = cage_centers_frac
        self.cage_types = cage_types
        self.cell_matrix = cell_matrix  # nm
        
        # Cage radii in nm (approximate, per cage type)
        self.cage_radii = {
            "12": 0.39,     # 5^12 small cage
            "14": 0.43,     # 5^12 6^2 large cage (sI)
            "16": 0.47,     # 5^12 6^4 large cage (sII)
            "12_1": 0.40,   # 4^3 5^6 6^3 medium cage (sH)
            "20": 0.57,     # 5^12 6^8 large cage (sH)
        }
        
        # Convert cage centers to Cartesian
        self.cage_centers_cart = cage_centers_frac @ cell_matrix
        
        # Occupancy: cage_id -> guest_molecule_id (or None)
        self.occupancy = {i: None for i in range(len(cage_centers_frac))}
    
    def update_occupancy(self, guest_positions, frame=0):
        """
        Determine which guest molecule is in which cage.
        
        Args:
            guest_positions: (N_guests, 3) Cartesian positions of guest molecules
            frame: frame number for time series tracking
        
        Returns:
            occupancy: dict mapping cage_id -> guest_id (or None)
        """
        N_cages = len(self.cage_centers_cart)
        N_guests = len(guest_positions)
        
        # For each cage, find the closest guest within the cage radius
        new_occupancy = {i: None for i in range(N_cages)}
        
        for cage_id in range(N_cages):
            ctype = self.cage_types[cage_id % len(self.cage_types)]
            radius = self.cage_radii.get(ctype, 0.40)  # default 4.0 Å
            center = self.cage_centers_cart[cage_id]
            
            # PBC-aware distance calculation
            for guest_id in range(N_guests):
                delta = guest_positions[guest_id] - center
                # Minimum image
                delta -= self.cell_matrix.T @ np.floor(
                    np.linalg.inv(self.cell_matrix).T @ delta + 0.5
                )
                dist = np.linalg.norm(delta)
                
                if dist < radius:
                    if new_occupancy[cage_id] is None or \
                       dist < self._dist_to_guest(center, new_occupancy[cage_id], guest_positions):
                        new_occupancy[cage_id] = guest_id
        
        self.occupancy = new_occupancy
        return new_occupancy
    
    def compute_occupancy_fraction(self):
        """Compute fraction of occupied cages, per type."""
        from collections import defaultdict
        total = defaultdict(int)
        occupied = defaultdict(int)
        
        for cage_id in range(len(self.cage_centers_frac)):
            ctype = self.cage_types[cage_id % len(self.cage_types)]
            total[ctype] += 1
            if self.occupancy[cage_id] is not None:
                occupied[ctype] += 1
        
        return {ct: occupied[ct] / total[ct] for ct in total}
```

## Feasibility Assessment

- **Lines of code** (coordinate-based): ~100-150
- **Lines of code** (topological cage detection): ~500-1000 (very complex)
- **Complexity**: LOW (coordinate-based), HIGH (topological)
- **Dependencies**: numpy only (coordinate-based); cycless, networkx, graphstat (topological — all already installed)
- **Blockers**:
  - **GenIce2 provides cage centers at generation time** — this eliminates the need for topological cage detection for initial structures
  - **For MD trajectories**: Cage centers drift as the structure evolves. Need to either:
    - (a) Update cage centers per frame using a reference structure + displacement tracking
    - (b) Recompute cage centers per frame (expensive)
    - (c) Use a hybrid: initial cage centers + nearest-water re-centering each frame
  - Option (c) is recommended: find the centroid of the 20 (5¹²) or 24 (5¹²6²) water molecules closest to each initial cage center
- **Confidence**: HIGH (coordinate-based approach, verified GenIce2 source); MEDIUM (topological, based on paper descriptions only)

## Reference Implementations

| Source | Language | URL/Reference | Confidence |
|--------|----------|---------------|------------|
| GenIce2 cage.py (built-in) | Python | Installed at `genice2/cage.py` | HIGH (verified) |
| genice2-cage plugin | Python | `pip install genice2-cage` | HIGH (from GenIce2 author) |
| Jacobson & Molinero cage code | LAMMPS | Referenced in Nguyen & Molinero (2015) | MEDIUM |
| OVITO cage analysis | C++ | https://www.ovito.org/ | MEDIUM |
| HashMap (Venditti) | Unknown | No public implementation found | LOW |

## Key Pitfalls

1. **Cage center drift during MD**: The initial cage centers from GenIce2 are valid at t=0. During MD, the hydrate lattice deforms, and cage centers shift. **Solution**: Re-center each cage by computing the centroid of its surrounding water molecules each frame.

2. **Cage center re-identification**: For each frame, find the water molecules closest to each initial cage center, then recompute the center as their centroid. This is O(N_cages × N_waters) per frame but can be optimized with KDTree.

3. **PBC wrapping of cage centers**: Cage centers defined in fractional coordinates may need special handling when molecules cross boundaries. GenIce2's `parse_cages` already wraps to [0, 1).

4. **Cage destruction during dissociation**: When a hydrate dissociates, cages break apart. The coordinate-based approach will produce unreliable results for dissociated cages. Switch to CHILL+ classification for dissociation studies.

5. **GenIce2 `raw` format for cage export**: To extract cage positions from GenIce2, use the `raw` output format or access `repcagepos` and `repcagetype` from the GenIce2 API. The `genice2-cage` plugin (not installed) provides cage analysis as an output format.

6. **sH lattice uses deprecated `self.cages` attribute**: The DOH.py lattice module uses `self.cages` (deprecated per GenIce2 warning) instead of `self.cagepos, self.cagetype = parse_cages(...)`. Both work but the interface differs slightly.

7. **Cage numbering across replicas**: When using `--rep N N N`, cage positions are replicated. The cage IDs in the replicated cell follow the formula: `cage_id_replica = cage_id_unit + n_cages_unit × replica_id`.
