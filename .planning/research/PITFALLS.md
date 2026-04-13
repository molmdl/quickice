# Domain Pitfalls

**Domain:** Molecule insertion into ice/interface structures (QuickIce v4.0)
**Researched:** 2026-04-14
**Context:** Adding Tab 2 (Molecules to Ice / hydrates) and Tab 4 (Insert to Liquid / NaCl ions + custom molecules) to existing QuickIce v3.5 system
**Overall confidence:** HIGH (based on direct codebase analysis + live GenIce2 API testing)

---

## Critical Pitfalls

Mistakes that cause rewrites, data corruption, or silent wrong results.

### Pitfall 1: GenIce2 Hydrate Guests Require Nested Dict, Not List

**What goes wrong:** The `guests` parameter to `GenIce.generate_ice()` expects a nested dict `{cagetype: {molecule_name: fraction}}`, NOT a list of molecule objects. Passing `guests=[methane_molecule]` raises `AttributeError: 'list' object has no attribute 'items'` — a cryptic error that doesn't explain the correct format.

**Why it happens:** GenIce2's API design is unconventional. The `guests` dict maps cage types (e.g., `"12"` for 12-hedron small cages, `"14"` for 14-hedron large cages in sI) to molecule-to-occupancy-fraction mappings. This is only discoverable by reading `genice2/genice.py` Stage7 source — it's NOT documented in GenIce2's README.

**Consequences:** Hydrate generation crashes with an unhelpful error. Developers waste time debugging the wrong thing (thinking the molecule plugin failed).

**Prevention:** Write a thin adapter function that translates QuickIce's user-facing API (select a molecule, specify occupancy) into GenIce2's dict format. Validate the guest dict structure before passing to GenIce.

**Detection:** Unit test that generates a hydrate with a guest molecule. If it crashes with `AttributeError: 'list' object has no attribute 'items'`, this pitfall was hit.

**Phase:** Phase 1 (Tab 2 — hydrate generation must work before any UI)

---

### Pitfall 2: Hydrate Lattice Names Are Case-Sensitive (Opposite Convention from Pure Ice)

**What goes wrong:** GenIce2 hydrate lattices use specific mixed-case names: `sI`, `sII`, `sH`, `CS1`, `CS2`, `CS4`. Using lowercase (`si`, `cs1`) or uppercase (`SI`) fails with `AssertionError: Nonexistent or failed to load the module`. This is the OPPOSITE convention from pure ice lattices which use lowercase (`ice1h`, `ice5`).

**Why it happens:** GenIce2's `safe_import()` resolves module names to Python files in `genice2/lattices/`. The hydrate files are literally named `sI.py`, `CS1.py`, etc. There's no case normalization.

**Consequences:** Hydrate generation fails silently. The error message ("Nonexistent module") doesn't hint at case sensitivity, leading developers to assume hydrate support is broken.

**Prevention:** Create a `HYDRATE_LATTICE_NAMES` mapping dict in `quickice/structure_generation/mapper.py`, similar to the existing `PHASE_TO_GENICE` mapping. Never expose GenIce2's raw lattice names to the UI. Verified available hydrate lattices: `sI`, `sII`, `sH`, `CS1`, `CS2`, `CS4`, `DOH`, `HS1`, `HS2`, `HS3`, `FAU`, `LTA`.

**Detection:** Test all hydrate lattice names in a unit test. Verify both the GenIce2 plugin loads AND the Lattice class instantiates.

**Phase:** Phase 1 (Tab 2 — must get names right before any generation works)

---

### Pitfall 3: Multi-Molecule-Type Topology Breaks the Single-SOL Convention

**What goes wrong:** The existing `write_interface_top_file()` uses a single `SOL` molecule type for ALL water molecules (ice + liquid combined). Adding ions (Na+, Cl-) and custom molecules requires MULTIPLE `[ moleculetype ]` sections in the `.top` file. Naively extending the existing writer produces invalid GROMACS topology that causes energy minimization failures.

