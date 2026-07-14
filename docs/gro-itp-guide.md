# GRO/ITP File Creation Guide for QuickIce

This guide explains how to create valid GROMACS coordinate (.gro) and topology (.itp) files for custom molecules in QuickIce v4.7.

## Introduction

### Purpose

QuickIce v4.7 allows you to insert custom molecules into ice-water interface structures. To do this, you need:

1. **GRO file** — Atomic coordinates in GROMACS format
2. **ITP file** — Force field topology parameters

This guide provides practical, tutorial-focused instructions for creating these files.

### Prerequisites

Before starting, ensure you have:
- GROMACS installed (for validation tools)
- Molecule structure available (PDB, MOL2, or other format)
- Basic understanding of molecular topology

### Quick Reference

| Task | Recommended Tool | Complexity |
|------|------------------|------------|
| Convert PDB to GRO | `gmx editconf` | Easy |
| Generate ITP from structure | ACPYPE or CHARMM-GUI | Medium |
| Manual GRO creation | Text editor | Medium |
| Manual ITP creation | Text editor | Hard (expert) |

---

## GRO File Format

### Structure Overview

A GRO file contains molecular coordinates in a fixed-width text format:

```
Title line (free format)
Number of atoms (free format)
Atom lines (fixed format)
Box vectors (free format)
```

### Fixed-Width Columns

Each atom line uses specific column positions:

| Field | Columns | Description | Example |
|-------|---------|-------------|---------|
| Residue number | 1-5 | Integer, right-justified | `    1` |
| Residue name | 6-10 | String, left-justified | `ETHAN` |
| Atom name | 11-15 | String, left-justified | `  CA ` |
| Atom number | 16-20 | Integer, right-justified | `    1` |
| X coordinate | 21-28 | Float (nm), 3 decimals | `  1.234` |
| Y coordinate | 29-36 | Float (nm), 3 decimals | `  2.345` |
| Z coordinate | 37-44 | Float (nm), 3 decimals | `  3.456` |
| X velocity | 45-52 | Float (nm/ps), optional | `  0.000` |
| Y velocity | 53-60 | Float (nm/ps), optional | `  0.000` |
| Z velocity | 61-68 | Float (nm/ps), optional | `  0.000` |

**Critical:** Column positions are fixed-width. Spaces matter!

### Units

- **Coordinates:** nanometers (nm)
- **Velocities:** nm/ps (optional)
- **Box vectors:** nanometers (nm)

### Example GRO File

```
Ethanol molecule
     9
    1ETHAN  CH3    1   0.000   0.000   0.000
    1ETHAN  CH2    2   0.127   0.000   0.000
    1ETHAN   OH    3   0.254   0.000   0.000
    1ETHAN   HO    4   0.300   0.089   0.000
    1ETHAN  H1     5  -0.046   0.089   0.000
    1ETHAN  H2     6  -0.046  -0.089   0.000
    1ETHAN  H3     7  -0.046   0.000   0.102
    1ETHAN  H4     8   0.127   0.089   0.000
    1ETHAN  H5     9   0.127  -0.089   0.000
   2.000   2.000   2.000
```

**Breakdown:**
- Line 1: Title (free format)
- Line 2: Atom count = 9
- Lines 3-11: Atom coordinates (fixed-width columns)
- Line 12: Box dimensions (2×2×2 nm³)

### Box Dimensions

The last line defines the simulation box. For custom molecules:
- Use a box large enough to contain the molecule
- Typical: 2-5 nm per dimension
- QuickIce will place molecules in a larger interface box

---

## Creating GRO Files

### Method 1: Using GROMACS editconf (Recommended)

Convert from PDB to GRO format:

```bash
# Basic conversion
gmx editconf -f molecule.pdb -o molecule.gro

# Center in box and set box size
gmx editconf -f molecule.pdb -o molecule.gro -c -box 2 2 2

# Preserve residue numbering
gmx editconf -f molecule.pdb -o molecule.gro -resnr 1
```

**Pros:**
- Automatic format conversion
- Handles atom naming conventions
- Validates structure

**Cons:**
- Requires GROMACS installation
- May need PDB format input

### Method 2: Manual Creation (Small Molecules)

For simple molecules, create the GRO file manually:

1. **Obtain coordinates** from molecular editor (Avogadro, PyMOL, etc.)
2. **Convert to nm** (divide Å by 10)
3. **Write GRO format** following column specifications

**Template:**

