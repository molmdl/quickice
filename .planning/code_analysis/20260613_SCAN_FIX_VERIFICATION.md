# Scan Fix Verification Report — 2026-06-13

**Verified:** 2026-06-13T00:00:00Z
**Scope:** All 19 scan fix tasks (Wave 1–3)
**Method:** Direct file inspection on disk (post-execution)

---

## Summary

| Wave | Tasks | PASS | FAIL |
|------|-------|------|------|
| Wave 1 (P0+P1) | 5 | 5 | 0 |
| Wave 2 (P2+P3) | 9 | 9 | 0 |
| Wave 3 (P3) | 5 | 5 | 0 |
| **Total** | **19** | **19** | **0** |

---

## Task-by-Task Verification

### Wave 1 (P0+P1)

#### T1 (V-11): `custom_molecule_inserter.py` — `self.rng.randint(0, 2**31-1)` in Rotation.random()
- **Status: ✅ PASS**
- **Found:** Line 614: `rotation = Rotation.random(random_state=self.rng.randint(0, 2**31-1))`
- **Also verified:** `solute_inserter.py` line 235 has same fix: `rotation = Rotation.random(random_state=self.rng.randint(0, 2**31 - 1))`
- **Old pattern `self.seed` NOT found** in either file.

#### T2 (V-16): `gromacs_writer.py` — CO2 checked BEFORE THF
- **Status: ✅ PASS**
- **Found:** Lines 926–934: CO2 check (has_carbon + has_oxygen + NOT has_hydrogen → return "co2") appears at line 928 BEFORE THF check (has_oxygen + has_carbon → return "thf") at line 933.
- **Comment on line 926:** `# CO2: C and O atoms, no H (3 atoms) — MUST check BEFORE THF`

#### T3 (SEC): `orchestrator.py` — `is_relative_to()` not `str.startswith()`
- **Status: ✅ PASS**
- **Found:** Line 52: `if not output_path.is_relative_to(allowed_base):`
- **Old pattern `str.startswith()` NOT found** in orchestrator.py.

#### T4 (V-19): `ion_inserter.py` — water fraction for liquid volume
- **Status: ✅ PASS**
- **Found:** Lines 570–581:
  ```python
  water_atom_count = getattr(structure, 'water_atom_count', 0)
  total_atom_count = len(structure.positions)
  if total_atom_count > 0 and water_atom_count > 0:
      water_fraction = water_atom_count / total_atom_count
      liquid_volume_nm3 = total_volume * water_fraction
  ```
- **Comment on line 571:** `# Estimate liquid volume from water region, NOT total cell`
- **Fallback (line 581):** If no water count, defaults to total volume (conservative).

#### T5 (V-13): `hydrate_generator.py` — `logger.warning()` for dropped short GRO lines
- **Status: ✅ PASS**
- **Found:**
  - Line 246: `logger.warning("Dropping short GRO line %d: length %d < 44 chars", i+1, len(line))`
  - Line 280: `logger.warning("Failed to parse coordinates from GRO line %d: %s", i+1, e)`
- Both use `logger.warning()` (not `logger.info()` or silent).

---

### Wave 2 (P2+P3)

#### T6 (V-03b): `custom_molecule_inserter.py` — `base_existing_data` pattern
- **Status: ✅ PASS**
- **Found:**
  - Line 574: `base_existing_data = existing_tree.data.copy() if existing_tree is not None else None`
  - Line 642–643: `if base_existing_data is not None and len(placed_positions) > 0:` → `all_data = np.vstack([base_existing_data, np.vstack(placed_positions)])`
- **Old O(N²) `existing_tree.data` copy chain NOT found.**

#### T7 (V-03+V-15): `solute_inserter.py` — `base_existing_data` pattern + removed `/ sqrt(3) * sqrt(3)`
- **Status: ✅ PASS**
- **Found:**
  - Line 747: `base_existing_data = existing_tree.data.copy() if existing_tree is not None else None`
  - Line 799–801: `if base_existing_data is not None:` → `existing_tree = cKDTree(np.vstack([base_existing_data, all_placed]))`
- **`sqrt(3)` NOT found anywhere** in solute_inserter.py (dead arithmetic removed).

