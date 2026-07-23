# Verification of CLI Documentation-vs-Code Crosscheck (15 Issues)

**Date:** 2026-07-23
**Mode:** READ-ONLY verification — no fixes applied, no commits made.
**Verifier approach:** For each issue, opened the cited DOC file at the cited line AND the cited CODE file at the cited line, compared the actual text on both sides, and formed an independent verdict. The original crosscheck report was used ONLY to obtain the 15 issue IDs and their claimed locations; no other files in `.planning/code_analysis/` were read (to avoid bias).

**Source report:** `.planning/code_analysis/20260723_documentation_crosscheck_cli.md`

---

## Verdict Summary Table

| Issue ID | Claimed Severity | Verdict | Doc location | Code location | One-line reality |
|----------|------------------|---------|--------------|---------------|------------------|
| CLI-01 | High | **TRUE** | `docs/cli-reference.md:119` | `quickice/main.py:143`; `quickice/cli/itp_helpers.py:314` | Doc says `tip4p_ice.itp` (underscore); code writes `tip4p-ice.itp` (hyphen) in both ice-only and pipeline paths. |
| CLI-02 | Med | **TRUE** | `docs/cli-reference.md:147-158`; `scripts/cli-examples.sh:57` | `quickice/cli/pipeline.py:183-193`; `quickice/main.py` (ice-only path) | `--no-overwrite` is read only inside `CLIPipeline.execute()`; `args.no_overwrite` is never referenced in the ice-only path (grep-confirmed), so it is a silent no-op there. Doc presents it as general with an ice-only example. |
| CLI-03 | Med | **TRUE** | `scripts/cli-examples.sh:53-54` | `quickice/main.py:70-74`; `quickice/cli/pipeline.py:416-421` | Ice-only `generate_candidates(...)` is called with NO seed arg; `args.seed` is never read in ice-only path (grep-confirmed). Pipeline source step DOES pass `base_seed=self.args.seed`. Example misleadingly labels it "Reproducible generation with custom seed" in ice-only mode. |
| CLI-04 | Med | **TRUE** | `docs/cli-reference.md:122` | `quickice/data/tip4p-ice.itp:1-2` | Doc credits keinsci forum; the bundled data file's own header credits sklogwiki under CC-BY-NC-SA 3.0. |
| CLI-05 | Med | **TRUE** | `README.md:313-322` | `environment.yml:47,55`; `quickice/output/validator.py:11`; `quickice/output/phase_diagram.py:13` | README deps table lists 8 packages (iapws, numpy, scipy, vtk, PySide6, genice2, genice-core, pytest) — omits `spglib` and `matplotlib`, both pinned in environment.yml and imported by CLI-path modules. |
| CLI-06 | Low | **TRUE** | `docs/cli-reference.md:84,1184` | `quickice/output/phase_diagram.py:1079-1081` | Doc mentions only `phase_diagram.png`; code also emits `phase_diagram.svg` and `phase_diagram_data.txt`. |
| CLI-07 | Low | **TRUE** | `docs/cli-reference.md:83` | `quickice/main.py:159-162` | Doc says glob `candidate_*.pdb`; code uses `base_name="ice_candidate"` → `ice_candidate_*.pdb`. Doc line 1175 (later) is correct; line 83 is wrong. |
| CLI-08 | Low | **TRUE** | `docs/cli-reference.md:1238` | `quickice/cli/parser.py:52-66`; `quickice/entry.py:181-187` | Both `--temperature` and `--pressure` are `required=True`. `--cli` alone is stripped to empty argv → argparse reports BOTH required args missing. Doc says only "Missing required `--temperature`". |
| CLI-09 | Low | **TRUE** | `docs/cli-reference.md:445` | `quickice/cli/parser.py:185-191,444-447` | `--pocket-shape` has `default="sphere"`; `validate_interface_args` only requires `pocket_diameter` (explicit comment: "pocket_shape has default, no validation needed"). Doc labels it "Required with" — it is optional. |
| CLI-10 | Low | **TRUE** | `docs/cli-reference.md:1139` | `quickice/main.py:121-122` | Doc summary table shows ice-only GRO as `{ice_type}.gro`; code writes `{phase_id}_{rank}.gro` (e.g. `ice_ih_1.gro`). Doc line 117 (detailed) is correct; line 1139 is wrong. |
| CLI-11 | Low | **TRUE** | `quickice/cli/pipeline.py:1,3`; `quickice/cli/parser.py:4` | `quickice/cli/pipeline.py:136`; `quickice/cli/parser.py:386` | Module docstrings say "v4.5" and "ice → interface", but the class docstring (line 136) says "source → interface" and the version constant is 4.7.0. Internal code-docstring contradiction. (Code-comment fix, not a user-doc fix.) |
| CLI-12 | Low | **TRUE** | `README.md:16,116,253,255,257-271` | (internal README consistency) | README conflates counts: line 16/116 say "11 ice polymorphs" (line 116 list omits Ice XI); line 253 header says "12 phases"; line 255 says "11"; the 12-row table (257-271) includes Ice XI. Generation is actually 8 (lines 274-288). |
| CLI-13 | Low | **TRUE** | `scripts/hydrate-interface-custom-ion.sh:17,105` | `quickice/cli/parser.py:207-212`; `quickice/structure_generation/interface_builder.py:121` | Script documents only sI/sII/sH and exposes no `--cage-guest`/`--depol`. It hardcodes `--interface --mode slab` (line 166); passing `c0te`/`c1te` would reach argparse (valid choice) but fail at the interface step (TRICLINIC_HYDRATE_PHASES block). |
| CLI-14 | Low | **TRUE** (fix direction needs confirmation) | `docs/cli-reference.md:1284`; `README_bin.md:10` | `README_bin.md:44-56` | Both platform-invocation tables list "Binary (Linux/macOS)", but the asset list documents only Linux and Windows binaries. Actual macOS-binary existence could NOT be verified from in-repo files (no build script / release manifest inspected). |
| CLI-15 | Low | **TRUE** | `docs/cli-reference.md:574-578,950,964-965` (+ no IAPWS/GenIce2 cite) | `quickice/structure_generation/hydrate_generator.py:48-49`; `quickice/phase_mapping/water_mapping.py:31`; `quickice/output/validator.py:11` | cli-reference names "Teeratchanan 2015"/"Smirnov 2013" in the lattice table without full citations; absent from README References. Uses GAFF2 and relies on IAPWS + GenIce2 without citing them (grep: no "iapws" in cli-reference.md; GenIce2 only mentioned in passing, no DOI/section). |

