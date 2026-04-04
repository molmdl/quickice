#!/bin/bash

#pyinstaller quickice-gui.spec

cd dist/
rm quickice-v2.0.0-linux-x86_64.tar.gz 

mkdir -p package
cp -r quickice-gui package/
cp ../README.md package/
cp ../LICENSE package/
mkdir -p package/docs
cp ../docs/gui-guide.md package/docs/
mkdir -p package/licenses
cp ../licenses/*.txt package/licenses/
tar -czf quickice-v2.0.0-linux-x86_64.tar.gz package
rm -r package/
