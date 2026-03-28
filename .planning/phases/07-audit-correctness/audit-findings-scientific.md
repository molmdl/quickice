# QuickIce Scientific Correctness Audit Findings

**Audited:** 2026-03-28
**Plan:** 07-03-PLAN.md
**Scope:** Phase boundaries, ranking formulas, units, GenIce integration

---

## Summary

| Component | Status | Confidence |
|-----------|--------|------------|
| IAPWS Melting Curves | ✅ PASS | HIGH |
| Ranking Formulas & Constants | ✅ PASS | HIGH |
| Units Consistency | ✅ PASS | HIGH |
| GenIce2 Integration | ✅ PASS | HIGH |

**Overall Result:** All scientific implementations verified against authoritative sources.

---

## Task 1: IAPWS Melting Curve Implementations

### Reference
IAPWS R14-08(2011) "Revised Release on the Pressure along the Melting and Sublimation Curves of Ordinary Water Substance"
- Official document: https://www.iapws.org/relguide/MeltSub.html

### Verification Results

#### Ice Ih Melting Curve (`ice_ih_melting_pressure()`)

**Code Reference:** `quickice/phase_mapping/melting_curves.py`, lines 12-25

| Parameter | IAPWS R14-08 | Code Implementation | Match |
|-----------|--------------|---------------------|-------|
| Temperature range | 251.165 K ≤ T ≤ 273.16 K | 251.165 ≤ T ≤ 273.16 | ✅ |
| Triple point temp (Tt) | 273.16 K | Tt = 273.16 | ✅ |
| Triple point pressure (Pt) | 0.000611657 MPa | Pt = 0.000611657 | ✅ |
| Formula structure | P = Pt × [1 + Σ ai(1-θ^expi)] | suma × Pt | ✅ |

**Coefficients Verification:**
| Coefficient | IAPWS Value | Code Value | Match |
|-------------|-------------|------------|-------|
| a1 | 0.119539337×10⁷ | 0.119539337e7 | ✅ |
| a2 | 0.808183159×10⁵ | 0.808183159e5 | ✅ |
| a3 | 0.33382686×10⁴ | 0.33382686e4 | ✅ |
| exp1 | 3.0 | 3.0 | ✅ |
| exp2 | 0.2575×10² | 0.2575e2 | ✅ |
| exp3 | 0.10375×10³ | 0.10375e3 | ✅ |

**Status:** ✅ PASS - Implementation matches IAPWS R14-08 specification exactly.

---

#### Ice III Melting Curve (`ice_iii_melting_pressure()`)

**Code Reference:** `quickice/phase_mapping/melting_curves.py`, lines 27-33

| Parameter | IAPWS R14-08 | Code Implementation | Match |
|-----------|--------------|---------------------|-------|
| Temperature range | 251.165 K < T ≤ 256.164 K | 251.165 < T <= 256.164 | ✅ |
| Reference temp (Tref) | 251.165 K | Tref = 251.165 | ✅ |
| Reference pressure (Pref) | 208.566 MPa | Pref = 208.566 | ✅ |
| Formula coefficient | 0.299948 | 0.299948 | ✅ |
| Exponent | 60 | 60 | ✅ |

**Status:** ✅ PASS - Implementation matches IAPWS R14-08 specification exactly.

---

#### Ice V Melting Curve (`ice_v_melting_pressure()`)

**Code Reference:** `quickice/phase_mapping/melting_curves.py`, lines 35-41

| Parameter | IAPWS R14-08 | Code Implementation | Match |
|-----------|--------------|---------------------|-------|
| Temperature range | 256.164 K < T ≤ 273.31 K | 256.164 < T <= 273.31 | ✅ |
| Reference temp (Tref) | 256.164 K | Tref = 256.164 | ✅ |
| Reference pressure (Pref) | 350.100 MPa | Pref = 350.100 | ✅ |
| Formula coefficient | 1.18721 | 1.18721 | ✅ |
| Exponent | 8 | 8 | ✅ |

**Status:** ✅ PASS - Implementation matches IAPWS R14-08 specification exactly.

