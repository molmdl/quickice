# QuickIce State

**Project:** QuickIce - Condition-based Ice Structure Generation
**Core Value:** Generate ready-to-use initial models and topologies for GROMACS for the simulation of ice, hydrates, solutes, and custom molecules in water
**Current Focus:** Phase 41 IN PROGRESS (3/11 plans) — GROMACS Export for Custom Guests (41-09, 41-01, 41-07 done)

---

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-27)

**Core value:** Generate ready-to-use initial models and topologies for GROMACS for the simulation of ice, hydrates, solutes, and custom molecules in water

**Current focus:** v4.7 Extended Hydrate Generation — Phase 41 IN PROGRESS (41-09, 41-01, 41-07 done; 41-02..41-06, 41-08, 41-10, 41-11 pending). Phase 40 COMPLETE (40-01..40-05 done).

**Tech stack:**
- Python 3.14, PySide6 6.10.2, VTK 9.5.2
- GenIce2 2.2.13.1, spglib, numpy, scipy, iapws
- MVVM architecture with QThread workers
- Unified CLI+GUI entry point (`python -m quickice`)

---

## Current Position

| Field | Value |
|-------|-------|
| Milestone | v4.7 Extended Hydrate Generation |
| Phase | 41 of 48 (GROMACS Export for Custom Guests) — IN PROGRESS |
| Plan | 3/11 complete (41-09, 41-01, 41-07 done) |
| Status | Phase 41 in progress; 41-07 (copy_custom_guest_itp + CLI hydrate routing) complete |
| Last activity | 2026-07-05 — Completed 41-07-PLAN.md (copy_custom_guest_itp + is_custom_guest branch) |

**Progress:** [████░░░░░░] ~40% (17/42 v4.7 plans complete)

---

## Milestone History

### v4.5 Solute & Custom Molecule Insertion (SHIPPED 2026-06-27)
**Phases:** 32-37.2 + e2e-export/api/compute (20 phases, 131 plans)
**Archive:** .planning/milestones/v4.5-ROADMAP.md

### v4.0 Molecule Insertion (SHIPPED 2026-05-01)
**Phases:** 28-31.2 (7 phases, 29 plans)
**Archive:** .planning/milestones/v4.0-ROADMAP.md

### v3.5 Interface Enhancements (SHIPPED 2026-04-13)
**Phases:** 22, 24-27 shipped; Phase 23 deferred

### v3.0 Interface Generation (SHIPPED 2026-04-11)
**Phases:** 16-21 (6 phases, 15 plans)

---

## Accumulated Context

### Decisions

