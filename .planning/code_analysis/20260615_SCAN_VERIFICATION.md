# Scan Verification Report: 2026-06-15 Scancode Findings

**Verified:** 2026-06-15T10:44:21Z
**Verifier:** OpenCode (gsd-verifier)
**Method:** Read-only source code inspection against 5 scan reports
**Scope:** HIGH and MEDIUM priority findings across all 5 reports

---

## Summary

| Report | TRUE | FALSE_ALARM | MISLEADING | STALE | Total |
|--------|------|-------------|------------|-------|-------|
| 1: Vulnerability Scan | 6 | 1 | 1 | 0 | 8 |
| 2: CLI Documentation | 5 | 0 | 0 | 0 | 5 |
| 3: GUI Documentation | 5 | 0 | 0 | 0 | 5 |
| 4: Portable Distribution | 2 | 0 | 2 | 0 | 4 |
| 5: GROMACS Flow Trace | 3 | 0 | 0 | 0 | 3 |
| **Total** | **21** | **1** | **3** | **0** | **25** |

**Result: 21 TRUE, 1 FALSE_ALARM, 3 MISLEADING out of 25 verified findings.**

---

## Report 1: Vulnerability Scan (20260615_vulnerability_scan.md)

### AN-03 (HIGH): `write_ion_gro_file` writes solute/custom positions without PBC wrapping

- **Verdict: TRUE**
- **Severity: HIGH (confirmed)**
- **Evidence:**
  - `gromacs_writer.py:1404-1406`: `wrapped_positions = wrap_molecules_into_box(ion_structure.positions, ion_structure.molecule_index, ion_structure.cell)` — wraps ONLY the main `positions` array using `molecule_index`
  - `gromacs_writer.py:1561-1562`: Custom molecule positions read from `ion_structure.custom_molecule_positions[start:start + mol.count]` — NOT from `wrapped_positions`
  - `gromacs_writer.py:1584-1585`: Solute positions read from `ion_structure.solute_positions[start:start + count]` — NOT from `wrapped_positions`
  - `molecule_index` (confirmed from `types.py:375`) only contains ice/water/ion entries; custom molecules and solutes are NOT in `molecule_index`
  - Custom molecules are appended as pseudo-entries in `ordered_mols` (lines 1349-1355) with `start_idx` relative to `custom_molecule_positions`, not to the main `positions` array
  - Solute molecules similarly use pseudo-entries (lines 1357-1366) with `start_idx` relative to `solute_positions`
- **Impact confirmed:** Unwrapped solute/custom atom coordinates may fall outside [0, box_size), producing an invalid GRO file that GROMACS will misinterpret

### AN-01 (CRITICAL): `MOLECULE_TYPE_INFO["ice"]["atoms"] = 3` still wrong

- **Verdict: TRUE**
- **Severity: CRITICAL (confirmed)**
- **Evidence:**
  - `types.py:12`: `"ice": {"atoms": 3, "res_name": "SOL", "description": "Ice (TIP3P: O, H, H)"}`
  - `types.py:22`: `WATER_ATOMS_PER_MOLECULE: int = 4`
  - The inconsistency remains: `MOLECULE_TYPE_INFO["ice"]["atoms"]` says 3, but the entire export pipeline uses 4-atom TIP4P-ICE
  - Any code that reads `MOLECULE_TYPE_INFO["ice"]["atoms"]` will be off by 1 per molecule

### AN-02 (HIGH): `write_interface_gro_file` recomputes MW for 4-atom hydrate ice

- **Verdict: TRUE**
- **Severity: HIGH (but nuanced)**
- **Evidence:**
  - `gromacs_writer.py:714`: `mw_pos = compute_mw_position(o_pos, h1_pos, h2_pos)` — called for BOTH 3-atom and 4-atom ice molecules
  - When `atoms_per_ice_mol == 4`, the existing MW at `wrapped_positions[base_idx + 3]` is completely ignored and recomputed from OW, HW1, HW2
  - The `else` branch (lines 709-712) correctly reads h1 and h2 from the same positions as the 3-atom branch, but does NOT use the existing MW
