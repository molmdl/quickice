# Codebase Concerns

**Analysis Date:** 2026-04-13

## Tech Debt

**Global numpy random state pollution in GenIce wrapper:**
- Issue: `quickice/structure_generation/generator.py` saves and restores `np.random` global state around each GenIce call, but GenIce internally mutates the global state. If an exception occurs between `np.random.seed(seed)` (line 97) and `np.random.set_state(original_state)` (line 122), the global state is NOT restored because the restore happens outside the try/except block's normal flow path — the `except` at line 143 wraps the error and re-raises, but never restores the random state.
- Files: `quickice/structure_generation/generator.py` lines 93–147
- Impact: After a generation failure, subsequent code using `np.random` gets an unpredictable global state, which can silently corrupt downstream results or make debugging extremely difficult.
- Fix approach: Move `np.random.set_state(original_state)` into a `finally` block to guarantee restoration regardless of success/failure.

**Phase diagram polygon overlap (Ice Ic vs Ice XI/Ih):**
- Issue: Phase diagram polygon rendering in `quickice/output/phase_diagram.py` uses rendering order to visually resolve overlaps (Ice Ic rendered last so it appears on top of Ice XI and Ice Ih). The underlying polygons still geometrically overlap — Shapely containment checks in `PhaseDetector` (in `quickice/gui/phase_diagram_widget.py`) can return wrong results near overlapping boundaries. The polygon approach for phase detection conflicts with the curve-based `lookup_phase()` function, creating two inconsistent phase detection mechanisms.
- Files: `quickice/output/phase_diagram.py` lines 876–891, `quickice/gui/phase_diagram_widget.py` lines 34–90
- Impact: Clicking the phase diagram in the GUI may show "Ice Ic" when the actual stable phase (per `lookup_phase()`) is "Ice Ih" or "Ice XI". Users get inconsistent phase identification between the diagram and the generated structure.
- Fix approach: Replace `PhaseDetector`'s polygon-based detection with a call to `lookup_phase()`, using the same single source of truth for phase identification. Keep polygons only for rendering, not for detection.

**Hardcoded phase boundary constants scattered across multiple files:**
- Issue: Phase boundary constants (triple point coordinates, boundary offsets like `P_vi - 5.0` in Ice II polygon, `P_vi + 5.0` in Ice VI polygon) are defined inline in multiple places rather than centralized. The `99.9` temperature boundary and `945.0` pressure boundary in `_build_ice_ii_polygon()` are magic numbers with no named constants.
- Files: `quickice/output/phase_diagram.py` lines 443, 461–467, 580–588; `quickice/phase_mapping/lookup.py` lines 239–254
- Impact: Any change to boundary values must be replicated across multiple files, and subtle inconsistencies between the diagram polygons and the `lookup_phase()` boundary logic can develop silently.
- Fix approach: Define all boundary constants in `quickice/phase_mapping/triple_points.py` or a new `quickice/phase_mapping/constants.py` module, and import them everywhere they are used. Eliminate magic offsets like `5.0 MPa` that have no physical justification.

**Hardcoded molecule count in CLI interface mode:**
- Issue: `quickice/main.py` line 104 hardcodes `nmolecules=256` for interface generation with no way for the user to override it via CLI arguments. The GUI uses the value from the input panel, creating an inconsistency between CLI and GUI.
- Files: `quickice/main.py` line 104
- Impact: CLI users cannot control molecule count for interface generation, potentially generating structures that are too small or unnecessarily large.
- Fix approach: Add `--interface-nmolecules` CLI argument or reuse `args.nmolecules` for interface generation.

**Two separate VTK availability checks with duplicate logic:**
- Issue: VTK availability detection logic is duplicated across `quickice/gui/view.py` lines 20–34, `quickice/gui/interface_panel.py` lines 28–42, and possibly `quickice/gui/phase_diagram_widget.py`. Each module independently checks `DISPLAY` environment variable and `QUICKICE_FORCE_VTK` with slightly different patterns. The `interface_panel.py` version catches `Exception` broadly (line 41), swallowing import errors silently.
- Files: `quickice/gui/view.py` lines 20–34, `quickice/gui/interface_panel.py` lines 28–42
- Impact: A VTK import error in one detection path might be handled differently than in another, leading to inconsistent VTK availability across tabs. The broad `except Exception` can hide real import problems (e.g., missing shared libraries).
- Fix approach: Extract VTK availability detection into a single `quickice/gui/vtk_check.py` utility module that all GUI components import. Use specific exception types instead of bare `except Exception`.