Recent decisions affecting v4.7 work:
- sys.modules injection for custom guests: main-thread registration before HydrateWorker (v4.7)
- _H suffix for hydrate guests via MoleculetypeRegistry (v4.7)
- Reject A/B → sigma/epsilon auto-conversion (v4.7)
- GRO 5-char residue name limit: base names ≤3 chars (v4.7)
- sT' = water-only generation in v4.7 (no cagepos in GenIce2)
- Built-in CO₂/H₂/ethane guests deferred to v4.8+ (force field verification needed)
- Water model selector deferred to v4.8+ (downstream impact)
- **[38-01]** Built-in guest types auto-populate metadata in __post_init__; custom types (Phase 40) must provide explicitly
- **[38-01]** guest_itp_path is NOT auto-populated (only relevant for custom guests)
- **[38-01]** atom_labels uses list copy from GUEST_MOLECULES to avoid shared mutable state
- **[38-03]** GRO residue name validation rejects >5 chars with ValueError (no silent truncation)
- **[38-03]** Validation checks only length, not content; callers must fix names upstream
- **[38-03]** Empty MoleculetypeRegistry fallback (source.upper()) can produce >5 char names — must be caught by validation
- **[38-04]** transform_guest_itp() is unified ITP transformation entry point (atomtypes comment-out + _H suffix + GRO name validation)
- **[38-04]** No [ atoms ] residue name rewriting in transform_guest_itp — deferred to Phase 40 custom guests
- **[38-04]** Hydrate export (GUI+CLI) uses read-transform-write instead of shutil.copy for guest ITPs
- **[38-02]** Guest identification checked BEFORE water in metadata-driven _build_molecule_index (prevents THF "O" misidentification)
- **[38-02]** Residue grouping is preferred path for GenIce2 output; atom-label sequence matching is the fallback
- **[38-02]** config=None preserves full backward-compatible pattern matching (two separate code paths, not unified)
- **[39-01]** sH is_triclinic=True for data accuracy but NOT blocked in interface_builder (phase_id-based blocking, not is_triclinic flag)
- **[39-01]** Filled ices use "guest" cage key (not small/large) with single-entry cage_type_map to prevent double-placement
- **[39-01]** is_triclinic is forward-looking metadata with no current consumer (future GUI tooltips/docs)
- **[39-01]** No water-only validation in HydrateConfig; generator handles guest skipping for empty-cage lattices
- **[39-02]** Numeric lattice module names (16, 17) loaded via safe_import at runtime — Python forbids `from X import 16`
- **[39-02]** Filled ices use only cage_type_map['small'] ('Ne1') — no 'large' key prevents double-placement
- **[39-02]** parse_guest used for ALL guest placement (spot_guests crashes with IndexError for filled ices)
- **[39-03]** TRICLINIC_HYDRATE_PHASES explicit set (hydrate_c0te, hydrate_c1te) for blocking — NOT is_triclinic flag (prevents sH regression)
- **[39-03]** CLI --lattice-type choices mirror HYDRATE_LATTICES keys (all 10 lattice types)
- **[39-04]** Water-only lattices disable ALL guest controls (combo + both occupancy spinners) in GUI
- **[39-04]** Filled ices (single cage_type_map key) disable only large occupancy spinner; small remains enabled
- **[39-04]** get_configuration unchanged — returns valid HydrateConfig with default ch4 even when guest controls disabled
- **[39-05]** 157 parametrized structural validation tests + 6 triclinic blocking regression tests for all 10 HYDRATE_LATTICES entries
- **[40-01]** parse_itp_defaults_comb_rule returns None when [ defaults ] absent (valid: main .top supplies comb-rule=2); reject only when non-None and != 2
- **[40-01]** Malformed/non-integer comb-rule returns None (not raise) — parser is a pure extraction primitive; callers decide rejection
- **[40-02]** transform_guest_itp Step 3 rewrites [ atoms ] resname (field index 3) to {guest_name}{suffix}; completes the deferred Phase 38-04 item so custom guest ITPs are internally consistent
- **[40-02]** Step 3 applies independently of [ moleculetype ] section presence — resname is rewritten whenever an [ atoms ] section is found
- **[40-02]** [ atoms ] comment/blank lines preserved verbatim; leading whitespace kept, internal spacing normalized to single spaces (GROMACS whitespace-flexible); graceful no-op when no [ atoms ] section
- **[40-03]** HydrateConfig gains guest_residue_name + guest_gro_path fields (default ""); is_custom_guest property returns guest_type not in GUEST_MOLECULES
- **[40-03]** Custom guests require ALL of guest_residue_name, guest_atom_labels, guest_atom_count, guest_gro_path (no auto-populate per [38-01]); built-in guests auto-populate unchanged (backward compat)
- **[40-03]** guest_name defaults to guest_residue_name (not guest_type) for custom guests; new fields default empty so old callers/dicts still work
- **[40-04]** build_custom_guest_module builds a synthetic genice2.molecules.<guest_type> ModuleType (centered sites_, labels_, name_); does NOT register in sys.modules (caller owns injection/cleanup)
- **[40-04]** validate_custom_guest_files runs the full checklist (parseable, atom count, name<=3, comb-rule=2, audit_name) with exact messages; accepts absent [ defaults ] (comb_rule=None — main .top supplies comb-rule=2)
- **[40-04]** custom_guest_module context manager + register/unregister pair provide thread-safe sys.modules injection with try/finally cleanup (main-thread registration per v4.7); [ atomtypes ] absence is a WARNING not an error
- **[40-04]** Added IndexError to GRO/ITP parse catch tuple — not_a_gro.txt raises IndexError (truncated file); plan's (ValueError,OSError) was insufficient (Rule 1 auto-fix)
- **[40-05]** generate() branches on config.is_custom_guest: custom path lazy-imports build_custom_guest_module/custom_guest_module, builds the synthetic Molecule module on the MAIN thread, wraps _run_via_api in the custom_guest_module context manager (try/finally sys.modules.pop); built-in path unchanged (no bridge import, no sys.modules injection)
- **[40-05]** _build_molecule_index uses guest_residue_name (fallback guest_type.upper()) for residue grouping — backward compatible (built-ins have guest_residue_name="" -> guest_type.upper()); preferred path for custom guests; atom-label matching is fragile fallback
- **[40-05]** _generate_report branches on config.is_custom_guest to use config.guest_name + guest_residue_name instead of GUEST_MOLECULES[guest_type]['name'] (avoids KeyError); mol_type for custom guests is config.guest_type (e.g. "etoh_e2e"), NOT guest_residue_name ("MOL")
- **[40-05]** Existing except Exception in _run_via_api left as-is per plan (pre-existing GUI-adjacent code; minimize regression risk)
- **[41-09]** _stage_custom_guest_itp(workspace, itp_path, residue_name) test helper applies the FULL transform_guest_itp (comment atomtypes + _H moleculetype rename + [atoms] resname rewrite), unlike _stage_itp_files (comment-only); staged ITP is internally consistent with .top [molecules] '{name}_H'
- **[41-09]** Call ordering for custom-guest grompp tests: _stage_itp_files first (stages tip4p-ice.itp + comments custom etoh.itp atomtypes but keeps moleculetype 'etoh'), then _stage_custom_guest_itp overwrites etoh.itp with moleculetype 'MOL_H'; purely additive (built-in staging unchanged, 18/18 existing grompp tests unaffected)
- **[41-09]** Tests use the ETOH_ITP absolute path constant (e2e_export_helpers) instead of cwd-relative paths for cwd-independence; identical fixture, no behavioral change
- **[41-01]** _merge_custom_atomtypes(f, itp_path, written, label) added as a shared tested merge+dedup primitive (parse → conflict-check → write-new-only → record); existing inline merge code in write_custom_molecule_top_file / write_ion_top_file is intentionally NOT refactored (zero regression risk; consumer phases EXPORT-03 / write_multi_molecule_top_file / write_interface_top_file will adopt it later)
- **[41-01]** No-op returns BEFORE writing the '; label' comment header — header is written only when parse_itp_atomtypes returns non-empty (so a no-section ITP yields a truly empty file)
- **[41-01]** Tests pre-seed *written* from GAFF2_ATOMTYPES (importable source of truth) rather than hardcoded values, guaranteeing exact LJ-param match with etoh.itp hc/c3/h1 for deterministic dedup
- **[41-07]** copy_custom_guest_itp(output_dir, itp_path, residue_name) added to quickice/cli/itp_helpers.py — reads custom guest ITP, applies transform_guest_itp(content, residue_name, '_H') (comments atomtypes + renames moleculetype to '{name}_H' + rewrites [atoms] resname), writes to output_dir/<itp basename>; uses except (OSError, ValueError) per AGENTS.md (no bare except Exception); returns None for missing source / >5-char residue name (logged at error)
- **[41-07]** copy_itp_files_for_structure hydrate branch dispatches on config.is_custom_guest BEFORE the built-in _resolve_guest_type_for_hydrate_step/_copy_hydrate_guest_itp path; custom path uses explicit config.guest_itp_path + config.guest_residue_name, built-in ch4/thf path UNCHANGED (still _copy_hydrate_guest_itp → '{guest_type}_hydrate.itp'); the two paths stay disjoint by is_custom_guest
- **[41-07]** Custom guest ITP basename preserved (output_dir / src.name, e.g. 'etoh.itp') so it matches the .top #include naming from plans 41-05/41-08; built-in _copy_hydrate_guest_itp keeps its '{guest_type}_hydrate.itp' convention; tests/test_cli/ subdir created without __init__.py (pytest discovers via rootdir mode)

