---
status: investigating
trigger: "Fix TIP4P dummy atom MW in validation"
created: 2026-04-21T00:00:00Z
updated: 2026-04-21T00:00:00Z
---

## Current Focus

hypothesis: "Need to update validation regex/pattern to accept 3-atom TIP4P (OW, HW1, HW2) and 4-atom TIP4P/2005 (MW, OW, HW1, HW2)"
test: "Search for validation code in vtk_utils.py and related files"
expecting: "Find where invalid atom ordering is detected and update patterns"
next_action: "Find validation logic and examine current patterns"

## Symptoms

expected: "Validation should accept TIP4P water models: ['OW', 'HW1', 'HW2'] (3 atoms) and ['MW', 'OW', 'HW1', 'HW2'] (4 atoms with dummy)"
actual: "Validation rejects ['MW', 'OW', 'HW1', 'HW2'] with error: Invalid ice atom ordering for molecule 1: expected ['O', 'H', 'H'] or ['OW', 'HW1', 'HW2'], got ['MW', 'OW', 'HW1']."
errors: "ValueError: Invalid ice atom ordering"
started: "WhenTIP4P/2005 water with dummy atom used in hydrate interface"
reproduction: "Run simulation with TIP4P/2005 water model in hydrate region"

## Eliminated

## Evidence

- timestamp: 2026-04-21T00:00:00Z
  checked: "Error message pattern"
  found: "Error shows expected patterns are ['O', 'H', 'H'] or ['OW', 'HW1', 'HW2']"
  implication: "Current validation hardcodes these two patterns, needs expansion"

## Resolution

root_cause: ""
fix: ""
verification: ""
files_changed: []