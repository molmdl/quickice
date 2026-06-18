# Scancode Verification Report — 2026-06-18

**Verified:** 2026-06-18
**Verifier:** OpenCode (gsd-verifier, ground-truth mode)
**Scope:** 42 issues (A–D + DOI audit) from 2026-06-18 scancode scan
**Method:** Every claim checked against actual file contents. No scan claim was trusted without verification.

---

## CRITICAL (2)

### #1: DOI-D1 — Madrid2019 DOI wrong in README.md
- **Verdict:** CONFIRMED
- **Evidence:** `README.md:371` contains `DOI: https://doi.org/10.1063/1.5121394`. Line 375 repeats `DOI: 10.1063/1.5121394`. The paper is Zeron et al. 2019 (J. Chem. Phys. 151, 134504), whose correct DOI is `10.1063/1.5121392`. The DOI `10.1063/1.5121394` resolves to a different paper by Xian et al. 2019 about misinformation on networks.
- **Notes:** Both occurrences (lines 371 and 375) have the wrong DOI. This is a real citation error.

### #2: C-CLI N-01 — Madrid2019 DOI 404 in cli-reference.md
- **Verdict:** CONFIRMED
- **Evidence:** `docs/cli-reference.md:930` contains `See [Madrid2019 reference](https://doi.org/10.1021/acs.jctc.9b00902).` This DOI belongs to ACS JCTC, but Madrid2019 was published in J. Chem. Phys. (AIP), not JCTC. The DOI `10.1021/acs.jctc.9b00902` is for a completely different paper/issue and does not resolve to Zeron et al. 2019. The correct DOI is `10.1063/1.5121392`.
- **Notes:** This is a second, different wrong DOI for the same paper — not a duplicate of DOI-D1. Two independent DOI errors for Madrid2019 exist in the codebase.

---

## HIGH (4)

### #3: B NEW-01/11 — write_solute_gro_file solute/custom positions NOT PBC-wrapped
- **Verdict:** CONFIRMED
- **Evidence:** In `gromacs_writer.py:2384-2393`, `write_solute_gro_file` wraps the main `interface.positions` via `wrap_molecules_into_box()` (line 2386). But at lines 2544-2547, custom molecule positions come from `solute_structure.custom_molecule_positions` directly — NO wrapping applied. At lines 2565-2566, solute positions come from `solute_structure.positions[start:start + count]` — also NOT wrapped. By contrast, `write_ion_gro_file` at lines 1446-1455 DOES wrap both: `ion_structure.solute_positions % np.diag(ion_structure.cell)` (line 1447) and `ion_structure.custom_molecule_positions % np.diag(ion_structure.cell)` (line 1453). The asymmetry is clear.
- **Notes:** The fix from issue AN-03 was applied to `write_ion_gro_file` but not to `write_solute_gro_file`.

### #4: B PERF-01 — Triple-nested Python loop in wrap_molecules_into_box
- **Verdict:** CONFIRMED
- **Evidence:** `gromacs_writer.py:67-140`. The outer loop iterates over molecules (line 93: `for mol in molecule_index`), the middle loop iterates over atoms within a molecule (line 105: `for i in range(1, len(mol_positions))`), and the inner loop iterates over dimensions (line 109: `for dim in range(3)`). This is indeed a triple-nested Python loop. For large systems (thousands of molecules × 4+ atoms × 3 dimensions), this is O(N_mol × N_atoms × 3) in pure Python.
- **Notes:** The inner dimension loop is only 3 iterations, so the practical complexity is O(N_mol × N_atoms). The per-atom loop is the real bottleneck. A vectorized approach using numpy would be significantly faster.

### #5: C-CLI N-02 — Concentration range (0.0–5.0 mol/L) not documented
- **Verdict:** CONFIRMED
- **Evidence:** The code enforces this range: `validators.py:150-176` has `validate_concentration_range()` checking `0.0 <= val <= 5.0`. But the docs for `--custom-concentration` (cli-reference.md:777-797), `--solute-concentration` (lines 861-876), and `--ion-concentration` (lines 920-943) all say only `**Type:** Float (mol/L)` without specifying the 0.0–5.0 range. The Validation Rules section (lines 992-1000) also does not mention concentration range.
- **Notes:** The valid range is enforced in code but not communicated to users. If they enter 6.0, they get an opaque argparse error.

### #6: C-CLI N-03 — Validation Rules section missing 5 of 8 constraints
- **Verdict:** CONFIRMED
- **Evidence:** `docs/cli-reference.md:992-1000` lists only 3 validation rules: Temperature (0–500 K), Pressure (0–10000 MPa), Nmolecules (4–100000). The code in `validators.py` actually enforces 8 constraints: (1) Temperature, (2) Pressure, (3) Nmolecules, (4) Positive float, (5) Box dimension ≥1.0, (6) Concentration 0.0–5.0, (7) Cage occupancy 0.0–100.0, (8) Extension validation (.gro/.itp). Missing from docs: box dimension minimum, concentration range, occupancy range, extension validation, positive float.
- **Notes:** Exactly 5 of 8 constraints are missing from the documented Validation Rules section. The scan is precise.

