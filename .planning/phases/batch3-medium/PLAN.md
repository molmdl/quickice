---
phase: batch3-medium
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/output/gromacs_writer.py
  - quickice/structure_generation/modes/slab.py
  - quickice/gui/main_window.py
  - quickice/structure_generation/gro_parser.py
  - docs/gui-guide.md
  - docs/cli-reference.md
  - README.md
autonomous: true

must_haves:
  truths:
    - "molecule_index.index() O(n²) eliminated, replaced with enumerate()"
    - "Invariant assertion after guest-water overlap removal catches non-divisible-by-4 atom counts"
    - "hasattr/getattr replaced with direct access + assertions on typed dataclass"
    - "GRO parser rejects coordinates > 50nm (catches Å→nm unit mixup)"
    - "Hydrate filename pattern in docs matches export.py: hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro"
    - "Solute filename pattern in docs matches export.py: solute_{type}_{count}molecules.gro"
    - "CLI docs version matches __version__: 4.5.0"
    - "GAFF and GAFF2 citations added to References section"
  artifacts:
    - path: "quickice/output/gromacs_writer.py"
      provides: "O(n) molecule iteration with enumerate"
      contains: "enumerate(molecule_index)"
    - path: "quickice/structure_generation/modes/slab.py"
      provides: "Post-overlap invariant assertion"
      contains: "assert len(trimmed_water_positions) % 4 == 0"
    - path: "quickice/gui/main_window.py"
      provides: "Direct attribute access on CustomMoleculeStructure"
      contains: "assert result.water_atom_count >= 0"
    - path: "quickice/structure_generation/gro_parser.py"
      provides: "Coordinate range validation"
      contains: "50.0"
    - path: "docs/gui-guide.md"
      provides: "Correct hydrate and solute filename patterns"
    - path: "docs/cli-reference.md"
      provides: "Correct version 4.5.0"
    - path: "README.md"
      provides: "GAFF/GAFF2 formal citations"
      contains: "GAFF2"
  key_links:
    - from: "quickice/output/gromacs_writer.py"
      to: "molecule_index list"
      via: "enumerate in loop"
      pattern: "for res_idx, mol in enumerate"
    - from: "quickice/gui/hydrate_export.py"
      to: "docs/gui-guide.md"
      via: "filename pattern must match"
      pattern: "hydrate_.*\\.gro"
---

<objective>
Fix 8 MEDIUM priority issues: O(n²) perf bug, missing invariant, fragile data flow, missing parser validation, incorrect docs (3), missing citation.

Purpose: These are correctness and maintainability fixes that prevent silent failures, performance degradation, and user confusion.
Output: 7 files modified with precise search-and-replace edits.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<tasks>

<task type="auto">
  <name>Issue 13: Fix O(n²) molecule_index.index() in loop</name>
  <files>quickice/output/gromacs_writer.py</files>
  <action>
Two edits in `quickice/output/gromacs_writer.py`:

**Edit 1 — Change the loop to use enumerate (line 1093):**

IMPORTANT: `for mol in molecule_index:` appears 3 times in the file (lines 87, 1093, 1174). Only the one at line 1093 (the one right before the `.index()` call) needs to change. Use surrounding context to make the edit unique:

OLD (lines 1091-1093):
```
        lines = []
        atom_num = 0
        for mol in molecule_index:
```

NEW:
```
        lines = []
        atom_num = 0
        for res_idx, mol in enumerate(molecule_index):
```

**Edit 2 — Replace .index() call with res_idx (line 1102):**

OLD (line 1102):
```
            res_num = (molecule_index.index(mol) + 1) % 100000
```

NEW:
```
            res_num = (res_idx + 1) % 100000
```

