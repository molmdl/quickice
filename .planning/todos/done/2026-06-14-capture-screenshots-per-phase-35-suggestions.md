---
created: 2026-05-07T03:33
updated: 2026-06-14
title: Capture screenshots per Phase 35 suggestions
area: docs
files:
  - docs/images/
  - docs/README.md
  - docs/gui-guide.md
---

## Problem

Phase 35 documentation updates require current screenshots to accurately represent v4.5 features. Existing screenshots are outdated and don't show the new Tab 3 (Custom Molecule), Tab 4 (Solute Insertion), or the updated Tab 5 (Ion with source dropdown). Documentation should have visual examples of the updated 6-tab interface.

**Source:** 35-06-SUMMARY.md (commit f345ca9, Option 1 decision confirmed)

## Current Tab Order (post-Phase 34.3 swap)

| Tab # | Name |
|-------|------|
| 0 | Ice Generation |
| 1 | Hydrate Generation |
| 2 | Interface Construction |
| 3 | Custom Molecule |
| 4 | Solute Insertion |
| 5 | Ion Insertion |

## Step 1: Rename existing screenshots (in `docs/images/`)

```bash
cd docs/images
mv tab2-hydrate-panel.png     hydrate-panel.png
mv tab4-ion-panel.png          ion-panel.png
mv tab2-piece-interface.png   piece-interface.png
mv tab2-slab-interface.png    slab-interface.png
mv tab2-pocket-interface.png  pocket-interface.png
```

## Step 2: Capture new screenshots (6 total)

| # | Filename | What to Show | Which Tab |
|---|----------|-------------|-----------|
| 1 | `quickice-v4-gui.png` | Main window showing all 6 tabs | All |
| 2 | `custom-molecule-panel.png` | Custom Molecule panel with Validate & Preview button visible | Tab 3 |
| 3 | `solute-panel.png` | Solute Insertion panel with Source dropdown visible | Tab 4 |
| 4 | `validation-preview.png` | Semi-transparent preview rendering (Phase 34.5 feature) | Tab 3 |
| 5 | `solute-source-dropdown.png` | Source dropdown expanded (Interface / Custom Molecule) | Tab 4 |
| 6 | *(Optional)* `custom-molecule-complete-system.png` | Complete system viewer with custom molecules rendered | Tab 3 |

## Step 3: Verify documentation references

Already done in commit `f345ca9` — all `tabX-*` references removed from docs.

## Prerequisites

- GUI must be running (requires display/X11 — cannot be done remotely over SSH without X forwarding)
- A structure must be generated on Tab 0 first (to populate the viewer for screenshots)
- For screenshots 4-6: must have an interface structure generated and custom molecules loaded

## Status

- [ ] Step 1: Rename existing files
- [ ] Step 2: Capture new screenshots
- [ ] Step 3: Verify doc references (already done in commit f345ca9)
