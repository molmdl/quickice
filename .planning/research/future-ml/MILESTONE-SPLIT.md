# Future Milestone Split Suggestion

**Synthesized from:** 5 research areas in `.planning/research/future-ml/` + genice3-upgrade
**Date:** 2026-06-17 (updated 2026-06-27)
**Based on:** STATE.md, ROADMAP.md, PROJECT.md, all SUMMARY.md + SYNTHESIS.md in future-ml subdirs

---

## Prerequisite: P16 TIP4P-ICE LJ Bug — FIXED ✅

**Status:** FIXED — values corrected in `gromacs_writer.py`

All 6 TOP-writing functions now emit correct TIP4P-ICE LJ parameters via constants `TIP4P_ICE_OW_SIGMA = 3.16680e-1` and `TIP4P_ICE_OW_EPSILON = 8.82110e-1`. Comb-rule remains 2 (Lorentz-Berthelot) with sigma/epsilon format — consistent with the `tip4p-ice.itp` template.

---

## Milestone Structure

### v4.6: Extended Hydrate Generation + Export Hardening

| Source | Phase | What | LOC (est.) | Risk | Value |
|--------|-------|------|-----------|------|-------|
| complex-hydrate | Phase 1: "Free Wins" | Filled ices (c0te, c1te, c2te, ice1hte, sTprime), Ice XVII/XVI, CO₂/H₂/ethane guests, mixed cage occupancy, water model selector, depol mode | ~300-400 | LOW | CRITICAL |
| flexible-interface | Phase 2: P3 Export Fix | Per-molecule `mol_type` MW detection in GROMACS export loop — prerequisite for ice+hydrate | ~30-50 | MEDIUM | HIGH |

**Why first:** GenIce2 already supports ALL free-win features (verified by 14/14 hands-on API tests). Zero new dependencies, zero new architecture. ~80% of scientific value for ~20% of effort. P3 fix is prerequisite for v5.0 ice+hydrate.

**User theme:** *"I can generate filled ice structures, binary clathrates (CO₂+CH₄), and choose water models"*

**Dependencies:** v4.5 complete (InterfaceConfig + MoleculetypeRegistry stable)

**Can overlap with:** v5.0 Phase 1 (asymmetric slab + crystal face) — no shared files

---

### v4.7: Custom Guest Molecule in Hydrate

| Source | Phase | What | LOC (est.) | Risk | Value |
|--------|-------|------|-----------|------|-------|
| custom-guest-hydrate | Phase 1: GRO/ITP → GenIce2 Molecule Bridge | `gro_itp_to_genice2_molecule()` + `register_genice2_molecule()`, GRO position centering, ITP atom name extraction, 5-char name truncation, `audit_name` sanitization | ~100-150 | LOW | CRITICAL |
| custom-guest-hydrate | Phase 2: HydrateGenerator Integration | Wire custom guest into `HydrateStructureGenerator._run_via_api()`, `sys.modules` injection before `generate_ice()`, cage occupancy passthrough, cleanup after generation | ~100-150 | LOW | HIGH |
| custom-guest-hydrate | Phase 3: GROMACS Export Pipeline | ITP validation checklist (moleculetype rename `_H`, atomtypes comment-out, residue name rewrite, comb-rule=2 format detection), `parse_itp_atomtypes()` merging with dedup, `.top` `[atomtypes]` + `[molecules]` section generation | ~150-200 | LOW | HIGH |
| custom-guest-hydrate | Phase 4: GUI/CLI Integration | Hydrate tab custom guest upload panel (.gro + .itp file pair), cage occupancy selector, CLI `--custom-guest` + `--custom-guest-itp` flags, thread-safe `sys.modules` injection in `HydrateWorker` | ~200-300 | MEDIUM | HIGH |
| custom-guest-hydrate | Phase 5: Cage-Guest Size Validation | `guest_effective_diameter()` (max COM distance × 2), cage cavity diameter lookup table (`5¹²`/`5¹²6²`/`5¹²6⁴`/`5¹²6⁸`/`4³5⁶6³`), guest-too-large-for-cage warning | ~50-80 | LOW | MEDIUM-HIGH |

**Why here:** Natural extension of v4.6 hydrate generation. Uses the same `_H` suffix convention (MoleculetypeRegistry), same ITP handling patterns (`comment_out_atomtypes_in_itp()`, `parse_itp_atomtypes()` dedup), same export infrastructure. Zero new dependencies. Does NOT depend on v5.0 (interface) or v5.5 (molecule library). Can ship before or alongside v5.0.

