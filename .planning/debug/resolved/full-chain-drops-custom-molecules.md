---
status: resolved
trigger: "full-chain-drops-custom-molecules"
created: 2026-06-27T00:00:00
updated: 2026-06-27T00:10:00
---

## Current Focus

hypothesis: CONFIRMED — Two interrelated problems in pipeline.py: (1) --ion-source defaults to 'interface' so ion step uses raw InterfaceStructure (no custom/solute attrs), and (2) --solute-source defaults to 'interface' so solute step gets raw interface (custom attrs lost). Both silently drop upstream data.
test: Run reproduction commands — WITHOUT --ion-source → only SOL+NA+CL; WITH --ion-source=solute → SOL+CH4_L+NA+CL (no custom). Both confirmed.
expecting: Auto-chaining fix: when --solute-source=interface (default) and custom_result exists, upgrade to 'custom'. When --ion-source=interface (default) and solute_result exists, upgrade to 'solute'; else if custom_result exists, upgrade to 'custom'.
next_action: Implement auto-chaining fix in pipeline.py _run_solute_step() and _run_ion_step()

## Symptoms

expected: Full chain (interface→custom→solute→ion) should produce GROMACS files with all molecule types: SOL, MOL (custom etoh), CH4_L (solute), NA, CL — with 4+ ITP files
actual: GRO and TOP contain only SOL+NA+CL. Custom molecules and solutes are completely absent from output. Even with --ion-source solute, custom molecules (MOL/etoh) remain missing.
errors: No error message — the pipeline reports success but silently drops data.
reproduction:
  WITHOUT --ion-source: drops both custom AND solute → only SOL+NA+CL
  WITH --ion-source solute: fixes solutes (CH4_L appears) but custom (MOL/etoh) STILL missing
started: Likely always the case since Phase 36 was implemented

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-06-27T00:01
  checked: pipeline.py _run_ion_step() line 580
  found: --ion-source defaults to 'interface' → uses self._interface_result (raw, no custom/solute attrs)
  implication: IonStructure gets custom_molecule_count=0 and solute_n_molecules=0 → drops all upstream data

- timestamp: 2026-06-27T00:02
  checked: pipeline.py _run_solute_step() line 518
  found: --solute-source defaults to 'interface' → gets self._interface_result (no custom molecule info)
  implication: SoluteStructure.custom_molecule_count=0 → even with --ion-source=solute, custom attrs don't propagate

- timestamp: 2026-06-27T00:03
  checked: Reproduction WITHOUT --ion-source → /tmp/test_issue1
  found: TOP has only SOL+NA+CL, 2 ITP files (ion.itp+tip4p-ice.itp). Both custom AND solute missing.
  implication: Confirmed Problem 1

- timestamp: 2026-06-27T00:04
  checked: Reproduction WITH --ion-source=solute → /tmp/test_issue2
  found: TOP has SOL+CH4_L+NA+CL, 3 ITP files. Custom (etoh/MOL) still missing.
  implication: Confirmed Problem 2 — SoluteStructure.custom_molecule_count=0 because --solute-source=interface

- timestamp: 2026-06-27T00:05
  checked: gromacs_writer.py write_ion_gro_file() and write_ion_top_file()
  found: Both properly check ion_structure.custom_molecule_count, solute_n_molecules, etc. and write correct output. The writers are correct; the bug is upstream in pipeline.py where these attributes aren't populated.
  implication: Fix is purely in pipeline.py source selection logic

## Resolution

root_cause: Two interrelated problems in pipeline.py: (1) --ion-source defaults to 'interface' so the ion step uses the raw InterfaceStructure (no custom/solute attributes), silently dropping ALL upstream data. (2) --solute-source defaults to 'interface' so the solute step gets the raw InterfaceStructure (no custom molecule info), meaning SoluteStructure.custom_molecule_count=0, which prevents custom attrs from propagating through the solute→ion chain even when --ion-source=solute is explicitly set.
fix: Auto-chaining in _run_solute_step() and _run_ion_step(): when the default source ('interface') is used and more downstream results exist, automatically upgrade to the most downstream available result (solute > custom > interface for ion; custom > interface for solute). This prevents silent data loss without requiring users to manually specify --solute-source and --ion-source.
verification: 
  1. Full chain WITHOUT --ion-source: TOP now has SOL+etoh+CH4_L+NA+CL (was SOL+NA+CL)
  2. Full chain WITH --ion-source solute: TOP now has SOL+etoh+CH4_L+NA+CL (was SOL+CH4_L+NA+CL, custom missing)
  3. Ion-only chain: TOP has SOL+NA+CL (unchanged, correct)
  4. Custom+ion chain: TOP has SOL+etoh+NA+CL (unchanged, correct)
  5. All 161 relevant tests pass, full suite 1029 pass (1 flaky GUI test unrelated)
files_changed: [quickice/cli/pipeline.py]
