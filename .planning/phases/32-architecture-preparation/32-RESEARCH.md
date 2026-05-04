# Phase 32: Architecture Preparation - Research

**Researched:** 2026-05-05
**Domain:** Python enum patterns, PySide6 tab management, GROMACS file formats, validation patterns
**Confidence:** HIGH

## Summary

This phase requires implementing four infrastructure components: (1) TabIndex enum for tab position constants, (2) MoleculetypeRegistry for unique GROMACS molecule naming, (3) ITP parser for GROMACS topology files, and (4) molecule validator for GRO/ITP consistency checking.

Python's `IntEnum` from the standard library is the standard approach for tab index constants, providing type safety and preventing hardcoded integer bugs. GROMACS ITP files have a well-documented format with `[ moleculetype ]` directive followed by `[ atoms ]` section. PySide6's `QTabWidget` supports tab reordering via `insertTab()` and `removeTab()` methods.

**Primary recommendation:** Use Python `IntEnum` for TabIndex, implement MoleculetypeRegistry with collision detection using a set of reserved names, parse ITP files with regex-based section extraction, and validate GRO/ITP consistency by comparing atom counts and residue names.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| enum.IntEnum | stdlib | Tab position constants | Type-safe, prevents hardcoded index bugs, standard library |
| re | stdlib | ITP file parsing | Standard library, sufficient for structured GROMACS format |
| dataclasses | stdlib | Registry data structures | Clean, type-safe data containers |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib.Path | stdlib | File path handling | All file I/O operations |
| typing.Optional, typing.Dict | stdlib | Type hints | Type safety throughout |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| IntEnum | plain constants | IntEnum provides type safety, automatic int conversion, iteration |
| regex parsing | full ITP parser library | GROMACS format is simple, regex is sufficient for extraction needs |

**Installation:**
All components use Python standard library only - no additional dependencies required.

## Architecture Patterns

### Recommended Project Structure
```
quickice/
├── gui/
│   ├── constants.py         # TabIndex enum definition
│   └── main_window.py       # Use TabIndex.ICE instead of hardcoded 0
├── structure_generation/
│   ├── moleculetype_registry.py  # MoleculetypeRegistry class
│   ├── itp_parser.py             # ITP file parsing (~80 lines)
│   └── molecule_validator.py     # GRO/ITP consistency checking
└── output/
    └── gromacs_writer.py     # Use registry for moleculetype naming
```

### Pattern 1: IntEnum for Tab Index Constants
**What:** Use Python's `IntEnum` to define tab positions as named constants
**When to use:** Replace all hardcoded tab index references in codebase
**Example:**
```python
from enum import IntEnum

class TabIndex(IntEnum):
    """Tab position constants for QTabWidget indices.
    
    Use instead of hardcoded integers to prevent bugs after reordering.
    Example: tab_widget.setCurrentIndex(TabIndex.ICE)
    """
    ICE = 0          # Ice Generation tab
    HYDRATE = 1      # Hydrate Config tab
    INTERFACE = 2    # Interface Construction tab
    SOLUTE = 3       # Solute Insertion tab (planned)
    CUSTOM = 4       # Custom Molecule tab (planned)
    ION = 5          # Ion Insertion tab (moves from position 4 to 6)
```

**Integration approach:**
```python
# Before (hardcoded):
self.tab_widget.setCurrentIndex(0)
if index == 0:  # Ice tab

# After (type-safe):
self.tab_widget.setCurrentIndex(TabIndex.ICE)
if index == TabIndex.ICE:
```

