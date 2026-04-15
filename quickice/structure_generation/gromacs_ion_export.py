"""GROMACS ion export module.

Provides functions to generate ion.itp files for Na+ and Cl- ions
with GROMACS standard atom types (Na+/Cl- from Madrid2019).
"""

from pathlib import Path

# Madrid2019 ion parameters
# Masses in g/mol
NA_ATOM_MASS = 22.9898
CL_ATOM_MASS = 35.453

# GROMACS atom type names (Madrid2019)
NA_ATOM_TYPE = "NA"
CL_ATOM_TYPE = "CL"

# Partial charges (Madrid2019 ion parameters)
NA_CHARGE = 0.85
CL_CHARGE = -0.85

# VDW parameters (from Madrid2019_085.top)
# sigma in nm, epsilon in kJ/mol
NA_SIGMA = 0.22173668
CL_SIGMA = 0.46990563
NA_EPSILON = 1.47235577
CL_EPSILON = 0.07692308


def generate_ion_itp(na_count: int, cl_count: int) -> str:
    """Generate ion.itp content with [moleculetype] sections.
    
    Args:
        na_count: Number of Na+ ions (for comment only, doesn't affect itp content)
        cl_count: Number of Cl- ions (for comment only, doesn't affect itp content)
    
    Returns:
        ion.itp file content as string with [moleculetype] and [atoms] sections.
    """
    itp_content = f"""[ moleculetype ]
; Name        nrexcl
NA            1

[ atoms ]
;  nr  type  resi  res  atom  cgnr  charge  mass
    1    NA      1    NA    NA     1      {NA_CHARGE}   {NA_ATOM_MASS}

[ moleculetype ]
; Name        nrexcl
CL            1

[ atoms ]
;  nr  type  resi  res  atom  cgnr  charge  mass
    1    CL      1    CL    CL     1      {CL_CHARGE}   {CL_ATOM_MASS}
"""
    return itp_content


def generate_itp_include_section(na_count: int, cl_count: int) -> str:
    """Generate section for .top file with #include and [molecules].
    
    Args:
        na_count: Number of Na+ ions
        cl_count: Number of Cl- ions
    
    Returns:
        String with #include directive and [molecules] section.
    """
    section = f"""; Include ion parameters
#include "ion.itp"

[ molecules ]
; Compound        nmols
NA              {na_count}
CL              {cl_count}
"""
    return section


def write_ion_itp(output_path: Path | str, na_count: int, cl_count: int) -> None:
    """Write ion.itp file to specified path.
    
    Args:
        output_path: Path to write ion.itp file
        na_count: Number of Na+ ions (for [molecules] section)
        cl_count: Number of Cl- ions (for [molecules] section)
    """
    content = generate_ion_itp(na_count, cl_count)
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)


def add_ion_molecules_to_topology(
    top_path: Path | str,
    na_count: int,
    cl_count: int,
) -> None:
    """Add ion molecule counts to existing .top file.
    
    Reads existing .top file, inserts #include "ion.itp" after last molecule
    definition, and adds ion counts to [molecules] section.
    
    Args:
        top_path: Path to existing .top file
        na_count: Number of Na+ ions
        cl_count: Number of Cl- ions
    """
    top_path = Path(top_path)
    content = top_path.read_text()
    
    lines = content.split('\n')
    
    # Find position to insert #include (after last #include or before [ system ])
    insert_idx = 0
    molecules_idx = None
    
    for i, line in enumerate(lines):
        if line.strip().startswith('#include'):
            insert_idx = i + 1
        if line.strip() == '[ molecules ]':
            molecules_idx = i + 1
    
    # Insert #include if not already present
    if '#include "ion.itp"' not in content:
        lines.insert(insert_idx, '#include "ion.itp"')
        # Adjust molecules_idx since we inserted a line
        if molecules_idx is not None and molecules_idx >= insert_idx:
            molecules_idx += 1
    
    # Add ion counts to [molecules] section
    if molecules_idx is not None:
        # Check if ions already added
        has_na = any(line.strip().startswith('NA ') for line in lines)
        has_cl = any(line.strip().startswith('CL ') for line in lines)
        
        if not has_na:
            lines.insert(molecules_idx, f"NA              {na_count}")
            molecules_idx += 1
        if not has_cl:
            lines.insert(molecules_idx, f"CL              {cl_count}")
    
    top_path.write_text('\n'.join(lines))


def get_ion_molecule_section(na_count: int, cl_count: int) -> str:
    """Get [molecules] section for ions.
    
    Args:
        na_count: Number of Na+ ions
        cl_count: Number of Cl- ions
    
    Returns:
        String with [molecules] section entries for NA and CL.
    """
    section = f"""[ molecules ]
; Compound        nmols
NA              {na_count}
CL              {cl_count}
"""
    return section