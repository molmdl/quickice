# Phase 45: E2E Hydrate Tab Workflow - Research

**Researched:** 2026-07-10
**Domain:** E2E test coverage for GUI/CLI tab workflows with new hydrate lattice types + custom hydrate guests
**Confidence:** HIGH (empirically verified by running GenIce2 + grompp directly in the `quickice` conda env; `gmx` IS on PATH at `/data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx`)

## Summary

The user REDEFINED Phase 45 from "CLI Integration" to **"make sure all the tabs can work e2e with the new hydrate and custom hydrate."** This is a comprehensive E2E verification phase: prove that ALL GUI tabs (Ice → Hydrate → Interface → Custom → Solute → Ion → Export) and the CLI pipeline work correctly with (a) the 7 new lattice types from Phase 39 (c0te, c1te, c2te, ice1hte, sTprime, 16, 17) and (b) custom hydrate guests (Phase 40 GenIce2 bridge).

I empirically verified the full lattice type matrix by running each lattice through `HydrateStructureGenerator.generate → to_candidate → generate_interface → write_interface_gro/top_file → copy_itp_files_for_structure → gmx grompp`. **8 of 10 lattice types pass grompp at the interface export step today** (verified rc=0). Only the 2 triclinic filled ices (c0te, c1te) are BLOCKED at the interface tab by design (`TRICLINIC_HYDRATE_PHASES = {"hydrate_c0te", "hydrate_c1te"}` in `interface_builder.py:121`), and their hydrate-only export needs a **4×4×4 supercell minimum** to pass grompp (the 1×1×1 unit cell is smaller than 2×rcoulomb=2.0 nm — grompp fatal-errors with "cut-off length longer than half the shortest box vector").

The gaps are **test-coverage gaps, not functional bugs**: the engine works, but no test proves it works for the new lattices through the full tab chain. ALL existing cross-tab e2e tests use **sI only** (`test_e2e_builtin_cross_tab_regression.py`, `test_e2e_custom_guest_cross_tab_gui.py`, `test_e2e_custom_guest_cross_tab_cli.py`). The 157-test `test_hydrate_lattice_types.py` only tests the data model + config + `HydrateLatticeInfo` — it does NOT exercise the tab chain. `test_triclinic_blocking.py` only calls `validate_interface_config` directly — it does NOT prove the CLI `_run_interface_step` or the GUI interface worker block triclinic end-to-end.

**Primary recommendation:** Write parametrized cross-tab e2e tests (one parametrized test per lattice, module-scoped fixtures amortizing GenIce2 ~1-5s calls) covering: (1) new lattices through the full GUI+CLI export chain with grompp, (2) triclinic blocking e2e through CLI `_run_interface_step` + GUI worker, (3) triclinic filled-ice hydrate-only export at 4×4×4 supercell, (4) custom guest with non-sI lattices, (5) the missing `--depol` CLI flag. Reuse the existing `e2e_export_helpers.py` infrastructure + module-scoped fixture pattern. SMALL plans, 20+ acceptable per user.

## Standard Stack

The established libraries/tools for this domain (all already in the `quickice` conda env — NO new dependencies):

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| GenIce2 | 2.2.13.1 | Hydrate lattice generation (10 lattice types) | Sole hydrate generator; lazy-imported in `hydrate_generator.py` |
| pytest | (env) | Test runner with parametrize + module-scoped fixtures | Repo standard (~1007 tests, no pytest.ini) |
| GROMACS `gmx` | 2023.5-plumed_2.9.3 | `gmx grompp` topology validation | On PATH; the ultimate "does it work" gate for export |
| PySide6 | 6.10.2 | GUI exporters (4: Interface/Solute/CustomMolecule/Ion) | `QT_QPA_PLATFORM=offscreen` for headless tests |

### Supporting (test infrastructure, all already in `tests/e2e_export_helpers.py`)
| Helper | Purpose | When to Use |
|---------|---------|------------|
| `parse_gro_residue_names` | Read .gro residue names | Assert residues match [molecules] |
| `parse_top_molecules` | Parse [molecules] dict | Assert expected molecule entries |
| `parse_top_includes` | List #include'd ITPs | Assert ITP referenced + present |
| `assert_itp_completeness` | Every #include'd ITP exists in ws | Catches "top references ITP but file missing" |
| `assert_gro_top_consistent` | .gro header + residues ↔ .top [molecules] | Catches _H suffix + missing-molecule bugs |
| `run_gmx_grompp` | Run gmx grompp, return (rc, stderr) | The sim-ready gate (rc==0) |
| `_insert_solutes` / `_insert_ions` / `_insert_ions_from_solute` | Build downstream structures | Chain interface→solute→ion |
| `_stage_itp_files` / `_stage_custom_guest_itp` | Stage ITPs for grompp | When calling writers directly |
| `ETOH_GRO` / `ETOH_ITP` / `MDP_PATH` | Test fixtures (ethanol guest, em.mdp) | Custom guest tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `gmx grompp` | Pure file-consistency asserts only | grompp is the authoritative gate — file-consistency catches less. Keep BOTH (file-consistency always runs; grompp `@gmx_skipif` when gmx absent) |
| Module-scoped fixtures | Function-scoped | Module-scoped amortizes GenIce2 (~1-5s each) — REQUIRED per AGENTS.md testing guidance |

**Installation:** None needed. All deps in `environment.yml`. `gmx` is external (on PATH).

## Architecture Patterns

### Recommended Test File Structure
```
tests/
├── test_e2e_lattice_cross_tab_gui.py      # NEW: 7 new lattices through 4 GUI exporters + grompp
├── test_e2e_lattice_cross_tab_cli.py      # NEW: 7 new lattices through CLI export branches + grompp
├── test_e2e_triclinic_blocking_e2e.py     # NEW: c0te/c1te blocked via CLI _run_interface_step + GUI worker
├── test_e2e_triclinic_hydrate_export.py   # NEW: c0te/c1te hydrate-only export @ 4x4x4 + grompp (CLI+GUI)
├── test_e2e_custom_guest_lattices.py      # NEW: custom ethanol guest with sII/c2te/ice1hte/16
├── test_cli/test_depol_flag.py            # NEW: --depol CLI flag (45-02a)
└── (existing files unchanged)
```

