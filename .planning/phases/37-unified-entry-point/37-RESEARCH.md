# Phase 37: Unified Entry Point - Research

**Researched:** 2026-06-14
**Domain:** Python package entry points, dual-mode CLI/GUI routing, display detection, graceful degradation
**Confidence:** HIGH

## Summary

Phase 37 creates `quickice/__main__.py` — a unified router that detects CLI flags and display availability to launch either CLI mode (`quickice.main.main()`) or GUI mode (`quickice.gui.main_window.run_app()`). The Python standard library's `__main__.py` mechanism is well-documented and mature: `python -m quickice` executes `quickice/__main__.py`, which should be kept minimal and delegate to existing entry functions.

Display detection must work across three platforms (Linux X11/Wayland, macOS Cocoa, Windows). The existing codebase already has partial patterns: `QUICKICE_FORCE_VTK` env var for SSH X11 forwarding, and `os.environ.get('DISPLAY')` checks in GUI viewer modules. The new `__main__.py` router should use a layered detection strategy: (1) check `--cli` flag, (2) try `import PySide6` and `import vtk`, (3) check `DISPLAY` env var on Linux, (4) attempt a minimal Qt platform check, falling back to CLI on any failure.

The argparse interaction is the trickiest design decision. The existing `quickice/cli/parser.py` has `--temperature` as a required argument, which means `python -m quickice` (no args, GUI mode) would trigger argparse error. The router must parse `sys.argv` BEFORE argparse: either (a) add `--cli`/`--gui` flags to a lightweight pre-parser, or (b) check if `sys.argv` contains any CLI flags before invoking argparse. Approach (a) is cleaner and more explicit.

**Primary recommendation:** Create `quickice/__main__.py` as a thin router: add `--cli` and `--gui` flags to a pre-parser that runs before argparse, detect display/PySide6 availability, then delegate to the existing `main()` or `run_app()` functions. Keep `quickice.py` as a backward-compatible pass-through.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `__main__.py` | 3.x stdlib | Package entry point for `python -m` | Official Python packaging pattern (PEP 338, `runpy` module) |
| `sys.argv` | stdlib | Argument inspection before argparse | Only way to detect mode flags before argparse consumes them |
| `os.environ` | stdlib | `DISPLAY`, `QT_QPA_PLATFORM`, `QUICKICE_FORCE_VTK` detection | Platform-standard environment variables |
| `argparse` | stdlib | CLI argument parsing (existing) | Already in use; no change needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `importlib.util.find_spec` | stdlib | Check if PySide6/VTK is importable without importing | Pre-import availability check |
| `PySide6.QtWidgets.QApplication` | 6.10.2 | GUI application (existing) | Only after PySide6 confirmed available |
| `subprocess` | stdlib | CLI integration tests (existing pattern) | End-to-end testing of entry point |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom pre-parser | `argparse.parse_known_args()` | `parse_known_args` is cleaner: it ignores unknown args, letting the CLI parser handle them later. Avoids building a custom parser. |
| Custom pre-parser | Click with subcommands | Complete rewrite of argparse → too invasive, breaks backward compat |
| `os.environ.get('DISPLAY')` | `QGuiApplication.platformName()` | Qt platform check is more reliable but requires importing PySide6 first (chicken-and-egg). Use DISPLAY as first check, Qt as second. |

**Installation:**
```bash
# No new packages needed — all stdlib
```

## Architecture Patterns

### Recommended Project Structure
```
quickice/
├── __init__.py         # version (existing)
├── __main__.py         # NEW: unified router (thin, <60 lines)
├── main.py             # CLI entry (existing, no changes to logic)
├── cli/
│   ├── parser.py       # argparse (existing, add --cli/--gui?)
│   └── pipeline.py     # CLIPipeline (existing)
├── gui/
│   ├── __main__.py     # GUI entry (existing, stays for `python -m quickice.gui`)
│   └── main_window.py # MainWindow + run_app() (existing)
quickice.py             # Root script (existing, add pass-through to __main__.py)
quickice-gui.spec       # PyInstaller spec (update entry point)
```

