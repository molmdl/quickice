---
phase: e2e-compute-export
plan: 06
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/output/gromacs_writer.py
  - tests/e2e_export_helpers.py
autonomous: true

must_haves:
  truths:
    - "write_ion_top_file writes GAFF2 atomtypes for solutes (c3,hc for CH4; os,c5,hc,h1 for THF) directly into TOP [atomtypes] section"
    - "write_ion_top_file [molecules] section uses ITP moleculetype name (e.g., etoh) not registry default (MOL) for custom molecules"
    - "write_ion_top_file does not produce duplicate atomtype definitions when guests and custom molecules share GAFF2 types"
    - "write_solute_top_file and write_custom_molecule_top_file have the same three fixes applied"
    - "_stage_itp_files() helper copies all #include-referenced ITPs to workspace with atomtypes commented out"
    - "run_gmx_grompp() helper executes gmx grompp and returns exit code + stderr"
  artifacts:
    - path: "quickice/output/gromacs_writer.py"
      provides: "Fixed TOP writers with correct atomtypes, moleculetype names, deduplication"
      contains: "needs_ch4_atomtypes"
    - path: "tests/e2e_export_helpers.py"
      provides: "GROMACS grompp validation helpers"
      exports: ["_stage_itp_files", "run_gmx_grompp", "MDP_PATH"]
  key_links:
    - from: "quickice/output/gromacs_writer.py"
      to: "quickice/structure_generation/itp_parser.py"
      via: "parse_itp_file for moleculetype name extraction"
      pattern: "parse_itp_file"
    - from: "tests/e2e_export_helpers.py"
      to: "quickice/output/gromacs_writer.py"
      via: "comment_out_atomtypes_in_itp import for ITP staging"
      pattern: "comment_out_atomtypes_in_itp"
---

<objective>
Fix three GROMACS-simulation-blocking bugs in TOP writers and add grompp validation helpers.

Purpose: The existing 116 bridge tests validate file CONTENT (parsing GRO/TOP/ITP), but no test
actually runs GROMACS on exported files. Manual gmx grompp testing reveals three bugs that prevent
GROMACS from processing the exported files. This plan fixes all three bugs and adds the helper
infrastructure needed for Plan 07's grompp validation tests.

Bugs discovered:
1. Solute atomtypes not written: ch4_liquid.itp and thf_liquid.itp have [atomtypes] pre-commented;
   parse_itp_atomtypes() returns empty, so solute GAFF2 atomtypes (c3, hc, os, c5, h1) are missing
   from the TOP [atomtypes] section. GROMACS error: "Atomtype c3 not found".
2. Moleculetype name mismatch: [molecules] section writes "MOL" (registry default) but etoh.itp
   defines moleculetype "etoh". GROMACS error: "No such moleculetype MOL".
3. Duplicate atomtypes: When GAFF2 guest section and custom molecule section both write the same
   atomtype (e.g., hc, h1 for THF+etoh), GROMACS warns about redefined atomtypes.

Output: Fixed gromacs_writer.py with all three bugs resolved, plus e2e_export_helpers.py extended
with ITP staging and grompp runner helpers.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@quickice/output/gromacs_writer.py
@quickice/structure_generation/itp_parser.py
@quickice/structure_generation/gromacs_ion_export.py
@quickice/data/custom/etoh.itp
@quickice/data/ch4_liquid.itp
@quickice/data/tip4p-ice.itp
@tests/e2e_export_helpers.py
@tests/em.mdp
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix write_ion_top_file — solute atomtypes, moleculetype name, dedup</name>
  <files>quickice/output/gromacs_writer.py</files>
  <action>
Fix three bugs in `write_ion_top_file()` (lines ~1626-1841):

**Bug 1: Solute atomtypes not written (CRITICAL — blocks gmx grompp)**

