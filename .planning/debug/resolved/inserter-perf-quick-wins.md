---
status: resolved
trigger: "PERF-04 + PERF-06: batch cKDTree query + vectorized water removal (scancode Group 6)"
created: 2026-07-19T00:00:00Z
updated: 2026-07-19T00:03:00Z
---

## Current Focus

hypothesis: Both PERF-04 (per-atom cKDTree query loop) and PERF-06 (per-mol water-removal
append loop) are confirmed in the cited files. Pure perf refactors with byte-identical
output are achievable: cKDTree.batch_query(positions, k=1) returns the same per-atom
distances the loop computed one-by-one, and water_reshaped[~mol_overlaps] selects the
same molecule blocks in the same ascending order as the loop's `np.where(~mol_overlaps)`
indices. No algorithmic change; no rebuild discipline touched.
test: (1) read the cited lines and confirm the loop shapes; (2) verify cKDTree.query
batched call returns same dists as loop on hand-crafted fixtures; (3) verify
water_reshaped[keep_mask].reshape(-1,3) == np.vstack([positions[start:end] for
mol_idx in water_molecules_to_keep]); (4) add seeded-RNG regression test asserting
identical output to a known-good snapshot; (5) run full non-GUI pytest suite for
regressions.
expecting: Batch query and vectorized mask produce byte-identical positions/counts/
order to the old loops. Full suite passes with zero new failures.
next_action: Apply PERF-04 to solute_inserter.py:417-421 and custom_molecule_inserter.py:367-371,
then add PERF-04 tests, commit; then apply PERF-06 to solute_inserter.py:561-567 +
downstream vstack adjustment, add PERF-06 tests, commit; run full suite.

## Symptoms

PERF-04:
  expected: A single batched cKDTree query computes all distances at once, identical
           overlap decision to the per-atom loop.
  actual: A per-atom Python loop calls `existing_tree.query(atom_pos, k=1)` N times,
          with Python-loop overhead.
  errors: None — perf only.
  reproduction: Profile a solute insertion with a large solute (many atoms); the
                per-atom query loop dominates.
  timeline: Present since the inserter was written.

PERF-06:
  expected: A vectorized boolean-mask selection produces the kept water positions in
           one numpy operation.
  actual: A per-mol Python loop appends to a list, with Python-loop overhead.
  errors: None — perf only.
  reproduction: Profile a solute insertion with many water molecules to remove; the
                per-mol append loop dominates.
  timeline: Present since the inserter was written.

## Eliminated

(none yet)

## Evidence

- 2026-07-19 env check: `quickice` conda env active (marked *); numpy 2.4.3,
  scipy 1.17.1. `gmx` on PATH at /data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx
  (GROMACS 2023.5-plumed_2.9.3). Python at /share/home/nglokwan/miniconda3/envs/quickice/bin/python.

- 2026-07-19 PERF-04 confirmed in solute_inserter.py:417-421:
    ```python
    for atom_pos in solute_positions:
        min_dist = existing_tree.query(atom_pos, k=1)[0]
        if min_dist < min_separation:
            return True
    return False
    ```
  Function `_check_solute_overlap(self, solute_positions, existing_tree, min_separation)`
  at solute_inserter.py:399-421. Short-circuits on first overlap. Plan cited 412-416 —
  the actual loop body shifted to 417-421 (docstring ends at 416). Caller at line 893
  passes `solute_positions` (2D (N,3) array from rotated_positions + position).

- 2026-07-19 PERF-04 confirmed in custom_molecule_inserter.py:367-371:
    ```python
    for atom_pos in positions:
        min_dist = existing_tree.query(atom_pos, k=1)[0]
        if min_dist < min_separation:
            return True
    return False
    ```
  Function `_check_overlap(self, positions, existing_tree, min_separation)` at
  custom_molecule_inserter.py:349-371. Same short-circuit pattern. Caller at line 643
  passes `placed_mol` (2D (N,3) array from centered_template @ rotation_matrix.T +
  position).

