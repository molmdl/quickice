---
status: testing
phase: 08-all-complete
source: 01-*-SUMMARY.md, 02-*-SUMMARY.md, 03-*-SUMMARY.md, 04-*-SUMMARY.md, 05-*-SUMMARY.md, 05.1-*-SUMMARY.md, 06-*-SUMMARY.md, 07-*-SUMMARY.md
started: 2026-03-28T23:00:00Z
updated: 2026-03-28T23:01:00Z
---

## Current Test

number: 10
name: Phase Lookup - Ice VII at High T Below Melting Curve
expected: |
  T=400K, P=2000MPa returns Liquid (UnknownPhaseError) - below VII melting curve at this T
awaiting: user response

## Tests

### 1. CLI Help Works
expected: Running `python quickice.py --help` displays usage information with all CLI flags.
result: pass

### 2. Valid Temperature Input
expected: CLI accepts temperature between 0-500K (e.g., --temperature 300)
result: pass

### 3. Valid Pressure Input
expected: CLI accepts pressure between 0-10000 MPa (e.g., --pressure 100)
result: pass

### 4. Valid Molecule Count Input
expected: CLI accepts nmolecules between 4-100000 (e.g., --nmolecules 100)
result: pass

### 5. Invalid Input Rejection
expected: Invalid inputs are rejected with clear error messages showing valid ranges
result: pass

### 6. Phase Lookup - Ice Ih at STP
expected: T=273K, P=0.1MPa returns Ice Ih (ice_ih)
result: pass

### 7. Phase Lookup - Ice VII at High Pressure
expected: T=300K, P=2500MPa returns Ice VII (ice_vii)
result: pass

### 8. Phase Lookup - Ice V
expected: T=260K, P=400MPa returns Ice V (ice_v) - previously overlapped with Ice II
result: [pending]

### 9. Phase Lookup - Ice III
expected: T=240K, P=220MPa returns Ice III (ice_iii) - previously overlapped with Ice II
result: [pending]

### 10. Phase Lookup - Ice VII at High T Below Melting Curve
expected: T=400K, P=2000MPa returns Liquid (UnknownPhaseError) - below VII melting curve at this T
result: [pending]

### 11. Phase Lookup - Ice VII at High T Above Melting Curve
expected: T=400K, P=3000MPa returns Ice VII (ice_vii) - above VII melting curve (P > P_melt)
result: [pending]

### 12. Phase Lookup - Ice VII Melting Curve Direction
expected: T=500K, P=4500MPa returns Liquid (UnknownPhaseError) - below VII melting curve at high T
result: [pending]

### 14. Structure Generation
expected: Generates 10 candidates for given T,P conditions
result: [pending]

### 15. Ranking Output
expected: Candidates are ranked with energy, density, diversity scores
result: [pending]

### 16. PDB Output Files
expected: 10 PDB files created in output/ with naming ice_candidate_01.pdb to ice_candidate_10.pdb
result: [pending]

### 17. Phase Diagram Generation
expected: PNG phase diagram generated with user's T,P point marked
result: [pending]

### 18. --output Flag
expected: Custom output directory can be specified with --output flag
result: [pending]

### 19. --no-diagram Flag
expected: Phase diagram can be disabled with --no-diagram flag
result: [pending]

### 20. Ice XI Detection
expected: T=50K, P=10MPa returns Ice XI (ice_xi) - proton-ordered phase at low T
result: [pending]

### 21. Ice X Detection
expected: T=300K, P=50000MPa returns Ice X (ice_x) - symmetric H bonds at extreme P
result: [pending]

### 22. Phase Diagram Extended Ranges
expected: Phase diagram shows T range to 50K and P range to 100 GPa
result: [pending]

### 23. README Exists
expected: README.md exists with installation instructions and quick start
result: [pending]

### 24. Documentation Exists
expected: docs/ folder contains cli-reference.md, ranking.md, principles.md
result: [pending]

### 25. Test Suite Passes
expected: pytest runs and all tests pass
result: [pending]

## Summary

total: 24
passed: 7
issues: 0
pending: 17
skipped: 0

## Gaps

[none yet]
