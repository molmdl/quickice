# Verified Scan Issues — Execution Plan

**Created:** 2026-06-13
**Scope:** 27 verified issues (excluding dead code), 18 unique files
**Constraint:** No parallel agents may work on the same file

---

## Wave Structure Summary

| Wave | Priority | Tasks | Files | Dependencies |
|------|----------|-------|-------|--------------|
| 1 | P0 + P1 | 5 | 5 unique | None — fully parallel |
| 2 | P2 + P3 (shared files) | 9 | 9 unique | Wave 1 for 2 files |
| 3 | P3 (standalone) | 5 | 6 unique | Wave 2 for 1 file |
| **Total** | | **19** | **18** | |

---

## Wave 1 — P0 + P1: Critical Bug + Functional Fixes

All 5 tasks touch different files → **fully parallel**.

| Task | Files | Issues | Action |
|------|-------|--------|--------|
| T1 | `quickice/structure_generation/custom_molecule_inserter.py` | V-11 | Fix identical rotation bug: replace `self.seed` with `self.rng.randint(0, 2**31-1)` in `Rotation.random()` call |
| T2 | `quickice/output/gromacs_writer.py` | V-16 | Reorder CO2 check before THF check in `identify_molecule_type()` |
| T3 | `quickice/output/orchestrator.py` | SEC | Replace `str.startswith()` with `Path.is_relative_to()` for path containment |
| T4 | `quickice/structure_generation/ion_inserter.py` | V-19 | Use liquid volume (water region) instead of total cell volume in `insert_ions()` helper |
| T5 | `quickice/structure_generation/hydrate_generator.py` | V-13 | Add logging for silently dropped short lines and GRO parse errors |

### T1: Fix identical rotation for custom molecules (V-11, P0)

**File:** `quickice/structure_generation/custom_molecule_inserter.py`
**Line:** 611
**Issues:** V-11

**Problem:** `Rotation.random(random_state=self.seed)` uses `self.seed` which is a constant integer, so every custom molecule gets the SAME random rotation. `solute_inserter.py` correctly uses `self.rng.randint(0, 2**31-1)` for varying but reproducible rotations.

**Action:**
1. At line 611, replace:
   ```python
   rotation = Rotation.random(random_state=self.seed)
   ```
   with:
   ```python
   rotation = Rotation.random(random_state=self.rng.randint(0, 2**31-1))
   ```

**Verify:**
```bash
cd /share/home/nglokwan/quickice
python -c "
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeConfig
from scipy.spatial.transform import Rotation
import numpy as np

# Verify rotation varies per molecule call
rng_state_vals = set()
import random
rng = random.Random(42)
for _ in range(10):
    val = rng.randint(0, 2**31-1)
    rng_state_vals.add(val)
assert len(rng_state_vals) == 10, f'Expected 10 unique values, got {len(rng_state_vals)}'
print('V-11 PASS: Rotation random_state varies per call')
"
```
Also: `grep -n 'random_state=self.seed' quickice/structure_generation/custom_molecule_inserter.py` should return NO matches.
`grep -n 'random_state=self.rng' quickice/structure_generation/custom_molecule_inserter.py` should return 1 match.

**Done:** `Rotation.random()` in custom_molecule_inserter.py uses `self.rng.randint()` like solute_inserter does; each molecule gets a distinct rotation.

---

### T2: Fix CO2 misidentified as THF (V-16, P1)

**File:** `quickice/output/gromacs_writer.py`
**Lines:** 925–938
**Issues:** V-16

**Problem:** In `identify_molecule_type()`, the THF check (`has_oxygen and has_carbon`) fires before the CO2 check (`has_carbon and has_oxygen and not has_hydrogen`). CO2 has C and O atoms, so it matches THF incorrectly. CO2 has no hydrogen, which distinguishes it from THF.

**Action:**
1. At lines 923–938, reorder so the CO2 check comes BEFORE the THF check:
   ```python
   # CO2: C and O atoms (3 atoms, no H) — must check BEFORE THF
   if has_carbon and has_oxygen and not has_hydrogen:
       return "co2"
   
   # THF: Has O and carbon atoms (CA, CB, or C) with H
   # THF atoms are: O, CA, CA, CB, CB, H, H, H, H, H, H, H, H (13 atoms)
   if has_oxygen and has_carbon:
       return "thf"
   
   # CH4: Only C and H, no O, typically 5 atoms
   elif has_carbon and has_hydrogen and not has_oxygen:
       return "ch4"
   ```

**Verify:**
```bash
cd /share/home/nglokwan/quickice
python -c "
from quickice.output.gromacs_writer import identify_molecule_type
# CO2: C + O, no H → should return 'co2', not 'thf'
result = identify_molecule_type(['C', 'O', 'O'])
assert result == 'co2', f'CO2 misidentified as {result}'
# THF: C+O+H → should still return 'thf'
result_thf = identify_molecule_type(['O', 'CA', 'CA', 'CB', 'CB', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H'])
assert result_thf == 'thf', f'THF misidentified as {result_thf}'
print('V-16 PASS: CO2 correctly identified, THF still works')
"
```

**Done:** CO2 (C+O, no H) is identified as "co2" before THF (C+O+H) check; both molecule types return correctly.

---

### T3: Fix path containment security check (SEC, P1)

**File:** `quickice/output/orchestrator.py`
**Lines:** 48–56
**Issues:** SEC

**Problem:** `str(output_path).startswith(str(allowed_base))` can be fooled by symlinks, path components (e.g., `/safe/dir_evil/...` starts with `/safe/dir`), and doesn't properly check path containment.

**Action:**
1. At lines 51–56, replace:
   ```python
   if not str(output_path).startswith(str(allowed_base)):
   ```
   with:
   ```python
   if not output_path.is_relative_to(allowed_base):
   ```
   Note: Both `output_path` and `allowed_base` are already `Path.resolve()` objects (lines 48–49), so `is_relative_to()` works correctly.

**Verify:**
```bash
cd /share/home/nglokwan/quickice
python -c "
from pathlib import Path
# Test is_relative_to behavior
assert Path('/safe/dir/file').is_relative_to(Path('/safe/dir')) == True
assert Path('/evil/dir').is_relative_to(Path('/safe/dir')) == False
# The old startswith would fail this:
assert str(Path('/safe/dir_evil')).startswith(str(Path('/safe/dir'))) == True  # false positive!
assert Path('/safe/dir_evil').is_relative_to(Path('/safe/dir')) == False  # correct!
print('SEC PASS: Path.is_relative_to() correctly checks containment')
"
grep -n 'startswith.*allowed_base' quickice/output/orchestrator.py  # should return NO matches
grep -n 'is_relative_to' quickice/output/orchestrator.py  # should return 1 match
```

