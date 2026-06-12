# Research Synthesis: Pre-built Small Molecules for GROMACS

**Project:** QuickIce
**Feature:** Pre-built small molecules converted from phenix geostd to GROMACS format
**Synthesized:** 2026-06-12
**Sources:** LICENSE.md, SUMMARY-A.md, FORMAT-CONVERSION.md, SUMMARY-B.md, RELEVANCE-FILTER.md, SUMMARY-C.md, ARCHITECTURE.md, PITFALLS.md

---

## Executive Summary

A pure-Python AMBER→GROMACS converter (~1,000–1,500 LOC) bundled with a curated library of 100–150 pre-built molecules is **fully feasible** and legally safe when sourced from the phenix geostd repository (BSD-3-Clause). The conversion is a format transformation with unit conversion, not a chemistry problem — no RDKit, ParmEd, or ACPYPE needed. The key technical challenges are well-understood: AMBER's dihedral convention (multi-term, idivf division, wildcards), LJ parameter convention (Rmin/2 → σ conversion), and the ½ factor difference in bond/angle force constants. All conversion formulas have been **verified** against existing QuickIce ITP files (ch4.itp, thf.itp, etoh.itp). The PDB CCD has a **catastrophic 25% name-collision rate** — codes like CH4 and THF map to complex PDB ligands, not the simple molecules scientists expect — making automated verification mandatory for every bundled molecule. About 15 critical hydrate guests (noble gases, propane, nitrogen, simple THF) are absent from geostd and require manual creation; QuickIce already ships two of these (ch4.itp, thf.itp). The most critical finding is **P16: TIP4P-ICE LJ parameters in generated .top files appear to be 1,000× too small**, which would make ALL TIP4P-ICE water LJ interactions effectively zero — this demands urgent verification as it affects ALL existing QuickIce output, not just this feature.

---

## Decision Matrix

| # | Key Question | Answer | Confidence | Source |
|---|-------------|--------|------------|--------|
| 1 | Can we legally redistribute geostd-derived data under MIT? | **YES** — source from phenix geostd (BSD-3-Clause), include attribution | HIGH | LICENSE.md, SUMMARY-A.md |
| 2 | Is pure Python conversion feasible without chemistry toolkits? | **YES** — format transformation only, ~1,000–1,500 LOC | HIGH | FORMAT-CONVERSION.md, SUMMARY-B.md |
| 3 | How many GAFF2 atom types needed? | **96** unique types in geostd; ~70 needed for typical molecules | HIGH | FORMAT-CONVERSION.md §5 |
| 4 | What % of geostd molecules convert cleanly? | **82%** with penalty ≤ 6; 12% have high penalty; 0.07% have ATTN entries | HIGH | FORMAT-CONVERSION.md §13 |
| 5 | Can PDB CCD codes be trusted as molecule names? | **NO** — 25% false-positive rate; CH4≠methane, THF≠simple THF | HIGH | RELEVANCE-FILTER.md §1-2 |
| 6 | How many hydrate guests exist in geostd? | **~50%** — critical absences: methane, simple THF, propane, N2, Xe, isobutane | HIGH | RELEVANCE-FILTER.md §1 |
| 7 | What ITP convention for bundled molecules? | **Active [atomtypes]** — self-describing, scalable, existing dedup handles it | MEDIUM | ARCHITECTURE.md §4 (conflicts with PITFALLS.md P3 — see below) |
| 8 | Bundle size estimate? | **~1–2 MB** for 100–200 molecules — negligible | HIGH | RELEVANCE-FILTER.md §6 |
| 9 | New external dependencies? | **NONE** — numpy + networkx already in requirements.txt | HIGH | ARCHITECTURE.md §9 |
| 10 | Is TIP4P-ICE LJ in .top files correct? | **LIKELY NOT** — σ appears 1000× too small, ε 10^6× too small | HIGH (data clear) | PITFALLS.md P16 |

---

## Resolved Disagreement: ITP Atomtypes Convention

**Architecture Agent (D):** Recommends ACTIVE `[atomtypes]` in bundled ITPs.
**Pitfalls Agent (E):** Recommends COMMENTED-OUT `[atomtypes]` (P3), for consistency with ch4.itp/thf.itp.

**Resolution: ACTIVE `[atomtypes]` is recommended.**