```
Custom Molecule Name
   N_ATOMS
    1RESNM  ATNM    1   X.XXX   Y.YYY   Z.ZZZ
    1RESNM  ATNM    2   X.XXX   Y.YYY   Z.ZZZ
...
   BX.XX   BY.YY   BZ.ZZ
```

**Tips:**
- Use monospace font to align columns
- Verify column positions (especially 6-10, 11-15, 21-44)
- Double-check decimal precision (3 decimal places)

### Method 3: Using Molecular Editors

**Avogadro (Free, Open Source):**

1. Build or import molecule
2. File → Export → GROMACS .gro
3. Check output format matches expectations

**PyMOL:**

```python
# Load molecule
load molecule.pdb

# Save as GRO (via intermediate PDB)
save molecule_temp.pdb, molecule
# Then convert with gmx editconf
```

**GaussView / Maestro:**
- Export to PDB or MOL2
- Convert to GRO using `gmx editconf`

### Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| "Atom count mismatch" | Header count ≠ actual atoms | Update line 2 to match atom lines |
| "Invalid coordinates" | Non-numeric values | Check for letters/symbols in coordinate columns |
| "Column misalignment" | Wrong column positions | Verify fixed-width format (use monospace font) |
| "Box dimensions wrong" | Missing or malformed last line | Add box dimensions (e.g., `   2.000   2.000   2.000`) |

---

## ITP File Format

### Required Sections

An ITP file for QuickIce must include these sections:

1. `[ atomtypes ]` — Force field atom types
2. `[ moleculetype ]` — Molecule definition
3. `[ atoms ]` — Atom list with charges and masses

### Optional Sections

For bonded interactions (if applicable):

- `[ bonds ]` — Covalent bonds
- `[ angles ]` — Bond angles
- `[ dihedrals ]` — Dihedral angles
- `[ pairs ]` — Non-bonded pairs
- `[ exclusions ]` — Excluded interactions

### Section Specifications

#### [ atomtypes ]

Defines force field parameters for each atom type:

```
[ atomtypes ]
; name  at.num  mass    charge  ptype  sigma   epsilon
  CT      6     12.01    0.00     A    0.340   0.2862
  HC      1      1.008   0.00     A    0.260   0.0657
  OH      8     16.00    0.00     A    0.307   0.5439
  HO      1      1.008   0.00     A    0.000   0.0000
```

**Fields:**
- `name` — Atom type identifier (must match [ atoms ] section)
- `at.num` — Atomic number (C=6, H=1, O=8, etc.)
- `mass` — Atomic mass (amu)
- `charge` — Reference charge (usually 0.00 for atomtype, actual charges in [ atoms ])
- `ptype` — Particle type (A = atom, V = virtual site)
- `sigma` — LJ radius (nm)
- `epsilon` — LJ well depth (kJ/mol)

**Note:** You must provide this section. QuickIce does not generate force field parameters.

#### [ moleculetype ]

Defines the molecule:

```
[ moleculetype ]
; name      nrexcl
  ETHANOL      3
```

**Fields:**
- `name` — Molecule name (must match GRO residue name)
- `nrexcl` — Number of bonded neighbors to exclude (typically 3)

#### [ atoms ]

Lists all atoms with properties:

```
[ atoms ]
; nr  type  resnr  residue  atom  cgnr  charge    mass
   1   CT      1    ETHAN    CH3    1   -0.18    12.01
   2   CT      1    ETHAN    CH2    2   -0.10    12.01
   3   OH      1    ETHAN     OH    3   -0.60    16.00
   4   HO      1    ETHAN     HO    4    0.40     1.008
   5   HC      1    ETHAN     H1    5    0.06     1.008
   6   HC      1    ETHAN     H2    6    0.06     1.008
   7   HC      1    ETHAN     H3    7    0.06     1.008
   8   HC      1    ETHAN     H4    8    0.04     1.008
   9   HC      1    ETHAN     H5    9    0.04     1.008
```

**Fields:**
- `nr` — Atom number (1, 2, 3, ...)
- `type` — Atom type (must appear in [ atomtypes ])
- `resnr` — Residue number (usually 1 for single molecule)
- `residue` — Residue name (must match GRO residue name)
- `atom` — Atom name (must match GRO atom name)
- `cgnr` — Charge group number (often same as atom number)
- `charge` — Partial charge (sum must be appropriate for molecule)
- `mass` — Atomic mass (amu)

#### [ bonds ] (Optional)

Defines covalent bonds:

```
[ bonds ]
; ai   aj  funct  length
   1    2      1   0.152
   2    3      1   0.143
   3    4      1   0.095
```

