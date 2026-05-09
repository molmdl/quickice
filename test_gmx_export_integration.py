#!/usr/bin/env python3
"""Integration test for GMX export fixes - verifies actual output files."""

import sys
from pathlib import Path
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from quickice.output.gromacs_writer import (
    comment_out_atomtypes_in_itp,
    parse_itp_atomtypes,
)


def test_etoh_itp_commenting():
    """Test that etoh.itp gets atomtypes commented out during export."""
    print("\n" + "="*60)
    print("Testing Issue 1: etoh.itp atomtypes commenting")
    print("="*60)
    
    etoh_path = Path("tmp/test/etoh.itp")
    if not etoh_path.exists():
        print("⚠ Skipping - etoh.itp not found")
        return
    
    # Simulate the export process
    print(f"\n1. Reading {etoh_path}...")
    itp_content = etoh_path.read_text()
    
    print("2. Commenting out atomtypes...")
    modified_content = comment_out_atomtypes_in_itp(itp_content)
    
    # Save to test output
    test_output = Path("tmp/test/etoh_fixed.itp")
    test_output.write_text(modified_content)
    print(f"3. Saved modified ITP to {test_output}")
    
    # Verify the changes
    lines = modified_content.split('\n')
    
    # Check for comment header
    has_header = any('; Modified for QuickIce' in line for line in lines)
    print(f"\n4. Checking comment header: {'✓ FOUND' if has_header else '✗ MISSING'}")
    
    # Check that atomtypes section is commented
    atomtypes_commented = False
    for i, line in enumerate(lines):
        if '; [ atomtypes ]' in line:
            atomtypes_commented = True
            print(f"5. Atomtypes header commented: ✓ (line {i+1})")
            # Check next few lines are also commented
            for j in range(i+1, min(i+10, len(lines))):
                if lines[j].strip() and not lines[j].strip().startswith(';'):
                    if '[ moleculetype ]' in lines[j]:
                        break
                    print(f"   ✗ Line {j+1} not commented: {lines[j][:50]}")
                    atomtypes_commented = False
                    break
            break
    
    # Check that moleculetype is NOT commented
    moltype_preserved = '[ moleculetype ]' in modified_content and '; [ moleculetype ]' not in modified_content
    print(f"6. Moleculetype section preserved: {'✓ YES' if moltype_preserved else '✗ NO'}")
    
    if has_header and atomtypes_commented and moltype_preserved:
        print("\n✅ Issue 1 FIXED: etoh.itp atomtypes properly commented")
    else:
        print("\n❌ Issue 1 FAILED")
    
    return test_output


def test_top_atomtypes():
    """Test that main .top includes custom molecule atomtypes."""
    print("\n" + "="*60)
    print("Testing Issue 2: Main .top includes custom atomtypes")
    print("="*60)
    
    top_path = Path("tmp/test/ions_32na_32cl_with_7ch4.top")
    etoh_path = Path("tmp/test/etoh.itp")
    ch4_path = Path("tmp/test/ch4_liquid.itp")
    
    if not top_path.exists():
        print("⚠ Skipping - .top file not found")
        return
    
    print(f"\n1. Checking {top_path}...")
    top_content = top_path.read_text()
    
    # Parse atomtypes from custom ITP
    custom_atomtypes = []
    if etoh_path.exists():
        print(f"2. Parsing atomtypes from {etoh_path}...")
        etoh_types = parse_itp_atomtypes(etoh_path)
        custom_atomtypes.extend(etoh_types)
        print(f"   Found {len(etoh_types)} atomtypes: {[t[0] for t in etoh_types]}")
    
    if ch4_path.exists():
        print(f"3. Parsing atomtypes from {ch4_path}...")
        ch4_types = parse_itp_atomtypes(ch4_path)
        custom_atomtypes.extend(ch4_types)
        print(f"   Found {len(ch4_types)} atomtypes: {[t[0] for t in ch4_types]}")
    
    # Check which atomtypes are in the .top file
    print(f"\n4. Checking which atomtypes are in main .top...")
    missing_types = []
    found_types = []
    
    for at in custom_atomtypes:
        type_name = at[0]
        if type_name in top_content:
            found_types.append(type_name)
            print(f"   ✓ {type_name} found in .top")
        else:
            missing_types.append(type_name)
            print(f"   ✗ {type_name} MISSING from .top")
    
    if missing_types:
        print(f"\n❌ Issue 2 NOT FIXED: Missing atomtypes: {missing_types}")
        print("\nCurrent .top [atomtypes] section:")
        in_atomtypes = False
        for line in top_content.split('\n'):
            if '[ atomtypes ]' in line.lower():
                in_atomtypes = True
            elif line.strip().startswith('[') and in_atomtypes:
                break
            if in_atomtypes:
                print(f"  {line}")
    else:
        print(f"\n✅ Issue 2 FIXED: All {len(found_types)} custom atomtypes in main .top")


