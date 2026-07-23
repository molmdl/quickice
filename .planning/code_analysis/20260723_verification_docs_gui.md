# Verification of GUI Documentation-vs-Code Issues (GUI-01..GUI-12)

**Date:** 2026-07-23
**Mode:** READ-ONLY verification, no fixes applied. Nothing was modified or committed.
**Verifier method:** For each issue, read the cited DOC file at the cited line AND the cited CODE file at the cited line, compared verbatim. Independent of prior `.planning/code_analysis/` reports (only the issue-list source `20260723_documentation_crosscheck_gui.md` was read for the 12 claims).

**Source of claims:** `/share/home/nglokwan/quickice/.planning/code_analysis/20260723_documentation_crosscheck_gui.md`

---

## Verdict Summary Table

| ID | Claimed severity | Verdict | Doc location | Code location | One-line reality |
|----|------------------|---------|--------------|---------------|------------------|
| GUI-01 | High | **TRUE** | `docs/gui-guide.md:88,90` | `quickice/gui/validators.py:106-107`; `quickice/gui/view.py:100,110` | Guide says 4–100,000; GUI (validator + in-app text) enforces 4–216. 100,000 is the CLI limit. |
| GUI-02 | Med | **TRUE** | `docs/gui-guide.md:675-677` | `quickice/gui/export.py:307-309,386,394` | Guide says `interface_with_custom.*`/`custom_molecule.itp`; code emits `custom_system_{moltype}_{N}molecules.gro/.top` + user's original ITP + `tip4p-ice.itp`. Stale strings absent from code. |
| GUI-03 | Med | **TRUE** | `docs/gui-guide.md:879-881` | `quickice/gui/export.py:464-467,489,533,540` | Guide says `interface_with_ions.*`; code emits `ions_{N}na_{N}cl[.gro/.top]` + `ion.itp` + `tip4p-ice.itp`. Stale strings absent from code. |
| GUI-04 | Med | **TRUE** | `README.md:16,26,116,253,255,257-270` | `quickice/phase_mapping/lookup.py:27-46`; `docs/gui-guide.md:103` | README prose says "11" in 4 places but heading + table + `PHASE_METADATA` say/list 12 (incl. Ice XI). README internally inconsistent. (Report's line refs 117/254 are off-by-1; actual 116/253.) |
| GUI-05 | Med | **TRUE** | `docs/gui-guide.md:7-14` | `quickice/gui/main_window.py:299-304` | Overview bullets name only Tabs 2/3/4, omit Tab 1 (Hydrate) and Tab 5 (Ion). Main Window Layout (49-55) is correct. |
| GUI-06 | Med | **TRUE** | `docs/gui-guide.md:205` | `quickice/gui/main_window.py:425-491` | No top-level "Export for GROMACS" item bound to Ctrl+G. Ctrl+G = "Export Ice..." under "Export As..." submenu; unified export is "Export Current Tab for GROMACS..." (Ctrl+S). |
| GUI-07 | Low | **TRUE** | `docs/gui-guide.md:392` | `quickice/gui/interface_panel.py:253-254,258` | Cited `:258` is tooltip text; dropdown defined at 253 (`QComboBox()`) + 254 (`addItems`). Minor line drift. |
| GUI-08 | Low | **TRUE** | `README.md:211`; `docs/gui-guide.md:677` | `quickice/gui/export.py:386` | `custom.itp`/`custom_molecule.itp` are stale; code preserves user's original ITP filename. (Overlaps GUI-02's gui-guide citation.) |
| GUI-09 | Low | **TRUE** | `docs/gui-guide.md:20-22` | `quickice/entry.py:168-178`; `README.md:78-84` | Guide documents only `python -m quickice.gui`; `--gui` route exists in `entry.py` and is documented in README. Completeness gap (not a contradiction). |
| GUI-10 | Low | **TRUE** | `quickice/gui/ion_panel.py:185-186` | `docs/gui-guide.md:872`; `README.md:382-383` | In-app ion tooltip gives journal ref but no DOI; external docs include `10.1063/1.5121392`. External docs are correct; in-app text is less complete. |
| GUI-11 | Low | **TRUE** | `quickice/gui/help_dialog.py:306-326` | `README.md` References | Help dialog "More Information & Notes" lists TIP4P-ICE/IAPWS/GenIce2 by name/URL but no DOIs; does not mention Madrid2019 or spglib. External README carries full DOIs. |
| GUI-12 | Low | **TRUE** | `README.md:313-322` | `environment.yml:55`; `quickice/output/validator.py:11` | Dependencies table omits `spglib` (8 pkgs listed); it is a direct dep (`spglib==2.7.0`, `import spglib`) and IS cited in README References (360-363). |

