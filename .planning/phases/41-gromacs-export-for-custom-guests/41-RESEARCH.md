# Phase 41: GROMACS Export for Custom Guests - Research

**Researched:** 2026-07-03
**Domain:** GROMACS topology/coordinate export for custom-guest clathrate hydrates (QuickIce dual-path CLI+GUI)
**Confidence:** HIGH (all claims verified by reading source with `file:line` citations; `gmx` IS on PATH)

## Summary

Phase 40 delivered a working custom-guest hydrate **generation** pipeline (ethanol in sI) with metadata-driven `_build_molecule_index` setting `mol_type = config.guest_type` (e.g. `"etoh_e2e"`) for custom guests. Phase 41 makes the **export** of those structures produce valid GROMACS input that passes `gmx grompp`.

There are **two independent hydrate export code paths**, and BOTH are broken for custom guests (verified by reading, not speculation):

1. **GUI path** — `quickice/gui/hydrate_export.py::HydrateGROMACSExporter.export_hydrate` → `write_multi_molecule_gro_file` + `write_multi_molecule_top_file` + `transform_guest_itp`. This path **crashes** for custom guests: `_get_hydrate_guest_itp_path(config.guest_type)` raises `FileNotFoundError` (looks for `etoh_e2e_hydrate.itp` which doesn't exist), and even if bypassed, `transform_guest_itp(content, config.guest_type.upper(), ...)` would raise `ValueError` (`"ETOH_E2E_H"` = 8 chars > 5-char GRO limit). The writers also fall back to `"UNK"` because `mol.mol_type not in ["ch4","thf","co2","h2"]`.

2. **CLI path** — `quickice/cli/pipeline.py::_run_export_step` wraps `HydrateStructure` into an `InterfaceStructure` and calls `write_interface_gro_file` + `write_interface_top_file` + `copy_itp_files_for_structure`. This path uses `detect_guest_type_from_atoms` (the P3 anti-pattern) which returns `None` for custom guests → GRO writes `"UNK"` residues, TOP writes no guest `[molecules]` entry, no `#include`, and falls back to CH4 atomtypes. `count_guest_atoms` (the per-molecule atom counter) also misfires for ethanol. Result: grompp fails.

**Primary recommendation:** Treat the two paths as separate work items sharing a common fix pattern — (a) thread custom-guest metadata (`guest_residue_name` + `guest_itp_path`) from `HydrateConfig` into the writers, (b) replace `detect_guest_type_from_atoms` with `mol_type`-driven lookups (P3 fix), (c) reuse the `parse_itp_atomtypes` + `_check_custom_atomtype_conflict` + `_format_custom_atomtype_line` merge pattern already proven in `write_custom_molecule_top_file` (line 2648) and `write_ion_top_file` (line 2238), and (d) validate with `gmx grompp` using the existing `run_gmx_grompp` helper + a transformed-ITP staging step.

**Key enabler (already present):** `HydrateConfig` carries BOTH `guest_gro_path` AND `guest_itp_path` as **separate, explicit fields** (`types.py:478-480`), and `HydrateStructure` propagates `guest_itp_path` (`hydrate_generator.py:197`) plus the full `config` (`hydrate_generator.py:189`). So the ITP path is directly available — it is NOT derived from the `.gro` path. No guessing required.

## Standard Stack

The established functions/files to modify and reference patterns to reuse. **All verified present by reading source.**

### Core functions to MODIFY

| File:Function | Line | What it does now | What it must do for custom guests |
|---------------|------|------------------|-----------------------------------|
| `gui/hydrate_export.py::export_hydrate` | 90 | Resolves guest ITP via `_get_hydrate_guest_itp_path(config.guest_type)`; registers `config.guest_type.upper()`; passes `guest_upper` to `transform_guest_itp` | Branch on `config.is_custom_guest`: use `config.guest_itp_path`; use `config.guest_residue_name` (not `guest_type.upper()`) for registry + transform; thread custom residue name + ITP path to writers |
| `output/gromacs_writer.py::write_multi_molecule_gro_file` | 1473 | Gated `if mol.mol_type in ["ch4","thf","co2","h2"]` for registry lookup; else `MOLECULE_TO_GROMACS.get(...,{"res_name":"UNK"})` → `"UNK"` (line 1529, 1541-1545) | Accept custom-guest residue name (new param or registry entry); write `"{guest_residue_name}_H"` (≤5 chars) instead of `"UNK"` |
| `output/gromacs_writer.py::write_multi_molecule_top_file` | 1591 | Registry lookup keyed `hydrate_{mol_type.upper()}`; falls back to `MOLECULE_TO_GROMACS.get(...,{"mol_name":"UNK"})`; `itp_files` already accepts `mol_type→filename` (line 1666-1673); writes NO custom atomtypes (only built-in CH4/THF/CO2/H2 blocks, line 1715-1729) | Write custom guest residue name in `[molecules]`; `#include` custom ITP filename (already supported via `itp_files`); **merge custom atomtypes** from the custom ITP into `[atomtypes]` with dedup |
| `output/gromacs_writer.py::write_interface_gro_file` | 1007 | `detect_guest_type_from_atoms` (line 1186) → `None` for custom; `guest_res_name="UNK"` (line 1194); `count_guest_atoms` heuristic (line 1201) miscounts ethanol | P3 fix: derive guest type/residue from `molecule_index` (`mol.mol_type`, `mol.count`) instead of atom-name heuristics; use custom residue name |
| `output/gromacs_writer.py::write_interface_top_file` | 1367 | `detect_guest_type_from_atoms` (line 1415) → `None`; writes CH4 atomtypes fallback (line 1430-1434); NO `#include` for guest (line 1442 gate); NO `[molecules]` entry (line 1468 gate) | P3 fix: use `molecule_index`; include custom ITP; write custom residue name in `[molecules]`; merge custom atomtypes |
| `cli/pipeline.py::_run_export_step` | 729 | Wraps `HydrateStructure` into `InterfaceStructure` (line 806-819) **without** carrying `config.guest_residue_name`/`guest_itp_path`/`is_custom_guest` | Thread custom-guest metadata onto the wrapper (or pass config) so `write_interface_*` + `copy_itp_files_for_structure` can handle custom guests |
| `cli/itp_helpers.py::get_hydrate_guest_itp_path` | 20 | `Path(...)/"data"/f"{guest_type}_hydrate.itp"` → `FileNotFoundError` for custom | Branch on custom guest: use `config.guest_itp_path` |
| `cli/itp_helpers.py::_copy_hydrate_guest_itp` | 167 | Calls `get_hydrate_guest_itp_path`; `except FileNotFoundError` (line 193) silently returns `None` → ITP not copied | Use custom ITP path; apply `transform_guest_itp` with `guest_residue_name` |

### Reference patterns to REUSE (do NOT reinvent)

| Pattern | Location | What it proves | Reuse for |
|---------|----------|----------------|-----------|
| Custom atomtypes merge + dedup | `write_custom_molecule_top_file` line **2648-2670** | `parse_itp_atomtypes(itp_path)` → loop → `_check_custom_atomtype_conflict(name, fields, written)` → `if name not in written: f.write(_format_custom_atomtype_line(fields)); written[name]=(...)` | Phase 41-02 atomtypes merge in `write_multi_molecule_top_file` (and CLI `write_interface_top_file`) |
| Same merge (ion path) | `write_ion_top_file` line **2238-2262** | Identical pattern; also handles `has_custom and ion_structure.custom_itp_path` | Cross-validates the pattern; confirms dedup via `_written_atomtypes` dict |
| ITP transformation (3 steps) | `transform_guest_itp` line **640** | Step1 `comment_out_atomtypes_in_itp`; Step2 rename moleculetype `"{guest_name}{suffix}"` + `validate_gro_residue_name`; Step3 `_rewrite_atoms_section_resname` | Already complete (Phase 38-04/40-02); Phase 41 just must call it with `guest_name=config.guest_residue_name` (NOT `config.guest_type.upper()`) |
| `_check_custom_atomtype_conflict` | line **164** | Raises `ValueError` if name exists with different LJ params; silent dedup if params match; uses `_lj_params_match` (rtol=1e-4) | Dedup of shared `hc`/`c3`/`h1` between GAFF2 and custom etoh |
| `parse_itp_atomtypes` | line **473** | Handles 7-col (inserts name as bond_type, line 516) and 8-col formats; returns `list[tuple[str,...]]` | Parsing etoh.itp `[atomtypes]` (which is 7-col Format 1) |
| `validate_gro_residue_name` | line **25** | `ValueError` if `>5` chars; message recommends ≤3 base for `_H` | Enforcing `MOL`→`MOL_H` (5 chars, OK) vs rejecting `ETOH_E2E`→`ETOH_E2E_H` (8 chars) |

### Supporting utilities (no change needed)

| Utility | Location | Note |
|---------|----------|------|
| `MoleculetypeRegistry.register_hydrate_guest` | `moleculetype_registry.py:46` | `f"{molecule}_H"`, key `f"hydrate_{molecule}"`. **Caveat:** hardcodes the name from the `molecule` arg; cannot accept a custom ≤3-char base AND a long `mol_type` key simultaneously — see Open Questions |
| `MOLECULE_TO_GROMACS` | `gromacs_writer.py:239` | Built-in map; custom `mol_type` misses → `"UNK"`/`"unknown.itp"` |
| `get_hydrate_guest_residue_name` | `gromacs_writer.py:763` | Built-in only; fallback `"UNK_H"` |
| `count_guest_atoms` | `molecule_utils.py:21` | Heuristic; only ch4/thf/Me/H2; **misfires for ethanol** — Phase 41 must avoid calling it for custom guests (use `mol.count` from `molecule_index`) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New params on `write_multi_molecule_*` for custom residue name | Register custom guest in `MoleculetypeRegistry` under `hydrate_{mol_type.upper()}` key | Registry hardcodes `f"{molecule}_H"` so registering `"ETOH_E2E"` yields 8-char `"ETOH_E2E_H"` (invalid). Registering `"MOL"` yields key `hydrate_MOL` but writers look up `hydrate_ETOH_E2E` — key mismatch. New param is cleaner (see Open Questions) |
| Fix CLI `write_interface_*` for custom guests | Switch CLI hydrate export to `write_multi_molecule_*` (same as GUI) | Eliminates the `write_interface_*` hydrate path + P3 entirely; bigger refactor but removes duplicate logic. **Recommended consideration** for the planner |
| Inline atomtypes merge in `write_multi_molecule_top_file` | Extract shared `_merge_custom_atomtypes(f, itp_path, written, label)` helper | DRY across `write_multi_molecule_top_file`, `write_custom_molecule_top_file`, `write_ion_top_file`. Recommended — the pattern is triplicated already |

**Installation:** No new dependencies. `gmx` is already on PATH (`/data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx`). All needed Python code is in-repo.

## Architecture Patterns

### Recommended Project Structure (files touched)
```
quickice/
├── output/gromacs_writer.py        # write_multi_molecule_{gro,top}_file, write_interface_{gro,top}_file, transform_guest_itp, atomtypes helpers
├── gui/hydrate_export.py           # export_hydrate (GUI path)
├── cli/pipeline.py                # _run_export_step (CLI path)
├── cli/itp_helpers.py             # get_hydrate_guest_itp_path, _copy_hydrate_guest_itp, copy_itp_files_for_structure
└── structure_generation/
    ├── types.py                   # HydrateConfig (guest_residue_name, guest_itp_path, guest_gro_path, is_custom_guest) — NO change needed
    ├── hydrate_generator.py       # _build_molecule_index already sets mol_type=config.guest_type — NO change needed
    └── moleculetype_registry.py   # MoleculetypeRegistry — possibly add a custom-name override (see Open Questions)
tests/
├── test_output/test_gromacs_export_hydrate.py  # ADD custom-guest export tests (model on existing CH4 tests + mock_hydrate_save_dialog)
├── test_e2e_gmx_validation.py                  # ADD custom-guest hydrate grompp test (or new file)
└── e2e_export_helpers.py                       # ADD transformed-ITP staging helper (transform_guest_itp, not just comment_out)
```

### Pattern 1: Metadata-driven mol_type (the P3 fix)
**What:** Use `mol.mol_type` from `molecule_index` (set by Phase 38/40 `_build_molecule_index` to `config.guest_type` for custom, e.g. `"etoh_e2e"`) instead of re-detecting from atom names.
**When to use:** Any export code that currently calls `detect_guest_type_from_atoms`.
**Why:** `_build_molecule_index` (`hydrate_generator.py:625`) already records `MoleculeIndex(start, count, config.guest_type)` for custom guests. `detect_guest_type_from_atoms` (`gromacs_writer.py:1313`) only recognizes ch4/thf/co2/h2/Me and returns `None` for everything else — confirmed by reading its body (lines 1326-1364).

### Pattern 2: Custom atomtypes merge + dedup (the 41-02 reference)
**What:** Parse `[atomtypes]` from the custom guest ITP, write each into the main `.top [atomtypes]`, skipping names already written (dedup) and raising on LJ-param conflicts.
**When to use:** Custom guest ITPs that ship their own `[atomtypes]` (like `etoh.itp` lines 3-9).
**Example (verbatim from `write_custom_molecule_top_file:2648-2670` — the canonical reference):**
```python
# Source: gromacs_writer.py:2648-2670 (read & verified)
if custom_structure.itp_path and custom_structure.itp_path.exists():
    custom_atomtypes = parse_itp_atomtypes(custom_structure.itp_path)
    if custom_atomtypes:
        f.write(f"; {custom_mol_name} custom molecule atom types\n")
        for atomtype in custom_atomtypes:
            if len(atomtype) >= 8:
                at_name = atomtype[0]
                _check_custom_atomtype_conflict(at_name, atomtype, _written_atomtypes)
                if at_name not in _written_atomtypes:
                    f.write(_format_custom_atomtype_line(atomtype))
                    try:
                        _written_atomtypes[at_name] = (
                            atomtype[1], int(atomtype[2]),
                            float(atomtype[3]), float(atomtype[4]),
                            atomtype[5], float(atomtype[6]),
                            float(atomtype[7]))
                    except (ValueError, IndexError):
                        pass  # Best-effort recording
```
`_written_atomtypes` is initialized with water (`WATER_ATOMTYPES`) + ion + GAFF2 blocks BEFORE the custom merge (line 2633, 2636-2638), so shared names (`hc`,`c3`,`h1` in etoh) dedup against GAFF2 and new names (`oh`,`ho`) get written.

### Pattern 3: ITP transformation (already complete — call correctly)
**What:** `transform_guest_itp(content, guest_name, suffix="_H")` does 3 steps: comment `[atomtypes]`, rename `[moleculetype]` to `"{guest_name}_H"` (+validate ≤5 chars), rewrite `[atoms]` resname.
**Critical:** It validates the result name at line 677 — so `guest_name` MUST be the ≤3-char base (`"MOL"`), NOT `config.guest_type.upper()` (`"ETOH_E2E"`). The current `export_hydrate` passes the WRONG value (line 151, 185).

### Anti-Patterns to Avoid
- **Re-detecting guest type from atom names** (`detect_guest_type_from_atoms`): returns `None` for custom guests → `"UNK"`/missing ITP. Use `mol_type` from `molecule_index`. (EXPORT-05)
- **Hardcoded `["ch4","thf","co2","h2"]` gates** in writers (gromacs_writer.py:1529, 1541, 1653): exclude custom `mol_type`. Use a passed residue-name mapping or registry.
- **`count_guest_atoms` heuristic** for custom guests: only knows ch4/thf/Me/H2; miscounts ethanol. Use `mol.count` from `molecule_index`.
- **Passing `config.guest_type.upper()` to `transform_guest_itp`/registry**: produces >5-char names → `ValueError`. Pass `config.guest_residue_name`.
- **`git add .` / `git add -A`**: AGENTS.md mandates atomic commits; stage only intended files.
- **Bare `except Exception`** in `quickice/cli/pipeline.py`: AGENTS.md forbids it; use specific exceptions.
- **Hardcoding TIP4P-ICE params / `0.0299` / `4`**: use module constants (not relevant to this phase's new code, but don't introduce violations).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Custom atomtypes dedup | Custom set-difference logic | `_check_custom_atomtype_conflict` + `_written_atomtypes` dict (line 164) | Handles LJ-param conflict detection + float-tolerant comparison (`_lj_params_match`, rtol=1e-4); already triplicated |
| ITP atomtypes commenting | New comment-walker | `comment_out_atomtypes_in_itp` (line 524) | Handles section boundaries, preserves comments/blank lines |
| ITP resname rewrite | New column parser | `_rewrite_atoms_section_resname` (line 571) | Regex-scoped to `[atoms]` only; preserves leading whitespace + comment lines |
| GRO residue-name length check | New `len()` assert | `validate_gro_residue_name` (line 25) | Centralized, clear error message referencing the ≤3-char base convention |
| grompp execution | New subprocess wrapper | `run_gmx_grompp` (e2e_export_helpers.py:559) | Handles stale-TPR cleanup, cwd, timeout=60, maxwarn |
| ITP staging for tests | New copy loop | `_stage_itp_files` (e2e_export_helpers.py:399) — **but needs a transform variant** (see test_fixtures) | Already finds ITPs in `data/` + `data/custom/`; comments atomtypes |

**Key insight:** Every primitive needed for Phase 41 already exists in `gromacs_writer.py` — `transform_guest_itp`, `parse_itp_atomtypes`, `_check_custom_atomtype_conflict`, `_format_custom_atomtype_line`, `_write_atomtypes_block`, `validate_gro_residue_name`. The work is **wiring** (threading custom metadata to the right call sites) and **replacing heuristics with metadata** (P3), not building new parsers.

## Code Paths (verified step-by-step with file:line)

### Path A — GUI hydrate export (currently CRASHES for custom guests)

```
HydrateGROMACSExporter.export_hydrate(structure, config)   # gui/hydrate_export.py:90
├─ default_name = f"hydrate_{lattice}_{guest}_{nx}x{ny}x{nz}.gro"   # :109
├─ QFileDialog.getSaveFileName(...)                                # :112  (mocked in tests)
├─ guest_itp_path = _get_hydrate_guest_itp_path(config.guest_type) # :144  ← BUG#1: FileNotFoundError for "etoh_e2e"
│                                                                  #   _get_hydrate_guest_itp_path looks for "{guest_type}_hydrate.itp" (:58)
├─ registry = MoleculetypeRegistry()                              # :147
├─ guest_upper = config.guest_type.upper()                         # :151  ← "ETOH_E2E" (wrong; should be guest_residue_name "MOL")
├─ registry.register_hydrate_guest(guest_upper)                   # :152  → "ETOH_E2E_H" (8 chars, key "hydrate_ETOH_E2E")
├─ write_multi_molecule_gro_file(positions, molecule_index, ...)  # :155  ← BUG#2: mol.mol_type="etoh_e2e" not in ["ch4","thf","co2","h2"]
│   └─ line 1529: if registry and mol.mol_type in ["ch4","thf","co2","h2"]:  → False (skips registry)
│   └─ line 1541: elif mol.mol_type in [...]:  → False
│   └─ line 1544: MOLECULE_TO_GROMACS.get("etoh_e2e", {"res_name":"UNK"}) → "UNK"
│   └─ line 1547: validate_gro_residue_name("UNK") → OK (3 chars) → writes "UNK" residues  ← BUG: should be "MOL_H"
├─ itp_files = {config.guest_type: guest_itp_path.name}            # :167  (would be {"etoh_e2e":"etoh.itp"} if BUG#1 fixed)
├─ write_multi_molecule_top_file(molecule_index, ..., itp_files, registry)  # :170
│   └─ line 1642: hydrate_key = "hydrate_ETOH_E2E" → in reg._registered → res_name="ETOH_E2E_H"  ← BUG#3: 8 chars, no validate call here
│   └─ line 1666: MOLECULE_TO_GROMACS.get("etoh_e2e",{"itp_file":"unknown.itp"}) → but itp_files overrides → "etoh.itp"  (OK if threaded)
│   └─ line 1715-1729: writes CH4/THF/CO2/H2 atomtype blocks only — NO custom atomtypes merge  ← BUG#4: missing oh,ho
│   └─ line 1736: #include "etoh.itp"  (OK if itp_files threaded)
│   └─ [molecules]: "ETOH_E2E_H <count>"  ← BUG#3: mismatches GRO "UNK" → grompp fatal
├─ shutil.copy(tip4p_itp_path, ...)                              # :180  (OK)
└─ transformed = transform_guest_itp(content, guest_upper, "_H")  # :185  ← BUG#5: validate_gro_residue_name("ETOH_E2E_H") → ValueError (8 chars) CRASH
```
**Net:** Crashes at line 144 (FileNotFoundError). If 144 bypassed, crashes at line 185 (ValueError). The writers produce inconsistent `"UNK"` (GRO) vs `"ETOH_E2E_H"` (TOP).

### Path B — CLI hydrate export (currently produces invalid output, no crash)

```
CLIPipeline._run_export_step()                                   # cli/pipeline.py:729
├─ structure, step_name = self._hydrate_result, "hydrate"        # :767
├─ hydrate = structure
├─ wrapper = InterfaceStructure(                                  # :806-819  ← NOTE: config NOT carried; guest_residue_name/guest_itp_path LOST
│     positions, atom_names, cell, molecule_index=hydrate.molecule_index,
│     mode="hydrate", ice_atom_count=0, water_atom_count=...,
│     guest_atom_count=..., guest_nmolecules=...,
│   )                                                            #   molecule_index HAS mol_type="etoh_e2e" but wrapper drops config
├─ write_interface_gro_file(wrapper, gro_path)                   # :820  ← BUG#6: detect_guest_type_from_atoms → None
│   └─ gromacs_writer.py:1186: guest_type = detect_guest_type_from_atoms(...) → None
│   └─ :1194: guest_res_name = "UNK"
│   └─ :1201: count_guest_atoms(...) → miscounts ethanol (only knows ch4/thf/Me/H2)
│   └─ writes "UNK" residues for guest atoms
├─ write_interface_top_file(wrapper, top_path)                   # :821  ← BUG#7
│   └─ :1415: guest_type = detect_guest_type_from_atoms(...) → None
│   └─ :1417: `if guest_atom_count>0 and guest_type:` → False → skip atomtypes
│   └─ :1430: `elif guest_atom_count>0:` → True → write CH4 atomtypes fallback (WRONG; missing oh,ho)
│   └─ :1442: `if guest_nmolecules>0 and guest_type:` → False → NO #include for guest ITP
│   └─ :1466-1470: `if guest_type:` → False → NO [molecules] entry for guest
│   └─ Result: [molecules] has SOL only; guest atoms in GRO are "UNK" unaccounted → grompp fatal
└─ copy_itp_files_for_structure(output_dir, structure, "hydrate") # :836  ← BUG#8
    └─ itp_helpers.py:279: guest_type = _resolve_guest_type_for_hydrate_step(structure)
       └─ :218: getattr(structure,"guest_type",None) → HydrateStructure has no `guest_type` attr → None
       └─ :223: config = getattr(structure,"config",None) → HydrateConfig (HAS guest_type="etoh_e2e") → returns "etoh_e2e"
       └─ :281: _copy_hydrate_guest_itp(output_dir, "etoh_e2e")
          └─ itp_helpers.py:185: get_hydrate_guest_itp_path("etoh_e2e") → looks for "etoh_e2e_hydrate.itp" → FileNotFoundError
          └─ :193: except FileNotFoundError → returns None (silently skips ITP copy)
       └─ Result: NO custom guest ITP copied to output dir
```
**Net:** No crash, but `.top` has no guest moleculetype/`#include`/atomtypes, `.gro` has `"UNK"` guest residues, custom ITP not copied. `gmx grompp` fails.

> NOTE on `_resolve_guest_type_for_hydrate_step` (itp_helpers.py:201): it DOES recover `config.guest_type="etoh_e2e"` via `structure.config` (strategy 2, line 223) — so the CLI knows the guest type. The bug is that `_copy_hydrate_guest_itp` then looks for a bundled `{guest_type}_hydrate.itp` instead of `config.guest_itp_path`.

## Bugs to Fix (mapped to EXPORT requirements)

Each bug is verified by reading; `file:line` cited; root cause stated.

### EXPORT-01 — Custom guest in `.top [molecules]` with correct `_H` name
- **Bug A (GUI):** `hydrate_export.py:151` uses `config.guest_type.upper()` (`"ETOH_E2E"`) → registry name `"ETOH_E2E_H"` (8 chars) and `transform_guest_itp` raises `ValueError` (line 677). **Root cause:** wrong identifier passed. **Fix:** use `config.guest_residue_name` (`"MOL"`) → `"MOL_H"` (5 chars).
- **Bug B (GUI):** `write_multi_molecule_top_file:1657` writes the registry name `"ETOH_E2E_H"` but GRO writes `"UNK"` (Bug C) → mismatch. **Fix:** both writers use the same `"{guest_residue_name}_H"`.
- **Bug C (CLI):** `write_interface_top_file:1468` gated on `guest_type` (None) → no `[molecules]` entry. **Fix:** P3 — use `molecule_index` to emit `"{guest_residue_name}_H <count>"`.

### EXPORT-02 — Custom `[atomtypes]` commented out in bundled `.itp`
- **Status:** Already handled by `transform_guest_itp` Step 1 (`comment_out_atomtypes_in_itp`, line 662). **Just call it** with `guest_name=config.guest_residue_name`. No new work — but the call at `hydrate_export.py:185` currently passes the wrong `guest_name`.

### EXPORT-03 — Custom atomtypes merged into main `.top [atomtypes]` with dedup
- **Bug D (GUI):** `write_multi_molecule_top_file:1715-1729` writes ONLY built-in CH4/THF/CO2/H2 blocks; no custom merge. **Root cause:** no ITP path threaded for atomtypes parsing. **Fix:** thread custom ITP path; reuse the `write_custom_molecule_top_file:2648-2670` pattern (parse→conflict-check→write-if-new→record).
- **Bug E (CLI):** `write_interface_top_file:1430-1434` writes CH4 atomtypes fallback (wrong) and misses `oh`/`ho`. **Fix:** same custom merge pattern.
- **Dedup proof:** etoh.itp atomtypes are `hc, c3, h1, oh, ho` (lines 5-9). `hc`/`c3`/`h1` exist in `GAFF2_ATOMTYPES` (line 67-80) with matching LJ params (verified: `hc` sigma `2.60018e-1` vs etoh `2.600177E-01` ≈ equal within rtol=1e-4) → `_check_custom_atomtype_conflict` silent-dedups them; `oh`/`ho` are new → written.

### EXPORT-04 — GRO residue name ≤5 chars with `_H` suffix
- **Bug F (GUI):** `write_multi_molecule_gro_file:1544` → `"UNK"` (3 chars, passes validate but WRONG name). **Fix:** write `"{guest_residue_name}_H"` (e.g. `"MOL_H"`, 5 chars, passes `validate_gro_residue_name` at line 1547).
- **Bug G (CLI):** `write_interface_gro_file:1194` → `"UNK"`. **Fix:** use `"{guest_residue_name}_H"`.
- **Enforcement already exists:** `validate_gro_residue_name` (line 25) raises `ValueError` for `>5` chars; `HydrateConfig.__post_init__` (types.py:505-510) requires `guest_residue_name` for custom guests; `validate_custom_guest_files` (custom_guest_bridge.py:254-261) rejects base names `>3` chars. So `"MOL"`→`"MOL_H"` (5) is the enforced contract.

### EXPORT-05 — Use `mol_type` from `molecule_index` (not re-detection) — the P3 fix
See the dedicated **p3_fix** section below.

### EXPORT-06 — `gmx grompp` validates
- Blocked by Bugs A–G above. Once fixed, `gmx grompp` should pass. `gmx` is on PATH (verified). Test pattern exists (`run_gmx_grompp`, e2e_export_helpers.py:559). **New requirement:** a transformed-ITP staging helper (current `_stage_itp_files` only does `comment_out_atomtypes_in_itp`, NOT the full `transform_guest_itp` with `_H` rename — see test_fixtures).

## P3 Fix (EXPORT-05) — `detect_guest_type_from_atoms` call sites

`detect_guest_type_from_atoms` is defined at `gromacs_writer.py:1313` and called at **9 sites in `gromacs_writer.py`** + **1 in `gui/export.py`** (verified via grep). Enclosing functions:

| Call line | Enclosing function | In Phase 41 scope? | Why |
|-----------|--------------------|-------------------|-----|
| 1186 | `write_interface_gro_file` | **YES (CLI hydrate)** | CLI hydrate GRO; returns None for custom → "UNK" |
| 1415 | `write_interface_top_file` | **YES (CLI hydrate)** | CLI hydrate TOP; returns None → no guest entry/ITP/atomtypes |
| 1985 | `write_ion_gro_file` | NO (ion path) | Hydrate guest in ion chain; built-in works; custom-guest-hydrate→ion is a later phase |
| 2149 | `write_ion_top_file` | NO (ion path) | Same |
| 2511 | `write_custom_molecule_gro_file` | NO (custom mol path) | Tab 5 custom molecule, not hydrate guest |
| 2597 | `write_custom_molecule_top_file` | NO (custom mol path) | Same |
| 2971 | `write_solute_gro_file` | NO (solute path) | Liquid solute |
| 3111, 3120 | `write_solute_top_file` | NO (solute path) | Liquid solute |
| gui/export.py:55 | (ion GUI exporter) | NO | Legacy ion GUI export |

**P3 fix scope for Phase 41 = lines 1186 + 1415** (the two `write_interface_*` calls used by the CLI hydrate path). The GUI `write_multi_molecule_*` writers do NOT call `detect_guest_type_from_atoms` (they use `mol.mol_type` directly) — their P3-equivalent bug is the hardcoded `["ch4","thf","co2","h2"]` gate (lines 1529, 1541, 1653), not a `detect_*` call.

**Fix approach (both call sites):** Replace `detect_guest_type_from_atoms(atom_names)` with a `molecule_index`-driven lookup:
```python
# P3 fix pattern (illustrative — planner decides exact API)
# Instead of:  guest_type = detect_guest_type_from_atoms(guest_atom_names)   # returns None for custom
# Use molecule_index to find the guest mol_type and its residue name:
guest_entries = [m for m in iface.molecule_index if m.mol_type not in ("ice","water","na","cl")]
# For a custom guest, m.mol_type == config.guest_type (e.g. "etoh_e2e");
# the residue name comes from threaded metadata (config.guest_residue_name + "_H")
```
Because `write_interface_*` receive an `InterfaceStructure` (no `config`), the custom-guest residue name + ITP path must be threaded onto the wrapper in `_run_export_step` (cli/pipeline.py:806) OR via new `InterfaceStructure` fields. See **Open Questions**.

## Atomtypes Merge (41-02) — reuse pattern

The canonical merge pattern lives in `write_custom_molecule_top_file:2648-2670` (and identically in `write_ion_top_file:2238-2262`). To reuse it in `write_multi_molecule_top_file`:

**Recommended: extract a shared helper** (DRY — the pattern is currently triplicated):
```python
# Suggested helper (planner decides signature/placement in gromacs_writer.py)
def _merge_custom_atomtypes(f, itp_path: Path, written: dict, label: str) -> None:
    """Parse custom ITP [atomtypes], conflict-check, write new ones, record."""
    custom_atomtypes = parse_itp_atomtypes(itp_path)
    if not custom_atomtypes:
        return
    f.write(f"; {label} custom molecule atom types\n")
    for atomtype in custom_atomtypes:
        if len(atomtype) >= 8:
            at_name = atomtype[0]
            _check_custom_atomtype_conflict(at_name, atomtype, written)
            if at_name not in written:
                f.write(_format_custom_atomtype_line(atomtype))
                try:
                    written[at_name] = (atomtype[1], int(atomtype[2]),
                        float(atomtype[3]), float(atomtype[4]),
                        atomtype[5], float(atomtype[6]), float(atomtype[7]))
                except (ValueError, IndexError):
                    pass
```

**Threading requirement:** `write_multi_molecule_top_file` currently takes `(molecule_index, filepath, system_name, itp_files, registry)` — it has NO custom ITP path for atomtypes parsing (it has `itp_files` = `mol_type→filename` but not a readable path). **Phase 41 must thread a `custom_guest_itp_path`** (or a `custom_guest_info` dict with residue name + ITP path) so the merge can `parse_itp_atomtypes` it. The `_written_atomtypes` dict is already initialized with water+ion+GAFF2 blocks (lines 1694-1729) before the merge point.

**Ordering invariant (GROMACS):** ALL `[atomtypes]` must be grouped after `[ defaults ]` and BEFORE any `#include` (enforced by the existing writers: atomtypes at lines 1690-1731, `#include` at 1735). The custom merge must slot in at line ~1730 (after GAFF2 blocks, before `#include`).

## Test Fixtures (verified)

### Custom guest fixtures (ethanol) — EXIST and are reusable
- `quickice/data/custom/etoh.gro` (508 bytes, 9 atoms, resname `MOL`) — read & verified
- `quickice/data/custom/etoh.itp` (5715 bytes) — read & verified:
  - `[ atomtypes ]` (lines 3-9): 5 types `hc, c3, h1, oh, ho` in **7-col Format 1** (no bond_type col) → `parse_itp_atomtypes` inserts name as bond_type (line 516)
  - `[ moleculetype ]` (line 11-13): name `etoh`, nrexcl 3
  - `[ atoms ]` (lines 15-25): resname `MOL`, 9 atoms
  - `[ bonds ]`, `[ angles ]`, `[ dihedrals ]`, `[ pairs ]` complete
- `e2e_export_helpers.py:45-46` defines `ETOH_GRO`/`ETOH_ITP` path constants
- `test_e2e_custom_guest_hydrate.py` (Phase 40) shows the exact `HydrateConfig` for a custom guest:
  ```python
  _GUEST_TYPE = "etoh_e2e"; _GUEST_RESIDUE_NAME = "MOL"
  _GUEST_GRO_PATH = "quickice/data/custom/etoh.gro"
  _GUEST_ITP_PATH = "quickice/data/custom/etoh.itp"
  _GUEST_ATOM_LABELS = ["H","C","H","H","C","H","H","O","H"]; _GUEST_ATOM_COUNT = 9
  ```

### grompp test helpers — EXIST (`tests/e2e_export_helpers.py`, read & verified)
- `run_gmx_grompp(workspace, gro_file, top_file, mdp_file="em.mdp", tpr_file="em.tpr", maxwarn=5)` (line 559) → `(exit_code, stderr)`; cleans stale `.tpr*`; `timeout=60`
- `parse_gro_residue_names`, `parse_gro_atom_count`, `parse_top_molecules`, `parse_top_includes` (lines 51-181)
- `assert_gro_top_consistent(gro_path, top_path)` (line 485) — cross-validates GRO residues ↔ TOP `[molecules]` (case-insensitive match for custom)
- `assert_itp_completeness(top_path, workspace)` (line 456) — every `#include`'d ITP exists
- `_stage_itp_files(top_path, workspace)` (line 399) — copies `#include`'d ITPs from `data/` + `data/custom/`, applies `comment_out_atomtypes_in_itp` if `[atomtypes]` present. **GAP:** it does NOT apply `transform_guest_itp` (no `_H` rename) — so a staged `etoh.itp` keeps moleculetype `etoh` + resname `MOL`, which won't match `.top [molecules] MOL_H`. **Phase 41 needs a transformed-ITP staging variant** (or the test must call `transform_guest_itp` explicitly on the custom guest ITP before staging).
- `MDP_PATH = tests/em.mdp` (line 395) — `integrator=steep`, `nsteps=500`, PME, `rcoulomb=1.0`, `rvdw=1.0`, `constraints=none`, `pbc=xyz` (read & verified)

### Test markers / env
- `gmx_skipif` = `pytest.mark.skipif(not _gmx_available(), ...)` (conftest.py:24). `gmx` IS available (`/data/nglokwan/ompi_plumed-gmx/.../gmx`) — so the custom-guest grompp test will actually RUN.
- `gmx_workspace` fixture (test_e2e_gmx_validation.py:64) — persistent dir under `tmp/e2e-gmx-validation/`.
- GUI hydrate export fixtures (`simple_hydrate_structure`, `simple_hydrate_config`, `mock_hydrate_save_dialog`) live in `tests/test_output/conftest.py` (verified via grep). The existing `test_gromacs_export_hydrate.py` mocks `QFileDialog` + `QMessageBox` and calls `HydrateGROMACSExporter.export_hydrate` — **this is the model for the GUI-path custom-guest export test** (it does NOT run grompp currently; Phase 41 can extend it or add a grompp variant).
- **No existing test** directly grompp-validates a custom-guest HYDRATE export (existing grompp tests use built-in ch4/thf hydrate→interface→...→ion chains, where `detect_guest_type_from_atoms` succeeds). Phase 41-04 adds this coverage.

## Common Pitfalls

### Pitfall 1: GROMACS `[ molecules ]` ↔ GRO residue name MUST match (FATAL otherwise)
**What goes wrong:** GRO writes `"UNK"` (or `"MOL"` without `_H`) but TOP `[molecules]` lists `"MOL_H"` (or vice versa) → `gmx grompp` fatal: "molecule X not found in coordinate file".
**Why:** The two writers use different code paths and disagree on the name.
**How to avoid:** Both writers must derive the name from the SAME source (`config.guest_residue_name + "_H"`). `assert_gro_top_consistent` (e2e_export_helpers.py:485) catches this.
**Warning signs:** Test asserting `expected_gro_keys` vs `expected_top_keys` disagree.

### Pitfall 2: `_H` suffix pushes name over the 5-char GRO limit
**What goes wrong:** `guest_type.upper() + "_H"` = `"ETOH_E2E_H"` (8 chars) → `validate_gro_residue_name` raises `ValueError` (line 25), crashing `transform_guest_itp` (line 677) and the GRO writer (line 1547).
**Why:** `config.guest_type` is the sys.modules/plugin slug (long), NOT the GRO residue name (short).
**How to avoid:** ALWAYS use `config.guest_residue_name` (≤3 chars, validated by `HydrateConfig.__post_init__` + `validate_custom_guest_files`) for the `_H` suffix. The contract: `guest_residue_name` ≤3 → `+ "_H"` ≤5.
**Warning signs:** Any code passing `config.guest_type` (not `guest_residue_name`) to `transform_guest_itp` or `register_hydrate_guest`.

### Pitfall 3: `[atomtypes]` MUST precede `#include` (GROMACS ordering)
**What goes wrong:** If custom atomtypes are written after `#include "etoh.itp"`, grompp errors (atomtype used before defined).
**Why:** GROMACS processes `.top` top-to-bottom; `[atomtypes]` must be globally visible before molecule definitions.
**How to avoid:** The existing writers enforce this (atomtypes block at lines 1690-1731, `#include` at 1735). The custom merge MUST slot in at line ~1730 (after GAFF2 blocks, before `#include`).
**Warning signs:** grompp error "Unknown atomtype 'oh'".

### Pitfall 4: `comb-rule=2` (Lorentz-Berthelot) is mandatory (AGENTS.md)
**What goes wrong:** Using comb-rule=1 breaks AMBER/GAFF2 mixing.
**How to avoid:** The main `.top [ defaults ]` already writes `1 2 yes 0.5 0.8333` (comb-rule=2) at line 1686/929. Don't change it. `etoh.itp` has NO `[ defaults ]` (acceptable — main `.top` supplies it; `validate_custom_guest_files` step 5 accepts absent `[ defaults ]`).
**Warning signs:** Any new `.top` writer emitting comb-rule≠2.

### Pitfall 5: `count_guest_atoms` heuristic miscounts custom guests
**What goes wrong:** `write_interface_gro_file:1201` calls `count_guest_atoms(guest_atom_names, mol_start)` which only knows ch4(5)/thf(13)/Me(1)/H2(2). For ethanol (9 atoms) it falls into the "C+H looks like CH4" branch (line 88) → returns 5, splitting one 9-atom ethanol into wrong chunks.
**How to avoid:** For custom guests, iterate `molecule_index` and use `mol.count` directly (not the heuristic). The P3 fix naturally addresses this.

### Pitfall 6: Registry key mismatch for custom guests
**What goes wrong:** Register `register_hydrate_guest("MOL")` → key `hydrate_MOL` → name `MOL_H`. But `write_multi_molecule_*` look up `hydrate_{mol.mol_type.upper()}` = `hydrate_ETOH_E2E` → miss → fallback `"UNK"`.
**How to avoid:** Either (a) thread the residue name via a new writer param (recommended — avoids registry contortions), or (b) register under a key the writers look up — but `register_hydrate_guest("ETOH_E2E")` yields 8-char name (invalid). So (a) is the only clean option. See Open Questions.

### Pitfall 7: Silent ITP-skip in CLI (`except FileNotFoundError`)
**What goes wrong:** `itp_helpers.py:193` `except FileNotFoundError: return None` silently skips the custom guest ITP copy → `.top` `#include`s a file that's missing → grompp "File not found".
**How to avoid:** For custom guests, don't go through `_copy_hydrate_guest_itp`/`get_hydrate_guest_itp_path` (bundled-file lookup); use `config.guest_itp_path` directly + `transform_guest_itp`. Surface real errors rather than silently skipping.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `detect_guest_type_from_atoms` heuristic | Metadata-driven `mol_type` in `MoleculeIndex` (Phase 38/40) | Phase 38-02 / 40-05 | Custom guests now have a correct `mol_type`; export just needs to USE it (P3) |
| `shutil.copy` of bundled guest ITP | `transform_guest_itp` read-transform-write (decision [38-04]) | v4.7 | GUI path already uses transform; CLI `_copy_hydrate_guest_itp` uses it too but with wrong guest_name |
| Built-in 2-entry `GUEST_MOLECULES` hard validation | `is_custom_guest` property + explicit custom metadata (Phase 40-03) | v4.7 | Custom guests accepted; export must read `guest_residue_name`/`guest_itp_path` |
| Per-atom-type hardcoded GAFF2 blocks | `parse_itp_atomtypes` + dedup (custom molecule path, Phase 34.2) | v4.6 | Pattern exists; just needs wiring into hydrate path |

**Deprecated/outdated:**
- `detect_guest_type_from_atoms` for hydrate guests (lines 1186, 1415) — superseded by `mol_type`; P3 removes these call sites.
- Hardcoded `["ch4","thf","co2","h2"]` gates in `write_multi_molecule_*` — exclude custom; replace with metadata lookup.

## Plan Hints (suggested, NOT binding — planner decides)

Aligned to the 4 roadmap-suggested plans. Each is a coherent, independently-verifiable unit. Order reflects dependency: 41-01 (P3) unblocks the writers' guest identification; 41-03 (GRO name) + 41-02 (atomtypes) make output valid; 41-04 (grompp) proves it.

### 41-01: P3 fix — use `mol_type` from `molecule_index` (EXPORT-05)
- Replace `detect_guest_type_from_atoms` at `gromacs_writer.py:1186` (`write_interface_gro_file`) and `:1415` (`write_interface_top_file`) with `molecule_index`-driven guest identification.
- Decide the metadata-threading mechanism for the CLI path (see Open Questions Q1).
- Tests: assert custom guest `mol_type` ("etoh_e2e") is recognized (not None); regression: built-in ch4/thf still detected.
- Verify no new `detect_guest_type_from_atoms` calls in the hydrate path.

### 41-03: GRO residue name `_H` suffix for custom guests (EXPORT-01, EXPORT-04)
- Fix `export_hydrate` (`hydrate_export.py:144,151,185`): use `config.guest_itp_path` + `config.guest_residue_name` for custom; `registry.register_hydrate_guest(config.guest_residue_name)`.
- Fix `write_multi_molecule_gro_file:1529,1541` and `write_multi_molecule_top_file:1638-1657` to emit `"{guest_residue_name}_H"` for custom `mol_type` (new param or mapping — see Open Questions Q2).
- Fix CLI `write_interface_gro_file:1194` to emit the custom residue name.
- Tests: GRO residues == `"MOL_H"`; `assert_gro_top_consistent` passes; `validate_gro_residue_name` not raised.

### 41-02: Custom guest atomtypes merging with dedup (EXPORT-02, EXPORT-03)
- Extract `_merge_custom_atomtypes(f, itp_path, written, label)` helper (DRY the triplicated pattern).
- Thread custom ITP path into `write_multi_molecule_top_file` and CLI `write_interface_top_file`.
- Call the helper after GAFF2 blocks, before `#include`.
- Tests: `.top [atomtypes]` contains `oh`/`ho`; `hc`/`c3`/`h1` NOT duplicated; bundled `etoh.itp` has `[atomtypes]` commented out; `_check_custom_atomtype_conflict` raises on a synthetic LJ-mismatch fixture.

### 41-04: grompp validation for custom guest exports (EXPORT-06)
- Add a transformed-ITP staging helper to `e2e_export_helpers.py` (apply `transform_guest_itp(content, guest_residue_name, "_H")` for custom guest ITPs; keep `_stage_itp_files` for built-ins).
- Add `@gmx_skipif` test(s): generate a custom-guest hydrate (ethanol sI, model on `test_e2e_custom_guest_hydrate.py` fixture); export via BOTH paths (GUI: `export_hydrate` with mocked dialog OR direct `write_multi_molecule_*`; CLI: `_run_export_step` OR direct `write_interface_*` + `copy_itp_files_for_structure`); stage tip4p-ice.itp + transformed etoh.itp; copy em.mdp; `run_gmx_grompp`; assert `exit_code==0`; assert `[molecules]` has `SOL` + `MOL_H`; assert GRO has `SOL` + `MOL_H` residues.
- Consider parameterizing over GUI vs CLI path and over lattice (sI/sII) if cheap.

### Cross-cutting
- Update `e2e_export_helpers.py` if a transformed-staging helper is added (non-test helper, no `test_` prefix).
- Ensure AGENTS.md constraints: atomic commits; specific exceptions in `pipeline.py`; no hardcoded TIP4P-ICE/`0.0299`/`4` (not expected in this phase's new code); `@gmx_skipif` on grompp tests; `QT_QPA_PLATFORM=offscreen` for any GUI test.

## Open Questions

1. **[Q1 — CLI metadata threading]** `write_interface_gro_file`/`write_interface_top_file` take an `InterfaceStructure` (no `config`). The CLI `_run_export_step` (pipeline.py:806) builds the wrapper and DROPS `config.guest_residue_name`/`guest_itp_path`/`is_custom_guest`. **Options:** (a) Add custom-guest fields to `InterfaceStructure` (or reuse `custom_*` fields? — but those mean Tab-5 custom molecules, different concept); (b) Pass `config`/a `custom_guest_info` dict alongside the wrapper to the writers; (c) Switch CLI hydrate export to `write_multi_molecule_*` (same as GUI), eliminating the `write_interface_*` hydrate path. **Recommendation:** (c) is cleanest long-term (removes the P3 call sites entirely + dedup logic) but is a bigger change; (a)/(b) is more surgical. **Planner decides.** Confidence: HIGH that the bug exists; MEDIUM on the best fix shape.

2. **[Q2 — GUI writer residue-name API]** `write_multi_molecule_gro_file`/`write_multi_molecule_top_file` need the custom residue name (`"MOL_H"`) but the `MoleculetypeRegistry` key mechanism can't cleanly carry it (Pitfall 6). **Options:** (a) New param `guest_residue_names: dict[str,str] | None` (mol_type→`"MOL_H"`) mirroring the existing `itp_files` param; (b) New param `custom_guest_info: dict | None` with residue name + ITP path; (c) Extend `MoleculetypeRegistry` with a custom-name override that decouples the key from the name. **Recommendation:** (a) — smallest, mirrors `itp_files`, keeps registry for built-ins. **Planner decides.** Confidence: HIGH that the registry alone is insufficient; MEDIUM on the exact param shape.

3. **[Q3 — Should `write_interface_*` hydrate path be retired?]** The CLI uses `write_interface_*` for hydrate export while the GUI uses `write_multi_molecule_*` — an inconsistency. If Phase 41 switches CLI to `write_multi_molecule_*` (Q1 option c), the P3 call sites at lines 1186/1415 become dead code for hydrates (still used by real interface structures). **Not blocking** — but worth a planner decision to avoid maintaining two hydrate export paths. Confidence: MEDIUM (architectural judgment).

4. **[Q4 — Transformed-ITP staging for tests]** `_stage_itp_files` (e2e_export_helpers.py:399) applies only `comment_out_atomtypes_in_itp`, NOT the full `transform_guest_itp` (`_H` rename). For custom guest grompp tests, the staged `etoh.itp` must have moleculetype `MOL_H` (matching `.top [molecules]`). **Recommendation:** add a `transform_guest=True` flag or a separate `_stage_transformed_guest_itp` helper. Confidence: HIGH that the gap exists (read the code); MEDIUM on the helper API.

## Sources

### Primary (HIGH confidence — source code read directly)
- `quickice/output/gromacs_writer.py` — read lines 1-1749, 2111-2296, 2572-2711; verified: `validate_gro_residue_name`(25), `transform_guest_itp`(640, validate at 677), `parse_itp_atomtypes`(473, 7-col handler at 516), `comment_out_atomtypes_in_itp`(524), `_rewrite_atoms_section_resname`(571), `_check_custom_atomtype_conflict`(164), `_write_atomtypes_block`(136), `_format_custom_atomtype_line`(118), `MOLECULE_TO_GROMACS`(239), `write_multi_molecule_gro_file`(1473, gate 1529, fallback 1541-1545), `write_multi_molecule_top_file`(1591, registry 1638-1657, itp_files 1666-1673, atomtypes 1715-1729, #include 1735), `detect_guest_type_from_atoms`(1313, body 1326-1364), `write_interface_gro_file`(1007, detect 1186, fallback 1194, count_guest_atoms 1201), `write_interface_top_file`(1367, detect 1415, fallback 1430-1434, #include 1442-1445, [molecules] 1466-1470), `write_custom_molecule_top_file`(2572, atomtypes merge 2648-2670), `write_ion_top_file`(2111, atomtypes merge 2238-2262)
- `quickice/gui/hydrate_export.py` — read full (197 lines); `_get_hydrate_guest_itp_path`(44), `export_hydrate`(90, lines 144/151/152/167/185)
- `quickice/cli/pipeline.py` — read `_run_export_step`(729-849); hydrate wrapper(806-819), writer dispatch(820-821), `copy_itp_files_for_structure`(836)
- `quickice/cli/itp_helpers.py` — read full (416 lines); `get_hydrate_guest_itp_path`(20), `_copy_hydrate_guest_itp`(167, except FileNotFoundError 193), `_resolve_guest_type_for_hydrate_step`(201, strategy 2 at 223), `copy_itp_files_for_structure`(242, hydrate branch 277-285)
- `quickice/structure_generation/types.py` — read full; `HydrateConfig`(430, `guest_itp_path`:478, `guest_residue_name`:479, `guest_gro_path`:480, `__post_init__`:482, custom validation 503-527, `is_custom_guest`:564), `HydrateStructure`(914, `config`:939, `guest_itp_path`:947), `MoleculeIndex`(62)
- `quickice/structure_generation/hydrate_generator.py` — read `_build_molecule_index`(556, mol_type=config.guest_type at 625, guest_residue_name fallback 609), `generate`→`HydrateStructure`(184-198, config passed 189, guest_itp_path propagated 197)
- `quickice/structure_generation/moleculetype_registry.py` — read full (166 lines); `register_hydrate_guest`(46, `f"{molecule}_H"`, key `f"hydrate_{molecule}"`), `RESERVED_NAMES`(35)
- `quickice/structure_generation/custom_guest_bridge.py` — read `validate_custom_guest_files`(177, resname ≤3 check 254-261, comb-rule check 263+)
- `quickice/utils/molecule_utils.py` — read `count_guest_atoms`(21, only ch4/thf/Me/H2)
- `quickice/data/custom/etoh.itp` — read full (85 lines); atomtypes(3-9, 7-col), moleculetype `etoh`(13), atoms resname `MOL`(17-25)
- `quickice/data/custom/etoh.gro` — read full (12 lines); 9 atoms, resname `MOL`
- `tests/e2e_export_helpers.py` — read full (603 lines); `run_gmx_grompp`(559), `_stage_itp_files`(399, NO transform), `assert_gro_top_consistent`(485), `assert_itp_completeness`(456), `ETOH_GRO/ITP`(45-46)
- `tests/test_e2e_gmx_validation.py` — read (1055+ lines); `@gmx_skipif` classes, `gmx_workspace` fixture(64), F1-F7+sII patterns
- `tests/test_e2e_gmx_param_validation.py` — read (90-209); `ChainParams`(61), parametric pattern, `_WRITERS`(200)
- `tests/test_e2e_custom_guest_hydrate.py` — read full (274 lines); Phase 40 fixture constants(31-36), `custom_guest_hydrate` fixture(39-62)
- `tests/test_output/test_gromacs_export_hydrate.py` — read (1-199); `HydrateGROMACSExporter` + `mock_hydrate_save_dialog` pattern
- `tests/conftest.py` — read (1-247); `gmx_skipif`(24), `hydrate_sI_ch4_structure`(118)
- `tests/em.mdp` — read; `integrator=steep`, PME, cutoffs 1.0, `constraints=none`
- `gmx` on PATH: verified `/data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx`

### Secondary (MEDIUM confidence)
- `tests/test_output/conftest.py` — `simple_hydrate_*`/`mock_hydrate_save_dialog` fixture location (via grep, not fully read — planner should confirm exact fixture signatures when writing GUI-path tests)

### Tertiary (LOW confidence)
- None. All claims are source-verified. The only labeled guesses are the Open Questions (Q1–Q4), explicitly marked as planner decisions.

## Metadata

**Confidence breakdown:**
- Standard stack (functions/files/line numbers): HIGH — every `file:line` read directly
- Architecture (code paths A & B): HIGH — traced step-by-step from source
- Bugs (A–G): HIGH — each verified by reading the exact line and its control flow
- P3 fix scope (call sites): HIGH — grep-enumerated all 9+1 call sites; enclosing functions identified
- Atomtypes merge pattern: HIGH — read the verbatim reference code (lines 2648-2670, 2238-2262)
- Test fixtures: HIGH — fixture files exist & read; gmx available; helpers read
- Open Questions (Q1–Q4 fix shapes): MEDIUM — the BUGS are certain; the best API is a judgment call for the planner

**Research date:** 2026-07-03
**Valid until:** 2026-08-03 (30 days — stable codebase; verify line numbers haven't shifted if Phase 41 work begins after other commits)
