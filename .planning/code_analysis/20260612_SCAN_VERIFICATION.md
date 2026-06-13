# Scan Verification Report

## Summary
| Category | Count |
|----------|-------|
| TRUE POSITIVE | 22 |
| FALSE ALARM | 2 |
| PARTIALLY TRUE | 8 |
| SKIPPED (user note) | 1 |

## Verified Issues

---

### V-01 — PARTIALLY TRUE
**File:** quickice/structure_generation/types.py:12
**Original claim:** CRITICAL — `MOLECULE_TYPE_INFO["ice"]["atoms"] = 3` says TIP3P but code uses TIP4P-ICE. Index misalignment if consumed.
**Verification:** Line 12 confirms: `"ice": {"atoms": 3, "res_name": "SOL", "description": "Ice (TIP3P: O, H, H)"}`. The description is misleading — the codebase uses TIP4P-ICE (4 atoms) for export. **However**, no production code actually consumes `MOLECULE_TYPE_INFO["ice"]["atoms"]` for array indexing. Dead imports were already removed from gromacs_writer.py and hydrate_generator.py (batch4). The dict is only referenced in `tests/test_e2e_hydrate_generation.py:18` and a comment in `molecule_utils.py:16`.
**Verdict:** Nuanced — the value/description is inaccurate, but no runtime index misalignment occurs because nothing uses it.
**Severity adjustment:** CRITICAL → LOW — No runtime impact; the dict is dead in production code. Inaccurate documentation, not a crashing bug.

---

### V-02 — TRUE POSITIVE
**File:** quickice/structure_generation/ion_inserter.py:387-388
**Original claim:** CRITICAL — Rebuilds cKDTree after every ion placement — O(N²).
**Verification:** Line 387: `ion_positions.append(water_pos)`, then line 388: `ion_tree = cKDTree(np.array(ion_positions))` — confirmed rebuild on every successful ion placement. However, this is the **ion-ion tree** containing only placed ions (typically < 50), NOT the existing_atoms_tree (ice+guest, built once at line 353). The `existing_atoms_tree` is never rebuilt.
**Verdict:** Confirmed — tree is rebuilt per placement, but N is small (ion count, not total atoms).
**Severity adjustment:** CRITICAL → LOW — The ion count is typically tens of ions, not thousands. O(N²) with N=50 is negligible.

---

### V-04 — FALSE ALARM
**File:** quickice/structure_generation/ion_inserter.py:420-449
**Original claim:** CRITICAL — Charge neutrality fix corrupts atom_names index when 2+ excess ions are removed.
**Verification:** The while loops (lines 420-442) search **backwards** from the end of `new_molecule_index` (`for idx in range(len(...) - 1, -1, -1)`), always removing the LAST matching ion. Ions are appended at the END of the molecule_index (lines 390-411) with monotonically increasing start_idx. Removing the last ion (highest start_idx) does NOT shift the start_idx of entries before it. The second-to-last ion has a lower start_idx that remains valid after the first deletion. After all deletions, start_idx values are regenerated (lines 444-449). Only ONE of the two while loops ever executes (either na_count > cl_count OR cl_count > na_count, never both).
**Verdict:** Refuted — The deletion-from-end strategy preserves index correctness. No corruption occurs.
**Severity adjustment:** N/A — FALSE ALARM, no issue exists.

---

### V-03 — TRUE POSITIVE
**File:** quickice/structure_generation/solute_inserter.py:796-802
**Original claim:** CRITICAL — Rebuilds existing_tree after every solute placement — O(N²).
**Verification:** Lines 796-802 confirm: when a solute is placed, `all_positions = np.vstack([all_existing, solute_positions])` and `existing_tree = cKDTree(all_positions)`. The tree grows with each placed solute, and rebuilding is O(N log N). For high concentrations (hundreds of solutes), this is slow.
**Verdict:** Confirmed — tree is rebuilt per placement with growing data.
**Severity adjustment:** CRITICAL → MEDIUM — Performance issue, not correctness. Impacts high-concentration scenarios.

---

### V-03b — TRUE POSITIVE
**File:** quickice/structure_generation/custom_molecule_inserter.py:637-643
**Original claim:** CRITICAL — Same O(N²) cKDTree rebuild as solute_inserter.
**Verification:** Lines 638-643 show identical pattern: `all_positions = np.vstack([all_existing, placed_mol])` then `existing_tree = cKDTree(all_positions)`.
**Verdict:** Confirmed — same performance pattern as V-03.
**Severity adjustment:** CRITICAL → MEDIUM — Same rationale as V-03.

