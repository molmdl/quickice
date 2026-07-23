# Code-Level Issue Verification — quickice

**Date:** 2026-07-23
**Mode:** READ-ONLY verification, no fixes applied. Nothing was run (no pytest, no python, no gmx).
**Sources verified:**
1. `.planning/codebase/CONCERNS.md` (9 sections: Tech Debt, Known Bugs, Security, Performance, Fragile Areas, Scaling Limits, Dependencies at Risk, Missing Critical Features, Test Coverage Gaps)
2. `.planning/code_analysis/20260723_vulnerability_scan.md` (12 findings: C1, S1, A1–A5, P1–P3, D1–D2)

**Bias controls:** No other files under `.planning/code_analysis/` or `.planning/codebase/` (prior VERIFICATION / SCAN_VERIFICATION / dead_code / scancode outputs) were read. Every finding below was confirmed by reading the actual source at the cited file:line.

**Verdict legend:** TRUE = claim confirmed against real code. FALSE ALARM = report wrong, code is fine. PARTIALLY TRUE = kernel correct but details/severity off.

---

## Verdict Summary Table

| Issue ID | Source | Claimed Severity | Verdict | Actual Severity | File:line | One-line reality |
|---|---|---|---|---|---|---|
| **C1** | VulnScan | High | **TRUE** | High (edge-case crash) | `modes/piece.py:361` | `logger` used but never imported/defined → `NameError` on the bounds-check branch |
| **S1** | VulnScan | Medium | **PARTIALLY TRUE** | Low (latent/consistency) | `modes/pocket.py:591-601` | Stale `tiling_factor` formula (slab.py fixed it, pocket.py didn't) — confirmed stale, but no demonstrated corruption in the normal single-guest path |
| **A1** | VulnScan | Low | **TRUE** | Low (nit) | `gui/main_window.py:1357` | `result.water_atom_count // 4` hardcodes `4` (next line uses `WATER_VOLUME_NM3`) |
| **A2** | VulnScan | Low | **TRUE** | Low (nit) | `gui/custom_molecule_panel.py:1220,1243,1296` | Three `water_count // 4` sites |
| **A3** | VulnScan | Low | **TRUE** | Low (nit) | `hydrate_generator.py:702,782` | Hardcoded `i += 4` and `MoleculeIndex(i, 4, "water")` for TIP4P water |
| **A4** | VulnScan | Low | **TRUE** (line-list partly wrong) | Low (nit) | `water_filler.py:133` | Local `ATOMS_PER_WATER_MOLECULE = 4` duplicates `types.WATER_ATOMS_PER_MOLECULE`; used at :663,:672 only (vuln-scan's :363,:679 are phantom) |
| **A5** | VulnScan | Low | **TRUE** | Low (nit) | `gui/vtk_utils.py:551` | `4 if (has_ow or has_mw) else 3` magic numbers (GUI render heuristic) |
| **P1** | VulnScan | Low | **TRUE** | Low (perf) | `custom_molecule_inserter.py:938-941` | O(n²) Python COM-COM `np.linalg.norm` loop, warning-only path |
| **P2** | VulnScan | Low | **TRUE** | Low (perf, deliberate) | `solute_inserter.py:977`; `custom_molecule_inserter.py:717` | `buffer_tree` rebuilt per placement (deliberate byte-identical design, batch≤8) |
| **P3** | VulnScan | Low | **TRUE** | Low (perf) | `modes/slab.py:407-419,567-574,668-680` | Three per-molecule Python PBC-wrap loops (O(n), vectorizable) |
| **D1** | VulnScan | Low | **TRUE** | Low (nit) | `ion_inserter.py:34-35` | `NA_VDW_RADIUS`/`CL_VDW_RADIUS` unused in inserter; redefined in `ion_renderer.py:18-19` |
| **D2** | VulnScan | Low | **TRUE** | Low (nit) | `gromacs_ion_export.py:30-33` | `NA_SIGMA`/`CL_SIGMA`/`NA_EPSILON`/`CL_EPSILON` never referenced anywhere |
| **TD1** | CONCERNS | Tech Debt | **TRUE** (=A4) | Low | `water_filler.py:133` | Duplicate water-atoms constant; CONCERNS line list (663,672) is accurate |
| **TD2** | CONCERNS | Tech Debt | **TRUE** (minor report typo) | Low | `hydrate_generator.py:323-326` | `raise RuntimeError(...)` lacks `from e`; siblings have `from e` (report's `from e from e` is a typo — actual code has one `from e`) |
| **TD3** | CONCERNS | Tech Debt | **TRUE** | Low (refactor target) | `gui/main_window.py` etc. | God-object files; line counts confirmed: 2318 / 1395 / 1138 / 1132 |
| **KB** | CONCERNS | Known Bugs | **TRUE** (negative result) | — (no bug) | multiple | "No active crashes" + positive claims (inserters return NEW structs, cKDTree rebuild, comb-rule=2, MoleculetypeRegistry) all verified correct |
| **SEC1** | CONCERNS | Security | **TRUE** | Low (latent) | `cli/pipeline.py:170-176,533-547` vs `gui/*` | CLI enforces `is_relative_to(cwd)`; GUI uses `QFileDialog` with no containment |
| **SEC2** | CONCERNS | Security | **TRUE** | Low | `cli/itp_helpers.py:162,196,317,482` | Broad `except Exception` confirmed (line 234 is narrower `except (OSError, ValueError)`) |
| **PERF1** | CONCERNS | Perf | **TRUE** (=P1) | Low | `custom_molecule_inserter.py:938-941` | O(n²) COM-COM overlap-notice loop |
| **PERF2** | CONCERNS | Perf | **TRUE** | Low | `water_filler.py:108-129` | Per-molecule Python PBC-wrap loop with per-iter matrix multiplies |
| **F1** | CONCERNS | Fragile | **TRUE** (accepted) | — (not a bug) | `cli/pipeline.py:786-830`; `gui/main_window.py` | Duck-typed attrs on `InterfaceStructure` exist as described; **accepted CP-01 per AGENTS.md — No action** |
| **F2** | CONCERNS | Fragile | **TRUE** (accepted) | — (not a bug) | `gui/hydrate_worker.py:15` | `class HydrateWorker(QThread)` confirmed; **accepted per AGENTS.md — No action** |
| **F3** | CONCERNS | Fragile | **TRUE** (documented) | Low | `utils/molecule_utils.py:161-170` | THF heuristic + WARNING comment present exactly as described |
| **F4** | CONCERNS | Fragile | **TRUE** (intentional) | — (by design) | `output/multi_molecule_writer.py:146-155` | NOTE confirms intentional omission of try/except cleanup |
| **F5** | CONCERNS | Fragile | **TRUE** | Low | `custom_guest_bridge.py:346` | Bare `assert key not in sys.modules, ...` — stripped under `python -O` |
| **F6** | CONCERNS | Fragile | **TRUE** | Low | `output/orchestrator.py:77,105,123` | `except Exception` per-candidate/per-diagram, logs+continues → partial results silently |
| **SL1** | CONCERNS | Scaling | **TRUE** | Low (by design) | `multi_molecule_writer.py:143-144` | `if n_atoms > 99999: logger.warning(...)` — warns, does not prevent |
| **SL2** | CONCERNS | Scaling | **TRUE** | — (by design) | `cli/pipeline.py:21,317-322` | `MAX_CSV_ROWS = 10000`, enforced |
| **DEP1** | CONCERNS | Dependency | **TRUE** (descriptive) | — (risk) | `hydrate_generator.py:78-81,253-255` | GenIce2 imported inside function bodies (lazy); no fallback |
| **DEP2** | CONCERNS | Dependency | **TRUE** (descriptive) | — (risk) | `ion_inserter.py:14`; `solute_inserter.py:15-16` | scipy `cKDTree`/`Rotation` top-level hard imports, no fallback |
| **DEP3** | CONCERNS | Dependency | **TRUE** (descriptive) | — (risk) | `entry.py:12,29` | PySide6 via `find_spec`; headless-fragile VTK |
| **DEP4** | CONCERNS | Dependency | **TRUE** (descriptive) | Low | `output/phase_diagram.py:946,953` | `IAPWS97` imported in-function; `except Exception` swallows per-T failures |
| **MCF1** | CONCERNS | Missing Feature | **TRUE** (by design) | — (deferred) | `cli/pipeline.py:102-107` | "Custom-guest CLI support is deferred" message confirmed |
| **TCG1** | CONCERNS | Test Gap | **TRUE** | Medium | `tests/conftest.py:24-27` | `gmx_skipif` skips grompp tests when `gmx` absent |
| **TCG2** | CONCERNS | Test Gap | **TRUE** | Low | gui viewer tests | VTK/headless rendering gap |
| **TCG3** | CONCERNS | Test Gap | **TRUE** | Low | `custom_guest_bridge.py:346` | No `-O`/`PYTHONOPTIMIZE` suite (relates to F5) |
| **TCG4** | CONCERNS | Test Gap | **TRUE** | Low | `custom_molecule_inserter.py:938-941` | No perf test for O(n²) warning loop (relates to P1/PERF1) |

**Verdict counts:** TRUE = 34 · PARTIALLY TRUE = 1 (S1) · FALSE ALARM = 0.

---

## Detailed Findings

### C1 — Undefined `logger` in piece.py (NameError) — TRUE

- **Claim (VulnScan):** `piece.py:361` calls `logger.warning(...)` but `logger` is never defined/imported in the file → `NameError` on the edge-case bounds-check branch.
- **Actual code:**
  - `piece.py` imports (lines 13–32): `numpy`, `molecule_utils`, `types`, `errors`, `water_filler`, `overlap_resolver`, `water_density`. **No `import logging`, no `logger = logging.getLogger(...)`** anywhere.
  - `piece.py:358-363`:
    ```python
    if len(centered_ice_positions) > 0 and len(water_positions) > 0:
        # Bounds check: ensure slicing indices are valid
        if atoms_per_mol > len(centered_ice_positions):
            logger.warning(f"atoms_per_mol ({atoms_per_mol}) exceeds array length ({len(centered_ice_positions)})")
        ice_o_positions = centered_ice_positions[::atoms_per_mol]
    ```
  - `grep -n "logger\|logging" piece.py` returns exactly one line — line 361 (the use). `slab.py`/`pocket.py` have no `logger` either, so the omission is specific to `piece.py`.
- **Traced impact:** When `atoms_per_mol > len(centered_ice_positions)`, the intended graceful warning instead raises `NameError: name 'logger' is not defined`, aborting piece-mode interface generation. `atoms_per_mol` comes from `detect_atoms_per_molecule(...)` (3 for GenIce ice, 4 for TIP4P/hydrate); the branch is reachable when a candidate has fewer total atoms than one molecule's atom count. The report's reachability analysis (a malformed/tiny candidate past `validate_interface_config`, which checks empty positions and cell shape but not `len(positions) >= atoms_per_mol`) is consistent with the code.
- **Verdict: TRUE.** Real crash bug on an edge-case branch where graceful degradation was intended.
- **Suggested action: Fix (P1).** Add `import logging` + `logger = logging.getLogger(__name__)` (mirrors `solute_inserter.py:10-31`). Optionally also guard the slice at :363.

---

### S1 — pocket.py stale `tiling_factor` atom-name rebuild — PARTIALLY TRUE

- **Claim (VulnScan, Medium):** `pocket.py:591-601` still uses the old `tiling_factor` formula that `slab.py:704-722` explicitly replaced and documented as buggy; for pocket guests where cavity removal leaves a non-multiple atom-name list, `processed_guest_atom_names` length ≠ `len(processed_guest_positions)`, corrupting the `InterfaceStructure.atom_names`/`positions` invariant. Report self-hedged as "SUSPICIOUS (needs runtime verification)".
- **Actual code:**
  - `pocket.py:591-601` (single-guest path):
    ```python
    if original_guest_nmolecules > 0 and tiled_guest_nmolecules > 0:
        tiling_factor = tiled_guest_nmolecules // original_guest_nmolecules
        processed_guest_atom_names = guest_atom_names * tiling_factor
        remainder = tiled_guest_nmolecules - (tiling_factor * original_guest_nmolecules)
        if remainder > 0:
            atoms_per_guest = len(guest_atom_names) // original_guest_nmolecules if original_guest_nmolecules > 0 else 0
            if atoms_per_guest > 0:
                processed_guest_atom_names.extend(guest_atom_names[:atoms_per_guest * remainder])
    ```
  - `slab.py:704-722` DID replace this:
    ```python
    # FIX: Compute guest atom names based on ACTUAL tiled positions
    # Previous approach used tiling_factor which assumes tile_structure() returns
    # exactly (tiling_factor * original_guest_nmolecules) molecules.
    # But tile_structure() FILTERS molecules at boundaries ..., causing
    # processed_guest_atom_names to be SHORTER than processed_guest_positions.
    actual_guest_nmolecules = len(processed_guest_positions) // atoms_per_guest
    guest_pattern = guest_atom_names[:atoms_per_guest]
    processed_guest_atom_names = guest_pattern * actual_guest_nmolecules
    ```
- **Traced impact (static):**
  - **Staleness confirmed:** pocket.py uses the old formula; slab.py fixed and documented it. TRUE.
  - **But the specific bug slab.py fixed does NOT apply to pocket.py's tiling:** slab.py's bug was `tile_structure()` *filtering* molecules at boundaries. pocket.py calls `tile_structure(..., filter_molecules=False)` for guests (`pocket.py:541`), so no boundary filtering occurs — `tiled_guest_nmolecules` is an exact multiple of `original_guest_nmolecules` *before* cavity removal.
  - **Cavity removal** (`pocket.py:569-589`) then sets `tiled_guest_nmolecules = len(keep_mols)`, which need not be a multiple → `remainder > 0` is genuinely possible.
  - **However**, in the normal single-guest path, `len(guest_atom_names) = original_guest_nmolecules × atoms_per_guest` (every guest molecule complete), so `atoms_per_guest = len(guest_atom_names) // original_guest_nmolecules` is *exact* (no floor error). The reconstructed length then equals `atoms_per_guest × tiled_guest_nmolecules = len(processed_guest_positions)`. **No mismatch.**
  - The report's truncation scenario requires `len(guest_atom_names)` to be a *non-multiple* of `original_guest_nmolecules`. The only path to that is `_detect_guest_atoms`'s tail `else` branch (`pocket.py:99-101`, `guest_indices.extend(range(i, n))`), which fires only when the candidate ends with fewer than `atoms_per_mol` (4) residual atoms — i.e. a *malformed* candidate. Well-formed GenIce2 output has complete molecules, so this branch does not fire in normal operation.
- **Verdict: PARTIALLY TRUE.** The code is genuinely stale (pocket.py did not port slab.py's fix) — that part is correct. But the claimed runtime corruption (atom-names/positions length mismatch) does **not** trigger in the normal single-guest path with well-formed candidates, because (a) pocket uses `filter_molecules=False` so the slab.py filtering bug is moot, and (b) `len(guest_atom_names)` is a clean multiple of `original_guest_nmolecules` for complete molecules. The report's own "SUSPICIOUS, needs runtime verification" hedge is honest. Severity should be **Low (latent/consistency)**, not Medium.
- **Suggested action: Fix (P3) for consistency / to close the latent edge case** — port slab.py's fix verbatim. Not an active crash.

---

### A1 — Hardcoded `// 4` in main_window.py — TRUE

- **Claim:** `main_window.py:1357` uses `// 4` instead of `WATER_ATOMS_PER_MOLECULE`; next line uses `WATER_VOLUME_NM3`.
- **Actual code** (`main_window.py:1357-1358`):
  ```python
  water_nmolecules = result.water_atom_count // 4
  liquid_vol = water_nmolecules * WATER_VOLUME_NM3
  ```
- **Verdict: TRUE** (nit, AGENTS.md "Never hardcode `4`" rule violation; correct for TIP4P but bypasses the constant).
- **Suggested action: Fix (P2).** `result.water_atom_count // WATER_ATOMS_PER_MOLECULE` (import the constant).

---

### A2 — Hardcoded `// 4` in custom_molecule_panel.py (3 sites) — TRUE

- **Claim:** Three `water_count // 4` sites at `:1220, :1243, :1296`.
- **Actual code:** Confirmed at all three lines — `:1220` `water_nmolecules = water_count // 4`, `:1243` `water_nmolecules = water_count // 4`, `:1296` `water_nmolecules = water_count // 4` (each followed by `* WATER_VOLUME_NM3`).
- **Verdict: TRUE** (nit).
- **Suggested action: Fix (P2).** Same as A1, three sites.

---

### A3 — Hardcoded `4` in hydrate_generator molecule-index builder — TRUE

- **Claim:** `hydrate_generator.py:702` and `:782` use `i += 4` / `MoleculeIndex(i, 4, "water")`.
- **Actual code:**
  - `:699-703`: `if atom == "OW" and i + 3 < len(atom_names): next_atoms = atom_names[i:i+4]; if next_atoms[1]=="HW1" and ...=="HW2" and ...=="MW": molecule_index.append(MoleculeIndex(i, 4, "water")); i += 4`
  - `:778-782`: identical pattern (pattern-matching path).
- **Verdict: TRUE** (nit; correct for TIP4P hydrate water, but bypasses `WATER_ATOMS_PER_MOLECULE`).
- **Suggested action: Fix (P3).** Use `WATER_ATOMS_PER_MOLECULE` and a `("OW","HW1","HW2","MW")` tuple constant. Low risk (hydrate water fixed to TIP4P).

---

### A4 / TD1 — Duplicated water-atom constant in water_filler.py — TRUE (vuln-scan line-list partly wrong)

- **Claim (VulnScan A4):** `water_filler.py:133` defines `ATOMS_PER_WATER_MOLECULE = 4`, used at lines "363, 663, 672, 679".
- **Claim (CONCERNS TD1):** Same duplicate, used at "lines 663, 672". AGENTS.md mandates `WATER_ATOMS_PER_MOLECULE` from `types.py`.
- **Actual code:**
  - `water_filler.py:133`: `ATOMS_PER_WATER_MOLECULE = 4`
  - `types.py:22`: `WATER_ATOMS_PER_MOLECULE: int = 4` (canonical)
  - `water_filler.py` imports (lines 11–18): `math`, `lru_cache`, `Path`, `Optional`, `numpy`, `cell_utils`, `gro_parser` — **does NOT import `WATER_ATOMS_PER_MOLECULE`**.
  - `grep -n "ATOMS_PER_WATER_MOLECULE" water_filler.py` → exactly 3 lines: `133` (def), `663` (`atoms_per_molecule=ATOMS_PER_WATER_MOLECULE`), `672` (`n_atoms = n_molecules * ATOMS_PER_WATER_MOLECULE`).
  - What the vuln-scan's phantom lines actually contain: `:363` is a string literal inside `warnings.warn(...)` (`"Pass atoms_per_molecule explicitly to avoid ambiguity."`); `:679` is `all_atom_names = WATER_ATOM_NAMES_TEMPLATE * n_molecules` (a *different* constant).
- **Verdict: TRUE** (core finding — duplicate constant, single-source-of-truth violation). **The vuln-scan's line list is inaccurate**: only `:663` and `:672` use the constant; `:363` and `:679` are mis-attributed. **CONCERNS TD1's line list (663, 672) is accurate.**
- **Suggested action: Fix (P2).** Import `WATER_ATOMS_PER_MOLECULE` from `types.py` and delete the local duplicate.

---

### A5 — Hardcoded 3/4 ice-atom detection in vtk_utils.py — TRUE

- **Claim:** `vtk_utils.py:551`: `atoms_per_ice_mol = 4 if (has_ow_in_ice or has_mw_in_ice) else 3`.
- **Actual code** (`:548-551`):
  ```python
  has_ow_in_ice = "OW" in ice_region_atom_names
  has_mw_in_ice = "MW" in ice_region_atom_names
  atoms_per_ice_mol = 4 if (has_ow_in_ice or has_mw_in_ice) else 3
  ```
- **Verdict: TRUE** (nit; GUI render heuristic; `WATER_ATOMS_PER_MOLECULE` covers the 4 case, 3 is the GenIce default).
- **Suggested action: Fix (P3) — optional** (render-only path).

---

### P1 / PERF1 — O(n²) overlap-notice loop in place_custom — TRUE

- **Claim:** `custom_molecule_inserter.py:938-941` nested Python COM-COM loop, warning-only.
- **Actual code** (`:934-941`):
  ```python
  if n_molecules >= 2:
      com_arr = np.array(positions, dtype=np.float64)
      total_pairs = n_molecules * (n_molecules - 1) // 2
      n_close_pairs = 0
      for i in range(n_molecules):
          for j in range(i + 1, n_molecules):
              if np.linalg.norm(com_arr[i] - com_arr[j]) < self.config.min_separation:
                  n_close_pairs += 1
  ```
- **Traced impact:** Up to `MAX_CSV_ROWS=10000` → ~50M `np.linalg.norm` calls; warning-only (placement proceeds). Not a correctness bug.
- **Verdict: TRUE** (perf nit). Matches CONCERNS PERF1.
- **Suggested action: Fix (P3) — optional.** `scipy.spatial.cKDTree.query_pairs(r=min_separation)`.

---

### P2 — buffer_tree rebuilt on every successful placement — TRUE (deliberate)

- **Claim:** `solute_inserter.py:977` and `custom_molecule_inserter.py:717` rebuild `buffer_tree` per placement, not only on batch flush.
- **Actual code:**
  - `solute_inserter.py:974-984`: `recent_buffer.append(solute_positions); buffer_tree = cKDTree(np.vstack(recent_buffer))` on every placement; `if len(recent_buffer) >= _SOLUTE_BATCH_SIZE:` rebuilds `existing_tree` and resets buffer.
  - `custom_molecule_inserter.py:714-724`: same pattern with `_CUSTOM_BATCH_SIZE`.
- **Traced impact:** Buffer capped at 8 placements, so each rebuild is O(8·A·log(8A)) — bounded. The comment at `solute_inserter.py:975-976` states this is for "byte-identical" distance computation. The report itself notes this is a deliberate tradeoff and flags it only as a minor amortization opportunity; it also notes the ion inserter uses a direct `np.linalg.norm` scan (`ion_inserter.py:560-565`) instead — an inconsistency, not a bug.
- **Verdict: TRUE** (perf nit, **deliberate/intended** — not a regression).
- **Suggested action: No action** (optional alignment with the ion inserter's direct-scan pattern; would be a behavior-equivalence change requiring byte-identical re-validation).

---

### P3 — Per-molecule Python PBC-wrap loops in slab.py — TRUE

- **Claim:** `slab.py:407-419, 567-574, 668-680` are per-molecule Python loops, vectorizable.
- **Actual code:** Confirmed all three sites are `for mol_idx in range(n_molecules):` / `for mi in range(n_top):` loops computing COM-Z and shifting `±adjusted_box_z`. O(n) Python, not O(n²). `water_filler.tile_structure` has vectorized wrapping.
- **Verdict: TRUE** (perf nit, O(n)). Correctness OK (COM-based shift).
- **Suggested action: Fix (P3) — optional** vectorization.

---

### D1 — Dead/duplicated ion VDW radii in ion_inserter.py — TRUE

- **Claim:** `ion_inserter.py:34-35` `NA_VDW_RADIUS`/`CL_VDW_RADIUS` unused in the inserter; `ion_renderer.py:18-19` redefines its own copies.
- **Actual code:** `ion_inserter.py:34-35`: `NA_VDW_RADIUS = 0.190`, `CL_VDW_RADIUS = 0.181`. `grep` shows they are re-exported via `gui/__init__.py:10-11,29-30` but the actual consumer `gui/ion_renderer.py:18-19` *redefines* `NA_VDW_RADIUS = 0.190` / `CL_VDW_RADIUS = 0.181` and uses those at `:100,:155,:209,:219`. So within `ion_inserter.py` the constants are unused (only re-exported), and the renderer carries a duplicate.
- **Verdict: TRUE** (nit; dead-within-inserter + duplicate in renderer; desync risk if one is updated).
- **Suggested action: Fix (P3).** Have `ion_renderer.py` import from `ion_inserter.py` (or move to a shared constants module).

---

### D2 — Dead ion LJ constants in gromacs_ion_export.py — TRUE

- **Claim:** `gromacs_ion_export.py:30-33` `NA_SIGMA`/`CL_SIGMA`/`NA_EPSILON`/`CL_EPSILON` are never referenced.
- **Actual code:** `:30-33` define the four constants. `generate_ion_itp` (`:36-63`) writes only `NA_CHARGE`/`NA_ATOM_MASS`/`CL_CHARGE`/`CL_ATOM_MASS` (LJ params come from `[atomtypes]` in `_constants.ION_ATOMTYPES`). `grep -rn` confirms the four names appear **only** at `:30-33` — nowhere else in `quickice/`.
- **Verdict: TRUE** (dead code; duplicates `ION_ATOMTYPES` sigma/epsilon to rounding — no unit mismatch, just dead duplication).
- **Suggested action: Fix (P3).** Remove the four dead constants.

---

### TD2 — Exception-cause chain lost in hydrate_generator — TRUE (report typo)

- **Claim (CONCERNS):** `hydrate_generator.py:323` wraps as `raise RuntimeError(f"...{e}")` WITHOUT `from e`; siblings `generator.py:150` and `interface_builder.py:370` correctly preserve the cause (CONCERNS wrote "`from e from e`" for the latter).
- **Actual code:**
  - `hydrate_generator.py:323-326`: `except Exception as e: raise RuntimeError(f"GenIce2 failed to generate structure: {e}")` — **no `from e`**.
  - `generator.py:150-154`: `except Exception as e: raise StructureGenerationError(...) from e` — has `from e`.
  - `interface_builder.py:370-375`: `except Exception as e: raise InterfaceGenerationError(..., mode=config.mode) from e` — has **one** `from e` (line 375). CONCERNS' "`from e from e`" is a **reporting typo**; the code is correct.
- **Verdict: TRUE.** The inconsistency is real: `hydrate_generator.py:323` is the only one of the three GenIce-error wrappers missing `from e`. (The "from e from e" in CONCERNS is a typo about the sibling, not a code defect.)
- **Suggested action: Fix (P1).** Append `from e` to the `raise RuntimeError(...)` at `hydrate_generator.py:324`.

---

### TD3 — Large GUI "god-object" files — TRUE

- **Claim:** `main_window.py` (2318), `custom_molecule_panel.py` (1395), `export.py` (1138), `phase_diagram.py` (1132).
- **Actual code:** `wc -l` confirms **exactly** 2318 / 1395 / 1138 / 1132. All four exceed 1100 lines.
- **Verdict: TRUE** (tech debt / refactor target; not a bug).
- **Suggested action: No action (refactor target, not emergency).**

---

### KB — Known Bugs section (negative result) — TRUE (no active bugs)

- **Claim (CONCERNS):** "No actively-crashing bugs were found." Positive sub-claims: inserters return NEW structures (V-17), cKDTree conditional-rebuild rule correct, comb-rule=2 centralized, Moleculetype `_H`/`_L` suffixing correct.
- **Actual code (spot-checked):**
  - `solute_inserter._remove_overlapping_water` builds a fresh `InterfaceStructure` (`:528-555`), sets custom attrs on `new_interface` (not input), returns it; `removed_count==0` no-custom branch returns original (`:509`, documented safe). ✓
  - `ion_inserter`: `ion_tree = None` (`:524`); rebuilds only at `:574` inside the batch-full guard after successful placements; rejection `continue`s at `:547,:554,:565` skip the rebuild. ✓
  - `_write_top_defaults` (`_shared.py:65-83`) is the single source of truth; comment at `:80`: "nbfunc=1, comb-rule=2 — emitted byte-identically in ONE place". ✓
  - `MoleculetypeRegistry.register_hydrate_guest` → `{mol}_H` (`moleculetype_registry.py:46-58`). ✓
- **Verdict: TRUE** (the section's negative conclusion + positive confirmations are all accurate). Note: this section predates the C1 finding in the vuln scan — C1 is a genuine latent crash the Known Bugs section did not surface.
- **Suggested action: No action** (this is a "no bug" confirmation; but see C1 above for the one real crash the section missed).

---

### SEC1 — Path containment inconsistent CLI vs GUI — TRUE

- **Claim:** CLI validates `--output`, custom `.gro`/`.itp`, positions CSV stay inside cwd; GUI has no equivalent.
- **Actual code:**
  - CLI: `cli/pipeline.py:170-175` (`output_path.is_relative_to(cwd)` for `--output`), `:533-547` (custom gro/itp `is_relative_to(cwd)`). Confirmed.
  - GUI: `gui/custom_molecule_panel.py:591,607` use `QFileDialog.getOpenFileName` (custom gro/itp); `gui/export.py` uses `QFileDialog.getSaveFileName` at 9 sites. `grep` for `is_relative_to`/`resolve()` in those GUI files returns **nothing** — no containment checks.
- **Verdict: TRUE** (latent asymmetry; low risk for a local desktop tool as CONCERNS notes).
- **Suggested action: No action** (GUI hardening optional; only relevant if GUI exposed to untrusted input).

---

### SEC2 — Broad exception swallowing in CLI ITP export — TRUE

- **Claim:** `cli/itp_helpers.py:162, 196, 317, 482` catch `except Exception` and return `None`; `:234` is narrower.
- **Actual code:** `grep` confirms `except Exception as e:` at `:162, :196, :317, :482` and `except (OSError, ValueError) as e:` at `:234`. A malformed custom-guest ITP can be silently omitted from the export dir.
- **Verdict: TRUE** (low; best-effort staging).
- **Suggested action: Fix (P3) — optional.** Narrow to `(OSError, ValueError)` and surface a non-zero exit when a required ITP fails to stage.

---

### PERF2 — Per-molecule PBC wrapping loop — TRUE

- **Claim:** `water_filler.py:108-129` loops molecule-by-molecule, fractional conversion + matrix multiplies per molecule.
- **Actual code** (`:108-129`): `for mol_idx in range(n_molecules): ... mol_frac = mol @ inv_cell_T; com_frac = mol_frac.mean(axis=0); shift_frac = -np.floor(com_frac); mol_frac += shift_frac; wrapped[start:end] = mol_frac @ cell.T`. Confirmed per-iteration numpy dispatch.
- **Verdict: TRUE** (perf nit; vectorizable).
- **Suggested action: Fix (P3) — optional** vectorization (reshape to `(n, A, 3)`, batch `@ inv_cell_T`, `.mean(axis=1)`).

---

### F1 — Duck-typed runtime attributes on InterfaceStructure (CP-01) — TRUE (accepted, NOT a bug)

- **Claim:** Both CLI and GUI mutate a shared `InterfaceStructure` in place by setting runtime attrs not declared on the dataclass; CP-01 accepted.
- **Actual code:** `cli/pipeline.py:786-830` sets `interface.custom_molecule_positions`, `interface.custom_molecule_moleculetype`, `interface.solute_type`, `interface.solute_positions`, `interface.custom_molecule_count`, etc. directly on the interface object. Confirmed exactly as described.
- **Verdict: TRUE (description accurate).** Per **AGENTS.md §Cross-Tab Data Flow / CP-01**, this is an **accepted design decision — NOT a bug**.
- **Suggested action: No action** (do not "fix"; when adding a carried attribute, add it as a defaulted dataclass field AND set it in both propagation blocks).

---

### F2 — HydrateWorker subclasses QThread directly (accepted) — TRUE (NOT a bug)

- **Claim:** `gui/hydrate_worker.py:15` `class HydrateWorker(QThread)`; accepted, do not fix.
- **Actual code:** `hydrate_worker.py:15`: `class HydrateWorker(QThread):`. Confirmed.
- **Verdict: TRUE (description accurate).** Per **AGENTS.md**, this is **accepted — NOT a bug**.
- **Suggested action: No action.**

---

### F3 — Guest-type identification heuristic — TRUE (documented)

- **Claim:** `utils/molecule_utils.py:167-170` WARNING comment: heuristic assumes any C-starting molecule with O in window is THF (13 atoms); misidentifies CO2/methanol/acetone.
- **Actual code** (`:161-170`): `# --- HEURISTIC FALLBACK ---` + `# WARNING: The heuristic assumes any C-starting molecule with an O atom in the sample window is THF (13 atoms). This would misidentify CO2, methanol, acetone, etc. as THF.` The explicit-`guest_type` path (`:154-158`) short-circuits before the heuristic.
- **Verdict: TRUE** (fragile, but documented and accepted for the two supported guests CH4/THF).
- **Suggested action: No action** (update heuristic when adding a new guest; add a regression test).

---

### F4 — multi_molecule_writer lacks try/except cleanup (intentional) — TRUE

- **Claim:** `output/multi_molecule_writer.py:146-155` intentionally omits the cleanup block; NOTE forbids "fixing" it.
- **Actual code** (`:146-155`): `# NOTE: This writer INTENTIONALLY LACKS the try/except (OSError, ValueError) cleanup block ... DO NOT add try/except here "for consistency" — that would be a behavior change ... violating the byte-identical / behavior-identical contract.` Followed by `with open(filepath, 'w') as f:` (no try/except).
- **Verdict: TRUE** (intentional divergence; documented).
- **Suggested action: No action** (do not add try/except — coordinated behavior change only).

---

### F5 — Bare `assert` in custom-guest bridge — TRUE

- **Claim:** `custom_guest_bridge.py:346` `assert key not in sys.modules, ...` is stripped under `python -O`.
- **Actual code** (`:345-346`): `key = f"genice2.molecules.{guest_type}"` / `assert key not in sys.modules, f"{key} already registered (stale state?)"`. Confirmed bare `assert`.
- **Verdict: TRUE** (fragile under `-O`; same class as the CRIT-04 assert already converted to `raise` in `cli/pipeline.py:33-56`).
- **Suggested action: Fix (P2).** Replace with `if key in sys.modules: raise RuntimeError(f"{key} already registered (stale state?)")`.

---

### F6 — Broad `except Exception` in output orchestrator — TRUE

- **Claim:** `output/orchestrator.py:77, 105, 123` catch `except Exception`, log warning, continue → partial results silently.
- **Actual code:** `:77` (PDB write), `:105` (validation), `:123` (phase diagram) all `except Exception as e: logging.warning(...); continue/append partial`. Confirmed.
- **Verdict: TRUE** (fragile; best-effort batch exporter — candidates can be silently dropped).
- **Suggested action: No action** (acceptable for best-effort; callers should check `len(output_files)` vs expected count).

---

### SL1 — GRO atom-number wraparound at 100,000 — TRUE

- **Claim:** `multi_molecule_writer.py:143-144` warns at `n_atoms > 99999` but does not prevent the write.
- **Actual code** (`:143-144`): `if n_atoms > 99999: logger.warning(f"GRO format wraps atom numbers at 100,000 (have {n_atoms} atoms)")`. No hard cap.
- **Verdict: TRUE** (scaling limit; by design — warning only).
- **Suggested action: No action** (documented limit; use a larger-count format or split for very large systems).

---

### SL2 — Custom-positions CSV cap — TRUE

- **Claim:** `MAX_CSV_ROWS = 10000` at `cli/pipeline.py:21`, enforced at `:317-322`.
- **Actual code:** `cli/pipeline.py:21`: `MAX_CSV_ROWS = 10000`; `:317-319` rejects with `f"CSV file exceeds maximum row limit of {MAX_CSV_ROWS}..."`. Confirmed.
- **Verdict: TRUE** (scaling limit; by design).
- **Suggested action: No action.**

---

### DEP1 — GenIce2 (lazy, required, no fallback) — TRUE (descriptive)

- **Claim:** Entire source step depends on GenIce2, imported inside function bodies; no vendored fallback.
- **Actual code:** `hydrate_generator.py:78-81` and `:253-255` import `genice2.genice`, `genice2.formats`, `genice2.lattices`, `genice2.molecules.tip4p`, `genice2.plugin`, `genice2.valueparser` — all inside function bodies (lazy, per AGENTS.md). Confirmed.
- **Verdict: TRUE** (risk description accurate; this is a dependency-risk note, not a bug).
- **Suggested action: No action** (pin version in `environment.yml`, track upstream).

---

### DEP2 — scipy (cKDTree, Rotation, no fallback) — TRUE (descriptive)

- **Claim:** `ion_inserter.py:14`, `solute_inserter.py:15-16` require scipy; only `UnivariateSpline` has a fallback.
- **Actual code:** `ion_inserter.py:14`: `from scipy.spatial import cKDTree`; `solute_inserter.py:15-16`: `from scipy.spatial import cKDTree` + `from scipy.spatial.transform import Rotation` (top-level, hard imports). `phase_diagram.py:229` has `except ImportError: pass` (UnivariateSpline fallback). Confirmed.
- **Verdict: TRUE** (descriptive risk).
- **Suggested action: No action** (keep scipy as hard dependency).

---

### DEP3 — PySide6 / VTK (GUI-only, lazy, headless-fragile) — TRUE (descriptive)

- **Claim:** GUI tests need `QT_QPA_PLATFORM=offscreen`; `entry.py` uses `find_spec` to check PySide6 without importing.
- **Actual code:** `entry.py:12`: "_is_pyside6_available() uses importlib.util.find_spec, never import PySide6"; `:29`: "Uses importlib.util.find_spec to avoid triggering a Qt crash". Confirmed.
- **Verdict: TRUE** (descriptive risk).
- **Suggested action: No action** (mock/skip VTK tests in headless — already the stated approach).

---

### DEP4 — iapws (IAPWS97), phase-diagram only — TRUE

- **Claim:** `phase_diagram.py:946` imports `IAPWS97` in-function; `:953` `except Exception` swallows per-T failures.
- **Actual code:** `:946`: `from iapws import IAPWS97`; `:950-954`: `try: st = IAPWS97(T=T, x=0); lv_P.append(st.P) except Exception as e: logging.warning(...)`. Confirmed. (Also a separate `except Exception` at `:232` for the scipy spline fallback — soft-fail.)
- **Verdict: TRUE** (descriptive; optional dependency, soft-fail).
- **Suggested action: No action** (leave soft-fail).

---

### MCF1 — CLI custom-guest mixed cage occupancy deferred — TRUE (by design)

- **Claim:** `cli/pipeline.py:102-107` rejects non-built-in guests with "Custom-guest CLI support is deferred (use the GUI...)".
- **Actual code:** `cli/pipeline.py:105`: `f"THF. Custom-guest CLI support is deferred (use the GUI for "` (confirmed via grep).
- **Verdict: TRUE** (missing feature, deliberately deferred to GUI).
- **Suggested action: No action** (deferred; GUI already supports it via `cage_guest_assignments`).

---

### TCG1 — grompp validation skipped when gmx absent — TRUE

- **Claim:** `tests/conftest.py:24-27` `gmx_skipif` skips grompp tests when `gmx` not on PATH.
- **Actual code** (`conftest.py:18-27`): `_gmx_available()` via `shutil.which("gmx")`; `gmx_skipif = pytest.mark.skipif(not _gmx_available(), reason="GROMACS (gmx) not found on PATH")`. Confirmed.
- **Verdict: TRUE** (test coverage gap; by design — residual risk is semantic topology drift invisible without `gmx`).
- **Suggested action: No action** (mitigated by byte-equivalence + structural invariant tests; run gmx in CI where available).

---

### TCG2 — VTK / headless GUI rendering — TRUE

- **Claim:** VTK-dependent viewer paths need a display / `QT_QPA_PLATFORM=offscreen`; may crash in some headless envs.
- **Verdict: TRUE** (test gap; ROADMAP.md TEST-06 deferred). Plausible from the referenced test setup; not independently re-executed (READ-ONLY).
- **Suggested action: No action** (Low priority — GUI rendering, not physics).

---

### TCG3 — `python -O` / `PYTHONOPTIMIZE=1` path — TRUE

- **Claim:** No test suite runs the pipeline under `-O`; the remaining bare `assert` at `custom_guest_bridge.py:346` is untested optimized.
- **Verdict: TRUE** (test gap; relates to F5 — the only remaining load-bearing `assert`).
- **Suggested action: No action** once F5 is converted to a real `raise` (the assert would no longer be load-bearing).

---

### TCG4 — O(n²) custom-molecule overlap-warning perf test — TRUE

- **Claim:** No perf test for the `place_custom` pairwise loop up to 10,000 rows.
- **Verdict: TRUE** (test gap; relates to P1/PERF1).
- **Suggested action: No action** (Low priority; warning-only path).

---

## Confirmed Bugs to Fix (prioritized)

| Priority | Issue | File:line | Action |
|---|---|---|---|
| **P0** | — | — | (No P0: nothing is an active crash in the *normal* code path. C1 is the only crash and is edge-case-gated.) |
| **P1** | **C1** | `modes/piece.py:361` | Add `import logging` + `logger = logging.getLogger(__name__)`. Real `NameError` on the bounds-check branch. Trivial fix. |
| **P1** | **TD2** | `hydrate_generator.py:324` | Append `from e` to `raise RuntimeError(...)`. Trivial; restores cause chain for parity with siblings. |
| **P2** | **TD1 / A4** | `water_filler.py:133` | Import `WATER_ATOMS_PER_MOLECULE`, delete local duplicate (AGENTS.md rule). |
| **P2** | **A1 / A2** | `gui/main_window.py:1357`; `gui/custom_molecule_panel.py:1220,1243,1296` | Replace `// 4` with `// WATER_ATOMS_PER_MOLECULE` (import the constant). |
| **P2** | **F5** | `custom_guest_bridge.py:346` | Convert bare `assert` to `if ...: raise RuntimeError(...)` (robust under `-O`). |
| **P3** | **S1** | `modes/pocket.py:591-601` | Port `slab.py:704-722`'s fix verbatim for consistency / to close the latent edge case. **Not an active bug.** |
| **P3** | **A3** | `hydrate_generator.py:702,782` | Use `WATER_ATOMS_PER_MOLECULE` + a `("OW","HW1","HW2","MW")` tuple constant. |
| **P3** | **A5** | `gui/vtk_utils.py:551` | Optional: use `WATER_ATOMS_PER_MOLECULE` for the 4-case (render-only). |
| **P3** | **D1** | `ion_inserter.py:34-35` + `gui/ion_renderer.py:18-19` | Have the renderer import from the inserter (or shared module); drop the duplicate. |
| **P3** | **D2** | `gromacs_ion_export.py:30-33` | Remove the four dead LJ constants. |
| **P3** | **PERF1/P1, PERF2, P3** | various | Optional vectorization / `cKDTree.query_pairs` (perf nits; warning/O(n) paths). |
| **P3** | **SEC2** | `cli/itp_helpers.py:162,196,317,482` | Optional: narrow to `(OSError, ValueError)`, surface non-zero exit on required-ITP failure. |

---

## False Alarms

**None.** Every claim in both documents has at least a kernel of truth. No report flagged an accepted pattern as a bug. The two reports **correctly** identify the accepted patterns (duck-typing CP-01, `HydrateWorker` QThread, GUI broad `except`) as *fragile-but-accepted*, not as bugs — consistent with AGENTS.md. So there is nothing to re-investigate as a false alarm.

**Reporting inaccuracies (not false alarms, but the user should know the details were off):**
- **A4 line list (VulnScan):** "used at lines 363, 663, 672, 679" is **wrong** — only `:663` and `:672` use `ATOMS_PER_WATER_MOLECULE`. `:363` is a `warnings.warn` string literal; `:679` uses a different constant (`WATER_ATOM_NAMES_TEMPLATE`). CONCERNS TD1 got the lines right (663, 672). The *core* finding (duplicate constant) is TRUE in both.
- **TD2 sibling wording (CONCERNS):** "`interface_builder.py:370` ... `from e from e`" is a **reporting typo** — the actual code has exactly one `from e` (line 375). The inconsistency claim (hydrate_generator lacks `from e`) is TRUE.
- **S1 severity (VulnScan):** Medium is **overstated**. The staleness is real, but no active corruption is demonstrated in the normal single-guest path (pocket uses `filter_molecules=False`, so the slab.py filtering bug is moot; complete molecules make `len(guest_atom_names)` a clean multiple). Actual severity: **Low (latent/consistency)**. The report's own "SUSPICIOUS, needs runtime verification" hedge is accurate.

---

## Notes on Verification Method

- READ-ONLY: no tests were executed, no Python was run. All verdicts derive from reading the cited source lines and tracing control/data flow statically.
- Known Bugs section's positive sub-claims (V-17 new-structure return, cKDTree conditional rebuild, comb-rule=2 centralization, MoleculetypeRegistry) were each spot-checked and confirmed correct — these are the AGENTS.md-mandated invariants and they hold.
- The one real crash (C1) was *not* surfaced by CONCERNS' "Known Bugs" section (which says "No actively-crashing bugs were found"); it was found only by the vuln scan. C1 is the highest-priority confirmed defect.
- S1's runtime impact could only be fully resolved by executing a pocket-mode hydrate generation where cavity removal leaves a non-multiple tile count *and* the candidate has a truncated atom-name tail. Static analysis shows this requires malformed input; well-formed GenIce2 output does not trigger it.