**Verdict counts:** TRUE: 12 / FALSE ALARM: 0 / PARTIALLY TRUE: 0

---

## Detailed Findings Per Issue

### GUI-01 — Molecule count range: docs say 100,000, GUI enforces 216 [High] → TRUE

**Claim:** `docs/gui-guide.md:87,90` says range 4–100,000 but GUI enforces 4–216.

**Actual doc text (`docs/gui-guide.md:86-90`):**
```
### Molecule Count

- Range: 4-100,000 molecules
- Purpose: Controls simulation cell size
- Validation: Must be integer, error shown if > 100,000
```

**Actual code:**
- `quickice/gui/validators.py:106-107`:
  ```python
  if nmol < 4 or nmol > 216:
      return (False, "Molecule count must be between 4 and 216")
  ```
- `quickice/gui/validators.py:6` docstring: `"Molecule count max is 216 (GUI limit) instead of 100000 (CLI limit)"`.
- In-app placeholder `quickice/gui/view.py:100`: `"Min count (4-216, actual may be higher)"`.
- In-app tooltip `quickice/gui/view.py:110`: `"Minimum number of water molecules (4-216). Actual count may be higher due to crystal symmetry. ..."`.

**Verdict + rationale:** TRUE. The external gui-guide documents the **CLI** limit (100,000) under the GUI "Molecule Count" section. The validator enforces 4–216 and the in-app text correctly says 4–216. A user following the guide would expect to enter up to 100,000 and be surprised by rejection above 216. In-app text is correct; only the external guide is wrong.

**Suggested action:** Doc-fix needed. Change range to `4-216 molecules` and validation line to `error shown if > 216` (note 100,000 is the CLI limit).

---

### GUI-02 — Custom-molecule export filenames are stale [Med] → TRUE

**Claim:** `docs/gui-guide.md:674-677` lists `interface_with_custom.*` / `custom_molecule.itp`; code emits `custom_system_*.gro` + user's original ITP.

**Actual doc text (`docs/gui-guide.md:674-677`):**
```
Exported files:
- `interface_with_custom.gro` — Coordinates with custom molecules
- `interface_with_custom.top` — Topology with custom moleculetype
- `custom_molecule.itp` — Your provided .itp file (bundled to output)
```

**Actual code (`quickice/gui/export.py`):**
- `export.py:307-309`:
  ```python
  default_name = _build_default_path(
      self.parent,
      f"custom_system_{moleculetype_name}_{n_molecules}molecules.gro",
  )
  ```
- `export.py:331`: `top_path = path.with_name(path.stem + '.top')` → companion `.top` is `custom_system_{moltype}_{N}molecules.top`.
- `export.py:386`: `custom_itp_dest = path.with_name(custom_structure.itp_path.name)` → user's **original** ITP filename (atomtypes commented out).
- `export.py:394`: `water_itp_dest = path.with_name("tip4p-ice.itp")` → also emitted, not listed in doc.
- Grep for `interface_with_custom` across `quickice/`: **No files found** (string absent from codebase).

**Verdict + rationale:** TRUE. The doc's three filenames are all wrong/stale: `.gro`/`.top` base is `custom_system_{moltype}_{N}molecules`, the ITP keeps the user's original name (not `custom_molecule.itp`), and `tip4p-ice.itp` is additionally emitted but unlisted.

**Suggested action:** Doc-fix needed. Update to `custom_system_{moleculetype}_{N}molecules.gro/.top`, `<user_itp_filename>.itp`, `tip4p-ice.itp`.

---

### GUI-03 — Ion export filenames are stale [Med] → TRUE

**Claim:** `docs/gui-guide.md:878-881` lists `interface_with_ions.*`; code emits `ions_{N}na_{N}cl*.gro`.

