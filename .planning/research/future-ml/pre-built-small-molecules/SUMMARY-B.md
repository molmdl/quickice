# Research Summary: AMBER→GROMACS Conversion Feasibility

**Domain:** AMBER geostd (28,745 mol2+frcmod files) → GROMACS .gro+.itp conversion
**Researched:** 2026-06-12
**Confidence:** HIGH

## Verdict

A pure-Python AMBER→GROMACS converter is **fully feasible** using only numpy, networkx, and stdlib. No chemistry toolkits (RDKit, ParmEd, ACPYPE) are needed because the AMBER geostd files already contain complete atom typing (GAFF2), charges (abcg2), and force field modifications (frcmod). The conversion is fundamentally a **format transformation with unit conversion** — not a chemistry problem. The converter will need a bundled GAFF2 parameter table (~2000 entries from gaff2.dat) for LJ parameters and for the standard bond/angle/dihedral parameters that frcmod doesn't override. Approximately 1,000–1,500 LOC. The key technical challenges are: (1) AMBER's dihedral convention (multiple terms per quartet, idivf division, wildcards), (2) generating the explicit `[ pairs ]` section from bond topology (solvable with networkx or simple BFS), and (3) expanding AMBER improper wildcards to explicit atom quartets. About 82% of molecules will convert with clean parameters (penalty ≤ 6), another ~6% with acceptable warnings, and ~12% have high penalty scores requiring review. The 19 files with "ATTN, need revision" entries should be flagged as unconvertable. QuickIce already uses GAFF2 atom type names in GROMACS (confirmed from ch4.itp, thf.itp, etoh.itp), so no atom type remapping is needed — the converter can keep GAFF2 types as-is, matching existing convention perfectly.
