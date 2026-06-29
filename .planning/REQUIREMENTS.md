# Requirements: QuickIce v4.7

**Defined:** 2026-06-27
**Core Value:** Generate ready-to-use initial models and topologies for GROMACS for the simulation of ice, hydrates, solutes, and custom molecules in water

## v4.7 Requirements

Requirements for v4.7 Extended Hydrate Generation milestone. Each maps to roadmap phases.

### Custom Guest in Hydrate

- [ ] **GUEST-01**: User can upload a custom guest molecule (.gro + .itp) and generate a hydrate structure with that molecule placed in cage positions
- [ ] **GUEST-02**: User can select which cage type (small/large/medium) to place the custom guest in
- [ ] **GUEST-03**: User can set cage occupancy percentage for custom guest (0-100%)
- [ ] **GUEST-04**: QuickIce validates custom guest GRO file is parseable (atom names + positions)
- [ ] **GUEST-05**: QuickIce validates custom guest ITP file is parseable (moleculetype name, atom types, charges)
- [ ] **GUEST-06**: QuickIce rejects custom guest residue names >3 chars (GRO 5-char limit with _H suffix)
- [ ] **GUEST-07**: QuickIce rejects ITP files with comb-rule=1 (must be comb-rule=2, Lorentz-Berthelot)
- [ ] **GUEST-08**: QuickIce registers custom guest in sys.modules and GenIce2 finds it via safe_import
- [ ] **GUEST-09**: QuickIce cleans up sys.modules injection after generation (prevents pollution)
- [ ] **GUEST-10**: Custom guest registration is thread-safe (main-thread registration before HydrateWorker starts)

### GROMACS Export for Custom Guests

- [ ] **EXPORT-01**: Custom guest appears in GROMACS .top with correct _H suffix moleculetype name
- [ ] **EXPORT-02**: Custom guest atomtypes are commented out in bundled .itp (moved to main .top [atomtypes] section)
- [ ] **EXPORT-03**: Custom guest ITP atomtypes are merged into main .top with deduplication (no duplicate atomtype entries)
- [ ] **EXPORT-04**: GRO export writes correct residue name for custom guest (≤5 chars with _H suffix)
- [ ] **EXPORT-05**: GROMACS export uses mol_type identity from pipeline (not re-detection from atom names) — P3 fix
- [ ] **EXPORT-06**: GROMACS grompp validates successfully on exported custom guest hydrate structures

### Extended Lattice Types

- [ ] **LATTICE-01**: User can select filled ice C0 (c0te) as hydrate lattice type
- [ ] **LATTICE-02**: User can select filled ice C1 (c1te) as hydrate lattice type
- [ ] **LATTICE-03**: User can select filled ice C2 (c2te) as hydrate lattice type
- [ ] **LATTICE-04**: User can select filled ice Ih (ice1hte) as hydrate lattice type
- [ ] **LATTICE-05**: User can select sT' (sTprime) as hydrate lattice type (water-only, no guest support)
- [ ] **LATTICE-06**: User can select Ice XVI (empty sII framework) as hydrate lattice type
- [ ] **LATTICE-07**: User can select Ice XVII (empty C0 framework) as hydrate lattice type
- [ ] **LATTICE-08**: Triclinic filled ices (C0, C1) are blocked for interface generation with clear error message (like Ice II)
- [ ] **LATTICE-09**: Filled ice lattices use spot_guests code path for guest placement (not parse_guest)

### Mixed Cage Occupancy

- [ ] **MIXED-01**: User can assign different guest types to different cage types on ALL hydrate lattices (sI small/large, sII small/large, sH small/medium/large, filled ice channels)
- [ ] **MIXED-02**: User can assign any available guest type (CH₄, THF, or custom) to any cage type (e.g., CH₄ in small cages + custom guest in large cages)
- [ ] **MIXED-03**: User can set per-cage-type occupancy percentage (e.g., 60% CH₄ in small + 100% custom in large)
- [ ] **MIXED-04**: Mixed occupancy hydrate exports correctly to GROMACS with multiple guest .itp files in .top
- [ ] **MIXED-05**: Mixed occupancy hydrate renders correctly in VTK with per-type styles

### Depol Mode

- [ ] **DEPOL-01**: User can select depol mode (strict/optimal) in Hydrate tab
- [ ] **DEPOL-02**: Depol mode is passed through to GenIce2 generate_ice() call
- [ ] **DEPOL-03**: Default depol mode is 'strict' (preserves current behavior)

### Internal Pipeline (prerequisite engineering)

- [x] **PIPE-01**: _build_molecule_index uses metadata-driven molecule identification (not pattern matching on atom names)
- [x] **PIPE-02**: HydrateConfig carries guest metadata (name, atom labels, atom count) through generation→export pipeline
- [x] **PIPE-03**: GRO residue name overflow is validated at write time (names >5 chars rejected, not silently corrupting format)
- [x] **PIPE-04**: ITP transformation pipeline handles _H suffix, atomtypes comment-out, residue name rewrite for custom guests

### GUI Integration