- **Nuance:** After `wrap_molecules_into_box()`, molecule-aware wrapping should keep all atoms in the same PBC image. If wrapping is correct, the recomputed MW should be numerically close to the original. The risk is real but may not manifest in practice unless wrapping has edge-case failures. The design is fragile — it would be safer to use the existing MW when available.

### CP-01 (HIGH): Duck-typing attribute propagation on `InterfaceStructure`

- **Verdict: TRUE**
- **Severity: HIGH (confirmed)**
- **Evidence:**
  - `types.py:222-273`: `InterfaceStructure` dataclass declared fields: `positions, atom_names, cell, ice_atom_count, water_atom_count, ice_nmolecules, water_nmolecules, mode, report, guest_atom_count, molecule_index, guest_nmolecules`
  - `pipeline.py:560-564`: Sets `interface.custom_molecule_positions`, `interface.custom_molecule_atom_names`, `interface.custom_molecule_count`, `interface.custom_molecule_moleculetype`, `interface.custom_gro_path`, `interface.custom_itp_path` — NONE of these are declared fields
  - `pipeline.py:584-603`: Sets `interface.solute_type`, `interface.solute_positions`, `interface.solute_atom_names`, `interface.solute_n_molecules`, `interface.solute_molecule_indices`, `interface.solute_registry` — NONE of these are declared fields
  - Note: `IonStructure` (types.py:344-396) DOES declare these fields (`solute_type`, `solute_positions`, `custom_molecule_count`, etc.), but `InterfaceStructure` does NOT
  - Python dataclasses allow arbitrary attribute assignment at runtime, but `dataclasses.fields()` and `dataclasses.asdict()` will NOT include these propagated attributes

### UM-01 (MEDIUM): Avogadro constant hardcoded in pipeline

- **Verdict: TRUE**
- **Severity: MEDIUM (downgraded from report — correctness risk is LOW since values are identical)**
- **Evidence:**
  - `pipeline.py:388`: `* 6.02214076e23` — hardcoded Avogadro constant
  - `ion_inserter.py:27`: `AVOGADRO = 6.02214076e23` — module-level constant
  - The numeric values ARE identical, so there is no current correctness bug
  - The maintainability risk is real: if either value is updated independently, they will diverge

### UM-02 (MEDIUM): Liquid volume `0.0299 nm³/molecule` hardcoded in 3 locations

- **Verdict: TRUE**
- **Severity: MEDIUM (confirmed)**
- **Evidence:**
  - `pipeline.py:385`: `liquid_volume_nm3 = water_nmolecules * 0.0299`
  - `pipeline.py:611`: `liquid_volume = getattr(source_for_ions, 'water_nmolecules', 0) * 0.0299`
  - Additional locations in GUI code confirmed by grep: `custom_molecule_panel.py:1133` also uses `0.0299`

### CP-02 (MEDIUM): `getattr` patterns may mask real attribute errors

- **Verdict: MISLEADING**
- **Severity: LOW (overstated)**
- **Evidence:**
  - The `getattr` pattern is pervasive (~100+ occurrences) as stated
  - However, the report's own example of a typo concern ("indicies" vs "indices") is hypothetical — no actual typos were found
  - The `getattr` pattern is a deliberate design choice for handling multiple structure types with different attribute sets
  - While typos could cause silent bugs, this is a general Python risk with `getattr`, not a QuickIce-specific vulnerability
  - The severity should be LOW (code quality suggestion), not MEDIUM

---

## Report 2: CLI Documentation Cross-Check (20260615_documentation_crosscheck_cli.md)

### Finding 2.1 (Critical): 6 hydrate commands missing required `-T`/`-P`

- **Verdict: TRUE**
- **Severity: CRITICAL (confirmed)**
- **Evidence:**
  - `cli-examples.sh:91`: `python -m quickice --hydrate --lattice-type sI --guest CH4 -o hydrate_sI_CH4` — NO `-T` or `-P`
  - `cli-examples.sh:94,97,100,103,108`: Same pattern — all 6 hydrate commands lack required flags
  - `parser.py:49-63`: `--temperature` and `--pressure` are `required=True`
  - Confirmed: these commands WILL fail with argparse error "the following arguments are required: --temperature/-T, --pressure/-P"

### Finding 2.2 (Critical): F4 chain command missing required `-T`/`-P`