**Verdict counts:** 15 TRUE / 0 FALSE ALARM / 0 PARTIAL.

---

## Detailed Findings (per issue)

### CLI-01 — Exported TIP4P ITP filename: underscore vs hyphen (TRUE)
**Claim:** Doc says exported ITP is `tip4p_ice.itp` (underscore); code writes `tip4p-ice.itp` (hyphen).

**Actual doc text** (`docs/cli-reference.md:119`):
> - **Single `.itp` file** — `tip4p_ice.itp` (force field is identical for all candidates)

**Actual code:**
- `quickice/main.py:143` — `itp_filename = "tip4p-ice.itp"` (hyphen)
- `quickice/main.py:138-141` — comment: *"The bundled data file is quickice/data/tip4p-ice.itp (hyphen, not underscore)."*
- `quickice/cli/itp_helpers.py:314` — `tip4p_dest = output_dir / "tip4p-ice.itp"` (hyphen)

**Verdict + rationale:** TRUE. The doc uses an underscore while both the ice-only and pipeline code paths write a hyphen. The `.top` `#include` must reference the hyphen form, so a user scripting against the doc's `tip4p_ice.itp` would get a broken include. Note `README.md` already uses the hyphen form (per the report's cross-reference), so only `cli-reference.md` is wrong.

**Suggested action:** Doc-fix — replace `tip4p_ice.itp` with `tip4p-ice.itp` at `docs/cli-reference.md:119`.

---

### CLI-02 — `--no-overwrite` is a silent no-op in ice-only mode (TRUE)
**Claim:** `--no-overwrite` only works in pipeline mode; silently ignored in ice-only mode, but doc/example present it as general.

