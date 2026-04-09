---
phase: 20
plan: 01
subsystem: output
tags: [gromacs, export, tip4p-ice, interface]
requires: [19-02]
provides: [compute_mw_position, write_interface_gro_file, write_interface_top_file]
affects: [20-02]
---

# Phase 20 Plan 01: Interface GROMACS Writer Functions Summary

**One-liner:** Three new GROMACS writer functions for InterfaceStructure export with TIP4P-ICE normalization (3→4 atom for ice molecules, pass-through for water).

**Status:** Complete

---

## What Changed

### Files Modified

| File | Change |
|------|--------|
| `quickice/output/gromacs_writer.py` | Added 3 new functions + TIP4P_ICE_ALPHA constant |

### Key Additions

1. **TIP4P_ICE_ALPHA constant** (line 14)
   - Value: 0.13458335 (exact match with tip4p-ice.itp virtual_sites3 directive)
   - Used for MW virtual site position calculation

2. **compute_mw_position()** (lines 178-199)
   - Takes O, H1, H2 positions as numpy arrays
   - Returns MW = O + α*(H1-O) + α*(H2-O)
   - Verified O-MW distance: 0.01578 nm for standard water geometry

3. **write_interface_gro_file()** (lines 202-264)
   - Ice loop: 3 atoms/mol (O, H, H) → computes MW, writes 4 atoms
   - Water loop: 4 atoms/mol (OW, HW1, HW2, MW) → pass-through
   - Residue numbering: ice 1..N_ice, water N_ice+1..N_ice+N_water
   - All molecules output as 4-atom TIP4P-ICE SOL

4. **write_interface_top_file()** (lines 267-345)
   - Single SOL molecule type with combined count
   - Header: "Ice/water interface ({mode}) exported by QuickIce"
   - [molecules]: SOL with ice_nmolecules + water_nmolecules

---

## Verification

| Check | Result |
|-------|--------|
| All 3 functions importable | ✓ Pass |
| MW position formula verified | ✓ Pass (O-MW = 0.01578 nm) |
| Existing functions still work | ✓ Pass (no regression) |

---

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| TIP4P_ICE_ALPHA = 0.13458335 | Exact match with tip4p-ice.itp virtual_sites3 directive |
| Ice stride = 3, water stride = 4 | Internal representation preserved (export-time normalization only) |
| Single combined SOL count | Simplifies GROMACS topology, avoids phase-specific molecule types |
| Residue numbering continuous | ice 1..N_ice, water N_ice+1..N_ice+N_water |

---

## Key Patterns

### MW Virtual Site Computation
```python
mw_pos = o_pos + α * (h1_pos - o_pos) + α * (h2_pos - o_pos)
# where α = 0.13458335 (TIP4P-ICE specific)
```

### Ice Molecule Normalization (3→4 atoms)
```python
for mol_idx in range(iface.ice_nmolecules):
    base_idx = mol_idx * 3  # Ice uses 3 atoms/mol
    o_pos = iface.positions[base_idx]
    h1_pos = iface.positions[base_idx + 1]
    h2_pos = iface.positions[base_idx + 2]
    mw_pos = compute_mw_position(o_pos, h1_pos, h2_pos)
    # Write OW, HW1, HW2, MW
```

### Water Molecule Pass-Through (4 atoms)
```python
for mol_idx in range(iface.water_nmolecules):
    base_idx = iface.ice_atom_count + mol_idx * 4  # Water starts after ice
    # Write OW, HW1, HW2, MW directly from positions
```

---

## Deviations from Plan

None - plan executed exactly as written.

---

## Next Phase Readiness

**Blockers:** None

**Ready for:** 20-02 (Export GUI integration)

**Notes:**
- Three writer functions now available for Tab 2 export action
- write_interface_gro_file() handles normalization automatically
- write_interface_top_file() uses single combined molecule count
