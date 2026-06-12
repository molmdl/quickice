# Domain Pitfalls: Flexible Interface Construction

**Domain:** Ice-water interface construction + GROMACS MD simulation
**Researched:** 2026-06-12
**Overall confidence:** HIGH (code-grounded; all pitfalls traced to actual source code)

---

## Executive Summary

This document catalogs the technical pitfalls for implementing three feasible flexible interface features in QuickIce: **asymmetric slab**, **crystal face selection**, and **ice + hydrate in same box**. Each pitfall is grounded in actual source code analysis of `gromacs_writer.py` (2000+ lines), `slab.py` (641 lines), `types.py` (722 lines), `interface_builder.py` (354 lines), and `moleculetype_registry.py` (166 lines).

The single most dangerous pitfall is **GROMACS `[molecules]` ordering violation** — the `.gro` file atom ordering MUST match the `[molecules]` section moleculetype order. Current code assumes exactly one ordering: SOL(ice+water) → guests. With ice+hydrate, the ordering becomes SOL(ice) → SOL(hydrate-water) → SOL(liquid-water) → guests, and GROMACS will crash if consecutive SOL molecules from different sources aren't grouped correctly.

The second most dangerous pitfall is **periodicity mismatch at ice-hydrate boundaries** — ice Ih and sI hydrate have fundamentally different lattice parameters (0.45 nm vs 1.2 nm), requiring LCM-like box dimensions that may be impractically large.

---

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: GROMACS `[molecules]` Section Ordering Violation

**What goes wrong:** GROMACS requires that in the `.gro` file, all atoms belonging to a single `[molecules]` entry appear **contiguously**. The `[molecules]` section defines how many consecutive atoms belong to each moleculetype. If ice SOL, hydrate SOL, and liquid SOL are interleaved (rather than grouped), GROMACS will interpret wrong atoms as wrong molecule types → simulation crashes at `grompp`.

**Why it happens:** Current `write_interface_top_file()` (gromacs_writer.py:947-1053) writes:
```
[molecules]
SOL          {ice_nmolecules + water_nmolecules}
```
This works because all SOL molecules (ice + water) are contiguous in the `.gro` file — ice atoms come first (lines 682-742), then water atoms (lines 744-758). With ice+hydrate, we would have THREE separate SOL groups that all share the same moleculetype "SOL":
1. Ice framework SOL (3→4 atom expanded)
2. Hydrate framework SOL (4-atom native TIP4P)
3. Liquid water SOL (4-atom from template)

**Consequences:** `grompp` crashes with "Atom X does not belong to moleculetype Y" because atom counts don't match molecule boundaries. This is a **silent data corruption** — the file looks valid but GROMACS misinterprets atom assignments.

**Prevention:** Two approaches (RECOMMENDED: approach A):
- **Approach A (simplest):** Keep all SOL molecules as a SINGLE contiguous group in `.gro` and a single `SOL {total}` in `[molecules]`. Since ALL water is normalized to TIP4P-ICE at export, this is valid. Order: ice SOL → hydrate SOL → liquid SOL → guests. This is what the current code already does — just extend it to include the hydrate SOL in the ice block.
- **Approach B (avoid):** Split into separate moleculetypes: `SOL_ICE`, `SOL_HYD`, `SOL_WAT`. This requires custom `.itp` files for each and breaks force field compatibility (different atomtypes for identical water model = wrong physics).

**Detection:** Run `grompp -f null.mdp -c out.gro -p out.top` on every export. If it fails, the ordering is wrong. Add this as a validation step in export tests.

**Source:** gromacs_writer.py:947-1053, GROMACS documentation (HIGH confidence)

### Pitfall 2: Periodicity Mismatch at Ice-Hydrate Boundaries

**What goes wrong:** Ice Ih has unit cell a≈0.45 nm, b≈0.78 nm (GenIce2 convention for 1h). sI hydrate has a≈1.20 nm cubic. For both structures to tile continuously in the same box with PBC, box dimensions must be integer multiples of BOTH lattice parameters. The LCM of 0.45 and 1.20 is 3.60 nm (8×ice_a = 3×hydrate_a), which is large but feasible. However, the mismatch in Z direction creates a structurally disordered boundary that cannot be "fixed" by overlap removal alone.

**Why it happens:** `round_to_periodicity()` (water_filler.py) rounds dimensions to multiples of the ice cell. But with TWO different cells, there is no single periodicity. Current code in `assemble_slab()` (slab.py:208-210) calls `round_to_periodicity(config.box_x, ice_cell_dims[0])` — this works for single-lattice but NOT for dual-lattice.