Rationale:
1. **Scalability:** With 100–150 molecules using 30+ unique GAFF2 atom types, maintaining a hardcoded lookup table in `gromacs_writer.py` is unsustainable. Active atomtypes in each ITP makes each file self-describing.
2. **Existing pipeline handles it:** `parse_itp_atomtypes()` extracts types, deduplication (Bug 3 fix pattern) prevents duplicates, and `comment_out_atomtypes_in_itp()` strips them from the output copy. This pipeline is already tested and working.
3. **Backward compatibility preserved:** Existing ch4.itp/thf.itp with commented atomtypes continue to work. The hardcoded atomtype table for CH4/THF in gromacs_writer.py still functions. No breaking changes.
4. **The real P3 concern (grompp "Atomtype defined more than once") is already solved:** The export pipeline's `comment_out_atomtypes_in_itp()` function removes active atomtypes from the ITP copy placed in the output directory, so the parent .top is the sole source of truth for the final simulation.

---

## Recommended Feature Scope

### BUILD (v1.0)

| Component | LOC (est.) | Description |
|-----------|-----------|-------------|
| `quickice/converters/` package | ~2,000 | Pure Python AMBER→GROMACS converter |
| mol2_parser.py | ~200 | MOL2 file parser |
| frcmod_parser.py | ~150 | FRCMOD file parser |
| gaff2_params.py | ~300 | Bundled GAFF2 parameter table |
| gromacs_writer.py (local) | ~250 | GRO/ITP string writer |
| amber_to_gromacs.py | ~1,200 | Core converter orchestration |
| converters.py | ~100 | CLI batch converter |
| `quickice/data/molecules/` | ~1–2 MB | 100–150 curated molecules with index.json |
| `quickice/structure_generation/molecule_library.py` | ~200 | Programmatic library access |
| `quickice/gui/molecule_library_dialog.py` | ~300 | Search/browse GUI dialog |
| `quickice/gui/molecule_library_model.py` | ~150 | Qt model for filtered list |
| `ATTRIBUTION.md` | ~30 | BSD-3-Clause attribution + citations |
| **TOTAL NEW CODE** | **~2,830** | |

### DEFER to v2.0+

- Multi-molecule selection in GUI (currently single custom molecule at a time)
- 3D structure preview in library dialog (reuse `create_custom_molecule_actor()`)
- Category icons in library dialog
- Recently-used molecules quick-access
- Penalty score badges/warnings in GUI
- On-demand download of full 28,745-molecule geostd
- OPLS-AA or CHARMM molecule support (different 1-4 scaling)
- Auto-detection of force field family conflicts

### NEVER DO

- Bundle data from `amber_geostd.tar.bz2` (no explicit license)
- Include molecules with ATTN entries or penalty > 50
- Use RDKit, ParmEd, or ACPYPE as converter dependencies

---

## Suggested Phase Structure

### Phase 1: Converter Core (No GUI impact)
**Rationale:** The converter is the foundation — it must be correct before anything else depends on it. All unit conversion pitfalls (P9, P10, P11) are concentrated here.

- **Delivers:** `quickice/converters/` package, CLI batch tool, GAFF2 parameter table
- **Features addressed:** AMBER→GROMACS format conversion
- **Pitfalls to avoid:**
  - P9 (LJ Rmin/2 → σ conversion) — verified formula, but implement carefully
  - P10 (½ factor in bond/angle) — verified formula, but implement carefully
  - P11 (idivf division for dihedrals) — must divide by idivf
  - P7 (ATTN molecules) — must detect and skip
- **Validation:** Convert 10–20 geostd molecules, compare against Sobtop reference ITPs (ch4.itp, thf.itp, etoh.itp). Verify 82%+ clean conversion rate on full geostd.
- **LOC:** ~2,000

**Research flag: Standard patterns** — conversion formulas are well-documented and verified; no deep research needed.

### Phase 2: Molecule Bundle Curation (Data-only)
**Rationale:** Curation quality is the bottleneck, not code. Must verify every molecule's identity against PDB CCD before bundling.

- **Delivers:** `quickice/data/molecules/` with 100–150 curated molecules, `index.json`, `ATTRIBUTION.md`
- **Features addressed:** Pre-built molecule library data
- **Pitfalls to avoid:**
  - P2 (PDB name collision 25%) — **mandatory automated verification: atom count + element composition + GAFF2 type set for every molecule**
  - P7 (ATTN molecules) — exclude all 19
  - P8 (high penalty) — exclude molecules with any penalty > 50; include ≤6 as "clean", 6–50 with warning metadata
  - P12 (residue name conflicts) — avoid SOL, HOH, WAT, NA, CL, K, CAL
  - P13 (atom name length) — truncate to 5 chars, strip apostrophes
- **Manual creation needed:** ~15 molecules absent from geostd (noble gases, propane, N2, O2, isobutane, cyclopentane, neopentane, adamantane, acetone, H2, Cl⁻/Na⁺/K⁺ ions)
- **Validation:** Load each molecule through existing CustomMoleculePanel upload flow. Run `gmx grompp` on each.
- **LOC:** ~0 (data + JSON manifest only)