The current code (lines ~1721-1748) tries to parse atomtypes from the solute ITP file
(ch4_liquid.itp or thf_liquid.itp), but these files have [atomtypes] ALREADY commented out
(pre-modified in the data directory), so `parse_itp_atomtypes()` returns empty. The writer then
writes a comment like `; CH4 atom types defined in ch4_liquid.itp` instead of actual atomtype
definitions. GROMACS can't find c3/hc/os/c5/h1 atomtypes.

Fix: Replace the "parse from ITP" approach with HARDCODED GAFF2 atomtypes, combined with the
existing GAFF2 guest section. The solute atomtypes are the SAME as the guest atomtypes for the
same molecule type (CH4 uses c3+hc; THF uses os+c5+hc+h1).

Replace the current guest+solute atomtypes logic (lines ~1708-1748) with a combined section:

```python
# Determine which GAFF2 atomtype sets are needed
needs_ch4_atomtypes = (guest_count > 0 and guest_type == "ch4") or \
                      (has_solutes and ion_structure.solute_type.upper() == "CH4")
needs_thf_atomtypes = (guest_count > 0 and guest_type == "thf") or \
                      (has_solutes and ion_structure.solute_type.upper() == "THF")

if needs_ch4_atomtypes:
    f.write("; CH4 atom types (GAFF2)\n")
    f.write("c3        c3        6             12.0107  0.0     A      3.39771e-1    4.51035e-1\n")
    f.write("hc        hc        1              1.0079  0.0     A      2.60018e-1    8.70272e-2\n")

if needs_thf_atomtypes:
    f.write("; THF atom types (GAFF2)\n")
    f.write("os        os        8             15.9994  0.0     A      3.15610e-1    3.03758e-1\n")
    f.write("c5        c5        6             12.0107  0.0     A      3.39771e-1    4.51035e-1\n")
    f.write("hc        hc        1              1.0079  0.0     A      2.60018e-1    8.70272e-2\n")
    f.write("h1        h1        1              1.0079  0.0     A      2.42200e-1    8.70272e-2\n")
```

REMOVE the old "solute atom types" parsing block (lines ~1721-1748) entirely — it's replaced
by the combined GAFF2 section above.

**Bug 2: Moleculetype name mismatch (CRITICAL — blocks gmx grompp)**

The [molecules] section currently writes "MOL" for custom molecules (from
`custom_molecule_moleculetype`), but the ITP file defines moleculetype "etoh". GROMACS requires
the [molecules] name to match the ITP [moleculetype] name.

Fix: Parse the actual moleculetype name from the ITP file and use it in [molecules].
At the top of `write_ion_top_file`, add import:
```python
from quickice.structure_generation.itp_parser import parse_itp_file
```

Replace the [molecules] custom molecule line (around line 1822-1825):
```python
# OLD:
custom_mol_name = ion_structure.custom_molecule_moleculetype if ion_structure.custom_molecule_moleculetype else "CUSTOM"

# NEW:
custom_mol_name = "CUSTOM"  # fallback
if ion_structure.custom_itp_path:
    from pathlib import Path as FilePath
    custom_itp_path = FilePath(ion_structure.custom_itp_path)
    if custom_itp_path.exists():
        try:
            itp_info = parse_itp_file(custom_itp_path)
            custom_mol_name = itp_info.molecule_name
        except Exception:
            if ion_structure.custom_molecule_moleculetype:
                custom_mol_name = ion_structure.custom_molecule_moleculetype
    elif ion_structure.custom_molecule_moleculetype:
        custom_mol_name = ion_structure.custom_molecule_moleculetype
```

The GRO file can continue to use "MOL" as the residue name — GROMACS doesn't require residue
names to match moleculetype names. Only [molecules] entries must match ITP [moleculetype] names.

**Bug 3: Duplicate atomtypes (WARNING — causes gmx grompp warnings)**

When the GAFF2 section writes hc/h1 for THF guest AND the custom molecule section writes
hc/h1 for etoh, GROMACS warns about redefined atomtypes.

Fix: Track written atomtype names in a set and skip duplicates when writing custom molecule
atomtypes. After writing TIP4P-ICE, ion, and GAFF2 atomtypes:

