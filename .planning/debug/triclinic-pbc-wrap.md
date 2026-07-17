---
status: resolved
trigger: "triclinic-pbc-wrap (scancode CRIT-01, Group 1 of an approved fix plan)"
created: 2026-07-17T00:00:00Z
updated: 2026-07-17T01:00:00Z
---

## Current Focus

hypothesis: CONFIRMED (verified by prior research + re-confirmed by direct code read).
  `wrap_positions_into_box` (gromacs_writer.py:308) and `wrap_molecules_into_box`
  (gromacs_writer.py:352) use diagonal-only modulo on `cell[dim,dim]`, which is only
  correct for orthogonal cells. Triclinic hydrate cells (sH/c0te/c1te) have non-zero
  off-diagonal shear (parsed at hydrate_generator.py:414-430), so atoms end up outside
  the cell after the diagonal-only wrap. The hydrate export path reaches this via
  pipeline.py:928 → write_interface_gro_file:1131-1136 → wrap_molecules_into_box,
  passing `hydrate.cell` (triclinic). Hydrate positions are intentionally unwrapped
  upstream (hydrate_generator.py:186-189), so the FIRST wrap happens at export — here.
test: apply the proven fractional-coordinate wrap pattern from
  water_filler.wrap_positions_triclinic (water_filler.py:84-129) behind an
  `is_cell_orthogonal(cell)` branch (cell_utils.py). Orthogonal path MUST stay on the
  existing diagonal-modulo fast path (slab interfaces are forced orthogonal at
  slab.py:619, so slab tests must pass byte-identical).
expecting: after fix, every exported atom position for a triclinic sH hydrate
  satisfies `0 <= frac <= 1` where `frac = pos @ inv(cell.T)`; orthogonal slab
  tests unchanged; full pytest suite has zero new failures.
next_action: apply the triclinic-aware branch to both wrap functions, add the
  regression test, run the targeted + full suite, then atomic commit.

## Symptoms

expected: Every exported atom position lies inside the simulation cell
  (0 <= fractional coordinate <= 1) for BOTH orthogonal and triclinic cells.
actual: For triclinic hydrate cells (off-diagonal elements nonzero), the
  diagonal-only `np.mod(wrapped[:, dim], cell[dim, dim])` wrap leaves atoms
  outside the cell because it ignores off-diagonal shear.
errors: No runtime exception — a silent geometric artifact. Exported atoms
  appear outside the triclinic box when inspected in VMD/gmx.
reproduction: Generate an sH (or c0te/c1te) hydrate (triclinic cell, parsed at
  hydrate_generator.py:414-430), export via the GRO path (write_interface_gro_file
  reached from pipeline.py:928 which passes hydrate.cell). Convert output
  positions to fractional coords via `frac = pos @ inv(cell.T)` and assert
  `0 <= frac <= 1`; the bug shows frac components outside [0,1].
started: Present since the diagonal-only wrap was written. Affects all triclinic
  hydrate exports.

## Evidence

- timestamp: 2026-07-17T00:00:00Z
  checked: gromacs_writer.py:291-309 (wrap_positions_into_box)
  found: line 308 `wrapped[:, dim] = np.mod(wrapped[:, dim], cell[dim, dim])`
    — per-axis modulo using ONLY diagonal cell elements. Correct for orthogonal
    cells; ignores off-diagonal shear for triclinic cells.
  implication: Per-atom wrap is wrong for triclinic cells.

- timestamp: 2026-07-17T00:00:00Z
  checked: gromacs_writer.py:312-382 (wrap_molecules_into_box)
  found: line 352 `box_sizes = np.array([cell[d, d] for d in range(3)])` (diagonal
    only) used for BOTH the unwrap step (lines 352-364: half_box, mask_ahead/
    mask_behind shifts) AND the center wrap (line 373 `center_wrapped = np.mod(
    center, box_sizes)`). Both ignore off-diagonal shear.
  implication: Molecule-aware wrap is wrong for triclinic cells in both its
    unwrap and its center-wrap steps.

