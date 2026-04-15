"""Ion insertion module for concentration-based NaCl placement.

This module provides the IonInserter class which calculates ion counts from
concentration and volume, then replaces water molecules in the liquid region
with Na+ and Cl- ions while maintaining charge neutrality.

All coordinates are in nanometers (nm).
"""

import random
from dataclasses import dataclass

import numpy as np
from scipy.spatial import cKDTree

from quickice.structure_generation.types import (
    IonConfig,
    IonStructure,
    IonStructure,
    MoleculeIndex,
)


# Physical constants
AVOGADRO = 6.02214076e23  # mol^-1

# Ion van der Waals radii (in nm)
NA_VDW_RADIUS = 0.190  # 190 pm
CL_VDW_RADIUS = 0.181  # 181 pm

# Ion colors for visualization (RGB)
NA_COLOR = (1.0, 0.84, 0.0)  # Gold
CL_COLOR = (0.56, 0.99, 0.56)  # Lime green

# Minimum separation distance between ions (nm)
MIN_SEPARATION = 0.3  # 3 Å


class IonInserter:
    """Handles concentration-based ion insertion into liquid water regions.
    
    Calculates ion counts from concentration (mol/L) and replaces water molecules
    with alternating Na+ and Cl- ions to maintain charge neutrality.
    
    Attributes:
        config: IonConfig with concentration_molar setting
        random_state: Random state for reproducibility
    """
    
    def __init__(self, config: IonConfig | None = None, seed: int | None = None):
        """Initialize IonInserter.
        
        Args:
            config: IonConfig configuration (optional, creates default if None)
            seed: Random seed for reproducibility (optional)
        """
        self.config = config if config is not None else IonConfig()
        self.rng = random.Random(seed)
    
    def calculate_ion_pairs(
        self,
        concentration_molar: float,
        liquid_volume_nm3: float,
    ) -> int:
        """Calculate number of ion pairs from concentration and volume.
        
        Uses: N_ions = C_M × V_L × NA
        
        Where:
            - C_M = concentration in mol/L
            - V_L = liquid volume in nm³ converted to L (× 1e-24)
            - NA = Avogadro's number
        
        Args:
            concentration_molar: NaCl concentration in mol/L (M)
            liquid_volume_nm3: Liquid region volume in nm³
            
        Returns:
            Number of ion pairs (each pair = 1 Na+ + 1 Cl-)
        """
        # Convert nm³ to L: 1 nm³ = 1e-24 L
        volume_liters = liquid_volume_nm3 * 1e-24
        
        # Calculate total number of ions
        n_ions = concentration_molar * volume_liters * AVOGADRO
        
        # Return ion pairs (round to nearest int)
        return int(round(n_ions / 2))
    
    def replace_water_with_ions(
        self,
        structure: IonStructure,
        ion_pairs: int,
    ) -> IonStructure:
        """Replace water molecules with ions.
        
        Takes an IonStructure and replaces specified number of water molecules
        with Na+ and Cl- ions alternatingly for charge neutrality.
        
        Args:
            structure: Input structure with water molecules
            ion_pairs: Number of ion pairs to insert
            
        Returns:
            New IonStructure with replaced ions
        """
        if ion_pairs <= 0:
            return structure
        
        # Extract water molecules from molecule_index
        water_mols = [m for m in structure.molecule_index if m.mol_type == "water"]
        
        if len(water_mols) < ion_pairs * 2:
            # Not enough water molecules
            ion_pairs = len(water_mols) // 2
            if ion_pairs == 0:
                return structure
        
        # Randomly select water molecules to replace
        indices = list(range(len(water_mols)))
        self.rng.shuffle(indices)
        selected = indices[: ion_pairs * 2]
        
        # Build new positions and atom_names
        new_positions = []
        new_atom_names = []
        new_molecule_index = []
        
        # Track which water molecule start_idx values are being replaced
        replaced_starts = set(water_mols[i].start_idx for i in selected)
        
        # First, add all non-water molecules and non-replaced water molecules
        current_idx = 0
        for mol in structure.molecule_index:
            if mol.mol_type != "water" or mol.start_idx not in replaced_starts:
                # Keep this molecule
                start = mol.start_idx
                end = start + mol.count
                mol_positions = structure.positions[start:end]
                new_positions.append(mol_positions)
                new_atom_names.extend(structure.atom_names[start:end])
                
                new_molecule_index.append(MoleculeIndex(
                    start_idx=current_idx,
                    count=mol.count,
                    mol_type=mol.mol_type,
                ))
                current_idx += mol.count
        
        # Build array of positions for molecules that will remain (not being replaced)
        remain_positions = []
        for mol in structure.molecule_index:
            if mol.mol_type != "water" or mol.start_idx not in replaced_starts:
                # Keep this molecule - include its atoms
                start = mol.start_idx
                end = start + mol.count
                remain_positions.append(structure.positions[start:end])
        
        if remain_positions:
            remain_positions = np.vstack(remain_positions)
            tree = cKDTree(remain_positions)
        else:
            # No other molecules - no overlap to check
            tree = None
        
        # Now add ions alternating Na+, Cl- with overlap checking
        na_count = 0
        cl_count = 0
        ion_positions = []  # Track placed ion positions
        
        for i, water_idx in enumerate(selected):
            water_mol = water_mols[water_idx]
            start = water_mol.start_idx
            
            # Get water position (use oxygen for placement)
            water_pos = structure.positions[start]  # First atom is O
            
            # Check minimum distance to existing atoms (water not being replaced)
            if tree is not None:
                min_dist = tree.query(water_pos, k=1)[0]
                if min_dist < MIN_SEPARATION:
                    # Too close - skip this ion
                    continue
            
            # Also check against previously placed ions
            if ion_positions:
                ion_tree = cKDTree(np.array(ion_positions))
                min_ion_dist = ion_tree.query(water_pos, k=1)[0]
                if min_ion_dist < MIN_SEPARATION:
                    # Too close to other ions - skip
                    continue
            
            # Valid position - add ion
            ion_positions.append(water_pos)
            
            if i % 2 == 0:
                # Add Na+
                new_positions.append(water_pos.reshape(1, 3))
                new_atom_names.append("NA")
                new_molecule_index.append(MoleculeIndex(
                    start_idx=current_idx,
                    count=1,
                    mol_type="na",
                ))
                current_idx += 1
                na_count += 1
            else:
                # Add Cl-
                new_positions.append(water_pos.reshape(1, 3))
                new_atom_names.append("CL")
                new_molecule_index.append(MoleculeIndex(
                    start_idx=current_idx,
                    count=1,
                    mol_type="cl",
                ))
                current_idx += 1
                cl_count += 1
        
        # Generate report
        requested_pairs = ion_pairs
        actual_pairs = (na_count + cl_count) // 2
        report = (
            f"Ion insertion: requested {requested_pairs * 2} water molecules, "
            f"placed {na_count} Na+ and {cl_count} Cl- ions\n"
        )
        if actual_pairs < requested_pairs:
            report += f"Warning: could not place {requested_pairs - actual_pairs} pairs (too close to existing atoms)\n"
        
        # Concatenate all positions
        if new_positions:
            combined = np.vstack(new_positions)
        else:
            combined = np.zeros((0, 3))
        
        return IonStructure(
            positions=combined,
            atom_names=new_atom_names,
            cell=structure.cell,
            molecule_index=new_molecule_index,
            na_count=na_count,
            cl_count=cl_count,
            report=report,
        )


def insert_ions(
    structure: IonStructure,
    concentration_molar: float,
    liquid_volume_nm3: float | None = None,
    seed: int | None = None,
) -> IonStructure:
    """Convenience function to insert ions into a structure.
    
    Args:
        structure: Input IonStructure with water molecules
        concentration_molar: NaCl concentration in mol/L
        liquid_volume_nm3: Liquid volume in nm³ (optional, estimates from structure if None)
        seed: Random seed (optional)
        
    Returns:
        New IonStructure with ions inserted
    """
    config = IonConfig(concentration_molar=concentration_molar)
    inserter = IonInserter(config=config, seed=seed)
    
    # Calculate ion pairs
    if liquid_volume_nm3 is None:
        # Estimate volume from cell and positions
        cell = structure.cell
        volume = np.abs(np.linalg.det(cell))
        liquid_volume_nm3 = volume
    else:
        liquid_volume_nm3 = liquid_volume_nm3
    
    ion_pairs = inserter.calculate_ion_pairs(concentration_molar, liquid_volume_nm3)
    
    return inserter.replace_water_with_ions(structure, ion_pairs)