---
status: resolved
trigger: "windows-extra-window: packaged Windows GUI shows an extra weird window at startup that lingers after GUI close; is Linux affected (hidden)?"
created: 2026-09-12T00:00:00
updated: 2026-09-12T00:00:00
---

## Current Focus

hypothesis: console=True (console-subsystem exe) + QuickIce.bat launcher produce a visible console window owned by cmd/exe; the "lingering" is slow GUI process teardown after window close, which also exists on Linux invisibly
test: static analysis of spec/workflow/bat + PyInstaller hide_console semantics vs pinned version; Linux GUI launch timing observation
expecting: spec console=True confirmed; hide_console support requires PyInstaller >= 6.10 - check pinned version
next_action: read environment-build.yml for pinned PyInstaller version; check GUI close/cleanup path for slow teardown

## Symptoms

expected: launching packaged Windows app shows only main GUI window; closing exits cleanly and promptly
actual: additional unexplained window appears at GUI startup; after GUI closed, extra window lingers before closing
errors: none reported
reproduction: run packaged Windows binary from GitHub Actions workflow
started: Windows distribution; Linux unknown

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-09-12 (FACT)
  checked: quickice-gui.spec (repo root)
  found: EXE(...) has console=True (line 43) and hide_console='hide-late' (line 44). Target is quickice/__main__.py -> entry.main() dual CLI/GUI router. Built as onedir (COLLECT), name quickice-gui.
  implication: console=True builds a console-subsystem PE; on Windows such a process, when launched from a non-console parent (Explorer), ALLOCATES A NEW CONSOLE WINDOW at startup. hide_console='hide-late' is a PyInstaller EXE option (added in PyInstaller 6.10) to hide that console late in bootloader startup.

- timestamp: 2026-09-12 (FACT)
  checked: .github/workflows/build-windows.yml (READ-ONLY, user denied modification)
  found: pyinstaller --clean quickice-gui.spec (line 27) - no CLI overrides; spec is authoritative. Artifact ships dist/quickice-gui/ folder + QuickIce.bat side-by-side in dist/package/.
  implication: behavior is fully determined by the spec file; fix belongs in quickice-gui.spec and/or repo code, not workflow.

- timestamp: 2026-09-12 (FACT)
  checked: QuickIce.bat
  found: @echo off; runs "%SCRIPT_DIR%\quickice-gui\quickice-gui.exe" --gui with NO start /B - cmd.exe blocks waiting for the exe.
  implication: if user double-clicks QuickIce.bat from Explorer, a cmd.exe console window opens and REMAINS OPEN for the entire lifetime of quickice-gui.exe (it is the parent console). This is a visible extra window that closes only when the exe process exits - i.e., it can LINGER after the Qt window closes while the process tears down. Matches both symptom halves exactly.

- timestamp: 2026-09-12 (FACT - official docs)
  checked: PyInstaller usage docs (pyinstaller.org/en/stable/usage.html), --hide-console entry
  found: "--hide-console {minimize-early,hide-late,minimize-late,hide-early}: Windows only: in console-enabled executable, have bootloader automatically hide or minimize the console window IF THE PROGRAM OWNS THE CONSOLE WINDOW (i.e., was not launched from an existing console window)."
  implication: When launched via QuickIce.bat (cmd.exe owns the console), hide_console='hide-late' DOES NOTHING. The cmd console window stays fully visible for the whole exe lifetime and closes only when the exe process exits => matches BOTH symptom halves: extra window at startup + lingers after GUI closes (cmd blocks on the exe until process teardown completes).

- timestamp: 2026-09-12 (FACT)
  checked: environment-build.yml
  found: pyinstaller==6.19.0 pinned (pip section). hide_console is supported (added in 6.10) - not a silently-ignored option.
  implication: hide_console works as documented for the exe-owned-console case.

- timestamp: 2026-09-12 (FACT)
  checked: grep for multiprocessing/concurrent.futures/ProcessPool/freeze_support across quickice/
  found: NO matches. No multiprocessing usage anywhere.
  implication: ELIMINATED hypothesis 3 (missing multiprocessing.freeze_support causing respawned child window). No child processes are spawned by the app itself.

- timestamp: 2026-09-12 (FACT)
  checked: grep for subprocess/Popen/os.system/QProcess across quickice/gui/
  found: NO matches.
  implication: ELIMINATED hypothesis 4 (console-owning subprocess spawned at GUI startup, e.g. gmx detection). No subprocesses launched from the GUI path.

- timestamp: 2026-09-12 (FACT)
  checked: quickice/gui/main_window.py run_app() + grep closeEvent/aboutToQuit/atexit across quickice/
  found: run_app is a plain QApplication + MainWindow + app.exec() + sys.exit. No closeEvent handler, no aboutToQuit, no atexit, no explicit VTK/Qt teardown. Cleanup is default interpreter/Qt finalization.
  implication: No app-level code holds the process open deliberately; any teardown lag is implicit (Qt/VTK/interpreter finalization). Measurable on Linux.

