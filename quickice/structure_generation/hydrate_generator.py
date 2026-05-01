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
        
        # Generate structure using GenIce2 Python API (not CLI)
        positions, cell, atom_names, residue_names, residue_seq_nums = self._run_via_api(lattice_name, config)
        
        # Build molecule index (positions from genice2 are already complete molecules)
        # NOTE: Do NOT wrap positions. GenIce2 outputs complete molecules, and wrapping
        # by cell index causes molecules to be split when atoms span multiple periodic
        # images. VTK's vtkMoleculeMapper handles positions outside [0,L) correctly
        # using the lattice setting. This matches genice2 CLI behavior.
        molecule_index = self._build_molecule_index(atom_names, positions, residue_names, residue_seq_nums)
        
        # Get lattice info
        lattice_info = HydrateLatticeInfo.from_lattice_type(config.lattice_type)
        
        # Count water and guest molecules separately
        # Guest = any molecule that is not water (ch4, thf, na, cl, etc.)
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
    
    def _run_via_api(self, lattice_name: str, config: HydrateConfig) -> tuple:
        """Run GenIce2 via Python API.
        
        Uses GenIce2 Python API directly instead of CLI subprocess,
        which ensures compatibility with PyInstaller bundled executables.
        
        Args:
            lattice_name: GenIce2 lattice name (e.g., "CS1", "CS2", "DOH")
            config: HydrateConfig with lattice, guest, occupancy, supercell
            
        Returns:
            Tuple of (positions, cell, atom_names, residue_names, residue_seq_nums)
        """
        from genice2.genice import GenIce
        from genice2.plugin import safe_import
        from genice2.valueparser import parse_guest
        from collections import defaultdict
        
        try:
            # Load lattice module
            lattice = safe_import('lattice', lattice_name).Lattice()
            
            # Build supercell matrix
            supercell_matrix = np.diag([
                config.supercell_x,
                config.supercell_y,
                config.supercell_z
            ])
            
            # Create GenIce instance with supercell
            ice = GenIce(lattice, reshape=supercell_matrix)
            
            # Load TIP4P water model (4-point: OW, HW1, HW2, MW)
            water = safe_import('molecule', 'tip4p').Molecule()
            
            # Load GROMACS formatter
            formatter = safe_import('format', 'gromacs').Format()
            
            # Build guests dictionary from config
            # Format: {"12": {"ch4": 0.5}, "14": {"ch4": 1.0}}
            guests = defaultdict(dict)
            
            guest_type = config.guest_type
            small_occ = config.cage_occupancy_small / 100.0
            large_occ = config.cage_occupancy_large / 100.0
            
            # Map guest type to GenIce2 molecule name
            if guest_type == "ch4":
                guest_name = "ch4"  # all-atom methane
            elif guest_type == "thf":
                guest_name = "thf"
            else:
                guest_name = guest_type
            
            # Small cages (12 = 5^12 cages)
            if small_occ > 0:
                guest_spec = f"12={guest_name}"
                if small_occ < 1.0:
                    guest_spec = f"12={guest_name}*{small_occ}"
                parse_guest(guests, guest_spec)
            
            # Large cages
            if large_occ > 0:
                # Determine large cage type based on lattice
                if config.lattice_type == "sI":
                    large_cage = "14"  # 5^12 6^4 for sI
                elif config.lattice_type == "sII":
                    large_cage = "16"  # 5^12 6^4 for sII
                else:
                    large_cage = "16"  # Default for sH
                
                guest_spec = f"{large_cage}={guest_name}"
                if large_occ < 1.0:
                    guest_spec = f"{large_cage}={guest_name}*{large_occ}"
                parse_guest(guests, guest_spec)
            
            # Generate hydrate structure using GenIce API
            gro_string = ice.generate_ice(
                formatter=formatter,
                water=water,
                guests=guests,
                depol='strict'
            )
            
            # Parse GRO format result
            return self._parse_gro_result(gro_string)
        
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
        residue_names = []  # Track residue names for guest molecule identification
        residue_seq_nums = []  # Track residue sequence numbers for molecule grouping
        
        for i in range(2, min(2 + n_atoms, len(lines))):
            line = lines[i]
            if not line.strip() or len(line) < 44:
                continue
            
            # GRO format fixed-width columns
            # Columns 0-5: residue sequence number (right-aligned)
            # Columns 5-10: residue name
            # Columns 10-15: atom name
            # Columns 20-28, 28-36, 36-44: x, y, z in nm
            # Example: "    1ICE      OW    1   1.065   0.370   0.004"
            #           ^5  ^10     ^15
            
            # Extract residue sequence number (columns 0-5) for grouping molecules
            try:
                residue_seq = int(line[0:5].strip())
            except ValueError:
                residue_seq = i  # Fallback to line index
            residue_seq_nums.append(residue_seq)
            
            # Extract residue name from columns 5-10 (needed for THF identification)
            residue_name = line[5:10].strip()
            residue_names.append(residue_name)
            
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
        
        # NOTE: Do NOT wrap positions here!
        # Wrapping must happen in generate() with molecule grouping (line 103).
        # If we wrap here individually, molecules spanning boundaries will be
        # split across the cell before molecule_index is built, causing atoms
        # to be missing from rendered molecules.
        
        return positions, cell, atom_names, residue_names, residue_seq_nums
    
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
    
    def _wrap_positions_to_cell(self, positions: np.ndarray, cell: np.ndarray, molecule_index: list = None) -> np.ndarray:
        """Wrap atom positions into the unit cell using periodic boundary conditions.
        
        Ensures all positions are within [0, L) for each dimension, where L is
        the box length along that dimension. This handles cases where GenIce2
        outputs atoms with negative coordinates or slightly outside the box.
        
        IMPORTANT: Wraps by molecule (not individually) to keep molecules intact
        across boundaries. ALL atoms in a molecule are wrapped by the same shift
        vector, chosen to place atoms in the primary cell [0, L) when possible.
        
        Strategy:
        1. If all atoms are in the same cell (or primary cell), wrap all to primary cell
        2. If atoms span multiple cells, wrap to the mode (most common) cell
        
        Args:
            positions: (N, 3) array of atom positions in nm
            cell: (3, 3) cell matrix (orthorhombic or triclinic)
            molecule_index: List of MoleculeIndex entries for grouping atoms by molecule
        
        Returns:
            (N, 3) array of wrapped positions in [0, L) range
        """
        if molecule_index is None:
            # Fall back to individual wrapping (legacy behavior)
            return self._wrap_positions_individual(positions, cell)
        
        # Wrap by molecule (keep molecules intact)
        wrapped = positions.copy()
        
        # Determine if cell is orthorhombic
        is_orthorhombic = np.allclose(cell - np.diag(np.diag(cell)), 0)
        
        from collections import Counter
        
        if is_orthorhombic:
            L = np.diag(cell)
            
            for mol in molecule_index:
                start = mol.start_idx
                end = start + mol.count
                mol_positions = positions[start:end]
                
                # Compute the integer cell index for each atom
                cell_indices = np.floor(mol_positions / L).astype(int)
                
                # Check if all atoms are in the same cell
                unique_cells = set(tuple(idx) for idx in cell_indices)
                
                if len(unique_cells) == 1:
                    # All atoms in same cell - wrap to primary cell (0, 0, 0)
                    current_cell = np.array(list(unique_cells)[0])
                    shift = -current_cell * L
                    wrapped[start:end] = mol_positions + shift
                else:
                    # Atoms span multiple cells - wrap to mode cell
                    # But prefer primary cell if it's the mode
                    cell_tuples = [tuple(idx) for idx in cell_indices]
                    counter = Counter(cell_tuples)
                    most_common = counter.most_common()
                    max_count = most_common[0][1]
                    mode_candidates = [idx for idx, count in most_common if count == max_count]
                    
                    if (0, 0, 0) in mode_candidates:
                        mode_index = np.array((0, 0, 0))
                    else:
                        mode_index = np.array(mode_candidates[0])
                    
                    # Calculate shift for EACH atom individually
                    for i, atom_idx in enumerate(cell_indices):
                        shift = (mode_index - atom_idx) * L
                        wrapped[start + i] = mol_positions[i] + shift
        else:
            # Triclinic cell - use fractional coordinates
            cell_inv = np.linalg.inv(cell)
            
            for mol in molecule_index:
                start = mol.start_idx
                end = start + mol.count
                mol_positions = positions[start:end]
                
                # Convert to fractional coordinates
                frac = mol_positions @ cell_inv
                
                # Compute the integer cell index for each atom in fractional space
                cell_indices = np.floor(frac).astype(int)
                
                # Check if all atoms are in the same cell
                unique_cells = set(tuple(idx) for idx in cell_indices)
                
                if len(unique_cells) == 1:
                    # All atoms in same cell - wrap to primary cell (0, 0, 0)
                    current_cell = np.array(list(unique_cells)[0])
                    shift_frac = -current_cell
                    for i in range(len(mol_positions)):
                        frac_wrapped = frac[i] + shift_frac
                        # Wrap to [0, 1)
                        frac_wrapped = frac_wrapped - np.floor(frac_wrapped)
                        wrapped[start + i] = frac_wrapped @ cell
                else:
                    # Atoms span multiple cells - wrap to mode cell
                    cell_tuples = [tuple(idx) for idx in cell_indices]
                    counter = Counter(cell_tuples)
                    most_common = counter.most_common()
                    max_count = most_common[0][1]
                    mode_candidates = [idx for idx, count in most_common if count == max_count]
                    
                    if (0, 0, 0) in mode_candidates:
                        mode_index = np.array((0, 0, 0))
                    else:
                        mode_index = np.array(mode_candidates[0])
                    
                    # Calculate shift for EACH atom individually, then wrap to [0, 1)
                    for i, atom_idx in enumerate(cell_indices):
                        shift_frac = mode_index - atom_idx
                        frac_wrapped = frac[i] + shift_frac
                        # Wrap to [0, 1)
                        frac_wrapped = frac_wrapped - np.floor(frac_wrapped)
                        wrapped[start + i] = frac_wrapped @ cell
        
        return wrapped
    
    def _wrap_positions_individual(self, positions: np.ndarray, cell: np.ndarray) -> np.ndarray:
        """Wrap individual atom positions into the unit cell (legacy behavior).
        
        Args:
            positions: (N, 3) array of atom positions in nm
            cell: (3, 3) cell matrix (orthorhombic or triclinic)
        
        Returns:
            (N, 3) array of wrapped positions in [0, L) range
        """
        # For orthorhombic cells (diagonal matrix), use simple modulo
        # For non-orthogonal cells, convert to fractional coordinates, wrap, convert back
        if np.allclose(cell - np.diag(np.diag(cell)), 0):
            # Orthorhombic: cell is diagonal
            # Get box lengths from diagonal
            L = np.diag(cell)
            # Wrap each dimension using modulo (handles negative values too)
            wrapped = positions % L
            # Handle any positions that ended up at exactly L (should be 0)
            wrapped = np.where(wrapped < 0, 0.0, wrapped)
            wrapped = np.where(wrapped >= L, L - 1e-10, wrapped)
            return wrapped
        else:
            # Triclinic cell: use fractional coordinate wrapping
            # Convert to fractional coordinates
            cell_inv = np.linalg.inv(cell)
            frac = positions @ cell_inv
            # Wrap to [0, 1)
            frac = frac - np.floor(frac)
            # Convert back to Cartesian
            return frac @ cell
    
    def _build_molecule_index(self, atom_names: list[str], positions: np.ndarray, residue_names: list[str] = None, residue_seq_nums: list[int] = None) -> list[MoleculeIndex]:
        """Build molecule index from atom names.
        
        Groups atoms by molecule type based on atom naming patterns and residue names.
        
        Handles:
        - TIP4P water: OW, HW1, HW2, MW (4 atoms)
        - 3-site water: O, H, H (3 atoms) 
        - United-atom methane: Me (1 atom)
        - All-atom methane: C, H, H, H, H (5 atoms)
        - THF: residue "THF" with O, CA, CA, CB, CB, H... (13 atoms)
        - Ions: Na, Cl (1 atom each)
        
        Args:
            atom_names: List of atom names from GRO file
            positions: Array of positions (for length reference)
            residue_names: List of residue names from GRO file (for guest identification)
            residue_seq_nums: List of residue sequence numbers (for grouping molecules)
        """
        molecule_index = []
        i = 0
        
        # Default empty residue_names if not provided
        if residue_names is None:
            residue_names = [""] * len(atom_names)
        
        # Default empty residue_seq_nums if not provided
        if residue_seq_nums is None:
            residue_seq_nums = list(range(len(atom_names)))
        
        while i < len(atom_names):
            atom = atom_names[i]
            residue = residue_names[i] if i < len(residue_names) else ""
            
            # Check for THF first (using residue name from GenIce2)
            # THF from GenIce2 has residue "THF" with 13 atoms: O, CA, CA, CB, CB, + 8H
            # Each THF molecule has a unique residue sequence number
            if residue == "THF":
                # Find all atoms with the same residue sequence number (same THF molecule)
                thf_seq = residue_seq_nums[i]
                thf_start = i
                thf_count = 0
                j = i
                while j < len(residue_seq_nums) and residue_seq_nums[j] == thf_seq:
                    thf_count += 1
                    j += 1
                molecule_index.append(MoleculeIndex(thf_start, thf_count, "thf"))
                i = j
                continue
            
            # Check for guest molecules (unique atom types)
            if atom == "Me":
                # United-atom methane (Me)
                molecule_index.append(MoleculeIndex(i, 1, "ch4"))
                i += 1
                continue
            
            # Check for all-atom methane (C followed by H atoms)
            # Be careful not to match THF carbon atoms (CA, CB)
            if atom == "C" and i + 4 < len(atom_names):
                # Make sure this is actually methane (C followed by 4 H atoms)
                # Check that residue is not THF (which uses CA, CB naming)
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
                # Make sure this isn't THF oxygen (THF has residue "THF")
                if atom_names[i+1] == "H" and atom_names[i+2] == "H" and residue != "THF":
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