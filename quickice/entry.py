"""Unified entry point routing for QuickIce.

This module provides the main() function that routes between CLI, GUI,
and help modes. All routing logic lives here so that __main__.py and
quickice.py can both delegate to entry.main().

Design decisions:
- argv parameter with None default → uses sys.argv if None
- All heavy imports (quickice.main, quickice.gui, quickice.cli.parser) are LAZY
  (inside function branches, never at module top level) to avoid importing
  PySide6 when not needed.
- _is_pyside6_available() uses importlib.util.find_spec, never import PySide6.
- _has_display() checks platform-specific display environment variables.
- _has_pipeline_flags() detects computation flags vs router flags.
"""

import importlib.util
import platform
import sys


# Router flags that are NOT pipeline computation flags
_ROUTER_FLAGS = frozenset({'--cli', '--gui', '--help', '--version', '-h', '-V'})


def _is_pyside6_available() -> bool:
    """Check if PySide6 is available without importing it.

    Uses importlib.util.find_spec to avoid triggering a Qt crash
    in headless environments. Returns False if the spec cannot be found
    or if any import-related error occurs.

    Returns:
        True if PySide6 package is findable, False otherwise.
    """
    try:
        return importlib.util.find_spec('PySide6') is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def _has_display() -> bool:
    """Check if a graphical display is available.

    On macOS and Windows, always returns True (GUI is expected).
    On Linux, checks for DISPLAY, WAYLAND_DISPLAY, or QT_QPA_PLATFORM
    environment variables indicating an active display server.

    Returns:
        True if a display is available, False otherwise.
    """
    system = platform.system()
    if system in ('Darwin', 'Windows'):
        return True

    # Linux: check display environment variables
    import os
    display = os.environ.get('DISPLAY', '')
    wayland = os.environ.get('WAYLAND_DISPLAY', '')
    qt_platform = os.environ.get('QT_QPA_PLATFORM', '')

    if display:
        return True
    if wayland:
        return True
    if qt_platform in ('wayland', 'xcb', 'offscreen'):
        return True

    return False


def _has_pipeline_flags(argv: list[str]) -> bool:
    """Detect if argv contains pipeline computation flags.

    Returns True if any argument in argv[1:] starts with '-' AND is NOT
    a router flag (--cli, --gui, --help, --version, -h, -V). This detects
    computation flags like -T, --interface, --hydrate, -P, -N, etc.

    Args:
        argv: Full argument list (argv[0] is program name).

    Returns:
        True if pipeline computation flags are present, False otherwise.
    """
    for arg in argv[1:]:
        if arg.startswith('-') and arg not in _ROUTER_FLAGS:
            return True
    return False


def _get_install_hint() -> str:
    """Return installation hint for PySide6 based on runtime context.

    If running as a PyInstaller frozen binary, the hint suggests reinstalling
    or reporting a bug. Otherwise, it points to environment.yml.

    Returns:
        Human-readable install hint string.
    """
    if getattr(sys, 'frozen', False):
        return "Reinstall or report bug — GUI should be included in binary distribution."
    return "See environment.yml for GUI dependencies."


def main(argv: list[str] | None = None) -> int:
    """Unified entry point routing for QuickIce.

    Routes between CLI mode, GUI mode, and help based on the arguments.
    Accepts an optional argv parameter for testability; defaults to
    sys.argv if None.

    Routing priority:
    1. No args → print help, return 0
    2. --help/-h → delegate to argparse help (exits with 0)
    3. --version/-V → delegate to argparse version (exits with 0)
    4. --gui explicit → check PySide6 + display, launch GUI
    5. --cli explicit → strip --cli, pass remaining to CLI
    6. Pipeline flags detected (implicit CLI) → strip --cli/--gui if present, pass to CLI
    7. No pipeline flags, no explicit mode → print help, return 0

    Args:
        argv: Full argument list including program name. If None, uses
            sys.argv. argv[0] should be the program name (like sys.argv[0]).

    Returns:
        Exit code: 0 for success, 1 for error, 2 for argparse errors.
    """
    if argv is None:
        argv = sys.argv

    # Pre-parse to detect --cli/--gui router flags
    # Uses a minimal parser that won't error on unknown args
    import argparse
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--cli', action='store_true', default=False)
    pre_parser.add_argument('--gui', action='store_true', default=False)
    known, remaining = pre_parser.parse_known_args(argv)

    # Effective args for routing (excluding program name and router flags)
    effective_args = argv[1:]

    # 1. No args → print help
    if not effective_args:
        from quickice.cli.parser import create_parser
        parser = create_parser()
        parser.print_help()
        return 0

    # 2. --help/-h in argv → delegate to argparse help
    if '--help' in effective_args or '-h' in effective_args:
        from quickice.cli.parser import create_parser
        parser = create_parser()
        parser.parse_args(['--help'])
        # parse_args with --help calls sys.exit(0), so this line is
        # technically unreachable, but kept for clarity
        return 0

    # 3. --version/-V in argv → delegate to argparse version
    if '--version' in effective_args or '-V' in effective_args:
        from quickice.cli.parser import create_parser
        parser = create_parser()
        parser.parse_args(['--version'])
        # parse_args with --version calls sys.exit(0), so this line is
        # technically unreachable, but kept for clarity
        return 0

    # 4. --gui explicit
    if known.gui:
        if not _is_pyside6_available():
            print("Error: --gui requested but PySide6 is not installed.", file=sys.stderr)
            print(_get_install_hint(), file=sys.stderr)
            return 1
        if not _has_display():
            print("Error: --gui requested but no display is available.", file=sys.stderr)
            return 1
        from quickice.gui.main_window import run_app
        run_app()
        return 0

    # 5. --cli explicit → strip --cli from argv, pass remaining to CLI
    if known.cli:
        # remaining includes argv[0] as a positional; use effective_args
        # (argv[1:]) with --cli/--gui stripped instead
        clean_argv = [arg for arg in effective_args if arg not in ('--cli', '--gui')]
        sys.argv = [sys.argv[0]] + clean_argv
        from quickice.main import main as cli_main
        return cli_main()

    # 6. Pipeline flags detected (implicit CLI mode)
    if _has_pipeline_flags(argv):
        # Strip --cli/--gui from effective_args (argv[1:]) if present
        clean_argv = [arg for arg in effective_args if arg not in ('--cli', '--gui')]
        sys.argv = [sys.argv[0]] + clean_argv
        from quickice.main import main as cli_main
        return cli_main()

    # 7. No pipeline flags, no explicit mode → print help
    from quickice.cli.parser import create_parser
    parser = create_parser()
    parser.print_help()
    return 0
