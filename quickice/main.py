"""Main entry point for QuickIce CLI."""

import sys
import shutil
from pathlib import Path

from quickice.cli.parser import get_arguments
from quickice.phase_mapping import lookup_phase, UnknownPhaseError
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import InterfaceConfig
from quickice.structure_generation.interface_builder import (
    generate_interface,
    InterfaceGenerationError,
)
from quickice.ranking import rank_candidates
from quickice.output import output_ranked_candidates
from quickice.output.gromacs_writer import (
    write_gro_file,
    write_top_file,
    write_interface_gro_file,
    write_interface_top_file,
    get_tip4p_itp_path,
)


def check_output_file(filepath: Path) -> bool:
    """Check if file exists and prompt for overwrite.
    
    Args:
        filepath: Path to check
        
    Returns:
        True if file doesn't exist or user confirms overwrite, False otherwise
    """
    if filepath.exists():
        response = input(f"File {filepath.name} exists. Overwrite? [y/N] ")
        return response.lower() == 'y'
    return True


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
        density = phase_info['density']
        if isinstance(density, float):
            print(f"Density: {density:.4f} g/cm³")
        else:
            print(f"Density: {density} g/cm³")
        print()
        
        # Interface generation workflow (new)
        if args.interface:
            # Create InterfaceConfig from CLI arguments
            config = InterfaceConfig(
                mode=args.mode,
                box_x=args.box_x,
                box_y=args.box_y,
                box_z=args.box_z,
                seed=args.seed,
                ice_thickness=args.ice_thickness or 0.0,
                water_thickness=args.water_thickness or 0.0,
                pocket_diameter=args.pocket_diameter or 0.0,
                pocket_shape=args.pocket_shape,
            )
            
            # Print interface parameters (matching GUI log panel style)
            print(f"\nStarting {config.mode} interface generation...")
            print(f"  Box: {config.box_x:.2f} x {config.box_y:.2f} x {config.box_z:.2f} nm")
            print(f"  Seed: {config.seed}")
            
            if config.mode == "slab":
                print(f"  Ice thickness: {config.ice_thickness:.2f} nm")
                print(f"  Water thickness: {config.water_thickness:.2f} nm")
            elif config.mode == "pocket":
                print(f"  Pocket diameter: {config.pocket_diameter:.2f} nm")
                print(f"  Pocket shape: {config.pocket_shape}")
            print()
            
            # Generate ice candidate
            print(f"Generating ice candidate ({phase_info['phase_id']})...")
            gen_result = generate_candidates(
                phase_info=phase_info,
                nmolecules=256,  # Default for interface generation
                n_candidates=1
            )
            candidate = gen_result.candidates[0]
            print(f"  Generated {candidate.nmolecules} molecules")
            print()
            
            # Generate interface
            print("Assembling interface...")
            result = generate_interface(candidate, config)
            print(f"  Ice molecules: {result.ice_nmolecules}")
            print(f"  Water molecules: {result.water_nmolecules}")
            
            # Print generation report (matching GUI log panel)
            if result.report:
                print("\n" + "=" * 50)
                print(result.report)
                print("=" * 50)
            
            print("\nInterface generation complete.")
            print()
            
            # Export GROMACS files
            output_path = Path(args.output)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate output filename: interface_{phase}_{mode}.gro
            base_name = f"interface_{phase_info['phase_id']}_{config.mode}"
            gro_filepath = output_path / f"{base_name}.gro"
            top_filepath = output_path / f"{base_name}.top"
            itp_filepath = output_path / "tip4p_ice.itp"
            
            # Check for file overwrite
            files_to_check = [gro_filepath, top_filepath, itp_filepath]
            skip_export = False
            for f in files_to_check:
                if not check_output_file(f):
                    print(f"Skipping export: {f.name} already exists")
                    skip_export = True
                    break
            
            if not skip_export:
                # Write GROMACS files
                write_interface_gro_file(result, str(gro_filepath))
                write_interface_top_file(result, str(top_filepath))
                
                # Copy tip4p_ice.itp
                itp_source = get_tip4p_itp_path()
                shutil.copy(itp_source, itp_filepath)
                
                print(f"Exported GROMACS files:")
                print(f"  - {gro_filepath.name}")
                print(f"  - {top_filepath.name}")
                print(f"  - {itp_filepath.name}")
                print(f"  Directory: {args.output}")
            
            return 0
        
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
            
            # Filter candidates if --candidate specified
            candidates_to_export = ranking_result.ranked_candidates
            specific_candidate = args.candidate is not None
            if specific_candidate:
                candidates_to_export = [
                    rc for rc in ranking_result.ranked_candidates 
                    if rc.rank == args.candidate
                ]
                if not candidates_to_export:
                    print(f"Warning: Candidate rank {args.candidate} not found. "
                          f"Available: 1-{len(ranking_result.ranked_candidates)}")
            
            exported_files = []
            
            # Write .gro files for all exported candidates
            for rc in candidates_to_export:
                candidate = rc.candidate
                base_name = f"{candidate.phase_id}_{rc.rank}"
                gro_filepath = output_path / f"{base_name}.gro"
                write_gro_file(candidate, str(gro_filepath))
                exported_files.append(f"{base_name}.gro")
            
            # Write .top and .itp only once (they're identical for all candidates)
            # Use the first candidate for phase_id reference
            if candidates_to_export:
                first_candidate = candidates_to_export[0].candidate
                phase_id = first_candidate.phase_id
                
                # Write single .top file
                top_filename = f"{phase_id}.top"
                top_filepath = output_path / top_filename
                write_top_file(first_candidate, str(top_filepath))
                
                # Copy .itp file from data directory (single copy)
                itp_source = get_tip4p_itp_path()
                itp_filename = "tip4p_ice.itp"
                itp_filepath = output_path / itp_filename
                shutil.copy(itp_source, itp_filepath)
                
                # Add to exported list after .gro files
                exported_files.append(top_filename)
                exported_files.append(itp_filename)
            
            print(f"\nExported GROMACS files:")
            for f in exported_files[:6]:
                print(f"  - {f}")
            if len(exported_files) > 6:
                print(f"  - ... and {len(exported_files) - 6} more")
            print(f"  Directory: {args.output}")
        
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
    except InterfaceGenerationError as e:
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
