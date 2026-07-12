# Phase 48: Documentation - Research

**Researched:** 2026-07-12
**Domain:** Technical documentation update + PySide6 help dialog restructure (v4.7 Extended Hydrate Generation milestone — FINAL phase)
**Confidence:** HIGH

## Summary

Phase 48 is pure documentation work: updating 4 existing external doc files (README.md, docs/gui-guide.md, docs/cli-reference.md, docs/gro-itp-guide.md) + restructuring 1 in-app help file (quickice/gui/help_dialog.py) + a tooltip audit of the hydrate panel. All v4.7 code (Phases 38-47) is COMPLETE; this phase documents shipped features. No new production code is required EXCEPT the help_dialog.py restructure (UI code) and optional tooltip additions.

The research audited all 5 doc files against the actual codebase (parser.py, types.py, hydrate_panel.py, pipeline.py, STATE.md). **The single most important finding is a flag-name discrepancy**: the phase objective lists flags `--custom-guest`, `--custom-guest-itp`, `--guest-small`, `--guest-large`, `--hydrate-lattice`, but NONE of these exist in the codebase. The actual CLI flags are `--lattice-type` (extended to 10 choices), `--cage-guest` (mixed occupancy, repeatable `KEY=GUEST:OCC`), `--depol` (strict/optimal). Furthermore, **custom guest in hydrate is GUI-ONLY for v4.7** — STATE.md line 183 explicitly states "custom-guest CLI deferred — research Q1 recommendation", and the CLI `HydrateConfig` construction (pipeline.py:332-342) never sets `guest_residue_name`/`guest_gro_path` from args. Documenting non-existent flags would be a critical error; the docs MUST use the real flag names and state that custom-guest-in-hydrate upload is a GUI-only feature.

**Primary recommendation:** Split into ~14 independent plans organized by file/section (no cross-file dependencies, safe for sequential execution). External docs (DOCS-01/02-ext/03/04) → 8 plans touching 4 files. In-app help restructure (DOCS-02-in-app) → 3 plans touching help_dialog.py. Tooltip audit → 1 plan touching hydrate_panel.py. Version-string bump + final verification → 2 plans. Every plan touches a distinct file or a distinct non-overlapping section, so merge conflicts are impossible.

---

## 1. Current Doc State Audit (per file — what exists vs what's missing)

Each file was read in full. Line numbers are exact insertion points.

### 1a. README.md (414 lines) — DOCS-01 + version sweep
**Existing sections:** Overview, Binary Distribution, Installation, Quick Start, Entry Point, Features (6-Tab Workflow: Tab 0-5), GROMACS Export, Ice Phase Support, Documentation, Known Issues, Dependencies, References, Testing, Project Structure.
**Outdated / missing:**
- **Line 14:** "QuickIce v4.5 provides a 6-tab GUI workflow" → must read v4.7
- **Lines 124-134 (Tab 1: Hydrate Generation):** says "Structure types — sI, sII, sH" (ONLY 3), "Guest molecules — CH₄ (methane), THF (tetrahydrofuran)", "Cage occupancy — Configure guest occupancy per cage type". MISSING: 7 more lattice types, custom guest upload, mixed cage occupancy (per-cage-type), depol mode. → **Full rewrite of Tab 1 bullet list (DOCS-01 core)**
- **Lines 185-216 (GROMACS Export / Molecule Ordering):** table lists `CH4_H`/`THF_H` but NOT custom-guest `MOL_H` row, and doesn't mention custom guest ITP staging. → Add custom-guest row + note that custom guest `.itp` is bundled/comment-out-atomtypes-merged
- **Lines 289-297 (Known Issues):** Line 296 "Only pure water ice systems supported" — **FALSE now** (hydrate/filled-ice/custom-guest systems shipped). Line 297 "CLI support for v4.5 features" → v4.7. → Remove/rewrite the "only pure water" lie
- **Line 413:** "QuickIce v4.5 — Solute & Custom Molecule Insertion" → v4.7 subtitle
- **Line 414:** "Last updated: 2026-06-15" → bump date
- **MISSING entirely:** A "Custom Guest in Hydrate Workflow (upload → validate → generate → export)" subsection — this is DOCS-01's explicit success criterion #1. Insert after the Tab 1 bullet list (~line 134) or as a new subsection under GROMACS Export.
**Insertion points:** Tab 1 block ~lines 124-134; Known Issues ~line 296; footer lines 413-414.

### 1b. docs/gui-guide.md (862 lines) — DOCS-02 external
**Existing sections:** Overview, Getting Started, Input Panel, Phase Diagram, 3D Viewer, Export Options, Keyboard Shortcuts, Hydrate Generation (Tab 1), Interface Construction (Tab 2), Custom Molecule Upload (Tab 3), Solute Insertion (Tab 4), Ion Insertion (Tab 5), Help Menu, Troubleshooting, Further Reading.
**Outdated / missing:**
- **Line 3:** "QuickIce v4.5 graphical user interface" → v4.7
- **Lines 39-40:** image caption "QuickIce GUI v4.5", note "v4.5 adds Custom Molecule... moving Ion to Tab 5" → v4.7
- **Lines 226-303 (Hydrate Generation Tab 1) — the bulk of DOCS-02 external:**
  - Line 233: "Select hydrate lattice type (sI, sII, sH)" → all 10
  - Lines 246-252 (Lattice Types table): 3 rows only → **replace with 10-row table** (key, genice name, description, cage_type_map, triclinic, water-only — see §3 / Code Examples). Add water-only note (sT′/17 hide guest+occupancy rows) and triclinic note (c0te/c1te blocked in interface).
  - Lines 254-260 (Guest Molecules): only CH4/THF → add custom guest upload (GUI-only: .gro+.itp, validation, "Custom: {residue}" appears in per-cage combos)
  - Lines 262-267 (Cage Occupancy): "Small cages / Large cages" only → **replace with per-cage-type mixed occupancy** (one guest QComboBox + one occupancy QDoubleSpinBox per cage_type_map key; multi-guest e.g. CH4 in small + THF in large)
  - Lines 276-284 (Workflow): "Select lattice type (sI, sII, or sH)" → outdated step
  - **MISSING:** Custom Guest Upload subsection; Mixed Cage Occupancy subsection; Depol Mode subsection. Insert all three within the Tab 1 section (after Cage Occupancy, before 3D Viewer ~line 286).
- **Line 182:** "QuickIce v4.0 added interface construction; v4.5 adds solute..." → v4.7
**Insertion points:** Header line 3; Tab 1 section lines 226-303 (multiple subsections).

