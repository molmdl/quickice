# CLI Documentation Cross-Check Report

**Analysis Date:** 2026-06-18
**Scope:** CLI-facing documentation (Scancode Task C, CLI Focus — Follow-up)
**Previous Scan:** `.planning/code_analysis/20260615_documentation_crosscheck_cli.md` (28 findings)
**Method:** Line-by-line comparison of documentation claims against source code in `quickice/cli/parser.py`, `quickice/cli/pipeline.py`, `quickice/validation/validators.py`, `quickice/structure_generation/types.py`

---

## Executive Summary

Of the 28 issues identified in the 2026-06-15 scan, **18 are confirmed FIXED** and **10 remain unfixed or partially fixed**. This follow-up scan identifies **8 new issues** (including 1 CRITICAL: a wrong Madrid2019 DOI in `docs/cli-reference.md` that points to a completely different paper). The most significant remaining gaps are: missing validation range documentation for concentration and occupancy flags, an incorrect DOI reference, and an incomplete Validation Rules section.

| Severity | Count (remaining from 2026-06-15) | Count (new) | Total |
|----------|-----------------------------------|-------------|-------|
| CRITICAL | 0 | 1 | 1 |
| HIGH | 0 | 2 | 2 |
| MEDIUM | 2 | 3 | 5 |
| LOW | 8 | 2 | 10 |

---

## Verification of Phase 37.1 Fixes

### Confirmed FIXED (18/28)

| Prev # | Issue | Verification |
|--------|-------|--------------|
| 1.1 | Missing v4.5 pipeline flag documentation | **FIXED** — `docs/cli-reference.md` now has sections for Hydrate (lines 536-666), Custom Molecule (669-823), Solute (826-913), Ion (916-988) |
| 1.2 | Exit codes table wrong | **FIXED** — `docs/cli-reference.md:280-284` now shows 0=Success, 1=Runtime error, 2=Argument error |
| 1.3 | `--no-overwrite` not documented | **FIXED** — `docs/cli-reference.md:147-158` documents flag with type, default, example |
| 1.5 | `--pocket-shape` default not shown | **FIXED** — `docs/cli-reference.md:435-457` documents default "sphere" |
| 1.7 | `--gromacs` no-op in pipeline mode | **FIXED** — `docs/cli-reference.md:126` has note about pipeline behavior |
| 1.8 | `--no-diagram` no-op in pipeline mode | **FIXED** — `docs/cli-reference.md:99` has note about pipeline behavior |
| 1.9 | `--gromacs` help string omits .itp | **FIXED** — `quickice/cli/parser.py:96` now says `(.gro, .top, .itp files)` |
| 1.10 | F1–F4 chain claim incomplete | **FIXED** — `docs/cli-reference.md:1146` now says "F1 and F4" |
| 2.1 | Hydrate commands missing `-T`/`-P` | **FIXED** — `scripts/cli-examples.sh:91,94,97,100,103,108` all have `-T 250 -P 0.1` |
| 2.2 | F4 chain missing `-T`/`-P` | **FIXED** — `scripts/cli-examples.sh:169` has `-T 250 -P 0.1` |
| 2.3 | Redundant `--gromacs -g` | **FIXED** — All 19 commands now use `--gromacs` only, no duplicate `-g` |
| 3.1 | Missing `--ion-source custom` | **FIXED** — `scripts/hydrate-interface-custom-ion.sh:166` includes `--ion-source custom` |
| 5.1 | CLI ref link to incomplete doc | **FIXED** — `docs/cli-reference.md` now has full v4.5 documentation |
| 5.2 | v4.5 CLI claim without documentation | **FIXED** — cli-reference.md documents all v4.5 flags |
| 5.3 | Non-existent test path | **FIXED** — `README.md:387` now uses generic `pytest tests/ -k solute -q` |
| 6.6 | Madrid2019 DOI inconsistency in README | **FIXED** — `README.md:371,375` both use `10.1063/1.5121394` |
| 6.7 | IAPWS R14-08 URL mismatch | **FIXED** — `README.md:328` now matches code: `http://www.iapws.org/release/MeltIce.pdf` |
| 6.8 | IAPWS R10-06 URL mismatch | **FIXED** — `README.md:332` now matches code: `https://www.iapws.org/release/Ice-2009.html` |

