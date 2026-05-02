---
phase: 007-code-quality-improvements-logging-dedu
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/utils/__init__.py
  - quickice/utils/molecule_utils.py
  - quickice/output/gromacs_writer.py
  - quickice/gui/dual_viewer.py
  - quickice/gui/phase_diagram_widget.py
  - quickice/gui/main_window.py
  - quickice/structure_generation/modes/pocket.py
  - quickice/structure_generation/modes/slab.py
  - quickice/structure_generation/modes/piece.py
  - quickice/structure_generation/hydrate_generator.py
  - quickice/structure_generation/ion_inserter.py
  - quickice/phase_mapping/ice_ih_density.py
  - quickice/phase_mapping/water_density.py
autonomous: true

must_haves:
  truths:
    - "All empty pass statements have logging instead of silent failure"
    - "Fallback density values trigger visible warnings"
    - "GRO atom limit warnings appear when >99,999 atoms"
    - "No duplicate _count_guest_atoms functions exist"
    - "No duplicate molecule index building functions exist"
    - "Parameter naming follows Python conventions (snake_case)"
  artifacts:
    - path: "quickice/utils/molecule_utils.py"
      provides: "Consolidated molecule utility functions"
      exports: ["count_guest_atoms", "build_molecule_index"]
    - path: "quickice/output/gromacs_writer.py"
      contains: "logger.warning"
    - path: "quickice/gui/dual_viewer.py"
      contains: "logger.debug"
  key_links:
    - from: "quickice/structure_generation/modes/*.py"
      to: "quickice/utils/molecule_utils.py"
      via: "import count_guest_atoms"
      pattern: "from quickice.utils.molecule_utils import"
---

<objective>
Improve code quality through logging, deduplication, and validation enhancements.

Purpose: Reduce technical debt by eliminating silent failures, duplicate code, and inconsistent patterns
Output: Cleaner, more maintainable codebase with proper error visibility
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add logging to pass statements and warnings for fallback values</name>
  <files>
    quickice/output/gromacs_writer.py
    quickice/gui/dual_viewer.py
    quickice/gui/phase_diagram_widget.py
    quickice/gui/main_window.py
    quickice/phase_mapping/ice_ih_density.py
    quickice/phase_mapping/water_density.py
  </files>
  <action>
Replace empty `pass` statements with proper logging to capture exception details:

1. **Add logging setup** to each affected file:
   - Import: `import logging`
   - Create module logger: `logger = logging.getLogger(__name__)`

2. **Replace pass statements with logging:**
   - `quickice/output/gromacs_writer.py:229, 261` - File read failures
     - Change: `except (IOError, OSError): pass`
     - To: `except (IOError, OSError) as e: logger.warning(f"Could not read file: {e}")`
   
   - `quickice/gui/dual_viewer.py:311, 325` - Index errors
     - Change: `except IndexError: pass`
     - To: `except IndexError as e: logger.debug(f"Invalid selector index: {e}")`
   
   - `quickice/gui/phase_diagram_widget.py:79, 90, 481` - Exceptions
     - Change: `except Exception: pass`
     - To: `except Exception as e: logger.warning(f"Operation failed: {e}")`
   
   - `quickice/gui/main_window.py:846` - Invalid input
     - Change: `except ValueError: pass`
     - To: `except ValueError as e: logger.info(f"Invalid user input: {e}")`

3. **Add fallback density warnings:**
   - `quickice/phase_mapping/ice_ih_density.py:71` - Before return fallback value
     - Add: `logger.warning("Using fallback density value for ice Ih")`
   
   - `quickice/phase_mapping/water_density.py:81, 86` - Before return fallback values
     - Add: `logger.warning("Using fallback density value for water phase")`

4. **Add GRO atom limit warning:**
   - `quickice/output/gromacs_writer.py` around line 304-376 (GRO writing section)
     - Add check: `if atom_count > 99999: logger.warning(f"GRO format wraps atom numbers at 100,000 (have {atom_count})")`

