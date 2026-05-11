---
created: 2026-05-07T03:32
title: Group UAT items by workflow for batch testing
area: testing
files:
  - .planning/phases/32-*/*-UAT.md
  - .planning/phases/33-*/*-UAT.md
  - .planning/phases/34*/*-UAT.md
  - .planning/phases/35-*/*-UAT.md
---

## Problem

After Phase 35 (Integration & Documentation) completes, all UAT files for milestone v4.5 will need user verification. Currently, UAT items are organized by phase (32, 33, 34, 34.1, 34.2, 35), but many items can be tested together because they belong to the same user workflow. Testing each phase's UAT individually would be inefficient and repetitive.

Need to:
- Review all UAT files from phases 32-35
- Identify common user workflows (e.g., ice generation, hydrate creation, solute insertion, custom molecule upload, GROMACS export)
- Group UAT items that can be tested within the same workflow session
- Create a batch testing plan that minimizes redundant setup/teardown

## Solution

After Phase 35 completion:
1. Scan all *-UAT.md files in phases 32-35
2. Extract individual test items and their requirements
3. Group by workflow:
   - Ice generation workflow (Tab 1 related items)
   - Hydrate workflow (Tab 2 related items)
   - Interface workflow (Tab 3 related items)
   - Solute insertion workflow (Tab 4 related items)
   - Custom molecule workflow (Tab 5 related items)
   - Ion insertion workflow (Tab 6 related items)
   - GROMACS export workflow (multi-tab items)
   - Keyboard shortcuts/UI workflow
4. Create consolidated batch testing checklist organized by workflow
5. User can then test all items in a workflow in one session before moving to next workflow

This approach reduces context switching and allows testing related features together.