### 1c. docs/cli-reference.md (1231 lines) — DOCS-03
**Existing sections:** Usage, Required Args, Optional Args, Ice Phase Examples, Exit Codes, Interface Generation Flags, Hydrate Generation Flags, Custom Molecule Insertion Flags, Solute Insertion Flags, Ion Insertion Flags, Validation Rules, Pipeline vs Ice-Only, Output Files, Common Issues, Validation, Unified Entry Point, Mode Selection, Example Scripts.
**Outdated / missing (Hydrate Generation Flags, lines 538-667):**
- **Lines 559-581 (--lattice-type):** choices shown as `sI, sII, sH` only → **expand to 10 choices** with per-type table (cages, water-only, triclinic). Add note: triclinic types (c0te/c1te/sH) blocked in `--interface` mode; water-only types (sTprime/17) ignore `--guest`/`--cage-guest`.
- **Lines 585-606 (--guest):** needs a **DEPRECATED** banner: "Use `--cage-guest` for mixed occupancy. Kept for backward compat (no behavior change). Custom guest in hydrate is GUI-ONLY for v4.7 — no CLI flag."
- **Lines 632-667 (--cage-occupancy-small / --cage-occupancy-large):** needs **DEPRECATED** banners (use `--cage-guest`).
- **MISSING flag: `--cage-guest`** (mixed occupancy, repeatable `KEY=GUEST:OCC`). Insert after `--cage-occupancy-large` (~line 667). Include: KEY ∈ cage_type_map keys (small/medium/large/guest), GUEST ∈ CH4/THF (built-in only on CLI for v4.7), OCC 0-100, example `--cage-guest small=CH4:60 --cage-guest large=THF:100`. Note filled-ice gotcha: use key `small` (NOT `guest`) for c2te/ice1hte/c0te/c1te.
- **MISSING flag: `--depol`** (strict|optimal, default strict). Insert after `--cage-guest`. strict = ice rules / zero net dipole; optimal = relaxed.
- **Line 169-170:** `--version` example output "4.5.0" → 4.7.0 (if version bumped, see Open Questions).
- **Line 182:** "v4.5 adds solute and custom molecule insertion" → v4.7
- Hydrate examples (lines 552-627): add examples using `--cage-guest`, `--depol`, and the extended `--lattice-type c0te`/`sTprime`.
**Insertion points:** Hydrate Generation Flags section lines 538-667 (rewrite + 2 new flag subsections).

### 1d. docs/gro-itp-guide.md (938 lines) — DOCS-04
**Existing sections:** Intro, GRO Format, Creating GRO, ITP Format, Creating ITP, Validation, Examples, Troubleshooting, Workflow Example, References, Quick Reference Checklist.
**Outdated / missing:**
- **Line 3:** "QuickIce v4.5" → v4.7
- **Line 481:** has an OPLS-AA comb-rule-3 warning (good) but NO hydrate-custom-guest-specific comb-rule=2 requirement
- **MISSING: "Custom Guest ITP Requirements (for Hydrate Cage Guests)" section — DOCS-04 core.** Insert after the Validation section (~line 566) or as a new top-level section. Must cover (exact rules — see Code Examples §DOCS-04):
  1. comb-rule=2 MANDATORY (rejected if `[ defaults ]` comb-rule=1; absent `[ defaults ]` OK because main .top supplies comb-rule=2)
  2. Residue base name ≤3 chars (GRO columns 6-10 = 5 chars max; `_H` suffix appended → `{base}_H`; e.g. MOL→MOL_H OK, ETHAN→ETHAN_H REJECTED)
  3. `_H` suffix convention (hydrate guests `_H`, liquid solutes `_L`; `transform_guest_itp` rewrites `[ atoms ]` resname)
  4. `[ atomtypes ]` commented out + merged into main .top via `_merge_custom_atomtypes`
  5. This is distinct from the existing Tab-3 LIQUID custom-molecule ITP (which does NOT get the `_H` suffix and does NOT require ≤3 chars) — make the distinction explicit to avoid confusion
- **Lines 937-938:** "Guide version: v4.5" / "For QuickIce v4.5 documentation" → v4.7
**Insertion points:** New section after Validation (~line 566); footer lines 937-938.

### 1e. quickice/gui/help_dialog.py (258 lines) — DOCS-02 in-app restructure
**Current structure:** `QScrollArea` → `QWidget` → `QVBoxLayout` (lines 42-50). Sections as `QLabel`s stacked vertically: Introduction (54), Keyboard Shortcuts (64-83), Workflow per-tab (86-133), Dimension Relationships (136-164), Best Practices (167-194), Custom Molecule Preparation (197-206), More Information (209-217), Important Notes (220-232). OK button at bottom (244-246).
**Outdated:**
- **Line 97:** "Select lattice type (sI, sII, sH)" — OUTDATED (only 3 lattices)
- **NO v4.7 content:** no extended lattices, no custom guest upload, no mixed occupancy, no depol mode
- **Structure problem:** single scrolling textbox — content has outgrown it (per phase objective). Needs restructure to indexed format.
**What to do:** (1) Restructure skeleton to `QStackedWidget` + `QListWidget` TOC (see §4). (2) Migrate existing 8 sections to pages. (3) Add 4 new v4.7 pages: Extended Lattice Types, Custom Guest in Hydrate (GUI-only), Mixed Cage Occupancy, Depol Mode. (4) Fix the "sI, sII, sH" line. (5) Add a headless smoke test.
**No existing tests** for help_dialog (grep found none) — the restructure plan must add one.

---

## 2. v4.7 Feature Documentation Requirements (what content goes where)

| v4.7 Feature | Doc file(s) | Section / content to write | Requirement |
|---|---|---|---|
| Extended lattice types (10) | README.md (Tab 1), gui-guide.md (Lattice Types table), cli-reference.md (--lattice-type), help_dialog.py (new page) | 10-row table: key, genice name, description, cage_type_map, triclinic, water-only. Note: sT′/17 water-only (hide guest UI); c0te/c1te/sH triclinic (blocked in --interface); 16 = Ice XVI empty framework | DOCS-02, DOCS-03 |
| Custom guest upload (GUI-only) | README.md (new workflow subsection), gui-guide.md (new subsection), gro-itp-guide.md (new ITP-requirements section), help_dialog.py (new page) | upload .gro+.itp → validate (comb-rule=2, ≤3-char resname, atom count) → "Custom: {residue}" appears in per-cage combos → generate → export (MOL_H residue, .itp bundled). STATE: GUI-only, no CLI flag for v4.7 | DOCS-01, DOCS-02, DOCS-04 |
| Custom guest ITP requirements | gro-itp-guide.md (new section), help_dialog.py (mention in custom-guest page) | comb-rule=2 mandatory; residue ≤3 chars; `_H` suffix; `[ atomtypes ]` commented-out+merged; distinct from Tab-3 liquid custom molecule | DOCS-04 |
| Mixed cage occupancy | README.md (Tab 1), gui-guide.md (new subsection), cli-reference.md (--cage-guest), help_dialog.py (new page) | Per-cage-type guest QComboBox + occupancy QDoubleSpinBox (one row per cage_type_map key); multi-guest e.g. CH4 small + THF large; CLI `--cage-guest KEY=GUEST:OCC` (repeatable); `--guest`/`--cage-occupancy-small/large` DEPRECATED; filled-ice gotcha: key `small` not `guest` | DOCS-02, DOCS-03 |
| Depol mode | README.md (Tab 1), gui-guide.md (new subsection), cli-reference.md (--depol), help_dialog.py (new page) | strict (ice rules, zero net dipole, default) vs optimal (relaxed); CLI `--depol strict|optimal`; GUI dropdown in hydrate panel | DOCS-02, DOCS-03 |
| CLI flags (deprecated marking) | cli-reference.md | Mark `--guest`, `--cage-occupancy-small`, `--cage-occupancy-large` DEPRECATED (kept, no behavior change) | DOCS-03 |
| Version string v4.5 → v4.7 | README.md, gui-guide.md, cli-reference.md, gro-itp-guide.md, README_bin.md, quickice/__init__.py, parser.py | Sweep all "v4.5"/"4.5.0" → "v4.7"/"4.7.0" (see §7 verification) | (cross-cutting) |

