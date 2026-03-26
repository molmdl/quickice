# Phase 1: Input Validation - Research

**Researched:** 2026-03-26
**Domain:** Python CLI argument parsing and input validation
**Confidence:** HIGH

## Summary

This phase implements CLI input validation for temperature, pressure, and molecule count parameters. Research confirms that Python's standard library `argparse` is the appropriate choice, providing built-in type conversion and validation capabilities without external dependencies. GenIce (the codebase this project wraps) already uses argparse, making this consistent with the existing codebase pattern.

The validation requirements are straightforward numeric ranges (T: 0-500K, P: 0-10000 MPa, N: 4-100000), which can be implemented using custom type converter functions that raise `argparse.ArgumentTypeError` for clean error messages.

**Primary recommendation:** Use Python's built-in argparse with custom type converter functions for range validation. No external dependencies needed.

## Standard Stack

The established libraries/tools for CLI argument parsing:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| argparse | Python 3.2+ stdlib | CLI argument parsing | Standard library, no dependencies, matches GenIce pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sys | Python stdlib | Exit codes, stderr | For error reporting and program exit |
| typing | Python 3.5+ stdlib | Type hints | For validation function signatures |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| argparse | click | Click requires external package (not in conda env); click is more feature-rich but overkill for 3 flags |
| argparse | typer | Typer requires external package (typora); Typer uses type hints elegantly but adds dependency |
| argparse | optparse | Deprecated; argparse replaced it in Python 3.2 |

**Why not alternatives:**
- **click**: Would require pip install click (not in current conda environment)
- **typer**: Same issue as click - external dependency
- **optparse**: Deprecated since Python 3.2

**Installation:**
```bash
# No installation needed - argparse is in Python standard library
```

## Architecture Patterns

### Recommended Project Structure
```
quickice/
├── cli/
│   ├── __init__.py
│   └── parser.py          # CLI argument parsing logic
├── validation/
│   ├── __init__.py
│   └── validators.py      # Custom type converters for validation
├── main.py                # Entry point
└── __init__.py
```

### Pattern 1: Custom Type Converter with ArgumentTypeError
**What:** Use argparse's `type` parameter with custom validation functions that raise `ArgumentTypeError` for invalid inputs
**When to use:** When you need range validation with user-friendly error messages
**Example:**
```python
# Source: https://docs.python.org/3/library/argparse.html#type
import argparse

def validate_temperature(value):
    """Validate temperature is in range 0-500K."""
    try:
        temp = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid number")
    
    if temp < 0 or temp > 500:
        raise argparse.ArgumentTypeError(
            f"temperature must be between 0 and 500 Kelvin, got {temp}"
        )
    return temp

# Usage in parser
parser.add_argument(
    '--temperature',
    type=validate_temperature,
    help='Temperature in Kelvin (0-500)'
)
```

### Pattern 2: Namespace with Typed Properties
**What:** Return a typed namespace object from argument parsing
**When to use:** For downstream phases that expect typed inputs
**Example:**
```python
import argparse
from dataclasses import dataclass

@dataclass
class CLIArguments:
    temperature: float
    pressure: float
    nmolecules: int

# Validation functions as shown above
# Parser setup
parser = argparse.ArgumentParser(description='QuickIce - ML-guided ice generation')
parser.add_argument('--temperature', type=validate_temperature, required=True)
parser.add_argument('--pressure', type=validate_pressure, required=True)
parser.add_argument('--nmolecules', type=validate_nmolecules, required=True)

args = parser.parse_args()
# args.temperature, args.pressure, args.nmolecules are validated floats/ints
```

