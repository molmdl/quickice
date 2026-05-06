---
created: 2026-05-07T03:33
title: Capture screenshots per Phase 35 suggestions
area: docs
files:
  - docs/README.md
  - docs/gui-guide.md
  - .planning/phases/35-integration-documentation/35-CONTEXT.md
  - .planning/phases/35-integration-documentation/35-RESEARCH.md
---

## Problem

Phase 35 documentation updates require current screenshots to accurately represent v4.5 features. Existing screenshots are outdated and don't show the new Tab 3 (Solute Insertion), Tab 4 (Custom Molecule), and Tab 5 (Ion Insertion - moved from Tab 4). Documentation should have visual examples of the updated 6-tab interface.

## Solution

Per Phase 35 CONTEXT.md and RESEARCH.md requirements:

**Screenshot scope:**
- Full refresh except Tab 1 screenshots (existing Tab 1 screenshots can be reused)
- Focus on Tab 3 (Solute), Tab 4 (Custom Molecule), Tab 5 (Ion in new position)
- Critical UI states showing new v4.5 features

**Naming convention:**
- Remove tabX prefix from figure filenames
- Use descriptive names: `quickice-v4-gui.png` NOT `tab1-quickice-v4-gui.png`
- Keep naming consistent and self-documenting

**Quantity:**
- Minimal but sufficient number to document critical states
- Don't over-document, but ensure key workflows are visualized

**Workflow:**
- Phase 35 plans will include human checkpoint listing required screenshots
- User takes screenshots during execution (not during planning)
- Screenshots serve as documentation checkpoints to verify UI matches docs

**Required screenshots (from Phase 35 scope):**
- Main window with 6-tab layout (Tab 0-5 visible)
- Tab 3 (Solute Insertion) with THF/CH₄ concentration controls
- Tab 4 (Custom Molecule) with GRO/ITP upload buttons and placement mode dropdown
- Tab 5 (Ion Insertion) showing ion source dropdown and charge warning
- Updated help dialog with correct keyboard shortcuts (Ctrl+L, Ctrl+M, Ctrl+H)
- Example GROMACS export showing molecule ordering (if needed for docs)