Use `logger.warning()` for issues users should know about, `logger.info()` for expected conditions, `logger.debug()` for development details.
  </action>
  <verify>
    grep -r "pass$" quickice/output/gromacs_writer.py quickice/gui/dual_viewer.py quickice/gui/phase_diagram_widget.py quickice/gui/main_window.py | grep -v "# pass" | wc -l
    # Should return 0 (no bare pass statements in except blocks)
    
    grep -n "logger.warning.*fallback" quickice/phase_mapping/ice_ih_density.py quickice/phase_mapping/water_density.py
    # Should find warning calls
    
    grep -n "logger.warning.*atom.*99999\|100,000" quickice/output/gromacs_writer.py
    # Should find GRO limit warning
  </verify>
  <done>
    - All 8+ empty pass statements replaced with logging
    - Fallback density warnings present in ice_ih_density.py and water_density.py
    - GRO atom limit warning present in gromacs_writer.py
    - No bare `pass` statements in exception handlers
  </done>
</task>

<task type="auto">
  <name>Task 2: Consolidate duplicate functions into shared utility module</name>
  <files>
    quickice/utils/__init__.py
    quickice/utils/molecule_utils.py
    quickice/structure_generation/modes/pocket.py
    quickice/structure_generation/modes/slab.py
    quickice/structure_generation/modes/piece.py
    quickice/output/gromacs_writer.py
    quickice/structure_generation/hydrate_generator.py
    quickice/structure_generation/ion_inserter.py
  </files>
  <action>
Create centralized utility module to eliminate duplicate code:

1. **Create quickice/utils/ directory structure:**
   - Create: `quickice/utils/__init__.py`
     - Content: `"""Utility functions for QuickIce."""`
   
   - Create: `quickice/utils/molecule_utils.py`

2. **Consolidate _count_guest_atoms (4 implementations):**
   
   In `quickice/utils/molecule_utils.py`, create:
   ```python
   """Molecule utility functions for atom counting and indexing."""
   
   def count_guest_atoms(atom_names: list[str], start: int) -> int:
       """Count atoms in a guest molecule starting at index.
       
       Handles multiple guest types:
       - Me: 1 atom (united-atom methane)
       - C: 5 atoms (all-atom methane: C + 4H) - C-first format
       - H: 5 atoms (all-atom methane: H, H, H, H, C) - H-first format (GenIce2 output)
       - H: 2 atoms (H2 molecule)
       - THF: 13 atoms (starts with O or C)
       
       Args:
           atom_names: List of atom names
           start: Starting index
       
       Returns:
           Number of atoms in this guest molecule
       """
       # Copy implementation from quickice/structure_generation/modes/slab.py:107-152
       # (This is the most comprehensive version)
   ```

   Update all 4 locations to import and use:
   - `quickice/structure_generation/modes/pocket.py:70` - Remove function, add import
   - `quickice/structure_generation/modes/slab.py:107` - Remove function, add import
   - `quickice/structure_generation/modes/piece.py:91` - Remove function, add import
   - `quickice/output/gromacs_writer.py:814` - Remove function, add import
   
   Add import: `from quickice.utils.molecule_utils import count_guest_atoms`
   Change calls: `_count_guest_atoms(...)` → `count_guest_atoms(...)`

3. **Consolidate molecule index building (2 implementations):**
   
   In `quickice/utils/molecule_utils.py`, add:
   ```python
   def build_molecule_index(atom_names: list[str], residue_names: list[str]) -> list:
       """Build molecule index from atom and residue names.
       
       Groups atoms into molecules based on residue boundaries.
       
       Args:
           atom_names: List of atom names
           residue_names: List of residue names
       
       Returns:
           List of molecule indices grouped by residue
       """
       # Merge implementations from:
       # - quickice/structure_generation/hydrate_generator.py:476 (_build_molecule_index)
       # - quickice/structure_generation/ion_inserter.py:60 (_build_molecule_index_from_structure)
       # Use the more general approach
   ```

   Update 2 locations:
   - `quickice/structure_generation/hydrate_generator.py:476` - Remove function, add import
   - `quickice/structure_generation/ion_inserter.py:60` - Remove function, add import
   
   Add import: `from quickice.utils.molecule_utils import build_molecule_index`

