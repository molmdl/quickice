# Project Milestones: QuickIce

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
