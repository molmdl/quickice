"""CLI argument parser for QuickIce.

This module defines the command-line interface using argparse with validators
for temperature, pressure, and molecule count.
"""

import argparse
import sys
from typing import Optional

from quickice.validation.validators import (
    validate_temperature,
    validate_pressure,
    validate_nmolecules,
    validate_positive_float,
    validate_box_dimension,
)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="python quickice.py",
        description="QuickIce - Ice structure generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python quickice.py --temperature 300 --pressure 100 --nmolecules 100
  python quickice.py --temperature 250 --pressure 0.1 --nmolecules 256
        """
    )
    
    parser.add_argument(
        "--temperature",
        "-T",
        type=validate_temperature,
        required=True,
        help="Temperature in Kelvin (0-500K)"
    )
    
    parser.add_argument(
        "--pressure",
        "-P",
        type=validate_pressure,
        required=True,
        help="Pressure in MPa (0-10000 MPa)"
    )
    
    parser.add_argument(
        "--nmolecules",
        "-N",
        type=validate_nmolecules,
        required=False,
        default=None,
        help="Number of water molecules (4-100000). Required for ice generation, optional for interface generation (default: 256)"
    )
    
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="output",
        help="Output directory for PDB files and phase diagram (default: output)"
    )
    
    parser.add_argument(
        "--no-diagram",
        action="store_true",
        default=False,
        help="Disable phase diagram generation"
    )
    
    parser.add_argument(
        "--gromacs",
        "-g",
        action="store_true",
        default=False,
        help="Export GROMACS format (.gro, .top files)"
    )

    parser.add_argument(
        "--candidate",
        "-c",
        type=int,
        default=None,
        help="Export specific candidate rank (1-10). Only used with --gromacs. Default: export all"
    )
    
    # Interface generation argument group
    interface_group = parser.add_argument_group(
        'interface generation',
        'Ice-water interface generation (requires --interface)'
    )
    
    interface_group.add_argument(
        "--interface",
        action="store_true",
        default=False,
        help="Generate ice-water interface structure"
    )
    
    interface_group.add_argument(
        "--mode", "-m",
        type=str,
        choices=["slab", "pocket", "piece"],
        default=None,
        help="Interface mode: slab, pocket, or piece (required with --interface)"
    )
    
    interface_group.add_argument(
        "--box-x", "-x",
        type=validate_box_dimension,
        default=None,
        help="Box X dimension in nm (required with --interface)"
    )
    
    interface_group.add_argument(
        "--box-y", "-y",
        type=validate_box_dimension,
        default=None,
        help="Box Y dimension in nm (required with --interface)"
    )
    
    interface_group.add_argument(
        "--box-z", "-z",
        type=validate_box_dimension,
        default=None,
        help="Box Z dimension in nm (required with --interface)"
    )
    
    interface_group.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    
    interface_group.add_argument(
        "--ice-thickness", "-t",
        type=validate_positive_float,
        default=None,
        help="Ice layer thickness in nm (required for slab mode)"
    )
    
    interface_group.add_argument(
        "--water-thickness", "-w",
        type=validate_positive_float,
        default=None,
        help="Water layer thickness in nm (required for slab mode)"
    )
    
    interface_group.add_argument(
        "--pocket-diameter", "-d",
        type=validate_positive_float,
        default=None,
        help="Pocket diameter in nm (required for pocket mode)"
    )
    
    interface_group.add_argument(
        "--pocket-shape",
        type=str,
        choices=["sphere", "cubic"],
        default="sphere",
        help="Pocket shape: sphere or cubic (default: sphere)"
    )
    
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version="%(prog)s 3.0.0"
    )
    
    return parser


def validate_interface_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Validate interface-specific arguments after parsing.
    
    Performs conditional validation for mode-specific parameters.
    Raises SystemExit via parser.error() if validation fails.
    
    Args:
        args: Parsed arguments from parser.parse_args()
        parser: ArgumentParser instance for error reporting
    """
    # --nmolecules is required for ice generation mode (not interface mode)
    if not args.interface and args.nmolecules is None:
        parser.error("--nmolecules is required for ice generation (omit for interface mode)")
    
    if not args.interface:
        return  # No validation needed if not using interface mode
    
    # --mode is required when --interface is set
    if args.mode is None:
        parser.error("--mode is required when using --interface")
    
    # Box dimensions are required when --interface is set
    if args.box_x is None:
        parser.error("--box-x is required when using --interface")
    if args.box_y is None:
        parser.error("--box-y is required when using --interface")
    if args.box_z is None:
        parser.error("--box-z is required when using --interface")
    
    # Mode-specific validation
    if args.mode == "slab":
        if args.ice_thickness is None:
            parser.error("--ice-thickness is required for slab mode")
        if args.water_thickness is None:
            parser.error("--water-thickness is required for slab mode")
    
    elif args.mode == "pocket":
        if args.pocket_diameter is None:
            parser.error("--pocket-diameter is required for pocket mode")
        # pocket_shape has default, no validation needed


def get_arguments(args: Optional[list] = None) -> argparse.Namespace:
    """Parse and return command-line arguments.
    
    Args:
        args: Optional list of arguments (for testing). If None, uses sys.argv.
        
    Returns:
        Namespace with validated arguments:
            - temperature: float (0-500K)
            - pressure: float (0-10000 MPa)
            - nmolecules: int (4-100000)
            - output: str (output directory path, default: "output")
            - no_diagram: bool (if True, skip diagram generation)
            - gromacs: bool (if True, export GROMACS format)
            - candidate: Optional[int] (candidate rank to export, only with --gromacs)
            - interface: bool (if True, generate ice-water interface)
            - mode: Optional[str] (interface mode: slab, pocket, or piece)
            - box_x, box_y, box_z: Optional[float] (box dimensions in nm)
            - seed: int (random seed, default: 42)
            - ice_thickness, water_thickness: Optional[float] (slab mode parameters)
            - pocket_diameter: Optional[float] (pocket mode parameter)
            - pocket_shape: str (pocket shape, default: "sphere")
            
    Raises:
        SystemExit: If arguments are invalid or missing
    """
    parser = create_parser()
    parsed = parser.parse_args(args)
    validate_interface_args(parsed, parser)
    return parsed