---

## 3. CLI Flags Inventory (complete — sourced from parser.py:199-280)

**v4.7 NEW hydrate flags:**
| Flag | Type | Choices/Format | Default | Help text (verbatim from parser.py) |
|------|------|----------------|---------|--------------------------------------|
| `--lattice-type` | str | `sI, sII, sH, c0te, c1te, c2te, ice1hte, sTprime, 16, 17` (10) | `sI` | "Hydrate lattice type (default: sI)" |
| `--cage-guest` | append (repeatable) | `KEY=GUEST:OCC` | None | "Per-cage-type guest assignment (repeatable). Format: --cage-guest small=CH4:60 --cage-guest large=THF:100. KEY is a cage_type_map key (small/medium/large/guest). GUEST is CH4 or THF (built-in only on CLI for v4.7). OCC is 0-100 occupancy percentage. When supplied, overrides --guest/--cage-occupancy-small/large." |
| `--depol` | str | `strict, optimal` | `strict` | "Depolarization mode (default: strict). 'strict' = ice rules, zero net dipole; 'optimal' = relaxed dipole optimization." |

**DEPRECATED hydrate flags (mark in docs, do NOT remove):**
| Flag | Status | Note to add in docs |
|------|--------|--------------------|
| `--guest` | DEPRECATED | "(deprecated; use --cage-guest for mixed occupancy)" — already in parser help text. Custom guest in hydrate is GUI-only for v4.7. |
| `--cage-occupancy-small` | DEPRECATED | "(deprecated; use --cage-guest for mixed occupancy)" |
| `--cage-occupancy-large` | DEPRECATED | "(deprecated; use --cage-guest for mixed occupancy)" |

**UNCHANGED hydrate flags:** `--hydrate`, `--supercell-x`, `--supercell-y`, `--supercell-z`
**NON-hydrate flags (unchanged, not in scope):** `--temperature/-T`, `--pressure/-P`, `--nmolecules/-N`, `--output/-o`, `--no-diagram`, `--gromacs/-g`, `--candidate/-c`, `--no-overwrite`, `--version/-V`, `--interface`, `--mode/-m`, `--box-x/y/z`, `--ice-thickness/-t`, `--water-thickness/-w`, `--pocket-diameter/-d`, `--pocket-shape`, `--seed`, `--custom-gro`, `--custom-itp`, `--custom-placement`, `--custom-count`, `--custom-concentration`, `--custom-positions-file`, `--solute-type`, `--solute-concentration`, `--solute-source`, `--ion-concentration`, `--ion-source`, `--cli`, `--gui`

> **DO NOT document flags `--custom-guest`, `--custom-guest-itp`, `--guest-small`, `--guest-large`, or `--hydrate-lattice`** — they do not exist. `--custom-gro`/`--custom-itp` exist but are for Tab-3 LIQUID custom molecules (require `--interface`), not hydrate cage guests.

---

## 4. Help Dialog Restructure Approach

**Recommendation: `QStackedWidget` + `QListWidget` TOC (left nav, right pages).** HIGH confidence — API verified against installed PySide6 6.10.2 (see Architecture Patterns §1 for full code example).

**Why this over the alternatives:**
| Option | Verdict | Reason |
|--------|---------|-------|
| QTabWidget | Rejected | ~11 sections at 450-600px wide → tabs ~40px each → labels truncate. Good for ≤8 sections; this use case exceeds that. |
| QListWidget + QStackedWidget (TOC) | **RECOMMENDED** | Left 160px nav column scales to any section count; right page stretches; clean modal dialog; built-in keyboard nav. |
| QSplitter | Rejected | Resizable divider adds complexity for no benefit in a small fixed-size modal. |

**Section list (11 pages — 8 migrated + 4 new, reorganized):**
1. Introduction (migrate)
2. Keyboard Shortcuts (migrate)
3. Workflow — All Tabs (migrate, fix "sI, sII, sH" → 10 lattices at line 97)
4. **Extended Lattice Types (NEW v4.7)** — the 10-row table + water-only/triclinic notes
5. **Custom Guest in Hydrate (NEW v4.7)** — GUI-only upload workflow + ITP requirements summary
6. **Mixed Cage Occupancy (NEW v4.7)** — per-cage guest+occupancy, multi-guest
7. **Depol Mode (NEW v4.7)** — strict vs optimal
8. Dimension Relationships (migrate)
9. Best Practices (migrate)
10. Custom Molecule Preparation (migrate — clarify this is Tab-3 LIQUID, distinct from hydrate custom guest)
11. More Information + Important Notes (migrate, combine)

**Constraints (from current help_dialog.py):** min width 450/max 600, min height 400/max 700 → **recommend widening to min 600/max 800** to fit TOC+content comfortably. OK button stays in the OUTER layout (never inside a stacked page). See Pitfall 5.

---

## 5. Tooltip Audit (what exists, what needs updating)

**Mechanism:** `HelpIcon(QLabel)` in `quickice/gui/view.py:638` — "?" badge with `setToolTip` + `QToolTip.showText` on `enterEvent`. Panels use `HelpIcon("text")` next to controls AND/OR `widget.setToolTip("text")` directly.

**Per-panel status:**
| Panel | setToolTip calls | HelpIcon uses | v4.7 coverage | Action |
|------|------------------|---------------|---------------|--------|
| hydrate_panel.py | **0** setToolTip | 4 HelpIcon (lattice line 193, depol line 223, generate line 103, +1) | Lattice tooltip (line 193-204) DOES list all 10 types ✓; depol tooltip (223) ✓; custom-guest group exists but **per-cage guest combos + occupancy spins (lines 487, 515) have NO tooltip** | **ADD tooltips to per-cage guest QComboBox + occupancy QDoubleSpinBox** (mixed-occupancy widgets lack help) |
| interface_panel.py | ~15 setToolTip + HelpIcon | Many | Hydrate-interface path tooltips present | Verify only (no v4.7 gap expected) |
| custom_molecule_panel.py | ~6 setToolTip + ~12 HelpIcon | Many | Tab-3 liquid custom molecule — already documented | Verify only |
| solute_panel.py | ~10 setToolTip + HelpIcon | Many | Already documented | Verify only |
| ion_panel.py | ~7 setToolTip + HelpIcon | Many | Already documented | Verify only |

