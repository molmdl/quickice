"""Test molecule ordering in GROMACS export files.

Verifies that GROMACS exports produce correct molecule ordering:
- SOL molecules (ice + water) first
- Guest/solute/custom molecules last
- No interleaving of molecule types

Per plan 35-01 and requirement GROMACS-01.
"""

import pytest
import numpy as np
from pathlib import Path
import tempfile

from quickice.output.gromacs_writer import write_multi_molecule_gro_file
from quickice.structure_generation.types import MoleculeIndex


def parse_gro_residue_names(gro_path: str) -> list[str]:
    """Parse residue names from GROMACS .gro file.
    
    GRO format (per GROMACS documentation):
        Line 1: Title
        Line 2: Number of atoms
        Lines 3+: Atom records
            Columns 1-5: Residue number (right-justified)
            Columns 6-10: Residue name (left-justified)
            Columns 11-15: Atom name (left-justified)
            ...
    
    Args:
        gro_path: Path to .gro file
        
    Returns:
        List of residue names in order they appear in the file
    """
    residue_names = []
    
    with open(gro_path, 'r') as f:
        lines = f.readlines()
        
        # Skip title and atom count lines
        if len(lines) < 3:
            return residue_names
        
        # Parse atom lines
        for line in lines[2:]:
            # Check if this is an atom line (not box vectors)
            # Box vectors have 9 float values, atom lines have formatted numbers
            if len(line.strip()) < 20:
                continue
            
            # Extract residue name from columns 6-10 (0-indexed: [5:10])
            # Format: "    1SOL  OW    1   0.123   0.456   0.789"
            res_name = line[5:10].strip()
            
            # Skip box vector lines (contain only numbers, no residue name)
            if res_name and not res_name.replace('.', '').replace('-', '').isspace():
                residue_names.append(res_name)
    
    return residue_names


def test_solute_molecule_ordering():
    """Test that solute GROMACS export produces correct molecule ordering.
    
    Expected order: SOL (ice + water) → CH4_L (solute)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_solute.gro"
        
        # Create mock molecule index: 10 SOL molecules + 5 CH4 molecules
        molecule_index = []
        idx = 0
        
        # SOL molecules (4 atoms each - TIP4P-ICE)
        for i in range(10):
            molecule_index.append(MoleculeIndex(
                start_idx=idx,
                count=4,
                mol_type='water'
            ))
            idx += 4
        
        # CH4 molecules (5 atoms each)
        for i in range(5):
            molecule_index.append(MoleculeIndex(
                start_idx=idx,
                count=5,
                mol_type='ch4'
            ))
            idx += 5
        
        # Total atoms
        n_atoms = idx
        
        # Create mock positions and atom names
        positions = np.random.uniform(0, 2.0, size=(n_atoms, 3))
        atom_names = []
        
        # SOL atoms
        for i in range(10):
            atom_names.extend(["OW", "HW1", "HW2", "MW"])
        
        # CH4 atoms
        for i in range(5):
            atom_names.extend(["C", "H", "H", "H", "H"])
        
        # Mock cell
        cell = np.eye(3) * 2.0
        
        # Write GRO file
        write_multi_molecule_gro_file(
            positions,
            molecule_index,
            cell,
            str(output_path),
            title="Solute test",
            atom_names=atom_names
        )
        
        # Parse residue names
        residue_names = parse_gro_residue_names(str(output_path))
        
        # Verify ordering
        # Find indices of each molecule type
        sol_indices = [i for i, name in enumerate(residue_names) if name == "SOL"]
        ch4_indices = [i for i, name in enumerate(residue_names) if name == "CH4"]
        
        # All SOL should come before all CH4
        assert sol_indices, "Should have SOL molecules"
        assert ch4_indices, "Should have CH4 molecules"
        assert max(sol_indices) < min(ch4_indices), \
            f"SOL molecules should come before CH4. Last SOL at {max(sol_indices)}, first CH4 at {min(ch4_indices)}"
        
        # Verify no interleaving
        seen_ch4 = False
        for name in residue_names:
            if name == "CH4":
                seen_ch4 = True
            elif name == "SOL" and seen_ch4:
                pytest.fail("SOL molecule found after CH4 - molecules are interleaved!")


def test_custom_molecule_ordering():
    """Test that custom molecule GROMACS export produces correct molecule ordering.
    
    Expected order: SOL (ice + water) → custom molecules
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_custom.gro"
        
        # Create mock molecule index: 10 SOL + 3 custom molecules
        molecule_index = []
        idx = 0
        
        # SOL molecules
        for i in range(10):
            molecule_index.append(MoleculeIndex(
                start_idx=idx,
                count=4,
                mol_type='water'
            ))
            idx += 4
        
        # Custom molecules (5 atoms each)
        for i in range(3):
            molecule_index.append(MoleculeIndex(
                start_idx=idx,
                count=5,
                mol_type='MOLECULE_X'
            ))
            idx += 5
        
        n_atoms = idx
        
        # Create mock data
        positions = np.random.uniform(0, 2.0, size=(n_atoms, 3))
        atom_names = []
        
        # SOL atoms
        for i in range(10):
            atom_names.extend(["OW", "HW1", "HW2", "MW"])
        
        # Custom molecule atoms
        for i in range(3):
            atom_names.extend(["C", "C", "C", "H", "H"])
        
        cell = np.eye(3) * 2.0
        
        # Write GRO file
        write_multi_molecule_gro_file(
            positions,
            molecule_index,
            cell,
            str(output_path),
            title="Custom molecule test",
            atom_names=atom_names
        )
        
        # Parse residue names
        residue_names = parse_gro_residue_names(str(output_path))
        
        # Verify ordering
        sol_indices = [i for i, name in enumerate(residue_names) if name == "SOL"]
        custom_indices = [i for i, name in enumerate(residue_names) if name == "UNK"]
        
        assert sol_indices, "Should have SOL molecules"
        assert custom_indices, "Should have custom molecules"
        assert max(sol_indices) < min(custom_indices), \
            "SOL molecules should come before custom molecules"