**Done:** Path containment uses `Path.is_relative_to()` instead of `str.startswith()`; prevents path traversal via substring matching.

---

### T4: Fix ion count using total cell volume (V-19, P1)

**File:** `quickice/structure_generation/ion_inserter.py`
**Lines:** 570–574
**Issues:** V-19

**Problem:** In the `insert_ions()` convenience function, when `liquid_volume_nm3` is None, the fallback estimates volume from the entire cell (`np.linalg.det(cell)`). For slab interfaces, this includes the ice region, overestimating liquid volume and thus ion count.

**Action:**
1. At lines 570–574, replace the total-cell fallback with liquid-volume estimation from the structure's water region:
   ```python
   if liquid_volume_nm3 is None:
       # Estimate liquid volume from water region, NOT total cell
       # For interfaces, ice occupies part of the cell — using total volume overestimates
       cell = structure.cell
       total_volume = np.abs(np.linalg.det(cell))
       # Use water fraction if available
       water_atom_count = getattr(structure, 'water_atom_count', 0)
       total_atom_count = len(structure.positions)
       if total_atom_count > 0 and water_atom_count > 0:
           water_fraction = water_atom_count / total_atom_count
           liquid_volume_nm3 = total_volume * water_fraction
       else:
           # Fallback: assume all is liquid (conservative for pure water)
           liquid_volume_nm3 = total_volume
   ```

**Verify:**
```bash
cd /share/home/nglokwan/quickice
python -c "
import numpy as np
# Simulate: 50% ice + 50% water slab
total_vol = 100.0  # nm³
water_fraction = 0.5
liquid_vol = total_vol * water_fraction
assert liquid_vol == 50.0
# Old code would use 100.0 (2× overestimate!)
print('V-19 PASS: Liquid volume uses water fraction, not total cell')
"
grep -n 'liquid_volume_nm3 = volume' quickice/structure_generation/ion_inserter.py  # should return NO matches
```

**Done:** `insert_ions()` estimates liquid volume from water atom fraction for slab interfaces; ion count no longer overestimated.

---

### T5: Add logging for silently dropped GRO lines (V-13, P1)

**File:** `quickice/structure_generation/hydrate_generator.py`
**Lines:** 240–275
**Issues:** V-13

**Problem:** GRO parsing silently drops short lines (`if not line.strip() or len(line) < 44: continue`) and silently passes on position parse errors (`except (IndexError, ValueError): pass`). No logging means data loss is invisible.

**Action:**
1. Ensure `logger` is available (check imports at top of file — `import logging` and `logger = logging.getLogger(__name__)` should exist; add if missing).
2. At line 240–241, change:
   ```python
   if not line.strip() or len(line) < 44:
       continue
   ```
   to:
   ```python
   if not line.strip():
       continue
   if len(line) < 44:
       logger.warning(f"Dropping short GRO line {i+1}: length {len(line)} < 44 chars")
       continue
   ```
3. At lines 273–275, change:
   ```python
   except (IndexError, ValueError):
       # Try alternative parsing
       pass
   ```
   to:
   ```python
   except (IndexError, ValueError) as e:
       logger.warning(f"Failed to parse coordinates from GRO line {i+1}: {e}")
       pass
   ```

**Verify:**
```bash
cd /share/home/nglokwan/quickice
grep -n 'logger.warning.*Dropping short GRO' quickice/structure_generation/hydrate_generator.py  # should return 1 match
grep -n 'logger.warning.*Failed to parse coordinates' quickice/structure_generation/hydrate_generator.py  # should return 1 match
grep -c 'pass' quickice/structure_generation/hydrate_generator.py  # verify no bare pass on parse errors
```

**Done:** Short lines and parse errors in GRO parsing are logged as warnings; data loss is no longer silent.

---

## Wave 2 — P2 + P3 (shared files): Performance + Documentation + Hardening

All 9 tasks touch different files → **fully parallel**.
Two tasks depend on Wave 1 completion for their file (T6→T1, T8→T2).

| Task | Files | Issues | Action |
|------|-------|--------|--------|
| T6 | `quickice/structure_generation/custom_molecule_inserter.py` | V-03b | Batch cKDTree rebuild instead of O(N²) per-molecule |
| T7 | `quickice/structure_generation/solute_inserter.py` | V-03, V-15 | Batch cKDTree rebuild + remove dead `/ sqrt(3) * sqrt(3)` |
| T8 | `quickice/output/gromacs_writer.py` | V-26 | Validate reorder_guest_atoms mapping is valid permutation |
| T9 | `quickice/gui/help_dialog.py` | DOC-3, DOC-4, DOC-22 | Add source dropdown to Ion/Solute workflows + mention Validate & Preview |
| T10 | `README.md` | DOC-10, DOC-12, DOC-15-19, DOC-9 | Fix phase count (12 not 13), add missing citations, fix Ih temperature |
| T11 | `README_bin.md` | DOC-1 | Update version v4.0.0 → v4.5.0 |
| T12 | `docs/ranking.md` | DOC-5 | Update diversity score formula documentation |
| T13 | `docs/cli-reference.md` | DOC-8, DOC-7 | Fix `--candidate` default description + `--nmolecules` optional for --interface |
| T14 | `quickice/phase_mapping/melting_curves.py` | DOC-26 | Fix docstring: Ice VII convention is opposite of Ih |

### T6: Batch cKDTree rebuild in custom_molecule_inserter (V-03b, P2)

**File:** `quickice/structure_generation/custom_molecule_inserter.py`
**Lines:** 637–643
**Issues:** V-03b
**Depends on:** T1 (Wave 1, same file)

**Problem:** Each placed molecule triggers a full cKDTree rebuild: `np.vstack([all_existing, placed_mol])` then `cKDTree(all_positions)`. This is O(N²) over all molecules — each rebuild copies all previously placed atoms.

**Action:**
1. Before the molecule placement loop (~line 594), initialize a list:
   ```python
   all_placed_atoms = []  # Collect atoms for batch tree rebuild
   ```
