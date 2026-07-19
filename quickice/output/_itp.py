"""ITP parsing, transformation, and GRO residue-name validation helpers.

Extracted from ``gromacs_writer.py`` (Phase 48.1, Wave 1). All function bodies
are byte-identical to the pre-refactor source — only the file path changed.

``validate_gro_residue_name`` lives here (not in ``_shared.py``) because its
primary caller ``transform_guest_itp`` is also in this module. The plan's
note placing it directly in ``_shared.py`` would create a circular import
(``_shared`` → ``_itp`` → ``_shared``); co-locating it with ``transform_guest_itp``
preserves byte-identical function bodies while breaking the cycle. ``_shared``
re-exports it from here.
"""

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def validate_gro_residue_name(res_name: str, context: str = "") -> None:
    """Validate that a GRO residue name fits in the 5-char fixed-width format.
    
    GRO format uses `%<5s` for residue names, which silently overflows if the
    name exceeds 5 characters, corrupting the fixed-width column alignment.
    This validation catches the problem at write time with a clear error.
    
    Args:
        res_name: Residue name to validate
        context: Optional context string for error message (e.g., "custom molecule 'ETHanol'")
        
    Raises:
        ValueError: If res_name exceeds 5 characters
    """
    if len(res_name) > 5:
        msg = (
            f"GRO residue name '{res_name}' ({len(res_name)} chars) exceeds "
            f"the 5-character GRO format limit. "
            f"Use a shorter residue name (≤3 chars recommended for hydrate guests "
            f"to allow for _H suffix: e.g., 'CH4' → 'CH4_H')."
        )
        if context:
            msg = f"{context}: {msg}"
        raise ValueError(msg)


def parse_itp_residue_name(itp_path: str | Path) -> Optional[str]:
    """Parse residue name from a GROMACS .itp file's [ atoms ] section.
    
    The residue name is found in column 4 of the [ atoms ] section lines.
    
    Args:
        itp_path: Path to the .itp file
        
    Returns:
        Residue name string (e.g., "CH4", "THF"), or None if not found
    """
    try:
        with open(itp_path, 'r') as f:
            in_atoms_section = False
            for line in f:
                line = line.strip()
                
                # Check for [ atoms ] section header
                if line.startswith('['):
                    if 'atoms' in line.lower():
                        in_atoms_section = True
                    else:
                        in_atoms_section = False
                    continue
                
                # Skip comments and empty lines
                if not line or line.startswith(';'):
                    continue
                
                # Parse [ atoms ] section line
                # Format: nr  type  resi  res  atom  cgnr  charge  mass
                if in_atoms_section:
                    parts = line.split()
                    if len(parts) >= 4:
                        # Column 4 (0-indexed: 3) is residue name
                        res_name = parts[3]
                        return res_name
    except (IOError, OSError) as e:
        logger.warning(f"Could not read ITP file: {e}")
    
    return None


def parse_itp_atomtypes(itp_path: str | Path) -> list[tuple[str, ...]]:
    """Parse atomtypes from a GROMACS .itp file.
    
    Extracts all atomtype definitions from [ atomtypes ] section.
    Each atomtype is returned as a tuple of the line parts.
    
    Supports two common formats:
    - Format 1 (7 cols): name, at.num, mass, charge, ptype, sigma, epsilon
    - Format 2 (8 cols): name, bond_type, at.num, mass, charge, ptype, sigma, epsilon
    
    Args:
        itp_path: Path to the .itp file
        
    Returns:
        List of atomtype tuples, each containing the parsed fields.
        For 7-col format, adds empty bond_type as second element.
    """
    atomtypes = []
    try:
        with open(itp_path, 'r') as f:
            in_atomtypes_section = False
            for line in f:
                stripped = line.strip()
                
                # Check for section headers
                if stripped.startswith('['):
                    if 'atomtypes' in stripped.lower():
                        in_atomtypes_section = True
                    else:
                        in_atomtypes_section = False
                    continue
                
                # Skip comments and empty lines
                if not stripped or stripped.startswith(';') or stripped.startswith('#'):
                    continue
                
                # Parse atomtype line
                if in_atomtypes_section:
                    parts = stripped.split()
                    if len(parts) >= 7:  # Minimum 7 columns for atomtype
                        # Normalize to 8-column format
                        if len(parts) == 7:
                            # Insert empty bond_type after name
                            parts.insert(1, parts[0])  # Use name as bond_type
                        atomtypes.append(tuple(parts))
    except (IOError, OSError) as e:
        logger.warning(f"Could not read ITP file for atomtypes: {e}")
    
    return atomtypes


