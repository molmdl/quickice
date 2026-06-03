# Phase e2e-compute-export: E2E Compute→Export Bridge Testing - Research

**Researched:** 2026-06-03
**Domain:** GROMACS export pipeline bridging (computation output → writer functions → file validation)
**Confidence:** HIGH

## Summary

This phase bridges two existing complete test phases: `e2e-api-workflow` (112 tests, validates computation pipeline with real GenIce2 structures but stops before export) and `e2e-export-test` (30+ tests, validates export pipeline but uses synthetic/mock fixtures). The gap is that no tests validate that REAL computation pipeline output flows correctly through GROMACS writer functions.

Research identified 10 writer functions across 5 structure types (Candidate, InterfaceStructure, CustomMoleculeStructure, SoluteStructure, IonStructure), each producing .gro/.top/.itp files. The existing e2e-api-workflow conftest.py provides 12 module-scoped real GenIce2 fixtures, and test_e2e_workflow_chains.py provides 9 reusable chain-building helpers. The test_output/conftest.py provides a factory-pattern mock dialog fixture, but for bridge tests we call writer functions DIRECTLY (bypassing QFileDialog entirely), so no mock dialogs are needed.

Two known bugs/limitations affect bridge testing: (1) P0 SoluteStructure→IonInserter AttributeError requiring the `_solute_to_ion_source()` workaround, and (2) `guest_nmolecules` loss through CustomMoleculeStructure (field doesn't exist on that type). Both have documented workarounds from e2e-api-workflow Plan 05.

**Primary recommendation:** Call writer functions directly (no QFileDialog mocking), use real GenIce2 fixtures from tests/conftest.py, reuse chain-building helpers from test_e2e_workflow_chains.py, and add GRO/TOP parsing helpers to tests/conftest.py for content validation.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 8.x | Test framework | Project standard, existing fixtures |
| numpy | 2.x | Position array operations | Required by all structure types |
| GenIce2 | 2.2.13.1 | Real ice structure generation | Production library, used by conftest fixtures |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib.Path | stdlib | File path handling | All GRO/TOP/ITP file operations |
| quickice.output.gromacs_writer | current | Writer functions being tested | Direct import, no GUI layer |
| quickice.structure_generation.gromacs_ion_export | current | Ion ITP generation | write_ion_itp() for ion.itp |
| quickice.structure_generation.moleculetype_registry | current | CH4_H/CH4_L naming | Must create registry per test chain |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Direct writer calls | Exporter class calls with QFileDialog mocking | Direct calls are simpler, no GUI setup needed, tests computation→export interface specifically |
| Inline chain helpers | Shared fixture for pre-built chains | Inline gives per-test control; fixtures would be fragile due to chain variability |

**Installation:**
No new packages needed — all dependencies already in project.

## Architecture Patterns

### Recommended Project Structure
```
tests/
├── conftest.py                          # GenIce2 fixtures + GRO/TOP parsing helpers (ADD parsing helpers)
├── test_e2e_compute_export.py           # Single-structure export bridge tests (NEW)
├── test_e2e_compute_export_chain.py     # Full-chain export bridge tests (NEW)
├── test_e2e_workflow_chains.py          # Chain helpers to copy/reuse
└── test_output/
    ├── conftest.py                      # Synthetic fixtures + mock dialogs (NOT used for bridge)
    ├── test_gromacs_export_chain.py     # Synthetic chain export tests (reference only)
    └── ...
```

### Pattern 1: Direct Writer Function Calls (No GUI)
**What:** Import writer functions directly, call with structure + tmp_path, validate output
**When to use:** ALL bridge tests — this is the core pattern for this phase
**Example:**
```python
# Source: quickice/output/gromacs_writer.py
from quickice.output.gromacs_writer import (
    write_gro_file, write_top_file,
    write_interface_gro_file, write_interface_top_file,
    write_custom_molecule_gro_file, write_custom_molecule_top_file,
    write_solute_gro_file, write_solute_top_file,
    write_ion_gro_file, write_ion_top_file,
)

def test_ice_export(ice_ih_candidate, tmp_path):
    gro_path = str(tmp_path / "ice.gro")
    write_gro_file(ice_ih_candidate, gro_path)
    # Parse and validate...
```

### Pattern 2: Chain Building with Workarounds
**What:** Build computation chain using helpers, then export the final structure
**When to use:** F1-F7 chain export tests
**Example:**
```python
# Source: tests/test_e2e_workflow_chains.py (lines 46-111)
# Build chain: Interface → Custom → Solute → Ion
custom = _insert_custom_molecules(interface_slab, n_molecules=3)
solute = _insert_solutes(custom, solute_type='CH4', concentration=0.3)
ion = _insert_ions_from_solute(solute, concentration=0.15)  # Uses BUG I5 workaround

# Export final structure
write_ion_gro_file(ion, str(tmp_path / "f1.gro"))
write_ion_top_file(ion, str(tmp_path / "f1.top"))
```

### Pattern 3: GRO Content Parsing
**What:** Parse .gro residue names and atom counts for validation
**When to use:** Every .gro file validation in bridge tests
**Example:**
```python
# Source: tests/test_gromacs_molecule_ordering.py (lines 20-62)
# GRO format: residue name at columns [5:10] (0-indexed)
def parse_gro_residue_names(gro_path: str) -> list[str]:
    residue_names = []
    with open(gro_path, 'r') as f:
        lines = f.readlines()
    if len(lines) < 3:
        return residue_names
    for line in lines[2:]:
        if len(line.strip()) < 20:
            continue
        res_name = line[5:10].strip()
        if res_name and not res_name.replace('.', '').replace('-', '').isspace():
            residue_names.append(res_name)
    return residue_names
```

### Anti-Patterns to Avoid
- **Don't use QFileDialog mocking for bridge tests:** The test_output/conftest.py `mock_save_dialog` factory is for testing the GUI exporter classes (SoluteGROMACSExporter, etc.). Bridge tests should call writer functions directly, bypassing the GUI layer entirely. This tests the actual computation→export interface.
- **Don't use synthetic fixtures for bridge tests:** The test_output/conftest.py fixtures (simple_candidate, simple_interface, etc.) are synthetic structures with 1-2 molecules. Bridge tests MUST use real GenIce2 fixtures from tests/conftest.py to validate real-world data flow.
- **Don't import conftest helpers via `from tests.conftest`:** Use `from conftest import ...` (pytest's test root resolution). The `tests/` directory is the test root; `from tests.conftest` doesn't work with pytest's discovery mechanism.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GRO residue name parsing | Custom column parser | `parse_gro_residue_names` from test_gromacs_molecule_ordering.py | Already implemented, battle-tested with real GRO files |
| Chain building helpers | New chain construction | Copy from test_e2e_workflow_chains.py (lines 46-169) | Already tested with 12 workflow chain tests, includes bug workarounds |
| Bug I5 workaround | Custom attribute injection | `_solute_to_ion_source()` from workflow_chains.py | Matches GUI behavior, preserves all conditional attrs |
| Moleculetype registry setup | Manual name registration | `MoleculetypeRegistry.register_hydrate_guest()` + `register_liquid_solute()` | Standard API, returns CH4_H/CH4_L names |
| Ion ITP generation | Custom ITP writer | `write_ion_itp()` from gromacs_ion_export.py | Madrid2019 parameters, tested in e2e-export-test-07 |

