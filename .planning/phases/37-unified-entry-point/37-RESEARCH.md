# Phase 37: Unified Entry Point - Research

**Researched:** 2026-06-14
**Domain:** Python package entry points, dual-mode CLI/GUI routing, display detection, graceful degradation
**Confidence:** HIGH

## Summary

Phase 37 creates `quickice/__main__.py` and `quickice/entry.py` — a unified router that detects CLI flags and display availability to route to either CLI mode (`quickice.main.main()`) or GUI mode (`quickice.gui.main_window.run_app()`), or show help (no-args, like `git`). The Python standard library's `__main__.py` mechanism (PEP 338, `runpy` module) is well-documented and mature: `python -m quickice` executes `quickice/__main__.py`, which per Python docs should be kept minimal and delegate to testable functions in other modules.

The argparse interaction is the critical design challenge. The existing `quickice/cli/parser.py` has `--temperature` as a **required** argument (line 53), which means `python -m quickice` with no args would trigger an argparse error if the router simply forwarded to `main()`. The CONTEXT.md decision resolves this: **no args → show help** (like `git` with no args). The router must intercept before argparse runs. The cleanest approach is `argparse.parse_known_args()` with a minimal pre-parser that handles `--cli`, `--gui`, `--help`, and `--version`, then routes based on the remaining args.

Display detection must work across three platforms. The existing codebase already has patterns in `quickice/gui/view.py` (lines 20-34): `DISPLAY` env var + `QUICKICE_FORCE_VTK` for SSH X11. The new router adds `WAYLAND_DISPLAY` and `QT_QPA_PLATFORM` checks. Per CONTEXT.md, PySide6 check (via `importlib.util.find_spec`) is sufficient; VTK is not separately pre-checked.

**Primary recommendation:** Create `quickice/entry.py` with the routing logic (testable independently), and `quickice/__main__.py` as a 3-line stub that calls `entry.main()`. Use `parse_known_args()` for a pre-parser that strips `--cli`/`--gui` flags before the CLI parser sees them. The "no args" case prints help and exits 0 (like `git`).

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `__main__.py` | 3.x stdlib | Package entry point for `python -m` | Official Python packaging pattern (PEP 338, `runpy` module) |
| `argparse.parse_known_args` | stdlib | Pre-parser for `--cli`/`--gui` before main parser | Officially documented partial-parsing API; ignores unknown args |
| `importlib.util.find_spec` | stdlib | Check if PySide6 is importable without importing | Official Python API; avoids side effects of importing Qt |
| `os.environ` | stdlib | `DISPLAY`, `WAYLAND_DISPLAY`, `QT_QPA_PLATFORM` detection | Platform-standard environment variables |
| `platform.system()` | stdlib | Cross-platform OS detection | Only reliable stdlib way to distinguish Linux/macOS/Windows |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `subprocess` | stdlib | CLI integration tests (existing pattern) | End-to-end testing of entry point |
| `pytest` | existing | Test runner | All test files already use it |
| `importlib.util` | stdlib | `find_spec()` for safe import checks | In `entry.py` for PySide6 availability check |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `parse_known_args()` pre-parser | Manual `sys.argv` inspection | `parse_known_args` is more robust: handles `--cli=foo` edge cases, combined short flags, and `--` separator. Manual inspection is fragile. |
| `parse_known_args()` pre-parser | Click with subcommands | Complete rewrite of argparse → too invasive, breaks backward compat |
| `importlib.util.find_spec('PySide6')` | `try: import PySide6` | `find_spec` avoids side effects (Qt plugin loading, display connection) — critical for headless envs |
| `os.environ.get('DISPLAY')` | `QGuiApplication.platformName()` | Qt platform check requires importing PySide6 first (chicken-and-egg). Use env vars first, Qt only after import confirmed safe. |

**Installation:**
```bash
# No new packages needed — all stdlib
```

## Architecture Patterns

### Recommended Project Structure
```
quickice/
├── __init__.py         # version (existing, unchanged)
├── __main__.py         # NEW: 3-line stub calling entry.main()
├── entry.py            # NEW: routing logic (testable independently)
├── main.py             # CLI entry (existing, no changes)
├── cli/
│   ├── parser.py       # argparse (existing, add --cli/--gui flags for discoverability)
│   └── pipeline.py     # CLIPipeline (existing, unchanged)
├── gui/
│   ├── __main__.py     # GUI entry (existing, stays for `python -m quickice.gui`)
│   └── main_window.py # MainWindow + run_app() (existing, unchanged)
quickice.py             # Root script (existing, updated to call entry.main())
quickice-gui.spec       # PyInstaller spec (existing, update entry point + console)
```

### Pattern 1: Minimal `__main__.py` Stub
**What:** `__main__.py` should be 3 lines max — just calls `entry.main()`
**When to use:** This is THE pattern for Phase 37
**Rationale:** Python docs explicitly say: "The content of `__main__.py` typically isn't fenced with an `if __name__ == '__main__'` block. Instead, those files are kept short and import functions to execute from other modules."
**Example:**
```python
# quickice/__main__.py
# Source: Python docs https://docs.python.org/3/library/__main__.html
"""Unified entry point for QuickIce (python -m quickice)."""
import sys
from quickice.entry import main

sys.exit(main())
```