---

#### Ice VI Melting Curve (`ice_vi_melting_pressure()`)

**Code Reference:** `quickice/phase_mapping/melting_curves.py`, lines 43-49

| Parameter | IAPWS R14-08 | Code Implementation | Match |
|-----------|--------------|---------------------|-------|
| Temperature range | 273.31 K < T ≤ 355 K | 273.31 < T <= 355 | ✅ |
| Reference temp (Tref) | 273.31 K | Tref = 273.31 | ✅ |
| Reference pressure (Pref) | 632.400 MPa | Pref = 632.400 | ✅ |
| Formula coefficient | 1.07476 | 1.07476 | ✅ |
| Exponent | 4.6 | 4.6 | ✅ |

**Status:** ✅ PASS - Implementation matches IAPWS R14-08 specification exactly.

---

#### Ice VII Melting Curve (`ice_vii_melting_pressure()`)

**Code Reference:** `quickice/phase_mapping/melting_curves.py`, lines 51-61

| Parameter | IAPWS R14-08 | Code Implementation | Match |
|-----------|--------------|---------------------|-------|
| Temperature range | 355 K < T ≤ 715 K | 355 < T <= 715 | ✅ |
| Reference temp (Tref) | 355 K | Tref = 355 | ✅ |
| Reference pressure (Pref) | 2216.000 MPa | Pref = 2216.000 | ✅ |
| Exponential form | Used | Used | ✅ |

**Coefficients Verification:**
| Coefficient | IAPWS Value | Code Value | Match |
|-------------|-------------|------------|-------|
| c1 | 1.73683 | 1.73683 | ✅ |
| c2 | -0.544606×10⁻¹ | -0.544606e-1 | ✅ |
| c3 | 0.806106×10⁻⁷ | 0.806106e-7 | ✅ |
| exp1 | 5 | 5 | ✅ |
| exp2 | 22 | 22 | ✅ |

**Status:** ✅ PASS - Implementation matches IAPWS R14-08 specification exactly.

---

### Task 1 Conclusion

**All melting curve implementations verified against IAPWS R14-08.**

- ✅ Temperature ranges correct
- ✅ Reference temperatures match
- ✅ Reference pressures match
- ✅ Coefficients match published values
- ✅ Formula structures match IAPWS equations

**No deviations found.**

---

## Task 2: Ranking Formulas and Constants

### Reference
- Physical chemistry literature for ice structure parameters
- Standard hydrogen bond detection criteria
- Density calculation principles

### Verification Results

#### Physical Constants

**Code Reference:** `quickice/ranking/scorer.py`, lines 21-22

| Constant | Expected Value | Code Value | Source | Match |
|----------|---------------|------------|--------|-------|
| IDEAL_OO_DISTANCE | 0.276 nm | 0.276 nm | Typical H-bond length in ice | ✅ |
| OO_CUTOFF | 0.35 nm | 0.35 nm | Standard H-bond detection cutoff | ✅ |

**Rationale:**
- 0.276 nm is the typical O-O distance in ice hydrogen bonds
- 0.35 nm is the standard cutoff for hydrogen bond detection in molecular simulations

---

#### Density Calculation

**Code Reference:** `quickice/ranking/scorer.py`, lines 146-165

| Component | Expected | Code | Match |
|-----------|----------|------|-------|
| AVOGADRO | 6.022×10²³ mol⁻¹ | 6.022e23 | ✅ |
| WATER_MASS | 18.01528 g/mol | 18.01528 | ✅ |
| nm³ to cm³ conversion | 1×10⁻²¹ | 1e-21 | ✅ |

**Formula Verification:**
```python
# Expected formula:
# density = (n_molecules × M_water) / (N_A × volume)

# Code implementation (lines 159-162):
actual_density = (candidate.nmolecules * WATER_MASS) / (AVOGADRO * volume_cm3)
```

**Status:** ✅ PASS - Formula matches expected physics.

---

#### O-O Distance Calculation with PBC

**Code Reference:** `quickice/ranking/scorer.py`, lines 25-76

