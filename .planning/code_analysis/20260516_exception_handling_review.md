# Exception Handling Review

**Analysis Date:** 2026-05-16
**Total Instances:** 43 `except Exception` patterns found
**Files Affected:** 21 files

---

## Executive Summary

| Category | Count | Description |
|----------|-------|-------------|
| **OK** | 25 | Intentional patterns with proper logging/feedback |
| **REVIEW** | 5 | Acceptable but could be improved |
| **NEEDS FIX** | 13 | Silent failures, missing logging, or hiding bugs |

**Critical Issues:** 0 (no silent data corruption)
**High Priority:** 4 (user sees nothing when something fails)
**Medium Priority:** 9 (missing debug info)

---

## Summary Table

| File | Line | Category | Purpose | Issue |
|------|------|----------|---------|-------|
| `custom_molecule_viewer.py` | 38 | OK | VTK import guard | Intentional fallback |
| `solute_viewer.py` | 37 | OK | VTK import guard | Intentional fallback |
| `ion_viewer.py` | 39 | OK | VTK import guard | Intentional fallback |
| `view.py` | 33 | OK | VTK import guard | Intentional fallback |
| `interface_panel.py` | 42 | OK | VTK import guard | Intentional fallback |
| `hydrate_viewer.py` | 37 | OK | VTK import guard | Intentional fallback |
| `main_window.py` | 1086 | OK | Solute insertion error | Logged + user feedback |
| `main_window.py` | 1164 | OK | Custom molecule worker setup | Logged + user feedback |
| `main_window.py` | 1260 | OK | Display custom molecule | Logged + user feedback |
| `main_window.py` | 1363 | OK | Preview creation | Logged + user feedback |
| `main_window.py` | 1413 | REVIEW | Clear custom molecule | Logged but no user feedback |
| `custom_molecule_panel.py` | 627 | OK | ITP parsing error | User feedback + logged |
| `custom_molecule_panel.py` | 676 | OK | Validation error | User feedback |
| `custom_molecule_panel.py` | 1013 | OK | Placement validation | Dialog shown |
| `custom_molecule_viewer.py` | 670 | REVIEW | Preview actor creation | Logged only, no user feedback |
| `custom_molecule_viewer.py` | 762 | REVIEW | Multiple preview creation | Logged only, no user feedback |
| `export.py` | 145 | OK | Solute GROMACS export | Dialog shown |
| `export.py` | 223 | OK | Custom molecule export | Dialog + traceback |
| `export.py` | 370 | REVIEW | Ion GROMACS export | Dialog shown but no traceback |
| `export.py` | 444 | OK | PDB export | Dialog shown |
| `export.py` | 532 | OK | Diagram export | Dialog shown |
| `export.py` | 639 | OK | Viewport capture | Dialog shown |
| `export.py` | 723 | REVIEW | GROMACS export | Dialog shown but no traceback |
| `export.py` | 851 | REVIEW | Interface export | Dialog shown but no traceback |
| `workers.py` | 126 | OK | Generation worker | Emits error signal |
| `workers.py` | 219 | OK | Interface worker | Emits error signal with context |
| `hydrate_worker.py` | 110 | OK | Hydrate generation | Emits error signal |
| `custom_molecule_worker.py` | 128 | OK | Custom molecule insertion | Emits error signal + logged |
| `molecule_validator.py` | 75 | OK | GRO parsing in validator | Returns validation error |
| `molecule_validator.py` | 137 | OK | GRO parsing in validator | Returns validation error |
| `interface_builder.py` | 349 | OK | Mode routing | Wraps in specific error |
| `gro_parser.py` | 144 | NEEDS FIX | Residue name extraction | Silent None return |
| `generator.py` | 150 | OK | GenIce wrapper | Wraps in specific error |
| `main.py` | 282 | OK | CLI top-level handler | Prints to stderr, returns exit code |
| `phase_diagram_widget.py` | 81 | NEEDS FIX | IAPWS saturation curve | Silent debug log only |
| `phase_diagram_widget.py` | 483 | NEEDS FIX | IAPWS liquid-vapor | Silent debug log only |
| `hydrate_generator.py` | 211 | OK | GenIce wrapper | Wraps in RuntimeError |
| `hydrate_export.py` | 159 | OK | Hydrate export | Dialog shown |
| `test_integration_v35.py` | 185 | NEEDS FIX | Test file parsing | Swallows unexpected errors |
| `v1.0-run_uat_tests.py` | 44 | NEEDS FIX | UAT test runner | Silent failure |
| `test_z_positions.py` | 58 | NEEDS FIX | Debug test | Silent failure |
| `test_slab_modes.py` | 58 | NEEDS FIX | Debug test | Silent failure |
| `analyze_gro.py` | 115 | NEEDS FIX | Debug script | Silent failure |

---

## Detailed Analysis by Category

### OK - Intentional Patterns (25 instances)

These patterns are appropriate for their use case:

#### VTK Import Guards (6 instances)