**Consequences:**
1. Box X/Y dimensions that are multiples of ice cell but NOT hydrate cell → gaps in hydrate PBC
2. Box X/Y dimensions that are multiples of hydrate cell but NOT ice cell → gaps in ice PBC
3. If we round to LCM, box dimensions may be 2-3× what the user requested → many more molecules → much slower generation + simulation

**Prevention:**
- Compute box dimensions as LCM of both lattice parameters (separately for X, Y, Z)
- Inform user of dimension adjustments in the report (current code already has this pattern)
- Accept that the ice-hydrate boundary region will have ~1 unit cell of structural disorder (this is physically realistic — real ice-hydrate interfaces are disordered)

**Detection:** Validate that `box_x % ice_a < epsilon AND box_x % hydrate_a < epsilon`. If not, warn and auto-adjust.

**Source:** slab.py:206-261, water_filler.py `round_to_periodicity()` (HIGH confidence from code)

### Pitfall 3: Dual MW Virtual Site Computation for Mixed-Source SOL

**What goes wrong:** In the current export, ice molecules come from GenIce2 with 3 atoms (O, H, H) and the MW virtual site is computed at export time (gromacs_writer.py:711). Hydrate molecules come from GenIce2 with 4 atoms (OW, HW1, HW2, MW) — MW already exists. When ice and hydrate SOL are mixed in the same `.gro` file, the export code must handle BOTH cases in the same write loop. If it treats a hydrate 4-atom molecule as a 3-atom ice molecule, it skips the MW and shifts all subsequent atom indices by 1 → total corruption.

**Why it happens:** Current `write_interface_gro_file()` detects `atoms_per_ice_mol` from the FIRST ice region atom name (gromacs_writer.py:692-693):
```python
has_ow_in_ice = "OW" in ice_region_atom_names
atoms_per_ice_mol = 4 if has_ow_in_ice else 3
```
This works when ALL ice atoms are from the same source. With ice+hydrate, the ice region may contain BOTH "O" (from pure ice) and "OW" (from hydrate framework), requiring per-molecule detection rather than per-region.

**Consequences:** If a hydrate water molecule (4 atoms) is read as ice (3 atoms), the MW atom is treated as the next molecule's oxygen → all subsequent atoms are shifted by 1 → total coordinate corruption → GROMACS crashes on energy minimization.

**Prevention:**
- Store per-molecule metadata in `molecule_index` (already exists: `MoleculeIndex.mol_type`)
- In the export loop, check `mol_type` for each molecule: "ice" → expand 3→4, "water_hydrate" → pass 4 atoms through, "water_liquid" → pass 4 atoms through
- All three produce the same TIP4P-ICE format output — just different input atom counts

**Detection:** After export, verify total atoms = (ice_nmol × 4) + (hydrate_water_nmol × 4) + (liquid_water_nmol × 4) + (guest_atoms). Add this as a post-export assertion.

**Source:** gromacs_writer.py:688-743, types.py:39-43 (HIGH confidence from code)

### Pitfall 4: Asymmetric Slab Validation Formula Breaks

**What goes wrong:** Current `validate_interface_config()` (interface_builder.py:119-142) enforces:
```python
expected_z = 2 * config.ice_thickness + config.water_thickness
```
For asymmetric slab (single ice + water), the formula should be:
```python
expected_z = config.ice_thickness + config.water_thickness
```
If the validation isn't updated, every asymmetric slab configuration is rejected with a confusing error message.

**Why it happens:** The formula is hardcoded for symmetric slab only. The new `InterfaceConfig` must encode whether the slab is symmetric (2 ice layers) or asymmetric (1 ice layer).

**Consequences:** Asymmetric slab generation is impossible — validation rejects all configurations before generation starts.

**Prevention:**
- Add `symmetric: bool = True` field to `InterfaceConfig` (or derive from `layer_order`)
- Update validation to check: `box_z = ice_thickness + water_thickness` for asymmetric, `box_z = 2*ice_thickness + water_thickness` for symmetric
- Backward compatibility: if `symmetric` not set, derive from mode (default = symmetric for "slab")

**Detection:** Unit test that attempts asymmetric slab generation → should NOT raise InterfaceGenerationError

**Source:** interface_builder.py:119-142 (HIGH confidence from code)

---

## Moderate Pitfalls

Mistakes that cause delays or technical debt.

### Pitfall 5: Guest Molecule Residue Naming Collision Between Ice and Hydrate Sources

