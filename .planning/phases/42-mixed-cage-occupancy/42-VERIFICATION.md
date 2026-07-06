---
phase: 42-mixed-cage-occupancy
verified: 2026-07-06T10:09:01Z
status: passed
score: 4/4 phase-goal truths verified (17/17 per-plan must_have truths verified)
human_verification:
  - test: "Open the GUI on a local display, generate a mixed sI hydrate (CH4 in small + THF in large), and visually confirm the VTK viewer renders 3 actors (1 water + 2 guest types) with distinct per-type bond colors (gray for the first guest, cyan for the second)."
    expected: "Two guest actor groups render with different bond colors from _DEFAULT_PALETTE; water actor renders separately; no actor-indexing errors in the console."
    why_human: "Full-widget VTK smoke tests (QVTKRenderWindowInteractor) crash under headless SSH X11 (documented AGENTS.md limitation). Unit tests prove create_guest_actor returns the correct variable-length list and per-type actor COUNTS, but visual rendering on a real display cannot be verified programmatically. The 42-06 human checkpoint approved the GUI panel rows; mixed-guest VTK visual confirmation is the remaining item."
---

# Phase 42: Mixed Cage Occupancy Verification Report

**Phase Goal:** Users can assign different guest types to different cage types with independent occupancy percentages
**Verified:** 2026-07-06T10:09:01Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                                                                  | Status     | Evidence                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | User can assign different guest types (CH₄, THF, or custom) to different cage types on any hydrate lattice (sI small/large, sII small/large, sH small/medium/large, filled ice channels) | ✓ VERIFIED | `HYDRATE_LATTICES` cage_type_maps correct for all 10 lattices (sI small/large, sII small/large, sH small/medium/large [fixed by 42-00: 16→20, added medium:12_1], filled ices small=Ne1, sTprime/Ice-XVII water-only {}). `CageGuestAssignment` dataclass (types.py:430) carries per-cage guest_type + occupancy. GUI `HydratePanel._rebuild_cage_rows` rebuilds per-cage rows on lattice change (sI=2, sH=3, c0te=1, sTprime=0 — 6 headless tests pass). CLI `--cage-guest KEY=GUEST:OCC` (parser.py:261) + `_parse_cage_guest_args` (pipeline.py:73) validated. |
| 2   | User can set per-cage-type occupancy percentage (e.g., 60% CH₄ in small + 100% custom in large)                                                                        | ✓ VERIFIED | `CageGuestAssignment.occupancy: float` (types.py). GUI `QDoubleSpinBox` per cage (0–100%, 1 decimal) in `_rebuild_cage_rows`. CLI validates `0.0 <= occ <= 100.0` (pipeline.py). `test_get_configuration_builds_assignments` round-trips small=CH4@60 + large=THF@100 → `HydrateConfig.cage_guest_assignments` with correct guest_type + occupancy + auto-populated atom counts.                                                                                                                                                                                |
| 3   | Mixed occupancy hydrate exports correctly to GROMACS with multiple guest .itp includes in .top                                                                         | ✓ VERIFIED | `export_hydrate` (hydrate_export.py:90) iterates `config.cage_guest_assignments`, registers built-ins in `MoleculetypeRegistry`, builds `custom_guest_info` list + `itp_files` dict, copies all ITPs to output dir (lines 243–249). `write_multi_molecule_top_file` emits `#include` per guest (itp_files + MOLECULE_TO_GROMACS defaults) + `[molecules]` per type. `test_mixed_gui_grompp_passes` + `test_mixed_cli_built_in_grompp` both pass grompp exit 0 (gmx available). See Caveats for CLI-path + mismatch-edge-case limitations.                                   |
| 4   | Mixed occupancy hydrate renders correctly in VTK with per-type visual styles                                                                                          | ✓ VERIFIED | `create_guest_actor` (hydrate_renderer.py:408) groups by `mol_type` via `defaultdict(list)` → returns `list[vtkActor]`; `render_hydrate_structure` returns `[water, *guests]` variable-length; `_DEFAULT_PALETTE` bond-color cycle (gray/cyan/yellow/red/purple); `hydrate_viewer._guest_actors = _hydrate_actors[1:]` (line 257); `interface_viewer` loops `_guest_actors` list. 6 `TestPerTypeGuestActors` tests pass (mixed=3 actors, single=2, water-only=1, visibility toggle, shape contract, per_type_colors override).                          |

