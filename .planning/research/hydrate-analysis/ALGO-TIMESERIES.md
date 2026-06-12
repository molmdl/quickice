# Algorithm: Hydrate Stability Tracking, Guest Residence Time, and Density Profiles

## What It Measures

These time-series and spatial analyses characterize:
1. **Hydrate stability/dissociation**: How much of the system remains in the hydrate phase over time
2. **Guest molecule residence time**: How long guest molecules stay in cages before exchanging
3. **Density profiles**: Spatial distribution of water and guest molecules, especially at interfaces

---

## 1. Hydrate Stability / Dissociation Tracking

### What It Measures

The fraction of water molecules classified as "hydrate-like" vs "liquid-like" over time, or equivalently the number of intact cages over time. This is the primary metric for hydrate stability in MD simulations.

### Method: F4/CHILL+ Classification Per Frame

The most common approach:

1. For each frame of the MD trajectory:
   - Classify each water molecule using F4 or CHILL+ (see ALGO-F3F4.md, ALGO-CHILL.md)
   - Count molecules classified as "clathrate" vs "liquid" vs "ice"
2. Plot the time series: `N_hydrate(t) / N_total` = hydrate fraction

```python
def track_hydrate_stability(trajectory, cell_matrix, method='chill_plus'):
    """
    Track hydrate stability over MD trajectory.
    
    Args:
        trajectory: iterable of (oxygen_positions, guest_positions) per frame
        cell_matrix: (3, 3) simulation cell
        method: 'chill_plus' or 'f4'
    
    Returns:
        time_series: dict with keys 'hydrate_fraction', 'ice_fraction', 'liquid_fraction'
        per_molecule: per-frame classification arrays
    """
    results = {
        'hydrate_fraction': [],
        'ice_fraction': [],
        'liquid_fraction': [],
    }
    per_molecule = []
    
    for frame_idx, (oxy_pos, guest_pos) in enumerate(trajectory):
        if method == 'chill_plus':
            classes = compute_chill_plus(oxy_pos, cell_matrix)
            # 0=Liquid, 1=Ih, 2=Ic, 3=Interfacial ice, 4=Clathrate, 5=Interfacial clathrate
            n_hydrate = np.sum((classes == 4) | (classes == 5))
            n_ice = np.sum((classes == 1) | (classes == 2) | (classes == 3))
            n_liquid = np.sum(classes == 0)
        elif method == 'f4':
            f4_system, f4_per_bond = compute_F4(oxy_pos, cell_matrix)
            # Assign per-molecule F4 from per-bond values
            n_hydrate = np.sum(f4_per_molecule > 0.5)
            n_ice = np.sum(f4_per_molecule < -0.2)
            n_liquid = np.sum((f4_per_molecule >= -0.2) & (f4_per_molecule <= 0.5))
        
        N = len(oxy_pos)
        results['hydrate_fraction'].append(n_hydrate / N)
        results['ice_fraction'].append(n_ice / N)
        results['liquid_fraction'].append(n_liquid / N)
        per_molecule.append(classes)
    
    return results, per_molecule
```

### Method: Cage Count Per Frame

Alternative using cage detection (see ALGO-CAGE.md):

1. For each frame, count occupied and intact cages
2. An "intact" cage = a cage where ≥90% of its surrounding water molecules are classified as "hydrate-like" by CHILL+
3. Plot: `N_intact_cages(t)` and `N_occupied_cages(t)`

```python
def track_cage_integrity(cage_tracker, classifications_per_frame):
    """
    Track cage integrity over time.
    A cage is "intact" if most of its surrounding waters are hydrate-like.
    """
    intact_counts = []
    
    for frame, classes in enumerate(classifications_per_frame):
        n_intact = 0
        for cage_id, center in enumerate(cage_tracker.cage_centers_cart):
            # Find surrounding water molecules of this cage
            surrounding = find_nearby_waters(center, oxygen_positions[frame], 
                                             cell_matrix, radius=0.6)  # ~6 Å
            if len(surrounding) > 0:
                hydrate_frac = np.sum(classes[surrounding] >= 4) / len(surrounding)
                if hydrate_frac > 0.5:
                    n_intact += 1
        
        intact_counts.append(n_intact)
    
    return intact_counts
```

