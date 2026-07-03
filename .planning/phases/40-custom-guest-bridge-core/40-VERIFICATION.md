---
phase: 40-custom-guest-bridge-core
verified: 2026-07-03T00:00:00Z
status: passed
score: 29/29 must-haves verified
re_verification: false
human_verification:
  - test: "GUI upload flow — file picker for .gro + .itp, validation feedback in UI"
    expected: "User selects a .gro and .itp file via file dialogs; validation errors (name >3 chars, comb-rule=1) surface as message boxes; generation kicks off"
    why_human: "Phase 40 modified core files only (custom_guest_bridge.py, hydrate_generator.py, types.py, itp_parser.py, gromacs_writer.py). No GUI files (main_window.py, hydrate_tab widgets) were touched — the GUI upload widget is out of scope for this core-bridge phase. The HydrateConfig API + generate() are the programmatic entry points that the GUI will later bind to."
  - test: "Visual VTK rendering of custom guest in cages"
    expected: "Custom ethanol molecules render at cage centers (not clustered at origin), visually distinct from water framework"
    why_human: "VTK rendering is GUI-path work; this phase only proves positions are correct (test_custom_guest_positions_not_all_at_origin asserts max|pos| > 0.1 nm). Visual confirmation requires a display (QT_QPA_PLATFORM=offscreen may still crash per AGENTS.md)."
---

# Phase 40: Custom Guest Bridge Core Verification Report

**Phase Goal:** Users can upload a custom guest molecule and have it placed in hydrate cage positions via GenIce2
**Verified:** 2026-07-03
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Phase Success Criteria #1-5)

| #   | Truth                                                                                              | Status     | Evidence                                                                                                                                                                                                                       |
| --- | -------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | User can upload a .gro+.itp pair and generate a hydrate structure with the custom molecule placed in specified cage positions | ✓ VERIFIED | `test_e2e_custom_guest_hydrate.py::test_custom_guest_placed_in_cages` passes; live integration `HydrateStructureGenerator().generate(cfg)` → guest_count=8, water_count=46, total_atoms=256, mol_types={'water','etoh_integ'}; `test_custom_guest_positions_not_all_at_origin` asserts max\|pos\| > 0.1 nm (guests at cage centers, not origin) |
| 2   | QuickIce rejects custom guest residue names >3 chars with a specific error message                 | ✓ VERIFIED | Live validation of synthetic 'ETHAN' (5-char) GRO returns `is_valid=False` with exact message: `"Custom guest residue name 'ETHAN' (5 chars) exceeds 3 chars. GRO format allows 5-char residue names; QuickIce reserves 2 chars for the '_H' hydrate suffix. Use a residue name of 3 chars or fewer (e.g. 'MOL')."`; `test_validate_rejects_name_too_long` passes |
| 3   | QuickIce rejects ITP files with comb-rule=1 with a specific error message                          | ✓ VERIFIED | Live validation of `etoh_combrule1.itp` returns `is_valid=False`, `comb_rule=1`, with exact message: `"ITP comb-rule must be 2 (Lorentz-Berthelot / AMBER-GAFF2); got comb-rule=1. QuickIce does not auto-convert A/B rules. Please regenerate the ITP with comb-rule=2."`; `test_validate_rejects_comb_rule_1` passes |
| 4   | Custom guest is registered in sys.modules on the main thread before HydrateWorker starts (thread-safe) | ✓ VERIFIED | `hydrate_generator.py::generate()` builds the module on the caller's (main) thread, registers via `custom_guest_module` context manager BEFORE `_run_via_api` runs; `register_custom_guest`/`unregister_custom_guest` pair provided for QThread async path (docstring: "call this on the main thread BEFORE HydrateWorker.start()"); `test_register_unregister_pair` + `test_context_manager_registers_and_cleans_up` (uses `safe_import`) pass |
| 5   | sys.modules injection is cleaned up after generation completes (no stale module pollution)         | ✓ VERIFIED | `custom_guest_module` context manager uses `try/finally` with `sys.modules.pop(key, None)` (lines 349-353); live integration confirms `'genice2.molecules.etoh_integ' not in sys.modules` after `generate()`; `test_sys_modules_clean_after_generation` + `test_context_manager_cleans_up_on_exception` pass |

**Score:** 5/5 phase success criteria verified

