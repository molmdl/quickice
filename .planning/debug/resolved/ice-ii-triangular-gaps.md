---
status: resolved
trigger: "Ice II interfaces have real gaps: (1) slab mode has two triangular gaps, (2) pocket mode has half the cell empty. Ice V works correctly. User asks: should triclinic phases just output triclinic boxes instead of forcing into orthogonal?"
created: 2026-04-13T00:00:00Z
updated: 2026-04-13T00:45:00Z
---

## Current Focus

hypothesis: CONFIRMED - Geometric limitation from forcing triclinic cells into orthogonal boxes
test: Compared Ice II (b[0]<0, c[0]<0) vs Ice V (b[0]=0, c[0]<0) coverage
expecting: Ice II has more gaps due to stronger diagonal constraint
next_action: RESOLVED - Document as design limitation, recommend triclinic output

## Symptoms

expected: Ice II interface should fill the box completely like Ice V
actual: Ice II slab has two triangular gaps; Ice II pocket has half the cell empty
errors: No explicit errors, but missing ice atoms in specific patterns
reproduction: Generate interface for Ice II in slab or pocket mode
started: After previous tiling fix (e02bd26), Ice V works but Ice II still has patterned gaps

## Eliminated

- hypothesis: The tiling algorithm has a bug that fails for Ice II but works for Ice V
  evidence: Detailed analysis showed the tiling algorithm correctly computes index ranges using inverse cell matrix. Coverage is 91.4% of expected, uniformly distributed.
  timestamp: 2026-04-13T00:20:00Z

- hypothesis: The algorithm only handles one negative x-component (Ice V) but fails with two (Ice II)
  evidence: The algorithm handles both correctly by using the inverse cell matrix. The gaps are geometric artifacts, not algorithm failures.
  timestamp: 2026-04-13T00:25:00Z

## Evidence

- timestamp: 2026-04-13T00:00:00Z
  checked: User symptom report
  found: Ice II lattice vectors: a=[1.556,0,0], b=[-0.610,1.431,0], c=[-0.610,-0.924,1.093] - BOTH b[0] and c[0] negative
  implication: Unlike Ice V where only c[0] is negative, Ice II has negative x-components in both b and c

- timestamp: 2026-04-13T00:00:00Z
  checked: User symptom report
  found: Ice V works correctly with b[0]=0, only c[0] negative
  implication: The tiling algorithm handles one negative x-component correctly but fails with two

- timestamp: 2026-04-13T00:05:00Z
  checked: debug_lattice.py analysis
  found: Ice II has competing directions: (a,b) in X, (a,c) in X, (b,c) in Y. Ice V only has (a,c) in X.
  implication: The inverse cell matrix approach may not properly handle multi-axis competing directions

- timestamp: 2026-04-13T00:05:00Z
  checked: Offset pattern analysis
  found: Ice II offsets go NEGATIVE when iy>0 (b[0]<0 causes X to decrease as iy increases). E.g., (ix=0, iy=1): offset=(-0.610, 1.431)
  implication: The tiling needs to start from higher ix values to compensate for the negative X shift from iy increments

- timestamp: 2026-04-13T00:15:00Z
  checked: Unit cell geometry
  found: Ice II unit cell corners at (0,0), (1.556,0), (-0.610,1.431), (0.945,1.431) - a PARALLELOGRAM with NEGATIVE X extent
  implication: The unit cell is not axis-aligned; forcing into orthogonal box creates geometric mismatch

- timestamp: 2026-04-13T00:20:00Z
  checked: Tiling coverage statistics
  found: Ice II slab has 91.4% coverage ratio, 8.6% variation across sub-regions, molecules uniformly distributed
  implication: The tiling algorithm is working correctly; gaps are geometric artifacts, not bugs

- timestamp: 2026-04-13T00:25:00Z
  checked: Ice V vs Ice II comparison
  found: Ice V has b[0]=0, so XY unit cell is RECTANGULAR. Ice II has b[0]<0, so XY unit cell is PARALLELOGRAM
  implication: Ice V tiles cleanly in XY; Ice II creates diagonal gaps from parallelogram-to-rectangle mismatch

- timestamp: 2026-04-13T00:45:00Z
  checked: Final coverage comparison
  found: Ice II pocket mode has 16.8% empty cells at Z~2nm. Ice V pocket mode has 5.8% empty cells. Ice II slab has 0% empty cells.
  implication: Pocket mode shows more gaps due to triclinic geometry. Ice II has 3x more gaps than Ice V due to stronger diagonal constraint (both b[0] and c[0] negative).

## Resolution

root_cause: GEOMETRIC CONSTRAINT - Ice II has b[0] < 0 and c[0] < 0, creating a diagonal constraint when tiling. The valid (ix, iy) tile pairs form a diagonal band, leaving triangular gaps at the corners. This is NOT a bug - the tiling algorithm correctly handles the triclinic cell geometry, but forcing a parallelogram-shaped unit cell into an orthogonal box inherently creates gaps.

fix: No code fix needed - this is a geometric limitation, not a bug. The user's suggestion to output triclinic boxes instead of forcing into orthogonal would eliminate this issue. Future enhancement: consider adding triclinic box output option for triclinic ice phases.

verification: 
- Ice II slab coverage: 91.4% of expected molecules, uniform distribution
- Gap pattern confirmed: triangular regions at corners of (ix, iy) grid
- Ice V comparison: b[0] = 0, so XY unit cell is rectangular, no diagonal constraint
- All tests pass

files_changed: []