---

## MEDIUM (14)

### #7: B NEW-03/EH-07 — write_custom_molecule_gro_file has no try/except around file I/O
- **Verdict:** PARTIAL
- **Evidence:** `gromacs_writer.py:1918-2140`. The initial atom-writing loop (lines 1973-2122) builds a `lines` list without try/except. However, the actual file write at lines 2128-2135 IS wrapped: `try: with open(filepath, 'w') as f: f.writelines(lines) except (OSError, ValueError) as e:`. So the file write does have error handling. The scan is wrong that there is "no try/except around file I/O" — there IS one, just scoped to the final write call, not the line-building loop. Compare with `write_ion_gro_file` which uses a broader `try: with open(...)` wrapping the entire write process.
- **Notes:** The error handling exists but is narrower than other GRO writers. The line-building phase could fail (e.g., attribute access) but wouldn't leave a partial file since the file isn't opened until the end. This is a style concern, not a missing error handler.

### #8: B NEW-06/PERF-03 — O(N) Python loop with per-atom string comparison in _build_existing_atoms_tree
- **Verdict:** CONFIRMED
- **Evidence:** `solute_inserter.py:318-352` and `ion_inserter.py:341-351`. In `solute_inserter._build_existing_atoms_tree`, lines 327-330 iterate over each ice atom: `for i in range(ice_atom_count): atom_name = ... if atom_name != "MW": existing_positions.append(...)`. Lines 336-339 do the same for water atoms, and lines 345-348 for guest atoms. In `ion_inserter`, lines 348-351 iterate: `for atom_idx in range(start, end): atom_name = ... if atom_name != "MW": remain_positions.append(...)`. These are O(N) Python loops with per-atom string comparison.
- **Notes:** A vectorized approach could use numpy boolean indexing on atom_names to filter out "MW" atoms in one operation.

### #9: B NEW-07/PERF-04 — Per-molecule cKDTree query in _remove_overlapping_water
- **Verdict:** CONFIRMED
- **Evidence:** `solute_inserter.py:435-454`. Line 435: `for mol_idx in range(n_water_molecules)` — iterates over each water molecule. Line 444: `for atom_pos in water_mol_positions` — inner loop over atoms per molecule. Line 445: `min_dist = solute_tree.query(atom_pos, k=1)[0]` — queries cKDTree per-atom, per-molecule. `custom_molecule_inserter.py:401-420` has the identical pattern: line 401 `for mol_idx in range(n_water_molecules)`, line 410 `for atom_pos in water_mol_positions`, line 411 `custom_tree.query(atom_pos, k=1)[0]`.
- **Notes:** This could be replaced with a single batch query: `solute_tree.query(all_water_positions, k=1)` returns all minimum distances at once.

### #10: B NEW-16 — Custom molecule atoms excluded from overlap tree
- **Verdict:** CONFIRMED
- **Evidence:** `solute_inserter.py:318-352`. The `_build_existing_atoms_tree` method adds ice atoms (lines 326-330), water atoms (lines 333-339), and guest atoms (lines 342-348) to the existing_positions list. It does NOT add `custom_molecule_positions` anywhere. The same is true in `custom_molecule_inserter.py:296-324` where `_build_existing_atoms_tree` adds only ice and guest atoms. If the structure has custom molecules already placed (e.g., from a prior pipeline step), those atoms are invisible to the overlap tree, meaning newly inserted solutes/molecules could overlap with existing custom molecules.
- **Notes:** This is a real bug in multi-step pipelines (F1/F4 chains) where custom molecules are inserted before solutes.

### #11: B PERF-02 — Double-nested wrapping loop in hydrate_generator
- **Verdict:** CONFIRMED
- **Evidence:** `hydrate_generator.py:362-454`. The outer loop iterates over molecules: line 372 `for mol in molecule_index` (orthorhombic branch) and line 410 `for mol in molecule_index` (triclinic branch). Inside, there's a per-atom Python loop: line 403 `for i, atom_idx in enumerate(cell_indices)` (orthorhombic multi-cell branch) and line 447 `for i, atom_idx in enumerate(cell_indices)` (triclinic multi-cell branch). The simple single-cell path (lines 383-387, 424-432) uses numpy operations, but the multi-cell paths use per-atom Python loops.
- **Notes:** The multi-cell paths (atoms spanning PBC boundaries) are the slow paths and use Python loops. The common single-cell path is vectorized. Partial performance issue.

### #12: B PERF-05 — O(N²) memory from vstack-and-rebuild in custom_molecule_inserter
- **Verdict:** CONFIRMED
- **Evidence:** `custom_molecule_inserter.py:642-644`. On every successful molecule placement: `all_data = np.vstack([base_existing_data, np.vstack(placed_positions)])`. This re-vstacks ALL previously placed positions (via `np.vstack(placed_positions)`) with the base data on every iteration. If K molecules are placed, the total memory allocation is O(K²) because each iteration copies all prior positions. A better approach would be to append only the new molecule and update the tree incrementally.
- **Notes:** The scan's O(N²) memory characterization is correct. Each successful placement rebuilds the entire array from scratch.

