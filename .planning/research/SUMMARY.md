# Project Research Summary: QuickIce v3 Milestone Exploration

**Project:** QuickIce — Post-v2.0 Feature Research  
**Domain:** Scientific visualization / Computational chemistry  
**Researched:** 2026-04-05  
**Confidence:** HIGH (verified via official documentation and standards)

---

## Executive Summary

This research synthesizes three potential feature directions for QuickIce's next milestone: GROMACS output support, seawater/saltwater ice phase diagrams, and liquid-solid interface generation. All three features are technically feasible and leverage existing dependencies, with no new external libraries required for MVP implementations.

**Recommended approach:** Implement features in order of increasing complexity — seawater phase diagram first (v2.1, lowest effort), GROMACS support second (v2.2), and interface generation last (v2.5/v3.0). This sequencing allows users to benefit from simpler features while the more complex interface generation matures. The critical risk across all features is validation — generated outputs must be scientifically meaningful, not just visually correct.

**Key insight:** All three features share a common architectural pattern — new service layer modules that integrate into the existing MVVM architecture without modifying core generation logic. This keeps the codebase maintainable and allows incremental delivery.

---

## Key Findings

### Feature 1: GROMACS Output Support (STACK_GROMACS.md)

**Complexity:** 3/5 (MODERATE)  
**Estimated Effort:** ~38 hours (~5 days)  
**Confidence:** HIGH

GenIce2 already produces GROMACS `.gro` coordinate files, but NOT `.top` topology files. QuickIce must generate topology files from scratch using the TIP4P-ICE force field parameters (published values from Abascal et al. 2005).

**Core requirements:**
- Generate `.top` topology file with proper GROMACS format
- Bundle `tip4p-ice.itp` force field file as application resource
- Integrate into existing export menu with UI controls
- Validate files can be loaded by GROMACS

**Technical findings:**
- GenIce2 provides `.gro` output natively (`-f gromacs` flag)
- TIP4P-ICE is NOT built into GROMACS; custom `.itp` required
- All parameters verified from primary literature (Vega group publications)

**Dependencies:** None new — GenIce2, NumPy already in environment

---

### Feature 2: Seawater Ice Phase Diagram (FEATURES_SEAWATER.md)

**Complexity:** 2/5 (LOW-MEDIUM)  
**Estimated Effort:** ~20-30 hours (~3-4 days)  
**Confidence:** HIGH

The IAPWS library (already installed: `iapws==1.5.5`) provides full IAPWS-08 seawater thermodynamics including freezing point calculations. The key finding is that seawater ice is fundamentally different from pure water ice — it's a single phase (Ice Ih) with brine pockets, not multiple high-pressure polymorphs.

**Core requirements:**
- New S-T (Salinity-Temperature) phase diagram widget
- Freezing curve calculation via IAPWS `_Tf()` function
- Single phase region (Ice Ih + brine) vs liquid seawater
- New tab in GUI (separate axes from T-P pure water diagram)

**Technical findings:**
- Seawater ice has NO high-pressure polymorphs at ocean conditions (<100 MPa)
- Valid salinity range: 0-12% (covers all natural seawater)
- IAPWS-08 is the authoritative international standard
- Different visualization: S-T axes, single freezing curve

**Dependencies:** None new — `iapws==1.5.5` already installed

---

### Feature 3: Liquid-Solid Interface Generation (ARCHITECTURE_INTERFACE.md)

**Complexity:** 3/5 (MODERATE)  
**Estimated Effort:** ~9-14 days (~70-100 hours)  
**Confidence:** MEDIUM

GenIce2 does NOT support interface generation — it's purely an ice crystal generator. Three approaches exist: rule-based assembly (recommended for MVP), pre-generated configuration library, or MD-based relaxation (avoid for now).

**Core requirements:**
- New `InterfaceGenerator` service module
- Liquid water configuration generator
- Interface assembly and validation logic
- VTK visualization enhancements (phase coloring, boundary plane)

**Technical findings:**
- Must NOT modify GenIce2; build interface as post-processing layer
- Rule-based assembly sufficient for visualization use case
- May need validation testing for physical reasonableness
- Existing VTK viewer can be extended for phase differentiation

**Dependencies:** None new — GenIce2, NumPy, VTK already in environment

---

## Version Recommendations

### v2.1: Seawater Phase Diagram

**Rationale:** Lowest complexity, leverages existing library, adds immediate user value for ocean science users. Well-defined scope with authoritative data source (IAPWS-08).

