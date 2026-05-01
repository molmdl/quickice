# Prompt 5: Packaging Optimization

**Workflow:** `/gsd-plan-phase`
**Priority:** LOW

---

## Prompt to Paste

```
Phase: Optimize PyInstaller Bundle Size

Goal: Reduce from ~700MB to ~500-550MB

Changes to quickice-gui.spec:
1. Add EXCLUDES list: pytest, gsw, git_filter_repo, pyinstaller deps
2. Add VTK to collect_all packages
3. Add collect_submodules('genice2.plugin') for hidden imports
4. Set optimize=2 in Analysis
5. Add upx_exclude for VTK binaries

Test all features after build:
- All ice phases
- All interface modes
- Hydrate generation
- Ion insertion
- All export formats
- 3D viewer

Reference: .planning/code_analysis/PACKAGING_2026-05-02.md
```