**Actual doc text (`docs/gui-guide.md:878-881`):**
```
Exported files:
- `interface_with_ions.gro` — Coordinates with ions
- `interface_with_ions.top` — Topology with Na⁺/Cl⁻
- `ion.itp` — Madrid2019 ion parameters
```

**Actual code (`quickice/gui/export.py`):**
- `export.py:464-467`:
  ```python
  if ion_structure.solute_n_molecules > 0:
      bare_name = f"ions_{na_count}na_{cl_count}cl_with_{ion_structure.solute_n_molecules}{ion_structure.solute_type.lower()}.gro"
  else:
      bare_name = f"ions_{na_count}na_{cl_count}cl.gro"
  ```
- `export.py:489`: `top_path = path.with_name(path.stem + '.top')` → `ions_{N}na_{N}cl*.top`.
- `export.py:533`: `ion_itp_path = path.with_name('ion.itp')` → matches doc.
- `export.py:540`: `water_itp_path = path.with_name("tip4p-ice.itp")` → also emitted, not listed in doc.
- Grep for `interface_with_ions` across `quickice/`: **No files found** (string absent from codebase).

**Verdict + rationale:** TRUE. The `.gro`/`.top` base names are stale (`ions_{N}na_{N}cl[...]` not `interface_with_ions`); `ion.itp` is correct; `tip4p-ice.itp` is additionally emitted but unlisted.

**Suggested action:** Doc-fix needed. Update to `ions_{N}na_{N}cl.gro/.top` (or `..._with_{N}{solute}.gro`), keep `ion.itp`, add `tip4p-ice.itp`.

---

### GUI-04 — README "11 ice polymorphs" contradicts the 12-phase GUI diagram/data [Med] → TRUE

**Claim:** README says "11 ice polymorphs" but `PHASE_METADATA`/diagram has 12 (incl. Ice XI); README table also lists 12.

**Actual doc text (`README.md`):**
- Line 16: `- **Ice Generation** — 11 ice polymorphs from thermodynamic conditions`
- Line 26: `- Interactive phase diagram with 11 ice polymorphs`
- Line 116: `- **11 ice polymorphs** — Ih, Ic, II, III, V, VI, VII, VIII, IX, XV, X` (11 names; **Ice XI omitted**)
- Line 253: `### Phase Detection (12 phases)` (heading says 12)
- Line 255: `The interactive phase diagram can identify 11 ice polymorphs based on temperature and pressure conditions:`
- Lines 257-270: table with **12 rows** including Ice XI at line 268 (`| Ice XI | Ordered Ih | Low pressure | < 72K |`).

**Actual code:**
- `quickice/phase_mapping/lookup.py:27-46` `PHASE_METADATA` has **12 keys**: `ice_ih` (28), `ice_ic` (33), `ice_ii` (34), `ice_iii` (35), `ice_v` (36), `ice_vi` (37), `ice_vii` (38), `ice_viii` (39), `ice_xi` (41), `ice_ix` (42), `ice_xv` (43), `ice_x` (45).
- `quickice/gui/phase_diagram_widget.py:45,327` docstrings reference "all 12 phases".
- `docs/gui-guide.md:103` (correct): `"QuickIce can generate structures for 8 ice polymorphs (Ih, Ic, II, III, V, VI, VII, VIII); the diagram also shows regions for Ice IX, X, XI, XV, liquid water, and vapor"` (8 generatable + 4 detection-only = 12).

**Verdict + rationale:** TRUE. The README is internally inconsistent: prose (lines 16, 26, 116, 255) says "11" while the heading (253) and table (257-270) say/list 12; `PHASE_METADATA` has 12 (incl. `ice_xi`). The gui-guide is correct. Note: the report's cited lines 117 and 254 are off-by-1 (actual 116 and 253), and it omitted line 26 which also says 11 — minor citation drift, substance fully correct.

**Suggested action:** Doc-fix needed. Reconcile README to 12 consistently and add Ice XI to the line-116 list (already in the table at line 268).

---

### GUI-05 — gui-guide Overview omits Tab 1 (Hydrate) and Tab 5 (Ion) [Med] → TRUE

**Claim:** `docs/gui-guide.md:7-14` Overview lists only Tabs 2/3/4, omitting Tab 1 and Tab 5.

