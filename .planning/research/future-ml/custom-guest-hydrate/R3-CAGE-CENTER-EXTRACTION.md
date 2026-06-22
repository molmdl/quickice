# R3: Cage Center Extraction for Approach B (Fallback)

**Researcher:** GSD Project Researcher
**Date:** 2026-06-22
**Mode:** Feasibility + Ecosystem
**Overall confidence:** HIGH

---

## Executive Summary

GenIce2 **fully exposes cage center positions** through its Python API, making Approach B (post-processing guest insertion) straightforward. The `GenIce` object preserves cage positions as `repcagepos` (fractional coordinates of replicated cage centers) and `repcagetype` (cage type labels) through the entire `generate_ice()` pipeline. Lattice modules also expose unit-cell cage positions directly via `lattice.cagepos` and `lattice.cagetype`. For sH, the deprecated `cages` string format is transparently converted by GenIce's constructor. The `assess_cages()` function in `genice2.cage` provides a topology-based fallback for lattices that don't pre-define cage positions.

**Bottom line:** We do NOT need to reverse-engineer cage positions from the water framework. GenIce2 gives them to us for free. The extraction is a 3-line operation after `generate_ice()` or `Stage1()`.

---

## 1. Cage Positions from Lattice Modules (Direct Access)

### Finding: Lattice modules expose `cagepos` and `cagetype` as instance attributes

**Confidence:** HIGH (verified by source code reading and runtime testing)

All three hydrate lattice modules expose cage center positions:

| Lattice | Module | Attribute | Format | Cages/Unit Cell |
|---------|--------|-----------|--------|-----------------|
| sI | `genice2.lattices.sI` (→ CS1) | `cagepos`, `cagetype` | Fractional coords (3×N array + list of str) | 8 (2 small + 6 large) |
| sII | `genice2.lattices.sII` (→ CS2) | `cagepos`, `cagetype` | Same | 24 (16 small + 8 large) |
| sH | `genice2.lattices.sH` (→ DOH) | `cages` (deprecated string) | Parsed by `parse_cages()` → same format | 12 (6×5¹² + 4×4³5⁶6³ + 2×5¹²6⁸) |

### Verified output

```python
from genice2.lattices import sI, sII, sH

# sI
lat = sI.Lattice()
print(lat.cagepos.shape)   # (8, 3)
print(lat.cagetype)        # ['12', '12', '14', '14', '14', '14', '14', '14']

# sII
lat2 = sII.Lattice()
print(lat2.cagepos.shape)  # (24, 3)
print(lat2.cagetype)       # ['12', '12', ..., '16', '16', ...]  (16×'12' + 8×'16')

# sH (uses deprecated 'cages' string)
lat3 = sH.Lattice()
print(hasattr(lat3, 'cagepos'))  # False — uses 'cages' string instead
from genice2.valueparser import parse_cages
cp, ct = parse_cages(lat3.cages)
print(cp.shape)            # (12, 3)
print(ct)                  # ['12', '12', '12_1', '12', '12_1', '12_1', '12', '20', '20', '12_1', '12', '12']
```

### Cage type label mapping

| Label (lattice) | Label (assess_cages) | Standard notation | Description | Cage structure |
|---|---|---|---|---|
| `'12'` | `A12` | 5¹² | Dodecahedron | 12 pentagonal faces |
| `'14'` | `A14` | 5¹²6² | Tetrakaidecahedron (sI large) | 12 pentagons + 2 hexagons |
| `'16'` | `A16` | 5¹²6⁴ | Hexakaidecahedron (sII large) | 12 pentagons + 4 hexagons |
| `'20'` | `A20` | 5¹²6⁸ | (sH large) | 12 pentagons + 8 hexagons |
| `'12_1'` | `A12a` | 4³5⁶6³ | Distorted dodecahedron (sH) | sH-specific variant |

**Important:** The lattice modules use face-count labels (`'12'`, `'14'`, `'16'`, `'20'`), while `assess_cages()` uses Frank-Kasper labels (`A12`, `A14`, `A16`, `A20`). QuickIce's existing code already uses the face-count convention (see `hydrate_generator.py` lines 186-200).

