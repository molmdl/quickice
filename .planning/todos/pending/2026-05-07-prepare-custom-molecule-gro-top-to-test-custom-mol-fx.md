---
created: 2026-05-07T03:29
title: prepare custom molecule gro top to test custom mol fx
area: testing
files:
  - custom molecule .gro and .top/.itp files for testing
---

## Problem

Need test data files (GRO coordinate files and TOP/ITP topology files) to verify that custom molecule insertion functionality works correctly with real molecular structures. Currently, the custom molecule workflow (Phase 34-34.2) has been implemented, but needs realistic test cases to ensure:
- GRO file parsing extracts residue names correctly
- ITP topology files are properly bundled in exports
- CustomMoleculeInserter works with actual molecular coordinates
- Two placement modes (random/custom) function as expected

## Solution

Prepare sample custom molecule coordinate (.gro) and topology (.top/.itp) files for comprehensive testing of the custom molecule insertion workflow. Should cover:
- Simple single-atom molecules
- Multi-atom molecules with bonds
- Molecules with different residue names
- Edge cases (large molecules, charged molecules)