**User theme:** *"I can place my own .gro/.itp molecule (ethanol, propane, cyclopentane) in GenIce2 hydrate cages"*

**Key technical findings:**
1. **`sys.modules` injection works** — Register `types.ModuleType("genice2.molecules.<name>")` with a `Molecule` subclass; GenIce2's `safe_import` finds it. End-to-end verified with CS1 + ethanol guest.
2. **Fallback available** — `ice.repcagepos` and `ice.repcagetype` survive full `generate_ice()` pipeline. Approach B (cage center extraction + manual placement) is fully feasible if injection fails.
3. **GRO 5-char residue name limit** — With `_H` suffix (2 chars), base names must be ≤3 chars. GenIce2 doesn't enforce this; QuickIce must validate and reject non-conforming names.
4. **ITP transformation required** — `_H` suffix on `[moleculetype]`, residue name rewrite in `[atoms]`, `[atomtypes]` commented out (moved to main `.top`), comb-rule=2 sigma/epsilon format validation (reject A/B format).
5. **No new libraries** — Everything uses existing `environment.yml` stack (GenIce2, numpy, PySide6).

**Dependencies:** v4.6 (MoleculetypeRegistry `_H` suffix, ITP handling functions stable)

**Can overlap with:** v5.0 Phase 1 (asymmetric slab) — no shared files; v5.5 (pre-built molecules) — complementary but independent

**Critical pitfall:** `sys.modules` injection in QThread context — concurrent hydrate generations with different custom guests sharing the same plugin name need a lock or unique per-run naming (e.g., `qice_<uuid>_<name>`).

---

### v5.0: Flexible Interface Construction

| Source | Phase | What | LOC (est.) | Risk | Value |
|--------|-------|------|-----------|------|-------|
| flexible-interface | Phase 1: Asymmetric Slab + Crystal Face | Asymmetric slab mode, crystal face QComboBox (basal vs prismatic), LayerSpec engine, LayerPreviewWidget | ~235 | LOW | HIGH |
| flexible-interface | Phase 3: Ice + Hydrate Triple Interface | Dual GenIce2 calls, LCM box dimensions, cross-layer overlap detection, dual-source UI | ~420 | HIGH | HIGH |

**User theme:** *"I can build any ice-water interface: asymmetric slab, basal/prismatic face, ice+hydrate triple"*

**Key insight:** "Slab orientation flip" is physically meaningless under PBC — do NOT implement it.

**Critical open question:** Verify what face current `1h` default actually exposes at Z — it may be prismatic, not basal.

**Dependencies:** v4.6 P3 fix (for Phase 3); Phase 1 depends on v5.0-01 layer_assembly.py

---

### v5.5: Pre-built Molecule Library

| Source | Phase | What | LOC (est.) | Risk | Value |
|--------|-------|------|-----------|------|-------|
| pre-built-molecules | Phase 1: Converter Core | Pure Python AMBER→GROMACS (mol2+frcmod → .gro+.itp) | ~2,000 | MEDIUM | HIGH |
| pre-built-molecules | Phase 2: Molecule Curation | 100-150 curated molecules from phenix geostd, identity verification, JSON index | data only | MEDIUM | HIGH |
| pre-built-molecules | Phase 4: Backend + GUI | MoleculeLibrary backend, browse dialog in CustomMoleculePanel | ~650 | LOW | MEDIUM-HIGH |
| pre-built-molecules | Phase 5: Polish | Attribution, penalty warnings, grompp validation on all 150 molecules | ~180 | LOW | MEDIUM |

**User theme:** *"I can browse 150 pre-built molecules instead of uploading my own .gro/.itp files"*

**Legal:** phenix geostd (BSD-3-Clause) is safe source; FSF GPL FAQ confirms antechamber output inherits input license.

**Critical finding:** PDB CCD has 25% name-collision rate — code "CH4" maps to 33-atom peptide, not methane. Automated identity verification mandatory.

**No new dependencies** — numpy + networkx already installed.

---

### v6.0: Hydrate Analysis Suite