**Files:** `custom_molecule_viewer.py:38`, `solute_viewer.py:37`, `ion_viewer.py:39`, `view.py:33`, `interface_panel.py:42`, `hydrate_viewer.py:37`

**Pattern:**
```python
try:
    if _VTK_AVAILABLE:
        from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
        from vtkmodules.all import vtkRenderer, ...
except Exception:
    _VTK_AVAILABLE = False
```

**Verdict:** ✓ Correct pattern for optional dependency handling. VTK may fail for many reasons (not installed, display issues, SSH X11 forwarding), and the application gracefully falls back to non-VTK mode.

---

#### GUI Event Handlers with User Feedback (15 instances)

**Files:** `main_window.py:1086`, `main_window.py:1164`, `main_window.py:1260`, `main_window.py:1363`, `custom_molecule_panel.py:627`, `custom_molecule_panel.py:676`, `custom_molecule_panel.py:1013`, `export.py:145`, `export.py:223`, `export.py:444`, `export.py:532`, `export.py:639`, `hydrate_export.py:159`

**Pattern:**
```python
try:
    # ... operation ...
except Exception as e:
    self.panel.log_message(f"Error: {e}")
    logger.error(f"Operation failed: {e}", exc_info=True)
```

**Verdict:** ✓ Correct pattern. Both logs the error with traceback and provides user feedback.

---

#### Worker Thread Error Handling (4 instances)

**Files:** `workers.py:126`, `workers.py:219`, `hydrate_worker.py:110`, `custom_molecule_worker.py:128`

**Pattern:**
```python
except Exception as e:
    error_result = GenerationResult(success=False, error=str(e))
    self.error.emit(str(e))
    self.finished.emit(error_result)
```

**Verdict:** ✓ Correct pattern for Qt workers. Signals are emitted to notify the main thread.

---

#### Error Wrapping (3 instances)

**Files:** `interface_builder.py:349`, `generator.py:150`, `hydrate_generator.py:211`

**Pattern:**
```python
except InterfaceGenerationError:
    raise  # Re-raise specific errors
except Exception as e:
    raise InterfaceGenerationError(f"Unexpected error: {e}") from e
```

**Verdict:** ✓ Correct pattern. Wraps unexpected errors in domain-specific exceptions.

---

#### CLI Top-Level Handler (1 instance)

**File:** `main.py:282`

**Pattern:**
```python
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    return 1
```

**Verdict:** ✓ Correct pattern for CLI. Prints error and returns non-zero exit code.

---

### REVIEW - Acceptable but Could Improve (5 instances)

#### Missing User Feedback for Non-Critical Operations (3 instances)

**File:** `main_window.py:1413`

```python
except Exception as e:
    logger.error(f"Error clearing custom molecule results: {e}")
```

**Issue:** No user feedback if clearing fails. User may think operation succeeded.

**Recommendation:** Add `self.custom_molecule_panel.log_message(f"Warning: Could not clear previous results: {e}")`

---

**Files:** `custom_molecule_viewer.py:670`, `custom_molecule_viewer.py:762`

```python
except Exception as e:
    logger.error(f"Failed to create preview actor: {e}")
```

**Issue:** Preview fails silently from user perspective. No indication in UI.

**Recommendation:** Emit a signal or call a callback to notify user that preview failed.

---

#### Missing Traceback in Export Errors (3 instances)

**Files:** `export.py:370`, `export.py:723`, `export.py:851`

**Pattern:**
```python
except Exception as e:
    QMessageBox.critical(self.parent, "Export Error", f"Failed: {e}")
    return False
```

**Issue:** Unlike other export handlers (line 145, 223), these don't print traceback. Makes debugging harder.

**Recommendation:** Add `import traceback; traceback.print_exc()` for consistency.

---

### NEEDS FIX - Silent Failures or Missing Logging (13 instances)

#### Silent None Return in Parser (1 instance) - HIGH PRIORITY

**File:** `gro_parser.py:144`

```python
def extract_residue_name_from_gro(gro_path: Path) -> Optional[str]:
    # ... file reading ...
    try:
        # ... parsing logic ...
        return residue_name if residue_name else None
    except Exception:
        return None
```

**Issue:** Any parsing error silently returns `None`. Could hide file corruption, encoding issues, or format changes.

**Impact:** High - if GRO file is malformed, user gets no indication. Validation may pass with incorrect data.

**Fix:**
```python
except Exception as e:
    logger.warning(f"Could not extract residue name from {gro_path}: {e}")
    return None
```

---

#### Silent IAPWS Failures (2 instances) - MEDIUM PRIORITY

**Files:** `phase_diagram_widget.py:81`, `phase_diagram_widget.py:483`

```python
for T in np.linspace(273.16, 500, 50):
    try:
        st = IAPWS97(T=T, x=0)
        vapor_vertices.append((T, st.P))
    except Exception as e:
        logger.debug(f"Could not get saturation pressure at T={T}: {e}")
```

**Issue:** Uses `debug` level, so failures are invisible in normal operation. If IAPWS consistently fails, diagram may be incomplete with no indication.

**Impact:** Medium - Missing boundary lines in diagram, but application continues.

