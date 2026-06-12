# Technology Stack: Complex Hydrate Generation

**Project:** QuickIce — Complex Hydrate Extension
**Researched:** 2026-06-12
**Updated:** 2026-06-12 (atomsk correction)

## ⚠️ CORRECTION (2026-06-12): Atomsk for Hydrate Assembly

Previous analysis stated "atomsk has zero hydrate/clathrate/ice-specific functionality" and recommended "Do NOT use atomsk." This was **incomplete** — atomsk's value for hydrate work is not in *generating* lattice structures (it can't), but in **assembling** polycrystalline hydrate systems from pre-generated building blocks. See [ATOMSK-HYDRATE-DEEPDIVE.md](./ATOMSK-HYDRATE-DEEPDIVE.md) for full analysis.

**Updated recommendation:** Atomsk is a viable **optional** external tool for polycrystalline hydrate assembly via `--polycrystal` mode (Voronoi tessellation from a monocrystalline seed). GPL-3.0 is manageable via subprocess invocation (same pattern as LAMMPS, Packmol). GenIce2 remains the primary structure generator; atomsk serves as a post-processing assembly tool. For simple stacking/merging, QuickIce's existing Python code is preferred (preserves GRO format, residue names, molecular connectivity).

**What changed:**
- Discovered 7+ hydrate-specific papers citing atomsk (Sveinsson & Cao 2025 explicitly uses ATOMSK for polycrystalline hydrate)
- `--polycrystal` mode provides Voronoi polycrystal generation that's ~200-300 LOC to replicate in Python
- `--merge` mode is less valuable (QuickIce already does stacking in Python)
- Confirmed atomsk does NOT support GRO format (adds pipeline friction)
- Confirmed `--polycrystal` uses a SINGLE seed (cannot mix sI+sII grains directly)

## Recommended Stack

### Core Tool for Complex Hydrates

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **GenIce2** | 2.2.13.3 | Primary hydrate/ice structure generation | Already installed, MIT license, **already supports filled ices (c0te, c1te, c2te, ice1hte, sTprime) and semiclathrates (HS1/HS2/HS3)**. Plugin system allows custom lattices and molecules. No other tool does hydrogen-disordering + depolarization for ice structures. |
| **genice2-cif** | 2.2.1 | Import arbitrary CIF files as ice structures | GenIce2 plugin; reads CIF files (including from IZA Zeolite DB) and converts them to hydrogen-disordered ice with proper ice rules. MIT-compatible. |
| **pymatgen** | 2026.5.4 | Structure manipulation, CIF I/O, symmetry analysis for structures outside GenIce2's catalog | MIT license, Python-native, excellent CIF reader, `Structure` class with spacegroup/symmetry operations, `Structure.from_spacegroup()` for building from space group + lattice params. Use when GenIce2 doesn't have the lattice. |
| **spglib** | 2.7.0 (installed) | Space group detection, cell refinement, symmetry operations | BSD-3-Clause (MIT-compatible). Already installed. Used by pymatgen internally. Provides `get_spacegroup()`, `refine_cell()`, `find_symmetry()`. |
| **Packmol** | 21.2.3 | Pack guest molecules into hydrate cages | MIT license, pip-installable (`pip install packmol`). Essential for placing guest molecules at specific positions inside cages when GenIce2's guest system isn't sufficient. |
| **atomsk** | Beta 0.13.1 | **Optional**: Voronoi polycrystalline hydrate assembly | GPL-3.0 (subprocess use is legally safe). `--polycrystal` mode creates polycrystalline hydrate from a GenIce2 seed — used in 7+ hydrate papers. Does NOT generate hydrate lattices. No GRO format support (use XYZ bridge). Single-grain-type only. See ATOMSK-HYDRATE-DEEPDIVE.md. |

### Supporting Libraries (Already Installed)

