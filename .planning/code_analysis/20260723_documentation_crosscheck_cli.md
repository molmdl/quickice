# Documentation vs. Code Crosscheck — CLI Focus

**Date:** 2026-07-23
**Scope:** CLI path of the quickice codebase (dual-path CLI+GUI tool)
**Mode:** READ-ONLY, bias-free, CLI focus. No docs or code were modified. No commands were executed. Prior scancode/verification outputs in `.planning/code_analysis/` and `.planning/codebase/` were NOT read; all conclusions below were formed by directly comparing actual documentation to actual code.

**Docs checked (CLI-relevant):**
- `README.md`, `README_bin.md`, `AGENTS.md`
- `docs/cli-reference.md`, `docs/gro-itp-guide.md`
- `scripts/cli-examples.sh`, `scripts/hydrate-interface-custom-ion.sh`
- `sample_output/cli_ice/README.md`, `sample_output/cli_interface/README.md`

**Code checked (CLI path):**
- `quickice/cli/parser.py`, `quickice/cli/pipeline.py`, `quickice/cli/itp_helpers.py`
- `quickice/entry.py`, `quickice/main.py`, `quickice.py`, `quickice/__main__.py`
- `quickice/validation/validators.py`
- `quickice/structure_generation/interface_builder.py`, `quickice/structure_generation/types.py`, `quickice/structure_generation/ion_inserter.py`, `quickice/structure_generation/gromacs_ion_export.py`, `quickice/structure_generation/hydrate_generator.py`
- `quickice/output/gromacs_writer.py`, `quickice/output/validator.py`, `quickice/output/orchestrator.py`, `quickice/output/phase_diagram.py`
- `quickice/data/tip4p-ice.itp`
- `environment.yml`, `setup.sh`

---

## Summary Table

| Issue ID | Severity | Type | Doc location | Code location | One-line description |
|----------|----------|------|-------------|---------------|----------------------|
| CLI-01 | High | output-mismatch | `docs/cli-reference.md:119` | `quickice/main.py:143`, `quickice/cli/itp_helpers.py:314` | Doc says exported ITP is `tip4p_ice.itp` (underscore); code writes `tip4p-ice.itp` (hyphen). |
| CLI-02 | Med | flag-mismatch | `docs/cli-reference.md:147-158`; `scripts/cli-examples.sh:57` | `quickice/cli/pipeline.py:183-193`; `quickice/main.py:100-156` | `--no-overwrite` only works in pipeline mode; silently ignored in ice-only mode, but doc/example present it as general. |
| CLI-03 | Med | flag-mismatch | `scripts/cli-examples.sh:54` | `quickice/main.py:70-74`; `quickice/cli/pipeline.py:415-421` | `--seed` is a no-op in ice-only mode; example labels it "Reproducible generation with custom seed". |
| CLI-04 | Med | missing-citation | `docs/cli-reference.md:122` | `quickice/data/tip4p-ice.itp:1-2` | Doc credits keinsci forum for the TIP4P-ICE itp; the data file itself credits sklogwiki. |
| CLI-05 | Med | setup | `README.md:313-322` | `environment.yml:43,47,55`; `quickice/output/validator.py:11`; `quickice/output/phase_diagram.py:13` | README "Dependencies" table omits `spglib` and `matplotlib`, both used in the CLI path. |
| CLI-06 | Low | output-mismatch | `docs/cli-reference.md:84,1184` | `quickice/output/phase_diagram.py:1079-1081` | Phase-diagram output documented as `phase_diagram.png` only; code also emits `.svg` and `_data.txt`. |
| CLI-07 | Low | output-mismatch | `docs/cli-reference.md:83` | `quickice/main.py:159-162` | Doc lists PDB glob as `candidate_*.pdb`; actual base name is `ice_candidate` (→ `ice_candidate_01.pdb`). |
| CLI-08 | Low | flag-mismatch | `docs/cli-reference.md:1238` | `quickice/cli/parser.py:53-66` | `--cli` alone fails on BOTH `--temperature` and `--pressure` (both required); doc says only "Missing required --temperature". |
| CLI-09 | Low | flag-mismatch | `docs/cli-reference.md:445` | `quickice/cli/parser.py:185-191,444-447` | `--pocket-shape` has a default (`sphere`) yet doc labels it "Required with: --interface --mode pocket". |
| CLI-10 | Low | output-mismatch | `docs/cli-reference.md:1139` | `quickice/main.py:121-122` | Ice-only GRO filename shown as `{ice_type}.gro`; actual is `{phase_id}_{rank}.gro` (e.g. `ice_ih_1.gro`). |
| CLI-11 | Low | comment-contradiction | `quickice/cli/pipeline.py:1,3`; `quickice/cli/parser.py:4` | `quickice/cli/pipeline.py:136` | Stale "v4.5" in module docstrings; pipeline.py line 3 says "ice → interface" while class docstring (line 136) correctly says "source → interface". |
| CLI-12 | Low | comment-contradiction | `README.md:16,116,253,255` | `README.md:257-271` | README conflates detection vs generation counts: "11 ice polymorphs" under Ice Generation, "12 phases" header, 12-row table incl. Ice XI, but line 116 list omits Ice XI. |
| CLI-13 | Low | example-broken | `scripts/hydrate-interface-custom-ion.sh:17,105` | `quickice/cli/parser.py:207-212`; `quickice/structure_generation/interface_builder.py:121` | Script documents only `sI/sII/sH` lattice choices and exposes no v4.7 flags (`--cage-guest`, `--depol`); passing `c0te`/`c1te` would fail (blocked with `--interface`). |
| CLI-14 | Low | flag-mismatch | `docs/cli-reference.md:1284` | `README_bin.md:44-56` | CLI ref "Platform Invocation" lists a macOS binary; `README_bin.md` documents only Linux and Windows assets. |
| CLI-15 | Low | missing-citation | `docs/cli-reference.md` (Solute/Hydrate tables) | `quickice/structure_generation/gromacs_ion_export.py:9`; `hydrate_generator.py:48` | Filled-ice sources (Teeratchanan 2015, Smirnov 2013) named in cli-reference table but absent from README References; GAFF2/IAPWS/GenIce2 not cited in cli-reference where used. |

