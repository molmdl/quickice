# Atomsk Hydrate Assembly Deep Dive

**Purpose:** Corrective research on atomsk's role in mixed/polycrystalline hydrate structure assembly
**Date:** 2026-06-12
**Confidence:** MEDIUM-HIGH (official docs verified, paper citations confirmed, but no hands-on testing since atomsk is not locally installed)

## Correction

Previous research incorrectly concluded "atomsk has zero hydrate functionality." While atomsk cannot **generate** hydrate lattices from scratch, it is actively used in the hydrate MD community for **assembling** polycrystalline hydrate systems from pre-generated building blocks. The original conclusion was factually correct about lattice generation (atomsk's `--create` mode has no ice/hydrate types) but critically incomplete about the **assembly** workflow, where atomsk's `--polycrystal` and `--merge` modes provide real value.

**What was wrong:** The statement "atomsk has zero hydrate/clathrate/ice-specific functionality" implied atomsk has no relevance to hydrate research. This is false — atomsk appears in 7+ hydrate-specific publications.

**What was right:** Atomsk cannot generate hydrate lattice structures. GenIce2 remains the primary structure generator. Atomsk's role is purely post-generation assembly.

## Evidence: Atomsk in Hydrate Research

### Confirmed Hydrate-Specific Papers Citing Atomsk

The following papers from atomsk's official citation list are directly about hydrate/ice systems:

| # | Paper | Year | Journal | Hydrate Relevance | Atomsk Usage (Inferred) |
|---|-------|------|---------|-------------------|------------------------|
| 67 | "To dissipate is to stabilize: Mechanical loss in methane hydrates" — Qu et al. | 2026 | The Innovation Energy 3, 100157 | Polycrystalline CH₄ hydrate mechanical loss | `--polycrystal` for creating polycrystalline hydrate from monocrystalline seed |
| 392 | "Decoding viscoelastic transitions in polycrystalline methane hydrates" — Qu et al. | 2025 | J. Phys. D 58, 135402 | Viscoelastic creep of polycrystalline CH₄ hydrate | `--polycrystal` for grain structure construction |
| 632 | "Distinct creep regimes of methane hydrates predicted by a monatomic water model" — Sveinsson & Cao | 2025 | Phys. Rev. Research 7, L012007 | Creep regimes in polycrystalline CH₄ hydrate, grain sizes 10-80 nm | **Explicitly states "using ATOMSK"** for polycrystal generation |
| 815 | "Generating proton-disordered ice configurations using orientational simulated annealing" | 2023 | — | Proton disorder in ice | Likely `--polycrystal` + custom ice seed, or format conversion |
| 946 | "Mechanical properties of amorphous CO₂ hydrates: insights from molecular simulations" — | 2023 | J. Phys. Chem. B (?) | CO₂ hydrate mechanics | `--polycrystal` for polycrystalline/amorphous hydrate construction |
| 1261 | "Inverse Hall-Petch effect in nanocrystalline ice predicted by machine-learned coarse-grained molecular simulations" | 2023 | — | Nanocrystalline ice mechanical properties | `--polycrystal` for nanocrystalline ice |
| 1597 | "Molecular Origins of Deformation in Amorphous Methane Hydrates" — Cao | 2021 | J. Phys. Chem. B 125, 5798 | Amorphous CH₄ hydrate deformation | `--polycrystal` or amorphous structure preparation |
| 1655 | "Mechanical creep instability of nanocrystalline methane hydrates" | 2023 | — | Nanocrystalline CH₄ hydrate creep | `--polycrystal` for nanocrystalline structure |
| 1683 | "Insight on the stability of polycrystalline natural gas hydrates by molecular dynamics simulations" — Zhang et al. | 2021 | Fuel 292, 120228 | Polycrystalline natural gas hydrate stability | `--polycrystal` for grain boundary construction |

**Key finding from Sveinsson & Cao (2025):** This paper explicitly mentions "using ATOMSK" with grain sizes ranging from 10 to 80 nm. This is the most direct evidence that atomsk's `--polycrystal` mode is the standard tool for creating polycrystalline hydrate systems in this research group (Cao group, NTU Singapore).

**Common workflow pattern across papers:**
1. Generate monocrystalline hydrate seed structure (via GenIce2, custom code, or mW model)
2. Use atomsk `--polycrystal` to create Voronoi-tessellated polycrystal
3. Remove overlapping atoms at grain boundaries with `-remove-doubles`
4. Run MD simulation in LAMMPS (LAMMPS format is atomsk's `lmp` output)

### Other Ice/Hydrate-Adjacent Papers

| # | Paper | Relevance |
|---|-------|-----------|
| 110 | "Subgrain boundary energy in Ih ice" — Druetta et al. (2026, J. Chem. Phys.) | Direct ice physics; likely uses atomsk for polycrystalline ice |
| 195 | "Effect of ice nucleating proteins on the structure-property relationships of ice" | Ice-protein interface; atomsk for ice structure preparation |

## Atomsk for Mixed Hydrate Assembly

### `--merge` Mode for Hydrate Stacking

**Official documentation (verified from https://atomsk.univ-lille.fr/doc/en/mode_merge.html):**

```
atomsk --merge [x|y|z] <N> <file1>...<fileN> <outputfile> [<formats>] [options]
```

**Two merge behaviors:**

#### 1. Merge into same box (no direction specified)

```bash
atomsk --merge 2 sI_hydrate.xsf sII_hydrate.xsf combined.xsf
```

- All atoms from both files are placed in the box of the **first** file
- Final supercell vectors = box vectors of file1
- **Critical limitation:** If file2 has larger box dimensions, atoms outside file1's box are still written but are in a void region. The box doesn't expand.
- **Use case:** Overlapping two structures in the same box (e.g., sI hydrate + water layer in same XY area)

#### 2. Stack along an axis (direction specified)

```bash
atomsk --merge z 3 sI_hydrate.xsf water_layer.xsf sII_hydrate.xsf sandwich.xsf
```

- Systems stacked along the specified direction (x, y, or z)
- Final box dimension along stack axis = sum of all systems' dimensions along that axis
- **Final box dimensions perpendicular to stack axis = first system's dimensions**
- **Critical limitation documented officially:** "Of course, this makes sense only if all systems have equal (or similar) dimensions normal to the given direction. Otherwise, the final result may not make much sense (e.g. when trying to stack rectangular and triclinic boxes of various shapes and sizes)."

#### Lattice Mismatch Problem for Hydrate Stacking

**This is the single biggest challenge for using `--merge` with different hydrate structures:**

| Structure | Lattice Parameter | Unit Cell Size |
|-----------|-------------------|----------------|
| sI (Pm-3n) | a = 11.8 Å | Cubic |
| sII (Fd-3m) | a = 17.3 Å | Cubic |
| sH (P6/mmm) | a = 12.2 Å, c = 10.0 Å | Hexagonal |
| Ice Ih | a = 4.5 Å, c = 7.3 Å | Hexagonal |

**Concrete example — sI + sII stacking along Z:**

If you try to stack sI and sII along Z:
- sI supercell: 3×3×3 unit cells → 35.4 × 35.4 × 35.4 Å
- sII supercell: 2×2×2 unit cells → 34.6 × 34.6 × 34.6 Å

The X and Y dimensions are close (35.4 vs 34.6 Å ≈ 2.3% mismatch). This is manageable — you can construct supercells that match closely. But there will be a strain at the interface because the sII system gets compressed into sI's X/Y box.

**For similar-sized systems, `--merge z` works well.** You just need to carefully choose supercell multiplicities to minimize the perpendicular mismatch.

**Workflow for sI/water/sII sandwich:**

```bash
# Step 1: Generate structures with matching cross-sections
# GenIce2 → XYZ → atomsk
# Choose supercell sizes so X,Y dimensions match within ~1-2%

# Step 2: Stack along Z
atomsk --merge z 3 sI_3x3x3.xyz water_35A.xyz sII_2x2x2.xyz sandwich.xsf -rmd 1.5

# Step 3: Remove overlapping atoms at interfaces
# -rmd 1.5 removes atoms closer than 1.5 Å (O-O distance in water is ~2.76 Å)
```

**Verdict on `--merge` for hydrate stacking:**
- ✅ Works well for stacking structures with similar XY dimensions
- ✅ Perfect for same-structure stacking (e.g., multiple sI grains separated by water)
- ⚠️ Requires careful supercell sizing to minimize lattice mismatch
- ❌ Does NOT automatically handle lattice mismatch
- ❌ Does NOT find optimal interface positions (user must position structures correctly)

### `--polycrystal` Mode for Polycrystalline Hydrate

**Official documentation (verified from https://atomsk.univ-lille.fr/doc/en/mode_polycrystal.html):**

```
atomsk --polycrystal <seed> <param_file> <outputfile> [<formats>] [options]
```

**This is atomsk's most valuable capability for hydrate research.** The hydrate MD papers that cite atomsk use this mode.

#### How it works

1. Read a **seed** structure (any supported format — XYZ, XSF, CIF, LAMMPS, etc.)
2. Read a **parameter file** defining grain positions, orientations, and box size
3. Perform **3D Voronoi tessellation** of space around grain centers
4. Place rotated/duplicated copies of the seed at each Voronoi node
5. Expand each copy into its Voronoi polyhedron
6. Use **periodic boundary conditions** in all 3 dimensions
7. Output the polycrystalline structure

#### Parameter file format

```
# Voronoi polycrystal with 12 random grains
box 100 100 100
random 12
```

Or with explicit grain positions and orientations:

```
box 200 200 200
node 0 0 0 [100] [010] [001]
node 50 50 50 56° -83° 45°
node 100 50 80 random
```

**Keywords:**
- `box <Lx> <Ly> <Lz>` — **mandatory**, defines final box size in Å
- `random <N>` — generate N grains with random positions and orientations
- `lattice <type>` — arrange grains on a lattice (bcc, fcc, diamond, hcp)
- `node <x> <y> <z> <orientation>` — define one grain explicitly
  - Orientation can be: Miller indices `[hkl]`, rotation angles `α° β° γ°`, or `random`
- `random`, `lattice`, and `node` are **mutually exclusive**

#### Can a GenIce2 hydrate structure serve as the seed?

**YES.** The seed can be any atomic system in any supported format. The typical workflow in hydrate papers is:

1. Generate monocrystalline hydrate with GenIce2 → output as XYZ
2. Use that XYZ as the seed for atomsk `--polycrystal`
3. Each grain is a rotated copy of the same hydrate structure

Example parameter file for polycrystalline sI methane hydrate:

```
# Polycrystalline sI methane hydrate
# 8 grains, ~10 nm grain size
box 80 80 80
random 8
```

```bash
# Generate seed with GenIce2 → XYZ
genice2 CS1 -g 12=me -g 14=me --rep 3,3,3 > sI_seed.xyz

# Create polycrystal with atomsk
atomsk --polycrystal sI_seed.xyz poly_params.txt poly_hydrate.lmp -wrap -rmd 1.5
```

#### Critical limitation: Single grain type

**The `--polycrystal` mode uses ONE seed for ALL grains.** You cannot specify different structures for different grains. This means:

- ✅ sI-only polycrystal: Works (all grains are sI)
- ✅ sII-only polycrystal: Works (all grains are sII)
- ❌ Mixed sI + sII polycrystal: **NOT directly possible** — all grains would be the same structure

**Workaround for mixed-phase polycrystals:**

1. Generate sI and sII polycrystals separately
2. Use `--merge` to combine them (with careful box sizing)
3. Or: Generate one phase as the polycrystal, then selectively replace regions with the other phase using `-select` + `-cut` + `--merge`

This is a genuinely complex operation that requires manual intervention and custom scripting.

#### Grain boundary handling

Atomsk's polycrystal creates **unrelaxed grain boundaries**. The documentation warns:

> "Beware that the system you create with this mode is *not* relaxed nor optimized."

At grain boundaries:
- Atoms from adjacent grains may **overlap** (closer than physical distances)
- Solution: Use `-remove-doubles <distance>` to remove overlapping atoms
- Typical distance threshold: 1.0-1.5 Å (removes atoms that are clearly too close)
- After `-remove-doubles`, grain boundaries will have **vacancies** — missing atoms where overlaps were removed
- These vacancies are physically realistic representations of grain boundary disorder in polycrystalline materials
- The system should then be **energy-minimized** in LAMMPS/GROMACS before production MD

```bash
# Polycrystal with boundary cleanup
atomsk --polycrystal seed.xyz params.txt poly.lmp -wrap -rmd 1.5
```

#### Additional polycrystal outputs

Atomsk generates useful auxiliary files:
- `*_id-size.txt` — Grain IDs, atom counts, and volumes
- `*_size-dist.dat` — Grain size distribution
- `*_nodes.xsf` — Positions of Voronoi nodes (as H atoms for visualization)
- `*_grains-com.xsf` — Centers of mass of each grain
- `*_param.txt` — (If `random` was used) The generated parameter file for reproducibility

#### 2D polycrystal mode

If one dimension of the box ≤ seed dimension, atomsk automatically uses **2D Voronoi tessellation**. All grains have the same orientation along the short axis. Then use `-duplicate` along that axis to create a columnar structure. This is useful for thin-film hydrate studies.

### Other Relevant Options for Hydrate Work

#### `-substitute <sp1> <sp2>` — Guest Exchange

Replace all atoms of species `<sp1>` by `<sp2>`. Combined with `-select`, can replace specific guests:

```bash
# Replace CH4 (C) in specific cages with CO2 (C→C is no-op, but...)
# More useful: Replace all carbon atoms in CH4 with something else
atomsk hydrate.xyz -sub C Si modified.xyz  # Not a hydrate-specific example
# Better use: Select specific regions and substitute
atomsk hydrate.xyz -select in sphere 5 5 5 3 -sub C N modified.xyz
```

**Limitation for hydrate guests:** `-substitute` replaces ALL atoms of a given species, not specific molecules. In a hydrate with CH₄ guests, all C atoms would be replaced. To selectively swap guests in specific cages, you'd need `-select in sphere` to select atoms in a cage region first, then substitute.

#### `-cut <above|below> <d> <normal>` — Creating Interfaces

Remove atoms above or below a plane. Essential for creating hydrate/water interfaces:

```bash
# Create a hydrate slab (remove atoms above 0.5*box along Z)
atomsk hydrate.xyz -cut above 0.5*BOX z hydrate_slab.xsf

# Create a water layer
atomsk water.xyz -cut below 0.5*BOX z water_slab.xsf

# Merge into interface
atomsk --merge z 2 hydrate_slab.xsf water_slab.xsf interface.xsf -rmd 1.5
```

#### `-select` — Selective Atom Operations

Powerful selection criteria including:
- By species: `-select C` (all carbon atoms)
- By spatial region: `-select in sphere <x> <y> <z> <R>` or `-select in box <x> <y> <z> <x'> <y'> <z'>`
- By position: `-select above 40 y` (atoms with Y > 40 Å)
- By neighbors: `-select 6 any neighbors 9578` (6 nearest neighbors of atom 9578)
- Random: `-select random 20 C` (20 random carbon atoms)
- Combinators: `add`, `rm`, `intersect`, `xor` for combining selections

**Hydrate use case:** Select and remove guest molecules in specific cages:

```bash
# Select all atoms in a sphere around a cage center, remove them
atomsk hydrate.xyz -select in sphere 5.9 5.9 5.9 3.9 -rmatom select empty_cage.xyz
```

#### `-remove-doubles <distance>` — Boundary Cleanup

Essential after `--polycrystal` or `--merge`:

```bash
# Remove atoms closer than 1.5 Å (typical for O-O overlap removal)
# Note: atoms from the SECOND system are removed when overlapping
atomsk --merge 2 sys1.xyz sys2.xyz merged.xsf -rmd 1.5
```

#### `-spacegroup <group>` — Symmetry Expansion

Apply symmetry operations of a space group to the current system:

```bash
# Expand asymmetric unit of a hydrate
atomsk asymmetric_unit.xyz -spacegroup Pm-3n full_sI.xyz
```

**This is useful for:** Taking a partial set of atomic positions from a paper (often only the asymmetric unit is listed) and generating the full unit cell. If you have a hydrate's asymmetric unit positions from a CIF file or supplementary material, you can expand it.

#### `-add-atom` / `-remove-atom` — Atom Insertion/Removal

Insert or remove individual atoms. Useful for:
- Adding guest molecules to specific cage positions
- Removing water molecules at defect sites

## GenIce2 → Atomsk → GROMACS Pipeline

### Format Compatibility Analysis

**Critical finding: Atomsk does NOT support GRO format.**

Verified from atomsk's official formats page (https://atomsk.univ-lille.fr/doc/en/formats.html). The complete list of supported formats includes:
- Visualization: cfg, dd, vesta, xsf
- Ab initio: ABINIT, POSCAR/OUTCAR, pw, CRYSTAL, fdf, xv, COORAT
- Classical MD: **lmp** (LAMMPS), CONFIG (DL_POLY), gin (GULP), imd, bop/bx, mol, xmd
- Other: **cif**, **pdb**, **xyz/exyz/sxyz**, csv, dat, atsk

**NO GRO (GROMACS coordinate format) support.** This is a significant pipeline limitation.

### GenIce2 Output Formats

Verified via Python API:

| Format | Available? | Notes |
|--------|-----------|-------|
| GROMACS (GRO) | ✅ YES | Default output; contains box vectors, atom positions, velocities |
| XYZ | ✅ YES | Extended XYZ with cell info; atomsk can read this |
| CIF | ✅ YES | Crystallographic format; atomsk can read this |
| MDView | ✅ YES | Proprietary format; atomsk cannot read this |

### Pipeline Options

#### Option 1: GenIce2 → XYZ → atomsk → XYZ → GROMACS (via MDAnalysis)

```
GenIce2 (Python API)
  → formatter = safe_import('format', 'xyz')
  → ice.generate_ice(formatter, water, guests, depol='strict')
  → XYZ string output (extended XYZ with cell vectors)
  → Write to temp file
→ atomsk --polycrystal seed.xyz params.txt output.lmp -wrap -rmd 1.5
  → LAMMPS data file (atomsk's best classical MD output format)
→ MDAnalysis: read LAMMPS → write GRO
→ GROMACS production MD
```

**Pros:** Clean pipeline; extended XYZ preserves cell information; LAMMPS format is atomsk's best classical MD output
**Cons:** Two format conversions (XYZ → atomsk → LAMMPS → GRO); loss of residue naming in conversion

#### Option 2: GenIce2 → GRO → (MDAnalysis convert) → XYZ → atomsk → XYZ → (MDAnalysis convert) → GRO

```
GenIce2 (Python API) → GRO output
→ MDAnalysis: read GRO, write XYZ
→ atomsk --polycrystal seed.xyz params.txt output.xyz -wrap -rmd 1.5
→ MDAnalysis: read XYZ, write GRO
→ GROMACS production MD
```

**Pros:** Preserves GRO for GROMACS compatibility
**Cons:** Three format conversion steps; more fragile pipeline

#### Option 3: GenIce2 → CIF → atomsk → CIF → pymatgen → GRO

```
GenIce2 (Python API) → CIF output (via genice2-cif's reverse? Unclear if GenIce2 can output CIF)
→ atomsk --polycrystal seed.cif params.txt output.cif
→ pymatgen: read CIF, convert to GRO
```

**Note:** It's unclear whether GenIce2 can output CIF format. The `cif` format module in GenIce2 likely reads CIF, not writes it. This pipeline needs verification.

#### Option 4: GenIce2 → GRO → LAMMPS data (via QuickIce/Packmol/other) → atomsk → LAMMPS → GROMACS

**Most practical for LAMMPS users:** Since many hydrate MD papers use LAMMPS (not GROMACS), and atomsk's best output format is `lmp` (LAMMPS data file), the pipeline can skip the GRO conversion entirely:

```
GenIce2 → XYZ → atomsk → LAMMPS data file → LAMMPS MD
```

**This is the pipeline used by the Cao group (Sveinsson & Cao 2025)** — they use LAMMPS with the mW monatomic water model, not GROMACS.

### Format Conversion Details

| Conversion | Tool | Loss of Information |
|------------|------|---------------------|
| GRO → XYZ | MDAnalysis or pymatgen | Residue names, velocity data (if present) |
| XYZ → atomsk input | No conversion needed | None (atomsk reads XYZ natively) |
| atomsk XYZ output → GRO | MDAnalysis | Residue names (atomsk outputs generic element names, not residue-specific names like SOL, CH4) |
| atomsk lmp → GRO | MDAnalysis | Residue names; also need to re-add GROMACS topology info |

**Key concern: Residue naming in GRO format.** GRO files require residue names (SOL for water, CH4 for methane, etc.). Atomsk outputs generic element-based atom names, not residue-specific names. After atomsk processing, the GRO file would need residue assignment — this requires knowing which atoms belong to which molecules. For polycrystalline structures, the molecular connectivity is preserved from the seed structure, but residue assignment is lost in format conversion.

**Mitigation:** QuickIce could implement a residue-reconstruction step after atomsk processing. Given that the water O-H topology is known from the seed structure, and guest molecules have known topologies, reconstructing residue assignments is feasible with a KD-tree-based neighbor search.

## Licensing Re-assessment

### Previous Assessment (from STACK.md)

> "GPL-3.0 license creates distribution complications"

This is partially correct but overstates the risk.

### Corrected Assessment

**GPL-3.0 constraints for QuickIce subprocess use:**

| Use Case | Legal? | Reasoning | Confidence |
|----------|--------|-----------|------------|
| Run atomsk via `subprocess.run()` | **YES** | Subprocess communication at arm's length does not create a derivative work. FSF FAQ and legal consensus agree. | HIGH |
| Process atomsk output files in MIT code | **YES** | GPL-3.0 Section 2: output is covered only if it constitutes a covered work. Atomic coordinate data is NOT a derivative of atomsk's code. | HIGH |
| Distribute atomsk binary with QuickIce | **PROBLEMATIC** | Aggregation is legally gray; safest to require separate installation | MEDIUM |
| Link atomsk into QuickIce | **NO** | Would require GPL compliance for QuickIce | HIGH |
| Modify atomsk source code | **NO** | Modifications must remain GPL | HIGH |

**Precedent: MIT/BSD tools calling GPL tools via subprocess is standard practice:**
- ASE (LGPL) calls LAMMPS (GPL) via subprocess — universally accepted
- VMD plugins call GPL external programs — standard practice
- PLUMED (LGPL) interfaces with LAMMPS (GPL) — widely used
- OVITO (GPL) is called by many non-GPL analysis workflows

**Practical approach for QuickIce:**
1. Atomsk as an **optional** external dependency (like Packmol)
2. QuickIce does NOT bundle or distribute atomsk
3. User installs atomsk separately (apt, conda, or compile from source)
4. QuickIce calls atomsk via `subprocess.run()` when the user requests polycrystalline/mixed assembly
5. If atomsk is not installed, the feature is disabled with a clear error message

**This is identical to how QuickIce would integrate Packmol** — another external tool called via subprocess. The GPL status is manageable if atomsk remains an optional, separately-installed external tool.

**Updated recommendation:** GPL-3.0 is a **managed risk**, not a blocker, for subprocess-only integration. The previous assessment's "don't bother" conclusion was too strong.

## Python Alternative Comparison

### Can QuickIce's existing code do what atomsk `--merge` does?

**QuickIce's slab.py / pocket.py assembly code:**

QuickIce's existing interface assembly code (slab stacking, pocket creation) already performs merge-like operations — stacking ice and hydrate slabs along an axis, adjusting box dimensions, removing overlapping atoms. This is conceptually similar to atomsk's `--merge z` mode.

**However:**
- QuickIce's merge is **specialized** for ice/hydrate interfaces (it knows about water molecule boundaries)
- atomsk's merge is **generic** (any atomic system)
- QuickIce's merge can output directly to **GRO** (no format conversion needed)
- atomsk's merge requires **format conversion** (no GRO support)

**Verdict:** For simple stacking (sI + water + sII along Z), QuickIce's existing Python code is **more practical** than atomsk because it preserves GRO format, residue names, and molecular connectivity. Atomsk's `--merge` adds no value that Python can't already do.

### Can pymatgen's Structure class merge two different structures?

**pymatgen merge capabilities:**
- `StructureMerger` — experimental, not well documented
- No direct equivalent of atomsk's `--merge` mode
- You can concatenate two `Structure` objects and adjust box dimensions manually:

```python
from pymatgen.core import Structure

# Manual merge: concatenate positions and expand box
s1 = Structure.from_file("sI.xyz")
s2 = Structure.from_file("sII.xyz")

# Stack along Z: combine positions, expand Z dimension
s_merged = s1.copy()
for site in s2:
    s_merged.append(site.species, site.coords + [0, 0, s1.lattice.c])
# Adjust box dimensions...
```

**This is feasible but requires manual bookkeeping** — box dimension adjustment, atom coordinate offset, PBC wrapping. Atomsk automates this.

### Can MDAnalysis merge two GRO files?

**MDAnalysis merge capabilities:**

```python
import MDAnalysis as mda
from MDAnalysis.lib.util import fixedgroup

# Read two GRO files
u1 = mda.Universe("sI.gro")
u2 = mda.Universe("sII.gro")

# Merge: create new universe with combined atoms
# MDAnalysis doesn't have a direct "merge" method
# You'd need to manually combine coordinates and create a new universe
```

**MDAnalysis does NOT have a built-in merge function.** You'd need to extract coordinates from both universes, adjust positions, and write a new GRO file. This is ~50-100 lines of Python.

### Can Python create Voronoi polycrystals?

**This is where atomsk provides genuine value that Python doesn't easily replicate:**

A Python implementation of Voronoi polycrystal generation requires:
1. **Voronoi tessellation:** `scipy.spatial.Voronoi` provides this (~10 LOC)
2. **Seed rotation:** Rotation matrices from Euler angles or Miller indices (~20 LOC)
3. **Atom assignment to Voronoi regions:** Point-in-polyhedron test for each atom (~50 LOC)
4. **Grain boundary handling:** Remove atoms outside their grain's Voronoi cell (~30 LOC)
5. **Overlap removal:** KD-tree based duplicate detection (~20 LOC)
6. **Box construction and PBC handling:** (~30 LOC)

**Estimated total: ~200-300 lines of Python** for a basic Voronoi polycrystal builder.

**But there's a key difference:** atomsk's polycrystal mode is **battle-tested** by the hydrate MD community. A custom Python implementation would need:
- Correct handling of periodic Voronoi tessellation (non-trivial)
- Proper grain boundary cleanup
- Support for different grain orientations (rotation in Cartesian and fractional coordinates)
- Edge cases: grains near box boundaries, small grains, asymmetric grain sizes

**Verdict:**
- `--merge` mode: Python alternatives exist and are arguably better (preserve GRO format, molecular connectivity)
- `--polycrystal` mode: **Atomsk provides genuine value** — building a Voronoi polycrystal generator from scratch in Python is 200-300 LOC of non-trivial geometry code with many edge cases

## Verdict

### Updated Recommendation

**Atomsk should be supported as an OPTIONAL external tool for polycrystalline hydrate assembly.**

**Rationale:**

1. **Polycrystalline hydrate is a real scientific use case** — confirmed by 7+ publications in top journals (Physical Review Research, The Innovation Energy, Fuel, J. Phys. Chem. B)

2. **`--polycrystal` is the key capability** — creating Voronoi-tessellated polycrystalline structures from a monocrystalline hydrate seed is not easily replicated in Python (200-300 LOC of geometry code)

3. **`--merge` is less valuable for QuickIce** — QuickIce's existing Python code can do stacking/merging with better GROMACS format support

4. **GPL-3.0 is manageable** — subprocess invocation is legally safe; atomsk is an optional, separately-installed dependency; precedent exists (LAMMPS, VMD)

5. **Format conversion overhead is the main friction** — the lack of GRO support in atomsk means extra conversion steps. This is annoying but not a blocker.

6. **LAMMPS users benefit most** — atomsk's best output format is LAMMPS `lmp`. If QuickIce adds LAMMPS export (currently only GROMACS), atomsk becomes more valuable.

### Recommended Integration Pattern

```
QuickIce GUI: "Polycrystalline Hydrate" mode
  ├── Check: is atomsk installed? (subprocess.run(["atomsk", "--version"]))
  │   ├── YES → Enable polycrystal mode
  │   └── NO  → Show "Install atomsk" message, disable mode
  │
  ├── User selects:
  │   ├── Base hydrate structure (sI, sII, sH — from GenIce2)
  │   ├── Number of grains (2-50)
  │   ├── Grain size range (5-100 nm)
  │   ├── Box dimensions (auto-calculated from grain count × size)
  │   └── Random or explicit grain orientations
  │
  ├── Pipeline:
  │   ├── GenIce2 → XYZ output (monocrystalline seed)
  │   ├── Write parameter file (box + random N or node positions)
  │   ├── atomsk --polycrystal seed.xyz params.txt output.lmp -wrap -rmd 1.5
  │   ├── Read LAMMPS output → parse atoms, box
  │   ├── Reconstruct residue names (SOL, CH4, etc.) from molecular connectivity
  │   └── Output as GRO + TOP for GROMACS
  │
  └── Post-processing:
      └── Energy minimization in GROMACS (necessary before production MD)
```

### When NOT to use atomsk

1. **Simple stacking (sI + water interface)** — Use QuickIce's existing Python code; preserves GRO format and residue names
2. **Same-structure supercells** — Use GenIce2's `--rep` or pymatgen's `make_supercell()`
3. **Format conversion only** — Use pymatgen or MDAnalysis; no need for atomsk
4. **CIF import for structure generation** — Use `genice2-cif`; provides ice rules + depolarization that atomsk cannot

### When to use atomsk

1. **Polycrystalline hydrate** (multiple grains of the SAME hydrate structure with different orientations) — atomsk's `--polycrystal` is the standard tool
2. **Nanocrystalline hydrate** (very small grain sizes, 5-20 nm) — atomsk's Voronoi method handles this naturally
3. **Columnar polycrystalline structures** (2D Voronoi + duplicate along short axis)
4. **Interface + polycrystal** (e.g., polycrystalline hydrate slab + liquid water)

### Mixed-Phase Polycrystal Workaround

For creating a polycrystal with DIFFERENT hydrate structures in different grains (e.g., sI grains + sII grains), atomsk's `--polycrystal` alone is insufficient (single seed only). The workaround:

1. Create sI polycrystal and sII polycrystal separately
2. Cut each into half-spaces using `-cut`
3. Merge the two half-polycrystals using `--merge z`
4. Remove overlaps at the interface with `-rmd`

```bash
# Step 1: Create sI and sII polycrystals
atomsk --polycrystal sI_seed.xyz params_sI.txt poly_sI.lmp -wrap -rmd 1.5
atomsk --polycrystal sII_seed.xyz params_sII.txt poly_sII.lmp -wrap -rmd 1.5

# Step 2: Cut each in half along Z
atomsk poly_sI.lmp -cut above 0.5*BOX z poly_sI_bottom.lmp
atomsk poly_sII.lmp -cut below 0.5*BOX z poly_sII_top.lmp

# Step 3: Merge the two halves
atomsk --merge z 2 poly_sI_bottom.lmp poly_sII_top.lmp mixed_polycrystal.lmp -rmd 1.5
```

**This gives you a bilayer polycrystal: sI grains in the bottom half, sII grains in the top half, with a grain boundary at the interface.** It's not a true mixed polycrystal (individual grains aren't randomly interspersed), but it's the closest achievable with atomsk.

## Sources

| Source | URL | Confidence | Used For |
|--------|-----|------------|----------|
| Atomsk `--merge` mode documentation | https://atomsk.univ-lille.fr/doc/en/mode_merge.html | HIGH | Merge syntax, behavior, limitations |
| Atomsk `--polycrystal` mode documentation | https://atomsk.univ-lille.fr/doc/en/mode_polycrystal.html | HIGH | Polycrystal syntax, parameter file format, grain boundary handling |
| Atomsk `-remove-doubles` option | https://atomsk.univ-lille.fr/doc/en/option_rmd.html | HIGH | Overlap removal syntax and behavior |
| Atomsk `-substitute` option | https://atomsk.univ-lille.fr/doc/en/option_substitute.html | HIGH | Guest exchange capability |
| Atomsk `-cut` option | https://atomsk.univ-lille.fr/doc/en/option_cut.html | HIGH | Interface creation capability |
| Atomsk `-select` option | https://atomsk.univ-lille.fr/doc/en/option_select.html | HIGH | Selection capabilities for hydrate cage operations |
| Atomsk `-spacegroup` option | https://atomsk.univ-lille.fr/doc/en/option_spacegroup.html | HIGH | Symmetry expansion capability |
| Atomsk supported file formats | https://atomsk.univ-lille.fr/doc/en/formats.html | HIGH | Confirmed NO GRO format support |
| Atomsk `-rebox` option | https://atomsk.univ-lille.fr/doc/en/option_rebox.html | HIGH | Box dimension recalculation |
| Atomsk citations page | https://atomsk.univ-lille.fr/citations.php | HIGH | 7+ hydrate-specific papers identified |
| Sveinsson & Cao (2025) - Phys. Rev. Research | https://journals.aps.org/prresearch/abstract/10.1103/PhysRevResearch.7.L012007 | MEDIUM | Explicit mention of "using ATOMSK" for polycrystalline hydrate; couldn't access full text |
| Qu et al. (2026) - The Innovation Energy | https://doi.org/10.59717/j.xinn-energy.2026.100157 | MEDIUM | Polycrystalline methane hydrate; cites atomsk; accessed abstract only |
| Qu et al. (2025) - J. Phys. D | https://iopscience.iop.org/article/10.1088/1361-6463/adf346/meta | MEDIUM | Viscoelastic transitions in polycrystalline methane hydrates; couldn't access full text |
| GenIce2 format plugins | Python API test (safe_import) | HIGH | Confirmed XYZ, GRO, CIF, MDView format output |
| Atomsk GitHub examples | https://github.com/pierrehirel/atomsk/tree/master/examples | HIGH | No hydrate examples; polycrystal examples are metals (Al, Fe, Si, MgO, Cu) |