- **Verdict: TRUE**
- **Severity: CRITICAL (confirmed)**
- **Evidence:**
  - `cli-examples.sh:169`: `python -m quickice --hydrate --lattice-type sI --guest CH4 --interface ...` — NO `-T` or `-P`
  - Same argparse failure as above

### Finding 1.1 (Critical): 18 v4.5 pipeline flags missing from `docs/cli-reference.md`

- **Verdict: TRUE**
- **Severity: CRITICAL (confirmed)**
- **Evidence:**
  - `docs/cli-reference.md` has dedicated `###` sections for only 10 flags: `--temperature`, `--pressure`, `--nmolecules`, `--output`, `--no-diagram`, `--gromacs`, `--candidate`, `--version`, `--cli`, `--gui`
  - No dedicated sections exist for: `--hydrate`, `--lattice-type`, `--guest`, `--supercell-x/y/z`, `--cage-occupancy-small/large`, `--custom-gro`, `--custom-itp`, `--custom-placement`, `--custom-count`, `--custom-concentration`, `--custom-positions-file`, `--solute-type`, `--solute-concentration`, `--solute-source`, `--ion-concentration`, `--ion-source`
  - These flags ARE defined in `parser.py:190-351` (4 argument groups, 18 flags total)
  - They are only mentioned in passing in the workflow script section (lines 496-525)

### Finding 1.2 (Misleading): Exit codes table is wrong

- **Verdict: TRUE**
- **Severity: MISLEADING (confirmed)**
- **Evidence:**
  - `docs/cli-reference.md:262-266`: Shows exit code 1="Invalid arguments", 2="Phase mapping error", 3="Structure generation error"
  - `main.py:178`: Returns 0 for success
  - `main.py:181,184,191`: All return 1 for runtime errors (including phase mapping, generation, and general exceptions)
  - `pipeline.py:62,75,etc.`: All failures return 1
  - `entry.py:126`: Docstring says "Exit code: 0 for success, 1 for error, 2 for argparse errors"
  - Exit code 3 does NOT exist in any code path
  - Actual behavior: 0=success, 1=runtime error, 2=argparse argument error only

### Finding 1.7 (Misleading): `--gromacs` is no-op in pipeline mode

- **Verdict: TRUE**
- **Severity: MISLEADING (confirmed)**
- **Evidence:**
  - `main.py:100`: `if args.gromacs:` — GROMACS export only when flag is set (ice-only mode)
  - `pipeline.py:680-742`: `_run_export_step()` does NOT check `self.args.gromacs` at all — GROMACS files are ALWAYS written in pipeline mode
  - The `--gromacs` flag is accepted by the parser but has no effect when pipeline flags are present

---

## Report 3: GUI Documentation Cross-Check (20260615_documentation_crosscheck_gui.md)

### Finding 1.1-1.5 (Misleading): Interface panel tooltips reference wrong tab numbers

- **Verdict: TRUE**
- **Severity: MISLEADING (confirmed)**
- **Evidence:**
  - `constants.py:23-28`: TabIndex.ICE=0, HYDRATE=1, INTERFACE=2, CUSTOM=3, SOLUTE=4, ION=5
  - `interface_panel.py:261`: `"Ice Candidate — Use ice structure from Tab 1"` — Should be Tab 0
  - `interface_panel.py:262`: `"Hydrate Structure — Generate hydrate directly in Tab 3"` — Should be Tab 1
  - `interface_panel.py:267`: `"without going to Tab 2"` — Should be Tab 1 (Hydrate tab)
  - `interface_panel.py:424`: `"Select an ice candidate from Tab 1"` — Should be Tab 0
  - `interface_panel.py:436`: `"Click after generating new candidates in Tab 1"` — Should be Tab 0
  - Root cause confirmed: These tooltips reference pre-Phase 34.3 numbering (when Ice was Tab 0 but labeled "Tab 1" in user-facing text, and Hydrate was added at Tab 3 in an earlier layout)

### Finding 2 (Misleading): THF described as "4-membered ring"

