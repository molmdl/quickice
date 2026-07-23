# Documentation vs. Code Crosscheck — GUI Focus

**Date:** 2026-07-23
**Scope:** QuickIce GUI path (dual-path CLI+GUI tool)
**Mode:** READ-ONLY, bias-free. This report was produced by comparing actual documentation to actual GUI code only. No prior scancode/verification results were consulted; no files in `.planning/code_analysis/` or `.planning/codebase/` were read during this analysis. Nothing was modified.

**Docs checked (GUI-relevant):**
- `README.md`
- `docs/gui-guide.md`
- `docs/principles.md`, `docs/flowchart.md`, `docs/cli-reference.md`, `docs/gro-itp-guide.md`
- `AGENTS.md`
- `.planning/ROADMAP.md`, `.planning/PROJECT.md`
- In-app UI text: `quickice/gui/help_dialog.py`, tooltips in `quickice/gui/*.py`
- Launch scripts: `scripts/run_gui_ssh.sh`, `scripts/run_oc.sh`
- Screenshots referenced in `docs/gui-guide.md` (verified present in `docs/images/`)

**Code checked (GUI-relevant):**
- `quickice/entry.py`, `quickice/__main__.py`, `quickice.py`, `quickice/gui/__main__.py`, `quickice/gui/__init__.py`
- `quickice/gui/main_window.py` (tab construction, shortcuts, workers, `_current_*_result`, `run_app`, `_configure_opengl_for_remote`)
- `quickice/gui/constants.py` (TabIndex), `quickice/gui/validators.py`, `quickice/gui/view.py`
- `quickice/gui/export.py`, `quickice/gui/hydrate_export.py` (export filenames/ITPs)
- `quickice/gui/{hydrate,interface,custom_molecule,solute,ion}_panel.py` (source dropdowns, tooltips)
- `quickice/gui/hydrate_worker.py`, `quickice/gui/workers.py` (threading patterns)
- `quickice/gui/help_dialog.py` (in-app help/citations)
- `quickice/phase_mapping/lookup.py` (PHASE_METADATA), `quickice/output/validator.py` (spglib), `quickice/output/_constants.py` (TIP4P-ICE), `quickice/output/_shared.py` (comb-rule)

---

## Summary Table

| ID | Severity | Type | Doc location | Code location | One-line description |
|----|----------|------|--------------|---------------|----------------------|
| GUI-01 | High | ui-text / data-flow | `docs/gui-guide.md:87,90` | `quickice/gui/validators.py:106-107`; `quickice/gui/view.py:100,110` | gui-guide says molecule range 4–100,000; GUI actually enforces 4–216 |
| GUI-02 | Med | stale-feature | `docs/gui-guide.md:674-677` | `quickice/gui/export.py:307-309,386,394` | Custom-molecule export filenames `interface_with_custom.*` / `custom_molecule.itp` are stale; code emits `custom_system_*.gro` + user's original ITP name |
| GUI-03 | Med | stale-feature | `docs/gui-guide.md:878-881` | `quickice/gui/export.py:465-467,533,540` | Ion export filenames `interface_with_ions.*` are stale; code emits `ions_{N}na_{N}cl*.gro` |
| GUI-04 | Med | ui-text / stale | `README.md:16,117,255` | `quickice/phase_mapping/lookup.py:27-45`; `docs/gui-guide.md:103` | README says "11 ice polymorphs" but GUI diagram/PHASE_METADATA has 12 (incl. Ice XI); README table also lists 12 |
| GUI-05 | Med | stale-feature | `docs/gui-guide.md:7-14` | `quickice/gui/main_window.py:299-304` | gui-guide Overview lists only Tabs 2/3/4, omitting Tab 1 (Hydrate) and Tab 5 (Ion) |
| GUI-06 | Med | ui-text | `docs/gui-guide.md:205` | `quickice/gui/main_window.py:425-491` | "Menu Path: File → Export for GROMACS (Ctrl+G)" — no such menu item exists; Ctrl+G is under File → Export As → Export Ice... |
| GUI-07 | Low | ui-text | `docs/gui-guide.md:392` | `quickice/gui/interface_panel.py:253-254` | Line ref `interface_panel.py:258` points into tooltip text; source dropdown is defined at lines 253–254 |
| GUI-08 | Low | stale-feature | `README.md:211`; `docs/gui-guide.md:677` | `quickice/gui/export.py:386` | "custom.itp" / "custom_molecule.itp" — code preserves the user's original ITP filename, not a fixed name |
| GUI-09 | Low | launch | `docs/gui-guide.md:20-22` | `quickice/entry.py:168-178`; `README.md:78-84` | gui-guide launch omits `python -m quickice --gui`; only documents `python -m quickice.gui` |
| GUI-10 | Low | missing-citation | `quickice/gui/ion_panel.py:185-186` | `docs/gui-guide.md:872`; `README.md:382-383` | Ion tooltip cites Madrid2019 paper but omits DOI 10.1063/1.5121392 |
| GUI-11 | Low | missing-citation | `quickice/gui/help_dialog.py:306-326` | `README.md` References | Help dialog "More Information & Notes" lacks DOIs for TIP4P-ICE, Madrid2019, spglib, GenIce2 paper |
| GUI-12 | Low | stale-feature | `README.md:313-322` | `environment.yml:55`; `quickice/output/validator.py:11` | README Dependencies table omits spglib, which is a direct dependency (imported in output/validator.py) |