**What goes wrong:** Current `MoleculetypeRegistry` uses suffixes `_H` (hydrate) and `_L` (liquid) to distinguish guest molecules from different sources (e.g., `CH4_H` vs `CH4_L`). With ice+hydrate in same box, the hydrate guests get `CH4_H`. But if the user also adds solutes via the solute tab, the solutes get `CH4_L`. The `.top` file must include BOTH `ch4_hydrate.itp` and `ch4_liquid.itp`, each defining a DIFFERENT `[moleculetype]` name (`CH4_H` vs `CH4_L`). If both itp files define the same moleculetype name, GROMACS errors on duplicate moleculetype definitions.

**Why it happens:** The registry pattern (moleculetype_registry.py) was designed for the current workflow where only ONE guest source exists per export. With ice+hydrate, we have TWO potential guest sources in the same box.

**Consequences:** `grompp` error: "Duplicate moleculetype definition for CH4" or atomtype conflicts if the two ITP files define incompatible atomtypes.

**Prevention:** The existing `_H`/`_L` suffix pattern handles this correctly. The key is ensuring:
1. `ch4_hydrate.itp` defines `[moleculetype] CH4_H` 
2. `ch4_liquid.itp` defines `[moleculetype] CH4_L`
3. Both are `#include`d in the `.top` file
4. The `[molecules]` section uses the correct suffix for each guest group

**Detection:** Check that all ITP files bundled with export have unique `[moleculetype]` names. Verify no duplicates.

**Source:** moleculetype_registry.py:35-166, gromacs_writer.py:990-1052 (HIGH confidence)

### Pitfall 6: Atomtype Deduplication Failure with Dual GAFF Sources

**What goes wrong:** With ice+hydrate in same box, the `.top` file needs atomtypes for:
- TIP4P-ICE water (OW_ice, HW_ice, MW)
- CH4 guests (c3, hc from GAFF2) — if present in hydrate
- THF guests (os, c5, hc, h1 from GAFF2) — if present in hydrate
- CH4 solutes (c3, hc from GAFF2) — if user adds liquid solutes
- Custom molecule atomtypes — if present

Current code in `write_ion_top_file()` (gromacs_writer.py:1693-1758) has a deduplication mechanism using `_written_atomtypes` set. But with dual GAFF sources (hydrate guests AND liquid solutes of the same type), the same atomtype names (c3, hc) appear in both the hydrate ITP and the liquid ITP. If both define `c3` with different LJ parameters (even slightly different due to model tuning), GROMACS uses the FIRST definition and silently ignores the second → wrong physics.

**Why it happens:** The `_H`/`_L` ITP separation creates distinct `[moleculetype]` names but does NOT prevent atomtype name collisions. GAFF2 `c3` is the same atomtype whether in `ch4_hydrate.itp` or `ch4_liquid.itp`. The deduplication in the `.top` file's `[atomtypes]` section is supposed to handle this, but it only deduplicates what's WRITTEN in the `.top` — it doesn't check the ITP files' internal `[atomtypes]` sections.

**Prevention:** The current approach of commenting out `[atomtypes]` in ITP files (gromacs_writer.py:311-355 `comment_out_atomtypes_in_itp`) already handles this. All atomtypes are centralized in the `.top` file. Ensure this function is called for ALL bundled ITP files (hydrate AND liquid).

**Detection:** Verify that every ITP file bundled with export has `[atomtypes]` commented out. Check no duplicate atomtype definitions remain.

**Source:** gromacs_writer.py:311-355, 1250-1290 (HIGH confidence from code)

### Pitfall 7: Crystal Face Selection Produces Triclinic Box Vectors

**What goes wrong:** Using GenIce2's non-diagonal `reshape` matrix (for crystal face rotation, e.g., `one[hh]` basal face on Z) can produce a non-orthogonal supercell. The current slab assembly code (slab.py:606) always outputs an orthogonal cell:
```python
cell = np.diag([adjusted_box_x, adjusted_box_y, adjusted_box_z])
```
If the crystal axes have been rotated (non-diagonal reshape), the ice positions in the box are defined by a triclinic cell matrix, but the output cell is forced to be orthogonal → positions don't match the box → atoms outside the box → GROMACS wrapping artifacts.

**Why it happens:** `tile_structure()` uses `cell_matrix` for triclinic-aware tiling (slab.py:275-276), but the final `InterfaceStructure.cell` is forced to diagonal. This works for the current default `1h` (where the effective tiling is orthogonal), but breaks for rotated crystal faces.

**Consequences:** Ice molecules positioned using rotated lattice vectors but output with orthogonal box → atoms wrap incorrectly → visible artifacts at PBC boundaries → GROMACS energy spikes at box edges.

