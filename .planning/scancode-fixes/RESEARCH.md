# Scancode Issues Verification (RESEARCH)

**Date:** 2026-07-16
**Method:** Read-only verification against current source. No code modified.
**Scope:** CRIT-01..05, PERF-01..06, UNIT-01..05, SAFE-01..07, SUSP-01..06, TD (FRAG-03/TD-01/TD-ADHOC/TD-07/TD-CONST/VTK-DUP), a sample of doc issues, and packaging report D.

## Verification Summary Table

| ID | Severity | Verdict | File:line | Notes |
|----|----------|---------|-----------|-------|
| CRIT-01 | HIGH | CONFIRMED | gromacs_writer.py:308,352 | Triclinic wrap diagonal-only modulo; triggers on hydrate export of sH/c0te/c1te; slab interfaces unaffected |
| CRIT-02 | HIGH | CONFIRMED | ion_inserter.py:458 | Na/Cl alternation uses enumerate index `i`, not placement counter; charge-neutral trim present at :488-510 |
| CRIT-03 | MEDIUM | PARTIAL (dead code) | pdb_writer.py:141 | Hardcoded `i//3` is a real bug, but `write_interface_pdb_file` has ZERO callers (not exported) |
| CRIT-04 | MEDIUM | CONFIRMED | pipeline.py:901 | `assert` for runtime validation (stripped by `python -O`) |
| CRIT-05 | LOW | PARTIAL (dead code) | pdb_writer.py:101,150,168 | `atom_name[0]` → MW→"M" is a real latent bug, but MW only appears in dead `write_interface_pdb_file`; reachable `write_pdb_with_cryst1` sees only O/H |
| PERF-01 | MEDIUM | CONFIRMED | ion_inserter.py:456 | cKDTree rebuilt per ion placement (O(k² log k)) |
| PERF-02 | MEDIUM | CONFIRMED | solute_inserter.py:909-910 | vstack + cKDTree rebuild per placement |
| PERF-03 | MEDIUM | CONFIRMED | custom_molecule_inserter.py:659-660 | Same vstack+rebuild pattern |
| PERF-04 | LOW | CONFIRMED | solute_inserter.py:412-416, custom:367-371 | Per-atom Python KDTree query (batchable) |
| PERF-05 | LOW | CONFIRMED (accepted) | gromacs_writer.py:900+ | Per-atom string formatting; comment at :892-898 explicitly accepts I/O-bound tradeoff |
| PERF-06 | LOW | CONFIRMED | solute_inserter.py:556-562 | Python-loop water-removal assembly |
| UNIT-01 | MEDIUM | CONFIRMED (by-design) | pdb_writer.py:77 vs gromacs_writer.py:856 | PDB 3N atoms, GRO 4N (MW added); PDB is visualization format |
| UNIT-02 | LOW | CONFIRMED | gromacs_writer.py:980-991 | Charges/settle/alpha hardcoded inline; LJ params ARE constants |
| UNIT-03 | LOW | CONFIRMED | gromacs_writer.py:52,386 | `TIP4P_ICE_ALPHA=0.13458335` defined twice; :991 also hardcodes inline |
| UNIT-04 | LOW | CONFIRMED | solute_inserter.py:166 | `r_ch = 0.109620` hardcoded CH4 C-H bond |
| UNIT-05 | LOW | CONFIRMED | gromacs_ion_export.py:19-20 | Ion charges ±0.85 not shared with gromacs_writer.py:91-92 (charge=0.0) |
| SAFE-01 | MEDIUM | CONFIRMED | main_window.py:935 | `insert_ions` on main thread, no worker (unlike HydrateWorker) |
| SAFE-02 | MEDIUM | FALSE ALARM | main_window.py:756 | Button IS disabled at :756 before `worker.start()` (:767); re-enabled in complete/error handlers |
| SAFE-03 | LOW | CONFIRMED (compliant) | interface_builder.py:370-374 | Broad `except Exception` re-raises with `from e`; AGENTS.md only bars bare-except in pipeline.py |
| SAFE-04 | LOW | CONFIRMED (by-design) | gromacs_writer.py:915 | GRO 3-decimal (`%8.3f`) precision |
| SAFE-05 | LOW | CONFIRMED | pipeline.py:137 | `--output` has no path-traversal check; inputs at :243-249,:495-509 DO check |
| SAFE-06 | NONE | CONFIRMED SAFE | — | No `shell=True`/`os.system`/`os.popen` in quickice/ |
| SAFE-07 | LOW | CONFIRMED | main_window.py:924 | `if concentration <= 0` no NaN check; NaN passes → crash in `round()` |
| SUSP-01 | MEDIUM | CONFIRMED | ion_inserter.py:103 | Fallback `// WATER_ATOMS_PER_MOLECULE(4)` wrong for 3-atom GenIce ice; requires ice_nmolecules==0 AND interface_structure None |
| SUSP-02 | LOW | PARTIAL | gromacs_writer.py:1462-1484 | Detection ORDER is actually CORRECT (CO2→THF→CH4→H2→Me); real concern is heuristic fragility for unknown C+H guests (bypassed via custom_guest_info) |
| SUSP-03 | LOW | CONFIRMED (fragile) | hydrate_generator.py:390-399 | Box-line loop confusing/inverted; works via fallback `box_line = lines[-1]` |
| SUSP-04 | LOW | CONFIRMED | gromacs_writer.py:456-462 | Returns canonical names not reordered input; limited risk (built-in ch4/thf match ITP) |
| SUSP-05 | LOW | CONFIRMED | gromacs_writer.py:359-364 | Unwrap shift only single box-length; low impact for typical systems |
| SUSP-06 | MEDIUM | CONFIRMED | custom_molecule_inserter.py:796-813 | `place_custom` no overlap check, no warning |
| FRAG-03 | TECH-DEBT | CONFIRMED | gromacs_writer.py | Exactly 4067 lines (`wc -l`) |
| TD-01 | TECH-DEBT | CONFIRMED | gromacs_writer.py:833,1044,1688,2044,2803,3336 | 6 near-identical GRO writer functions at cited lines |
| TD-ADHOC | TECH-DEBT | CONFIRMED | gromacs_writer.py:2133,2144,3415,3422,3448,3464,3474 | 7 instances of `type('obj',(object,),{...})()` |
| TD-07 | TECH-DEBT | CONFIRMED | molecule_validator.py:185 | Upload validation checks atomtypes PRESENCE only, not CONFLICT with built-in types |
| TD-CONST | TECH-DEBT | CONFIRMED | ion_inserter.py:29 | AVOGADRO defined once; 4 importers: solute_inserter:28, custom_molecule_inserter:28, pipeline.py:15, scorer.py:18 |
| VTK-DUP | TECH-DEBT | CONFIRMED | 6 viewer files | `_VTK_AVAILABLE=False` copy-paste in: custom_molecule_viewer, hydrate_viewer, interface_panel, ion_viewer, solute_viewer, view.py |
| CLI #1 | DOC | CONFIRMED | docs/cli-reference.md:149 | Says exit code 1; pipeline.py:155 returns 0 |
| CLI #2 | DOC | CONFIRMED | README.md:229 | Order "SOL→guests→solutes→custom→ions"; code is SOL→guest→custom→solute→NA→CL (solute/custom swapped) |
| CLI #3 | DOC | CONFIRMED (scan path wrong) | main.py:139 vs cli/itp_helpers.py:314 | main.py uses underscore `tip4p_ice.itp`; itp_helpers uses hyphen `tip4p-ice.itp`. NOTE: scan cited `structure_generation/itp_helpers.py` — actual path is `cli/itp_helpers.py` |
| CLI I1 | DOC | CONFIRMED | types.py:32-38 | Labels reversed: "For TIP4P-ICE specifically" is on TIP4P/2005 paper (DOI 10.1063/1.2121600); AGENTS.md attributes 10.1063/1.1931662 to TIP4P-ICE |
| GUI MISS-1 | DOC | CONFIRMED | interface_panel.py:258 | "Hydrate Structure" source option exists; docs/gui-guide.md has no mention |
| GUI MISS-2 | DOC | CONFIRMED | main_window.py:2139 | Sets `__GLX_VENDOR_LIBRARY_NAME=mesa`; docs/gui-guide.md has no mention |
| GUI CITE-3 | DOC | FALSE ALARM (discrepancy) | README.md:383,387 | Both lines say `10.1063/1.5121392` (internally consistent); no `.1394` anywhere in repo |
| CLI #4-12, M1-M5, GUI INC-2/3/4, CITE-1/2/4/5/6, HEAD-* | DOC | DOC-ONLY (not code-verified) | — | Not deep-verified in this pass; low risk |
| PACKAGING spec | — | CONFIRMED | quickice-gui.spec | strip=False (EXE:41 + COLLECT:55); collect_all=9 pkgs (:9); excludes=6 (:27); optimize=0 (:29); one-dir COLLECT (:51); upx=True (bonus) |
| PACKAGING tkinter | — | CONFIRMED (none) | — | No `import tkinter`/`from tkinter` in quickice/ |
| PACKAGING scipy | — | PARTIAL | — | cKDTree + Rotation confirmed, BUT scan missed `scipy.interpolate.UnivariateSpline` (phase_diagram.py:223) |

