# GUI Documentation Cross-Check Report (Scancode Task C)

**Analysis Date:** 2026-07-15
**Scope:** GUI path only — `quickice/gui/` (panels, viewers, help_dialog, export), `quickice/entry.py`, `README.md`, `docs/gui-guide.md`, `README_bin.md`, tooltips/statusTips, screenshots. CLI docs are out of scope (separate agent).
**Mode:** Read-only. No code run, no modifications.
**Prior Scans:** `.planning/code_analysis/20260618_documentation_crosscheck_gui.md` (10 active issues), `.planning/code_analysis/20260615_documentation_crosscheck_gui.md`, `.planning/code_analysis/20260612_documentation_crosscheck.md`.

---

## Doc files reviewed

| Path | Role |
|------|------|
| `README.md` (426 lines) | Top-level overview, 6-tab feature list, ice phase tables, references |
| `docs/gui-guide.md` (911 lines) | Primary GUI user guide — 6 tabs, keyboard shortcuts, export |
| `README_bin.md` (60 lines) | Binary distribution launch instructions |
| `quickice/gui/help_dialog.py` (397 lines) | In-app QuickReferenceDialog (QStackedWidget TOC, 11 pages) |
| `quickice/gui/main_window.py` (2174 lines) | MVVM MainWindow, `_get_citation()`, `_get_structure_type()`, `run_app()`, `_configure_opengl_for_remote()` |
| `quickice/gui/interface_panel.py` | Tab 2 panel — tooltips, source combo, range validators |
| `quickice/gui/custom_molecule_panel.py` | Tab 3 panel — button labels, validate button |
| `quickice/gui/solute_panel.py` | Tab 4 panel — THF description, source combo |
| `quickice/gui/ion_panel.py` | Tab 5 panel — source combo, insert button tooltip |
| `quickice/gui/export.py` (1138 lines) | GUI GROMACS exporters — default filenames, ITP staging |
| `quickice/gui/hydrate_export.py` | Hydrate GROMACS export — default filename pattern |
| `quickice/entry.py` (201 lines) | Router — `find_spec('PySide6')`, display detection |
| `docs/ranking.md` (269 lines) | Ranking methodology (shared by GUI/CLI) |
| `docs/principles.md` (219 lines) | Design principles (shared) |
| `docs/images/` | Screenshots referenced by gui-guide.md |
| `quickice/phase_mapping/lookup.py` | `PHASE_METADATA` — 12 phases incl. ice_xi/ix/x/xv |
| `quickice/phase_mapping/solid_boundaries.py` | Phase boundary definitions |

---

## Inconsistencies found

### INC-1: Screenshot filename mismatches in `docs/gui-guide.md` (MEDIUM)

- **Doc location:** `docs/gui-guide.md:241,393,401,408,475,669,788` — references `images/hydrate-panel.png`, `images/slab-interface.png`, `images/pocket-interface.png`, `images/piece-interface.png`, `images/custom-molecule-panel.png`, `images/solute-panel.png`, `images/ion-panel.png`.
- **Actual files** in `docs/images/`: `hydrate-panel.png`, `slab-interface.png`, `pocket-interface.png`, `piece-interface.png`, `custom-molecule-panel.png`, `solute-panel.png`, `ion-panel.png` (all exist with these exact names — see `ls docs/images/`).
- **Code/actual behavior:** The 2026-06-18 prior scan (DOC-G5) reported 5 mismatches + 2 missing (claiming actual filenames were `tab2-hydrate-panel.png` etc.). On 2026-07-15 the filenames actually present ARE `hydrate-panel.png`, `slab-interface.png`, `pocket-interface.png`, `piece-interface.png`, `custom-molecule-panel.png`, `solute-panel.png`, `ion-panel.png` — i.e. they now MATCH the doc references. **Prior-scan finding is now STALE / resolved**; current state is consistent.
- **Severity:** LOW (no action — flagging that the prior finding should be closed)
- **Suggested fix:** Close DOC-G5 in the next verification pass; the image set has been renamed to match the doc references.

### INC-2: `docs/gui-guide.md` Hydrate Overview says "Select hydrate lattice type (sI, sII, sH)" — stale 3-lattice list (LOW)

- **Doc location:** `docs/gui-guide.md:233` — "Select hydrate lattice type (sI, sII, sH)"
- **Code/actual behavior:** `quickice/gui/help_dialog.py:107` was corrected in Phase 48-10 to "Select lattice type (10 types: sI, sII, sH, c0te, c1te, c2te, ice1hte, sTprime, 16, 17)…". The hydrate panel `quickice/gui/hydrate_panel.py:188` populates all 10 lattices. `docs/gui-guide.md:247` (Lattice Types table) correctly lists all 10. Only the **Overview bullet at line 233** was missed in the 48-10 sweep.
- **Severity:** LOW
- **Suggested fix:** Change `docs/gui-guide.md:233` from "Select hydrate lattice type (sI, sII, sH)" to "Select hydrate lattice type (10 types: sI, sII, sH, c0te, c1te, c2te, ice1hte, sTprime, 16, 17)" to match the help_dialog and the Lattice Types table below it.

