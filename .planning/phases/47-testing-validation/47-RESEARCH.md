# Phase 47: Testing & Validation - Research

**Researched:** 2026-07-12
**Domain:** GROMACS grompp validation tests for filled-ice lattice exports (CLI hydrate branch)
**Confidence:** HIGH

## Summary

Phase 47's roadmap text for plan 47-05 is **stale** and overstates the gap. The
roadmap says "filled-ice (c0te/c1te/c2te/ice1hte) grompp not explicitly tested",
but Phase 45 (completed AFTER the roadmap text was written) already closed
most of this gap. After verifying every claim against the actual test files and
running the tests, the **true remaining gap is even smaller than the
orchestrator's pre-discovery suggested**.

**Correction to the orchestrator's pre-discovery:** The orchestrator's Finding
1 claimed `tests/test_e2e_lattice_cross_tab_cli.py` "does NOT run grompp (no
`run_gmx_grompp` or `@gmx_skipif` in that file — confirmed via grep)". This is
**factually wrong**. That file DOES run grompp for c2te/ice1hte: line 66 imports
`gmx_skipif`, line 79 imports `run_gmx_grompp`, line 353 applies `@gmx_skipif`,
and lines 303-309 call `run_gmx_grompp` with `assert exit_code == 0`. The
parametrized `test_lattice_cross_tab_cli_grompp[c2te]` and
`[ice1hte]` cases PASS (verified by running them). What that test does NOT
cover is the **hydrate-only** branch of `_run_export_step` (it covers the
interface / solute / ion branches, which use a slab-wrapped InterfaceStructure).

**The actual gap (the only real remaining work for 47-05 / TEST-08):** A CLI
**hydrate-only branch** grompp test for the two **orthorhombic** filled-ice
lattices **c2te** and **ice1hte** — i.e., a direct mirror of
`test_e2e_triclinic_hydrate_cli_export_grompp[c0te/c1te]` but for c2te/ice1hte.
This exercises the `HydrateStructure → InterfaceStructure` wrapper path
(`pipeline.py:886-929`) with the lattices' **native orthorhombic supercell**
(3x3x3 for c2te = 2.65 nm shortest, 4x4x4 for ice1hte = 2.76 nm), which is a
distinct cell geometry from the 3x3x8 nm slab already tested via the interface
branch. Every helper, pattern, and supercell size needed already exists and is
proven; this is a one-file, one-parametrized-test addition.

**Primary recommendation:** Create `tests/test_e2e_filled_ice_cli_hydrate_grompp.py`
with a module-scoped fixture mirroring `test_e2e_mixed_filled_ice_gui.py`'s
`filled_ice_hydrates` (c2te=3x3x3, ice1hte=4x4x4, built-in ch4) and a
parametrized `@gmx_skipif` test mirroring
`test_e2e_triclinic_hydrate_cli_export_grompp` (CLI hydrate branch via
`CLIPipeline` + `_hydrate_result` + `_run_export_step`), asserting CH4_H + SOL
+ `ch4_hydrate.itp` + `assert_itp_completeness` + `assert_gro_top_consistent` +
`gmx grompp` rc=0.

## Standard Stack

