# Roadmap: QuickIce

## Milestones

- ✅ **v1.0 MVP** - Phases 1-7 (shipped 2026-03-29)
- ✅ **v1.1 Hotfix** - Phase 7 (shipped 2026-03-31)
- ✅ **v2.0 GUI** - Phases 8-13 (shipped 2026-04-04)
- ✅ **v2.1 GROMACS Export** - Phase 14 (shipped 2026-04-07)
- ✅ **v2.1.1 Phase Diagram Data** - Phase 15 (shipped 2026-04-08)
- ✅ **v3.0 Interface Generation** - Phases 16-21 (shipped 2026-04-11)
- ✅ **v3.5 Interface Enhancements** - Phases 22-27 (shipped 2026-04-13)
- ✅ **v4.0 Molecule Insertion** - Phases 28-31.2 (shipped 2026-05-01)
- ✅ **v4.5 Solute & Custom Molecule** - Phases 32-37.2 (shipped 2026-06-27)
- 🚧 **v4.7 Extended Hydrate Generation** - Phases 38-48 (in progress)

## Overview

v4.7 extends QuickIce's hydrate generation from 3 lattices with 2 guest types (sI/sII/sH + CH₄/THF) to support filled ice structures, custom guest molecules via GenIce2 bridge, mixed cage occupancy, and depol mode. The pipeline is refactored from pattern-matching to metadata-driven molecule identification, enabling custom guests and fixing the P3 export issue. All features are exposed in both GUI and CLI paths.

## Phases

### 🚧 v4.7 Extended Hydrate Generation (In Progress)

**Milestone Goal:** Extend hydrate generation with filled ices, custom guest molecules via GenIce2 bridge, mixed cage occupancy, and depol mode — with metadata-driven pipeline and valid GROMACS export

#### Phase 38: Internal Pipeline Refactor
**Goal**: Pipeline identifies molecules by metadata (not atom-name pattern matching) and validates format constraints at write time
**Depends on**: Nothing (first v4.7 phase, builds on v4.5 shipped code)
**Requirements**: PIPE-01, PIPE-02, PIPE-03, PIPE-04
**Success Criteria** (what must be TRUE):
  1. `_build_molecule_index` identifies molecules from HydrateConfig guest metadata (name, atom labels, atom count) instead of pattern matching on atom/residue names
  2. HydrateConfig carries guest metadata (name, atom labels, atom count, ITP path) through the generation→export pipeline
  3. GRO writer rejects residue names >5 chars with a clear error instead of silently corrupting the fixed-width format
  4. ITP transformation pipeline applies _H suffix, comments out atomtypes section, and rewrites residue names for custom guests
**Plans:** 4 plans

Plans:
- [x] 38-01: Extend GUEST_MOLECULES + HydrateConfig/HydrateStructure with guest metadata (PIPE-02)
- [x] 38-02: Refactor _build_molecule_index for metadata-driven identification (PIPE-01)
- [x] 38-03: Add GRO residue name validation at all write points (PIPE-03)
- [x] 38-04: Build ITP transformation pipeline (_H suffix, atomtypes, residue rewrite) (PIPE-04)

#### Phase 39: Extended Lattice Types
**Goal**: Users can generate structures for all new lattice types, and triclinic filled ices are blocked for interface generation
**Depends on**: Phase 38 (HydrateConfig extension needed for new lattice config fields)
**Requirements**: LATTICE-01, LATTICE-02, LATTICE-03, LATTICE-04, LATTICE-05, LATTICE-06, LATTICE-07, LATTICE-08, LATTICE-09
**Success Criteria** (what must be TRUE):
  1. User can select any of C0 (c0te), C1 (c1te), C2 (c2te), Ih (ice1hte), sT' (sTprime), Ice XVI (16), Ice XVII (17) as a hydrate lattice type
  2. Attempting interface generation with triclinic filled ices (C0, C1) produces a clear error message (same pattern as Ice II blocking)
  3. Filled ice lattices place guests via the `parse_guest` code path (NOT spot_guests — crashes with IndexError per RESEARCH.md)
  4. sT' and Ice XVII generate water-only structures with guest UI disabled
**Plans:** 5 plans

Plans:
- [x] 39-01-PLAN.md — Extend HYDRATE_LATTICES data model with 7 new entries + cage_type_map/is_triclinic/is_water_only
- [x] 39-02-PLAN.md — Rewrite generator cage routing with cage_type_map-driven parse_guest
- [x] 39-03-PLAN.md — Triclinic C0/C1 blocking for interface + CLI lattice type choices
- [x] 39-04-PLAN.md — GUI hydrate panel water-only guest toggling + info display
- [x] 39-05-PLAN.md — Unit tests for extended lattice types

#### Phase 40: Custom Guest Bridge Core
**Goal**: Users can upload a custom guest molecule and have it placed in hydrate cage positions via GenIce2
**Depends on**: Phase 38 (metadata-driven molecule index, ITP transformation), Phase 39 (lattice types for cage targeting)
**Requirements**: GUEST-01, GUEST-02, GUEST-03, GUEST-04, GUEST-05, GUEST-06, GUEST-07, GUEST-08, GUEST-09, GUEST-10
**Success Criteria** (what must be TRUE):
  1. User can upload a .gro+.itp pair and generate a hydrate structure with the custom molecule placed in specified cage positions
  2. QuickIce rejects custom guest residue names >3 chars with a specific error message (GRO 5-char limit with _H suffix)
  3. QuickIce rejects ITP files with comb-rule=1 with a specific error message (must be Lorentz-Berthelot)
  4. Custom guest is registered in sys.modules on the main thread before HydrateWorker starts (thread-safe)
  5. sys.modules injection is cleaned up after generation completes (no stale module pollution)
