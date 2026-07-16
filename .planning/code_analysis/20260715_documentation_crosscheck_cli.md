# CLI Documentation Cross-Check Report — QuickIce

**Date:** 2026-07-15
**Scope:** CLI path only (router, parser, pipeline, structure_generation, output writers, data files, docs)
**Mode:** Read-only analysis. No code was run or modified.

---

## Doc Files Reviewed

- `README.md` (root) — main project readme, 426 lines
- `README_bin.md` — binary distribution guide, 60 lines
- `docs/cli-reference.md` — CLI flag reference, 1347 lines
- `docs/gro-itp-guide.md` — GRO/ITP preparation guide, 987 lines
- `docs/ranking.md` — ranking methodology, 269 lines
- `docs/flowchart.md` — execution flowchart, 272 lines
- `docs/principles.md` — design principles (skimmed)
- `scripts/cli-examples.sh` — CLI example commands, 189 lines
- `scripts/hydrate-interface-custom-ion.sh` — workflow script, 192 lines
- `sample_output/cli_ice/README.md`, `sample_output/cli_interface/README.md` — generation provenance
- argparse `--help` strings in `quickice/cli/parser.py`
- Inline docstrings in `quickice/entry.py`, `quickice/main.py`, `quickice/cli/pipeline.py`, `quickice/cli/itp_helpers.py`
- Module constants docstrings in `quickice/structure_generation/types.py`, `quickice/output/gromacs_writer.py`, `quickice/structure_generation/ion_inserter.py`, `quickice/structure_generation/gromacs_ion_export.py`
- `quickice/data/tip4p-ice.itp` (bundled force field file header)

**Code cross-checked against:**
- `quickice/entry.py` (router), `quickice/__main__.py`, `quickice.py` (back-compat wrapper)
- `quickice/main.py` (ice-only CLI main), `quickice/cli/parser.py`, `quickice/cli/pipeline.py`, `quickice/cli/itp_helpers.py`
- `quickice/structure_generation/types.py` (HYDRATE_LATTICES, WATER_VOLUME_NM3, WATER_ATOMS_PER_MOLECULE)
- `quickice/structure_generation/hydrate_generator.py`, `interface_builder.py`, `ion_inserter.py`, `moleculetype_registry.py`, `gromacs_ion_export.py`
- `quickice/output/gromacs_writer.py` (TIP4P_ICE_OW_SIGMA/EPSILON, writers, ITP naming), `quickice/output/validator.py` (spglib)
- `quickice/phase_mapping/lookup.py`, `melting_curves.py`, `water_density.py`, `ice_ih_density.py`

> **Note on task premise:** The task description referenced `quickice/output/lammps_writer.py` and `quickice/output/data_writer.py`. These files do **not exist** in the codebase. Only `gromacs_writer.py`, `pdb_writer.py`, `validator.py`, `phase_diagram.py`, `orchestrator.py`, `types.py`, and `guest_info.py` exist under `quickice/output/`. QuickIce does not support LAMMPS export (confirmed by grep — LAMMPS is only mentioned in `.planning/research/` as a future/non-feature). No documentation claims LAMMPS support, so this is not a doc defect, only a correction to the task's file list.

---

## Inconsistencies Found

### 1. `--no-overwrite` exit code contradicts code (MAJOR)

- **Doc:** `docs/cli-reference.md:149` — "If files exist, the pipeline exits with code 1."
- **Code:** `quickice/cli/pipeline.py:145-155`
  ```python
  if getattr(self.args, 'no_overwrite', False):
      existing_files = list(self._output_dir.glob("*"))
      if existing_files:
          logger.info("Output directory %s already contains files and --no-overwrite was specified; skipping", ...)
          report_progress("Output directory not empty; --no-overwrite set")
          return 0
  ```
