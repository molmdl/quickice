# CLI Documentation Cross-Check Report

**Analysis Date:** 2026-06-15
**Scope:** CLI-facing documentation (Scancode Task C, CLI portion)
**Focus:** Phases 36-37 changes — unified entry point, CLI pipeline, workflow scripts
**Reference:** `.planning/code_analysis/20260612_documentation_crosscheck.md`
**Method:** Line-by-line comparison of documentation claims against source code

---

## Executive Summary

28 findings identified across 6 severity levels. Critical issues include 7 broken hydrate commands in `scripts/cli-examples.sh` (missing required `-T`/`-P`), a completely missing documentation section for v4.5 pipeline flags in `docs/cli-reference.md`, and an incorrect exit codes table. Several code-vs-doc inconsistencies could cause runtime failures or mislead users about CLI capabilities.

| Severity | Count |
|----------|-------|
| Critical | 2 |
| Misleading | 5 |
| Outdated | 3 |
| Minor | 10 |
| Suggestion | 8 |

---

## 1. `docs/cli-reference.md` vs `quickice/cli/parser.py`

### 1.1 Missing v4.5 Pipeline Flag Documentation (Critical)

- **Document:** `docs/cli-reference.md` — entire file
- **What docs say:** No documentation for v4.5 argument groups (hydrate, custom molecule, solute, ion)
- **What code does:** `quickice/cli/parser.py:190-351` defines 4 argument groups with 18 flags total:
  - **Hydrate generation** (lines 190-252): `--hydrate`, `--lattice-type`, `--guest`, `--supercell-x`, `--supercell-y`, `--supercell-z`, `--cage-occupancy-small`, `--cage-occupancy-large`
  - **Custom molecule insertion** (lines 254-301): `--custom-gro`, `--custom-itp`, `--custom-placement`, `--custom-count`, `--custom-concentration`, `--custom-positions-file`
  - **Solute insertion** (lines 303-330): `--solute-type`, `--solute-concentration`, `--solute-source`
  - **Ion insertion** (lines 332-351): `--ion-concentration`, `--ion-source`
- **Severity:** Critical
- **Impact:** Users cannot discover v4.5 CLI features from the primary CLI reference document. `README.md:297` states "CLI support for v4.5 features (Tabs 3-5) is available via `python -m quickice`" and points to `docs/cli-reference.md` for CLI usage, but the referenced doc omits all v4.5 flags.
- **Suggested correction:** Add dedicated sections for each argument group with flag names, defaults, choices, help strings, and cross-flag validation rules (matching `validate_pipeline_args()` in `quickice/cli/parser.py:422-483`).

### 1.2 Exit Codes Table Is Wrong (Misleading)

- **Document:** `docs/cli-reference.md:259-266`
- **What docs say:**

  | Code | Meaning |
  |------|---------|
  | 0 | Success |
  | 1 | Invalid arguments (validation error) |
  | 2 | Phase mapping error (conditions outside known regions) |
  | 3 | Structure generation error |

- **What code does:**
  - `quickice/entry.py:105-201` — returns 0 for success/help/version, 1 for GUI errors (no PySide6, no display), delegates to `cli_main()` otherwise
  - `quickice/main.py:23-191` — returns 0 for success, 1 for `UnknownPhaseError`/`InterfaceGenerationError`/general `Exception`, re-raises `SystemExit` (argparse exit code 2)
  - `quickice/cli/pipeline.py:48-108` — returns 0 for success, 1 for all step failures
  - **Actual exit codes:** 0 = success; 1 = all runtime errors (phase mapping, structure generation, missing packages, file not found, etc.); 2 = argparse argument errors only; **no exit code 3 exists**
- **Severity:** Misleading
- **Impact:** Users interpreting exit codes for scripting/error handling will get wrong diagnostics
- **Suggested correction:**

  | Code | Meaning |
  |------|---------|
  | 0 | Success |
  | 1 | Runtime error (phase mapping, structure generation, I/O, missing packages, etc.) |
  | 2 | Argument error (invalid/missing CLI arguments, from argparse) |

### 1.3 `--no-overwrite` Flag Not Documented (Minor)