**Plans:** 5 plans

Plans:
- [x] 40-01-PLAN.md — ITP comb-rule parser + test fixtures (GUEST-07 foundation)
- [x] 40-02-PLAN.md — [ atoms ] resname rewrite in transform_guest_itp (deferred 38-04)
- [x] 40-03-PLAN.md — HydrateConfig extension for custom guests (guest_residue_name, guest_gro_path, is_custom_guest)
- [x] 40-04-PLAN.md — Custom guest bridge: build + validate + inject + cleanup (custom_guest_bridge.py)
- [x] 40-05-PLAN.md — Integrate bridge into hydrate generator + E2E test

#### Phase 41: GROMACS Export for Custom Guests
**Goal**: Custom guest hydrate structures export to valid GROMACS input files that pass grompp
**Depends on**: Phase 38 (metadata pipeline, P3 fix), Phase 40 (custom guest types exist)
**Requirements**: EXPORT-01, EXPORT-02, EXPORT-03, EXPORT-04, EXPORT-05, EXPORT-06
**Success Criteria** (what must be TRUE):
  1. Custom guest appears in .top with correct _H suffix moleculetype name
  2. Custom guest atomtypes are commented out in the bundled .itp and merged into main .top [atomtypes] with deduplication
  3. GRO export writes correct ≤5-char residue name for custom guest (with _H suffix)
  4. GROMACS grompp validates successfully on exported custom guest hydrate structures
**Plans**: 11 plans

Plans:
- [x] 41-01-PLAN.md — Extract `_merge_custom_atomtypes` shared helper (TDD, EXPORT-03 primitive)
- [x] 41-02-PLAN.md — `write_multi_molecule_gro_file` custom guest residue name `_H` (GUI GRO, EXPORT-04)
- [x] 41-03-PLAN.md — `write_multi_molecule_top_file` custom residue name + atomtypes merge (GUI TOP, EXPORT-01/03)
- [x] 41-04-PLAN.md — `write_interface_gro_file` P3 fix — metadata-driven custom guest (CLI GRO, EXPORT-04/05)
- [x] 41-05-PLAN.md — `write_interface_top_file` P3 fix — merge + #include + [molecules] (CLI TOP, EXPORT-01/03/05)
- [x] 41-06-PLAN.md — GUI `export_hydrate` is_custom_guest branch (guest_itp_path, guest_residue_name, custom_guest_info) + content e2e test (EXPORT-01/02/04)
- [x] 41-07-PLAN.md — CLI `copy_custom_guest_itp` + custom routing in itp_helpers (EXPORT-02, CLI ITP provisioning)
- [x] 41-08-PLAN.md — CLI `_run_export_step` threads `custom_guest_info` + content e2e test (EXPORT-01/04/05)
- [x] 41-09-PLAN.md — `_stage_custom_guest_itp` transformed-ITP staging test helper (EXPORT-06 enablement)
- [x] 41-10-PLAN.md — GUI grompp e2e validation (EXPORT-06, GUI path)
- [x] 41-11-PLAN.md — CLI grompp e2e validation (EXPORT-06, CLI path)

#### Phase 42: Mixed Cage Occupancy
**Goal**: Users can assign different guest types to different cage types with independent occupancy percentages
**Depends on**: Phase 39 (lattice types with cage type mappings), Phase 40 (custom guest available as guest type option)
**Requirements**: MIXED-01, MIXED-02, MIXED-03, MIXED-04, MIXED-05
**Success Criteria** (what must be TRUE):
  1. User can assign different guest types (CH₄, THF, or custom) to different cage types on any hydrate lattice (sI small/large, sII small/large, sH small/medium/large, filled ice channels)
  2. User can set per-cage-type occupancy percentage (e.g., 60% CH₄ in small cages + 100% custom in large cages)
  3. Mixed occupancy hydrate exports correctly to GROMACS with multiple guest .itp includes in .top
  4. Mixed occupancy hydrate renders correctly in VTK with per-type visual styles
**Plans:** 8 plans

Plans:
- [x] 42-00-PLAN.md — Fix sH cage_type_map bug (prerequisite: large→20, add medium→12_1)
- [x] 42-01-PLAN.md — Data model: CageGuestAssignment + HydrateConfig.cage_guest_assignments + legacy shim + HydrateStructure.guest_descriptors (MIXED-01/02/03 foundation)
- [x] 42-02-PLAN.md — Generator: multi-guest _run_via_api loop + ExitStack + _build_molecule_index (MIXED-01/02/03 generation)
- [x] 42-03-PLAN.md — GROMACS writers: list[dict] custom_guest_info across 4 writers + looped atomtypes merge (MIXED-04)
- [x] 42-04-PLAN.md — VTK per-type rendering: create_guest_actor list + variable-length render + caller updates (MIXED-05)
- [x] 42-05-PLAN.md — GUI export glue: export_hydrate builds list + loops transform_guest_itp + mixed grompp e2e (MIXED-04 GUI)
- [x] 42-06-PLAN.md — GUI per-cage-type controls: hydrate_panel rows + get_configuration builds cage_guest_assignments (MIXED-01/02/03 GUI)
- [x] 42-07-PLAN.md — CLI surface: --cage-guest repeatable flag + pipeline build config + CLI mixed grompp e2e (MIXED-01/02/03/04 CLI)