**Fields:**
- `ai`, `aj` — Atom numbers
- `funct` — Bond function type (1 = harmonic)
- `length` — Equilibrium bond length (nm)

#### [ angles ] (Optional)

Defines bond angles:

```
[ angles ]
; ai   aj   ak  funct  angle
   4    3    2      1   109.5
   3    2    1      1   109.5
```

**Fields:**
- `ai`, `aj`, `ak` — Atom numbers (aj is central atom)
- `funct` — Angle function type (1 = harmonic)
- `angle` — Equilibrium angle (degrees)

#### [ dihedrals ] (Optional)

Defines dihedral angles:

```
[ dihedrals ]
; ai   aj   ak   al  funct  phase  k
   4    3    2    1      1   180.0  0.62
```

**Fields:**
- `ai`, `aj`, `ak`, `al` — Atom numbers
- `funct` — Dihedral function type (1 = proper dihedral)
- `phase` — Phase angle (degrees)
- `k` — Force constant (kJ/mol/rad²)

### Example ITP File

```
[ atomtypes ]
; name  at.num  mass    charge  ptype  sigma   epsilon
  CT      6     12.01    0.00     A    0.340   0.2862
  HC      1      1.008   0.00     A    0.260   0.0657
  OH      8     16.00    0.00     A    0.307   0.5439
  HO      1      1.008   0.00     A    0.000   0.0000

[ moleculetype ]
; name      nrexcl
  ETHANOL      3

[ atoms ]
; nr  type  resnr  residue  atom  cgnr  charge    mass
   1   CT      1    ETHAN    CH3    1   -0.18    12.01
   2   CT      1    ETHAN    CH2    2   -0.10    12.01
   3   OH      1    ETHAN     OH    3   -0.60    16.00
   4   HO      1    ETHAN     HO    4    0.40     1.008
   5   HC      1    ETHAN     H1    5    0.06     1.008
   6   HC      1    ETHAN     H2    6    0.06     1.008
   7   HC      1    ETHAN     H3    7    0.06     1.008
   8   HC      1    ETHAN     H4    8    0.04     1.008
   9   HC      1    ETHAN     H5    9    0.04     1.008

[ bonds ]
; ai   aj  funct  length
   1    2      1   0.152
   2    3      1   0.143
   3    4      1   0.095
   1    5      1   0.109
   1    6      1   0.109
   1    7      1   0.109
   2    8      1   0.109
   2    9      1   0.109

[ angles ]
; ai   aj   ak  funct  angle
   5    1    2      1   109.5
   6    1    2      1   109.5
   7    1    2      1   109.5
   8    2    1      1   109.5
   9    2    1      1   109.5
   4    3    2      1   109.5
   1    2    3      1   109.5

[ dihedrals ]
; ai   aj   ak   al  funct  phase  k
   4    3    2    1      1   180.0  0.62
```

---

## Creating ITP Files

### Method 1: Using ACPYPE (Recommended for GAFF/GAFF2)

ACPYPE generates GROMACS topology files from structure files using AMBER force fields (GAFF/GAFF2).

**Installation:**

```bash
conda install -c conda-forge acpype
```

**Usage:**

```bash
# From MOL2 file (preferred)
acpype -i molecule.mol2

# From PDB file
acpype -i molecule.pdb

# Specify charge method
acpype -i molecule.mol2 -c bcc

# Output directory
acpype -i molecule.mol2 -o output_dir
```

**Output:**
- `molecule_GMX.itp` — GROMACS topology
- `molecule_GMX.gro` — GROMACS coordinates (if needed)

**Pros:**
- Automatic parameter assignment
- GAFF/GAFF2 force field (compatible with QuickIce hydrate guests)
- Handles partial charges

**Cons:**
- Requires AMBERTools or standalone installation
- May need charge calculation for novel molecules

### Method 2: Using CHARMM-GUI (For CHARMM Force Field)

CHARMM-GUI provides a web interface for generating CHARMM force field parameters.

**Steps:**

1. Visit: https://charmm-gui.org/?doc=input/gmx
2. Upload structure file (PDB, MOL2, etc.)
3. Select force field (CHARMM36 recommended)
4. Generate topology
5. Download GROMACS files

**Pros:**
- CHARMM force field (well-validated for biomolecules)
- Web interface (no installation)
- Excellent documentation

**Cons:**
- Requires registration (free for academic use)
- Different force field from QuickIce hydrate guests (may need adjustment)