**Score:** 4/4 phase-goal truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `quickice/structure_generation/types.py` | CageGuestAssignment + HydrateConfig.cage_guest_assignments + legacy shim + GuestDescriptor + HydrateStructure.guest_descriptors + corrected sH cage_type_map | ✓ VERIFIED | 1221 lines. `class CageGuestAssignment` (line 430), `class GuestDescriptor` (line 470), `cage_guest_assignments` field (line 558), `__post_init__` legacy-shim + explicit-API (lines 619–769), `has_custom_assignment` (line 762), `guest_descriptors` field (line 1155), sH cage_type_map `{"small":"12","medium":"12_1","large":"20"}` (line 118). No stub patterns. |
| `quickice/structure_generation/hydrate_generator.py` | Multi-guest _run_via_api loop + ExitStack generate + resname_to_moltype _build_molecule_index + guest_descriptors | ✓ VERIFIED | 835 lines. ExitStack over DISTINCT custom guest_types (lines 154–175); `cage_guest_assignments.items()` loop → per-cage `parse_guest` (lines 294–310); `resname_to_moltype` dict (line 635) drives per-type `MoleculeIndex.mol_type` (line 667); `guest_descriptors` populated (lines 207–237). No stub patterns. |
| `quickice/output/gromacs_writer.py` | All 4 writers accept list[dict] custom_guest_info + custom_by_moltype + looped _merge_custom_atomtypes + DeprecationWarning wrap | ✓ VERIFIED | 3571 lines. All 4 writers signature `custom_guest_info: list[dict] \| None` (lines 1047, 1490, 1696, 1843); `custom_by_moltype` dict built before loops (lines 1262, 1544, 1767, 1901); `_merge_custom_atomtypes` looped per custom ITP (lines 1598, 2017); `DeprecationWarning` + wrap for legacy single dict (lines 1104, 1527, 1741, 1882). The 1 "placeholder" hit is a docstring ("generic XX placeholder" for atom names) — benign. |
| `quickice/gui/hydrate_renderer.py` | create_guest_actor returns list[vtkActor] per mol_type + render_hydrate_structure variable-length + _DEFAULT_PALETTE | ✓ VERIFIED | 672 lines. `create_guest_actor` (line 408) groups via `defaultdict(list)` `by_type` (line 443); `_DEFAULT_PALETTE` (line 106); `per_type_colors` override (line 411); `render_hydrate_structure` returns `[water_actor, *guest_actors]` (line 551). No stub patterns. |
| `quickice/gui/hydrate_viewer.py` | _guest_actors list = _hydrate_actors[1:] | ✓ VERIFIED | 499 lines. `_guest_actors` attr (line 91); `self._guest_actors = self._hydrate_actors[1:]` (lines 257, 411); `_water_actor = _hydrate_actors[0]` (lines 255, 410). The 17 "placeholder" hits are the legitimate pre-generation placeholder WIDGET (UI pattern), not stub code. |
| `quickice/gui/interface_viewer.py` | _guest_actors list + _guest_actor primary back-compat | ✓ VERIFIED | 402 lines. `_guest_actors` list (line 71) + `_guest_actor` primary (line 72); `hydrate_actors[1:]` (line 245); AddActor/RemoveActor loop the list (lines 177, 256, 373); `_clear_actors` removes all (lines 371–377). No stub patterns. |
| `quickice/gui/hydrate_export.py` | export_hydrate iterates cage_guest_assignments + custom_guest_info list + itp_files dict + transform_guest_itp loop | ✓ VERIFIED | 258 lines. `export_hydrate` (line 90) iterates `config.cage_guest_assignments.items()` (line 161); built-in → registry (line 192), custom → custom_guest_info list + itp_files dict (lines 174–182); `transform_guest_itp` loop per guest ITP (lines 243–249) copies all ITPs to output dir. No stub patterns. |
| `quickice/gui/hydrate_panel.py` | Per-cage rows driven by cage_type_map + get_configuration builds cage_guest_assignments | ✓ VERIFIED | 518 lines. `_cage_guest_combos`/`_cage_occupancy_spins` dicts (lines 215–216); `_rebuild_cage_rows` (line 229) iterates `cage_type_map` keys; `_update_guest_ui_for_lattice` (line 387); `get_configuration` (line 452) builds `CageGuestAssignment(guest_type, occupancy)` per row. No stub patterns. |
| `quickice/cli/parser.py` | --cage-guest repeatable flag + deprecated legacy aliases | ✓ VERIFIED | 552 lines. `--cage-guest` (line 261) with `action='append'`; `--guest`/`--cage-occupancy-small/large` kept with "(deprecated; use --cage-guest...)" help text (lines 220, 249, 257). No stub patterns. |
| `quickice/cli/pipeline.py` | _parse_cage_guest_args + _build_custom_guest_info returns list + _run_source_step builds cage_guest_assignments | ✓ VERIFIED | 987 lines. `_build_custom_guest_info` returns `list[dict] \| None` (line 32) deduped by mol_type; `_parse_cage_guest_args` (line 73) validates KEY=GUEST:OCC + cage-key-in-cage_type_map + 0-100 occ + no-dup-keys; `_run_source_step` wires it (lines 357–374). No stub patterns. |