#### Phase 43: Depol Mode
**Goal**: Users can select depol mode for hydrate generation, with strict as the safe default
**Depends on**: Phase 38 (HydrateConfig extension)
**Requirements**: DEPOL-01, DEPOL-02, DEPOL-03
**Success Criteria** (what must be TRUE):
  1. User can select depol mode (strict/optimal) in the Hydrate tab
  2. Depol mode is passed through to GenIce2 generate_ice() call
  3. Default depol mode is 'strict' (preserves current behavior for existing users)
**Plans**: 2 plans

Plans:
- [x] 43-01-PLAN.md — HydrateConfig depol_mode field + generator passthrough + tests
- [x] 43-02-PLAN.md — GUI depol mode selector (QComboBox) + get_configuration wiring + headless tests

#### Phase 44: GUI Integration
**Goal**: All new hydrate features are accessible from the Hydrate tab with validation feedback
**Depends on**: Phase 39 (lattice types), Phase 40 (custom guest bridge), Phase 42 (mixed occupancy), Phase 43 (depol mode)
**Requirements**: GUI-01, GUI-02, GUI-03, GUI-04, GUI-05, GUI-06
**Success Criteria** (what must be TRUE):
  1. Hydrate tab lattice dropdown includes all new lattice types (filled ices + Ice XVI/XVII + sT')
  2. User can upload a custom guest .gro+.itp pair from the Hydrate tab and see specific validation errors (name too long, wrong comb-rule, unparseable)
  3. Hydrate tab has cage-type guest assignment controls (small/large/medium → guest type) for mixed occupancy
  4. Hydrate tab has depol mode dropdown (strict/optimal) with strict as default
**Plans**: 1 plan (3 of 4 original stubs already satisfied by prior vertical-slice phases; only custom-guest upload remains)

Plans:
- [x] 44-01: Add new lattice types to Hydrate tab dropdown — **DONE in 39-04** (`hydrate_panel.py:178` iterates `HYDRATE_LATTICES` for all 10 types; `test_hydrate_panel.py` covers c0te/sTprime). Satisfies **GUI-01**.
- [x] 44-02: Custom guest upload panel in Hydrate tab (.gro + .itp QFileDialog + validation feedback) — **DONE**. Covers **GUI-02 + GUI-05**. Also unblocks **GUI-06** (custom-per-cage via existing 42-06 row infra; built-in-only limit was the documented 42-06 known limitation).
- [x] 44-03: Mixed occupancy per-cage-type guest/occupancy controls — **DONE in 42-06** (`_rebuild_cage_rows` + per-cage combos/spinners; built-in guests only — custom-per-cage is gated on 44-02). Satisfies **GUI-03** (built-in path) + **GUI-06** (built-in path).
- [x] 44-04: Depol mode dropdown + HydrateWorker config passthrough — **DONE in 43-02** (`depol_combo` QComboBox strict/optimal + `get_configuration` passthrough; 43-02-SUMMARY explicitly notes "Phase 44 #4 references this as already-integrated — do NOT double-build"). Satisfies **GUI-04**.

#### Phase 44.1: Wire Custom Guest Through All Tabs Like Standard Hydrate (INSERTED)

**Goal**: Custom guest hydrate flows through the Interface tab and exports valid GROMACS output like a standard (built-in) hydrate, and the Pitfall 6 engine over-restriction is relaxed so the same custom guest can be assigned to multiple cages (aggregating like ch4).
**Depends on**: Phase 44 (GUI custom guest upload panel done; issues discovered during 44-02 human-verify checkpoint)
**Plans:** 22 plans

Plans:
- [x] 44.1-01-PLAN.md — Pitfall 6 engine relaxation (track residue_name→guest_type; reject only different guest_types)
- [x] 44.1-02-PLAN.md — to_candidate() carries guest_descriptors + guest_atom_counts in metadata
- [x] 44.1-03-PLAN.md — count_guest_atoms accepts guest_atom_count for custom guests
- [x] 44.1-04-PLAN.md — Move _build_custom_guest_info to neutral quickice/output/guest_info.py
- [x] 44.1-05-PLAN.md — slab.py threads guest_atom_count from candidate metadata
- [x] 44.1-06-PLAN.md — pocket.py threads guest_atom_count from candidate metadata
- [x] 44.1-07-PLAN.md — piece.py threads guest_atom_count from candidate metadata
- [x] 44.1-08-PLAN.md — Shared _stage_hydrate_guest_itps helper (DRY across 4 exporters)
- [x] 44.1-09-PLAN.md — GUI InterfaceGROMACSExporter threads custom_guest_info + ITP staging
- [x] 44.1-10-PLAN.md — GUI MainWindow interface export handler passes hydrate_config
- [x] 44.1-11-PLAN.md — GUI SoluteGROMACSExporter + extend write_solute_top/gro_file with custom_guest_info
- [x] 44.1-12-PLAN.md — GUI MainWindow solute export handler passes hydrate_config
- [x] 44.1-13-PLAN.md — GUI CustomMoleculeGROMACSExporter + extend write_custom_molecule_top/gro_file
- [x] 44.1-14-PLAN.md — GUI MainWindow custom-molecule export handler passes hydrate_config
- [x] 44.1-15-PLAN.md — GUI IonGROMACSExporter + extend write_ion_top/gro_file with custom_guest_info
- [x] 44.1-16-PLAN.md — GUI MainWindow ion export handler passes hydrate_config
- [x] 44.1-17-PLAN.md — CLI interface/custom/solute/ion export branches thread custom_guest_info + itp_helpers
- [x] 44.1-18-PLAN.md — Remove 44-02 _enforce_single_custom_cage auto-clear (engine now allows 2 cages)
- [x] 44.1-19-PLAN.md — Full e2e (GUI): custom guest → interface → solute → ion → export grompp
- [x] 44.1-20-PLAN.md — Full e2e (CLI): custom guest → all export branches grompp
- [x] 44.1-21-PLAN.md — Full e2e: same custom guest in 2 cages (Pitfall 6 relaxation) → grompp
- [x] 44.1-22-PLAN.md — Regression guard: built-in ch4 + thf through ALL tabs (GUI + CLI)

**Details:**
Two issues discovered during Phase 44-02 human-verify checkpoint (user-generated custom guest hydrate → Interface tab → export):

1. **Pitfall 6 engine over-restriction** (`quickice/structure_generation/types.py:711-720`): `HydrateConfig.__post_init__` rejects duplicate `guest_residue_name` across custom cage assignments, but checks residue name alone — not `(guest_type, guest_residue_name)`. This blocks the SAFE case (same custom guest in 2 cages, which aggregates to one `MOL_H` moleculetype exactly like ch4-in-all-cages) while correctly blocking the UNSAFE case (two different custom guests sharing the same residue name). Fix: track `guest_residue_name → guest_type`; only raise when a *different* `guest_type` claims an already-seen residue name. ~3-line change. This lets the 44-02 GUI auto-revert mitigation be removed/relaxed (single custom guest can occupy multiple cages like ch4).

2. **Interface tab custom guest export broken** (two parts):
   - **(a)** `quickice/structure_generation/types.py:1168` `HydrateStructure.to_candidate()` carries `guest_type_counts` in metadata but DROPS the `CageGuestAssignment` descriptor fields (residue_name, gro_path, itp_path, atom_labels, atom_count). When a hydrate becomes an interface template, the custom guest info is lost.
   - **(b)** `quickice/gui/export.py:901-965` `InterfaceGROMACSExporter.export_interface_gromacs()` calls `write_interface_gro_file`/`write_interface_top_file` with NO `custom_guest_info` kwarg (export.py:942-947) — the Phase 41-04/41-05 custom path never fires. It instead uses the old `_detect_guest_type_from_structure` heuristic (export.py:959) which returns `None` for custom guests → no ITP staged, no atomtypes merged, wrong/missing residue name → broken `.top`.
   - **Fix:** mirror the 42-08 pattern — `to_candidate()` carries custom guest descriptors (or the exporter reconstructs `custom_guest_info` from the interface structure's `guest_descriptors` + the original `HydrateConfig`); `export_interface_gromacs` threads `custom_guest_info` to both interface writers using the structure-driven ITP staging approach.

**Scope note:** Phase 44 goal ("Hydrate tab") is COMPLETE — these are cross-tab concerns that predates Phase 44 (the Interface export path was never wired for custom guests in any phase). Marked INSERTED/URGENT because the user hit this immediately during 44-02 acceptance testing.

#### Phase 45: E2E Hydrate Tab Workflow (redefined from CLI Integration)
**Goal**: Prove that ALL GUI tabs (Ice → Hydrate → Interface → Custom → Solute → Ion → Export) AND the CLI pipeline work correctly end-to-end with BOTH (a) the 7 new lattice types from Phase 39 (c0te, c1te, c2te, ice1hte, sTprime, 16, 17) and (b) custom hydrate guests (Phase 40 GenIce2 bridge). Close the --depol CLI flag gap (CLI-03).
**Depends on**: Phase 38 (pipeline), Phase 39 (lattice types), Phase 40 (custom guest), Phase 43 (depol)
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04
**Success Criteria** (what must be TRUE):
  1. New lattice types (sII, sH, c2te, ice1hte, sTprime, 16, 17) produce grompp-valid output through the Interface tab (GUI + CLI)
  2. New lattice types (sII, c2te, ice1hte, 16) pass grompp through the FULL tab chain (Interface→Solute→Custom→Ion) via GUI + CLI
  3. Water-only lattices (sTprime, 17) survive solute/ion insertion without crashing + grompp rc=0
  4. Triclinic lattices (c0te, c1te) are blocked at the CLI interface step + GUI worker (e2e, not just validator)
  5. Triclinic hydrate-only export @ 4×4×4 passes grompp (CLI + GUI — both export paths)
  6. Custom ethanol guest with non-sI lattices (sII, c2te, ice1hte, 16) passes grompp through GUI + CLI
  7. CLI --depol flag accepts strict/optimal with strict as default (CLI-03)
  8. Mixed built-in occupancy with new lattices passes grompp via GUI hydrate exporter
**Plans**: 14 plans in 6 waves (13 test-only + 1 code-change for --depol)

Plans:
- [x] 45-01-PLAN.md — New lattices (sII/c2te/ice1hte/sTprime/16/17) GUI interface export + grompp
- [x] 45-02-PLAN.md — New lattices (sII/c2te/ice1hte/sTprime/16/17) CLI interface export + grompp
- [x] 45-03-PLAN.md — sH (4480 guests, slow) GUI + CLI interface export + grompp
- [x] 45-04-PLAN.md — New lattices (sII/c2te/ice1hte/16) GUI full cross-tab (4 exporters) + grompp
- [x] 45-05-PLAN.md — New lattices (sII/c2te/ice1hte/16) CLI full cross-tab (3 branches) + grompp
- [x] 45-06-PLAN.md — sH full cross-tab GUI (4 exporters) + CLI (3 branches) + grompp
- [x] 45-07-PLAN.md — Water-only (sTprime/17) solute/ion cross-tab — verify no crash + grompp (Pitfall 3)
- [x] 45-08-PLAN.md — Triclinic blocking e2e (CLI _run_interface_step + GUI worker) for c0te/c1te
- [x] 45-09-PLAN.md — Triclinic hydrate-only export @ 4×4×4 (CLI + GUI) + grompp for c0te/c1te (Pitfall 1 + 6)
- [x] 45-10-PLAN.md — Custom ethanol + non-sI lattices (sII/c2te/ice1hte/16) GUI interface export + grompp
- [x] 45-11-PLAN.md — Custom ethanol + non-sI lattices CLI interface export + grompp
- [x] 45-12-PLAN.md — --depol CLI flag (parser.py + pipeline.py threading + test) — closes CLI-03 (ONLY code change)
- [x] 45-13-PLAN.md — Mixed built-in (CH4+THF) + sII/16 via GUI hydrate exporter + grompp
- [x] 45-14-PLAN.md — Filled-ice (c2te/ice1hte) single-cage-key GUI hydrate export + grompp

**Prior work already satisfied:** CLI-01 (--hydrate-lattice all 10 types — DONE in 39-03), CLI-04 (--cage-guest mixed occupancy — DONE in 42-07). CLI-02 (--custom-guest/--custom-guest-itp) is DEFERRED BY DESIGN (pipeline.py:73-81 — GUI-only for v4.7; CLI custom-cage-guest e2e tests use the Python API directly, tested in 45-10/45-11).

#### Phase 46: VTK Rendering
**Goal**: Custom guest molecules render with distinct visual style in the 3D hydrate viewer
**Depends on**: Phase 40 (custom guest types exist in pipeline)
**Requirements**: VTK-01, VTK-02
**Success Criteria** (what must be TRUE):
  1. Custom guest molecules render with distinct style in the hydrate 3D viewer (visually different from built-in CH₄/THF)
  2. Element map covers common custom guest atom types (C, O, H, N, S, etc.) so non-standard elements are not rendered as unknown
**Plans**: 0 plans (both requirements already satisfied by prior phases — verification-only)

Plans:
- [x] 46-01: Extend element map for common custom guest atom types — **DONE** (`hydrate_renderer.py:68` `ELEMENT_TO_ATOMIC_NUMBER` covers H..Ca including C, O, H, N, S, Cl, P, F, Na, K, Mg, Si, B). Satisfies **VTK-02**.
- [x] 46-02: Custom guest distinct rendering style in hydrate viewer — **DONE in 42-04** (`create_guest_actor` returns `list[vtkActor]` one per non-water mol_type with per-type bond color palette from `_DEFAULT_PALETTE`; `render_hydrate_structure` returns variable-length `[water, *guest_actors]`; mixed hydrate e2e test in 42-05 exercises the path). Satisfies **VTK-01**.

**Note:** Phase 46 is marked COMPLETE via code verification (no PLAN/SUMMARY files created — work was delivered as vertical slices inside 42-04/42-05). A `/gsd-verify-work 46` pass can confirm if desired, but no new plans are needed.

#### Phase 47: Testing & Validation
**Goal**: All new features are covered by unit tests, e2e tests, and grompp validation
**Depends on**: Phases 38-42 (all core features implemented)
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06, TEST-07, TEST-08
**Success Criteria** (what must be TRUE):
  1. Unit tests cover custom guest GRO/ITP validation (valid, name too long, wrong comb-rule, unparseable), sys.modules injection/cleanup, and _build_molecule_index with custom guest types
  2. E2E tests cover filled ice generation (C0, C1, C2, Ih, sT') and custom guest hydrate generation + GROMACS export
  3. E2E tests cover mixed cage occupancy hydrate generation
  4. Grompp validation tests confirm both custom guest and new lattice type exports produce valid GROMACS inputs
**Plans**: 1 plan (7 of 8 test requirements already satisfied by prior phases' TDD-style vertical slices; only filled-ice grompp gap remains)

Plans:
- [x] 47-01: Unit tests for custom guest validation, sys.modules, _build_molecule_index — **DONE** in Phase 40 (`test_custom_guest_bridge.py` covers validate_custom_guest_files + custom_guest_module injection/cleanup; `test_hydrate_config_custom.py` + `test_hydrate_config_metadata.py` cover _build_molecule_index with custom guest types; GRO/ITP validation edge cases covered in 40-01/40-04). Satisfies **TEST-01, TEST-02, TEST-03**.
- [x] 47-02: E2E tests for filled ice generation — **DONE in 39-05** (`test_hydrate_lattice_types.py` parametrized for c0te/c1te/c2te/ice1hte/sTprime/16/17; 157 parametrized structural validation tests). Satisfies **TEST-04**.
- [x] 47-03: E2E tests for custom guest hydrate + GROMACS export — **DONE in 41** (`test_e2e_custom_guest_hydrate.py` + `test_e2e_custom_guest_gui_grompp.py` + `test_e2e_custom_guest_cli_grompp.py`). Satisfies **TEST-05 + TEST-07** (custom guest half).
- [x] 47-04: E2E tests for mixed cage occupancy — **DONE in 42** (`test_e2e_mixed_cage_occupancy.py` + `test_e2e_sh_cage_occupancy.py` + `test_cli/test_mixed_cage_cli.py`). Satisfies **TEST-06**.
- [x] 47-05-PLAN.md — CLI hydrate-only branch grompp validation for c2te/ice1hte filled-ice lattices at native orthorhombic supercells (closes **TEST-08** — the only remaining gap; c2te@3x3x3 + ice1hte@4x4x4 via `CLIPipeline._run_export_step` hydrate branch). The roadmap's prior "c0te/c1te/c2te/ice1hte grompp not explicitly tested" framing is STALE — Phase 45 already closed c0te/c1te (CLI+GUI), c2te/ice1hte (GUI hydrate branch via 45-14), and c2te/ice1hte (CLI interface/solute/ion branches via 45-05). Only the CLI hydrate-ONLY branch for c2te/ice1hte remained. **DONE 2026-07-12** — tests/test_e2e_filled_ice_cli_hydrate_grompp.py (2 parametrized @gmx_skipif cases, gmx grompp rc=0; ZERO new production code).

#### Phase 48: Documentation
**Goal**: Users can learn about all new hydrate features from updated documentation (in-app + external)
**Depends on**: Phases 38-46 (all features shipped)
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04
**Success Criteria** (what must be TRUE):
  1. README documents the custom guest in hydrate workflow (upload → validate → generate → export)
  2. GUI guide covers new lattice types, custom guest upload, mixed occupancy controls, and depol selector
  3. CLI reference documents new flags (--lattice-type extended to 10 choices, --cage-guest, --depol) and marks --guest/--cage-occupancy-small/--cage-occupancy-large as DEPRECATED. Custom guest in hydrate is GUI-only for v4.7 (no CLI flag).
  4. Custom guest ITP requirements are documented (comb-rule=2 mandatory, residue name ≤3 chars for _H suffix, _H suffix convention explained)
  5. In-app help (help_dialog.py + tooltips) is updated for v4.7 features and restructured for navigability (QStackedWidget + QListWidget TOC — content has outgrown a single scrolling textbox)
**Plans**: 14 plans in 4 waves

Plans:
- [x] 48-01-PLAN.md — README Tab 1 hydrate rewrite + custom-guest workflow subsection (DOCS-01) ✓ DONE 2026-07-12
- [x] 48-02-PLAN.md — README version + Known Issues + footer sweep v4.5→v4.7 (cross-cutting) ✓ DONE 2026-07-14
- [x] 48-03-PLAN.md — GUI guide Hydrate lattice types table (10 rows) (DOCS-02-ext) ✓ DONE 2026-07-12
- [x] 48-04-PLAN.md — GUI guide Custom guest upload + mixed occupancy + depol subsections (DOCS-02-ext) ✓ DONE 2026-07-14
- [x] 48-05-PLAN.md — GUI guide header/version sweep v4.5→v4.7 (cross-cutting) ✓ DONE 2026-07-14
- [x] 48-06-PLAN.md — CLI ref hydrate flags rewrite + --cage-guest + --depol + DEPRECATED banners (DOCS-03) ✓ DONE 2026-07-12
- [x] 48-07-PLAN.md — CLI ref version/examples sweep v4.5→v4.7 + v4.7 examples (cross-cutting) ✓ DONE 2026-07-14
- [x] 48-08-PLAN.md — GRO/ITP guide custom guest ITP requirements section (DOCS-04) ✓ DONE 2026-07-14
- [x] 48-09-PLAN.md — help_dialog.py skeleton restructure to QStackedWidget+QListWidget TOC (DOCS-02-in-app) ✓ DONE 2026-07-12
- [x] 48-10-PLAN.md — help_dialog.py v4.7 content pages (4 new pages) (DOCS-02-in-app) ✓ DONE 2026-07-14
- [x] 48-11-PLAN.md — help_dialog headless smoke test (DOCS-02-in-app) ✓ DONE 2026-07-14
- [x] 48-12-PLAN.md — hydrate_panel per-cage tooltips (DOCS-02-in-app) ✓ DONE 2026-07-12
- [x] 48-13-PLAN.md — Version string bump 4.5.0 → 4.7.0 (cross-cutting) ✓ DONE 2026-07-12
- [x] 48-14-PLAN.md — Final verification sweep (all DOCS) ✓ DONE 2026-07-14

#### Phase 48.1: Split gromacs_writer.py monolith + dedup GRO writers (FRAG-03/TD-01) (INSERTED)

**Goal:** Split the 4067-line `quickice/output/gromacs_writer.py` monolith into per-structure modules and dedup the 6 near-identical GRO writer functions — behavior must stay byte-identical for GROMACS
**Depends on:** Phase 48 (v4.7 complete — scancode Groups 1/5/8 already cleaned up gromacs_writer.py on main at `74fc4b72`)
**Requirements:** FRAG-03, TD-01
**Success Criteria** (what must be TRUE):
  1. `gromacs_writer.py` is split into per-structure modules (e.g. `gro_writers.py`, `top_writers.py`, `ion_writer.py`, `shared.py`) — no single file exceeds ~800 lines
  2. The 6 near-identical GRO writer functions (`write_gro_file`, `write_interface_gro_file`, `write_multi_molecule_gro_file`, `write_ion_gro_file`, `write_custom_molecule_gro_file`, `write_solute_gro_file`) share extracted helpers (DRY)
  3. All produced `.top`/`.gro`/`.itp` files are byte-identical (or semantically identical — same numbers, possibly different comment/whitespace) to pre-refactor output
  4. `gmx grompp` dry-run passes on all export paths (ice, hydrate, interface, solute, custom, ion — both CLI + GUI)
  5. Full pytest suite passes with zero new failures (~1558+ tests)
**Plans:** 14 plans in 10 waves (Wave 0-9, sequential — each wave is a verification gate)

Plans:
- [x] 48.1-01-PLAN.md — Wave 0: Capture SHA256 byte-equivalence baselines (TDD, 7 export paths) ✓ DONE 2026-07-19
- [x] 48.1-02-PLAN.md — Wave 1: Extract _shared.py (constants + 17 helpers + _registry singleton) + update test_tip4p_ice_lj_values.py ✓ DONE 2026-07-19
- [x] 48.1-03-PLAN.md — Wave 2a: Create _gro_format.py with 10 DRY helpers (TD-01 scaffolding, no caller updates) ✓ DONE 2026-07-20
- [x] 48.1-04-PLAN.md — Wave 2b: Apply helpers to write_gro_file + write_interface_gro_file (byte-eq verify) ✓ DONE 2026-07-20
- [x] 48.1-05-PLAN.md — Wave 2c: Apply helpers to write_multi_molecule_gro_file + write_ion_gro_file (byte-eq verify) ✓ DONE 2026-07-20
- [x] 48.1-06-PLAN.md — Wave 2d: Apply helpers to write_custom_molecule_gro_file + write_solute_gro_file (byte-eq verify, preserve divergences) ✓ DONE 2026-07-20
- [x] 48.1-07-PLAN.md — Wave 2e: Extract TOP [defaults] block to _shared._write_top_defaults (all 6 TOP writers) ✓ DONE 2026-07-20
- [x] 48.1-08-PLAN.md — Wave 3: Split ice_writer.py (smallest — validates pattern) ✓ DONE 2026-07-20
- [ ] 48.1-09-PLAN.md — Wave 4: Split interface_writer.py (preserve 'if custom_guest_info:' gate divergence)
- [ ] 48.1-10-PLAN.md — Wave 5: Split multi_molecule_writer.py (_registry singleton + no try/except)
- [ ] 48.1-11-PLAN.md — Wave 6: Split ion_writer.py (largest — MoleculeIndex + 7 molecule types)
- [ ] 48.1-12-PLAN.md — Wave 7: Split custom_writer.py (preserve divergent header format — NO :5d)
- [ ] 48.1-13-PLAN.md — Wave 8: Split solute_writer.py (RISKIEST — empty-molecule_index fallback + no try/except)
- [ ] 48.1-14-PLAN.md — Wave 9: Final verification + PR (all 5 success criteria documented)

**Details:**
Last remaining scancode item (FRAG-03 + TD-01 from `.planning/scancode-fixes/PLAN.md`). L-complexity major refactor with high regression risk — touches every export path. The 4067-line `gromacs_writer.py` file contains 6 near-identical GRO writer functions that should be split into per-structure modules with shared GRO-writer helpers extracted. Behavior must stay byte-identical for GROMACS (`.top`/`.gro`/`.itp` output must pass `gmx grompp`).

**Work on a PR branch** (`refactor/frag03-split-gromacs-writer`) from current main (`74fc4b72`) which includes the Group 1/5/8 cleanup. Run full regression + `gmx grompp` validation before merge. The split starts from a cleaned-up file (Group 5 extracted constants, Group 8 replaced ad-hoc type() with MoleculeIndex dataclass, Group 1 fixed triclinic PBC).

**Verification plan:**
- Snapshot MD5 of `.top`/`.itp`/`.gro` output before refactor → re-export after → assert byte-identical (matches Group 5 pattern)
- `gmx grompp` dry-run on all 6 export paths × (CLI + GUI) = 12 grompp validations
- Full pytest suite (~1558+ tests, excluding slow GUI/Qt/VTK files for non-GUI runs)
- comb-rule=2 preserved in all `.top` files (AGENTS.md)
- All inserters return NEW structure objects (V-17 fix preserved)

## Progress

**Execution Order:**
Phases execute in numeric order: 38 → 39 → 40 → 41 → 42 → 43 → 44 → **44.1** → 45 → 46 → 47 → 48 → **48.1**

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 38. Internal Pipeline Refactor | v4.7 | 4/4 | ✓ Complete | 2026-06-29 |
| 39. Extended Lattice Types | v4.7 | 5/5 | ✓ Complete | 2026-06-30 |
| 40. Custom Guest Bridge Core | v4.7 | 5/5 | ✓ Complete | 2026-07-02 |
| 41. GROMACS Export for Custom Guests | v4.7 | 11/11 | ✓ Complete | 2026-07-05 |
| 42. Mixed Cage Occupancy | v4.7 | 8/8 | ✓ Complete | 2026-07-06 |
| 43. Depol Mode | v4.7 | 2/2 | ✓ Complete | 2026-07-07 |
| 44. GUI Integration | v4.7 | 1/1 (3 of 4 stubs done in 39-04/42-06/43-02) | ✓ Complete | 2026-07-07 |
| 44.1. Wire Custom Guest Through All Tabs (INSERTED) | v4.7 | 22/22 | ✓ Complete | 2026-07-10 |
| 45. E2E Hydrate Tab Workflow | v4.7 | 14/14 (13 test-only + 1 code-change --depol) | ✓ Complete | 2026-07-11 |
| 46. VTK Rendering | v4.7 | 0/0 (both reqs done in 42-04 + element map) | ✓ Complete (verification-only) | 2026-07-07 |
| 47. Testing & Validation | v4.7 | 1/1 (7 of 8 test reqs done in 39-05/40/41/42 + 47-05 closes TEST-08) | ✓ Complete | 2026-07-12 |
| 48. Documentation | v4.7 | 14/14 (4 waves: 11 Wave-1 + 1 Wave-2 + 1 Wave-3 + 1 Wave-4) | ✓ Complete | 2026-07-14 |
| 48.1. Split gromacs_writer.py + dedup GRO writers (INSERTED) | v4.7 | 8/14 | 🚧 In progress (Waves 0-3 complete — 14 byte-eq tests PASS, 7 sub-modules + _gro_format.py with 10 DRY helpers + _write_top_defaults parameterized helper extracted, ALL 6 GRO + ALL 6 TOP writers refactored to call shared helpers, Wave 3 FIRST per-structure split complete — ice_writer.py created with write_gro_file + write_top_file moved byte-verbatim, gromacs_writer.py re-exports, per-structure split pattern validated for Waves 4-8), 1840 tests) | 2026-07-20 |

**v4.7 status after reorganization:** Phase 48 Documentation COMPLETE — all 14 plans (48-01..48-14) done (aggressively split per user request). Phase 47 COMPLETE (1/1). **Phases 38-48 ALL COMPLETE** — v4.7 milestone requirements 57/61 complete (4 pending: GUEST-01/02/03 GUI surfaces done in 44-02, CLI-02 deferred by design; DOCS-01..04 all complete). The 2 doc-hygiene gaps logged by the 48-14 verification sweep (gro-itp-guide.md:3,9 stale v4.5 intro; README.md:17 lone 3-lattice list) were FIXED by orchestrator correction commit 1923ab9.

## Dependency Graph

```
Phase 38: Internal Pipeline Refactor
     │
     ▼
Phase 39: Extended Lattice Types
     │
     ├────────────────────────────────┐
     ▼                                ▼
Phase 40: Custom Guest Bridge     Phase 43: Depol Mode
     │                           (depends on Phase 38 only)
     ▼
Phase 41: GROMACS Export
     │
     ▼
Phase 42: Mixed Cage Occupancy
     │
     ├──┬──────────────┬───────────┐
     │  │              │           │
     ▼  ▼              ▼           ▼
Phase 43*  Phase 44: GUI  Phase 45: CLI  Phase 46: VTK
(already)   Integration    Integration    Rendering ✓ DONE
      │      (44-02 only)   (45-01b+02a)   (no plans needed)
      │          │
      │          ▼
      │   Phase 44.1 (INSERTED)
      │   (wire custom guest
      │    through all tabs)
      │          │
      │          ▼
      ├──────────┴───────────┐
      │                      │
      ▼                      ▼
Phase 47: Testing & Validation  Phase 45: CLI
  (47-05 filled-ice grompp gap)   (45-01b+02a)
      │
      ▼
Phase 48: Documentation
  (14 plans: 8 external docs + 3 in-app help + 1 tooltip + 1 version bump + 1 verification)
```

*Phase 43 (Depol Mode) executed after Phase 38, parallel with Phases 39-42. Phase 46 (VTK Rendering) requires no new plans — VTK-01/VTK-02 satisfied by 42-04 + the existing element map. Phase 44.1 (INSERTED) handles urgent cross-tab custom-guest issues discovered during 44-02 acceptance testing (Pitfall 6 engine relaxation + Interface tab export wiring) — executes between 44 and 45. Phase 45/47 are reduced to single plans each after reorganization (most stubs were delivered as vertical slices inside 39-42).

---

<details>
<summary>✅ v4.5 Solute & Custom Molecule (Phases 32-37.2) - SHIPPED 2026-06-27</summary>

Phases 32-37.2 + e2e-export/api/compute. 20 phases, 131 plans. See archive: .planning/milestones/v4.5-ROADMAP.md

</details>

<details>
<summary>✅ v4.0 Molecule Insertion (Phases 28-31.2) - SHIPPED 2026-05-01</summary>

Phases 28-31.2. 7 phases, 29 plans. See archive: .planning/milestones/v4.0-ROADMAP.md

</details>

<details>
<summary>✅ v3.5 Interface Enhancements (Phases 22-27) - SHIPPED 2026-04-13</summary>

Phases 22, 24-27 shipped; Phase 23 deferred. See archive: .planning/milestones/v3.5-ROADMAP.md

</details>

<details>
<summary>✅ v3.0 Interface Generation (Phases 16-21) - SHIPPED 2026-04-11</summary>

Phases 16-21. 6 phases, 15 plans. See archive: .planning/milestones/v3.0-ROADMAP.md

</details>

<details>
<summary>✅ v2.1.1 Phase Diagram Data (Phase 15) - SHIPPED 2026-04-08</summary>

Phase 15. 9 plans. See archive: .planning/milestones/v2.1.1-ROADMAP.md

</details>

<details>
<summary>✅ v2.1 GROMACS Export (Phase 14) - SHIPPED 2026-04-07</summary>

Phase 14. 8 plans. See archive: .planning/milestones/v2.1-ROADMAP.md

</details>

<details>
<summary>✅ v2.0 GUI Application (Phases 8-13) - SHIPPED 2026-04-04</summary>

Phases 8-13. 28 plans. See archive: .planning/milestones/v2.0-ROADMAP.md

</details>

<details>
<summary>✅ v1.0-v1.1 MVP + Hotfix (Phases 1-7) - SHIPPED 2026-03-29/31</summary>

See archives: .planning/milestones/v1-ROADMAP.md, .planning/milestones/v1.1-ROADMAP.md

</details>