### Method 3: Manual Creation (Expert Users)

For expert users with force field knowledge:

1. **Obtain parameters** from:
   - Force field documentation (GAFF, CHARMM, OPLS-AA)
   - Literature (published parameters for your molecule)
   - Automated tools (see Methods 1-2) as starting point

2. **Define atomtypes:**
   - Assign LJ parameters (σ, ε)
   - Use atom typing rules from force field

3. **Calculate partial charges:**
   - RESP2, AM1-BCC, or literature values
   - Sum should be appropriate for molecule charge

4. **Define bonded parameters:**
   - Bond lengths, angles, dihedrals
   - Use force field database or QM calculations

5. **Validate:**
   - Check parameter consistency
   - Test with small MD simulation

**Tips:**
- Start from existing molecule (similar structure)
- Use force field parameter databases
- Validate with short test simulation

### Force Field Parameter Sources

| Source | Force Field | URL | Access |
|--------|-------------|-----|--------|
| ATB | GROMOS, others | https://atb.uq.edu.au/ | Free registration |
| LigParGen | OPLS-AA | http://zarbi.chem.yale.edu/ligpargen/ | Free |
| CGenFF | CHARMM | https://cgenff.paramchem.org/ | Free registration |
| GAFF | AMBER | Via ACPYPE | Open source |
| SwissParam | CHARMM/MMTB | https://www.swissparam.ch/ | Free |

> **⚠️ Combining Rule Incompatibility:** OPLS-AA uses geometric combining rules (`comb-rule 3` in GROMACS), while TIP4P-ICE water uses Lorentz-Berthelot combining rules (`comb-rule 2`). Using OPLS-AA parameters with TIP4P-ICE produces incorrect LJ cross-interactions. If you use LigParGen/OPLS-AA, you must manually set `[comb-rule 3]` in your `.top` file and ensure all atom pairs use geometric combining. For easiest compatibility with QuickIce's default settings, prefer GAFF (AMBER) or CHARMM parameters instead.

---

## Validation

### What QuickIce Checks

QuickIce validates GRO/ITP files before insertion:

1. **Atom count match** — GRO file atom count equals ITP [ atoms ] count
2. **Residue name consistency** — GRO residue name matches ITP moleculetype name
3. **Required sections present** — ITP has [ atomtypes ], [ moleculetype ], [ atoms ]

### Pre-Upload Validation

Validate files before uploading to QuickIce:

#### Check GRO Format

```bash
# Verify atom count
head -2 molecule.gro

# Check coordinate format
sed -n '3,$p' molecule.gro | head -5

# Verify box dimensions
tail -1 molecule.gro
```

#### Check ITP Format

```bash
# Verify required sections
grep -E "^\[ atomtypes \]|^\[ moleculetype \]|^\[ atoms \]" molecule.itp

# Count atoms
grep -v "^;" molecule.itp | grep -A 100 "^\[ atoms \]" | grep -E "^\s+[0-9]" | wc -l
```

#### Validate with GROMACS

```bash
# Check topology consistency
gmx check -f molecule.gro -s molecule.itp

# Test short MD simulation (optional)
gmx grompp -f minim.mdp -c molecule.gro -p topol.top -r molecule.gro
gmx mdrun -deffnm em
```

### Common Validation Errors

| Error | Cause | Fix |
|-------|-------|-----|
| "Atom count mismatch" | GRO header ≠ ITP atoms | Update GRO header or ITP atoms section |
| "Residue name not found" | GRO residue ≠ ITP moleculetype | Make residue names match exactly |
| "Missing [ atomtypes ] section" | ITP lacks force field parameters | Add [ atomtypes ] with LJ parameters |
| "Undefined atom type" | Atom type not in [ atomtypes ] | Add missing atom type definition |
| "Inconsistent charges" | Atom charges sum ≠ molecular charge | Adjust partial charges |

### Residue Name Consistency

**Critical:** GRO residue name (columns 6-10) must match ITP moleculetype name.

**Example:**

GRO file:
```
Custom Molecule
     9
    1CUSTOM  CA    1   0.000   0.000   0.000
    ...
```

ITP file:
```
[ moleculetype ]
; name      nrexcl
  CUSTOM       3
```

Both use "CUSTOM" as the identifier.

---

## Custom Guest ITP Requirements (for Hydrate Cage Guests)

