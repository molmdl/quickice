# QuickIce

## What This Is

A cross-platform GUI application for generating plausible ice structures and ice-water interfaces; QuickIce is also a minimal GUI of basic GenIce2 functions with extended capabilities. Users select thermodynamic conditions via interactive phase diagram or text input, generate ranked PDB structure candidates with 3D visualization, and build interface structures (slab, pocket, piece modes) with GROMACS export.

## Core Value

Generate plausible ice structure candidates and interfaces quickly with an intuitive visual interface.

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

### Active

**v3.5 Interface Enhancements:**
- Triclinic→orthogonal transformation (all ice phases for interface)
- CLI interface generation (--interface flag)
- Water density from T/P (display in UI)
- Ice Ih accurate IAPWS density

**v4.0 Molecule Insertion (Future):**
- Tab 2: Molecules to ice (GenIce hydrates, user topology)
- Tab 4: Insert to liquid (NaCl ions, custom molecules)
- Display styles per molecule type in 3D viewer

### Out of Scope

- Physics-based ranking/simulation (GenIce for generation only)
- Structure analysis tools
- Python API (CLI + GUI only)
- Non-water systems
- Training new ML models
- Web-based viewer
- Real-time preview while typing
- Cloud sync/collaboration

## Current Milestone: v3.5 Interface Enhancements

**Goal:** Enable all ice phases in interface generation with CLI access and accurate densities.

**Target features:**
- Triclinic→orthogonal automatic transformation
- CLI interface generation (--interface flag)
- Water density from T/P in UI
- Ice Ih IAPWS density

## Current State

**Version:** v3.0 (shipped 2026-04-11)
**Tech Stack:** Python 3.11, PySide6 6.10.2, VTK 9.5.2, GenIce2, spglib, numpy, scipy, matplotlib
**Code:** ~12,768 lines of Python (test files excluded)
**Test Coverage:** 62 tests passing
**Output:** PDB, GROMACS (.gro/.top/.itp), PNG/SVG exports, 3D viewport captures
**Phases Supported:** 12 ice polymorphs (Ih, Ic, II, III, IV, V, VI, VII, VIII, IX, XI, X)
**Interface Modes:** Slab, Pocket (sphere/cubic), Piece
**Distribution:** Standalone executable
**Water Model:** TIP4P-ICE (Abascal et al. 2005, DOI: 10.1063/1.1931662)
**Thermodynamic Data:** IAPWS R14-08(2011), Journaux et al. (2019, 2020)

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
| QTabWidget two-tab workflow | Separate ice gen from interface | ✓ Confirmed — clean separation |
| QStackedWidget mode switching | Mode-specific controls | ✓ Confirmed — clean UI |
| scipy cKDTree for PBC | Automatic periodic boundaries | ✓ Confirmed — robust overlap detection |
| Line-based bonds (Tab 2) | Performance for large systems | ✓ Confirmed — smooth rendering |
| Single SOL molecule type | Simplifies GROMACS topology | ✓ Confirmed — works with GROMACS |
| Ctrl+I for interface export | No conflict with Ctrl+G | ✓ Confirmed — intuitive shortcut |

## Context

- GenIce codebase mapped: `./planning/codebase/` contains architecture docs
- GenIce provides ice generation pipeline and PDB output capability
- This project wraps/extends GenIce with a simple condition matching interface
- Initial prompt notes: "pure vibe coding project"
- v2.0 adds PySide6 GUI with interactive phase diagram and VTK 3D viewer
- v3.0 adds two-tab interface with ice-water interface generation and GROMACS export

## Constraints

- **Runtime**: Minimal resource usage — lightweight model
- **Output**: PDB format only (plus image exports, GROMACS for interface)
- **Dependencies**: Only Python libraries in current conda environment
- **Scope**: Water ice only, generation only
- **Installation**: Do NOT auto-install dependencies. Add to env.yml, seek approval, wait for user to install.

---
*Last updated: 2026-04-12 after v3.5 milestone started*
