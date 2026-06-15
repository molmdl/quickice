# nucleation_tracker Research

**Tool:** FennellLab/nucleation_tracker
**Paper:** "Assessing Order in Liquid, Supercooled, and Crystalline Water" — J. Phys. Chem. B (2026), doi:10.1021/acs.jpcb.5c08791
**Researched:** 2026-06-15

## Summary

nucleation_tracker is a Python/C++ tool for enumerating hydrogen-bonded ring distributions in water simulations. It identifies closed loops (3- to 10-membered) in the H-bond network, computes the Errington-Debenedetti tetrahedral order parameter, and calculates a Ring Summation Factor (RSF). The associated paper applies these analyses to liquid, supercooled, and crystalline water — **not specifically to clathrate hydrates**. The tool is script-based (no pip install), reads only GROMACS .gro coordinate files (not .xtc/.trr trajectories), has no LICENSE file, and has extremely poor code quality with deeply nested brute-force loops.

For QuickIce, the core analytical concept — H-bond ring distribution as an order parameter for water/ice phase transitions — is **complementary** to our planned F3/F4, CHILL+, and cage analyses. However, the tool itself is **unsuitable as a dependency** due to missing license, incompatible architecture (no MDAnalysis), and poor code quality. The algorithms should be **reimplemented** properly within QuickIce's MDAnalysis-based framework, which will also enable trajectory-wide time-series analysis that nucleation_tracker cannot do.

## What It Does

nucleation_tracker performs three main analyses on water simulations:

### 1. H-Bond Ring Enumeration
The primary analysis. Starting from an H-bond network (detected via Luzar-Chandler geometric criteria or TIP4P energy criteria), the tool performs brute-force graph traversal to find all closed loops of 3-10 water molecules connected by H-bonds. It then applies pruning algorithms to remove "short-circuited" rings (larger rings that contain smaller rings as sub-paths).

**Features:**
- Ring sizes 3 through 10 (configurable via `-r` flag)
- Two counting modes: minimal/primitive rings (`-c 0`) vs. all non-self-intersecting rings (`-c 1`)
- Four pruning algorithms: vertex, common edge (hbond), common angle (hbondAngle), common torsion
- Directional ring tracking (`-d` flag) — tracks proton acceptor direction
- PBC-aware ring detection — excludes rings that don't properly close across periodic boundaries
- Ring spatial binning (`-b` flag) — distributes rings by spatial position

### 2. Tetrahedral Order Parameter
Calculates the Errington-Debenedetti tetrahedral order parameter q for each water molecule:
```
q = 1 - (3/8) * Σ_{i<j} [cos(θ_ij) + 1/3]²
```
where θ_ij is the angle between O-O vectors to the four nearest neighbors. Uses H-bond priority for selecting the four nearest neighbors when more than four are within the distance cutoff.

Output: per-frame average q and standard deviation in `.dat` file, per-molecule q in PDB b-factor column.

### 3. Ring Summation Factor (RSF)
A system-level order parameter:
```
RSF = (# of rings) / (2 * N_molecules)
```
where the denominator is the "optimum" number of H-bonds. RSF is not calculated for directional rings or unpruned ring counting.

### Variant: Aqueous HCl
`nucleation_tracker_hcl.py` is a modified version for aqueous HCl systems, handling Cl⁻ ions, hydronium (H₃O⁺ with 3 H atoms), and water simultaneously in the ring network. This demonstrates extensibility to mixed-component systems.

## Algorithms & Methods

### H-Bond Detection

**Geometric criteria (default):** Luzar-Chandler definition:
- O-O distance < 3.5 Å
- O-H··O angle < 30° (cone angle)
- Checks both donor and acceptor orientations
- Handles 3-site, 4-site (TIP4P with MW), and 5-site water models

