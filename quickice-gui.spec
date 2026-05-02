# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Packages to exclude (development-only and unused)
EXCLUDES = [
    # Testing
    'pytest', 'iniconfig', 'pluggy', 'pygments', '_pytest',
    
    # PyInstaller (build-time only)
    'pyinstaller', 'altgraph', 'pyinstaller_hooks_contrib',
    
    # Unused packages
    'gsw',  # Gibbs Sea Water - not used
    'git_filter_repo',  # Git tool - not used
]

# Collect all data files, binaries, and hidden imports from packages
datas = [('quickice/data', 'quickice/data')]
binaries = []
hiddenimports = []

# Collect runtime dependencies
RUNTIME_PACKAGES = [
    'vtk', 'vtkmodules',
    'iapws', 'genice2', 'genice_core',
    'matplotlib', 'scipy', 'numpy', 
    'shapely', 'networkx', 'spglib',
]

for pkg in RUNTIME_PACKAGES:
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception as e:
        print(f"Warning: Could not collect {pkg}: {e}")

# Add genice2 plugin hidden imports
hiddenimports += collect_submodules('genice2.plugin')

a = Analysis(
    ['quickice/gui/__main__.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='quickice-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'vtk*.so',
        'libpython*.so',
    ],
    name='quickice-gui',
)
