#!/bin/bash

version=$1
#pyinstaller quickice-gui.spec

cd dist/
rm quickice-${version}-linux-x86_64.tar.gz 

mkdir -p package
cp -r quickice-gui package/
cp ../README.md ../README_bin.md package/
cp ../LICENSE package/
mkdir -p package/docs
cp -r ../docs/gui-guide.md ../docs/principles.md ../docs/ranking.md ../docs/images package/docs/
mkdir -p package/licenses
cp ../licenses/*.txt package/licenses/
tar -czf quickice-${version}-linux-x86_64.tar.gz package
rm -r package/
