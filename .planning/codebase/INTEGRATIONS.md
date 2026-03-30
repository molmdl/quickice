# External Integrations

**Analysis Date:** 2026-03-30

## APIs & External Services

**None** - This is a standalone CLI application with no external API calls or network services.

## Scientific Libraries

**GenIce2 (genice2):**
- Purpose: Generate hydrogen-disordered ice crystal structures
- Integration: `quickice/structure_generation/generator.py`
- Usage: Plugin system via `safe_import("lattice", name)` and `safe_import("molecule", "tip3p")`
- Key classes: `GenIce` class for structure generation with density and supercell parameters
- Output format: GRO (GROMACS) internally, converted to PDB
- Reference: https://github.com/genice-dev/GenIce2

**IAPWS (iapws):**
- Purpose: Water/ice thermophysical properties per IAPWS standards
- Integration: `quickice/phase_mapping/melting_curves.py`, `quickice/output/phase_diagram.py`
- Usage: 
  - `IAPWS97(T=T, x=0)` - Saturated liquid properties for vapor-liquid curve
  - `melting_pressure(T, ice_type)` - Melting curve calculations per IAPWS R14-08
- Standards implemented:
  - IAPWS R14-08(2011) - Melting and sublimation curves
  - IAPWS R10-06(2009) - Thermodynamic properties
- Key functions: `ice_ih_melting_pressure`, `ice_iii_melting_pressure`, `ice_v_melting_pressure`, `ice_vi_melting_pressure`, `ice_vii_melting_pressure`

**spglib:**
- Purpose: Space group analysis and crystal symmetry operations
- Integration: `quickice/output/validator.py`
- Usage: `spglib.get_spacegroup()` for structure validation
- Validates generated ice structures have correct symmetry

## Data Storage

**Databases:**
- None - No database integration

**File Storage:**
- Local filesystem only
- Output directory configurable via `--output` CLI flag
- Default: `output/` directory (created if not exists)

**Caching:**
- None - No caching layer

## Internal Data Files

**Phase Boundary Data:**
- `quickice/phase_mapping/triple_points.py` - Triple point coordinates (T, P) for ice polymorphs
- `quickice/phase_mapping/melting_curves.py` - IAPWS R14-08 melting curve equations
- `quickice/phase_mapping/solid_boundaries.py` - Solid-solid phase boundary interpolations
- All data is embedded in Python code (no external data files)

**GenIce Lattices:**
- Uses GenIce2 plugin system to load lattice definitions
- Supported lattices: ice_ih, ice_ic, ice_ii, ice_iii, ice_v, ice_vi, ice_vii, ice_viii, ice_xi, ice_ix, ice_x, ice_xv
- Mapping: `quickice/structure_generation/mapper.py` - phase_id to GenIce lattice name

## Authentication & Identity

**None** - No authentication or identity management

## Monitoring & Observability

**Error Tracking:**
- None - Errors printed to stderr via `print(..., file=sys.stderr)`

**Logging:**
- Minimal logging via Python `logging` module in `quickice/output/orchestrator.py`
- No centralized logging configuration
- Errors handled via exceptions with descriptive messages

**Output Tracking:**
- Terminal STDOUT for progress and results
- Files written to output directory

## CI/CD & Deployment

**Hosting:**
- Standalone CLI tool - no deployment platform

**CI Pipeline:**
- None detected (no `.github/workflows/`, `.gitlab-ci.yml`, etc.)
- Tests runnable via `pytest`

## Environment Configuration

**Required env vars:**
- None - All configuration via CLI arguments

**PYTHONPATH:**
- Must include project root for imports to work
- Set by `setup.sh`: `export PYTHONPATH=/path/to/quickice`

**Conda Environment:**
- Environment name: `quickice`
- Create: `conda env create -f env.yml`
- Activate: `conda activate quickice`

## Webhooks & Callbacks

**Incoming:**
- None - CLI tool with no server component

**Outgoing:**
- None - No external notifications or callbacks

## Third-Party Data Sources

**Scientific Standards:**
- IAPWS R14-08(2011) - "Revised Release on the Pressure along the Melting and Sublimation Curves of Ordinary Water Substance"
  - URL: https://www.iapws.org/relguide/MeltSub.html
  - Implementation: `quickice/phase_mapping/melting_curves.py`
  
- Literature triple points - Used for solid-solid boundaries
  - LSBU Water Phase Data
  - IUPAC recommendations
  - Implementation: `quickice/phase_mapping/triple_points.py`

**No External API Calls:**
- All scientific data embedded in code
- No network requests at runtime

---

*Integration audit: 2026-03-30*