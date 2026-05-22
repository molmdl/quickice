---
phase: e2e-export-test
plan: 03
type: execute
wave: 2
depends_on: ["e2e-export-test-01"]
files_modified:
  - tests/test_output/test_gromacs_export_hydrate.py
autonomous: true

must_haves:
  truths:
    - "Hydrate export creates .gro, .top, tip4p-ice.itp, and guest .itp files"
    - "MoleculetypeRegistry produces _H suffix for hydrate guests (CH4 → CH4_H)"
    - "Guest ITP file (ch4_hydrate.itp) is copied to output directory"
    - "Cancelled dialog returns False"
    - "Correct mock path: quickice.gui.hydrate_export.QFileDialog (NOT quickice.gui.export)"
  artifacts:
    - path: "tests/test_output/test_gromacs_export_hydrate.py"
      provides: "E2E tests for HydrateGROMACSExporter (Tab 1)"
      min_lines: 100
  key_links:
    - from: "tests/test_output/test_gromacs_export_hydrate.py"
      to: "quickice/gui/hydrate_export.py"
      via: "import HydrateGROMACSExporter"
      pattern: "from quickice\\.gui\\.hydrate_export import HydrateGROMACSExporter"
    - from: "tests/test_output/test_gromacs_export_hydrate.py"
      to: "tests/test_output/conftest.py"
      via: "simple_hydrate_structure, simple_hydrate_config, mock_hydrate_save_dialog"
      pattern: "simple_hydrate_structure|mock_hydrate_save_dialog"
---

<objective>
Test HydrateGROMACSExporter (Tab 1 — Hydrate) end-to-end. This exporter is in a DIFFERENT module (`hydrate_export.py`) from all other exporters (`export.py`), so the QFileDialog mock path is different — a key risk area.

Purpose: Validates the hydrate-specific mock path and the MoleculetypeRegistry _H suffix pattern. This is the only exporter that uses `write_multi_molecule_gro_file` and `write_multi_molecule_top_file` (all others use structure-specific writers).

Output: `tests/test_output/test_gromacs_export_hydrate.py` with `TestHydrateGROMACSExporter` class containing 5 test methods.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/e2e-export-test/e2e-export-test-RESEARCH.md
@.planning/phases/e2e-export-test/PLAN-01-fixtures.md
@quickice/gui/hydrate_export.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create test_gromacs_export_hydrate.py with 5 test methods</name>
  <files>tests/test_output/test_gromacs_export_hydrate.py</files>
  <action>
Create `tests/test_output/test_gromacs_export_hydrate.py` with class `TestHydrateGROMACSExporter` containing these 5 tests:

**Test 1: `test_export_creates_all_files`**
- Create HydrateGROMACSExporter with `parent_widget=None`
- Use `mock_hydrate_save_dialog` fixture (from conftest), filename "hydrate_test.gro"
- Call `exporter.export_hydrate(simple_hydrate_structure, simple_hydrate_config)`
- Assert `result is True`
- Assert files exist: `hydrate_test.gro`, `hydrate_test.top`, `tip4p-ice.itp`, `ch4_hydrate.itp`
- NOTE: Unlike Ice exporter, the water ITP is always named "tip4p-ice.itp" (not stem-based), and the guest ITP uses its original name (`ch4_hydrate.itp`)

**Test 2: `test_export_cancelled_returns_false`**
- Use `mock_cancel_dialog` with `module_path='quickice.gui.hydrate_export'`
- Call `exporter.export_hydrate(simple_hydrate_structure, simple_hydrate_config)`
- Assert `result is False`

**Test 3: `test_guest_itp_copied`**
- Export hydrate with CH4 guest
- Assert `(tmp_path / "ch4_hydrate.itp").exists()`
- Read file content, assert it contains `[ moleculetype ]` (hydrate guest ITP has moleculetype section)

**Test 4: `test_top_file_references_guest_itp`**
- Export hydrate, read .top file content
- Assert content contains `#include "ch4_hydrate.itp"` (the .top includes the guest ITP)
- Assert content contains `CH4_H` (the registry-registered name for hydrate CH4 guest)

**Test 5: `test_top_file_references_tip4p_ice`**
- Export hydrate, read .top file content
- Assert content contains `#include "tip4p-ice.itp"`
- Assert content contains `SOL` with water molecule count

**Mock pattern:**
```python
def test_export_creates_all_files(self, simple_hydrate_structure, simple_hydrate_config, mock_hydrate_save_dialog):
    from quickice.gui.hydrate_export import HydrateGROMACSExporter
    
    save_path, dialog_p, mb_p = mock_hydrate_save_dialog("hydrate_test.gro")
    exporter = HydrateGROMACSExporter(parent_widget=None)
    
    with dialog_p, mb_p:
        result = exporter.export_hydrate(simple_hydrate_structure, simple_hydrate_config)
    
    assert result is True
    tmp_path = Path(save_path).parent
    assert (tmp_path / "hydrate_test.gro").exists()
    assert (tmp_path / "hydrate_test.top").exists()
    assert (tmp_path / "tip4p-ice.itp").exists()
    assert (tmp_path / "ch4_hydrate.itp").exists()
```

**CRITICAL mock path difference:**
- HydrateGROMACSExporter is in `quickice.gui.hydrate_export`, NOT `quickice.gui.export`
- QFileDialog mock path: `'quickice.gui.hydrate_export.QFileDialog.getSaveFileName'`
- QMessageBox mock path: `'quickice.gui.hydrate_export.QMessageBox'`
- Using the wrong path will cause the mock to not intercept the dialog call, and the real QFileDialog will appear (hanging the test)
- This is explicitly tested in Test 2 with `mock_cancel_dialog(module_path='quickice.gui.hydrate_export')`

**Hydrate export method signature differs from other exporters:**
- All other exporters: `export_xxx(self, structure) -> bool`
- Hydrate: `export_hydrate(self, structure: HydrateStructure, config: HydrateConfig) -> bool`
- The `config` argument is needed because the exporter uses `config.guest_type` and `config.lattice_type` for filename and ITP lookup
  </action>
  <verify>
    cd /share/home/nglokwan/quickice && python -m pytest tests/test_output/test_gromacs_export_hydrate.py -v --tb=short 2>&1 | tail -30
  </verify>
  <done>
    - 5 test methods in TestHydrateGROMACSExporter class
    - All 5 pass
    - Mock path correctly uses quickice.gui.hydrate_export (NOT quickice.gui.export)
    - ch4_hydrate.itp is copied to output directory
    - .top file references CH4_H (registry suffix) and ch4_hydrate.itp
  </done>
</task>

</tasks>

<verification>
```bash
cd /share/home/nglokwan/quickice && python -m pytest tests/test_output/test_gromacs_export_hydrate.py -v
```
All 5 tests pass.
</verification>

<success_criteria>
- test_gromacs_export_hydrate.py exists with TestHydrateGROMACSExporter class
- 5/5 tests pass
- Mock path uses `quickice.gui.hydrate_export` (verified by cancelled test)
- ch4_hydrate.itp is created alongside .gro/.top
- .top contains `CH4_H` (MoleculetypeRegistry _H suffix)
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-export-test/e2e-export-test-03-SUMMARY.md`
</output>