---

## Detailed Findings

### CLI-01 — Exported TIP4P ITP filename: underscore vs hyphen (High)
**Doc text** (`docs/cli-reference.md:117-119`):
> When this flag is set, QuickIce exports:
> - One `.gro` file per candidate — `ice_ih_1.gro`, ...
> - Single `.top` file — `ice_ih.top`
> - Single `.itp` file — `tip4p_ice.itp` (force field is identical for all candidates)

**Code reality:**
- `quickice/main.py:143` — `itp_filename = "tip4p-ice.itp"` (hyphen).
- `quickice/main.py:138-141` comment explicitly states: *"The bundled data file is quickice/data/tip4p-ice.itp (hyphen, not underscore)."*
- `quickice/cli/itp_helpers.py:314` — `tip4p_dest = output_dir / "tip4p-ice.itp"` (hyphen).
- The `.top` file `#include` line must match; the written include is `tip4p-ice.itp` (hyphen).

**Recommended doc change (NOT applied):** Replace `tip4p_ice.itp` with `tip4p-ice.itp` at `docs/cli-reference.md:119`. Note this is consistent with `README.md:208-213` (which already uses the hyphen form), so only `cli-reference.md` is wrong.

---

### CLI-02 — `--no-overwrite` ignored in ice-only mode (Med)
**Doc text** (`docs/cli-reference.md:147-158`):
> Do not overwrite existing output files. When this flag is set, QuickIce checks if the output directory already contains files before writing. If files exist, the pipeline skips this run and exits with code 0...

**Example** (`scripts/cli-examples.sh:57`):
> `# python -m quickice -T 250 -P 0.1 -N 96 --no-overwrite`