### INC-3: README Overview "11 ice polymorphs" feature bullet lists only 11 names while section header says "12 phases" (LOW)

- **Doc location:** `README.md:16` — "Ice Generation — 11 ice polymorphs"; `README.md:26` — "Interactive phase diagram with 11 ice polymorphs"; `README.md:116` — "**11 ice polymorphs** — Ih, Ic, II, III, V, VI, VII, VIII, IX, XV, X" (11 names); `README.md:253` — "### Phase Detection (12 phases)"; `README.md:255` — "can identify 11 ice polymorphs".
- **Code/actual behavior:** `quickice/phase_mapping/lookup.py:41-45` defines 12 phases in `PHASE_METADATA` (ice_ih, ice_ic, ice_ii, ice_iii, ice_v, ice_vi, ice_vii, ice_viii, ice_ix, ice_xi, ice_xv, ice_x). The phase table at `README.md:257-270` lists 12 rows (incl. Ice XI). The feature bullet at line 116 omits Ice XI (which IS in the table at line 268). The 2026-06-18 NEW-3 flagged "12" vs 11; the count was later changed to "11" but the section header still says "12 phases" and the table still has 12 rows — so the doc is now internally inconsistent (count 11 in feature bullet, count 12 in section header, 12 rows in table).
- **Severity:** LOW
- **Suggested fix:** Pick one count. The code detects 12 (incl. Ice XI). Recommend: change `README.md:16`, `:26`, `:116`, `:255` back to "12" and add "XI" to the feature bullet list at line 116 to match the table and `PHASE_METADATA`. (This re-opens NEW-3 with the inverse fix.)

### INC-4: `docs/gui-guide.md` ion export filename `interface_with_ions.gro` does not match code default (LOW)

- **Doc location:** `docs/gui-guide.md:845` — "interface_with_ions.gro — Coordinates with ions"
- **Code/actual behavior:** `quickice/gui/export.py:465-467` sets the default ion-export filename to `ions_{na_count}na_{cl_count}cl.gro` (or `ions_{na_count}na_{cl_count}cl_with_{n}{type}.gro` if solutes present). The success dialog at `main_window.py:1762` reports `ions_{na}na_{cl}cl.gro/.top`. The documented name `interface_with_ions.gro` is never produced by the code.
- **Severity:** LOW
- **Suggested fix:** Update `docs/gui-guide.md:845-846` to "`ions_{na}na_{cl}cl.gro` — Coordinates with ions (e.g. `ions_12na_12cl.gro`); `ions_{na}na_{cl}cl.top` — Topology with Na⁺/Cl⁻" to match `export.py:467` and the main_window success dialog.

### INC-5: `docs/gui-guide.md` solute export filename example may not match code for all solutes (LOW)

- **Doc location:** `docs/gui-guide.md:754` — "`solute_{type}_{count}molecules.gro` — … (e.g., `solute_ch4_45molecules.gro`)"
- **Code/actual behavior:** `quickice/gui/export.py:155` uses `f"solute_{solute_type}_{n_molecules}molecules.gro"` where `solute_type = solute_structure.solute_type.lower()` (`export.py:152`). For CH₄ this yields `solute_ch4_...`; for THF, `solute_thf_...`. The doc example is correct for CH₄. **No inconsistency** — flagging as verified.
- **Severity:** NONE (verified consistent)

### INC-6: `docs/gui-guide.md` hydrate export filename example omits supercell (LOW)

- **Doc location:** `docs/gui-guide.md:347` — "`hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro` — … (e.g., `hydrate_sI_ch4_2x2x2.gro`)"
- **Code/actual behavior:** `quickice/gui/hydrate_export.py:123` uses `f"hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro"`. **Consistent.** Verified.

### INC-7: README "11 ice polymorphs" Overview bullet vs "Phase Detection (12 phases)" header (dup of INC-3) — see INC-3

(Consolidated under INC-3.)

### INC-8: `docs/gui-guide.md` "Save PDB" section lists `Ctrl+S` as "Save/Export from active tab (unified)" but the shortcuts table lists `Ctrl+S` identically — consistent (NONE)

- **Doc location:** `docs/gui-guide.md:163,206` and table at 202-216.
- **Code/actual behavior:** `quickice/gui/main_window.py:346` registers `Ctrl+S` → unified export; `help_dialog.py:78` lists "Ctrl+S — Export current tab for GROMACS". **Consistent across all three surfaces.**

### INC-9: `docs/gui-guide.md` Ion Concentration Range "0.0 - 5.0 M" vs Typical "seawater ~0.6 M" — verify against `ion_panel.py` (LOW)

