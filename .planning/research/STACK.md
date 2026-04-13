# Technology Stack — QuickIce v4.0 Molecule Insertion

**Project:** QuickIce v4.0 — Add molecule insertion via new tabs  
**Researched:** 2026-04-14  
**Focus:** Stack additions/changes for molecule insertion (Tab 2: hydrates, Tab 4: ions)

---

## Executive Summary

**No new external dependencies are required.** All molecule insertion capabilities can be built using the existing stack (GenIce2, scipy, numpy, VTK, PySide6). The key discovery is that GenIce2 already has first-class support for:

1. **Hydrate generation** — Lattice plugins `CS1`/`sI` and `CS2`/`sII` with built-in cage detection and guest molecule insertion via `guests={cagetype: {molecule: fraction}}`
2. **Cation/anion substitution** — `cations={water_idx: ion_name}` and `anions={water_idx: ion_name}` parameters in `GenIce.__init__()`
3. **Guest molecules** — Built-in molecule plugins: `ch4`, `co2`, `H2`, `et` (ethane), `me` (methanol), `thf` (tetrahydrofuran), `one` (single atom)

The implementation work is entirely in **application logic** (UI tabs, data flow, GROMACS topology extensions, VTK multi-actor rendering), not in acquiring new libraries.

---

## Recommended Stack

### Core Framework (Unchanged)

| Technology | Version | Purpose | Status | Why |
|------------|---------|---------|--------|-----|
| Python | 3.14.3 | Runtime | Existing | No change needed |
| PySide6 | 6.10.2 | GUI framework | Existing | New tabs via QTabWidget; no upgrade needed |
| VTK | 9.5.2 | 3D visualization | Existing | Multi-actor rendering for molecule types; verified working |
| numpy | 2.4.3 | Numerical operations | Existing | Position manipulation for ion placement |
| scipy | 1.17.1 | Scientific computing | Existing | cKDTree for collision detection in liquid phase |
| matplotlib | 3.10.8 | Phase diagram plotting | Existing | Unchanged |
| iapws | 1.5.5 | Thermodynamics | Existing | Water density from T/P; unchanged |
| spglib | 2.7.0 | Crystallographic symmetry | Existing | Unchanged |

### Hydrate Generation (Existing — GenIce2)

| Technology | Version | Purpose | Status | Why |
|------------|---------|---------|--------|-----|
| GenIce2 | 2.2.13.1 | Ice + hydrate structure generation | Existing | **Already supports hydrate generation via cage+guest system** |
| genice-core | 1.4.3 | GenIce internals | Existing | Required by GenIce2 |

**GenIce2 hydrate capabilities verified:**

| Lattice | Cages | Cage Types | Density (g/cm³) | Common Guests |
|---------|-------|------------|------------------|---------------|
| `CS1`/`sI` | 8 | 2×12-hedron + 6×14-hedron | 0.795 | CH₄, CO₂, H₂, THF |
| `CS2`/`sII` | 24 | 16×12-hedron + 8×16-hedron | 0.810 | CH₄, C₂H₆, C₃H₈, THF |
| `MTN` | 24 | 16×12-hedron + 8×16-hedron | 0.810 | (same guests as sII) |

**GenIce2 molecule plugins available for guests:**

| Plugin | Residue Name | Atoms | Use Case |
|--------|-------------|-------|----------|
| `ch4` | CH4 | C, H×4 | Methane hydrate (sI, sII) |
| `co2` | CO2 | C, O×2 | CO₂ hydrate (sI) |
| `H2` | H2 | H×2 | Hydrogen hydrate (sII, sH) |
| `et` | Et | Et (united atom) | Ethane guest |
| `me` | Me | Me (united atom) | Methanol guest |
| `thf` | THF | O, CA×2, CB×2, H×8 | THF hydrate (sII) |
| `one` | X | X (single atom) | Placeholder monatomic |

### Ion Insertion (Existing — GenIce2 + Custom Code)

| Technology | Version | Purpose | Status | Why |
|------------|---------|---------|--------|-----|
| GenIce2 cations/anions | 2.2.13.1 | Replace water molecules with ions | Existing | **GenIce2 supports `cations={idx: 'one'}` and `anions={idx: 'one'}` natively** |
| scipy cKDTree | 1.17.1 | Collision detection in liquid phase | Existing | For random ion placement in water boxes |

**Ion insertion approach:**