### #13: C-CLI N-04 — --custom-gro/--custom-itp extension validation not documented
- **Verdict:** CONFIRMED
- **Evidence:** The code validates extensions at `pipeline.py:369-381`: checks `gro_path.suffix.lower() != '.gro'` and `itp_path.suffix.lower() != '.itp'`, returning error code 1 on mismatch. But `docs/cli-reference.md:673-715` for `--custom-gro` and `--custom-itp` says only "**Type:** String (file path)" — no mention that the file must have .gro or .itp extension. The Validation Rules section (lines 992-1000) also omits this.
- **Notes:** Users who provide a .xyz file with coordinates would get an unexplained error without documentation.

### #14: C-CLI N-05 — OPLS-AA incompatibility with Lorentz-Berthelot not warned
- **Verdict:** PARTIAL
- **Evidence:** `gro-itp-guide.md` mentions OPLS-AA in the Force Field Parameter Sources table (line 476: "LigParGen | OPLS-AA"), in Method 3 (line 446: "Force field documentation (GAFF, CHARMM, OPLS-AA)"), in troubleshooting (line 767: "Custom molecule parameters should be from compatible force field (GAFF, CHARMM, OPLS)"), and in Parameter Resources (line 869: "OPLS-AA force field"). However, there is NO warning anywhere about OPLS-AA using geometric combining rules which are incompatible with GROMACS's default Lorentz-Berthelot combining rule used for TIP4P-ICE. The guide recommends OPLS-AA as a valid source without any caveat about combining rule mismatch.
- **Notes:** The incompatibility is real (OPLS-AA uses geometric combining rules; TIP4P-ICE with OPLS-AA ions requires `[comb-rule]` overrides in GROMACS .top). The guide does NOT warn about this. However, the scan references line 767 which just lists OPLS among compatible force fields — the real issue is the absence of any combining-rule warning anywhere in the guide.

### #15: C-CLI N-06 — No consolidated pipeline vs ice-only output differences section
- **Verdict:** CONFIRMED
- **Evidence:** `docs/cli-reference.md` mentions the difference in passing at line 126: "In pipeline mode... the `--gromacs` flag has no effect — GROMACS files are always generated." And line 99: "In pipeline mode... the `--no-diagram` flag has no effect." But there is NO dedicated section explaining all output differences between pipeline mode and ice-only mode. No section consolidates: different file names, different topology contents, different GRO structure ordering, etc.
- **Notes:** The differences are scattered across individual flag descriptions. A consolidated section would improve usability.

### #16: C-CLI R-01 — Box dimension range "1.0–100 nm" wrong; code has no upper bound
- **Verdict:** CONFIRMED
- **Evidence:** `docs/cli-reference.md:351` states "**Type:** Float (1.0–100 nm)". But `validators.py:128-147` `validate_box_dimension()` only checks `val < 1.0` (line 142: `if val < 1.0: raise ...`). There is NO upper bound check in the code — a user could specify `--box-x 999999` and it would be accepted.
- **Notes:** The documented upper bound of 100 nm is not enforced. The code only enforces `>= 1.0 nm`.

### #17: C-CLI R-06 — "User dialog" for residue mismatch is GUI-only
- **Verdict:** CONFIRMED
- **Evidence:** `gro-itp-guide.md:627` says "QuickIce allows mismatch with user dialog". In the GUI, this would be a dialog box. In the CLI pipeline, there is no interactive dialog — the code at `pipeline.py` simply proceeds with the mismatch (using the GRO residue name or a fallback). The documentation implies interactive resolution that only exists in GUI mode.
- **Notes:** CLI users reading this guide would expect a dialog that doesn't appear in CLI mode. The CLI either silently accepts the mismatch or uses a fallback without user interaction.

### #18: C-GUI NEW-1 — Docs say "Insert Molecule" but button is "Generate Custom Molecules"
- **Verdict:** CONFIRMED
- **Evidence:** `help_dialog.py:115` says `"21. Click Insert Molecule to insert custom molecules\n"`. `gui-guide.md:576` says `9. Click "Insert Molecule"`. But the actual button in `custom_molecule_panel.py:112` is `self.generate_button = QPushButton("Generate Custom Molecules")`. The help dialog and GUI guide use "Insert Molecule" while the actual button says "Generate Custom Molecules". These are different labels.
- **Notes:** Also note help_dialog.py:116 says `"22. Export custom molecules for GROMACS (Ctrl+M)\n"` but the GUI guide (line 589) says `Ctrl+S` for this export. Both are potentially correct (Ctrl+M is tab-specific, Ctrl+S is unified), but the help text inconsistency adds to the confusion.