**Delivers:**
- Salinity-Temperature phase diagram tab
- Freezing point depression curve
- Phase region labels (Sea Ice vs Liquid Seawater)
- Click interaction with phase info display

**Estimated timeline:** 3-4 days  
**Risk level:** LOW

---

### v2.2: GROMACS Export

**Rationale:** Moderate complexity, serves computational chemistry users who need simulation-ready files. Builds on existing GenIce integration.

**Delivers:**
- GROMACS `.top` topology file generation
- Bundled `tip4p-ice.itp` force field file
- Export menu integration
- GROMACS validation testing

**Estimated timeline:** 5 days  
**Risk level:** MEDIUM (validation needed)

---

### v2.5: Interface Generation (MVP)

**Rationale:** Higher complexity, requires new service layer. Rule-based assembly provides core functionality without MD complexity. Could be v3.0 if scope expands.

**Delivers:**
- Ice-water interface structure generation
- Rule-based assembly combining ice + liquid layers
- Phase-colored VTK visualization
- Basic interface orientation controls

**Estimated timeline:** 2-3 weeks  
**Risk level:** MEDIUM (needs validation testing)

---

### v3.0: Enhanced Features (Future)

Potential v3.0 enhancements depending on user feedback:
- Configuration library for pre-generated interface structures
- MD relaxation option for interface generation
- Extended water models beyond TIP4P-ICE
- 3D S-T-P surface visualization
- Brine pocket fraction modeling

---

## Complexity Comparison Matrix

| Feature | Complexity | Effort | Dependencies | Risk | User Value |
|---------|------------|--------|--------------|------|------------|
| Seawater Phase Diagram | 2/5 | 3-4 days | None | LOW | HIGH (ocean science) |
| GROMACS Export | 3/5 | 5 days | None | MEDIUM | HIGH (simulation) |
| Interface Generation | 3/5 | 2-3 weeks | None | MEDIUM | MEDIUM (visualization) |

---

## Effort Breakdown

### Seawater Phase Diagram (~25 hours)

| Task | Hours | Notes |
|------|-------|-------|
| Core logic (S-T lookup) | 2 | Wrapper around `_Tf()` |
| Phase diagram widget | 10 | New widget, S-T axes |
| GUI tab integration | 5 | Standard pattern |
| Export functionality | 3 | Reuse existing export |
| Testing | 5 | Unit + integration |
| **Total** | **25** | |

### GROMACS Export (~38 hours)

| Task | Hours | Notes |
|------|-------|-------|
| Research finalization | 2 | Verify TIP4P-ICE params |
| Create tip4p-ice.itp file | 4 | Encode force field |
| Implement .top generator | 16 | Python module |
| Integrate with export menu | 8 | UI integration |
| Testing with GROMACS | 8 | Validate files work |
| **Total** | **38** | |

### Interface Generation (~90 hours)

| Task | Hours | Notes |
|------|-------|-------|
| Interface module development | 16 | Core generation logic |
| Liquid generator module | 12 | Water configuration |
| Worker/ViewModel integration | 8 | Standard patterns |
| VTK visualization updates | 12 | Phase coloring |
| UI controls | 8 | New input controls |
| Testing & validation | 20 | Physical reasonableness |
| Documentation | 14 | User guide updates |
| **Total** | **90** | |

---

## Dependencies Analysis

### New Dependencies Required: NONE

All three features can be implemented using existing packages:

| Package | Version | Used By |
|---------|---------|---------|
| genice2 | 2.2.13.1 | GROMACS, Interface |
| iapws | 1.5.5 | Seawater |
| numpy | (existing) | All features |
| vtk | 9.5.2 | Interface visualization |
| PySide6 | 6.10.2 | All UI work |

### Optional Future Dependencies

| Package | Purpose | Recommended For |
|---------|---------|------------------|
| mdanalysis | File validation | Post-MVP GROMACS |
| openmm | MD relaxation | v3.0 Interface |

---

## Architecture Implications

### Existing MVVM Pattern Extends Cleanly

All three features follow the same architectural pattern:

```
FeatureXService (new module)
    │
    ├── Encapsulates feature logic
    ├── Called by ViewModel
    └── Returns typed result objects
```

### New Modules Required

| Module | Location | Responsibility |
|--------|----------|----------------|
| `gromacs_export.py` | `export/` | .top file generation |
| `seawater_diagram.py` | `diagrams/` | S-T phase diagram widget |
| `interface_generator.py` | `structure_generation/` | Ice-water assembly |
| `liquid_generator.py` | `structure_generation/` | Liquid water config |