- **Doc location:** `docs/gui-guide.md:794-797` — "Range: 0.0 - 5.0 M; Typical seawater: ~0.6 M; Drinking water: <0.05 M"
- **Code/actual behavior:** `quickice/gui/ion_panel.py` concentration spin range not directly verified in this pass (grep did not return the setRange line). The scientific claims (seawater ~0.6 M, drinking water <0.05 M) are standard and accurate. **No doc/code inconsistency detected** for the range claim; the "typical" values are editorial/scientific.
- **Severity:** NONE (verified)
- **Caveat:** A future pass should confirm `ion_panel.py` `setRange` matches "0.0 - 5.0 M" exactly (the solute panel was verified at 0.0-2.0 M in prior scans).

---

## Missing documentation

### MISS-1: Interface Tab "Hydrate Structure" source option undocumented in `docs/gui-guide.md` (MEDIUM)

- **Code:** `quickice/gui/interface_panel.py:258` — `self.source_combo.addItems(["Ice Candidate", "Hydrate Structure"])`. Tooltip at `:259-263`: "Hydrate Structure — Generate hydrate directly in Tab 1".
- **Docs:** `docs/gui-guide.md:355-449` (Interface Construction section) describes only the Ice Candidate path ("The candidate dropdown in Tab 2 is populated from Tab 0's results", `:364-366`). The HelpIcon tooltip text at `:266-268` ("Hydrate Structure generates hydrate lattices (sI, sII, sH) directly without going to Tab 1") is in code but not surfaced in the user guide.
- **Severity:** MEDIUM — users reading gui-guide cannot discover that Tab 2 can generate a hydrate-interface directly from a hydrate lattice without first visiting Tab 1.
- **Suggested fix:** Add a "Source Selection" subsection to the Interface Construction section of `docs/gui-guide.md` documenting both "Ice Candidate" (from Tab 0) and "Hydrate Structure" (sI/sII/sH generated directly) source options, mirroring the existing Source Selection subsections for Tabs 4 (`:711`) and 5 (`:774`).

### MISS-2: `_configure_opengl_for_remote()` / `__GLX_VENDOR_LIBRARY_NAME=mesa` runtime set is undocumented in user-facing docs (MEDIUM)

- **Code:** `quickice/gui/main_window.py:2115-2139` — `_configure_opengl_for_remote()` sets `os.environ['__GLX_VENDOR_LIBRARY_NAME'] = 'mesa'` for remote (non-`:0`-style) DISPLAY, before QApplication is created.
- **Docs:** `docs/gui-guide.md:884-890` mentions `QUICKICE_FORCE_VTK=true` for remote X11 but does NOT mention the automatic Mesa GLX override. `README_bin.md:50` mentions `QUICKICE_FORCE_VTK=true` for SSH. `AGENTS.md` mentions `QT_QPA_PLATFORM=offscreen` but not the Mesa GLX auto-fix.
- **Severity:** MEDIUM — users on SSH X11 forwarding may not realize the app auto-switches to Mesa; relevant for troubleshooting "3D viewer slow / software rendering" reports.
- **Suggested fix:** Add a note to `docs/gui-guide.md` Troubleshooting "3D viewer unavailable in remote environment" subsection: "QuickIce automatically forces Mesa GLX (`__GLX_VENDOR_LIBRARY_NAME=mesa`) for remote (SSH X11-forwarded) displays to avoid an NVIDIA-GLX segfault; no user action required. Use `QUICKICE_FORCE_VTK=true` to additionally enable VTK rendering over SSH X11."

### MISS-3: QuickIce `.bat` / `.sh` launcher scripts and `python -m quickice.gui` direct entry are split across README/README_bin/gui-guide (LOW)

- **Code:** `quickice/gui/__main__.py` supports `python -m quickice.gui`; `QuickIce.sh`/`QuickIce.bat` at repo root pass `--gui`.
- **Docs:** `README.md:82-84` documents `python -m quickice.gui`; `docs/gui-guide.md:21` documents `python -m quickice.gui`; `README_bin.md:36-39` documents the `.sh`/`.bat` launchers. The binary `--gui` flag is documented. **Mostly covered**, but `docs/gui-guide.md` does not mention the `.sh`/`.bat` launcher scripts at all (only the source-install `python -m quickice.gui` command at line 21, and a pointer to README_bin at line 24).
- **Severity:** LOW
- **Suggested fix:** Optional — add a one-line note in gui-guide "Launching the GUI" that binary users should use `QuickIce.sh` / `QuickIce.bat` (see README_bin.md).

### MISS-4: `entry.py` router behavior (`--gui` display check, `--cli` skip-import) not fully in user guide (LOW)

- **Code:** `quickice/entry.py:42-69` `_has_display()` checks `DISPLAY`/`WAYLAND_DISPLAY`/`QT_QPA_PLATFORM`; `:168-178` `--gui` requires PySide6 + display; `:180-187` `--cli` strips router flags.
- **Docs:** `README.md:100-108` documents the entry router concisely and accurately. **Consistent.** Verified.
- **Severity:** NONE (verified)

