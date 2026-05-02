---
phase: 008-optimize-pyinstaller-bundle-size
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice-gui.spec
  - quickice/gui/vtk_utils.py
autonomous: true

must_haves:
  truths:
    - "PyInstaller bundle size reduced from ~700MB to ~500-550MB"
    - "All features work after optimization (ice, hydrate, interface, ion, export)"
    - "No development dependencies bundled"
    - "VTK properly collected with all plugins"
  artifacts:
    - path: "quickice-gui.spec"
      provides: "Optimized PyInstaller configuration"
      contains: "EXCLUDES = ["
    - path: "dist/quickice-gui/"
      provides: "Optimized executable bundle"
  key_links:
    - from: "quickice-gui.spec"
      to: "quickice executable"
      via: "pyinstaller build"
      pattern: "pyinstaller quickice-gui.spec"
---

<objective>
Reduce PyInstaller bundle size from ~700MB to ~500-550MB by optimizing exclusions and collection strategy.

Purpose: Improve distribution size and build efficiency without sacrificing functionality
Output: Smaller, optimized executable bundle that passes all feature tests
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/code_analysis/PACKAGING_2026-05-02.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update PyInstaller spec file with optimizations</name>
  <files>quickice-gui.spec</files>
  <action>
    Update `quickice-gui.spec` with the following optimizations:

    1. **Add EXCLUDES list** (after imports):
       ```python
       EXCLUDES = [
           # Testing
           'pytest', 'iniconfig', 'pluggy', 'pygments', '_pytest',
           
           # PyInstaller (build-time only)
           'pyinstaller', 'altgraph', 'pyinstaller_hooks_contrib',
           
           # Unused packages
           'gsw',  # Gibbs Sea Water - not used
           'git_filter_repo',  # Git tool - not used
       ]
       ```

    2. **Add VTK to collect_all packages**:
       Update RUNTIME_PACKAGES to include `'vtk', 'vtkmodules'` at the start.

    3. **Add genice2 plugin hidden imports**:
       Add `hiddenimports += collect_submodules('genice2.plugin')` after the collect_all loop.

    4. **Set optimize=2** in Analysis:
       Add `optimize=2` parameter to Analysis() call.

    5. **Add UPX exclusions** for VTK binaries in COLLECT():
       ```python
       upx_exclude=[
           'vtk*.so',
           'libpython*.so',
       ]
       ```

    Reference the optimized spec file in PACKAGING_2026-05-02.md lines 207-290 for the complete example.
  </action>
  <verify>
    Check that quickice-gui.spec contains:
    - EXCLUDES list with pytest, gsw, git_filter_repo
    - VTK in RUNTIME_PACKAGES
    - collect_submodules('genice2.plugin')
    - optimize=2 in Analysis
    - upx_exclude in COLLECT
  </verify>
  <done>Spec file updated with all optimizations, ready for build testing</done>
</task>

<task type="auto">
  <name>Task 2: Build and test optimized executable</name>
  <files>quickice-gui.spec</files>
  <action>
    Build the optimized executable and test all features:

    1. **Build the executable**:
       ```bash
       pyinstaller quickice-gui.spec --clean
       ```

    2. **Check bundle size**:
       ```bash
       du -sh dist/quickice-gui/
       ```
       Target: ~500-550MB (down from ~700MB)

    3. **Test all features** (launch `./dist/quickice-gui/quickice-gui`):
       - Launch GUI successfully
       - Generate ice structure for each supported phase
       - Generate interface structures (slab, pocket, piece modes)
       - Generate hydrate structures
       - Insert ions into structure
       - Export to GROMACS format (.gro, .top, .itp)
       - Export to PDB format
       - Generate phase diagram
       - Use 3D molecular viewer (rotate, zoom, pan)

    If any feature fails, check for missing hidden imports or dependencies.
  </action>
  <verify>
    - Bundle size is reduced
    - All features work (manual testing checklist)
    - No runtime errors or missing dependencies
  </verify>
  <done>Optimized executable built and all features verified working</done>
</task>

</tasks>

<verification>
- [ ] Spec file contains EXCLUDES list
- [ ] Spec file includes VTK in collect_all
- [ ] Spec file has genice2.plugin hidden imports
- [ ] Spec file has optimize=2
- [ ] Executable builds successfully
- [ ] Bundle size reduced (check du -sh)
- [ ] All features tested and working
</verification>

<success_criteria>
PyInstaller bundle size reduced by ~150-200MB (from ~700MB to ~500-550MB) with all features verified working.
</success_criteria>

<output>
After completion, create `.planning/quick/008-optimize-pyinstaller-bundle-size/008-SUMMARY.md`
</output>
