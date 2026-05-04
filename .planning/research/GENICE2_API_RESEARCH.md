# GenIce2 API Complete Reference

**Research Date:** May 5, 2026  
**Version:** 2.2.13.1 (installed), 2.2.13.3 (PyPI latest)  
**GitHub:** https://github.com/vitroid/GenIce  
**Documentation:** https://vitroid.github.io/GenIce  
**License:** MIT

---

## Executive Summary

GenIce2 is a comprehensive Python library and command-line tool for generating hydrogen-disordered ice structures. It produces ice crystal configurations that obey the ice rules (each water molecule has exactly 4 hydrogen bonds, 2 donors and 2 acceptors) with guaranteed zero net dipole moment. The library supports 249+ ice lattice types, multiple water models, clathrate hydrates with guest molecules, and ion doping.

---

## Core API

### Main Entry Point: `GenIce` Class

**Location:** `genice2.genice.GenIce`

The primary class for generating ice structures.

```python
from genice2.genice import GenIce
from genice2.plugin import safe_import

# Load a lattice plugin
lat = safe_import("lattice", "1h").Lattice()

# Create GenIce instance
gi = GenIce(
    lat,                    # Lattice instance
    signature="",           # Optional signature text
    density=0.92,           # Target density (g/cm³)
    reshape=np.eye(3),      # Reshape matrix (3x3 integer array)
    cations={0: "Na"},      # Dict of {water_index: cation_name}
    anions={1: "Cl"},       # Dict of {water_index: anion_name}
    spot_guests={13: "me"}, # Dict of {cage_id: guest_name}
    spot_groups={13: "bu-:0"}, # Dict of {cage_id: group:root}
    asis=False,             # If True, don't shuffle orientations
    shift=(0.0, 0.0, 0.0),  # Fractional shift of origin
)

# Generate ice structure
result = gi.generate_ice(
    formatter=formatter,    # Format instance
    water=water,            # Water model instance
    guests={},              # Dict of {cage_type: {guest: fraction}}
    depol="strict",         # "strict", "optimal", or "none"
    noise=0.0,              # Position noise (percent of molecular diameter)
    assess_cages=False,     # Auto-detect cages
    target_polarization=(0.0, 0.0, 0.0),  # Target polarization vector
)
```

### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lat` | `Lattice` | Required | Ice lattice plugin instance |
| `signature` | `str` | `""` | Text inserted in output |
| `density` | `float` | 0 | Target density in g/cm³ (0 = use lattice default) |
| `reshape` | `np.ndarray` | `np.eye(3)` | 3x3 integer matrix for cell reshaping |
| `cations` | `dict` | `{}` | `{water_index: cation_name}` replacements |
| `anions` | `dict` | `{}` | `{water_index: anion_name}` replacements |
| `spot_guests` | `dict` | `{}` | `{cage_id: guest_name}` for specific cages |
| `spot_groups` | `dict` | `{}` | `{cage_id: "group:root"}` for semiclathrates |
| `asis` | `bool` | `False` | Skip HB orientation shuffling |
| `shift` | `tuple` | `(0,0,0)` | Fractional origin shift |

### `generate_ice()` Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `formatter` | `Format` | Required | Output format plugin |
| `water` | `Molecule` | `tip3p` | Water model plugin |
| `guests` | `dict` | `{}` | `{cage_type: {guest: fraction}}` |
| `depol` | `str` | `"strict"` | Depolarization mode |
| `noise` | `float` | `0.0` | Position noise (percent) |
| `assess_cages` | `bool` | `False` | Auto-detect cage positions |
| `target_polarization` | `tuple` | `(0,0,0)` | Target polarization vector |

---

## 7 Processing Stages

GenIce processes ice generation through 7 distinct stages. Format plugins can hook into any stage:

| Stage | Name | Description | Available Data |
|-------|------|-------------|----------------|
| 0 | Init | Before any processing | Lattice info |
| 1 | Replicate | Replicate unit cell | `reppositions`, `repcell`, `repcagetype`, `repcagepos`, `cagetypes` |
| 2 | Graph | Build random graph | `dopants`, `groups`, `filled_cages`, `graph` |
| 3 | Ice Rules | Apply ice rules | `digraph` (random orientation) |
| 4 | Depolarize | Minimize dipole | `digraph` (depolarized) |
| 5 | Orientations | Compute rotations | `rotmatrices` |
| 6 | Water Atoms | Place water atoms | `universe` (water molecules) |
| 7 | Guest Atoms | Place guest atoms | `universe` (all molecules) |