**The one real gap:** `hydrate_panel.py` per-cage guest combos (line 487) and occupancy spinboxes (line 515) — the v4.7 mixed-occupancy widgets — have NEITHER `setToolTip` NOR `HelpIcon`. Plan should add a `HelpIcon` to each cage row explaining: guest choice (built-in CH4/THF or uploaded custom; built-in only on CLI for v4.7) and occupancy (0-100%, default 100%).

---

## 6. Recommended Plan Split Strategy (14 plans — independent, no cross-file deps)

All plans touch DISTINCT files or non-overlapping sections → safe sequential execution, zero merge conflicts. Organized into the official 48-01 (external docs) / 48-02 (in-app help) split, then aggressively sub-split per the user's request.

### Group A — External docs (DOCS-01, DOCS-02-external, DOCS-03, DOCS-04)
| # | Plan | File(s) touched | Requirement | Content |
|---|------|-----------------|-------------|---------|
| A1 | README Tab 1 hydrate rewrite + custom-guest workflow | README.md (lines 124-134 + new subsection) | DOCS-01 | Replace 3-lattice list with 10; add "Custom Guest in Hydrate Workflow (upload→validate→generate→export)" subsection; add mixed-occupancy + depol bullets |
| A2 | README version + Known Issues + footer sweep | README.md (lines 14, 296-297, 413-414) | cross-cutting | v4.5→v4.7; remove "only pure water" lie; bump subtitle + date |
| A3 | GUI guide — Hydrate lattice types table (10 rows) | docs/gui-guide.md (lines 246-252) | DOCS-02-ext | 10-row table with cage_type_map/triclinic/water-only; water-only + triclinic notes |
| A4 | GUI guide — Custom guest upload + mixed occupancy + depol subsections | docs/gui-guide.md (lines 254-284, new subsections) | DOCS-02-ext | 3 new subsections within Tab 1; fix workflow steps; mark GUI-only |
| A5 | GUI guide — header/version sweep | docs/gui-guide.md (lines 3, 39-40, 182) | cross-cutting | v4.5→v4.7 strings |
| A6 | CLI ref — hydrate flags rewrite + 2 new flags | docs/cli-reference.md (lines 538-667) | DOCS-03 | Expand --lattice-type to 10; add --cage-guest + --depol subsections; mark --guest/--cage-occupancy-* DEPRECATED; add filled-ice gotcha note; custom-guest-is-GUI-only note |
| A7 | CLI ref — version/examples sweep | docs/cli-reference.md (lines 169-170, 182, examples) | cross-cutting | v4.5→v4.7; add --cage-guest/--depol/extended-lattice examples |
| A8 | GRO/ITP guide — custom guest ITP requirements section | docs/gro-itp-guide.md (new section after line 566, footer 937-938) | DOCS-04 | comb-rule=2 mandatory; ≤3-char resname; `_H` suffix; atomtypes comment-out+merge; distinct from Tab-3 liquid custom molecule |

### Group B — In-app help (DOCS-02 in-app)
| # | Plan | File(s) touched | Requirement | Content |
|---|------|-----------------|-------------|---------|
| B1 | help_dialog.py skeleton restructure | quickice/gui/help_dialog.py | DOCS-02-in-app | Replace QScrollArea with QStackedWidget+QListWidget TOC; migrate 8 existing sections to pages verbatim; widen dialog to 600-800px; keep OK button in outer layout. NO content changes yet. |
| B2 | help_dialog.py v4.7 content pages | quickice/gui/help_dialog.py | DOCS-02-in-app | Add 4 new pages (Extended Lattices, Custom Guest in Hydrate, Mixed Occupancy, Depol); fix "sI, sII, sH" line. Depends on B1 skeleton but SAME file → run B1 then B2 sequentially. |
| B3 | help_dialog headless smoke test | tests/test_help_dialog.py (NEW) | DOCS-02-in-app | `QT_QPA_PLATFORM=offscreen`; assert toc.count()==11, pages.count()==11, no v4.5 string, all 10 lattice names present. |

### Group C — Tooltip audit
| # | Plan | File(s) touched | Requirement | Content |
|---|------|-----------------|-------------|---------|
| C1 | hydrate_panel per-cage tooltips | quickice/gui/hydrate_panel.py (lines 487, 515) | DOCS-02-in-app | Add HelpIcon to each cage row (guest combo + occupancy spin) explaining mixed occupancy. Independent of B1/B2 (different file). |

### Group D — Version bump + verification
| # | Plan | File(s) touched | Requirement | Content |
|---|------|-----------------|-------------|---------|
| D1 | Version string bump 4.5.0 → 4.7.0 | quickice/__init__.py:3, quickice/cli/parser.py:386 | cross-cutting | 2-line code change so `--version` matches docs. (Ask user — see Open Questions.) |
| D2 | Final verification sweep | (no file edits — verification only) | all DOCS | grep for outdated strings (v4.5, "only pure water", "sI, sII, sH" alone); DOCS-01..04 coverage matrix; confirm help_dialog test passes under offscreen. |

**Dependency note:** B2 depends on B1 (same file, skeleton first). All other plans are independent. Suggested order: A1-A8 (any order) → B1 → B2 → B3 → C1 → D1 → D2. Total = 14 plans (within the 10-20 target).

---

## 7. Verification Approach (how to check completeness)

**Automated greps (run in D2 — `rg` is NOT installed; use `grep` or the Grep tool):**
```bash
# 1. No stale v4.5 version strings in docs (allow historical mention in changelog-style prose)
grep -rn "v4\.5\|QuickIce v4\.5" README.md docs/ quickice/gui/help_dialog.py
# Expected: ZERO matches (or only intentional historical references)

# 2. No "only pure water" lie
grep -rn "Only pure water" README.md docs/
# Expected: ZERO matches

# 3. No lone "sI, sII, sH" 3-lattice lists
grep -rn "sI, sII, sH" README.md docs/ quickice/gui/help_dialog.py
# Expected: ZERO matches lacking the other 7 types (or matches inside the 10-row table context)

# 4. All 10 lattice keys appear in gui-guide + help_dialog
grep -rln "c0te" docs/gui-guide.md quickice/gui/help_dialog.py  # filled ice C0
grep -rln "sTprime" docs/gui-guide.md quickice/gui/help_dialog.py  # water-only
grep -rln "ice1hte" docs/cli-reference.md  # CLI ref must list all 10 choices

# 5. New CLI flags documented
grep -rln "\-\-cage-guest" docs/cli-reference.md
grep -rln "\-\-depol" docs/cli-reference.md

# 6. DEPRECATED banners present
grep -rln "deprecated" docs/cli-reference.md  # --guest, --cage-occupancy-small/large

# 7. DOCS-04 ITP requirements present
grep -rln "comb-rule" docs/gro-itp-guide.md  # must mention comb-rule=2 mandatory
grep -rln "_H" docs/gro-itp-guide.md  # must explain _H suffix

# 8. Version string bumped
grep -n "__version__" quickice/__init__.py  # should be 4.7.0
python -m quickice --version  # should print 4.7.0
```