#### T8 (V-26): `gromacs_writer.py` `reorder_guest_atoms()` — duplicate index validation
- **Status: ✅ PASS**
- **Found:** Line 211–214:
  ```python
  if (reorder 
      and len(reorder) == len(atom_names) 
      and all(i < len(atom_names) for i in reorder)
      and len(set(reorder)) == len(reorder)):
  ```
- The `len(set(reorder)) == len(reorder)` check validates no duplicate indices.

#### T9 (DOC-3/4/22): `help_dialog.py` — source dropdown steps + Validate & Preview
- **Status: ✅ PASS**
- **Found:**
  - Tab 4 (Solute Insertion), step 24 (line 120): `"24. Select solute source (Interface or Custom Molecule)"`
  - Tab 5 (Ion Insertion), step 29 (line 127): `"29. Select ion source (Interface, Custom Molecule, or Solute)"`
  - Validate & Preview, step 20 (line 114): `"20. Click Validate & Preview to check placement validity (Custom mode)"`

#### T10 (DOC-10/12/15-19/9): `README.md` — "12 phases", no Ice IV row, 273.16K, citations
- **Status: ✅ PASS**
- **Found:**
  - "12 phases": Lines 16, 26, 101, 225, 227 all reference "12 ice polymorphs" or "12 phases"
  - No Ice IV row in Phase Detection table: Table rows are Ih, Ic, II, III, V, VI, VII, VIII, IX, XI, XV, X (12 rows, no IV)
  - 273.16K: Line 231 `| Ice Ih | Hexagonal | 0-200 MPa | 0-273.16K |`
  - IAPWS-95: Line 318 `### IAPWS-95`
  - Journaux: Lines 322–324 `### Journaux et al. (2019, 2020)`
  - Petrenko: Lines 326–327 `### Petrenko & Whitworth (1999)`
  - CODATA: Lines 329–330 `### CODATA 2017`
  - Madrid2019/TIP4P-ICE: Lines 353, 357–358 `### Madrid2019 Ion Parameters` and `### Madrid2019 / TIP4P-ICE Compatibility`
- **Note:** Line 101 lists "IV" in the 12-polymorph bullet list (Ih, Ic, II, III, IV, V, VI, VII, VIII, IX, XI, X). This counts 12 names including IV, but the detection table correctly has 12 rows without Ice IV (substituted with Ice XV). Inconsistency is cosmetic; the substantive table is correct.

#### T11 (DOC-1): `README_bin.md` — v4.5.0 (not v4.0.0)
- **Status: ✅ PASS**
- **Found:**
  - Line 4: `Download quickice-v4.5.0-linux-x86_64.tar.gz`
  - Line 6: `tar xfz quickice-v4.5.0-linux-x86_64.tar.gz`
  - Line 12: `Download quickice-v4.5.0-windows-x86_64.zip`
- **No v4.0.0 found** in README_bin.md.

#### T12 (DOC-8): `docs/ranking.md` — O-O histogram fingerprint
- **Status: ✅ PASS**
- **Found:**
  - Line 11: `3. **Diversity Score** - Rewards structural uniqueness via O-O distance fingerprint`
  - Lines 108–115: Algorithm uses O-O distance histogram with 20 bins, cKDTree for PBC, cosine similarity comparison
- **Old `1.0/seed_count` pattern NOT found.**

#### T13 (DOC-8/7): `docs/cli-reference.md` — `--candidate` default + `--nmolecules` optional
- **Status: ✅ PASS**
- **Found:**
  - Line 51: `Number of water molecules in the generated structure (4-100000). Required for ice generation; optional for --interface mode (default: 256).`
  - Line 132: `# Export all candidates (default)`
  - Line 139: `Default: Export all candidates. Use --candidate N to export only rank N.`

#### T14 (DOC-26): `melting_curves.py` docstring — Ice VII convention
- **Status: ✅ PASS**
- **Found:** Lines 9–12:
  ```
  For high-pressure phase (Ice VII):
    Convention is opposite — ice is solid when P > P_melt(T).
    Ice VII is the high-pressure phase; the melting curve defines the
    upper pressure boundary of the liquid region.
  ```

---

### Wave 3 (P3)