```python
# Track written atomtype names for deduplication
_written_atomtypes = {"OW_ice", "HW_ice", "MW"}
if na_count > 0: _written_atomtypes.add("NA")
if cl_count > 0: _written_atomtypes.add("CL")
if needs_ch4_atomtypes: _written_atomtypes.update({"c3", "hc"})
if needs_thf_atomtypes: _written_atomtypes.update({"os", "c5", "hc", "h1"})
```

Then when writing custom molecule atomtypes (lines ~1750-1763), skip duplicates:
```python
if has_custom and ion_structure.custom_itp_path:
    from pathlib import Path as FilePath
    custom_itp_path = FilePath(ion_structure.custom_itp_path)
    if custom_itp_path.exists():
        custom_atomtypes = parse_itp_atomtypes(custom_itp_path)
        if custom_atomtypes:
            custom_mol_name = ...  # from Bug 2 fix
            f.write(f"; {custom_mol_name} custom molecule atom types\n")
            for atomtype in custom_atomtypes:
                if len(atomtype) >= 8 and atomtype[0] not in _written_atomtypes:
                    f.write(f"{atomtype[0]:<8s} {atomtype[1]:<8s} {atomtype[2]:>6s} {atomtype[3]:>12s} {atomtype[4]:>6s} {atomtype[5]:<4s} {atomtype[6]:>12s} {atomtype[7]:>12s}\n")
                    _written_atomtypes.add(atomtype[0])
```

IMPORTANT: Do NOT modify any GRO writer functions. The GRO residue name "MOL" is fine.
Do NOT modify write_interface_top_file — it doesn't have solutes or custom molecules.
  </action>
  <verify>cd /share/home/nglokwan/quickice && python3 -c "
import sys; sys.path.insert(0, 'tests')
from pathlib import Path
import shutil
from quickice.phase_mapping.lookup import lookup_phase
from quickice.structure_generation.generator import IceStructureGenerator
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.types import InterfaceConfig
from quickice.output.gromacs_writer import write_ion_gro_file, write_ion_top_file, comment_out_atomtypes_in_itp
from quickice.structure_generation.gromacs_ion_export import write_ion_itp
from e2e_export_helpers import parse_top_includes, parse_top_molecules, _insert_custom_molecules, _insert_solutes, _insert_ions_from_solute
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
import quickice
data_dir = Path(quickice.__file__).parent / 'data'

# Build F6 (CH4 solute — tests Bug 1 fix)
phase_info = lookup_phase(250, 0.1)
gen = IceStructureGenerator(phase_info, 96)
c = gen.generate_all(1)[0]
interface = generate_interface(c, InterfaceConfig(mode='slab', box_x=3.0, box_y=3.0, box_z=8.0, seed=42, ice_thickness=2.0, water_thickness=4.0))
solute = _insert_solutes(interface, solute_type='CH4', concentration=0.3)
ion = _insert_ions_from_solute(solute, concentration=0.15)

ws = Path('tmp/gmx-verify-06')
ws.mkdir(parents=True, exist_ok=True)
write_ion_gro_file(ion, str(ws / 'f6.gro'))
write_ion_top_file(ion, str(ws / 'f6.top'))
write_ion_itp(ws / 'ion.itp', ion.na_count, ion.cl_count)
shutil.copy(Path('tests/em.mdp'), ws / 'em.mdp')

# Stage ITPs
for itp_name in parse_top_includes(str(ws / 'f6.top')):
    if itp_name == 'ion.itp': continue
    src = data_dir / itp_name
    if not src.exists(): src = data_dir / 'custom' / itp_name
    if src.exists():
        content = src.read_text()
        if '[ atomtypes ]' in content.lower(): content = comment_out_atomtypes_in_itp(content)
        (ws / itp_name).write_text(content)

# Verify atomtypes
with open(ws / 'f6.top') as f:
    content = f.read()
    assert 'c3' in content, 'c3 atomtype missing from TOP'
    assert 'hc' in content, 'hc atomtype missing from TOP'