| Source | Phase | What | LOC (est.) | Risk | Value |
|--------|-------|------|-----------|------|-------|
| hydrate-analysis | Phase 1: Cage Capture + Basic Analysis | GenIce2 cage centers in HydrateStructure, RDF, density profiles, cage occupancy, MSD, H-bonds | ~200-300 | LOW | HIGH |
| hydrate-analysis | Phase 2: F3/F4 Order Parameters | Per-molecule F3/F4, stability time series | ~200-300 | MEDIUM | HIGH |
| hydrate-analysis | Phase 3: CHILL+ + freud | 5-way classification, VTK color-by-class | ~300-400 | MEDIUM | HIGH |
| hydrate-analysis | Phase 4: Analysis Tab GUI | Trajectory loading, config panel, progress tracking, result viewer | ~400-500 | LOW | HIGH |
| hydrate-analysis | Phase 5: Advanced Time-Series | Residence time, cage evolution, ring distribution, tetrahedral q | ~300-400 | MEDIUM | MEDIUM-HIGH |

**User theme:** *"I can analyze my hydrate MD trajectories with F3/F4, CHILL+, cage occupancy, and stability tracking"*

**New dependency:** freud-analysis 3.5.0 (BSD-3, MIT-compatible, ~10MB, cp312-abi3 for Python 3.14.3)

**Key infrastructure:** GenIce2 `cagepos1`/`cagetype1` already exposed after `generate_ice()` — currently discarded at `hydrate_generator.py:213`. Capturing this (~50 lines) eliminates need for topological cage detection.

**Critical pitfall:** `scipy.special.sph_harm` replaced by `sph_harm_y(l, m, theta, phi)` with **reversed angle conventions** — prefer freud to avoid entirely.

---

### v7.0: Advanced Hydrate Building

| Source | Phase | What | LOC (est.) | Risk | Value |
|--------|-------|------|-----------|------|-------|
| complex-hydrate | Phase 2: CIF Import | genice2-cif UI integration, cage auto-detection, IZA Zeolite DB browser, CIF validation | ~200-300 | MEDIUM | HIGH |
| complex-hydrate | Phase 3: Python Polycrystal | Voronoi polycrystal builder, multi-phase grains, periodic boundary conditions | ~250-370 | MEDIUM | MEDIUM-HIGH |
| complex-hydrate | Phase 4: Custom Lattice Plugins | TBAB semiclathrate, custom molecule plugins, virtual multi-occupancy molecules | ~40-80 per plugin | LOW | MEDIUM |

**User theme:** *"I can import any hydrate CIF, build polycrystalline hydrates, and create custom lattice plugins"*

**Why deferred:** Niche features. CIF import needs validation layer. TBAB may need ICSD (commercial). Python polycrystal is superior to atomsk (multi-phase, native GRO, no GPL). **Note:** The polycrystal portion is now superseded by the expanded v8.0 Interactive Polycrystalline Builder research below — that research covers the full interactive GUI + multi-phase engine, whereas v7.0 Phase 3 was algorithmic-only (Voronoi + tiling). CIF Import and Custom Lattice Plugins remain v7.0.

---

### v8.0: Interactive Polycrystalline Builder

**Source:** `.planning/research/future-ml/polycrystalline-builder/` (5 research agents, 20 files)
**Date:** 2026-06-28

**User theme:** *"I can draw regions of ice, hydrate, and liquid in a box, assign phases, and generate a polycrystalline MD starting structure"*

**Research verdict:** **V1 FEASIBLE with existing libraries — NO new dependencies needed.** Full 3D arbitrary shapes would require trimesh (BSD-3, ~15MB), but 2.5D prism model (shapely Polygon + Z-range) covers ~90% of scientifically interesting cases (columnar grains, layered slabs, Voronoi tessellations).

