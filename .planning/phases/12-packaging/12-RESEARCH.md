# Phase 12: Packaging & Distribution - Research

**Researched:** 2026-04-04
**Domain:** Python application packaging, standalone executable creation, license compliance
**Confidence:** HIGH

## Summary

This research covers PyInstaller packaging for PySide6 + VTK GUI applications, license compatibility for bundling LGPL-3.0 Qt libraries with MIT-licensed projects, and dependency version pinning best practices.

PyInstaller is the standard tool for creating standalone Python executables, with mature support for Qt (PySide6) applications through built-in hooks. VTK bundling requires attention to plugins and data files. The key licensing consideration is Qt's LGPL-3.0 status, which requires proper attribution and allows dynamic linking bundling.

**Primary recommendation:** Use PyInstaller with default one-dir mode, rely on auto-discovery for dependencies, include LGPL-3.0 attribution for Qt, and pin exact dependency versions in environment.yml.

## Standard Stack

The established tools for Python application packaging:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyInstaller | 6.x | Creates standalone executable | Most mature, best Qt/VTK support, active maintenance |
| PySide6 | 6.11.0 | Qt GUI framework | Official Qt bindings, LGPL-3.0 compatible for bundling |
| VTK | 9.6.1 | 3D visualization | BSD-3 licensed, MIT-compatible |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| conda | 25.x | Environment management | Project already uses environment.yml |
| GitHub Actions | N/A | CI/CD for Windows build | Cross-platform builds without local Windows |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyInstaller | Nuitka | Compiles to C, harder to debug, less mature Qt support |
| PyInstaller | cx_Freeze | Less active development, fewer hooks |
| One-dir | One-file | One-file is slower startup, extraction on each run |
| PyInstaller | AppImage (Linux) | AppImage is Linux-only, adds complexity |

**Installation:**
```bash
conda activate quickice
pip install pyinstaller
```

## Architecture Patterns

### Recommended Project Structure
```
dist/
├── quickice-gui           # Main executable
├── _internal/             # Bundled libraries (PyInstaller default)
│   ├── PySide6/           # Qt libraries
│   ├── vtkmodules/        # VTK modules
│   └── ...                # Other dependencies
├── licenses/              # License attribution (added manually)
│   ├── LICENSE            # MIT license
│   └── LGPL-3.0.txt        # Qt license
└── docs/                   # Essential documentation
    ├── README.md
    └── gui-guide.md
```

### Pattern 1: PyInstaller One-Dir Build
**What:** Default mode creates executable + `_internal/` folder with all dependencies
**When to use:** Recommended for all cases - easier debugging, faster startup, allows library replacement (LGPL compliance)
**Example:**
```bash
# Source: PyInstaller documentation
pyinstaller --name quickice-gui \
    --onedir \
    --windowed \
    --collect-all vtk \
    quickice/gui/__main__.py
```

### Pattern 2: Entry Point Specification
**What:** Use `python -m quickice.gui` style entry point for cleaner invocation
**When to use:** When package has `__main__.py` in a submodule
**Example:**
```python
# quickice/gui/__main__.py
from .main import main

if __name__ == "__main__":
    main()
```
```bash
# Build command
pyinstaller --name quickice-gui \
    --onedir \
    --windowed \
    quickice/gui/__main__.py
```

### Pattern 3: Spec File for Complex Builds
**What:** Use .spec file for repeatable builds with custom configuration
**When to use:** When build requires multiple data files or custom hooks
**Example:**
```python
# quickice-gui.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['quickice/gui/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('LICENSE', 'licenses'),
        ('LGPL-3.0.txt', 'licenses'),
        ('README.md', 'docs'),
        ('docs/gui-guide.md', 'docs'),
    ],
    hiddenimports=[
        'vtkmodules.all',
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='quickice-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # GUI mode
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx_exclude=[],
    upx=False,
    upx_include=[],
    name='quickice-gui',
)
```

