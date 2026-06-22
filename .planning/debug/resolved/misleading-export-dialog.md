---
status: verifying
trigger: "Info dialog per export for the chain CH4 hydrate → interface (slab) → solute (CH4) counts only the solute CH4 molecules, which is misleading."
created: 2026-06-22T00:00:00Z
updated: 2026-06-22T00:00:02Z
---

## Current Focus

hypothesis: CONFIRMED and FIXED — All four export dialogs updated to show complete molecule breakdowns
test: Run all relevant test suites (output, scancode, solute export, gmx validation)
expecting: All tests pass, no regressions
next_action: Verify tests pass, then commit

## Symptoms

expected: The info dialog should clearly distinguish between hydrate CH4 and solute CH4, or show total CH4 count, so the user isn't misled into thinking there are only 36 CH4 molecules total when there are actually more (hydrate CH4 + solute CH4).
actual: Dialog shows "CH4: 36 molecules" which only reflects solute CH4, omitting hydrate guest CH4 entirely.
errors: No error — the export files are correct. Only the dialog message is misleading.
reproduction: 1) Create a CH4 hydrate structure, 2) Add interface (slab), 3) Add solute CH4, 4) Export — the info dialog will show only solute CH4 count
started: Likely always been this way — not a regression

## Eliminated

## Evidence

- timestamp: 2026-06-22T00:00:01
  checked: main_window.py lines 1747-1763 (_on_export_solute_gromacs)
  found: Dialog shows Ice, Water, and {solute_type}: {n_molecules}. No guest or custom molecule info shown.
  implication: Primary bug confirmed — solute dialog omits guest molecules

- timestamp: 2026-06-22T00:00:02
  checked: main_window.py lines 1716-1727 (_on_export_ion_gromacs)
  found: Dialog shows Water, Na+, Cl- only. IonStructure has guest_nmolecules, solute_n_molecules, custom_molecule_count but none are shown.
  implication: Ion export dialog also omits guest/solute/custom molecules

- timestamp: 2026-06-22T00:00:03
  checked: main_window.py lines 1782-1791 (_on_export_custom_molecule_gromacs)
  found: Dialog shows Molecule type, Molecules, ITP bundled only. No ice/water/guest/solute info.
  implication: Custom molecule export dialog also omits ice/water/guest/solute molecules

- timestamp: 2026-06-22T00:00:04
  checked: main_window.py lines 1645-1659 (_on_export_interface_gromacs)
  found: Dialog shows Ice, Water, Total. No guest info if hydrate guests are present in interface.
  implication: Interface dialog omits guest molecules if present

- timestamp: 2026-06-22T00:00:05
  checked: gromacs_writer.py write_solute_gro_file (lines 2325+)
  found: .gro writer outputs molecules in order: SOL (ice+water), guest, custom, solute
  implication: The .gro file contains ALL molecule types but the dialog doesn't report all of them

- timestamp: 2026-06-22T00:00:06
  checked: SoluteStructure dataclass and interface_structure attribute
  found: SoluteStructure has interface_structure (InterfaceStructure) which has guest_nmolecules and guest_atom_count. SoluteStructure also has custom_molecule_count. No guest_type field directly, but _detect_guest_type_from_structure() can detect it.
  implication: All needed data IS available in the structure objects; the dialog just doesn't use it

- timestamp: 2026-06-22T00:00:07
  checked: CLI pipeline (pipeline.py) export handling
  found: CLI just does report_progress with filenames, no molecule counts
  implication: Bug is GUI-only, no CLI changes needed

- timestamp: 2026-06-22T00:00:08
  checked: Test suite after fix
  found: All 118 relevant tests pass (output, scancode_bugs_gromacs, solute_export, gmx_validation). No test directly verifies dialog message content.
  implication: Fix is safe; no regressions introduced

## Resolution

root_cause: The export dialog messages in main_window.py only show a subset of the molecule types present in the exported .gro files. Specifically, the solute export dialog shows only ice/water/solute counts and omits guest and custom molecule counts, causing "CH4: 36" to appear as if it's the total CH4 count when hydrate guest CH4 also exists. The ion, custom molecule, and interface dialogs have similar omissions.
fix: Updated all four affected export dialogs in main_window.py to show complete molecule breakdowns matching what the .gro files actually contain. Labels now clearly distinguish between "Guest CH4" (hydrate cages) and "Solute CH4" (liquid-phase solutes). Uses _detect_guest_type_from_structure() for guest type detection. Custom molecules, ice counts, and water counts are now shown where applicable.
verification: All 118 relevant tests pass. No tests directly verify dialog message content, but the fix only changes message display strings, not export logic.
files_changed: [quickice/gui/main_window.py]