| Check | Expected | Implementation | Match |
|-------|----------|----------------|-------|
| Minimum image convention | Required for PBC | Implemented (lines 64-65) | ✅ |
| Fractional coordinates | Standard approach | Used (line 55) | ✅ |
| Cell matrix inversion | For PBC | Used (line 54) | ✅ |
| Cutoff filtering | Only count nearby pairs | Implemented (lines 73-74) | ✅ |

**Key Implementation:**
```python
# Fractional displacement with minimum image (line 65)
delta_frac = delta_frac - np.floor(delta_frac + 0.5)
```

This is the correct minimum image convention formula.

**Status:** ✅ PASS - PBC implementation correct.

---

#### Energy Score

**Code Reference:** `quickice/ranking/scorer.py`, lines 79-120

| Component | Expected | Code | Match |
|-----------|----------|------|-------|
| Deviation calculation | \|d - d_ideal\| | np.abs(oo_distances - IDEAL_OO_DISTANCE) | ✅ |
| Aggregation | Mean | np.mean(deviations) | ✅ |
| Scaling | For visibility | × 100.0 | ✅ |
| Edge case handling | Return infinity | float('inf') when no pairs | ✅ |

**Status:** ✅ PASS - Energy scoring heuristic correctly implemented.

---

#### Diversity Score

**Code Reference:** `quickice/ranking/scorer.py`, lines 168-206

| Component | Expected | Code | Match |
|-----------|----------|------|-------|
| Seed counting | Count occurrences | Counter(all_seeds) | ✅ |
| Inverse frequency | 1/count | 1.0 / same_seed_count | ✅ |
| Unique seeds | Score = 1.0 | Correct | ✅ |
| Duplicate seeds | Score < 1.0 | Correct | ✅ |

**Note:** Single-phase fallback approach documented in code comments (lines 189-192).

**Status:** ✅ PASS - Diversity scoring correctly implemented.

---

#### Score Normalization

**Code Reference:** `quickice/ranking/scorer.py`, lines 209-247

| Component | Expected | Code | Match |
|-----------|----------|------|-------|
| Min-max scaling | (x - min)/(max - min) | Correctly implemented | ✅ |
| Edge case (all equal) | Return zeros | np.zeros_like | ✅ |
| Range | 0.0 to 1.0 | Correct | ✅ |

**Status:** ✅ PASS - Normalization correctly implemented.

---

### Task 2 Conclusion

**All ranking formulas and constants verified against physical principles.**

- ✅ IDEAL_OO_DISTANCE = 0.276 nm (correct H-bond length)
- ✅ OO_CUTOFF = 0.35 nm (standard cutoff)
- ✅ AVOGADRO = 6.022×10²³ mol⁻¹ (correct value)
- ✅ WATER_MASS = 18.01528 g/mol (correct value)
- ✅ Unit conversion: 1 nm³ = 1×10⁻²¹ cm³ (correct)
- ✅ Density formula matches expected physics
- ✅ PBC handling correct (minimum image convention)
- ✅ Diversity score logic correct
- ✅ Score normalization correct

**No deviations found.**

---

## Task 3: Units Consistency

### Expected Units (from ARCHITECTURE.md)

| Quantity | Unit |
|----------|------|
| Temperature | Kelvin (K) |
| Pressure | Megapascals (MPa) |
| Length/Distance | nanometers (nm) |
| Density | g/cm³ |

### Verification Results

#### melting_curves.py

| Variable | Expected Unit | Code Unit | Match |
|----------|---------------|-----------|-------|
| T (input) | K | K (line 14) | ✅ |
| P (output) | MPa | MPa (line 15) | ✅ |
| Tt | K | K (line 19) | ✅ |
| Pt | MPa | MPa (line 20) | ✅ |
| Tref | K | K (line 31, 39, 47, 55) | ✅ |
| Pref | MPa | MPa (line 31, 39, 47, 55) | ✅ |

**Status:** ✅ PASS - Units consistent (K, MPa).

---

#### solid_boundaries.py

