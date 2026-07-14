# QuickIce

A portable GUI application for generating ice structures, ice-water interfaces, hydrate systems, export to full GROMACS-ready format, providing an interface for basic [GenIce2](https://github.com/genice-dev/GenIce2) functions with more focus on gromacs input preparation.

> **Experimental**
>
> - This is a "pure vibe coding project" created as a coding exercise.
> - While I (the human) attempted to review every single reference manually, please report to me for any incorrect citations that I didn't catch or critical flaws in the implemented methods.

## Overview

**What is QuickIce?**

QuickIce v4.7 provides a 6-tab GUI workflow for generating molecular dynamics starting structures:

- **Ice Generation** — 11 ice polymorphs from thermodynamic conditions
- **Hydrate Generation** — 10 lattice types (sI, sII, sH, filled ices, water-only) with built-in and custom guest molecules
- **Interface Construction** — Ice-water boundaries for surface studies
- **Custom Molecule Upload** — User-provided molecules in liquid phase
- **Solute Insertion** — THF/CH₄ concentration-based placement
- **Ion Insertion** — NaCl concentration-based placement

All exports are GROMACS-ready with TIP4P-ICE water model and bundled force field parameters.

**Key Features:**
- Interactive phase diagram with 11 ice polymorphs
- Real-time 3D molecular visualization (VTK)
- Side-by-side candidate comparison
- Multiple export formats (PDB, GROMACS .gro/.top/.itp, PNG, SVG)
- Unified keyboard shortcut for export (Ctrl+S)
- Multi-molecule GROMACS topologies

## Binary Distribution (No Installation Required)

Pre-built executables are available for Linux and Windows. No Python or conda setup needed.

**Quick Start:**
- **Linux**: Download, extract, run `./quickice-gui`
- **Windows**: Download, extract, double-click `quickice-gui.exe`

**Details**: See [README_bin.md](README_bin.md) for download links and usage instructions.

## Installation

### System Requirements

**Linux:**
- GLIBC 2.28 or higher (Ubuntu 20.04+, Debian 10+, Rocky/RHEL 8+)
- 64-bit architecture
- OpenGL support for 3D visualization

### Prerequisites

- Conda (Miniconda or Anaconda)

### One-Time Setup

```bash
# Create conda environment
conda env create -f environment.yml

# For each new shell
source setup.sh

# Verify installation
python -m quickice --help
```

For detailed GUI documentation, see [docs/gui-guide.md](docs/gui-guide.md).

For CLI usage, see [docs/cli-reference.md](docs/cli-reference.md).

## Quick Start (GUI)

### Launch the GUI

```bash
python -m quickice --gui
```

Or for direct GUI access (bypasses router):
```bash
python -m quickice.gui
```

### 5-Minute Workflow

1. **Generate Ice** (Tab 0) — Click on phase diagram or enter T/P/N → Generate → View ranked candidates
2. **Build Interface** (Tab 2) — Select mode (slab/pocket/piece) → Generate interface → View ice/water phases
3. **Insert Molecules** (Tabs 3-5) — Upload custom molecule (Tab 3) OR set solute concentration (Tab 4) OR set ion concentration (Tab 5)
4. **Export** — Press **Ctrl+S** for GROMACS export from active tab

**Example workflow:**
- Tab 0: Generate Ice Ih at 273K, 0.1 MPa
- Tab 2: Build slab interface (ice-water-ice layers)
- Tab 4: Insert THF solutes at 0.5 M concentration
- Tab 5: Insert NaCl ions at 0.15 M concentration
- Ctrl+S: Export multi-molecule GROMACS files

## Entry Point

QuickIce uses `python -m quickice` as the unified entry point:

- **No arguments** — Show help (like `git` with no args)
- **Computation flags** (`-T`, `--interface`, etc.) — CLI mode automatically
- **`--cli`** — Force CLI mode (skip PySide6 import, useful in CI)
- **`--gui`** — Force GUI mode (requires PySide6 + display)
- **`python quickice.py`** — Backward compatible, delegates to unified router

## Features (6-Tab Workflow)

### Tab 0: Ice Generation

Generate ice crystal structures from thermodynamic conditions:

- **11 ice polymorphs** — Ih, Ic, II, III, V, VI, VII, VIII, IX, XV, X
- **Interactive phase diagram** — Click to select T/P conditions
- **10 ranked candidates** — Energy-based ranking with diversity
- **Real-time 3D viewer** — Ball-and-stick, stick, VDW styles
- **Hydrogen bonds** — Dashed line visualization

*Tip: Click on the phase diagram to populate temperature/pressure inputs automatically.*

### Tab 1: Hydrate Generation

Generate clathrate hydrate structures with guest molecules:

- **Structure types** — 10 lattice types: sI, sII, sH (classical clathrates); c0te, c1te, c2te, ice1hte (filled ices); sTprime, 17 (water-only); 16 (Ice XVI empty framework)
- **Guest molecules** — Built-in CH₄ (methane) and THF (tetrahydrofuran), plus custom guest upload (.gro + .itp, GUI-only for v4.7)
- **Mixed cage occupancy** — Assign different guest types to different cage types (e.g., CH₄ in small cages + THF in large cages) with per-cage occupancy percentages
- **Depol mode** — Strict (ice rules, zero net dipole, default) or Optimal (relaxed dipole optimization)
- **Custom guest upload** — Upload a custom .gro + .itp pair; QuickIce validates comb-rule=2, residue name ≤3 chars, and atom count (see Custom Guest Workflow below)
- **Supercell size** — Set unit cell repetitions
- **Dual-style rendering** — Water lines + guest ball-and-stick (per-type colors for mixed guests)

*Export includes bundled GAFF2 parameters for guest molecules.*

### Custom Guest in Hydrate Workflow

QuickIce v4.7 supports uploading custom guest molecules for hydrate cage placement (GUI-only for v4.7):

1. **Upload** — In the Hydrate tab, upload a `.gro` + `.itp` file pair for your custom guest molecule
2. **Validate** — QuickIce validates the ITP: comb-rule must be 2 (Lorentz-Berthelot), residue base name must be ≤3 characters (the `_H` suffix for hydrate guests brings the total to ≤5 chars per GRO format limits), and the GRO must be parseable
3. **Generate** — Select the custom guest from the per-cage dropdown and generate the hydrate structure; the custom guest appears as `Custom: {residue}` in the cage guest combos
4. **Export** — Export for GROMACS; the custom guest `.itp` is bundled with atomtypes commented out and merged into the main `.top`, and the residue name gets the `_H` suffix (e.g., MOL → MOL_H)

> **Note:** Custom guest in hydrate is a GUI-only feature for v4.7. The CLI supports built-in CH₄/THF guests via `--cage-guest`. See [GRO/ITP Guide](docs/gro-itp-guide.md) for detailed ITP format requirements.

### Tab 2: Interface Construction

Build ice-water interfaces for molecular dynamics simulations:

- **Slab mode** — Layered ice-water boundaries (ice | water | ice)
- **Pocket mode** — Water cavities within ice (sphere/cubic)
- **Piece mode** — Ice crystals embedded in water
- **Phase-distinct visualization** — Cyan ice, cornflower blue water
- **PBC-aware collision detection** — Automatic overlap removal

*Generate ice candidates in Tab 0 first. Tab 2 uses candidates from Tab 0.*

### Tab 3: Custom Molecule Upload

Insert user-provided molecules into liquid water:

- **File upload** — Load .gro (coordinates) and .itp (topology) files
- **Two placement modes:**
  - **Random** — Automatic placement with overlap checking
  - **Custom** — User-specified position and rotation (Euler angles)
- **Validation** — Atom count check, residue name verification
- **Distinct rendering** — Unique colors per molecule type

*Requires interface structure from Tab 2. User-provided .itp must include [ atomtypes ] section.*

### Tab 4: Solute Insertion

Insert THF or CH₄ solutes into liquid water:

- **Concentration-based** — Input mol/L → automatic molecule count
- **Solute types** — THF (tetrahydrofuran), CH₄ (methane)
- **Source selection** — Use interface from Tab 2 or custom molecules from Tab 3
- **All-atom overlap checking** — Prevents atom clashes
- **Distinct rendering** — CPK coloring for multi-atom molecules

*Molecule count formula: N = concentration × liquid_volume × Avogadro*

### Tab 5: Ion Insertion

Insert Na⁺/Cl⁻ ions into liquid water:

- **Concentration-based** — Input mol/L → automatic ion count
- **Source selection** — Interface, custom molecule, or solute structures
- **Charge neutrality** — Equal Na⁺/Cl⁻ with Madrid2019 parameters (±0.85e) [Madrid2019]
- **Automatic overlap removal** — Prevents ion-water clashes
- **VDW sphere rendering** — Gold Na⁺, green Cl⁻

*Requires structure from Tab 2, Tab 3, or Tab 4.*

## GROMACS Export

QuickIce exports GROMACS-ready files with unified keyboard shortcut:

### Unified Export (Ctrl+S)

Press **Ctrl+S** from any tab to export the current structure:

| Active Tab | Export Action | Files Generated |
|------------|---------------|-----------------|
| Tab 0 | Ice GROMACS | .gro, .top, tip4p_ice.itp |
| Tab 1 | Hydrate GROMACS | .gro, .top, tip4p_ice.itp, ch4_hydrate.itp/thf_hydrate.itp |
| Tab 2 | Interface GROMACS | .gro, .top, tip4p_ice.itp |
| Tab 3 | Custom Molecule GROMACS | .gro, .top, tip4p_ice.itp, custom.itp |
| Tab 4 | Solute GROMACS | .gro, .top, tip4p_ice.itp, ch4_liquid.itp/thf_liquid.itp |
| Tab 5 | Ion GROMACS | .gro, .top, tip4p_ice.itp, ion.itp |

### Molecule Ordering

Multi-molecule topologies follow GROMACS convention:

```
[ molecules ]
SOL               5919    ; Water molecules
CH4_H             128     ; Hydrate guests (from Tab 1)
THF_L             45      ; Liquid solutes (from Tab 4)
CUSTOM_MOL_1      10      ; Custom molecules (from Tab 3)
NA                12      ; Ions (from Tab 5)
CL                12
```

Order: SOL → hydrate guests → solutes → custom molecules → ions

### Water Model

All exports use **TIP4P-ICE** water model:

```
Abascal, J. L. F., Sanz, E., García Fernández, R., & Vega, C. (2005).
A potential model for the study of ices and amorphous water: TIP4P/Ice.
Journal of Chemical Physics, 122(23), 234511.
DOI: https://doi.org/10.1063/1.1931662
```

### Guest Molecule Parameters

CH₄ and THF use GAFF2 force field with RESP2(0.5) partial charges:

- Prepared with Sobtop 2026.1.16 and Multiwfn 3.8(dev) using the RESP2.sh script from Multiwfn. QM calculations were done using Gaussian 16 Rev. C01.
- See [docs/gro-itp-guide.md](docs/gro-itp-guide.md) for custom molecule preparation

## Ice Phase Support

QuickIce distinguishes between phase detection and structure generation capabilities:

### Phase Detection (12 phases)

The interactive phase diagram can identify 11 ice polymorphs based on temperature and pressure conditions:

| Phase | Crystal System | Pressure Range | Temperature Range |
|-------|----------------|----------------|-------------------|
| Ice Ih | Hexagonal | 0-200 MPa | 0-273.16K |
| Ice Ic | Cubic | Low pressure | < 150K |
| Ice II | Rhombohedral | 200-600 MPa | < 250K |
| Ice III | Tetragonal | 200-400 MPa | 250-260K |
| Ice V | Monoclinic | 400-600 MPa | 250-270K |
| Ice VI | Tetragonal | 600-2000 MPa | 250-350K |
| Ice VII | Cubic | > 2000 MPa | 273-355K |
| Ice VIII | Ordered VII | > 2000 MPa | < 273K |
| Ice IX | Ordered III | 200-400 MPa | < 175K |
| Ice XI | Ordered Ih | Low pressure | < 72K |
| Ice XV | Ordered VI | 950-2100 MPa | 50-100K |
| Ice X | Symmetric | > 30 GPa | — |

**Note:** Phase boundaries depend on both T and P simultaneously. Ranges above are approximate.

### Structure Generation (8 phases)

GenIce2 lattice implementations are available for 8 ice polymorphs:

| Phase | GenIce Lattice | Notes |
|-------|----------------|-------|
| Ice Ih | ice1h | Most common form |
| Ice Ic | ice1c | Cubic ice |
| Ice II | ice2 | Rhombohedral (no interface support) |
| Ice III | ice3 | Tetragonal |
| Ice V | ice5 | Monoclinic |
| Ice VI | ice6 | Double network |
| Ice VII | ice7 | Double network |
| Ice VIII | ice8 | Ordered Ice VII |

**Detection-only phases:** Ice IX, XI, XV, and X appear in the phase diagram for informational purposes but cannot generate molecular structures. This is a GenIce2 library limitation.

**Interface construction:** All generatable phases except Ice II work with Tab 2 interface generation. Ice II (rhombohedral) cannot form orthogonal supercells.

## Documentation

- **[GUI Guide](docs/gui-guide.md)** — Complete graphical interface documentation
- **[CLI Reference](docs/cli-reference.md)** — Command-line interface for ice generation
- **[GRO/ITP Guide](docs/gro-itp-guide.md)** — Preparing custom molecule files
- **[Example Scripts](scripts/)** — Ready-made CLI examples and workflow scripts
- **[Ranking Algorithm](docs/ranking.md)** — How candidates are scored
- **[Design Principles](docs/principles.md)** — Project architecture

## Known Issues

Key limitations:

- Ranking uses distance-based energy estimates, not force field calculations
- Some phase boundaries have limited experimental data
- High-pressure phases (> 30 GPa) have larger uncertainties
- CLI support for v4.7 features is available via `python -m quickice`

## Dependencies

| Package | Purpose |
|---------|---------|
| `iapws` | IAPWS-95 validated water/ice properties |
| `numpy` | Numerical operations |
| `scipy` | Scientific computing |
| `vtk` | 3D molecular visualization |
| `PySide6` | GUI framework |
| `genice2` | Ice structure generation |
| `genice-core` | GenIce core algorithms |
| `pytest` | Testing framework |

## References

If you found QuickIce useful, please cite the [original publication of GenIce2](#genice2), and library of ice/water property curves [IAPWS](#iapws-r14-08).

While QuickIce is mainly a vibe coding project coded by free or open-source LLMs under human supervision, you are also welcomed to cite this repository:
```
QuickIce GUI, Version [version you use], https://github.com/molmdl/quickice (accessed on [DD MM YYYY])
```

### GenIce2
- Repository: https://github.com/genice-dev/GenIce2
- Paper: "GenIce: Hydrogen-disordered ice structures by combinatorial generation", J. Comput. Chem. 2017
- DOI: https://doi.org/10.1002/jcc.25077

### IAPWS R14-08
- Document: "Revised Release on the Pressure along the Melting and Sublimation Curves of Ordinary Water Substance"
- URL: http://www.iapws.org/release/MeltIce.pdf

### IAPWS R10-06
- Document: "Revised Release on the Equation of State 2006 for H₂O Ice Ih"
- URL: https://www.iapws.org/release/Ice-2009.html

### IAPWS-95
- "Revised Release on the IAPWS Formulation 1995 for the Thermodynamic Properties of Ordinary Water Substance for General and Scientific Use"
- URL: https://www.iapws.org/relguide/IAPWS-95.html

### Journaux et al. (2019, 2020)
- Journaux, B. et al. (2019). J. Geophys. Res.: Planets, 124. DOI: 10.1029/2019JE006176
- Journaux, B. et al. (2020). Space Sci. Rev., 216, 7. DOI: 10.1007/s11214-019-0634-7

### Petrenko & Whitworth (1999)
- Petrenko, V. F. & Whitworth, R. W. (1999). Physics of Ice. Oxford University Press. ISBN: 978-0198518945

### CODATA 2017
- Tiesinga, E. et al. (2021). Rev. Mod. Phys., 93(2), 025010. DOI: 10.1103/RevModPhys.93.025010

### spglib
- Repository: https://github.com/atztogo/spglib
- Paper: "Spglib: a software library for crystal symmetry search", Sci. Technol. Adv. Mater., Meth. 4, 2384822 (2024)
- DOI: https://doi.org/10.1080/27660400.2024.2384822

### Multiwfn
- Tian Lu, Feiwu Chen, Multiwfn: A Multifunctional Wavefunction Analyzer, J. Comput. Chem. 33, 580-592 (2012)
- DOI: 10.1002/jcc.22885
- Tian Lu, A comprehensive electron wavefunction analysis toolbox for chemists, Multiwfn, J. Chem. Phys., 161, 082503 (2024)
- DOI: 10.1063/5.0216272

### Sobtop
- Tian Lu, Sobtop, Version 2026.1.16, http://sobereva.com/soft/Sobtop (accessed on 15 Apr 2026)

### GAFF / GAFF2
- Wang, J., Wolf, R. M., Caldwell, J. W., Kollman, P. A., & Case, D. A. (2004). Development and testing of a general amber force field. Journal of Computational Chemistry, 25(9), 1157–1174. DOI: https://doi.org/10.1002/jcc.20035
- He, X., Man, V. H., Yang, Y., Wang, L.-P., & Merz, K. M. (2020). A fast and high-quality charge model for molecular mechanical force fields. Journal of Chemical Information and Modeling, 60(5), 247–257. DOI: https://doi.org/10.1021/acs.jcim.9b01131

### Gaussian 16 Rev. C01
- Gaussian 16, Revision C.01, M. J. Frisch, G. W. Trucks, H. B. Schlegel, G. E. Scuseria, M. A. Robb, J. R. Cheeseman, G. Scalmani, V. Barone, G. A. Petersson, H. Nakatsuji, X. Li, M. Caricato, A. V. Marenich, J. Bloino, B. G. Janesko, R. Gomperts, B. Mennucci, H. P. Hratchian, J. V. Ortiz, A. F. Izmaylov, J. L. Sonnenberg, D. Williams-Young, F. Ding, F. Lipparini, F. Egidi, J. Goings, B. Peng, A. Petrone, T. Henderson, D. Ranasinghe, V. G. Zakrzewski, J. Gao, N. Rega, G. Zheng, W. Liang, M. Hada, M. Ehara, K. Toyota, R. Fukuda, R. Hasegawa, M. Ishida, T. Nakajima, Y. Honda, O. Kitao, H. Nakai, T. Vreven, K. Throssell, J. A. Montgomery, Jr., J. E. Peralta, F. Ogliaro, M. J. Bearpark, J. J. Heyd, E. Brothers, K. N. Kudin, V. N. Staroverov, T. A. Keith, R. Kobayashi, J. Normand, K. Raghavachari, A. P. Rendell, J. C. Burant, J. M. Millam, M. Klene, C. Adamo, R. Cammi, J. W. Ochterski, R. L. Martin, K. Morokuma, O. Farkas, J. B. Foresman, and D. J. Fox, Gaussian, Inc., Wallingford CT, 2016.

### Madrid2019 Ion Parameters
- Zeron, I. M., Abascal, J. L. F., & Vega, C. (2019). A force field of Li+, Na+, K+, Mg2+, Ca2+, Cl−, and SO42− in aqueous solution based on the TIP4P/2005 water model and scaled charges for the ions. Journal of Chemical Physics, 151, 134504.
- DOI: https://doi.org/10.1063/1.5121392

### Madrid2019 / TIP4P-ICE Compatibility
- The Madrid2019 ion model (±0.85e charges) was parameterized for TIP4P/2005 water. QuickIce uses these parameters with TIP4P-ICE water, which is common practice but technically a force field combination.
- Zeron et al. (2019). J. Chem. Phys. 151, 134504. DOI: 10.1063/1.5121392

## Testing

```bash
# Run test suite
pytest

# Verbose output
pytest -v

# Specific test module
pytest tests/ -k solute -q
```

## Project Structure

```
quickice/
├── quickice.py          # Backward-compat entry wrapper
├── quickice/__main__.py # Unified entry point (python -m quickice)
├── quickice/entry.py    # Entry router (CLI/GUI routing)
├── quickice/            # Main package
│   ├── cli/             # Command-line interface
│   ├── gui/             # Graphical User Interface
│   ├── phase_mapping/   # T,P → ice polymorph lookup
│   ├── structure_generation/  # GenIce2 integration
│   ├── ranking/         # Candidate scoring
│   ├── output/          # PDB/GROMACS export
│   └── data/            # Bundled force field files
├── docs/                # Documentation
├── sample_output/       # CLI output examples
├── environment.yml      # Conda environment
└── setup.sh             # Environment setup script
```

---

*QuickIce v4.7 — Extended Hydrate Generation*
*Last updated: 2026-07-12*