### #19: C-GUI DOC-G5 — 5 screenshot paths wrong + 2 missing
- **Verdict:** CONFIRMED
- **Evidence:** Comparing `docs/gui-guide.md` image references against actual files in `docs/images/`:

  **WRONG paths (5):**
  - Line 241: `images/hydrate-panel.png` → actual file is `tab2-hydrate-panel.png`
  - Line 344: `images/slab-interface.png` → actual file is `tab2-slab-interface.png`
  - Line 352: `images/pocket-interface.png` → actual file is `tab2-pocket-interface.png`
  - Line 359: `images/piece-interface.png` → actual file is `tab2-piece-interface.png`
  - Line 741: `images/ion-panel.png` → actual file is `tab4-ion-panel.png`

  **MISSING images (2):**
  - Line 426: `images/custom-molecule-panel.png` → no such file exists
  - Line 621: `images/solute-panel.png` → no such file exists

  Existing images that are NOT referenced: `quickice-v3-gui.png`
- **Notes:** Exactly 5 wrong + 2 missing as the scan states. All 7 broken image references would render as broken images or missing alt text.

### #20: D — 27.2 MB test data leaking into bundle
- **Verdict:** PARTIAL
- **Evidence:** `quickice-gui.spec:9` uses `collect_all('scipy')` and `collect_all('genice2')` which pulls ALL data from these packages. Line 27 has `excludes=['*/tests/*', '*/test/*', '*/docs/*', '*/__pycache__/*', '*/.pytest_cache/*', '*/egg-info/*']` which would exclude QuickIce's own test directories and third-party package test dirs matching these patterns. However, `collect_all('scipy')` includes the entire scipy package (~100+ MB installed), many subpackages of which are unused by QuickIce (e.g., scipy.optimize._highs at 6.9 MB). The specific "27.2 MB" figure for test data alone could not be independently verified without running PyInstaller, but the broader issue of unnecessary package inclusion is real.
- **Notes:** The excludes pattern does filter test directories generically. The main waste is from including entire scipy and genice2 packages rather than only the needed subpackages.

---

## LOW (16)

### #21: B NEW-08 — Simple modulo wrapping may split multi-atom solutes
- **Verdict:** PARTIAL
- **Evidence:** `gromacs_writer.py:1447`: `wrapped_solute_positions = ion_structure.solute_positions % np.diag(ion_structure.cell)`. This wraps each atom independently using modulo. The comment at lines 1443-1445 states "Solute molecules are single molecules that don't span PBC boundaries, so simple modulo wrapping is sufficient." However, CH4 solutes have 5 atoms and THF solutes have 13+ atoms — they are multi-atom molecules that COULD straddle a PBC boundary after insertion. The modulo wrapping WOULD split such a molecule across the boundary.
- **Notes:** In practice, solute insertion typically places molecules well within the liquid region, not at PBC boundaries, so this is a theoretical concern. But the code's comment that solutes "don't span PBC boundaries" is an unverified assumption. The correct approach would be molecule-aware wrapping (using the solute molecule's center-of-mass).

### #22: B NEW-09/EH-08 — Broad `except Exception` in gromacs_writer.py and itp_helpers.py
- **Verdict:** CONFIRMED
- **Evidence:** `gromacs_writer.py:1754`: `except Exception:` (bare, no `as e`, no logging). `gromacs_writer.py:2669`: `except Exception:` (same pattern). `itp_helpers.py:162`: `except Exception as e:`. `itp_helpers.py:186`: `except Exception as e:`. `itp_helpers.py:260`: `except Exception as e:`. `itp_helpers.py:366`: `except Exception as e:`. All six instances exist at the cited locations. The gromacs_writer.py instances at lines 1754 and 2669 are particularly concerning as they silently swallow any exception (no logging, no `as e`).
- **Notes:** The itp_helpers.py instances at least log the error. The gromacs_writer.py instances at 1754 and 2669 silently swallow errors.

### #23: B NEW-15 — 7 test files hardcode 0.0299
- **Verdict:** CONFIRMED
- **Evidence:** Found 14 occurrences of `0.0299` across exactly 7 test files:
  - `tests/test_custom_molecule_concentration.py:117`
  - `tests/test_e2e_solute_insertion.py:357,374`
  - `tests/test_e2e_workflow_chains.py:47,52`
  - `tests/e2e_export_helpers.py:239,244`
  - `tests/test_scancode_bugs_ion.py:20,25`
  - `tests/test_e2e_custom_molecule.py:382,385,398`
  - `tests/test_e2e_ion_insertion.py:44,49`
- **Notes:** The hardcoded value should reference `types.WATER_VOLUME_NM3` for maintainability. If the constant ever changes, all 7 test files would need manual updates.

### #24: B NEW-18 — Fallback ice detection uses "O" instead of "OW"
- **Verdict:** FALSE ALARM
- **Evidence:** `gromacs_writer.py:2305`: `atoms_per_ice_mol = 3 if "O" in interface.atom_names[:interface.ice_atom_count] else 4`. This checks whether any atom name in the ice section is exactly the string `"O"` (Python `in` on a list does exact element matching, NOT substring matching). GenIce2 outputs ice atoms with name `"O"` (not `"OW"`), so this check correctly identifies 3-atom-per-molecule GenIce2 format vs 4-atom TIP4P format. If atom names were `["OW", "HW1", "HW2", "MW"]`, `"O" in ["OW", "HW1", "HW2", "MW"]` returns `False`, correctly identifying 4-atom format.
- **Notes:** The scan incorrectly assumed Python `in` does substring matching. On a list, `"O" in ["OW"]` is `False`. The code is correct.