- **Actual behavior:** Returns `0` (success/skip), NOT `1`. Also `main.py` (ice-only path) has no `--no-overwrite` handling at all — the flag is parsed but silently ignored in ice-only mode.
- **Severity:** MAJOR (users scripting against exit code 1 will break; `--no-overwrite` is silently a no-op in ice-only mode).
- **Suggested fix:** Either (a) change code to `return 1` to match docs, or (b) change docs to "exits with code 0 (skip)" and document that `--no-overwrite` is only honored in pipeline mode (add ice-only handling or state the limitation).

### 2. Molecule ordering in `[ molecules ]` contradicts code (MAJOR)

- **Doc:** `README.md:216-229` — example block and prose:
  ```
  SOL  CH4_H (hydrate guests)  THF_L (liquid solutes)  CUSTOM_MOL_1 (custom molecules)  NA  CL
  Order: SOL → hydrate guests → solutes → custom molecules → ions
  ```
- **Code:** `quickice/output/gromacs_writer.py` — the `[ molecules ]` section is written in order **SOL → guest → custom → solute → NA → CL**:
  - `:2769` comment "ORDER: SOL, guest, custom, solute, NA, CL" (ion top writer)
  - `:4045` comment "ORDER: SOL, guest, custom, solute" (solute top writer)
  - `:3320` comment "ORDER: SOL, guest, custom" (custom top writer)
- **Actual behavior:** Custom molecules come **before** solutes. README shows solutes before custom.
- **Severity:** MAJOR (incorrect molecule order in a `.top` causes GROMACS atom-coordinate mismatch errors since `[ molecules ]` counts must align with coordinate file order).
- **Suggested fix:** Correct `README.md:229` to "Order: SOL → hydrate guests → custom molecules → solutes → ions" and reorder the example block (`CUSTOM_MOL_1` before `THF_L`).

### 3. TIP4P ITP filename mismatch between ice-only and pipeline modes (MAJOR)

- **Doc:** `README.md:208-213` and `docs/cli-reference.md:119` both state the exported ITP is `tip4p_ice.itp` (underscore).
- **Code:**
  - **Ice-only path** `quickice/main.py:138-141`:
    ```python
    itp_source = get_tip4p_itp_path()      # returns .../data/tip4p-ice.itp (HYPHEN)
    itp_filename = "tip4p_ice.itp"          # UNDERSCORE output name
    itp_filepath = output_path / itp_filename
    shutil.copy(itp_source, itp_filepath)
    ```
    Output file: `tip4p_ice.itp` (underscore). Note `write_top_file` (`gromacs_writer.py:948-1005`) inlines the molecule definition and emits **no `#include`**, so the copied ITP is redundant in ice-only mode.
  - **Pipeline path** `quickice/cli/itp_helpers.py:311-316`:
    ```python
    tip4p_dest = output_dir / "tip4p-ice.itp"   # HYPHEN
    shutil.copy(tip4p_source, tip4p_dest)
    ```
    And the pipeline-mode `.top` writers `#include "tip4p-ice.itp"` (hyphen) — e.g. `gromacs_writer.py:1627, 2722, 3290, 4007`.
  - Bundled source file: `quickice/data/tip4p-ice.itp` (hyphen), returned by `get_tip4p_itp_path()` (`gromacs_writer.py:1008-1021`).
- **Actual behavior:** Ice-only mode writes `tip4p_ice.itp` (underscore); pipeline mode writes `tip4p-ice.itp` (hyphen). The two modes produce differently-named ITP files. The `.top` in pipeline mode `#include`s the hyphen name, so ice-only's underscore copy would not even be found by a pipeline `.top`.
- **Severity:** MAJOR (inconsistent output naming; underscore copy in ice-only is unreachable by any `#include`).
- **Suggested fix:** Standardize on `tip4p-ice.itp` (hyphen, matching the source) everywhere. Change `main.py:139` to `itp_filename = "tip4p-ice.itp"` and update README/cli-reference tables to `tip4p-ice.itp`. (The `MOLECULE_TO_GROMACS` dict at `gromacs_writer.py:277-278` already uses `tip4p-ice.itp` hyphen.)

