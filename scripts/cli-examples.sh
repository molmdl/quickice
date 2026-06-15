#!/bin/bash
# QuickIce CLI Example Commands
# Demonstrates all available CLI flag combinations for python -m quickice
#
# Usage: View this file as a reference, or uncomment commands you want to run
# See docs/cli-reference.md for full documentation

set -e

# ==============================================================================
# Ice Generation
# ==============================================================================

# === Ice Generation ===

# Ice Ih at ambient conditions
# python -m quickice -T 250 -P 0.1 -N 96

# Ice Ic (cubic, low temperature)
# python -m quickice -T 200 -P 0.1 -N 96

# Ice II (moderate pressure, ordered)
# python -m quickice -T 200 -P 300 -N 96

# Ice III (moderate pressure)
# python -m quickice -T 250 -P 250 -N 96

# Ice V (higher pressure, monoclinic)
# python -m quickice -T 260 -P 450 -N 96

# Ice VI (high pressure, double network)
# python -m quickice -T 280 -P 700 -N 96

# Ice VII (very high pressure, cubic)
# python -m quickice -T 300 -P 2500 -N 96

# Ice VIII (ordered Ice VII)
# python -m quickice -T 200 -P 2500 -N 96

# === Ice Generation + GROMACS Export ===

# Export Ice Ih with GROMACS format
# python -m quickice -T 250 -P 0.1 -N 256 --gromacs -g -o ice_ih_gmx

# Export Ice VII specific candidate (rank 2)
# python -m quickice -T 300 -P 2500 -N 256 --gromacs -g --candidate 2 -o ice_vii_c2

# === Ice Generation + Options ===

# Skip phase diagram generation
# python -m quickice -T 250 -P 0.1 -N 96 --no-diagram

# Reproducible generation with custom seed
# python -m quickice -T 250 -P 0.1 -N 96 --seed 12345

# Prevent output overwrite
# python -m quickice -T 250 -P 0.1 -N 96 --no-overwrite

# ==============================================================================
# Interface Generation
# ==============================================================================

# === Interface Generation - Slab Mode ===

# Slab interface: ice|water|ice layers
# python -m quickice -T 250 -P 0.1 --interface --mode slab --box-x 5.0 --box-y 5.0 --box-z 10.0 --ice-thickness 3.0 --water-thickness 4.0 --gromacs -g --no-diagram -o slab_output

# Slab with GROMACS export, custom seed
# python -m quickice -T 250 -P 0.1 --interface --mode slab --box-x 4.0 --box-y 4.0 --box-z 8.0 --ice-thickness 2.5 --water-thickness 3.0 --gromacs -g --seed 42 -o slab_seed42

# === Interface Generation - Pocket Mode ===

# Spherical pocket in ice matrix
# python -m quickice -T 253 -P 500 --interface --mode pocket --box-x 4.0 --box-y 4.0 --box-z 4.0 --pocket-diameter 2.0 --gromacs -g --no-diagram -o pocket_sphere

# Cubic pocket in ice matrix
# python -m quickice -T 253 -P 500 --interface --mode pocket --box-x 4.0 --box-y 4.0 --box-z 4.0 --pocket-diameter 2.0 --pocket-shape cubic --gromacs -g -o pocket_cubic

# === Interface Generation - Piece Mode ===

# Ice crystal embedded in water
# python -m quickice -T 180 -P 1000 --interface --mode piece --box-x 4.0 --box-y 4.0 --box-z 4.0 --gromacs -g --no-diagram -o piece_output

# ==============================================================================
# Hydrate Generation
# ==============================================================================

# === Hydrate Generation ===

# sI hydrate with CH4 guest (default)
# python -m quickice --hydrate --lattice-type sI --guest CH4 -o hydrate_sI_CH4

# sII hydrate with THF guest
# python -m quickice --hydrate --lattice-type sII --guest THF -o hydrate_sII_THF

# sH hydrate with CH4
# python -m quickice --hydrate --lattice-type sH --guest CH4 -o hydrate_sH_CH4

# sI hydrate with 2x2x2 supercell
# python -m quickice --hydrate --lattice-type sI --guest CH4 --supercell-x 2 --supercell-y 2 --supercell-z 2 -o hydrate_sI_222

# sI hydrate with partial cage occupancy
# python -m quickice --hydrate --lattice-type sI --guest CH4 --cage-occupancy-small 80.0 --cage-occupancy-large 95.0 -o hydrate_sI_partial

# === Hydrate + GROMACS Export ===

# sI CH4 hydrate with GROMACS export
# python -m quickice --hydrate --lattice-type sI --guest CH4 --gromacs -g --no-diagram -o hydrate_gmx

# ==============================================================================
# Custom Molecule Insertion
# ==============================================================================

# === Interface + Custom Molecule (Random Placement) ===

# Slab interface with ethanol molecules (random, by count)
# python -m quickice -T 250 -P 0.1 --interface --mode slab --box-x 5.0 --box-y 5.0 --box-z 10.0 --ice-thickness 3.0 --water-thickness 4.0 --custom-gro quickice/data/custom/etoh.gro --custom-itp quickice/data/custom/etoh.itp --custom-placement random --custom-count 5 --gromacs -g --no-diagram -o custom_random_count

