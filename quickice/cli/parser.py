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
)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="quickice",
        description="QuickIce - Ice structure generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --temperature 300 --pressure 100 --nmolecules 100
  %(prog)s --temperature 250 --pressure 0.1 --nmolecules 256
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
        required=True,
        help="Number of water molecules (4-100000)"
    )
    
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version="%(prog)s 0.1.0"
    )
    
    return parser


def get_arguments(args: Optional[list] = None) -> argparse.Namespace:
    """Parse and return command-line arguments.
    
    Args:
        args: Optional list of arguments (for testing). If None, uses sys.argv.
        
    Returns:
        Namespace with validated arguments:
            - temperature: float (0-500K)
            - pressure: float (0-10000 MPa)
            - nmolecules: int (4-100000)
            
    Raises:
        SystemExit: If arguments are invalid or missing
    """
    parser = create_parser()
    return parser.parse_args(args)