# Verify moleculetype name for F1
registry = MoleculetypeRegistry()
registry.register_liquid_solute('CH4')
custom = _insert_custom_molecules(interface, n_molecules=3)
solute2 = _insert_solutes(custom, solute_type='CH4', concentration=0.3)
ion2 = _insert_ions_from_solute(solute2, concentration=0.15)
write_ion_top_file(ion2, str(ws / 'f1.top'))
mols = parse_top_molecules(str(ws / 'f1.top'))
assert 'etoh' in mols, f'Expected etoh in [molecules], got: {mols}'

print('ALL CHECKS PASSED')
" 2>&1 | tail -5</verify>
  <done>
1. F6 TOP file contains c3 and hc atomtype definitions in [atomtypes] section (not just a comment)
2. F1 TOP [molecules] section lists "etoh" instead of "MOL" for custom molecules
3. F4 TOP [atomtypes] section has no duplicate atomtype names (hc and h1 appear only once)
4. All existing bridge tests still pass (pytest tests/test_e2e_*.py)
  </done>
</task>

<task type="auto">
  <name>Task 2: Fix write_solute_top_file + write_custom_molecule_top_file + add grompp helpers</name>
  <files>quickice/output/gromacs_writer.py, tests/e2e_export_helpers.py</files>
  <action>
**Part A: Fix write_solute_top_file (lines ~2478-2698)**

Apply the same three fixes as Task 1:

1. **Solute atomtypes**: Replace the ITP-parsing approach (lines ~2593-2614) with hardcoded GAFF2
   atomtypes for CH4 and THF solutes, using the same combined GAFF2 pattern. The solute writer
   doesn't have a guest GAFF2 section currently, but should use the same logic:
   ```python
   if has_solutes:
       solute_type_upper = solute_structure.solute_type.upper()
       if solute_type_upper == "CH4":
           f.write("; CH4 solute atom types (GAFF2)\n")
           f.write("c3        c3        6             12.0107  0.0     A      3.39771e-1    4.51035e-1\n")
           f.write("hc        hc        1              1.0079  0.0     A      2.60018e-1    8.70272e-2\n")
       elif solute_type_upper == "THF":
           f.write("; THF solute atom types (GAFF2)\n")
           f.write("os        os        8             15.9994  0.0     A      3.15610e-1    3.03758e-1\n")
           f.write("c5        c5        6             12.0107  0.0     A      3.39771e-1    4.51035e-1\n")
           f.write("hc        hc        1              1.0079  0.0     A      2.60018e-1    8.70272e-2\n")
           f.write("h1        h1        1              1.0079  0.0     A      2.42200e-1    8.70272e-2\n")
   ```
   REMOVE the old ITP-parsing block for solute atomtypes.

2. **Moleculetype name**: Parse ITP moleculetype name for custom molecules in [molecules] section.
   Same pattern as Task 1 — use `parse_itp_file()` on the custom ITP path.

3. **Dedup atomtypes**: Track written atomtype names and skip duplicates when writing custom
   molecule atomtypes. Same pattern as Task 1.

**Part B: Fix write_custom_molecule_top_file (lines ~2051-2200)**

This writer doesn't have solutes, but needs fixes 2 and 3:

1. **Moleculetype name**: Parse ITP moleculetype name for the custom molecule in [molecules].
   Use `parse_itp_file()` on `custom_structure.itp_path`. The current code uses
   `moleculetype_name` which is "MOL" — should be the ITP name (e.g., "etoh").

2. **Dedup atomtypes**: Track written atomtype names (TIP4P-ICE + guest GAFF2 already written)
   and skip duplicates when writing custom molecule atomtypes.

**Part C: Add grompp validation helpers to tests/e2e_export_helpers.py**

Add the following at the end of the file (after the existing chain-building helpers):