**DOCS requirements coverage matrix (manual check in D2):**
| Req | Success criterion | Verified by |
|-----|------------------|-----------|
| DOCS-01 | README documents custom-guest-in-hydrate workflow (upload→validate→generate→export) | grep "Custom Guest" README.md; visual read |
| DOCS-02 ext | GUI guide covers 10 lattice types, custom guest upload, mixed occupancy, depol | grep c0te/sTprime/--depol in gui-guide.md |
| DOCS-02 in-app | help_dialog restructured (TOC/indexed) + v4.7 content + test passes | `QT_QPA_PLATFORM=offscreen pytest tests/test_help_dialog.py`; assert toc.count()==11 |
| DOCS-03 | CLI ref documents --lattice-type (10), --cage-guest, --depol; marks deprecated | grep checks #4/#5/#6 above |
| DOCS-04 | ITP requirements: comb-rule=2, ≤3-char resname, _H suffix | grep checks #7 above |

**Headless GUI test (B3):** `QT_QPA_PLATFORM=offscreen pytest tests/test_help_dialog.py -v`. help_dialog.py has NO VTK imports, so it is safe to run headless (no VTK crash risk per AGENTS.md TEST-06 caveat). Assert: dialog constructs, `toc.count() == pages.count() == 11`, no "v4.5" string in any page text, all 10 lattice keys present in the Extended Lattices page.

---

## 8. Common Pitfalls (what to avoid)

*(Full detail in the "Common Pitfalls" section below; summary here for the planner.)*

1. **Flag-name hallucination (CRITICAL):** Do NOT document `--custom-guest`, `--custom-guest-itp`, `--guest-small`, `--guest-large`, `--hydrate-lattice` — none exist. Real flags: `--lattice-type`, `--cage-guest`, `--depol`. Custom-guest-in-hydrate is GUI-only.
2. **Version-string inconsistency:** Docs say v4.7 but `--version` says 4.5.0. Bump `__version__` (D1) or document the discrepancy.
3. **Stale "only pure water" / 3-lattice lists:** Remove the "Only pure water ice systems supported" lie (README:296); expand all 3-lattice lists to 10.
4. **DOCS-04 inaccuracy:** Be EXACT — "comb-rule=2" (not "AMBER-compatible"), "≤3 chars" (not "short"), "`_H` suffix" (not "renamed"). Source from types.py:591-615 + tests.
5. **Help dialog OK button / scroll:** Keep `QDialogButtonBox` in the OUTER layout, outside the QStackedWidget.
6. **Headless test crash:** Use `QT_QPA_PLATFORM=offscreen` (help_dialog has no VTK — safe).
7. **`rg` not installed:** Use `grep` or the Grep tool for verification sweeps.
8. **Atomic commits:** Stage only intended files with `git add <path>` (AGENTS.md); never `git add .`.

---

## Standard Stack

This is a documentation phase. The "stack" is the documentation toolchain + the PySide6 widgets used in the help dialog restructure. No new libraries are needed — everything is already installed in the `quickice` conda env (PySide6 6.10.2 confirmed by direct import).

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PySide6 | 6.10.2 | GUI framework (help_dialog.py restructure) | Already the project GUI framework; confirmed installed & importable |
| Python | 3.x (conda env) | Doc source files are Markdown; restructure is .py | Project runtime |

### Supporting (verification only)
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `grep`/`rg` (if available) | Sweep outdated version strings | Final verification plan. NOTE: `rg` is NOT installed in this env — use `grep` or the Grep tool |
| `QT_QPA_PLATFORM=offscreen` | Headless GUI test for help dialog | help_dialog smoke test (AGENTS.md constraint) |
| `pytest` | Run any new help_dialog test | Default discovery; no pytest.ini needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| QStackedWidget + QListWidget (TOC) for help dialog | QTabWidget | QTabWidget tabs get cramped at 450-600px wide with 10-12 sections; QStackedWidget+TOC scales better (see §4) |
| QStackedWidget + QListWidget (TOC) | QSplitter | QSplitter adds resizable-divider complexity for no benefit in a small modal dialog |

**Installation:**
```bash
# No installation needed. All deps already in the quickice conda env.
# If a function fails to import, check env before calling python (AGENTS.md).
```

## Architecture Patterns

### Recommended Project Structure (doc file ownership — unchanged)
```
README.md                         # Top-level overview (DOCS-01 + version sweep)
docs/
├── gui-guide.md                  # GUI guide (DOCS-02 external)
├── cli-reference.md              # CLI reference (DOCS-03)
├── gro-itp-guide.md              # GRO/ITP guide (DOCS-04)
├── flowchart.md                  # (no v4.5 refs — NOT in scope)
├── principles.md                 # (no v4.5 refs — NOT in scope)
└── ranking.md                    # (no v4.5 refs — NOT in scope)
quickice/gui/
└── help_dialog.py               # In-app help (DOCS-02 in-app restructure)
quickice/gui/
├── hydrate_panel.py              # Tooltip audit (per-cage widgets lack tooltips)
├── interface_panel.py            # (tooltips already present — verify only)
├── custom_molecule_panel.py      # (tooltips already present — verify only)
├── solute_panel.py               # (tooltips already present — verify only)
└── ion_panel.py                  # (tooltips already present — verify only)
```

### Pattern 1: QStackedWidget + QListWidget TOC (RECOMMENDED for help_dialog restructure)
**What:** Replace the single `QScrollArea`+`QVBoxLayout` with a horizontal split: a `QListWidget` (section list / table of contents) on the left, a `QStackedWidget` on the right holding one page per section. Selecting a list row switches the stacked widget page.
**When to use:** Modal help dialog with 10-12 sections at 450-600px wide — exactly this use case. Tabs would be cramped; a single scroll box has outgrown its content (per the phase objective).
**Why over QTabWidget:** With ~11 sections (Introduction, Shortcuts, Workflow-Tabs-0-5 as one page or per-tab, Dimension Relationships, Best Practices, Custom Molecule Prep, Custom Guest in Hydrate [NEW], Mixed Occupancy [NEW], Depol [NEW], Extended Lattices [NEW], More Info, Important Notes), QTabWidget would need ≥11 tabs across ~450px ≈ 40px/tab — labels truncate. QListWidget rows wrap naturally and scale to any count.
**Example (verified against installed PySide6 6.10.2 — all methods confirmed present):**
```python
# Source: verified by direct import of PySide6 6.10.2 in the quickice env
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget, QLabel, QWidget
)
from PySide6.QtCore import Qt

class QuickReferenceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Reference - QuickIce")
        self.setMinimumWidth(600)      # wider to fit TOC + content
        self.setMaximumWidth(800)
        self.setMinimumHeight(450)
        self.setMaximumHeight(700)

        outer = QVBoxLayout(self)
        body = QHBoxLayout()

        # --- TOC (left) ---
        self.toc = QListWidget()
        self.toc.setFixedWidth(160)     # fixed nav column
        self.toc.currentRowChanged.connect(self._on_section_changed)

        # --- Pages (right) ---
        self.pages = QStackedWidget()

        # Helper to add a section
        def add_section(title, content_widget):
            item = QListWidgetItem(title)
            self.toc.addItem(item)
            page = self.pages.addWidget(content_widget)

        # Build sections...
        add_section("Introduction", self._build_intro_page())
        add_section("Keyboard Shortcuts", self._build_shortcuts_page())
        add_section("Hydrate Generation (v4.7)", self._build_hydrate_page())
        # ... etc

        body.addWidget(self.toc)
        body.addWidget(self.pages, 1)   # pages stretch
        outer.addLayout(body)

        # OK button OUTSIDE the stacked widget (always visible)
        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.accepted.connect(self.accept)
        outer.addWidget(btns)

        self.toc.setCurrentRow(0)       # show first section on open

    def _on_section_changed(self, row):
        self.pages.setCurrentIndex(row)

    def _build_hydrate_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel(
            "<b>Hydrate Generation (Tab 1) — v4.7</b><br><br>"
            "<b>10 lattice types:</b> sI, sII, sH, c0te, c1te, c2te, "
            "ice1hte (filled ices), sTprime, 17 (water-only), 16 (Ice XVI).<br>"
            "<b>Custom guest upload:</b> Upload .gro + .itp (GUI only). "
            "comb-rule=2 mandatory; residue name ≤3 chars (_H suffix → ≤5 chars).<br>"
            "<b>Mixed occupancy:</b> Per-cage-type guest + occupancy rows.<br>"
            "<b>Depol mode:</b> Strict (ice rules) or Optimal (relaxed)."
        )
        label.setWordWrap(True)
        label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        layout.addWidget(label)
        layout.addStretch()
        return page
```