## Detailed Verifications

### CRIT-01: Triclinic PBC wrap uses diagonal-only modulo
- **Claim:** `wrap_positions_into_box`/`wrap_molecules_into_box` wrap by diagonal cell elements only → corrupts triclinic hydrate exports.
- **Verdict:** CONFIRMED
- **Evidence:**
  - `gromacs_writer.py:308`: `wrapped[:, dim] = np.mod(wrapped[:, dim], cell[dim, dim])` — diagonal-only per-axis modulo.
  - `gromacs_writer.py:352`: `box_sizes = np.array([cell[d, d] for d in range(3)])` — diagonal-only.
  - Correct reference exists: `water_filler.py:106` `inv_cell_T = np.linalg.inv(cell.T)` then fractional wrap (`:117 mol_frac = mol @ inv_cell_T`, `:127 wrapped = mol_frac @ cell.T`).
  - `types.py` HYDRATE_LATTICES: sH (`:119`), c0te (`:131`), c1te (`:142`) are `is_triclinic: True`.
  - Reachability: `pipeline.py:928` `write_interface_gro_file(wrapper, gro_path, ...)` passes `cell=hydrate.cell` (triclinic for sH/c0te/c1te, parsed at `hydrate_generator.py:414-430` from 9-value box line). `write_interface_gro_file:1131-1136` calls `wrap_molecules_into_box(iface.positions, iface.molecule_index, iface.cell)`.
