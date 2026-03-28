# Architecture

**Analysis Date:** 2026-03-28

## Pattern Overview

**Overall:** Pipeline Architecture with Layered Modules

**Key Characteristics:**
- Sequential pipeline: CLI → Phase Mapping → Structure Generation → Ranking → Output
- Each phase is an independent module with clean interfaces
- Data types (dataclasses) flow between layers
- External dependencies isolated to specific layers (GenIce, spglib, matplotlib)

## Layers

**CLI Layer:**
- Purpose: Parse and validate user inputs, orchestrate pipeline execution
- Location: `quickice/cli/`
- Contains: `parser.py` for argparse setup, `main.py` for orchestration
- Depends on: All downstream layers (validation, phase_mapping, structure_generation, ranking, output)
- Used by: User via command line

**Validation Layer:**
- Purpose: Validate CLI inputs (temperature, pressure, molecule count)
- Location: `quickice/validation/validators.py`
- Contains: Type validators for argparse
- Depends on: argparse (ArgumentTypeError)
- Used by: CLI Layer

**Phase Mapping Layer:**
- Purpose: Identify ice phase from temperature/pressure conditions
- Location: `quickice/phase_mapping/`
- Contains: Curve-based lookup algorithms, boundary functions, triple point data
- Depends on: Math, internal boundary/melting curve equations
- Used by: Main pipeline, Output (phase diagram)

**Structure Generation Layer:**
- Purpose: Generate ice structure candidates using GenIce library
- Location: `quickice/structure_generation/`
- Contains: Generator class, phase-to-GenIce mapping, supercell calculations
- Depends on: GenIce2 (external), numpy
- Used by: Main pipeline

**Ranking Layer:**
- Purpose: Score and rank generated candidates by energy, density, diversity
- Location: `quickice/ranking/`
- Contains: Scoring functions, normalization, ranking logic
- Depends on: numpy, Candidate type from structure_generation
- Used by: Main pipeline

**Output Layer:**
- Purpose: Write PDB files, validate structures, generate phase diagrams
- Location: `quickice/output/`
- Contains: PDB writer, space group validator, phase diagram generator, orchestrator
- Depends on: spglib (external), matplotlib, shapely, scipy, IAPWS
- Used by: Main pipeline

## Data Flow

**Main Pipeline Flow:**

1. CLI parses arguments → validated Namespace object
2. `lookup_phase(temperature, pressure)` → phase_info dict
3. `generate_candidates(phase_info, nmolecules)` → GenerationResult with Candidate list
4. `rank_candidates(candidates)` → RankingResult with RankedCandidate list
5. `output_ranked_candidates(ranking_result, output_dir)` → OutputResult with file paths

**State Management:**
- No global state - pure functions with explicit inputs/outputs
- State passed through dataclass instances
- Each layer produces new objects, doesn't mutate inputs

## Key Abstractions

**Candidate:**
- Purpose: Represents a single generated ice structure
- Examples: `quickice/structure_generation/types.py`
- Pattern: Immutable dataclass with numpy arrays for positions/cell

```python
@dataclass
class Candidate:
    positions: np.ndarray      # (N_atoms, 3) in nm
    atom_names: list[str]      # ["O", "H", "H", ...]
    cell: np.ndarray           # (3, 3) cell vectors in nm
    nmolecules: int
    phase_id: str
    seed: int
    metadata: dict[str, Any]
```

**GenerationResult:**
- Purpose: Container for multiple candidates with metadata
- Examples: `quickice/structure_generation/types.py`
- Pattern: Result wrapper tracking requested vs actual molecule count

**RankedCandidate:**
- Purpose: Candidate with scoring breakdown
- Examples: `quickice/ranking/types.py`
- Pattern: Wraps Candidate with energy_score, density_score, diversity_score, combined_score, rank

**RankingResult:**
- Purpose: Final ranked output with metadata
- Examples: `quickice/ranking/types.py`
- Pattern: Sorted list of RankedCandidate with scoring metadata

**OutputResult:**
- Purpose: Final pipeline output with file paths and validation
- Examples: `quickice/output/types.py`
- Pattern: Result wrapper with file lists and validation status

## Entry Points

**CLI Entry Point:**
- Location: `quickice/main.py:main()`
- Triggers: `python quickice.py` or `python -m quickice.main`
- Responsibilities: Orchestrates all pipeline phases

**Package Entry:**
- Location: `quickice/__init__.py`
- Exports: `__version__ = "0.1.0"`

**Module Entry Points:**
- `quickice/phase_mapping/__init__.py` → exports `lookup_phase`, `IcePhaseLookup`
- `quickice/structure_generation/__init__.py` → exports `generate_candidates`, `IceStructureGenerator`
- `quickice/ranking/__init__.py` → exports `rank_candidates`
- `quickice/output/__init__.py` → exports `output_ranked_candidates`

## Error Handling

**Strategy:** Custom exception hierarchy with context

**Patterns:**
- Base exceptions per layer: `PhaseMappingError`, `StructureGenerationError`
- Specific exceptions: `UnknownPhaseError`, `UnsupportedPhaseError`
- Errors include context: temperature, pressure, phase_id attributes
- Main catches exceptions and returns appropriate exit codes

**Exception Flow:**
```python
# Phase mapping
raise UnknownPhaseError("No ice phase found", temperature=T, pressure=P)

# Structure generation
raise UnsupportedPhaseError("Phase not supported", phase_id="ice_xxx")

# Main handles
except UnknownPhaseError as e:
    print(f"Error: {e}", file=sys.stderr)
    return 1
```

## Cross-Cutting Concerns

**Logging:** Python logging module in output/orchestrator.py for warnings

**Validation:** 
- Input validation via argparse type functions in `validation/validators.py`
- Structure validation (space group, overlap) in `output/validator.py`

**Authentication:** Not applicable (no external services)

**Unit Conversions:**
- Internal units: nm for length, MPa for pressure, K for temperature
- PDB output: nm → Angstrom (multiply by 10.0)
- GenIce: Uses nm internally

**Configuration:**
- Phase boundary data: constants in `phase_mapping/triple_points.py`, `phase_mapping/solid_boundaries.py`
- Melting curves: IAPWS equations in `phase_mapping/melting_curves.py`
- Phase metadata: densities in `phase_mapping/lookup.py:PHASE_METADATA`

---

*Architecture analysis: 2026-03-28*
