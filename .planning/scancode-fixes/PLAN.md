# Scancode Fixes Plan

**Date:** 2026-07-16
**Based on:** `.planning/scancode-fixes/RESEARCH.md` (verified, read-only)
**Goal:** Group verified scancode findings into coherent, atomic-commit fix tasks for a future debug session.

## Plan Overview

This plan covers the **31 CONFIRMED + 6 PARTIAL** findings from `RESEARCH.md`. It is organized into **9 in-scope fix groups** (S/M complexity, higher-priority correctness/robustness/tech-debt/doc issues) and a separate **Requires User Approval** section for L-complexity major refactors, low-priority/by-design items, and items needing external verification before any change.

**In scope (9 groups):** 2 correctness fixes rated HIGH/MEDIUM that affect real export/insertion paths (CRIT-01 triclinic PBC, CRIT-02 ion alternation), 1 pipeline robustness group (CRIT-04 assert→raise + SAFE-05 output-path check), 1 GUI group (SAFE-01 ion worker + SAFE-07 NaN guard), 1 module-constants cleanup (UNIT-02/03/04/05), 1 perf quick-wins group (PERF-04/06), 1 structure-generation robustness group (SUSP-03/06), 1 tech-debt group (TD-ADHOC + TD-07), and 1 documentation group (CLI #1/#2/#3, CLI I1, GUI MISS-1/2).

**Approval required:** FRAG-03 + TD-01 (split/dedup the 4067-line `gromacs_writer.py` monolith — L); PERF-01/02/03 (M perf, not correctness); CRIT-03/05 (bugs live in dead code `write_interface_pdb_file` — decide delete-vs-wire); VTK-DUP; TD-CONST (AVOGADRO relocation conflicts with AGENTS.md:48); plus by-design/accepted items needing no change (PERF-05, SAFE-03, SAFE-04, UNIT-01, SUSP-02/04/05). GUI CITE-3 needs external DOI verification before any edit.

**Overall risk:** Low-to-medium. The two correctness fixes (CRIT-01, CRIT-02) are the highest-value items and must land first with regression tests. Three groups touch `gromacs_writer.py` (Groups 1, 5, 8) and are ordered to avoid edit conflicts. All work follows AGENTS.md: conda-only (no auto-install), atomic commits per logical change, never hardcode physical constants, comb-rule=2, inserters return NEW structures, lazy imports for PySide6/VTK/GenIce2.

---

## Fix Groups (in-scope — S/M complexity, higher priority)

### Group 1: Triclinic PBC wrap fix
**Scope:** CRIT-01
**Files:** `quickice/output/gromacs_writer.py` (lines 308, 352); reference `quickice/structure_generation/water_filler.py` (106, 117, 127); `quickice/structure_generation/types.py` (119, 131, 142); `quickice/structure_generation/slab.py` (619)
**Risk:** medium (touches the hydrate export path)
**Why grouped:** Single correctness bug with one fix pattern (route triclinic cells through fractional-coordinate wrap); the orthogonal (slab) path must remain on the fast diagonal-modulo branch.
**Tasks:**
1. CRIT-01 — `gromacs_writer.py:308` — In `wrap_positions_into_box`, detect triclinic cells (off-diagonal `cell` elements non-zero, or a passed `is_triclinic` flag). For triclinic cells, wrap via fractional coordinates: `frac = pos @ inv(cell.T)`; `frac = np.mod(frac, 1.0)`; `wrapped = frac @ cell.T` — reusing the proven pattern from `water_filler.py:106-127` (`wrap_positions_triclinic`). For orthogonal cells, keep the existing diagonal-only `np.mod(wrapped[:, dim], cell[dim, dim])` (correct for slab interfaces forced orthogonal at `slab.py:619`).
2. CRIT-01 — `gromacs_writer.py:352` — Apply the same triclinic-aware branch in `wrap_molecules_into_box` (used by `write_interface_gro_file` via `pipeline.py:928`, which passes `hydrate.cell` that is triclinic for sH/c0te/c1te parsed at `hydrate_generator.py:414-430`). Do NOT wrap hydrate positions upstream (they are intentionally unwrapped at `hydrate_generator.py:186-189`) — wrapping happens here at export.
**Tests to add/update:** Add `tests/test_scancode_bugs_triclinic_pbc.py`: build or load a small sH (or c0te/c1te) hydrate with a triclinic cell, export via the GRO path, assert every output position satisfies `0 <= frac <= 1` in fractional coordinates (`frac = pos @ inv(cell.T)`), and assert no atom drifted outside the cell by a diagonal-only-modulo artifact. Keep the orthogonal slab test passing unchanged.
**Commit message:** `fix(scancode): triclinic-aware PBC wrap in gromacs_writer (CRIT-01)`
**Verification:** `pytest tests/test_scancode_bugs_triclinic_pbc.py -v` and full `pytest` (no regressions in slab/interface export tests). Manual: export an sH hydrate and confirm atoms remain inside the triclinic cell in VMD/gmx.

---

### Group 2: Ion inserter fixes (alternation parity + 3-atom fallback)
**Scope:** CRIT-02, SUSP-01
**Files:** `quickice/structure_generation/ion_inserter.py` (lines 103, 431, 444, 451, 458, 488-510)
**Risk:** low
**Why grouped:** Both are S fixes in the same file; CRIT-02 is a correctness bug (spatial clustering), SUSP-01 is a silent miscount on a rare fallback path. Two atomic commits, one file.
**Tasks:**
1. CRIT-02 — `ion_inserter.py:458` — Introduce a `placed_count` counter initialized to 0 before the `for i, water_idx in enumerate(selected):` loop at `:431`. Increment `placed_count` ONLY on successful placement (after the `continue` skips at `:444` overlap-with-existing and `:451` overlap-with-ions). Replace `if i % 2 == 0:` with `if placed_count % 2 == 0:` so parity reflects placement order, not enumerate index. The charge-neutrality trim at `:488-510` is correct and must remain unchanged (it guarantees net zero charge; only spatial alternation was wrong).
2. SUSP-01 — `ion_inserter.py:103` — The fallback `ice_mols = ice_atom_count // WATER_ATOMS_PER_MOLECULE` assumes 4 atoms/water and is wrong for 3-atom GenIce ice (only reached when `ice_nmolecules == 0` AND `interface_structure is None`). Guard the fallback: if `ice_nmolecules` is unavailable, do NOT assume `WATER_ATOMS_PER_MOLECULE` (4) — raise a clear `ValueError` (or require the caller to supply `ice_nmolecules`/`atoms_per_mol`) instead of silently computing 75 mols for 300 atoms. Use the `WATER_ATOMS_PER_MOLECULE` constant only when the ice is confirmed 4-atom (TIP4P-family); otherwise compute from the actual GenIce atom count.
**Tests to add/update:** `tests/test_scancode_bugs_ion_inserter.py` — (a) CRIT-02: craft a selected-water list where ≥1 candidate is rejected for overlap; assert Na/Cl strictly alternate by *placement* order and that rejected candidates do not flip parity. (b) SUSP-01: feed a 3-atom GenIce ice (300 atoms, no `ice_nmolecules`, no interface) and assert the fallback raises rather than returning 75.
**Commit messages:** `fix(scancode): ion alternation uses placement counter not enumerate index (CRIT-02)` and `fix(scancode): ion inserter fallback rejects 3-atom GenIce miscount (SUSP-01)`
**Verification:** `pytest tests/test_scancode_bugs_ion_inserter.py -v` and `pytest -k ion`.

---

### Group 3: Pipeline robustness (assert→raise + output path check)
**Scope:** CRIT-04, SAFE-05
**Files:** `quickice/cli/pipeline.py` (lines 137, 901; reference inputs at 243-249 and 495-509; reference `quickice/output/orchestrator.py:48-56`)
**Risk:** low-medium
**Why grouped:** Both are small robustness fixes in `cli/pipeline.py`; one converts a stripped-by-`-O` assert to a real raise, the other closes an input-validation inconsistency (inputs check path-traversal, output does not).
**Tasks:**
1. CRIT-04 — `pipeline.py:901` — Replace `assert water_atom_count + guest_atom_count == len(hydrate.positions), ...` with `if water_atom_count + guest_atom_count != len(hydrate.positions): raise ValueError(f"Hydrate atom-count mismatch: {water_atom_count} water + {guest_atom_count} guest != {len(hydrate.positions)} total")`. This keeps the check active under `python -O` / `PYTHONOPTIMIZE=1`. Note: this is distinct from AGENTS.md's "no bare except Exception" rule (which concerns `except`, not `assert`); converting assert→raise is a robustness fix, not a violation.
2. SAFE-05 — `pipeline.py:137` — After `output_path = Path(self.args.output).resolve()`, add a containment check mirroring the input checks at `:243-249` and `:495-509` (and `orchestrator.py:48-56`): reject outputs that escape the working directory, e.g. `if not output_path.is_relative_to(Path.cwd()): raise ValueError("--output must stay within the working directory")`. Use a more specific exception (`ValueError`), never a bare `except`.
**Tests to add/update:** `tests/test_scancode_bugs_pipeline.py` — (a) CRIT-04: run the count-check under `python -O` and assert a `ValueError` (not silent skip) on a deliberately mismatched wrapper. (b) SAFE-05: assert `--output` pointing outside cwd raises `ValueError` and an in-cwd path succeeds.
**Commit messages:** `fix(scancode): replace stripped assert with ValueError in pipeline (CRIT-04)` and `fix(scancode): validate --output stays within cwd (SAFE-05)`
**Verification:** `pytest tests/test_scancode_bugs_pipeline.py -v`; `python -O -m pytest -k "pipeline"` to confirm the check still fires under optimization.

---

### Group 4: GUI threading & input validation (ion worker + NaN guard)
**Scope:** SAFE-01, SAFE-07
**Files:** `quickice/gui/main_window.py` (lines 924, 935; reference `HydrateWorker` at 759, complete handler 802, error handler 821)
**Risk:** medium (introduces a new worker thread class)
**Why grouped:** Both are GUI-threading/validation fixes in `main_window.py`; SAFE-01 moves synchronous ion insertion off the main thread, SAFE-07 hardens the concentration input. Follow the EXISTING `HydrateWorker(QThread)` pattern (AGENTS.md: HydrateWorker subclasses QThread directly — do NOT migrate to QObject+moveToThread; the new worker must follow the same direct-subclass pattern for consistency).
**Tasks:**
1. SAFE-01 — `main_window.py:935` — Create `IonInsertionWorker(QThread)` mirroring `HydrateWorker` (constructed at `:759`, started at `:767`, with complete/error handlers at `:802`/`:821`). Move the synchronous `insert_ions(interface, concentration, volume_arg)` call into the worker's `run()`. In the handler that currently calls `insert_ions` at `:935`, disable the ion button, construct/start the worker, and re-enable the button in complete/error handlers (same lifecycle as hydrate). Emit results via signals; do NOT mutate GUI widgets from `run()`.
2. SAFE-07 — `main_window.py:924` — Harden `if concentration <= 0` to also reject NaN/Inf: `import math` and use `if concentration is None or math.isnan(concentration) or math.isinf(concentration) or concentration <= 0:` raising/showing a clear user-facing error before `int(round(...))` (which raises `ValueError` on NaN — replace the unhelpful crash with a guided message).
**Tests to add/update:** `tests/test_scancode_bugs_gui_ion.py` (use `QT_QPA_PLATFORM=offscreen`; mock/skip VTK if the headless env crashes). (a) SAFE-01: assert `IonInsertionWorker` is a `QThread` subclass, that `insert_ions` is NOT called on the main thread (mock and check thread identity), and that the ion button is disabled during work and re-enabled on completion/error. (b) SAFE-07: feed NaN and Inf concentrations and assert a clear error is raised/shown (no `ValueError` from `round`).
**Commit messages:** `fix(scancode): run ion insertion off the GUI thread via IonInsertionWorker (SAFE-01)` and `fix(scancode): reject NaN/Inf ion concentration before round (SAFE-07)`
**Verification:** `QT_QPA_PLATFORM=offscreen pytest tests/test_scancode_bugs_gui_ion.py -v`; manual GUI check: insert ions on a realistic system and confirm the UI stays responsive; type a non-numeric concentration and confirm a clean error.

---

### Group 5: Module constants cleanup (TIP4P-ICE / ion / CH4 params)
**Scope:** UNIT-02, UNIT-03, UNIT-04, UNIT-05
**Files:** `quickice/output/gromacs_writer.py` (52, 386, 56-57, 91-92, 980-991); `quickice/structure_generation/solute_inserter.py` (166); `quickice/structure_generation/gromacs_ion_export.py` (19-20)  *(path corrected from RESEARCH.md's bare `gromacs_ion_export.py` — the file is under `structure_generation/`, not `output/`)*
**Risk:** low (pure refactor — MUST NOT change any numeric value)
**Why grouped:** All four are "extract inline magic numbers to named module constants" fixes aligned with AGENTS.md ("Never hardcode TIP4P-ICE parameters. Use module constants"). Three touch `gromacs_writer.py`, so they land together before the structural TD-ADHOC refactor (Group 8).
**Tasks:**
1. UNIT-03 — `gromacs_writer.py:52` and `:386` — `TIP4P_ICE_ALPHA = 0.13458335` is defined twice (same value). Remove the duplicate at `:386`; keep the single definition at `:52`. Replace the inline `0.13458335` at `:991` with the `TIP4P_ICE_ALPHA` constant.
2. UNIT-02 — `gromacs_writer.py:980-991` — Extract the inline TIP4P-ICE charges (`HW_ice: 0.5897`, `MW: -1.1794`), settle distances (`0.09572 0.15139`), and alpha (`0.13458335`) into named module constants next to the existing LJ constants at `:56-57` (`TIP4P_ICE_OW_SIGMA`/`TIP4P_ICE_OW_EPSILON`). Reference the constants inline. Do NOT change any value; cross-check against `quickice/data/tip4p-ice.itp` and Abascal 2005 (DOI 10.1063/1.1931662, per AGENTS.md).
3. UNIT-04 — `solute_inserter.py:166` — Replace inline `r_ch = 0.109620` (CH4 C-H bond, comment "from ch4.itp") with a named module-level constant (e.g. `CH4_CH_BOND_LENGTH_NM = 0.109620`) with a comment citing `ch4.itp`.
4. UNIT-05 — `gromacs_ion_export.py:19-20` vs `gromacs_writer.py:91-92` — **Investigate first:** GROMACS `[atomtypes]` sections conventionally carry `charge=0.0` (nonbonded params only) while the real ion charge lives in the `[moleculetype] [atoms]` section written by `gromacs_ion_export.py` (`NA_CHARGE=0.85`, `CL_CHARGE=-0.85`). If `gromacs_writer.py:91-92` `ION_ATOMTYPES` `charge=0.0` is the `[atomtypes]` convention, it is CORRECT and these are NOT duplicates — in that case add a clarifying comment and do NOT merge. Only if they represent the same field should they be consolidated into a single shared constant. Verify against a produced `.top`/`.itp` before changing anything.
**Tests to add/update:** No behavior change expected; run the full suite and any ion-export E2E test (`tests/test_e2e_ion_export.py`) and a `gmx grompp` dry run if `gmx` is available (`@gmx_skipif` otherwise) to confirm the produced topology is byte-identical (or semantically identical) to before.
**Commit messages:** one per task, e.g. `refactor(scancode): dedup TIP4P_ICE_ALPHA definition (UNIT-03)`, `refactor(scancode): extract TIP4P-ICE charges/settle/alpha to constants (UNIT-02)`, `refactor(scancode): name CH4 C-H bond constant (UNIT-04)`, `refactor(scancode): clarify ion charge sources, no value change (UNIT-05)`
**Verification:** `pytest` (full suite, ~1007 tests, no regressions); `git diff` shows only constant extraction — no numeric value changes.

---

### Group 6: Inserter performance quick wins (batch query + vectorized water removal)
**Scope:** PERF-04, PERF-06
**Files:** `quickice/structure_generation/solute_inserter.py` (412-416, 556-562); `quickice/structure_generation/custom_molecule_inserter.py` (367-371)
**Risk:** low (pure perf — results must be identical)
**Why grouped:** Both are S perf wins using existing data (cKDTree batch `query` and boolean masking) — no algorithmic change, just vectorization. SAFE under AGENTS.md's "cKDTree conditional rebuild" rule (these do NOT add rebuilds; they batch existing queries).
**Tasks:**
1. PERF-04 — `solute_inserter.py:412-416` and `custom_molecule_inserter.py:367-371` — Replace the per-atom Python loop `for atom_pos in solute_positions: existing_tree.query(atom_pos, k=1)` with a single batch call `dists, idxs = existing_tree.query(solute_positions, k=1)`. Preserve the same overlap decision logic (compare `dists` against the same threshold). cKDTree supports batched `query` natively.
2. PERF-06 — `solute_inserter.py:556-562` — The `mol_overlaps` mask is already computed; replace the `for mol_idx in water_molecules_to_keep: kept_water_positions.append(...)` loop with a vectorized boolean-mask selection over the water-positions array (e.g. `kept = water_positions[~mol_overlaps]` reshaped per molecule). Verify the kept set matches the loop output exactly.
**Tests to add/update:** `tests/test_scancode_bugs_inserter_perf.py` — assert batch-query and vectorized-removal produce identical positions/counts to the old loop on a deterministic fixture (seeded RNG).
**Commit messages:** `perf(scancode): batch cKDTree query in solute/custom inserters (PERF-04)` and `perf(scancode): vectorize water removal in solute inserter (PERF-06)`
**Verification:** `pytest tests/test_scancode_bugs_inserter_perf.py -v`; `pytest -k inserter`; confirm identical output via a seeded e2e comparison before/after.

---

### Group 7: Structure generation robustness (box-line parse + custom overlap warning)
**Scope:** SUSP-03, SUSP-06
**Files:** `quickice/structure_generation/hydrate_generator.py` (390-399); `quickice/structure_generation/custom_molecule_inserter.py` (796-813)
**Risk:** low
**Why grouped:** Both are S robustness fixes in structure-generation parsing/placement code; neither changes correct-path behavior, only removes fragility / adds a warning.
**Tasks:**
1. SUSP-03 — `hydrate_generator.py:390-399` — The box-line loop skips lines whose first char is not a digit and relies on the fallback `if box_line is None: box_line = lines[-1]` (`:398-399`). Simplify to robustly identify the box line: parse the last GRO-record line that matches the box-line format (3 or 9 floats), or explicitly take `lines[-1]` after stripping trailing whitespace/blank lines. Add a guard that raises a clear `ValueError` if no box line is found. Keep behavior identical for standard GenIce2 output.
2. SUSP-06 — `custom_molecule_inserter.py:796-813` — `place_custom` documents "No overlap checking (user responsibility)" but emits no warning. Add a `logging.warning(...)` (or `warnings.warn`) when placed molecules are closer than a sensible threshold, OR at minimum log an explicit "no overlap check performed" notice when the function is called, so users are warned rather than silently getting overlaps. Do NOT add a hard rejection (keep current placement behavior).
**Tests to add/update:** `tests/test_scancode_bugs_structure_gen.py` — (a) SUSP-03: feed a standard GenIce GRO and a GRO with trailing blank lines; assert the box line is parsed correctly and that a malformed input raises. (b) SUSP-06: place two overlapping custom molecules and assert a warning is emitted (use `pytest.warns` / caplog).
**Commit messages:** `fix(scancode): robustly parse GRO box line in hydrate_generator (SUSP-03)` and `fix(scancode): warn on custom molecule placement without overlap check (SUSP-06)`
**Verification:** `pytest tests/test_scancode_bugs_structure_gen.py -v`; `pytest -k hydrate` and `pytest -k custom`.

---

### Group 8: Tech debt cleanup (ad-hoc type objects + atomtype-conflict validation)
**Scope:** TD-ADHOC, TD-07
**Files:** `quickice/output/gromacs_writer.py` (2133, 2144, 3415, 3422, 3448, 3464, 3474); `quickice/structure_generation/molecule_validator.py` (185)
**Risk:** medium (TD-ADHOC replaces 7 anonymous-class instances used downstream; TD-07 adds a validation gate that could reject valid uploads if too strict)
**Why grouped:** Both are M tech-debt fixes; TD-ADHOC touches `gromacs_writer.py` and is sequenced AFTER Group 5 (constants) so the two `gromacs_writer.py` edits layer cleanly. TD-07 is a validation improvement.
**Tasks:**
1. TD-ADHOC — `gromacs_writer.py` (7 sites: 2133, 2144, 3415, 3422, 3448, 3464, 3474) — Replace `type('obj', (object,), {...})()` anonymous-class instances with a proper `@dataclass` (e.g. `MoleculeIndex`) carrying the same fields. Grep all usages first to confirm attribute access patterns; keep field names identical for a drop-in replacement. Define the dataclass once at module top (respecting lazy-import rules — this is a plain dataclass, no PySide6/VTK). Verify each of the 7 sites constructs the dataclass with the same values.
2. TD-07 — `molecule_validator.py:185` — Currently `if not itp_info.has_atomtypes_section` checks only atomtypes PRESENCE. Add an atomtype-CONFLICT check in `validate_custom_molecule`: detect user-defined atomtype names that collide with built-in TIP4P-ICE/GAFF2 types (e.g. `OW_ice`, `HW_ice`, `MW`, `NA`, `CL`) and raise a clear validation error at upload time (before `gmx grompp`). Use the built-in atomtype names from `gromacs_writer.py` `ION_ATOMTYPES` / TIP4P-ICE atomtype constants as the conflict set. Do NOT reject non-conflicting uploads.
**Tests to add/update:** `tests/test_scancode_bugs_tech_debt.py` — (a) TD-ADHOC: assert the 7 construction sites produce objects with identical attributes to the old anonymous-class shape (use the existing GRO writer tests as regression). (b) TD-07: upload a custom molecule that redefines `OW_ice` and assert a clear validation error; upload a non-conflicting molecule and assert acceptance.
**Commit messages:** `refactor(scancode): replace ad-hoc type() objects with MoleculeIndex dataclass (TD-ADHOC)` and `fix(scancode): reject built-in atomtype conflicts at upload (TD-07)`
**Verification:** `pytest tests/test_scancode_bugs_tech_debt.py -v`; full `pytest` (especially GRO writer and validator tests); if `gmx` available, `gmx grompp` dry-run on a built-in-atomtype-conflicting upload to confirm the error now surfaces earlier.

---

### Group 9: Documentation fixes (CLI + GUI + citation labels)
**Scope:** CLI #1, CLI #2, CLI #3, CLI I1, GUI MISS-1, GUI MISS-2
**Files:** `docs/cli-reference.md` (149); `README.md` (222-229); `quickice/main.py` (139) + `quickice/cli/itp_helpers.py` (311-316); `quickice/structure_generation/types.py` (32-38); `docs/gui-guide.md`; `quickice/gui/interface_panel.py` (258, reference only); `quickice/gui/main_window.py` (2139, reference only)
**Risk:** low (docs + one source-comment fix + one filename-investigation)
**Why grouped:** All are S documentation/citation-label fixes; CLIs and GUI guide are doc-only, CLI I1 is a source-comment label fix, CLI #3 may be a code filename fix (investigate first).
**Tasks:**
1. CLI #1 — `docs/cli-reference.md:149` — The doc says the pipeline exits with code 1 for `--no-overwrite`, but `pipeline.py:155` `return 0` (success on skip). Correct the doc to say it exits 0 (skip) when `--no-overwrite` finds an existing file.
2. CLI #2 — `README.md:229` — The prose order "SOL → guests → solutes → custom → ions" swaps solutes and custom vs the code (`gromacs_writer.py:2776-2800`: SOL → guest → custom → solute → NA → CL). Fix the prose AND the example block at `:222-226` (which shows `THF_L` before `CUSTOM_MOL_1`) to match the code order: SOL → guest → custom → solute → NA → CL.
3. CLI #3 — `main.py:139` vs `cli/itp_helpers.py:314` — `main.py` uses `tip4p_ice.itp` (underscore); `itp_helpers.py:314` and the actual data file `quickice/data/tip4p-ice.itp` use a hyphen. **Investigate first:** if `main.py:139` is used to locate/copy the data file, it is a bug — fix to `tip4p-ice.itp` (hyphen). If it is only a display label, align it to the hyphen form for consistency. Confirm the resolved path exists. *(Note: RESEARCH.md corrected the scan's path — the real file is `cli/itp_helpers.py`, not `structure_generation/itp_helpers.py`.)*
4. CLI I1 — `types.py:32-38` — The citation labels are reversed: line 36 says "For TIP4P-ICE specifically:" but attaches to the TIP4P/2005 paper (DOI 10.1063/1.2121600, self-identified as TIP4P/2005). Per AGENTS.md, DOI 10.1063/1.1931662 (Abascal 2005) is TIP4P-ICE. Swap the labels so "TIP4P-ICE" labels 10.1063/1.1931662 and "TIP4P/2005" labels 10.1063/1.2121600. Do NOT introduce new references — only relabel existing DOIs already in the file (AGENTS.md: "never make up references").
5. GUI MISS-1 — `docs/gui-guide.md` — Document the "Hydrate Structure" source option that exists in `interface_panel.py:258` (`self.source_combo.addItems(["Ice Candidate", "Hydrate Structure"])`). Add a section explaining when to use each source.
6. GUI MISS-2 — `docs/gui-guide.md` — Document the remote-OpenGL configuration in `main_window.py:2139` (`_configure_opengl_for_remote()` sets `__GLX_VENDOR_LIBRARY_NAME=mesa`). Add a "Remote/headless OpenGL" note with the env var and when it applies.
**Tests to add/update:** No unit tests (docs). Optional: add a smoke test for CLI #3 that the resolved itp path exists; for CLI I1, a grep-based assertion that the TIP4P-ICE label is on the 10.1063/1.1931662 line.
**Commit messages:** `docs(scancode): fix --no-overwrite exit code (CLI #1)`, `docs(scancode): fix molecule order in README (CLI #2)`, `fix(scancode): align tip4p-ice.itp filename (CLI #3)`, `docs(scancode): fix reversed TIP4P-ICE/TIP4P-2005 citation labels (CLI I1)`, `docs(scancode): document Hydrate Structure source option (GUI MISS-1)`, `docs(scancode): document remote OpenGL mesa config (GUI MISS-2)`
**Verification:** `pytest` (no regressions); manual: re-read the changed docs for accuracy; for CLI #3, `python -c "from pathlib import Path; assert Path('quickice/data/tip4p-ice.itp').exists()"`.

---

## Requires User Approval

### Major codebase changes (L complexity)
| ID | Issue | Why major | Recommendation |
|----|-------|-----------|----------------|
| FRAG-03 | `gromacs_writer.py` is 4067 lines — split into per-structure modules | Touches the most-used export module; high regression risk; large refactor touching every export path | **Defer.** Do only together with TD-01. Land the in-scope `gromacs_writer.py` fixes (Groups 1, 5, 8) first so the eventual split starts from a cleaned-up file. Needs a full regression + `gmx grompp` suite before/after. |
| TD-01 | 6 near-identical GRO writer functions (`write_gro_file`:833, `write_interface_gro_file`:1044, `write_multi_molecule_gro_file`:1688, `write_ion_gro_file`:2044, `write_custom_molecule_gro_file`:2803, `write_solute_gro_file`:3336) | Dedup extraction across 6 functions; behavior must stay byte-identical for GROMACS | **Defer.** Pair with FRAG-03 — extract shared GRO-writer helpers first, then split modules. Requires user approval and a regression plan. |

### Low-priority items (need user approval per instruction)
| ID | Issue | Why low-priority | Recommendation |
|----|-------|-------------------|----------------|
| CRIT-03 / CRIT-05 | `i//3` and `MW→"M"` bugs live in DEAD code `write_interface_pdb_file` (`pdb_writer.py:113`, not exported, zero callers) | Bugs are real but UNREACHABLE; reachable `write_pdb_with_cryst1` only sees O/H atoms | **Decide delete-vs-wire.** Minimal safe action: DELETE `write_interface_pdb_file` (removes both latent bugs in one stroke, S). If the interface-PDB export path is intended to exist, that is a larger wire-up task — needs user intent. |
| PERF-01 | `ion_inserter.py:456` cKDTree rebuilt per ion placement (O(k² log k)) | M perf, NOT correctness; charge-neutrality trim already guarantees net zero | **Defer / approve.** Batch or incremental KDTree index; medium effort, no behavior change. |
| PERF-02 | `solute_inserter.py:909-910` vstack + cKDTree rebuild per placement | M perf, not correctness | **Defer / approve.** Pre-allocate + batch rebuild. |
| PERF-03 | `custom_molecule_inserter.py:659-660` same vstack+rebuild pattern | M perf, not correctness | **Defer / approve.** Same pattern as PERF-02. |
| TD-CONST | `AVOGADRO` defined in `ion_inserter.py:29`, imported by 4 files | AGENTS.md:48 MANDATES `ion_inserter.py` as the single source; already single-sourced (no duplication) | **Keep as-is** unless user wants centralization in `types.py`. Relocating would require updating AGENTS.md:48 — treat as a doc+code coordination decision needing approval. |
| VTK-DUP | `_VTK_AVAILABLE=False` copy-paste in 6 viewer files (custom_molecule_viewer, hydrate_viewer, interface_panel, ion_viewer, solute_viewer, view.py) | M tech debt; lower priority; GUI-only | **Defer / approve.** Extract a shared `vtk_utils.py` helper. Flagged lower-priority by user. |
| ITP staging dual path | (Not separately verified as a distinct ID in RESEARCH.md) | Not deep-verified in this pass | **Verify scope first** before planning — confirm whether this is a distinct concern or overlaps SUSP-02 / the itp_helpers path. |
| PERF-05 | `gromacs_writer.py:900+` per-atom string formatting | **Explicitly accepted** I/O-bound tradeoff (comment at :892-898) | **No change.** Accepted by design. |
| SAFE-03 | `interface_builder.py:370-374` broad `except Exception ... from e` | Compliant with AGENTS.md (bare-except bar is `cli/pipeline.py` only); re-raises with traceback | **No change.** Compliant; fragility only. |
| SAFE-04 | `gromacs_writer.py:915` GRO 3-decimal precision | By-design; `grompp` recomputes settles/vsites | **No change.** By design. |
| UNIT-01 | PDB 3N atoms vs GRO 4N (MW added) | By-design: PDB is visualization (no MW), GRO adds MW for simulation | **No change.** Document if desired. |
| SUSP-02 | `gromacs_writer.py:1462-1484` guest-name heuristic | Detection ORDER is actually CORRECT (CO2→THF→CH4→H2→Me); only fragile for unknown C+H guests, which bypass via `custom_guest_info` | **No change** (optionally add a warning for unrecognized C+H guests — needs approval). |
| SUSP-04 | `gromacs_writer.py:456-462` returns canonical names not reordered input | By intent; built-in ch4/thf ITPs match canonical names; custom guests skip this | **No change.** By intent. |
| SUSP-05 | `gromacs_writer.py:359-364` unwrap handles only single box-length | Low impact for typical systems (water 0.28 nm in 2+ nm box) | **No change.** Low impact. |

### Items needing external verification before any change
| ID | Issue | What to verify |
|----|-------|---------------|
| GUI CITE-3 | Madrid2019 DOI — `README.md:383,387` both say `10.1063/1.5121392`; the claimed `.1392` vs `.1394` discrepancy is a FALSE ALARM (no `.1394` in repo) | Before ANY edit, fetch both DOIs (`10.1063/1.5121392` and `10.1063/1.5121394`) via the web to confirm which resolves to the intended Madrid2019 paper. Per AGENTS.md "never make up references," do NOT change the DOI without external confirmation. Also cross-check `.planning/code_analysis/20260516_madrid2019_citation_research.md`. |

---

## Out of Scope (false alarms / already fixed / safe)
| ID | Reason |
|----|--------|
| SAFE-02 | FALSE ALARM — the Generate button IS disabled at `main_window.py:756` before `HydrateWorker(config)` (`:759`) and `start()` (`:767`); re-enabled in complete/error handlers (`:802`/`:821`). (Narrower residual: a worker crash without emitting a signal could leave the button stuck — not the concurrent-race claim.) Not planned. |
| SAFE-06 | CONFIRMED SAFE — no `shell=True`/`os.system`/`os.popen` in `quickice/`. No action. |
| GUI CITE-3 (discrepancy claim) | FALSE ALARM on the internal discrepancy (both README lines read `.1392`). The remaining "is `.1392` correct?" question is external-verification-only (see above), not a fix task. |

---

## Suggested Execution Order
1. **Group 1 (CRIT-01 triclinic PBC)** — highest-value correctness fix on the export path; lock export correctness first; touches `gromacs_writer.py` (do before Groups 5/8 on the same file).
2. **Group 2 (CRIT-02 + SUSP-01 ion inserter)** — quick correctness fix, independent file (`ion_inserter.py`).
3. **Group 3 (CRIT-04 + SAFE-05 pipeline)** — quick robustness, independent file (`cli/pipeline.py`).
4. **Group 5 (UNIT-02/03/04/05 constants)** — touches `gromacs_writer.py`; do BEFORE Group 8 so the file is layered (constants → structural TD-ADHOC).
5. **Group 4 (SAFE-01 + SAFE-07 GUI)** — medium effort; new `IonInsertionWorker`; do after core correctness fixes.
6. **Group 6 (PERF-04/06 perf quick wins)** — independent inserter perf, low risk.
7. **Group 7 (SUSP-03 + SUSP-06 robustness)** — independent structure-gen files.
8. **Group 8 (TD-ADHOC + TD-07 tech debt)** — touches `gromacs_writer.py`; do AFTER Group 5 (constants) to avoid conflicting edits.
9. **Group 9 (documentation)** — lowest risk; do LAST so docs reflect the final code state (filename, order, labels).

*Rationale:* The three `gromacs_writer.py` groups are ordered 1 → 5 → 8 (correctness → constants → structural) so each commit layers on a stable file. All other groups are file-disjoint and can be reordered freely. Approval-required items (FRAG-03/TD-01, PERF-01/02/03, CRIT-03/05, VTK-DUP, TD-CONST, GUI CITE-3) are excluded from this order.

---

## Test Strategy
- **Pattern:** Add a `tests/test_scancode_bugs_*.py` regression file per group (matches the existing `test_scancode_bugs_*.py` convention in AGENTS.md).
- **Per-group:** Each fix gets a targeted test that would FAIL before the fix and PASS after:
  - CRIT-01 → triclinic sH export stays in fractional [0,1].
  - CRIT-02 → alternation by placement order with overlap rejections.
  - CRIT-04 → check fires under `python -O`.
  - SAFE-05 → `--output` outside cwd rejected.
  - SAFE-01 → `insert_ions` not on main thread; button lifecycle.
  - SAFE-07 → NaN/Inf concentration → clean error.
  - PERF-04/06 → identical output to loop on a seeded fixture.
  - SUSP-01 → 3-atom GenIce fallback raises.
  - SUSP-03 → box line parsed with trailing blanks; malformed raises.
  - SUSP-06 → overlap emits a warning (`pytest.warns`/caplog).
  - TD-ADHOC → 7 sites produce identical attributes.
  - TD-07 → built-in-atomtype conflict rejected at upload; non-conflict accepted.
- **Regression gate:** Run the full suite `pytest` (~1007 tests) after every group; expect zero new failures. Run `pytest -x --timeout=120` to fail fast.
- **GROMACS tests:** Use `@gmx_skipif` for `gmx`-dependent tests; if `gmx` is on PATH, add a `gmx grompp` dry-run for the ion/topology changes (UNIT-02/05, TD-07) to confirm the produced topology is still valid. comb-rule=2 must remain in all `.top` files (AGENTS.md).
- **GUI tests:** Set `QT_QPA_PLATFORM=offscreen`; mock or skip VTK-dependent tests if the headless env crashes (AGENTS.md / ROADMAP TEST-06 deferred).
- **No new dependencies:** All fixes use existing libs (numpy, scipy, PySide6, pytest). Do NOT add dependencies; if one is needed, seek user approval and edit `environment.yml` (AGENTS.md).
- **Atomic commits:** One commit per logical change (commit messages listed per group). Never `git add .` / `git add -A` — stage only intended files (AGENTS.md).