def test_gro_residue_names():
    """Test that GRO file uses 5-character residue names."""
    print("\n" + "="*60)
    print("Testing Issue 3: GRO file residue name length")
    print("="*60)
    
    gro_path = Path("tmp/test/ions_32na_32cl_with_7ch4.gro")
    
    if not gro_path.exists():
        print("⚠ Skipping - .gro file not found")
        return
    
    print(f"\n1. Checking {gro_path} for long residue names...")
    
    # Find lines with long residue names
    lines = gro_path.read_text().split('\n')
    long_residue_lines = []
    
    # Skip header and count lines
    for i, line in enumerate(lines[2:], start=3):  # Skip title and atom count
        if not line.strip() or len(line) < 10:
            continue
        
        # GRO format: resid(5) resname(5) atomname(5) atomid(5) x(8) y(8) z(8)
        # Check if line looks like an atom line
        try:
            # Try to parse - if residue name is too long, coordinates will be pushed
            parts = line.split()
            if len(parts) >= 5:
                # Try to parse coordinates
                try:
                    x = float(parts[-3])
                    y = float(parts[-2])
                    z = float(parts[-1])
                    
                    # Check if residue name in line is > 5 chars
                    # Residue name is positions 5-10 (0-indexed: 5:10)
                    if len(line) > 10:
                        res_name_in_line = line[5:15].strip().split()[0] if len(line) > 15 else ""
                        if len(res_name_in_line) > 5:
                            long_residue_lines.append((i, res_name_in_line, line[:80]))
                except (ValueError, IndexError):
                    continue
        except:
            continue
    
    if long_residue_lines:
        print(f"\n❌ Issue 3 NOT FIXED: Found {len(long_residue_lines)} lines with residue names > 5 chars:")
        for line_num, res_name, line_content in long_residue_lines[:5]:  # Show first 5
            print(f"   Line {line_num}: resname='{res_name}' ({len(res_name)} chars)")
            print(f"      {line_content}")
    else:
        print("\n✅ Issue 3 FIXED: No residue names exceed 5 characters")
        
        # Show a sample CH4_LIQ line
        for i, line in enumerate(lines[2:], start=3):
            if 'CH4' in line or 'CH4_L' in line:
                print(f"\nSample CH4 line (line {i}):")
                print(f"  {line}")
                # Parse to show format
                if len(line) >= 44:
                    res_id = line[0:5]
                    res_name = line[5:10]
                    atom_name = line[10:15]
                    atom_id = line[15:20]
                    x = line[20:28]
                    y = line[28:36]
                    z = line[36:44]
                    print(f"  ResID: '{res_id}' ResName: '{res_name}' Atom: '{atom_name}' AtomID: '{atom_id}'")
                    print(f"  Coords: ({x}, {y}, {z})")
                break


if __name__ == "__main__":
    print("\n" + "="*70)
    print("COMPREHENSIVE TEST FOR GMX EXPORT FIXES")
    print("Testing actual output files")
    print("="*70)
    
    # Test Issue 1
    test_etoh_itp_commenting()
    
    # Test Issue 2
    test_top_atomtypes()
    
    # Test Issue 3
    test_gro_residue_names()
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print("Issues tested:")
    print("  1. etoh.itp atomtypes commenting")
    print("  2. Main .top includes custom atomtypes")  
    print("  3. GRO file residue name length (5 chars max)")
    print("\nNote: Run actual export to generate fixed output files")
    print("="*70 + "\n")
