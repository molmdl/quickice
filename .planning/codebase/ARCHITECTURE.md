# Architecture

**Analysis Date:** 2026-03-30

## Pattern Overview

**Overall:** Layered pipeline architecture

**Key Characteristics:**
- Clear separation of concerns across 6 functional layers
- Dataclass-based data flow between layers
- External dependency on GenIce for structure generation
- Single-direction pipeline (input → output)
- Functional core with CLI wrapper

## Layers

**CLI Layer:**
- Purpose: Command-line interface and argument parsing
- Location: `quickice/cli/`
- Contains: Argument parser, input validators
- Depends on: argparse, validation layer
- Used by: `quickice.py` entry point

**Validation Layer:**
- Purpose: Input validation for CLI arguments
- Location: `quickice/validation/`
- Contains: Temperature, pressure, molecule count validators
- Depends on: None (pure functions)
- Used by: CLI layer

**Phase Mapping Layer:**
- Purpose: Determine ice phase from temperature/pressure conditions
- Location: `quickice/phase_mapping/`
- Contains: Phase lookup, melting curves, solid boundaries, triple points
- Depends on: numpy, IAPWS library for melting curves
- Used by: Main orchestration

**Structure Generation Layer:**
- Purpose: Generate ice structure candidates using GenIce
- Location: `quickice/structure_generation/`
- Contains: Generator class, mapper, types, errors
- Depends on: GenIce2, numpy
- Used by: Main orchestration

**Ranking Layer:**
- Purpose: Score and rank generated candidates
- Location: `quickice/ranking/`
- Contains: Scoring functions, types
- Depends on: numpy, scipy (KDTree)
- Used by: Main orchestration

**Output Layer:**
- Purpose: Write PDB files, generate phase diagrams
- Location: `quickice/output/`
- Contains: PDB writer, validator, phase diagram generator, orchestrator
- Depends on: matplotlib, numpy, shapely, IAPWS
- Used by: Main orchestration

## Data Flow

**Pipeline Flow:**

1. User provides T, P, N via CLI
2. Validators check input ranges (T: 0-500K, P: 0-10000 MPa, N: 4-100000)
3. Phase mapping determines ice polymorph (e.g., ice_ih, ice_vii)
4. Structure generator creates N candidates with diverse hydrogen bond networks
5. Ranking scores candidates by energy, density, diversity
6. Output writes top 10 ranked PDB files + phase diagram

**State Management:**
- No global state - all data passed as arguments
- Dataclasses carry data between layers (Candidate, GenerationResult, RankingResult, OutputResult)
- Immutable flow: input dict → phase_info dict → Candidate list → RankedCandidate list → files

## Key Abstractions

**Candidate:**
- Purpose: Single generated ice structure with coordinates, cell, metadata
- Examples: `quickice/structure_generation/types.py`
- Pattern: Frozen dataclass with positions, atom_names, cell, nmolecules, phase_id, seed, metadata

**Phase Info Dict:**
- Purpose: Carry phase identification results between layers
- Examples: `quickice/phase_mapping/lookup.py` returns dict with phase_id, phase_name, density, temperature, pressure
- Pattern: Simple dict with fixed keys, passed through pipeline

**GenerationResult:**
- Purpose: Bundle generated candidates with metadata
- Examples: `quickice/structure_generation/types.py`
- Pattern: Dataclass with candidates list, requested/actual nmolecules, phase info, was_rounded flag

**RankingResult:**
- Purpose: Carry ranked candidates and scoring metadata
- Examples: `quickice/ranking/types.py`
- Pattern: Dataclass with ranked_candidates list, scoring_metadata dict, weight_config dict

**OutputResult:**
- Purpose: Summarize output files and validation results
- Examples: `quickice/output/types.py`
- Pattern: Dataclass with output_files, phase_diagram_files, validation_results, summary dict

## Entry Points

**CLI Entry Point:**
- Location: `quickice.py`
- Triggers: `python quickice.py --temperature T --pressure P --nmolecules N`
- Responsibilities: Import main() from quickice.main, call sys.exit()

**Main Orchestrator:**
- Location: `quickice/main.py`
- Triggers: Called by CLI entry point
- Responsibilities:
  - Parse CLI arguments
  - Call lookup_phase() for phase mapping
  - Call generate_candidates() for structure generation
  - Call rank_candidates() for scoring
  - Call output_ranked_candidates() for file output
  - Print progress and results
  - Handle exceptions

**Error Handling:**
- UnknownPhaseError for conditions outside phase diagram
- StructureGenerationError for GenIce failures
- SystemExit propagation for argparse errors

## Error Handling

**Strategy:** Exception-based with specific error types

**Patterns:**
- Custom exceptions in `quickice/phase_mapping/errors.py` (PhaseMappingError, UnknownPhaseError)
- Custom exceptions in `quickice/structure_generation/errors.py` (StructureGenerationError, UnsupportedPhaseError)
- ArgumentTypeError for CLI validation failures
- Logged warnings for non-fatal issues (validation failures, diagram generation)

## Cross-Cutting Concerns

**Logging:** Python logging module (warnings for validation issues)

**Validation:**
- Input: Temperature (0-500K), Pressure (0-10000 MPa), Molecules (4-100000)
- Output: Space group validation, atomic overlap detection

**Authentication:** None (scientific tool, no auth required)

**Configuration:** Command-line arguments only, no config files

**External Dependencies:**
- GenIce2: Structure generation (lattice plugin system)
- iapws: Water properties for melting curves and phase diagram
- scipy: KDTree for neighbor calculations in ranking
- matplotlib: Phase diagram visualization
- shapely: Polygon geometry for phase diagram
- numpy: Array operations throughout

---

*Architecture analysis: 2026-03-30*