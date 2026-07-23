# v4.7 UAT Workflows

User acceptance test workflows for the **v4.7 Extended Hydrate Generation** milestone.

This file organizes all 51 UAT tests (across 13 phases) into **script-runnable** and
**interactive** workflows. Each workflow groups related tests so you can run them
batch-style with a single command, or step through them with a checklist.

**Environment:** conda env `quickice` activated. `gmx` is on PATH. `python -m quickice`
is the entry point.

---

## How To Use This File

Each workflow below has:
- **Scope:** which phase UAT items it covers
- **Script:** a copy-pasteable bash command that runs pytest / CLI checks / file inspections and prints a PASS/FAIL summary
- **Interactive checklist:** a manual checklist you step through if you want to verify by eye

Three ways to run:
1. **Run the script** — fast, automated, prints a results table. Use for the "script" workflows.
2. **Step the checklist** — for GUI/visual tests that a script cannot verify. Each item is one UAT test; mark `[ ]` → `[x]` as you confirm.
3. **Both** — run the script first for the automated subset, then walk the checklist for the remainder.

---

## Workflow A: Automated Unit & Validation Tests (Phase 38, 40)

Script-runnable. Covers metadata-driven identification, GRO residue name validation,
ITP transformation, custom guest bridge validation, sys.modules injection/cleanup.

**Scope:** Phase 38 UAT 1-4, Phase 40 UAT 2-5 (the validation/system parts).

### Script

```bash
bash .planning/uat-workflows/A-unit-validation.sh
```

What it checks (prints PASS/FAIL for each):
1. Phase 38-1: `_build_molecule_index` metadata-driven identification (THF not misidentified as water)
2. Phase 38-2: HydrateConfig guest metadata threads through pipeline
3. Phase 38-3: GRO writer rejects residue names >5 chars with ValueError
4. Phase 38-4: ITP transformation applies _H suffix + comments atomtypes + rewrites residue names
5. Phase 40-2: Custom guest residue name >3 chars rejected with specific error
6. Phase 40-3: ITP comb-rule=1 rejected, comb-rule=2 accepted, no-[defaults] accepted
7. Phase 40-4: Custom guest registered in sys.modules on main thread (thread-safe)
8. Phase 40-5: sys.modules injection cleaned up after generation

### Interactive Checklist (optional, for eye-verification)

- [ ] **38-1.** Generate a hydrate with THF; exported .top identifies THF correctly (not water)
- [ ] **38-3.** Attempt export with a >5-char residue name; clear ValueError shown (no silent truncation)
- [ ] **40-2.** Upload custom guest with residue name >3 chars; specific rejection message shown
- [ ] **40-3.** Upload custom guest .itp with comb-rule=1; rejected with "must be Lorentz-Berthelot"

---

## Workflow B: CLI Surface & Flags (Phase 43, 45)

Script-runnable. Covers depol CLI flag, CLI lattice type choices, --cage-guest flag.

**Scope:** Phase 43 UAT 1, Phase 45 UAT 7.

### Script

```bash
bash .planning/uat-workflows/B-cli-surface.sh
```

What it checks:
1. Phase 43-1: `--depol` flag present in CLI help with strict/optimal choices
2. Phase 45-7: `--depol strict` runs, `--depol optimal` runs, default is strict (no flag = strict)
3. Phase 45-7: Invalid depol value rejected
4. Phase 45-7: `--lattice-type` shows all 10 choices (CLI-01)
5. Phase 45-7: `--cage-guest` repeatable flag works (CLI-04)

### Interactive Checklist

- [ ] **43-1.** `python -m quickice --cli --help` shows `--depol {strict,optimal}` (default strict)
- [ ] **45-7.** `--depol strict` generates; `--depol optimal` generates; no flag defaults to strict
- [ ] **45-7.** `--lattice-type` lists all 10 types
- [ ] **45-7.** `--cage-guest small=CH4:60 --cage-guest large=THF:100` accepted

---

## Workflow C: E2E Generation & Grompp Validation (Phase 41, 45, 47)

Script-runnable. Covers custom guest grompp (GUI + CLI paths), new lattice grompp,
filled-ice CLI hydrate grompp, mixed occupancy, triclinic blocking, water-only survival.