**Key insight:** The chain-building helpers in test_e2e_workflow_chains.py encapsulate 5 months of iteration on bugs, workarounds, and edge cases. Reuse them wholesale — don't re-derive.

## Common Pitfalls

### Pitfall 1: SoluteStructure→IonInserter AttributeError (BUG I5)
**What goes wrong:** `IonInserter.replace_water_with_ions()` calls `getattr(source_structure, 'solute_type')` and other solute-specific attributes. When `source_structure` is a `SoluteStructure`, these attributes exist on the solute itself but NOT on `solute.interface_structure`, which is what IonInserter actually accesses.
**Why it happens:** API design mismatch — IonInserter expects a flat structure with all attributes, but SoluteStructure stores solute attrs on itself and ice/water attrs on nested `interface_structure`.
**How to avoid:** Use `_solute_to_ion_source(solute)` workaround that copies solute attrs to `solute.interface_structure` before passing to IonInserter.
**Warning signs:** `AttributeError: 'InterfaceStructure' object has no attribute 'solute_type'`

### Pitfall 2: guest_nmolecules Lost Through CustomMoleculeStructure
**What goes wrong:** When the chain passes through `CustomMoleculeInserter`, the output `CustomMoleculeStructure` does NOT have a `guest_nmolecules` field. Only `guest_atom_count` is preserved.
**Why it happens:** `CustomMoleculeStructure` dataclass doesn't define `guest_nmolecules` — it only has `guest_atom_count: int = 0`.
**How to avoid:** In assertions, check `guest_atom_count > 0` instead of `guest_nmolecules > 0` when the chain passes through the custom molecule step. Document this as a known limitation.
**Warning signs:** `ion.guest_nmolecules == 0` despite `ion.guest_atom_count > 0` in chains that went through CustomMoleculeStructure.

