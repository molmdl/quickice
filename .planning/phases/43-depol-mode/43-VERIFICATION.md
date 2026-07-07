---
phase: 43-depol-mode
verified: 2026-07-07T00:00:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
human_verification:
  - test: "Visual sanity of Depolarization group in Hydrate tab"
    expected: "Group labeled 'Depolarization' with a 'Depol mode:' row showing a QComboBox (default text 'Strict (ice rules, zero net dipole)') and a help icon; positioned between Supercell and Lattice info groups."
    why_human: "Pixel-level layout/appearance cannot be verified programmatically. Structural placement (lines 78-87) and widget hierarchy are verified; headless test exercises the combo."
  - test: "Full click-through flow: change depol combo -> click Generate -> observe structure"
    expected: "Changing combo to Optimal and generating produces a valid hydrate structure (same atom count as Strict per e2e invariant)."
    why_human: "End-to-end GUI→worker→GenIce2 click flow not directly exercised in one test (each link is verified independently by automated tests). Optional confirmation only."
---

# Phase 43: Depol Mode Verification Report

**Phase Goal:** Users can select depol mode for hydrate generation, with strict as the safe default
**Verified:** 2026-07-07
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | HydrateConfig carries a depol_mode field defaulting to 'strict' | ✓ VERIFIED | `types.py:561` `depol_mode: str = "strict"`; test `test_depol_mode_default_is_strict` passes |
| 2 | Invalid depol_mode (e.g. 'none', 'banana') raises ValueError in __post_init__ | ✓ VERIFIED | `types.py:586-589` `if self.depol_mode not in ("strict", "optimal"): raise ValueError(...)`; tests `test_depol_mode_invalid_none_raises` & `test_depol_mode_invalid_banana_raises` pass |
| 3 | config.depol_mode reaches GenIce2 generate_ice() as the depol kwarg | ✓ VERIFIED | `hydrate_generator.py:317` `depol=config.depol_mode` (diff confirms swap from hardcoded `'strict'`); e2e test `test_generate_with_optimal_depol_succeeds` calls real `gen.generate(config)` with `depol_mode="optimal"` and asserts `structure.water_count > 0` |
| 4 | Existing HydrateConfig call sites still work unchanged (backward compat) | ✓ VERIFIED | `depol_mode` is the LAST dataclass field with default `"strict"` — all existing keyword/positional calls unchanged; `generator.py` ice-path hardcode UNCHANGED (1× `depol='strict'`, 0× `depol_mode` in generator.py); full regression 200 tests pass |
| 5 | from_dict passes depol_mode through when present, defaults to 'strict' when absent | ✓ VERIFIED | `types.py:759` `depol_mode=d.get("depol_mode", "strict")`; tests `test_from_dict_depol_passthrough_explicit` & `test_from_dict_depol_defaults_to_strict` pass |
| 6 | User can select strict or optimal in the Hydrate tab via a QComboBox | ✓ VERIFIED | `hydrate_panel.py:209` `self.depol_combo = QComboBox()`; `:210-211` addItem Strict/Optimal; test `test_depol_combo_has_two_items` asserts count==2 with data {strict, optimal} |
| 7 | Selected depol mode flows into HydrateConfig via get_configuration() | ✓ VERIFIED | `hydrate_panel.py:506` `depol_mode=self.depol_combo.currentData()`; test `test_get_configuration_default_depol_is_strict` switches to optimal and asserts `cfg2.depol_mode == "optimal"` |
| 8 | Default selection is strict (combo index 0, data 'strict') | ✓ VERIFIED | `hydrate_panel.py:210` first addItem is Strict with data "strict"; test `test_depol_combo_default_is_strict` asserts `currentIndex()==0` and `currentData()=="strict"` |
| 9 | Changing the depol combo emits configuration_changed | ✓ VERIFIED | `hydrate_panel.py:395` `self.depol_combo.currentIndexChanged.connect(lambda: self.configuration_changed.emit())`; test `test_depol_combo_change_emits_configuration_changed` connects to signal and asserts emission on switch |
| 10 | The depol group renders between the supercell group and the info group | ✓ VERIFIED | `hydrate_panel.py:78-87` ordering: `supercell_group` (line 78) → `depol_group` (line 82) → `info_group` (line 86), all added to `left_layout` in sequence |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `quickice/structure_generation/types.py` | depol_mode field + __post_init__ validation + from_dict passthrough | ✓ VERIFIED | Lines 559-561 (field), 583-589 (validation), 759 (from_dict). Substantive (1232 lines); no stubs. |
| `quickice/structure_generation/hydrate_generator.py` | generate_ice passes config.depol_mode | ✓ VERIFIED | Line 317 `depol=config.depol_mode`. Diff confirms 1-line swap from hardcoded `'strict'`. |
| `tests/test_hydrate_config_metadata.py` | Unit tests for depol_mode default/override/from_dict | ✓ VERIFIED | `TestDepolMode` class with 6 tests, all pass. Real assertions (`pytest.raises(ValueError)`, `assert config.depol_mode == ...`). |
| `tests/test_hydrate_lattice_types.py` | e2e depol passthrough test | ✓ VERIFIED | `TestDepolModePassthrough` with module-scoped fixtures making real `gen.generate(config)` calls. 2 tests pass. |
| `quickice/gui/hydrate_panel.py` | _create_depol_group + _setup_ui insertion + _setup_connections + get_configuration passthrough | ✓ VERIFIED | Lines 203-224 (group), 82-83 (insertion), 395 (connection), 506 (get_configuration). Substantive (547 lines); no stubs. |
| `tests/test_hydrate_panel.py` | Headless GUI tests for depol combo | ✓ VERIFIED | `TestDepolCombo` class with 4 tests, all pass headless (QT_QPA_PLATFORM=offscreen). Real QComboBox assertions. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `hydrate_generator.py` _run_via_api | `HydrateConfig.depol_mode` | `depol=config.depol_mode` at generate_ice call | ✓ WIRED | Line 317; e2e test exercises full path to GenIce2 |
| `HydrateConfig.__post_init__` | `ValueError` on invalid depol_mode | `if depol_mode not in ("strict","optimal"): raise` | ✓ WIRED | Lines 586-589; 2 invalid-value tests pass |
| `HydrateConfig.from_dict` | `HydrateConfig.depol_mode` | `d.get("depol_mode", "strict")` | ✓ WIRED | Line 759; explicit + default tests pass |
| `hydrate_panel.py` get_configuration | `HydrateConfig(depol_mode=...)` | `depol_mode=self.depol_combo.currentData()` | ✓ WIRED | Line 506; round-trip test asserts strict→optimal switch |
| `hydrate_panel.py` _setup_connections | `configuration_changed` signal | `depol_combo.currentIndexChanged → configuration_changed.emit()` | ✓ WIRED | Line 395; signal-emission test passes |
| `hydrate_panel.py` _setup_ui | left_layout order | supercell → depol → info | ✓ WIRED | Lines 78-87; structural order confirmed in source |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
| --- | --- | --- |
| DEPOL-01: User can select depol mode (strict/optimal) in Hydrate tab | ✓ SATISFIED | None — QComboBox with 2 items wired to get_configuration (truths 6, 7, 8) |
| DEPOL-02: Depol mode is passed through to GenIce2 generate_ice() call | ✓ SATISFIED | None — `depol=config.depol_mode` at line 317, e2e test confirms (truths 1, 3) |
| DEPOL-03: Default depol mode is 'strict' (preserves current behavior) | ✓ SATISFIED | None — field default "strict", combo index 0 "strict", from_dict defaults "strict", ice-path hardcode unchanged (truths 1, 4, 5, 8) |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| (none) | — | — | — | No TODO/FIXME/placeholder/empty-return/stub-handler patterns found in any of the 3 modified source files |