**Actual doc text** (`docs/cli-reference.md:147-158`):
> Do not overwrite existing output files. When this flag is set, QuickIce checks if the output directory already contains files before writing. If files exist, the pipeline skips this run and exits with code 0 (success; the existing files are left untouched)...
> ```bash
> # Safe re-run without overwriting existing results
> python -m quickice -T 260 -P 0.1 -N 100 --no-overwrite
> ```

**Actual code:**
- `quickice/cli/pipeline.py:182-193` — `--no-overwrite` is checked only inside `CLIPipeline.execute()` (pipeline mode).
- `quickice/main.py` ice-only path (lines 99-166) — `args.no_overwrite` is **never referenced** (grep for `no_overwrite|args.seed|args.no_overwrite` in `main.py` returned ZERO matches in main.py; only pipeline.py:183 and parser.py:529 matched). The ice-only path calls `output_path.mkdir(parents=True, exist_ok=True)` (line 102) and writes GROMACS/PDB/diagram files unconditionally.
- `scripts/cli-examples.sh:57` — `# python -m quickice -T 250 -P 0.1 -N 96 --no-overwrite` (ice-only example, no pipeline flags).

**Verdict + rationale:** TRUE. Unlike `--no-diagram` (line 99) and `--gromacs` (line 126), which both carry explicit "In pipeline mode..." caveats, `--no-overwrite` has NO such caveat, yet its example is ice-only where the flag does nothing. A user relying on this in ice-only mode would silently have files overwritten.

**Suggested action:** Doc-fix — add an ice-mode caveat to `docs/cli-reference.md:147-158` mirroring the `--no-diagram`/`--gromacs` notes, and/or relabel the `cli-examples.sh:57` example as pipeline-only.

---

### CLI-03 — `--seed` is a no-op in ice-only mode (TRUE)
**Claim:** `--seed` is a no-op in ice-only mode; example labels it "Reproducible generation with custom seed".

**Actual doc/example text** (`scripts/cli-examples.sh:53-54`):
> `# Reproducible generation with custom seed`
> `# python -m quickice -T 250 -P 0.1 -N 96 --seed 12345`

**Actual code:**
- `quickice/main.py:70-74` — ice-only candidate generation:
  `gen_result = generate_candidates(phase_info=phase_info, nmolecules=args.nmolecules, n_candidates=10)` — **no seed argument**; `args.seed` is never read in the ice-only path (grep-confirmed: zero `args.seed` matches in main.py).
- `quickice/cli/pipeline.py:416-421` — pipeline source step DOES use it: `generate_candidates(phase_info, nmolecules=nmolecules, n_candidates=1, base_seed=self.args.seed)`. (Also used at pipeline.py:469, 587, 605, 680, 845 for interface/custom/solute/ion steps.)

**Verdict + rationale:** TRUE. The example promises "Reproducible generation with custom seed" in ice-only mode, but the ice-only path never passes a seed. The flag only takes effect in pipeline mode. (If ice-only reproducibility is intended, that is a code gap; as stated, the doc/example over-promises.)

**Suggested action:** Doc/example-fix — remove or relabel `scripts/cli-examples.sh:53-54`, OR scope it to a pipeline example.

---

### CLI-04 — TIP4P-ICE itp source credit mismatch (TRUE)
**Claim:** Doc credits keinsci; the data file credits sklogwiki.

**Actual doc text** (`docs/cli-reference.md:122`):
> Credit: itp file adapted from http://bbs.keinsci.com/forum.php?mod=viewthread&tid=32973&page=1#pid222346

**Actual code** (`quickice/data/tip4p-ice.itp:1-2`):
> ;File adapted from the following link under the cc-by-nc-sa 3.0 license https://creativecommons.org/licenses/by-nc-sa/3.0/
> ;http://www.sklogwiki.org/SklogWiki/index.php/GROMACS_topology_file_for_the_TIP4P/Ice_model

**Verdict + rationale:** TRUE. The doc's credit URL (keinsci forum) does not match the bundled file's own header (sklogwiki + CC-BY-NC-SA 3.0). These are two different sources.

**Suggested action:** Doc-fix — reconcile `docs/cli-reference.md:122` with the file header (sklogwiki URL + license). Keep Abascal et al. 2005 (DOI 10.1063/1.1931662, already at `:1346`) for the model itself.

---