### Method: Potential Energy Decomposition

Decompose the total potential energy into guest-host and host-host contributions over time. Rising guest-host interaction energy indicates weakening hydrate stability.

**Requires**: GROMACS energy file (`.edr`) or LAMMPS thermo output. This is a post-processing step, not a per-frame structural analysis.

### Feasibility Assessment

- **Lines of code**: ~100-150 (per-frame classification + counting)
- **Complexity**: MEDIUM (depends on underlying classification method)
- **Dependencies**: numpy + CHILL+ or F4 implementation; MDAnalysis for trajectory I/O
- **Blockers**: Speed depends on classification algorithm. CHILL+ per frame for 10K waters ≈ 0.5-2 seconds. For 10K frames → ~3-6 hours. Consider frame subsampling (every 10th or 100th frame).
- **Confidence**: HIGH (well-established method in hydrate MD literature)

---

## 2. Guest Molecule Residence Time

### What It Measures

How long a guest molecule continuously occupies a particular cage before exchanging to another cage or escaping to the liquid/bulk phase. This quantifies the kinetic stability of guest encapsulation.

### Method: Continuous and Intermittent Correlation Functions

**Source**: Standard methodology from gas hydrate MD literature.

**Step 1**: For each frame, determine which cage (if any) each guest molecule occupies using the cage tracker (ALGO-CAGE.md).

```python
def build_occupancy_timeline(cage_tracker, trajectory):
    """
    Build a timeline: for each guest, which cage is it in at each frame?
    
    Returns:
        timeline: (N_frames, N_guests) array of cage IDs (or -1 if not in any cage)
    """
    N_frames = len(trajectory)
    N_guests = len(trajectory[0][1])  # guest positions from first frame
    
    timeline = np.full((N_frames, N_guests), -1, dtype=int)
    
    for frame_idx, (oxy_pos, guest_pos) in enumerate(trajectory):
        occupancy = cage_tracker.update_occupancy(guest_pos, frame_idx)
        # Invert: for each guest, find which cage it's in
        for cage_id, guest_id in occupancy.items():
            if guest_id is not None:
                timeline[frame_idx, guest_id] = cage_id
    
    return timeline
```

**Step 2**: Compute residence time.

**Continuous residence time** (most common):
```
τ_continuous = average over all guest molecules of:
    (total number of frames where guest is in the SAME cage continuously)
    × Δt_frame
```

A guest "leaves" a cage when it is not found in that cage for at least one frame.

**Intermittent residence time** (accounts for brief excursions):
```
h(t) = 1 if guest is in the same cage at time t as at time 0
       0 otherwise

C(t) = ⟨h(0) · h(t)⟩  (intermittent correlation function)

τ_intermittent = ∫₀^∞ C(t) dt  (integral of correlation function)
```

The intermittent version allows for brief departures (guest temporarily leaves cage but returns).

