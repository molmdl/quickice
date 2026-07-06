"""CLI argument parser for QuickIce.

This module defines the command-line interface using argparse with validators
for temperature, pressure, molecule count, and v4.5 pipeline flags (hydrate,
custom molecule, solute, ion insertion).
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
    validate_concentration_range,
    validate_occupancy_range,
)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="python -m quickice",
        description="QuickIce - Ice structure generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Ice generation:
    python -m quickice --temperature 300 --pressure 100 --nmolecules 100
    python -m quickice --temperature 250 --pressure 0.1 --nmolecules 256

   Hydrate generation:
     python -m quickice -T 270 -P 0.1 --hydrate --lattice-type sI --guest CH4
     python -m quickice -T 260 -P 10 --hydrate --lattice-type sII --guest THF --supercell-x 2
     python -m quickice -T 250 -P 50 --hydrate --lattice-type c0te --guest CH4

  Interface + custom molecule:
    python -m quickice -T 270 -P 0.1 --interface --mode slab --box-x 3 --box-y 3 --box-z 5 --ice-thickness 1.5 --water-thickness 2.0 --custom-gro mol.gro --custom-itp mol.itp --custom-placement random --custom-count 5

  Interface + solute + ions:
    python -m quickice -T 270 -P 0.1 --interface --mode slab --box-x 3 --box-y 3 --box-z 5 --ice-thickness 1.5 --water-thickness 2.0 --solute-type CH4 --solute-concentration 0.5 --ion-concentration 0.15 --ion-source solute
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
        help="Export GROMACS format (.gro, .top, .itp files)"
    )

    parser.add_argument(
        "--candidate",
        "-c",
        type=int,
        default=None,
        help="Export specific candidate rank (1-10). Only used with --gromacs. Default: export all"
    )

    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        default=False,
        help="Do not overwrite existing output files"
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

    # Hydrate generation argument group
    hydrate_group = parser.add_argument_group(
        'hydrate generation',
        'Clathrate hydrate generation (requires --hydrate)'
    )

    hydrate_group.add_argument(
        "--hydrate",
        action="store_true",
        default=False,
        help="Generate clathrate hydrate structure"
    )

    hydrate_group.add_argument(
        "--lattice-type",
        type=str,
        choices=["sI", "sII", "sH", "c0te", "c1te", "c2te", "ice1hte", "sTprime", "16", "17"],
        default="sI",
        help="Hydrate lattice type (default: sI)"
    )

    hydrate_group.add_argument(
        "--guest",
        type=str,
        choices=["CH4", "THF"],
        default="CH4",
        help="Guest molecule type (default: CH4). Ignored for water-only lattices "
             "(sTprime, 17). (deprecated; use --cage-guest for mixed occupancy)"
    )

    hydrate_group.add_argument(
        "--supercell-x",
        type=int,
        default=1,
        help="Supercell repetition in X direction (default: 1)"
    )

    hydrate_group.add_argument(
        "--supercell-y",
        type=int,
        default=1,
        help="Supercell repetition in Y direction (default: 1)"
    )

    hydrate_group.add_argument(
        "--supercell-z",
        type=int,
        default=1,
        help="Supercell repetition in Z direction (default: 1)"
    )

    hydrate_group.add_argument(
        "--cage-occupancy-small",
        type=validate_occupancy_range,
        default=100.0,
        help="Small cage occupancy percentage (default: 100.0). "
             "(deprecated; use --cage-guest for mixed occupancy)"
    )

    hydrate_group.add_argument(
        "--cage-occupancy-large",
        type=validate_occupancy_range,
        default=100.0,
        help="Large cage occupancy percentage (default: 100.0). "
             "(deprecated; use --cage-guest for mixed occupancy)"
    )

    hydrate_group.add_argument(
        "--cage-guest",
        action="append",
        default=None,
        metavar="KEY=GUEST:OCC",
        help=("Per-cage-type guest assignment (repeatable). Format: "
              "--cage-guest small=CH4:60 --cage-guest large=THF:100. "
              "KEY is a cage_type_map key (small/medium/large/guest). "
              "GUEST is CH4 or THF (built-in only on CLI for v4.7). "
              "OCC is 0-100 occupancy percentage. "
              "When supplied, overrides --guest/--cage-occupancy-small/large."),
    )

    # Custom molecule insertion argument group
    custom_group = parser.add_argument_group(
        'custom molecule insertion',
        'Custom molecule insertion into liquid region (requires --interface)'
    )

    custom_group.add_argument(
        "--custom-gro",
        type=str,
        default=None,
        help="Path to custom molecule GRO file"
    )

    custom_group.add_argument(
        "--custom-itp",
        type=str,
        default=None,
        help="Path to custom molecule ITP file"
    )

    custom_group.add_argument(
        "--custom-placement",
        type=str,
        choices=["random", "custom"],
        default="random",
        help="Placement mode: random or custom positions (default: random)"
    )

    custom_group.add_argument(
        "--custom-count",
        type=int,
        default=None,
        help="Number of custom molecules to insert (for random placement)"
    )

    custom_group.add_argument(
        "--custom-concentration",
        type=validate_concentration_range,
        default=None,
        help="Custom molecule concentration in mol/L (for random placement)"
    )

    custom_group.add_argument(
        "--custom-positions-file",
        type=str,
        default=None,
        help="Path to CSV file with custom positions (for custom placement)"
    )

    # Solute insertion argument group
    solute_group = parser.add_argument_group(
        'solute insertion',
        'Solute molecule insertion into liquid region (requires --interface)'
    )

    solute_group.add_argument(
        "--solute-type",
        type=str,
        choices=["CH4", "THF"],
        default=None,
        help="Solute molecule type"
    )

    solute_group.add_argument(
        "--solute-concentration",
        type=validate_concentration_range,
        default=None,
        help="Solute concentration in mol/L"
    )

    solute_group.add_argument(
        "--solute-source",
        type=str,
        choices=["interface", "custom"],
        default="interface",
        help="Source for solute insertion: interface (liquid water) or custom molecule coordinates (default: interface)"
    )

    # Ion insertion argument group
    ion_group = parser.add_argument_group(
        'ion insertion',
        'Ion insertion for charge screening (requires --interface)'
    )

    ion_group.add_argument(
        "--ion-concentration",
        type=validate_concentration_range,
        default=None,
        help="Ion concentration in mol/L"
    )

    ion_group.add_argument(
        "--ion-source",
        type=str,
        choices=["interface", "custom", "solute"],
        default="interface",
        help="Source for ion insertion: interface (liquid water), custom molecule coordinates, or solute coordinates (default: interface)"
    )

    
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version="%(prog)s 4.5.0"
    )
    
    # Mode selection flags (consumed by entry router before argparse runs;
    # added here for --help discoverability only)
    parser.add_argument(
        "--cli",
        action="store_true",
        default=False,
        help="Force CLI mode; skip PySide6 import entirely (useful in headless/CI environments)"
    )
    
    parser.add_argument(
        "--gui",
        action="store_true",
        default=False,
        help="Force GUI mode; requires PySide6 and a display"
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
    # --nmolecules is required for ice generation mode (not interface or hydrate mode)
    if not args.interface and not getattr(args, 'hydrate', False) and args.nmolecules is None:
        parser.error("--nmolecules is required for ice generation (omit for interface or hydrate mode)")
    
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


def validate_pipeline_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Validate v4.5 pipeline arguments after parsing.
    
    Performs cross-flag validation for hydrate, custom molecule, solute,
    and ion insertion flags. Raises SystemExit via parser.error() if
    validation fails (exit code 2).
    
    Args:
        args: Parsed arguments from parser.parse_args()
        parser: ArgumentParser instance for error reporting
    """
    # Keep existing interface validation
    validate_interface_args(args, parser)
    
    # --hydrate + --nmolecules is invalid (hydrate uses supercell, not molecule count)
    if args.hydrate and args.nmolecules is not None:
        parser.error("--hydrate and --nmolecules are mutually exclusive (hydrate uses --supercell-x/y/z)")
    
    # --custom-gro requires --custom-itp and vice versa
    if args.custom_gro is not None and args.custom_itp is None:
        parser.error("--custom-gro requires --custom-itp")
    if args.custom_itp is not None and args.custom_gro is None:
        parser.error("--custom-itp requires --custom-gro")
    
    # --custom-gro requires --interface
    if args.custom_gro is not None and not args.interface:
        parser.error("--custom-gro requires --interface")
    
    # --custom-placement custom requires --custom-positions-file
    if args.custom_placement == "custom" and args.custom_positions_file is None:
        parser.error("--custom-placement custom requires --custom-positions-file")
    
    # --custom-placement random requires --custom-count or --custom-concentration (not both)
    if args.custom_placement == "random" and args.custom_gro is not None:
        if args.custom_count is None and args.custom_concentration is None:
            parser.error("--custom-placement random requires --custom-count or --custom-concentration")
        if args.custom_count is not None and args.custom_concentration is not None:
            parser.error("--custom-count and --custom-concentration are mutually exclusive")
    
    # --solute-type requires --solute-concentration
    if args.solute_type is not None and args.solute_concentration is None:
        parser.error("--solute-type requires --solute-concentration")
    
    # --solute-type requires --interface
    if args.solute_type is not None and not args.interface:
        parser.error("--solute-type requires --interface")
    
    # --solute-source custom requires --custom-gro
    if args.solute_source == "custom" and args.custom_gro is None:
        parser.error("--solute-source custom requires --custom-gro")
    
    # --ion-concentration requires --interface
    if args.ion_concentration is not None and not args.interface:
        parser.error("--ion-concentration requires --interface")
    
    # --ion-source custom requires --custom-gro
    if args.ion_source == "custom" and args.custom_gro is None:
        parser.error("--ion-source custom requires --custom-gro")
    
    # --ion-source solute requires --solute-type
    if args.ion_source == "solute" and args.solute_type is None:
        parser.error("--ion-source solute requires --solute-type")


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
            - no_overwrite: bool (if True, do not overwrite existing files)
            - interface: bool (if True, generate ice-water interface)
            - mode: Optional[str] (interface mode: slab, pocket, or piece)
            - box_x, box_y, box_z: Optional[float] (box dimensions in nm)
            - seed: int (random seed, default: 42)
            - ice_thickness, water_thickness: Optional[float] (slab mode parameters)
            - pocket_diameter: Optional[float] (pocket mode parameter)
            - pocket_shape: str (pocket shape, default: "sphere")
            - hydrate: bool (if True, generate clathrate hydrate)
            - lattice_type: str (hydrate lattice: sI, sII, sH, c0te, c1te, c2te, ice1hte, sTprime, 16, 17; default: sI)
            - guest: str (guest molecule: CH4, THF; default: CH4)
            - supercell_x, supercell_y, supercell_z: int (supercell repeats; default: 1)
            - cage_occupancy_small: float (small cage occupancy %; default: 100.0)
            - cage_occupancy_large: float (large cage occupancy %; default: 100.0)
            - custom_gro: Optional[str] (path to custom molecule GRO file)
            - custom_itp: Optional[str] (path to custom molecule ITP file)
            - custom_placement: str (placement mode: random, custom; default: random)
            - custom_count: Optional[int] (number of molecules for random placement)
            - custom_concentration: Optional[float] (concentration mol/L for random placement)
            - custom_positions_file: Optional[str] (CSV file for custom placement)
            - solute_type: Optional[str] (solute molecule: CH4, THF)
            - solute_concentration: Optional[float] (solute concentration in mol/L)
            - solute_source: str (solute source: interface, custom; default: interface)
            - ion_concentration: Optional[float] (ion concentration in mol/L)
            - ion_source: str (ion source: interface, custom, solute; default: interface)
            
    Raises:
        SystemExit: If arguments are invalid or missing (exit code 2)
    """
    parser = create_parser()
    parsed = parser.parse_args(args)
    validate_pipeline_args(parsed, parser)
    return parsed