- **True scope:** Direct hydrate export of triclinic lattices (sH, c0te, c1te). Slab-mode interfaces force orthogonal cells (`slab.py:619` `cell = np.diag([adjusted_box_x, adjusted_box_y, adjusted_box_z])`) → diagonal-only wrap is CORRECT for them, so interface exports are unaffected. Hydrate positions are intentionally NOT wrapped in hydrate_generator (`:186-189`), so first wrap happens at export — here.
- **Fix complexity:** M — route triclinic cells through fractional wrap; reuse `water_filler.wrap_positions_triclinic` or add triclinic branch in `wrap_molecules_into_box`. Needs test on a real sH export.

### CRIT-02: Na+/Cl- alternation uses selection-list index `i`
- **Claim:** Alternation `if i % 2 == 0` uses enumerate index; `continue` on overlap skips placement but increments `i` → clustered ions.
- **Verdict:** CONFIRMED
- **Evidence:**
  - `ion_inserter.py:431` `for i, water_idx in enumerate(selected):`.
  - `:444` `continue` (too close to existing atoms); `:451` `continue` (too close to other ions).
  - `:458` `if i % 2 == 0:` — uses `i` (enumerate index), not a placement counter. After a skip, parity no longer reflects placement order.
  - Charge-neutrality trim present at `:488-510` (removes excess Na+/Cl-), so NET charge is always zero; only SPATIAL alternation is wrong.
- **True scope:** Any ion insertion where ≥1 candidate is rejected for overlap (common for realistic concentrations in confined geometry). Produces same-type clustering, not charge imbalance.
- **Fix complexity:** S — add a `placed_count` counter, increment only on successful placement, use `placed_count % 2` for parity.

