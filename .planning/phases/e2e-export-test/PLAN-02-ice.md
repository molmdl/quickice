---
phase: e2e-export-test
plan: 02
type: execute
wave: 2
depends_on: ["e2e-export-test-01"]
files_modified:
  - tests/test_output/test_gromacs_export_ice.py
autonomous: true

must_haves:
  truths:
    - "Ice export creates .gro, .top, and .itp files in output directory"
    - "Cancelled QFileDialog returns False without creating files"
    - ".gro file contains nmolecules * 4 atoms (TIP4P-ICE expansion: O,H,H → OW,HW1,HW2,MW)"
    - ".top file contains [molecules] section with SOL count matching nmolecules"
    - ".itp file is a copy of tip4p-ice.itp"
  artifacts:
    - path: "tests/test_output/test_gromacs_export_ice.py"
      provides: "E2E tests for GROMACSExporter (Tab 0)"
      min_lines: 100
  key_links:
    - from: "tests/test_output/test_gromacs_export_ice.py"
      to: "quickice/gui/export.py"
      via: "import GROMACSExporter"
      pattern: "from quickice\\.gui\\.export import GROMACSExporter"
    - from: "tests/test_output/test_gromacs_export_ice.py"
      to: "tests/test_output/conftest.py"
      via: "pytest fixture injection"
      pattern: "ranked_candidate|mock_save_dialog|tmp_path"
---

<objective>
Test GROMACSExporter (Tab 0 — Ice) end-to-end. This is the simplest exporter and validates the QFileDialog/QMessageBox mock pattern that all subsequent tests will follow.

Purpose: Ice export is the baseline — if the mock pattern works here, it'll work for all 6 exporters. It also validates the 3→4 atom expansion (O,H,H → OW,HW1,HW2,MW) which is unique to ice structures.

Output: `tests/test_output/test_gromacs_export_ice.py` with `TestIceGROMACSExporter` class containing 5 test methods.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/e2e-export-test/e2e-export-test-RESEARCH.md
@.planning/phases/e2e-export-test/PLAN-01-fixtures.md
@quickice/gui/export.py
@quickice/output/gromacs_writer.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create test_gromacs_export_ice.py with 5 test methods</name>
  <files>tests/test_output/test_gromacs_export_ice.py</files>
  <action>
Create `tests/test_output/test_gromacs_export_ice.py` with class `TestIceGROMACSExporter` containing these 5 tests:

**Test 1: `test_export_creates_gro_top_itp`**
- Create GROMACSExporter with `parent_widget=None`
- Use `mock_save_dialog` fixture from conftest, filename "ice_test.gro"
- Call `exporter.export_gromacs(ranked_candidate, T=195, P=1.36)`
- Assert `result is True`
- Assert `(tmp_path / "ice_test.gro").exists()`
- Assert `(tmp_path / "ice_test.top").exists()`
- Assert `(tmp_path / "ice_test.itp").exists()` (note: ITP filename uses .gro stem, NOT "tip4p-ice.itp")

**Test 2: `test_export_cancelled_returns_false`**
- Use `mock_cancel_dialog` fixture with module_path='quickice.gui.export'
- Call `exporter.export_gromacs(ranked_candidate, T=195, P=1.36)`
- Assert `result is False`
- Assert no files created in tmp_path

**Test 3: `test_gro_file_has_correct_atom_count`**
- Export ice, then read the .gro file
- Line 2 of .gro file contains the atom count (integer)
- For `nmolecules=1`, expect `n_atoms = 1 * 4 = 4` (TIP4P-ICE expansion: O,H,H → OW,HW1,HW2,MW)
- Parse the atom count from line 2: `int(lines[1].strip())`
- Assert atom count == 4

**Test 4: `test_gro_file_has_tip4p_atom_names`**
- Export ice, read .gro file lines 3-6 (4 atoms for 1 molecule)
- Assert atom names are OW, HW1, HW2, MW (columns 10-13 of each GRO line)
- This validates the 3→4 expansion: the input candidate has O,H,H but the output has OW,HW1,HW2,MW

**Test 5: `test_top_file_has_molecules_section`**
- Export ice, read .top file content
- Assert content contains `[ molecules ]`
- Assert content contains `SOL` with molecule count matching `nmolecules`
- For 1 molecule: expect `SOL  1` or `SOL    1`

**Mock pattern for each test:**
```python
def test_export_creates_gro_top_itp(self, ranked_candidate, mock_save_dialog):
    from quickice.gui.export import GROMACSExporter
    
    save_path, dialog_p, mb_p = mock_save_dialog("ice_test.gro")
    exporter = GROMACSExporter(parent_widget=None)
    
    with dialog_p, mb_p:
        result = exporter.export_gromacs(ranked_candidate, T=195, P=1.36)
    
    assert result is True
    # Check files exist
    tmp_path = Path(save_path).parent
    assert (tmp_path / "ice_test.gro").exists()
    assert (tmp_path / "ice_test.top").exists()
    assert (tmp_path / "ice_test.itp").exists()
```

**IMPORTANT notes:**
- The ITP destination filename is `{stem}.itp` where stem comes from the .gro filename. For "ice_test.gro", the ITP is "ice_test.itp", NOT "tip4p-ice.itp". This is documented in RESEARCH line 43.
- The .gro file second line is the atom count as a zero-padded integer.
- GRO format: residue number (5 chars), residue name (5 chars, left-padded), atom name (5 chars, left-padded), atom number (5 chars), then 3 floats for x,y,z (8.3f each).
- The atom name is extracted from positions 10:15 (0-indexed) in each GRO line.
- Do NOT use a QApplication — GROMACSExporter only needs QFileDialog and QMessageBox which are fully mocked.
  </action>
  <verify>
    cd /share/home/nglokwan/quickice && python -m pytest tests/test_output/test_gromacs_export_ice.py -v --tb=short 2>&1 | tail -30
  </verify>
  <done>
    - 5 test methods in TestIceGROMACSExporter class
    - All 5 pass: creates files, cancelled returns False, correct atom count (4 for 1 molecule), TIP4P atom names, [molecules] section
    - Mock pattern validated for use by Plans 03-08
  </done>
</task>

</tasks>

<verification>
```bash
cd /share/home/nglokwan/quickice && python -m pytest tests/test_output/test_gromacs_export_ice.py -v
```
All 5 tests pass.
</verification>

<success_criteria>
- test_gromacs_export_ice.py exists with TestIceGROMACSExporter class
- 5/5 tests pass
- .gro file has nmolecules * 4 atoms (not nmolecules * 3)
- .itp filename matches .gro stem (not "tip4p-ice.itp")
- Cancelled dialog returns False
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-export-test/e2e-export-test-02-SUMMARY.md`
</output>
