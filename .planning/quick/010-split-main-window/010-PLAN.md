---
phase: 010-split-main-window
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/gui/main_window.py
  - quickice/gui/main_window/__init__.py
  - quickice/gui/main_window/tab_setup.py
  - quickice/gui/main_window/actions.py
  - quickice/gui/main_window/menu_bar.py
autonomous: true

must_haves:
  truths:
    - "main_window.py split into modules under quickice/gui/main_window/"
    - "Each module <500 lines with single responsibility"
    - "GUI launches successfully"
    - "All tabs and actions work correctly"
  artifacts:
    - path: "quickice/gui/main_window/tab_setup.py"
      provides: "Tab initialization logic"
      max_lines: 500
    - path: "quickice/gui/main_window/actions.py"
      provides: "Action handlers"
      max_lines: 500
    - path: "quickice/gui/main_window/menu_bar.py"
      provides: "Menu bar setup"
      max_lines: 500
  key_links:
    - from: "quickice/gui/main_window.py"
      to: "quickice/gui/main_window/*"
      via: "import delegation"
      pattern: "from quickice.gui.main_window import"
---

<objective>
Split main_window.py (1317 lines) into smaller, focused modules.

Purpose: Improve maintainability of main GUI component
Output: Modular structure with each file <500 lines
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/codebase/CONCERNS.md
@.planning/codebase/ARCHITECTURE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Split main_window.py into modules</name>
  <files>
    quickice/gui/main_window.py
    quickice/gui/main_window/__init__.py
    quickice/gui/main_window/tab_setup.py
    quickice/gui/main_window/actions.py
    quickice/gui/main_window/menu_bar.py
  </files>
  <action>
    Refactor `quickice/gui/main_window.py` (1317 lines) into smaller modules:

    1. **Create module structure**:
       ```
       quickice/gui/main_window/
       ├── __init__.py           # MainWindow class export
       ├── tab_setup.py          # Tab initialization
       ├── actions.py            # Action handlers (generate, export, etc.)
       └── menu_bar.py           # Menu bar and toolbar setup
       ```

    2. **Assign responsibilities**:
       - `tab_setup.py`: _setup_tabs(), _create_ice_tab(), _create_hydrate_tab(), etc.
       - `actions.py`: on_generate(), on_export(), on_save(), etc.
       - `menu_bar.py`: _setup_menu_bar(), _setup_toolbar(), menu actions

    3. **Keep MainWindow class in __init__.py**:
       - MainWindow remains the main class
       - Helper methods moved to appropriate modules
       - MainWindow imports and uses helper functions

    4. **Maintain backward compatibility**:
       - `from quickice.gui.main_window import MainWindow` still works
       - Internal refactoring only, no API changes

    Reference: quickice/gui/main_window.py current structure
  </action>
  <verify>
    - New directory structure created
    - Each file <500 lines
    - GUI launches (python -m quickice.gui)
    - All tabs render correctly
    - Menu bar and actions work
  </verify>
  <done>main_window.py refactored into 4 modules, each <500 lines, GUI fully functional</done>
</task>

</tasks>

<verification>
- [ ] quickice/gui/main_window/ directory exists
- [ ] __init__.py contains MainWindow class
- [ ] tab_setup.py <500 lines
- [ ] actions.py <500 lines
- [ ] menu_bar.py <500 lines
- [ ] GUI launches successfully
- [ ] All 4 tabs work (Ice, Hydrate, Interface, Ion)
- [ ] Menu bar functional
- [ ] Actions trigger correctly
</verification>

<success_criteria>
main_window.py (1317 lines) split into 4 modules, each <500 lines, GUI fully functional.
</success_criteria>

<output>
After completion, create `.planning/quick/010-split-main-window/010-SUMMARY.md`
</output>
