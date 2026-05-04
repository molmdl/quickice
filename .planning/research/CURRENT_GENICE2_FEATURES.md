# Current GenIce2 Feature Coverage (Accurate)

**Analysis Date:** 2026-05-05  
**Verified by:** Code inspection with exact line numbers

## Water Models Supported

### QuickIce Uses:
- **TIP3P** (3-site): O, H, H
  - File: `quickice/structure_generation/generator.py:119`
  - Used for: Ice generation (classic ice phases)
  - GenIce2 call: `water = safe_import('molecule', 'tip3p').Molecule()`
  
- **TIP4P** (4-site): OW, HW1, HW2, MW  
  - File: `quickice/structure_generation/hydrate_generator.py:154`
  - Used for: Hydrate structures
  - GenIce2 call: `water = safe_import('molecule', 'tip4p').Molecule()`
  - Note: Classic ice generated with TIP3P, normalized to TIP4P-ICE at export

### GenIce2 Also Supports (NOT used by QuickIce):
- tip5p, spce, 3site, 4site, 5site, 6site, 7site, physical_water

---

## Ice Phases Supported

### QuickIce Exposes via GenIce2:
- **Ice Ih** (`ice_ih`): `quickice/structure_generation/mapper.py:19` — lattice `1h`
- **Ice II** (`ice_ii`): lattice `2`
- **Ice III** (`ice_iii`): lattice `3`
- **Ice IV** (`ice_iv`): lattice `4`
- **Ice V** (`ice_v`): lattice `5`
- **Ice VI** (`ice_vi`): lattice `6`
- **Ice VII** (`ice_vii`): lattice `7`
- **Ice VIII** (`ice_viii`): lattice `8`
- **Ice IX** (`ice_ix`): lattice `9`
- **Ice XI** (`ice_xi`): lattice `11`
- **Ice XII** (`ice_xii`): lattice `12`
- **Ice XIII** (`ice_xiii`): lattice `13`
- **Ice XIV** (`ice_xiv`): lattice `14`
- **Ice XV** (`ice_xv`): lattice `15`
- **Ice XVI** (`ice_xvi`): lattice `16`
- **Ice XVII** (`ice_xvii`): lattice `17`
- **Ice XVIII** (`ice_xviii`): lattice `18`

**File:** `quickice/structure_generation/mapper.py:19-35`  
**Mapping function:** `get_genice_lattice_name(phase_id)` converts QuickIce phase IDs to GenIce2 lattice names

### GenIce2 Also Supports (NOT exposed in QuickIce):
- 50+ additional lattices including: A15, ACO, B, BSV, C14, C15, C36, CRN1-3, CS1-4, DDR, DOH, EMT, etc.
- Full list: 79 lattices total

---

## Hydrate Types Supported

### QuickIce Exposes:
- **Structure I (sI)**: `quickice/structure_generation/types.py:HYDRATE_LATTICES`
  - GenIce2 lattice: `CS1`
  - Small cages: 5^12 (pentagonal dodecahedron)
  - Large cages: 5^12 6^2 (tetrakaidecahedron)
  
- **Structure II (sII)**: 
  - GenIce2 lattice: `CS2`
  - Small cages: 5^12
  - Large cages: 5^12 6^4 (hexakaidecahedron)
  
- **Structure H (sH)**:
  - GenIce2 lattice: `DOH`
  - Small cages: 5^12
  - Large cages: 5^12 6^8

**File:** `quickice/structure_generation/hydrate_generator.py:54-63`

---

## Guest Molecules Supported

### QuickIce Exposes:
- **CH4** (methane): `quickice/structure_generation/types.py:GUEST_MOLECULES`
  - All-atom: 5 atoms (C, H, H, H, H)
  - United-atom: 1 atom (Me)
  - GenIce2 molecule: `ch4` or `me`
  
- **THF** (tetrahydrofuran):
  - 13 atoms (O, CA, CA, CB, CB, + 8 H)
  - GenIce2 molecule: `thf`
  
- **CO2** (carbon dioxide):
  - 3 atoms (C, O, O)
  - GenIce2 molecule: `co2`
  
- **H2** (hydrogen):
  - 2 atoms (H, H)
  - GenIce2 molecule: `H2`

**File:** `quickice/structure_generation/types.py:143-163`

### GenIce2 Also Supports (NOT exposed in QuickIce):
- et (ethanol), g12, g14, g15, g16 (guest types), NvdE, uathf, uathf6, ice, mol, one, empty

---

## Export Formats - DETAILED

### Format: GRO (GROMACS Coordinate)

