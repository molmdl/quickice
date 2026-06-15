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

### `--version`, `-V`

Display the current QuickIce version.

**Usage:**
```bash
python -m quickice --version
# Output: python -m quickice 4.5.0
```

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
| 1 | Invalid arguments (validation error) |
| 2 | Phase mapping error (conditions outside known regions) |
| 3 | Structure generation error |

---

## Interface Generation

QuickIce can generate ice-water interface structures directly from the command line using the `--interface` flag. This is useful for batch processing or scripting.

### Interface Mode

The `--mode` parameter specifies the interface geometry:

| Mode | Description | Required Parameters |
|------|-------------|---------------------|
| `slab` | Layered ice-water interface | `--ice-thickness`, `--water-thickness` |
| `pocket` | Water cavity within ice matrix | `--pocket-diameter` |
| `piece` | Ice crystal embedded in water | None (dimensions from candidate) |

### Box Dimensions

All interface modes require box dimensions:

- `--box-x`, `--box-y`, `--box-z`: Simulation box dimensions in nanometers (1.0–100 nm)

**Slab mode constraint:** Box Z must equal `2 × ice_thickness + water_thickness`.

### Common Parameters

| Option | Default | Description |
|--------|---------|-------------|
| `--seed` | 42 | Random seed for reproducible water placement |
| `--gromacs` | False | Export GROMACS format (.gro, .top, .itp) |

### Slab Interface Example

Generate a layered ice-water-ice slab:

```bash
python -m quickice --temperature 250 --pressure 0.1 \
  --interface --mode slab \
  --box-x 5.0 --box-y 5.0 --box-z 10.0 \
  --ice-thickness 3.0 --water-thickness 4.0 \
  --gromacs --output slab_output
```

Creates two ice layers (3.0 nm each) with a 4.0 nm water layer between them.

### Pocket Interface Example

Generate a water cavity within ice:

```bash
python -m quickice --temperature 253 --pressure 500 \
  --interface --mode pocket \
  --box-x 4.0 --box-y 4.0 --box-z 4.0 \
  --pocket-diameter 2.0 \
  --gromacs --output pocket_output
```

Creates a 2.0 nm spherical water pocket inside an Ice V matrix.

### Piece Interface Example

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

## Validation Rules

All inputs are validated before processing:

- **Temperature:** Must be between 0 and 500 K
- **Pressure:** Must be between 0 and 10000 MPa
- **Nmolecules:** Must be between 4 and 100000

Invalid inputs will cause immediate exit with an error message.

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

**Priority:** `--gui` > computation flags (→CLI) > no arguments (→help)

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
- Interface generation (slab, pocket, piece modes)
- Hydrate generation (sI, sII, sH with guest options)
- Custom molecule insertion (random and custom placement)
- Solute insertion (CH4, THF with source selection)
- Ion insertion (3 source modes)
- Full workflow chains (F1–F4)
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