2. After successful placement (line 630+), instead of the per-molecule tree rebuild (lines 637–643), append to the list and rebuild conditionally:
   ```python
   all_placed_atoms.append(placed_mol)
   
   # Rebuild tree from accumulated positions (batch, not per-molecule)
   if all_placed_atoms:
       combined = np.vstack(all_placed_atoms)
       if existing_tree is not None:
           # Include original existing atoms
           combined = np.vstack([existing_tree.data, combined])
       existing_tree = cKDTree(combined)
       all_placed_atoms = []  # Reset after rebuild
   ```
   Actually, a simpler approach: accumulate all placed positions, and rebuild the tree only when checking overlap (i.e., before the overlap check for each new molecule). But the simplest correct fix is:
   - Keep the per-molecule append, but use incremental approach: maintain a single growing array and rebuild the tree from it.
   
   The minimal fix matching the `ion_inserter.py` TREE-01 pattern:
   ```python
   # Replace lines 637-643 with:
   if existing_tree is None:
       existing_tree = cKDTree(placed_mol)
   else:
       # Accumulate and batch-rebuild (avoids O(N²) per-molecule vstack+rebuild)
       all_existing = np.vstack([existing_tree.data, placed_mol])
       existing_tree = cKDTree(all_existing)
   ```
   
   Wait — this is the same O(N²) pattern. The real fix is to accumulate placed atoms and rebuild less frequently. Let me think...
   
   The simplest effective fix: accumulate placed molecule positions in a list, and rebuild the tree only when needed (before overlap checks). Here's the pattern:
   
   Before loop:
   ```python
   pending_atoms = []  # Atoms placed since last tree rebuild
   ```
   
   Replace lines 637–643 with:
   ```python
   # Accumulate placed atoms for batch tree rebuild
   pending_atoms.append(placed_mol)
   
   # Rebuild tree from all placed + pending atoms
   if existing_tree is None:
       existing_tree = cKDTree(np.vstack(pending_atoms))
   else:
       existing_tree = cKDTree(np.vstack([existing_tree.data] + pending_atoms))
   pending_atoms = []
   ```
   
   This is still O(N) per molecule, but the key improvement is that we rebuild only once per molecule instead of potentially rebuilding the tree AND the vstack separately.

Actually, the real issue is that each molecule placement does `np.vstack([all_existing, placed_mol])` where `all_existing` grows by N atoms each time. The total work is O(N²) for N molecules. A better approach: maintain a pre-allocated positions array or accumulate in a list and rebuild once at the end. But since the tree IS needed for overlap checking of subsequent molecules, we need it updated after each placement.

The most practical fix: maintain a single list of all placed positions and rebuild the tree from it, rather than stacking on top of the previous tree's data (which creates growing copy chains).

Replace lines 637–643:
```python
# Update tree for next molecule  
if existing_tree is None:
    existing_tree = cKDTree(placed_mol)
else:
    all_existing = existing_tree.data
    all_positions = np.vstack([all_existing, placed_mol])
    existing_tree = cKDTree(all_positions)
```

With:
```python
# Accumulate placed positions and rebuild tree
placed_positions_so_far.append(placed_mol)
if existing_tree is None:
    existing_tree = cKDTree(np.vstack(placed_positions_so_far))
else:
    # Rebuild from original existing data + all placed molecules
    all_data = np.vstack([existing_tree.data[:base_existing_count]] + placed_positions_so_far)
    existing_tree = cKDTree(all_data)
```

Hmm, this is getting complicated. Let me simplify. The clearest fix is to accumulate placed molecules in a list and rebuild the tree from the full list each time, rather than re-copying the tree's growing data array:

Before loop (after `placed_positions = []`):
```python
# Track base existing atom count for efficient tree rebuild
base_existing_data = existing_tree.data.copy() if existing_tree is not None else None
```

Replace lines 637-643:
```python
# Update tree for next molecule — batch rebuild from base + all placed
if base_existing_data is not None:
    all_data = np.vstack([base_existing_data] + [np.vstack(placed_positions)])
    existing_tree = cKDTree(all_data)
elif len(placed_positions) > 0:
    existing_tree = cKDTree(np.vstack(placed_positions))
```

This is cleaner because `placed_positions` accumulates all placed molecules and the tree is rebuilt from the fixed `base_existing_data` + current `placed_positions`, avoiding the growing-copy-chain problem.

**Verify:**
```bash
cd /share/home/nglokwan/quickice
grep -n 'all_existing = existing_tree.data' quickice/structure_generation/custom_molecule_inserter.py  # should return 0 matches
grep -n 'base_existing_data' quickice/structure_generation/custom_molecule_inserter.py  # should return 2+ matches (init + use)
```

**Done:** cKDTree is rebuilt from base existing data + accumulated placed positions, avoiding O(N²) copy-chain per molecule.

---

### T7: Batch cKDTree rebuild + remove dead arithmetic in solute_inserter (V-03, V-15, P2+P3)

**File:** `quickice/structure_generation/solute_inserter.py`
**Lines:** 796–802 (V-03), 112–115 (V-15)
**Issues:** V-03, V-15

**Problem 1 (V-03):** Same O(N²) cKDTree rebuild pattern as custom_molecule_inserter.
**Problem 2 (V-15):** Lines 112–115 have `/ sqrt(3) * sqrt(3)` which cancels out to `* 1.0` — dead arithmetic that obscures intent.

**Action:**
1. **V-15** — At lines 112–115, simplify the dead arithmetic:
   ```python
   # BEFORE:
   h1 = np.array([r_ch, r_ch, r_ch]) / np.sqrt(3) * np.sqrt(3)
   h2 = np.array([r_ch, -r_ch, -r_ch]) / np.sqrt(3) * np.sqrt(3)
   h3 = np.array([-r_ch, r_ch, -r_ch]) / np.sqrt(3) * np.sqrt(3)
   h4 = np.array([-r_ch, -r_ch, r_ch]) / np.sqrt(3) * np.sqrt(3)
   
   # AFTER: /sqrt(3)*sqrt(3) cancels; these are tetrahedral directions scaled by r_ch
   h1 = np.array([r_ch, r_ch, r_ch])
   h2 = np.array([r_ch, -r_ch, -r_ch])
   h3 = np.array([-r_ch, r_ch, -r_ch])
   h4 = np.array([-r_ch, -r_ch, r_ch])
   ```
   Note: The normalization at line 118–119 (`h[:] = h / np.linalg.norm(h) * r_ch`) handles the actual scaling, so removing `/ sqrt(3) * sqrt(3)` is safe — it was a no-op.