#### Ice Structure Export (Tab 1):
- **Menu Action:** `main_window.py:311` — "Export for GROMACS..." (Ctrl+G)
- **Handler:** `export.py:417` — `GROMACSExporter.export_gromacs()`
- **Writer Function:** `gromacs_writer.py:288` — `write_gro_file(candidate, filepath)`
- **File Extension:** `.gro`
- **GenIce2 Integration:** 
  - GenIce2 generates GRO internally: `generator.py:125` — `gro_string = ice.generate_ice(formatter=formatter, water=water, depol='strict')`
  - Formatter: `safe_import('format', 'gromacs').Format()` at line 122
  - QuickIce parses and rewrites with TIP4P-ICE normalization
- **Parameters:**
  - Water model: TIP4P-ICE (4 atoms per molecule)
  - MW virtual site added during export: `gromacs_writer.py:338` — `compute_mw_position()`
  - Atom naming: OW, HW1, HW2, MW
  - Residue name: SOL
  - Coordinate wrapping: Individual atoms wrapped to [0, L)
- **Default Filename:** `{phase}_{T}K_{P}MPa_c{rank}.gro`
- **Notes:** 
  - Input is 3-atom TIP3P format, output is 4-atom TIP4P-ICE
  - Box vectors in triclinic format (9 values)
  - Atom numbers wrap at 100,000 for large systems

#### Interface Structure Export (Tab 3):
- **Menu Action:** `main_window.py:318` — "Export Interface for GROMACS..." (Ctrl+I)
- **Handler:** `export.py:528` — `InterfaceGROMACSExporter.export_interface_gromacs()`
- **Writer Function:** `gromacs_writer.py:468` — `write_interface_gro_file(iface, filepath)`
- **File Extension:** `.gro`
- **Parameters:**
  - Combined ice + water + guests
  - Molecule-aware wrapping: `wrap_molecules_into_box()` at line 518
  - Order: ice → water → guests
- **Default Filename:** `interface_{mode}.gro`

#### Ion Structure Export (Tab 4):
- **Menu Action:** `main_window.py:332` — "Export Ions for GROMACS..." (Ctrl+J)
- **Handler:** `export.py:34` — `IonGROMACSExporter.export_ion_gromacs()`
- **Writer Function:** `gromacs_writer.py:1137` — `write_ion_gro_file(ion_structure, filepath)`
- **File Extension:** `.gro`
- **Parameters:**
  - Order: SOL (ice+water) → guests → NA → CL
  - Molecule-aware wrapping
- **Default Filename:** `ions_{na_count}na_{cl_count}cl.gro`

#### Hydrate Structure Export (Tab 2):
- **Menu Action:** `main_window.py:325` — "Export Hydrate for GROMACS..." (Ctrl+E)
- **Handler:** `hydrate_export.py:62` — `HydrateGROMACSExporter.export_hydrate()`
- **Writer Function:** `gromacs_writer.py:907` — `write_multi_molecule_gro_file()`
- **File Extension:** `.gro`
- **Parameters:**
  - Multi-molecule system with molecule_index
  - Guest atom reordering: `reorder_guest_atoms()` at line 974
- **Default Filename:** `hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro`

---

### Format: PDB (Protein Data Bank)

- **Menu Action:** `main_window.py:285` — "Save PDB (Left Viewer)..." (Ctrl+S)
- **Alternative Action:** `main_window.py:290` — "Save PDB (Right Viewer)..." (Ctrl+Shift+S)
- **Handler:** `export.py:146` — `PDBExporter.export_candidate()`
- **Writer Function:** `pdb_writer.py:50` — `write_pdb_with_cryst1(candidate, filepath)`
- **File Extension:** `.pdb`
- **GenIce2 Call:** NONE — QuickIce uses custom PDB writer (not GenIce2 format)
- **Parameters:**
  - CRYST1 record with cell parameters: a, b, c, alpha, beta, gamma (Å)
  - Coordinates converted from nm to Å (multiply by 10.0)
  - ATOM records with HETATM for water molecules
  - Residue name: HOH
  - Chain ID: A
- **Default Filename:** `{phase}_{T}K_{P}MPa_c{rank}.pdb`
- **Notes:**
  - No GenIce2 formatter used
  - Custom implementation for CRYST1 record generation
  - Atoms per molecule auto-detected from position count

---

### Format: TOP (GROMACS Topology)

- **Generated By:** All GROMACS exporters (automatically)
- **Writer Functions:**
  - Ice: `gromacs_writer.py:374` — `write_top_file(candidate, filepath)`
  - Interface: `gromacs_writer.py:800` — `write_interface_top_file(iface, filepath)`
  - Hydrate: `gromacs_writer.py:1004` — `write_multi_molecule_top_file()`