### CLI-05 — README Dependencies table missing spglib and matplotlib (TRUE)
**Claim:** README deps table omits `spglib` and `matplotlib`, both used in the CLI path.

**Actual doc text** (`README.md:313-322`) — 8 rows only:
> `iapws`, `numpy`, `scipy`, `vtk`, `PySide6`, `genice2`, `genice-core`, `pytest`

**Actual code:**
- `environment.yml:55` — `spglib==2.7.0` (pinned)
- `environment.yml:47` — `matplotlib==3.10.8` (pinned)
- `quickice/output/validator.py:11` — `import spglib` (used by CLI ice-only validation via `output_ranked_candidates`)
- `quickice/output/phase_diagram.py:13` — `import matplotlib.pyplot as plt` (used by CLI ice-only phase-diagram path)

**Verdict + rationale:** TRUE. Both packages are pinned runtime dependencies imported by CLI-path modules, but absent from the README deps table. (`spglib` IS cited in README References at 360-363 and in cli-reference at 1203-1208, making its omission from the deps table an internal inconsistency.)

**Suggested action:** Doc-fix — add `spglib` (crystal-symmetry validation) and `matplotlib` (phase-diagram rendering) rows to `README.md:313-322`.

---

### CLI-06 — Phase-diagram outputs under-documented (TRUE)
**Claim:** Doc mentions only `phase_diagram.png`; code also emits `.svg` and `_data.txt`.

**Actual doc text:**
- `docs/cli-reference.md:84` — `- phase_diagram.png - Phase diagram showing input conditions`
- `docs/cli-reference.md:1183-1185` — `### Phase Diagram` → `output/phase_diagram.png`

**Actual code** (`quickice/output/phase_diagram.py:1079-1081`):
> `png_path = output_dir / "phase_diagram.png"`
> `svg_path = output_dir / "phase_diagram.svg"`
> `txt_path = output_dir / "phase_diagram_data.txt"`

(All three are written at lines 1084-1088; the module docstring at line 6 also states "Outputs PNG, SVG, and text data files.")

**Verdict + rationale:** TRUE. Two doc locations mention only the PNG; the code emits three files.

**Suggested action:** Doc-fix — list `phase_diagram.png`, `phase_diagram.svg`, and `phase_diagram_data.txt` at `docs/cli-reference.md:84` and the "Phase Diagram" subsection (~1181-1185).

---

### CLI-07 — PDB filename glob vs actual base name (TRUE)
**Claim:** Doc lists PDB glob as `candidate_*.pdb`; actual base is `ice_candidate`.

**Actual doc text** (`docs/cli-reference.md:83`):
> - `candidate_*.pdb` - Ranked ice structure candidates in PDB format

**Actual code** (`quickice/main.py:159-162`):
> `output_ranked_candidates(ranking_result=ranking_result, output_dir=args.output, base_name="ice_candidate", ...)`

→ produces `ice_candidate_01.pdb`, etc. (Consistent with `docs/cli-reference.md:1175`, which correctly shows `output/ice_candidate_03.pdb`.)

**Verdict + rationale:** TRUE. Line 83 says `candidate_*.pdb`; line 1175 and the code say `ice_candidate_*.pdb`. Internal doc inconsistency + doc-vs-code mismatch.

**Suggested action:** Doc-fix — change `docs/cli-reference.md:83` to `ice_candidate_*.pdb`.

---

### CLI-08 — `--cli` alone: which required args are missing (TRUE)
**Claim:** `--cli` alone fails on BOTH `--temperature` and `--pressure`; doc says only "Missing required --temperature".

**Actual doc text** (`docs/cli-reference.md:1238`):
> | `--cli` alone | CLI (error) | Missing required `--temperature` |

**Actual code:**
- `quickice/cli/parser.py:52-58` — `--temperature`/`-T` with `required=True`
- `quickice/cli/parser.py:60-66` — `--pressure`/`-P` with `required=True`
- `quickice/entry.py:181-187` — `--cli` is stripped: `clean_argv = [arg for arg in effective_args if arg not in ('--cli', '--gui')]`, then `sys.argv = [sys.argv[0]] + clean_argv` and delegates to `cli_main()` → `get_arguments()` → `create_parser().parse_args()`.

