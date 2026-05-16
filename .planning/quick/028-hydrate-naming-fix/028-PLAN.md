---
phase: quick-028
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/data/ch4_hydrate.itp
  - quickice/data/thf_hydrate.itp
  - quickice/structure_generation/moleculetype_registry.py
  - quickice/gui/hydrate_export.py
  - quickice/output/gromacs_writer.py
  - tests/test_moleculetype_registry.py
autonomous: true

must_haves:
  truths:
    - "Hydrate guest molecules use _H suffix (CH4_H, THF_H) in GROMACS topology"
    - "Hydrate .top [ molecules ] entry matches ITP moleculetype name exactly"
    - "ch4_hydrate.itp defines moleculetype CH4_H with resname CH4_H"
    - "thf_hydrate.itp defines moleculetype THF_H with resname THF_H"
    - "Hydrate export copies ch4_hydrate.itp (not ch4.itp) for CH4 guests"
  artifacts:
    - path: "quickice/data/ch4_hydrate.itp"
      provides: "Hydrate-specific CH4 ITP with CH4_H moleculetype"
      contains: "CH4_H"
    - path: "quickice/data/thf_hydrate.itp"
      provides: "Hydrate-specific THF ITP with THF_H moleculetype"
      contains: "THF_H"
    - path: "quickice/structure_generation/moleculetype_registry.py"
      provides: "Registry with _H suffix for hydrate guests"
      contains: "_H"
  key_links:
    - from: "quickice/gui/hydrate_export.py"
      to: "quickice/data/ch4_hydrate.itp"
      via: "_get_hydrate_guest_itp_path()"
      pattern: "_hydrate\\.itp"
    - from: "quickice/output/gromacs_writer.py"
      to: "quickice/data/ch4_hydrate.itp"
      via: "get_hydrate_guest_residue_name()"
      pattern: "_hydrate\\.itp"
---

<objective>
Fix hydrate guest naming consistency for GROMACS compatibility.

Purpose: The current hydrate export produces invalid GROMACS topology — the .top file references `CH4_HYD` (from MoleculetypeRegistry) but the bundled ITP file (`ch4.itp`) defines moleculetype `ch4` with resname `CH4`. GROMACS fails with "moleculetype not found". The fix follows the established `_L` (liquid) pattern by using `_H` (hydrate) suffix and creating hydrate-specific ITP files.

Output: Hydrate exports produce self-consistent GROMACS topology where .top [ molecules ] names match ITP moleculetype definitions exactly.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/quick/028-hydrate-naming-fix/CONTEXT.md

@quickice/structure_generation/moleculetype_registry.py
@quickice/gui/hydrate_export.py
@quickice/output/gromacs_writer.py
@quickice/data/ch4.itp
@quickice/data/ch4_liquid.itp
@quickice/data/thf.itp
@quickice/data/thf_liquid.itp
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create hydrate-specific ITP files and update registry suffix</name>
  <files>quickice/data/ch4_hydrate.itp, quickice/data/thf_hydrate.itp, quickice/structure_generation/moleculetype_registry.py, tests/test_moleculetype_registry.py</files>
  <action>
1. **Create `quickice/data/ch4_hydrate.itp`** by copying `quickice/data/ch4.itp` and making these changes:
   - Change `[ moleculetype ]` name from `ch4` to `CH4_H` (line 11: `CH4_H  3`)
   - Change all `[ atoms ]` resname from `CH4` to `CH4_H` (lines 15-19: column 4 changes to `CH4_H`)
   - Follow the exact same pattern as `ch4_liquid.itp` which uses `CH4_L` moleculetype and `CH4_L` resname

2. **Create `quickice/data/thf_hydrate.itp`** by copying `quickice/data/thf.itp` and making these changes:
   - Change `[ moleculetype ]` name from `thf` to `THF_H` (line 13: `THF_H  3`)
   - Change all `[ atoms ]` resname from `THF` to `THF_H` (lines 17-29: column 4 changes to `THF_H`)
   - Follow the exact same pattern as `thf_liquid.itp` which uses `THF_L` moleculetype and `THF_L` resname

3. **Update `quickice/structure_generation/moleculetype_registry.py`**:
   - Line 16: Change docstring `CH4_HYD` to `CH4_H`
   - Line 19: Add comment about `_H` suffix: `Note: Hydrate guests use _H suffix (5 chars max) for GRO format compatibility.`
   - Line 27: Change example output from `'CH4_HYD'` to `'CH4_H'`
   - Line 31: Change example output from `'CH4_HYD'` to `'CH4_H'`
   - Line 36: Change RESERVED_NAMES from `"CH4_HYD", "CH4_L", "THF_HYD", "THF_L"` to `"CH4_H", "CH4_L", "THF_H", "THF_L"`
   - Line 46: Change docstring `_HYD suffix` to `_H suffix`
   - Line 52: Change docstring `_HYD suffix (e.g., 'CH4_HYD')` to `_H suffix (e.g., 'CH4_H')`
   - Line 56: Change example `'CH4_HYD'` to `'CH4_H'`
   - Line 58: Change `f"{molecule}_HYD"` to `f"{molecule}_H"`
   - Line 154: Change example `'CH4_HYD'` to `'CH4_H'`

