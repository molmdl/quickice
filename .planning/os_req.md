# Operating System Requirements Analysis

## Executive Summary

The quickice GUI 3D viewer environment requires **GLIBC 2.28+** due to Qt 6.10.2 (PySide6). This makes the application incompatible with older Linux distributions like Ubuntu 18.04 and Linux Mint 19.1.

---

## 1. Dependency Trace Analysis

### 1.1 Environment Overview

| Component | Version | Source |
|-----------|---------|--------|
| Python | 3.14.3 | conda-forge |
| PySide6 | 6.10.2 | conda |
| VTK | 9.5.2 | conda-forge |
| NumPy | 2.4.3 | conda-forge |
| SciPy | 1.17.1 | conda-forge |
| Matplotlib | 3.10.8 | pip |
| Qt | 6.10.2 | bundled with PySide6 |

### 1.2 Key Library GLIBC Requirements

| Library | Max GLIBC | Purpose |
|---------|-----------|---------|
| libQt6Core.so | **2.28** | Qt core functionality |
| libQt6WebEngineCore.so | **2.28** | Web engine (if used) |
| libQt6Gui.so | 2.27 | GUI rendering |
| libQt6Widgets.so | 2.14 | Widget toolkit |
| libvtkRenderingOpenGL2.so | 2.27 | 3D rendering |
| libvtksys.so | 2.17 | VTK system layer |
| libpython3.14.so | 2.10 | Python runtime |
| libstdc++.so.6 | GLIBCXX_3.4.34 | C++ standard library |

### 1.3 GCC Version Requirements

| Symbol | Version | Required by |
|--------|---------|-------------|
| GCC_14.0.0 | 14.x | libstdc++, Python |
| GCC_7.0.0 | 7.x | Various libraries |
| GCC_4.8.0 | 4.8+ | Base compatibility |

---

## 2. OS Compatibility Matrix

### 2.1 Linux Distribution Support

| Distribution | GLIBC Version | Status | Notes |
|--------------|---------------|--------|-------|
| Ubuntu 14.04 | 2.19 | ❌ FAIL | EOL |
| Ubuntu 16.04 | 2.23 | ❌ FAIL | EOL |
| Ubuntu 18.04 / Mint 19.1 | 2.27 | ❌ FAIL | **Primary blocker** |
| **Ubuntu 20.04** | 2.31 | ✅ Works | Minimum recommended |
| **Ubuntu 22.04+** | 2.35+ | ✅ Works | Recommended |
| **Debian 10+** | 2.28 | ✅ Works | Minimum supported |
| **Debian 12** | 2.36 | ✅ Works | Works on user's machine |
| **Rocky/RHEL 8+** | 2.28 | ✅ Works | Works on user's machine |
| **Rocky/RHEL 9+** | 2.34+ | ✅ Works | Recommended |
| CentOS 7 | 2.17 | ❌ FAIL | GLIBC too old |

### 2.2 Root Cause

The primary blocker is **Qt 6.10.2**:
- `libQt6Core.so` uses GLIBC 2.28 symbols (e.g., `gettid`, `copy_file_range`)
- VTK 9.5.2 requires GLIBC 2.27+
- These are compiled into the conda-forge binaries and cannot be downgraded

---

## 3. Qt Licensing Analysis

### 3.1 Current License

```
PySide6 6.10.2: LGPL-3.0-only (conda package)
```

This is the **Qt Community Edition**.

### 3.2 Distribution Rights

| Distribution Method | LGPL-3.0 Compliant? | Requirements |
|---------------------|---------------------|--------------|
| Dynamic linking (PyInstaller default) | ✅ Yes | Include Qt `.so`/`.dll` files separately, provide LGPL license text, users can replace Qt libs |
| Static linking | ⚠️ Restricted | Must provide object files for relinking OR open-source your app under LGPL/GPL |
| Commercial license | ✅ Yes | ~$5,000+/year, no restrictions |

### 3.3 Compliance Checklist for Dynamic Linking

- [ ] Bundle Qt `.so`/`.dll` files separately (replaceable)
- [ ] Include `LGPL-3.0.txt` license file
- [ ] Add copyright notice for Qt/PySide6
- [ ] Document relinking instructions in README
- [ ] Credit Qt Project in application

---

## 4. Cross-Platform Standalone Options

### 4.1 Distribution Methods

| Method | Linux | Windows | macOS | Notes |
|--------|-------|---------|-------|-------|
| PyInstaller folder | ✅ | ✅ | ✅ | Recommended for flexibility |
| PyInstaller --onefile | ✅ | ✅ | ✅ | Single executable, slower startup |
| AppImage | ✅ | - | - | Linux portable |
| .msi installer | - | ✅ | - | Windows installer |
| .app bundle | - | - | ✅ | macOS standard |
| Docker/Singularity | ✅ | ✅ | ✅ | Full isolation, but requires runtime |

### 4.2 Cross-Compilation Feasibility

