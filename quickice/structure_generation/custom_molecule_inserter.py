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
        
        Reuses exact pattern from SoluteInserter._build_existing_atoms_tree().
        
        Args:
            structure: InterfaceStructure with positions and atom_names
            
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
        
        # Add ice atoms
        if ice_atom_count > 0:
            for i in range(ice_atom_count):
                atom_name = structure.atom_names[i] if i < len(structure.atom_names) else ""
                if atom_name != "MW":  # Exclude virtual sites
                    existing_positions.append(structure.positions[i])
        
        # Add water atoms
        if water_atom_count > 0:
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
        
        # Register with MoleculetypeRegistry
        moleculetype_name = self.registry.register_custom_molecule()
        
        # Combine all placed molecules
        all_positions = np.vstack(placed_positions)
        
        logger.info(
            f"Random placement complete: {n_molecules} molecules, "
            f"{len(placed_atom_names)} total atoms, moleculetype={moleculetype_name}"
        )
        
        return CustomMoleculeStructure(
            positions=all_positions,
            atom_names=placed_atom_names,
            cell=structure.cell,
            molecule_index=molecule_index,
            config=self.config,
            moleculetype_name=moleculetype_name,
            gro_path=self.config.gro_path,
            itp_path=self.config.itp_path,
            residue_name=moleculetype_name,  # Use moleculetype as residue name
            custom_molecule_count=n_molecules
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
        
        # Register with MoleculetypeRegistry
        moleculetype_name = self.registry.register_custom_molecule()
        
        # Combine all placed molecules
        all_positions = np.vstack(placed_positions)
        
        n_molecules = len(positions)
        
        logger.info(
            f"Custom placement complete: {n_molecules} molecules, "
            f"{len(placed_atom_names)} total atoms, moleculetype={moleculetype_name}"
        )
        
        return CustomMoleculeStructure(
            positions=all_positions,
            atom_names=placed_atom_names,
            cell=structure.cell,
            molecule_index=molecule_index,
            config=self.config,
            moleculetype_name=moleculetype_name,
            gro_path=self.config.gro_path,
            itp_path=self.config.itp_path,
            residue_name=moleculetype_name,  # Use moleculetype as residue name
            custom_molecule_count=n_molecules
        )