### 4. Phase-detection count: 11 vs 12 (MINOR)

- **Doc:** `README.md` is internally contradictory:
  - `:14` "11 ice polymorphs"
  - `:118` "10 ranked candidates" (ok)
  - `:253` heading "Phase Detection (12 phases)"
  - `:255` "can identify 11 ice polymorphs"
  - Table `:258-270` lists **12** rows: Ih, Ic, II, III, V, VI, VII, VIII, IX, XI, XV, X
  - `:289` "Detection-only phases: Ice IX, XI, XV, and X" (4 detection-only) → 12 − 4 = 8 generatable ✓
- `docs/flowchart.md:141-143, 167` states "Loop: 11 phases" / "11 phases done?".
- **Code:** `quickice/output/phase_diagram.py:136-148` defines `PHASE_LABELS` for **12** phases (`ice_ih` … `ice_xv`). `quickice/phase_mapping/lookup.py` returns 12 possible `phase_id`s (Ih, Ic, II, III, V, VI, VII, VIII, IX, XI, XV, X).
- **Actual behavior:** 12 phases are detected/drawn.
- **Severity:** MINOR (internal README contradiction; flowchart wrong).
- **Suggested fix:** Standardize on "12 phases" everywhere. Change README `:14` and `:255` to "12 ice polymorphs"; change `flowchart.md` "11 phases" → "12 phases" (3 occurrences).

### 5. `--cage-occupancy-small`/`--cage-occupancy-large` marked "Required" but have defaults (MINOR)

- **Doc:** `docs/cli-reference.md:667` and `:687` both say "**Required with:** `--hydrate`".
- **Code:** `quickice/cli/parser.py:245-258` defines both with `default=100.0` (and `validate_occupancy_range`). They are optional; `HydrateConfig.__post_init__` synthesizes assignments from them when `--cage-guest` is absent (`pipeline.py:318-342`).
- **Actual behavior:** Optional with default 100.0%.
- **Severity:** MINOR.
- **Suggested fix:** Change "Required with: `--hydrate`" → "Optional (default 100.0); used only when `--cage-guest` is not supplied."

### 6. `--cage-guest` KEY list includes `guest`, which is never valid (MINOR)

- **Doc:** `docs/cli-reference.md:707` — "KEY — A `cage_type_map` key: `small`, `medium`, `large`, or `guest`". Also `parser.py:267` help string lists "guest".
- **Code:** `quickice/structure_generation/types.py:84-199` — `cage_type_map` keys across all 10 lattices are only `small`, `medium`, `large`. The filled-ice `cages` dict has a `guest` key, but `cage_type_map` for filled ices uses `small` (mapped to GenIce2 id `Ne1`). `_parse_cage_guest_args` (`pipeline.py:92-97`) rejects any key not in `cage_type_map`, so `guest=...` always raises ValueError.
- **Actual behavior:** `guest` is always rejected; valid keys are `small`/`medium`/`large`.
- **Severity:** MINOR (the filled-ice gotcha at `cli-reference.md:725` correctly explains to use `small`, but the KEY list still misleads).
- **Suggested fix:** Remove `guest` from the KEY list in `cli-reference.md:707` and `parser.py:267` help; keep only `small`, `medium`, `large`.

### 7. Ice VIII temperature threshold differs between docs (MINOR)

- **Doc:** `docs/cli-reference.md:272` "Ice VIII … low temperature (< 278K)"; `README.md:266` table "Ice VIII | Ordered VII | > 2000 MPa | < 273K".
- **Code:** `quickice/phase_mapping/lookup.py` — Ice VIII vs VII boundary `P_vii_viii` (the exact value was not fully traced in this pass, but the two docs disagree on whether the threshold is 273 K or 278 K).
- **Severity:** MINOR.
- **Suggested fix:** Reconcile to the actual `P_vii_viii` boundary value in `lookup.py` and use one number in both docs.

