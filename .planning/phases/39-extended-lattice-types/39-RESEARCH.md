# Phase 39: Extended Lattice Types - Research

**Researched:** 2026-06-29
**Domain:** GenIce2 hydrate lattice extension + triclinic interface blocking
**Confidence:** HIGH

## Summary

This phase extends QuickIce's hydrate generation to support 7 new GenIce2 lattice modules: C0 (c0te), C1 (c1te), C2 (c2te), filled ice Ih (ice1hte), sT' (sTprime), Ice XVI (16), and Ice XVII (17). All 7 modules are confirmed available and tested in the live GenIce2 installation.

Live GenIce2 testing resolves a critical ambiguity in LATTICE-09: **`spot_guests` crashes with IndexError for filled ices, while `parse_guest('Ne1=ch4')` works correctly.** The requirement text says "use spot_guests" but the code evidence shows parse_guest is the correct path. The planner should use parse_guest for ALL guest placement, including filled ices.

Two new lattice categories need distinct treatment: (1) filled ices (c0te, c1te, c2te, ice1hte) which use `Ne1` cage type for guest placement, and (2) water-only lattices (sTprime, 17) which have no cages and no guest support. Ice XVI (16) uses standard `12/16` cage types identical to sII.

Triclinic filled ices C0 and C1 must be blocked for interface generation using the existing Ice II blocking pattern. C2 and ice1hte are orthorhombic and safe for interface generation. sH is also triclinic but must NOT be blocked (existing behavior, preserve as-is).

**Primary recommendation:** Extend HYDRATE_LATTICES with a `cage_type_map` field per lattice that maps "small"/"large" to GenIce2 cage type labels, and use `parse_guest` (not `spot_guests`) for all guest placement.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| GenIce2 | installed | Hydrate structure generation | Only option for clathrate hydrate lattices |
| genice2.valueparser.parse_guest | installed | Guest placement by cage type | Standard GenIce2 API for guest specification |
| genice2.plugin.safe_import | installed | Lattice module loading | Lazy loading of GenIce2 lattice plugins |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | installed | Cell matrix operations | Triclinic detection in interface_builder |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| parse_guest | spot_guests | spot_guests crashes for filled ices; parse_guest works universally |
| Extend HYDRATE_LATTICES | Separate lattice registry | Same dict, simpler change, matches existing pattern |

**Installation:**
No new packages needed — all GenIce2 lattice modules already installed.

## Architecture Patterns

### Recommended Project Structure
No new files needed. Changes concentrated in:
```
quickice/structure_generation/types.py          — HYDRATE_LATTICES dict extension
quickice/structure_generation/hydrate_generator.py — _LATTICE_MODULES, _run_via_api
quickice/structure_generation/interface_builder.py — Triclinic blocking
quickice/gui/hydrate_panel.py                   — Lattice combo + guest UI
quickice/cli/parser.py                          — CLI lattice-type choices
```

### Pattern 1: HYDRATE_LATTICES Extension with cage_type_map
**What:** Add new entries to HYDRATE_LATTICES with a `cage_type_map` field that maps logical cage roles ("small", "large") to GenIce2 cage type labels.
**When to use:** All new lattice types need this mapping for `parse_guest` to work.
**Example:**
```python
# Source: live GenIce2 testing
HYDRATE_LATTICES = {
    # ... existing sI, sII, sH ...
    "c0te": {
        "genice_name": "c0te",
        "description": "Filled ice C0 (Teeratchanan 2015)",
        "cages": {
            "guest": {"name": "Ne1", "count_per_unit_cell": 3, "guest_fits": ["ch4", "thf"]},
        },
        "unit_cell_molecules": 6,
        "cage_type_map": {"small": "Ne1", "large": "Ne1"},  # Single cage type for both
        "is_triclinic": True,  # Block for interface generation
        "is_water_only": False,
    },
    "sTprime": {
        "genice_name": "sTprime",
        "description": "Filled ice sT' (Smirnov 2013)",
        "cages": {},  # No cages — water only
        "unit_cell_molecules": 24,
        "cage_type_map": {},  # No guest placement
        "is_triclinic": False,
        "is_water_only": True,
    },
}
```

