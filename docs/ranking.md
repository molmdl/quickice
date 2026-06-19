# QuickIce Ranking Methodology

This document explains how QuickIce ranks ice structure candidates.

## Overview

QuickIce generates multiple candidate structures for given thermodynamic conditions and ranks them using three scoring components:

1. **Energy Score** - Based on O-O distance deviation from ideal
2. **Density Score** - Comparison to expected phase density
3. **Diversity Score** - Penalizes structural similarity via O-O distance fingerprint

These scores are combined into a single ranking score, with lower values indicating better candidates.

---

## Energy Score

### Concept

The energy score estimates how "ideal" the ice structure is based on O-O (oxygen-oxygen) distances. In ice, oxygen atoms are connected by hydrogen bonds with a characteristic O-O distance of approximately 0.276 nm. Structures with O-O distances close to this ideal value are assumed to have lower energy.

### Formula

```
energy_score = mean(|d_OO - 0.276|) × 100
```

Where:
- `d_OO` = O-O distances within cutoff (0.35 nm)
- `0.276` = Ideal O-O distance in nm (Petrenko & Whitworth, 1999, Physics of Ice)
- `100` = Scaling factor for visibility

### Interpretation

- **Lower score = better** (closer to ideal O-O distances)
- Typical range: 0.1 - 1.0 (for reasonable structures)
- `inf` = No O-O pairs found (degenerate case)

### Example Calculation

For a structure with O-O distances: [0.274, 0.278, 0.280, 0.275] nm

```
deviations = |0.274 - 0.276|, |0.278 - 0.276|, |0.280 - 0.276|, |0.275 - 0.276|
deviations = 0.002, 0.002, 0.004, 0.001
mean_deviation = (0.002 + 0.002 + 0.004 + 0.001) / 4 = 0.00225 nm
energy_score = 0.00225 × 100 = 0.225
```

### Important Notes

**This is NOT an actual energy calculation.** This is an estimation based on O-O distance statistics. For real energies, use molecular dynamics simulations with appropriate force fields.

---

## Density Score

### Concept

The density score measures how closely the candidate's actual density matches the expected density for its phase. Each ice polymorph has a characteristic density at given conditions.

### Formula

```
density_score = |actual_density - expected_density|
```

Where:
- `actual_density` = Calculated from structure (g/cm³)
- `expected_density` = From phase metadata (default: 0.9167 g/cm³ for Ice Ih)

### Density Calculation

```
actual_density = (n_molecules × 18.01528 g/mol) / (N_A × volume_cm³)
```

Where:
- `n_molecules` = Number of water molecules
- `18.01528` = Molecular mass of water (g/mol)
- `N_A` = Avogadro's number (6.022 × 10²³)
- `volume_cm³` = Cell volume in cm³

### Interpretation

- **Lower score = better** (closer match to expected density)
- Units: g/cm³
- Typical range: 0.0 - 0.1 for good matches

### Example Calculation

For Ice Ih with 100 molecules in a cell of 30.5 nm³:

```
volume_cm³ = 30.5 × 10⁻²¹ = 3.05 × 10⁻²⁰ cm³
actual_density = (100 × 18.01528) / (6.022e23 × 3.05e-20) = 0.980 g/cm³
expected_density = 0.9167 g/cm³ (Ice Ih at standard conditions)
density_score = |0.980 - 0.9167| = 0.063 g/cm³
```

---

## Diversity Score

### Concept

The diversity score measures how structurally unique a candidate is compared to others in the same generation batch. It uses O-O (oxygen-oxygen) distance distribution histograms as structural fingerprints: candidates with similar O-O distance distributions are structurally alike, while those with different distributions are truly diverse.

### Algorithm

1. **Compute O-O distance histogram** for each candidate:
   - Extract oxygen atom positions (O or OW names)
   - Calculate O-O distances using `cKDTree` with `boxsize` parameter for periodic boundary conditions (orthorhombic cells) or 3×3×3 supercell fallback (triclinic cells)
   - Build a 20-bin normalized histogram over the range `[0, oo_cutoff]` (default 0.35 nm)