### 8. `tip4p-ice.itp` provenance credits disagree (MINOR)

- **Doc:** `docs/cli-reference.md:122` — "Credit: itp file adapted from http://bbs.keinsci.com/forum.php?mod=viewthread&tid=32973&page=1#pid222346"
- **Code:** `quickice/data/tip4p-ice.itp:1-2` header — "File adapted from the following link under the cc-by-nc-sa 3.0 license … http://www.sklogwiki.org/SklogWiki/index.php/GROMACS_topology_file_for_the_TIP4P/Ice_model"
- **Actual behavior:** Two different sources are credited (keinsci forum vs sklogwiki) for the same file.
- **Severity:** MINOR (provenance/licensing ambiguity).
- **Suggested fix:** Pick one authoritative source. The sklogwiki credit in the file header (with explicit cc-by-nc-sa 3.0 license note) is more complete; update `cli-reference.md:122` to match, or add both with explanation.

### 9. `scripts/cli-examples.sh` claims "every possible CLI flag combination" but omits v4.7 flags (MINOR)

- **Doc:** `docs/cli-reference.md:1299-1301` describes `scripts/cli-examples.sh` as "A comprehensive reference script showing example commands for **every possible CLI flag combination**".
- **Code:** `scripts/cli-examples.sh` hydrate section (`:88-108`) only uses `--guest`, `--cage-occupancy-small/large` (deprecated). It does **not** include `--cage-guest` (mixed occupancy) or `--depol` (v4.7 depol mode). The v4.7 examples block in `cli-reference.md:756-781` documents these but the example script does not.
- **Severity:** MINOR (script is stale for v4.7 hydrate features).
- **Suggested fix:** Either add `--cage-guest`/`--depol` examples to `cli-examples.sh`, or soften the cli-reference claim to "example commands for most CLI flag combinations (v4.5 feature set; see v4.7 Hydrate Examples above for `--cage-guest`/`--depol`)."

### 10. `--seed` shown for ice-only generation but has no effect there (MINOR)

- **Doc:** `scripts/cli-examples.sh:54` — under "Ice Generation + Options": `# python -m quickice -T 250 -P 0.1 -N 96 --seed 12345` (implies `--seed` affects ice generation).
- **Code:** `quickice/main.py:70-74` ice-only path calls `generate_candidates(phase_info=phase_info, nmolecules=args.nmolecules, n_candidates=10)` — **no `seed`/`base_seed` argument**. Only the pipeline source step (`pipeline.py:382`) passes `base_seed=self.args.seed`. `parser.py:158-162` defines `--seed` in the `interface_group`.
- **Actual behavior:** `--seed` is ignored in ice-only mode; only affects interface/hydrate/custom/solute/ion.
- **Severity:** MINOR.
- **Suggested fix:** Move the `--seed` example out of the "Ice Generation" section of `cli-examples.sh` (it already appears under Interface Generation at `:54`… actually it appears in both; remove from the ice-generation block), and note in `cli-reference.md` that `--seed` only applies to interface/pipeline modes.

### 11. README Project Structure omits `quickice/main.py` (MINOR)