- **Document:** `docs/cli-reference.md` — entire file
- **What docs say:** No mention of `--no-overwrite`
- **What code does:** `quickice/cli/parser.py:105-110` defines `--no-overwrite` (action="store_true", default=False, help="Do not overwrite existing output files"); `quickice/cli/pipeline.py:64-75` implements the check
- **Severity:** Minor
- **Impact:** Users won't discover this flag from the CLI reference
- **Suggested correction:** Add `--no-overwrite` to the Optional Arguments section

### 1.4 Box Dimension Range Mismatch (Minor)

- **Document:** `docs/cli-reference.md:288`
- **What docs say:** "1.0–100 nm"
- **What code does:** `quickice/validation/validators.py:128-145` — `validate_box_dimension()` only enforces `>= 1.0`, no upper bound
- **Severity:** Minor
- **Impact:** Users may think 100 nm is the maximum, but there's no enforced upper limit
- **Suggested correction:** Change to ">= 1.0 nm" or "1.0 nm minimum" without specifying an upper bound

### 1.5 `--pocket-shape` Default Not Documented (Minor)

- **Document:** `docs/cli-reference.md:276-282`
- **What docs say:** Interface mode table lists modes and required parameters but doesn't show `--pocket-shape` default
- **What code does:** `quickice/cli/parser.py:182-188` — `--pocket-shape` has `choices=["sphere", "cubic"]`, `default="sphere"`
- **Severity:** Minor
- **Impact:** Users won't know the default is "sphere" unless they check `--help`
- **Suggested correction:** Add `--pocket-shape` to the Common Parameters table with default value "sphere"

### 1.6 Routing Table Missing `--cli` + `--gui` Conflict (Minor)

- **Document:** `docs/cli-reference.md:422-433`
- **What docs say:** Priority: `--gui > computation flags (→CLI) > no arguments (→help)`. No mention of `--cli + --gui` conflict.
- **What code does:** `quickice/entry.py:168` checks `known.gui` BEFORE `known.cli` (line 181), so `--gui` wins when both are set
- **Severity:** Minor
- **Impact:** Users who accidentally specify both flags won't know the resolution behavior
- **Suggested correction:** Add a row to the routing table: "`--cli + --gui` → GUI → `--gui` takes priority" or add a note about the resolution order

### 1.7 `--gromacs` Flag Behavior Differs Between Pipeline and Ice-Only Modes (Misleading)

- **Document:** `docs/cli-reference.md:101-123`
- **What docs say:** "`--gromacs`, `-g`" — "Export structure in GROMACS format (.gro, .top, .itp files)." Implies flag controls whether GROMACS export happens.
- **What code does:**
  - **Ice-only mode** (`quickice/main.py:100-152`): `if args.gromacs:` — GROMACS export only when flag is set
  - **Pipeline mode** (`quickice/cli/pipeline.py:632-743`): `_run_export_step()` ALWAYS writes GROMACS files regardless of `--gromacs`. The flag is not checked.
- **Severity:** Misleading
- **Impact:** Users running pipeline commands without `--gromacs` will still get GROMACS output, contradicting the documented behavior. Conversely, users who think they need `--gromacs` for pipeline commands are adding a no-op flag.
- **Suggested correction:** Add a note: "In pipeline mode (when `--interface`, `--hydrate`, `--custom-gro`, `--solute-type`, or `--ion-concentration` are set), GROMACS export is always performed. The `--gromacs` flag only controls export in ice-only generation mode."

### 1.8 `--no-diagram` Is a No-Op in Pipeline Mode (Minor)

- **Document:** `docs/cli-reference.md:88-97`
- **What docs say:** "Disable phase diagram generation."
- **What code does:**
  - **Ice-only mode** (`quickice/main.py:157-162`): `generate_diagram=not args.no_diagram` — flag is effective
  - **Pipeline mode** (`quickice/cli/pipeline.py:48-108`): No phase diagram code exists; diagram is never generated regardless of `--no-diagram`
- **Severity:** Minor
- **Impact:** Users adding `--no-diagram` to pipeline commands are specifying a no-op flag
- **Suggested correction:** Add note: "Only effective in ice-only generation mode. Pipeline mode never generates a phase diagram."

### 1.9 `--gromacs` Help String Incomplete (Minor)

