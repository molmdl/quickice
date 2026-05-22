---
status: resolved
trigger: "SoluteGROMACSExporter.export_solute_gromacs() in quickice/gui/export.py will crash at runtime due to 3 bugs: (1) missing import numpy as np causing NameError, (2) write_gro_file() called with wrong number of arguments causing TypeError, (3) write_top_file() called with wrong signature causing TypeError. Additionally, even if these crashes were fixed, the underlying writers used are wrong — they produce ice-only .top files without solute moleculetype entries, and don't compute MW for ice atoms."
created: 2026-05-22T14:00:00Z
updated: 2026-05-22T14:50:00Z
---

## Current Focus

hypothesis: CONFIRMED AND FIXED
test: End-to-end test with CH4 and THF solutes, with and without guest molecules
expecting: Correct .gro and .top output with proper molecule types and atom counts
next_action: Archive debug session

## Symptoms

expected: Solute tab export should produce a complete GROMACS system (.gro with ice+water+solute atoms including MW, .top with SOL + CH4_L/THF_L moleculetype entries, bundled solute .itp + tip4p-ice.itp)
actual: Code will crash with NameError/TypeError. Even if it didn't crash, the simple writers it calls produce incomplete files.
errors: (1) NameError: name 'np' is not defined at line 75, (2) TypeError: write_gro_file() takes 2 positional arguments but 4 were given at line 83, (3) TypeError: write_top_file() takes 2 positional arguments but 5+ were given at line 123
reproduction: Generate an interface structure, go to Solute tab (Tab 4), add solutes, click Export. Application will crash.
started: Introduced during Phase 33 (Solute Insertion) — likely never tested end-to-end

## Eliminated

## Evidence

- timestamp: 2026-05-22T14:00
  checked: export.py lines 1-21 for numpy import
  found: No `import numpy as np` anywhere in the file. Line 75 uses `np.vstack()` — NameError confirmed.
  implication: Bug 1 confirmed: missing numpy import

- timestamp: 2026-05-22T14:01
  checked: gromacs_writer.py line 426 for write_gro_file signature
  found: `def write_gro_file(candidate: Candidate, filepath: str)` — takes exactly 2 args (Candidate, filepath)
  implication: Bug 2 confirmed: export.py line 83 passes 4 args (positions, atom_names, cell, path) — TypeError

- timestamp: 2026-05-22T14:02
  checked: gromacs_writer.py line 512 for write_top_file signature
  found: `def write_top_file(candidate: Candidate, filepath: str)` — takes exactly 2 args (Candidate, filepath)
  implication: Bug 3 confirmed: export.py line 123 passes 5+ args — TypeError

- timestamp: 2026-05-22T14:03
  checked: write_gro_file (line 426) and write_top_file (line 512) actual behavior
  found: Both are ice-only writers. write_gro_file only writes SOL molecules with 3→4 atom conversion. write_top_file only creates SOL moleculetype entry. Neither handles solutes, guests, or custom molecules.
  implication: Even if crash bugs were fixed by changing arg count, output would be wrong — no solute moleculetype entries, no MW for ice in mixed systems

- timestamp: 2026-05-22T14:04
  checked: Working exporter patterns — IonGROMACSExporter (line 231) and InterfaceGROMACSExporter (line 786)
  found: Both use dedicated writer functions that take the full structure object: write_ion_gro_file(ion_structure, filepath), write_ion_top_file(ion_structure, filepath), write_interface_gro_file(iface, filepath), write_interface_top_file(iface, filepath)
  implication: SoluteGROMACSExporter needs analogous write_solute_gro_file() and write_solute_top_file() functions

- timestamp: 2026-05-22T14:05
  checked: SoluteStructure dataclass (types.py line 424)
  found: Has interface_structure (InterfaceStructure with molecule_index), positions/atom_names (solute-only), molecule_indices, registry, plus propagated custom molecule attributes
  implication: New writers can follow the ion writer pattern, simplified for the solute case (no ions)

- timestamp: 2026-05-22T14:06
  checked: IonGROMACSExporter solute handling (gromacs_writer.py lines 1341-1590)
  found: Ion writer handles solutes by: building ordered_mols list, extracting from solute_structure.solute_positions/atom_names, using registry for residue name, writing with proper GRO formatting
  implication: Solute writer should follow same pattern but without ion-related code

## Resolution

root_cause: SoluteGROMACSExporter was never properly integrated with the multi-molecule writer infrastructure. It was written with wrong function calls to ice-only writers (write_gro_file/write_top_file which take Candidate, not multi-molecule data), missing numpy import, and the molecule_index construction uses dicts instead of MoleculeIndex objects. The underlying ice-only writers can't produce correct output for mixed systems anyway.
fix: Created write_solute_gro_file() and write_solute_top_file() in gromacs_writer.py following the ion writer pattern (ordered_mols, proper 3→4 ice atom expansion, MW computation, guest detection/reordering, custom molecule propagation, registry-based residue names). Rewrote SoluteGROMACSExporter.export_solute_gromacs() to use these new writers. Also added solute .itp atomtypes commenting and custom .itp copying.
verification: End-to-end test with CH4 solutes (2 molecules) — 30 atoms, 20 SOL, 10 CH4_L, MW atoms present, correct .top sections. THF solutes with THF hydrate guests — 47 atoms, 8 SOL, 13 THF_H, 26 THF_L, both hydrate and liquid ITP includes. Full test suite: 413 passed, 2 skipped, 3 pre-existing failures unrelated to this fix.
files_changed: [quickice/output/gromacs_writer.py, quickice/gui/export.py]