### Pattern 1: Minimal `__main__.py` Router
**What:** Thin router that detects mode and delegates to existing entry functions
**When to use:** This is THE pattern for Phase 37
**Example:**
```python
# quickice/__main__.py
# Source: Python docs https://docs.python.org/3/library/__main__.html
"""Unified entry point for QuickIce.

Usage:
    python -m quickice              # Launch GUI (if display available)
    python -m quickice --cli ...   # Launch CLI mode
    python -m quickice --gui        # Force GUI mode
    python -m quickice -T 300 ...   # CLI mode (detected from CLI flags)
"""
import sys


def _is_gui_available() -> tuple[bool, str]:
    """Check if GUI mode is possible.
    
    Returns:
        Tuple of (available, reason). If not available, reason explains why.
    """
    # Check PySide6 importability without importing
    try:
        import importlib.util
        if importlib.util.find_spec('PySide6') is None:
            return False, "PySide6 not installed"
    except (ImportError, ValueError):
        return False, "PySide6 not installed"
    
    # Check VTK importability
    try:
        import importlib.util
        if importlib.util.find_spec('vtk') is None:
            return False, "VTK not installed"
    except (ImportError, ValueError):
        return False, "VTK not installed"
    
    # Check DISPLAY on Linux (not needed on macOS/Windows)
    import platform
    if platform.system() == 'Linux':
        import os
        display = os.environ.get('DISPLAY', '')
        if not display:
            return False, "No DISPLAY environment variable (headless environment)"
    
    return True, ""


def _has_cli_flags(argv: list[str]) -> bool:
    """Detect if argv contains CLI-mode flags.
    
    Returns True if any argument looks like a CLI flag (starts with -).
    Excludes --cli, --gui, --help, --version which are router flags.
    """
    router_flags = {'--cli', '--gui', '--help', '--version', '-h', '-V'}
    for arg in argv[1:]:
        if arg.startswith('-') and arg not in router_flags:
            return True
    return False


def main() -> int:
    """Route to CLI or GUI based on arguments and environment."""
    # Check for explicit --cli or --gui flags
    if '--cli' in sys.argv:
        # Remove --cli from argv before passing to CLI parser
        sys.argv.remove('--cli')
        from quickice.main import main as cli_main
        return cli_main()
    
    if '--gui' in sys.argv:
        # Force GUI mode — fail if not available
        available, reason = _is_gui_available()
        if not available:
            print(f"Error: GUI mode requested but not available: {reason}",
                  file=sys.stderr)
            print("Install PySide6 and VTK, or run in a display-enabled environment.",
                  file=sys.stderr)
            return 1
        from quickice.gui.main_window import run_app
        run_app()
        return 0
    
    # No explicit mode flag — auto-detect
    if _has_cli_flags(sys.argv):
        # Has CLI-like flags (e.g., -T, --temperature) → CLI mode
        from quickice.main import main as cli_main
        return cli_main()
    
    # No CLI flags → try GUI, fall back to CLI
    available, reason = _is_gui_available()
    if available:
        try:
            from quickice.gui.main_window import run_app
            run_app()
            return 0
        except Exception as e:
            print(f"GUI launch failed: {e}", file=sys.stderr)
            print("Falling back to CLI mode. Use --cli to skip GUI.",
                  file=sys.stderr)
            from quickice.main import main as cli_main
            return cli_main()
    else:
        print(f"GUI not available: {reason}", file=sys.stderr)
        print("Falling back to CLI mode. Use --cli to skip this message.",
              file=sys.stderr)
        from quickice.main import main as cli_main
        return cli_main()


if __name__ == "__main__":
    sys.exit(main())
```

### Pattern 2: Backward-Compatible Root Script
**What:** Update `quickice.py` to use `python -m quickice` internally
**When to use:** Phase 37 — maintain backward compat while normalizing entry
**Example:**
```python
#!/usr/bin/env python
"""QuickIce CLI entry point (backward compatible).

For unified entry, use: python -m quickice
"""
import sys
from quickice.main import main

if __name__ == "__main__":
    sys.exit(main())
```
Note: `quickice.py` remains unchanged in behavior — it still calls `quickice.main.main()` directly. The unified entry point is the NEW `python -m quickice` path.

### Pattern 3: PyInstaller Spec Update
**What:** Update `quickice-gui.spec` to use `quickice/__main__.py` as entry
**When to use:** Building GUI distribution
**Example:**
```python
# In quickice-gui.spec, change:
#   ['quickice/gui/__main__.py']
# To:
#   ['quickice/__main__.py']
#
# This makes the binary use the unified router.
# For GUI-only binary, add a runtime hook that forces GUI mode:
# runtime_hooks=['quickice/_gui_hook.py']
```