| Phase | What | LOC (est.) | Risk | Value |
|-------|------|-----------|------|-------|
| Phase 1: Data Model + Shape Primitives | PhaseRegion dataclass (shapely Polygon + Z-range + phase type), WKT+JSON serialization, shape factory (rectangle, ellipse, polygon), overlap detection (shapely) | ~200-300 | LOW | CRITICAL |
| Phase 2: QGraphicsView 2D Shape Editor | 2D canvas with shape creation/selection/move/resize/delete, QUndoStack, Qt→shapely coordinate mapping, phase assignment combo box | ~400-600 | LOW-MEDIUM | HIGH |
| Phase 3: VTK 3D Region Preview | Translucent region actors (extruded prisms), box wireframe, phase color legend, region labels | ~150-250 | MEDIUM | MEDIUM-HIGH |
| Phase 4: Single-Phase Region Filling | Generate-Clip-Resolve: GenIce2 supercell → clip by molecule COM → fill region. Extends water_filler.py + overlap_resolver.py | ~300-500 | MEDIUM | CRITICAL |
| Phase 5: Crystal Rotation + Multi-Grain Assembly | Rotation matrices for orthogonal phases (Ih, Ic, III, VI), grain boundary buffer zones (1nm water), multi-region overlap resolution | ~300-450 | MEDIUM-HIGH | HIGH |
| Phase 6: Voronoi Auto-Generation | scipy.spatial.Voronoi with mirror-point technique, convert Voronoi cells → shapely Polygons, auto-assign random orientations, seed count control | ~200-300 | MEDIUM | MEDIUM-HIGH |
| Phase 7: Hydrate-Containing Polycrystal | Buffer zone insertion for incompatible lattices (hydrate↔ice), guest molecule handling at boundaries, multi-phase GROMACS export | ~300-500 | HIGH | HIGH |
| Phase 8: GUI Integration + GROMACS Export | New Tab 6 "Polycrystal Builder", PolycrystalWorker (QThread), PolycrystalStructure dataclass, multi-phase GROMACS .gro/.top, phase-specific colors | ~500-700 | MEDIUM | HIGH |

**Key technical findings:**

1. **QGraphicsView is the clear winner for 2D shape editing** — built into PySide6, provides selection/move/resize/undo out of the box. VTK Actor2D overlays and matplotlib are both unsuitable for interactive shape creation. (HIGH confidence)

2. **2.5D data model (shapely Polygon + Z-range)** covers columnar ice, layered slabs, and Voronoi polycrystals — ~90% of scientifically interesting cases. Full 3D CSG (spherical inclusions, tapered pores) requires trimesh — flagged for future, NOT V1. (HIGH confidence, benchmarked)

3. **Generate-Clip-Resolve algorithm is viable** — GenIce2 generates supercells in <0.1s/molecule; clipping by molecule COM membership preserves molecular integrity; existing `tile_structure()` + `overlap_resolver.py` cover most needs. (MEDIUM-HIGH confidence)

4. **Crystal rotation safe for orthogonal phases (Ih, Ic, III, VI, VII) but blocked for triclinic (Ice II, Ice V)** — Ice II already excluded from interfaces. Ice V rotation requires triclinic box output — defer. (HIGH confidence from existing codebase constraints)

5. **Three-tier boundary strategy required** — (1) Same-phase GBs: Voronoi + overlap-removal; (2) Ice-water/hydrate-water: overlap-removal (existing QuickIce pattern); (3) Incompatible lattices (Ice↔hydrate, Ice Ih↔Ice II): mandatory 1–2 nm disordered water buffer zone. (MEDIUM confidence — buffer width 0.5-1.0nm is reasonable but needs MD validation)

6. **No lattice matching exists between ice and clathrate hydrates** — Nguyen et al. 2015 proved definitively. Ice-clathrate interface always contains ~1 nm disordered interfacial layer rich in 5-membered rings. (MEDIUM-HIGH confidence)

7. **Performance benchmarks (actual hardware):** cKDTree overlap detection: 0.17s for 100k atoms, 0.42s for 200k. shapely contains_xy: 0.005s for 100k points. NumPy rotation: 0.003s for 100k atoms. GenIce2: ~0.3μs/molecule. All acceptable for interactive use. (HIGH confidence, benchmarked)

8. **New Tab 6 "Polycrystal Builder"** recommended over sub-mode under Interface tab — different UX interaction model (draw→assign→preview→generate vs select→configure→generate), different component needs (QGraphicsView, QUndoStack, 2D/3D split view). (HIGH confidence from codebase analysis)

9. **VTK offscreen rendering segfaults in headless** — known issue; 3D preview must handle with try/except + fallback.

**Critical pitfall:** 2D↔3D coordinate synchronization — Qt (Y-down) vs VTK (Y-up). A well-tested SceneCoordinateMapper is essential.

**Dependencies:** v4.6 (P3 fix for GROMACS export), v5.0 (interface infrastructure). Phase 1-3 (GUI) can overlap with v6.0/v7.0. Phase 4-7 (core engine) need stable overlap_resolver + water_filler from v5.0.

**Can overlap with:** v6.0 Hydrate Analysis (no shared files), v7.0 CIF Import (no shared files). Cannot overlap with v5.0 Interface (shares overlap_resolver, water_filler).

