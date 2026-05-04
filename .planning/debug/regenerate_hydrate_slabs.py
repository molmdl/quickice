#!/usr/bin/env python3
"""Regenerate hydrate slab structures with the ice boundary fix.

This script regenerates CH4 and THF hydrate slab structures to verify
that the filter_molecules=False fix eliminates gaps at periodic boundaries.
"""

import numpy as np
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from quickice.structure_generation.types import Candidate, InterfaceConfig
from quickice.structure_generation.modes.slab import assemble_slab
from quickice.output.gromacs_writer import write_interface_gro_file


def load_hydrate_candidate(gro_path: Path) -> Candidate:
    """Load a hydrate candidate from a GRO file.
    
    Args:
        gro_path: Path to hydrate GRO file
        
    Returns:
        Candidate with hydrate metadata
    """
    from quickice.structure_generation.gro_parser import parse_gro_file
    
    positions, atom_names, cell = parse_gro_file(gro_path)
    
    # Count molecules (TIP4P = 4 atoms per water molecule)
    # For hydrates, count water molecules only (not guests)
    n_water = sum(1 for name in atom_names if name == "OW")
    
    # Detect guest type
    has_ch4 = "C" in atom_names
    has_thf = "O" in atom_names and "C" in atom_names  # THF has both O and C
    
    # Determine phase ID
    if has_ch4 and not has_thf:
        phase_id = "sI_hydrate_ch4"
    elif has_thf:
        phase_id = "sII_hydrate_thf"
    else:
        phase_id = "unknown_hydrate"
    
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=n_water,
        phase_id=phase_id,
        seed=42,
        metadata={
            "temperature": 273.15,
            "pressure": 0.101325,
            "original_hydrate": True
        }
    )


def regenerate_hydrate_slab(hydrate_gro: Path, output_dir: Path, box_config: dict):
    """Regenerate hydrate slab interface with current code.
    
    Args:
        hydrate_gro: Path to hydrate candidate GRO file
        output_dir: Output directory for generated files
        box_config: Dict with box_x, box_y, box_z, ice_thickness, water_thickness
    """
    print(f"\nRegenerating slab from: {hydrate_gro.name}")
    
    # Load hydrate candidate
    candidate = load_hydrate_candidate(hydrate_gro)
    print(f"  Loaded candidate: {candidate.phase_id}")
    print(f"  Water molecules: {candidate.nmolecules}")
    
    # Configure slab mode
    config = InterfaceConfig(
        mode="slab",
        seed=42,
        **box_config
    )
    
    print(f"  Box: {config.box_x:.3f} x {config.box_y:.3f} x {config.box_z:.3f} nm")
    print(f"  Ice thickness: {config.ice_thickness:.3f} nm")
    print(f"  Water thickness: {config.water_thickness:.3f} nm")
    
    # Generate slab interface
    iface = assemble_slab(candidate, config)
    
    print(f"  Generated interface:")
    print(f"    Ice molecules: {iface.ice_nmolecules}")
    print(f"    Guest molecules: {iface.guest_nmolecules}")
    print(f"    Water molecules: {iface.water_nmolecules}")
    
    # Write output files
    output_dir.mkdir(parents=True, exist_ok=True)
    
    gro_path = output_dir / "interface_slab.gro"
    write_interface_gro_file(iface, gro_path)
    print(f"  Written: {gro_path}")
    
    return gro_path


def main():
    """Regenerate CH4 and THF hydrate slab structures."""
    print("=" * 70)
    print("Regenerating hydrate slab structures with ice boundary fix")
    print("=" * 70)
    
    # Configuration for CH4 hydrate (sI)
    ch4_config = {
        "box_x": 3.6,
        "box_y": 3.6,
        "box_z": 10.928,
        "ice_thickness": 3.0,
        "water_thickness": 4.928
    }
    
    # Configuration for THF hydrate (sII)
    thf_config = {
        "box_x": 3.3,
        "box_y": 3.3,
        "box_z": 10.574,
        "ice_thickness": 3.0,
        "water_thickness": 4.574
    }
    
    # Regenerate CH4 hydrate slab
    ch4_hydrate = Path("tmp/ch4/hydrate_sI_ch4_1x1x1.gro")
    ch4_output = Path("tmp/ch4/slab")
    
    if ch4_hydrate.exists():
        regenerate_hydrate_slab(ch4_hydrate, ch4_output, ch4_config)
    else:
        print(f"\nSKIPPING: CH4 hydrate candidate not found: {ch4_hydrate}")
    
    # Regenerate THF hydrate slab
    thf_hydrate = Path("tmp/thf/hydrate_sII_thf_1x1x1.gro")
    thf_output = Path("tmp/thf/slab")
    
    if thf_hydrate.exists():
        regenerate_hydrate_slab(thf_hydrate, thf_output, thf_config)
    else:
        print(f"\nSKIPPING: THF hydrate candidate not found: {thf_hydrate}")
    
    print("\n" + "=" * 70)
    print("Regeneration complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