### Pitfall 3: GRO 5-Character Residue Name Limit
**What goes wrong:** GROMACS .gro format allows only 5 characters for residue names. Truncation can cause name collisions.
**Why it happens:** Writer uses `res_name[:5]` for custom and solute residue names. "CH4_L" is 5 chars (fits), "THF_L" is 5 chars (fits), "ETOH" is 4 chars (fits), but longer names get truncated.
**How to avoid:** In assertions, match against the truncated 5-char names. For CH4_L and THF_L, they fit exactly. Custom molecule names depend on `moleculetype_name[:5]`.
**Warning signs:** Unexpected residue name truncation in parsed .gro files.

### Pitfall 4: TIP4P-ICE 3→4 Atom Expansion
**What goes wrong:** Ice molecules stored as 3 atoms (O, H, H) expand to 4 atoms (OW, HW1, HW2, MW) at export time. Forgetting this leads to incorrect atom count expectations.
**Why it happens:** The MW (massless virtual site) is computed at export time, not stored in the structure.
**How to avoid:** Expected atom count = `ice_nmolecules * 4` (NOT `* 3`). Water molecules are already 4 atoms each. Hydrate ice is already 4 atoms (OW, HW1, HW2, MW).
**Warning signs:** Atom count mismatch where .gro has MORE atoms than `positions.shape[0]`.

### Pitfall 5: solute_molecule_indices Are Relative to solute_positions
**What goes wrong:** `solute_molecule_indices` (e.g., `[(0, 5)]`) index into `solute_positions`, NOT into the main `positions` array.
**Why it happens:** SoluteStructure stores solute positions separately from interface positions.
**How to avoid:** When calculating atom counts from solute_molecule_indices, use `len(solute_structure.atom_names)` or `solute_structure.positions.shape[0]`, not the main positions array.
**Warning signs:** IndexError when indexing into main positions with solute_molecule_indices.

### Pitfall 6: Registry Must Be Populated Before Writer Use
**What goes wrong:** Writer functions call `registry.get_gromacs_name()` which returns `source.upper()` if the key isn't registered, leading to incorrect residue names (e.g., "LIQUID_CH4" instead of "CH4_L").
**Why it happens:** Registry is empty by default and must be explicitly populated with `register_hydrate_guest()` or `register_liquid_solute()`.
**How to avoid:** Always call `registry.register_liquid_solute("CH4")` (or THF) before creating SoluteStructure, and `registry.register_hydrate_guest("CH4")` for hydrate chain tests BEFORE calling `insert_solutes()`.
**Warning signs:** Unexpected uppercase residue names like "LIQUID_CH4" in .gro output.