The established libraries/tools for this domain (all already in the project):

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.0.2 | Test runner (default discovery, no pytest.ini) | Project standard (AGENTS.md) |
| GROMACS `gmx` | (on PATH) | `gmx grompp` topology validation | Real simulation-input validation |
| GenIce2 | (conda) | Hydrate lattice generation (c2te/ice1hte) | Phase 39 lattice source |
| `quickice.structure_generation` | (local) | `HydrateStructureGenerator`, `HydrateConfig`, `HYDRATE_LATTICES` | Core under test |
| `quickice.cli.pipeline` | (local) | `CLIPipeline._run_export_step` hydrate branch | The code path under test |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tests/e2e_export_helpers.py` | (local) | GRO/TOP parsing + grompp runner + consistency asserts | EVERY assertion in the new test — do not reimplement |
| `tests/conftest.gmx_skipif` | (local) | `pytest.mark.skipif` when `gmx` absent on PATH | Decorate the test (CI without gmx still runs file-consistency) |
| `unittest.mock.patch` | stdlib | Mock `QFileDialog`/`QMessageBox` for GUI | NOT needed for this CLI test |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New test file | Extend `test_e2e_triclinic_hydrate_export.py` | Rejected: c2te/ice1hte are ORTHORHOMBIC (not triclinic); mixing them into a "triclinic" file is misleading and would require renaming the file. A dedicated `test_e2e_filled_ice_cli_hydrate_grompp.py` is cleaner. |
| Explicit `cage_guest_assignments` | Legacy `guest_type="ch4"` only | Both work (backward-compat shim in `types.py:637-665` auto-synthesizes from `cage_type_map`). The triclinic test uses the legacy form; the GUI test uses explicit. Either is fine — see Code Examples. |

**Installation:**
```bash
# No new dependencies. Everything is already in the quickice conda env.
```

## Architecture Patterns

### Recommended Project Structure
```
tests/
├── test_e2e_triclinic_hydrate_export.py   # c0te/c1te CLI+GUI hydrate grompp (EXISTING — mirror this)
├── test_e2e_mixed_filled_ice_gui.py       # c2te/ice1hte GUI hydrate grompp (EXISTING — borrow fixture pattern)
├── test_e2e_lattice_cross_tab_cli.py      # c2te/ice1hte CLI interface/solute/ion grompp (EXISTING — NOT the gap)
├── test_e2e_filled_ice_cli_hydrate_grompp.py  # NEW: c2te/ice1hte CLI hydrate-ONLY branch grompp (THE GAP)
├── e2e_export_helpers.py                  # Shared helpers (EXISTING — import from here)
└── conftest.py                            # gmx_skipif marker, module-scoped fixtures (EXISTING)
```

### Pattern 1: CLI Hydrate-Branch Export Test (the exact pattern to mirror)
**What:** Drive `CLIPipeline._run_export_step` into its **hydrate** branch by
setting ONLY `_hydrate_result` (NOT `_interface_result` / `_solute_result` /
`_ion_result`). The priority selector
(`pipeline.py:851-862`: ion > solute > custom > interface > **hydrate** > ice)
then picks the hydrate branch, which wraps the `HydrateStructure` in an
`InterfaceStructure`-compatible wrapper and writes `hydrate.gro` / `hydrate.top`
via `write_interface_gro_file` / `write_interface_top_file` +
`copy_itp_files_for_structure`.
**When to use:** Validating the hydrate-only export path (no interface slab) for
a filled-ice lattice — the only export path available for triclinic filled
ices (c0te/c1te, blocked at interface) and a valid direct-export option for
orthorhombic filled ices (c2te/ice1hte).
**Example (EXISTING — `test_e2e_triclinic_hydrate_export.py:174-212`):**
```python
# Source: tests/test_e2e_triclinic_hydrate_export.py (verified, PASSING)
@pytest.mark.parametrize("lattice_type", ["c0te", "c1te"])
@gmx_skipif
def test_triclinic_hydrate_cli_export_grompp(
    tmp_path, triclinic_hydrates, lattice_type
):
    chain = triclinic_hydrates[lattice_type]
    ws = tmp_path / "cli"
    ws.mkdir()
    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = ws
    pipe._hydrate_result = chain.hydrate  # carries .config for ITP staging
    # Only _hydrate_result set -> export priority picks the hydrate branch.
    code = pipe._run_export_step()
    assert code == 0
    _assert_hydrate_export(ws, "hydrate.gro", "hydrate.top")