**Why it happens:** GROMACS requires each distinct molecule type to have its own `[ moleculetype ]` section, `[ atoms ]` definition, and entry in `[ molecules ]`. Current code has ONE: `SOL` with TIP4P-ICE parameters. Ions need separate `NA` and `CL` sections. Custom molecules need user-defined sections.

**Consequences:** GROMACS rejects the topology file (`gmx grompp` fails). At worst, if atom types silently mismatch, the simulation runs with wrong force field parameters and produces garbage results.

**Prevention:** Refactor the GROMACS writer to accept a list of molecule specifications: `[(moltype_name, atom_count_per_mol, nmols, itp_source), ...]`. The `.top` file should `#include` TIP4P-ICE `.itp` for water, bundled ion `.itp` files for NaCl, and reference user-provided `.itp` files for custom molecules. Design this data structure BEFORE writing any Tab 4 code.

**Detection:** Run `gmx grompp` on exported topology with NaCl. If it fails with "Invalid topology" or "Unknown moleculetype", this pitfall was hit.

**Phase:** Phase 2 (Tab 4 — topology export for multi-molecule systems)

---

### Pitfall 4: Ion Insertion Replaces Ice Molecules, Not Just Water

**What goes wrong:** When inserting NaCl ions into the liquid phase, code must ONLY replace water molecules in the liquid region. If selection logic accidentally picks molecules from the ice region, it destroys the crystal structure and creates unphysical defects.

**Why it happens:** `InterfaceStructure` stores all atoms in a single flat array with `ice_atom_count` as the boundary marker. To replace a water molecule, code must: (1) start at index `>= ice_atom_count`, (2) select molecules at random from the liquid region, (3) remove ALL 4 atoms of that water molecule (OW, HW1, HW2, MW), (4) insert the ion at the removed molecule's center-of-mass. If step (1) uses `<` instead of `>=`, or if `atoms_per_molecule` is wrong (3 vs 4), ice molecules get destroyed.

**Consequences:** Crystal structure corruption. The interface is no longer physically valid. This is a SILENT error — no crash, just wrong results that propagate through all downstream analysis.

**Prevention:**
1. Write explicit guard assertions: `assert mol_start_idx >= iface.ice_atom_count` before any replacement.
2. Separate the "select liquid molecules to replace" step from "perform replacement" step, with validation between them.
3. Unit test: Generate an interface, insert ions, verify `ice_atom_count` positions still contain O, H, H atoms with ice-like O-O distances.

**Detection:** After insertion, check that the ice region's O-O distance distribution matches the pre-insertion distribution. Any deviation >0.01 nm indicates accidental ice replacement.

**Phase:** Phase 2 (Tab 4 — ion insertion logic)

---

### Pitfall 5: Variable Atoms-Per-Molecule Breaks All Position Array Assumptions

**What goes wrong:** The ENTIRE codebase assumes a UNIFORM `atoms_per_molecule`: 3 for ice (O, H, H), 4 for water (OW, HW1, HW2, MW). Adding ions (Na+=1 atom, Cl-=1 atom) and custom molecules (arbitrary atom count) breaks this assumption in `overlap_resolver.py`, `water_filler.py`, `gromacs_writer.py`, `vtk_utils.py`, and the `InterfaceStructure` type itself.

**Why it happens:** `InterfaceStructure` stores positions as a single flat `(N, 3)` array with `ice_atom_count` and `water_atom_count` boundary markers. All downstream code iterates using uniform `atoms_per_molecule`. With ions (1 atom/mol), the indexing math `mol_idx * atoms_per_molecule` gives wrong offsets. This is the SINGLE BIGGEST refactoring required for v4.0.

**Consequences:** Out-of-bounds array access, wrong atom positions read, bonds created on wrong atom pairs, GROMACS export with garbled coordinates, VTK rendering crashes.