### Anti-Patterns to Avoid
- **Heavy logic in `__main__.py`:** The `__main__.py` file should be a thin router (<60 lines). All business logic stays in `main.py` and `gui/main_window.py`.
- **Importing PySide6 at module level in `__main__.py`:** This defeats the purpose of graceful degradation. Always use lazy imports inside functions.
- **Modifying `sys.argv` before checking it:** `sys.argv.remove('--cli')` is safe, but deep-copy argv first if you need the original.
- **Custom display detection library:** No third-party library exists for this; stdlib `os.environ` + `platform.system()` + `importlib.util.find_spec` is sufficient.
- **Rewriting argparse:** Do not replace the existing parser with subcommands or Click. Add `--cli`/`--gui` as pre-parser flags that are stripped before argparse sees them.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Check if PySide6 is importable | `try: import PySide6` at top level | `importlib.util.find_spec('PySide6')` | Avoids side effects of importing (creates QApplication, loads plugins) |
| Check if VTK is importable | `try: import vtk` at top level | `importlib.util.find_spec('vtk')` | VTK import may crash in headless envs if OpenGL not available |
| Display detection on Linux | Custom X11/Wayland detection | `os.environ.get('DISPLAY')` + `QT_QPA_PLATFORM` | X11 uses DISPLAY; Wayland uses WAYLAND_DISPLAY; Qt uses QT_QPA_PLATFORM. These env vars are the standard interface. |
| Cross-platform headless detection | Custom platform checks | `platform.system()` + env vars | macOS/Windows always have display servers; only Linux needs DISPLAY check |
| CLI/GUI flag parsing | Custom tokenizer | `parse_known_args()` or simple `in sys.argv` check | `--cli`/`--gui` are simple boolean flags; no need for complex parsing |

**Key insight:** The hardest part isn't the routing logic — it's avoiding the PySide6/VTK import crashes in headless environments. `importlib.util.find_spec()` checks availability without importing, which is the critical pattern.

## Common Pitfalls

### Pitfall 1: argparse Required Args Block GUI Mode
**What goes wrong:** `python -m quickice` with no args → argparse sees `--temperature` is required → exits with error code 2
**Why it happens:** The router calls `main()` which calls `get_arguments()` which calls `parser.parse_args()` with no args
**How to avoid:** The router must detect "no CLI flags at all" BEFORE argparse runs. If `sys.argv[1:]` is empty (or only contains `--gui`), go to GUI mode. If any CLI flag is present, route to CLI.
**Warning signs:** `python -m quickice` exits with "error: the following arguments are required: --temperature"

### Pitfall 2: PySide6 Import Crashes in Headless
**What goes wrong:** `import PySide6` triggers OpenGL platform plugin load → segfault in headless/SSH env
**Why it happens:** Qt tries to connect to display server during import; without one, it crashes
**How to avoid:** Use `importlib.util.find_spec('PySide6')` to check availability WITHOUT importing. Only import PySide6 inside `_is_gui_available()` or after display detection confirms it's safe.
**Warning signs:** `python -m quickice` segfaults in Docker/CI

### Pitfall 3: VTK Import Requires OpenGL Context
**What goes wrong:** `import vtk` may fail or crash if no OpenGL context available
**Why it happens:** VTK attempts to load GL libraries; indirect rendering (SSH X11) can cause segfaults
**How to avoid:** Check `importlib.util.find_spec('vtk')` first, then wrap the actual import in try/except. The existing `QUICKICE_FORCE_VTK` env var pattern already handles this for viewer modules.
**Warning signs:** VTK import segfaults on remote SSH connections

### Pitfall 4: sys.argv Modification Leaks Between Tests
**What goes wrong:** Tests that modify `sys.argv` (e.g., `sys.argv.remove('--cli')`) affect subsequent tests
**Why it happens:** `sys.argv` is a mutable global; modifying it in one test persists to the next
**How to avoid:** In the router, copy `sys.argv` before modification, or restore after. In tests, use `subprocess.run()` (the existing pattern) which isolates process state.
**Warning signs:** Test order dependencies; passing in isolation but failing in full suite

### Pitfall 5: PyInstaller Spec Breaks After Entry Point Change
**What goes wrong:** Changing spec entry from `quickice/gui/__main__.py` to `quickice/__main__.py` changes binary behavior
**Why it happens:** The binary now goes through the router, which may fall back to CLI if display detection fails
**How to avoid:** Add a PyInstaller runtime hook that sets `QUICKICE_FORCE_GUI=true` for the binary, or use `--gui` flag in the spec's `EXE(argv=...)`. For the GUI binary, we WANT it to force GUI mode.
**Warning signs:** Binary launches CLI mode instead of GUI on headless systems