- **Tab 4 (liquid phase):** Custom Python code places Na⁺ and Cl⁻ ions at random positions in the liquid water region, using cKDTree for overlap detection against existing water molecules
- **GenIce2 cations/anions** are NOT used for Tab 4 because we need concentration-based placement (mol/L), not index-based replacement
- **Ion topology (.itp):** Must be created as a bundled data file. Joung-Cheatham parameters (J. Phys. Chem. B, 2008) are the standard for TIP4P-compatible ions

### VTK Multi-Actor Rendering (Existing)

| Technology | Version | Purpose | Status | Why |
|------------|---------|---------|--------|-----|
| vtkMoleculeMapper | 9.5.2 | Per-molecule-type rendering | Existing | Each type gets its own mapper + actor with unique style |
| vtkActor | 9.5.2 | Per-molecule-type visibility/color | Existing | Toggle visibility, set color per molecule type |
| vtkPolyDataMapper | 9.5.2 | Ion sphere rendering | Existing | Alternative for single-atom ions without bonds |

**Verified approach:** Each molecule type (ice water, liquid water, ions, guest molecules) gets its own `vtkMoleculeMapper` + `vtkActor` pair. Each mapper can use different representation (VDW for ions, ball-and-stick for guests, lines for water). All actors added to the same `vtkRenderer`. Verified working in testing.

### GROMACS Topology (New Bundled Files Required)

| File | Purpose | Status | Why |
|------|---------|--------|-----|
| `ions-na-cl.itp` | Na⁺ and Cl⁻ ion topology (Joung-Cheatham) | **NEW** | Required for GROMACS export with NaCl; TIP4P-ICE compatible |
| Guest `.itp` files | CH₄, CO₂, THF topology | **NEW** | Required for hydrate GROMACS export; one per supported guest |

---

## New Bundled Data Files

### ions-na-cl.itp — Na⁺ and Cl⁻ Parameters

**Why new:** The existing `tip4p-ice.itp` only defines the SOL water molecule type. For NaCl solution export, we need ion molecule types compatible with TIP4P-ICE.

**Source:** Joung & Cheatham, J. Phys. Chem. B, 112, 9020-9041 (2008). These are the standard parameters for monovalent ions with TIP4P water models.

**Parameters (AMBER-compatible format):**

```
[ moleculetype ]
; molname    nrexcl
NA           1

[ atoms ]
; id  at type  res nr  residu name  at name  cg nr  charge    mass
1   Na        1       NA           NA       1      1.0000    22.98977

[ moleculetype ]
; molname    nrexcl
CL           1

[ atoms ]
; id  at type  res nr  residu name  at name  cg nr  charge    mass
1   Cl        1       CL           CL       1      -1.0000   35.45300
```

**LJ parameters** (must be added to `[ atomtypes ]` in .top file):

| Ion | σ (nm) | ε (kJ/mol) | Source |
|-----|--------|-------------|--------|
| Na⁺ | 0.33284 | 1.15897×10⁻² | Joung-Cheatham (2008) |
| Cl⁻ | 0.440104 | 4.18400×10⁻¹ | Joung-Cheatham (2008) |

**Why bundled, not user-provided:** Matches existing pattern of `tip4p-ice.itp`. Users won't need to find/download ion parameters.

### Guest Molecule .itp Files

**Why new:** Hydrate structures contain guest molecules (CH₄, CO₂, etc.) that need their own topology entries.

**Approach:** Create minimal `.itp` files for each supported guest. These define the molecule type, atoms, bonds, angles, and exclusions. For simple guests like CH₄ and CO₂, these are small files.

**Priority files:**
1. `ch4.itp` — Methane (5 atoms, most common hydrate guest)
2. `co2.itp` — Carbon dioxide (3 atoms, second most common)

Lower priority (defer to post-MVP):
3. `h2.itp` — Hydrogen (2 atoms)
4. `thf.itp` — Tetrahydrofuran (13 atoms, complex)

### CH₄ Topology Parameters (OPLS-AA compatible)

```
[ moleculetype ]
; molname    nrexcl
CH4          3

[ atoms ]
; id  at type  res nr  residu name  at name  cg nr  charge    mass
1   CT        1       CH4          C        1      -0.240    12.0110
2   HC        1       CH4          H1       1       0.060     1.0080
3   HC        1       CH4          H2       1       0.060     1.0080
4   HC        1       CH4          H3       1       0.060     1.0080
5   HC        1       CH4          H4       1       0.060     1.0080

[ bonds ]
; ai  aj  funct  b0      kb
1    2   1      0.109   287741.8
1    3   1      0.109   287741.8
1    4   1      0.109   287741.8
1    5   1      0.109   287741.8

[ angles ]
; ai  aj  ak  funct  theta   ktheta
2    1   3   1      109.47  273.97
2    1   4   1      109.47  273.97
2    1   5   1      109.47  273.97
3    1   4   1      109.47  273.97
3    1   5   1      109.47  273.97
4    1   5   1      109.47  273.97
```

