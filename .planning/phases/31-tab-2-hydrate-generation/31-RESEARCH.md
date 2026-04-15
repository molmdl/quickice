# Phase 31: Tab 2 - Hydrate Generation - Research

**Researched:** 2026-04-15
**Domain:** GenIce2 hydrate generation with guest molecules, GROMACS export, 3D visualization
**Confidence:** HIGH

## Summary

This phase implements hydrate structure generation (sI, sII, sH lattices) with guest molecules (CH4, THF) using GenIce2, with 3D visualization and GROMACS export capabilities. Key findings:

1. **GenIce2 API confirmed:** Uses `--guest` CLI option with format `cage_type=guest*occupancy` (e.g., `12=me` for small cages with methane, `14=me*0.6+co2*0.4` for mixed occupancy). Python API uses `GenIce` class with `.format()` method.

2. **Guest molecule format (confirmed from PyPI v2.2.13):**
   - Small cages: `--guest 12=me` (512 cages)
   - Large cages: `--guest 14=me` (5¹²6⁴ cages for sI), `--guest 16=me` (for sII)
   - Partial occupancy: `--guest 12=co2*0.6+me*0.4`

3. **GROMACS export already implemented:** `write_multi_molecule_gro_file` and `write_multi_molecule_top_file` exist in `gromacs_writer.py` with `MOLECULE_TO_GROMACS` mapping.

4. **Data structures already exist:** `HydrateConfig`, `HydrateStructure`, `HydrateLatticeInfo`, `MoleculeIndex` all defined in `types.py`. `HydrateStructureGenerator` exists in `hydrate_generator.py`.

5. **Guest rendering:** Use per-type `vtkMoleculeMapper` actors - one mapper per molecule type (water vs guests). Guests as ball-and-stick (distinct from water framework lines).

**Primary recommendation:** Connect existing data structures to new GUI tab. GenIce2 CLI options already implemented in `HydrateStructureGenerator._build_genice_options()`. GROMACS export already supports multi-molecule via `MOLECULE_TO_GROMACS` mapping.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| GenIce2 | >=2.2.13 | Hydrate lattice generation | Primary ice/hydrate structure generator with guest support |
| VTK | - | 3D molecular rendering | Already in stack, used by MolecularViewerWidget |
| PySide6 | - | Qt GUI integration | Already in stack |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| genice2-cage | >=2.5 | Cage detection for info display | When displaying cage counts to user (optional) |
| numpy | >=1.26 | Position arrays | Already in stack |

### Guest Force Fields
| Molecule | Recommended FF | Source | Notes |
|----------|----------------|--------|-------|
| CH4 | GAFF/GAFF2 | User provides .itp | "me" in GenIce2 = monatomic methane |
| THF | GAFF/GAFF2 | User provides .itp | "uathf6" = united atom THF |

**Installation:**
```bash
pip install genice2 genice2-cage
```

## Architecture Patterns

### Existing Implementation Overview

**Phase 29 established these for hydrate:**
- `HydrateConfig` dataclass: lattice_type, guest_type, cage_occupancy_small/large, supercell_x/y/z
- `HydrateStructure`: positions, atom_names, cell, molecule_index, lattice_info, report, guest_count, water_count
- `HydrateLatticeInfo`: cage_types, cage_counts, unit_cell_molecules, total_cages
- `MoleculeIndex`: start_idx, count, mol_type (for variable atoms-per-molecule)
- `HydrateStructureGenerator`: generate() method calling GenIce2 Python API
- `MOLECULE_TO_GROMACS`: mapping from mol_type to GROMACS names
- `write_multi_molecule_gro_file()`: multi-molecule .gro export
- `write_multi_molecule_top_file()`: multi-molecule .top export with #include

### Pattern 1: Hydrate Generation Workflow

```python
# Source: hydrate_generator.py, confirmed working
from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
from quickice.structure_generation.types import HydrateConfig

# Create generator
generator = HydrateStructureGenerator()

# Configure hydrate (sI, CH4, 100% small cages, 100% large cages)
config = HydrateConfig(
    lattice_type="sI",
    guest_type="ch4",
    cage_occupancy_small=100.0,
    cage_occupancy_large=100.0,
    supercell_x=1,
    supercell_y=1,
    supercell_z=1,
)

# Generate
structure = generator.generate(config)

# Access results
print(structure.water_count)  # Water molecules
print(structure.guest_count)  # Guest molecules
print(structure.report)        # Generation report
print(structure.lattice_info.cage_types)  # ["5¹²", "5¹²6⁴"]
```