### Pitfall 6: --cli Flag Conflicts with argparse
**What goes wrong:** `--cli` is not a recognized argparse argument → argparse raises "unrecognized arguments: --cli"
**Why it happens:** argparse `parse_args()` rejects unknown flags
**How to avoid:** Strip `--cli`/`--gui` from `sys.argv` BEFORE passing to argparse. The router removes these flags before calling `cli_main()`.
**Warning signs:** `python -m quickice --cli -T 300 -P 0.1 -N 100` exits with "unrecognized arguments: --cli"

### Pitfall 7: Wayland Detection on Modern Linux
**What goes wrong:** Linux systems using Wayland don't set `DISPLAY` → router thinks no display available
**Why it happens:** Wayland uses `WAYLAND_DISPLAY` instead of `DISPLAY`; XWayland sets `DISPLAY` but pure Wayland doesn't
**How to avoid:** Check both `DISPLAY` and `WAYLAND_DISPLAY` on Linux. Also check `QT_QPA_PLATFORM=wayland`.
**Warning signs:** `python -m quickice` falls back to CLI on Wayland-only Linux desktop

## Code Examples

Verified patterns from official sources:

### Python `__main__.py` — Idiomatic Pattern
```python
# Source: Python docs https://docs.python.org/3/library/__main__.html
# The content of __main__.py typically isn't fenced with an
# if __name__ == '__main__' block. Instead, those files are kept
# short and import functions to execute from other modules.

import sys
from .student import search_students

student_name = sys.argv[1] if len(sys.argv) >= 2 else ''
print(f'Found student: {search_students(student_name)}')
```

### venv `__main__.py` — Minimal Standard Library Example
```python
# Source: CPython https://github.com/python/cpython/blob/main/Lib/venv/__main__.py
import sys
from . import main

rc = 1
try:
    main()
    rc = 0
except Exception as e:
    print('Error:', e, file=sys.stderr)
sys.exit(rc)
```

### `importlib.util.find_spec` — Safe Import Check
```python
# Source: Python docs https://docs.python.org/3/library/importlib.html
import importlib.util

def is_package_available(name: str) -> bool:
    """Check if a package can be imported without actually importing it."""
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False

# Usage:
if is_package_available('PySide6') and is_package_available('vtk'):
    # Safe to import GUI
    from quickice.gui.main_window import run_app
    run_app()
else:
    print("GUI dependencies not available", file=sys.stderr)
```

### Existing VTK/Display Detection Pattern in QuickIce
```python
# Source: quickice/gui/view.py (existing codebase)
_VTK_AVAILABLE = False
try:
    if os.environ.get('DISPLAY') and 'localhost' in os.environ.get('DISPLAY', ''):
        # Likely SSH X11 forwarding - check for direct rendering
        _VTK_AVAILABLE = os.environ.get('QUICKICE_FORCE_VTK', '').lower() == 'true'
    else:
        # Local display or forced - assume VTK works
        _VTK_AVAILABLE = True
    
    if _VTK_AVAILABLE:
        from quickice.gui.dual_viewer import DualViewerWidget
except Exception:
    _VTK_AVAILABLE = False
```

### argparse `parse_known_args` — Partial Parsing
```python
# Source: Python docs https://docs.python.org/3/library/argparse.html
# parse_known_args() returns a tuple of (known_args, remaining_argv)
# It does NOT raise errors for unknown arguments.

pre_parser = argparse.ArgumentParser(add_help=False)
pre_parser.add_argument('--cli', action='store_true', help='Force CLI mode')
pre_parser.add_argument('--gui', action='store_true', help='Force GUI mode')
known, remaining = pre_parser.parse_known_args()

if known.cli:
    # CLI mode — remaining args go to full CLI parser
    sys.argv = [sys.argv[0]] + remaining
    from quickice.main import main as cli_main
    return cli_main()
```

