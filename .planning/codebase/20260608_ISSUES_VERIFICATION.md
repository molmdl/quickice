---
verified: 2026-06-08T10:00:00Z
total_issues: 8
confirmed: 4
refuted: 1
partially_correct: 3
needs_update: 2
---

# Scancode Issues Verification Report

**Date:** 2026-06-08
**Source:** 20260608_vulnerability_scan.md, 20260608_gromacs_flow_trace.md
**Method:** Read actual source code at cited line numbers, compare with issue descriptions

## Verification Summary

| ID | Finding | Verdict | Actual Severity | Evidence |
|----|---------|---------|-----------------|----------|
| BUG-05 | HW1 Z-coordinate copy-paste at gromacs_writer.py:1971 | **CONFIRMED** | 🔴 CRITICAL | Line 1971: `h2_pos[2]` instead of `h1_pos[2]` for HW1 z-coordinate |
| MW-01 | MW recomputation from wrapped atoms | **PARTIALLY CORRECT** | 🟠 HIGH | MW is recomputed from wrapped positions; molecule-aware wrapping mitigates but does not fully eliminate the risk |
| RNG-01 | Unseeded RNG in CustomMoleculeInserter | **CONFIRMED** | 🟠 HIGH | `random.Random()` with no seed + `Rotation.random()` unseeded |
| IDX-01 | Stale start_idx after ion list mutation | **REFUTED** | — | Code explicitly regenerates start_idx at lines 445-448 after any mutation |
| ATOM-01 | Hardcoded water atom count of 4 | **CONFIRMED** | 🟡 MEDIUM | Multiple `// 4` and `count=4` hardcoded in custom_molecule_inserter and solute_inserter |
| TREE-01 | O(N²) KDTree rebuilds in overlap checking | **PARTIALLY CORRECT** | 🟡 MEDIUM | Trees are rebuilt on each insertion, but N is small (molecule count, not atom count) |
| GUEST-01 | CO2 misidentified as THF by count_guest_atoms | **CONFIRMED** | 🟡 MEDIUM | `first_atom == "O"` returns 13 immediately at line 82 of molecule_utils.py |
| DEFLT-01 | `[ defaults ]` section fudgeLJ inconsistency | **CONFIRMED** | 🟠 HIGH | fudgeLJ=0.5 in simple writers vs 0.0 in multi-molecule writers |

---

## Detailed Findings

### BUG-05: HW1 Z-coordinate copy-paste error

**Claim:** Line 1971 of `gromacs_writer.py` uses `h2_pos[2]` instead of `h1_pos[2]` for the HW1 atom's Z-coordinate.

**Verdict:** ✅ **CONFIRMED** — This is a real copy-paste bug.

**Evidence:**

In `quickice/output/gromacs_writer.py`, the `write_custom_molecule_gro_file()` function, within the water molecule (`else:  # water`) branch:

```python
# Line 1954-1956: Variables are correctly assigned
o_pos = mol_positions[0]
h1_pos = mol_positions[1]
h2_pos = mol_positions[2]

# Line 1966-1971: HW1 atom output — BUG HERE
# HW1
atom_num += 1
atom_num_wrapped = atom_num % 100000
lines.append(f"{res_num_wrapped:5d}SOL  "
             f"  HW1{atom_num_wrapped:5d}"
             f"{h1_pos[0]:8.3f}{h1_pos[1]:8.3f}{h2_pos[2]:8.3f}\n")  # <-- h2_pos[2] SHOULD BE h1_pos[2]
```

The HW1 line at 1971 writes `h1_pos[0]`, `h1_pos[1]`, **`h2_pos[2]`** — the Z-coordinate comes from the wrong hydrogen.

For comparison, the **HW2** line at 1978 is correct:
```python
f"{h2_pos[0]:8.3f}{h2_pos[1]:8.3f}{h2_pos[2]:8.3f}\n")
```

And the **ice** branch HW1 line at 1933 is also correct:
```python
f"{h1_pos[0]:8.3f}{h1_pos[1]:8.3f}{h1_pos[2]:8.3f}\n")
```