**Energy criteria (`-e` flag):** TIP4P-specific energy evaluation:
- LJ potential: V_LJ(r) = 4ε[(σ/r)¹² - (σ/r)⁶]
- Coulombic potential with TIP4P charges (q_O = -1.040, q_H = +0.520)
- H-bond threshold: -2.0 kcal/mol (configurable)
- Speedy et al. pruning: limits to 4 H-bonds per water, removes weakest if excess

### Ring Enumeration Algorithm

The algorithm is a **brute-force depth-first traversal** of the H-bond adjacency graph:

1. For each water molecule `init_wat`, traverse its H-bond neighbors
2. At each level (depth 3-10), check if the path loops back to `init_wat`
3. If a closed loop is found, sort member indices to prevent double-counting
4. Check PBC validity: for each ring edge, count how many times the ring "exits" the box in each dimension; the ring is valid only if exit counts are even in all dimensions
5. Separate rings by size (3-membered through 10-membered)

**Critical code quality issue:** The depth-first traversal is implemented as **8 levels of deeply nested for-loops** (one for each ring size from 3 to 10), each level containing the same pattern. This is ~500 lines of copy-pasted code. A proper recursive or iterative implementation would be ~20-30 lines.

### Ring Pruning Algorithms

After enumerating all closed rings, four pruning strategies remove "short-circuited" rings (non-primitive/minimal rings):

| Algorithm | Code | Criterion | Description |
|-----------|------|-----------|-------------|
| Vertex | `-m vertex` | ≥1 shared member | Removes larger rings sharing any member with a smaller ring |
| Common Edge | `-m hbond` | ≥2 shared members with H-bond between them | Removes larger rings sharing a H-bond edge with a smaller ring |
| Common Angle | `-m hbondAngle` | ≥3 shared members with H-bond angle path | Removes larger rings containing a 3-molecule H-bond angle from a smaller ring |
| Common Torsion | `-m torsion` | ≥4 shared members with H-bond torsion path | Removes larger rings containing a 4-molecule H-bond torsion from a smaller ring |

**Note:** The paper recommends `hbondAngle` (common angle) as the default, called "DCA" (Directional Common Angle) when used with directional ring tracking.

### PBC Handling

The tool uses the **h-matrix** approach for minimum image convention:
- Reads GROMACS box vectors from .gro file
- Constructs the h-matrix and its inverse
- Applies PBC corrections per dimension independently
- Ring PBC check: counts box crossings per dimension; requires even crossings

### Tetrahedral Order Parameter Algorithm

1. Find all O-O neighbors within 2×(3.5 Å)² distance cutoff
2. Sort neighbors by distance
3. If >4 neighbors within 0.5 Å of the closest: select 4 using H-bond priority
4. Compute O-O unit vectors for 4 nearest neighbors
5. Sum cos(θ_ij) + 1/3 for all 6 pairs (i<j)
6. q = 1 - (3/8) × cosine_sum

### Input/Output

**Input:** GROMACS .gro files (coordinate format only)
- Single frame or multi-frame .gro files
- Orthogonal lattice vectors required (triclinic partially supported via h-matrix)
- Water molecules must be present (OW/HW1/HW2 or O/H1/H2 naming)
- No .xtc/.trr trajectory support

**Output files:**
- `*_CA_ringsCount.dat` / `*_DCA_ringsCount.dat` — Ring count statistics per frame (columns: frame, hbonds, RSF, rings_3..rings_N)
- `*_tetra.dat` — Tetrahedral order parameter (avg, stdev per frame)
- `*_tetra.pdb` — Per-molecule tetrahedrality in b-factor column
- `rings_location.xyz` — Ring center positions with element-encoding ring size
- `rings_dist.dat` — Spatially binned ring distribution
- `pov_files/` — POVRay rendering files for ring visualization

## Comparison with QuickIce's Planned Analyses