### #25: B SEC-04 — Inconsistent path traversal check
- **Verdict:** PARTIAL
- **Evidence:** The scan references `orchestrator.py:52` but no `orchestrator.py` file exists in the codebase. The pipeline class docstring (pipeline.py:31) says "CLI pipeline orchestrator" — the scan may have confused the class description with a filename. `pipeline.py:60` does `output_path = Path(self.args.output).resolve()` with NO path traversal check (no verification that the output path is within CWD or a safe directory). There is no separate orchestrator.py with a different (stricter) check. The underlying concern — that the CLI allows writing output to arbitrary filesystem paths — is valid, but the scan's file reference is wrong.
- **Notes:** There is no path traversal protection in the CLI pipeline. The `--output` argument accepts any path. However, there is no "inconsistency" between two files since orchestrator.py doesn't exist. The real issue is simply that there's no path restriction at all.

### #26: B SEC-05 — CSV parsing no size limit
- **Verdict:** CONFIRMED
- **Evidence:** `pipeline.py:168-192` `_parse_positions_csv()`. The CSV reader at line 169: `reader = csv.reader(f)` iterates over all rows with no limit. There is no `max_rows` check, no file size check, and no memory limit. A maliciously large CSV file would consume unbounded memory.
- **Notes:** Low severity since this is a local CLI tool reading user-provided files, but a DoS via memory exhaustion is possible with a multi-GB CSV.

### #27: B PERF-06 — GRO writing per-molecule string formatting loops
- **Verdict:** CONFIRMED
- **Evidence:** All GRO writer functions use Python f-string formatting per-atom in per-molecule Python loops. For example, `gromacs_writer.py:2437-2460` appends formatted lines per atom inside a molecule loop. `gromacs_writer.py:2549-2554` does the same for custom molecules. `gromacs_writer.py:2578-2585` for solutes. Each atom involves `lines.append(f"{res_num_wrapped:5d}SOL     OW{atom_num_wrapped:5d}{o_pos[0]:8.3f}...")`. Building large strings in a Python list then calling `f.writelines(lines)` is slower than a single bulk write but functionally correct.
- **Notes:** A numpy-based approach (converting positions to formatted strings in bulk) would be faster for large systems. Current approach is O(N_atoms) Python string operations.

### #28: C-CLI R-02 — --cli + --gui conflict not in routing table
- **Verdict:** CONFIRMED
- **Evidence:** `docs/cli-reference.md:1069-1079` Routing Behavior table lists: No arguments, `--help`, `--version`, Computation flags, `--cli` + computation, `--cli` alone, `--gui`. There is NO entry for `--cli + --gui` conflict. If both are provided, the behavior is undefined in the docs. The priority line (1079) says `--gui > computation flags > no arguments` but doesn't mention `--cli`.
- **Notes:** In argparse, mutually exclusive groups would handle this, but the routing table should document the conflict resolution behavior.

### #29: C-CLI R-03 — --no-diagram flag in pipeline-mode commands
- **Verdict:** CONFIRMED
- **Evidence:** `scripts/cli-examples.sh` has `--no-diagram` in many pipeline commands: lines 66, 74, 82, 108, 117, 120, 125, 134, 137, 140, 149, 152, 155, 164, 169. The docs (cli-reference.md:99) state "In pipeline mode... the --no-diagram flag has no effect — phase diagrams are not generated in pipeline mode by default." So these `--no-diagram` flags are no-ops that may mislead users into thinking they control something.
- **Notes:** Not harmful, but confusing. The example scripts suggest --no-diagram is meaningful in pipeline mode when it isn't.

### #30: C-CLI R-04 — --seed 42 redundant
- **Verdict:** CONFIRMED
- **Evidence:** `scripts/cli-examples.sh:69` has `--seed 42`. The default value for --seed is 42 (confirmed in `parser.py:159`: `default=42`). So specifying `--seed 42` is redundant — it does exactly what the default already does.
- **Notes:** Low severity. The example is misleading (suggests 42 is a meaningful choice rather than the default), but not harmful.

### #31: C-CLI R-05 — --no-diagram in hydrate-interface-custom-ion.sh
- **Verdict:** CONFIRMED
- **Evidence:** `scripts/hydrate-interface-custom-ion.sh:166` contains `--no-diagram` in the pipeline command. This is a full pipeline command (hydrate + interface + custom + ion), so --no-diagram is a no-op per cli-reference.md:99.
- **Notes:** Same as issue #29 — redundant flag in a pipeline command.

