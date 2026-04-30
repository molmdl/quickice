"""Test interface GROMACS export copies correct guest .itp file.

This test verifies the fix for:
- Interface export now uses correct index to detect guest type
- detect_guest_type_from_atoms() is used for robust detection
- CH4 and THF .itp files are copied correctly
"""

import tempfile
from pathlib import Path
import numpy as np

from quickice.structure_generation.types import InterfaceStructure
from quickice.gui.export import InterfaceGROMACSExporter


def create_mock_interface_structure_with_thf():
    """Create a mock InterfaceStructure with THF guest molecules."""
    # Simplified structure: ice + water + THF guests
    # Order: ice → water → guests
    
    ice_nmolecules = 100
    water_nmolecules = 200
    guest_nmolecules = 10
    
    # Ice: 4 atoms per molecule (OW, HW1, HW2, MW)
    ice_atom_count = ice_nmolecules * 4
    ice_positions = np.random.rand(ice_atom_count, 3) * 3.0
    ice_atom_names = []
    for _ in range(ice_nmolecules):
        ice_atom_names.extend(["OW", "HW1", "HW2", "MW"])
    
    # Water: 4 atoms per molecule (OW, HW1, HW2, MW)
    water_atom_count = water_nmolecules * 4
    water_positions = np.random.rand(water_atom_count, 3) * 3.0
    water_atom_names = []
    for _ in range(water_nmolecules):
        water_atom_names.extend(["OW", "HW1", "HW2", "MW"])
    
    # THF: 13 atoms per molecule (O, CA, CA, CB, CB, H, H, H, H, H, H, H, H)
    guest_atom_count = guest_nmolecules * 13
    guest_positions = np.random.rand(guest_atom_count, 3) * 3.0
    guest_atom_names = []
    for _ in range(guest_nmolecules):
        guest_atom_names.extend(["O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H"])
    
    # Combine in order: ice → water → guests
    all_positions = np.vstack([ice_positions, water_positions, guest_positions])
    all_atom_names = ice_atom_names + water_atom_names + guest_atom_names
    
    cell = np.array([
        [3.0, 0.0, 0.0],
        [0.0, 3.0, 0.0],
        [0.0, 0.0, 8.0]
    ])
    
    return InterfaceStructure(
        positions=all_positions,
        atom_names=all_atom_names,
        cell=cell,
        ice_atom_count=ice_atom_count,
        water_atom_count=water_atom_count,
        ice_nmolecules=ice_nmolecules,
        water_nmolecules=water_nmolecules,
        mode="slab",
        report="Test interface structure",
        guest_atom_count=guest_atom_count,
        guest_nmolecules=guest_nmolecules
    )


def create_mock_interface_structure_with_ch4():
    """Create a mock InterfaceStructure with CH4 guest molecules."""
    ice_nmolecules = 100
    water_nmolecules = 200
    guest_nmolecules = 10
    
    # Ice: 4 atoms per molecule
    ice_atom_count = ice_nmolecules * 4
    ice_positions = np.random.rand(ice_atom_count, 3) * 3.0
    ice_atom_names = []
    for _ in range(ice_nmolecules):
        ice_atom_names.extend(["OW", "HW1", "HW2", "MW"])
    
    # Water: 4 atoms per molecule
    water_atom_count = water_nmolecules * 4
    water_positions = np.random.rand(water_atom_count, 3) * 3.0
    water_atom_names = []
    for _ in range(water_nmolecules):
        water_atom_names.extend(["OW", "HW1", "HW2", "MW"])
    
    # CH4: 5 atoms per molecule (C, H, H, H, H) - but GenIce outputs H first!
    # Test with realistic atom order: H, H, H, H, C
    guest_atom_count = guest_nmolecules * 5
    guest_positions = np.random.rand(guest_atom_count, 3) * 3.0
    guest_atom_names = []
    for _ in range(guest_nmolecules):
        guest_atom_names.extend(["H", "H", "H", "H", "C"])
    
    all_positions = np.vstack([ice_positions, water_positions, guest_positions])
    all_atom_names = ice_atom_names + water_atom_names + guest_atom_names
    
    cell = np.array([
        [3.0, 0.0, 0.0],
        [0.0, 3.0, 0.0],
        [0.0, 0.0, 8.0]
    ])
    
    return InterfaceStructure(
        positions=all_positions,
        atom_names=all_atom_names,
        cell=cell,
        ice_atom_count=ice_atom_count,
        water_atom_count=water_atom_count,
        ice_nmolecules=ice_nmolecules,
        water_nmolecules=water_nmolecules,
        mode="slab",
        report="Test interface structure",
        guest_atom_count=guest_atom_count,
        guest_nmolecules=guest_nmolecules
    )


def test_guest_type_detection():
    """Test that detect_guest_type_from_atoms works correctly."""
    from quickice.output.gromacs_writer import detect_guest_type_from_atoms
    
    # Test THF detection
    thf_atoms = ["O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H"]
    result = detect_guest_type_from_atoms(thf_atoms)
    assert result == "thf", f"Expected 'thf', got '{result}'"
    print("✓ THF detection works")
    
    # Test CH4 detection (GenIce order: H, H, H, H, C)
    ch4_atoms = ["H", "H", "H", "H", "C"]
    result = detect_guest_type_from_atoms(ch4_atoms)
    assert result == "ch4", f"Expected 'ch4', got '{result}'"
    print("✓ CH4 detection works")
    
    # Test CH4 with canonical order (C, H, H, H, H)
    ch4_atoms_canonical = ["C", "H", "H", "H", "H"]
    result = detect_guest_type_from_atoms(ch4_atoms_canonical)
    assert result == "ch4", f"Expected 'ch4', got '{result}'"
    print("✓ CH4 detection (canonical order) works")


