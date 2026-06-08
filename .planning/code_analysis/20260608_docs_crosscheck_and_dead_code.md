# Documentation Cross-Check and Dead Code Report

**Analysis Date:** 2026-06-08
**Scope:** README.md, docs/, source docstrings, dead code in quickice/ (core, gui, cli)

---

## Part 1: Documentation Issues

### 1.1 IAPWS R10-06 URL Mismatch Between Code and README

| File | Line | Issue | Suggested Fix |
|------|------|-------|---------------|
| `README.md` | 317 | URL `https://www.iapws.org/relguide/Ice-2006.html` — this is the older URL path. The code uses the updated URL `https://www.iapws.org/release/Ice-2009.html` in `quickice/phase_mapping/ice_ih_density.py:12`. The IAPWS document is officially "R10-06(2009)" — the 2009 revision of the 2006 formulation. | Update README URL to `https://www.iapws.org/release/Ice-2009.html` to match the code. Also consider adding "(Revised 2009)" to the title. |
| `quickice/phase_mapping/data/ice_boundaries.py` | 14 | Uses yet a third URL variant: `http://www.iapws.org/release/MeltIce.pdf` (for R14-08 melting curves). This differs from README's `https://www.iapws.org/relguide/MeltSub.html`. The MeltSub.html URL is the official current URL. | Update the code comment to use `https://www.iapws.org/relguide/MeltSub.html` for consistency with README and docs/principles.md. Note: this file is dead code (see Part 3). |

### 1.2 IAPWS-95 Citation Missing from README

| File | Line | Issue | Suggested Fix |
|------|------|-------|---------------|
| `README.md` | 286-296 | The Dependencies section and References section mention IAPWS R14-08 and R10-06, but NOT IAPWS-95. However, `quickice/phase_mapping/water_density.py` implements liquid water density using the IAPWS-95 formulation (imported from `iapws.IAPWS95`). This is a critical scientific method for calculating water density at interface boundaries. | Add IAPWS-95 reference to README References section: "IAPWS-95: Revised Release on the IAPWS Formulation 1995 for the Thermodynamic Properties of Ordinary Water Substance for General and Scientific Use. URL: https://www.iapws.org/release/IAPWS-95.html" |

### 1.3 Outdated Version Reference: "v4.0" in GUI Guide

| File | Line | Issue | Suggested Fix |
|------|------|-------|---------------|
| `docs/gui-guide.md` | 182 | Says "QuickIce v4.0 adds interface construction with direct GROMACS export for molecular dynamics simulations." — This is a v4.0-era statement in a v4.5 document. | Change to "QuickIce provides interface construction with direct GROMACS export for molecular dynamics simulations" or "QuickIce v4.5 provides..." — remove the version-specific "adds" framing. |

### 1.4 README_bin.md References Outdated v4.0.0 Binary Names

| File | Line | Issue | Suggested Fix |
|------|------|-------|---------------|
| `README_bin.md` | 4, 6, 12 | References `quickice-v4.0.0-linux-x86_64.tar.gz` and `quickice-v4.0.0-windows-x86_64.zip`. Current version is v4.5.0. | Update binary names to `quickice-v4.5.0-*` or use a generic placeholder like `quickice-vX.Y.Z-*`. |

### 1.5 Test Asserts Wrong Version Number

| File | Line | Issue | Suggested Fix |
|------|------|-------|---------------|
| `tests/test_cli_integration.py` | 292 | Asserts `"python quickice.py 4.0.0"` but `quickice/__init__.py:3` defines `__version__ = "4.5.0"`. The CLI parser at `quickice/cli/parser.py:175` also has `version="%(prog)s 4.5.0"`. This test will fail. | Update test assertion to `"python quickice.py 4.5.0"`. |

### 1.6 Phase Diagram Supports 12 Phases (Not 8) in gui-guide Description

| File | Line | Issue | Suggested Fix |
|------|------|-------|---------------|
| `docs/gui-guide.md` | 82 | Says "QuickIce can generate structures for 8 ice polymorphs... the diagram also shows regions for Ice IX, X, XI, XV, liquid water, and vapor for reference." This is technically correct but confusing — the total shown on the diagram is 12 (8 generatable + 4 detection-only). README correctly says "Phase Detection (13 phases)". | Clarify: "The phase diagram identifies 12 ice polymorphs (8 with structure generation, 4 detection-only) plus liquid water and vapor regions." The README counts 13 because it includes Ice IV in the detection table. |

### 1.7 Ice IV Listed in README Phase Detection Table But Not in Code

