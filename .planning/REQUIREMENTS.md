# Requirements: QuickIce v4.7

**Defined:** 2026-06-27
**Core Value:** Generate ready-to-use initial models and topologies for GROMACS for the simulation of ice, hydrates, solutes, and custom molecules in water

## v4.7 Requirements

Requirements for v4.7 Extended Hydrate Generation milestone. Each maps to roadmap phases.

### Custom Guest in Hydrate

- [ ] **GUEST-01**: User can upload a custom guest molecule (.gro + .itp) and generate a hydrate structure with that molecule placed in cage positions
- [ ] **GUEST-02**: User can select which cage type (small/large/medium) to place the custom guest in
- [ ] **GUEST-03**: User can set cage occupancy percentage for custom guest (0-100%)
- [x] **GUEST-04**: QuickIce validates custom guest GRO file is parseable (atom names + positions) — *Phase 40-04*
- [x] **GUEST-05**: QuickIce validates custom guest ITP file is parseable (moleculetype name, atom types, charges) — *Phase 40-04*
- [x] **GUEST-06**: QuickIce rejects custom guest residue names >3 chars (GRO 5-char limit with _H suffix) — *Phase 38-03 + 40-03*
- [x] **GUEST-07**: QuickIce rejects ITP files with comb-rule=1 (must be comb-rule=2, Lorentz-Berthelot) — *Phase 40-01 + 40-04*
- [x] **GUEST-08**: QuickIce registers custom guest in sys.modules and GenIce2 finds it via safe_import — *Phase 40-04 + 40-05*
- [x] **GUEST-09**: QuickIce cleans up sys.modules injection after generation (prevents pollution) — *Phase 40-04 (custom_guest_module context manager, try/finally)*
- [x] **GUEST-10**: Custom guest registration is thread-safe (main-thread registration before HydrateWorker starts) — *Phase 40-05*

**Note:** GUEST-01/02/03 remain pending — the data path + generator bridge + export all work (Phase 40/41), and the GUI upload panel is now done (Phase 44-02). The CLI user-facing surface (`--custom-guest`/`--custom-guest-itp`) remains pending (Phase 45-01b). GUEST-04..10 (the engine/validation/thread-safety layer) are complete.

### GROMACS Export for Custom Guests

- [x] **EXPORT-01**: Custom guest appears in GROMACS .top with correct _H suffix moleculetype name
- [x] **EXPORT-02**: Custom guest atomtypes are commented out in bundled .itp (moved to main .top [atomtypes] section)
- [x] **EXPORT-03**: Custom guest ITP atomtypes are merged into main .top with deduplication (no duplicate atomtype entries)
- [x] **EXPORT-04**: GRO export writes correct residue name for custom guest (≤5 chars with _H suffix)
- [x] **EXPORT-05**: GROMACS export uses mol_type identity from pipeline (not re-detection from atom names) — P3 fix
- [x] **EXPORT-06**: GROMACS grompp validates successfully on exported custom guest hydrate structures

### Extended Lattice Types

- [x] **LATTICE-01**: User can select filled ice C0 (c0te) as hydrate lattice type
- [x] **LATTICE-02**: User can select filled ice C1 (c1te) as hydrate lattice type
- [x] **LATTICE-03**: User can select filled ice C2 (c2te) as hydrate lattice type
- [x] **LATTICE-04**: User can select filled ice Ih (ice1hte) as hydrate lattice type
- [x] **LATTICE-05**: User can select sT' (sTprime) as hydrate lattice type (water-only, no guest support)
- [x] **LATTICE-06**: User can select Ice XVI (empty sII framework) as hydrate lattice type
- [x] **LATTICE-07**: User can select Ice XVII (empty C0 framework) as hydrate lattice type
- [x] **LATTICE-08**: Triclinic filled ices (C0, C1) are blocked for interface generation with clear error message (like Ice II)
- [x] **LATTICE-09**: Filled ice lattices place guests via parse_guest code path (spot_guests crashes with IndexError — corrected from original requirement)

### Mixed Cage Occupancy