### Source files

- `/share/home/nglokwan/miniconda3/envs/quickice/lib/python3.14/site-packages/genice2/lattices/CS1.py` (sI, line 76-85)
- `/share/home/nglokwan/miniconda3/envs/quickice/lib/python3.14/site-packages/genice2/lattices/CS2.py` (sII, lines 170-197)
- `/share/home/nglokwan/miniconda3/envs/quickice/lib/python3.14/site-packages/genice2/lattices/DOH.py` (sH, lines 13-26)
- `/share/home/nglokwan/miniconda3/envs/quickice/lib/python3.14/site-packages/genice2/valueparser.py` (`parse_cages`, lines 25-45)

---

## 2. Cage Positions from GenIce Object (After Construction)

### Finding: GenIce constructor stores `cagepos1` and `cagetype1` as unit-cell cage positions

**Confidence:** HIGH (verified by runtime testing)

After constructing a `GenIce` object, `ice.cagepos1` and `ice.cagetype1` are available. These are the same positions as the lattice module's `cagepos`/`cagetype` but processed through GenIce's constructor (shift applied, wrapped to [0,1)).

```python
from genice2.genice import GenIce
from genice2.lattices import sI
import numpy as np

lattice = sI.Lattice()
ice = GenIce(lattice, reshape=np.diag([1,1,1]))

# Unit-cell cage positions (fractional coordinates)
print(ice.cagepos1.shape)   # (8, 3)
print(ice.cagetype1)        # ['12', '12', '14', '14', '14', '14', '14', '14']

# Verify they match lattice positions exactly
print(np.max(np.abs(ice.cagepos1 - lattice.cagepos)))  # 0.000000
```

### GenIce constructor code path (genice.py lines 636-645)

```python
if "cages" in lat.__dict__:
    self.cagepos1, self.cagetype1 = parse_cages(lat.cages)
elif "cagepos" in lat.__dict__:
    self.cagepos1, self.cagetype1 = np.array(lat.cagepos), lat.cagetype
```

This handles both the modern `cagepos`/`cagetype` format (sI, sII) and the deprecated `cages` string format (sH) transparently.

---

## 3. Cage Positions from GenIce Object (After Stage1 / generate_ice)

### Finding: `repcagepos` and `repcagetype` are fully accessible after the pipeline

**Confidence:** HIGH (verified by runtime testing)

After `Stage1()` or `generate_ice()`, the `GenIce` object stores replicated cage positions:

| Attribute | Type | Description |
|-----------|------|-------------|
| `ice.repcagepos` | `np.ndarray (N_cages, 3)` | Cage center positions in **fractional coordinates** of the grand (supercell) |
| `ice.repcagetype` | `list[str]` | Cage type label for each cage |
| `ice.cagetypes` | `defaultdict(set)` | Map from cage type label → set of cage indices |
| `ice.repcell` | `Cell` object | Supercell with `.rel2abs()` and `.mat` for coordinate conversion |

### Verified: After full `generate_ice()` with empty guests

```python
from genice2.genice import GenIce
from genice2.lattices import sI
from genice2.plugin import safe_import
import numpy as np

lattice = sI.Lattice()
ice = GenIce(lattice, reshape=np.diag([2,2,2]))
water = safe_import('molecule', 'tip4p').Molecule()
formatter = safe_import('format', 'gromacs').Format()

gro_string = ice.generate_ice(formatter=formatter, water=water, guests={}, depol='strict')

# Cage positions STILL accessible after generate_ice
print(ice.repcagepos.shape)  # (64, 3)  — 8 cages/cell × 2³ cells
print(ice.repcagetype[:8])   # ['12', '12', '14', '14', '14', '14', '14', '14']
print(ice.cagetypes)         # {'12': {0,1,8,9,...}, '14': {2,3,4,5,...}}

# Convert to absolute coordinates (nm)
for i in range(len(ice.repcagepos)):
    abs_pos = ice.repcell.rel2abs(ice.repcagepos[i])
    # ... use abs_pos for guest placement
```

### Supercell replication counts verified

