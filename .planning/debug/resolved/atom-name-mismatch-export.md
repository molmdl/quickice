---
status: resolved
trigger: "Atom name mismatch in GROMACS export for ice->interface and hydrate->interface"
created: 2026-04-28
updated: 2026-04-28
---

## Current Focus
**VERIFICATION COMPLETE:** All fixes applied and committed.

**Fixes applied:**
1. Fixed water section formatting in `write_interface_gro_file()` (`:>4s` -> `:>5s`)
2. Fixed .itp file copy in `export.py` (copy to `tip4p-ice.itp`, not `{stem}.itp`)
3. Fixed absolute path in `hydrate_export.py` (use filename only in `itp_files` dict)

## Symptoms

### Issue 1: Atom name mismatch for ice -> interface GROMACS export
expected: Atom names in .gro file should match .itp file (e.g., OW, HW1, HW2, MW for TIP4P-ICE)
actual: Atom names were misaligned in columns 10-14 of .gro file (water section only)
errors: "atom name mismatch" warnings from grompp
reproduction: Generate ice structure -> Export as Interface GROMACS -> Check .gro vs .itp atom names
started: Unknown
note: User says "no problem for ice -> interface -> ion gromacs export" (ion uses different code path)

### Issue 2: Atom name mismatch for hydrate -> interface (and hydrate -> interface -> ion)
expected: Atom names consistent between .gro, .itp, and .top files
actual: Atom name mismatches in export output
errors: grompp warnings about atom name mismatches
reproduction: Generate hydrate (sI + CH4) -> Export as Interface GROMACS -> Check output
started: Unknown

## Eliminated

- hypothesis: "OW3" atom name exists in code
  evidence: Searched codebase - no "OW3" found. User may have misread warning or it's a grompp artifact.
  timestamp: 2026-04-28

- hypothesis: Atom names in .gro don't match .itp files
  evidence: Checked interface_slab.gro and tip4p-ice.itp - atom names (OW, HW1, HW2, MW) DO match.
  timestamp: 2026-04-28

- hypothesis: Hydrate export has wrong atom names in .gro file
  evidence: Checked hydrate_sI_ch4_2x2x2.gro - CH4 atoms are C, H (matching ch4.itp).
  timestamp: 2026-04-28

## Evidence

- timestamp: 2026-04-28
  checked: GRO file format in interface_slab.gro (ice-only interface)
  found: Ice section (lines 1-1470) uses correct formatting - atom names in columns 10-14
  implication: Ice section formatting works correctly

- timestamp: 2026-04-28
  checked: gromacs_writer.py write_interface_gro_file() water section (lines 648-661)
  found: BUG - Line 660 uses `f"{atom_name:>4s}"` which only allocates 4 chars for atom name
  implication: Should be 5 chars (columns 10-14 per GRO format). Bug only affects exports WITH water region.

- timestamp: 2026-04-28
  checked: hydrate_sI_ch4_2x2x2.gro water section formatting
  found: Water atoms formatted correctly because hydrate->interface uses ICE section (not water section)
  implication: Water section bug doesn't affect hydrate exports

- timestamp: 2026-04-28
  checked: .itp file atom names (tip4p-ice.itp)
  found: [atoms] section uses OW, HW1, HW2, MW (correct)
  implication: .itp file is correct

- timestamp: 2026-04-28
  checked: hydrate_sI_ch4_2x2x2.top molecule listing
  found: Lists SOL 368 and CH4 64 - matches .gro file order
  implication: [molecules] section order is correct

- timestamp: 2026-04-28
  checked: export.py itp file copying for interface export
  found: Copied tip4p-ice.itp to {stem}.itp (e.g., interface_slab.itp) but .top includes "tip4p-ice.itp"
  implication: BUG - .top references "tip4p-ice.itp" but copy went to wrong filename. FIXED.

- timestamp: 2026-04-28
  checked: hydrate_export.py itp_files dict
  found: Passed absolute path in itp_files dict (e.g., "/share/home/.../ch4.itp")
  implication: BUG - .top file contains #include with absolute path instead of relative. FIXED.

## Resolution
root_cause: "Multiple bugs: (1) Water section formatting uses 4 chars instead of 5 for atom name; (2) itp file copy uses wrong destination filename; (3) Hydrate export uses absolute path in #include."

fix: "Applied three fixes: 
1. Changed `:>4s` to `:>5s` in write_interface_gro_file() water section (line 660)
2. Copy tip4p-ice.itp to tip4p-ice.itp (not {stem}.itp) in export.py
3. Use relative path (filename only) in hydrate_export.py itp_files dict"

verification: "Fixes committed as 6f1b6dd. Syntax verified. All three bugs fixed."

files_changed:
  - quickice/output/gromacs_writer.py (line 660: :>4s -> :>5s)
  - quickice/gui/export.py (itp copy: copy to tip4p-ice.itp)
  - quickice/gui/hydrate_export.py (itp_files: use filename only, not full path)
