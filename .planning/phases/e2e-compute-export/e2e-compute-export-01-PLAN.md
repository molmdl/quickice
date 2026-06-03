---
phase: e2e-compute-export
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/conftest.py
  - tests/test_gromacs_molecule_ordering.py
  - tests/test_e2e_compute_export.py
autonomous: true

must_haves:
  truths:
    - "Ice candidate exported via write_gro_file produces valid .gro with only SOL residues"
    - "Interface structure exported produces .gro with SOL before guests, .top with correct [molecules]"
    - "Custom molecule structure exported produces .gro with SOL before custom molecules"
    - "Solute structure exported produces .gro with SOL before solutes"
    - "Ion structure exported produces .gro with SOL → ions ordering"
    - "Atom count in .gro header matches actual atom lines for every export"
    - ".top [molecules] section lists correct molecule type counts for every export level"
  artifacts:
    - path: "tests/conftest.py"
      provides: "GRO/TOP parsing helper functions (parse_gro_residue_names, parse_gro_atom_count, parse_top_molecules, parse_top_includes)"
      contains: "def parse_gro_residue_names"
    - path: "tests/test_e2e_compute_export.py"
      provides: "Single-structure export e2e tests (~12 tests)"
      contains: "class TestIceExport"
  key_links:
    - from: "tests/conftest.py"
      to: "tests/test_e2e_compute_export.py"
      via: "import of parse_gro_residue_names and parse_top_molecules"
      pattern: "from.*conftest.*import|parse_gro_residue_names|parse_top_molecules"
    - from: "tests/test_e2e_compute_export.py"
      to: "quickice/output/gromacs_writer.py"
      via: "direct writer function calls (no QFileDialog)"
      pattern: "write_(ice|interface|custom_molecule|solute|ion)_(gro|top)_file"
---

<objective>
Add GRO/TOP parsing helpers to conftest.py and create e2e tests that export REAL structures (from GenIce2 fixtures) via pure writer functions, validating .gro atom ordering and .top [molecules] section correctness.

Purpose: Establish the compute→export bridge for single-structure exports (Ice, Interface, Interface+guests, Custom, Solute, Ion) using real GenIce2-generated data — not synthetic fixtures.

Output: Shared parsing helpers in conftest.py + test_e2e_compute_export.py with ~12 passing tests
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@tests/conftest.py
@tests/test_gromacs_molecule_ordering.py
@quickice/output/gromacs_writer.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add GRO/TOP parsing helpers to conftest.py</name>
  <files>tests/conftest.py, tests/test_gromacs_molecule_ordering.py</files>
  <action>
1. Add the following parsing helper functions to the END of `tests/conftest.py` (AFTER the fixture definitions, before any `if __name__` block). These are plain module-level functions, NOT fixtures:

```python
# ── GRO/TOP parsing helpers (shared across e2e export test files) ─────────────

def parse_gro_residue_names(gro_path: str) -> list[str]:
    """Parse residue names from GROMACS .gro file.
    
    GRO format: line 1=title, line 2=atom count, lines 3+=atom records.
    Residue name at columns 6-10 (0-indexed: [5:10]).
    
    Returns list of residue names in file order.
    """
    residue_names = []
    with open(gro_path, 'r') as f:
        lines = f.readlines()
    if len(lines) < 3:
        return residue_names
    for line in lines[2:]:
        if len(line.strip()) < 20:
            continue
        res_name = line[5:10].strip()
        if res_name and not res_name.replace('.', '').replace('-', '').isspace():
            residue_names.append(res_name)
    return residue_names


def parse_gro_atom_count(gro_path: str) -> int:
    """Parse atom count from GROMACS .gro file line 2."""
    with open(gro_path, 'r') as f:
        lines = f.readlines()
    if len(lines) < 2:
        return 0
    return int(lines[1].strip())


def parse_top_molecules(top_path: str) -> dict[str, int]:
    """Parse [molecules] section from GROMACS .top file.
    
    Returns dict mapping molecule type name to count.
    """
    molecules = {}
    in_molecules = False
    with open(top_path, 'r') as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith('['):
                in_molecules = '[ molecules ]' in stripped.lower() or stripped == '[ molecules ]'
                continue
            if not in_molecules:
                continue
            if not stripped or stripped.startswith(';') or stripped.startswith('#'):
                continue
            parts = stripped.split()
            if len(parts) >= 2:
                try:
                    molecules[parts[0]] = int(parts[1])
                except ValueError:
                    continue
    return molecules


def parse_top_includes(top_path: str) -> list[str]:
    """Parse #include directives from GROMACS .top file.
    
    Returns list of included filenames (e.g., ['tip4p-ice.itp', 'ion.itp']).
    """
    includes = []
    with open(top_path, 'r') as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith('#include'):
                # Extract filename from #include "filename.itp"
                start = stripped.find('"')
                end = stripped.rfind('"')
                if start != -1 and end != -1 and end > start:
                    includes.append(stripped[start+1:end])
    return includes
```