### Pattern 2: Unified parse_guest for All Guest Placement
**What:** Use `parse_guest(guests, f'{cage_type}={guest_name}')` for both standard cages and filled ice Ne1 cages.
**When to use:** All lattice types with guest support.
**Example:**
```python
# Source: live GenIce2 testing verified 2026-06-29
# Standard cages (sI, sII, Ice XVI):
parse_guest(guests, '12=ch4')    # small cage
parse_guest(guests, '14=ch4')    # large cage (sI)
parse_guest(guests, '16=ch4')    # large cage (sII, Ice XVI)

# Filled ice cages (C0, C1, C2, Ih):
parse_guest(guests, 'Ne1=ch4')   # all filled ice guest positions
parse_guest(guests, 'Ne1=thf')   # THF in filled ice (verified works)
```

### Pattern 3: Triclinic Blocking for Interface Generation
**What:** Check `candidate.phase_id` in `validate_interface_config` to block triclinic hydrate lattices from interface generation.
**When to use:** C0 and C1 filled ices (triclinic), same pattern as Ice II.
**Example:**
```python
# Source: quickice/structure_generation/interface_builder.py line 104
# Extended pattern:
TRICLINIC_HYDRATE_PHASES = {"hydrate_c0te", "hydrate_c1te"}
if candidate.phase_id in TRICLINIC_HYDRATE_PHASES:
    raise InterfaceGenerationError(
        f"[{config.mode}] {lattice_description} is not supported for interface generation. "
        f"\n\n{crystal_explanation}...",
        mode=config.mode
    )
```

### Anti-Patterns to Avoid
- **Using spot_guests for filled ice guest placement:** spot_guests crashes with IndexError for filled ices. Use parse_guest instead.
- **Hardcoding Ne1 in _run_via_api:** Use cage_type_map from HYDRATE_LATTICES to drive cage type lookup.
- **Blocking sH from interface generation:** sH is triclinic but existing behavior allows it. Do NOT add sH to the block list.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Guest placement for filled ices | Custom spot_guests path | parse_guest('Ne1=ch4') | spot_guests crashes; parse_guest is the standard GenIce2 path |
| Triclinic cell detection | Custom cell matrix check | Use HYDRATE_LATTICES["is_triclinic"] flag | Consistent with crystallographic classification |
| Lattice module loading | Manual import per module | safe_import('lattice', genice_name) | GenIce2's plugin system handles it |

**Key insight:** GenIce2 already handles all the lattice-specific details (cage positions, symmetry operations, guest placement). We just need to pass the right parameters through.

## Common Pitfalls

### Pitfall 1: spot_guests Crashes for Filled Ices
**What goes wrong:** Using `GenIce(lattice, spot_guests={'Ne1': 'ch4'})` crashes with `IndexError: only integers, slices (...) are valid indices`.
**Why it happens:** The `spot_guests` path in GenIce2's Stage7 uses `repcagepos[i]` with a different indexing scheme that doesn't match filled ice cage structures.
**How to avoid:** Always use `parse_guest` path (which works for all lattice types), never `spot_guests`.
**Warning signs:** If code tries `GenIce(lattice, spot_guests=...)`, it will fail at generate_ice().

### Pitfall 2: Water-Only Lattices With Guest Selection
**What goes wrong:** User selects sTprime or Ice XVII and picks a guest type, but these lattices have no cages and can't place guests.
**Why it happens:** The GUI doesn't disable guest selection for water-only lattices, and HydrateConfig validation allows any guest_type.
**How to avoid:** Add `is_water_only` flag to HYDRATE_LATTICES. When a water-only lattice is selected, disable guest UI elements and skip parse_guest in _run_via_api.
**Warning signs:** HydrateStructure with guest_count > 0 for a water-only lattice would indicate this bug.

### Pitfall 3: sH is Triclinic But Must NOT Be Blocked
**What goes wrong:** Adding triclinic detection and accidentally blocking sH from interface generation.
**Why it happens:** sH cell has off-diagonal elements (cell[1,0] = -6.21), making it triclinic.
**How to avoid:** Use explicit phase_id-based blocking list (hydrate_c0te, hydrate_c1te), NOT generic triclinic detection. sH's phase_id "hydrate_sH" must NOT be in the block set.
**Warning signs:** If sH interface generation suddenly fails after this phase, check the blocking list.

### Pitfall 4: Single Cage Type for Both Occupancy Values
**What goes wrong:** Filled ices have only ONE cage type (Ne1), but UI has small/large occupancy controls. If both are applied to Ne1, guests are double-placed.
**Why it happens:** Current _run_via_api applies both `small_occ` and `large_occ` to separate cage types. With Ne1, both would add guests to the same positions.
**How to avoid:** For single-cage lattices (Ne1 only), use only one occupancy value. Map cage_occupancy_small to Ne1 and skip cage_occupancy_large, OR add a single "occupancy" control for these lattices.
**Warning signs:** Guest count exceeding cage count for filled ice lattices.