```

### Pattern 2: Per-Lattice Supercell Fixture (the fixture pattern to mirror)
**What:** Module-scoped fixture builds each lattice's hydrate ONCE with the
empirically-verified minimum supercell that satisfies grompp's PBC rule
(shortest box vector > 2*rcoulomb = 2.0 nm). Amortizes GenIce2 calls across the
parametrized cases per AGENTS.md.
**When to use:** Any filled-ice grompp test — the 1x1x1 unit cells are tiny
(c2te 0.88 nm, ice1hte 0.69 nm) and FAIL grompp.
**Example (EXISTING — `test_e2e_mixed_filled_ice_gui.py:90-160`):**
```python
# Source: tests/test_e2e_mixed_filled_ice_gui.py (verified, PASSING)
_FILLED_ICE_SUPERCELLS = {
    "c2te": (3, 3, 3),      # shortest 2.65 nm -> grompp rc=0 (7776 atoms)
    "ice1hte": (4, 4, 4),   # shortest 2.76 nm -> grompp rc=0 (6656 atoms)
}

@pytest.fixture(scope="module")
def filled_ice_hydrates():
    chains = {}
    for lattice_type in ("c2te", "ice1hte"):
        gen = HydrateStructureGenerator()
        nx, ny, nz = _FILLED_ICE_SUPERCELLS[lattice_type]
        config = HydrateConfig(
            lattice_type=lattice_type,
            guest_type="ch4",  # built-in
            cage_guest_assignments={  # explicit form (legacy guest_type also works)
                "small": CageGuestAssignment(guest_type="ch4", occupancy=100.0),
            },
            supercell_x=nx, supercell_y=ny, supercell_z=nz,
        )
        hydrate = gen.generate(config)
        assert hydrate.guest_count > 0
        chains[lattice_type] = SimpleNamespace(hydrate=hydrate, config=config)
    yield chains
```

### Pattern 3: Hydrate-Export Assertion Block (the assertions to reuse)
**What:** The full assertion sequence for a built-in-ch4 hydrate export: files
written → `ch4_hydrate.itp` staged with `CH4_H` moleculetype → `[molecules]`
has `SOL` + `CH4_H` → `.gro` residues have `SOL` + `CH4_H` →
`assert_itp_completeness` → `assert_gro_top_consistent` → `gmx grompp` rc=0.
**When to use:** Every built-in-ch4 hydrate export grompp test.
**Example (EXISTING — `test_e2e_triclinic_hydrate_export.py:115-168`,
`_assert_hydrate_export`):** See Code Examples section below.

### Anti-Patterns to Avoid
- **Don't set `_interface_result` when testing the hydrate branch:** The
  priority selector (ion > solute > custom > interface > hydrate > ice) would
  pick the interface branch instead. Set ONLY `_hydrate_result`.
- **Don't call `_stage_itp_files` for the CLI hydrate branch:** The CLI path's
  `copy_itp_files_for_structure` (called inside `_run_export_step`) stages ITPs
  itself. Re-staging via `_stage_itp_files` could conflict. Only copy `em.mdp`.
- **Don't use the GUI export path for a CLI test:** GUI uses
  `write_multi_molecule_*` + `MoleculetypeRegistry`; CLI hydrate branch uses
  `write_interface_*` + the `InterfaceStructure` wrapper. Different writers
  (Pitfall 6). Do NOT import `HydrateGROMACSExporter` in the CLI test.
- **Don't use 2x2x2 (or smaller) supercells for c2te/ice1hte:** They FAIL
  grompp (c2te 2x2x2 = 1.76 nm, ice1hte 2x2x2 = 1.38 nm; ice1hte even fails
  3x3x3 = 2.07 nm). Use the empirically-verified minimums (c2te 3x3x3, ice1hte
  4x4x4).
- **Don't assert exact guest/water counts:** Counts vary by lattice/GenIce2
  version (Pitfall 5). Assert `> 0` only in the fixture sanity check.

## Don't Hand-Roll

Problems that look simple but have existing solutions — ALL already in the repo:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Run `gmx grompp` + capture rc/stderr | `subprocess.run` inline | `e2e_export_helpers.run_gmx_grompp(ws, gro_file, top_file)` | Handles stale `.tpr` backup cleanup, `-maxwarn`, 60s timeout, cwd |
| Parse `[ molecules ]` from .top | Regex inline | `e2e_export_helpers.parse_top_molecules(top_path)` | Tracks `[ section ]` state, skips comments |
| Parse .gro residue names | Column slicing inline | `e2e_export_helpers.parse_gro_residue_names(gro_path)` | Correct GRO column offsets [5:10], skips box-vector lines |
| Assert all `#include` ITPs exist | Manual `glob` | `e2e_export_helpers.assert_itp_completeness(top_path, ws)` | Catches the "top references ITP but file missing" bug class |
| Cross-validate GRO/TOP consistency | Manual count diff | `e2e_export_helpers.assert_gro_top_consistent(gro, top)` | Catches header-count mismatch + residue/[molecules] mismatch |
| Skip when `gmx` absent | `pytest.mark.skipif(shutil.which(...))` inline | `from tests.conftest import gmx_skipif` + `@gmx_skipif` | Project-standard marker |
| Energy-minimization MDP path | Hardcode path | `e2e_export_helpers.MDP_PATH` | Points to `tests/em.mdp` |
| Hydrate config with cage guests | Manual cage_type_map lookup | `HydrateConfig(lattice_type=..., guest_type="ch4", ...)` | Backward-compat shim auto-synthesizes `cage_guest_assignments` from `cage_type_map` (`types.py:637-665`) |

