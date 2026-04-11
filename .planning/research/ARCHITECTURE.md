# Architecture Research: QuickIce v3.5 Interface Enhancements

**Domain:** Scientific visualization / Computational chemistry  
**Project:** QuickIce v3.5 Interface Enhancements  
**Researched:** 2026-04-12  
**Overall confidence:** HIGH (verified against existing codebase patterns)

---

## Executive Summary

This research addresses integrating three new features into QuickIce's existing MVVM architecture:

1. **Triclinic→orthogonal transformation service** — Currently, QuickIce rejects triclinic cells (Ice II, V) with an error. The transformation service will convert these to equivalent orthogonal representations for interface generation.

2. **CLI `--interface` flag handling** — Extend the CLI to support interface generation directly from command line, mirroring Tab 2 GUI functionality.

3. **Water density calculation service** — New service module for water density calculations using IAPWS standards, supporting both liquid water and Ice Ih density lookups.

**Key architectural insight:** All three features follow the established service layer pattern — new modules in `structure_generation/` that integrate with existing ViewModel→Worker pipeline without modifying core generation logic.

---

## 1. Integration Points with Existing Architecture

### 1.1 Current Architecture Overview

The existing QuickIce architecture follows a well-established MVVM pattern:

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLI Layer                                  │
│  quickice/main.py → cli/parser.py (argparse)                        │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         ViewModel Layer                              │
│  gui/viewmodel.py (MainViewModel)                                    │
│  ├── Tab 1 signals: generation_started/complete/error               │
│  ├── Tab 2 signals: interface_generation_started/complete/error     │
│  └── Manages QThread workers                                        │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Worker Layer                                 │
│  gui/workers.py                                                      │
│  ├── GenerationWorker (Tab 1 ice generation)                        │
│  └── InterfaceGenerationWorker (Tab 2 interface)                    │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Service/Model Layer                             │
│  structure_generation/                                               │
│  ├── generator.py (IceStructureGenerator)                          │
│  ├── interface_builder.py (validate, generate_interface)           │
│  ├── modes/ (slab.py, pocket.py, piece.py)                          │
│  └── types.py (Candidate, InterfaceConfig, InterfaceStructure)     │
│                                                                      │
│  phase_mapping/                                                      │
│  └── lookup.py (lookup_phase)                                       │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          View Layer                                  │
│  gui/main_window.py (QMainWindow + QTabWidget)                      │
│  ├── Tab 1: generation controls + viewer                            │
│  └── Tab 2: interface_panel + interface_viewer                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 New Feature Integration Points

#### Feature 1: Triclinic→Orthogonal Transformation

**Integration point:** `structure_generation/interface_builder.py`

The existing validation function `is_cell_orthogonal()` (lines 25-40 in interface_builder.py) detects triclinic cells and raises `InterfaceGenerationError`. This will be extended to:

1. **Detect** triclinic cells (existing behavior)
2. **Attempt transformation** to orthogonal (NEW)
3. **Use transformed cell** for interface generation (NEW)

```python
# Current code (interface_builder.py:119-130)
if not is_cell_orthogonal(candidate.cell):
    raise InterfaceGenerationError(
        f"Triclinic (non-orthogonal) cell detected..."
    )

# New flow:
if not is_cell_orthogonal(candidate.cell):
    # NEW: Attempt transformation
    transformed = transform_triclinic_to_orthogonal(candidate.cell)
    candidate = Candidate(
        ...,
        cell=transformed  # Use orthogonal version
    )
```

**New module:** `quickice/structure_generation/cell_transformer.py`

| Function | Responsibility |
|----------|----------------|
| `transform_triclinic_to_orthogonal(cell)` | Convert triclinic to orthogonal using lattice parameter extraction |
| `extract_lattice_parameters(cell)` | Extract a, b, c, α, β, γ from triclinic cell matrix |
| `build_orthogonal_cell(a, b, c)` | Construct orthogonal cell from lattice parameters |

#### Feature 2: CLI `--interface` Flag

**Integration point:** `cli/parser.py` and `cli/interface_parser.py` (NEW)

