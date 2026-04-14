"""Hydrate structure generation via GenIce2.

Provides HydrateStructureGenerator class for creating hydrate structures
with configurable lattice type, guest molecules, and cage occupancy.
"""

import numpy as np
from pathlib import Path

from quickice.structure_generation.types import (
    HydrateConfig,
    HydrateStructure,
    HydrateLatticeInfo,
    MoleculeIndex,
    MOLECULE_TYPE_INFO,
    HYDRATE_LATTICES,
    GUEST_MOLECULES,
)


class HydrateStructureGenerator:
    """Generator for hydrate structures using GenIce2.
    
    Supports sI, sII, sH hydrate lattices with configurable guest molecules
    (CH4, THF, CO2, H2) and cage occupancy.
    """
    
    def __init__(self):
        """Initialize the generator."""
        self._genice_module = None
    
    def _ensure_genice_import(self):
        """Lazy import of GenIce2 to avoid startup overhead."""
        if self._genice_module is None:
            try:
                import genice2
                self._genice_module = genice2
            except ImportError as e:
                raise ImportError(
                    "GenIce2 is required for hydrate generation. "
                    f"Import error: {e}"
                )
    
    def generate(self, config: HydrateConfig) -> HydrateStructure:
        """Generate hydrate structure with given configuration.
        
        Args:
            config: HydrateConfig with lattice, guest, occupancy, supercell
            
        Returns:
            HydrateStructure with positions, cell, and molecule_index
            
        Raises:
            ImportError: If GenIce2 is not available
            ValueError: If configuration is invalid
        """
        self._ensure_genice_import()
        
        # Get GenIce2 lattice name
        lattice_name = config.get_genice_lattice_name()
        
        # Build GenIce2 command options
        options = self._build_genice_options(config)
        
        # Generate structure using GenIce2
        positions, cell, atom_names = self._run_genice(lattice_name, options)
        
        # Build molecule index
        molecule_index = self._build_molecule_index(atom_names, positions)
        
        # Get lattice info
        lattice_info = HydrateLatticeInfo.from_lattice_type(config.lattice_type)
        
        # Count water and guest molecules
        water_count = sum(1 for m in molecule_index if m.mol_type == "water")
        guest_count = sum(1 for m in molecule_index if m.mol_type != "water")
        
        report = self._generate_report(config, water_count, guest_count)
        
        return HydrateStructure(
            positions=positions,
            atom_names=atom_names,
            cell=cell,
            molecule_index=molecule_index,
            config=config,
            lattice_info=lattice_info,
            report=report,
            guest_count=guest_count,
            water_count=water_count,
        )
    
    def _build_genice_options(self, config: HydrateConfig) -> list[str]:
        """Build GenIce2 command options from config."""
        options = []
        
        # Guest molecule option
        guest = config.guest_type
        if guest == "ch4":
            guest_param = "me"  # methane
        elif guest == "thf":
            guest_param = "thf"
        elif guest == "co2":
            guest_param = "co2"
        elif guest == "h2":
            guest_param = "h2"
        else:
            guest_param = guest
        
        # Small cage occupancy (using 5^12 cage type code)
        # GenIce2 format: guest_type*occupancy
        small_occ = config.cage_occupancy_small / 100.0
        large_occ = config.cage_occupancy_large / 100.0
        
        # Build guest option for small cages (type 12 = 5^12)
        if small_occ > 0:
            if small_occ < 1.0:
                # Partial occupancy: put remaining guests in large cages
                options.append(f"--guest 12={guest_param}*{small_occ}")
            else:
                options.append(f"--guest 12={guest_param}")
        
        # Large cage occupancy (type 14 for sI/sII = 5^12 6^4, type 16 for some)
        if large_occ > 0:
            if large_occ < 1.0:
                # Determine cage type for large cages based on lattice
                if config.lattice_type == "sI":
                    large_cage = "14"  # 5^12 6^4
                elif config.lattice_type == "sII":
                    large_cage = "16"  # 5^12 6^4
                else:  # sH
                    large_cage = "16"
                options.append(f"--guest {large_cage}={guest_param}*{large_occ}")
            else:
                # Full occupancy
                if config.lattice_type == "sI":
                    options.append("--guest 14=" + guest_param)
                elif config.lattice_type == "sII":
                    options.append("--guest 16=" + guest_param)
                else:  # sH
                    options.append("--guest 16=" + guest_param)
        
        # Water model - use TIP4P for better GROMACS compatibility
        options.append("--water tip4p")
        
        return options
    
    def _run_genice(self, lattice_name: str, options: list[str]) -> tuple:
        """Run GenIce2 to generate structure.
        
        Returns:
            Tuple of (positions, cell, atom_names)
        """
        genice = self._genice_module.GenIce
        
        try:
            # Create GenIce instance
            ice = genice(lattice_name)
            
            # Generate using options (GenIce2 uses format() method)
            result = ice.format(format_name="gromacs", options=options)
            
            # Parse GRO format result
            return self._parse_gro_result(result)
            
        except Exception as e:
            raise RuntimeError(
                f"GenIce2 failed to generate {lattice_name}: {e}"
            )
    
    def _parse_gro_result(self, gro_string: str) -> tuple:
        """Parse GRO format string from GenIce2."""
        lines = gro_string.strip().split('\n')
        
        # Skip title and atom count lines
        # GRO format: title, atom_count, atom_lines, box
        
        try:
            n_atoms = int(lines[1].strip())
        except (IndexError, ValueError):
            raise RuntimeError("Invalid GRO format from GenIce2")
        
        # Parse atom lines (lines 2 to n_atoms+1)
        positions = []
        atom_names = []
        
        for i in range(2, min(2 + n_atoms, len(lines))):
            line = lines[i]
            # GRO format: resnum resname atomname atomnum x y z
            # Fixed format: positions at columns 20-68
            
            # Extract atom name (columns 10-15, but variable)
            parts = line.split()
            if len(parts) >= 5:
                atom_names.append(parts[2])
            
            # Extract positions (columns 20-44, 44-52, 52-60) - in nm
            try:
                x = float(line[20:28])
                y = float(line[28:36])
                z = float(line[36:44])
                positions.append([x, y, z])
            except (IndexError, ValueError):
                # Try alternative parsing
                pass
        
        positions = np.array(positions, dtype=np.float64)
        
        # Parse box vectors from last non-empty line
        box_line = None
        for line in lines[-5:]:
            if line.strip() and not line[0].isdigit():
                continue
            if line.strip():
                box_line = line
                break
        
        if box_line is None:
            box_line = lines[-1]
        
        cell = self._parse_box_line(box_line)
        
        return positions, cell, atom_names
    
    def _parse_box_line(self, line: str) -> np.ndarray:
        """Parse box vector line from GRO file."""
        values = line.split()
        if len(values) >= 9:
            # Triclinic: v1(x) v2(y) v3(z) v1(y) v1(z) v2(x) v2(z) v3(x) v3(y)
            v1x = float(values[0])
            v2y = float(values[1])
            v3z = float(values[2])
            v1y = float(values[3]) if len(values) > 3 else 0.0
            v1z = float(values[4]) if len(values) > 4 else 0.0
            v2x = float(values[5]) if len(values) > 5 else 0.0
            v2z = float(values[6]) if len(values) > 6 else 0.0
            v3x = float(values[7]) if len(values) > 7 else 0.0
            v3y = float(values[8]) if len(values) > 8 else 0.0
            
            cell = np.array([
                [v1x, v1y, v1z],
                [v2x, v2y, v2z],
                [v3x, v3y, v3z],
            ], dtype=np.float64)
        elif len(values) >= 3:
            # Orthorhombic: just v1(x), v2(y), v3(z)
            cell = np.diag([float(v) for v in values[:3]])
        else:
            cell = np.eye(3) * 10.0  # Default 10nm box
        
        return cell
    
    def _build_molecule_index(self, atom_names: list[str], positions: np.ndarray) -> list[MoleculeIndex]:
        """Build molecule index from atom names.
        
        Groups atoms by molecule type based on atom naming patterns.
        """
        molecule_index = []
        i = 0
        
        while i < len(atom_names):
            atom = atom_names[i]
            
            # Determine molecule type based on atom patterns
            # TIP4P water: OW, HW1, HW2, MW
            # Methane: C, H, H, H, H
            # CO2: C, O, O
            # H2: H, H
            
            if atom == "OW" or atom == "O":
                # Could be water or ice - check pattern
                if i + 3 < len(atom_names):
                    next_atoms = atom_names[i:i+4]
                    if "HW" in next_atoms[1] or "H" in next_atoms[1]:
                        # It's water (4 atoms: OW, HW1, HW2, MW) or ice (3 atoms: O, H, H)
                        if "MW" in next_atoms:
                            molecule_index.append(MoleculeIndex(i, 4, "water"))
                            i += 4
                        else:
                            molecule_index.append(MoleculeIndex(i, 3, "ice"))
                            i += 3
                        continue
                
                # Single O - default to water (might be guest)
                molecule_index.append(MoleculeIndex(i, 1, "water"))
                i += 1
            
            elif atom == "C":
                # Carbon - could be CH4 or CO2
                # Check surrounding atoms
                if i + 2 < len(atom_names):
                    next2 = atom_names[i+1:i+3]
                    o_count = sum(1 for a in next2 if a == "O")
                    h_count = sum(1 for a in next2 if a == "H")
                    
                    if o_count == 2:
                        # CO2: C, O, O
                        molecule_index.append(MoleculeIndex(i, 3, "co2"))
                        i += 3
                        continue
                    elif h_count >= 4:
                        # CH4: C + 4H
                        molecule_index.append(MoleculeIndex(i, 5, "ch4"))
                        i += 5
                        continue
                
                # Fallback
                molecule_index.append(MoleculeIndex(i, 1, "water"))
                i += 1
            
            elif atom == "H":
                # Hydrogen - check if it's H2 (2 H atoms)
                if i + 1 < len(atom_names) and atom_names[i+1] == "H":
                    molecule_index.append(MoleculeIndex(i, 2, "h2"))
                    i += 2
                else:
                    # Orphan H - skip (will be part of another molecule)
                    i += 1
            
            elif atom in ["NA", "Na"]:
                molecule_index.append(MoleculeIndex(i, 1, "na"))
                i += 1
            
            elif atom in ["CL", "Cl"]:
                molecule_index.append(MoleculeIndex(i, 1, "cl"))
                i += 1
            
            elif atom == "MW":
                # Virtual site - skip (part of water)
                i += 1
            
            else:
                # Unknown atom type - assume water (single atom for safety)
                molecule_index.append(MoleculeIndex(i, 1, "water"))
                i += 1
        
        return molecule_index
    
    def _generate_report(self, config: HydrateConfig, water_count: int, guest_count: int) -> str:
        """Generate human-readable report."""
        lines = [
            f"Generated {config.lattice_type} hydrate structure",
            f"  Lattice: {config.lattice_type} ({config.get_genice_lattice_name()})",
            f"  Guest: {GUEST_MOLECULES[config.guest_type]['name']}",
            f"  Small cage occupancy: {config.cage_occupancy_small}%",
            f"  Large cage occupancy: {config.cage_occupancy_large}%",
            f"  Supercell: {config.supercell_x} × {config.supercell_y} × {config.supercell_z}",
            f"  Water molecules: {water_count}",
            f"  Guest molecules: {guest_count}",
        ]
        return "\n".join(lines)