- **Document:** `quickice/cli/parser.py:91-94`
- **What code says:** `help="Export GROMACS format (.gro, .top files)"`
- **What actually happens:** `.itp` files are also generated (via `copy_itp_files_for_structure()` in `quickice/cli/itp_helpers.py:232-405`)
- **Severity:** Minor
- **Impact:** The argparse help text understates the output
- **Suggested correction:** Change help string to `"Export GROMACS format (.gro, .top, .itp files)"`

### 1.10 F1–F4 Workflow Chains Claim Incomplete (Minor)

- **Document:** `docs/cli-reference.md:500`
- **What docs say:** "Full workflow chains (F1–F4)"
- **What exists:** `scripts/cli-examples.sh` only contains F1 (line 164) and F4 (line 169) chain examples; F2 and F3 are not present
- **Severity:** Minor
- **Impact:** Users may expect F2 and F3 examples that don't exist
- **Suggested correction:** Change to "Full workflow chains (F1, F4)" or add F2/F3 examples

---

## 2. `scripts/cli-examples.sh` vs `quickice/cli/parser.py`

### 2.1 Hydrate Commands Missing Required `-T` and `-P` Flags (Critical)

- **Document:** `scripts/cli-examples.sh:91,94,97,100,103,108`
- **What script says:** All 6 hydrate-only commands omit `-T` and `-P`:
  ```bash
  python -m quickice --hydrate --lattice-type sI --guest CH4 -o hydrate_sI_CH4
  python -m quickice --hydrate --lattice-type sII --guest THF -o hydrate_sII_THF
  python -m quickice --hydrate --lattice-type sH --guest CH4 -o hydrate_sH_CH4
  python -m quickice --hydrate --lattice-type sI --guest CH4 --supercell-x 2 --supercell-y 2 --supercell-z 2 -o hydrate_sI_222
  python -m quickice --hydrate --lattice-type sI --guest CH4 --cage-occupancy-small 80.0 --cage-occupancy-large 95.0 -o hydrate_sI_partial
  python -m quickice --hydrate --lattice-type sI --guest CH4 --gromacs -g --no-diagram -o hydrate_gmx
  ```
- **What code does:** `quickice/cli/parser.py:49-62` — `--temperature` and `--pressure` are `required=True` for ALL modes, including hydrate. argparse will reject these commands with "the following arguments are required: --temperature/-T, --pressure/-P".
- **Note:** The parser's own epilog examples (lines 38-39) CORRECTLY include T/P for hydrate commands: `python -m quickice -T 270 -P 0.1 --hydrate --lattice-type sI --guest CH4`
- **Severity:** Critical
- **Impact:** All 6 hydrate commands will fail at runtime. Users uncommenting these will get argument errors.
- **Suggested correction:** Add `-T <temp> -P <pressure>` to all hydrate commands. Use appropriate T/P values for hydrate stability (e.g., `-T 270 -P 0.1` for sI CH4).

### 2.2 F4 Chain Command Missing Required `-T` and `-P` (Critical)

- **Document:** `scripts/cli-examples.sh:169`
- **What script says:** F4 chain command starts with `python -m quickice --hydrate ...` without `-T` or `-P`
- **What code does:** Same as 2.1 — argparse requires these flags
- **Severity:** Critical
- **Impact:** F4 chain command will fail at runtime
- **Suggested correction:** Add `-T 260 -P 0.1` (or appropriate values) before `--hydrate`

### 2.3 Redundant `--gromacs -g` in 19 Commands (Minor)

- **Document:** `scripts/cli-examples.sh` — 19 commands
- **What script says:** Commands like `python -m quickice -T 250 -P 0.1 -N 256 --gromacs -g -o ice_ih_gmx`
- **What code does:** `quickice/cli/parser.py:89-95` — `-g` is the short form of `--gromacs`; specifying both is redundant (argparse just sets `gromacs=True` twice)
- **Affected lines:** 43, 46, 66, 69, 74, 77, 82, 108, 117, 120, 125, 134, 137, 140, 149, 152, 155, 164, 169
- **Severity:** Minor
- **Impact:** Confusing but functional — users may wonder if `--gromacs` and `-g` are different flags
- **Suggested correction:** Use either `--gromacs` or `-g`, not both. Prefer `--gromacs` for clarity in examples.

### 2.4 `--no-diagram` Is a No-Op in 15 Pipeline Commands (Minor)