def comment_out_atomtypes_in_itp(itp_content: str) -> str:
    """Comment out [ atomtypes ] section in ITP file content.
    
    Adds comment header and semicolons to all lines in atomtypes section.
    This is needed because atomtypes should be defined in the main .top file,
    not in individual molecule .itp files (to avoid duplication errors).
    
    Args:
        itp_content: Original ITP file content as string
        
    Returns:
        Modified ITP content with atomtypes section commented out
    """
    lines = itp_content.split('\n')
    result_lines = []
    in_atomtypes_section = False
    atomtypes_found = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Check for section headers
        if stripped.startswith('['):
            if 'atomtypes' in stripped.lower():
                in_atomtypes_section = True
                atomtypes_found = True
                # Add comment header before the section
                result_lines.append("; Modified for QuickIce: [atomtypes] commented - types defined in main .top file")
                result_lines.append("; " + line)  # Comment out the [ atomtypes ] header
                continue
            else:
                in_atomtypes_section = False
        
        # Comment out lines in atomtypes section
        if in_atomtypes_section:
            if stripped and not stripped.startswith(';') and not stripped.startswith('#'):
                # This is a data line, comment it out
                result_lines.append('; ' + line)
            else:
                # Keep existing comments/blank lines as-is
                result_lines.append(line)
        else:
            result_lines.append(line)
    
    return '\n'.join(result_lines)


