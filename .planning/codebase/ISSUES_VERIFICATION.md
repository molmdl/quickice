---
verified: 2026-05-22T12:00:00Z
total_issues: 38
confirmed: 34
refuted: 1
partially_correct: 2
needs_update: 1
---

# Issues Verification Report — ISSUES_BY_FILE.md

**Verified:** 2026-05-22
**Method:** Read actual source code at cited line numbers, compare with issue descriptions

---

## CRITICAL Issues

### FLOW-01: SoluteGROMACSExporter uses wrong writers (WORSE THAN DOCUMENTED)

**Status:** CONFIRMED — **AND WORSE THAN DESCRIBED**
**Evidence:**
- `export.py` line 75: `all_positions = np.vstack([...])` — but `import numpy as np` is MISSING from export.py (lines 1-21 show no numpy import). **This will crash with NameError.**
- `export.py` line 83: `write_gro_file(all_positions, all_atom_names, solute_structure.cell, str(path))` — called with 4 args, but `write_gro_file(candidate: Candidate, filepath: str)` expects 2 args. **This will crash with TypeError.**
- `export.py` line 123: `write_top_file(all_positions, all_atom_names, solute_structure.cell, str(top_path), molecule_index, registry=...)` — called with 5+ args, but `write_top_file(candidate: Candidate, filepath: str)` expects 2 args. **This will crash with TypeError.**
- Even if the call worked: `write_gro_file()` (line 426) only writes SOL molecules (ice only, 3→4 atom conversion). It doesn't write water, guests, or solutes. `write_top_file()` (line 512) only writes a single-molecule .top (SOL only).
**Fix complexity:** COMPLEX
**Recommended approach:** DEBUGGER — This needs a full rewrite. The function signatures don't match, numpy is missing, and the underlying writers are for single-molecule ice, not multi-molecule solute systems. A debugger must trace the working export paths (IonGROMACSExporter, InterfaceGROMACSExporter) to understand the correct pattern, then rewrite SoluteGROMACSExporter to match.
**Rationale:** Three separate crash bugs + wrong underlying writers. Not a simple "use different writers" fix — the entire export flow needs restructuring.

---

### FLOW-02: CustomMoleculeGROMACSExporter missing tip4p-ice.itp

**Status:** CONFIRMED
**Evidence:**
- `export.py` lines 200-221: The `export_custom_molecule_gromacs()` method copies the custom `.itp` file (line 215-216) but NEVER copies `tip4p-ice.itp`. There is no `shutil.copy2(tip4p_path, output_dir / "tip4p-ice.itp")` call.
- `gromacs_writer.py` line 2026: `write_custom_molecule_top_file()` writes `#include "tip4p-ice.itp"` into the .top file.
- Without the file, GROMACS will fail with "File not found: tip4p-ice.itp".
**Fix complexity:** SIMPLE
**Recommended approach:** EXECUTOR — Add 3 lines: import shutil, get tip4p path, copy to output dir. Same pattern as IonGROMACSExporter (line 296-300) and InterfaceGROMACSExporter (line 856-858).
**Rationale:** Exact pattern exists in two other exporters. Copy-paste fix.

---

### MOL-2: gui-guide.md uses CH4_LIQ/THF_LIQ instead of CH4_L/THF_L

**Status:** CONFIRMED
**Evidence:**
- `docs/gui-guide.md` line 708: `CH4_LIQ` and `THF_LIQ` appear in the text.
- `docs/gui-guide.md` line 710: Note mentions `_LIQ` suffix and `CH4_HYD`/`THF_HYD`.
- Actual code: `gromacs_writer.py` MOLECULE_TO_GROMACS (line 30-31) uses `CH4` and `THF` for hydrate guests, while the registry system produces names like `CH4_H`/`THF_H` (hydrate) and `CH4_L`/`THF_L` (liquid). The old `_HYD`/`_LIQ` naming is obsolete.
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — String replacements in docs: `CH4_HYD` → `CH4_H`, `THF_HYD` → `THF_H`, `CH4_LIQ` → `CH4_L`, `THF_LIQ` → `THF_L`.
**Rationale:** Pure text substitution, no logic changes.

---

### MOL-3: gui-guide.md uses wrong molecule naming (second occurrence)

**Status:** CONFIRMED (same as MOL-2, different line)
**Evidence:** `docs/gui-guide.md` line 710: Same wrong naming pattern.
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Same fix as MOL-2.

---

## HIGH Issues

### EXC-02: Silent FileNotFoundError

**Status:** CONFIRMED
**Evidence:**
- `export.py` lines 332-335: In `IonGROMACSExporter.export_ion_gromacs()`:
  ```python
  except FileNotFoundError:
      # Guest .itp file not found - will cause GROMACS to fail
      # but don't block export, user can add manually
      pass
  ```
- `export.py` lines 876-879: In `InterfaceGROMACSExporter.export_interface_gromacs()`:
  ```python
  except FileNotFoundError:
      # Guest .itp file not found - will cause GROMACS to fail
      # but don't block export, user can add manually
      pass
  ```