- **Document:** `scripts/cli-examples.sh` — 15 pipeline-mode commands
- **What script says:** Pipeline commands include `--no-diagram` (e.g., line 66, 74, 82, 108, 117, 120, 125, 134, 137, 140, 149, 152, 155, 164, 169)
- **What code does:** Pipeline mode (`quickice/cli/pipeline.py`) never generates phase diagrams; the flag has no effect
- **Severity:** Minor
- **Impact:** Misleading but harmless — users may think the flag is doing something
- **Suggested correction:** Remove `--no-diagram` from pipeline-mode commands, or add a comment explaining it's only for ice-only mode

### 2.5 `--seed 42` Is Redundant (Minor)

- **Document:** `scripts/cli-examples.sh:69`
- **What script says:** `--seed 42` with interface slab command
- **What code does:** `quickice/cli/parser.py:156-159` — `--seed` has `default=42`
- **Severity:** Minor
- **Impact:** Specifying the default value explicitly is redundant
- **Suggested correction:** Either use a different seed value for the example or remove it to show the default applies

---

## 3. `scripts/hydrate-interface-custom-ion.sh` vs `quickice/cli/pipeline.py`

### 3.1 Missing `--ion-source custom` Flag (Misleading)

- **Document:** `scripts/hydrate-interface-custom-ion.sh:166`
- **What script says:** Command includes `--custom-gro ... --custom-itp ... --custom-placement random --custom-count ${CUSTOM_COUNT} --ion-concentration ${ION_CONC}` but does NOT include `--ion-source custom`
- **What code does:** `quickice/cli/parser.py:345-351` — `--ion-source` defaults to `"interface"`. When ion source is "interface", `quickice/cli/pipeline.py:529-535` uses `self._interface_result` for ion placement, ignoring custom molecules. When ion source is "custom", `pipeline.py:537-566` uses `self._custom_result` and propagates custom molecule attributes.
- **Severity:** Misleading
- **Impact:** Ions are placed in the interface structure without awareness of custom molecules, potentially causing ion-custom-molecule overlaps. The script description says "inserts custom molecules and NaCl ions" but the ions don't account for the custom molecules.
- **Suggested correction:** Add `--ion-source custom` to the constructed command on line 166

### 3.2 `--no-diagram` in Pipeline Command (Minor)

- **Document:** `scripts/hydrate-interface-custom-ion.sh:166`
- **What script says:** Includes `--no-diagram` in the pipeline command
- **What code does:** Pipeline mode never generates phase diagrams (see finding 1.8)
- **Severity:** Minor
- **Impact:** No-op flag in pipeline mode
- **Suggested correction:** Remove `--no-diagram` from the command or add a comment

### 3.3 Pipeline Step Order Is Consistent (Confirmed)

- **Document:** `scripts/hydrate-interface-custom-ion.sh:166`
- **What script constructs:** `--hydrate → --interface → --custom-gro/itp/placement/count → --ion-concentration → --gromacs → output flags`
- **What code does:** `quickice/cli/pipeline.py:48-108` — Step order: Source → Interface → Custom → Solute → Ion → Export
- **Severity:** N/A — consistent
- **Impact:** Pipeline step order matches the script's flag combination

### 3.4 Shell Script Flag Values Within Parser Constraints (Confirmed)

- **Default values:** `LATTICE_TYPE="sI"` (choice: sI, sII, sH ✓), `GUEST="CH4"` (choice: CH4, THF ✓), `ION_CONC=0.15` (float ✓), `CUSTOM_COUNT=5` (int ✓), `TEMPERATURE=260` (0-500K ✓), `PRESSURE=0.1` (0-10000 MPa ✓)
- **Severity:** N/A — consistent

---

## 4. `docs/gro-itp-guide.md` CLI References

### 4.1 "User Dialog" for GRO/ITP Residue Name Mismatch (Minor)

- **Document:** `docs/gro-itp-guide.md:627`
- **What docs say:** "Residue name 'ETHAN' in GRO, moleculetype 'ETHANOL' in ITP (QuickIce allows mismatch with user dialog)"
- **What code does:** The "user dialog" is a GUI-only feature. CLI mode (`quickice/cli/pipeline.py:335-443`) does not have any dialog or prompt for mismatched residue names — it would either silently accept or fail depending on the inserter implementation
- **Severity:** Minor
- **Impact:** CLI users reading this guide may expect a prompt that doesn't exist
- **Suggested correction:** Add clarification: "(In CLI mode, residue names must match exactly or insertion will fail; the user dialog is a GUI-only feature)"