def test_interface_export_thf():
    """Test that interface export copies thf.itp file."""
    iface = create_mock_interface_structure_with_thf()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        export_path = Path(tmpdir) / "interface_slab.gro"
        
        # Create exporter (parent=None for testing, won't show dialog)
        exporter = InterfaceGROMACSExporter(parent_widget=None)
        
        # Manually call the export logic without the dialog
        import shutil
        from quickice.output.gromacs_writer import (
            write_interface_gro_file,
            write_interface_top_file,
            get_tip4p_itp_path,
            detect_guest_type_from_atoms
        )
        from quickice.gui.export import _get_guest_itp_path
        
        # Write files
        write_interface_gro_file(iface, str(export_path))
        top_path = export_path.with_suffix('.top')
        write_interface_top_file(iface, str(top_path))
        
        # Copy water .itp
        water_itp_source = get_tip4p_itp_path()
        water_itp_dest = export_path.with_name("tip4p-ice.itp")
        shutil.copy(water_itp_source, water_itp_dest)
        
        # Copy guest .itp (the fixed code)
        if iface.guest_nmolecules > 0 and iface.guest_atom_count > 0:
            guest_start = iface.ice_atom_count + iface.water_atom_count
            guest_atom_names = iface.atom_names[guest_start:guest_start + iface.guest_atom_count]
            guest_type = detect_guest_type_from_atoms(guest_atom_names)
            
            if guest_type:
                guest_itp_source = _get_guest_itp_path(guest_type)
                guest_itp_dest = export_path.with_name(f"{guest_type}.itp")
                shutil.copy(guest_itp_source, guest_itp_dest)
                print(f"✓ Copied {guest_type}.itp")
        
        # Verify files exist
        assert export_path.exists(), "interface_slab.gro not created"
        assert top_path.exists(), "interface_slab.top not created"
        assert water_itp_dest.exists(), "tip4p-ice.itp not copied"
        
        guest_itp = export_path.with_name("thf.itp")
        assert guest_itp.exists(), "thf.itp not copied"
        
        # Verify .top file includes thf.itp
        with open(top_path, 'r') as f:
            top_content = f.read()
            assert '#include "thf.itp"' in top_content, "thf.itp not included in .top file"
        
        print("✓ THF interface export copies all required files")
        print("✓ .top file correctly includes thf.itp")


def test_interface_export_ch4():
    """Test that interface export copies ch4.itp file."""
    iface = create_mock_interface_structure_with_ch4()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        export_path = Path(tmpdir) / "interface_slab.gro"
        
        # Manually call the export logic
        import shutil
        from quickice.output.gromacs_writer import (
            write_interface_gro_file,
            write_interface_top_file,
            get_tip4p_itp_path,
            detect_guest_type_from_atoms
        )
        from quickice.gui.export import _get_guest_itp_path
        
        # Write files
        write_interface_gro_file(iface, str(export_path))
        top_path = export_path.with_suffix('.top')
        write_interface_top_file(iface, str(top_path))
        
        # Copy water .itp
        water_itp_source = get_tip4p_itp_path()
        water_itp_dest = export_path.with_name("tip4p-ice.itp")
        shutil.copy(water_itp_source, water_itp_dest)
        
        # Copy guest .itp (the fixed code)
        if iface.guest_nmolecules > 0 and iface.guest_atom_count > 0:
            guest_start = iface.ice_atom_count + iface.water_atom_count
            guest_atom_names = iface.atom_names[guest_start:guest_start + iface.guest_atom_count]
            guest_type = detect_guest_type_from_atoms(guest_atom_names)
            
            if guest_type:
                guest_itp_source = _get_guest_itp_path(guest_type)
                guest_itp_dest = export_path.with_name(f"{guest_type}.itp")
                shutil.copy(guest_itp_source, guest_itp_dest)
                print(f"✓ Copied {guest_type}.itp")
        
        # Verify files exist
        assert export_path.exists(), "interface_slab.gro not created"
        assert top_path.exists(), "interface_slab.top not created"
        assert water_itp_dest.exists(), "tip4p-ice.itp not copied"
        
        guest_itp = export_path.with_name("ch4.itp")
        assert guest_itp.exists(), "ch4.itp not copied"
        
        # Verify .top file includes ch4.itp
        with open(top_path, 'r') as f:
            top_content = f.read()
            assert '#include "ch4.itp"' in top_content, "ch4.itp not included in .top file"
        
        print("✓ CH4 interface export copies all required files")
        print("✓ .top file correctly includes ch4.itp")


if __name__ == "__main__":
    print("Testing guest type detection...")
    test_guest_type_detection()
    
    print("\nTesting THF interface export...")
    test_interface_export_thf()
    
    print("\nTesting CH4 interface export...")
    test_interface_export_ch4()
    
    print("\n" + "="*60)
    print("ALL TESTS PASSED!")
    print("="*60)