### Scope Boundaries

| Boundary | Expected | Status | Evidence |
| --- | --- | --- | --- |
| `hydrate_worker.py` unmodified | No edits | ✓ HONORED | Not in `git show --stat` for any 43-01/43-02 commit |
| `gromacs_writer.py` unmodified | No edits | ✓ HONORED | Not in `git show --stat` for any 43-01/43-02 commit |
| `cli/pipeline.py` unmodified | No edits | ✓ HONORED | Not in `git show --stat` for any 43-01/43-02 commit |
| `generator.py` ice-path hardcode unchanged | 1× `depol='strict'`, 0× `depol_mode` | ✓ HONORED | `grep -c "depol='strict'" generator.py` = 1; `grep -c "depol_mode" generator.py` = 0 |
| No "none" combo item | 0× `"none"` in hydrate_panel.py | ✓ HONORED | `grep -c '"none"' hydrate_panel.py` = 0 |

### Human Verification Required

Two optional visual/flow confirmations are noted (NOT blocking — automated checks fully verify goal achievement):

### 1. Visual sanity of Depolarization group

**Test:** Launch the GUI on a display, open the Hydrate tab, locate the "Depolarization" group.
**Expected:** A QGroupBox titled "Depolarization" with a "Depol mode:" row containing a QComboBox (default text "Strict (ice rules, zero net dipole)") and a help icon, positioned between the Supercell group and the Lattice info group.
**Why human:** Pixel-level appearance cannot be verified headless; structural placement (lines 78-87) and widget hierarchy are already verified, and the headless test exercises the combo's behavior.