**Prevention:**
- **Approach A (recommended for v5.0):** Restrict crystal face selection to options that produce orthogonal supercells. GenIce2 `one[hh]` with diagonal reshape produces orthogonal cells. Document which face options produce orthogonal vs triclinic cells.
- **Approach B (future):** Output triclinic box vectors (GRO format supports this: 9 values on last line). This is already partially supported — `write_interface_gro_file()` writes all 9 cell values (gromacs_writer.py:816-820).

**Detection:** After generation, check `is_cell_orthogonal(candidate.cell)`. If not orthogonal, warn user that triclinic output is needed.

**Source:** slab.py:270-277, 599-606, cell_utils.py, gromacs_writer.py:816-820 (HIGH confidence from code)

### Pitfall 8: Overlap Detection Across Layer Boundaries in Layer Assembly

**What goes wrong:** When assembling a multi-layer structure (ice → hydrate → water), each layer is tiled independently and then stacked. The overlap detection (`detect_overlaps()`) currently checks ice-water overlaps (slab.py:350-359) and guest-water overlaps (slab.py:537-563). With ice+hydrate, there are THREE overlap checks needed:
1. Ice ↔ liquid water
2. Hydrate framework ↔ liquid water
3. Ice ↔ hydrate framework (at the ice-hydrate boundary)

Check #3 is NEW and currently doesn't exist. At the ice-hydrate boundary, water molecules from both structures may overlap because the tiling doesn't account for the other structure's molecules.

**Why it happens:** Current code does overlap detection in two passes:
- Pass 1: combined_ice (bottom+top) ↔ water (slab.py:350-359)
- Pass 2: guests ↔ remaining water (slab.py:537-563)

With ice+hydrate, the "combined ice" would need to be "combined ice + hydrate framework", but the overlap between ice and hydrate at their shared boundary is never checked. Both are solid phases that should be contiguous — but if their tiling leaves a gap or creates overlap, there's no detection.

**Prevention:**
- After assembling all solid layers (ice + hydrate), run overlap detection between ALL solid oxygen positions and ALL liquid water oxygen positions
- Do NOT check ice ↔ hydrate overlaps (they should be contiguous, not overlapping — any gap between them is filled by water, any overlap means the layers overlap)
- Actually, ice-hydrate overlap at the boundary SHOULD be checked: if the hydrate slab extends into the ice region, hydrate framework molecules overlap with ice molecules → structural corruption. Detect this and remove from the OVERLAPPING side.

