# Codebase Concerns

**Analysis Date:** 2026-05-02

## Tech Debt

**Large File Complexity:**
- Issue: Three files exceed 1000 lines, indicating high complexity and maintenance burden
- Files: 
  - `quickice/output/gromacs_writer.py` (1559 lines)
  - `quickice/gui/main_window.py` (1317 lines)
  - `quickice/output/phase_diagram.py` (1132 lines)
- Impact: Difficult to navigate, test, and maintain; high cognitive load for changes
- Fix approach: Refactor into smaller modules with single responsibilities

**Empty Pass Statements:**
- Issue: Multiple `pass` statements indicate incomplete implementations or silent failures
- Files:
  - `quickice/phase_mapping/lookup.py:294` - Logic flow with no action
  - `quickice/phase_mapping/lookup.py:418` - Exception handler with no action
  - `quickice/structure_generation/hydrate_generator.py:268` - Parse error silently ignored
  - `quickice/output/phase_diagram.py:231` - ITP parsing failure silently ignored
  - `quickice/output/gromacs_writer.py:229,261` - File read failures silently ignored
  - `quickice/gui/phase_diagram_widget.py:79,481,495,565` - Exception handlers with no action
  - `quickice/gui/export.py:122,603` - File copy failures silently ignored
- Impact: Failures may go unnoticed, debugging becomes difficult
- Fix approach: Add logging, raise appropriate exceptions, or document intentional silent handling

**Deprecated Code Patterns:**
- Issue: Heuristic inference of `atoms_per_molecule` is deprecated but still present
- Files: `quickice/structure_generation/water_filler.py:335-359`
- Impact: May produce incorrect results for ambiguous cases; emits DeprecationWarning
- Fix approach: Require explicit `atoms_per_molecule` parameter, remove heuristic in future version

**Hardcoded Values:**
- Issue: Some values are hardcoded with fallback behavior
- Files:
  - `quickice/output/gromacs_writer.py:264-270` - Fallback residue names
  - `quickice/gui/hydrate_renderer.py:11` - Hardcoded radii (documented as adjustable)
- Impact: Values may not match actual ITP files; limited flexibility
- Fix approach: Document hardcoded values, provide configuration options where appropriate

**Legacy Debug Code:**
- Issue: Debug and test files accumulated in non-standard locations
- Files:
  - `tmp/*.py` - 15 debug/analysis scripts (2276 lines total)
  - `.planning/debug/deferred/*.py` - 21 deferred debug scripts
  - `.planning/debug/resolved/*.py` - 13 resolved test scripts
- Impact: Clutters repository, may cause confusion about test location
- Fix approach: Remove resolved debug scripts, integrate useful tests into `tests/`, clean up `tmp/`

## Known Bugs

**Hydrate Water Overlap (FIXED):**
- Symptoms: ~6,500 overlapping water pairs with minimum O-O distance of 0.0286 nm
- Files: `quickice/structure_generation/water_filler.py`
- Trigger: Hydrate-to-interface conversion when hydrate structure covers >=95% of target box
- Workaround: Fix applied in lines 315-324 with tolerance-based tile count calculation
- Verification: Regenerate hydrate/interface structures and check overlaps
- Status: Fixed but verification required by user

## Security Considerations

**File Path Handling:**
- Risk: File paths from user input (save dialogs, CLI arguments)
- Files: `quickice/gui/export.py`, `quickice/output/gromacs_writer.py`, `quickice/output/pdb_writer.py`
- Current mitigation: Uses Path objects, validates extensions, prompts for overwrite
- Recommendations: No issues found - proper handling with context managers and validation

**Input Validation:**
- Risk: Invalid thermodynamic parameters could cause downstream issues
- Files: `quickice/validation/validators.py`
- Current mitigation: Comprehensive validators for temperature (0-500K), pressure (0-10000 MPa), molecule count (4-100000)
- Recommendations: Validation is robust, no issues found

**Exception Handling:**
- Risk: Overly broad exception handlers may hide real errors
- Files: 20+ locations with `except Exception as e:`
- Current mitigation: Most wrap errors with context before re-raising
- Recommendations: Use specific exception types where possible, add logging for caught exceptions

## Performance Bottlenecks

**Large Structure Generation:**
- Problem: Generation for large molecule counts (>10000) may be slow
- Files: `quickice/structure_generation/generator.py`, `quickice/structure_generation/interface_builder.py`
- Cause: GenIce2 computation time scales with molecule count
- Improvement path: Progress callbacks implemented in GUI workers; no optimization needed in core

