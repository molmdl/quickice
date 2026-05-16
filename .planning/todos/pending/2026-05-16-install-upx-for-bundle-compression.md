---
created: 2026-05-16T12:30
title: Install UPX for bundle compression
area: tooling
files:
  - quickice-gui.spec:42,55
  - scripts/build-linux.sh
---

## Problem

PyInstaller bundle is 871 MB (289 MB compressed). The spec file already has `upx=True` configured, but UPX binary is not installed on the system, so the bundle was built without UPX compression.

Expected savings: 80-130 MB with no code changes required.

## Solution

1. Download UPX binary from GitHub releases:
   ```
   wget https://github.com/upx/upx/releases/download/v4.2.2/upx-4.2.2-amd64_linux.tar.xz
   tar -xf upx-4.2.2-amd64_linux.tar.xz
   cp upx-4.2.2-amd64_linux/upx ~/bin/
   ```

2. Verify: `upx --version`

3. Rebuild bundle: `./scripts/build-linux.sh`

4. Test executable and verify size reduction

**Note:** Per project policy, installation must be done manually by user.

**Reference:** Quick Task 023 investigation - `.planning/quick/023-check-upx-compression-feasibility/023-SUMMARY.md`