---

## Detailed Findings

### GUI-01 — Molecule count range: docs say 100,000, GUI enforces 216 [High]

**Doc text (`docs/gui-guide.md:86-90`):**
```
### Molecule Count
- Range: 4-100,000 molecules
- Purpose: Controls simulation cell size
- Validation: Must be integer, error shown if > 100,000
```

**Code reality:**
- `quickice/gui/validators.py:106-107`:
  ```python
  if nmol < 4 or nmol > 216:
      return (False, "Molecule count must be between 4 and 216")
  ```
- `quickice/gui/view.py:17` imports `validate_nmolecules` and wires it at `view.py:144`.
- `quickice/gui/view.py:100` placeholder: `"Min count (4-216, actual may be higher)"`.
- `quickice/gui/view.py:110` tooltip: `"Minimum number of water molecules (4-216). Actual count may be higher due to crystal symmetry. ..."`
- `quickice/gui/validators.py:6` docstring explicitly states: `"Molecule count max is 216 (GUI limit) instead of 100000 (CLI limit)"`.
- The 100,000 value is the **CLI** limit; the GUI limit is 216.

**In-app text is correct (4–216); the gui-guide documents the CLI limit instead of the GUI limit.** A user following the guide would expect to enter up to 100,000 and be surprised by rejection above 216.

**Recommended doc change (not applied):** In `docs/gui-guide.md` change the Molecule Count range to `4-216 molecules` and the validation line to `error shown if > 216`, noting that 100,000 is the CLI limit. Cross-reference `quickice/gui/validators.py`.

---

### GUI-02 — Custom-molecule export filenames are stale [Med]

**Doc text (`docs/gui-guide.md:674-677`):**
```
Exported files:
- `interface_with_custom.gro` — Coordinates with custom molecules
- `interface_with_custom.top` — Topology with custom moleculetype
- `custom_molecule.itp` — Your provided .itp file (bundled to output)
```

**Code reality (`quickice/gui/export.py`):**
- `export.py:307-309` default .gro name:
  ```python
  default_name = _build_default_path(
      self.parent,
      f"custom_system_{moleculetype_name}_{n_molecules}molecules.gro",
  )
  ```
- `export.py:331` companion `.top` is `path.with_name(path.stem + '.top')` (i.e. `custom_system_<moltype>_<N>molecules.top`).
- `export.py:386` the custom ITP is copied under the **user's original filename**, not a fixed name:
  ```python
  custom_itp_dest = path.with_name(custom_structure.itp_path.name)
  custom_itp_dest.write_text(modified_content)
  ```