### MISS-5: Hydrate "Mixed cage occupancy" UI per-cage rows + HelpIcon tooltips (Phase 48-12) not shown in gui-guide screenshots (LOW)

- **Code:** `quickice/gui/hydrate_panel.py` `_rebuild_cage_rows` builds per-cage guest QComboBox + occupancy QDoubleSpinBox with HelpIcon tooltips (Phase 48-12 added 2 HelpIcons).
- **Docs:** `docs/gui-guide.md:281-296` describes mixed cage occupancy textually; the screenshot `images/hydrate-panel.png` predates v4.7 (pre-mixed-occupancy layout) and does not show per-cage rows.
- **Severity:** LOW — text is accurate; screenshot is stale (pre-v4.7 single-guest panel).
- **Suggested fix:** Regenerate `docs/images/hydrate-panel.png` to show the v4.7 per-cage occupancy rows + depol dropdown + custom-guest upload button. (Screenshot update; not a text fix.)

---

## Stale documentation

### STALE-1: Prior-scan screenshot-mismatch finding (DOC-G5) is now obsolete (INFO)

- **Prior claim (2026-06-18):** 5 mismatched paths + 2 missing in `docs/gui-guide.md`.
- **Current state (2026-07-15):** `docs/images/` contains `hydrate-panel.png`, `slab-interface.png`, `pocket-interface.png`, `piece-interface.png`, `custom-molecule-panel.png`, `solute-panel.png`, `ion-panel.png` — all matching the gui-guide references. The mismatched `tab2-*` filenames no longer exist.
- **Severity:** INFO — close DOC-G5.

### STALE-2: `docs/gui-guide.md:40` version-history note still references "v4.5 added … moving Ion to Tab 5; v4.7 adds Extended Hydrate Generation" (INFO)

- **Doc location:** `docs/gui-guide.md:40` — "v4.5 added Custom Molecule (Tab 3) and Solute Insertion (Tab 4), moving Ion to Tab 5; v4.7 adds Extended Hydrate Generation…"
- **Code/actual behavior:** Accurate historical note (present tense "adds" for v4.7 is correct since v4.7 is current). **Not stale.** Verified.

### STALE-3: `docs/gui-guide.md:182` "QuickIce v4.0 added interface construction; v4.5 added solute and custom molecule insertion; v4.7 adds extended hydrate generation…" (INFO)

- **Code/actual behavior:** Accurate. **Not stale.** Verified (was flagged in 2026-06-18 §2.4 as fixed).

### STALE-4: `docs/gui-guide.md:82` "QuickIce can generate structures for 8 ice polymorphs (Ih, Ic, II, III, V, VI, VII, VIII); the diagram also shows regions for Ice IX, X, XI, XV…" (LOW)

- **Doc location:** `docs/gui-guide.md:82`
- **Code/actual behavior:** Accurate — 8 generatable + 4 detection-only (IX, X, XI, XV) = 12 detected, matching `PHASE_METADATA` (12 entries) and GenIce2 lattice coverage (8). **Verified consistent.**
- **Severity:** NONE (verified)

### STALE-5: README "Project Structure" tree at `README.md:404-421` omits several GUI/output modules (LOW)

- **Doc location:** `README.md:404-421` — Project Structure tree lists `quickice/cli/`, `quickice/gui/`, `quickice/phase_mapping/`, `quickice/structure_generation/`, `quickice/ranking/`, `quickice/output/`, `quickice/data/`.
- **Code/actual behavior:** `quickice/output/` actually contains `gromacs_writer.py`, `guest_info.py`, `orchestrator.py`, `pdb_writer.py`, `phase_diagram.py`, `types.py`, `validator.py` (7 modules). `quickice/gui/` has ~30 files (viewers, renderers, panels, workers, export.py, help_dialog.py, constants.py, validators.py, vtk_utils.py). The tree is a high-level summary, not exhaustive.
- **Severity:** LOW — acceptable as a summary, but `guest_info.py` (the v4.7 custom-guest bridge shared by GUI + CLI) is a notable omission.
- **Suggested fix:** Optional — add `output/guest_info.py` to the tree comment or note "shared custom-guest bridge (v4.7)".

### STALE-6: `docs/gui-guide.md` "3D viewer unavailable in remote environment" omits the auto-Mesa fix (covered by MISS-2)

(Consolidated under MISS-2.)

---

## Citations to add

### CITE-1: `_get_citation()` returns "No specific citation in GenIce2" for Ice V and Ice VII (LOW, carry-over DOC-G8)