| Technology | Version | Purpose | When to Use |
|------------|---------|---------|-------------|
| **MDAnalysis** | 2.10.0 | Read/write many MD formats, structure manipulation | Use for I/O conversion (via `genice2-mdanalysis` integration) and post-processing of generated structures |
| **numpy** | 2.4.3 | Array operations for coordinate manipulation | Always — fundamental for all structure math |
| **scipy** | 1.17.1 | Optimization, interpolation, spatial algorithms | Use `scipy.spatial` for neighbor searches when building custom cage detection |
| **shapely** | 2.1.2 | 2D geometric operations | **Limited utility** — only 2D geometry, not suitable for 3D crystal structures. Use only for 2D projection visualization. |

### Alternative Tools Evaluated

| Technology | Version | Purpose | Why Not / When to Use |
|------------|---------|---------|----------------------|
| **atomsk** | Beta 0.13.1 | Crystal structure manipulation & format conversion | **NOT RECOMMENDED for generation; OPTIONAL for polycrystalline assembly.** GPL-3.0 license (see Licensing section), Fortran95 (no Python API). Cannot generate hydrate lattices, but `--polycrystal` mode creates Voronoi polycrystals from a hydrate seed — used in 7+ hydrate papers. See ATOMSK-HYDRATE-DEEPDIVE.md. |
| **ASE** | 3.28.0 | Structure building, I/O, analysis | **LGPL-2.1 license** — compatible with MIT for use but modifications must remain LGPL. Overlaps heavily with pymatgen. Use only if you need ASE-specific calculators (not relevant for structure generation). pymatgen is preferred for MIT purity. |
| **cif2ice** | (via genice2-cif) | Convert CIF → GenIce2 lattice plugin | Already bundled with `genice2-cif`; use as part of that plugin, not standalone. |

## Atomsk Analysis

### Capabilities

**Language & Build:** Fortran95 (NOT C as commonly assumed). Build via `make atomsk` in `src/`. Binary distribution available for Linux, Windows, macOS.

**Current version:** Beta 0.13.1 (released Dec 2023). Actively maintained; 16,500 downloads in 2025, 430+ citations.

**Lattice creation (`--create` mode):**

| Lattice | Lattice Params | Atom Species | Notes |
|---------|---------------|--------------|-------|
| sc | 1 (a) | 1 | Simple cubic |
| bcc / CsCl | 1 (a) | 1 or 2 | CsCl when 2 species |
| fcc | 1 (a) | 1 or 2 | Alloy when 2 species |
| L12 | 1 (a) | 2 | |
| fluorite | 1 (a) | 2 | |
| diamond / zincblende | 1 (a) | 1 or 2 | |
| rocksalt | 1 (a) | 2 | |
| perovskite | 1 (a) | 3 | |
| A15 | 1 (a) | 2 | |
| C15 Laves | 1 (a) | 2 | |
| hcp | 2 (a, c) | 1 or 2 | Orientable |
| wurtzite | 2 (a, c) | 2 | |
| graphite | 2 (a, c) | 1 or 2 | |
| BN / B12 | 2 (a, c) | 2 | |
| C14 Laves | 2 (a, c) | 2 | |
| C36 Laves | 2 (a, c) | 2 | |
| nanotube | 1 + (m,n) | 1 or 2 | Chiral indices |

**CRITICAL: No ice, hydrate, or clathrate lattice types.** Atomsk cannot create any ice polymorph, clathrate hydrate, or filled ice structure. This alone makes it unsuitable as a primary tool for QuickIce.

**Structure manipulation options:**
- `-duplicate` — supercell construction
- `-rotate` — rotation around axis
- `-deform` — uniaxial/shear strain
- `-cut` — remove atoms in region
- `-shift` — shift part of system
- `-mirror` — mirror transformation
- `-orient` — change crystallographic orientation (cubic/hex only)
- `-spacegroup` — apply space group symmetry operations
- `-substitute` — replace atoms by other atoms
- `-add-atom` — insert new atoms
- `-remove-atom` — remove specific atoms
- `-remove-doubles` — remove duplicate atoms
- `-wrap` — wrap atoms into box
- `-select` — select atoms by criterion
- `-merge` mode — merge two systems
- `-polycrystal` mode — Voronoi polycrystal
- Interactive mode — scriptable manipulation

**File format I/O (comprehensive):**

