# v4.7 UAT Issues Found

**Date:** 2026-08-04 (updated 2026-08-05)
**Source:** UAT Workflow F (GUI interactive testing)
**Status:** 2 issues found, 1 resolved, 1 open

---

## Issue 1: Long residue name silently ignored (RESOLVED)

**UAT tests affected:** 40-UAT #2, 44-UAT #2
**Severity:** major
**Status:** ✅ RESOLVED (commit 0baf0043)

### What happened

Uploaded `etoh_long_name.itp` (residue name "ETHANOL", 6 chars) as a custom guest in the Hydrate tab. Expected: QuickIce rejects it with a specific error about residue name >3 chars / GRO 5-char limit.

Actual: No validation error shown. Generation proceeded. Export produced a structure as if no custom guest was uploaded — fell back to built-in CH4 only.

### Fix

Commit 0baf0043 — reject ITP [atoms] resname mismatch with GRO in custom guest validation. User confirmed F-5 now correctly blocked.

---

## Issue 2: Duplicate `#include "etoh.itp"` → grompp "moleculetype etoh redefined" (RESOLVED)

**UAT tests affected:** 44.1-UAT #3 (Custom/Solute/Ion tabs)
**Severity:** major
**Status:** ✅ RESOLVED (commit 520ad042)

### What happened

Generated a custom guest hydrate (ethanol in cages) → Interface tab → then inserted a custom molecule (also ethanol) via the Custom tab → Solute tab → Ion tab. Exported from each tab. The Interface tab export passes grompp. The Custom/Solute/Ion tab exports all fail grompp with `moleculetype etoh is redefined`.

### Root cause

The cage-guest `etoh.itp` (transformed to moleculetype `MOL_H`) and the custom-molecule `etoh.itp` (moleculetype `etoh`) share the same basename. Both staged to same file in output dir. Duplicate `#include` in .top causes grompp redefinition error.

### Fix

Commit 520ad042 — rename custom molecule ITP on basename collision to avoid duplicate #include (mirrors CLI cmet.itp pattern). User confirmed F-15 now passes grompp.

---

## Issue 3: .top molecule count mismatch with .gro for sII custom guest (OPEN)

**UAT tests affected:** F-15 (full tab chain, sII variant), F-16, F-18
**Severity:** major
**Status:** ❌ OPEN

### What happened

Generated a sII 3×3 hydrate with custom ethanol guest (MOL_H) in cages → Interface (slab) → Custom molecule (etoh) → Solute (CH4) → Ion (NaCl). Exported from Ion tab. gmx grompp fails:

```
Fatal error:
number of coordinates in coordinate file (ions_23na_23cl_with_24ch4.gro, 34813)
             does not match topology (ions_23na_23cl_with_24ch4.top, 37405)
```

### Evidence

Export files in `tmp/SII-ch4-mol_slab_etohL_ch4L_ion/`:

| Source | MOL_H count | Total atoms |
|--------|-------------|-------------|
| `.top [molecules]` | 864 | 37,405 |
| `.gro` (actual) | 576 | 34,813 |
| **Difference** | **288 mols** | **2,592 atoms** |

Full breakdown:

| Molecule | .top count | .gro atoms | .gro mols | Match? |
|----------|-----------|------------|-----------|--------|
| SOL | 7305 | 29,220 | 7,305 | ✅ |
| MOL_H | 864 | 5,184 | 576 | ❌ |
| etoh (custom) | 27 | 243 | 27 | ✅ |
| CH4_L (solute) | 24 | 120 | 24 | ✅ |
| NA | 23 | 23 | 23 | ✅ |
| CL | 23 | 23 | 23 | ✅ |
| **Total** | | **34,813** | | **.top expects 37,405** |

### Lattice confirmation

- Box XY = 5.13629 nm, sII `a` = 1.713 nm → 5.13629 / 1.713 = 3.00 → **sII 3×3**
- sII 3×3×3 = 27 unit cells, 32 cages/cell = 864 total cages
- `.top` MOL_H = 864 = all cages at 100% occupancy
- `.gro` MOL_H = 576 = actual generated count (576 = 864 × 2/3)

### Root cause (preliminary)

The `.top` [molecules] MOL_H count (864) appears to be derived from the **config** (expected cage count = 32 × 27 = 864 at 100% occupancy), not from the **actual structure** (576 molecules in the .gro). This is the same class of bug as the 42-08 "config/structure desync" issue, but for the sII lattice with custom guest.

Possible causes:
1. The .top writer uses `config.cage_guest_assignments` to compute the molecule count instead of `structure.molecule_index` or `structure.guest_count`
2. GenIce2 sII 3×3 generates fewer cages than expected (576 instead of 864) — the structure is correct, but the .top count is wrong
3. The slab assembly may drop some cages (slab mode cuts the hydrate, removing some cage positions) — the .gro is correct (only cages in the slab), but the .top still reports the full hydrate count

### Hypothesis: slab mode cage loss

The export is from a **slab** interface structure (box z = 10.57382, elongated). Slab mode assembles ice + water layers, which may truncate the hydrate and remove some cages. If 288 cages were lost during slab assembly (864 → 576), the .gro is correct but the .top count wasn't updated to reflect the slab-truncated structure.

