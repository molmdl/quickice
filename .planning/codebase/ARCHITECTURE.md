# Architecture

**Analysis Date:** 2026-05-02

## Pattern Overview

**Overall:** Layered architecture with MVVM for GUI

**Key Characteristics:**
- Domain-driven modules with single responsibility
- Pipeline pattern for data flow (phase lookup → generation → ranking → output)
- MVVM separation for GUI (View/ViewModel)
- Strategy pattern for interface modes (slab/pocket/piece)
- Factory pattern for structure generation

## Layers

**CLI Layer:**
- Purpose: Command-line argument parsing and orchestration
- Location: `quickice/cli/`
- Contains: Argument parser, validation routing
- Depends on: All domain modules
- Used by: `quickice.py` entry point

**GUI Layer:**
- Purpose: Graphical user interface with 3D visualization
- Location: `quickice/gui/`
- Contains: Qt widgets, VTK viewers, MVVM View/ViewModel
- Depends on: All domain modules, PySide6, VTK
- Used by: `python -m quickice.gui` entry point

**Phase Mapping Layer:**
- Purpose: Determine ice phase from T/P conditions using IAPWS curves
- Location: `quickice/phase_mapping/`
- Contains: Curve-based phase lookup, triple points, melting curves
- Depends on: `iapws` library, numpy
- Used by: Main workflow, GUI phase diagram

**Structure Generation Layer:**
- Purpose: Generate ice structures via GenIce, build interfaces
- Location: `quickice/structure_generation/`
- Contains: GenIce wrapper, interface builder, hydrate generator, ion inserter
- Depends on: `genice2`, numpy, scipy
- Used by: Main workflow, GUI

**Ranking Layer:**
- Purpose: Score and rank ice structure candidates
- Location: `quickice/ranking/`
- Contains: Energy/density/diversity scoring functions
- Depends on: numpy, scipy (KDTree for O-O distance calculation)
- Used by: Main workflow

**Output Layer:**
- Purpose: Write PDB/GRO/TOP files, generate phase diagrams
- Location: `quickice/output/`
- Contains: PDB writer, GROMACS writer, phase diagram generator, orchestrator
- Depends on: matplotlib (diagrams), spglib (validation)
- Used by: Main workflow, GUI export

**Validation Layer:**
- Purpose: Input validation for CLI arguments
- Location: `quickice/validation/`
- Contains: Temperature/pressure/molecule count validators
- Depends on: None
- Used by: CLI parser, GUI validators

## Data Flow

**Standard Ice Generation Pipeline:**

1. User input (T, P, N molecules) → Input validation (`quickice/validation/validators.py`)
2. Phase lookup → `lookup_phase(T, P)` returns phase_id, density (`quickice/phase_mapping/lookup.py`)
3. Structure generation → `generate_candidates()` creates multiple candidates (`quickice/structure_generation/generator.py`)
4. Ranking → `rank_candidates()` scores and sorts (`quickice/ranking/scorer.py`)
5. Output → `output_ranked_candidates()` writes files (`quickice/output/orchestrator.py`)

**Interface Generation Pipeline:**

1. Phase lookup (same as above)
2. Single ice candidate generation
3. Interface configuration validation (`quickice/structure_generation/interface_builder.py:validate_interface_config()`)
4. Mode routing to slab/pocket/piece assembler
5. Water filling and overlap resolution (`quickice/structure_generation/water_filler.py`, `quickice/structure_generation/overlap_resolver.py`)
6. GROMACS export (GRO/TOP files)

**Hydrate Generation Pipeline:**

1. Configuration input (lattice type, guest type, occupancy)
2. GenIce2 hydrate lattice generation (`quickice/structure_generation/hydrate_generator.py`)
3. Guest molecule placement in cages
4. GROMACS export with guest ITP files

**State Management:**
- CLI: Stateless, single-pass execution
- GUI: `MainViewModel` holds state (`quickice/gui/viewmodel.py`)
- No persistent state between runs

## Key Abstractions

**Candidate:**
- Purpose: Represents a single ice structure configuration
- Examples: `quickice/structure_generation/types.py:94-122`
- Pattern: Dataclass with positions, cell, metadata
- Contains: numpy arrays for positions (N×3), cell vectors (3×3), atom names, phase_id

**GenerationResult:**
- Purpose: Container for multiple candidates with metadata
- Examples: `quickice/structure_generation/types.py:124-145`
- Pattern: Dataclass wrapping list of Candidates

**InterfaceConfig:**
- Purpose: Configuration for ice-water interface generation
- Examples: `quickice/structure_generation/types.py:147-214`
- Pattern: Dataclass with mode-specific parameters, validated in `__post_init__`

**InterfaceStructure:**
- Purpose: Combined ice + water (+ guest) structure with phase distinction
- Examples: `quickice/structure_generation/types.py:217-268`
- Pattern: Dataclass with position arrays and atom count boundaries (ice_atom_count, water_atom_count, guest_atom_count)

**HydrateStructure:**
- Purpose: Gas hydrate with water framework and guest molecules
- Examples: `quickice/structure_generation/types.py:412-502`
- Pattern: Dataclass with `to_candidate()` method for interface compatibility

**RankedCandidate:**
- Purpose: Candidate with computed scores
- Examples: `quickice/ranking/types.py`
- Pattern: Wrapper adding energy_score, density_score, diversity_score, combined_score

## Entry Points

**CLI Entry Point:**
- Location: `quickice.py`
- Triggers: User runs `python quickice.py [args]`
- Responsibilities: Delegates to `quickice.main:main()`
- Flow: Parse args → lookup_phase → generate_candidates → rank → output

**GUI Entry Point:**
- Location: `quickice/gui/__main__.py`
- Triggers: User runs `python -m quickice.gui`
- Responsibilities: Creates QApplication, instantiates MainWindow
- Flow: Event-driven UI → worker threads → callbacks

**Main Entry (shared):**
- Location: `quickice/main.py`
- Triggers: Both CLI and GUI entry points
- Responsibilities: Orchestrates the full pipeline for CLI mode

## Error Handling

**Strategy:** Exception-based with custom error types

**Patterns:**
- Domain-specific exceptions: `UnknownPhaseError`, `StructureGenerationError`, `InterfaceGenerationError`
- Error messages include context: "Box Z dimension (X nm) does not match layer thicknesses..."
- GUI errors shown in status bar/info panel, CLI errors to stderr
- Validation errors raise before expensive operations (fail-fast)

**Error Types:**
- `quickice/phase_mapping/errors.py`: `PhaseMappingError`, `UnknownPhaseError`
- `quickice/structure_generation/errors.py`: `StructureGenerationError`, `UnsupportedPhaseError`, `InterfaceGenerationError`

## Cross-Cutting Concerns

**Logging:**
- Standard Python logging module
- Used in output orchestrator for validation warnings
- No file logging (console only)

**Validation:**
- Input validation: Temperature (0-500K), pressure (0-10000 MPa), molecules (4-100000)
- Structure validation: Space group check via spglib, atomic overlap detection
- Output validation: Path traversal protection in orchestrator

**Authentication:**
- Not applicable (local desktop application)

**Threading:**
- GUI uses QThread workers for long operations (`quickice/gui/workers.py`)
- Generation operations not thread-safe (GenIce uses global numpy random state)

---

*Architecture analysis: 2026-05-02*
