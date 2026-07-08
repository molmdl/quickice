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
- [ ] 44.1-02-PLAN.md — to_candidate() carries guest_descriptors + guest_atom_counts in metadata
- [ ] 44.1-03-PLAN.md — count_guest_atoms accepts guest_atom_count for custom guests
- [ ] 44.1-04-PLAN.md — Move _build_custom_guest_info to neutral quickice/output/guest_info.py
- [ ] 44.1-05-PLAN.md — slab.py threads guest_atom_count from candidate metadata
- [ ] 44.1-06-PLAN.md — pocket.py threads guest_atom_count from candidate metadata
- [ ] 44.1-07-PLAN.md — piece.py threads guest_atom_count from candidate metadata
- [ ] 44.1-08-PLAN.md — Shared _stage_hydrate_guest_itps helper (DRY across 4 exporters)
- [ ] 44.1-09-PLAN.md — GUI InterfaceGROMACSExporter threads custom_guest_info + ITP staging
- [ ] 44.1-10-PLAN.md — GUI MainWindow interface export handler passes hydrate_config
- [ ] 44.1-11-PLAN.md — GUI SoluteGROMACSExporter + extend write_solute_top/gro_file with custom_guest_info
- [ ] 44.1-12-PLAN.md — GUI MainWindow solute export handler passes hydrate_config
- [ ] 44.1-13-PLAN.md — GUI CustomMoleculeGROMACSExporter + extend write_custom_molecule_top/gro_file
- [ ] 44.1-14-PLAN.md — GUI MainWindow custom-molecule export handler passes hydrate_config
- [ ] 44.1-15-PLAN.md — GUI IonGROMACSExporter + extend write_ion_top/gro_file with custom_guest_info
- [ ] 44.1-16-PLAN.md — GUI MainWindow ion export handler passes hydrate_config
- [ ] 44.1-17-PLAN.md — CLI interface/custom/solute/ion export branches thread custom_guest_info + itp_helpers
- [ ] 44.1-18-PLAN.md — Remove 44-02 _enforce_single_custom_cage auto-clear (engine now allows 2 cages)
- [ ] 44.1-19-PLAN.md — Full e2e (GUI): custom guest → interface → solute → ion → export grompp
- [ ] 44.1-20-PLAN.md — Full e2e (CLI): custom guest → all export branches grompp
- [ ] 44.1-21-PLAN.md — Full e2e: same custom guest in 2 cages (Pitfall 6 relaxation) → grompp
- [ ] 44.1-22-PLAN.md — Regression guard: built-in ch4 + thf through ALL tabs (GUI + CLI)

**Details:**
Two issues discovered during Phase 44-02 human-verify checkpoint (user-generated custom guest hydrate → Interface tab → export):

1. **Pitfall 6 engine over-restriction** (`quickice/structure_generation/types.py:711-720`): `HydrateConfig.__post_init__` rejects duplicate `guest_residue_name` across custom cage assignments, but checks residue name alone — not `(guest_type, guest_residue_name)`. This blocks the SAFE case (same custom guest in 2 cages, which aggregates to one `MOL_H` moleculetype exactly like ch4-in-all-cages) while correctly blocking the UNSAFE case (two different custom guests sharing the same residue name). Fix: track `guest_residue_name → guest_type`; only raise when a *different* `guest_type` claims an already-seen residue name. ~3-line change. This lets the 44-02 GUI auto-revert mitigation be removed/relaxed (single custom guest can occupy multiple cages like ch4).

