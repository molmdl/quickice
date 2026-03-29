# QuickIce

> **Experimental** - This is a "pure vibe coding project" created as a coding exercise. No physics simulations are performed. Results are plausible candidates, not validated structures.

Condition-based ice structure candidate generation from thermodynamic conditions (temperature and pressure).

## Overview

**What is QuickIce?**

QuickIce is a command-line tool that generates plausible ice crystal structure candidates for given thermodynamic conditions. Given a temperature (K) and pressure (MPa), it:

1. **Identifies the ice polymorph** that would form under those conditions (Ice Ih, Ice Ic, Ice II, III, V, VI, VII, VIII, IX, X, XI, XV, or Liquid)
2. **Generates candidate structures** using GenIce2 with appropriate lattice parameters
3. **Ranks candidates** by energy estimate, density match, and structural diversity
4. **Outputs PDB files** and a phase diagram visualization

**Why QuickIce?**

Ice exhibits at least 19 different crystalline phases depending on temperature and pressure. QuickIce provides a quick way to:

- Generate initial structure candidates for molecular dynamics simulations
- Explore which ice polymorphs form under specific conditions
- Visualize the ice phase diagram with your conditions marked
- Produce starting structures for further refinement

**How it works:**

QuickIce uses:
- **IAPWS-95 validated melting curves** for high-confidence phase boundaries
- **Triple point data** for solid-solid phase transitions
- **GenIce2** for structure generation with proper hydrogen bonding networks
- **Knowledge-based ranking** based on lattice energy estimates and density matching

## Installation

### Prerequisites

- Conda (Miniconda or Anaconda)

### One-Time Setup

```bash
# Create conda environment
conda env create -f env.yml
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

Terminal STDOUT:
```
QuickIce - Ice structure generation

Temperature: 273.0K
Pressure: 0.1 MPa
Molecules: 216

Phase: Ice Ih (ice_ih)
Density: 0.9167 g/cm³

Generated 10 candidates
Ranked 10 candidates

Ranking scores (lower combined = better):
----------------------------------------------------------------------
Rank  Energy      Density     Diversity   Combined    
----------------------------------------------------------------------
1     0.0898      0.0008      1.0000      1.0000      
2     0.0899      0.0008      1.0000      1.0353      
3     0.0900      0.0008      1.0000      1.0839      
4     0.0900      0.0008      1.0000      1.1040      
5     0.0901      0.0008      1.0000      1.1179      
----------------------------------------------------------------------

Output:
  PDB files: 10
  Directory: /tmp/sample_output
    - ice_candidate_01.pdb
    - ice_candidate_02.pdb
    - ice_candidate_03.pdb
    - ... and 7 more
  Phase diagram: sample_output/phase_diagram.png

Validation:
  Valid structures: 10/10
```

See [sample_output](sample_output) for files generated with this example (ice Ih at 273K and 1atm).
``

### CLI Options

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--temperature` | `-T` | Yes | Temperature in Kelvin (0-500K) |
| `--pressure` | `-P` | Yes | Pressure in MPa (0-10000 MPa) |
| `--nmolecules` | `-N` | Yes | Number of water molecules (4-100000) |
| `--output` | `-o` | No | Output directory (default: `output`) |
| `--no-diagram` | | No | Disable phase diagram generation |
| `--version` | `-V` | No | Show version number |
| `--help` | `-h` | No | Show help message |

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

QuickIce supports 12 ice polymorphs plus liquid water:

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
| Ice IX | Ordered III | ~200-400 MPa | < 140K |
| Ice X | Symmetric | > 30000 MPa | All T |
| Ice XI | Ordered Ih | Low pressure | < 72K |
| Ice XV | Ordered VI | ~1100 MPa | 80-108K |

**Note:** These are approximate ranges. Phase boundaries depend on both T and P simultaneously.

## Documentation

For more details, see:

- **[CLI Reference](docs/cli-reference.md)** - Complete command-line documentation
- **[Ranking Algorithm](docs/ranking.md)** - How candidates are scored and ranked
- **[Design Principles](docs/principles.md)** - Project architecture and decisions

## Known Issues

See [ISSUES.md](ISSUES.md) for known limitations and planned improvements.

Key limitations:

- Ranking uses distance-based energy estimates, not actual force field calculations
- Some phase boundaries have limited experimental data
- High-pressure phases (> 30 GPa) have larger uncertainties
- Generated structures require validation for production use

## Project Structure

```
quickice/
├── quickice.py          # CLI entry point
├── quickice/            # Main package
│   ├── main.py          # Workflow orchestration
│   ├── cli/             # Command-line parsing
│   ├── validation/      # Input validation
│   ├── phase_mapping/   # T,P → ice polymorph lookup
│   ├── structure_generation/  # GenIce2 integration
│   ├── ranking/         # Candidate scoring
│   └── output/          # PDB writing and diagrams
├── output/              # Default output directory
├── requirements-dev.txt # Development dependencies
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