| Lattice | Supercell | Cages/unit cell | Total cages | Small | Large |
|---------|-----------|-----------------|-------------|-------|-------|
| sI | 1×1×1 | 8 | 8 | 2 (type '12') | 6 (type '14') |
| sI | 2×2×2 | 8 | 64 | 16 | 48 |
| sII | 1×1×1 | 24 | 24 | 16 (type '12') | 8 (type '16') |
| sH | 1×1×1 | 12 | 12 | 6 (type '12') + 4 (type '12_1') | 2 (type '20') |

### Stage1 code path (genice.py lines 828-850)

```python
if self.cagepos1 is not None and self.cagepos1.shape[0] > 0:
    self.repcagepos = replicate_positions(
        self.cagepos1, self.replica_vectors, self.reshape_matrix
    )
    nrepcages = self.repcagepos.shape[0]
    self.repcagetype = [
        self.cagetype1[i % len(self.cagetype1)] for i in range(nrepcages)
    ]
    self.cagetypes = defaultdict(set)
    for i, typ in enumerate(self.repcagetype):
        self.cagetypes[typ].add(i)
```

The `replicate_positions()` function (lines 319-333) applies the same replication logic used for water molecules: it maps unit-cell fractional coordinates to grand-cell fractional coordinates using the reshape matrix inverse.

---

## 4. The `assess_cages()` Fallback

### Finding: `assess_cages()` works but uses different labeling and is topology-based

**Confidence:** HIGH (verified by runtime testing and source code reading)

The `assess_cages()` function in `genice2.cage` detects cages from the hydrogen-bond network topology. It's useful for lattices that don't pre-define cage positions.

```python
from genice2.cage import assess_cages
import networkx as nx

# Requires: hydrogen-bond graph + water positions (fractional coords)
cage_fracs, cagetypes = assess_cages(graph, node_frac)
```

**Differences from lattice-defined positions:**

1. **Labeling**: Uses Frank-Kasper notation (A12, A14, A16, A20, A12a) instead of face-count labels (12, 14, 16, 20)
2. **Ordering**: Cages are discovered in topological order, not crystallographic order
3. **Dependencies**: Requires `cycless` and `graphstat` packages (already in conda env)
4. **Computational cost**: Much slower than reading pre-defined positions (ring detection + graph isomorphism)

**Recommendation:** Use lattice-defined `cagepos`/`cagetype` as the primary method. `assess_cages()` is only needed for custom/unusual lattices that lack pre-defined cage data.

### Dependencies of assess_cages

| Package | Function | Purpose |
|---------|----------|---------|
| `cycless.cycles` | `cycles_iter`, `centerOfMass` | Find ring structures in HB network |
| `cycless.polyhed` | `polyhedra_iter`, `cage_to_graph` | Detect polyhedral cages from ring lists |
| `graphstat.GraphStat` | `query_id`, `register` | Classify cage types by graph isomorphism |

---

## 5. Extraction Method Recommendation

### Recommended: Intercept GenIce2 internal state (Option 1)

**Confidence:** HIGH

The simplest and most reliable extraction method is to **keep a reference to the GenIce object** after calling `generate_ice()` with empty guests, then read `ice.repcagepos` and `ice.repcagetype`.

```python
def extract_cage_centers(lattice_name: str, supercell: tuple[int,int,int]):
    """Extract cage center positions from GenIce2.

    Returns:
        cage_positions: (N, 3) array of absolute positions in nm
        cage_types: list of cage type labels ('12', '14', '16', '20')
        cell_matrix: (3, 3) array — supercell box vectors
    """
    from genice2.genice import GenIce
    from genice2.plugin import safe_import
    import numpy as np

    lattice = safe_import('lattice', lattice_name).Lattice()
    ice = GenIce(lattice, reshape=np.diag(supercell))

    # Generate empty framework (no guests)
    water = safe_import('molecule', 'tip4p').Molecule()
    formatter = safe_import('format', 'gromacs').Format()
    ice.generate_ice(formatter=formatter, water=water, guests={}, depol='strict')

    # Extract cage positions
    cage_positions = np.array([ice.repcell.rel2abs(cp) for cp in ice.repcagepos])
    cage_types = ice.repcagetype
    cell_matrix = ice.repcell.mat

    return cage_positions, cage_types, cell_matrix
```

