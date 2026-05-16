---
phase: quick
plan: 023
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: true
---

<objective>
Investigate UPX compression feasibility for reducing QuickIce bundle size.

Purpose: Determine if UPX can be enabled to reduce the 871 MB bundle size without code changes.
Output: Investigation report with findings and recommendation for user approval.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

## Current Bundle Analysis

**Current sizes:**
- Uncompressed bundle: 871 MB
- Compressed tarball: 289 MB
- Main executable: 29 MB
- Internal libraries: ~842 MB in `_internal/`

**PyInstaller spec status:**
- File: `quickice-gui.spec`
- Lines 42 and 55: `upx=True` already configured
- UPX is already enabled in spec but NOT available on system

**System check:**
- UPX binary: NOT found in PATH
- Result: Bundle was built without UPX compression despite spec setting
</context>

<tasks>

<task type="auto">
  <name>Task 1: Document current state and installation options</name>
  <files></files>
  <action>
Create investigation findings document with:

1. **Current State Summary**
   - Bundle sizes (871 MB uncompressed, 289 MB compressed)
   - Spec already configured with `upx=True`
   - UPX not installed on system

2. **Installation Options**
   - Option A: System package (if available for RHEL/CentOS)
     - Command: `sudo yum install upx` or check EPEL repo
   - Option B: Download binary from GitHub releases
     - URL: https://github.com/upx/upx/releases
     - Extract and add to PATH or copy to ~/bin/

3. **Expected Benefits**
   - Main executable compression: 29 MB → ~17-23 MB (20-40% reduction)
   - Shared library compression in `_internal/`: Significant additional savings
   - Total estimated savings: 80-130 MB (from planning context)
   - No code changes required

4. **Compatibility Notes**
   - UPX is stable and widely used for PyInstaller bundles
   - PyInstaller natively supports UPX compression
   - May slightly increase startup time (decompression overhead)
   - Antivirus software sometimes flags UPX-packed binaries (false positive)

5. **Recommendation**
   - Install UPX (download binary is most reliable)
   - Rebuild bundle with existing spec
   - No spec modifications needed
   - Test executable after rebuild

Do NOT make any changes. Document findings for user review.
  </action>
  <verify>
Check that findings document exists and contains all five sections.
  </verify>
  <done>
Investigation complete. User can review findings and approve UPX installation + rebuild.
  </done>
</task>

</tasks>

<verification>
- [ ] Current state documented (bundle sizes, spec status, UPX availability)
- [ ] Installation options documented (system package vs binary download)
- [ ] Expected benefits documented (savings estimate)
- [ ] Compatibility notes documented
- [ ] Clear recommendation provided
- [ ] NO changes made to code or spec
</verification>

<success_criteria>
Investigation report created with all findings. User can make informed decision about UPX installation and rebuild. No implementation performed.
</success_criteria>

<output>
After completion, create `.planning/quick/023-check-upx-compression-feasibility/023-SUMMARY.md` with investigation findings and recommendation.
</output>