### Pattern 2: Testable Router in `entry.py`
**What:** All routing logic lives in `quickice/entry.py`, testable independently
**When to use:** This is THE core new file for Phase 37
**Rationale:** CONTEXT.md explicitly states: "Routing logic lives in `quickice/entry.py` (testable independently); `__main__.py` just calls `entry.main()`"
**Example:**
```python
# quickice/entry.py
"""Unified entry point routing for QuickIce.

Routes to CLI or GUI mode based on:
1. Explicit --gui flag → GUI mode (fail if PySide6 missing)
2. Pipeline flags present → CLI mode (implicit)
3. --cli flag → CLI mode (skip PySide6 import entirely)
4. Display available + PySide6 installed → show help (like git)
5. No display or no PySide6 → show help (like git)

Priority: --gui > pipeline flags (→CLI) > --cli > no-args (→help)
"""
import argparse
import importlib.util
import os
import platform
import sys


def _is_pyside6_available() -> bool:
    """Check if PySide6 is importable without actually importing it.
    
    Uses importlib.util.find_spec to avoid side effects:
    - Importing PySide6 triggers Qt plugin loading
    - Qt may crash in headless environments during import
    """
    try:
        return importlib.util.find_spec('PySide6') is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def _has_display() -> bool:
    """Check if a graphical display is available.
    
    Returns:
        True on macOS/Windows (always have display servers).
        On Linux: True if DISPLAY or WAYLAND_DISPLAY is set,
        or QT_QPA_PLATFORM indicates a display is configured.
    """
    system = platform.system()
    if system in ('Darwin', 'Windows'):
        return True  # macOS/Windows always have display servers
    
    # Linux: check X11, Wayland, or Qt platform
    if os.environ.get('DISPLAY'):
        return True
    if os.environ.get('WAYLAND_DISPLAY'):
        return True
    qpa = os.environ.get('QT_QPA_PLATFORM', '')
    if qpa in ('wayland', 'xcb', 'offscreen'):
        return True
    
    return False


def _has_pipeline_flags(argv: list[str]) -> bool:
    """Detect if argv contains CLI pipeline flags.
    
    Returns True if any argument looks like a CLI computation flag
    (starts with - and is NOT a router-only flag like --cli, --gui, --help, --version).
    """
    router_flags = {'--cli', '--gui', '--help', '--version', '-h', '-V'}
    for arg in argv[1:]:
        if arg.startswith('-') and arg not in router_flags:
            return True
    return False


def _get_install_hint() -> str:
    """Return context-appropriate installation hint for GUI dependencies."""
    # Detect if running from PyInstaller binary
    if getattr(sys, 'frozen', False):
        return "Reinstall or report bug — GUI should be included in binary distribution."
    return "See environment.yml for GUI dependencies."


def main(argv: list[str] | None = None) -> int:
    """Route to CLI or GUI based on arguments and environment.
    
    Args:
        argv: Command-line arguments (default: sys.argv[1:])
        
    Returns:
        Exit code (0 for success, 1 for error, 2 for argument error).
    """
    if argv is None:
        argv = sys.argv[1:]
    
    # Pre-parse --cli, --gui, --help, --version
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--cli', action='store_true',
                            help='Force CLI mode (skip PySide6 import)')
    pre_parser.add_argument('--gui', action='store_true',
                            help='Force GUI mode')
    known, remaining = pre_parser.parse_known_args(argv)
    
    # Handle --help and --version through the full CLI parser
    if not argv:
        # No args at all → show help (like git)
        from quickice.cli.parser import create_parser
        parser = create_parser()
        parser.print_help()
        return 0
    
    if '--help' in argv or '-h' in argv:
        from quickice.cli.parser import create_parser
        parser = create_parser()
        parser.parse_args(['--help'])  # exits with 0
        return 0  # unreachable, but explicit
    
    if '--version' in argv or '-V' in argv:
        from quickice.cli.parser import create_parser
        parser = create_parser()
        parser.parse_args(['--version'])  # exits with 0
        return 0  # unreachable
    
    # Explicit --gui → require GUI dependencies
    if known.gui:
        if not _is_pyside6_available():
            print("Error: --gui requested but PySide6 is not installed.",
                  file=sys.stderr)
            print(_get_install_hint(), file=sys.stderr)
            return 1
        if not _has_display():
            print("Error: --gui requested but no display is available.",
                  file=sys.stderr)
            return 1
        from quickice.gui.main_window import run_app
        run_app()
        return 0
    
    # Explicit --cli → CLI mode, skip PySide6 import entirely
    if known.cli:
        sys.argv = [sys.argv[0]] + remaining
        from quickice.main import main as cli_main
        return cli_main()
    
    # Pipeline flags detected → CLI mode (implicit)
    if _has_pipeline_flags(argv):
        # Strip --cli/--gui from argv if present alongside pipeline flags
        # (they were already parsed by pre_parser, but main parser shouldn't see them)
        clean_argv = [a for a in argv if a not in ('--cli', '--gui')]
        sys.argv = [sys.argv[0]] + clean_argv
        from quickice.main import main as cli_main
        return cli_main()
    
    # No pipeline flags, no explicit mode → show help (like git)
    from quickice.cli.parser import create_parser
    parser = create_parser()
    parser.print_help()
    return 0
```

