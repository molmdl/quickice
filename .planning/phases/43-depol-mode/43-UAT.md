---
status: testing
phase: 43-depol-mode
source: [43-01-SUMMARY.md, 43-02-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T12:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: Select depol mode (strict/optimal) in Hydrate tab
expected: |
  Open the QuickIce GUI, go to the Hydrate tab. A depol mode dropdown (QComboBox) should be
  present with two options: "strict" and "optimal". The default selection should be "strict".
  Switching between modes should not crash and should update the configuration.
awaiting: user response

## Tests

### 1. Select depol mode (strict/optimal) in Hydrate tab
expected: Open the QuickIce GUI, go to the Hydrate tab. A depol mode dropdown (QComboBox) should be present with two options: "strict" and "optimal". The default selection should be "strict". Switching between modes should not crash and should update the configuration.
result: [pending]

### 2. Depol mode passed through to GenIce2 generate_ice() call
expected: Generate a hydrate structure with depol mode set to "optimal" (different from default "strict"). The depol mode should be passed through to the GenIce2 generate_ice() call. Verify the generated structure differs from the strict-mode structure (e.g. different water positions due to depolarized hydrogen orientation).
result: [pending]

### 3. Default depol mode is strict (preserves current behavior)
expected: Open the GUI with a fresh Hydrate tab. The depol mode dropdown should default to "strict". Generate a hydrate structure without changing the depol mode — the output should be identical to pre-v4.7 behavior (strict = depolarization preserved = current behavior for existing users).
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0

## Gaps

[none yet]