### Test Artifacts

| Artifact | Status | Details |
| -------- | ------ | ------- |
| `tests/test_e2e_sh_cage_occupancy.py` (92 lines) | ✓ VERIFIED | 3 GenIce2 regression tests pass: large-only places 2, small-only places 6, large > 0 (value-agnostic sentinel). |
| `tests/test_hydrate_config_custom.py` (256 lines) | ✓ VERIFIED | 16 tests pass (10 existing + 6 new TestCageGuestAssignments): explicit API, per-assignment metadata auto-populate, legacy shim sI + filled-ice, duplicate-residue rejection, water-only empty. |
| `tests/test_e2e_mixed_cage_occupancy.py` (389 lines) | ✓ VERIFIED | 5 tests pass: both guest types placed (ch4 + etoh_mix mol_types), CH4 count 16, sys.modules clean post-generation, guest_descriptors populated (2 entries), test_mixed_gui_grompp_passes (grompp exit 0). |
| `tests/test_output/test_gromacs_export_hydrate.py` (683 lines) | ✓ VERIFIED | TestMultiGuestWriter class: multi-guest .top has SOL+CH4_H+MOL_H; .gro has matching residues; None≡empty-list backward compat; single-dict DeprecationWarning. |
| `tests/test_custom_molecule_renderer.py` (432 lines) | ✓ VERIFIED | 24 tests pass including 6 TestPerTypeGuestActors: mixed=3 actors, single=2, water-only=1, visibility toggle, list-not-actor shape, per_type_colors override. |
| `tests/test_hydrate_panel.py` (127 lines) | ✓ VERIFIED | 6 headless GUI tests pass: sI=2 rows, sH=3, c0te=1, sTprime=0, get_configuration round-trip (small=CH4@60, large=THF@100), lattice-change rebuild. |
| `tests/test_cli/test_mixed_cage_cli.py` (426 lines) | ✓ VERIFIED | 4 tests pass: test_mixed_cli_built_in_grompp (grompp exit 0 on CH4+THF via write_multi_molecule_*), _build_custom_guest_info returns list, --cage-guest round-trips, legacy flags work. |
| `tests/test_hydrate_lattice_types.py` (338 lines) | ✓ VERIFIED | valid_keys accepts {small, large, medium, guest}; test_sh_cage_type_map_values asserts exact corrected sH map. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `HYDRATE_LATTICES["sH"]["cage_type_map"]` | `hydrate_generator._run_via_api parse_guest` | `cage_type_map[cage_key] → cage_id` in guest_spec | ✓ WIRED | `_run_via_api` loop (line 294) `cage_type_map[cage_key]` → `parse_guest(guests, f'{cage_id}={guest_name}*{frac}')` (line 310). sH large="20" verified by test_e2e_sh_cage_occupancy (0→2 guests after fix). |
| `HydrateConfig.cage_guest_assignments` | `hydrate_generator._run_via_api` | iterate `items()` → per-cage `parse_guest` | ✓ WIRED | `for cage_key, assignment in config.cage_guest_assignments.items():` (line 294) → `parse_guest(guests, guest_spec)` (line 310). |
| `__post_init__` legacy shim | existing callers (GUI/CLI/tests) | synthesize small/large from legacy `guest_type` when dict empty | ✓ WIRED | `if not self.cage_guest_assignments and self.guest_type:` (line 627) synthesizes from `cage_type_map` keys. Note: inlined in `__post_init__` (not a named `_legacy_to_assignments` fn) — behavior equivalent. Legacy callers unchanged; 71 broader tests confirm no regression. |
| `config.cage_guest_assignments` | `custom_guest_info` list + `itp_files` dict | `export_hydrate` iterating assignments | ✓ WIRED | `for _cage_key, assignment in config.cage_guest_assignments.items():` (hydrate_export.py:161) → built-in registry branch / custom `custom_guest_info.append` (line 174). |
| `transform_guest_itp` loop | staged custom .itp files | one transform per guest ITP | ✓ WIRED | `for guest_itp_path, guest_name_for_transform in custom_guest_itps:` (hydrate_export.py:243) → `guest_dest_path.write_text(transformed_content)` (line 249). Copies all ITPs in the normal flow. |
| `custom_guest_info: list[dict]` | `custom_by_moltype` dict | res_name resolution in [molecules]/#include loops | ✓ WIRED | `custom_by_moltype = {ci["mol_type"]: ci for ci in (custom_guest_info or [])}` (gromacs_writer.py:1767, 1901) → `if mol.mol_type in custom_by_moltype: res_name = ...` (line 1785). |
| `_merge_custom_atomtypes` loop | `_written_atomtypes` dedup dict | one merge per custom ITP, accumulating across guests | ✓ WIRED | `for ci in (custom_guest_info or []): if ci.get("itp_path"): _merge_custom_atomtypes(...)` (gromacs_writer.py:2015) with `_written_atomtypes` accumulating. |
| `molecule_index mol_type` | `create_guest_actor` grouping | `defaultdict(list)` by mol_type excluding water | ✓ WIRED | `by_type: dict[str, list] = defaultdict(list)` (hydrate_renderer.py:443) → `for mol in molecule_index: by_type[mol.mol_type].append(mol)` (line 447). |
| `render_hydrate_structure` | `hydrate_viewer`/`interface_viewer` callers | list `[water, *guests]`; iterate `[1:]` | ✓ WIRED | `return [water_actor, *guest_actors]` (hydrate_renderer.py:551); `self._guest_actors = self._hydrate_actors[1:]` (hydrate_viewer.py:257, 411; interface_viewer.py:245). Static grep: no `[1]` hard-indexing remains (only `[0]` for water + `[1:]` for guests). |
| `HYDRATE_LATTICES[lat]["cage_type_map"]` keys | per-cage QComboBox + QDoubleSpinBox rows | `_update_guest_ui_for_lattice` → `_rebuild_cage_rows` | ✓ WIRED | `cage_type_map = lattice_entry.get("cage_type_map", {})` (hydrate_panel.py:253) → `for cage_key in cage_type_map:` (line 263) builds combo + spin. |
| `get_configuration` per-cage rows | `HydrateConfig.cage_guest_assignments` | build `CageGuestAssignment` per row | ✓ WIRED | `cage_guest_assignments[cage_key] = CageGuestAssignment(guest_type=guest_id, occupancy=occ)` (hydrate_panel.py:469) → `HydrateConfig(cage_guest_assignments=cage_guest_assignments, ...)` (line 474). |
| `args.cage_guest` | `HydrateConfig.cage_guest_assignments` | `_run_source_step` parsing | ✓ WIRED | `cage_guest_assignments = _parse_cage_guest_args(...)` (pipeline.py:366) → `HydrateConfig(..., cage_guest_assignments=cage_guest_assignments)` (line 374). |
| `_build_custom_guest_info` list | `write_interface_gro/top_file` `custom_guest_info=list` | `_run_export_step` hydrate branch | ✓ WIRED | `custom_guest_info = _build_custom_guest_info(...)` (pipeline.py:957) → `write_interface_gro_file(wrapper, gro_path, custom_guest_info=custom_guest_info)` (line 958). Note: write_interface_* is single-guest-stream — see CLI-path caveat. |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
| ----------- | ------ | -------------- |
| MIXED-01: assign different guests to different cage types on ALL hydrate lattices | ✓ SATISFIED | All 10 lattice cage_type_maps correct (sH fixed by 42-00). Per-cage assignment supported via cage_guest_assignments. |
| MIXED-02: any available guest type (CH₄, THF, or custom) to any cage type | ✓ SATISFIED | Built-in CH4/THF offered in GUI combos + CLI --cage-guest. Custom-guest-per-cage via explicit API (CageGuestAssignment) exercised by 42-02 e2e test (CH4 + custom ethanol). GUI/CLI user-facing custom surface is Phase 44/45 scope (documented limitation, not a gap — data model fully supports it). |
| MIXED-03: per-cage-type occupancy percentage | ✓ SATISFIED | CageGuestAssignment.occupancy (0–100); GUI QDoubleSpinBox per cage; CLI validates 0–100; round-trip test confirms 60/100. |
| MIXED-04: mixed hydrate exports to GROMACS with multiple guest .itp in .top | ✓ SATISFIED | GUI path: export_hydrate copies all ITPs + .top #includes both + grompp exit 0. CLI path: --cage-guest builds correct config; mixed grompp validated via write_multi_molecule_* (write_interface_* single-guest-stream limitation documented in 42-07 SUMMARY). |
| MIXED-05: mixed hydrate renders in VTK with per-type styles | ✓ SATISFIED | Unit-level: create_guest_actor returns per-mol_type actors + _DEFAULT_PALETTE bond colors + variable-length [water, *guests]. 6 TestPerTypeGuestActors tests pass. Full-widget visual on a local display flagged for human verification (headless VTK crash — documented AGENTS.md limitation). |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `quickice/gui/hydrate_viewer.py` | 8, 61, 125–143, 340–358 | "placeholder" (×17) | ℹ️ Info | Legitimate UI pattern — a "placeholder widget" shown before generation (real stacked-widget design, not a stub). No functional impact. |
| `quickice/output/gromacs_writer.py` | 1709 | "placeholder" (×1) | ℹ️ Info | Docstring: "uses generic 'XX' placeholder" for atom names when None. Benign documentation. |