- [x] **MIXED-01**: User can assign different guest types to different cage types on ALL hydrate lattices (sI small/large, sII small/large, sH small/medium/large, filled ice channels)
- [x] **MIXED-02**: User can assign any available guest type (CH₄, THF, or custom) to any cage type (e.g., CH₄ in small cages + custom guest in large cages)
- [x] **MIXED-03**: User can set per-cage-type occupancy percentage (e.g., 60% CH₄ in small + 100% custom in large)
- [x] **MIXED-04**: Mixed occupancy hydrate exports correctly to GROMACS with multiple guest .itp files in .top
- [x] **MIXED-05**: Mixed occupancy hydrate renders correctly in VTK with per-type styles

### Depol Mode

- [x] **DEPOL-01**: User can select depol mode (strict/optimal) in Hydrate tab
- [x] **DEPOL-02**: Depol mode is passed through to GenIce2 generate_ice() call
- [x] **DEPOL-03**: Default depol mode is 'strict' (preserves current behavior)

### Internal Pipeline (prerequisite engineering)

- [x] **PIPE-01**: _build_molecule_index uses metadata-driven molecule identification (not pattern matching on atom names)
- [x] **PIPE-02**: HydrateConfig carries guest metadata (name, atom labels, atom count) through generation→export pipeline
- [x] **PIPE-03**: GRO residue name overflow is validated at write time (names >5 chars rejected, not silently corrupting format)
- [x] **PIPE-04**: ITP transformation pipeline handles _H suffix, atomtypes comment-out, residue name rewrite for custom guests

### GUI Integration

