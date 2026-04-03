# Phase 12: Packaging & Distribution - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver standalone executable(s) with bundled dependencies and verified license compliance. Users receive v2.0.0 release with essential documentation and proper Qt LGPL-3.0 attribution. CLI tooling and additional features remain unchanged — this phase packages the existing GUI application.

</domain>

<decisions>
## Implementation Decisions

### Target Platforms
- Linux: Build locally with PyInstaller (primary target for Phase 12)
- Windows: Provide GitHub Actions workflow in repo, user enables when ready
- macOS: Skip for now, document as future work
- Testing: Verify Linux build only, document testing steps for other platforms

### Distribution Format
- Binary name: `quickice-gui` (matches existing CLI convention)
- Structure: PyInstaller default — `quickice-gui` executable + `_internal/` folder for libraries
- Release packaging: Manual tarball creation (`tar -czf quickice-v2.0.0-linux-x86_64.tar.gz`)
- Version: v2.0.0 for this milestone

### Documentation Bundling
- Essential docs only: README.md, docs/gui-guide.md, LICENSE (MIT), LGPL-3.0.txt
- Include LICENSE and LGPL-3.0.txt in distribution `licenses/` folder
- Licenses: Research all bundled dependencies, include appropriate attribution files (see OpenCode's Discretion)

### Build Process
- Dependency discovery: Full auto-discovery via PyInstaller analysis
- Entry point: Module main — `python -m quickice.gui`
- Build commands: Document in PLAN, no automation script
- Cleanup: Skip automatic cleanup, user cleans manually when needed
- GitHub Actions: Provide workflow file for Windows, not executed in this phase

### Bundle Size
- No size target: Accept whatever PyInstaller produces
- Qt modules: Include all auto-detected modules (WebEngine, Quick, etc. may be included)
- VTK modules: Include all auto-detected modules
- Strip symbols: Do not strip debug symbols from bundled libraries

### OS Requirements Documentation
- Linux: GLIBC 2.28+ (Ubuntu 20.04+, Debian 10+, Rocky 8+)
- Windows: Windows 10/11 64-bit (document in README)
- macOS: Document as not supported in v2.0.0

### OpenCode's Discretion
- License file organization: Research all bundled dependencies (PySide6, VTK, NumPy, SciPy, Matplotlib, GenIce2, etc.) and determine appropriate license inclusion strategy
- GLIBC runtime check: Implement startup check if straightforward, otherwise skip
- Spec file optimization: Use PyInstaller defaults, add explicit excludes only if needed for build errors

</decisions>

<specifics>
## Specific Ideas

- User prefers GitHub Actions for Windows build over local Windows compilation
- Project already on GitHub, can enable Actions when ready
- User wants thorough license compliance research for all bundled dependencies
- Release should be manually packaged tarball, not automated GitHub release

</specifics>

<deferred>
## Deferred Ideas

- macOS build support — future phase
- AppImage format — could revisit if single-file distribution needed
- Size optimization — acceptable if future users request smaller bundles
- Automated GitHub Releases — manual tarball sufficient for now

</deferred>

---
*Phase: 12-packaging*
*Context gathered: 2026-04-03*
