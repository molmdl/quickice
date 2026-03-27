"""Orchestrator function for coordinating all output operations.

Wires together PDB writing, validation, and phase diagram generation
into a single entry point for complete Phase 5 output.
"""

import logging
from pathlib import Path

from quickice.output.types import OutputResult
from quickice.output.pdb_writer import write_pdb_with_cryst1
from quickice.output.validator import validate_space_group, check_atomic_overlap
from quickice.output.phase_diagram import generate_phase_diagram
from quickice.ranking.types import RankingResult


def output_ranked_candidates(
    ranking_result: RankingResult,
    output_dir: str,
    base_name: str = "ice_candidate",
    generate_diagram: bool = True,
    user_t: float | None = None,
    user_p: float | None = None,
) -> OutputResult:
    """Coordinate all output operations for ranked ice structure candidates.

    This function is the main entry point for Phase 5 output. It:
    - Writes top 10 ranked candidates as PDB files with CRYST1 records
    - Validates each structure (space group, atomic overlap)
    - Optionally generates a phase diagram if user T,P provided

    Args:
        ranking_result: RankingResult with ranked_candidates from Phase 4
        output_dir: Directory to write output files
        base_name: Base filename for PDB files (default: "ice_candidate")
        generate_diagram: Whether to generate phase diagram (default: True)
        user_t: User's temperature in Kelvin (required for diagram)
        user_p: User's pressure in MPa (required for diagram)

    Returns:
        OutputResult with:
        - output_files: List of PDB file paths
        - phase_diagram_files: List of diagram file paths (empty if not generated)
        - validation_results: Per-structure validation info
        - summary: Summary info (n_candidates, n_validated, user_T, user_P)
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Initialize result containers
    output_files: list[str] = []
    phase_diagram_files: list[str] = []
    validation_results: list[dict[str, any]] = []

    # Process top 10 ranked candidates
    for ranked_candidate in ranking_result.ranked_candidates[:10]:
        candidate = ranked_candidate.candidate
        rank = ranked_candidate.rank

        # Write PDB file
        filename = f"{base_name}_{rank:02d}.pdb"
        filepath = output_path / filename

        try:
            write_pdb_with_cryst1(candidate, str(filepath))
            output_files.append(str(filepath))
        except Exception as e:
            logging.warning(f"Failed to write PDB for rank {rank}: {e}")
            continue

        # Validate structure
        try:
            val_result = validate_space_group(candidate)
            has_overlap = check_atomic_overlap(candidate)

            # Store validation result
            validation_results.append({
                'rank': rank,
                'file': filename,
                'spacegroup': val_result.get('spacegroup_symbol', 'UNKNOWN'),
                'valid': val_result.get('valid', False) and not has_overlap,
                'has_overlap': has_overlap,
            })

            # Warn if validation issues
            if not val_result.get('valid', False):
                logging.warning(
                    f"Rank {rank} ({filename}): Space group validation failed"
                )
            if has_overlap:
                logging.warning(
                    f"Rank {rank} ({filename}): Atomic overlap detected"
                )

        except Exception as e:
            logging.warning(f"Validation failed for rank {rank}: {e}")
            # Store partial result
            validation_results.append({
                'rank': rank,
                'file': filename,
                'spacegroup': 'UNKNOWN',
                'valid': False,
                'has_overlap': None,
                'error': str(e),
            })

    # Generate phase diagram if requested and T,P provided
    if generate_diagram and user_t is not None and user_p is not None:
        try:
            phase_diagram_files = generate_phase_diagram(
                user_t, user_p, output_dir
            )
        except Exception as e:
            logging.warning(f"Failed to generate phase diagram: {e}")
            phase_diagram_files = []

    # Create summary
    n_validated = sum(1 for v in validation_results if v.get('valid', False))
    summary = {
        'n_candidates': len(output_files),
        'n_validated': n_validated,
        'user_T': user_t,
        'user_P': user_p,
    }

    return OutputResult(
        output_files=output_files,
        phase_diagram_files=phase_diagram_files,
        validation_results=validation_results,
        summary=summary,
    )