### 4.2 Workflow Example Flags Consistent (Confirmed)

- **Document:** `docs/gro-itp-guide.md:828-842`
- **What docs say:** Examples use `--custom-gro`, `--custom-itp`, `--ion-conc`, `--temperature`, `--lattice-type`, `--guest` — all valid shell script flags
- **Severity:** N/A — consistent with `scripts/hydrate-interface-custom-ion.sh`

---

## 5. `README.md` CLI Quick-Start and Version References

### 5.1 CLI Reference Link Points to Incomplete Doc (Misleading)

- **Document:** `README.md:71`
- **What docs say:** "For CLI usage, see [docs/cli-reference.md](docs/cli-reference.md)."
- **What exists:** `docs/cli-reference.md` is missing documentation for 18 v4.5 pipeline flags (see finding 1.1)
- **Severity:** Misleading
- **Impact:** Users following the link for CLI v4.5 features won't find the relevant documentation
- **Suggested correction:** Update cli-reference.md first (see finding 1.1), or add a temporary note: "For v4.5 pipeline flags (--hydrate, --custom-gro, --solute-type, --ion-concentration), see `python -m quickice --help`"

### 5.2 "CLI support for v4.5 features is available" vs Missing Doc (Misleading)

- **Document:** `README.md:297`
- **What docs say:** "CLI support for v4.5 features (Tabs 3-5) is available via `python -m quickice`"
- **What exists:** Code supports these features (parser + pipeline), but `docs/cli-reference.md` doesn't document them
- **Severity:** Misleading
- **Impact:** The claim is true at the code level, but users can't discover how to use these features from the CLI reference
- **Suggested correction:** Update cli-reference.md with v4.5 flag documentation

### 5.3 Test Path Still Non-Existent (Outdated — from previous scan)

- **Document:** `README.md:387`
- **What docs say:** `pytest tests/gui/test_solute_inserter.py`
- **What exists:** No file at that path. Tests are at paths like `tests/test_solute_insertion.py`
- **Severity:** Outdated (carried from `.planning/code_analysis/20260612_documentation_crosscheck.md` finding 5.2)
- **Impact:** Users following the example get "file not found"
- **Suggested correction:** Change to `pytest tests/test_solute_insertion.py` or just `pytest`

### 5.4 Backward-Compatible `quickice.py` Verified (Confirmed)

- **Document:** `README.md:108`, `docs/cli-reference.md:482`
- **What docs say:** "`python quickice.py` — Backward compatible, delegates to unified router"
- **What code does:** `quickice.py` exists at project root, delegates to `quickice.entry.main()` — MATCH
- **Severity:** N/A — consistent

### 5.5 Entry Point Descriptions Match Code (Confirmed)

- **Document:** `README.md:102-108`
- **What docs say:** Entry point behaviors (no args → help, computation flags → CLI, --cli → force CLI, --gui → force GUI)
- **What code does:** `quickice/entry.py:105-201` — all described behaviors match
- **Severity:** N/A — consistent

### 5.6 Version References Current (Confirmed)

- **Document:** `README.md:14,413`
- **What docs say:** "v4.5"
- **What code does:** `quickice/__init__.py:3` — `__version__ = "4.5.0"`; `quickice/cli/parser.py:358` — `"%(prog)s 4.5.0"`
- **Severity:** N/A — consistent (previous scan finding 1.1 about README_bin.md v4.0.0 is not in CLI scope)

---

## 6. Citation Completeness

### 6.1 IAPWS-95 Citation Now Present (Fixed — from previous scan)

- **Document:** `README.md:334-336`
- **What docs say:** IAPWS-95 reference with URL `https://www.iapws.org/relguide/IAPWS-95.html`
- **Previous scan finding:** 3.1 — IAPWS-95 was missing from user-facing docs
- **Status:** FIXED since 20260612 scan
- **Severity:** N/A — resolved

### 6.2 Journaux et al. Citation Now Present (Fixed — from previous scan)

- **Document:** `README.md:338-340`
- **What docs say:** Full Journaux et al. (2019, 2020) citation
- **Previous scan finding:** 3.4 — Journaux was missing
- **Status:** FIXED
- **Severity:** N/A — resolved