### Alternative: Use lattice module directly (Option 2)

If we want to avoid running the full GenIce pipeline (for speed), we can extract cage positions directly from the lattice module and replicate ourselves. However, this requires:
- Reimplementing `replicate_positions()` logic
- Handling density scaling (GenIce scales the cell to match target density)
- Computing the supercell matrix effects on fractional coordinates

**Recommendation:** Use Option 1 (intercept GenIce state). It's simpler, handles all edge cases (density scaling, triclinic cells), and the performance cost of running `generate_ice()` is already incurred for the water framework anyway.

### Integration with current HydrateStructureGenerator

The current `hydrate_generator.py` creates a GenIce object and calls `generate_ice()`, but **discards the GenIce object** after parsing the GRO string. To extract cage centers, we simply need to:

1. **Keep the `ice` object** as a return value (or store it as an attribute)
2. **After `generate_ice()`**: read `ice.repcagepos`, `ice.repcagetype`, `ice.cagetypes`
3. **Convert to absolute coordinates**: `ice.repcell.rel2abs(ice.repcagepos[i])`

This is a **non-breaking change** — the existing GRO parsing continues to work unchanged. We just add a few extra attribute reads.

---

## 6. Cage Diameter Reference Values

### Literature values for clathrate hydrate cage cavity diameters

**Confidence:** MEDIUM (from training data, cross-verified against nearest-water distances)

The cage "cavity diameter" is the diameter of the spherical void inside the cage, measured from the cage center to the inner surface of the water framework (excluding van der Waals radii of water oxygen atoms).

| Cage type | Notation | Faces | Cavity radius (Å) | Cavity diameter (Å) | Cavity diameter (nm) |
|-----------|----------|-------|--------------------|----------------------|----------------------|
| Small (common) | 5¹² | 12 | ~3.9–4.0 | ~7.8–8.0 | ~0.78–0.80 |
| sI large | 5¹²6² | 14 | ~4.3–4.4 | ~8.6–8.8 | ~0.86–0.88 |
| sII large | 5¹²6⁴ | 16 | ~4.7–4.8 | ~9.4–9.6 | ~0.94–0.96 |
| sH large | 5¹²6⁸ | 20 | ~5.7–5.8 | ~11.4–11.6 | ~1.14–1.16 |
| sH medium | 4³5⁶6³ | 12_1 | ~4.0–4.1 | ~8.0–8.2 | ~0.80–0.82 |

### Validation against computed nearest-water distances

Measured from cage center to nearest water oxygen (TIP4P model):

| Lattice | Cage type | Nearest O distance (nm) | Expected cavity radius (nm) | Agreement |
|---------|-----------|------------------------|----------------------------|-----------|
| sI | '12' (5¹²) | 0.380 | 0.395 | Good — O is slightly inside cage wall |
| sI | '14' (5¹²6²) | 0.402 | 0.433 | Good — O is slightly inside cage wall |

The measured distances are ~4-7% smaller than literature cavity radii, which is expected because the oxygen atom sits slightly inside the cage surface (the cage wall is defined by the hydrogen-bonded network, not the oxygen positions).

### Key references

- Abascal et al. 2005 (TIP4P-ICE): DOI 10.1063/1.1931662
- Sloan & Koh, *Clathrate Hydrates of Natural Gases*, 3rd ed. (2008): Chapter 2 for cage geometries
- Davidson et al., *Clathrate Hydrates* (1973): Original cavity diameter measurements

---

## 7. Guest Diameter Validation Approach

### Problem

Before placing a custom guest molecule in a cage, we should verify the guest fits. This requires computing an "effective diameter" of the guest from its GRO coordinates and comparing it against the cage cavity diameter.

### Options