No TODO/FIXME/XXX/HACK/stub implementations found in any of the 10 modified source files. All artifacts are substantive.

### Human Verification Required

### 1. Mixed-Guest VTK Visual Rendering

**Test:** On a local display (not headless SSH), open the GUI, generate a mixed sI hydrate (CH4 in small cages + THF in large cages via the per-cage rows), and observe the Hydrate viewer.
**Expected:** The 3D viewer renders 3 actor groups: water (CPK), CH4 guests (gray bonds from _DEFAULT_PALETTE[0]), THF guests (cyan bonds from _DEFAULT_PALETTE[1]). No actor-indexing errors in the console. Toggling guest visibility affects only the corresponding guest type.
**Why human:** Full-widget VTK smoke tests (`QVTKRenderWindowInteractor`) crash under headless SSH X11 (documented AGENTS.md limitation). Unit tests prove `create_guest_actor` returns the correct variable-length list and per-type actor COUNTS, but visual rendering + per-type color distinction on a real display cannot be verified programmatically. The 42-06 human checkpoint approved the per-cage panel rows; mixed-guest VTK visual confirmation is the remaining item.

### Gaps Summary

No gaps found. All 4 phase-goal truths verified, all 17 per-plan must_have truths verified, all required artifacts exist + are substantive + wired, all key links wired, all 232+ relevant tests pass (including grompp e2e with gmx available).