---

## Alternatives Considered

### RDKit for Custom Molecule Input

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Custom molecule parsing | **Custom .gro/.itp file reader** | RDKit | RDKit is a heavy dependency (~200MB conda package) for a feature that reads 2 file types. Our users provide GROMACS coordinate/topology files directly. |
| SMILES → 3D | Not needed | RDKit | Tab 4 specifies coordinates in .gro files; no SMILES input needed |
| Molecule visualization | **VTK multi-actor** | RDKit + 3Dmol.js | Would require web stack; native VTK already works |

**Decision:** Do NOT add RDKit. The custom molecule workflow (Tab 2 and Tab 4) requires users to provide `.gro` + `.itp` files — GROMACS standard formats. A simple GRO parser (already exists in QuickIce for `tip4p.gro`) handles this.

### Open Babel for Format Conversion

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Molecule format conversion | **GRO parser (existing)** | Open Babel | Adds C++ dependency; we only need GRO parsing, which we already have |

**Decision:** Do NOT add Open Babel. QuickIce already has a GRO parser (`_parse_gro()` in `generator.py`) and reads the `tip4p.gro` file. Extending this for custom molecules is straightforward.

### MDAnalysis / MDTraj for Coordinate Manipulation

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Coordinate manipulation | **numpy (existing)** | MDAnalysis / MDTraj | These are analysis libraries; we're doing simple coordinate placement (random insertion, overlap removal). numpy + cKDTree handle this. |

**Decision:** Do NOT add MDAnalysis or MDTraj. Ion placement is: (1) compute random positions, (2) check overlaps via cKDTree, (3) remove overlapping water molecules. This is ~50 lines of Python using existing scipy.

### ParmEd for Topology Manipulation

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| GROMACS topology writing | **String-template writer (existing pattern)** | ParmEd | ParmEd is for complex topology manipulation; we're concatenating simple .itp blocks. The existing `write_top_file()` pattern works. |

**Decision:** Do NOT add ParmEd. The GROMACS topology writer (`gromacs_writer.py`) already writes `.top` files using string templates. Extending it to include ion and guest molecule types follows the same pattern — no need for a full topology manipulation library.

### ASE (Atomic Simulation Environment)

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Crystal structure manipulation | **numpy + GenIce2** | ASE | ASE would add significant dependency for crystal operations; GenIce2 handles structure generation, numpy handles coordinate manipulation |

**Decision:** Do NOT add ASE. GenIce2 provides all hydrate generation. ASE's `ase.io.read()` could parse GRO files, but our existing parser works. ASE's `Atoms` class is convenient but doesn't justify adding a ~50MB dependency.

---

## Integration Points with Existing Stack

### 1. GenIce2 Hydrate Generation → Tab 2

**Existing code:** `IceStructureGenerator._generate_single()` in `quickice/structure_generation/generator.py`

**New code needed:** `HydrateStructureGenerator` that calls GenIce2 with `guests` parameter:

```python
# Existing pattern:
ice = GenIce(lattice, density=self.density, reshape=self.supercell_matrix)
gro_string = ice.generate_ice(formatter=formatter, water=water, depol="strict")

# New pattern for hydrates:
ice = GenIce(lattice, density=self.density)
gro_string = ice.generate_ice(
    formatter=formatter, water=water, depol="strict",
    guests={'12': {'ch4': 1.0}, '14': {'ch4': 1.0}}  # Full occupancy
)
```

**Key integration detail:** GenIce2 hydrate output contains multiple residue types (SOL + CH4, SOL + CO2, etc.). The existing `_parse_gro()` method returns flat arrays — it must be extended to return per-residue-type data for correct VTK rendering and GROMACS export.

### 2. cKDTree Collision Detection → Tab 4

**Existing code:** `quickice/structure_generation/overlap_resolver.py`

**New code needed:** Ion placement function that:
1. Reads existing water positions from `InterfaceStructure`
2. Computes number of Na⁺/Cl⁻ from concentration (mol/L)
3. Places ions at random positions in the liquid phase
4. Uses cKDTree with PBC to detect overlaps with water molecules
5. Removes overlapping water molecules (whole molecules, not partial)

**Integration detail:** The existing `detect_overlaps()` and `remove_overlapping_molecules()` functions already do exactly what's needed — they detect overlaps via cKDTree and remove whole molecules. The new code wraps these with concentration-based ion counting.

### 3. VTK Multi-Actor Rendering → 3D Viewer

