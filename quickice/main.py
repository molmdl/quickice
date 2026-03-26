"""Main entry point for QuickIce CLI."""

import sys


def main() -> int:
    """Main entry point for QuickIce.
    
    Returns:
        Exit code (0 for success, non-zero for error).
    """
    print("QuickIce - ML-guided ice structure generation")
    print("Run 'python quickice.py --help' for usage.")
    print()
    print("Note: CLI parser will be implemented in Phase 1, Plan 03.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