### 6.3 Petrenko & Whitworth Citation Now Present (Fixed — from previous scan)

- **Document:** `README.md:342-343`
- **Previous scan finding:** 3.5
- **Status:** FIXED
- **Severity:** N/A — resolved

### 6.4 CODATA 2017 Citation Now Present (Fixed — from previous scan)

- **Document:** `README.md:345-346`
- **Previous scan finding:** 3.7
- **Status:** FIXED
- **Severity:** N/A — resolved

### 6.5 Madrid2019 / TIP4P-ICE Compatibility Note Now Present (Fixed — from previous scan)

- **Document:** `README.md:373-375`
- **Previous scan finding:** 3.9
- **Status:** FIXED — both Madrid2019 citation AND compatibility note are now present
- **Severity:** N/A — resolved

### 6.6 Madrid2019 DOI Inconsistency (Outdated)

- **Document:** `README.md:371,375`
- **What docs say:** Line 371 has DOI `10.1063/1.5121392`; line 375 has DOI `10.1063/1.5121394`
- **What is correct:** The Madrid2019 paper (Zeron et al. 2019, J. Chem. Phys. 151, 134504) has DOI `10.1063/1.5121392`. The DOI `10.1063/1.5121394` may be incorrect or refer to a different paper.
- **Severity:** Outdated
- **Impact:** The compatibility section may reference the wrong DOI
- **Suggested correction:** Verify DOI `10.1063/1.5121394` and standardize both references to `10.1063/1.5121392`

### 6.7 IAPWS R14-08 URL Mismatch Still Present (Outdated — from previous scan)

- **Document:** `README.md:328` vs `quickice/phase_mapping/data/ice_boundaries.py:14`
- **What docs say:** `https://www.iapws.org/relguide/MeltSub.html`
- **What code says:** `http://www.iapws.org/release/MeltIce.pdf`
- **Previous scan finding:** 3.2
- **Status:** NOT FIXED
- **Severity:** Outdated
- **Impact:** Neither URL may be stable; inconsistent references

### 6.8 IAPWS R10-06 URL Mismatch Still Present (Outdated — from previous scan)

- **Document:** `README.md:332` vs `quickice/phase_mapping/ice_ih_density.py:12`
- **What docs say:** `https://www.iapws.org/relguide/Ice-2006.html`
- **What code says:** `https://www.iapws.org/release/Ice-2009.html`
- **Previous scan finding:** 3.3
- **Status:** NOT FIXED
- **Severity:** Outdated

### 6.9 Magic Constant 0.0299 nm³ Without Citation (Suggestion)

- **Document:** `quickice/cli/pipeline.py:385,611`
- **What code does:** Uses `0.0299` nm³ per water molecule for liquid volume calculation without citation or explanation:
  ```python
  liquid_volume_nm3 = water_nmolecules * 0.0299
  ```
- **What should be:** This value is derived from IAPWS-95 water density (~0.997 g/cm³ at 300K → ~30.0 Å³/molecule → 0.0300 nm³). The value 0.0299 is close but uses the TIP4P water model volume rather than IAPWS-95.
- **Also appears in:** `quickice/structure_generation/solute_inserter.py:651`, `quickice/gui/custom_molecule_panel.py:1133,1156,1209`, `quickice/gui/main_window.py:626,1204`
- **Severity:** Suggestion
- **Impact:** Users cannot trace the origin of this constant; unclear if it's temperature-dependent or fixed
- **Suggested correction:** Add comment: `# 0.0299 nm³ per water molecule (TIP4P water model volume; not temperature-dependent)`

### 6.10 Ice X Range Still Wrong in README (Misleading — from previous scan)

- **Document:** `README.md:257`
- **What docs say:** Ice X pressure range "> 40 GPa" and temperature "> 273K"
- **What code does:** `quickice/phase_mapping/solid_boundaries.py:x_boundary()` — Ice X boundary varies from 30-62 GPa depending on T (30 GPa at 300K, 62 GPa at 100K); Ice X can exist at any temperature
- **Previous scan finding:** 2.7
- **Status:** NOT FIXED
- **Severity:** Misleading
- **Suggested correction:** Change to "> 30 GPa (varies with T: 30 GPa at 300K, 62 GPa at 100K)" and remove temperature constraint "> 273K"

