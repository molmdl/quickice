---
phase: 35-integration-documentation
verified: 2026-06-17T10:30:00Z
status: gaps_found
score: 0/10 screenshot gaps resolved
re_verification: true
previous_status: gaps_found
previous_score: 6/7 must-haves (3 screenshot gaps)
gaps_closed: []
gaps_remaining:
  - "Screenshot files never renamed from tab2-*/tab4-* prefixes"
  - "New screenshots (custom-molecule-panel.png, solute-panel.png, validation-preview.png, solute-source-dropdown.png) never created"
  - "Screenshot update pending notes still at 4 lines in gui-guide.md"
  - "Image references in gui-guide.md point to non-existent renamed files"
regressions: []
---

# Phase 35 Screenshot Re-Verification Report

**Purpose:** Re-verify the Phase 35 screenshot gaps against the ACTUAL state of the filesystem and documentation, not planning documents.

**Previous Verification:** 2026-05-11 — identified 3 screenshot-related gaps (failed/partial)

**Re-verification Result:** **All 4 screenshot gaps remain unresolved.** None of the screenshot issues have been fixed since the original Phase 35 verification.

## Screenshot Gap Status

| # | Gap | Status | Evidence |
|---|-----|--------|----------|
| 1 | Files renamed from tab2-*/tab4-* prefixes | ✗ NOT FIXED | `ls docs/images/` shows: `tab2-hydrate-panel.png`, `tab2-slab-interface.png`, `tab2-pocket-interface.png`, `tab2-piece-interface.png`, `tab4-ion-panel.png` — all still have tabX prefixes |
| 2 | `docs/images/hydrate-panel.png` exists | ✗ NOT FIXED | File does not exist; only `tab2-hydrate-panel.png` exists |
| 3 | `docs/images/ion-panel.png` exists | ✗ NOT FIXED | File does not exist; only `tab4-ion-panel.png` exists |
| 4 | `docs/images/slab-interface.png` exists | ✗ NOT FIXED | File does not exist; only `tab2-slab-interface.png` exists |
| 5 | `docs/images/pocket-interface.png` exists | ✗ NOT FIXED | File does not exist; only `tab2-pocket-interface.png` exists |
| 6 | `docs/images/piece-interface.png` exists | ✗ NOT FIXED | File does not exist; only `tab2-piece-interface.png` exists |
| 7 | `docs/images/custom-molecule-panel.png` created | ✗ NOT FIXED | File does not exist (new Tab 3 screenshot never captured) |
| 8 | `docs/images/solute-panel.png` created | ✗ NOT FIXED | File does not exist (new Tab 4 screenshot never captured) |
| 9 | `docs/images/validation-preview.png` created | ✗ NOT FIXED | File does not exist (Phase 34.5 feature screenshot never captured) |
| 10 | `docs/images/solute-source-dropdown.png` created | ✗ NOT FIXED | File does not exist (Phase 34.6 feature screenshot never captured) |

## Documentation State

### Image References in gui-guide.md (BROKEN)

| Line | Reference | Actual File | Status |
|------|-----------|-------------|--------|
| 241 | `images/hydrate-panel.png` | `tab2-hydrate-panel.png` | ✗ BROKEN — file doesn't exist at referenced path |
| 344 | `images/slab-interface.png` | `tab2-slab-interface.png` | ✗ BROKEN |
| 352 | `images/pocket-interface.png` | `tab2-pocket-interface.png` | ✗ BROKEN |
| 359 | `images/piece-interface.png` | `tab2-piece-interface.png` | ✗ BROKEN |
| 426 | `images/custom-molecule-panel.png` | — | ✗ BROKEN — never created |
| 621 | `images/solute-panel.png` | — | ✗ BROKEN — never created |
| 741 | `images/ion-panel.png` | `tab4-ion-panel.png` | ✗ BROKEN — file doesn't exist at referenced path |

### Pending Notes Still Present

| Line | Note | Status |
|------|------|--------|
| 40 | `v4.5 adds Custom Molecule (Tab 3) and Solute Insertion (Tab 4), moving Ion to Tab 5. Screenshot update pending.` | ✗ NOT REMOVED |
| 430 | `Screenshot update pending for v4.5.` | ✗ NOT REMOVED |
| 625 | `Screenshot update pending for v4.5.` | ✗ NOT REMOVED |
| 745 | `Screenshot update pending for v4.5.` | ✗ NOT REMOVED |

## Files in docs/images/

```
3d-viewer.png
dual-viewport.png
export-menu.png
phase-diagram.png
quickice-v3-gui.png
quickice-v4-gui.png
tab2-hydrate-panel.png       ← needs rename → hydrate-panel.png
tab2-piece-interface.png     ← needs rename → piece-interface.png
tab2-pocket-interface.png    ← needs rename → pocket-interface.png
tab2-slab-interface.png      ← needs rename → slab-interface.png
tab4-ion-panel.png           ← needs rename → ion-panel.png
```

## What Needs to Happen

### Option A: Rename existing files + capture new screenshots (recommended)

1. **Rename 5 existing screenshots:**
   - `mv docs/images/tab2-hydrate-panel.png docs/images/hydrate-panel.png`
   - `mv docs/images/tab2-slab-interface.png docs/images/slab-interface.png`
   - `mv docs/images/tab2-pocket-interface.png docs/images/pocket-interface.png`
   - `mv docs/images/tab2-piece-interface.png docs/images/piece-interface.png`
   - `mv docs/images/tab4-ion-panel.png docs/images/ion-panel.png`

2. **Capture 4 new screenshots (requires running GUI):**
   - `custom-molecule-panel.png` — Tab 3 Custom Molecule panel
   - `solute-panel.png` — Tab 4 Solute Insertion panel
   - `validation-preview.png` — Validate & Preview feature
   - `solute-source-dropdown.png` — Solute source dropdown

3. **Remove 4 "Screenshot update pending" notes from gui-guide.md**

### Option B: Revert image references to match existing filenames

If new screenshots can't be captured:

1. **Revert gui-guide.md image references to use existing filenames:**
   - `images/hydrate-panel.png` → `images/tab2-hydrate-panel.png`
   - `images/ion-panel.png` → `images/tab4-ion-panel.png`
   - etc.

2. **Replace "Screenshot update pending" notes with "Screenshot coming in future release"**

This option is less ideal but at least makes the documentation functional (images display correctly).

## Impact Assessment

- **User-facing impact:** When rendered (GitHub, MkDocs, etc.), gui-guide.md shows **7 broken images** instead of screenshots
- **Developer-facing impact:** Tab-named files are confusing for new contributors (tab2/tab4 prefixes are from v4.0 tab numbering, not v4.5)
- **Severity:** MEDIUM — documentation is functional in text but broken in visual rendering

---

_Verified: 2026-06-17T10:30:00Z_
_Verifier: OpenCode (gsd-verifier)_
_Method: Direct filesystem inspection of docs/images/ + grep of gui-guide.md_
