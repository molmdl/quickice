# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# Collect all data files, binaries, and hidden imports from packages
datas = [('quickice/data', 'quickice/data')]
binaries = []
hiddenimports = []

for pkg in ['iapws', 'genice2', 'genice_core', 'matplotlib', 'scipy', 'numpy', 'shapely', 'networkx', 'spglib']:
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception as e:
        print(f"Warning: Could not collect {pkg}: {e}")

a = Analysis(
    ['quickice/__main__.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['*/tests/*', '*/test/*', '*/docs/*', '*/__pycache__/*', '*/.pytest_cache/*', '*/egg-info/*'],
    noarchive=False,
    optimize=0,
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
    # console=True is required because the same exe serves both --cli and
    # --gui modes (CLI needs stdout/stderr in an existing terminal).
    # hide_console='hide-early' hides the exe-owned console at the earliest
    # bootloader stage on Windows to minimise the console flash when the GUI
    # is launched outside a terminal (double-click / QuickIce.bat via start).
    # NOTE: hide_console only applies when the program OWNS its console; when
    # launched from an existing console (e.g. plain cmd, or QuickIce.bat
    # without `start`), this option has no effect -- QuickIce.bat therefore
    # launches the exe via `start` so the exe owns its console.
    console=True,
    hide_console='hide-early',
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
    upx_exclude=[],
    name='quickice-gui',
)