### Pattern 2: MoleculetypeRegistry Design
**What:** Registry that tracks molecule types and generates unique GROMACS names
**When to use:** When exporting GROMACS files that need unique moleculetype names
**Example:**
```python
class MoleculetypeRegistry:
    """Registry for unique GROMACS moleculetype naming.
    
    Ensures CH4 from hydrate cages (CH4_HYD) is distinct from
    CH4 dissolved in liquid (CH4_LIQ) in GROMACS topology files.
    """
    
    # Reserved names - user cannot create custom molecules with these
    RESERVED_NAMES = {
        "SOL", "NA", "CL", "CH4", "THF", "CO2", "H2",
        "CH4_HYD", "CH4_LIQ", "THF_HYD", "THF_LIQ"
    }
    
    def __init__(self):
        self._registered: dict[str, str] = {}  # source -> moleculetype name
        self._counter = 0  # For CUSTOM_MOL_1, CUSTOM_MOL_2, etc.
    
    def register_hydrate_guest(self, molecule: str) -> str:
        """Register hydrate guest molecule (CH4_HYD, THF_HYD)."""
        name = f"{molecule.upper()}_HYD"
        self._registered[f"hydrate_{molecule}"] = name
        return name
    
    def register_liquid_solute(self, molecule: str) -> str:
        """Register liquid solute (CH4_LIQ, THF_LIQ)."""
        name = f"{molecule.upper()}_LIQ"
        self._registered[f"liquid_{molecule}"] = name
        return name
    
    def register_custom_molecule(self, user_name: str = "MOL") -> str:
        """Register custom molecule with unique name.
        
        Args:
            user_name: User-provided name (default "MOL")
            
        Returns:
            Unique moleculetype name (MOL, MOL_1, MOL_2, etc.)
            
        Raises:
            ValueError: If name conflicts with reserved names
        """
        if user_name.upper() in self.RESERVED_NAMES:
            raise ValueError(
                f"'{user_name}' is reserved. "
                f"Reserved names: {', '.join(sorted(self.RESERVED_NAMES))}"
            )
        
        # Generate unique name
        name = user_name.upper()
        if name in [n for n in self._registered.values()]:
            self._counter += 1
            name = f"{name}_{self._counter}"
        
        self._registered[f"custom_{self._counter}"] = name
        return name
    
    def get_gromacs_name(self, source: str) -> str:
        """Get moleculetype name for GROMACS export."""
        return self._registered.get(source, source.upper())
```

### Pattern 3: ITP Parser Implementation
**What:** Parse GROMACS .itp topology files to extract moleculetype information
**When to use:** When validating user-uploaded custom molecule .itp files
**Example:**
```python
import re
from pathlib import Path
from dataclasses import dataclass

@dataclass
class ITPMoleculeInfo:
    """Parsed information from ITP file."""
    molecule_name: str
    atom_count: int
    atom_types: list[str]
    has_atomtypes_section: bool

def parse_itp_file(filepath: Path) -> ITPMoleculeInfo:
    """Parse GROMACS .itp topology file.
    
    Extracts:
    - moleculetype name from [ moleculetype ] directive
    - atom count from [ atoms ] section
    - atom types from [ atoms ] section
    
    Args:
        filepath: Path to .itp file
        
    Returns:
        Parsed molecule information
        
    Raises:
        ValueError: If file format is invalid or missing required sections
    """
    content = filepath.read_text()
    
    # Extract moleculetype name
    mol_match = re.search(
        r'\[\s*moleculetype\s*\]\s*\n\s*;\s*Name\s+nrexcl\s*\n\s*(\w+)',
        content,
        re.IGNORECASE
    )
    if not mol_match:
        raise ValueError(
            f"Missing [ moleculetype ] section in {filepath.name}\n"
            "Required format:\n"
            "[ moleculetype ]\n"
            "; Name  nrexcl\n"
            "MOLNAME  3"
        )
    
    molecule_name = mol_match.group(1)
    
    # Extract atoms section
    atoms_match = re.search(
        r'\[\s*atoms\s*\](.*?)(?=\[\s*\w+\s*\]|$)',
        content,
        re.DOTALL | re.IGNORECASE
    )
    if not atoms_match:
        raise ValueError(
            f"Missing [ atoms ] section in {filepath.name}"
        )
    
    # Count atoms and extract types
    atoms_section = atoms_match.group(1)
    atom_lines = [
        line for line in atoms_section.split('\n')
        if line.strip() and not line.strip().startswith(';')
    ]
    
    atom_types = []
    for line in atom_lines:
        fields = line.split()
        if len(fields) >= 2:
            atom_types.append(fields[1])  # Atom type is second column
    
    atom_count = len(atom_types)
    
    # Check for [ atomtypes ] section
    has_atomtypes = bool(re.search(
        r'\[\s*atomtypes\s*\]',
        content,
        re.IGNORECASE
    ))
    
    return ITPMoleculeInfo(
        molecule_name=molecule_name,
        atom_count=atom_count,
        atom_types=atom_types,
        has_atomtypes_section=has_atomtypes
    )
```

**GROMACS ITP format reference:**
```
[ moleculetype ]
; Name        nrexcl
MOLECULE      3

[ atoms ]
;  nr  type  resi  res  atom  cgnr  charge  mass
    1   C      1    MOL   C1     1     0.0   12.01
    2   H      1    MOL   H1     1     0.1    1.008
```