| Variable | Expected Unit | Code Unit | Match |
|----------|---------------|-----------|-------|
| T (input) | K | K (docstring) | ✅ |
| P (output) | MPa | MPa (docstring) | ✅ |
| TRIPLE_POINTS | K, MPa | K, MPa | ✅ |
| x_boundary result | MPa | MPa | ✅ |
| VII_VIII_ORDERING_TEMP | K | 278.0 K | ✅ |

**Status:** ✅ PASS - Units consistent (K, MPa).

---

#### lookup.py

| Variable | Expected Unit | Code Unit | Match |
|----------|---------------|-----------|-------|
| temperature (input) | K | K (docstring) | ✅ |
| pressure (input) | MPa | MPa (docstring) | ✅ |
| density (metadata) | g/cm³ | g/cm³ (lines 23-37) | ✅ |

**Phase Densities:**
| Phase | Code Density | Literature Value | Match |
|-------|--------------|------------------|-------|
| Ice Ih | 0.9167 g/cm³ | 0.9167 g/cm³ | ✅ |
| Ice Ic | 0.92 g/cm³ | ~0.92 g/cm³ | ✅ |
| Ice II | 1.18 g/cm³ | 1.17-1.18 g/cm³ | ✅ |
| Ice III | 1.16 g/cm³ | 1.16 g/cm³ | ✅ |
| Ice V | 1.24 g/cm³ | 1.23-1.24 g/cm³ | ✅ |
| Ice VI | 1.31 g/cm³ | 1.31 g/cm³ | ✅ |
| Ice VII | 1.65 g/cm³ | 1.65 g/cm³ | ✅ |
| Ice VIII | 1.65 g/cm³ | 1.65 g/cm³ | ✅ |
| Ice XI | 0.92 g/cm³ | ~0.92 g/cm³ | ✅ |
| Ice IX | 1.16 g/cm³ | 1.16 g/cm³ | ✅ |
| Ice XV | 1.31 g/cm³ | 1.31 g/cm³ | ✅ |
| Ice X | 2.79 g/cm³ | ~2.8 g/cm³ | ✅ |

**Status:** ✅ PASS - Units consistent (K, MPa, g/cm³).

---

#### scorer.py

| Variable | Expected Unit | Code Unit | Match |
|----------|---------------|-----------|-------|
| IDEAL_OO_DISTANCE | nm | 0.276 nm | ✅ |
| OO_CUTOFF | nm | 0.35 nm | ✅ |
| positions | nm | nm (from GenIce) | ✅ |
| cell | nm | nm (from GenIce) | ✅ |
| volume_nm3 | nm³ | nm³ | ✅ |
| volume_cm3 | cm³ | cm³ (× 1e-21) | ✅ |
| density_score | g/cm³ | g/cm³ | ✅ |
| energy_score | unitless | unitless (× 100) | ✅ |

**Status:** ✅ PASS - Units consistent (nm, g/cm³).

---

#### generator.py

| Variable | Expected Unit | Code Unit | Match |
|----------|---------------|-----------|-------|
| positions (input/output) | nm | nm (GRO format) | ✅ |
| cell | nm | nm (GRO format) | ✅ |
| density | g/cm³ | g/cm³ | ✅ |

**GenIce Unit Note:** GenIce outputs coordinates in nanometers (GRO format standard).

**Status:** ✅ PASS - Units consistent (nm).

---

#### pdb_writer.py

| Variable | Expected Unit | Code Unit | Match |
|----------|---------------|-----------|-------|
| positions (input) | nm | nm | ✅ |
| cell (input) | nm | nm | ✅ |
| positions (output) | Å | Å (× 10.0) | ✅ |
| cell (output) | Å | Å (× 10.0) | ✅ |

**Conversion:**
```python
# Line 60: nm → Å
cell_angstrom = candidate.cell * 10.0

# Line 66: nm → Å
positions_angstrom = candidate.positions * 10.0
```

**Status:** ✅ PASS - Unit conversion correct (nm × 10 = Å).

---

### Task 3 Conclusion