**Additional dependency for future (NOT V1):** trimesh (BSD-3, ~15MB) for full 3D CSG arbitrary shape definition. Flagged for V2 or v8.5.

**Critical research files:**

| File | Purpose |
|------|---------|
| `polycrystalline-builder/shape-gui/SUMMARY.md` | QGraphicsView + 2.5D model recommendation (HIGH confidence) |
| `polycrystalline-builder/shape-gui/ARCHITECTURE.md` | Two-panel layout, coordinate mapping, QUndoStack patterns |
| `polycrystalline-builder/poly-gen/SUMMARY.md` | Generate-Clip-Resolve algorithm (MEDIUM-HIGH confidence) |
| `polycrystalline-builder/poly-gen/ARCHITECTURE.md` | Pipeline design, rotation matrices, buffer zones |
| `polycrystalline-builder/phase-boundary/SUMMARY.md` | Three-tier boundary strategy (MEDIUM confidence) |
| `polycrystalline-builder/phase-boundary/PITFALLS.md` | 13 pitfalls (6 critical: density mismatch, PBC shapes, buffer composition) |
| `polycrystalline-builder/tech-feasibility/SUMMARY.md` | Feasibility verdict: YES for 2.5D V1 (HIGH confidence, benchmarked) |
| `polycrystalline-builder/tech-feasibility/STACK.md` | Performance benchmarks, API gotchas, no-new-deps proof |
| `polycrystalline-builder/arch-integration/SUMMARY.md` | Tab 6 placement, PolycrystalStructure dataclass, worker threading |
| `polycrystalline-builder/arch-integration/ARCHITECTURE.md` | Component diagram, GROMACS multi-phase export, VTK rendering |

---

## Dependency Graph

```
v4.5 completion (P16 already fixed)
     │
     ├──────────────────────────────┐
     ▼                              ▼
v4.6: Free Wins + P3 Fix     v5.0 Phase 1: Asymmetric Slab + Crystal Face
     │                         (PARALLEL — no shared files)
     │                              │
     ├─────────────┐               │
     ▼             ▼               │
v4.7: Custom   v5.0 Phase 1      │
 Guest in       (can overlap       │
 Hydrate        with v4.7)        │
(depends on                       │
 v4.6 only)                       │
     │                             │
     │◄────────────────────────────┘
     ▼
v5.0 Phase 3: Ice+Hydrate Triple Interface
(depends on v4.6 P3 fix + v5.0 layer_assembly.py)
     │
     ├──────────────────────────────┐
     ▼                              ▼
v5.5: Pre-built Molecules     v6.0: Hydrate Analysis
(INDEPENDENT)                  (INDEPENDENT)
     │                              │
     └──────────────────────────────┘
                    ▼
              v7.0: Advanced Building
              (CIF import, custom lattice plugins)
                    │
                    ├──────────────────────────────┐
                    ▼                              ▼
              v8.0 Phase 1-3:               v8.0 Phase 4-7:
              Polycrystal GUI               Polycrystal Core Engine
              (shape editor, preview)        (depends on v5.0 overlap_resolver,
              (PARALLEL with v6.0/v7.0)       water_filler stable)
                    │                              │
                    └──────────────────────────────┘
                                   ▼
                         v8.0 Phase 8: Full Integration + Export
```

---

### v5.GenIce3: GenIce3 Migration (Future Milestone)

**Source:** `.planning/research/future-ml/genice3-upgrade/` (5 research files + SUMMARY.md)
**Date:** 2026-06-27

| Phase | What | LOC (est.) | Risk | Value |
|-------|------|-----------|------|-------|
| Phase 0: Upstream Engagement | File Python 3.14 issue + PR on GenIce3 GitHub; file fastapi/uvicorn packaging bug | ~0 (issues only) | LOW | CRITICAL (resolves blockers) |
| Phase 1: Proof of Concept | Patched GenIce3 on Python 3.14; validate API; verify GRO output; verify sH cage naming | ~50-100 (prototype branch) | MEDIUM | HIGH |
| Phase 2: Core Migration | Rewrite generator.py + hydrate_generator.py for GenIce3 API; update environment.yml; adapt gromacs_writer.py for `water_model="ice"` | ~130-200 | MEDIUM | CRITICAL |
| Phase 3: Test & Validation | Update all test fixtures; verify GRO round-trips; PyInstaller verification | ~100-200 (test changes) | MEDIUM | HIGH |
| Phase 4: Cleanup & Feature Adoption | Remove 3→4 normalization; update GUI URLs/citations; add cage survey; add CIF input support | ~150-250 | LOW | MEDIUM-HIGH |