4. **Create or update `tests/test_moleculetype_registry.py`** — verify all existing tests pass with `_H` instead of `_HYD`. Search for existing test file first. If it exists, update any `_HYD` references to `_H`. If no test file exists, create one with these tests:
   - `test_register_hydrate_guest_ch4`: `registry.register_hydrate_guest('CH4')` returns `'CH4_H'`
   - `test_register_hydrate_guest_thf`: `registry.register_hydrate_guest('THF')` returns `'THF_H'`
   - `test_get_gromacs_name_hydrate`: `registry.get_gromacs_name('hydrate_CH4')` returns `'CH4_H'`
   - `test_reserved_names_include_h_suffix`: Verify `'CH4_H'` and `'THF_H'` in RESERVED_NAMES
   - `test_reserved_names_exclude_old_suffix`: Verify `'CH4_HYD'` NOT in RESERVED_NAMES
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -m pytest tests/test_moleculetype_registry.py -v 2>&1 | tail -20</verify>
  <done>Hydrate ITP files exist with CH4_H/THF_H moleculetype and resname. Registry uses _H suffix. All tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Update hydrate export to use hydrate-specific ITP files and update gromacs_writer</name>
  <files>quickice/gui/hydrate_export.py, quickice/output/gromacs_writer.py</files>
  <action>
1. **Update `quickice/gui/hydrate_export.py`** — add a `_get_hydrate_guest_itp_path()` function and update export logic:
   - Add new function `_get_hydrate_guest_itp_path(guest_type: str) -> Path` following the exact pattern of the existing `_get_guest_itp_path()` but resolving to `{guest_type}_hydrate.itp` instead of `{guest_type}.itp`:
     ```python
     def _get_hydrate_guest_itp_path(guest_type: str) -> Path:
         """Get the path to a hydrate-specific guest .itp file.
         
         Args:
             guest_type: Guest molecule type ("ch4", "thf")
         
         Returns:
             Path to the hydrate guest .itp file (e.g., ch4_hydrate.itp)
         """
         import quickice
         package_dir = Path(quickice.__file__).parent
         itp_path = package_dir / "data" / f"{guest_type}_hydrate.itp"
         
         if itp_path.exists():
             return itp_path
         
         # Fallback to project root (for development)
         fallback = Path(__file__).parent.parent / "data" / f"{guest_type}_hydrate.itp"
         if fallback.exists():
             return fallback
         
         raise FileNotFoundError(f"No hydrate .itp file found for guest type: {guest_type}")
     ```
   - In `export_hydrate()`, change line 116 from `guest_itp_path = _get_guest_itp_path(config.guest_type)` to `guest_itp_path = _get_hydrate_guest_itp_path(config.guest_type)`
   - In `export_hydrate()`, update comment on line 122 from `# This ensures CH4 gets registered as "CH4_HYD", THF as "THF_HYD"` to `# This ensures CH4 gets registered as "CH4_H", THF as "THF_H"`