**Verification:** `molecule_index.index(` only appeared once in the file at line 1102 (confirmed via grep). The other two `for mol in molecule_index:` loops (lines 87 and 1174) do NOT use `.index()` — they just iterate. No other occurrences to fix.
  </action>
  <verify>cd /share/home/nglokwan/quickice && grep -n "molecule_index.index(" quickice/output/gromacs_writer.py — should return no matches; grep -n "enumerate(molecule_index)" quickice/output/gromacs_writer.py — should match line 1093</verify>
  <done>No .index() calls on molecule_index remain; loop uses enumerate; res_idx used for residue numbering</done>
</task>

<task type="auto">
  <name>Issue 14: Add invariant assertion after guest-water overlap removal</name>
  <files>quickice/structure_generation/modes/slab.py</files>
  <action>
Add assertion after the second overlap removal step (guest-water overlap) in `quickice/structure_generation/modes/slab.py`.

The second overlap removal is at lines 543-554. After line 554 (after `water_atom_names = filter_atom_names(...)`), add the invariant assertion.

Insert AFTER this block (line 554 is the last line of the inner if-guest_overlap_indices block):

```
                # Filter atom names to match positions
                water_atom_names = filter_atom_names(
                    water_atom_names,
                    guest_overlap_indices,
                    atoms_per_molecule=4
                )
```

INSERT the following immediately after (before line 556 `# === HYDRATE FIX:`):

```
                # Invariant: water atom count must be divisible by 4 (TIP4P has 4 atoms/molecule)
                assert len(trimmed_water_positions) % 4 == 0, (
                    f"Water atom count {len(trimmed_water_positions)} not divisible by 4 "
                    f"after guest-water overlap removal"
                )
```

Also add the same invariant after the FIRST overlap removal step (lines 364-377). After line 375 (`atoms_per_molecule=4` closing paren of filter_atom_names), before line 376 (`else:`), add:

```
        # Invariant: water atom count must be divisible by 4 (TIP4P has 4 atoms/molecule)
        assert len(trimmed_water_positions) % 4 == 0, (
            f"Water atom count {len(trimmed_water_positions)} not divisible by 4 "
            f"after ice-water overlap removal"
        )
```

Note: The first assertion goes INSIDE the `if overlapping_mol_indices:` block (lines 364-375), after `filter_atom_names` and before the `else:` on line 376. Indentation is 2 levels (8 spaces).
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -c "import ast; ast.parse(open('quickice/structure_generation/modes/slab.py').read()); print('Syntax OK')"</verify>
  <done>Two invariant assertions added: one after ice-water overlap removal, one after guest-water overlap removal. Both assert trimmed_water_positions length is divisible by 4.</done>
</task>

<task type="auto">
  <name>Issue 15: Replace fragile hasattr/getattr with direct access + assertions</name>
  <files>quickice/gui/main_window.py</files>
  <action>
In `quickice/gui/main_window.py`, the block at lines 1193-1241 uses `hasattr(result, 'water_atom_count')` and `getattr(result, 'water_atom_count', 'N/A')` on a `CustomMoleculeStructure` dataclass. Since `water_atom_count` is a required field on this dataclass, hasattr/getattr is unnecessary and hides real bugs.

**Edit 1 — Replace the liquid volume block (lines 1199-1209):**

OLD:
```
            logger.info(f"[Liquid Volume Debug] hasattr(result, 'water_atom_count'): {hasattr(result, 'water_atom_count')}")
            if hasattr(result, 'water_atom_count'):
                logger.info(f"[Liquid Volume Debug] result.water_atom_count: {result.water_atom_count}")
            
            if hasattr(result, 'water_atom_count') and result.water_atom_count > 0:
                water_nmolecules = result.water_atom_count // 4
                liquid_vol = water_nmolecules * 0.0299
                self.solute_panel.set_liquid_volume(liquid_vol)
                logger.info(f"Updated solute panel liquid volume: {liquid_vol:.2f} nm³ from {water_nmolecules} water molecules")
            else:
                logger.warning(f"[Liquid Volume Debug] FAILED to set liquid volume! hasattr={hasattr(result, 'water_atom_count')}, value={getattr(result, 'water_atom_count', 'N/A')}")
```