## Code Examples

Verified patterns from official sources:

### Writer Function Signatures (Complete Inventory)
```python
# Source: quickice/output/gromacs_writer.py

# 1. Ice Candidate → .gro + .top + tip4p-ice.itp
write_gro_file(candidate: Candidate, filepath: str) -> None
write_top_file(candidate: Candidate, filepath: str) -> None

# 2. Interface → .gro + .top + tip4p-ice.itp + optional {guest}_hydrate.itp
write_interface_gro_file(iface: InterfaceStructure, filepath: str) -> None
write_interface_top_file(iface: InterfaceStructure, filepath: str) -> None

# 3. Custom Molecule → .gro + .top + tip4p-ice.itp + etoh.itp + optional {guest}_hydrate.itp
write_custom_molecule_gro_file(custom_structure: CustomMoleculeStructure, filepath: str) -> None
write_custom_molecule_top_file(custom_structure: CustomMoleculeStructure, filepath: str) -> None

# 4. Solute → .gro + .top + tip4p-ice.itp + {solute}_liquid.itp + optional {guest}_hydrate.itp + optional etoh.itp
write_solute_gro_file(solute_structure: SoluteStructure, filepath: str) -> None
write_solute_top_file(solute_structure: SoluteStructure, filepath: str) -> None

# 5. Ion → .gro + .top + tip4p-ice.itp + ion.itp + optional {guest}_hydrate.itp + optional {solute}_liquid.itp + optional etoh.itp
write_ion_gro_file(ion_structure: IonStructure, filepath: str) -> None
write_ion_top_file(ion_structure: IonStructure, filepath: str) -> None

# 6. Multi-molecule (used by hydrate export)
write_multi_molecule_gro_file(positions, molecule_index, cell, filepath, title, atom_names) -> None
write_multi_molecule_top_file(molecule_index, filepath, system_name, itp_files, registry) -> None

# 7. Utility functions
get_tip4p_itp_path() -> Path
comment_out_atomtypes_in_itp(itp_content: str) -> str
detect_guest_type_from_atoms(atom_names: list[str]) -> str | None
get_hydrate_guest_residue_name(guest_type: str) -> str
compute_mw_position(o_pos, h1_pos, h2_pos) -> np.ndarray
parse_itp_residue_name(itp_path: str | Path) -> str | None
parse_itp_atomtypes(itp_path: str | Path) -> list[tuple]
wrap_positions_into_box(positions, cell) -> np.ndarray
wrap_molecules_into_box(positions, molecule_index, cell) -> np.ndarray

# 8. Ion ITP generation (separate module)
# Source: quickice/structure_generation/gromacs_ion_export.py
write_ion_itp(output_path: Path | str, na_count: int, cl_count: int) -> None
```

### Molecule Ordering in GRO Output
```python
# Source: quickice/output/gromacs_writer.py (write_ion_gro_file, lines 1316-1361)
# Molecule ordering in .gro output:
# Pass 1: SOL (ice + water combined)
# Pass 2: guest molecules (CH4, THF from hydrate cages → CH4_H, THF_H)
# Pass 3: custom molecules (ETOH, etc.)
# Pass 4: solute molecules (CH4_L, THF_L liquid solutes)
# Pass 5: NA ions
# Pass 6: CL ions

# .top [molecules] section ordering matches .gro:
# SOL → guest_res_name → custom_mol_name → solute_mol_name → NA → CL
```

### [molecules] Section Format in .top
```python
# Source: quickice/output/gromacs_writer.py (write_ion_top_file, lines 1811-1840)
# Format: {name:<17s} {count}
# Example output:
# SOL              128
# CH4_H            8
# ETOH             3
# CH4_L            5
# NA               12
# CL               12
```