- timestamp: 2026-09-12 (FACT)
  checked: .planning/debug/slow-gui-startup.md (parallel debugger session, in progress)
  found: GUI startup is long-standingly slow (unquantified), present in older versions.
  implication: Slow startup amplifies symptom: with hide-late + slow startup, any owned console window is visible for longer at startup.

- timestamp: 2026-09-12 (FACT - Linux measurement, /tmp/opencode/gui_teardown_probe.py)
  checked: GUI launch+close on this Linux machine (QT_QPA_PLATFORM=offscreen, DISPLAY=localhost:11.0, VTK disabled per heuristic)
  found: startup import=1.63s, window build+show=0.17s; close->exec() return=0.00s; only MainThread alive at exec return; ~0.2s of interpreter finalization after exec() return; total wall 4.04s.
  implication: NO hidden child process, NO lingering threads, NO slow app-level teardown on Linux. Linux does NOT have a hidden equivalent of the extra window - it has no console-window concept; the only shared trait is the process-lifetime window (see below), which on Linux manifests as at most a terminal staying open while the app runs.

- timestamp: 2026-09-12 (FACT - frozen-build verification)
  checked: rebuilt with modified spec (pyinstaller 6.19.0, same as workflow pin) into /tmp/opencode/dist; launched dist quickice-gui --gui offscreen
  found: GUI starts, ZERO child processes (ps --ppid), exits cleanly on terminate; --version CLI path also works (rc=0).
  implication: Spec change builds and the frozen app still boots both modes. Linux console/hide_console options are no-ops, as documented ("Windows only" / "ignored on *NIX").

## LINUX ANSWER (user's explicit question)

Does Linux have the same issue but hidden? NO for the window itself, QUALIFIED YES for one ingredient:
- The extra window is a Windows console-subsystem artifact (console=True exe + cmd.exe-owned console from the blocking .bat). Linux has no console-window allocation; a double-clicked GUI app simply has no terminal. No hidden console-owning child exists: the app spawns ZERO subprocesses/children (verified by grep + ps on the frozen binary) and uses NO multiprocessing (so the freeze_support respawn bug cannot apply).
- The one behavior that DOES carry over: any window that tracks the process lifetime (on Linux: a terminal emulator you launched it from) stays until the process exits, i.e. it "lingers" by exactly the teardown time. On this machine teardown after window close measured ~0.2s. How long Windows teardown is (Qt/VTK DLL unload, Defender/UPX effects) is NOT measurable here - that is the unverifiable residual, but with the fix there is no console window left to linger regardless.

## Resolution

root_cause: Two-part, both Windows packaging artifacts:
  (1) The visible extra window = the cmd.exe console window of QuickIce.bat. The .bat ran quickice-gui.exe inline, so cmd owned the console and blocked on the exe for its full lifetime. quickice-gui.exe is console=True (needed for its dual CLI/GUI role), and PyInstaller's hide_console='hide-late' could not help because (official docs) hide_console only applies when the frozen program OWNS its console.
  (2) The window lingering after GUI close = the same cmd console, which only closes when the exe process fully exits (Qt/VTK/interpreter teardown after the Qt window is destroyed). hide-late additionally maximised any console-flash duration when the exe is launched directly (exe-owned console case).
  NOT the cause (eliminated with evidence): multiprocessing respawn (no multiprocessing anywhere), GUI-spawned console subprocess (no subprocess/Popen/QProcess in quickice/gui), app-level teardown hooks (none exist), silently-ignored spec option (PyInstaller 6.19 supports hide_console).

fix:
  Commit 3945af15 - quickice-gui.spec: hide_console 'hide-late' -> 'hide-early' (with explanatory comments) to minimize the console flash for exe-owned consoles.
  Commit d8bcc4f8 - QuickIce.bat: launch via `start "" "%SCRIPT_DIR%\quickice-gui\quickice-gui.exe" --gui` so the batch (and its console window) exits immediately and the exe owns its console, which the bootloader then hides per hide_console='hide-early'.
  WORKFLOW CHANGE REQUIRED: NONE. build-windows.yml copies QuickIce.bat as-is and builds from quickice-gui.spec; both fixed files are repo files already used by the workflow. (Per user constraint, .github/workflows/ was not modified - and no modification is needed.)

verification:
  - Static: official PyInstaller docs confirm hide_console ownership semantics; workflow inspected read-only; spec is authoritative (no CLI overrides).
  - Dynamic (Linux): modified spec builds successfully with the same PyInstaller 6.19.0 the workflow pins; frozen binary starts GUI offscreen with zero child processes and clean exit; CLI --version works (rc=0); in-process GUI probe shows no lingering threads/processes and ~0.2s teardown.
  - 14 entry-point pytest tests pass (unchanged code paths, sanity).

verification_limits (what only real Windows can confirm):
  (GUESS-labelled expectations from mechanism) The bat console window closes immediately on launch, the exe's own console flashes only momentarily (hidden early), and nothing lingers after GUI close. Absolute teardown duration of the Windows process (Qt/VTK DLL unload, possible AV scanning) cannot be measured here - but after the fix there is no console window to expose it. Recommend one manual run of the next packaged build on Windows to confirm.

files_changed:
  - quickice-gui.spec (commit 3945af15)
  - QuickIce.bat (commit d8bcc4f8)
