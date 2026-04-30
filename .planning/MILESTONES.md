# Project Milestones: QuickIce

## v4.0 Molecule Insertion (Shipped: 2026-05-01)

**Delivered:** Hydrate generation (Tab 2), NaCl ion insertion (Tab 4), multi-molecule GROMACS export

**Phases completed:** 28-31.2 (7 phases, 29 plans total)

**Key accomplishments:**
- Hydrate generation with GenIce2 (sI, sII, sH structures with CH4/THF guests)
- Dual-style 3D rendering (water framework as lines, guests as ball-and-stick)
- Ion insertion with concentration-based Na+/Cl- placement (Madrid2019 parameters)
- Multi-molecule GROMACS export with bundled guest .itp files
- Hydrate→Interface workflow via Tab 3 source dropdown
- Water density display in Tab 1 info panel (IAPWS-95)

**Stats:**
- ~21,370 lines of Python (quickice package)
- 7 phases, 29 plans, 4 inserted decimal phases
- 19/33 requirements satisfied, 11 deferred to v4.5
- 17 days (2026-04-14 → 2026-05-01)
- ~290 commits

**Git range:** `feat(28-01)` → `docs(31.2-03)`

**What's next:** v4.5 (custom molecule upload + display controls) or v5.0

**Archive:** [.planning/milestones/v4.0-ROADMAP.md](./milestones/v4.0-ROADMAP.md)

---

## v3.5 Interface Enhancements (Shipped: 2026-04-13)

**Delivered:** Ice Ih IAPWS density, native triclinic handling, CLI interface generation, and documentation corrections

**Phases completed:** 22, 24-27 (16 plans shipped; Phase 23 water density deferred)

**Key accomplishments:**
- Ice Ih IAPWS density (temperature-dependent via R10-06(2009), replaces hardcoded 0.9167 g/cm³)
- Native triclinic handling (Ice V, Ice VI work with lattice-vector tiling; Ice II correctly blocked)
- CLI interface generation (--interface flag with slab/pocket/piece modes and full parameter control)
- GROMACS export validation (atom number wrapping at 100k for large systems)
- Crystal system documentation corrected (Ice VI tetragonal, Ice V monoclinic, Ice II rhombohedral)

**Deferred to v4.0:**
- Water density integration (Tab 1 display, Tab 2 interface spacing) - see Phase 23 UAT

**Stats:**
- ~17,018 lines of Python (test files excluded)
- 5 phases shipped, 1 phase deferred, 16 plans executed
- 11 requirements satisfied, 4 deferred (WATER-01 to WATER-04)
- 18 days (2026-03-26 → 2026-04-13)
- 27 feature commits

**Git range:** `feat(22-01)` → `docs(27-04)`

**What's next:** v4.0 (complete water density + molecule insertion)

**Archive:** [.planning/milestones/v3.5-ROADMAP.md](./milestones/v3.5-ROADMAP.md)

---

## v3.0 Interface Generation (Shipped: 2026-04-11)

**Delivered:** Ice-water interface generation with three geometry modes, phase-distinct visualization, and GROMACS export

**Phases completed:** 16-21 (15 plans total)

**Key accomplishments:**
- Two-tab workflow (Ice Generation + Interface Construction) with candidate selection flow
- Three interface geometry modes (slab, pocket, piece) with mode-specific configuration controls
- PBC-aware structure generation with collision detection using scipy cKDTree
- Phase-distinct VTK visualization (cyan ice, cornflower blue water) with line-based bonds
- GROMACS export with TIP4P-ICE normalization (3→4 atom for ice molecules)
- Version bump to 3.0.0 and comprehensive documentation (README, gui-guide, in-app help)

**Stats:**
- ~12,768 lines of Python (test files excluded)
- 6 phases, 15 plans, 61 must-haves verified
- 4 days (2026-04-08 → 2026-04-11)
- 23/23 requirements satisfied, 0 gaps

**Git range:** `docs(16)` → `test(21)`

**What's next:** v4.0 (next milestone to be defined)

**Archive:** [.planning/milestones/v3.0-ROADMAP.md](./milestones/v3.0-ROADMAP.md)

---

## v2.1.1 Phase Diagram Data Update (Shipped: 2026-04-08)

**Delivered:** Corrected thermodynamic data per IAPWS R14-08(2011) and added Ice Ic metastable phase region

**Phases completed:** 15 (9 plans total)

**Key accomplishments:**
- Updated 32 triple point coordinate values to IAPWS/Journaux compliant values across both data files
- Added Ice Ic polygon region (72-150K, 0-204 MPa) with proper scientific boundaries
- Fixed all polygon overlaps (Ice Ih/Ic, Ice Ic/Ice XI) for clean phase region visualization
- Added metastability documentation with literature citations for scientific users
- Maintained full test coverage (62/62 tests passing) with corrected thermodynamic data
- Complete integration across CLI phase diagram export, GUI visualization, and phase lookup

**Stats:**
- 39 files modified
- ~8,472 lines of Python
- 1 phase, 9 plans (4 initial + 5 gap closure), 18 tasks
- Same-day completion (April 8, 2026, ~13 hours)

**Git range:** `f2e1394` → `de5f274`

**What's next:** v3 Seawater + Interface

**Archive:** [.planning/milestones/v2.1.1-ROADMAP.md](./milestones/v2.1.1-ROADMAP.md)

---

## v2.1 GROMACS Export (Shipped: 2026-04-07)

**Delivered:** GROMACS simulation workflow support with .gro/.top/.itp file export

**Phases completed:** 14 (8 plans total)

**Key accomplishments:**
- GROMACS file writers (.gro, .top) with bundled TIP4P-ICE force field
- GUI GROMACS export with Ctrl+G shortcut (single action for all 3 files)
- CLI GROMACS export with --gromacs and --candidate flags
- Fixed critical bugs (water model TIP3P→TIP4P, PDB residue numbering, AttributeError crash)
- Complete documentation with academic citation (Abascal et al. 2005, DOI: 10.1063/1.1931662)
- Candidate selection for selective export (GUI dropdown, CLI --candidate flag)

**Stats:**
- 79 files modified
- ~8,700 lines of Python
- 1 phase, 8 plans, 30+ tasks
- 3 days (2026-04-05 → 2026-04-07)

**Git range:** `a84323a` → `HEAD`

**What's next:** v2.5 Seawater Phase Diagram

**Archive:** [.planning/milestones/v2.1-ROADMAP.md](./milestones/v2.1-ROADMAP.md)

---

## v2.0 GUI Application (Shipped: 2026-04-04)

**Delivered:** PySide6 GUI with interactive phase diagram and VTK 3D viewer

**Phases completed:** 8-13 (28 plans total)

**Archive:** [.planning/milestones/v2.0-ROADMAP.md](./milestones/v2.0-ROADMAP.md)

---

## v1.1 Hotfix (Shipped: 2026-03-31)

**Delivered:** Performance fixes and critical bug patches

**Archive:** [.planning/milestones/v1.1-ROADMAP.md](./milestones/v1.1-ROADMAP.md)

---

## v1.0 MVP (Shipped: 2026-03-29)

**Delivered:** CLI tool for condition-based ice structure generation

**Archive:** [.planning/milestones/v1-ROADMAP.md](./milestones/v1-ROADMAP.md)