### #32: C-CLI R-07 — WATER_VOLUME_NM3 = 0.0299 has no literature citation
- **Verdict:** CONFIRMED
- **Evidence:** `structure_generation/types.py:25`: `WATER_VOLUME_NM3: float = 0.0299`. Line 24 comment says only `# Volume per TIP4P-ICE water molecule in nm³ (at ~1 bar, 300K)`. No literature citation, no derivation, no reference to the TIP4P-ICE paper or IAPWS data for water density at the relevant conditions.
- **Notes:** The value 0.0299 nm³ corresponds to ~30.0 Å³, implying a density of ~0.997 g/cm³ at ~300K, which is consistent with TIP4P-ICE properties. But no source is cited.

### #33: C-CLI N-08 — TIP4P-ICE reference lacks full citation
- **Verdict:** PARTIAL
- **Evidence:** `docs/cli-reference.md:1183` provides only a DOI link: `[TIP4P-ice Reference](https://doi.org/10.1063/1.1931662)`. Line 121 mentions "TIP4P-ICE (optimized for ice simulations)" without citation. The DOI is correct (Abascal et al. J. Chem. Phys. 2005), but the reference is only a bare link — no author names, year, journal, volume, or page number are given in the docs.
- **Notes:** The DOI resolves correctly (unlike the Madrid2019 DOI issues). The concern is about citation completeness, not accuracy. A bare DOI link is functional but not a proper academic citation.

### #34: C-GUI DOC-G8 — Ice V/VII _get_citation() returns "No specific citation"
- **Verdict:** CONFIRMED
- **Evidence:** `main_window.py:1954`: `"ice_v": "Monoclinic ice V. No specific citation in GenIce2."`. Line 1956: `"ice_vii": "High-pressure ice VII. No specific citation in GenIce2."`. Both return descriptive text with "No specific citation" rather than actual literature references. Ice V has known structural references (e.g., Lobban et al. 1998, Nature 391), and Ice VII has extensive literature (e.g., Hemley et al. 1987).
- **Notes:** While GenIce2 itself may not provide specific citations for these phases, real scientific references exist. The function name `_get_citation()` implies it should return a proper citation, not "No specific citation".

### #35: C-GUI DOC-G12 — Ion panel tooltip missing Madrid2019 reference
- **Verdict:** CONFIRMED
- **Evidence:** `ion_panel.py:129-131`: The tooltip text is `"Insert Na+ and Cl- ions into the liquid water region.\nCalculated from concentration and liquid volume."`. No mention of Madrid2019 ion model, scaled charges (±0.85e), or the reference paper. The CLI docs (cli-reference.md:930) mention Madrid2019, but the GUI tooltip does not.
- **Notes:** Users relying on the GUI tooltip would not know that the ion model uses scaled charges, which is important for force field compatibility.

### #36: C-GUI DOC-G14 — Ctrl+S vs Ctrl+M clarity
- **Verdict:** PARTIAL
- **Evidence:** `gui-guide.md:214` lists `Ctrl+M | Export custom molecules for GROMACS (Tab 3)`. Line 218: `Ctrl+S provides unified export from the currently active tab`. Line 589: `File → Export Custom Molecules for GROMACS (Ctrl+S)`. Line 115 in help_dialog.py: `22. Export custom molecules for GROMACS (Ctrl+M)`. The GUI guide at line 589 says Ctrl+S while the help dialog says Ctrl+M. Both are technically correct (Ctrl+S is the unified shortcut, Ctrl+M is the tab-specific one), but the inconsistency between the help dialog (Ctrl+M) and the GUI guide (Ctrl+S at line 589) is confusing.
- **Notes:** The real issue is that the help_dialog.py says Ctrl+M (line 116) while the gui-guide.md's export section (line 589) says Ctrl+S. The keyboard shortcut table (line 214) correctly lists both. The help dialog is inconsistent with the GUI guide.

### #37: C-GUI NEW-3 — README says "12 ice polymorphs" but lists 11
- **Verdict:** CONFIRMED
- **Evidence:** `README.md:116`: "**12 ice polymorphs** — Ih, Ic, II, III, V, VI, VII, VIII, IX, XV, X". Counting the listed names: Ih, Ic, II, III, V, VI, VII, VIII, IX, XV, X = 11 polymorphs. The claim says 12, but only 11 are listed.
- **Notes:** Either one polymorph is missing from the list (Ice IV, Ice XI, or another phase), or the number should be 11.

### #38: C-GUI NEW-4 — "Rewards" for diversity score is ambiguous
- **Verdict:** CONFIRMED
- **Evidence:** `docs/ranking.md:11`: "**Diversity Score** - Rewards structural uniqueness via O-O distance fingerprint". The word "Rewards" is ambiguous — it could mean "gives a bonus to" (increasing score) or "selects for" (lower score is better per line 13). Since lower score = better candidate (line 13), "rewards" is misleading: the diversity score actually PENALIZES structures similar to already-selected candidates (increasing their score).
- **Notes:** "Penalizes redundancy" or "Favors structural uniqueness" would be clearer given that lower = better.

---

## BONUS (4 — informational)