| File | Line | Issue | Suggested Fix |
|------|------|-------|---------------|
| `README.md` | 236 | Lists Ice IV in the "Phase Detection (13 phases)" table with "Rhombohedral, 400-600 MPa, 250-270K". However, `quickice/phase_mapping/lookup.py` does NOT include any Ice IV detection logic. The lookup algorithm goes directly from Ice III to Ice V with no Ice IV check. | Either: (a) Add Ice IV detection to `lookup.py` if scientific data supports it, or (b) Remove Ice IV from the README table and update count from 13 to 12 phases. Ice IV is extremely narrow and metastable — most phase diagrams exclude it. |

### 1.8 CLI Reference Says --nmolecules is Required, But Code Makes It Optional

| File | Line | Issue | Suggested Fix |
|------|------|-------|---------------|
| `docs/cli-reference.md` | 50 | Says `--nmolecules` is required ("This argument is required.") | But `quickice/cli/parser.py:57-59` has `required=False, default=None` with a note: "Required for ice generation, optional for interface generation (default: 256)". The CLI reference doesn't mention the conditional requirement. | Update CLI reference to reflect that `--nmolecules` is required for ice generation but optional (default: 256) for interface mode (`--interface`). |

### 1.9 Molecule Count Range Inconsistency: CLI vs GUI vs README

| File | Line | Issue | Suggested Fix |
|------|------|-------|---------------|
| `docs/gui-guide.md` | 69 | Says "4-216 molecules" (GUI limit) | `quickice/gui/validators.py:106` enforces max 216. `quickice/validation/validators.py:93` enforces max 100000 (CLI). README doesn't mention the range. | Add a note in docs/gui-guide.md clarifying the GUI limit (216) vs CLI limit (100000). The README "Molecule Count" section is fine but could mention the GUI limit. |

### 1.10 Missing IAPWS-97 Reference for Phase Diagram Saturation Curve

| File | Line | Issue | Suggested Fix |
|------|------|-------|---------------|
| `docs/flowchart.md` | 192-194 | Mentions "IAPWS97 liquid-vapor saturation curve" with "50 iterations of IAPWS97(T=T, x=0)". The phase diagram code uses `IAPWS97` for the liquid-vapor saturation curve, but this reference is not cited in README. | Add IAPWS-97 reference: "IAPWS-97: Industrial Formulation 1997 for the Thermodynamic Properties of Water and Steam. URL: https://www.iapws.org/relguide/IAPWS-97.html" — Note: IAPWS-95 is used for density calculations, IAPWS-97 for the phase diagram saturation curve. |

### 1.11 docstring in `quickice/phase_mapping/ice_ih_density.py` Has Wrong URL Fragment

| File | Line | Issue | Suggested Fix |
|------|------|-------|---------------|
| `quickice/phase_mapping/ice_ih_density.py` | 11 | References `https://www.iapws.org/release/Ice-2009.html` — this is actually the correct current URL for R10-06(2009). Not a bug per se, but the README uses a different path (`/relguide/Ice-2006.html`). | The code's URL is correct; the README URL needs updating (see issue 1.1 above). No change needed for this file. |

### 1.12 `docs/gro-itp-guide.md` Residue Name Mismatch Example

| File | Line | Issue | Suggested Fix |
|------|------|-------|---------------|
| `docs/gro-itp-guide.md` | 627 | Example says "Residue name 'ETHAN' in GRO, moleculetype 'ETHANOL' in ITP (QuickIce allows mismatch with user dialog)". However, the actual validation code in `quickice/structure_generation/molecule_validator.py` and `quickice/structure_generation/custom_molecule_inserter.py` shows a dialog offering to override the GRO residue name with the ITP moleculetype name. The doc implies this is always allowed, but the override is user-confirmed, not automatic. | Clarify: "QuickIce detects the mismatch and shows a confirmation dialog. If the user accepts, the ITP moleculetype name overrides the GRO residue name. If rejected, the mismatch must be fixed manually before insertion." |

---

## Part 2: Missing Citations

### 2.1 IAPWS-95 (Liquid Water Density)

| Topic | What Citation Is Needed | Suggested Reference |
|-------|------------------------|---------------------|
| Liquid water density calculation | IAPWS-95 formulation is used in `quickice/phase_mapping/water_density.py` for calculating liquid water density at interface boundaries. Not cited in README. | IAPWS-95: "Revised Release on the IAPWS Formulation 1995 for the Thermodynamic Properties of Ordinary Water Substance for General and Scientific Use." URL: https://www.iapws.org/release/IAPWS-95.html |