### CRIT-03: PDB writer hardcodes 3 atoms/ice
- **Claim:** `residue_num = (i // 3) + 1` breaks for 4-atom hydrate ice.
- **Verdict:** PARTIAL (bug in dead code)
- **Evidence:**
  - `pdb_writer.py:141` `residue_num = (i // 3) + 1` — hardcoded 3 (water loop at `:160` uses `i // 4`). The gromacs writer DOES detect dynamically: `gromacs_writer.py:1178-1180` `has_ow_in_ice = "OW" in ice_region_atom_names; atoms_per_ice_mol = 4 if has_ow_in_ice else 3`.
  - **`write_interface_pdb_file` is DEAD CODE:** grep across `quickice/` and `tests/` found ZERO callers (only the definition at `pdb_writer.py:113`). It is NOT exported in `output/__init__.py` (only `write_pdb_with_cryst1` and `write_ranked_candidates` are). `orchestrator.py:11` and `gui/export.py:19` import only `write_pdb_with_cryst1`.
- **True scope:** The bug is real but UNREACHABLE in current code. No production path calls `write_interface_pdb_file`.
- **Fix complexity:** S — either delete the dead function OR fix the hardcoded `3` (mirror gromacs detection) AND wire it up. Recommend deciding intent first (delete vs. wire).

### CRIT-04: `assert` for runtime validation
- **Claim:** `assert` stripped by `python -O`.
- **Verdict:** CONFIRMED
- **Evidence:** `pipeline.py:901` `assert water_atom_count + guest_atom_count == len(hydrate.positions), \ ...` — it is an `assert` (not `if...raise`). Note: distinct from AGENTS.md's "no bare except Exception" rule (which is about except, not assert).
- **True scope:** Hydrate export when `python -O` or `PYTHONOPTIMIZE=1`. Check silently skipped → corrupted wrapper could propagate to GRO/TOP writers.
- **Fix complexity:** S — replace with `if ... != ...: raise ValueError(...)`.

### CRIT-05: PDB element from `atom_name[0]` → MW→"M"
- **Claim:** `element = atom_name[0]` yields "M" for MW (invalid element).
- **Verdict:** PARTIAL (latent bug; trigger in dead code)
- **Evidence:**
  - `pdb_writer.py:101,150,168` all use `element = atom_name[0] if atom_name else ""`. For "MW" → "M" (no element "M").
  - Line 101 is in `write_pdb_with_cryst1` (REACHABLE: orchestrator.py:75, gui/export.py:662). But Candidate structures are ice-only with atom_names ["O","H","H",...] (no MW) → `atom_name[0]` yields "O"/"H" (correct). MW is never present.
  - Lines 150, 168 are in `write_interface_pdb_file` (DEAD CODE — see CRIT-03). Only there do MW atoms appear.
- **True scope:** The naive extraction is a real latent bug, but the MW→"M" trigger exists only in dead code. Reachable `write_pdb_with_cryst1` only sees correct single-char atoms (O/H).
- **Fix complexity:** S — add an atom-name→element map (at least MW→""). Couple with CRIT-03 decision (fix+wire the dead function, or delete it).

### PERF-01..06: Performance concerns
- **PERF-01 (CONFIRMED):** `ion_inserter.py:456` `ion_tree = cKDTree(np.array(ion_positions))` inside the placement block — rebuild per successful placement. Fix complexity M (incremental index or batch validation).
- **PERF-02 (CONFIRMED):** `solute_inserter.py:909-910` `combined_tree_data = np.vstack([combined_tree_data, solute_positions]); existing_tree = cKDTree(combined_tree_data)` per placement. Fix complexity M (pre-allocate, batch rebuild).
- **PERF-03 (CONFIRMED):** `custom_molecule_inserter.py:659-660` identical pattern. Fix complexity M.
- **PERF-04 (CONFIRMED):** `solute_inserter.py:412-416` and `custom_molecule_inserter.py:367-371` per-atom Python loop `for atom_pos in solute_positions: existing_tree.query(atom_pos, k=1)`. cKDTree supports batch `query(solute_positions, k=1)`. Fix complexity S.
- **PERF-05 (CONFIRMED, accepted):** `gromacs_writer.py:900+` per-atom `lines.append(f"...")`. Comment at `:892-898` explicitly states it is I/O-bound and kept for clarity. Low priority / accepted tradeoff.
- **PERF-06 (CONFIRMED):** `solute_inserter.py:556-562` Python loop `for mol_idx in water_molecules_to_keep: kept_water_positions.append(...)`. The `mol_overlaps` mask is already computed — could use boolean masking. Fix complexity S.

