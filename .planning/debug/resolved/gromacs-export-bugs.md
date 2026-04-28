---
status: resolved
trigger: "Investigate GROMACS export workflow issues: hydrate -> interface -> ion, all using default settings. Bugs: 1. Residues aren't grouped in .gro files 2. Missing [atomtypes] section in ion topology"
created: 2026-04-28T00:00:00Z
updated: 2026-04-28T02:30:00Z
---

## Current Focus

hypothesis: (1) BUG CONFIRMED: write_interface_gro_file writes ice -> guests -> water order, but write_interface_top_file expects ice+water -> guests order. The .gro file has 6380 ice SOL + 447 CH4 + 3337 water SOL, but .top says 9717 SOL (ice+water) + 447 CH4. Order mismatch! (2) BUG CONFIRMED: write_ion_top_file doesn't include [atomtypes] for NA/CL. Need to add it like write_multi_molecule_top_file does.
test: Verified .gro file structure: residues 1-6380 (ice SOL), 6381-6827 (CH4), 6828-10164 (water SOL). .top expects 9717 SOL first, then 447 CH4.
expecting: Bug 1 fix requires reordering .gro file OR .top file to match. Bug 2 fix requires adding [atomtypes] section to write_ion_top_file.
next_action: Determine correct fix approach - reorder .gro to match .top (ice+water first), or reorder .top to match .gro (ice, guest, water)

## Symptoms