**Prevention:**
1. Replace the flat positions array with a structured approach: store a list of molecule segments, where each segment has `positions`, `atom_names`, `moltype`, `atoms_per_molecule`, and `nmolecules`.
2. Or: keep the flat array but add an index structure: `molecule_segments = [(start_idx, end_idx, moltype, atoms_per_molecule), ...]` alongside the positions array.
3. ALL code that iterates over molecules must use the index structure instead of uniform `atoms_per_molecule`.

**Detection:** Write a test that creates a structure with water (4 atoms/mol) + Na+ (1 atom/mol) + Cl- (1 atom/mol) and verifies every molecule's atoms are correctly indexed.

**Phase:** Phase 1 (data structure design — MUST be resolved before ANY Tab 2 or Tab 4 code works)

---

### Pitfall 6: Electroneutrality Violation in Ion Insertion

**What goes wrong:** Users might request only Na+ ions (or only Cl-), or unequal numbers. GROMACS requires total system charge to be zero for energy minimization. A charged system causes `gmx grompp` to fail with "System has non-zero total charge" or causes numerical instabilities during MD.

**Why it happens:** The v4-context.md spec says "Auto-calculate number of Na+ and Cl- ions" from concentration. But if the user provides a concentration, the calculated number of ion pairs may not be an integer (e.g., 3.2 → rounds to 3, but what about the fractional 0.2?). Also, users may want custom ion counts.

**Consequences:** GROMACS rejects the topology. For MD simulations, even ~1e net charge in a periodic system creates an artificial electric field that corrupts results.

**Prevention:**
1. Always pair Na+ with Cl- in equal numbers.
2. If concentration yields a non-integer ion pair count, round to nearest integer and show the actual resulting concentration.
3. Add validation: `assert abs(total_charge) < 1e-6` before writing topology.
4. For custom ion insertion, warn: "System has net charge of +Xe. GROMACS may reject this."

**Detection:** After ion insertion, sum all charges and verify `abs(total_charge) < 1e-6`.

**Phase:** Phase 2 (Tab 4 — ion insertion validation)

---

### Pitfall 7: GenIce2 Numpy Random State Not Restored on Exception

**What goes wrong:** The existing tech debt in `generator.py` (documented in CONCERNS.md) means `np.random.set_state(original_state)` is NOT called if an exception occurs between seed and restore. Hydrate generation is MORE complex and MORE likely to throw exceptions (invalid guest dict format, too many guests for cage capacity, incompatible molecule-lattice pairs), making this bug much more dangerous.

**Why it happens:** `set_state()` is outside the try/except block. GenIce2's Stage7 (guest placement) can throw `AssertionError: Too many guests` which bypasses the restore.

**Consequences:** After ANY hydrate generation failure, ALL subsequent random number generation in QuickIce is polluted. This silently corrupts interface generation, ranking, and any code using `np.random`.

**Prevention:** Move `np.random.set_state(original_state)` into a `finally` block. This is a pre-existing fix that should be done BEFORE any v4.0 work.

**Detection:** Generate a hydrate with too many guests (should throw), then generate a pure ice structure. If the ice structure differs from a fresh-session generation, random state is polluted.

**Phase:** Phase 0 (pre-requisite fix before v4.0 work begins)

---

## Moderate Pitfalls

Mistakes that cause delays, confusing errors, or technical debt.

### Pitfall 8: Concentration-to-Count Requires Liquid Volume (Cross-Tab Dependency)

**What goes wrong:** Converting "0.5 mol/L NaCl" to a number of ion pairs requires knowing the LIQUID water volume (not total box volume). The liquid volume is determined by Tab 3 (Interface Construction) which runs BEFORE Tab 4. This creates a tight cross-tab dependency: Tab 4 needs Tab 3's output to calculate ion counts.