**Code reality:**
- `quickice/cli/pipeline.py:183-193` — `--no-overwrite` is checked only inside `CLIPipeline.execute()` (pipeline mode).
- `quickice/main.py:99-156` — The ice-only path (`has_pipeline_flags` is False) calls `output_path.mkdir(parents=True, exist_ok=True)` and writes files unconditionally; `args.no_overwrite` is never read. So in ice-only mode the flag is silently a no-op.

**Recommended doc change (NOT applied):** In `docs/cli-reference.md:147-158`, add a note mirroring the `--no-diagram`/`--gromacs` notes: *"In ice-only mode (no pipeline flags), `--no-overwrite` has no effect — files are always overwritten. The flag is only honored in pipeline mode."* Either fix the `cli-examples.sh:57` example (move it under an interface/pipeline example) or annotate it as pipeline-only.

---

### CLI-03 — `--seed` is a no-op in ice-only mode (Med)
**Example** (`scripts/cli-examples.sh:54`):
> `# Reproducible generation with custom seed`
> `# python -m quickice -T 250 -P 0.1 -N 96 --seed 12345`

**Code reality:**
- `quickice/main.py:70-74` — ice-only candidate generation calls `generate_candidates(phase_info=phase_info, nmolecules=args.nmolecules, n_candidates=10)` with NO seed argument; `args.seed` is never referenced in the ice-only path.
- `quickice/cli/pipeline.py:415-421` — `args.seed` IS used as `base_seed=self.args.seed` only in the pipeline source step (interface/hydrate mode).
- `quickice/cli/parser.py:157-162` — `--seed` lives in the `interface_group` (help-scoped to "reproducible water placement"), so it is correctly scoped in `cli-reference.md:463-487`, but the script example uses it in ice-only mode where it does nothing.

**Recommended doc change (NOT applied):** Remove or relabel `scripts/cli-examples.sh:53-54`. If ice-only reproducibility is intended, that is a code gap (not a doc fix); the doc/example should not promise reproducibility that the ice-only path does not deliver.

---

### CLI-04 — TIP4P-ICE itp source credit mismatch (Med)
**Doc text** (`docs/cli-reference.md:122`):
> Credit: itp file adapted from http://bbs.keinsci.com/forum.php?mod=viewthread&tid=32973&page=1#pid222346

**Code reality** (`quickice/data/tip4p-ice.itp:1-2`):
> ;File adapted from the following link under the cc-by-nc-sa 3.0 license https://creativecommons.org/licenses/by-nc-sa/3.0/
> ;http://www.sklogwiki.org/SklogWiki/index.php/GROMACS_topology_file_for_the_TIP4P/Ice_model

**Recommended doc change (NOT applied):** Reconcile the credit. The bundled file's own header cites sklogwiki (CC-BY-NC-SA 3.0); the doc cites a different keinsci forum URL. Either update `docs/cli-reference.md:122` to match the file header (sklogwiki + license), or, if both sources were used, list both. (See Citation Suggestions.)

---

### CLI-05 — README Dependencies table missing spglib and matplotlib (Med)
**Doc text** (`README.md:313-322`): Dependencies table lists `iapws, numpy, scipy, vtk, PySide6, genice2, genice-core, pytest` only.

**Code reality:**
- `environment.yml:55` — `spglib==2.7.0` is a pinned dependency.
- `environment.yml:47` — `matplotlib==3.10.8` is a pinned dependency.
- `quickice/output/validator.py:11` — `import spglib` (used by the CLI ice-only validation path: `output_ranked_candidates` → validator).
- `quickice/output/phase_diagram.py:13` — `import matplotlib.pyplot as plt` (used by the CLI ice-only phase-diagram path).
- `quickice/cli/pipeline.py` and `quickice/main.py` both reach these via `output_ranked_candidates`/`generate_phase_diagram`.

**Recommended doc change (NOT applied):** Add rows for `spglib` (crystal symmetry validation) and `matplotlib` (phase-diagram rendering) to `README.md:313-322`. (`spglib` is already cited in `docs/cli-reference.md:1203-1208` and `README.md` References, making its absence from the deps table inconsistent.)

---