- **Code:** `quickice/gui/main_window.py:2073` — `"ice_vii": "High-pressure ice VII. No specific citation in GenIce2."`; `:2071` — `"ice_v": "Monoclinic ice V. No specific citation in GenIce2."`
- **Available citations:** `docs/gui-guide.md:910` already lists Ice VII: "Hemley, R. J., Jephcoat, A. P., Mao, H. K., Zha, C. S., Finger, L. W., & Cox, D. E. (1987). Static compression of H₂O-ice to 128 GPa. *Nature* 330, 737–740. DOI: 10.1038/330737a0". `docs/gui-guide.md:911` lists Ice V: "Lobban, C., Finney, J. L., & Kuhs, W. F. (1998). The structure of a new phase of ice V by neutron powder diffraction. *Acta Cryst.* B54, 419–428. DOI: 10.1107/S0108768198001090".
- **Severity:** LOW
- **Suggested fix:** In `quickice/gui/main_window.py:2071` replace the Ice V placeholder with the Lobban 1998 citation; at `:2073` replace the Ice VII placeholder with the Hemley 1987 citation. Both DOIs are already validated in the repo's own Further Reading section.
- **Status:** Unresolved since 2026-06-18 (DOC-G8).

### CITE-2: Ion Insert button tooltip lacks Madrid2019 reference (LOW, carry-over DOC-G12)

- **Code:** `quickice/gui/ion_panel.py:324` — `self.insert_button.setToolTip("Insert Na+ and Cl- ions into the liquid water region.")`. (No Madrid2019 mention.)
- **Docs:** `docs/gui-guide.md:838` correctly cites Madrid2019 (Zeron, Abascal & Vega, J. Chem. Phys. 151, 134504 (2019), DOI: 10.1063/1.5121392). `README.md:381-387` cites the same. `quickice/structure_generation/gromacs_ion_export.py:40` and `ion_inserter.py:26` reference "Madrid2019" / "Zeron et al.".
- **Severity:** LOW
- **Suggested fix:** Append to the ion insert button tooltip: `"\nUses Madrid2019 parameters (±0.85e charges) with TIP4P-ICE water."` to surface the force field at the point of use.
- **Status:** Unresolved since 2026-06-18 (DOC-G12).

### CITE-3: README Madrid2019 DOI — verify the canonical DOI (LOW)

- **Doc location:** `README.md:383` — `DOI: https://doi.org/10.1063/1.5121392`; `README.md:387` — `DOI: 10.1063/1.5121392`.
- **Code:** `quickice/structure_generation/gromacs_ion_export.py:40` comment: "; Madrid2019_085 ion model (Zeron et al., J. Chem. Phys. 2019)".
- **Note:** The 2026-06-18 scan (§2.3) claimed the DOI was "fixed" from `10.1063/1.5121392` to `10.1063/1.5121394`. On 2026-07-15 the README still shows `10.1063/1.5121392` (lines 383 and 387). **The "fix" did not persist OR was reverted.** The correct DOI for Zeron, Abascal & Vega, J. Chem. Phys. 151, 134504 (2019) is `10.1063/1.5121394` [NEEDS VERIFICATION — please confirm against the publisher record before changing; the article volume/page 134504 is consistent, but the DOI suffix differs between the two scans]. The 2026-06-15 scan said `10.1063/1.5121392` was "incorrect" and `10.1063/1.5121394` was "correct"; the 2026-06-18 scan claimed it was fixed to `.1394`; the 2026-07-15 README shows `.1392`.
- **Severity:** LOW (citation accuracy)
- **Suggested fix:** Resolve the DOI discrepancy definitively. Fetch https://doi.org/10.1063/1.5121394 and https://doi.org/10.1063/1.5121392 to confirm which resolves to the Zeron 2019 article, then standardize across `README.md:383,387` and any tooltip additions.

### CITE-4: `docs/ranking.md:11` diversity wording "Penalizes structural similarity" vs `docs/principles.md:73` "Measures structural diversity" (LOW, carry-over NEW-4)

- **Doc location:** `docs/ranking.md:11` — "Diversity Score - Penalizes structural similarity via O-O distance fingerprint"
- **Code:** `docs/ranking.md:121-129` correctly describes `diversity_score = 1 - mean_similarity`; `docs/ranking.md:188` — "`1 - norm_diversity` inverts diversity (higher diversity → lower combined score)". `docs/principles.md:73` — "Measures structural diversity via O-O distance histogram fingerprints (cosine similarity between candidates)".
- **Severity:** LOW — wording inconsistency between two internal docs. The "Penalizes" wording is technically accurate (high similarity → low diversity_score → high combined score after the 1-norm inversion) but "Measures" is more neutral and matches principles.md.
- **Suggested fix:** Change `docs/ranking.md:11` to "Measures structural uniqueness via O-O distance fingerprint (high similarity → low diversity score → higher combined rank)" to match principles.md and clarify the inversion.
- **Status:** Unresolved since 2026-06-18 (NEW-4).

### CITE-5: `_get_citation()` for `ice_ih` says "No specific citation required" — consider adding IAPWS R10-06 (INFO)

