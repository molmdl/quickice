# Phase 25: CLI Interface Generation - Research

**Researched:** 2026-04-12
**Domain:** Python argparse CLI extension, ice-water interface generation
**Confidence:** HIGH

## Summary

Phase 25 extends QuickIce's existing CLI to support ice-water interface generation via the `--interface` flag. The existing CLI (`quickice/main.py`) uses argparse with custom validators and follows a clear pattern: parse arguments → generate candidates → process → output. Interface generation adds a parallel workflow that requires: ice candidate generation → interface assembly → GROMACS export.

The key insight is that all business logic already exists in `interface_builder.py`, `modes/`, and `gromacs_writer.py`. The CLI task is to wire argparse flags to these existing services, handle mode-specific parameter validation, and produce output matching the GUI log panel style.

**Primary recommendation:** Extend the existing parser with an `--interface` flag group, reuse validators pattern for parameter validation, and call existing generation/export services directly.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| argparse | 1.1 (stdlib) | CLI argument parsing | Already used in quickice/cli/parser.py |
| pathlib | stdlib | File path handling | Used throughout codebase |
| sys | stdlib | stderr output, exit codes | Standard for CLI errors |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typing | stdlib | Type hints for validators | New validator functions |
| dataclasses | stdlib | InterfaceConfig construction | Converting args to config |

### Existing Code to Reuse
| Module | Purpose | Key Function/Class |
|--------|---------|-------------------|
| `quickice/cli/parser.py` | CLI parser pattern | `create_parser()`, validators |
| `quickice/structure_generation/interface_builder.py` | Interface generation | `generate_interface()`, `validate_interface_config()` |
| `quickice/structure_generation/generator.py` | Ice candidate generation | `generate_candidates()` |
| `quickice/phase_mapping/lookup.py` | Phase lookup | `lookup_phase()` |
| `quickice/output/gromacs_writer.py` | GROMACS export | `write_interface_gro_file()`, `write_interface_top_file()` |
| `quickice/structure_generation/types.py` | Data types | `InterfaceConfig`, `InterfaceStructure` |

**Installation:**
No new dependencies required - all are stdlib or existing project modules.

## Architecture Patterns

### Recommended Project Structure
```
quickice/
├── cli/
│   ├── parser.py          # Existing parser - extend with --interface
│   ├── validators.py      # Existing validators - add interface validators
│   └── interface_args.py  # NEW: Interface-specific argument handling
├── main.py                # Existing main() - add interface workflow
└── ...
```

### Pattern 1: Flag Grouping with Argument Groups
**What:** Use argparse argument groups to organize related flags in help text.
**When to use:** When adding a new feature with multiple related flags.
**Example:**
```python
# Source: Python 3.14 argparse docs
parser = argparse.ArgumentParser(...)

# Interface generation group
interface_group = parser.add_argument_group(
    'interface generation',
    'Ice-water interface generation (requires --interface)'
)
interface_group.add_argument(
    '--interface',
    action='store_true',
    help='Generate ice-water interface structure'
)
interface_group.add_argument(
    '--mode', '-m',
    choices=['slab', 'pocket', 'piece'],
    required=False,  # Only required when --interface is set
    help='Interface mode (required with --interface)'
)
```

### Pattern 2: Conditional Required Arguments
**What:** Validate required arguments conditionally after parsing.
**When to use:** When arguments are only required in certain modes.
**Example:**
```python
# After parser.parse_args(), validate mode-specific requirements
def validate_interface_args(args):
    """Validate interface-specific arguments."""
    if not args.interface:
        return  # No validation needed if not using interface mode
    
    if not args.mode:
        parser.error("--mode is required when using --interface")
    
    # Mode-specific validation
    if args.mode == 'slab':
        if args.ice_thickness is None:
            parser.error("--ice-thickness is required for slab mode")
        if args.water_thickness is None:
            parser.error("--water-thickness is required for slab mode")
    
    elif args.mode == 'pocket':
        if args.pocket_diameter is None:
            parser.error("--pocket-diameter is required for pocket mode")
```

### Pattern 3: Custom Validators (Following Existing Pattern)
**What:** Create validator functions that raise ArgumentTypeError.
**When to use:** For type conversion with validation.
**Example:**
```python
# Source: quickice/validation/validators.py pattern
from argparse import ArgumentTypeError

def validate_positive_float(value: str) -> float:
    """Validate positive float input."""
    try:
        val = float(value)
    except ValueError:
        raise ArgumentTypeError(f"Expected a number, got '{value}'")
    
    if val <= 0:
        raise ArgumentTypeError(f"Value must be positive, got {val}")
    
    return val

def validate_box_dimension(value: str) -> float:
    """Validate box dimension (positive, minimum 1.0 nm)."""
    val = validate_positive_float(value)
    if val < 1.0:
        raise ArgumentTypeError(
            f"Box dimension must be >= 1.0 nm, got {val:.3f} nm"
        )
    return val
```