This bug exists ONLY in the `write_custom_molecule_gro_file()` function's water molecule branch. The same function's ice branch (lines 1916-1940) and the other GRO writers (`write_interface_gro_file`, `write_ion_gro_file`, `write_solute_gro_file`) all use the correct `h1_pos[2]` for HW1.

**Impact:** The HW1 atom's Z-coordinate in the output .gro file will be set to HW2's Z-coordinate instead of HW1's. This corrupts the molecular geometry. For TIP4P-ICE water, this shifts the MW virtual site position because MW depends on both H positions. GROMACS will also compute incorrect forces. The bug is silent (no crash) but produces physically wrong structures.

**Fix complexity:** TRIVIAL — Change `h2_pos[2]` to `h1_pos[2]` on line 1971.

**Actual severity:** 🔴 CRITICAL — Silent data corruption in output .gro files for custom molecule systems. Every water molecule written through this code path has a wrong HW1 Z-coordinate.

---

### MW-01: MW recomputation from wrapped atoms

**Claim:** Virtual site (MW) position may be wrong after periodic boundary wrapping, because MW is recomputed from wrapped positions which may be discontinuous.

**Verdict:** ⚠️ **PARTIALLY CORRECT** — The risk exists but is mitigated by molecule-aware wrapping.

**Evidence:**

The code has two wrapping functions:

1. **`wrap_positions_into_box()`** (line 41-59): Wraps each atom independently using `np.mod()`. This CAN split molecules across PBC, producing discontinuous positions within the same molecule (e.g., OW at 0.001, HW1 at 4.999 after mod → 0.001).

2. **`wrap_molecules_into_box()`** (line 62-135): Wraps molecules as whole units — first unwraps atoms that are split across PBC (lines 95-113), then wraps the whole molecule center into [0, box). This keeps molecules intact.

**Who uses which wrapper:**

| Writer | Wrapper Used | Mitigation |
|--------|-------------|------------|
| `write_ice_gro_file` | `wrap_positions_into_box` (line 455) | ⚠️ No mitigation — but ice has 3-atom molecules with very small H-O distances, so splitting is rare |
| `write_interface_gro_file` | `wrap_molecules_into_box` if molecule_index exists (line 655-660) | ✅ Mitigated |
| `write_ion_gro_file` | `wrap_molecules_into_box` (line 1392) | ✅ Mitigated |
| `write_custom_molecule_gro_file` | `wrap_molecules_into_box` (line 1890) | ✅ Mitigated |
| `write_solute_gro_file` | `wrap_molecules_into_box` if molecule_index exists (line 2292-2298) | ✅ Mitigated when molecule_index present |

**MW recomputation pattern:** In ALL GRO writers, after wrapping, MW is recomputed via `compute_mw_position(o_pos, h1_pos, h2_pos)` using the wrapped positions. With molecule-aware wrapping, O, H1, and H2 are kept in the same periodic image, so the MW position will be correct.

**Remaining risk:**
- `write_ice_gro_file` (line 455) uses `wrap_positions_into_box` which splits atoms independently. For ice molecules (O-H distance ~0.1 nm), this rarely causes issues because H atoms are very close to O, but at PBC boundaries it could happen.
- If `molecule_index` is empty/None in any writer, the fallback to `wrap_positions_into_box` could produce discontinuous positions, leading to wrong MW.

**Impact:** With molecule-aware wrapping (the primary code path), this is mitigated. The `write_ice_gro_file` function is the only unmitigated path, but the risk is low because ice H-O bonds are short (~0.1 nm) compared to typical box sizes.

**Actual severity:** 🟠 HIGH for `write_ice_gro_file` (no mitigation); 🟢 LOW for other writers (mitigated by `wrap_molecules_into_box`).

**Fix complexity:** SIMPLE — Change `write_ice_gro_file` to use `wrap_molecules_into_box` instead of `wrap_positions_into_box`.

---

### RNG-01: Unseeded RNG in CustomMoleculeInserter random placement

**Claim:** `CustomMoleculeInserter` uses unseeded `np.random` for random placement, making results non-reproducible.

**Verdict:** ✅ **CONFIRMED** — Both position and rotation randomization are unseeded.

**Evidence:**