### UNIT-01..05: Unit / atom-number mismatches
- **UNIT-01 (CONFIRMED, by-design):** `pdb_writer.py:77` `atoms_per_water = len(positions) // candidate.nmolecules` (=3 for Candidate) vs `gromacs_writer.py:856` `n_atoms = nmol * 4` (MW added). PDB is visualization format (no MW); GRO adds MW for simulation. Intentional inconsistency. Low priority.
- **UNIT-02 (CONFIRMED):** `gromacs_writer.py:980-983` hardcodes charges (`HW_ice: 0.5897`, `MW: -1.1794`); `:987` settle `0.09572 0.15139`; `:991` alpha `0.13458335` inline. LJ sigma/epsilon ARE module constants (`:56-57`). Fix complexity S.
- **UNIT-03 (CONFIRMED):** `TIP4P_ICE_ALPHA = 0.13458335` at `:52` AND `:386` (same value); `:991` also hardcodes inline. Dead first definition. Fix complexity S.
- **UNIT-04 (CONFIRMED):** `solute_inserter.py:166` `r_ch = 0.109620` (CH4 C-H, comment "from ch4.itp"). Fix complexity S.
- **UNIT-05 (CONFIRMED):** `gromacs_ion_export.py:19-20` `NA_CHARGE=0.85`, `CL_CHARGE=-0.85`; `gromacs_writer.py:91-92` `ION_ATOMTYPES` charge=0.0. Not shared/imported. Fix complexity S (single source of truth).

### SAFE-01..07: Safety / robustness
- **SAFE-01 (CONFIRMED):** `main_window.py:935` `ion_structure = insert_ions(interface, concentration, volume_arg)` — synchronous on main thread, no worker. Contrast `HydrateWorker` at `:759`. Fix complexity M (create `IonInsertionWorker`).
- **SAFE-02 (FALSE ALARM):** Scan claimed button "NOT disabled at the START". FALSE — `main_window.py:756` `self.hydrate_panel.generate_button.setEnabled(False)` runs BEFORE `HydrateWorker(config)` (`:759`) and `start()` (`:767`); re-enabled in `_on_hydrate_generation_complete` (`:802`) and `_on_hydrate_generation_error` (`:821`). Residual (not the claim): if the worker thread crashes without emitting a signal, the button stays disabled — a narrower stuck-button concern, not the concurrent-worker race claimed.
- **SAFE-03 (CONFIRMED, compliant):** `interface_builder.py:370-374` `except Exception as e: raise InterfaceGenerationError(...) from e`. `InterfaceGenerationError` re-raised as-is at `:367-369`. `from e` preserves traceback. AGENTS.md bars bare-except only in `cli/pipeline.py`, so this is compliant. Fragility, not violation. Low priority.
- **SAFE-04 (CONFIRMED, by-design):** `gromacs_writer.py:915` `{o_pos[0]:8.3f}` — 3-decimal (0.001 nm). GROMACS supports higher precision; low impact (grompp recomputes settles/vsites). Low priority.
- **SAFE-05 (CONFIRMED):** `pipeline.py:137` `output_path = Path(self.args.output).resolve(); output_path.mkdir(parents=True, exist_ok=True)` — NO `is_relative_to(cwd)` check. Inputs DO check: `:243-249` (CSV), `:495-509` (GRO/ITP). `output/orchestrator.py:48-56` DOES check output dir. Inconsistent. Fix complexity S.
- **SAFE-06 (CONFIRMED SAFE):** No `shell=True`/`os.system`/`os.popen` in `quickice/`. GenIce2 via Python API.
- **SAFE-07 (CONFIRMED):** `main_window.py:924` `if concentration <= 0` — NaN comparisons return False, so NaN passes. `int(round(float('nan')))` raises ValueError → unhelpful crash. No bad structure. Fix complexity S (add `math.isnan`/`math.isinf` check).

