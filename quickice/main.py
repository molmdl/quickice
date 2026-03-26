"""Main entry point for QuickIce CLI."""

import sys

from quickice.cli.parser import get_arguments
from quickice.phase_mapping.lookup import lookup_phase
from quickice.phase_mapping.errors import UnknownPhaseError


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