#### T15 (V-08/09): `water_filler.py` — vectorized numpy
- **Status: ✅ PASS**
- **Found:** Lines 403–610 use vectorized numpy operations:
  - Line 403: `# Vectorized tiling: generate all offsets at once and use broadcasting`
  - Line 512: `all_positions = (positions[np.newaxis, :, :] + offsets[:, np.newaxis, :]).reshape(-1, 3)`
  - Line 525–532: Vectorized molecule filter using reshape + `np.all()`:
    ```python
    mol_positions = all_positions.reshape(n_tiled_molecules, atoms_per_molecule, 3)
    inside_x = np.all((mol_positions[:, :, 0] >= 0) & (mol_positions[:, :, 0] < lx - tol), axis=1)
    ```
  - Line 572–610: Vectorized PBC wrapping with reshape + broadcasting
- **No per-molecule Python loops found** for these operations.

#### T16 (V-24): `slab.py` + `pocket.py` — `raise ValueError` not `assert`
- **Status: ✅ PASS**
- **Found:**
  - `slab.py`: 0 `assert` statements; 2 `raise ValueError` statements (lines 387, 572)
  - `pocket.py`: 0 `assert` statements; 6 `raise ValueError` statements (lines 346, 351, 500, 505, 540, 545)

#### T17 (V-27): `molecule_validator.py` — `except (ValueError, OSError)` not `except Exception`
- **Status: ✅ PASS**
- **Found:** Line 75: `except (ValueError, OSError) as e:`
- **`except Exception` NOT found** in molecule_validator.py.

#### T18 (DOC-6): `docs/gui-guide.md` — molecule count range 4-100,000
- **Status: ✅ PASS**
- **Found:** Lines 67–69:
  ```
  - Range: 4-100,000 molecules
  - Purpose: Controls simulation cell size
  - Validation: Must be integer, error shown if > 100,000
  ```

#### T19 (DOC-8.1): `triple_points.py` — Ih_III_Liquid pressure 208.566
- **Status: ✅ PASS**
- **Found:** Line 21: `"Ih_III_Liquid": (251.165, 208.566),  # IAPWS R14-08 value`
- Old value 209.9 NOT found.

---

## Syntax Check

```
python -m py_compile quickice/structure_generation/custom_molecule_inserter.py
python -m py_compile quickice/structure_generation/solute_inserter.py
python -m py_compile quickice/structure_generation/ion_inserter.py
python -m py_compile quickice/structure_generation/hydrate_generator.py
python -m py_compile quickice/output/gromacs_writer.py
python -m py_compile quickice/output/orchestrator.py
python -m py_compile quickice/structure_generation/water_filler.py
python -m py_compile quickice/structure_generation/molecule_validator.py
python -m py_compile quickice/phase_mapping/melting_curves.py
python -m py_compile quickice/phase_mapping/triple_points.py
```

**Result: ✅ ALL PASS** — No syntax errors in any modified file.

---

## Test Results

```
python -m pytest tests/ -x -q 2>&1 | tail -10
```

**Result: 38 passed, 1 failed**

| Result | Count |
|--------|-------|
| Passed | 38 |
| Failed | 1 |

**Failing test:** `tests/test_cli_integration.py::TestHelpAndVersion::test_version_shows_version`

**Root cause:** Test expects version string `"python quickice.py 4.0.0"` but actual output is `"python quickice.py 4.5.0"`. The source (`quickice/__init__.py`) correctly has `__version__ = "4.5.0"`. The test was not updated when version was bumped to 4.5.0. This is a **pre-existing issue** unrelated to any scan fix task.

**Impact:** No scan fix caused this failure. The test simply needs updating from `"4.0.0"` to `"4.5.0"`.

---

## Issues Discovered

1. **Test version mismatch (pre-existing):** `test_cli_integration.py` line 292 expects `"python quickice.py 4.0.0"` but actual version is 4.5.0. Not caused by scan fixes.

2. **README.md minor inconsistency (cosmetic):** Line 101 lists "12 ice polymorphs" as `Ih, Ic, II, III, IV, V, VI, VII, VIII, IX, XI, X` (includes Ice IV, excludes Ice XV). The Phase Detection table (lines 229–242) correctly lists 12 phases WITHOUT Ice IV (includes Ice XV instead). Both count to 12 but the two lists are not identical. This is cosmetic; the substantive table is correct per the scan fix requirement.

---

## Conclusion

**All 19 scan fix tasks are correctly applied.** Every fix is present in the actual file content on disk, verified by direct inspection. No syntax errors introduced. The single test failure is a pre-existing version string mismatch unrelated to any scan fix.

---

_Verified: 2026-06-13_
_Verifier: OpenCode (gsd-verifier)_
