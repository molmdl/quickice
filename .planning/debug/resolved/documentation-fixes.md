---
status: resolved
trigger: "Investigate and fix SIX documentation/citation-label issues (scancode Group 9): CLI #1, CLI #2, CLI #3, CLI I1, GUI MISS-1, GUI MISS-2. GUI CITE-3 is RESOLVED (no edit needed)."
created: 2026-07-19T00:00:00Z
updated: 2026-07-19T00:00:00Z
---

## Current Focus

hypothesis: All six findings are CONFIRMED by reading current code/docs. CLI #3 is a
  real BUG (main.py:139 produces a destination filename that differs from the .top
  #include reference and all other 20+ references in the codebase). Applying fixes
  in 6 atomic commits per the plan.
test: read each referenced file:line, confirm the discrepancy, apply the planned fix.
expecting: each fix aligns the doc/label to the authoritative code state; pytest
  shows no new regressions (docs changes + 2 source-comment fixes).
next_action: apply CLI #1 fix (docs/cli-reference.md:149 exit code 1 -> 0).

## Symptoms

expected: Docs and source citation labels match the authoritative code behavior.
actual:
  - CLI #1: docs/cli-reference.md:149 says exit code 1 for --no-overwrite; code returns 0.
  - CLI #2: README.md:229 prose + :222-226 example swap solutes/custom vs code order.
  - CLI #3: main.py:139 uses tip4p_ice.itp (underscore) as DESTINATION filename for
    shutil.copy; all other 20+ refs (incl. .top #include) use tip4p-ice.itp (hyphen).
  - CLI I1: types.py:32-38 has TIP4P-ICE label on the TIP4P/2005 DOI (reversed).
  - GUI MISS-1: docs/gui-guide.md doesn't document the "Hydrate Structure" source option.
  - GUI MISS-2: docs/gui-guide.md doesn't document the remote-OpenGL mesa config.
errors: none (docs/label issues, not runtime errors).
reproduction: read the cited file:line and compare to the authoritative code.
started: pre-existing doc/label drift.

## Confirmation Evidence (current state — line numbers re-verified)

### CLI #1 — CONFIRMED
- docs/cli-reference.md:149 (current): "If files exist, the pipeline exits with
  code 1."
- quickice/cli/pipeline.py:182-193 (current): `if getattr(self.args, 'no_overwrite',
  False): ... if existing_files: ... return 0` — returns 0 (success on skip), NOT 1.
- Fix: change "exits with code 1" -> "exits with code 0 (skip)".

### CLI #2 — CONFIRMED
- README.md:222-226 (current example block) shows:
  `CH4_H` (guest) -> `THF_L` (solute, Tab 4) -> `CUSTOM_MOL_1` (custom, Tab 3) ->
  `NA`/`CL` (ions).
  This puts solutes BEFORE custom.
- README.md:229 (current prose): "Order: SOL -> hydrate guests -> solutes -> custom
  molecules -> ions" — same swap.
- quickice/output/gromacs_writer.py:2841 (current comment): "[ molecules ] section -
  written in ORDER: SOL, guest, custom, solute, NA, CL". Code at :2849-2872 writes
  in exactly that order: SOL -> guest -> custom -> solute -> NA -> CL.
- Fix: swap lines 223-224 in the example (CUSTOM_MOL_1 before THF_L) AND fix prose
  to "SOL -> hydrate guests -> custom molecules -> solutes -> ions".

### CLI #3 — CONFIRMED AS A REAL BUG (not just a display label)
- quickice/main.py:139 (current): `itp_filename = "tip4p_ice.itp"` (UNDERSCORE).
  Used at :140-141 as the DESTINATION for `shutil.copy(itp_source, itp_filepath)`.
  So main.py copies data/tip4p-ice.itp (hyphen source) -> output/tip4p_ice.itp
  (underscore destination).
- quickice/cli/itp_helpers.py:314 (current): `tip4p_dest = output_dir / "tip4p-ice.itp"`
  (HYPHEN) — the pipeline path. :316 appends "tip4p-ice.itp" to the copied list.
- quickice/output/gromacs_writer.py:1080-1093 (current): `get_tip4p_itp_path()` returns
  `data/tip4p-ice.itp` (hyphen) — the actual data file.
- quickice/data/tip4p-ice.itp (current): EXISTS (hyphen form, 1368 bytes).
- quickice/gui/export.py:391,1120 (current comments): `# Copy water .itp file (must
  match the #include "tip4p-ice.itp" in .top file)` — confirms the .top #include
  references the HYPHEN form. If main.py produces the UNDERSCORE form, GROMACS
  grompp would fail to find the included file.
- Grep across quickice/: 20+ references to `tip4p-ice.itp` (hyphen); ONLY main.py:139
  uses `tip4p_ice.itp` (underscore). This is the ONLY outlier.
- quickice/entry.py:186,194 (current): both CLI routes call `from quickice.main import
  main as cli_main` -> `cli_main()`. So main.py:139 is REACHABLE on the --gromacs
  export path (main.py:137-145). This is a live bug, not dead code.
- Fix: change main.py:139 from `"tip4p_ice.itp"` to `"tip4p-ice.itp"` (hyphen) to match
  the data file, the pipeline path, and the .top #include.
- Note (out of scope): README.md:210-213 table also lists `tip4p_ice.itp` (underscore)
  for Tabs 2-5. This is the same class of inconsistency but is NOT in the plan's
  CLI #2 (README:222-229) or CLI #3 (main.py:139) scope. Leaving as a deferred
  observation.
- Smoke test: assert `quickice/data/tip4p-ice.itp` exists.

### CLI I1 — CONFIRMED
- quickice/structure_generation/types.py:32-38 (current):
  Line 32-34: "Reference: Abascal, J. L. F., Sanz, E., Garcia Fernandez, R., & Vega,
  C. (2005). A potential model for the phase diagram of TIP4P water. J. Chem. Phys.
  122, 234511. DOI: 10.1063/1.1931662"  <- generic label, no model name.
  Line 36-38: "For TIP4P-ICE specifically: Abascal, J. L. F., & Vega, C. (2005). A
  general purpose model for the condensed phases of water: TIP4P/2005. J. Chem.
  Phys. 123, 234505. DOI: 10.1063/1.2121600"  <- labeled TIP4P-ICE but title
  self-identifies as TIP4P/2005.
- AGENTS.md: "Never hardcode TIP4P-ICE parameters. ... the original literature
  (Abascal et al. 2005, DOI: 10.1063/1.1931662)." So 10.1063/1.1931662 = TIP4P-ICE.
- README.md:236-239 (current) confirms: 10.1063/1.1931662 is "TIP4P/Ice" (title
  "A potential model for the study of ices and amorphous water: TIP4P/Ice").
- The labels are REVERSED: "For TIP4P-ICE specifically" is on the 10.1063/1.2121600
  line (which is actually TIP4P/2005).
- Fix (per plan: swap LABELS only, do NOT introduce new references):
  - Line 32: "Reference:" -> "For TIP4P-ICE specifically:"
  - Line 36: "For TIP4P-ICE specifically:" -> "For TIP4P/2005:"
  - DOIs, titles, and volume/issue stay unchanged.
- Deferred observation (out of scope): line 33 title "A potential model for the
  phase diagram of TIP4P water" doesn't match README's title for the same DOI
  ("A potential model for the study of ices and amorphous water: TIP4P/Ice").
  Per the plan's "only relabel" instruction, I am NOT changing titles — only
  swapping the descriptive label prefixes. The title discrepancy is a separate
  pre-existing issue.
- Grep test: assert the TIP4P-ICE label is near the 10.1063/1.1931662 line.

### GUI MISS-1 — CONFIRMED
- quickice/gui/interface_panel.py:258 (current): `self.source_combo.addItems(["Ice
  Candidate", "Hydrate Structure"])`. Tooltip at :259-263 and HelpIcon at :265-268
  already explain: "Ice Candidate uses existing ice structures. Hydrate Structure
  generates hydrate lattices (sI, sII, sH) directly without going to Tab 1."
- docs/gui-guide.md:355-366 (current "Interface Construction (Tab 2)" section):
  Prerequisites say "Generate ice candidates in Tab 0 ... before using Tab 2."
  This assumes the "Ice Candidate" source only; no mention of "Hydrate Structure".
- Fix: add a "### Source Selection" subsection in the Interface Construction section
  documenting both source options and when to use each.

### GUI MISS-2 — CONFIRMED (line shifted 2139 -> 2259)
- quickice/gui/main_window.py:2259 (current): `def _configure_opengl_for_remote():`
  (line shifted from the plan's :2139 — git log shows prior groups added code above).
- :2271-2283: checks `DISPLAY` env var; for remote displays (not starting with ":"),
  sets `os.environ['__GLX_VENDOR_LIBRARY_NAME'] = 'mesa'`.
- :2262-2267 docstring: "Fixes VTK segfault when running via SSH X11 forwarding. The
  NVIDIA GLX library crashes with indirect rendering... Mesa GLX handles indirect
  rendering correctly. This only applies when running remotely (DISPLAY set, no
  local GPU)."
- :2297: called from `run_app()` before creating QApplication.
- docs/gui-guide.md:18-24 (current "Launching the GUI" section): only mentions
  `python -m quickice.gui` and the binary distribution; no remote/headless note.
- Fix: add a "### Remote and Headless OpenGL" subsection after "Launching the GUI"
  documenting the env var and when it applies.

## Resolution

root_cause: Six independent doc/label drifts: (1) exit code text, (2) molecule
  order prose+example, (3) itp filename underscore-vs-hyphen (real bug — produces
  a file the .top won't #include), (4) reversed citation labels, (5) undocumented
  source option, (6) undocumented remote-OpenGL config.
fix:
  - CLI #1 (commit e6236646): docs/cli-reference.md:149 "exits with code 1"
    -> "exits with code 0 (skip)".
  - CLI #2 (commit a1483198): README.md:222-226 example block swapped
    CUSTOM_MOL_1/THF_L; :229 prose "solutes -> custom" -> "custom -> solutes".
  - CLI #3 (commit 9fc88ac3): quickice/main.py:139 "tip4p_ice.itp" (underscore)
    -> "tip4p-ice.itp" (hyphen) + explanatory comment. Added 2 smoke tests.
  - CLI I1 (commit 442f116b): quickice/structure_generation/types.py:32,36
    label prefixes swapped ("For TIP4P-ICE specifically:" now on
    10.1063/1.1931662; "For TIP4P/2005:" now on 10.1063/1.2121600). DOIs/titles
    unchanged. Added 1 grep test.
  - GUI MISS-1 (commit 474f0037): docs/gui-guide.md — new "### Source Selection"
    subsection in Interface Construction (Tab 2) documenting both source
    options.
  - GUI MISS-2 (commit 4a625487): docs/gui-guide.md — new "### Remote and
    Headless OpenGL" subsection after Launching the GUI, documenting
    __GLX_VENDOR_LIBRARY_NAME=mesa and QT_QPA_PLATFORM=offscreen.
verification:
  - New doc tests (tests/test_scancode_bugs_documentation.py): 3/3 PASSED.
    Verified both the CLI #3 and CLI I1 tests FAIL on the pre-fix state
    (git stash) and PASS after the fix — the tests genuinely catch the bugs.
  - Directly-affected tests (test_gromacs_molecule_ordering,
    test_gromacs_moleculetype_names, test_cli_integration, test_entry_point):
    55 passed, 2 failed. The 2 failures are the pre-existing
    test_version_shows_version (assert "4.5.0" but version is "4.7.0").
  - Full non-GUI suite (excluding 35 GUI/Qt/VTK-touching test files,
    QT_QPA_PLATFORM=offscreen, --timeout=120): 1430 passed, 1 failed in
    161s. The 1 failure is the same pre-existing test_version_shows_version
    (the second instance is in test_entry_point.py, which was excluded from
    this run as a GUI-touching file but verified to fail identically in the
    directly-affected run).
  - Pre-existing failures confirmed NOT caused by this change: my 6 commits
    touched only README.md, docs/cli-reference.md, docs/gui-guide.md,
    quickice/main.py, quickice/structure_generation/types.py,
    tests/test_scancode_bugs_documentation.py. The version "4.7.0" lives in
    quickice/cli/parser.py:386 and quickice/__init__.py:3 — NOT touched by
    any of my commits. The version was bumped to 4.7.0 in a prior commit;
    the tests asserting "4.5.0" are stale (pre-existing).
  - gmx IS available on PATH (GROMACS 2023.5-plumed_2.9.3). Not exercised by
    these doc/label fixes (no .top/.gro output changed except the destination
    filename of the ice-candidate .itp, which now matches the .top #include).
files_changed:
  - docs/cli-reference.md (CLI #1)
  - README.md (CLI #2)
  - quickice/main.py (CLI #3)
  - tests/test_scancode_bugs_documentation.py (CLI #3 + CLI I1 tests, new file)
  - quickice/structure_generation/types.py (CLI I1)
  - docs/gui-guide.md (GUI MISS-1 + GUI MISS-2)
commits:
  - e6236646 docs(scancode): fix --no-overwrite exit code (CLI #1)
  - a1483198 docs(scancode): fix molecule order in README (CLI #2)
  - 9fc88ac3 fix(scancode): align tip4p-ice.itp filename (CLI #3)
  - 442f116b docs(scancode): fix reversed TIP4P-ICE/TIP4P-2005 citation labels (CLI I1)
  - 474f0037 docs(scancode): document Hydrate Structure source option (GUI MISS-1)
  - 4a625487 docs(scancode): document remote OpenGL mesa config (GUI MISS-2)
deferred_observations (out of scope, not fixed):
  - README.md:210-213 table lists "tip4p_ice.itp" (underscore) for Tabs 2-5.
    Same class of inconsistency as CLI #3 but NOT in the plan's CLI #2
    (README:222-229) or CLI #3 (main.py:139) scope. The code produces
    "tip4p-ice.itp" (hyphen) for all tabs.
  - quickice/structure_generation/types.py:33 title "A potential model for
    the phase diagram of TIP4P water" does not match README.md:237 title
    for the same DOI 10.1063/1.1931662 ("A potential model for the study of
    ices and amorphous water: TIP4P/Ice"). Per the plan's "only relabel"
    instruction, titles were NOT changed; this is a separate pre-existing
    citation-title issue.