```python
def compute_residence_times(timeline, dt_frame):
    """
    Compute continuous and intermittent residence times.
    
    Args:
        timeline: (N_frames, N_guests) array of cage IDs per frame
        dt_frame: time between frames in ps
    
    Returns:
        continuous_residence: list of continuous residence times per guest-cage event
        intermittent_corr: intermittent correlation function C(t)
    """
    N_frames, N_guests = timeline.shape
    continuous_residences = []
    
    # Continuous residence time
    for guest_id in range(N_guests):
        cage_history = timeline[:, guest_id]
        
        # Find continuous segments in the same cage
        current_cage = cage_history[0]
        segment_start = 0
        
        for t in range(1, N_frames):
            if cage_history[t] != current_cage:
                if current_cage >= 0:  # was in a cage
                    duration = (t - segment_start) * dt_frame
                    continuous_residences.append(duration)
                current_cage = cage_history[t]
                segment_start = t
        
        # Last segment
        if current_cage >= 0:
            duration = (N_frames - segment_start) * dt_frame
            continuous_residences.append(duration)
    
    # Intermittent correlation function
    C = np.zeros(N_frames)
    for t in range(N_frames):
        same_cage = np.array([
            timeline[t, g] == timeline[0, g] and timeline[0, g] >= 0
            for g in range(N_guests)
        ])
        C[t] = np.mean(same_cage)
    
    return continuous_residences, C
```

### Feasibility Assessment

- **Lines of code**: ~150-200
- **Complexity**: LOW-MEDIUM
- **Dependencies**: numpy + cage tracker (from ALGO-CAGE.md)
- **Blockers**: 
  - Guest tracking across PBC: guest molecules may be re-imaged by GROMACS, causing apparent "jumps". Must unwrap trajectories first.
  - Guest identity: GROMACS may reorder atoms between frames. Use MDAnalysis to maintain consistent atom indexing.
- **Confidence**: HIGH (well-established methodology)

---

## 3. Density Profile Analysis

### What It Measures

The spatial density distribution of water and guest molecules along a specified axis (typically z, normal to the hydrate-liquid interface). Used to:
1. Identify the hydrate-liquid interface position
2. Determine interface width
3. Quantify guest density inside vs outside cages

### Method: Binned Density Profile with PBC

```python
def compute_density_profile(positions, cell_matrix, axis=2, n_bins=200):
    """
    Compute 1D density profile along the specified axis.
    
    Args:
        positions: (N, 3) Cartesian positions
        cell_matrix: (3, 3) cell matrix
        axis: axis along which to compute profile (0=x, 1=y, 2=z)
        n_bins: number of bins
    
    Returns:
        bin_centers: (n_bins,) bin center positions
        density: (n_bins,) number density in each bin (molecules/nm³)
    """
    # Cell length along the axis
    L = np.linalg.norm(cell_matrix[axis])
    
    # Bin positions
    bin_edges = np.linspace(0, L, n_bins + 1)
    bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    bin_width = L / n_bins
    
    # Histogram of positions along axis
    counts, _ = np.histogram(positions[:, axis] % L, bins=bin_edges)
    
    # Number density (molecules per nm³)
    # Cross-sectional area = volume / L_axis
    cell_volume = np.abs(np.linalg.det(cell_matrix))
    cross_area = cell_volume / L
    
    density = counts / (cross_area * bin_width)
    
    return bin_centers, density


def identify_interface(bin_centers, density_water, threshold_fraction=0.5):
    """
    Identify hydrate-liquid interface position from density profile.
    
    The interface is where the water density drops to a fraction of the 
    hydrate bulk density.
    
    Args:
        bin_centers: bin positions
        density_water: water density profile
        threshold_fraction: fraction of bulk hydrate density (default 0.5)
    
    Returns:
        interface_positions: list of z-positions where interface occurs
        interface_width: approximate interface width
    """
    # Find bulk hydrate density (maximum region)
    max_density = np.max(density_water)
    bulk_hydrate = max_density * 0.9  # 90% of max as bulk reference
    
    threshold = bulk_hydrate * threshold_fraction
    
    # Find crossing points
    above = density_water > threshold
    crossings = np.where(np.diff(above.astype(int)))[0]
    
    interface_positions = bin_centers[crossings]
    
    if len(interface_positions) >= 2:
        interface_width = interface_positions[-1] - interface_positions[0]
    else:
        interface_width = 0.0
    
    return interface_positions, interface_width
```

### Method: Using MDAnalysis (Alternative)