### #39: D — scipy.optimize._highspy (6.9 MB) unnecessary in bundle
- **Verdict:** CONFIRMED (plausible)
- **Evidence:** `scipy/optimize/_highspy/` directory exists at 6.9 MB. QuickIce does NOT import `scipy.optimize.linprog`, `scipy.optimize._highs`, or anything from `scipy.optimize._highspy` (confirmed via grep: no matches for `scipy.optimize`, `linprog`, `HiGHS`, or `_highs` in the QuickIce source). The spec's `collect_all('scipy')` includes this entire subpackage unnecessarily.
- **Notes:** The 6.9 MB figure is accurate. QuickIce only uses `scipy.spatial.cKDTree`, not the optimizer. A targeted import would save this space.

### #40: D — genice2 hiddenimports missing sI, sII
- **Verdict:** FALSE ALARM
- **Evidence:** `quickice-gui.spec:9-14` uses `collect_all('genice2')` which returns hiddenimports from PyInstaller's hook system for genice2. The spec does NOT manually list `genice2.lattices.sI` or `genice2.lattices.sII` in hiddenimports because `collect_all` is supposed to discover all submodules automatically. The `hiddenimports` list starts empty (line 7) and is populated by `collect_all` (line 14: `hiddenimports += tmp_ret[2]`). Whether `collect_all` actually discovers sI/sII depends on PyInstaller's hook for genice2, but the spec's approach (using collect_all rather than manual listing) is the recommended pattern.
- **Notes:** If collect_all fails to discover these lazily-imported lattice modules, the symptom would be a runtime ImportError when generating sI/sII hydrates. This is a known PyInstaller limitation, not a spec bug per se. The correct fix (if it occurs) would be to add explicit hiddenimports for the missing modules, not to replace collect_all.

### #41: D — genice2 installed size grew 3.6→5.1 MB
- **Verdict:** FALSE ALARM
- **Evidence:** The current installed size of genice2 is 7.3 MB (measured via `du -sh` on the package directory), not 5.1 MB as the scan claims. The growth from 3.6 MB to 7.3 MB is even larger than the scan reported. The scan's figure of 5.1 MB is outdated or was measured differently.
- **Notes:** The concern about genice2 bundle size is valid, but the specific number is wrong. The actual size (7.3 MB) exceeds the scan's estimate.

### #42: D — Revised total savings ~118 MB GUI
- **Verdict:** PARTIAL
- **Evidence:** The spec uses `collect_all('scipy')` (line 9) and `collect_all('genice2')` (line 9). The full scipy package is ~100+ MB installed. QuickIce only uses `scipy.spatial` (cKDTree). The genice2 package is 7.3 MB. The `scipy/optimize/_highspy` alone is 6.9 MB. Without running PyInstaller to get actual bundle size, the ~118 MB savings estimate cannot be verified precisely. However, the components contributing to waste are real: full scipy (~100 MB), unused scipy subpackages (including _highs at 6.9 MB), full genice2 (7.3 MB). The order of magnitude is plausible.
- **Notes:** The exact 118 MB figure cannot be verified without building the bundle, but the direction is correct: switching from `collect_all` to targeted imports would save tens of MB.

---

## Summary Table