### Anti-Patterns to Avoid
- **Silent truncation:** Don't use `int(value)` without checking range - floating point values will be silently truncated
- **Generic error messages:** Don't just raise `ValueError` - argparse won't format it as nicely as `ArgumentTypeError`
- **Post-validation:** Don't parse arguments then validate separately - validation should happen during parsing via type converters

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Numeric range validation | Custom validation after parse_args() | argparse `type=` with custom converter | Parsing happens once, cleaner error messages |
| Type conversion (str→float/int) | Manual try/except blocks | argparse `type=int/float` | Built into argparse, handles basic cases |
| Help message formatting | Custom help generation | argparse help= parameter | Auto-formats, respects --help |
| Error exit codes | Manual sys.exit() calls | argparse default behavior | Returns exit code 2 on error automatically |

**Key insight:** Argparse handles all these natively. Custom solutions add code without adding value.

## Common Pitfalls

### Pitfall 1: Not Handling Invalid Numeric Input
**What goes wrong:** User enters `--temperature abc`, program crashes with ugly traceback
**Why it happens:** Forgetting to handle non-numeric input in custom type converters
**How to avoid:** Always wrap numeric conversion in try/except:
```python
def validate_temperature(value):
    try:
        temp = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid number")
    # ... rest of validation
```

### Pitfall 2: Integer Truncation
**What goes wrong:** User enters `--nmolecules 4.5`, gets silently truncated to 4
**Why it happens:** Using `type=int` directly without checking for float inputs
**How to avoid:** Use custom validator that checks for float input:
```python
def validate_nmolecules(value):
    try:
        num = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid number")
    
    if num != int(num):
        raise argparse.ArgumentTypeError(
            f"molecule count must be an integer, got {num}"
        )
    # ... range validation
```

### Pitfall 3: Boundary Condition Confusion
**What goes wrong:** User enters `--temperature 500.1`, debate over whether 500 is valid
**Why it happens:** Not clearly documenting inclusive vs exclusive bounds
**How to avoid:** Be explicit in help text: `(0-500 inclusive)` or `(exclusive: 0 < T < 500)`

### Pitfall 4: Missing Required Arguments
**What goes wrong:** User forgets a required flag, gets confusing error
**Why it happens:** Not using `required=True` for mandatory arguments
**How to avoid:** Always mark required arguments explicitly:
```python
parser.add_argument('--temperature', type=validate_temperature, required=True)
```

## Code Examples

### Validation Functions for INPUT-04
```python
# Source: Python argparse documentation + validation best practices
import argparse
import sys

def validate_temperature(value: str) -> float:
    """
    Validate temperature is in range 0-500 Kelvin.
    
    Args:
        value: String input from CLI
        
    Returns:
        Valid temperature as float
        
    Raises:
        argparse.ArgumentTypeError: If value is invalid
    """
    try:
        temp = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"'{value}' is not a valid number. Temperature must be numeric."
        )
    
    if temp < 0 or temp > 500:
        raise argparse.ArgumentTypeError(
            f"temperature must be between 0 and 500 Kelvin, got {temp}K. "
            f"Valid range: 0-500K"
        )
    return temp


def validate_pressure(value: str) -> float:
    """Validate pressure is in range 0-10000 MPa."""
    try:
        pres = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"'{value}' is not a valid number. Pressure must be numeric."
        )
    
    if pres < 0 or pres > 10000:
        raise argparse.ArgumentTypeError(
            f"pressure must be between 0 and 10000 MPa, got {pres}MPa. "
            f"Valid range: 0-10000 MPa"
        )
    return pres


def validate_nmolecules(value: str) -> int:
    """Validate molecule count is in range 4-100000."""
    try:
        num = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"'{value}' is not a valid number. Molecule count must be numeric."
        )
    
    if num != int(num):
        raise argparse.ArgumentTypeError(
            f"molecule count must be an integer, got {num}"
        )
    
    num = int(num)
    if num < 4 or num > 100000:
        raise argparse.ArgumentTypeError(
            f"molecule count must be between 4 and 100000, got {num}. "
            f"Valid range: 4-100000"
        )
    return num
```

