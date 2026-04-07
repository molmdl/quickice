"""Main entry point for QuickIce CLI."""

import sys
from pathlib import Path

from quickice.cli.parser import get_arguments
from quickice.phase_mapping import lookup_phase, UnknownPhaseError
from quickice.structure_generation import generate_candidates
from quickice.ranking import rank_candidates
from quickice.output import output_ranked_candidates
from quickice.output.gromacs_writer import write_gro_file, write_top_file


def main() -> int:
    """Main entry point for QuickIce.
    
    Parses command-line arguments and prints validated inputs.
    
    Returns:
        Exit code (0 for success, non-zero for error).
    """
    try:
        args = get_arguments()
        
        # Print validated inputs
        print("QuickIce - Ice structure generation")
        print()
        print(f"Temperature: {args.temperature}K")
        print(f"Pressure: {args.pressure} MPa")
        print(f"Molecules: {args.nmolecules}")
        print()
        
        # Lookup phase for given conditions
        phase_info = lookup_phase(args.temperature, args.pressure)
        
        # Print phase information
        print(f"Phase: {phase_info['phase_name']} ({phase_info['phase_id']})")
        print(f"Density: {phase_info['density']} g/cm³")
        print()
        
        # Generate candidates for the phase
        gen_result = generate_candidates(
            phase_info=phase_info,
            nmolecules=args.nmolecules,
            n_candidates=10
        )
        print(f"Generated {len(gen_result.candidates)} candidates")
        
        # Warn if actual molecule count differs from requested
        if gen_result.was_rounded:
            print(f"Note: Actual molecule count ({gen_result.actual_nmolecules}) differs from "
                  f"requested ({gen_result.requested_nmolecules})")
            print(f"      This ensures valid crystal structure symmetry.")
            print()
        
        # Rank candidates by energy, density, diversity
        ranking_result = rank_candidates(
            candidates=gen_result.candidates
        )
        print(f"Ranked {len(ranking_result.ranked_candidates)} candidates")
        
        # Print ranking scores for top candidates
        print("\nRanking scores (lower combined = better):")
        print("-" * 70)
        print(f"{'Rank':<6}{'Energy':<12}{'Density':<12}{'Diversity':<12}{'Combined':<12}")
        print("-" * 70)
        for rc in ranking_result.ranked_candidates[:5]:
            print(f"{rc.rank:<6}{rc.energy_score:<12.4f}{rc.density_score:<12.4f}{rc.diversity_score:<12.4f}{rc.combined_score:<12.4f}")
        print("-" * 70)
        
        # Export GROMACS files if requested
        if args.gromacs:
            output_path = Path(args.output)
            output_path.mkdir(parents=True, exist_ok=True)
            
            for rc in ranking_result.ranked_candidates:
                candidate = rc.candidate
                gro_filename = f"{candidate.phase_id}_{rc.rank}.gro"
                gro_filepath = output_path / gro_filename
                write_gro_file(candidate, str(gro_filepath))
                
                # Write .top file only for first candidate
                if rc.rank == 1:
                    top_filepath = output_path / f"{candidate.phase_id}_1.top"
                    write_top_file(candidate, str(top_filepath))
                    print(f"Exported GROMACS files: {gro_filename}, {candidate.phase_id}_1.top")
            
            print(f"  GROMACS files written to: {args.output}")
        
        # Output PDB files and phase diagram
        output_result = output_ranked_candidates(
            ranking_result=ranking_result,
            output_dir=args.output,
            base_name="ice_candidate",
            generate_diagram=not args.no_diagram,
            user_t=args.temperature,
            user_p=args.pressure
        )
        
        print(f"\nOutput:")
        print(f"  PDB files: {len(output_result.output_files)}")
        print(f"  Directory: {args.output}")
        for f in output_result.output_files[:3]:
            print(f"    - {Path(f).name}")
        if len(output_result.output_files) > 3:
            print(f"    - ... and {len(output_result.output_files) - 3} more")
        
        if output_result.phase_diagram_files:
            print(f"  Phase diagram: {Path(output_result.phase_diagram_files[0]).parent / 'phase_diagram.png'}")
        
        print(f"\nValidation:")
        print(f"  Valid structures: {output_result.summary['n_validated']}/{output_result.summary['n_candidates']}")
        
        return 0
    except UnknownPhaseError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except SystemExit:
        # argparse calls sys.exit on error or --help
        # Re-raise to propagate the exit code
        raise
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