2. **Update `quickice/output/gromacs_writer.py`** — add `get_hydrate_guest_residue_name()` function:
   - Add a new function `get_hydrate_guest_residue_name(guest_type: str) -> str` that reads the residue name from the hydrate-specific ITP file (e.g., `ch4_hydrate.itp`):
     ```python
     def get_hydrate_guest_residue_name(guest_type: str) -> str:
         """Get the residue name for a hydrate guest molecule from its hydrate-specific itp file.
         
         Args:
             guest_type: Guest molecule type ("ch4", "thf", etc.)
         
         Returns:
             Residue name from the hydrate ITP file (e.g., "CH4_H", "THF_H")
         """
         try:
             import quickice
             package_dir = Path(quickice.__file__).parent
             itp_path = package_dir / "data" / f"{guest_type}_hydrate.itp"
             
             if not itp_path.exists():
                 itp_path = Path(__file__).parent.parent / "data" / f"{guest_type}_hydrate.itp"
             
             if itp_path.exists():
                 res_name = parse_itp_residue_name(itp_path)
                 if res_name:
                     return res_name
         except Exception as e:
             logger.warning(f"Could not read hydrate guest residue name from ITP file: {e}")
         
         FALLBACK_HYDRATE_NAMES = {
             "ch4": "CH4_H",
             "thf": "THF_H",
             "co2": "CO2_H",
             "h2": "H2_H",
         }
         return FALLBACK_HYDRATE_NAMES.get(guest_type, "UNK_H")
     ```
   - Place this function right after the existing `get_guest_residue_name()` function (after line 390)
   - Also update the `write_multi_molecule_top_file()` function: in the `[ molecules ]` section where it uses `get_guest_residue_name(mol_type)` as fallback (line 1170), this path is already handled by the registry check (lines 1156-1165). Since the hydrate exporter passes a registry with `CH4_H`/`THF_H` registered, the fallback `get_guest_residue_name` won't be hit for hydrate exports. No change needed here — the registry path correctly uses `reg.get_gromacs_name(hydrate_key)` which now returns `CH4_H`.
   - Update the `write_interface_top_file()` function at line 984: change `f'#include "{guest_type}.itp"\n'` to `f'#include "{guest_type}_hydrate.itp"\n'` — because interface guests come from hydrate cages and should use hydrate ITP. Also at line 1008, change `get_guest_residue_name(guest_type)` to `get_hydrate_guest_residue_name(guest_type)` — the [ molecules ] entry must match the ITP moleculetype name.
   - Update the `write_ion_top_file()` function at line 1740: change `f'#include "{guest_type}.itp"\n'` to `f'#include "{guest_type}_hydrate.itp"\n'` — because ion guests come from hydrate cages. Also at line 1630, change `guest_res_name = get_guest_residue_name(guest_type)` to `guest_res_name = get_hydrate_guest_residue_name(guest_type)` — the [ molecules ] entry must match the ITP moleculetype name.
   - Update `export.py` interface exporter (around line 847): change `guest_itp_dest = path.with_name(f"{guest_type}.itp")` to `guest_itp_dest = path.with_name(f"{guest_type}_hydrate.itp")` and change the `_get_guest_itp_path(guest_type)` call to `_get_hydrate_guest_itp_path(guest_type)`. Also add the `_get_hydrate_guest_itp_path` function to `export.py` (or import from hydrate_export — but since these are separate modules, add the function locally following the same pattern).
   - Update `export.py` ion exporter (around line 330): change `guest_itp_dest = path.with_name(f"{guest_type}.itp")` to `guest_itp_dest = path.with_name(f"{guest_type}_hydrate.itp")` and change the `_get_guest_itp_path(guest_type)` call to `_get_hydrate_guest_itp_path(guest_type)`.
   - Update the `MOLECULE_TO_GROMACS` dict (line 30-31): change ch4 and thf itp_file entries from `"ch4.itp"` to `"ch4_hydrate.itp"` and `"thf.itp"` to `"thf_hydrate.itp"` — since these defaults are for hydrate guests.
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -c "from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry; r = MoleculetypeRegistry(); print(r.register_hydrate_guest('CH4')); assert r.register_hydrate_guest('CH4') == 'CH4_H'; print('Registry OK')" && python -c "from quickice.output.gromacs_writer import get_hydrate_guest_residue_name; assert get_hydrate_guest_residue_name('ch4') == 'CH4_H'; assert get_hydrate_guest_residue_name('thf') == 'THF_H'; print('gromacs_writer OK')" && python -m pytest tests/ -k "moleculetype" -v 2>&1 | tail -20</verify>
  <done>Hydrate export uses ch4_hydrate.itp/thf_hydrate.itp. All three exporters (hydrate, interface, ion) use _hydrate.itp and get_hydrate_guest_residue_name(). MOLECULE_TO_GROMACS references _hydrate.itp. Registry returns CH4_H/THF_H.</done>
</task>

</tasks>

<verification>
1. `python -c "from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry; r = MoleculetypeRegistry(); assert r.register_hydrate_guest('CH4') == 'CH4_H'; assert r.register_hydrate_guest('THF') == 'THF_H'"` — registry produces _H suffix
2. `python -c "from quickice.output.gromacs_writer import get_hydrate_guest_residue_name; assert get_hydrate_guest_residue_name('ch4') == 'CH4_H'; assert get_hydrate_guest_residue_name('thf') == 'THF_H'"` — gromacs_writer reads hydrate ITP residue names
3. `grep -c "CH4_H" quickice/data/ch4_hydrate.itp` — hydrate ITP contains CH4_H
4. `grep -c "THF_H" quickice/data/thf_hydrate.itp` — hydrate ITP contains THF_H
5. `grep "_HYD" quickice/structure_generation/moleculetype_registry.py quickice/gui/hydrate_export.py quickice/output/gromacs_writer.py quickice/gui/export.py` — no remaining _HYD references
6. `python -m pytest tests/ -k "moleculetype" -v` — all tests pass
</verification>

<success_criteria>
- MoleculetypeRegistry.register_hydrate_guest() returns CH4_H/THF_H (not CH4_HYD/THF_HYD)
- ch4_hydrate.itp defines moleculetype CH4_H and resname CH4_H
- thf_hydrate.itp defines moleculetype THF_H and resname THF_H
- Hydrate export copies {guest_type}_hydrate.itp files
- Interface and ion exports use {guest_type}_hydrate.itp and get_hydrate_guest_residue_name()
- No _HYD references remain in source code
- All existing tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/028-hydrate-naming-fix/028-SUMMARY.md`
</output>
