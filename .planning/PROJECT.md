# QuickIce

## What This Is

A portable, cross-platform GUI and CLI application for generating plausible ice structures, ice-water interfaces, hydrate systems, and molecular solutions. QuickIce provides a 6-tab GUI with interactive 3D visualization, plus a full-featured CLI pipeline — both producing GROMACS-ready simulation inputs (.gro/.top/.itp). Using GenIce2 for ice and hydrate model support, QuickIce focuses on preparing ready-to-use initial models and topologies for molecular dynamics simulations.

## Core Value

Generate ready-to-use initial models and topologies for GROMACS for the simulation of ice, hydrates, solutes, and custom molecules in water.

## Requirements

### Validated

**v1.0-v1.1 (CLI Tool):**
- ✓ CLI interface with flags: temperature, pressure, molecule count — v1.0
- ✓ Phase diagram mapping (T,P → ice polymorphs) — v1.0 (12 phases)
- ✓ GenIce integration for coordinate generation — v1.0
- ✓ Output 10 ranked PDB candidates per query — v1.0
- ✓ Energy/density-based ranking — v1.0
- ✓ Basic structure validation (spglib) — v1.0
- ✓ README noting "pure vibe coding project" — v1.0
- ✓ Professional documentation (usage, principles, explanation of outcomes) — v1.0
- ✓ Use only Python libraries in current conda environment — v1.0

**v2.0 (GUI Application):**
- ✓ Interactive 12-phase ice diagram with click-to-select — v2.0
- ✓ Textbox input with validation (T: 0-500K, P: 0-10000 bar, N: 4-216) — v2.0
- ✓ VTK-based 3D molecular viewer (ball-and-stick, stick, VDW) — v2.0
- ✓ Hydrogen bond visualization as dashed lines — v2.0
- ✓ Dual viewport for candidate comparison — v2.0
- ✓ Unit cell boundary box toggle — v2.0
- ✓ Auto-rotation and zoom-to-fit — v2.0
- ✓ Export: PDB, PNG, SVG — v2.0
- ✓ Phase info with citations (DOI references) — v2.0
- ✓ Help tooltips and in-app quick reference — v2.0
- ✓ Standalone Linux executable distribution — v2.0
- ✓ License compliance audit (MIT-compatible) — v2.0
- ✓ Exact version pinning for all dependencies — v2.0

**v2.1 GROMACS Export:**
- ✓ GROMACS .gro coordinate file export — v2.1
- ✓ GROMACS .top topology file export — v2.1
- ✓ Bundled tip4p-ice.itp force field — v2.1
- ✓ 4-point water coordinates (TIP4P-ICE) — v2.1
- ✓ GUI export with Ctrl+G shortcut — v2.1
- ✓ CLI --gromacs and --candidate flags — v2.1
- ✓ Complete documentation with academic citation — v2.1

**v2.1.1 Phase Diagram Data Update:**
- ✓ Triple point data corrected to IAPWS R14-08(2011) compliant values — v2.1.1
- ✓ II-III-V and II-V-VI triple points per Journaux et al. (2019, 2020) — v2.1.1
- ✓ Ice Ic metastable phase region (72-150K, 0-204 MPa) — v2.1.1
- ✓ Zero polygon overlaps across all 12 ice phases — v2.1.1
- ✓ Metastability documentation with literature citations — v2.1.1

**v3.0 Interface Generation:**
- ✓ Two-tab workflow (Ice Generation + Interface Construction) — v3.0
- ✓ Three interface geometry modes (slab, pocket, piece) — v3.0
- ✓ Interface configuration controls (boxsize, mode, seed, thickness) — v3.0
- ✓ Liquid water from bundled tip4p.gro — v3.0
- ✓ PBC-aware collision detection via scipy cKDTree — v3.0
- ✓ Phase-distinct VTK visualization (cyan ice, cornflower blue water) — v3.0
- ✓ Interface GROMACS export with TIP4P-ICE normalization — v3.0
- ✓ Ctrl+I shortcut for interface export — v3.0