---

## 7. Unified Entry Point Routing Cross-Check

### 7.1 Routing Table Mostly Accurate (Confirmed with Caveats)

- **Document:** `docs/cli-reference.md:422-431`
- **What docs say:** Routing table with 7 rows
- **What code does:** `quickice/entry.py:105-201` — 7 routing steps

| Doc Row | Code Step | Match |
|---------|-----------|-------|
| No arguments → Help | Step 1 (lines 143-147) | ✓ |
| `--help` → Help | Step 2 (lines 150-156) | ✓ |
| `--version` → Version | Step 3 (lines 159-165) | ✓ |
| Computation flags → CLI | Step 6 (lines 190-195) | ✓ |
| `--cli` + flags → CLI | Step 5 (lines 181-187) | ✓ |
| `--cli` alone → Error | Step 5 → cli_main → argparse error | ✓ |
| `--gui` → GUI | Step 4 (lines 168-178) | ✓ |

**Caveat:** Table doesn't show the `--cli + --gui` case (see finding 1.6). Priority note says `--gui > computation flags > no arguments` which is a simplified but essentially correct representation.

### 7.2 Platform Invocation Table (Confirmed)

- **Document:** `docs/cli-reference.md:472-477`
- **What docs say:** `quickice-gui [options]` for binary distributions
- **Note:** Binary name "quickice-gui" implies GUI-only, but the unified entry point supports CLI mode through the same binary. Not technically wrong, but potentially confusing.
- **Severity:** Suggestion
- **Suggested correction:** Consider renaming binary to just `quickice` or add a note that CLI mode is available via `quickice-gui --cli -T ...`

### 7.3 Entry Point Help Behavior Correct (Confirmed)

- **Document:** `docs/cli-reference.md:406-417`
- **What docs say:** "When run without arguments, it displays a help message (similar to `git` with no arguments)."
- **What code does:** `quickice/entry.py:143-147` — prints help and returns 0
- **Severity:** N/A — consistent

---

## 8. Pipeline Output Behavior (Undocumented)

### 8.1 Pipeline Mode vs Ice-Only Mode Output Differences (Misleading)

- **Document:** `docs/cli-reference.md:82-122` — describes output files generically
- **What code does:**

  | Behavior | Ice-Only Mode | Pipeline Mode |
  |----------|--------------|---------------|
  | PDB files | Always (via `output_ranked_candidates`) | Never |
  | Phase diagram | Always (unless `--no-diagram`) | Never |
  | GROMACS .gro/.top | Only with `--gromacs` | Always |
  | GROMACS .itp | Only with `--gromacs` | Always |
  | `--gromacs` flag | Controls GROMACS export | No effect |
  | `--no-diagram` flag | Controls diagram generation | No effect |

