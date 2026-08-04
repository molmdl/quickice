---
status: resolved
trigger: "Investigate UAT Workflow F issues: Issue 1 (long residue name silently ignored) and Issue 2 (duplicate #include etoh.itp -> grompp moleculetype redefined). Confirm shared root cause or independent bugs."
created: 2026-08-04T00:00:00Z
updated: 2026-08-04T01:00:00Z
---

## Current Focus

hypothesis: CONFIRMED — Two INDEPENDENT root causes (NOT one shared). Issue 1 = validate_custom_guest_files doesn't check ITP [atoms] resname vs GRO resname (validation gap). Issue 2 = GUI exporters stage custom-molecule ITP to colliding basename + writers emit duplicate #include (staging + #include collision).
test: Ran validate_custom_guest_files(etoh.gro, etoh_long_name.itp) -> is_valid=True (confirmed Issue 1). Read all 3 top-file writers -> confirmed duplicate #include pattern at solute_writer.py:731+739, custom_writer.py:537+547, ion_writer.py:757+777 (confirmed Issue 2).
expecting: Fix proposal for both issues, checkpoint:decision for rename strategy.
next_action: Raise checkpoint:decision for fix approach (ITP resname validation + rename strategy).

## Symptoms

expected:
- Issue 1: Upload etoh_long_name.itp (residue name "ETHANOL", 6 chars) as custom guest in Hydrate tab -> QuickIce rejects with specific error about residue name >3 chars / GRO 5-char limit.
- Issue 2: When custom molecule ITP basename collides with cage-guest ITP basename, GUI exporter should rename custom molecule ITP copy (e.g. cmet.itp) and update #include in .top, mirroring CLI e2e pattern.

actual:
- Issue 1: No validation error shown. Generation proceeded. Export produced structure as if NO custom guest uploaded -> fell back to built-in CH4 only. (SILENT failure.)
- Issue 2: Both files staged to SAME filename in output dir (second overwrites first). .top has TWO #include "etoh.itp" lines. grompp reads file twice, sees moleculetype etoh defined twice -> fails.

errors:
- Issue 1: None (silent failure - this IS the bug).
- Issue 2: gmx grompp returns "ERROR: moleculetype etoh is redefined" (rc != 0). Affects Custom/Solute/Ion tab exports; Interface tab export PASSES.

reproduction:
- Issue 1: Upload quickice/data/custom/test_invalid/etoh_long_name.itp (ITP [atoms] resname "ETHANOL") + etoh.gro (GRO resname "MOL") as custom guest; validation passes silently.
- Issue 2: Generate custom guest hydrate (ethanol in cages) -> Interface -> Custom (also ethanol) -> Solute -> Ion. Export from each; gmx grompp. Interface passes; Custom/Solute/Ion fail.

started: Discovered during UAT Workflow F on 2026-08-04.

## Eliminated

- hypothesis: "GUI upload path may not call validate_custom_guest_files (or may swallow the error)"
  evidence: hydrate_panel.py::_try_validate_custom_guest (line 365) DOES call validate_custom_guest_files and DOES handle invalid results (line 369-377 shows red error, clears _custom_guest). The GUI validation IS wired correctly. The issue is the validation FUNCTION doesn't check the ITP [atoms] resname.
  timestamp: 2026-08-04T00:10Z

- hypothesis: "Check ITP [ moleculetype ] name for <=3 chars"
  evidence: The VALID etoh.itp has [ moleculetype ] name "etoh" (4 chars > 3). Checking the moleculetype name for <=3 chars would REJECT the valid case. The moleculetype name is overwritten by transform_guest_itp to "{GRO_resname}_H" at export, so its length doesn't matter.
  timestamp: 2026-08-04T00:20Z