### Pattern 4: Converting Args to Config Object
**What:** Convert argparse Namespace to dataclass for type safety.
**When to use:** When passing configuration to existing services.
**Example:**
```python
# Source: InterfaceConfig.from_dict pattern in types.py
from quickice.structure_generation.types import InterfaceConfig

def args_to_interface_config(args) -> InterfaceConfig:
    """Convert CLI args to InterfaceConfig."""
    return InterfaceConfig(
        mode=args.mode,
        box_x=args.box_x,
        box_y=args.box_y,
        box_z=args.box_z,
        seed=args.seed if args.seed else 42,
        ice_thickness=args.ice_thickness or 0.0,
        water_thickness=args.water_thickness or 0.0,
        pocket_diameter=args.pocket_diameter or 0.0,
        pocket_shape=args.pocket_shape or 'sphere',
    )
```

### Anti-Patterns to Avoid
- **Subparsers for interface:** Overly complex for single-operation workflow. Use flag-based approach like `--gromacs` instead.
- **Re-validating in CLI:** The `validate_interface_config()` function already handles all validation. Don't duplicate.
- **Printing to stdout on error:** Use `print(..., file=sys.stderr)` for errors, stdout for normal output.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Box dimension validation | Custom checks | `validate_interface_config()` | Already handles minimum dimensions, mode-specific constraints |
| Mode-specific validation | CLI-side checks | `InterfaceGenerationError` | Existing errors have descriptive messages |
| Interface generation | New generation code | `generate_interface()` | Existing function handles all modes |
| GROMACS export | Custom writer | `write_interface_gro_file()` | Handles TIP4P-ICE normalization |
| Phase lookup | T/P matching | `lookup_phase()` | IAPWS-compliant boundary curves |
| Candidate generation | New generator | `generate_candidates()` | GenIce2 integration complete |

**Key insight:** The CLI layer should be thin - parsing and output only. All business logic exists in the service layer.

## Common Pitfalls

### Pitfall 1: Missing Mode-Specific Parameters
**What goes wrong:** User specifies `--interface --mode slab` but forgets `--ice-thickness`.
**Why it happens:** argparse can't express "required if other arg has value X".
**How to avoid:** Post-parse validation with clear error messages.
**Warning signs:** `None` values reaching `InterfaceConfig` construction.

```python
# WRONG: Let InterfaceConfig fail with confusing error
config = InterfaceConfig(mode='slab', ice_thickness=None, ...)

# RIGHT: Validate early with helpful message
if args.mode == 'slab' and args.ice_thickness is None:
    parser.error("--ice-thickness is required for slab mode")
```

### Pitfall 2: Incorrect Exit Codes
**What goes wrong:** Returning 0 even on error, or crashing without proper exit code.
**Why it happens:** Forgetting to return non-zero on error paths.
**How to avoid:** Follow existing pattern in `main.py`:
- Exit 0 on success
- Exit 1 on `UnknownPhaseError` or other errors
- Let argparse handle its own exit (via SystemExit)

```python
# Source: quickice/main.py pattern
def main() -> int:
    try:
        args = get_arguments()
        # ... processing ...
        return 0
    except UnknownPhaseError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except InterfaceGenerationError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except SystemExit:
        raise  # Let argparse exit normally
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
```

### Pitfall 3: Output Not Matching GUI
**What goes wrong:** CLI output differs significantly from GUI log panel content.
**Why it happens:** Implementing output independently of GUI.
**How to avoid:** Match GUI log panel format from `main_window.py` lines 448-481:
```python
# GUI log panel pattern:
"Starting {mode} interface generation..."
"  Box: {box_x:.2f} x {box_y:.2f} x {box_z:.2f} nm"
"  Candidate: {phase_id} ({nmolecules} molecules)"
# ... generation report from InterfaceStructure.report ...
"Interface generation complete."
```

### Pitfall 4: Overwriting Files Silently
**What goes wrong:** User's existing files overwritten without warning.
**Why it happens:** Not checking file existence before write.
**How to avoid:** Interactive prompt for overwrite (CONTEXT.md decision):
```python
def check_output_file(filepath: Path) -> bool:
    """Check if file exists and prompt for overwrite."""
    if filepath.exists():
        response = input(f"File {filepath} exists. Overwrite? [y/N] ")
        return response.lower() == 'y'
    return True
```

## Code Examples

Verified patterns from existing codebase:

### Existing CLI Pattern (main.py)
```python
# Source: quickice/main.py
def main() -> int:
    try:
        args = get_arguments()
        
        # Print validated inputs
        print("QuickIce - Ice structure generation")
        print()
        print(f"Temperature: {args.temperature}K")
        # ... processing ...
        
        return 0
    except UnknownPhaseError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
```

### Existing Validator Pattern (validators.py)
```python
# Source: quickice/validation/validators.py
def validate_temperature(value: str) -> float:
    try:
        temp = float(value)
    except ValueError:
        raise ArgumentTypeError(f"Temperature must be a number, got '{value}'")
    
    if temp < 0 or temp > 500:
        raise ArgumentTypeError(f"Temperature must be between 0 and 500K, got {temp}K")
    
    return temp
```

### Interface Generation Workflow
```python
# Source: quickice/structure_generation/interface_builder.py
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.types import InterfaceConfig

# 1. Generate ice candidate
candidates = generate_candidates(phase_info, nmolecules=256, n_candidates=1)
candidate = candidates.candidates[0]

# 2. Create configuration
config = InterfaceConfig(
    mode='slab',
    box_x=5.0, box_y=5.0, box_z=10.0,
    seed=42,
    ice_thickness=3.0,
    water_thickness=4.0,
)

# 3. Generate interface (validation happens internally)
result = generate_interface(candidate, config)

# 4. Export GROMACS
write_interface_gro_file(result, 'interface_Ih_slab.gro')
write_interface_top_file(result, 'interface_Ih_slab.top')
```

### GUI Log Panel Pattern
```python
# Source: quickice/gui/main_window.py lines 448-481
self.interface_panel.append_log(f"Starting {config.mode} interface generation...")
self.interface_panel.append_log(f"  Box: {config.box_x:.2f} x {config.box_y:.2f} x {config.box_z:.2f} nm")
self.interface_panel.append_log(f"  Candidate: {candidate.phase_id} ({candidate.nmolecules} molecules)")

# After generation:
if result.report:
    self.interface_panel.append_log("\n" + "=" * 50)
    self.interface_panel.append_log(result.report)
    self.interface_panel.append_log("=" * 50)

self.interface_panel.append_log(f"\nInterface generation complete.")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual argument counting | argparse validators | Project start | Type-safe, clear errors |
| CLI-only output | GUI-matching output | v3.0 | Consistent user experience |
| Subparsers for modes | Flag-based (`--interface`) | This phase | Simpler CLI surface |

**Deprecated/outdated:**
- `optparse`: Use argparse instead (stdlib)
- `getopt`: Use argparse instead (too low-level)

## Open Questions

Things that couldn't be fully resolved:

1. **Short flag assignments**
   - What we know: CONTEXT.md says "OpenCode's discretion"
   - What's unclear: Optimal short flags for box dimensions
   - Recommendation: Use `-x`, `-y`, `-z` for `--box-x`, `--box-y`, `--box-z`; `-m` for `--mode`; `-t` for `--ice-thickness`; `-w` for `--water-thickness`; `-d` for `--pocket-diameter`

2. **Verbose/Quiet flags**
   - What we know: CONTEXT.md says "OpenCode's discretion"
   - What's unclear: Whether to add `--verbose` for debugging
   - Recommendation: Skip for v3.5; can add in future if needed. Current output is appropriately verbose.

3. **Default box dimensions**
   - What we know: Box dimensions are mode-dependent
   - What's unclear: Best defaults when user doesn't specify
   - Recommendation: Require `--box-x`, `--box-y`, `--box-z` when `--interface` is used (no defaults). Forces user to think about system size.

## Sources

### Primary (HIGH confidence)
- Python 3.14 argparse documentation - API reference and patterns
- `quickice/cli/parser.py` - Existing CLI parser pattern
- `quickice/main.py` - Existing main entry point
- `quickice/structure_generation/interface_builder.py` - Interface generation API
- `quickice/output/gromacs_writer.py` - GROMACS export API
- `quickice/gui/main_window.py` lines 448-481 - GUI log panel reference

### Secondary (MEDIUM confidence)
- `quickice/structure_generation/types.py` - InterfaceConfig and InterfaceStructure definitions
- `quickice/structure_generation/generator.py` - Candidate generation API
- `quickice/validation/validators.py` - Validator pattern reference

### Tertiary (LOW confidence)
- None - all findings verified against source code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - argparse is stdlib, existing code patterns verified
- Architecture: HIGH - existing codebase provides clear patterns to follow
- Pitfalls: HIGH - based on actual existing code patterns and Python best practices

**Research date:** 2026-04-12
**Valid until:** Stable - argparse API stable, existing codebase patterns well-established