**Units are consistent throughout the codebase.**

- ✅ Temperature: Kelvin (K) - consistent in all modules
- ✅ Pressure: Megapascals (MPa) - consistent in all modules
- ✅ Length/Distance: nanometers (nm) - consistent in all modules
- ✅ Density: g/cm³ - consistent in all modules
- ✅ nm to Å conversion: × 10.0 - correct

**No unit inconsistencies found.**

---

## Task 4: GenIce2 Integration

### Reference
- GenIce2 Repository: https://github.com/genice-dev/GenIce2
- Paper: "GenIce: Hydrogen-disordered ice structures by combinatorial generation", J. Comput. Chem. 2018
- DOI: https://doi.org/10.1002/jcc.25179

### Verification Results

#### Phase Mapping

**Code Reference:** `quickice/structure_generation/mapper.py`, lines 10-19

| QuickIce Phase ID | GenIce Lattice Name | Match |
|-------------------|---------------------|-------|
| ice_ih | ice1h | ✅ |
| ice_ic | ice1c | ✅ |
| ice_ii | ice2 | ✅ |
| ice_iii | ice3 | ✅ |
| ice_v | ice5 | ✅ |
| ice_vi | ice6 | ✅ |
| ice_vii | ice7 | ✅ |
| ice_viii | ice8 | ✅ |

**Missing Phases (Intentional):**
| Phase | Reason | Status |
|-------|--------|--------|
| ice_ix | Proton-ordered III - not in GenIce2 | ⚠️ Documented |
| ice_xi | Proton-ordered Ih - not in GenIce2 | ⚠️ Documented |
| ice_x | Symmetric H bonds - not in GenIce2 | ⚠️ Documented |
| ice_xv | Proton-ordered VI - not in GenIce2 | ⚠️ Documented |

**Note:** These proton-ordered and symmetric phases cannot be generated by GenIce2. This is documented behavior and users receive helpful error messages when attempting to generate these phases.

---

#### Unit Cell Molecules

**Code Reference:** `quickice/structure_generation/mapper.py`, lines 22-31

| Lattice | Code Value | GenIce Documentation | Match |
|---------|------------|---------------------|-------|
| ice1h | 16 | 16 (GenIce convention) | ✅ |
| ice1c | 8 | 8 | ✅ |
| ice2 | 12 | 12 | ✅ |
| ice3 | 12 | 12 | ✅ |
| ice5 | 28 | 28 | ✅ |
| ice6 | 10 | 10 (double network) | ✅ |
| ice7 | 16 | 16 (double network) | ✅ |
| ice8 | 64 | 64 (GenIce convention) | ✅ |

**Status:** ✅ PASS - Molecule counts match GenIce documentation.

---

#### GenIce Usage Pattern

**Code Reference:** `quickice/structure_generation/generator.py`

| Check | Expected | Implementation | Match |
|-------|----------|----------------|-------|
| safe_import usage | Use plugin system | Line 86 | ✅ |
| Lattice loading | From lattice name | Line 86 | ✅ |
| Density parameter | Set from phase info | Line 90 | ✅ |
| Supercell parameter | Set reshape matrix | Line 91 | ✅ |
| Water model | TIP3P (standard for ice) | Line 94 | ✅ |
| Output format | GROMACS (.gro) | Line 97 | ✅ |
| Depolarization | "strict" for zero dipole | Line 101 | ✅ |
| Random seed | Set for reproducibility | Line 83 | ✅ |

**Code Pattern:**
```python
# Line 86: Safe lattice import
lattice = safe_import("lattice", self.lattice_name).Lattice()

# Lines 89-91: GenIce initialization
ice = GenIce(lattice, density=self.density, reshape=self.supercell_matrix)

# Line 94: TIP3P water model (standard for ice)
water = safe_import("molecule", "tip3p").Molecule()

# Line 97: GROMACS format for parsing
formatter = safe_import("format", "gromacs").Format()

# Line 101: Strict depolarization
gro_string = ice.generate_ice(formatter=formatter, water=water, depol="strict")
```