---

## Lattice Types (249 Total)

### Standard Ice Polymorphs

| Symbol | Aliases | Description |
|--------|---------|-------------|
| `1h` | `Ih`, `ice1h` | Hexagonal ice I (most common) |
| `1c` | `Ic`, `ice1c` | Cubic ice I |
| `2` | `II`, `ice2` | Hydrogen-ordered ice II |
| `2d` | `ice2d`, `ice2rect` | Hydrogen-disordered ice II |
| `3` | `III`, `ice3` | Ice III |
| `4` | `IV`, `ice4` | Ice IV |
| `4R` | | Orthogonalized ice IV |
| `5` | `V`, `ice5` | Monoclinic ice V |
| `5R` | | Ice V with orthogonal cell |
| `6` | `VI`, `ice6` | High-pressure ice VI |
| `6h` | | Half lattice of ice VI |
| `7` | `VII`, `ice7` | Ice VII |
| `8` | `VIII`, `ice8` | Hydrogen-ordered ice VII |
| `9` | `IX`, `ice9` | Hydrogen-ordered ice III |
| `11` | `XI`, `ice11` | Antiferroelectric ice XI |
| `11alt` | | Layered ferroelectric ice XI |
| `11i` | | 16 candidates for ice XI |
| `12` | `XII`, `ice12` | Metastable high-pressure ice XII |
| `13` | `XIII`, `ice13` | Hydrogen-ordered ice V |
| `14` | `ice14` | Partially hydrogen-ordered ice XII |
| `16` | `XVI`, `ice16`, `CS2`, `MTN`, `sII` | Ultralow-density ice XVI |
| `17` | `XVII`, `ice17` | Ultralow-density ice XVII |
| `0` | `ice0` | Metastable ice "0" |

### Clathrate Hydrates

| Symbol | Aliases | Description | Cage Types |
|--------|---------|-------------|------------|
| `CS1` | `sI`, `MEP`, `A15` | Structure I | 5¹², 5¹²6² |
| `CS2` | `sII`, `16`, `MTN`, `C15` | Structure II | 5¹², 5¹²6⁴ |
| `HS1` | `sIV` | Structure IV | 5¹², 5¹²6⁴ |
| `HS2` | `sV` | Structure V | |
| `HS3` | `sH`, `DOH` | Structure H | 5¹², 4³5⁶6³, 5¹²6⁸ |
| `TS1` | `sIII` | Structure III | |

### Hypothetical & Zeolitic Ices

| Symbol | Description |
|--------|-------------|
| `A`, `B` | Hypothetical ices A & B |
| `A15`, `BSV`, `ACO`, `DDR`, `EMT`, `FAU`, `IWV`, `LTA`, `MAR`, `NON`, `RHO`, `SGT`, `SOD` | Zeolitic ices |
| `Struct01` - `Struct84` | Space fullerene structures |
| `C14`, `C15`, `C36` | Frank-Kasper structures |
| `CRN1`, `CRN2`, `CRN3` | Continuous random networks |

### Filled Ices

| Symbol | Description |
|--------|-------------|
| `c0te` | Filled ice C0 (Teeratchanan) |
| `c1te` | Hydrogen hydrate C1 (Teeratchanan) |
| `c2te` | Filled ice C2 (Teeratchanan) |
| `ice1hte` | Filled ice Ih (Teeratchanan) |
| `sTprime` | Filled ice sT' |

### Special Structures

| Symbol | Description |
|--------|-------------|
| `one` | Ice I with stacking disorder |
| `bilayer` | Bilayer honeycomb ice |
| `2D3` | Trilayer honeycomb ice |
| `oprism` | Hydrogen-ordered ice nanotubes |
| `YKD` | Ice in d-surface |
| `xFAU` | Aeroice xFAU |
| `xdtc` | Porous ice with cylindrical channels |

### Loading External CIF Files

```python
# Via genice2-cif plugin
genice2 cif[structure.cif] -f gromacs > output.gro
genice2 zeolite[ITT] -f gromacs > output.gro  # From IZA database
```

---

## Output Formats (30+ Formats)

### Coordinate Formats

