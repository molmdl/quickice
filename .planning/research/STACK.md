# Stack Research

**Domain:** ML-based ice structure generation
**Researched:** 2026-03-26
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| NumPy | 2.4.x | Numerical array computing | Foundation of scientific Python for coordinates, lattices |
| SciPy | 1.17.x | Scientific computing | Distance calculations, geometry, optimization |
| spglib-python | 2.7.x | Crystal symmetry detection | Standard library for space groups and crystal validation |
| Click | 8.3.x | CLI framework | Industry standard, auto-help, composable subcommands |
| PyYAML | 6.0.x | Configuration handling | For reading presets and templates |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| GenIce | 2.x | Ice structure generation | Coordinate generation pipeline |
| networkx | 3.x | Graph operations | Hydrogen bond network analysis |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | Unit testing | Standard Python testing |
| pytest-cov | Coverage reporting | Track test coverage |

## Installation

```bash
pip install numpy>=2.4.0 scipy>=1.17.0 spglib>=2.7.0 click>=8.3.0 pyyaml>=6.0 pytest>=8.3.0
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| NumPy + SciPy | ASE | ASE is heavier; use only for complex format conversion |
| Click | argparse | Click provides better DX for complex CLIs |
| spglib | ase.spacegroup | spglib is more widely used and maintained |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| TensorFlow | Heavy (~500MB), complex for inference | NumPy for simple ML, PyTorch if training needed |
| MDAnalysis | Full MD toolkit overkill | Custom PDB parser |
| Keras | Requires TensorFlow | Standalone if needed |

## Stack Patterns by Variant

**If neural network-based generation required:**
- Add PyTorch 2.11.x for inference
- Because: Efficient tensor operations

**If pre-trained model inference only:**
- Use NumPy-based inference
- Because: Minimal dependencies, faster startup

## Version Compatibility

| Package | Python Version | Notes |
|---------|----------------|-------|
| NumPy 2.4.x | Python 3.10+ | Current stable |
| SciPy 1.17.x | Python 3.10+ | Current stable |
| spglib 2.7.x | Python 3.9+ | Works with Python 3.9-3.13 |
| Click 8.3.x | Python 3.8+ | LTS version |

## Sources

- NumPy 2.4.0 Release Notes
- SciPy 1.17.0 Documentation
- Spglib GitHub v2.7.0
- Click Documentation v8.3.1

---
*Stack research for: ML-based ice structure generation*
*Researched: 2026-03-26*