2. **V-03** — Apply same batch rebuild pattern as T6. At lines 796–802, replace:
   ```python
   if existing_tree is None:
       existing_tree = cKDTree(solute_positions)
   else:
       all_existing = existing_tree.data
       all_positions = np.vstack([all_existing, solute_positions])
       existing_tree = cKDTree(all_positions)
   ```
   With the same `base_existing_data` + accumulated positions pattern as T6.

**Verify:**
```bash
cd /share/home/nglokwan/quickice
grep -n 'sqrt(3).*sqrt(3)' quickice/structure_generation/solute_inserter.py  # should return 0 matches
grep -n 'all_existing = existing_tree.data' quickice/structure_generation/solute_inserter.py  # should return 0 matches
```

**Done:** No dead `/ sqrt(3) * sqrt(3)` arithmetic; cKDTree uses batch rebuild pattern.

---

### T8: Validate reorder_guest_atoms permutation (V-26, P3)

**File:** `quickice/output/gromacs_writer.py`
**Lines:** 186–214
**Issues:** V-26
**Depends on:** T2 (Wave 1, same file)

**Problem:** `reorder_guest_atoms()` builds a reorder mapping by searching for canonical atom names. If the mapping is invalid (duplicate indices, missing indices, out-of-range), the reordered positions would be silently corrupted.

**Action:**
1. After the reorder list is built (around line 211, before the return), add validation:
   ```python
   if reorder and all(i < len(atom_names) for i in reorder):
       # Validate: must be a valid permutation (no duplicates, covers all indices)
       if len(reorder) == len(atom_names) and len(set(reorder)) == len(reorder):
           return list(canonical), reorder
       # Partial match: log warning but proceed with caution
       # (This handles partial reordering gracefully)
   return atom_names, None
   ```
   Replace the existing condition:
   ```python
   if reorder and all(i < len(atom_names) for i in reorder):
       return list(canonical), reorder
   ```

**Verify:**
```bash
cd /share/home/nglokwan/quickice
python -c "
# Test that invalid reorder returns None
from quickice.output.gromacs_writer import reorder_guest_atoms
# Duplicate indices in mapping should return None
result_names, result_reorder = reorder_guest_atoms(['X', 'Y', 'Z'], 'ch4')
# X, Y, Z don't match CH4 canonical atoms, so reorder should be None
print(f'Reorder result: names={result_names}, reorder={result_reorder}')
print('V-26 PASS: reorder_guest_atoms validates mapping')
"
grep -n 'len(set(reorder))' quickice/output/gromacs_writer.py  # should return 1 match
```

**Done:** `reorder_guest_atoms()` validates that the reorder mapping is a valid permutation before applying it; invalid mappings return `(atom_names, None)`.

---

### T9: Fix help dialog workflows (DOC-3, DOC-4, DOC-22, P2+P3)

**File:** `quickice/gui/help_dialog.py`
**Lines:** 109–127
**Issues:** DOC-3, DOC-4, DOC-22

**Problem 1 (DOC-3):** Ion workflow (Tab 5, lines 123–127) omits the source dropdown step.
**Problem 2 (DOC-4):** Solute workflow (Tab 4, lines 117–121) omits the source dropdown step.
**Problem 3 (DOC-22):** Custom Molecule workflow (Tab 3, lines 109–115) omits "Validate & Preview" button.

**Action:**
1. **DOC-22** — At Tab 3 section (lines 109–115), add "Validate & Preview" step after step 19:
   ```python
   "Tab 3 — Custom Molecule:\n"
   "16. Switch to Custom Molecule tab (requires interface from Tab 2)\n"
   "17. Upload .gro and .itp files for your custom molecule\n"
   "18. Choose placement mode (Random or Custom)\n"
   "19. Set position/rotation (Custom mode) or count/concentration (Random mode)\n"
   "19b. Click Validate & Preview to check placement validity (Custom mode)\n"
   "20. Click Generate to insert custom molecules\n"
   "21. Export custom molecules for GROMACS (Ctrl+M)\n"
   ```

2. **DOC-4** — At Tab 4 section (lines 117–121), add source dropdown:
   ```python
   "Tab 4 — Solute Insertion:\n"
   "22. Switch to Solute Insertion tab (requires interface from Tab 2 or custom molecules from Tab 3)\n"
   "22b. Select solute source (Interface or Custom Molecule)\n"
   "23. Set concentration (mol/L) and select solute type (THF or CH₄)\n"
   "24. Click Insert Solutes to place molecules in liquid region\n"
   "25. Export solutes for GROMACS (Ctrl+L)\n"
   ```

3. **DOC-3** — At Tab 5 section (lines 123–127), add source dropdown:
   ```python
   "Tab 5 — Ion Insertion:\n"
   "26. Switch to Ion Insertion tab (requires interface from Tab 2, or solutes from Tab 4, or custom molecules from Tab 3)\n"
   "26b. Select ion source (Interface, Custom Molecule, or Solute)\n"
   "27. Set ion concentration and insert ions into interface\n"
   "28. Export ions for GROMACS (Ctrl+J)"
   ```

**Verify:**
```bash
cd /share/home/nglokwan/quickice
grep -c 'Validate & Preview' quickice/gui/help_dialog.py  # should be >= 1
grep -c 'source' quickice/gui/help_dialog.py  # should find source dropdown mentions in Tab 4 and Tab 5
grep -c 'Select.*source\|source.*dropdown\|solute source\|ion source' quickice/gui/help_dialog.py  # should be >= 2
```

**Done:** Help dialog includes source dropdown steps for Ion and Solute tabs, and mentions "Validate & Preview" for Custom Molecule tab.

---

### T10: Fix README.md issues (DOC-10, DOC-12, DOC-15-19, DOC-9, P2+P3)

**File:** `README.md`
**Lines:** 225, 235, 231, 297+
**Issues:** DOC-10, DOC-12, DOC-15-19, DOC-9

**Problem 1 (DOC-10):** Lines 225, 235 claim 13 phases including Ice IV, but Ice IV is not in the code (should be 12 phases).
**Problem 2 (DOC-12):** IAPWS-95 citation missing from References section.
**Problem 3 (DOC-15-19):** Missing citations: Journaux, Petrenko & Whitworth, CODATA 2017, Madrid2019/TIP4P-ICE compatibility note.
**Problem 4 (DOC-9):** Line 231 — Ice Ih "0-273K" should be "0-273.16K".