### Per-Plan Must-Have Verification

#### Plan 40-01: ITP comb-rule parser + test fixtures (5/5 truths)

| Truth                                                                 | Status     | Evidence |
| --------------------------------------------------------------------- | ---------- | -------- |
| parse_itp_defaults_comb_rule returns 2 for ITP/TOP with comb-rule=2    | ✓ VERIFIED | `itp_parser.py:204` `return int(fields[1])`; `test_comb_rule_2` + `test_etoh_top_returns_2` pass |
| Returns 1 for comb-rule=1                                              | ✓ VERIFIED | `test_comb_rule_1` + `test_etoh_combrule1_fixture_returns_1` pass |
| Returns None when [ defaults ] section absent                         | ✓ VERIFIED | `itp_parser.py:195-196` `if not match: return None`; `test_defaults_absent_returns_none` (etoh.itp has no [ defaults ]) passes |
| Ignores comment lines (; and #) and blank lines                        | ✓ VERIFIED | `itp_parser.py:199-200` skips `;`/`#`/blank; `test_comment_lines_ignored` + `test_hash_comments_ignored` pass |
| Returns None for malformed comb-rule values                           | ✓ VERIFIED | `itp_parser.py:205-206` `except (ValueError, IndexError): return None`; `test_malformed_comb_rule_returns_none` passes |

**Artifacts:** `itp_parser.py` (207 lines, has `parse_itp_defaults_comb_rule`), `etoh_combrule1.itp` (89 lines, has `[ defaults ]` comb-rule=1), `test_itp_parser_combrule.py` (10 tests, all pass). **Key links:** test imports `parse_itp_defaults_comb_rule` ✓; consumed by `custom_guest_bridge.py:40-43, 268` ✓

#### Plan 40-02: [ atoms ] resname rewrite in transform_guest_itp (5/5 truths)

| Truth                                                                 | Status     | Evidence |
| --------------------------------------------------------------------- | ---------- | -------- |
| transform_guest_itp rewrites [ atoms ] resname to {guest_name}_H      | ✓ VERIFIED | `gromacs_writer.py:722` `content = _rewrite_atoms_section_resname(content, new_name)`; `test_custom_guest_resname_rewritten` asserts fields[3]=="MOL_H" |
| All non-comment atom lines rewritten consistently                       | ✓ VERIFIED | `test_all_atom_lines_rewritten` asserts all 9 etoh atom lines have resname MOL_H |
| Built-in guests (CH4 -> CH4_H) backward compat                        | ✓ VERIFIED | `test_builtin_ch4_backward_compat` asserts moleculetype "CH4_H" + atoms resname "CH4_H" |
| Comment lines and blank lines preserved, not rewritten                 | ✓ VERIFIED | `gromacs_writer.py:623-625` preserves comment/blank lines; `test_comment_lines_preserved` asserts `;` header preserved verbatim |
| ITP with no [ atoms ] does not crash (graceful no-op)                  | ✓ VERIFIED | `gromacs_writer.py:611-613` `if not match: return content`; `test_no_atoms_section_no_crash` passes |

**Artifacts:** `gromacs_writer.py` `_rewrite_atoms_section_resname` (lines 571-637) + Step 3 in `transform_guest_itp` (line 722); `test_transform_guest_itp_atoms.py` (7 tests, all pass). **Key links:** test imports `transform_guest_itp` ✓; `transform_guest_itp` is WIRED — used in `gui/hydrate_export.py:185` and `cli/itp_helpers.py:189` ✓

#### Plan 40-03: HydrateConfig extension for custom guests (5/5 truths)

| Truth                                                                 | Status     | Evidence |
| --------------------------------------------------------------------- | ---------- | -------- |
| Accepts custom guest_type with guest_residue_name                     | ✓ VERIFIED | `types.py:503-530` custom branch; `test_custom_guest_valid` asserts is_custom_guest=True, guest_name="MOL" |
| Requires explicit guest_atom_labels/count/gro_path (no auto-populate)  | ✓ VERIFIED | `types.py:505-527` four `ValueError` checks; `test_custom_guest_without_{residue_name,atom_labels,atom_count,gro_path}_raises` pass (4 tests) |
| is_custom_guest property (True custom, False built-in)                | ✓ VERIFIED | `types.py:564-567` `return self.guest_type not in GUEST_MOLECULES`; tests assert True/False correctly |
| Built-ins auto-populate metadata (backward compat)                    | ✓ VERIFIED | `types.py:531-539` else branch auto-populates; `test_builtin_ch4_still_works` (name="Methane", 5 atoms) + `test_builtin_thf_still_works` (13 atoms) pass |
| from_dict passes guest_residue_name and guest_gro_path through        | ✓ VERIFIED | `types.py:560-561` passes both fields; `test_from_dict_passes_custom_fields` + `test_from_dict_backward_compat` pass |

**Artifacts:** `types.py` HydrateConfig (guest_residue_name:479, guest_gro_path:480, is_custom_guest:564-567, custom validation:503-530, from_dict:560-561); `test_hydrate_config_custom.py` (10 tests, all pass). **Key links:** `hydrate_generator.py:136,158,609,768` uses `config.is_custom_guest`, `config.guest_residue_name`, `config.guest_gro_path` ✓

#### Plan 40-04: Custom guest bridge — build + validate + inject + cleanup (8/8 truths)

| Truth                                                                 | Status     | Evidence |
| --------------------------------------------------------------------- | ---------- | -------- |
| build_custom_guest_module produces centered Molecule (mean ~0, correct labels_, name_) | ✓ VERIFIED | `custom_guest_bridge.py:126-127` `centered = positions - centroid`; `test_build_valid_etoh` asserts mean < 1e-10, 9 labels, name_="MOL", shape (9,3) |
| validate rejects unparseable GRO with clear error                     | ✓ VERIFIED | `custom_guest_bridge.py:225-231` catches `(ValueError, OSError, IndexError)`; `test_validate_rejects_not_gro` + `test_validate_rejects_mismatch` pass |
| validate rejects atom count mismatch                                  | ✓ VERIFIED | `custom_guest_bridge.py:246-250`; `test_validate_rejects_mismatch` asserts "Atom count mismatch" or "parse" |
| validate rejects residue names >3 chars (specific message)            | ✓ VERIFIED | `custom_guest_bridge.py:255-261` exact message; `test_validate_rejects_name_too_long` passes |
| validate rejects comb-rule=1 (specific message)                       | ✓ VERIFIED | `custom_guest_bridge.py:276-281` exact message; `test_validate_rejects_comb_rule_1` passes |
| custom_guest_module context manager registers + cleans up (try/finally) | ✓ VERIFIED | `custom_guest_bridge.py:347-353` registers then `finally: sys.modules.pop`; `test_context_manager_registers_and_cleans_up` + `test_context_manager_cleans_up_on_exception` pass |
| register/unregister pair works for GUI async                          | ✓ VERIFIED | `custom_guest_bridge.py:356-394`; `test_register_unregister_pair` + `test_unregister_when_absent_is_safe` + `test_re_register_after_cleanup` pass |
| safe_import finds injected module after registration                  | ✓ VERIFIED | `test_context_manager_registers_and_cleans_up` uses `safe_import("molecule","etoh_cm")` asserts `loaded is mod`; live manual check confirms safe_import returns the injected module |

**Artifacts:** `custom_guest_bridge.py` (394 lines, ≥120 min); `test_custom_guest_bridge.py` (13 tests, all pass). **Key links:** imports from `gro_parser` (parse_gro_file, extract_residue_name_from_gro) ✓, `itp_parser` (parse_itp_file, parse_itp_defaults_comb_rule) ✓, `genice2.molecules.Molecule` via exec'd code (line 152-162) ✓, `sys.modules` injection (lines 347, 377, 393) ✓

#### Plan 40-05: Integrate bridge into hydrate generator + E2E test (6/6 truths)

| Truth                                                                 | Status     | Evidence |
| --------------------------------------------------------------------- | ---------- | -------- |
| generate() with custom guest produces HydrateStructure with guest_count > 0 | ✓ VERIFIED | Live: guest_count=8, water_count=46; `test_custom_guest_placed_in_cages` asserts guest_count > 0 |
| Custom guest atoms placed in cage positions (not all at origin)       | ✓ VERIFIED | `test_custom_guest_positions_not_all_at_origin` asserts max\|pos\| > 0.1 nm; GenIce2 arrange() adds cage center to centered sites_ |
| sys.modules does NOT contain custom guest key after generation        | ✓ VERIFIED | `test_sys_modules_clean_after_generation` asserts key absent; live check confirms clean |
| _build_molecule_index identifies custom guest by guest_residue_name   | ✓ VERIFIED | `hydrate_generator.py:609` `guest_res_name = getattr(config, "guest_residue_name", "") or guest_type.upper()`; `test_custom_guest_molecule_index_identified` asserts mol_type=="etoh_e2e", no "unknown" |
| Built-in guests (ch4, thf) generate unchanged (no regression)         | ✓ VERIFIED | `test_builtin_ch4_still_generates` + `test_builtin_thf_still_generates` pass; regression suite `test_e2e_hydrate_generation.py` 16/16 pass; ch4 derived guest_res_name="CH4" (backward compat verified) |
| _generate_report does not raise KeyError for custom guests            | ✓ VERIFIED | `hydrate_generator.py:768-777` `elif config.is_custom_guest:` branch avoids GUEST_MOLECULES lookup; live report generation succeeds (no KeyError) |

**Artifacts:** `hydrate_generator.py` generate() (lines 102-194: lazy import + context manager wrap), _build_molecule_index (line 609: guest_residue_name fallback), _generate_report (lines 768-777: custom branch); `test_e2e_custom_guest_hydrate.py` (7 tests, all pass). **Key links:** imports `build_custom_guest_module, custom_guest_module` (line 140-143) ✓; uses `config.is_custom_guest/guest_residue_name/guest_gro_path` ✓; sys.modules via context manager ✓

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `quickice/structure_generation/itp_parser.py` | parse_itp_defaults_comb_rule | ✓ VERIFIED | 207 lines, function at lines 163-207, handles absent/valid/malformed/comments |
| `quickice/data/custom/test_invalid/etoh_combrule1.itp` | [ defaults ] comb-rule=1 fixture | ✓ VERIFIED | 89 lines, [ defaults ] block at top with comb-rule=1, parser returns 1 |
| `quickice/data/custom/test_invalid/README.md` | Documents etoh_combrule1.itp | ✓ VERIFIED | Row added: "ITP with [ defaults ] comb-rule=1 (should be rejected) \| Test comb-rule=1 rejection (GUEST-07)" |
| `quickice/output/gromacs_writer.py` | _rewrite_atoms_section_resname + Step 3 | ✓ VERIFIED | 3278 lines total; _rewrite_atoms_section_resname (571-637) + Step 3 call (722); scoped to [ atoms ] only |
| `quickice/structure_generation/types.py` | guest_residue_name, guest_gro_path, is_custom_guest | ✓ VERIFIED | 1013 lines; fields at 479-480, property at 564-567, custom validation at 503-530, from_dict at 560-561 |
| `quickice/structure_generation/custom_guest_bridge.py` | build/validate/inject/cleanup primitives | ✓ VERIFIED | 394 lines (≥120 min); build (71-174), validate (177-313), context manager (316-353), register/unregister (356-394) |
| `quickice/structure_generation/hydrate_generator.py` | generate() bridge integration | ✓ VERIFIED | 793 lines; generate() custom branch (136-165), _build_molecule_index (609), _generate_report (768-777) |
| `tests/test_itp_parser_combrule.py` | 10 unit tests | ✓ VERIFIED | 10 tests, all pass |
| `tests/test_transform_guest_itp_atoms.py` | 7 unit tests | ✓ VERIFIED | 7 tests, all pass |
| `tests/test_hydrate_config_custom.py` | 10 unit tests | ✓ VERIFIED | 10 tests, all pass |
| `tests/test_custom_guest_bridge.py` | Build/validate/inject/cleanup tests | ✓ VERIFIED | 13 tests, all pass |
| `tests/test_e2e_custom_guest_hydrate.py` | E2E test | ✓ VERIFIED | 7 tests, all pass (module-scoped fixture amortizes GenIce2 call) |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `test_itp_parser_combrule.py` | `itp_parser.py` | `import parse_itp_defaults_comb_rule` | ✓ WIRED | Test imports function (line 17); function used in custom_guest_bridge.py:268 |
| `test_transform_guest_itp_atoms.py` | `gromacs_writer.py` | `import transform_guest_itp` | ✓ WIRED | Test imports (line 22); transform_guest_itp used in gui/hydrate_export.py:185 + cli/itp_helpers.py:189 |
| `test_hydrate_config_custom.py` | `types.py` | `import HydrateConfig` | ✓ WIRED | Test imports (line 15); HydrateConfig used in hydrate_generator.py + GUI + CLI |
| `custom_guest_bridge.py` | `gro_parser.py` | `import parse_gro_file, extract_residue_name_from_gro` | ✓ WIRED | Lines 36-39; parse_gro_file used at 116, extract_residue_name_from_gro at 254 |
| `custom_guest_bridge.py` | `itp_parser.py` | `import parse_itp_file, parse_itp_defaults_comb_rule` | ✓ WIRED | Lines 40-43; parse_itp_file at 235, parse_itp_defaults_comb_rule at 268 |
| `custom_guest_bridge.py` | `genice2.molecules.Molecule` | subclass in exec'd module | ✓ WIRED | Lines 152-162 exec code subclasses Molecule; verified safe_import returns module |
| `custom_guest_bridge.py` | `sys.modules` | injection + pop | ✓ WIRED | Lines 347/352 (context manager), 377 (register), 393 (unregister) |
| `hydrate_generator.py` | `custom_guest_bridge.py` | `import build_custom_guest_module, custom_guest_module` | ✓ WIRED | Lines 140-143 (lazy import inside generate()); used at 153, 158 |
| `hydrate_generator.py` | `types.py` | `config.is_custom_guest, guest_residue_name, guest_gro_path` | ✓ WIRED | Lines 136, 154-156, 609, 768, 774 |
| `hydrate_generator.py` | `sys.modules` | context manager try/finally | ✓ WIRED | Line 158 `with custom_guest_module(...)`; cleanup via finally in bridge |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
| ----------- | ------ | -------------- |
| GUEST-01 (upload .gro+.itp, generate with cage placement) | ✓ SATISFIED | E2E test + live integration: guest_count=8, guests at cage centers |
| GUEST-02 (select cage type small/large/medium) | ⚠️ PARTIAL | Core bridge honors cage_occupancy_small/large (validated 0-100%) which controls cage placement; explicit per-cage-type GUI selection control is out of scope (deferred to Phase 42 Mixed Cage Occupancy). Phase success criteria #1 ("specified cage positions") satisfied via occupancy settings. |
| GUEST-03 (cage occupancy 0-100% for custom guest) | ✓ SATISFIED | HydrateConfig cage_occupancy_small/large validated in __post_init__ (types.py:496-499); works for custom guests (unchanged) |
| GUEST-04 (GRO parseable validation) | ✓ SATISFIED | validate_custom_guest_files step 1 (custom_guest_bridge.py:223-231) |
| GUEST-05 (ITP parseable validation) | ✓ SATISFIED | validate_custom_guest_files step 2 (custom_guest_bridge.py:234-243) |
| GUEST-06 (reject residue names >3 chars) | ✓ SATISFIED | SC #2; custom_guest_bridge.py:255-261 exact message |
| GUEST-07 (reject comb-rule=1) | ✓ SATISFIED | SC #3; custom_guest_bridge.py:276-281 exact message |
| GUEST-08 (register in sys.modules, safe_import finds it) | ✓ SATISFIED | SC #4; verified safe_import returns injected module |
| GUEST-09 (cleanup sys.modules) | ✓ SATISFIED | SC #5; context manager try/finally + register/unregister pair |
| GUEST-10 (thread-safe main-thread registration) | ✓ SATISFIED | SC #4; generate() builds on caller's thread; register_custom_guest docstring: "call this on the main thread BEFORE HydrateWorker.start()" |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `molecule_validator.py` | 17-18 | "placeholders" / "XXX" in GENERIC_RESIDUE_NAMES set | ℹ️ Info | Not a stub — "XXX" is a literal generic residue name string in a set; "placeholders" describes generic names. Pre-existing, not modified in this phase. |
| `gromacs_writer.py` | 1493 | "placeholder" in docstring | ℹ️ Info | Not a stub — describes fallback "XX" label behavior. Pre-existing, not in transform_guest_itp path. |

**No blocker anti-patterns found** in phase 40 modified files (custom_guest_bridge.py, itp_parser.py, types.py, hydrate_generator.py generate/_build_molecule_index/_generate_report, gromacs_writer.py transform_guest_itp). No TODO/FIXME/HACK/stub patterns in the new/modified code.

### Test Execution Results

| Test Suite | Result | Details |
| ---------- | ------ | ------- |
| `tests/test_itp_parser_combrule.py` | ✓ 10/10 pass | comb-rule parser: valid/invalid/absent/malformed/comments/boundaries |
| `tests/test_transform_guest_itp_atoms.py` | ✓ 7/7 pass | [ atoms ] resname rewrite: custom/built-in/comments/no-crash/scoping |
| `tests/test_hydrate_config_custom.py` | ✓ 10/10 pass | HydrateConfig custom: valid/missing-fields/backward-compat/from_dict |
| `tests/test_custom_guest_bridge.py` | ✓ 13/13 pass | build/validate/inject/cleanup: all reject paths + lifecycle |
| `tests/test_e2e_custom_guest_hydrate.py` | ✓ 7/7 pass | E2E: cage placement, molecule_index, sys.modules clean, positions, regression |
| `tests/test_e2e_hydrate_generation.py` (regression) | ✓ 16/16 pass | No regression in built-in ch4/thf/sI/sII generation |
| **Total** | **✓ 63/63 pass** | 50 phase tests + 16 regression tests, 1.81s combined |

### Live Integration Verification

```
HydrateStructureGenerator().generate(HydrateConfig(
    lattice_type='sI', guest_type='etoh_integ', guest_residue_name='MOL',
    guest_gro_path='quickice/data/custom/etoh.gro',
    guest_itp_path='quickice/data/custom/etoh.itp',
    guest_atom_labels=['H','C','H','H','C','H','H','O','H'], guest_atom_count=9))
→ guest_count=8, water_count=46, total_atoms=256
→ mol_types={'water', 'etoh_integ'}  (custom guest identified, no 'unknown')
→ sys_modules_clean  (context manager cleanup worked)
→ report succeeds (no KeyError)
```

### Human Verification Required

The following items are **out of scope for this core-bridge phase** (no GUI files modified — confirmed via `git diff --stat`: only custom_guest_bridge.py, hydrate_generator.py, types.py, itp_parser.py, gromacs_writer.py touched). They will need human testing when the GUI integration phase binds these core APIs to UI widgets:

1. **GUI upload flow** — file picker for .gro + .itp, validation feedback in UI
   - Expected: User selects files via dialogs; validation errors (name >3 chars, comb-rule=1) surface as message boxes; generation kicks off
   - Why human: Phase 40 is the core bridge; GUI widgets are a later phase. The HydrateConfig API + generate() are the programmatic entry points.

2. **Visual VTK rendering of custom guest in cages**
   - Expected: Custom ethanol molecules render at cage centers (not clustered at origin), visually distinct from water framework
   - Why human: VTK rendering is GUI-path work; this phase only proves positions are correct programmatically (test_custom_guest_positions_not_all_at_origin asserts max|pos| > 0.1 nm). Visual confirmation requires a display (QT_QPA_PLATFORM=offscreen may still crash per AGENTS.md).

### Gaps Summary

No gaps found. All 29 must-have truths across 5 plans are verified as TRUE in the actual codebase (not just SUMMARY claims). All 5 phase success criteria are demonstrably TRUE via code inspection + test execution + live integration:

- **SC #1** (upload + generate + cage placement): E2E test + live run produce guest_count=8 with atoms at cage centers (max|pos| > 0.1 nm, not origin)
- **SC #2** (reject name >3 chars): Exact error message verified against synthetic 'ETHAN' GRO
- **SC #3** (reject comb-rule=1): Exact error message verified against etoh_combrule1.itp fixture
- **SC #4** (thread-safe main-thread registration): generate() builds module on caller's thread; context manager registers before _run_via_api; register_custom_guest provided for QThread async path
- **SC #5** (sys.modules cleanup): Context manager try/finally pops key; verified clean after live generation; exception path also cleans up

The only partial requirement is GUEST-02 (explicit per-cage-type GUI selection), which is intentionally deferred to Phase 42 (Mixed Cage Occupancy) — the core bridge honors occupancy settings that satisfy SC #1's "specified cage positions".

---

_Verified: 2026-07-03_
_Verifier: OpenCode (gsd-verifier)_