**Key insight:** This phase adds ZERO new production code and ZERO new
helpers. Every assertion primitive already exists in `e2e_export_helpers.py`.
The only deliverable is ONE new test file that composes existing helpers +
mirrors an existing passing test for two new lattice parameters.

## Common Pitfalls

### Pitfall 1: Box-Size (CRITICAL — empirically verified)
**What goes wrong:** `gmx grompp` fatal-errors with "cut-off length is longer
than half the shortest box vector" when the shortest box vector < 2*rcoulomb
(2.0 nm from `em.mdp`).
**Why it happens:** Filled-ice unit cells are tiny. c2te 1x1x1 = 0.88 nm;
ice1hte 1x1x1 = 0.69 nm. Even 2x2x2 fails (c2te 1.76 nm, ice1hte 1.38 nm).
ice1hte even fails 3x3x3 (2.07 nm) — GROMACS's check is stricter than the
simple vector-length test for non-orthogonal cells (though ice1hte IS
orthogonal, the 3x3x3 still empirically fails).
**How to avoid:** Use per-lattice supercells from
`_FILLED_ICE_SUPERCELLS`: **c2te = 3x3x3 (2.65 nm)**, **ice1hte = 4x4x4
(2.76 nm)**. Both verified to produce grompp rc=0.
**Warning signs:** `gmx grompp` rc=1 with stderr mentioning "cut-off" or
"shortest box vector".

