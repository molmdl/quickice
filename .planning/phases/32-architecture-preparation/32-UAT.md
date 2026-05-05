---
status: testing
phase: 32-architecture-preparation
source: 32-01-SUMMARY.md, 32-02-SUMMARY.md, 32-03-SUMMARY.md
started: 2026-05-05T00:00:00Z
updated: 2026-05-05T00:00:00Z
---

## Current Test

number: 1
name: Application Starts with 4 Tabs
expected: |
  Launch QuickIce application. MainWindow should display 4 tabs in order: Ice Generation (Tab 0), Hydrate Generation (Tab 1), Interface Construction (Tab 2), Ion Insertion (Tab 3). Each tab should switch correctly without crashes.
awaiting: user response

## Tests

### 1. Application Starts with 4 Tabs
expected: Launch QuickIce application. MainWindow should display 4 tabs in order: Ice Generation (Tab 0), Hydrate Generation (Tab 1), Interface Construction (Tab 2), Ion Insertion (Tab 3). Each tab should switch correctly without crashes.
result: pending

### 2. Cross-Tab Data Flow (Ice → Interface)
expected: Generate ice structure on Ice Generation tab, then switch to Interface Construction tab. The ice structure should be available for interface generation (Create Interface button should work with generated ice).
result: pending

### 3. Cross-Tab Data Flow (Hydrate → Interface)
expected: Generate hydrate structure on Hydrate Generation tab, then switch to Interface Construction tab. The hydrate structure should be available for interface generation (Create Interface button should work with generated hydrate).
result: pending

### 4. Cross-Tab Data Flow (Interface → Ion)
expected: Create interface structure on Interface Construction tab, then switch to Ion Insertion tab. The interface structure should be available for ion insertion (Insert Ions button should work with generated interface).
result: pending

### 5. GROMACS Export with Hydrate Guests
expected: Generate hydrate structure with CH4 or THF guests, export to GROMACS format. Check the .top file - guests should have unique moleculetype names (CH4_HYD or THF_HYD), not generic names.
result: pending

### 6. Integration Tests Pass
expected: Run integration tests with: pytest tests/test_integration_v35.py -v. All 11 integration tests should pass without errors.
result: pending

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0

## Gaps

[none yet]