MDAnalysis 2.10 has a `DensityAnalysis` class that computes 3D density grids:

```python
import MDAnalysis as mda
from MDAnalysis.analysis.density import DensityAnalysis

# Load trajectory
u = mda.Universe('topol.tpr', 'traj.xtc')

# Select oxygen atoms
oxygens = u.select_atoms('name OW')

# Compute density
dens = DensityAnalysis(oxygens, delta=0.5).run()
dens.density.export('water_density.dx', type='dx')
```

**Limitation**: MDAnalysis's DensityAnalysis computes 3D density. For 1D profiles along z, custom binning (as above) is simpler and faster.

### Interface Width from Hyperbolic Tangent Fit

The hydrate-liquid interface density profile is well-fitted by:

```
ρ(z) = 0.5 * (ρ_hydrate + ρ_liquid) - 0.5 * (ρ_hydrate - ρ_liquid) * tanh((z - z_interface) / d)
```

where `d` is the interface width. Fitting this to the computed profile gives both the interface position `z_interface` and width `d`.

```python
from scipy.optimize import curve_fit

def tanh_profile(z, rho_h, rho_l, z_if, d):
    return 0.5 * (rho_h + rho_l) - 0.5 * (rho_h - rho_l) * np.tanh((z - z_if) / d)

# Fit to data
p0 = [np.max(density), np.min(density), np.mean(bin_centers), 0.5]
popt, pcov = curve_fit(tanh_profile, bin_centers, density, p0=p0)
rho_hydrate, rho_liquid, z_interface, interface_width = popt
```

### Feasibility Assessment

- **Lines of code**: ~80-120
- **Complexity**: LOW
- **Dependencies**: numpy, scipy (for curve_fit), MDAnalysis (optional, for trajectory I/O)
- **Blockers**: None significant. Standard binning + fitting approach.
- **Confidence**: HIGH (standard methodology, well-documented in MD literature)

---

## Integration Architecture

All time-series analyses depend on the per-frame classification methods:

```
Frame from trajectory
    │
    ├── CHILL+ classification → per-molecule label
    │       │
    │       ├── Hydrate stability: count molecules per label type → time series
    │       └── Cage integrity: check if cage-surrounding waters are "hydrate"
    │
    ├── Cage occupancy tracker → which guest is in which cage
    │       │
    │       ├── Residence time: continuous/intermittent from occupancy timeline
    │       └── Occupancy fraction: per cage type
    │
    └── Density profile: bin positions along z → 1D density
            │
            └── Interface position + width from tanh fit
```

### Recommended Implementation Order

1. **CHILL+ classification** (prerequisite for everything else) — ~300 lines
2. **Density profile** (simplest, no dependencies on other algorithms) — ~100 lines
3. **Hydrate stability tracking** (uses CHILL+ output) — ~100 lines
4. **Cage occupancy** (uses GenIce2 cage centers) — ~150 lines
5. **Guest residence time** (uses cage occupancy) — ~200 lines
6. **Cage integrity** (uses CHILL+ + cage centers) — ~100 lines

### Performance Estimates

For a system with ~10,000 water molecules and ~500 guest molecules, per-frame:

| Analysis | Time (estimated) | Notes |
|----------|-------------------|-------|
| CHILL+ classification | 0.5-2 sec | Bottleneck: neighbor search + spherical harmonics |
| F4 order parameter | 0.3-1 sec | Simpler than CHILL+ per frame |
| Cage occupancy | 0.01-0.05 sec | Simple distance check per cage-guest pair |
| Density profile | 0.001 sec | Just histogram binning |
| Residence time | 0.01 sec | Simple lookups from occupancy table |

For 10,000 frames: CHILL+ → ~3-6 hours; cage occupancy → ~1-2 min; density → ~10 sec.

**Optimization**: Pre-compute the CHILL+ classification for all frames, then run all downstream analyses (stability, cage integrity) from the cached classification arrays.