### Pattern 3: `--cli`/`--gui` in argparse for Discoverability
**What:** Add `--cli` and `--gui` to `create_parser()` so they appear in `--help`
**When to use:** CONTEXT.md decision: "`--cli` and `--gui` flags added to existing parser for discoverability via `--help`"
**Rationale:** Users who run `python -m quickice --help` should see `--cli` and `--gui` documented. But argparse must NOT reject them as "unrecognized" — the router strips them before argparse sees them.
**Implementation:**
```python
# In quickice/cli/parser.py, add to create_parser():
# These flags are consumed by the entry router before argparse runs.
# They are added here for --help discoverability only.
parser.add_argument(
    "--cli",
    action="store_true",
    default=False,
    help=argparse.SUPPRESS  # OR: "Force CLI mode (see python -m quickice --help)"
)
parser.add_argument(
    "--gui",
    action="store_true",
    default=False,
    help=argparse.SUPPRESS  # OR: "Force GUI mode (see python -m quickice --help)"
)
```
**Key decision:** Use `argparse.SUPPRESS` for the help text if `--cli`/`--gui` are documented in the main `python -m quickice` help, OR show them with help text if they should be discoverable from the CLI `--help` output. The CONTEXT.md says they should be "added to existing parser for discoverability via `--help`", so they should have visible help text (not SUPPRESS).

**Critical interaction:** When `--cli`/`--gui` are added to `create_parser()`, argparse's `parse_args()` will accept them natively — no "unrecognized arguments" error. But the router's `parse_known_args()` pre-parser also needs to handle them. The correct approach is:
1. Pre-parser consumes `--cli`/`--gui` and strips them from `remaining`
2. `remaining` is passed to the full CLI parser
3. Full CLI parser also defines `--cli`/`--gui` (with defaults), so even if they slip through, no error occurs
4. The `cli_main()` function receives `args.cli` and `args.gui` attributes but ignores them (router already handled routing)

### Pattern 4: Backward-Compatible `quickice.py`
**What:** Update `quickice.py` to delegate to `entry.main()` instead of `main()` directly
**When to use:** CONTEXT.md decision: "`quickice.py` updated to delegate to `entry.main()` instead of `main()` directly"
**Example:**
```python
#!/usr/bin/env python
"""QuickIce entry point (backward compatible).

For unified entry, use: python -m quickice
"""
import sys
from quickice.entry import main

if __name__ == "__main__":
    sys.exit(main())
```

### Pattern 5: PyInstaller Spec Update for Dual-Mode Binary
**What:** Update `quickice-gui.spec` to use `quickice/__main__.py` as entry and set `console=True`
**When to use:** Building binary that supports both CLI and GUI modes
**Key details from PyInstaller docs:**
- `console=False` (windowed mode) on Windows: no console window, so CLI mode stdout/stderr are invisible
- `console=True` on Windows: console window appears (even for GUI), CLI mode works
- On Linux/macOS: `console` flag is **ignored** — console always works
- For dual-mode binary: MUST use `console=True` so CLI mode stdout is visible
- Alternative: Use `--hide-console hide-late` on Windows (hides console after GUI opens)