- **File Extension:** `.top`
- **GenIce2 Call:** NONE — Custom writer
- **Parameters:**
  - Force field: Amber-compatible defaults
  - Atom types: OW_ice, HW_ice, MW, plus guest types
  - Water model: TIP4P-ICE
  - Include directives: `#include "tip4p-ice.itp"`, `#include "{guest}.itp"`
  - Molecule counts in [molecules] section

---

### Format: ITP (GROMACS Include Topology)

- **Source:** Bundled files in `quickice/data/`
  - `tip4p-ice.itp` — TIP4P-ICE water model
  - `ch4.itp` — Methane (GAFF2 parameters)
  - `thf.itp` — Tetrahydrofuran (GAFF2 parameters)
  - `co2.itp` — Carbon dioxide (GAFF2 parameters)
  - `h2.itp` — Hydrogen (GAFF2 parameters)
- **Generated:** `ion.itp` — Na+/Cl- ions (Madrid2019)
  - Writer: `gromacs_ion_export.py:80` — `write_ion_itp()`
- **File Extension:** `.itp`
- **GenIce2 Call:** NONE — Bundled parameter files
- **Notes:**
  - Copied to export directory during GROMACS export
  - Pre-parameterized with GAFF2 force field for guests
  - Madrid2019 ion parameters for Na+/Cl-

---

### Format: PNG (Image)

#### Viewport Screenshot:
- **Menu Action:** `main_window.py:303` — "Save Viewport..." (Ctrl+Alt+S)
- **Handler:** `export.py:311` — `ViewportExporter.capture_viewport()`
- **Writer:** VTK `vtkPNGWriter` (line 386)
- **File Extension:** `.png`
- **GenIce2 Call:** NONE
- **Parameters:**
  - Scale: 2x resolution (`SetScale(2)`)
  - Quality: N/A (PNG is lossless)
  - Offscreen buffer: `ReadFrontBufferOff()`
- **Default Filename:** `ice_structure_{viewport_name}.png`
- **Notes:**
  - Captures both left and right viewports
  - Forces render before capture to avoid black images

#### Phase Diagram:
- **Menu Action:** `main_window.py:298` — "Save Diagram..." (Ctrl+D)
- **Handler:** `export.py:222` — `DiagramExporter.export_diagram()`
- **Writer:** matplotlib `savefig()`
- **File Extension:** `.png`
- **Parameters:**
  - DPI: 300
  - Bbox: tight
  - Facecolor: white
  - Padding: 0.2 inches

---

### Format: JPEG (Image)

- **Menu Action:** Same as PNG (format selected in save dialog)
- **Handler:** `export.py:311` — `ViewportExporter.capture_viewport()`
- **Writer:** VTK `vtkJPEGWriter` (line 383)
- **File Extension:** `.jpg`
- **GenIce2 Call:** NONE
- **Parameters:**
  - Quality: 95
  - Scale: 2x resolution

---

### Format: SVG (Vector Graphics)

- **Menu Action:** `main_window.py:298` — "Save Diagram..." (Ctrl+D)
- **Handler:** `export.py:222` — `DiagramExporter.export_diagram()`
- **Writer:** matplotlib `savefig(format='svg')`
- **File Extension:** `.svg`
- **GenIce2 Call:** NONE
- **Parameters:**
  - Format: svg
  - Bbox: tight
  - Facecolor: white

---

## GenIce2 Formats NOT Exposed in QuickIce

### GenIce2 Available Formats:
Based on `genice2.formats` package inspection:

- `xyz` — XYZ coordinates
- `exyz` — Extended XYZ
- `cif` — Crystallographic Information File
- `c` — C code output
- `cif2` — Alternative CIF format
- `com` — Generic comment format
- `d` — Distance matrix
- `digraph` — Directed graph
- `e` — Energy output
- `euler` — Euler characteristics
- `exmol` — Extended molecule format
- `g` — Graph format
- `graph` — Graph representation
- `m` — Matrix format
- `mdv_au`, `mdview` — MDView format
- `null` — No output
- `p` — Position format
- `povray` — POV-Ray scene
- `python` — Python pickle
- `q` — Quaternion format
- `quaternion` — Quaternion representation
- `r` — Ring format
- `raw` — Raw coordinates
- `rcom` — Relative COM
- `rings` — Ring analysis
- `towhee` — Towhee format
- `y` — Y format
- `yaplot` — Yaplot visualization

**Total GenIce2 formats:** 30+  
**QuickIce uses:** 1 (gromacs) internally, then custom writers for output

---

## Integration Architecture

### How GenIce2 is Called:

