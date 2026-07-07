# Phase 43: Depol Mode - Research

**Researched:** 2026-07-07
**Domain:** GenIce2 `generate_ice()` depolarization parameter + QuickIce HydrateConfig/GUI wiring
**Confidence:** HIGH (GenIce2 source inspected + empirically verified; QuickIce source read directly)

## Summary

This is a **small, low-risk, well-scoped phase** — essentially a 1-line passthrough plus a GUI combo box. The GenIce2 `depol` parameter is already known and currently hardcoded to `'strict'` at exactly **one** in-scope call site (`hydrate_generator.py:317`). The work is: (1) add a `depol_mode: str = "strict"` field to `HydrateConfig` with `{"strict","optimal"}` validation, (2) pass `config.depol_mode` into the existing `ice.generate_ice(...)` call, (3) thread it through `from_dict()`, and (4) add a `QComboBox` in the Hydrate tab wired exactly like the existing lattice combo. **No blockers. No new dependencies. No export/worker changes.** Backward compatibility is automatic — every existing `HydrateConfig(...)` call site uses keyword args and will silently pick up the `"strict"` default, preserving current behavior.

**One critical caveat the planner MUST internalize:** in GenIce2 2.2.13.1, `'strict'` and `'optimal'` are **functionally identical** — both set `dipoleOptimizationCycles=1000`. Only `'none'` differs (iter=0, no depolarization → physically unrealistic). QuickIce exposes `strict`/`optimal` per the ROADMAP and **excludes `none`**. The phase still has value: it wires the passthrough so that when the distinction becomes real (e.g. GenIce3 `pol_loop_1`/`pol_loop_2`), QuickIce is ready, and it gives users a visible knob. **Tests must NOT assert that strict and optimal produce different structures** — they don't (same atom count, same depol effort).

**Primary recommendation:** Add `depol_mode` as the last `HydrateConfig` field with `"strict"` default + `__post_init__` validation against `{"strict","optimal"}`; replace the single `depol='strict'` literal at `hydrate_generator.py:317` with `depol=config.depol_mode`; add a `QComboBox` group in `hydrate_panel.py` mirroring the lattice-combo pattern; wire `get_configuration()` + `_setup_connections()`. Two plans: 43-01 (config + passthrough + tests), 43-02 (GUI combo + tests).

## GenIce2 depol API

### Valid values (VERIFIED in source + empirically)

The `generate_ice()` signature (`genice2/genice.py:678-687`):
```python
def generate_ice(self, formatter, water=None, guests={}, depol="strict",
                 noise=0.0, assess_cages=False, target_polarization=(0.0,0.0,0.0)):
```
- **Default:** `"strict"` (matches current QuickIce hardcode — no behavior change).
- **Documented values** (GenIce2 CLI help, `cli/genice.py:165`): `'Depolarization. (strict, optimal, or none) ["strict"]'`.
- **Accepted values:** ANY string is accepted — GenIce2 does **no validation**. Empirically confirmed `strict`, `optimal`, `none` all run without error (sI 1×1×1 → 184 atoms each).

### Semantics — IMPORTANT: strict ≡ optimal in 2.2.13.1

The `depol` value flows to `Stage34E` (`genice.py:746`), whose entire branching logic is (`genice.py:936-954`):
```python
def Stage34E(self, depol: str = "none", target_polarization=(0.0,0.0,0.0)):
    if depol == "none":
        iter = 0
    else:
        iter = 1000
    self.digraph = genice_core.ice_graph(..., dipoleOptimizationCycles=iter, ...)
```
- `depol == "none"` → `dipoleOptimizationCycles = 0` (NO depolarization; nonzero net dipole → physically unrealistic).
- **anything else** (including `"strict"` AND `"optimal"`) → `dipoleOptimizationCycles = 1000` (full depolarization).

**Therefore `strict` and `optimal` produce identical depolarization effort in GenIce2 2.2.13.1.** There is no `if depol == "strict"` or `if depol == "optimal"` branch anywhere in the package (grep-verified). Some lattice plugins use `--depol=optimal` (HS1, iceR, iceT2) and others `--depol=none` (H-ordered ices: 11i, ice14, ice8) in their test options, but the runtime behavior of `optimal` == `strict`.

