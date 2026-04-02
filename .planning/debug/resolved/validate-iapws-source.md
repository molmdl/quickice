---
status: resolved
trigger: "Validate IAPWS Ice Ih reference source - user reports no 2023 release"
created: 2026-04-02T00:00:00Z
updated: 2026-04-02T00:10:00Z
---

## Current Focus

hypothesis: CONFIRMED - The IAPWS Ice Ih equation of state reference had wrong publication year
test: Fixed density_note and docs/principles.md
expecting: Correct references to IAPWS R10-06(2009) for Ice Ih equation of state
next_action: Archive session

## Symptoms

expected: Correct IAPWS publication reference for Ice Ih equation of state
actual: User reports there is no 2023 IAPWS release for Ice Ih
errors: N/A
reproduction: Review codebase references and validate against official source
started: Unknown

## Eliminated

(none)

## Evidence

- timestamp: initial
  checked: state_reference.md
  found: File contains general IAPWS Python library link (pypi), not specific Ice Ih publication
  implication: Need to search codebase for specific IAPWS Ice Ih references and check iapws.org

- timestamp: investigation-1
  checked: iapws.org/release.html
  found: Found R10-06(2009): "Revised Release on the Equation of State 2006 for H2O Ice Ih" - originally released 2006, minor revision 2009
  implication: Confirmed - there is NO 2023 release for Ice Ih

- timestamp: investigation-2
  checked: iapws.org/release/MeltSub.html
  found: R14-08(2011): "Revised Release on the Pressure along the Melting and Sublimation Curves of Ordinary Water Substance"
  implication: R14-08 is about MELTING/SUBLIMATION CURVES, NOT the Equation of State for Ice Ih

- timestamp: investigation-3
  checked: docs/principles.md line 188
  found: "Phase boundaries are based on the IAPWS Release on the Equation of State for Ice Ih (R14-08)"
  implication: INCORRECT - R14-08 is about melting curves, not equation of state. The title is wrong.

- timestamp: fix-1
  checked: lookup.py line 26
  found: density_note referenced "(2023)" - incorrect year
  implication: Fixed to R10-06(2009) with correct URL

- timestamp: fix-2
  checked: docs/principles.md lines 186-191
  found: R14-08 section incorrectly titled "Equation of State for Ice Ih"
  implication: Fixed to correct title "Pressure along the Melting and Sublimation Curves of Ordinary Water Substance"

- timestamp: verification
  checked: All 62 phase mapping tests
  found: All tests passed
  implication: Fix verified, no regressions

## Resolution

root_cause: Two incorrect IAPWS references in codebase:
  1. lookup.py density_note referenced non-existent "2023" release
  2. docs/principles.md conflated R14-08 (melting curves) with R10-06 (equation of state)
fix: Updated both references:
  1. lookup.py: Changed to "IAPWS R10-06(2009): Revised Release on the Equation of State 2006 for H2O Ice Ih (https://www.iapws.org/release/Ice-2009.html)"
  2. docs/principles.md: Corrected R14-08 section title to "Pressure along the Melting and Sublimation Curves of Ordinary Water Substance"
verification: All 62 phase mapping tests pass
files_changed: 
  - quickice/phase_mapping/lookup.py
  - docs/principles.md
