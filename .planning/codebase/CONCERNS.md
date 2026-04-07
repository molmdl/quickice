# Codebase Concerns

**Analysis Date:** 2026-04-07

## Tech Debt

**Debug Print Statements in Production:**
- Issue: Debug print statements left in production code
- Files: `quickice/gui/main_window.py` lines 529, 543, 545
- Impact: Pollutes console output, indicates incomplete cleanup
- Fix approach: Remove or convert to proper logging with `logging.debug()`

```python
# Lines 529, 543, 545 in main_window.py
print(f"[DEBUG] _on_phase_info called with phase_id='{phase_id}'")
print(f"[DEBUG] Converted to phase_id_full='{phase_id_full}'")
print(f"[DEBUG] PHASE_METADATA lookup returned: {meta}")
```

**Global Random State Pollution:**
- Issue: GenIce generator modifies global `np.random` state
- Files: `quickice/structure_generation/generator.py` lines 84-111
- Impact: Not thread-safe, can affect other code using numpy random
- Fix approach: Use `numpy.random.Generator` instances throughout, pass to GenIce if supported

**Hardcoded Scoring Constants:**
- Issue: Magic numbers in ranking/scoring logic
- Files: `quickice/ranking/scorer.py` lines 22-23, 129
- Impact: Makes tuning difficult, unclear rationale for values
- Fix approach: Move to configuration or constants module with documentation

```python
# Lines 22-23 in scorer.py
IDEAL_OO_DISTANCE = 0.276  # nm - ideal O-O distance in ice
OO_CUTOFF = 0.35  # nm - cutoff for H-bond detection
```

**Duplicate Validator Logic:**
- Issue: Two separate validator modules (CLI and GUI) with overlapping logic
- Files: `quickice/validation/validators.py`, `quickice/gui/validators.py`
- Impact: Maintenance burden, potential inconsistency between CLI and GUI limits
- Fix approach: Create shared validation core with different limit configurations

## Known Bugs

**Empty Candidate List Handling:**
- Symptoms: ValueError "zero-size array" when normalizing scores for empty list
- Files: `quickice/ranking/scorer.py` line 218 (normalize_scores)
- Trigger: Calling `rank_candidates([])` with empty list
- Workaround: Tests document this behavior, but no guard in production code

**VTK Fallback in Remote Environments:**
- Symptoms: 3D viewer unavailable when SSH X11 forwarding detected
- Files: `quickice/gui/view.py` lines 20-34
- Trigger: `DISPLAY` environment variable contains "localhost"
- Workaround: Set `QUICKICE_FORCE_VTK=true` to override detection

## Security Considerations

**File Path Handling:**
- Risk: User-provided paths in file export without sanitization
- Files: `quickice/gui/export.py`, `quickice/output/pdb_writer.py`, `quickice/output/gromacs_writer.py`
- Current mitigation: QFileDialog restricts to user-selected paths
- Recommendations: Consider validating paths don't escape expected directories

**Input Validation:**
- Risk: Numeric inputs parsed without bounds checking in some paths
- Files: `quickice/main.py` line 162 (catches generic Exception)
- Current mitigation: Validators for temperature, pressure, molecule count
- Recommendations: Ensure all file I/O operations have proper error handling

## Performance Bottlenecks

**Phase Diagram Generation:**
- Problem: Large file with 977 lines, complex polygon calculations
- Files: `quickice/output/phase_diagram.py`
- Cause: Multiple polygon building functions, spline interpolation
- Improvement path: Consider caching polygon vertices, lazy computation

**O-O Distance Calculation:**
- Problem: 3x3x3 supercell construction for every candidate
- Files: `quickice/ranking/scorer.py` lines 59-66
- Cause: PBC handling requires supercell expansion
- Improvement path: Use minimum image convention directly for small cells

**Candidate Generation:**
- Problem: Sequential generation of 10 candidates
- Files: `quickice/structure_generation/generator.py` lines 214-217
- Cause: No parallelization of candidate generation
- Improvement path: Use multiprocessing for independent candidate generation

## Fragile Areas

**Phase Mapping Logic:**
- Files: `quickice/phase_mapping/lookup.py` (392 lines)
- Why fragile: Complex hierarchical condition checking for phase boundaries
- Safe modification: Test thoroughly at boundary conditions, especially triple points
- Test coverage: Unit tests exist but may not cover all edge cases

**GUI State Management:**
- Files: `quickice/gui/viewmodel.py`, `quickice/gui/workers.py`
- Why fragile: Multi-threaded QThread worker pattern, signal/slot connections
- Safe modification: Ensure proper cleanup of threads, use Qt's signal/slot thread safety
- Test coverage: No GUI tests detected

**Phase Diagram Widget:**
- Files: `quickice/gui/phase_diagram_widget.py` (775 lines)
- Why fragile: Interactive matplotlib canvas with bidirectional binding
- Safe modification: Test diagram click -> input update -> diagram update cycle
- Test coverage: No integration tests for interactive features

## Scaling Limits

**Molecule Count:**
- Current capacity: CLI max 100,000 molecules, GUI max 216 molecules
- Limit: GUI limited by computational constraints in interactive mode
- Scaling path: Background generation already implemented, consider progress feedback

**Candidate Generation:**
- Current capacity: 10 candidates per generation
- Limit: No hard limit, but performance degrades with more candidates
- Scaling path: Already uses background thread, could add configuration option

## Dependencies at Risk

**GenIce2:**
- Risk: External package for ice structure generation, critical dependency
- Impact: Entire structure generation fails without it
- Migration plan: Core functionality - no practical alternative, ensure version pinned

**IAPWS:**
- Risk: Thermodynamic property calculations for phase boundaries
- Impact: Phase diagram and melting curve calculations fail
- Migration plan: IAPWS is a scientific standard - low risk, but ensure fallback error handling

**VTK:**
- Risk: 3D visualization library, heavy dependency
- Impact: GUI visualization fails without it
- Migration plan: Already has fallback mode, consider py3Dmol as lightweight alternative

**Shapely:**
- Risk: Used for polygon centroid calculation in phase diagram
- Impact: Phase diagram label positioning fails
- Migration plan: Could implement simple centroid calculation without Shapely

## Missing Critical Features

**User Preference Persistence:**
- Problem: No settings/configuration persistence between sessions
- Blocks: Users must re-enter preferred parameters each session

**Undo/Redo Support:**
- Problem: No undo capability for accidental clicks or parameter changes
- Blocks: User experience degradation on mistakes

**Batch Processing:**
- Problem: Can only generate one T,P condition at a time
- Blocks: Users wanting to scan phase diagram regions

## Test Coverage Gaps

**GUI Module:**
- What's not tested: All GUI components (view, viewmodel, workers, main_window)
- Files: `quickice/gui/*.py` (all 10+ files)
- Risk: UI regressions, signal/slot connection failures, thread safety issues
- Priority: High - critical user-facing functionality

**Integration Tests:**
- What's not tested: End-to-end CLI workflow, file export validation
- Files: `tests/test_cli_integration.py` exists but may not cover all paths
- Risk: Breaking user workflows without detection
- Priority: Medium

**Phase Diagram Generation:**
- What's not tested: Polygon building functions, label positioning
- Files: `quickice/output/phase_diagram.py` (977 lines)
- Risk: Incorrect phase boundaries displayed to users
- Priority: High - scientific accuracy concern

**Error Path Coverage:**
- What's not tested: Error handling branches, edge cases in validators
- Files: Various
- Risk: Cryptic errors or crashes on invalid input
- Priority: Medium

---

*Concerns audit: 2026-04-07*