### Anti-Patterns to Avoid
- **One-file mode for Qt applications:** Slower startup, extraction on each run, harder to replace libraries for LGPL compliance
- **Hardcoding paths:** Use `sys._MEIPASS` for bundled resource paths in frozen mode
- **Missing VTK plugins:** VTK requires `--collect-all vtk` to include rendering plugins
- **Forgetting windowed mode:** Use `--windowed` (macOS/Linux) or `--noconsole` (Windows) for GUI apps

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Resource path handling | Custom `__file__` logic | `sys._MEIPASS` check | PyInstaller provides this for bundled resources |
| Qt plugin bundling | Manual file copying | PyInstaller hooks | Built-in hooks handle platform-specific plugins |
| VTK module collection | Manual binary inclusion | `--collect-all vtk` | VTK has complex plugin dependencies |
| Version extraction | Custom parsing | `importlib.metadata.version()` | Standard library solution |
| GLIBC version check | Shell script wrapper | Document in README | Simpler, users can verify with `ldd --version` |

**Key insight:** PyInstaller's built-in hooks handle most Qt/VTK complexity automatically. Manual binary collection is error-prone.

## License Compatibility Analysis

### License Summary Table
| Library | License | Compatible with MIT | Requires Attribution | Bundling Notes |
|---------|---------|-------------------|---------------------|----------------|
| PySide6 6.11.0 | LGPL-3.0/GPL-2.0/GPL-3.0 | Yes (dynamic linking) | Yes - must include LGPL-3.0 text | Dynamic linking allows bundling |
| VTK 9.6.1 | BSD-3-Clause | Yes | Yes - include copyright notice | Permissive, no restrictions |
| NumPy 2.4.3 | BSD-3-Clause | Yes | Yes - include copyright notice | Permissive, no restrictions |
| SciPy | BSD-3-Clause | Yes | Yes - include copyright notice | Permissive, no restrictions |
| Matplotlib | PSF-based (BSD-like) | Yes | Yes - include license text | Permissive, no restrictions |
| GenIce2 | MIT | Yes | Yes - include license text | Same license, fully compatible |
| NetworkX | BSD-3-Clause | Yes | Yes - include copyright notice | Permissive, no restrictions |
| Click | BSD-3-Clause | Yes | Yes - include copyright notice | Permissive, no restrictions |

### LGPL-3.0 Compliance Requirements
For bundling Qt/PySide6 (LGPL-3.0) with MIT-licensed QuickIce:

1. **Include LGPL-3.0 license text** in distribution `licenses/` folder
2. **State that Qt is used** - Add attribution in README or LICENSE file
3. **Allow library replacement** - One-dir mode satisfies this (users can replace `.so`/`.dll` files)
4. **Provide notice** - Include text like: "This software uses Qt framework (https://qt.io) under LGPL-3.0 license"

**Critical:** One-file mode may NOT satisfy LGPL requirements because users cannot easily replace the dynamically linked libraries. Use one-dir mode for LGPL compliance.

### Recommended License Files
```
licenses/
├── LICENSE              # QuickIce MIT license
├── LGPL-3.0.txt         # Qt/PySide6 license
└── THIRD-PARTY-NOTICES  # Combined notices for all dependencies
```

## Common Pitfalls

### Pitfall 1: VTK Rendering Plugins Missing
**What goes wrong:** Black screen or "no OpenGL context" errors when VTK widgets initialize
**Why it happens:** VTK plugins for rendering are in separate directories not detected by default import analysis
**How to avoid:** Use `--collect-all vtk` flag
**Warning signs:** `ImportError` for `vtkRenderingOpenGL2` or similar modules

### Pitfall 2: Qt Platform Plugins Missing
**What goes wrong:** Application fails to start with "could not find the Qt platform plugin" error
**Why it happens:** Qt platform plugins (xcb, cocoa, windows) are platform-specific and sometimes missed
**How to avoid:** PyInstaller's PySide6 hooks usually handle this, but verify `_internal/PySide6/plugins/platforms/` exists
**Warning signs:** Empty plugins directory, missing `.so` files on Linux

