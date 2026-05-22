# External Integrations

**Analysis Date:** 2026-05-22

## APIs & External Services

**Scientific formulations (embedded, not network APIs):**
- IAPWS (International Association for the Properties of Water and Steam) - Thermodynamic property equations
  - SDK/Client: `iapws` Python package (v1.5.5)
  - Auth: None (open scientific formulation library)
  - Used via: `iapws.IAPWS95`, `iapws._iapws._Ice`, `iapws.IAPWS97`
  - Files: `quickice/phase_mapping/water_density.py`, `quickice/phase_mapping/ice_ih_density.py`, `quickice/gui/phase_diagram_widget.py`
  - Note: All calculations are local (no network calls). IAPWS provides mathematical formulations implemented in pure Python.

**GenIce2 ice generation engine:**
- SDK/Client: `genice2` Python package (v2.2.13.1) + `genice-core` (v1.4.3)
- Auth: None (open scientific software)
- Used via: `genice2.genice.GenIce`, `genice2.plugin.safe_import`, `genice2.formats.gromacs`, `genice2.lattices` (sI, sII, sH), `genice2.molecules` (tip3p, tip4p), `genice2.valueparser.parse_guest`
- Files: `quickice/structure_generation/generator.py`, `quickice/structure_generation/hydrate_generator.py`
- Note: Local computation only. GenIce2 generates crystal structures algorithmically (no network calls).

## Data Storage

**Databases:**
- None. All data is computed on-the-fly or loaded from bundled files.

**File Storage:**
- Local filesystem only
  - Bundled molecular data: `quickice/data/` (ITP, GRO, TOP files)
  - Phase boundary data: `quickice/phase_mapping/data/ice_phases.json`
  - Custom molecule examples: `quickice/data/custom/`
  - User output: configurable via `--output` CLI flag (default: `output/`)

**Caching:**
- Python `lru_cache` (in-memory, per-process)
  - `quickice/phase_mapping/water_density.py`: `water_density_kgm3()` cached with maxsize=256
  - `quickice/phase_mapping/ice_ih_density.py`: `ice_ih_density_kgm3()` cached with maxsize=256
  - No disk cache, no Redis, no Memcached

## Authentication & Identity

**Auth Provider:**
- None. Desktop application with no user authentication.

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, Rollbar, etc.)

**Logs:**
- Python `logging` module with `logging.getLogger(__name__)` pattern
- Level: WARNING for fallback density calculations, INFO for file parsing
- No centralized log aggregation
- No log file output configured (console logging only)

## CI/CD & Deployment

**Hosting:**
- Desktop application (not hosted on servers)

**CI Pipeline:**
- None detected (no `.github/workflows/`, no `.gitlab-ci.yml`, no `Makefile` with CI targets)

**Build Pipeline:**
- `scripts/build-linux.sh` → PyInstaller → `dist/quickice-gui/quickice-gui` (Linux standalone)
- `scripts/assemble-dist.sh` → Distribution assembly
- Spec file: `quickice-gui.spec` (PyInstaller configuration)

## Environment Configuration

**Required env vars:**
- None required (all configuration via CLI arguments or GUI inputs)

**PYTHONPATH setup:**
- `source setup.sh` adds project root to `PYTHONPATH` (needed for `import quickice`)

**Conda environment:**
- `environment.yml` defines runtime environment (`quickice`)
- `environment-build.yml` defines build environment (`quickice-build`) with PyInstaller added

**Secrets location:**
- Not applicable (no secrets in this application)

## GROMACS Integration

**File formats handled:**
- `.gro` (GROMACS coordinate files) — Read and write
  - Parser: `quickice/structure_generation/gro_parser.py` (`parse_gro_string`, `parse_gro_file`)
  - Writer: `quickice/output/gromacs_writer.py` (`write_gro_file`, `write_interface_gro_file`, `write_multi_molecule_gro_file`)
  - Hydrate parser: `quickice/structure_generation/hydrate_generator.py` (`_parse_gro_result`)
  - Template: `quickice/data/tip4p.gro` (single TIP4P water molecule)

- `.top` (GROMACS topology files) — Write only
  - Writer: `quickice/output/gromacs_writer.py` (`write_top_file`, `write_interface_top_file`, `write_multi_molecule_top_file`)
  - Uses `#include` directives for molecule ITP files

- `.itp` (GROMACS molecule topology files) — Read and bundled write
  - Parser: `quickice/structure_generation/itp_parser.py` (`parse_itp_file`)
  - ITP residue reader: `quickice/output/gromacs_writer.py` (`parse_itp_residue_name`, `parse_itp_atomtypes`)
  - Bundled files: `quickice/data/tip4p-ice.itp`, `quickice/data/ch4.itp`, `quickice/data/ch4_hydrate.itp`, `quickice/data/ch4_liquid.itp`, `quickice/data/thf.itp`, `quickice/data/thf_hydrate.itp`, `quickice/data/thf_liquid.itp`
  - Ion ITP generator: `quickice/structure_generation/gromacs_ion_export.py` (`generate_ion_itp`)

**GROMACS conventions:**
- TIP4P-ICE water model (4-site: OW, HW1, HW2, MW)
- GAFF2 force field for guest molecules (CH4, THF)
- Madrid2019 ion parameters for Na+/Cl-
- Atom/residue numbers wrap at 100000 (GRO format limit)
- Coordinates in nanometers (GROMACS standard)
- Triclinic box vectors in GRO format (9 values: v1x v2y v3z v1y v1z v2x v2z v3x v3y)

## File Format Export

**Output formats:**
- PDB (Protein Data Bank) — `quickice/output/pdb_writer.py` with CRYST1 records
- GRO (GROMACS coordinates) — `quickice/output/gromacs_writer.py`
- TOP (GROMACS topology) — `quickice/output/gromacs_writer.py`
- ITP (GROMACS molecule topology) — Generated for ions; bundled for water/guests
- PNG/SVG — Phase diagram images (`quickice/output/phase_diagram.py`)
- PNG/JPEG — 3D viewport screenshots (via VTK `vtkWindowToImageFilter`)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Third-Party Dependencies (Transitive via GenIce2)

The following packages are installed as GenIce2 dependencies but not directly imported by QuickIce code:

| Package | Version | Purpose (GenIce2 internal) |
|---------|---------|---------------------------|
| `cycless` | 0.7 | Cycle detection in hydrogen bond networks |
| `graphstat` | 0.3.3 | Graph statistics computation |
| `pairlist` | 0.6.4 | Pair list computation for molecular interactions |
| `openpyscad` | 0.5.0 | OpenSCAD 3D model generation |
| `yaplotlib` | 0.1.3 | Yaplot visualization format output |
| `deprecated` | 1.3.1 | Deprecation warning decorators |
| `deprecation` | 2.1.0 | Deprecation decorator utilities |
| `methodtools` | 0.4.7 | LRU cache for class methods |
| `wirerope` | 1.0.0 | Decorator utility |
| `wrapt` | 2.1.2 | Transparent object wrapping |
| `six` | 1.17.0 | Python 2/3 compatibility layer |
| `spglib` | 2.7.0 | Space group symmetry (used by GenIce2 lattice analysis) |
| `networkx` | 3.6.1 | Graph/network algorithms for hydrogen bond topology |

**Note for PyInstaller:** The spec file (`quickice-gui.spec`) explicitly collects all data/binaries/hidden-imports from `iapws`, `genice2`, `genice_core`, `matplotlib`, `scipy`, `numpy`, `shapely`, `networkx`, and `spglib` to ensure complete bundling.

---

*Integration audit: 2026-05-22*