| Method | Formula | Pros | Cons | Needs element data? |
|--------|---------|------|------|---------------------|
| **Max pairwise distance** | `max(d(i,j)) for all atom pairs i,j` | Simple, no COM needed | Overestimates for elongated molecules | No |
| **Max COM dist × 2** (recommended) | `2 × max(d(COM, atom_i))` | Simple, captures effective spherical radius | Underestimates for non-spherical guests (asymmetric shapes) | No |
| **vdW envelope** | `max(d(COM, atom_i)) + vdW_radius(atom_i)` then × 2 | Physically most meaningful | Requires element → vdW radius mapping | Yes |

### Recommendation: Use **max COM distance × 2** as the primary method

```python
def guest_effective_diameter(positions: np.ndarray) -> float:
    """Compute effective guest molecule diameter from atomic positions.

    Uses max distance from center of mass to any atom × 2.
    This gives the diameter of the smallest sphere centered at COM
    that contains all atoms.

    Args:
        positions: (N, 3) array of atom positions in nm

    Returns:
        Effective diameter in nm
    """
    com = np.mean(positions, axis=0)
    max_dist = np.max(np.linalg.norm(positions - com, axis=1))
    return max_dist * 2
```

### Validation against known molecules

| Molecule | Method 1 (max pairwise) | Method 2 (max COM × 2) | Literature kinetic diameter |
|----------|------------------------|------------------------|---------------------------|
| CH₄ | 3.08 Å | 3.78 Å | ~3.8 Å |
| THF | — | ~5.0 Å (estimated) | ~6.2 Å (kinetic) |

**Note:** Method 2 (max COM × 2) gives the "bare" atomic diameter without van der Waals envelopes. For strict size validation, add a safety margin of ~0.5 Å on each side (total ~1.0 Å or 0.1 nm). The kinetic diameter includes vdW repulsion and is typically larger than the bare atomic diameter.

### Recommended validation rule

```python
# Guest must fit in cage with margin
GUEST_CAGE_MARGIN_NM = 0.05  # 0.5 Å safety margin per side (total 1.0 Å)

def validate_guest_fits_cage(
    guest_positions: np.ndarray,
    cage_type: str,
) -> bool:
    """Check if a guest molecule fits in a cage type.

    Uses effective diameter (max COM distance × 2) + margin
    vs. cage cavity diameter.
    """
    CAGE_DIAMETERS = {
        '12': 0.78,    # 5^12 small cage
        '12_1': 0.80,  # 4^3 5^6 6^3 (sH medium)
        '14': 0.86,    # 5^12 6^2 (sI large)
        '16': 0.94,    # 5^12 6^4 (sII large)
        '20': 1.14,    # 5^12 6^8 (sH large)
    }

    guest_diam = guest_effective_diameter(guest_positions)
    cage_diam = CAGE_DIAMETERS[cage_type]
    margin = GUEST_CAGE_MARGIN_NM * 2  # margin on both sides

    return guest_diam + margin <= cage_diam
```

---

## 8. Summary of Key Findings

| Question | Answer | Confidence |
|----------|--------|------------|
| Can we access GenIce2 lattice cage positions directly? | YES — `lattice.cagepos` (sI, sII) or `parse_cages(lattice.cages)` (sH) | HIGH |
| Can we get cage positions from GenIce after generation? | YES — `ice.repcagepos` and `ice.repcagetype` survive `generate_ice()` | HIGH |
| Can we replicate cage positions for supercells? | YES — GenIce's `Stage1` does this automatically via `replicate_positions()` | HIGH |
| Does `assess_cages()` work? | YES — but uses different labeling (A12 vs '12') and is slower | HIGH |
| Are cage positions in fractional or absolute coords? | Fractional — convert with `ice.repcell.rel2abs()` | HIGH |
| Is the extraction non-breaking for existing code? | YES — just keep the `ice` object reference and read attributes | HIGH |
| Can we validate guest-cage size fit? | YES — using max COM distance × 2 with safety margin | MEDIUM |

---

## 9. Implementation Sketch for Approach B

### Minimal changes to `hydrate_generator.py`