### CLI-06 — Phase-diagram outputs under-documented (Low)
**Doc text** (`docs/cli-reference.md:84` and `:1184`): mentions only `phase_diagram.png`.

**Code reality** (`quickice/output/phase_diagram.py:1079-1081`):
```
png_path = output_dir / "phase_diagram.png"
svg_path = output_dir / "phase_diagram.svg"
txt_path = output_dir / "phase_diagram_data.txt"
```
Three files are produced (PNG, SVG, and a data TXT), all returned in `phase_diagram_files` (`quickice/output/orchestrator.py:120-125`).

**Recommended doc change (NOT applied):** In `docs/cli-reference.md:84` and the "Phase Diagram" subsection (~line 1179-1185), list `phase_diagram.png`, `phase_diagram.svg`, and `phase_diagram_data.txt`.

---

### CLI-07 — PDB filename glob vs actual base name (Low)
**Doc text** (`docs/cli-reference.md:83`): `candidate_*.pdb - Ranked ice structure candidates in PDB format`
**Code reality:** `quickice/main.py:159-162` calls `output_ranked_candidates(..., base_name="ice_candidate", ...)`, producing `ice_candidate_01.pdb`, etc. (This is correctly stated later at `docs/cli-reference.md:1173`.)

**Recommended doc change (NOT applied):** Make `docs/cli-reference.md:83` consistent with `:1173` — use `ice_candidate_*.pdb`.

---

### CLI-08 — `--cli` alone: which required args are missing (Low)
**Doc text** (`docs/cli-reference.md:1238`): `| --cli alone | CLI (error) | Missing required --temperature |`
**Code reality:** `quickice/cli/parser.py:53-66` — both `--temperature`/`-T` and `--pressure`/`-P` are `required=True`. With `--cli` alone, argparse reports BOTH required arguments missing (exit code 2).

**Recommended doc change (NOT applied):** Change the cell to "Missing required `--temperature` and `--pressure`" at `docs/cli-reference.md:1238`.

---

### CLI-09 — `--pocket-shape` labeled "Required" despite having a default (Low)
**Doc text** (`docs/cli-reference.md:443-445`): `Default: sphere` then `Required with: --interface --mode pocket`.
**Code reality:** `quickice/cli/parser.py:185-191` — `default="sphere"`; `validate_interface_args` (`parser.py:444-447`) never requires `pocket_shape` (only `pocket_diameter`).

**Recommended doc change (NOT applied):** At `docs/cli-reference.md:445`, change "Required with" to "Only relevant with" (or drop the line), since the default `sphere` makes it optional.

---

### CLI-10 — Ice-only GRO filename in summary table (Low)
**Doc text** (`docs/cli-reference.md:1139`): Ice-Only GRO file shown as `{ice_type}.gro`.
**Code reality:** `quickice/main.py:121-122` — `base_name = f"{candidate.phase_id}_{rc.rank}"` → e.g. `ice_ih_1.gro` (rank suffix present). The detailed `--gromacs` section (`cli-reference.md:117-118`) correctly shows `ice_ih_1.gro`.

**Recommended doc change (NOT applied):** At `docs/cli-reference.md:1139`, use `{ice_type}_{rank}.gro` to match `:117-118`.

---

### CLI-11 — Stale "v4.5" / "ice" wording in CLI module docstrings (Low)
**Code text:**
- `quickice/cli/pipeline.py:1` — `"""CLI pipeline for QuickIce v4.5."""`
- `quickice/cli/pipeline.py:3-4` — `"""Orchestrates the ice → interface → custom → solute → ion → export workflow..."""`
- `quickice/cli/parser.py:4-5` — `"""...v4.5 pipeline flags (hydrate, custom molecule, solute, ion insertion)."""`

**Code reality (contradicting itself):**
- `quickice/cli/pipeline.py:136` — class docstring correctly says `"source → interface → custom → solute → ion → export"` and `AGENTS.md:29` says `"source → interface → custom → solute → ion → export"`. The module docstring's "ice → interface" omits the hydrate source added in v4.7.
- Version is now 4.7.0 (`quickice/cli/parser.py:386`); v4.7 added `--cage-guest`, `--depol`, filled-ice lattices — so "v4.5 pipeline flags" is stale.

