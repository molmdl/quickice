---
phase: e2e-api-workflow
plan: 02
type: execute
wave: 2
depends_on: ["e2e-api-workflow-01"]
files_modified:
  - tests/test_e2e_interface_generation.py
autonomous: true

must_haves:
  truths:
    - "Ice candidate → Interface generation works for slab, pocket, piece modes"
    - "Hydrate candidate → Interface generation works for slab mode"
    - "Ice II raises InterfaceGenerationError with clear message"
    - "Interface has correct atom counts: ice + water + guests == total"
    - "Interface molecule_index tracks all molecule types correctly"
  artifacts:
    - path: "tests/test_e2e_interface_generation.py"
      provides: "~10 interface generation e2e tests"
      exports: ["test_ice_slab_interface", "test_ice_pocket_interface", "test_ice_ii_rejection"]
  key_links:
    - from: "tests/test_e2e_interface_generation.py"
      to: "quickice/structure_generation/interface_builder.py"
      via: "generate_interface(candidate, config)"
      pattern: "generate_interface"
    - from: "tests/test_e2e_interface_generation.py"
      to: "tests/conftest.py"
      via: "pytest fixtures (ice_ih_candidate, interface_slab, etc.)"
      pattern: "ice_ih_candidate|interface_slab"
---

<objective>
Create interface generation e2e tests covering all modes and edge cases

Purpose: Test the interface generation pipeline (Workflow 4) end-to-end: ice→interface and hydrate→interface, all three modes (slab, pocket, piece), rejection of unsupported phases (Ice II), and structural invariant verification (atom counts, molecule_index, water_nmolecules > 0).

Output: tests/test_e2e_interface_generation.py with ~10 tests
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/e2e-api-workflow/CONTEXT.md
@quickice/structure_generation/interface_builder.py
@quickice/structure_generation/types.py
@quickice/structure_generation/errors.py
@tests/conftest.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create interface generation e2e tests for all modes</name>
  <files>tests/test_e2e_interface_generation.py</files>
  <action>
Create `tests/test_e2e_interface_generation.py` covering Workflow 4 (Interface Generation). ~10 tests.

Use conftest fixtures `ice_ih_candidate`, `hydrate_sI_ch4_candidate`, `interface_slab`, `interface_pocket`, `interface_hydrate_slab` where applicable. Generate new interfaces inline for parameterized tests.

Tests to create:

1. `test_ice_ih_slab_interface_generation` — Use `interface_slab` fixture. Verify: `interface.ice_atom_count > 0`, `interface.water_atom_count > 0`, `interface.ice_nmolecules > 0`, `interface.water_nmolecules > 0`, `interface.mode == "slab"`, `np.all(np.isfinite(interface.positions))`.

2. `test_ice_ih_pocket_interface_generation` — Use `interface_pocket` fixture. Verify pocket-specific: `interface.mode == "pocket"`, has ice and water atoms.

3. `test_ice_ih_piece_interface_generation` — Generate piece-mode interface: `InterfaceConfig(mode='piece', box_x=3.0, box_y=3.0, box_z=4.0, seed=42)` with ice_ih_candidate. Verify piece mode generates.

4. `test_hydrate_sI_ch4_slab_interface` — Use `interface_hydrate_slab` fixture. Verify: `interface.guest_atom_count > 0`, `interface.guest_nmolecules > 0`, `interface.ice_atom_count > 0`, `interface.water_atom_count > 0`.

5. `test_interface_atom_count_sum` — For slab interface: `interface.ice_atom_count + interface.water_atom_count + interface.guest_atom_count == len(interface.positions)`. Same for `len(interface.atom_names)`.

6. `test_interface_molecule_index_tracks_all_molecules` — Verify `interface.molecule_index` has entries for ice, water, and (if hydrate) guest molecules. Total molecules: `len(interface.molecule_index) == interface.ice_nmolecules + interface.water_nmolecules + interface.guest_nmolecules`.

7. `test_interface_cell_has_positive_volume` — `np.linalg.det(interface.cell) > 0`.

