#!/bin/bash
# QuickIce environment setup
# Usage: source setup.sh
#
# Run this EVERY NEW SHELL after conda env create -f env.yml (one time)

# 1. Activate conda environment
conda activate quickice

# 2. Add project to PYTHONPATH so 'quickice' package is importable
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo "QuickIce environment activated."
echo "Run 'python quickice.py --help' for usage."