### Remaining Unfixed or Partially Fixed (10/28)

| Prev # | Issue | Current Status | New ID |
|--------|-------|----------------|--------|
| 1.4 | Box dimension range "1.0–100 nm" | **UNFIXED** — `docs/cli-reference.md:351` still says "1.0–100 nm"; code only enforces >= 1.0 nm | R-01 |
| 1.6 | `--cli + --gui` conflict not in routing table | **UNFIXED** — `docs/cli-reference.md:1069-1079` still omits this case | R-02 |
| 2.4 | `--no-diagram` in pipeline commands | **PARTIALLY FIXED** — behavior is now documented (finding 1.8), but `scripts/cli-examples.sh` lines 66,74,82,108,117,120,125,134,137,140,149,152,155,164,169 still include the no-op flag | R-03 |
| 2.5 | `--seed 42` redundant | **UNFIXED** — `scripts/cli-examples.sh:69` still specifies the default value | R-04 |
| 3.2 | `--no-diagram` in hydrate script | **PARTIALLY FIXED** — behavior documented, but `scripts/hydrate-interface-custom-ion.sh:166` still includes `--no-diagram` | R-05 |
| 4.1 | "User dialog" is GUI-only | **UNFIXED** — `docs/gro-itp-guide.md:627` still says "QuickIce allows mismatch with user dialog" without CLI caveat | R-06 |
| 6.9 | Magic constant 0.0299 without citation | **PARTIALLY FIXED** — `quickice/structure_generation/types.py:24-25` has comment "Volume per TIP4P-ICE water molecule in nm³ (at ~1 bar, 300K)" but no citation to TIP4P literature for the specific value | R-07 |
| 6.10 | Ice X range wrong | **FIXED** — `README.md:257` now says "> 30 GPa" (was "> 40 GPa") | — |
| 8.1 | No consolidated pipeline vs ice-only output section | **PARTIALLY FIXED** — individual flags have notes (lines 99, 126), but no consolidated section | R-08 |
| 7.2 | Binary name "quickice-gui" implies GUI-only | Suggestion only, no fix expected | R-09 |

---

## New Findings

### N-01: CRITICAL — Madrid2019 DOI in cli-reference.md Points to Wrong Paper

- **Finding ID:** N-01
- **Severity:** CRITICAL
- **Category:** WRONG
- **Document:** `docs/cli-reference.md:930`
- **What docs say:** `See [Madrid2019 reference](https://doi.org/10.1021/acs.jctc.9b00902).`
- **What is correct:** The Madrid2019 paper is Zeron, Abascal, & Vega, J. Chem. Phys. **151**, 134504 (2019). The DOI `10.1021/acs.jctc.9b00902` is for an ACS Journal of Chemical Theory and Computation paper — a completely different journal and paper. The correct DOI is `10.1063/1.5121394` (AIP/Journal of Chemical Physics).
- **Code reference:** `README.md:371,375` correctly uses `10.1063/1.5121394`
- **Impact:** Users following the CLI reference link will be directed to a paper about a different force field or topic entirely. This is a factual/scientific error.
- **Suggested fix:** Change `https://doi.org/10.1021/acs.jctc.9b00902` to `https://doi.org/10.1063/1.5121394` in `docs/cli-reference.md:930`

---

### N-02: HIGH — Concentration Range (0.0–5.0 mol/L) Not Documented for Any Concentration Flag

- **Finding ID:** N-02
- **Severity:** HIGH
- **Category:** MISSING
- **Document:** `docs/cli-reference.md` — sections for `--custom-concentration` (777-797), `--solute-concentration` (861-876), `--ion-concentration` (920-944)
- **What docs say:** Each flag is documented as `**Type:** Float (mol/L)` with no valid range
- **What code does:** `quickice/validation/validators.py:150-176` — `validate_concentration_range()` enforces **0.0 to 5.0 mol/L**. Values outside this range produce an `ArgumentTypeError`:
  ```python
  if not (0.0 <= val <= 5.0):
      raise ArgumentTypeError(
          f"concentration must be between 0.0 and 5.0 mol/L, got {val}"
      )
  ```
