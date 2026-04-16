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

# Map from our lattice type names to GenIce2 lattice modules
_LATTICE_MODULES = {
    "sI": "sI",
    "sII": "sII",
    "sH": "sH",
}

# Lazy-loaded GenIce2 modules (loaded in _ensure_genice_import)
_genice_lib = None
_gromacs_format = None
_lattice_modules_loaded = {}


class HydrateStructureGenerator:
    """Generator for hydrate structures using GenIce2.
    
    Supports sI, sII, sH hydrate lattices with configurable guest molecules
    (CH4, THF, CO2, H2) and cage occupancy.
    """
    
    def __init__(self):
        """Initialize the generator."""
        self._genice_lib = None
        self._gromacs_format = None
        self._lattice_modules = {}
    
    def _ensure_genice_import(self):
        """Lazy import of GenIce2 to avoid startup overhead."""
        global _genice_lib, _gromacs_format, _lattice_modules_loaded
        
        if self._genice_lib is None:
            try:
                import genice2.genice as genice_lib
                from genice2.formats import gromacs
                from genice2.lattices import sI, sII, sH
                from genice2.molecules.tip4p import Molecule as TIP4P
                
                self._genice_lib = genice_lib
                self._gromacs_format = gromacs
                self._lattice_modules = {
                    "sI": sI,
                    "sII": sII,
                    "sH": sH,
                }
                self._water_molecule = TIP4P()
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
        
        # Get GenIce2 lattice name from config
        lattice_name = config.get_genice_lattice_name()
        
        # Build GenIce2 CLI options based on config
        options = self._build_genice_options(config)
        
        # Generate structure using GenIce2 CLI via subprocess
        positions, cell, atom_names = self._run_via_cli(lattice_name, options)
        
        # Build molecule index
        molecule_index = self._build_molecule_index(atom_names, positions)
        
        # Get lattice info
        lattice_info = HydrateLatticeInfo.from_lattice_type(config.lattice_type)
        
        # Count water and guest molecules separately (guest = ch4, na, cl, etc.)
        water_count = sum(1 for m in molecule_index if m.mol_type == "water")
        guest_count = sum(1 for m in molecule_index if m.mol_type == "ch4")
        
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
            guest_param = "ch4"  # all-atom methane (C + 4 H), not "me" (united atom)
        elif guest == "thf":
            guest_param = "thf"
        else:
            guest_param = guest
        
        # Small cage occupancy (using GenIce2 CLI cage type codes)
        # GenIce2 CLI format: 12=me for small, 14=me for large
        small_occ = config.cage_occupancy_small / 100.0
        large_occ = config.cage_occupancy_large / 100.0
        
        # Build guest option for small cages (12 = 5^12 cages via CLI)
        if small_occ > 0:
            if small_occ < 1.0:
                # Partial occupancy
                options.append(f"--guest 12={guest_param}*{small_occ}")
            else:
                options.append(f"--guest 12={guest_param}")
        
        # Large cage occupancy (14 for sI = 5^12 6^4, 16 for sII/sH)
        if large_occ > 0:
            if large_occ < 1.0:
                if config.lattice_type == "sI":
                    large_cage = "14"
                elif config.lattice_type == "sII":
                    large_cage = "16"
                else:
                    large_cage = "16"
                options.append(f"--guest {large_cage}={guest_param}*{large_occ}")
            else:
                if config.lattice_type == "sI":
                    options.append("--guest 14=" + guest_param)
                elif config.lattice_type == "sII":
                    options.append("--guest 16=" + guest_param)
                else:
                    options.append("--guest 16=" + guest_param)
        
        # Water model - use TIP4P for better GROMACS compatibility
        options.append("--water tip4p")
        
        return options
    
    def _run_via_cli(self, lattice_name: str, options: list[str]) -> tuple:
        """Run GenIce2 via subprocess CLI.
        
        Args:
            lattice_name: GenIce2 lattice name (e.g., "CS1", "CS2", "DOH")
            options: GenIce2 CLI-style options (e.g., ["--guest 14=me", "--guest 12=me"])
        
        Returns:
            Tuple of (positions, cell, atom_names)
        """
        import subprocess
        import shlex
        
        try:
            # Build command using shell-style invocation for proper argument parsing
            cmd_args = [lattice_name] + options + ["--quiet"]
            cmd = "genice2 " + " ".join(cmd_args)
            
            # Run command and capture GRO output
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                check=True,
                timeout=60
            )
            
            # Parse GRO format result
            return self._parse_gro_result(result.stdout)
        
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"GenIce2 CLI failed: {e.stderr}"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                "GenIce2 CLI timed out"
            )
        except Exception as e:
            raise RuntimeError(
                f"GenIce2 failed to generate structure: {e}"
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
            if not line.strip() or len(line) < 44:
                continue
            
            # GRO format fixed-width columns
            # Columns 10-15: atom name
            # Columns 20-28, 28-36, 36-44: x, y, z in nm
            # Example: "    1SOL      O    1   1.065   0.370   0.004"
            #                    ^10  ^15
            
            # Extract atom name from columns 10-15 (correct for GRO format)
            atom_name = line[10:15].strip()
            if atom_name:
                atom_names.append(atom_name)
            
            # Extract positions (columns 20-28, 28-36, 36-44) - in nm
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
        
        Handles:
        - TIP4P water: OW, HW1, HW2, MW (4 atoms)
        - 3-site water: O, H, H (3 atoms) 
        - United-atom methane: Me (1 atom)
        - All-atom methane: C, H, H, H, H (5 atoms)
        - Ions: Na, Cl (1 atom each)
        """
        molecule_index = []
        i = 0
        
        while i < len(atom_names):
            atom = atom_names[i]
            
            # Check for guest molecules first (unique atom types)
            if atom == "Me":
                # United-atom methane (Me)
                molecule_index.append(MoleculeIndex(i, 1, "ch4"))
                i += 1
                continue
            
            # Check for all-atom methane (C followed by H atoms)
            if atom == "C" and i + 4 < len(atom_names):
                next_atoms = atom_names[i+1:i+5]
                if all(a == "H" for a in next_atoms):
                    molecule_index.append(MoleculeIndex(i, 5, "ch4"))
                    i += 5
                    continue
            
            # Check for water (TIP4P: OW, HW1, HW2, MW)
            if atom == "OW" and i + 3 < len(atom_names):
                next_atoms = atom_names[i:i+4]
                if next_atoms[1] == "HW1" and next_atoms[2] == "HW2" and next_atoms[3] == "MW":
                    molecule_index.append(MoleculeIndex(i, 4, "water"))
                    i += 4
                    continue
            
            # Check for 3-site water (O, H, H)
            if atom == "O" and i + 2 < len(atom_names):
                if atom_names[i+1] == "H" and atom_names[i+2] == "H":
                    molecule_index.append(MoleculeIndex(i, 3, "water"))
                    i += 3
                    continue
            
            # Check for ions
            if atom in ["NA", "Na"]:
                molecule_index.append(MoleculeIndex(i, 1, "na"))
                i += 1
                continue
            
            if atom in ["CL", "Cl"]:
                molecule_index.append(MoleculeIndex(i, 1, "cl"))
                i += 1
                continue
            
            # Unknown atom type - skip but count as water for now to continue scanning
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