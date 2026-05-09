"""Custom molecule insertion module for user-provided molecule placement.

This module provides the CustomMoleculeInserter class which handles placement
of custom molecules uploaded via .gro/.itp file pairs. Supports two placement
modes: random (with overlap checking) and custom (user-specified positions/rotations).

All coordinates are in nanometers (nm).
"""

import logging
import random
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from quickice.structure_generation.types import (
    CustomMoleculeConfig,
    CustomMoleculeStructure,
    InterfaceStructure,
    PlacementValidationResult,
)
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
from quickice.structure_generation.gro_parser import parse_gro_file


logger = logging.getLogger(__name__)


class InsertionError(Exception):
    """Raised when molecule insertion fails after max attempts.
    
    Attributes:
        message: Error message with details
        attempts: Number of attempts made
    """
    
    def __init__(self, message: str, attempts: int = 0):
        self.message = message
        self.attempts = attempts
        super().__init__(message)


class CustomMoleculeInserter:
    """Handles custom molecule placement with two modes.
    
    Mode 1 (Random): Random positions in liquid region, random rotations,
                     all-atom overlap checking (reuses SoluteInserter pattern)
    
    Mode 2 (Custom): User-specified positions and rotations (Euler angles),
                     no overlap checking (user responsibility)
    
    Attributes:
        config: CustomMoleculeConfig with placement settings
        registry: MoleculetypeRegistry for GROMACS naming
        template_positions: Template molecule positions from GRO file
        template_atom_names: Template atom names from GRO file
        residue_name: Residue name from GRO/ITP file
    """
    
    def __init__(
        self,
        config: CustomMoleculeConfig,
        registry: MoleculetypeRegistry | None = None
    ):
        """Initialize CustomMoleculeInserter.
        
        Args:
            config: CustomMoleculeConfig with placement settings
            registry: MoleculetypeRegistry (optional, creates new if None)
        """
        self.config = config
        self.registry = registry if registry is not None else MoleculetypeRegistry()
        
        # Load template from GRO file
        self.template_positions, self.template_atom_names, cell = parse_gro_file(
            config.gro_path
        )
        
        # Residue name will be determined during placement
        # (from ITP if override accepted, else from GRO)
        self.residue_name = None
        
        logger.info(
            f"Loaded custom molecule template from {config.gro_path.name}: "
            f"{len(self.template_atom_names)} atoms"
        )
    
    def validate_single_placement(
        self,
        structure: InterfaceStructure,
        position: tuple[float, float, float],
        rotation: tuple[float, float, float],
    ) -> PlacementValidationResult:
        """Validate placement for single molecule without full insertion.
        
        This is a READ-ONLY operation - does not modify MoleculetypeRegistry
        or insert any molecules. Used for validation before commit.
        
        Args:
            structure: InterfaceStructure to validate against
            position: (x, y, z) center-of-mass position in nm
            rotation: (alpha, beta, gamma) Euler angles in degrees
            
        Returns:
            PlacementValidationResult with validation outcome
        """
        # 1. Check bounds
        ice_atom_count = getattr(structure, 'ice_atom_count', 0)
        water_atom_count = getattr(structure, 'water_atom_count', 0)
        
        if water_atom_count == 0:
            return PlacementValidationResult(
                is_valid=False,
                within_bounds=False,
                has_overlap=False,
                min_distance=float('inf'),
                nearest_atom_type=None,
                error_message="No liquid region in structure"
            )
        
        liquid_positions = structure.positions[ice_atom_count:ice_atom_count + water_atom_count]
        min_coords = liquid_positions.min(axis=0)
        max_coords = liquid_positions.max(axis=0)
        
        within_bounds = all(
            min_coords[i] <= position[i] <= max_coords[i]
            for i in range(3)
        )
        
        if not within_bounds:
            return PlacementValidationResult(
                is_valid=False,
                within_bounds=False,
                has_overlap=False,
                min_distance=float('inf'),
                nearest_atom_type=None,
                error_message="Position outside liquid region"
            )
        
        # 2. Build KDTree from existing atoms (reuse existing method)
        existing_tree = self._build_existing_atoms_tree(structure)
        
        # 3. Rotate and place template molecule
        center = self.template_positions.mean(axis=0)
        centered_template = self.template_positions - center
        rot_matrix = self._euler_to_rotation_matrix(*rotation)
        rotated = centered_template @ rot_matrix.T
        placed_mol = rotated + np.array(position)
        
        # 4. Check overlap (reuse existing method)
        has_overlap = False
        min_distance = float('inf')
        nearest_atom_type = None
        nearest_atom_idx = None
        
        if existing_tree is not None:
            for atom_pos in placed_mol:
                dist, idx = existing_tree.query(atom_pos, k=1)
                if dist < min_distance:
                    min_distance = dist
                    nearest_atom_idx = idx
                if dist < self.config.min_separation:
                    has_overlap = True
        
            # Get nearest atom type for user feedback
            if nearest_atom_idx is not None and hasattr(structure, 'atom_types'):
                nearest_atom_type = structure.atom_types[ice_atom_count + nearest_atom_idx]
        
        # 5. Return result
        is_valid = within_bounds and not has_overlap
        
        error_message = None
        if not is_valid:
            if has_overlap:
                error_message = f"Overlap detected (min distance: {min_distance:.3f} nm)"
        
        return PlacementValidationResult(
            is_valid=is_valid,
            within_bounds=within_bounds,
            has_overlap=has_overlap,
            min_distance=min_distance,
            nearest_atom_type=nearest_atom_type,
            error_message=error_message
        )
    
    def _euler_to_rotation_matrix(
        self,
        alpha: float,
        beta: float,
        gamma: float
    ) -> np.ndarray:
        """Convert Euler angles (α, β, γ) to rotation matrix.
        
        Uses ZXZ convention (common in crystallography).
        
        Args:
            alpha: First rotation around Z-axis (degrees)
            beta: Second rotation around X-axis (degrees)
            gamma: Third rotation around Z-axis (degrees)
            
        Returns:
            (3, 3) rotation matrix
        """
        rotation = Rotation.from_euler('ZXZ', [alpha, beta, gamma], degrees=True)
        return rotation.as_matrix()
    
    def _build_existing_atoms_tree(
        self,
        structure: InterfaceStructure,
    ) -> cKDTree | None:
        """Build cKDTree from existing atoms for overlap checking.
        
        For custom molecule insertion, only checks ice and guest atoms.
        Liquid water atoms are EXCLUDED from overlap checking because
        they will be removed during insertion if they overlap with
        custom molecules (via _remove_overlapping_water()).
        
        Args:
            structure: InterfaceStructure with positions and atom_names
            
        Returns:
            cKDTree of atom positions (ice + guests only), or None if no atoms
            
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
        
        # Add ice atoms
        if ice_atom_count > 0:
            for i in range(ice_atom_count):
                atom_name = structure.atom_names[i] if i < len(structure.atom_names) else ""
                if atom_name != "MW":  # Exclude virtual sites
                    existing_positions.append(structure.positions[i])
        
        # DO NOT add water atoms - they will be removed if they overlap
        # with custom molecules during insertion
        
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
    
    def _check_overlap(
        self,
        positions: np.ndarray,
        existing_tree: cKDTree,
        min_separation: float,
    ) -> bool:
        """Check if molecule overlaps with existing atoms.
        
        Checks ALL atoms in molecule (not just center-of-mass).
        
        Args:
            positions: (N_atoms, 3) positions for molecule
            existing_tree: cKDTree of existing atoms
            min_separation: Minimum allowed distance in nm
            
        Returns:
            True if overlap detected, False if placement is valid
        """
        for atom_pos in positions:
            min_dist = existing_tree.query(atom_pos, k=1)[0]
            if min_dist < min_separation:
                return True
        return False
    
    def _remove_overlapping_water(
        self,
        structure: InterfaceStructure,
        custom_molecule_positions: np.ndarray,
        min_separation: float,
    ) -> InterfaceStructure:
        """Remove water molecules that overlap with placed custom molecules.
        
        CRITICAL: This is the water replacement logic. For each water molecule,
        check if any of its atoms are within min_separation of any custom molecule atom.
        If so, remove that entire water molecule.
        
        Args:
            structure: Original InterfaceStructure with ice, water, and guests
            custom_molecule_positions: (N_custom_atoms, 3) positions of placed custom molecules
            min_separation: Minimum distance threshold for overlap (nm)
            
        Returns:
            New InterfaceStructure with overlapping water molecules removed
        """
        from quickice.structure_generation.types import InterfaceStructure
        
        # If no custom molecules placed, return original structure
        if len(custom_molecule_positions) == 0:
            logger.info("No custom molecules placed, keeping all water molecules")
            return structure
        
        # Build KDTree from custom molecule atoms
        custom_tree = cKDTree(custom_molecule_positions)
        
        # Get water molecule boundaries
        ice_atom_count = structure.ice_atom_count
        water_atom_count = structure.water_atom_count
        
        # Calculate atoms per water molecule
        # This handles both TIP3P (3 atoms) and TIP4P (4 atoms) models
        if structure.water_nmolecules > 0:
            atoms_per_water = water_atom_count // structure.water_nmolecules
        else:
            # Fallback to TIP4P (most common in this codebase)
            atoms_per_water = 4
        
        water_start = ice_atom_count
        water_end = ice_atom_count + water_atom_count
        n_water_molecules = structure.water_nmolecules
        
        # Track which water molecules to keep
        water_molecules_to_keep = []
        removed_count = 0
        
        # Check each water molecule
        for mol_idx in range(n_water_molecules):
            atom_start = water_start + mol_idx * atoms_per_water
            atom_end = atom_start + atoms_per_water
            
            # Get positions for this water molecule
            water_mol_positions = structure.positions[atom_start:atom_end]
            
            # Check if any atom in this water molecule overlaps with custom molecules
            overlaps = False
            for atom_pos in water_mol_positions:
                min_dist = custom_tree.query(atom_pos, k=1)[0]
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
            f"({removed_count * atoms_per_water} atoms) that overlapped with custom molecules"
        )
        
        # If no water molecules removed, return original
        if removed_count == 0:
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
        guest_positions = structure.positions[guest_start:]
        guest_atom_names = structure.atom_names[guest_start:]
        
        # Combine: ice + kept_water + guests
        if kept_water_positions:
            water_positions_array = np.vstack(kept_water_positions)
        else:
            water_positions_array = np.zeros((0, 3))
        
        new_positions = np.vstack([
            ice_positions,
            water_positions_array,
            guest_positions
        ])
        
        new_atom_names = list(ice_atom_names) + kept_water_atom_names + list(guest_atom_names)
        
        # Update counts
        new_water_atom_count = len(kept_water_atom_names)
        new_water_nmolecules = len(water_molecules_to_keep)
        
        # Rebuild molecule_index for the new structure
        from quickice.structure_generation.types import MoleculeIndex
        new_molecule_index = []
        
        # Ice molecules
        if ice_atom_count > 0:
            ice_mol_count = ice_atom_count // 3
            current_idx = 0
            for _ in range(ice_mol_count):
                new_molecule_index.append(MoleculeIndex(current_idx, current_idx + 4, "ice"))
                current_idx += 4
        
        # Kept water molecules
        if new_water_nmolecules > 0:
            current_idx = ice_atom_count
            for _ in range(new_water_nmolecules):
                new_molecule_index.append(MoleculeIndex(current_idx, current_idx + atoms_per_water, "water"))
                current_idx += atoms_per_water
        
        # Guest molecules (shift indices for new water count)
        guest_atom_count = len(guest_atom_names)
        if guest_atom_count > 0 and hasattr(structure, 'molecule_index'):
            shift = water_atom_count - new_water_atom_count
            for mol_idx in structure.molecule_index:
                if mol_idx.mol_type == "guest":
                    new_molecule_index.append(MoleculeIndex(
                        mol_idx.start_idx - shift,
                        mol_idx.end_idx - shift,
                        "guest"
                    ))
        
        # Create new InterfaceStructure
        return InterfaceStructure(
            positions=new_positions,
            atom_names=new_atom_names,
            cell=structure.cell,
            ice_atom_count=ice_atom_count,
            water_atom_count=new_water_atom_count,
            guest_atom_count=guest_atom_count,
            ice_nmolecules=structure.ice_nmolecules,
            water_nmolecules=new_water_nmolecules,
            molecule_index=new_molecule_index if new_molecule_index else None,
            mode=getattr(structure, 'mode', 'slab'),
            report=getattr(structure, 'report', ''),
            guest_nmolecules=getattr(structure, 'guest_nmolecules', 0)
        )
    
    def place_random(
        self,
        structure: InterfaceStructure,
        n_molecules: int
    ) -> CustomMoleculeStructure:
        """Place molecules randomly in liquid region with overlap checking.
        
        Reuses SoluteInserter pattern:
        - Build cKDTree from existing atoms (exclude MW virtual sites)
        - Sample random positions in liquid region bounds
        - Generate random rotations using Rotation.random()
        - Check all-atom overlaps with min_separation threshold
        
        Args:
            structure: InterfaceStructure with ice + water
            n_molecules: Number of molecules to place
            
        Returns:
            CustomMoleculeStructure with placed molecules
            
        Raises:
            InsertionError: If placement fails after max_attempts
        """
        # Get structure info
        ice_atom_count = getattr(structure, 'ice_atom_count', 0)
        water_atom_count = getattr(structure, 'water_atom_count', 0)
        
        # Build tree from existing atoms
        existing_tree = self._build_existing_atoms_tree(structure)
        
        # Get liquid region bounds
        liquid_start = ice_atom_count
        liquid_end = ice_atom_count + water_atom_count
        
        if liquid_start >= liquid_end or water_atom_count == 0:
            raise InsertionError(
                "No liquid water region available for molecule insertion"
            )
        
        # Get liquid region positions for sampling
        liquid_positions = structure.positions[liquid_start:liquid_end]
        
        # Calculate liquid region bounds
        min_coords = liquid_positions.min(axis=0)
        max_coords = liquid_positions.max(axis=0)
        
        # Center template at origin for rotation
        center = self.template_positions.mean(axis=0)
        centered_template = self.template_positions - center
        
        # Place molecules
        placed_positions = []
        placed_atom_names = []
        molecule_index = []
        current_idx = 0
        
        for mol_idx in range(n_molecules):
            placed = False
            
            for attempt in range(self.config.max_attempts):
                # Generate random position in liquid region
                rng = random.Random()
                position = np.array([
                    rng.uniform(min_coords[0], max_coords[0]),
                    rng.uniform(min_coords[1], max_coords[1]),
                    rng.uniform(min_coords[2], max_coords[2])
                ])
                
                # Generate random rotation
                rotation = Rotation.random()
                rotation_matrix = rotation.as_matrix()
                
                # Apply rotation
                rotated = centered_template @ rotation_matrix.T
                
                # Translate to position
                placed_mol = rotated + position
                
                # Check overlap
                if existing_tree is not None:
                    if self._check_overlap(
                        placed_mol,
                        existing_tree,
                        self.config.min_separation
                    ):
                        continue  # Try again
                
                # Valid placement - add to structure
                placed_positions.append(placed_mol)
                placed_atom_names.extend(self.template_atom_names)
                molecule_index.append((current_idx, current_idx + len(self.template_atom_names)))
                
                current_idx += len(self.template_atom_names)
                placed = True
                
                # Update tree for next molecule
                if existing_tree is None:
                    existing_tree = cKDTree(placed_mol)
                else:
                    all_existing = existing_tree.data
                    all_positions = np.vstack([all_existing, placed_mol])
                    existing_tree = cKDTree(all_positions)
                
                break  # Move to next molecule
            
            if not placed:
                raise InsertionError(
                    f"Failed to place molecule {mol_idx + 1} after {self.config.max_attempts} attempts. "
                    f"Consider increasing max_attempts or reducing molecule count.",
                    attempts=self.config.max_attempts
                )
        
        # Get interface structure info
        guest_atom_count = getattr(structure, 'guest_atom_count', 0)
        
        # CRITICAL: Remove water molecules that overlap with placed custom molecules
        if placed_positions:
            all_custom_positions = np.vstack(placed_positions)
        else:
            all_custom_positions = np.zeros((0, 3))
        
        modified_structure = self._remove_overlapping_water(
            structure,
            all_custom_positions,
            self.config.min_separation
        )
        
        # Get updated counts after water removal
        ice_atom_count = modified_structure.ice_atom_count
        water_atom_count = modified_structure.water_atom_count
        guest_atom_count = modified_structure.guest_atom_count
        
        # Build complete molecule_index
        from quickice.structure_generation.types import MoleculeIndex
        complete_molecule_index = []
        
        # Ice molecules (3 input atoms -> 4 output atoms per molecule)
        if ice_atom_count > 0:
            ice_mol_count = ice_atom_count // 3  # 3 atoms per ice molecule input
            current_idx = 0
            for _ in range(ice_mol_count):
                complete_molecule_index.append(MoleculeIndex(current_idx, current_idx + 4, "ice"))
                current_idx += 4
        
        # Water molecules (4 atoms per molecule)
        if water_atom_count > 0:
            water_mol_count = water_atom_count // 4
            current_idx = ice_atom_count
            for _ in range(water_mol_count):
                complete_molecule_index.append(MoleculeIndex(current_idx, current_idx + 4, "water"))
                current_idx += 4
        
        # Guest molecules (if present)
        if guest_atom_count > 0:
            # Add guest molecule indices from structure
            if hasattr(structure, 'molecule_index'):
                for mol_idx in structure.molecule_index:
                    if mol_idx.mol_type == "guest":
                        complete_molecule_index.append(mol_idx)
        
        # Custom molecules
        current_idx = ice_atom_count + water_atom_count + guest_atom_count
        for start, end in molecule_index:
            complete_molecule_index.append(MoleculeIndex(current_idx, current_idx + (end - start), "custom"))
            current_idx += (end - start)
        
        # Combine positions and atom names from modified structure
        complete_positions = np.vstack([
            modified_structure.positions[:ice_atom_count + water_atom_count + guest_atom_count],
            np.vstack(placed_positions)
        ])
        
        complete_atom_names = list(modified_structure.atom_names[:ice_atom_count + water_atom_count + guest_atom_count]) + placed_atom_names
        
        # Register with MoleculetypeRegistry
        moleculetype_name = self.registry.register_custom_molecule()
        
        logger.info(
            f"Random placement complete: {n_molecules} custom molecules, "
            f"{len(complete_atom_names)} total atoms (ice+water+custom), moleculetype={moleculetype_name}"
        )
        
        return CustomMoleculeStructure(
            positions=complete_positions,
            atom_names=complete_atom_names,
            cell=modified_structure.cell,
            molecule_index=complete_molecule_index,
            ice_atom_count=ice_atom_count,
            water_atom_count=water_atom_count,
            custom_molecule_atom_count=len(placed_atom_names),
            guest_atom_count=guest_atom_count,
            config=self.config,
            moleculetype_name=moleculetype_name,
            gro_path=self.config.gro_path,
            itp_path=self.config.itp_path,
            residue_name=moleculetype_name,
            custom_molecule_count=n_molecules,
            interface_structure=modified_structure
        )
    
    def place_custom(
        self,
        structure: InterfaceStructure,
        positions: list[tuple[float, float, float]],
        rotations: list[tuple[float, float, float]]
    ) -> CustomMoleculeStructure:
        """Place molecules at user-specified positions with rotations.
        
        No overlap checking (user responsibility).
        
        Args:
            structure: InterfaceStructure (for cell info)
            positions: List of (x, y, z) center-of-mass positions in nm
            rotations: List of (α, β, γ) Euler angles in degrees
            
        Returns:
            CustomMoleculeStructure with placed molecules
        """
        # Validate input
        if len(positions) != len(rotations):
            raise ValueError(
                f"positions and rotations must have same length, "
                f"got {len(positions)} vs {len(rotations)}"
            )
        
        # Center template at origin for rotation
        center = self.template_positions.mean(axis=0)
        centered_template = self.template_positions - center
        
        # Place molecules
        placed_positions = []
        placed_atom_names = []
        molecule_index = []
        current_idx = 0
        
        for com, euler_angles in zip(positions, rotations):
            # Convert Euler angles to rotation matrix
            rot_matrix = self._euler_to_rotation_matrix(*euler_angles)
            
            # Rotate template around origin
            rotated = centered_template @ rot_matrix.T
            
            # Translate to COM position
            placed_mol = rotated + np.array(com)
            
            # Add to result
            placed_positions.append(placed_mol)
            placed_atom_names.extend(self.template_atom_names)
            molecule_index.append((current_idx, current_idx + len(self.template_atom_names)))
            
            current_idx += len(self.template_atom_names)
        
        # Get interface structure info
        ice_atom_count = getattr(structure, 'ice_atom_count', 0)
        water_atom_count = getattr(structure, 'water_atom_count', 0)
        guest_atom_count = getattr(structure, 'guest_atom_count', 0)
        
        # CRITICAL: Remove water molecules that overlap with placed custom molecules
        if placed_positions:
            all_custom_positions = np.vstack(placed_positions)
        else:
            all_custom_positions = np.zeros((0, 3))
        
        modified_structure = self._remove_overlapping_water(
            structure,
            all_custom_positions,
            self.config.min_separation
        )
        
        # Get updated counts after water removal
        ice_atom_count = modified_structure.ice_atom_count
        water_atom_count = modified_structure.water_atom_count
        guest_atom_count = modified_structure.guest_atom_count
        
        # Build complete molecule_index
        from quickice.structure_generation.types import MoleculeIndex
        complete_molecule_index = []
        
        # Ice molecules
        if ice_atom_count > 0:
            ice_mol_count = ice_atom_count // 3
            current_idx = 0
            for _ in range(ice_mol_count):
                complete_molecule_index.append(MoleculeIndex(current_idx, current_idx + 4, "ice"))
                current_idx += 4
        
        # Water molecules
        if water_atom_count > 0:
            water_mol_count = water_atom_count // 4
            current_idx = ice_atom_count
            for _ in range(water_mol_count):
                complete_molecule_index.append(MoleculeIndex(current_idx, current_idx + 4, "water"))
                current_idx += 4
        
        # Guest molecules
        if guest_atom_count > 0:
            if hasattr(modified_structure, 'molecule_index'):
                for mol_idx in modified_structure.molecule_index:
                    if mol_idx.mol_type == "guest":
                        complete_molecule_index.append(mol_idx)
        
        # Custom molecules
        current_idx = ice_atom_count + water_atom_count + guest_atom_count
        for start, end in molecule_index:
            complete_molecule_index.append(MoleculeIndex(current_idx, current_idx + (end - start), "custom"))
            current_idx += (end - start)
        
        # Combine positions and atom names from modified structure
        complete_positions = np.vstack([
            modified_structure.positions[:ice_atom_count + water_atom_count + guest_atom_count],
            np.vstack(placed_positions)
        ])
        
        complete_atom_names = list(modified_structure.atom_names[:ice_atom_count + water_atom_count + guest_atom_count]) + placed_atom_names
        
        # Register with MoleculetypeRegistry
        moleculetype_name = self.registry.register_custom_molecule()
        
        n_molecules = len(positions)
        
        logger.info(
            f"Custom placement complete: {n_molecules} custom molecules, "
            f"{len(complete_atom_names)} total atoms (ice+water+custom), moleculetype={moleculetype_name}"
        )
        
        return CustomMoleculeStructure(
            positions=complete_positions,
            atom_names=complete_atom_names,
            cell=modified_structure.cell,
            molecule_index=complete_molecule_index,
            ice_atom_count=ice_atom_count,
            water_atom_count=water_atom_count,
            custom_molecule_atom_count=len(placed_atom_names),
            guest_atom_count=guest_atom_count,
            config=self.config,
            moleculetype_name=moleculetype_name,
            gro_path=self.config.gro_path,
            itp_path=self.config.itp_path,
            residue_name=moleculetype_name,
            custom_molecule_count=n_molecules,
            interface_structure=modified_structure
        )