```python
# ── GROMACS grompp validation helpers ─────────────────────────────────────────

MDP_PATH = Path(__file__).resolve().parent / "em.mdp"
"""Path to the energy minimization MDP file for grompp validation."""


def _stage_itp_files(top_path: str, workspace: Path) -> list[str]:
    """Copy all #include-referenced ITP files to workspace with atomtypes commented out.
    
    Reads the TOP file, finds #include directives, locates source ITP files in
    quickice/data/ (or quickice/data/custom/ for custom molecule ITPs), applies
    comment_out_atomtypes_in_itp() if the ITP has an active [atomtypes] section,
    and writes the (possibly modified) ITP to the workspace directory.
    
    Skips ion.itp (already generated by write_ion_itp in the workspace).
    
    Args:
        top_path: Path to the .top file to scan for #include directives
        workspace: Directory to copy ITP files into
        
    Returns:
        List of ITP filenames that were staged
    """
    from quickice.output.gromacs_writer import comment_out_atomtypes_in_itp
    
    import quickice
    data_dir = Path(quickice.__file__).parent / "data"
    custom_data_dir = data_dir / "custom"
    
    includes = parse_top_includes(top_path)
    staged = []
    
    for itp_name in includes:
        # Skip ion.itp — generated by write_ion_itp(), already in workspace
        if itp_name == "ion.itp":
            continue
        
        # Find source ITP file
        src = data_dir / itp_name
        if not src.exists():
            src = custom_data_dir / itp_name
        
        if not src.exists():
            # ITP not found — skip with warning
            continue
        
        # Read and optionally comment out atomtypes
        content = src.read_text()
        if "[ atomtypes ]" in content.lower():
            content = comment_out_atomtypes_in_itp(content)
        
        # Write to workspace
        (workspace / itp_name).write_text(content)
        staged.append(itp_name)
    
    return staged


def run_gmx_grompp(workspace: Path, gro_file: str = "struct.gro",
                    top_file: str = "struct.top",
                    mdp_file: str = "em.mdp",
                    tpr_file: str = "em.tpr",
                    maxwarn: int = 5) -> tuple[int, str]:
    """Run gmx grompp in the workspace directory and return exit code + stderr.
    
    Args:
        workspace: Directory containing all input files (.gro, .top, .itp, .mdp)
        gro_file: Name of .gro file (relative to workspace)
        top_file: Name of .top file (relative to workspace)
        mdp_file: Name of .mdp file (relative to workspace)
        tpr_file: Name of output .tpr file (relative to workspace)
        maxwarn: Maximum number of warnings to accept
        
    Returns:
        Tuple of (exit_code, stderr_text). exit_code 0 means success.
    """
    import subprocess
    
    cmd = [
        "gmx", "grompp",
        "-f", mdp_file,
        "-c", gro_file,
        "-p", top_file,
        "-o", tpr_file,
        "-maxwarn", str(maxwarn),
    ]
    
    result = subprocess.run(
        cmd,
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=60,
    )
    
    return result.returncode, result.stderr
```

