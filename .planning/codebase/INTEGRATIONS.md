# External Integrations

**Analysis Date:** 2026-05-12

## APIs & External Services

**No external network APIs used.** QuickIce is a standalone desktop application with no network calls or external API integrations. All computation happens locally.

## Scientific Libraries (Core Integrations)

**GenIce2:**
- Purpose: Ice crystal structure generation with hydrogen bond disorder
- SDK: `genice2` package via pip
- Usage: `quickice/structure_generation/generator.py`, `quickice/structure_generation/hydrate_generator.py`
- Lattice types: Ice Ih, Ic, II, III, IV, V, VI, VII, VIII, IX, XI, X, hydrate sI/sII/sH
- Import pattern:
  ```python
  from genice2.genice import GenIce
  from genice2.plugin import safe_import
  from genice2.lattices import sI, sII, sH
  ```

**IAPWS:**
- Purpose: Water/ice thermodynamic properties from IAPWS-95 standard
- SDK: `iapws` package via pip
- Usage: `quickice/phase_mapping/water_density.py`, `quickice/phase_mapping/ice_ih_density.py`
- Provides: Temperature-dependent density for Ice Ih, melting curve calculations
- Import pattern:
  ```python
  from iapws import IAPWS95, IAPWS97
  from iapws._iapws import _Ice
  ```

**Spglib:**
- Purpose: Crystal symmetry analysis and space group validation
- SDK: `spglib` package via pip
- Usage: `quickice/output/validator.py`
- Validates: Generated structures match expected space groups

## Data Storage

**Databases:**
- None. No database connections.

**File Storage:**
- Local filesystem only
- Output formats: PDB, GROMACS (.gro, .top, .itp), PNG, SVG
- Input files: User-provided .gro and .itp files for custom molecules
- Bundled data: `quickice/data/` contains force field parameters

**Force Field Files (Bundled):**
- `quickice/data/tip4p-ice.itp` - TIP4P-ICE water model parameters
- `quickice/data/tip4p.gro` - TIP4P water structure template
- `quickice/data/ch4.itp` - Methane GAFF2 parameters (hydrate guests)
- `quickice/data/thf.itp` - THF GAFF2 parameters (hydrate guests)
- `quickice/data/ch4_liquid.itp` - Methane parameters (liquid solutes)
- `quickice/data/thf_liquid.itp` - THF parameters (liquid solutes)

**Caching:**
- None. All computations are performed fresh for each run.

## Authentication & Identity

**Auth Provider:**
- Not applicable. No authentication required for desktop application.

## Monitoring & Observability

**Error Tracking:**
- None. Application uses Python exception handling with user-facing error messages.

**Logs:**
- Console output for CLI usage
- GUI log panel for graphical interface (displays generation progress and errors)
- No persistent log files

## CI/CD & Deployment

**Hosting:**
- GitHub repository for source distribution
- GitHub Releases for binary distribution

**CI Pipeline:**
- GitHub Actions (`.github/workflows/build-windows.yml`)
- Trigger: Manual workflow dispatch
- Build target: Windows executable via PyInstaller
- Cross-compilation: Linux development → Windows production build
- Artifacts: ZIP archives containing executable, docs, licenses

**Dependabot:**
- Enabled for conda and pip ecosystems (`.github/dependabot.yml`)
- Weekly update checks
- Pull requests disabled (`open-pull-requests-limit: 0`)

## Environment Configuration

**Required env vars:**
- None required at runtime
- Development: `PYTHONPATH` set by `setup.sh`

**Secrets location:**
- Not applicable. No secrets or credentials needed.

## Webhooks & Callbacks

**Incoming:**
- None. Desktop application.

**Outgoing:**
- None. No network requests.

## Molecular Dynamics Integration

**GROMACS Export:**
- Primary output format for molecular dynamics simulations
- File types: `.gro` (coordinates), `.top` (topology), `.itp` (include files)
- Water model: TIP4P-ICE (Abascal et al., J. Chem. Phys. 2005)
- Force field: Bundled ITP files with GAFF2 parameters

**Output Module:**
- Location: `quickice/output/`
- Writers: `gromacs_writer.py`, `pdb_writer.py`
- Multi-molecule support: Handles water + hydrate guests + solutes + custom molecules + ions

**Molecule Ordering Convention:**
```
[ molecules ]
SOL               ; Water molecules
CH4_HYD           ; Hydrate guests (from Tab 1)
THF_LIQ           ; Liquid solutes (from Tab 4)
CUSTOM_MOL_1      ; Custom molecules (from Tab 3)
NA                ; Sodium ions (from Tab 5)
CL                ; Chloride ions (from Tab 5)
```

## External Reference Data

**Scientific Standards:**
- IAPWS R14-08(2011): Melting and sublimation curves
- IAPWS R10-06(2006): Ice Ih equation of state
- Triple point data from Journaux et al. (2019, 2020)
- LSBU Water Phase Data for additional phase boundaries

**Built-in Reference Files:**
- `quickice/phase_mapping/melting_curves.py` - IAPWS melting curve equations
- `quickice/phase_mapping/solid_boundaries.py` - Solid-solid phase boundaries
- `quickice/phase_mapping/triple_points.py` - Triple point coordinates

---

*Integration audit: 2026-05-12*