**Duplicated `_parse_gro()` logic:**
- Issue: GRO format parsing is implemented identically in two places: `quickice/structure_generation/generator.py` lines 149–208 (as a method) and `quickice/structure_generation/water_filler.py` lines 268–294 (inline in `load_water_template()`). Both parse the same fixed-width column format with the same indices.
- Files: `quickice/structure_generation/generator.py` lines 149–208, `quickice/structure_generation/water_filler.py` lines 268–294
- Impact: Any fix to GRO parsing (e.g., handling malformed files, supporting different formats) must be applied in two places, risking divergence.
- Fix approach: Extract `_parse_gro()` into a shared utility function in `quickice/structure_generation/` or `quickice/io_utils.py`.

**Duplicated `is_cell_orthogonal()` function:**
- Issue: Two separate implementations of `is_cell_orthogonal()` exist: `quickice/structure_generation/water_filler.py` lines 51–78 (uses angle tolerance 0.1°) and `quickice/structure_generation/interface_builder.py` lines 25–40 (uses off-diagonal element tolerance 1e-10). These are fundamentally different approaches that can give different results for the same cell matrix.
- Files: `quickice/structure_generation/water_filler.py` lines 51–78, `quickice/structure_generation/interface_builder.py` lines 25–40
- Impact: A cell that is "orthogonal" by angle tolerance might not be "orthogonal" by element tolerance, causing different tiling behavior in `water_filler.py` vs different validation behavior in `interface_builder.py`. This can produce inconsistent results for nearly-orthogonal triclinic cells.
- Fix approach: Consolidate into a single function in a shared utility, decide on one tolerance strategy, and import everywhere.

## Known Bugs

**Candidate metadata missing `temperature` and `pressure` keys:**
- Symptoms: In `quickice/structure_generation/modes/slab.py` lines 149–151 and `quickice/structure_generation/modes/pocket.py` lines 153–155, water density is calculated using `candidate.metadata.get('temperature', 273.15)` and `candidate.metadata.get('pressure', 0.101325)`. However, the `Candidate` metadata dict (set in `quickice/structure_generation/generator.py` lines 136–138) only includes `density` and `phase_name` — it never stores `temperature` or `pressure`. The `.get()` calls always fall back to defaults (273.15 K, 0.101325 MPa), regardless of the user's actual T,P input.
- Files: `quickice/structure_generation/generator.py` lines 136–138, `quickice/structure_generation/modes/slab.py` lines 149–151, `quickice/structure_generation/modes/pocket.py` lines 153–155
- Trigger: Generate an interface structure at any T,P conditions other than 273.15 K / 0.1 MPa. The water density will be wrong (calculated at default instead of actual conditions).
- Workaround: None currently. The fallback values produce physically reasonable but inaccurate water densities.

**Top file atom charges set to 0.0 for oxygen:**
- Symptoms: `quickice/output/gromacs_writer.py` line 152 writes `OW_ice` with charge `0.0`, but TIP4P-ICE oxygen should have partial charge `0.0` only in the topology file if charges are handled via `[ atoms ]` section properly. However, line 153–154 sets HW charges to `0.5897` and MW to `-1.1794`, which is correct for TIP4P-ICE. The oxygen charge of `0.0` appears intentional (the oxygen charge is effectively zero for TIP4P because all charge is on H and MW), but this is NOT standard TIP4P-ICE topology — standard TIP4P-ICE has oxygen charge around `-1.1794` distributed via the virtual site. The topology will likely cause GROMACS to fail energy minimization because the net charge per molecule is 0.5897 + 0.5897 - 1.1794 = 0.0 (neutral), but the oxygen has no LJ interaction since charge is 0. This is actually the correct pattern for TIP4P with virtual sites where charges are on H and MW only.
- Files: `quickice/output/gromacs_writer.py` lines 140–165
- Trigger: Run GROMACS energy minimization with exported .top file. May or may not fail depending on force field setup.
- Workaround: Users may need to manually adjust the topology file for their specific GROMACS setup.

## Security Considerations