**Why it happens:** NaCl goes into the liquid phase only. Liquid volume = total volume - ice volume. For slab: `liquid_volume = box_x × box_y × water_thickness`. For pocket: `liquid_volume = (4/3) × π × (diameter/2)³`. For piece: `liquid_volume = total_volume - ice_volume`. But `InterfaceStructure` currently doesn't carry `liquid_volume_nm3`.

**Consequences:** Without liquid volume, ion count is wrong. Too many ions over-saturates the solution; too few under-saturates it.

**Prevention:**
1. Add `liquid_volume_nm3: float` field to `InterfaceStructure`, computed during each interface mode's assembly.
2. Tab 4 reads this field to calculate: `n_ion_pairs = concentration_mol_L × liquid_volume_nm3 × 1e-24 × NA` where `NA = 6.022e23`.
3. If no interface structure is available, require manual box volume input.

**Detection:** Test with known system (0.5 mol/L in 5×5×4 nm water → should give ~30 ion pairs). Compare calculated count to expected value.

**Phase:** Phase 2 (Tab 4 — depends on InterfaceStructure carrying liquid volume)

---

### Pitfall 9: User-Provided .gro/.itp File Path Problems

**What goes wrong:** The `.top` file must `#include` the user's `.itp` file. Absolute paths (`#include "/home/user/molecules/methane.itp"`) break when moved to another machine. Relative paths (`#include "methane.itp"`) only work if GROMACS runs from the same directory as the `.itp` file.

**Why it happens:** GROMACS resolves `#include` paths relative to the working directory where `gmx grompp` is run, NOT relative to the `.top` file location. There's no standard way to handle this in GROMACS.

**Consequences:** Users can't run MD simulations with exported files without manually editing `.top`. This undermines the "generate GROMACS-ready input" value proposition.

**Prevention:**
1. Copy user-provided `.itp` files to the output directory alongside `.gro` and `.top`.
2. Use relative paths in `#include` directives.
3. Document that all `.itp` files must be in the same directory as `.top` when running GROMACS.
4. Bundle common ion `.itp` files (Na+, Cl-) in `quickice/data/` like `tip4p-ice.itp`.

**Detection:** Export system with custom molecules, move all output files to a different directory, try `gmx grompp`. If it fails with "file not found", path handling is broken.

**Phase:** Phase 2 (Tab 4 export)

---

### Pitfall 10: Overlap Detection Uses O-O Distance for Non-Water Molecules

**What goes wrong:** Current `detect_overlaps()` uses O-O distance (0.25 nm threshold) as collision criterion. This works for water-water overlap. But for ion-water overlap, the threshold should be based on VDW radii. Na+ (ionic radius 0.116 nm) is smaller than O (0.152 nm VDW). Cl- (ionic radius 0.167 nm) is larger. Using 0.25 nm O-O distance over-estimates Na+ exclusion zone; for Cl-, it may under-estimate.

**Why it happens:** The overlap resolver was designed for water-water collision detection only. It uses O atom positions as reference points and assumes all molecules are water.

**Consequences:** After ion insertion, Na+ may be too far from water molecules (over-excluded) or Cl- may overlap with water (under-excluded). GROMACS energy minimization may fail for Cl- overlap cases.

**Prevention:**
1. Add atom-type-aware overlap detection: use cKDTree with per-atom-type thresholds based on VDW radii.
2. For ions: use ion VDW radius + O VDW radius as threshold (Na-O: ~0.27 nm, Cl-O: ~0.33 nm).
3. For custom molecules: use the largest atom's VDW radius.
4. Make the overlap threshold a parameter per atom type, not a single global value.

**Detection:** Insert Na+ ions, check that no Na-O distance is less than ~0.2 nm (sum of VDW radii minus tolerance). Insert Cl- ions, check that no Cl-O distance is less than ~0.25 nm.

**Phase:** Phase 2 (Tab 4 — overlap detection for non-water molecules)

---

### Pitfall 11: VTK Visualization Hardcodes Water-Only Atom Types