```python
# Current CLI arguments (cli/parser.py:35-96)
# --temperature, --pressure, --nmolecules, --output, --gromacs

# New CLI arguments for v3.5
# --interface [mode]       Interface mode: slab|pocket|piece
# --interface-box-x        Box X dimension (nm)
# --interface-box-y        Box Y dimension (nm)  
# --interface-box-z        Box Z dimension (nm)
# --ice-thickness          Ice layer thickness (slab mode)
# --water-thickness        Water layer thickness (slab mode)
# --pocket-diameter        Pocket diameter (pocket mode)
```

**CLI flow change:**

```
Current: main.py → lookup_phase → generate_candidates → rank_candidates → output

New with --interface:
  main.py → lookup_phase → generate_candidates → rank_candidates
          → select candidate → generate_interface → output_interface
```

**New module:** `quickice/cli/interface_parser.py`

| Function | Responsibility |
|----------|----------------|
| `add_interface_arguments(parser)` | Add --interface group to argparse |
| `parse_interface_args(args)` | Parse interface-specific arguments |
| `validate_interface_args(args)` | Cross-validate interface parameters |

#### Feature 3: Water Density Calculation Service

**Integration point:** New module `structure_generation/density_service.py`

This service provides IAPWS-standard density calculations:

| Function | Responsibility |
|----------|----------------|
| `get_water_density(temperature, pressure)` | IAPWS-95 liquid water density |
| `get_ice_ih_density(temperature)` | IAPWS R10-06 Ice Ih density |
| `calculate_water_molecules(box_volume, temperature, pressure)` | Convert box volume to molecule count |
| `calculate_ice_molecules(box_volume, temperature)` | Convert box volume to ice molecules |

**Integration with existing modules:**

- `interface_builder.py`: Use density service to auto-calculate water layer molecule count
- `water_filler.py`: Use density for realistic water placement
- `cli/main.py`: Display density information in CLI output

---

## 2. New Components vs. Modified Components

### 2.1 New Components (Files to Create)

| File | Location | Purpose |
|------|----------|---------|
| `cell_transformer.py` | `quickice/structure_generation/` | Triclinic→orthogonal transformation |
| `density_service.py` | `quickice/structure_generation/` | IAPWS density calculations |
| `interface_parser.py` | `quickice/cli/` | CLI interface argument handling |

### 2.2 Modified Components (Files to Update)

| File | Changes |
|------|---------|
| `structure_generation/__init__.py` | Export new functions/classes |
| `cli/parser.py` | Add --interface argument group |
| `cli/__init__.py` | Export interface parser |
| `main.py` | Handle --interface flag execution |
| `interface_builder.py` | Call cell_transformer on triclinic detection |
| `structure_generation/types.py` | Add density-related fields (optional) |

### 2.3 No Changes Required

| Component | Rationale |
|-----------|-----------|
| `gui/viewmodel.py` | Existing interface signals sufficient |
| `gui/workers.py` | Existing workers handle interface generation |
| `gui/main_window.py` | Tab 2 already exists; may add UI for new features |
| `structure_generation/generator.py` | Ice generation unchanged |

---

## 3. Data Flow Changes

### 3.1 Current Data Flow (v3.0)

```
User Input (T, P, N)
        │
        ▼
MainViewModel.start_generation()
        │
        ▼
GenerationWorker (QThread)
        │
        ├─► lookup_phase(T, P) ──► PhaseInfo
        │
        ├─► generate_candidates() ──► [Candidate]
        │
        └─► rank_candidates() ──► RankingResult
                │
                ▼
        ViewModel.ranked_candidates_ready
                │
                ▼
        GUI displays candidates
```

### 3.2 New Data Flow (v3.5) — Interface with Triclinic

```
User Input (T, P, N, InterfaceConfig)
        │
        ▼
MainViewModel.start_interface_generation()
        │
        ▼
InterfaceGenerationWorker (QThread)
        │
        ├─► validate_interface_config()
        │
        ├─► is_cell_orthogonal(candidate.cell)
        │          │
        │          ▼ (if triclinic)
        │   transform_triclinic_to_orthogonal()  ◄── NEW
        │          │
        │          ▼
        └─► assemble_<mode>(candidate, config)
                │
                ▼
        InterfaceStructure
                │
                ▼
        ViewModel.interface_generation_complete
                │
                ▼
        GUI displays interface
```

### 3.3 New Data Flow (v3.5) — CLI Interface