### Pitfall 2: Cage Key "small" vs "guest"
**What goes wrong:** Setting `cage_guest_assignments={"guest": ...}` produces
0 guests — the hydrate generator's `_run_via_api` (`hydrate_generator.py:294-
297`) skips cage keys not present in `cage_type_map` with the warning "cage_key
'guest' not in cage_type_map".
**Why it happens:** c2te/ice1hte have `cage_type_map = {"small": "Ne1"}` (the
GenIce2 cage ID mapping). The `cages` DISPLAY dict uses the human-readable key
"guest" (the cage NAME), but `cage_type_map` uses "small". These are two
different dicts with different keys — easy to conflate.
**How to avoid:** Either (a) use the legacy `guest_type="ch4"` form WITHOUT
`cage_guest_assignments` (the backward-compat shim auto-synthesizes from
`cage_type_map` keys correctly), OR (b) if passing `cage_guest_assignments`
explicitly, use `"small"` as the key (matching `cage_type_map`), NOT "guest".
**Warning signs:** `hydrate.guest_count == 0` in the fixture sanity check.

### Pitfall 6: Two Export Paths (CLI vs GUI)
**What goes wrong:** A CLI test accidentally imports/exercises the GUI export
path, or vice versa, testing the wrong writers.
**Why it happens:** The CLI hydrate branch (`pipeline.py:886-929`) wraps
`HydrateStructure` in an `InterfaceStructure`-compatible wrapper +
`write_interface_gro_file` / `write_interface_top_file` +
`copy_itp_files_for_structure`. The GUI path
(`hydrate_export.py::HydrateGROMACSExporter.export_hydrate`) uses
`write_multi_molecule_gro_file` / `write_multi_molecule_top_file` +
`MoleculetypeRegistry`. Different writers, different ITP staging.
**How to avoid:** The CLI test must use `CLIPipeline` + `_run_export_step` and
must NOT import `quickice.gui.hydrate_export` (keeps PySide6 out of the import
path per AGENTS.md lazy-import rule). The GUI grompp test for c2te/ice1hte
already exists (`test_filled_ice_single_cage_gui_grompp`); the new CLI test
complements it — do not conflate.
**Warning signs:** Test imports `HydrateGROMACSExporter` or patches
`QFileDialog` (GUI-only) in a CLI test.

### Pitfall (Lazy Imports)
**What goes wrong:** Importing `PySide6`/`VTK`/`GenIce2` at module top level
breaks the CLI test's import path or headless environments.
**Why it happens:** AGENTS.md mandates lazy imports for these heavy/optional
deps. `GenIce2` is imported inside `HydrateStructureGenerator` method bodies
(already handled). `PySide6` is only needed for the GUI exporter (NOT this
test).
**How to avoid:** The new CLI test imports only `pytest`, `shutil`,
`SimpleNamespace`, `CLIPipeline`, `HydrateStructureGenerator`, `HydrateConfig`
(+ optional `CageGuestAssignment`), `gmx_skipif`, and the e2e helpers. No
PySide6/VTK import anywhere. No `QT_QPA_PLATFORM` needed for the CLI test.

### Pitfall 5: Guest/Water Counts Vary
**What goes wrong:** Asserting an exact guest count makes the test brittle
across GenIce2 versions.
**How to avoid:** Assert `hydrate.guest_count > 0` and `hydrate.water_count > 0`
in the fixture sanity check only. Do NOT assert exact counts in the export test.

### Pitfall 4: GRO Atom-Number Wrap (cosmetic)
**What goes wrong:** GRO residue numbers wrap at 100,000 (GRO format limit).
**How to avoid:** `assert_gro_top_consistent` counts atom LINES (not the
header atom-count field), so it is robust to the wrap. Do NOT rely on the
header count. This is cosmetic; grompp still rc=0.

## Code Examples

Verified patterns from the actual passing test files (run during research,
all 11 tests PASS):

### Example 1: The CLI hydrate-branch test to MIRROR (c0te/c1te — the triclinic siblings)
```python
# Source: tests/test_e2e_triclinic_hydrate_export.py:174-212 (VERIFIED PASSING)
@pytest.mark.parametrize("lattice_type", ["c0te", "c1te"])
@gmx_skipif
def test_triclinic_hydrate_cli_export_grompp(
    tmp_path, triclinic_hydrates, lattice_type
):
    chain = triclinic_hydrates[lattice_type]
    ws = tmp_path / "cli"
    ws.mkdir()
    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = ws
    pipe._hydrate_result = chain.hydrate  # carries .config for ITP staging
    code = pipe._run_export_step()
    assert code == 0
    _assert_hydrate_export(ws, "hydrate.gro", "hydrate.top")
