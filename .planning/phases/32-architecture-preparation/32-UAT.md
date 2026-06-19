---
status: testing
phase: 32-architecture-preparation
source: 32-01-SUMMARY.md, 32-02-SUMMARY.md, 32-03-SUMMARY.md
started: 2026-05-05T00:00:00Z
updated: 2026-06-19T00:00:00Z
stale_warnings:
  - "Tests 1-4 reference 4 tabs and Ion at Tab 3 — superseded by 6-tab layout (Phases 33-34.3). Current layout: Ice(0) Hydrate(1) Interface(2) Custom(3) Solute(4) Ion(5). See 34.3-UAT for current tab order tests."
  - "Test 5 references CH4_HYD/THF_HYD naming — superseded by CH4_H/THF_H (Quick Task 028) and CH4_L/THF_L for liquid solutes (Phase 34.2). See v4.5 batch checklist Workflow 9 for current naming verification."
---

## Current Test

number: 5
name: GROMACS Export with Hydrate Guests
expected: |
  Generate hydrate structure with CH4 or THF guests, export to GROMACS format. Check the .top file - guests should have unique moleculetype names (CH4_H or THF_H), not generic names.
awaiting: user response

## Tests

### 1. Application Starts with 6 Tabs
expected: Launch QuickIce application. MainWindow should display 6 tabs in order: Ice(0) Hydrate(1) Interface(2) Custom(3) Solute(4) Ion(5). Each tab should switch correctly without crashes.
result: ✅ passed (2026-06-19, WF1 — 6 tabs verified: Ice(0) Hydrate(1) Interface(2) Custom(3) Solute(4) Ion(5), all switch without crashes)
note: Original test specified 4 tabs; v4.5 now has 6 tabs. Full tab order verification in 34.3-UAT.

### 2. Cross-Tab Data Flow (Ice → Interface)
expected: Generate ice structure on Ice Generation tab, then switch to Interface Construction tab. The ice structure should be available for interface generation (Create Interface button should work with generated ice).
result: ✅ passed (2026-06-19, WF2+WF4 — ice generation verified, ice→interface flow works)

### 3. Cross-Tab Data Flow (Hydrate → Interface)
expected: Generate hydrate structure on Hydrate Generation tab, then switch to Interface Construction tab. The hydrate structure should be available for interface generation (Create Interface button should work with generated hydrate).
result: ✅ passed (2026-06-19, WF4 — hydrate→interface flow works)

### 4. Cross-Tab Data Flow (Interface → Ion)
expected: Create interface structure on Interface Construction tab, then switch to Ion Insertion tab. The interface structure should be available for ion insertion (Insert Ions button should work with generated interface).
result: ✅ passed (2026-06-19, WF4 — interface→ion flow works)

### 5. GROMACS Export with Hydrate Guests
expected: Generate hydrate structure with CH4 or THF guests, export to GROMACS format. Check the .top file - guests should have unique moleculetype names (CH4_H or THF_H), not generic names.
result: pending

### 6. Integration Tests Pass
expected: Run integration tests with: pytest tests/test_integration_v35.py -v. All 11 integration tests should pass without errors.
result: ✅ passed (2026-06-19, 41.16s, 11/11 tests)

## Summary

total: 6
passed: 4
issues: 0
pending: 1
skipped: 0
stale: 2 (Tests 1 and 5 reference pre-v4.5 state — see stale_warnings in frontmatter)

## Gaps

[none yet]