**Spec changes:**
```python
# In quickice-gui.spec:
a = Analysis(
    ['quickice/__main__.py'],  # Changed from ['quickice/gui/__main__.py']
    # ... rest unchanged
)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='quickice-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,              # Changed from False — needed for CLI mode
    hide_console='hide-late',  # NEW: auto-hide console on Windows when GUI starts
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

**Note:** The `hide_console='hide-late'` parameter is PyInstaller 5.x+ and auto-hides the console window on Windows when the GUI app starts, while keeping it visible for CLI mode. On Linux/macOS this parameter is ignored.

### Anti-Patterns to Avoid
- **Heavy logic in `__main__.py`:** Python docs explicitly warn: keep `__main__.py` minimal. All routing logic goes in `entry.py`.
- **Importing PySide6 at module level in `entry.py`:** Defeats graceful degradation. Always use lazy imports inside functions after `find_spec` confirms availability.
- **Modifying `sys.argv` without saving original:** The router strips `--cli`/`--gui` from `sys.argv`. Must save/restore in test contexts. PyInstaller's `__main__.py` does this pattern (saves `old_sys_argv`, restores in `finally`).
- **Custom display detection library:** No third-party library exists for this; stdlib `os.environ` + `platform.system()` + `importlib.util.find_spec` is sufficient and correct.
- **Rewriting argparse with subcommands:** CONTEXT.md explicitly defers subcommands to future: "Subcommand structure (quickice generate, quickice gui) — could be v5.0 consideration"
- **Using `console=False` in PyInstaller spec:** Makes CLI mode invisible on Windows — binary MUST have `console=True` for dual-mode support.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Check if PySide6 is importable | `try: import PySide6` at top level | `importlib.util.find_spec('PySide6')` | Avoids side effects: importing PySide6 loads Qt plugins, may crash in headless envs |
| Check if VTK is importable | `try: import vtk` at top level | `importlib.util.find_spec('vtk')` | VTK import may crash with OpenGL errors in headless envs |
| Display detection on Linux | Custom X11/Wayland detection | `os.environ.get('DISPLAY')` + `WAYLAND_DISPLAY` + `QT_QPA_PLATFORM` | X11 uses DISPLAY; Wayland uses WAYLAND_DISPLAY; Qt uses QT_QPA_PLATFORM. These are the standard interfaces. |
| Pre-parse --cli/--gui | Manual sys.argv tokenization | `argparse.parse_known_args()` with `add_help=False` | `parse_known_args` handles `--cli=foo`, combined short flags, `--` separator, and edge cases correctly |
| Cross-platform headless detection | Custom platform checks | `platform.system()` + env vars | macOS/Windows always have display servers; only Linux needs DISPLAY check |
| CLI/GUI flag stripping | Manual `sys.argv.remove('--cli')` | List comprehension filtering | `sys.argv.remove()` only removes first occurrence; list comprehension is safe and explicit |

**Key insight:** The hardest part isn't the routing logic — it's avoiding the PySide6/VTK import crashes in headless environments. `importlib.util.find_spec()` checks availability without importing, which is the critical pattern. This is officially documented in Python docs under "Checking if a module can be imported" in the importlib examples section.

## Common Pitfalls

### Pitfall 1: argparse Required Args Block No-Args Help Display
**What goes wrong:** `python -m quickice` with no args → argparse sees `--temperature` is required → exits with error code 2 and "error: the following arguments are required: --temperature"
**Why it happens:** The router calls `main()` which calls `get_arguments()` which calls `parser.parse_args()` with no args — argparse enforces required args
**How to avoid:** The router intercepts BEFORE argparse: if `sys.argv[1:]` is empty (no args), print help and exit 0. The router calls `parser.print_help()` directly instead of `parser.parse_args()`.
**Warning signs:** `python -m quickice` exits with code 2 and "required: --temperature"
**Context decision:** "No arguments → show help message (like `git` with no args)"

### Pitfall 2: `--cli` Flag Causes argparse "Unrecognized Arguments" Error
**What goes wrong:** `python -m quickice --cli -T 300 -P 0.1 -N 100` exits with "error: unrecognized arguments: --cli"
**Why it happens:** `--cli` is not defined in `create_parser()`, so `parse_args()` rejects it
**How to avoid:** Two approaches (use BOTH): (1) Router strips `--cli`/`--gui` from argv before passing to CLI parser, (2) Add `--cli`/`--gui` to `create_parser()` so argparse accepts them natively
**Warning signs:** `python -m quickice --cli -T 300 -P 0.1 -N 100` exits with code 2

### Pitfall 3: PySide6 Import Crashes in Headless Environments
**What goes wrong:** `import PySide6` triggers Qt platform plugin load → segfault in headless/SSH/Docker env
**Why it happens:** Qt tries to connect to display server during import; without one, it may crash
**How to avoid:** Use `importlib.util.find_spec('PySide6')` to check availability WITHOUT importing. Only import PySide6 after display detection confirms it's safe. The `--cli` flag short-circuits even the `find_spec` check.
**Warning signs:** `python -m quickice` segfaults in Docker/CI
**Verified:** `find_spec` does NOT trigger module execution — confirmed via Python docs and testing in this environment

### Pitfall 4: `sys.argv` Modification Leaks Between Tests
**What goes wrong:** Tests that modify `sys.argv` (e.g., `sys.argv = [sys.argv[0]] + remaining`) affect subsequent tests
**Why it happens:** `sys.argv` is a mutable global; modifying it in one test persists to the next
**How to avoid:** In `entry.main()`, accept `argv` as a parameter (default `None` → uses `sys.argv[1:]`). The `main()` function should construct a clean argv from the parameter, not modify `sys.argv` directly when called from tests. For subprocess tests (the existing pattern), argv isolation is automatic.
**Warning signs:** Test order dependencies; passing in isolation but failing in full suite

### Pitfall 5: Wayland Detection Missing on Modern Linux
**What goes wrong:** Linux systems using Wayland don't set `DISPLAY` → router thinks no display available
**Why it happens:** Wayland uses `WAYLAND_DISPLAY` instead of `DISPLAY`; pure Wayland sessions don't set `DISPLAY`
**How to avoid:** Check both `DISPLAY` AND `WAYLAND_DISPLAY` on Linux. Also check `QT_QPA_PLATFORM=wayland`.
**Warning signs:** `python -m quickice` shows help instead of launching GUI on Wayland-only Linux desktop

### Pitfall 6: PyInstaller `console=False` Hides CLI Output on Windows
**What goes wrong:** Binary built with `console=False` → CLI mode stdout/stderr are invisible on Windows
**Why it happens:** On Windows, `console=False` means no console window is allocated. CLI output goes nowhere.
**How to avoid:** Use `console=True` for the dual-mode binary. Add `hide_console='hide-late'` to auto-hide console when GUI launches. This is documented in PyInstaller usage docs under `--hide-console`.
**Warning signs:** Windows users report `quickice-gui -T 300 -P 0.1 -N 100` produces no output

### Pitfall 7: `--cli` with No Other Args Triggers argparse Error
**What goes wrong:** `python -m quickice --cli` → argparse sees no `--temperature` → exits with error
**Why it happens:** `--cli` is a mode flag, not a substitute for required computation args
**How to avoid:** This is correct behavior — `--cli` alone is an incomplete CLI invocation. Let argparse handle the error naturally (exit code 2 with "required: --temperature"). Do NOT special-case `--cli` alone.
**Context decision:** "`--cli` flag is a convenience alias meaning 'skip PySide6 import entirely' — useful in headless/CI environments. It does NOT need to be set when pipeline flags are present."

### Pitfall 8: `prog="python quickice.py"` Still Shows Old Invocation
**What goes wrong:** `python -m quickice --help` shows `python quickice.py` in usage line and examples
**Why it happens:** `create_parser()` hardcodes `prog="python quickice.py"` at line 28
**How to avoid:** Change `prog` to `"python -m quickice"`. Python 3.14 actually auto-detects `prog` from `__main__` module attributes, but we should explicitly set it for backward compat with Python 3.10+.
**Warning signs:** `python -m quickice --help` shows `python quickice.py` in usage

## Code Examples

Verified patterns from official sources:

### Python `__main__.py` — Idiomatic Pattern (from Python docs)
```python
# Source: Python docs https://docs.python.org/3/library/__main__.html
# "The content of __main__.py typically isn't fenced with an
#  if __name__ == '__main__' block. Instead, those files are kept
#  short and import functions to execute from other modules."

