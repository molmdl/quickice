# Research Summary: Custom Guest Molecule in Hydrate

**Domain:** Clathrate hydrate generation with arbitrary user-provided guest molecules
**Researched:** 2026-06-22
**Overall confidence:** HIGH

## Executive Summary

Custom guest molecule insertion into GenIce2-generated hydrate cages is **fully feasible** using two complementary methods. The primary method (Approach A) injects a custom `genice2.molecules.Molecule` subclass into `sys.modules` before calling GenIce2, letting GenIce2 handle cage center placement, rotation, occupancy, and GRO formatting automatically. The fallback method (Approach B) extracts cage center positions from GenIce2's `repcagepos` attribute after generation and uses QuickIce's own insertion logic — this gives full control over placement but requires reimplementing cage occupancy assignment.

Both approaches require bridging user-provided `.gro` + `.itp` files into GenIce2's `Molecule` format (`sites_` centered at origin in nm, `labels_` from ITP atom names, `name_` truncated to ≤5 chars). GROMACS export requires ITP transformation (`_H` suffix moleculetype, atomtypes commented out, comb-rule=2 validation). The GRO 5-character residue name limit is the tightest constraint — base names must be ≤3 characters when including `_H` suffix.

No additional libraries are needed. Everything uses the existing `environment.yml` stack (GenIce2, numpy, scipy, PySide6, VTK).

## Key Findings

**Injection method:** `sys.modules` injection of `types.ModuleType("genice2.molecules.<name>")` works end-to-end. GenIce2's `safe_import` checks `sys.modules` first via `importlib.import_module`, so a pre-registered module is found without filesystem access.

**Fallback method:** `ice.repcagepos` and `ice.repcagetype` survive the entire `generate_ice()` pipeline and can be read afterward. Fractional→absolute conversion via `ice.repcell.rel2abs()`. This makes Approach B a 3-line extraction.

**GRO name limit:** GROMACS 2023.5 rejects GRO files with >5-character residue names. With `_H` suffix, base names must be ≤3 characters (e.g., `ET_H`, `PR_H`). GenIce2 does NOT enforce this — QuickIce must validate.

**ITP transformation:** User's `.itp` needs `_H` suffix on moleculetype name, atomtypes commented out (moved to main `.top`), residue names matching moleculetype name. The existing `comment_out_atomtypes_in_itp()` function handles atomtypes removal.

**comb-rule=2 validation:** A/B format atomtypes (values >>10 in column 7) are incompatible with Lorentz-Berthelot combining rules. QuickIce must detect and reject/warn.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Phase 1: GRO/ITP → GenIce2 Molecule Bridge** — Core conversion + registration
   - Addresses: R1 (sys.modules injection), R2 (GRO→Molecule conversion)
   - Avoids: GenIce2 API coupling (sys.modules injection is standard Python)
   - Deliverable: `gro_itp_to_genice2_molecule()` + `register_genice2_molecule()`

2. **Phase 2: HydrateGenerator Integration** — Wire custom guest into hydrate pipeline
   - Addresses: R1 (end-to-end GenIce2 flow), R4 (GROMACS export)
   - Depends on: Phase 1
   - Deliverable: Custom guest support in `HydrateStructureGenerator._run_via_api()`

3. **Phase 3: GROMACS Export Pipeline** — ITP transformation + atomtypes merging
   - Addresses: R4 (ITP validation, atomtypes dedup, comb-rule check)
   - Depends on: Phase 2
   - Deliverable: Custom hydrate guest ITP generation, `_H` suffix handling

4. **Phase 4: GUI/CLI Integration** — UI for custom guest upload in Hydrate tab
   - Addresses: User workflow (upload .gro+.itp, select cage occupancy)
   - Depends on: Phases 1-3
   - Deliverable: Hydrate tab custom guest panel, CLI `--custom-guest` flag

5. **Phase 5: Cage-Guest Size Validation** — Diameter check + warning
   - Addresses: R3 (cage diameter references, guest diameter computation)
   - Can be developed in parallel with Phase 4
   - Deliverable: Validation that guest fits in selected cage type

**Phase ordering rationale:**
- Phase 1 must come first (conversion bridge is the foundation)
- Phase 2 depends on Phase 1 (needs the bridge to call GenIce2)
- Phase 3 depends on Phase 2 (needs hydrate generation output for export)
- Phase 4 depends on all above (UI integrates the pipeline)
- Phase 5 is independent of UI (validation is a pure computation)

**Research flags for phases:**
- Phase 2: LOW risk — GenIce2 API is stable, sys.modules injection verified
- Phase 4: MEDIUM risk — GUI integration needs careful thread-safety for sys.modules injection
- Phase 5: LOW risk — cage diameters are well-documented in hydrate literature

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| sys.modules injection | HIGH | End-to-end tested with GenIce2 CS1 lattice |
| mol[file=path] syntax | HIGH | End-to-end tested; secondary method |
| Cage center extraction | HIGH | Runtime verified for all 3 hydrate types |
| GRO→Molecule conversion | HIGH | Working code tested with ethanol example |
| GROMACS export requirements | HIGH | All from source code reading + existing patterns |
| GRO residue name limit | HIGH | GROMACS 2023.5 fatal error reproduced |
| Cage diameter validation | MEDIUM | Values from training data, cross-verified but not primary-sourced |
| Thread safety (sys.modules) | MEDIUM | Not tested in QThread context; likely needs lock or unique naming |

## Gaps to Address

- Thread safety of `sys.modules` injection in QThread context (HydrateWorker)
- Atom ordering mismatch between GRO and ITP (rare but possible)
- Physical fit validation for large guests in small cages (GenIce2 doesn't check)
- Whether custom guest can simultaneously be hydrate guest AND liquid solute
- sH lattice uses deprecated `cages` string format — may need upstream fix

## Source Files

| File | Key Content |
|------|-------------|
| R1-SAFE-IMPORT-FEASIBILITY.md | sys.modules injection, mol plugin, monkey-patch comparison |
| R2-GRO-MOLECULE-BRIDGE.md | gro_itp_to_genice2_molecule() code, .mol conversion, element inference |
| R3-CAGE-CENTER-EXTRACTION.md | repcagepos access, lattice cagepos, cage diameters, assess_cages() |
| R4-GROMACS-EXPORT.md | ITP validation checklist, atomtypes merging, comb-rule-2 detection |
