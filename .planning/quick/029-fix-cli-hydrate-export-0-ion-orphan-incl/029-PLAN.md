---
phase: 029-fix-cli-hydrate-export-0-ion-orphan-incl
plan: 029
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/output/ion_writer.py
  - quickice/cli/itp_helpers.py
  - quickice/cli/pipeline.py
  - tests/e2e/solute_ion/test_e2e_cli_zero_ion_export.py
  - tests/e2e/hydrate/test_e2e_cli_mixed_builtin_hydrate_grompp.py
autonomous: true

must_haves:
  truths:
    - "CLI export where the ion step inserted 0 ions produces a .top with NO ion.itp #include, no ion.itp staged, and gmx grompp rc==0"
    - "CLI export with ions present still stages + #includes ion.itp and passes grompp (ion users unaffected)"
    - "CLI hydrate-branch export of a mixed built-in hydrate (CH4 small + THF large) emits CH4_H and THF_H as separate [molecules] entries whose counts match the .gro"
    - "CLI mixed built-in hydrate export stages and #includes BOTH ch4_hydrate.itp and thf_hydrate.itp; grompp rc==0"
    - "Single-guest CLI hydrate exports unchanged (existing filled-ice/triclinic e2e still green)"
  artifacts:
    - path: "quickice/output/ion_writer.py"
      provides: "write_ion_top_file #include gate on na/cl counts"
      contains: "na_count > 0 or cl_count > 0"
    - path: "quickice/cli/itp_helpers.py"
      provides: "ion branch staging gate + hydrate branch multi-type built-in staging"
      contains: "_detect_builtin_guest_types"
    - path: "quickice/cli/pipeline.py"
      provides: "hydrate-branch wrapper threading guest_descriptors + guest_atom_counts"
      contains: "_derive_guest_atom_counts"
    - path: "tests/e2e/solute_ion/test_e2e_cli_zero_ion_export.py"
      provides: "RED-first e2e repro for bug (a) + ion-present regression guard"
    - path: "tests/e2e/hydrate/test_e2e_cli_mixed_builtin_hydrate_grompp.py"
      provides: "RED-first e2e repro for bug (b)"
  key_links:
    - from: "quickice/cli/pipeline.py hydrate-branch wrapper"
      to: "quickice/output/interface_writer.py mixed_builtin gates (lines ~428 GRO / ~656 TOP)"
      via: "InterfaceStructure kwargs guest_descriptors + guest_atom_counts"
      pattern: "guest_atom_counts=_derive_guest_atom_counts"
    - from: "quickice/cli/itp_helpers.py hydrate branch staging"
      to: "write_interface_top_file #include directives"
      via: "stage every distinct built-in type the writers include"
      pattern: "_detect_builtin_guest_types"
    - from: "quickice/output/ion_writer.py #include gate"
      to: "quickice/cli/itp_helpers.py ion branch staging gate"
      via: "same condition na_count>0 or cl_count>0 (writer counts from molecule_index; staging from structure attrs)"
      pattern: "na_count > 0 or cl_count > 0"
---

<objective>
Fix two CLI hydrate-workflow export bugs documented in the 48.3-25 exit audit (STATE.md "Status"):

**(a) 0-ion orphan include** — CLI export after an ion step that inserted 0 ions (na_count==cl_count==0, e.g. tiny concentration rounding to 0 pairs) still writes `#include "ion.itp"` into ion.top and stages ion.itp. The NA/CL `[atomtypes]` block in ion.top is gated on the counts (ion_writer.py:824) while the include is NOT (ion_writer.py:951), and ion.itp's `[atoms]` reference atomtypes NA/CL → `gmx grompp` fatal. **Live-verified failure:** `ERROR 1 [file ion.itp, line 8]: Atomtype NA not found` (rc=1).
Fix = documented preferred option (2): skip include + staging when na_count==cl_count==0. No output change for ion users.