Ensure all imports are at module level (top of file) following Python conventions.
  </action>
  <verify>
    grep -rn "def _count_guest_atoms" quickice/
    # Should return no results (function removed from all locations)
    
    grep -rn "from quickice.utils.molecule_utils import" quickice/
    # Should find 6 imports (4 for count_guest_atoms, 2 for build_molecule_index)
    
    ls -la quickice/utils/molecule_utils.py
    # File should exist
    
    python3 -c "from quickice.utils.molecule_utils import count_guest_atoms, build_molecule_index; print('Imports work')"
    # Should print "Imports work"
  </verify>
  <done>
    - quickice/utils/molecule_utils.py created with consolidated functions
    - No duplicate _count_guest_atoms functions remain
    - No duplicate molecule index building functions remain
    - All imports updated and working
    - Module can be imported successfully
  </done>
</task>

<task type="auto">
  <name>Task 3: Add validation enhancements and fix parameter naming</name>
  <files>
    quickice/structure_generation/modes/piece.py
  </files>
  <action>
Add validation and fix naming convention violations:

1. **Fix parameter naming inconsistency:**
   - File: `quickice/structure_generation/modes/piece.py:50`
   - Change parameter name: `atoms_perMol` → `atoms_per_mol`
   - Update all references within the file (typically 3-5 occurrences in function body and docstring)
   - This violates PEP 8 snake_case convention for parameters

2. **Add unit validation at data entry points:**
   
   Identify file parsing and user input points where coordinates are received:
   - Look for functions accepting coordinates from external sources
   - Add validation comment or assertion: `# Units: nm (GROMACS standard)`
   - Consider adding validation for obvious mismatches:
     ```python
     # Heuristic: If all coordinates > 10, likely in Å instead of nm
     if coordinates is not None and np.all(coordinates > 10):
         logger.warning("Coordinates may be in Å instead of nm (GROMACS uses nm)")
     ```
   
   Add to key parsing locations:
   - `quickice/output/gromacs_writer.py` - GRO/ITP file parsing sections
   - Any user input handlers in GUI components

3. **Add bounds validation for array operations:**
   
   Identify array slicing/indexing operations that could fail:
   - Add defensive checks before array operations
   - Example pattern:
     ```python
     # Before: array[i:i+count]
     # After:
     if i + count > len(array):
         logger.warning(f"Array bounds exceeded: {i+count} > {len(array)}")
         count = len(array) - i
     ```
   
   Focus on:
   - Coordinate array operations in structure generation
   - Atom index operations in GROMACS writer

Keep validation lightweight - use logging, don't raise exceptions for recoverable cases.
  </action>
  <verify>
    grep -n "atoms_perMol" quickice/structure_generation/modes/piece.py
    # Should return no results (parameter renamed)
    
    grep -n "atoms_per_mol" quickice/structure_generation/modes/piece.py
    # Should find the renamed parameter
    
    python3 -m py_compile quickice/structure_generation/modes/piece.py
    # Should compile without errors
  </verify>
  <done>
    - Parameter `atoms_perMol` renamed to `atoms_per_mol` throughout piece.py
    - Unit validation comments added at key data entry points
    - Bounds validation checks added for array operations
    - File compiles without syntax errors
  </done>
</task>

</tasks>

<verification>
Run comprehensive code quality checks:
1. All files compile: `python3 -m py_compile quickice/utils/molecule_utils.py quickice/structure_generation/modes/piece.py`
2. No duplicate functions: `grep -rn "def _count_guest_atoms" quickice/` returns nothing
3. No bare pass statements: `grep -r "pass$" quickice/output quickice/gui | grep -v "# pass"` returns nothing
4. Imports work: `python3 -c "from quickice.utils.molecule_utils import count_guest_atoms"`
</verification>

<success_criteria>
- All 8 empty pass statements replaced with logging
- Fallback density warnings added (ice_ih_density.py, water_density.py)
- GRO atom limit warning added (gromacs_writer.py)
- 4 duplicate `_count_guest_atoms` functions consolidated into 1
- 2 duplicate molecule index functions consolidated into 1
- Parameter naming fixed (`atoms_perMol` → `atoms_per_mol`)
- Validation enhancements added at key points
- All imports working correctly
</success_criteria>

<output>
After completion, create `.planning/quick/007-code-quality-improvements-logging-dedu/007-SUMMARY.md`
</output>