- timestamp: 2026-07-17T00:00:00Z
  checked: water_filler.py:84-129 (wrap_positions_triclinic — proven reference)
  found: `inv_cell_T = np.linalg.inv(cell.T)`; per molecule: `mol_frac = mol @
    inv_cell_T`; `com_frac = mol_frac.mean(axis=0)`; `shift_frac = -np.floor(
    com_frac)`; `mol_frac += shift_frac`; `wrapped = mol_frac @ cell.T`. This
    handles BOTH unwrap and wrap in one step via fractional coords, naturally
    accounting for triclinic shear.
  implication: Reuse this exact pattern (adapted for variable-size molecule_index)
    for the triclinic branch of wrap_molecules_into_box; use the per-atom
    fractional modulo `frac = pos @ inv(cell.T); frac = np.mod(frac, 1.0);
    wrapped = frac @ cell.T` for wrap_positions_into_box.

- timestamp: 2026-07-17T00:00:00Z
  checked: cell_utils.py:9-47 (is_cell_orthogonal)
  found: Established shared helper, already imported by water_filler.py:18.
    Checks off-diagonal elements with tol=1e-10. Returns True for diagonal cells.
  implication: Use `is_cell_orthogonal(cell)` for the branch — reuses the
    existing shared helper rather than a local np.allclose check.

- timestamp: 2026-07-17T00:00:00Z
  checked: types.py:84-199 (HYDRATE_LATTICES)
  found: sH (:119), c0te (:131), c1te (:142) have `is_triclinic: True`. sI/sII/
    c2te/ice1hte/sTprime/16/17 are `is_triclinic: False`.
  implication: The bug triggers for sH/c0te/c1te hydrate exports; orthogonal
    hydrate exports (sI/sII) are unaffected.