**What goes wrong:** `vtk_utils.py` maps atom names to atomic numbers with a fixed dict: `{"O": 8, "H": 1, "OW": 8, "HW1": 1, "HW2": 1, "MW": None}`. Adding ions (Na=11, Cl=17) and custom molecules (C=6, S=16, etc.) requires extending this mapping. The current bond creation logic assumes water molecule structure (3 visible atoms per molecule, O-H-H pattern).

**Why it happens:** VTK conversion functions were written for water-only systems. `candidate_to_vtk_molecule()` and `interface_to_vtk_molecules()` assume `[O, H, H]` or `[OW, HW1, HW2]` patterns. The per-molecule bond creation iterates assuming 3 visible atoms per molecule.

**Consequences:** Ions and custom molecules are invisible (KeyError for unmapped atom names) or rendered incorrectly (bonds drawn between Na+ and adjacent water molecules). The 3D viewer silently fails or shows garbage.

**Prevention:**
1. Use a general element-to-atomic-number lookup (periodic table style) instead of a hardcoded dict.
2. Separate bond creation from atom creation: ions have NO bonds, custom molecules may have internal bonds defined by their topology.
3. Create separate VTK actors per molecule type with per-type rendering styles (VDW for ions, ball-and-stick for small molecules, lines for water) as specified in v4-context.md.

**Detection:** Render a structure with Na+ ions. If they don't appear or if bonds are drawn between Na+ and water molecules, this pitfall was hit.

**Phase:** Phase 3 (3D viewer enhancements — display styles per molecule type)

---

### Pitfall 12: Hydrate Unit Cells Differ from Pure Ice

**What goes wrong:** Methane hydrate sI has a unit cell of 12.24 Å (1.224 nm) with 46 water molecules + 8 guest cages. This is fundamentally different from ice Ih (variable supercell). If Tab 2 passes the same `nmolecules` parameter to the hydrate lattice as it does to pure ice, `calculate_supercell()` will be wrong.

**Why it happens:** `calculate_supercell()` uses `UNIT_CELL_MOLECULES` which maps GenIce lattice names to molecules per unit cell. Hydrate lattices have different molecule counts AND include guest cages that are not water molecules. The density is also different (0.795 g/cm³ for sI vs 0.92 g/cm³ for ice Ih).

**Consequences:** Wrong supercell size, wrong molecule count, wrong density. Generated structure may have far too many or too few water molecules.

**Prevention:**
1. Create a `HYDRATE_UNIT_CELL_MOLECULES` mapping separate from `UNIT_CELL_MOLECULES`.
2. Hydrate generation should use the lattice's own `density` attribute (`lattice.density`), not the phase-based density from `lookup_phase()`.
3. Hydrate generation is NOT a simple replacement of `PHASE_TO_GENICE["ice_ih"]` with `PHASE_TO_GENICE["sI"]` — the generation flow is fundamentally different.

**Detection:** Generate sI hydrate. Verify the unit cell has the expected dimensions (~1.224 nm) and 46 water molecules per unit cell.

**Phase:** Phase 1 (Tab 2 — hydrate generation)

---

### Pitfall 13: MW Virtual Site Computation Called on Non-Water Molecules

**What goes wrong:** `compute_mw_position()` computes the TIP4P-ICE virtual site from O, H1, H2 positions. If the GROMACS writer iterates over all molecules and blindly calls `compute_mw_position()` for each, it crashes or produces garbage for ions (1 atom, not 3) and custom molecules (different atom layouts).

**Why it happens:** The writer's loop `for mol_idx in range(nmol)` assumes every molecule is water. With ions and custom molecules, this assumption breaks.

**Consequences:** `IndexError` when accessing `positions[base_idx + 1]` for a 1-atom ion. Or silent wrong coordinates if the ion's single atom position is misinterpreted as O.

