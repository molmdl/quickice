# Features

**Analysis Date:** 2026-03-26

## Ice Structure Generation

**Core Capability:**
Generate hydrogen-disordered ice structures for various polymorphs with zero net dipole moment.

### Supported Ice Polymorphs

**Common Ice Phases:**
- `1h`, `Ih`, `ice1h` - Hexagonal ice I (most common)
- `1c`, `Ic`, `ice1c` - Cubic ice I
- `2`, `II`, `ice2` - Ice II (hydrogen-ordered)
- `3`, `III`, `ice3` - Ice III
- `4`, `IV`, `ice4` - Ice IV
- `5`, `V`, `ice5` - Ice V
- `6`, `VI`, `ice6` - Ice VI (high-pressure)
- `7`, `VII`, `ice7` - Ice VII (high-pressure)
- `8`, `VIII`, `ice8` - Ice VIII (ordered ice VII)
- `9`, `IX`, `ice9` - Ice IX
- `11`, `XI`, `ice11` - Ice XI
- `12`, `XII`, `ice12` - Ice XII
- `13`, `XIII`, `ice13` - Ice XIII
- `16`, `CS2`, `MTN`, `XVI`, `ice16`, `sII` - Ice XVI (clathrate)
- `17`, `XVII`, `ice17` - Ice XVII

**Clathrate Hydrates:**
- `CS1`, `MEP`, `sI` - Structure I clathrate
- `CS2`, `MTN`, `sII` - Structure II clathrate
- `DOH`, `HS3`, `sH` - Structure H clathrate
- `A15`, `Struct33` - A15 clathrate structure

**Hypothetical/Zeolitic Ices:**
- BSV, engel01-engel34 - Zeolitic ice structures
- Multiple PCOD structures
- Aeroice structures (xFAU)

**Special Structures:**
- `0`, `ice0` - Metastable ice "0"
- `CRN1`, `CRN2`, `CRN3` - Continuous random network
- `bilayer` - Bilayer honeycomb ice
- `oprism` - Hydrogen-ordered ice nanotubes

### Generation Algorithm

**Novel Approach (GenIce2):**
1. Build 4-connected undirected graph from nearest neighbors
2. Tile graph with cycles (always possible for 4-regular graphs)
3. Direct each cycle to satisfy ice rules
4. Choose orientations to minimize polarization
5. Place water molecule atoms according to orientations

**Key Features:**
- 5x faster than GenIce1
- Always produces zero net dipole (with `--depol strict`)
- Handles any 4-coordinated network

## Output Formats

### Atomic Coordinate Formats

**GROMACS (.gro):**
- Format: `g`, `gromacs`
- Output: Atomic positions with residue info
- Cell: Triclinic box specification
- Example: `genice2 1h -f gromacs > ice.gro`

**XYZ:**
- Format: `xyz`
- Output: Simple atomic coordinates (Angstrom)
- Example: `genice2 1h -f xyz > ice.xyz`

**Extended XYZ:**
- Format: `exyz`, `exyz2`
- Output: Extended XYZ with lattice info
- Two variants: Open Babel and QUIP formats

**CIF:**
- Format: `cif`, `cif2`
- Output: Crystallographic Information File
- Example: `genice2 1h -f cif > ice.cif`

**MDView:**
- Format: `m`, `mdview`, `mdv_au`
- Output: MDView format (nm or atomic units)

### Molecular Orientations

**Quaternions:**
- Format: `q`, `quaternion`
- Output: Rigid body orientations as quaternions
- File: `.nx4a`

**Euler Angles:**
- Format: `e`, `euler`
- Output: Rigid body orientations as Euler angles
- File: `.nx3a`

### Graph/Network Formats

**Directed Graph:**
- Format: `d`, `digraph`
- Output: Hydrogen bond directed graph
- File: `.ngph`

**Undirected Graph:**
- Format: `graph`
- Output: Hydrogen bond network as undirected graph
- File: `.ngph`

### Visualization Formats

**Yaplot:**
- Format: `y`, `yaplot`
- Output: Yaplot visualization with HB network
- File: `.yap`

**POVRay:**
- Format: `povray`
- Output: POV-Ray scene file
- File: `.pov`

**OpenSCAD:**
- Format: `openscad`
- Output: OpenSCAD 3D model
- File: `.scad`

### Analysis Formats