### SUSP-01..06: Suspicious code
- **SUSP-01 (CONFIRMED):** `ion_inserter.py:103` fallback `ice_mols = ice_atom_count // WATER_ATOMS_PER_MOLECULE` (4) — wrong for 3-atom GenIce ice (300 atoms → 75 mols instead of 100). Requires `ice_nmolecules==0` AND `interface_structure is None` (both fallbacks fail). Low trigger probability but silently incorrect. Fix complexity S.
- **SUSP-02 (PARTIAL):** `gromacs_writer.py:1462-1484` — detection ORDER is actually CORRECT: CO2 (`:1464`, requires no H) → THF (`:1469`, has O+carbon) → CH4 (`:1473`) → H2 (`:1477`) → Me (`:1481`). The scan's "order-dependent" framing is misleading; the order is right. Real concern: heuristic fails for unknown C+H molecules (e.g., ethane → "ch4"), but custom guests bypass via `custom_guest_info` metadata. Low priority.
- **SUSP-03 (CONFIRMED, fragile):** `hydrate_generator.py:390-399` loop: skips lines where `line.strip() and not line[0].isdigit()` (i.e., skips lines whose first char is NOT a digit), takes first non-skipped line. For standard GRO (leading-space box line), the box line is skipped too, then fallback `if box_line is None: box_line = lines[-1]` (`:398-399`) saves it (last line is always box line). Works via fallback; fragile if GenIce2 appends trailing comments. Fix complexity S.
- **SUSP-04 (CONFIRMED):** `gromacs_writer.py:456-462` `return list(canonical), reorder` — returns canonical names (e.g., `["C","H","H","H","H"]`), not reordered input. Comment explains intent. Limited risk (built-in ch4/thf ITPs match canonical names; custom guests skip this). Low priority.
- **SUSP-05 (CONFIRMED):** `gromacs_writer.py:359-364` unwrap `shifts[mask_ahead] -= box_sizes[...]` handles only single box-length shifts. Fine for water (0.28 nm in 2+ nm box); fails for molecules > half box. Low impact. Low priority.
- **SUSP-06 (CONFIRMED):** `custom_molecule_inserter.py:796-813` `place_custom` docstring "No overlap checking (user responsibility)" — no warning emitted when molecules overlap. Fix complexity S (log a warning).

### Tech Debt
- **FRAG-03 (CONFIRMED):** `gromacs_writer.py` = exactly 4067 lines (`wc -l`). Fix complexity L (major refactor — split into per-structure modules). **NEEDS USER APPROVAL (L).**
- **TD-01 (CONFIRMED):** 6 GRO writer functions: `write_gro_file`(:833), `write_interface_gro_file`(:1044), `write_multi_molecule_gro_file`(:1688), `write_ion_gro_file`(:2044), `write_custom_molecule_gro_file`(:2803), `write_solute_gro_file`(:3336). Fix complexity L (extract shared helpers). **NEEDS USER APPROVAL (L).**
- **TD-ADHOC (CONFIRMED):** 7 instances of `type('obj',(object,),{...})()` at `:2133,:2144,:3415,:3422,:3448,:3464,:3474`. Fix complexity M (replace with `MoleculeIndex`/dataclass).
- **TD-07 (CONFIRMED):** `molecule_validator.py:185` `if not itp_info.has_atomtypes_section` — upload-time validation checks atomtypes PRESENCE only, NOT whether user atomtypes CONFLICT with built-in TIP4P-ICE/GAFF2 types (e.g., redefining `OW_ice`). Conflict only caught at `gmx grompp`. Fix complexity M (add atomtype-overlap check in `validate_custom_molecule`).
- **TD-CONST (CONFIRMED):** `AVOGADRO = 6.02214076e23` at `ion_inserter.py:29`; imported by `solute_inserter.py:28`, `custom_molecule_inserter.py:28`, `cli/pipeline.py:15`, `ranking/scorer.py:18` (4 importers). Fix complexity S (move to `types.py`/`constants.py`).
- **VTK-DUP (CONFIRMED):** `_VTK_AVAILABLE = False` copy-paste detection in 6 files: `custom_molecule_viewer.py`, `hydrate_viewer.py`, `interface_panel.py`, `ion_viewer.py`, `solute_viewer.py`, `view.py`. Fix complexity M (shared `vtk_utils` helper).