2. Update `tests/test_gromacs_molecule_ordering.py` to import `parse_gro_residue_names` from conftest instead of defining it locally:
   - Add `from conftest import parse_gro_residue_names` at the top imports
   - Remove the local `parse_gro_residue_names` function definition (lines 20-62)
   - Note: pytest conftest.py is auto-imported for fixtures but NOT for regular functions. Use explicit import: `from conftest import parse_gro_residue_names` (relative import works since tests/ is the test root)

IMPORTANT: The `parse_gro_residue_names` function in conftest.py must have IDENTICAL logic to the one in test_gromacs_molecule_ordering.py (columns [5:10], same skip logic for box vectors). Copy the implementation exactly.
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -m pytest tests/test_gromacs_molecule_ordering.py -v --no-header -q 2>&1 | tail -5</verify>
  <done>All 4 existing molecule ordering tests still pass; parse_gro_residue_names, parse_gro_atom_count, parse_top_molecules, parse_top_includes are importable from conftest.py</done>
</task>

<task type="auto">
  <name>Task 2: Create test_e2e_compute_export.py with single-structure export tests</name>
  <files>tests/test_e2e_compute_export.py</files>
  <action>
Create `tests/test_e2e_compute_export.py` with end-to-end tests that take REAL GenIce2-generated structures (from conftest.py fixtures) and export them via pure writer functions (no QFileDialog), validating the output .gro and .top files.

Test structure — use `tmp_path` pytest fixture for output directory. Import writer functions directly from `quickice.output.gromacs_writer`. Import parsing helpers from `conftest`. Reuse the chain-building helper pattern from `tests/test_e2e_workflow_chains.py` (copy the inline helper functions: `_insert_custom_molecules`, `_insert_solutes`, `_insert_ions`, `_solute_to_ion_source`, `_insert_ions_from_solute`).

**Class TestIceExport:**
- `test_ice_gro_has_only_sol_residues(self, ice_ih_candidate, tmp_path)`: Call `write_gro_file(ice_ih_candidate, str(tmp_path / "ice.gro"))`. Parse residue names via `parse_gro_residue_names`. Assert ALL residues are "SOL". Assert `parse_gro_atom_count` matches len of residue_names list.
- `test_ice_top_molecules_section(self, ice_ih_candidate, tmp_path)`: Call `write_top_file(ice_ih_candidate, str(tmp_path / "ice.top"))`. Parse via `parse_top_molecules`. Assert `molecules["SOL"] == ice_ih_candidate.nmolecules`.

**Class TestInterfaceExport:**
- `test_interface_gro_sol_only_no_guests(self, interface_slab, tmp_path)`: Call `write_interface_gro_file(interface_slab, ...)`. Parse residue names. Assert all are "SOL" (no guests in plain interface). Assert `parse_gro_atom_count` matches len of residue names.
- `test_interface_top_molecules(self, interface_slab, tmp_path)`: Call `write_interface_top_file(interface_slab, ...)`. Parse molecules dict. Assert `molecules["SOL"] == interface_slab.ice_nmolecules + interface_slab.water_nmolecules`. Assert no guest entry in dict (guest_nmolecules=0).
- `test_interface_hydrate_gro_has_guests(self, interface_hydrate_slab, tmp_path)`: Call `write_interface_gro_file(interface_hydrate_slab, ...)`. Parse residue names. Find SOL and CH4_H residue indices. Assert max(SOL indices) < min(CH4_H indices) — SOL before guests. Assert `parse_gro_atom_count` matches len of residue names.
- `test_interface_hydrate_top_has_guest_itp(self, interface_hydrate_slab, tmp_path)`: Call `write_interface_top_file(interface_hydrate_slab, ...)`. Parse `parse_top_molecules` — assert SOL count and CH4_H count > 0. Parse `parse_top_includes` — assert "ch4_hydrate.itp" in includes AND "tip4p-ice.itp" in includes.

