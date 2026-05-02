# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Packages to exclude (development-only and unused)
EXCLUDES = [
    # Testing frameworks
    'pytest', 'iniconfig', 'pluggy', 'pygments', '_pytest',
    
    # PyInstaller (build-time only)
    'pyinstaller', 'altgraph', 'pyinstaller_hooks_contrib',
    
    # Unused packages
    'gsw',  # Gibbs Sea Water - not used
    'git_filter_repo',  # Git tool - not used
    
    # Test modules (collected by collect_all but not needed at runtime)
    'numpy.tests', 'numpy._pyinstaller.tests', 'numpy.f2py.tests',
    'numpy._core.tests', 'numpy.lib.tests', 'numpy.linalg.tests',
    'numpy.fft.tests', 'numpy.ma.tests', 'numpy.matrixlib.tests',
    'numpy.polynomial.tests', 'numpy.testing.tests', 'numpy.typing.tests',
    'numpy.random.tests',
    'scipy.tests', 'scipy.special.tests', 'scipy.stats.tests',
    'scipy.spatial.tests', 'scipy.spatial.transform.tests',
    'scipy.sparse.tests', 'scipy.linalg.tests', 'scipy.optimize.tests',
    'scipy.integrate.tests', 'scipy.interpolate.tests', 'scipy.io.tests',
    'scipy.ndimage.tests', 'scipy.signal.tests', 'scipy.cluster.tests',
    'networkx.tests', 'networkx.algorithms.tests',
    'networkx.algorithms.approximation.tests', 'networkx.algorithms.assortativity.tests',
    'networkx.algorithms.bipartite.tests', 'networkx.algorithms.centrality.tests',
    'networkx.algorithms.community.tests', 'networkx.algorithms.components.tests',
    'networkx.algorithms.connectivity.tests', 'networkx.algorithms.flow.tests',
    'networkx.algorithms.isomorphism.tests', 'networkx.algorithms.link_analysis.tests',
    'networkx.algorithms.operators.tests', 'networkx.algorithms.shortest_paths.tests',
    'networkx.algorithms.traversal.tests', 'networkx.algorithms.tree.tests',
    'networkx.classes.tests', 'networkx.drawing.tests', 'networkx.generators.tests',
    'networkx.linalg.tests', 'networkx.readwrite.tests',
    'shapely.tests', 'shapely.tests.legacy',
    'matplotlib.tests',
    # scipy unused modules (safe to exclude - no transitive dependencies)
    'scipy.cluster', 'scipy.cluster.tests',
    'scipy.integrate', 'scipy.integrate.tests',
    'scipy.io', 'scipy.io.tests',
    'scipy.ndimage', 'scipy.ndimage.tests',
    'scipy.signal', 'scipy.signal.tests',
    'scipy.stats', 'scipy.stats.tests',
]

# Collect all data files, binaries, and hidden imports from packages
datas = [('quickice/data', 'quickice/data')]
binaries = []
hiddenimports = []

# scipy - only spatial and interpolate (with their transitive dependencies)
hiddenimports += collect_submodules('scipy.spatial')
hiddenimports += collect_submodules('scipy.interpolate')

# Collect runtime dependencies
RUNTIME_PACKAGES = [
    'vtk', 'vtkmodules',
    'iapws', 'genice2', 'genice_core',
    'matplotlib', 'numpy', 
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