**Actual doc text (`docs/gui-guide.md:7-14`):**
```
The QuickIce GUI provides an intuitive visual interface for:
- Interactive phase diagram selection
- Real-time 3D molecular structure visualization
- Side-by-side candidate comparison
- Multiple export formats (PDB, PNG, SVG)
- Interface Construction for ice-water systems (Tab 2)
- Custom molecule upload and insertion (Tab 3)
- Solute molecule insertion (Tab 4)
```

**Actual code (`quickice/gui/main_window.py:299-304`):** six tabs added:
```python
self.tab_widget.addTab(tab1_widget, "Ice Generation")            # Tab 0
self.tab_widget.addTab(self.hydrate_panel, "Hydrate Generation") # Tab 1
self.tab_widget.addTab(self.interface_panel, "Interface Construction")  # Tab 2
self.tab_widget.addTab(self.custom_molecule_panel, "Custom Molecule")   # Tab 3
self.tab_widget.addTab(self.solute_panel, "Solute Insertion")          # Tab 4
self.tab_widget.addTab(self.ion_panel, "Ion Insertion")                # Tab 5
```

**Verdict + rationale:** TRUE. The Overview bullets name Tabs 2, 3, 4 but omit Tab 1 (Hydrate Generation) and Tab 5 (Ion Insertion). The "Main Window Layout" section immediately below (lines 49-55) correctly lists all six tabs, so only the Overview intro is stale/incomplete.

**Suggested action:** Doc-fix needed. Add bullets for Tab 1 (Hydrate Generation) and Tab 5 (Ion Insertion).

---

### GUI-06 — "Export for GROMACS" menu path does not exist [Med] → TRUE

**Claim:** `docs/gui-guide.md:205` says `File → Export for GROMACS (Ctrl+G)`; no such item exists.

**Actual doc text (`docs/gui-guide.md:205`):**
```
**Menu Path:** File → Export for GROMACS (Ctrl+G)
```

**Actual code (`quickice/gui/main_window.py:425-491`):**
- `main_window.py:429`: `export_current_action = file_menu.addAction("Export Current Tab for GROMACS...")`
- `main_window.py:430`: `export_current_action.setShortcut("Ctrl+S")` (unified export = Ctrl+S)
- `main_window.py:461`: `export_as_menu = file_menu.addMenu("Export As...")` (submenu)
- `main_window.py:464`: `export_ice_action = export_as_menu.addAction("Export Ice...")`
- `main_window.py:465`: `export_ice_action.setShortcut("Ctrl+G")` (Ctrl+G is Ice-specific, under Export As)