- **Impact:** Users have no way to know the valid range from the CLI reference. They may attempt values > 5.0 (e.g., concentrated brines at ~6 mol/L) and get an opaque argparse error.
- **Suggested fix:** Add `**Valid range:** 0.0 to 5.0 mol/L` to all three concentration flag sections, matching the pattern used for temperature, pressure, and nmolecules.

---

### N-03: HIGH — Validation Rules Section Incomplete — Missing 5 Validation Constraints

- **Finding ID:** N-03
- **Severity:** HIGH
- **Category:** INCONSISTENCY
- **Document:** `docs/cli-reference.md:992-1000`
- **What docs say:**
  ```
  ## Validation Rules
  All inputs are validated before processing:
  - Temperature: Must be between 0 and 500 K
  - Pressure: Must be between 0 and 10000 MPa
  - Nmolecules: Must be between 4 and 100000
  ```
- **What code does:** `quickice/validation/validators.py` validates 7 additional constraints not listed:
  - **Concentration:** 0.0 to 5.0 mol/L (`validate_concentration_range`, line 171)
  - **Cage occupancy:** 0.0 to 100.0% (`validate_occupancy_range`, line 201)
  - **Box dimensions:** >= 1.0 nm (`validate_box_dimension`, line 143)
  - **Ice/water thickness:** > 0 (positive float, `validate_positive_float`, line 121)
  - **Pocket diameter:** > 0 (positive float, `validate_positive_float`, line 121)
- **Impact:** The Validation Rules section is the natural place users look for input constraints. It's missing 5 of 8 constraints, creating a false impression that only T/P/N are validated.
- **Suggested fix:** Add the missing constraints:
  ```
  - **Concentration (mol/L):** Must be between 0.0 and 5.0 mol/L
  - **Cage occupancy:** Must be between 0.0 and 100.0%
  - **Box dimensions:** Must be >= 1.0 nm
  - **Ice/water thickness, pocket diameter:** Must be positive (> 0)
  ```

---

### N-04: MEDIUM — `--custom-gro`/`--custom-itp` Extension Validation Not Documented

- **Finding ID:** N-04
- **Severity:** MEDIUM
- **Category:** MISSING
- **Document:** `docs/cli-reference.md:673-715` (custom-gro and custom-itp sections)
- **What docs say:** "Path to a custom molecule GROMACS coordinate file (`.gro`)" and "Path to a custom molecule GROMACS topology file (`.itp`)" — implies the file type but doesn't state enforcement.
- **What code does:** `quickice/cli/pipeline.py:369-381` — the pipeline explicitly validates file extensions (SEC-02):
  ```python
  if gro_path.suffix.lower() != '.gro':
      report_progress(
          f"Error: --custom-gro file must have .gro extension, "
          f"got '{gro_path.suffix}'"
      )
      return 1
  if itp_path.suffix.lower() != '.itp':
      report_progress(
          f"Error: --custom-itp file must have .itp extension, "
          f"got '{itp_path.suffix}'"
      )
      return 1
  ```
- **Impact:** Users who name their files with different extensions (e.g., `mol.gro.bz2`, `topol.itp.bak`) will get a runtime error with no prior documentation warning.
- **Suggested fix:** Add to both flag sections: `**Constraint:** File must have .gro extension (case-insensitive). Other extensions cause a runtime error.` (and similarly for .itp)

---

### N-05: MEDIUM — Force Field Combining Rule Not Documented in GRO/ITP Guide

- **Finding ID:** N-05
- **Severity:** MEDIUM
- **Category:** MISSING
- **Document:** `docs/gro-itp-guide.md:765-767`
- **What docs say:** "Custom molecule parameters should be from compatible force field (GAFF, CHARMM, OPLS)"
- **What is actually the case:** QuickIce uses `comb-rule=2` (Lorentz-Berthelot) throughout all top files. This is compatible with GAFF2 and TIP4P-ICE, but **NOT compatible with OPLS-AA** (which uses `comb-rule=3`, geometric combining for both σ and ε). Users who create ITP files with OPLS-AA parameters (e.g., via LigParGen, referenced at `docs/gro-itp-guide.md:476`) will produce incorrect cross-interactions when mixed with TIP4P-ICE water and Madrid2019 ions.
- **Code reference:** The combining rule is set in all GROMACS top writers (e.g., `quickice/output/gromacs_writer.py:1277`). Research docs at `.planning/research/future-ml/pre-built-small-molecules/PITFALLS.md:215-232` document this explicitly.
- **Impact:** Users may unknowingly create OPLS-AA ITP files (recommended by the guide itself at line 476!) that produce scientifically incorrect LJ cross-interactions. No runtime error occurs — results are silently wrong.
- **Suggested fix:** In `docs/gro-itp-guide.md:767`, change to: "Custom molecule parameters should use a force field with Lorentz-Berthelot combining rules (GAFF2, CHARMM). OPLS-AA uses geometric combining rules and will produce incorrect cross-interactions with TIP4P-ICE water and Madrid2019 ions." Also add a warning note near the LigParGen reference (line 476).