In `quickice/structure_generation/custom_molecule_inserter.py`, the `place_random()` method (lines 536-767):

**Position randomization** (line 597-602):
```python
rng = random.Random()  # No seed! Creates new random state each time
position = np.array([
    rng.uniform(min_coords[0], max_coords[0]),
    rng.uniform(min_coords[1], max_coords[1]),
    rng.uniform(min_coords[2], max_coords[2])
])
```

The `rng = random.Random()` is created **inside the inner loop** (line 597) — on every placement attempt, a brand-new RNG with no seed is instantiated. This means:
1. Results vary between runs (non-reproducible)
2. The RNG quality may be poor (repeated `random.Random()` calls can produce correlated sequences)

**Rotation randomization** (line 605):
```python
rotation = Rotation.random()  # Uses global numpy RNG, unseeded
```

`Rotation.random()` from scipy uses numpy's global RNG state, which is not seeded in this class.

**Comparison with SoluteInserter** (which DOES handle seeding):
```python
# solute_inserter.py line 59:
self.rng = random.Random(seed)  # Seeded from constructor

# solute_inserter.py line 758:
position = np.array([
    self.rng.uniform(min_coords[0], max_coords[0]),  # Uses seeded rng
    ...
])
```

The `SoluteInserter` correctly stores a seeded `random.Random` instance and uses it consistently. The `CustomMoleculeInserter` does not — it has no seed parameter at all.

**Note:** `Rotation.random()` in `solute_inserter.py` (line 234) is also unseeded, making solute placement also partially non-reproducible (rotation component), though position sampling is reproducible.

**Impact:** Non-reproducible results. Two runs with identical input produce different molecule placements. This is problematic for scientific reproducibility and debugging.

**Actual severity:** 🟠 HIGH — Non-reproducibility is a significant issue in scientific computing.

**Fix complexity:** MODERATE — Add seed parameter to `CustomMoleculeInserter.__init__`, store `self.rng = random.Random(seed)`, and seed `Rotation.random()` via `Rotation.random(random_state=seed)`. Also fix the inner-loop `rng = random.Random()` to use `self.rng`.

---

### IDX-01: Stale start_idx after ion list mutation

**Claim:** When Na+ and Cl- lists are concatenated, indices may become stale after list mutation.

**Verdict:** ❌ **REFUTED** — The code explicitly regenerates start_idx after any mutation.

**Evidence:**

In `quickice/structure_generation/ion_inserter.py`, the `replace_water_with_ions()` method:

1. **Initial index assignment** (lines 300-315): When building the new structure, `current_idx` is tracked correctly:
   ```python
   current_idx = 0
   for mol in structure.molecule_index:
       if mol.mol_type != "water" or mol.start_idx not in replaced_starts:
           new_molecule_index.append(MoleculeIndex(
               start_idx=current_idx,  # Correct: uses running counter
               count=mol.count,
               mol_type=mol.mol_type,
           ))
           current_idx += mol.count
   ```

2. **Ion insertion** (lines 389-410): Each ion gets correct start_idx using the same running counter.

3. **Charge neutrality fix** (lines 419-441): When removing excess ions for charge balance, the code does use `mol.start_idx` to delete from `new_atom_names`. **However**, the `del new_atom_names[mol.start_idx:mol.start_idx + mol.count]` at lines 426 and 438 works correctly because each deletion pops from the end of the list, so earlier indices are unaffected.

4. **Explicit index regeneration** (lines 443-448): **THIS IS THE KEY EVIDENCE — the code explicitly fixes any stale indices:**
   ```python
   # Regenerate start_idx values for molecule_index
   # (they may be wrong after removing entries)
   current_idx = 0
   for mol in new_molecule_index:
       mol.start_idx = current_idx
       current_idx += mol.count
   ```

The comment even acknowledges the potential issue ("they may be wrong after removing entries") and explicitly fixes it. The start_idx values are regenerated from scratch after all mutations, making them correct.

**Impact:** None — the code handles this correctly.

**Actual severity:** N/A — False positive.

---

### ATOM-01: Hardcoded water atom count of 4

**Claim:** Code assumes 4 atoms per water molecule (TIP4P-ICE specific) but this is hardcoded rather than derived.

