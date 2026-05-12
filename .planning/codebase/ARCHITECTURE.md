# Architecture

**Analysis Date:** 2026-05-12

## Pattern Overview

**Overall:** Modular Pipeline with MVVM GUI Layer

**Key Characteristics:**
- **Pipeline architecture**: Sequential data flow through processing stages (Phase Mapping → Generation → Ranking → Output)
- **MVVM for GUI**: Model-View-ViewModel pattern with PySide6/Qt for the graphical interface
- **Functional core**: Business logic is purely functional with dataclasses for immutable data structures
- **Dual interfaces**: Both CLI and GUI interfaces share the same core processing pipeline

## Layers

### CLI Layer
- **Purpose**: Command-line interface for batch processing and scripting
- **Location**: `quickice/cli/`, `quickice.py` (entry point), `quickice/main.py`
- **Contains**: Argument parsing, validation, main orchestration
- **Depends on**: All core processing modules (phase_mapping, structure_generation, ranking, output)
- **Used by**: End users via command line

### GUI Layer
- **Purpose**: Interactive graphical interface with 3D visualization
- **Location**: `quickice/gui/`
- **Contains**: 
  - Views: `main_window.py`, `view.py`, various panel files
  - ViewModel: `viewmodel.py` for state management
  - Workers: `workers.py`, `hydrate_worker.py` for background threading
  - Renderers: `molecular_viewer.py`, `hydrate_renderer.py`, `ion_renderer.py`, etc.
  - Exporters: `export.py`, `hydrate_export.py`
- **Depends on**: Core processing modules, PySide6, VTK
- **Used by**: End users via GUI application

### Phase Mapping Layer
- **Purpose**: Determine ice phase from temperature/pressure conditions
- **Location**: `quickice/phase_mapping/`
- **Contains**: Curve-based phase lookup using IAPWS R14-08 melting curves
- **Depends on**: `iapws` library, `scipy`, `numpy`
- **Used by**: Main orchestration, GUI, CLI

### Structure Generation Layer
- **Purpose**: Generate ice crystal structures using GenIce
- **Location**: `quickice/structure_generation/`
- **Contains**: 
  - Generator: `generator.py` wraps GenIce API
  - Interface Builder: `interface_builder.py` for ice-water interfaces
  - Modes: `modes/slab.py`, `modes/pocket.py`, `modes/piece.py`
  - Inserters: `ion_inserter.py`, `solute_inserter.py`, `custom_molecule_inserter.py`
  - Hydrate: `hydrate_generator.py`
  - Types: `types.py` with all dataclasses
- **Depends on**: GenIce2, numpy, phase_mapping module
- **Used by**: Main orchestration, GUI workers

### Ranking Layer
- **Purpose**: Score and rank generated ice structure candidates
- **Location**: `quickice/ranking/`
- **Contains**: Energy, density, and diversity scoring algorithms
- **Depends on**: numpy, scipy (KDTree), structure_generation types
- **Used by**: Main orchestration

### Output Layer
- **Purpose**: Export structures to PDB, GROMACS formats and generate phase diagrams
- **Location**: `quickice/output/`
- **Contains**: PDB writer, GROMACS writer, phase diagram generator, validator, orchestrator
- **Depends on**: matplotlib, spglib, ranking types
- **Used by**: Main orchestration, GUI exporters

### Validation Layer
- **Purpose**: Input validation for CLI and GUI
- **Location**: `quickice/validation/`
- **Contains**: Validators for temperature, pressure, molecule count
- **Depends on**: argparse (for ArgumentTypeError)
- **Used by**: CLI parser, GUI input panels

### Data Layer
- **Purpose**: Static data files (force field parameters, templates)
- **Location**: `quickice/data/`
- **Contains**: ITP files (tip4p-ice.itp, ch4.itp, thf.itp), GRO templates, custom molecule storage
- **Depends on**: None (static files)
- **Used by**: Output layer (GROMACS writer), structure generation

## Data Flow

### Ice Generation Pipeline

1. **Input Validation** (`quickice/validation/validators.py`)
   - User provides temperature (K), pressure (MPa), molecule count
   - Validators check ranges: T=[0,500], P=[0,10000], N=[4,100000]

2. **Phase Lookup** (`quickice/phase_mapping/lookup.py`)
   - `lookup_phase(T, P)` returns phase_id, phase_name, density
   - Uses curve-based boundary evaluation (IAPWS R14-08)

3. **Structure Generation** (`quickice/structure_generation/generator.py`)
   - `generate_candidates(phase_info, nmolecules)` creates multiple candidates
   - GenIce generates ice lattices with diverse hydrogen bond networks
   - Each candidate has: positions, atom_names, cell, nmolecules, phase_id, seed

4. **Ranking** (`quickice/ranking/scorer.py`)
   - `rank_candidates(candidates)` scores by energy, density, diversity
   - Lower combined score = better structure