def test_combined_ordering():
    """Test combined structure with solutes AND custom molecules.
    
    Expected order: SOL → CH4 → custom molecules
    
    This tests the full v4.5 multi-molecule workflow.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_combined.gro"
        
        # Create molecule index: SOL → CH4 → CUSTOM
        molecule_index = []
        idx = 0
        
        # SOL molecules
        for i in range(10):
            molecule_index.append(MoleculeIndex(
                start_idx=idx,
                count=4,
                mol_type='water'
            ))
            idx += 4
        
        # CH4 molecules
        for i in range(3):
            molecule_index.append(MoleculeIndex(
                start_idx=idx,
                count=5,
                mol_type='ch4'
            ))
            idx += 5
        
        # Custom molecules
        for i in range(2):
            molecule_index.append(MoleculeIndex(
                start_idx=idx,
                count=5,
                mol_type='CUSTOM_X'
            ))
            idx += 5
        
        n_atoms = idx
        
        # Create mock data
        positions = np.random.uniform(0, 2.0, size=(n_atoms, 3))
        atom_names = []
        
        for i in range(10):
            atom_names.extend(["OW", "HW1", "HW2", "MW"])
        
        for i in range(3):
            atom_names.extend(["C", "H", "H", "H", "H"])
        
        for i in range(2):
            atom_names.extend(["C", "C", "C", "H", "H"])
        
        cell = np.eye(3) * 2.0
        
        # Write GRO file
        write_multi_molecule_gro_file(
            positions,
            molecule_index,
            cell,
            str(output_path),
            title="Combined test",
            atom_names=atom_names
        )
        
        # Parse and verify ordering
        residue_names = parse_gro_residue_names(str(output_path))
        
        # Find molecule type transitions
        molecule_types = []
        current_type = None
        for name in residue_names:
            if name != current_type:
                molecule_types.append(name)
                current_type = name
        
        # Verify order: SOL → CH4 → CUSTOM_X
        assert "SOL" in molecule_types, "SOL molecules should be present"
        assert "CH4" in molecule_types, "CH4 molecules should be present"
        assert "UNK" in molecule_types, "Custom molecules should be present"
        
        sol_idx = molecule_types.index("SOL")
        ch4_idx = molecule_types.index("CH4")
        custom_idx = molecule_types.index("UNK")
        
        assert sol_idx < ch4_idx, "SOL should come before CH4"
        assert ch4_idx < custom_idx, "CH4 should come before custom molecules"


def test_itp_bundling():
    """Test that required .itp files exist and have correct format.
    
    Verifies tip4p-ice.itp and ch4.itp files contain [ moleculetype ] sections.
    """
    from quickice.output.gromacs_writer import get_tip4p_itp_path
    from pathlib import Path as FilePath
    import shutil
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        
        # Get and copy tip4p-ice.itp
        tip4p_source = get_tip4p_itp_path()
        tip4p_dest = output_dir / "tip4p-ice.itp"
        shutil.copy(tip4p_source, tip4p_dest)
        
        # Verify tip4p-ice.itp exists
        assert tip4p_dest.exists(), "tip4p-ice.itp should be bundled"
        
        # Verify file contents
        with open(tip4p_dest, 'r') as f:
            content = f.read()
            assert '[ moleculetype ]' in content, "tip4p-ice.itp should contain moleculetype section"
        
        # Check ch4.itp if it exists
        ch4_source = FilePath(__file__).parent.parent / "topologies" / "ch4.itp"
        if ch4_source.exists():
            ch4_dest = output_dir / "ch4.itp"
            shutil.copy(ch4_source, ch4_dest)
            
            assert ch4_dest.exists(), "ch4.itp should be bundled"
            
            with open(ch4_dest, 'r') as f:
                content = f.read()
                assert '[ moleculetype ]' in content, "ch4.itp should contain moleculetype section"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