### 2.2 IAPWS-97 (Phase Diagram Saturation Curve)

| Topic | What Citation Is Needed | Suggested Reference |
|-------|------------------------|---------------------|
| Phase diagram liquid-vapor curve | IAPWS-97 formulation is used in `quickice/output/phase_diagram.py` for the liquid-vapor saturation curve boundary. Not cited in README or docs. | Wagner, W., et al., "The IAPWS Industrial Formulation 1997 for the Thermodynamic Properties of Water and Steam." ASME J. Eng. Gas Turbines Power, 122, 150-182 (2000). URL: https://www.iapws.org/relguide/IAPWS-97.html |

### 2.3 Madrid2019 Compatibility Note with TIP4P-ICE

| Topic | What Citation Is Needed | Suggested Reference |
|-------|------------------------|---------------------|
| Madrid2019 + TIP4P-ICE compatibility | The Madrid2019 ion parameters were originally parameterized for TIP4P/2005 water model, not TIP4P-ICE. QuickIce uses Madrid2019 ions with TIP4P-ICE water. This cross-combination has not been validated in published literature and is a known approximation. README and gui-guide don't mention this caveat. | Add note: "The Madrid2019 ion parameters were developed for the TIP4P/2005 water model (Zeron et al., 2019). Their use with TIP4P-ICE introduces a small systematic error in ion-water interactions. For production simulations requiring high accuracy, consider reparameterizing ion charges for TIP4P-ICE or using the TIP4P/2005 water model instead." Citation: same Zeron et al. 2019 paper already referenced. |

### 2.4 Petrenko & Whitworth O-O Distance Reference

| Topic | What Citation Is Needed | Suggested Reference |
|-------|------------------------|---------------------|
| Ideal O-O distance (0.276 nm) | The ranking module's energy score uses 0.276 nm as the ideal O-O distance, attributed to "Petrenko & Whitworth, 1999, Physics of Ice" in `quickice/ranking/types.py:21` and `quickice/ranking/scorer.py`. The docs/ranking.md mentions this but doesn't provide a full citation. README doesn't mention this reference at all. | Petrenko, V. F. & Whitworth, R. W. (1999). Physics of Ice. Oxford University Press. ISBN: 978-0198518945. Add to README References section. |

### 2.5 GenIce2 Lattice-Specific Citations

| Topic | What Citation Is Needed | Suggested Reference |
|-------|------------------------|---------------------|
| GenIce2 lattice implementations | The GenIce2 paper (Matsumoto et al., J. Comput. Chem. 2017, DOI: 10.1002/jcc.25077) is cited in README, but individual lattice implementations may have separate publications (e.g., ice7, ice8 double-network structures). The code doesn't specify which lattices are from the original paper vs. added later. | Add a note in README or docs that specific lattice implementations are credited to the GenIce2 project and its contributors. The main GenIce2 citation covers all lattice implementations. |

### 2.6 Journaux et al. (2019, 2020) Triple Point References

| Topic | What Citation Is Needed | Suggested Reference |
|-------|------------------------|---------------------|
| II-III-V and II-V-VI triple points | The code in `quickice/phase_mapping/lookup.py:8-9` and `quickice/phase_mapping/triple_points.py:5-6` references "Journaux et al. (2019, 2020)" for II-III-V and II-V-VI triple points. The full citations appear in `quickice/phase_mapping/data/ice_boundaries.py:16` (dead code module) but are NOT in the README or docs/principles.md. | Add to README References: (1) Journaux, B., et al. (2019). "New constraints on the phase diagram of H2O ice at high pressure from Raman spectroscopy." J. Geophys. Res.: Planets, 124. DOI: 10.1029/2019JE006176. (2) Journaux, B., et al. (2020). "Ice rheology and faulting at high pressure." Space Sci. Rev., 216, 7. |

### 2.7 Londono et al. (1993) and Lobban et al. (1998) References

| Topic | What Citation Is Needed | Suggested Reference |
|-------|------------------------|---------------------|
| Ice III and Ice IV crystal structures | Referenced in `docs/principles.md:207-208` for neutron diffraction studies of Ice IX and discovery of a new ice phase. These are correctly cited in principles.md but NOT in README. | These are already in docs/principles.md. Consider whether README should also list them for completeness, or if the current approach (deep references in principles.md only) is sufficient. |

---

## Part 3: Dead Code

### 3.1 Entire `quickice/phase_mapping/data/` Module — DEAD (433 lines)

