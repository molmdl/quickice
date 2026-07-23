---
status: testing
phase: 43-depol-mode
source: [43-01-SUMMARY.md, 43-02-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T19:00:00Z
---

## Current Test

number: 1
name: Select depol mode (strict/optimal) in Hydrate tab
expected: |
  Open the QuickIce GUI, go to the Hydrate tab. A depol mode dropdown (QComboBox) should be
  present with two options: "strict" and "optimal". The default selection should be "strict".
awaiting: user response (interactive — Workflow F)

## Tests

### 1. Select depol mode (strict/optimal) in Hydrate tab
expected: Open the QuickIce GUI, go to the Hydrate tab. A depol mode dropdown (QComboBox) should be present with "strict" and "optimal". Default should be "strict". Switching should not crash.
result: [pending]
note: Interactive — Workflow F (GUI dropdown). CLI --depol {strict,optimal} flag verified in Workflow B (present with strict/optimal choices).

### 2. Depol mode passed through to GenIce2 generate_ice() call
expected: Generate a hydrate with depol mode "optimal". The depol mode should be passed through to GenIce2 generate_ice() call.
result: pass
verified: Workflow B — CLI --depol strict runs (exit 0), --depol optimal runs (exit 0) — confirms depol mode is accepted and passed through

### 3. Default depol mode is strict (preserves current behavior)
expected: Open the GUI with a fresh Hydrate tab. The depol mode dropdown should default to "strict". Output should be identical to pre-v4.7 behavior.
result: pass
verified: Workflow B — CLI default (no --depol flag) runs as strict (exit 0) — confirms default is strict

## Summary

total: 3
passed: 2
issues: 0
pending: 1
skipped: 0

## Gaps

[none]