```

### Example 2: The assertion helper to REUSE/ADAPT
```python
# Source: tests/test_e2e_triclinic_hydrate_export.py:115-168 (VERIFIED PASSING)
def _assert_hydrate_export(ws, gro_name, top_name):
    gro_path = ws / gro_name
    top_path = ws / top_name
    assert gro_path.exists()
    assert top_path.exists()
    assert (ws / "ch4_hydrate.itp").exists()  # built-in guest ITP staged
    assert "CH4_H" in (ws / "ch4_hydrate.itp").read_text()
    mols = parse_top_molecules(str(top_path))
    assert "CH4_H" in mols and "SOL" in mols
    gro_res = set(parse_gro_residue_names(str(gro_path)))
    assert "CH4_H" in gro_res and "SOL" in gro_res
    shutil.copy(MDP_PATH, ws / "em.mdp")
    assert_itp_completeness(str(top_path), ws)
    assert_gro_top_consistent(str(gro_path), str(top_path))
    if shutil.which("gmx"):
        rc, stderr = run_gmx_grompp(ws, gro_file=gro_name, top_file=top_name)
        assert rc == 0, f"gmx grompp failed:\n{stderr}"
```

### Example 3: The fixture + supercell constants to REUSE (c2te/ice1hte — the GUI siblings)
```python
# Source: tests/test_e2e_mixed_filled_ice_gui.py:90-160 (VERIFIED PASSING)
_FILLED_ICE_SUPERCELLS = {"c2te": (3, 3, 3), "ice1hte": (4, 4, 4)}

@pytest.fixture(scope="module")
def filled_ice_hydrates():
    chains = {}
    for lattice_type in ("c2te", "ice1hte"):
        gen = HydrateStructureGenerator()
        nx, ny, nz = _FILLED_ICE_SUPERCELLS[lattice_type]
        config = HydrateConfig(
            lattice_type=lattice_type,
            guest_type="ch4",
            cage_guest_assignments={
                "small": CageGuestAssignment(guest_type="ch4", occupancy=100.0),
            },
            supercell_x=nx, supercell_y=ny, supercell_z=nz,
        )
        hydrate = gen.generate(config)
        assert hydrate.guest_count > 0
        chains[lattice_type] = SimpleNamespace(hydrate=hydrate, config=config)
    yield chains
```

### Example 4: SIMPLER fixture form (legacy — also works, used by the triclinic test)
```python
# Source: tests/test_e2e_triclinic_hydrate_export.py:88-108 (VERIFIED PASSING)
# The backward-compat shim (types.py:637-665) auto-synthesizes
# cage_guest_assignments from cage_type_map keys, so this is equivalent to
# Example 3 for single-cage lattices like c2te/ice1hte.
config = HydrateConfig(
    lattice_type=lattice_type,       # "c2te" or "ice1hte"
    guest_type="ch4",                # built-in; no cage_guest_assignments needed
    supercell_x=nx, supercell_y=ny, supercell_z=nz,
)
hydrate = gen.generate(config)
```

### Example 5: The `_run_export_step` hydrate branch under test (pipeline.py:886-929)
```python
# Source: quickice/cli/pipeline.py:886-929 (the code path the new test exercises)
elif step_name == "hydrate":
    # HydrateStructure -> InterfaceStructure-compatible wrapper
    hydrate = structure
    water_atom_count = hydrate.water_count * WATER_ATOMS_PER_MOLECULE
    guest_atom_count = len(hydrate.positions) - water_atom_count
    assert water_atom_count + guest_atom_count == len(hydrate.positions)
    wrapper = InterfaceStructure(
        positions=hydrate.positions, atom_names=hydrate.atom_names,
        cell=hydrate.cell, molecule_index=hydrate.molecule_index,
        mode="hydrate", water_atom_count=water_atom_count,
        water_nmolecules=hydrate.water_count,
        guest_atom_count=guest_atom_count, guest_nmolecules=hydrate.guest_count,
        # ... ice_atom_count=0, ice_nmolecules=0
    )
    custom_guest_info = _build_custom_guest_info(getattr(hydrate, "config", None))
    write_interface_gro_file(wrapper, gro_path, custom_guest_info=custom_guest_info)
    write_interface_top_file(wrapper, top_path, custom_guest_info=custom_guest_info)