### Pending Todos

- [2026-06-20] Decide disposition of 26 rogue pip packages in quickice env (tooling)
- [2026-05-24] Pre-built small molecules for custom mol with GROMACS format (feature)
- [2026-05-16] Install UPX for bundle compression (tooling)
- [2026-05-07] Capture screenshots per Phase 35 suggestions (docs)

### Blockers/Concerns

- ~~GRO `:<5s` overflow (NOT truncation) — must validate at every write entry point~~ **[RESOLVED in 38-03]** validate_gro_residue_name() now called at all 10 GRO write entry points
- ~~`_build_molecule_index` is single-point bottleneck — must refactor before any new guest/water model~~ **[RESOLVED in 38-02]** metadata-driven identification replaces hardcoded patterns
- ~~Thread safety gap: `sys.modules` injection must happen outside existing `_genice_lock` scope~~ **[RESOLVED in 40-05]** generate() registers the custom guest module in sys.modules between _ensure_genice_import() and _run_via_api (outside _genice_lock); custom_guest_module context manager wraps _run_via_api with try/finally cleanup

---

## Session Continuity

Last session: 2026-07-05T05:28Z
Stopped at: Completed 41-07-PLAN.md (copy_custom_guest_itp + is_custom_guest branch in CLI hydrate ITP copy)
Resume file: None
