# External Integrations

**Analysis Date:** 2026-03-28

## APIs & External Services

**None detected.**
- No external API calls
- No web services consumed
- No cloud platform integrations
- This is a self-contained scientific computing tool

## Scientific Libraries as "Integrations"

**GenIce (Ice Structure Generation):**
- Package: `genice2`, `genice-core`
- Purpose: Generate physically valid ice crystal structures
- Integration pattern: Plugin system via `genice2.plugin.safe_import()`
- Used in: `quickice/structure_generation/generator.py`
- Example usage:
  ```python
  from genice2.plugin import safe_import
  from genice2.genice import GenIce
  
  lattice = safe_import("lattice", "ice1h").Lattice()
  ice = GenIce(lattice, density=0.9167, reshape=supercell_matrix)
  water = safe_import("molecule", "tip3p").Molecule()
  formatter = safe_import("format", "gromacs").Format()
  gro_string = ice.generate_ice(formatter=formatter, water=water, depol="strict")
  ```
- Supported lattices: ice1h, ice1c, ice2, ice3, ice5, ice6, ice7, ice8

**IAPWS (Water/Steam Properties):**
- Package: `iapws`
- Purpose: International standard thermodynamic properties for water
- Used in: `quickice/output/phase_diagram.py`
- Example usage:
  ```python
  from iapws import IAPWS97
  st = IAPWS97(T=T, x=0)  # saturated liquid
  pressure = st.P
  ```
- Note: IAPWS equations also implemented directly in `melting_curves.py` (Simon-Glatzel form)

**spglib (Crystal Symmetry):**
- Package: `spglib`
- Purpose: Space group detection for crystal structures
- Used in: `quickice/output/validator.py`
- Example usage:
  ```python
  import spglib
  dataset = spglib.get_symmetry_dataset((lattice, positions, atom_types), symprec=1e-4)
  spacegroup_number = dataset.number
  spacegroup_symbol = dataset.international
  ```

## Data Storage

**Databases:**
- None - No database connectivity

**File Storage:**
- Local filesystem only
- Output directory: `output/` (created at runtime)
- Generated files:
  - PDB files: `ice_candidate_01.pdb`, `ice_candidate_02.pdb`, etc.
  - Phase diagram: `phase_diagram.png`, `phase_diagram.svg`, `phase_diagram_data.txt`

**Caching:**
- None - No caching layer

## Authentication & Identity

**Auth Provider:**
- None - No authentication required
- Single-user local application

## Monitoring & Observability

**Error Tracking:**
- None - Standard Python exception handling

**Logs:**
- Standard library `logging` module
- Used in: `quickice/output/orchestrator.py`
- Pattern: `logging.warning()` for non-critical issues

## CI/CD & Deployment

**Hosting:**
- None - Local development tool

**CI Pipeline:**
- None detected - No `.github/`, `.gitlab-ci.yml`, or similar

**Version Control:**
- Git repository (`.git/` present)
- No hooks configured

## Environment Configuration

**Required env vars:**
- None - All configuration via command-line arguments

**Configuration files:**
- `env.yml` - Conda environment specification
- `setup.sh` - Shell script to activate environment and set PYTHONPATH
- `requirements-dev.txt` - Development dependencies (pytest)

**Secrets location:**
- None - No secrets or credentials required

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## File Format Integrations

**Input Formats:**
- None - User input via CLI arguments only

**Output Formats:**
- PDB (Protein Data Bank format) - Crystal structure coordinates
  - Writer: `quickice/output/pdb_writer.py`
  - Includes: `CRYST1` record for unit cell, `HETATM` records for atoms
- GRO (GROMACS format) - Intermediate format from GenIce
  - Parser: `quickice/structure_generation/generator.py:_parse_gro()`
  - Not written to output, only parsed internally
- PNG/SVG - Phase diagram visualization
- Plain text - Phase diagram data file

## Scientific Data Sources

**Built-in Data Tables:**
- Triple points: `quickice/phase_mapping/triple_points.py`
  - Source: IAPWS R14-08(2011), LSBU Water Phase Data
  - 12 triple point coordinates defined
- Melting curve coefficients: `quickice/phase_mapping/data/ice_boundaries.py`
  - Simon-Glatzel equation parameters for ice phases

**External Data:**
- None - All scientific data is embedded in code

---

*Integration audit: 2026-03-28*