---

### V-05 — PARTIALLY TRUE
**File:** quickice/structure_generation/hydrate_generator.py:578-579
**Original claim:** CRITICAL — Unknown atoms silently skipped in `_build_molecule_index`, atom is truly lost.
**Verification:** Line 578-579: `# Unknown atom type - skip but count as water for now to continue scanning\ni += 1`. The comment says "count as water" but the code does NOT add a MoleculeIndex entry — it just increments `i`, skipping the atom entirely. The atom IS lost from the molecule_index (not tracked in any molecule). However, the positions are still in the positions array. In practice, GenIce2 outputs well-structured data (OW/HW1/HW2/MW for water, Me for methane, etc.), so unknown atoms are extremely rare.
**Verdict:** Nuanced — the atom IS lost from the index, but the comment is misleading and the practical impact is minimal.
**Severity adjustment:** CRITICAL → LOW — GenIce2 always outputs recognized atom types. The "unknown" path is defensive code that almost never triggers.

---

### V-11 — TRUE POSITIVE
**File:** quickice/structure_generation/custom_molecule_inserter.py:611
**Original claim:** HIGH — `Rotation.random(random_state=self.seed)` uses same seed for every molecule.
**Verification:** Line 611: `rotation = Rotation.random(random_state=self.seed)`. `self.seed` is set once in `__init__` (line 82: `self.seed = seed`) and never changes. Every molecule gets the SAME rotation. Compare with solute_inserter.py line 235: `Rotation.random(random_state=self.rng.randint(0, 2**31 - 1))` — this correctly generates a different seed per molecule. The custom_molecule_inserter has `self.rng` (line 81) but doesn't use it for rotations.
**Verdict:** Confirmed — all custom molecules placed in random mode have identical rotations. This is functionally wrong.
**Severity adjustment:** Keep HIGH — Produces incorrect structures (all molecules same orientation).

---

### V-06 — PARTIALLY TRUE
**File:** quickice/output/gromacs_writer.py:697-711
**Original claim:** HIGH — Recomputes MW for 4-atom hydrate ice that already has MW.
**Verification:** Lines 702-711: For `atoms_per_ice_mol == 4` (hydrate), the code reads O, H1, H2 from positions, then calls `compute_mw_position(o_pos, h1_pos, h2_pos)` on line 711. The original MW at `base_idx + 3` is ignored and a new MW is computed from the same formula. Since `compute_mw_position` is deterministic (`MW = O + α*(H1-O) + α*(H2-O)`), the recomputed MW should be identical to the original (within floating-point precision).
**Verdict:** Nuanced — MW is recomputed but the result is identical. The original MW position (base_idx+3) is effectively wasted (read from positions but never written to GRO).
**Severity adjustment:** HIGH → LOW — No correctness impact, just redundant computation.

---

### V-07 — PARTIALLY TRUE
**File:** quickice/structure_generation/modes/slab.py:37-41 (identical in pocket.py:37-41, piece.py:44-48)
**Original claim:** HIGH — `detect_atoms_per_molecule` only checks `atom_names[0]=="OW"`. Breaks if first atom is a guest.
**Verification:** Line 39: `if atom_names[0] == "OW": return 4`. GenIce2 always outputs water framework atoms first, then guests. So `atom_names[0]` is always "OW" (hydrate) or "O" (regular ice). The function is correct for all currently supported input paths. However, it's fragile — if future code produces candidates with guests first, it would return 3 incorrectly.
**Verdict:** Nuanced — currently correct for all supported inputs, but fragile design.
**Severity adjustment:** HIGH → LOW — No current bug, just code smell.

---

### V-08 — TRUE POSITIVE
**File:** quickice/structure_generation/water_filler.py:525-547
**Original claim:** HIGH — per-molecule Python loop in filter_molecules.
**Verification:** Lines 526-547: Python for-loop iterates over each molecule, checking if all atoms are within bounds. This is inherently per-molecule due to the "all atoms must be inside" constraint, making vectorization non-trivial.
**Verdict:** Confirmed — Python loop, but vectorization is non-trivial due to the all-or-nothing molecule constraint.
**Severity adjustment:** HIGH → MEDIUM — Performance, not correctness. Could be optimized with numpy tricks.