- 2026-07-19 PERF-06 confirmed in solute_inserter.py:561-567:
    ```python
    kept_water_positions = []
    kept_water_atom_names = []
    for mol_idx in water_molecules_to_keep:
        atom_start = water_start + mol_idx * atoms_per_water
        atom_end = atom_start + atoms_per_water
        kept_water_positions.append(structure.positions[atom_start:atom_end])
        kept_water_atom_names.extend(structure.atom_names[atom_start:atom_end])
    ```
  `water_molecules_to_keep = np.where(~mol_overlaps)[0].tolist()` (line 492) — ascending
  molecule indices. `mol_overlaps` already a boolean mask (line 489).
  `water_reshaped` already computed at line 481 as
  `water_positions_all.reshape(n_water_molecules, atoms_per_water, 3)` where
  `water_positions_all = structure.positions[water_start:water_start + n_check_atoms]`
  and `n_check_atoms = n_water_molecules * atoms_per_water`.

  Downstream consumers that may need adjustment when `kept_water_positions` becomes an
  array:
  - line 598-601:
      ```python
      if kept_water_positions:  # list-truthiness; FAILS on numpy array
          water_positions_array = np.vstack(kept_water_positions)
      else:
          water_positions_array = np.zeros((0, 3))
      ```
  - line 613-617: `kept_water_atom_names` used in list concatenation (works if it stays
    a flat Python list — `.tolist()` ensures this).
  - line 640-646: `for mol_idx in water_molecules_to_keep:` rebuilds molecule_index
    from the kept list — UNCHANGED (still uses `water_molecules_to_keep`, not
    `kept_water_positions`).
  - line 685: `water_atom_count=len(kept_water_atom_names)` — works if names is a flat
    list.
  - line 687: `water_nmolecules=len(water_molecules_to_keep)` — UNCHANGED.

  Out-of-scope: custom_molecule_inserter.py:454-460 has the SAME water-removal loop
  pattern, but PERF-06 is explicitly scoped to solute_inserter.py only (per PLAN.md
  Group 6). Do NOT touch custom_molecule_inserter's water-removal loop.

- 2026-07-19 cKDTree batch-query behavior verified:
    - `tree.query(positions_2d, k=1)` returns `(dists, idxs)` with `dists.shape == (N,)`
      for input `(N, 3)`.
    - Empty input `np.zeros((0,3))` returns empty arrays `(array([]), array([]))` — no
      raise. So no empty-guard needed, but I'll add one for clarity/safety.
    - Single atom `(1, 3)` returns `(array([d]), array([i]))`.
    - Verified byte-equivalence on 3 fixtures (overlap short-circuit, no-overlap,
      partial overlap): `bool(np.any(dists < threshold)) == loop_result` in all cases.