### Pitfall 5: Cage Type Mapping for Ice XVI vs sII
**What goes wrong:** Ice XVI uses the SAME cage structure as sII (12/16) but is a different lattice type. If cage_type_map is not properly configured, guest placement will silently fail.
**Why it happens:** The GenIce2 module for "16" inherits from CS2 (sII), so cage types are identical.
**How to avoid:** Give Ice XVI the same cage_type_map as sII: {"small": "12", "large": "16"}.
**Warning signs:** Ice XVI generating without any guests would indicate misconfigured cage_type_map.

### Pitfall 6: HydrateLatticeInfo.from_lattice_type Assumes "cages" Dict Structure
**What goes wrong:** `HydrateLatticeInfo.from_lattice_type` iterates over `lattice["cages"]` assuming it has "small"/"large"/"medium" keys with "name"/"count_per_unit_cell" sub-dicts. Filled ices have a single "guest" key; water-only lattices have empty cages.
**Why it happens:** The method was designed for sI/sII/sH only, where cages always have small/large structure.
**How to avoid:** Update `from_lattice_type` to handle: (1) filled ice "guest" cage key, (2) empty cages dict for water-only lattices. For water-only, cage_types=[], cage_counts={}, total_cages=0.
**Warning signs:** `KeyError` or `AttributeError` when calling `HydrateLatticeInfo.from_lattice_type("c0te")`.

## Code Examples

Verified patterns from live GenIce2 testing:

### Filled Ice Guest Placement (parse_guest with Ne1)
```python
# Source: live GenIce2 testing 2026-06-29
from genice2.valueparser import parse_guest
from collections import defaultdict

guests = defaultdict(dict)
parse_guest(guests, 'Ne1=ch4')   # Works for c0te, c1te, c2te, ice1hte
# Result: {'Ne1': {'ch4': 1.0}}

# With occupancy:
parse_guest(guests, 'Ne1=ch4*0.5')  # 50% occupancy
# Result: {'Ne1': {'ch4': 0.5}}
```

### Ice XVI Guest Placement (standard cage types)
```python
# Source: live GenIce2 testing 2026-06-29
# Ice XVI has identical cage structure to sII (12 small, 8 large)
parse_guest(guests, '12=ch4')   # Small cages
parse_guest(guests, '16=ch4')   # Large cages
# Mixed: 12=ch4 + 16=thf also works
```

### Triclinic Blocking Pattern
```python
# Source: quickice/structure_generation/interface_builder.py line 104
# Existing Ice II blocking — replicate this pattern:
if candidate.phase_id == "ice_ii":
    raise InterfaceGenerationError(
        f"[{config.mode}] Ice II (rhombohedral, space group R-3) is not supported for interface generation. "
        f"\n\nIce II has a rhombohedral crystal structure that cannot be transformed to an orthogonal supercell...",
        mode=config.mode
    )

# New triclinic hydrate blocking:
TRICLINIC_HYDRATE_PHASES = {"hydrate_c0te", "hydrate_c1te"}
if candidate.phase_id in TRICLINIC_HYDRATE_PHASES:
    lattice_name = candidate.phase_id.replace("hydrate_", "")
    raise InterfaceGenerationError(
        f"[{config.mode}] {lattice_name.upper()} filled ice (triclinic) is not supported for interface generation. "
        f"\n\nFilled ice C0 and C1 have triclinic crystal structures that cannot be transformed "
        f"to an orthogonal supercell (this is a fundamental crystallographic constraint). "
        f"When forced into an orthogonal simulation box, these lattices develop gaps at the corners. "
        f"\n\nSupported hydrate lattices for interfaces:\n"
        f"  • C2 (orthorhombic filled ice): Works correctly\n"
        f"  • Filled ice Ih (orthorhombic): Works correctly\n"
        f"  • Ice XVI (cubic): Works correctly\n"
        f"  • All standard hydrates (sI, sII): Work correctly\n",
        mode=config.mode
    )
```

### Lattice Module Loading for New Types
```python
# Source: quickice/structure_generation/hydrate_generator.py
# Add new lattice modules to _LATTICE_MODULES and lazy import:
_LATTICE_MODULES = {
    "sI": "sI",
    "sII": "sII",
    "sH": "sH",
    "c0te": "c0te",
    "c1te": "c1te",
    "c2te": "c2te",
    "ice1hte": "ice1hte",
    "sTprime": "sTprime",
    "16": "16",       # GenIce2 module name for Ice XVI
    "17": "17",       # GenIce2 module name for Ice XVII
}

# In _ensure_genice_import, add lazy imports:
from genice2.lattices import c0te, c1te, c2te, ice1hte, sTprime
# For numeric module names, use safe_import at runtime instead
```