**(b) Mixed built-in guest mislabeling** — the CLI hydrate branch (pipeline.py:924-969) wraps the HydrateStructure in an InterfaceStructure but never threads `guest_descriptors` / `guest_atom_counts`, so `write_interface_gro_file`/`write_interface_top_file` fall to the single-stream `detect_guest_type_from_atoms` path and ALL guests collapse to CH4_H. The writers ALREADY have correct mixed-built-in paths (interface_writer.py:423-498 GRO, 635-698/782-861/887-899 TOP — added by the 48.3-05/45-15 line of fixes); they are just never activated on this path. **Live-verified:** mixed sII (CH4 small + THF large) exports `[molecules] = SOL 1088 / CH4_H 192` and stages only ch4_hydrate.itp.
Fix = thread the metadata into the existing path (44.1-02..07 precedent) + stage every distinct built-in guest ITP (48.3-05 config-driven staging precedent). Do NOT reroute through the multi-molecule writers — the minimal threading fix was live-verified to grompp rc=0.

Purpose: a passing CLI e2e must mean the real workflow passed, before the user's manual UAT run.
Output: 2 production fixes + 2 true-e2e regression files (RED-first), all committed atomically.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

Source slices to READ before editing (use Read offset/limit — do NOT read whole files):
- quickice/cli/pipeline.py:859-997 (export step; hydrate branch at 924-969)
- quickice/output/ion_writer.py:604-675 (counts + custom_active) and 940-962 (the unconditional include)
- quickice/cli/itp_helpers.py:324-340 (hydrate branch staging) and 488-511 (ion branch staging)
- quickice/output/interface_writer.py:635-698 (TOP mixed_builtin gate — read-only, NO edits needed here)
- quickice/structure_generation/types.py:1163-1208 (_derive_guest_atom_counts) and 1211-1249 (HydrateStructure fields)

Test-pattern references (read once, then mirror):
- tests/e2e/hydrate/test_e2e_filled_ice_cli_hydrate_grompp.py (CLIPipeline._run_export_step surface + assert helpers)
- tests/e2e/solute_ion/test_e2e_mixed_ion_export.py:163-216 (mixed sII fixture + slab config pattern)

Environment facts (verified 2026-09-25): conda env `quickice` already active; `gmx` on PATH; plain `git add` works for quickice/output/ (git check-ignore rc=1 — NOT ignored, no -f needed).
</context>

<tasks>

<task type="auto">
  <name>Task 1: Bug (a) — skip ion.itp include+staging when 0 ions (RED-first e2e)</name>
  <files>tests/e2e/solute_ion/test_e2e_cli_zero_ion_export.py, quickice/output/ion_writer.py, quickice/cli/itp_helpers.py</files>
  <action>
**Step 1 — RED test.** Create `tests/e2e/solute_ion/test_e2e_cli_zero_ion_export.py` (dir has `__init__.py`; pytest discovers normally). Mirror the filled-ice CLI surface pattern. Contents:

- Module-scoped fixture `zero_ion_export(tmp_path_factory)`: real generators only —
  `HydrateStructureGenerator().generate(HydrateConfig(lattice_type="sI", guest_type="ch4", supercell_x=1, supercell_y=1, supercell_z=1))` → `hydrate.to_candidate()` → slab interface via `generate_interface(candidate, InterfaceConfig(mode="slab", box_x=max(ce[0]*2, 4.0), box_y=max(ce[1]*2, 4.0), box_z=2*max(ce[2], 2.0)+3.0, ice_thickness=max(ce[2], 2.0), water_thickness=3.0, seed=42))` where `ce = get_cell_extent(candidate.cell)` (imports: `quickice.structure_generation.interface_builder.generate_interface`, `quickice.structure_generation.water_filler.get_cell_extent`, `HydrateConfig`/`InterfaceConfig` from `quickice.structure_generation.types`).
  Then `insert_ions(iface, 0.001, None, seed=42)` — 0.001 M with the REAL volume estimate (None → water_nmolecules × WATER_VOLUME_NM3, exactly mirroring pipeline.py:838-846) rounds to 0 ion pairs (verified: 2587 waters → n≈0.046 → 0). Sanity assert `ion.na_count == 0 and ion.cl_count == 0` — **if this assert fails, STOP and report** (the repro precondition changed).
  Then `CLIPipeline(args=SimpleNamespace())`, `pipe._output_dir = ws` (mktemp dir), `pipe._ion_result = ion` (only `_ion_result` set → priority picks the ion branch), `rc = pipe._run_export_step()`; assert `rc == 0`.
