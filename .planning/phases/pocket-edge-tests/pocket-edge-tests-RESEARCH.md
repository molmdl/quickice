# Phase: Pocket Mode Edge Cases - Research

**Researched:** 2026-05-22
**Domain:** Pocket mode cavity generation in QuickIce (ice-water interface)
**Confidence:** HIGH

## Summary

This research investigates the pocket mode code in QuickIce to identify edge cases for thin cavities and non-spherical pockets, and to determine what tests should be written. The pocket mode (`assemble_pocket()` in `pocket.py`) creates a water-filled cavity inside an ice matrix. It supports two shapes (sphere and cubic), handles both regular ice and hydrate candidates, and performs multi-phase overlap removal.

**Primary recommendation:** Write focused edge-case tests using mock candidates (no GenIce2 dependency) that verify structural invariants (atom count divisibility, positions-within-bounds, atom_names/positions consistency, no ice-inside-cavity, no water-outside-cavity) across shape variants, size extremes, and hydrate combinations. Also add the missing water-count-divisible-by-4 assertion in pocket.py (matching slab.py's FRAG-02 fix).

## Code Map

### Core Pocket Files

| File | Purpose | Key Functions |
|------|---------|---------------|
| `quickice/structure_generation/modes/pocket.py` | Pocket mode assembly | `assemble_pocket()`, `detect_atoms_per_molecule()`, `_detect_guest_atoms()`, `_count_guest_molecules()` |
| `quickice/structure_generation/overlap_resolver.py` | PBC-aware overlap detection & removal | `detect_overlaps()`, `remove_overlapping_molecules()`, `filter_atom_names()` |
| `quickice/structure_generation/water_filler.py` | Tiling & water filling | `tile_structure()`, `fill_region_with_water()`, `round_to_periodicity()`, `get_cell_extent()`, `scale_positions_for_density()`, `load_water_template()` |
| `quickice/structure_generation/types.py` | Data types | `Candidate`, `InterfaceConfig`, `InterfaceStructure` |
| `quickice/structure_generation/interface_builder.py` | Validation & routing | `validate_interface_config()`, `generate_interface()` |
| `quickice/structure_generation/errors.py` | Error types | `InterfaceGenerationError` |
| `quickice/utils/molecule_utils.py` | Guest atom counting | `count_guest_atoms()` |
| `quickice/phase_mapping/water_density.py` | Water density from T/P | `water_density_gcm3()` |

### Supporting Files (Shared with Slab/Piece)

| File | Shared Code | Pocket-Specific Differences |
|------|-------------|------------------------------|
| `quickice/structure_generation/modes/slab.py` | `detect_atoms_per_molecule()`, `_detect_guest_atoms()`, `_count_guest_molecules()`, overlap removal, guest tiling | Slab has 2-phase overlap removal (ice-water then guest-water) with FRAG-02 assertions; Pocket has the same but **without** the assertions |
| `quickice/structure_generation/modes/piece.py` | Same helper functions, overlap detection | Piece centers ice in water; no cavity |

### Existing Test Files with Pocket Coverage

| File | What It Tests | Coverage Gaps |
|------|---------------|---------------|
| `tests/test_interface_modes_audit.py` | Pocket mode with ice & hydrate candidates; verifies `len(atom_names) == len(positions)` | Only tests sphere shape, diameter=1.0, single box size. No shape variants, no size extremes, no invariant checks beyond length match |
| `tests/test_triclinic_interface.py` | Ice II rejected in pocket mode | Only Ice II rejection; no Ice V pocket test (Ice V should work) |
| `tests/test_med03_minimum_box_size.py` | Small box rejected in pocket mode | Only validation, not generation |
| `tests/test_overlap_removal_invariants.py` | Water count % 4 == 0 after overlap removal (FRAG-02) | Tests `remove_overlapping_molecules()` directly, NOT through `assemble_pocket()`. Does NOT test pocket-specific removal sequences |
| `tests/test_atom_names_filtering.py` | `filter_atom_names()` correctness | Unit-level only, not integration through pocket |
| `tests/test_integration_v35.py` | CLI pocket interface with Ice V | Integration test; only sphere, diameter=2.0 |

### Debug/Resolved Test Files

| File | What It Tests |
|------|---------------|
| `.planning/debug/resolved/test_med04_pocket_performance.py` | Performance optimization (fill bounding box not entire box). Tests small cavity in large box and edge cases (very small & large pocket). **Not in main test suite** |
| `.planning/debug/deferred/test_pocket_ice.py` | Tests Ice II pocket (should be rejected). Debug script, not in test suite |

## Algorithm Walkthrough

### Step-by-Step: `assemble_pocket()` (pocket.py:120-559)

**Step 1: Detect atoms per molecule** (lines 152-153)
- Call `detect_atoms_per_molecule()` on `candidate.atom_names`
- Returns 3 for GenIce ice (O, H, H), 4 for TIP4P/hydrate (OW, HW1, HW2, MW)
- **Edge case:** What if candidate has 0 atoms? → `atom_names` is empty → returns 3 (default)
- **Risk:** Empty atom_names always returns 3, even for empty candidate. If positions is also empty, downstream `tile_structure()` returns zeros

**Step 2: Extract hydrate guests** (lines 155-178)
- Check `metadata["original_hydrate"]`
- If hydrate: call `_detect_guest_atoms()` to split water framework vs guests
- Extract `raw_guest_positions`, `guest_atom_names`, `guest_nmolecules`
- **Edge case:** Guest positions could be None or empty if all molecules are water
- **Risk:** `_detect_guest_atoms()` safeguard checks for OW misclassification, but what if guest type is unknown?

**Step 3: Adjust box dimensions for periodicity** (lines 180-197)
- `round_to_periodicity()` for each box dimension → ensures continuous PBC images
- Adjusts to multiples of ice unit cell dimensions
- **Edge case:** If cell dims are very small and box is large → many cells, large positions array
- **Edge case:** If cell dims don't evenly divide box → dimensions are rounded UP, potentially changing box size significantly

**Step 4: Tile ice to fill box** (lines 205-211)
- `tile_structure(water_framework_positions, ice_cell_dims, box_dims, ...)`
- For hydrate: tiles only water framework (not guests)
- **Edge case:** Tiling with very small cell in large box → huge arrays
- **Risk:** `filter_molecules` defaults to True in `tile_structure()`, which removes molecules spanning PBC boundaries

**Step 5: Build ice atom names** (lines 219-224)
- Generate `["OW", "HW1", "HW2", "MW"] * ice_nmolecules` or `["O", "H", "H"] * ice_nmolecules`
- **Edge case:** If `ice_nmolecules` is 0 (no ice after tiling) → empty list

**Step 6: Remove ice molecules inside cavity** (lines 226-262)
- **Shape-dependent:**
  - **Sphere:** `distances = np.linalg.norm(ice_o_positions - center, axis=1)` → `ice_inside_cavity = set(np.where(distances < radius)[0])`
  - **Cubic:** `|dx| < radius AND |dy| < radius AND |dz| < radius` → `ice_inside_cavity`
- Call `remove_overlapping_molecules(ice_positions, ice_inside_cavity, atoms_per_molecule=atoms_per_mol)`
- Call `filter_atom_names(ice_atom_names, ice_inside_cavity, atoms_per_molecule=atoms_per_mol)`
- **Critical:** `ice_inside_cavity` uses **strict inequality** (`< radius` for sphere, `< radius` for cubic)
- **Edge case:** If no ice is inside cavity → `ice_inside_cavity` is empty → no removal
- **Edge case for cubic:** The cubic cavity uses `< radius` for each dimension independently. This means a molecule exactly at `center + [radius-ε, radius-ε, radius-ε]` is inside, but one at `center + [radius, 0, 0]` is outside. For "thin" boxes (e.g., box is flat in one dimension), the cavity could overlap with the box boundary.

**Step 7: Fill cavity with water** (lines 264-293)
- `fill_dims = [2*radius, 2*radius, 2*radius]` → bounding box of cavity
- `fill_region_with_water(fill_dims, target_density=target_water_density)`
- Translate water positions from `[0, 2r]` to `[center-r, center+r]`
- **Edge case:** Very small pocket (0.5nm diameter → 0.25nm radius) → `fill_dims = [0.5, 0.5, 0.5]` → may produce 0 or very few water molecules
- **Risk:** `fill_region_with_water()` uses `tile_structure()` which filters molecules. Very small regions may lose all molecules

**Step 8: Remove water OUTSIDE cavity** (lines 295-330)
- **Shape-dependent:**
  - **Sphere:** `water_distances >= radius` → outside
  - **Cubic:** `|dx| >= radius OR |dy| >= radius OR |dz| >= radius` → outside
- Call `remove_overlapping_molecules(water_positions, water_outside, atoms_per_molecule=4)`
- Call `filter_atom_names(water_atom_names, water_outside, atoms_per_molecule=4)`
- **Critical:** Uses `>=` for boundary (water AT boundary is outside), while Step 6 uses `<` (ice AT boundary stays)
- **Edge case:** For cubic shape, the volume is (2r)³. For sphere, volume is (4/3)πr³. Cubic holds more water but has less symmetry → more boundary overlap issues
- **MISSING:** No `assert len(water_positions) % 4 == 0` after this step (slab.py has this in FRAG-02!)

**Step 9: Hydrate guest tiling** (lines 332-432)
- Tile guests in full box, then remove guests INSIDE cavity
- Uses `filter_molecules=False` for guests (GenIce2 outputs complete molecules)
- Guest removal uses distance from center, similar to ice removal
- **Edge case:** If all guests end up inside cavity → `tilable_guest_positions = None`
- **Risk:** Guest atom names calculation uses `tiling_factor = tiled_guest_nmolecules // original_guest_nmolecules` which can have remainder issues

**Step 10: Guest-water overlap detection** (lines 434-461)
- Detect overlaps between ALL guest atoms and water OW atoms
- Remove overlapping water molecules
- **Edge case:** If guests are very close to cavity boundary, many water molecules may be removed
- **MISSING:** No `assert len(water_positions) % 4 == 0` after this step either

**Step 11: Ice-water overlap detection** (lines 463-490)
- Detect overlaps between ice O atoms and water O atoms
- Remove overlapping water molecules (NOT ice)
- **Edge case:** For cubic pockets, the ice-water boundary has different geometry than sphere → may have different overlap patterns
- **MISSING:** No `assert len(water_positions) % 4 == 0` after this step either

**Step 12: Combine all positions** (lines 492-559)
- Order: ice, then water, then guests
- Compute counts, build cell matrix, build report
- Return `InterfaceStructure`

### Key Observation: Missing FRAG-02 Assertions in Pocket Mode

Slab.py has **two** assertions after overlap removal (lines 377-380 and 561-564):
```python
assert len(trimmed_water_positions) % 4 == 0, (
    f"Water atom count {len(trimmed_water_positions)} not divisible by 4 "
    f"after ice-water overlap removal"
)
```

Pocket.py has the **same three overlap removal steps** (Steps 8, 10, 11) but **NO assertions** checking water atom count divisibility. This is a gap — if any bug corrupts the water positions array, pocket mode would silently produce invalid output while slab mode would catch it.

## Existing Test Coverage

### What IS Tested

1. **Pocket + ice candidate** (test_interface_modes_audit.py:196-215): sphere, diameter=1.0, box=3×3×3 → verifies `len(atom_names) == len(positions)`
2. **Pocket + hydrate candidate** (test_interface_modes_audit.py:218-240): sphere, diameter=1.0, box=3×3×3 → verifies `len(atom_names) == len(positions)`
3. **Ice II rejection in pocket mode** (test_triclinic_interface.py:81-98): validates error message
4. **Small box rejection in pocket mode** (test_med03_minimum_box_size.py:136-149): box=0.5×0.5×0.5, diameter=0.3
5. **CLI pocket with Ice V** (test_integration_v35.py:254-278): integration test, validates .gro file
6. **Overlap removal invariants** (test_overlap_removal_invariants.py): tests `remove_overlapping_molecules()` and `filter_atom_names()` directly, but NOT through `assemble_pocket()`
7. **Atom names filtering** (test_atom_names_filtering.py): tests `filter_atom_names()` directly

### What is NOT Tested (Gaps)

1. **Cubic pocket shape** — Zero tests use `pocket_shape="cubic"`. All existing tests default to `"sphere"`
2. **Small pocket sizes** — No test with `pocket_diameter` near minimum (0.5 nm from GUI range)
3. **Large pocket relative to box** — No test where pocket is close to box size (e.g., 4.0 nm diameter in 5.0 nm box)
4. **Non-cubic boxes** — All tests use cubic boxes (3×3×3, 4×4×4). No test with rectangular box (e.g., 5×3×3)
5. **Water count divisible by 4** — No pocket-specific test verifying `water_atom_count % 4 == 0` after overlap removal
6. **Ice molecules correctly outside cavity** — No test verifying ice O atoms are all outside the cavity radius
7. **Water molecules correctly inside cavity** — No test verifying water O atoms are all inside the cavity radius
8. **Positions within box bounds** — No test verifying all positions are in [0, box_dims)
9. **Atom ordering consistency** — No test verifying ice atoms come first, then water, then guests
10. **Guest removal inside cavity** — No test verifying guests are removed from cavity region
11. **Guest-water overlap removal** — No test for the guest-water overlap fix added in the resolved debug session
12. **Thin/asymmetric cavities** — Impossible with current code (no aspect ratio parameter), but the "cubic" shape creates a different boundary geometry than sphere
13. **Cavity near box boundary** — When adjusted box size causes cavity center to be at adjusted_center, PBC wrapping should keep everything inside
14. **Multiple overlap removal phases** — No test verifying water count stays consistent through all 3 removal phases (water-outside-cavity, guest-water, ice-water)

## Edge Cases Identified

### EC-1: Cubic Shape Boundary Geometry
**What:** The cubic cavity uses axis-aligned boundaries (`|dx| < radius`), creating a sharp square interface. Unlike the sphere (smooth radial boundary), the cubic boundary has edges and corners where ice molecules are closer to the cavity wall.
**Risk:** At the 12 edges of the cubic cavity, ice molecules at distances like `([radius-ε, radius-ε, 0])` are classified as inside, while a sphere would have them outside (distance = radius*√2). This creates a differently-shaped ice-water interface with potentially different overlap counts.
**Test needed:** Verify cubic pocket has water only inside cubic region and ice only outside.

### EC-2: Very Small Pocket (Near-Minimum Diameter)
**What:** `pocket_diameter = 0.5` nm (GUI minimum), radius = 0.25 nm. The bounding box is [0.5, 0.5, 0.5] nm. This is barely larger than a single water molecule (~0.28 nm O-O distance).
**Risk:** `fill_region_with_water()` on [0.5, 0.5, 0.5] nm may produce very few or zero water molecules after molecule filtering. `tile_structure()` filters molecules spanning PBC boundaries — in a 0.5 nm box, many molecules may span the boundary and get filtered out.
**Test needed:** Verify `assemble_pocket()` with minimum diameter produces valid output (may have 0 water molecules, which is acceptable, but must not crash or produce corrupt data).

### EC-3: Pocket Diameter Close to Box Size
**What:** `pocket_diameter = 4.5` in a `box = 5.0 × 5.0 × 5.0` box. Only 0.25 nm of ice on each side.
**Risk:** Very thin ice shell. Almost all ice molecules could be inside the cavity, leaving very few ice molecules. The `ice_nmolecules` could be very small. Also, periodicity adjustments could push box slightly bigger, making the pocket even closer to box.
**Test needed:** Verify thin ice shell pocket still produces valid structure with `ice_nmolecules > 0`.

### EC-4: Non-Cubic Box with Pocket
**What:** Box = [5.0, 3.0, 3.0] nm with `pocket_diameter = 2.0` nm (sphere). The cavity center is at [2.5, 1.5, 1.5]. The sphere fits in all dimensions, but the box is elongated in X.
**Risk:** After periodicity adjustment, box dimensions could change unevenly. The cavity is always at `box_dims / 2.0`, but periodicity adjustments differ per dimension.
**Test needed:** Verify rectangular box pocket produces valid structure.

### EC-5: Sphere Boundary vs. Cubic Boundary Water Count
**What:** For same diameter, cubic cavity has volume (2r)³ = 8r³ while sphere has (4/3)πr³ ≈ 4.19r³. Cubic should have roughly 2× more water molecules.
**Risk:** The water count difference between shapes for same diameter is significant. No test verifies this ratio is reasonable.
**Test needed:** Verify cubic pocket contains more water molecules than sphere pocket with same diameter.

### EC-6: Hydrate Guests Inside Cavity
**What:** Guest molecules inside the cavity should be removed (Step 9). But if guest positions tile such that some guests end up very close to the cavity boundary...
**Risk:** The distance check uses `np.linalg.norm(guest_o_positions - center, axis=1)` for ALL guest shapes (including non-spherical guests like THF). For cubic pocket, the guest removal uses Euclidean distance, not the cubic criterion. **This is a bug:** guests are removed based on sphere distance even when `pocket_shape == "cubic"`.
**Test needed:** Verify guests are removed from cavity for BOTH shapes. For cubic, guest removal should use the cubic criterion, but currently uses sphere distance.

### EC-7: Water-Out-Cavity Removal Consistency
**What:** Step 8 removes water OUTSIDE the cavity. For sphere, uses `>= radius`. For cubic, uses `|dx| >= radius OR |dy| >= radius OR |dz| >= radius`.
**Risk:** A water molecule at the exact boundary (distance == radius for sphere, |dx| == radius for cubic) is classified as OUTSIDE and removed. But the corresponding ice molecule at the boundary (Step 6, distance == radius) is classified as OUTSIDE the cavity (ice stays). This means there's a gap at the boundary where neither ice nor water exists — this is intentional (the overlap resolver handles it in Step 11).
**Test needed:** Verify no water molecules exist outside the cavity after Step 8.

### EC-8: Three-Phase Overlap Removal Consistency
**What:** Pocket has 3 overlap removal phases: (1) water-outside-cavity, (2) guest-water, (3) ice-water. Each phase operates on the result of the previous phase.
**Risk:** If any phase corrupts the atom count (e.g., produces non-divisible-by-4 water count), subsequent phases operate on invalid data. Slab.py has assertions after each phase; pocket.py does NOT.
**Test needed:** Verify `water_atom_count % 4 == 0` after each overlap removal phase.

### EC-9: Atom Names / Positions Length Match After All Removals
**What:** Each `remove_overlapping_molecules()` call must be paired with a `filter_atom_names()` call using the SAME `overlapping_mol_indices`.
**Risk:** If indices don't match (e.g., one uses stale indices), positions and atom_names arrays diverge. This was the FRAG-02 class of bugs.
**Test needed:** Verify `len(positions) == len(atom_names)` in final InterfaceStructure.

### EC-10: Cavity Center After Box Adjustment
**What:** `center = box_dims / 2.0` where `box_dims` uses ADJUSTED dimensions. If box_x was adjusted from 3.0 to 3.572, center shifts from 1.5 to 1.786.
**Risk:** Water positions are translated relative to this adjusted center. If the adjustment is significant, the cavity could be positioned differently than the user expects.
**Test needed:** Verify cavity center matches `adjusted_box / 2.0` and water molecules are centered there.

### EC-11: Pocket with Different Ice Phases
**What:** Ice Ih, Ic, III, V, VI, VII, VIII all have different cell dimensions and atom arrangements.
**Risk:** Some phases have triclinic cells (Ice V). The tiling uses `cell_matrix` for triclinic-aware tiling. Ice II is blocked (rhombohedral). Other triclinic phases should work.
**Test needed:** Verify pocket mode works with at least Ice V (monoclinic/triclinic) candidate.

### EC-12: Empty Water After All Removals
**What:** If all water molecules in the cavity overlap with ice (e.g., very small cavity), `water_nmolecules` could be 0.
**Risk:** The code does not raise an error if `water_nmolecules == 0` after overlap removal (only raises if `fill_region_with_water()` returns 0 initially). This is probably fine — a tiny pocket with no water is physically valid but unusual.
**Test needed:** Verify small pocket doesn't crash even if water_nmolecules == 0.

## Risk Areas

### RISK-1: Missing Water Count Assertions (HIGH)
**What:** Pocket.py has 3 overlap removal phases but NO assertions that water atom count stays divisible by 4 after each phase. Slab.py added these in FRAG-02.
**Impact:** If a bug corrupts the water array (e.g., partial molecule removal), pocket mode silently produces invalid output that will crash GROMACS.
**Recommendation:** Add 3 assertions in pocket.py matching slab.py's FRAG-02 pattern.

### RISK-2: Guest Removal Uses Sphere Distance for Cubic Pockets (MEDIUM)
**What:** In Step 9 (lines 388-390), guest removal from cavity uses `np.linalg.norm(guest_o_positions - center, axis=1)` (Euclidean distance = sphere criterion) regardless of `pocket_shape`. For cubic pockets, guests should be removed if `|dx| < radius AND |dy| < radius AND |dz| < radius`.
**Impact:** For cubic pockets with hydrate, guests near the cubic edges/corners that are outside the sphere but inside the cube will NOT be removed. This means guests end up inside the water cavity.
**Current code:**
```python
# Line 388-390 (pocket.py)
distances = np.linalg.norm(guest_o_positions - center, axis=1)
outside_mask = distances >= radius
```
**Should be:**
```python
if config.pocket_shape == "sphere":
    distances = np.linalg.norm(guest_o_positions - center, axis=1)
    outside_mask = distances >= radius
elif config.pocket_shape == "cubic":
    dx = np.abs(guest_o_positions[:, 0] - center[0])
    dy = np.abs(guest_o_positions[:, 1] - center[1])
    dz = np.abs(guest_o_positions[:, 2] - center[2])
    outside_mask = ~((dx < radius) & (dy < radius) & (dz < radius))
```

### RISK-3: Hydrate Guest Atom Names Calculation (MEDIUM)
**What:** Lines 420-428 compute `processed_guest_atom_names` using `tiling_factor = tiled_guest_nmolecules // original_guest_nmolecules` and a remainder calculation. Slab.py was refactored (lines 500-528) to use `actual_guest_nmolecules = len(processed_guest_positions) // atoms_per_guest` which is more robust.
**Impact:** The pocket.py approach can produce wrong atom names count if tiling filtering removes molecules.
**Current code (pocket.py:421-428):**
```python
tiling_factor = tiled_guest_nmolecules // original_guest_nmolecules
processed_guest_atom_names = guest_atom_names * tiling_factor
remainder = tiled_guest_nmolecules - (tiling_factor * original_guest_nmolecules)
if remainder > 0:
    ...
```
**Slab.py approach (more robust, lines 506-522):**
```python
atoms_per_guest = len(guest_atom_names) // original_guest_nmolecules
actual_guest_nmolecules = len(processed_guest_positions) // atoms_per_guest
guest_pattern = guest_atom_names[:atoms_per_guest]
processed_guest_atom_names = guest_pattern * actual_guest_nmolecules
```

### RISK-4: BUG-04 — diversity_score Always 1.0 (LOW)
**What:** `diversity_score()` in `scorer.py:196-234` always returns 1.0 because all candidates have unique seeds.
**Impact on testing:** This doesn't affect pocket mode tests directly. Diversity scoring is a separate concern. However, if tests reference `InterfaceStructure.diversity_score`, it could be unreliable. The `InterfaceStructure` doesn't have a diversity_score field, so this is NOT a concern for pocket tests.

## Test Strategy

### Recommended Test Structure

```
tests/test_pocket_edge_cases.py
├── TestPocketShapeVariants
│   ├── test_sphere_shape_basic_invariants
│   ├── test_cubic_shape_basic_invariants
│   ├── test_cubic_has_more_water_than_sphere
│   └── test_invalid_shape_raises_error
├── TestPocketSizeExtremes
│   ├── test_minimum_diameter_sphere
│   ├── test_minimum_diameter_cubic
│   ├── test_large_diameter_near_box_size
│   └── test_very_large_pocket_thin_ice_shell
├── TestPocketBoxGeometry
│   ├── test_cubic_box_pocket
│   ├── test_rectangular_box_pocket
│   └── test_very_elongated_box_pocket
├── TestPocketStructuralInvariants
│   ├── test_water_atom_count_divisible_by_4
│   ├── test_atom_names_match_positions_length
│   ├── test_ice_outside_cavity
│   ├── test_water_inside_cavity
│   ├── test_all_positions_within_box
│   └── test_atom_ordering_ice_then_water_then_guests
├── TestPocketWithHydrate
│   ├── test_hydrate_sphere_basic
│   ├── test_hydrate_cubic_basic
│   ├── test_hydrate_guests_removed_from_cavity
│   ├── test_hydrate_guest_water_overlap
│   └── test_hydrate_with_ch4_guest
├── TestPocketOverlapRemoval
│   ├── test_ice_water_overlap_removal_preserves_divisibility
│   ├── test_guest_water_overlap_removal_preserves_divisibility
│   ├── test_water_outside_cavity_removal_preserves_divisibility
│   └── test_three_phase_overlap_removal_consistency
└── TestPocketValidationErrors
    ├── test_negative_diameter_rejected
    ├── test_diameter_exceeds_box_rejected
    ├── test_zero_diameter_rejected
    └── test_unknown_shape_rejected
```

### Test Approach

1. **Mock candidates only** — No GenIce2 dependency. Use `create_mock_ice_candidate()` and `create_mock_hydrate_candidate()` from test_interface_modes_audit.py (or enhanced versions).
2. **Structural invariant focus** — Every test verifies one or more invariants: atom count divisibility, positions-within-bounds, atom_names/positions consistency, cavity containment, etc.
3. **Parameterized where possible** — Use `pytest.mark.parametrize` for shape × diameter × box combinations.
4. **Deterministic** — Fixed seed, fixed candidate → reproducible results.
5. **No performance tests** — Performance is already verified in MED-04 resolved tests.

### Key Invariants to Test

| Invariant | Description | Check |
|-----------|-------------|-------|
| INV-1 | Water atom count divisible by 4 | `result.water_atom_count % 4 == 0` |
| INV-2 | Ice atom count divisible by 3 (or 4 for hydrate) | `result.ice_atom_count % atoms_per_mol == 0` |
| INV-3 | Atom names match positions length | `len(result.atom_names) == len(result.positions)` |
| INV-4 | All positions within box | `all pos >= 0 and pos < box_dims` |
| INV-5 | Ice molecules outside cavity | `all ice_O dist >= radius (sphere) or |dx|>=r or ... (cubic)` |
| INV-6 | Water molecules inside cavity | `all water_O dist < radius (sphere) or |dx|<r and ... (cubic)` |
| INV-7 | Guest molecules outside cavity | `all guest dist >= radius (sphere)` — **NOTE: cubic shape bug here** |
| INV-8 | Atom ordering: ice, water, guests | `result.positions[:ice_atom_count]` are ice atoms, etc. |
| INV-9 | Mode field | `result.mode == "pocket"` |
| INV-10 | Cell matrix is diagonal | `result.cell` is `np.diag([adjusted_x, adjusted_y, adjusted_z])` |
| INV-11 | Total atoms = ice + water + guest | `len(positions) == ice_atom_count + water_atom_count + guest_atom_count` |

## Mock/Stub Needs

### No External Mocking Required

The pocket mode tests do NOT need to mock:
- **GenIce2** — We use mock `Candidate` objects with fixed positions
- **Water template** — `fill_region_with_water()` loads `tip4p.gro` from `data/` — this is a bundled file, always available
- **IAPWS** — `water_density_gcm3()` calls IAPWS95 — this is a dependency, always available in test env

### Mock Candidate Factories Needed

1. **`create_mock_ice_candidate(n_molecules, cell_dim)`** — Simple cubic ice with O,H,H pattern
2. **`create_mock_ice_candidate_realistic(n_molecules)`** — Ice Ih-like with proper density (~0.917 g/cm³)
3. **`create_mock_hydrate_candidate(n_water, n_guest, guest_type)`** — TIP4P water + Me/CH4 guests
4. **`create_mock_candidate_positions_in_box(n_molecules, box_dims)`** — Pre-positioned in box to avoid tiling artifacts

These can reuse/adapt the factories from `test_interface_modes_audit.py` with enhancements for:
- Configurable cell dimensions (not just 0.9 nm)
- Configurable atom patterns (ice vs TIP4P)
- More realistic positions (not just simple cubic)
- Guest type selection (Me, CH4, THF)

## Fixtures Needed

### Shared Fixtures (conftest.py or in-file)

```python
@pytest.fixture
def ice_candidate():
    """Standard Ice Ih mock candidate for pocket tests."""
    return create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)

@pytest.fixture
def hydrate_candidate():
    """Standard hydrate mock candidate with Me guests."""
    return create_mock_hydrate_candidate(n_water=32, n_guest=4, guest_type="Me")

@pytest.fixture
def standard_pocket_config():
    """Standard pocket config: 3×3×3 nm box, 1.0 nm diameter, sphere."""
    return InterfaceConfig(
        mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
        seed=42, pocket_diameter=1.0, pocket_shape="sphere"
    )
```

### Parameterized Fixtures

```python
# Shape variants
@pytest.fixture(params=["sphere", "cubic"])
def pocket_shape(request):
    return request.param

# Size variants
@pytest.fixture(params=[0.5, 1.0, 2.0, 4.0])
def pocket_diameter(request):
    return request.param
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fill entire box with water, then filter | Fill bounding box of cavity only | MED-04 (resolved) | 10-100× performance improvement |
| No guest-water overlap check in pocket | Guest-water overlap detection added | Debug resolved session | Prevents guest-water clashes |
| Slab-only FRAG-02 assertions | Pocket has NO assertions | Current state | Pocket missing safety checks |

**Deprecated/outdated:**
- The debug test `test_med04_pocket_performance.py` should be migrated to main test suite (it's currently in `.planning/debug/resolved/`)

## Open Questions

1. **Cubic guest removal bug:** Should we file this as a bug to fix, or just document it in the test? The guest removal in pocket.py (line 388-390) uses sphere distance for cubic pockets. This is a real bug but may not cause issues if no one uses cubic + hydrate together.

2. **Guest atom names calculation:** Pocket.py uses a different (less robust) approach than slab.py for computing `processed_guest_atom_names`. Should we refactor pocket.py to match slab.py's approach, or just test that the current approach works?

3. **Minimum viable pocket diameter:** What's the smallest diameter that can produce at least 1 water molecule? This depends on the water template cell size (~1.87 nm) and the tiling algorithm. A pocket of 0.5 nm diameter → 0.5 nm fill region → likely produces 0 molecules after filtering.

4. **Non-spherical pocket parameter:** The current code only supports "sphere" and "cubic". Should we consider "ellipsoid" or "cylinder" as future shapes? The test should be structured to make adding shapes easy.

## Sources

### Primary (HIGH confidence)
- `quickice/structure_generation/modes/pocket.py` — Full algorithm read, all 559 lines
- `quickice/structure_generation/overlap_resolver.py` — Full overlap detection/removal read, all 218 lines
- `quickice/structure_generation/water_filler.py` — Full tiling/filling read, all 687 lines
- `quickice/structure_generation/types.py` — Full data types read, all 718 lines
- `quickice/structure_generation/interface_builder.py` — Full validation read, all 354 lines
- `quickice/structure_generation/modes/slab.py` — Full comparison read, all 641 lines
- `quickice/structure_generation/modes/piece.py` — Full comparison read, all 385 lines
- `quickice/utils/molecule_utils.py` — Full guest atom counting read, all 108 lines

### Secondary (MEDIUM confidence)
- `tests/test_interface_modes_audit.py` — Existing pocket tests, mock factories
- `tests/test_overlap_removal_invariants.py` — FRAG-02 invariant tests
- `tests/test_atom_names_filtering.py` — Atom names filtering tests
- `.planning/debug/resolved/apply-slab-fixes-to-pocket.md` — Guest-water overlap fix history
- `.planning/debug/resolved/test_med04_pocket_performance.py` — Performance optimization tests
- `.planning/codebase/ISSUES_BY_FILE.md` — BUG-04 issue documentation

## Metadata

**Confidence breakdown:**
- Code map: HIGH — All source files read directly
- Algorithm walkthrough: HIGH — Traced every step of assemble_pocket()
- Edge cases: HIGH — Identified from code analysis, not guessing
- Risk areas: HIGH — Verified by reading actual code
- Test strategy: HIGH — Based on existing test patterns and identified gaps
- Pitfalls (cubic guest removal bug): MEDIUM — Inferred from code; needs runtime verification

**Research date:** 2026-05-22
**Valid until:** 2026-06-22 (stable codebase, 30 days)