- [x] **GUI-01**: Hydrate tab lattice dropdown includes all new lattice types (filled ices + Ice XVI/XVII + sT') — *Phase 39-04*
- [x] **GUI-02**: Hydrate tab has custom guest upload panel (.gro + .itp file pair selection) — *Phase 44-02*
- [x] **GUI-03**: Hydrate tab has cage-type guest assignment controls (small/large/medium → guest type) — *Phase 42-06 (built-in) + 44-02 (custom-per-cage)*
- [x] **GUI-04**: Hydrate tab has depol mode dropdown (strict/optimal) — *Phase 43-02*
- [x] **GUI-05**: Custom guest upload shows validation errors with specific messages (name too long, wrong comb-rule, unparseable) — *Phase 44-02*
- [x] **GUI-06**: Hydrate tab mixed occupancy shows per-cage-type guest type and occupancy controls — *Phase 42-06 (built-in) + 44-02 (custom-per-cage via "Custom: {residue}" combo option)*

### CLI Integration

- [x] **CLI-01**: CLI --hydrate-lattice flag supports new lattice type names (c0te, c1te, c2te, ice1hte, sTprime, 16, 17) — *Phase 39-03*
- [ ] **CLI-02**: CLI --custom-guest and --custom-guest-itp flags for custom guest .gro/.itp file pair — *Phase 45-01b (DEFERRED BY DESIGN — pipeline.py:73-81; GUI-only for v4.7; CLI custom-cage-guest e2e tested via Python API in 45-10/45-11)*
- [x] **CLI-03**: CLI --depol flag (strict/optimal, default strict) — *Phase 45-12*
- [x] **CLI-04**: CLI mixed occupancy via --guest-small and --guest-large with occupancy values — *Phase 42-07 (implemented as repeatable `--cage-guest KEY=GUEST:OCC`, superset of the original spec — supports medium cage + any cage_type_map key)*

### VTK Rendering

- [x] **VTK-01**: Custom guest molecules render with distinct style in hydrate 3D viewer — *Phase 42-04 (create_guest_actor returns list[vtkActor] per mol_type with per-type bond color palette)*
- [x] **VTK-02**: Element map is extended for common custom guest atom types (C, O, H, N, S, etc.) — *hydrate_renderer.py:68 ELEMENT_TO_ATOMIC_NUMBER covers H..Ca*

### Testing & Validation

- [x] **TEST-01**: Unit tests for custom guest GRO/ITP validation (valid, name too long, wrong comb-rule, unparseable) — *Phase 40-04 (test_custom_guest_bridge.py)*
- [x] **TEST-02**: Unit tests for sys.modules injection and cleanup — *Phase 40-04 (test_custom_guest_bridge.py)*
- [x] **TEST-03**: Unit tests for _build_molecule_index with custom guest types — *Phase 40-05 + test_hydrate_config_custom.py + test_hydrate_config_metadata.py*
- [x] **TEST-04**: E2E tests for filled ice generation (C0, C1, C2, Ih, sT') — *Phase 39-05 (test_hydrate_lattice_types.py, 157 parametrized tests)*
- [x] **TEST-05**: E2E tests for custom guest hydrate generation + GROMACS export — *Phase 41 (test_e2e_custom_guest_hydrate.py + _gui_grompp.py + _cli_grompp.py)*
- [x] **TEST-06**: E2E tests for mixed cage occupancy hydrate generation — *Phase 42 (test_e2e_mixed_cage_occupancy.py + test_e2e_sh_cage_occupancy.py + test_cli/test_mixed_cage_cli.py)*
- [x] **TEST-07**: Grompp validation tests for custom guest hydrate exports — *Phase 41-10/41-11 (GUI + CLI custom-guest grompp e2e)*
- [x] **TEST-08**: Grompp validation tests for new lattice type exports — *Phase 47-05 (CLI hydrate-only branch grompp for c2te@3x3x3 + ice1hte@4x4x4 native orthorhombic supercells — the last remaining gap; c0te/c1te closed by Phase 45)*

### Documentation

- [x] **DOCS-01**: README updated with custom guest in hydrate workflow — *Phase 48-01/48-02*
- [x] **DOCS-02**: GUI guide updated with new lattice types, custom guest upload, mixed occupancy, depol selector — *Phase 48-03/48-04/48-05 (external docs) + Phase 48-09/48-10/48-11/48-12 (in-app help_dialog.py + tooltips, restructured to indexed format)*
- [x] **DOCS-03**: CLI reference updated with new flags (--lattice-type extended to 10 choices, --cage-guest, --depol) and deprecated banners — *Phase 48-06/48-07*
- [x] **DOCS-04**: Custom guest ITP requirements documented (comb-rule=2, residue name ≤3 chars, _H suffix convention) — *Phase 48-08*

## Deferred (v4.8+)

- Built-in CO₂/H₂/ethane guests (force field verification needed)
- Water model selector (TIP4P/2005, TIP3P, SPC/E)
- Binary clathrate presets (one-click "CH₄+CO₂ sI")
- Cage occupancy display (post-generation fill statistics)
- Per-cage guest assignment (spot_guests for individual cages)
- sT' guest placement (no cagepos in GenIce2)
- 5/6/7-site water models

## Out of Scope

| Feature | Reason |
|---------|--------|
| Built-in CO₂/H₂/ethane guests | Force field parameters need literature verification before bundling |
| Water model selector | Downstream impact on molecule_index + ITP files; defer to v4.8 |
| CIF import pipeline | Requires genice2-cif + validation layer; defer to v5+ |
| Semiclathrate TBAB preset | Multi-step assembly; low MD demand |
| Multiple H₂ per cage | GenIce2 limitation; needs virtual molecule plugin |
| 5/6/7-site water models | Niche; increases ITP burden significantly |
| Polycrystalline hydrate | Separate milestone (v7.0) |
| sT' guest placement | No cagepos attribute in GenIce2; defer to v5+ with custom lattice plugin |
| Auto-convert A/B → sigma/epsilon atomtypes | Risk of rounding errors; reject and ask user to regenerate ITP |
| Random guest orientation in cages | GenIce2 Stage7 uses identity rotation; not configurable |
| Slab orientation flip | PBC no-op — identical structure shifted by half box |
| Mixed sI+sII hydrate | 31% lattice mismatch; zero published MD precedent |
| Force field parameterization for exotic guests | Not a structure generator's job |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PIPE-01 | Phase 38 | Complete |
| PIPE-02 | Phase 38 | Complete |
| PIPE-03 | Phase 38 | Complete |
| PIPE-04 | Phase 38 | Complete |
| LATTICE-01 | Phase 39 | Complete |
| LATTICE-02 | Phase 39 | Complete |
| LATTICE-03 | Phase 39 | Complete |
| LATTICE-04 | Phase 39 | Complete |
| LATTICE-05 | Phase 39 | Complete |
| LATTICE-06 | Phase 39 | Complete |
| LATTICE-07 | Phase 39 | Complete |
| LATTICE-08 | Phase 39 | Complete |
| LATTICE-09 | Phase 39 | Complete |
| GUEST-01 | Phase 40 + 44-02 | Pending (engine done in 40; user GUI surface in 44-02) |
| GUEST-02 | Phase 40 + 44-02 | Pending (engine done in 40; user GUI surface in 44-02) |
| GUEST-03 | Phase 40 + 44-02 | Pending (engine done in 40; user GUI surface in 44-02) |
| GUEST-04 | Phase 40 | Complete |
| GUEST-05 | Phase 40 | Complete |
| GUEST-06 | Phase 38 + 40 | Complete |
| GUEST-07 | Phase 40 | Complete |
| GUEST-08 | Phase 40 | Complete |
| GUEST-09 | Phase 40 | Complete |
| GUEST-10 | Phase 40 | Complete |
| EXPORT-01 | Phase 41 | Complete |
| EXPORT-02 | Phase 41 | Complete |
| EXPORT-03 | Phase 41 | Complete |
| EXPORT-04 | Phase 41 | Complete |
| EXPORT-05 | Phase 41 | Complete |
| EXPORT-06 | Phase 41 | Complete |
| MIXED-01 | Phase 42 | Complete |
| MIXED-02 | Phase 42 | Complete |
| MIXED-03 | Phase 42 | Complete |
| MIXED-04 | Phase 42 | Complete |
| MIXED-05 | Phase 42 | Complete |
| DEPOL-01 | Phase 43 | Complete |
| DEPOL-02 | Phase 43 | Complete |
| DEPOL-03 | Phase 43 | Complete |
| GUI-01 | Phase 39-04 | Complete |
| GUI-02 | Phase 44-02 | Complete |
| GUI-03 | Phase 42-06 + 44-02 | Complete |
| GUI-04 | Phase 43-02 | Complete |
| GUI-05 | Phase 44-02 | Complete |
| GUI-06 | Phase 42-06 + 44-02 | Complete |
| CLI-01 | Phase 39-03 | Complete |
| CLI-02 | Phase 45-01b | Pending (deferred by design — GUI-only for v4.7) |
| CLI-03 | Phase 45-12 | Complete |
| CLI-04 | Phase 42-07 | Complete |
| VTK-01 | Phase 42-04 | Complete |
| VTK-02 | Phase 42-04 + element map | Complete |
| TEST-01 | Phase 40-04 | Complete |
| TEST-02 | Phase 40-04 | Complete |
| TEST-03 | Phase 40-05 | Complete |
| TEST-04 | Phase 39-05 | Complete |
| TEST-05 | Phase 41 | Complete |
| TEST-06 | Phase 42 | Complete |
| TEST-07 | Phase 41-10/41-11 | Complete |
| TEST-08 | Phase 47-05 | Complete |
| DOCS-01 | Phase 48-01/48-02 | Complete |
| DOCS-02 | Phase 48-03/04/05 + 48-09/10/11/12 | Complete |
| DOCS-03 | Phase 48-06/48-07 | Complete |
| DOCS-04 | Phase 48-08 | Complete |

**Coverage:**
- v4.7 requirements: 61 total (PIPE×4, LATTICE×9, GUEST×10, EXPORT×6, MIXED×5, DEPOL×3, GUI×6, CLI×4, VTK×2, TEST×8, DOCS×4)
- Mapped to phases: 61/61 ✓
- Unmapped: 0
- Complete: 57
- Pending: 4 (GUEST-01/02/03 → 45-01b (GUI half done in 44-02); CLI-02 → 45-01b (deferred by design))

---
*Requirements defined: 2026-06-27*
*Last updated: 2026-06-27 after v4.7 milestone initialization*