### Display Detection — Cross-Platform
```python
# Source: Qt docs + Linux standards
import os
import platform

def _has_display() -> bool:
    """Check if a graphical display is available.
    
    Returns:
        True on macOS/Windows (always have display servers).
        On Linux: True if DISPLAY or WAYLAND_DISPLAY is set.
    """
    system = platform.system()
    if system in ('Darwin', 'Windows'):
        return True  # macOS/Windows always have display servers
    
    # Linux: check X11 or Wayland
    if os.environ.get('DISPLAY'):
        return True
    if os.environ.get('WAYLAND_DISPLAY'):
        return True
    if os.environ.get('QT_QPA_PLATFORM', '') in ('wayland', 'xcb', 'offscreen'):
        # offscreen is used in CI — counts as "display available" for Qt
        return True
    
    return False
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `python quickice.py` (root script) | `python -m quickice` (package entry) | Phase 37 (new) | Standard Python packaging pattern; works with pip install |
| `python -m quickice.gui` (separate GUI entry) | `python -m quickice` (unified entry with routing) | Phase 37 (new) | Single entry point; auto-detects mode |
| Hard crash on missing PySide6 | Graceful fallback to CLI | Phase 37 (new) | No segfault in headless/CI; informative message |
| `DISPLAY` only check | `DISPLAY` + `WAYLAND_DISPLAY` + `QT_QPA_PLATFORM` | Phase 37 (new) | Wayland support |

**Deprecated/outdated:**
- `python quickice.py` as primary invocation: Still works (backward compat), but `python -m quickice` is now the recommended way
- `./quickice-gui` binary pointing to `quickice/gui/__main__.py`: Will point to `quickice/__main__.py` with GUI-force runtime hook

## Documentation Gaps

### cli-reference.md (docs/cli-reference.md)
**Status:** Outdated — references `python quickice.py` throughout
**Gaps identified:**
1. **Usage line:** Says `python quickice.py --temperature <T> ...` — needs `python -m quickice --cli --temperature <T> ...` (or `python -m quickice --temperature <T> ...` since CLI flags auto-detect)
2. **All 409 lines:** Every example uses `python quickice.py` — all need updating to `python -m quickice`
3. **Missing `--cli` and `--gui` flags:** No documentation for the new routing flags
4. **Missing unified entry point section:** No explanation of `python -m quickice` auto-detection behavior
5. **Missing display detection section:** No explanation of how `python -m quickice` chooses GUI vs CLI mode
6. **Missing graceful degradation section:** No docs for "PySide6 not installed" → CLI fallback behavior
7. **Exit codes section:** Currently says code 1 = "Invalid arguments" and code 2 = "Phase mapping error" — inconsistent with code 2 actually being argparse errors (exit code 2 from argparse). Need clarification.
8. **Version output:** Shows `python quickice.py 4.5.0` — will change to `python -m quickice 4.5.0` after prog name update

### README.md
**Status:** Partially outdated — uses mixed invocation patterns
**Gaps identified:**
1. **Installation section (line 66-68):** Says `python -m quickice.gui` for verification — should be `python -m quickice`
2. **Quick Start section (line 78-79):** Says `python -m quickice.gui` — should mention `python -m quickice` as primary
3. **Project Structure section (line 378):** Says `quickice.py # CLI entry point` — should note `quickice/__main__.py` as unified entry
4. **Missing `python -m quickice` documentation:** No section explains the unified entry point and its behavior
5. **No `--cli` flag mention:** CLI usage examples all use `python quickice.py`
6. **Binary Distribution section (lines 38-41):** Uses `./quickice-gui` — correct for binary, but should also mention `python -m quickice`

### README_bin.md
**Status:** Minor update needed
**Gaps identified:**
1. **QUICKICE_FORCE_VTK flag (line 9):** Documents `QUICKICE_FORCE_VTK=true` for SSH — relevant to unified entry point but no context about how the router interacts with it

## Test Gaps

### Current Test Coverage
- `tests/test_cli_integration.py`: 292 lines, uses `subprocess.run([sys.executable, str(QUICKICE_SCRIPT)])` — invokes `quickice.py` directly
- `tests/test_cli_pipeline.py`: 675 lines, same subprocess pattern via `quickice.py`
- `tests/test_integration_v35.py`: Uses same subprocess pattern via `quickice.py`
- **All three files:** Reference `QUICKICE_SCRIPT = Path(__file__).parent.parent / "quickice.py"` — none test `python -m quickice`

### Missing Tests (New Tests to Add)
1. **`test_unified_entry.py` — Unified entry point routing tests:**
   - `python -m quickice --cli -T 300 -P 0.1 -N 100` → CLI mode, exit 0
   - `python -m quickice --gui` → GUI mode (with QT_QPA_PLATFORM=offscreen)
   - `python -m quickice -T 300 -P 0.1 -N 100` → CLI mode (auto-detected from CLI flags)
   - `python -m quickice --version` → prints version
   - `python -m quickice --help` → prints help
   - `python -m quickice` (no args, no display) → falls back to CLI mode with informative message
   - `python -m quickice` (no args, with display) → GUI mode
   - `python -m quickice --cli` (no other args) → argparse error (missing required --temperature)
   - Missing PySide6 graceful fallback (mock `importlib.util.find_spec` to return None)