> **Note:** The earlier `.planning/research/v4.7-STACK.md` row says "strict = ice rules, optimal = relaxed" with "✅ both modes". That research verified both modes are *accepted* (don't crash), not that they *differ*. The source code is definitive: they do not differ in 2.2.13.1. The distinction is **intended** (per CLI help / GenIce3 design) but **not implemented** in this GenIce2 version. Forward-compatibility value: GenIce3 replaces `depol` with `pol_loop_1`/`pol_loop_2` integers (see `.planning/research/future-ml/genice3-upgrade/01-API-MIGRATION-MAP.md:208-217`), where the distinction *is* real.

### What QuickIce should expose

Per ROADMAP/REQUIREMENTS: **`strict` and `optimal` only; `none` excluded; `strict` is the default.**
- Excluding `none` is correct — it yields physically unrealistic structures (nonzero net dipole). The GenIce2 H-ordered ice lattices use `none` internally, but QuickIce's hydrate path should never offer it to users.
- QuickIce's `HydrateConfig.__post_init__` is the **only gatekeeper** for valid values (GenIce2 won't reject `depol="banana"` — it would silently run iter=1000). Validation here is mandatory.

## Current code state

### Hardcode location (the ONE in-scope site)

`quickice/structure_generation/hydrate_generator.py:312-318` — inside `_run_via_api()`, after the per-cage `parse_guest` loop:
```python
# Generate hydrate structure using GenIce API
gro_string = ice.generate_ice(
    formatter=formatter,
    water=water,
    guests=guests,
    depol='strict'          # <-- line 317: the ONLY change → depol=config.depol_mode
)
```
This is the sole in-scope edit to the generator. `config` is in scope here (`_run_via_api(self, config)`).

### Second generate_ice site — OUT OF SCOPE (do not touch)