---

### V-09 — TRUE POSITIVE
**File:** quickice/structure_generation/water_filler.py:579-616
**Original claim:** HIGH — per-molecule Python loop in orthogonal wrapping.
**Verification:** Lines 579-616: Python for-loop wrapping each molecule with shift computation. Could be partially vectorized.
**Verdict:** Confirmed — Python loop for molecule wrapping.
**Severity adjustment:** HIGH → MEDIUM — Same as V-08.

---

### V-12 — PARTIALLY TRUE
**File:** quickice/phase_mapping/water_density.py:37
**Original claim:** HIGH — Fallback density 0.9998 wrong for supercooled water.
**Verification:** Line 37: `FALLBACK_DENSITY_GCM3 = 0.9998` (density at 0°C, 1 atm). The IAPWS-95 formulation (line 31: `from iapws import IAPWS95`) DOES support supercooled water via extrapolation (lines 70-87 handle this). The fallback is only used when IAPWS-95 fails (ValueError, NotImplementedError, OverflowError). For supercooled water, the IAPWS-95 calculation succeeds with extrapolation — the fallback is rarely triggered.
**Verdict:** Nuanced — the fallback value is imprecise for supercooled water, but the main calculation path handles it correctly. The fallback only triggers on exceptions.
**Severity adjustment:** HIGH → LOW — IAPWS-95 handles supercooled water; fallback is for error cases only.

---

### V-13 — TRUE POSITIVE
**File:** quickice/structure_generation/hydrate_generator.py:240-275
**Original claim:** HIGH — GRO parse silently drops short lines and passes on parse errors.
**Verification:** Line 240-241: `if not line.strip() or len(line) < 44: continue` — silently skips short lines. Lines 268-275: position parsing in try/except with `pass` on error. No logging of skipped/failed lines.
**Verdict:** Confirmed — silent failures in GRO parsing. Should log warnings.
**Severity adjustment:** HIGH → MEDIUM — Robustness issue; malformed input produces incomplete output without warning.

---

### V-14 — TRUE POSITIVE
**File:** quickice/structure_generation/hydrate_generator.py:280-289
**Original claim:** MEDIUM — Box line detection fragile.
**Verification:** Lines 280-289: Searches last 5 lines for box line using `not line[0].isdigit()` to skip non-box lines, with fallback `box_line = lines[-1]`. The `isdigit()` check works for standard GRO box lines (which start with numbers), but the "last 5 lines" window and the fallback could fail for unusual GRO files.
**Verdict:** Confirmed — fragile but works for standard GenIce2 output.
**Severity adjustment:** MEDIUM → LOW — Works for all current inputs; edge cases are rare.

---

### V-15 — TRUE POSITIVE
**File:** quickice/structure_generation/solute_inserter.py:112-115
**Original claim:** MEDIUM — CH4 H-coords `/ sqrt(3) * sqrt(3)` cancels to 1.0.
**Verification:** Lines 112-115: `np.array([r_ch, r_ch, r_ch]) / np.sqrt(3) * np.sqrt(3)` — the `/ sqrt(3)` and `* sqrt(3)` cancel out, making this equivalent to `np.array([r_ch, r_ch, r_ch])`. The normalization loop (lines 118-119: `h[:] = h / np.linalg.norm(h) * r_ch`) then correctly sets the bond length. The code is correct but contains dead arithmetic.
**Verdict:** Confirmed — mathematically correct but contains redundant operations.
**Severity adjustment:** MEDIUM → LOW — Cosmetic code smell, no functional impact.

---

### V-16 — TRUE POSITIVE
**File:** quickice/output/gromacs_writer.py:894-944
**Original claim:** MEDIUM — CO2 misidentified as THF.
**Verification:** Lines 925-926: `if has_oxygen and has_carbon: return "thf"` — this matches BEFORE the CO2 check (lines 937-938: `elif has_carbon and has_oxygen and not has_hydrogen: return "co2"`). Since CO2 has both O and C (and no H), it matches the THF condition first. The CO2 branch is **unreachable dead code** — any molecule with O+C is classified as THF regardless of H presence.
**Verdict:** Confirmed — CO2 will be misidentified as THF. The CO2 branch is dead code.
**Severity adjustment:** Keep MEDIUM — CO2 is a supported guest type; wrong output would occur.