- hypothesis: "Check ITP [ moleculetype ] name vs GRO resname mismatch"
  evidence: The VALID etoh.itp has moleculetype "etoh" but GRO resname "MOL" — they mismatch. A mismatch check on the moleculetype name would generate a false positive for the valid case. The moleculetype name is intentionally different from the GRO resname (it's overwritten at export).
  timestamp: 2026-08-04T00:22Z

- hypothesis: "Use shallow copy of structure with renamed itp_path to avoid writer signature changes"
  evidence: Writers read itp_path for parse_itp_file (molecule_name) AND parse_itp_atomtypes (atomtypes for main .top). The staged ITP has [atomtypes] commented out, so parse_itp_atomtypes would return empty -> atomtypes missing from .top -> grompp error. The writer needs the ORIGINAL itp_path for parsing but the RENAMED name for #include. These are separate needs requiring a new kwarg.
  timestamp: 2026-08-04T00:25Z

## Evidence

### Issue 1: Validation gap (ITP [atoms] resname not checked)

- timestamp: 2026-08-04T00:01Z
  checked: custom_guest_bridge.py::validate_custom_guest_files (lines 177-313)
  found: Step 4 (line 254) checks ONLY extract_residue_name_from_gro(gro_path) for <=3 chars. The ITP residue name is NOT checked. itp_info (from parse_itp_file, line 235) has molecule_name but NOT [atoms] resname.
  implication: Validation gap — ITP [atoms] resname not validated against GRO resname.

- timestamp: 2026-08-04T00:06Z
  checked: Ran validate_custom_guest_files('etoh.gro', 'etoh_long_name.itp', 'custom_gui')
  found: is_valid=True, errors=[], residue_name='MOL' (from GRO). The ITP's "ETHANOL" is NOT checked. CONFIRMED: validation passes silently.
  implication: This is the root cause of Issue 1 — the invalid ITP passes validation.

- timestamp: 2026-08-04T00:15Z
  checked: molecule_validator.py::validate_custom_molecule (lines 127-255) — the CUSTOM MOLECULE validator
  found: DOES check ITP residue name (line 177: itp_residue_name = itp_info.molecule_name) and GRO/ITP mismatch (line 181-205). Returns residue_name_mismatch=True with a warning for the etoh_long_name case.
  implication: The custom molecule validator is MORE thorough than the hydrate guest validator. Inconsistency confirmed.

- timestamp: 2026-08-04T00:28Z
  checked: ITP [atoms] resname for valid vs invalid files
  found: VALID etoh.itp [atoms] resname = "MOL" (matches GRO "MOL"). INVALID etoh_long_name.itp [atoms] resname = "ETHANOL" (mismatches GRO "MOL"). ITPMoleculeInfo does NOT have atom_resname field.
  implication: The correct check is ITP [atoms] resname vs GRO resname. Valid case matches (MOL==MOL), invalid case mismatches (ETHANOL!=MOL). Need to add atom_resname to ITPMoleculeInfo.

- timestamp: 2026-08-04T00:29Z
  checked: transform_guest_itp behavior
  found: transform_guest_itp(content, 'MOL', '_H') overwrites BOTH [moleculetype] name AND [atoms] resname to "MOL_H". Verified: both valid etoh.itp and invalid etoh_long_name.itp produce identical transformed output (moleculetype MOL_H, atoms resname MOL_H).
  implication: ITP [atoms] resname is overwritten at export, so it doesn't affect the output. But a mismatch between ITP [atoms] resname and GRO resname is a user-error signal that should be caught at validation time.

### Issue 2: Staging collision + duplicate #include

- timestamp: 2026-08-04T00:03Z
  checked: guest_info.py::_stage_hydrate_guest_itps (lines 331-333)
  found: Cage-guest ITP staged as dest_name = src_itp_path.name; dest_path = output_dir / dest_name. For custom cage guest etoh.itp, writes output_dir/etoh.itp (moleculetype MOL_H, transformed).

- timestamp: 2026-08-04T00:04Z
  checked: export.py — 3 exporters staging custom molecule ITP
  found: All 3 stage via custom_itp_dest = path.with_name(custom_itp_source.name) (line 249 Solute, line 386 Custom, line 574 Ion). If custom_itp_source.name == "etoh.itp", OVERWRITES the cage-guest etoh.itp with custom-molecule etoh.itp (moleculetype etoh). Last write wins.

- timestamp: 2026-08-04T00:08Z
  checked: solute_writer.py::write_solute_top_file #include generation
  found: Line 731: #include "{Path(ci["itp_path"]).name}" (cage guest etoh.itp, when custom_active). Line 739: #include "{custom_itp_name}" (custom molecule etoh.itp, when has_custom). BOTH write #include "etoh.itp" -> DUPLICATE.

- timestamp: 2026-08-04T00:09Z
  checked: custom_writer.py::write_custom_molecule_top_file #include generation
  found: Line 537: #include "{Path(ci["itp_path"]).name}" (cage guest etoh.itp). Line 547: #include "{custom_structure.itp_path.name}" (custom molecule etoh.itp). DUPLICATE.

- timestamp: 2026-08-04T00:10Z
  checked: ion_writer.py::write_ion_top_file #include generation
  found: Line 757: #include "{Path(ci["itp_path"]).name}" (cage guest etoh.itp). Line 777: #include "{custom_itp_name}" (custom molecule etoh.itp). DUPLICATE.

- timestamp: 2026-08-04T00:12Z
  checked: CLI e2e test test_custom_guest_cli_custom_molecule_export_grompp (test_e2e_custom_guest_cli_grompp.py lines 329-429)
  found: The CLI test PRE-RENAMES the custom molecule files to cmet.gro/cmet.itp (lines 353-364, renaming moleculetype "etoh"->"MOL") BEFORE passing them to CustomMoleculeConfig. The CLI exporter (itp_helpers.py) uses the SAME output_dir/source.name staging pattern. The rename happens in the TEST FIXTURE, not the exporter.
  implication: The CLI avoids the collision by pre-renaming, not by auto-rename in the exporter. The GUI should auto-rename because GUI users can't be expected to pre-rename files.

- timestamp: 2026-08-04T00:14Z
  checked: InterfaceGROMACSExporter (export.py lines 1028-1138)
  found: Interface exporter calls _stage_hydrate_guest_itps but does NOT stage a custom molecule ITP (interface path has no custom molecules). Only one #include "etoh.itp" (cage guest). No collision possible.
  implication: Confirms why Interface tab export PASSES — no custom molecule ITP to collide with.

### Root cause determination: 1 shared or 2 independent?

- timestamp: 2026-08-04T00:30Z
  checked: Both issues' root causes
  found: Issue 1 root cause is in the VALIDATION layer (custom_guest_bridge.py: validate_custom_guest_files doesn't check ITP [atoms] resname). Issue 2 root cause is in the STAGING + WRITER layer (export.py: colliding basename staging + 3 writers: duplicate #include). Different layers, different mechanisms.
  implication: TWO INDEPENDENT bugs, NOT one shared root cause. The ISSUES-FOUND.md "1 root cause shared" claim is imprecise — they share a THEME (GUI custom guest path lacks safety nets) but have different code-level root causes.

## Resolution

root_cause:
  issue1: "validate_custom_guest_files (custom_guest_bridge.py:254) only checks GRO residue name for <=3 chars, NOT the ITP [atoms] resname. When etoh_long_name.itp (ITP [atoms] resname 'ETHANOL') is paired with etoh.gro (GRO resname 'MOL'), validation passes silently. The custom molecule validator (molecule_validator.py) DOES check ITP/GRO mismatch, but the hydrate guest validator does not — inconsistency."
  issue2: "GUI exporters (export.py:249/386/574) stage the custom-molecule ITP to output_dir/<basename> which collides with the cage-guest ITP staged by _stage_hydrate_guest_itps (guest_info.py:331) when both share basename 'etoh.itp'. The 3 top-file writers (solute_writer.py:731+739, custom_writer.py:537+547, ion_writer.py:757+777) each emit TWO #include 'etoh.itp' lines (one for cage guest, one for custom molecule). grompp reads the (overwritten) file twice -> moleculetype etoh redefined."
  shared: false  # TWO INDEPENDENT bugs, NOT one shared root cause

fix:
  issue1: "Add atom_resname field to ITPMoleculeInfo (itp_parser.py). Parse fields[3] in parse_itp_file. Add ITP [atoms] resname vs GRO resname mismatch check to validate_custom_guest_files (custom_guest_bridge.py). Valid etoh.itp passes (MOL==MOL), invalid etoh_long_name.itp fails (ETHANOL!=MOL). Minimal: 2 files, ~10 lines."
  issue2: "Add custom_molecule_itp_name=None kwarg to 3 top-file writers. In each writer, use custom_molecule_itp_name or Path(structure.itp_path).name for the #include. In each exporter, detect collision (custom_itp_name in _staged_guest_itps), rename to cm_{basename}, stage to renamed name, pass renamed name to writer. Moderate: 6 files, ~30 lines. Mirrors CLI cmet.itp pattern."

verification:
  issue1: "Confirmed: validate_custom_guest_files('etoh.gro', 'etoh_long_name.itp', 'custom_gui') now returns is_valid=False with specific error about ITP [atoms] resname mismatch. Valid etoh.itp still passes (is_valid=True). 150 targeted tests pass including test_validate_rejects_itp_resname_mismatch + test_validate_accepts_matching_itp_resname."
  issue2: "Confirmed: _resolve_custom_molecule_itp_name correctly detects collision and renames to etoh_L.itp. Writers honor custom_molecule_itp_name kwarg for #include. 150 targeted tests pass including helper tests + writer behavior tests. Existing e2e grompp tests (CLI path) still pass."
  regressions: "None — 150 tests pass across test_custom_guest_bridge, test_hydrate_panel, test_itp_transformation, test_e2e_custom_guest_cli_grompp, test_output/*, scancode/test_scancode_bugs_*."
files_changed:
  - "quickice/structure_generation/itp_parser.py (added atom_resname field to ITPMoleculeInfo + parsing)"
  - "quickice/structure_generation/custom_guest_bridge.py (added ITP [atoms] resname mismatch check)"
  - "quickice/output/solute_writer.py (added custom_molecule_itp_name kwarg to write_solute_top_file)"
  - "quickice/output/custom_writer.py (added custom_molecule_itp_name kwarg to write_custom_molecule_top_file)"
  - "quickice/output/ion_writer.py (added custom_molecule_itp_name kwarg to write_ion_top_file)"
  - "quickice/gui/export.py (added _resolve_custom_molecule_itp_name helper + updated 3 exporters for collision detection + rename)"
  - "tests/test_custom_guest_bridge.py (added Issue 1 regression tests)"
  - "tests/test_uat_f_custom_guest_fixes.py (new: Issue 2 helper + writer tests)"