### Pattern 2: HelpIcon tooltip mechanism (existing — for tooltip audit)
**What:** `quickice/gui/view.py:638` defines `HelpIcon(QLabel)` — a "?" badge that calls `setToolTip()` and `QToolTip.showText()` on `enterEvent`. Panels add `HelpIcon("text")` next to a control, OR call `widget.setToolTip("text")` directly.
**When to use:** Adding tooltips to the per-cage guest combos + occupancy spins in hydrate_panel.py (they currently lack BOTH — see §5).
**Example:**
```python
# Source: quickice/gui/view.py:638-680 (existing pattern used across all panels)
from quickice.gui.view import HelpIcon
row.addWidget(HelpIcon(
    "Guest molecule for this cage type. Built-in CH4/THF or a uploaded "
    "custom guest. Built-in CH4/THF only on CLI for v4.7."
))
```

### Anti-Patterns to Avoid
- **Documenting non-existent CLI flags:** The objective names `--custom-guest`, `--custom-guest-itp`, `--guest-small`, `--guest-large`, `--hydrate-lattice`. NONE exist. Use the real names: `--lattice-type`, `--cage-guest`, `--depol`. Stating custom-guest-in-hydrate has CLI flags would be factually wrong.
- **Hardcoding lattice counts:** Don't write "3 lattice types" or "8 ice polymorphs" without checking types.py. Hydrate = 10 lattices; ice = 8 generatable / 12 detectable. Always source from `HYDRATE_LATTICES` (types.py:84-199).
- **Single scrolling textbox for 11+ sections:** The current help_dialog.py QScrollArea is the anti-pattern being fixed. Don't "fix" it by adding more sections to the same scroll box — restructure to QStackedWidget+TOC.
- **Bare `except Exception` in any new test code:** AGENTS.md forbids it in core pipeline; prefer specific exceptions in test helpers too.
- **`git add .` / `git add -A`:** AGENTS.md mandates atomic commits with explicit file paths.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Help dialog navigation | Custom button-bar + show/hide widgets | `QStackedWidget` + `QListWidget.currentRowChanged` | Built-in, handles focus/keyboard nav, tested by Qt |
| Tooltip display | Custom hover popup | `HelpIcon` (view.py:638) / `setToolTip` | Already used across all 5 panels; consistent UX |
| Section content layout | Manual text concatenation | One `QLabel` per page with `setWordWrap(True)` + `setTextInteractionFlags(SelectableByMouse\|SelectableByKeyboard)` | Matches current help_dialog copy-paste-friendly pattern |
| CLI flag list | Re-derive from memory | Read `quickice/cli/parser.py` `add_argument` calls | The parser is the source of truth; 3 flags are deprecated and must be marked as such |

**Key insight:** The help_dialog restructure is the ONLY new "code" in this phase. Keep it a pure UI skeleton swap — migrate existing QLabel content verbatim into per-section pages, then add v4.7 pages. Do not refactor the content text in the same plan as the skeleton swap (split them: skeleton plan first, content plan second).

## Common Pitfalls

### Pitfall 1: Flag-name hallucination (CRITICAL)
**What goes wrong:** The phase objective lists `--custom-guest`, `--custom-guest-itp`, `--guest-small`, `--guest-large`, `--hydrate-lattice`. A planner/executor trusting the objective would document flags that don't exist.
**Why it happens:** The objective's flag names are approximate/wrong. `--custom-gro`/`--custom-itp` exist but are for Tab-3 LIQUID custom molecules (require `--interface`), NOT hydrate cage guests. `--cage-occupancy-small/large` exist but are deprecated. `--cage-guest` is the real mixed-occupancy flag.
**How to avoid:** Source ALL flag docs from `quickice/cli/parser.py` (lines 199-280). The real v4.7-new hydrate flags are: `--lattice-type` (extended to 10 choices), `--cage-guest` (new), `--depol` (new). Mark `--guest`, `--cage-occupancy-small`, `--cage-occupancy-large` as DEPRECATED. Explicitly state custom-guest-in-hydrate is GUI-only (no CLI flag).
**Warning signs:** Any doc text mentioning `--custom-guest`, `--hydrate-lattice`, `--guest-small`, or `--guest-large` is wrong.

### Pitfall 2: Version-string inconsistency
**What goes wrong:** Docs say "v4.7" but `python -m quickice --version` outputs `4.5.0` (quickice/__init__.py:3 `__version__ = "4.5.0"`; parser.py:386 `version="%(prog)s 4.5.0"`).
**Why it happens:** The version string was never bumped during v4.7 development.
**How to avoid:** Include a tiny code-change plan to bump `__version__` to `"4.7.0"` and parser.py version to `"%(prog)s 4.7.0"`. OR, if the user wants zero code changes, document the version as "v4.7 (milestone); --version reports 4.5.0 pending version bump" — but this is awkward. RECOMMEND the bump (2-line code change, clearly in the spirit of "document the v4.7 release"). Ask the user if unsure.
**Warning signs:** `grep -rn "4\.5\.0" quickice/__init__.py quickice/cli/parser.py` returns matches after this phase.