**Research flag: Needs phase-specific research** — the 2-pass curation (structure filter + manual verification) requires domain expertise for each molecule.

### Phase 3: P16 — TIP4P-ICE LJ Bug Investigation & Fix (URGENT)
**Rationale:** The TIP4P-ICE LJ values in generated .top files appear to be 1000× too small (σ) and 10^6× too small (ε). This is a **critical existing bug** affecting ALL QuickIce simulations, not just this feature. It must be verified and fixed before releasing pre-built molecules because users will trust the atomtype definitions for both water AND guests.

- **Delivers:** Fixed `gromacs_writer.py`, regression test for TIP4P-ICE LJ values
- **What to investigate:**
  - Compare `gromacs_writer.py` output OW_ice σ=0.31668e-3 vs. correct σ=0.31668
  - Compare ε=0.88216e-6 vs. correct ε=0.88211
  - Check all 6 TOP-writing functions in gromacs_writer.py (lines 541, 974, 1253)
  - Verify against Abascal 2005 TIP4P-ICE paper: σ_O = 3.1668 Å, ε_O/k_B = 106.1 K
  - Add validation test: assert σ > 0.01 nm and ε > 0.001 kJ/mol for all atomtypes
- **Validation:** Run short MD with fixed values, check water density at 270 K matches ~990 kg/m³

**Research flag: URGENT — needs immediate investigation** — this affects all existing QuickIce output.

### Phase 4: Programmatic Library Access + GUI Integration
**Rationale:** Once data exists and is validated, backend access and GUI can be built together since the GUI depends on the backend.

- **Delivers:** `molecule_library.py`, `MoleculeLibraryEntry` dataclass, `MoleculeLibraryDialog`, modified `CustomMoleculePanel`
- **Features addressed:** GUI search/browse, programmatic molecule selection
- **Pitfalls to avoid:**
  - P1 (1-4 scaling) — document GAFF2+TIP4P-ICE+Madrid2019 scope, warn on mixing
  - P3 (atomtypes convention) — use active atomtypes, existing dedup handles it
  - P2 (name collision) — show verified name + formula + atom count in GUI
- **Validation:** E2E test: select molecule → insert → export → validate with `gmx grompp`
- **LOC:** ~650 (200 backend + 450 GUI)

**Research flag: Standard patterns** — Qt model/view and dialog patterns are well-established in the existing codebase.

### Phase 5: Polish, Edge Cases & Release
**Rationale:** Final quality pass before users see the feature.

- **Delivers:** Preview, penalty warnings, attribution in exported .top, full E2E tests
- **Features addressed:** UX polish, edge cases
- **Pitfalls to avoid:**
  - P5 (combining rule mismatch) — document GAFF2-only scope
  - P6 (atom type name collision) — document naming convention
  - P14 (GRO box = 0.0) — document convention
  - P17 (GAFF2 table accuracy) — cross-validate against gaff2.dat
  - P19 (improper wildcard dedup) — ensure deduplication
- **Validation:** Full regression suite, `gmx grompp` on all 150 molecules

**Research flag: Standard patterns** — QA and polish are routine.

---

## Critical Discoveries Affecting Other Features

### P16: TIP4P-ICE LJ Parameters 1000× Too Small (URGENT)

**Discovery:** The `[ atomtypes ]` section in QuickIce-generated .top files writes TIP4P-ICE LJ parameters with σ=0.31668e-3 nm and ε=0.88216e-6 kJ/mol, but the correct values are σ=0.31668 nm and ε=0.88211 kJ/mol. This means:
- **ALL TIP4P-ICE water LJ interactions are effectively zero**
- Water-water van der Waals forces are eliminated
- Guest-host van der Waals stabilization (the primary hydrate stabilizing force) is destroyed
- Simulations may "appear to work" because PME electrostatics still provides cohesion, but thermodynamic properties (dissociation pressure, hydration free energy, cage occupancy) would be catastrophically wrong

**Impact:** This affects **ALL existing QuickIce simulations** that use TIP4P-ICE water, not just the pre-built molecule feature.

**Action required:** IMMEDIATE investigation of `gromacs_writer.py` lines 541, 974, and 1253. Compare output against TIP4P-ICE reference (Abascal 2005, σ_O = 3.1668 Å, ε_O/k_B = 106.1 K → ε = 0.882 kJ/mol).

**Confidence:** HIGH — the discrepancy is clear from direct file inspection. The commented-out values in tip4p-ice.itp (line 4) match the Abascal paper; the active values in .top files are 1000× smaller.

### PDB Code Name Collision (25% False-Positive Rate)