### Pattern 1: Module-Scoped Parametrized Cross-Tab Fixture (THE template)
**What:** Build the full chain (hydrate → interface → solute/custom/ion) ONCE per lattice, amortize GenIce2 across all parametrized export cases.
**When to use:** Every cross-tab e2e test (this is the established repo pattern from `test_e2e_builtin_cross_tab_regression.py` + `test_e2e_custom_guest_cross_tab_gui.py`).
**Example:**
```python
# Source: tests/test_e2e_builtin_cross_tab_regression.py (the proven template)
@pytest.fixture(scope="module")
def lattice_chains(request):
    """Build chains for ALL parametrized lattices ONCE."""
    chains = {}
    for lattice_type in ("sII", "sH", "c2te", "ice1hte", "sTprime", "16", "17"):
        gen = HydrateStructureGenerator()
        config = HydrateConfig(lattice_type=lattice_type, guest_type="ch4",
                               supercell_x=1, supercell_y=1, supercell_z=1)
        hydrate = gen.generate(config)
        candidate = hydrate.to_candidate()
        iface = assemble_slab(candidate, InterfaceConfig(
            mode="slab", box_x=3.0, box_y=3.0, box_z=8.0,
            seed=42, ice_thickness=2.0, water_thickness=4.0))
        solute = _insert_solutes(iface, solute_type="CH4", concentration=0.3)
        ion = _insert_ions(iface, concentration=0.15)
        chains[lattice_type] = SimpleNamespace(hydrate=hydrate, iface=iface,
                                                solute=solute, ion=ion)
    yield chains

@pytest.mark.parametrize("lattice_type", ["sII","sH","c2te","ice1hte","sTprime","16","17"])
def test_lattice_interface_export_grompp(tmp_path, lattice_chains, lattice_type):
    chain = lattice_chains[lattice_type]
    # ... export + assert_itp_completeness + assert_gro_top_consistent + run_gmx_grompp
```

### Pattern 2: Fresh Interface Per Inserter (Ion Mutation Isolation)
**What:** The ion inserter mutates `iface.molecule_index` (`ion_inserter.py:259`). Give each inserter its OWN fresh `assemble_slab` (deterministic with `seed=42`) so the solute exporter's `interface_structure.molecule_index` reference isn't cross-contaminated.
**When to use:** When a single fixture drives multiple inserters (solute + custom + ion) that all read the interface.
**Example:**
```python
# Source: tests/test_e2e_custom_guest_cross_tab_gui.py lines 120-139
iface = _make_iface()          # interface exporter
iface_solute = _make_iface()   # solute inserter (own copy)
iface_custom = _make_iface()   # custom inserter (own copy)
iface_ion = _make_iface()       # ion inserter (own copy — gets mutated)
```

### Pattern 3: GUI Exporter Test with QFileDialog Mocking
**What:** Under `QT_QPA_PLATFORM=offscreen`, `QFileDialog.getSaveFileName` returns `("", "")` → exporter returns False without writing. MUST inline-patch `QFileDialog.getSaveFileName` + `QMessageBox`.
**When to use:** ALL GUI exporter tests.
**Example:**
```python
# Source: tests/test_e2e_builtin_cross_tab_regression.py lines 292-301
with patch("quickice.gui.export.QFileDialog.getSaveFileName",
           return_value=(str(gro_path), "GRO Files (*.gro)")), \
     patch("quickice.gui.export.QMessageBox"):
    exporter = InterfaceGROMACSExporter(parent_widget=None)
    ok = exporter.export_interface_gromacs(chain.iface, hydrate_config=config)
    assert ok is True
```

### Pattern 4: CLI Export-Step-Direct (no full pipeline run)
**What:** Construct `CLIPipeline(args=SimpleNamespace())`, set `_hydrate_result` + one `_<downstream>_result`, call `_run_export_step()` directly. Avoids running the full CLI arg parse + source/interface steps.
**When to use:** CLI export branch tests.
**Example:**
```python
# Source: tests/test_e2e_custom_guest_cross_tab_cli.py lines 155-166
pipe = CLIPipeline(args=SimpleNamespace())
pipe._output_dir = ws
pipe._hydrate_result = hydrate          # carries .config for cgi threading
setattr(pipe, downstream_attr, struct) # e.g. "_interface_result"
code = pipe._run_export_step()
assert code == 0
```

### Anti-Patterns to Avoid
- **Function-scoped GenIce2 fixtures:** Wastes ~1-5s × N parametrized cases. Use module-scoped (AGENTS.md).
- **Asserting strict != optimal depol:** In GenIce2 2.2.13.1 both modes set `dipoleOptimizationCycles=1000` → IDENTICAL output. Asserting a difference is a false-future-proofing bug (Pitfall 1, see `test_hydrate_lattice_types.py:394-405`).
- **1×1×1 supercell for triclinic filled ice grompp:** c0te/c1te 1×1×1 unit cell (shortest vector ~0.54-0.61 nm) is SMALLER than 2×rcoulomb=2.0 nm → grompp fatal-errors. MUST use 4×4×4 minimum.
- **Mixing the two hydrate export paths:** CLI `_run_export_step` hydrate branch wraps in `InterfaceStructure` + `write_interface_*` (pipeline.py:906-928); GUI `HydrateGROMACSExporter.export_hydrate` uses `write_multi_molecule_*` (hydrate_export.py). These are DIFFERENT code paths — test BOTH separately.
- **Reusing a mutated interface across inserters:** Ion inserter mutates `iface.molecule_index`. Use fresh `assemble_slab` per inserter.

## Don't Hand-Roll

Problems that look simple but have existing solutions — REUSE these:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GRO/TOP parsing + consistency | Manual line parsing | `e2e_export_helpers.{parse_gro_residue_names, parse_top_molecules, parse_top_includes, assert_gro_top_consistent, assert_itp_completeness}` | Battle-tested; catches _H suffix + missing-molecule bugs |
| Running grompp | Manual subprocess | `e2e_export_helpers.run_gmx_grompp` | Handles stale .tpr cleanup, maxwarn, timeout, cwd |
| Building downstream structures | Manual inserter calls | `e2e_export_helpers.{_insert_solutes, _insert_ions, _insert_ions_from_solute, _solute_to_ion_source}` | Encodes the auto-chain + duck-typing propagation |
| Building slab interface | Manual assemble_slab | `e2e_export_helpers._make_slab_interface` | Correct box dims for grompp PBC rule |
| Staging custom guest ITP | Manual copy+transform | `e2e_export_helpers._stage_custom_guest_itp` | Applies `transform_guest_itp(content, resname, "_H")` — required for grompp |
| CLI export branch testing | Full `CLIPipeline.execute()` | `_make_cli_pipeline` + `_run_export_step()` direct | Avoids arg-parse + source step; isolates export |
| Building custom guest metadata | Manual CageGuestAssignment | `HydrateConfig(guest_type=..., guest_residue_name=..., guest_gro_path=..., guest_itp_path=..., guest_atom_labels=..., guest_atom_count=...)` | `__post_init__` auto-populates built-in metadata (42-01 single source of truth) |
| Threading custom guest to writers | Manual dict | `_build_custom_guest_info(hydrate_config)` from `quickice.output.guest_info` | Dedups by mol_type; None for built-in, list for custom |
| Copying ITPs for export | Manual shutil.copy | `quickice.cli.itp_helpers.copy_itp_files_for_structure` | Handles built-in + custom guest ITP staging (transforms custom) |
| `gmx_skipif` marker | Manual skipif | `from tests.conftest import gmx_skipif` | Skips when gmx not on PATH; file-consistency still runs |