### Pitfall 3: Stale "only pure water" / wrong lattice counts
**What goes wrong:** README.md:296 says "Only pure water ice systems supported" — this is now FALSE (hydrate + filled-ice + custom guest systems shipped). README/gui-guide say "sI, sII, sH" (3 lattices) — now 10.
**Why it happens:** Docs predate v4.7 features.
**How to avoid:** Sweep README.md Known Issues, gui-guide.md Lattice Types table, help_dialog.py hydrate workflow text. Replace 3-lattice lists with the full 10. Remove the "only pure water" limitation line.
**Warning signs:** `grep -rn "sI, sII, sH" README.md docs/ quickice/gui/help_dialog.py` returns matches lacking the other 7 types.

### Pitfall 4: Comb-rule / residue-name inaccuracy in DOCS-04
**What goes wrong:** Vague "use compatible force field" instead of the precise rules: comb-rule=2 MANDATORY (rejected if comb-rule=1 via `parse_itp_defaults_comb_rule`); residue base name ≤3 chars (so `_H` suffix yields ≤5 chars for GRO fixed-width); `_H` suffix applied by `transform_guest_itp` Step 3 (rewrites `[ atoms ]` resname to `{name}_H`); `[ atomtypes ]` is commented out + merged into main `.top`.
**Why it happens:** These are engine-internal details not obvious from the GUI.
**How to avoid:** Source DOCS-04 from `types.py:591-615` (HydrateConfig custom-guest validation), `itp_parser.py:163` (`parse_itp_defaults_comb_rule`), `moleculetype_registry.py:47` (`_H` suffix), `cli/itp_helpers.py:170` (`transform_guest_itp`), tests `test_gro_resname_validation.py` and `test_custom_guest_bridge.py:165-175`. Be exact: "≤3 chars" not "short"; "comb-rule=2" not "AMBER-compatible".
**Warning signs:** DOCS-04 text that doesn't mention `comb-rule=2`, `_H` suffix, or the 5-char GRO limit.

### Pitfall 5: Help dialog restructure breaks the OK button / scroll
**What goes wrong:** Putting the OK button inside the QStackedWidget page (disappears when switching pages) or inside a QScrollArea (button scrolls away).
**Why it happens:** Copy-pasting the current structure where the button is at the bottom of the main layout.
**How to avoid:** Keep `QDialogButtonBox` in the OUTER `QVBoxLayout`, AFTER the `QHBoxLayout` that holds TOC+pages (see Pattern 1 — button is outside the stacked widget). Each page handles its own internal scroll if needed.
**Warning signs:** OK button only visible on one page, or content overflow off-dialog.

### Pitfall 6: Headless test crash without offscreen platform
**What goes wrong:** A new help_dialog test crashes with "could not connect to display" on a remote/headless machine.
**Why it happens:** PySide6 needs a display; this env is remote.
**How to avoid:** Set `QT_QPA_PLATFORM=offscreen` (AGENTS.md). The test should construct `QuickReferenceDialog()` and assert `toc.count() == N` and `pages.count() == N` without `show()`/`exec()` if possible, or under offscreen. Mock/skip VTK-dependent paths (help_dialog has no VTK, so it's safe).
**Warning signs:** Test segfaults or errors with "Display" / "xcb" in the message.

## Code Examples

### CLI hydrate flags — the AUTHORITATIVE list (from parser.py:199-280)
```python
# Source: quickice/cli/parser.py (read in full; this is the ground truth)
# --- v4.7 NEW flags ---
"--lattice-type"   choices=["sI","sII","sH","c0te","c1te","c2te","ice1hte","sTprime","16","17"]  default="sI"
"--cage-guest"     action="append"  metavar="KEY=GUEST:OCC"   # repeatable; KEY ∈ cage_type_map keys (small/medium/large/guest)
"--depol"          choices=["strict","optimal"]  default="strict"

# --- DEPRECATED (kept for backward compat; help text already says so) ---
"--guest"                    choices=["CH4","THF"]  default="CH4"   # "(deprecated; use --cage-guest for mixed occupancy)"
"--cage-occupancy-small"     float  default=100.0                  # "(deprecated; use --cage-guest for mixed occupancy)"
"--cage-occupancy-large"     float  default=100.0                  # "(deprecated; use --cage-guest for mixed occupancy)"

# --- UNCHANGED ---
"--hydrate"  "--supercell-x/y/z"
```

### The 10 HYDRATE_LATTICES (from types.py:84-199) — for lattice-types table
```
| Key       | GenIce2 name | Description                    | Cage type_map                  | Triclinic | Water-only |
|-----------|--------------|--------------------------------|--------------------------------|----------|------------|
| sI        | CS1          | Structure I hydrate            | {small:"12", large:"14"}       | No       | No         |
| sII       | CS2          | Structure II hydrate           | {small:"12", large:"16"}       | No       | No         |
| sH        | sH           | Structure H hydrate             | {small:"12", medium:"12_1", large:"20"} | YES | No |
| c0te      | c0te         | Filled ice C0 (Teeratchanan 2015) | {small:"Ne1"}               | YES      | No         |
| c1te      | c1te         | Filled ice C1 (Teeratchanan 2015) | {small:"Ne1"}               | YES      | No         |
| c2te      | c2te         | Filled ice C2 (Teeratchanan 2015) | {small:"Ne1"}               | No       | No         |
| ice1hte   | ice1hte      | Filled ice Ih (Teeratchanan 2015) | {small:"Ne1"}               | No       | No         |
| sTprime   | sTprime      | Filled ice sT′ (Smirnov 2013)   | {} (no cages)                  | No       | YES        |
| 16        | 16           | Ice XVI (empty sII framework)  | {small:"12", large:"16"}       | No       | No         |
| 17        | 17           | Ice XVII (ultralow density)    | {} (no cages)                  | No       | YES        |
```
NOTE: `c0te`/`c1te` are TRICLINIC and BLOCKED in interface generation (interface_builder). `sTprime`/`17` are water-only (no guests; UI hides guest/occupancy rows). Filled ices have a SINGLE cage_type_map key `"small"` (mapped to GenIce2 cage id `"Ne1"`) — NOT `"guest"` despite the `cages` display dict using `"guest"` as the key. This distinction is a known gotcha (see test_e2e_mixed_filled_ice_gui.py) — `--cage-guest small=CH4:100` is correct; `--cage-guest guest=CH4:100` produces 0 guests.

### Custom guest ITP requirements (DOCS-04) — from types.py:591-615 + itp_parser.py
```
1. comb-rule = 2 (Lorentz-Berthelot / AMBER-GAFF2). REJECTED if comb-rule=1.
   parse_itp_defaults_comb_rule() reads [ defaults ]; if it returns 1, upload fails
   with "comb-rule must be 2 ... got comb-rule=1". Absent [ defaults ] is OK
   (the main .top supplies comb-rule=2).
2. Residue base name ≤ 3 chars (GRO fixed-width columns 6-10 = 5 chars max).
   validate_gro_residue_name() enforces this. "_H" suffix is appended → "{base}_H".
   e.g. MOL (3) → MOL_H (5) OK; ETHAN (5) → ETHAN_H (7) REJECTED.
3. _H suffix convention: hydrate cage guests use "_H"; liquid solutes use "_L".
   transform_guest_itp() Step 3 rewrites [ atoms ] resname "{base}" → "{base}_H".
   MoleculetypeRegistry (moleculetype_registry.py:47) produces the registered name.
4. [ atomtypes ] in the uploaded .itp is COMMENTED OUT and merged into the main .top
   via _merge_custom_atomtypes (prevents duplicate-atomtype conflicts).
5. Required HydrateConfig fields for custom guest: guest_residue_name, guest_atom_labels,
   guest_atom_count, guest_gro_path (guest_itp_path). Built-in ch4/thf auto-populate
   from GUEST_MOLECULES; custom guests REQUIRE explicit metadata (no auto-populate).
```

## State of the Art

| Old Approach (v4.5 docs) | Current Approach (v4.7 docs) | When Changed | Impact |
|--------------------------|------------------------------|--------------|--------|
| 3 hydrate lattices (sI/sII/sH) | 10 lattices (incl. filled ices C0/C1/C2/Ih, water-only sT′/17, Ice XVI) | Phase 39 (v4.7) | Lattice-types tables must list 10 rows with triclinic/water-only flags |
| CH4/THF built-in guests only | Built-in + custom guest upload (GUI) | Phase 40/44 (v4.7) | GUI guide + gro-itp-guide need custom-guest-ITP section |
| Single guest + small/large occupancy | Per-cage-type mixed occupancy (`--cage-guest`) | Phase 42 (v4.7) | CLI ref needs `--cage-guest`; GUI guide needs mixed-occupancy section; `--cage-occupancy-small/large` deprecated |
| No depol control | `--depol strict|optimal` | Phase 43 (v4.7) | CLI ref + GUI guide need depol section |
| `--guest` as primary | `--guest` DEPRECATED; `--cage-guest` primary | Phase 42 (v4.7) | CLI ref must mark `--guest` deprecated |
| help_dialog single QScrollArea | QStackedWidget + QListWidget TOC | Phase 48 (this phase) | help_dialog.py restructure |
| `--version` → 4.5.0 | `--version` → 4.7.0 (recommended bump) | Phase 48 (this phase) | 2-line code change in __init__.py + parser.py |

**Deprecated/outdated (must be marked in docs, NOT removed — backward compat):**
- `--guest`: use `--cage-guest` for mixed occupancy (kept as deprecated alias)
- `--cage-occupancy-small` / `--cage-occupancy-large`: use `--cage-guest` (kept as deprecated; `HydrateConfig.__post_init__` synthesizes `cage_guest_assignments` from them when `--cage-guest` absent — NO behavior change)

## Open Questions

1. **Version-string bump — in scope?**
   - What we know: `__version__ = "4.5.0"` (quickice/__init__.py:3) and parser.py:386 `version="%(prog)s 4.5.0"`. Docs will say v4.7; `--version` says 4.5.0 — inconsistent.
   - What's unclear: Is a 2-line version bump "documentation" or "code"? The phase is billed as "no new production code except help_dialog.py restructure."
   - Recommendation: Include a tiny dedicated plan to bump to "4.7.0" (2 lines). It's the cleanest fix and makes docs truthful. If the user prefers zero code changes, document the discrepancy explicitly. LOW risk either way.

2. **README_bin.md — in scope?**
   - What we know: README_bin.md references `quickice-v4.5.0-linux-x86_64.tar.gz` download links (lines 44/46/56). It's a binary-distribution doc, not a feature doc.
   - What's unclear: Whether binary release artifacts for v4.7 exist yet (they likely don't — this is the docs phase, not a release).
   - Recommendation: Sweep the version STRING in README_bin.md to v4.7.0 for consistency, but do NOT fabricate download URLs (AGENTS.md: never make up references). Leave actual asset links as-is or mark "pending release". Flag to user.