**Prevention:**
1. Refactor the writer to iterate over molecule segments with per-segment `atoms_per_molecule` and `moltype`.
2. Only call `compute_mw_position()` for water molecules (moltype == "SOL").
3. Ions and custom molecules write their atoms directly from positions without MW computation.

**Detection:** Export a system with water + NaCl. If the writer crashes with IndexError or the GRO file has garbage coordinates for Na+, this pitfall was hit.

**Phase:** Phase 2 (GROMACS export for multi-molecule systems)

---

### Pitfall 14: Tab 2 Hydrate Generation Must Be a Separate Pipeline, Not Tab 1 Modification

**What goes wrong:** If hydrate generation is implemented as a modification of Tab 1 (replacing the ice lattice with a hydrate lattice), it breaks Tab 1's validated flow. Hydrate structures are fundamentally different from pure ice: no phase lookup needed (lattice chosen directly), no ranking (one structure per lattice), output contains both water AND guest molecules.

**Why it happens:** It's tempting to reuse Tab 1's generation pipeline. But hydrate generation requires: selecting a hydrate lattice (not a phase from T/P), providing a guest molecule (not just water), and producing output with mixed molecule types (water + guests). Tab 1's flow is: T/P → phase lookup → lattice → generate → rank → display. Tab 2's flow is: select lattice → select guest → generate → display (no ranking needed).

**Prevention:** Implement hydrate generation as a SEPARATE pipeline in Tab 2 with its own ViewModel, Worker, and generation logic. Tab 1 remains unchanged.

**Detection:** If Tab 2 code imports or modifies Tab 1's `generate_candidates()` or `rank_candidates()`, this pitfall was hit.

**Phase:** Phase 1 (Tab 2 architecture decision — make this explicit before coding)

---

### Pitfall 15: Missing Temperature/Pressure in Candidate Metadata

**What goes wrong:** Already documented as a known bug in CONCERNS.md: `candidate.metadata` never includes `temperature` or `pressure`. Water density calculations in interface modes always use defaults (273.15 K, 0.1 MPa). For Tab 4, ion concentration calculations depend on liquid volume, which depends on water density, which depends on temperature.

**Why it happens:** `IceStructureGenerator._generate_single()` at line 136-138 only stores `density` and `phase_name` in metadata. Temperature and pressure are available at call time but not persisted.

**Prevention:** Add `"temperature": temperature` and `"pressure": pressure` to `candidate.metadata` in `_generate_single()`. This is a pre-existing fix.

**Detection:** Generate a candidate, check `candidate.metadata`. If `temperature` and `pressure` keys are missing, this bug is present.

**Phase:** Phase 0 (pre-requisite fix)

---

### Pitfall 16: GRO Parser Duplication Gets Worse with Custom Molecules

**What goes wrong:** Two separate `_parse_gro()` implementations exist (CONCERNS.md). With custom molecules, users will provide `.gro` files that also need parsing. A third copy would be disastrous.

**Why it happens:** Both `generator.py` and `water_filler.py` implement GRO parsing independently. Custom molecule parsing requires the same format handling plus user-provided file loading.

**Prevention:** Extract `_parse_gro()` into a shared `quickice/structure_generation/gro_parser.py` module. Use it everywhere. This is a pre-existing tech debt fix.

**Detection:** Count GRO parsing implementations. If >1, this pitfall hasn't been addressed.

**Phase:** Phase 0 (pre-requisite fix)

---

## Minor Pitfalls

Mistakes that cause annoyance but are fixable with moderate effort.

### Pitfall 17: Residue Naming in GRO/Top Output

**What goes wrong:** Current code uses "SOL" as the residue name for all molecules. With ions, GROMACS convention is "NA" for sodium, "CL" for chloride. Using "SOL" for everything confuses analysis tools.

**Prevention:** Store residue name as part of molecule segment specification. Use per-moltype residue naming.

**Phase:** Phase 2 (GROMACS export)

---

### Pitfall 18: Random Ion Placement Can Create Ion-Ion Pairs Too Close