# CPython venv/__main__.py pattern:
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

### Real-World `__main__.py` Patterns (from GitHub)
```python
# Source: jupyter/notebook __main__.py
"""CLI entry point for notebook."""
import sys
from notebook.app import main
sys.exit(main())

# Source: ipython/ipython __main__.py
from IPython import start_ipython
start_ipython()

# Source: psf/black __main__.py
from black import patched_main
patched_main()

# Pattern: ALL real projects keep __main__.py as 1-3 lines,
# delegating to a testable function in another module.
```

### `argparse.parse_known_args()` — Partial Parsing (from Python docs)
```python
# Source: Python docs https://docs.python.org/3/library/argparse.html#partial-parsing
# parse_known_args() returns (known_args, remaining_argv)
# It does NOT raise errors for unknown arguments.

pre_parser = argparse.ArgumentParser(add_help=False)
pre_parser.add_argument('--cli', action='store_true', help='Force CLI mode')
pre_parser.add_argument('--gui', action='store_true', help='Force GUI mode')
known, remaining = pre_parser.parse_known_args()

# Verified behavior:
# Input: ['--cli', '-T', '300', '-P', '0.1', '-N', '100']
# known = Namespace(cli=True, gui=False)
# remaining = ['-T', '300', '-P', '0.1', '-N', '100']

# Input: ['-T', '300', '-P', '0.1', '-N', '100']
# known = Namespace(cli=False, gui=False)
# remaining = ['-T', '300', '-P', '0.1', '-N', '100']

# Input: ['--gui']
# known = Namespace(cli=False, gui=True)
# remaining = []
```

### `importlib.util.find_spec()` — Safe Import Check (from Python docs)
```python
# Source: Python docs https://docs.python.org/3/library/importlib.html#checking-if-a-module-can-be-imported
import importlib.util

def is_package_available(name: str) -> bool:
    """Check if a package can be imported without actually importing it."""
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False

# Verified behavior in current environment:
# is_package_available('PySide6') → True (returns ModuleSpec)
# is_package_available('vtk') → True (returns ModuleSpec)
# is_package_available('nonexistent_xyz') → False (returns None)
# find_spec('.relative') → raises ImportError (no package specified)
```

