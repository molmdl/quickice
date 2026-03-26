#!/usr/bin/env python
"""QuickIce CLI entry point.

This script is run by users: python quickice.py --temperature 300 ...
It imports from the quickice/ package directory.

Usage:
    python quickice.py --temperature 300 --pressure 100 --nmolecules 100
"""
import sys
from quickice.main import main

if __name__ == "__main__":
    sys.exit(main())