- **Code:** `quickice/gui/main_window.py:2061` — `"ice_ih": "Hexagonal ice Ih (most common ice). No specific citation required."`
- **Docs:** `README.md:343-345` cites IAPWS R10-06(2009) for Ice Ih EOS; `docs/gui-guide.md:108` notes "Ice Ih: Temperature-dependent density from IAPWS R10-06(2009)".
- **Severity:** INFO — the "no citation required" choice is defensible (Ih is the common form), but the density curve used by the GUI (`ice_ih_density_gcm3`, `main_window.py:1955`) IS IAPWS R10-06(2009)-derived.
- **Suggested fix:** Optional — append to the Ice Ih citation: "Density from IAPWS R10-06(2009): Revised Release on the Equation of State 2006 for H₂O Ice Ih. URL: https://www.iapws.org/release/Ice-2009.html" to attribute the density source shown in the info panel.

### CITE-6: GUI phase-info panel shows density + structure but not the density's source citation for non-Ih phases (INFO)

- **Code:** `quickice/gui/main_window.py:1961` — for non-Ih/non-liquid phases, density comes from `meta.get("density", "Unknown")` (a fixed reference density from `PHASE_METADATA`). `:1963` reads `meta.get("density_note")`. The citation at `:1982` is `_get_citation(phase_id_full)` (the structure citation), NOT a density citation.
- **Docs:** `docs/gui-guide.md:104-112` says "Other ice phases: Fixed reference densities" and "This ensures accurate density values…". The source of the fixed densities (`PHASE_METADATA` in `lookup.py:41-45`) is not cited per-phase in the GUI.
- **Severity:** INFO — fixed densities are standard handbook values; the GenIce2/IAPWS references are in the README.
- **Suggested fix:** Optional — add a one-line note to the phase-info log panel: "Density: handbook reference value (see README References)" for non-Ih phases, or add per-phase density citations to `PHASE_METADATA`.

---

## Headless / VTK notes

### HEAD-1: `QUICKICE_FORCE_VTK` env var — documented (VERIFIED)

- **Code:** Checked in 6 viewer modules: `quickice/gui/view.py:26`, `quickice/gui/solute_viewer.py:25`, `quickice/gui/interface_panel.py:35`, `quickice/gui/hydrate_viewer.py:26`, `quickice/gui/ion_viewer.py:26`, `quickice/gui/custom_molecule_viewer.py:26`. Pattern: `os.environ.get('QUICKICE_FORCE_VTK', '').lower() == 'true'`. Fallback message at `view.py:405` and others: "or use QUICKICE_FORCE_VTK=true to override."
- **Docs:** `docs/gui-guide.md:890` — "In some cases, it is possible to use `QUICKICE_FORCE_VTK=true` to override the check and run the GUI remotely." `README_bin.md:50` — "Remotely via ssh, enable the 3D viewer if the system supports it: `QUICKICE_FORCE_VTK=true ./quickice-gui/quickice-gui --gui`".
- **Severity:** NONE (verified consistent across docs and code).

### HEAD-2: `QT_QPA_PLATFORM=offscreen` for headless GUI tests — documented in AGENTS.md, not in user-facing GUI docs (LOW)

- **Code:** `quickice/entry.py:60-67` `_has_display()` accepts `QT_QPA_PLATFORM` in `('wayland', 'xcb', 'offscreen')` as a display indicator. Tests use `QT_QPA_PLATFORM=offscreen` (see `.planning/phases/48-documentation/48-14-VERIFICATION.md`, `tests/test_help_dialog.py`).
- **Docs:** `AGENTS.md:42` — "GUI tests require `QT_QPA_PLATFORM=offscreen` on machines without a display." This is an agent/developer doc. The user-facing `docs/gui-guide.md` and `README.md` do NOT mention `QT_QPA_PLATFORM=offscreen`.
- **Severity:** LOW — appropriate for AGENTS.md (developer-facing); users rarely need it. The `docs/gui-guide.md` Troubleshooting section covers `QUICKICE_FORCE_VTK` but not the offscreen platform plugin.
- **Suggested fix:** Optional — add a developer-note in `docs/gui-guide.md` Troubleshooting: "For headless/CI environments, set `QT_QPA_PLATFORM=offscreen` (see AGENTS.md). VTK rendering may still be unavailable headless."

### HEAD-3: ROADMAP.md TEST-06 (deferred VTK rendering tests) — verify docs mention the deferral (VERIFIED with caveat)