### Documentation (verified sample)
- **CLI #1 (CONFIRMED):** `docs/cli-reference.md:149` "the pipeline exits with code 1" for `--no-overwrite`. But `pipeline.py:155` `return 0` (success) when skipping. Doc is wrong. Fix S.
- **CLI #2 (CONFIRMED):** `README.md:229` "Order: SOL → hydrate guests → solutes → custom molecules → ions". Actual code (`gromacs_writer.py:2776-2800`): SOL, guest, custom, solute, NA, CL. README swaps "solutes" and "custom molecules"; the README example block (`:222-226`) also shows THF_L (solute) before CUSTOM_MOL_1 — matches prose, not code. Fix S.
- **CLI #3 (CONFIRMED; scan path wrong):** `main.py:139` `itp_filename = "tip4p_ice.itp"` (underscore) vs `cli/itp_helpers.py:314` `tip4p_dest = output_dir / "tip4p-ice.itp"` (hyphen). Actual data file is `tip4p-ice.itp` (hyphen, confirmed in `quickice/data/`). NOTE: scan cited `structure_generation/itp_helpers.py` — the real path is `cli/itp_helpers.py` (line numbers 311-316 were correct). Fix S.
- **CLI I1 (CONFIRMED):** `types.py:32-38`. Line 36 labels the second citation "For TIP4P-ICE specifically:" but attaches it to "A general purpose model for the condensed phases of water: TIP4P/2005" (DOI 10.1063/1.2121600) — which self-identifies as TIP4P/2005. AGENTS.md attributes DOI 10.1063/1.1931662 (the first citation, `:32-34`) to TIP4P-ICE. So the TIP4P/Ice vs TIP4P/2005 labels are reversed. (Verification per in-repo AGENTS.md + self-identifying paper title; web not fetched per instructions.) Fix S.
- **GUI MISS-1 (CONFIRMED):** `interface_panel.py:258` `self.source_combo.addItems(["Ice Candidate", "Hydrate Structure"])` — "Hydrate Structure" option exists. `docs/gui-guide.md` has no "Hydrate Structure" mention (grep returned none). Doc gap. Fix S.
- **GUI MISS-2 (CONFIRMED):** `main_window.py:2139` `os.environ['__GLX_VENDOR_LIBRARY_NAME'] = 'mesa'` in `_configure_opengl_for_remote()`. `docs/gui-guide.md` has no GLX/mesa mention (grep returned none). Doc gap. Fix S.
- **GUI CITE-3 (FALSE ALARM on discrepancy):** `README.md:383` "DOI: https://doi.org/10.1063/1.5121392" and `:387` "DOI: 10.1063/1.5121392" — BOTH use `.1392` (internally consistent). Grep found NO `.1394` anywhere in the repo. The ".1392 vs .1394 discrepancy claim" is unsupported by the file. (Whether `.1392` is the correct DOI is out of scope for read-only verification; web not fetched per AGENTS.md.)
- **Other doc issues (DOC-ONLY, not code-verified in this pass):** CLI #4-#12, M1-M5, GUI INC-2/3/4, CITE-1/2/4/5/6, HEAD-1..6 — low risk, not deep-verified.

### Packaging (report D — spec file facts, NOT built)
- **Spec facts CONFIRMED:** `quickice-gui.spec` — `strip=False` in EXE (`:41`) AND COLLECT (`:55`); `collect_all` list of 9 packages (`:9`: iapws, genice2, genice_core, matplotlib, scipy, numpy, shapely, networkx, spglib); `excludes` list of 6 patterns (`:27`: `*/tests/*`,`*/test/*`,`*/docs/*`,`*/__pycache__/*`,`*/.pytest_cache/*`,`*/egg-info/*`); `optimize=0` (`:29`); one-dir via COLLECT (`:51`, `exclude_binaries=True` at `:37`). Bonus: `upx=True` (`:42,:56`).
- **No tkinter CONFIRMED:** grep for `import tkinter`/`from tkinter` in `quickice/` returned nothing.
- **scipy usage PARTIAL:** cKDTree confirmed (7 files: vtk_utils, validator, scorer, custom_molecule_inserter, ion_inserter, overlap_resolver, solute_inserter) and `scipy.spatial.transform.Rotation` confirmed (custom_molecule_inserter, solute_inserter). **BUT scan missed `scipy.interpolate.UnivariateSpline`** at `output/phase_diagram.py:223`. The "only cKDTree and Rotation" claim is incomplete.