**Discovery:** The PDB CCD systematically reuses short chemical formula codes for complex PDB ligands. Of 39 molecules checked, 10 have misleading codes. This is a domain-wide risk for anyone working with PDB CCD data.

**Impact on other features:** Any feature that uses PDB CCD codes as molecule identifiers (e.g., auto-import from PDB) MUST include identity verification. Never trust a PDB code alone.

---

## Open Questions Requiring User Input or Further Investigation

1. **P16 Verification (URGENT):** Is the TIP4P-ICE LJ value discrepancy a real bug in gromacs_writer.py, or is there a compensating mechanism? Must verify by tracing the actual code path that generates .top files and running a validation simulation.

2. **phenix geostd coverage:** How many of the ~150 target molecules have entries in phenix geostd (vs. AMBER geostd)? The license analysis recommends phenix geostd as the source, but its coverage may be smaller than AMBER geostd's 28,745 molecules.

3. **Manual molecule creation:** For the ~15 molecules absent from geostd (noble gases, propane, N2, etc.), should we:
   - (a) Create them manually with GAFF2 parameters using antechamber?
   - (b) Use literature LJ parameters for noble gases (Xe, Ar, Kr)?
   - (c) Provide them as separate downloads rather than bundling?
   - **Recommendation:** (b) for noble gases (simpler, more accurate); (a) for alkanes (GAFF2 gives consistent parameters).

4. **gaff2.dat version pinning:** The GAFF2 parameter table must be extracted from a specific gaff2.dat version (recommend v2.20 from AmberTools24). Should we pin this version or support multiple versions? **Recommendation:** Pin to v2.20 and document it.

5. **Active vs. commented atomtypes — final decision:** While the synthesis recommends active atomtypes, the existing QuickIce convention (ch4.itp, thf.itp) uses commented. Should we migrate existing files or maintain both? **Recommendation:** Keep both for now; active for new bundled ITPs, commented for legacy ITPs.

6. **Ions from Madrid2019:** Cl⁻, Na⁺, K⁺ are not in PDB CCD. Should the pre-built library include them? They're needed for many MD simulations but require different force field parameters (Madrid2019, not GAFF2). **Recommendation:** Include them in the library but in a separate "ions" category with Madrid2019 parameters, clearly labeled as non-GAFF2.

---

## Cross-References to Detailed Research

| Topic | Primary File | Section |
|-------|-------------|---------|
| License provenance chain | LICENSE.md | §1–7, Summary Verdict Table |
| phenix geostd BSD-3 precedent | LICENSE.md | §2 ("Critical Detail") |
| FSF GPL FAQ on output | LICENSE.md | §3 (FAQ quotes) |
| mol2 format anatomy | FORMAT-CONVERSION.md | §1 |
| frcmod format anatomy | FORMAT-CONVERSION.md | §2, Appendix B |
| LJ Rmin/2 → σ conversion derivation | FORMAT-CONVERSION.md | §6 (detailed derivation) |
| Bond/angle ½ factor derivation | FORMAT-CONVERSION.md | §6 (verified) |
| Dihedral idivf handling | FORMAT-CONVERSION.md | §7 |
| Pairs generation algorithm | FORMAT-CONVERSION.md | §8 |
| Improper handling (funct=9) | FORMAT-CONVERSION.md | §9 |
| GAFF2 LJ parameter table | FORMAT-CONVERSION.md | §10, Appendix D |
| Full conversion algorithm | FORMAT-CONVERSION.md | §11 |
| Edge cases (10 cases) | FORMAT-CONVERSION.md | §12 |
| Penalty score distribution | FORMAT-CONVERSION.md | §13 |
| LOC estimate (1,000–1,500) | FORMAT-CONVERSION.md | §16 |
| PDB code name collision table | RELEVANCE-FILTER.md | §1–2 |
| Absent hydrate guest list | RELEVANCE-FILTER.md | §3, §5 |
| Bundle size estimates | RELEVANCE-FILTER.md | §6 |
| Category taxonomy (7 categories) | RELEVANCE-FILTER.md | §5 |
| Component architecture diagram | ARCHITECTURE.md | §1 |
| File organization | ARCHITECTURE.md | §2 |
| ITP convention analysis | ARCHITECTURE.md | §4 |
| Converter API design | ARCHITECTURE.md | §5 |
| GUI integration plan | ARCHITECTURE.md | §6 |
| Export pipeline compatibility | ARCHITECTURE.md | §8 |
| Phase implementation sequence | ARCHITECTURE.md | §10 |
| All 20 pitfalls | PITFALLS.md | P1–P20 |
| TIP4P-ICE LJ bug (P16) | PITFALLS.md | §P16 |
| Phase-specific warnings table | PITFALLS.md | Phase-Specific Warnings |
