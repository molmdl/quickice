# Research Summary: Pre-built Small Molecules for GROMACS

**Domain:** Molecular simulation tool — pre-built molecule library
**Researched:** 2026-06-12
**Overall confidence:** HIGH

## Executive Summary

The pre-built small molecules feature for QuickIce is both legally safe and technically feasible. A pure-Python AMBER→GROMACS converter (~1,000–1,500 LOC) can transform phenix geostd mol2+frcmod files into GROMACS .gro+.itp format using only numpy, networkx, and stdlib — no chemistry toolkits required. The conversion is a format transformation with unit conversion, and all key formulas (LJ Rmin/2→σ, bond/angle ½ factor, dihedral idivf division) have been verified against existing QuickIce reference files (ch4.itp, thf.itp, etoh.itp). Sourcing data from the phenix geostd repository (BSD-3-Clause) provides a clear legal path for redistribution under MIT, with the FSF's own GPL FAQ confirming that antechamber output files inherit the input data's license rather than being GPL-encumbered.

However, two critical findings demand attention before proceeding. First, the PDB Chemical Component Dictionary has a catastrophic 25% name-collision rate — codes like CH4 map to a 33-atom peptide-like molecule, not methane; THF maps to a 55-atom ligand, not simple tetrahydrofuran. This means automated identity verification (atom count, element composition, GAFF2 type set) is mandatory for every bundled molecule, and ~15 critical hydrate guests (noble gases, propane, nitrogen, isobutane) are entirely absent from geostd and require manual creation. Second, and most urgently, the TIP4P-ICE LJ parameters in QuickIce's generated .top files appear to be 1,000× too small for σ and 10^6× too small for ε — effectively eliminating ALL water-water van der Waals interactions in every simulation. This is a pre-existing bug (P16) that affects all QuickIce output and must be verified and fixed before releasing the pre-built molecule feature.

The recommended scope is 100–150 curated molecules (~1–2 MB bundle), organized into 7 categories (gases, solvents, hydrate guests, alkanes, amino acid fragments, drug-like, ions), with a JSON index for search/filter and a GUI browse panel integrated into the existing CustomMoleculePanel. Total new code is estimated at ~2,830 LOC across converter (~2,000), library backend (~200), and GUI (~450), with no new external dependencies and no breaking changes to existing functionality.

## Key Findings

**License:** Source from phenix geostd (BSD-3-Clause) — legally safe, FSF FAQ confirms antechamber output inherits input license, GAFF2 atom types and individual parameters likely not copyrightable as functional labels and scientific facts.

**Conversion:** Pure Python AMBER→GROMACS converter is fully feasible at ~1,000–1,500 LOC; 82% of geostd molecules convert with penalty ≤ 6; 96 unique GAFF2 atom types; key formulas verified against ch4.itp, thf.itp, etoh.itp.

**Architecture:** 5-phase implementation totaling ~2,830 LOC; bundled in `quickice/data/molecules/` with JSON index; active `[atomtypes]` in ITPs (existing dedup pipeline handles it); CustomMoleculeConfig unchanged — library just sets gro_path/itp_path; no new dependencies.

**Critical pitfall:** TIP4P-ICE LJ parameters in generated .top files are 1000× too small (σ=0.31668e-3 instead of 0.31668 nm) — this effectively eliminates ALL water LJ interactions in ALL existing QuickIce simulations and demands URGENT investigation.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **P16 Investigation & Fix** - TIP4P-ICE LJ bug is pre-existing and affects ALL simulations; must verify and fix before any new feature release
   - Addresses: Critical correctness of all QuickIce output
   - Avoids: Releasing molecules library with wrong water-guest cross-interactions

2. **Converter Core** - Foundation for everything else; all unit conversion pitfalls concentrated here
   - Addresses: AMBER→GROMACS format conversion (core feature)
   - Avoids: P9 (LJ convention), P10 (½ factor), P11 (idivf), P7 (ATTN detection)

3. **Molecule Bundle Curation** - Data-only; curation quality is the bottleneck, not code
   - Addresses: Pre-built molecule library data
   - Avoids: P2 (PDB name collision 25% — mandatory verification), P8 (high penalty — exclude >50)