---

### N-06: MEDIUM — No Consolidated Pipeline vs Ice-Only Output Differences Section

- **Finding ID:** N-06
- **Severity:** MEDIUM
- **Category:** MISSING
- **Document:** `docs/cli-reference.md` — entire file
- **What docs say:** Individual flag notes mention `--gromacs` (line 126) and `--no-diagram` (line 99) pipeline behavior, but there's no consolidated section describing all output differences.
- **What code does:** Pipeline mode (`quickice/cli/pipeline.py:48-111`) and ice-only mode (`quickice/main.py`) produce fundamentally different outputs:

  | Behavior | Ice-Only Mode | Pipeline Mode |
  |----------|--------------|---------------|
  | PDB files | Always (ranked candidates) | Never |
  | Phase diagram | Always (unless `--no-diagram`) | Never |
  | GROMACS .gro/.top | Only with `--gromacs` | Always |
  | GROMACS .itp | Only with `--gromacs` | Always |
  | `--gromacs` flag | Controls GROMACS export | No effect |
  | `--no-diagram` flag | Controls diagram generation | No effect |
  | Output naming | `candidate_*.pdb`, `ice_ih.gro` | `<step>.gro`, `<step>.top` |

- **Impact:** Users running pipeline commands may expect PDB output or may not realize GROMACS files are always generated. The scattered notes are easy to miss.
- **Suggested fix:** Add a new section "## Pipeline Mode vs Ice-Only Mode" between the Validation Rules and Output Files sections (after line 1000), containing the table above.

---

### N-07: LOW — gui-guide.md Has Old Madrid2019 DOI

- **Finding ID:** N-07
- **Severity:** LOW
- **Category:** INCONSISTENCY
- **Document:** `docs/gui-guide.md:793`
- **What doc says:** `DOI: https://doi.org/10.1063/1.5121392`
- **What is correct:** The Madrid2019 paper DOI is `10.1063/1.5121394` (verified in Phase 37.1, and now used consistently in `README.md:371,375`)
- **Note:** This is outside strict CLI scope but creates a cross-document inconsistency.
- **Impact:** Users comparing docs will find contradictory DOIs for the same paper.
- **Suggested fix:** Change `10.1063/1.5121392` to `10.1063/1.5121394` in `docs/gui-guide.md:793`

---

### N-08: LOW — TIP4P-ICE Reference in cli-reference.md Lacks Full Citation

- **Finding ID:** N-08
- **Severity:** LOW
- **Category:** CITATION
- **Document:** `docs/cli-reference.md:121,1183`
- **What docs say:** Line 121: "**Water model:** TIP4P-ICE (optimized for ice simulations)". Line 1183: `[TIP4P-ice Reference](https://doi.org/10.1063/1.1931662) - TIP4P-ice reference`
- **What is missing:** No full author/title/journal citation. The README provides the full citation (lines 222-227). Users who only read the CLI reference see just a DOI link with no context.
- **Impact:** Low — the DOI link is correct and functional. But for academic users, a full citation is preferred.
- **Suggested fix:** Add inline citation at line 121 or 1183: "Abascal et al. (2005), J. Chem. Phys. 122, 234511"

---

## Full Finding Summary