**Path traversal protection is overly restrictive:**
- Risk: `quickice/output/orchestrator.py` lines 48–55 restricts output paths to within the current working directory (`Path.cwd().resolve()`). This prevents users from writing output to absolute paths outside CWD (e.g., `/tmp/quickice_output/`), which is a valid use case for CLI workflows. The security check also uses string prefix matching (`str(output_path).startswith(str(allowed_base))`), which can be bypassed with symlinks or paths like `/home/user/quickice-evil/` matching `/home/user/quickice`.
- Files: `quickice/output/orchestrator.py` lines 48–55
- Current mitigation: Prevents writing outside CWD, preventing some path traversal attacks
- Recommendations: Use `Path.is_relative_to()` (Python 3.9+) for proper path containment checking. Consider making the restriction optional (e.g., a CLI flag `--allow-absolute-output`) rather than enforcing it unconditionally.

**CLI file overwrite prompt uses `input()` — hangs in piped/non-interactive contexts:**
- Risk: `quickice/main.py` lines 36–37 calls `input()` to prompt for file overwrite. In non-interactive contexts (piped stdin, CI/CD, batch scripts), this hangs indefinitely waiting for input that will never come.
- Files: `quickice/main.py` lines 36–37
- Current mitigation: None
- Recommendations: Check `sys.stdin.isatty()` before prompting. In non-interactive mode, either skip the prompt and overwrite, or fail with a clear error message. Add a `--force` flag for batch usage.

## Performance Bottlenecks

**Molecule-by-molecule filtering in `tile_structure()` is O(n×m):**
- Problem: `quickice/structure_generation/water_filler.py` lines 538–560 iterates over every molecule (`for mol_idx in range(n_tiled_molecules)`) to check if all its atoms are inside the target region. For large systems (100k+ molecules), this Python-level loop dominates the tiling runtime.
- Files: `quickice/structure_generation/water_filler.py` lines 538–560
- Cause: Python loop over molecules instead of vectorized numpy operations
- Improvement path: Vectorize the containment check using numpy broadcasting: reshape positions to (n_molecules, atoms_per_molecule, 3), then use `np.all()` along axis=1 to check all atoms of each molecule simultaneously.

**Per-molecule wrapping loop in `tile_structure()` is also O(n):**
- Problem: The orthogonal wrapping loop in `quickice/structure_generation/water_filler.py` lines 583–623 iterates over every molecule for PBC wrapping. Same performance concern as the filtering loop.
- Files: `quickice/structure_generation/water_filler.py` lines 583–623
- Cause: Python loop for per-molecule PBC wrapping instead of vectorized approach
- Improvement path: Use vectorized modulo operations with per-molecule center-of-mass shifts computed via numpy broadcasting.

**cKDTree supercell approach for PBC in scoring:**
- Problem: `quickice/ranking/scorer.py` lines 54–61 builds a 27× (3×3×3) supercell by replicating all oxygen positions, then builds a cKDTree over the supercell. For large systems (100k+ molecules), this uses 27× memory and 27× tree construction time.
- Files: `quickice/ranking/scorer.py` lines 54–61, `quickice/output/validator.py` lines 119–129
- Cause: Using brute-force supercell replication for PBC instead of cKDTree's native `boxsize` parameter
- Improvement path: Use `cKDTree(positions, boxsize=cell_dims)` which handles PBC internally without supercell replication. This is already done correctly in `quickice/structure_generation/overlap_resolver.py` lines 61–63 — apply the same pattern to scorer and validator.

**Spline interpolation in phase diagram generation:**
- Problem: `quickice/output/phase_diagram.py` lines 182–251 performs per-point sampling of melting curves with spline interpolation, including a `scipy.interpolate.UnivariateSpline` import inside the function. The sampling uses `n_sample = max(n_points * 5, 500)` points per curve, and this runs for 5 melting curves plus boundary curves.
- Files: `quickice/output/phase_diagram.py` lines 182–251
- Cause: Per-point curve evaluation and heavy spline interpolation
- Improvement path: Cache sampled curves (the boundaries never change between calls with different user T,P). The existing `_SHARED_BOUNDARY_CACHE` (line 37) partially addresses this but only for boundary curves, not melting curves.

## Fragile Areas

**Phase lookup boundary conditions:**
- Files: `quickice/phase_mapping/lookup.py`
- Why fragile: The hierarchical if/elif chain (lines 171–400) uses exact floating-point comparisons against boundary values (e.g., `T >= 278`, `P > 2100`). Changes to boundary values require careful consideration of every branch that references them. Adding new phases (e.g., Ice XVII, Ice XIX) requires inserting branches at exactly the right position in the hierarchy. The `P > 30000` quick-filter for Ice X (line 177) could miss valid Ice X conditions if the boundary constant changes.
- Safe modification: When adding or modifying phase boundaries, test every boundary condition with values just above and below the threshold. Consider refactoring to a data-driven boundary table instead of hardcoded if/elif chains.
- Test coverage: `quickice/tests/test_phase_mapping.py` tests many conditions but may miss edge cases at exact boundary values