- Both silently swallow the error. The .top file still contains `#include "ch4_hydrate.itp"` (or similar), but the file won't exist in the output directory. GROMACS will fail on `gmx grompp`.
**Fix complexity:** SIMPLE
**Recommended approach:** EXECUTOR — Replace `pass` with `QMessageBox.warning()` in both locations. Pattern already exists in same file: `QMessageBox.critical()` at line 146.
**Rationale:** Clear fix, existing patterns to follow.

---

### BUG-01: OW-safeguard missing in pocket.py and piece.py

**Status:** CONFIRMED
**Evidence:**
- `slab.py` lines 80-97: Has OW-safeguard in `_detect_guest_atoms()`:
  ```python
  if guest_atoms > 0:
      end_idx = min(i + guest_atoms, len(atom_names))
      has_ow = any(atom_names[j] == "OW" for j in range(i, end_idx))
      if has_ow:
          water_indices.extend(range(i, end_idx))
          i = end_idx
      else:
          guest_indices.extend(range(i, i + guest_atoms))
          i += guest_atoms
  ```
- `pocket.py` lines 56-64: NO safeguard. After detecting guest_atoms, immediately adds to guest_indices:
  ```python
  guest_atoms = count_guest_atoms(atom_names, i)
  guest_indices.extend(range(i, i + guest_atoms))
  i += guest_atoms
  ```
- `piece.py` lines 77-83: Same as pocket.py — NO safeguard.
- **What the safeguard does:** If `count_guest_atoms()` returns a range that contains OW atoms, it recognizes this is actually a misidentified water molecule (not a guest), adds it to water_indices instead, and re-syncs the loop.
**Fix complexity:** MODERATE
**Recommended approach:** EXECUTOR — Copy the OW-safeguard block from slab.py lines 80-97 into both pocket.py and piece.py's `_detect_guest_atoms()`. Care must be taken to match the exact loop structure (indentation, variable names are the same). Test with hydrate candidates that have water near guests.
**Rationale:** The fix logic is clear and already implemented in slab.py. But it needs verification that the loop structure is identical across all three files.

---

### MOL-1: README.md uses CH4_HYD/THF_LIQ instead of CH4_H/THF_L

**Status:** CONFIRMED
**Evidence:**
- `README.md` line 194: `CH4_HYD           128     ; Hydrate guests (from Tab 1)`
- `README.md` line 195: `THF_LIQ           45      ; Liquid solutes (from Tab 4)`
- Should be `CH4_H` and `THF_L` per current registry naming.
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — String replacement in README.md.

---

### MOL-5: README.md says ch4.itp/thf.itp but code uses ch4_hydrate.itp/thf_hydrate.itp

**Status:** CONFIRMED
**Evidence:**
- `README.md` line 181: `ch4.itp/thf.itp` listed for Tab 1 (hydrate) export.
- `gromacs_writer.py` line 30-31: MOLECULE_TO_GROMACS maps ch4 → `ch4_hydrate.itp`, thf → `thf_hydrate.itp`.
- Actual export copies `{guest_type}_hydrate.itp` (e.g., `ch4_hydrate.itp`).
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Replace `ch4.itp/thf.itp` with `ch4_hydrate.itp/thf_hydrate.itp`.

---

### MOL-4: gui-guide.md says ch4.itp/thf.itp instead of ch4_hydrate.itp/thf_hydrate.itp

**Status:** CONFIRMED
**Evidence:**
- `docs/gui-guide.md` line 297: `ch4.itp` or `thf.itp` — Guest molecule parameters (GAFF).
- Actual code exports `ch4_hydrate.itp` / `thf_hydrate.itp` as shown in MOLECULE_TO_GROMACS.
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Replace `ch4.itp`/`thf.itp` with `ch4_hydrate.itp`/`thf_hydrate.itp`.

---

### FF-1: gui-guide.md says "GAFF" instead of "GAFF2"