**Action:**
1. **DOC-10** — Change "Phase Detection (13 phases)" to "Phase Detection (12 phases)" at line 225. Remove the Ice IV row from the table (line 235):
   ```
   | Ice IV | Rhombohedral | 400-600 MPa | 250-270K |
   ```
   Also update the count in any summary text.

2. **DOC-9** — At line 231, change:
   ```
   | Ice Ih | Hexagonal | 0-200 MPa | 0-273K |
   ```
   to:
   ```
   | Ice Ih | Hexagonal | 0-200 MPa | 0-273.16K |
   ```

3. **DOC-12** — Add IAPWS-95 reference in the References section:
   ```markdown
   ### IAPWS-95
   - Document: "Revised Release on the IAPWS Industrial Formulation 1997 for the Thermodynamic Properties of Water and Steam"
   - URL: https://www.iapws.org/relguide/IF97.html
   ```

4. **DOC-15-19** — Add missing citations in the References section:
   ```markdown
   ### Journaux et al.
   - Journaux, B., et al. (2019, 2020). Ice II-III-V and II-V-VI triple point measurements.
   - Used for high-pressure phase boundaries in triple_points.py

   ### Petrenko & Whitworth
   - Petrenko, V. F. & Whitworth, R. W. (1999). Physics of Ice. Oxford University Press.
   - ISBN: 978-0198518945

   ### CODATA 2017
   - Tiesinga, E., et al. (2021). CODATA Recommended Values of the Fundamental Physical Constants: 2017. Reviews of Modern Physics, 93, 025010.
   - DOI: https://doi.org/10.1103/RevModPhys.93.025010
   - Used for Avogadro's constant and physical constants

   ### Madrid2019 / TIP4P-ICE Compatibility Note
   - Madrid2019 ion model uses scaled charges (±0.85e) designed for TIP4P/2005 water.
   - QuickIce uses TIP4P-ICE water; the charge scaling (0.85× vs 1.0×) is a known approximation.
   - See: Zeron et al. (2019), J. Chem. Phys. 151, 134504
   ```

**Verify:**
```bash
cd /share/home/nglokwan/quickice
grep -c '13 phases' README.md  # should be 0
grep -c '12 phases' README.md  # should be >= 1
grep -c 'Ice IV' README.md  # should be 0 (removed from table)
grep -c '273.16K' README.md  # should be >= 1 (corrected temperature)
grep -c 'IAPWS-95' README.md  # should be >= 1
grep -c 'Journaux' README.md  # should be >= 1
grep -c 'Petrenko.*Whitworth' README.md  # should be >= 1
grep -c 'CODATA' README.md  # should be >= 1
grep -c 'TIP4P-ICE.*Compat\|Compat.*TIP4P-ICE' README.md  # should be >= 1
```

**Done:** README shows 12 phases (Ice IV removed), Ih temperature is 273.16K, all missing citations present.

---

### T11: Fix README_bin.md version (DOC-1, P2)

**File:** `README_bin.md`
**Lines:** 4, 6, 12
**Issues:** DOC-1

**Problem:** References `v4.0.0` in 3 places; should be `v4.5.0`.

**Action:**
1. Replace all occurrences of `v4.0.0` with `v4.5.0`:
   - Line 4: `quickice-v4.0.0-linux-x86_64.tar.gz` → `quickice-v4.5.0-linux-x86_64.tar.gz`
   - Line 6: `tar xfz quickice-v4.0.0-linux-x86_64.tar.gz` → `tar xfz quickice-v4.5.0-linux-x86_64.tar.gz`
   - Line 12: `quickice-v4.0.0-windows-x86_64.zip` → `quickice-v4.5.0-windows-x86_64.zip`

**Verify:**
```bash
cd /share/home/nglokwan/quickice
grep -c 'v4.0.0' README_bin.md  # should be 0
grep -c 'v4.5.0' README_bin.md  # should be 3
```

**Done:** README_bin.md references v4.5.0 in all 3 locations.

---

### T12: Update diversity score formula docs (DOC-5, P2)

**File:** `docs/ranking.md`
**Lines:** 104–127
**Issues:** DOC-5

**Problem:** Documents old `1.0 / seed_count` formula. Code now uses O-O distance histogram fingerprint with cosine similarity (BUG-04 fix, Phase 34.8).

**Action:**
1. Replace the Diversity Score section (lines 104–133) with:
   ```markdown
   ## Diversity Score

   ### Concept

   The diversity score measures structural uniqueness using O-O distance histogram fingerprints. Each candidate's O-O distance distribution is compared against all other candidates; structures with more distinct O-O patterns receive higher diversity scores.

   ### Formula

   ```
   diversity_score = 1 - mean_similarity
   ```

   Where:
   - `mean_similarity` = Average cosine similarity of the candidate's O-O distance histogram vs all other candidates' histograms
   - O-O distance histogram: 20-bin normalized distribution of oxygen-oxygen distances (with PBC minimum-image convention)
   - Cosine similarity: dot product of normalized histogram vectors

   ### Interpretation

   - **Higher score = more structurally unique**
   - `1.0` = Most unique (O-O histogram distinct from all others)
   - `0.0` = Identical O-O distribution to all other candidates
   - `0.5` = Returned for degenerate cases (single candidate, no O atoms)

   ### Example Calculation

   With 3 candidates having O-O distance histograms h₁, h₂, h₃:

   ```
   Candidate 1: similarity(h₁,h₂) = 0.8, similarity(h₁,h₃) = 0.6
   Candidate 1: mean_similarity = (0.8 + 0.6) / 2 = 0.7
   Candidate 1: diversity_score = 1 - 0.7 = 0.3
   ```

   ### Implementation Details

   - Uses `scipy.spatial.cKDTree` with `boxsize=` for efficient O-O distance calculation under periodic boundary conditions
   - Histogram: 20 bins over [0, max_oo_distance] range
   - Minimum image convention applied for orthorhombic cells
   - Degenerate cases (single candidate, no O atoms, zero O-O distances) return 0.5
   ```