| Target | Cross-compile from Linux? | Notes |
|--------|---------------------------|-------|
| Linux → Windows | ❌ Not practical | PyInstaller requires native Windows Python + Qt; VTK has Windows-specific OpenGL bindings |
| Windows → Linux | ❌ Not practical | Same reason |
| All platforms | Build on each platform natively | Recommended approach |

### 4.3 Build Strategy

**Recommended: Two separate binaries, built natively**

```
Platform       Build Method           Output
─────────────────────────────────────────────────
Linux          PyInstaller on Linux   .AppImage or folder bundle
Windows        PyInstaller on Windows .exe (--onefile or folder)
```

---

## 5. Windows Build Options

### 5.1 Options for Windows Build (without WSL)

| Option | Effort | Requirements |
|--------|--------|--------------|
| **Windows PC** | Low | Native hardware, install miniconda + env.yml |
| **Windows VM** (VirtualBox) | Medium | VM setup, same as above |
| **GitHub Actions** | Low | GitHub repo, free Windows runners, automated CI/CD |
| **Azure DevOps** | Medium | Similar to GitHub Actions |

### 5.2 GitHub Actions Workflow (Recommended for automation)

```yaml
# .github/workflows/build.yml
jobs:
  build-linux:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - name: Setup Miniconda
        uses: conda-incubator/setup-miniconda@v3
      - name: Build
        run: |
          conda env create -f env.yml
          pip install pyinstaller
          pyinstaller quickice-gui.spec
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: quickice-linux
          path: dist/

  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Miniconda
        uses: conda-incubator/setup-miniconda@v3
      - name: Build
        run: |
          conda env create -f env.yml
          pip install pyinstaller
          pyinstaller quickice-gui.spec
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: quickice-windows
          path: dist/
```

---

## 6. Recommendations for Phase 12

### 6.1 Distribution Strategy

| Priority | Action |
|----------|--------|
| 1 | Build Linux binary with PyInstaller (dynamic linking) |
| 2 | Build Windows binary natively (VM or GitHub Actions) |
| 3 | Document minimum OS requirements (GLIBC 2.28+) |
| 4 | Include LGPL-3.0 license and Qt attribution |

### 6.2 Directory Structure for Release

```
quickice-v1.0.0/
├── quickice-gui          # Linux binary (or .AppImage)
├── quickice-gui.exe      # Windows binary
├── lib/                  # Qt and other shared libraries
│   ├── libQt6Core.so.6
│   ├── libQt6Gui.so.6
│   ├── libQt6Widgets.so.6
│   └── ...
├── licenses/
│   ├── LGPL-3.0.txt
│   ├── LICENSE.txt       # Your project license
│   └── THIRD-PARTY.txt   # All third-party attributions
├── README.md
│   └── Minimum Requirements section:
│       - Linux: GLIBC 2.28+ (Ubuntu 20.04+, Debian 10+, Rocky 8+)
│       - Windows: Windows 10/11 (64-bit)
└── examples/
    └── sample_data/
```

### 6.3 Technical Notes

1. **GLIBC Check**: Add runtime check for GLIBC version on Linux:
   ```python
   import ctypes
   libc = ctypes.CDLL('libc.so.6')
   glibc_version = ctypes.c_char_p()
   libc.gnu_get_libc_version(ctypes.byref(glibc_version))
   if float(glibc_version.value.decode()) < 2.28:
       print("ERROR: Requires GLIBC 2.28+")
   ```

2. **PyInstaller Spec File**: Create optimized spec file with:
   - Exclude unused Qt modules (WebEngine, Quick, etc.) to reduce size
   - Include only required VTK modules
   - Target size: ~300-500MB

3. **AppImage (Linux)**: Consider AppImageTool for single-file Linux distribution:
   ```bash
   pyinstaller --onedir quickice-gui.spec
   appimagetool dist/quickice-gui quickice-gui-x86_64.AppImage
   ```

---

## 7. Summary Table

| Aspect | Finding | Action |
|--------|---------|--------|
| Minimum Linux GLIBC | 2.28 | Document in README, add runtime check |
| Minimum Windows | Windows 10 64-bit | Document in README |
| Qt License | LGPL-3.0 | Include license, use dynamic linking |
| Static linking | Not recommended | Use dynamic linking for LGPL compliance |
| Cross-compile | Not feasible | Build on each platform natively |
| Windows build | VM or GitHub Actions | Automate with CI/CD |
| Distribution | Folder bundle | PyInstaller with replaceable libs |

---

## 8. Files to Create in Phase 12

| File | Purpose |
|------|---------|
| `quickice-gui.spec` | PyInstaller spec file |
| `.github/workflows/build.yml` | CI/CD for automated builds |
| `licenses/LGPL-3.0.txt` | Qt license |
| `licenses/THIRD-PARTY.txt` | All third-party attributions |
| `scripts/check_glibc.py` | Runtime GLIBC version check |