**v3.5 Interface Enhancements:**
- ✓ Ice Ih IAPWS density (temperature-dependent via R10-06(2009)) — v3.5
- ✓ Native triclinic handling for interface generation — v3.5
- ✓ Ice V, Ice VI interfaces work via lattice-vector tiling — v3.5
- ✓ Ice II correctly blocked with clear error message — v3.5
- ✓ CLI interface generation (--interface flag) — v3.5
- ✓ All three interface modes from CLI (slab/pocket/piece) — v3.5
- ✓ Full parameter control from CLI (box, thickness, seed) — v3.5
- ✓ GROMACS export from CLI for interfaces — v3.5
- ✓ Crystal system documentation corrected — v3.5
- ✓ GROMACS atom wrapping for large systems (>99k atoms) — v3.5

**v4.0 Molecule Insertion:**
- ✓ Hydrate generation with GenIce2 (sI, sII, sH structures) — v4.0
- ✓ Guest molecule support (CH4, THF) with cage occupancy — v4.0
- ✓ Dual-style 3D rendering (water lines, guest ball-and-stick) — v4.0
- ✓ Multi-molecule GROMACS export with bundled guest .itp — v4.0
- ✓ Ion insertion with concentration-based Na+/Cl- placement — v4.0
- ✓ Madrid2019 ion parameters (charge=±0.85) — v4.0
- ✓ Ion visualization as VDW spheres (gold Na+, green Cl-) — v4.0
- ✓ Water density display in Tab 1 info panel (IAPWS-95) — v4.0
- ✓ Hydrate→Interface workflow via Tab 3 source dropdown — v4.0
- ✓ Four-tab workflow (Ice, Hydrate, Interface, Ion) — v4.0

**v4.5 Solute & Custom Molecule Insertion:**
- ✓ TabIndex enum for tab position constants — v4.5
- ✓ MoleculetypeRegistry for unique GROMACS naming — v4.5
- ✓ ITP parser for .itp topology file parsing — v4.5
- ✓ GRO/ITP molecule validator with specific errors — v4.5
- ✓ Solute insertion (THF/CH₄) with concentration-based placement — v4.5
- ✓ All-atom overlap checking with rotation matrices — v4.5
- ✓ Custom molecule upload (.gro/.itp) with validation — v4.5
- ✓ Random and custom placement modes — v4.5
- ✓ Placement validation with preview — v4.5
- ✓ Six-tab workflow (Ice, Hydrate, Interface, Custom, Solute, Ion) — v4.5
- ✓ Source dropdowns (Ion, Solute) for cross-tab data flow — v4.5
- ✓ Custom Molecule as source for Solute and Ion — v4.5
- ✓ CLI feature parity (full pipeline with all v4.5 features) — v4.5
- ✓ Unified entry point (`python -m quickice`) — v4.5
- ✓ Ctrl+S unified export from active tab — v4.5
- ✓ GROMACS export with correct molecule ordering (SOL→guests→solutes→custom→ions) — v4.5
- ✓ 45 grompp validation tests confirming export integrity — v4.5
- ✓ Comprehensive documentation (README, GUI guide, GRO/ITP guide, CLI reference) — v4.5
- ✓ Critical bug fixes (TIP4P-ICE LJ parameters, PBC wrapping, comb-rule, DOIs) — v4.5

### Active

**v4.7 Extended Hydrate Generation:**

- [ ] Filled ice structures (c0te, c1te, c2te, ice1hte, sTprime) via GenIce2
- [ ] New guest molecules in hydrate (CO₂, H₂, ethane)
- [ ] Mixed cage occupancy / binary clathrates (e.g., CO₂+CH₄)
- [ ] Water model selector (TIP4P-ICE, SPC/E, TIP3P) for hydrate generation
- [ ] Depol mode (hydrate without guests)
- [ ] P3 export fix (per-molecule mol_type MW detection in GROMACS export)
- [ ] Custom guest molecule in hydrate (user-provided .gro/.itp → GenIce2 bridge)
- [ ] sys.modules injection for custom guest registration with GenIce2
- [ ] ITP transformation pipeline (_H suffix, atomtypes comment-out, residue rewrite, comb-rule validation)
- [ ] Custom guest upload panel in Hydrate tab (GUI)
- [ ] CLI --custom-guest + --custom-guest-itp flags
- [ ] Cage-guest size validation (effective diameter vs cage cavity)
- [ ] Thread-safe custom guest registration (QThread context)

### Out of Scope