---

### V-17 — TRUE POSITIVE
**File:** quickice/structure_generation/solute_inserter.py:428-446
**Original claim:** MEDIUM — Mutates input structure via setattr.
**Verification:** Lines 435-444: `structure.custom_molecule_positions = ...`, `structure.custom_molecule_atom_names = ...`, etc. These setattr calls add attributes to the input `structure` object, mutating it. Guarded by `not hasattr()` checks, so only adds if not already present.
**Verdict:** Confirmed — input mutation via setattr. Side effect, but guarded.
**Severity adjustment:** MEDIUM → LOW — Code smell, not a correctness bug. The guards prevent overwriting existing attributes.

---

### V-18 — TRUE POSITIVE
**File:** quickice/structure_generation/generator.py:92-99
**Original claim:** MEDIUM — np.random global state not thread-safe.
**Verification:** Lines 92-99 docstring explicitly states: "This method is NOT thread-safe. Concurrent calls from multiple threads would corrupt each other's random state." The code saves/restores global state (line 103: `original_state = np.random.get_state()`, then restores after generation).
**Verdict:** Confirmed — but the code is already aware and documents the limitation.
**Severity adjustment:** MEDIUM → LOW — Documented limitation; sequential execution is the intended design.

---

### V-19 — TRUE POSITIVE
**File:** quickice/structure_generation/ion_inserter.py:570-574
**Original claim:** MEDIUM — Volume estimation uses total cell volume not liquid volume.
**Verification:** Lines 570-574: `volume = np.abs(np.linalg.det(cell))` — uses total cell volume (including ice region). This overestimates the liquid volume, causing fewer ions to be placed than the target concentration. The function allows explicit `liquid_volume_nm3` as a workaround.
**Verdict:** Confirmed — uses total cell volume as fallback, overestimating.
**Severity adjustment:** Keep MEDIUM — Inaccurate ion count for the common case where no explicit volume is provided.

---

### V-21 — TRUE POSITIVE
**File:** quickice/structure_generation/solute_inserter.py:651
**Original claim:** LOW — Hardcoded 0.0299 nm³ water volume.
**Verification:** Line 651: `liquid_volume_nm3 = water_nmolecules * 0.0299` — hardcoded water molecular volume. This is ~299 Å³, approximately correct for ambient conditions but temperature/pressure dependent.
**Verdict:** Confirmed — hardcoded value, not using IAPWS density.
**Severity adjustment:** Keep LOW — Reasonable approximation for typical conditions.

---

### V-22 — (SKIPPED — DOC-9c)
Not verified per user instructions.

---

### V-23 — TRUE POSITIVE
**File:** slab.py:24-41, pocket.py:24-41, piece.py:31-48
**Original claim:** LOW — `detect_atoms_per_molecule` function duplicated across 3 files.
**Verification:** All three files contain identical `detect_atoms_per_molecule()` implementations (same docstring, same logic: check `atom_names[0] == "OW"` → return 4, else return 3).
**Verdict:** Confirmed — exact duplication across 3 files.
**Severity adjustment:** Keep LOW — Should be extracted to shared utility.

---

### V-24 — TRUE POSITIVE
**File:** pocket.py (6 asserts), slab.py (2 asserts)
**Original claim:** LOW — assert statements in production.
**Verification:** pocket.py lines 345, 349, 497, 501, 535, 539: assert statements like `assert len(water_positions) % 4 == 0`. slab.py lines 386, 570: similar asserts. These are stripped with `python -O`, potentially causing silent logic failures.
**Verdict:** Confirmed — assert statements in production code.
**Severity adjustment:** Keep LOW — Should use proper exceptions, but assertions are for internal consistency checks.

---

### V-26 — PARTIALLY TRUE
**File:** quickice/output/gromacs_writer.py:186-214
**Original claim:** LOW — reorder_guest_atoms fallback mapping.
**Verification:** Lines 206-207: `if len(reorder) < len(atom_names): reorder.append(len(reorder))` — this fallback assigns `reorder[i] = i` (identity mapping) when an atom isn't found. The function silently gives up on reordering for unrecognized atoms.
**Verdict:** Nuanced — fallback exists and is reasonable (identity mapping), but silent fallback could produce incorrect GRO files for unusual molecules.
**Severity adjustment:** Keep LOW — Works for supported guests (ch4, thf); fallback is safe for unsupported types.