**Class TestCustomMoleculeExport:**
- `test_custom_gro_molecule_ordering(self, interface_slab, tmp_path)`: Build custom structure via `_insert_custom_molecules(interface_slab, n_molecules=3)`. Call `write_custom_molecule_gro_file(custom, str(tmp_path / "custom.gro"))`. Parse residue names. Assert SOL residues exist AND come before any non-SOL residues. Assert atom count matches.
- `test_custom_top_has_itp(self, interface_slab, tmp_path)`: Call `write_custom_molecule_top_file(custom, ...)`. Parse includes — assert "tip4p-ice.itp" AND "etoh.itp" in includes. Parse molecules — assert custom molecule type count == 3.

**Class TestSoluteExport:**
- `test_solute_gro_molecule_ordering(self, interface_slab, tmp_path)`: Build solute via `_insert_solutes(interface_slab, solute_type='CH4', concentration=0.5)`. Call `write_solute_gro_file(solute, ...)`. Parse residue names. Assert SOL before any solute residues. Assert CH4_L (or CH4LIQ — check what registry produces, it should be "CH4_L") residues present.
- `test_solute_top_molecules_and_itp(self, interface_slab, tmp_path)`: Call `write_solute_top_file(solute, ...)`. Parse includes — assert "ch4_liquid.itp" in includes. Parse molecules — assert CH4_L count matches solute.n_molecules.

**Class TestIonExport:**
- `test_ion_gro_molecule_ordering(self, interface_slab, tmp_path)`: Build ion via `_insert_ions(interface_slab, concentration=0.15)`. Call `write_ion_gro_file(ion, ...)`. Parse residue names. Find SOL, NA, CL indices. Assert max(SOL) < min(NA) < min(CL) — correct ordering. Assert atom count matches.
- `test_ion_top_molecules_and_itp(self, interface_slab, tmp_path)`: Call `write_ion_top_file(ion, ...)`. Parse includes — assert "ion.itp" AND "tip4p-ice.itp" in includes. Parse molecules — assert NA count == ion.na_count AND CL count == ion.cl_count.

CRITICAL implementation details:
- Use `from conftest import parse_gro_residue_names, parse_gro_atom_count, parse_top_molecules, parse_top_includes` (NOT `from tests.conftest`)
- Use `from pathlib import Path` and `DATA_DIR = Path(__file__).resolve().parent.parent / "quickice" / "data" / "custom"` for ETOH paths
- Use `tmp_path` pytest fixture (not tempfile) — it's per-test and auto-cleaned
- For CustomMoleculeConfig, use `ETOH_GRO = DATA_DIR / "etoh.gro"` and `ETOH_ITP = DATA_DIR / "etoh.itp"` (same pattern as workflow_chains.py)
- The SoluteInserter needs `inserter.registry.register_hydrate_guest("CH4")` ONLY for hydrate interface tests, NOT for plain interface tests
- CH4_L residue name in GRO: the solute writer uses `solute_structure.registry.get_gromacs_name(f"liquid_{solute_structure.solute_type}")` which returns "CH4_L" (5 chars, fits GRO 5-char limit). Use this in assertions.
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -m pytest tests/test_e2e_compute_export.py -v --no-header -q 2>&1 | tail -15</verify>
  <done>All ~12 single-structure export tests pass: Ice (2), Interface (4), Custom (2), Solute (2), Ion (2). Each test validates .gro residue ordering AND .top [molecules] section. Atom counts in .gro headers match actual atom lines.</done>
</task>

</tasks>

<verification>
1. `python -m pytest tests/test_e2e_compute_export.py -v` — all tests pass
2. `python -m pytest tests/test_gromacs_molecule_ordering.py -v` — existing 4 tests still pass (refactoring didn't break them)
3. `python -m pytest tests/ -k "compute_export" --co -q` — lists all new tests
</verification>

<success_criteria>
1. 4 parsing helper functions added to conftest.py (parse_gro_residue_names, parse_gro_atom_count, parse_top_molecules, parse_top_includes)
2. test_gromacs_molecule_ordering.py updated to import from conftest (no local definition)
3. test_e2e_compute_export.py created with ~12 tests covering all 5 single-structure export types
4. All tests pass with real GenIce2-generated data
5. Atom count verification works for every .gro file
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-compute-export/e2e-compute-export-01-SUMMARY.md`
</output>