- timestamp: 2026-07-17T00:00:00Z
  checked: hydrate_generator.py:186-189 and :403-409 and :411-430
  found: Positions are intentionally NOT wrapped upstream ("Do NOT wrap
    positions. GenIce2 outputs complete molecules..."). Cell is parsed from
    the 9-value GRO box line at :414-430 into a full 3x3 matrix (off-diagonal
    elements v1y/v1z/v2x/v2z/v3x/v3y populated).
  implication: First wrap happens at export time (the gromacs_writer functions).
    CONFIRMS the fix location is the export wrap functions, NOT upstream.

- timestamp: 2026-07-17T00:00:00Z
  checked: pipeline.py:900-928 and modes/slab.py:619
  found: pipeline.py:907-920 builds an InterfaceStructure wrapper with
    `cell=hydrate.cell` (triclinic for sH/c0te/c1te) and `molecule_index=
    hydrate.molecule_index`; pipeline.py:928 calls write_interface_gro_file(
    wrapper, gro_path, ...). Inside write_interface_gro_file:1131-1136,
    `if iface.molecule_index:` → wrap_molecules_into_box(iface.positions,
    iface.molecule_index, iface.cell). slab.py:619 forces orthogonal:
    `cell = np.diag([adjusted_box_x, adjusted_box_y, adjusted_box_z])`.
  implication: The hydrate export path reaches wrap_molecules_into_box with a
    triclinic cell (bug site). The slab/interface path reaches it with an
    orthogonal cell (correct fast path — MUST stay unchanged).

- timestamp: 2026-07-17T00:00:00Z
  checked: existing tests test_output/test_molecule_wrapping.py and
    test_pbc_wrapping.py and test_scancode_bugs_gromacs.py (MW-01)
  found: All use ORTHOGONAL cells (diagonal). My fix keeps the orthogonal
    branch byte-identical, so these tests must pass unchanged.
  implication: Safe to add a triclinic branch; orthogonal regression coverage
    already exists and will guard the fast path.

## Resolution

root_cause: wrap_positions_into_box (gromacs_writer.py:308) and
  wrap_molecules_into_box (gromacs_writer.py:352) wrapped atom/molecule positions
  using diagonal-only modulo on `cell[dim,dim]`, which is correct only for
  orthogonal cells. For triclinic hydrate cells (sH/c0te/c1te — non-zero
  off-diagonal cell elements parsed at hydrate_generator.py:414-430), the
  diagonal-only wrap ignores off-diagonal shear and silently leaves atoms
  outside the simulation cell on the GRO export path (pipeline.py:928 →
  write_interface_gro_file → wrap_molecules_into_box with the triclinic
  hydrate.cell). CONFIRMED on a real sH+ch4 hydrate: the OLD diagonal-only
  wrap left atoms up to 0.357 fractional (0.428 nm — a third of the ~1.24 nm
  cell) outside the parallelepiped; 90/312 atoms outside.
fix:
  - Added `from quickice.structure_generation.cell_utils import is_cell_orthogonal`
    import (the established shared helper already used by water_filler.py).
  - wrap_positions_into_box: added a triclinic branch BEFORE the orthogonal
    fast path. For triclinic cells, wrap via fractional coords
    `frac = pos @ inv(cell.T); frac = np.mod(frac, 1.0); return frac @ cell.T`
    (per-atom). For orthogonal cells, the existing diagonal modulo is kept
    byte-identical (slab fast path unchanged). Added an empty-input guard.
  - wrap_molecules_into_box: added a triclinic branch that wraps each molecule
    by its fractional center-of-mass (reusing the PROVEN
    water_filler.wrap_positions_triclinic pattern, adapted for variable-size
    molecule_index): per molecule `mol_frac = mol @ inv(cell.T)`;
    `shift_frac = -np.floor(mol_frac.mean(axis=0))`; `mol_frac += shift_frac`;
    `wrapped = mol_frac @ cell.T`. This handles unwrap + wrap in one step and
    accounts for the off-diagonal shear. The orthogonal branch (unwrap +
    center-wrap with diagonal box_sizes) is kept byte-identical. Added an
    empty-input / empty-molecule_index guard.
  - Constraint honored: hydrate positions are NOT wrapped upstream (still
    intentionally unwrapped at hydrate_generator.py:186-189); wrapping happens
    ONLY at export. The orthogonal/slab path is numerically unchanged (slab.py:619
    forces orthogonal cells). numpy-only (no new deps).
verification:
  - New regression test tests/test_scancode_bugs_triclinic_pbc.py (14 tests):
    - Unit: synthetic triclinic cell — per-atom wrap puts every atom in frac
      [0,1]; PROVEN that OLD diagonal-only leaves the same atom outside (bug
      caught).
    - Unit: orthogonal fast path byte-identical to old code (regression guard,
      reproduced inline).
    - Unit: triclinic molecule-aware wrap — COM in [0,1), molecules intact,
      variable molecule sizes (water/ion/ch4).
    - Integration: real sH+ch4 hydrate export via write_interface_gro_file (the
      actual bug site) — every molecule COM in [0,1), molecules intact, max
      atom excursion 0.088 fractional (molecule straddling) << 0.15 tol, AND
      OLD diagonal-only would produce 0.357 fractional (4.1x worse) — proves
      the bug is real and the fix helps.
    - gmx grompp dry-run on exported 2x2x2 sH supercell (1x1x1 too small for
      1.0 nm cutoff) → exit_code 0 (gmx IS available; triclinic topology
      processes).
    Result: 14 passed, 0 failed.
  - Targeted regression subset `pytest -k "pbc or wrap or gro or hydrate or
    export or slab or interface"`: 788 passed, 0 failed (137s).
  - Directly-relevant tests/test_e2e_triclinic_hydrate_export.py (c0te/c1te
    4x4x4 CLI+GUI export + grompp): 4 passed, 0 failed.
  - Full suite (QT_QPA_PLATFORM=offscreen, with 2 pre-existing version-string
    failures deselected and 1 pre-existing headless GUI hang ignored):
    1524 passed, 2 skipped, 2 deselected, 0 FAILED (213s).
  - Pre-existing (confirmed on baseline, NOT caused by this fix):
    * 2 version-string failures (assert "4.5.0" vs actual "4.7.0") in
      test_cli_integration.py and test_entry_point.py.
    * 1 headless Qt hang: test_custom_molecule_panel_34_6.py::
      test_button_state_persistence (PySide6 panel widget test; hangs in
      full-suite context even with offscreen; AGENTS.md-documented VTK/
      headless limitation, ROADMAP TEST-06 deferred). Confirmed identical
      hang on baseline (my fix stashed).
files_changed:
  - quickice/output/gromacs_writer.py (triclinic-aware branches in
    wrap_positions_into_box and wrap_molecules_into_box; + is_cell_orthogonal
    import)
  - tests/test_scancode_bugs_triclinic_pbc.py (new regression test, 14 tests)
  - .planning/debug/triclinic-pbc-wrap.md (this debug file)