### Pattern 2: GenIce2 Command Building

```python
# Source: hydrate_generator.py, _build_genice_options() method
# GenIce2 formats:
# - Small cages (512): type 12
# - Large cages (5¹²6⁴): type 14 for sI, type 16 for sII
# - Guest names in GenIce2: "me" (methane), "thf" (THF), "co2", "h2"

options = []

# Small cage occupancy
if small_occ > 0:
    if small_occ < 1.0:
        options.append(f"--guest 12={guest_param}*{small_occ}")
    else:
        options.append(f"--guest 12={guest_param}")

# Large cage occupancy
if large_occ > 0:
    if config.lattice_type == "sI":
        large_cage = "14"
    elif config.lattice_type == "sII":
        large_cage = "16"
    else:  # sH
        large_cage = "16"
    options.append(f"--guest {large_cage}={guest_param}")

# Water model
options.append("--water tip4p")
```

### Pattern 3: Multi-Molecule GROMACS Export

```python
# Source: gromacs_writer.py
from quickice.output.gromacs_writer import (
    write_multi_molecule_gro_file,
    write_multi_molecule_top_file,
    MOLECULE_TO_GROMACS,
)

# Write coordinates
write_multi_molecule_gro_file(
    positions=structure.positions,
    molecule_index=structure.molecule_index,
    cell=structure.cell,
    filepath="hydrate.gro",
    title=f"{config.lattice_type} hydrate exported by QuickIce",
)

# Write topology (will include molecule types from MOLECULE_TO_GROMACS)
write_multi_molecule_top_file(
    molecule_index=structure.molecule_index,
    filepath="hydrate.top",
    system_name=f"{config.lattice_type} hydrate structure",
    # Optional: custom .itp paths per molecule type
    # itp_files={"ch4": "/path/to/ch4.itp", "thf": "/path/to/thf.itp"},
)
```

**Note:** User provides .itp files for CH4/THF. For bundled .itp files, would need to ship `ch4.itp` and `thf.itp` in `quickice/data/`.

### Pattern 4: Dual-Style 3D Rendering (Guests vs Water)

**Per CONTEXT.md:** Guests render as ball-and-stick, water framework as lines.

**Implementation approach:**
```python
# Option 1: Multiple mappers (recommended - per molecule type styling)
from vtkmodules.all import vtkMoleculeMapper, vtkActor

# Water framework mapper (lines style or simplified)
water_mapper = vtkMoleculeMapper()
water_mapper.SetInputData(water_vtk_molecule)
water_mapper.SetRenderAtoms(False)  # Lines only
water_mapper.SetRenderBonds(False)

# Guest molecules mapper (ball-and-stick)
guest_mapper = vtkMoleculeMapper()
guest_mapper.SetInputData(guest_vtk_molecule)
guest_mapper.SetRenderAtoms(True)
guest_mapper.SetRenderBonds(True)
guest_mapper.UseBallAndStickSettings()

# Option 2: Single mapper with ignore list
# More complex, not recommended for initial implementation
```

### Recommended Project Structure

```
quickice/
├── gui/
│   ├── tabs/
│   │   ├── hydrate_tab.py        # NEW: HydrateConfigTab widget
│   │   └── hydrate_config_tab.py  # NEW: Alternative naming
│   ├── hydrate_viewer.py        # NEW: Dedicated hydrate viewer widget
│   └── export.py                 # Extend for hydrate export
├── structure_generation/
│   └── hydrate_generator.py     # EXISTS
├── output/
│   └── gromacs_writer.py        # EXISTS (multi-molecule functions)
└── data/
    ├── tip4p-ice.itp            # EXISTS
    ├── ch4.itp                  # NEW: GAFF methane
    └── thf.itp                  # NEW: GAFF THF
```

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Hydrate lattice generation | Custom algorithm | GenIce2 Python API | GenIce2 already handles hydrogen disorder, cage topology |
| Multi-molecule .gro export | Custom writer | `write_multi_molecule_gro_file()` | Handles variable atoms-per-molecule |
| Multi-molecule .top export | Custom topology | `write_multi_molecule_top_file()` | Uses #include pattern, counts molecules |
| Guest molecule insertion | Manual placement | GenIce2 `--guest` option | Handles occupancy, cage-specific placement |
| Per-molecule atom counting | Hardcoded `mol_idx * 3` | MoleculeIndex list | Works for any molecule type |
| Force field parameters | Generate from scratch | GAFF via antechamber/AmberTools | Already validated, available from virtualchemistry.org |
| Guest rendering differentiation | Shader tricks | Multiple vtkMoleculeMapper | Standard approach, clean separation |