| Format | Aliases | Extension | Description |
|--------|---------|-----------|-------------|
| `gromacs` | `g` | `.gro` | GROMACS format (default) |
| `xyz` | | `.xyz` | XYZ coordinates |
| `exyz` | | `.xyz` | Extended XYZ (Open Babel) |
| `exyz2` | | `.xyz` | Extended XYZ (QUIP) |
| `cif` | | `.cif` | Crystallographic Information File |
| `cif2` | | `.cif` | Alternative CIF format |
| `mdview` | `m`, `mdv_au` | `.mdv` | MDView format |
| `towhee` | | `.coords` | TowHee format |
| `povray` | | `.pov` | POV-Ray scene |
| `exmol` | | | Extended XMol format |

### Orientation Formats

| Format | Aliases | Extension | Description |
|--------|---------|-----------|-------------|
| `euler` | `e` | `.nx3a` | Euler angles (3 values) |
| `quaternion` | `q` | `.nx4a` | Quaternions (4 values) |
| `com` | `c` | `.ar3a` | Center of mass positions |
| `rcom` | `r` | `.ar3r` | Relative center of mass |

### Graph Formats

| Format | Aliases | Extension | Description |
|--------|---------|-----------|-------------|
| `digraph` | `d` | `.ngph` | Directed HB graph |
| `graph` | | `.ngph` | Undirected HB graph |

### Visualization Formats

| Format | Aliases | Extension | Description |
|--------|---------|-----------|-------------|
| `yaplot` | `y` | `.yap` | Yaplot visualization |
| `rings` | | `.yap` | Ring visualization |
| `svg` | | `.svg` | SVG graphics (via plugin) |
| `png` | | `.png` | PNG graphics (via plugin) |

### Analysis Formats

| Format | Description |
|--------|-------------|
| `raw` | Python dict with internal data (for Jupyter) |
| `_ringstat` | Ring phase statistics |
| `_KG` | Kirkwood G(r) for long-range disorder |
| `_pol` | Polarization check |
| `_cage` | Cage detection and analysis (via plugin) |
| `_RDF` | Radial distribution functions (via plugin) |
| `twist` | Twist order parameter (via plugin) |

### Raw Format (Jupyter/Python API)

```python
from genice2.formats.raw import Format as RawFormat

formatter = RawFormat(stage=[1, 4, 5, 6])  # Select stages to capture
result = gi.generate_ice(formatter=formatter)

# Access internal data
positions = result["reppositions"]  # Fractional coordinates
cell = result["repcell"]            # Cell matrix
digraph = result["digraph"]         # HB network (nx.DiGraph)
rotmatrices = result["rotmatrices"] # Rotation matrices
mols = result["mols"]               # Molecule data
```

---

## Water Models

### Built-in Water Models

| Model | Aliases | Sites | Description |
|-------|---------|-------|-------------|
| `tip3p` | `3site` | 3 | Standard 3-site TIP3P |
| `tip4p` | `4site` | 4 | 4-site TIP4P (with M-site) |
| `tip5p` | `5site` | 5 | 5-site TIP5P (with L-sites) |
| `NvdE` | `6site` | 6 | Nada-van der Eerden 6-site |
| `7site` | | 7 | Seven-site model |
| `spce` | `ice` | 3 | SPC/E water |
| `physical_water` | | 1 | Physical model (O on lattice point) |

### Using Water Models

```python
# Via CLI
genice2 1h --water tip4p -o output.gro

# Via Python API
from genice2.plugin import safe_import
water = safe_import("molecule", "tip4p").Molecule()
```

---

## Guest Molecules (for Clathrates)

### Built-in Guest Molecules

| Symbol | Description |
|--------|-------------|
| `me` | United-atom methane |
| `ch4` | All-atom methane |
| `et` | United-atom ethane |
| `thf` | All-atom tetrahydrofuran |
| `uathf` | United-atom 5-site THF |
| `uathf6` | United-atom 6-site THF |
| `H2` | Hydrogen molecule |
| `co2` | Carbon dioxide |
| `empty` | Empty cage placeholder |
| `mol` | Loader for MOL files |

### Specifying Guests

```python
# Via CLI: -g cage_type=guest*occupancy+guest*occupancy
genice2 CS2 -g 16=uathf -g 12=co2*0.6+me*0.4 -o output.gro

# Via CLI: -G specific_cage_id=guest (for specific cages)
genice2 CS2 -G 13=me -G 15=co2 -o output.gro

# Via Python API
guests = {
    "16": {"uathf": 1.0},      # All 16-cages filled with THF
    "12": {"co2": 0.6, "me": 0.4}  # Mixed occupancy
}
```

---

