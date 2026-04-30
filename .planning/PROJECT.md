# QuickIce

## What This Is

A portable, cross-platform GUI application for generating plausible ice structures, ice-water interfaces, and hydrate systems. QuickIce provides a minimal GUI of basic GenIce2 functions with extended capabilities including hydrate generation with guest molecules (CH4, THF), NaCl ion insertion, and multi-molecule GROMACS export. Users select thermodynamic conditions via interactive phase diagram or text input, generate ranked PDB structure candidates with 3D visualization, and build interface structures with GROMACS-ready outputs.

## Core Value

Generate plausible ice structure candidates, interfaces, and hydrates quickly with an intuitive visual interface.

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

### Active

(None — ready for next milestone planning)

### Out of Scope

- Physics-based ranking/simulation (GenIce for generation only)
- Structure analysis tools
- Python API (CLI + GUI only)
- Non-water systems
- Training new ML models
- Web-based viewer
- Real-time preview while typing
- Cloud sync/collaboration
- Additional ice phases beyond GenIce2 support
- Automated interface geometry optimization
- Multiple salt types (KCl, MgCl2)

## Current State

**Version:** v4.0 (shipped 2026-05-01)
**Tech Stack:** Python 3.11, PySide6 6.10.2, VTK 9.5.2, GenIce2, spglib, numpy, scipy, matplotlib, iapws
**Code:** ~21,370 lines of Python (quickice package)
**Test Coverage:** 307+ tests passing
**Output:** PDB, GROMACS (.gro/.top/.itp), PNG/SVG exports, 3D viewport captures
**Phases Supported:** 12 ice polymorphs (Ih, Ic, II, III, IV, V, VI, VII, VIII, IX, XI, X)
**Hydrate Structures:** sI, sII, sH with CH4/THF guests
**Ion Types:** NaCl (Madrid2019 parameters)
**Interface Modes:** Slab, Pocket (sphere/cubic), Piece
**CLI Interface Generation:** Full support for all modes with parameter control
**Triclinic Support:** Ice V, Ice VI work natively; Ice II blocked
**Distribution:** Standalone executable
**Water Model:** TIP4P-ICE (Abascal et al. 2005, DOI: 10.1063/1.1931662)
**Thermodynamic Data:** IAPWS R14-08(2011), Journaux et al. (2019, 2020)
**Density Calculations:** IAPWS R10-06(2009) for Ice Ih, IAPWS-95 for water

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CLI-only interface | Keep it simple, fast to use | ✓ Confirmed — works well |
| PDB output format | Standard, universal compatibility | ✓ Confirmed — universal |
| Ranking approach | Knowledge-based (energy, density, diversity) | ✓ Confirmed — simple and effective |
| Pre-trained model | Minimal resources, no training needed | ✓ Confirmed — vibe-based ranking works |
| Curve-based phase lookup | Avoid polygon overlap errors | ✓ Confirmed — clean boundaries |
| Extended to 12 phases | Comprehensive coverage | ✓ Confirmed — user value |
| KDTree for neighbor search | O(n log n) performance | ✓ Confirmed — 50x faster for large structures |
| Save/restore numpy state | GenIce compatibility | ✓ Confirmed — preserves reproducibility |
| MVVM architecture for GUI | Separation of concerns, testability | ✓ Confirmed — clean signal/slot wiring |
| VTK for 3D viewer | Industry standard, MIT-compatible | ✓ Confirmed — full 3D interactivity |
| PyInstaller bundling | Standalone distribution | ✓ Confirmed — Linux executable complete |
| Exact version pinning | Reproducibility, security | ✓ Confirmed — all deps =x.y.z |
| TIP4P-ICE water model | GROMACS compatibility | ✓ Confirmed — 4-point coordinates |
| Single export action | Simplified workflow | ✓ Confirmed — .gro/.top/.itp together |
| IAPWS/Journaux data sources | Scientific accuracy | ✓ Confirmed — all triple points verified |
| Ice Ic lower boundary at 72K | Avoid Ice XI overlap | ✓ Confirmed — zero polygon overlaps |
| Ice Ic upper pressure ~204 MPa | Ih-II curve boundary | ✓ Confirmed — scientifically accurate |
| Ice Ih bounded at T=150K | Avoid Ice Ic overlap | ✓ Confirmed — clean phase regions |
| Metastability documentation | Scientific transparency | ✓ Confirmed — literature citations added |
| QTabWidget multi-tab workflow | Separate ice/hydrate/interface/ion | ✓ Confirmed — v4.0 |
| QStackedWidget mode switching | Mode-specific controls | ✓ Confirmed — clean UI |
| scipy cKDTree for PBC | Automatic periodic boundaries | ✓ Confirmed — robust overlap detection |
| Line-based bonds (Tab 2) | Performance for large systems | ✓ Confirmed — smooth rendering |
| Multi-molecule GROMACS export | [molecules] counts per type | ✓ Confirmed — v4.0 |
| Ctrl+I for interface export | No conflict with Ctrl+G | ✓ Confirmed — intuitive shortcut |
| IAPWS library for density | Already in environment, scientifically accurate | ✓ Confirmed — v3.5 |
| Native triclinic handling | Transformation creates gaps during tiling | ✓ Confirmed — v3.5 |
| Ice II blocked for interfaces | Rhombohedral crystal incompatible | ✓ Confirmed — v3.5 |
| GROMACS atom wrapping at 100k | Standard convention for large systems | ✓ Confirmed — v3.5 |
| MoleculeIndex dataclass | Variable atoms-per-molecule tracking | ✓ Confirmed — v4.0 |
| Madrid2019 ion parameters | Scientifically validated charges (±0.85) | ✓ Confirmed — v4.0 |
| GAFF2 guest parameters | CH4/THF topology for GROMACS | ✓ Confirmed — v4.0 |
| Dual-style hydrate rendering | Water lines + guest ball-and-stick | ✓ Confirmed — v4.0 |
| Concentration-based ion placement | mol/L → ion count calculation | ✓ Confirmed — v4.0 |
| Per-type VTK actors | Multi-molecule visualization | ✓ Confirmed — v4.0 |
| Tab order: Ice→Hydrate→Interface→Ion | User-approved deviation from spec | ✓ Confirmed — v4.0 |

## Context

- GenIce codebase mapped: `./planning/codebase/` contains architecture docs
- GenIce provides ice generation pipeline and PDB output capability
- This project wraps/extends GenIce with a simple condition matching interface
- Initial prompt notes: "pure vibe coding project"
- v2.0 adds PySide6 GUI with interactive phase diagram and VTK 3D viewer
- v3.0 adds two-tab interface with ice-water interface generation and GROMACS export
- v3.5 adds IAPWS density calculations, triclinic support, and CLI interface generation
- v4.0 adds four-tab workflow with hydrate generation, ion insertion, and multi-molecule export

## Constraints

- **Runtime**: Minimal resource usage — lightweight model
- **Output**: PDB format plus image exports, GROMACS-ready inputs
- **Dependencies**: Only Python libraries in current conda environment
- **Scope**: Water ice and hydrate systems, generation only
- **Installation**: Do NOT auto-install dependencies. Add to environment.yml, seek approval, wait for user to install.
- **Reference**: Do not make up any reference or information. Always verify source. Note and explicitly document limitations.

---
*Last updated: 2026-05-01 after v4.0 milestone completion*