def _rewrite_atoms_section_resname(content: str, new_name: str) -> str:
    """Rewrite the resname column in the [ atoms ] section to ``new_name``.

    GROMACS ``[ atoms ]`` section format::

        [ atoms ]
        ;  Index   type   residue  resname   atom         cgnr     charge       mass
             1     hc         1      MOL     H              1    0.05772791    1.007941

    The resname is the 4th column (0-based index 3) on each data line.  Columns
    are whitespace-separated.

    Comment lines (starting with ``;`` or ``#``) and blank lines are preserved
    unchanged.  Only data lines with at least 4 whitespace-separated fields have
    their resname column replaced.  Leading whitespace on each data line is
    preserved; internal spacing is normalized to single spaces (GROMACS is
    whitespace-flexible in ITP files).

    This step is scoped to the ``[ atoms ]`` section only — it does not touch
    ``[ moleculetype ]``, ``[ atomtypes ]``, ``[ bonds ]`` or any other section
    (those are handled by Steps 1-2 or must remain untouched).

    Args:
        content: ITP content (after Steps 1-2 of ``transform_guest_itp``).
        new_name: New residue name to write into the resname column
            (e.g., ``"MOL_H"``).

    Returns:
        Content with the ``[ atoms ]`` resname column rewritten.  If no
        ``[ atoms ]`` section is found, ``content`` is returned unchanged
        (graceful no-op — some ITPs may lack an ``[ atoms ]`` section).
    """
    # Match the [ atoms ] header and capture the body up to the next
    # [ section ] header or end of string.  re.IGNORECASE so "[ ATOMS ]" is
    # also handled; re.DOTALL so '.' spans newlines.
    match = re.search(
        r'\[\s*atoms\s*\](.*?)(?=\[\s*\w+\s*\]|$)',
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if not match:
        # No [ atoms ] section — graceful no-op
        return content

    body_start = match.start(1)
    body_end = match.end(1)
    body = match.group(1)

    new_lines = []
    for line in body.split('\n'):
        stripped = line.strip()
        # Preserve blank lines and comment lines unchanged
        if not stripped or stripped.startswith(';') or stripped.startswith('#'):
            new_lines.append(line)
            continue
        # Data line: replace resname (field index 3) with new_name
        leading_ws = line[:len(line) - len(line.lstrip())]
        fields = stripped.split()
        if len(fields) >= 4:
            fields[3] = new_name
            new_lines.append(leading_ws + ' '.join(fields))
        else:
            # Not enough fields to contain a resname column — preserve as-is
            new_lines.append(line)

    new_body = '\n'.join(new_lines)
    return content[:body_start] + new_body + content[body_end:]


def transform_guest_itp(itp_content: str, guest_name: str, suffix: str = "_H") -> str:
    """Transform a guest molecule ITP file for hydrate export.
    
    Applies three transformations:
    1. Comments out [ atomtypes ] section (types defined in main .top)
    2. Appends suffix to moleculetype name (e.g., "CH4" → "CH4_H")
    3. Rewrites the resname column in the [ atoms ] section to match the new
       moleculetype name (e.g., "MOL" → "MOL_H"), so the ITP is internally
       consistent.  Deferred from Phase 38-04.
    
    Args:
        itp_content: Original ITP file content as string
        guest_name: Original guest molecule name (e.g., "CH4", "THF", or custom name)
        suffix: Suffix to append (default "_H" for hydrate guests)
        
    Returns:
        Transformed ITP content
        
    Raises:
        ValueError: If transformed residue name exceeds 5 chars (GRO format limit)
    """
    # Step 1: Comment out atomtypes (existing behavior)
    content = comment_out_atomtypes_in_itp(itp_content)
    
    # Step 2: Rewrite moleculetype name with suffix
    # Pattern: [ moleculetype ] header line followed by name line
    # ITP format:
    #   [ moleculetype ]
    #   ; Name        nrexcl
    #   CH4           3
    # We need to change "CH4" → "CH4_H" on the name line
    lines = content.split('\n')
    result_lines = []
    in_moleculetype = False
    new_name = f"{guest_name}{suffix}"
    
    # Validate the new name fits GRO format
    validate_gro_residue_name(new_name, context=f"Transformed guest ITP moleculetype name '{new_name}'")
    # (validate_gro_residue_name raises ValueError with clear message if >5 chars)
    # Note: For built-in guests (CH4_H, THF_H), the name is exactly 5 chars — passes.
    # For custom guests with base names >3 chars, this will raise — intentionally.
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if stripped.startswith('[') and 'moleculetype' in stripped.lower():
            in_moleculetype = True
            result_lines.append(line)
            continue
        
        if in_moleculetype:
            # Check if this is the name line (not a comment, not empty)
            if stripped and not stripped.startswith(';') and not stripped.startswith('#'):
                # This is the moleculetype name line
                # Replace the old name with new name
                parts = stripped.split()
                old_name = parts[0]
                # Replace old_name with new_name, preserving the rest of the line
                # (e.g., "CH4           3" → "CH4_H         3")
                new_line = line.replace(old_name, new_name, 1)
                result_lines.append(new_line)
                in_moleculetype = False
                continue
            elif not stripped:
                # Empty line after moleculetype header — still in section
                result_lines.append(line)
                continue
            else:
                # Comment line — still in section
                result_lines.append(line)
                continue
        
        result_lines.append(line)
    
    content = '\n'.join(result_lines)
    
    # Step 3: Rewrite the resname column in the [ atoms ] section to new_name
    # (the same "{guest_name}{suffix}" value used for the moleculetype rename).
    # This makes a custom guest ITP internally consistent:
    #   [ moleculetype ] etoh_custom_H  ...  [ atoms ] ... MOL_H ...
    # Graceful no-op if no [ atoms ] section is present (deferred Phase 38-04
    # item, completed in Phase 40-02).
    content = _rewrite_atoms_section_resname(content, new_name)
    
    return content
