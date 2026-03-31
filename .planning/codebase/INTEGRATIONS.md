# External Integrations

**Analysis Date:** 2026-03-31

## APIs & External Services

**None** - QuickIce is a standalone scientific application with no external API calls or web services.

## Scientific Libraries

**GenIce2 (Ice Structure Generation):**
- Purpose: Generate ice crystal structures with hydrogen bond networks
- SDK/Client: `genice2` pip package, `genice2.plugin.safe_import`
- Integration pattern: Plugin-based lattice loading
- Key usage: `quickice/structure_generation/generator.py`
  ```python
  from genice2.plugin import safe_import
  from genice2.genice import GenIce
  
  lattice = safe_import("lattice", self.lattice_name).Lattice()
  ice = GenIce(lattice, density=self.density, reshape=self.supercell_matrix)
  water = safe_import("molecule", "tip3p").Molecule()
  formatter = safe_import("format", "gromacs").Format()
  gro_string = ice.generate_ice(formatter=formatter, water=water, depol="strict")
  ```
- Supported lattices: `ice1h`, `ice1c`, `ice2`, `ice3`, `ice5`, `ice6`, `ice7`, `ice8`
- Water model: TIP3P

**IAPWS (Water Properties):**
- Purpose: Calculate water/ice thermodynamic properties using IAPWS-95 standard
- SDK/Client: `iapws` pip package
- Integration pattern: Direct function calls
- Key usage: `quickice/output/phase_diagram.py`
  ```python
  from iapws import IAPWS97
  
  st = IAPWS97(T=T, x=0)  # saturated liquid
  pressure = st.P  # saturation pressure
  ```
- Used for: Liquid-vapor boundary in phase diagrams

**spglib (Crystal Symmetry):**
- Purpose: Analyze crystal space groups for structure validation
- SDK/Client: `spglib` pip package
- Integration pattern: Direct function calls
- Key usage: `quickice/output/validator.py`
  ```python
  import spglib
  
  # Get space group from lattice and positions
  spacegroup = spglib.get_spacegroup((cell, positions, numbers))
  ```
- Used for: Validate generated ice structures have correct symmetry

## Data Storage

**Databases:**
- None - No database integration

**File Storage:**
- Local filesystem only
- Output directory: Configurable via `--output` flag (default: `output/`)
- File formats:
  - PDB files (Protein Data Bank format) - molecular coordinates
  - PNG files - phase diagram images
  - SVG files - vector phase diagrams
  - TXT files - phase diagram data

**Caching:**
- None - No caching mechanism

## Authentication & Identity

**Auth Provider:**
- None - Local CLI application, no authentication

## Monitoring & Observability

**Error Tracking:**
- None - Logging only

**Logs:**
- Python `logging` module (stdlib)
- Integration: `quickice/output/orchestrator.py`
  ```python
  import logging
  logging.warning(f"Failed to write PDB for rank {rank}: {e}")
  ```
- No external log aggregation

## CI/CD & Deployment

**Hosting:**
- None - Desktop/local application

**CI Pipeline:**
- None detected - No CI configuration files found

## Environment Configuration

**Required env vars:**
- None - Pure Python application

**Environment setup:**
- `conda env create -f env.yml` - Creates environment with all dependencies
- `source setup.sh` - Activates environment and sets PYTHONPATH

**Secrets location:**
- Not applicable - No secrets required

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Scientific Data Sources

**Phase Boundary Data:**
- Source: IAPWS R14-08(2011) - Melting curves for ice phases
- Implementation: `quickice/phase_mapping/melting_curves.py`
  - Ice Ih melting: 251.165 K ≤ T ≤ 273.16 K
  - Ice III melting: 251.165 K < T ≤ 256.164 K
  - Ice V melting: 256.164 K < T ≤ 273.31 K
  - Ice VI melting: 273.31 K < T ≤ 355 K
  - Ice VII melting: 355 K < T ≤ 715 K

**Triple Point Data:**
- Source: Literature values (LSBU Water Phase Diagram)
- Implementation: `quickice/phase_mapping/triple_points.py`
- Triple points stored as constants:
  ```python
  TRIPLE_POINTS = {
      "Ih_III_Liquid": (251.165, 207.5),
      "Ih_II_III": (238.55, 212.9),
      "II_III_V": (248.85, 344.3),
      # ... etc
  }
  ```

**Phase Metadata:**
- Source: IAPWS R14-08 and literature
- Implementation: `quickice/phase_mapping/lookup.py`
- Density values for each ice phase stored as constants

## Input/Output Formats

**Input:**
- Command-line arguments (temperature, pressure, number of molecules)
- No file input required

**Output:**
- PDB format: Molecular coordinates with CRYST1 records
  - Written by: `quickice/output/pdb_writer.py`
  - Format: Standard PDB with HETATM records for water molecules
  
- PNG/SVG: Phase diagram visualization
  - Written by: `quickice/output/phase_diagram.py`
  - Uses matplotlib for rendering

- TXT: Phase diagram data file
  - Written by: `quickice/output/phase_diagram.py`
  - Contains triple points and melting curve data

---

*Integration audit: 2026-03-31*