### Pitfall 3: GLIBC Version Incompatibility
**What goes wrong:** "version `GLIBC_X.XX' not found" when running on older Linux
**Why it happens:** Building on newer Linux links against newer glibc; target must have equal or newer glibc
**How to avoid:** Build on oldest supported Linux (Ubuntu 20.04 for glibc 2.31)
**Warning signs:** `ImportError: libpthread.so.0: version `GLIBC_2.34' not found`

### Pitfall 4: Missing Data Files
**What goes wrong:** Application can't find icons, styles, or other resources
**Why it happens:** PyInstaller only collects Python modules by default; data files need explicit inclusion
**How to avoid:** Add to `datas=[]` in spec file or use `--add-data` flag
**Warning signs:** Missing icons, default Qt styling, "file not found" errors

### Pitfall 5: Console Window Appears
**What goes wrong:** Black console window appears alongside GUI on Windows
**Why it happens:** Default PyInstaller mode is console application
**How to avoid:** Use `--windowed` (macOS/Linux) or `--noconsole` (Windows) flags
**Warning signs:** CMD window visible when running GUI

## Code Examples

### Basic PyInstaller Build Command
```bash
# Source: PyInstaller documentation
# Build for Linux (one-dir mode)
pyinstaller \
    --name quickice-gui \
    --onedir \
    --windowed \
    --collect-all vtk \
    --hidden-import PySide6.QtCore \
    --hidden-import PySide6.QtWidgets \
    --hidden-import PySide6.QtGui \
    --add-data "LICENSE:licenses" \
    --add-data "LGPL-3.0.txt:licenses" \
    quickice/gui/__main__.py
```

### Runtime Path Handling for Frozen Apps
```python
# Source: PyInjector documentation
import sys
import os
from pathlib import Path

def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and frozen mode."""
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle
        base_path = Path(sys._MEIPASS)
    else:
        # Running in development
        base_path = Path(__file__).parent.parent
    
    return base_path / relative_path

# Usage
icon_path = get_resource_path("assets/icon.png")
```

### Spec File with All Required Elements
```python
# quickice-gui.spec
# Source: PyInstaller documentation patterns
# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

# Get the project root
project_root = Path(SPECPATH).parent

a = Analysis(
    ['quickice/gui/__main__.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # License files
        (str(project_root / 'LICENSE'), 'licenses'),
        (str(project_root / 'LGPL-3.0.txt'), 'licenses'),
        # Documentation
        (str(project_root / 'README.md'), 'docs'),
        (str(project_root / 'docs' / 'gui-guide.md'), 'docs'),
    ],
    hiddenimports=[
        # VTK modules
        'vtkmodules.all',
        'vtkmodules.vtkCommonCore',
        'vtkmodules.vtkRenderingOpenGL2',
        # PySide6 modules (usually auto-detected but explicit is safer)
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce bundle size
        'tkinter',
        'unittest',
        'test',
        'tests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='quickice-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disable UPX for stability
    console=False,  # GUI mode - no console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='quickice-gui',
)
```

### Creating Release Tarball
```bash
# Source: Standard Linux packaging practices
cd dist/
tar -czf quickice-v2.0.0-linux-x86_64.tar.gz quickice-gui/

# Verify contents
tar -tzf quickice-v2.0.0-linux-x86_64.tar.gz | head -20
```

## Dependency Version Pinning

### Current environment.yml Analysis
The project currently uses:
- `pyside6>=6.9.3` (minimum version, not pinned)
- `vtk>=9.5.2` (minimum version, not pinned)
- `numpy==2.4.3` (exact version, good)
- `scipy>=1.8` (minimum version, not pinned)
- `matplotlib>=3.5` (minimum version, not pinned)
- `genice2==2.2.13.1` (exact version, good)