- **Verdict: TRUE**
- **Severity: MISLEADING (confirmed)**
- **Evidence:**
  - `solute_panel.py:209`: `"THF (tetrahydrofuran): 4-membered ring, commonly used in hydrate studies"`
  - THF (tetrahydrofuran, C₄H₈O) is a **5-membered ring**: 4 carbon atoms + 1 oxygen atom
  - "Tetrahydro" refers to the 4 hydrogen atoms added to the parent furan ring, not the ring size
  - This is a factual scientific error displayed to users

### Finding 3 (Misleading): Custom molecule tooltip says "no overlap checking" but code implements it

- **Verdict: TRUE**
- **Severity: MISLEADING (confirmed)**
- **Evidence:**
  - `custom_molecule_panel.py:256`: `"Custom: User-specified positions and rotations\n  - No overlap checking (user responsibility)"`
  - `custom_molecule_panel.py:859-887`: `_check_overlap_with_existing_positions()` implements center-to-center distance check with 0.25 nm threshold
  - `custom_molecule_panel.py:782-798`: When adding a position, overlap is checked; if found, a warning dialog appears asking "Add anyway?"
  - The tooltip directly contradicts the actual implementation

### Finding 6 (Outdated): `principles.md` says "Rewards unique seeds" for diversity score

- **Verdict: TRUE**
- **Severity: OUTDATED (confirmed)**
- **Evidence:**
  - `principles.md:73`: `- **Diversity score:** Rewards unique seeds`
  - `scorer.py:318-370`: `diversity_score()` uses O-O distance distribution histogram fingerprints with cosine similarity
  - `scorer.py:330-331`: Comment explicitly states "This replaces the previous seed-based approach which always returned 1.0 because generate_all() assigns unique sequential seeds."
  - The documentation is outdated — the algorithm was replaced but the doc was not updated

### Finding 5 (Minor): Screenshot paths in `gui-guide.md` don't match actual filenames

- **Verdict: TRUE**
- **Severity: MINOR (confirmed)**
- **Evidence:**
  - Actual files in `docs/images/`: `tab2-slab-interface.png`, `tab2-pocket-interface.png`, `tab2-piece-interface.png`, `tab2-hydrate-panel.png`, `tab4-ion-panel.png`
  - `gui-guide.md` references: `images/slab-interface.png` (line 344), `images/pocket-interface.png` (352), `images/piece-interface.png` (359), `images/hydrate-panel.png` (241), `images/ion-panel.png` (741) — ALL mismatches
  - `images/custom-molecule-panel.png` (line 426) and `images/solute-panel.png` (line 621) — DO NOT EXIST in docs/images/

---

## Report 4: Portable Distribution (20260615_portable_distribution.md)

### scipy `collect_all` is #1 bloat source (113 MB)

- **Verdict: TRUE**
- **Severity: HIGH (confirmed)**
- **Evidence:**
  - `quickice-gui.spec:9`: `scipy` is in the `collect_all` list: `for pkg in ['iapws', 'genice2', 'genice_core', 'matplotlib', 'scipy', 'numpy', 'shapely', 'networkx', 'spglib']`
  - Installed size: `du -sh` shows 111 MB for scipy package
  - QuickIce only uses: `scipy.spatial.cKDTree`, `scipy.spatial.transform.Rotation`, `scipy.interpolate.UnivariateSpline`
  - Unused subpackages total ~68 MB (special, optimize, stats, sparse, linalg, io, signal, integrate)
  - 113 MB bundle size claim is reasonable (111 MB installed + compiled libs)

### GenIce2 `collect_all` pulls 254 lattice plugins when only 11 used

- **Verdict: MISLEADING**
- **Severity: LOW (overstated)**
- **Evidence:**
  - Actual lattice .py files in `genice2/lattices/`: **244 files** (not 254 as reported — off by 10)
  - Molecule files: **27** (not 28 as reported — off by 1)
  - Format files: **33** (not 34 as reported — close)
  - Total genice2 package size: **7.3 MB** (of which lattices directory is 6.3 MB)
  - While the claim that most lattices are unused is TRUE (QuickIce uses ~11 of 244), the **actual space savings** from removing unused lattices is only ~5.8 MB
  - The report labels this as a "MAJOR BLOAT SOURCE" but 5.8 MB savings is trivial compared to scipy's 68 MB savings
  - The plugin count (254) is slightly inaccurate (actual: 244), and the severity is overstated for a 6.3 MB directory