**Recommended doc change (NOT applied):** Update `pipeline.py:1` to "v4.7", `pipeline.py:3` "ice →" to "source →", and `parser.py:4` "v4.5" to "v4.7" (and mention cage-guest/depol). These are code comments, but they contradict both the class docstring and `AGENTS.md`.

---

### CLI-12 — README ice-polymorph count: detection vs generation (Low)
**Doc text:**
- `README.md:16` — "Ice Generation — 11 ice polymorphs from thermodynamic conditions"
- `README.md:116` — "11 ice polymorphs — Ih, Ic, II, III, V, VI, VII, VIII, IX, XV, X" (omits Ice XI)
- `README.md:253` — header "Phase Detection (12 phases)"
- `README.md:255` — "can identify 11 ice polymorphs"
- `README.md:257-271` — table has 12 rows (includes Ice XI)

**Code reality / cross-doc:** `docs/cli-reference.md:178` correctly states "8 ice polymorphs (those with GenIce2 lattice implementations)" for generation; `README.md:274-289` separately lists 8 generatable + detection-only phases. The mismatch is internal to `README.md`: it conflates the 12 detection phases, the 11 count, and the 8 generatable phases, and the line-116 list omits Ice XI which the detection table includes.

**Recommended doc change (NOT applied):** In `README.md`, separate "detection (12, incl. Ice XI)" from "generation (8)". Fix line 116 to either include Ice XI or clarify it is the generation list (which is 8, not 11). Align line 255 with the 12-row table.

---

### CLI-13 — `hydrate-interface-custom-ion.sh` lacks v4.7 surface and triclinic caveat (Low)
**Doc text** (`scripts/hydrate-interface-custom-ion.sh:17,105`): `--lattice-type TYPE  Hydrate lattice: sI, sII, sH (default: sI)` — only 3 choices documented; no `--cage-guest`/`--depol` exposed.
**Code reality:**
- `quickice/cli/parser.py:207-212` — `--lattice-type` accepts 10 choices (`sI, sII, sH, c0te, c1te, c2te, ice1hte, sTprime, 16, 17`).
- `quickice/structure_generation/interface_builder.py:121` — `TRICLINIC_HYDRATE_PHASES = {"hydrate_c0te", "hydrate_c1te"}` — c0te/c1te are blocked with `--interface`.
- The script hardcodes `--interface --mode slab` (`hydrate-interface-custom-ion.sh:166`), so passing `--lattice-type c0te` would error. The script's documented 3-choice set is implicitly safe but unlabeled as such, and the v4.7 mixed-occupancy/depol features are inaccessible from this script.

**Recommended doc change (NOT applied):** In `scripts/hydrate-interface-custom-ion.sh:17,105`, note that only orthogonal (interface-compatible) lattices are supported by this script (sI/sII/sH), and that v4.7 features (`--cage-guest`, `--depol`) require calling `python -m quickice` directly. (No code change needed.)

---

### CLI-14 — Platform Invocation lists a macOS binary (Low)
**Doc text** (`docs/cli-reference.md:1284`): `| Binary (Linux/macOS) | quickice-gui [options] |`
**Code reality:** `README_bin.md:44-56` documents only `quickice-v4.7.0-linux-x86_64.tar.gz` and `quickice-v4.7.0-windows-x86_64.zip` (no macOS asset). `README_bin.md:9-11` Platform Invocation table also lists "Binary (Linux/macOS)".

**Recommended doc change (NOT applied):** Either confirm a macOS binary exists (and add it to `README_bin.md`) or change "Linux/macOS" to "Linux" in both `docs/cli-reference.md:1284` and `README_bin.md:10`. (Could not fully verify without inspecting `scripts/build-linux.sh`/release assets, so flagged Low.)

---