**Scope:** Phase 41 UAT 4, Phase 45 UAT 1-6, 8, Phase 47 UAT 2-4.

> Note: Some grompp tests are `@gmx_skipif` — they run only when `gmx` is on PATH.
> `gmx` IS available on this machine, so they will execute.

### Script

```bash
bash .planning/uat-workflows/C-e2e-grompp.sh
```

What it checks (each prints PASS/SKIP/FAIL):
1. Phase 41-4: Custom guest GUI grompp (write_multi_molecule_* path) → rc=0
2. Phase 41-4: Custom guest CLI grompp (write_interface_* path) → rc=0
3. Phase 47-2: Filled ice generation e2e (c0te, c1te, c2te, ice1hte, sTprime structural validation)
4. Phase 47-3: Mixed cage occupancy e2e (built-in CH4+THF, sH occupancy)
5. Phase 47-4: Filled-ice CLI hydrate-only grompp (c2te@3x3x3, ice1hte@4x4x4) → rc=0
6. Phase 45-1: New lattice types CLI interface export + grompp (sII, c2te, ice1hte, sTprime, 16, 17)
7. Phase 45-3: Water-only lattices (sTprime, 17) solute/ion survival + grompp
8. Phase 45-4: Triclinic blocking at CLI interface step (c0te, c1te) → blocked with error
9. Phase 45-8: Mixed built-in (CH4+THF) + sII/16 GUI hydrate exporter grompp → rc=0
10. Phase 45-8: Filled-ice (c2te, ice1hte) single-cage-key GUI hydrate export grompp → rc=0

### Interactive Checklist (manual grompp spot-check, optional)

- [ ] **41-4.** Export custom guest hydrate via GUI; `gmx grompp` on output → rc=0
- [ ] **41-4.** Export custom guest hydrate via CLI; `gmx grompp` on output → rc=0
- [ ] **45-1.** For each new lattice (sII, sH, c2te, ice1hte, sTprime, 16, 17): generate + interface export + grompp → rc=0
- [ ] **45-2.** For sII, c2te, ice1hte, 16: full tab chain (Interface→Solute→Custom→Ion) + grompp → rc=0
- [ ] **45-4.** Triclinic (c0te, c1te) blocked at CLI interface step with clear error
- [ ] **45-5.** Triclinic hydrate-only export @ 4×4×4 + grompp → rc=0 (CLI + GUI)
- [ ] **45-6.** Custom ethanol + non-sI lattices (sII, c2te, ice1hte, 16) + grompp → rc=0
- [ ] **45-8.** Mixed CH4+THF on sII/16 via GUI hydrate exporter + grompp → rc=0

---

## Workflow D: Documentation Audit (Phase 48)

Script-runnable (greps doc files for required content) + interactive (open docs to eyeball).

**Scope:** Phase 48 UAT 1-5.

### Script

```bash
bash .planning/uat-workflows/D-documentation.sh
```

What it checks (greps for required strings, prints PASS/FAIL):
1. Phase 48-1: README.md documents custom guest hydrate workflow (upload → validate → generate → export)
2. Phase 48-2: README.md version references say v4.7 (not stale v4.5 as current version)
3. Phase 48-3: docs/gui-guide.md has 10-row lattice types table
4. Phase 48-4: docs/gui-guide.md has custom guest upload + mixed occupancy + depol subsections
5. Phase 48-5: docs/gui-guide.md version references say v4.7
6. Phase 48-6: docs/cli-reference.md documents --lattice-type (10 choices), --cage-guest, --depol
7. Phase 48-6: docs/cli-reference.md marks --guest/--cage-occupancy-small/large as DEPRECATED
8. Phase 48-7: docs/cli-reference.md version says v4.7
9. Phase 48-8: docs/gro-itp-guide.md documents custom guest ITP requirements (comb-rule=2, residue ≤3 chars, _H suffix)
10. Phase 48-13: Version string is 4.7.0 (`python -m quickice --version`)

### Interactive Checklist (open the docs to confirm content quality)