**GenIce API dependency:**
- Files: `quickice/structure_generation/generator.py` lines 99–119
- Why fragile: The generator directly calls GenIce's internal `safe_import`, `GenIce`, and `Format` APIs. GenIce is a research tool with no stability guarantees. The `depol="strict"` parameter, `tip3p` molecule model, and `gromacs` formatter are implementation details that could change between GenIce versions. If GenIce's API changes, all structure generation breaks.
- Safe modification: Pin GenIce version in `environment.yml`. Consider wrapping GenIce calls behind a thin adapter layer that isolates API changes.

**Triclinic cell handling across modules:**
- Files: `quickice/structure_generation/water_filler.py`, `quickice/structure_generation/interface_builder.py`, `quickice/structure_generation/modes/slab.py`, `quickice/structure_generation/modes/pocket.py`
- Why fragile: Triclinic cell support (Ice V, Ice II) requires careful coordinate transformations across tiling, wrapping, and cell matrix construction. The slab mode forces an orthogonal output cell (line 222: `cell = np.diag(...)`) even when ice atoms were positioned using triclinic lattice vectors. Ice II is explicitly blocked for interfaces (`quickice/structure_generation/interface_builder.py` lines 119–133), but Ice V is allowed despite being monoclinic. Adding triclinic output support would require coordinating changes across all mode modules.
- Safe modification: Any triclinic-related change should be tested with both Ice V (monoclinic, allowed) and Ice II (rhombohedral, blocked) to ensure consistent behavior.
- Test coverage: `quickice/tests/test_triclinic_interface.py` covers some triclinic cases

**Dual atom naming convention (TIP3P vs TIP4P):**
- Files: `quickice/structure_generation/generator.py` line 111 (TIP3P generation), `quickice/output/gromacs_writer.py` lines 40–106 (TIP4P-ICE export), `quickice/gui/vtk_utils.py` lines 46–52 (both)
- Why fragile: Structures are generated with TIP3P atom names (O, H, H = 3 atoms/molecule) but exported as TIP4P-ICE (OW, HW1, HW2, MW = 4 atoms/molecule) with the MW virtual site computed at export time. Interface structures store mixed TIP3P ice + TIP4P water (3+4 atoms/molecule) in a single positions array with `ice_atom_count` marking the boundary. Any code that processes positions must know which atoms belong to which model. The `InterfaceStructure` stores atoms per molecule differently for ice (3) vs water (4), and downstream code (VTK, GRO writer, PDB writer) must correctly handle both.
- Safe modification: When modifying any code that iterates over atom positions, always check `atoms_per_molecule` and the ice/water boundary. Never assume a fixed atoms-per-molecule count.

## Scaling Limits

**Molecule count for interface generation:**
- Current capacity: Typical interface generation handles 1,000–10,000 molecules well. The molecule-by-molecule Python loops in `water_filler.py` become slow above 10,000 molecules.
- Limit: Above ~50,000 molecules, `tile_structure()` takes multiple seconds due to O(n) Python loops. The cKDTree-based overlap detection scales better (O(n log n)) but still uses significant memory for the 27× supercell approach.
- Scaling path: Vectorize the filtering and wrapping loops in `tile_structure()`. Use cKDTree's `boxsize` parameter instead of supercell replication.

**Phase diagram rendering time:**
- Current capacity: Phase diagram generation takes ~2–5 seconds due to curve sampling, spline interpolation, and Shapely polygon operations.
- Limit: Each call regenerates all 12+ phase polygons from scratch. No caching between calls.
- Scaling path: Cache computed polygons and melting curve samples across calls (the boundaries don't change, only the user's T,P marker moves).

## Dependencies at Risk

**GenIce2 (genice2==2.2.13.1):**
- Risk: GenIce is a niche research tool with a small user base. Breaking API changes between versions are possible. GenIce uses deprecated `np.random` global state instead of the modern `numpy.random.Generator` API. GenIce is the ONLY way QuickIce generates ice structures — there is no fallback generator.
- Impact: Complete structure generation failure if GenIce breaks or is unavailable
- Migration plan: If GenIce becomes unavailable or incompatible, would need to implement a custom ice structure generator or find an alternative tool. Consider caching a library of pre-generated structures as a fallback.