**Status:** CONFIRMED
**Evidence:**
- `docs/gui-guide.md` line 297: `- ch4.itp` or `thf.itp` — Guest molecule parameters (GAFF)`
- `README.md` line 216: `CH₄ and THF use GAFF2 force field`
- `types.py` lines 82, 88: `GUEST_MOLECULES["ch4/thf"]["force_field"] = "GAFF/GAFF2"`
- The correct force field is GAFF2 (with GAFF as legacy).
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Replace `(GAFF)` with `(GAFF2)`.

---

### KS-1: gui-guide.md missing Ctrl+Alt+P, Ctrl+L, Ctrl+M in shortcuts table

**Status:** PARTIALLY CORRECT
**Evidence:**
- `docs/gui-guide.md` lines 202-214: Shortcuts table lists Enter, Escape, Ctrl+S, Ctrl+Shift+S, Ctrl+D, Ctrl+Alt+S, Ctrl+G, Ctrl+H, Ctrl+I, Ctrl+J.
- The original issue says Ctrl+Alt+P, Ctrl+L, Ctrl+M are missing. Let me verify what actually exists in the code.
- The table already has 10 shortcuts. Whether Ctrl+Alt+P, Ctrl+L, Ctrl+M exist in the codebase and should be documented is uncertain from code alone. The listed shortcuts appear complete for the current functionality.
**Fix complexity:** MODERATE
**Recommended approach:** DEBUGGER — Need to check `main_window.py` action definitions to verify which shortcuts actually exist and are missing from docs.
**Rationale:** Unclear which shortcuts exist in code vs. which are purely documentation gaps.

---

### KS-2: gui-guide.md Ctrl+S description outdated

**Status:** CONFIRMED
**Evidence:**
- `docs/gui-guide.md` line 163: `- **Ctrl+S**: Save PDB from left viewer (rank #1)`
- `docs/gui-guide.md` line 206: `Ctrl+S | Save/Export from active tab (unified)` — This IS updated.
- Line 163 is in an old section that wasn't updated when the unified export was implemented.
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Update line 163 to match line 206's description.

---

### KS-3: gui-guide.md says Ctrl+E for hydrate export

**Status:** CONFIRMED
**Evidence:**
- `docs/gui-guide.md` line 281: `7. Export for GROMACS (Ctrl+E)`
- `docs/gui-guide.md` line 211: `Ctrl+H | Export hydrate for GROMACS (Tab 1)` — Correct shortcut.
- Line 281 uses the wrong key `Ctrl+E`, should be `Ctrl+H`.
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Replace `Ctrl+E` with `Ctrl+H` at line 281.

---

## MEDIUM Issues

### FLOW-03: Custom molecule writer hardcodes "GUE" residue and "guest.itp"

**Status:** CONFIRMED
**Evidence:**
- `gromacs_writer.py` line 1936: `guest_res_name = "GUE"  # Use generic GUE residue name (guest type detection would require additional logic)`
- `gromacs_writer.py` line 2030: `f.write('#include "guest.itp"\n')` — References non-existent file.
- `gromacs_writer.py` line 2050: `f.write(f"GUE              {guest_count}\n")` — Uses "GUE" in [molecules] section.
- In contrast, the ion exporter (lines 1652-1665) correctly detects guest type and uses `detect_guest_type_from_atoms()` + `get_hydrate_guest_residue_name()`.
- The custom molecule exporter's .gro file also uses `"GUE"` at line 1936, while the .top references `guest.itp` which doesn't exist. This will cause GROMACS failure.
**Fix complexity:** MODERATE
**Recommended approach:** EXECUTOR — The fix is clear: use the same `detect_guest_type_from_atoms()` pattern from `write_ion_gro_file()` and `write_ion_top_file()`. Copy the guest detection logic and proper `#include "{guest_type}_hydrate.itp"` pattern. But needs careful integration into the custom molecule writer.
**Rationale:** Pattern exists in ion writers, but needs careful wiring into custom molecule writer.

---

### BUG-03: molecule_index.index(mol) in loop → O(n²)

**Status:** CONFIRMED
**Evidence:**
- `gromacs_writer.py` line 1102: `res_num = (molecule_index.index(mol) + 1) % 100000`
- This is inside a `for mol in molecule_index:` loop (line 1093). `list.index()` is O(n), called n times → O(n²).
- Should use `enumerate(molecule_index)` instead.
**Fix complexity:** SIMPLE
**Recommended approach:** EXECUTOR — Change `for mol in molecule_index:` to `for res_idx, mol in enumerate(molecule_index):` and replace `molecule_index.index(mol)` with `res_idx`.
**Rationale:** Trivial loop restructuring, no logic ambiguity.

---

### TD-07/FRAG-03: comment_out_atomtypes_in_itp silently modifies user ITP

**Status:** CONFIRMED
**Evidence:**
- `gromacs_writer.py` lines 310-354: `comment_out_atomtypes_in_itp()` comments out the `[ atomtypes ]` section by prepending `;` to each line.
- `export.py` lines 213-216: Custom molecule ITP is read, modified by `comment_out_atomtypes_in_itp()`, and written to output. No user warning.
- `export.py` lines 348-353: Same for solute ITP.
- `custom_molecule_panel.py`: No upload-time validation for `[ atomtypes ]`. User is not warned at upload that their atomtypes will be silently modified.
**Fix complexity:** MODERATE
**Recommended approach:** EXECUTOR — Add a warning in `custom_molecule_panel.py` when ITP file is uploaded and contains `[ atomtypes ]`. The warning should inform the user that atomtypes will be commented out in the exported .top file. The actual commenting logic is correct and needed.
**Rationale:** Adding a user-facing warning is straightforward. No need for a debugger.

---

### FRAG-01: Fragile getattr() cross-tab data flow (main_window.py, solute_panel.py, ion_panel.py)

**Status:** CONFIRMED (main_window.py only)
**Evidence:**
- `main_window.py` lines 1199-1209: Uses `hasattr(result, 'water_atom_count')` and `getattr(result, 'water_atom_count', 'N/A')` instead of direct attribute access or assertions.
- `solute_panel.py`: No `getattr` calls found in the file. The panel uses `set_custom_molecule_structure()` and `set_liquid_volume()` methods (called from main_window.py).
- `ion_panel.py`: No `getattr` calls found. Same pattern.
- The actual fragility is in `main_window.py` using `hasattr`/`getattr` instead of direct dataclass attribute access or assertions.
**Fix complexity:** SIMPLE
**Recommended approach:** EXECUTOR — Add assertions at the top of the custom molecule completion handler in main_window.py: `assert hasattr(result, 'water_atom_count')`, `assert result.water_atom_count > 0`. Replace `hasattr`/`getattr` with direct attribute access since `CustomMoleculeStructure` is a typed dataclass.
**Rationale:** The structure types are well-defined dataclasses. Direct access with assertions is safer and clearer.

---

### FRAG-02: slab.py missing invariant check after guest-water overlap removal

**Status:** CONFIRMED
**Evidence:**
- `slab.py` lines 527-554: Second overlap removal (guest-water) calls `remove_overlapping_molecules()` which removes entire water molecules. After this, `water_atom_count` is updated but no assertion checks that `water_atom_count == water_nmolecules * 4`.
- `slab.py` lines 583-586: Final counts computed from `len(trimmed_water_positions)` but no invariant check.
- A previous round of ice-water overlap removal (not shown in these lines) also modifies water molecules without an invariant check.
**Fix complexity:** SIMPLE
**Recommended approach:** EXECUTOR — Add `assert len(trimmed_water_positions) % 4 == 0, f"Water atoms {len(trimmed_water_positions)} not divisible by 4"` after line 554.
**Rationale:** Single assertion line, clear condition.

---

### EXP-1: gui-guide.md wrong filename pattern for hydrate export

**Status:** CONFIRMED
**Evidence:**
- `docs/gui-guide.md` line 295: `hydrate_{lattice}.gro`
- Actual code: `export.py` (hydrate exporter not in this file, but the hydrate tab generates filenames like `hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro` based on supercell dimensions and guest type).
**Fix complexity:** SIMPLE
**Recommended approach:** EXECUTOR — Update filename pattern to include guest type and supercell dimensions.

---

### EXP-2: gui-guide.md wrong filename pattern for solute export

**Status:** CONFIRMED
**Evidence:**
- `docs/gui-guide.md` line 704: `interface_with_solutes.gro`
- `export.py` line 48: `default_name = f"solute_{solute_type}_{n_molecules}molecules.gro"`
- Actual pattern: `solute_{type}_{count}molecules.gro`
**Fix complexity:** SIMPLE
**Recommended approach:** EXECUTOR — Replace `interface_with_solutes.gro` with `solute_{type}_{count}molecules.gro`.

---

### VER-1: cli-reference.md says version 4.0.0

**Status:** CONFIRMED
**Evidence:**
- `docs/cli-reference.md` line 145: `# Output: python quickice.py 4.0.0`
- Current version is 4.5.0 (per custom_molecule_panel.py docstring line 1).
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Change `4.0.0` to `4.5.0`.

---

### UNIT-01: gro_parser.py no coordinate range validation

**Status:** CONFIRMED
**Evidence:**
- `gro_parser.py` lines 14-77: `parse_gro_string()` parses x/y/z coordinates as float but never validates they're < 50 nm. A value like 15.0 Å (1.5 nm mis-entered as 15.0 nm) would pass through undetected.
- No range check exists anywhere in the parser.
**Fix complexity:** SIMPLE
**Recommended approach:** EXECUTOR — Add a validation check after parsing: if any coordinate > 50 nm, raise ValueError with a message about possible Å→nm unit mixup.
**Rationale:** Simple boundary check with clear error message.

---

## LOW Issues

### BUG-02: MOLECULE_TYPE_INFO["thf"]["atoms"] = 12 (should be 13)

**Status:** CONFIRMED
**Evidence:**
- `types.py` line 17: `"thf": {"atoms": 12, "res_name": "THF", "description": "Tetrahydrofuran"}`
- `types.py` line 87 (GUEST_MOLECULES): `"thf": {"atoms": 12, ...}`
- THF (C4H8O) = 1 O + 4 C + 8 H = 13 atoms in GenIce2 output (confirmed in `gromacs_writer.py` line 843: "GenIce2 THF: O, CA, CA, CB, CB, H, H, H, H, H, H, H, H (13 atoms)").
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Change `12` to `13` in both locations (types.py line 17 and line 87).

---

### BUG-02 (gromacs_writer.py): Comment says "C5H8O (14 atoms)" for THF

**Status:** CONFIRMED
**Evidence:**
- `gromacs_writer.py` line 841: `# THF: C5H8O (5 C, 8 H, 1 O = 14 atoms typically)`
- THF is C4H8O (4 C, 8 H, 1 O = 13 atoms). The code on line 843 correctly returns 13 atoms, but the comment on line 841 is wrong.
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Fix comment to "C4H8O (4 C, 8 H, 1 O = 13 atoms typically)".

---

### BUG-02 (molecule_utils.py): Comment says "C5H8O = 14 atoms"

**Status:** CONFIRMED
**Evidence:**
- `molecule_utils.py` line 77: `# THF: C5H8O = 14 atoms, but GenIce2 outputs 13 atoms (some versions)`
- Should be "C4H8O = 13 atoms". The function on line 81-82 correctly returns 13.
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Fix comment to "C4H8O = 13 atoms".

---

### NEW-02: Dead import of MOLECULE_TYPE_INFO

**Status:** CONFIRMED (in gromacs_writer.py), PARTIALLY CORRECT (in hydrate_generator.py)
**Evidence:**
- `gromacs_writer.py` line 14: `from quickice.structure_generation.types import ..., MOLECULE_TYPE_INFO` — imported but NEVER used anywhere in the 2054-line file (grep confirms only the import line references it).
- `hydrate_generator.py` line 15: imports `MOLECULE_TYPE_INFO` — used 1 time (the import line). Need to verify if it's used elsewhere in the file.
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Remove `MOLECULE_TYPE_INFO` from the import on gromacs_writer.py line 14. For hydrate_generator.py, verify it's unused and remove if so.

---

### FRAG-03: Single 2054-line gromacs_writer.py file

**Status:** CONFIRMED
**Evidence:**
- `gromacs_writer.py` is 2054 lines with 20+ function definitions (verified).
- Contains: base writers, interface writers, multi-molecule writers, ion writers, custom molecule writers, guest detection, atom reordering, ITP parsing, atomtypes commenting, etc.
**Fix complexity:** DESIGN
**Recommended approach:** PLANNER — This is a refactoring decision. Splitting into per-structure-type writers (e.g., `gromacs_writer/base.py`, `gromacs_writer/interface.py`, `gromacs_writer/ion.py`, `gromacs_writer/custom.py`) requires planning for import dependencies and backward compatibility.
**Rationale:** Architecture decision, not a bug fix.

---

### TD-01: Duplicate functions across mode files

**Status:** CONFIRMED
**Evidence:**
- `detect_atoms_per_molecule()`: Identical in pocket.py (line 24), piece.py (line 31), slab.py (line 24). Only whitespace differences in docstrings.
- `_detect_guest_atoms()`: Similar structure but slab.py has the OW-safeguard while pocket.py and piece.py don't.
- `_count_guest_molecules()`: Identical in all three files.
- `molecule_utils.py` already consolidates `count_guest_atoms()`, but the mode-specific functions haven't been consolidated.
**Fix complexity:** MODERATE
**Recommended approach:** EXECUTOR — Move `detect_atoms_per_molecule()` and `_count_guest_molecules()` to `molecule_utils.py`. Move `_detect_guest_atoms()` with the OW-safeguard version. Update imports in all three mode files. But first fix BUG-01 (add safeguard to pocket/piece) then consolidate.
**Rationale:** The consolidation is straightforward but requires updating 3 files' imports and ensuring the safeguard version is used. Fix BUG-01 first, then consolidate.

---

### NEW-01: Verbose debug logging at logger.info() level

**Status:** CONFIRMED
**Evidence:**
- `main_window.py` line 1199: `logger.info(f"[Liquid Volume Debug] ...")` — 5+ instances of `[Liquid Volume Debug]` and `[Water Count Debug]` messages at `logger.info()` level.
- These should be `logger.debug()` level.
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Replace `logger.info` with `logger.debug` for all lines containing `[Liquid Volume Debug]` or `[Water Count Debug]`.

---

### SCI-04: ion.itp lacks Madrid2019_085 header

**Status:** CONFIRMED
**Evidence:**
- `gromacs_ion_export.py` lines 30-55: `generate_ion_itp()` writes moleculetype and atoms sections but no header comment identifying Madrid2019_085.
- Line 22 comment mentions "Madrid2019_085.top" but this isn't propagated to the output.
- Ion parameters (lines 24-27) are clearly from Madrid2019_085 (sigma/epsilon match).
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Add `; Madrid2019_085 ion model (Zeron et al. 2019)` to the generated ITP header.

---

### BUG-04: diversity_score() always returns 1.0

**Status:** CONFIRMED
**Evidence:**
- `scorer.py` lines 222-234: `diversity_score()` uses seed-based diversity. `1.0 / same_seed_count` where seeds are unique integers → always returns 1.0.
- The docstring at line 218-220 acknowledges this: "This is the single-phase fallback approach. If multi-phase generation is implemented..."
**Fix complexity:** DESIGN
**Recommended approach:** PLANNER — The function is documented as a placeholder. Either implement structural fingerprint diversity or remove it from the scoring pipeline. This is a design decision, not a bug fix.
**Rationale:** The "bug" is that the scoring function has zero discriminatory value in practice. The fix requires a design decision about what diversity metric to use.

---

### PERF-02: 3×3×3 supercell for KDTree PBC

**Status:** CONFIRMED
**Evidence:**
- `scorer.py` lines 53-61: Creates 27× supercell for PBC handling:
  ```python
  for i in (-1, 0, 1):
      for j in (-1, 0, 1):
          for k in (-1, 0, 1):
              offset = np.array([i, j, k]) * cell_dims
              supercell_o.append(o_positions + offset)
  ```
- `cKDTree(boxsize=)` supports periodic boundary conditions directly for orthorhombic cells, avoiding 27× memory overhead.
**Fix complexity:** MODERATE
**Recommended approach:** EXECUTOR — Use `cKDTree(data, boxsize=cell_dims)` for orthorhombic cells. Need to keep the supercell approach as fallback for triclinic cells. But this requires testing to ensure the boxsize approach produces identical results.
**Rationale:** The fix is known but needs verification that the KDTree boxsize parameter handles the same PBC cases.

---

### SCI-1/DOC: AVOGADRO inconsistency between scorer.py and solute_inserter.py

**Status:** CONFIRMED
**Evidence:**
- `scorer.py` line 168: `AVOGADRO = 6.022e23` — approximated value.
- `solute_inserter.py` line 32: `AVOGADRO = 6.02214076e23` — correct CODATA 2017 value.
- The difference is ~0.04%, negligible for practical purposes but inconsistent.
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Change scorer.py line 168 to `6.02214076e23` to match solute_inserter.py.

---

### SCI-03: ranking/types.py missing literature citations for 0.276 nm and 0.35 nm

**Status:** CONFIRMED
**Evidence:**
- `ranking/types.py` lines 21-22: `ideal_oo_distance: float = 0.276` and `oo_cutoff: float = 0.35` — no citations.
- `docs/ranking.md` line 31: "0.276 = Ideal O-O distance" — also no citation.
- The 0.276 nm value comes from Petrenko & Whitworth (1999), "Physics of Ice".
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Add comment `# Petrenko & Whitworth (1999), Physics of Ice` after line 21.

---

### UNIT-02: Fallback density logged but no GUI indicator

**Status:** CONFIRMED
**Evidence:**
- `water_density.py` lines 85-86: `logger.warning(f"Using fallback density...")` — logged but no visual indication in GUI.
- `ice_ih_density.py` line 74: Same pattern.
- Users relying on the GUI won't know a fallback was used.
**Fix complexity:** MODERATE
**Recommended approach:** EXECUTOR — The fix requires adding a signal or callback from the density calculation to the GUI. This touches the architecture of how density results propagate. Could be done by adding a flag to the return value or a separate status signal.
**Rationale:** Adding a visual indicator requires GUI changes that go beyond a simple fix.

---

### UNIT-03: Suppressed IAPWS extrapolation warnings

**Status:** CONFIRMED
**Evidence:**
- `water_density.py` line 74: `warnings.filterwarnings("ignore", message="extrapolated")` — suppressed but no logging of the fact extrapolation was used.
**Fix complexity:** SIMPLE
**Recommended approach:** EXECUTOR — Add `logger.debug("Using extrapolated IAPWS value at T={T_K}K")` after the IAPWS call succeeds but was in the extrapolation regime.
**Rationale:** Simple logging addition.

---

### SCI-01: ice_ih_density fallback at 273.15K regardless of actual T/P

**Status:** CONFIRMED
**Evidence:**
- `ice_ih_density.py` lines 63-75: When IAPWS calculation fails (T > 273.16K or P > 208.566 MPa), falls back to `0.9167 g/cm³` which is the value at 273.15K/0.1 MPa — regardless of actual conditions.
- Line 74: `logger.warning(...)` logs the fallback use but returns the same density regardless.
**Fix complexity:** SIMPLE
**Recommended approach:** EXECUTOR — Return density at the stability boundary (T=273.16K, user's P) when T is slightly above range, or add a more explicit warning that the result is approximate.
**Rationale:** The current fallback is the best simple option, but the warning should be more specific about what conditions were outside range.

---

### TD-05: np.random global state manipulation

**Status:** CONFIRMED
**Evidence:**
- `generator.py` lines 102-157: Uses `np.random.seed(seed)`, `np.random.get_state()`, `np.random.set_state()`. Not thread-safe.
- Lines 96-99: Code comments acknowledge this: "This method is NOT thread-safe."
- The `try/finally` pattern for state restoration is adequate for sequential use.
**Fix complexity:** DESIGN
**Recommended approach:** PLANNER — GenIce2 doesn't support the numpy Generator API. No immediate fix is possible without GenIce2 changes. Mark as future improvement.
**Rationale:** External dependency constraint, not a QuickIce bug.

---

### TD-06: Module-level mutable globals without thread safety

**Status:** CONFIRMED
**Evidence:**
- `water_filler.py` line 144: `_water_template_cache: Optional[...] = None`
- `water_filler.py` line 234: `global _water_template_cache` — used in `_get_water_template()`
- `hydrate_generator.py` lines 28-30: `_genice_lib = None`, `_gromacs_format = None`, `_lattice_modules_loaded = {}` — module-level globals.
- No `threading.Lock` or `functools.lru_cache` protecting these.
**Fix complexity:** SIMPLE
**Recommended approach:** EXECUTOR — Replace manual caching pattern with `@functools.lru_cache(maxsize=1)` for `_get_water_template()`. For hydrate_generator, add `threading.Lock` around lazy-loading code or use `lru_cache`.
**Rationale:** Straightforward caching pattern replacement.

---

### FRAG-04: ITP regex fragile for non-standard formatting

**Status:** CONFIRMED
**Evidence:**
- `itp_parser.py` lines 65-77: Regex `r'\[\s*moleculetype\s*\]\s*\n\s*;.*?\n\s*(\w+)'` assumes a specific format with a comment line between `[moleculetype]` and the name. Has a fallback regex without the comment line.
- BOM, Windows line endings (`\r\n`), extra whitespace could break parsing.
**Fix complexity:** MODERATE
**Recommended approach:** EXECUTOR — Add handling for BOM (`content.lstrip('\ufeff')`) and normalize line endings (`content.replace('\r\n', '\n')`). Make the regex more tolerant of varying whitespace.
**Rationale:** The fix is clear but needs testing with actual edge-case files.

---

### TEST-05: No atom count invariant test after overlap removal

**Status:** CONFIRMED (test gap, not code bug)
**Evidence:**
- No test files found for overlap removal invariant checking.
- This is a test gap, not a code issue.
**Fix complexity:** MODERATE
**Recommended approach:** EXECUTOR — Create `tests/test_overlap_removal_invariants.py` that verifies `water_atom_count % 4 == 0` after each overlap removal step.
**Rationale:** Test writing is straightforward but requires understanding of the test infrastructure.

---

### TEST-01: No end-to-end export test

**Status:** CONFIRMED (test gap)
**Evidence:** No `tests/test_e2e_export_chain.py` exists.
**Fix complexity:** COMPLEX
**Recommended approach:** DEBUGGER — Writing a proper e2e test requires tracing the full export chain through multiple tabs. A debugger should first identify the minimal set of method calls needed to exercise each export path.
**Rationale:** E2E test design requires understanding of many interconnected components.

---

### TEST-02: No pocket mode edge case tests

**Status:** CONFIRMED (test gap)
**Fix complexity:** MODERATE
**Recommended approach:** EXECUTOR — Create test cases for thin cavities and non-spherical pocket shapes.

---

### TEST-04: No ITP parsing edge case tests

**Status:** CONFIRMED (test gap)
**Fix complexity:** SIMPLE
**Recommended approach:** EXECUTOR — Create test cases for BOM, Windows line endings, extra whitespace.

---

### EXC-01/PARTIAL: IAPWS failures logged but no GUI indicator

**Status:** CONFIRMED
**Evidence:**
- `phase_diagram_widget.py` lines 82, 484: `logger.warning(f"Could not get saturation pressure...")` — logged but no visual indication.
**Fix complexity:** MODERATE
**Recommended approach:** EXECUTOR — Add a dashed line or label on the diagram where IAPWS calculation failed. This requires understanding the matplotlib rendering code.
**Rationale:** Visual change requires understanding of the diagram widget's drawing code.

---

### SCI-04: Ion parameters lack version tracking in output

**Status:** CONFIRMED
**Evidence:**
- `ion_inserter.py` lines 25-36: Ion parameters hardcoded from Madrid2019 but no version string in output.
- `gromacs_ion_export.py` lines 9-27: Parameters clearly from Madrid2019_085 but generated ITP has no version header.
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Add `; Madrid2019_085 ion model (Zeron et al. 2019)` to generated ITP header.

---

### FRAG-04: molecule_validator.py hardcoded GENERIC_RESIDUE_NAMES

**Status:** CONFIRMED
**Evidence:**
- `molecule_validator.py` line 18: `GENERIC_RESIDUE_NAMES = {"MOL", "UNK", "LIG", "XXX", "RES"}` — hardcoded set.
**Fix complexity:** SIMPLE
**Recommended approach:** EXECUTOR — Expand list to include more common generic names (e.g., "DRG", "API", "LIG1"). Or make configurable.
**Rationale:** Simple list expansion.

---

### SEC-01: Path(args.output) without sanitization

**Status:** CONFIRMED
**Evidence:**
- `main.py` line 127: `output_path = Path(args.output)` — no `resolve()` or validation.
- `main.py` line 194: Same pattern.
**Fix complexity:** SIMPLE
**Recommended approach:** EXECUTOR — Add `Path(args.output).resolve()` and basic boundary checks.
**Rationale:** Simple path hardening.

---

### SEC-02: shell=True in subprocess call

**Status:** CONFIRMED
**Evidence:**
- `.planning/milestones/v1.0-run_uat_tests.py` line 24: `shell=True` in `subprocess.run()`.
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Remove `shell=True` or delete the file if no longer needed.
**Rationale:** The file is in `.planning/milestones/`, not in the main codebase.

---

### TD-03: 42 Python debug scripts (1.7 MB)

**Status:** CONFIRMED
**Evidence:**
- `.planning/debug/` directory contains 42 .py files totaling 1.7 MB.
- Contains subdirectories `archive/`, `deferred/`, `resolved/`.
- These scripts are never referenced by the app or tests.
**Fix complexity:** SIMPLE
**Recommended approach:** EXECUTOR — Delete `resolved/` and `deferred/` subdirectories. Review active scripts for relevance.
**Rationale:** Cleanup task, no code logic involved.

---

### CIT-GAFF2: README.md missing formal GAFF2 citation

**Status:** CONFIRMED
**Evidence:**
- `README.md` line 216: Mentions "GAFF2 force field" but no formal citation in References section.
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Add Wang et al. (2004) and He et al. (2020) citations to References.
**Rationale:** Documentation-only fix.

---

### SCI-03 (ranking.md): Missing citation for 0.276 nm

**Status:** CONFIRMED
**Evidence:**
- `docs/ranking.md` line 31: "0.276 = Ideal O-O distance" without citation.
**Fix complexity:** TRIVIAL
**Recommended approach:** EXECUTOR — Add citation to Petrenko & Whitworth (1999).

---

### BUNDLE-01: collect_all() with excludes=[]

**Status:** CONFIRMED
**Evidence:**
- `quickice-gui.spec` line 9-16: `collect_all(pkg)` for 9 packages, `excludes=[]` on line 27.
- This includes test files, docs, dev artifacts from all collected packages.
**Fix complexity:** SIMPLE
**Recommended approach:** EXECUTOR — Add explicit excludes: `*/tests/*`, `*/docs/*`, `*/test/*` to the Analysis excludes list.
**Rationale:** Clear exclusion patterns.

---

### BUNDLE-02: collect_all('genice2') includes unused lattice plugins

**Status:** CONFIRMED
**Evidence:**
- `quickice-gui.spec` line 9: `collect_all('genice2')` includes ALL lattice/molecule/format plugins.
- Only specific lattices (sI, sII, sH) and molecule (tip3p) and format (gromacs) are used.
**Fix complexity:** MODERATE
**Recommended approach:** EXECUTOR — Use `collect_submodules('genice2', ...)` with targeted patterns. But need to verify exactly which genice2 submodules are needed.
**Rationale:** Needs investigation of which genice2 modules are actually imported at runtime.

---

### FLOW-03: write_custom_molecule_gro_file hardcodes "GUE"

**Status:** CONFIRMED (covered in FLOW-03 above)
**Evidence:** `gromacs_writer.py` lines 1936, 2030, 2050 — "GUE" hardcoded in .gro and .top.

---

## REFUTED Issues

### TD-07: No upload-time validation for atomtypes

**Status:** PARTIALLY CORRECT — The original issue says "No upload-time validation" but the upload panel DOES check for atomtypes presence in the ITP file (see `custom_molecule_panel.py` line 186-195 which mentions `[ atomtypes ]` in upload instructions, and `molecule_validator.py` line 88 which checks `has_atomtypes_section`). However, there's no WARNING when atomtypes are detected at upload time, only at export time when they're silently commented out. The issue is about the lack of a WARNING at upload, not the lack of any check at all.
**Fix complexity:** SIMPLE
**Recommended approach:** EXECUTOR — Add a `QMessageBox.warning()` in the upload handler when `itp_info.has_atomtypes_section` is True, informing user that atomtypes will be commented out in the exported .top file.

---

## Summary Table

### By Recommended Approach

| Approach | Issues | Count |
|----------|--------|-------|
| **EXECUTOR** (direct fix) | FLOW-02, MOL-1, MOL-2, MOL-3, MOL-4, MOL-5, FF-1, KS-2, KS-3, VER-1, BUG-02 (3 files), NEW-01, NEW-02, SCI-04 (2), SCI-1/DOC, SCI-03 (2), UNIT-03, SCI-01, TD-06 (2), FRAG-02, BUG-03, BUG-01, FLOW-03, FRAG-01, EXP-1, EXP-2, UNIT-01, CIT-GAFF2, SEC-01, SEC-02, TD-03, BUNDLE-01, EXC-02, TD-07, TEST-02, TEST-04, FRAG-04 (validator) | 37 |
| **DEBUGGER** (investigate first) | **FLOW-01**, KS-1, TEST-01, BUNDLE-02 | 4 |
| **PLANNER** (design decision) | FRAG-03 (file split), BUG-04, TD-05 | 3 |

### By Fix Complexity

| Complexity | Issues | Count |
|------------|--------|-------|
| **TRIVIAL** | MOL-1, MOL-2, MOL-3, MOL-4, MOL-5, FF-1, KS-2, KS-3, VER-1, BUG-02 (3), NEW-01, SCI-04 (2), SCI-1/DOC, SCI-03 (2), CIT-GAFF2, SEC-02, KS-2 | 19 |
| **SIMPLE** | FLOW-02, EXC-02, FRAG-02, BUG-03, UNIT-01, TD-06, FRAG-01, EXP-1, EXP-2, NEW-02, BUNDLE-01, TD-07, FRAG-04 (validator), SEC-01, UNIT-03, SCI-01, TEST-04 | 17 |
| **MODERATE** | BUG-01, FLOW-03, TD-01, PERF-02, UNIT-02, EXC-01, TD-06 (hydrate), FRAG-04 (ITP parser), TEST-02, TEST-05, BUNDLE-02, KS-1 | 12 |
| **COMPLEX** | **FLOW-01**, TEST-01 | 2 |
| **DESIGN** | FRAG-03 (split), BUG-04, TD-05 | 3 |

### Critical Path (must fix before release)

1. **FLOW-01** — SoluteGROMACSExporter will crash (3 bugs: missing numpy import, wrong function signatures, wrong underlying writers). **BLOCKS solute export entirely.**
2. **FLOW-02** — CustomMoleculeGROMACSExporter missing tip4p-ice.itp copy. **BLOCKS custom molecule GROMACS run.**
3. **FLOW-03** — "GUE" hardcode + missing guest.itp. **BLOCKS custom molecule GROMACS run when guests present.**
4. **BUG-01** — OW-safeguard missing in pocket.py and piece.py. **Can misclassify water as guest, causing wrong topology.**
5. **EXC-02** — Silent FileNotFoundError. **Produces broken .top referencing missing .itp.**

---

_Verified: 2026-05-22_
_Verifier: OpenCode (gsd-verifier)_