- [ ] **48-1.** README custom guest hydrate workflow section is followable by a new user
- [ ] **48-2.** README has no stale "v4.5" as current version
- [ ] **48-3.** GUI guide lattice table has all 10 rows (sI, sII, sH, C0, C1, C2, Ih, sT', 16, 17)
- [ ] **48-4.** GUI guide has custom guest upload + mixed occupancy + depol subsections
- [ ] **48-6.** CLI reference documents --cage-guest (repeatable) + --depol + DEPRECATED banners
- [ ] **48-8.** GRO/ITP guide explains comb-rule=2 mandatory + residue ≤3 chars + _H convention

---

## Workflow E: Test Suite & Refactor Integrity (Phase 47, 48.1, 48.2)

Script-runnable. Covers test collection count, full suite pass, gromacs_writer split structure,
byte-equivalence baselines, DRY helper existence, test reorganization.

**Scope:** Phase 47 UAT 1, Phase 48.1 UAT 1-5, Phase 48.2 UAT 1-2.

### Script

```bash
bash .planning/uat-workflows/E-test-refactor.sh
```

What it checks:
1. Phase 48.2-1: `pytest --collect-only` collects 1854 tests, 0 collection errors
2. Phase 48.2-2: tests/ root decluttered (0 `test_scancode_*.py` at root, 0 `phase_48_1_` prefixes)
3. Phase 48.2-2: tests/scancode/ has 18 files; tests/test_cli/ has 8 files; tests/test_output/ has 21 files
4. Phase 48.1-1: gromacs_writer.py is a thin re-export shim (<120 lines)
5. Phase 48.1-1: Per-structure writer modules exist (ice_writer, interface_writer, multi_molecule_writer, ion_writer, custom_writer, solute_writer)
6. Phase 48.1-1: No output module file >800 lines
7. Phase 48.1-2: _gro_format.py has DRY GRO helpers
8. Phase 48.1-2: _shared.py has shared constants/helpers + _write_top_defaults
9. Phase 48.1-3: baseline_shas.json exists (byte-equivalence baselines captured)
10. Phase 47-1: Custom guest validation unit tests pass
11. Phase 47-1: _build_molecule_index tests pass
12. Phase 47-1: sys.modules injection/cleanup tests pass

> **Note:** Full pytest suite run (Phase 48.1-5, 48.2-1) is SLOW (~3-5 min) and optional.
> The script runs a fast subset by default. See the script's `RUN_FULL` env var to enable the full run.

### Interactive Checklist

- [ ] **48.2-1.** `pytest --collect-only -q` shows "1854 tests collected" with 0 errors
- [ ] **48.1-1.** `quickice/output/gromacs_writer.py` is a thin re-export shim (<120 lines)
- [ ] **48.1-1.** All 6 per-structure writer modules exist in `quickice/output/`
- [ ] **48.1-2.** `_gro_format.py` contains the DRY GRO writer helpers
- [ ] **48.1-3.** `.planning/phases/48.1-*/baseline_shas.json` exists
- [ ] **47-1.** `pytest tests/test_custom_guest_bridge.py` passes (validation + sys.modules)
- [ ] **48.2-2.** No `test_scancode_*.py` files remain at `tests/` root
- [ ] **48.2-2.** No `phase_48_1_` prefixes in test file names

---

## Workflow F: GUI Interactive (Phase 39, 40, 42, 43, 44, 44.1, 46)

Interactive-only. These tests require launching the GUI and clicking through tabs.
Cannot be scripted (VTK rendering, visual styles, QComboBox interactions, custom guest upload dialog).

**Scope:** Phase 39 UAT 1, 4, Phase 40 UAT 1, Phase 42 UAT 1, 2, 4, Phase 43 UAT 1, 2, Phase 44 UAT 1-4, Phase 44.1 UAT 1-3, Phase 46 (VTK).

> **To launch GUI:** `python -m quickice --gui` (requires display; set `QT_QPA_PLATFORM=offscreen` for headless smoke, but visual tests need a real display)

### Interactive Checklist

**Hydrate Tab — Lattice & Controls (Phases 39, 43, 44)**
- [ ] **39-1.** Hydrate tab lattice dropdown lists all 10 types (sI, sII, sH, C0, C1, C2, Ih, sT', 16, 17)
- [ ] **39-4.** Selecting sT' or 17 disables guest controls (water-only); generates water-only structure
- [ ] **44-1.** Selecting any new lattice type doesn't crash; cage info display updates
- [ ] **44-3.** Multi-cage lattice (sI, sH) shows per-cage-type rows (QComboBox + QDoubleSpinBox each)
- [ ] **44-3.** Changing lattice rebuilds cage rows (sI=2, sH=3, c0te=1, sTprime=0)
- [ ] **43-1.** Depol mode dropdown present with "strict" (default) and "optimal"
- [ ] **43-2.** Generate with "optimal" depol; structure differs from "strict" (water H orientation)
- [ ] **43-3.** Fresh Hydrate tab defaults to "strict" depol (matches pre-v4.7 behavior)

**Hydrate Tab — Custom Guest Upload (Phase 40, 44)**
- [ ] **40-1.** Upload custom guest .gro+.itp (e.g. etoh.gro + etoh.itp); generates hydrate with custom guest in cages
- [ ] **44-2.** Upload valid custom guest → no error, ready to generate
- [ ] **44-2.** Upload invalid (name >3 chars) → specific validation error message
- [ ] **44-2.** Upload invalid (comb-rule=1) → specific rejection message
- [ ] **40-4.** No race condition / "module not found" errors during generation (main-thread sys.modules)
- [ ] **40-5.** After generation, custom guest module cleaned from sys.modules; second different guest works

**Hydrate Tab — Mixed Occupancy (Phase 42)**
- [ ] **42-1.** sI: assign CH4 to small + THF to large (different guests per cage type)
- [ ] **42-2.** Set 60% CH4 small + 100% THF large; generate; counts match percentages
- [ ] **42-4.** Mixed hydrate (CH4+THF) renders with distinct per-type colors in 3D viewer (gray/cyan/yellow/red/purple)
- [ ] **42-4.** Single-guest hydrate keeps legacy gray style (unchanged from pre-v4.7)

**Cross-Tab — Custom Guest Through All Tabs (Phase 44.1)**
- [ ] **44.1-1.** Upload custom guest; assign to BOTH small + large cages of sI → allowed (aggregates to one MOL_H, like ch4)
- [ ] **44.1-2.** Custom guest hydrate → Interface tab → generate → export → `gmx grompp` rc=0
- [ ] **44.1-3.** Custom guest → Interface → Solute → Custom → Ion → each export `gmx grompp` rc=0 (full GUI tab chain)

**VTK Rendering (Phase 46)**
- [ ] **46.** Custom guest renders with distinct style in 3D hydrate viewer (visually different from CH4/THF)
- [ ] **46.** Non-standard elements (C, O, H, N, S, Cl, P) render correctly (not as "unknown")

---

## Workflow G: Export File Inspection (Phase 38, 41, 42)

Hybrid — script generates the files, then you inspect output OR the script greps for required content.

**Scope:** Phase 38 UAT 1-2, Phase 41 UAT 1-3, Phase 42 UAT 3.

### Script

```bash
bash .planning/uat-workflows/G-export-inspection.sh
```

What it does:
1. Generates + exports a custom guest hydrate (CLI path) to a temp workspace
2. Greps the exported .top for: custom guest with _H suffix moleculetype name (41-1)
3. Greps the exported .itp for: commented-out [atomtypes] (41-2)
4. Greps the exported .top [atomtypes] for: merged custom atomtypes, deduped (41-2)
5. Checks the exported .gro custom guest residue name is ≤5 chars (41-3)
6. Generates + exports a mixed CH4+THF hydrate (CLI --cage-guest) to a temp workspace
7. Greps the exported .top for: multiple guest .itp #includes (ch4_hydrate.itp + thf_hydrate.itp) (42-3)
8. Greps the exported .top [molecules] for: both CH4_H and THF_H moleculetypes (42-3)

### Interactive Checklist (inspect the generated files by eye)

- [ ] **38-1.** Exported .top for a THF hydrate: THF identified correctly (not as water)
- [ ] **38-2.** Exported .top/.gro: guest moleculetype name + atom count match HydrateConfig metadata
- [ ] **41-1.** Exported .top: custom guest appears as "MOL_H" (or similar) in [molecules] with correct count
- [ ] **41-2.** Exported custom .itp: [atomtypes] section commented out
- [ ] **41-2.** Exported .top [atomtypes]: custom atomtypes merged in, shared types (hc, c3, h1) not duplicated
- [ ] **41-3.** Exported .gro: custom guest residue name ≤5 chars (e.g. "MOL_H"); consistent with .top
- [ ] **42-3.** Exported mixed hydrate .top: both ch4_hydrate.itp + thf_hydrate.itp #included
- [ ] **42-3.** Exported mixed hydrate .top [molecules]: both CH4_H + THF_H listed with counts
- [ ] **42-3.** `gmx grompp` on mixed hydrate export → rc=0

---

## Workflow H: In-App Help (Phase 48)

Interactive-only. Requires launching the GUI help dialog and checking page navigation.

**Scope:** Phase 48 UAT 5 (in-app help portion).

### Interactive Checklist

- [ ] **48-5.** Launch GUI → open Help dialog
- [ ] **48-5.** Help dialog is QStackedWidget + QListWidget TOC (not a single scrolling textbox)
- [ ] **48-5.** 4 new v4.7 content pages exist: extended lattice types, custom guest upload, mixed cage occupancy, depol mode
- [ ] **48-5.** TOC navigation works (clicking a TOC entry switches the content page)
- [ ] **48-12.** Hover tooltips on Hydrate panel per-cage controls provide guidance
- [ ] **48-13.** GUI shows version 4.7.0 (not 4.5.0)

---

## Quick Reference: All 51 Tests → Workflow Mapping

| Workflow | Script | Tests | Phase UATs Covered |
|----------|--------|-------|--------------------|
| A | ✓ | 8 | 38-1, 38-2, 38-3, 38-4, 40-2, 40-3, 40-4, 40-5 |
| B | ✓ | 5 | 43-1, 45-7 (lattice choices, cage-guest, depol x3) |
| C | ✓ | 10 | 41-4, 47-2, 47-3, 47-4, 45-1, 45-3, 45-4, 45-5/6/8 (grompp subset) |
| D | ✓ | 10 | 48-1, 48-2, 48-3, 48-4, 48-5(docs), 48-6, 48-7, 48-8, 48-13 |
| E | ✓ | 12 | 47-1, 48.1-1, 48.1-2, 48.1-3, 48.2-1, 48.2-2 |
| F | — | 18 | 39-1, 39-4, 40-1, 42-1, 42-2, 42-4, 43-1/2/3, 44-1/2/3/4, 44.1-1/2/3, 46 |
| G | ✓ | 8 | 38-1, 38-2, 41-1, 41-2, 41-3, 42-3 |
| H | — | 6 | 48-5 (in-app help), 48-12, 48-13 (GUI) |

**Script-runnable:** 53 test-checks across 6 workflows (A, B, C, D, E, G)
**Interactive-only:** 24 test-checks across 2 workflows (F, H)

---

## Running Multiple Workflows

Run all script workflows at once:

```bash
for wf in A B C D E G; do
  echo "=== Workflow $wf ==="
  bash .planning/uat-workflows/${wf}-*.sh
  echo ""
done
```

Or run them individually (each is self-contained, ~1-5 min):
- `bash .planning/uat-workflows/A-unit-validation.sh` — fastest (~1 min)
- `bash .planning/uat-workflows/B-cli-surface.sh` — fast (~1 min)
- `bash .planning/uat-workflows/C-e2e-grompp.sh` — slower (~3-5 min, grompp)
- `bash .planning/uat-workflows/D-documentation.sh` — fast (~30 sec, greps)
- `bash .planning/uat-workflows/E-test-refactor.sh` — fast subset (~1 min) / slow full (~5 min)
- `bash .planning/uat-workflows/G-export-inspection.sh` — moderate (~2 min, generates + exports)

Interactive workflows (F, H) require launching the GUI:
- `python -m quickice --gui` then step through Workflow F and H checklists

---

## After Testing

As you complete each workflow, tell me the results (pass / describe issues). I will:
1. Update the corresponding `{phase}-UAT.md` files with pass/issue status
2. Infer severity from your descriptions (never ask)
3. On completion, commit the UAT results
4. If issues are found: diagnose root causes, create fix plans, verify with checker, prepare `/gsd-execute-phase --gaps-only`

**You can report results per-workflow or all at once.** Plain text is fine:
- "Workflow A all pass" → I mark all 8 tests pass
- "A3 failed: the error message was unclear" → I log an issue (major, inferred)
- "A pass, B pass, C had 1 issue on test 5..." → batch update