```
CLI: quickice --temperature 250 --pressure 100 --nmolecules 128 \
         --interface slab --interface-box-x 5 --interface-box-y 5 \
         --interface-box-z 10 --ice-thickness 3 --water-thickness 4
        │
        ▼
cli/parser.parse_args()
        │
        ├─► Standard args validated
        │
        └─► Interface args validated ──► InterfaceConfig  ◄── NEW
        │
        ▼
main.py with --interface flag
        │
        ├─► lookup_phase(T, P)
        │
        ├─► generate_candidates() → Candidate
        │
        ├─► generate_interface(candidate, config)
        │         │
        │         ├── is_cell_orthogonal() ──► transform_triclinic() (if needed)
        │         │
        │         └── assemble_<mode>()
        │
        └─► output_interface() ──► PDB/CIF files
```

---

## 4. Suggested Build Order

### Phase 1: Density Service Foundation

**Rationale:** Lowest risk, foundational for other features

| Task | Files | Dependencies |
|------|-------|--------------|
| Create `density_service.py` | New module | None |
| Add unit tests | tests/test_density_service.py | density_service |
| Update `__init__.py` exports | structure_generation/__init__.py | density_service |

**Why first:** Independent of other features, validates IAPWS integration approach

### Phase 2: Triclinic Transformation Service

**Rationale:** Unblocks interface generation for Ice II, V phases

| Task | Files | Dependencies |
|------|-------|--------------|
| Create `cell_transformer.py` | New module | None |
| Add unit tests | tests/test_cell_transformer.py | cell_transformer |
| Update `interface_builder.py` | Call transformer on triclinic detect | cell_transformer |
| Integration test | tests/test_triclinic_interface.py | cell_transformer, interface_builder |

**Why second:** Uses density service for validation, unblocks Phase 3

### Phase 3: CLI Interface Integration

**Rationale:** Builds on existing CLI patterns, separate from GUI

| Task | Files | Dependencies |
|------|-------|--------------|
| Create `cli/interface_parser.py` | New module | None |
| Update `cli/parser.py` | Add --interface args | interface_parser |
| Update `main.py` | Handle --interface flag | interface_parser, interface_builder |
| Add CLI integration tests | tests/test_cli_interface.py | cli modules |

**Why third:** Independent of density/triclinic; can use existing orthogonal cells

### Phase 4: Integration & Polish

**Rationale:** Bring features together, add UI if needed

| Task | Files | Dependencies |
|------|-------|--------------|
| End-to-end CLI test | Full flow | All previous phases |
| GUI enhancement (optional) | main_window.py | density_service for display |
| Documentation | CLI help, docstrings | All modules |

---

## 5. Technical Details

### 5.1 Triclinic→Orthogonal Transformation Algorithm

The transformation converts a triclinic cell to an equivalent orthogonal cell by:

1. **Extract lattice parameters** from cell matrix:
   ```python
   a = norm(cell[0])
   b = norm(cell[1])
   c = norm(cell[2])
   alpha = arccos(dot(cell[1], cell[2]) / (b*c))
   beta = arccos(dot(cell[0], cell[2]) / (a*c))
   gamma = arccos(dot(cell[0], cell[1]) / (a*b))
   ```

2. **Build orthogonal cell** preserving volume:
   ```python
   # Orthogonal cell with same volume
   volume = abs(det(cell))
   orthogonal = diag(
       a,
       b * sin(alpha),
       volume / (a * b * sin(alpha))
   )
   ```

3. **Scale positions** to fit new cell:
   ```python
   # Positions already in fractional coords relative to cell
   # Just need to reinterpret in orthogonal cell
   ```

### 5.2 Density Service IAPWS Integration

```python
# Using iapws library (already installed: iapws==1.5.5)
from iapws import Water, Ice

# Liquid water density (IAPWS-95)
water = Water(T=temperature, P=pressure)  # T in K, P in MPa
rho_liquid = water.rho  # kg/m³ → convert to g/cm³

# Ice Ih density (IAPWS R10-06)
# Note: IAPWS library may not have Ice Ih; may need manual implementation
# Based on: ρ = 0.9167 - 1.4e-4 * (T - 273.15) g/cm³
rho_ice = 0.9167 - 1.4e-4 * (temperature - 273.15)
```

### 5.3 CLI Argument Group Structure