3. **flowchart.md / principles.md / ranking.md — confirmed out of scope?**
   - What we know: `grep` found ZERO "v4.5" references in these 3 files. They don't document hydrate features.
   - What's unclear: Nothing — they're out of scope.
   - Recommendation: Do NOT touch them. Saves plan budget.

## Sources

### Primary (HIGH confidence)
- **quickice/cli/parser.py** (read in full, 561 lines) — authoritative CLI flag list, choices, help text, deprecation notes
- **quickice/structure_generation/types.py:84-199** — HYDRATE_LATTICES (all 10 entries with cage_type_map/is_triclinic/is_water_only)
- **quickice/structure_generation/types.py:502-660** — HydrateConfig dataclass (custom-guest field requirements, depol_mode validation, cage_guest_assignments shim)
- **quickice/cli/pipeline.py:300-363** — CLI HydrateConfig construction (confirms custom-guest fields NOT set from CLI args → GUI-only)
- **quickice/gui/help_dialog.py** (read in full, 258 lines) — current single-QScrollArea structure
- **quickice/gui/hydrate_panel.py:235-526** — custom guest upload group, depol group, per-cage rows (confirms NO tooltips on cage combos/spins)
- **quickice/gui/view.py:638-680** — HelpIcon class (existing tooltip mechanism)
- **quickice/structure_generation/itp_parser.py:163** — parse_itp_defaults_comb_rule (comb-rule=2 enforcement)
- **.planning/STATE.md** lines 183, 205 — confirms "custom-guest CLI deferred" and the official 48-01/48-02 split
- **PySide6 6.10.2** — direct import verification of QStackedWidget/QListWidget/QTabWidget API (all methods confirmed present)
- **README.md, docs/gui-guide.md, docs/cli-reference.md, docs/gro-itp-guide.md** — read in full (current doc state audit)

### Secondary (MEDIUM confidence)
- **tests/test_gro_resname_validation.py, tests/test_custom_guest_bridge.py, tests/test_itp_parser_combrule.py** — confirm the exact validation rules (≤3 chars, comb-rule=2 rejection, _H suffix) for DOCS-04
- **tests/test_hydrate_panel.py** — confirms comb-rule=1 → "comb-rule must be 2" error, 5-char residue → "exceeds 3 chars" error
- **README_bin.md** — confirmed v4.5.0 download-link references

### Tertiary (LOW confidence)
- None. All findings sourced from the codebase itself (the ground truth for a documentation phase).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — PySide6 6.10.2 directly verified; no new deps
- Architecture (help dialog restructure): HIGH — QStackedWidget+QListWidget API verified against installed version; pattern is idiomatic Qt
- CLI flags inventory: HIGH — read parser.py in full; cross-checked with pipeline.py + STATE.md
- Custom-guest-is-GUI-only: HIGH — pipeline.py:332-342 never sets custom-guest fields; STATE.md line 183 explicitly states deferred
- Doc state audit: HIGH — read all 5 files in full
- Tooltip audit: HIGH — grep + read of hydrate_panel.py:454-526 confirms cage combos/spins lack setToolTip/HelpIcon
- Pitfalls: HIGH — all sourced from codebase
- Version-string bump question: MEDIUM — recommendation is judgment call; flagged to user

**Research date:** 2026-07-12
**Valid until:** 2026-08-11 (30 days — stable; docs phase, no fast-moving deps. Re-verify the 10-lattice list if Phase 48 is delayed beyond v4.7 freeze.)