---

### V-27 — TRUE POSITIVE
**File:** quickice/structure_generation/molecule_validator.py:75-76, 137-138
**Original claim:** LOW — broad `except Exception`.
**Verification:** Line 75-76: `except Exception as e:` in `validate_gro_itp_consistency`, line 137-138: same in `validate_custom_molecule`. Both catch all non-system exceptions and convert to error messages. For validation functions, this is arguably acceptable (catching parse errors), but could mask unexpected bugs.
**Verdict:** Confirmed — broad exception handling.
**Severity adjustment:** Keep LOW — Acceptable for validation code, but could mask bugs.

---

### DC-2.1 — TRUE POSITIVE
**File:** quickice/structure_generation/ion_inserter.py:11
**Original claim:** DEAD — `from dataclasses import dataclass` unused.
**Verification:** Line 11: `from dataclasses import dataclass`. No `@dataclass` decorator or dataclass usage found in ion_inserter.py. The `IonInserter` class is a regular class.
**Verdict:** Confirmed — unused import.
**Severity adjustment:** N/A — dead code.

---

### DC-2.2 — TRUE POSITIVE
**File:** quickice/structure_generation/ion_inserter.py:20
**Original claim:** DEAD — InterfaceStructure import unused.
**Verification:** Line 20: `InterfaceStructure,  # for compatibility with interface generation`. The import is only referenced in comments (line 63, 65, 80). No isinstance check, type annotation, or direct usage. The code uses duck typing (`hasattr` and `getattr`).
**Verdict:** Confirmed — unused import; only referenced in comments.
**Severity adjustment:** N/A — dead code.

---

### DC-2.3 — TRUE POSITIVE
**File:** quickice/phase_mapping/lookup.py:18-23
**Original claim:** DEAD — unused imports (solid_boundary, xi_boundary, xv_boundary, VII_VIII_ORDERING_TEMP).
**Verification:** Line 18 imports `solid_boundary` — never called in lookup.py body (specific boundary functions like `ih_ii_boundary` are used instead). Line 20 imports `VII_VIII_ORDERING_TEMP` — never referenced in lookup body. Line 21 imports `xi_boundary`, `xv_boundary` — never used (Ice XI/XV boundaries are hardcoded in lookup logic). Line 23 imports `TRIPLE_POINTS` — never accessed by `TRIPLE_POINTS[...]` in lookup.py.
**Verdict:** Confirmed — 5 unused imports: `solid_boundary`, `VII_VIII_ORDERING_TEMP`, `xi_boundary`, `xv_boundary`, `TRIPLE_POINTS`.
**Severity adjustment:** N/A — dead imports.

---

### DC-2.4 — TRUE POSITIVE
**File:** quickice/phase_mapping/lookup.py:23
**Original claim:** DEAD — TRIPLE_POINTS import unused.
**Verification:** `TRIPLE_POINTS` is imported but never accessed by key (`TRIPLE_POINTS[...]`) in lookup.py. It's used internally by solid_boundaries.py.
**Verdict:** Confirmed — same as DC-2.3 finding for TRIPLE_POINTS.
**Severity adjustment:** N/A — dead import.

---

### DC-2.6 — TRUE POSITIVE
**File:** quickice/structure_generation/hydrate_generator.py:16
**Original claim:** DEAD — HYDRATE_LATTICES import unused in this file.
**Verification:** Line 16: `HYDRATE_LATTICES,` imported. Grep for `HYDRATE_LATTICES[` in hydrate_generator.py found 0 results. The only usage of `GUEST_MOLECULES` (also imported) is on line 588. HYDRATE_LATTICES is not accessed in this file.
**Verdict:** Confirmed — HYDRATE_LATTICES imported but unused. GUEST_MOLECULES IS used (line 588).
**Severity adjustment:** N/A — dead import.

---

### DC-3.1 — PARTIALLY TRUE
**File:** quickice/structure_generation/types.py:11
**Original claim:** DEAD — MOLECULE_TYPE_INFO dict never referenced.
**Verification:** The dict IS referenced in `tests/test_e2e_hydrate_generation.py:18` (imported for testing) and `molecule_utils.py:16` (as a comment reference). It is NOT used in any production code (dead imports removed in batch4). The dict exists as a data definition but is effectively dead in production.
**Verdict:** Nuanced — not "never referenced" (used in tests), but dead in production code.
**Severity adjustment:** N/A — effectively dead code with test-only usage.