5. **Output** (`quickice/output/orchestrator.py`)
   - `output_ranked_candidates()` writes PDB files, validates structures
   - Optional GROMACS export (.gro, .top, .itp)
   - Optional phase diagram generation

### Interface Generation Pipeline

1. **Phase Lookup** → Get ice phase info

2. **Ice Generation** → Create single ice candidate

3. **Interface Assembly** (`quickice/structure_generation/interface_builder.py`)
   - `generate_interface(candidate, config)` assembles ice + water
   - Mode routing to slab/pocket/piece implementations

4. **Optional Insertions** (sequential pipeline):
   - Ion insertion → `IonInserter.insert_ions()`
   - Solute insertion → `solute_inserter.insert_solutes()`
   - Custom molecule insertion → `custom_molecule_inserter.insert_custom_molecules()`

5. **GROMACS Export** → Write .gro, .top, .itp files

### Hydrate Generation Pipeline

1. **Config Setup** (`HydrateConfig`) → Lattice type, guest, occupancy

2. **Hydrate Generation** (`quickice/structure_generation/hydrate_generator.py`)
   - `HydrateStructureGenerator` uses GenIce hydrate lattices (CS1, CS2, sH)
   - Places guest molecules in cages

3. **Export** → GROMACS files with guest .itp includes

### State Management

**GUI State:**
- `MainViewModel` stores `_last_ranking_result`, `_last_interface_result`, `_current_hydrate_result`
- Results cached for export operations
- Thread-safe via Qt signal/slot mechanism

**CLI State:**
- Stateless: each invocation processes independently
- No persistent state between runs

## Key Abstractions

### Candidate
- **Purpose**: Represents a generated ice structure with all atomic data
- **Examples**: `quickice/structure_generation/types.py` (lines 95-122)
- **Pattern**: Immutable dataclass with numpy arrays for positions

### InterfaceStructure
- **Purpose**: Combined ice + water + guests structure with region tracking
- **Examples**: `quickice/structure_generation/types.py` (lines 218-269)
- **Pattern**: Dataclass with atom count boundaries (ice_atom_count, water_atom_count, guest_atom_count)

### HydrateStructure
- **Purpose**: Hydrate lattice with water framework and guest molecules
- **Examples**: `quickice/structure_generation/types.py` (lines 627-718)
- **Pattern**: Dataclass with `to_candidate()` method for interface integration

### MoleculeIndex
- **Purpose**: Tracks variable-length molecules in atom arrays
- **Examples**: `quickice/structure_generation/types.py` (lines 21-39)
- **Pattern**: (start_idx, count, mol_type) tuple for multi-molecule-type systems

### GenerationResult / RankingResult / OutputResult
- **Purpose**: Result containers for each pipeline stage
- **Pattern**: Immutable dataclass carrying both data and metadata

## Entry Points

### CLI Entry Point
- **Location**: `quickice.py`
- **Triggers**: `python quickice.py --temperature 300 --pressure 100 --nmolecules 256`
- **Responsibilities**: 
  - Parse arguments via `get_arguments()`
  - Orchestrate full pipeline
  - Handle errors and exit codes

### GUI Entry Point
- **Location**: `quickice/gui/__main__.py`
- **Triggers**: `python -m quickice.gui`
- **Responsibilities**:
  - Create QApplication
  - Instantiate MainWindow
  - Start Qt event loop

### Main Module
- **Location**: `quickice/main.py`
- **Triggers**: Imported by quickice.py
- **Responsibilities**:
  - `main()` function orchestrates CLI workflow
  - Prints progress and results to stdout
  - Handles UnknownPhaseError, InterfaceGenerationError

## Error Handling

**Strategy**: Exception-based with custom error classes

**Patterns:**
- Custom exceptions: `UnknownPhaseError`, `InterfaceGenerationError`, `StructureGenerationError`
- Descriptive error messages with context and suggested fixes
- Validation fail-fast: check preconditions before expensive operations
- GUI: Errors emitted as signals, displayed in status/log panels
- CLI: Errors printed to stderr with exit code 1

**Error Classes:**
- `quickice/phase_mapping/errors.py`: `PhaseMappingError`, `UnknownPhaseError`
- `quickice/structure_generation/errors.py`: `StructureGenerationError`, `UnsupportedPhaseError`, `InterfaceGenerationError`

## Cross-Cutting Concerns

**Logging:** Python `logging` module, configured in GUI main_window.py

**Validation:** 
- Input validation in `quickice/validation/validators.py`
- Runtime validation in dataclass `__post_init__` methods
- Pre-generation validation in `validate_interface_config()`

**Authentication:** Not applicable (local desktop application)

**Threading:**
- GUI uses QThread for background generation
- Workers emit progress/status signals to UI
- Generation is NOT thread-safe (GenIce uses global numpy random state)

**Testing:**
- Unit tests in `tests/` directory
- pytest framework
- Integration tests for CLI and GUI workflows

---

*Architecture analysis: 2026-05-12*