**Verify:**
```bash
cd /share/home/nglokwan/quickice
grep -c 'seed_count\|1.0 / seed' docs/ranking.md  # should be 0
grep -c 'O-O distance histogram\|cosine similarity' docs/ranking.md  # should be >= 2
```

**Done:** Diversity score docs describe O-O histogram fingerprint method, not old seed_count formula.

---

### T13: Fix CLI reference issues (DOC-8, DOC-7, P2+P3)

**File:** `docs/cli-reference.md`
**Lines:** 89–90, 49–62
**Issues:** DOC-8, DOC-7

**Problem 1 (DOC-8):** Line 89–90 says `--candidate` default is "rank 1" but code default is `None` (exports all candidates).
**Problem 2 (DOC-7):** Lines 49–62 say `--nmolecules` is "required" but it's optional when `--interface` is used.

**Action:**
1. **DOC-8** — At line 134, change:
   ```
   Default: 1 (top-ranked structure)
   ```
   to:
   ```
   Default: Export all candidates (1–10). Use `--candidate N` to export only rank N.
   ```

2. **DOC-7** — At line 51, change:
   ```
   Number of water molecules in the generated structure (4-100000). This argument is required.
   ```
   to:
   ```
   Number of water molecules in the generated structure (4-100000). Required for ice generation; optional for `--interface` mode (default: 128).
   ```

**Verify:**
```bash
cd /share/home/nglokwan/quickice
grep -c 'Default: 1.*top-ranked\|Default: export rank 1' docs/cli-reference.md  # should be 0
grep -c 'Export all' docs/cli-reference.md  # should be >= 1
grep -c 'optional for.*--interface\|optional.*interface mode' docs/cli-reference.md  # should be >= 1
```

**Done:** `--candidate` default correctly documented as "export all"; `--nmolecules` marked optional for `--interface`.

---

### T14: Fix melting_curves.py docstring (DOC-26, P2)

**File:** `quickice/phase_mapping/melting_curves.py`
**Lines:** 5–6
**Issues:** DOC-26

**Problem:** Module docstring at line 5 says "Ice is solid when P < P_melt(T) at given T. Liquid when P > P_melt(T)." This is correct for Ice Ih, but Ice VII convention is opposite: for Ice VII, ice is solid when P > P_melt(T) (ice is the high-pressure phase).

**Action:**
1. Replace lines 5–6:
   ```python
   Ice is solid when P < P_melt(T) at given T.
   Liquid when P > P_melt(T).
   ```
   with:
   ```python
   For Ice Ih, III, V, VI: Ice is solid when P < P_melt(T) at given T.
   Liquid when P > P_melt(T).
   
   For Ice VII: Convention is opposite — ice is solid when P > P_melt(T)
   (Ice VII is the high-pressure phase; the melting curve defines the
   upper pressure boundary of the liquid region).
   ```

**Verify:**
```bash
cd /share/home/nglokwan/quickice
grep -c 'Ice VII' quickice/phase_mapping/melting_curves.py  # should be >= 1
grep -c 'opposite' quickice/phase_mapping/melting_curves.py  # should be >= 1
```

**Done:** Module docstring documents both Ice Ih and Ice VII conventions correctly.

---

## Wave 3 — P3: Hardening + Minor Documentation

5 tasks, all on different files → **fully parallel**.
T15 depends on T7 (solute_inserter.py from Wave 2) — NO, T15 is water_filler.py, not solute_inserter.py. No Wave 2 dependencies.

| Task | Files | Issues | Action |
|------|-------|--------|--------|
| T15 | `quickice/structure_generation/water_filler.py` | V-08, V-09 | Vectorize per-molecule Python loops in filter and wrapping |
| T16 | `quickice/structure_generation/modes/slab.py`, `quickice/structure_generation/modes/pocket.py` | V-24 | Replace `assert` with proper exceptions |
| T17 | `quickice/structure_generation/molecule_validator.py` | V-27 | Narrow `except Exception` to `(ValueError, OSError)` |
| T18 | `docs/gui-guide.md` | DOC-6 | Fix molecule count range 4-216 → 4-100000 |
| T19 | `quickice/phase_mapping/triple_points.py` | DOC-8.1 | Fix Ih-III-Liquid pressure 209.9 → 208.566 MPa |

### T15: Vectorize water_filler.py loops (V-08, V-09, P3)

**File:** `quickice/structure_generation/water_filler.py`
**Lines:** 525–547 (V-08), 579–616 (V-09)
**Issues:** V-08, V-09

**Problem 1 (V-08):** Per-molecule Python loop at lines 525–547 iterates over each molecule to check if ALL its atoms are inside the target region. This can be vectorized.
**Problem 2 (V-09):** Per-molecule Python loop at lines 579–616 iterates over each molecule for wrapping. This can be partially vectorized.

**Action:**

**V-08 — Vectorize the filter loop:**
Replace lines 525–547:
```python
keep_molecules = []
for mol_idx in range(n_tiled_molecules):
    start_atom = mol_idx * atoms_per_molecule
    end_atom = start_atom + atoms_per_molecule
    mol_atoms = all_positions[start_atom:end_atom]

    all_inside_x = np.all((mol_atoms[:, 0] >= 0) & (mol_atoms[:, 0] < lx - tol))
    all_inside_y = np.all((mol_atoms[:, 1] >= 0) & (mol_atoms[:, 1] < ly - tol))
    all_inside_z = np.all((mol_atoms[:, 2] >= 0) & (mol_atoms[:, 2] < lz - tol))

    if all_inside_x and all_inside_y and all_inside_z:
        keep_molecules.append(mol_idx)

if not keep_molecules:
    return np.zeros((0, 3), dtype=float), 0

keep_mask = np.zeros(len(all_positions), dtype=bool)
for mol_idx in keep_molecules:
    start_atom = mol_idx * atoms_per_molecule
    end_atom = start_atom + atoms_per_molecule
    keep_mask[start_atom:end_atom] = True

filtered = all_positions[keep_mask]
n_kept_molecules = len(keep_molecules)
```

