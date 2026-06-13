"""Solute insertion module for concentration-based THF/CH4 placement.

This module provides the SoluteInserter class which calculates solute molecule counts
from concentration and volume, then places them in liquid water regions with random
position and rotation while checking for all-atom overlaps.

All coordinates are in nanometers (nm).
"""

import logging
import random
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from quickice.structure_generation.types import (
    SoluteConfig,
    SoluteStructure,
    InterfaceStructure,
    MoleculeIndex,
    WATER_ATOMS_PER_MOLECULE,
)
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
from quickice.structure_generation.itp_parser import parse_itp_file


logger = logging.getLogger(__name__)


# Physical constants
AVOGADRO = 6.02214076e23  # mol^-1

# Minimum separation distance between molecules (nm)
MIN_SEPARATION = 0.3  # 3 Å


class SoluteInserter:
    """Handles concentration-based solute insertion into liquid water regions.
    
    Calculates solute molecule counts from concentration (mol/L), generates random
    positions and orientations, checks all-atom overlaps, and places molecules
    in liquid water regions.
    
    Attributes:
        config: SoluteConfig with concentration and placement settings
        rng: Random state for reproducibility
        registry: MoleculetypeRegistry for GROMACS naming
    """
    
    def __init__(self, config: SoluteConfig | None = None, seed: int | None = None):
        """Initialize SoluteInserter.

        Args:
            config: SoluteConfig configuration (optional, creates default if None)
            seed: Random seed for reproducibility (optional)
        """
        self.config = config if config is not None else SoluteConfig()
        self.rng = random.Random(seed)
        self.registry = MoleculetypeRegistry()
    
    def calculate_molecule_count(
        self,
        concentration_molar: float,
        liquid_volume_nm3: float,
    ) -> int:
        """Calculate number of molecules from concentration and volume.
        
        Uses: N = C_M × V_L × NA
        
        Where:
            - C_M = concentration in mol/L (molarity)
            - V_L = liquid volume in nm³ converted to L (× 1e-24)
            - NA = Avogadro's number
        
        Args:
            concentration_molar: Solute concentration in mol/L (M)
            liquid_volume_nm3: Liquid region volume in nm³
            
        Returns:
            Number of molecules to insert
        """
        # Convert nm³ to L: 1 nm³ = 1e-24 L
        volume_liters = liquid_volume_nm3 * 1e-24
        
        # Calculate molecules from molarity
        n_molecules = concentration_molar * volume_liters * AVOGADRO
        
        return int(round(n_molecules))
    
    def _generate_ch4_coordinates(self) -> np.ndarray:
        """Generate CH4 (methane) coordinates with tetrahedral geometry.
        
        Uses C-H bond length from ITP file (0.109620 nm) and tetrahedral
        H-C-H angle of 109.47 degrees.
        
        Returns:
            (5, 3) array with [C, H1, H2, H3, H4] positions centered at origin
        """
        # Bond length from ch4.itp
        r_ch = 0.109620  # nm
        
        # Tetrahedral geometry: C at center, 4 H atoms at corners of tetrahedron
        # Tetrahedral angle = arccos(-1/3) ≈ 109.47°
        
        # Place C at origin
        c_pos = np.array([0.0, 0.0, 0.0])
        
        # Place H atoms at tetrahedral positions
        # Tetrahedral directions scaled by r_ch (normalization loop below sets correct bond length)
        h1 = np.array([r_ch, r_ch, r_ch])
        h2 = np.array([r_ch, -r_ch, -r_ch])
        h3 = np.array([-r_ch, r_ch, -r_ch])
        h4 = np.array([-r_ch, -r_ch, r_ch])
        
        # Scale to correct bond length
        for h in [h1, h2, h3, h4]:
            h[:] = h / np.linalg.norm(h) * r_ch
        
        positions = np.array([c_pos, h1, h2, h3, h4])
        return positions
    
    def _generate_thf_coordinates(self) -> np.ndarray:
        """Generate THF (tetrahydrofuran) coordinates with correct geometry.

        THF is a 5-membered ring: O-CB-CA-CA-CB with 8 hydrogens.
        Uses coordinates from actual hydrate structure verified against thf.itp.

        Bond lengths from ITP:
        - O-CB: 0.143460 nm
        - CA-CA: 0.154830 nm
        - CA-CB: 0.154830 nm
        - CA-H: 0.109540 nm
        - CB-H: 0.109720 nm

        Returns:
            (13, 3) array with atom positions centered at origin:
            [O, CA, CA, CB, CB, H1, H2, H3, H4, H5, H6, H7, H8]

        Note:
            Coordinates match thf.itp atom ordering:
            - Atoms 1-5: O, CA, CA, CB, CB (ring atoms)
            - Atoms 6-9: H on CA carbons
            - Atoms 10-13: H on CB carbons
        """
        # THF template coordinates (centered at origin)
        # Based on actual hydrate structure verified against thf.itp
        # Bond lengths: O-CB ~0.143 nm, C-C ~0.154 nm, C-H ~0.109 nm
        # H-C-H angles: ~107-108° (tetrahedral geometry)
        thf_template = np.array([
            [ 0.149462,  0.000000,  0.000000],  # O
            [-0.074538, -0.072000, -0.022000],  # CA (atom 2)
            [-0.074538,  0.072000,  0.022000],  # CA (atom 3)
            [ 0.065462, -0.116000,  0.014000],  # CB (atom 4)
            [ 0.066462,  0.116000, -0.014000],  # CB (atom 5)
            [-0.151538, -0.133000,  0.026000],  # H (atom 6) - on CA
            [-0.088538, -0.078000, -0.131000],  # H (atom 7) - on CA
            [-0.151538,  0.133000, -0.026000],  # H (atom 8) - on CA
            [-0.088538,  0.078000,  0.131000],  # H (atom 9) - on CA
            [ 0.071462, -0.149000,  0.118000],  # H (atom 10) - on CB
            [ 0.102462, -0.196000, -0.051000],  # H (atom 11) - on CB
            [ 0.071462,  0.149000, -0.118000],  # H (atom 12) - on CB
            [ 0.102462,  0.196000,  0.051000],  # H (atom 13) - on CB
        ])

        return thf_template.copy()
    
    def _load_solute_template(
        self,
        solute_type: str,
    ) -> tuple[np.ndarray, list[str], list[str]]:
        """Load solute molecule template from bundled ITP file.
        
        Args:
            solute_type: Solute type ("CH4" or "THF")
            
        Returns:
            Tuple of (positions, atom_names, atom_types)
            - positions: (N_atoms, 3) template positions centered at origin
            - atom_names: List of atom names (for visualization and atomic number lookup)
            - atom_types: List of atom types from ITP file (for forcefield)
            
        Raises:
            FileNotFoundError: If ITP file not found
            ValueError: If solute_type is invalid
        """
        if solute_type not in ("CH4", "THF"):
            raise ValueError(f"Invalid solute_type: {solute_type}. Must be 'CH4' or 'THF'")
        
        # Get path to bundled ITP file
        data_dir = Path(__file__).parent.parent / "data"
        itp_file = data_dir / f"{solute_type.lower()}.itp"
        
        if not itp_file.exists():
            raise FileNotFoundError(f"ITP file not found: {itp_file}")
        
        # Parse ITP file
        itp_info = parse_itp_file(itp_file)
        
        logger.info(
            f"Loaded {solute_type} template: {itp_info.molecule_name}, "
            f"{itp_info.atom_count} atoms"
        )
        
        # Generate molecular coordinates based on type
        if solute_type == "CH4":
            positions = self._generate_ch4_coordinates()
        elif solute_type == "THF":
            positions = self._generate_thf_coordinates()
        else:
            # Fallback to zeros (should not reach here due to validation above)
            positions = np.zeros((itp_info.atom_count, 3))
        
        # Use atom names (not types) for visualization
        # Atom names are the actual element identifiers (C, H, O, etc.)
        atom_names = itp_info.atom_names
        atom_types = itp_info.atom_types
        
        logger.info(
            f"Generated {solute_type} template coordinates: "
            f"{positions.shape[0]} atoms, center at origin"
        )
        
        return positions, atom_names, atom_types
    
    def _generate_random_rotation_matrix(self) -> np.ndarray:
        """Generate random 3x3 rotation matrix.
        
        Uses uniform random quaternion for unbiased rotation.
        
        Returns:
            (3, 3) rotation matrix
        """
        rotation = Rotation.random(random_state=self.rng.randint(0, 2**31 - 1))
        return rotation.as_matrix()
    
    def _rotate_molecule(
        self,
        positions: np.ndarray,
        rotation_matrix: np.ndarray,
    ) -> np.ndarray:
        """Rotate molecule around its center of mass.
        
        Args:
            positions: (N_atoms, 3) positions in nm
            rotation_matrix: (3, 3) rotation matrix
            
        Returns:
            Rotated positions
        """
        # Calculate center
        center = positions.mean(axis=0)
        
        # Translate to origin
        centered = positions - center
        
        # Apply rotation
        rotated = centered @ rotation_matrix.T
        
        # Translate back
        return rotated + center
    
    def _build_existing_atoms_tree(
        self,
        structure: InterfaceStructure,
        exclude_water: bool = False,
    ) -> cKDTree | None:
        """Build cKDTree from existing atoms for overlap checking.
        
        Args:
            structure: InterfaceStructure with positions and atom_names
            exclude_water: If True, exclude water molecules (for replacement)
            
        Returns:
            cKDTree of atom positions, or None if no atoms
            
        Note:
            Excludes MW atoms (virtual sites) to avoid false positives.
            MW atoms are massless virtual sites in TIP4P water models,
            placed very close (~0.015 nm) to oxygen atoms.
        """
        existing_positions = []
        
        # Get region boundaries
        ice_atom_count = getattr(structure, 'ice_atom_count', 0)
        water_atom_count = getattr(structure, 'water_atom_count', 0)
        guest_atom_count = getattr(structure, 'guest_atom_count', 0)
        
        # Add ice atoms (if exclude_water is True, keep ice)
        if ice_atom_count > 0:
            for i in range(ice_atom_count):
                atom_name = structure.atom_names[i] if i < len(structure.atom_names) else ""
                if atom_name != "MW":  # Exclude virtual sites
                    existing_positions.append(structure.positions[i])
        
        # Add water atoms (skip if exclude_water is True)
        if not exclude_water and water_atom_count > 0:
            water_start = ice_atom_count
            water_end = ice_atom_count + water_atom_count
            for i in range(water_start, water_end):
                atom_name = structure.atom_names[i] if i < len(structure.atom_names) else ""
                if atom_name != "MW":  # Exclude virtual sites
                    existing_positions.append(structure.positions[i])
        
        # Add guest atoms
        if guest_atom_count > 0:
            guest_start = ice_atom_count + water_atom_count
            guest_end = guest_start + guest_atom_count
            for i in range(guest_start, guest_end):
                atom_name = structure.atom_names[i] if i < len(structure.atom_names) else ""
                if atom_name != "MW":  # Exclude virtual sites
                    existing_positions.append(structure.positions[i])
        
        if existing_positions:
            return cKDTree(np.array(existing_positions))
        return None
    
    def _check_solute_overlap(
        self,
        solute_positions: np.ndarray,
        existing_tree: cKDTree,
        min_separation: float,
    ) -> bool:
        """Check if solute molecule overlaps with existing atoms.
        
        Checks ALL atoms in solute molecule (not just center-of-mass).
        
        Args:
            solute_positions: (N_atoms, 3) positions for solute molecule
            existing_tree: cKDTree of existing atoms
            min_separation: Minimum allowed distance in nm
            
        Returns:
            True if overlap detected, False if placement is valid
        """
        for atom_pos in solute_positions:
            min_dist = existing_tree.query(atom_pos, k=1)[0]
            if min_dist < min_separation:
                return True
        return False
    
    def _remove_overlapping_water(
        self,
        structure: InterfaceStructure,
        solute_positions: np.ndarray,
        min_separation: float,
    ) -> InterfaceStructure:
        """Remove water molecules that overlap with placed solutes.
        
        CRITICAL: This is the water replacement logic. For each water molecule,
        check if any of its atoms are within min_separation of any solute atom.
        If so, remove that entire water molecule.
        
        Args:
            structure: Original InterfaceStructure with ice, water, and guests
            solute_positions: (N_solute_atoms, 3) positions of placed solutes
            min_separation: Minimum distance threshold for overlap (nm)
            
        Returns:
            New InterfaceStructure with overlapping water molecules removed
        """
        from quickice.structure_generation.types import InterfaceStructure
        
        # If no solutes placed, return original structure
        if len(solute_positions) == 0:
            logger.info("No solutes placed, keeping all water molecules")
            return structure
        
        # Build KDTree from solute atoms
        solute_tree = cKDTree(solute_positions)
        
        # Get water molecule boundaries
        ice_atom_count = structure.ice_atom_count
        water_atom_count = structure.water_atom_count
        
        # Calculate atoms per water molecule
        # This handles both TIP3P (3 atoms) and TIP4P (4 atoms) models
        water_nmolecules = getattr(structure, 'water_nmolecules', None)
        if water_nmolecules is None:
            # Calculate from water_atom_count (assume TIP4P: 4 atoms per molecule)
            water_nmolecules = water_atom_count // WATER_ATOMS_PER_MOLECULE if water_atom_count > 0 else 0
        
        if water_nmolecules > 0:
            atoms_per_water = water_atom_count // water_nmolecules
        else:
            # Fallback to TIP4P (most common in this codebase)
            atoms_per_water = WATER_ATOMS_PER_MOLECULE
        
        water_start = ice_atom_count
        water_end = ice_atom_count + water_atom_count
        # Use water_nmolecules calculated earlier (handles both InterfaceStructure and CustomMoleculeStructure)
        n_water_molecules = water_nmolecules
        
        # Track which water molecules to keep
        water_molecules_to_keep = []
        removed_count = 0
        
        # Check each water molecule
        for mol_idx in range(n_water_molecules):
            atom_start = water_start + mol_idx * atoms_per_water
            atom_end = atom_start + atoms_per_water
            
            # Get positions for this water molecule
            water_mol_positions = structure.positions[atom_start:atom_end]
            
            # Check if any atom in this water molecule overlaps with solutes
            overlaps = False
            for atom_pos in water_mol_positions:
                min_dist = solute_tree.query(atom_pos, k=1)[0]
                if min_dist < min_separation:
                    overlaps = True
                    break
            
            if not overlaps:
                # Keep this water molecule
                water_molecules_to_keep.append(mol_idx)
            else:
                removed_count += 1
        
        logger.info(
            f"Water replacement: Removed {removed_count} water molecules "
            f"({removed_count * atoms_per_water} atoms) that overlapped with solutes"
        )
        
        # If no water molecules removed, return original with custom molecule attributes set
        if removed_count == 0:
            # For CustomMoleculeStructure, set custom molecule positions/atom_names attributes
            # so downstream code can access them
            if hasattr(structure, 'custom_molecule_atom_count') and structure.custom_molecule_atom_count > 0:
                guest_atom_count = getattr(structure, 'guest_atom_count', 0)
                custom_start = ice_atom_count + water_atom_count + guest_atom_count
                
                # Set attributes on the structure (if not already set)
                if not hasattr(structure, 'custom_molecule_positions'):
                    structure.custom_molecule_positions = structure.positions[custom_start:]
                if not hasattr(structure, 'custom_molecule_atom_names'):
                    structure.custom_molecule_atom_names = list(structure.atom_names[custom_start:])
                if hasattr(structure, 'moleculetype_name') and not hasattr(structure, 'custom_molecule_moleculetype'):
                    structure.custom_molecule_moleculetype = structure.moleculetype_name
                if hasattr(structure, 'gro_path') and not hasattr(structure, 'custom_gro_path'):
                    structure.custom_gro_path = structure.gro_path
                if hasattr(structure, 'itp_path') and not hasattr(structure, 'custom_itp_path'):
                    structure.custom_itp_path = structure.itp_path
            
            return structure
        
        # Build new structure with water molecules removed
        # Keep ice atoms
        ice_positions = structure.positions[:ice_atom_count]
        ice_atom_names = structure.atom_names[:ice_atom_count]
        
        # Keep only non-overlapping water molecules
        kept_water_positions = []
        kept_water_atom_names = []
        for mol_idx in water_molecules_to_keep:
            atom_start = water_start + mol_idx * atoms_per_water
            atom_end = atom_start + atoms_per_water
            kept_water_positions.append(structure.positions[atom_start:atom_end])
            kept_water_atom_names.extend(structure.atom_names[atom_start:atom_end])
        
        # Keep guest atoms
        guest_start = ice_atom_count + water_atom_count
        
        # Check if structure has custom molecules (CustomMoleculeStructure case)
        # For CustomMoleculeStructure, guest_atom_count is 0, but custom molecules exist
        # They are appended after guests, so we need to separate them
        has_custom_molecules = hasattr(structure, 'custom_molecule_atom_count') and structure.custom_molecule_atom_count > 0
        
        if has_custom_molecules:
            # Separate guests and custom molecules
            # Structure is: ice + water + guests + custom molecules
            guest_atom_count = getattr(structure, 'guest_atom_count', 0)
            guest_end = guest_start + guest_atom_count
            
            guest_positions = structure.positions[guest_start:guest_end]
            guest_atom_names = structure.atom_names[guest_start:guest_end]
            
            # Custom molecules come after guests
            custom_start = guest_end
            custom_positions = structure.positions[custom_start:]
            custom_atom_names = structure.atom_names[custom_start:]
        else:
            # No custom molecules, everything after water is guests
            guest_positions = structure.positions[guest_start:]
            guest_atom_names = structure.atom_names[guest_start:]
            custom_positions = None
            custom_atom_names = None
        
        # Combine: ice + kept_water + guests + custom_molecules (if present)
        if kept_water_positions:
            water_positions_array = np.vstack(kept_water_positions)
        else:
            water_positions_array = np.zeros((0, 3))
        
        # Build positions array
        position_arrays = [ice_positions, water_positions_array, guest_positions]
        if has_custom_molecules and custom_positions is not None:
            position_arrays.append(custom_positions)
        
        new_positions = np.vstack(position_arrays)
        
        # Build atom names list
        new_atom_names = (
            list(ice_atom_names) +
            kept_water_atom_names +
            list(guest_atom_names)
        )
        if has_custom_molecules and custom_atom_names is not None:
            new_atom_names.extend(custom_atom_names)
        
        # Update molecule_index to reflect new positions array
        # CRITICAL: Old molecule_index has indices pointing to old positions array
        # Need to rebuild molecule_index with correct start_idx values
        new_molecule_index = []
        current_idx = 0
        
        # Check if structure has molecule_index to rebuild
        # If not, leave molecule_index empty (ion_inserter will build it if needed)
        if hasattr(structure, 'molecule_index') and structure.molecule_index:
            # Add ice molecules (indices don't change, they're at the start)
            for mol in structure.molecule_index:
                if mol.mol_type == "ice":
                    new_molecule_index.append(MoleculeIndex(
                        start_idx=current_idx,
                        count=mol.count,
                        mol_type=mol.mol_type,
                    ))
                    current_idx += mol.count
            
            # Add kept water molecules with updated indices
            atoms_per_water = water_atom_count // n_water_molecules if n_water_molecules > 0 else WATER_ATOMS_PER_MOLECULE
            for mol_idx in water_molecules_to_keep:
                new_molecule_index.append(MoleculeIndex(
                    start_idx=current_idx,
                    count=atoms_per_water,
                    mol_type="water",
                ))
                current_idx += atoms_per_water
            
            # Add guest molecules with shifted indices
            # current_idx already accounts for removed water atoms
            for mol in structure.molecule_index:
                if mol.mol_type == "guest":
                    new_molecule_index.append(MoleculeIndex(
                        start_idx=current_idx,
                        count=mol.count,
                        mol_type=mol.mol_type,
                    ))
                    current_idx += mol.count
            
            # Add custom molecules with shifted indices
            # This preserves custom molecule information through the workflow
            if has_custom_molecules:
                for mol in structure.molecule_index:
                    if mol.mol_type == "custom":
                        new_molecule_index.append(MoleculeIndex(
                            start_idx=current_idx,
                            count=mol.count,
                            mol_type=mol.mol_type,
                        ))
                        current_idx += mol.count
        
        # Create new InterfaceStructure
        # For CustomMoleculeStructure, get mode and report from interface_structure
        mode = getattr(structure, 'mode', None)
        report = getattr(structure, 'report', None)
        if mode is None and hasattr(structure, 'interface_structure'):
            mode = getattr(structure.interface_structure, 'mode', 'slab')
        if report is None and hasattr(structure, 'interface_structure'):
            report = getattr(structure.interface_structure, 'report', '')
        
        new_interface = InterfaceStructure(
            positions=new_positions,
            atom_names=new_atom_names,
            cell=structure.cell,
            ice_atom_count=structure.ice_atom_count,
            water_atom_count=len(kept_water_atom_names),
            ice_nmolecules=getattr(structure, 'ice_nmolecules', 0),
            water_nmolecules=len(water_molecules_to_keep),
            mode=mode or 'slab',
            report=report or '',
            guest_atom_count=structure.guest_atom_count,
            molecule_index=new_molecule_index,
            guest_nmolecules=getattr(structure, 'guest_nmolecules', 0),
        )
        
        # Preserve custom molecule attributes if present in input structure
        # This handles the workflow: Interface → Custom → Solute → Ion
        # When solutes are inserted from a CustomMoleculeStructure, we need to
        # preserve the custom molecule information for downstream processing
        if has_custom_molecules:
            # Preserve custom molecule count and metadata
            if hasattr(structure, 'custom_molecule_count'):
                new_interface.custom_molecule_count = structure.custom_molecule_count
            if hasattr(structure, 'moleculetype_name'):
                new_interface.custom_molecule_moleculetype = structure.moleculetype_name
            if hasattr(structure, 'gro_path'):
                new_interface.custom_gro_path = structure.gro_path
            if hasattr(structure, 'itp_path'):
                new_interface.custom_itp_path = structure.itp_path
            
            # Set custom molecule atom count and positions from the actual data
            # (not from potentially stale attributes)
            new_interface.custom_molecule_atom_count = len(custom_atom_names) if custom_atom_names else 0
            new_interface.custom_molecule_positions = custom_positions
            new_interface.custom_molecule_atom_names = list(custom_atom_names) if custom_atom_names else []
        
        return new_interface
    
    def insert_solutes(
        self,
        structure: InterfaceStructure,
        config: SoluteConfig | None = None,
    ) -> SoluteStructure:
        """Insert solute molecules into liquid water region.
        
        Args:
            structure: InterfaceStructure with ice and water
            config: SoluteConfig (optional, uses self.config if None)
            
        Returns:
            SoluteStructure with placed molecules
            
        Raises:
            ValueError: If concentration is invalid or no liquid region
        """
        if config is None:
            config = self.config
        
        # Validate concentration
        if config.concentration_molar < 0:
            raise ValueError(
                f"Invalid concentration: {config.concentration_molar} mol/L. "
                "Must be >= 0."
            )
        
        # Get structure info
        ice_atom_count = getattr(structure, 'ice_atom_count', 0)
        water_atom_count = getattr(structure, 'water_atom_count', 0)
        guest_atom_count = getattr(structure, 'guest_atom_count', 0)
        
        # Calculate liquid volume from water molecule count
        # TIP4P water volume per molecule: 0.0299 nm³
        # Handle both InterfaceStructure (has water_nmolecules) and CustomMoleculeStructure (doesn't)
        water_nmolecules = getattr(structure, 'water_nmolecules', None)
        if water_nmolecules is None:
            # Calculate from water_atom_count (assume TIP4P: 4 atoms per molecule)
            water_nmolecules = water_atom_count // WATER_ATOMS_PER_MOLECULE if water_atom_count > 0 else 0
        
        liquid_volume_nm3 = water_nmolecules * 0.0299
        
        # Calculate molecule count
        n_molecules = self.calculate_molecule_count(
            config.concentration_molar,
            liquid_volume_nm3
        )
        
        if n_molecules == 0:
            logger.warning(
                f"Concentration too low: {config.concentration_molar} M in "
                f"{liquid_volume_nm3:.1f} nm³ results in 0 molecules"
            )
            # Extract custom molecule attributes from input structure
            # This preserves custom molecule info for downstream processing
            custom_molecule_count = getattr(structure, 'custom_molecule_count', 0)
            custom_molecule_atom_count = getattr(structure, 'custom_molecule_atom_count', 0)
            custom_molecule_positions = getattr(structure, 'custom_molecule_positions', None)
            custom_molecule_atom_names = getattr(structure, 'custom_molecule_atom_names', None)
            custom_molecule_moleculetype = getattr(structure, 'custom_molecule_moleculetype', "")
            custom_gro_path = getattr(structure, 'custom_gro_path', None)
            custom_itp_path = getattr(structure, 'custom_itp_path', None)
            
            return SoluteStructure(
                positions=np.zeros((0, 3)),
                atom_names=[],
                cell=structure.cell,
                solute_type=config.solute_type,
                n_molecules=0,
                molecule_indices=[],
                registry=self.registry,
                interface_structure=structure,
                custom_molecule_count=custom_molecule_count,
                custom_molecule_atom_count=custom_molecule_atom_count,
                custom_molecule_positions=custom_molecule_positions,
                custom_molecule_atom_names=custom_molecule_atom_names,
                custom_molecule_moleculetype=custom_molecule_moleculetype,
                custom_gro_path=custom_gro_path,
                custom_itp_path=custom_itp_path,
            )
        
        # Load solute template
        template_positions, template_atom_names, template_atom_types = \
            self._load_solute_template(config.solute_type)
        
        n_atoms_per_molecule = len(template_atom_names)
        
        # Build tree from existing atoms (exclude water for replacement)
        existing_tree = self._build_existing_atoms_tree(
            structure,
            exclude_water=True
        )
        
        # Get liquid region bounds
        # CRITICAL: Only sample positions from liquid region
        liquid_start = ice_atom_count
        liquid_end = ice_atom_count + water_atom_count
        
        if liquid_start >= liquid_end or water_atom_count == 0:
            logger.warning("No liquid water region available for solute insertion")
            # Extract custom molecule attributes from input structure
            # This preserves custom molecule info for downstream processing
            custom_molecule_count = getattr(structure, 'custom_molecule_count', 0)
            custom_molecule_atom_count = getattr(structure, 'custom_molecule_atom_count', 0)
            custom_molecule_positions = getattr(structure, 'custom_molecule_positions', None)
            custom_molecule_atom_names = getattr(structure, 'custom_molecule_atom_names', None)
            custom_molecule_moleculetype = getattr(structure, 'custom_molecule_moleculetype', "")
            custom_gro_path = getattr(structure, 'custom_gro_path', None)
            custom_itp_path = getattr(structure, 'custom_itp_path', None)
            
            return SoluteStructure(
                positions=np.zeros((0, 3)),
                atom_names=[],
                cell=structure.cell,
                solute_type=config.solute_type,
                n_molecules=0,
                molecule_indices=[],
                registry=self.registry,
                interface_structure=structure,
                custom_molecule_count=custom_molecule_count,
                custom_molecule_atom_count=custom_molecule_atom_count,
                custom_molecule_positions=custom_molecule_positions,
                custom_molecule_atom_names=custom_molecule_atom_names,
                custom_molecule_moleculetype=custom_molecule_moleculetype,
                custom_gro_path=custom_gro_path,
                custom_itp_path=custom_itp_path,
            )
        
        # Get liquid region positions for sampling
        liquid_positions = structure.positions[liquid_start:liquid_end]
        
        # Calculate liquid region bounds
        min_coords = liquid_positions.min(axis=0)
        max_coords = liquid_positions.max(axis=0)
        
        # Save base tree data before loop to avoid O(N²) per-molecule rebuild
        base_existing_data = existing_tree.data.copy() if existing_tree is not None else None
        
        # Place molecules
        placed_positions = []
        placed_atom_names = []
        molecule_indices = []
        placed_count = 0
        current_idx = 0
        
        for mol_idx in range(n_molecules):
            placed = False
            
            for attempt in range(config.max_attempts):
                # Generate random position in liquid region
                position = np.array([
                    self.rng.uniform(min_coords[0], max_coords[0]),
                    self.rng.uniform(min_coords[1], max_coords[1]),
                    self.rng.uniform(min_coords[2], max_coords[2])
                ])
                
                # Generate random rotation
                rotation_matrix = self._generate_random_rotation_matrix()
                
                # Rotate template (centered at origin)
                rotated_positions = self._rotate_molecule(
                    template_positions.copy(),
                    rotation_matrix
                )
                
                # Translate to position
                solute_positions = rotated_positions + position
                
                # Check overlap
                if existing_tree is not None:
                    if self._check_solute_overlap(
                        solute_positions,
                        existing_tree,
                        config.min_separation
                    ):
                        continue  # Try again
                
                # Valid placement - add to structure
                placed_positions.append(solute_positions)
                placed_atom_names.extend(template_atom_names)
                molecule_indices.append((current_idx, current_idx + n_atoms_per_molecule))
                
                current_idx += n_atoms_per_molecule
                placed_count += 1
                placed = True
                
                # Rebuild tree from base + all accumulated placed positions
                # This avoids the O(N²) per-molecule vstack pattern
                if base_existing_data is not None:
                    all_placed = np.vstack(placed_positions) if placed_positions else np.zeros((0, 3))
                    existing_tree = cKDTree(np.vstack([base_existing_data, all_placed]))
                else:
                    all_placed = np.vstack(placed_positions) if placed_positions else np.zeros((0, 3))
                    existing_tree = cKDTree(all_placed)
                
                break  # Move to next molecule
            
            if not placed:
                logger.warning(
                    f"Failed to place {config.solute_type} molecule {mol_idx + 1} "
                    f"after {config.max_attempts} attempts"
                )
        
        # Generate report
        if placed_count < n_molecules:
            logger.warning(
                f"Partial success: placed {placed_count} of {n_molecules} "
                f"{config.solute_type} molecules"
            )
        
        # Register with MoleculetypeRegistry
        self.registry.register_liquid_solute(config.solute_type)

        # Create result
        if placed_positions:
            all_positions = np.vstack(placed_positions)
        else:
            all_positions = np.zeros((0, 3))

        # CRITICAL: Remove water molecules that overlap with placed solutes
        modified_interface = self._remove_overlapping_water(
            structure,
            all_positions,
            config.min_separation
        )

        # Extract custom molecule attributes from modified_interface
        # This propagates custom molecule info through the workflow: Interface → Custom → Solute → Ion
        custom_molecule_count = getattr(modified_interface, 'custom_molecule_count', 0)
        custom_molecule_atom_count = getattr(modified_interface, 'custom_molecule_atom_count', 0)
        custom_molecule_positions = getattr(modified_interface, 'custom_molecule_positions', None)
        custom_molecule_atom_names = getattr(modified_interface, 'custom_molecule_atom_names', None)
        custom_molecule_moleculetype = getattr(modified_interface, 'custom_molecule_moleculetype', "")
        custom_gro_path = getattr(modified_interface, 'custom_gro_path', None)
        custom_itp_path = getattr(modified_interface, 'custom_itp_path', None)

        return SoluteStructure(
            positions=all_positions,
            atom_names=placed_atom_names,
            cell=structure.cell,
            solute_type=config.solute_type,
            n_molecules=placed_count,
            molecule_indices=molecule_indices,
            registry=self.registry,
            interface_structure=modified_interface,
            custom_molecule_count=custom_molecule_count,
            custom_molecule_atom_count=custom_molecule_atom_count,
            custom_molecule_positions=custom_molecule_positions,
            custom_molecule_atom_names=custom_molecule_atom_names,
            custom_molecule_moleculetype=custom_molecule_moleculetype,
            custom_gro_path=custom_gro_path,
            custom_itp_path=custom_itp_path,
        )


def insert_solutes(
    structure: InterfaceStructure,
    concentration_molar: float,
    solute_type: str = "CH4",
    liquid_volume_nm3: float | None = None,
    seed: int | None = None,
) -> SoluteStructure:
    """Convenience function to insert solutes into a structure.
    
    Args:
        structure: Input InterfaceStructure with ice and water
        concentration_molar: Solute concentration in mol/L
        solute_type: Solute type ("CH4" or "THF")
        liquid_volume_nm3: Liquid volume in nm³ (optional, estimates from structure if None)
        seed: Random seed (optional)
        
    Returns:
        SoluteStructure with placed molecules
    """
    config = SoluteConfig(
        concentration_molar=concentration_molar,
        solute_type=solute_type
    )
    inserter = SoluteInserter(config=config, seed=seed)
    
    return inserter.insert_solutes(structure, config)