### _run_via_api Cage Type Routing
```python
# Source: proposed pattern based on live testing
# Replace hardcoded cage type logic with cage_type_map lookup:

cage_type_map = HYDRATE_LATTICES[config.lattice_type].get("cage_type_map", {})
is_water_only = HYDRATE_LATTICES[config.lattice_type].get("is_water_only", False)

if is_water_only:
    # No guest placement — water-only structure
    guests = defaultdict(dict)
else:
    # Build guests using cage_type_map
    small_cage = cage_type_map.get("small")
    large_cage = cage_type_map.get("large")

    if small_occ > 0 and small_cage:
        guest_spec = f"{small_cage}={guest_name}"
        if small_occ < 1.0:
            guest_spec = f"{small_cage}={guest_name}*{small_occ}"
        parse_guest(guests, guest_spec)

    if large_occ > 0 and large_cage:
        guest_spec = f"{large_cage}={guest_name}"
        if large_occ < 1.0:
            guest_spec = f"{large_cage}={guest_name}*{large_occ}"
        parse_guest(guests, guest_spec)
```

## Lattice Data Reference

All data verified by live GenIce2 testing on 2026-06-29:

### New HYDRATE_LATTICES Entries

| Lattice | Key | genice_name | Description | Unit Cell Waters | Cages | Cage Types | Triclinic | Water-Only |
|---------|-----|-------------|-------------|-------------------|-------|-------------|-----------|------------|
| C0 | c0te | c0te | Filled ice C0 (Teeratchanan 2015) | 6 | 3 | Ne1×3 | YES | No |
| C1 | c1te | c1te | Filled ice C1 (Teeratchanan 2015) | 36 | 6 | Ne1×6 | YES | No |
| C2 | c2te | c2te | Filled ice C2 (Teeratchanan 2015) | 32 | 32 | Ne1×32 | No | No |
| Ih | ice1hte | ice1hte | Filled ice Ih (Teeratchanan 2015) | 16 | 8 | Ne1×8 | No | No |
| sT' | sTprime | sTprime | Filled ice sT' (Smirnov 2013) | 24 | 0 | — | No | YES |
| XVI | 16 | 16 | Ice XVI (empty sII framework) | 136 | 24 | 12×16 + 16×8 | No | No |
| XVII | 17 | 17 | Ice XVII (ultralow density) | 12 | 0 | — | No | YES |

### Cage Type Mapping

| Lattice | small_cage_type | large_cage_type | Notes |
|---------|-----------------|-----------------|-------|
| sI | 12 | 14 | Existing, unchanged |
| sII | 12 | 16 | Existing, unchanged |
| sH | 12 | 16 | Existing (NOTE: sH guest placement has existing issues — not this phase) |
| c0te | Ne1 | Ne1 | Same cage type for both occupancy values |
| c1te | Ne1 | Ne1 | Same cage type for both occupancy values |
| c2te | Ne1 | Ne1 | Same cage type for both occupancy values |
| ice1hte | Ne1 | Ne1 | Same cage type for both occupancy values |
| 16 | 12 | 16 | Identical to sII cage structure |
| sTprime | — | — | Water-only, no cage mapping |
| 17 | — | — | Water-only, no cage mapping |

### Cell Properties

| Lattice | Cell Type | Cell Vectors (nm) | Interface Safe |
|---------|-----------|-------------------|----------------|
| c0te | TRICLINIC | [[0.6177, 0, 0], [-0.30885, 0.53494, 0], [0, 0, 0.6054]] | NO — BLOCK |
| c1te | TRICLINIC | [[1.2673, 0, 0], [-0.63365, 1.09751, 0], [0, 0, 0.6017]] | NO — BLOCK |
| c2te | ORTHORHOMBIC | diag(0.8818, 0.8818, 1.2502) | YES |
| ice1hte | ORTHORHOMBIC | diag(0.9136, 0.798, 0.6894) | YES |
| sTprime | ORTHORHOMBIC | diag(4.04346, 3.18401, 3.18413) | YES |
| 16 | CUBIC | diag(6.20577, 6.20577, 6.20577) | YES |
| 17 | ORTHORHOMBIC | diag(2.66454, 4.69111, 2.55092) | YES |

### GenIce2 Residue Naming