### ViewModel Additions

Each feature needs:
- New signal (e.g., `seawater_generation_complete`)
- New method (e.g., `start_seawater_generation()`)
- New worker class (runs in QThread)

---

## Critical Pitfalls

### 1. GROMACS Validation (MEDIUM Severity)
**Risk:** Generated `.top` files may not load correctly in GROMACS.  
**Prevention:** Test with actual GROMACS installation, validate atom naming conventions.

### 2. Interface Physical Reasonableness (MEDIUM Severity)
**Risk:** Rule-based interfaces may have unrealistic hydrogen bonding at boundaries.  
**Prevention:** Compare with published MD simulation snapshots; add validation tests.

### 3. Seawater Axis Confusion (LOW Severity)
**Risk:** Users may expect T-P diagram but get S-T diagram instead.  
**Prevention:** Clear labels, tooltips, documentation explaining the difference.

### 4. Performance with Dense Sampling (LOW Severity)
**Risk:** Dense S-T grids may slow down rendering.  
**Prevention:** Use vectorized numpy operations, lazy evaluation.

---

## Recommendations for Milestone Scoping

### Recommended Release Schedule

| Version | Feature | Timeline | Cumulative |
|---------|---------|----------|------------|
| v2.1 | Seawater Phase Diagram | Week 1-2 | 2 weeks |
| v2.2 | GROMACS Export | Week 3-4 | 4 weeks |
| v2.5 | Interface Generation MVP | Week 5-7 | 7 weeks |

### Alternative: Single v3.0 Release

Bundle all features into v3.0 (estimated 7-8 weeks total). This delays user value but creates a more significant release.

**Recommendation:** Incremental releases preferred — users benefit from each feature immediately.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| GROMACS Technical | HIGH | GenIce2 capabilities verified; format documented |
| GROMACS Parameters | HIGH | TIP4P-ICE from primary literature |
| Seawater Technical | HIGH | IAPWS-08 is authoritative standard |
| Seawater Feasibility | HIGH | Single function call for freezing point |
| Interface Technical | MEDIUM | Approaches identified, implementation details need refinement |
| Interface Validation | LOW | Need domain expert review for physical reasonableness |

**Overall confidence:** MEDIUM-HIGH

---

## Gaps to Address

| Gap | How to Address | Priority |
|-----|----------------|----------|
| Interface validation criteria | Consult with domain expert or compare to MD literature | HIGH |
| GROMACS user testing | Recruit beta testers from computational chemistry users | MEDIUM |
| Seawater user personas | Survey ocean science users for expected use cases | LOW |
| Performance benchmarks | Test with various molecule counts | LOW |

---

## Sources

### Primary (HIGH confidence)

1. **GenIce2 PyPI** — https://pypi.org/project/genice2/ — GROMACS .gro format support verified
2. **GROMACS Manual** — https://manual.gromacs.org/current/reference-manual/topologies/topology-file-formats.html — .top format specification
3. **IAPWS-08 Standard** — http://www.iapws.org/relguide/Seawater.html — Seawater thermodynamics
4. **IAPWS Python Library** — https://pypi.org/project/iapws/ — Implementation
5. **TIP4P-ICE Publication** — Abascal et al., J. Chem. Phys. 122, 234511 (2005) — Force field parameters

### Secondary (MEDIUM confidence)

6. **TIP4P-ICE in GROMACS** — González & Abascal, JCTC 14, 3674 (2018)
7. **Sea Ice Wikipedia** — https://en.wikipedia.org/wiki/Sea_ice — Phase behavior
8. **Phases of Ice Wikipedia** — https://en.wikipedia.org/wiki/Phases_of_ice — Pressure thresholds

### Tertiary (MEDIUM confidence)

9. **QuickIce Architecture** — Existing codebase patterns (MVVM, threading, VTK)

---

## Open Questions

1. **Interface validation:** Should we engage domain experts for review, or rely on comparison with published structures?
2. **GROMACS testing:** Can users provide GROMACS installations for validation, or is offline file validation sufficient?
3. **Seawater UI:** Should seawater diagram be a tab, or integrated into the existing phase diagram?
4. **Version numbering:** Should interface generation be v2.5 (small increment) or v3.0 (major)?

---

*Research completed: 2026-04-05*  
*Ready for milestone definition: yes*