- `export.py:394` also copies `tip4p-ice.itp` (not mentioned in the gui-guide's Custom export list):
  ```python
  water_itp_dest = path.with_name("tip4p-ice.itp")
  shutil.copy(water_itp_source, water_itp_dest)
  ```
- The strings `interface_with_custom` and `custom_molecule.itp` appear **nowhere** in the codebase (confirmed by grep).

**Recommended doc change (not applied):** Update `docs/gui-guide.md:674-677` to:
- `custom_system_{moleculetype}_{N}molecules.gro`
- `custom_system_{moleculetype}_{N}molecules.top`
- `<user_itp_filename>.itp` (user's original ITP, `[ atomtypes ]` commented out)
- `tip4p-ice.itp` (water topology, copied)

---

### GUI-03 — Ion export filenames are stale [Med]

**Doc text (`docs/gui-guide.md:878-881`):**
```
Exported files:
- `interface_with_ions.gro` — Coordinates with ions
- `interface_with_ions.top` — Topology with Na⁺/Cl⁻
- `ion.itp` — Madrid2019 ion parameters
```

**Code reality (`quickice/gui/export.py`):**
- `export.py:465-467` default .gro name:
  ```python
  if ion_structure.solute_n_molecules > 0:
      bare_name = f"ions_{na_count}na_{cl_count}cl_with_{ion_structure.solute_n_molecules}{ion_structure.solute_type.lower()}.gro"
  else:
      bare_name = f"ions_{na_count}na_{cl_count}cl.gro"
  ```
- `export.py:489` companion `.top` is `path.with_name(path.stem + '.top')` (i.e. `ions_<N>na_<N>cl*.top`).
- `export.py:533` `ion.itp` is correct: `ion_itp_path = path.with_name('ion.itp')`.
- `export.py:540` also copies `tip4p-ice.itp` (not listed in the gui-guide's Ion export list): `water_itp_path = path.with_name("tip4p-ice.itp")`.
- The string `interface_with_ions` appears **nowhere** in the codebase (confirmed by grep). Only `ion.itp` matches the doc.

**Recommended doc change (not applied):** Update `docs/gui-guide.md:878-881` to:
- `ions_{N}na_{N}cl.gro` (or `ions_{N}na_{N}cl_with_{N}{solute}.gro` when solutes are present)
- `ions_{N}na_{N}cl*.top`
- `ion.itp` (Madrid2019 ion parameters) — keep
- `tip4p-ice.itp` (water topology, copied) — add

---

### GUI-04 — README "11 ice polymorphs" contradicts the 12-phase GUI diagram [Med]

**Doc text:**
- `README.md:16`: `- **Ice Generation** — 11 ice polymorphs from thermodynamic conditions`
- `README.md:116-117`: `- **11 ice polymorphs** — Ih, Ic, II, III, V, VI, VII, VIII, IX, XV, X` (11 listed; **Ice XI omitted**)
- `README.md:254`: `### Phase Detection (12 phases)`
- `README.md:255`: `The interactive phase diagram can identify 11 ice polymorphs`
- `README.md:257-270` table lists **12 rows** (Ih, Ic, II, III, V, VI, VII, VIII, IX, **XI**, XV, X) — Ice XI appears at `README.md:268`.

**Code reality:**
- `quickice/phase_mapping/lookup.py:27-45` `PHASE_METADATA` has **12 keys**: `ice_ih`, `ice_ic`, `ice_ii`, `ice_iii`, `ice_v`, `ice_vi`, `ice_vii`, `ice_viii`, `ice_xi` (`lookup.py:41`), `ice_ix` (`lookup.py:42`), `ice_xv` (`lookup.py:43`), `ice_x` (`lookup.py:45`).
- The GUI phase diagram (`quickice/gui/phase_diagram_widget.py`) is driven by these phases.
- `docs/gui-guide.md:103` is **correct**: `"QuickIce can generate structures for 8 ice polymorphs (Ih, Ic, II, III, V, VI, VII, VIII); the diagram also shows regions for Ice IX, X, XI, XV, liquid water, and vapor"` (8 + 4 = 12).

**Inconsistency:** README prose says 11 (and its own list at line 117 omits Ice XI), but the GUI diagram and `PHASE_METADATA` have 12, and README's own table lists 12. The gui-guide is accurate; the README is internally inconsistent and contradicts the GUI diagram.

**Recommended doc change (not applied):** In `README.md` make the count consistently 12 and add Ice XI to the line-117 list (it is already in the table at line 268). Align line 16, 117, and 255 with the 12-phase `PHASE_METADATA`.

---

### GUI-05 — gui-guide Overview omits Tab 1 (Hydrate) and Tab 5 (Ion) [Med]

**Doc text (`docs/gui-guide.md:7-14`):**
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

**Code reality (`quickice/gui/main_window.py:299-304`):** Six tabs are added:
- Tab 0 `"Ice Generation"`, Tab 1 `"Hydrate Generation"`, Tab 2 `"Interface Construction"`, Tab 3 `"Custom Molecule"`, Tab 4 `"Solute Insertion"`, Tab 5 `"Ion Insertion"`.
- `quickice/gui/constants.py:9-27` `TabIndex` confirms HYDRATE=1, ION=5.

The Overview bulleted list names Tabs 2, 3, 4 but **omits Tab 1 (Hydrate Generation) and Tab 5 (Ion Insertion)**. The "Main Window Layout" section immediately below (`docs/gui-guide.md:49-55`) correctly lists all six tabs, so only the Overview intro is incomplete/stale.

**Recommended doc change (not applied):** Add bullets for Tab 1 (Hydrate Generation) and Tab 5 (Ion Insertion) to the `docs/gui-guide.md` Overview list.

---

### GUI-06 — "Export for GROMACS" menu path does not exist [Med]

**Doc text (`docs/gui-guide.md:200-205`):**
```
### Export for GROMACS
...
**Menu Path:** File → Export for GROMACS (Ctrl+G)
```

**Code reality (`quickice/gui/main_window.py:416-491`):** The File menu contains:
- `main_window.py:429` `"Export Current Tab for GROMACS..."` with shortcut `Ctrl+S` (`main_window.py:430`).
- `main_window.py:435` `"Save PDB (Left Viewer)..."` `Ctrl+Alt+P`.
- `main_window.py:440` `"Save PDB (Right Viewer)..."` `Ctrl+Shift+S`.
- `main_window.py:448` `"Save Diagram..."` `Ctrl+D`.
- `main_window.py:453` `"Save Viewport..."` `Ctrl+Alt+S`.
- `main_window.py:461` an `"Export As..."` **submenu** containing `main_window.py:464` `"Export Ice..."` (`Ctrl+G`, `main_window.py:465`), `"Export Hydrate..."` (`Ctrl+H`), `"Export Interface..."` (`Ctrl+I`), `"Export Solute..."` (`Ctrl+L`), `"Export Custom Molecule..."` (`Ctrl+M`), `"Export Ion..."` (`Ctrl+J`).

There is **no** top-level menu item named "Export for GROMACS" bound to `Ctrl+G`. The unified export is `Ctrl+S` ("Export Current Tab for GROMACS..."); `Ctrl+G` is the Ice-specific entry under the "Export As..." submenu.

**Recommended doc change (not applied):** Replace the menu path with either:
- `File → Export Current Tab for GROMACS... (Ctrl+S)` (the unified path), or
- `File → Export As → Export Ice... (Ctrl+G)` (the Ice-specific path).

---

### GUI-07 — interface_panel line reference points into tooltip text [Low]

**Doc text (`docs/gui-guide.md:392`):**
```
The **Source** dropdown at the top of Tab 2 picks which structure to build the
interface from (defined in `quickice/gui/interface_panel.py:258`):
```

**Code reality (`quickice/gui/interface_panel.py`):**
- `interface_panel.py:253` `self.source_combo = QComboBox()`
- `interface_panel.py:254` `self.source_combo.addItems(["Ice Candidate", "Hydrate Structure"])`
- `interface_panel.py:255-259` is the `setToolTip(...)` call; line 258 is the tooltip string `"• Hydrate Structure — Generate hydrate directly in Tab 1"`.

The dropdown is *defined* at lines 253–254; line 258 is inside the tooltip text. Minor line-number drift.

**Recommended doc change (not applied):** Update the reference to `quickice/gui/interface_panel.py:253-254` (or `:254` for the `addItems` line).

---

### GUI-08 — "custom.itp" / "custom_molecule.itp" filename is not what the code emits [Low]

**Doc text:**
- `README.md:211`: `| Tab 3 | Custom Molecule GROMACS | .gro, .top, tip4p-ice.itp, custom.itp |`
- `docs/gui-guide.md:677`: `- \`custom_molecule.itp\` — Your provided .itp file (bundled to output)`

**Code reality (`quickice/gui/export.py:386`):**
```python
custom_itp_dest = path.with_name(custom_structure.itp_path.name)
```
The output ITP keeps the **user's original ITP filename** (with `[ atomtypes ]` commented out via `comment_out_atomtypes_in_itp`, `export.py:383-387`). Neither a fixed `custom.itp` nor `custom_molecule.itp` is ever written.

**Recommended doc change (not applied):** In `README.md:211` replace `custom.itp` with `<user_itp_name>.itp`; in `docs/gui-guide.md:677` replace `custom_molecule.itp` with `<user_itp_filename>.itp`.

---

### GUI-09 — gui-guide launch section omits `python -m quickice --gui` [Low]

**Doc text (`docs/gui-guide.md:20-22`):**
```
### Launching the GUI

```bash
python -m quickice.gui
```
```

**Code reality:**
- `quickice/entry.py:168-178` handles `--gui` explicitly: checks `_is_pyside6_available()` (`entry.py:26-39`, using `importlib.util.find_spec('PySide6')`) and `_has_display()` (`entry.py:42-69`), then calls `run_app()`.
- `quickice/gui/__main__.py:6-9` supports `python -m quickice.gui` directly (bypasses the router).
- `README.md:78-84` documents both `python -m quickice --gui` and `python -m quickice.gui`.

Not a contradiction, but the gui-guide is less complete than the README.

**Recommended doc change (not applied):** Add `python -m quickice --gui` to `docs/gui-guide.md` as the unified-entry alternative, noting it requires PySide6 + a display (per `entry.py`).

---

### GUI-10 — Ion tooltip cites Madrid2019 paper but omits the DOI [Low]

**Doc/text location (`quickice/gui/ion_panel.py:185-186`):**
```python
"Ion model: Madrid2019 (Na⁺/Cl⁻ charges ±0.85e).\n"
"Ref: Zeron et al., J. Chem. Phys. 151, 134504 (2019)."
```

**Code/docs reality:**
- `docs/gui-guide.md:872` and `README.md:382-383` include the DOI: `https://doi.org/10.1063/1.5121392`.
- The in-app tooltip gives the journal reference but not the DOI.

**Recommended change (not applied):** Append `DOI: 10.1063/1.5121392` to the ion-panel HelpIcon text at `quickice/gui/ion_panel.py:186` so the in-app citation matches `docs/gui-guide.md` and `README.md`.

---

### GUI-11 — Help dialog "More Information & Notes" lacks DOIs / key citations [Low]

**Doc/text location (`quickice/gui/help_dialog.py:306-326`):**
- `help_dialog.py:321` `"• TIP4P-ICE water model used for GROMACS compatibility"` (no DOI).
- `help_dialog.py:324` `"• Ice Ih density uses IAPWS R10-06(2009) ..."` (no URL/DOI).
- `help_dialog.py:325` `"• Water density for interfaces uses IAPWS-95 formulation"` (no URL/DOI).
- `help_dialog.py:308-309` gives GenIce2 repo URL and IAPWS URL only.

**Code reality (citations are already maintained elsewhere):**
- TIP4P-ICE parameters live in `quickice/output/_constants.py:21-22` (`TIP4P_ICE_OW_SIGMA`, `TIP4P_ICE_OW_EPSILON`) with comments citing `Abascal et al. 2005, DOI: 10.1063/1.1931662` (`_constants.py:8,16,19,25`).
- Madrid2019 ion charges (±0.85e) are surfaced in the ion panel (`quickice/gui/ion_panel.py:185`).
- spglib is used in `quickice/output/validator.py:11` (`import spglib`).
- `README.md` References (lines 333–388) carries the full citations/DOIs for GenIce2, IAPWS, spglib, Madrid2019, GAFF/GAFF2, etc.

The in-app help dialog mentions TIP4P-ICE, IAPWS R10-06, IAPWS-95, GenIce2, and IAPWS by name/URL but **without DOIs**, and does not mention spglib or Madrid2019 at all.

**Recommended change (not applied):** Add DOIs/short citations to the "More Information & Notes" page in `quickice/gui/help_dialog.py` (see Citation Suggestions below).

---

### GUI-12 — README Dependencies table omits spglib [Low]

**Doc text (`README.md:313-322`):** The Dependencies table lists `iapws`, `numpy`, `scipy`, `vtk`, `PySide6`, `genice2`, `genice-core`, `pytest` — **spglib is not listed**.

**Code reality:**
- `environment.yml:55` `- spglib==2.7.0` (and `environment-build.yml:41`).
- `quickice/output/validator.py:11` `import spglib`; `validator.py:62` `spglib.get_symmetry_dataset(...)` (space-group detection for generated structures).
- `README.md:360-363` References section *does* cite spglib with DOI, and `docs/principles.md:195-199` and `docs/cli-reference.md:1203-1206` describe spglib usage — so spglib is documented as a reference but missing from the Dependencies table.

**Recommended doc change (not applied):** Add a `spglib` row to the `README.md` Dependencies table (Purpose: "Crystal symmetry detection / structure validation").

---

## Additional Observation (informational, not a doc-vs-code contradiction)

**Mixed worker threading patterns (no doc misdescribes it):**
- `quickice/gui/hydrate_worker.py:15` `class HydrateWorker(QThread):` — direct `QThread` subclass (per `AGENTS.md`: "HydrateWorker subclasses QThread directly ... do not 'fix' this").
- `quickice/gui/main_window.py:49` `class IonInsertionWorker(QThread):` — also a direct `QThread` subclass; its docstring (`main_window.py:53-54`) explicitly states it mirrors `HydrateWorker` "per AGENTS.md — NOT QObject+moveToThread".
- `quickice/gui/workers.py:7,29,41` and `quickice/gui/custom_molecule_worker.py:13,22,33` use the **opposite** pattern: `QObject` + `moveToThread` (workers.py docstring: "Uses the worker-object pattern (QObject with run method, NOT subclassing QThread)").

No documentation claims a single threading pattern for all workers, so this is **not** a documentation inconsistency. The codebase legitimately mixes two patterns; `AGENTS.md` only calls out `HydrateWorker` (and by extension `IonInsertionWorker`) as intentionally subclassing `QThread`. Documenting the pattern split (which workers use which pattern) in `docs/principles.md` or `AGENTS.md` would reduce future confusion, but no current doc is wrong.

---

## Citation Suggestions (suggest only — do not add)

These are the physical models surfaced in the GUI and where a citation (with DOI) could be added. Existing citations in `README.md` and `docs/gui-guide.md` "Further Reading" are noted; the gap is the **in-app help dialog** (`quickice/gui/help_dialog.py`).

### 1. TIP4P-ICE water model — already cited in README/gui-guide, missing in help dialog
- **Citation:** Abascal, J. L. F., Sanz, E., García Fernández, R., & Vega, C. (2005). A potential model for the study of ices and amorphous water: TIP4P/Ice. *J. Chem. Phys.* 122, 234511. **DOI: 10.1063/1.1931662**
- **Where to add:** `quickice/gui/help_dialog.py` "More Information & Notes" page (line ~321, where "TIP4P-ICE water model used for GROMACS compatibility" appears). Currently mentions TIP4P-ICE with no DOI.
- **Why:** The GUI exports TIP4P-ICE topologies everywhere; the help dialog is the natural in-app place to surface the primary literature. The parameters themselves are already commented with the DOI at `quickice/output/_constants.py:8,16,19,25`.

### 2. Madrid2019 ion parameters — already cited (with DOI) in README/gui-guide, DOI missing from ion tooltip
- **Citation:** Zeron, I. M., Abascal, J. L. F., & Vega, C. (2019). A force field of Li+, Na+, K+, Mg2+, Ca2+, Cl−, and SO42− in aqueous solution based on the TIP4P/2005 water model and scaled charges for the ions. *J. Chem. Phys.* 151, 134504. **DOI: 10.1063/1.5121392**
- **Where to add:** `quickice/gui/ion_panel.py:186` (append `DOI: 10.1063/1.5121392` to the existing "Ref: Zeron et al. ..." tooltip line), and optionally a line in `quickice/gui/help_dialog.py` (the dialog has no ion-model citation today).
- **Why:** The ion panel already surfaces the model name and journal ref to the user at hover; adding the DOI makes the in-app citation match `docs/gui-guide.md:872` and `README.md:382-383`. Also note the TIP4P-2005→TIP4P-ICE compatibility caveat already documented at `README.md:385-387` could be mirrored in the ion tooltip.

### 3. spglib — cited in README References, not mentioned in GUI help
- **Citation:** Spglib: a software library for crystal symmetry search. *Sci. Technol. Adv. Mater., Meth.* 4, 2384822 (2024). **DOI: 10.1080/27660400.2024.2384822** (repo: https://github.com/atztogo/spglib)
- **Where to add:** `quickice/gui/help_dialog.py` "More Information & Notes" page, plus a row in the `README.md:313-322` Dependencies table (see GUI-12).
- **Why:** spglib is a direct dependency used by `quickice/output/validator.py:11` for space-group validation of generated/exported structures (invoked on the GUI export path). It is currently invisible in the in-app help and the Dependencies table.

### 4. GenIce2 — repo URL in help dialog, paper DOI missing
- **Citation:** Matsumoto, M. et al. (2017). GenIce: Hydrogen-disordered ice structures by combinatorial generation. *J. Comput. Chem.* 2017. **DOI: 10.1002/jcc.25077** (repo: https://github.com/genice-dev/GenIce2)
- **Where to add:** `quickice/gui/help_dialog.py:308` (currently lists only the repo URL). Add the paper DOI.
- **Why:** The help dialog points users to the GenIce2 repo but not the paper; `README.md:333-336` already carries both. Adding the DOI in-app keeps the citation complete.

### 5. IAPWS formulations — named in help dialog, URLs/DOIs missing
- **Citations:**
  - IAPWS R10-06(2009): "Revised Release on the Equation of State 2006 for H₂O Ice Ih" — https://www.iapws.org/release/Ice-2009.html
  - IAPWS-95: "Revised Release on the IAPWS Formulation 1995 ..." — https://www.iapws.org/relguide/IAPWS-95.html
  - IAPWS R14-08: "Revised Release on the Pressure along the Melting and Sublimation Curves ..." — http://www.iapws.org/release/MeltIce.pdf
- **Where to add:** `quickice/gui/help_dialog.py:324-325` (names R10-06 and IAPWS-95 with no links). `README.md:338-348` already carries the URLs.
- **Why:** Density values shown in the GUI phase-diagram log panel (`quickice/gui/main_window.py` uses `ice_ih_density_gcm3`/`water_density_gcm3` per `quickice/phase_mapping/ice_ih_density.py`) derive from these IAPWS releases; surfacing the document links in-app would let users verify the density sources.

### 6. AMBER/GAFF2 (comb-rule=2) — cited in README, not in help dialog
- **Citations:**
  - Wang, J. et al. (2004). Development and testing of a general amber force field. *J. Comput. Chem.* 25(9), 1157–1174. **DOI: 10.1002/jcc.20035**
  - He, X. et al. (2020). A fast and high-quality charge model for molecular mechanical force fields. *J. Chem. Inf. Model.* 60(5), 247–257. **DOI: 10.1021/acs.jcim.9b01131**
- **Where to add:** `quickice/gui/help_dialog.py` "Custom Guest in Hydrate" (line ~174, which says "comb-rule=2 mandatory" without citation) and "Custom Molecule Preparation" (line ~289-294) sections.
- **Why:** The GUI enforces comb-rule=2 (Lorentz–Berthelot, AMBER/GAFF2 convention) for custom guests and uses GAFF2 for CH₄/THF (`quickice/output/_shared.py:77-83` is the single source of truth for comb-rule=2). The help dialog states the rule but not its provenance; `README.md:374-376` already cites GAFF/GAFF2.

### 7. Ice V / Ice VII phase references — already in gui-guide "Further Reading"
- `docs/gui-guide.md:944` cites Lobban et al. 1998 (Ice V, DOI 10.1107/S0108768198001090) and `docs/gui-guide.md:945` cites Hemley et al. 1987 (Ice VII, DOI 10.1038/330737a0). These are surfaced when clicking phase regions (`quickice/gui/main_window.py` phase-info handler). **No change needed** — these are accurate and already linked from the GUI.

---

## Docs That Are Accurate (checked and consistent with code)

The following GUI-related documentation items were verified against the code and are **consistent** (no change needed):

**Tabs & layout**
- Tab order and labels: `docs/gui-guide.md:49-55` and `README.md:110-196` match `quickice/gui/main_window.py:299-304` (Tab 0 Ice, 1 Hydrate, 2 Interface, 3 Custom, 4 Solute, 5 Ion) and `quickice/gui/constants.py:23-27` (`TabIndex`).
- "Tab 1" is **Hydrate Generation** (the cross-tab note Tab 0→2→3→4→5 deliberately treats hydrate as optional). Verified at `main_window.py:300`.
- `quickice/gui/constants.py:9-22` comment ("Tab order swapped in Phase 34.3 ... Custom Molecule now appears before Solute") matches `docs/gui-guide.md:61`.

**Keyboard shortcuts**
- `docs/gui-guide.md:222-237` and `quickice/gui/help_dialog.py:76-88` match `quickice/gui/main_window.py:430,436,441,449,454,465,470,475,480,485,490` (Ctrl+S, Ctrl+Alt+P, Ctrl+Shift+S, Ctrl+D, Ctrl+Alt+S, Ctrl+G, Ctrl+H, Ctrl+I, Ctrl+L, Ctrl+M, Ctrl+J).
- Enter→generate / Escape→cancel: `main_window.py:400,406,412`. Matches `docs/gui-guide.md:225-226`.
- "Save PDB (right viewer, Tab 0 only)": `docs/gui-guide.md:229` — the dual viewer lives only in Tab 0 (`main_window.py:234-281`).

**Cross-tab data flow & source dropdowns**
- Interface source `["Ice Candidate","Hydrate Structure"]`: `docs/gui-guide.md:394-400` matches `quickice/gui/interface_panel.py:254`.
- Solute source `["Interface","Custom Molecule"]`: `docs/gui-guide.md:747-752` matches `quickice/gui/solute_panel.py:88`.
- Ion source `["Interface","Custom Molecule","Solute"]`: `docs/gui-guide.md:808-816` matches `quickice/gui/ion_panel.py:94`.
- `MainWindow._current_*_result` attributes (`_current_interface_result`, `_current_hydrate_result`, `_current_ion_result`, `_current_solute_result`, `_current_custom_molecule_result`) exist at `quickice/gui/main_window.py:158,162,174,180,183` and are used throughout — matches `AGENTS.md`.
- Duck-typed `InterfaceStructure.solute_type` / `.custom_molecule_positions` are real: set in `quickice/cli/pipeline.py:811,826`, declared in `quickice/structure_generation/types.py:425,434,875,884`, and read via `getattr`/`hasattr` in `quickice/structure_generation/ion_inserter.py:292,301` and `quickice/gui/solute_viewer.py:516-518`. This is the accepted CP-01 design; docs describe it as-is (no misdescription).

**Workers / threading**
- `HydrateWorker` subclasses `QThread` (`quickice/gui/hydrate_worker.py:15`), matching `AGENTS.md`. `docs/gui-guide.md` does not misdescribe threading.

**Hydrate (Tab 1)**
- 10 lattice types (sI, sII, sH, c0te, c1te, c2te, ice1hte, sTprime, 16, 17): `docs/gui-guide.md:270-281` and `README.md:128` match `quickice/gui/hydrate_panel.py:194-205` tooltip and `quickice/gui/hydrate_panel.py:4`.
- Depol Strict/Optimal (default Strict): `docs/gui-guide.md:330-337` matches `quickice/gui/hydrate_panel.py:219-220,221`.
- Custom-guest validation (comb-rule=2, residue ≤3 chars, `_H` suffix → ≤5 total): `docs/gui-guide.md:318-328` matches `quickice/gui/hydrate_panel.py:174` (help_dialog) and the transform logic in `quickice/gui/hydrate_export.py:225,307`.
- Hydrate export filenames `hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro`/`.top` + `ch4_hydrate.itp`/`thf_hydrate.itp` + `tip4p-ice.itp`: `docs/gui-guide.md:367-370` matches `quickice/gui/hydrate_export.py:121-123,346,358,65`.

**Solute (Tab 4) & Ion (Tab 5)**
- Solute export filenames `solute_{type}_{count}molecules.gro`/`.top` + `ch4_liquid.itp`/`thf_liquid.itp`: `docs/gui-guide.md:787-790` matches `quickice/gui/export.py:152-155,232`.
- `ion.itp` and `tip4p-ice.itp` are emitted by the ion exporter (`quickice/gui/export.py:533,540`); only the `.gro`/`.top` base names are stale (GUI-03).
- Molecule-count formula `N = C_M × V_L × N_A` (×10⁻²⁴ for nm³→L): `docs/gui-guide.md:589-592,728-737` matches the GUI/CLI insertion path.
- Ion charge neutrality (±0.85e Madrid2019): `docs/gui-guide.md:872` matches `quickice/gui/ion_panel.py:185`.

**Export / molecule ordering**
- Molecule ordering SOL → hydrate guests → custom → solutes → ions with `_H` (hydrate) / `_L` (liquid) suffixes: `README.md:217-229` matches `AGENTS.md` (MoleculetypeRegistry) and `quickice/structure_generation/moleculetype_registry.py`.
- comb-rule=2 (Lorentz–Berthelot, AMBER/GAFF2) enforced as the single source of truth at `quickice/output/_shared.py:77-83,124-139`; documented at `AGENTS.md` and `README.md:143`. Consistent.

**Phase support & generation**
- 8 generatable phases (Ih, Ic, II, III, V, VI, VII, VIII) via GenIce2; detection-only (IX, XI, XV, X): `docs/gui-guide.md:103` and `README.md:274-289` match `quickice/phase_mapping/lookup.py:27-45` (8 generatable `ice_*` + 4 detection-only). (The 11-vs-12 prose inconsistency is GUI-04, isolated to `README.md`.)
- 10 ranked candidates: `docs/gui-guide.md:118` / `README.md:118` match `quickice/gui/workers.py:104` (`n_candidates=10`).
- Ice II not supported for interfaces (rhombohedral): `docs/gui-guide.md:285,409` and `README.md:291` match the GUI behavior and `quickice/gui/help_dialog.py:279`.
- Ice V monoclinic→orthogonal transformation message: `docs/gui-guide.md:464-473` matches the GUI status-log behavior.

**Input validators (Tab 0)**
- Temperature 0–500 K: `docs/gui-guide.md:76` matches `quickice/gui/validators.py:34` and placeholder `quickice/gui/view.py:79,89`.
- Pressure 0–10000 MPa: `docs/gui-guide.md:82` matches `quickice/gui/validators.py:65` and `quickice/gui/phase_diagram_widget.py:333` (axis 0.1–100000 MPa).
- Box 1.0–100 nm, thickness 0.5–50 nm, pocket 0.5–50 nm, seed 1–999999: `docs/gui-guide.md:425-453` match `quickice/gui/validators.py:134,166,199,242`. (Only molecule count is wrong — GUI-01.)
- Pocket shape options "Sphere"/"Cubic": `docs/gui-guide.md:438` matches `quickice/gui/interface_panel.py:195` (`addItems(["Sphere","Cubic"])`).

**Launch / headless / remote**
- `entry.py` routing (no-args→help, `--cli`, `--gui`, pipeline-flag detection): `README.md:100-108` matches `quickice/entry.py:105-201`; `_is_pyside6_available()` uses `importlib.util.find_spec('PySide6')` (`entry.py:37`) as `AGENTS.md` states.
- `quickice.py:7` and `quickice/__main__.py:3` both delegate to `quickice.entry.main()` — matches `AGENTS.md` ("Entry router is `quickice/entry.py::main()`").
- `_configure_opengl_for_remote()` sets `__GLX_VENDOR_LIBRARY_NAME=mesa` for remote (non-`:0`) displays and no-ops when `DISPLAY` unset: `docs/gui-guide.md:26-45` matches `quickice/gui/main_window.py:2259-2283`, called before `QApplication` at `main_window.py:2297-2300`.
- `QT_QPA_PLATFORM=offscreen` for headless/CI: `docs/gui-guide.md:43-45` and `AGENTS.md` match the code (no-ops when `DISPLAY` unset; offscreen is user-set).
- `QUICKICE_FORCE_VTK=true` override: `docs/gui-guide.md:924` and `scripts/run_gui_ssh.sh` match `quickice/gui/vtk_utils.py:874` and the viewer hint strings (`solute_viewer.py:232`, `ion_viewer.py:232`, etc.).
- PySide6/Qt version: `docs/gui-guide.md:901` ("Qt 6.10.2") matches `environment.yml:35` (`pyside6=6.10.2`).

**Screenshots**
- All 12 images referenced in `docs/gui-guide.md` (`quickice-v4-gui.png`, `phase-diagram.png`, `3d-viewer.png`, `dual-viewport.png`, `export-menu.png`, `hydrate-panel.png`, `slab/pocket/piece-interface.png`, `custom-molecule-panel.png`, `solute-panel.png`, `ion-panel.png`) are present in `docs/images/`. No stale/missing screenshot references.

**In-app UI text**
- "Validate & Preview" button exists: `docs/gui-guide.md:617-628` and `quickice/gui/help_dialog.py:124` match `quickice/gui/custom_molecule_panel.py:287` (`QPushButton("Validate & Preview")`).
- Candidate selector shows `"Rank N (phase)"`: `docs/gui-guide.md:213` matches `quickice/gui/dual_viewer.py:344,353` and `quickice/gui/view.py:581,590`.
- Density info (Ice Ih via IAPWS R10-06, liquid via IAPWS-95, others fixed): `docs/gui-guide.md:126-133` matches `quickice/phase_mapping/lookup.py:60-63` and `quickice/phase_mapping/ice_ih_density.py`.

---

*End of GUI documentation crosscheck — 2026-07-23. READ-ONLY; no files were modified.*