## Aggregate Findings

- **31 TRUE POSITIVE (CONFIRMED)** — CRIT-01, CRIT-02, CRIT-04; PERF-01..06; UNIT-01..05; SAFE-01, SAFE-03, SAFE-04, SAFE-05, SAFE-06, SAFE-07; SUSP-01, SUSP-03, SUSP-04, SUSP-05, SUSP-06; FRAG-03, TD-01, TD-ADHOC, TD-07, TD-CONST, VTK-DUP; CLI #1, CLI #2, CLI #3, CLI I1; GUI MISS-1, GUI MISS-2; packaging spec facts.
- **6 PARTIAL** — CRIT-03 (dead code), CRIT-05 (dead-code trigger), SUSP-02 (order correct, heuristic fragile), GUI CITE-3 (no internal discrepancy), packaging scipy (scan missed UnivariateSpline), CLI #3 (content confirmed but scan's file path was wrong).
- **1 FALSE ALARM** — SAFE-02 (button IS disabled at line 756).
- **0 ALREADY FIXED / STALE** (all cited code present as described, modulo the dead-code nuance).
- **DOC-ONLY (not code-verified):** CLI #4-#12, M1-M5, GUI INC-2/3/4, CITE-1/2/4/5/6, HEAD-1..6.

### Issues requiring MAJOR codebase change (L — need user approval)
- **FRAG-03** — split the 4067-line `gromacs_writer.py` monolith into per-structure modules.
- **TD-01** — deduplicate the 6 near-identical GRO writer functions (extract shared helpers).

### Low-priority issues (recommend user approval before acting, per instructions)
- **CRIT-03, CRIT-05** — bugs live in DEAD code (`write_interface_pdb_file`); decide delete-vs-wire before fixing.
- **PERF-05** — explicitly accepted I/O-bound tradeoff (comment at :892-898).
- **SAFE-04** — GRO 3-decimal precision is by-design (grompp recomputes).
- **UNIT-01** — PDB-vs-GRO atom-count difference is by-design (PDB=visualization, no MW).
- **SAFE-03** — broad `except` is compliant with AGENTS.md (not in pipeline.py); fragility only.
- **SUSP-02, SUSP-04, SUSP-05** — low-impact edge cases (custom guests bypass the heuristic; typical systems unaffected).
- **GUI CITE-3** — no internal discrepancy exists; only a "is .1392 the correct DOI" question (web verification out of scope).

### Notable cross-cutting finding
**`write_interface_pdb_file` (pdb_writer.py:113) is entirely DEAD CODE** — defined but never called, not exported in `output/__init__.py`, imported nowhere in `quickice/` or `tests/`. This simultaneously downgrades CRIT-03 and CRIT-05 from "active bugs" to "latent bugs in dead code." Any fix decision should first resolve whether the interface-PDB export path is intended to exist (wire it up + fix bugs) or be removed (delete the function). The reachable PDB path is `write_pdb_with_cryst1` (Candidate ice-only, 3-atom O/H), which is correct for its inputs.

## Sources

All findings verified by direct read of current source at the cited file:line (read-only; no code executed). Cross-references:
- `AGENTS.md` (repo constraints / accepted design / TIP4P-ICE DOI authority).
- `.planning/codebase/CONCERNS.md` (TD-01/07/ADHOC/CONST/FRAG-03 definitions).
- `.planning/code_analysis/20260715_vulnerability_scan.md` (the scan under verification).

No web sources were fetched (per task instruction for CITE-3, and per AGENTS.md "never make up references" for the DOI literature claims — CLI I1 verdict relies on the in-repo AGENTS.md DOI attribution plus the self-identifying paper title "TIP4P/2005", not on external verification).