## Ion Doping

### Adding Ions

```python
# Via CLI: -c water_index=cation, -a water_index=anion
genice2 CS2 -c 0=Na -a 1=Cl --depol=optimal -o output.gro

# Via Python API
gi = GenIce(
    lat,
    cations={0: "Na"},   # Replace water 0 with Na+
    anions={1: "Cl"},    # Replace water 1 with Cl-
)
```

**Important Notes:**
- Numbers of cations and anions must be equal (to satisfy ice rules)
- `--depol=optimal` is required when doping ions
- Currently only monatomic ions are supported

---

## Semiclathrate Hydrates (Experimental)

### Placing Functional Groups

```python
# -H cage_id=group:root_atom
genice2 HS1 -c 0=N -a 2=Br -H 0=Bu-:0 -H 9=Bu-:0 -H 2=Bu-:0 -H 7=Bu-:0 --depol=optimal
```

---

## genice-core Module

**Location:** `genice_core` (separate package)

The core algorithm for generating hydrogen bond networks that satisfy ice rules.

### Main Function: `ice_graph()`

```python
import genice_core
import networkx as nx

# Generate directed ice graph from undirected graph
digraph = genice_core.ice_graph(
    g,                              # nx.Graph or edge list
    vertex_positions=None,          # N x 3 array of positions
    is_periodic_boundary=False,     # PBC flag
    dipole_optimization_cycles=1000, # Depolarization iterations
    fixed_edges=nx.DiGraph(),       # Pre-oriented edges
    pairing_attempts=100,           # Max pairing attempts
    target_pol=np.array([0., 0., 0.]), # Target polarization
    return_edges=False,             # Return edge list vs DiGraph
    g_format=None,                  # "edges" or "adjacency"
)
```

### Other Core Functions

| Function | Description |
|----------|-------------|
| `noodlize()` | Convert graph to path decomposition |
| `noodlize_nx()` | NetworkX version of noodlize |
| `topology()` | Get graph topology |
| `topology_nx()` | NetworkX version of topology |
| `dipole()` | Calculate dipole moment |
| `force_polarize()` | Force specific polarization |
| `optimize()` | Optimize graph configuration |
| `split_into_simple_paths()` | Decompose into simple paths |
| `connect_matching_paths()` | Connect path segments |
| `arrays_to_directed_edges()` | Convert arrays to directed edges |

---

## Cell Module

**Location:** `genice2.cell`

### Cell Class

```python
from genice2.cell import Cell, cellvectors, cellshape

# Create cell from matrix
cell = Cell(np.array([[a1, a2, a3], [b1, b2, b3], [c1, c2, c3]]))

# Coordinate conversions
rel_coords = cell.abs2rel(abs_coords)  # Absolute to fractional
abs_coords = cell.rel2abs(rel_coords)  # Fractional to absolute

# Cell properties
vol = cell.volume()
cell.scale(1.1)  # Scale cell by factor
a, b, c, A, B, C = cell.shape()  # Get cell parameters

# Create cell vectors from parameters
mat = cellvectors(a=10, b=10, c=10, A=90, B=90, C=90)
```

---

## Cage Module

**Location:** `genice2.cage`

### Functions

```python
from genice2.cage import assess_cages, center_of_graph

# Auto-detect cages from HB network topology
cagepos, cagetypes = assess_cages(graph, node_positions)

# Calculate cage center
center = center_of_graph(subgraph, node_positions)
```

---

## Plugin System

### Plugin Categories

1. **Lattice plugins** (`genice2.lattices.*`) - Ice structures
2. **Format plugins** (`genice2.formats.*`) - Output formats
3. **Molecule plugins** (`genice2.molecules.*`) - Water/guest models
4. **Group plugins** (`genice2.groups.*`) - Functional groups
5. **Loader plugins** (`genice2.loaders.*`) - Input file formats

### Loading Plugins

```python
from genice2.plugin import safe_import, Lattice, Format, Molecule

# Method 1: Using safe_import
lat_module = safe_import("lattice", "1h")
lat = lat_module.Lattice()

# Method 2: Using convenience functions
lat = Lattice("1h")
formatter = Format("gromacs")
water = Molecule("tip4p")
```

### Plugin Search Order

1. **Local**: `./lattices/`, `./formats/`, `./molecules/` (current directory)
2. **System**: `genice2.lattices.*`, `genice2.formats.*`, `genice2.molecules.*`
3. **Extra**: Entry points in `genice2_lattice`, `genice2_format`, etc.