**Detection:** After layer assembly, verify that no two solid-phase oxygen atoms are within `overlap_threshold` of each other (except within the same layer, where they're crystal-structure neighbors).

**Source:** slab.py:347-383, overlap_resolver.py:14-60 (HIGH confidence from code)

### Pitfall 9: Ice-Hydrate Density Mismatch Creates Void or Overlap at Boundary

**What goes wrong:** Ice Ih density ≈ 0.92 g/cm³. CH₄-sI hydrate density ≈ 0.91 g/cm³ (very close!). But when both are tiled to fill the same box, their different lattice parameters mean different water densities in each region. The `density` parameter in GenIce2 (STACK.md:87-93) scales the ENTIRE cell uniformly. If ice is generated at 0.92 g/cm³ and hydrate at 0.93 g/cm³ (slight difference), the resulting cell dimensions differ slightly, and stacking them creates a density discontinuity at the boundary.

**Why it happens:** Each GenIce2 call scales its cell independently based on `density`. When the two scaled cells are placed adjacent in Z, their XY dimensions may differ slightly, creating a mismatch at the shared boundary.

**Consequences:** Minor density artifact at the ice-hydrate boundary (~1-2% mismatch). This is physically realistic (real ice-hydrate interfaces have a disordered transition region) but may confuse users who expect perfect lattice continuity.

**Prevention:**
- Generate BOTH ice and hydrate at the SAME density (0.92 g/cm³ for ice-like conditions)
- Accept that the boundary will have a ~0.5 nm transition region of structural disorder
- This is actually a FEATURE, not a bug — real ice-hydrate interfaces are disordered

**Detection:** Compare ice and hydrate densities in the generation report. Warn if mismatch > 5%.

**Source:** STACK.md:87-93, FEATURES.md:120-126 (MEDIUM confidence — density values from domain knowledge)

### Pitfall 10: Asymmetric Slab with Vacuum Gap — GROMACS PBC Handling

**What goes wrong:** For asymmetric slab (ice on bottom, water on top), many MD studies add a vacuum gap above the water to prevent interaction through PBC in Z. This requires either:
1. `pbc = nil` in GROMACS mdp file (2D PBC: xy periodic, z non-periodic)
2. A vacuum slab thick enough that the Z interaction is negligible

Current QuickIce exports with 3D PBC (standard for all modes). If the user wants 2D PBC for asymmetric slab, the `.mdp` file needs `pbc = nil nil nil` or `pbc = xy xy nil`, and GROMACS requires `nwall = 2` with wall parameters. QuickIce doesn't generate `.mdp` files.

**Why it happens:** The simplest asymmetric slab is just `box_z = ice_thickness + water_thickness` with 3D PBC. Under 3D PBC, this creates `...|ice|water|ice|water|...` which is a symmetric slab again. The "asymmetric" part is only meaningful with 2D PBC or a vacuum gap.

**Consequences:** Without vacuum or 2D PBC, the "asymmetric" slab IS the current symmetric slab — no new behavior. User gets a structure that looks asymmetric but is actually periodic.

**Prevention:**
- **Approach A (recommended for v5.0):** Allow `box_z = ice_thickness + water_thickness` and document that under 3D PBC this creates a symmetric structure. The user adds vacuum manually by increasing `box_z` beyond `ice_thickness + water_thickness`.
- **Approach B (future):** Add a "vacuum gap" parameter to `InterfaceConfig`. Generate the gap as empty Z-space. Set `pbc-z` to nil in the export (but this requires `.mdp` generation or instructions to user).
- **Approach C (simplest):** Document that "asymmetric slab" in QuickIce means one ice layer + water. The ice-water interface is the same as in symmetric slab, but you only have ONE interface (reducing computational cost). Under 3D PBC, the structure still repeats, but the simulation has fewer unique atoms.

**Detection:** After generation, check if `box_z > 2*ice_thickness + water_thickness`. If so, the extra Z-space is either vacuum or needs explanation.

**Source:** interface_builder.py:119-142, GROMACS documentation on PBC (HIGH confidence)

---

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 11: GRO Format 5-Character Residue Name Limit

**What goes wrong:** GROMACS `.gro` format limits residue names to 5 characters. Current hydrate guests use `CH4_H` (5 chars) and `THF_H` (5 chars) — right at the limit. With ice+hydrate+liquid, we might need `CH4_L` (5 chars) — also at limit. Any future molecule naming scheme (e.g., `CUSTO_H`) risks exceeding 5 chars.

**Why it happens:** GRO format is fixed-width from GROMACS 4.x era. No workaround.

**Consequences:** Residue names longer than 5 chars are silently truncated → `grompp` error when truncated name doesn't match any `[moleculetype]`.

**Prevention:** Enforce 5-char limit in `MoleculetypeRegistry`. Current code already truncates (gromacs_writer.py:1548, 1592, 2035). Ensure all registration paths check this.

**Detection:** Add assertion: `len(registered_name) <= 5` in registry.

**Source:** gromacs_writer.py:1548, 1592 (HIGH confidence)

### Pitfall 12: Multiple GenIce2 Calls with Different Random Seeds

**What goes wrong:** For ice+hydrate, QuickIce calls GenIce2 twice — once for ice, once for hydrate. Each call uses a different random seed, producing different hydrogen bond (HB) network realizations. The ice HB network and hydrate HB network are independently consistent, but at the ice-hydrate boundary, there's no guaranteed HB connectivity. Water molecules at the boundary may have dangling hydrogen bonds pointing into the gap.

**Why it happens:** GenIce2 generates an entire HB network per call. It cannot generate a "half-network" or "boundary-matched" network. This is a fundamental limitation of the single-lattice design.

**Consequences:** The ice-hydrate boundary has a disordered HB network. This is physically realistic (real interfaces are disordered) but means the initial structure will need energy minimization before production MD. Users must be warned to run `grompp + mdrun -deffnm em` before production runs.

**Prevention:** Document that ice-hydrate structures require energy minimization. This is already standard practice for MD — no special handling needed.

**Detection:** No automated detection possible. This is expected behavior.

**Source:** STACK.md:152-169 (HIGH confidence — GenIce2 design limitation)

### Pitfall 13: UI Layer Validation for Mixed Source Selection

**What goes wrong:** With ice+hydrate mode, the UI needs TWO source selections (one for ice, one for hydrate). The current `InterfacePanel` (interface_panel.py) has a SINGLE source dropdown. Adding a second source requires careful layout changes. If both sources are "ice" or both are "hydrate", the user gets a meaningless configuration (ice-ice interface or hydrate-hydrate with different seeds).

**Why it happens:** The UI was designed for single-source interface construction.

**Consequences:** Confusing UI. User selects two ice sources and gets a regular ice-water-ice sandwich (not the ice+hydrate they expected).

**Prevention:**
- Use `QStackedWidget` to show mode-specific controls (already imported in interface_panel.py:17)
- For "ice+hydrate" mode, show two source dropdowns with labels "Ice source" and "Hydrate source"
- Validate that the two sources are DIFFERENT types (one ice, one hydrate)
- For "asymmetric slab" mode, show single source dropdown + layer ordering toggle

**Detection:** Validate source types before generation. Raise error if both sources are the same type.

**Source:** interface_panel.py:17-19, 80-100 (HIGH confidence from code)

### Pitfall 14: Backward Compatibility Break in InterfaceConfig

**What goes wrong:** Adding new fields to `InterfaceConfig` (e.g., `layer_order`, `symmetric`, `candidates`) could break existing code that uses `InterfaceConfig.from_dict()`. The current `from_dict()` (types.py:196-219) uses `.get()` with defaults for optional fields, which is backward-compatible. But if a NEW required field is added without a default, old configurations crash.

**Why it happens:** Adding fields to a dataclass without defaults makes them required. Any code constructing `InterfaceConfig` without the new field raises `TypeError: __init__ missing required argument`.

**Prevention:**
- ALL new fields must have defaults (use `field(default=...)` or `=None`)
- `from_dict()` must use `.get()` with defaults for new fields
- Add field `layer_order: list[str] = field(default_factory=lambda: ["ice", "water", "ice"])` for backward compat
- Add field `symmetric: bool = True` for backward compat

**Detection:** Unit test that constructs `InterfaceConfig(mode="slab", box_x=5, ...)` with only old fields → should not raise TypeError.

**Source:** types.py:152-219 (HIGH confidence from code)

### Pitfall 15: Generation Performance with Multiple GenIce2 Calls

**What goes wrong:** For ice+hydrate, QuickIce calls GenIce2 twice. Each call involves:
- Lattice import
- Supercell calculation
- HB network generation (most expensive step)
- Formatting

Current single-call generation takes ~2-10 seconds depending on system size. Two calls doubles this. For large systems (>5000 molecules per call), the wait time becomes noticeable (>20 seconds).

**Why it happens:** GenIce2 HB network generation is O(N²) for the graph search.

**Consequences:** User waits longer. The GUI freezes during generation (current pattern: QThread worker, so GUI stays responsive but progress bar doesn't show per-layer progress).

**Prevention:**
- Show per-layer progress in the UI ("Generating ice structure... 50% / Generating hydrate structure... 0%")
- Current worker pattern (QThread) already handles background execution
- This is a UX concern, not a correctness concern

**Detection:** Measure generation time with multiple GenIce2 calls. If >30 seconds, add a warning.

**Source:** STACK.md:152-169 (MEDIUM confidence — performance estimation)

---

## GROMACS Export Complications

### Current Export Pipeline

The current GROMACS export pipeline (as traced from actual code):

1. **Generation** → `InterfaceStructure` with fields: `positions`, `atom_names`, `cell`, `ice_atom_count`, `water_atom_count`, `ice_nmolecules`, `water_nmolecules`, `guest_atom_count`, `guest_nmolecules`, `molecule_index`

2. **Atom ordering convention** (after commit 90afe86):
   - `positions[0:ice_atom_count]` = ice atoms (3-atom or 4-atom per molecule)
   - `positions[ice_atom_count:ice_atom_count+water_atom_count]` = water atoms (4-atom TIP4P)
   - `positions[ice_atom_count+water_atom_count:]` = guest atoms (variable)

3. **GRO file writing** (`write_interface_gro_file`):
   - Ice molecules: 3→4 atom expansion (compute MW virtual site)
   - Water molecules: pass through 4 atoms, recompute MW from OW/HW1/HW2
   - Guest molecules: detect type, reorder atoms to match ITP canonical order, write with hydrate residue name

4. **TOP file writing** (`write_interface_top_file`):
   - `[defaults]`: comb-rule 2, fudgeLJ 0.5, fudgeQQ 0.8333 (TIP4P-ICE/Amber compatible)
   - `[atomtypes]`: OW_ice, HW_ice, MW + GAFF2 guest types if present
   - `#include "tip4p-ice.itp"` — water topology
   - `#include "{guest}_hydrate.itp"` — guest topology (if guests present)
   - `[system]`: descriptive name
   - `[molecules]`: `SOL {ice+water_count}`, then `CH4_H/THF_H {guest_count}`

5. **ITP bundling**:
   - `tip4p-ice.itp` — copied from `quickice/data/`
   - `{guest}_hydrate.itp` — copied from `quickice/data/`, with `[atomtypes]` commented out
   - `ion.itp` — generated from `gromacs_ion_export.py` (if ions present)
   - Custom molecule ITPs — copied with `[atomtypes]` commented out

### Complications from Asymmetric Slab

**Vacuum gap handling:**
- Current code: `box_z = 2*ice_thickness + water_thickness` (interface_builder.py:125)
- Asymmetric slab: `box_z = ice_thickness + water_thickness` under 3D PBC
- To create true single interface: need vacuum gap → `box_z = ice_thickness + water_thickness + vacuum_thickness`
- GROMACS `.mdp` needs `pbc-z = nil` for 2D PBC → QuickIce doesn't generate `.mdp`
- **Recommendation:** Just allow `box_z = ice_thickness + water_thickness` and document that 3D PBC makes this periodic. Let user add vacuum manually.

**Residue ordering:**
- Same as current: ice SOL → water SOL → (no top ice SOL)
- No change needed for GROMACS export — SOL count is still contiguous

**Box vectors:**
- Same orthogonal diagonal cell as current
- No triclinic complications

### Complications from Ice + Hydrate

**Dual SOL types:**
- Ice SOL (3→4 atom expansion) and hydrate SOL (4-atom native) are BOTH "SOL" moleculetype
- GROMACS requires all SOL atoms contiguous in `.gro` file
- **Solution:** Keep ordering: ice SOL → hydrate SOL → liquid water SOL → guests
- All use same `#include "tip4p-ice.itp"` — same water model

**Guest molecule placement:**
- Hydrate guests go IN the hydrate layer (not in water region)
- Current slab.py already handles this pattern (slab.py:384-530 for hydrate guest tiling)
- With ice+hydrate, guest tiling applies only to the hydrate layer(s), not ice layers

**Molecule ordering in `.gro`:**
- Current: `[ice SOL] → [water SOL] → [guests]`
- With ice+hydrate: `[ice SOL] → [hydrate SOL] → [water SOL] → [hydrate guests]`
- All SOL entries collapse to single `SOL {total}` in `[molecules]`

**ITP bundling:**
- Same ITPs as current: `tip4p-ice.itp`, `{guest}_hydrate.itp`
- No new ITP files needed (hydrate guests already handled)
- Must ensure `comment_out_atomtypes_in_itp()` is called for all ITPs

### Complications from Crystal Face Selection

**Orientation and box vectors:**
- Default `1h` lattice: axes are exchanged (GenIce2 convention). Current QuickIce uses this → Z interface may be prismatic, not basal
- `one[hh]` lattice: basal face on Z. Produces different supercell shape
- Non-diagonal `reshape` → triclinic cell → must output triclinic GRO box vectors
- Current `slab.py:606` forces orthogonal cell → **MUST be updated** for non-diagonal reshape

**PBC handling:**
- With rotated crystal face, the tiling pattern changes
- `tile_structure()` already accepts `cell_matrix` for triclinic-aware tiling (slab.py:275-276)
- The issue is ONLY in the final cell output → needs triclinic support

---

## Risk Matrix

| Pitfall | Likelihood | Impact | Mitigation |
|---------|-----------|--------|-----------|
| P1: GROMACS `[molecules]` ordering | **HIGH** — will happen if not addressed first | **CRITICAL** — silent corruption | Use single SOL group; keep atom ordering contiguous |
| P2: Periodicity mismatch | **HIGH** — inevitable with ice+hydrate | **HIGH** — gaps at PBC or oversized boxes | Compute LCM dimensions; warn user of auto-adjustment |
| P3: Dual MW computation | **HIGH** — 3-atom vs 4-atom mixing | **CRITICAL** — total coordinate corruption | Use per-molecule mol_type detection in export loop |
| P4: Asymmetric validation formula | **MEDIUM** — easy to miss in code change | **HIGH** — blocks all asymmetric generation | Update InterfaceConfig + validation together |
| P5: Guest residue naming collision | **LOW** — existing `_H`/`_L` pattern handles it | **MEDIUM** — grompp crash if pattern breaks | Test dual-guest export explicitly |
| P6: Atomtype deduplication | **LOW** — comment_out_atomtypes handles it | **MEDIUM** — wrong physics if missed | Verify all ITPs have atomtypes commented |
| P7: Triclinic box vectors | **MEDIUM** — only for non-diagonal reshape | **HIGH** — PBC wrapping artifacts | Restrict v5.0 to orthogonal face options |
| P8: Cross-layer overlap detection | **MEDIUM** — boundary region is thin | **HIGH** — structural corruption at boundary | Add ice↔hydrate overlap check |
| P9: Density mismatch | **LOW** — 0.92 vs 0.91 is small | **LOW** — realistic boundary disorder | Generate both at same density |
| P10: Vacuum gap / 2D PBC | **MEDIUM** — users expect true asymmetric | **LOW** — just documentation | Document 3D PBC implications; manual vacuum |
| P11: 5-char residue name | **LOW** — current names fit | **LOW** — truncated name | Enforce 5-char limit in registry |
| P12: Different HB networks | **CERTAIN** — GenIce2 design | **LOW** — expected physics | Document need for energy minimization |
| P13: UI source selection | **MEDIUM** — new UI elements | **MEDIUM** — confusing UX | QStackedWidget + validation |
| P14: InterfaceConfig backward compat | **MEDIUM** — easy to forget defaults | **HIGH** — all existing configs break | All new fields with defaults |
| P15: Performance (dual GenIce2) | **CERTAIN** — twice the calls | **LOW** — just slower | Per-layer progress UI |

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|-----------|
| Asymmetric slab — InterfaceConfig change | P4: Validation formula break | Update `validate_interface_config()` and `InterfaceConfig` in same commit |
| Asymmetric slab — Assembly | P10: 3D PBC makes it periodic | Document; allow manual vacuum gap |
| Asymmetric slab — Export | P1: SOL ordering still works | No change needed — ice + water are still contiguous SOL |
| Crystal face — GenIce2 integration | P7: Triclinic cell from non-diagonal reshape | Restrict to orthogonal face options for v5.0 |
| Crystal face — UI exposure | P13: Dropdown for face selection | Simple combobox; no layout change needed |
| Ice+hydrate — Generation | P2: LCM box dimensions | Compute and report auto-adjustments |
| Ice+hydrate — Assembly | P8: Ice↔hydrate boundary overlaps | Add cross-layer overlap detection |
| Ice+hydrate — Export | P1: SOL ordering (3 sources) | Group all SOL atoms contiguously; single SOL count |
| Ice+hydrate — Export | P3: 3-atom vs 4-atom ice mixing | Per-molecule mol_type check in export loop |
| Ice+hydrate — Export | P5: Dual guest ITPs | Bundle both hydrate ITP; use _H/_L naming |
| All features — InterfaceConfig | P14: Backward compat break | All new fields with defaults; from_dict with .get() |

---

## Implementation Priority Order

Based on risk analysis, address pitfalls in this order:

1. **P3 (Dual MW computation)** — CRITICAL, will silently corrupt data. Fix FIRST in export pipeline.
2. **P1 (GROMACS [molecules] ordering)** — CRITICAL, but natural extension handles it if P3 is fixed.
3. **P4 (Asymmetric validation formula)** — HIGH, blocks asymmetric slab completely. Simple fix.
4. **P2 (Periodicity mismatch)** — HIGH, needs algorithm but well-understood math (LCM).
5. **P8 (Cross-layer overlap detection)** — HIGH, but can defer to testing phase.
6. **P14 (InterfaceConfig backward compat)** — HIGH impact, but easy to prevent with defaults.
7. **P7 (Triclinic box vectors)** — Restrict scope to avoid for v5.0.
8. Everything else — MEDIUM/LOW impact, address during implementation.

---

## Sources

| Source | Confidence | Notes |
|--------|------------|-------|
| `quickice/output/gromacs_writer.py` (2328 lines) | HIGH | Full file read; all export logic analyzed |
| `quickice/structure_generation/modes/slab.py` (641 lines) | HIGH | Full file read; all assembly logic analyzed |
| `quickice/structure_generation/types.py` (722 lines) | HIGH | Full file read; all data structures analyzed |
| `quickice/structure_generation/interface_builder.py` (354 lines) | HIGH | Full file read; all validation logic analyzed |
| `quickice/structure_generation/moleculetype_registry.py` (166 lines) | HIGH | Full file read; registry pattern analyzed |
| `quickice/structure_generation/overlap_resolver.py` | HIGH | Partial read; cKDTree overlap detection analyzed |
| `quickice/gui/export.py` (929 lines) | HIGH | Full file read; all GUI export handlers analyzed |
| `quickice/gui/hydrate_export.py` (192 lines) | HIGH | Full file read; hydrate export pattern analyzed |
| `.planning/research/future-ml/flexible-interface-construction/STACK.md` | HIGH | Wave 1 research; GenIce2 API analysis |
| `.planning/research/future-ml/flexible-interface-construction/FEATURES.md` | HIGH | Wave 1 research; feature categorization |
| GROMACS `[molecules]` ordering requirement | HIGH | Standard GROMACS convention; confirmed in grompp documentation |
| GROMACS triclinic box format | HIGH | 9-value box line in GRO format; already implemented in writer |