NEW:
```
            # CustomMoleculeStructure always has water_atom_count (required dataclass field)
            assert result.water_atom_count >= 0, f"Invalid water_atom_count: {result.water_atom_count}"
            
            if result.water_atom_count > 0:
                water_nmolecules = result.water_atom_count // 4
                liquid_vol = water_nmolecules * 0.0299
                self.solute_panel.set_liquid_volume(liquid_vol)
                logger.info(f"Updated solute panel liquid volume: {liquid_vol:.2f} nm³ from {water_nmolecules} water molecules")
            else:
                logger.warning(f"Cannot set liquid volume: water_atom_count={result.water_atom_count}")
```

**Edit 2 — Replace ion panel hasattr block (lines 1217-1219):**

This is the second occurrence of `hasattr(result, 'water_atom_count')`. It's distinguished by the `# Update ion panel` comment above it and `self.ion_panel.set_liquid_volume(liquid_vol)` below.

OLD:
```
            # Update ion panel with liquid volume for ion count calculation
            if hasattr(result, 'water_atom_count') and result.water_atom_count > 0:
                self.ion_panel.set_liquid_volume(liquid_vol)
```

NEW:
```
            # Update ion panel with liquid volume for ion count calculation
            if result.water_atom_count > 0:
                self.ion_panel.set_liquid_volume(liquid_vol)
```

**Edit 3 — Replace interface_structure hasattr blocks (lines 1230-1236):**

The `interface_structure` field on `CustomMoleculeStructure` has a default of `None` (typed as `Any = None`), so a None-check is legitimate — but `hasattr` is unnecessary since the field always exists on the dataclass.

OLD:
```
                    logger.info(f"[Water Count Debug] hasattr(result, 'interface_structure'): {hasattr(result, 'interface_structure')}")
                    if hasattr(result, 'interface_structure') and result.interface_structure is not None:
                        modified_water_count = result.interface_structure.water_nmolecules
                        logger.info(f"[Water Count Debug] modified_water_count: {modified_water_count}")
                    else:
                        logger.warning(f"[Water Count Debug] result.interface_structure is missing or None!")
                        modified_water_count = original_water_count  # Fallback to avoid negative count
```

NEW:
```
                    # CustomMoleculeStructure.interface_structure is a typed dataclass field (can be None)
                    if result.interface_structure is not None:
                        modified_water_count = result.interface_structure.water_nmolecules
                        logger.info(f"[Water Count Debug] modified_water_count: {modified_water_count}")
                    else:
                        logger.warning("[Water Count Debug] result.interface_structure is None, using original count as fallback")
                        modified_water_count = original_water_count  # Fallback to avoid negative count
```

Note: Do NOT touch the `hasattr(self, '_current_interface_result')` check on lines 1223-1227 — that's checking an instance attribute on `self` which may not exist yet, which is a different (legitimate) pattern.
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -c "import ast; ast.parse(open('quickice/gui/main_window.py').read()); print('Syntax OK')"</verify>
  <done>All hasattr(result, 'water_atom_count') and hasattr(result, 'interface_structure') replaced with direct attribute access. hasattr removed from dataclass attribute checks. getattr removed from warning log. Debug-level hasattr logging removed. Assertions added for required fields.</done>
</task>

<task type="auto">
  <name>Issue 16: Add coordinate validation in GRO parser</name>
  <files>quickice/structure_generation/gro_parser.py</files>
  <action>
Add a coordinate range check after parsing all coordinates in `parse_gro_string()`.

Insert the check AFTER the for-loop that fills `positions` (after line 57: `positions[i] = [x, y, z]`) and BEFORE the cell parsing section (before line 59: `# Parse cell dimensions`).

Insert:

```
    # Validate coordinate range: GRO coordinates must be in nm.
    # Values > 50 nm likely indicate an Å→nm unit mixup (50nm ≈ 500Å).
    max_coord = np.max(np.abs(positions))
    if max_coord > 50.0:
        raise ValueError(
            f"Coordinate value {max_coord:.2f} nm exceeds 50 nm limit. "
            f"Possible unit mixup: coordinates may be in Ångströms instead of nm. "
            f"GRO format requires nm (1 nm = 10 Å)."
        )
```