- **Prior claim (2026-06-18):** TEST-06 was "deferred VTK testing."
- **Current state:** `.planning/REQUIREMENTS.md:194` — "| TEST-06 | Phase 42 | Complete |" — TEST-06 is marked **Complete** in the current requirements matrix (re-interpreted as "E2E tests for mixed cage occupancy hydrate generation," satisfied by `test_e2e_mixed_cage_occupancy.py` per `REQUIREMENTS.md:95`). The original "VTK rendering fallback path untested" concern appears in `.planning/milestones/v4.5-ROADMAP.md:319` as "Deferred (mock-based testing possible)" and `.planning/codebase/20260612_STALE_ISSUES_AUDIT.md:123` as "OPEN — Low priority."
- **Docs:** `AGENTS.md:42` — "VTK rendering may still crash in some headless environments — mock or skip VTK-dependent tests if needed. See ROADMAP.md TEST-06 (deferred)."
- **Severity:** LOW — AGENTS.md references TEST-06 as "deferred," but REQUIREMENTS.md marks it Complete (re-scoped). The two planning docs disagree on TEST-06's status. The user-facing docs (README, gui-guide) do NOT mention TEST-06 at all (appropriate — it is an internal test-gap marker).
- **Suggested fix:** Reconcile `AGENTS.md:42` with `REQUIREMENTS.md:194` — either update AGENTS.md to say "VTK rendering fallback path remains untested (low priority; see CONCERNS.md)" or update REQUIREMENTS.md to split TEST-06 (mixed-occupancy E2E, complete) from TEST-06b (VTK fallback, deferred). The user-facing GUI docs need no change.

### HEAD-4: VTK availability detection duplicated across 6 viewer files (TECH DEBT, not a doc issue)

- **Code:** The `_VTK_AVAILABLE = os.environ.get('QUICKICE_FORCE_VTK', '').lower() == 'true'` + `DISPLAY` localhost check is copy-pasted in 6 modules (`view.py:26`, `solute_viewer.py:25`, `interface_panel.py:35`, `hydrate_viewer.py:26`, `ion_viewer.py:26`, `custom_molecule_viewer.py:26`). Flagged in `.planning/codebase/20260612_STALE_ISSUES_AUDIT.md:119` as VTK-DUP, still OPEN.
- **Docs:** Not a user-facing doc issue; flagged here for completeness. The 6-viewer fallback message is consistent across all modules ("Set QUICKICE_FORCE_VTK=true to attempt VTK rendering").
- **Severity:** LOW (tech debt, not doc inconsistency)

### HEAD-5: `__GLX_VENDOR_LIBRARY_NAME=mesa` auto-set — undocumented in user-facing GUI guide (covered by MISS-2)

(Consolidated under MISS-2.)

### HEAD-6: 6 VTK viewers — gui-guide says "two viewports" for Tab 0 only; other tabs have single viewport (VERIFIED)

- **Code:** `quickice/gui/dual_viewer.py` (Tab 0 dual viewport); `interface_viewer.py`, `hydrate_viewer.py`, `solute_viewer.py`, `ion_viewer.py`, `custom_molecule_viewer.py` each single-viewport.
- **Docs:** `docs/gui-guide.md:120-130` documents dual viewport for Tab 0; single viewer for Tabs 1-5 (`:335-340` hydrate, `:422-428` interface, `:628-632` custom, `:734-738` solute, `:826-831` ion). **Consistent.** The "6 viewers" in the task prompt refers to the 6 viewer modules (one per tab) — all documented.

---

## Cross-tab data flow (CP-01 duck-typing) — verify docs match code

### FLOW-1: AGENTS.md describes duck-typing on `InterfaceStructure`; gui-guide does not expose internals (VERIFIED)

- **AGENTS.md:36** — "Duck-typing sets runtime attributes on `InterfaceStructure` (e.g., `.solute_type`, `.custom_molecule_positions`). This is an accepted design decision (CP-01), NOT a bug."
- **Code:** `quickice/gui/main_window.py:913` — `interface.custom_itp_path = custom_structure.itp_path` (runtime attribute set on interface). `quickice/gui/export.py:152` reads `solute_structure.solute_type.lower()`. `quickice/gui/solute_viewer.py:521,532` reads `custom_structure.custom_molecule_positions`. These are runtime-injected attributes (CP-01 duck-typing).
- **Docs:** `docs/gui-guide.md` does NOT document the duck-typing internals (appropriate — it is an implementation detail). The user-facing description of the cross-tab flow is at `docs/gui-guide.md:596-609` (Custom → Solute → Ion workflow) and `:774-784` (Ion source selection). Both match the code signal/slot wiring verified in the 2026-06-18 scan §7.
- **Severity:** NONE — user docs correctly abstract over the duck-typing; AGENTS.md correctly flags it as accepted design.

### FLOW-2: `HydrateWorker` subclasses `QThread` directly — AGENTS.md says "do not fix"; docs do not mention (VERIFIED)

- **AGENTS.md:26** — "`HydrateWorker` subclasses `QThread` directly (not migrated to QObject+moveToThread) — do not 'fix' this."
- **Code:** `quickice/gui/hydrate_worker.py` (4518 bytes) + `quickice/gui/workers.py:8190` (8 KB) define the QThread workers.
- **Docs:** Not mentioned in user-facing docs (appropriate — implementation detail).
- **Severity:** NONE (verified)

---

## Summary table