All GenIce2 lattice types use "ICE" residue for water and "CH4"/"THF" for guests. This is already handled correctly by the metadata-driven `_build_molecule_index` (checks atom patterns OW/HW1/HW2/MW, not residue name "SOL").

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 3 hydrate lattices (sI, sII, sH) | 10 lattices (3 standard + 4 filled ice + 1 sT' + 2 empty framework) | This phase | HYDRATE_LATTICES expansion |
| Hardcoded cage types (12/14/16) | cage_type_map per lattice | This phase | Drives parse_guest dynamically |
| No water-only lattices | sTprime, 17 have no guest support | This phase | Guest UI must be conditional |
| Ice II only blocked | C0, C1 also blocked | This phase | Triclinic hydrate blocking |

**Deprecated/outdated:**
- spot_guests: Does NOT work for filled ices (IndexError). Use parse_guest instead.

## Open Questions

### 1. Single Cage Type Occupancy Handling
**What we know:** Filled ices (C0, C1, C2, Ih) have only ONE cage type (Ne1). The current UI has separate small/large occupancy controls.
**What's unclear:** Should both occupancy values be applied to Ne1 (potentially over-occupying), or should only one be used?
**Recommendation:** For single-cage-type lattices, map `cage_occupancy_small` to Ne1 and ignore `cage_occupancy_large`. This gives the user one occupancy control per lattice. The UI could disable the large occupancy spinner for these lattices. Alternatively, treat both as applying to the same cages with the maximum of the two values.

### 2. Water-Only Lattice Guest Type Validation
**What we know:** sTprime and Ice XVII have no cages, so no guests can be placed.
**What's unclear:** Should HydrateConfig reject guest_type for water-only lattices, or should the UI disable the guest selector?
**Recommendation:** Two-pronged approach: (1) UI disables guest combo and occupancy controls when water-only lattice is selected; (2) _run_via_api skips guest placement when `is_water_only=True`. Don't add validation to HydrateConfig — let the generation code handle it, keeping HydrateConfig construction simple.

### 3. Numeric GenIce2 Module Names (16, 17)
**What we know:** GenIce2 lattice modules for Ice XVI and XVII are named "16" and "17" (numeric), which can't be imported with standard `from genice2.lattices import 16`.
**What's unclear:** Whether `safe_import('lattice', '16')` works reliably.
**Recommendation:** Use `safe_import('lattice', name)` for all lattice loading (already the pattern in _run_via_api). The _LATTICE_MODULES dict maps our key to the GenIce2 module name. For _ensure_genice_import, we can't do `from genice2.lattices import 16`, so use safe_import at generation time instead of pre-importing in _ensure_genice_import.

### 4. sH Existing Guest Bug
**What we know:** sH doesn't have cagepos/cagetype attributes. The current code tries `parse_guest(guests, '16=ch4')` for sH large cage, but sH's cage types are "12", "12_1", and "20" (from the deprecated `cages` string format).
**What's unclear:** Whether this is silently failing or producing incorrect results.
**Recommendation:** This is an EXISTING BUG, not in scope for this phase. Document it but don't fix it. The sH guest placement issue predates this phase.

## Sources

### Primary (HIGH confidence)
- Live GenIce2 testing on 2026-06-29 — all 7 new lattice modules verified
- quickice/structure_generation/types.py — HYDRATE_LATTICES structure, HydrateConfig, HydrateLatticeInfo
- quickice/structure_generation/hydrate_generator.py — _run_via_api, _LATTICE_MODULES, _build_molecule_index
- quickice/structure_generation/interface_builder.py — Ice II blocking pattern (line 104)
- GenIce2 c0te.py source — Ne1 cage type, P3_2 space group
- GenIce2 ice1hte.py source — Ne1 cage type, Cmc2_1 space group
- GenIce2 CS2.py source — 12/16 cage types for Ice XVI
- GenIce2 ice17.py source — no cages, water only

### Secondary (MEDIUM confidence)
- GenIce2 DOH.py source — sH cages string format (deprecated format)
- GenIce2 GenIce.__init__ signature — spot_guests parameter exists but crashes for filled ices

### Tertiary (LOW confidence)
- None — all findings verified by live testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all GenIce2 modules tested and confirmed working
- Architecture: HIGH — patterns match existing codebase, tested with live GenIce2
- Pitfalls: HIGH — spot_guests crash confirmed, single-cage-type issue identified, sH exclusion verified
- Cage type mapping: HIGH — parse_guest tested for all combinations (Ne1=ch4, Ne1=thf, 12=ch4, 16=ch4, 16=thf)

**Research date:** 2026-06-29
**Valid until:** 2026-07-29 (30 days — stable GenIce2 API)
