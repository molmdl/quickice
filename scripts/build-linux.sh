#!/bin/bash
# Build Linux standalone executable with PyInstaller
# Usage: ./scripts/build-linux.sh
#
# Prerequisites:
#   - Conda environment 'quickice' activated
#   - PyInstaller installed (pip install -r requirements-dev.txt)
#
# Output:
#   - dist/quickice-gui/quickice-gui (executable)
#   - dist/quickice-gui/_internal/ (bundled libraries)

set -e

echo "=== Building QuickIce v2.1.1 Linux Executable ==="

# Check if in correct conda environment
if [[ "$CONDA_DEFAULT_ENV" != "quickice" ]]; then
    echo "ERROR: Please activate the quickice conda environment first:"
    echo "  source setup.sh"
    exit 1
fi

# Check if PyInstaller is available
if ! command -v pyinstaller &> /dev/null; then
    echo "ERROR: PyInstaller not found. Install dev dependencies:"
    echo "  pip install -r requirements-dev.txt"
    exit 1
fi

# Clean previous build
echo "Cleaning previous build..."
rm -rf build/ dist/

# Build using spec file (includes all data file collections)
echo "Building executable (this takes 5-15 minutes)..."
pyinstaller --clean quickice-gui.spec

# Verify build
if [ -x "dist/quickice-gui/quickice-gui" ]; then
    SIZE=$(du -sh dist/quickice-gui/ | cut -f1)
    echo ""
    echo "=== Build Complete ==="
    echo "Executable: dist/quickice-gui/quickice-gui"
    echo "Size: $SIZE"
    echo ""
    echo "Test with: ./dist/quickice-gui/quickice-gui"
else
    echo "ERROR: Build failed - executable not found"
    exit 1
fi