**Existing code:** `quickice/gui/molecular_viewer.py` (single `vtkMoleculeMapper` + `vtkActor`)

**New code needed:** Expand to support multiple actors per molecule type:

```python
# Current: single mapper/actor
self._mapper = vtkMoleculeMapper()
self._molecule_actor = vtkActor()

# New: dictionary of mapper/actor per molecule type
self._molecule_actors = {
    'ice_water': (vtkMoleculeMapper(), vtkActor()),     # Lines, cyan
    'liquid_water': (vtkMoleculeMapper(), vtkActor()),  # Lines, cornflower blue
    'ions': (vtkMoleculeMapper(), vtkActor()),           # VDW spheres, yellow/green
    'guest_molecules': (vtkMoleculeMapper(), vtkActor()), # Ball-and-stick, orange
}
```

**Integration detail:** `candidate_to_vtk_molecule()` in `vtk_utils.py` currently creates a single `vtkMolecule` from a `Candidate`. Must be extended to create multiple `vtkMolecule` objects from a composite structure (interface + ions + guests), splitting atoms by molecule type.

### 4. GROMACS Writer → Multi-Residue Export

**Existing code:** `quickice/output/gromacs_writer.py` (single SOL molecule type)

**New code needed:** Extended writer that:
1. Writes multiple `[ moleculetype ]` blocks (SOL, NA, CL, CH4, CO2)
2. Writes correct `[ molecules ]` section with counts per type
3. Includes bundled `.itp` files (ions + guests) alongside `tip4p-ice.itp`
4. Handles ordering: SOL first, then ions, then guests

**Integration detail:** The existing writer hardcodes SOL molecule type. The extended writer must parse the structure's molecule type information and write appropriate topology sections. This follows the same string-template pattern already used.

### 5. UI Tab Integration → PySide6 QTabWidget

**Existing code:** `quickice/gui/main_window.py` (2 tabs: Ice Generation + Interface Construction)

**New tabs:**
- **Tab 2:** "Molecules to Ice" — QStackedWidget with GenIce hydrate preset vs custom molecule
- **Tab 4:** "Insert to Liquid" — Concentration input, ion/molecule selection

**Integration detail:** The existing tab structure uses `QTabWidget`. Adding Tab 2 and Tab 4 means inserting widgets at index 1 and index 3, pushing existing Tab 2 (Interface Construction) to Tab 3.

---

## Installation

**No new packages to install.** All capabilities exist in the current environment.

### New Data Files to Bundle

```bash
# Add to quickice/data/
quickice/data/ions-na-cl.itp    # Na⁺ and Cl⁻ topology (Joung-Cheatham)
quickice/data/ch4.itp           # Methane topology (OPLS-AA)
quickice/data/co2.itp           # Carbon dioxide topology (OPLS-AA)
```

### Existing Environment (Unchanged)

```yaml
# environment.yml — no changes needed
pip:
  - genice2==2.2.13.1       # Hydrate generation + cation/anion support (existing)
  - scipy==1.17.1            # cKDTree for collision detection (existing)
  - numpy==2.4.3             # Coordinate manipulation (existing)
  - pyside6==6.10.2          # GUI tabs (existing)
  - vtk==9.5.2               # Multi-actor rendering (existing)
  # ... other existing packages unchanged ...
```

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| GenIce2 hydrate generation | **HIGH** | Verified: CS1/sI, CS2/sII lattices with cage data, guest molecule insertion via `guests` parameter. Tested CH₄ in sI structure successfully. |
| GenIce2 cation/anion support | **HIGH** | Verified: `cations={}` and `anions={}` parameters work. Note: produces 'X' residue name (monatomic placeholder), not chemically-specific ion names. |
| Ion placement in liquid (cKDTree) | **HIGH** | Verified: `detect_overlaps()` with PBC already works. Random placement + overlap removal is straightforward extension. |
| VTK multi-actor rendering | **HIGH** | Verified: Created separate `vtkMoleculeMapper` + `vtkActor` per molecule type with different styles. Works correctly. |
| Joung-Cheatham ion parameters | **HIGH** | Standard published parameters from J. Phys. Chem. B 112, 9020 (2008). Widely used in GROMACS community. |
| GRO parsing for multi-residue | **MEDIUM** | GenIce2 output for hydrates contains mixed residue types (SOL + CH4). Must extend `_parse_gro()` to return per-type data. Verified GenIce2 output format; implementation needed. |
| Guest molecule .itp files | **MEDIUM** | CH₄ and CO₂ parameters are well-established in literature. Must be verified for exact compatibility with the existing AMBER-force-field-based `tip4p-ice.itp`. |
| Custom molecule .gro/.itp input | **MEDIUM** | User-provided coordinate files. Simple GRO parsing exists; must add validation and error handling for arbitrary molecules. |

