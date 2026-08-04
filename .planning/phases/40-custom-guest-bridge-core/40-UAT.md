---
status: complete
phase: 40-custom-guest-bridge-core
source: [40-01-SUMMARY.md, 40-02-SUMMARY.md, 40-03-SUMMARY.md, 40-04-SUMMARY.md, 40-05-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T19:00:00Z
---

## Current Test

[all script-runnable tests complete — 4 pass, 1 skipped (GUI) via Workflow A]

## Tests

### 1. Upload custom guest .gro+.itp and generate hydrate
expected: In the GUI Hydrate tab, upload a custom guest molecule (.gro + .itp pair). Generate a hydrate structure with the custom molecule placed in cage positions. The structure should be generated successfully via the GenIce2 bridge.
result: skipped
reason: Requires GUI + human verification (headless environment). Custom guest in hydrate is GUI-only for v4.7 (no CLI flag). Validation logic verified in Workflow A.

### 2. Reject custom guest residue names >3 chars with specific error
expected: Attempt to upload a custom guest with a residue name longer than 3 characters. QuickIce should reject it with a specific error message about the GRO 5-char limit.
result: pass
verified: Workflow A — test_custom_guest_bridge.py (name/residue validation tests) passed

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
issues: 0
pending: 0
skipped: 1

## Gaps

[none]
