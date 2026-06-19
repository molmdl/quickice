---
status: resolved
trigger: "missing-_H-in-hydrate-gro-export"
created: 2026-06-19T00:00:00Z
updated: 2026-06-19T00:15:00Z
---

## Current Focus

hypothesis: CONFIRMED and FIXED
test: Added registry parameter to write_multi_molecule_gro_file(), passed from hydrate_export.py
expecting: .gro file outputs CH4_H/THF_H residue names matching .top [molecules] section
next_action: Final verification complete — archive session

## Symptoms

expected: In the .gro file, hydrate guest molecules should have residue names with _H suffix (e.g., CH4_H, THF_H) to match hydrate-specific ITP moleculetype names and .top [molecules] section
actual: The .gro file uses plain residue names (CH4, THF) without _H suffix, causing GROMACS topology mismatch
errors: GROMACS fails with "No such moleculetype" or atom count mismatch
reproduction: Export any hydrate structure using HydrateGROMACSExporter; check .gro file guest residue names
started: Present since hydrate export was implemented

## Eliminated

## Evidence

- timestamp: 2026-06-19T00:01
  checked: gromacs_writer.py lines 1160-1164
  found: write_multi_molecule_gro_file() calls get_guest_residue_name(mol.mol_type) for guest types, which returns "CH4" / "THF" WITHOUT _H suffix
  implication: .gro file will always have plain residue names for guests regardless of context

- timestamp: 2026-06-19T00:01
  checked: gromacs_writer.py lines 1255-1274
  found: write_multi_molecule_top_file() checks MoleculetypeRegistry first (hydrate_key = "hydrate_CH4"), then falls back to get_guest_residue_name(). With registry, it correctly outputs "CH4_H"
  implication: The .top file works correctly because it has registry context; the .gro file doesn't

- timestamp: 2026-06-19T00:02
  checked: hydrate_export.py lines 146-161
  found: MoleculetypeRegistry is created and register_hydrate_guest("CH4") is called, but registry is only passed to write_multi_molecule_top_file(), NOT to write_multi_molecule_gro_file()
  implication: The hydrate exporter already has the registry — it just needs to pass it through

- timestamp: 2026-06-19T00:02
  checked: gromacs_writer.py lines 826-828
  found: write_interface_gro_file() correctly uses get_hydrate_guest_residue_name() because it has direct structure context
  implication: Confirms that the _H suffix is the expected behavior for hydrate guests

- timestamp: 2026-06-19T00:03
  checked: All call sites of write_multi_molecule_gro_file()
  found: Only hydrate_export.py calls it in production code; 3 test calls exist but don't pass registry
  implication: Adding optional registry parameter won't break any existing callers

## Resolution

root_cause: write_multi_molecule_gro_file() always used get_guest_residue_name() for guest molecules, returning plain names like "CH4" without context about whether they were hydrate cage guests. The MoleculetypeRegistry (which maps hydrate_CH4 → CH4_H) was only passed to write_multi_molecule_top_file(), not to the .gro writer. This caused a mismatch: .top referenced "CH4_H" in [molecules] but .gro had "CH4" as residue name.
fix: Added optional `registry` parameter to write_multi_molecule_gro_file() and implemented the same registry-based residue name lookup pattern used in write_multi_molecule_top_file(). When registry is provided and contains a hydrate_ or liquid_ registration for a guest molecule, the registry name is used (e.g. CH4_H). Falls back to get_guest_residue_name() when no registry or no matching registration. Updated hydrate_export.py to pass the already-created registry to write_multi_molecule_gro_file().
verification: 1) New test test_gro_file_guest_residue_name_has_h_suffix verifies CH4_H appears in .gro output. 2) All 74 tests in test_output/ and test_gromacs_molecule_ordering.py pass. 3) Direct output comparison confirms: without registry → CH4, with registry → CH4_H. 4) .gro and .top residue names now match (both CH4_H).
files_changed: [quickice/output/gromacs_writer.py, quickice/gui/hydrate_export.py, tests/test_output/test_gromacs_export_hydrate.py]
