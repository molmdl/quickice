# v4.7 UAT Issues Found

**Date:** 2026-08-04
**Source:** UAT Workflow F (GUI interactive testing)
**Status:** 2 distinct issues found (both major), 1 root cause shared

---

## Issue 1: Long residue name silently ignored (no validation error)

**UAT tests affected:** 40-UAT #2, 44-UAT #2
**Severity:** major

### What happened

Uploaded `etoh_long_name.itp` (residue name "ETHANOL", 6 chars) as a custom guest in the Hydrate tab. Expected: QuickIce rejects it with a specific error about residue name >3 chars / GRO 5-char limit.

Actual: No validation error shown. Generation proceeded. Export produced a structure as if no custom guest was uploaded — fell back to built-in CH4 only.

### Evidence

Export files in `tmp/` (step 5 export):
- `tmp/hydrate_sI_ch4_1x1x1.top` `[molecules]`: SOL 46 + CH4_H 8 (no MOL_H)
- `tmp/hydrate_sI_ch4_1x1x1.top` `#include`: tip4p-ice.itp + ch4_hydrate.itp (no etoh.itp)
- `tmp/hydrate_sI_ch4_1x1x1.gro` residues: SOL + CH4_H (no MOL_H)
- No `etoh.itp` staged in output dir

### Root cause (preliminary)

The GUI custom guest upload validation does not enforce the ≤3 char residue name limit at upload time. When the invalid ITP is silently rejected, the GUI falls back to built-in CH4 without informing the user. The unit tests (test_custom_guest_bridge.py) test the validation function in isolation but the GUI upload path may not call it (or may swallow the error).

### Expected fix

The GUI should call `validate_custom_guest_files()` (or equivalent) at upload time and display the specific error message. If validation fails, the custom guest should NOT be silently ignored — the user must be told why.

### Files to investigate

- `quickice/gui/hydrate_panel.py` — custom guest upload handler
- `quickice/structure_generation/custom_guest_bridge.py` — `validate_custom_guest_files()`
- `quickice/gui/export.py` — where custom guest info is built for export

---

## Issue 2: Duplicate `#include "etoh.itp"` → grompp "moleculetype etoh redefined"

**UAT tests affected:** 44.1-UAT #3 (Custom/Solute/Ion tabs)
**Severity:** major

### What happened

Generated a custom guest hydrate (ethanol in cages) → Interface tab → then inserted a custom molecule (also ethanol) via the Custom tab → Solute tab → Ion tab. Exported from each tab. The Interface tab export passes grompp. The Custom/Solute/Ion tab exports all fail grompp with `moleculetype etoh is redefined`.

### Evidence

Export files (step 15, full tab chain):