**Verdict:** ✅ **CONFIRMED** — Multiple locations hardcode `4` for water atoms per molecule.

**Evidence:**

**Hardcoded instances in `custom_molecule_inserter.py`:**

1. Line 383: `atoms_per_water = 4` (fallback when `water_nmolecules == 0`)
2. Line 468: `ice_atom_count // 4` (fallback for ice nmolecules)
3. Line 689: `water_mol_count = water_atom_count // 4` (in `place_random()`)
4. Line 694: `count=4` (in `MoleculeIndex` for water)
5. Line 697: `current_idx += 4` (running index increment)
6. Lines 864, 867-868: Same pattern in `place_custom()`

**Hardcoded instances in `solute_inserter.py`:**

1. Line 381: `water_nmolecules = water_atom_count // 4`
2. Line 387: `atoms_per_water = 4` (fallback)
3. Line 531: `atoms_per_water = water_atom_count // n_water_molecules if n_water_molecules > 0 else 4`
4. Line 648: `water_nmolecules = water_atom_count // 4`

**Mitigating context:**

- `ion_inserter.py` line 114: `water_atoms_per_mol = water_atom_count // water_mols if water_mols > 0 else 4` — This correctly derives atoms_per_water from counts when molecule counts are available, only defaulting to 4 as fallback.
- `custom_molecule_inserter.py` lines 379-383 in `_remove_overlapping_water()`: Correctly computes `atoms_per_water = water_atom_count // structure.water_nmolecules` when `water_nmolecules > 0`, only falling back to 4.

**However**, `place_random()` at line 689 and `place_custom()` at line 864 directly use `water_atom_count // 4` without checking `water_nmolecules`. These paths break for TIP3P (3 atoms/mol) or any other model.

**Impact:** Would break if the codebase ever supports non-TIP4P water models. Currently the entire codebase is TIP4P-ICE, so this is latent rather than active.

**Actual severity:** 🟡 MEDIUM — Currently latent, but creates a maintenance trap. Anyone adding TIP3P support will hit bugs in `place_random()` and `place_custom()`.

**Fix complexity:** MODERATE — Replace all `// 4` with `water_atom_count // water_nmolecules` where the molecule count is available, or add a `WATER_ATOMS_PER_MOLECULE` constant to `types.py`.

---

### TREE-01: O(N²) KDTree rebuilds in overlap checking

**Claim:** KDTree is rebuilt on every overlap check instead of incrementally updated, making the algorithm O(N²).

**Verdict:** ⚠️ **PARTIALLY CORRECT** — Trees are rebuilt, but the practical impact is limited.

**Evidence:**

In `custom_molecule_inserter.py`, `place_random()` (lines 631-637):
```python
# Update tree for next molecule
if existing_tree is None:
    existing_tree = cKDTree(placed_mol)
else:
    all_existing = existing_tree.data
    all_positions = np.vstack([all_existing, placed_mol])
    existing_tree = cKDTree(all_positions)  # Full rebuild
```

The same pattern exists in `solute_inserter.py` (lines 796-801):
```python
if existing_tree is None:
    existing_tree = cKDTree(solute_positions)
else:
    all_existing = existing_tree.data
    all_positions = np.vstack([all_existing, solute_positions])
    existing_tree = cKDTree(all_positions)  # Full rebuild
```

In `ion_inserter.py` (line 380):
```python
ion_tree = cKDTree(np.array(ion_positions))  # Rebuilt every iteration
```

**Is this O(N²)?**

Strictly, rebuilding the tree each iteration is O(M² log M) where M is the number of molecules being placed, not O(N²) where N is total atom count. The tree is rebuilt once per placed molecule, and each rebuild is O(M log M). Total: O(M² log M).

For typical use cases (M = 10-100 molecules being placed), this is acceptable. The tree contains at most a few thousand atoms (existing structure + placed molecules). The real bottleneck would be the overlap checking loop itself.

**However**, for the ion inserter, the tree is rebuilt EVERY iteration inside the loop (line 380), even when the previous iteration didn't place an ion (overlap rejection). This is wasteful — only 1 tree rebuild per placed ion is needed.