- **Severity:** Misleading
- **Impact:** Users may expect PDB output from pipeline commands (which never produces PDB), or may think `--gromacs` is required for GROMACS output in pipeline mode (it's not)
- **Suggested correction:** Add a section to cli-reference.md describing output behavior differences between ice-only and pipeline modes

---

## Summary Table

| # | Category | Document | Section/Line | Severity | Brief Description |
|---|----------|----------|--------------|----------|-------------------|
| 1 | Missing | `docs/cli-reference.md` | Entire file | Critical | 18 v4.5 pipeline flags undocumented |
| 2 | Wrong | `docs/cli-reference.md:259-266` | Exit Codes | Misleading | Exit codes 1/2/3 meanings are wrong; no code 3 exists |
| 3 | Missing | `docs/cli-reference.md` | Optional Args | Minor | `--no-overwrite` not documented |
| 4 | Wrong | `docs/cli-reference.md:288` | Box Dimensions | Minor | "1.0–100 nm" but code has no upper bound |
| 5 | Missing | `docs/cli-reference.md:276-282` | Interface Table | Minor | `--pocket-shape` default not shown |
| 6 | Missing | `docs/cli-reference.md:422-433` | Routing Table | Minor | `--cli + --gui` conflict not documented |
| 7 | Wrong | `docs/cli-reference.md:101-123` | `--gromacs` | Misleading | `--gromacs` is no-op in pipeline mode |
| 8 | Wrong | `docs/cli-reference.md:88-97` | `--no-diagram` | Minor | `--no-diagram` is no-op in pipeline mode |
| 9 | Wrong | `quickice/cli/parser.py:91-94` | `--gromacs` help | Minor | Help omits .itp in output |
| 10 | Wrong | `docs/cli-reference.md:500` | F1–F4 chains | Minor | Only F1 and F4 exist, not F2–F3 |
| 11 | Bug | `scripts/cli-examples.sh:91,94,97,100,103,108` | Hydrate cmds | Critical | 6 hydrate commands missing required `-T`/`-P` |
| 12 | Bug | `scripts/cli-examples.sh:169` | F4 chain | Critical | F4 chain missing required `-T`/`-P` |
| 13 | Redundant | `scripts/cli-examples.sh` (19 lines) | `--gromacs -g` | Minor | Both `--gromacs` and `-g` are same flag |
| 14 | No-op | `scripts/cli-examples.sh` (15 lines) | `--no-diagram` | Minor | Flag has no effect in pipeline mode |
| 15 | Redundant | `scripts/cli-examples.sh:69` | `--seed 42` | Minor | 42 is the default value |
| 16 | Missing | `scripts/hydrate-interface-custom-ion.sh:166` | `--ion-source` | Misleading | Should use `--ion-source custom` with custom molecules |
| 17 | No-op | `scripts/hydrate-interface-custom-ion.sh:166` | `--no-diagram` | Minor | No effect in pipeline mode |
| 18 | Wrong | `docs/gro-itp-guide.md:627` | Residue mismatch | Minor | "User dialog" is GUI-only, not CLI |
| 19 | Missing | `README.md:71` | CLI ref link | Misleading | Links to incomplete cli-reference.md |
| 20 | Incomplete | `README.md:297` | v4.5 CLI claim | Misleading | Claims available but cli-ref.md omits flags |
| 21 | Outdated | `README.md:387` | Test path | Outdated | Non-existent test path (from previous scan) |
| 22 | Wrong | `README.md:371,375` | Madrid2019 DOI | Outdated | Two different DOIs for same paper |
| 23 | Outdated | `README.md:328` vs code | IAPWS R14-08 URL | Outdated | URL mismatch (from previous scan, not fixed) |
| 24 | Outdated | `README.md:332` vs code | IAPWS R10-06 URL | Outdated | URL mismatch (from previous scan, not fixed) |
| 25 | Suggestion | `quickice/cli/pipeline.py:385,611` | 0.0299 constant | Suggestion | Magic number without citation/explanation |
| 26 | Misleading | `README.md:257` | Ice X range | Misleading | "> 40 GPa" vs code "> 30 GPa" (from previous scan, not fixed) |
| 27 | Misleading | `docs/cli-reference.md:82-122` | Output behavior | Misleading | Pipeline vs ice-only output differences undocumented |
| 28 | Suggestion | `docs/cli-reference.md:472-477` | Binary name | Suggestion | "quickice-gui" name implies GUI-only |

---

## Changes Since Previous Scan (20260612)

The following issues from `.planning/code_analysis/20260612_documentation_crosscheck.md` have been **resolved** in CLI-relevant areas:

| Previous # | Issue | Status |
|------------|-------|--------|
| 3.1 | IAPWS-95 missing from docs | **FIXED** — now in README.md:334-336 |
| 3.4 | Journaux et al. missing | **FIXED** — now in README.md:338-340 |
| 3.5 | Petrenko & Whitworth missing | **FIXED** — now in README.md:342-343 |
| 3.7 | CODATA 2017 not cited | **FIXED** — now in README.md:345-346 |
| 3.9 | Madrid2019 / TIP4P-ICE compatibility | **FIXED** — now in README.md:373-375 |
| 2.4 | `--candidate` default wrong | **FIXED** — docs now say "Default: Export all candidates" |
| 2.3 | `--nmolecules` labeled required | **FIXED** — now says "Required for ice generation; optional for `--interface` mode" |

The following issues remain **unfixed**:

| Previous # | Issue | Status |
|------------|-------|--------|
| 2.7 | Ice X range wrong | Not fixed |
| 3.2 | IAPWS R14-08 URL mismatch | Not fixed |
| 3.3 | IAPWS R10-06 URL mismatch | Not fixed |
| 5.2 | Test path non-existent | Not fixed |

---

*CLI Documentation cross-check: 2026-06-15*