**Key insight:** Phase 29 established all the infrastructure. This phase is primarily GUI integration.

## Common Pitfalls

### Pitfall 1: Guest Molecule Format Mismatch

**What goes wrong:** GenIce2 rejects guest option or places wrong molecule.
**Why it happens:** Confusing cage type codes (12 vs 14 vs 16) or guest name (`me` vs `ch4`).
**How to avoid:** Use correct mapping:
- sI small cages: `--guest 12=...`
- sI large cages: `--guest 14=...`
- sII large cages: `--guest 16=...`
- GenIce2 guest names: `me` (methane), `thf`, `co2`, `h2`

**Warning signs:** GenIce2 error "unknown guest" or "invalid cage type".

### Pitfall 2: Water Model Mismatch

**What goes wrong:** Hydrate exports with wrong water model, causing GROMACS errors.
**Why it happens:** TIP4P-ice vs TIP4P/EW water model incompatibility.
**How to avoid:** Use `--water tip4p` option (matches TIP4P-ice virtual site parameters). The code already does this in `_build_genice_options()`.

### Pitfall 3: Molecule Type Not in MOLECULE_TO_GROMACS

**What goes wrong:** Export fails for unknown molecule type.
**Why it happens:** New guest type not added to mapping.
**How to avoid:** Ensure all guest types are in `MOLECULE_TO_GROMACS`. Currently: ice, water, na, cl, ch4, thf, co2, h2.

### Pitfall 4: User Missing .itp Files

**What goes wrong:** GROMACS export fails because user doesn't have guest .itp files.
**Why it happens:** .itp files not bundled with app.
**How to avoid:** Ship bundled .itp files for CH4 and THF with app, OR prompt user to provide file path.

### Pitfall 5: sH Non-Orthogonal Cell

**What goes wrong:** Interface generation fails with sH hydrate.
**Why it happens:** sH has non-orthogonal unit cell, creates gaps in interfaces.
**How to avoid:** Show warning in info panel if sH selected for "Hydrate → Interface Builder". Per CONTEXT.md: "Show warning in info panel if selected lattice is non-orthogonal".

### Pitfall 6: Atom Number Overflow

**What goes wrong:** GROMALS .gro file rejects >99999 atoms or residues.
**Why it happens:** 5-digit limit in standard .gro format.
**How to avoid:** Wrap at 100000 (standard GROMACS convention). Code already does this in `write_multi_molecule_gro_file()`.

## Code Examples

### Hydrate Generation Complete Flow

```python
# Full generation + export example
from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
from quickice.structure_generation.types import HydrateConfig
from quickice.output.gromacs_writer import write_multi_molecule_gro_file, write_multi_molecule_top_file

# Configure
config = HydrateConfig(
    lattice_type="sI",
    guest_type="ch4",
    cage_occupancy_small=100.0,
    cage_occupancy_large=100.0,
)

# Generate
gen = HydrateStructureGenerator()
structure = gen.generate(config)

# Info display (per HYDR-08)
print(f"Cage types: {structure.lattice_info.cage_types}")
print(f"Cage counts: {structure.lattice_info.cage_counts}")
print(f"Water molecules: {structure.water_count}")
print(f"Guest molecules: {structure.guest_count}")

# Export to GROMACS (.gro + .top)
write_multi_molecule_gro_file(
    structure.positions,
    structure.molecule_index,
    structure.cell,
    "hydrate_export.gro",
)
write_multi_molecule_top_file(
    structure.molecule_index,
    "hydrate_export.top",
    "sI CH4 hydrate",
)
```

### GROMACS Multi-Molecule .top Structure