| Category | Formats (read → write) |
|----------|----------------------|
| Visualization | cfg (AtomEye), vesta, xsf (XCrySDen), dd (ddplot) |
| Ab initio | ABINIT, POSCAR/OUTCAR (VASP), pw/out (QE), CRYSTAL, fdf/xv (SIESTA), COORAT |
| Classical MD | lmp/lmc (LAMMPS), CONFIG (DL_POLY), gin (GULP), imd (XMD), bop/bx (BOPfox), mol (MOLDY) |
| Electron microscopy | cel (Dr Probe), jems, cfg (QSTEM) |
| General | **cif**, pdb, xyz/exyz, csv, dat, atsk (binary) |

**CIF support:** Can read CIF with space group info (applies symmetry automatically). Can write CIF with occupancy/charge data.

**Space group support:** `-spacegroup <group>` applies symmetry operations. Accepts number or Hermann-Mauguin symbol. Useful for expanding asymmetric unit → full unit cell.

### Licensing Constraints

**Atomsk license: GPL-3.0-or-later** (confirmed from official LICENSE file at https://raw.githubusercontent.com/pierrehirel/atomsk/master/LICENSE)

**What GPL-3.0 constrains for QuickIce (MIT):**

| Use Case | Legal? | Reasoning |
|----------|--------|-----------|
| Run atomsk via `subprocess.run()` | **YES** | Running a GPL program as a separate process does NOT create a derivative work. FSF and legal consensus agree: subprocess communication via pipes/files is "arm's length" interaction. |
| Process atomsk output files in MIT code | **YES** | GPL-3.0 Section 2: "The output from running a covered work is covered by this License only if the output, given its content, constitutes a covered work." Atomic coordinate data is NOT a derivative of atomsk's code. |
| Link atomsk into QuickIce | **NO** | Static or dynamic linking would make QuickIce a derivative work, requiring GPL compliance. |
| Copy/adapt atomsk source code | **NO** | Any code adaptation requires GPL compliance. |
| Distribute atomsk binary with QuickIce | **PROBLEMATIC** | Distributing GPL binary alongside MIT code in a single package could imply aggregation, but is legally gray. Best to require separate installation. |
| Import atomsk as Python module | **N/A** | No Python bindings exist. This is moot. |

**Precedent:** Many MIT-licensed projects call GPL tools via subprocess:
- GROMACS (LGPL) is called by MIT analysis tools
- VMD plugins call GPL external programs
- LAMMPS (GPL) is called via subprocess by many non-GPL tools

**Conclusion:** Using atomsk via subprocess is legally safe, but distributing it with QuickIce is problematic. The real question is: **why bother with the GPL complexity when better alternatives exist?**

### Integration Options

| Option | Feasibility | Recommendation |
|--------|-------------|----------------|
| **Subprocess call** | Technically feasible, legally OK | **Don't bother** — GenIce2 + pymatgen provide equivalent functionality with MIT license |
| **Python bindings** | **DO NOT EXIST** | No option |
| **Read atomsk output** | Feasible (CIF, XYZ, etc.) | Unnecessary — pymatgen reads these directly |
| **Interactive mode scripting** | Possible via stdin pipe | Overkill for QuickIce's needs |

## Environment-Compatible Alternatives

### GenIce2 Plugin System

**This is the most important finding.** GenIce2 already has extensive complex hydrate support that eliminates most need for atomsk.

**Filled ices (already built-in):**

| Code | Description | Reference |
|------|-------------|-----------|
| `c0te` | Filled ice C0 (H-disordered, guest positions supplied) | Teeratchanan 2015 |
| `c1te` | Hydrogen hydrate C1 (H-ordered, guest positions supplied) | Teeratchanan 2015 |
| `c2te` | Filled ice C2 / cubic ice (H-disordered, guest positions supplied) | Teeratchanan 2015 |
| `ice1hte` | Filled ice Ih (H-disordered, guest positions supplied) | Teeratchanan 2015 |
| `sTprime` | Filled ice sT' | Smirnov 2013 |

**Clathrate hydrates (already built-in):**

| Code | Jeffrey | Kosyakov | Zeolite | Description |
|------|---------|----------|---------|-------------|
| `CS1` / `sI` / `MEP` | sI | CS1 | MEP/A15 | Structure I clathrate |
| `CS2` / `sII` / `MTN` / `XVI` | sII | CS2 | MTN/C15 | Structure II clathrate |
| `HS3` / `sH` / `DOH` | sH | HS3 | DOH | Structure H clathrate |
| `HS1` / `sIV` | sIV | HS1 | — | Structure IV |
| `HS2` / `sV` | sV | HS2 | — | Structure V |
| `CS4` / `sVII` / `SOD` | sVII | CS4 | SOD | Structure VII |

**Semiclathrate hydrates (already built-in):**

| Code | Description | Guest/Ion Support |
|------|-------------|-----------------|
| `HS1` | Semiclathrate (sIV topology) | TBA, TBP, TBAB via `-c`, `-a`, `-H` options |
| `HS2` | Semiclathrate (sV topology) | Ion doping supported |

**GenIce2 semiclathrate workflow:**
```bash
# Place TBA ion in HS1 semiclathrate
genice2 HS1 -c 0=N -a 2=Br --depol=optimal > HS1.gro

# Add butyl groups in adjacent cages
genice2 HS1 -c 0=N -a 2=Br -H 0=Bu-:0 -H 9=Bu-:0 -H 2=Bu-:0 -H 7=Bu-:0 --depol=optimal > HS1_TBAB.gro
```

**Custom lattice plugin system:**
1. Create a folder named `lattices` in the working directory
2. Write a Python module defining the lattice (cell vectors, atom positions, bonding)
3. GenIce2 reads it as a plugin — applies ice rules, depolarization, hydrogen disorder
4. The `genice2-cif` plugin automates this from CIF files

**genice2-cif plugin** (pip install genice2-cif):
```bash
# Import any CIF file as an ice structure
genice2 "cif[my_hydrate.cif]" > my_hydrate.gro

# Import from IZA Zeolite Database
genice2 "zeolite[ITT]" > ITT.gro

# Specify which atom is the tetrahedral center (default: T or Si atoms)
genice2 "cif[ice.cif:O=O]" > ice.gro
```

**Custom molecule plugin:**
```python
# molecules/eo.py
import numpy as np
import genice2.molecules

class Molecule(genice2.molecules.Molecule):
    def __init__(self):
        # Define sites, atoms, labels
        self.sites = np.array([...])
        self.atoms_ = ["O", "C", "C"]
        self.labels_ = ["Oe", "Ce", "Ce"]
        self.name_ = "EO"
```

**What GenIce2 CANNOT do (gaps for complex hydrates):**
1. **Mixed-phase hydrates** — cannot create a single system with two different hydrate structures
2. **Heterogeneous interfaces** — cannot create ice/hydrate or hydrate/hydrate interfaces (but QuickIce already has interface code)
3. **Non-standard guest molecules in filled ices** — the built-in filled ices have fixed guest positions, customizing requires new lattice plugins
4. **Partially occupied cages with complex molecules** — the `-g` and `-G` options work well for simple guests but complex multi-atom guests in specific cages need custom molecule plugins

### MDAnalysis + spglib

**Feasibility:** MEDIUM-HIGH for structure building from CIF

**Approach:**
```python
# Read CIF → expand symmetry → manipulate
from pymatgen.core import Structure  # or use spglib directly
import spglib
import MDAnalysis as mda
import numpy as np

# spglib can:
# 1. Find space group from atomic positions
lattice = [[a, b, c], [alpha, beta, gamma]]
positions = [[0.0, 0.0, 0.0], ...]
numbers = [8, 1, 1]  # O, H, H
spg = spglib.get_spacegroup((lattice, positions, numbers))

# 2. Refine cell to conventional setting
refined = spglib.refine_cell((lattice, positions, numbers))

# 3. Find symmetry operations
symops = spglib.get_symmetry((lattice, positions, numbers))
```

**Limitation:** Neither MDAnalysis nor spglib alone can apply ice rules (Bernal-Fowler rules) or perform depolarization. This is GenIce2's unique capability. Use spglib for crystallographic operations, then pass the result to GenIce2 for hydrogen disordering.

### ASE (Atomic Simulation Environment)

**License:** LGPL-2.1 — **compatible with MIT for use, but modifications must remain LGPL**

**Version:** 3.28.0 (March 2026)

**Capabilities for hydrate structures:**
- `ase.spacegroup.crystal()` — build crystal from space group + lattice params + basis
- `ase.io.read()` / `ase.io.write()` — extensive format support (CIF, XYZ, POSCAR, etc.)
- `ase.build.bulk()` — common bulk crystal builder
- `ase.build.surface()` — surface slab creation
- `ase.build.stack()` — stack structures (useful for interfaces)
- `ase.build.make_supercell()` — supercell construction
- Atoms object — full manipulation (rotate, translate, repeat, etc.)

**Why NOT the primary choice:** LGPL license means if you modify ASE itself, those modifications must be LGPL. For pure use (import and call), this is fine. But pymatgen (MIT) provides equivalent structure manipulation with a cleaner license. **Use ASE only if you need ASE-specific calculators (not relevant for structure generation).**

### pymatgen (Python Materials Genomics)

**License:** MIT ✅ — **fully compatible with QuickIce**

**Version:** 2026.5.4, Python >=3.11

**Capabilities for hydrate structures:**
- `Structure.from_spacegroup(sg, lattice, species, coords)` — build from space group
- `Structure.from_file("hydrate.cif")` — read CIF
- `Structure.make_supercell()` — supercell construction
- `Structure.apply_symmetry_operations()` — symmetry expansion
- `SymmetrizedStructure` — symmetry-aware structure representation
- Extensive CIF I/O with space group support
- `Molecule` class for defining guest molecules
- `StructureMerger` for combining structures (experimental)

**Why pymatgen is the recommended alternative to atomsk:**
1. **MIT license** — no GPL complications
2. **Python-native** — integrates directly into QuickIce's Python codebase
3. **Superior CIF handling** — reads CIF with full symmetry operations, equivalent to atomsk's `-spacegroup` but in Python
4. **Space group builder** — `Structure.from_spacegroup()` does what atomsk's `--create` + `-spacegroup` does, but programmatically
5. **Structure manipulation** — all of atomsk's transform capabilities available via Python API
6. **Active ecosystem** — Materials Project integration, 430+ citations, monthly releases

**Example: Building a hydrate structure from space group with pymatgen:**
```python
from pymatgen.core import Structure, Lattice

# Build structure from space group + lattice params + basis
# This is equivalent to atomsk --create + -spacegroup
lattice = Lattice.from_parameters(a=11.8, b=11.8, c=11.8, alpha=90, beta=90, gamma=90)
structure = Structure.from_spacegroup(
    sg="Pm-3n",  # sI clathrate space group
    lattice=lattice,
    species=["O", "O", "O"],
    coords=[[0.0, 0.0, 0.0], [0.25, 0.5, 0.0], [0.183, 0.183, 0.183]]
)

# Make supercell
structure.make_supercell([2, 2, 2])

# Export to various formats
structure.to(filename="hydrate.cif")
structure.to(filename="hydrate.POSCAR")
```

### Packmol

**License:** MIT ✅

**Version:** 21.2.3, pip-installable (`pip install packmol`)

**Capabilities:**
- Pack molecules into defined spatial regions
- Constraint-based placement (inside box, inside sphere, outside sphere, etc.)
- Guarantees no steric clashes between molecules
- Input: PDB, TINKER, XYZ files

**Use case for complex hydrates:**
```bash
# Place guest molecules inside hydrate cages
# 1. Generate empty hydrate framework with GenIce2
genice2 CS2 -g 16=empty -g 12=empty --water tip4p > empty_cs2.gro

# 2. Convert to PDB for Packmol
# 3. Define Packmol input to place THF in large cages, methane in small cages
```

**Limitation:** Packmol doesn't know about cages — you must manually define spatial constraints (sphere/box coordinates) for each cage. This requires knowing cage center positions from the GenIce2 output. The `-G` (specific cage) option in GenIce2 is usually simpler.

## Recommendation

### Primary: Extend GenIce2 (not atomsk)

**Use GenIce2 as the core engine for complex hydrate generation.** It already supports:

1. **Filled ices:** c0te, c1te, c2te, ice1hte, sTprime — with guest positions
2. **Semiclathrates:** HS1, HS2, HS3 — with ion doping (TBA, Br, etc.)
3. **Standard clathrates:** sI, sII, sH, sIV, sV, sVII
4. **CIF import:** `genice2-cif` plugin reads any CIF file and generates H-disordered ice
5. **Custom lattice plugins:** Create new lattice types from crystallographic data
6. **Custom molecule plugins:** Define any guest molecule
7. **Ice rules + depolarization:** The unique value that no other tool provides

### Secondary: pymatgen + spglib for novel structures

When GenIce2 doesn't have a specific complex hydrate structure:

1. **Find the CIF file** from literature (CCDC, ICSD, or supplementary materials)
2. **Use pymatgen to read the CIF** and extract the crystallographic data
3. **Use spglib to verify/refine the symmetry** — ensure the space group and atomic positions are consistent
4. **Create a GenIce2 lattice plugin** from the CIF data — this is the cleanest path because GenIce2's lattice plugin format is simple Python
5. **OR use genice2-cif directly** — `genice2 "cif[structure.cif]"` handles the conversion automatically

### Tertiary: Packmol for complex guest placement

When GenIce2's guest molecule system (`-g`, `-G`, `-H`) isn't sufficient (e.g., large organic guests, mixed occupancy, constrained placement):

1. Generate the empty hydrate framework with GenIce2
2. Identify cage center positions (GenIce2 outputs cage IDs and types)
3. Use Packmol to place guest molecules at those positions with steric clash avoidance

### Do NOT use atomsk for structure generation; CONSIDER for polycrystalline assembly

**Rationale for rejecting atomsk as a PRIMARY tool:**

1. **Zero hydrate lattice generation capability** — atomsk creates fcc, bcc, hcp lattices. It has no concept of cages, guests, ice rules, or hydrogen disorder. **GenIce2 remains the primary structure generator.**
2. **GPL-3.0 license** — While subprocess use is technically legal, it creates distribution complexity and is philosophically incompatible with QuickIce's MIT license.
3. **No Python API** — Only subprocess integration, which means: format conversion overhead, no programmatic control, error handling is harder, debugging is harder.
4. **GenIce2 + pymatgen cover all useful atomsk features for structure generation:**
   - Lattice creation → GenIce2 (ice-specific) + pymatgen `Structure.from_spacegroup()`
   - CIF reading → pymatgen (better Python API) + genice2-cif
   - Symmetry operations → spglib (already installed) + pymatgen
   - Structure manipulation → pymatgen `Structure` + numpy
   - Format conversion → pymatgen I/O + MDAnalysis
   - Supercell construction → GenIce2 `--rep` + pymatgen `make_supercell()`
5. **Fortran95 codebase** — Can't extend or customize for hydrate-specific needs without GPL compliance.

**Rationale for considering atomsk as an OPTIONAL assembly tool:**

1. **`--polycrystal` mode creates Voronoi-tessellated polycrystals** — This is genuinely valuable and not easily replicated in Python (~200-300 LOC of geometry code). 7+ hydrate papers cite atomsk for this capability.
2. **`--merge` mode stacks structures** — But QuickIce's existing Python code already does this for GRO files (no format conversion needed), so atomsk's merge adds minimal value.
3. **GPL-3.0 via subprocess is legally safe** — Same pattern as calling LAMMPS, VMD, or Packmol.
4. **No GRO format support** — Requires XYZ or LAMMPS format conversion, adding pipeline complexity.
5. **Single grain type** — `--polycrystal` uses one seed for all grains; cannot create mixed sI+sII polycrystals directly.

**See ATOMSK-HYDRATE-DEEPDIVE.md for full analysis of atomsk's hydrate assembly capabilities.**

### Implementation Path

```
Phase 1: Leverage existing GenIce2 capabilities
├── Expose filled ice options (c0te, c1te, c2te, ice1hte, sTprime) in QuickIce GUI
├── Expose semiclathrate options (HS1 TBA/TBAB, HS2 TBP) in QuickIce GUI
├── Test genice2-cif plugin with known hydrate CIF files
└── Add guest molecule customization (new molecule plugins)

Phase 2: Add custom hydrate support via CIF
├── Integrate pymatgen for CIF reading (pip install pymatgen)
├── Build CIF → GenIce2 lattice plugin converter
├── Use spglib for symmetry verification of imported structures
└── Test with complex hydrate CIFs from literature

Phase 3: Advanced features
├── Packmol integration for complex guest placement
├── Mixed-phase hydrate systems (interface code already in QuickIce)
└── Custom lattice plugin authoring wizard in GUI
```

## Sources

| Source | URL | Confidence |
|--------|-----|------------|
| Atomsk official documentation | https://atomsk.univ-lille.fr/doc/en/ | HIGH |
| Atomsk GitHub repository | https://github.com/pierrehirel/atomsk/ | HIGH |
| Atomsk LICENSE file (GPL-3.0) | https://raw.githubusercontent.com/pierrehirel/atomsk/master/LICENSE | HIGH |
| Atomsk `--create` mode docs | https://atomsk.univ-lille.fr/doc/en/mode_create.html | HIGH |
| Atomsk file format support | https://atomsk.univ-lille.fr/doc/en/formats.html | HIGH |
| Atomsk spacegroup option | https://atomsk.univ-lille.fr/doc/en/option_spacegroup.html | HIGH |
| GenIce2 PyPI page | https://pypi.org/project/genice2/ | HIGH |
| GenIce GitHub repository | https://github.com/vitroid/GenIce | HIGH |
| genice2-cif plugin | https://github.com/vitroid/genice-cif | HIGH |
| ASE documentation | https://wiki.fysik.dtu.dk/ase/ | HIGH |
| ASE LICENSE file (LGPL-2.1) | https://gitlab.com/ase/ase/-/raw/master/LICENSE | HIGH |
| pymatgen PyPI page | https://pypi.org/project/pymatgen/ | HIGH |
| Packmol GitHub repository | https://github.com/m3g/packmol | HIGH |
| Packmol LICENSE file (MIT) | https://raw.githubusercontent.com/m3g/packmol/master/LICENSE | HIGH |
| GPL-3.0 full text | https://www.gnu.org/licenses/gpl-3.0.txt | HIGH |
| FSF on GPL and aggregated programs | https://www.gnu.org/licenses/gpl-faq.html#MereAggregation | MEDIUM |

## Appendix: Atomsk vs GenIce2 Capability Comparison

| Capability | Atomsk (GPL-3.0) | GenIce2 (MIT) | pymatgen (MIT) |
|-----------|------------------|----------------|-----------------|
| Ice/hydrate lattice creation | ❌ None | ✅ 100+ ice structures, clathrates, filled ices, semiclathrates | ⚠️ From CIF/spacegroup only |
| Hydrogen disordering | ❌ No concept of H-bonds | ✅ Ice rules + depolarization | ❌ No ice rule support |
| Clathrate cage filling | ❌ No cage concept | ✅ `-g`, `-G`, `-H` options with guest molecules | ❌ No cage concept |
| Semiclathrate ion doping | ❌ | ✅ `-c`, `-a` options | ❌ |
| CIF I/O | ✅ Read/write with space group | ✅ Via genice2-cif plugin | ✅ Best Python CIF support |
| Space group symmetry | ✅ `-spacegroup` option | ✅ Built into lattice plugins | ✅ `Structure.from_spacegroup()` |
| Custom lattice creation | ⚠️ Basic lattices only (fcc, bcc, etc.) | ✅ Python lattice plugins | ✅ From spacegroup params |
| Custom molecule definition | ❌ | ✅ Python molecule plugins | ✅ `Molecule` class |
| Format conversion | ✅ 30+ formats | ✅ Gromacs, CIF, XYZ, MDView, etc. | ✅ CIF, POSCAR, XYZ, etc. |
| Supercell construction | ✅ `-duplicate` | ✅ `--rep` | ✅ `make_supercell()` |
| Python API | ❌ Command-line only | ✅ Full Python API | ✅ Full Python API |
| License | GPL-3.0 | MIT | MIT |