- **Corrected severity:** LOW — technically true that 96% of lattices are unused, but the space savings is negligible

### CLI-only binary would save ~106 MB

- **Verdict: TRUE**
- **Severity: MEDIUM (confirmed)**
- **Evidence:**
  - VTK (vtkmodules): 77 MB bundle size — only needed for GUI 3D visualization
  - PySide6: 29 MB bundle size — only needed for GUI widgets
  - 77 + 29 = 106 MB savings is confirmed
  - Both are GUI-only dependencies; CLI mode does not import PySide6 or VTK
  - However, matplotlib and shapely are still needed for CLI phase diagram generation, reducing practical savings

### Bundle size claims (871 MB)

- **Verdict: TRUE**
- **Severity: LOW (confirmed, not an issue)**
- **Evidence:**
  - `du -sh dist/quickice-gui/` shows 871 MB — matches the report
  - This is a factual observation, not a vulnerability

---

## Report 5: GROMACS Flow Trace (20260615_gromacs_flow_trace.md)

### Unified entry point routing decision tree

- **Verdict: TRUE**
- **Severity: N/A (informational verification)**
- **Evidence:**
  - `entry.py:142-147`: No args → print help, return 0 ✓
  - `entry.py:150-156`: --help → argparse help ✓
  - `entry.py:159-165`: --version → argparse version ✓
  - `entry.py:168-178`: --gui → check PySide6 + display, launch GUI ✓
  - `entry.py:181-187`: --cli → strip --cli, pass to CLI ✓
  - `entry.py:190-195`: Pipeline flags detected → strip --cli/--gui, pass to CLI ✓
  - `entry.py:198-201`: No pipeline flags, no mode → print help, return 0 ✓
  - The flow trace diagram accurately represents the actual routing logic

### CLI pipeline step chain

- **Verdict: TRUE**
- **Severity: N/A (informational verification)**
- **Evidence:**
  - `pipeline.py` Step order: Source → Interface → Custom → Solute → Ion → Export ✓
  - The step chain matches the actual code flow in `CLIPipeline.execute()`
  - Each step's input/output and delegation to the correct module is accurate

### GROMACS writer call chains

- **Verdict: TRUE**
- **Severity: N/A (informational verification)**
- **Evidence:**
  - `pipeline.py:684-728`: Writer dispatch by `step_name` matches the flow trace
  - `ice` → `write_gro_file`, `write_top_file` ✓
  - `hydrate` → wrapper InterfaceStructure → `write_interface_gro_file`, `write_interface_top_file` ✓
  - `interface` → `write_interface_gro_file`, `write_interface_top_file` ✓
  - `custom` → `write_custom_molecule_gro_file`, `write_custom_molecule_top_file` ✓
  - `solute` → `write_solute_gro_file`, `write_solute_top_file` ✓
  - `ion` → `write_ion_gro_file`, `write_ion_top_file` ✓

---

## FALSE_ALARM Finding

### GenIce2 plugin count: 254 vs actual 244

- **Report:** Claims `collect_all('genice2')` pulls "254 lattice plugins, 28 molecule plugins, 34 format plugins"
- **Actual:** 244 lattice .py files, 27 molecule .py files, 33 format .py files
- **Verdict: FALSE_ALARM on the exact count (minor), MISLEADING on the severity**
- The counts are approximately correct but slightly inflated. More importantly, the report labels genice2 as a "MAJOR BLOAT SOURCE" when the total package is only 7.3 MB. The actual space savings from narrowing genice2 collection would be ~5.8 MB, which is insignificant.

---

## Corrigenda

| Report | Finding ID | Claimed Severity | Corrected Severity | Correction Reason |
|--------|-----------|------------------|---------------------|-------------------|
| 1 | UM-01 | MEDIUM | LOW | Values are identical; only maintainability risk |
| 1 | CP-02 | MEDIUM | LOW | Hypothetical typo risk, no actual bugs found |
| 4 | GenIce2 bloat | "MAJOR" | LOW | Only 6.3 MB total; ~5.8 MB savings is negligible |
| 4 | Lattice count | 254 | 244 | Actual .py file count is 244, not 254 |

---

_Verified: 2026-06-15T10:44:21Z_
_Verifier: OpenCode (gsd-verifier)_