This goes at line 58 (between the for-loop and the cell parsing comment), with 4-space indentation matching the function body.
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -c "
from quickice.structure_generation.gro_parser import parse_gro_string
import numpy as np

# Test: valid coordinates (nm) should pass
gro_ok = 'test\\n1\\n    1SOL    OW    1   1.000   2.000   3.000\\n   1.000   1.000   1.000'
try:
    parse_gro_string(gro_ok)
    print('PASS: valid coords accepted')
except ValueError:
    print('FAIL: valid coords rejected')

# Test: Å coordinates (>50nm) should raise
gro_bad = 'test\\n1\\n    1SOL    OW    1 100.000 200.000 300.000\\n   1.000   1.000   1.000'
try:
    parse_gro_string(gro_bad)
    print('FAIL: bad coords accepted')
except ValueError as e:
    print(f'PASS: bad coords rejected: {e}')
"</verify>
  <done>GRO parser raises ValueError when any coordinate exceeds 50nm. Valid nm-scale coordinates pass through.</done>
</task>

<task type="auto">
  <name>Issues 17+18: Fix hydrate and solute filename patterns in docs</name>
  <files>docs/gui-guide.md</files>
  <action>
Two edits in `docs/gui-guide.md`:

**Edit 1 — Fix hydrate filename pattern (line 298):**

Verified actual pattern from `quickice/gui/hydrate_export.py` line 109:
`default_name = f"hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro"`

OLD (line 298):
```
- `hydrate_{lattice}.gro` — Coordinates
- `hydrate_{lattice}.top` — Topology
```

NEW:
```
- `hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro` — Coordinates (e.g., `hydrate_sI_ch4_2x2x2.gro`)
- `hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.top` — Topology
```

**Edit 2 — Fix solute filename pattern (lines 707-708):**

Verified actual pattern from `quickice/gui/export.py` line 58:
`default_name = f"solute_{solute_type}_{n_molecules}molecules.gro"`

OLD (lines 707-708):
```
- `interface_with_solutes.gro` — Coordinates with solutes
- `interface_with_solutes.top` — Topology with solute moleculetype
```

NEW:
```
- `solute_{type}_{count}molecules.gro` — Coordinates with solutes (e.g., `solute_ch4_45molecules.gro`)
- `solute_{type}_{count}molecules.top` — Topology with solute moleculetype
```
  </action>
  <verify>cd /share/home/nglokwan/quickice && grep -n "hydrate_{lattice}" docs/gui-guide.md — should show the updated pattern with guest and supercell; grep -n "interface_with_solutes" docs/gui-guide.md — should return no matches</verify>
  <done>Hydrate filename pattern updated to include guest type and supercell dimensions. Solute filename pattern updated to match actual export code. No stale patterns remain.</done>
</task>

<task type="auto">
  <name>Issues 19+20: Fix version in CLI docs and add GAFF2 citation</name>
  <files>docs/cli-reference.md, README.md</files>
  <action>
**Edit 1 — Fix version in docs/cli-reference.md (line 145):**

Verified actual version from `quickice/__init__.py` line 3: `__version__ = "4.5.0"`
and `quickice/cli/parser.py` line 175: `version="%(prog)s 4.5.0"`. Only one occurrence of `4.0.0` exists (confirmed via grep).

OLD (line 145):
```
# Output: python quickice.py 4.0.0
```

NEW:
```
# Output: python quickice.py 4.5.0
```

**Edit 2 — Add GAFF/GAFF2 citations in README.md:**

Line 216 mentions GAFF2 but the References section (starting line 296) has no formal citation for GAFF or GAFF2.

Insert a new subsection AFTER the "Sobtop" section (after line 330) and BEFORE the "Gaussian 16 Rev. C01" section (before line 332):