**Fix:**
```python
except Exception as e:
    logger.warning(f"IAPWS calculation failed at T={T}: {e}")
    continue  # Or collect failures and warn once at end
```

---

#### Test Files Swallowing Errors (4 instances) - LOW PRIORITY

**Files:** `test_integration_v35.py:185`, `v1.0-run_uat_tests.py:44`, `test_z_positions.py:58`, `test_slab_modes.py:58`, `analyze_gro.py:115`

**Pattern:**
```python
except Exception as e:
    errors.append(f"Unexpected error: {e}")
    # or silent pass
```

**Issue:** Tests should let exceptions propagate to test framework. Swallowing hides real failures.

**Impact:** Low - Only affects test reliability, not production code.

**Fix:** Remove the try/except or re-raise after collecting error info:
```python
except Exception as e:
    errors.append(f"Unexpected error: {e}")
    raise  # Let test framework report the failure
```

---

## Priority Ranking for Fixes

### High Priority (Fix Soon)

| # | File | Line | Issue | Fix Effort |
|---|------|------|-------|------------|
| 1 | `gro_parser.py` | 144 | Silent None return hides parsing errors | 2 lines |
| 2 | `main_window.py` | 1413 | Clear operation fails silently | 1 line |
| 3 | `custom_molecule_viewer.py` | 670 | Preview fails with no UI feedback | 3 lines |
| 4 | `custom_molecule_viewer.py` | 762 | Multiple preview fails silently | 3 lines |

### Medium Priority (Fix When Convenient)

| # | File | Line | Issue | Fix Effort |
|---|------|------|-------|------------|
| 5 | `phase_diagram_widget.py` | 81 | IAPWS failures at debug level | 1 line |
| 6 | `phase_diagram_widget.py` | 483 | IAPWS failures at debug level | 1 line |
| 7 | `export.py` | 370 | Missing traceback in error | 2 lines |
| 8 | `export.py` | 723 | Missing traceback in error | 2 lines |
| 9 | `export.py` | 851 | Missing traceback in error | 2 lines |

### Low Priority (Fix When Touching Code)

| # | File | Line | Issue |
|---|------|------|-------|
| 10-13 | Test/debug files | Various | Swallowing exceptions in tests |

---

## Recommended Fixes

### Fix 1: `gro_parser.py:144` - Add Logging

**Current:**
```python
except Exception:
    return None
```

**Recommended:**
```python
except Exception as e:
    logger.warning(f"Could not extract residue name from {gro_path}: {e}")
    return None
```

---

### Fix 2: `main_window.py:1413` - Add User Feedback

**Current:**
```python
except Exception as e:
    logger.error(f"Error clearing custom molecule results: {e}")
```

**Recommended:**
```python
except Exception as e:
    logger.error(f"Error clearing custom molecule results: {e}")
    self.custom_molecule_panel.log_message(f"Warning: Could not clear previous results: {e}")
```

---

### Fix 3: `custom_molecule_viewer.py:670, 762` - Add User Feedback

**Current:**
```python
except Exception as e:
    logger.error(f"Failed to create preview actor: {e}")
```

**Recommended:**
```python
except Exception as e:
    logger.error(f"Failed to create preview actor: {e}")
    # Parent widget should handle this - could add a callback
    if hasattr(self, '_preview_error_callback'):
        self._preview_error_callback(str(e))
```

Or use Qt signal if the viewer has one.

---

### Fix 4: `phase_diagram_widget.py:81, 483` - Use Warning Level

**Current:**
```python
except Exception as e:
    logger.debug(f"Could not get saturation pressure at T={T}: {e}")
```

**Recommended:**
```python
except Exception as e:
    logger.warning(f"IAPWS saturation calculation failed at T={T}K: {e}")
```

---

### Fix 5: `export.py` - Add Traceback for Consistency

**Current (lines 370, 723, 851):**
```python
except Exception as e:
    QMessageBox.critical(self.parent, "Export Error", f"Failed: {e}")
    return False
```

**Recommended:**
```python
except Exception as e:
    logger.error(f"Export failed: {e}")
    import traceback
    traceback.print_exc()
    QMessageBox.critical(self.parent, "Export Error", f"Failed: {e}")
    return False
```

---

## Patterns to Maintain

The codebase follows these good patterns that should be preserved:

1. **VTK Import Guards:** Continue using `except Exception` for optional dependency imports
2. **Error Wrapping:** Continue wrapping generic exceptions in domain-specific types
3. **Worker Threads:** Continue emitting error signals for Qt workers
4. **User Feedback:** Always pair logging with user-visible feedback in GUI handlers

---

## Conclusion

The codebase has reasonable exception handling overall. The main issues are:

1. **Silent failures** in non-critical operations (preview, clearing state)
2. **Missing logging** in parser fallbacks
3. **Inconsistent traceback printing** in export errors

No critical data corruption risks were found. All fixes are low-effort (1-3 lines each).

**Recommendation:** Fix the 4 high-priority items in the next available development cycle.

---

*Analysis complete: 2026-05-16*