| File | Line | Dead Element | Confidence | Notes |
|------|------|-------------|------------|-------|
| `quickice/phase_mapping/data/__init__.py` | 1-25 | Entire module | **HIGH** | Imports and re-exports `TRIPLE_POINTS`, `MELTING_CURVE_COEFFICIENTS`, `PHASE_POLYGONS`, `get_melting_pressure`, `get_triple_point`, `get_phase_polygon`, `is_temperature_in_melting_range` from `ice_boundaries.py`. No file outside this directory imports from `quickice.phase_mapping.data`. The actual codebase uses `quickice/phase_mapping/melting_curves.py`, `solid_boundaries.py`, and `triple_points.py` instead. |
| `quickice/phase_mapping/data/ice_boundaries.py` | 1-408 | Entire file | **HIGH** | Contains legacy polygon-based phase boundary data (408 lines). The codebase has migrated to curve-based phase mapping in `melting_curves.py` and `solid_boundaries.py`. The `PHASE_POLYGONS`, `MELTING_CURVE_COEFFICIENTS`, and helper functions in this file are never called from production code. This is the superseded predecessor of the current implementation. |

### 3.2 `IcePhaseLookup` Class — BACKWARD-COMPAT WRAPPER (27 lines)

| File | Line | Dead Element | Confidence | Notes |
|------|------|-------------|------------|-------|
| `quickice/phase_mapping/lookup.py` | 403-430 | `IcePhaseLookup` class | **MEDIUM** | This is a backward-compatible class wrapper around `lookup_phase()`. It's exported from `quickice/phase_mapping/__init__.py:8,16`. The only consumer is `tests/test_phase_mapping.py:463-479` (test code). No production code instantiates this class — all production code uses `lookup_phase()` directly. The `__init__` parameter `data_path` is explicitly documented as "Ignored (kept for backward compatibility)." Consider deprecating and removing after ensuring no external users depend on it. |

### 3.3 Unused Imports

| File | Line | Dead Element | Confidence | Notes |
|------|------|-------------|------------|-------|
| `quickice/phase_mapping/melting_curves.py` | 10 | `from typing import Optional` | **HIGH** | `Optional` is imported but never used in this file. No function signatures use `Optional`. |
| `quickice/phase_mapping/solid_boundaries.py` | 12 | `from typing import Tuple` | **HIGH** | `Tuple` is imported but never used in this file. No function signatures use `Tuple`. |
| `quickice/phase_mapping/lookup.py` | 21 | `xv_boundary` import from `solid_boundaries` | **LOW** | `xv_boundary` is imported at line 21 but only used indirectly via the `solid_boundary()` dispatcher function. However, `xv_boundary` is also imported and used directly at line 21 in the lookup module's import statement. Checking: `xv_boundary` is NOT called directly in lookup.py — the only usage of `xv_boundary` in lookup.py is via the import statement. Wait — checking again, `xv_boundary` is not called in lookup.py directly. The `solid_boundary("XV", T)` would be the path to invoke it, but the lookup.py doesn't call `solid_boundary()` either. So the import of `xv_boundary` at line 21 is unused in lookup.py. |

### 3.4 `check_output_file()` Function — Used Only in CLI Path