# Slab interface with ethanol (random, by concentration)
# python -m quickice -T 250 -P 0.1 --interface --mode slab --box-x 5.0 --box-y 5.0 --box-z 10.0 --ice-thickness 3.0 --water-thickness 4.0 --custom-gro quickice/data/custom/etoh.gro --custom-itp quickice/data/custom/etoh.itp --custom-placement random --custom-concentration 0.5 --gromacs -g --no-diagram -o custom_random_conc

# === Interface + Custom Molecule (Custom Positions) ===

# Custom molecule at specified positions from CSV
# python -m quickice -T 250 -P 0.1 --interface --mode slab --box-x 5.0 --box-y 5.0 --box-z 10.0 --ice-thickness 3.0 --water-thickness 4.0 --custom-gro quickice/data/custom/etoh.gro --custom-itp quickice/data/custom/etoh.itp --custom-placement custom --custom-positions-file quickice/data/examples/custom_positions.csv --gromacs -g --no-diagram -o custom_positions

# ==============================================================================
# Solute Insertion
# ==============================================================================

# === Interface + Solute ===

# CH4 solute in liquid water
# python -m quickice -T 250 -P 0.1 --interface --mode slab --box-x 5.0 --box-y 5.0 --box-z 10.0 --ice-thickness 3.0 --water-thickness 4.0 --solute-type CH4 --solute-concentration 0.3 --gromacs -g --no-diagram -o solute_ch4

# THF solute in liquid water
# python -m quickice -T 250 -P 0.1 --interface --mode slab --box-x 5.0 --box-y 5.0 --box-z 10.0 --ice-thickness 3.0 --water-thickness 4.0 --solute-type THF --solute-concentration 0.5 --gromacs -g --no-diagram -o solute_thf

# Solute from custom molecule source
# python -m quickice -T 250 -P 0.1 --interface --mode slab --box-x 5.0 --box-y 5.0 --box-z 10.0 --ice-thickness 3.0 --water-thickness 4.0 --custom-gro quickice/data/custom/etoh.gro --custom-itp quickice/data/custom/etoh.itp --custom-placement random --custom-concentration 0.3 --solute-type CH4 --solute-concentration 0.15 --solute-source custom --gromacs -g --no-diagram -o solute_from_custom

# ==============================================================================
# Ion Insertion
# ==============================================================================

# === Interface + Ion Insertion ===

# NaCl ions from interface source (default)
# python -m quickice -T 250 -P 0.1 --interface --mode slab --box-x 5.0 --box-y 5.0 --box-z 10.0 --ice-thickness 3.0 --water-thickness 4.0 --ion-concentration 0.15 --gromacs -g --no-diagram -o ion_interface

# NaCl ions from custom molecule source
# python -m quickice -T 250 -P 0.1 --interface --mode slab --box-x 5.0 --box-y 5.0 --box-z 10.0 --ice-thickness 3.0 --water-thickness 4.0 --custom-gro quickice/data/custom/etoh.gro --custom-itp quickice/data/custom/etoh.itp --custom-placement random --custom-concentration 0.3 --ion-concentration 0.15 --ion-source custom --gromacs -g --no-diagram -o ion_custom

# NaCl ions from solute source
# python -m quickice -T 250 -P 0.1 --interface --mode slab --box-x 5.0 --box-y 5.0 --box-z 10.0 --ice-thickness 3.0 --water-thickness 4.0 --solute-type CH4 --solute-concentration 0.3 --ion-concentration 0.15 --ion-source solute --gromacs -g --no-diagram -o ion_solute

# ==============================================================================
# Full Workflow Chains
# ==============================================================================

# === Full Chain: Interface → Custom → Solute → Ion (F1) ===

# Complete F1 chain: interface + custom + solute + ion
# python -m quickice -T 250 -P 0.1 --interface --mode slab --box-x 5.0 --box-y 5.0 --box-z 10.0 --ice-thickness 3.0 --water-thickness 4.0 --custom-gro quickice/data/custom/etoh.gro --custom-itp quickice/data/custom/etoh.itp --custom-placement random --custom-concentration 0.3 --solute-type CH4 --solute-concentration 0.15 --solute-source custom --ion-concentration 0.15 --ion-source solute --gromacs -g --no-diagram -o chain_F1

# === Full Chain: Hydrate → Interface → Custom → Solute → Ion (F4) ===

# Complete F4 chain: hydrate + interface + custom + solute + ion
# python -m quickice --hydrate --lattice-type sI --guest CH4 --interface --mode slab --box-x 5.0 --box-y 5.0 --box-z 10.0 --ice-thickness 3.0 --water-thickness 4.0 --custom-gro quickice/data/custom/etoh.gro --custom-itp quickice/data/custom/etoh.itp --custom-placement random --custom-concentration 0.3 --solute-type THF --solute-concentration 0.15 --solute-source custom --ion-concentration 0.15 --ion-source solute --gromacs -g --no-diagram -o chain_F4

# ==============================================================================
# Mode Flags
# ==============================================================================

# === Mode Flags ===

# Force CLI mode (skip PySide6 import)
# python -m quickice --cli -T 250 -P 0.1 -N 96

# Force GUI mode
# python -m quickice --gui

# Show help message
# python -m quickice --help

# Show version
# python -m quickice --version

echo "This script is a reference. Uncomment commands you want to run." && exit 0