| # | ID | Severity | Category | Document | Line(s) | Description |
|---|-----|----------|----------|----------|---------|-------------|
| 1 | N-01 | CRITICAL | WRONG | `docs/cli-reference.md` | 930 | Madrid2019 DOI points to wrong paper (`10.1021/acs.jctc.9b00902` should be `10.1063/1.5121394`) |
| 2 | N-02 | HIGH | MISSING | `docs/cli-reference.md` | 777-797, 861-876, 920-944 | Concentration valid range (0.0–5.0 mol/L) not documented for `--custom-concentration`, `--solute-concentration`, `--ion-concentration` |
| 3 | N-03 | HIGH | INCONSISTENCY | `docs/cli-reference.md` | 992-1000 | Validation Rules section missing 5 of 8 validation constraints |
| 4 | R-01 | MEDIUM | WRONG | `docs/cli-reference.md` | 351 | Box dimension range "1.0–100 nm" — code has no upper bound (only >=1.0 nm) |
| 5 | N-04 | MEDIUM | MISSING | `docs/cli-reference.md` | 673-715 | `--custom-gro`/`--custom-itp` extension validation (.gro/.itp required) not documented |
| 6 | N-05 | MEDIUM | MISSING | `docs/gro-itp-guide.md` | 476, 767 | OPLS-AA incompatibility with Lorentz-Berthelot combining rule not warned |
| 7 | N-06 | MEDIUM | MISSING | `docs/cli-reference.md` | — | No consolidated pipeline vs ice-only output differences section |
| 8 | R-06 | MEDIUM | INCONSISTENCY | `docs/gro-itp-guide.md` | 627 | "User dialog" for residue mismatch is GUI-only, CLI users will not see it |
| 9 | R-08 | MEDIUM | MISSING | `docs/cli-reference.md` | — | Pipeline vs ice-only output differences only in scattered notes (partially fixed from prev 8.1) |
| 10 | R-02 | LOW | MISSING | `docs/cli-reference.md` | 1069-1079 | `--cli + --gui` conflict not documented in routing table |
| 11 | R-03 | LOW | INCONSISTENCY | `scripts/cli-examples.sh` | 15 lines | `--no-diagram` flag included in pipeline-mode commands (behavior documented but examples still include no-op flag) |
| 12 | R-04 | LOW | INCONSISTENCY | `scripts/cli-examples.sh` | 69 | `--seed 42` is the default value — redundant but harmless |
| 13 | R-05 | LOW | INCONSISTENCY | `scripts/hydrate-interface-custom-ion.sh` | 166 | `--no-diagram` included in pipeline command (behavior documented) |
| 14 | R-07 | LOW | MISSING | `quickice/structure_generation/types.py` | 24-25 | WATER_VOLUME_NM3 = 0.0299 has comment but no literature citation |
| 15 | R-09 | LOW | — | Binary name | — | "quickice-gui" name implies GUI-only (suggestion only) |
| 16 | N-07 | LOW | INCONSISTENCY | `docs/gui-guide.md` | 793 | Madrid2019 DOI `10.1063/1.5121392` differs from README's `10.1063/1.5121394` (outside CLI scope) |
| 17 | N-08 | LOW | CITATION | `docs/cli-reference.md` | 121, 1183 | TIP4P-ICE reference lacks full author/journal citation (only DOI link) |

---

## Detailed Verification by Document

### 1. `docs/cli-reference.md` vs `quickice/cli/parser.py`

**Overall Assessment:** Substantially improved since Phase 37.1. All 4 argument groups are now documented. Exit codes are correct. Pipeline mode notes added for `--gromacs` and `--no-diagram`. The remaining issues are:

| Flag | Parser Definition | Doc Matches? | Issue |
|------|-------------------|--------------|-------|
| `--temperature` `-T` | `type=validate_temperature`, range 0-500K, required | ✓ | — |
| `--pressure` `-P` | `type=validate_pressure`, range 0-10000, required | ✓ | — |
| `--nmolecules` `-N` | `type=validate_nmolecules`, range 4-100000, optional | ✓ | — |
| `--output` `-o` | `type=str`, default="output" | ✓ | — |
| `--no-diagram` | `action="store_true"`, default=False | ✓ | Note added about pipeline no-op |
| `--gromacs` `-g` | `action="store_true"`, default=False | ✓ | Note added about pipeline always-exports |
| `--candidate` `-c` | `type=int`, default=None | ✓ | — |
| `--no-overwrite` | `action="store_true"`, default=False | ✓ | New section added |
| `--interface` | `action="store_true"`, default=False | ✓ | — |
| `--mode` `-m` | `choices=["slab","pocket","piece"]` | ✓ | — |
| `--box-x/y/z` `-x/-y/-z` | `type=validate_box_dimension`, >=1.0 nm | ✗ | Doc says "1.0–100 nm" (R-01) |
| `--seed` | `type=int`, default=42 | ✓ | — |
| `--ice-thickness` `-t` | `type=validate_positive_float` | ✓ | — |
| `--water-thickness` `-w` | `type=validate_positive_float` | ✓ | — |
| `--pocket-diameter` `-d` | `type=validate_positive_float` | ✓ | — |
| `--pocket-shape` | `choices=["sphere","cubic"]`, default="sphere" | ✓ | — |
| `--hydrate` | `action="store_true"` | ✓ | — |
| `--lattice-type` | `choices=["sI","sII","sH"]`, default="sI" | ✓ | — |
| `--guest` | `choices=["CH4","THF"]`, default="CH4" | ✓ | — |
| `--supercell-x/y/z` | `type=int`, default=1 | ✓ | — |
| `--cage-occupancy-small` | `type=validate_occupancy_range`, 0-100%, default=100.0 | ✓ | Range documented |
| `--cage-occupancy-large` | `type=validate_occupancy_range`, 0-100%, default=100.0 | ✓ | Range documented |
| `--custom-gro` | `type=str`, default=None | ✗ | Extension validation not documented (N-04) |
| `--custom-itp` | `type=str`, default=None | ✗ | Extension validation not documented (N-04) |
| `--custom-placement` | `choices=["random","custom"]`, default="random" | ✓ | — |
| `--custom-count` | `type=int`, default=None | ✓ | — |
| `--custom-concentration` | `type=validate_concentration_range`, 0-5 mol/L | ✗ | Range not documented (N-02) |
| `--custom-positions-file` | `type=str`, default=None | ✓ | — |
| `--solute-type` | `choices=["CH4","THF"]`, default=None | ✓ | — |
| `--solute-concentration` | `type=validate_concentration_range`, 0-5 mol/L | ✗ | Range not documented (N-02) |
| `--solute-source` | `choices=["interface","custom"]`, default="interface" | ✓ | — |
| `--ion-concentration` | `type=validate_concentration_range`, 0-5 mol/L | ✗ | Range not documented (N-02) |
| `--ion-source` | `choices=["interface","custom","solute"]`, default="interface" | ✓ | — |
| `--version` `-V` | `version="%(prog)s 4.5.0"` | ✓ | — |
| `--cli` | `action="store_true"` | ✓ | — |
| `--gui` | `action="store_true"` | ✓ | — |

**Summary:** 32/37 flag definitions fully match. 5 have documentation gaps (box dimension range, extension validation, 3 concentration ranges, Madrid2019 DOI).

---

### 2. `scripts/cli-examples.sh` vs `quickice/cli/parser.py`

**Overall Assessment:** All commands now reference valid flags. All hydrate commands have `-T`/`-P`. No more redundant `--gromacs -g`. Remaining minor issues:

- Line 69: `--seed 42` is the default — redundant but harmless (R-04)
- 15 pipeline commands include `--no-diagram` — documented as no-op but still in examples (R-03)
- All flag values are within parser-validated ranges ✓
- All `--solute-source` and `--ion-source` values are valid choices ✓
- F1 and F4 chains are consistent with pipeline step order ✓

---

### 3. `scripts/hydrate-interface-custom-ion.sh` vs `quickice/cli/pipeline.py`

**Overall Assessment:** Pipeline chain is consistent with code.

| Aspect | Script | Code | Match? |
|--------|--------|------|--------|
| Step order | hydrate → interface → custom → ion → export | Source(1) → Interface(2) → Custom(3) → Ion(5) → Export(6) | ✓ |
| `--ion-source custom` | Present (line 166) | Required for Custom→Ion chain | ✓ |
| Required `-T`/`-P` | Present (line 166) | Required by argparse | ✓ |
| `--no-diagram` | Present (line 166) | No-op in pipeline mode | ✗ (R-05) |
| Default values within ranges | T=260, P=0.1, ion=0.15, count=5 | All within validator ranges | ✓ |

**Shell script flag mapping:**
- `--ion-conc` → `--ion-concentration` (mapped correctly in script)
- `--temperature` → `--temperature` (direct pass-through)
- All other flags pass through directly to `python -m quickice` ✓