`quickice/structure_generation/generator.py:124-127` — the **ICE candidate generator** (phase-diagram ice path, non-hydrate, uses TIP3P):
```python
# Generate ice structure with strict depolarization
gro_string = ice.generate_ice(
    formatter=formatter, water=water, depol='strict'
)
```
This is `IceStructureGenerator.generate()` (a different class, no `HydrateConfig`). **Phase 43 is hydrate-only.** Leave `generator.py` untouched. (A future phase could add depol to the ice path, but that is not in Phase 43's scope, requirements, or success criteria.)

### HydrateConfig gaps (`quickice/structure_generation/types.py:501-774`)

The `HydrateConfig` dataclass currently has **no `depol_mode` field**. Existing fields (all have defaults):
`lattice_type, guest_type, cage_occupancy_small/large, supercell_x/y/z, guest_name, guest_atom_labels, guest_atom_count, guest_itp_path, guest_residue_name, guest_gro_path, cage_guest_assignments` (last field, line 558).

- `__post_init__` (lines 560-710): validates lattice_type, occupancies, supercell, guest metadata, cage_guest_assignments. **No depol validation exists** — needs adding.
- `from_dict()` (lines 712-749): constructs from UI dict with `d.get(..., default)` per field. **No depol passthrough** — needs adding (line 748 area).

### GUI gaps (`quickice/gui/hydrate_panel.py`)

The panel has **no depol selector**. Relevant structure:
- `_setup_ui` (lines 52-165) stacks groups top-to-bottom: `lattice_group` (69) → `cage_group` (74) → `supercell_group` (78) → `info_group` (82) → generate button (86).
- Lattice combo pattern (lines 172-195) — the **template** for the depol combo:
  ```python
  lattice_row = QHBoxLayout()
  self.lattice_combo = QComboBox()
  for lattice_id, lattice_info in HYDRATE_LATTICES.items():
      self.lattice_combo.addItem(f"{lattice_id} - {lattice_info['description']}", lattice_id)
  lattice_row.addWidget(self.lattice_combo)
  lattice_row.addWidget(HelpIcon("..."))
  lattice_row.addStretch()
  layout.addRow("Lattice type:", lattice_row)
  ```
- `_setup_connections` (lines 363-370): wires `currentIndexChanged`/`valueChanged` → `configuration_changed.emit()`. Depol combo needs the same.
- `get_configuration` (lines 452-478): builds `HydrateConfig(...)` from UI — needs `depol_mode=self.depol_combo.currentData()`.

### Worker / export — NO changes needed

- `quickice/gui/hydrate_worker.py`: `HydrateWorker(QThread)` takes `HydrateConfig`, calls `generator.generate(self._config)`. Depol flows through `config` automatically. **No edit.**
- Export path (`gromacs_writer.py`, `HydrateGROMACSExporter`): depol only affects H-bond orientation **during generation**, not the GRO/topology output. **No edit.**

## Required changes (minimal diff)

### Plan 43-01: HydrateConfig + generator passthrough

**`quickice/structure_generation/types.py`:**
1. Add field (after `cage_guest_assignments`, line 558 — last field, safest minimal diff):
   ```python
   # Phase 43 depol mode: 'strict' (default, preserves current behavior) or 'optimal'.
   # 'none' is excluded — produces physically unrealistic structures (nonzero dipole).
   depol_mode: str = "strict"
   ```
2. In `__post_init__` (after the supercell check, ~line 579), add validation:
   ```python
   if self.depol_mode not in ("strict", "optimal"):
       raise ValueError(
           f"depol_mode must be 'strict' or 'optimal', got {self.depol_mode!r}"
       )
   ```
3. In `from_dict()` (line 748 area, inside the `cls(...)` call), add:
   ```python
   depol_mode=d.get("depol_mode", "strict"),
   ```

**`quickice/structure_generation/hydrate_generator.py:317`:**
```python
depol=config.depol_mode    # was: depol='strict'
```
(One line. `config` is the `_run_via_api(self, config)` parameter, already in scope.)

### Plan 43-02: GUI depol selector

**`quickice/gui/hydrate_panel.py`:**
1. Add a `_create_depol_group()` method mirroring `_create_lattice_group()`:
   ```python
   def _create_depol_group(self) -> QGroupBox:
       group = QGroupBox("Depolarization")
       layout = QFormLayout()
       row = QHBoxLayout()
       self.depol_combo = QComboBox()
       self.depol_combo.addItem("Strict (ice rules, zero net dipole)", "strict")
       self.depol_combo.addItem("Optimal (relaxed)", "optimal")
       # currentIndex 0 = strict = default
       row.addWidget(self.depol_combo)
       row.addWidget(HelpIcon(
           "Depolarization mode for hydrogen-bond orientation.\n"
           "• Strict — enforce ice rules / zero net dipole (default, safe).\n"
           "• Optimal — relaxed depolarization.\n"
           "Affects H-bond orientation only; does not change atom count."
       ))
       row.addStretch()
       layout.addRow("Depol mode:", row)
       group.setLayout(layout)
       return group
   ```
   > **Tooltip caution:** because strict≡optimal in GenIce2 2.2.13.1, do NOT promise a structural difference. The text above describes intent, not a guaranteed runtime delta. Keep it factual.
2. In `_setup_ui`, insert the group between `supercell_group` and `info_group` (~line 79-82):
   ```python
   supercell_group = self._create_supercell_group()
   left_layout.addWidget(supercell_group)
   depol_group = self._create_depol_group()      # NEW
   left_layout.addWidget(depol_group)            # NEW
   info_group = self._create_info_group()
   left_layout.addWidget(info_group)
   ```
3. In `_setup_connections` (line 370 area): `self.depol_combo.currentIndexChanged.connect(lambda: self.configuration_changed.emit())`
4. In `get_configuration` (line 472-478), add to the `HydrateConfig(...)` call: `depol_mode=self.depol_combo.currentData(),`

## Backward compatibility

**Adding a field with a default breaks NO call site** — verified by grep. Every `HydrateConfig(...)` construction in the repo uses keyword args (none positional beyond the dataclass default boundary). All existing call sites omit `depol_mode` and therefore inherit `"strict"` (the current behavior).

In-scope construction sites that must continue to work (all get `"strict"` default automatically — no edit needed):

| File:Line | Context | Passes depol_mode? | Result |
|-----------|---------|-------------------|--------|
| `quickice/gui/hydrate_panel.py:472` | `get_configuration()` | Will after 43-02 | `"strict"` default → combo sets it |
| `quickice/cli/pipeline.py:372` | CLI `_run_source_step` | No (Phase 45 adds `--depol`) | `"strict"` default → **current behavior preserved** ✓ |
| `quickice/gui/hydrate_worker.py:27` | docstring example only | N/A | N/A |
| `tests/conftest.py:74,89,104,121,135,149,163` | fixtures | No | `"strict"` default ✓ |
| `tests/test_hydrate_config_metadata.py` | many | No | `"strict"` default ✓ |
| `tests/test_hydrate_config_custom.py` | many | No | `"strict"` default ✓ |
| `tests/test_e2e_hydrate_generation.py:227,240,245,250` | invalid-config tests | No | `"strict"` default ✓ |
| `tests/test_hydrate_lattice_types.py:296+` | lattice tests | No | `"strict"` default ✓ |
| `tests/test_e2e_mixed_cage_occupancy.py`, `tests/test_e2e_custom_guest_hydrate.py`, `tests/test_cli/test_mixed_cage_cli.py`, `tests/test_cli/test_pipeline_custom_guest_export.py`, `tests/test_cli/test_itp_helpers_custom_guest.py`, `tests/e2e_export_helpers.py`, `tests/test_output/*`, `tests/test_e2e_workflow_chains.py`, `tests/test_structure_generation.py`, `tests/test_e2e_gmx_validation.py`, `tests/test_build_molecule_index.py`, `tests/test_e2e_solute_insertion.py`, `tests/test_custom_molecule_renderer.py` | various | No | `"strict"` default ✓ |

**Dataclass field-ordering note:** every existing `HydrateConfig` field already has a default, so a new defaulted field can be placed anywhere. Placing `depol_mode` **last** (after `cage_guest_assignments`) minimizes the diff and avoids touching the `__post_init__` auto-populate/shim logic. Do not place it before `cage_guest_assignments` (no benefit; larger diff).

**`from_dict` round-trip:** old UI dicts without `depol_mode` → `d.get("depol_mode", "strict")` → `"strict"` default. New UI dicts with it → passthrough. Backward compatible. ✓

## Testing strategy

### Existing test files & patterns

- **`tests/test_hydrate_config_metadata.py`** — HydrateConfig field auto-population, explicit override, `from_dict` round-trip. **Pattern to follow** for `depol_mode` unit tests (construct `HydrateConfig(...)`, assert field).
- **`tests/test_hydrate_config_custom.py`** — `pytest.raises(ValueError, match=...)` for invalid fields. **Pattern to follow** for invalid `depol_mode` validation test.
- **`tests/test_e2e_hydrate_generation.py`** — `TestHydrateInvalidConfig` (lines 221-250): `pytest.raises(ValueError, match="...")` on bad `HydrateConfig(...)`. **Pattern to follow**; can add `test_hydrate_invalid_depol_raises` here.
- **`tests/test_hydrate_lattice_types.py`** — runs `HydrateStructureGenerator().generate(HydrateConfig(lattice_type=...))` for real (GenIce2). **Pattern** for an e2e depol passthrough test.
- **Existing `tests/test_gui/test_hydrate_panel*.py`** (headless, `QT_QPA_PLATFORM=offscreen`) — GUI panel get_configuration round-trip tests; mirror for depol combo. (Confirm exact path during planning.)
- **No existing depol tests** — `grep depol tests/` returns nothing. All depol tests are net-new.

### Tests to add (recommended)

**Plan 43-01 (config + passthrough):**
1. `test_depol_mode_default_is_strict` — `HydrateConfig(guest_type="ch4").depol_mode == "strict"`.
2. `test_depol_mode_optimal_passthrough` — `HydrateConfig(guest_type="ch4", depol_mode="optimal").depol_mode == "optimal"`.
3. `test_depol_mode_invalid_raises` — `pytest.raises(ValueError, match="depol_mode")` for `depol_mode="none"` and `depol_mode="banana"` (confirms `none` is rejected even though GenIce2 accepts it).
4. `test_from_dict_depol_passthrough` — `HydrateConfig.from_dict({...,"depol_mode":"optimal"}).depol_mode == "optimal"`; and `from_dict({...without depol_mode...}).depol_mode == "strict"`.
5. (e2e, optional but recommended) `test_generate_with_optimal_depol_succeeds` — `HydrateStructureGenerator().generate(HydrateConfig(lattice_type="sI", depol_mode="optimal"))` returns a structure with expected water_count. **Do NOT assert strict≠optimal** (they're identical in 2.2.13.1); just assert both succeed and have equal atom counts.

> **Strict passthrough assertion (optional rigor):** To prove `config.depol_mode` actually reaches `generate_ice`, monkeypatch `GenIce.generate_ice` to capture the `depol` kwarg and assert it equals `config.depol_mode`. This is the only way to assert passthrough without relying on a strict/optimal behavioral difference (which doesn't exist). Given the change is a 1-line literal→attribute swap, this is optional; the e2e "generates without error" test plus the field-validation tests are sufficient for a phase this small.

**Plan 43-02 (GUI):**
6. Headless GUI test: build `HydratePanel`, assert `depol_combo` defaults to index 0 / data `"strict"`.
7. `get_configuration().depol_mode == "strict"` by default; set combo to `"optimal"`, assert `get_configuration().depol_mode == "optimal"`.
8. Changing the combo emits `configuration_changed` (follow existing panel signal-test pattern).

### Test conventions (from AGENTS.md)
- pytest, default discovery; `test_*.py`.
- Module-scoped fixtures amortize GenIce2 calls (~3-5s each) — use for e2e depol generation tests.
- `tmp_path` for any temp files (none expected here — depol needs no I/O).
- Headless GUI: `QT_QPA_PLATFORM=offscreen`.
- No bare `except Exception` in `cli/pipeline.py` — not relevant (Phase 43 adds no CLI code).

## Pitfalls & edge cases

1. **strict ≡ optimal in GenIce2 2.2.13.1 (HIGH).** Source `genice.py:943` branches only on `"none"`; everything else → iter=1000. Empirically confirmed (sI 1×1×1: 184 atoms for strict/optimal/none). **Implication:** GUI tooltip must not promise a structural difference; tests must not assert strict≠optimal differ. The phase is forward-compatibility + user-visible knob, not a runtime behavioral change.
2. **`none` must be rejected by QuickIce (HIGH).** GenIce2 accepts `none` silently (iter=0 → nonzero dipole → physically unrealistic). `HydrateConfig.__post_init__` is the only gatekeeper. Validate against `{"strict","optimal"}` only.
3. **GenIce2 does not validate depol values (HIGH).** `depol="banana"` runs fine (iter=1000). QuickIce validation is mandatory and is the sole defense against typo'd values reaching GenIce2.
4. **Two `generate_ice` call sites — only one is in scope (HIGH).** `hydrate_generator.py:317` (hydrate, IN scope) and `generator.py:126` (ice candidate, OUT of scope). Do not touch `generator.py`.
5. **Export path is unaffected (HIGH).** Depol sets H-bond orientation during generation; the GRO/topology writers and `HydrateGROMACSExporter` do not read depol. No `gromacs_writer.py` edit.
6. **HydrateWorker is unaffected (HIGH).** It passes `config` opaquely to `generator.generate(config)`; depol rides along. No `hydrate_worker.py` edit.
7. **CLI default preserved (HIGH).** `cli/pipeline.py:372` omits `depol_mode` → gets `"strict"` default → byte-identical current behavior. CLI `--depol` is Phase 45 (CLI-03), NOT Phase 43.
8. **GUI-04 / Phase 44 overlap (MEDIUM).** DEPOL-01 (Phase 43) and GUI-04 (Phase 44) both describe a depol dropdown. 43-02 **implements** the dropdown (satisfies DEPOL-01); Phase 44 #4 references it as an already-integrated feature. Do not double-build — 43-02 owns the implementation.
9. **Don't reorder existing HydrateConfig fields (LOW).** Adding `depol_mode` last (after `cage_guest_assignments`) avoids disturbing the `__post_init__` legacy-shim logic and the `from_dict` field list. Reordering risks larger diffs and review burden for zero benefit.

## Out of scope

- **`quickice/structure_generation/generator.py` (ICE candidate generator, `depol='strict'` at line 126).** This is the non-hydrate phase-diagram ice path (TIP3P, `IceStructureGenerator`). Phase 43 is hydrate-only. A separate phase would be needed to add depol there.
- **CLI `--depol` flag (Phase 45 / CLI-03).** The CLI constructs `HydrateConfig` at `pipeline.py:372` without `depol_mode` (gets `"strict"` default). Adding `--depol` argparse + wiring is Phase 45. Do not add CLI surface in Phase 43.
- **Phase 44 GUI integration / validation feedback (GUI-04).** 43-02 adds the selector; Phase 44 handles broader GUI integration/validation polish. Don't pre-empt Phase 44 work.
- **Water model depol interaction, `target_polarization`, `assess_cages`, `noise`.** All out of scope; leave the existing `generate_ice` call's other kwargs untouched.

## Standard Stack

No new libraries. Phase 43 reuses the existing, verified stack:

### Core (unchanged)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| GenIce2 | 2.2.13.1 | `generate_ice(depol=...)` — the parameter being wired | Already integrated; `depol` is an existing kwarg |
| PySide6 | 6.10.2 | `QComboBox` for the depol selector | Already used for lattice/cage combos |

### Supporting (unchanged)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | (existing) | Unit + e2e tests | Field validation, from_dict, generator passthrough |

**Installation:** None. `conda` env unchanged; no `environment.yml` edit; no new deps to seek approval for.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Depol value validation | A custom validator function | `HydrateConfig.__post_init__` `if depol_mode not in ("strict","optimal")` | Matches the existing validation style (lattice_type, occupancies, supercell) — single source of truth, raises `ValueError` like all other HydrateConfig validation |
| Depol combo widget | A custom widget | `QComboBox` + `HelpIcon` (lattice-combo pattern, `hydrate_panel.py:172-195`) | Established panel pattern; consistent UX; `addItem(text, userData)` gives free id↔label separation |
| Depol passthrough | A new method/param on the generator | `config.depol_mode` read at the existing `generate_ice` call site | Depol is a generation param; `config` is already the carrier; 1-line change beats a new API surface |

**Key insight:** This phase adds a knob, not an algorithm. The "algorithm" (depolarization) is GenIce2's. QuickIce only carries a user choice to an existing kwarg. Resist any urge to interpret/transform the value — pass it through verbatim after validation.

## Common Pitfalls

### Pitfall 1: Asserting strict ≠ optimal in tests
**What goes wrong:** A test asserts `generate(depol_mode="strict")` and `generate(depol_mode="optimal")` produce different structures/atom counts.
**Why it happens:** Assumption that two exposed options imply two behaviors.
**How to avoid:** In GenIce2 2.2.13.1 both → iter=1000 (identical). Tests should assert both *succeed* and have *equal* atom counts, not that they *differ*. Use a monkeypatch on `GenIce.generate_ice` to assert the `depol` kwarg value if passthrough rigor is needed.
**Warning signs:** A test failing with "expected 184, got 184" style assertions, or flaky H-bond-orientation comparisons.

### Pitfall 2: Exposing `none` because GenIce2 accepts it
**What goes wrong:** GUI/validation allows `none`, users generate physically unrealistic hydrates (nonzero net dipole).
**Why it happens:** GenIce2's CLI help lists `none` and GenIce2 doesn't reject it.
**How to avoid:** `HydrateConfig` validation restricts to `{"strict","optimal"}`. GUI combo only offers two items. Never add a `none` item.
**Warning signs:** A three-item combo, or validation set containing `"none"`.

### Pitfall 3: Touching `generator.py` (ice path) thinking it's in scope
**What goes wrong:** Depol added to the ice candidate generator, expanding scope and risk into the phase-diagram path.
**Why it happens:** `grep depol` shows two call sites.
**How to avoid:** Only `hydrate_generator.py:317` is in scope. `generator.py:126` is the ice path (different class, no HydrateConfig). Leave it.
**Warning signs:** Edits to `generator.py` in the Phase 43 diff.

### Pitfall 4: Adding CLI `--depol` in Phase 43
**What goes wrong:** Scope creep into Phase 45 (CLI-03); larger diff; CLI test surface.
**Why it happens:** It "feels" complete to add the flag alongside the config field.
**How to avoid:** CLI `--depol` is Phase 45. Phase 43 only adds the config field + generator passthrough + GUI. The CLI `pipeline.py:372` call gets `"strict"` automatically — no edit.
**Warning signs:** argparse additions in `cli/pipeline.py` or a new `--depol` flag.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `depol='strict'` hardcoded in hydrate_generator | `depol=config.depol_mode` (Phase 43) | This phase | User-selectable; default unchanged |
| No depol field on HydrateConfig | `depol_mode: str = "strict"` field + validation | This phase | Validates values; rejects `none`/typos |

**Forward-looking (NOT this phase):** GenIce3 replaces `depol` with integer `pol_loop_1`/`pol_loop_2` (`.planning/research/future-ml/genice3-upgrade/01-API-MIGRATION-MAP.md:208-217`), where strict/optimal distinctions *are* real. QuickIce's `depol_mode` string field is forward-compatible — a future GenIce3 migration maps `"strict"`→`pol_loop_1=2000`, `"optimal"`→lower values. Do not encode integer cycles now.

**Deprecated/outdated:** None. The earlier v4.7-STACK.md "strict = ice rules, optimal = relaxed" phrasing is aspirational, not reflective of 2.2.13.1 runtime behavior — treat as intent, not fact.

## Open Questions

1. **Exact GUI group placement (LOW).** Recommended: new `Depolarization` group between `Supercell` and `Lattice Information`. Alternative: a row inside the `Hydrate Lattice` group. Both work; the planner decides. A separate group is more discoverable and matches the per-section `QGroupBox` convention.
2. **Whether to add a strict-passthrough monkeypatch test (LOW).** The 1-line `depol='strict'`→`depol=config.depol_mode` change is trivially correct by inspection. A monkeypatch test on `GenIce.generate_ice` adds rigor but also coupling to GenIce2 internals. Recommended: include it only if the planner wants belt-and-suspenders; the e2e "generates without error with depol_mode='optimal'" test is sufficient for a phase this small.
3. **GUI test file path (LOW).** Confirm the exact headless panel-test path during planning (referenced as `tests/test_gui/test_hydrate_panel*.py` style; verify via glob before writing tests).

## Sources

### Primary (HIGH confidence)
- `genice2/genice.py:678-687` — `generate_ice` signature (`depol="strict"` default).
- `genice2/genice.py:936-954` — `Stage34E` branching: `if depol == "none": iter=0; else: iter=1000` (proves strict≡optimal).
- `genice2/cli/genice.py:161-165` — CLI `--depol` help: `(strict, optimal, or none) ["strict"]`.
- Empirical run (2026-07-07, `quickice` conda env, Python 3.14): sI 1×1×1 with `depol` ∈ {strict, optimal, none} → all accepted, 184 atoms each.
- `quickice/structure_generation/hydrate_generator.py:312-318` — the in-scope hardcode.
- `quickice/structure_generation/generator.py:124-127` — the out-of-scope ICE generator hardcode.
- `quickice/structure_generation/types.py:501-774` — HydrateConfig dataclass (no depol field; `__post_init__` + `from_dict`).
- `quickice/gui/hydrate_panel.py:172-195, 363-370, 452-478` — lattice combo pattern, connections, get_configuration.
- `quickice/gui/hydrate_worker.py` — worker passes config opaquely (no depol handling needed).
- `quickice/cli/pipeline.py:372-381` — CLI HydrateConfig construction (omits depol_mode → "strict" default).
- `.planning/research/v4.7-STACK.md:280-289, 331` — prior verified depol API (signature + feature matrix).

### Secondary (MEDIUM confidence)
- `.planning/research/future-ml/genice3-upgrade/01-API-MIGRATION-MAP.md:208-217` — GenIce3 `pol_loop_1`/`pol_loop_2` mapping (forward-compat context; GenIce3 not installed).

### Tertiary (LOW confidence)
- None. All findings are source- or empirically-verified.

## Metadata

**Confidence breakdown:**
- GenIce2 depol API (values + semantics): HIGH — source-inspected + empirically verified.
- Current code state (hardcode, gaps): HIGH — files read directly with line numbers.
- Backward compatibility (call sites): HIGH — grep-verified all `HydrateConfig(` sites use keyword args.
- Testing strategy: HIGH — existing test files read; patterns confirmed.
- Pitfalls: HIGH — source + empirical for strict≡optimal; source for none≠non-none.

**Research date:** 2026-07-07
**Valid until:** 2026-08-06 (stable; GenIce2 2.2.13.1 is the pinned env version — no API drift expected within 30 days)