**Key insight:** The repo has a mature e2e test infrastructure in `tests/e2e_export_helpers.py` (635 lines) + the `test_e2e_builtin_cross_tab_regression.py` / `test_e2e_custom_guest_cross_tab_*.py` templates. New tests should MIRROR these templates, swapping sI → parametrized lattices. Do NOT invent new helpers.

## Common Pitfalls

### Pitfall 1: Triclinic Filled-Ice grompp Box-Size (CRITICAL — empirically verified)
**What goes wrong:** c0te/c1te at 1×1×1 supercell → `gmx grompp` fails rc=1: "The cut-off length is longer than half the shortest box vector... Increase the box size or decrease rlist."
**Why it happens:** c0te unit cell: `|a|=0.6177, |b|=0.6177, |c|=0.6054` nm. c1te: `|a|=1.2673, |b|=1.2673, |c|=0.6017` nm. The shortest vector (~0.54-0.61 nm) is < 2×rcoulomb (1.0 nm) = 2.0 nm. `em.mdp` has `rcoulomb=rvdw=1.0`.
**How to avoid:** Use **4×4×4 supercell** for c0te AND c1te hydrate-only export tests (4 × 0.5349 = 2.14 nm > 2.0 ✓; verified rc=0). Do NOT use 1×1×1, 2×2×2, or 3×3×3 — all fail the box-size rule.
**Warning signs:** grompp stderr contains "cut-off length is longer than half the shortest box vector".

### Pitfall 2: CLI Export is Single-Guest-Stream (Mixed Built-In Limitation)
**What goes wrong:** CLI `write_interface_gro/top_file` uses `detect_guest_type_from_atoms` to pick ONE guest type for the whole guest region. Mixed BUILT-IN occupancy (CH4 in small + THF in large) through the CLI interface/solute/ion export may emit only ONE guest type's residues/ITP.
**Why it happens:** Per `test_cli/test_mixed_cage_cli.py` docstring (lines 27-38): "those writers carry a single guest stream... they cannot emit a mixed [molecules] block with both CH4_H and THF_H. The multi-molecule writers (GUI HydrateGROMACSExporter) DO handle mixed."
**How to avoid:** Mixed CUSTOM guests (same mol_type, deduped by `_build_custom_guest_info`) work through CLI (see `test_e2e_same_custom_two_cages.py`). Mixed BUILT-IN (ch4+thf) through CLI interface export is a known limitation — test mixed built-in via the GUI hydrate exporter (`write_multi_molecule_*`) OR document as out-of-scope for CLI.
**Warning signs:** CLI mixed built-in export produces only `CH4_H` OR only `THF_H` (not both).

### Pitfall 3: Water-Only Lattices + Downstream Inserters (Risk — verify)
**What goes wrong:** sTprime/17 have `guest_nmolecules=0`, `guest_atom_count=0`. Downstream inserters (solute, ion) or exporters may IndexError or emit empty ITP includes.
**Why it happens:** `guest_info.py:250` gates: `if guest_atom_count <= 0 or guest_nmolecules <= 0: return None, {}` — correctly skips guest ITP staging. But the writers' `[molecules]` + `#include` logic for the no-guest path is less exercised.
**How to avoid:** Empirically verified: sTprime + 17 interface export → grompp rc=0, mols={'SOL': N} (no guest ITP, no guest residues). BUT the full chain (solute/ion) with water-only is UNTESTED. New tests MUST verify solute/ion inserters don't crash on `guest_nmolecules=0`.
**Warning signs:** IndexError, KeyError, or empty `#include ""` in .top for water-only lattices.

### Pitfall 4: GRO Atom-Number Wrap at 100,000 (Cosmetic)
**What goes wrong:** Large lattices (c2te 4×4×4 = 220736 atoms; sH interface = 49584+ waters + 4480 guests) trigger `gromacs_writer` warning: "GRO format wraps atom numbers at 100,000 (have N atoms)".
**Why it happens:** GRO format reserves 5 digits for atom numbers. Standard GROMACS limitation.
**How to avoid:** grompp STILL ACCEPTS wrapped atom numbers (verified rc=0 for c2te). Tests must NOT assert atom-number exactness in the .gro header for large systems. Use `assert_gro_top_consistent` (counts atom LINES, not header) — it's robust to this.
**Warning signs:** A warning log line (not an error); grompp still succeeds.

### Pitfall 5: sH Huge Guest Count (sH medium cages routed)
**What goes wrong:** sH 1×1×1 through interface produces 4480 guests (vs 8 at generation) — surprisingly large.
**Why it happens:** sH unit cell is small; the 3×3×8 nm slab tiles it many times. sH has 3 cage types (small+medium+large); all routed. This is EXPECTED, not a bug.
**How to avoid:** Don't assert exact guest counts for sH through interface (version-dependent). Assert `guest_nmolecules > 0` and grompp rc=0. Tests with sH will be SLOWER (~5-10s for GenIce2 + tiling).
**Warning signs:** Test timeout — give sH cases a generous timeout (≥120s).

### Pitfall 6: Two Different Hydrate Export Paths (Don't conflate)
**What goes wrong:** Tests assume CLI and GUI hydrate export use the same writers — they DON'T.
**Why it happens:** CLI `_run_export_step` hydrate branch (pipeline.py:885-928) wraps HydrateStructure in InterfaceStructure + `write_interface_gro/top_file` + `copy_itp_files_for_structure`. GUI `HydrateGROMACSExporter.export_hydrate` (hydrate_export.py) uses `write_multi_molecule_gro/top_file` + MoleculetypeRegistry.
**How to avoid:** Test the CLI hydrate export via `_run_export_step` (Pattern 4). Test the GUI hydrate export via `HydrateGROMACSExporter.export_hydrate` with QFileDialog mock (Pattern 3). These are SEPARATE test cases.
**Warning signs:** A test that mocks one path but asserts behavior of the other.