**User theme:** *"QuickIce uses the latest GenIce3 engine with direct TIP4P-ICE generation, CIF crystal import, and spot ion placement"*

**Verdict: GO LATER** — Upgrade is the right long-term direction but two hard blockers prevent immediate action:
1. **Python 3.14 incompatibility** — GenIce3 requires `<3.14`, QuickIce runs 3.14.3 (bound is conservative, one-line patch resolves)
2. **genice-core version conflict** — GenIce2 pins `<1.3`, GenIce3 requires `≥1.5.4` (mutually exclusive, full migration required)
3. **Beta status** — GenIce3 is 3.0b3/3.0b4, no stable 3.0.0 release, no timeline announced

**Key benefits of upgrading:**
- `water_model="ice"` eliminates 3→4 atom TIP4P-ICE normalization hack
- CIF input enables arbitrary crystal structures (could replace hardcoded 8-phase limit)
- Spot ions (`-A`/`-C`) allow per-molecule ion replacement (better than unit-cell-only)
- Cage survey JSON for structured cage data in hydrate UI
- Ice XXI (newly discovered 2025 phase) extends phase diagram
- Cleaner API: `Exporter("gromacs").dumps(genice, water_model="ice")` vs `safe_import`+`GenIce`+`generate_ice()`

**Key risks:**
- Beta API may change before stable release
- Fork maintenance if Python 3.14 patch needed long-term
- Complete GenIce2 removal required (no coexistence possible due to genice-core conflict)
- New dependencies: pyyaml, jinja2, cif2ice (pip-only)
- fastapi/uvicorn are in core deps due to packaging bug (should be optional)

**Estimated effort:** 6-11 days total (2-3 days critical path for Phase 2-3)

**Dependencies:** Can be done at any time after blockers resolved. Does NOT depend on v4.6/v4.7/v5.0/v5.5/v6.0.

**Can overlap with:** Nothing — this is a library swap that affects the core generation engine. Should NOT overlap with other milestone work that touches generator.py or hydrate_generator.py.

**Critical research files:**

| File | Purpose |
|------|---------|
| `genice3-upgrade/SUMMARY.md` | Executive summary with phase structure |
| `genice3-upgrade/01-API-MIGRATION-MAP.md` | Complete GenIce2→GenIce3 API mapping (13 calls, HIGH confidence) |
| `genice3-upgrade/02-DEPENDENCY-COMPATIBILITY.md` | Dependency conflicts, Python 3.14 investigation, packaging bug |
| `genice3-upgrade/03-MIGRATION-IMPACT.md` | File-by-file migration checklist, effort estimate, risk register |
| `genice3-upgrade/04-NEW-FEATURES.md` | New feature inventory with QuickIce relevance ratings |
| `genice3-upgrade/05-UPGRADE-RECOMMENDATION.md` | Go/no-go decision matrix, scenario analysis, upstream action items |

**Upstream action items (30 min effort, HIGH ROI):**
1. File issue on genice-dev/GenIce3: Request Python 3.14 support (point out genice-core has no upper bound)
2. File issue/PR: Move fastapi/uvicorn from core deps to [web] optional extras
3. File issue: sH hydrate cage naming documentation (A12/A20 vs 12/16)

---

## Anti-Features (explicitly NOT building)