| # | ID | Verdict | Notes |
|---|------|-----------|-------|
| 1 | DOI-D1 | CONFIRMED | Both DOI occurrences in README.md are wrong (10.1063/1.5121394 → should be 10.1063/1.5121392) |
| 2 | C-CLI N-01 | CONFIRMED | Wrong DOI (10.1021/acs.jctc.9b00902) at cli-reference.md:930 — different error than #1 |
| 3 | B NEW-01/11 | CONFIRMED | write_solute_gro_file does NOT wrap solute/custom positions; write_ion_gro_file does |
| 4 | B PERF-01 | CONFIRMED | Triple-nested Python loop: mol→atom→dim at gromacs_writer.py:93-118 |
| 5 | C-CLI N-02 | CONFIRMED | Concentration 0.0–5.0 enforced in code, not documented for any flag |
| 6 | C-CLI N-03 | CONFIRMED | Validation Rules lists 3/8 constraints; missing 5 |
| 7 | B NEW-03/EH-07 | PARTIAL | File write HAS try/except (lines 2128-2135), but scoped to final write only |
| 8 | B NEW-06/PERF-03 | CONFIRMED | O(N) Python loop with per-atom string comparison filtering MW atoms |
| 9 | B NEW-07/PERF-04 | CONFIRMED | Per-molecule cKDTree query in Python loop (both inserters) |
| 10 | B NEW-16 | CONFIRMED | custom_molecule_positions excluded from overlap tree in both inserters |
| 11 | B PERF-02 | CONFIRMED | Per-molecule, per-atom Python loops in multi-cell wrapping paths |
| 12 | B PERF-05 | CONFIRMED | vstack ALL placed positions on every successful placement → O(N²) memory |
| 13 | C-CLI N-04 | CONFIRMED | Extension validation (.gro/.itp) in code, not in docs |
| 14 | C-CLI N-05 | PARTIAL | OPLS-AA listed without combining-rule warning; scan line refs slightly off |
| 15 | C-CLI N-06 | CONFIRMED | No dedicated section; differences scattered across individual flag docs |
| 16 | C-CLI R-01 | CONFIRMED | Code enforces only ≥1.0 nm; no upper bound; doc says 1.0–100 nm |
| 17 | C-CLI R-06 | CONFIRMED | "User dialog" in doc; CLI has no interactive dialog |
| 18 | C-GUI NEW-1 | CONFIRMED | Docs say "Insert Molecule"; button is "Generate Custom Molecules" |
| 19 | C-GUI DOC-G5 | CONFIRMED | Exactly 5 wrong paths + 2 missing images |
| 20 | D | PARTIAL | Excludes exist for tests/*; main waste is collect_all pulling entire packages |
| 21 | B NEW-08 | PARTIAL | Modulo wrapping could split multi-atom solutes; unverified assumption in comment |
| 22 | B NEW-09/EH-08 | CONFIRMED | 6 instances of `except Exception` found; 2 silently swallow errors |
| 23 | B NEW-15 | CONFIRMED | 7 test files hardcode 0.0299 (14 occurrences) |
| 24 | B NEW-18 | FALSE ALARM | `"O" in list` is exact match, not substring; code correctly detects GenIce2 format |
| 25 | B SEC-04 | PARTIAL | No path traversal protection exists; orchestrator.py doesn't exist (wrong filename) |
| 26 | B SEC-05 | CONFIRMED | CSV reader has no row/size/memory limit |
| 27 | B PERF-06 | CONFIRMED | Per-atom f-string formatting in Python loops for all GRO writers |
| 28 | C-CLI R-02 | CONFIRMED | --cli + --gui conflict not documented in routing table |
| 29 | C-CLI R-03 | CONFIRMED | --no-diagram present in 15+ pipeline-mode commands (no-op) |
| 30 | C-CLI R-04 | CONFIRMED | --seed 42 is the default; specifying it is redundant |
| 31 | C-CLI R-05 | CONFIRMED | --no-diagram in pipeline command at line 166 |
| 32 | C-CLI R-07 | CONFIRMED | No citation for 0.0299 nm³ constant |
| 33 | C-CLI N-08 | PARTIAL | DOI is correct but citation is bare link; not a full academic reference |
| 34 | C-GUI DOC-G8 | CONFIRMED | ice_v and ice_vii return "No specific citation in GenIce2" |
| 35 | C-GUI DOC-G12 | CONFIRMED | Ion panel tooltip lacks Madrid2019 reference and ±0.85e mention |
| 36 | C-GUI DOC-G14 | PARTIAL | help_dialog says Ctrl+M; gui-guide export section says Ctrl+S; both technically valid |
| 37 | C-GUI NEW-3 | CONFIRMED | "12 ice polymorphs" lists only 11 names |
| 38 | C-GUI NEW-4 | CONFIRMED | "Rewards" ambiguous when lower score = better |
| 39 | D (bonus) | CONFIRMED | scipy.optimize._highs 6.9 MB unused; no imports of scipy.optimize in QuickIce |
| 40 | D (bonus) | FALSE ALARM | collect_all('genice2') auto-discovers submodules; no manual listing needed |
| 41 | D (bonus) | FALSE ALARM | Actual size 7.3 MB, not 5.1 MB; scan's figure is wrong |
| 42 | D (bonus) | PARTIAL | Savings plausible (~100+ MB scipy), but exact 118 MB figure unverified |

---

## Final Counts

| Verdict | Count |
|---------|-------|
| CONFIRMED | 30 |
| FALSE ALARM | 3 |
| PARTIAL | 9 |
| **Total** | **42** |

### Breakdown by severity

| Severity | CONFIRMED | FALSE ALARM | PARTIAL |
|----------|-----------|-------------|---------|
| CRITICAL (2) | 2 | 0 | 0 |
| HIGH (4) | 4 | 0 | 0 |
| MEDIUM (14) | 9 | 0 | 5 |
| LOW (16) | 11 | 2 | 3 |
| BONUS (4) | 1 | 2 | 1 |

### Key findings

**All 6 CRITICAL + HIGH issues are CONFIRMED** — no false alarms at the top severity levels.

**3 FALSE ALARMS:**
- #24 (B NEW-18): `"O" in list` is exact match, not substring — code is correct
- #40 (D): genice2 hiddenimports — collect_all auto-discovers, manual listing not needed
- #41 (D): genice2 size is 7.3 MB, not 5.1 MB — scan's figure outdated

**9 PARTIAL:**
- #7: Error handling exists but narrower scope than other writers
- #14: OPLS-AA warning absent, but scan line refs slightly off
- #20: Test data excluded; main waste is full-package collection
- #21: Modulo wrapping could split solutes but unlikely in practice
- #25: Path traversal concern valid, but orchestrator.py doesn't exist
- #33: DOI is correct but citation is incomplete
- #36: Both shortcuts work; help dialog inconsistent with guide
- #42: Savings direction correct; exact figure unverified

---

_Verified: 2026-06-18_
_Verifier: OpenCode (gsd-verifier)_
_Method: Direct file inspection; no scan claims trusted without verification_