---

## Notable Technical Decisions

### 1. No RDKit/Open Babel — Use GRO Parser Instead

**Decision:** Users provide molecule structures as GROMACS `.gro` + `.itp` file pairs. QuickIce parses these with the existing GRO parser.

**Rationale:** 
- QuickIce's target users (molecular dynamics researchers) work with GROMACS format daily
- Adding RDKit (~200MB) or Open Babel (C++ dependency) for 2 file formats is overkill
- The existing `_parse_gro()` handles the parsing; just needs extension for multi-residue output

### 2. No ASE — Use GenIce2 for Hydrate Generation

**Decision:** Use GenIce2's built-in hydrate lattice plugins (CS1/sI, CS2/sII) with `guests` parameter for hydrate generation. Do NOT use ASE for crystal manipulation.

**Rationale:**
- GenIce2 already generates correct clathrate hydrate structures with guest molecules in cages
- ASE would add ~50MB dependency for operations GenIce2 already handles
- GenIce2's `guests={'12': {'ch4': 1.0}}` syntax is clean and well-documented
- Verified working: CS1 + CH₄ produces 46 SOL + 8 CH₄ in a single unit cell

### 3. GenIce2 Cation/Anion for Reference Only — Custom Placement for Tab 4

**Decision:** Tab 4 (Insert to Liquid) uses custom Python code for ion placement, NOT GenIce2's `cations`/`anions` parameters.

**Rationale:**
- GenIce2's `cations`/`anions` replace water molecules in the ice lattice (by index)
- Tab 4 needs concentration-based ion placement in the **liquid phase** of an interface
- The liquid phase already exists (from `tip4p.gro` or interface construction)
- Custom placement: count Na⁺/Cl⁻ from mol/L, randomly place in liquid region, check overlaps via cKDTree
- This is more physically correct than GenIce2's index-based approach

### 4. Joung-Cheatham Parameters for Na⁺/Cl⁻

**Decision:** Use Joung-Cheatham (2008) ion parameters with TIP4P-ICE water model.

**Rationale:**
- These are the standard and most widely-validated parameters for monovalent ions with 4-point water models
- Published in I.S. Joung and T.E. Cheatham III, J. Phys. Chem. B, 112, 9020-9041 (2008)
- Compatible with the AMBER force field style already used in `tip4p-ice.itp`
- Same parameters used in GROMACS's `amber99sb-ildn.ff/ions.itp`
- Specifically optimized for TIP4P water models

### 5. Bundled .itp Files — Not User-Provided for NaCl

**Decision:** Bundle `ions-na-cl.itp` with QuickIce (like `tip4p-ice.itp`). Users provide their own `.itp` for custom molecules only.

**Rationale:**
- NaCl is the most common salt — users shouldn't need to find/download ion parameters
- Bundling ensures version compatibility with TIP4P-ICE
- Pattern established by existing `tip4p-ice.itp`
- Custom molecules (Tab 2 and Tab 4) require user-provided `.itp` because we can't predict what molecules users want

---

## Sources

- GenIce2 source code: `genice2/genice.py` — `GenIce.__init__()`, `Stage7()` for guest placement, `generate_ice()` with `guests` parameter (verified in installed package v2.2.13.1)
- GenIce2 lattice plugins: `genice2/lattices/CS1.py`, `CS2.py`, `sI.py`, `sII.py` — hydrate structures with cage detection (verified working)
- GenIce2 molecule plugins: `genice2/molecules/ch4.py`, `co2.py`, `H2.py`, `thf.py`, `one.py` — guest molecules (verified working)
- Joung & Cheatham (2008): "Determination of Alkali and Halide Monovalent Ion Parameters for Use in Explicitly Solvated Biomolecular Simulations", J. Phys. Chem. B, 112, 9020-9041
- GROMACS AMBER force field ions: `/share/apps/plumed-gromacs-gpu/share/gromacs/top/amber99sb-ildn.ff/ions.itp` (verified Na⁺ σ=0.33284 nm, Cl⁻ σ=0.440104 nm)
- VTK 9.5.2 API: `vtkMoleculeMapper`, `vtkActor`, `vtkPolyDataMapper` — verified multi-actor rendering pattern works (tested in quickice environment)
- QuickIce existing stack: `.planning/codebase/STACK.md` (verified versions)
- QuickIce v4 context: `.planning/v4-context.md` (feature specification)