**Ring Statistics:**
- Format: `_ringstat`
- Output: Bond direction statistics

**Kirkwood G-factor:**
- Format: `_KG`
- Output: G(r) for checking long-range disorder

**Python/Raw:**
- Format: `p`, `python`, `raw`
- Output: Pickled data structure for further processing

## Water Models

### Built-in Models

**3-Site Models:**
- `tip3p`, `3site` - Standard TIP3P
- `spce` - SPC/E water model

**4-Site Models:**
- `tip4p`, `4site` - Standard TIP4P

**5-Site Models:**
- `tip5p`, `5site` - Standard TIP5P

**6-Site Models:**
- `NvdE` - Nada-van der Eerden model

**7-Site Models:**
- `7site` - Seven-site water model

**Special:**
- `physical_water` - Physical O positions on lattice points
- `ice` - Ice-specific configuration

## Guest Molecules

### Built-in Guests

**Small Molecules:**
- `me` - United-atom methane
- `ch4` - All-atom methane
- `et` - United-atom ethane
- `H2` - Hydrogen molecule
- `co2` - Carbon dioxide
- `thf` - All-atom tetrahydrofuran
- `uathf`, `uathf6` - United-atom THF variants

**Placeholder:**
- `empty` - Empty cage (for occupancy calculations)
- `one` - Single atom placeholder

**Custom Guests:**
- `mol[filename.mol]` - Load from MOL file (MolView.org format)

## Cell Operations

### Replication

**Simple Replication:**
```bash
genice2 --rep 3 3 3 1h > ice.gro
```
- Creates 3×3×3 supercell

**Reshape Matrix:**
```bash
genice2 --reshape 3,0,0,0,2,0,0,0,1 1h > ice.gro
```
- Custom cell transformation
- Equivalent to `--rep 3 2 1`

### Density Control

**Specify Density:**
```bash
genice2 --dens 0.95 1h > ice.gro
```
- Scales cell dimensions to achieve target density (g/cm³)

### Noise/Perturbation

**Add Thermal Noise:**
```bash
genice2 --add_noise 1 1h > ice.gro
```
- Adds Gaussian noise (1% of molecular diameter)

## Ion Doping

**Anions:**
```bash
genice2 -a 0=Cl -a 1=F CS1 > ice.gro
```
- Replaces water molecule at index 0 with Cl⁻

**Cations:**
```bash
genice2 -c 0=Na CS1 > ice.gro
```
- Replaces water molecule at index 0 with Na⁺

**Depolarization for Ions:**
```bash
genice2 --depol=optimal -c 0=Na -a 1=Cl CS1 > ice.gro
```
- Use `optimal` depolarization (strict fails with ions)

## Cage Occupancy

**Specify Guests in Cage Types:**
```bash
genice2 -g 12=co2*0.6+me*0.4 -g 14=co2 CS1 > ice.gro
```
- Cage type 12: 60% CO₂, 40% methane
- Cage type 14: 100% CO₂

**Specific Cage Occupancy:**
```bash
genice2 -G 0=me CS2 > ice.gro
```
- Place methane in cage index 0

**Group Placement:**
```bash
genice2 -H 0=Bu-:0 -H 9=Bu-:0 CS2 > ice.gro
```
- Place butyl groups attached to dopant at index 0

## Depolarization Modes

**Strict:**
- Default mode
- Ensures zero net dipole
- Fails if not possible

**Optimal:**
- Minimizes dipole
- Used for structures with defects/ions

**None:**
- No depolarization
- Random orientations

## Analysis Features

**Cage Assessment:**
```bash
genice2 --assess_cages CS1 > ice.gro
```
- Detects cages from network topology
- Classifies cage types

**Analice Tool:**
```bash
analice2 input.gro
```
- Analyzes existing ice structures
- Infers hydrogen bond network
- Validates ice rules

## External Plugins

**Available via pip:**
- `genice2-cage` - Cage detection and analysis
- `genice2-rdf` - Radial distribution functions
- `genice2-svg` - SVG visualization
- `genice2-twist` - Twist order parameter
- `genice2-mdanalysis` - MDAnalysis integration
- `genice2-cif` - CIF file input

**Custom Plugins:**
- Create `lattices/`, `formats/`, `molecules/` directories
- Add Python modules with appropriate classes

---

*Features analysis: 2026-03-26*