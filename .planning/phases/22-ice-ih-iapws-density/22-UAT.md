---
status: complete
phase: 22-ice-ih-iapws-density
source: 22-01-SUMMARY.md, 22-02-SUMMARY.md, 22-03-SUMMARY.md, 22-04-SUMMARY.md
started: 2026-04-13T14:00:00Z
updated: 2026-04-13T14:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Tab 1 Ice Ih Density Display
expected: Select Ice Ih phase, density shows IAPWS-calculated value (not hardcoded 0.9167)
result: pass

### 2. 4 Decimal Formatting
expected: Ice Ih density displays with 4 decimal places (e.g., 0.9167 g/cm³)
result: pass

### 3. CLI Ice Ih Density
expected: Run `quickice --temperature 260 --pressure 0.1 --nmolecules 100`, density output shows 4 decimals
result: pass

### 4. Temperature Variation
expected: Change temperature (e.g., 200K vs 270K), Ice Ih density changes accordingly
result: pass

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0

## Gaps

[none]

---
*Phase: 22-ice-ih-iapws-density*
*UAT Complete: 2026-04-13*