**What goes wrong:** Multiple Na+ and Cl- ions placed randomly in the liquid phase may end up very close together. Like-charge ion pairs (Na-Na, Cl-Cl) cause GROMACS energy minimization to fail or converge slowly.

**Prevention:** After placing all ions, run overlap check with ion-ion thresholds (~0.3 nm for Na-Na, ~0.4 nm for Cl-Cl). If overlaps found, re-place offending ions. Optionally warn if too many ions for the liquid volume.

**Phase:** Phase 2 (Tab 4 — post-insertion validation)

---

### Pitfall 19: Custom Molecule Orientation May Cross PBC Boundaries

**What goes wrong:** In Tab 4 custom mode, the user specifies center-of-mass and rotation matrix. If the molecule is large (e.g., THF with 14+ atoms) and the COM is near a box edge, some atoms may end up outside the periodic box after rotation, creating "broken" molecules spanning PBC boundaries.

**Prevention:** After placing a custom molecule with rotation, wrap all atoms using molecule-as-unit wrapping (same approach as `water_filler.py`'s `tile_structure()`). Check that no intra-molecular bond exceeds a reasonable distance.

**Phase:** Phase 2 (Tab 4 — custom molecule placement)

---

### Pitfall 20: No Cancellation UI for Long-Running Molecule Insertion

**What goes wrong:** The existing GUI has no cancel button for Tab 3 interface generation (noted in CONCERNS.md). Tab 4 molecule insertion (especially random placement with overlap checking for large systems) may also be slow. Users must wait or kill the application.

**Prevention:** Add a cancel button to Tab 2 and Tab 4 generation panels. Connect to `QThread.requestInterruption()` in the worker. This is a pre-existing UX gap.

**Phase:** Phase 3 (GUI polish)

---

### Pitfall 21: Dual is_cell_orthogonal() Functions Cause Inconsistency

**What goes wrong:** Two `is_cell_orthogonal()` implementations exist (CONCERNS.md): one in `water_filler.py` (angle tolerance 0.1°) and one in `interface_builder.py` (off-diagonal element tolerance 1e-10). For hydrate unit cells, which may have near-orthogonal angles, these can give DIFFERENT results, causing one code path to use triclinic tiling while another uses orthogonal.

**Prevention:** Consolidate into a single function with one tolerance strategy. This is a pre-existing tech debt fix.

**Phase:** Phase 0 (pre-requisite fix)

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Pre-requisite fixes | Random state not restored on exception (#7) | Move `set_state()` to `finally` block |
| Pre-requisite fixes | Missing T/P in metadata (#15) | Add temperature/pressure to Candidate.metadata |
| Pre-requisite fixes | GRO parser duplication (#16) | Extract to shared module |
| Pre-requisite fixes | Dual is_cell_orthogonal (#21) | Consolidate to one function |
| Data structure design | Variable atoms-per-molecule (#5) | Design molecule segment index before any Tab 2/4 code |
| Tab 2 hydrate generation | GenIce2 guest dict format (#1) | Write adapter function; unit test with methane guest |
| Tab 2 hydrate generation | Case-sensitive lattice names (#2) | Create hydrate-to-GenIce name mapping |
| Tab 2 hydrate generation | Different unit cells for hydrates (#12) | Separate HYDRATE_UNIT_CELL_MOLECULES mapping |
| Tab 2 architecture | Hydrate must be separate pipeline (#14) | Design as separate flow, not Tab 1 modification |
| Tab 4 ion insertion | Ion replaces ice molecule (#4) | Guard assertions + boundary validation |
| Tab 4 ion insertion | Electroneutrality violation (#6) | Always pair Na+ with Cl-; validate total charge |
| Tab 4 ion insertion | Cross-tab volume dependency (#8) | Add liquid_volume_nm3 to InterfaceStructure |
| Tab 4 overlap detection | O-O threshold for non-water (#10) | Atom-type-aware overlap thresholds |
| Tab 4 custom placement | PBC boundary crossing (#19) | Molecule-as-unit wrapping after rotation |
| GROMACS export | Single-SOL topology broken (#3) | Multi-moltype topology writer |
| GROMACS export | MW computed for non-water (#13) | Per-moltype export logic |
| GROMACS export | .itp file paths broken (#9) | Copy .itp files to output directory |
| GROMACS export | Wrong residue names (#17) | Per-moltype residue naming |
| 3D viewer | Hardcoded atom types (#11) | General element lookup + per-type rendering |
| 3D viewer | No cancel button (#20) | Add cancel to Tab 2 and Tab 4 panels |

---

## Dependency Order (What Must Be Fixed Before What)

```
Pre-requisite (Phase 0):
  #7 Random state restore → #1 Hydrate generation safety
  #15 Missing T/P metadata → #8 Liquid volume calculation
  #16 GRO parser duplication → Any .gro file reading for custom molecules
  #21 Dual is_cell_orthogonal → Consistent cell type detection for hydrates

Core data structure (Phase 1):
  #5 Variable atoms-per-molecule → ALL downstream code
  #5 → #3 Multi-moltype topology
  #5 → #4 Ion insertion boundary
  #5 → #11 VTK visualization
  #5 → #13 MW virtual site per moltype

Tab 2 (Phase 1):
  #2 Lattice name mapping → #1 Guest dict adapter → Hydrate generation works
  #12 Hydrate unit cells → #14 Separate pipeline design → Tab 2 UI

Tab 4 (Phase 2):
  #8 Liquid volume → #6 Electroneutrality → Ion count calculation
  #4 Ice boundary guards → Ion replacement logic
  #10 Atom-type overlaps → #18 Ion-ion distance check
  #3 → #13 → #9 → #17 → GROMACS export works

3D viewer (Phase 3):
  #11 VTK atom types → Per-type rendering styles
  #20 Cancel button → UX for long operations
```

---

## Confidence Assessment

| Pitfall | Confidence | Source |
|---------|------------|--------|
| #1 GenIce2 guest dict format | HIGH | Verified by running code; read Stage7 source |
| #2 Case-sensitive lattice names | HIGH | Verified by running `safe_import('lattice', 'sI')` vs `'cs1'` |
| #3 Single-SOL topology | HIGH | Read existing `write_interface_top_file()` source |
| #4 Ion replaces ice molecule | HIGH | Read `InterfaceStructure` type + `overlap_resolver.py` logic |
| #5 Variable atoms-per-molecule | HIGH | Read all code that iterates over molecules |
| #6 Electroneutrality | HIGH | GROMACS standard requirement |
| #7 Random state pollution | HIGH | Read generator.py source + CONCERNS.md |
| #8 Cross-tab volume | HIGH | Read v4-context.md + existing interface mode code |
| #9 .itp file paths | MEDIUM | GROMACS convention; not verified with actual export yet |
| #10 O-O overlap for non-water | HIGH | Read `overlap_resolver.py` source |
| #11 VTK hardcoded types | HIGH | Read `vtk_utils.py` source |
| #12 Hydrate unit cells | HIGH | Verified GenIce2 lattice attributes (cell, density, cagepos) |
| #13 MW for non-water | HIGH | Read `gromacs_writer.py` compute loop |
| #14 Separate pipeline | HIGH | Read v4-context.md + understood GenIce2 hydrate flow |
| #15 Missing T/P metadata | HIGH | Read generator.py source + CONCERNS.md |
| #16 GRO parser duplication | HIGH | Read generator.py + water_filler.py + CONCERNS.md |
| #17-21 Minor pitfalls | MEDIUM | Based on code reading and GROMACS conventions |

---

*Pitfalls research: 2026-04-14*
*Sources: Codebase analysis (all files read directly), GenIce2 API testing (live execution), GROMACS topology conventions*