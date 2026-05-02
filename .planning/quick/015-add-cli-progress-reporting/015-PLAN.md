---
phase: 015-add-cli-progress-reporting
plan: 01
type: execute
wave: 1
depends_on: [013, 014]
files_modified:
  - quickice/main.py
autonomous: true

must_haves:
  truths:
    - "Progress messages display during long CLI operations"
    - "User sees feedback during structure generation"
    - "Progress shows for hydrate generation"
    - "Progress shows for ion insertion"
    - "Progress shows for export operations"
  artifacts:
    - path: "quickice/main.py"
      provides: "CLI with progress reporting"
      contains: "print.*progress"
  key_links:
    - from: "quickice/main.py"
      to: "stdout"
      via: "print statements"
      pattern: "print.*Generating"
---

<objective>
Add progress reporting to CLI for long-running operations.

Purpose: Provide user feedback during structure generation and export
Output: Progress messages displayed during CLI operations
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/codebase/ARCHITECTURE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add progress reporting to CLI</name>
  <files>quickice/main.py</files>
  <action>
    Add progress reporting to `quickice/main.py` for long operations:

    1. **Add progress reporting functions**:
       ```python
       def report_progress(message: str):
           """Display progress message to user."""
           print(f"[PROGRESS] {message}", file=sys.stderr)
       ```

    2. **Add progress calls at key points**:
       - Structure generation start:
         ```python
         report_progress(f"Generating {args.ice} ice structure...")
         ```
       - Hydrate generation:
         ```python
         report_progress(f"Generating {args.lattice_type} hydrate with {args.guest} guests...")
         ```
       - Ion insertion:
         ```python
         report_progress(f"Inserting ions at {args.ion_concentration} mol/L...")
         ion_count = calculate_ion_count(...)
         report_progress(f"Adding {ion_count} cations and {ion_count} anions...")
         ```
       - Export:
         ```python
         report_progress(f"Writing {output_path}...")
         report_progress(f"Exported {len(structure.atoms)} atoms")
         ```

    3. **Optional: Add tqdm for molecule counting**:
       - If generating large structures (>1000 molecules), show progress bar
       - Wrap loops with tqdm if available:
         ```python
         try:
             from tqdm import tqdm
         except ImportError:
             tqdm = lambda x: x  # Fallback if tqdm not installed
         ```

    4. **Test progress display**:
       ```bash
       python -m quickice --hydrate --lattice-type sI --guest CH4 -o test.gro
       # Should see: [PROGRESS] Generating sI hydrate with CH4 guests...
       #              [PROGRESS] Writing test.gro...
       #              [PROGRESS] Exported 1244 atoms
       ```

    Reference: GUI worker patterns in quickice/gui/workers/
  </action>
  <verify>
    - Progress messages appear during generation
    - Messages show in stderr (separate from stdout for piping)
    - All major operations report progress
    - Final summary shows atom count
  </verify>
  <done>CLI displays progress messages during all long-running operations</done>
</task>

</tasks>

<verification>
- [ ] report_progress function added
- [ ] Progress shown for ice generation
- [ ] Progress shown for hydrate generation
- [ ] Progress shown for ion insertion
- [ ] Progress shown for export
- [ ] Test: python -m quickice --hydrate -o test.gro 2>&1 | grep PROGRESS
</verification>

<success_criteria>
CLI displays progress messages during structure generation, hydrate creation, ion insertion, and export operations.
</success_criteria>

<output>
After completion, create `.planning/quick/015-add-cli-progress-reporting/015-SUMMARY.md`
</output>