### Creating Custom Plugins

#### Custom Lattice Plugin

```python
# File: lattices/myice.py
import genice2.lattices
from genice2.cell import cellvectors

class Lattice(genice2.lattices.Lattice):
    def __init__(self):
        self.density = 0.92           # g/cm³
        self.bondlen = 0.3            # nm (HB threshold)
        self.cell = cellvectors(      # Cell vectors (nm)
            a=7.848, b=7.377, c=9.066
        )
        self.waters = """             # Water positions
        1.328 1.802 3.38
        5.267 4.524 1.109
        ...
        """
        self.coord = "absolute"       # or "relative"
        
        # Optional: specify HB pairs
        self.pairs = [(0,1), (1,2), ...]
        
        # Optional: specify cage positions
        self.cagepos = [[0.5, 0.5, 0.5], ...]
        self.cagetype = ["12", "16", ...]
```

#### Custom Format Plugin

```python
# File: formats/myformat.py
import genice2.formats
from genice2.decorators import banner, timeit

desc = {
    "brief": "My custom format",
    "usage": "No options available.",
}

class Format(genice2.formats.Format):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def hooks(self):
        # Return dict of {stage_number: hook_function}
        return {7: self.Hook7}
    
    @timeit
    @banner
    def Hook7(self, ice):
        # Access internal data
        positions = ice.reppositions
        cell = ice.repcell.mat
        mols = ice.universe
        
        # Build output
        self.output = "..."  # String or bytes
    
    def dump(self):
        return self.output
```

#### Custom Molecule Plugin

```python
# File: molecules/mymol.py
import genice2.molecules
import numpy as np

desc = {
    "brief": "My molecule model",
    "usage": "No options available.",
}

class Molecule(genice2.molecules.Molecule):
    def __init__(self):
        # Site positions relative to center of mass
        self.sites_ = np.array([
            [0.0, 0.0, 0.0],    # Site 1
            [0.1, 0.1, 0.0],    # Site 2
            ...
        ])
        # Shift to center of mass if needed
        self.sites_ -= np.mean(self.sites_, axis=0)
        
        # Atom labels
        self.labels_ = ["O", "H1", "H2", ...]
        
        # Molecule name (for residue name)
        self.name_ = "H2O"
```

---

## AnalIce: Analyzing Existing Structures

**Location:** `genice2.analice.AnalIce`

The `analice` tool analyzes existing coordinate files rather than generating new structures.

```python
from genice2.analice import AnalIce
from genice2.plugin import safe_import

# Load a structure from file
loader = safe_import("loader", "gro").Loader("structure.gro")

# Analyze
ai = AnalIce(loader)
result = ai.analyze_ice(
    water=water_model,
    formatter=formatter,
    noise=0.0,
)
```

---

## Utilities

### Rigid Body Operations (`genice2.rigid`)

```python
from genice2.rigid import (
    euler2quat, quat2euler,
    quat2rotmat, rotmat2quat,
    QfromE, EfromQ,
    QfromtRM, tRMfromQ,
    rand_rotation_matrix,
)

# Convert between representations
q = euler2quat([0.1, 0.2, 0.3])  # Euler to quaternion
e = quat2euler(q)                 # Quaternion to Euler
r = quat2rotmat(q)                # Quaternion to rotation matrix
q = rotmat2quat(r)                # Rotation matrix to quaternion

# Vectorized operations
quats = QfromE(euler_array)       # Array of quaternions
eulers = EfromQ(quats)            # Array of Euler angles
rotmats = tRMfromQ(quats)         # Array of rotation matrices

# Random rotation
r = rand_rotation_matrix(deflection=1.0)  # Random rotation matrix
```

### Value Parsing (`genice2.valueparser`)

```python
from genice2.valueparser import (
    parse_cages,
    parse_guest,
    parse_pairs,
    plugin_option_parser,
)

# Parse cage specification
cagepos, cagetypes = parse_cages("12 0.5 0.5 0.5\n16 0.25 0.25 0.25")

# Parse guest specification
guests = {}
parse_guest(guests, "16=uathf*0.8+me*0.2")

# Parse plugin options
name, kwargs = plugin_option_parser("myformat[opt1=val1:opt2]")
# Returns: ("myformat", {"opt1": "val1", "opt2": True})
```

---

## External Plugins