### Pattern 4: GRO/ITP Validation
**What:** Validate consistency between .gro structure file and .itp topology file
**When to use:** Immediate validation when user uploads custom molecule files
**Example:**
```python
from pathlib import Path
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of GRO/ITP consistency validation."""
    is_valid: bool
    errors: list[str]
    warnings: list[str]

def validate_gro_itp_consistency(
    gro_path: Path,
    itp_info: ITPMoleculeInfo
) -> ValidationResult:
    """Validate GRO file consistency with ITP file.
    
    Checks:
    1. Atom count matches between GRO and ITP
    2. Residue name matches ITP moleculetype name
    
    Args:
        gro_path: Path to .gro file
        itp_info: Parsed ITP information
        
    Returns:
        Validation result with errors and warnings
    """
    errors = []
    warnings = []
    
    # Parse GRO file
    try:
        from quickice.structure_generation.gro_parser import parse_gro_file
        positions, atom_names, cell = parse_gro_file(gro_path)
        gro_atom_count = len(positions)
    except Exception as e:
        errors.append(f"Failed to parse GRO file: {e}")
        return ValidationResult(False, errors, warnings)
    
    # Check atom count
    if gro_atom_count != itp_info.atom_count:
        errors.append(
            f"Atom count mismatch:\n"
            f"  GRO file has {gro_atom_count} atoms\n"
            f"  ITP file defines {itp_info.atom_count} atoms\n"
            f"  in [ atoms ] section"
        )
    
    # Check residue name (would need to read GRO residue names)
    # This requires extending gro_parser to extract residue names
    
    # Check for [ atomtypes ] section
    if not itp_info.has_atomtypes_section:
        warnings.append(
            f"Missing [ atomtypes ] section in {gro_path.stem}.itp\n"
            "User must provide atom type parameters separately"
        )
    
    is_valid = len(errors) == 0
    return ValidationResult(is_valid, errors, warnings)
```

### Anti-Patterns to Avoid
- **Hardcoded tab indices:** Never use magic numbers like `tab_widget.setCurrentIndex(0)` - use `TabIndex.ICE`
- **String-based tab references:** Don't use "Tab 1", "Tab 2" in error messages - use tab names "Ice Generation tab"
- **Duplicate moleculetype names:** GROMACS fails with duplicate moleculetype definitions - always use registry
- **Validation at export time:** Don't wait until export to validate - validate immediately on file upload

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tab index constants | Integer constants | `enum.IntEnum` | Type safety, iteration, prevents typos |
| GRO parsing | Custom parser | Existing `gro_parser.py` | Already handles triclinic cells, proven |
| Unique ID generation | Counter variable | MoleculetypeRegistry with collision detection | Reserved names, conflict detection |

**Key insight:** Standard library `IntEnum` and existing `gro_parser.py` eliminate need for custom solutions. Focus effort on ITP parsing and validation logic.

## Common Pitfalls

### Pitfall 1: Tab Reordering Breaking Hardcoded References
**What goes wrong:** After Ion tab moves from position 4 to 6, all code using `if index == 3` breaks
**Why it happens:** Hardcoded integers don't update when tabs are reordered
**How to avoid:** Use `TabIndex.ION` constant everywhere - single source of truth
**Warning signs:** grep for `currentIndex() ==` or `if index ==` patterns in codebase

### Pitfall 2: GROMACS Duplicate Moleculetype Errors
**What goes wrong:** Export fails with "Duplicate moleculetype definition for CH4"
**Why it happens:** Same CH4 molecule appears in hydrate cages and liquid phase with same name
**How to avoid:** Always use MoleculetypeRegistry to generate distinct names (CH4_HYD vs CH4_LIQ)
**Warning signs:** Single `CH4` name used for both hydrate guest and liquid solute

### Pitfall 3: ITP Parser Missing Sections
**What goes wrong:** Parser fails on valid ITP file because it expects exact format
**Why it happens:** GROMACS format has optional whitespace, comments, case variations
**How to avoid:** Use regex with `re.IGNORECASE`, `re.DOTALL`, handle semicolon comments
**Warning signs:** Parser fails on files that work with GROMACS tools

### Pitfall 4: Validation Too Late in Workflow
**What goes wrong:** User discovers GRO/ITP mismatch only at export time after working for hours
**Why it happens:** Validation not performed on file upload
**How to avoid:** Validate immediately when user selects .gro/.itp files, show errors right away
**Warning signs:** Validation only called in export code path

### Pitfall 5: Error Messages Too Generic
**What goes wrong:** User sees "Validation failed" with no actionable information
**Why it happens:** Exception caught and replaced with generic message
**How to avoid:** Provide specific error: "GRO has 15 atoms, ITP defines 12 atoms" with file names
**Warning signs:** Error messages without file names or specific values

## Code Examples