When uploading a custom guest molecule for hydrate cage placement (GUI-only for v4.7), the `.gro` and `.itp` files must meet specific requirements enforced by QuickIce's validation pipeline. The CLI supports built-in CH₄/THF guests only (via `--cage-guest KEY=GUEST:OCC`); there is no CLI flag for custom hydrate cage guests in v4.7.

### 1. comb-rule = 2 (Mandatory)

The ITP `[ defaults ]` section, when present, must specify `comb-rule = 2` (Lorentz-Berthelot combining rules, AMBER/GAFF2 convention). This is consistent with QuickIce's main `.top` file, which always supplies `comb-rule = 2`.

- **Rejected:** If `[ defaults ]` contains a comb-rule other than 2 (e.g. `comb-rule = 1`), the upload fails with: `ITP comb-rule must be 2 (Lorentz-Berthelot / AMBER-GAFF2); got comb-rule=1. QuickIce does not auto-convert A/B rules. Please regenerate the ITP with comb-rule=2.`
- **Accepted:** If `[ defaults ]` is absent, the upload succeeds — the main `.top` file supplies `comb-rule = 2`.

This is enforced by `parse_itp_defaults_comb_rule()` in `quickice/structure_generation/itp_parser.py`, with the rejection check in `quickice/structure_generation/custom_guest_bridge.py` (the validator rejects only when the parsed value is non-`None` and `!= 2`).

### 2. Residue Base Name ≤ 3 Characters

The GRO file format uses fixed-width columns (6-10) for residue names, allowing a maximum of 5 characters. QuickIce appends an `_H` suffix to hydrate guest residue names (see rule 3 below), so the **base name must be ≤ 3 characters** to keep the total ≤ 5 chars.

- **Accepted:** `MOL` (3 chars) → `MOL_H` (5 chars) ✓
- **Rejected:** `ETHAN` (5 chars) → `ETHAN_H` (7 chars) ✗ — error: `Custom guest residue name 'ETHAN' (5 chars) exceeds 3 chars. GRO format allows 5-char residue names; QuickIce reserves 2 chars for the '_H' hydrate suffix. Use a residue name of 3 chars or fewer (e.g. 'MOL').`

The ≤3-char base-name check is enforced at upload time in `quickice/structure_generation/custom_guest_bridge.py`; the downstream 5-char GRO limit is enforced by `validate_gro_residue_name()` in `quickice/output/gromacs_writer.py` (raises `ValueError` if the transformed name exceeds 5 chars).

### 3. `_H` Suffix Convention

Hydrate cage guests use the `_H` suffix; liquid solutes use the `_L` suffix. The `MoleculetypeRegistry` (in `quickice/structure_generation/moleculetype_registry.py`) produces the registered moleculetype name: `register_hydrate_guest('MOL')` → `MOL_H`, `register_liquid_solute('CH4')` → `CH4_L`. During export, `transform_guest_itp()` (in `quickice/output/gromacs_writer.py`) rewrites the `[ moleculetype ]` name and the `[ atoms ]` residue name from `{base}` to `{base}_H`.

Example: A custom guest with residue name `MOL` becomes `MOL_H` in the exported `.gro` and `.top` files. Built-in guests follow the same convention: `CH4` → `CH4_H`, `THF` → `THF_H`.

### 4. `[ atomtypes ]` Commented Out + Merged

The `[ atomtypes ]` section in the uploaded `.itp` is **commented out** during export (step 1 of `transform_guest_itp`), and the atom type definitions are **merged into the main `.top`** file's `[ atomtypes ]` section via `_merge_custom_atomtypes()` (in `quickice/output/gromacs_writer.py`). This prevents duplicate atomtype conflicts between the custom guest and the bundled force field parameters (TIP4P-ICE water + GAFF2 built-in guests).

### 5. Distinct from Tab-3 Liquid Custom Molecule

The hydrate custom guest (Tab 1) is distinct from the liquid custom molecule (Tab 3):

| Property | Hydrate Custom Guest (Tab 1) | Liquid Custom Molecule (Tab 3) |
|----------|-------------------------------|--------------------------------|
| Suffix | `_H` | None |
| Residue name limit | ≤ 3 chars (base) | ≤ 5 chars (no suffix) |
| comb-rule requirement | comb-rule = 2 mandatory (if `[ defaults ]` present) | Inherited from main `.top` |
| `[ atomtypes ]` handling | Commented out + merged into main `.top` | Commented out + merged into main `.top` |
| Placement | Hydrate cages (GenIce2 bridge) | Liquid region (random/custom positions) |
| CLI flag | None (GUI-only for v4.7) | `--custom-gro` + `--custom-itp` (requires `--interface`) |