With `--cli` alone, `clean_argv` is empty, so argparse sees no `-T` and no `-P` and reports BOTH required arguments missing (standard argparse error lists all missing required args; exit code 2).

**Verdict + rationale:** TRUE. The doc cell names only `--temperature`; both `--temperature` and `--pressure` are required and both would be reported missing.

**Suggested action:** Doc-fix — change the cell at `docs/cli-reference.md:1238` to "Missing required `--temperature` and `--pressure`".

---

### CLI-09 — `--pocket-shape` labeled "Required" despite having a default (TRUE)
**Claim:** `--pocket-shape` has a default (`sphere`) yet doc labels it "Required with: --interface --mode pocket".

**Actual doc text** (`docs/cli-reference.md:441-445`):
> **Choices:** `sphere`, `cubic`
> **Default:** `sphere`
> **Required with:** `--interface --mode pocket`

**Actual code:**
- `quickice/cli/parser.py:185-191` — `--pocket-shape` with `choices=["sphere", "cubic"]`, `default="sphere"`
- `quickice/cli/parser.py:444-447` — pocket-mode validation:
  > `if args.pocket_diameter is None:` → `parser.error("--pocket-diameter is required for pocket mode")`
  > `# pocket_shape has default, no validation needed`

**Verdict + rationale:** TRUE. The flag has a default and is explicitly NOT validated as required (the code comment confirms). The doc convention "Required with" (e.g. `--mode` "Required with: --interface", where `--mode` IS required) implies the user must supply it; for `--pocket-shape` that is false.

**Suggested action:** Doc-fix — change "Required with" to "Only relevant with" (or drop the line) at `docs/cli-reference.md:445`.

---

### CLI-10 — Ice-only GRO filename in summary table (TRUE)
**Claim:** Ice-only GRO file shown as `{ice_type}.gro`; actual is `{phase_id}_{rank}.gro`.

**Actual doc text** (`docs/cli-reference.md:1139`):
> | GRO file | Step-specific names (e.g., `ion.gro`, `solute.gro`) | `{ice_type}.gro` |

**Actual code** (`quickice/main.py:121-122`):
> `base_name = f"{candidate.phase_id}_{rc.rank}"`
> `gro_filepath = output_path / f"{base_name}.gro"`

→ e.g. `ice_ih_1.gro` (rank suffix present). Consistent with the detailed `--gromacs` section at `docs/cli-reference.md:117` (`ice_ih_1.gro`).

**Verdict + rationale:** TRUE. The summary table omits the `_{rank}` suffix; the detailed section and code both include it.

**Suggested action:** Doc-fix — use `{ice_type}_{rank}.gro` at `docs/cli-reference.md:1139` to match `:117`.

---

### CLI-11 — Stale "v4.5" / "ice" wording in CLI module docstrings (TRUE)
**Claim:** Stale "v4.5" in module docstrings; pipeline.py line 3 says "ice → interface" while the class docstring (line 136) correctly says "source → interface".

**Actual code text:**
- `quickice/cli/pipeline.py:1` — `"""CLI pipeline for QuickIce v4.5."""`
- `quickice/cli/pipeline.py:3-4` — `"""Orchestrates the ice → interface → custom → solute → ion → export workflow..."""`
- `quickice/cli/parser.py:4-5` — `"...for temperature, pressure, molecule count, and v4.5 pipeline flags (hydrate, custom molecule, solute, ion insertion)."`
- `quickice/cli/pipeline.py:136` (class docstring) — `"Runs ordered steps (source → interface → custom → solute → ion → export)"`
- `quickice/cli/parser.py:386` — `version="%(prog)s 4.7.0"` (current version; v4.7 added `--cage-guest`, `--depol`, filled-ice lattices)

**Verdict + rationale:** TRUE. The module docstrings are internally contradictory with the class docstring (line 136) and with the actual version (4.7.0). The "ice →" wording omits the hydrate source added in v4.7. These are code comments/docstrings (not user-facing docs), but they are genuine inconsistencies within the code.

**Suggested action:** Code-comment-fix (not user-doc) — update `pipeline.py:1` → "v4.7", `pipeline.py:3` "ice →" → "source →", `parser.py:4` "v4.5" → "v4.7" (optionally mention cage-guest/depol).