# ... then copy_itp_files_for_structure(...) stages ch4_hydrate.itp + tip4p-ice.itp
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Roadmap 47-05 text: "filled-ice grompp not explicitly tested" | Phase 45 added c0te/c1te (CLI+GUI) + c2te/ice1hte (GUI) + c2te/ice1hte (CLI interface/solute/ion) grompp tests | Phase 45 (2026-07) | Only the CLI hydrate-ONLY branch for c2te/ice1hte remains untested |
| Orchestrator pre-discovery: "no CLI grompp test for c2te/ice1hte" | `test_lattice_cross_tab_cli_grompp[c2te/ice1hte]` EXISTS and PASSES (interface/solute/ion branches) | Verified 2026-07-12 | Gap narrows to the hydrate-only branch |

**Deprecated/outdated:**
- The roadmap 47-05 plan text ("filled-ice c0te/c1te/c2te/ice1hte grompp not
  explicitly tested") is **stale** — 3 of the 4 lattices (c0te, c1te, and
  c2te/ice1hte-via-interface-branch) already have CLI grompp coverage, and
  c2te/ice1hte have GUI grompp coverage. Only c2te/ice1hte via the CLI
  hydrate-only branch remains.

## Open Questions

1. **Is the hydrate-only CLI branch for c2te/ice1hte a meaningfully DISTINCT path from what's already tested?**
   - What we know: The hydrate branch (`pipeline.py:886-929`) wraps
     `HydrateStructure` in an `InterfaceStructure` wrapper and exports the
     lattice's NATIVE cell (c2te 3x3x3 orthorhombic 2.65 nm, ice1hte 4x4x4
     orthorhombic 2.76 nm). The already-passing `test_lattice_cross_tab_cli_grompp`
     exports via the INTERFACE branch using a 3x3x8 nm SLAB (assemble_slab) —
     a different cell geometry.
   - What's unclear: Whether the wrapper code path (lattice-agnostic) adds
     coverage beyond c0te/c1te. The wrapper IS lattice-agnostic, but the
     grompp PBC check is geometry-sensitive, so the native orthorhombic cell
     is a distinct validation target.
   - Recommendation: Close the gap — it's small (one parametrized test, 2
     cases), satisfies TEST-08 literally ("new lattice type exports"), and
     validates the direct hydrate→export user workflow for c2te/ice1hte
     (which is a legitimate path since c2te/ice1hte are NOT blocked at the
     interface tab, unlike c0te/c1te).

2. **Legacy `guest_type="ch4"` vs explicit `cage_guest_assignments` for the new test?**
   - What we know: Both forms work for c2te/ice1hte. The triclinic CLI test
     (c0te/c1te) uses the legacy form; the GUI test (c2te/ice1hte) uses the
     explicit form. The backward-compat shim (`types.py:637-665`) makes them
     equivalent for single-cage lattices.
   - Recommendation: Use the explicit `cage_guest_assignments={"small": ...}`
     form (matching the GUI test for c2te/ice1hte) since it's the
     empirically-verified form for THESE specific lattices and documents the
     cage-key pitfall inline. The legacy form is a acceptable simpler
     alternative if the planner prefers minimalism.

3. **Should the new test live in a new file or extend an existing one?**
   - Recommendation: New file
     `tests/test_e2e_filled_ice_cli_hydrate_grompp.py`. Extending
     `test_e2e_triclinic_hydrate_export.py` would mislabel orthorhombic
     c2te/ice1hte as "triclinic" and require renaming. Extending
     `test_e2e_mixed_filled_ice_gui.py` would mix CLI + GUI in a GUI file.
     A dedicated file is the cleanest mirror of the existing structure.

## Sources

