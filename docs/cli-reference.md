# QuickIce CLI Reference

Complete documentation for QuickIce command-line interface.

> **Note:** Ice-water interface construction is available in the [GUI](gui-guide.md#interface-construction-tab-2) (recommended) and via CLI with the `--interface` flag.

## Usage

```bash
python -m quickice --temperature <T> --pressure <P> --nmolecules <N> [options]
```

## Required Arguments

### `--temperature`, `-T`

Temperature in Kelvin (0-500K). This argument is required.

**Valid range:** 0 to 500 K

**Examples:**
```bash
# Ice Ih (ambient conditions)
python -m quickice -T 260 -P 0.1 -N 100

# High temperature
python -m quickice --temperature 300 --pressure 100 --nmolecules 50
```

---

### `--pressure`, `-P`

Pressure in MPa (0-10000 MPa). This argument is required.

**Valid range:** 0 to 10000 MPa (0 to 10 GPa)

**Examples:**
```bash
# Ice III (moderate pressure)
python -m quickice -T 250 -P 250 -N 100

# Ice VII (very high pressure)
python -m quickice -T 300 -P 2500 -N 50
```

---

### `--nmolecules`, `-N`

Number of water molecules in the generated structure (4-100000). Required for ice generation; optional for `--interface` mode (default: 256).

**Valid range:** 4 to 100000 molecules

**Examples:**
```bash
# Small test structure
python -m quickice -T 260 -P 0.1 -N 50

# Larger structure for better statistics
python -m quickice -T 260 -P 0.1 -N 1000

# Interface mode (nmolecules omitted — uses default)
python -m quickice -T 250 -P 0.1 --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0
```

---

## Optional Arguments

### `--output`, `-o`

Output directory for generated PDB files and phase diagram. Default: `output`

**Usage:**
```bash
python -m quickice -T 260 -P 0.1 -N 100 --output my_structures
```

The output directory will contain:
- `candidate_*.pdb` - Ranked ice structure candidates in PDB format
- `phase_diagram.png` - Phase diagram showing input conditions

---

### `--no-diagram`

Disable phase diagram generation. By default, QuickIce generates a phase diagram with a marker showing the input conditions.

**Usage:**
```bash
python -m quickice -T 260 -P 0.1 -N 100 --no-diagram
```

Use this flag when you only need the PDB output files and want to save time.

**Note:** In pipeline mode (when any pipeline flags like `--hydrate`, `--interface`, `--custom-gro`, `--solute-type`, or `--ion-concentration` are present), the `--no-diagram` flag has no effect — phase diagrams are not generated in pipeline mode by default.

---

### `--gromacs`, `-g`

Export structure in GROMACS format (.gro, .top, .itp files).

**Usage:**
```bash
# Export all candidates with shared top/itp files
python -m quickice -T 250 -P 100 -N 128 --gromacs --output ice_gro

# Export specific ranked candidate
python -m quickice -T 250 -P 100 -N 128 --gromacs --candidate 2
```

When this flag is set, QuickIce exports:
- **One `.gro` file per candidate** — `ice_ih_1.gro`, `ice_ih_2.gro`, etc. (coordinates differ per candidate)
- **Single `.top` file** — `ice_ih.top` (topology is identical for all candidates)
- **Single `.itp` file** — `tip4p_ice.itp` (force field is identical for all candidates)

**Water model:** TIP4P-ICE (optimized for ice simulations)
Credit: itp file adapted from http://bbs.keinsci.com/forum.php?mod=viewthread&tid=32973&page=1#pid222346

**Note:** The molecule count specifies a *minimum* number. GenIce2 creates supercells to satisfy crystal symmetry, so actual count may be higher (e.g., 2× the minimum for some phases).

**Note:** In pipeline mode (when any pipeline flags like `--hydrate`, `--interface`, `--custom-gro`, `--solute-type`, or `--ion-concentration` are present), the `--gromacs` flag has no effect — GROMACS files are always generated. The `--gromacs` flag only controls GROMACS export in ice-only mode (single ice candidate generation without pipeline flags).

---

### `--candidate`, `-c`

Select which ranked candidate to export for GROMACS (1-based index).

**Usage:**
```bash
# Export all candidates (default)
python -m quickice -T 250 -P 100 -N 128 --gromacs

# Export the second-ranked candidate
python -m quickice -T 250 -P 100 -N 128 --gromacs --candidate 2
```

Default: Export all candidates. Use `--candidate N` to export only rank N.

---

### `--no-overwrite`

Do not overwrite existing output files. When this flag is set, QuickIce checks if the output directory already contains files before writing. If files exist, the pipeline exits with code 1.

**Type:** Boolean flag (store_true)

**Default:** False (overwriting is allowed by default)

```bash
# Safe re-run without overwriting existing results
python -m quickice -T 260 -P 0.1 -N 100 --no-overwrite
```

---

### `--version`, `-V`

Display the current QuickIce version.

**Usage:**
```bash
python -m quickice --version
# Output: python -m quickice 4.7.0
```

> **Version history:** v4.0 added interface construction; v4.5 added solute and custom molecule insertion; v4.7 adds extended hydrate generation with filled ices, custom guests, mixed cage occupancy, and depol mode.

---

## Ice Phase Examples

QuickIce supports 8 ice polymorphs (those with GenIce2 lattice implementations). Below are example commands for generating structures in different ice phases:

### Ice Ih (Hexagonal Ice)

The most common form of ice, stable at ambient pressure and temperatures below 273K.

```bash
python -m quickice -T 260 -P 0.1 -N 100
```

**Phase region:** Low pressure (< 200 MPa), moderate temperature (200-273K)

---

### Ice Ic (Cubic Ice)

Cubic form of ice, metastable at ambient pressure.

```bash
python -m quickice -T 200 -P 0.1 -N 100
```

**Phase region:** Low pressure (< 200 MPa), low temperature (< 200K)

---

### Ice II

Ordered form of ice, stable at moderate pressures.

```bash
python -m quickice -T 200 -P 300 -N 100
```

**Phase region:** Moderate pressure (200-500 MPa), low temperature (< 250K)

---

### Ice III

Tetragonal ice, stable at moderate pressures.

```bash
python -m quickice -T 250 -P 250 -N 100
```

**Phase region:** Moderate pressure (200-400 MPa), moderate temperature (250-270K)

---

### Ice V

Complex monoclinic structure.

```bash
python -m quickice -T 260 -P 450 -N 100
```

**Phase region:** Higher pressure (400-600 MPa), moderate temperature (240-270K)

---

### Ice VI

First high-pressure phase with two independent networks.

```bash
python -m quickice -T 280 -P 700 -N 100
```

**Phase region:** High pressure (600-2000 MPa), moderate temperature (270-350K)

---

### Ice VII

Cubic high-pressure phase with two interpenetrating networks.

```bash
python -m quickice -T 300 -P 2500 -N 100
```

**Phase region:** Very high pressure (> 2000 MPa), any temperature up to 355K

---

### Ice VIII

Ordered form of Ice VII, stable at lower temperatures.

```bash
python -m quickice -T 200 -P 2500 -N 100
```

**Phase region:** Very high pressure (> 2000 MPa), low temperature (< 278K)

---

**Note:** Ice IX, Ice X, Ice XI, and Ice XV are not supported (no GenIce2 lattice implementations available).

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Runtime error (phase mapping, structure generation, or general exception) |
| 2 | Argument error (invalid or missing required flags) |

---

## Interface Generation Flags

QuickIce can generate ice-water interface structures directly from the command line using the `--interface` flag. This is useful for batch processing or scripting.

### `--interface`

Enable ice-water interface generation mode. When set, QuickIce generates an interface structure instead of an ice candidate.

**Type:** Boolean flag (store_true)

**Default:** False

**Required with:** `--mode`, `--box-x`, `--box-y`, `--box-z`

```bash
# Enable interface generation with slab mode
python -m quickice --temperature 250 --pressure 0.1 \
  --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0
```

---

### `--mode`, `-m`

Interface geometry mode. Determines the type of ice-water interface to generate.

**Choices:** `slab`, `pocket`, `piece`

**Default:** None (required with `--interface`)

| Mode | Description | Required Parameters |
|------|-------------|---------------------|
| `slab` | Layered ice-water interface | `--ice-thickness`, `--water-thickness` |
| `pocket` | Water cavity within ice matrix | `--pocket-diameter` |
| `piece` | Ice crystal embedded in water | None (dimensions from candidate) |

```bash
# Slab mode: layered ice-water-ice
python -m quickice --temperature 250 --pressure 0.1 \
  --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0

# Pocket mode: water cavity in ice
python -m quickice --temperature 253 --pressure 500 \
  --interface --mode pocket \
  --box-x 4.0 --box-y 4.0 --box-z 4.0 \
  --pocket-diameter 2.0

# Piece mode: ice fragment in water
python -m quickice --temperature 180 --pressure 1000 \
  --interface --mode piece \
  --box-x 4.0 --box-y 4.0 --box-z 4.0
```

---

### `--box-x`, `--box-y`, `--box-z`, `-x`, `-y`, `-z`

Simulation box dimensions in nanometers. All interface modes require box dimensions to define the simulation cell.

**Type:** Float (≥1.0 nm)

**Default:** None (required with `--interface`)

**Slab mode constraint:** Box Z must equal `2 × ice_thickness + water_thickness`.

```bash
# 5×5×10 nm box for slab interface
python -m quickice --temperature 250 --pressure 0.1 \
  --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0

# 4×4×4 nm box for pocket interface
python -m quickice --temperature 253 --pressure 500 \
  --interface --mode pocket \
  --box-x 4.0 --box-y 4.0 --box-z 4.0 \
  --pocket-diameter 2.0
```

---

### `--ice-thickness`, `-t`

Ice layer thickness in nanometers. Each ice layer in the slab has this thickness.

**Type:** Float (nm)

**Default:** None

**Required with:** `--interface --mode slab`

```bash
# 3.0 nm ice layers with 4.0 nm water layer
python -m quickice --temperature 250 --pressure 0.1 \
  --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0
```

---

### `--water-thickness`, `-w`

Water layer thickness in nanometers. The water region between the two ice layers.

**Type:** Float (nm)

**Default:** None

**Required with:** `--interface --mode slab`

**Slab constraint:** `box-z = 2 × ice-thickness + water-thickness`

```bash
# 4.0 nm water layer between 3.0 nm ice layers
python -m quickice --temperature 250 --pressure 0.1 \
  --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0
```

---

### `--pocket-diameter`, `-d`

Pocket diameter in nanometers for pocket-mode interface generation.

**Type:** Float (nm)

**Default:** None

**Required with:** `--interface --mode pocket`

```bash
# 2.0 nm spherical pocket in ice matrix
python -m quickice --temperature 253 --pressure 500 \
  --interface --mode pocket \
  --box-x 4.0 --box-y 4.0 --box-z 4.0 \
  --pocket-diameter 2.0
```

---

### `--pocket-shape`

Pocket shape for pocket-mode interface generation. Determines whether the water cavity within the ice matrix is spherical or cubic.

**Choices:** `sphere`, `cubic`

**Default:** `sphere`

**Required with:** `--interface --mode pocket`

```bash
# Spherical pocket (default)
python -m quickice --temperature 253 --pressure 500 \
  --interface --mode pocket \
  --box-x 4.0 --box-y 4.0 --box-z 4.0 \
  --pocket-diameter 2.0

# Cubic pocket
python -m quickice --temperature 253 --pressure 500 \
  --interface --mode pocket \
  --box-x 4.0 --box-y 4.0 --box-z 4.0 \
  --pocket-diameter 2.0 --pocket-shape cubic
```

---

### `--seed`

Random seed for reproducible water placement. Using the same seed produces identical water molecule positions across runs.

**Type:** Integer

**Default:** 42

**Note:** The default seed is 42 for reproducibility. Specifying `--seed 42` is redundant and produces the same result as omitting the flag entirely.

```bash
# Reproducible interface with specific seed
python -m quickice --temperature 250 --pressure 0.1 \
  --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --seed 12345

# Different seed for different water arrangement
python -m quickice --temperature 250 --pressure 0.1 \
  --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --seed 99999
```

---

### Examples

#### Slab Interface

Generate a layered ice-water-ice slab:

```bash
python -m quickice --temperature 250 --pressure 0.1 \
  --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --gromacs --output slab_output
```

Creates two ice layers (3.0 nm each) with a 4.0 nm water layer between them.

#### Pocket Interface

Generate a water cavity within ice:

```bash
python -m quickice --temperature 253 --pressure 500 \
  --interface --mode pocket \
  --box-x 4.0 --box-y 4.0 --box-z 4.0 \
  --pocket-diameter 2.0 \
  --gromacs --output pocket_output
```

Creates a 2.0 nm spherical water pocket inside an Ice V matrix.

#### Piece Interface

Generate an ice fragment in water:

```bash
python -m quickice --temperature 180 --pressure 1000 \
  --interface --mode piece \
  --box-x 4.0 --box-y 4.0 --box-z 4.0 \
  --gromacs --output piece_output
```

Box dimensions must exceed the ice candidate dimensions.

### Triclinic Phase Support

All supported ice phases except Ice II work with interface generation. Ice II (rhombohedral) cannot form orthogonal supercells. Ice V (monoclinic) can be transformed to orthogonal cells. Ice VI (tetragonal) and other orthogonal phases work natively.

---

## Hydrate Generation Flags

QuickIce can generate clathrate hydrate structures using the `--hydrate` flag. Hydrate structures are ice-like lattices that trap guest molecules (CH4, THF) in cages. The `-T` and `-P` flags are required to set the thermodynamic conditions for hydrate stability.

### `--hydrate`

Enable clathrate hydrate generation mode. When this flag is set, QuickIce generates a hydrate lattice instead of an ice structure.

**Required with:** `-T`, `-P` (temperature and pressure must be set for hydrate conditions)

**Incompatible with:** `--nmolecules` (hydrate uses `--supercell-x/y/z` for size control)

**Default:** Disabled (ice generation mode)

```bash
# sI CH4 hydrate at 250K, 0.1 MPa
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sI --guest CH4
```

---

### `--lattice-type`

Hydrate lattice type. Determines the cage structure and guest molecule arrangement.

**Choices:** `sI`, `sII`, `sH`, `c0te`, `c1te`, `c2te`, `ice1hte`, `sTprime`, `16`, `17` (10 total)

**Default:** `sI`

| Choice | Description | Cage Keys | Water-Only | Triclinic |
|--------|-------------|-----------|------------|-----------|
| `sI` | Structure I hydrate | `small`, `large` | No | No |
| `sII` | Structure II hydrate | `small`, `large` | No | No |
| `sH` | Structure H hydrate | `small`, `medium`, `large` | No | Yes |
| `c0te` | Filled ice C0 (Teeratchanan 2015) | `small` | No | Yes |
| `c1te` | Filled ice C1 (Teeratchanan 2015) | `small` | No | Yes |
| `c2te` | Filled ice C2 (Teeratchanan 2015) | `small` | No | No |
| `ice1hte` | Filled ice Ih (Teeratchanan 2015) | `small` | No | No |
| `sTprime` | Filled ice sT′ (Smirnov 2013) | — (no cages) | Yes | No |
| `16` | Ice XVI (empty sII framework) | `small`, `large` | No | No |
| `17` | Ice XVII (ultralow density) | — (no cages) | Yes | No |

**Required with:** `--hydrate`

**Notes:**

- **Triclinic types** (`c0te`, `c1te`): Blocked when used with `--interface` (produces an error — these filled-ice structures have triclinic cells with off-diagonal elements that cannot be transformed into an orthogonal supercell). Hydrate-only export is supported. Note that `sH` is marked triclinic for data accuracy but is **not** blocked in interface generation.
- **Water-only types** (`sTprime`, `17`): Ignore `--guest` and `--cage-guest` (there are no cages to fill). They generate pure water frameworks.
- **Filled ices** (`c0te`, `c1te`, `c2te`, `ice1hte`): Use cage key `small` (NOT `guest`) with `--cage-guest`. The `cage_type_map` for these lattices has a single `small` key (mapped to the GenIce2 cage id `Ne1`). See the `--cage-guest` filled-ice gotcha below.

```bash
# Structure II hydrate with THF guest
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sII --guest THF

# Structure H hydrate with CH4
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sH --guest CH4

# Filled ice C0 (hydrate-only export; not compatible with --interface)
python -m quickice -T 250 -P 50 --hydrate --lattice-type c0te --guest CH4

# Water-only sT′ (ignores --guest / --cage-guest)
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sTprime
```

---

### `--guest`

> **⚠️ DEPRECATED:** Use `--cage-guest` for mixed cage occupancy. `--guest` is kept for backward compatibility with no behavior change.

Guest molecule type trapped in the hydrate cages. The guest molecule determines the hydrate stability and cage occupancy.

**Choices:** `CH4`, `THF`

**Default:** `CH4`

| Guest | Atoms | Typical Lattice | Notes |
|-------|-------|-----------------|-------|
| `CH4` | 5 (C + 4H) | sI, sH | Small guest; fits in small and large cages |
| `THF` | 13 (C₄H₈O) | sII | Large guest; occupies large cages only |

**Required with:** `--hydrate`

```bash
# Methane hydrate (sI)
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sI --guest CH4

# THF hydrate (sII)
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sII --guest THF
```

> **Custom guest:** Custom guest upload in hydrate is GUI-only for v4.7. There is no CLI flag for custom guest upload; the CLI `--guest` and `--cage-guest` flags support the built-in `CH4`/`THF` guests only.

---

### `--supercell-x`, `--supercell-y`, `--supercell-z`

Supercell repetition counts in each Cartesian direction. These control the size of the generated hydrate structure.

**Type:** Integer (default: 1 for each)

**Valid range:** 1 or greater

**Note:** Mutually exclusive with `--nmolecules` in hydrate mode. Use these flags instead of `--nmolecules` to control hydrate size.

```bash
# 2×2×2 supercell of sI CH4 hydrate (8× unit cell)
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sI --guest CH4 \
  --supercell-x 2 --supercell-y 2 --supercell-z 2

# 3×1×1 supercell (elongated along X)
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sI --guest CH4 \
  --supercell-x 3 --supercell-y 1 --supercell-z 1
```

---

### `--cage-occupancy-small`

> **⚠️ DEPRECATED:** Use `--cage-guest` for mixed cage occupancy. This flag is kept for backward compatibility with no behavior change.

Occupancy percentage for small cages (0–100%). Controls what fraction of small cages contain guest molecules.

**Type:** Float (default: 100.0)

**Valid range:** 0.0 to 100.0

**Required with:** `--hydrate`

```bash
# Partial occupancy: 80% small cages filled, 95% large cages filled
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sI --guest CH4 \
  --cage-occupancy-small 80.0 --cage-occupancy-large 95.0
```

---

### `--cage-occupancy-large`

> **⚠️ DEPRECATED:** Use `--cage-guest` for mixed cage occupancy. This flag is kept for backward compatibility with no behavior change.

Occupancy percentage for large cages (0–100%). Controls what fraction of large cages contain guest molecules.

**Type:** Float (default: 100.0)

**Valid range:** 0.0 to 100.0

**Required with:** `--hydrate`

```bash
# Full occupancy (default)
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sI --guest CH4

# Partial occupancy
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sI --guest CH4 \
  --cage-occupancy-small 80.0 --cage-occupancy-large 95.0
```

---

### `--cage-guest`

Per-cage-type guest assignment (repeatable). Allows mixed cage occupancy — different guest types in different cage types with independent occupancy percentages.

**Format:** `KEY=GUEST:OCC` (repeatable)

**Parameters:**
- `KEY` — A `cage_type_map` key: `small`, `medium`, `large`, or `guest`
- `GUEST` — Guest molecule: `CH4` or `THF` (built-in only on CLI for v4.7)
- `OCC` — Occupancy percentage: 0-100

**Default:** None. When supplied, overrides `--guest`/`--cage-occupancy-small`/`--cage-occupancy-large`.

**Required with:** `--hydrate`

```bash
# Mixed occupancy: CH4 in small cages (60%) + THF in large cages (100%)
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sI \
  --cage-guest small=CH4:60 --cage-guest large=THF:100

# sH with 3 cage types
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sH \
  --cage-guest small=CH4:100 --cage-guest medium=CH4:50 --cage-guest large=THF:100
```

> **Filled-ice gotcha:** For filled ices (`c0te`, `c1te`, `c2te`, `ice1hte`), use cage key `small` (NOT `guest`). These lattices have a single `cage_type_map` entry keyed `small` (mapped to the GenIce2 cage id `Ne1`). Using `--cage-guest guest=CH4:100` produces 0 guests.

> **Custom guest:** Custom guest upload in hydrate is GUI-only for v4.7. The CLI `--cage-guest` flag supports the built-in `CH4`/`THF` guests only.

---

### `--depol`

Depolarization mode for hydrate generation.

**Choices:** `strict`, `optimal`

**Default:** `strict`

- **`strict`** — Ice rules enforced, zero net dipole (default; preserves standard behavior)
- **`optimal`** — Relaxed dipole optimization

**Required with:** `--hydrate`

```bash
# Strict depol (default)
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sI --depol strict

# Optimal depol
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sI --depol optimal
```

> **Note:** In GenIce2 2.2.13.1, `strict` and `optimal` produce identical atom counts. The depol mode affects H-bond orientation during generation, not the number of atoms.

---

### v4.7 Hydrate Examples

Comprehensive examples combining the v4.7 hydrate flags (`--lattice-type`, `--cage-guest`, `--depol`):

```bash
# Extended lattice type (filled ice C0)
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type c0te --cage-guest small=CH4:100

# Water-only lattice (no guests)
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sTprime

# Mixed cage occupancy (CH4 in small + THF in large)
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sI \
  --cage-guest small=CH4:60 --cage-guest large=THF:100

# sH with 3 cage types
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sH \
  --cage-guest small=CH4:100 --cage-guest medium=CH4:50 --cage-guest large=THF:100

# Depol mode (optimal)
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type sI \
  --cage-guest small=CH4:100 --depol optimal

# Ice XVI (empty sII framework, 16)
python -m quickice -T 250 -P 0.1 --hydrate --lattice-type 16
```

> **Filled-ice gotcha:** For filled ices (`c0te`, `c1te`, `c2te`, `ice1hte`), use cage key `small` (NOT `guest`) with `--cage-guest`. See the [`--cage-guest` filled-ice gotcha](#--cage-guest) above.

---

## Custom Molecule Insertion Flags

Custom molecule insertion allows placing user-provided molecules into the liquid region of an interface structure. This requires both a GROMACS coordinate file (`.gro`) and a topology file (`.itp`). See [GRO/ITP Guide](gro-itp-guide.md) for file preparation.

### `--custom-gro`

Path to a custom molecule GROMACS coordinate file (`.gro`). Required for custom molecule insertion.

**Type:** String (file path)

**Extension:** Must end in `.gro` (case-insensitive)

**Default:** None

**Required with:** `--custom-itp`, `--interface`

**Incompatible without:** `--interface` (custom molecules require an interface structure)

```bash
# Insert ethanol molecules from etoh.gro
python -m quickice -T 250 -P 0.1 --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --custom-gro quickice/data/custom/etoh.gro \
  --custom-itp quickice/data/custom/etoh.itp \
  --custom-placement random --custom-count 5
```

---

### `--custom-itp`

Path to a custom molecule GROMACS topology file (`.itp`). Defines the force field parameters for the custom molecule. Must be provided together with `--custom-gro`.

**Type:** String (file path)

**Extension:** Must end in `.itp` (case-insensitive)

**Default:** None

**Required with:** `--custom-gro`

```bash
# Both GRO and ITP are required together
python -m quickice -T 250 -P 0.1 --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --custom-gro my_molecule.gro \
  --custom-itp my_molecule.itp \
  --custom-placement random --custom-count 3
```

---

### `--custom-placement`

Placement mode for custom molecules in the liquid region.

**Choices:** `random`, `custom`

**Default:** `random`

| Mode | Description | Additional Required Flags |
|------|-------------|--------------------------|
| `random` | Random placement with overlap checking | `--custom-count` or `--custom-concentration` |
| `custom` | User-specified positions from CSV file | `--custom-positions-file` |

```bash
# Random placement by count
python -m quickice -T 250 -P 0.1 --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --custom-gro quickice/data/custom/etoh.gro \
  --custom-itp quickice/data/custom/etoh.itp \
  --custom-placement random --custom-count 5

# Custom placement from CSV
python -m quickice -T 250 -P 0.1 --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --custom-gro quickice/data/custom/etoh.gro \
  --custom-itp quickice/data/custom/etoh.itp \
  --custom-placement custom \
  --custom-positions-file custom_positions.csv
```

---

### `--custom-count`

Number of custom molecules to insert. Used with `--custom-placement random` mode.

**Type:** Integer

**Default:** None

**Mutually exclusive with:** `--custom-concentration` (use one or the other)

**Required with:** `--custom-placement random` (if `--custom-concentration` not set)

```bash
# Insert 5 ethanol molecules
python -m quickice -T 250 -P 0.1 --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --custom-gro quickice/data/custom/etoh.gro \
  --custom-itp quickice/data/custom/etoh.itp \
  --custom-placement random --custom-count 5
```

---

### `--custom-concentration`

Custom molecule concentration in mol/L. Used with `--custom-placement random` mode. The number of molecules is calculated from concentration and liquid volume.

**Type:** Float (0.0–5.0 mol/L)

**Default:** None

**Mutually exclusive with:** `--custom-count` (use one or the other)

**Required with:** `--custom-placement random` (if `--custom-count` not set)

```bash
# Insert ethanol at 0.5 mol/L concentration
python -m quickice -T 250 -P 0.1 --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --custom-gro quickice/data/custom/etoh.gro \
  --custom-itp quickice/data/custom/etoh.itp \
  --custom-placement random --custom-concentration 0.5
```

---

### `--custom-positions-file`

Path to a CSV file specifying custom molecule positions and orientations. Required when `--custom-placement custom` is set.

**Type:** String (file path)

**Default:** None

**Required with:** `--custom-placement custom`

**CSV format:** Each row contains `x, y, z, alpha, beta, gamma` (position in nm, Euler angles in degrees)

```bash
# Place molecules at positions from CSV
python -m quickice -T 250 -P 0.1 --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --custom-gro quickice/data/custom/etoh.gro \
  --custom-itp quickice/data/custom/etoh.itp \
  --custom-placement custom \
  --custom-positions-file quickice/data/examples/custom_positions.csv
```

---

## Solute Insertion Flags

Solute insertion places small predefined molecules (CH4, THF) into the liquid region of an interface structure. Unlike custom molecules, solutes use built-in force field parameters (GAFF2) and do not require separate GRO/ITP files.

### `--solute-type`

Solute molecule type to insert into the liquid region.

**Choices:** `CH4`, `THF`

**Default:** None (no solute insertion)

**Required with:** `--solute-concentration`, `--interface`

| Solute | Atoms | Force Field | Notes |
|--------|-------|-------------|-------|
| `CH4` | 5 | GAFF2 (c3, hc) | Methane — small nonpolar molecule |
| `THF` | 13 | GAFF2 (os, c5, h1) | Tetrahydrofuran — larger cyclic ether |

```bash
# CH4 solute at 0.3 mol/L
python -m quickice -T 250 -P 0.1 --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --solute-type CH4 --solute-concentration 0.3

# THF solute at 0.5 mol/L
python -m quickice -T 250 -P 0.1 --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --solute-type THF --solute-concentration 0.5
```

---

### `--solute-concentration`

Solute concentration in mol/L. Required when `--solute-type` is set.

**Type:** Float (0.0–5.0 mol/L)

**Default:** None

**Required with:** `--solute-type`

```bash
python -m quickice -T 250 -P 0.1 --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --solute-type CH4 --solute-concentration 0.3
```

---

### `--solute-source`

Source structure for solute insertion. Determines which liquid region receives the solute molecules.

**Choices:** `interface`, `custom`

**Default:** `interface`

| Source | Description | Required Flags |
|--------|-------------|----------------|
| `interface` | Insert solutes into the interface liquid region (default) | `--interface` |
| `custom` | Insert solutes using custom molecule coordinates as source | `--custom-gro`, `--interface` |

**Required with:** `--solute-type`

**Conditional requirement:** `--solute-source custom` requires `--custom-gro`

```bash
# Solute from interface source (default)
python -m quickice -T 250 -P 0.1 --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --solute-type CH4 --solute-concentration 0.3

# Solute from custom molecule source
python -m quickice -T 250 -P 0.1 --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --custom-gro quickice/data/custom/etoh.gro \
  --custom-itp quickice/data/custom/etoh.itp \
  --custom-placement random --custom-concentration 0.3 \
  --solute-type CH4 --solute-concentration 0.15 --solute-source custom
```

---

## Ion Insertion Flags

Ion insertion adds Na⁺/Cl⁻ ions (Madrid2019 parameters) to the liquid region for charge screening or salt solution simulations. Ions are always added in equal numbers to maintain charge neutrality.

### `--ion-concentration`

Ion concentration in mol/L. Specifies the NaCl concentration; equal numbers of Na⁺ and Cl⁻ ions are inserted.

**Type:** Float (0.0–5.0 mol/L)

**Default:** None (no ion insertion)

**Required with:** `--interface`

**Note:** Madrid2019 ion model with charges ±0.85e (not ±1.0e). See [Madrid2019 reference](https://doi.org/10.1063/1.5121392).

```bash
# 0.15 M NaCl (physiological concentration)
python -m quickice -T 250 -P 0.1 --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --ion-concentration 0.15

# 0.5 M NaCl
python -m quickice -T 250 -P 0.1 --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --ion-concentration 0.5
```

---

### `--ion-source`

Source structure for ion insertion. Determines which coordinates define the liquid region for ion placement.

**Choices:** `interface`, `custom`, `solute`

**Default:** `interface`

| Source | Description | Required Flags |
|--------|-------------|----------------|
| `interface` | Insert ions into interface liquid region (default) | `--interface` |
| `custom` | Insert ions using custom molecule coordinates as source | `--custom-gro`, `--interface` |
| `solute` | Insert ions using solute coordinates as source | `--solute-type`, `--interface` |

**Conditional requirements:**
- `--ion-source custom` requires `--custom-gro`
- `--ion-source solute` requires `--solute-type`

```bash
# Ions from interface source (default)
python -m quickice -T 250 -P 0.1 --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --ion-concentration 0.15

# Ions from custom molecule source
python -m quickice -T 250 -P 0.1 --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --custom-gro quickice/data/custom/etoh.gro \
  --custom-itp quickice/data/custom/etoh.itp \
  --custom-placement random --custom-concentration 0.3 \
  --ion-concentration 0.15 --ion-source custom

# Ions from solute source
python -m quickice -T 250 -P 0.1 --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --solute-type CH4 --solute-concentration 0.3 \
  --ion-concentration 0.15 --ion-source solute
```

---

## Validation Rules

All inputs are validated before processing:

- **Temperature:** Must be between 0 and 500 K
- **Pressure:** Must be between 0 and 10000 MPa
- **Nmolecules:** Must be between 4 and 100000
- **Box dimension:** Must be ≥1.0 nm (no upper bound enforced)
- **Concentration:** Must be in 0.0–5.0 mol/L range
- **Cage occupancy:** Must be in 0.0–100.0% range
- **File extension:** `--custom-gro` must end in `.gro`, `--custom-itp` must end in `.itp`
- **Positive float:** Numeric inputs must be positive real numbers

Invalid inputs will cause immediate exit with an error message.

---

## Pipeline Mode vs Ice-Only Output

QuickIce has two main operating modes with different output behavior:

### File Naming

| Aspect | Pipeline Mode | Ice-Only Mode |
|--------|--------------|---------------|
| GRO file | Step-specific names (e.g., `ion.gro`, `solute.gro`) | `{ice_type}.gro` |
| TOP file | Step-specific names (e.g., `ion.top`) | Not generated by default |
| ITP files | Multiple molecule-type files (e.g., `tip4p-ice.itp`, `ion.itp`, custom `.itp`) | Not generated by default |

### Topology Structure

| Aspect | Pipeline Mode | Ice-Only Mode |
|--------|--------------|---------------|
| `[molecules]` section | Includes multiple molecule types (SOL, ion, custom, solute) | Includes SOL only |
| `[atomtypes]` section | Includes all molecule atom types | Not generated by default |

### GROMACS Export

| Aspect | Pipeline Mode | Ice-Only Mode |
|--------|--------------|---------------|
| File generation | Always produces `.gro`, `.top`, and `.itp` files | Requires `--gromacs` flag |
| Flag effect | `--gromacs` has no effect (files always generated) | `--gromacs` triggers GROMACS file output |

### Phase Diagrams

| Aspect | Pipeline Mode | Ice-Only Mode |
|--------|--------------|---------------|
| Diagram generation | Does not generate phase diagrams | Generates PNG diagram by default |
| `--no-diagram` flag | Has no effect (diagrams not generated) | Suppresses diagram generation |

---

## Output Files

### PDB Files

Each candidate is saved as a separate PDB file:

```
output/ice_candidate_01.pdb  # Best-ranked structure
output/ice_candidate_02.pdb  # Second-best
output/ice_candidate_03.pdb  # Third-best
...
```

### Phase Diagram

A PNG image showing the water phase diagram with a marker at your input conditions:

```
output/phase_diagram.png
```

---

## Common Issues

### "No phase found for given conditions"

The input temperature and pressure combination does not fall within any known ice phase region. Check the phase diagram or try conditions closer to known stable regions.

### "Invalid temperature/pressure/nmolecules"

Input values are outside the valid range. Check the validation rules above.

---

## Validation

QuickIce validates generated structures using spglib for crystal
symmetry analysis:

- Repository: https://github.com/atztogo/spglib
- Paper: "Spglib: a software library for crystal symmetry search"
- DOI: https://doi.org/10.1080/27660400.2024.2384822

---

## Unified Entry Point

QuickIce uses `python -m quickice` as the canonical invocation. When run without arguments, it displays a help message (similar to `git` with no arguments).

```bash
# Show help
python -m quickice

# Run CLI mode (implicit when computation flags are present)
python -m quickice -T 300 -P 0.1 -N 100

# Run GUI mode (when display is available)
python -m quickice --gui
```

The backward-compatible `python quickice.py` invocation also works.

### Routing Behavior

| Input | Mode | Behavior |
|-------|------|----------|
| No arguments | Help | Print usage and exit 0 |
| `--help` | Help | Print full argparse help and exit 0 |
| `--version` | Version | Print version and exit 0 |
| Computation flags (e.g., `-T`, `--interface`) | CLI | Implicit CLI mode |
| `--cli` + computation flags | CLI | Explicit CLI mode, skip PySide6 import |
| `--cli` alone | CLI (error) | Missing required `--temperature` |
| `--gui` | GUI | Launch GUI (error if no display or PySide6) |
| `--cli` + `--gui` | GUI | `--gui` takes priority over `--cli` |

**Priority:** `--gui` > `--cli` > computation flags (→CLI) > no arguments (→help). When both `--cli` and `--gui` are specified, `--gui` takes priority and the GUI is launched.

---

## Mode Selection

### `--cli`

Force CLI mode and skip PySide6 import entirely. Useful in headless or CI environments where GUI libraries are not available.

```bash
# CLI mode with explicit flag
python -m quickice --cli -T 300 -P 0.1 -N 100

# CLI mode is implicit when computation flags are present
python -m quickice -T 300 -P 0.1 -N 100
```

Note: `--cli` alone (without computation flags) triggers an argparse error because `--temperature` is required for CLI mode.

### `--gui`

Force GUI mode. Requires PySide6 and a display server. If PySide6 is not installed or no display is available, exits with an error.

```bash
# Launch GUI explicitly
python -m quickice --gui
```

Error messages:
- PySide6 missing: "Error: --gui requested but PySide6 is not installed." + installation hint
- No display: "Error: --gui requested but no display is available."

For direct GUI launch without routing: `python -m quickice.gui`

---

## Platform Invocation

| Platform | Command |
|----------|---------|
| Source install | `python -m quickice [options]` |
| Binary (Linux/macOS) | `quickice-gui [options]` |
| Binary (Windows) | `quickice-gui.exe [options]` |

Windows users: append `.exe` to the binary name. All flags are identical across platforms.

### Backward Compatibility

The `python quickice.py` invocation continues to work for source installations. It delegates to the same unified router as `python -m quickice`.

---

## Example Scripts

The `scripts/` directory includes ready-made example scripts for common workflows:

### CLI Examples (`scripts/cli-examples.sh`)

A comprehensive reference script showing example commands for **every possible CLI flag combination**, organized by feature area:

- Ice generation (8 phases with realistic T/P values)
- Interface generation (slab, pocket, piece modes — see [Interface Generation](#interface-generation))
- Hydrate generation (sI, sII, sH with guest options — see [Hydrate Generation Flags](#hydrate-generation-flags))
- Custom molecule insertion (random and custom placement — see [Custom Molecule Insertion Flags](#custom-molecule-insertion-flags))
- Solute insertion (CH4, THF with source selection — see [Solute Insertion Flags](#solute-insertion-flags))
- Ion insertion (3 source modes — see [Ion Insertion Flags](#ion-insertion-flags))
- Full workflow chains (F1 and F4)
- Mode flags (--cli, --gui, --help)

All commands are commented out for safety — uncomment only the ones you want to run.

```bash
# View the script
cat scripts/cli-examples.sh

# Run it (just shows the reference message)
./scripts/cli-examples.sh
```

### Hydrate-Interface-Custom-Ion Workflow (`scripts/hydrate-interface-custom-ion.sh`)

A runnable workflow script that demonstrates the hydrate→interface→custom molecule→ion pipeline. See [GRO/ITP Guide](gro-itp-guide.md) for custom molecule file preparation.

```bash
# Run with default ethanol molecule and ion concentration
./scripts/hydrate-interface-custom-ion.sh \
  --custom-gro quickice/data/custom/etoh.gro \
  --custom-itp quickice/data/custom/etoh.itp

# Custom ion concentration and temperature
./scripts/hydrate-interface-custom-ion.sh \
  --custom-gro my_molecule.gro \
  --custom-itp my_molecule.itp \
  --ion-conc 0.5 \
  --temperature 270
```

---

## See Also

- [Ranking Methodology](./ranking.md) - How candidates are scored and ranked
- [Principles](./principles.md) - QuickIce philosophy and approach
- [TIP4P-ice Reference](https://doi.org/10.1063/1.1931662) - TIP4P-ice reference