#### For Ice Generation (Classic Phases):
```
File: quickice/structure_generation/generator.py

Line 108: lattice = safe_import('lattice', self.lattice_name).Lattice()
Line 111: ice = GenIce(lattice, density=self.density, reshape=self.supercell_matrix)
Line 119: water = safe_import('molecule', 'tip3p').Molecule()
Line 122: formatter = safe_import('format', 'gromacs').Format()
Line 125: gro_string = ice.generate_ice(formatter=formatter, water=water, depol='strict')
```

#### For Hydrate Generation:
```
File: quickice/structure_generation/hydrate_generator.py

Line 141: lattice = safe_import('lattice', lattice_name).Lattice()
Line 151: ice = GenIce(lattice, reshape=supercell_matrix)
Line 154: water = safe_import('molecule', 'tip4p').Molecule()
Line 157: formatter = safe_import('format', 'gromacs').Format()
Line 161-195: Build guests dict with parse_guest()
Line 198: gro_string = ice.generate_ice(formatter=formatter, water=water, guests=guests, depol='strict')
```

### Data Flow:
1. GenIce2 generates GRO format string
2. QuickIce parses GRO → positions, atom_names, cell
3. QuickIce wraps coordinates (molecule-aware)
4. QuickIce exports via custom writers:
   - `gromacs_writer.py` → GRO/TOP/ITP
   - `pdb_writer.py` → PDB
   - VTK/matplotlib → PNG/JPEG/SVG

---

## Parameters Exposed in GUI

### Ice Generation Tab:
- **Temperature:** 0-273 K (via input panel)
- **Pressure:** 0-1000 MPa (via input panel)
- **Molecule count:** 4-10000 (via input panel)
- **Phase:** Auto-selected from T/P via phase diagram
- **Depolarization:** Fixed to 'strict' (not user-configurable)

### Hydrate Tab:
- **Lattice type:** sI, sII, sH (dropdown)
- **Guest type:** ch4, thf, co2, h2 (dropdown)
- **Small cage occupancy:** 0-100% (slider)
- **Large cage occupancy:** 0-100% (slider)
- **Supercell:** nx, ny, nz (spin boxes)

### Interface Tab:
- **Mode:** parallel, perpendicular, sandwich (dropdown)
- **Ice source:** Generated structure or hydrate
- **Water thickness:** 0-50 Å (slider)

### Ion Tab:
- **Ion type:** Na+, Cl-, both (dropdown)
- **Ion count:** 0-100 (spin box)
- **Salt concentration:** 0.0-3.5 mol/kg (slider)

**File:** `quickice/gui/input_panel.py`, `hydrate_panel.py`, `interface_panel.py`, `ion_panel.py`

---

## Planned Features (from milestones)

### Version 4.5:
- Additional GenIce2 lattice support (A15, BSV, etc.)
- Custom guest molecule definition
- Multi-guest hydrates
- Export to additional formats (XYZ, CIF)

### Future:
- GROMACS mdp file generation
- Energy minimization workflow
- MD simulation template generation

---

## Known Limitations

### Intentional Design Choices:
1. **No XYZ export** — PDB/GRO sufficient for molecular dynamics
2. **No CIF export** — Not needed for GROMACS workflow
3. **TIP3P for ice, TIP4P for hydrates** — Different use cases
4. **Fixed depolarization='strict'** — Ensures physically valid structures
5. **No concurrent generation** — Thread safety with global random state

### GenIce2 Features Not Exposed:
1. Ring statistics analysis
2. Graph representation
3. Quaternion orientation
4. Energy calculations
5. POV-Ray scene export
6. Custom molecule definitions (beyond bundled guests)

### Current Issues:
1. Large systems (>100K atoms) have atom number wrapping in GRO format
2. Guest atom order mismatch between GenIce2 output and .itp definitions (handled via reordering)
3. Molecule wrapping across PBC requires special handling (implemented in `wrap_molecules_into_box`)

---

## Summary Table

| Export Format | GenIce2 Format String | QuickIce Writer | Menu Action | File Extension |
|---------------|----------------------|-----------------|-------------|----------------|
| GRO | `gromacs` (internal) | `gromacs_writer.py` | Export GROMACS | .gro |
| PDB | None | `pdb_writer.py` | Save PDB | .pdb |
| TOP | None | `gromacs_writer.py` | Auto-generated | .top |
| ITP | None | Bundled files | Auto-copied | .itp |
| PNG | None | VTK `vtkPNGWriter` | Save Viewport | .png |
| JPEG | None | VTK `vtkJPEGWriter` | Save Viewport | .jpg |
| SVG | None | matplotlib | Save Diagram | .svg |

**Key Insight:** QuickIce uses GenIce2's `gromacs` format only for internal structure generation, then applies custom writers for all user-facing exports. This allows TIP4P-ICE normalization, proper topology generation, and format-specific optimizations.

---

*Feature coverage analysis complete: 2026-05-05*
