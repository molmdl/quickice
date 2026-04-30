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
    MoleculeIndex,
    InterfaceStructure,  # for compatibility with interface generation
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

    def _build_molecule_index_from_structure(self, structure) -> list[MoleculeIndex]:
        """Build molecule_index from structure metadata (InterfaceStructure compatibility).

        InterfaceStructure has ice_atom_count, guest_atom_count, water_atom_count attributes
        that mark the exact boundaries in the positions array. This method uses those
        counts to build molecule_index entries.

        Order in positions array:
        - Ice atoms: 0 to ice_atom_count-1
        - Guest atoms: ice_atom_count to ice_atom_count + guest_atom_count - 1
        - Water atoms: ice_atom_count + guest_atom_count onward

        Args:
            structure: Structure with ice_atom_count, guest_atom_count, water_atom_count attributes

        Returns:
            List of MoleculeIndex entries for ice, guest, and water molecules, or None if not possible
        """
        # Check if this is an InterfaceStructure (has ice_atom_count)
        if not hasattr(structure, 'ice_atom_count'):
            return None

        ice_mols = getattr(structure, 'ice_nmolecules', 0)
        water_mols = getattr(structure, 'water_nmolecules', 0)
        guest_mols = getattr(structure, 'guest_nmolecules', 0)
        ice_atom_count = getattr(structure, 'ice_atom_count', 0)
        guest_atom_count = getattr(structure, 'guest_atom_count', 0)
        water_atom_count = getattr(structure, 'water_atom_count', 0)

        if ice_mols == 0 and water_mols == 0 and guest_mols == 0:
            return None

        mol_index = []
        current_idx = 0

        # Add ice molecules
        # Use ice_atom_count to determine where ice region ends
        if ice_mols > 0 and ice_atom_count > 0:
            # Calculate atoms per ice molecule from actual counts
            ice_atoms_per_mol = ice_atom_count // ice_mols if ice_mols > 0 else 4
            for i in range(ice_mols):
                mol_index.append(MoleculeIndex(
                    start_idx=current_idx,
                    count=ice_atoms_per_mol,
                    mol_type="ice"
                ))
                current_idx += ice_atoms_per_mol

        # Add guest molecules
        # Use guest_atom_count to determine guest region size
        if guest_mols > 0 and guest_atom_count > 0:
            # Calculate atoms per guest molecule from actual counts
            guest_atoms_per_mol = guest_atom_count // guest_mols if guest_mols > 0 else 5
            for i in range(guest_mols):
                mol_index.append(MoleculeIndex(
                    start_idx=current_idx,
                    count=guest_atoms_per_mol,
                    mol_type="guest"
                ))
                current_idx += guest_atoms_per_mol

        # Add water molecules
        # Use water_atom_count to determine water region size
        if water_mols > 0 and water_atom_count > 0:
            # Water always uses 4 atoms per molecule (TIP4P)
            water_atoms_per_mol = water_atom_count // water_mols if water_mols > 0 else 4
            for i in range(water_mols):
                mol_index.append(MoleculeIndex(
                    start_idx=current_idx,
                    count=water_atoms_per_mol,
                    mol_type="water"
                ))
                current_idx += water_atoms_per_mol

        return mol_index
    
    def calculate_ion_pairs(
        self,
        concentration_molar: float,
        liquid_volume_nm3: float,
    ) -> int:
        """Calculate number of ion pairs from concentration and volume.
        
        Uses: N = C_M × V_L × NA
        
        Where:
            - C_M = concentration in mol/L (molarity of NaCl salt)
            - V_L = liquid volume in nm³ converted to L (× 1e-24)
            - NA = Avogadro's number
        
        Note: 1 M NaCl = 1 mol NaCl per liter = produces 2 mol ions (Na+ + Cl-)
        The factor of 2 is handled automatically when inserting alternating ions.
        
        Args:
            concentration_molar: NaCl concentration in mol/L (M)
            liquid_volume_nm3: Liquid region volume in nm³
            
        Returns:
            Number of NaCl formula units (each becomes 1 Na+ + 1 Cl- ion pair)
        """
        # Convert nm³ to L: 1 nm³ = 1e-24 L
        volume_liters = liquid_volume_nm3 * 1e-24
        
        # Calculate number of NaCl formula units from molarity
        # C_M (mol/L) × V (L) = moles of NaCl
        # moles × NA = number of NaCl formula units
        n_formula_units = concentration_molar * volume_liters * AVOGADRO
        
        # Return formula units (each will be inserted as a Na+/Cl- ion pair)
        return int(round(n_formula_units))
    
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
        # Handle structures without molecule_index (e.g., InterfaceStructure)
        # by building one from available metadata
        if not structure.molecule_index:
            # Try to build molecule_index from metadata
            # This handles InterfaceStructure which has ice_nmolecules and water_nmolecules but no molecule_index
            mol_index = self._build_molecule_index_from_structure(structure)
            if mol_index is None:
                # No water molecules found - return zero ions
                return IonStructure(
                    positions=structure.positions,
                    atom_names=structure.atom_names,
                    cell=structure.cell,
                    molecule_index=[],
                    na_count=0,
                    cl_count=0,
                    report=f"Ion insertion: no water molecules found in structure\n",
                )
            structure.molecule_index = mol_index

        if ion_pairs <= 0:
            # Return a properly typed IonStructure with zero ions
            return IonStructure(
                positions=structure.positions,
                atom_names=structure.atom_names,
                cell=structure.cell,
                molecule_index=structure.molecule_index if hasattr(structure, 'molecule_index') else [],
                na_count=0,
                cl_count=0,
                report=f"Ion insertion: requested 0 ion pairs (concentration too low or volume too small)\n",
            )

        # Extract water molecules from molecule_index
        water_mols = [m for m in structure.molecule_index if m.mol_type == "water"]

        if len(water_mols) < ion_pairs * 2:
            # Not enough water molecules
            ion_pairs = len(water_mols) // 2
            if ion_pairs == 0:
                # Return a properly typed IonStructure with zero ions
                guest_nmolecules = getattr(structure, 'guest_nmolecules', 0)
                guest_atom_count = getattr(structure, 'guest_atom_count', 0)
                return IonStructure(
                    positions=structure.positions,
                    atom_names=structure.atom_names,
                    cell=structure.cell,
                    molecule_index=structure.molecule_index if hasattr(structure, 'molecule_index') else [],
                    na_count=0,
                    cl_count=0,
                    report=f"Ion insertion: not enough water molecules for ion placement\n",
                    guest_nmolecules=guest_nmolecules,
                    guest_atom_count=guest_atom_count,
                )
        
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
        # Check against BOTH ice AND guest molecules to prevent ions from penetrating
        # into the hydrate crystallite region (cages contain guest molecules)
        remain_positions = []
        for mol in structure.molecule_index:
            # Only keep ice and guest (not water being replaced OR retained)
            if mol.mol_type in ("ice", "guest"):
                start = mol.start_idx
                end = start + mol.count
                remain_positions.append(structure.positions[start:end])

        if remain_positions:
            remain_positions = np.vstack(remain_positions)
            ice_tree = cKDTree(remain_positions)
        else:
            # No ice molecules - no overlap to check against ice
            ice_tree = None
        
        # Now add ions alternating Na+, Cl- with overlap checking
        na_count = 0
        cl_count = 0
        ion_positions = []  # Track placed ion positions
        
        for i, water_idx in enumerate(selected):
            water_mol = water_mols[water_idx]
            start = water_mol.start_idx
            
            # Get water position (use oxygen for placement)
            water_pos = structure.positions[start]  # First atom is O
            
            # Check minimum distance to ice AND guest molecules (both define the hydrate crystallite region)
            if ice_tree is not None:
                min_dist = ice_tree.query(water_pos, k=1)[0]
                if min_dist < MIN_SEPARATION:
                    # Too close to hydrate - skip this ion
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
        
        # Ensure charge neutrality: na_count must equal cl_count
        # Remove excess ions from the end (prefer removing from end to minimize disruption)
        # 
        # IMPORTANT: new_atom_names is a FLAT list of atoms, while new_molecule_index
        # and new_positions are lists of MOLECULES. We cannot use molecule index (idx)
        # to pop from new_atom_names - we must use the molecule's start_idx and count
        # to remove the correct atoms.
        while na_count > cl_count:
            # Find and remove the last NA from new_molecule_index
            for idx in range(len(new_molecule_index) - 1, -1, -1):
                if new_molecule_index[idx].mol_type == "na":
                    # Remove this NA using its start_idx and count
                    mol = new_molecule_index.pop(idx)
                    # Remove atoms from flat atom_names list using molecule's start_idx
                    del new_atom_names[mol.start_idx:mol.start_idx + mol.count]
                    new_positions.pop(idx)
                    na_count -= 1
                    break
        
        while cl_count > na_count:
            # Find and remove the last CL from new_molecule_index
            for idx in range(len(new_molecule_index) - 1, -1, -1):
                if new_molecule_index[idx].mol_type == "cl":
                    # Remove this CL using its start_idx and count
                    mol = new_molecule_index.pop(idx)
                    # Remove atoms from flat atom_names list using molecule's start_idx
                    del new_atom_names[mol.start_idx:mol.start_idx + mol.count]
                    new_positions.pop(idx)
                    cl_count -= 1
                    break
        
        # Regenerate start_idx values for molecule_index
        # (they may be wrong after removing entries)
        current_idx = 0
        for mol in new_molecule_index:
            mol.start_idx = current_idx
            current_idx += mol.count
        
        # Generate report
        requested_pairs = ion_pairs
        actual_pairs = (na_count + cl_count) // 2
        report = (
            f"Ion insertion: requested {requested_pairs * 2} water molecules, "
            f"placed {na_count} Na+ and {cl_count} Cl- ions\n"
        )
        if actual_pairs < requested_pairs:
            report += f"Warning: could not place {requested_pairs - actual_pairs} pairs (too close to existing atoms)\n"
        if na_count != cl_count:
            report += f"Warning: removed excess ions to maintain charge neutrality\n"
        
        # Concatenate all positions
        if new_positions:
            combined = np.vstack(new_positions)
        else:
            combined = np.zeros((0, 3))
        
        # Preserve guest molecule information from input structure
        guest_nmolecules = getattr(structure, 'guest_nmolecules',0)
        guest_atom_count = getattr(structure, 'guest_atom_count',0)
        
        return IonStructure(
            positions=combined,
            atom_names=new_atom_names,
            cell=structure.cell,
            molecule_index=new_molecule_index,
            na_count=na_count,
            cl_count=cl_count,
            report=report,
            guest_nmolecules=guest_nmolecules,
            guest_atom_count=guest_atom_count,
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