| Tab | Directory | grompp result |
|-----|-----------|---------------|
| Interface | `tmp/ch4_custom_slab/` | ✅ rc=0 (1 #include etoh.itp) |
| Custom | `tmp/ch4_custom_slab_customSol/` | ❌ ERROR: etoh redefined (2 #include etoh.itp) |
| Solute | `tmp/ch4_custom_slab_customSol_ch4L/` | ❌ ERROR: etoh redefined (2 #include etoh.itp) |
| Ion | `tmp/ch4_custom_slab_customSol_ch4L_ion/` | ❌ ERROR: etoh redefined (2 #include etoh.itp) |

The .top files contain duplicate `#include "etoh.itp"`:
```
#include "tip4p-ice.itp"
#include "etoh.itp"          ← cage guest (transformed to moleculetype MOL_H)
#include "etoh.itp"          ← custom molecule (moleculetype etoh) — DUPLICATE
#include "ch4_liquid.itp"
```

### Root cause (preliminary)

The cage-guest `etoh.itp` (transformed to moleculetype `MOL_H`) and the custom-molecule `etoh.itp` (moleculetype `etoh`) share the same basename. Both are staged to the same filename in the output directory — the second copy overwrites the first. The .top then has two `#include "etoh.itp"` lines, causing grompp to read the file twice and see `moleculetype etoh` defined twice.

The CLI e2e tests avoid this by using a renamed copy (`cmet.itp`/`cmet.gro`) for the custom molecule when it shares a basename with the cage guest ITP. The GUI export path does not perform this rename.

### Expected fix

When the custom molecule ITP basename collides with the cage-guest ITP basename, the GUI exporter should rename the custom molecule ITP copy (e.g. `cmet.itp` instead of `etoh.itp`) and update the `#include` statement in the .top accordingly. This mirrors the CLI e2e test pattern (`cmet.itp`/`cmet.gro`).

### Files to investigate

- `quickice/gui/export.py` — `CustomMoleculeGROMACSExporter`, `SoluteGROMACSExporter`, `IonGROMACSExporter` (staging + #include logic)
- `quickice/output/custom_writer.py` — `write_custom_molecule_top_file` (#include generation)
- `quickice/output/solute_writer.py` — `write_solute_top_file` (#include generation)
- `quickice/output/ion_writer.py` — `write_ion_top_file` (#include generation)
- `quickice/cli/itp_helpers.py` — `copy_itp_files_for_structure` (CLI staging, for comparison)
- `tests/test_e2e_custom_guest_cli_grompp.py` — `test_custom_guest_cli_custom_molecule_export_grompp` (CLI pattern using cmet.itp rename)

### Note on steps 16-18

Steps 16-18 (new lattices full tab chain, triclinic 4×4×4, custom ethanol + non-sI) were not tested because:
- Step 16 (full tab chain) would hit the same etoh redefinition bug if a custom molecule is also inserted
- Step 18 (custom ethanol + non-sI) would hit the same bug if going through Custom/Solute/Ion tabs
- Step 17 (triclinic hydrate-only 4×4×4) does NOT involve a custom molecule and may pass, but was deferred pending the etoh issue resolution

The etoh redefinition bug affects ALL GUI exports where the same molecule is used as both cage guest AND custom molecule (or solute). It does NOT affect:
- Hydrate-only exports (no Custom/Solute/Ion tabs)
- Interface-only exports (single #include, no collision)
- CLI exports (uses cmet.itp rename pattern)
- Built-in guest exports (ch4_hydrate.itp vs ch4_liquid.itp — different basenames by design)

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
| H | Interactive | ✅ 5/5 pass (user verified) |
| F | Interactive | ⚠️ Partially complete |

### Workflow F progress

| Step | Test | Result | Notes |
|------|------|--------|-------|
| 1 | Lattice dropdown (39-1, 44-1) | ✅ pass | All 10 types, no crash |
| 2 | Water-only lattices (39-4) | ✅ pass | sTprime/17 disables guest controls |
| 3 | Depol dropdown (43-1, 44-4) | ✅ pass | strict/optimal, default strict |
| 4 | Custom guest upload + generate (40-1) | ✅ pass | etoh.gro+etoh.itp → MOL_H in export |
| 5 | Long name validation (40-2, 44-2) | ❌ issue | **Issue 1** — silently ignored, no error |
| 6 | Wrong comb-rule validation (40-3) | ✅ pass | Correctly rejected |
| 7 | Per-cage guest assignment (42-1) | ✅ pass | CH4 small + THF large |
| 8 | Per-cage occupancy % (42-2) | ✅ pass | 60% small + 100% large, counts match |
| 9 | Lattice change rebuilds rows (44-3) | ✅ pass | sI→sH→c0te→sTprime row rebuild |
| 10 | Mixed hydrate VTK colors (42-4) | ✅ pass | Gray only (accepted, distinct colors deferred) |
| 11 | Single-guest VTK (42-4) | ✅ pass | Keeps legacy gray |
| 12 | Custom guest VTK (46) | ✅ pass | Gray (accepted, same as 10) |
| 13 | Same guest in 2 cages (44.1-1) | ✅ pass | Allowed, Pitfall 6 relaxation works |
| 14 | Interface tab flow + grompp (44.1-2) | ✅ pass | gmx grompp rc=0 |
| 15 | Full tab chain + grompp (44.1-3) | ❌ issue | **Issue 2** — etoh redefined (Custom/Solute/Ion) |
| 16 | New lattices full tab chain (45-2) | ⏳ deferred | Likely affected by Issue 2 if custom mol used |
| 17 | Triclinic hydrate-only 4×4×4 (45-5) | ⏳ deferred | May pass (no custom molecule involved) |
| 18 | Custom ethanol + non-sI (45-6) | ⏳ deferred | Likely affected by Issue 2 |

### Summary

- **15/18 steps completed** (12 pass, 2 issues, 1 accepted limitation)
- **3 steps deferred** (16-18) — pending Issue 2 resolution
- **2 issues found** (both major)
- **0 blockers** (workarounds exist: use different molecule for custom vs cage guest, or use CLI)

### Steps to re-test after fix

1. **After Issue 1 fix:** Re-run F step 5 — upload `etoh_long_name.itp`, expect validation error
2. **After Issue 2 fix:** Re-run F step 15 — full tab chain (Custom+Solute+Ion), expect gmx grompp rc=0
3. **After both fixes:** Re-run F steps 16-18 — complete remaining GUI tests

### Test files for re-test

- F step 5: `quickice/data/custom/test_invalid/etoh_long_name.itp`
- F step 6: `quickice/data/custom/test_invalid/etoh_comb_rule_1.itp` (already passes)
- F step 15: Use valid `etoh.gro` + `etoh.itp` as both cage guest AND custom molecule