---

### 4. `docs/gro-itp-guide.md` CLI References

**Overall Assessment:** Guide focuses on file preparation, not CLI syntax. CLI references are sparse but consistent.

| Issue | Description | Status |
|-------|-------------|--------|
| R-06 | "User dialog" for residue mismatch (line 627) is GUI-only | Unfixed |
| N-05 | OPLS-AA incompatibility with combining rule not warned | New |

---

### 5. `README.md` CLI Quick-Start and Version References

**Overall Assessment:** CLI quick-start references are current and consistent.

| Aspect | README | Code | Match? |
|--------|--------|------|--------|
| Entry point description | Lines 102-108 | `quickice/entry.py` | ✓ |
| Version | "v4.5" (line 14, 413) | `__version__ = "4.5.0"` | ✓ |
| CLI ref link | Line 71 → `docs/cli-reference.md` | Now has full v4.5 docs | ✓ |
| Test commands | Lines 380-387 | Generic `pytest` commands | ✓ |
| Ice X range | Line 257: "> 30 GPa" | Code: `x_boundary()` starts at 30 GPa | ✓ |
| IAPWS R14-08 URL | Line 328: `MeltIce.pdf` | Code: `MeltIce.pdf` | ✓ |
| IAPWS R10-06 URL | Line 332: `Ice-2009.html` | Code: `Ice-2009.html` | ✓ |
| Madrid2019 DOI | Lines 371, 375: `10.1063/1.5121394` | Consistent within README | ✓ |

---

### 6. `README_bin.md` — Unified Entry Point

**Overall Assessment:** Consistent with code. Binary name "quickice-gui" noted as suggestion (R-09).

| Aspect | README_bin | Code | Match? |
|--------|------------|------|--------|
| Source install command | `python -m quickice [options]` | `__main__.py` entry point | ✓ |
| Binary command | `quickice-gui [options]` | Binary distribution | ✓ |
| `--cli` flag | Documented (line 22-24) | `parser.py` definition | ✓ |
| CLI ref link | Line 27 → `docs/cli-reference.md` | Has full v4.5 docs | ✓ |

---

### 7. Citation Completeness for CLI-Related Code

| Scientific Method | Where Used in CLI | Documented in CLI-facing docs? | Correct? |
|-------------------|-------------------|-------------------------------|----------|
| **Madrid2019 ions** | `--ion-concentration` | `cli-reference.md:930` — **WRONG DOI** (`10.1021/acs.jctc.9b00902`) | ✗ (N-01) |
| **GAFF2 for solutes** | `--solute-type` | `cli-reference.md:828` mentions "GAFF2" but no citation | Partial |
| **IAPWS for phase mapping** | `--temperature`/`--pressure` lookup | Not referenced in CLI docs | OK (README has it) |
| **Lorentz-Berthelot combining rule** | All GROMACS exports | Not mentioned in `gro-itp-guide.md` | ✗ (N-05) |
| **TIP4P-ICE water model** | All exports | `cli-reference.md:121,1183` — DOI link only | Partial (N-08) |
| **WATER_VOLUME_NM3 = 0.0299** | Concentration → molecule count conversion | No citation in code or docs | ✗ (R-07) |

---

## Priority Recommendations

1. **CRITICAL (N-01):** Fix Madrid2019 DOI in `docs/cli-reference.md:930` — change `10.1021/acs.jctc.9b00902` → `10.1063/1.5121394`
2. **HIGH (N-02 + N-03):** Add concentration range (0.0–5.0 mol/L) documentation to all 3 concentration flags and expand Validation Rules section
3. **MEDIUM (N-04):** Document `--custom-gro`/`--custom-itp` extension validation
4. **MEDIUM (N-05):** Add combining rule compatibility warning to `docs/gro-itp-guide.md`
5. **MEDIUM (N-06):** Add consolidated Pipeline vs Ice-Only output section
6. **MEDIUM (R-01):** Fix box dimension range documentation
7. **MEDIUM (R-06):** Add CLI caveat to gro-itp-guide.md residue mismatch note

---

*CLI Documentation cross-check: 2026-06-18*
*Previous scan: .planning/code_analysis/20260615_documentation_crosscheck_cli.md*
