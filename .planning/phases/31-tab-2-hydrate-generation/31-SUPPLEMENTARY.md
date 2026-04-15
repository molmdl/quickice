# Phase 31 Supplementary Context — User Corrections

**Created:** 2026-04-15
**Status:** Awaiting gap-filling plan

---

## User Corrections

### 1. Force Field Sources (User-Provided)

| File | Source | Status |
|------|--------|--------|
| `quickice/data/tip4p-ice.itp` | User-provided | ✓ Existing |
| `quickice/output/gromacs_writer.py` | User-provided (slightly different topology writer) | ⚠️ May need review |

**Note:** User has a "slightly different topology writer" that differs from what was generated. May need to reconcile.

### 2. Ion Parameters (Madrid2019)

| Item | Value | Notes |
|------|-------|-------|
| Force field | **Madrid2019** | Standard (non-polarizable) |
| Charge | **~0.85e** | Reduced charge |
| User will provide | Example topology file | To extract Na/Cl parameters |

**Action needed:**
- User provides Madrid2019 example topology
- Executor extracts Na/Cl atom types, masses, charges, VDW params
- Update `gromacs_ion_export.py`

### 3. Guest Molecule Parameters (GAFF/GAFF2)

| Guest | Force field | Status |
|-------|-------------|--------|
| CH4 | GAFF | User will provide ch4.itp |
| THF | GAFF | User will provide thf.itp |

**Note:** GAFF chosen for easier custom guest extensibility in future (Phase 32).

### 4. CO2/H2 Removal

**Status:** Not yet removed from code

**Files needing modification:**
- `quickice/structure_generation/types.py` — GUEST_MOLECULES dict
- `quickice/gui/hydrate_panel.py` — guest_combo
- `quickice/structure_generation/hydrate_generator.py` — guest parameter mapping
- `quickice/gui/hydrate_export.py` — _get_guest_itp_path()

---

## Bug Reports

### Bug 1: Error generating hydrate structures

**Symptoms:** Generation fails with error
**Affected:** Phase 31 hydrate generation
**Priority:** High

### Bug 2: Error generating ion insertion

**Symptoms:** Ion insertion fails with error
**Affected:** Phase 30 ion insertion
**Priority:** High

### Bug 3: Tab ordering issues

**Symptoms:** Tabs in wrong order
**Affected:** Main window tab widget
**Current order:** Ice Generation → Interface → Hydrate → Ion (?)
**Expected order:** (User to specify)

**Priority:** Medium-High

---

## Proposed Urgent Phase

### Recommendation: Insert NEW Phase between Phase 28 and Phase 29

**Rationale:**
1. Bugfixes (GUI errors) should be isolated from feature phases
2. FF corrections affect Phase 30-31, not completed phases
3. Phase 28 is explicitly for "pre-requisite fixes" — consistent pattern
4. Bugfixing before Phase 29-31 replanning prevents wasted effort

### Proposed Phase Structure

```
Phase 28: Pre-requisite Fixes (COMPLETED)
    │
    ▼
Phase 28.5: URGENT — Bugfixes + FF Corrections (NEW)
    │
    ▼
Phase 29: Data Structures + Multi-Molecule GROMACS (COMPLETED - needs FF review)
Phase 30: Ion Insertion (needs FF correction)
Phase 31: Hydrate Generation (BLOCKED - needs FF + bugfix)
Phase 32: Custom Molecules + Display Controls (NOT STARTED)
```

### Phase 28.5 Scope

| Category | Items |
|----------|-------|
| **Bugfixes** | Hydrate generation error, Ion insertion error, Tab ordering |
| **FF Corrections** | Replace amberGS with Madrid2019 for ions |
| **Code Cleanup** | Remove CO2/H2 from hydrate UI |
| **Topology Writer** | Review/reconcile with user-provided gromacs_writer.py |

### Affected Files for Phase 28.5

| Category | File | Change |
|----------|------|--------|
| Bugfix | `quickice/gui/main_window.py` | Tab ordering |
| Bugfix | `quickice/gui/hydrate_panel.py` | Generation error |
| Bugfix | `quickice/gui/ion_panel.py` | Insertion error |
| FF | `quickice/structure_generation/gromacs_ion_export.py` | Madrid2019 |
| Cleanup | `quickice/structure_generation/types.py` | Remove CO2/H2 |
| Cleanup | `quickice/gui/hydrate_panel.py` | Remove CO2/H2 |
| Cleanup | `quickice/structure_generation/hydrate_generator.py` | Remove CO2/H2 |
| Cleanup | `quickice/gui/hydrate_export.py` | Remove CO2/H2 |
| Review | `quickice/output/gromacs_writer.py` | Compare with user version |

---

## User Files Pending

| File | Phase | Status |
|------|-------|--------|
| Madrid2019 example topology | 28.5 | ☐ User will provide |
| ch4.itp (GAFF) | 31 | ☐ User will provide |
| thf.itp (GAFF) | 31 | ☐ User will provide |
| tip4p-ice.itp | — | ✓ Already exists |
| gromacs_writer.py | 28.5 | ⚠️ May need reconciliation |

---

## Planner Instructions

1. **Insert Phase 28.5** between Phase 28 and Phase 29
2. **Scope:** Bugfixes + FF corrections + CO2/H2 removal
3. **User will provide:** Madrid2019 example topology before Phase 28.5 execution
4. **After Phase 28.5:** Replan Phase 30-31 for FF + continue Phase 32