### Expected fix

The .top [molecules] count for MOL_H should be derived from the actual structure's molecule_index or guest_count, not from the config's expected cage count. This mirrors the 42-08 fix pattern (structure-driven ITP staging, not config-driven).

### Files to investigate

- `quickice/output/ion_writer.py` — `write_ion_top_file` [molecules] MOL_H count source
- `quickice/output/solute_writer.py` — `write_solute_top_file` (same pattern)
- `quickice/output/custom_writer.py` — `write_custom_molecule_top_file` (same pattern)
- `quickice/output/interface_writer.py` — `write_interface_top_file` (check if Interface tab also affected)
- `quickice/output/multi_molecule_writer.py` — `write_multi_molecule_top_file` (hydrate-only export, check if affected)
- `quickice/structure_generation/types.py` — `HydrateStructure.guest_count` vs config cage count
- `quickice/structure_generation/modes/slab.py` — slab assembly cage truncation

### Test data

- Export dir: `tmp/SII-ch4-mol_slab_etohL_ch4L_ion/`
- .top: `ions_23na_23cl_with_24ch4.top` (MOL_H = 864)
- .gro: `ions_23na_23cl_with_24ch4.gro` (MOL_H = 576, 34,813 atoms)
- grompp error: "number of coordinates (34813) does not match topology (37405)"

### Note on other lattices

This issue may affect all lattices when exported through slab mode with custom guests — the slab truncation reduces cage count but the .top count reflects the full hydrate. Built-in guests (CH4/THF) may not show this because their count is derived differently (via `count_guest_atoms` heuristic or `detect_guest_type_from_atoms`).

---

## UAT Workflow Status

### Completed workflows

| Workflow | Type | Result |
|----------|------|--------|
| A | Script | ✅ 7/7 pass |
| B | Script | ✅ 7/7 pass |
| C | Script | ✅ 9/9 pass |
| D | Script | ✅ 28/28 pass |
| E | Script | ✅ 12 pass, 1 skip |
| G | Script | ✅ 6/6 pass |
| H | Interactive | ✅ 5/5 pass |
| F | Interactive | ⚠️ Partially complete |

### Workflow F progress

| Step | Test | Result | Notes |
|------|------|--------|-------|
| 1 | Lattice dropdown (39-1, 44-1) | ✅ pass | All 10 types, no crash |
| 2 | Water-only lattices (39-4) | ✅ pass | sTprime/17 disables guest controls |
| 3 | Depol dropdown (43-1, 44-4) | ✅ pass | strict/optimal, default strict |
| 4 | Custom guest upload + generate (40-1) | ✅ pass | etoh.gro+etoh.itp → MOL_H in export |
| 5 | Long name validation (40-2, 44-2) | ✅ pass | Fixed (0baf0043), now blocked |
| 6 | Wrong comb-rule validation (40-3) | ✅ pass | Correctly rejected |
| 7 | Per-cage guest assignment (42-1) | ✅ pass | CH4 small + THF large |
| 8 | Per-cage occupancy % (42-2) | ✅ pass | 60% small + 100% large, counts match |
| 9 | Lattice change rebuilds rows (44-3) | ✅ pass | sI→sH→c0te→sTprime row rebuild |
| 10 | Mixed hydrate VTK colors (42-4) | ✅ pass | Gray only (accepted, distinct colors deferred) |
| 11 | Single-guest VTK (42-4) | ✅ pass | Keeps legacy gray |
| 12 | Custom guest VTK (46) | ✅ pass | Gray (accepted, same as 10) |
| 13 | Same guest in 2 cages (44.1-1) | ✅ pass | Allowed, Pitfall 6 relaxation works |
| 14 | Interface tab flow + grompp (44.1-2) | ✅ pass | gmx grompp rc=0 |
| 15 | Full tab chain + grompp (44.1-3) | ❌ issue | **Issue 3** — sII .top/gro MOL_H count mismatch |
| 16 | New lattices full tab chain (45-2) | ⏳ deferred | Likely affected by Issue 3 |
| 17 | Triclinic hydrate-only 4×4×4 (45-5) | ⏳ deferred | May pass (no custom molecule, no slab) |
| 18 | Custom ethanol + non-sI (45-6) | ⏳ deferred | Likely affected by Issue 3 |

### Summary

- **15/18 steps completed** (14 pass, 1 issue)
- **3 steps deferred** (16-18) — pending Issue 3 resolution
- **3 issues total** (2 resolved, 1 open)
- **0 blockers** (workarounds: use hydrate-only export without slab, or use CLI)

### Steps to re-test after fix

1. **After Issue 3 fix:** Re-run F step 15 — sII full tab chain export, expect .top MOL_H count = .gro count, gmx grompp rc=0
2. **After Issue 3 fix:** Re-run F steps 16-18 — complete remaining GUI tests

### Test data for re-test

- F step 15: sII 3×3 hydrate with custom ethanol → slab → custom → solute → ion. Compare .top [molecules] MOL_H count vs .gro MOL_H atom count / 9.
- F step 17: c0te or c1te at 4×4×4, hydrate-only export (no slab, no custom molecule) — may not be affected by Issue 3.