### Pitfall 7: Pitfall-6-from-44.1 (Same Custom Guest in 2 Cages — already relaxed)
**What goes wrong:** (Pre-44.1) Assigning the same custom guest to 2 cages raised ValueError from `HydrateConfig.__post_init__`.
**Why it happens:** Over-restriction, relaxed in 44.1-01 (now rejects ONLY different guest_types sharing a residue name).
**How to avoid:** Already fixed + covered by `test_e2e_same_custom_two_cages.py` (sI). When testing custom guest with sII/16 (2 cage types), the same custom guest in both cages is now VALID. Don't assert it raises.
**Warning signs:** A new test asserting ValueError for same-custom-two-cages — that's the OLD behavior.

## Code Examples

Verified patterns from the repo (use as copy-paste templates):

### New lattice through Interface export + grompp (empirically verified rc=0)
```python
# Source: empirically verified 2026-07-10 in quickice env (this research)
from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.types import HydrateConfig, InterfaceConfig
from quickice.output.gromacs_writer import write_interface_gro_file, write_interface_top_file
from quickice.output.guest_info import _build_custom_guest_info
from quickice.cli.itp_helpers import copy_itp_files_for_structure
from e2e_export_helpers import MDP_PATH, run_gmx_grompp, assert_itp_completeness, assert_gro_top_consistent

gen = HydrateStructureGenerator()
config = HydrateConfig(lattice_type="c2te", guest_type="ch4", supercell_x=1, supercell_y=1, supercell_z=1)
hydrate = gen.generate(config)
candidate = hydrate.to_candidate()
iface = generate_interface(candidate, InterfaceConfig(
    mode="slab", box_x=3.0, box_y=3.0, box_z=8.0, seed=42,
    ice_thickness=2.0, water_thickness=4.0))
cgi = _build_custom_guest_info(config)  # None for built-in ch4
write_interface_gro_file(iface, str(gro), custom_guest_info=cgi)
write_interface_top_file(iface, str(top), custom_guest_info=cgi)
copy_itp_files_for_structure(ws, iface, "interface", hydrate_config=config)
shutil.copy(MDP_PATH, ws / "em.mdp")
assert_itp_completeness(str(top), ws)
assert_gro_top_consistent(str(gro), str(top))
rc, stderr = run_gmx_grompp(ws, gro_file="interface.gro", top_file="interface.top")
assert rc == 0  # verified rc=0 for c2te, ice1hte, sTprime, 16, 17, sH, sII
```

### Triclinic blocking assertion (CLI _run_interface_step)
```python
# Source: empirically verified — c0te raises InterfaceGenerationError in validate_interface_config
# called by generate_interface, called by CLI _run_interface_step (pipeline.py:432)
from quickice.structure_generation.errors import InterfaceGenerationError
# CLI path: _run_interface_step catches InterfaceGenerationError -> returns 1
# (pipeline.py:441-444) — assert the CLI returns non-zero
code = pipe._run_interface_step()
assert code != 0  # triclinic blocked
```

### Triclinic filled-ice hydrate-only export @ 4x4x4 (verified rc=0)
```python
# Source: empirically verified 2026-07-10 — c0te 4x4x4 rc=0, mols={'SOL': 384, 'CH4_H': 192}
config = HydrateConfig(lattice_type="c0te", guest_type="ch4",
                       supercell_x=4, supercell_y=4, supercell_z=4)  # CRITICAL: 4x4x4 not 1x1x1
hydrate = gen.generate(config)
# CLI hydrate branch wraps in InterfaceStructure (pipeline.py:906-919)
water_atom_count = hydrate.water_count * WATER_ATOMS_PER_MOLECULE
guest_atom_count = len(hydrate.positions) - water_atom_count
wrapper = InterfaceStructure(
    positions=hydrate.positions, atom_names=hydrate.atom_names, cell=hydrate.cell,
    molecule_index=hydrate.molecule_index, mode="hydrate", report="",
    ice_atom_count=0, water_atom_count=water_atom_count,
    ice_nmolecules=0, water_nmolecules=hydrate.water_count,
    guest_atom_count=guest_atom_count, guest_nmolecules=hydrate.guest_count)
cgi = _build_custom_guest_info(config)
write_interface_gro_file(wrapper, str(gro), custom_guest_info=cgi)
write_interface_top_file(wrapper, str(top), custom_guest_info=cgi)
copy_itp_files_for_structure(ws, wrapper, "hydrate", hydrate_config=config)
# grompp rc=0 at 4x4x4 (shortest vector 2.14 nm > 2.0)
```

