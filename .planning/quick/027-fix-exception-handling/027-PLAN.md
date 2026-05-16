---
phase: 027
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/structure_generation/gro_parser.py
  - quickice/gui/main_window.py
  - quickice/gui/custom_molecule_viewer.py
  - quickice/gui/phase_diagram_widget.py
  - quickice/gui/export.py
autonomous: true
user_setup: []

must_haves:
  truths:
    - "GRO parsing failures log warnings instead of silently returning None"
    - "Clear operation failures show user-visible warnings in the UI"
    - "Preview failures show user feedback in the UI"
    - "IAPWS calculation failures logged at warning level (not debug)"
    - "Export errors include traceback for debugging"
  artifacts:
    - path: "quickice/structure_generation/gro_parser.py"
      provides: "Residue name extraction with error logging"
      contains: "logger.warning"
    - path: "quickice/gui/main_window.py"
      provides: "Clear operation with UI feedback"
      contains: "log_message.*Warning"
    - path: "quickice/gui/custom_molecule_viewer.py"
      provides: "Preview with user feedback on failure"
    - path: "quickice/gui/phase_diagram_widget.py"
      provides: "IAPWS error logging at warning level"
      contains: "logger.warning.*saturation"
    - path: "quickice/gui/export.py"
      provides: "Export errors with traceback"
      contains: "traceback.print_exc"
  key_links:
    - from: "gro_parser.py:extract_residue_name_from_gro"
      to: "logger"
      via: "warning on parse failure"
    - from: "main_window.py:_clear_custom_molecule_results"
      to: "custom_molecule_panel.log_message"
      via: "UI feedback on error"
    - from: "custom_molecule_viewer.py:show_preview/show_multiple_previews"
      to: "parent UI"
      via: "Error signal or log message"
---

<objective>
Fix 9 exception handling issues across 5 files to improve error visibility and debugging.

Purpose: Silent failures and low-priority logging hide real issues from users and developers. This plan adds logging, UI feedback, and tracebacks to make errors discoverable.

Output: 5 files with improved exception handling (4 high priority + 5 medium priority fixes)
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

# File Locations (corrected from input)
- gro_parser.py: quickice/structure_generation/gro_parser.py (NOT quickice/parsers/)
- All GUI files: quickice/gui/
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add logging to parsing and phase diagram calculations</name>
  <files>
    - quickice/structure_generation/gro_parser.py
    - quickice/gui/phase_diagram_widget.py
  </files>
  <action>
    **Issue #1 - gro_parser.py:144-145**
    
    Currently:
    ```python
    except Exception:
        return None
    ```
    
    Change to:
    ```python
    except Exception as e:
        logger.warning(f"Could not extract residue name from {gro_path}: {e}")
        return None
    ```
    
    Note: `gro_path` parameter is available in the function signature. Add `import logging` and `logger = logging.getLogger(__name__)` at the top if not present.
    
    **Issue #5 - phase_diagram_widget.py:82**
    
    Currently:
    ```python
    logger.debug(f"Could not get saturation pressure at T={T}: {e}")
    ```
    
    Change to:
    ```python
    logger.warning(f"Could not get saturation pressure at T={T}: {e}")
    ```
    
    **Issue #6 - phase_diagram_widget.py:484**
    
    Currently:
    ```python
    logger.debug(f"Could not get liquid-vapor boundary at T={T}: {e}")
    ```
    
    Change to:
    ```python
    logger.warning(f"Could not get liquid-vapor boundary at T={T}: {e}")
    ```
    
    These IAPWS failures indicate problematic thermodynamic calculations that users should be aware of.
  </action>
  <verify>
    ```bash
    # Check gro_parser.py has warning log
    grep -n "logger.warning.*Could not extract residue name" quickice/structure_generation/gro_parser.py
    
    # Check phase_diagram_widget.py has warnings (not debug)
    grep -n "logger.warning.*saturation pressure" quickice/gui/phase_diagram_widget.py
    grep -n "logger.warning.*liquid-vapor boundary" quickice/gui/phase_diagram_widget.py
    
    # Ensure no debug level for these messages
    ! grep "logger.debug.*saturation pressure\|logger.debug.*liquid-vapor" quickice/gui/phase_diagram_widget.py
    ```
  </verify>
  <done>
    - gro_parser.py logs warning when residue extraction fails
    - phase_diagram_widget.py logs warnings for IAPWS failures (not debug)
    - All changes are 1-line additions/modifications
  </done>
</task>