| Anti-Feature | Source | Why Not |
|-------------|--------|---------|
| Slab orientation flip | flexible-interface | PBC no-op — identical structure shifted by half a box |
| Mixed sI+sII hydrate | flexible-interface | 31% lattice mismatch, zero published MD precedent |
| Atomsk subprocess for generation | complex-hydrate | GenIce2 does everything atomsk can for hydrates |
| Atomsk subprocess for polycrystal | complex-hydrate | Python implementation superior (multi-phase, GRO, no GPL) |
| General drag-and-drop layer UI | flexible-interface | Over-engineering; named modes cover all demand |
| Topological cage detection from scratch | hydrate-analysis | GenIce2 cage centers already available; just capture them |
| pytim for interface detection | hydrate-analysis | GPL-3.0 incompatible with MIT |
| nucleation_tracker as dependency | hydrate-analysis | No LICENSE file; reimplement from published algorithms |
| RDKit/ParmEd/ACPYPE as converter deps | pre-built-molecules | Pure Python converter works; no chemistry toolkits needed |
| ML-based classification | hydrate-analysis | F3/F4 + CHILL+ are interpretable, lightweight, sufficient |
| Packmol integration | complex-hydrate | GenIce2 -g/-G flags cover most guest placement needs |
| Auto-convert A/B → sigma/epsilon atomtypes | custom-guest-hydrate | Risk of rounding errors; REJECT and ask user to regenerate ITP with correct comb-rule |
| Random guest orientation in cages | custom-guest-hydrate | GenIce2 Stage7 uses identity rotation — would require monkey-patching or post-processing |
| Silent GRO residue name truncation | custom-guest-hydrate | Must REJECT with clear error (e.g., "ETOH_H" is 6 chars → user must choose ≤3-char base name) |
| Full 3D CSG shape definition | polycrystalline-builder | Requires trimesh (not in env); 2.5D prism model covers 90% of cases for V1 |
| 3D VTK widget-based shape editing | polycrystalline-builder | VTK widgets are for clipping/selection, not shape creation workflows; QGraphicsView is superior |
| PBC-wrapping shapes in V1 | polycrystalline-builder | Complex geometric splitting; constrain shapes to box boundaries in v8.0, add PBC-wrap in v8.5 |
| Ice II / Ice V rotation in polycrystal | polycrystalline-builder | Triclinic cell rotation creates invalid structures; block like existing interface mode |
| Atomsk subprocess for polycrystal | complex-hydrate | Python implementation superior (multi-phase, GRO, no GPL) |
| Direct crystal-crystal overlap stitching | polycrystalline-builder | No lattice matching between incompatible phases; buffer zone is mandatory |

---

## UI Architecture Decision: Builder / Analyzer Layout

**Decision: Tabs.**

When v6.0 (analysis) lands, the app will have two fundamentally different workflows — Build and Analyze — that need distinct controls, distinct output, and a distinct mental model. Three layout options were considered:

| Option | Pros | Cons |
|--------|------|------|
| **Separate windows** | Clean separation; can have both open simultaneously (build → run → analyze loop) | Window management burden; harder to share state; lost windows |
| **Tabs** | Simple switch; one window; familiar pattern; shared sidebar/context; each tab IS the mode | Can't see both at once |
| **Mode toggle button** | One UI; feels lightweight; fast switch | Hardest to implement well — same widgets serve two masters; crowded or oversimplified; confusing what's visible when |

**Why tabs:**

1. **Builder and Analyzer are separate apps that happen to live in one binary.** You don't analyze while building. Tabs encode this naturally: "I'm done building, let me switch to analysis."

2. **Shared context is easy.** Build tab can have a "Send to Analysis" button that switches tabs and pre-fills the trajectory path. Tabs share the same window state.

3. **No window management.** No "which window has focus," no lost windows behind the terminal.

4. **Each tab owns its layout.** No hide/show widget juggling based on mode — the tab IS the mode. Build tab has parameter controls + Build button + file output. Analyze tab has trajectory loader + metric selector + plot viewer.

5. **Future-proof.** v7.0 advanced building = sub-tab under Build. v5.5 molecule library = tab or panel within Build. Hydrate analysis tiers = sub-tabs under Analyze. The pattern scales.

**Pattern:** `Build tab | Analyze tab` with a shared status bar showing system name + file paths.

---

## Open Questions Requiring User Input

1. ~~**P16 verification**~~ — ✅ FIXED. Comb-rule 2 kept with correct sigma/epsilon values.

2. **v4.6 vs v5.0 sequencing** — Should "free wins" and "asymmetric slab" ship together as one v5.0, or separately as v4.6 + v5.0?

3. **Molecule library scope** — 100-150 molecules or start smaller (30-50 hydrate-relevant only)?

4. **Analysis vs molecules priority** — v6.0 (analysis) has higher scientific value; v5.5 (molecules) is more immediately usable. Which first?

5. **Freud dependency** — Is adding freud-analysis 3.5.0 acceptable? Only new external dependency across all 5 research areas.

6. **Crystal face default** — Should QuickIce switch default from `1h` (likely prismatic) to `one[hh]` (basal) for scientific correctness? Breaking change for existing users.

7. **Custom guest thread safety** — `sys.modules` injection in `HydrateWorker` (QThread) may race if two hydrate generations run concurrently with different custom guests sharing a plugin name. Options: (a) per-run UUID-prefixed names (`qice_<uuid>_<name>`), (b) QMutex lock around registration+generation, (c) enforce serial generation. Which approach?