> **Note:** Custom guest in hydrate is a GUI-only feature for v4.7. The CLI supports built-in CH₄/THF guests only (via `--cage-guest KEY=GUEST:OCC`, repeatable). Documenting `--custom-gro`/`--custom-itp` as hydrate cage guest flags would be incorrect — those flags are for Tab-3 liquid custom molecules and require `--interface`.

---

## Examples

### Example 1: Small Molecule (Ethanol)

**Ethanol GRO file (`ethanol.gro`):**

```
Ethanol molecule
     9
    1ETHAN  CH3    1   0.000   0.000   0.000
    1ETHAN  CH2    2   0.127   0.000   0.000
    1ETHAN   OH    3   0.254   0.000   0.000
    1ETHAN   HO    4   0.300   0.089   0.000
    1ETHAN  H1     5  -0.046   0.089   0.000
    1ETHAN  H2     6  -0.046  -0.089   0.000
    1ETHAN  H3     7  -0.046   0.000   0.102
    1ETHAN  H4     8   0.127   0.089   0.000
    1ETHAN  H5     9   0.127  -0.089   0.000
   1.000   1.000   1.000
```

**Ethanol ITP file (`ethanol.itp`):**

```
[ atomtypes ]
; name  at.num  mass    charge  ptype  sigma   epsilon
  CT      6     12.01    0.00     A    0.340   0.2862
  HC      1      1.008   0.00     A    0.260   0.0657
  OH      8     16.00    0.00     A    0.307   0.5439
  HO      1      1.008   0.00     A    0.000   0.0000

[ moleculetype ]
; name      nrexcl
  ETHANOL      3

[ atoms ]
; nr  type  resnr  residue  atom  cgnr  charge    mass
   1   CT      1    ETHAN    CH3    1   -0.18    12.01
   2   CT      1    ETHAN    CH2    2   -0.10    12.01
   3   OH      1    ETHAN     OH    3   -0.60    16.00
   4   HO      1    ETHAN     HO    4    0.40     1.008
   5   HC      1    ETHAN     H1    5    0.06     1.008
   6   HC      1    ETHAN     H2    6    0.06     1.008
   7   HC      1    ETHAN     H3    7    0.06     1.008
   8   HC      1    ETHAN     H4    8    0.04     1.008
   9   HC      1    ETHAN     H5    9    0.04     1.008

[ bonds ]
; ai   aj  funct  length
   1    2      1   0.152
   2    3      1   0.143
   3    4      1   0.095
   1    5      1   0.109
   1    6      1   0.109
   1    7      1   0.109
   2    8      1   0.109
   2    9      1   0.109
```

**Key points:**
- 9 atoms in both GRO and ITP
- Residue name "ETHAN" in GRO, moleculetype "ETHANOL" in ITP (QuickIce allows mismatch with user dialog in GUI mode; in CLI mode, the mismatch is accepted silently)
- GAFF atom types (CT, HC, OH, HO)
- Charge sum = -0.18 - 0.10 - 0.60 + 0.40 + 0.06×3 + 0.04×2 = 0.00 (neutral)

### Example 2: Drug Molecule (Aspirin)

**Aspirin (Acetylsalicylic acid) has 21 atoms.**

**Key considerations:**
- Aromatic ring with proper LJ parameters
- Carboxylic acid group with appropriate charges
- Ester linkage with dihedral parameters

**Recommended workflow:**
1. Obtain structure from PubChem (CID 2244)
2. Convert to MOL2 with Open Babel: `obabel -:"aspirin" -O aspirin.mol2`
3. Generate ITP with ACPYPE: `acpype -i aspirin.mol2`
4. Convert GRO with editconf: `gmx editconf -f aspirin_GMX.gro -o aspirin.gro`

**Charge considerations:**
- Neutral aspirin: total charge = 0.0
- Deprotonated aspirin: total charge = -1.0

### Example 3: Polymer Fragment

**Polyethylene glycol (PEG) fragment (3-monomer chain).**

**Challenges:**
- Multiple repeating units
- Consistent atom naming across monomers
- Proper bonded parameters between monomers

**Workflow:**
1. Build monomer structure in Avogadro
2. Duplicate and connect monomers
3. Generate parameters for full fragment
4. Ensure consistent residue naming