4. **Library Backend + GUI Integration** - Backend access and search/browse panel
   - Addresses: GUI search/browse, programmatic molecule selection
   - Avoids: P3 (atomtypes convention — use active, dedup handles it), P1 (1-4 scaling — document scope)

5. **Polish & Release** - Quality pass, preview, warnings, attribution, E2E tests
   - Addresses: UX polish, edge cases
   - Avoids: P5 (comb-rule mismatch — document), P17 (GAFF2 table accuracy — validate), P19 (improper dedup)

**Phase ordering rationale:**
- P16 fix comes FIRST because it affects ALL existing functionality — it would be irresponsible to add new features atop broken water LJ
- Converter comes before data because the bundle is generated by the converter
- Curation comes before GUI because you need data before you can browse it
- Backend + GUI combined because they're tightly coupled (GUI depends on backend API)
- Polish is last — ship a working MVP first, iterate

**Research flags for phases:**
- Phase 1 (P16): **Needs immediate investigation** — verify actual bug by running a test simulation and comparing energies
- Phase 2 (Converter): **Standard patterns** — formulas are well-documented and verified; unlikely to need research
- Phase 3 (Curation): **Needs phase-specific research** — each molecule requires identity verification; some need manual creation with GAFF2 or literature parameters
- Phase 4 (Backend+GUI): **Standard patterns** — Qt model/view and dialog patterns well-established in codebase
- Phase 5 (Polish): **Standard patterns** — routine QA

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| License | HIGH | FSF FAQ + phenix geostd BSD-3 precedent + scientific facts analysis all consistent |
| Conversion | HIGH | All formulas verified against existing QuickIce ITP files; 82% clean rate from statistical survey |
| Architecture | HIGH | Based on direct codebase analysis; no new dependencies; existing pipeline handles both atomtype conventions |
| Pitfalls | HIGH | 20 pitfalls catalogued with severity, status, and prevention strategies; P16 data discrepancy is unambiguous |
| Curation | MEDIUM | PDB name collision rate well-quantified (25%), but manual molecule creation for ~15 absent hydrate guests needs domain expertise |
| P16 severity | HIGH (data clear) | Values are unambiguously wrong by 1000×/10^6×; but whether there's a compensating mechanism needs verification |

## Quick Wins

- **P16 fix:** The TIP4P-ICE LJ fix is likely a single-line change in `gromacs_writer.py` (correct the scientific notation: `0.31668e-3` → `3.16680e-1`, `0.88216e-6` → `8.82160e-1`) plus adding a validation test. High impact, low effort.
- **ATTN molecule exclusion:** Parse for `"ATTN, need revision"` string in frcmod and skip — trivial to implement, prevents 19 broken molecules.
- **GAFF2 parameter extraction:** Programmatic extraction from `gaff2.dat` into a Python dict eliminates manual transcription risk (~2000 entries, one-time script).
- **Penalty scoring:** Parse `penalty score=` from frcmod comments and embed in index.json metadata — enables future GUI warnings with near-zero effort.

## Gaps to Address

- **P16 full verification:** The LJ value discrepancy is clear from file comparison, but we haven't traced the actual gromacs_writer.py code path to confirm the root cause or check for compensating mechanisms. Run a test simulation with corrected values and compare water density.
- **phenix geostd coverage:** We know AMBER geostd has 28,745 molecules, but haven't confirmed how many of these are also in phenix geostd (the BSD-3-Clause-licensed source). If coverage is significantly smaller, we may need to contact the AMBER team for redistribution permission.
- **Full GAFF2 parameter table:** Only 7 of 96 atom types have been verified against QuickIce ITP files. The remaining 89 types must be extracted from `gaff2.dat` and validated.
- **Manual molecule parameters:** The ~15 molecules absent from geostd (noble gases, propane, N2, O2, etc.) need parameters sourced from literature or generated with antechamber. Noble gases use LJ-only parameters from published papers; alkanes need GAFF2 parametrization.
- **Ions (Cl⁻, Na⁺, K⁺):** Not in PDB CCD. Need Madrid2019 parameters, which are a different force field. How to integrate these into a GAFF2-focused library needs design.
