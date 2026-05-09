---
status: verifying
trigger: "Investigate and fix export issues for custom molecules in ion workflow"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:15:00Z
---

## Current Focus

hypothesis: All fixes implemented, ready for testing
test: Run export on test case and verify all three issues are resolved
expecting: 
1. etoh.itp has atomtypes commented
2. main .top includes custom atomtypes
3. GRO file uses 5-char residue names
next_action: Test the fixes

## Symptoms

expected: 
1. Custom mol ITP should have atomtypes commented out with header
2. Main .top should include all atomtypes from all molecule ITPs
3. GRO file should use 5-character residue names (truncate or map)
4. [molecules] section should use the moleculetype name from ITP (etoh, not MOL)

actual:
1. etoh.itp atomtypes section not commented out (lines 3-9)
2. Custom mol atom types not included in main .top file (missing hc, c3, h1, oh, ho)
3. GRO file CH4_LIQ residue name too long (7 chars vs 5 char limit), pushes coordinates

errors: GRO format broken, atomtypes duplicated/missing
reproduction: Run workflow Interface → Custom → Solute → Ion, check tmp/test output files

started: Always broken

## Eliminated

## Evidence

- timestamp: 2026-05-09T00:00:00Z
  checked: tmp/test/etoh.itp (lines 3-9)
  found: [atomtypes] section NOT commented out, contains hc, c3, h1, oh, ho types
  implication: Should be commented like ch4_liquid.itp does

- timestamp: 2026-05-09T00:00:00Z
  checked: tmp/test/ions_32na_32cl_with_7ch4.top (lines 9-18)
  found: [atomtypes] only has OW_ice, HW_ice, MW, NA, CL - no custom mol types
  implication: Missing atomtypes for etoh (hc, c3, h1, oh, ho) and ch4_liquid (c3, hc)

- timestamp: 2026-05-09T00:00:00Z
  checked: tmp/test/ions_32na_32cl_with_7ch4.gro (line 47869)
  found: Residue name "CH4_LIQ" is 7 chars, format line shows coordinates pushed right
  implication: GRO format only allows 5 chars for residue name, breaks parsing

- timestamp: 2026-05-09T00:00:00Z
  checked: quickice/output/gromacs_writer.py line 1444
  found: Solute residue name uses f"{solute_type_upper}_LIQ" which creates 7-char names
  implication: Need to truncate or map to 5-char names

- timestamp: 2026-05-09T00:00:00Z
  checked: quickice/gui/export.py line 347-348
  found: Custom ITP file copied without modification via shutil.copy()
  implication: Need to parse and modify ITP during copy to comment out atomtypes

- timestamp: 2026-05-09T00:00:00Z
  checked: quickice/output/gromacs_writer.py lines 1611-1616
  found: Custom ITP included via #include, but atomtypes not extracted to main .top
  implication: Need to parse custom ITP atomtypes and add to main .top file

- timestamp: 2026-05-09T00:10:00Z
  checked: quickice/output/gromacs_writer.py
  found: Added parse_itp_atomtypes() and comment_out_atomtypes_in_itp() functions
  implication: Can now parse and modify ITP files for proper export

- timestamp: 2026-05-09T00:10:00Z
  checked: quickice/gui/export.py
  found: Updated export_ion_gromacs and export_custom_molecule_gromacs to use comment_out_atomtypes_in_itp
  implication: ITP files will have atomtypes commented during export

- timestamp: 2026-05-09T00:10:00Z
  checked: quickice/output/gromacs_writer.py write_ion_top_file
  found: Added parsing of custom ITP atomtypes to include in main .top
  implication: Custom molecule atomtypes will be in main topology

- timestamp: 2026-05-09T00:10:00Z
  checked: quickice/output/gromacs_writer.py write_ion_gro_file
  found: Added truncation to 5 chars for residue names
  implication: GRO format will be valid even with long moleculetype names

## Resolution

root_cause: 
1. ITP files copied without modification - no atomtype commenting
2. Topology writer didn't parse ITP atomtypes to add to main .top
3. GRO writer used untruncated residue names exceeding 5-char limit

fix: 
1. Created comment_out_atomtypes_in_itp() to modify ITP during export
   - Comments out [ atomtypes ] section with header explaining types are in main .top
   - Preserves all other ITP content unchanged
   
2. Created parse_itp_atomtypes() to extract atomtypes from ITP
   - Supports both 7-column and 8-column atomtype formats
   - Normalizes to 8-column format for consistent .top output
   
3. Updated export functions:
   - export_ion_gromacs: modifies custom and solute ITP during copy
   - export_custom_molecule_gromacs: modifies custom ITP during copy
   
4. Updated topology writers to parse and include atomtypes:
   - write_ion_top_file: parses custom ITP and solute ITP atomtypes
   - write_custom_molecule_top_file: parses custom ITP atomtypes
   - Adds [defaults] and [atomtypes] sections before #include directives
   
5. Added truncation to 5 chars for all GRO residue names:
   - write_ion_gro_file: custom molecules and solutes
   - write_custom_molecule_gro_file: custom molecules
   - Uses [:5] slicing to ensure GRO format compliance

verification: 
- Unit tests: ✓ All passed (comment_out_atomtypes_in_itp, parse_itp_atomtypes, residue truncation)
- Integration test: Shows fixes work correctly
- Requires re-running actual export to generate fixed output files

files_changed: 
- quickice/output/gromacs_writer.py (added functions, updated writers)
- quickice/gui/export.py (updated export handlers)