- Test `test_zero_ion_export_has_no_orphan_ion_include(zero_ion_export)` — the CORRECT behavior (fails today):
  1. `'#include "ion.itp"'` NOT in ion.top text
  2. `(ws / "ion.itp")` does NOT exist
  3. `parse_top_molecules` has neither "NA" nor "CL" keys
  4. `assert_itp_completeness(str(top), ws)` + `assert_gro_top_consistent(str(gro), str(top))`
  5. `@gmx_skipif`-guarded grompp: `shutil.copy(MDP_PATH, ws/"em.mdp")`; `rc, err = run_gmx_grompp(ws, gro_file="ion.gro", top_file="ion.top")`; assert `rc == 0`
- Test `test_ion_present_export_keeps_ion_include(tmp_path, ...)` — regression guard for ion users (passes today AND after fix): second module fixture (or shared iface fixture) with `insert_ions(iface, 0.5, None, seed=42)`; assert na_count>0; export via the same pipe surface; assert ion.itp IS staged, `'#include "ion.itp"'` IS in ion.top, "NA"/"CL" ARE in `parse_top_molecules` with counts == ion.na_count/ion.cl_count, completeness+consistency asserts, grompp rc==0.
  Note: `insert_ions` sets `iface.molecule_index` on first call (duck-typing, CP-01) — calling it twice on the same iface is safe (verified idempotent path).

Helpers imported from `tests.e2e_export_helpers`: MDP_PATH, run_gmx_grompp, parse_top_molecules, assert_itp_completeness, assert_gro_top_consistent. `@gmx_skipif` from `tests.conftest`. No PySide6/VTK imports.

**Step 2 — Run RED:** `timeout 300 python -m pytest tests/e2e/solute_ion/test_e2e_cli_zero_ion_export.py -q`
Expected: `test_zero_ion_export_has_no_orphan_ion_include` FAILS at the grompp assert (rc=1) with `ERROR 1 [file ion.itp, line 8]: Atomtype NA not found` (live-verified 2026-09-25); the ion-present guard test PASSES. **If the failure does NOT match this documented cause, STOP and report — do not thrash; escalate via /gsd-debug for bug (a).**

**Step 3 — Fix (skip-when-empty).** Two gated sites, same condition:
- `quickice/output/ion_writer.py` `write_ion_top_file`, line ~950-951 — replace the unconditional
  `f.write('#include "ion.itp"\n\n')` with:
  ```python
  if na_count > 0 or cl_count > 0:
      f.write('#include "ion.itp"\n')
  f.write("\n")
  ```
  (`na_count`/`cl_count` are the molecule_index-derived counts from lines ~622-623 — the SAME source the `[atomtypes]` gate at line ~824 uses. Byte-identical output when ions present; the standalone `f.write("\n")` preserves the blank line before `[ system ]` in both cases.)
- `quickice/cli/itp_helpers.py` ion branch, lines ~505-511 — wrap the existing try-block in `if na_count > 0 or cl_count > 0:` (na_count/cl_count already computed at lines 505-506 from structure attrs); when 0, `logger.info("0 ions — skipping ion.itp generation")` and do not append. Keep the existing `except Exception` inside as-is (pre-existing; do not add new broad catches).

**Step 4 — Run GREEN:** same pytest command → 2 passed. Commit atomically (stage only these 3 files):
`git add quickice/output/ion_writer.py quickice/cli/itp_helpers.py tests/e2e/solute_ion/test_e2e_cli_zero_ion_export.py`
`git commit -m "fix(029): skip ion.itp include+staging for 0-ion CLI exports"`
  </action>
  <verify>timeout 300 python -m pytest tests/e2e/solute_ion/test_e2e_cli_zero_ion_export.py -q  →  2 passed; and RED was observed first with the documented grompp failure signature</verify>
  <done>0-ion CLI export: no ion.itp staged or included, grompp rc==0; ion-present export unchanged and grompp rc==0; both committed</done>
</task>

<task type="auto">
  <name>Task 2: Bug (b) — thread guest metadata into CLI hydrate export for mixed built-in guests (RED-first e2e)</name>
  <files>tests/e2e/hydrate/test_e2e_cli_mixed_builtin_hydrate_grompp.py, quickice/cli/pipeline.py, quickice/cli/itp_helpers.py</files>
  <action>