2. **Interface tab custom guest export broken** (two parts):
   - **(a)** `quickice/structure_generation/types.py:1168` `HydrateStructure.to_candidate()` carries `guest_type_counts` in metadata but DROPS the `CageGuestAssignment` descriptor fields (residue_name, gro_path, itp_path, atom_labels, atom_count). When a hydrate becomes an interface template, the custom guest info is lost.
   - **(b)** `quickice/gui/export.py:901-965` `InterfaceGROMACSExporter.export_interface_gromacs()` calls `write_interface_gro_file`/`write_interface_top_file` with NO `custom_guest_info` kwarg (export.py:942-947) — the Phase 41-04/41-05 custom path never fires. It instead uses the old `_detect_guest_type_from_structure` heuristic (export.py:959) which returns `None` for custom guests → no ITP staged, no atomtypes merged, wrong/missing residue name → broken `.top`.
   - **Fix:** mirror the 42-08 pattern — `to_candidate()` carries custom guest descriptors (or the exporter reconstructs `custom_guest_info` from the interface structure's `guest_descriptors` + the original `HydrateConfig`); `export_interface_gromacs` threads `custom_guest_info` to both interface writers using the structure-driven ITP staging approach.

**Scope note:** Phase 44 goal ("Hydrate tab") is COMPLETE — these are cross-tab concerns that predates Phase 44 (the Interface export path was never wired for custom guests in any phase). Marked INSERTED/URGENT because the user hit this immediately during 44-02 acceptance testing.

#### Phase 45: CLI Integration
**Goal**: All new hydrate features are accessible from the CLI for scripting and batch workflows
**Depends on**: Phase 38 (pipeline), Phase 39 (lattice types), Phase 40 (custom guest), Phase 43 (depol)
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04
**Success Criteria** (what must be TRUE):
  1. CLI --hydrate-lattice flag accepts all new lattice type names (c0te, c1te, c2te, ice1hte, sTprime, 16, 17)
  2. CLI --custom-guest and --custom-guest-itp flags allow specifying a custom guest .gro/.itp file pair
  3. CLI --depol flag supports strict/optimal selection with strict as default
  4. CLI --guest-small and --guest-large flags enable mixed cage occupancy with per-cage occupancy values
**Plans**: 1 plan (2 of 4 sub-items already satisfied; collapse remaining into one plan covering CLI-02 + CLI-03 + custom-guest grompp e2e)

Plans:
- [x] 45-01a: Extend --hydrate-lattice for new types — **DONE in 39-03** (`parser.py:209` choices list already includes all 10 lattice types; `test_triclinic_blocking.py` covers c0te/c1te/c2te/ice1hte). Satisfies **CLI-01**.
- [ ] 45-01b: Add `--custom-guest` / `--custom-guest-itp` flags + CLI custom-guest grompp e2e — **REMAINING**. `pipeline.py:113-115` comment explicitly defers this ("CLI surface is built-in-only for v4.7"). Covers **CLI-02** + closes the CLI half of EXPORT-06 / TEST-07 for custom guests. Combine with 45-02a in one plan (both touch `parser.py` + `pipeline.py`).
- [ ] 45-02a: Add `--depol` flag (strict/optimal, default strict) — **REMAINING**. Config field exists since 43-01 (`HydrateConfig.depol_mode`); CLI call site at `pipeline.py:372` inherits "strict" automatically — just needs the argparse flag + passthrough. Covers **CLI-03**. Combine with 45-01b.
- [x] 45-02b: `--guest-small`/`--guest-large` mixed occupancy — **DONE in 42-07** as repeatable `--cage-guest KEY=GUEST:OCC` (better design than two separate flags; supports medium cage + any cage_type_map key). `test_cli/test_mixed_cage_cli.py` has grompp e2e. Satisfies **CLI-04**.
- [x] 45-03 (partial): CLI e2e for built-in mixed occupancy — **DONE in 42-07** (`test_mixed_cli_built_in_grompp`). Custom-guest CLI grompp e2e folds into 45-01b.

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
- [ ] 47-05: Grompp validation tests for new lattice type exports (filled ices) — **REMAINING (THE ONLY GAP)**. Custom guest grompp done (47-03); built-in mixed grompp done (42-07); **filled-ice (c0te/c1te/c2te/ice1hte) grompp not explicitly tested** — these lattices use `parse_guest` + `cage_type_map["guest"]` single-entry path (39-02) which has no grompp e2e. One small plan: parameterized `@gmx_skipif` grompp test for the 4 filled-ice lattices. Satisfies **TEST-08**.

#### Phase 48: Documentation
**Goal**: Users can learn about all new hydrate features from updated documentation (in-app + external)
**Depends on**: Phases 38-46 (all features shipped)
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04
**Success Criteria** (what must be TRUE):
  1. README documents the custom guest in hydrate workflow (upload → validate → generate → export)
  2. GUI guide covers new lattice types, custom guest upload, mixed occupancy controls, and depol selector
  3. CLI reference documents new flags (--hydrate-lattice extended values, --custom-guest, --custom-guest-itp, --depol, --guest-small, --guest-large)
  4. Custom guest ITP requirements are documented (comb-rule=2 mandatory, residue name ≤3 chars for _H suffix, _H suffix convention explained)
  5. In-app help (help_dialog.py + tooltips) is updated for v4.7 features and restructured for navigability (TOC buttons or tabbed sections — content has outgrown a single scrolling textbox)
**Plans**: 2 plans (split external docs from in-app help restructure)

Plans:
- [ ] 48-01: External docs — README custom guest workflow + GUI guide + CLI reference + ITP requirements (covers **DOCS-01, DOCS-02, DOCS-03, DOCS-04**). One plan, 2-3 tasks: README + docs/gui-guide.md + docs/cli-reference.md + docs/gro-itp-guide.md. All four files already exist — this is an update, not creation.
- [ ] 48-02: In-app help restructure — audit `quickice/gui/help_dialog.py` + per-widget tooltips for v4.7 features (new lattice types, custom guest upload, depol, mixed cage); restructure help dialog from single scrolling textbox to indexed format (TOC buttons or QTabWidget sections) since content volume now warrants navigation. Covers the in-app-help half of DOCS-02 (user-facing text inside the app, not the markdown guide). One plan, 2 tasks: restructure dialog container + populate v4.7 content.

## Progress

**Execution Order:**
Phases execute in numeric order: 38 → 39 → 40 → 41 → 42 → 43 → 44 → **44.1** → 45 → 46 → 47 → 48

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 38. Internal Pipeline Refactor | v4.7 | 4/4 | ✓ Complete | 2026-06-29 |
| 39. Extended Lattice Types | v4.7 | 5/5 | ✓ Complete | 2026-06-30 |
| 40. Custom Guest Bridge Core | v4.7 | 5/5 | ✓ Complete | 2026-07-02 |
| 41. GROMACS Export for Custom Guests | v4.7 | 11/11 | ✓ Complete | 2026-07-05 |
| 42. Mixed Cage Occupancy | v4.7 | 8/8 | ✓ Complete | 2026-07-06 |
| 43. Depol Mode | v4.7 | 2/2 | ✓ Complete | 2026-07-07 |
| 44. GUI Integration | v4.7 | 1/1 (3 of 4 stubs done in 39-04/42-06/43-02) | ✓ Complete | 2026-07-07 |
| 44.1. Wire Custom Guest Through All Tabs (INSERTED) | v4.7 | 1/22 | In progress | 2026-07-08 |
| 45. CLI Integration | v4.7 | 0/1 (2 of 4 sub-items done in 39-03/42-07) | Not started | - |
| 46. VTK Rendering | v4.7 | 0/0 (both reqs done in 42-04 + element map) | ✓ Complete (verification-only) | 2026-07-07 |
| 47. Testing & Validation | v4.7 | 0/1 (7 of 8 test reqs done in 39-05/40/41/42) | Not started | - |
| 48. Documentation | v4.7 | 0/2 (external + in-app help restructure) | Not started | - |

**Remaining v4.7 work after reorganization:** ~5 plans (44-02, 45-01b+02a combined, 47-05, 48-01, 48-02) down from 14 stubs.

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
  (48-01 external + 48-02 in-app help restructure)
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