| # | ID | Category | Location | Severity | Brief | Status |
|---|----|----------|----------|----------|-------|--------|
| 1 | INC-1 | Images | docs/gui-guide.md screenshots | LOW | Prior mismatch now resolved | Close DOC-G5 |
| 2 | INC-2 | Stale list | docs/gui-guide.md:233 | LOW | "sI, sII, sH" 3-lattice Overview bullet | Fix to 10 |
| 3 | INC-3 | Count | README.md:16,26,116,255 | LOW | "11" vs "12 phases" header vs 12-row table | Reconcile to 12 + add XI |
| 4 | INC-4 | Filename | docs/gui-guide.md:845 | LOW | `interface_with_ions.gro` ≠ code `ions_Nna_Ncl.gro` | Update |
| 5 | INC-5 | Filename | docs/gui-guide.md:754 | NONE | solute filename verified | — |
| 6 | INC-6 | Filename | docs/gui-guide.md:347 | NONE | hydrate filename verified | — |
| 7 | INC-8 | Shortcut | docs/gui-guide.md:163,206 | NONE | Ctrl+S verified | — |
| 8 | INC-9 | Range | docs/gui-guide.md:794 | NONE | ion range claims verified (setRange unverified) | — |
| 9 | MISS-1 | Missing | docs/gui-guide.md Interface section | MEDIUM | "Hydrate Structure" source option undocumented | Add Source Selection subsection |
| 10 | MISS-2 | Missing | docs/gui-guide.md:884-890 | MEDIUM | `__GLX_VENDOR_LIBRARY_NAME=mesa` auto-fix undocumented | Add note |
| 11 | MISS-3 | Missing | docs/gui-guide.md:21 | LOW | `.sh`/`.bat` launchers not in gui-guide | Optional one-liner |
| 12 | MISS-4 | Router | entry.py vs README | NONE | router docs verified | — |
| 13 | MISS-5 | Screenshot | docs/images/hydrate-panel.png | LOW | pre-v4.7 screenshot, no per-cage rows | Regenerate |
| 14 | STALE-1 | Prior scan | DOC-G5 | INFO | screenshot mismatch resolved | Close |
| 15 | STALE-2 | Version | docs/gui-guide.md:40 | INFO | version note verified | — |
| 16 | STALE-3 | Version | docs/gui-guide.md:182 | INFO | version note verified | — |
| 17 | STALE-4 | Phases | docs/gui-guide.md:82 | NONE | 8+4 split verified | — |
| 18 | STALE-5 | Tree | README.md:404-421 | LOW | output/guest_info.py omitted | Optional |
| 19 | CITE-1 | Citation | main_window.py:2071,2073 | LOW | Ice V/VII no citation (DOC-G8) | Add Lobban/Hemley |
| 20 | CITE-2 | Citation | ion_panel.py:324 | LOW | Madrid2019 not in tooltip (DOC-G12) | Append to tooltip |
| 21 | CITE-3 | Citation | README.md:383,387 | LOW | Madrid2019 DOI `.1392` vs prior `.1394` fix | Verify + standardize [NEEDS VERIFICATION] |
| 22 | CITE-4 | Wording | docs/ranking.md:11 | LOW | "Penalizes" vs "Measures" (NEW-4) | Align with principles.md |
| 23 | CITE-5 | Citation | main_window.py:2061 | INFO | Ice Ih "no citation" but density from IAPWS R10-06 | Optional add |
| 24 | CITE-6 | Citation | main_window.py:1961 | INFO | Non-Ih density source uncited in GUI | Optional note |
| 25 | HEAD-1 | VTK | QUICKICE_FORCE_VTK | NONE | verified consistent | — |
| 26 | HEAD-2 | VTK | QT_QPA_PLATFORM=offscreen | LOW | in AGENTS.md only, not user guide | Optional dev note |
| 27 | HEAD-3 | VTK | ROADMAP TEST-06 | LOW | AGENTS.md "deferred" vs REQUIREMENTS.md "Complete" | Reconcile |
| 28 | HEAD-4 | VTK | 6 viewer files | LOW | VTK-DUP tech debt (not doc) | — |
| 29 | HEAD-5 | VTK | mesa GLX auto-set | (see MISS-2) | — | — |
| 30 | HEAD-6 | VTK | 6 viewers documented | NONE | verified | — |
| 31 | FLOW-1 | CP-01 | InterfaceStructure duck-typing | NONE | docs abstract correctly | — |
| 32 | FLOW-2 | CP-01 | HydrateWorker QThread | NONE | verified | — |

**New actionable findings (2026-07-15):** INC-2, INC-3 (re-opened/inverted), INC-4, MISS-1, MISS-2, CITE-3 (DOI discrepancy), plus 2 carry-over citations (CITE-1, CITE-2) and 1 carry-over wording (CITE-4) unresolved since 2026-06-18.

**Resolved since prior scan:** DOC-G5 screenshot mismatches (INC-1/STALE-1).

---

*GUI Documentation Cross-Check: 2026-07-15*
*Read-only analysis. No code run, no modifications.*
*Delta from: .planning/code_analysis/20260618_documentation_crosscheck_gui.md*