OLD:
```
### Sobtop
- Tian Lu, Sobtop, Version 2026.1.16, http://sobereva.com/soft/Sobtop (accessed on 15 Apr 2026)

### Gaussian 16 Rev. C01
```

NEW:
```
### Sobtop
- Tian Lu, Sobtop, Version 2026.1.16, http://sobereva.com/soft/Sobtop (accessed on 15 Apr 2026)

### GAFF / GAFF2
- Wang, J., Wolf, R. M., Caldwell, J. W., Kollman, P. A., & Case, D. A. (2004). Development and testing of a general amber force field. Journal of Computational Chemistry, 25(9), 1157–1174. DOI: https://doi.org/10.1002/jcc.20035
- He, X., Man, V. H., Yang, Y., Wang, L.-P., & Merz, K. M. (2020). A fast and high-quality charge model for molecular mechanical force fields. Journal of Chemical Information and Modeling, 60(5), 247–257. DOI: https://doi.org/10.1021/acs.jcim.9b01131

### Gaussian 16 Rev. C01
```
  </action>
  <verify>cd /share/home/nglokwan/quickice && grep "4\.0\.0" docs/cli-reference.md — should return no matches; grep -c "GAFF2" README.md — should find at least 2 occurrences (line 216 + new citation); grep -c "Wang, J." README.md — should be 1</verify>
  <done>CLI docs version updated to 4.5.0 matching __version__. GAFF (Wang 2004) and GAFF2 (He 2020) citations added to References section in README.md.</done>
</task>

</tasks>

<verification>
# Full verification after all edits
cd /share/home/nglokwan/quickice

# 1. Syntax check all modified Python files
python -c "
import ast
for f in ['quickice/output/gromacs_writer.py', 'quickice/structure_generation/modes/slab.py', 'quickice/gui/main_window.py', 'quickice/structure_generation/gro_parser.py']:
    ast.parse(open(f).read())
    print(f'OK: {f}')
"

# 2. Verify no .index() calls on molecule_index remain
grep -n "molecule_index.index(" quickice/output/gromacs_writer.py && echo "FAIL" || echo "PASS: no .index() calls"

# 3. Verify enumerate pattern
grep -n "enumerate(molecule_index)" quickice/output/gromacs_writer.py

# 4. Verify assertions in slab.py
grep -n "assert len(trimmed_water_positions) % 4 == 0" quickice/structure_generation/modes/slab.py

# 5. Verify no hasattr(result pattern remains for water_atom_count/interface_structure
grep -n "hasattr(result," quickice/gui/main_window.py | grep -v "ranked_candidates" | grep -v "lattice_info" || echo "PASS: no hasattr on result for fixed attrs"

# 6. Verify coordinate validation exists
grep -n "50.0" quickice/structure_generation/gro_parser.py

# 7. Verify doc patterns
grep -n "hydrate_{lattice}_{guest}" docs/gui-guide.md
grep -n "solute_{type}" docs/gui-guide.md
grep "4\.0\.0" docs/cli-reference.md && echo "FAIL: stale version" || echo "PASS: no 4.0.0"
grep -c "GAFF / GAFF2" README.md
</verification>

<success_criteria>
- `molecule_index.index()` has zero occurrences in gromacs_writer.py
- Two `assert len(trimmed_water_positions) % 4 == 0` assertions in slab.py
- Zero `hasattr(result, 'water_atom_count')` or `hasattr(result, 'interface_structure')` in main_window.py
- GRO parser raises ValueError for coordinates > 50nm
- Hydrate filename pattern includes `{guest}_{nx}x{ny}x{nz}` in docs
- Solute filename pattern is `solute_{type}_{count}molecules.gro` in docs
- CLI docs show version 4.5.0
- README.md References section includes GAFF/GAFF2 subsection
</success_criteria>

<output>
After completion, create `.planning/phases/batch3-medium/batch3-medium-01-SUMMARY.md`
</output>
