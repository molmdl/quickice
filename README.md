# QuickIce

> **Experimental** 
>
> - This is a "pure vibe coding project" created as a coding exercise. No physics simulations are performed. Results are plausible candidates, not validated structures.
>
> - While I (the human) attempted to review every single reference manually, please report to me for any incorrect citations that I didn't catch or critical flaws in the implemented methods.

A portable condition-based ice structure candidate generator from thermodynamic conditions with a simple Ice-water interface builder. QuickIce also generates clathrate hydrate structures and inserts ions into interface systems (GUI-only). 

QuickIce is also a minimal GUI of basic [GenIce2](https://github.com/genice-dev/GenIce2) functions with extended capabilities.

## Overview

**What is QuickIce?**

QuickIce generates plausible ice crystal structure candidates and constructs ice-water interfaces from given thermodynamic conditions (temperature and pressure). The v4.0 GUI introduces **interface construction** and **molecule insertion** — build slab, pocket, and piece geometries for molecular dynamics simulations of ice-water systems, generate clathrate hydrate structures, and insert ions into liquid phases.

**Interface construction** is a major feature available in the GUI (Tab 3), enabling:
- **Slab interfaces** — Layered ice-water boundaries for surface studies
- **Pocket interfaces** — Water cavities within ice for confined water studies
- **Piece interfaces** — Ice crystals embedded in water for nucleation studies

**Hydrate generation** (Tab 2, GUI-only) and **ion insertion** (Tab 4, GUI-only) extend QuickIce for molecular insertion studies:

**Hydrate generation:**
- Generate clathrate hydrate structures (sI, sII, sH)
- Select guest molecules (CH₄, THF)
- Configure cage occupancy and supercell size
- Export to GROMACS with bundled force field parameters

**Ion insertion:**
- Insert Na⁺/Cl⁻ ions into liquid water regions
- Concentration-based ion count calculation
- Automatic charge neutrality enforcement
- Export to GROMACS with Madrid2019 ion parameters

*Note: Hydrate and ion features are available in the GUI only. CLI support may be added in a future release.*

Given temperature and pressure, QuickIce:

1. **Identifies the ice polymorph** that would form under those conditions (Ice Ih, Ice Ic, Ice II, III, V, VI, VII, or VIII)
2. **Generates candidate structures** using GenIce2 with appropriate lattice parameters
3. **Ranks candidates** by energy estimate, density match, and structural diversity
4. **Constructs ice-water interfaces** — slab, pocket, or piece geometries (GUI only)
5. **Outputs PDB files** and **GROMACS-compatible input**

**Why QuickIce?**

Ice exhibits at least 19 different crystalline phases depending on temperature and pressure. QuickIce provides a quick way to:

- Generate initial structure candidates for molecular dynamics simulations
- Explore which ice polymorphs form under specific conditions
- Visualize the ice phase diagram with your conditions marked
- Produce starting structures for further refinement

**How it works:**

QuickIce uses:
- **IAPWS-95 validated melting curves** for high-confidence phase boundaries
- **IAPWS R10-06(2009)** for temperature-dependent Ice Ih density
- **Triple point data** for solid-solid phase transitions
- **GenIce2** for structure generation with proper hydrogen bonding networks
- **Knowledge-based ranking** based on lattice energy estimates and density matching

Water density for interface generation uses IAPWS-95 formulation for accuracy.

## Installation

### System Requirements

**Linux:**
- GLIBC 2.28 or higher (Ubuntu 20.04+, Debian 10+, Rocky/RHEL 8+)
- 64-bit architecture
- OpenGL support for 3D visualization

**Note:** The GUI requires Qt 6.10.2, which needs GLIBC 2.28+ on Linux. Older distributions (Ubuntu 18.04, Mint 19.1, CentOS 7) are not supported. 

### Prerequisites

- Conda (Miniconda or Anaconda)

### One-Time Setup

```bash
# Create conda environment (includes v4.0 GUI dependencies)
conda env create -f envronment.yml
```

### Setup Environment

```bash
# For each new shell - setup.sh activates conda and exports PYTHONPATH
source setup.sh
```

### Verify Installation

```bash
python quickice.py --help
```

### GUI Usage

QuickIce v4.0 includes an optional GUI application with ice-water interface construction. To launch:

```bash
python -m quickice.gui
```

For detailed GUI documentation, see [docs/gui-guide.md](docs/gui-guide.md).

![QuickIce v4.0 GUI — Ice Generation, Hydrate, Interface, and Ion tabs](docs/images/quickice-v4-gui.png)
*QuickIce GUI showing ice generation, hydrate configuration, interface construction, and ion insertion tabs*

For the usage of the binary distribution, see [README_bin.md](README_bin.md).

## Quick Start

### Basic Usage

Generate ice structures for 250K at 100 MPa with 128 water molecules:

```bash
python quickice.py --temperature 250 --pressure 100 --nmolecules 128
```

### Output

The tool will:

1. Identify the ice phase (e.g., Ice Ih at these conditions)
2. Generate 10 candidate structures
3. Rank them by combined score
4. Output PDB files to the `output/` directory
5. Generate a phase diagram PNG showing the input conditions

Example output:

**Standard mode**

See [sample_output/cli_ice](sample_output/cli_ice) for the command and files generated with this example (ice Ih at 273K and 1atm).

STDOUT: 
```
QuickIce - Ice structure generation

Temperature: 273.0K
Pressure: 0.1 MPa
Molecules: 216

Phase: Ice Ih (ice_ih)
Density: 0.9167 g/cm³

Generated 10 candidates
Note: Actual molecule count (432) differs from requested (216)
      This ensures valid crystal structure symmetry.

Ranked 10 candidates

Ranking scores (lower combined = better):
----------------------------------------------------------------------
Rank  Energy      Density     Diversity   Combined    
----------------------------------------------------------------------
1     0.0800      0.0008      1.0000      1.0000      
2     0.0802      0.0008      1.0000      1.0542      
3     0.0805      0.0008      1.0000      1.1317      
4     0.0810      0.0008      1.0000      1.2404      
5     0.0814      0.0008      1.0000      1.3481      
----------------------------------------------------------------------

Exported GROMACS files:
  - ice_ih_1.gro
  - ice_ih_2.gro
  - ice_ih_3.gro
  - ice_ih_4.gro
  - ice_ih_5.gro
  - ice_ih_6.gro
  - ... and 6 more
  Directory: sample_output/cli_ice

Output:
  PDB files: 10
  Directory: sample_output/cli_ice
    - ice_candidate_01.pdb
    - ice_candidate_02.pdb
    - ice_candidate_03.pdb
    - ... and 7 more
  Phase diagram: sample_output/cli_ice/phase_diagram.png

Validation:
  Valid structures: 10/10
```

**Interface mode**

See [sample_output/cli_interface](sample_output/cli_interface) for the command and files generated with this example (ice Ih at 273K and 1atm).

STDOUT: 
```
QuickIce - Ice structure generation

Temperature: 273.0K
Pressure: 0.1 MPa
Molecules: 216

Phase: Ice Ih (ice_ih)
Density: 0.9167 g/cm³


Starting slab interface generation...
  Box: 4.00 x 4.00 x 8.00 nm
  Seed: 42
  Ice thickness: 2.00 nm
  Water thickness: 4.00 nm

Generating ice candidate (ice_ih)...
  Generated 432 molecules

Assembling interface...
  Ice molecules: 3384
  Water molecules: 2535

==================================================
Generated slab interface structure
  Ice molecules: 3384
  Water molecules: 2535
  Total molecules: 5919
  Box: 4.70 x 4.42 x 9.43 nm

Periodicity adjustments (for continuous images):
  box_x: 4.000 → 4.699 nm (2 cells)
  box_y: 4.000 → 4.417 nm (2 cells)
  ice_thickness: 2.000 → 2.714 nm (1 cells)
  box_z: 8.000 → 9.428 nm (auto-adjusted)
==================================================

Interface generation complete.

Exported GROMACS files:
  - interface_ice_ih_slab.gro
  - interface_ice_ih_slab.top
  - tip4p_ice.itp
  Directory: sample_output/cli_interface
```

### CLI Options

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--temperature` | `-T` | Yes | Temperature in Kelvin (0-500K) |
| `--pressure` | `-P` | Yes | Pressure in MPa (0-10000 MPa) |
| `--nmolecules` | `-N` | Yes | Number of water molecules (4-100000) |
| `--output` | `-o` | No | Output directory (default: `output`) |
| `--gromacs` | `-g` | No | Export GROMACS format (.gro, .top, .itp) |
| `--candidate` | `-c` | No | Export specific candidate rank (with `-g`) |
| `--no-diagram` | | No | Disable phase diagram generation |
| `--version` | `-V` | No | Show version number |
| `--help` | `-h` | No | Show help message |

**Interface Generation:** Use `--interface` flag with `--mode`, `--box-x/y/z`, and mode-specific parameters. See [CLI Reference](docs/cli-reference.md) for details.

### More Examples

Generate Ice VII structures at high pressure:

```bash
python quickice.py -T 300 -P 2500 -N 256 -o ice_vii_output
```

Generate Ice Ic (cubic ice) at low temperature:

```bash
python quickice.py -T 150 -P 0.1 -N 100
```

Generate structures without phase diagram:

```bash
python quickice.py -T 200 -P 500 -N 128 --no-diagram
```

## Supported Ice Phases

QuickIce supports 8 ice polymorphs (those with GenIce2 lattice implementations):

| Phase | Name | Pressure Range | Temperature Range |
|-------|------|----------------|-------------------|
| Ice Ih | Hexagonal ice | 0 - ~200 MPa | 0-273K |
| Ice Ic | Cubic ice | Low pressure | < 150K |
| Ice II | Rhombohedral | ~200-600 MPa | < 250K |
| Ice III | Tetragonal | ~200-400 MPa | 250-260K |
| Ice V | Monoclinic | ~400-600 MPa | 250-270K |
| Ice VI | Tetragonal | ~600-2000 MPa | 250-350K |
| Ice VII | Cubic | > 2000 MPa | 273-350K |
| Ice VIII | Ordered VII | > 2000 MPa | < 273K |

**Note:** These are approximate ranges. Phase boundaries depend on both T and P simultaneously.

**Not supported:** Ice IX, Ice X, Ice XI, Ice XV, and liquid water (no GenIce2 lattices available).

All supported ice phases except Ice II work with interface construction. Ice II (rhombohedral) cannot form orthogonal supercells for interface generation. Ice V (monoclinic) is automatically transformed to orthogonal cells. Ice VI (tetragonal) and other orthogonal phases work natively.

## GROMACS Export

QuickIce can export ice structures as GROMACS input files for molecular dynamics simulations.

### Exported Files

When exporting with `--gromacs`:
- **`.gro` files** — One per candidate (coordinates differ): `ice_ih_1.gro`, `ice_ih_2.gro`, etc.
- **`.top` file** — Single file (topology identical for all): `ice_ih.top`
- **`.itp` file** — Single file (force field identical for all): `tip4p_ice.itp`

This avoids duplicate top/itp files since all candidates use the same TIP4P-ICE water model.

### CLI Usage

```bash
# Export all 10 candidates (10 .gro files + 1 .top + 1 .itp)
python quickice.py -T 250 -P 100 -N 128 --gromacs --output ice_gro

# Export specific ranked candidate (1 .gro + 1 .top + 1 .itp)
python quickice.py -T 250 -P 100 -N 128 --gromacs --candidate 2
```

The `--gromacs` flag enables GROMACS format output. Use `--candidate N` to select which ranked candidate to export (1-based, default: exports all candidates).

### GUI Usage

1. Generate structures normally (enter T, P, N and click Generate)
2. Menu → **File → Export for GROMACS** (Ctrl+G)
3. Select candidate from the dropdown (left viewport selection to choose the one exported for gromacs)
4. Files are saved to the output directory

### Interface GROMACS Export (Tab 3)

1. Generate ice candidates in Tab 1 first
2. Switch to Interface Construction tab (Tab 3)
3. Select mode (Slab/Pocket/Piece), configure parameters, click Generate Interface
4. **File → Export Interface for GROMACS** (Ctrl+I)

### Hydrate GROMACS Export (Tab 2)

1. Configure hydrate structure in Tab 2 (lattice, guest, occupancy)
2. Click Generate Hydrate
3. **File → Export Hydrate for GROMACS** (Ctrl+E)
4. Exported files include bundled guest molecule parameters (ch4.itp, thf.itp)

### Ion GROMACS Export (Tab 4)

1. Generate interface in Tab 3 first
2. Insert ions in Tab 4 (configure concentration, click Insert Ions)
3. **File → Export Ions for GROMACS** (Ctrl+J)
4. Exported files include Madrid2019 Na⁺/Cl⁻ parameters

### Guest Molecules: GAFF2

CH₄ (methane) and THF (tetrahydrofuran) guest molecules use GAFF2 force field parameters with RESP2(0.5) partial charges:

**GAFF2 Preparation Method:**

GAFF2 parameters were prepared using Sobtop 2026.1.16 and Multiwfn 3.8(dev) with RESP2 partial charges using default settings in the bundled RESP2.sh script.

**Multiwfn citations:**
- Tian Lu, Feiwu Chen, Multiwfn: A Multifunctional Wavefunction Analyzer, J. Comput. Chem. 33, 580-592 (2012) DOI: 10.1002/jcc.22885
- Tian Lu, A comprehensive electron wavefunction analysis toolbox for chemists, Multiwfn, J. Chem. Phys., 161, 082503 (2024) DOI: 10.1063/5.0216272

**Sobtop citation:**
- Tian Lu, Sobtop, Version 2026.1.16, http://sobereva.com/soft/Sobtop (accessed on 15 Apr 2026)

### Water Model: TIP4P-ICE

The TIP4P-ICE water model is optimized for ice simulations:

```
Abascal, J. L. F., Sanz, E., García Fernández, R., & Vega, C. (2005). 
A potential model for the study of ices and amorphous water: TIP4P/Ice. 
Journal of Chemical Physics, 122(23), 234511. 
DOI: https://doi.org/10.1063/1.1931662
```

Credit: itp file adapted from [sklogwiki](http://www.sklogwiki.org/SklogWiki/index.php/GROMACS_topology_file_for_the_TIP4P/Ice_model) and the [computational chemistry commune](http://bbs.keinsci.com/forum.php?mod=viewthread&tid=32973&page=1#pid222346)

### Molecule Count

The molecule count input specifies a **minimum** number of molecules. GenIce2 creates supercells to satisfy space group symmetry, so the actual count may be higher. For example, requesting 216 molecules might produce 432 (2× supercell) depending on the ice phase.

## Documentation

For more details, see:

- **[CLI Reference](docs/cli-reference.md)** - Complete command-line documentation
- **[GUI Guide](docs/gui-guide.md)** - QuickIce v4.0 graphical interface documentation
- **[Ranking Algorithm](docs/ranking.md)** - How candidates are scored and ranked
- **[Design Principles](docs/principles.md)** - Project architecture and decisions

## Known Issues

Key limitations:

- Ranking uses distance-based energy estimates, not actual force field calculations
- Some phase boundaries have limited experimental data
- High-pressure phases (> 30 GPa) have larger uncertainties
- **Only 8 ice phases supported** (Ih, Ic, II, III, V, VI, VII, VIII) — Ice IX, X, XI, XV and liquid water lack GenIce2 lattice implementations
- Only pure water ice is supported

## Project Structure

```
quickice/
├── quickice.py          # CLI entry point
├── quickice/            # Main package
│   ├── main.py          # Workflow orchestration
│   ├── cli/             # Command-line parsing
│   ├── gui/             # Graphical User Interface
│   ├── validation/      # Input validation
│   ├── phase_mapping/   # T,P → ice polymorph lookup
│   ├── structure_generation/  # GenIce2 integration
│   ├── ranking/         # Candidate scoring
├── sample_output/       # Sample CLI output directory
├── environment.yml      # Conda environment file
├── setup.sh             # Environment file to source in a new shell
└── README.md            # This file
```

## Testing

Run the test suite:

```bash
pytest
```

Run with verbose output:

```bash
pytest -v
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `iapws` | IAPWS-95 validated water/ice properties |
| `numpy` | Numerical operations |
| `scipy` | Scientific computing |
| `matplotlib` | Phase diagram visualization |
| `genice2` | Ice structure generation |
| `genice-core` | GenIce core algorithms |
| `pytest` | Testing framework |

## Reference

### GenIce2
- Repository: https://github.com/genice-dev/GenIce2
- Paper: "GenIce: Hydrogen-disordered ice structures by combinatorial generation", J. Comput. Chem. 2017
- DOI: https://doi.org/10.1002/jcc.25077

### IAPWS R14-08
- Document: "Revised Release on the Pressure along the Melting and Sublimation Curves of Ordinary Water Substance"
- URL: https://www.iapws.org/relguide/MeltSub.html

### spglib
- Repository: https://github.com/atztogo/spglib
- Paper: "Spglib: a software library for crystal symmetry search", Sci. Technol. Adv. Mater., Meth. 4, 2384822 (2024)
- DOI: https://doi.org/10.1080/27660400.2024.2384822