### Recommended Pinning Approach
For reproducibility and security (PACKAGE-03 requirement), pin ALL dependencies:

```yaml
# environment.yml (recommended format)
name: quickice
channels:
  - conda-forge
  - defaults
dependencies:
  # System libraries (pinned for reproducibility)
  - python=3.14.3
  - pyside6=6.11.0
  - vtk=9.6.1
  
  # Pip dependencies with exact versions
  - pip:
      - click==8.3.1
      - cycless==0.7
      - deprecated==1.3.1
      - deprecation==2.1.0
      - genice-core==1.4.3
      - genice2==2.2.13.1
      - graphstat==0.3.3
      - iapws==1.5.4
      - matplotlib==3.10.1
      - methodtools==0.4.7
      - networkx==3.6.1
      - numpy==2.4.3
      - openpyscad==0.5.0
      - pairlist==0.6.4
      - scipy==1.15.3
      - shapely==2.1.1
      - six==1.17.0
      - spglib==2.7.0
      - wirerope==1.0.0
      - wrapt==2.1.2
      - yaplotlib==0.1.3
```

### Creating Locked Environment
```bash
# Export exact versions from current environment
conda env export --from-history > environment.yml

# Or for full lockfile with all transitive dependencies
conda list --explicit > spec-file.txt

# Create environment from locked file
conda create --name quickice --file spec-file.txt
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| One-file builds | One-dir builds | ~2020 | Better LGPL compliance, faster startup |
| Manual binary collection | Built-in hooks | PyInstaller 4.x+ | Automatic Qt/VTK handling |
| `pyinstaller` direct command | Spec files | Best practice | Reproducible builds |
| Version ranges in env.yml | Exact version pinning | 2020s best practice | Security and reproducibility |

**Deprecated/outdated:**
- `py2exe`: No longer maintained, Windows only
- `py2app`: macOS only, less active development
- `cx_Freeze`: Less mature hooks, more manual configuration required

## Open Questions

1. **GLIBC runtime check implementation**
   - What we know: Linux requires checking glibc version compatibility
   - What's unclear: Whether to implement in Python startup or document in README
   - Recommendation: Document in README for simplicity - `ldd --version | head -1`

2. **Bundle size optimization**
   - What we know: Full VTK + Qt bundles can be 300-500MB
   - What's unclear: Whether selective module imports reduce size significantly
   - Recommendation: Accept current size, optimize if users request smaller bundles

## Sources

### Primary (HIGH confidence)
- PyInstaller Documentation - https://pyinstaller.org/en/stable/usage.html (PyInstaller usage, spec files, CLI options)
- NumPy License - https://numpy.org/doc/stable/license.html (BSD-3-Clause)
- VTK PyPI - https://pypi.org/project/vtk/ (BSD-3-Clause)
- PySide6 PyPI - https://pypi.org/project/PySide6/ (LGPL-3.0/GPL-2.0/GPL-3.0)
- GenIce2 PyPI - https://pypi.org/project/genice2/ (MIT)
- SciPy GitHub - https://github.com/scipy/scipy/blob/main/LICENSE.txt (BSD-3-Clause)
- Matplotlib GitHub - https://github.com/matplotlib/matplotlib/blob/main/LICENSE/LICENSE (Matplotlib License)

### Secondary (MEDIUM confidence)
- Qt Licensing Page - https://www.qt.io/licensing (dual licensing model)
- Conda Documentation - https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html (version pinning)

### Tertiary (LOW confidence)
- None - all primary information verified from official sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - PyInstaller is the established standard, well-documented
- Architecture: HIGH - One-dir mode is standard, hooks handle Qt/VTK automatically
- Pitfalls: HIGH - Common issues well-documented in PyInstaller issues and docs
- License compatibility: HIGH - LGPL bundling requirements verified from Qt docs

**Research date:** 2026-04-04
**Valid until:** 2027-04-04 (1 year for stable tools, 3 months for fast-moving dependencies)