8. `test_ice_ii_rejection_raises_error` — Try to generate interface from Ice II candidate. First generate Ice II: lookup appropriate phase, create candidate, then call `generate_interface(ice_ii_candidate, InterfaceConfig(mode='slab', ...))`. Expect `InterfaceGenerationError` with message containing "Ice II" or "rhombohedral". Use `pytest.raises(InterfaceGenerationError)`.

9. `test_interface_water_available_for_downstream` — Verify `interface.water_nmolecules > 0` (required for solute/ion/custom molecule insertion). This is a critical invariant — if no water, downstream steps fail.

10. `test_ice_ic_slab_interface_generation` — Generate Ice Ic interface. Verify same structural invariants as test 1. Shows that Ice Ic (cubic) works correctly for slab mode.

For Ice II test (test 8): Generate Ice II candidate using `lookup_phase` with appropriate T/P for Ice II stability (~100K, ~300MPa). If GenIce2 doesn't support Ice II, use `pytest.mark.xfail`. The key test is that `validate_interface_config` rejects it before generation.

IMPORTANT: `generate_interface` may take 2-5s per call. Use module-scoped fixtures from conftest.py where possible. Only generate inline for parameterized variants.
IMPORTANT: Box dimensions for slab mode: `box_z = 2*ice_thickness + water_thickness`. The conftest fixture uses box_z=8.0, ice_thickness=2.0, water_thickness=4.0 (8 = 2*2 + 4).
  </action>
  <verify>`pytest tests/test_e2e_interface_generation.py -v` passes with 10+ tests</verify>
  <done>10 interface generation tests pass, covering slab/pocket/piece modes, hydrate→interface, Ice II rejection, and structural invariants</done>
</task>

<task type="auto">
  <name>Task 2: Add edge case and error handling tests for interface generation</name>
  <files>tests/test_e2e_interface_generation.py</files>
  <action>
Add edge case tests to the SAME file `tests/test_e2e_interface_generation.py`. These test error conditions and boundary cases.

Additional tests to add (append to the file from Task 1):

1. `test_pocket_diameter_too_large_raises_error` — Pocket diameter >= box_z should raise `InterfaceGenerationError`. Use `InterfaceConfig(mode='pocket', box_x=3.0, box_y=3.0, box_z=3.0, seed=42, pocket_diameter=5.0)`.

2. `test_piece_mode_box_too_small_raises_error` — Piece mode with box smaller than ice candidate cell should raise error or produce minimal structure. Test with very small box (e.g., box_x=1.0, box_y=1.0, box_z=1.0 with default MINIMUM_BOX_DIMENSION check).

3. `test_zero_water_interface_unsupported` — Verify that an interface with zero water molecules is either rejected or handled. Generate an interface with very thin water layer (e.g., water_thickness=0.1, ice_thickness=2.0). If it produces no water, verify downstream operations would fail gracefully.

4. `test_interface_positions_within_cell_bounds` — For slab interface, verify all atom positions are within [0, box_x] × [0, box_y] × [0, box_z] (considering PBC). This catches wrapping bugs.

These tests verify the error handling described in CONTEXT.md edge cases #6-8.
  </action>
  <verify>`pytest tests/test_e2e_interface_generation.py -v` shows 13+ tests total, all pass</verify>
  <done>Interface test file has 13+ tests including error handling and edge cases</done>
</task>

</tasks>

<verification>
```bash
# All interface tests pass
pytest tests/test_e2e_interface_generation.py -v

# Verify test count
pytest tests/test_e2e_interface_generation.py --collect-only | grep "test session starts"
pytest tests/test_e2e_interface_generation.py -v | grep -c "PASSED"
```
</verification>

<success_criteria>
1. test_e2e_interface_generation.py has 10+ tests, all pass
2. All three modes (slab, pocket, piece) tested with Ice Ih
3. Hydrate → Interface tested with sI+CH4
4. Ice II rejection tested with InterfaceGenerationError
5. Error handling tests for invalid config parameters
6. Structural invariants verified (atom counts, molecule_index, cell volume)
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-api-workflow/e2e-api-workflow-02-SUMMARY.md`
</output>