**Step 1 — RED test.** Create `tests/e2e/hydrate/test_e2e_cli_mixed_builtin_hydrate_grompp.py`:

- Module-scoped fixture `mixed_sii_hydrate()`: `HydrateStructureGenerator().generate(HydrateConfig(lattice_type="sII", guest_type="ch4", cage_guest_assignments={"small": CageGuestAssignment(guest_type="ch4", occupancy=100.0), "large": CageGuestAssignment(guest_type="thf", occupancy=100.0)}, supercell_x=2, supercell_y=2, supercell_z=2))`. 2×2×2 needed because sII 1×1×1 ≈ 1.73 nm < 2×rcoulomb (grompp box check — filled-ice Pitfall 1); 2×2×2 ≈ 3.46 nm passes (live-verified).
  Sanity asserts (live-verified empirical values, 42-00 precedent): `hydrate.guest_count == 192` (128 CH4 + 64 THF); `{"ch4","thf"} <= {d.mol_type for d in hydrate.guest_descriptors}`; `_derive_guest_atom_counts(hydrate.molecule_index, hydrate.guest_descriptors) == {"ch4": 5, "thf": 13}`. **If any fails, STOP and report.**
- Test `test_cli_mixed_builtin_hydrate_export_grompp(tmp_path, mixed_sii_hydrate)` with `@gmx_skipif`: `pipe = CLIPipeline(args=SimpleNamespace()); pipe._output_dir = ws; pipe._hydrate_result = hydrate` (only `_hydrate_result` → hydrate branch), `rc = pipe._run_export_step()`; assert `rc == 0`; then the CORRECT behavior (fails today):
  1. `.gro` residues (parse_gro_residue_names) contain BOTH "CH4_H" and "THF_H" — **today this fails first** (all 192 guests CH4_H)
  2. `parse_top_molecules`: `mols["CH4_H"] == 128`, `mols["THF_H"] == 64` (empirical sII 2×2×2 counts: 16 small + 8 large per cell × 8)
  3. both `(ws / "ch4_hydrate.itp")` and `(ws / "thf_hydrate.itp")` exist (thf not staged today)
  4. ion.top — i.e. hydrate.top — text `#include`s BOTH `"ch4_hydrate.itp"` and `"thf_hydrate.itp"`
  5. `assert_itp_completeness` + `assert_gro_top_consistent`
  6. grompp rc==0
  Helpers/imports identical to Task 1's file (plus HydrateStructureGenerator, HydrateConfig, CageGuestAssignment, `_derive_guest_atom_counts` from `quickice.structure_generation.types`). No PySide6/VTK.

**Step 2 — Run RED:** `timeout 300 python -m pytest tests/e2e/hydrate/test_e2e_cli_mixed_builtin_hydrate_grompp.py -q`
Expected: FAILS at assert 1 (THF_H missing from .gro residues; [molecules] shows `CH4_H 192`, only ch4_hydrate.itp staged — live-verified 2026-09-25). **If the failure does NOT match this documented cause, STOP and report — escalate via /gsd-debug for bug (b).**