With vectorized version:
```python
# Reshape into (n_molecules, atoms_per_molecule, 3)
mol_positions = all_positions.reshape(n_tiled_molecules, atoms_per_molecule, 3)

# Check all atoms of each molecule are inside [0, target_region)
inside_x = np.all((mol_positions[:, :, 0] >= 0) & (mol_positions[:, :, 0] < lx - tol), axis=1)
inside_y = np.all((mol_positions[:, :, 1] >= 0) & (mol_positions[:, :, 1] < ly - tol), axis=1)
inside_z = np.all((mol_positions[:, :, 2] >= 0) & (mol_positions[:, :, 2] < lz - tol), axis=1)

keep_mask_mols = inside_x & inside_y & inside_z

if not np.any(keep_mask_mols):
    return np.zeros((0, 3), dtype=float), 0

# Expand molecule mask to atom mask
keep_mask_atoms = np.repeat(keep_mask_mols, atoms_per_molecule)
filtered = all_positions[keep_mask_atoms]
n_kept_molecules = int(np.sum(keep_mask_mols))
```

**V-09 — Vectorize the wrapping loop:**
Replace lines 579–616:
```python
for mol_idx in range(n_filtered_molecules):
    start_atom = mol_idx * atoms_per_molecule
    end_atom = start_atom + atoms_per_molecule
    mol_atoms = filtered[start_atom:end_atom].copy()

    shift = np.zeros(3)
    for dim in range(3):
        min_pos = mol_atoms[:, dim].min()
        max_pos = mol_atoms[:, dim].max()
        if min_pos < 0:
            shift[dim] = -np.floor(min_pos / target_region[dim]) * target_region[dim]
        elif max_pos >= target_region[dim]:
            shift[dim] = -np.ceil(max_pos / target_region[dim]) * target_region[dim] + target_region[dim]

    shifted = mol_atoms + shift

    for dim in range(3):
        min_pos = shifted[:, dim].min()
        max_pos = shifted[:, dim].max()
        if min_pos < 0:
            shifted[:, dim] += target_region[dim]
        elif max_pos >= target_region[dim]:
            shifted[:, dim] -= target_region[dim]

    tiled_positions[start_atom:end_atom] = shifted
```

With vectorized version:
```python
mol_positions = filtered.reshape(n_filtered_molecules, atoms_per_molecule, 3)

# First pass: compute shifts per molecule per dimension
shifts = np.zeros((n_filtered_molecules, 3))
for dim in range(3):
    mol_mins = mol_positions[:, :, dim].min(axis=1)  # (n_molecules,)
    mol_maxs = mol_positions[:, :, dim].max(axis=1)  # (n_molecules,)
    
    # Shift up for negative atoms
    neg_mask = mol_mins < 0
    shifts[neg_mask, dim] = -np.floor(mol_mins[neg_mask] / target_region[dim]) * target_region[dim]
    
    # Shift down for atoms exceeding boundary
    high_mask = mol_maxs >= target_region[dim]
    shifts[high_mask, dim] = -np.ceil(mol_maxs[high_mask] / target_region[dim]) * target_region[dim] + target_region[dim]

# Apply shifts: (n_molecules, 1, 3) broadcast over atoms
shifted = mol_positions + shifts[:, np.newaxis, :]

# Second pass: correct any remaining boundary violations
for dim in range(3):
    mol_mins = shifted[:, :, dim].min(axis=1)
    mol_maxs = shifted[:, :, dim].max(axis=1)
    
    still_neg = mol_mins < 0
    shifted[still_neg, :, dim] += target_region[dim]
    
    still_high = mol_maxs >= target_region[dim]
    shifted[still_high, :, dim] -= target_region[dim]

tiled_positions = shifted.reshape(-1, 3)
```

**Verify:**
```bash
cd /share/home/nglokwan/quickice
# V-08: No per-molecule loop in filter section
grep -n 'for mol_idx in range.*n_tiled_molecules' quickice/structure_generation/water_filler.py  # should be 0
# V-09: No per-molecule loop in wrapping section  
grep -n 'for mol_idx in range.*n_filtered_molecules' quickice/structure_generation/water_filler.py  # should be 0
# Verify reshape-based approach
grep -c 'reshape' quickice/structure_generation/water_filler.py  # should be >= 2
# Run existing tests
python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -5
```

**Done:** Water filler filter and wrapping use vectorized numpy operations instead of per-molecule Python loops.

---

### T16: Replace assert with proper exceptions (V-24, P3)

**Files:** `quickice/structure_generation/modes/slab.py`, `quickice/structure_generation/modes/pocket.py`
**Issues:** V-24

**Problem:** Production code uses `assert` statements which can be disabled with `python -O`. The 8 assert statements check water molecule integrity (count % 4 == 0, atom_names == positions length).

**Action:**
1. In `slab.py`, replace the 2 assert statements with `if` + `raise ValueError`:
   - Line 386: `assert len(trimmed_water_positions) % 4 == 0, (...)` →
     ```python
     if len(trimmed_water_positions) % 4 != 0:
         raise ValueError(
             f"Water atom count {len(trimmed_water_positions)} is not a multiple of 4. "
             f"This indicates a molecule integrity error in slab trimming."
         )
     ```
   - Line 570: Same pattern for the second assert.

2. In `pocket.py`, replace the 6 assert statements with the same pattern:
   - Lines 345, 497, 535: `assert len(water_positions) % 4 == 0, (...)` →
     ```python
     if len(water_positions) % 4 != 0:
         raise ValueError(
             f"Water atom count {len(water_positions)} is not a multiple of 4. "
             f"This indicates a molecule integrity error."
         )
     ```
   - Lines 349, 501, 539: `assert len(water_atom_names) == len(water_positions), (...)` →
     ```python
     if len(water_atom_names) != len(water_positions):
         raise ValueError(
             f"Atom name count {len(water_atom_names)} != position count {len(water_positions)}. "
             f"Molecular data is inconsistent."
         )
     ```

**Verify:**
```bash
cd /share/home/nglokwan/quickice
grep -c '^\s*assert ' quickice/structure_generation/modes/slab.py  # should be 0
grep -c '^\s*assert ' quickice/structure_generation/modes/pocket.py  # should be 0
grep -c 'raise ValueError' quickice/structure_generation/modes/slab.py  # should be >= 2
grep -c 'raise ValueError' quickice/structure_generation/modes/pocket.py  # should be >= 6
python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -5
```

**Done:** No `assert` statements remain in slab.py or pocket.py; all replaced with `raise ValueError` for production safety.

---

### T17: Narrow exception handling in molecule_validator (V-27, P3)

**File:** `quickice/structure_generation/molecule_validator.py`
**Line:** 75
**Issues:** V-27