---

### CLI-12 — README ice-polymorph count: detection vs generation (TRUE)
**Claim:** README conflates detection vs generation counts ("11 ice polymorphs" vs "12 phases" vs 12-row table vs line 116 omits Ice XI).

**Actual doc text:**
- `README.md:16` — `**Ice Generation** — 11 ice polymorphs from thermodynamic conditions`
- `README.md:116` — `- **11 ice polymorphs** — Ih, Ic, II, III, V, VI, VII, VIII, IX, XV, X` (omits Ice XI; listed under "Tab 0: Ice Generation")
- `README.md:253` — `### Phase Detection (12 phases)`
- `README.md:255` — `The interactive phase diagram can identify 11 ice polymorphs based on temperature and pressure conditions:`
- `README.md:257-271` — 12-row detection table (Ih, Ic, II, III, V, VI, VII, VIII, IX, **XI**, XV, X) — includes Ice XI

**Cross-reference:** `docs/cli-reference.md:178` correctly states "8 ice polymorphs (those with GenIce2 lattice implementations)" for generation; `README.md:274-289` separately lists 8 generatable + 4 detection-only (IX, XI, XV, X). So generation = 8, detection = 12, but README's "11" appears in both a generation context (line 16) and a detection context (line 255) and the line-116 list omits Ice XI while the detection table includes it.

**Verdict + rationale:** TRUE. The README conflates the three counts (12 detection / 8 generation / "11" as stated) and the line-116 list is internally inconsistent with the 12-row detection table (omits Ice XI).

**Suggested action:** Doc-fix — in README, separate "detection (12, incl. Ice XI)" from "generation (8)"; fix line 116 to either include Ice XI or clarify it is the 8-phase generation list; align line 255 with the 12-row table.

---

### CLI-13 — `hydrate-interface-custom-ion.sh` lacks v4.7 surface and triclinic caveat (TRUE)
**Claim:** Script documents only sI/sII/sH and no v4.7 flags (`--cage-guest`, `--depol`); `c0te`/`c1te` would fail.

**Actual doc text:**
- `scripts/hydrate-interface-custom-ion.sh:17` — `#   --lattice-type TYPE  Hydrate lattice: sI, sII, sH (default: sI)`
- `scripts/hydrate-interface-custom-ion.sh:105` — `echo "  --lattice-type TYPE    Hydrate lattice: sI, sII, sH (default: sI)"`

**Actual code:**
- `quickice/cli/parser.py:207-212` — `--lattice-type` accepts 10 choices: `["sI", "sII", "sH", "c0te", "c1te", "c2te", "ice1hte", "sTprime", "16", "17"]`
- `quickice/structure_generation/interface_builder.py:121` — `TRICLINIC_HYDRATE_PHASES = {"hydrate_c0te", "hydrate_c1te"}`; line 122-129 raises `InterfaceGenerationError` for these when used with `--interface`.
- The script's parse loop (lines 42-124) handles only the documented flags; `--cage-guest` and `--depol` are NOT handled (unknown options error at line 117-120). The final command (line 166) hardcodes `--interface --mode slab` and does not include `--cage-guest`/`--depol`.

**Verdict + rationale:** TRUE. The script's documented 3-choice set is a safe subset but is unlabeled as such; the v4.7 features (`--cage-guest`, `--depol`) are inaccessible from this script. Because the script hardcodes `--interface`, passing `--lattice-type c0te` (a valid argparse choice) would pass parsing but fail at `interface_builder.py:121` (triclinic block) — so the report's "c0te/c1te would fail" is accurate (fails at the interface step, not at argparse).

**Suggested action:** Doc/example-fix — note in `scripts/hydrate-interface-custom-ion.sh:17,105` that only orthogonal (interface-compatible) lattices (sI/sII/sH) are supported by this script, and that v4.7 features require calling `python -m quickice` directly. (No code change needed.)

---

### CLI-14 — Platform Invocation lists a macOS binary (TRUE — fix direction needs confirmation)
**Claim:** CLI ref "Platform Invocation" lists a macOS binary; `README_bin.md` documents only Linux/Windows.