### Display Detection — Cross-Platform (verified in current environment)
```python
# Source: Linux standards (DISPLAY, WAYLAND_DISPLAY), Qt docs (QT_QPA_PLATFORM)
import os
import platform

def _has_display() -> bool:
    """Check if a graphical display is available."""
    system = platform.system()
    if system in ('Darwin', 'Windows'):
        return True  # macOS/Windows always have display servers
    
    # Linux: check X11, Wayland, or Qt platform
    if os.environ.get('DISPLAY'):
        return True
    if os.environ.get('WAYLAND_DISPLAY'):
        return True
    qpa = os.environ.get('QT_QPA_PLATFORM', '')
    if qpa in ('wayland', 'xcb', 'offscreen'):
        return True
    
    return False

# Verified in current headless Linux environment:
# Platform: Linux
# DISPLAY: <not set>
# WAYLAND_DISPLAY: <not set>
# QT_QPA_PLATFORM: <not set>
# _has_display() → False (correct for headless CI)
```

### Existing VTK/Display Detection Pattern in QuickIce
```python
# Source: quickice/gui/view.py lines 20-34 (existing codebase)
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

### PyInstaller Spec — Dual-Mode Binary Configuration
```python
# Source: PyInstaller docs https://pyinstaller.org/en/stable/spec-files.html
# Key changes for dual-mode binary:

a = Analysis(
    ['quickice/__main__.py'],  # Changed from ['quickice/gui/__main__.py']
    # ... rest unchanged
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='quickice-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,               # Changed from False — needed for CLI mode output
    hide_console='hide-late',    # NEW: auto-hide console on Windows when GUI starts
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `python quickice.py` (root script) | `python -m quickice` (package entry) | Phase 37 (new) | Standard Python packaging pattern; works with pip install |
| `python -m quickice.gui` (separate GUI entry) | `python -m quickice` (unified entry with routing) | Phase 37 (new) | Single entry point; auto-detects mode from flags |
| Hard crash on missing PySide6 | Graceful fallback with informative message | Phase 37 (new) | No segfault in headless/CI; actionable error messages |
| `DISPLAY` only check | `DISPLAY` + `WAYLAND_DISPLAY` + `QT_QPA_PLATFORM` | Phase 37 (new) | Wayland support |
| `quickice-gui.spec` with `console=False` | `console=True` + `hide_console='hide-late'` | Phase 37 (new) | CLI mode output visible on Windows; console auto-hides for GUI |
| `prog="python quickice.py"` in argparse | `prog="python -m quickice"` | Phase 37 (new) | Help output matches canonical invocation |
| 3 separate `run_cli()` helpers in test files | 1 shared helper in `tests/conftest.py` | Phase 37 (new) | DRY; consistent timeout handling |

**Deprecated/outdated:**
- `python quickice.py` as primary invocation: Still works (backward compat), but `python -m quickice` is now canonical
- `./quickice-gui` binary pointing to `quickice/gui/__main__.py`: Will point to `quickice/__main__.py` with dual-mode support
- `console=False` in PyInstaller spec: Changed to `console=True` for dual-mode binary support

## Documentation Gaps

### Exact Reference Counts (verified 2026-06-14)

| File | Lines | `quickice.py` refs | `python -m quickice` refs | Updates Needed |
|------|-------|--------------------|---------------------------|----------------|
| `quickice/cli/parser.py` | 517 | 8 (prog + 7 epilog examples) | 0 | Change prog + all epilog examples |
| `docs/cli-reference.md` | 409 | 27 | 0 | Replace all 27 occurrences with `python -m quickice` |
| `docs/flowchart.md` | 272 | 2 | 0 | Replace 2 occurrences |
| `docs/gui-guide.md` | 864 | 0 | 1 | Keep existing; add unified entry section |
| `docs/gro-itp-guide.md` | 910 | 0 | 0 | No changes needed |
| `README.md` | 396 | 1 | 2 | Update 1 `quickice.py` ref; expand unified entry docs |
| `README_bin.md` | 15 | 0 | 0 | Add platform invocation table |
| `setup.sh` | ~20 | 1 | 0 | Update help message |

**Total files needing `quickice.py` → `python -m quickice` replacement: 5 files, 39 occurrences**
**Files needing new unified entry point documentation: 3 files (README.md, docs/cli-reference.md, README_bin.md)**

### Per-File Gap Details

**`quickice/cli/parser.py` (8 occurrences):**
- Line 28: `prog="python quickice.py"` → `prog="python -m quickice"`
- Line 34-45: 7 epilog examples using `python quickice.py` → `python -m quickice`
- Need to add `--cli` and `--gui` argument definitions for discoverability
- Need to add `--cli`/`--gui` help text explaining routing behavior

**`docs/cli-reference.md` (27 occurrences):**
- Line 10: Usage line `python quickice.py --temperature <T> ...` → `python -m quickice --temperature <T> ...`
- Lines 24-332: 26 example invocations → all change to `python -m quickice`
- Line 150: Version output `python quickice.py 4.5.0` → `python -m quickice 4.5.0`
- Need new section: "Unified Entry Point" explaining `python -m quickice` routing
- Need new section: "Mode Selection" documenting `--cli` and `--gui` flags
- Need platform invocation table (source vs binary)

**`docs/flowchart.md` (2 occurrences):**
- Line 6: `python quickice.py -T <T> -P <P> -N <N> -o <output_dir>` → `python -m quickice -T <T> ...`
- Line 10: Architecture box `quickice.py` → add `quickice/__main__.py` (unified) alongside `quickice.py` (compat)

**`README.md` (1 occurrence + gaps):**
- Line 378: `quickice.py # CLI entry point` → `quickice/__main__.py # Unified entry point` + `quickice.py # Backward compat wrapper`
- Lines 66, 78: Already use `python -m quickice.gui` → should update to `python -m quickice` (primary)
- Need unified entry point section explaining routing behavior

**`README_bin.md` (0 occurrences but needs platform table):**
- Need platform invocation table:
  - Source install: `python -m quickice [options]`
  - Binary (Linux/macOS): `quickice-gui [options]`
  - Binary (Windows): `quickice-gui.exe [options]`
- Brief "Windows: append .exe" note

**`setup.sh` (1 occurrence):**
- Line 15: `echo "Run 'python quickice.py --help' for usage."` → `echo "Run 'python -m quickice --help' for usage."`

## Test Gaps

### Current Test Coverage (verified 2026-06-14)

**4 test files use subprocess to invoke QuickIce:**

| File | Pattern | `run_cli()` Signature | QUICKICE_SCRIPT |
|------|---------|-----------------------|-----------------|
| `tests/test_cli_integration.py` | subprocess via `quickice.py` | `run_cli(*args)` → timeout=10 | `Path(__file__).parent.parent / "quickice.py"` |
| `tests/test_cli_pipeline.py` | subprocess via `quickice.py` | `run_cli(*args, timeout=120)` | `Path(__file__).parent.parent / "quickice.py"` |
| `tests/test_integration_v35.py` | subprocess via `quickice.py` | `run_cli(*args, timeout=60)` | `Path(__file__).parent.parent / "quickice.py"` |
| `tests/test_phase_mapping.py` | inline subprocess (no helper) | `subprocess.run([sys.executable, "quickice.py", ...])` | Inline string `"quickice.py"` |

**Key difference: `test_phase_mapping.py` uses inline `subprocess.run` calls with string `"quickice.py"` instead of the `QUICKICE_SCRIPT` Path pattern.**

### Consolidation Plan

**Shared `run_quickice()` helper in `tests/conftest.py`:**
```python
# tests/conftest.py
import subprocess
import sys

def run_quickice(*args: str, timeout: int = 60) -> tuple[int, str, str]:
    """Run python -m quickice with given arguments.
    
    Args:
        *args: Command-line arguments to pass.
        timeout: Timeout in seconds (default: 60s).
        
    Returns:
        Tuple of (return_code, stdout, stderr).
    """
    cmd = [sys.executable, "-m", "quickice"] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr
```

**Migration for each test file:**
- `test_cli_integration.py`: Replace local `run_cli()` with `run_quickice()` from conftest. Remove `QUICKICE_SCRIPT`. Default timeout 10 → override where needed.
- `test_cli_pipeline.py`: Replace local `run_cli()` with `run_quickice()` from conftest. Remove `QUICKICE_SCRIPT`. Default timeout 120 → pass explicitly.
- `test_integration_v35.py`: Replace local `run_cli()` with `run_quickice()` from conftest. Remove `QUICKICE_SCRIPT`. Default timeout 60 → use default.
- `test_phase_mapping.py`: Replace inline `subprocess.run([sys.executable, "quickice.py", ...])` with `run_quickice(...)` from conftest.

### New Test File: `tests/test_entry_point.py`

~8-10 tests as specified in CONTEXT.md:

| Test | Invocation | Expected Behavior |
|------|------------|-------------------|
| No args → help | `python -m quickice` | Prints help, exit 0 |
| `--help` | `python -m quickice --help` | Full argparse help, exit 0 |
| `--version` | `python -m quickice --version` | Version string, exit 0 |
| `--cli` only | `python -m quickice --cli` | argparse error: required --temperature, exit 2 |
| `--cli` + pipeline flags | `python -m quickice --cli -T 300 -P 0.1 -N 100` | CLI mode, exit 0 |
| Pipeline flags (implicit CLI) | `python -m quickice -T 300 -P 0.1 -N 100` | CLI mode, exit 0 |
| `--gui` (headless) | `QT_QPA_PLATFORM=offscreen python -m quickice --gui` | GUI launch or error if no display |
| Missing PySide6 fallback | mock `find_spec` → None, no-args | Shows help, exit 0 |
| `--gui` + missing PySide6 | mock `find_spec` → None, `--gui` flag | Error message, exit 1 |
| Backward compat | `python quickice.py -T 300 -P 0.1 -N 100` | CLI mode, exit 0 |

**PySide6 mock pattern for testing missing dependency:**
```python
# In test_entry_point.py
import unittest.mock

def test_gui_missing_pyside6():
    """Explicit --gui + PySide6 missing → error exit."""
    with unittest.mock.patch('quickice.entry._is_pyside6_available', return_value=False):
        rc, stdout, stderr = run_quickice("--gui")
        assert rc == 1
        assert "PySide6 is not installed" in stderr
```

## Open Questions

1. **Should `--cli`/`--gui` in `create_parser()` use `argparse.SUPPRESS` for help or visible help text?**
   - What we know: CONTEXT.md says "added to existing parser for discoverability via `--help`"
   - What's unclear: Whether SUPPRESS is appropriate (they appear in `python -m quickice --help` but not in the pipeline help)
   - Recommendation: Use visible help text, not SUPPRESS. The `--cli`/`--gui` flags should be documented in the argparse `--help` output since CONTEXT.md explicitly says "for discoverability via `--help`".

2. **Should `hide_console='hide-late'` be used or just `console=True`?**
   - What we know: `hide-late` auto-hides console on Windows when GUI starts, which is nice UX
   - What's unclear: Whether PyInstaller version supports this parameter (it's PyInstaller 5.x+)
   - Recommendation: Use `hide_console='hide-late'` — the current `quickice-gui.spec` already uses PyInstaller 5.x+ features (`collect_all`). If it causes an error, fall back to `console=True` only.

