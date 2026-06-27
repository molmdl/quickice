@echo off
REM Double-click this to launch the QuickIce GUI.
REM Must sit next to the dist\quickice-gui\ folder (or be in the project root).

set "SCRIPT_DIR=%~dp0"
"%SCRIPT_DIR%dist\quickice-gui\quickice-gui.exe" --gui