expected: 
1. GROMACS .gro files should have properly grouped residues (each molecule's atoms should have the same residue number)
2. ions_28na_28cl.top should have [atomtypes] section defining NA and CL atom types

actual:
1. Looking at interface_slab.gro: File has 41,103 atoms but the topology (interface_slab.top) claims 9717 SOL + 447 CH4 molecules. The .gro file seems to only contain SOL molecules (no CH4 molecules present), or residue numbering is incorrect
2. ions_28na_28cl.top includes "ion.itp" which defines [moleculetype] and [atoms] for NA and CL, but the atom types (NA, CL) are not defined in any [atomtypes] section in either the .top file or the .itp file

errors:
- GROMACS will fail to run with ions_28na_28cl.top because atom types NA and CL are undefined
- Interface .gro/.top mismatch: .gro file residue count doesn't match .top molecule counts

reproduction:
1. Run QuickIce workflow: hydrate -> interface -> ion with default settings
2. Check output files in ./tmp directory
3. Examine interface_slab.gro for residue grouping
4. Examine ions_28na_28cl.top and ion.itp for [atomtypes] section

started: Bugs exist in current export output

## Eliminated

- hypothesis: [none yet]
  evidence: [none yet]
  timestamp: [none yet]

## Evidence

- timestamp: 2026-04-28T00:00:00Z
  checked: Bug report symptoms prefilled
  found: Two bugs identified: (1) residue grouping in .gro files, (2) missing [atomtypes] in ion topology
  implication: Need to investigate gromacs_writer.py and gromacs_ion_export.py

- timestamp: 2026-04-28T00:30:00Z
  checked: interface_slab.gro residue numbering
  found: CH4 molecules present (2235 atoms = 447 × 5), but residue numbers start at 6381 instead of 9718. The residue 6381 appears in line 25523 of .gro file. SOL residues go up to at least 10164.
  implication: Residue numbering is incorrect - CH4 should start at 9718 (after 9717 SOL). Either ice_nmolecules is wrong or residue numbering logic has bug.

- timestamp: 2026-04-28T00:35:00Z
  checked: ions_28na_28cl.top and ion.itp content
  found: ions_28na_28cl.top includes "ion.itp" which has [moleculetype] and [atoms] for NA/CL, but NO [atomtypes] section defining NA and CL atom types. The main .top file also lacks [atomtypes] for ions.
  implication: Ion export workflow doesn't include [atomtypes] for NA and CL. Need to trace how ion topology is generated.

- timestamp: 2026-04-28T00:40:00Z
  checked: gromacs_ion_export.py generate_ion_itp function
  found: Function only generates [moleculetype] and [atoms] sections, does NOT generate [atomtypes] section. The Madrid2019 ion parameters (NA_SIGMA, NA_EPSILON, etc.) are defined but never written to file.
  implication: Root cause of bug 2 - ion.itp needs [atomtypes] OR main .top needs to include them (like write_multi_molecule_top_file does).

- timestamp: 2026-04-28T01:00:00Z
  checked: interface_slab.gro structure analysis
  found: "CONFIRMED BUG 1 - ORDER MISMATCH: .gro file order is: (1) ice SOL 6380 mol, (2) CH4 447 mol, (3) water SOL 3337 mol = 9717 total SOL. But .top file expects: SOL 9717 (ice+water combined) then CH4 447. The .gro writes ice->guest->water but .top expects ice+water->guest."
  implication: GROMACS uses [molecules] to group consecutive atoms into molecules. Order in .gro MUST match order in .top [molecules] section.

- timestamp: 2026-04-28T01:10:00Z
  checked: write_ion_top_file function (line 1334-1419)
  found: "CONFIRMED BUG 2 - MISSING [atomtypes]: write_ion_top_file does NOT write [atomtypes] section for NA and CL. Compare to write_multi_molecule_top_file (line 1062-1104) which correctly adds ion [atomtypes]. The Madrid2019 parameters exist in gromacs_ion_export.py but are never used."
  implication: Need to add [atomtypes] section to write_ion_top_file, similar to write_multi_molecule_top_file.

## Resolution

root_cause: |
  BUG 1 - Order Mismatch: write_interface_gro_file writes ice->guest->water order, 
  but write_interface_top_file wrote SOL (ice+water)->guests order. The .gro file order 
  (ice->guest->water) doesn't match .top [molecules] section order (SOL->guest).
  This causes GROMACS to misidentify molecules since it uses [molecules] to group 
  consecutive atoms.
  
  Evidence: interface_slab.gro has 10164 residues in order: 1-6380 (ice SOL), 
  6381-6827 (CH4), 6828-10164 (water SOL). But original interface_slab.top 
  had only 2 entries: "SOL 9717" and "CH4 447".
  
  BUG 2 - Missing [atomtypes]: write_ion_top_file didn't include [atomtypes] section 
  for NA and CL ions. The Madrid2019 ion parameters are defined in gromacs_ion_export.py 
  but never written to the .top file. GROMACS requires atom types to be defined before use.
  
  Evidence: ions_28na_28cl.top includes "#include ion.itp" but ion.itp only has 
  [moleculetype] and [atoms] sections - no [atomtypes] for NA and CL.
  
fix: |
  BUG 1 FIX (gromacs_writer.py:write_interface_top_file, lines 818-916): 
  - Changed [molecules] section to write THREE separate entries in order: 
    SOL (ice_nmolecules), guest (guest_nmolecules), SOL (water_nmolecules)
  - This matches the .gro file order: ice SOL -> guest -> water SOL
  - Before fix: f.write(f"SOL          {iface.ice_nmolecules + iface.water_nmolecules}\n")
  - After fix: Two separate SOL entries with ice and water counts
  
  BUG 2 FIX (gromacs_writer.py:write_ion_top_file, lines 1343-1461):
  - Added [atomtypes] section BEFORE #include directives (required by GROMACS)
  - Added Madrid2019 ion parameters for NA and CL (when present)
  - Added GAFF2 atom types for guests (when present, same as write_multi_molecule_top_file)
  - Structure mirrors write_multi_molecule_top_file (lines 1062-1104)
  
verification: |
  Both fixes verified with unit tests:
  
  Test 1 (Bug 1):
  - Created InterfaceStructure with 5 ice + 2 CH4 + 5 water
  - Generated .top file with write_interface_top_file
  - Verified [molecules] has 3 entries: "SOL 5", "CH4 2", "SOL 5"
  - Result: PASS
  
  Test 2 (Bug 2):
  - Created IonStructure with 1 SOL + 1 NA + 1 CL
  - Generated .top file with write_ion_top_file  
  - Verified [atomtypes] section present with NA and CL definitions
  - Verified Madrid2019 parameters: NA sigma=0.221737nm, CL sigma=0.469906nm
  - Result: PASS
  
  Code syntax: PASSED (python3 -m py_compile)
  Module import: PASSED
  
files_changed: 
  - /share/home/nglokwan/quickice/quickice/output/gromacs_writer.py