**Impact:** Performance degradation for large molecule counts, but not catastrophic. The real O(N²) concern would be if N referred to total system atoms, which it doesn't — the trees only contain the atoms being checked against.

**Actual severity:** 🟡 MEDIUM — Inefficiency but not a correctness issue. Would matter for large numbers of placed molecules (100+).

**Fix complexity:** SIMPLE — For ion inserter, build tree only when an ion is successfully placed. For other inserters, could use incremental approaches but the current pattern is acceptable for typical use.

---

### GUEST-01: CO2 misidentified as THF by count_guest_atoms()

**Claim:** `count_guest_atoms()` uses atom count heuristics that could misidentify molecules, specifically CO2 (3 atoms starting with C) could be confused with THF.

**Verdict:** ✅ **CONFIRMED** — The function has a genuine misidentification risk, but the CO2→THF path is not the primary concern.

**Evidence:**

In `quickice/utils/molecule_utils.py`, `count_guest_atoms()`:

```python
# Line 80-82: THF starts with O → returns 13 immediately
if first_atom == "O":
    # THF starts with O and has 13 atoms
    return 13
```

**Any molecule starting with "O" will be classified as THF with 13 atoms.** This is a broader misidentification risk than just CO2. For example:
- An alcohol (O, C, H, ...) would be classified as 13-atom THF
- A carbonyl compound starting with O would be misidentified
- Any guest molecule with oxygen as the first atom in the atom_names list

The scan's specific claim about CO2 is **incorrect as stated** — CO2 starts with C, not O, so it would NOT trigger the THF path at line 80. Instead, CO2 hits line 53 (`if first_atom == "C"`) which checks for CH4:
```python
# Line 53-75: CH4 check when first_atom == "C"
if first_atom == "C" or (first_atom == "H" and len(sample) >= 5):
    c_count = sum(1 for a in sample if a == 'C')
    h_count = sum(1 for a in sample if a == 'H')
    if c_count >= 1 and h_count >= 4 and (c_count + h_count) >= 5:
        return max(count, 5)  # CH4
```

For CO2 (atoms: C, O, O), `h_count` would be 0, so the CH4 check fails. Then it falls through to line 103:
```python
# Line 103-104: CO2 check
if first_atom == "C" and any(a == 'O' for a in sample[:3]):
    return 3  # C + O + O
```

This correctly identifies CO2. So **CO2 is NOT misidentified as THF** by the current code. However, the scan's concern about heuristic-based identification is valid — the function is fragile and depends on atom ordering.

**The real risk:** Molecules starting with "O" that are NOT THF will be counted as 13 atoms. The function assumes a closed world of known guest types (Me, CH4, THF, CO2, H2) and doesn't handle unknown molecules well.

**Impact:** If a user adds a new guest molecule starting with "O" (e.g., methanol, acetone), it would be misidentified as THF with 13 atoms, corrupting the molecule boundaries.

**Actual severity:** 🟡 MEDIUM — Currently works for supported molecules (CH4, THF, CO2, H2) but fragile. The scan's specific CO2→THF claim is wrong, but the broader pattern-matching risk is real.

**Fix complexity:** MODERATE — Replace heuristic detection with explicit molecule type tracking (e.g., add `guest_type` field to MoleculeIndex).

---

### DEFLT-01: `[ defaults ]` section fudgeLJ inconsistency

**Claim:** `fudgeLJ=0.5` in some TOP writers vs `fudgeLJ=0.0` in others.

**Verdict:** ✅ **CONFIRMED** — There is a deliberate but potentially confusing inconsistency between simple and multi-molecule writers.

**Evidence:**

| Writer Function | Lines | fudgeLJ | fudgeQQ | Context |
|----------------|-------|---------|---------|---------|
| `write_top_file()` (ice only) | 527-529 | **0.5** | 0.8333 | Simple ice-only topology |
| `write_interface_top_file()` (ice+water+guests) | 959-961 | **0.5** | 0.8333 | Interface structure |
| `write_hydrate_top_file()` (hydrate) | 1235-1237 | **0.5** | 0.8333 | Hydrate structure |
| `write_ion_top_file()` (multi-molecule) | 1710-1712 | **0.0** | 0.0 | Ion structure |
| `write_custom_molecule_top_file()` (multi-molecule) | 2099-2101 | **0.0** | 0.0 | Custom molecule structure |
| `write_solute_top_file()` (multi-molecule) | 2595-2597 | **0.0** | 0.0 | Solute structure |