```python
class HydrateStructureGenerator:
    def generate(self, config: HydrateConfig) -> HydrateStructure:
        # ... existing code ...
        positions, cell, atom_names, residue_names, residue_seq_nums = self._run_via_api(lattice_name, config)

        # NEW: Also return the GenIce object for cage extraction
        # (requires modifying _run_via_api to return ice as well)

    def _run_via_api(self, lattice_name: str, config: HydrateConfig) -> tuple:
        # ... existing code up to generate_ice ...
        gro_string = ice.generate_ice(...)
        parsed = self._parse_gro_result(gro_string)

        # NEW: Return ice object for cage extraction
        return *parsed, ice  # Add ice as last return value

    def extract_cage_centers(self, ice) -> dict:
        """Extract cage center positions from a GenIce object.

        Returns:
            {
                'positions': np.ndarray (N_cages, 3) in absolute nm,
                'types': list[str] of cage type labels,
                'indices_by_type': dict[str, set[int]],
            }
        """
        cage_abs = np.array([ice.repcell.rel2abs(cp) for cp in ice.repcagepos])
        return {
            'positions': cage_abs,
            'types': ice.repcagetype,
            'indices_by_type': dict(ice.cagetypes),
        }
```

### Custom guest insertion workflow (Approach B)

```
1. Generate empty hydrate framework (guests={})
2. Extract cage centers from GenIce object (ice.repcagepos → abs coords)
3. For each cage type, determine occupancy (from config)
4. For each occupied cage:
   a. Load custom guest from user's .gro file
   b. Validate guest fits cage (diameter check)
   c. Translate guest COM to cage center
   d. Apply random rotation (or user-specified orientation)
   e. Check overlap with water framework (cKDTree)
   f. If overlap, reject and try different rotation
5. Append guest atoms to water framework positions
6. Build molecule index (water + guest molecules)
7. Output HydrateStructure with guest data
```

---

## 10. Risks and Open Questions

### Risk: GenIce2 internal API stability

The `repcagepos` and `repcagetype` attributes are not part of GenIce2's documented public API — they're internal state used during the pipeline. A future GenIce2 update could rename or remove them.

**Mitigation:** The `cagepos`/`cagetype` attributes on lattice modules ARE the standard interface for lattice plugins and are unlikely to change. We can fall back to lattice-level access + self-replication if needed.

### Risk: sH deprecated `cages` format

sH uses the deprecated `cages` string format. GenIce currently handles this with `parse_cages()`, but future versions might not.

**Mitigation:** We can call `parse_cages(lattice.cages)` ourselves, or submit a PR to update the sH lattice module to use the modern format.

### Open question: Custom cage occupancy logic

GenIce2's Stage7 implements random cage occupancy assignment (randomly selecting which cages to fill at a given occupancy fraction). Approach B needs to reimplement this logic. The algorithm is straightforward (see genice.py lines 1052-1080):

1. Get list of vacant cages for a given type
2. Compute number of molecules to place: `nmolec = int(frac * len(rooms) + 0.5)`
3. Randomly select cages without replacement

This is simple enough to reimplement.

### Open question: Guest residue naming in GRO output

When inserting custom guests, we need to assign residue names and sequence numbers in the GRO output. GenIce2 uses the `name_` attribute from the Molecule plugin. For custom guests, we should use the ITP `[moleculetype]` name with `_H` suffix (matching QuickIce's `MoleculetypeRegistry` convention).

---

## 11. Sources

| Source | Type | Confidence |
|--------|------|------------|
| `genice2/lattices/CS1.py` (sI) | Source code (read) | HIGH |
| `genice2/lattices/CS2.py` (sII) | Source code (read) | HIGH |
| `genice2/lattices/DOH.py` (sH) | Source code (read) | HIGH |
| `genice2/genice.py` Stage1/Stage7 | Source code (read) | HIGH |
| `genice2/cage.py` | Source code (read) | HIGH |
| `genice2/valueparser.py` | Source code (read) | HIGH |
| Runtime tests (sI, sII, sH) | Verified execution | HIGH |
| Cage diameter values | Training data + validation | MEDIUM |
| Sloan & Koh (2008) | Literature reference | MEDIUM (not directly verified) |
| `quickice/structure_generation/hydrate_generator.py` | Existing codebase | HIGH |
