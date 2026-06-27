#!/bin/bash
# Double-click this to launch the QuickIce GUI.
# Must sit next to the dist/quickice-gui/ folder (or be in the project root).
# On Linux: chmod +x first, then double-click or right-click → Run.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/quickice-gui/quickice-gui" --gui