- Physics-based ranking/simulation (GenIce for generation only)
- Structure analysis tools
- Python API (CLI + GUI only)
- Non-water systems
- Training new ML models
- Web-based viewer
- Cloud sync/collaboration
- Additional ice phases beyond GenIce2 support
- Automated interface geometry optimization
- Multiple salt types (KCl, MgCl2)
- Multiple solute types simultaneously (defer to v5.0+)
- Multiple custom molecule types in single session (beyond v4.7 scope)
- VTK rendering correctness (headless environment limitation)
- CIF crystal import (defer to v7.0)
- Polycrystal builder (defer to v7.0)
- Hydrate analysis (F3/F4, CHILL+, RDF — defer to v6.0)
- GenIce3 migration (blocked: Python 3.14 compat, genice-core version conflict)
- Auto-convert A/B → sigma/epsilon atomtypes (risk of rounding errors; reject and ask user to regenerate)
- Slab orientation flip (PBC no-op — identical structure shifted by half box)
- Random guest orientation in cages (GenIce2 Stage7 uses identity rotation)

## Current Milestone: v4.7 Extended Hydrate Generation

**Goal:** Extend hydrate generation with filled ices, new guests, custom cage occupancy, water model selection, and user-provided custom guest molecules via GenIce2 bridge

**Target features:**
- Filled ice structures (c0te, c1te, c2te, ice1hte, sTprime) — zero new architecture, GenIce2 supports all
- New guest molecules (CO₂, H₂, ethane) + mixed cage occupancy (binary clathrates)
- Water model selector for hydrate generation (TIP4P-ICE, SPC/E, TIP3P)
- Custom guest molecule bridge (.gro/.itp → GenIce2 molecule via sys.modules injection)
- GROMACS export hardening (P3 fix, ITP transformation pipeline)

## Current State

**Version:** v4.5 (shipped 2026-06-27)
**Tech Stack:** Python 3.14, PySide6 6.10.2, VTK 9.5.2, GenIce2, spglib, numpy, scipy, matplotlib, iapws
**Code:** ~33,558 lines of Python (quickice package), ~27,838 lines (tests)
**Test Coverage:** 1,032 tests passing (422 E2E, 45 grompp validation)
**Output:** PDB, GROMACS (.gro/.top/.itp), PNG/SVG exports, 3D viewport captures
**Phases Supported:** 12 ice polymorphs (Ih, Ic, II, III, IV, V, VI, VII, VIII, IX, XI, X)
**Hydrate Structures:** sI, sII, sH with CH4/THF guests
**Ion Types:** NaCl (Madrid2019 parameters)
**Solute Types:** CH4, THF (GAFF2 parameters)
**Custom Molecules:** User-provided .gro/.itp with validation
**Interface Modes:** Slab, Pocket (sphere/cubic), Piece
**CLI Pipeline:** Full 6-step pipeline (source→interface→custom→solute→ion→export)
**Entry Point:** `python -m quickice` (auto-routes CLI/GUI)
**Distribution:** Standalone executable (PyInstaller)
**Water Model:** TIP4P-ICE (Abascal et al. 2005, DOI: 10.1063/1.1931662)
**Combining Rule:** Lorentz-Berthelot (comb-rule=2, AMBER/GAFF2 convention)
**Thermodynamic Data:** IAPWS R14-08(2011), Journaux et al. (2019, 2020)
**Density Calculations:** IAPWS R10-06(2009) for Ice Ih, IAPWS-95 for water

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CLI-only interface | Keep it simple, fast to use | ✓ Confirmed |
| PDB output format | Standard, universal compatibility | ✓ Confirmed |
| Ranking approach | Knowledge-based (energy, density, diversity) | ✓ Confirmed |
| KDTree for neighbor search | O(n log n) performance | ✓ Confirmed — 50x faster for large structures |
| MVVM architecture for GUI | Separation of concerns, testability | ✓ Confirmed — clean signal/slot wiring |
| VTK for 3D viewer | Industry standard, MIT-compatible | ✓ Confirmed |
| PyInstaller bundling | Standalone distribution | ✓ Confirmed |
| TIP4P-ICE water model | GROMACS compatibility | ✓ Confirmed |
| Single export action | Simplified workflow | ✓ Confirmed |
| QTabWidget multi-tab workflow | Separate ice/hydrate/interface/custom/solute/ion | ✓ Confirmed — v4.5 (6 tabs) |
| MoleculetypeRegistry for molecule tracking | Unique GROMACS naming (CH4_H vs CH4_L) | ✓ Confirmed — v4.5 |
| TabIndex enum for tab positions | Prevents hardcoded index bugs after reordering | ✓ Confirmed — v4.5 |
| All-atom overlap checking | Multi-atom molecules need full overlap check (not COM) | ✓ Confirmed — v4.5 |
| GAFF2 parameters for solutes | Consistent with hydrate guest parameters | ✓ Confirmed — v4.5 |
| TIP4P-ICE comb-rule 2 (Lorentz-Berthelot) | AMBER/GAFF2 convention; LJ bug was in VALUES not rule | ✓ Confirmed — v4.5 |
| TIP4P_ICE_OW_SIGMA/EPSILON module constants | Single source of truth prevents copy-paste exponent errors | ✓ Confirmed — v4.5 |
| Unified entry point via `python -m quickice` | Auto-routes CLI/GUI with graceful fallback | ✓ Confirmed — v4.5 |
| CustomMoleculeStructure complete system export | Follows IonStructure pattern for chain workflow | ✓ Confirmed — v4.5 |
| WATER_VOLUME_NM3 shared constant | Single source of truth replaces 9 hardcoded values | ✓ Confirmed — v4.5 |
| AVOGADRO single definition in ion_inserter.py | DRY: 3 definitions consolidated to 1 | ✓ Confirmed — v4.5 |
| Concentration range validation [0.0, 5.0] mol/L | Seawater ~0.6 M, saturated ~5 M; absurd values rejected | ✓ Confirmed — v4.5 |
| SoluteStructure.molecule_indices naming (tuple) | Uses tuple[int,int] instead of MoleculeIndex; working workaround exists | ⚠️ Revisit |
| sys.modules injection for custom guests | GenIce2 safe_import finds registered ModuleType objects; verified end-to-end with CS1+ethanol | — v4.7 |
| _H suffix for hydrate guests (MoleculetypeRegistry) | Consistent with v4.5 guest naming; distinguishes hydrate guests from liquid solutes (_L) | — v4.7 |
| Reject A/B → sigma/epsilon auto-conversion | Risk of rounding errors in LJ parameters; force user to provide correct comb-rule=2 ITP | — v4.7 |
| GRO 5-char residue name limit with _H suffix | Base names ≤3 chars; reject non-conforming names with clear error | — v4.7 |