**Phase Diagram Rendering:**
- Problem: Rendering high-resolution phase diagram with many boundaries
- Files: `quickice/output/phase_diagram.py`
- Cause: Complex matplotlib rendering with multiple curves and annotations
- Improvement path: Acceptable for current use case; could implement caching for repeated renders

## Fragile Areas

**Phase Mapping Lookup:**
- Files: `quickice/phase_mapping/lookup.py` (430 lines)
- Why fragile: Complex multi-condition logic for ice phase identification; many boundary conditions
- Safe modification: Add new phases carefully, ensure boundary curves are validated
- Test coverage: Good - `tests/test_phase_mapping.py` (618 lines)

**GROMACS Export:**
- Files: `quickice/output/gromacs_writer.py` (1559 lines)
- Why fragile: Handles multiple export types (ice, interface, ion, hydrate), molecule wrapping, PBC
- Safe modification: Test each export type independently after changes
- Test coverage: Good - multiple test files cover wrapping, molecule integrity, atom ordering

**GUI State Management:**
- Files: `quickice/gui/main_window.py` (1317 lines), `quickice/gui/viewmodel.py`
- Why fragile: Multiple result types stored (ice, interface, hydrate, ion), tab switching, export routing
- Safe modification: Clear all result storage variables when adding new result types
- Test coverage: Limited - GUI has only 3 test files

## Scaling Limits

**Molecule Count Limits:**
- Current capacity: 4-100,000 molecules (validator-enforced)
- Limit: GRO format limits atom/residue numbers to 5 digits (99,999)
- Scaling path: For >99,999 atoms, wrap numbers at 100,000 (standard GROMACS convention) - already implemented

**Memory for Large Structures:**
- Current capacity: Handles structures up to ~100,000 atoms comfortably
- Limit: Memory scales linearly with atom count; no streaming for export
- Scaling path: For very large structures (>1M atoms), implement streaming export

## Dependencies at Risk

**GenIce2:**
- Risk: External dependency for ice structure generation
- Impact: Critical - no fallback if GenIce2 API changes
- Mitigation: Pin version in environment.yml (`genice2==2.2.13.1`)

**IAPWS:**
- Risk: External dependency for water properties and melting curves
- Impact: Critical for phase diagram and density calculations
- Mitigation: Pin version (`iapws==1.5.5`)

**PySide6:**
- Risk: Qt binding for GUI; version 6.10.2 required
- Impact: GUI won't run on systems with older GLIBC
- Mitigation: Document system requirements clearly (GLIBC 2.28+)

## Missing Critical Features

**CLI Hydrate Generation:**
- Problem: Hydrate generation (Tab 2) only available in GUI
- Files: `quickice/cli/parser.py` - no hydrate arguments
- Blocks: Batch/scripted hydrate structure generation

**CLI Ion Insertion:**
- Problem: Ion insertion (Tab 4) only available in GUI
- Files: `quickice/cli/parser.py` - no ion insertion arguments
- Blocks: Batch/scripted ion insertion workflows

**Progress Reporting for CLI:**
- Problem: No progress indication during long-running CLI operations
- Files: `quickice/main.py`
- Blocks: User feedback during large structure generation

## Test Coverage Gaps

**GUI Modules:**
- What's not tested: Most GUI components (dialogs, panels, viewers, workers)
- Files: `quickice/gui/` (16 files, only 3 test files touch GUI)
- Risk: GUI regressions may go undetected
- Priority: Medium - GUI is user-facing but hard to test

**Hydrate Generation:**
- What's not tested: Full hydrate generation workflow
- Files: `quickice/structure_generation/hydrate_generator.py`
- Risk: Hydrate-related bugs may not be caught by CI
- Priority: High - recent overlap bug indicates need for more tests

**Ion Insertion:**
- What's not tested: Ion insertion workflow
- Files: `quickice/structure_generation/ion_inserter.py`
- Risk: Ion placement or charge neutrality issues
- Priority: High - ion insertion is a key feature

**Export Modules:**
- What's not tested: Complete export workflows for interface, ion, hydrate structures
- Files: `quickice/output/gromacs_writer.py` (limited test coverage)
- Risk: Export format regressions
- Priority: High - export is critical output

---

*Concerns audit: 2026-05-02*