**Actual doc text:**
- `docs/cli-reference.md:1284` — `| Binary (Linux/macOS) | quickice-gui [options] |`
- `README_bin.md:10` — `| Binary (Linux/macOS) | quickice-gui [options] |` (same table)
- `README_bin.md:44-56` — assets: `quickice-v4.7.0-linux-x86_64.tar.gz` (Linux, lines 44-52) and `quickice-v4.7.0-windows-x86_64.zip` (Windows, lines 54-60) — NO macOS asset listed.

**Actual code:** No in-repo build script or release manifest was inspected, so the existence of an actual macOS binary could NOT be verified from files read.

**Verdict + rationale:** TRUE. Both platform-invocation tables claim a macOS binary, but the asset list documents only Linux and Windows. This is a confirmed doc inconsistency. The *direction* of the fix (add macOS to the asset list if it exists, vs. change "Linux/macOS" → "Linux" if it does not) cannot be determined from in-repo files alone — hence "needs confirmation".

**Suggested action:** Needs confirmation — either confirm a macOS binary exists (and add it to `README_bin.md:44-56`) or change "Linux/macOS" to "Linux" in both `docs/cli-reference.md:1284` and `README_bin.md:10`.

---

### CLI-15 — Missing/under-cited references in cli-reference.md (TRUE)
**Claim:** Filled-ice sources (Teeratchanan 2015, Smirnov 2013) named in the cli-reference table but absent from README References; GAFF2/IAPWS/GenIce2 not cited where used.

**Actual doc text:**
- `docs/cli-reference.md:574-578` — lattice table rows: `Filled ice C0 (Teeratchanan 2015)`, `...C1 (Teeratchanan 2015)`, `...C2 (Teeratchanan 2015)`, `Filled ice Ih (Teeratchanan 2015)`, `Filled ice sT′ (Smirnov 2013)` — surname+year only, no DOI/bibliographic entry.
- `docs/cli-reference.md:950,964-965` — solute section mentions GAFF2 (e.g. "`GAFF2 (c3, hc)`") with no citation.
- `README.md:324-388` (References) — contains GenIce2, IAPWS (R14-08, R10-06, IAPWS-95), Journaux, Petrenko & Whitworth, CODATA 2017, spglib, Multiwfn, Sobtop, GAFF/GAFF2, Gaussian 16, Madrid2019 — but NO Teeratchanan 2015 and NO Smirnov 2013.
- grep for `iapws` (case-insensitive) in `docs/cli-reference.md` → **zero matches** (IAPWS is not mentioned at all in cli-reference.md).
- grep for `genice` in `docs/cli-reference.md` → matches at lines 124, 178, 276, 588, 725, 752 — GenIce2 is mentioned in passing but has NO citation section, DOI, or repository link in cli-reference.md.

**Actual code:**
- `quickice/structure_generation/hydrate_generator.py:48` — `"- c0te, c1te, c2te, ice1hte: Filled ice structures (Teeratchanan 2015)"`
- `quickice/structure_generation/hydrate_generator.py:49` — `"- sTprime: Filled ice sT' (Smirnov 2013) — water-only"`
- `quickice/phase_mapping/water_density.py:31` — `from iapws import IAPWS95` (IAPWS used for CLI phase-mapping/density)
- `quickice/structure_generation/gromacs_ion_export.py:9` — Madrid2019 (already cited at `cli-reference.md:1052`)
- `quickice/output/validator.py:11` — `import spglib` (already cited at `cli-reference.md:1203-1208`)

**Verdict + rationale:** TRUE. The named filled-ice sources lack citable references in both cli-reference and README. GAFF2 is used in the solute section without a citation (it IS cited in `docs/gro-itp-guide.md:947` and `README.md:374-376`, but not in cli-reference). IAPWS underpins the CLI phase lookup but is absent from cli-reference entirely. GenIce2 is the structure-generation backbone but only mentioned in passing (no DOI/paper). Madrid2019, spglib, and TIP4P-ICE ARE already correctly cited in cli-reference (1052, 1203-1208, 1346).

**Suggested action:** Doc-fix — add full citations for Teeratchanan 2015 and Smirnov 2013 (in cli-reference lattice table + README References); add GAFF2, IAPWS (R14-08/R10-06/IAPWS-95), and GenIce2 citations to cli-reference where used (all already exist in README References and can be mirrored).