8. **Custom guest + v5.5 molecule library overlap** — v4.7 (custom guest from user files) and v5.5 (pre-built molecule library) both place guest molecules in hydrate cages. Should v5.5's curated molecules feed into v4.7's bridge, or should they use a separate code path?

9. ~~**Comb-rule convention**~~ — ✅ RESOLVED. Kept comb-rule 2 (Lorentz-Berthelot) with correct sigma/epsilon format — consistent with tip4p-ice.itp template and existing guest atomtypes.

10. **Polycrystal V1 scope** — 2.5D prism model (draw on XY plane, extrude along Z) or start with 3D primitives? Research recommends 2.5D for V1 (90% coverage, no new deps); trimesh for V2 if spherical/tapered shapes needed.

11. **Polycrystal boundary buffer width** — Default 0.5-1.0 nm for incompatible crystal-crystal boundaries. Needs MD validation to confirm. Should this be user-adjustable?

12. **Polycrystal + existing Interface coexistence** — Keep slab/pocket/piece as "quick modes" under Interface tab; polycrystal as new Tab 6 for multi-grain/multi-phase. No replacement planned. Is this acceptable?

13. **PolycrystalStructure vs InterfaceStructure** — Recommended: separate dataclass with `.to_interface_structure()` conversion method for downstream Solute→Ion→Export compatibility. Accept duck-typing pattern (CP-01) or clean conversion?

---

## Research Confidence Matrix

| Area | Confidence | Key Risk |
|------|-----------|---------|
| Free Wins (v4.6) | HIGH | All GenIce2 APIs verified by hands-on testing |
| P3 Export Fix (v4.6) | HIGH | Contained change, well-understood |
| GRO/ITP Bridge (v4.7) | HIGH | sys.modules injection end-to-end verified with CS1 + ethanol |
| HydrateGenerator Integration (v4.7) | HIGH | GenIce2 API stable, injection verified |
| GROMACS Export (v4.7) | HIGH | All building blocks exist (comment_out_atomtypes, parse_itp_atomtypes dedup) |
| GUI/CLI Integration (v4.7) | MEDIUM | QThread + sys.modules thread safety not yet tested |
| Cage-Guest Size Validation (v4.7) | MEDIUM | Cage diameters from training data (cross-verified but not primary-sourced) |
| Asymmetric Slab (v5.0) | HIGH | ~2 lines of assembly change |
| Crystal Face (v5.0) | MEDIUM | Must verify `one[hh]` orthogonality with diagonal reshape |
| Ice+Hydrate (v5.0) | MEDIUM | P3 fix prerequisite; LCM dimension algorithm needs testing |
| Converter Core (v5.5) | HIGH | All formulas verified against existing ITP files |
| Molecule Curation (v5.5) | MEDIUM | PDB CCD name collisions; ~15 molecules need manual creation |
| Cage Capture (v6.0) | HIGH | GenIce2 API verified; ~50 lines |
| F3/F4 (v6.0) | MEDIUM | Threshold values vary by water model; need calibration |
| CHILL+ (v6.0) | MEDIUM | freud convention vs paper convention needs verification |
| CIF Import (v7.0) | MEDIUM | CIF quality varies; validation layer essential |
| Polycrystal (v7.0) | MEDIUM | Periodic Voronoi edge cases need testing |
| Shape GUI (v8.0) | HIGH | QGraphicsView + shapely 2.5D model verified; no new deps |
| Generate-Clip-Resolve (v8.0) | MEDIUM-HIGH | Algorithm sound; boundary artifacts need MD validation |
| Crystal Rotation (v8.0) | HIGH | Orthogonal phases straightforward; triclinic correctly blocked |
| Phase Boundaries (v8.0) | MEDIUM | Three-tier strategy; buffer width needs MD calibration |
| Tech Feasibility (v8.0) | HIGH | All benchmarks pass; V1 no new deps; V2 may need trimesh |
| Architecture Integration (v8.0) | HIGH | Tab 6 placement; PolycrystalStructure dataclass; worker pattern |

---

*Synthesized: 2026-06-17 | Updated: 2026-06-28 (added v8.0 Interactive Polycrystalline Builder from 5-agent research; updated v7.0 note, dependency graph, anti-features, confidence matrix, open questions)*
*For milestone planning: use as input when starting next milestone after v4.5*