- 2026-07-19 Vectorized water-removal equivalence verified by construction:
  - `water_reshaped[i] == structure.positions[water_start + i*atoms_per_water :
    water_start + (i+1)*atoms_per_water]` (numpy reshape semantics).
  - The loop's `structure.positions[atom_start:atom_end]` with `atom_start = water_start
    + mol_idx * atoms_per_water` is the same slice.
  - `np.where(~mol_overlaps)[0]` returns indices in ascending order, so the loop iterates
    kept molecules in ascending index order. `water_reshaped[~mol_overlaps]` (boolean
    mask selection) also yields rows in ascending index order. Same order.
  - `np.vstack([slice_per_mol for ...])` == `water_reshaped[keep_mask].reshape(-1, 3)`.
  - `kept_water_atom_names` flat list (via `.extend` per molecule) ==
    `water_atom_names_reshaped[keep_mask].reshape(-1).tolist()`.

## Resolution

root_cause: (perf, not correctness) Per-atom Python loop in cKDTree query (PERF-04) and
per-mol Python append loop in water-removal assembly (PERF-06) — both replaceable with
single numpy/scipy vectorized operations producing byte-identical output.
fix:
  - PERF-04 applied (COMMITTED as c91d521a): solute_inserter.py:417-421 and
    custom_molecule_inserter.py:367-371 replaced per-atom
    `for atom_pos in positions: tree.query(atom_pos, k=1)[0]` loop with batch
    `dists, _ = existing_tree.query(positions, k=1); return bool(np.any(dists
    < min_separation))`. Byte-identical decision (any overlap -> True).
  - PERF-06 applied (pending commit): solute_inserter.py:562-569 replaced per-mol
    `for mol_idx in water_molecules_to_keep: kept_water_positions.append(...)`
    loop with vectorized `keep_mask = ~mol_overlaps; kept_water_positions =
    water_reshaped[keep_mask]` and `kept_water_atom_names =
    water_atom_names_all[keep_mask].reshape(-1).tolist()`. Downstream vstack
    at line 600-603 adjusted to `if kept_water_positions.size > 0:
    water_positions_array = kept_water_positions.reshape(-1, 3)` (numpy array
    does not support bool() truthiness). `water_molecules_to_keep` and
    `mol_overlaps` were already computed above; only the append loop + downstream
    vstack check changed. Byte-identical kept positions / atom_names / order.
verification:
  - PERF-04: 17 new tests in tests/test_scancode_bugs_inserter_perf.py all PASS
    (direct batch-vs-loop byte-equivalence on 6 seeds x 20 fixtures x 2 inserters,
    edge cases, end-to-end seeded reproducibility on 3 seeds).
  - PERF-06: 15 new tests all PASS (direct vectorized-vs-loop byte-equivalence on
    6 seeds, edge cases incl. no-overlap/all-overlap/single-mol/odd-pattern, and
    method-level byte-equivalence on 5 seeds asserting
    `_remove_overlapping_water` output matches the manual per-mol loop oracle on
    positions / atom_names / water_atom_count / water_nmolecules, plus 3
    end-to-end seeded-RNG reproducibility checks asserting water is removed).
  - Regression (broad inserter subset): 98 passed / 2 skipped across
    test_scancode_bugs_inserters, test_scancode_bugs_solute, test_solute_insertion,
    test_solute_ion_molecule_index, test_nmolecules_fields, test_custom_molecule,
    test_e2e_workflow_chains, test_e2e_solute_export, test_e2e_ion_insertion,
    test_e2e_custom_molecule. Zero new failures.
  - Full non-GUI suite (QT_QPA_PLATFORM=offscreen, 11 GUI files excluded, 180s
    per-test timeout): 2 failed, 1507 passed, 2 skipped in 196s. The 2 failures
    are pre-existing test_version_shows_version (assert "4.5.0" vs actual
    "4.7.0"; version bumped in commit da076717 before this work). Verified
    pre-existing by stash: 2 version tests fail at c91d521a with PERF-06 stashed.
    ZERO new failures from PERF-04 + PERF-06.
files_changed:
  - quickice/structure_generation/solute_inserter.py (PERF-04 committed c91d521a; PERF-06 committed 7ec57f24)
  - quickice/structure_generation/custom_molecule_inserter.py (PERF-04 committed c91d521a)
  - tests/test_scancode_bugs_inserter_perf.py (PERF-04 committed c91d521a; PERF-06 committed 7ec57f24)

## Commits

- c91d521a: perf(scancode): batch cKDTree query in solute/custom inserters (PERF-04)
- 7ec57f24: perf(scancode): vectorize water removal in solute inserter (PERF-06)

## Outcome

Both PERF-04 and PERF-06 applied as two atomic commits. Output is byte-identical to
the old loops (proven by direct loop-vs-batch / loop-vs-vectorized byte-equivalence
tests across many seeded fixtures + method-level oracle comparison + end-to-end
seeded-RNG reproducibility). Full non-GUI suite: 2 pre-existing failures (stale
version-string tests), 1507 passed, 2 skipped, ZERO new failures.
