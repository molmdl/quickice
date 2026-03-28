# QuickIce Ranking Methodology

This document explains how QuickIce ranks ice structure candidates.

## Overview

QuickIce generates multiple candidate structures for given thermodynamic conditions and ranks them using three scoring components:

1. **Energy Score** - Based on O-O distance deviation from ideal
2. **Density Score** - Comparison to expected phase density
3. **Diversity Score** - Rewards unique structural seeds

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
- `0.276` = Ideal O-O distance in nm (typical hydrogen bond length)
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

**This is NOT an actual energy calculation.** This is a heuristic based on O-O distance statistics. For real energies, use molecular dynamics simulations with appropriate force fields.

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

The diversity score rewards structures generated from unique random seeds. When multiple candidates share the same seed, they are less diverse and receive lower scores.

### Formula

```
diversity_score = 1.0 / seed_count
```

Where:
- `seed_count` = Number of candidates with the same seed

### Interpretation

- **Higher score = more unique**
- `1.0` = Most unique (seed appears once)
- `0.5` = Seed appears twice
- `0.33` = Seed appears three times

### Example Calculation

In a batch of 5 candidates with seeds [1, 2, 1, 3, 1]:

```
Candidate with seed 1: diversity_score = 1.0 / 3 = 0.33
Candidate with seed 2: diversity_score = 1.0 / 1 = 1.0
Candidate with seed 3: diversity_score = 1.0 / 1 = 1.0
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

- Based on random seeds, not structural fingerprints
- Does not detect structural similarity between different seeds
- May not capture true structural diversity

### General

- Scoring is heuristic, suitable for "vibe coding" exploration
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