Add `import subprocess` at the top of the file is NOT needed (it's inside the function).

NOTE: The `MDP_PATH` constant uses the same pattern as the existing `DATA_DIR` and `ETOH_GRO/ETOH_ITP` constants at the top of the file.
  </action>
  <verify>cd /share/home/nglokwan/quickice && python3 -c "
import sys; sys.path.insert(0, 'tests')
from e2e_export_helpers import MDP_PATH, _stage_itp_files, run_gmx_grompp
from pathlib import Path

# Verify MDP_PATH exists
assert MDP_PATH.exists(), f'MDP not found at {MDP_PATH}'

# Verify _stage_itp_files is callable
assert callable(_stage_itp_files), '_stage_itp_files not callable'

# Verify run_gmx_grompp is callable
assert callable(run_gmx_grompp), 'run_gmx_grompp not callable'

print('HELPER CHECKS PASSED')
" && python3 -c "
import sys; sys.path.insert(0, 'tests')
from pathlib import Path
import shutil
from quickice.phase_mapping.lookup import lookup_phase
from quickice.structure_generation.generator import IceStructureGenerator
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.types import InterfaceConfig
from quickice.output.gromacs_writer import write_ion_gro_file, write_ion_top_file, comment_out_atomtypes_in_itp
from quickice.structure_generation.gromacs_ion_export import write_ion_itp
from e2e_export_helpers import (
    parse_top_includes, parse_top_molecules,
    _insert_custom_molecules, _insert_solutes, _insert_ions_from_solute,
    _hydrate_sI_thf_candidate, _make_slab_interface, _stage_itp_files, run_gmx_grompp, MDP_PATH
)
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry

# Test F4 full pipeline (most complex — tests ALL 3 fixes)
hydrate = _hydrate_sI_thf_candidate()
interface = _make_slab_interface(hydrate)
registry = MoleculetypeRegistry()
registry.register_hydrate_guest('THF')
custom = _insert_custom_molecules(interface, n_molecules=3)
solute = _insert_solutes(custom, solute_type='THF', concentration=0.3)
ion = _insert_ions_from_solute(solute, concentration=0.15)

ws = Path('tmp/gmx-verify-06b')
ws.mkdir(parents=True, exist_ok=True)
write_ion_gro_file(ion, str(ws / 'struct.gro'))
write_ion_top_file(ion, str(ws / 'struct.top'))
write_ion_itp(ws / 'ion.itp', ion.na_count, ion.cl_count)
shutil.copy(MDP_PATH, ws / 'em.mdp')

# Stage ITPs using the new helper
staged = _stage_itp_files(str(ws / 'struct.top'), ws)
print(f'Staged: {staged}')

# Check [molecules] uses 'etoh' not 'MOL'
mols = parse_top_molecules(str(ws / 'struct.top'))
assert 'etoh' in mols, f'Expected etoh in [molecules], got: {mols}'

# Run gmx grompp
exit_code, stderr = run_gmx_grompp(ws)
if exit_code != 0:
    print(f'gmx grompp FAILED (exit {exit_code}):')
    print(stderr[-500:])
else:
    print('gmx grompp PASSED for F4!')

# Cleanup
import os; os.remove(str(ws / 'em.tpr')) if (ws / 'em.tpr').exists() else None
" 2>&1 | tail -10</verify>
  <done>
1. write_solute_top_file writes GAFF2 atomtypes for CH4/THF solutes directly (not via ITP parsing)
2. write_solute_top_file [molecules] uses ITP moleculetype name for custom molecules (not "MOL")
3. write_custom_molecule_top_file [molecules] uses ITP moleculetype name (not "MOL")
4. Both writers deduplicate atomtypes against already-written types
5. MDP_PATH, _stage_itp_files(), and run_gmx_grompp() are importable from e2e_export_helpers
6. F4 chain (THF hydrate + custom + THF solute + ions) passes gmx grompp (exit code 0)
  </done>
</task>

</tasks>

<verification>
1. All existing bridge tests still pass: `python -m pytest tests/test_e2e_*.py -x -q`
2. F6 chain (CH4 solute, no custom, no guest) passes gmx grompp
3. F4 chain (THF hydrate + custom + THF solute + ions) passes gmx grompp
4. No duplicate atomtypes in any TOP [atomtypes] section
5. [molecules] section for custom molecules uses ITP moleculetype name (e.g., "etoh")
</verification>

<success_criteria>
1. F6 (Interface→Solute(CH4)→Ion) gmx grompp exits with code 0
2. F1 (Interface→Custom→Solute→Ion) gmx grompp exits with code 0
3. F4 (Hydrate→Interface→Custom→Solute→Ion) gmx grompp exits with code 0
4. _stage_itp_files() copies all referenced ITPs with atomtypes commented
5. run_gmx_grompp() returns exit code 0 on valid input
6. All 116 existing bridge tests still pass
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-compute-export/e2e-compute-export-06-SUMMARY.md`
</output>