### Chain Building Helper (F1 Full Chain)
```python
# Source: tests/test_e2e_workflow_chains.py (lines 46-111)
DATA_DIR = Path(__file__).resolve().parent.parent / "quickice" / "data" / "custom"
ETOH_GRO = DATA_DIR / "etoh.gro"
ETOH_ITP = DATA_DIR / "etoh.itp"

def _insert_custom_molecules(interface, n_molecules=3):
    config = CustomMoleculeConfig(
        placement_mode="random",
        gro_path=ETOH_GRO,
        itp_path=ETOH_ITP,
        molecule_count=n_molecules,
    )
    inserter = CustomMoleculeInserter(config)
    return inserter.place_random(interface, n_molecules)

def _insert_solutes(source_structure, solute_type='CH4', concentration=0.3, seed=42):
    config = SoluteConfig(concentration_molar=concentration, solute_type=solute_type)
    inserter = SoluteInserter(config=config, seed=seed)
    return inserter.insert_solutes(source_structure, config)

def _solute_to_ion_source(solute):
    """BUG I5 workaround: attach solute attrs to interface_structure."""
    interface_for_ions = solute.interface_structure
    interface_for_ions.solute_type = solute.solute_type
    interface_for_ions.solute_positions = solute.positions
    interface_for_ions.solute_atom_names = solute.atom_names
    interface_for_ions.solute_n_molecules = solute.n_molecules
    interface_for_ions.solute_molecule_indices = solute.molecule_indices
    interface_for_ions.solute_registry = solute.registry
    if solute.custom_molecule_count > 0:
        interface_for_ions.custom_molecule_count = solute.custom_molecule_count
        interface_for_ions.custom_molecule_atom_count = solute.custom_molecule_atom_count
        interface_for_ions.custom_molecule_positions = solute.custom_molecule_positions
        interface_for_ions.custom_molecule_atom_names = solute.custom_molecule_atom_names
        interface_for_ions.custom_molecule_moleculetype = solute.custom_molecule_moleculetype
        interface_for_ions.custom_gro_path = solute.custom_gro_path
        interface_for_ions.custom_itp_path = solute.custom_itp_path
    return interface_for_ions

def _insert_ions_from_solute(solute, concentration=0.15, seed=42):
    ion_source = _solute_to_ion_source(solute)
    return _insert_ions(ion_source, concentration, seed)
```

