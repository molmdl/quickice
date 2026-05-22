---
phase: e2e-export-test
plan: 05
type: execute
wave: 3
depends_on: ["e2e-export-test-01", "e2e-export-test-04"]
files_modified:
  - tests/test_output/test_gromacs_export_custom.py
autonomous: true

must_haves:
  truths:
    - "Custom molecule export creates .gro, .top, tip4p-ice.itp, and custom ITP"
    - "Custom ITP has [atomtypes] section commented out (comment_out_atomtypes_in_itp applied)"
    - "tip4p-ice.itp is copied (not stem-named)"
    - "Guest ITP is copied conditionally when guests present"
    - "itp_path must point to existing file for read_text() to succeed"
  artifacts:
    - path: "tests/test_output/test_gromacs_export_custom.py"
      provides: "E2E tests for CustomMoleculeGROMACSExporter (Tab 3)"
      min_lines: 120
  key_links:
    - from: "tests/test_output/test_gromacs_export_custom.py"
      to: "quickice/gui/export.py"
      via: "import CustomMoleculeGROMACSExporter"
      pattern: "from quickice\\.gui\\.export import CustomMoleculeGROMACSExporter"
    - from: "tests/test_output/test_gromacs_export_custom.py"
      to: "quickice/output/gromacs_writer.py"
      via: "comment_out_atomtypes_in_itp modifies ITP before writing"
      pattern: "comment_out_atomtypes"
---

<objective>
Test CustomMoleculeGROMACSExporter (Tab 3 — Custom Molecule) end-to-end. This exporter has two unique features: (1) ITP modification via `comment_out_atomtypes_in_itp()`, and (2) the `itp_path` field must point to an existing file that is read with `read_text()`.

Purpose: Validates that `comment_out_atomtypes_in_itp()` is correctly applied to the custom ITP (the [atomtypes] section is commented out in the output but NOT in the source). Also validates that `itp_path` must be a real Path object pointing to an existing file.

Output: `tests/test_output/test_gromacs_export_custom.py` with `TestCustomMoleculeGROMACSExporter` class containing 5 test methods.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/e2e-export-test/e2e-export-test-RESEARCH.md
@.planning/phases/e2e-export-test/PLAN-01-fixtures.md
@quickice/gui/export.py
@quickice/data/custom/etoh.itp
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create test_gromacs_export_custom.py with 5 test methods</name>
  <files>tests/test_output/test_gromacs_export_custom.py</files>
  <action>
Create `tests/test_output/test_gromacs_export_custom.py` with class `TestCustomMoleculeGROMACSExporter` containing these 5 tests:

**Test 1: `test_export_creates_all_files`**
- Use `custom_structure` fixture from conftest (itp_path=Path("quickice/data/custom/etoh.itp"))
- Use `mock_save_dialog`, filename "custom_etoh.gro"
- Call `exporter.export_custom_molecule_gromacs(custom_structure)`
- Assert `result is True`
- Assert files exist: `custom_etoh.gro`, `custom_etoh.top`, `tip4p-ice.itp`, `etoh.itp`
- NOTE: The custom ITP keeps its original name (`etoh.itp`) in the output directory

**Test 2: `test_custom_itp_has_atomtypes_commented_out`**
- Export custom molecule system
- Read the output `etoh.itp` file
- If the source etoh.itp has a `[ atomtypes ]` section:
  - Assert that the output contains `; [ atomtypes ]` (commented header) OR the atomtypes section is prefixed with `;`
  - The `comment_out_atomtypes_in_itp()` function adds `; ` prefix to lines in atomtypes section
- Also read the ORIGINAL etoh.itp and verify it is NOT modified (source file untouched)
- Implementation: check that output file contains the comment header `"; Modified for QuickIce: [atomtypes] commented"` if atomtypes section exists in source

**Test 3: `test_tip4p_ice_itp_copied`**
- Export, then assert `tip4p-ice.itp` exists in output directory
- Read it, assert it contains `[ moleculetype ]` section

**Test 4: `test_export_with_guests_creates_guest_itp`**
- Create a custom_structure variant where `guest_atom_count > 0` and molecule_index has mol_type="guest"
- This requires building a custom_structure with CH4 guest atoms
- Simplest approach: use a custom_structure fixture that includes guests (add to conftest if needed, or build inline)
- Export and assert `ch4_hydrate.itp` exists in output directory
- NOTE: The exporter checks `custom_structure.guest_atom_count > 0 and guest_count > 0` where `guest_count = sum(1 for m in custom_structure.molecule_index if m.mol_type == "guest")`

**Test 5: `test_export_no_guests_no_guest_itp`**
- Use `custom_structure` fixture (which has guest_atom_count=0)
- Export and assert NO `ch4_hydrate.itp` or `thf_hydrate.itp` in output directory

**CRITICAL: itp_path must exist**
The exporter calls `custom_structure.itp_path.read_text()` directly (line 221 of export.py). If `itp_path` is None or points to a nonexistent file, the export will crash with `FileNotFoundError` or `AttributeError`. The conftest fixture MUST use:
```python
itp_path = Path("quickice/data/custom/etoh.itp")
```
This file exists in the repo (verified: quickice/data/custom/etoh.itp).

**comment_out_atomtypes_in_itp behavior (from gromacs_writer.py line 310-353):**
- Finds lines starting with `[` that contain `atomtypes`
- Comments out the header: `; [ atomtypes ]`
- Comments out data lines: `; <original line>`
- Adds comment header: `; Modified for QuickIce: [atomtypes] commented - types defined in main .top file`
- Existing comments (`;` or `#` prefixed) and blank lines are preserved as-is
- If no [atomtypes] section exists in the ITP, the content is returned unchanged

**Guest detection in CustomMolecule exporter (lines 234-253):**
```python
guest_count = sum(1 for m in custom_structure.molecule_index if m.mol_type == "guest")
if custom_structure.guest_atom_count > 0 and guest_count > 0:
    guest_start = custom_structure.ice_atom_count + custom_structure.water_atom_count
    guest_atom_names = custom_structure.atom_names[guest_start:guest_start + custom_structure.guest_atom_count]
    guest_type = detect_guest_type_from_atoms(guest_atom_names)
```
The test for guests must set BOTH `guest_atom_count > 0` AND have `mol_type="guest"` entries in `molecule_index`.
  </action>
  <verify>
    cd /share/home/nglokwan/quickice && python -m pytest tests/test_output/test_gromacs_export_custom.py -v --tb=short 2>&1 | tail -30
  </verify>
  <done>
    - 5 test methods in TestCustomMoleculeGROMACSExporter class
    - All 5 pass
    - Custom ITP has atomtypes commented out (verified by content comparison)
    - tip4p-ice.itp copied correctly
    - Guest ITP conditional logic works
  </done>
</task>

</tasks>

<verification>
```bash
cd /share/home/nglokwan/quickice && python -m pytest tests/test_output/test_gromacs_export_custom.py -v
```
All 5 tests pass.
</verification>

<success_criteria>
- test_gromacs_export_custom.py exists with TestCustomMoleculeGROMACSExporter class
- 5/5 tests pass
- comment_out_atomtypes_in_itp modification verified in output
- etoh.itp source file NOT modified (read-only access)
- Guest ITP conditional logic works (present when guests, absent when no guests)
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-export-test/e2e-export-test-05-SUMMARY.md`
</output>