<task type="auto">
  <name>Task 2: Add UI feedback for user-facing operation failures</name>
  <files>
    - quickice/gui/main_window.py
    - quickice/gui/custom_molecule_viewer.py
  </files>
  <action>
    **Issue #2 - main_window.py:1413-1414**
    
    Currently (lines 1413-1414):
    ```python
    except Exception as e:
        logger.error(f"Error clearing custom molecule results: {e}")
    ```
    
    Add UI feedback after the logger.error line:
    ```python
    except Exception as e:
        logger.error(f"Error clearing custom molecule results: {e}")
        if hasattr(self, 'custom_molecule_panel') and self.custom_molecule_panel:
            self.custom_molecule_panel.log_message(f"Warning: Could not clear previous results: {e}")
    ```
    
    This provides user-visible feedback when the clear operation fails.
    
    **Issue #3 - custom_molecule_viewer.py:670-671**
    
    Currently:
    ```python
    except Exception as e:
        logger.error(f"Failed to create preview actor: {e}")
    ```
    
    Add UI feedback after the logger.error line:
    ```python
    except Exception as e:
        logger.error(f"Failed to create preview actor: {e}")
        # Provide user feedback if parent has log_message method
        if hasattr(self, 'parent') and hasattr(self.parent, 'log_message'):
            self.parent.log_message(f"Warning: Could not create preview: {e}")
    ```
    
    **Issue #4 - custom_molecule_viewer.py:762-763**
    
    Currently:
    ```python
    except Exception as e:
        logger.error(f"Failed to create preview actor: {e}")
    ```
    
    Add UI feedback after the logger.error line:
    ```python
    except Exception as e:
        logger.error(f"Failed to create preview actor: {e}")
        # Provide user feedback if parent has log_message method
        if hasattr(self, 'parent') and hasattr(self.parent, 'log_message'):
            self.parent.log_message(f"Warning: Could not create preview: {e}")
    ```
    
    The custom_molecule_viewer widget is embedded in CustomMoleculePanel which has a log_message method.
  </action>
  <verify>
    ```bash
    # Check main_window.py has UI feedback
    grep -A2 "Error clearing custom molecule results" quickice/gui/main_window.py | grep "log_message.*Warning"
    
    # Check custom_molecule_viewer.py has UI feedback at both locations
    grep -A3 "Failed to create preview actor" quickice/gui/custom_molecule_viewer.py | grep "parent.*log_message"
    
    # Should have 2 occurrences (lines 670 and 762)
    grep -c "parent.*log_message.*Could not create preview" quickice/gui/custom_molecule_viewer.py
    ```
  </verify>
  <done>
    - main_window.py shows UI warning when clear operation fails
    - custom_molecule_viewer.py shows UI warnings when preview fails (both single and multiple)
    - All failures are now visible to users, not just in logs
  </done>
</task>

<task type="auto">
  <name>Task 3: Add traceback printing for export errors</name>
  <files>
    - quickice/gui/export.py
  </files>
  <action>
    **Issue #7 - export.py:370-371**
    
    Currently:
    ```python
    except Exception as e:
        QMessageBox.critical(self.parent, "Export Error", f"Failed: {e}")
        return False
    ```
    
    Add traceback before the return:
    ```python
    except Exception as e:
        import traceback
        traceback.print_exc()
        QMessageBox.critical(self.parent, "Export Error", f"Failed: {e}")
        return False
    ```
    
    **Issue #8 - export.py:723-724**
    
    Same pattern - add traceback before the return:
    ```python
    except Exception as e:
        import traceback
        traceback.print_exc()
        QMessageBox.critical(self.parent, "Export Error", f"Failed: {e}")
        return False
    ```
    
    **Issue #9 - export.py:851-852**
    
    Same pattern - add traceback before the return:
    ```python
    except Exception as e:
        import traceback
        traceback.print_exc()
        QMessageBox.critical(self.parent, "Export Error", f"Failed: {e}")
        return False
    ```
    
    Import traceback inside the except block to avoid unused import warnings in the success path.
  </action>
  <verify>
    ```bash
    # Check all three locations have traceback.print_exc()
    grep -B2 "traceback.print_exc" quickice/gui/export.py | grep "import traceback"
    
    # Should have 3 occurrences
    grep -c "traceback.print_exc" quickice/gui/export.py
    ```
  </verify>
  <done>
    - export.py prints traceback for all three export failure points
    - Developers can debug export issues from console output
    - Users still see QMessageBox with error message
  </done>
</task>

</tasks>

<verification>
After all tasks complete:

1. Run syntax check on all modified files:
   ```bash
   python -m py_compile quickice/structure_generation/gro_parser.py
   python -m py_compile quickice/gui/main_window.py
   python -m py_compile quickice/gui/custom_molecule_viewer.py
   python -m py_compile quickice/gui/phase_diagram_widget.py
   python -m py_compile quickice/gui/export.py
   ```

2. Verify logging changes don't break imports:
   ```bash
   python -c "from quickice.structure_generation.gro_parser import extract_residue_name_from_gro; print('OK')"
   ```
</verification>

<success_criteria>
- All 9 exception handling issues fixed (4 high + 5 medium priority)
- 5 files modified with targeted 1-3 line changes
- All files pass Python syntax check
- Errors are now visible to users (UI feedback) and developers (warnings + tracebacks)
- No functional behavior changes, only improved error visibility
</success_criteria>

<output>
After completion, create `.planning/quick/027-fix-exception-handling/027-SUMMARY.md`
</output>