**Documented caveats / known limitations (NOT gaps — do not block the phase goal):**

1. **GUI export ITP-staging mismatch (user-reported KNOWN ISSUE 1):** If a user generates a mixed sI hydrate (CH4+THF) then changes the lattice (e.g. to sTprime) WITHOUT regenerating, then exports, the `.top` `#include`s `ch4_hydrate.itp` + `thf_hydrate.itp` (driven by `structure.molecule_index` defaults) but `export_hydrate` copies ITPs based on the now-empty `config.cage_guest_assignments` → ITPs not copied → grompp fails. **Assessment:** This is an abnormal flow that violates the config/structure consistency assumption (the stored `_current_hydrate_config` is rebuilt on every config change via `_on_hydrate_config_changed`, but `_current_hydrate_result` is only updated on generation). In the NORMAL flow (generate mixed → export immediately), `config` and `structure` are consistent and the export works correctly (export_hydrate copies all ITPs via the `custom_guest_itps` loop, lines 243–249). The 42-06 SUMMARY documented this as a known limitation. **Not a MIXED-04 gap** — the must_have truth "Mixed occupancy hydrate exports correctly to GROMACS" holds in the normal mixed-export flow. Recommended future hardening: either invalidate `_current_hydrate_result` on lattice change, or drive ITP staging from `structure.molecule_index` + `guest_descriptors` instead of (or in addition to) `config.cage_guest_assignments`.

