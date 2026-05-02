---
phase: 009-split-gromacs-writer
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/output/gromacs_writer.py
  - quickice/output/gromacs/__init__.py
  - quickice/output/gromacs/topology_writer.py
  - quickice/output/gromacs/coordinate_writer.py
  - quickice/output/gromacs/molecule_utils.py
autonomous: true

must_haves:
  truths:
    - "gromacs_writer.py split into modules under quickice/output/gromacs/"
    - "Each module <500 lines with single responsibility"
    - "All GROMACS export functionality preserved"
    - "Imports resolve correctly across codebase"
  artifacts:
    - path: "quickice/output/gromacs/topology_writer.py"
      provides: "TOP/ITP file writing"
      max_lines: 500
    - path: "quickice/output/gromacs/coordinate_writer.py"
      provides: "GRO file writing"
      max_lines: 500
    - path: "quickice/output/gromacs/molecule_utils.py"
      provides: "Molecule indexing utilities"
      max_lines: 500
  key_links:
    - from: "quickice/output/gromacs_writer.py"
      to: "quickice/output/gromacs/*"
      via: "import delegation"
      pattern: "from quickice.output.gromacs import"
---

<objective>
Split gromacs_writer.py (1559 lines) into smaller, focused modules.

Purpose: Improve maintainability and reduce cognitive load
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
  <name>Task 1: Split gromacs_writer.py into modules</name>
  <files>
    quickice/output/gromacs_writer.py
    quickice/output/gromacs/__init__.py
    quickice/output/gromacs/topology_writer.py
    quickice/output/gromacs/coordinate_writer.py
    quickice/output/gromacs/molecule_utils.py
  </files>
  <action>
    Refactor `quickice/output/gromacs_writer.py` (1559 lines) into smaller modules:

    1. **Create module structure**:
       ```
       quickice/output/gromacs/
       ├── __init__.py              # Public API exports
       ├── topology_writer.py       # TopologyWriter class (TOP/ITP)
       ├── coordinate_writer.py     # GRO writing functions
       └── molecule_utils.py        # MoleculeIndex, atom counting
       ```

    2. **Assign responsibilities**:
       - `topology_writer.py`: TopologyWriter class, write_top(), write_itp()
       - `coordinate_writer.py`: write_gro(), coordinate formatting
       - `molecule_utils.py`: MoleculeIndex dataclass, build_molecule_index(), count_guest_atoms()

    3. **Maintain backward compatibility**:
       - Keep `quickice/output/gromacs_writer.py` as thin wrapper
       - Import from new modules: `from quickice.output.gromacs import TopologyWriter, write_gro`
       - Update internal imports across codebase

    4. **Verify line counts**:
       After split, verify each file <500 lines.

    Reference: quickice/output/gromacs_writer.py current structure
  </action>
  <verify>
    - New directory structure created
    - Each file <500 lines
    - All imports resolve (python -m quickice.main --help)
    - GROMACS export works (generate test structure and export)
  </verify>
  <done>gromacs_writer.py refactored into 4 modules under quickice/output/gromacs/, each <500 lines</done>
</task>

</tasks>

<verification>
- [ ] quickice/output/gromacs/ directory exists
- [ ] topology_writer.py <500 lines
- [ ] coordinate_writer.py <500 lines
- [ ] molecule_utils.py <500 lines
- [ ] __init__.py exports public API
- [ ] Old gromacs_writer.py delegates to new modules
- [ ] All imports updated across codebase
- [ ] GROMACS export tested and working
</verification>

<success_criteria>
gromacs_writer.py (1559 lines) split into 4 modules, each <500 lines, all GROMACS export functionality preserved.
</success_criteria>

<output>
After completion, create `.planning/quick/009-split-gromacs-writer/009-SUMMARY.md`
</output>