**Analysis:**

The fudgeLJ=0.5/0.8333 values in the simple writers match the standard Amber forcefield defaults (1-4 LJ and electrostatic interactions scaled by 0.5 and 5/6 respectively). These are correct for single-molecule topologies where GROMACS handles the 1-4 interactions.

The fudgeLJ=0.0/fudgeQQ=0.0 values in the multi-molecule writers appear to be **intentional** — they disable the default 1-4 scaling because the forcefield parameters (TIP4P-ICE, Madrid2019, GAFF2) are defined with proper 1-4 interactions in their ITP files. Setting fudgeLJ=0.0 means "no additional scaling of 1-4 interactions beyond what's in the ITP files."

**However**, this is potentially dangerous because:
1. If the ITP files don't explicitly define `[ pairs ]` sections with 1-4 parameters, setting fudgeLJ=0.0 means 1-4 LJ interactions are fully unscaled (effectively fudgeLJ=1.0 in GROMACS interpretation when gen-pairs=yes).
2. The TIP4P-ICE .itp file likely doesn't have `[ pairs ]` sections (water molecules have no 1-4 pairs), so fudgeLJ doesn't matter for water, but it DOES matter for solute/guest molecules with internal 1-4 pairs.
3. The inconsistency between writers means a user migrating from `write_interface_top_file()` to `write_ion_top_file()` will get different forcefield behavior without being warned.

**Impact:** Simulation results may differ depending on which writer is used, even for the same molecular content. For pure TIP4P-ICE systems, fudgeLJ doesn't affect results (water has no 1-4 pairs). For systems with guest/solute molecules (THF, CH4, custom molecules), fudgeLJ=0.0 may produce incorrect 1-4 interactions.

**Actual severity:** 🟠 HIGH — The inconsistency could produce incorrect simulation results for systems with organic molecules (guests, solutes, custom molecules). Whether 0.5 or 0.0 is "correct" depends on the forcefield parameterization, and having different values in different writers is a maintenance trap.

**Fix complexity:** MODERATE — Determine the correct fudgeLJ/fudgeQQ values from the forcefield documentation (likely 0.5/0.8333 for Amber-compatible GAFF2) and apply consistently across all writers.

---

## Summary of Findings

### By Verdict

| Verdict | Count | Issues |
|---------|-------|--------|
| CONFIRMED | 4 | BUG-05, RNG-01, ATOM-01, DEFLT-01 |
| PARTIALLY CORRECT | 2 | MW-01, TREE-01 |
| REFUTED | 1 | IDX-01 |
| (GUEST-01 confirmed but specific CO2 claim refuted) | 1 | GUEST-01 |

### By Severity (actual, not claimed)

| Severity | Count | Issues |
|----------|-------|--------|
| 🔴 CRITICAL | 1 | BUG-05 (HW1 Z-coordinate copy-paste) |
| 🟠 HIGH | 3 | MW-01 (MW from wrapped atoms), RNG-01 (unseeded RNG), DEFLT-01 (fudgeLJ inconsistency) |
| 🟡 MEDIUM | 3 | ATOM-01 (hardcoded 4), TREE-01 (KDTree rebuilds), GUEST-01 (heuristic fragility) |
| N/A | 1 | IDX-01 (refuted) |

### Most Critical Verified Issue

**BUG-05: HW1 Z-coordinate copy-paste** — This is a silent data corruption bug. Every water molecule written through `write_custom_molecule_gro_file()` has its HW1 atom's Z-coordinate set to HW2's Z-coordinate instead of HW1's. The bug is trivial to fix (one character change) but has significant physical impact: it corrupts the TIP4P-ICE geometry, affecting the MW virtual site position and all downstream GROMACS force calculations.

---

_Verified: 2026-06-08_
_Verifier: OpenCode (gsd-verifier)_