```python
# New argument group in cli/parser.py
interface_group = parser.add_argument_group(
    'interface generation',
    'Options for ice-water interface generation (requires --interface)'
)
interface_group.add_argument(
    '--interface', choices=['slab', 'pocket', 'piece'],
    help='Generate ice-water interface with specified mode'
)
# ... box dimensions, mode-specific args
```

---

## 6. Architecture Patterns to Follow

### 6.1 Service Layer Pattern

All new features follow the established service pattern:

```python
# Structure:
quickice/structure_generation/
    ├── density_service.py      # New
    │   def get_water_density(T, P) -> float: ...
    │
    ├── cell_transformer.py     # New
    │   def transform_triclinic_to_orthogonal(cell) -> np.ndarray: ...
    │
    └── interface_builder.py    # Existing, modified
        def generate_interface(candidate, config):
            # NEW: Uses cell_transformer
            if not is_cell_orthogonal(candidate.cell):
                candidate.cell = transform_triclinic_to_orthogonal(candidate.cell)
```

### 6.2 CLI Extension Pattern

```python
# Structure:
quickice/cli/
    ├── parser.py               # Existing
    │   def create_parser() -> ArgumentParser:
    │
    └── interface_parser.py    # New
        def add_interface_args(parser): ...
        def parse_interface_args(ns): ...
```

### 6.3 Worker→Service Integration Pattern

```python
# In workers.py, generation already calls services:
def run(self):
    from quickice.structure_generation import generate_interface
    
    # This will internally use cell_transformer if needed
    result = generate_interface(self._candidate, self._config)
```

---

## 7. Anti-Patterns to Avoid

### 7.1 Don't Modify Core Generation

**Anti-pattern:** Adding triclinic support to `generator.py` (GenIce wrapper)

**Why bad:** GenIce generates triclinic cells for certain phases by design. QuickIce should transform post-generation, not modify GenIce behavior.

**Correct:** Transform in `interface_builder.py` before assembly

### 7.2 Don't Duplicate Validation Logic

**Anti-pattern:** Separate validation for CLI and GUI

**Why bad:** Inconsistent behavior, maintenance burden

**Correct:** CLI parses → creates InterfaceConfig → uses same `validate_interface_config()` as GUI

### 7.3 Don't Block UI Thread

**Anti-pattern:** Running density calculations on main thread

**Why bad:** Density lookups may involve interpolation, could cause UI freeze

**Correct:** All new services are called from Worker.run() which runs in QThread

---

## 8. Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Integration points | HIGH | Verified against existing viewmodel/worker patterns |
| Build order | HIGH | Follows dependency graph correctly |
| Triclinic algorithm | MEDIUM | Standard crystallographic approach, needs validation |
| Density service | HIGH | IAPWS library already in use (seawater) |
| CLI patterns | HIGH | Matches existing argparse structure |

---

## 9. Sources

### Primary (HIGH Confidence)

1. **QuickIce codebase** — Verified existing architecture patterns
   - `gui/viewmodel.py` — MVVM signal/slot patterns
   - `gui/workers.py` — QThread worker implementation
   - `cli/parser.py` — CLI argument structure
   - `structure_generation/interface_builder.py` — Service layer pattern
   - `structure_generation/generator.py` — Cell parsing (triclinic handling at lines 191-206)

2. **IAPWS Python library** — Already installed (`iapws==1.5.5`)
   - Documentation: https://pypi.org/project/iapws/
   - Used for seawater phase diagram (existing feature)

### Secondary (MEDIUM Confidence)

3. **GenIce2 documentation** — Triclinic cell handling
   - https://pypi.org/project/GenIce/
   - Cell format parsing verified in `generator.py:149-208`

4. **Previous research** — ARCHITECTURE_INTERFACE.md for interface generation patterns

---

## 10. Open Questions

1. **Triclinic transformation accuracy:** Should transformed cells preserve exact volume, or accept approximate volume for visualization purposes?

2. **Density at extreme conditions:** IAPWS equations valid for specific T,P ranges. How to handle out-of-range values (error vs. extrapolation)?

3. **CLI interface mode defaults:** What default values for box dimensions when not specified?

4. **Backward compatibility:** If triclinic transformation produces unexpected results, should users be able to disable it and get original error?

---

*Research completed: 2026-04-12*  
*Ready for roadmap creation: yes*