## Context

- GenIce codebase mapped: `./planning/codebase/` contains architecture docs
- GenIce provides ice generation pipeline and PDB output capability
- This project wraps/extends GenIce with a simple condition matching interface
- Initial prompt notes: "pure vibe coding project"
- v2.0 adds PySide6 GUI with interactive phase diagram and VTK 3D viewer
- v3.0 adds two-tab interface with ice-water interface generation and GROMACS export
- v3.5 adds IAPWS density calculations, triclinic support, and CLI interface generation
- v4.0 adds four-tab workflow with hydrate generation, ion insertion, and multi-molecule export
- v4.5 adds six-tab workflow with solute insertion, custom molecule upload, CLI pipeline, unified entry point

**Shipped v4.5 with ~61,396 LOC Python (33,558 package + 27,838 tests).**
**Test suite: 1,032 tests (422 E2E, 45 grompp validation, 51 CLI pipeline).**
**User testing showed demand for custom molecule workflows (Phase 34).**

**Known tech debt:**
- SoluteStructure.molecule_indices naming inconsistency (working workaround)
- Liquid volume TODO (uses total box volume instead of liquid region)
- 2 missing low-priority screenshots (validation-preview, solute-source-dropdown)
- Stale code comments in main_window.py ("Future data flows" now current)

## Constraints

- **Runtime**: Minimal resource usage — lightweight model
- **Output**: PDB format plus image exports, GROMACS-ready inputs
- **Dependencies**: Only Python libraries in current conda environment
- **Scope**: Water ice and hydrate systems, generation only
- **Installation**: Do NOT auto-install dependencies. Add to environment.yml, seek approval, wait for user to install.
- **Reference**: Do not make up any reference or information. Always verify source. Note and explicitly document limitations.

---
*Last updated: 2026-06-27 after v4.7 milestone initialization*
