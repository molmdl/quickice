# Architecture

**Analysis Date:** 2026-03-31

## Pattern Overview

**Overall:** Pipeline Architecture with Modular Processing Stages

**Key Characteristics:**
- Sequential data flow through distinct processing phases
- Each module exposes a clean public API via `__init__.py`
- Data types defined in dedicated `types.py` files within each module
- Error handling via custom exception classes per module
- Single responsibility: each module handles one pipeline stage

## Layers

**CLI Layer:**
- Purpose: Parse and validate command-line arguments
- Location: `quickice/cli/`
- Contains: Argument parser, validation type converters
- Depends on: `quickice/validation/validators.py`
- Used by: `quickice/main.py`

**Validation Layer:**
- Purpose: Input validation with clear error messages
- Location: `quickice/validation/`
- Contains: Temperature, pressure, molecule count validators
- Depends on: Python standard library only
- Used by: `quickice/cli/parser.py`

**Phase Mapping Layer:**
- Purpose: Map temperature/pressure conditions to ice phase
- Location: `quickice/phase_mapping/`
- Contains: Curve-based phase lookup, melting curves, solid boundaries, triple points
- Depends on: IAPWS library (via `iapws` package)
- Used by: `quickice/main.py`

**Structure Generation Layer:**
- Purpose: Generate ice structure candidates using GenIce2
- Location: `quickice/structure_generation/`
- Contains: GenIce wrapper, phase-to-lattice mapping, supercell calculation
- Depends on: `genice2`, `numpy`
- Used by: `quickice/main.py`

**Ranking Layer:**
- Purpose: Score and rank candidates by energy, density, diversity
- Location: `quickice/ranking/`
- Contains: Scoring functions, normalization, ranking algorithm
- Depends on: `numpy`, `scipy`
- Used by: `quickice/main.py`

**Output Layer:**
- Purpose: Write PDB files, validate structures, generate phase diagrams
- Location: `quickice/output/`
- Contains: PDB writer, space group validator, phase diagram generator, orchestrator
- Depends on: `matplotlib`, `spglib`, `shapely`
- Used by: `quickice/main.py`

## Data Flow

**Main Pipeline:**

1. User invokes `quickice.py` with temperature, pressure, molecule count
2. CLI parser validates inputs using type converters
3. `main.py` orchestrates the pipeline:
   - Calls `lookup_phase(T, P)` → returns phase info dict
   - Calls `generate_candidates(phase_info, nmolecules)` → returns `GenerationResult`
   - Calls `rank_candidates(candidates)` → returns `RankingResult`
   - Calls `output_ranked_candidates(ranking_result, output_dir)` → returns `OutputResult`
4. Results printed to stdout and written to output directory

**State Management:**
- No global state; each function is pure or uses local state
- Data flows through immutable dataclasses (`Candidate`, `GenerationResult`, `RankedCandidate`, `RankingResult`, `OutputResult`)
- Random state managed explicitly in `IceStructureGenerator._generate_single()` for reproducibility

## Key Abstractions

**Candidate:**
- Purpose: Represents a single generated ice structure
- Examples: `quickice/structure_generation/types.py`
- Pattern: Dataclass with positions, cell, metadata

**Phase Lookup:**
- Purpose: Determine ice phase from T,P using curve-based evaluation
- Examples: `quickice/phase_mapping/lookup.py`
- Pattern: Hierarchical boundary evaluation (high pressure to low pressure)

**Scoring Functions:**
- Purpose: Evaluate candidate quality
- Examples: `quickice/ranking/scorer.py`
- Pattern: Independent scoring components combined with weights

**Orchestrator:**
- Purpose: Coordinate multiple output operations
- Examples: `quickice/output/orchestrator.py`
- Pattern: Single entry point that calls multiple sub-functions

## Entry Points

**CLI Entry Point:**
- Location: `quickice.py`
- Triggers: User runs `python quickice.py --temperature T --pressure P --nmolecules N`
- Responsibilities: Import and call `main()` from `quickice/main.py`

**Programmatic Entry Point:**
- Location: `quickice/main.py::main()`
- Triggers: CLI entry point or direct import
- Responsibilities: Parse args, orchestrate pipeline phases, print results

**Test Entry Points:**
- Location: `tests/test_*.py`
- Triggers: `pytest` command
- Responsibilities: Test each module independently and integration tests

## Error Handling

**Strategy:** Custom exceptions per module with contextual information

**Patterns:**
- Base exception per module: `PhaseMappingError`, `StructureGenerationError`
- Specific exception subclasses: `UnknownPhaseError`, `UnsupportedPhaseError`
- Exceptions include context: temperature, pressure values in error messages
- Graceful degradation: phase diagram generation failures logged but don't halt pipeline
- Exit codes: `main()` returns 0 for success, 1 for errors

**Exception Hierarchy:**
```
PhaseMappingError (base)
└── UnknownPhaseError

StructureGenerationError (base)
└── UnsupportedPhaseError
```

## Cross-Cutting Concerns

**Logging:** Python `logging` module used in output orchestrator
**Validation:** Input validation at CLI layer via argparse type converters
**Unit Conversion:** Positions stored in nm, converted to Angstrom for PDB output
**Security:** Path traversal protection in `output_ranked_candidates()`

## Module Dependencies

```
main.py
├── cli/parser.py
│   └── validation/validators.py
├── phase_mapping/
│   ├── lookup.py
│   ├── melting_curves.py
│   ├── solid_boundaries.py
│   └── triple_points.py
├── structure_generation/
│   ├── generator.py
│   ├── mapper.py
│   └── types.py
├── ranking/
│   ├── scorer.py
│   └── types.py
└── output/
    ├── orchestrator.py
    ├── pdb_writer.py
    ├── validator.py
    └── phase_diagram.py
```

---

*Architecture analysis: 2026-03-31*