| Feature | nucleation_tracker | QuickIce Planned (MDA+freud+custom) | Overlap? | Complement? |
|---------|-------------------|--------------------------------------|----------|-------------|
| F3/F4 order parameters | **No** | Yes (MDAnalysis-based) | No | No |
| CHILL+ classification | **No** | Yes (freud-based) | No | No |
| Cage detection/occupancy | **No** | Yes (custom) | No | No |
| H-bond ring enumeration | **Yes** (3-10 membered, 4 pruning algorithms) | Not currently planned | No | **Yes** |
| Tetrahedral order parameter | **Yes** (Errington-Debenedetti q) | Not explicitly planned | No | **Yes** |
| Ring Summation Factor | **Yes** (RSF = #rings / 2N) | Not planned | No | **Yes** |
| Directional ring analysis | **Yes** (proton acceptor direction) | Not planned | No | **Yes** |
| PBC-aware ring detection | **Yes** (h-matrix, per-dimension) | N/A (MDA handles PBC) | Partial | No |
| Trajectory time-series | **No** (.gro frames only) | Yes (MDAnalysis .xtc/.trr) | No | — |
| .gro file parsing | Custom (linecache-based) | MDAnalysis | Partial | No |
| Multi-format support | .gro only | .gro/.xtc/.trr/.pdb/.lammpstrj/etc. | No | — |
| Visualization | POVRay | VTK/PySide6 | No | No |
| Mixed-component systems | HCl variant only | Not planned (hydrate focus) | No | Partial |

**Key insight:** nucleation_tracker fills a gap in QuickIce's planned analysis suite. Ring distribution analysis is a well-established order parameter for distinguishing water/ice phases and could be highly relevant for tracking hydrate nucleation, since clathrate hydrate cages ARE closed H-bonded rings (5-membered, 6-membered) that form polyhedral structures. The ring distribution directly reflects cage topology.

**However:** The tool does NOT specifically detect or classify hydrate cages (5¹², 5¹²6², 5¹²6⁴, etc.). It counts ALL rings of a given size, not just those that form specific cage types. Cage detection remains QuickIce's unique contribution.

## Technical Profile

| Attribute | Value |
|-----------|-------|
| Language | Python 3 + C++ (in development) |
| Dependencies | numpy only (plus stdlib: math, sys, os, linecache, getopt, itertools, threading, time) |
| Python version | Python 3 (no version constraint specified) |
| Install method | Script-based; no pip install, no setup.py, no pyproject.toml |
| Codebase size | ~5,200 lines Python total (3,100 main + 1,600 HCl + 500 tetra), ~5,000 lines C++ (incomplete) |
| Last commit | June 28, 2025 (README update); active development 2022-2025 |
| Active maintenance | Moderate — 75 commits over 3 years, 2 contributors (rmaharj17, cfennell) |
| Stars/Forks/Watchers | 0 / 0 / 1 |
| Authors | Rajendra Maharjan, Casey Williamson, Christopher J. Fennell (Oklahoma State University) |
| No test suite | No unit tests, no integration tests |
| No CI/CD | No GitHub Actions, no automated testing |
| Example files | `py_examples/` (liquid water + ice crystal), `gro_file_examples/` (hexagonal ice, grown ice) |

### Code Quality Assessment

**Major issues:**
1. **Deeply nested loops:** The ring enumeration is 8 levels of nested for-loops, each level copy-pasted with minor variations (~500 lines of repetitive code). Should be a recursive or iterative graph traversal.
2. **Global mutable state:** Functions modify lists defined in enclosing scope; no encapsulation.
3. **No classes, no modularity:** Everything is in one function (`beginCalc`) or global scope. The H-bond detection, ring enumeration, pruning, and output are all interleaved.
4. **Manual .gro parsing:** Uses `linecache.getline()` with hardcoded column positions (nm→Å conversion via ×10). Breaks if atom names differ from expected patterns.
5. **No error handling:** No validation of input, no graceful failure on malformed files.
6. **Memory concerns:** `np.subtract.outer()` creates N² arrays for distance computation — O(N²) memory for large systems.
7. **No trajectory support:** Only reads multi-frame .gro files, not .xtc/.trr trajectories.
8. **Hardcoded water model assumptions:** TIP4P parameters hardcoded in energy_defn function.

**Minor issues:**
- Uses `linecache` for file reading (designed for debugging, not production use)
- PDB output format has minor formatting issues
- Thread animation for loading spinner is cosmetic, not functional
- Coordinate conversion nm→Å (×10) scattered throughout instead of centralized

## License

**No LICENSE file exists in the repository.** The GitHub API also reports no license.

This is a **critical issue** for QuickIce integration:

- **Default copyright:** Without an explicit license, all code defaults to exclusive copyright of the authors under the Berne Convention. All rights are reserved.
- **Cannot use as dependency:** Legally, we cannot import or link to this code without permission.
- **Cannot copy algorithms:** We cannot copy/adapt code sections without permission.
- **Cannot redistribute:** We cannot bundle or redistribute the code.
- **Must contact authors:** Any use requires explicit written permission from the authors.

**Practical options:**
1. Contact Fennell Lab (Oklahoma State University) to request MIT licensing
2. Reimplement the algorithms independently (the underlying algorithms are well-known from published literature)
3. Wait for the authors to add a license

**Assessment:** Since the underlying algorithms (Luzar-Chandler H-bond criteria, Errington-Debenedetti tetrahedral order, graph-based ring enumeration, various pruning strategies) are all published in the scientific literature, reimplementing them independently is legally sound. We would NOT be copying nucleation_tracker's code — we would be implementing published algorithms.

## Paper Details

**Title:** "Assessing Order in Liquid, Supercooled, and Crystalline Water"
**Authors:** R. Maharjan, C. Williamson, and C. J. Fennell
**Journal:** Journal of Physical Chemistry B
**Year:** 2026 (online 2025, DOI cycle 5c08791)
**DOI:** 10.1021/acs.jpcb.5c08791
**ACS link:** https://pubs.acs.org/doi/abs/10.1021/acs.jpcb.5c08791

**Key findings from Google Scholar snippet:**
- Water has strong directional interactions forming H-bond networks
- The paper proposes enumerating directional rings to examine unique ring distributions
- Different water phases (liquid, supercooled, crystalline) show distinct ring distributions
- The tool enables topological analysis of the H-bond network

**Note:** The full paper is behind the ACS paywall (403 Forbidden). The abstract and methodology details are inferred from the codebase and the Google Scholar snippet. The paper appears to validate the tool by showing that ring distributions differ between water phases (liquid vs. ice), which is directly relevant to hydrate nucleation analysis.

**Related work:** R. Maharjan's dissertation (2023, Oklahoma State University): "Investigation of Hidden Structure and the Dipole Moment Distribution in Liquid Water and Ice" — precursor work covering H-bond ring analysis and dipole moment distributions.

**Confidence on paper details:** MEDIUM — based on Google Scholar metadata and codebase analysis; full paper inaccessible due to paywall.

## Integration Assessment

### As dependency: NOT FEASIBLE
- **No license** — cannot legally use as dependency
- **No pip install** — script-based, would need to vendor the entire codebase
- **Incompatible architecture** — uses manual .gro parsing, not MDAnalysis
- **No trajectory support** — only single .gro frames; QuickIce needs .xtc/.trr time-series
- **Poor code quality** — deeply nested loops, global mutable state, no error handling
- **Python 3.14.3 untested** — tool requires only numpy, likely compatible, but untested

### Algorithm reuse: FEASIBLE AND RECOMMENDED
The core algorithms are well-known published methods that can be reimplemented cleanly:

1. **H-bond ring enumeration:** Graph-based cycle detection on the H-bond adjacency network. The brute-force DFS in nucleation_tracker is correct but poorly implemented. A proper implementation using NetworkX or a custom DFS would be 50-100 lines, not 500.

2. **Ring pruning:** The four pruning strategies (vertex, common edge, common angle, common torsion) are clearly defined and straightforward to reimplement. The "hbondAngle" (common angle) method is the recommended default.

3. **Tetrahedral order parameter:** The Errington-Debenedetti q parameter is a standard calculation. MDAnalysis can provide neighbor lists directly, making this a 30-50 line AnalysisBase subclass.

4. **RSF:** Trivially computed as ring_count / (2 * n_molecules).

5. **Directional ring tracking:** The directionality modification (tracking which waters are proton acceptors/donors) is algorithmically simple — it constrains the DFS to follow H-bond directions.

### Unique value: YES, BUT REIMPLEMENT
nucleation_tracker provides analytical capabilities that QuickIce's current planned analyses (F3/F4, CHILL+, cage occupancy) do NOT cover:

1. **H-bond ring distribution** — directly reveals the topological structure of the H-bond network. In hydrate systems, the appearance of specific ring sizes (particularly 5- and 6-membered rings) signals cage formation, which is the precursor to nucleation. This is **different** from but **complementary to** cage detection:
   - Cage detection asks: "How many complete 5¹²/5¹²6² cages exist?"
   - Ring distribution asks: "How does the topology of the H-bond network change as rings form and close?"
   - Ring distribution can detect **early nucleation events** before complete cages form

2. **Tetrahedral order parameter** — provides a per-molecule measure of local tetrahedral ordering that complements CHILL+ classification. CHILL+ classifies (ice, clathrate, interfacial, liquid), while q measures the degree of tetrahedral distortion continuously.

3. **RSF** — a simple scalar order parameter for the whole system that tracks global ordering over time. Useful for quick nucleation/dissociation detection in time-series.

4. **Directional ring analysis** — tracking proton directionality in rings reveals asymmetries in the H-bond network that are important for understanding hydrate stability.

### What nucleation_tracker does NOT provide (that QuickIce needs):
- F3/F4 order parameters
- CHILL+ ice/clathrate classification
- Specific cage type detection (5¹², 5¹²6², 5¹²6⁴, etc.)
- Cage occupancy (guest molecules in cages)
- Trajectory-level time-series analysis
- Visualization integration (VTK/PySide6)
- Multiple trajectory format support

## Recommendation

**REIMPLEMENT the core algorithms; do NOT use nucleation_tracker as a dependency.**

### Rationale:

1. **Legal:** No license means we cannot legally use, modify, or redistribute the code. Reimplementing published algorithms is legally sound.

2. **Architectural mismatch:** nucleation_tracker uses manual .gro parsing and cannot read trajectories. QuickIce uses MDAnalysis, which provides trajectory iteration, PBC handling, atom selection, and neighbor detection for free.

3. **Code quality:** The 500-line nested-loop ring enumeration can be replaced with a 50-100 line recursive DFS or NetworkX-based cycle finder. The rest of the code has similar improvement potential.

4. **Complementary value:** The analytical concepts (ring distribution, tetrahedral order, RSF) are valuable for hydrate analysis and should be part of QuickIce's analysis suite. They fill a genuine gap between our planned per-molecule analyses (F3/F4, CHILL+) and per-cage analyses (occupancy).

5. **Priority assessment:** Ring distribution analysis is a **lower priority** than F3/F4, CHILL+, and cage detection for QuickIce's hydrate analysis milestone. It should be a Phase 2 or Phase 3 addition, not Phase 1.

### Suggested reimplementation approach:

```
class HBondRingAnalysis(mda.analysis.base.AnalysisBase):
    """Enumerate H-bonded ring distributions using MDAnalysis."""
    
    def __init__(self, universe, max_ring_size=8, 
                 hbond_cutoff=3.5, angle_cutoff=30,
                 pruning='common_angle', directional=False):
        ...
    
    def _compute_hbond_network(self):
        """Build H-bond adjacency using MDAnalysis hydrogenbond analysis."""
        ...
    
    def _enumerate_rings(self):
        """Find all closed rings via DFS on H-bond adjacency graph."""
        ...
    
    def _prune_rings(self, method='common_angle'):
        """Remove short-circuited rings."""
        ...
    
    def _compute_rsf(self):
        """Calculate Ring Summation Factor."""
        ...

class TetrahedralOrderParameter(mda.analysis.base.AnalysisBase):
    """Errington-Debenedetti tetrahedral order parameter."""
    
    def __init__(self, universe, cutoff=3.5):
        ...
```

This approach:
- Uses MDAnalysis's trajectory iteration (supports .xtc, .trr, .gro, .pdb, etc.)
- Uses MDAnalysis's built-in PBC handling
- Leverages MDAnalysis's HydrogenBondAnalysis for H-bond detection
- Implements ring enumeration as a clean recursive DFS
- Outputs results compatible with QuickIce's time-series visualization
- Is MIT-licensable (reimplementation of published algorithms)

## Sources

| Source | URL | Confidence | Notes |
|--------|-----|------------|-------|
| GitHub repo (code, README, commits) | https://github.com/FennellLab/nucleation_tracker | HIGH | Directly inspected all source files |
| Raw nucleation_tracker.py | https://raw.githubusercontent.com/FennellLab/nucleation_tracker/master/nucleation_tracker.py | HIGH | Full 3100-line source reviewed |
| Raw tetrahedrality.py | https://raw.githubusercontent.com/FennellLab/nucleation_tracker/master/tetrahedrality.py | HIGH | Full 519-line source reviewed |
| Raw nucleation_tracker_hcl.py | https://raw.githubusercontent.com/FennellLab/nucleation_tracker/master/nucleation_tracker_hcl.py | HIGH | Partial review (1602 lines) |
| py_examples/README.txt | https://github.com/FennellLab/nucleation_tracker/blob/master/py_examples/README.txt | HIGH | Author list, algorithm descriptions |
| Commit history | https://github.com/FennellLab/nucleation_tracker/commits/master | HIGH | 75 commits, 2022-2025 |
| LICENSE file (404) | https://raw.githubusercontent.com/FennellLab/nucleation_tracker/master/LICENSE | HIGH | Confirmed: no license file exists |
| Paper (ACS, paywall 403) | https://pubs.acs.org/doi/10.1021/acs.jpcb.5c08791 | N/A | Inaccessible — paywall blocked |
| Google Scholar (paper metadata) | https://scholar.google.com/scholar?q=Maharjan+Fennell+hydrogen+bond+ring+distribution+water+J+Phys+Chem+B | MEDIUM | Title, authors, year confirmed; abstract snippet only |
| Maharjan dissertation (2023) | https://search.proquest.com/openview/74fe950bda9a0fbc3914edb825db2ddb/1 | LOW | Not directly accessed; Google Scholar metadata only |

## Appendix: Ring Distribution Relevance to Hydrate Analysis

Clathrate hydrate structures are built from specific H-bonded ring combinations:

| Hydrate structure | Cage types | Key ring sizes |
|-------------------|------------|----------------|
| sI (structure I) | 5¹² + 5¹²6² | Pentagons (5) + Hexagons (6) |
| sII (structure II) | 5¹² + 5¹²6⁴ | Pentagons (5) + Hexagons (6) |
| sH (structure H) | 5¹² + 4³5⁶6³ + 5¹²6⁸ | Pentagons (5) + Squares (4) + Hexagons (6) |

Ring distribution analysis during nucleation simulations would show:
- **Pre-nucleation:** Broad distribution of ring sizes (3-8), dominated by 5- and 6-membered rings in liquid
- **Early nucleation:** Increase in 5- and 6-membered rings as cages begin forming
- **Post-nucleation:** Sharp dominance of 5- and 6-membered rings matching the hydrate structure

This makes ring distribution a potentially sensitive **early indicator** of nucleation, detectable before complete cages form. It complements (but does not replace) cage detection, which identifies fully formed cages.