### 2. Full click-through flow

**Test:** In the GUI, switch the depol combo to "Optimal", click Generate, wait for the structure.
**Expected:** A valid hydrate structure renders with the same atom count as "Strict" (per the documented GenIce2 2.2.13.1 invariant — both modes set dipoleOptimizationCycles=1000).
**Why human:** The end-to-end GUI→worker→GenIce2 click flow is not exercised in a single test; each link is verified independently (combo+signal, get_configuration, e2e generate). Optional confirmation only.

### Gaps Summary

No gaps found. All 10 must-have truths verified against actual source code and passing tests:

- **Config layer (43-01):** `depol_mode: str = "strict"` field added as the LAST dataclass field (backward compatible); `__post_init__` validates against `{"strict","optimal"}` rejecting "none" and typos; `from_dict` threads through with strict default; `hydrate_generator.py` swaps hardcoded `'strict'` for `config.depol_mode` at the single `generate_ice` call site. The ice-path generator (`generator.py:126`) retains its hardcoded `depol='strict'` — explicitly out of scope for Phase 43 (CLI `--depol` is Phase 45).
- **GUI layer (43-02):** `_create_depol_group()` adds a QComboBox mirroring the established lattice-combo pattern (QComboBox + HelpIcon + addStretch + QFormLayout row); inserted between supercell and info groups; `_setup_connections` wires `currentIndexChanged` → `configuration_changed`; `get_configuration` passes `depol_combo.currentData()` as `depol_mode` kwarg. Default is index 0 / "strict".

Test evidence: 12 depol-specific tests pass (6 config-metadata unit, 2 lattice-types e2e with real GenIce2 calls, 4 headless GUI); full-file regression 200 tests pass (36 + 154 + 10); no anti-patterns in modified source; scope boundaries honored (no edits to hydrate_worker/gromacs_writer/cli/pipeline; generator.py ice-path hardcode unchanged; no "none" combo item).

Phase goal "Users can select depol mode for hydrate generation, with strict as the safe default" is ACHIEVED. DEPOL-01, DEPOL-02, DEPOL-03 SATISFIED.

---

_Verified: 2026-07-07_
_Verifier: OpenCode (gsd-verifier)_