```
; Generated by QuickIce
; Multi-molecule topology

[ defaults ]
; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ
1               2               yes             0.5     0.8333

; Molecule definitions
#include "tip4p-ice.itp"
#include "ch4.itp"

[ system ]
sI CH4 hydrate

[ molecules ]
; Compound        #mols
SOL                136
CH4                 8
```

### Guest .itp File Template (GAFF)

```
; CH4.itp - GAFF methane (self-contained)
; Generated via antechamber/GAFF

[ moleculetype ]
; Name        nrexcl
CH4            3

[ atoms ]
;   nr  type  resi  res  atom  cgnr     charge    mass
    1   ca      1  CH4    C1     1      0.0000  12.01000
    2   hc      1  CH4   HC1     1      0.0000   1.00800
    3   hc      1  CH4   HC2     1      0.0000   1.00800
    4   hc      1  CH4   HC3     1      0.0000   1.00800
    5   hc      1  CH4   HC4     1      0.0000   1.00800

[ bonds ]
;  i    j  funct
    1    2    1
    1    3    1
    1    4    1
    1    5    1

[ angles ]
;  i    j    k  funct
    2    1    3    1
    2    1    4    1
    2    1    5    1
    3    1    4    1
    3    1    5    1
    4    1    5    1

[ dihedrals ]
;  i    j    k    l  funct
    2    1    3    4    9
    2    1    3    5    9
    3    1    4    2    9
; ... more dihedrals
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No hydrate support | GenIce2 --guest option | Phase 29 | Full hydrate generation with guests |
| Single molecule type | MoleculeIndex list | Phase 29 | Variable atoms-per-molecule |
| Single moleculetype | #include pattern | Phase 29 | Multi-molecule .top export |
| No cage info | HydrateLatticeInfo | Phase 29 | Display cage counts to user |
| Line-only rendering | Single mapper | Phase 10 | Basic molecular viewing |

**Deprecated/outdated:**
- TraPPE for guests with TIP4P-ice (GAFF recommended instead)
- Single molecule type assumption in GROMACS export

## Open Questions

1. **Bundled guest .itp files**
   - What we know: User provides .itp files per CONTEXT.md
   - What's unclear: Whether to ship bundled CH4.itp and THF.itp
   - Recommendation: Ship minimal bundled .itp files for CH4 and THF for out-of-box experience, or prompt user for file path

2. **Guest placement verification**
   - What we know: GenIce2 places guests in cages
   - What's unclear: Whether guest ends up in wrong cage type
   - Recommendation: Display occupancy achieved vs requested in info panel (per HYDR-08)

3. **sH interface feasibility**
   - What we know: sH is non-orthogonal (per HYDRATE_LATTICES in types.py)
   - What's unclear: Whether sH creates gaps in interface construction
   - Recommendation: Show warning in info panel if sH selected

## Sources

### Primary (HIGH confidence)
- GenIce2 PyPI v2.2.13 - hydrate CLI options, guest format
- gromacs_writer.py - multi-molecule export functions (existing implementation)
- hydrate_generator.py - GenIce2 Python API usage (existing implementation)
- types.py - HydrateConfig, HydrateStructure, MOLECULE_TO_GROMACS (existing definitions)

### Secondary (MEDIUM confidence)
- GROMACS 2025.2 documentation - topology file format, #include pattern
- virtualchemistry.org - GAFF molecule parameters for GROMACS

### Tertiary (LOW confidence)
- genice2-cage package - for cage detection (optional, not required)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - GenIce2 well-documented, VTK in stack
- Architecture: HIGH - existing code proven in Phase 29
- Pitfalls: HIGH - code patterns already exist
- Guest FF: MEDIUM - need bundled .itp files

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (30 days - stable domain)

## Implementation Checklist

Based on research findings:

- [ ] Create HydrateConfigTab widget (or rename per team convention)
- [ ] Connect to existing HydrateStructureGenerator
- [ ] Add dedicated hydrate viewer widget (distinct from main MolecularViewerWidget)
- [ ] Implement dual-style rendering (guests ball-and-stick, water lines)
- [ ] Display lattice info (cage types, cage counts, occupancy)
- [ ] Wire up export menu for hydrate .gro/.top/.itp
- [ ] Add sH non-orthogonal warning for interface builder
- [ ] Optionally bundle CH4.itp and THF.itp files
- [ ] Handle missing .itp file case (prompt user or error message)