### Primary (HIGH confidence)
- `tests/test_e2e_triclinic_hydrate_export.py` — read in full (257 lines); the
  CLI hydrate-branch grompp test pattern to mirror (lines 174-212) + the
  `_assert_hydrate_export` helper (lines 115-168). VERIFIED PASSING.
- `tests/test_e2e_mixed_filled_ice_gui.py` — read in full (317 lines); the
  per-lattice supercell constants `_FILLED_ICE_SUPERCELLS` (lines 90-93) +
  the `filled_ice_hydrates` fixture pattern (lines 101-160) + the
  `cage_guest_assignments={"small":...}` form. VERIFIED PASSING.
- `tests/test_e2e_lattice_cross_tab_cli.py` — read key sections (1-120,
  250-417); CONFIRMS c2te/ice1hte CLI grompp IS tested (interface/solute/ion
  branches via `test_lattice_cross_tab_cli_grompp`, lines 353-417), refuting
  the orchestrator's claim. VERIFIED PASSING.
- `tests/e2e_export_helpers.py` — read in full (635 lines); all helpers
  (`run_gmx_grompp`, `parse_top_molecules`, `parse_gro_residue_names`,
  `assert_itp_completeness`, `assert_gro_top_consistent`, `MDP_PATH`).
- `quickice/cli/pipeline.py` — read `_run_export_step` (lines 821-957);
  priority selector (851-862) + hydrate branch wrapper (886-929).
- `quickice/structure_generation/types.py` — `HYDRATE_LATTICES` (c2te/ice1hte
  have `cage_type_map={"small":"Ne1"}`) + backward-compat shim (lines 637-665).
- `tests/conftest.py` — `gmx_skipif` marker definition (lines 24-27).
- Test run: `pytest tests/test_e2e_triclinic_hydrate_export.py
  tests/test_e2e_mixed_filled_ice_gui.py tests/test_e2e_lattice_cross_tab_cli.py
  -v --timeout=300` → **11 passed in 4.98s** (run during research, 2026-07-12).
- `HYDRATE_LATTICES` introspection (run during research): confirmed all 10
  entries; c2te/ice1hte both have `cage_type_map={'small': 'Ne1'}`,
  `cages_keys=['guest']`, NOT triclinic (orthorhombic).

### Secondary (MEDIUM confidence)
- Box-vector measurements (c2te 3x3x3 = 2.65 nm, ice1hte 4x4x4 = 2.76 nm)
  are sourced from the empirically-verified comments in
  `test_e2e_mixed_filled_ice_gui.py:85-93` and the test's passing status
  confirms grompp rc=0 at these sizes.

### Tertiary (LOW confidence)
- None. All findings are backed by reading the actual test files + running
  the tests + reading the production code under test.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools already in the project; verified by running tests.
- Architecture (test pattern): HIGH — exact pattern to mirror is a verified
  passing test (`test_triclinic_hydrate_cli_export_grompp`); the gap is a
  direct parametrization of an existing pattern for 2 new lattice values.
- Pitfalls: HIGH — all pitfalls are documented in the existing test file
  headers AND verified by the tests passing (box-size, cage key, two paths).
- Gap analysis: HIGH — verified by reading all 3 relevant test files + grep
  for `grompp`/`gmx_skipif`/`run_gmx` + running the 11 tests (all pass).

**Important correction for the planner:** The orchestrator's pre-discovery
Finding 1 contained a factual error (claimed
`test_e2e_lattice_cross_tab_cli.py` lacks grompp; it does NOT — it has
`test_lattice_cross_tab_cli_grompp` which PASSES for c2te/ice1hte via the
interface/solute/ion branches). The true gap is ONLY the CLI **hydrate-only**
branch for c2te/ice1hte. The plan should target that single, narrow gap — do
NOT write tests that duplicate the existing interface/solute/ion coverage.

**Research date:** 2026-07-12
**Valid until:** 2026-08-11 (stable — production code under test is not
expected to change; the test pattern is established and passing)