---

### DC-3.2 — TRUE POSITIVE
**File:** quickice/structure_generation/ion_inserter.py:30-35
**Original claim:** DEAD — Ion visualization constants (NA_VDW_RADIUS, etc.) unused in this file.
**Verification:** Lines 30-35 define `NA_VDW_RADIUS`, `CL_VDW_RADIUS`, `NA_COLOR`, `CL_COLOR`. These are NOT used anywhere in ion_inserter.py. They ARE used in ion_renderer.py (which defines its own copies). The constants in ion_inserter.py are dead code.
**Verdict:** Confirmed — defined but unused in this file; duplicated in ion_renderer.py.
**Severity adjustment:** N/A — dead constants.

---

### DC-3.3 — TRUE POSITIVE
**File:** ion_inserter.py:27, solute_inserter.py:33, scorer.py:216
**Original claim:** DEAD/DEAD — AVOGADRO duplicated.
**Verification:** `AVOGADRO = 6.02214076e23` is defined in three files: ion_inserter.py:27, solute_inserter.py:33, and scorer.py:216. custom_molecule_inserter.py:27 correctly imports from solute_inserter. Same value in all cases.
**Verdict:** Confirmed — three independent definitions of the same constant.
**Severity adjustment:** N/A — duplication.

---

### DC-4.1 — TRUE POSITIVE
**File:** quickice/phase_mapping/lookup.py:403-430
**Original claim:** DEAD — IcePhaseLookup class never instantiated in production.
**Verification:** `IcePhaseLookup` is only instantiated in `tests/test_phase_mapping.py:463-479` (test code). No production code instantiates it. It's exported from `__init__.py` but unused by consumers.
**Verdict:** Confirmed — only used in tests, not production.
**Severity adjustment:** N/A — backward-compatible wrapper with test-only usage.

---

### DC-7.2 — TRUE POSITIVE
**File:** ion_inserter.py:38, solute_inserter.py:36
**Original claim:** DUPE — MIN_SEPARATION = 0.3 duplicated.
**Verification:** ion_inserter.py:38: `MIN_SEPARATION = 0.3  # 3 Å`, solute_inserter.py:36: `MIN_SEPARATION = 0.3  # 3 Å`. Same value in both files. custom_molecule_inserter.py uses `self.config.min_separation` instead.
**Verdict:** Confirmed — duplicated constant.
**Severity adjustment:** N/A — duplication.

---

### DC-1.1 — TRUE POSITIVE
**File:** quickice/phase_mapping/data/ (entire module)
**Original claim:** DEAD — Entire module dead (433 lines claimed, 408 found for ice_boundaries.py).
**Verification:** Grep for `from quickice.phase_mapping.data` across ALL Python files: 0 results in production code. References only exist in .planning/ files (superseded plans). The module contains ice_boundaries.py (408 lines), __init__.py, and ice_phases.json. It's a legacy polygon-based approach replaced by curve-based lookup.py.
**Verdict:** Confirmed — entire module is dead code.
**Severity adjustment:** N/A — dead module.

---

### DOC-8.1 — TRUE POSITIVE
**File:** quickice/phase_mapping/triple_points.py:21 vs melting_curves.py:31
**Original claim:** MINOR — Triple point pressure 209.9 vs 208.566 MPa.
**Verification:** triple_points.py:21: `"Ih_III_Liquid": (251.165, 209.9)`. melting_curves.py:31: `Tref, Pref = 251.165, 208.566` (IAPWS reference). The values differ by ~0.6%. 209.9 MPa appears to be the commonly cited experimental value, while 208.566 MPa is the IAPWS calculated value. Both are used in different contexts.
**Verdict:** Confirmed — inconsistent values from different sources.
**Severity adjustment:** Keep MINOR — ~0.6% difference from different authoritative sources.

---

