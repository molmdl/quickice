# Research Summary: Pre-built Small Molecules Relevance Filtering

**Project:** QuickIce — Pre-built small molecules for hydrate/clathrate MD
**Researched:** 2026-06-12
**Mode:** Ecosystem (relevance filtering)
**Overall confidence:** HIGH (direct archive scanning)

## Verdict

Bundling a curated subset of 100–200 pre-built molecules from the AMBER geostd archive is **feasible and worthwhile**, but the geostd alone covers only ~50% of hydrate-relevant molecules. The PDB CCD naming creates a severe "name collision" problem — 25% of codes that look like simple molecules (CH4, THF, XEN, NEO, CPN, ADA, PPR, ETA, AR1, NE1) are actually complex PDB ligands. The most critical hydrate guests (simple methane, simple THF, propane, nitrogen, xenon, isobutane, noble gases) are **absent** from the geostd because they are gases, not protein ligands. QuickIce already ships methane and THF .itp files; the remaining ~15 missing molecules require manual GAFF2 parametrization or LJ-only creation. The recommended strategy is a **2-pass approach**: structure-based filtering (atom count ≤30, CHONS only) to identify candidates from the ~8,300 small molecules, followed by manual verification of each molecule's actual identity against the PDB CCD. The final curated bundle would be ~1–2 MB (negligible), with the bottleneck being curation quality, not data size.

## What's Missing (Must Come from Elsewhere)

- **Methane, simple THF** — already shipped by QuickIce (ch4.itp, thf.itp)
- **Propane, N2, O2, H2, Xe, Ar, Kr, Ne** — require manual creation (simple GAFF2 or LJ-only)
- **Isobutane, cyclopentane, neopentane, adamantane** — require manual GAFF2 parametrization
- **Acetone** — PDB ACN = acetic acid, not acetone
- **Ions (Cl⁻, Na⁺, K⁺)** — not in PDB CCD; use standard MD ion parameters

## Recommended Scope

**100–150 molecules** total, organized by category:
- 15 hydrate guests (sI/sII/sH + noble gases)
- 25 solvents (alcohols, ethers, aprotic solvents)
- 10 simple gases
- 10 ions
- 15 alkanes/cyclic alkanes
- 20 amino acid fragments
- 20 drug-like small molecules
- 10 nucleotide components
- 10–25 "utility" molecules (buffers, cofactors, etc.)

This is the right range: enough to populate a search panel meaningfully, few enough to curate with confidence. 200+ would dilute quality; 50 would feel incomplete.