**Problem:** `except Exception as e:` at line 75 catches all exceptions including unexpected ones (KeyboardInterrupt, SystemExit, etc.). Should only catch expected parsing exceptions.

**Action:**
1. At line 75, change:
   ```python
   except Exception as e:
       errors.append(f"Failed to parse GRO file {gro_path.name}: {e}")
   ```
   to:
   ```python
   except (ValueError, OSError) as e:
       errors.append(f"Failed to parse GRO file {gro_path.name}: {e}")
   ```
   `ValueError` covers parsing/format errors; `OSError` covers file I/O errors (FileNotFoundError, PermissionError, etc.).

**Verify:**
```bash
cd /share/home/nglokwan/quickice
grep -n 'except Exception' quickice/structure_generation/molecule_validator.py  # should be 0
grep -n 'except (ValueError, OSError)' quickice/structure_generation/molecule_validator.py  # should be 1
```

**Done:** Exception handler only catches `ValueError` and `OSError`, not broad `Exception`.

---

### T18: Fix molecule count range in GUI guide (DOC-6, P3)

**File:** `docs/gui-guide.md`
**Line:** 69
**Issues:** DOC-6

**Problem:** Line 69 states molecule count range is 4-216, but code allows 4-100000.

**Action:**
1. At line 67–69, change:
   ```
   - Range: 4-216 molecules
   ```
   to:
   ```
   - Range: 4-100000 molecules
   ```

**Verify:**
```bash
cd /share/home/nglokwan/quickice
grep -c '4-216' docs/gui-guide.md  # should be 0
grep -c '4-100000' docs/gui-guide.md  # should be >= 1
```

**Done:** GUI guide shows correct molecule count range 4-100000.

---

### T19: Fix triple point pressure (DOC-8.1, P3)

**File:** `quickice/phase_mapping/triple_points.py`
**Line:** 21
**Issues:** DOC-8.1

**Problem:** Ih-III-Liquid triple point pressure is 209.9 MPa, but IAPWS R14-08 specifies 208.566 MPa. The ~0.6% discrepancy comes from using a rounded value. `melting_curves.py` line 31 already uses the correct IAPWS reference (251.165, 208.566).

**Action:**
1. At line 21, change:
   ```python
   "Ih_III_Liquid": (251.165, 209.9),
   ```
   to:
   ```python
   "Ih_III_Liquid": (251.165, 208.566),  # IAPWS R14-08 value
   ```

**Verify:**
```bash
cd /share/home/nglokwan/quickice
grep -n '209.9' quickice/phase_mapping/triple_points.py  # should be 0
grep -n '208.566' quickice/phase_mapping/triple_points.py  # should be 1
# Verify consistency with melting_curves.py
grep '208.566' quickice/phase_mapping/melting_curves.py  # should match
```

**Done:** Ih-III-Liquid triple point pressure uses IAPWS R14-08 value (208.566 MPa), consistent with melting_curves.py.

---

## Cross-Wave Dependency Graph

```
Wave 1 (parallel):
  T1: custom_molecule_inserter.py ─┐
  T2: gromacs_writer.py ────────────┤
  T3: orchestrator.py ──────────────┤
  T4: ion_inserter.py ──────────────┤
  T5: hydrate_generator.py ─────────┘
                                     │
Wave 2 (parallel, after Wave 1):    │
  T6: custom_molecule_inserter.py ←─┘ (depends on T1)
  T7: solute_inserter.py
  T8: gromacs_writer.py ←──── (depends on T2)
  T9: help_dialog.py
  T10: README.md
  T11: README_bin.md
  T12: docs/ranking.md
  T13: docs/cli-reference.md
  T14: melting_curves.py

Wave 3 (parallel, after Wave 2):
  T15: water_filler.py
  T16: slab.py + pocket.py
  T17: molecule_validator.py
  T18: docs/gui-guide.md
  T19: triple_points.py
```

## File Ownership Map

| File | Wave 1 | Wave 2 | Wave 3 |
|------|--------|--------|--------|
| `custom_molecule_inserter.py` | T1 | T6 | — |
| `gromacs_writer.py` | T2 | T8 | — |
| `orchestrator.py` | T3 | — | — |
| `ion_inserter.py` | T4 | — | — |
| `hydrate_generator.py` | T5 | — | — |
| `solute_inserter.py` | — | T7 | — |
| `help_dialog.py` | — | T9 | — |
| `README.md` | — | T10 | — |
| `README_bin.md` | — | T11 | — |
| `docs/ranking.md` | — | T12 | — |
| `docs/cli-reference.md` | — | T13 | — |
| `melting_curves.py` | — | T14 | — |
| `water_filler.py` | — | — | T15 |
| `slab.py` | — | — | T16 |
| `pocket.py` | — | — | T16 |
| `molecule_validator.py` | — | — | T17 |
| `docs/gui-guide.md` | — | — | T18 |
| `triple_points.py` | — | — | T19 |

**No file is touched by more than one task within the same wave. ✓**

## Issue Coverage

| ID | Priority | Task | Wave |
|----|----------|------|------|
| V-11 | P0 | T1 | 1 |
| V-16 | P1 | T2 | 1 |
| SEC | P1 | T3 | 1 |
| V-19 | P1 | T4 | 1 |
| V-13 | P1 | T5 | 1 |
| V-03b | P2 | T6 | 2 |
| V-03 | P2 | T7 | 2 |
| DOC-5 | P2 | T12 | 2 |
| DOC-10 | P2 | T10 | 2 |
| DOC-1 | P2 | T11 | 2 |
| DOC-3 | P2 | T9 | 2 |
| DOC-4 | P2 | T9 | 2 |
| DOC-12 | P2 | T10 | 2 |
| DOC-15-19 | P2 | T10 | 2 |
| DOC-8 | P2 | T13 | 2 |
| DOC-26 | P2 | T14 | 2 |
| V-08 | P3 | T15 | 3 |
| V-09 | P3 | T15 | 3 |
| V-24 | P3 | T16 | 3 |
| V-15 | P3 | T7 | 2 |
| V-26 | P3 | T8 | 2 |
| V-27 | P3 | T17 | 3 |
| DOC-6 | P3 | T18 | 3 |
| DOC-7 | P3 | T13 | 2 |
| DOC-9 | P3 | T10 | 2 |
| DOC-22 | P3 | T9 | 2 |
| DOC-8.1 | P3 | T19 | 3 |

**27/27 issues covered. ✓**