### Tab Reordering Implementation
```python
# In main_window.py _setup_ui()

# Current order (v4.0):
# Tab 0: Ice Generation
# Tab 1: Hydrate Config
# Tab 2: Interface Construction
# Tab 3: Ion Insertion

# New order (v4.5):
# Tab 0: Ice Generation
# Tab 1: Hydrate Config
# Tab 2: Interface Construction
# Tab 3: Solute Insertion (new)
# Tab 4: Custom Molecule (new)
# Tab 5: Ion Insertion (moved from 3 to 5)

# Implementation approach:
# 1. Define TabIndex enum with final positions
# 2. Update all tab references to use TabIndex constants
# 3. Tab widget maintains position automatically via insertTab() order

# No runtime reordering needed - tabs added in correct order from start
```

### Error Reporting Pattern
```python
# Immediate validation on file selection (from CONTEXT.md)
def on_custom_molecule_file_selected(self, gro_path: Path, itp_path: Path):
    """Validate files immediately when user selects them."""
    
    # Parse ITP
    try:
        itp_info = parse_itp_file(itp_path)
    except ValueError as e:
        QMessageBox.warning(
            self, "ITP File Error",
            f"Failed to parse {itp_path.name}:\n\n{str(e)}\n\n"
            "Please check the file format."
        )
        return
    
    # Validate consistency
    result = validate_gro_itp_consistency(gro_path, itp_info)
    
    if not result.is_valid:
        # Batch report all errors
        error_text = "\n\n".join(result.errors)
        QMessageBox.critical(
            self, "Validation Failed",
            f"File validation failed:\n\n{error_text}"
        )
        return
    
    if result.warnings:
        # Show warnings but allow continuation
        warning_text = "\n\n".join(result.warnings)
        QMessageBox.warning(
            self, "Validation Warnings",
            f"Warnings:\n\n{warning_text}\n\n"
            "You can continue, but may need to provide "
            "additional parameters."
        )
    
    # Files validated successfully
    self.load_custom_molecule(gro_path, itp_path, itp_info)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded tab indices | TabIndex enum constants | Phase 32 (this phase) | Type safety, prevents reorder bugs |
| Single molecule name per type | Context-specific names (CH4_HYD vs CH4_LIQ) | Phase 32 | GROMACS export correctness |
| Validation at export | Immediate validation on upload | Phase 32 | Better UX, catch errors early |
| Generic errors | Specific file/line-level errors | Phase 32 | Faster debugging, clearer guidance |

**Deprecated/outdated:**
- Hardcoded integer tab references: Replaced by TabIndex enum
- Generic "Tab 1", "Tab 2" UI text: Replaced by tab names only
- Single MOLECULE_TO_GROMACS mapping: Replaced by MoleculetypeRegistry

## Open Questions

### 1. Validation Thoroughness Level
**What we know:** Minimum validation includes atom count, residue name, file existence
**What's unclear:** Whether to validate mass/charge sanity, bond lengths, angle parameters
**Recommendation:** Start with minimum (atom count, residue name), add optional deep validation later. Focus on user-facing errors that prevent GROMACS from running.

### 2. Multiple Issues Reporting Format
**What we know:** CONTEXT.md allows batch report, fail-fast, or warnings+errors approaches
**What's unclear:** Which approach is most user-friendly
**Recommendation:** Use batch report for errors (show all issues at once so user can fix everything), warnings+errors approach (warnings don't block continuation). This balances clarity with user control.

### 3. Error Log File Writing
**What we know:** CONTEXT.md mentions optional error log file writing
**What's unclear:** Filename format, when to write, whether to prompt user
**Recommendation:** Skip error log file for Phase 32. In-app log box + error dialog is sufficient. Log files add complexity without clear benefit for typical use cases.

## Sources

### Primary (HIGH confidence)
- Python enum documentation - IntEnum usage, type safety, iteration
- GROMACS 2026.1 manual - ITP file format, moleculetype directive, atoms section
- GROMACS 2026.1 manual - GRO file format, atom records, residue numbering
- Existing codebase - gro_parser.py, gromacs_ion_export.py, types.py

### Secondary (MEDIUM confidence)
- PySide6 QTabWidget documentation - tab management methods
- CONTEXT.md decisions - locked choices for implementation approach

### Tertiary (LOW confidence)
None - all findings verified with official documentation or existing codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Python stdlib (IntEnum, re, dataclasses), proven approach
- Architecture: HIGH - Based on existing codebase patterns, official GROMACS docs
- Pitfalls: HIGH - Directly addresses CONTEXT.md decisions and GROMACS requirements

**Research date:** 2026-05-05
**Valid until:** Stable - Python enum and GROMACS format are stable standards