### Custom guest with non-sI lattice (generation verified OK for sII/c2te/ice1hte/16)
```python
# Source: empirically verified 2026-07-10 — all 4 lattices generate OK with custom ethanol
from quickice.structure_generation.types import HydrateConfig
config = HydrateConfig(
    lattice_type="sII",  # or "c2te", "ice1hte", "16"
    guest_type="etoh_e2e", guest_residue_name="MOL",
    guest_gro_path=str(ETOH_GRO), guest_itp_path=str(ETOH_ITP),
    guest_atom_labels=["H","C","H","H","C","H","H","O","H"], guest_atom_count=9,
    supercell_x=1, supercell_y=1, supercell_z=1)
hydrate = gen.generate(config)  # OK: guest_count=24 (sII), 32 (c2te), 8 (ice1hte), 24 (16)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| sI-only cross-tab e2e tests | Need: ALL 10 lattices through tabs | Phase 45 (this phase) | Closes the new-lattice coverage gap |
| CLI `--cage-guest` built-in-only | (unchanged — custom-guest CLI deferred) | pipeline.py:73-81 (Phase 42) | CLI cannot place custom cage guests; GUI-only by design |
| No `--depol` CLI flag | Need: add `--depol strict/optimal` | Phase 45-02a | GUI has depol combo; CLI missing |
| `validate_interface_config` direct test | Need: e2e blocking through CLI+GUI pipeline | Phase 45 | Proves blocking works in real pipeline |
| c0te/c1te 1×1×1 grompp (fails) | Need: 4×4×4 supercell for triclinic filled ice | Phase 45 (this research) | Tests must use large supercell |

**Deprecated/outdated:**
- `--guest` / `--cage-occupancy-small` / `--cage-occupancy-large` CLI flags: deprecated; use `--cage-guest` for mixed occupancy (parser.py:219, 249, 257). Still work (legacy shim in `HydrateConfig.__post_init__`).
- `detect_guest_type_from_atoms` single-stream heuristic: works for single-guest; CANNOT handle mixed built-in (use multi-molecule writers for mixed).

## Current State — E2E Coverage Today

### Existing e2e tests (what's covered):
| Test File | Scope | Lattices | Tabs | grompp |
|-----------|-------|----------|------|--------|
| `test_e2e_builtin_cross_tab_regression.py` | built-in ch4+thf | **sI only** | ALL 4 GUI + 4 CLI branches | ✓ (PASSES, 4 tests 12.88s) |
| `test_e2e_custom_guest_cross_tab_gui.py` | custom ethanol guest | **sI only** | ALL 4 GUI exporters | ✓ |
| `test_e2e_custom_guest_cross_tab_cli.py` | custom ethanol guest | **sI only** | CLI interface/solute/ion | ✓ |
| `test_e2e_custom_guest_hydrate.py` | custom guest generation | sI | gen only | — |
| `test_e2e_custom_guest_gui_grompp.py` | GUI per-exporter | sI | 4 GUI exporters | ✓ |
| `test_e2e_custom_guest_cli_grompp.py` | CLI per-branch | sI | 4 CLI branches | ✓ |
| `test_e2e_same_custom_two_cages.py` | same custom 2 cages | sI | interface export | ✓ |
| `test_e2e_mixed_cage_occupancy.py` | mixed CH4+etoh_mix | sI 2×2×2 | gen only | — |
| `test_e2e_sh_cage_occupancy.py` | sH cage occupancy | sH | gen only | — |
| `test_hydrate_lattice_types.py` | 157 structural tests | ALL 10 | data model only | — |
| `test_triclinic_blocking.py` | triclinic block | c0te/c1te | `validate_interface_config` direct | — |
| `test_hydrate_panel.py` | GUI panel rows | ALL 10 | panel rendering only | — |
| `test_cli/test_mixed_cage_cli.py` | CLI mixed built-in | sI | multi-molecule writers | ✓ |
| `test_cli/test_pipeline_custom_guest_export.py` | CLI custom export | sI | `_run_export_step` | — |

**Key observation:** EVERY cross-tab e2e test uses **sI only**. The 157 lattice tests only exercise the data model, NOT the tab chain.

## Lattice Type Matrix (empirically verified 2026-07-10)

| Lattice | is_triclinic | is_water_only | Gen | Interface Tab | Interface grompp | Full Tab Chain e2e | Custom Guest | Notes |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|-------|
| sI | F | F | ✓ | ✓ | ✓ (COVERED) | ✓ (COVERED) | ✓ (COVERED) | Baseline — fully covered |
| sII | F | F | ✓ | ✓ | ✓ (verified rc=0) | ✗ UNTESTED | ✗ UNTESTED | gen works; needs cross-tab test |
| sH | T (allowed) | F | ✓ | ✓ | ✓ (verified rc=0) | ✗ UNTESTED | ✗ UNTESTED | triclinic BUT explicitly allowed; huge guest count (4480) |
| c0te | T | F | ✓ | ✗ BLOCKED | N/A | N/A | N/A (blocked) | hydrate-only export needs 4×4×4; 1×1×1 grompp FAILS |
| c1te | T | F | ✓ | ✗ BLOCKED | N/A | N/A | N/A (blocked) | hydrate-only export needs 4×4×4; 1×1×1 grompp FAILS |
| c2te | F | F | ✓ | ✓ | ✓ (verified rc=0) | ✗ UNTESTED | ✗ UNTESTED (gen OK) | filled ice orthorhombic; 2048 guests at 1×1×1 iface |
| ice1hte | F | F | ✓ | ✓ | ✓ (verified rc=0) | ✗ UNTESTED | ✗ UNTESTED (gen OK) | filled ice orthorhombic |
| sTprime | F | T | ✓ | ✓ | ✓ (verified rc=0) | ✗ UNTESTED | N/A (water-only) | 0 guests; verify solute/ion with guest_nmolecules=0 |
| 16 | F | F | ✓ | ✓ | ✓ (verified rc=0) | ✗ UNTESTED | ✗ UNTESTED (gen OK) | Ice XVI; same cage_map as sII |
| 17 | F | T | ✓ | ✓ | ✓ (verified rc=0) | ✗ UNTESTED | N/A (water-only) | Ice XVII; 0 guests |

**Legend:** ✓ verified | ✗ untested | N/A not applicable | COVERED = existing test | BLOCKED = by design (triclinic)

## Gap Analysis (the e2e gaps to close)

1. **New lattice types through FULL tab chain (Interface → Custom → Solute → Ion → Export)** — sII, sH, c2te, ice1hte, sTprime, 16, 17: UNTESTED through full chain (both GUI+CLI). Only interface-export grompp verified. Need solute/ion/custom tabs + grompp at each step.

2. **Triclinic blocking e2e (CLI + GUI pipeline)** — c0te/c1te: blocking EXISTS (verified `validate_interface_config` raises) but NOT proven through CLI `_run_interface_step` (returns non-zero) or GUI interface worker (emits error). `test_triclinic_blocking.py` only tests the validator directly.

3. **Triclinic filled-ice hydrate-only export (c0te, c1te)** — blocked at interface, so only Hydrate → Export is possible. CRITICAL: needs 4×4×4 supercell (1×1×1 fails grompp box-size). UNTESTED for both CLI (`_run_export_step` hydrate branch) and GUI (`HydrateGROMACSExporter.export_hydrate`).

4. **Filled-ice grompp through full chain (c2te, ice1hte)** — interface grompp verified rc=0, but NOT through Custom/Solute/Ion tabs. Context's "TEST-08 / Phase 47-05: filled-ice grompp NOT explicitly tested" = confirmed gap.

5. **Water-only lattices (sTprime, 17) through downstream tabs** — interface grompp verified (SOL only), but solute/ion inserters with `guest_nmolecules=0` UNTESTED. Risk: IndexError or empty-include bugs.

6. **Custom hydrate guest with non-sI lattices** — generation verified OK for sII/c2te/ice1hte/16. NOT tested through interface/custom/solute/ion/export + grompp. ALL custom guest e2e tests use sI only.

7. **Depol mode CLI flag (`--depol`) MISSING (45-02a)** — GUI has depol combo (hydrate_panel.py:218, strict/optimal). CLI parser has NO `--depol` flag — `depol_mode` always defaults to "strict". `HydrateConfig` accepts it (types.py:559-588); `test_hydrate_lattice_types.py::TestDepolModePassthrough` covers generation only (GUI path). CLI cannot select depol mode.

8. **Custom guest CLI flags (`--custom-guest`, `--custom-guest-itp`) MISSING** — pipeline.py:73-81 EXPLICITLY states this is DEFERRED BY DESIGN ("CLI surface is built-in-only for v4.7... The GUI already supports custom-guest mixed occupancy via the explicit API"). This is a DESIGN DECISION, not a gap to fix — but it means CLI custom-cage-guest e2e tests must use the Python API directly (the established pattern in `test_e2e_custom_guest_cross_tab_cli.py`), NOT a CLI flag.

9. **Mixed cage occupancy with new lattices + through tabs** — `test_e2e_mixed_cage_occupancy.py` (sI 2×2×2, gen only); `test_e2e_sh_cage_occupancy.py` (sH, gen only). NOT through tabs. CLI export single-stream limitation (Pitfall 2). Lower priority.

## CLI Flag Gaps

| Flag | GUI | CLI | Status | Action |
|------|:---:|:---:|--------|--------|
| `--hydrate` | ✓ | ✓ | Present | — |
| `--lattice-type` (all 10) | ✓ | ✓ (parser.py:209) | Present | — |
| `--guest` (CH4/THF) | ✓ | ✓ | Present (deprecated) | — |
| `--cage-guest` (built-in mixed) | ✓ | ✓ (parser.py:261) | Present | — |
| `--supercell-x/y/z` | ✓ | ✓ | Present | — |
| `--custom-gro` / `--custom-itp` (LIQUID molecule, Tab 3) | ✓ | ✓ | Present | — |
| `--solute-type` / `--solute-concentration` | ✓ | ✓ | Present | — |
| `--ion-concentration` / `--ion-source` | ✓ | ✓ | Present | — |
| **`--depol` (strict/optimal)** | ✓ (combo) | ✗ **MISSING** | 45-02a gap | **ADD** to `hydrate_group` in parser.py |
| **`--custom-guest` / `--custom-guest-itp` (CAGE guest)** | ✓ (panel) | ✗ **DEFERRED** | By design (pipeline.py:73-81) | Document as out-of-scope; test via API |

**The only CLI flag to ADD is `--depol`** (45-02a). Custom-cage-guest CLI flags are intentionally deferred — e2e tests use the Python API directly (matching `test_e2e_custom_guest_cross_tab_cli.py`).

`--depol` flag spec (for 45-02a):
```python
hydrate_group.add_argument(
    "--depol",
    type=str,
    choices=["strict", "optimal"],
    default="strict",
    help="Depolarization mode (default: strict). 'strict' = ice rules, zero net dipole; 'optimal' = relaxed.",
)
```
Then in `_run_source_step` (pipeline.py:332): add `depol_mode=getattr(self.args, 'depol', 'strict')` to the `HydrateConfig(...)` call. Validation: `HydrateConfig.__post_init__` already validates `depol_mode in ("strict","optimal")` (types.py:586).

## Test Strategy (small plans, 20+ acceptable per user)

The user wants SMALL plans. Structure as waves of focused test files. Each test file = 1-3 plans. Recommended breakdown:

### Wave 1: New lattices through Interface tab (foundation) — ~2 plans
- **Plan 1:** `test_e2e_lattice_interface_export.py` — parametrized sII/sH/c2te/ice1hte/sTprime/16/17 → gen → interface → export → grompp (GUI InterfaceGROMACSExporter + CLI `_run_export_step` interface branch). Module-scoped fixture per lattice. This is the FOUNDATION (proves new lattices produce grompp-valid output at the first export step). Reuse `test_e2e_builtin_cross_tab_regression.py` template.
- **Plan 2:** Add water-only (sTprime, 17) + filled-ice (c2te, ice1hte) specific assertions (no guests / single-cage-key paths).

### Wave 2: New lattices through FULL tab chain — ~2-3 plans
- **Plan 3:** `test_e2e_lattice_cross_tab_gui.py` — parametrized 7 lattices → ALL 4 GUI exporters (interface/solute/custom/ion) + grompp. Module-scoped fixture. Use Pattern 1 + 2 (fresh iface per inserter).
- **Plan 4:** `test_e2e_lattice_cross_tab_cli.py` — parametrized 7 lattices → CLI interface/solute/ion export branches + grompp. Use Pattern 4 (`_make_cli_pipeline` + `_run_export_step`).
- **Plan 5:** Water-only full-chain deep-dive (sTprime, 17) — verify solute/ion inserters don't IndexError on `guest_nmolecules=0`.

### Wave 3: Triclinic blocking + hydrate-only export — ~2 plans
- **Plan 6:** `test_e2e_triclinic_blocking_e2e.py` — c0te/c1te → CLI `_run_interface_step` returns non-zero (catches InterfaceGenerationError); GUI `InterfaceWorker` emits error (construct worker, run, assert `error` signal). Proves blocking in real pipelines, not just validator.
- **Plan 7:** `test_e2e_triclinic_hydrate_export.py` — c0te/c1te @ **4×4×4** → CLI hydrate export (`_run_export_step` hydrate branch) + GUI `HydrateGROMACSExporter.export_hydrate` → grompp rc=0. CRITICAL: 4×4×4 supercell (not 1×1×1).

### Wave 4: Custom guest with non-sI lattices — ~1-2 plans
- **Plan 8:** `test_e2e_custom_guest_lattices.py` — parametrized sII/c2te/ice1hte/16 → custom ethanol guest → interface → export → grompp (GUI + CLI). Verify `MOL_H` staged + referenced at each step. Use `test_e2e_custom_guest_cross_tab_gui.py` template, swap sI → parametrized.
- **Plan 9 (optional):** Custom guest with sH (triclinic-but-allowed) + water-only (N/A — no cages). Document sH custom guest works; sTprime/17 custom guest is N/A (water-only, no cages).

### Wave 5: Depol CLI flag (45-02a) — ~1 plan
- **Plan 10:** Add `--depol` to parser.py + thread to `HydrateConfig` in `_run_source_step`. `test_cli/test_depol_flag.py` — arg parse + `--depol optimal`/`--depol strict` reaches config + generation succeeds. DO NOT assert strict != optimal (Pitfall 1).

### Wave 6 (lower priority): Mixed occupancy + new lattices — ~1-2 plans
- **Plan 11:** Mixed cage occupancy with c2te/ice1hte (single "small" cage key) — verify single-cage-key mixed path. sII/16 mixed (small+large). Through GUI hydrate exporter (multi-molecule writers handle mixed).
- **Plan 12 (optional):** Document CLI single-stream limitation for mixed built-in (Pitfall 2) — test mixed built-in via GUI hydrate exporter only.

**Total: ~10-12 plans.** Each plan = 1 test file (or 1 flag-add + test). SMALL, focused, independently verifiable.

## Risk Areas (known crashes / edge cases)

1. **Triclinic filled-ice grompp box-size (CRITICAL):** c0te/c1te 1×1×1 FAILS grompp (box < 2.0 nm). Tests MUST use 4×4×4. Empirically verified c0te 4×4×4 → rc=0.
2. **Water-only + downstream inserters (VERIFY):** sTprime/17 have `guest_nmolecules=0`. Interface export verified OK. Solute/ion inserters UNTESTED with no guests — possible IndexError. Wave 2 Plan 5 must verify.
3. **sH huge guest count:** sH interface = 4480 guests (medium cages routed). Large but works (rc=0). Tests need ≥120s timeout; don't assert exact counts.
4. **GRO atom-number wrap (cosmetic):** c2te 4×4×4 = 220736 atoms → warning, grompp still rc=0. `assert_gro_top_consistent` is robust (counts lines, not header).
5. **CLI mixed built-in single-stream (Pitfall 2):** CLI `write_interface_*` picks ONE guest type. Mixed built-in (ch4+thf) through CLI export = known limitation. Mixed custom (same mol_type) works.
6. **Two hydrate export paths:** CLI wraps in InterfaceStructure (`write_interface_*`); GUI uses `write_multi_molecule_*`. Test BOTH separately (Pitfall 6).
7. **Ion inserter mutates iface.molecule_index:** Use fresh `assemble_slab` per inserter (Pattern 2).
8. **Auto-chaining in CLI:** `_run_solute_step`/`_run_ion_step` auto-upgrade source to most-downstream result (pipeline.py:620-625, 702-714). Tests using `_run_export_step` direct bypass this — set the correct `_<downstream>_result` explicitly.

## Test Helper Infrastructure

### Existing (REUSE — do NOT rebuild):
- `tests/e2e_export_helpers.py` (635 lines): all parsers, consistency asserts, grompp runner, chain builders, ITP staging, fixtures (ETOH_GRO/ITP, MDP_PATH).
- `tests/conftest.py`: `gmx_skipif` marker.
- `tests/test_e2e_builtin_cross_tab_regression.py`: MODULE-SCOPED multi-lattice-chain fixture + 4-exporter GUI + 4-branch CLI template (THE best template for Wave 1-2).
- `tests/test_e2e_custom_guest_cross_tab_gui.py`: fresh-iface-per-inserter + QFileDialog mock template (Wave 4).
- `tests/test_e2e_custom_guest_cross_tab_cli.py`: `_make_cli_pipeline` + `_assert_step_output` CLI template (Wave 2-4).

### May need extending (LOW confidence — verify during planning):
- Helpers for new lattice candidates: `e2e_export_helpers.py` has `_hydrate_sI_ch4_candidate`, `_hydrate_sII_ch4_candidate` etc. Consider adding `_hydrate_candidate(lattice_type, guest_type)` generic helper to reduce boilerplate, OR just inline `HydrateConfig(...)` per test (the template pattern).
- A `_assert_export_grompp(ws, gro_name, top_name, expected_mols, hydrate_config)` generic assertion helper could DRY the parametrized tests — but the existing `_assert_builtin_export` / `_assert_step_output` are already good templates. Prefer COPYING + adapting over abstracting prematurely.

## Don't Hand Roll (consolidated)

- **GRO/TOP/ITP parsing + consistency:** `e2e_export_helpers.*` (6 functions).
- **grompp execution:** `run_gmx_grompp` (handles stale .tpr, maxwarn, timeout).
- **Downstream structure building:** `_insert_solutes`, `_insert_ions`, `_insert_ions_from_solute`, `_solute_to_ion_source`.
- **Slab/pocket/piece interface:** `_make_slab_interface`, `_make_pocket_interface` OR call `assemble_slab`/`assemble_pocket`/`assemble_piece` directly.
- **Custom guest ITP staging:** `_stage_custom_guest_itp` (applies `_H` transform).
- **Built-in ITP staging:** `_stage_itp_files` (comments atomtypes).
- **CLI export branch:** `_make_cli_pipeline` + `_run_export_step()` direct (don't run full `execute()`).
- **Custom guest metadata:** `HydrateConfig(guest_type=..., guest_residue_name=..., guest_gro_path=..., guest_itp_path=..., guest_atom_labels=..., guest_atom_count=...)` — `__post_init__` auto-populates built-ins.
- **Custom guest info threading:** `_build_custom_guest_info(hydrate_config)` — None for built-in, list for custom.
- **ITP copy for export:** `copy_itp_files_for_structure` from `quickice.cli.itp_helpers`.
- **gmx skip:** `from tests.conftest import gmx_skipif`.

**Key insight:** The infrastructure is MATURE. New tests = COPY the template (`test_e2e_builtin_cross_tab_regression.py` for built-in lattices, `test_e2e_custom_guest_cross_tab_gui.py` for custom guest), SWAP sI → parametrized lattice list. ~80% of test code is reusable verbatim.

## Open Questions

1. **Water-only through solute/ion (Pitfall 3 — VERIFY in Wave 2 Plan 5):** I verified interface export works for sTprime/17 (grompp rc=0, SOL only). The solute/ion inserters' behavior with `guest_nmolecules=0` is UNVERIFIED. Risk: IndexError or empty `#include`. Recommendation: Wave 2 Plan 5 MUST run sTprime/17 through solute + ion inserters + export + grompp and assert no crash. If a crash is found, that becomes a FIX plan (not just a test plan).