---

## Confirmed Doc-Fixes Needed (with suggested priority)

| Priority | Issue | Fix summary |
|----------|-------|-------------|
| **P0** | CLI-01 | `docs/cli-reference.md:119`: `tip4p_ice.itp` → `tip4p-ice.itp` (breaks `#include` references if user scripts against the doc). |
| **P0** | CLI-02 | `docs/cli-reference.md:147-158` + `scripts/cli-examples.sh:57`: add ice-mode caveat that `--no-overwrite` is a no-op in ice-only mode (silent overwrite/data-loss risk). |
| **P1** | CLI-03 | `scripts/cli-examples.sh:53-54`: remove/relabel the ice-only `--seed` example (reproducibility not delivered in ice-only mode). |
| **P1** | CLI-04 | `docs/cli-reference.md:122`: reconcile credit with the data file header (sklogwiki + CC-BY-NC-SA 3.0). |
| **P1** | CLI-05 | `README.md:313-322`: add `spglib` and `matplotlib` rows to the Dependencies table. |
| **P1** | CLI-07 | `docs/cli-reference.md:83`: `candidate_*.pdb` → `ice_candidate_*.pdb` (breaks user globs). |
| **P1** | CLI-10 | `docs/cli-reference.md:1139`: `{ice_type}.gro` → `{ice_type}_{rank}.gro` (breaks user globs). |
| **P2** | CLI-06 | `docs/cli-reference.md:84,1183-1185`: list `phase_diagram.svg` and `phase_diagram_data.txt` alongside the PNG. |
| **P2** | CLI-08 | `docs/cli-reference.md:1238`: "Missing required `--temperature`" → "Missing required `--temperature` and `--pressure`". |
| **P2** | CLI-09 | `docs/cli-reference.md:445`: change "Required with" → "Only relevant with" (flag is optional, has default `sphere`). |
| **P2** | CLI-11 | (Code-comment fix, not user doc) `quickice/cli/pipeline.py:1,3` and `quickice/cli/parser.py:4`: update stale "v4.5" / "ice →" to "v4.7" / "source →". |
| **P2** | CLI-12 | `README.md:16,116,253,255`: separate detection (12, incl. Ice XI) from generation (8); fix line 116 (omits Ice XI) and align line 255 with the 12-row table. |
| **P2** | CLI-13 | `scripts/hydrate-interface-custom-ion.sh:17,105`: note only sI/sII/sH are interface-compatible here; v4.7 flags (`--cage-guest`/`--depol`) require `python -m quickice` directly. |
| **P2 (needs confirmation)** | CLI-14 | `docs/cli-reference.md:1284` + `README_bin.md:10`: confirm whether a macOS binary exists; either add it to the asset list or change "Linux/macOS" → "Linux". |
| **P2** | CLI-15 | `docs/cli-reference.md`: add full citations for Teeratchanan 2015, Smirnov 2013, GAFF2, IAPWS, GenIce2 (mirror existing README References). |

---

## False Alarms

**None.** All 15 reported issues were verified as TRUE against the actual documentation text and actual source code. No report claim was found to be a false alarm.

---

## Notes & Caveats

- **CLI-11** is a code-comment/docstring inconsistency, not a user-facing documentation issue. The fix is in source docstrings (`pipeline.py`, `parser.py`), not in `docs/` or `README.md`. Listed under "confirmed doc-fixes" for completeness but flagged as a code-comment fix.
- **CLI-14** is the only issue where the *direction* of the fix is uncertain: the doc inconsistency (platform table says macOS; asset list says only Linux/Windows) is confirmed TRUE, but whether a macOS binary actually exists could not be verified from in-repo files (no build script / release manifest was inspected). Marked "needs confirmation".
- **CLI-15** overlaps with the source report's "Citation Suggestions" table (C-1 through C-8). The citation gaps are real; the suggested action is to mirror citations already present in `README.md` References into `docs/cli-reference.md`.
- Verification was strictly read-only. No files were modified and no git operations were performed.

---

*End of verification — 2026-07-23. READ-ONLY; no files were modified; no commits made.*
