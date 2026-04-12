---
phase: 27-documentation-update
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/gui/help_dialog.py
  - quickice/gui/main_window.py
  - quickice/gui/__init__.py
autonomous: true
user_setup: []

must_haves:
  truths:
    - "User sees corrected help dialog without triclinic error message"
    - "User sees transformation status in Tab 2 interface generation log"
    - "Tooltips have consistent width across all GUI elements"
  artifacts:
    - path: "quickice/gui/help_dialog.py"
      provides: "Updated in-app help content"
      contains: "transformation"
    - path: "quickice/gui/main_window.py"
      provides: "Transformation status display in Tab 2"
      contains: "transformation_status"
    - path: "quickice/gui/__init__.py"
      provides: "Global tooltip stylesheet"
      contains: "QToolTip"
  key_links:
    - from: "main_window.py"
      to: "candidate.metadata"
      via: "transformation_status and transformation_message"
      pattern: "transformation_status.*transformation_message"
---

<objective>
Update in-app help, add transformation status display, and fix tooltip width issues.

Purpose: Ensure in-app help is accurate, Tab 2 shows transformation status, and tooltips have consistent width.
Output: Updated help_dialog.py, main_window.py, and global tooltip stylesheet.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/27-documentation-update/27-CONTEXT.md

# Current help_dialog.py line 156:
# "• 'Triclinic cell': Select different ice phase (ice_ii, ice_v are triclinic)"
# This is now WRONG - triclinic phases work with transformation

# main_window.py line 450 shows candidate info:
# self.interface_panel.append_log(f"  Candidate: {candidate.phase_id} ({candidate.nmolecules} molecules)")
# Need to add transformation status/message after this line

# Candidate metadata fields (from Phase 24):
# - transformation_status: "transformed" or None
# - transformation_multiplier: int (e.g., 6 for Ice II)
# - transformation_message: str (human-readable message)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix help_dialog.py triclinic error message</name>
  <files>quickice/gui/help_dialog.py</files>
  <action>
    Update help_dialog.py to fix the outdated triclinic cell message and add minimal density context:

    1. **Fix TROUBLESHOOTING section (line 156):**
       - FIND: `"'Triclinic cell': Select different ice phase (ice_ii, ice_v are triclinic)"`
       - REPLACE with: `"'Triclinic cell': Transformation applied automatically (Ice II, V, VI work with interfaces)"`

    2. **Add density note in Important Notes section (around line 175-181):**
       - After the existing notes about molecule count and GROMACS, ADD:
       - `"• Ice Ih density uses IAPWS R10-06(2009) for temperature-dependent accuracy\n"`
       - `"• Water density for interfaces uses IAPWS-95 formulation\n"`

    3. **Verify no other triclinic error references exist in the file**

    The changes should:
    - Not add new sections (match existing structure)
    - Be minimal additions (not comprehensive density documentation)
    - Match existing text style (bullet points, concise)
  </action>
  <verify>
    grep -n "Select different ice phase" quickice/gui/help_dialog.py should return 0 matches
    grep -n "Transformation applied automatically" quickice/gui/help_dialog.py should find the fixed line
    grep -n "IAPWS R10-06" quickice/gui/help_dialog.py should find the density note
  </verify>
  <done>
    Help dialog updated with correct triclinic transformation info and minimal density context.
  </done>
</task>

<task type="auto">
  <name>Task 2: Add transformation status display in Tab 2</name>
  <files>quickice/gui/main_window.py</files>
  <action>
    Add transformation status and message display in the Tab 2 interface generation log:

    1. **Find the line after candidate info (around line 450):**
       ```python
       self.interface_panel.append_log(f"  Candidate: {candidate.phase_id} ({candidate.nmolecules} molecules)")
       ```

    2. **ADD transformation status display immediately after (before line 451):**
       ```python
       # Show transformation status if candidate was transformed
       if candidate.metadata.get("transformation_status") == "transformed":
           multiplier = candidate.metadata.get("transformation_multiplier", "?")
           message = candidate.metadata.get("transformation_message", "Cell transformed")
           self.interface_panel.append_log(f"  Transformation: {message} ({multiplier}x multiplier)")
       ```

    3. **Verify the placement:**
       - The transformation message should appear right after the candidate line
       - It should be indented to match the candidate line (2 spaces prefix)
       - Should only appear when transformation_status is "transformed"

    The metadata fields come from TriclinicTransformer (Phase 24):
    - transformation_status: "transformed" when cell was converted
    - transformation_multiplier: int (e.g., 6 for Ice II rhombohedral→hexagonal→orthogonal)
    - transformation_message: str (e.g., "Rhombohedral cell transformed to orthogonal")
  </action>
  <verify>
    grep -n "transformation_status" quickice/gui/main_window.py should find the new code
    grep -n "transformation_message" quickice/gui/main_window.py should find the new code
    grep -n "transformation_multiplier" quickice/gui/main_window.py should find the new code
  </verify>
  <done>
    Tab 2 interface log now shows transformation status when triclinic phases are used.
  </done>
</task>

<task type="auto">
  <name>Task 3: Apply global tooltip width limit</name>
  <files>quickice/gui/__init__.py</files>
  <action>
    Add global QToolTip stylesheet to fix tooltip width issues:

    1. **In quickice/gui/__init__.py, add QApplication import and stylesheet:**
       - The file currently only imports MainWindow, run_app, PhaseDiagramPanel
       - Add QApplication import for setting stylesheet
       - This should be applied at module load time or via run_app()

    2. **Option A - Apply in run_app() function:**
       - Add the stylesheet to the QApplication in run_app() (in main_window.py)
       - This is cleaner since run_app() creates the QApplication

    Actually, looking at the code structure, run_app() is in main_window.py.
    Let me update the approach:

    **Update quickice/gui/main_window.py run_app() function instead:**
    
    In the run_app() function (around line 893-907), add after creating QApplication:

    ```python
    def run_app():
        """Run the QuickIce GUI application.
        ...
        """
        import sys
        app = QApplication(sys.argv)
        
        # Apply global tooltip width limit for consistent display
        app.setStyleSheet("""
            QToolTip {
                max-width: 400px;
            }
        """)
        
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    ```

    This applies a global 400px max-width to all tooltips, preventing overly wide tooltips from breaking layout.

    Do NOT:
    - Reword tooltip text manually
    - Apply individual fixes to each tooltip
    - Change tooltip content
  </action>
  <verify>
    grep -n "QToolTip" quickice/gui/main_window.py should find the stylesheet
    grep -n "max-width" quickice/gui/main_window.py should find the width limit
    python -c "from quickice.gui.main_window import run_app" should not error
  </verify>
  <done>
    Global tooltip width limit applied via QToolTip stylesheet. All tooltips now have consistent maximum width.
  </done>
</task>

</tasks>

<verification>
- help_dialog.py: No "Select different ice phase" message, IAPWS density notes present
- main_window.py: transformation_status display code added after candidate info
- main_window.py: QToolTip stylesheet with max-width applied
- No syntax errors when importing modules
</verification>

<success_criteria>
- User sees correct triclinic transformation info in help dialog
- User sees transformation status when using Ice II, V, VI in Tab 2
- All tooltips have consistent maximum width (no overflow)
</success_criteria>

<output>
After completion, create `.planning/phases/27-documentation-update/27-02-SUMMARY.md`
</output>