3. **Should `_has_pipeline_flags()` detect all CLI flags or just computation flags?**
   - What we know: CONTEXT.md says "Any computation flag (`--temperature`/`-T`, `--interface`, `--hydrate`, etc.) → CLI mode automatically"
   - What's unclear: Should `--output`, `--no-diagram`, `--gromacs` (non-computation output flags) also trigger CLI mode?
   - Recommendation: YES — any flag that starts with `-` and is not a router flag (`--cli`, `--gui`, `--help`, `--version`) should trigger CLI mode. If someone passes `--output mydir` alone, argparse will error about missing `--temperature` anyway, which is the correct behavior.

4. **Should `python -m quickice --cli` with no pipeline flags show help or argparse error?**
   - What we know: `--cli` alone means "CLI mode" but no computation specified
   - What's unclear: Whether router should show help or let argparse handle it
   - Recommendation: Let argparse handle it — `--cli` alone triggers `parser.parse_args([])` which errors "required: --temperature". This is correct behavior per CONTEXT.md: "--cli flag is a convenience alias meaning skip PySide6 import entirely."

## Sources

### Primary (HIGH confidence)
- Python docs `__main__.html` — `__main__.py` patterns, idiomatic usage, `python -m` behavior. Key quote: "The content of __main__.py typically isn't fenced with an if __name__ == '__main__' block. Instead, those files are kept short and import functions to execute from other modules."
- Python docs `argparse.html#partial-parsing` — `parse_known_args()` for partial argument parsing. Verified behavior via live testing.
- Python docs `importlib.html` — `importlib.util.find_spec()` for safe import checks. Verified behavior: returns `ModuleSpec` for available packages, `None` for missing, raises `ImportError` for relative imports.
- PyInstaller docs `spec-files.html` — Spec file structure, `console` parameter, `hide_console` option.
- PyInstaller docs `usage.html` — `--hide-console` option documentation, `--console` vs `--windowed`.

### Secondary (MEDIUM confidence)
- CPython `venv/__main__.py` — Minimal `__main__.py` example (try/except with sys.exit pattern)
- jupyter/notebook `__main__.py` — Real-world CLI entry point pattern (2 lines: import + sys.exit)
- ipython/ipython `__main__.py` — Real-world dual-mode entry (1 line: import + call)
- psf/black `__main__.py` — Real-world CLI entry (1 line: import + call)
- PyInstaller `__main__.py` — Complex real-world example with argv save/restore pattern
- QuickIce codebase `quickice/gui/view.py` — Existing display detection + QUICKICE_FORCE_VTK pattern
- QuickIce codebase `quickice/gui/main_window.py` — `_configure_opengl_for_remote()` + `run_app()` patterns
- QuickIce codebase `quickice/cli/parser.py` — Existing argparse with required `--temperature` (line 53), prog name (line 28), epilog examples

### Tertiary (LOW confidence)
- None — all findings verified against official docs, existing codebase, or live testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All stdlib; `__main__.py` pattern is well-documented in Python docs
- Architecture: HIGH — Pattern follows Python docs recommendations; verified against venv/notebook/ipython/black `__main__.py`
- Display detection: HIGH — `DISPLAY`/`WAYLAND_DISPLAY`/`QT_QPA_PLATFORM` env vars are Linux standards; verified in current headless environment
- argparse interaction: HIGH — `parse_known_args()` behavior verified via live testing; required-args pitfall identified from codebase
- PyInstaller spec: MEDIUM — `hide_console` parameter documented but version-specific; needs build verification
- Documentation gaps: HIGH — Exact counts verified via grep: 39 occurrences across 5 files
- Test gaps: HIGH — Exact patterns identified from code review of all 4 subprocess-using test files

**Research date:** 2026-06-14
**Valid until:** 2026-07-14 (stable — stdlib patterns don't change frequently; PyInstaller spec details may need re-verification on next major version)