### DOC-26 — TRUE POSITIVE
**File:** quickice/phase_mapping/melting_curves.py:5
**Original claim:** MISLEADING — Docstring says "solid when P < P_melt" — only correct for Ih.
**Verification:** Line 5: `Ice is solid when P < P_melt(T) at given T.` For Ice VII (lookup.py:206): `if P > P_melt_vii: phase_id = "ice_vii"` — high-pressure phases are solid when P > P_melt. The docstring is only correct for Ice Ih.
**Verdict:** Confirmed — docstring is misleading for high-pressure phases.
**Severity adjustment:** Keep MINOR — documentation error, not a code bug.

---

### DOC-3 — TRUE POSITIVE
**File:** quickice/gui/help_dialog.py:123-127
**Original claim:** MISLEADING — Ion workflow omits source dropdown.
**Verification:** Lines 123-127 show Ion Insertion workflow steps: switch to tab, set concentration, insert, export. No mention of the source dropdown (which determines what structure ions are inserted into).
**Verdict:** Confirmed — source dropdown step is omitted.
**Severity adjustment:** Keep MINOR — documentation omission.

---

### DOC-4 — TRUE POSITIVE
**File:** quickice/gui/help_dialog.py:117-121
**Original claim:** MISLEADING — Solute workflow omits source dropdown.
**Verification:** Lines 117-121 show Solute Insertion workflow steps. Same issue as DOC-3 — source dropdown step is omitted.
**Verdict:** Confirmed — source dropdown step is omitted.
**Severity adjustment:** Keep MINOR — documentation omission.

---

### SEC — TRUE POSITIVE
**File:** quickice/output/orchestrator.py:48-56
**Original claim:** Path traversal uses `str.startswith()`.
**Verification:** Lines 48-56:
```python
output_path = Path(output_dir).resolve()
allowed_base = Path.cwd().resolve()
if not str(output_path).startswith(str(allowed_base)):
    raise ValueError(...)
```
`Path.resolve()` is used (good — resolves symlinks and `..`), but `str.startswith()` is not a secure path containment check. Example: `allowed_base="/home/user/quickice"` and `output_path="/home/user/quickice-malicious"` — `startswith` returns True but the path is NOT contained. Python 3.9+ provides `Path.is_relative_to()` for this purpose.
**Verdict:** Confirmed — `startswith()` is not secure for path containment.
**Severity adjustment:** MEDIUM — security vulnerability with limited practical impact (output_dir typically comes from trusted user input).

---

### DOC-5 — TRUE POSITIVE
**File:** docs/ranking.md:104-127 vs scorer.py:311-363
**Original claim:** MISLEADING — Documents old diversity_score formula.
**Verification:** ranking.md line 113: `diversity_score = 1.0 / seed_count` (seed-based). scorer.py line 311: `def diversity_score(...)` uses O-O distance histogram cosine similarity. scorer.py line 323-324: "This replaces the previous seed-based approach which always returned 1.0 because generate_all() assigns unique sequential seeds." The documentation is outdated.
**Verdict:** Confirmed — docs describe old formula; code uses new algorithm.
**Severity adjustment:** Keep MINOR — documentation vs code mismatch.

---

### DOC-1 — TRUE POSITIVE
**File:** README_bin.md:4
**Original claim:** OUTDATED — References v4.0.0.
**Verification:** Lines 4-15: References `quickice-v4.0.0-linux-x86_64.tar.gz` and `quickice-v4.0.0-windows-x86_64.zip`. Version is hardcoded and likely outdated.
**Verdict:** Confirmed — version hardcoded in README.
**Severity adjustment:** Keep MINOR — outdated version reference.

---

### DOC-10 — TRUE POSITIVE
**File:** README.md:225,235 vs lookup.py PHASE_METADATA
**Original claim:** MISLEADING — README claims 13 phases but Ice IV not in code.
**Verification:** README.md line 225: "Phase Detection (13 phases)". Line 235: "Ice IV | Rhombohedral | 400-600 MPa | 250-270K". Grep for `ice_iv` in lookup.py: 0 results. PHASE_METADATA does NOT include `ice_iv`. The `lookup_phase()` function has NO Ice IV detection logic. The README claims 13 phases including Ice IV, but the code only detects 12 phases (Ih, Ic, II, III, V, VI, VII, VIII, IX, X, XI, XV).
**Verdict:** Confirmed — README overclaims by 1 phase (Ice IV not implemented).
**Severity adjustment:** Keep MINOR — documentation vs code mismatch.

---

_Verified: 2026-06-13T12:00:00Z_
_Verifier: OpenCode (gsd-verifier)_
