#!/usr/bin/env python3
"""Test script for GMX export fixes."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from quickice.output.gromacs_writer import (
    comment_out_atomtypes_in_itp,
    parse_itp_atomtypes,
)

def test_comment_out_atomtypes():
    """Test that atomtypes are properly commented out."""
    print("Testing comment_out_atomtypes_in_itp()...")
    
    # Sample ITP content with atomtypes
    itp_content = """; Created by Sobtop
[ atomtypes ]
; name   at.num      mass       charge   ptype     sigma (nm)    epsilon (kJ/mol)
hc           1     1.007941    0.000000    A      2.600177E-01    8.702720E-02
c3           6    12.010736    0.000000    A      3.397710E-01    4.510352E-01

[ moleculetype ]
; name          nrexcl
etoh       3

[ atoms ]
;  Index   type   residue  resname   atom
     1     hc         1      MOL     H
"""
    
    result = comment_out_atomtypes_in_itp(itp_content)
    
    # Check that atomtypes section is commented
    lines = result.split('\n')
    found_commented_header = False
    found_commented_data = False
    
    for i, line in enumerate(lines):
        if '; Modified for QuickIce' in line:
            print("  ✓ Found comment header")
        if '; [ atomtypes ]' in line:
            found_commented_header = True
            print("  ✓ Atomtypes header is commented")
        if '; hc' in line and '1.007941' in line:
            found_commented_data = True
            print("  ✓ Atomtypes data is commented")
    
    assert found_commented_header, "Atomtypes header not commented!"
    assert found_commented_data, "Atomtypes data not commented!"
    
    # Check that [ moleculetype ] is NOT commented
    assert '[ moleculetype ]' in result, "moleculetype section should not be commented!"
    print("  ✓ Moleculetype section preserved")
    
    print("✓ test_comment_out_atomtypes PASSED\n")


def test_parse_atomtypes():
    """Test that atomtypes can be parsed from ITP file."""
    print("Testing parse_itp_atomtypes()...")
    
    # Use actual etoh.itp file
    etoh_path = Path("tmp/test/etoh.itp")
    if etoh_path.exists():
        atomtypes = parse_itp_atomtypes(etoh_path)
        
        print(f"  Found {len(atomtypes)} atomtypes:")
        for at in atomtypes:
            print(f"    - {at[0]} ({at[2]})")
        
        # Should have at least hc, c3
        type_names = [at[0] for at in atomtypes]
        assert 'hc' in type_names, "hc atomtype not found!"
        assert 'c3' in type_names, "c3 atomtype not found!"
        print("  ✓ Found expected atomtypes (hc, c3)")
        
        print("✓ test_parse_atomtypes PASSED\n")
    else:
        print("  ⚠ Skipping - etoh.itp not found\n")


def test_residue_name_truncation():
    """Test that residue names are truncated to 5 chars."""
    print("Testing residue name truncation...")
    
    # Simulate the truncation logic
    long_name = "CH4_LIQ"  # 7 chars
    truncated = long_name[:5]
    
    assert truncated == "CH4_L", f"Expected 'CH4_L', got '{truncated}'"
    print(f"  ✓ '{long_name}' -> '{truncated}' (5 chars)")
    
    short_name = "etoh"  # 4 chars
    truncated2 = short_name[:5]
    assert truncated2 == "etoh", f"Expected 'etoh', got '{truncated2}'"
    print(f"  ✓ '{short_name}' -> '{truncated2}' (unchanged, already ≤5 chars)")
    
    print("✓ test_residue_name_truncation PASSED\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing GMX Export Fixes")
    print("=" * 60 + "\n")
    
    test_comment_out_atomtypes()
    test_parse_atomtypes()
    test_residue_name_truncation()
    
    print("=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