### GRO/TOP Parsing Helpers (to add to conftest.py)
```python
# Source: tests/test_gromacs_molecule_ordering.py (lines 20-62)
# Already exists locally — refactor to conftest.py

def parse_gro_residue_names(gro_path: str) -> list[str]:
    """Parse residue names from GROMACS .gro file.
    GRO format: residue name at columns [5:10] (0-indexed)."""
    residue_names = []
    with open(gro_path, 'r') as f:
        lines = f.readlines()
    if len(lines) < 3:
        return residue_names
    for line in lines[2:]:
        if len(line.strip()) < 20:
            continue
        res_name = line[5:10].strip()
        if res_name and not res_name.replace('.', '').replace('-', '').isspace():
            residue_names.append(res_name)
    return residue_names

def parse_gro_atom_count(gro_path: str) -> int:
    """Parse atom count from GROMACS .gro file line 2."""
    with open(gro_path, 'r') as f:
        lines = f.readlines()
    if len(lines) < 2:
        return 0
    return int(lines[1].strip())

def parse_top_molecules(top_path: str) -> dict[str, int]:
    """Parse [molecules] section from GROMACS .top file."""
    molecules = {}
    in_molecules = False
    with open(top_path, 'r') as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith('['):
                in_molecules = '[ molecules ]' in stripped.lower() or stripped == '[ molecules ]'
                continue
            if not in_molecules:
                continue
            if not stripped or stripped.startswith(';') or stripped.startswith('#'):
                continue
            parts = stripped.split()
            if len(parts) >= 2:
                try:
                    molecules[parts[0]] = int(parts[1])
                except ValueError:
                    continue
    return molecules

def parse_top_includes(top_path: str) -> list[str]:
    """Parse #include directives from GROMACS .top file."""
    includes = []
    with open(top_path, 'r') as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith('#include'):
                start = stripped.find('"')
                end = stripped.rfind('"')
                if start != -1 and end != -1 and end > start:
                    includes.append(stripped[start+1:end])
    return includes
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Stuttered [molecules] entries | Grouped molecule counts | e2e-export-test-08 | All SOL counted together, not ice-SOL then water-SOL |
| guest.itp | {guest}_hydrate.itp | Quick Task 028 (2026-05-16) | Hydrate guests get _H suffix, separate from generic guest ITP |
| CH4/THF in [molecules] | CH4_H/CH4_L via MoleculetypeRegistry | v4.5 Phase 32-34 | Same molecule type from different sources gets distinct GROMACS names |
| 3-atom ice export | TIP4P-ICE 4-atom export | v2.1 Phase 14 | MW virtual site computed at export time |
| Synthetic-only export tests | Synthetic (test_output/) + real GenIce2 (tests/) | e2e-api-workflow + e2e-export-test | Bridge tests needed to connect both |

**Deprecated/outdated:**
- `build_molecule_index` function: Removed (Quick Task 021), molecule_index built by inserters
- `CH4_HYD` residue name: Replaced by `CH4_H` (Quick Task 028, 2026-05-16)
- `CH4_LIQ`/`THF_LIQ` names: Replaced by `CH4_L`/`THF_L` (5 chars max for GRO format)

## Existing Draft Plan Coverage and Gaps

### What the Draft Plans Cover (e2e-compute-export-01-PLAN.md and -02-PLAN.md)

**Plan 01 (Single-Structure Export):**
- ✅ GRO/TOP parsing helpers added to conftest.py (4 functions)
- ✅ parse_gro_residue_names refactored from test_gromacs_molecule_ordering.py
- ✅ ~12 single-structure export tests (Ice, Interface, Interface+Hydrate, Custom, Solute, Ion)
- ✅ Direct writer function calls (no QFileDialog)
- ✅ Real GenIce2 fixtures used
- ✅ Atom count validation

**Plan 02 (Full Chain Export):**
- ✅ F1, F2, F3, F4, F6, F7 chain export tests (~12 tests)
- ✅ Molecule ordering in .gro validated for each chain
- ✅ [molecules] section validated for each chain
- ✅ ITP bundling validation (existence + [moleculetype] check)
- ✅ Atom conservation tests
- ✅ THF hydrate chain (F4) with guest_nmolecules limitation handling
- ✅ BUG I5 workaround usage (_solute_to_ion_source)

### Gaps Identified in Draft Plans

1. **Missing: Hydrate candidate export bridge test** — Plan 01 tests ice candidates but not hydrate structure export via HydrateGROMACSExporter (which uses write_multi_molecule_gro_file/write_multi_molecule_top_file). The hydrate_slab fixture IS in conftest.py but hydrate-specific export via multi-molecule writers is not tested.

2. **Missing: Interface→Custom→Solute→Ion cumulative ITP verification at the writer level** — Plan 02 checks ITP existence in data directory, but doesn't verify that the EXPORTED ITP files in the tmp_path directory contain valid [moleculetype] sections for the specific molecule types in the chain (e.g., ion.itp has both NA and CL sections, etoh.itp has ETOH section).

3. **Missing: .top [atomtypes] section validation** — The [atomtypes] section in .top must include atom types for ALL molecule types in the system (TIP4P-ICE water + Madrid2019 ions + GAFF2 guests/solutes/custom). No test validates that atom types are present for each molecule type.

4. **Missing: write_interface_gro_file with hydrate candidates having 4-atom ice** — Hydrate ice starts with 4 atoms (OW, HW1, HW2, MW), not 3. The interface writer handles this via `has_ow_in_ice` detection, but this code path isn't explicitly tested with real hydrate-generated data.

5. **Gap: Plan 01 Task 1 `from conftest import parse_gro_residue_names` may not work** — pytest's conftest.py auto-imports fixtures but does NOT auto-import module-level functions. The `from conftest import ...` syntax requires conftest.py to be on the import path, which depends on how pytest is invoked. Alternative: use `pytest.importorskip` or add tests/ to sys.path, or use a separate helper module.

## Open Questions

1. **Import path for conftest.py helper functions**
   - What we know: pytest auto-imports fixtures from conftest.py, but NOT module-level functions
   - What's unclear: Whether `from conftest import parse_gro_residue_names` works from test files in the same `tests/` directory
   - Recommendation: Test this explicitly — if `from conftest import X` fails, move helpers to a separate `tests/helpers.py` module and import from there

2. **IonStructure.molecule_index contents after _solute_to_ion_source workaround**
   - What we know: The workaround attaches solute attrs to interface_structure, and IonInserter builds its own molecule_index from that
   - What's unclear: Whether guest molecule entries appear in IonStructure.molecule_index when the chain goes through CustomMoleculeStructure (guest_nmolecules is lost)
   - Recommendation: Check `ion.molecule_index` for "guest" entries in F1 and F4 chains; if missing, guest atoms won't appear in .gro output either

3. **Expected CH4_L vs CH4_LIQ in GRO residue names**
   - What we know: `MoleculetypeRegistry.register_liquid_solute("CH4")` returns "CH4_L" (5 chars)
   - What's unclear: Whether the writer truncates "CH4_L" to "CH4_L" (it already fits in 5 chars) or does something unexpected
   - Recommendation: Assert against "CH4_L" in GRO residue name parsing — it's 5 chars, fits exactly

## Sources

### Primary (HIGH confidence)
- quickice/output/gromacs_writer.py — Complete writer function inventory (2559 lines, all signatures verified)
- quickice/structure_generation/types.py — All structure type dataclass definitions (718 lines)
- quickice/structure_generation/gromacs_ion_export.py — Ion ITP generation (163 lines)
- quickice/gui/export.py — All 5 GROMACS exporter classes (929 lines, showing the GUI→writer bridge)
- quickice/structure_generation/moleculetype_registry.py — Registry API (166 lines)
- tests/conftest.py — 12 module-scoped GenIce2 fixtures (201 lines)
- tests/test_e2e_workflow_chains.py — 9 chain-building helpers + F1-F7 test structure (594 lines)
- tests/test_gromacs_molecule_ordering.py — parse_gro_residue_names implementation (346 lines)
- tests/test_output/conftest.py — Synthetic fixtures + mock dialog factory (499 lines)
- tests/test_output/test_gromacs_export_chain.py — Synthetic chain export test pattern (568 lines)
- tests/test_output/test_gromacs_export_ion.py — Ion export test pattern (278 lines)
- tests/test_output/test_gromacs_export_solute.py — Solute export test pattern (195 lines)
- .planning/STATE.md — All prior decisions including workarounds and limitations

### Secondary (MEDIUM confidence)
- .planning/phases/e2e-compute-export/e2e-compute-export-01-PLAN.md — Draft Plan 01 structure
- .planning/phases/e2e-compute-export/e2e-compute-export-02-PLAN.md — Draft Plan 02 structure

### Tertiary (LOW confidence)
- None — all findings verified from source code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries/packages verified in source code
- Architecture: HIGH — writer function signatures and structure types verified line-by-line
- Pitfalls: HIGH — all 6 pitfalls verified in source code and prior test files
- Code examples: HIGH — all examples extracted directly from source with line numbers
- Gaps identification: MEDIUM — draft plans reviewed but execution may reveal additional gaps

**Research date:** 2026-06-03
**Valid until:** 2026-07-03 (stable — no external library changes expected)
