@echo off
REM Double-click this to launch the QuickIce GUI.
REM Must sit next to the dist\quickice-gui\ folder (or be in the project root).
REM
REM Uses `start` so that this batch script (and its console window) exits
REM immediately instead of blocking on quickice-gui.exe. While blocked, the
REM batch console belongs to cmd.exe, so PyInstaller's hide_console option
REM cannot hide it (it only hides consoles OWNED by the frozen program),
REM leaving a stray console window visible for the whole GUI session that
REM lingers after the GUI closes while the process tears down.
REM `start` (without /B) starts the exe in its own new console, which the
REM exe owns; the bootloader then hides it via hide_console='hide-early'
REM (see quickice-gui.spec).

set "SCRIPT_DIR=%~dp0"
start "" "%SCRIPT_DIR%\quickice-gui\quickice-gui.exe" --gui
