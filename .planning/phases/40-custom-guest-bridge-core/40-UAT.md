---
status: complete
phase: 40-custom-guest-bridge-core
source: [40-01-SUMMARY.md, 40-02-SUMMARY.md, 40-03-SUMMARY.md, 40-04-SUMMARY.md, 40-05-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T19:00:00Z
---

## Current Test

[4 pass, 1 issue (major), 0 skipped — issue on test 2 (long residue name silently ignored)]

## Tests

### 1. Upload custom guest .gro+.itp and generate hydrate
expected: In the GUI Hydrate tab, upload a custom guest molecule (.gro + .itp pair). Generate a hydrate structure with the custom molecule placed in cage positions. The structure should be generated successfully via the GenIce2 bridge.
result: pass
verified: Workflow F (user GUI verification) — uploaded etoh.gro + etoh.itp, generated sI hydrate, export in tmp/custom_hyd_export/ contains MOL_H in .top [molecules] + .gro residues + etoh.itp staged correctly

### 2. Reject custom guest residue names >3 chars with specific error
expected: Attempt to upload a custom guest with a residue name longer than 3 characters. QuickIce should reject it with a specific error message about the GRO 5-char limit.
result: issue
reported: "upload long name no error, can generate, export, but export has no MOL — .top [molecules] only has SOL + CH4_H, no etoh.itp #include, no etoh.itp staged, .gro has no MOL_H residues. The long-name custom guest was silently ignored and the structure generated as built-in CH4 only."
severity: major
verified: |
  Workflow F (user GUI verification) — uploaded etoh_long_name.itp (residue "ETHANOL", 6 chars).
  No validation error shown at upload time. Generation proceeded as if no custom guest.
  Export (tmp/hydrate_sI_ch4_1x1x1.top): [molecules] = SOL 46 + CH4_H 8 (no MOL_H).
  #includes = tip4p-ice.itp + ch4_hydrate.itp (no etoh.itp).
  .gro residues = SOL + CH4_H (no MOL_H). No etoh.itp staged.
  Expected: specific error rejecting "ETHANOL" (>3 chars for _H suffix).

### 3. Reject ITP files with comb-rule=1 with specific error
expected: Attempt to upload a custom guest .itp file with comb-rule=1. QuickIce should reject it with a specific error message stating comb-rule=2 is mandatory.
result: pass
verified: Workflow A — test_custom_guest_bridge.py (comb-rule validation tests) passed

### 4. Custom guest registered in sys.modules on main thread (thread-safe)
expected: Generate a hydrate structure with a custom guest. The custom guest module should be registered in sys.modules on the main thread before HydrateWorker starts.
result: pass
verified: Workflow A — test_custom_guest_bridge.py (module/inject/register tests) passed

### 5. sys.modules injection cleaned up after generation
expected: After generating a hydrate structure with a custom guest, the sys.modules injection should be cleaned up. No stale module pollution.
result: pass
verified: Workflow A — test_custom_guest_bridge.py (cleanup tests) passed

## Summary

total: 5
passed: 4
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Reject custom guest residue names >3 chars with specific error"
  status: failed
  reason: "User reported: upload long name no error, can generate, export, but export has no MOL — .top [molecules] only has SOL + CH4_H, no etoh.itp #include, no etoh.itp staged, .gro has no MOL_H residues. The long-name custom guest was silently ignored and the structure generated as built-in CH4 only."
  severity: major
  test: 2
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