**iapws (iapws==1.5.5):**
- Risk: The IAPWS library provides thermodynamic calculations (melting curves, density). It is used for phase boundary calculations and water density computation. If the library changes its API or calculation methods, all phase identification and density calculations break.
- Impact: Incorrect phase identification and water density calculations
- Migration plan: Could implement the IAPWS R14-08 and R10-06 equations directly (they are well-documented), but this would be significant effort.

**Shapely (shapely==2.1.2):**
- Risk: Used for polygon containment checks in `PhaseDetector` and for centroid calculations in phase diagram rendering. If Shapely's API changes or the library is unavailable, the phase diagram and interactive phase detection break. The phase diagram widget imports Shapely at module level (`quickice/gui/phase_diagram_widget.py` line 19), meaning any Shapely import failure crashes the entire GUI.
- Impact: Phase diagram and phase detection unavailable
- Migration plan: Replace Shapely-based `PhaseDetector` with `lookup_phase()` calls (already available). For centroid calculations, use a simple average of polygon vertices instead.

## Missing Critical Features

**No GUI cancellation for interface generation:**
- Problem: The GUI has no cancel button for Tab 2 (Interface Construction). The `InterfacePanel` does not include a cancel button, and `MainViewModel.cancel_interface_generation()` is implemented but never connected to a UI element. Users must wait for interface generation to complete or restart the application.
- Files: `quickice/gui/interface_panel.py`, `quickice/gui/main_window.py`

**No CLI test suite for interface modes:**
- Problem: The test suite covers phase mapping, structure generation, ranking, and output, but there are no CLI integration tests for `--interface` mode. The `test_cli_integration.py` file only tests the standard (non-interface) CLI workflow.
- Files: `quickice/tests/test_cli_integration.py`

## Test Coverage Gaps

**Interface generation modes:**
- What's not tested: Slab, pocket, and piece mode end-to-end integration tests with actual GenIce-generated candidates. `test_structure_generation.py` tests candidate generation but not interface assembly. `test_med03_minimum_box_size.py` tests validation only.
- Files: `quickice/tests/test_structure_generation.py`, `quickice/tests/test_med03_minimum_box_size.py`
- Risk: Breaking changes in slab/pocket/piece mode logic (e.g., overlap resolution, density scaling, atom name filtering) may go undetected
- Priority: High

**GUI worker thread error paths:**
- What's not tested: Error conditions in `GenerationWorker.run()` and `InterfaceGenerationWorker.run()` — e.g., what happens when GenIce raises an exception, when phase lookup returns an unknown phase, or when cancellation is requested mid-generation.
- Files: `quickice/gui/workers.py`
- Risk: Thread-related bugs (hung threads, missing signal emissions, UI state inconsistencies after errors) may go undetected
- Priority: Medium

**GROMACS export for triclinic cells:**
- What's not tested: The triclinic cell vector output format in `write_gro_file()` and `write_interface_gro_file()` — only tested with orthogonal cells. The 9-value triclinic box format (lines 112–114, 315–317) is not verified against GROMACS.
- Files: `quickice/output/gromacs_writer.py` lines 112–114, 315–317
- Risk: Exported .gro files for triclinic structures (Ice V) may be unreadable by GROMACS
- Priority: Medium

**Phase diagram output validation:**
- What's not tested: Whether generated phase diagram PNG/SVG files are valid and render correctly. No pixel-level or structural validation of diagram output.
- Files: `quickice/output/phase_diagram.py`
- Risk: Diagram rendering regressions (wrong colors, overlapping labels, clipped regions) go undetected
- Priority: Low

**Density calculation for Ice Ic, Ice XI, Ice IX, Ice X, Ice XV:**
- What's not tested: `PHASE_METADATA` in `quickice/phase_mapping/lookup.py` uses fixed density values for these phases (Ice Ic: 0.92, Ice XI: 0.92, Ice IX: 1.16, Ice X: 2.79, Ice XV: 1.31). There are no tests verifying these values are physically correct or consistent with literature.
- Files: `quickice/phase_mapping/lookup.py` lines 27–46
- Risk: Incorrect density values produce structures with wrong molecular spacing
- Priority: Medium

---

*Concerns audit: 2026-04-13*