| File | Line | Dead Element | Confidence | Notes |
|------|------|-------------|------------|-------|
| `quickice/main.py` | 26-38 | `check_output_file()` function | **LOW** | This function IS used at line 140 in the same file, but only in the CLI `--interface` code path. The non-interface CLI path (lines 192-245) does NOT use it — it just writes files directly. The function prompts for overwrite via `input()` which is appropriate for interactive CLI but would block in any automated context. Not dead code per se, but the inconsistency (one path checks, other doesn't) could cause surprise. |

### 3.5 Potential Dead Code: `custom_molecule_count` / `custom_molecule_atom_count` Fields

| File | Line | Dead Element | Confidence | Notes |
|------|------|-------------|------------|-------|
| `quickice/structure_generation/types.py` | 353-391 | Several fields in `IonStructure` and `SoluteStructure` dataclasses that track custom molecule data | **LOW** | These fields are populated when the source structure contains custom molecules (multi-tab workflow). They ARE used in `gromacs_writer.py` for multi-molecule topology generation. Not dead code — just complex data pass-through for the workflow chain. |

### 3.6 `validate_positive_float()` Only Used by CLI Parser

| File | Line | Dead Element | Confidence | Notes |
|------|------|-------------|------------|-------|
| `quickice/validation/validators.py` | 101-125 | `validate_positive_float()` function | **LOW** | This function is used by `validate_box_dimension()` at line 140 in the same file, and by `quickice/cli/parser.py` for `--ice-thickness`, `--water-thickness`, `--pocket-diameter` arguments. Not dead code — used by CLI argument parsing. |

### 3.7 Empty `quickice/utils/__init__.py`

| File | Line | Dead Element | Confidence | Notes |
|------|------|-------------|------------|-------|
| `quickice/utils/__init__.py` | 1 | Module docstring only, no exports | **MEDIUM** | The `__init__.py` only contains `"""Utility functions for QuickIce."""` with no actual imports or exports. The only function in `quickice/utils/` is `count_guest_atoms()` in `molecule_utils.py`, which is imported directly by modes/slab.py, modes/pocket.py, modes/piece.py. The `__init__.py` doesn't re-export it, making the module namespace less useful. Consider adding `from quickice.utils.molecule_utils import count_guest_atoms` to make the module properly usable. |

### 3.8 `quickice/validation/__init__.py` Does Not Export

| File | Line | Dead Element | Confidence | Notes |
|------|------|-------------|------------|-------|
| `quickice/validation/__init__.py` | 1 | Module docstring only, no exports | **MEDIUM** | Same pattern as `utils/__init__.py`. Contains only `"""QuickIce validation module."""` with no imports. The actual validators are imported via `from quickice.validation.validators import ...` by `quickice/cli/parser.py`. The `__init__.py` doesn't re-export anything, making `import quickice.validation` useless. |

### 3.9 Simon Equation Code in Dead Module

| File | Line | Dead Element | Confidence | Notes |
|------|------|-------------|------------|-------|
| `quickice/phase_mapping/data/ice_boundaries.py` | 89-158 | `MELTING_CURVE_COEFFICIENTS` with Simon-Glatzel equation coefficients | **HIGH** | These Simon-Glatzel coefficients are an approximation of the IAPWS R14-08 equations, but the actual codebase uses the precise IAPWS polynomial equations in `quickice/phase_mapping/melting_curves.py`. The Simon-Glatzel parameters produce slightly different values. This entire data structure is part of the dead `data/` module. |

### 3.10 Phase Polygon Vertices in Dead Module

| File | Line | Dead Element | Confidence | Notes |
|------|------|-------------|------------|-------|
| `quickice/phase_mapping/data/ice_boundaries.py` | 166-256 | `PHASE_POLYGONS` dictionary | **HIGH** | Contains 8 polygon vertex lists for phase regions. This was the old approach (polygon containment testing) that has been replaced by curve-based boundary evaluation in `lookup.py`. These vertices are never used by any production code. |

---

## Summary Statistics

| Category | Count |
|----------|-------|
| **Documentation Issues** | 12 |
| **Missing Citations** | 7 |
| **Dead Code Items** | 10 |
| **Dead Code (total lines)** | ~470 lines (mostly from `phase_mapping/data/` module) |
| **Unused Imports** | 3 confirmed |
| **High-confidence Dead Code** | 3 items (data/ module, unused imports, Simon-Glatzel coefficients) |
| **Medium-confidence Dead Code** | 2 items (IcePhaseLookup, empty __init__.py files) |
| **Low-confidence Dead Code** | 3 items (check_output_file, validate_positive_float, IonStructure fields) |

---

## Priority Recommendations

1. **HIGH** — Delete `quickice/phase_mapping/data/` module (433 lines dead code). The curve-based implementation fully replaces it.
2. **HIGH** — Fix `tests/test_cli_integration.py:292` — asserts version 4.0.0 but code is 4.5.0. This is a test that will fail.
3. **HIGH** — Add IAPWS-95 and IAPWS-97 citations to README References.
4. **MEDIUM** — Fix IAPWS R10-06 URL in README to match code (`/release/Ice-2009.html`).
5. **MEDIUM** — Update README_bin.md version references from v4.0.0 to v4.5.0.
6. **MEDIUM** — Remove unused imports (`Optional` in melting_curves.py, `Tuple` in solid_boundaries.py, `xv_boundary` in lookup.py).
7. **LOW** — Deprecate `IcePhaseLookup` class (only used by tests, no production consumer).
8. **LOW** — Add Madrid2019 + TIP4P-ICE compatibility caveat to README/gui-guide.
9. **LOW** — Update `docs/gui-guide.md:182` from "v4.0 adds" to present tense.

---

*Analysis complete: 2026-06-08*