2. **c1te exact supercell for grompp (HIGH confidence 4×4×4):** Verified c0te 4×4×4 → rc=0. c1te shortest vector 0.6017 nm → 4× = 2.407 nm > 2.0. Logic says 4×4×4 works but NOT empirically run for c1te. Recommendation: Wave 3 Plan 7 runs c1te 4×4×4 empirically; if it fails, try 5×5×5.

3. **GUI interface worker triclinic blocking test (MEDIUM confidence):** The GUI `InterfaceWorker` (workers.py:190-225) catches `InterfaceGenerationError` and emits `error` signal. Constructing + running the worker in a test requires QThread/QApplication setup (heavier than the GUI exporter tests). Recommendation: Wave 3 Plan 6 — test the CLI `_run_interface_step` path (simple, HIGH confidence) as the primary; test the GUI worker path IF feasible, otherwise test `generate_interface` directly with a mock candidate (already covered by `test_triclinic_blocking.py` — extend with a GUI-worker-level test if time permits).

4. **Mixed built-in through CLI export (Pitfall 2 — DESIGN LIMITATION, not a bug):** The CLI `write_interface_*` path is single-guest-stream. Mixed built-in (ch4+thf) through CLI interface/solute/ion export emits ONE guest type. This is documented in `test_cli/test_mixed_cage_cli.py:27-38`. Recommendation: Do NOT write a test asserting mixed built-in works through CLI interface export (it won't). Test mixed built-in via the GUI `HydrateGROMACSExporter` (multi-molecule writers) OR document as out-of-scope.

5. **sH through full chain performance (MEDIUM):** sH interface = 4480 guests + 49584 waters → ~54k atoms. Solute/ion insertion + grompp on this may be slow (~10-30s). Recommendation: Wave 2 tests for sH should use a SMALLER box (e.g., 2.5×2.5×6.0 nm) OR assert with `@pytest.mark.timeout(300)`. Verify during planning.

## Sources

### Primary (HIGH confidence)
- **Empirical verification (2026-07-10):** Ran all 10 lattices through `HydrateStructureGenerator.generate → to_candidate → generate_interface → write_interface_gro/top_file → copy_itp_files_for_structure → gmx grompp` in the `quickice` conda env. Confirmed: 8/10 pass interface grompp (rc=0); c0te/c1te blocked at interface (InterfaceGenerationError); c0te/c1te 1×1×1 hydrate-only grompp FAILS (box too small); c0te 4×4×4 hydrate-only grompp rc=0. `gmx` at `/data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx`.
- **`quickice/structure_generation/types.py`:** `HYDRATE_LATTICES` (10 entries, lines 84-199), `HydrateConfig.depol_mode` (line 559-588), `is_triclinic`/`is_water_only` flags.
- **`quickice/structure_generation/interface_builder.py`:** `TRICLINIC_HYDRATE_PHASES = {"hydrate_c0te", "hydrate_c1te"}` (line 121), `validate_interface_config` (line 26), `generate_interface` calls validate (line 351).
- **`quickice/cli/pipeline.py`:** `_parse_cage_guest_args` (built-in-only CLI note, lines 73-81), `_run_source_step` (hydrate branch, lines 307-362), `_run_interface_step` (catches InterfaceGenerationError, 441-444), `_run_export_step` (hydrate branch wraps in InterfaceStructure, 885-928; priority order ion>solute>custom>interface>hydrate>ice).
- **`quickice/cli/parser.py`:** All flags present EXCEPT `--depol` (MISSING). `--lattice-type` has all 10 (line 209). `--cage-guest` built-in-only (line 261).
- **`quickice/structure_generation/hydrate_generator.py`:** water-only skip (lines 291-310: `if not is_water_only`), depol threading (line 317), custom guest module injection (lines 144-183).
- **`quickice/output/guest_info.py`:** no-guest gate (line 250: `if guest_atom_count <= 0 or guest_nmolecules <= 0: return None, {}`).
- **`quickice/gui/export.py`:** 4 exporters (Interface/Solute/CustomMolecule/Ion), all accept `hydrate_config` param.
- **`quickice/gui/main_window.py`:** all 4 export handlers pass `hydrate_config=self._current_hydrate_config` (lines 1651-1652, 1748-1749, 1811-1812, 1870-1871).
- **`quickice/gui/workers.py`:** `InterfaceWorker` catches `InterfaceGenerationError` (lines 200, 215-218).
- **`quickice/gui/hydrate_panel.py`:** depol combo (line 218-220), `get_configuration` builds cage_guest_assignments (lines 705-738).
- **`tests/e2e_export_helpers.py`:** full helper inventory (635 lines).
- **`tests/test_e2e_builtin_cross_tab_regression.py`:** module-scoped multi-chain fixture + 4 GUI + 4 CLI template (448 lines, PASSES).
- **`tests/test_e2e_custom_guest_cross_tab_gui.py`:** fresh-iface-per-inserter + QFileDialog mock template (451 lines).
- **`tests/test_e2e_custom_guest_cross_tab_cli.py`:** `_make_cli_pipeline` + `_assert_step_output` CLI template (298 lines).
- **`tests/test_triclinic_blocking.py`:** `validate_interface_config` direct tests (109 lines).
- **`tests/test_hydrate_lattice_types.py`:** 157 structural tests + `TestDepolModePassthrough` (405 lines).

### Secondary (MEDIUM confidence)
- **`tests/test_cli/test_mixed_cage_cli.py` docstring (lines 27-38):** documents CLI `write_interface_*` single-guest-stream limitation for mixed built-in.
- **`quickice/gui/hydrate_export.py`:** GUI `HydrateGROMACSExporter.export_hydrate` uses `write_multi_molecule_*` (different from CLI path).

### Tertiary (LOW confidence — verify during planning)
- **c1te 4×4×4 grompp:** inferred from c0te 4×4×4 (rc=0) + c1te shortest-vector math (0.6017×4=2.407>2.0). Not directly run for c1te.
- **Water-only through solute/ion:** interface export verified OK; downstream inserters UNVERIFIED (Pitfall 3).
- **GUI InterfaceWorker blocking test feasibility:** worker requires QThread setup; may need mock-based approach.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all verified in the `quickice` env (GenIce2 2.2.13.1, gmx 2023.5, PySide6 6.10.2).
- Architecture (tab flow, export paths): HIGH — read all relevant source; empirically ran lattices through interface+grompp.
- Lattice matrix: HIGH — empirically verified 8/10 interface grompp + c0te 4×4×4 hydrate grompp.
- Triclinic blocking e2e: HIGH (blocking exists) / MEDIUM (GUI worker test feasibility).
- CLI flag gaps: HIGH — read parser.py (552 lines) fully; `--depol` confirmed absent.
- Water-only downstream: MEDIUM — interface verified; solute/ion unverified (flagged Open Question 1).
- Pitfalls: HIGH — Pitfall 1 (box-size) empirically verified; Pitfall 2 (single-stream) from test docstring; Pitfall 5 (sH count) empirically observed.

**Research date:** 2026-07-10
**Valid until:** 2026-08-10 (30 days — stable codebase, no fast-moving deps; GenIce2/gmx versions pinned)