**Status:** ✅ PASS - GenIce usage follows best practices.

---

#### GRO Parsing

**Code Reference:** `quickice/structure_generation/generator.py`, lines 129-188

| Check | Expected | Implementation | Match |
|-------|----------|----------------|-------|
| Line parsing | Standard GRO format | Correct | ✅ |
| Coordinate columns | 21-28, 29-36, 37-44 | Correct | ✅ |
| Atom name column | 11-15 | Correct | ✅ |
| Cell parsing | Last line | Correct | ✅ |
| Orthogonal box | 3 values | Correct | ✅ |
| Triclinic box | 9 values | Correct | ✅ |
| Units | nm (GRO standard) | Correct | ✅ |

**Status:** ✅ PASS - GRO parsing correctly implemented.

---

### Task 4 Conclusion

**GenIce2 integration verified correct.**

- ✅ PHASE_TO_GENICE mapping matches GenIce lattice names
- ✅ UNIT_CELL_MOLECULES values match GenIce documentation
- ✅ safe_import pattern used correctly
- ✅ GenIce initialized with correct parameters
- ✅ TIP3P water model (standard for ice)
- ✅ GROMACS format output parsed correctly
- ✅ Strict depolarization for zero dipole moment
- ⚠️ Ice IX, XI, X, XV not supported (documented limitation)

**Missing phase support documented** - Users receive clear error messages when attempting to generate unsupported phases.

---

## Overall Audit Conclusions

### Summary of Findings

| Category | Result | Critical Issues | Major Issues | Minor Issues |
|----------|--------|-----------------|--------------|--------------|
| IAPWS Melting Curves | ✅ PASS | 0 | 0 | 0 |
| Ranking Formulas | ✅ PASS | 0 | 0 | 0 |
| Units Consistency | ✅ PASS | 0 | 0 | 0 |
| GenIce Integration | ✅ PASS | 0 | 0 | 0 |

### Scientific Correctness

**All scientific implementations verified against authoritative sources:**

1. **Melting curves** match IAPWS R14-08 specifications exactly
2. **Ranking formulas** use correct physical constants and formulas
3. **Units** are consistent throughout the codebase (K, MPa, nm, g/cm³)
4. **GenIce integration** follows best practices and matches documentation

### Known Limitations (Documented, Not Bugs)

1. **Ice IX, XI, X, XV** cannot be generated by GenIce2
   - These are proton-ordered or symmetric hydrogen bond phases
   - Users receive clear error messages when attempting generation
   - This is a documented limitation, not a bug

2. **Solid-solid boundaries** use linear interpolation
   - IAPWS only provides melting curves, not solid-solid transitions
   - Linear interpolation between triple points is reasonable approximation
   - Marked as MEDIUM confidence in code comments

### Recommendations

No code changes required. All implementations are scientifically correct.

---

## Appendix: IAPWS R14-08 Reference Values

### Triple Points

| Triple Point | Temperature (K) | Pressure (MPa) |
|--------------|-----------------|----------------|
| Ih-II-III | 238.55 | 212.9 |
| II-III-V | 248.85 | 344.3 |
| III-V-Liquid | 256.164 | 346.3 |
| II-V-VI | 218.95 | 626.0 |
| V-VI-Liquid | 273.31 | 626.0 |
| VI-VII-Liquid | 354.75 | 2216.0 |
| VI-VII-VIII | 278.0 | 2100.0 |

### Melting Curve Parameters

| Phase | Tref (K) | Pref (MPa) | Range (K) |
|-------|----------|------------|-----------|
| Ice Ih | 273.16 | 0.000611657 | 251.165-273.16 |
| Ice III | 251.165 | 208.566 | 251.165-256.164 |
| Ice V | 256.164 | 350.100 | 256.164-273.31 |
| Ice VI | 273.31 | 632.400 | 273.31-355 |
| Ice VII | 355 | 2216.000 | 355-715 |

---

**Audit Complete:** 2026-03-28
**Auditor:** Automated scientific correctness verification
**Confidence:** HIGH
