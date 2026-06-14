#!/usr/bin/env python
"""QuickIce entry point (backward compatible).

For unified entry, use: python -m quickice
"""
import sys
from quickice.entry import main

if __name__ == "__main__":
    sys.exit(main())