**Atom numbering:**
```
[ atoms ]
; nr  type  resnr  residue  atom  cgnr  charge    mass
   1   CT      1    PEG1     C1     1   -0.10    12.01
   2   OS      1    PEG1     O1     2   -0.40    16.00
   ...
  21   CT      2    PEG2     C1    21   -0.10    12.01
  22   OS      2    PEG2     O1    22   -0.40    16.00
  ...
```

**Note:** Each monomer has different residue number (resnr) and residue name.

---

## Troubleshooting

### "Atom count mismatch" Error

**Symptom:** QuickIce shows "GRO file has N atoms, ITP file has M atoms"

**Causes:**
1. GRO header line 2 is incorrect
2. ITP [ atoms ] section missing atoms
3. Different molecule versions

**Fixes:**
```bash
# Check GRO atom count
head -2 molecule.gro

# Count ITP atoms
grep -v "^;" molecule.itp | grep -A 100 "^\[ atoms \]" | grep -E "^\s+[0-9]" | wc -l

# If mismatch, update GRO header to match ITP
sed -i "2s/.*/$(grep -v '^;' molecule.itp | grep -A 100 '^\[ atoms \]' | grep -E '^\s+[0-9]' | wc -l)/" molecule.gro
```

### "Residue name not found" Error

**Symptom:** QuickIce shows "GRO residue name 'XXX' not found in ITP"

**Causes:**
1. GRO residue name (columns 6-10) doesn't match ITP moleculetype
2. Extra spaces or characters in residue name
3. Case sensitivity

**Fixes:**

Check GRO residue name:
```bash
# Extract residue name from GRO (columns 6-10)
sed -n '3p' molecule.gro | cut -c6-10
```

Check ITP moleculetype:
```bash
# Extract moleculetype name from ITP
grep -A 1 "^\[ moleculetype \]" molecule.itp | tail -1 | awk '{print $1}'
```

If mismatch, update ITP moleculetype to match GRO residue name (or vice versa).

### "Missing [ atomtypes ] section" Error

**Symptom:** QuickIce shows "ITP file missing required [ atomtypes ] section"

**Causes:**
1. ITP file doesn't include force field parameters
2. Section present but incorrectly formatted
3. Using incompatible ITP format

**Fixes:**

Check for section:
```bash
grep "^\[ atomtypes \]" molecule.itp
```

If missing, you must add it. Use ACPYPE or CHARMM-GUI to generate proper ITP with atomtypes.

If present but malformed, verify format:
```
[ atomtypes ]
; name  at.num  mass    charge  ptype  sigma   epsilon
  CT      6     12.01    0.00     A    0.340   0.2862
```

### GROMACS Simulation Failures After Export

**Symptom:** GROMACS simulation crashes with "Undefined atom type" or similar errors

**Causes:**
1. Atom type parameters not compatible with water model
2. Missing bonded parameters
3. Incorrect charge group assignments

**Fixes:**

1. **Verify force field compatibility:**
   - QuickIce uses TIP4P-ICE water model
   - Custom molecule parameters should be from a compatible force field. **GAFF (AMBER) and CHARMM** use Lorentz-Berthelot combining rules compatible with TIP4P-ICE. **OPLS-AA** uses geometric combining rules and is NOT compatible with QuickIce's default `comb-rule 2` — using OPLS-AA without adjusting `[comb-rule]` in the .top file will produce incorrect LJ cross-interactions.

2. **Check bonded parameters:**
   ```bash
   # List bonds in ITP
   grep -A 20 "^\[ bonds \]" molecule.itp
   
   # List angles
   grep -A 20 "^\[ angles \]" molecule.itp
   
   # List dihedrals
   grep -A 20 "^\[ dihedrals \]" molecule.itp
   ```

3. **Test minimization:**
   ```bash
   # Create minimal test system
   gmx insert-molecules -ci molecule.gro -box 3 3 3 -nmol 1 -o test.gro
   
   # Add water
   gmx solvate -cp test.gro -cs tip4p-ice.gro -o test_solvated.gro
   
   # Run minimization
   gmx grompp -f minim.mdp -c test_solvated.gro -p topol.top
   gmx mdrun -deffnm em -v
   ```

### "Invalid coordinate format" Error

**Symptom:** QuickIce shows "Invalid coordinates in GRO file"

**Causes:**
1. Non-numeric values in coordinate columns
2. Wrong column positions
3. Incorrect decimal format

**Fixes:**

Check coordinate format:
```bash
# Show first few atom lines
sed -n '3,7p' molecule.gro
```

Verify column positions (X: 21-28, Y: 29-36, Z: 37-44):
```bash
# Extract coordinates
sed -n '3p' molecule.gro | cut -c21-44
```