### CLI-15 — Missing/under-cited references in cli-reference.md (Low, see Citation Suggestions)
**Doc text:** `docs/cli-reference.md` uses GAFF2 for solutes (`:964-965`), IAPWS-backed density/phase data (implicitly, via the phase diagram), GenIce2 for all structure generation, and names "Teeratchanan 2015"/"Smirnov 2013" in the hydrate lattice table (`:574-578`) without full citations.
**Code reality:** `quickice/structure_generation/gromacs_ion_export.py:9` (Madrid2019), `quickice/phase_mapping/water_density.py:31` (`from iapws import IAPWS95`), `quickice/structure_generation/hydrate_generator.py:48` (Teeratchanan 2015), `quickice/output/validator.py:11` (spglib). README References (`README.md:324-388`) carry GenIce2, IAPWS, spglib, GAFF2, Madrid2019 — but cli-reference.md only cites spglib (`:1203-1208`) and Madrid2019 (`:1052`) and TIP4P-ice (`:1346`).

**Recommended doc change (NOT applied):** See Citation Suggestions below.

---

## Citation Suggestions (suggest only; do NOT add)

| # | Where to add | Citation to add | Why |
|---|--------------|-----------------|-----|
| C-1 | `docs/cli-reference.md:122` (TIP4P-ICE itp credit) | Reconcile with `quickice/data/tip4p-ice.itp:1-2`: sklogwiki URL `http://www.sklogwiki.org/SklogWiki/index.php/GROMACS_topology_file_for_the_TIP4P/Ice_model` under CC-BY-NC-SA 3.0 (https://creativecommons.org/licenses/by-nc-sa/3.0/). Keep Abascal et al. 2005, DOI 10.1063/1.1931662 (already at `:1346` and `README.md:236-240`) for the model itself. | The doc's keinsci credit does not match the file's own stated source. |
| C-2 | `docs/cli-reference.md` Hydrate lattice table (`:574-578`) | Add full citations for filled-ice sources: Teeratchanan 2015 (c0te/c1te/c2te/ice1hte) and Smirnov 2013 (sTprime), and add them to `README.md` References. Currently only surnames+years appear in the table; no DOIs/bibliographic entries exist in README References. | Code references them (`hydrate_generator.py:48`); doc names them without a citable reference. |
| C-3 | `docs/cli-reference.md` Solute section (`:948-965`) | Add GAFF2 citation: Wang et al. 2004, J. Comput. Chem. 25(9), 1157–1174, DOI 10.1002/jcc.20035; He et al. 2020, JCIM 60(5), 247–257, DOI 10.1021/acs.jcim.9b01131 (already in `README.md:374-376`). | Solute force field is GAFF2; cli-reference mentions GAFF2 (`:964`) without citation. |
| C-4 | `docs/cli-reference.md` near phase-diagram / density discussion | Add IAPWS citations (IAPWS-95, R14-08, R10-06) already in `README.md:338-348`. Code uses `iapws.IAPWS95` (`quickice/phase_mapping/water_density.py:31`) and `_Ice` (`quickice/phase_mapping/ice_ih_density.py:27`) for the phase diagram/density shown in the CLI ice-only path. | CLI phase lookup relies on IAPWS; cli-reference does not cite it. |
| C-5 | `docs/cli-reference.md` Ice Phase Examples / structure generation intro | Add GenIce2 citation: "GenIce: Hydrogen-disordered ice structures by combinatorial generation", J. Comput. Chem. 2017, DOI 10.1002/jcc.25077 (already in `README.md:333-336`). | All 8 generatable ice polymorphs and all hydrate lattices come from GenIce2 (`genice2==2.2.13.1` per `environment.yml:43`); cli-reference mentions GenIce2 in passing but does not cite it. |
| C-6 | `docs/cli-reference.md:1052` (Madrid2019) | Already present and correct (Zeron et al. 2019, DOI 10.1063/1.5121392). Consider adding the TIP4P/2005-vs-TIP4P-ICE compatibility caveat already in `README.md:385-387`. | Code hardcodes Madrid2019 params (`gromacs_ion_export.py:25-33`); the caveat about water-model mismatch is documented in README but not cli-reference. |
| C-7 | `docs/cli-reference.md:1203-1208` (spglib) | Already present and correct (DOI 10.1080/27660400.2024.2384822). No action needed; verify it stays in sync with `quickice/output/validator.py:11`. | Verification only. |
| C-8 | `docs/cli-reference.md` (Avogadro constant) | Optional: CODATA 2017 — Tiesinga et al. 2021, Rev. Mod. Phys. 93(2), 025010, DOI 10.1103/RevModPhys.93.025010 (already in `README.md:357-358`). | `quickice/structure_generation/ion_inserter.py:31` defines `AVOGADRO = 6.02214076e23  # mol^-1 (CODATA 2017)`, used for concentration→count in the CLI solute/ion steps. |

---

## Docs That Are Accurate (verified against code)

The following CLI doc claims were checked and ARE consistent with the code:

**Flags & argparse (`docs/cli-reference.md` vs `quickice/cli/parser.py`):**
- All flag names, short options, defaults, and `choices` match: `-T/--temperature` (required), `-P/--pressure` (required), `-N/--nmolecules` (default None, effective 256 in interface mode), `-o/--output` (default `output`), `--no-diagram`, `-g/--gromacs`, `-c/--candidate` (1-10), `--no-overwrite`, `-V/--version`, `--cli`, `--gui`.
- Interface group: `--interface`, `-m/--mode` (choices slab/pocket/piece), `--box-x/-x`, `--box-y/-y`, `--box-z/-z` (≥1.0 nm), `--seed` (default 42), `-t/--ice-thickness`, `-w/--water-thickness`, `-d/--pocket-diameter`, `--pocket-shape` (choices sphere/cubic, default sphere).
- Hydrate group: `--hydrate`, `--lattice-type` (exactly 10 choices: sI, sII, sH, c0te, c1te, c2te, ice1hte, sTprime, 16, 17; default sI), `--guest` (CH4/THF, default CH4; deprecated), `--supercell-x/y/z` (default 1), `--cage-occupancy-small/large` (default 100.0; deprecated), `--cage-guest` (append, KEY=GUEST:OCC), `--depol` (strict/optimal, default strict).
- Custom group: `--custom-gro`, `--custom-itp`, `--custom-placement` (random/custom, default random), `--custom-count`, `--custom-concentration`, `--custom-positions-file`.
- Solute group: `--solute-type` (CH4/THF), `--solute-concentration`, `--solute-source` (choices interface/custom, default interface).
- Ion group: `--ion-concentration`, `--ion-source` (choices interface/custom/solute, default interface).
- Version string `4.7.0` (`parser.py:386`) matches `docs/cli-reference.md:169` and `README.md:425` and `README_bin.md:44`.

**Cross-flag validation (`docs/cli-reference.md` "Validation Rules" vs `quickice/cli/parser.py:validate_pipeline_args` and `validators.py`):**
- Temperature 0-500 K, pressure 0-10000 MPa, nmolecules 4-100000, box ≥1.0 nm (no upper bound), concentration 0.0-5.0 mol/L, occupancy 0.0-100.0%, `.gro`/`.itp` extension checks (case-insensitive) — all match.
- `--hydrate` mutually exclusive with `--nmolecules`; `--custom-gro`/`--custom-itp` required together and require `--interface`; `--custom-placement custom` requires `--custom-positions-file`; random requires count XOR concentration; `--solute-type` requires `--solute-concentration` and `--interface`; `--solute-source custom` requires `--custom-gro`; `--ion-concentration` requires `--interface`; `--ion-source custom` requires `--custom-gro`; `--ion-source solute` requires `--solute-type` — all enforced in `parser.py:462-511`.

**Pipeline step order (`AGENTS.md:29`, `docs/cli-reference.md:1309`, `scripts/cli-examples.sh:161-169` vs `quickice/cli/pipeline.py:195-226`):**
- source → interface → custom → solute → ion → export matches `CLIPipeline.execute()`. F1 (interface→custom→solute→ion) and F4 (hydrate→interface→custom→solute→ion) example chains match.

**Slab constraint (`docs/cli-reference.md:357,405` vs `quickice/structure_generation/interface_builder.py:141-161`):**
- `box_z = 2 × ice_thickness + water_thickness` IS enforced (0.01 nm tolerance).

**Hydrate specifics (`docs/cli-reference.md:565-583,725,752` vs code):**
- 10 lattice choices match `parser.py:209` and `types.py:84+`.
- Filled-ice gotcha (cage key `small` NOT `guest` for c0te/c1te/c2te/ice1hte) verified: `types.py:130,141,152,163` all have `cage_type_map: {"small": "Ne1"}`.
- `--cage-guest` built-in-only (ch4/thf) enforced at `pipeline.py:102-107`.
- GenIce2 version 2.2.13.1 in the depol note (`cli-reference.md:752`) matches `environment.yml:43`.

**Mode behavior (`docs/cli-reference.md:99,126,1131-1163` vs `quickice/main.py`, `quickice/cli/pipeline.py`):**
- `--no-diagram` and `--gromacs` have no effect in pipeline mode (pipeline always exports GROMACS, never diagrams); both verified.
- Pipeline GRO/TOP use step-specific names (`{step_name}.gro/.top`, `pipeline.py:908-909`); ice-only requires `--gromacs` and writes `{phase_id}_{rank}.gro` + single `{phase_id}.top` (`main.py:121-135`).

**Routing (`docs/cli-reference.md:1231-1242`, `README.md:100-108` vs `quickice/entry.py:105-201`):**
- No args → help (exit 0); `--help`/`-h` → argparse help; `--version`/`-V` → version; `--gui` (priority) → GUI with PySide6+display checks; `--cli` → strip and delegate; pipeline flags → implicit CLI; priority `--gui > --cli > pipeline > help` — all match. Error messages for missing PySide6 / no display match `entry.py:170-175`.
- Backward-compat `python quickice.py` delegates to `entry.main` (`quickice.py:7`); `python -m quickice` uses `quickice/__main__.py:3`.

**Exit codes (`docs/cli-reference.md:282-287` vs `quickice/main.py`, `quickice/cli/pipeline.py`):** 0 success, 1 runtime error, 2 argparse error — match.

**Citations present and correct:**
- TIP4P-ICE: Abascal et al. 2005, DOI 10.1063/1.1931662 (`README.md:236-240`, `docs/cli-reference.md:1346`); constants not hardcoded (`quickice/output/gromacs_writer.py` re-exports `TIP4P_ICE_OW_SIGMA/EPSILON` from `_shared`, per `AGENTS.md:45`).
- Madrid2019: Zeron et al. 2019, DOI 10.1063/1.5121392 (`README.md:381-387`, `docs/cli-reference.md:1052`); code reference at `gromacs_ion_export.py:9,46` and `ion_inserter.py:28`; charges ±0.85e at `gromacs_ion_export.py:25-26`.
- spglib: DOI 10.1080/27660400.2024.2384822 (`docs/cli-reference.md:1203-1208`, `README.md:360-363`); used at `quickice/output/validator.py:11`.
- iapws: `README.md:338-348`; used at `quickice/phase_mapping/water_density.py:31` and `ice_ih_density.py:27` (CLI phase-mapping path).
- Water-volume / atoms-per-molecule constants used (not hardcoded): `WATER_VOLUME_NM3` and `WATER_ATOMS_PER_MOLECULE` at `quickice/cli/pipeline.py:16,568,838` (per `AGENTS.md:46-47`).

**Sample-output READMEs:** `sample_output/cli_ice/README.md` and `sample_output/cli_interface/README.md` use the backward-compat `python quickice.py` invocation with valid flags; the interface example (`-x 4 -y 4 -z 8 -t 2 -w 4`) satisfies the slab constraint (2×2+4=8).

---

*End of CLI documentation crosscheck — 2026-07-23. READ-ONLY; no files were modified.*
