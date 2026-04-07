# QuickIce CLI Reference

Complete documentation for QuickIce command-line interface.

## Usage

```bash
python quickice.py --temperature <T> --pressure <P> --nmolecules <N> [options]
```

## Required Arguments

### `--temperature`, `-T`

Temperature in Kelvin (0-500K). This argument is required.

**Valid range:** 0 to 500 K

**Examples:**
```bash
# Ice Ih (ambient conditions)
python quickice.py -T 260 -P 0.1 -N 100

# High temperature
python quickice.py --temperature 300 --pressure 100 --nmolecules 50
```

---

### `--pressure`, `-P`

Pressure in MPa (0-10000 MPa). This argument is required.

**Valid range:** 0 to 10000 MPa (0 to 10 GPa)

**Examples:**
```bash
# Ice III (moderate pressure)
python quickice.py -T 250 -P 250 -N 100

# Ice VII (very high pressure)
python quickice.py -T 300 -P 2500 -N 50
```

---

### `--nmolecules`, `-N`

Number of water molecules in the generated structure (4-100000). This argument is required.

**Valid range:** 4 to 100000 molecules

**Examples:**
```bash
# Small test structure
python quickice.py -T 260 -P 0.1 -N 50

# Larger structure for better statistics
python quickice.py -T 260 -P 0.1 -N 1000
```

---

## Optional Arguments

### `--output`, `-o`

Output directory for generated PDB files and phase diagram. Default: `output`

**Usage:**
```bash
python quickice.py -T 260 -P 0.1 -N 100 --output my_structures
```

The output directory will contain:
- `candidate_*.pdb` - Ranked ice structure candidates in PDB format
- `phase_diagram.png` - Phase diagram showing input conditions

---

### `--no-diagram`

Disable phase diagram generation. By default, QuickIce generates a phase diagram with a marker showing the input conditions.

**Usage:**
```bash
python quickice.py -T 260 -P 0.1 -N 100 --no-diagram
```

Use this flag when you only need the PDB output files and want to save time.

---

### `--gromacs`, `-g`

Export structure in GROMACS format (.gro, .top, .itp files).

**Usage:**
```bash
# Export all candidates with shared top/itp files
python quickice.py -T 250 -P 100 -N 128 --gromacs --output ice_gro

# Export specific ranked candidate
python quickice.py -T 250 -P 100 -N 128 --gromacs --candidate 2
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
# Export the top-ranked candidate (default)
python quickice.py -T 250 -P 100 -N 128 --gromacs

# Export the second-ranked candidate
python quickice.py -T 250 -P 100 -N 128 --gromacs --candidate 2
```

Default: 1 (top-ranked structure)

---

### `--version`, `-V`

Display the current QuickIce version.

**Usage:**
```bash
python quickice.py --version
# Output: python quickice.py 0.1.0
```

---

## Ice Phase Examples

QuickIce supports 12 ice polymorphs. Below are example commands for generating structures in different ice phases:

### Ice Ih (Hexagonal Ice)

The most common form of ice, stable at ambient pressure and temperatures below 273K.

```bash
python quickice.py -T 260 -P 0.1 -N 100
```

**Phase region:** Low pressure (< 200 MPa), moderate temperature (200-273K)

---

### Ice Ic (Cubic Ice)

Cubic form of ice, metastable at ambient pressure.

```bash
python quickice.py -T 200 -P 0.1 -N 100
```

**Phase region:** Low pressure (< 200 MPa), low temperature (< 200K)

---

### Ice II

Ordered form of ice, stable at moderate pressures.

```bash
python quickice.py -T 200 -P 300 -N 100
```

**Phase region:** Moderate pressure (200-500 MPa), low temperature (< 250K)

---

### Ice III

Tetragonal ice, stable at moderate pressures.

```bash
python quickice.py -T 250 -P 250 -N 100
```

**Phase region:** Moderate pressure (200-400 MPa), moderate temperature (250-270K)

---

### Ice V

Complex monoclinic structure.

```bash
python quickice.py -T 260 -P 450 -N 100
```

**Phase region:** Higher pressure (400-600 MPa), moderate temperature (240-270K)

---

### Ice VI

First high-pressure phase with two independent networks.

```bash
python quickice.py -T 280 -P 700 -N 100
```

**Phase region:** High pressure (600-2000 MPa), moderate temperature (270-350K)

---

### Ice VII

Cubic high-pressure phase with two interpenetrating networks.

```bash
python quickice.py -T 300 -P 2500 -N 100
```

**Phase region:** Very high pressure (> 2000 MPa), any temperature up to 355K

---

### Ice VIII

Ordered form of Ice VII, stable at lower temperatures.

```bash
python quickice.py -T 200 -P 2500 -N 100
```

**Phase region:** Very high pressure (> 2000 MPa), low temperature (< 278K)

---

### Ice IX

Proton-ordered form of Ice III.

```bash
python quickice.py -T 130 -P 280 -N 100
```

**Phase region:** Moderate pressure (200-400 MPa), very low temperature (< 140K)

---

### Ice X

Symmetric hydrogen bonds at extreme pressure.

```bash
python quickice.py -T 300 -P 35000 -N 100
```

**Phase region:** Extreme pressure (> 30000 MPa / 30 GPa)

---

### Ice XI

Proton-ordered form of Ice Ih, stable at very low temperatures.

```bash
python quickice.py -T 60 -P 0.1 -N 100
```

**Phase region:** Low pressure (< 200 MPa), very low temperature (< 72K)

---

### Ice XV

Proton-ordered form of Ice VI.

```bash
python quickice.py -T 100 -P 1100 -N 100
```

**Phase region:** Moderate-high pressure (1000-1500 MPa), low temperature (80-108K)

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Invalid arguments (validation error) |
| 2 | Phase mapping error (conditions outside known regions) |
| 3 | Structure generation error |

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

## See Also

- [Ranking Methodology](./ranking.md) - How candidates are scored and ranked
- [Principles](./principles.md) - QuickIce philosophy and approach
- [TIP4P-ice Reference](https://doi.org/10.1063/1.1931662) - TIP4P-ice reference