- [ ] **GUI-01**: Hydrate tab lattice dropdown includes all new lattice types (filled ices + Ice XVI/XVII + sT')
- [ ] **GUI-02**: Hydrate tab has custom guest upload panel (.gro + .itp file pair selection)
- [ ] **GUI-03**: Hydrate tab has cage-type guest assignment controls (small/large/medium → guest type)
- [ ] **GUI-04**: Hydrate tab has depol mode dropdown (strict/optimal)
- [ ] **GUI-05**: Custom guest upload shows validation errors with specific messages (name too long, wrong comb-rule, unparseable)
- [ ] **GUI-06**: Hydrate tab mixed occupancy shows per-cage-type guest type and occupancy controls

### CLI Integration

- [ ] **CLI-01**: CLI --hydrate-lattice flag supports new lattice type names (c0te, c1te, c2te, ice1hte, sTprime, 16, 17)
- [ ] **CLI-02**: CLI --custom-guest and --custom-guest-itp flags for custom guest .gro/.itp file pair
- [ ] **CLI-03**: CLI --depol flag (strict/optimal, default strict)
- [ ] **CLI-04**: CLI mixed occupancy via --guest-small and --guest-large with occupancy values

### VTK Rendering

- [ ] **VTK-01**: Custom guest molecules render with distinct style in hydrate 3D viewer
- [ ] **VTK-02**: Element map is extended for common custom guest atom types (C, O, H, N, S, etc.)

### Testing & Validation

- [ ] **TEST-01**: Unit tests for custom guest GRO/ITP validation (valid, name too long, wrong comb-rule, unparseable)
- [ ] **TEST-02**: Unit tests for sys.modules injection and cleanup
- [ ] **TEST-03**: Unit tests for _build_molecule_index with custom guest types
- [ ] **TEST-04**: E2E tests for filled ice generation (C0, C1, C2, Ih, sT')
- [ ] **TEST-05**: E2E tests for custom guest hydrate generation + GROMACS export
- [ ] **TEST-06**: E2E tests for mixed cage occupancy hydrate generation
- [ ] **TEST-07**: Grompp validation tests for custom guest hydrate exports
- [ ] **TEST-08**: Grompp validation tests for new lattice type exports

### Documentation

- [ ] **DOCS-01**: README updated with custom guest in hydrate workflow
- [ ] **DOCS-02**: GUI guide updated with new lattice types, custom guest upload, mixed occupancy, depol selector
- [ ] **DOCS-03**: CLI reference updated with new flags (--hydrate-lattice, --custom-guest, --depol)
- [ ] **DOCS-04**: Custom guest ITP requirements documented (comb-rule=2, residue name ≤3 chars, _H suffix convention)

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
| LATTICE-01 | Phase 39 | Pending |
| LATTICE-02 | Phase 39 | Pending |
| LATTICE-03 | Phase 39 | Pending |
| LATTICE-04 | Phase 39 | Pending |
| LATTICE-05 | Phase 39 | Pending |
| LATTICE-06 | Phase 39 | Pending |
| LATTICE-07 | Phase 39 | Pending |
| LATTICE-08 | Phase 39 | Pending |
| LATTICE-09 | Phase 39 | Pending |
| GUEST-01 | Phase 40 | Pending |
| GUEST-02 | Phase 40 | Pending |
| GUEST-03 | Phase 40 | Pending |
| GUEST-04 | Phase 40 | Pending |
| GUEST-05 | Phase 40 | Pending |
| GUEST-06 | Phase 40 | Pending |
| GUEST-07 | Phase 40 | Pending |
| GUEST-08 | Phase 40 | Pending |
| GUEST-09 | Phase 40 | Pending |
| GUEST-10 | Phase 40 | Pending |
| EXPORT-01 | Phase 41 | Pending |
| EXPORT-02 | Phase 41 | Pending |
| EXPORT-03 | Phase 41 | Pending |
| EXPORT-04 | Phase 41 | Pending |
| EXPORT-05 | Phase 41 | Pending |
| EXPORT-06 | Phase 41 | Pending |
| MIXED-01 | Phase 42 | Pending |
| MIXED-02 | Phase 42 | Pending |
| MIXED-03 | Phase 42 | Pending |
| MIXED-04 | Phase 42 | Pending |
| MIXED-05 | Phase 42 | Pending |
| DEPOL-01 | Phase 43 | Pending |
| DEPOL-02 | Phase 43 | Pending |
| DEPOL-03 | Phase 43 | Pending |
| GUI-01 | Phase 44 | Pending |
| GUI-02 | Phase 44 | Pending |
| GUI-03 | Phase 44 | Pending |
| GUI-04 | Phase 44 | Pending |
| GUI-05 | Phase 44 | Pending |
| GUI-06 | Phase 44 | Pending |
| CLI-01 | Phase 45 | Pending |
| CLI-02 | Phase 45 | Pending |
| CLI-03 | Phase 45 | Pending |
| CLI-04 | Phase 45 | Pending |
| VTK-01 | Phase 46 | Pending |
| VTK-02 | Phase 46 | Pending |
| TEST-01 | Phase 47 | Pending |
| TEST-02 | Phase 47 | Pending |
| TEST-03 | Phase 47 | Pending |
| TEST-04 | Phase 47 | Pending |
| TEST-05 | Phase 47 | Pending |
| TEST-06 | Phase 47 | Pending |
| TEST-07 | Phase 47 | Pending |
| TEST-08 | Phase 47 | Pending |
| DOCS-01 | Phase 48 | Pending |
| DOCS-02 | Phase 48 | Pending |
| DOCS-03 | Phase 48 | Pending |
| DOCS-04 | Phase 48 | Pending |

**Coverage:**
- v4.7 requirements: 45 total
- Mapped to phases: 45/45 ✓
- Unmapped: 0

---
*Requirements defined: 2026-06-27*
*Last updated: 2026-06-27 after v4.7 milestone initialization*