**Step 3 — Fix (thread metadata into the existing path; the writers' mixed_builtin code already exists and needs no edits):**
- `quickice/cli/pipeline.py` hydrate branch (~lines 928-960): add `_derive_guest_atom_counts` to the existing `from quickice.structure_generation.types import (...)`; before the wrapper construction add
  `hydrate_descriptors = getattr(hydrate, "guest_descriptors", [])`
  and add TWO kwargs to the `InterfaceStructure(...)` constructor (after `guest_nmolecules=guest_nmolecules,`):
  ```python
  guest_descriptors=hydrate_descriptors,
  guest_atom_counts=_derive_guest_atom_counts(
      hydrate.molecule_index, hydrate_descriptors
  ),
  ```
  (Mirrors HydrateStructure.to_candidate()'s metadata derivation at types.py:1342 — same helper, same argument order. This activates write_interface_gro_file's mixed path at interface_writer.py:423-498 and write_interface_top_file's at 635-698/782-861/887-899. Live-verified to produce `[molecules] SOL 1088 / CH4_H 128 / THF_H 64` + both includes + grompp rc=0.)
- `quickice/cli/itp_helpers.py` hydrate branch built-in path (~lines 333-340): the .top now includes EVERY distinct built-in type, so stage them all. Replace the single `_resolve_guest_type_for_hydrate_step` call with:
  ```python
  from quickice.output.guest_info import _detect_builtin_guest_types
  from quickice.output.gromacs_writer import detect_guest_type_from_atoms
  guest_types = _detect_builtin_guest_types(structure, detect_guest_type_from_atoms)
  if not guest_types:
      # config-less / empty-index fallback — preserves today's single-type path
      _single = _resolve_guest_type_for_hydrate_step(structure, args_ref)
      guest_types = [_single] if _single else []
  for guest_type in guest_types:
      itp_name = _copy_hydrate_guest_itp(output_dir, guest_type)
      if itp_name:
          copied.append(itp_name)
  if not guest_types:
      logger.warning("Hydrate step but no guest type detected — skipping guest ITP")
  ```
  (Lazy imports inside the function per module style; `_detect_builtin_guest_types` walks the populated hydrate molecule_index — verified live it returns `["ch4", "thf"]`. For single-guest ch4 it returns `["ch4"]` → same staged file as today, byte-identical outcome.)
  Do NOT touch the custom branch above it (`config.is_custom_guest` path stays unchanged).

**Step 4 — Run GREEN:** same pytest command → 1 passed.
**Step 5 — Regression sweep:**
- `timeout 600 python -m pytest tests/e2e -q` (all e2e incl. filled-ice/triclinic single-guest CLI hydrate + mixed_ion — expect 0 failed)
- `timeout 600 python -m pytest tests/test_cli tests/test_output -q` (itp_helpers + writer units)
- Final gate (AGENTS.md): `QT_QPA_PLATFORM=offscreen timeout 900 python -m pytest -q` (~4 min; expect 0 failed; count 1846 → 1849: +2 Task-1 tests, +1 Task-2 test)
Commit atomically (stage only these 3 files):
`git add quickice/cli/pipeline.py quickice/cli/itp_helpers.py tests/e2e/hydrate/test_e2e_cli_mixed_builtin_hydrate_grompp.py`
`git commit -m "fix(029): thread guest metadata into CLI hydrate export for mixed built-in guests"`
  </action>
  <verify>timeout 300 python -m pytest tests/e2e/hydrate/test_e2e_cli_mixed_builtin_hydrate_grompp.py -q → 1 passed; then tests/e2e + tests/test_cli + tests/test_output sweeps 0 failed; RED was observed first with the documented mislabeling signature</verify>
  <done>Mixed built-in CLI hydrate export: CH4_H 128 + THF_H 64 in [molecules] matching .gro, both guest ITPs staged+included, grompp rc==0; single-guest exports unchanged; full suite green; committed</done>
</task>

</tasks>

<verification>
1. `timeout 300 python -m pytest tests/e2e/solute_ion/test_e2e_cli_zero_ion_export.py tests/e2e/hydrate/test_e2e_cli_mixed_builtin_hydrate_grompp.py -q` → 3 passed
2. `QT_QPA_PLATFORM=offscreen timeout 900 python -m pytest -q` → 0 failed (external timeout guard per AGENTS.md — pytest-timeout cannot interrupt C-level hangs)
3. `git log --oneline -3` shows exactly 2 atomic fix commits (test+fix per bug); no `git add .`/`-A`
</verification>

<success_criteria>
- Bug (a): 0-ion CLI export leaves NO ion.itp in the export dir and NO `#include "ion.itp"` in ion.top; grompp rc==0. Ion-present exports byte-identical to before (ion.itp staged + included, grompp rc==0).
- Bug (b): mixed built-in CLI hydrate export emits per-type [molecules] runs (CH4_H 128 / THF_H 64) matching the .gro, stages + includes both {ch4,thf}_hydrate.itp, grompp rc==0. Single-guest CLI hydrate path outcome unchanged.
- Both fixes reuse existing writer/staging machinery — no writer rewrites, no new dependencies, no hardcoded TIP4P-ICE/water constants.
- 3 new e2e tests pass; full suite green; work committed as 2 atomic commits.
</success_criteria>

<output>
After completion, create `.planning/quick/029-fix-cli-hydrate-export-0-ion-orphan-incl/029-SUMMARY.md`
</output>
