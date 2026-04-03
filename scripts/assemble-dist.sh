#!/bin/bash
# Assemble distribution tarball for release
# Usage: ./scripts/assemble-dist.sh [version]
#
# Arguments:
#   version - Optional version number (default: 2.0.0)
#
# Prerequisites:
#   - Executable built with ./scripts/build-linux.sh
#   - Screenshots in docs/images/
#
# Output:
#   - quickice-v{version}-linux-x86_64.tar.gz in project root

set -e

VERSION="${1:-2.0.0}"
TARBALL_NAME="quickice-v${VERSION}-linux-x86_64.tar.gz"

echo "=== Assembling QuickIce v${VERSION} Distribution ==="

# Verify executable exists
if [ ! -x "dist/quickice-gui/quickice-gui" ]; then
    echo "ERROR: Executable not found. Run ./scripts/build-linux.sh first"
    exit 1
fi

# Create distribution directory
echo "Creating distribution structure..."
rm -rf dist/package
mkdir -p dist/package
mkdir -p dist/package/docs

# Copy executable and libraries
cp -r dist/quickice-gui dist/package/
cp -r dist/quickice-gui/_internal dist/package/

# Copy essential documentation
cp README.md dist/package/
cp LICENSE dist/package/
cp docs/gui-guide.md dist/package/docs/

# Copy screenshots if they exist
if [ -d "docs/images" ] && [ "$(ls -A docs/images 2>/dev/null)" ]; then
    mkdir -p dist/package/docs/images
    cp -r docs/images/* dist/package/docs/images/
    echo "Included screenshots from docs/images/"
else
    echo "Warning: No screenshots found in docs/images/"
fi

# Copy license files
cp -r licenses dist/package/

# Create tarball
echo "Creating tarball..."
cd dist
tar -czf "$TARBALL_NAME" package/
mv "$TARBALL_NAME" ../
cd ..

# Clean up
rm -rf dist/package

# Report
SIZE=$(du -sh "$TARBALL_NAME" | cut -f1)
echo ""
echo "=== Distribution Complete ==="
echo "Tarball: $TARBALL_NAME"
echo "Size: $SIZE"
echo ""
echo "Contents:"
tar -tzf "$TARBALL_NAME" | head -20
echo "..."
echo ""
echo "Users can extract and run:"
echo "  tar -xzf $TARBALL_NAME"
echo "  ./package/quickice-gui/quickice-gui"