| Package | Description |
|---------|-------------|
| `genice2-cage` | Cage detection and vitrite analysis |
| `genice2-rdf` | Radial distribution functions |
| `genice2-svg` | SVG/PNG graphics output |
| `genice2-twist` | Twist order parameter |
| `genice2-mdanalysis` | MDAnalysis format integration |
| `genice2-cif` | CIF file input |

Install via pip:
```bash
pip install genice2-cage genice2-rdf genice2-svg genice2-mdanalysis genice2-cif
```

---

## Command Line Interface

### Basic Usage

```bash
# Generate ice Ih
genice2 1h > ice1h.gro

# Specify water model and repetitions
genice2 1h --water tip4p --rep 3 3 3 > ice1h.gro

# Generate clathrate with guests
genice2 CS2 -g 16=uathf -g 12=co2*0.5 > cs2.gro

# Dope with ions
genice2 CS2 -c 0=Na -a 1=Cl --depol=optimal > doped.gro

# Change density
genice2 6 --dens 1.00 > ice6_d1.00.gro

# Add noise
genice2 1h --add_noise 1.0 > ice1h_noisy.gro

# Set random seed
genice2 1h -s 12345 > ice1h_seed12345.gro

# Assess cages automatically
genice2 CS2 --assess_cages > cs2.gro

# Output in different formats
genice2 1h --format xyz > ice1h.xyz
genice2 1h --format cif > ice1h.cif
genice2 1h --format raw > ice1h.raw  # For Jupyter
```

### All CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--version` | `-V` | Show version |
| `--rep X Y Z` | `-r` | Repeat cell (default: 1 1 1) |
| `--reshape M` | `-R` | Reshape matrix (9 comma-separated integers) |
| `--shift X Y Z` | `-S` | Shift origin (default: 0 0 0) |
| `--dens D` | `-d` | Density in g/cm³ |
| `--add_noise P` | | Add noise (percent) |
| `--seed N` | `-s` | Random seed (default: 1000) |
| `--format F` | `-f` | Output format (default: gromacs) |
| `--water W` | `-w` | Water model (default: tip3p) |
| `--guest G` | `-g` | Guest specification |
| `--Guest G` | `-G` | Specific cage guest |
| `--Group G` | `-H` | Group specification |
| `--anion A` | `-a` | Anion doping |
| `--cation C` | `-c` | Cation doping |
| `--depol D` | | Depolarization (strict/optimal/none) |
| `--target_polarization X Y Z` | | Target polarization |
| `--asis` | | Skip HB shuffling |
| `--assess_cages` | `-A` | Auto-assess cages |
| `--debug` | `-D` | Debug mode |
| `--quiet` | `-q` | Suppress progress messages |

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `genice-core` | >=1.2,<1.3 | Core algorithm |
| `numpy` | >=2.0 | Numerical operations |
| `networkx` | >=2.0 | Graph operations |
| `pairlist` | >=0.6.4 | Pair detection |
| `cycless` | >=0.4.2 | Cycle detection |
| `graphstat` | >=0.3.3 | Graph statistics |
| `yaplotlib` | >=0.1.2 | Visualization |
| `openpyscad` | >=0.5.0 | OpenSCAD integration |
| `deprecation` | >=2.1.0 | Deprecation warnings |

---

## Version History

| Version | Date | Key Changes |
|---------|------|-------------|
| 2.2.13.3 | Mar 2026 | Latest PyPI release |
| 2.2.13.1 | - | Installed version |
| 2.2 | - | Core algorithm separated to genice-core |
| 2.1 | - | MDAnalysis integration |
| 2.0 | - | New ice rule algorithm (5x faster) |

---

## References

- **GitHub:** https://github.com/vitroid/GenIce
- **Documentation:** https://vitroid.github.io/GenIce
- **PyPI:** https://pypi.org/project/genice2/
- **Google Colab:** https://colab.research.google.com/github/vitroid/GenIce/blob/main/jupyter.ipynb
- **genice-core:** https://github.com/genice-dev/genice-core

---

## Summary

GenIce2 is a comprehensive, modular Python library for generating ice structures with:
- 249+ predefined ice lattice types
- Multiple water models (TIP3P, TIP4P, TIP5P, etc.)
- Clathrate hydrate support with guest molecules
- Ion doping capabilities
- 30+ output formats
- Extensible plugin architecture
- Integration with Jupyter/Google Colab via `raw` format
- Guaranteed zero dipole moment (ice rules satisfied)
- Fast algorithm (5x faster than GenIce1)