Ensure coordinates are numeric with 3 decimal places:
```
   1.234   2.345   3.456
```

---

## Workflow Example

After creating your GRO and ITP files, you can test them with the QuickIce hydrate-interface-custom-ion workflow script:

```bash
# Run with your custom molecule and default settings
./scripts/hydrate-interface-custom-ion.sh \
  --custom-gro my_molecule.gro \
  --custom-itp my_molecule.itp

# Customize temperature, ion concentration, and hydrate type
./scripts/hydrate-interface-custom-ion.sh \
  --custom-gro my_molecule.gro \
  --custom-itp my_molecule.itp \
  --temperature 270 \
  --ion-conc 0.3 \
  --lattice-type sII \
  --guest THF
```

This script generates a clathrate hydrate structure, creates an ice-water interface, inserts your custom molecules into the liquid phase, and adds NaCl ions — producing GROMACS-ready output files in a single command.

See the [CLI Reference](cli-reference.md#example-scripts) for additional example scripts.

---

## References

### GROMACS Documentation

- **File formats:** http://manual.gromacs.org/current/reference-manual/file-formats.html
- **Topology file:** http://manual.gromacs.org/current/reference-manual/topology/topology-file.html
- **Coordinate file:** http://manual.gromacs.org/current/reference-manual/file-formats.html#gro

### Parameter Generation Tools

- **ACPYPE:** https://github.com/alanwilter/ACPYPE
  - GAFF/GAFF2 parameter generation
  - AMBER-BCC charge calculation
  
- **CHARMM-GUI:** http://www.charmm-gui.org/
  - CHARMM force field parameters
  - Web interface for topology generation
  
- **LigParGen:** http://zarbi.chem.yale.edu/ligpargen/
  - OPLS-AA force field
  - Automated parameter assignment

### Force Field Databases

- **Automated Topology Builder (ATB):** https://atb.uq.edu.au/
  - GROMOS force field
  - Large molecule database
  
- **CGenFF:** https://cgenff.paramchem.org/
  - CHARMM General Force Field
  - Small molecule parameters

### Molecular Editors

- **Avogadro:** https://avogadro.cc/
  - Open source, cross-platform
  - Structure building and optimization
  
- **PyMOL:** https://pymol.org/2/
  - Molecular visualization
  - Structure editing capabilities

### Scientific References

- **TIP4P-ICE:** Abascal, J. L. F., Sanz, E., García Fernández, R., & Vega, C. (2005). A potential model for the study of ices and amorphous water: TIP4P/Ice. *Journal of Chemical Physics*, 122(23), 234511. DOI: 10.1063/1.1931662

- **GAFF2:** Wang, J., Wolf, R. M., Caldwell, J. W., Kollman, P. A., & Case, D. A. (2004). Development and testing of a general amber force field. *Journal of Computational Chemistry*, 25(9), 1157-1174. DOI: 10.1002/jcc.20035

---

## Quick Reference Checklist

Before uploading custom molecule files to QuickIce, verify:

- [ ] **GRO file format**
  - [ ] Title line present
  - [ ] Atom count matches actual atoms
  - [ ] Coordinates in nanometers (3 decimals)
  - [ ] Box dimensions present (last line)
  - [ ] Fixed-width columns correct (especially 6-10, 11-15, 21-44)

- [ ] **ITP file format**
  - [ ] [ atomtypes ] section present with LJ parameters
  - [ ] [ moleculetype ] section defines molecule name
  - [ ] [ atoms ] section lists all atoms with charges and masses
  - [ ] Atom types match between [ atomtypes ] and [ atoms ]

- [ ] **Consistency**
  - [ ] GRO atom count = ITP [ atoms ] count
  - [ ] GRO residue name matches ITP moleculetype name (or user will be prompted)
  - [ ] All atoms in ITP have defined atom types

- [ ] **Parameters**
  - [ ] Partial charges sum to appropriate value (neutral, +1, -1, etc.)
  - [ ] LJ parameters (σ, ε) are reasonable (check against similar molecules)
  - [ ] Bonded parameters (if present) are consistent with structure

- [ ] **Validation**
  - [ ] `gmx check -f molecule.gro -s molecule.itp` passes
  - [ ] Short minimization test runs without errors
  - [ ] Visual inspection shows correct molecular geometry

---

*Guide version: v4.7*
*Last updated: 2026-07-12*
*For QuickIce v4.7 documentation, see [GUI Guide](gui-guide.md)*
