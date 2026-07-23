---
status: testing
phase: 40-custom-guest-bridge-core
source: [40-01-SUMMARY.md, 40-02-SUMMARY.md, 40-03-SUMMARY.md, 40-04-SUMMARY.md, 40-05-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T12:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: Upload custom guest .gro+.itp and generate hydrate
expected: |
  In the GUI Hydrate tab, upload a custom guest molecule (.gro + .itp pair, e.g. ethanol).
  Generate a hydrate structure (e.g. sI lattice) with the custom molecule placed in the
  specified cage positions. The structure should be generated successfully via the GenIce2
  bridge with the custom guest module registered in sys.modules.
awaiting: user response

## Tests

### 1. Upload custom guest .gro+.itp and generate hydrate
expected: In the GUI Hydrate tab, upload a custom guest molecule (.gro + .itp pair, e.g. ethanol). Generate a hydrate structure (e.g. sI lattice) with the custom molecule placed in the specified cage positions. The structure should be generated successfully via the GenIce2 bridge with the custom guest module registered in sys.modules.
result: [pending]

### 2. Reject custom guest residue names >3 chars with specific error
expected: Attempt to upload a custom guest with a residue name longer than 3 characters (e.g. "ETHANOL"). QuickIce should reject it with a specific error message explaining the GRO 5-char limit (3 chars + _H suffix = 5 max). The validation should happen before generation starts, not produce a corrupted .gro file.
result: [pending]

### 3. Reject ITP files with comb-rule=1 with specific error
expected: Attempt to upload a custom guest .itp file with comb-rule=1 (not Lorentz-Berthelot). QuickIce should reject it with a specific error message stating that comb-rule=2 (Lorentz-Berthelot) is mandatory. ITP files with comb-rule=2 should be accepted. ITP files with no [defaults] section should also be accepted (main .top supplies comb-rule=2).
result: [pending]

### 4. Custom guest registered in sys.modules on main thread (thread-safe)
expected: Generate a hydrate structure with a custom guest. The custom guest module should be registered in sys.modules on the main thread before HydrateWorker starts (thread-safe). This is an internal check but should manifest as: no race condition errors, no "module not found" errors during generation.
result: [pending]

### 5. sys.modules injection cleaned up after generation
expected: After generating a hydrate structure with a custom guest, the sys.modules injection should be cleaned up. Verify by checking that the custom guest module is no longer present in sys.modules after generation completes (no stale module pollution). Generate a second structure with a different guest to confirm no interference from the previous injection.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0

## Gaps

[none yet]