2. **Existing tests should ALSO pass via `python -m quickice`:**
   - `test_cli_integration.py` tests: Verify all still pass when invoked as `python -m quickice --cli <args>` instead of `python quickice.py <args>`
   - `test_cli_pipeline.py` tests: Same verification

3. **Display detection unit tests:**
   - Linux with `DISPLAY` set → detected as GUI available
   - Linux with `WAYLAND_DISPLAY` set → detected as GUI available
   - Linux with no display env vars → detected as headless
   - macOS → always GUI available
   - Windows → always GUI available
   - `QT_QPA_PLATFORM=offscreen` → detected as "display available" (CI)

4. **Backward compatibility tests:**
   - `python quickice.py -T 300 -P 0.1 -N 100` still works unchanged
   - `python -m quickice.gui` still works for direct GUI launch

5. **PyInstaller spec tests:**
   - Binary built from `quickice/__main__.py` launches GUI mode
   - Binary with `QT_QPA_PLATFORM=offscreen` doesn't crash

## Open Questions

1. **Should `--cli` and `--gui` be added to argparse itself or handled by a pre-parser?**
   - What we know: argparse `parse_known_args()` can handle this cleanly
   - What's unclear: Whether `parse_known_args()` or simple `sys.argv` inspection is better for this use case
   - Recommendation: Use `parse_known_args()` with a minimal pre-parser — it's more robust than manual `sys.argv` parsing and handles edge cases like `--cli=foo` or combined short flags

2. **Should `python -m quickice` (no args, no display) fall back to CLI or show help?**
   - What we know: Falling back to CLI would trigger "required: --temperature" error
   - What's unclear: Whether showing `--help` instead is better UX
   - Recommendation: Fall back to CLI — the argparse error message is informative ("required: --temperature"). Adding a special case for "no args + no display → show help" adds complexity for minimal benefit.

3. **Should the PyInstaller binary force `--gui` or use the router?**
   - What we know: The binary is called `quickice-gui`, so users expect GUI
   - What's unclear: Whether a runtime hook or entry point change is cleaner
   - Recommendation: Change the spec to use `quickice/__main__.py` as entry, but add a runtime hook that inserts `--gui` into `sys.argv`. This way the binary always tries GUI first.

## Sources

### Primary (HIGH confidence)
- Python docs `__main__.html` — `__main__.py` patterns, idiomatic usage, `python -m` behavior
- Python docs `runpy.html` — How `python -m` executes `__main__.py` in packages
- Python docs `argparse.html` — `parse_known_args()` for partial argument parsing
- Python docs `importlib.html` — `importlib.util.find_spec()` for safe import checks
- Qt docs `qguiapplication.html` — `platformName` property, QPA platform plugins (offscreen, xcb, wayland, cocoa, windows)

### Secondary (MEDIUM confidence)
- CPython `venv/__main__.py` — Minimal `__main__.py` example (try/except with sys.exit)
- Jupyter `notebook/__main__.py` — Real-world CLI entry point pattern
- QuickIce codebase `quickice/gui/view.py` — Existing display detection + QUICKICE_FORCE_VTK pattern
- QuickIce codebase `quickice/gui/main_window.py` — `_configure_opengl_for_remote()` + `run_app()` patterns
- QuickIce codebase `quickice/cli/parser.py` — Existing argparse with required `--temperature`

### Tertiary (LOW confidence)
- None — all findings verified against official docs or existing codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All stdlib; `__main__.py` pattern is well-documented in Python docs
- Architecture: HIGH — Pattern follows Python docs recommendations; verified against venv/__main__.py and notebook/__main__.py
- Display detection: MEDIUM — `DISPLAY`/`WAYLAND_DISPLAY` env vars are standard, but Wayland-only setups vary. `importlib.util.find_spec` is well-documented.
- Pitfalls: HIGH — All pitfalls identified from existing codebase patterns and Python/Qt documentation
- Documentation gaps: HIGH — Identified from direct code review of docs/cli-reference.md (409 lines) and README.md (396 lines)
- Test gaps: HIGH — Identified from direct code review of existing test files

**Research date:** 2026-06-14
**Valid until:** 2026-07-14 (stable — stdlib patterns don't change frequently)