- **Doc:** `README.md:404-421` Project Structure lists `quickice.py`, `quickice/__main__.py`, `quickice/entry.py`, and subdirs — but not `quickice/main.py`.
- **Code:** `quickice/main.py` is the actual ice-only + pipeline-dispatch CLI entry (imported by `entry.py:186,194` via `from quickice.main import main as cli_main`). `AGENTS.md` correctly names `quickice/cli/main.py` in its architecture note, but the actual file is `quickice/main.py` (not under `cli/`).
- **Severity:** MINOR (also note: `AGENTS.md` says "CLI path: `entry.py` → `main.py` → `CLIPipeline.execute()`" which is correct, but the task prompt's reference to `quickice/cli/main.py` is wrong — `main.py` lives at `quickice/main.py`, and `quickice/cli/` contains only `__init__.py`, `parser.py`, `pipeline.py`, `itp_helpers.py`).
- **Suggested fix:** Add `quickice/main.py # CLI main (ice-only + pipeline dispatch)` to the README Project Structure tree.

### 12. `docs/flowchart.md` only documents the ice-only path (MINOR/stale)

- **Doc:** `docs/flowchart.md` depicts only: `__main__.py` → `get_arguments()` → `lookup_phase()` → `generate_candidates()` → `rank_candidates()` → `output_ranked_candidates()`. It does not show the pipeline branch (`CLIPipeline.execute()` → source/interface/custom/solute/ion/export) that `main.py:36-46` delegates to when pipeline flags are present.
- **Code:** `quickice/main.py:37-46` dispatches to `CLIPipeline` when `--interface`/`--hydrate`/`--custom-gro`/`--solute-type`/`--ion-concentration` set.
- **Severity:** MINOR (incomplete for v4.5+ features, but not incorrect for the ice-only path it shows).
- **Suggested fix:** Add a second flowchart branch for `has_pipeline_flags → CLIPipeline.execute()` with the 6 ordered steps.

---

## Missing Documentation

### M1. Auto-chaining of `--solute-source` / `--ion-source` is undocumented in CLI reference

- **Code:** `quickice/cli/pipeline.py:617-626` (solute) and `:698-715` (ion) silently upgrade the source when upstream results exist:
  - `--solute-source interface` → auto-upgraded to `custom` if custom molecules were placed.
  - `--ion-source interface` → auto-upgraded to `solute` (if solute step ran) or `custom` (if custom step ran).
  This prevents silent data loss (custom/solute attributes dropped from output).
- **Docs:** `docs/cli-reference.md:1002-1034` (solute-source) and `:1070-1110` (ion-source) describe the explicit choices but **never mention auto-chaining**. A user setting `--ion-source interface` in a full chain would not know their source is silently upgraded.
- **Suggested fix:** Add a "Auto-chaining" note under both `--solute-source` and `--ion-source` explaining the upgrade behavior and that it exists to prevent silent data loss.

### M2. `--seed` no-op in ice-only mode is undocumented

(See inconsistency #10.) `cli-reference.md` documents `--seed` under Interface Generation Flags but does not state it is ignored for plain ice generation. Suggested fix: add "Note: `--seed` affects interface, hydrate, custom, solute, and ion placement; it does not affect ice-only candidate generation."

### M3. Ice-only vs pipeline ITP filename difference not documented

(See inconsistency #3.) No doc mentions that ice-only writes `tip4p_ice.itp` while pipeline writes `tip4p-ice.itp`. After fixing #3 this becomes moot, but until then users mixing outputs from both modes will hit `#include` resolution failures.

### M4. `--candidate` only meaningful with `--gromacs` (and only in ice-only mode) not fully stated

- **Code:** `parser.py:100-106` `--candidate` help says "Only used with --gromacs. Default: export all". In pipeline mode, `CLIPipeline` ignores `args.candidate` entirely (single structure export per step). `main.py:106-114` honors it only in ice-only GROMACS export.
- **Docs:** `cli-reference.md:130-143` documents `--candidate` but does not state it is ignored in pipeline mode.
- **Suggested fix:** Add "Note: `--candidate` is honored only in ice-only mode with `--gromacs`; pipeline mode exports a single final structure and ignores `--candidate`."

### M5. SEC-04 path-traversal restriction on `--custom-gro`/`--custom-itp`/`--custom-positions-file` undocumented

- **Code:** `pipeline.py:243-249, 494-509` rejects paths resolving outside the working directory (SEC-04), and `:278-284` rejects CSV files > 10000 rows (SEC-05, `MAX_CSV_ROWS`).
- **Docs:** `cli-reference.md` custom-molecule section (`:787-944`) does not mention these restrictions.
- **Suggested fix:** Document that custom file paths must resolve under the current working directory, and that positions CSV files are capped at 10,000 rows.

---

## Stale Documentation

### S1. `docs/flowchart.md` — does not reflect v4.5+ pipeline mode
(See inconsistency #12.) The flowchart predates interface/hydrate/custom/solute/ion pipeline steps.

### S2. `scripts/cli-examples.sh` — missing v4.7 hydrate flags
(See inconsistency #9.) The hydrate section uses only deprecated `--guest`/`--cage-occupancy-*`; no `--cage-guest` or `--depol` examples.

### S3. `sample_output/cli_ice/README.md` and `sample_output/cli_interface/README.md` use legacy `python quickice.py` invocation
- `sample_output/cli_ice/README.md:1` — `python quickice.py -T 273 -P 0.1 -N 216 -o sample_output/cli_ice -g`
- These still work (`quickice.py` delegates to `entry.main`), but use the deprecated `-g` short flag and `python quickice.py` rather than the canonical `python -m quickice`. Low severity; consider regenerating with `python -m quickice` for consistency with current docs.

---

## Citations to Add

### C1. spglib — used in `validator.py` with no inline citation
- **Location:** `quickice/output/validator.py:11` `import spglib` and `:62` `spglib.get_symmetry_dataset(...)`. The module docstring (`:1-6`) mentions "spglib" but gives no citation/DOI.
- **Docs that do cite it:** `README.md:360-363` and `docs/cli-reference.md:1203-1208` cite: "Spglib: a software library for crystal symmetry search", Sci. Technol. Adv. Mater., Meth. 4, 2384822 (2024), DOI: 10.1080/27660400.2024.2384822.
- **Suggested:** Add the same citation to `validator.py` module docstring.

### C2. GenIce2 — used in `hydrate_generator.py` with no citation
- **Location:** `quickice/structure_generation/hydrate_generator.py:78` `import genice2.genice as genice_lib` (lazy). Module docstring (`:1-5`) describes GenIce2 usage but cites nothing.
- **Docs:** `README.md:333-336` cites "GenIce: Hydrogen-disordered ice structures by combinatorial generation", J. Comput. Chem. 2017, DOI: 10.1002/jcc.25077.
- **⚠️ [NEEDS VERIFICATION]:** The 2017 J. Comput. Chem. paper (Matsumoto et al.) is for **GenIce (v1)**. The code uses **GenIce2** (v2, `genice2==2.2.13.1` per `environment.yml:43`). Whether GenIce2 has its own publication (or is covered by the 2017 paper) was not verified in this read-only pass. Check the GenIce2 repository README (https://github.com/genice-dev/GenIce2) and PyPI metadata for a separate paper before citing. If no GenIce2-specific paper exists, cite the 2017 GenIce paper and note the version.
- **Suggested:** Add a citation comment to `hydrate_generator.py` near the lazy import; verify against the GenIce2 repo first.

### C3. Madrid2019 ion parameters — code mentions author/year but no DOI
- **Locations:**
  - `quickice/structure_generation/ion_inserter.py:26` — "Ion parameters from Madrid2019_085 (Zeron et al., J. Chem. Phys. 2019)"
  - `quickice/structure_generation/gromacs_ion_export.py:40` — "; Madrid2019_085 ion model (Zeron et al., J. Chem. Phys. 2019)"
- **Docs that do cite the DOI:** `README.md:381-387` — Zeron, Abascal & Vega (2019), J. Chem. Phys. 151, 134504, DOI: 10.1063/1.5121392.
- **Suggested:** Append "DOI: 10.1063/1.5121392" to both code comments for traceability.

### C4. AVOGADRO constant — cites "CODATA 2017" but no DOI in code
- **Location:** `quickice/structure_generation/ion_inserter.py:29` `AVOGADRO = 6.02214076e23  # mol^-1 (CODATA 2017)`
- **Docs:** `README.md:357-358` cites Tiesinga et al. (2021), Rev. Mod. Phys. 93(2), 025010, DOI: 10.1103/RevModPhys.93.025010 (the CODATA 2017 redefinition, published 2021).
- **Suggested:** Add the DOI to the code comment. (The value 6.02214076e23 is the exact defined Avogadro constant since the 2019 SI redefinition.)

### C5. Water density (IAPWS-95) and Ice Ih density (IAPWS R10-06) — code has URL but docs have fuller reference
- **Code:** `quickice/phase_mapping/water_density.py:12-16` (IAPWS-95 URL) and `ice_ih_density.py:10-12` (IAPWS R10-06 URL). `melting_curves.py:1-3` references "IAPWS R14-08(2011)".
- **Docs:** `README.md:338-348` lists IAPWS R14-08, R10-06, and IAPWS-95 with document titles and URLs.
- **Status:** Code references are present but lighter than docs. No incorrect citation. Optional: mirror the full document titles into the code module docstrings. No action required for correctness.

### C6. `WATER_VOLUME_NM3` — citation present but muddled (see "Citations present but incorrect" #1 below)

---

## Citations Present but Incorrect

### I1. `WATER_VOLUME_NM3` citation in `types.py` — wrong paper title for the TIP4P/Ice DOI (MAJOR for citation accuracy)

- **Location:** `quickice/structure_generation/types.py:32-38`
  ```python
  # Reference: Abascal, J. L. F., Sanz, E., García Fernández, R., & Vega, C.
  # (2005). A potential model for the phase diagram of TIP4P water.
  # J. Chem. Phys. 122, 234511. DOI: 10.1063/1.1931662
  #
  # For TIP4P-ICE specifically: Abascal, J. L. F., & Vega, C. (2005).
  # A general purpose model for the condensed phases of water: TIP4P/2005.
  # J. Chem. Phys. 123, 234505. DOI: 10.1063/1.2121600
  WATER_VOLUME_NM3: float = 0.0299
  ```
- **Problems:**
  1. The title "A potential model for the phase diagram of TIP4P water" is **wrong** for DOI 10.1063/1.1931662 (J. Chem. Phys. 122, 234511). The correct title of that paper is **"A potential model for the study of ices and amorphous water: TIP4P/Ice"** (Abascal, Sanz, García Fernández & Vega, 2005). The README (`:236-240`) cites it correctly.
  2. The second block labels the TIP4P/**2005** paper (DOI 10.1063/1.2121600, J. Chem. Phys. 123, 234505) as "For TIP4P-ICE specifically" — this is **incorrect**: TIP4P/2005 is a *different* water model from TIP4P/Ice. TIP4P/Ice is the first paper (DOI 10.1063/1.1931662); TIP4P/2005 is the second. The comment reverses which paper is "for TIP4P-ICE."
  3. The derivation comment (`:24-30`) says density ≈ 0.997 g/cm³ for "TIP4P-ICE liquid water at ~300K/1bar." Both TIP4P/Ice and TIP4P/2005 give ~0.997–1.000 g/cm³ at ambient conditions, so the numeric value is defensible, but the citation mapping is wrong.
- **Suggested fix:** Rewrite the comment so the TIP4P/**Ice** paper (DOI 10.1063/1.1931662, *J. Chem. Phys.* 122, 234511, title "A potential model for the study of ices and amorphous water: TIP4P/Ice") is the primary reference for `WATER_VOLUME_NM3`, and drop or correctly contextualize the TIP4P/2005 reference (it is not "for TIP4P-ICE specifically").

### I2. GenIce2 citation in README is for GenIce (v1) — [NEEDS VERIFICATION]

- **Location:** `README.md:333-336` — "Paper: 'GenIce: Hydrogen-disordered ice structures by combinatorial generation', J. Comput. Chem. 2017. DOI: https://doi.org/10.1002/jcc.25077". The code (`environment.yml:43` `genice2==2.2.13.1`) uses **GenIce2**, the v2 rewrite.
- **Concern:** The 2017 J. Comput. Chem. paper (Matsumoto, Anzawa, Anzawa, Arai) describes GenIce v1. GenIce2 may or may not have a separate publication. If GenIce2 has its own paper, the README citation should be updated; if not, the README should note "GenIce2 is the v2 rewrite of GenIce; cite the original GenIce paper."
- **Suggested:** Verify at https://github.com/genice-dev/GenIce2 (README/PyPI) whether a GenIce2-specific paper exists before changing. Mark this as [NEEDS VERIFICATION] until checked.

### I3. TIP4P-ICE parameters — citation correct but split across two provenances

- **Location:** `quickice/output/gromacs_writer.py:54` — "# TIP4P-ICE LJ parameters (Abascal et al. 2005, DOI: 10.1063/1.1931662)" with `TIP4P_ICE_OW_SIGMA = 3.16680e-1` and `TIP4P_ICE_OW_EPSILON = 8.82110e-1` (`:56-57`). The bundled `quickice/data/tip4p-ice.itp:4` (commented) and `:15` confirm σ=0.31668 nm, and the test `tests/test_tip4p_ice_lj_values.py:158-177` asserts σ≈0.31668 nm and ε≈0.88211 kJ/mol against "Abascal 2005."
- **Verification:** DOI 10.1063/1.1931662 = Abascal, Sanz, García Fernández & Vega (2005), TIP4P/Ice, J. Chem. Phys. 122, 234511. The LJ parameters σ=3.1668 Å, ε/k=106.1 K (→ 0.88211 kJ/mol) match the published TIP4P/Ice values. **Citation is correct.**
- **Only issue:** the file-header provenance disagrees with the cli-reference credit (see inconsistency #8 — sklogwiki vs keinsci). The DOI citation itself is accurate.

### I4. Madrid2019 DOI — correct
- `README.md:383` DOI 10.1063/1.5121392 = Zeron, Abascal & Vega (2019), J. Chem. Phys. 151, 134504. Matches `ion_inserter.py`/`gromacs_ion_export.py` "Madrid2019_085" (±0.85e charges, confirmed at `gromacs_ion_export.py:19-20` `NA_CHARGE = 0.85`, `CL_CHARGE = -0.85`, and `:24-27` σ/ε values). **Citation correct.** Only missing the DOI in code (see C3).

### I5. CODATA 2017 / Avogadro — correct
- `README.md:357-358` Tiesinga et al. (2021) Rev. Mod. Phys. 93, 025010, DOI 10.1103/RevModPhys.93.025010. Code `ion_inserter.py:29` value 6.02214076e23 matches the defined constant. **Citation correct** (DOI absent in code — see C4).

---

## Summary

| Category | Count | Severity breakdown |
|----------|-------|--------------------|
| Inconsistencies | 12 | 3 MAJOR (#1, #2, #3), 9 MINOR |
| Missing documentation | 5 | all MINOR–MODERATE |
| Stale documentation | 3 | MINOR |
| Citations to add | 6 | C2 needs verification (GenIce2 paper) |
| Citations incorrect | 5 | I1 (wrong title + reversed papers) is the most serious; I2 needs verification |

**Top-priority fixes:**
1. **#1** `--no-overwrite` exit code (doc 1 vs code 0) — user-facing breakage.
2. **#2** Molecule ordering in `[ molecules ]` (README wrong order) — GROMACS-breaking if users follow README.
3. **#3** `tip4p_ice.itp` (underscore, ice-only) vs `tip4p-ice.itp` (hyphen, pipeline) — inconsistent output, `#include` resolution failure.
4. **I1** `types.py` `WATER_VOLUME_NM3` citation has wrong paper title and reverses TIP4P/Ice vs TIP4P/2005.

**Verify before changing:**
- **C2 / I2** — whether GenIce2 (v2) has its own publication distinct from the 2017 GenIce paper. Check https://github.com/genice-dev/GenIce2.

---

*End of report. Generated 2026-07-15. Read-only analysis — no code was executed or modified.*