**Verdict + rationale:** TRUE. There is no top-level menu item "Export for GROMACS" bound to Ctrl+G. The unified export is `File → Export Current Tab for GROMACS... (Ctrl+S)`; `Ctrl+G` is `File → Export As → Export Ice...`. (The guide's own Keyboard Shortcuts table at lines 232-237 is correct: `Ctrl+G | Export ice for GROMACS (Tab 0)`.)

**Suggested action:** Doc-fix needed. Replace the menu path with `File → Export Current Tab for GROMACS... (Ctrl+S)` (unified) or `File → Export As → Export Ice... (Ctrl+G)` (Ice-specific).

---

### GUI-07 — interface_panel line reference points into tooltip text [Low] → TRUE

**Claim:** `docs/gui-guide.md:392` cites `interface_panel.py:258`, but the dropdown is defined at 253-254; 258 is tooltip text.

**Actual doc text (`docs/gui-guide.md:391-392`):**
```
The **Source** dropdown at the top of Tab 2 picks which structure to build the
interface from (defined in `quickice/gui/interface_panel.py:258`):
```

**Actual code (`quickice/gui/interface_panel.py`):**
- Line 253: `self.source_combo = QComboBox()`
- Line 254: `self.source_combo.addItems(["Ice Candidate", "Hydrate Structure"])`
- Lines 255-259: `self.source_combo.setToolTip(...)`; line 258 is the tooltip string `"• Hydrate Structure — Generate hydrate directly in Tab 1"`.

**Verdict + rationale:** TRUE. The dropdown is *defined* at lines 253-254; cited line 258 falls inside the `setToolTip(...)` string literal. Minor line-number drift, low impact (the doc's prose + table at 394-397 correctly describe the two source options).

**Suggested action:** Doc-fix needed (cosmetic). Update reference to `interface_panel.py:253-254`.

---

### GUI-08 — "custom.itp" / "custom_molecule.itp" filename is not what the code emits [Low] → TRUE

**Claim:** `README.md:211` says `custom.itp`; `docs/gui-guide.md:677` says `custom_molecule.itp`; code preserves user's original ITP filename.

**Actual doc text:**
- `README.md:211`: `| Tab 3 | Custom Molecule GROMACS | .gro, .top, tip4p-ice.itp, custom.itp |`
- `docs/gui-guide.md:677`: `- \`custom_molecule.itp\` — Your provided .itp file (bundled to output)`

**Actual code (`quickice/gui/export.py:386`):**
```python
custom_itp_dest = path.with_name(custom_structure.itp_path.name)
custom_itp_dest.write_text(modified_content)
```
- Grep for `custom_molecule.itp` and `custom.itp` across `quickice/`: **No files found** (neither fixed name is ever written).

**Verdict + rationale:** TRUE. The output ITP keeps the user's **original** ITP filename (with `[ atomtypes ]` commented out via `comment_out_atomtypes_in_itp`). Neither `custom.itp` nor `custom_molecule.itp` is ever emitted. Note: this overlaps GUI-02 (which cites the same gui-guide line 677 for the broader stale-filename issue); GUI-08 adds the README `custom.itp` citation.

**Suggested action:** Doc-fix needed. Replace `custom.itp` (README:211) and `custom_molecule.itp` (gui-guide:677) with `<user_itp_filename>.itp`.

---

### GUI-09 — gui-guide launch section omits `python -m quickice --gui` [Low] → TRUE

**Claim:** `docs/gui-guide.md:20-22` only documents `python -m quickice.gui`, omitting `python -m quickice --gui`.

**Actual doc text (`docs/gui-guide.md:20-22`):**
```
```bash
python -m quickice.gui
```
```
(Only the direct-GUI invocation is shown.)

**Actual code / other docs:**
- `quickice/entry.py:168-178` handles `--gui` explicitly: checks `_is_pyside6_available()` and `_has_display()`, then calls `run_app()`.
- `README.md:78`: `python -m quickice --gui` (documented as the primary launch).
- `README.md:83`: `python -m quickice.gui` (documented as "direct GUI access, bypasses router").

**Verdict + rationale:** TRUE. The guide omits the unified `--gui` route that the README documents. This is a completeness gap, not a contradiction (the report itself frames it as "Not a contradiction, but the gui-guide is less complete than the README").

**Suggested action:** Doc-fix needed (completeness). Add `python -m quickice --gui` as the unified-entry alternative, noting it requires PySide6 + a display.

---

### GUI-10 — Ion tooltip cites Madrid2019 paper but omits the DOI [Low] → TRUE

**Claim:** `quickice/gui/ion_panel.py:185-186` tooltip gives journal ref but no DOI; external docs include `10.1063/1.5121392`.

**Actual in-app text (`quickice/gui/ion_panel.py:185-186`):**
```python
"Ion model: Madrid2019 (Na⁺/Cl⁻ charges ±0.85e).\n"
"Ref: Zeron et al., J. Chem. Phys. 151, 134504 (2019)."
```

**Actual external docs (correct, include DOI):**
- `docs/gui-guide.md:872`: `... Madrid2019 force field parameters used (Na⁺ charge = +0.85, Cl⁻ charge = -0.85) — Zeron, Abascal, & Vega, J. Chem. Phys. 151, 134504 (2019), DOI: https://doi.org/10.1063/1.5121392`
- `README.md:382-383`: `... Journal of Chemical Physics, 151, 134504.` + `- DOI: https://doi.org/10.1063/1.5121392`

**Verdict + rationale:** TRUE. The in-app ion tooltip cites the paper by journal reference but omits the DOI, while both external docs include it. The external docs are correct; this is an in-app text completeness gap (not a doc error in the external guide). Under the report's broad scope (in-app UI text counted as "docs checked"), this is a TRUE finding.

**Suggested action:** Needs confirmation / in-app text enhancement. Append `DOI: 10.1063/1.5121392` to the ion-panel tooltip at `ion_panel.py:186`. (Not an external-doc fix — the external docs already carry the DOI.)

---

### GUI-11 — Help dialog "More Information & Notes" lacks DOIs / key citations [Low] → TRUE

**Claim:** `quickice/gui/help_dialog.py:306-326` lacks DOIs for TIP4P-ICE, Madrid2019, spglib, GenIce2.

**Actual in-app text (`quickice/gui/help_dialog.py:306-326`):**
```python
refs_label = QLabel(
    "• Click phase regions in diagram to see scientific references\n"
    "• GenIce2 repository: https://github.com/genice-dev/GenIce2\n"   # repo URL, no paper DOI
    "• IAPWS (water standards): https://www.iapws.org"                # URL, no DOI
)
...
notes_label = QLabel(
    "• Actual molecule count may differ from requested to satisfy\n"
    "  crystal structure symmetry constraints\n"
    "• GROMACS export generates .gro, .top, and .itp files\n"
    "• TIP4P-ICE water model used for GROMACS compatibility\n"        # no DOI
    "• GROMACS export uses candidate selected in left viewport dropdown\n"
    "• Interface GROMACS export uses same TIP4P-ICE model for both ice and water\n"
    "• Ice Ih density uses IAPWS R10-06(2009) for temperature-dependent accuracy\n"  # no URL/DOI
    "• Water density for interfaces uses IAPWS-95 formulation"       # no URL/DOI
)
```
- The dialog does **not** mention Madrid2019 or spglib at all.

**Actual external docs (correct, carry full citations):**
- `README.md` References (333-388) carries DOIs for GenIce2 (336), IAPWS R14-08/R10-06/IAPWS-95 (338-348), spglib (360-363), Madrid2019 (381-383), GAFF/GAFF2 (374-376).
- `quickice/output/_constants.py` comments cite TIP4P-ICE `Abascal et al. 2005, DOI: 10.1063/1.1931662`.

**Verdict + rationale:** TRUE. The help dialog names TIP4P-ICE, IAPWS R10-06, IAPWS-95, GenIce2 by name/URL but without DOIs, and omits Madrid2019 and spglib entirely. The external README carries the full DOIs. This is an in-app text completeness gap; the external docs are correct.

**Suggested action:** Needs confirmation / in-app text enhancement. Add DOIs/short citations (TIP4P-ICE, Madrid2019, spglib, GenIce2 paper) to the help dialog "More Information & Notes" page.

---

### GUI-12 — README Dependencies table omits spglib [Low] → TRUE

**Claim:** `README.md:313-322` Dependencies table omits spglib, which is a direct dependency imported in `output/validator.py`.

**Actual doc text (`README.md:313-322`):**
```
| Package | Purpose |
|---------|---------|
| `iapws` | IAPWS-95 validated water/ice properties |
| `numpy` | Numerical operations |
| `scipy` | Scientific computing |
| `vtk` | 3D molecular visualization |
| `PySide6` | GUI framework |
| `genice2` | Ice structure generation |
| `genice-core` | GenIce core algorithms |
| `pytest` | Testing framework |
```
(8 packages; no spglib row.)

**Actual code / env:**
- `environment.yml:55`: `- spglib==2.7.0` (pip section).
- `quickice/output/validator.py:11`: `import spglib`; docstring (4): `"Space group detection using spglib"`.
- `README.md:360-363` References **does** cite spglib with DOI + repo — so spglib is documented as a reference but missing from the Dependencies table.

**Verdict + rationale:** TRUE. spglib is a direct dependency (declared in environment.yml, imported and used in core structure validation) but is absent from the README Dependencies table. It is, however, cited in the References section, so it is not entirely undocumented — only missing from the deps table. (Note: the table is selective — it also omits matplotlib, networkx, shapely, etc. — but spglib is arguably "main" given its role in space-group validation of generated/exported structures.)

**Suggested action:** Doc-fix needed. Add a `spglib` row to the Dependencies table (Purpose: "Crystal symmetry detection / structure validation").

---

## Confirmed Doc-Fixes Needed (with suggested priority)

| Priority | ID | Fix |
|----------|----|-----|
| **P0** | GUI-01 | gui-guide "Molecule Count": change range to `4-216` and validation to `> 216` (100,000 is CLI limit). Actively misleading — users are rejected above 216. |
| **P1** | GUI-06 | gui-guide:205 menu path → `File → Export Current Tab for GROMACS... (Ctrl+S)` or `File → Export As → Export Ice... (Ctrl+G)`. |
| **P1** | GUI-02 | gui-guide:675-677 custom export filenames → `custom_system_{moltype}_{N}molecules.gro/.top`, `<user_itp>.itp`, `tip4p-ice.itp`. |
| **P1** | GUI-03 | gui-guide:879-881 ion export filenames → `ions_{N}na_{N}cl.gro/.top` (or `..._with_{N}{solute}.gro`), keep `ion.itp`, add `tip4p-ice.itp`. |
| **P1** | GUI-04 | README: reconcile "11"→"12" at lines 16, 26, 116, 255 and add Ice XI to the line-116 list (already in table at 268). |
| **P1** | GUI-05 | gui-guide Overview (7-14): add bullets for Tab 1 (Hydrate Generation) and Tab 5 (Ion Insertion). |
| **P2** | GUI-08 | README:211 `custom.itp` → `<user_itp_name>.itp`; (gui-guide:677 covered by GUI-02). |
| **P2** | GUI-07 | gui-guide:392 line ref → `interface_panel.py:253-254`. Cosmetic. |
| **P2** | GUI-09 | gui-guide:20-22: add `python -m quickice --gui` (unified entry). Completeness. |
| **P2** | GUI-12 | README:313-322 Dependencies: add `spglib` row. |
| **P2** | GUI-10 | In-app: append `DOI: 10.1063/1.5121392` to `ion_panel.py:186` tooltip. (External docs already correct.) |
| **P2** | GUI-11 | In-app: add DOIs/citations (TIP4P-ICE, Madrid2019, spglib, GenIce2) to `help_dialog.py:306-326`. (External docs already correct.) |

**Notes on priority:**
- **P0** = actively misleading in a user-facing way (validation rejection contrary to documented range).
- **P1** = wrong/stale external-doc facts (filenames, menu path, counts, tab list) that would confuse users looking for files/menu items that don't exist.
- **P2** = cosmetic line drift, completeness gaps, or in-app text enhancements where the external docs are already correct.

---

## False Alarms

None. All 12 claims verified as TRUE.

---

## Notes & Caveats

- **Line-number drift (does not affect any verdict):**
  - GUI-04: report cites `README.md:117` (actual 116) and `:254` (actual 253). Substance correct. The report also omitted line 26 (`Interactive phase diagram with 11 ice polymorphs`), which is a fourth "11" occurrence.
  - GUI-07: the cited `:258` is a real line in the file but points into tooltip text, not the dropdown definition (253-254) — this is the substance of the issue, not drift.
- **Overlaps (not double-counting errors):** GUI-08's gui-guide citation (line 677) is the same line as GUI-02's. Both are valid; GUI-02 covers the broader stale-filename set, GUI-08 covers the ITP-name specifically and adds the README `custom.itp` citation.
- **In-app vs external-doc framing (GUI-10, GUI-11):** These are in-app text *completeness* gaps, not external-doc errors — the external docs (gui-guide.md, README.md) are correct and complete. The report's scope explicitly includes "In-app UI text" under "Docs checked", so under that scope these are TRUE. If the scope were strictly "external docs vs code", these two would be in-app enhancement requests rather than doc fixes.
- **Acceptable code patterns verified NOT to be issues (per AGENTS.md / task bias rules):** duck-typed `InterfaceStructure` attributes (CP-01), `HydrateWorker`/`IonInsertionWorker` `QThread` subclassing, and broad `except Exception` in GUI code — none of the 12 issues frame these as bugs, so no false-alarm adjudication was needed for them.
- **Secondary claims verified by grep:** `interface_with_custom`, `interface_with_ions`, `custom_molecule.itp`, `custom.itp` each return **No files found** across `quickice/` source — confirming the report's "appears nowhere in the codebase" claims for GUI-02/03/08.

---

*End of READ-ONLY verification — 2026-07-23. No files were modified or committed.*