### Full Parser Setup
```python
# Source: Based on GenIce's CLI pattern + argparse best practices
import argparse
from validation.validators import (
    validate_temperature,
    validate_pressure,
    validate_nmolecules
)


def get_arguments() -> argparse.Namespace:
    """Parse and validate command-line arguments."""
    parser = argparse.ArgumentParser(
        description='QuickIce - ML-guided ice structure generation for given thermodynamic conditions',
        prog='quickice',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    parser.add_argument(
        '--temperature',
        type=validate_temperature,
        required=True,
        help='Temperature in Kelvin (valid range: 0-500)'
    )
    
    parser.add_argument(
        '--pressure',
        type=validate_pressure,
        required=True,
        help='Pressure in MPa (valid range: 0-10000)'
    )
    
    parser.add_argument(
        '--nmolecules',
        type=validate_nmolecules,
        required=True,
        help='Number of water molecules (valid range: 4-100000)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    return parser.parse_args()


if __name__ == '__main__':
    args = get_arguments()
    print(f"Temperature: {args.temperature}K")
    print(f"Pressure: {args.pressure}MPa")
    print(f"Molecules: {args.nmolecules}")
```

### Error Output Examples
```
$ quickice --temperature 600
usage: quickice [-h] --temperature TEMPERATURE --pressure PRESSURE --nmolecules NMOLECULES
quickice: error: argument --temperature: temperature must be between 0 and 500 Kelvin, got 600K. Valid range: 0-500K

$ quickice --nmolecules abc
usage: quickice [-h] --temperature TEMPERATURE --pressure PRESSURE --nmolecules NMOLECULES
quickice: error: argument --nmolecules: 'abc' is not a valid number. Molecule count must be numeric.

$ quickice --pressure 4.5
usage: quickice [-h] --temperature TEMPERATURE --pressure PRESSURE --nmolecules NMOLECULES
quickice: error: argument --pressure: pressure must be between 0 and 10000 MPa, got 4.5MPa. Valid range: 0-10000 MPa
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| optparse (deprecated) | argparse | Python 3.2 (2011) | All new CLI tools use argparse |
| Manual validation after parsing | Type converters during parsing | argparse always supported this | Cleaner error messages |
| sys.exit(1) for errors | argparse auto-exit with code 2 | Always | Consistent error handling |

**Deprecated/outdated:**
- optparse: Removed from Python documentation focus since 3.2
- getopt: Low-level, only for backwards compatibility

## Open Questions

1. **Should nmolecules default to None or be required?**
   - What we know: Requirements say INPUT-03 accepts molecule count via flag
   - What's unclear: Is molecule count optional (generate minimal by default) or required?
   - Recommendation: Make required per initial requirements, can add optional in v2

2. **Should temperature/pressure also support atmosphere units?**
   - What we know: Requirements specify MPa
   - What's unclear: Users might expect atm support
   - Recommendation: Stick to MPa per requirements, could add unit conversion in v2

3. **What's the behavior for boundary values (0, 500, 10000, 100000)?**
   - What we know: Ranges are 0-500K, 0-10000 MPa, 4-100000 molecules
   - What's unclear: Are boundaries inclusive or exclusive?
   - Recommendation: Treat as inclusive (0 and 500 are valid) - clearer for users

## Sources

### Primary (HIGH confidence)
- Python 3.14 argparse documentation - https://docs.python.org/3/library/argparse.html
- GenIce CLI implementation pattern (genice2/cli/genice.py) - Uses argparse with custom formatters

### Secondary (MEDIUM confidence)
- Click documentation for comparison - https://click.palletsprojects.com/
- Python argparse tutorial - https://docs.python.org/3/howto/argparse.html

### Tertiary (LOW confidence)
- Community patterns for scientific CLI validation - General practice, no specific source needed

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - argparse is standard library, matches GenIce pattern
- Architecture: HIGH - Simple patterns well-documented in Python docs
- Pitfalls: HIGH - Common issues with well-known solutions

**Research date:** 2026-03-26
**Valid until:** 2027-03-26 (argparse is stable, no breaking changes expected)