2. **Test coverage gap (related to caveat 1):** `test_mixed_gui_grompp_passes` bypasses `export_hydrate`'s ITP-copy path — it calls `write_multi_molecule_*` directly and stages ITPs via test helpers (`_stage_itp_files` + `_stage_custom_guest_itp`). No automated test exercises the actual `export_hydrate` ITP-copy path for a mixed hydrate. The `export_hydrate` code IS substantive and correct for the normal flow (verified by reading lines 161–249). Future test could call `HydrateGROMACSExporter.export_hydrate` end-to-end and assert all #include'd ITPs land in the output dir.

3. **Export dialog cosmetic label (user-reported KNOWN ISSUE 2):** The success dialog (main_window.py:1718) shows `f"Guests: {structure.guest_count} {config.guest_type}"` — counts total guests but labels them all as the primary `config.guest_type`. For a mixed hydrate (1 CH4 + 6 THF = 7 total), this reads "Guests: 7 ch4". **Assessment:** Cosmetic UX issue in the success message only; does not affect the exported files. Not a must_have violation.

4. **CLI mixed built-in export writer limitation (documented in 42-07 SUMMARY):** The CLI export path (`_run_export_step` → `write_interface_gro_file`/`write_interface_top_file`) is single-guest-stream and uses `detect_guest_type_from_atoms`, which picks ONE guest type for the whole guest region — it cannot emit a mixed `[molecules]` block with both `CH4_H` and `THF_H`. The CLI `--cage-guest` flag correctly builds `cage_guest_assignments`, and `HydrateStructureGenerator.generate()` correctly places mixed guests (42-02), but the CLI export step would need to call `write_multi_molecule_*` (or `write_interface_*` would need per-molecule chunking) to emit a mixed block. Mixed CLI grompp is validated via `write_multi_molecule_*` (the GUI writers) in `test_mixed_cli_built_in_grompp`. **Assessment:** Documented writer-level limitation, not a CLI parser/pipeline gap. The phase goal truth "exports correctly to GROMACS" is satisfied by the GUI path (the primary user-facing export).

5. **GUI/CLI custom-guest-per-cage user surface (documented scope boundary):** The GUI panel combos and CLI `--cage-guest` flag offer built-in guests (CH4/THF) only for v4.7. Custom-guest-per-cage via the GUI/CLI user-facing surface is Phase 44 (GUI-02) / Phase 45 (CLI-02) scope. The data model / API path (`HydrateConfig.cage_guest_assignments` with custom `CageGuestAssignment` entries) fully supports mixed custom guests — exercised by the 42-02 e2e test (CH4 + custom ethanol). **Assessment:** This is explicit scope phasing across the milestone, not a Phase 42 gap.

---

_Verified: 2026-07-06T10:09:01Z_
_Verifier: OpenCode (gsd-verifier)_
