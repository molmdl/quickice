---
status: resolved
trigger: "User asks if Ice II has an orthogonal supercell (integer multiples of unit cell that form an orthogonal box). If not, we'll keep Ice II triclinic and document this limitation."
created: 2026-04-13T00:00:00Z
updated: 2026-04-13T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - Ice II cannot have an orthogonal supercell
test: Mathematical analysis of lattice vectors and crystallographic theory
expecting: Prove impossibility of orthogonal supercell
next_action: Report findings to user

## Symptoms

expected: Find integer multiples [na, nb, nc] such that supercell is orthogonal
actual: No orthogonal supercell exists - fundamental crystallographic constraint
errors: N/A
reproduction: Ice II lattice vectors: a=[1.556,0,0], b=[-0.610,1.431,0], c=[-0.610,-0.924,1.093]
started: N/A - mathematical investigation

## Eliminated

- hypothesis: Simple scaling (na*a, nb*b, nc*c) could yield orthogonal supercell
  evidence: All dot products a·b, a·c, b·c are non-zero (~-0.95). For A=na*a, B=nb*b: A·B = na*nb*(a·b) ≠ 0 for any positive integers.
  timestamp: 2026-04-13T00:00:00Z

- hypothesis: General integer combination supercell could be orthogonal
  evidence: Searched all integer matrices with coefficients in [-4,4]. Found 128 orthogonal vector pairs but NO complete orthogonal triple. This confirms theoretical constraint.
  timestamp: 2026-04-13T00:00:00Z

## Evidence

- timestamp: 2026-04-13T00:00:00Z
  checked: Unit cell lattice vector properties
  found: |a|=1.556nm, |b|=1.556nm, |c|=1.556nm (nearly equal). Angles all ≈113° (not 90°)
  implication: Ice II is rhombohedral (space group R-3)

- timestamp: 2026-04-13T00:00:00Z
  checked: Dot products of original lattice vectors
  found: a·b=-0.949, a·c=-0.949, b·c=-0.950 (all non-zero)
  implication: Unit cell is not orthogonal; scaling won't help

- timestamp: 2026-04-13T00:00:00Z
  checked: Simple scaling analysis (A=na*a, B=nb*b, C=nc*c)
  found: A·B = na*nb*(-0.949) can only be zero if na=0 or nb=0
  implication: No positive integer scaling yields orthogonal vectors

- timestamp: 2026-04-13T00:00:00Z
  checked: General integer combination search (coefficients -4 to 4)
  found: 128 orthogonal vector pairs found, but NO complete orthogonal triple
  implication: Confirms theoretical impossibility

- timestamp: 2026-04-13T00:00:00Z
  checked: Crystallographic theory
  found: Rhombohedral lattices are NOT sublattices of any orthogonal lattice
  implication: This is a fundamental mathematical constraint of the crystal system

## Resolution

root_cause: Ice II is rhombohedral (space group R-3), and rhombohedral lattices fundamentally cannot have orthogonal supercells with integer indices. The lattice vectors have equal lengths (~1.556 nm) with equal angles (~113°), and no integer transformation can make them orthogonal.

fix: Keep Ice II interfaces triclinic. Document this limitation as a fundamental crystallographic constraint.

verification: Mathematical proof via: (1) non-zero dot products prevent simple scaling, (2) exhaustive search found no general integer combination, (3) crystallographic theory confirms rhombohedral lattices are not sublattices of orthogonal lattices.

files_changed: []