2. **Compare fingerprints** using cosine similarity:
   - For each candidate, compute cosine similarity of its histogram against every other candidate's histogram
   - Cosine similarity ∈ [0, 1], where 1 = identical distributions

3. **Compute diversity score**:
   ```
   diversity_score = 1 - mean_similarity
   ```

### Formula

```
diversity_score = 1 - (1/N) × Σ cos_sim(hist_i, hist_j)   for all j ≠ i
```

Where:
- `hist_i` = Normalized O-O distance histogram for candidate i (20 bins)
- `cos_sim` = Cosine similarity between histogram vectors
- `N` = Number of other candidates in the batch

### Degenerate Cases

| Condition | Return Value | Rationale |
|-----------|-------------|-----------|
| Single candidate in batch | 0.5 | Neutral — no comparison possible |
| No oxygen atoms found | 0.5 | Cannot compute fingerprint |
| No O-O distances within cutoff | 0.5 | Zero-norm histogram |

### Interpretation

- **Higher score = more structurally unique**
- `~1.0` = Very different from all others (diverse)
- `~0.0` = Very similar to others (not diverse)
- `0.5` = Neutral (degenerate case or single candidate)

### Example Calculation

In a batch of 3 candidates with O-O distance histograms A, B, C:

```
cos_sim(A, B) = 0.92    (similar structures)
cos_sim(A, C) = 0.35    (different structures)

mean_similarity for A = (0.92 + 0.35) / 2 = 0.635
diversity_score for A = 1 - 0.635 = 0.365
```

---

## Combined Score

### Normalization

Each component score is normalized to a 0-1 range using min-max scaling:

```
normalized = (score - min) / (max - min)
```

For all scores equal, normalized = 0.

### Combination Formula

```
combined_score = w_energy × norm_energy 
               + w_density × norm_density 
               + w_diversity × (1 - norm_diversity)
```

Where:
- Default weights: `w_energy = w_density = w_diversity = 1.0` (equal weighting)
- `1 - norm_diversity` inverts diversity (higher diversity → lower combined score)

### Interpretation

- **Lower combined score = better**
- `0` = Best possible (lowest energy, closest density, most unique)
- Scores are comparable across batches with the same number of candidates

### Example

For a candidate with:
- norm_energy = 0.2
- norm_density = 0.3
- norm_diversity = 1.0 (most unique)

```
combined_score = 1.0 × 0.2 + 1.0 × 0.3 + 1.0 × (1 - 1.0)
combined_score = 0.2 + 0.3 + 0.0 = 0.5
```

---

## Ranking Process

1. Generate candidates for the specified phase
2. Calculate raw scores for each component
3. Normalize scores to 0-1 range
4. Compute combined score with weights
5. Sort by combined_score (ascending, lower = better)
6. Assign ranks (rank 1 = best)

---

## Limitations

### Energy Score

- **Not a real energy calculation** - Based on O-O distance statistics only
- Does not account for hydrogen bond angles
- Does not consider proton ordering
- For accurate energies, use molecular dynamics with TIP3P/TIP4P force fields

### Density Score

- Expected densities are approximate (from literature at standard conditions)
- Does not account for temperature/pressure effects on density
- May not be accurate for metastable phases

### Diversity Score

- Based on O-O distance distributions only; does not consider hydrogen positions or bond angles
- Cosine similarity measures distribution shape, not absolute distances
- Small batches may produce unreliable similarity estimates

### General

- Scoring is estimated based on geometry
- Not a replacement for rigorous physics-based analysis
- For production use, validate top candidates with proper MD simulations

---

## Customizing Weights

Weights can be customized to prioritize different scoring components:

```python
from quickice.ranking.scorer import rank_candidates

# Prioritize energy over density
weights = {'energy': 2.0, 'density': 0.5, 'diversity': 1.0}
result = rank_candidates(candidates, weights=weights)
```

Higher weight = more influence on final ranking.

---

## See Also

- [CLI Reference](./cli-reference.md) - Command-line usage
- [Principles](./principles.md) - QuickIce philosophy and approach
